# LinkedIn Agent

**Role:** Leaf agent under Social Media Manager. Drafts LinkedIn posts, audits
them against a bounded revision cap, gets Hasnain's approval in Discord.

**Status:** Active (Phase 1, 2026-09-29).

**Skills:** linkedin-post-writer, linkedin-comment-drafter, linkedin-content-planner,
linkedin-profile-optimizer, linkedin-engager-analytics, linkedin-approval-loop
(custom). `linkedin-humanizer` was deliberately skipped — its AI-detector
sub-feature needs five paid API keys we don't have; the mechanical parts of
its checklist were reimplemented directly in `linkedin-approval-loop`.

**Tools:** clarify, terminal.

**Data:** reads/writes `drafts` (Neon), scoped to no other agent's rows.

**Never does:** publish content, revise a draft twice, act on any platform
other than LinkedIn.

See [`src/agents/social-media-manager/linkedin/README.md`](../../agents/social-media-manager/linkedin/README.md)
for the full scope statement.
