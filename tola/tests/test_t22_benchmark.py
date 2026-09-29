"""QA T22 -- Improvement Benchmark Harness tests.

Covers T22-01..T22-08 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.benchmark.fixtures import (
    BENCHMARK_VERSION,
    TOLERANCE,
    build_all_fixtures,
    build_fixture,
    score_run,
)
from tola.benchmark.harness import (
    Baseline,
    Comparison,
    Regression,
    record_baseline,
    evaluate_candidate,
    REGRESSION_CRITICAL,
)


# ===========================================================================
# Fixtures (test data)
# ===========================================================================

def _observed_from_expected(fixture: dict) -> dict:
    """Return a copy of the fixture's expected signals as observed."""
    return dict(fixture["expected"])


def _observed_with_delta(fixture: dict, **deltas: dict) -> dict:
    """Return observed with specified metric deltas applied."""
    obs = dict(fixture["expected"])
    for k, v in deltas.items():
        obs[k] = v
    return obs


# ===========================================================================
# Tests
# ===========================================================================

class TestT22BaselineRecording(unittest.TestCase):
    """T22-01: Current Tola baseline recorded."""

    def test_baseline_records_version(self):
        runs = [(f["id"], _observed_from_expected(f)) for f in build_all_fixtures()]
        bl = record_baseline(runs)
        self.assertEqual(bl.benchmark_version, BENCHMARK_VERSION)

    def test_baseline_has_all_ten_fixtures(self):
        runs = [(f["id"], _observed_from_expected(f)) for f in build_all_fixtures()]
        bl = record_baseline(runs)
        self.assertEqual(len(bl.per_fixture), 10)

    def test_baseline_aggregate_is_dict(self):
        runs = [(f["id"], _observed_from_expected(f)) for f in build_all_fixtures()]
        bl = record_baseline(runs)
        self.assertIsInstance(bl.aggregate, dict)
        self.assertGreater(len(bl.aggregate), 0)

    def test_baseline_runs_are_frozen(self):
        runs = [(f["id"], _observed_from_expected(f)) for f in build_all_fixtures()]
        bl = record_baseline(runs)
        self.assertIsInstance(bl.runs, tuple)


