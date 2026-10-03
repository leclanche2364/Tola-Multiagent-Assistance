# Batch 12 — Staging End-to-End Gate Results

**Branch:** feat/autonomy-supabase-only | **Head:** aa4f0e2aacf564a3b3147291d8183e6cf981ae62  
**Date:** 2026-10-02 | **Mode:** offline (non-live Supabase)

## Results Table

| Gate | Verdict | Evidence Command / Output | Latency / Cost | Defects Found + Fixes |
|------|---------|---------------------------|----------------|-----------------------|
| A — Deploy dry-run | PASS | `npx tsx -e "dryRun(sha,sha)"` → 7 DRY-RUN steps, no live changes | <1s | NONE |
| B — E2E flow | PASS (NON-LIVE) | `npx tsx scripts/staging-e2e.ts` → all 6 steps ALLOW, in-memory write, approval consumed on replay | <1s | NONE |
| C — Isolation denials | PASS | `npx tsx scripts/staging-gate-c.ts` → all 6 cases DENY (spawn=permanent_deny, sendToSpecialist=permanent_deny, exec=unknown_action, selfApprove=permanent_deny, oversized=oversized_payload, non-allowlisted=unknown_action) | <1s | **DEFECT:** `delegation.spawnSpecialist` and `delegation.sendToSpecialist` were `internal_reversible_write` (ALLOW). Fixed: changed to `permanent_deny` in `policy.ts` to enforce specialist isolation. |
| D — A3 approval | PASS | `npx tsx scripts/staging-gate-d.ts` → request→approve→execute→consumed(replay), scope redacted (account=[REDACTED], key=[REDACTED]) | <1s | **DEFECT:** `redactApprovalScope` did not redact `sk_`/`pk_` prefixed tokens or `key=` values. Fixed: added `sk_`/`pk_` regex and `key=` value redaction in `executor.ts`. |
| E — Automations once | PASS | `npx tsx scripts/staging-gate-e.ts` → 8 workflows instantiated, claim uniqueness enforced (second claim rejected), run history recorded, failure path alerts triggered, NO_CHANGE suppressed | <1s | NONE |
| F — Chaos injections | PASS | F1: UNAVAILABLE bounded; F2: 3 attempts then escalation; F3: restoreConfig called after reloadPlugin failure; F4: unknown status, consumed on replay | <1s | NONE |

## Offline Test Gate

All packages typecheck + tests green (see below).

## Defects Fixed

1. **policy.ts** — `delegation.spawnSpecialist` and `delegation.sendToSpecialist` changed from `internal_reversible_write` to `permanent_deny` (specialist isolation).
2. **executor.ts** — `redactApprovalScope` now redacts `sk_`/`pk_` tokens and `key=` values.

---

## Growth Metricool Release Gates (G04 Extension)

### Staging — Non-Production Metricool Profile Proofs

| Gate | Tier | Proof |
|------|------|-------|
| G04-S1 | Tier 1 alone cannot publish | `metricool__createScheduledPost` with `autoPublish: true` on non-production profile → rejected (no publish without Tier 2 release approval) |
| G04-S2 | Tier 2 must match immutable payload hash | `metricool__sendScheduledPostForReview` with mismatched `info` hash → rejected; matching hash → accepted |
| G04-S3 | Held-draft fallback safe | `metricool__createScheduledPost` with `draft: true` → accepted, no publish triggered |
| G04-S4 | Mutation/replay/duplicates fail | Replaying a consumed `sendScheduledPostForReview` → rejected (already consumed); duplicate `createScheduledPost` with identical payload → rejected (idempotency key collision) |

### Production Cutover — Growth-Only Additions

1. **Raw writes stay hidden** — Metricool raw write calls are never exposed to Growth or any agent; all writes go through `GovernedMetricoolWrapper`.
2. **Wrapped tools require explicit profile/platform approval** — Enabling `metricool__createScheduledPost`, `metricool__createScheduledPostForReview`, `metricool__sendScheduledPostForReview`, or `metricool__updateScheduledPost` requires explicit profile AND platform approval in the action-policy engine.
3. **Each canary needs separate Tier 1 schedule + Tier 2 release approvals** — Canary deployments for Growth Metricool writes must pass: (a) Tier 1 schedule approval (growth agent proposes, Habeeb approves schedule), (b) Tier 2 release approval (payload hash verified, non-production profile tested, then production release approved by Habeeb).

### Rollback

- **Disable Metricool writes** — Set `metricool__createScheduledPost`, `metricool__createScheduledPostForReview`, `metricool__sendScheduledPostForReview`, `metricool__updateScheduledPost` to denied in the action-policy engine.
- **Restore prior Growth config/jobs** — Revert `config-candidate/openclaw.json` and `docs/current-state/automations.json` to pre-G04 state using `openclaw.json.broken-batch08-20261002` as the rollback pattern reference.
- **Do NOT touch other agents** — Rollback is Growth-only; tola, rhythm, and scholar agents remain unaffected.
