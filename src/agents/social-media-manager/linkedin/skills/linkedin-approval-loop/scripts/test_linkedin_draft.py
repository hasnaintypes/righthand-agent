"""Self-check for linkedin_draft.py's state machine.

Run directly: python3 test_linkedin_draft.py
Needs NEON_CONNECTION_STRING in the environment (same as the script itself).
Creates and deletes its own throwaway rows -- safe to run against the real DB.
"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(__file__), "linkedin_draft.py")


def run(*args):
    result = subprocess.run(
        [sys.executable, SCRIPT, *args], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def write_temp(content):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


def cleanup(draft_id):
    import psycopg2

    conn = psycopg2.connect(os.environ["NEON_CONNECTION_STRING"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("delete from drafts where draft_id = %s", (draft_id,))
    conn.close()


def test_checklist_catches_banned_phrase():
    sys.path.insert(0, os.path.dirname(__file__))
    from linkedin_draft import run_checklist

    hits = run_checklist("This is a total game-changer for your career.")
    assert any("game-changer" in h for h in hits), hits


def test_clean_content_passes_first_audit():
    path = write_temp("A clean, specific post about one afternoon debugging a flaky test.")
    created = run("create", "linkedin", path)
    draft_id = created["draft_id"]
    try:
        result = run("audit", draft_id)
        assert result["state"] == "awaiting_approval", result
        assert result["escalated"] is False, result
    finally:
        cleanup(draft_id)


def test_one_revision_cap_enforced():
    """The architecture-invariant test: a second failed check must escalate,
    never route back to revising, no matter how bad the content still is."""
    bad_content = "This is a total game-changer, here's the thing about it."
    path = write_temp(bad_content)
    created = run("create", "linkedin", path)
    draft_id = created["draft_id"]
    try:
        first = run("audit", draft_id)
        assert first["state"] == "revising", first
        assert first["revision_count"] == 1, first

        # Simulate a revision that still fails every check.
        revised_path = write_temp(bad_content)
        run("revise", draft_id, revised_path)

        second = run("audit", draft_id)
        assert second["state"] == "awaiting_approval", second
        assert second["escalated"] is True, second
        assert second["checklist_hits"], second
    finally:
        cleanup(draft_id)


if __name__ == "__main__":
    tests = [
        test_checklist_catches_banned_phrase,
        test_clean_content_passes_first_audit,
        test_one_revision_cap_enforced,
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print("All tests passed.")
