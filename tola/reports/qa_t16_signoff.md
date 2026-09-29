# QA T16 - Scope Control - Sign-off

Batch: T16
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T16-01 (high-value aligned work -> START): PASS
- T16-02 (oversized work -> SHAPE_SMALLER, smallest viable version
  spelled out): PASS after gate fix
- T16-03 (good idea at wrong time -> DEFER with revisit condition): PASS
- T16-04 (low value -> STOP with stop condition; missing dependencies
  -> blocked): PASS
- T16-05 (opportunity cost explicitly shown; displaces populated): PASS
- T16-06 (consequential ambiguous -> NEEDS_USER_DECISION, never
  guessed): PASS
- T16-07 (reasoning references current priorities/capacity, not
  generic advice): PASS after gate fix

Verdict set frozen: START | SHAPE_SMALLER | DEFER | STOP |
NEEDS_USER_DECISION. scope_gate returns a T15 register-record
skeleton for auditable verdicts. Pure functions, no I/O.

Gate arbitration by Tola main session (child stalled mid-fix):
- Oversized detection added: an aligned proposal declaring its own
  smallest viable version routes to SHAPE_SMALLER ahead of dependency
  and capacity stops.
- SHAPE_SMALLER reasoning lines now cite concrete capacity values.
- Test typo fixed (displays -> displaces) in determinism check.

Main-session verification: 562/562 PASS (543 T1-T15 + 19 T16), re-run
by Tola main session. Plain-ASCII check: clean after normalisation
(recurring registry/profiles.py). Boundary check: no My Rhythm write
capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
