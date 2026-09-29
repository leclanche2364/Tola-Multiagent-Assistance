# QA T15 tests -- Decision Register.
# Stdlib only. Plain ASCII. Deterministic.

import unittest
from dataclasses import replace as dc_replace

from tola.decisions.register import (
    DecisionRecord,
    register_decision,
    supersede_decision,
)
from tola.decisions.review import (
    due_reviews,
    check_revisit_triggers,
)
from tola.decisions.explain import explain_decision


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _active_record() -> DecisionRecord:
    return DecisionRecord(
        decision="Use async I/O for report generation",
        reason="Sync I/O blocks the event loop during large exports",
        evidence="Benchmark shows 3x throughput improvement on 10k-row exports",
        alternatives="Batch sync writes; stream with backpressure",
        tradeoff="Added complexity in error handling vs throughput gain",
        owner="tola-build",
        date="2026-09-29",
        expected_outcome="Report generation completes within SLA",
        review_date="2026-12-01T00:00:00Z",
        revisit_trigger={"kind": "METRIC_BELOW", "name": "export_throughput", "threshold": 500},
        id="DEC-ACTIVE-001",
    )


def _superseded_record() -> DecisionRecord:
    return DecisionRecord(
        decision="Use sync I/O for report generation",
        reason="Simpler code path for small exports",
        evidence="Works for under 1k rows",
        alternatives="Async I/O; batch sync writes",
        tradeoff="Lower throughput for simpler code",
        owner="tola-build",
        date="2026-09-01",
        expected_outcome="Report generation works for small datasets",
        review_date=None,
        revisit_trigger=None,
        id="DEC-OLD-001",
        superseded_by="DEC-ACTIVE-001",
    )


