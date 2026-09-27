# righthand-agent — Code Style & Conventions

Sep 27, 2026 · @Hasnain

Companion to the [PRD](./PRD.md) and [Architecture Document](./Architecture%20Document.md) — this is *how* code gets written, not *what* gets built. Split out from the Build Roadmap so it can be pointed to (and enforced by a pre-commit hook / linter config) without wading through phase sequencing.

## Language

Python throughout — matches Hermes Agent itself and every sourced skill (linkedin-skills, reddit-poster, goal-tracker, etc.). No second language for "just this one script" — a bash cron wrapper or a Node publishing tool would be a second toolchain to maintain for no real gain.

## Skill files

Every skill is a folder with a `SKILL.md` (frontmatter: `name`, `description`, trigger conditions) plus implementation — the same shape as the sourced skills, not a new convention. Applies equally to:

- **Installed skills** (linkedin-post-writer, reddit-poster, goal-tracker, etc.) — used as-is from their source repos (see PRD's Agents & Skills tables for the list and source links).
- **Custom skills built in-house** — `roadmap-sync`, `intake-and-route`, `context-switch-guard`. These follow the identical `SKILL.md` shape so they're indistinguishable from installed ones once the system is running. No "custom skill format" fork.

## Formatting & linting

- `black` for formatting, `ruff` for linting.
- Versions pinned in `pyproject.toml` — no floating versions for tooling that reformats or fails CI.
- Both run in a **pre-commit hook**, not just CI. Catching a formatting issue at commit time is one keystroke; catching it in CI is a round trip.

## Type hints

Required on every tool function signature — this is the actual interface boundary between the LLM and the system. An untyped signature turns a bad tool call into a runtime error deep in agent logic instead of a clear validation failure at the boundary, which matters more here than in typical application code because the caller is a model, not a human who read the docstring.

Not required on every internal helper — only where the LLM (via Hermes tool-calling) is the caller.

## Naming

| What | Convention | Example |
| --- | --- | --- |
| Files & functions | `snake_case` | `roadmap_sync.py`, `check_draft_state()` |
| Skill folder names | `kebab-case` | `linkedin-post-writer/`, `roadmap-sync/` (matches every sourced skill's own convention) |
| `platform` / `agent_id` enum values | lowercase | `linkedin`, `reddit`, `devto`, `medium` — matches Neon column values exactly, no casing bugs at the query layer (see Architecture Document's Data Model: `drafts.platform`, `memory_chunks.agent_id`) |

## Commits

Conventional Commits, scoped by agent:

```
feat(linkedin-agent): add humanizer retry bound
fix(project-manager): correct read-only token scope
```

The scope matches the Control Room's per-agent registry files (`control-room/agents/<agent>.md`), so a commit log and an agent registry entry can be cross-referenced when debugging "what changed and why" months later.

## Testing

Every custom skill ships with **at least one test that exercises its access boundary, not just its happy path**. This is the single most important testing convention in this repo, because the boundaries themselves are security properties (see [Security.md](./Security.md)), not just features:

- Project Manager's suite must include a test that *asserts a GitHub write attempt fails* — not just that reads succeed.
- Any skill touching a scoped credential (GitHub PAT, Notion integration token) needs the negative case tested, not just the positive one.

Happy-path tests are still expected where logic actually branches (state machine transitions, rearrangement/batching logic) — see the Build Roadmap's Definition of Done table for which automated tests gate which phase.

## Per-agent README

Each agent folder (`agents/<manager>/<agent>/README.md`) carries a short README stating:

1. Its scope — what it's for
2. Its tools — what it can call
3. What it explicitly **does not do** — mirroring the Architecture Document's Component Responsibilities table's "Never does" column

The point of duplicating the "never does" fact in two places (Architecture doc + per-agent README) is that the README is what a contributor — including future-Hasnain — actually opens when touching that agent's code. A boundary recorded only in a separate architecture doc is a boundary nobody reads at the moment they'd break it.
