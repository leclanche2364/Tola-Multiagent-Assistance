# QA T4 - Agent Capability and Boundary Registry - Sign-off

Batch: T4
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T4-01..T4-03 (domain routing: scheduling->Rhythm, product->Growth, learning->Scholar): PASS
- T4-04 (Growth direct schedule writes rejected): PASS
- T4-05 (Tola My Rhythm writes rejected): PASS (hard enforcement in boundaries.py)
- T4-06 (Scholar product-growth authority rejected): PASS
- T4-07 (unknown domain safe escalation, never guess): PASS
- T4-08 (profile version change audit log): PASS
- T4-09 (profile shape matches plan section 7): PASS
- T4-10 (delegation to non-ACTIVE agent raises DelegationBlockedError): PASS
- T4-11 (eligible marketing work routes to Growth): PASS
- T4-12 (ineligible marketing work -> FUTURE_SPECIALIST_DEPENDENCY, never faked): PASS
- T4-13 (Marketing activation requires all activation_requirements): PASS

Main-session verification: 192/192 PASS (32 T1 + 27 T2 + 18 T3 + 115 T4),
re-run by Tola main session. Plain-ASCII check: clean after
normalisation (2 files fixed at gate). Boundary check: My Rhythm strings
in registry are enforcement rules (forbidden actions), verified correct.
__pycache__ removed.

Overall: PASS
Approved by: Tola main session
