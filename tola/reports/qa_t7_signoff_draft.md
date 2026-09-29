# QA T7 - Dependency and Risk Graph - Sign-off Draft

Batch: T7
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T7-01 (cycle detection raises/flags): PASS
- T7-02 (topological order deterministic): PASS
- T7-03 (risk propagation follows edges downstream only): PASS
- T7-04 (orphaned risks detected): PASS
- T7-05 (unowned risks detected): PASS
- T7-06 (critical path correct on fixture chain): PASS
- T7-07 (risk register from snapshot): PASS
- T7-08 (from_plans and from_snapshot builders): PASS

Files created:
- tola/graph/__init__.py
- tola/graph/graph.py (DependencyGraph, Node, Edge, CyclePath; from_plans, from_snapshot, topological_order, detect_cycles)
- tola/graph/risks.py (risk_register_from_snapshot, orphaned_risks, risk_propagation, unowned_risks, critical_path_milestones)
- tola/tests/test_t7_graph.py (305 total tests across all batches)

Propagation semantics: risk_propagation walks dependents (reverse of dependency edges) from the risk's target entity, returning all entities that would be affected downstream if that entity fails.

Main-session verification: 305/305 PASS (271 T1-T6 + 34 T7), re-run by Tola sub-agent. Plain-ASCII check: clean. ast.parse: clean for all new files. Boundary check: no My Rhythm write capability. No T1-T6 code modified.

Overall: PASS (draft)
