# QA T27 Signoff Draft
# Weekly Executive Review (Batch T27)

## Per-Case Results

| Case | Description | Result |
|------|-------------|--------|
| T27-01 | Multiple projects -> coherent portfolio priorities | PASS |
| T27-02 | Rhythm capacity incorporated (overload -> capacity_request) | PASS |
| T27-03 | Material growth opportunity incorporated; immaterial excluded | PASS |
| T27-04 | Scholar obligations incorporated (deadline-driven) | PASS |
| T27-05 | Stalled work surfaced | PASS |
| T27-06 | Experiments/decisions awaiting action surfaced | PASS |
| T27-07 | Every next action has owner + follow_up type | PASS |
| T27-08 | Briefing concise (<= max lines, no empty lines, plain ASCII) | PASS |
| T27-09 | Dormant deferred work excluded; revived only with revive_reason | PASS |

## Determinism

All pipeline steps are deterministic: same inputs produce identical output across repeated runs. Ranking uses stable tiebreak by project id.

## Priority/Dormant Rules

- Portfolio priorities are scored by materiality (blocked/stalled/deadline/risk signals), ranked descending, tiebreak by id.
- Deferred items (deferred=True) are EXCLUDED from next_week_priorities and follow-ups unless they have an explicit revive_reason, in which case they are flagged REVIVED_WITH_REASON.

## Test Summary

- New tests: 9 QA T27 cases (T27-01..T27-09) plus determinism, plain-ASCII, and priority cap tests
- Combined test count (T1..T27): 879 total (844 pre-existing + 35 new T27 tests)
- All tests pass: 0 failures, 0 errors

## Files Created

- tola/review/__init__.py
- tola/review/weekly.py
- tola/tests/test_t27_review.py
- tola/reports/qa_t27_signoff_draft.md

## Deviations / Concerns

- None. All 9 QA T27 cases pass. The combined test suite (T1..T27) passes with 0 failures and 0 errors.
- All new files are plain ASCII. No network, no Supabase, no LLM calls, no clock reads.
- No writes outside four-agent-repo/tola. No git commands. No My Rhythm write capability.
- `build_weekly_briefing` caps at BRIEFING_MAX_LINES (20) and strips empty lines.
- `run_weekly_review` caps next_week_priorities at MAX_NEXT_WEEK_PRIORITIES (5).