# QA T3 Signoff Draft -- Project Health and Materiality Engine

Date: 2026-09-29
Batch: T3

## Per-Case Results

| Case | Description | Result |
|------|-------------|--------|
| T3-01 | Healthy project remains ON_TRACK | PASS |
| T3-02 | Deadline risk triggers attention | PASS |
| T3-03 | Stalled project detected | PASS |
| T3-04 | Completed experiment awaiting review detected | PASS |
| T3-05 | Blocked dependency reflected | PASS |
| T3-06 | Project with no next action detected | PASS |
| T3-07 | Normal project does not become false urgent signal | PASS |
| T3-08 | Underlying evidence is available behind health label | PASS |

## Test Counts

- T1 tests: 32 (all PASS)
- T2 tests: 27 (all PASS)
- T3 tests: 12 (all PASS)
- Combined: 77 tests, 77 PASS, 0 FAIL

## Threshold Constants Chosen

- STALLED_DAYS_WITHOUT_PROGRESS = 5: A task with no progress for 5 days is a clear stall signal.
- DEADLINE_RISK_DAYS = 7: One week provides enough lead time for intervention.
- BLOCKED_DURATION_DAYS = 3: Three days blocked is enough to warrant a BLOCKED label.
- MILESTONE_SLIPPAGE_DAYS = 3: Milestones past due by 3 days are slipping.
- EXPERIMENT_DECISION_DAYS = 7: A completed experiment awaiting a decision for a week is material.
- APPROVAL_PENDING_DAYS = 5: Pending approvals older than 5 days block progress.
- CAPACITY_CONFLICT_TASKS = 2: Two active tasks on the same agent is a conflict.
- METRIC_DETERIORATION_DELTA = 0.15: A 15% negative move in a metric is material.
- NO_NEXT_ACTION_HOURS = 48: No actionable work within 48 hours signals dormancy.

## Deviations

None. All T3-01..T3-08 cases pass. The health engine is deterministic (timestamps come from inputs, never the clock), evidence-backed (every label carries HealthSignal instances with type, entity reference, and observed values), and does not produce false urgent signals on healthy projects (materiality_check returns False for ON_TRACK with no signals).