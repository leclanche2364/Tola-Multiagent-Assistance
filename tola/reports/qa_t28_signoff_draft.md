# QA T28 Signoff Draft -- Weekly Persona and Self-Improvement Review

**Date:** 2026-09-29  
**Batch:** T28  
**Gate:** QA T28  

---

## Per-Case Results

| Test ID | Description | Result | Notes |
|---------|-------------|--------|-------|
| T28-01 | Repeated candidate preference promotes correctly | PASS | PROMOTION_THRESHOLD=3; below threshold stays candidate, at threshold promotes, above threshold promotes once |
| T28-02 | Contradictory evidence prevents premature promotion | PASS | 3 positive + 1 negative observation = blocked with CONTRADICTION_BLOCK reason; no promotion occurs |
| T28-03 | Repeated delegation weakness creates improvement candidate | PASS | DELEGATION/PLAN_CORRECTION/USER_CORRECTION at REPEATED_WEAKNESS_THRESHOLD=3 creates candidate |
| T28-04 | One-off failure remains observation only | PASS | Single failure produces observation_kept but no candidate |
| T28-05 | Skill improvement remains proposal-only | PASS | SKILL_CHANGE candidates have status=PROPOSAL, applied=False always |
| T28-06 | No sensitive profile expansion | PASS | All 5 sensitive categories blocked; SENSITIVE_CATEGORIES matches T18 |
| T28-07 | Superseded profile entries remain historically traceable | PASS | record_supersession + trace() returns full chain old -> new |

## Determinism

All review functions are deterministic: same inputs produce same outputs across multiple calls. No clock reads (now_iso is input parameter). No random or non-deterministic operations.

## Deviations

None. All QA T28 cases pass. All 7 test classes cover the specified cases.

## Promotion/Proposal Rules

- Promotion: a candidate preference observed >= 3 times (PROMOTION_THRESHOLD) promotes from CANDIDATE to ACTIVE.
- Contradiction: opposite-direction evidence in window blocks promotion and records blocked_promotion with reason CONTRADICTION_BLOCK.
- Skill changes: proposal-only (status=PROPOSAL, applied=False); never auto-applied.
- Sensitive blocklist: health_conditions, relationship_status, finances, protected_characteristics, location_tracking -- never promote or extend profile.
- Superseded: prior preference preserved in superseded[] with traceable chain via trace(superseded_id).

## Files Created

- `tola/review/persona_review.py`
- `tola/review/improvement_review.py`
- `tola/tests/test_t28_persona.py`
- `tola/reports/qa_t28_signoff_draft.md`

## Combined Test Count

- Total tests: 910 (879 existing + 31 new T28)
- Passed: 910
- Failed: 0
- Errors: 0