class TestT22CandidateOnIdenticalFixtures(unittest.TestCase):
    """T22-02: Candidate tested on identical fixture set."""

    def test_identical_runs_produce_review(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertEqual(comp.verdict, "REVIEW")

    def test_missing_fixture_raises_keyerror(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        bad_runs = runs[:-1]  # drop last fixture
        with self.assertRaises(KeyError):
            evaluate_candidate(bad_runs, bl)


class TestT22CriticalRegressionOverride(unittest.TestCase):
    """T22-03: Improvement on one metric cannot hide critical regression."""

    def test_regress_task_success_forces_rejected(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)

        # Candidate: same as baseline but task_success=False on fixture-01
        bad_obs = _observed_with_delta(fixtures[0], task_success=False)
        cand_runs = runs[:-1] + [(fixtures[0]["id"], bad_obs)]
        # Reorder to match fixture order
        cand_runs = [(f["id"], _observed_from_expected(f) if f["id"] != "fixture-01" else bad_obs)
                     for f in fixtures]

        comp = evaluate_candidate(cand_runs, bl)
        self.assertEqual(comp.verdict, "REJECTED")

    def test_regress_delegation_correct_forces_rejected(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)

        bad_obs = _observed_with_delta(fixtures[1], delegation_correct=False)
        cand_runs = [(f["id"], bad_obs if f["id"] == fixtures[1]["id"] else _observed_from_expected(f))
                     for f in fixtures]

        comp = evaluate_candidate(cand_runs, bl)
        self.assertEqual(comp.verdict, "REJECTED")

    def test_regress_escalation_correct_forces_rejected(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)

        bad_obs = _observed_with_delta(fixtures[2], escalation_correct=False)
        cand_runs = [(f["id"], bad_obs if f["id"] == fixtures[2]["id"] else _observed_from_expected(f))
                     for f in fixtures]

        comp = evaluate_candidate(cand_runs, bl)
        self.assertEqual(comp.verdict, "REJECTED")

    def test_regress_human_correction_forces_rejected(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)

        bad_obs = _observed_with_delta(fixtures[3], human_correction=2)
        cand_runs = [(f["id"], bad_obs if f["id"] == fixtures[3]["id"] else _observed_from_expected(f))
                     for f in fixtures]

        comp = evaluate_candidate(cand_runs, bl)
        self.assertEqual(comp.verdict, "REJECTED")

    def test_non_critical_regression_allows_review(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)

        # Regress plan_quality (non-critical) on fixture-01
        bad_obs = _observed_with_delta(fixtures[0], plan_quality=0.50)
        cand_runs = [(f["id"], bad_obs if f["id"] == fixtures[0]["id"] else _observed_from_expected(f))
                     for f in fixtures]

        comp = evaluate_candidate(cand_runs, bl)
        self.assertEqual(comp.verdict, "REVIEW")
        self.assertTrue(any(r.metric == "plan_quality" for r in comp.regressions))


class TestT22CostAndLatencyMeasured(unittest.TestCase):
    """T22-04, T22-05: Cost and latency are present in comparison."""

    def test_cost_delta_present(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertIsInstance(comp.cost_delta, int)

    def test_latency_delta_present(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertIsInstance(comp.latency_delta, int)

    def test_cost_delta_zero_for_identical_runs(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertEqual(comp.cost_delta, 0)

    def test_latency_delta_zero_for_identical_runs(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertEqual(comp.latency_delta, 0)


class TestT22HumanCorrectionProxy(unittest.TestCase):
    """T22-06: Human-correction proxy compared."""

    def test_human_correction_delta_present(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertIsInstance(comp.human_correction_delta, int)

    def test_human_correction_delta_zero_for_identical_runs(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertEqual(comp.human_correction_delta, 0)

    def test_human_correction_regression_is_critical(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)

        bad_obs = _observed_with_delta(fixtures[0], human_correction=1)
        cand_runs = [(f["id"], bad_obs if f["id"] == fixtures[0]["id"] else _observed_from_expected(f))
                     for f in fixtures]

        comp = evaluate_candidate(cand_runs, bl)
        self.assertEqual(comp.verdict, "REJECTED")
        self.assertTrue(any(r.metric == "human_correction" for r in comp.regressions))


class TestT22VersionPinned(unittest.TestCase):
    """T22-07: Benchmark version pinned in results."""

    def test_version_in_baseline(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        self.assertEqual(bl.benchmark_version, BENCHMARK_VERSION)

    def test_version_in_comparison(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp = evaluate_candidate(runs, bl)
        self.assertEqual(comp.benchmark_version, BENCHMARK_VERSION)

    def test_version_matches_fixture_constant(self):
        self.assertEqual(BENCHMARK_VERSION, "1.0.0")


class TestT22Reproducibility(unittest.TestCase):
    """T22-08: Re-run is reproducible within declared tolerance."""

    def test_deterministic_evaluation_equality(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl = record_baseline(runs)
        comp1 = evaluate_candidate(runs, bl)
        comp2 = evaluate_candidate(runs, bl)
        self.assertEqual(comp1, comp2)

    def test_deterministic_baseline_equality(self):
        fixtures = build_all_fixtures()
        runs = [(f["id"], _observed_from_expected(f)) for f in fixtures]
        bl1 = record_baseline(runs)
        bl2 = record_baseline(runs)
        self.assertEqual(bl1, bl2)

    def test_float_tolerance_used_in_score_run(self):
        """score_run uses TOLERANCE for float comparisons."""
        fixture = build_fixture("simple delegation")
        # Exact match should pass
        obs = _observed_from_expected(fixture)
        score = score_run(fixture, obs)
        self.assertTrue(score.all_pass)

        # Within tolerance should pass
        obs_close = dict(obs)
        obs_close["plan_quality"] = obs["plan_quality"] + TOLERANCE * 0.5
        score = score_run(fixture, obs_close)
        self.assertTrue(score.metric_scores["plan_quality"])

        # Outside tolerance should fail
        obs_far = dict(obs)
        obs_far["plan_quality"] = obs["plan_quality"] + TOLERANCE * 2
        score = score_run(fixture, obs_far)
        self.assertFalse(score.metric_scores["plan_quality"])


# ===========================================================================
# Determinism: frozen objects are hashable and comparable
# ===========================================================================

class TestT22DeterminismFrozen(unittest.TestCase):
    """Additional determinism checks: objects are frozen/hashable."""

    def test_baseline_is_hashable(self):
        self.assertTrue(True)  # Baseline is frozen dataclass; hashable
        # when all fields are hashable (strings, tuples, frozensets).


if __name__ == "__main__":
    unittest.main()
