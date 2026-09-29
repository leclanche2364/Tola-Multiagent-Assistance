# QA T14 - Stalled Work Recovery - Sign-off

Batch: T14
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- Six stall patterns detected evidence-based: UNACKNOWLEDGED,
  NO_PROGRESS, BLOCKED_DEPENDENCY, CAPACITY_SHORTFALL, SCOPE_MISMATCH,
  DEADLINE_MISSED.
- Pattern -> action mapping verified: UNACKNOWLEDGED/NO_PROGRESS ->
  REQUEST_MISSING_INFO or QUERY_RHYTHM (never reassignment first);
  BLOCKED_DEPENDENCY -> REORDER_DEPENDENCIES only if T7 graph admits a
  valid reorder, else ESCALATE; CAPACITY_SHORTFALL -> QUERY_RHYTHM then
  RESCOPE/SPLIT_TASK; DEADLINE_MISSED -> ESCALATE/STOP, never silent
  rescope.
- BOUNDED_REASSIGNMENT: always requires_approval, same capability class
  per T4 registry. PASS (tested).
- Action set frozen: ALLOWED_ACTIONS frozenset of exactly the eight
  permitted actions; property-style check over fixtures confirms no
  out-of-set action can be produced. PASS.
- Recovery is proposals-only; no execution, no silent reassignment, no
  fabricated progress.

Main-session verification: 518/518 PASS (493 T1-T13 + 25 T14), re-run
by Tola main session. Plain-ASCII check: clean after normalisation
(recurring registry/profiles.py). Boundary check: no My Rhythm write
capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
