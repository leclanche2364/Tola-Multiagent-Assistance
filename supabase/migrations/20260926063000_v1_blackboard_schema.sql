-- V1 Blackboard schema — four-agent system
-- Derived from openclaw_four_agent_system_v1_1.md §9 (Supabase = authoritative organisational state)
-- Core rules: UUID PKs, idempotency keys, optimistic-concurrency version columns,
-- constrained status/type fields, timestamps, indexes for active-task and agent/status lookups.

create extension if not exists "pgcrypto";

-- ============ 1. agents ============
create table agents (
  agent_id        uuid primary key default gen_random_uuid(),
  agent_name      text not null unique check (agent_name in ('tola','rhythm','growth','scholar')),
  role            text not null,
  status          text not null default 'active' check (status in ('active','paused','retired')),
  config          jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- ============ 2. projects ============
create table projects (
  project_id      uuid primary key default gen_random_uuid(),
  project_name    text not null,
  description     text,
  status          text not null default 'active' check (status in ('active','paused','completed','archived')),
  strategic_priority integer not null default 5 check (strategic_priority between 1 and 10),
  owner_agent_id  uuid references agents(agent_id),
  version         integer not null default 1,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create unique index projects_name_uniq on projects (project_name);

-- ============ 3. goals ============
create table goals (
  goal_id         uuid primary key default gen_random_uuid(),
  project_id      uuid not null references projects(project_id),
  goal_name       text not null,
  description     text,
  status          text not null default 'open' check (status in ('open','in_progress','blocked','achieved','dropped')),
  owner_agent_id  uuid references agents(agent_id),
  due_date        date,
  version         integer not null default 1,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index goals_project_status_idx on goals (project_id, status);

-- ============ 4. tasks ============
create table tasks (
  task_id         uuid primary key default gen_random_uuid(),
  idempotency_key uuid not null unique,
  parent_task_id  uuid references tasks(task_id),
  project_id      uuid references projects(project_id),
  goal_id         uuid references goals(goal_id),
  title           text not null,
  instructions    text,
  context_refs    jsonb not null default '[]'::jsonb,
  required_output text,
  success_criteria jsonb not null default '[]'::jsonb,
  requested_by    text not null references agents(agent_name),
  assigned_to     text not null references agents(agent_name),
  status          text not null default 'pending' check (status in ('pending','in_progress','blocked','needs_approval','completed','failed','cancelled')),
  risk_class      text not null default 'A0' check (risk_class in ('A0','A1','A2','A3')),
  model_route     text check (model_route in ('R0','R1','R2','R3','R4')),
  allowed_tools   jsonb not null default '[]'::jsonb,
  timeout_seconds integer,
  deadline        timestamptz,
  version         integer not null default 1,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index tasks_status_assigned_idx on tasks (assigned_to, status);
create index tasks_status_active_idx on tasks (status) where status in ('pending','in_progress','blocked','needs_approval');
create index tasks_project_idx on tasks (project_id);

-- ============ 5. task_dependencies ============
create table task_dependencies (
  dependency_id   uuid primary key default gen_random_uuid(),
  task_id         uuid not null references tasks(task_id) on delete cascade,
  depends_on_task_id uuid not null references tasks(task_id) on delete cascade,
  created_at      timestamptz not null default now(),
  unique (task_id, depends_on_task_id),
  check (task_id <> depends_on_task_id)
);

-- ============ 6. task_runs ============
create table task_runs (
  run_id          uuid primary key default gen_random_uuid(),
  task_id         uuid not null references tasks(task_id) on delete cascade,
  idempotency_key uuid not null unique,
  attempt         integer not null default 1,
  status          text not null default 'running' check (status in ('running','success','partial','blocked','needs_approval','failed')),
  summary         text,
  outputs         jsonb not null default '[]'::jsonb,
  evidence_refs   jsonb not null default '[]'::jsonb,
  tool_actions    jsonb not null default '[]'::jsonb,
  blockers        jsonb not null default '[]'::jsonb,
  verification    jsonb not null default '{}'::jsonb,
  started_at      timestamptz not null default now(),
  finished_at     timestamptz
);
create index task_runs_task_idx on task_runs (task_id, started_at);

-- ============ 7. decisions ============
create table decisions (
  decision_id     uuid primary key default gen_random_uuid(),
  task_id         uuid references tasks(task_id),
  made_by         text not null references agents(agent_name),
  decision_type   text not null,
  rationale       text,
  payload         jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now()
);
create index decisions_task_idx on decisions (task_id);

-- ============ 8. approvals ============
create table approvals (
  approval_id     uuid primary key default gen_random_uuid(),
  task_id         uuid references tasks(task_id),
  requested_by    text not null references agents(agent_name),
  approval_type   text not null,
  payload         jsonb not null default '{}'::jsonb,
  status          text not null default 'pending' check (status in ('pending','approved','rejected','expired')),
  decided_by      text,
  decided_at      timestamptz,
  created_at      timestamptz not null default now()
);
create index approvals_pending_idx on approvals (status) where status = 'pending';

-- ============ 9. metrics ============
create table metrics (
  metric_id       uuid primary key default gen_random_uuid(),
  project_id      uuid references projects(project_id),
  goal_id         uuid references goals(goal_id),
  metric_name     text not null,
  metric_value    numeric not null,
  unit            text,
  source          text,
  snapshot_at     timestamptz not null default now(),
  idempotency_key uuid unique
);
create index metrics_name_time_idx on metrics (metric_name, snapshot_at desc);

-- ============ 10. schedule_constraints ============
create table schedule_constraints (
  constraint_id   uuid primary key default gen_random_uuid(),
  agent_name      text references agents(agent_name),
  constraint_type text not null check (constraint_type in ('shift','block','recurring','one_off','blackout')),
  title           text not null,
  starts_at       timestamptz not null,
  ends_at         timestamptz not null,
  recurrence      jsonb not null default '{}'::jsonb,
  source          text not null default 'manual' check (source in ('manual','calendar','user','agent')),
  version         integer not null default 1,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  check (ends_at > starts_at)
);
create index schedule_constraints_window_idx on schedule_constraints (starts_at, ends_at);

-- ============ 11. agent_events ============
create table agent_events (
  event_id        uuid primary key default gen_random_uuid(),
  agent_name      text not null references agents(agent_name),
  task_id         uuid references tasks(task_id),
  event_type      text not null,
  payload         jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now()
);
create index agent_events_agent_time_idx on agent_events (agent_name, created_at desc);
create index agent_events_task_idx on agent_events (task_id);

-- ============ 12. model_runs ============
create table model_runs (
  model_run_id    uuid primary key default gen_random_uuid(),
  task_run_id     uuid references task_runs(run_id) on delete set null,
  model_route     text not null check (model_route in ('R0','R1','R2','R3','R4')),
  model_id        text,
  input_tokens    integer,
  output_tokens   integer,
  cost_usd        numeric(12,6),
  latency_ms      integer,
  status          text not null default 'completed' check (status in ('completed','failed','timeout')),
  created_at      timestamptz not null default now()
);
create index model_runs_route_idx on model_runs (model_route, created_at desc);

-- ============ 13. external_refs ============
create table external_refs (
  ref_id          uuid primary key default gen_random_uuid(),
  entity_type     text not null check (entity_type in ('project','goal','task','task_run','decision','approval','metric','schedule_constraint')),
  entity_id       uuid not null,
  ref_kind        text not null,
  ref_value       text not null,
  created_at      timestamptz not null default now(),
  unique (entity_type, entity_id, ref_kind, ref_value)
);
create index external_refs_entity_idx on external_refs (entity_type, entity_id);

-- ============ 14. skill_registry ============
create table skill_registry (
  skill_id          uuid primary key default gen_random_uuid(),
  skill_name        text not null,
  owner_agent_id    uuid references agents(agent_id),
  origin_type       text not null check (origin_type in ('native','external','generated')),
  source_repository text,
  source_commit     text,
  source_version    text,
  licence           text,
  local_revision    integer not null default 1,
  status            text not null default 'quarantined' check (status in ('quarantined','reviewing','testing','approved','active','rejected','retired')),
  approved_by       text,
  approved_at       timestamptz,
  content_hash      text not null,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (skill_name, local_revision)
);
create index skill_registry_status_idx on skill_registry (status);

-- ============ 15. skill_evaluations ============
create table skill_evaluations (
  evaluation_id          uuid primary key default gen_random_uuid(),
  skill_id               uuid not null references skill_registry(skill_id),
  agent_id               uuid references agents(agent_id),
  baseline_revision      integer not null,
  candidate_revision     integer not null,
  fixture_set            text,
  task_success_before    numeric,
  task_success_after     numeric,
  boundary_violations    integer,
  trigger_precision      numeric,
  trigger_recall         numeric,
  avg_tokens_before      integer,
  avg_tokens_after       integer,
  avg_latency_before     integer,
  avg_latency_after      integer,
  human_correction_before numeric,
  human_correction_after  numeric,
  decision               text not null check (decision in ('promote','reject','iterate','pending')),
  notes                  text,
  created_at             timestamptz not null default now()
);
create index skill_evaluations_skill_idx on skill_evaluations (skill_id, created_at desc);

-- ============ updated_at triggers ============
create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_agents_updated before update on agents for each row execute function set_updated_at();
create trigger trg_projects_updated before update on projects for each row execute function set_updated_at();
create trigger trg_goals_updated before update on goals for each row execute function set_updated_at();
create trigger trg_tasks_updated before update on tasks for each row execute function set_updated_at();
create trigger trg_schedule_updated before update on schedule_constraints for each row execute function set_updated_at();
create trigger trg_skills_updated before update on skill_registry for each row execute function set_updated_at();

-- ============ seed agents ============
insert into agents (agent_name, role) values
  ('tola',    'Chief of Staff — orchestration, routing, verification'),
  ('rhythm',  'Life planning and scheduling'),
  ('growth',  'Growth intelligence'),
  ('scholar', 'Research and learning')
on conflict (agent_name) do nothing;
