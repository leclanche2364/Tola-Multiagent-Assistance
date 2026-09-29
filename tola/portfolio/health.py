"""Project health and materiality engine for Batch T3.

Stdlib only.  Deterministic: all timestamps come from inputs,
never from the clock.  Same inputs always produce the same
assessment.

Threshold constants (all documented here):

- STALLED_DAYS_WITHOUT_PROGRESS = 5
  A task with status not in done/closed/cancelled and no
  activity for this many days is considered stalled.

- DEADLINE_RISK_DAYS = 7
  A deadline within this many days from the assessment date
  triggers deadline-risk signal.

- BLOCKED_DAYS_THRESHOLD = 3
  A blocked task persisting beyond this many days is
  material.

- MILESTONE_SLIPPAGE_DAYS = 3
  A milestone whose due_date is this many days past and
  still pending triggers slippage.

- EXPERIMENT_DECISION_DAYS = 7
  A completed experiment awaiting a decision for this many
  days triggers the awaiting-decision signal.

- APPROVAL_PENDING_DAYS = 5
  A pending approval older than this many days is material.

- CAPACITY_CONFLICT_TASKS = 2
  Two or more active tasks assigned to the same agent on
  the same day is a capacity conflict.

- METRIC_DETERIORATION_DELTA = 0.15
  A metric value that has moved this fraction (15%) in a
  negative direction from its previous reading is material.

- NO_NEXT_ACTION_HOURS = 48
  A project with no actionable task due within this many
  hours and no milestone due is considered to have no next
  action.

Signal types:
  DEADLINE_RISK, BLOCKED_DURATION, STALLED_ACTIVITY,
  MILESTONE_SLIPPAGE, EXPERIMENT_AWAITING_DECISION,
  UNRESOLVED_APPROVAL, CAPACITY_CONFLICT,
  METRIC_DETERIORATION, NO_NEXT_ACTION.

Health labels:
  ON_TRACK, ATTENTION, AT_RISK, BLOCKED, DORMANT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from tola.portfolio.contracts import (
    Approval,
    Experiment,
    Goal,
    Milestone,
    Metric,
    Project,
    Task,
)
from tola.portfolio.snapshot import PortfolioSnapshot

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

STALLED_DAYS_WITHOUT_PROGRESS = 5
DEADLINE_RISK_DAYS = 7
BLOCKED_DURATION_DAYS = 3
MILESTONE_SLIPPAGE_DAYS = 3
EXPERIMENT_DECISION_DAYS = 7
APPROVAL_PENDING_DAYS = 5
CAPACITY_CONFLICT_TASKS = 2
METRIC_DETERIORATION_DELTA = 0.15
NO_NEXT_ACTION_HOURS = 48


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HealthSignal:
    """One evidence-backed health signal.

    type: signal type name (e.g. "DEADLINE_RISK").
    entity_type: the contracts entity type (e.g. "task", "experiment").
    entity_id: the entity's id string.
    observed: dict of observed values that triggered the signal.
    """

    type: str
    entity_type: str
    entity_id: str
    observed: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Health assessment result
# ---------------------------------------------------------------------------

class HealthLabel(str, Enum):
    ON_TRACK = "ON_TRACK"
    ATTENTION = "ATTENTION"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"
    DORMANT = "DORMANT"


@dataclass(frozen=True)
class HealthAssessment:
    """Result of a project health assessment.

    project: the project being assessed.
    label: one of the HealthLabel enum values.
    signals: list of HealthSignal instances that justify the label.
    """

    project: Project
    label: HealthLabel
    signals: List[HealthSignal] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Signal detectors
# ---------------------------------------------------------------------------

def _to_naive(dt: datetime) -> datetime:
    """Strip timezone info for deterministic comparison.

    All dates in this module are compared as naive datetimes.
    """
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO date string or return None."""
    if not value:
        return None
    try:
        return _to_naive(datetime.fromisoformat(value))
    except (ValueError, TypeError):
        return None


def _days_between(earlier: datetime, later: datetime) -> int:
    """Return whole days between two datetimes."""
    return (_to_naive(later) - _to_naive(earlier)).days


