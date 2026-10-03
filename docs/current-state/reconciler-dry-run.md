# Reconciler Dry-Run Output — G04 (Existing Jobs & Release Gates)

**Branch:** feat/autonomy-supabase-only | **Commit:** b8b5443 | **Date:** 2026-10-03

## Reconciliation Method
- Compare `docs/current-state/automations.json` stable names against the manifest
- Only missing or changed jobs are proposed; existing stable names unchanged
- No new job creation unless delta audit proves a distinct schedule is needed
- Metricool owns exact publish times — no OpenClaw posting cron added

## Manifest Stable Names (automations.json)

| Stable Name | Owner | Schedule | Status |
|---|---|---|---|
| blackboard-reconciler | tola | 0 6 * * * | EXISTING (unchanged) |
| tola-morning-brief | tola | 30 7 * * * | EXISTING (unchanged) |
| growth-daily-anomaly | growth | 0 8 * * * | EXISTING (unchanged) |
| rhythm-capacity-refresh | rhythm | 0 5 * * * | EXISTING (unchanged) |
| scholar-weekly-progress | scholar | 0 9 * * 1 | EXISTING (unchanged) |
| tola-weekly-portfolio-review | tola | 0 10 * * 1 | EXISTING (unchanged) |
| nightly-integrity-cost-check | tola | 0 23 * * * | EXISTING (unchanged) |
| weekly-readonly-ops-check | tola | 0 8 * * 0 | EXISTING (unchanged) |
| growth-social-workflow | growth | 0 10 * * * | EXISTING (unchanged) |

## Reconciliation Result: NO CHANGES PROPOSED
- All 9 stable names from the manifest already exist in automations.json
- No missing jobs detected
- No changed schedule definitions detected
- growth-social-workflow already contains the social workflow (G00 spec item 4 satisfied by existing job)

## growth-data-pull-06 Config Fix (Config Candidate)
- **File:** config-candidate/openclaw.json
- **Change:** Added `delivery` block to the growth agent with Discord recipient `channel:1553077643807563847`
- **Rationale:** Reuses existing `growth-data-pull-06` cron entry (known ERROR in BASELINE/QA-00 for missing Discord recipient); fixes the config candidate instead of creating a new data-pull job
- **No new data-pull job created**

## Metricool Publish Times
- Metricool owns exact publish times; no OpenClaw posting cron added
- growth-social-workflow schedule (0 10 * * *) is the existing weekly review slot; no new job needed

## Staging Gate Extensions (G04)
See docs/current-state/STAGING_GATE.md — Growth Metricool Release Gates appendix

## Production Cutover Extensions (G04)
See docs/current-state/PRODUCTION_RELEASE.md — Growth Metricool Release Gates appendix

## Rollback (G04)
- Disable Metricool writes in action-policy engine
- Restore prior Growth config/jobs from openclaw.json.broken-batch08-20261002 pattern
- Growth-only rollback; do NOT touch other agents
