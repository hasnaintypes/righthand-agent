# Personal AI Assistant — Architecture Document

Sep 27, 2026 · @Hasnain

## System Overview

One Hermes Agent process, three levels of delegation, one human contact point (Discord), and one shared memory store (Neon). External systems are read from, never written to except where explicitly noted.

```mermaid
flowchart TD
    H[Hasnain] <-->|single channel| O[Orchestrator<br/>Hermes Agent]
    O --> SMM[Social Media Manager]
    O --> TM[Task Manager]
    SMM --> LI[LinkedIn Agent]
    SMM --> RD[Reddit Agent]
    SMM --> DT[Dev.to Agent]
    SMM --> MD[Medium Agent]
    TM --> PM[Project Manager]
    TM --> LM[Learning Manager]
    TM --> GM[Generic Manager]
    O -.memory.-> NEON[(Neon + pgvector)]
    PM -.read only.-> GH[(GitHub)]
    PM <-.read/write.-> NO[(Notion)]
    TM -.schedule.-> ING[Inngest]
```

The orchestrator is the only component with a human-facing surface. Every manager and leaf agent is reachable only through it — there is no path for Hasnain to message a sub-agent directly, and no path for a sub-agent to message Hasnain except by routing through the orchestrator's Discord channel.

## Channel Topology

**Added 2026-09-29**, after Phase 1 exposed a gap: the first LinkedIn approval loop had Hasnain invoking the LinkedIn agent's skill directly and approving in that same conversation — leaf-agent-direct, not orchestrator-mediated, defeating the PRD's single-point-of-contact design. **This is a standing rule for every leaf agent in the system, not a LinkedIn-specific fix** — LinkedIn is just the first one built, and so the first one this rule applies to. Every leaf agent added in Phases 2–7 (Reddit, Dev.to, Medium, Project Manager, Learning Manager, Generic Manager) follows the exact same pattern described here; none of them get bespoke treatment.

```mermaid
flowchart LR
    H[Hasnain] <-->|DM: the only<br/>interaction surface| O[Orchestrator]
    O -.narrates progress.-> LC["#&lt;agent&gt;-agent channel<br/>(read-only for Hasnain)"]
    O -.delegate_task.-> LA[Any leaf agent's logic]
    LA -.result.-> O
    O -->|clarify approval card| H
```

**One Hermes profile, one Discord bot token, multiple channels — not one bot per agent.** Hermes profiles are fully independent ("islands" — separate config, memory, state) and *"a bot can only belong to one profile"*: giving every leaf agent its own Discord identity would mean creating a separate Discord application/bot token per agent (seven of them, eventually), inviting each one, and managing seven separate deployments. That's unnecessary — the requirement is **visibility**, not a separate identity, so one bot operating in multiple channels of the same server covers all seven:

- **Main channel (DM).** Hasnain's only interaction surface, for every agent. All requests go here; all approvals come back here, regardless of which leaf agent did the work.
- **One dedicated channel per leaf agent**, created as each one goes live: `#linkedin-agent` (Phase 1), then `#reddit-agent` (Phase 2), `#project-manager` (Phase 3), `#devto-agent` / `#medium-agent` (Phase 5), `#learning-manager` (Phase 6), `#generic-manager` (Phase 7). The orchestrator posts narration into the relevant channel as it delegates work — "drafting...", "audit flagged X, revising...", "clean, bringing it to you" — using the same Discord bot's ability to post to any channel it's a member of. Hasnain can read any of these any time; he never needs to post in them, and nothing in them ever asks him anything.
- **The relay mechanism is `delegate_task`**, Hermes's built-in subagent tool (supports `role="orchestrator"` on the parent, scoped child context) — not a second profile, not a second bot, and the same mechanism for every agent. The orchestrator delegates the actual work (drafting, syncing, tracking — whatever that leaf agent does), relays progress to its channel, and when the child returns a result, the orchestrator itself calls `clarify` in the main channel. **The hard rule, for every leaf agent without exception:** `clarify` is only ever called from the orchestrator's own turn in the main channel — a leaf-agent delegation never calls `clarify` directly, even though it technically could. This is a prompt-level rule for now (enforced by each leaf agent's `SKILL.md` instructions and the orchestrator's own system prompt), not something Hermes blocks structurally — worth revisiting if a future leaf agent's skill ever gets invoked outside orchestrator delegation.

