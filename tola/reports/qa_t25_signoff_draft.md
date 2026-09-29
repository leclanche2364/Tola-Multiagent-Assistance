# QA T25 Sign-off Draft — Executive Heartbeat

## Files Created

- `tola/heartbeat/__init__.py`
- `tola/heartbeat/policy.py`
- `tola/heartbeat/heartbeat.py`
- `tola/tests/test_t25_heartbeat.py`
- `tola/reports/qa_t25_signoff_draft.md` (this file)

## Test Results

| Test suite | Count | Pass | Fail | Error |
|---|---|---|---|---|
| All T1–T25 (full suite) | 811 | 811 | 0 | 0 |
| T25-01..T25-08 (new) | 15 | 15 | 0 | 0 |

## Per-Case Results (QA T25)

| Case | Description | Result |
|---|---|---|
| T25-01 | Nothing material → no LLM wake | PASS — empty and non-material conditions yield `wake=False`, `cost_units=IDLE_COST` |
| T25-02 | Overdue material task → wake | PASS — `OVERDUE_TASK` with material flag and negative age_days triggers `wake=True` |
| T25-03 | Long-standing blocker → wake | PASS — blocker older than `BLOCKER_AGE_LIMIT` (3d) wakes; at or below limit does not |
| T25-04 | Approval beyond threshold → wake | PASS — `APPROVAL_PENDING` older than `APPROVAL_AGE_LIMIT` (5d) wakes |
| T25-05 | Unreviewed experiment → wake | PASS — `EXPERIMENT_UNREVIEWED` older than `EXPERIMENT_REVIEW_AGE` (7d) wakes |
| T25-06 | Stale PortfolioSnapshot → refresh/wake | PASS — within hard limit → `ACTION_ONLY` + `REFRESH_SNAPSHOT`, no wake; beyond hard limit → wake |
| T25-07 | Repeated identical condition suppressed | PASS — second run with same fingerprint suppresses new wake; severity escalation re-wakes |
| T25-08 | Idle cost within target | PASS — quiet run costs `IDLE_COST` (1); action-only stays within target; wake exceeds target |

## Threshold / Anti-Spam Rules

- **THRESHOLDS**: `OVERDUE_TASK` (0d, any overdue material task wakes), `BLOCKER_AGE_LIMIT` (3d), `APPROVAL_AGE_LIMIT` (5d), `EXPERIMENT_REVIEW_AGE` (7d), `SNAPSHOT_MAX_AGE` (3d → REFRESH_SNAPSHOT), `SNAPSHOT_HARD_LIMIT` (7d → wake).
- **Anti-spam**: state dict keyed by `kind:id`; fingerprint = `kind:id:severity:age_bucket`; identical fingerprint on repeat sweep suppresses new wake; changed severity/age bucket or new condition re-wakes.
- **Cost**: `IDLE_COST=1` for quiet runs, `WAKE_COST=50` per wake finding, `ACTION_ONLY` (REFRESH_SNAPSHOT) adds no cost.

## Deviations / Concerns

- None. All 811 tests pass (0 failures, 0 errors). All new files pass `ast.parse`.
- `now_iso` is an input parameter only; no clock reads anywhere.
- No writes outside `tola/`. No network, no Supabase, no LLM calls.
