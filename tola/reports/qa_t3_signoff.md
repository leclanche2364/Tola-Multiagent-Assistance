# QA T3 - Project Health and Materiality Engine - Sign-off

Batch: T3
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T3-01 (healthy project stays ON_TRACK): PASS
- T3-02 (deadline risk triggers attention): PASS
- T3-03 (stalled project detected): PASS
- T3-04 (experiment awaiting review detected): PASS
- T3-05 (blocked dependency reflected): PASS
- T3-06 (no next action detected): PASS
- T3-07 (no false urgent signal): PASS
- T3-08 (evidence available behind health label): PASS

History: first build pass left 4 failures (stale fixture timestamps
producing false STALLED_ACTIVITY signals, and a label-mapping error where
a single deadline risk mapped to AT_RISK instead of ATTENTION). One Ling
fix cycle resolved all 4: label mapping corrected, no-next-action
detection now treats any active task as having a next action, fixtures
re-dated to the assessment date. Engine semantics preserved (no tests
weakened to pass).

Main-session verification: 77/77 PASS (32 T1 + 27 T2 + 18 T3), re-run by
Tola main session. Plain-ASCII check: clean after normalisation.
Boundary check: no My Rhythm write capability.

Overall: PASS
Approved by: Tola main session
