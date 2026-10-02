-- Batch 10: automation run claims and occurrence extensions.
-- Extends the automation_occurrences table from Batch 03 with
-- release_sha and openclaw_job_id tracking, plus a staging view
-- for offline test fixture usage.
-- This migration is repo-only and never applied to a live DB.

-- ------------------------------------------------------------------
-- 1. Add claim tracking columns to automation_occurrences
-- ------------------------------------------------------------------
alter table public.automation_occurrences
  add column if not exists release_sha text,
  add column if not exists openclaw_job_id text,
  add column if not exists claimed_by text,
  add column if not exists claimed_at timestamptz;

-- ------------------------------------------------------------------
-- 2. Staging view for offline test fixture (repo-only, not applied live)
-- ------------------------------------------------------------------
create or replace view public.automation_occurrences_staging as
select
  occurrence_id,
  automation_key,
  scheduled_for,
  openclaw_job_id,
  release_sha,
  claimed_by,
  claimed_at,
  status,
  created_at,
  updated_at
from public.automation_occurrences;

-- ------------------------------------------------------------------
-- 3. Insert-if-absent helper for test fixtures (idempotent on
--    (automation_key, scheduled_for) uniqueness constraint)
-- ------------------------------------------------------------------
create or replace function public.ensure_occurrence(
  p_automation_key text,
  p_scheduled_for  timestamptz,
  p_release_sha    text default null,
  p_openclaw_job_id text default null
) returns table (occurrence_id uuid, created boolean)
language plpgsql
security definer
set search_path = public as $$
declare
  v_occurrence_id uuid;
  v_created boolean := false;
begin
  insert into public.automation_occurrences
    (automation_key, scheduled_for, release_sha, openclaw_job_id, status)
  values (p_automation_key, p_scheduled_for, p_release_sha, p_openclaw_job_id, 'pending')
  on conflict (automation_key, scheduled_for) do nothing
  returning automation_occurrences.occurrence_id into v_occurrence_id;

  if v_occurrence_id is not null then
    v_created := true;
  else
    select occurrence_id into v_occurrence_id
      from public.automation_occurrences
     where automation_key = p_automation_key and scheduled_for = p_scheduled_for;
  end if;

  return query select v_occurrence_id, v_created;
end $$;

grant select on public.automation_occurrences_staging to service_role;
grant execute on function public.ensure_occurrence(text, timestamptz, text, text) to service_role;