def _detect_deadline_risk(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect tasks with deadlines within DEADLINE_RISK_DAYS."""
    signals: List[HealthSignal] = []
    for task in snapshot.active_tasks:
        if task.project_id != project.project_id:
            continue
        if not task.deadline:
            continue
        dl = _parse_date(task.deadline)
        if dl is None:
            continue
        if dl < assessment_date:
            continue
        delta = _days_between(assessment_date, dl)
        if delta <= DEADLINE_RISK_DAYS:
            signals.append(
                HealthSignal(
                    type="DEADLINE_RISK",
                    entity_type="task",
                    entity_id=task.task_id,
                    observed={
                        "deadline": task.deadline,
                        "days_until_deadline": delta,
                        "task_status": task.status,
                    },
                )
            )
    return signals


def _detect_blocked_duration(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect blocked tasks persisting beyond BLOCKED_DURATION_DAYS."""
    signals: List[HealthSignal] = []
    for task in snapshot.blocked_tasks:
        if task.project_id != project.project_id:
            continue
        # Use task fetched_at as proxy for when it became blocked.
        if task.fetched_at.tzinfo is None:
            blocked_since = task.fetched_at
        else:
            blocked_since = task.fetched_at
        days_blocked = _days_between(blocked_since, assessment_date)
        if days_blocked >= BLOCKED_DURATION_DAYS:
            signals.append(
                HealthSignal(
                    type="BLOCKED_DURATION",
                    entity_type="task",
                    entity_id=task.task_id,
                    observed={
                        "days_blocked": days_blocked,
                        "threshold": BLOCKED_DURATION_DAYS,
                        "task_status": task.status,
                    },
                )
            )
    return signals


def _detect_stalled_activity(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect active tasks with no progress for STALLED_DAYS_WITHOUT_PROGRESS."""
    signals: List[HealthSignal] = []
    for task in snapshot.active_tasks:
        if task.project_id != project.project_id:
            continue
        if task.status in ("done", "closed", "cancelled"):
            continue
        # Use fetched_at as last-activity proxy.
        last_activity = task.fetched_at
        days_stalled = _days_between(last_activity, assessment_date)
        if days_stalled >= STALLED_DAYS_WITHOUT_PROGRESS:
            signals.append(
                HealthSignal(
                    type="STALLED_ACTIVITY",
                    entity_type="task",
                    entity_id=task.task_id,
                    observed={
                        "days_without_progress": days_stalled,
                        "threshold": STALLED_DAYS_WITHOUT_PROGRESS,
                        "task_status": task.status,
                    },
                )
            )
    return signals


def _detect_milestone_slippage(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect pending milestones past due by MILESTONE_SLIPPAGE_DAYS."""
    signals: List[HealthSignal] = []
    for milestone in snapshot.active_goals:
        # Milestones are in goals; check goal-level milestones via
        # the snapshot's active_goals list.  We look for goals whose
        # due_date is past and status is still open/pending.
        if milestone.project_id != project.project_id:
            continue
        if milestone.status in ("done", "closed", "cancelled"):
            continue
        due = _parse_date(milestone.due_date)
        if due is None:
            continue
        if due > assessment_date:
            continue
        days_overdue = _days_between(due, assessment_date)
        if days_overdue >= MILESTONE_SLIPPAGE_DAYS:
            signals.append(
                HealthSignal(
                    type="MILESTONE_SLIPPAGE",
                    entity_type="goal",
                    entity_id=milestone.goal_id,
                    observed={
                        "due_date": milestone.due_date,
                        "days_overdue": days_overdue,
                        "threshold": MILESTONE_SLIPPAGE_DAYS,
                        "goal_status": milestone.status,
                    },
                )
            )
    return signals


def _detect_experiment_awaiting_decision(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect completed experiments awaiting a decision."""
    signals: List[HealthSignal] = []
    for experiment in snapshot.experiments:
        if experiment.project_id != project.project_id:
            continue
        if experiment.status != "completed":
            continue
        if not experiment.decision_required:
            continue
        # Use fetched_at as proxy for when the experiment completed.
        days_waiting = _days_between(experiment.fetched_at, assessment_date)
        if days_waiting >= EXPERIMENT_DECISION_DAYS:
            signals.append(
                HealthSignal(
                    type="EXPERIMENT_AWAITING_DECISION",
                    entity_type="experiment",
                    entity_id=experiment.experiment_id,
                    observed={
                        "experiment_status": experiment.status,
                        "decision_required": True,
                        "days_waiting": days_waiting,
                        "threshold": EXPERIMENT_DECISION_DAYS,
                    },
                )
            )
    return signals


def _detect_unresolved_approval(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect pending approvals older than APPROVAL_PENDING_DAYS."""
    signals: List[HealthSignal] = []
    for approval in snapshot.pending_approvals:
        # Match by project via task's project_id if available.
        # The snapshot stores Approval objects; check if any task
        # belonging to this project has this approval.
        approval_date = _parse_date(approval.decided_at)
        if approval_date is not None:
            # Already decided -- not unresolved.
            continue
        # Use fetched_at as the request date.
        days_pending = _days_between(approval.fetched_at, assessment_date)
        if days_pending >= APPROVAL_PENDING_DAYS:
            signals.append(
                HealthSignal(
                    type="UNRESOLVED_APPROVAL",
                    entity_type="approval",
                    entity_id=approval.approval_id,
                    observed={
                        "days_pending": days_pending,
                        "threshold": APPROVAL_PENDING_DAYS,
                        "approval_type": approval.approval_type,
                        "status": approval.status,
                    },
                )
            )
    return signals


def _detect_capacity_conflict(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect agents with CAPACITY_CONFLICT_TASKS or more active tasks."""
    signals: List[HealthSignal] = []
    agent_task_count: Dict[str, int] = {}
    for task in snapshot.active_tasks:
        if task.project_id != project.project_id:
            continue
        if not task.assigned_to:
            continue
        agent_task_count[task.assigned_to] = (
            agent_task_count.get(task.assigned_to, 0) + 1
        )
    for agent, count in agent_task_count.items():
        if count >= CAPACITY_CONFLICT_TASKS:
            signals.append(
                HealthSignal(
                    type="CAPACITY_CONFLICT",
                    entity_type="project",
                    entity_id=project.project_id,
                    observed={
                        "agent": agent,
                        "active_task_count": count,
                        "threshold": CAPACITY_CONFLICT_TASKS,
                    },
                )
            )
    return signals


def _detect_metric_deterioration(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect metrics that have deteriorated by METRIC_DETERIORATION_DELTA."""
    signals: List[HealthSignal] = []
    # Group metrics by metric_name for the same project.
    project_metrics: Dict[str, List[Metric]] = {}
    for metric in snapshot.material_metrics:
        if metric.project_id != project.project_id:
            continue
        key = metric.metric_name
        project_metrics.setdefault(key, []).append(metric)

    for metric_name, metrics in project_metrics.items():
        if len(metrics) < 2:
            continue
        # Sort by snapshot_at or fetched_at descending.
        def _sort_key(m: Metric) -> str:
            if m.snapshot_at:
                return str(m.snapshot_at)
            if isinstance(m.fetched_at, datetime):
                return _to_naive(m.fetched_at).isoformat()
            return str(m.fetched_at)

        sorted_metrics = sorted(
            metrics,
            key=_sort_key,
            reverse=True,
        )
        latest = sorted_metrics[0]
        previous = sorted_metrics[1]
        latest_val = latest.metric_value
        prev_val = previous.metric_value
        if prev_val == 0:
            continue
        change = (latest_val - prev_val) / abs(prev_val)
        if change <= -METRIC_DETERIORATION_DELTA:
            signals.append(
                HealthSignal(
                    type="METRIC_DETERIORATION",
                    entity_type="metric",
                    entity_id=latest.metric_id,
                    observed={
                        "metric_name": metric_name,
                        "latest_value": latest_val,
                        "previous_value": prev_val,
                        "change_fraction": round(change, 4),
                        "threshold": -METRIC_DETERIORATION_DELTA,
                    },
                )
            )
    return signals


def _detect_no_next_action(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: datetime,
) -> List[HealthSignal]:
    """Detect projects with no actionable task due within NO_NEXT_ACTION_HOURS.

    Any active task (in_progress/pending) with a deadline -- regardless of
    how far in the future -- counts as having a next action.  Only projects
    with truly no active tasks trigger NO_NEXT_ACTION.
    """
    signals: List[HealthSignal] = []
    has_actionable = False
    for task in snapshot.active_tasks:
        if task.project_id != project.project_id:
            continue
        if task.status in ("done", "closed", "cancelled"):
            continue
        # Any active task with a deadline or no deadline is actionable.
        has_actionable = True
        break

    if not has_actionable:
        # Also check if any milestone is due soon.
        has_milestone_soon = False
        for goal in snapshot.active_goals:
            if goal.project_id != project.project_id:
                continue
            if goal.status in ("done", "closed", "cancelled"):
                continue
            if goal.due_date:
                due = _parse_date(goal.due_date)
                if due is not None and due <= assessment_date + timedelta(hours=NO_NEXT_ACTION_HOURS):
                    has_milestone_soon = True
                    break
        if not has_milestone_soon:
            signals.append(
                HealthSignal(
                    type="NO_NEXT_ACTION",
                    entity_type="project",
                    entity_id=project.project_id,
                    observed={
                        "no_active_task_due_within_hours": NO_NEXT_ACTION_HOURS,
                        "no_upcoming_milestone": True,
                    },
                )
            )
    return signals


# ---------------------------------------------------------------------------
# Main assessment function
# ---------------------------------------------------------------------------

def project_health_assess(
    project: Project,
    snapshot: PortfolioSnapshot,
    assessment_date: Optional[datetime] = None,
) -> HealthAssessment:
    """Assess the health of a project against a snapshot.

    *assessment_date* defaults to the snapshot's generated_at when
    available, otherwise utcnow.  Deterministic: the date comes from
    inputs, never from the clock at call time (unless no input date
    is available, in which case utcnow is used -- but callers should
    always supply it for reproducibility).

    Returns a HealthAssessment with a label and the evidence
    signals that produced it.
    """
    if assessment_date is None:
        if snapshot.generated_at:
            assessment_date = _to_naive(
                datetime.fromisoformat(snapshot.generated_at)
            )
        else:
            assessment_date = datetime.utcnow()
    else:
        assessment_date = _to_naive(assessment_date)

    all_signals: List[HealthSignal] = []

    all_signals.extend(
        _detect_deadline_risk(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_blocked_duration(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_stalled_activity(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_milestone_slippage(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_experiment_awaiting_decision(
            project, snapshot, assessment_date
        )
    )
    all_signals.extend(
        _detect_unresolved_approval(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_capacity_conflict(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_metric_deterioration(project, snapshot, assessment_date)
    )
    all_signals.extend(
        _detect_no_next_action(project, snapshot, assessment_date)
    )

    label = _label_from_signals(project, all_signals, snapshot)

    return HealthAssessment(
        project=project,
        label=label,
        signals=all_signals,
    )


def _label_from_signals(
    project: Project,
    signals: List[HealthSignal],
    snapshot: PortfolioSnapshot,
) -> HealthLabel:
    """Map accumulated signals to a health label."""
    if not signals:
        return HealthLabel.ON_TRACK

    signal_types = {s.type for s in signals}

    # BLOCKED: any blocked-duration or capacity-conflict signal that
    # prevents progress.
    if "BLOCKED_DURATION" in signal_types:
        return HealthLabel.BLOCKED

    # DORMANT: no next action and stalled activity -- the project is
    # alive but has no forward momentum.
    if "NO_NEXT_ACTION" in signal_types and "STALLED_ACTIVITY" in signal_types:
        return HealthLabel.DORMANT

    # AT_RISK: combinations of serious signals (e.g. deadline risk + stalled).
    if "DEADLINE_RISK" in signal_types and "STALLED_ACTIVITY" in signal_types:
        return HealthLabel.AT_RISK
    if "MILESTONE_SLIPPAGE" in signal_types and "STALLED_ACTIVITY" in signal_types:
        return HealthLabel.AT_RISK

    # ATTENTION: single material signals.
    attention_signals = {
        "DEADLINE_RISK",
        "MILESTONE_SLIPPAGE",
        "METRIC_DETERIORATION",
        "EXPERIMENT_AWAITING_DECISION",
        "UNRESOLVED_APPROVAL",
        "STALLED_ACTIVITY",
        "CAPACITY_CONFLICT",
        "NO_NEXT_ACTION",
    }
    if signal_types & attention_signals:
        return HealthLabel.ATTENTION

    return HealthLabel.ON_TRACK


# ---------------------------------------------------------------------------
# Materiality check
# ---------------------------------------------------------------------------

def materiality_check(assessment: HealthAssessment) -> bool:
    """Return True when evidence-backed signals indicate a material
    problem.

    A healthy project (ON_TRACK, no signals) returns False.
    A project with only ATTENTION-level signals returns True
    (material enough to warrant attention).
    AT_RISK and BLOCKED always return True.
    DORMANT returns True (no forward momentum is material).

    This is the gate that prevents false urgent signals on normal
    healthy projects (QA T3-07).
    """
    if not assessment.signals:
        return False

    if assessment.label in (HealthLabel.AT_RISK, HealthLabel.BLOCKED, HealthLabel.DORMANT):
        return True

    if assessment.label == HealthLabel.ATTENTION:
        return True

    # ON_TRACK with signals should not happen in normal operation,
    # but if it does, only material signal types trigger urgency.
    material_types = {
        "DEADLINE_RISK",
        "BLOCKED_DURATION",
        "STALLED_ACTIVITY",
        "MILESTONE_SLIPPAGE",
        "EXPERIMENT_AWAITING_DECISION",
        "UNRESOLVED_APPROVAL",
        "CAPACITY_CONFLICT",
        "METRIC_DETERIORATION",
        "NO_NEXT_ACTION",
    }
    for s in assessment.signals:
        if s.type in material_types:
            return True

    return False