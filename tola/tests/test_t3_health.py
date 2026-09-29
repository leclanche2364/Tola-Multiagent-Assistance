"""QA T3 tests -- Project Health and Materiality Engine.

Covers T3-01..T3-08 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest, datetime, dataclasses.  Plain ASCII.
"""

from __future__ import annotations

import datetime
import unittest

from tola.portfolio.contracts import (
    Approval,
    Experiment,
    Goal,
    Metric,
    Project,
    Task,
)
from tola.portfolio.health import (
    HealthLabel,
    HealthAssessment,
    HealthSignal,
    STALLED_DAYS_WITHOUT_PROGRESS,
    DEADLINE_RISK_DAYS,
    BLOCKED_DURATION_DAYS,
    MILESTONE_SLIPPAGE_DAYS,
    EXPERIMENT_DECISION_DAYS,
    APPROVAL_PENDING_DAYS,
    CAPACITY_CONFLICT_TASKS,
    METRIC_DETERIORATION_DELTA,
    NO_NEXT_ACTION_HOURS,
    project_health_assess,
    materiality_check,
)
from tola.portfolio.snapshot import PortfolioSnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_project(
    pid: str = "P1",
    name: str = "Test Project",
    status: str = "active",
) -> Project:
    return Project(
        project_id=pid,
        project_name=name,
        status=status,
        source_system="blackboard",
        source_id=f"src-{pid}",
        fetched_at=datetime.datetime(2026, 9, 29, 12, 0, 0),
        source_version="1.0",
    )


def _make_snapshot(
    tasks: list = None,
    goals: list = None,
    experiments: list = None,
    approvals: list = None,
    metrics: list = None,
    blocked_tasks: list = None,
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        generated_at="2026-09-29T19:00:00",
        projects=[_make_project()],
        active_goals=goals or [],
        active_tasks=tasks or [],
        blocked_tasks=blocked_tasks or [],
        experiments=experiments or [],
        pending_approvals=approvals or [],
        material_metrics=metrics or [],
        source_versions={"blackboard": {"source_version": "1.0"}},
    )


# ---------------------------------------------------------------------------
# T3-01: Healthy project remains ON_TRACK
# ---------------------------------------------------------------------------

