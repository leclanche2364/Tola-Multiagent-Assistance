# Batch T30 -- Controlled Tola Pilot tests.
# QA T30: 15 tracked metrics, required scenarios, determinism, pass/fail.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

import unittest

from tola.pilot.scenarios import (
    PILOT_SCENARIOS,
    PILOT_VERSION,
    ALL_METRICS,
    CRITICAL_METRICS,
    METRIC_DELEGATION_ACCURACY,
    METRIC_FIRST_PASS_COMPLETION,
    METRIC_PARTIAL_RATE,
    METRIC_BLOCKED_RATE,
    METRIC_STALLED_RECOVERY,
    METRIC_INCORRECT_ESCALATION,
    METRIC_MISSED_MATERIAL_EVENTS,
    METRIC_USER_CORRECTION_RATE,
    METRIC_PLAN_REVISION_RATE,
    METRIC_BRIEFING_USEFULNESS,
    METRIC_NOTIFICATION_NOISE,
    METRIC_PREFERENCE_ACCURACY,
    METRIC_PROPOSAL_QUALITY,
    METRIC_COST,
    METRIC_LATENCY,
)
from tola.pilot.metrics import (
    score_pilot,
    evaluate_pilot,
    PilotScorecard,
    PilotVerdict,
)
from tola.pilot.pilot import run_pilot, PilotReport


NOW = "2026-09-29T12:00:00"

# Required scenario IDs from QA T30 testing plan.
REQUIRED_SCENARIO_IDS = frozenset([
    "MULTI_PROJECT",
    "CAPACITY_CONFLICT",
    "PLAN_CRITIQUE",
    "STALLED_TASK",
    "PARTIAL_OUTPUT",
    "USER_CORRECTION",
    "EXPLICIT_PREFERENCE",
    "REPEATED_INFERRED_PREFERENCE",
    "MATERIAL_EVENT",
    "QUIET_HEARTBEAT",
    "WEEKLY_REVIEW",
    "IMPROVEMENT_PROPOSAL",
])


# ===========================================================================
# Metric tracking tests
# ===========================================================================

class TestT30_MetricTracking(unittest.TestCase):
    """All 15 metrics are tracked and named as constants."""

    def test_all_15_metrics_named(self):
        self.assertEqual(len(ALL_METRICS), 15)

    def test_delegation_accuracy_named(self):
        self.assertIn(METRIC_DELEGATION_ACCURACY, ALL_METRICS)

    def test_first_pass_completion_named(self):
        self.assertIn(METRIC_FIRST_PASS_COMPLETION, ALL_METRICS)

    def test_partial_rate_named(self):
        self.assertIn(METRIC_PARTIAL_RATE, ALL_METRICS)

    def test_blocked_rate_named(self):
        self.assertIn(METRIC_BLOCKED_RATE, ALL_METRICS)

    def test_stalled_recovery_named(self):
        self.assertIn(METRIC_STALLED_RECOVERY, ALL_METRICS)

    def test_incorrect_escalation_named(self):
        self.assertIn(METRIC_INCORRECT_ESCALATION, ALL_METRICS)

    def test_missed_material_events_named(self):
        self.assertIn(METRIC_MISSED_MATERIAL_EVENTS, ALL_METRICS)

    def test_user_correction_rate_named(self):
        self.assertIn(METRIC_USER_CORRECTION_RATE, ALL_METRICS)

    def test_plan_revision_rate_named(self):
        self.assertIn(METRIC_PLAN_REVISION_RATE, ALL_METRICS)

    def test_briefing_usefulness_named(self):
        self.assertIn(METRIC_BRIEFING_USEFULNESS, ALL_METRICS)

    def test_notification_noise_named(self):
        self.assertIn(METRIC_NOTIFICATION_NOISE, ALL_METRICS)

    def test_preference_accuracy_named(self):
        self.assertIn(METRIC_PREFERENCE_ACCURACY, ALL_METRICS)

    def test_proposal_quality_named(self):
        self.assertIn(METRIC_PROPOSAL_QUALITY, ALL_METRICS)

    def test_cost_named(self):
        self.assertIn(METRIC_COST, ALL_METRICS)

    def test_latency_named(self):
        self.assertIn(METRIC_LATENCY, ALL_METRICS)


# ===========================================================================
# Scenario presence tests
# ===========================================================================

