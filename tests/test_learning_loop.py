"""Batch 10 QA tests for learning_loop.py.

Covers: record_outcome (completed, partial, skipped, estimation error,
fatigue mismatch), summarise aggregation, advisory-only guard
(summary cannot mutate capacity constants).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.daily_synthesis.learning_loop import (
    DEFAULT_CAPACITY_TOTAL_MINUTES,
    DEFAULT_RECOVERY_BUFFER_MINUTES,
    ExecutionRecord,
    MAX_MAJOR_OUTCOMES,
    OutcomeStatus,
    TrendSummary,
    record_outcome,
    summarise,
)
from agents.daily_synthesis.contracts import ValidationError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _brief(**overrides):
    defaults = dict(
        schema_version="daily_command_brief.v1",
        top_outcomes=[
            {"estimated_minutes": 30, "definition_of_done": "do X"},
            {"estimated_minutes": 20, "definition_of_done": "do Y"},
        ],
    )
    defaults.update(overrides)
    return defaults


def _record(**overrides):
    defaults = dict(
        domain="scholar",
        planned_minutes=30,
        actual_minutes=30,
        status="completed",
        fatigue_energy_predicted="medium",
        fatigue_energy_actual="medium",
        capacity_predicted_minutes=50,
        capacity_actual_available_minutes=60,
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# 1. Completed outcome
# ---------------------------------------------------------------------------

class CompletedOutcomeTest(unittest.TestCase):
    def test_completed_record_outcome(self):
        brief = _brief()
        records = [_record(status="completed", actual_minutes=28)]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.completion_rate, 1.0)
        self.assertEqual(result.estimation_error_minutes, 22)  # 50 - 28
        self.assertEqual(len(result.partial_reasons), 0)
        self.assertEqual(len(result.skip_reasons), 0)

    def test_all_completed_perfect_estimate(self):
        brief = _brief()
        records = [
            _record(status="completed", actual_minutes=30, domain="scholar"),
            _record(status="completed", actual_minutes=20, domain="growth"),
        ]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.completion_rate, 1.0)
        self.assertEqual(result.estimation_error_minutes, 0)


# ---------------------------------------------------------------------------
# 2. Partial with reason
# ---------------------------------------------------------------------------

class PartialOutcomeTest(unittest.TestCase):
    def test_partial_with_reason(self):
        brief = _brief()
        records = [_record(status="partial", reason="interruption", actual_minutes=15)]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.completion_rate, 0.0)
        self.assertEqual(len(result.partial_reasons), 1)
        self.assertIn("interruption", result.partial_reasons[0])

    def test_multiple_partials(self):
        brief = _brief()
        records = [
            _record(status="partial", reason="interruption", actual_minutes=10),
            _record(status="partial", reason="fatigue", actual_minutes=5),
        ]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.completion_rate, 0.0)
        self.assertEqual(len(result.partial_reasons), 2)


# ---------------------------------------------------------------------------
# 3. Skipped
# ---------------------------------------------------------------------------

class SkippedOutcomeTest(unittest.TestCase):
    def test_skipped_with_reason(self):
        brief = _brief()
        records = [_record(status="skipped", reason="blocked by dependency", actual_minutes=0)]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.completion_rate, 0.0)
        self.assertEqual(len(result.skip_reasons), 1)
        self.assertIn("blocked", result.skip_reasons[0])

    def test_multiple_skips(self):
        brief = _brief()
        records = [
            _record(status="skipped", reason="blocked", actual_minutes=0),
            _record(status="skipped", reason="no capacity", actual_minutes=0),
            _record(status="completed", actual_minutes=25),
        ]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertAlmostEqual(result.completion_rate, 1 / 3, places=2)
        self.assertEqual(len(result.skip_reasons), 2)


# ---------------------------------------------------------------------------
# 4. Estimation error positive and negative
# ---------------------------------------------------------------------------

class EstimationErrorTest(unittest.TestCase):
    def test_positive_error_over_estimated(self):
        brief = _brief()
        records = [_record(status="completed", actual_minutes=10)]  # planned 50, actual 10
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertGreater(result.estimation_error_minutes, 0)
        self.assertEqual(result.estimation_error_minutes, 40)

    def test_negative_error_under_estimated(self):
        brief = _brief()
        records = [_record(status="completed", actual_minutes=60)]  # planned 50, actual 60
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertLess(result.estimation_error_minutes, 0)
        self.assertEqual(result.estimation_error_minutes, -10)


# ---------------------------------------------------------------------------
# 5. Fatigue mismatch flagged
# ---------------------------------------------------------------------------

class FatigueMismatchTest(unittest.TestCase):
    def test_fatigue_mismatch_flagged(self):
        brief = _brief()
        records = [_record(
            status="completed",
            fatigue_energy_predicted="deep",
            fatigue_energy_actual="low",
        )]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(len(result.fatigue_mismatches), 1)
        self.assertIn("deep", result.fatigue_mismatches[0])
        self.assertIn("low", result.fatigue_mismatches[0])

    def test_no_fatigue_mismatch(self):
        brief = _brief()
        records = [_record(
            status="completed",
            fatigue_energy_predicted="medium",
            fatigue_energy_actual="medium",
        )]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(len(result.fatigue_mismatches), 0)


# ---------------------------------------------------------------------------
# 6. Aggregation across several days
# ---------------------------------------------------------------------------

class AggregationTest(unittest.TestCase):
    def test_summarise_across_days(self):
        day1 = [
            ExecutionRecord(domain="scholar", planned_minutes=30, actual_minutes=25, status="completed", fatigue_energy_predicted="medium", fatigue_energy_actual="medium"),
            ExecutionRecord(domain="growth", planned_minutes=20, actual_minutes=20, status="completed", fatigue_energy_predicted="medium", fatigue_energy_actual="medium"),
        ]
        day2 = [
            ExecutionRecord(domain="scholar", planned_minutes=30, actual_minutes=35, status="completed", fatigue_energy_predicted="medium", fatigue_energy_actual="medium"),
            ExecutionRecord(domain="scholar", planned_minutes=15, actual_minutes=10, status="partial", reason="time ran out", fatigue_energy_predicted="medium", fatigue_energy_actual="medium"),
        ]
        day3 = [
            ExecutionRecord(domain="growth", planned_minutes=20, actual_minutes=0, status="skipped", reason="blocked", fatigue_energy_predicted="medium", fatigue_energy_actual="medium"),
        ]
        summary = summarise([day1, day2, day3])

        # Average estimation error by domain
        self.assertIn("scholar", summary.avg_estimation_error_by_domain)
        self.assertIn("growth", summary.avg_estimation_error_by_domain)

        # Most common skip reasons
        self.assertIn("blocked", summary.most_common_skip_reasons)

        # Over/under planning frequencies
        self.assertGreaterEqual(summary.over_planning_frequency, 0.0)
        self.assertGreaterEqual(summary.under_planning_frequency, 0.0)

    def test_empty_days(self):
        summary = summarise([])
        self.assertEqual(summary.advisory_note, "No data available")

    def test_empty_day_records(self):
        summary = summarise([[]])
        self.assertEqual(summary.advisory_note, "No records to summarise")


# ---------------------------------------------------------------------------
# 7. Advisory-only guard — constants unchanged after summarise
# ---------------------------------------------------------------------------

class AdvisoryOnlyGuardTest(unittest.TestCase):
    def test_constants_unchanged_after_summarise(self):
        before_max = MAX_MAJOR_OUTCOMES
        before_buffer = DEFAULT_RECOVERY_BUFFER_MINUTES
        before_capacity = DEFAULT_CAPACITY_TOTAL_MINUTES

        day1 = [
            ExecutionRecord(domain="scholar", planned_minutes=30, actual_minutes=25, status="completed", fatigue_energy_predicted="medium", fatigue_energy_actual="medium"),
        ]
        summarise([day1])

        self.assertEqual(MAX_MAJOR_OUTCOMES, before_max)
        self.assertEqual(DEFAULT_RECOVERY_BUFFER_MINUTES, before_buffer)
        self.assertEqual(DEFAULT_CAPACITY_TOTAL_MINUTES, before_capacity)

    def test_summarise_returns_advisory_note(self):
        day1 = [ExecutionRecord(domain="scholar", planned_minutes=30, actual_minutes=25, status="completed", fatigue_energy_predicted="medium", fatigue_energy_actual="medium")]
        summary = summarise([day1])
        self.assertIsInstance(summary, TrendSummary)
        self.assertIn("advisory", summary.advisory_note.lower())


# ---------------------------------------------------------------------------
# 8. Schema validation
# ---------------------------------------------------------------------------

class SchemaValidationTest(unittest.TestCase):
    def test_valid_record_passes(self):
        rec = ExecutionRecord(
            domain="scholar",
            planned_minutes=30,
            actual_minutes=25,
            status="completed",
            fatigue_energy_predicted="medium",
            fatigue_energy_actual="medium",
        )
        result = rec.validate()
        self.assertEqual(result["domain"], "scholar")

    def test_invalid_status_raises(self):
        rec = ExecutionRecord(
            domain="scholar",
            planned_minutes=30,
            actual_minutes=25,
            status="unknown_status",
            fatigue_energy_predicted="medium",
            fatigue_energy_actual="medium",
        )
        with self.assertRaises(ValidationError):
            rec.validate()

    def test_negative_planned_minutes_raises(self):
        rec = ExecutionRecord(
            domain="scholar",
            planned_minutes=-5,
            actual_minutes=25,
            status="completed",
            fatigue_energy_predicted="medium",
            fatigue_energy_actual="medium",
        )
        with self.assertRaises(ValidationError):
            rec.validate()

    def test_invalid_fatigue_energy_raises(self):
        rec = ExecutionRecord(
            domain="scholar",
            planned_minutes=30,
            actual_minutes=25,
            status="completed",
            fatigue_energy_predicted="extreme",
            fatigue_energy_actual="medium",
        )
        with self.assertRaises(ValidationError):
            rec.validate()


# ---------------------------------------------------------------------------
# 9. Capacity predicted vs actual-available
# ---------------------------------------------------------------------------

class CapacityAvailabilityTest(unittest.TestCase):
    def test_capacity_delta_computed(self):
        brief = _brief()
        records = [
            _record(
                status="completed",
                capacity_predicted_minutes=50,
                capacity_actual_available_minutes=40,
            ),
            _record(
                status="completed",
                domain="growth",
                capacity_predicted_minutes=30,
                capacity_actual_available_minutes=35,
            ),
        ]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.capacity_predicted, 80)
        self.assertEqual(result.capacity_actual_available, 75)
        self.assertEqual(result.capacity_delta, 5)

    def test_capacity_mismatch_flagged(self):
        brief = _brief()
        records = [_record(
            status="completed",
            capacity_predicted_minutes=100,
            capacity_actual_available_minutes=30,
        )]
        result = record_outcome(brief, records, "2026-10-03T09:00:00+00:00")
        self.assertEqual(result.capacity_delta, 70)


if __name__ == "__main__":
    unittest.main()
