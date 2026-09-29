# QA T13 tests -- Outcome Verifier.
# Stdlib only. Plain ASCII. Deterministic.

import unittest

from tola.verification.criteria import (
    SuccessCriterion,
    build_criteria,
    CriterionKind,
)
from tola.verification.verifier import (
    VerificationOutcome,
    verify_outcome,
)
from tola.verification.closer import (
    CloseDecision,
    verify_and_close,
)
from tola.monitoring.tracker import (
    DelegationTracker,
    TrackingEvent,
)
from tola.delegation.protocol import DelegationStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_criteria() -> list:
    return build_criteria([
        {
            "criterion_id": "C1",
            "description": "Report artifact exists",
            "kind": CriterionKind.ARTIFACT_EXISTS.value,
            "check": {"artifact_name": "report.pdf"},
        },
        {
            "criterion_id": "C2",
            "description": "Score meets threshold",
            "kind": CriterionKind.THRESHOLD_MET.value,
            "check": {"metric": "score", "threshold": 80},
        },
        {
            "criterion_id": "C3",
            "description": "Confirmation received",
            "kind": CriterionKind.CONFIRMATION_RECEIVED.value,
            "check": {},
        },
    ])


def _make_evidence(items: list) -> dict:
    return {"items": items, "timestamp": "2026-09-29T12:00:00Z"}


