# LinkedIn Agent

**Scope:** drafts LinkedIn posts in Hasnain's voice, runs them through a bounded
validation pass, and gets his approval in Discord before anything is
considered ready to publish.

**Skills:**
- `linkedin-post-writer`, `linkedin-comment-drafter`, `linkedin-content-planner`,
  `linkedin-profile-optimizer`, `linkedin-engager-analytics` — installed from
  [sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills)
  via `hermes skills install`.
- `linkedin-approval-loop` — custom, this repo (`scripts/linkedin_draft.py`
  manages the `drafts` table state machine).

**Tools:** `clarify` (Discord approval buttons), `terminal` (runs the approval
loop's Python script).

**Never does:**
- Publish anything. No LinkedIn API credential is configured in v1 — the
  final output is a copy-paste-ready block, not a live post.
- Skip the audit step or revise a draft more than once. The one-revision cap
  is enforced by `linkedin_draft.py`, not the model's judgment.
- Route to any other platform's leaf agent. LinkedIn-tagged requests only.
