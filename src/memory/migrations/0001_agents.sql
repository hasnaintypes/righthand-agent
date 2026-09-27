-- Phase 0: bootstrap table only. Every other table (tasks, drafts, miss_log, etc.)
-- is created in the migration for the phase that first needs it.
create extension if not exists vector;

create table if not exists agents (
    agent_id text primary key,
    role text not null,
    status text not null default 'inactive'
);
