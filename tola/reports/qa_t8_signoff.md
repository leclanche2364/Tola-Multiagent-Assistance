# QA T8 - Escalation Matrix and Stop Rules - Sign-off

Batch: T8
Environment: four-agent repo, main branch, built by Ling 3.0 Flash sub-agent
Date: 2026-09-29

- T8-01..T8-09 (trigger level mapping, boundary violations always stop,
  healthy ON_TRACK work never stops, minor items do-not-escalate,
  escalation routing targets, determinism, BLOCKED/DORMANT material stop):
  PASS (58 T8 tests)

Escalation ladder verified: NOTE -> FLAG -> PAUSE -> STOP_AND_ESCALATE.
Routing verified: STOP_AND_ESCALATE -> Habeeb; NOTE/FLAG -> owning
specialist. Pure routing, no I/O, no message sending.

Main-session verification: 363/363 PASS (305 T1-T7 + 58 T8), re-run by
Tola main session. Child's final analysis concern (BLOCKED with
materiality not stopping) was verified resolved in final code:
MATERIAL_STOP_LABELS = {"BLOCKED","DORMANT"} present in stop_rules.py,
covered by tests. Plain-ASCII check: clean after normalisation (5 files,
including recurring registry/profiles.py). Boundary check: no My Rhythm
write capability. __pycache__ removed.

Overall: PASS
Approved by: Tola main session