## Deployment Topology

```mermaid
flowchart LR
    subgraph Railway
        HERMES[Hermes container<br/>+ persistent volume]
    end
    subgraph Inngest
        FN1[rearrangement fn]
        FN2[briefing fn]
        FN3[publish-pipeline fn]
    end
    DISCORD[Discord] <--> HERMES
    HERMES <--> NEON[(Neon Postgres<br/>+ pgvector)]
    HERMES <--> NOTION[(Notion)]
    HERMES -->|read only| GITHUB[(GitHub)]
    CRON[Railway native cron] -->|wake| HERMES
    HERMES -->|events| FN1
    FN1 --> FN2
    HERMES -->|events| FN3
    FN1 & FN2 & FN3 <--> NEON
```

One Railway service runs the Hermes container with a persistent volume (sessions, skill state, config survive restarts). Neon is external to Railway — connected by connection string, not a Railway add-on. Railway's native cron handles simple wake-up triggers (the 5–10 min Notion/GitHub poll); Inngest handles the three jobs that need retries and step-level observability (rearrangement, briefing generation, the multi-platform publish pipeline). Inngest functions call back into the same Hermes process rather than duplicating agent logic outside it.

## Data Flow: Daily Operating Loop

```mermaid
sequenceDiagram
    participant Cron as Railway Cron
    participant Sync as Sync job
    participant Neon
    participant Ing as Inngest
    participant TM as Task Manager
    participant O as Orchestrator
    participant H as Hasnain (Discord)

    loop every 5-10 min
        Cron->>Sync: wake
        Sync->>Neon: write latest Notion + GitHub state
    end

    Note over Ing: midnight
    Ing->>TM: run rearrangement
    TM->>Neon: read tasks, priorities, roadmap
    TM->>TM: batch by project, re-slot missed tasks
    TM->>Neon: write updated plan

    Ing->>TM: build morning briefing
    TM->>Neon: read updated plan
    TM->>O: hand off briefing
    O->>H: post to-do list (before 9am)

    alt 2-3 day miss streak detected
        TM->>O: flag pattern + options
        O->>H: ask - retry full load or reduce?
        H->>O: decision
        O->>TM: apply decision
    end
```

## Data Flow: Content Approval

```mermaid
sequenceDiagram
    participant SMM as Social Media Manager
    participant LI as LinkedIn Agent
    participant Neon
    participant O as Orchestrator
    participant H as Hasnain (Discord)

    SMM->>LI: start (sequential - LinkedIn first)
    LI->>Neon: read voice/style context
    LI->>LI: draft post
    LI->>LI: audit + humanize check
    alt check fails
        LI->>LI: revise once, re-check
        alt still fails
            LI->>O: escalate with flags
            O->>H: draft + flags, needs a human call
        end
    end
    LI->>O: draft ready
    O->>H: post for approval
    H->>O: approve / reject / edit
    O->>SMM: result
    SMM->>SMM: proceed to next platform (Reddit)
```

Hasnain publishes manually for now (LinkedIn, Reddit, dev.to, Medium publishing tools are backlogged per the PRD) — this flow ends at approval, not at publish. The link/draft is what reaches Discord; the actual post is his click.

## State Machine: Validation & Bounded Retry

```mermaid
stateDiagram-v2
    [*] --> Drafted
    Drafted --> Checking
    Checking --> Passed: audit ok
    Checking --> Revising: audit flags issue (pass 1)
    Revising --> Checking
    Checking --> Escalated: audit flags issue (pass 2)
    Passed --> AwaitingApproval
    Escalated --> AwaitingApproval: sent with flags attached
    AwaitingApproval --> Approved: Hasnain approves
    AwaitingApproval --> Rejected: Hasnain rejects
    Rejected --> [*]: reason logged as feedback, not a retry trigger
    Approved --> [*]
```

