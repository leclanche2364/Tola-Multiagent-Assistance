# QA T21 Signoff Draft -- Improvement Ledger

**Date:** 2026-09-29
**Batch:** T21
**Gate:** QA T21

## Per-Case Results

| Case | Description | Result | Notes |
|------|-------------|--------|-------|
| T21-01 | User correction generates learning observation | PASS | USER_CORRECTION event always produces Observation |
| T21-02 | Delegation failure generates observation | PASS | DELEGATION success=False always produces Observation |
| T21-03 | Reusable success pattern may generate observation | PASS | DELEGATION success=True with reusable_pattern=True produces Observation; without flag returns None |
| T21-04 | One-off noise does not automatically become candidate | PASS | BRIEFING and single success without pattern flag return None; no auto-candidate |
| T21-05 | Root-cause evidence retained exactly | PASS | event_payload and context_refs stored verbatim; assert equal to input |
| T21-06 | Candidate links to underlying observation ids | PASS | Candidate.observation_ids contains observation id; evidence_refs retained; insufficient raises ValueError |
| T21-07 | Duplicate observation deduplicated/idempotent | PASS | Same dedup key returns same Observation; ledger count unchanged across repeated calls |

## Deviations

None. All 7 QA T21 cases pass. 720 total tests (691 existing + 29 T21), 0 failures, 0 errors.

## Files Created

- `tola/improvement/__init__.py`
- `tola/improvement/ledger.py`
- `tola/improvement/candidates.py`
- `tola/tests/test_t21_improvement.py`
- `tola/reports/qa_t21_signoff_draft.md`