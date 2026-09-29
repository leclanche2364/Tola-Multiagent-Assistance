# QA T28 - Weekly Persona and Improvement Review - Sign-off

Batch: T28
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T28-01 (repeated candidate preference promotes at threshold
  3): PASS
- T28-02 (contradictory evidence blocks premature promotion,
  CONTRADICTION_BLOCK reason recorded even with 3+ supporting):
  PASS
- T28-03 (repeated delegation weakness >= 3 -> improvement
  candidate): PASS
- T28-04 (one-off failure remains observation only): PASS
- T28-05 (skill improvement remains proposal-only: status=PROPOSAL,
  applied always False): PASS
- T28-06 (no sensitive profile expansion; sensitive categories
  never promote or extend profile): PASS
- T28-07 (superseded profile entries historically traceable:
  trace(id) returns full old -> new chain): PASS

Rule constants replicated (not imported) from T18/T21 per
constraint: PROMOTION_THRESHOLD=3, REPEATED_WEAKNESS_THRESHOLD=3,
sensitive categories aligned. Pure functions, timestamps are
inputs, no I/O, deterministic, no clock reads.

No deviations reported. Main-session verification: 910/910 PASS
(879 T1-T27 + 31 T28), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (recurring registry/profiles.py).
Boundary check: no My Rhythm write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
