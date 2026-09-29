# QA T6 - Goal Decomposition Engine - Sign-off

Batch: T6
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T6-01 (decomposition produces ordered milestones): PASS
- T6-02 (goal with existing milestones handled): PASS
- T6-03 (unknown goal type warns + lowers confidence, never invents): PASS
- T6-04 (dependencies respected in ordering): PASS
- T6-05 (replan produces new version, history preserved): PASS
- T6-06 (dependency block: blocked milestone marked, others preserved): PASS
- T6-07 (deadline moved -> anchors re-derived): PASS
- T6-08 (feasibility: within capacity -> FEASIBLE, overload -> options not auto-applied): PASS
- T6-09 (no invented facts: missing inputs -> warnings): PASS

History: first build pass left 4 failures + 4 errors (phase-ordering
mismatch, substring goal-type matching, dependency-block propagation,
UNDERLOADED mislabel, missing replanner import). One Ling fix cycle
resolved 6 of 8; the last 2 (UNKNOWN_GOAL_TYPE warning never appended;
dependency-block marking dependents as well as the blocked milestone,
giving 2 blocked instead of 1) were fixed at gate by Tola main session.
Engine semantics preserved; keyword matching is exact-token.

Main-session verification: 271/271 PASS (32 T1 + 27 T2 + 18 T3 + 115 T4
+ 41 T5 + 38 T6), re-run by Tola main session. Plain-ASCII check: clean
after normalisation. Boundary check: no My Rhythm write capability.

Overall: PASS
Approved by: Tola main session
