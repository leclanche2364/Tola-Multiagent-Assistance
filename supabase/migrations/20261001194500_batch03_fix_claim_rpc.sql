-- Batch 03 fix: PL/pgSQL OUT parameter `occurrence_id` in
-- claim_automation_occurrence shadowed the table column, making
-- `where occurrence_id = ...` ambiguous at first execution.
-- Redefines the RPC with qualified column references and a renamed
-- OUT column (claimed_id). Additive/replacement only.
create or replace function public.claim_automation_occurrence(
  p_automation_key text,
  p_scheduled_for  timestamptz,
  p_release_sha    text,
  p_openclaw_job_id text,
  p_claimed_by     text
) returns table (claimed_id uuid, outcome text)
language plpgsql
security definer
set search_path = public as $$
declare
  v_occurrence_id uuid;
begin
  insert into public.automation_occurrences
    (automation_key, scheduled_for, release_sha, openclaw_job_id)
  values (p_automation_key, p_scheduled_for, p_release_sha, p_openclaw_job_id)
  on conflict (automation_key, scheduled_for) do update
    set updated_at = now()
  returning automation_occurrences.occurrence_id into v_occurrence_id;

  update public.automation_occurrences as occ
     set status = 'claimed', claimed_by = p_claimed_by,
         claimed_at = now(), updated_at = now()
   where occ.occurrence_id = v_occurrence_id
     and occ.status in ('pending','failed')   -- failed occurrences may be re-claimed
  returning occ.occurrence_id into v_occurrence_id;

  if v_occurrence_id is not null then
    return query select v_occurrence_id, 'claimed'::text;
  else
    select occ.occurrence_id into v_occurrence_id
      from public.automation_occurrences as occ
     where occ.automation_key = p_automation_key
       and occ.scheduled_for = p_scheduled_for;
    return query select v_occurrence_id, 'already_claimed'::text;
  end if;
end $$;

revoke all on function public.claim_automation_occurrence(text, timestamptz, text, text, text) from anon;
grant execute on function public.claim_automation_occurrence(text, timestamptz, text, text, text) to service_role;
