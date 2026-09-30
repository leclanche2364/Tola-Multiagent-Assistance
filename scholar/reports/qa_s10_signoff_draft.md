# QA Sign-Off Draft — Batch S10: Learning-Goal Decomposition

**Date:** 2026-09-30
**Status:** DRAFT — pending final sign-off
**Test pass status:** 805/805 green (719 prior + 86 new S10 tests)

---

## Summary

Batch S10 implements learning-goal decomposition: mapping goals to curriculum nodes, proficiencies, prerequisites, mastery dimensions, time horizon, and evidence requirements. All S10-01 through S10-05 acceptance criteria are met, plus edge-case coverage for PAUSED/SUPERSEDED goals, evidence requirements, deterministic repeat, and malformed goal rejection.

## Test Suite

- **File:** `scholar/tests/test_s10_decomposition.py`
- **Test count:** 86 new tests (S10-01..S10-05 + edge cases)
- **Combined count:** 805 (719 prior + 86 new)
- **Pass rate:** 100% (805/805 green)
- **Framework:** `python3 -m unittest` (pytest not installed)
- **No network, no real clocks** — deterministic clock injection throughout

## Acceptance Criteria

| Criterion | Status | Evidence |
|---|---|---|
| S10-01: Mechanical ventilation goal maps to relevant curriculum | PASS | 10 tests in `TestS10_01MechanicalVentilationMapsToCurriculum` |
| S10-02: Multi-domain goal decomposes correctly | PASS | 3 tests in `TestS10_02MultiDomainGoal` |
| S10-03: Missing prerequisite detected | PASS | 4 tests in `TestS10_03MissingPrerequisiteDetected` |
| S10-04: Unrealistic time horizon flagged as risk | PASS | 6 tests in `TestS10_04UnrealisticHorizonFlagged` |
| S10-05: Unknown proficiency no invented mapping | PASS | 4 tests in `TestS10_05UnknownProficiencyNoInventedMapping` |
| PAUSED goal decomposition still works | PASS | 2 tests in `TestEdgeCasePausedGoalDecomposition` |
| SUPERSEDED goal decomposition still works | PASS | 2 tests in `TestEdgeCaseSupersededGoalDecomposition` |
| Evidence requirements present | PASS | 3 tests in `TestEdgeCaseEvidenceRequirementsPresent` |
| Deterministic repeat calls give identical output | PASS | 9 tests in `TestEdgeCaseDeterministicRepeatCalls` |
| Malformed goal rejected | PASS | 4 tests in `TestEdgeCaseMalformedGoalRejected` |

## Key Design Decisions

1. **Mappings grounded in S7/S8 registries** — all curriculum nodes and proficiency mappings are resolved through `CurriculumRegistry` and `ProficiencyRegistry`, not hard-coded prompt data. Verified by `test_ventilation_goal_grounded_in_s7_registry` and `test_ventilation_goal_grounded_in_s8_registry`.

2. **No invented mappings for unknown proficiency** (S10-05) — goals with no matching curriculum keywords produce empty `curriculum_nodes`, `proficiencies`, and `evidence_requirements` lists. Zero domains, not multi-domain.

3. **Deterministic key** — `DecompositionResult.deterministic_key` is stable across repeat calls and across decomposer instances with identical registry state.

4. **Clock injection** — all tests use a deterministic `_fake_now()` clock (2026-09-30T12:00:00). No `datetime.utcnow()` calls in test code.

5. **Frozen dataclass** — `DecompositionResult` is a frozen dataclass; mutation attempts raise `Exception`.

## Modified Files

- `scholar/decomposition/registry.py` — fixed bugs (missing `re` import, stop words filtering, word-boundary token matching, word-number time horizon parsing, domain counting from proficiency mappings only)
- `scholar/tests/test_s10_decomposition.py` — new comprehensive test suite (86 tests)

## No Changes To

- `scholar/goals/registry.py` — no gap found; state machine and persistence contract intact
- `scholar/curriculum/registry.py` — read-only; no modifications
- `scholar/curriculum/proficiency_registry.py` — read-only; no modifications
- `scholar/fixtures/curriculum.py`, `scholar/fixtures/proficiency.py`, `scholar/fixtures/goals.py` — deterministic fixtures; no modifications
- `scholar/fixtures/decomposition.py` — new file; decomposition fixtures and helper

## Deviations

None. All 805 tests pass green.

---

*Draft prepared by Rhythm (subagent). Sign-off pending.*