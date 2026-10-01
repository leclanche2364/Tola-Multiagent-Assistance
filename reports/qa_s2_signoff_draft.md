# QA S2 Signoff Draft — Scholar Authentication and Scope

**Date:** 2026-09-30
**Batch:** S2
**QA Gate:** S2

---

## Per-Test Results

| Test ID | Description | Result |
|---------|-------------|--------|
| S2-01 | Learner-state read allowed | PASS |
| S2-02 | Learning-plan read allowed | PASS |
| S2-03 | Learning-plan write allowed (PUT only) | PASS |
| S2-04 | Events read allowed | PASS |
| S2-05 | Progress write denied | PASS |
| S2-06 | Assessment submit denied | PASS |
| S2-07 | Course/topic delete denied | PASS |
| S2-08 | Wrong user denied | PASS |
| S2-E1 | Scope escalation: learning-plan:write cannot write learner-state | PASS |
| S2-E2 | Scope escalation: learning-plan:write cannot write events | PASS |
| S2-E3 | Scope escalation: learner-state:read cannot write learner-state | PASS |
| S2-E4 | Scope escalation: learner-state:read cannot write learning-plan | PASS |
| S2-E5 | Scope escalation: events:read cannot write learner-state | PASS |
| S2-E6 | Scope escalation: events:read cannot write learning-plan | PASS |
| S2-E7 | User mutation denied even with valid user | PASS |
| S2-E8 | Empty scopes denied | PASS |
| S2-E9 | Unknown scopes denied | PASS |
| S2-E10 | Empty scopes list denied | PASS |
| S2-X1 | Every NOT_FOR_SCHOLAR registry entry denied by check_access | PASS |
| S2-X2 | Every NOT_FOR_SCHOLAR entry is also is_forbidden | PASS |
| S2-X3 | AUTH_POLICY structure (credential design, principles) | PASS |
| S2-X4 | SCHOLAR_SCOPES frozenset has exactly 4 entries | PASS |
| S2-X5 | ast.parse passes for all 3 new files | PASS |

---

## Summary

- **Files created:**
  - `scholar/intensiq/scopes.py` — `SCHOLAR_SCOPES` frozenset (4 scopes) + `ScopeCheck.can()` helper
  - `scholar/intensiq/auth_policy.py` — `AUTH_POLICY` document-object + `check_access()` function
  - `scholar/tests/test_s2_auth.py` — 25 test methods across 12 test classes
- **Combined test count:** 145 (92 prior S0+S1 + 53 new S2)
- **Scope summary:** `learner-state:read`, `learning-plan:read`, `learning-plan:write`, `events:read`
- **Deviations:** None. All S0/S1 outputs preserved unchanged.