def _make_tracker_with_result_received(delegation_id: str) -> DelegationTracker:
    """Helper: create tracker with a delegation in RESULT_RECEIVED state."""
    tracker = DelegationTracker()
    tracker.register_delegation(
        type(
            "Obj",
            (),
            {
                "delegation_id": delegation_id,
                "status": DelegationStatus.RESULT_RECEIVED,
                "timestamps": {},
            },
        )()
    )
    return tracker


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestT13OutcomeVerifier(unittest.TestCase):
    """QA T13 -- Outcome Verifier test suite."""

    # T13-01: Complete fixture returns VERIFIED and closes via tracker.
    def test_t13_01_complete_fixture_verified_and_closes(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "artifact", "data": {"name": "report.pdf"}},
            {"criterion_id": "C2", "kind": "metric", "data": {"score": 92}},
            {"criterion_id": "C3", "kind": "confirmation", "data": {"confirmed": True}},
        ])
        result = verify_outcome(criteria, evidence)
        self.assertEqual(result.outcome, VerificationOutcome.VERIFIED.value)
        self.assertEqual(len(result.checks), 3)
        self.assertTrue(all(c.passed for c in result.checks))

        tracker = _make_tracker_with_result_received("D1")
        close = verify_and_close(tracker, "D1", criteria, evidence)
        self.assertEqual(close.decision, CloseDecision.CLOSED.value)
        self.assertEqual(close.new_status, DelegationStatus.ACCEPTED.value)

    # T13-02: Polished but incomplete result returns PARTIALLY_VERIFIED.
    def test_t13_02_polished_incomplete_not_verified(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "artifact", "data": {"name": "report.pdf"}},
            {"criterion_id": "C2", "kind": "metric", "data": {"score": 92}},
            # C3 missing confirmation -- polished but incomplete
        ])
        result = verify_outcome(criteria, evidence)
        self.assertEqual(result.outcome, VerificationOutcome.PARTIALLY_VERIFIED.value)
        self.assertIn("C3", result.missing)
        self.assertNotEqual(result.outcome, VerificationOutcome.VERIFIED.value)

    # T13-03: Missing evidence blocks full success.
    def test_t13_03_missing_evidence_blocks_success(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "artifact", "data": {"name": "report.pdf"}},
            # C2 and C3 have no evidence at all
        ])
        result = verify_outcome(criteria, evidence)
        self.assertIn(result.outcome, [
            VerificationOutcome.PARTIALLY_VERIFIED.value,
            VerificationOutcome.NOT_VERIFIED.value,
        ])
        self.assertIn("C2", result.missing)
        self.assertIn("C3", result.missing)

    # T13-04: External blocker -- evidence kind incompatible returns UNVERIFIABLE.
    def test_t13_04_wrong_evidence_kind_unverifiable(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "field", "data": {"name": "report.pdf"}},
            # C1 needs artifact kind but got field kind
        ])
        result = verify_outcome(criteria, evidence)
        unverifiable = [c for c in result.checks if "incompatible" in c.reason.lower()]
        self.assertTrue(len(unverifiable) >= 1)
        self.assertIn(result.outcome, [
            VerificationOutcome.UNVERIFIABLE.value,
            VerificationOutcome.NOT_VERIFIED.value,
        ])

    # T13-05: Self-reported completion without evidence cannot close.
    def test_t13_05_self_reported_complete_no_evidence(self):
        criteria = _make_criteria()
        evidence = _make_evidence([])
        result = verify_outcome(criteria, evidence)
        self.assertNotEqual(result.outcome, VerificationOutcome.VERIFIED.value)
        self.assertEqual(len(result.missing), 3)

    # T13-06: False-success fixture cannot close.
    def test_t13_06_false_success_cannot_close(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "artifact", "data": {"name": "report.pdf"}},
            {"criterion_id": "C2", "kind": "metric", "data": {"score": 45}},
            {"criterion_id": "C3", "kind": "confirmation", "data": {"confirmed": True}},
        ])
        result = verify_outcome(criteria, evidence)
        self.assertNotEqual(result.outcome, VerificationOutcome.VERIFIED.value)
        self.assertIn("C2", result.missing)

    # T13-07: Revision request is bounded to missing criteria.
    def test_t13_07_revision_request_bounded_to_missing(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "artifact", "data": {"name": "report.pdf"}},
            # C2 missing, C3 present
            {"criterion_id": "C3", "kind": "confirmation", "data": {"confirmed": True}},
        ])
        result = verify_outcome(criteria, evidence)
        self.assertEqual(result.outcome, VerificationOutcome.PARTIALLY_VERIFIED.value)
        self.assertEqual(result.missing, ["C2"])

    # Unknown criterion kind rejected at build time.
    def test_unknown_kind_rejected_at_build(self):
        with self.assertRaises(ValueError):
            build_criteria([
                {
                    "criterion_id": "X1",
                    "description": "Bad kind",
                    "kind": "UNKNOWN_KIND",
                    "check": {},
                }
            ])

    # No criteria provided returns UNVERIFIABLE.
    def test_empty_criteria_unverifiable(self):
        result = verify_outcome([], {"items": []})
        self.assertEqual(result.outcome, VerificationOutcome.UNVERIFIABLE.value)

    # UNVERIFIABLE flags Tola via closer.
    def test_unverifiable_flags_tola(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "bogus", "data": {"name": "report.pdf"}},
            {"criterion_id": "C2", "kind": "bogus", "data": {"score": 92}},
            {"criterion_id": "C3", "kind": "bogus", "data": {"confirmed": True}},
        ])
        result = verify_outcome(criteria, evidence)
        tracker = _make_tracker_with_result_received("D1")
        close = verify_and_close(tracker, "D1", criteria, evidence)
        self.assertEqual(close.decision, CloseDecision.FLAGGED_TOLA.value)

    # PARTIALLY_VERIFIED returns to specialist with missing list.
    def test_partially_verified_returns_to_specialist(self):
        criteria = _make_criteria()
        evidence = _make_evidence([
            {"criterion_id": "C1", "kind": "artifact", "data": {"name": "report.pdf"}},
            # C2 and C3 missing
        ])
        result = verify_outcome(criteria, evidence)
        tracker = _make_tracker_with_result_received("D1")
        close = verify_and_close(tracker, "D1", criteria, evidence)
        self.assertEqual(close.decision, CloseDecision.RETURN_TO_SPECIALIST.value)
        self.assertIn("C2", close.missing_criteria)
        self.assertIn("C3", close.missing_criteria)
        self.assertNotEqual(close.new_status, DelegationStatus.ACCEPTED.value)


if __name__ == "__main__":
    unittest.main()