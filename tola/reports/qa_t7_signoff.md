# QA T7 - Risk and Dependency Graph - Sign-off

Batch: T7
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T7-01..T7-08 (cycle detection, deterministic topological order, risk
  propagation downstream-only, orphaned/unowned risks, critical path,
  no T1-T6 regressions): PASS (34 T7 tests)

Built in one clean pass with the one-file-per-pass rule. Propagation
semantics verified: risk_propagation walks dependents (reverse of
dependency edges) from the risk's target entity; upstream dependencies
excluded.

Main-session verification: 305/305 PASS (271 T1-T6 + 34 T7), re-run by
Tola main session. Plain-ASCII check: clean after normalisation (3
files fixed at gate, including a recurring registry/profiles.py
regression). Boundary check: no My Rhythm write capability.
__pycache__ removed.

Overall: PASS
Approved by: Tola main session
