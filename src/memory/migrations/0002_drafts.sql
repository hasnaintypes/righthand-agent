-- Phase 1: drafts table backing the validation state machine
-- (Drafted -> Checking -> Passed | Revising -> Checking -> Escalated).
-- Checking may route to Revising only once; the second flag always
-- routes to Escalated -- enforced in code, not by this schema.
create table if not exists drafts (
    draft_id text primary key,
    platform text not null,
    content text not null,
    state text not null default 'drafted',
    flags text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
