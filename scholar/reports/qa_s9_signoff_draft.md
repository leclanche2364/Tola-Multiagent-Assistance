# QA S9 Sign-Off Draft — Learning Goal Contract

**Batch:** S9  
**Version/commit:** S9-impl-001  
**Environment:** Python 3 stdlib, unittest framework  
**Date:** 2026-09-30  
**Prior suite:** 537 tests (S0–S8), all green  
**New tests:** 182 (S9-01..S9-06 + edge cases)  
**Combined count:** 719 tests, all green  

---

## Functional Tests

| Test ID | Description | Result |
|---------|-------------|--------|
| S9-01 | Direct user goal created | PASS |
| S9-02 | Tola goal created | PASS |
| S9-03 | Pause: state retained | PASS |
| S9-04 | Stop: no further planning | PASS |
| S9-05 | Supersede: history retained | PASS |
| S9-06 | Restart: goal persists across sessions | PASS |

## Edge Case Tests

| Category | Tests | Result |
|----------|-------|--------|
| Invalid state transitions rejected | 14 cases (pause/resume/complete/stop/supersede on invalid states) | PASS |
| Malformed source rejected | 8 cases (empty fields, bad types, duplicate versions, unknown source types) | PASS |
| Goal retrieval after supersede | 7 cases (latest, version-1, history, non-existent) | PASS |
| Persistence independent of session | 7 cases (state round-trip, no session reference, multiple sessions) | PASS |
| Deterministic fixtures | 6 cases (source hashes, goal titles) | PASS |
| Malformed goal rejected | 8 cases (missing title/description, bad source type, non-string fields) | PASS |
| Malformed source rejected | 8 cases (empty fields, non-dict content, duplicate versions) | PASS |
| Source management (replace_source, get_source, history) | 10 cases | PASS |
| Frozen dataclass immutability | 3 cases | PASS |
| Version increment across transitions | 2 cases | PASS |
| Mixed source types (direct_user + tola) | 4 cases | PASS |
| Registry validation | 3 cases | PASS |
| State serialization round-trip | 3 cases | PASS |
| Injectable clock / deterministic timestamps | 6 cases | PASS |

## S9-01..S9-06 Coverage

- **S9-01** (Direct user goal created): 15 test methods covering creation, validation, rejection of malformed input, duplicate IDs, and source traceability.
- **S9-02** (Tola goal created): 8 test methods covering Tola-sourced goals, source type validation, and persistence independent of session.
- **S9-03** (Pause: state retained): 12 test methods covering ACTIVE→PAUSED transition, versioning, rejected invalid transitions, source traceability, and deterministic clock.
- **S9-04** (Stop: no further planning): 12 test methods covering ACTIVE/PAUSED→STOPPED, all invalid transitions blocked, and STOPPED means no further planning.
- **S9-05** (Supersede: history retained): 18 test methods covering version creation, old version retrievable, superseded state, rejected invalid transitions, source traceability, and mixed source types.
- **S9-06** (Restart: goal persists across sessions): 7 test methods covering state round-trip through `get_state()`/`GoalRecord`/`GoalStateTransition` reconstruction, multiple session boundaries, and session independence.

## Deviations

None. All 719 tests pass. No modifications were made to `contracts.py`, `event_outbox.py`, `events/consumer.py`, `curriculum/registry.py`, or `curriculum/proficiency_registry.py`.

## Files Created

1. `scholar/goals/registry.py` — `GoalRegistry` with `GoalSource`, `GoalRecord`, `GoalStateTransition` dataclasses; full state machine (ACTIVE/PAUSED/COMPLETED/STOPPED/SUPERSEDED); versioning with history preservation; injectable clock; deterministic fixtures support.
2. `scholar/fixtures/goals.py` — Deterministic fixtures for S9 QA: sources (direct_user, tola), goals, malformed data, invalid transition data, and helper builders (`make_registry`, `make_source`, `make_goal`, `make_tola_goal`, etc.).
3. `scholar/tests/test_s9_goals.py` — 182 test methods covering S9-01..S9-06 plus edge cases (invalid state transitions, malformed source rejection, goal retrieval after supersede, persistence independent of session).

## Approved by

Pending sign-off.

## Notes

- The `GoalRegistry` follows the same patterns as `ProficiencyRegistry` from S8: frozen dataclasses, injectable clock, versioned records with history preservation, and deterministic fixture support.
- Goals persist independently of any session object — no session/chat state is stored in the registry.
- The `replace_source` method was added to `GoalRegistry` to match the pattern from `ProficiencyRegistry`, enabling source versioning for goals.
- The `get_state()` method returns serializable dicts that can be round-tripped into a new registry instance, proving session independence.
