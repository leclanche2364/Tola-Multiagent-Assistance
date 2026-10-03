-- Daily Synthesis v1.2 schema migration
-- Generated: 2026-10-03
-- Target: supabase/migrations/20261003130000_daily_synthesis_schema.sql
-- NOTE: Real UNIQUE constraints on idempotency_key (not partial indexes).
-- PostgREST lesson: partial unique indexes do NOT enforce uniqueness for upserts;
-- a real UNIQUE constraint is required for idempotency_key conflict resolution.

-- ============================================================
-- handoffs table
-- ============================================================
create table if not exists handoffs (
    id uuid primary key default gen_random_uuid(),
    idempotency_key uuid not null,
    schema_version text not null,
    agent_id text not null,
    timestamp timestamptz not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    constraint chk_handoffs_schema_version check (schema_version in (
        'rhythm_capacity_handoff.v1',
        'scholar_handoff.v1',
        'growth_handoff.v1',
        'project_status_handoff.v1',
        'daily_command_brief.v1',
        'rhythm_schedule_conflict.v1',
        'daily_plan_to_rhythm.v1'
    ))
);

create unique index if not exists handoffs_idempotency_key_idx
    on handoffs (idempotency_key);

-- ============================================================
-- briefs table
-- ============================================================
create table if not exists briefs (
    id uuid primary key default gen_random_uuid(),
    idempotency_key uuid not null,
    schema_version text not null,
    agent_id text not null,
    timestamp timestamptz not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    constraint chk_briefs_schema_version check (schema_version in (
        'daily_command_brief.v1'
    ))
);

create unique index if not exists briefs_idempotency_key_idx
    on briefs (idempotency_key);

-- ============================================================
-- conflicts table
-- ============================================================
create table if not exists conflicts (
    id uuid primary key default gen_random_uuid(),
    idempotency_key uuid not null,
    schema_version text not null,
    agent_id text not null,
    timestamp timestamptz not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    constraint chk_conflicts_schema_version check (schema_version in (
        'rhythm_schedule_conflict.v1'
    ))
);

create unique index if not exists conflicts_idempotency_key_idx
    on conflicts (idempotency_key);

-- ============================================================
-- outcomes table
-- ============================================================
create table if not exists outcomes (
    id uuid primary key default gen_random_uuid(),
    idempotency_key uuid not null,
    schema_version text not null,
    agent_id text not null,
    timestamp timestamptz not null,
    payload jsonb not null,
    created_at timestamptz not null default now(),
    constraint chk_outcomes_schema_version check (schema_version in (
        'daily_plan_to_rhythm.v1',
        'growth_handoff.v1',
        'project_status_handoff.v1'
    ))
);

create unique index if not exists outcomes_idempotency_key_idx
    on outcomes (idempotency_key);
