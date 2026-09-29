# QA S2 - Scholar Authentication and Scope - Sign-off

Batch: S2
Environment: four-agent repo, main branch, built by Ling 3.0 Flash
sub-agent, closed out and gate-verified by Tola main session
Date: 2026-09-30

- S2-01 learner-state:read allowed. PASS
- S2-02 learning-plan:read allowed. PASS
- S2-03 learning-plan:write allowed (PUT route only). PASS
- S2-04 events:read allowed. PASS
- S2-05 progress write denied. PASS
- S2-06 assessment submit denied. PASS
- S2-07 course/topic delete denied. PASS
- S2-08 wrong user denied. PASS
- Extra coverage: scope-escalation attempts denied,
  user mutation denied, empty/unknown scopes denied, and every
  forbidden S1 registry entry is denied by check_access
  (cross-layer drift guard). PASS

145/145 unittest cases pass (29 S0 + 63 S1 + 53 S2), verified
by Tola main session (independent re-run). SCHOLAR_SCOPES is
exactly the four plan scopes. Import defect found at gate and
fixed at source: scopes.py/auth_policy.py and two S1 test files
used bare 'from intensiq import ...'; normalised to package-
qualified 'from scholar.intensiq import ...' so later batches
can import the package cleanly. Plain ASCII confirmed.
__pycache__ removed.

Overall: PASS
Approved by: Tola main session
