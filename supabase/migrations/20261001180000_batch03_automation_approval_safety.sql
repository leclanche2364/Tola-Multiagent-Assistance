-- Batch 03: durable automation occurrences, single-use approvals, external-operation journal.
-- Never edits the applied v1 migration; this file only ADDs objects.
-- Style follows 20260926063000_v1_blackboard_schema.sql (uuid PKs, CHECK enums, timestamptz).

-- ------------------------------------------------------------------
-- 1. Automation occurrences
-- ------------------------------------------------------------------
create table if not exists public.automation_occurrences (
  occurrence_id   uuid primary key default gen_random_uuid(),
  automation_key  text        not null,
  scheduled_for   timestamptz not null,
  openclaw_job_id text,
  release_sha     text,
  claimed_by      text,
  claimed_at      timestamptz,
  status          text        not null default 'pending'
                  check (status in ('pending','claimed','succeeded','failed','skipped')),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  -- one effect per scheduled occurrence of an automation
  unique (automation_key, scheduled_for)
);
create index if not exists automation_occurrences_pending_idx
  on public.automation_occurrences (scheduled_for)
  where status = 'pending';

-- Transactional claim: concurrent callers race on the row lock; exactly one
-- winner transitions pending -> claimed, the rest get 'already_claimed'.
create or replace function public.claim_automation_occurrence(
  p_automation_key text,
  p_scheduled_for  timestamptz,
  p_release_sha    text,
  p_openclaw_job_id text,
  p_claimed_by     text
) returns table (occurrence_id uuid, outcome text)
language plpgsql
security definer
set search_path = public as $$
declare
  v_occurrence_id uuid;
begin
  -- upsert the occurrence row itself (idempotent on the uniqueness rule)
  insert into public.automation_occurrences
    (automation_key, scheduled_for, release_sha, openclaw_job_id)
  values (p_automation_key, p_scheduled_for, p_release_sha, p_openclaw_job_id)
  on conflict (automation_key, scheduled_for) do update
    set updated_at = now()
  returning automation_occurrences.occurrence_id into v_occurrence_id;

  update public.automation_occurrences
     set status = 'claimed', claimed_by = p_claimed_by,
         claimed_at = now(), updated_at = now()
   where occurrence_id = v_occurrence_id
     and status in ('pending','failed')     -- failed occurrences may be re-claimed
   returning occurrence_id into v_occurrence_id;

  if v_occurrence_id is not null then
    return query select v_occurrence_id, 'claimed'::text;
  else
    -- someone else already holds it or it finished; report, do not double-run
    select occurrence_id into v_occurrence_id
      from public.automation_occurrences
     where automation_key = p_automation_key and scheduled_for = p_scheduled_for;
    return query select v_occurrence_id, 'already_claimed'::text;
  end if;
end $$;

-- mark the outcome after execution (idempotent per state transition rules)
create or replace function public.finish_automation_occurrence(
  p_occurrence_id uuid,
  p_status        text,
  p_release_sha   text
) returns void
language plpgsql
security definer
set search_path = public as $$
begin
  if p_status not in ('succeeded','failed','skipped') then
    raise exception 'invalid completion status %', p_status;
  end if;
  update public.automation_occurrences
     set status = p_status, release_sha = coalesce(p_release_sha, release_sha),
         updated_at = now()
   where occurrence_id = p_occurrence_id
     and status in ('claimed','failed','succeeded');
end $$;

-- ------------------------------------------------------------------
-- 2. Approvals: extend with single-use consumption semantics
-- ------------------------------------------------------------------
alter table public.approvals
  add column if not exists action_type  text,
  add column if not exists payload_hash text,
  add column if not exists expires_at   timestamptz,
  add column if not exists consumed_at  timestamptz,
  add column if not exists consumed_by  text;

-- Consume exactly once: blocks on the row, validates approval state, expiry,
-- canonical payload hash and requester, then stamps the single-use marker.
-- A second caller finds consumed_at not null and is rejected.
create or replace function public.consume_approval(
  p_approval_id  uuid,
  p_payload_hash text,
  p_consumer     text,
  p_release_sha  text
) returns table (outcome text)
language plpgsql
security definer
set search_path = public as $$
declare
  v record;