class TestT30_ScenarioPresence(unittest.TestCase):
    """Every required scenario is present and executable."""

    def test_required_scenario_ids_present(self):
        scenario_ids = {s["id"] for s in PILOT_SCENARIOS}
        missing = REQUIRED_SCENARIO_IDS - scenario_ids
        self.assertEqual(missing, set(), f"Missing scenarios: {missing}")

    def test_scenario_count_at_least_9(self):
        self.assertGreaterEqual(len(PILOT_SCENARIOS), 9)

    def test_all_scenarios_have_inputs_and_expected(self):
        for s in PILOT_SCENARIOS:
            self.assertIn("inputs", s, f"{s['id']} missing inputs")
            self.assertIn("expected", s, f"{s['id']} missing expected")

    def test_scenario_ids_are_ascii(self):
        for s in PILOT_SCENARIOS:
            self.assertEqual(s["id"], s["id"].encode("ascii").decode("ascii"))

    def test_scenario_names_are_ascii(self):
        for s in PILOT_SCENARIOS:
            self.assertEqual(s["name"], s["name"].encode("ascii").decode("ascii"))

    def test_pilot_version_constant(self):
        self.assertIsInstance(PILOT_VERSION, str)
        self.assertTrue(len(PILOT_VERSION) > 0)


# ===========================================================================
# Determinism tests
# ===========================================================================

class TestT30_Determinism(unittest.TestCase):
    """Pilot run twice produces identical scorecards."""

    def test_two_runs_identical_scorecards(self):
        r1 = run_pilot(NOW, runs=2)
        r2 = run_pilot(NOW, runs=2)
        self.assertEqual(
            r1.scorecard.aggregates,
            r2.scorecard.aggregates,
        )

    def test_two_runs_identical_verdict(self):
        r1 = run_pilot(NOW, runs=2)
        r2 = run_pilot(NOW, runs=2)
        self.assertEqual(r1.verdict.verdict, r2.verdict.verdict)

    def test_two_runs_identical_reasons(self):
        r1 = run_pilot(NOW, runs=2)
        r2 = run_pilot(NOW, runs=2)
        self.assertEqual(r1.verdict.reasons, r2.verdict.reasons)

    def test_score_pilot_deterministic(self):
        r = run_pilot(NOW, runs=2)
        results = r.run_results[0]
        sc1 = score_pilot(results)
        sc2 = score_pilot(results)
        self.assertEqual(sc1.aggregates, sc2.aggregates)
        for ss1, ss2 in zip(sc1.scenario_scores, sc2.scenario_scores):
            self.assertEqual(ss1.metric_scores, ss2.metric_scores)


# ===========================================================================
# Baseline workload pass test
# ===========================================================================

class TestT30_BaselinePass(unittest.TestCase):
    """Baseline workload (no injected failures) should PASS."""

    def test_baseline_passes(self):
        r = run_pilot(NOW, runs=2)
        self.assertEqual(r.verdict.verdict, "PASS")

    def test_baseline_zero_critical_failures(self):
        r = run_pilot(NOW, runs=2)
        for reason in r.verdict.reasons:
            self.assertNotIn("Critical failure", reason)


# ===========================================================================
# Injected critical failure test
# ===========================================================================

class TestT30_InjectedCriticalFailure(unittest.TestCase):
    """An injected critical failure (incorrect escalation) forces FAIL."""

    def test_injected_incorrect_escalation_fails(self):
        # Inject a critical failure by scoring a scenario where
        # incorrect_escalation is expected=True but the outcome
        # reports it as a failure (score 0.0).
        from tola.pilot.metrics import (
            score_pilot,
            evaluate_pilot,
            PilotScorecard,
            ScenarioScores,
            ALL_METRICS,
            METRIC_INCORRECT_ESCALATION,
        )
        sid = "INJECTED_ESCALATION_FAILURE"
        # All metrics 1.0 except incorrect_escalation = 0.0 (critical failure)
        bad_scores = {m: 1.0 for m in ALL_METRICS}
        bad_scores[METRIC_INCORRECT_ESCALATION] = 0.0
        ss = ScenarioScores(scenario_id=sid, metric_scores=bad_scores)
        scorecard = PilotScorecard(
            run_index=0,
            scenario_scores=(ss,),
            aggregates={m: (0.0 if m == METRIC_INCORRECT_ESCALATION else 1.0) for m in ALL_METRICS},
        )
        verdict = evaluate_pilot(scorecard, runs=1)
        self.assertEqual(verdict.verdict, "FAIL")
        self.assertTrue(
            any("incorrect_escalation" in r for r in verdict.reasons)
        )


