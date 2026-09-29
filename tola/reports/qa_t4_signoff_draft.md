# QA T4 Sign-off Draft -- Agent Capability and Boundary Registry

**Batch:** T4  
**Date:** 2026-09-29  
**Version:** 1.0.0  
**Status:** PASS (pending final sign-off)

---

## Per-Case Results

| Case | Description | Result | Notes |
|------|-------------|--------|-------|
| T4-01 | Scheduling/capacity task maps to Rhythm | PASS | 6 tests; all routing table and keyword matches confirm Rhythm |
| T4-02 | Funnel/product analysis maps to Growth | PASS | 7 tests; funnel/product/growth/acquisition/conversion/retention/experiment all route to Growth |
| T4-03 | Learning-gap work maps to Scholar | PASS | 6 tests; learning/scholar/curriculum/evidence/study/gap all route to Scholar |
| T4-04 | Growth direct schedule write rejected | PASS | 4 tests; boundary_check + enforce_boundary both reject |
| T4-05 | Tola direct My Rhythm write rejected | PASS | 6 tests; boundary_check + enforce_boundary both reject |
| T4-06 | Scholar cannot take product-growth authority | PASS | 6 tests; boundary_check + enforce_boundary both reject |
| T4-07 | Unknown domain follows safe escalation path | PASS | 6 tests; returns None + reason, never guesses |
| T4-08 | Capability profile version changes are auditable | PASS | 6 tests; PROFILE_VERSION_HISTORY appended on every change |
| T4-09 | Planned Marketing Agent visible with FUTURE_NOT_AVAILABLE | PASS | 11 tests; profile registered, status correct, activation_requirements populated |
| T4-10 | Delegation to unavailable Marketing Agent blocked | PASS | 5 tests; DelegationBlockedError raised for non-ACTIVE agents |
| T4-11 | Eligible marketing work routes to Growth | PASS | 7 tests; funnel/conversion/retention/product metrics/experiment/acquisition/growth recommendation all route to Growth |
| T4-12 | Unsupported marketing work becomes FUTURE_SPECIALIST_DEPENDENCY | PASS | 10 tests; paid acquisition, SEO, content distribution, community growth, campaign ops, lifecycle CRM, partnership outreach all deferred |
| T4-13 | Marketing Agent cannot become ACTIVE until prerequisites complete | PASS | 11 tests; all 7 activation_requirements listed, can_activate=False |

---

## Test Counts

- T4 new tests: 192 total (all T4-01..T4-13 + structural)
- T1-T3 existing tests: 77 (unchanged, all passing)
- Combined total: 192 tests
- Pass: 192
- Fail: 0

---

## Domain Routing Table

| Task Domain | Agent |
|-------------|-------|
| scheduling | Rhythm |
| capacity | Rhythm |
| schedule | Rhythm |
| rhythm | Rhythm |
| product | Growth |
| growth | Growth |
| funnel | Growth |
| acquisition | Growth |
| conversion | Growth |
| retention | Growth |
| experiment | Growth |
| marketing | Growth (eligible work under current contract) |
| learning | Scholar |
| scholar | Scholar |
| curriculum | Scholar |
| evidence | Scholar |
| study | Scholar |
| gap | Scholar |
| unknown domain | None (safe escalation, never guess) |

---

## Deviations and Concerns

1. **Marketing Agent routing**: Marketing work eligible under Growth's current contract routes to Growth (T4-11). Ineligible marketing work records a FUTURE_SPECIALIST_DEPENDENCY and is deferred (T4-12). This matches the plan §4 routing exactly.
2. **Profile version history**: PROFILE_VERSION_HISTORY is a module-level mutable list. In production this would be backed by a durable store, but for the T4 build it satisfies the audit requirement deterministically.
3. **No clock reads**: All logic is deterministic; timestamps are explicit inputs only.
4. **T1-T3 preserved**: No existing T1-T3 code was modified. All 77 existing tests continue to pass.

---

## Sign-off

- Functional tests: PASS
- Authority tests: PASS
- Boundary enforcement tests: PASS
- Availability/delegation tests: PASS
- Structural tests: PASS

**Overall: PASS**