begin
  select * into v from public.approvals
   where approval_id = p_approval_id
   for update;                       -- serialize concurrent consumers

  if not found then
    return query select 'not_found'::text;
  elsif v.consumed_at is not null then
    return query select 'already_consumed'::text;
  elsif v.status <> 'approved' then
    return query select format('not_approved:%s', v.status)::text;
  elsif v.expires_at is not null and v.expires_at < now() then
    update public.approvals set status = 'expired' where approval_id = p_approval_id;
    return query select 'expired'::text;
  elsif p_payload_hash is distinct from v.payload_hash then
    return query select 'payload_mismatch'::text;
  else
    update public.approvals
       set consumed_at = now(), consumed_by = p_consumer
     where approval_id = p_approval_id;
    insert into public.agent_events (agent_name, event_type, payload)
    values (p_consumer, 'approval.consumed',
            jsonb_build_object('approval_id', p_approval_id, 'release_sha', p_release_sha,
                               'action_type', v.action_type, 'payload_hash', v.payload_hash));
    return query select 'consumed'::text;
  end if;
end $$;

-- ------------------------------------------------------------------
-- 3. External-operation journal
-- ------------------------------------------------------------------
create table if not exists public.external_operations (
  op_id           uuid primary key default gen_random_uuid(),
  idempotency_key text        not null unique,   -- stable key drives safe retry
  action_type     text        not null,
  target          text        not null,
  state           text        not null default 'pending'
                  check (state in ('pending','succeeded','failed','unknown')),
  evidence_ref    text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- Transition rules: 'unknown' must never be blindly replayed; the caller must
-- resolve it (evidence) before any successor operation for the same key.
create or replace function public.set_operation_state(
  p_idempotency_key text,
  p_state           text,
  p_evidence_ref    text
) returns text
language plpgsql
security definer
set search_path = public as $$
declare
  v_current text;
begin
  if p_state not in ('pending','succeeded','failed','unknown') then
    raise exception 'invalid state %', p_state;
  end if;

  select state into v_current from public.external_operations
   where idempotency_key = p_idempotency_key
   for update;

  if v_current is null then
    insert into public.external_operations (idempotency_key, action_type, target, state, evidence_ref)
    values (p_idempotency_key, 'unspecified', 'unspecified', p_state, p_evidence_ref);
    return p_state;
  end if;

  -- succeeded/unknown are terminal without explicit evidence-backed resolution
  if v_current in ('succeeded') and p_state in ('pending','succeeded') then
    return 'noop:' || v_current;       -- already done; a retry is a no-op
  end if;
  if v_current = 'unknown' and p_state <> 'unknown' and p_evidence_ref is null then
    return 'blocked:unknown_requires_evidence';
  end if;

  update public.external_operations
     set state = p_state, evidence_ref = coalesce(p_evidence_ref, evidence_ref),
         updated_at = now()
   where idempotency_key = p_idempotency_key;
  return p_state;
end $$;

-- ------------------------------------------------------------------
-- 4. Access control: RLS + narrow RPC grants
-- ------------------------------------------------------------------
-- Agents never receive generic table-write authority. RLS enabled with NO
-- policies = deny-all for anon/authenticated; only service_role (which
-- bypasses RLS) and the SECURITY DEFINER RPCs below can mutate state.
alter table public.automation_occurrences enable row level security;
alter table public.approvals               enable row level security;
alter table public.external_operations     enable row level security;

-- Supabase manages the anon/authenticated/service_role roles; on a bare
-- Postgres instance (local disposable test DBs) they don't exist. Create
-- them as NOLOGIN stubs if missing so the migration is self-contained.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin;
  end if;
end $$;

revoke all on public.automation_occurrences from anon, authenticated;
revoke all on public.approvals               from anon, authenticated;
revoke all on public.external_operations     from anon, authenticated;

revoke all on function public.claim_automation_occurrence(text, timestamptz, text, text, text)  from anon;
revoke all on function public.finish_automation_occurrence(uuid, text, text)                    from anon;
revoke all on function public.consume_approval(uuid, text, text, text)                          from anon;
revoke all on function public.set_operation_state(text, text, text)                             from anon;
grant execute on function public.claim_automation_occurrence(text, timestamptz, text, text, text) to service_role;
grant execute on function public.finish_automation_occurrence(uuid, text, text)                   to service_role;
grant execute on function public.consume_approval(uuid, text, text, text)                         to service_role;
grant execute on function public.set_operation_state(text, text, text)                            to service_role;
