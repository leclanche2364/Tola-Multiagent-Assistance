# QA T20 Signoff Draft — Tola Performance Model

**Date:** 2026-09-29
**Batch:** T20
**Gate:** QA T20

## Per-Case Results

| Case | Description | Result | Notes |
|------|-------------|--------|-------|
| T20-01 | Delegation success metric correct | PASS | Exact fraction 7/9 on fixture |
| T20-02 | First-pass completion correct | PASS | 5 of 9 delegations had zero retries |
| T20-03 | User correction captured | PASS | 2 USER_CORRECTION events linked to delegation ids |
| T20-04 | Retry count correct | PASS | d1=0, d6=1, d7=2; KeyError on missing id |
| T20-05 | Correct/incorrect escalations tracked separately | PASS | correct=3, incorrect=1 |
| T20-06 | Time-window trends work | PASS | Inclusive boundaries; empty window returns [] |
| T20-07 | Cost/latency observable | PASS | cost_total=60.0, cost_avg=20.0, latency_total=600.0, latency_avg=200.0 |
| T20-08 | Evidence gate (claims) | PASS | <5 samples raises ValueError; >=5 stores with provenance |

## Deviations

None. All 8 QA T20 cases pass. 691 total tests (675 existing + 16 T20), 0 failures, 0 errors.

## Files Created

- `tola/performance/__init__.py`
- `tola/performance/metrics.py`
- `tola/performance/claims.py`
- `tola/tests/test_t20_performance.py`
- `tola/reports/qa_t20_signoff_draft.md`