# righthand-agent — Build Roadmap

Sep 27, 2026 · @Hasnain

## Overview

This is the build order — what to ship, in what sequence, and how to know each phase is actually done before starting the next. It assumes the [PRD](./PRD.md) (scope, skills, tech stack) and the [Architecture Document](./Architecture%20Document.md) (components, data flow, data model) as given; this document doesn't repeat their content, it sequences it and tells you exactly which piece of which doc to build from at each step.

Code style and security are no longer sections of this doc — they're their own files so they can be enforced (linter config, credential checklist) independently of build order:

- **[Code Style Guide.md](./Code%20Style%20Guide.md)** — language, skill file shape, formatting/linting, type hints, naming, commits, testing convention, per-agent README requirement.
- **[Security.md](./Security.md)** — secrets handling, per-integration credential scoping (GitHub/Notion/Discord/Neon), publish-credential policy, kill switch, audit trail, and a per-phase security checklist.

The ordering principle carried over from the PRD: prove the core loop once (draft → validate → approve → log) on one platform before replicating it, and keep the Task Manager branch independent enough to build in parallel with the Social Media Manager branch once each proves itself separately.

## Build Order at a Glance

| Phase | Delivers | Depends on | Can parallelize with |
| --- | --- | --- | --- |
| 0. Foundation | Railway + Discord + Neon + repo scaffold, nothing agent-specific yet | — | — |
| 1. LinkedIn Agent + approval loop | The core draft → validate → approve → log loop, proven once | Phase 0 | — |
| 2. Reddit Agent | Same loop, second platform | Phase 1 | Phase 3 |
| 3. Project Manager | Read-only GitHub + Notion sync, tasks/projects tables | Phase 0 | Phase 2 |
| 4. Rearrangement + morning briefing | Priority-aware scheduling, miss-streak detection, idea dump | Phase 3 | — |
| 5. Dev.to + Medium Agents | Multi-platform content reuse | Phase 2 | Phase 6 |
| 6. Learning Manager | Same rearrangement logic, applied to learning tracks | Phase 4 | Phase 5 |
| 7. Generic Manager + hardening | Unstructured intake, Control Room pattern, skill governance | Phases 1–6 all running | — |

Phases 2 and 3 can run in parallel once Phase 1 proves the approval loop works — they don't depend on each other. Phase 7 is deliberately last: it needs the other six agents to exist before there's anything to govern or route between.

## How to read each phase

Every phase below follows the same shape so it can double as a checklist while building:

- **Build** — concrete files/directories/config to create, referencing the PRD's repo structure and skill tables directly.
- **Data touched** — which Neon tables from the Architecture Document's Data Model this phase reads/writes, and who else reads them.
- **Credentials / env vars** — what needs to exist in Railway env vars before this phase can run (see [Security.md](./Security.md) for scoping rules).
- **Exit criteria** — the bar for calling the phase done. Not "the code runs" — every phase's bar includes either a multi-day unattended run or an explicit security-boundary test.

## Phase Details

### Phase 0 — Foundation

**Build**

