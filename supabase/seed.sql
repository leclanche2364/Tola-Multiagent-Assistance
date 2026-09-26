-- Supabase seed data (idempotent) — four-agent system
-- Run by `supabase db reset` / CLI seed step, or applied manually via SQL editor.
-- Satisfies T3.2 (seed twice = deterministic, no duplication) and T3.6
-- (approved skills require source/revision/hash metadata — this seed keeps
-- tola-core-v1 in 'quarantined' until a real review promotes it).

-- ============ agents (deterministic, conflict-safe) ============
insert into agents (agent_name, role) values
  ('tola',    'Chief of Staff — orchestration, routing, verification'),
  ('rhythm',  'Life planning and scheduling'),
  ('growth',  'Growth intelligence'),
  ('scholar', 'Research and learning')
on conflict (agent_name) do nothing;

-- ============ tola-core-v1 (native skill, quarantined) ============
-- content_hash is sha256 of the canonical descriptor below; update it if the
-- skill definition changes, and bump local_revision per skill_registry unique
-- constraint (skill_name, local_revision).
insert into skill_registry (
  skill_name,
  owner_agent_id,
  origin_type,
  source_repository,
  source_commit,
  source_version,
  local_revision,
  status,
  content_hash
)
select
  'tola-core-v1',
  (select agent_id from agents where agent_name = 'tola'),
  'native',
  'https://github.com/leclanche2364/Tola-Multiagent-Assistance',
  '3306ec1',
  'v1',
  1,
  'quarantined',
  encode(digest(
    'tola-core-v1|native|v1|chief-of-staff-core|orchestration,routing,verification',
    'sha256'
  ), 'hex')
where not exists (
  select 1 from skill_registry
  where skill_name = 'tola-core-v1' and local_revision = 1
);
