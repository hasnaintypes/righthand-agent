# righthand-agent

A personal multi-agent AI assistant, built on Hermes Agent, that runs continuously in the background handling social media content production and personal task/learning management — nothing public ever goes out without approval.

One Discord channel, one point of contact: an orchestrator that relays to the right manager/agent and reports back. Separate deployment, separate memory, from any startup/team Hermes instance.

## Docs

Read these in order — each assumes the ones before it:

- [`docs/PRD.md`](docs/PRD.md) — what this is, goals/non-goals, agents & skills, tech stack, rollout plan
- [`docs/Architecture Document.md`](docs/Architecture%20Document.md) — components, data flow, data model, security boundaries
- [`docs/Build Roadmap.md`](docs/Build%20Roadmap.md) — build order, phase-by-phase tasks, exit criteria
- [`docs/Code Style Guide.md`](docs/Code%20Style%20Guide.md) — language, skill file shape, naming, testing convention
- [`docs/Security.md`](docs/Security.md) — credential scoping, secrets handling, kill switch

## Architecture (short version)

```
Hasnain (Discord) <--> Orchestrator (Hermes Agent)
                          ├── Social Media Manager --> LinkedIn / Reddit / Dev.to / Medium
                          └── Task Manager          --> Project Manager / Learning Manager / Generic Manager
                          -- shared memory --> Neon (Postgres + pgvector)
```

Every public-facing action requires a human approval step in Discord before it ships. No exceptions in v1.

## Repo layout

```
righthand-agent/
├── docs/                  # PRD, architecture, roadmap, style, security
├── src/
│   ├── control-room/      # agent registry, runbooks
│   ├── orchestrator/      # Hermes config, routing, Discord gateway
│   ├── agents/            # social-media-manager/, task-manager/ and their leaf agents
│   ├── memory/            # Neon schema + migrations
│   └── inngest/           # durable job functions (rearrangement, briefing, publish pipeline)
├── railway.json
└── .env.example
```

## Status

Phase 0 (Foundation) in progress — see [Build Roadmap.md](docs/Build%20Roadmap.md) for the full phase sequence and exit criteria.

## Stack

Python · Hermes Agent · Neon (Postgres + pgvector) · Discord · Notion · Railway · Inngest

## Setup

```bash
cp .env.example .env   # fill in real values, never commit this file
```

See [`docs/Security.md`](docs/Security.md) for how each credential should be scoped before it goes into Railway's environment variables.
