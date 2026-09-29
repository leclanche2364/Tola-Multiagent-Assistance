"""Benchmark harness for Batch T22 -- Improvement Benchmark Harness.

record_baseline(runs) -> Baseline
evaluate_candidate(runs, baseline) -> Comparison

Plain ASCII. Stdlib only. No I/O. No clock reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.benchmark.fixtures import (
    BENCHMARK_VERSION,
    TOLERANCE,
    build_all_fixtures,
    build_fixture,
    score_run,
    FixtureScore,
)

# ---------------------------------------------------------------------------
# Critical-metric rule
# ---------------------------------------------------------------------------

REGRESSION_CRITICAL = frozenset({
    "task_success",
    "delegation_correct",
    "escalation_correct",
    "human_correction",
})


# ---------------------------------------------------------------------------
# Frozen data objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Baseline:
    """Recorded baseline from current-Tola runs."""
    per_fixture: dict[str, FixtureScore]
    aggregate: dict[str, float]
    benchmark_version: str
    runs: tuple[tuple[str, dict[str, Any]], ...]


@dataclass(frozen=True)
class Regression:
    fixture_id: str
    fixture_name: str
    metric: str
    baseline_value: Any
    candidate_value: Any


@dataclass(frozen=True)
class Improvement:
    fixture_id: str
    fixture_name: str
    metric: str
    baseline_value: Any
    candidate_value: Any


@dataclass(frozen=True)
class Comparison:
    """Result of comparing candidate runs against a baseline."""

    per_fixture: frozenset[tuple[str, tuple[tuple[str, bool], ...]]]
    regressions: tuple[Regression, ...]
    improvements: tuple[Improvement, ...]
    verdict: str  # "ACCEPTED" | "REJECTED" | "REVIEW"
    benchmark_version: str
    cost_delta: int
    latency_delta: int
    human_correction_delta: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _aggregate(scores: list[FixtureScore]) -> dict[str, float]:
    """Compute mean pass-rate per metric across fixtures."""
    if not scores:
        return {}
    metrics = set()
    for s in scores:
        metrics.update(s.metric_scores.keys())
    result = {}
    for m in sorted(metrics):
        passes = sum(1 for s in scores if s.metric_scores.get(m) is True)
        result[m] = passes / len(scores)
    return result


def _extract_observed(runs: list[tuple[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Map fixture_id -> observed dict from runs."""
    return {fixture_id: obs for fixture_id, obs in runs}


# Metrics where a HIGHER value is worse (regression = increase).
# For all other numeric metrics, lower is worse (regression = decrease).
_HIGHER_IS_WORSE: frozenset[str] = frozenset({"human_correction"})


def _compare_values(metric: str, base: Any, cand: Any) -> str:
    """Classify the delta for a single metric."""
    if isinstance(base, (int, float)) and isinstance(cand, (int, float)):
        if metric in _HIGHER_IS_WORSE:
            if cand > base:
                return "regression"
            if cand < base:
                return "improvement"
        else:
            if cand < base:
                return "regression"
            if cand > base:
                return "improvement"
        return "neutral"
    if base is True and cand is False:
        return "regression"
    if base is False and cand is True:
        return "improvement"
    return "neutral"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_baseline(runs: list[tuple[str, dict[str, Any]]]) -> Baseline:
    """Record a baseline from current-Tola runs.

    runs: list of (fixture_id, observed_dict).
    Returns a frozen Baseline.
    """
    fixtures = build_all_fixtures()
    fixture_map = {f["id"]: f for f in fixtures}
    scores = []
    for fixture_id, obs in runs:
        f = fixture_map[fixture_id]
        scores.append(score_run(f, obs))
    return Baseline(
        per_fixture={s.fixture_id: s for s in scores},
        aggregate=_aggregate(scores),
        benchmark_version=BENCHMARK_VERSION,
        runs=tuple(runs),
    )


def evaluate_candidate(
    runs: list[tuple[str, dict[str, Any]]],
    baseline: Baseline,
) -> Comparison:
    """Evaluate candidate runs against a recorded baseline.

    Rules:
    - Any regression in a critical metric on any fixture forces REJECTED.
    - Non-critical regressions are listed but verdict may be REVIEW.
    - If no regressions and at least one improvement: ACCEPTED.
    - If no regressions and no improvements: REVIEW.
    Cost and latency deltas are always reported.
    """
    fixtures = build_all_fixtures()
    fixture_map = {f["id"]: f for f in fixtures}
    candidate_obs = _extract_observed(runs)

    regressions: list[Regression] = []
    improvements: list[Improvement] = []
    per_fixture: dict[str, dict[str, bool]] = {}
    total_cost_delta = 0
    total_latency_delta = 0
    total_hc_delta = 0

    for f in fixtures:
        fid = f["id"]
        fname = f["name"]
        base_score = baseline.per_fixture[fid]
        cand_obs = candidate_obs[fid]
        cand_score = score_run(f, cand_obs)

        per_fixture[fid] = tuple(sorted((k, v) for k, v in cand_score.metric_scores.items()))

        for metric in f["expected"]:
            b_val = f["expected"][metric]
            c_val = cand_obs.get(metric)
            if c_val is None:
                continue
            direction = _compare_values(metric, b_val, c_val)
            if direction == "regression":
                regressions.append(Regression(
                    fixture_id=fid,
                    fixture_name=fname,
                    metric=metric,
                    baseline_value=b_val,
                    candidate_value=c_val,
                ))
            elif direction == "improvement":
                improvements.append(Improvement(
                    fixture_id=fid,
                    fixture_name=fname,
                    metric=metric,
                    baseline_value=b_val,
                    candidate_value=c_val,
                ))

        # Accumulate deltas for cost/latency/human_correction
        total_cost_delta += cand_obs.get("token_cost", 0) - f["expected"].get("token_cost", 0)
        total_latency_delta += cand_obs.get("latency_ms", 0) - f["expected"].get("latency_ms", 0)
        total_hc_delta += cand_obs.get("human_correction", 0) - f["expected"].get("human_correction", 0)

    # Verdict logic: critical-regression override
    has_critical_regression = any(
        r.metric in REGRESSION_CRITICAL for r in regressions
    )

    if has_critical_regression:
        verdict = "REJECTED"
    elif regressions:
        verdict = "REVIEW"
    elif improvements:
        verdict = "ACCEPTED"
    else:
        verdict = "REVIEW"

    return Comparison(
        per_fixture=frozenset(per_fixture.items()),
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        verdict=verdict,
        benchmark_version=BENCHMARK_VERSION,
        cost_delta=total_cost_delta,
        latency_delta=total_latency_delta,
        human_correction_delta=total_hc_delta,
    )
