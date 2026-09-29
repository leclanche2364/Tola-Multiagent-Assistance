"""QA T14 -- Stalled Work Recovery tests.

Covers QA T14-01..T14-07 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.  Fixture-driven.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from tola.delegation.protocol import DelegationStatus
from tola.monitoring.tracker import TrackingEntry, TrackingEvent
from tola.recovery.patterns import (
    StallKind,
    StallPattern,
    detect_stall_pattern,
)
from tola.recovery.actions import (
    RecoveryAction,
    ALLOWED_ACTIONS,
    RecoveryPlan,
    propose_recovery,
)
from tola.graph.graph import DependencyGraph, Node, Edge


# ===========================================================================
# Fixtures
# ===========================================================================

FIXTURE_DELEGATION_ID = "DEL-001"
FIXTURE_TS_1 = "2026-09-29T10:00:00"
FIXTURE_TS_2 = "2026-09-29T12:00:00"
FIXTURE_TS_OVERDUE = "2026-10-01T12:00:00"


def _make_tracking_entry(
    delegation_id: str = FIXTURE_DELEGATION_ID,
    status: DelegationStatus = DelegationStatus.IN_PROGRESS,
    events: list[tuple[str, str]] | None = None,
) -> TrackingEntry:
    """Create a TrackingEntry from plain string event tuples."""
    typed_events: list[tuple[TrackingEvent, str]] = []
    for e_str, ts in (events or []):
        e = TrackingEvent(e_str)
        typed_events.append((e, ts))
    return TrackingEntry(
        delegation_id=delegation_id,
        status=status,
        event_history=typed_events,
    )


def _make_graph_with_dependency(
    from_id: str,
    to_id: str,
) -> DependencyGraph:
    """Create a simple dependency graph: from_id depends on to_id."""
    g = DependencyGraph()
    g.add_node(Node(from_id, "task"))
    g.add_node(Node(to_id, "task"))
    g.add_edge(Edge(from_id, to_id, "depends_on"))
    return g


def _make_snapshot(
    current_load: int = 0,
    task_count: int = 0,
    thresholds: dict | None = None,
) -> SimpleNamespace:
    """Create a minimal snapshot-like object."""
    return SimpleNamespace(
        current_load=current_load,
        task_count=task_count,
        thresholds=thresholds or {},
    )


# ===========================================================================
# T14-01: Missing specialist information prompts targeted request.
# UNACKNOWLEDGED -> REQUEST_MISSING_INFO
# ===========================================================================

class TestT14_01_MissingInfoRequestsTargetedRequest(unittest.TestCase):
    def test_unacknowledged_maps_to_request_missing_info(self):
        # No ACK event at all -> UNACKNOWLEDGED
        entry = _make_tracking_entry(
            status=DelegationStatus.COMMITTED,
            events=[],
        )
        pattern = detect_stall_pattern(entry, None, None)
        self.assertEqual(pattern.kind, StallKind.UNACKNOWLEDGED)

        context = {}
        plan = propose_recovery(pattern, context)
        self.assertIn(
            RecoveryAction.REQUEST_MISSING_INFO.value,
            plan.actions,
        )

    def test_unacknowledged_never_requires_approval_first(self):
        entry = _make_tracking_entry(events=[])
        pattern = detect_stall_pattern(entry, None, None)
        plan = propose_recovery(pattern, {})
        self.assertFalse(plan.requires_approval)


# ===========================================================================
# T14-02: Oversized task is split/rescoped appropriately.
# SCOPE_MISMATCH -> SPLIT_TASK or RESCOPE
# ===========================================================================

class TestT14_02_OversizedTaskSplitRescope(unittest.TestCase):
    def test_scope_mismatch_with_multiple_tasks_proposes_split(self):
        # Has ACK and PROGRESS -> not UNACKNOWLEDGED/NO_PROGRESS
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(task_count=5)
        pattern = detect_stall_pattern(entry, None, snapshot)
        self.assertEqual(pattern.kind, StallKind.SCOPE_MISMATCH)

        context = {"task_count": 5}
        plan = propose_recovery(pattern, context)
        self.assertIn(RecoveryAction.SPLIT_TASK.value, plan.actions)

    def test_scope_mismatch_single_task_proposes_rescope(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(task_count=1)
        pattern = detect_stall_pattern(entry, None, snapshot)
        self.assertEqual(pattern.kind, StallKind.SCOPE_MISMATCH)

        context = {"task_count": 1}
        plan = propose_recovery(pattern, context)
        self.assertIn(RecoveryAction.RESCOPE.value, plan.actions)


# ===========================================================================
# T14-03: Capacity blocker routes to Rhythm.
# CAPACITY_SHORTFALL -> QUERY_RHYTHM
# ===========================================================================

class TestT14_03_CapacityBlockerRoutesToRhythm(unittest.TestCase):
    def test_capacity_shortfall_proposes_query_rhythm(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(current_load=100)
        pattern = detect_stall_pattern(entry, None, snapshot)
        self.assertEqual(pattern.kind, StallKind.CAPACITY_SHORTFALL)

        context = {"current_load": 100}
        plan = propose_recovery(pattern, context)
        self.assertIn(RecoveryAction.QUERY_RHYTHM.value, plan.actions)

    def test_capacity_shortfall_requires_approval(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(current_load=100)
        pattern = detect_stall_pattern(entry, None, snapshot)
        context = {"current_load": 100}
        plan = propose_recovery(pattern, context)
        self.assertTrue(plan.requires_approval)


# ===========================================================================
# T14-04: Dependency sequence corrected.
# BLOCKED_DEPENDENCY -> REORDER_DEPENDENCIES (valid reorder) or ESCALATE
# ===========================================================================

class TestT14_04_DependencySequenceCorrected(unittest.TestCase):
    def test_blocked_dependency_with_valid_reorder_proposes_reorder(self):
        # Entry with ACK + PROGRESS, graph has valid topo order
        # Graph node must match delegation_id for deps to be found
        entry = _make_tracking_entry(
            delegation_id=FIXTURE_DELEGATION_ID,
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        graph = _make_graph_with_dependency(FIXTURE_DELEGATION_ID, "DEL-002")
        pattern = detect_stall_pattern(entry, graph, None)
        self.assertEqual(pattern.kind, StallKind.BLOCKED_DEPENDENCY)

        context = {"graph": graph}
        plan = propose_recovery(pattern, context)
        self.assertIn(
            RecoveryAction.REORDER_DEPENDENCIES.value,
            plan.actions,
        )

    def test_blocked_dependency_no_valid_reorder_escalates(self):
        # Graph with a cycle has no valid topological order -> escalate
        g = DependencyGraph()
        g.add_node(Node(FIXTURE_DELEGATION_ID, "task"))
        g.add_node(Node("DEL-002", "task"))
        g.add_edge(Edge(FIXTURE_DELEGATION_ID, "DEL-002", "depends_on"))
        g.add_edge(Edge("DEL-002", FIXTURE_DELEGATION_ID, "depends_on"))

        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        pattern = detect_stall_pattern(entry, g, None)
        self.assertEqual(pattern.kind, StallKind.BLOCKED_DEPENDENCY)

        context = {"graph": g}
        plan = propose_recovery(pattern, context)
        self.assertIn(RecoveryAction.ESCALATE.value, plan.actions)
        self.assertTrue(plan.requires_approval)


# ===========================================================================
# T14-05: Unrecoverable task escalated or stopped.
# DEADLINE_MISSED -> ESCALATE (never silent rescope)
# ===========================================================================

class TestT14_05_UnrecoverableTaskEscalatedOrStopped(unittest.TestCase):
    def test_deadline_missed_proposes_escalate(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(
            thresholds={"ESCALATE": FIXTURE_TS_1},
        )
        pattern = detect_stall_pattern(entry, None, snapshot)
        self.assertEqual(pattern.kind, StallKind.DEADLINE_MISSED)

        context = {}
        plan = propose_recovery(pattern, context)
        self.assertIn(RecoveryAction.ESCALATE.value, plan.actions)

    def test_deadline_missed_never_silently_rescoped(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(
            thresholds={"ESCALATE": FIXTURE_TS_1},
        )
        pattern = detect_stall_pattern(entry, None, snapshot)
        context = {}
        plan = propose_recovery(pattern, context)
        self.assertNotIn(RecoveryAction.RESCOPE.value, plan.actions)
        self.assertNotIn(RecoveryAction.SPLIT_TASK.value, plan.actions)

    def test_deadline_missed_requires_approval(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(
            thresholds={"ESCALATE": FIXTURE_TS_1},
        )
        pattern = detect_stall_pattern(entry, None, snapshot)
        context = {}
        plan = propose_recovery(pattern, context)
        self.assertTrue(plan.requires_approval)


# ===========================================================================
# T14-06: Recovery never crosses authority boundary.
# Bounded reassignment only within same capability class.
# ===========================================================================

class TestT14_06_RecoveryNeverCrossesAuthorityBoundary(unittest.TestCase):
    def test_bounded_reassignment_same_capability_class(self):
        """Reassignment within same capability class is allowed (with approval)."""
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(current_load=100)
        pattern = detect_stall_pattern(entry, None, snapshot)
        self.assertEqual(pattern.kind, StallKind.CAPACITY_SHORTFALL)

        context = {
            "current_load": 100,
            "source_agent": "rhythm",
            "target_agent": "rhythm",
        }
        plan = propose_recovery(pattern, context)
        self.assertIn(
            RecoveryAction.BOUNDED_REASSIGNMENT.value,
            plan.actions,
        )
        self.assertTrue(plan.requires_approval)

    def test_bounded_reassignment_different_capability_class_excluded(self):
        """Reassignment across capability classes is excluded."""
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(current_load=100)
        pattern = detect_stall_pattern(entry, None, snapshot)

        context = {
            "current_load": 100,
            "source_agent": "rhythm",
            "target_agent": "growth",
        }
        plan = propose_recovery(pattern, context)
        self.assertNotIn(
            RecoveryAction.BOUNDED_REASSIGNMENT.value,
            plan.actions,
        )

    def test_all_proposed_actions_are_within_allowed_set(self):
        """Property-style check: every proposed action is in ALLOWED_ACTIONS."""
        for kind in StallKind:
            entry = _make_tracking_entry(
                status=DelegationStatus.IN_PROGRESS,
                events=[
                    ("ACKNOWLEDGED", FIXTURE_TS_1),
                    ("PROGRESS_NOTED", FIXTURE_TS_1),
                ],
            )
            pattern = StallPattern(kind=kind, evidence=("test",))
            context = {
                "current_load": 100,
                "source_agent": "rhythm",
                "target_agent": "rhythm",
                "task_count": 3,
                "graph": None,
            }
            plan = propose_recovery(pattern, context)
            for action in plan.actions:
                self.assertIn(
                    action,
                    ALLOWED_ACTIONS,
                    msg=f"Action '{action}' from pattern '{kind}' "
                    f"is not in ALLOWED_ACTIONS.",
                )


# ===========================================================================
# T14-07: Recovery attempts are bounded and logged.
# Determinism: same inputs always produce same plan.
# ===========================================================================

class TestT14_07_RecoveryBoundedAndLogged(unittest.TestCase):
    def test_determinism_same_inputs_same_plan(self):
        """Same pattern + context always produces the same RecoveryPlan."""
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(current_load=100)
        pattern = detect_stall_pattern(entry, None, snapshot)
        context = {
            "current_load": 100,
            "source_agent": "rhythm",
            "target_agent": "rhythm",
        }
        plan1 = propose_recovery(pattern, context)
        plan2 = propose_recovery(pattern, context)
        self.assertEqual(plan1.actions, plan2.actions)
        self.assertEqual(plan1.requires_approval, plan2.requires_approval)
        self.assertEqual(plan1.rationale, plan2.rationale)

    def test_no_progress_routes_to_request_missing_info_not_reassignment(self):
        """NO_PROGRESS must not propose reassignment first."""
        # ACK but no PROGRESS_NOTED -> NO_PROGRESS
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[("ACKNOWLEDGED", FIXTURE_TS_1)],
        )
        pattern = detect_stall_pattern(entry, None, None)
        self.assertEqual(pattern.kind, StallKind.NO_PROGRESS)

        plan = propose_recovery(pattern, {})
        self.assertIn(
            RecoveryAction.REQUEST_MISSING_INFO.value,
            plan.actions,
        )
        self.assertNotIn(
            RecoveryAction.BOUNDED_REASSIGNMENT.value,
            plan.actions,
        )

    def test_unacknowledged_never_proposes_reassignment(self):
        """UNACKNOWLEDGED must not propose reassignment as first action."""
        entry = _make_tracking_entry(events=[])
        pattern = detect_stall_pattern(entry, None, None)
        plan = propose_recovery(pattern, {})
        self.assertEqual(
            plan.actions[0],
            RecoveryAction.REQUEST_MISSING_INFO.value,
        )

    def test_blocked_dependency_no_reorder_escalates_not_guesses(self):
        """No valid reorder -> escalate, never guess or silently proceed."""
        g = DependencyGraph()
        g.add_node(Node(FIXTURE_DELEGATION_ID, "task"))
        g.add_node(Node("DEL-002", "task"))
        g.add_edge(Edge(FIXTURE_DELEGATION_ID, "DEL-002", "depends_on"))
        g.add_edge(Edge("DEL-002", FIXTURE_DELEGATION_ID, "depends_on"))

        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        pattern = detect_stall_pattern(entry, g, None)
        plan = propose_recovery(pattern, {"graph": g})
        self.assertIn(RecoveryAction.ESCALATE.value, plan.actions)
        self.assertNotIn(RecoveryAction.REORDER_DEPENDENCIES.value, plan.actions)


# ===========================================================================
# Additional: ESCALATE and STOP for DEADLINE_MISSED
# ===========================================================================

class TestT14_DeadlineMissedEscalateOrStop(unittest.TestCase):
    def test_deadline_missed_never_silent_rescope_or_reassign(self):
        """DEADLINE_MISSED must never produce RESCOPE or SPLIT_TASK."""
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(
            thresholds={"ESCALATE": FIXTURE_TS_1},
        )
        pattern = detect_stall_pattern(entry, None, snapshot)
        plan = propose_recovery(pattern, {})
        for action in plan.actions:
            self.assertNotEqual(action, RecoveryAction.RESCOPE.value)
            self.assertNotEqual(action, RecoveryAction.SPLIT_TASK.value)


# ===========================================================================
# Integration: full pattern-to-action mapping
# ===========================================================================

class TestT14_FullPatternActionMapping(unittest.TestCase):
    """Each stall pattern maps to its expected recovery action."""

    def test_unacknowledged_maps_to_request_missing_info(self):
        entry = _make_tracking_entry(events=[])
        pattern = detect_stall_pattern(entry, None, None)
        plan = propose_recovery(pattern, {})
        self.assertEqual(
            plan.actions[0],
            RecoveryAction.REQUEST_MISSING_INFO.value,
        )

    def test_no_progress_maps_to_request_missing_info(self):
        # ACK but no PROGRESS_NOTED -> NO_PROGRESS
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[("ACKNOWLEDGED", FIXTURE_TS_1)],
        )
        pattern = detect_stall_pattern(entry, None, None)
        plan = propose_recovery(pattern, {})
        self.assertEqual(
            plan.actions[0],
            RecoveryAction.REQUEST_MISSING_INFO.value,
        )

    def test_blocked_dependency_maps_to_reorder_or_escalate(self):
        entry = _make_tracking_entry(
            delegation_id=FIXTURE_DELEGATION_ID,
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        g = _make_graph_with_dependency(FIXTURE_DELEGATION_ID, "DEL-002")
        pattern = detect_stall_pattern(entry, g, None)
        plan = propose_recovery(pattern, {"graph": g})
        self.assertIn(
            RecoveryAction.REORDER_DEPENDENCIES.value,
            plan.actions,
        )

    def test_capacity_shortfall_maps_to_query_rhythm(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(current_load=100)
        pattern = detect_stall_pattern(entry, None, snapshot)
        plan = propose_recovery(pattern, {"current_load": 100})
        self.assertIn(
            RecoveryAction.QUERY_RHYTHM.value,
            plan.actions,
        )

    def test_scope_mismatch_maps_to_split_or_rescope(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(task_count=5)
        pattern = detect_stall_pattern(entry, None, snapshot)
        plan = propose_recovery(pattern, {"task_count": 5})
        self.assertIn(
            RecoveryAction.SPLIT_TASK.value,
            plan.actions,
        )

    def test_deadline_missed_maps_to_escalate(self):
        entry = _make_tracking_entry(
            status=DelegationStatus.IN_PROGRESS,
            events=[
                ("ACKNOWLEDGED", FIXTURE_TS_1),
                ("PROGRESS_NOTED", FIXTURE_TS_1),
            ],
        )
        snapshot = _make_snapshot(
            thresholds={"ESCALATE": FIXTURE_TS_1},
        )
        pattern = detect_stall_pattern(entry, None, snapshot)
        plan = propose_recovery(pattern, {})
        self.assertIn(
            RecoveryAction.ESCALATE.value,
            plan.actions,
        )


# ===========================================================================
# Run
# ===========================================================================

if __name__ == "__main__":
    unittest.main()