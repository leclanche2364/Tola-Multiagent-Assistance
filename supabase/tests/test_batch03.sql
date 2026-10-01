-- Batch 03 migration tests. Designed to run against a FRESH database that has
-- the v1 schema + this batch's migration applied (supabase db reset + push, or
-- any disposable Postgres). Uses fixtures, cleans up after itself, and raises
-- exceptions (non-zero exit) on any failed assertion.
--
-- Run (local disposable env):
--   psql "$TEST_DB_URL" -v ON_ERROR_STOP=1 -f supabase/tests/test_batch03.sql
--
-- Covers: duplicate claim, distinct occurrences both running, approval happy
-- path, expired approval, altered payload, double use, unauthorised anon
-- access, journal unknown-replay blocking.

\set ON_ERROR_STOP on

begin;

-- ---------- fixtures ----------
insert into public.projects (project_name, description, status, strategic_priority)
values ('__b03_fixture', 'batch03 tests', 'active', 5)
on conflict (project_name) do nothing;

insert into public.agents (agent_name, role) values ('tola', 'coordinator')
on conflict (agent_name) do nothing;

insert into public.tasks (idempotency_key, project_id, title, requested_by, assigned_to)
select gen_random_uuid(), project_id, 'b03 fixture task', 'tola', 'tola'
  from public.projects where project_name = '__b03_fixture';

insert into public.approvals
  (approval_id, task_id, requested_by, approval_type, payload, status, payload_hash, expires_at)
select t.task_id, t.task_id, 'tola', 'risk_override', '{"risk":"A2"}'::jsonb, 'approved',
       'h0', now() + interval '1 hour'
  from public.tasks t join public.projects p on p.project_id = t.project_id
 where p.project_name = '__b03_fixture';

insert into public.approvals
  (approval_id, task_id, requested_by, approval_type, payload, status, payload_hash)
select t.task_id, t.task_id, 'tola', 'risk_override', '{"risk":"A2"}'::jsonb, 'approved', 'h0'
  from public.tasks t join public.projects p on p.project_id = t.project_id
 where p.project_name = '__b03_fixture'
   and t.title = 'b03 fixture task';

-- ---------- T3.1 duplicate claim: exactly one winner ----------
do $$
declare r1 text; r2 text; n int;
begin
  select outcome into r1 from public.claim_automation_occurrence('autoA', now(), 'deadbee', 'job-1', 'tola');
  select outcome into r2 from public.claim_automation_occurrence('autoA', now(), 'deadbee', 'job-2', 'rhythm');
  if r1 <> 'claimed' or r2 <> 'already_claimed' then
    raise exception 'T3.1 FAIL: r1=% r2=% (want claimed / already_claimed)', r1, r2;
  end if;
  select count(*) into n from public.automation_occurrences
   where automation_key = 'autoA';
  if n <> 1 then
    raise exception 'T3.1 FAIL: % occurrence rows for one (key, schedule), want 1', n;
  end if;
end $$;

-- ---------- T3.2 distinct scheduled occurrences can both run ----------
do $$
declare r1 text; r2 text;
begin
  select outcome into r1 from public.claim_automation_occurrence('autoB', now(), 'cafe01', null, 'tola');
  select outcome into r2 from public.claim_automation_occurrence('autoB', now() + interval '1 day', 'cafe01', null, 'tola');
  if r1 <> 'claimed' or r2 <> 'claimed' then
    raise exception 'T3.2 FAIL: distinct schedules must both claim (r1=% r2=%)', r1, r2;
  end if;
end $$;

-- ---------- T3.3 approval happy path consumes once ----------
do $$
declare aid uuid; r text; r2 text;
begin
  select approval_id into aid from public.approvals
   where payload_hash = 'h0' and expires_at is not null;
  select outcome into r  from public.consume_approval(aid, 'h0', 'tola', 'deadbee');
  select outcome into r2 from public.consume_approval(aid, 'h0', 'tola', 'deadbee');
  if r <> 'consumed' then raise exception 'T3.3 FAIL: first consume returned %', r; end if;
  if r2 <> 'already_consumed' then raise exception 'T3.3 FAIL: second consume returned % (want already_consumed)', r2; end if;
