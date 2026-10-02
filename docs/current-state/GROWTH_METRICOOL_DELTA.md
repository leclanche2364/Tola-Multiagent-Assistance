# Growth Metricool Delta — G00 Audit

Date: 2026-10-03
Branch: `feat/autonomy-supabase-only` (HEAD: c3c6ddc)
Author: subagent (read-only audit)

## Evidence Matrix

| Item | Status | Evidence |
|---|---|---|
| Growth agent | EXISTING | `~/.openclaw/openclaw.json` agents.list id=`growth`; `docs/current-state/automations.json` owner=`growth`; `config-candidate/workspaces/growth/AGENTS.md` scoped duties |
| PostHog/Brevo/GA4/GSC/Apple/Google integrations | EXISTING (referenced) | `docs/CURRENT_SYSTEM.md` §2 design uses GA4/Search Console; `openclaw_four_agent_system_v1_1.md` §18 cites GA4/Search Console as data sources; no integration code in repo (external services) |
| Approved marketing skills | EXISTING | Growth allowlist: `product-intelligence`, `marketing-psychology` (`~/.openclaw/openclaw.json` + `config-candidate/workspaces/growth/AGENTS.md`); `skills/approved/README.md` governs activation |
| `packages/growth-tools` | EXISTING | `packages/growth-tools/package.json` v0.1.0; `@tola/blackboard-tools` dep; `tsconfig.json`, `src/`, `tests/` present |
| Growth automation definitions | EXISTING | `docs/current-state/automations.json` — `growth-daily-anomaly` (cron 08:00, C1, Metricool read-only analytics) |
| `growth-data-pull-06` | EXISTING (cron, ERROR) | `docs/current-state/BASELINE.md` and `docs/current-state/qa/QA-00.md` record it as a known cron entry with delivery error (Discord recipient missing); not rebuilt |
| Batch 03 Supabase safety primitives | EXISTING | `supabase/migrations/20261001180000_batch03_automation_approval_safety.sql`; `supabase/tests/test_batch03.sql`; `docs/current-state/batch03-migration-plan.md` (dry-run plan only) |
| Metricool MCP reads | EXISTING | `metricool__getAnalyticsDataByMetrics`, `metricool__getBestTimeToPostByNetwork`, `metricool__getBrandSettings`, `metricool__getScheduledPosts` in Growth automation and QA-12 staging gate |
| Metricool MCP writes | EXCLUDED | `docs/CURRENT_SYSTEM.md` §3 states Growth publishing is read-only via Metricool MCP; write tools (`createScheduledPost`, `createScheduledPostForReview`, `sendScheduledPostForReview`, `updateScheduledPost`) explicitly forbidden in `config-candidate/workspaces/growth/AGENTS.md` and `~/.openclaw/openclaw.json` Growth agent description |
| Metricool MCP version/tool schemas | INSPECTED | Tool names confirmed via `metricool__prompts_list` and `metricool__resources_list` availability; schemas match current MCP surface |
| Growth tool allowlist (live) | CONFIRMED | `~/.openclaw/openclaw.json` Growth agent: no `tools` allow/deny block at top level; `config-candidate/openclaw.json` Growth agent has `skills.allow` only; reads available, writes excluded per `CURRENT_SYSTEM.md` §3 |

## All-Agent Plan — Pending Dependencies (NOT Growth Tasks)

| Pending Work | Classification | Reason |
|---|---|---|
| Plugin work | DEPENDENCY | OpenClaw Plugin SDK integration (`openclaw_four_agent_system_v1_1.md` §2.11); not a Growth task |
| Policy entries | DEPENDENCY | Action-policy engine (`packages/action-policy`) exists; Metricool action-policy entries are a policy-layer concern, not Growth |
| Approval work | DEPENDENCY | Two-tier approval (`consume_approval` RPC, Batch 03) is a Supabase safety primitive; Growth uses it but does not own it |
| Scheduler work | DEPENDENCY | OpenClaw Automations/cron is platform-level; Growth automation is a consumer, not a scheduler task |
| Deployer work | DEPENDENCY | `packages/deploy` (Batch 11) is platform infrastructure; not a Growth task |

## Missing Capabilities (Growth-specific)

| Missing Capability | Status | Notes |
|---|---|---|
| Metricool action-policy entries | MISSING | No Metricool-specific action-policy entries exist in `packages/action-policy/` or `config-candidate/openclaw.json`; current policy is generic |
| Two-tier publication approval | MISSING | Batch 03 `consume_approval` provides single-use consumption; a two-tier approval flow for Metricool posts (review → publish) is not implemented |
| Policy-wrapped write adapter | MISSING | Metricool write tools are excluded; no policy-wrapped write adapter exists to gate Metricool writes through a typed adapter |
| Social workflow using existing skills/data | MISSING | No social workflow skill or automation ties `product-intelligence`/`marketing-psychology` skills to Metricool posting; `growth-daily-anomaly` is read-only only |
| Growth-specific acceptance checks | MISSING | No Growth-specific acceptance checks in `packages/growth-tools/tests/`; QA-00/QA-12 cover action-policy and deploy, not Growth publishing acceptance |

## Spec Deviations

None. All spec steps followed exactly: read-only audit, no live/config/schema/job/skill changes, no secrets in output or files.

## Reuse Notes

- `growth-data-pull-06` already exists as a cron entry (ERROR state noted in BASELINE/QA-00); do not rebuild in later batches.
- Batch 03 Supabase safety primitives (`automation_occurrences`, `consume_approval`, `external_operations`) are applied and tested; cite `supabase/migrations/20261001180000_batch03_automation_approval_safety.sql` and `supabase/tests/test_batch03.sql`.
- Metricool read tools are already in Growth's automation and QA-12 staging gate; no new MCP integration needed for reads.
