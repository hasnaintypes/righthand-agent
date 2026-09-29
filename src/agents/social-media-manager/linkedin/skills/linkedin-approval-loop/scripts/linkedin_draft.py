#!/usr/bin/env python3
"""Deterministic state machine for the LinkedIn draft approval loop.

State machine (Architecture Document): drafted -> checking -> revising -> checking
-> awaiting_approval (clean, or escalated with flags after a second failed check)
-> approved | rejected.

The one hard rule enforced HERE, not left to model discretion: a draft may be
sent back for revision at most once. The second failed check always escalates.

Usage:
    linkedin_draft.py create <platform> <content-file>        # new draft, prints draft_id
    linkedin_draft.py audit <draft_id>                        # run checklist, advance state
    linkedin_draft.py revise <draft_id> <content-file>        # save revised content
    linkedin_draft.py decide <draft_id> approve|reject         # record Hasnain's decision
"""
import json
import os
import re
import sys
import uuid

import psycopg2


def _conn():
    conn_str = os.environ["NEON_CONNECTION_STRING"]
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    return conn


# Mechanical subset of references/humanizer-checklist.md — the objectively
# checkable rules only. Subjective judgment (paragraph rhythm, staccato
# stacks, hedging) stays with the drafting model; this script exists to
# enforce the retry cap deterministically, not to fully automate the checklist.
BANNED_PHRASES = [
    "it's not just", "the result?", "the catch?", "stop overthinking, start",
    "here's what", "here's how", "here's the thing",
    "in today's fast-paced world", "game-changer", "game changer",
    "deep dive", "at the end of the day", "needle-moving",
]


def run_checklist(content: str) -> list[str]:
    hits = []
    lower = content.lower()

    for phrase in BANNED_PHRASES:
        if phrase in lower:
            hits.append(f"banned phrase: \"{phrase}\"")

    words = max(len(content.split()), 1)
    em_dash_count = content.count("—")
    if em_dash_count / words * 100 > 2:
        hits.append(f"em dash density too high ({em_dash_count} in {words} words)")

    if "–" in re.sub(r"\d\s*–\s*\d", "", content):
        hits.append("en dash used between clauses (only number ranges allowed)")

    if "--" in content:
        hits.append("double dash (--) used")

    if "“" in content or "”" in content:
        hits.append("curly quotes used (should be straight quotes)")

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    for p in paragraphs:
        if len(p.split()) == 1:
            hits.append(f"one-word paragraph: \"{p}\"")

    if content.strip().rstrip("?").lower().endswith("what do you think"):
        hits.append('closes with "What do you think?"')

    return hits


def cmd_create(platform: str, content_path: str) -> None:
    with open(content_path, encoding="utf-8") as f:
        content = f.read()
    draft_id = str(uuid.uuid4())
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into drafts (draft_id, platform, content, state) values (%s, %s, %s, 'drafted')",
            (draft_id, platform, content),
        )
    print(json.dumps({"draft_id": draft_id, "state": "drafted"}))


def cmd_audit(draft_id: str) -> None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("select content, state, flags from drafts where draft_id = %s", (draft_id,))
        row = cur.fetchone()
        if row is None:
            print(json.dumps({"error": f"no draft {draft_id}"}))
            sys.exit(1)
        content, state, flags_raw = row
        flags = json.loads(flags_raw) if flags_raw else {"revision_count": 0}

        hits = run_checklist(content)

        if not hits:
            new_state = "awaiting_approval"
            flags["escalated"] = False
            flags["checklist_hits"] = []
        elif flags.get("revision_count", 0) == 0:
            new_state = "revising"
            flags["revision_count"] = 1
            flags["checklist_hits"] = hits
        else:
            # Second failed check: always escalate, never revise again.
            new_state = "awaiting_approval"
            flags["escalated"] = True
            flags["checklist_hits"] = hits

        cur.execute(
            "update drafts set state = %s, flags = %s, updated_at = now() where draft_id = %s",
            (new_state, json.dumps(flags), draft_id),
        )
        print(json.dumps({"draft_id": draft_id, "state": new_state, **flags}))


def cmd_revise(draft_id: str, content_path: str) -> None:
    with open(content_path, encoding="utf-8") as f:
        content = f.read()
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "update drafts set content = %s, state = 'checking', updated_at = now() where draft_id = %s",
            (content, draft_id),
        )
    print(json.dumps({"draft_id": draft_id, "state": "checking"}))


def cmd_decide(draft_id: str, decision: str) -> None:
    if decision not in ("approve", "reject"):
        print(json.dumps({"error": "decision must be approve or reject"}))
        sys.exit(1)
    new_state = "approved" if decision == "approve" else "rejected"
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "update drafts set state = %s, updated_at = now() where draft_id = %s",
            (new_state, draft_id),
        )
    print(json.dumps({"draft_id": draft_id, "state": new_state}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "create":
            cmd_create(sys.argv[2], sys.argv[3])
        elif cmd == "audit":
            cmd_audit(sys.argv[2])
        elif cmd == "revise":
            cmd_revise(sys.argv[2], sys.argv[3])
        elif cmd == "decide":
            cmd_decide(sys.argv[2], sys.argv[3])
        else:
            print(__doc__)
            sys.exit(1)
    except IndexError:
        print(__doc__)
        sys.exit(1)
