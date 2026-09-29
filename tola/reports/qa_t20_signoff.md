# QA T20 - Tola Performance Model - Sign-off

Batch: T20
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T20-01 (delegation success metric correct): PASS (exact-fraction
  test on known fixture)
- T20-02 (first-pass completion correct: delegations with zero
  retries): PASS
- T20-03 (user correction captured and linked to delegation): PASS
- T20-04 (retry count correct): PASS
- T20-05 (correct/incorrect escalations tracked separately): PASS
- T20-06 (time-window trends work; inclusive bounds, deterministic):
  PASS
- T20-07 (cost/latency observable; totals and averages exact): PASS
- T20-08 (Tola cannot claim strength/weakness without measured
  evidence): PASS (claims require sample_count >= MIN_SAMPLE = 5;
  insufficient samples raise, nothing stored)

Metric kinds: DELEGATION | REVIEW | RECOVERY | BRIEFING |
ESCALATION | COST | LATENCY | USER_CORRECTION. Evidence gate in
claims.py; every stored claim carries the exact metric values and
sample counts it was derived from. Pure in-memory, no I/O,
deterministic, timestamps are inputs.

No deviations reported. Main-session verification: 691/691 PASS
(675 T1-T19 + 16 T20), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (5 files this batch, including
recurring registry/profiles.py). Boundary check: no My Rhythm write
capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
