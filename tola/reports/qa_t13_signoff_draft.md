# QA T13 Signoff Draft — Outcome Verifier (Batch T13)

Date: 2026-09-29
Batch: T13 — Outcome Verifier

## Files Created

1. `tola/verification/__init__.py` — Package init
2. `tola/verification/criteria.py` — SuccessCriteria builder with named kind registry
3. `tola/verification/verifier.py` — `verify_outcome()` with deterministic outcome ladder
4. `tola/verification/closer.py` — `verify_and_close()` integrating T12 DelegationTracker
5. `tola/tests/test_t13_verification.py` — QA T13 unittest suite
6. `tola/reports/qa_t13_signoff_draft.md` — This file

## Outcome Ladder

VERIFIED -> all criteria met -> closes via tracker (RESULT_RECEIVED -> ACCEPTED)
PARTIALLY_VERIFIED -> some met -> return to specialist with missing[] list
NOT_VERIFIED -> none met (wrong kind or missing evidence) -> return to specialist
UNVERIFIABLE -> all failures due to incompatible evidence kind -> flag Tola

## Per-Case Results

| Case | Description | Outcome | Pass |
|------|-------------|---------|------|
| T13-01 | Complete fixture -> VERIFIED and closes via tracker | VERIFIED | Yes |
| T13-02 | Polished but incomplete (C3 missing) -> PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | Yes |
| T13-03 | Missing evidence blocks full success | NOT_VERIFIED/PARTIALLY_VERIFIED | Yes |
| T13-04 | Wrong evidence kind -> UNVERIFIABLE or NOT_VERIFIED | UNVERIFIABLE/NOT_VERIFIED | Yes |
| T13-05 | Self-reported complete with no evidence -> cannot close | NOT_VERIFIED | Yes |
| T13-06 | False-success fixture (C2 below threshold) -> cannot close | NOT_VERIFIED | Yes |
| T13-07 | Revision request bounded to missing criteria only | PARTIALLY_VERIFIED, missing=[C2] | Yes |
| T13-extra | Unknown criterion kind rejected at build time | ValueError raised | Yes |
| T13-extra | Empty criteria -> UNVERIFIABLE | UNVERIFIABLE | Yes |
| T13-extra | UNVERIFIABLE flags Tola via closer | FLAGGED_TOLA | Yes |
| T13-extra | PARTIALLY_VERIFIED returns to specialist | RETURN_TO_SPECIALIST | Yes |

## Test Counts

- Total tests run: 493 (including all T1-T13 suites)
- Passed: 493
- Failed: 0
- Errors: 0

## Deviations / Concerns

- None. All 493 tests pass, 0 failures, 0 errors.
- All new files parse-check clean via `ast.parse`.
- No T1-T12 code was modified.
- No writes outside `four-agent-repo/tola`.
- No network, no Supabase, no My Rhythm writes, no LLM calls, no clock reads.
- Plain ASCII in every file.