# ===========================================================================
# Cost and latency aggregates test
# ===========================================================================

class TestT30_CostAndLatency(unittest.TestCase):
    """Cost and latency aggregates are present and finite."""

    def test_cost_aggregate_present(self):
        r = run_pilot(NOW, runs=2)
        self.assertIn(METRIC_COST, r.scorecard.aggregates)

    def test_latency_aggregate_present(self):
        r = run_pilot(NOW, runs=2)
        self.assertIn(METRIC_LATENCY, r.scorecard.aggregates)

    def test_cost_aggregate_finite(self):
        r = run_pilot(NOW, runs=2)
        cost = r.scorecard.aggregates[METRIC_COST]
        self.assertIsInstance(cost, (int, float))
        self.assertFalse(cost != cost)  # not NaN

    def test_latency_aggregate_finite(self):
        r = run_pilot(NOW, runs=2)
        latency = r.scorecard.aggregates[METRIC_LATENCY]
        self.assertIsInstance(latency, (int, float))
        self.assertFalse(latency != latency)  # not NaN


# ===========================================================================
# Notification noise test
# ===========================================================================

class TestT30_NotificationNoise(unittest.TestCase):
    """Notification noise is counted from actual wake/message outputs."""

    def test_notification_noise_aggregate_present(self):
        r = run_pilot(NOW, runs=2)
        self.assertIn(METRIC_NOTIFICATION_NOISE, r.scorecard.aggregates)

    def test_notification_noise_is_numeric(self):
        r = run_pilot(NOW, runs=2)
        noise = r.scorecard.aggregates[METRIC_NOTIFICATION_NOISE]
        self.assertIsInstance(noise, (int, float))


# ===========================================================================
# Critical metrics rule test
# ===========================================================================

class TestT30_CriticalMetricsRule(unittest.TestCase):
    """A critical failure on any run forces FAIL with reason."""

    def test_critical_metrics_frozenset(self):
        self.assertIsInstance(CRITICAL_METRICS, frozenset)
        self.assertGreaterEqual(len(CRITICAL_METRICS), 3)

    def test_critical_failure_forces_fail(self):
        # Score a pilot where a critical metric is 0.0
        from tola.pilot.metrics import PilotScorecard, ScenarioScores
        sid = "TEST_SCENARIO"
        bad_scores = {m: 0.0 for m in ALL_METRICS}
        bad_scores[METRIC_INCORRECT_ESCALATION] = 0.0
        ss = ScenarioScores(scenario_id=sid, metric_scores=bad_scores)
        scorecard = PilotScorecard(
            run_index=0,
            scenario_scores=(ss,),
            aggregates={m: 0.0 for m in ALL_METRICS},
        )
        verdict = evaluate_pilot(scorecard, runs=1)
        self.assertEqual(verdict.verdict, "FAIL")
        self.assertTrue(len(verdict.reasons) > 0)
        self.assertTrue(
            any("incorrect_escalation" in r for r in verdict.reasons)
        )


# ===========================================================================
# Report structure test
# ===========================================================================

class TestT30_ReportStructure(unittest.TestCase):
    """PilotReport has all required fields."""

    def test_report_has_pilot_version(self):
        r = run_pilot(NOW, runs=2)
        self.assertEqual(r.pilot_version, "T30.0.0")

    def test_report_has_now_iso(self):
        r = run_pilot(NOW, runs=2)
        self.assertEqual(r.now_iso, NOW)

    def test_report_has_runs(self):
        r = run_pilot(NOW, runs=2)
        self.assertEqual(r.runs, 2)

    def test_report_has_scorecard(self):
        r = run_pilot(NOW, runs=2)
        self.assertIsInstance(r.scorecard, PilotScorecard)

    def test_report_has_verdict(self):
        r = run_pilot(NOW, runs=2)
        self.assertIsInstance(r.verdict, PilotVerdict)

    def test_report_has_run_results(self):
        r = run_pilot(NOW, runs=2)
        self.assertEqual(len(r.run_results), 2)


# ===========================================================================
# Scenario executability test
# ===========================================================================

class TestT30_ScenarioExecutability(unittest.TestCase):
    """Every scenario can be replayed without error."""

    def test_all_scenarios_executable(self):
        from tola.pilot.pilot import _replay_scenario
        for scenario in PILOT_SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                outcome = _replay_scenario(scenario)
                self.assertIsInstance(outcome, dict)
                self.assertNotIn("error", outcome)


if __name__ == "__main__":
    unittest.main()