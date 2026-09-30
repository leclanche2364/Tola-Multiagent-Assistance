# QA S4 Sign-Off Draft — Versioned Learning Plan

**Batch:** S4 — Versioned Learning Plan  
**Date:** 2026-09-30  
**Environment:** Python 3 stdlib only, no network, no real clocks  
**Test runner:** `python3 -m unittest discover -s scholar/tests -t . -v`

---

## Implementation Files

| File | Purpose |
|------|---------|
| `scholar/intensiq/learning_plan.py` | `LearningPlanService` — GET/PUT with optimistic concurrency |
| `scholar/fixtures/learning_plans.py` | Deterministic plan-version fixtures (PLAN_V1, PLAN_V2, etc.) |
| `scholar/tests/test_s4_learning_plan.py` | S4-01..S4-07 + malformed-input edge cases |

## Contract Change (Minor)

**File:** `scholar/intensiq/contracts.py`  
**What changed:** `_has_calendar_time_fields` now recurses into list items (not just dicts).  
**Why:** The original implementation only checked dict keys, so calendar-time fields nested inside lists (e.g., `ordered_learning_items` containing a dict with `start_time`) were not detected. The fix adds list recursion so all nested structures are checked.

## S4 QA Gate Results

### S4-01 Create: new plan written — PASS
- PUT with no existing plan creates version 1
- EPV set to 0 for new plans
- Creator and updated_at injected by service
- Input dict not mutated (deep-copy)
- Stored plan retrievable via GET

### S4-02 Read: stored plan returned unchanged — PASS
- GET returns full plan with all required fields
- GET returns None for absent course_id
- Stored plan matches what was written

### S4-03 Version increment: correct — PASS
- Second PUT increments version to 2
- Third PUT increments to 3
- EPV matches the previous stored version
- Different courses have independent version counters

### S4-04 Stale write: rejected — PASS
- PUT with EPV != current stored version raises ValueError
- Stale write does not overwrite the stored plan
- Fresh write (EPV matches current version) succeeds

### S4-05 Calendar fields: rejected — PASS
- Top-level `scheduled_at` rejected
- Nested `start_time` in list items rejected
- `session_times` in nested dict rejected
- Valid plan without calendar fields accepted

### S4-06 Wrong creator: policy enforced — PASS
- `created_by: "tola"` rejected when creator="scholar"
- Correct creator accepted
- Direct `validate_learning_plan` also rejects wrong creator

### S4-07 Goal link: preserved across versions — PASS
- goal_id preserved when caller tries to change it on update
- goal_id preserved across multiple sequential updates
- Different initial goal_id accepted for new plans

### Malformed-input edge cases — PASS
- Missing required field rejected
- Empty plan_id rejected
- Non-positive version rejected
- Negative expected_previous_version rejected
- Float version rejected
- None creator rejected
- Calendar field in nested dict (mastery_targets list) rejected
- Direct `validate_learning_plan` rejects calendar fields, missing fields, non-int version

## Combined Test Count

| Suite | Tests |
|-------|-------|
| Prior (S0–S3) | 180 |
| New (S4) | 38 |
| **Combined** | **218** |
| **Status** | **ALL PASS** |

## Deviations

None. All 218 tests pass with zero failures or errors.

## Sign-Off

- **Functional tests:** PASS
- **IntenSIQ contract tests:** PASS
- **Evidence-integrity tests:** N/A (S4 does not touch evidence)
- **Versioning/safety tests:** PASS
- **Boundary tests:** PASS

**Overall:** PASS

**Approved by:** (pending QA review)  
**Notes:** Contract change to `contracts.py` is minimal and documented above — list recursion was required for correct calendar-time detection.