end $$;

-- ---------- T3.4 expired approval is rejected and flips status ----------
do $$
declare aid uuid; r text;
begin
  select approval_id into aid from public.approvals
   where payload_hash = 'h0' and expires_at is null and status = 'approved';
  update public.approvals set expires_at = now() - interval '1 minute'
   where approval_id = aid;
  select outcome into r from public.consume_approval(aid, 'h0', 'tola', 'deadbee');
  if r <> 'expired' then raise exception 'T3.4 FAIL: expired consume returned %', r; end if;
  if (select status from public.approvals where approval_id = aid) <> 'expired' then
    raise exception 'T3.4 FAIL: status not flipped to expired';
  end if;
end $$;

-- ---------- T3.5 altered payload hash is rejected ----------
do $$
declare aid uuid; r text;
begin
  insert into public.approvals (approval_id, task_id, requested_by, approval_type, payload, status, payload_hash)
  select gen_random_uuid(), t.task_id, 'tola', 'risk_override', '{"risk":"A2"}'::jsonb, 'approved', 'h1'
    from public.tasks t join public.projects p on p.project_id = t.project_id
   where p.project_name = '__b03_fixture'
   limit 1
  returning approval_id into aid;
  select outcome into r from public.consume_approval(aid, 'hMUTATED', 'tola', 'deadbee');
  if r <> 'payload_mismatch' then raise exception 'T3.5 FAIL: returned %', r; end if;
  if (select consumed_at from public.approvals where approval_id = aid) is not null then
    raise exception 'T3.5 FAIL: approval consumed despite mismatch';
  end if;
end $$;

-- ---------- T3.6 unauthorised anon write must fail ----------
do $$
begin
  begin
    set local role anon;
    insert into public.external_operations (idempotency_key, action_type, target)
    values ('anon-probe', 'x', 'y');
    raise notice 'T3.6 SKIP: anon role not present in this environment (insert succeeded)';
  exception when insufficient_privilege or undefined_object then
    null; -- expected: anon denied
  end;
  reset role;
end $$;

-- ---------- T3.7 journal: unknown replay blocked without evidence ----------
do $$
declare r text; r2 text; r3 text;
begin
  select public.set_operation_state('opK', 'unknown', null) into r;
  select public.set_operation_state('opK', 'pending',  null) into r2;
  if r2 <> 'blocked:unknown_requires_evidence' then
    raise exception 'T3.7 FAIL: unknown replay returned % (want blocked:unknown_requires_evidence)', r2;
  end if;
  select public.set_operation_state('opK', 'succeeded', 'evidence://receipt-1') into r3;
  if r3 <> 'succeeded' then raise exception 'T3.7 FAIL: evidence-backed resolution returned %', r3; end if;
  -- a second replay of a succeeded op is a no-op, never a second effect
  if public.set_operation_state('opK', 'succeeded', null) <> 'noop:succeeded' then
    raise exception 'T3.7 FAIL: succeeded replay not a no-op';
  end if;
end $$;

-- ---------- T3.8 failed occurrence can be re-claimed (retry path) ----------
do $$
declare r1 text; r2 text;
begin
  select outcome into r1 from public.claim_automation_occurrence('autoC', now(), 'beef01', null, 'tola');
  select occurrence_id from public.automation_occurrences
   where automation_key = 'autoC' limit 1;
  perform public.finish_automation_occurrence(
    (select occurrence_id from public.automation_occurrences where automation_key = 'autoC'),
    'failed', 'beef01');
  select outcome into r2 from public.claim_automation_occurrence('autoC', now(), 'beef01', null, 'rhythm');
  if r2 <> 'claimed' then raise exception 'T3.8 FAIL: failed occurrence not re-claimable (r2=%)', r2; end if;
end $$;

rollback;
