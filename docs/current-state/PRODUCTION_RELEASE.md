# Production Release — Batch 13 cutover record

**Release SHA:** `7cbff2e` (staging-tested, QA-12 signed). Docs-only commits after: `1e82c44` (postmortem, QA backfills, workflow regen), `5fc3648` (deploy CLI fixes).
**Cutover date:** 2026-10-02, 19:16 BST. Approved by Habeeb ("Go and do it safely").
**Repository:** leclanche2364/Tola-Multiagent-Assistance, branch `feat/autonomy-supabase-only`.

## What changed in production

### 1. Supabase — four-agent project `jcqiokvbkocnoxgeitin`
- Confirmed against repo `.env` before any apply (project-ref discipline).
- Applied via linked Supabase CLI (no raw DB passwords): `20261002080000_batch10_automation_run_claims.sql` (column skip notice — already present) and `20261002090000_batch11_deployments.sql` (deployments table + index created).
- Verified: REST probe `GET /rest/v1/deployments` → 200 with anon key. RLS correctly denies anonymous inserts (401).

### 2. Live OpenClaw config — intentionally NOT modified
Per `docs/current-state/postmortems/2026-10-02-config-allowlist-outage.md`, agent-facing config apply remains disabled. Already-live items were verified during cutover: subagent caps (maxSpawnDepth 1, maxChildrenPerAgent 3, maxConcurrent 3), `tools.sessions.visibility: all`, `agentToAgent.enabled: false`.
Follow-up (operator-approved apply, non-blocking): agent description enrichment; optional `workshop` key as config-documented governance. No approved feature depends on it.

### 3. Automations — 5 of 8 manifest entries live
Created as isolated cron jobs (owner tola), Telegram delivery (`telegram:5647750316`), idempotent declaration keys `autonomy:<stableName>`:

| Stable name | Schedule | Job id |
|---|---|---|
| blackboard-reconciler | 06:00 daily | cb36dc80-b90c-4a9a-a42f-5f0642f9f539 |
| tola-morning-brief | 07:30 daily | bc1557f3-22cd-4013-8f62-4ed70c6a605f |
| weekly-readonly-ops-check | Sun 08:00 | a66293fc-281d-4e7a-982e-f0537c9174f8 |
| tola-weekly-portfolio-review | Mon 10:00 | 24e2ea20-1302-4ef7-87f5-3b732b6416b1 |
| nightly-integrity-cost-check | 23:00 daily | 0cb88c37-3318-4fec-ad37-83c8004fc8c7 |

Known limitation (agent-side safeguard): the agent cron tool cannot register jobs owned by other agents. Three specialist-owned entries remain operator-created:
- rhythm-capacity-refresh — 05:00 daily, agentId rhythm
- growth-daily-anomaly — 08:00 daily, agentId growth
- scholar-weekly-progress — Mondays 09:00, agentId scholar
Prompts: `docs/current-state/automations.json`. Decision pending with Habeeb: create now or accept as known limitation for the 7-day review.

### 4. Canaries — all four PASS
1. Read-only Supabase probe (REST, anon key) — PASS.
2. Internal reversible write (write → verify md5 match → delete) — PASS.
3. Delegated specialist task via scholar (repo-head verification, reported `5fc3648 PASS`) — PASS.
4. Approval-required dry action via Skill Workshop — PASS: canary proposal entered `pending`, pre-install scan clean. Left pending deliberately for Habeeb to reject: `batch13-canary-proposal-20261002-89b70c94e5`.

### 5. Forced run evidence
- weekly-readonly-ops-check force-run 19:30 (runId `manual:a66293fc…:1790965822198:1`) — delivery route to Telegram exercised.
- Remaining four tola-owned jobs force-run post-record (results appended below).

## Rollback
- Cron jobs: `openclaw cron remove <jobId>` (ids above; declaration keys in `docs/current-state/automations.json`).
- Supabase: `drop table public.deployments;` — no other schema change was made.
- Live config: nothing to roll back.

## 7-day review
Check-back on 2026-10-09: all 8 automations running (or limitation confirmed), cost/sanity checks clean, specialist jobs created if approved.