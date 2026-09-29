---
name: linkedin-approval-loop
description: Draft -> audit -> bounded revision -> Discord approval for LinkedIn posts, backed by Neon
---

# LinkedIn Approval Loop

Wraps `linkedin-post-writer` with the draft/validate/approve/log loop from the
Architecture Document's state machine. Use this whenever Hasnain asks for a
LinkedIn post to be drafted — never post content he hasn't approved in this
chat (there is no publish credential configured; approval just means "ready
to paste in").

## Steps

1. **Draft.** Use `/linkedin-post-writer` to write the post per Hasnain's request.
2. **Create the draft row.** Write the content to a scratch file, then:
   ```
   python scripts/linkedin_draft.py create linkedin /path/to/content.txt
   ```
   This prints `{"draft_id": "...", "state": "drafted"}`. Keep the `draft_id`.
3. **Audit.**
   ```
   python scripts/linkedin_draft.py audit <draft_id>
   ```
   Reads back one of two outcomes:
   - `state: awaiting_approval, escalated: false` — clean, go to step 5.
   - `state: revising, checklist_hits: [...]` — fix exactly those issues
     (nothing else — don't rewrite a clean paragraph because you're touching
     the file), save the revised text to a file, then:
     ```
     python scripts/linkedin_draft.py revise <draft_id> /path/to/revised.txt
     python scripts/linkedin_draft.py audit <draft_id>
     ```
     This second audit can only return `awaiting_approval` — clean or
     escalated with flags. **Never call `revise` a second time for the same
     draft; the script enforces the one-revision cap regardless, but don't
     try.**
4. If the second audit came back `escalated: true`, note the specific
   `checklist_hits` — you'll show these to Hasnain, not hide them.
5. **Get approval.** Call the `clarify` tool with the full draft text in the
   question (and the checklist hits if escalated), choices `["Approve",
   "Reject"]`. If Hasnain's answer includes edit instructions instead of a
   clean approve/reject, apply them, save via `revise` (this is a
   Hasnain-directed edit, not a checklist retry, so it doesn't count against
   the one-revision cap), and ask for approval again.
6. **Record the decision.**
   ```
   python scripts/linkedin_draft.py decide <draft_id> approve
   python scripts/linkedin_draft.py decide <draft_id> reject
   ```
7. On approval, give Hasnain the final text in a clean copy-paste block — he
   posts it manually. On rejection, ask if he wants to try a different angle
   or drop it; log his stated reason so it isn't silently forgotten (per the
   Architecture Document's edge case: a rejection is feedback for next time,
   not a retry trigger).

## Requires

`NEON_CONNECTION_STRING` in the environment (already set for this deployment).
