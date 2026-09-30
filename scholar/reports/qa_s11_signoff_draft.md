# QA S11 Sign-Off Draft — Learner-State Analysis

**Batch:** S11 — Learner-State Analysis  
**Version/commit:** N/A (implementation in progress)  
**Environment:** local (Python 3 stdlib, no network)  
**Date:** 2026-09-30  
**Fixture version:** S11 fixtures v1.0  
**Model route:** Ling 3.0 Flash (seam-injected; tests use deterministic stub)  

---

## Functional Tests

| Test ID | Description | Result |
|---------|-------------|--------|
| S11-01 | Strong evidence recognised | PASS |
| S11-02 | Weak evidence recognised | PASS |
| S11-03 | Missing evidence → uncertainty explicit (never invented) | PASS |
| S11-04 | Observation vs interpretation separated (interpretation traceable to evidence refs) | PASS |
| S11-05 | Malformed Ling output → schema validation rejects it | PASS |

## IntenSIQ Contract Tests

N/A — S11 does not interact with IntenSIQ endpoints directly.

## Evidence-Integrity Tests

- Observed evidence never invented — all evidence refs point to actual LearnerState data.
- Interpretation is traceable to evidence_refs (S11-04).
- Uncertainty wording is explicit for missing/weak evidence (S11-03).
- PAUSED/SUPERSEDED goals are recorded with their state but not treated as active for planning.

## Curriculum/Proficiency Tests

N/A — S11 does not modify curriculum or proficiency registries.

## Goal/Strategy Tests

- PAUSED goals excluded from active analysis (state recorded, not planned).
- SUPERSEDED goals excluded from active analysis (state recorded, not planned).
- Goal metadata (title, state) extracted from LearnerState where available.

## Rhythm-Boundary Tests

N/A — S11 does not write to Rhythm.

## Research Tests

N/A — S11 is a learner-state analysis module, not a research module.

## Assessment-Integrity Tests

N/A — S11 does not generate or submit assessments.

## Model-Routing Tests

- Ling analyser is seam-injected via `LingAnalyserInterface`.
- Default is a deterministic stub (no network, no real model).
- Tests inject fixture outputs including deliberately malformed ones for S11-05.
- No real model calls in any test.

## Failure-Injection Tests

- Malformed Ling output (missing fields, wrong types, empty strings, non-dict, None) → `LingSchemaError` raised.
- Malformed learner state (missing schema_version, empty schema_version, missing state_version, non-dict) → `ValueError` raised.
- Analysis result records `ling_valid=False` and `ling_errors` when Ling output is malformed.
- Analysis still returns a result with evidence/interpretations even when Ling output is malformed.

## Cost/Observability Tests

N/A — no Ling API calls in tests.

---

## Critical Defects

None.

## High Defects

None.

## Medium Defects

None.

## Low Defects

None.

---

## Overall

**PASS**

All S11-01..S11-05 tests pass.  
All edge cases pass (interpretation without evidence ref rejected, uncertainty wording present for missing data, deterministic repeat calls, malformed learner state rejected, PAUSED/SUPERSEDED goals excluded from active analysis).  
Combined test count: **859** (805 prior S0–S10 + 54 new S11 tests).  
All green.

---

## Evidence

- `scholar/learner_state_analysis/__init__.py` — module exports.
- `scholar/learner_state_analysis/schema.py` — Ling output schema validation (`LingOutputSchema`, `LingSchemaError`, `validate_ling_output`).
- `scholar/learner_state_analysis/analyser.py` — `LearnerStateAnalyser` with seam-injected `LingAnalyserInterface`, deterministic stub default, strict evidence/interpretation/uncertainty separation.
- `scholar/fixtures/learner_state_analysis.py` — deterministic fixtures for strong/weak/missing evidence states, malformed states, PAUSED/SUPERSEDED states, Ling fixture outputs (valid and malformed).
- `scholar/tests/test_s11_analysis.py` — 54 tests covering S11-01..S11-05 plus edge cases.

## Approved by

Pending QA sign-off.

## Notes

- The `LingAnalyserInterface` is the seam for Ling model integration. The default stub is deterministic and produces valid output. Tests inject fixture outputs including deliberately malformed ones for S11-05.
- No real model calls are made in any test.
- The `LingSchemaError` dataclass was renamed to `LingSchemaErrorDetail` to avoid collision with the `LingSchemaError` exception class.
- PAUSED and SUPERSEDED goals are recorded with their state in analysis results but are not treated as active for planning purposes.
