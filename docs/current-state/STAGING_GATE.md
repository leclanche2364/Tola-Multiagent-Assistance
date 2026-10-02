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
