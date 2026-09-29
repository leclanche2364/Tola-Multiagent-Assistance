"""QA T12 -- Delegation Monitoring and Follow-Through tests.

Covers T12-01..T12-07 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import unittest

from tola.delegation.protocol import DelegationStatus
from tola.monitoring.tracker import (
    DelegationTracker,
    TrackingEvent,
    TrackingEntry,
)
from tola.monitoring.followup import (
    ACK_TIMEOUT,
    PROGRESS_TIMEOUT,
    REVIEW_TIMEOUT,
    ESCALATE,
    NUDGE,
    FLAG,
    due_followups,
    FollowUpAction,
)
from tola.monitoring.summary import delegation_ledger


# ===========================================================================
# Fixtures
# ===========================================================================

FIXTURE_TS = "2026-09-29T12:00:00"
FIXTURE_TS_LATER = "2026-09-29T14:00:00"
FIXTURE_TS_DEADLINE = "2026-09-30T12:00:00"
FIXTURE_TS_OVERDUE = "2026-10-01T12:00:00"


class _FakeDelegation:
    """Minimal delegation-like object for tracker registration."""

    def __init__(
        self,
        delegation_id: str,
        status: DelegationStatus = DelegationStatus.DRAFTED,
        timestamps: dict | None = None,
    ) -> None:
        self.delegation_id = delegation_id
        self.status = status
        self.timestamps = timestamps or {}


def _make_tracker() -> DelegationTracker:
    return DelegationTracker()


# ===========================================================================
# T12-01: Assigned task tracked
# ===========================================================================

class TestT12_01_AssignedTaskTracked(unittest.TestCase):
    """T12-01: Assigned task is tracked after registration."""

    def test_registration_creates_entry(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-200",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        entry = tracker.register_delegation(d)
        self.assertEqual(entry.delegation_id, "DEL-200")
        self.assertEqual(entry.status, DelegationStatus.COMMITTED)
        self.assertEqual(len(entry.event_history), 1)
        self.assertEqual(entry.event_history[0][0], TrackingEvent.ASSIGNED)

    def test_tracker_count_increases(self):
        tracker = _make_tracker()
        d = _FakeDelegation("DEL-201")
        tracker.register_delegation(d)
        self.assertEqual(tracker.count(), 1)

    def test_status_returns_entry(self):
        tracker = _make_tracker()
        d = _FakeDelegation("DEL-202")
        tracker.register_delegation(d)
        entry = tracker.status("DEL-202")
        self.assertEqual(entry.delegation_id, "DEL-202")

    def test_unknown_delegation_raises(self):
        tracker = _make_tracker()
        with self.assertRaises(ValueError):
            tracker.status("NONEXISTENT")


# ===========================================================================
# T12-02: Acknowledgement recorded
# ===========================================================================

class TestT12_02_AcknowledgementRecorded(unittest.TestCase):
    """T12-02: Acknowledgement event is recorded and advances status."""

    def test_acknowledged_event_recorded(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-300",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        entry = tracker.record_event(
            delegation_id="DEL-300",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS_LATER,
        )
        self.assertEqual(entry.status, DelegationStatus.IN_PROGRESS)
        self.assertEqual(len(entry.event_history), 2)
        self.assertEqual(entry.event_history[1][0], TrackingEvent.ACKNOWLEDGED)

    def test_acknowledged_event_timestamp_stored(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-301",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-301",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS_LATER,
        )
        entry = tracker.status("DEL-301")
        _, ts = entry.event_history[1]
        self.assertEqual(ts, FIXTURE_TS_LATER)


# ===========================================================================
# T12-03: Started/progress state tracked
# ===========================================================================

class TestT12_03_ProgressStateTracked(unittest.TestCase):
    """T12-03: Started/progress state is tracked via PROGRESS_NOTED."""

    def test_progress_noted_keeps_in_progress(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-400",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        # First progress note
        e1 = tracker.record_event(
            delegation_id="DEL-400",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp=FIXTURE_TS_LATER,
        )
        self.assertEqual(e1.status, DelegationStatus.IN_PROGRESS)
        self.assertEqual(len(e1.event_history), 2)

        # Second progress note
        e2 = tracker.record_event(
            delegation_id="DEL-400",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp="2026-09-29T15:00:00",
        )
        self.assertEqual(e2.status, DelegationStatus.IN_PROGRESS)
        self.assertEqual(len(e2.event_history), 3)

    def test_result_received_transitions_out_of_in_progress(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-401",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-401",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp=FIXTURE_TS_LATER,
        )
        entry = tracker.record_event(
            delegation_id="DEL-401",
            event=TrackingEvent.RESULT_RECEIVED,
            timestamp="2026-09-29T16:00:00",
        )
        self.assertEqual(entry.status, DelegationStatus.RESULT_RECEIVED)


# ===========================================================================
# T12-04: No progress creates TASK_STALLED signal
# ===========================================================================

class TestT12_04_NoProgressCreatesStalled(unittest.TestCase):
    """T12-04: IN_PROGRESS without PROGRESS_NOTED is detected as stalled."""

    def test_in_progress_without_progress_event_is_overdue(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-500",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        # Record ACKNOWLEDGED to get into IN_PROGRESS
        tracker.record_event(
            delegation_id="DEL-500",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        # No PROGRESS_NOTED ever recorded
        thresholds = {PROGRESS_TIMEOUT: FIXTURE_TS_LATER}
        actions = due_followups(tracker, FIXTURE_TS_LATER, thresholds)
        stalled = [a for a in actions if NUDGE in a.action and FLAG in a.action]
        self.assertTrue(len(stalled) >= 1)
        self.assertIn("without progress event", stalled[0].reason)

    def test_progress_event_prevents_stalled_flag(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-501",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-501",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        tracker.record_event(
            delegation_id="DEL-501",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp=FIXTURE_TS_LATER,
        )
        thresholds = {PROGRESS_TIMEOUT: FIXTURE_TS_OVERDUE}
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        stalled = [a for a in actions if NUDGE in a.action and FLAG in a.action]
        self.assertEqual(len(stalled), 0)


# ===========================================================================
# T12-05: Deadline risk creates TASK_AT_RISK signal
# ===========================================================================

class TestT12_05_DeadlineRisk(unittest.TestCase):
    """T12-05: Delegation past deadline triggers escalation."""

    def test_overdue_delegation_gets_escalate_action(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-600",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-600",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        thresholds = {ESCALATE: FIXTURE_TS}
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        escalate_actions = [a for a in actions if a.action == ESCALATE]
        self.assertTrue(len(escalate_actions) >= 1)

    def test_on_time_delegation_no_escalate(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-601",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-601",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        thresholds = {ESCALATE: FIXTURE_TS_OVERDUE}
        actions = due_followups(tracker, FIXTURE_TS, thresholds)
        escalate_actions = [a for a in actions if a.action == ESCALATE]
        self.assertEqual(len(escalate_actions), 0)


# ===========================================================================
# T12-06: Completed/cancelled task stops follow-up
# ===========================================================================

class TestT12_06_CompletedCancelledStopsFollowUp(unittest.TestCase):
    """T12-06: Terminal statuses do not produce follow-up actions."""

    def _register_and_acknowledge(self, tracker, did, status):
        d = _FakeDelegation(
            delegation_id=did,
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id=did,
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        if status == DelegationStatus.IN_PROGRESS:
            tracker.record_event(
                delegation_id=did,
                event=TrackingEvent.PROGRESS_NOTED,
                timestamp=FIXTURE_TS_LATER,
            )

    def test_accepted_no_followup(self):
        tracker = _make_tracker()
        self._register_and_acknowledge(tracker, "DEL-700", DelegationStatus.IN_PROGRESS)
        tracker.record_event(
            delegation_id="DEL-700",
            event=TrackingEvent.RESULT_RECEIVED,
            timestamp="2026-09-29T15:00:00",
        )
        tracker.record_event(
            delegation_id="DEL-700",
            event=TrackingEvent.ACCEPTED,
            timestamp="2026-09-29T16:00:00",
        )
        thresholds = {
            ACK_TIMEOUT: FIXTURE_TS,
            PROGRESS_TIMEOUT: FIXTURE_TS,
            REVIEW_TIMEOUT: FIXTURE_TS,
            ESCALATE: FIXTURE_TS_OVERDUE,
        }
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        self.assertEqual(len(actions), 0)

    def test_rejected_no_followup(self):
        tracker = _make_tracker()
        self._register_and_acknowledge(tracker, "DEL-701", DelegationStatus.IN_PROGRESS)
        tracker.record_event(
            delegation_id="DEL-701",
            event=TrackingEvent.RESULT_RECEIVED,
            timestamp="2026-09-29T15:00:00",
        )
        tracker.record_event(
            delegation_id="DEL-701",
            event=TrackingEvent.REJECTED,
            timestamp="2026-09-29T16:00:00",
        )
        thresholds = {
            ACK_TIMEOUT: FIXTURE_TS,
            PROGRESS_TIMEOUT: FIXTURE_TS,
            REVIEW_TIMEOUT: FIXTURE_TS,
            ESCALATE: FIXTURE_TS_OVERDUE,
        }
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        self.assertEqual(len(actions), 0)

    def test_cancelled_no_followup(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-702",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-702",
            event=TrackingEvent.CANCELLED,
            timestamp=FIXTURE_TS,
        )
        thresholds = {
            ACK_TIMEOUT: FIXTURE_TS,
            PROGRESS_TIMEOUT: FIXTURE_TS,
            REVIEW_TIMEOUT: FIXTURE_TS,
            ESCALATE: FIXTURE_TS_OVERDUE,
        }
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        self.assertEqual(len(actions), 0)


# ===========================================================================
# T12-07: Duplicate progress event does not duplicate follow-up
# ===========================================================================

class TestT12_07_DuplicateProgressNoDuplicateFollowUp(unittest.TestCase):
    """T12-07: Duplicate PROGRESS_NOTED events do not create duplicate
    follow-up actions."""

    def test_multiple_progress_events_single_followup_check(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-800",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-800",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        # Multiple progress notes
        tracker.record_event(
            delegation_id="DEL-800",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp="2026-09-29T13:00:00",
        )
        tracker.record_event(
            delegation_id="DEL-800",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp="2026-09-29T14:00:00",
        )
        tracker.record_event(
            delegation_id="DEL-800",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp="2026-09-29T15:00:00",
        )
        # With a PROGRESS_TIMEOUT that has passed, the delegation IS
        # IN_PROGRESS and has progress events, so no NUDGE+FLAG should fire.
        thresholds = {PROGRESS_TIMEOUT: FIXTURE_TS_OVERDUE}
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        nudge_flag = [a for a in actions if NUDGE in a.action and FLAG in a.action]
        self.assertEqual(len(nudge_flag), 0)


# ===========================================================================
# Transition validation
# ===========================================================================

class TestTransitionValidation(unittest.TestCase):
    """Invalid transitions raise ValueError; history is never rewritten."""

    def test_invalid_transition_raises(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-900",
            status=DelegationStatus.DRAFTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        # DRAFTED cannot go directly to ACKNOWLEDGED
        with self.assertRaises(ValueError):
            tracker.record_event(
                delegation_id="DEL-900",
                event=TrackingEvent.ACKNOWLEDGED,
                timestamp=FIXTURE_TS_LATER,
            )

    def test_history_not_rewritten_on_invalid(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-901",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        original_len = len(tracker.status("DEL-901").event_history)
        with self.assertRaises(ValueError):
            tracker.record_event(
                delegation_id="DEL-901",
                event=TrackingEvent.PROGRESS_NOTED,
                timestamp=FIXTURE_TS_LATER,
            )
        # History unchanged
        self.assertEqual(len(tracker.status("DEL-901").event_history), original_len)

    def test_accepted_cannot_receive_progress(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-902",
            status=DelegationStatus.ACCEPTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        with self.assertRaises(ValueError):
            tracker.record_event(
                delegation_id="DEL-902",
                event=TrackingEvent.PROGRESS_NOTED,
                timestamp=FIXTURE_TS_LATER,
            )


# ===========================================================================
# Follow-up rules
# ===========================================================================

class TestFollowUpRules(unittest.TestCase):
    """Verify each follow-up rule fires under the right conditions."""

    def test_nudge_fires_only_after_ack_timeout(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-1000",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        # No ACKNOWLEDGED event at all
        thresholds = {ACK_TIMEOUT: FIXTURE_TS}
        actions = due_followups(tracker, FIXTURE_TS_LATER, thresholds)
        nudge_actions = [a for a in actions if a.action == NUDGE and "ACK_TIMEOUT" in a.reason]
        self.assertEqual(len(nudge_actions), 1)

    def test_nudge_does_not_fire_before_ack_timeout(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-1001",
            status=DelegationStatus.COMMITTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        thresholds = {ACK_TIMEOUT: FIXTURE_TS_OVERDUE}
        actions = due_followups(tracker, FIXTURE_TS, thresholds)
        nudge_actions = [a for a in actions if a.action == NUDGE and "ACK_TIMEOUT" in a.reason]
        self.assertEqual(len(nudge_actions), 0)

    def test_progress_timeout_flags_nudge_and_flag(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-1002",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-1002",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        thresholds = {PROGRESS_TIMEOUT: FIXTURE_TS}
        actions = due_followups(tracker, FIXTURE_TS_LATER, thresholds)
        nf = [a for a in actions if NUDGE in a.action and FLAG in a.action]
        self.assertEqual(len(nf), 1)

    def test_result_received_unreviewed_flags(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-1003",
            status=DelegationStatus.RESULT_RECEIVED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-1003",
            event=TrackingEvent.RESULT_RECEIVED,
            timestamp=FIXTURE_TS,
        )
        thresholds = {REVIEW_TIMEOUT: FIXTURE_TS}
        actions = due_followups(tracker, FIXTURE_TS_LATER, thresholds)
        flag_actions = [a for a in actions if a.action == FLAG and "REVIEW_TIMEOUT" in a.reason]
        self.assertEqual(len(flag_actions), 1)

    def test_escalate_on_missed_deadline(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-1004",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-1004",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        thresholds = {ESCALATE: FIXTURE_TS}
        actions = due_followups(tracker, FIXTURE_TS_OVERDUE, thresholds)
        esc = [a for a in actions if a.action == ESCALATE]
        self.assertTrue(len(esc) >= 1)


# ===========================================================================
# Ledger summary
# ===========================================================================

class TestLedgerSummary(unittest.TestCase):
    """delegation_ledger returns correct counts and data."""

    def test_counts_match_tracker(self):
        tracker = _make_tracker()
        for i in range(3):
            d = _FakeDelegation(
                delegation_id=f"DEL-S{i}",
                status=DelegationStatus.COMMITTED,
                timestamps={"requested_at": FIXTURE_TS},
            )
            tracker.register_delegation(d)
        summary = delegation_ledger(tracker)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["counts_by_status"]["COMMITTED"], 3)

    def test_open_vs_closed(self):
        tracker = _make_tracker()
        d1 = _FakeDelegation(
            delegation_id="DEL-OC1",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        d2 = _FakeDelegation(
            delegation_id="DEL-OC2",
            status=DelegationStatus.ACCEPTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d1)
        tracker.register_delegation(d2)
        summary = delegation_ledger(tracker)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["closed"], 1)

    def test_oldest_open_item(self):
        tracker = _make_tracker()
        d1 = _FakeDelegation(
            delegation_id="DEL-OLD1",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": "2026-09-01T10:00:00"},
        )
        d2 = _FakeDelegation(
            delegation_id="DEL-OLD2",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": "2026-09-15T10:00:00"},
        )
        tracker.register_delegation(d1)
        tracker.register_delegation(d2)
        summary = delegation_ledger(tracker)
        self.assertEqual(summary["oldest_open"], "DEL-OLD1")

    def test_overdue_list_includes_non_terminal(self):
        tracker = _make_tracker()
        d1 = _FakeDelegation(
            delegation_id="DEL-OV1",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        d2 = _FakeDelegation(
            delegation_id="DEL-OV2",
            status=DelegationStatus.ACCEPTED,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d1)
        tracker.register_delegation(d2)
        summary = delegation_ledger(tracker)
        self.assertIn("DEL-OV1", summary["overdue"])
        self.assertNotIn("DEL-OV2", summary["overdue"])

    def test_event_counts(self):
        tracker = _make_tracker()
        d = _FakeDelegation(
            delegation_id="DEL-EC1",
            status=DelegationStatus.IN_PROGRESS,
            timestamps={"requested_at": FIXTURE_TS},
        )
        tracker.register_delegation(d)
        tracker.record_event(
            delegation_id="DEL-EC1",
            event=TrackingEvent.ACKNOWLEDGED,
            timestamp=FIXTURE_TS,
        )
        tracker.record_event(
            delegation_id="DEL-EC1",
            event=TrackingEvent.PROGRESS_NOTED,
            timestamp=FIXTURE_TS_LATER,
        )
        summary = delegation_ledger(tracker)
        self.assertEqual(summary["event_counts"]["ASSIGNED"], 1)
        self.assertEqual(summary["event_counts"]["ACKNOWLEDGED"], 1)
        self.assertEqual(summary["event_counts"]["PROGRESS_NOTED"], 1)


# ===========================================================================
# Structural
# ===========================================================================

class TestT12_Structure(unittest.TestCase):
    """Structural checks on the monitoring module."""

    def test_tracking_event_enum_has_all_values(self):
        expected = {
            "ASSIGNED", "ACKNOWLEDGED", "PROGRESS_NOTED",
            "RESULT_RECEIVED", "ACCEPTED", "REJECTED", "CANCELLED",
        }
        actual = {e.value for e in TrackingEvent}
        self.assertTrue(expected.issubset(actual))

    def test_follow_up_action_is_frozen(self):
        action = FollowUpAction(
            delegation_id="X",
            action=NUDGE,
            reason="test",
            current_status="IN_PROGRESS",
            last_event="ACKNOWLEDGED",
            timestamp=FIXTURE_TS,
        )
        with self.assertRaises(Exception):
            action.action = ESCALATE

    def test_threshold_constants_are_strings(self):
        self.assertIsInstance(ACK_TIMEOUT, str)
        self.assertIsInstance(PROGRESS_TIMEOUT, str)
        self.assertIsInstance(REVIEW_TIMEOUT, str)


if __name__ == "__main__":
    unittest.main()