The hard rule that prevents an infinite loop: **Checking can only route to Revising once.** The second flag always routes to Escalated, never back to Revising. This caps every draft at exactly two automated passes before a human sees it, independent of how many issues the audit step finds.

## Data Model (Neon)

| Table | Key columns | Written by | Read by |
| --- | --- | --- | --- |
| `agents` | agent\_id, role, status | Orchestrator (bootstrap only) | All |
| `memory_chunks` | agent\_id (scope), content, embedding (pgvector) | Each leaf agent, on its own scope | All (similarity search), scoped by agent\_id so context doesn't bleed |
| `tasks` | task\_id, project\_id, notion\_id, github\_issue\_id (nullable), status, priority, due\_date | Sync job (from Notion/GitHub reads), rearrangement job | Task Manager, Project Manager |
| `projects` | project\_id, name, priority\_tier, roadmap\_ref | Sync job (from Notion) | Task Manager, rearrangement logic |
| `learning_tracks` | track\_id, name, priority\_tier, milestone\_state | Sync job, Learning Manager | Learning Manager |
| `drafts` | draft\_id, platform, content, state (matches the state machine), flags | Social Media leaf agents | Social Media Manager, Orchestrator |
| `miss_log` | date, tasks\_missed, consecutive\_count | Rearrangement job | Task Manager, Learning Manager (consecutive-miss detection) |
| `idea_dump` | idea\_id, description, status, overlap\_flag | Orchestrator (on intake) | Task Manager |

`memory_chunks.agent_id` scoping is the mechanism that keeps LinkedIn drafts, GitHub context, and learning notes from cross-contaminating in similarity search — every query filters on it before ranking by embedding distance.

## Component Responsibilities

| Component | Trigger | Reads | Writes | Never does |
| --- | --- | --- | --- | --- |
| Orchestrator | Discord message; scheduled hand-off from Task/Social Media Manager | Nothing directly — always via a manager | Discord channel | Draft content, decide task priority |
| Social Media Manager | Daily content window (Inngest) | `memory_chunks` (voice/style) | `drafts` | Publish without approval |
| LinkedIn / Reddit / Dev.to / Medium Agent | Called by Social Media Manager, one at a time | Platform-specific style context | Its own `drafts` row | Act out of sequence with its siblings |
| Task Manager | Sync poll, midnight rearrangement, briefing job | `tasks`, `projects`, `miss_log` | `tasks` (rearranged plan), `miss_log` | Create or assign GitHub issues |
| Project Manager | Called by Task Manager | GitHub (read-only), Notion | Notion (status/priority fields it owns) | Write to GitHub in any form |
| Learning Manager | Same cadence as Task Manager | `learning_tracks`, `miss_log` | `learning_tracks` | Auto-reduce workload without asking |
| Generic / Routine Manager | Ad hoc, on unstructured input | Nothing structured | Routes to Notion inbox or another agent | Attempt to classify beyond simple routing (v1 scope) |

## Security & Access Boundaries

| Boundary | Scope | Enforced by |
| --- | --- | --- |
| GitHub | Read-only, scoped repos only | Token scoped to read at the provider level, not just by convention — the credential itself cannot write |
| Notion | Read/write, but only the fields the agent owns (status, priority sync) | Notion integration permissions per database |
| Discord | One channel; Hasnain is the only authorized user the orchestrator acts on | Hermes access control config |
| Publishing (LinkedIn/Reddit/dev.to/Medium) | No credentials configured in v1 — backlogged | Not built, not a permission to revoke later |
| Neon | Single database, agent-scoped rows via `agent_id`, no cross-tenant concern since this is single-user | Application-level scoping, not row-level security (not needed at this scale) |
| Startup's Hermes instance | Fully separate deployment, separate Neon database, no shared credentials or memory | Physical separation, not a config flag |

The GitHub read-only boundary is the one worth being strict about at the infrastructure level rather than trusting the skill's prompt: the token itself should be a read-only PAT or a GitHub App installation scoped to `contents:read` and `issues:read`, so a bug in a skill can't accidentally write even if the skill's logic tries to.