class TestT3_01_HealthyOnTrack(unittest.TestCase):
    def test_healthy_project_is_on_track(self):
        """T3-01: A healthy project with no risk signals stays ON_TRACK."""
        project = _make_project()
        task = Task(
            task_id="T1",
            idempotency_key="k1",
            title="On track task",
            project_id="P1",
            status="in_progress",
            deadline="2026-10-15",
            source_system="blackboard",
            source_id="src-t1",
            fetched_at=datetime.datetime(2026, 9, 29, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        assessment = project_health_assess(project, snapshot)
        self.assertEqual(assessment.label, HealthLabel.ON_TRACK)
        self.assertEqual(len(assessment.signals), 0)


# ---------------------------------------------------------------------------
# T3-02: Deadline risk triggers attention
# ---------------------------------------------------------------------------

class TestT3_02_DeadlineRisk(unittest.TestCase):
    def test_deadline_within_risk_window_triggers_attention(self):
        """T3-02: A task with a deadline within DEADLINE_RISK_DAYS triggers ATTENTION."""
        project = _make_project()
        task = Task(
            task_id="T2",
            idempotency_key="k2",
            title="Near deadline task",
            project_id="P1",
            status="in_progress",
            deadline="2026-10-01",
            source_system="blackboard",
            source_id="src-t2",
            fetched_at=datetime.datetime(2026, 9, 25, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        assessment = project_health_assess(project, snapshot)
        self.assertEqual(assessment.label, HealthLabel.ATTENTION)
        signal_types = {s.type for s in assessment.signals}
        self.assertIn("DEADLINE_RISK", signal_types)


# ---------------------------------------------------------------------------
# T3-03: Stalled project detected
# ---------------------------------------------------------------------------

class TestT3_03_StalledActivity(unittest.TestCase):
    def test_stalled_task_triggers_attention(self):
        """T3-03: A task with no progress for STALLED_DAYS_WITHOUT_PROGRESS
        triggers a stalled-activity signal and ATTENTION label."""
        project = _make_project()
        task = Task(
            task_id="T3",
            idempotency_key="k3",
            title="Stalled task",
            project_id="P1",
            status="in_progress",
            deadline=None,
            source_system="blackboard",
            source_id="src-t3",
            fetched_at=datetime.datetime(2026, 9, 20, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        assessment = project_health_assess(project, snapshot)
        signal_types = {s.type for s in assessment.signals}
        self.assertIn("STALLED_ACTIVITY", signal_types)
        # Stalled activity alone maps to ATTENTION.
        self.assertEqual(assessment.label, HealthLabel.ATTENTION)


# ---------------------------------------------------------------------------
# T3-04: Completed experiment awaiting review detected
# ---------------------------------------------------------------------------

class TestT3_04_ExperimentAwaitingDecision(unittest.TestCase):
    def test_completed_experiment_awaiting_decision(self):
        """T3-04: A completed experiment with decision_required=True that has
        been waiting >= EXPERIMENT_DECISION_DAYS triggers ATTENTION."""
        project = _make_project()
        experiment = Experiment(
            experiment_id="E1",
            project_id="P1",
            title="Completed experiment",
            status="completed",
            decision_required=True,
            source_system="local_doc",
            source_id="src-e1",
            fetched_at=datetime.datetime(2026, 9, 20, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(experiments=[experiment])
        assessment = project_health_assess(project, snapshot)
        signal_types = {s.type for s in assessment.signals}
        self.assertIn("EXPERIMENT_AWAITING_DECISION", signal_types)
        self.assertEqual(assessment.label, HealthLabel.ATTENTION)


# ---------------------------------------------------------------------------
# T3-05: Blocked dependency reflected
# ---------------------------------------------------------------------------

class TestT3_05_BlockedDependency(unittest.TestCase):
    def test_blocked_task_reflected_in_assessment(self):
        """T3-05: A blocked task persisting beyond BLOCKED_DURATION_DAYS
        triggers BLOCKED_DURATION signal and BLOCKED label."""
        project = _make_project()
        task = Task(
            task_id="T5",
            idempotency_key="k5",
            title="Blocked task",
            project_id="P1",
            status="blocked",
            deadline="2026-10-20",
            source_system="blackboard",
            source_id="src-t5",
            fetched_at=datetime.datetime(2026, 9, 20, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(
            tasks=[task], blocked_tasks=[task]
        )
        assessment = project_health_assess(project, snapshot)
        signal_types = {s.type for s in assessment.signals}
        self.assertIn("BLOCKED_DURATION", signal_types)
        self.assertEqual(assessment.label, HealthLabel.BLOCKED)


# ---------------------------------------------------------------------------
# T3-06: Project with no next action detected
# ---------------------------------------------------------------------------

class TestT3_06_NoNextAction(unittest.TestCase):
    def test_no_next_action_detected(self):
        """T3-06: A project with no active task due within NO_NEXT_ACTION_HOURS
        and no upcoming milestone triggers NO_NEXT_ACTION signal."""
        project = _make_project()
        # A task with a far-future deadline, done status (not actionable).
        task = Task(
            task_id="T6",
            idempotency_key="k6",
            title="Done task",
            project_id="P1",
            status="done",
            deadline="2027-01-01",
            source_system="blackboard",
            source_id="src-t6",
            fetched_at=datetime.datetime(2026, 9, 20, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        assessment = project_health_assess(project, snapshot)
        signal_types = {s.type for s in assessment.signals}
        self.assertIn("NO_NEXT_ACTION", signal_types)
        self.assertEqual(assessment.label, HealthLabel.ATTENTION)


# ---------------------------------------------------------------------------
# T3-07: Normal project does not become false urgent signal
# ---------------------------------------------------------------------------

class TestT3_07_NoFalseUrgent(unittest.TestCase):
    def test_healthy_project_not_urgent(self):
        """T3-07: A normal healthy project must NEVER produce a material
        urgent signal.  materiality_check returns False for ON_TRACK."""
        project = _make_project()
        task = Task(
            task_id="T7",
            idempotency_key="k7",
            title="Healthy task",
            project_id="P1",
            status="in_progress",
            deadline="2026-12-31",
            source_system="blackboard",
            source_id="src-t7",
            fetched_at=datetime.datetime(2026, 9, 29, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        assessment = project_health_assess(project, snapshot)
        self.assertEqual(assessment.label, HealthLabel.ON_TRACK)
        self.assertFalse(materiality_check(assessment))


# ---------------------------------------------------------------------------
# T3-08: Underlying evidence is available behind health label
# ---------------------------------------------------------------------------

class TestT3_08_EvidenceAvailable(unittest.TestCase):
    def test_health_label_carries_evidence(self):
        """T3-08: Every health label MUST carry its underlying evidence
        (list of signal instances with type, entity reference, and
        observed values) -- never a bare label."""
        project = _make_project()
        task = Task(
            task_id="T8",
            idempotency_key="k8",
            title="Near deadline task",
            project_id="P1",
            status="in_progress",
            deadline="2026-10-01",
            source_system="blackboard",
            source_id="src-t8",
            fetched_at=datetime.datetime(2026, 9, 25, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        assessment = project_health_assess(project, snapshot)
        # Label is present.
        self.assertIn(assessment.label, HealthLabel)
        # Evidence is non-empty when label is not ON_TRACK.
        if assessment.label != HealthLabel.ON_TRACK:
            self.assertGreater(len(assessment.signals), 0)
        # Every signal has type, entity_type, entity_id, observed.
        for signal in assessment.signals:
            self.assertIsInstance(signal.type, str)
            self.assertIsInstance(signal.entity_type, str)
            self.assertIsInstance(signal.entity_id, str)
            self.assertIsInstance(signal.observed, dict)
            self.assertGreater(len(signal.observed), 0)


# ---------------------------------------------------------------------------
# Additional deterministic-reproducibility check
# ---------------------------------------------------------------------------

class TestDeterminism(unittest.TestCase):
    def test_same_inputs_produce_same_assessment(self):
        """Determinism: same inputs always produce the same assessment."""
        project = _make_project()
        task = Task(
            task_id="DT1",
            idempotency_key="kd",
            title="Deterministic task",
            project_id="P1",
            status="in_progress",
            deadline="2026-10-01",
            source_system="blackboard",
            source_id="src-dt1",
            fetched_at=datetime.datetime(2026, 9, 25, 12, 0, 0),
            source_version="1.0",
        )
        snapshot = _make_snapshot(tasks=[task])
        a1 = project_health_assess(project, snapshot)
        a2 = project_health_assess(project, snapshot)
        self.assertEqual(a1.label, a2.label)
        self.assertEqual(len(a1.signals), len(a2.signals))
        for s1, s2 in zip(a1.signals, a2.signals):
            self.assertEqual(s1.type, s2.type)
            self.assertEqual(s1.entity_id, s2.entity_id)
            self.assertEqual(s1.observed, s2.observed)


# ---------------------------------------------------------------------------
# Threshold constants are documented and accessible
# ---------------------------------------------------------------------------

class TestThresholdConstants(unittest.TestCase):
    """Verify threshold constants are named integers/floats."""

    def test_stalled_days_is_positive_int(self):
        self.assertIsInstance(STALLED_DAYS_WITHOUT_PROGRESS, int)
        self.assertGreater(STALLED_DAYS_WITHOUT_PROGRESS, 0)

    def test_deadline_risk_days_is_positive_int(self):
        self.assertIsInstance(DEADLINE_RISK_DAYS, int)
        self.assertGreater(DEADLINE_RISK_DAYS, 0)

    def test_blocked_duration_days_is_positive_int(self):
        self.assertIsInstance(BLOCKED_DURATION_DAYS, int)
        self.assertGreater(BLOCKED_DURATION_DAYS, 0)

    def test_milestone_slippage_days_is_positive_int(self):
        self.assertIsInstance(MILESTONE_SLIPPAGE_DAYS, int)
        self.assertGreater(MILESTONE_SLIPPAGE_DAYS, 0)

    def test_experiment_decision_days_is_positive_int(self):
        self.assertIsInstance(EXPERIMENT_DECISION_DAYS, int)
        self.assertGreater(EXPERIMENT_DECISION_DAYS, 0)

    def test_approval_pending_days_is_positive_int(self):
        self.assertIsInstance(APPROVAL_PENDING_DAYS, int)
        self.assertGreater(APPROVAL_PENDING_DAYS, 0)

    def test_capacity_conflict_tasks_is_positive_int(self):
        self.assertIsInstance(CAPACITY_CONFLICT_TASKS, int)
        self.assertGreater(CAPACITY_CONFLICT_TASKS, 0)

    def test_metric_deterioration_delta_is_positive_float(self):
        self.assertIsInstance(METRIC_DETERIORATION_DELTA, float)
        self.assertGreater(METRIC_DETERIORATION_DELTA, 0.0)

    def test_no_next_action_hours_is_positive_int(self):
        self.assertIsInstance(NO_NEXT_ACTION_HOURS, int)
        self.assertGreater(NO_NEXT_ACTION_HOURS, 0)


if __name__ == "__main__":
    unittest.main()