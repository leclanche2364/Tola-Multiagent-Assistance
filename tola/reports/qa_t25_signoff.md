# QA T25 - Executive Heartbeat - Sign-off

Batch: T25
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T25-01 (nothing material -> no LLM wake, cost == IDLE_COST): PASS
- T25-02 (overdue material task -> wake): PASS
- T25-03 (long-standing blocker > 3 days -> wake): PASS
- T25-04 (approval pending > 5 days -> wake): PASS
- T25-05 (unreviewed experiment > 7 days -> wake): PASS
- T25-06 (stale PortfolioSnapshot > 3 days -> REFRESH_SNAPSHOT
  action-only; > 7 days hard limit -> wake): PASS
- T25-07 (repeated identical unresolved condition suppressed via
  kind:id:severity:age_bucket fingerprint; severity escalation
  re-wakes): PASS
- T25-08 (idle heartbeat cost within target; IDLE_COST=1,
  WAKE_COST=50 per finding; idle_cost_within_target helper): PASS

Deterministic sweep, timestamps are inputs, no clock reads, no
I/O. Anti-spam leaves state untouched on suppression.

No deviations reported. Main-session verification: 811/811 PASS
(785 T1-T24 + 26 T25), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (recurring registry/profiles.py).
Boundary check: no My Rhythm write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
