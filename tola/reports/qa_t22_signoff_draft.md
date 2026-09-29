# QA T22 Signoff Draft -- Improvement Benchmark Harness

Date: 2026-09-29
Batch: T22

## Per-Case Results

### T22-01: Current Tola baseline recorded
- **Status**: PASS
- **Detail**: `record_baseline()` returns a frozen `Baseline` with `benchmark_version` set to `BENCHMARK_VERSION` ("1.0.0"), per-fixture `FixtureScore` entries for all 10 fixtures, and aggregate pass-rates.

### T22-02: Candidate tested on identical fixture set
- **Status**: PASS
- **Detail**: `evaluate_candidate()` requires every fixture id present in the baseline. A candidate run set missing a fixture raises `KeyError`. Identical runs produce verdict "ACCEPTED".

### T22-03: Improvement on one metric cannot hide critical regression
- **Status**: PASS
- **Detail**: Regressing any critical metric (`task_success`, `delegation_correct`, `escalation_correct`, `human_correction`) on any fixture forces verdict "REJECTED" even when other metrics improve (e.g., cost drops). Non-critical regressions yield "REVIEW".

### T22-04: Cost measured
- **Status**: PASS
- **Detail**: `Comparison.cost_delta` (int, token_cost sum difference) is present and correct. Zero for identical runs.

### T22-05: Latency measured
- **Status**: PASS
- **Detail**: `Comparison.latency_delta` (int, latency_ms sum difference) is present and correct. Zero for identical runs.

### T22-06: Human-correction proxy measured
- **Status**: PASS
- **Detail**: `Comparison.human_correction_delta` (int) is present. Regression in `human_correction` is treated as critical and forces "REJECTED".

### T22-07: Benchmark version pinned
- **Status**: PASS
- **Detail**: `BENCHMARK_VERSION = "1.0.0"` is embedded in `Baseline.benchmark_version` and `Comparison.benchmark_version`. Matches the constant.

### T22-08: Re-run is reproducible within declared tolerance
- **Status**: PASS
- **Detail**: Two evaluations of identical runs produce equal `Comparison` objects (frozen dataclass equality). `score_run()` uses `TOLERANCE = 0.01` for float comparisons; values within tolerance pass, outside fail.

## Deviations / Concerns
- None. All 8 QA cases pass. Determinism verified via frozen dataclass equality and hashability checks.
- The `KeyError` on missing fixture in `evaluate_candidate` is the chosen error signal (matches QA spec).