def _make_register() -> dict:
    reg = {}
    active = _active_record()
    superseded = _superseded_record()
    reg[active.id] = active
    reg[superseded.id] = superseded
    return reg


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestT15DecisionRegister(unittest.TestCase):
    """QA T15 -- Decision Register test suite."""

    # T15-01: Decision captures reason/evidence/tradeoff.
    def test_t15_01_decision_captures_reason_evidence_tradeoff(self):
        rec = _active_record()
        self.assertEqual(rec.reason, "Sync I/O blocks the event loop during large exports")
        self.assertEqual(rec.evidence, "Benchmark shows 3x throughput improvement on 10k-row exports")
        self.assertEqual(rec.tradeoff, "Added complexity in error handling vs throughput gain")

    # T15-01 continued: incomplete decision rejected.
    def test_t15_01_incomplete_decision_rejected(self):
        incomplete = DecisionRecord(
            decision="",
            reason="",
            evidence="",
            alternatives="",
            tradeoff="",
            owner="",
            date="",
            expected_outcome="",
        )
        with self.assertRaises(ValueError):
            register_decision(incomplete)

    # T15-02: Review date surfaces exactly when due.
    def test_t15_02_review_date_before_due(self):
        reg = _make_register()
        result = due_reviews(reg, "2026-11-15T00:00:00Z")
        self.assertEqual(len(result), 0)

    def test_t15_02_review_date_at_due(self):
        reg = _make_register()
        result = due_reviews(reg, "2026-12-01T00:00:00Z")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "DEC-ACTIVE-001")

    def test_t15_02_review_date_after_due(self):
        reg = _make_register()
        result = due_reviews(reg, "2027-01-15T00:00:00Z")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "DEC-ACTIVE-001")

    # T15-03: Revisit trigger activates correctly.
    def test_t15_03_revisit_trigger_match(self):
        reg = _make_register()
        context = {"metrics": {"export_throughput": 300}}
        result = check_revisit_triggers(reg, context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "DEC-ACTIVE-001")

    def test_t15_03_revisit_trigger_no_match(self):
        reg = _make_register()
        context = {"metrics": {"export_throughput": 800}}
        result = check_revisit_triggers(reg, context)
        self.assertEqual(len(result), 0)

    def test_t15_03_revisit_trigger_health_label(self):
        rec = DecisionRecord(
            decision="Route to specialist",
            reason="Health label indicates degraded",
            evidence="Health probe returned DEGRADED",
            alternatives="Continue as-is; circuit break",
            tradeoff="Availability vs complexity",
            owner="tola-build",
            date="2026-09-29",
            expected_outcome="Degraded path isolated",
            review_date=None,
            revisit_trigger={"kind": "HEALTH_LABEL", "project_id": "proj-x", "equals": "DEGRADED"},
            id="DEC-HEALTH-001",
        )
        reg = {rec.id: rec}
        context = {"health_label": "DEGRADED", "project_id": "proj-x"}
        result = check_revisit_triggers(reg, context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "DEC-HEALTH-001")

    def test_t15_03_revisit_trigger_event_occurred(self):
        rec = DecisionRecord(
            decision="Escalate on failure",
            reason="Failure events need human review",
            evidence="Three failures in one hour",
            alternatives="Auto-retry; ignore",
            tradeoff="Response time vs noise",
            owner="tola-build",
            date="2026-09-29",
            expected_outcome="Failures reviewed within SLA",
            review_date=None,
            revisit_trigger={"kind": "EVENT_OCCURRED", "name": "critical_failure"},
            id="DEC-EVENT-001",
        )
        reg = {rec.id: rec}
        context = {"events": ["critical_failure", "warning"]}
        result = check_revisit_triggers(reg, context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "DEC-EVENT-001")

    def test_t15_03_revisit_trigger_event_no_match(self):
        rec = DecisionRecord(
            decision="Escalate on failure",
            reason="Failure events need human review",
            evidence="Three failures in one hour",
            alternatives="Auto-retry; ignore",
            tradeoff="Response time vs noise",
            owner="tola-build",
            date="2026-09-29",
            expected_outcome="Failures reviewed within SLA",
            review_date=None,
            revisit_trigger={"kind": "EVENT_OCCURRED", "name": "critical_failure"},
            id="DEC-EVENT-001",
        )
        reg = {rec.id: rec}
        context = {"events": ["warning", "info"]}
        result = check_revisit_triggers(reg, context)
        self.assertEqual(len(result), 0)

    def test_t15_03_unknown_trigger_kind_rejected(self):
        rec = DecisionRecord(
            decision="Unknown trigger test",
            reason="Test unknown kind rejection",
            evidence="Test evidence",
            alternatives="None",
            tradeoff="None",
            owner="tola-build",
            date="2026-09-29",
            expected_outcome="ValueError raised",
            review_date=None,
            revisit_trigger={"kind": "UNKNOWN_KIND", "name": "x"},
            id="DEC-UNKNOWN-001",
        )
        reg = {rec.id: rec}
        context = {}
        with self.assertRaises(ValueError):
            check_revisit_triggers(reg, context)

    # T15-04: Superseded decision keeps history.
    def test_t15_04_superseded_keeps_history(self):
        reg = _make_register()
        old = reg["DEC-OLD-001"]
        self.assertTrue(old.is_superseded())
        self.assertEqual(old.superseded_by, "DEC-ACTIVE-001")
        new = reg["DEC-ACTIVE-001"]
        self.assertFalse(new.is_superseded())
        self.assertIsNone(new.superseded_by)

    def test_t15_04_both_records_retrievable(self):
        reg = _make_register()
        self.assertIn("DEC-OLD-001", reg)
        self.assertIn("DEC-ACTIVE-001", reg)
        self.assertEqual(len(reg), 2)

    def test_t15_04_supersede_raises_on_already_superseded(self):
        reg = _make_register()
        newer = DecisionRecord(
            decision="Use async I/O v3",
            reason="Even better performance",
            evidence="v3 benchmark",
            alternatives="v2; v1",
            tradeoff="More complexity",
            owner="tola-build",
            date="2026-09-30",
            expected_outcome="Best throughput",
            id="DEC-NEWEST-001",
        )
        with self.assertRaises(ValueError):
            supersede_decision(reg, "DEC-OLD-001", newer)

    # T15-05: Material decision missing reason rejected.
    def test_t15_05_missing_reason_rejected(self):
        incomplete = DecisionRecord(
            decision="Use async I/O",
            reason="",
            evidence="Benchmark data",
            alternatives="Sync I/O",
            tradeoff="Complexity",
            owner="tola-build",
            date="2026-09-29",
            expected_outcome="Better throughput",
        )
        with self.assertRaises(ValueError):
            register_decision(incomplete)

    def test_t15_05_missing_date_rejected(self):
        incomplete = DecisionRecord(
            decision="Use async I/O",
            reason="Sync blocks",
            evidence="Benchmark data",
            alternatives="Sync I/O",
            tradeoff="Complexity",
            owner="tola-build",
            date="",
            expected_outcome="Better throughput",
        )
        with self.assertRaises(ValueError):
            register_decision(incomplete)

    def test_t15_05_empty_evidence_rejected(self):
        incomplete = DecisionRecord(
            decision="Use async I/O",
            reason="Sync blocks",
            evidence="",
            alternatives="Sync I/O",
            tradeoff="Complexity",
            owner="tola-build",
            date="2026-09-29",
            expected_outcome="Better throughput",
        )
        with self.assertRaises(ValueError):
            register_decision(incomplete)

    # T15-06: Historical decision can be explained later.
    def test_t15_06_explain_superseded_decision(self):
        reg = _make_register()
        output = explain_decision(reg, "DEC-OLD-001")
        self.assertIn("Use sync I/O for report generation", output)
        self.assertIn("SUPERSEDED", output)
        self.assertIn("DEC-ACTIVE-001", output)

    def test_t15_06_explain_active_decision(self):
        reg = _make_register()
        output = explain_decision(reg, "DEC-ACTIVE-001")
        self.assertIn("Use async I/O for report generation", output)
        self.assertIn("ACTIV", output)
        self.assertIn("Review date: 2026-12-01T00:00:00Z", output)
        self.assertIn("Revisit trigger", output)

    def test_t15_06_explain_includes_all_fields(self):
        reg = _make_register()
        output = explain_decision(reg, "DEC-ACTIVE-001")
        self.assertIn("Reason:", output)
        self.assertIn("Evidence:", output)
        self.assertIn("Alternatives considered:", output)
        self.assertIn("Tradeoff:", output)
        self.assertIn("Owner:", output)
        self.assertIn("Date:", output)
        self.assertIn("Expected outcome:", output)

    # Determinism: same register state produces same results.
    def test_t15_06_determinism_due_reviews(self):
        reg = _make_register()
        r1 = due_reviews(reg, "2026-12-01T00:00:00Z")
        r2 = due_reviews(reg, "2026-12-01T00:00:00Z")
        self.assertEqual(len(r1), len(r2))
        self.assertEqual(r1[0].id, r2[0].id)

    def test_t15_06_determinism_triggers(self):
        reg = _make_register()
        context = {"metrics": {"export_throughput": 300}}
        r1 = check_revisit_triggers(reg, context)
        r2 = check_revisit_triggers(reg, context)
        self.assertEqual(len(r1), len(r2))
        self.assertEqual(r1[0].id, r2[0].id)

    # Determinism: register_decision is idempotent for valid records.
    def test_t15_06_determinism_register_idempotent(self):
        rec = _active_record()
        r1 = register_decision(rec)
        r2 = register_decision(rec)
        self.assertEqual(r1.id, r2.id)
        self.assertEqual(r1.decision, r2.decision)


if __name__ == "__main__":
    unittest.main()


class TestT15SupersededFiltering(unittest.TestCase):
    """Superseded decisions must not surface in review/trigger queries."""

    def test_superseded_excluded_from_due_reviews(self):
        reg = _make_register()
        old = _superseded_record()
        old_with_review = dc_replace(old, review_date="2026-09-01T00:00:00Z")
        reg[old.id] = old_with_review
        due = [d.id for d in due_reviews(reg, "2026-12-02T00:00:00Z")]
        self.assertNotIn(old.id, due)
        self.assertIn("DEC-ACTIVE-001", due)

    def test_superseded_excluded_from_revisit_triggers(self):
        reg = _make_register()
        old = _superseded_record()
        old_with_trigger = dc_replace(
            old,
            revisit_trigger={"kind": "METRIC_BELOW", "name": "export_throughput", "threshold": 99999},
        )
        reg[old.id] = old_with_trigger
        fired = [d.id for d in check_revisit_triggers(
            reg, {"metrics": {"export_throughput": 100}}
        )]
        self.assertNotIn(old.id, fired)
        self.assertIn("DEC-ACTIVE-001", fired)
