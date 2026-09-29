"""QA T20 -- Tola Performance Model tests.

Covers T20-01..T20-08 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.performance.metrics import (
    PerformanceMetrics,
    DELEGATION,
    REVIEW,
    RECOVERY,
    BRIEFING,
    ESCALATION,
    COST,
    LATENCY,
    USER_CORRECTION,
)
from tola.performance.claims import ClaimStore, MIN_SAMPLE


# ===========================================================================
# Fixtures
# ===========================================================================

TS = "2026-09-29T12:00:00"


def _build_metrics() -> PerformanceMetrics:
    """Return a metrics ledger pre-loaded with fixture events."""
    m = PerformanceMetrics()
    # 5 successful delegations (delegation ids d1..d5)
    for i in range(1, 6):
        m.record_event(DELEGATION, {
            "delegation_id": f"d{i}",
            "success": True,
            "retry_count": 0,
        }, TS)
    # 2 failed delegations (d6, d7) -- each retried once then succeeded
    m.record_event(DELEGATION, {
        "delegation_id": "d6", "success": False, "retry_count": 1,
    }, TS)
    m.record_event(DELEGATION, {
        "delegation_id": "d6", "success": True, "retry_count": 1,
    }, TS)
    m.record_event(DELEGATION, {
        "delegation_id": "d7", "success": False, "retry_count": 2,
    }, TS)
    m.record_event(DELEGATION, {
        "delegation_id": "d7", "success": True, "retry_count": 2,
    }, TS)
    # REVIEW events
    for _ in range(3):
        m.record_event(REVIEW, {"outcome": "pass"}, TS)
    # RECOVERY events
    for _ in range(2):
        m.record_event(RECOVERY, {"action": "rollback"}, TS)
    # BRIEFING events
    for _ in range(4):
        m.record_event(BRIEFING, {"topic": "standup"}, TS)
    # ESCALATION events -- 3 correct, 1 incorrect
    for _ in range(3):
        m.record_event(ESCALATION, {"correct": True}, TS)
    m.record_event(ESCALATION, {"correct": False}, TS)
    # COST events
    for amount in [10.0, 20.0, 30.0]:
        m.record_event(COST, {"amount": amount}, TS)
    # LATENCY events (ms)
    for ms in [100.0, 200.0, 300.0]:
        m.record_event(LATENCY, {"ms": ms}, TS)
    # USER_CORRECTION events
    m.record_event(USER_CORRECTION, {"delegation_id": "d1", "note": "wrong agent"}, TS)
    m.record_event(USER_CORRECTION, {"delegation_id": "d3", "note": "ambiguous scope"}, TS)
    return m


# ===========================================================================
# Tests
# ===========================================================================

class TestT20DelegationSuccess(unittest.TestCase):
    """T20-01: delegation success metric correct."""

    def test_exact_fraction(self):
        m = _build_metrics()
        # 7 successful out of 9 total DELEGATION events
        rate = m.delegation_success_rate()
        self.assertEqual(rate, 7 / 9)


class TestT20FirstPassCompletion(unittest.TestCase):
    """T20-02: first-pass completion counts delegations with zero retries."""

    def test_first_pass_count(self):
        m = _build_metrics()
        # d1..d5 have retry_count=0; d6 and d7 have retries
        fp = m.first_pass_completion()
        self.assertEqual(fp, 5 / 9)


class TestT20UserCorrection(unittest.TestCase):
    """T20-03: user correction event captured and linked."""

    def test_correction_linked_to_delegation(self):
        m = _build_metrics()
        corrections = [e for e in m.events if e.kind == USER_CORRECTION]
        self.assertEqual(len(corrections), 2)
        self.assertEqual(corrections[0].payload["delegation_id"], "d1")
        self.assertEqual(corrections[1].payload["delegation_id"], "d3")


class TestT20RetryCount(unittest.TestCase):
    """T20-04: retry count exact."""

    def test_retry_count_values(self):
        m = _build_metrics()
        self.assertEqual(m.retry_count("d1"), 0)
        self.assertEqual(m.retry_count("d6"), 1)
        self.assertEqual(m.retry_count("d7"), 2)

    def test_missing_delegation_raises(self):
        m = _build_metrics()
        with self.assertRaises(KeyError):
            m.retry_count("nonexistent")


class TestT20EscalationAccuracy(unittest.TestCase):
    """T20-05: correct and incorrect escalations counted separately."""

    def test_separate_counts(self):
        m = _build_metrics()
        acc = m.escalation_accuracy()
        self.assertEqual(acc["correct"], 3)
        self.assertEqual(acc["incorrect"], 1)


class TestT20Trend(unittest.TestCase):
    """T20-06: time-window trends return only in-window events."""

    def test_boundary_inclusive(self):
        m = PerformanceMetrics()
        m.record_event(DELEGATION, {"success": True}, "2026-09-28T10:00:00")  # before
        m.record_event(DELEGATION, {"success": True}, "2026-09-29T12:00:00")  # at start
        m.record_event(DELEGATION, {"success": False}, "2026-09-29T14:00:00")  # inside
        m.record_event(DELEGATION, {"success": True}, "2026-09-30T10:00:00")  # at end
        m.record_event(DELEGATION, {"success": True}, "2026-10-01T10:00:00")  # after

        result = m.trend(DELEGATION, "2026-09-29T12:00:00", "2026-09-30T10:00:00")
        self.assertEqual(len(result), 3)
        timestamps = [e.timestamp for e in result]
        self.assertEqual(timestamps, [
            "2026-09-29T12:00:00",
            "2026-09-29T14:00:00",
            "2026-09-30T10:00:00",
        ])

    def test_empty_window(self):
        m = _build_metrics()
        result = m.trend(DELEGATION, "2026-01-01T00:00:00", "2026-01-02T00:00:00")
        self.assertEqual(result, [])


class TestT20CostLatency(unittest.TestCase):
    """T20-07: cost and latency observable (totals/averages exact)."""

    def test_cost_total(self):
        m = _build_metrics()
        self.assertEqual(m.cost_total(), 60.0)

    def test_cost_average(self):
        m = _build_metrics()
        self.assertEqual(m.cost_average(), 20.0)

    def test_latency_total_ms(self):
        m = _build_metrics()
        self.assertEqual(m.latency_total_ms(), 600.0)

    def test_latency_average_ms(self):
        m = _build_metrics()
        self.assertEqual(m.latency_average_ms(), 200.0)


class TestT20EvidenceGate(unittest.TestCase):
    """T20-08: cannot claim strength/weakness without measured evidence."""

    def test_insufficient_samples_raises(self):
        m = PerformanceMetrics()
        store = ClaimStore(m)
        with self.assertRaises(ValueError):
            store.claim("strength", "delegation works", "DELEGATION")

    def test_sufficient_samples_stores_with_provenance(self):
        m = _build_metrics()
        store = ClaimStore(m)
        c = store.claim("strength", "delegation works", "DELEGATION")
        self.assertEqual(c.kind, "strength")
        self.assertEqual(c.metric_kind, "DELEGATION")
        self.assertEqual(c.sample_count, 9)
        self.assertIsInstance(c.metric_value, float)

    def test_list_claims_includes_provenance(self):
        m = _build_metrics()
        store = ClaimStore(m)
        store.claim("strength", "delegation works", "DELEGATION")
        claims = store.list_claims()
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].sample_count, 9)

    def test_determinism(self):
        """Same fixture produces same results every run."""
        m1 = _build_metrics()
        m2 = _build_metrics()
        self.assertEqual(m1.delegation_success_rate(), m2.delegation_success_rate())
        self.assertEqual(m1.escalation_accuracy(), m2.escalation_accuracy())
        self.assertEqual(m1.cost_total(), m2.cost_total())


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main()