- Railway service running the bare Hermes container, Docker-based, with a persistent volume attached (so sessions/skill state survive restarts — see Architecture Document's Deployment Topology).
- Discord bot connected via Hermes's native gateway; access control restricted to Hasnain's Discord user ID only (see Security.md's Discord section) — no other user ID should get a response, test this by having a second account message the bot and confirming silence.
- Neon Postgres project provisioned, `pgvector` extension enabled, connected via connection string (external to Railway, not a Railway add-on) through Neon's pooler endpoint, not the direct endpoint.
- Repo scaffolded exactly per the PRD's Repo & Project Structure:
  ```
  righthand-agent/
  ├── src/
  │   ├── control-room/agents/     # empty for now — populated per-phase from Phase 1 on
  │   ├── control-room/runbooks/
  │   ├── orchestrator/            # Hermes config, routing rules, Discord gateway config
  │   ├── agents/social-media-manager/
  │   ├── agents/task-manager/
  │   ├── memory/                  # Neon schema + migrations
  │   └── inngest/                 # empty until Phase 4
  ├── railway.json
  └── .env.example                 # placeholder names only, see Security.md
  ```
- `src/memory/` gets its first migration here: the `agents` table only (bootstrap row per agent, written once by the orchestrator — see Data Model). Every other table (`tasks`, `drafts`, `miss_log`, etc.) is created in the phase that first needs it, not all up front — a `memory_chunks` table nothing writes to yet is dead schema.
- Kill switch tested once per Security.md: pause the Railway service, confirm no Discord response and no cron firing, resume, confirm normal operation resumes.

**Data touched:** `agents` (created + first bootstrap row).

**Credentials / env vars:** `DISCORD_BOT_TOKEN`, `NEON_CONNECTION_STRING`, model provider key(s) for Hermes itself.

**Exit criteria:** Hasnain can message the bare orchestrator in Discord and get a response; the Hermes process can read and write Neon; the kill switch has been exercised once, not just documented.

### Phase 1 — LinkedIn Agent + Approval Loop

**Build**

- `src/agents/social-media-manager/linkedin/skills/` — install the six skills from the PRD's LinkedIn Agent table: `linkedin-post-writer`, `linkedin-humanizer`, `linkedin-comment-drafter`, `linkedin-content-planner`, `linkedin-profile-optimizer`, `linkedin-engager-analytics` (source: [sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills)).
- Social Media Manager routing config in `src/orchestrator/`: routes platform-tagged requests to `linkedin/`, and reads/writes `memory_chunks` scoped to `agent_id = social-media-manager` for the shared voice/style context (per Architecture Data Model note on `memory_chunks.agent_id` scoping).
- `src/memory/` migration for the `drafts` table (`draft_id`, `platform`, `content`, `state`, `flags` — Data Model).
- Implement the validation state machine exactly as specified in the Architecture Document's State Machine diagram: `Drafted → Checking → Passed | Revising → Checking → Escalated`. **The hard rule to encode directly in code, not just prompt:** `Checking` can only route to `Revising` once — the second flag always routes to `Escalated`. This is a state machine invariant, not a suggestion to the model.
- Wire `linkedin-humanizer`'s AI-detector pass as the audit step that drives `Checking`'s transitions.
- Discord approval flow: `Passed` and `Escalated` drafts both land in Discord (per the sequence diagram) with approve/reject/edit options; an `Escalated` draft additionally carries the specific flags (e.g., "detector flagged this as AI-written, paragraph 2").
- `src/control-room/agents/linkedin-agent.md` — first Control Room registry entry, plus `src/agents/social-media-manager/linkedin/README.md` per the Code Style Guide's per-agent README requirement.

**Data touched:** `drafts` (written by LinkedIn Agent, read by Social Media Manager + Orchestrator), `memory_chunks` (read for voice/style, agent_id-scoped).

**Credentials / env vars:** none new — no publish credential (see Security.md: publishing is backlogged, drafts/links only in v1).

**Exit criteria:** a LinkedIn draft goes from request to logged approval/rejection end to end, and runs unattended for 7 days before Phase 2 starts. State machine unit tests cover all transitions, including the 2-pass retry cap specifically (a test that tries to force a third pass and asserts it's rejected).

### Phase 2 — Reddit Agent

**Build**

- `src/agents/social-media-manager/reddit/skills/` — install `reddit-poster` (discover → draft → dry-run → approve flow, flair handling; [cskwork/reddit-skill](https://github.com/cskwork/reddit-skill)) and `reddit-insights` (semantic search for pain points/idea validation; [BrianRWagner/ai-marketing-claude-code-skills](https://github.com/BrianRWagner/ai-marketing-claude-code-skills), `reddit-insights/SKILL.md`).
- Reuse Phase 1's `drafts` table and state machine unmodified — new rows with `platform = reddit`. No schema change, no new state machine.
- Extend Social Media Manager's routing to send Reddit-tagged requests to `reddit/`, still processed sequentially after LinkedIn per the PRD's "Processing order" rule (SMM runs its four leaves one at a time, not in parallel) — confirm this ordering is actually enforced in the routing code, not just assumed.
- `src/control-room/agents/reddit-agent.md` + README, matching Phase 1's pattern.

**Data touched:** `drafts` (`platform = reddit`), same table as Phase 1 — no new table.

**Credentials / env vars:** none new — Reddit posting itself is manual (dry-run + link, per reddit-poster's flow); no Reddit API write credential configured.

**Exit criteria:** same approval flow works for Reddit with zero changes to the state machine; Hasnain posts manually via the link the agent provides. Phase 1's test suite re-run against `platform = reddit` passes without modification (this is the proof that the loop actually generalized, not just LinkedIn-shaped code with a second copy for Reddit).

### Phase 3 — Project Manager

**Build**

- Provision a read-only GitHub PAT or GitHub App installation scoped to exactly `contents:read` + `issues:read` — see Security.md, this is the highest-priority credential boundary in the whole system. Set as a Railway env var, never committed.
- Connect Notion, scoped per-database (tasks, projects — not workspace-wide).
- `src/agents/task-manager/project-manager/skills/` — install `triage-issue` in **read-only mode** ([warpdotdev/oz-for-oss](https://github.com/warpdotdev/oz-for-oss/blob/main/.agents/skills/triage-issue/SKILL.md), tool permissions scoped to read only — no label/comment/assign calls anywhere in its invoked path), `spec-to-implementation` ([tommy-ca/notion-skills](https://github.com/tommy-ca/notion-skills)), and `notion-cli` ([CaesiumY/notion-cli-skill](https://github.com/CaesiumY/notion-cli-skill)) for reading/writing only the Notion fields Project Manager owns (status, priority).
- Build `roadmap-sync` as a **custom skill** (no existing repo fits Hasnain's specific schema, per the PRD) — polls Notion + GitHub every 5–10 min via Railway native cron, matches new/updated items against the 90-day roadmap and project priority tier, writes `tasks` and `projects`.
- Build `context-switch-guard` as a **custom skill** (also has no real repo match per the PRD) — scope this small; it's a guard, not a scheduler (scheduling logic belongs to Phase 4's rearrangement pass).
- `src/control-room/agents/project-manager.md` + README stating explicitly, per the Architecture Document's Component Responsibilities table: "Never writes to GitHub in any form."

**Data touched:** `tasks` (`task_id`, `project_id`, `notion_id`, `github_issue_id` nullable, `status`, `priority`, `due_date` — written by sync job, read by Task Manager + Project Manager), `projects` (`project_id`, `name`, `priority_tier`, `roadmap_ref` — written by sync job from Notion, read by Task Manager + rearrangement logic).

**Credentials / env vars:** `GITHUB_READONLY_TOKEN` (or GitHub App installation credentials), `NOTION_INTEGRATION_TOKEN` scoped per-database.

**Exit criteria:** `tasks` reflects a Notion or GitHub change within 10 minutes (the 5–10 min cron interval plus processing). Security test: a deliberate attempt to write to GitHub through the skill fails **at the credential level** — the test should call the actual token against a write endpoint and assert a 403/permission error, not just assert the skill's code path never calls a write function.

### Phase 4 — Rearrangement & Morning Briefing

**Build**

- `src/inngest/` gets its first two functions, matching the Architecture Document's Deployment Topology (`FN1: rearrangement`, `FN2: briefing`) — these call back into the same Hermes process rather than duplicating agent logic outside it.
- **Rearrangement function** (midnight trigger): reads `tasks`, `projects.priority_tier`, `miss_log`; implements the PRD's Task & Learning Rearrangement Logic in full:
  - Priority signal read first, before touching anything else.
  - Project batching: favor consecutive work on the same project over daily context-switching, unless a higher-priority + time-sensitive project overrides it.
  - Missed-task rearrangement: unfinished tasks re-slot into upcoming days by priority, not just pushed to tomorrow.
  - Writes the re-slotted plan back to `tasks`.
- **Briefing function** (before 9am, gated on rearrangement's Inngest step-completion signal — not a race, an explicit dependency per the Architecture Document's sequence diagram note: "Briefing job waits on rearrangement's completion signal rather than racing it"): reads the updated plan, hands off to the Orchestrator, which posts to Discord.
- **Consecutive-miss detection**, writing/reading `miss_log`: on a 2–3 day miss streak, do not silently reduce scope — flag the pattern in the morning briefing and ask Hasnain directly (retry full load, or cut lower-priority items). If Hasnain doesn't answer, per the PRD's edge case table: don't re-ask every day, note "pending Hasnain's call" in subsequent briefings until answered.
- **Idea-dump intake**: when Hasnain mentions a new idea mid-conversation, the Orchestrator checks `idea_dump` for overlap before adding — flag overlap explicitly rather than silently merging or silently duplicating.
- **Edge case to encode explicitly, not assume:** Notion vs. GitHub status conflicts — GitHub is source of truth for code state, Notion for priority/planning; on conflict, flag in the briefing rather than silently picking one.

**Data touched:** `tasks` (rearranged plan, written), `miss_log` (`date`, `tasks_missed`, `consecutive_count` — written by rearrangement job), `idea_dump` (`idea_id`, `description`, `status`, `overlap_flag` — written by Orchestrator on intake).

**Credentials / env vars:** Inngest API key/signing key; no new external credentials.

**Exit criteria:** a to-do list appears in Discord before 9am for 7 consecutive days with no manual intervention; a simulated 3-day miss streak correctly triggers the retry-or-reduce prompt and — this is the part to actually test, not assume — never auto-reduces without asking first.

### Phase 5 — Dev.to + Medium Agents

**Build**

- `src/agents/social-media-manager/devto/` — no dedicated "voice" skill exists for dev.to (per the PRD), so this agent reuses LinkedIn Agent's `linkedin-content-planner` output, reformatted, rather than drafting independently. Publishing via `publish-devto` (GitHub Action, [cloudx-labs/publish-devto](https://github.com/cloudx-labs/publish-devto)) or `devto-cli` ([rnag/devto-cli](https://github.com/rnag/devto-cli)) as the calling mechanism — but see Security.md: **no publish credential gets configured yet**, this phase produces formatted drafts/links only, same as LinkedIn/Reddit.
- `src/agents/social-media-manager/medium/` — adapts the `publish-all` pattern ([iPythoning/publish-all](https://github.com/iPythoning/publish-all), extensible per-platform converter) for Medium's format, or `post-to-medium-action` ([philips-software/post-to-medium-action](https://github.com/philips-software/post-to-medium-action)) as the reference implementation to adapt from.
- Both reuse Phase 1's `drafts` table (`platform = devto` / `platform = medium`) and the same state machine — no schema change.
- `src/control-room/agents/devto-agent.md` and `medium-agent.md` + READMEs.

**Data touched:** `drafts` (`platform = devto`, `platform = medium`) — same table, no new schema.

**Credentials / env vars:** none new (see Security.md — still no publish credentials configured in v1).

**Exit criteria:** one piece of content (from LinkedIn's content-planner) produces correctly formatted drafts for all four platforms in a single pass. Manual spot-check of formatting on all four before calling this done — an automated format-conversion test per platform catches structural regressions later but doesn't replace one human look at real output the first time.

### Phase 6 — Learning Manager

**Build**

- `src/agents/task-manager/learning-manager/skills/` — install `goal-tracker` (milestones, daily logging, weekly summary, HTML dashboard, nudges after 3+ days without progress; [bighardperson/computer-science-skills-collection](https://github.com/bighardperson/computer-science-skills-collection)) and `last30days` (researches a topic across Reddit/X/web from the last 30 days for resource curation; [BrianRWagner/ai-marketing-claude-code-skills](https://github.com/BrianRWagner/ai-marketing-claude-code-skills), `last30days/SKILL.md`).
- `src/memory/` migration for `learning_tracks` (`track_id`, `name`, `priority_tier`, `milestone_state` — written by sync job + Learning Manager, read by Learning Manager).
- **Mirror Phase 4's rearrangement and consecutive-miss logic exactly** onto `learning_tracks` — same priority field, same batching logic, same consecutive-miss check, applied to learning tracks (e.g. system design, interview prep) instead of projects. This should be close enough to Phase 4's implementation that most of it is reuse, not a parallel rewrite — if it isn't, that's a sign Phase 4 wasn't built generically enough.
- `src/control-room/agents/learning-manager.md` + README.

**Data touched:** `learning_tracks` (new table), `miss_log` (shared with Task Manager's rearrangement, consecutive-miss detection reused across both).

**Credentials / env vars:** none new.

**Exit criteria:** two concurrent learning tracks get separate daily tasks, and a miss streak on either triggers the same retry-or-reduce prompt as Task Manager — verified by reusing Phase 4's miss-detection tests against `learning_tracks` rather than writing a parallel test suite from scratch.

### Phase 7 — Generic Manager + Hardening

**Build**

- `src/agents/task-manager/generic-manager/skills/intake-and-route/` — the smallest, dumbest skill in the system per the PRD: takes unstructured input (text or voice, via Discord/Telegram) and routes it to the right agent or the Notion inbox. No off-the-shelf skill fits (it's inherently Hasnain-specific) — build thin, resist the temptation to make this "smart" in v1 (explicit PRD non-goal: no fully autonomous Generic/Routine Manager logic in v1).
- Adopt the `hermes-agent-control-room` pattern fully now that all seven leaf agents exist: `src/control-room/agents/` should have one file per agent (role, skills, tools, status) for all seven, not just the ones added incrementally — do a pass to backfill any that were stubbed during earlier phases.
- Add `skill-tracker` (git-backed PR review for self-modifying skills) — this is the point where the skill count actually justifies the overhead; don't add it earlier just because it's in the tech stack list.
- Weekly Sunday full resync job (new issues Hasnain logged over the week) — an Inngest function, reusing `roadmap-sync`'s read logic rather than a new sync implementation.
- Voice-note ingestion: confirmed in-scope for v1 per the PRD's routing requirement ("Capture unstructured input (text or voice) ... route it to the right agent") — if this is still an open question by this phase (see PRD's Open Questions), resolve it before building rather than guessing.

**Data touched:** nothing new structurally — routes into existing tables (`idea_dump`, `tasks`, or hands off to an existing agent) per the Architecture Document's Component Responsibilities row for Generic/Routine Manager ("Reads: nothing structured; Writes: routes to Notion inbox or another agent").

**Credentials / env vars:** Telegram bot token if voice-note ingestion goes through Telegram rather than Discord (per PRD's "Discord/Telegram" phrasing — confirm which channel(s) are actually in scope before building both).

**Exit criteria:** an unstructured voice note gets classified and routed to the right agent without Hasnain specifying which one — the same kind of input that started this project in the first place (per the PRD's Overview & Problem Statement). Classification accuracy checked against a small labeled set, not just eyeballed on a handful of examples.

## Definition of Done / Testing Checklist

| Phase | Manual test | Automated test | Sign-off condition |
| --- | --- | --- | --- |
| 0. Foundation | Message the bot in Discord, get a response | Neon connection healthcheck | Both pass once; kill switch exercised once |
| 1. LinkedIn Agent | Request, review, approve a real draft | State machine unit tests (all transitions, including the 2-pass retry cap) | 7 days unattended, no crashes, no runaway retries |
| 2. Reddit Agent | Same, platform=reddit | Reuses Phase 1's suite against the new platform value | Same approval flow confirmed working, zero suite modifications needed |
| 3. Project Manager | Change a Notion task, confirm it's reflected in `tasks` | Test asserting a GitHub write attempt is rejected by the token itself | 10-minute sync latency confirmed; zero GitHub writes possible |
| 4. Rearrangement | Deliberately miss 3 days of tasks, confirm the retry-or-reduce prompt fires | Unit tests on the batching and priority logic | 7 consecutive days of on-time morning briefings |
| 5. Dev.to + Medium | One content piece produces all four platform formats correctly | Format-conversion tests per platform | Manual spot-check of formatting on all four |
| 6. Learning Manager | Two tracks running concurrently, one deliberately missed | Reuses Phase 4's miss-detection tests against `learning_tracks` | Same prompt behavior confirmed for learning as for tasks |
| 7. Generic Manager | Send a rambling voice note, confirm correct routing | Classification accuracy check against a small labeled set | Correctly routes without Hasnain specifying the target agent |

No phase is done on "the code runs" alone — every phase's sign-off condition includes either a multi-day unattended run or an explicit security-boundary test. See [Security.md](./Security.md)'s per-phase security checklist for the security-specific conditions layered on top of this table, and [Code Style Guide.md](./Code%20Style%20Guide.md) for the testing convention (access-boundary tests, not just happy-path) that phases 1, 3, and 6 lean on most heavily.
