# QA S1 Sign-off Draft -- IntenSIQ Capability Contract

**Batch:** S1
**Date:** 2026-09-30
**Status:** PASS (draft)

---

## Per-Test Results

| Test ID | Test | Result |
|---------|------|--------|
| S1-01 | Existing endpoints classified per plan | PASS |
| S1-01 | All registry entries have required keys (route, verb, classification, rationale) | PASS |
| S1-01 | All classification values are valid | PASS |
| S1-01 | All rationales are non-empty | PASS |
| S1-02 | Progress write is NOT_FOR_SCHOLAR | PASS |
| S1-02 | Practice write is NOT_FOR_SCHOLAR | PASS |
| S1-02 | Assessment submit is NOT_FOR_SCHOLAR | PASS |
| S1-02 | Course delete is NOT_FOR_SCHOLAR | PASS |
| S1-02 | Topic delete is NOT_FOR_SCHOLAR | PASS |
| S1-02 | User mutation is NOT_FOR_SCHOLAR | PASS |
| S1-02 | is_forbidden returns True for progress write | PASS |
| S1-02 | is_forbidden returns True for practice write | PASS |
| S1-02 | is_forbidden returns True for assessment submit | PASS |
| S1-02 | is_forbidden returns True for course/topic delete | PASS |
| S1-02 | is_forbidden returns True for user mutation | PASS |
| S1-02 | is_forbidden returns False for GET progress | PASS |
| S1-02 | is_forbidden returns False for unknown route | PASS |
| S1-02 | FORBIDDEN_VERBS structure correct | PASS |
| S1-02 | ENDPOINTS structure correct | PASS |
| S1-03 | Exactly 3 NEW_INTEGRATION_NEEDED entries | PASS |
| S1-03 | Learner-state GET is NEW_INTEGRATION_NEEDED | PASS |
| S1-03 | Learning-plan GET/PUT is NEW_INTEGRATION_NEEDED | PASS |
| S1-03 | Events GET is NEW_INTEGRATION_NEEDED | PASS |
| S1-03 | No other new integration routes exist | PASS |
| S1-04 | All entries have rationale referencing plan | PASS |
| S1-04 | LearnerStateRead fields match plan 8.1 exactly | PASS |
| S1-04 | LearningPlan fields match plan 8.2 exactly | PASS |
| S1-04 | LearningEvent fields match plan 8.3 exactly | PASS |
| S1-04 | EVENT_TYPES frozenset matches plan 8.3 (9 types) | PASS |
| S1-04 | All contracts are frozen dataclasses | PASS |
| S1-04 | New integration entries reference plan sections 8.1-8.3 | PASS |
| VAL-01 | Valid plan dict passes validation | PASS |
| VAL-02 | Missing required field raises ValueError | PASS |
| VAL-03 | Multiple missing fields raises ValueError | PASS |
| VAL-04 | scheduled_at rejected | PASS |
| VAL-05 | calendar_time rejected | PASS |
| VAL-06 | session_times rejected | PASS |
| VAL-07 | start_time rejected | PASS |
| VAL-08 | end_time rejected | PASS |
| VAL-09 | Wrong creator (tola) rejected | PASS |
| VAL-10 | Wrong creator with custom validator rejected | PASS |
| VAL-11 | version=0 rejected | PASS |
| VAL-12 | version=-1 rejected | PASS |
| VAL-13 | expected_previous_version=0 accepted (first version) | PASS |
| VAL-14 | expected_previous_version=-1 rejected | PASS |
| VAL-15 | version not int rejected | PASS |
| VAL-16 | LearningPlan dataclass validates | PASS |
| DENIAL | GET progress not forbidden | PASS |
| DENIAL | GET practice not forbidden | PASS |
| DENIAL | POST progress is forbidden | PASS |
| DENIAL | PATCH progress is forbidden | PASS |
| DENIAL | DELETE course is forbidden | PASS |
| DENIAL | GET courses not forbidden | PASS |
| DENIAL | FORBIDDEN_VERBS count=4 | PASS |
| DENIAL | ENDPOINTS count=6 | PASS |
| PARSE | capability_registry.py ast.parse OK | PASS |
| PARSE | contracts.py ast.parse OK | PASS |
| PARSE | denials.py ast.parse OK | PASS |
| PARSE | test_s1_contract.py ast.parse OK | PASS |

---

## Classification Summary

| Classification | Count |
|----------------|-------|
| READ_EXISTING | 11 |
| WRITE_EXISTING | 0 |
| NOT_FOR_SCHOLAR | 6 |
| NEW_INTEGRATION_NEEDED | 3 |
| **Total** | **20** |

---

## Combined Test Count

- S0 tests: 29
- S1 tests: 63
- **Total: 92**
- Failures: 0
- Errors: 0

---

## Deviations

None. All S1 deliverables match the specification exactly.
