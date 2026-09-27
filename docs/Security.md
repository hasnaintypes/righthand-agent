# righthand-agent — Security

Sep 27, 2026 · @Hasnain

Companion to the [PRD](./PRD.md) and [Architecture Document](./Architecture%20Document.md) (see its **Security & Access Boundaries** table for the source-of-truth summary this file expands on). Split out from the Build Roadmap so security requirements are checkable independently of build sequencing, and so each phase's exit criteria can link back here instead of restating the rule.

## Guiding principle

Every boundary in this system is enforced **at the credential level, not the code level, wherever that's possible.** A skill's prompt or logic saying "don't write to GitHub" is not a boundary — a read-only PAT that is physically incapable of writing is. This principle shows up repeatedly below; treat it as the default answer to "is this permission scoped tightly enough?"

## Secrets

- Discord bot token, GitHub credential, Notion integration token, Neon connection string, and model provider keys live **only** in Railway environment variables.
- The repo's `.env.example` carries placeholder names only — never a real value, never even in a private branch, never in commit history (if one leaks, rotate it — don't just delete the commit).
- No secret is duplicated into Inngest config separately — Inngest functions call back into the same Hermes process (per the Architecture Document's Deployment Topology), so they inherit the same environment rather than needing their own copy of any credential.

## GitHub — the boundary that matters most

- **Scope:** Read-only PAT or GitHub App installation scoped to exactly `contents:read` + `issues:read`. No broader scope, ever, for any reason — not even temporarily for debugging.
- **Why this is the priority boundary:** it's the one credential in the system with write capability to an external system that Hasnain has explicitly reserved for himself (PRD non-goal: "No GitHub write access of any kind"). Every other boundary in this doc is important; this one is load-bearing for a hard product constraint.
- **Enforcement:** at the credential level. A bug in `roadmap-sync` or `triage-issue` cannot write to GitHub even if its logic tried to, because the token it holds is physically incapable of it.
- **Required test (see [Code Style Guide.md](./Code%20Style%20Guide.md)):** Project Manager's test suite must include a test that deliberately attempts a GitHub write and asserts it is rejected by the token itself — this is a Phase 3 sign-off condition in the Build Roadmap, not an optional nice-to-have.

## Notion

- Integration permissions scoped **per-database** (tasks, projects, learning tracks, idea dump) rather than workspace-wide.
- The agent should not be able to see or touch Notion pages that have nothing to do with this system, even if Hasnain's workspace grows to include unrelated pages later.
- Read/write is allowed here (unlike GitHub) but only on the fields the agent owns — status and priority sync — per the Architecture Document's Component Responsibilities table (Project Manager writes "Notion (status/priority fields it owns)," nothing else).

## Discord

- The orchestrator responds only to **Hasnain's Discord user ID** — not to anyone else who might end up in that server, now or later.
- The bot's own server permissions are scoped to read/send in one channel — not admin-level permissions it has no use for.
- This is the single human-facing surface for the entire system (per the PRD's interaction model), so an access-control bug here is the highest-leverage bug in the repo: it's the one place an unauthorized actor could both read private context and trigger agent actions.

## Publishing credentials (LinkedIn / Reddit / dev.to / Medium)

- **No publish credentials are configured anywhere in v1.** This is a deliberate security property, not just a scope decision — since publishing tools are backlogged per the PRD, there is no credential in existence that could auto-publish, even if the approval-loop logic had a bug.
- Consequence: the worst case in v1 is a bad Discord message, never an unauthorized public post. Keep this true through Phase 5 (Dev.to + Medium Agents) — those agents produce drafts and links, they do not get API keys.
- **When publishing credentials are eventually added** (backlogged, not v1 — see PRD's Tech Stack row on Postiz / Free-AI-Social-Media-Scheduler): that phase deserves the same credential-level scrutiny Phase 3's GitHub token got, not just a code review. Scope each platform credential to the narrowest permission the platform's API offers (e.g., post-only, no read-DM / read-connections scopes), and add the same "assert a disallowed action is rejected" test pattern used for GitHub.

## Neon

- Connections over TLS (Neon's default).
- Through Neon's **connection pooler**, not direct long-lived connections from the Hermes process — avoids exhausting connection limits during a long-running session (Hermes runs as a single long-lived container per the Architecture Document's Deployment Topology).
- Row scoping is **application-level** (`agent_id` on `memory_chunks`, per the Data Model), not row-level security — acceptable because this is single-user, single-tenant. If this system ever grows a second human user, this decision needs revisiting; it is not currently a gap, but it is not a guarantee that scales past one user.

## Separation from the startup's Hermes instance

- Fully separate deployment, separate Neon database, no shared credentials or memory with the startup's Hermes-based PM bot.
- Enforced by **physical separation** (separate Railway service, separate Neon project), not a config flag or environment toggle that could be flipped by mistake.

## Dependency hygiene

- Pin all dependency versions (`pyproject.toml`, matching the Code Style Guide's tooling-version convention).
- Enable Dependabot (or equivalent) on the repo.
- Review dependency updates before merging — don't auto-merge Dependabot PRs. This repo's deployment environment holds real credentials (Discord token, GitHub PAT, Notion token, Neon connection string, model provider keys), so a compromised dependency here has more reach than in a typical side project with no persistent secrets.

## Audit trail

- Every approval/rejection decision is logged in the `drafts` table (state, flags) — by design, per the Architecture Document's Data Model.
- Every rearrangement action is logged in the `miss_log` table.
- This isn't just observability — it's the answer to "why did it reschedule X" or "why did this post get flagged" months from now, without needing to reconstruct it from memory or Discord scrollback.

## Kill switch

- A documented, tested way to fully stop the orchestrator from acting must exist **before Phase 1 ships**, not be added later once something's already misbehaving.
- Pausing the Railway service is sufficient as the mechanism — no need to build an in-app "pause" command as a v1 requirement. But "sufficient" only holds if it's actually been tested once (paused, confirmed no Discord activity, no cron firing, resumed cleanly) — untested is the same as not existing.

## Overall blast radius (v1)

With GitHub write access absent and publish credentials absent in v1, **the system cannot lose data or take an unauthorized public action even in a worst-case bug.** Treat this constraint as a feature to preserve, not a limitation to lift quickly:

- Every future phase that adds real write access (GitHub write scope, any publish credential) is a phase that removes part of this guarantee, and deserves the Phase 3 level of credential-level scrutiny, not just a code review.
- If a future request asks to "just add write access for convenience," that request should be weighed against this document, not approved by default.

## Security checklist by phase (cross-reference)

See the Build Roadmap's Definition of Done table for the full per-phase testing checklist. The security-relevant sign-offs are:

| Phase | Security condition that must hold before sign-off |
| --- | --- |
| 0. Foundation | Kill switch (Railway pause) tested once |
| 1. LinkedIn Agent | No publish credential configured; approval gate cannot be bypassed by a retry-loop bug (2-pass cap enforced in code, see state machine) |
| 3. Project Manager | GitHub write attempt rejected at the token level, not just code level; Notion scoped per-database, not workspace-wide |
| 5. Dev.to + Medium | Still no publish credentials configured — drafts/links only |
| 7. Generic Manager + hardening | Dependabot enabled; dependency review process actually exercised once, not just configured |
