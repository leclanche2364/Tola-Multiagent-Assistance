# QA T21 - Improvement Ledger - Sign-off

Batch: T21
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T21-01 (user correction generates learning observation): PASS
- T21-02 (delegation failure generates observation): PASS
- T21-03 (reusable success pattern may generate observation):
  PASS (opt-in reusable_pattern flag)
- T21-04 (one-off noise does not automatically become candidate):
  PASS (returns None, never stored)
- T21-05 (root-cause evidence retained verbatim; evidence fields
  equal inputs exactly): PASS
- T21-06 (candidate links to underlying observations; LINK_MIN=1
  for corrections/failures, MIN_PATTERN=3 for reusable successes):
  PASS
- T21-07 (duplicate observation deduplicated/idempotent; SHA-256
  dedup key returns same observation, ledger length unchanged):
  PASS

Observation rules: USER_CORRECTION and DELEGATION failure always
observe; reusable success observes opt-in; noise never observes.
Evidence is stored verbatim, never summarised. Pure in-memory, no
I/O, deterministic, timestamps are inputs.

No deviations reported. Main-session verification: 720/720 PASS
(691 T1-T20 + 29 T21), re-run by Tola main session. Plain-ASCII
check: clean after normalisation (recurring registry/profiles.py).
Boundary check: no My Rhythm write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
