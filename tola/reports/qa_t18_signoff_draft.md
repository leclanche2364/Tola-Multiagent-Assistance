# QA T18 Signoff Draft — Persona Awareness

Date: 2026-09-29
Batch: T18 — User Operating Profile and Persona Awareness

## Per-Case Results

| Case | Description | Result |
|------|-------------|--------|
| T18-01 | Explicit preference gets highest authority | PASS |
| T18-02 | Single behavioural observation stays CANDIDATE | PASS |
| T18-03 | Repeated pattern promotes only after threshold | PASS |
| T18-04 | Contradiction supersedes old preference with history | PASS |
| T18-05 | Sensitive inference is not stored | PASS |
| T18-06 | Repeated approval does not expand Tola permissions | PASS |
| T18-07 | Every active preference has provenance/confidence | PASS |
| T18-08 | Project-scoped preference does not become global without evidence | PASS |

## Deviations

None. All T18 cases pass.

## Files Created

- `tola/persona/__init__.py`
- `tola/persona/profile.py` — UserOperatingProfile, preference lifecycle (observe/promote/supersede), sensitive inference guard, scope isolation
- `tola/persona/permissions.py` — check_authority (approval does not expand capability set), get_active_preferences
- `tola/tests/test_t18_persona.py` — 30 tests covering T18-01..T18-08, determinism, plain ASCII
- `tola/reports/qa_t18_signoff_draft.md` — this file

## Test Count

624 total tests (all existing T1-T17 + 30 new T18 tests). 624 passed, 0 failed, 0 errors.