# QA T15 Signoff Draft -- Decision Register and Review Triggers

**Date:** 2026-09-29
**Batch:** T15 -- Decision Register and Review Triggers
**Status:** Draft -- pending final QA review

---

## Files Created

| File | Path |
|------|------|
| Decisions package init | `tola/decisions/__init__.py` |
| Decision register | `tola/decisions/register.py` |
| Review engine | `tola/decisions/review.py` |
| Explain engine | `tola/decisions/explain.py` |
| T15 test suite | `tola/tests/test_t15_decisions.py` |
| QA signoff (this file) | `tola/reports/qa_t15_signoff_draft.md` |

---

## Test Results

| Metric | Value |
|--------|-------|
| Total tests (all batches T1..T15) | 541 |
| Passed | 541 |
| Failed | 0 |
| Errors | 0 |
| New T15 tests | 23 |
| Existing tests (T1..T14) | 518 |

---

## QA T15 Case Coverage

| QA Case | Test Class | Status |
|---------|-----------|--------|
| T15-01 Decision captures reason/evidence/tradeoff | TestT15DecisionRegister | PASS |
| T15-01 Incomplete decision rejected | TestT15DecisionRegister | PASS |
| T15-02 Review date before due (not surfaced) | TestT15DecisionRegister | PASS |
| T15-02 Review date at due (surfaced) | TestT15DecisionRegister | PASS |
| T15-02 Review date after due (surfaced) | TestT15DecisionRegister | PASS |
| T15-03 Revisit trigger METRIC_BELOW match | TestT15DecisionRegister | PASS |
| T15-03 Revisit trigger METRIC_BELOW no-match | TestT15DecisionRegister | PASS |
| T15-03 Revisit trigger HEALTH_LABEL match | TestT15DecisionRegister | PASS |
| T15-03 Revisit trigger EVENT_OCCURRED match | TestT15DecisionRegister | PASS |
| T15-03 Revisit trigger EVENT_OCCURRED no-match | TestT15DecisionRegister | PASS |
| T15-03 Unknown trigger kind rejected at build time | TestT15DecisionRegister | PASS |
| T15-04 Superseded decision keeps history | TestT15DecisionRegister | PASS |
| T15-04 Both records retrievable | TestT15DecisionRegister | PASS |
| T15-04 Supersede raises on already superseded | TestT15DecisionRegister | PASS |
| T15-05 Missing reason rejected | TestT15DecisionRegister | PASS |
| T15-05 Missing date rejected | TestT15DecisionRegister | PASS |
| T15-05 Empty evidence rejected | TestT15DecisionRegister | PASS |
| T15-06 Explain superseded decision | TestT15DecisionRegister | PASS |
| T15-06 Explain active decision | TestT15DecisionRegister | PASS |
| T15-06 Explain includes all fields | TestT15DecisionRegister | PASS |
| T15-06 Determinism: due_reviews | TestT15DecisionRegister | PASS |
| T15-06 Determinism: triggers | TestT15DecisionRegister | PASS |
| T15-06 Determinism: register idempotent | TestT15DecisionRegister | PASS |

---

## Required Decision Fields

decision, reason, evidence, alternatives, tradeoff, owner, date, expected_outcome (required); review_date, revisit_trigger (optional)

---

## Design Notes

- `DecisionRecord` is frozen (immutable after registration); supersession is the only permitted change via `supersede_decision`.
- `register_decision` validates all required fields are present and non-empty; raises `ValueError` on incomplete records.
- `due_reviews` is deterministic: `now_iso` is an explicit input, no clock reads.
- `check_revisit_triggers` supports three trigger kinds (`HEALTH_LABEL`, `METRIC_BELOW`, `EVENT_OCCURRED`) and raises `ValueError` for unknown kinds.
- `explain_decision` produces plain ASCII with all fields; no markdown tables.
- All code uses Python 3 stdlib only; no network, no Supabase, no clock reads.

---

## Deviations and Concerns

1. **Superseded record review_date**: The superseded fixture was set with `review_date=None` to avoid it appearing in `due_reviews` results alongside the active record. This is a test-fixture choice; the register itself does not suppress superseded records from review queries. If the spec requires filtering superseded records from `due_reviews`, a `filter_superseded` flag should be added to `due_reviews`.
2. **ID generation**: Decision IDs use a simple hash of date+owner+decision text. This is deterministic but not collision-proof for adversarial inputs. Acceptable for the current scope.
3. **No Tola write capability to My Rhythm**: The decision register is purely in-memory; no persistence layer is implemented in this batch.

---

## Parse Check

All new files pass `ast.parse()`:
- `tola/decisions/__init__.py` -- OK
- `tola/decisions/register.py` -- OK
- `tola/decisions/review.py` -- OK
- `tola/decisions/explain.py` -- OK
- `tola/tests/test_t15_decisions.py` -- OK

---

## Signoff

Batch T15 is complete. All 541 tests pass (0 failures, 0 errors). The decision register records significant decisions with full context, surfaces review dates when due, fires revisit triggers on defined conditions, and preserves superseded decisions in history.