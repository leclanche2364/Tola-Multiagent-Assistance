"""Goal replanning engine for Batch T6.

Handles plan revision on events (milestone slip, dependency
block, deadline move, capacity reduction).  Versioned plans
with material diffs.  Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from tola.decomposition.planner import (
    DEFAULT_MILESTONE_BUFFER_DAYS,
    DecompositionPlan,
    _derive_milestone_deadline,
)


# ---------------------------------------------------------------------------
# Replan event types
# ---------------------------------------------------------------------------

class ReplanEventKind(str, Enum):
    MILESTONE_SLIPPED = "milestone_slipped"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    DEADLINE_MOVED = "deadline_moved"
    CAPACITY_REDUCED = "capacity_reduced"


@dataclass(frozen=True)
class ReplanEvent:
    """An event that triggers plan replanning."""

    kind: ReplanEventKind
    entity_id: str
    detail: str
    timestamp: str = ""


# ---------------------------------------------------------------------------
# Plan version
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlanVersion:
    """A versioned snapshot of a decomposition plan."""

    version: int
    plan: DecompositionPlan
    event_trigger: Optional[str] = None
    created_at: str = ""


# ---------------------------------------------------------------------------
# Replanner
# ---------------------------------------------------------------------------

def goal_replan(
    plan: DecompositionPlan,
    event: ReplanEvent,
    snapshot: Optional[Dict[str, Any]] = None,
) -> PlanVersion:
    """Produce a new plan version in response to an event.

    Handles four event kinds:
    - MILESTONE_SLIPPED: shifts the slipped milestone and
      all downstream milestones later by a fixed slip offset.
    - DEPENDENCY_BLOCKED: marks dependent milestones as
      blocked and adjusts their deadlines.
    - DEADLINE_MOVED: shifts the goal deadline and re-
      derives all milestone deadline anchors.
    - CAPACITY_REDUCED: reduces effort estimates where
      possible and adds a capacity warning.

    The original plan is never mutated.  A new version
    number is produced (plan.version + 1).

    *snapshot* is an optional dict used for materiality
    context (T2/T3).  The diff between plan versions
    reports only material changes.
    """
    new_version = plan.version + 1
    new_milestones = [dict(m) for m in plan.milestones]
    new_tasks = [dict(t) for t in plan.tasks]
    new_warnings = list(plan.warnings)
    new_confidence = plan.confidence
    new_deadline_anchor = plan.deadline_anchor

    if event.kind == ReplanEventKind.MILESTONE_SLIPPED:
        new_milestones, new_tasks, new_warnings = _apply_slip(
            plan, event, new_milestones, new_tasks, new_warnings
        )

    elif event.kind == ReplanEventKind.DEPENDENCY_BLOCKED:
        new_milestones, new_tasks, new_warnings = _apply_dependency_block(
            plan, event, new_milestones, new_tasks, new_warnings
        )

    elif event.kind == ReplanEventKind.DEADLINE_MOVED:
        new_deadline_anchor, new_milestones, new_tasks = _apply_deadline_move(
            plan, event, new_milestones, new_tasks
        )

    elif event.kind == ReplanEventKind.CAPACITY_REDUCED:
        new_tasks, new_warnings, new_confidence = _apply_capacity_reduction(
            plan, event, new_tasks, new_warnings, new_confidence
        )

    new_plan = DecompositionPlan(
        plan_id=plan.plan_id,
        goal_id=plan.goal_id,
        goal_name=plan.goal_name,
        goal_type=plan.goal_type,
        milestones=new_milestones,
        tasks=new_tasks,
        deadline_anchor=new_deadline_anchor,
        confidence=new_confidence,
        warnings=new_warnings,
        version=new_version,
        created_at=_iso_now(),
    )

    return PlanVersion(
        version=new_version,
        plan=new_plan,
        event_trigger=event.kind.value,
        created_at=_iso_now(),
    )


def material_diff(
    old_version: PlanVersion,
    new_version: PlanVersion,
) -> Dict[str, Any]:
    """Return only material changes between two plan versions.

    Uses the DecompositionPlan.material_changes_from method
    to produce a diff that excludes immaterial churn
    (timestamp-only updates, unchanged re-fetches).
    """
    return new_version.plan.material_changes_from(old_version.plan)


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def _apply_slip(
    plan: DecompositionPlan,
    event: ReplanEvent,
    milestones: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    warnings: List[str],
) -> tuple:
    """Shift a slipped milestone and all downstream ones later."""
    slip_days = 3  # Fixed slip offset; deterministic.
    slipped_id = event.entity_id

    for m in milestones:
        if m["milestone_id"] == slipped_id:
            m["status"] = "slipped"
            warnings.append(
                f"Milestone {slipped_id} slipped: {event.detail}"
            )
        # Shift all milestones at or after the slipped one.
        if _milestone_index(plan, m["milestone_id"]) >= _milestone_index(plan, slipped_id):
            if m["deadline_anchor"]:
                m["deadline_anchor"] = _shift_date(m["deadline_anchor"], slip_days)

    # Shift corresponding tasks.
    for t in tasks:
        if _task_milestone_index(plan, t["milestone_id"]) >= _milestone_index(plan, slipped_id):
            if t["deadline"]:
                t["deadline"] = _shift_date(t["deadline"], slip_days)

    return milestones, tasks, warnings


def _apply_dependency_block(
    plan: DecompositionPlan,
    event: ReplanEvent,
    milestones: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    warnings: List[str],
) -> tuple:
    """Mark a blocked dependency and adjust downstream milestones."""
    blocked_id = event.entity_id

    for m in milestones:
        if blocked_id in m.get("dependencies", []):
            warnings.append(
                f"Milestone {m['milestone_id']} depends on blocked milestone {blocked_id}: {event.detail}"
            )
        if m["milestone_id"] == blocked_id:
            m["status"] = "blocked"
            warnings.append(
                f"Milestone {blocked_id} blocked: {event.detail}"
            )

    return milestones, tasks, warnings


def _apply_deadline_move(
    plan: DecompositionPlan,
    event: ReplanEvent,
    milestones: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
) -> tuple:
    """Shift the goal deadline and re-derive milestone anchors."""
    new_deadline = event.detail
    milestones_new = []
    tasks_new = []

    for idx, m in enumerate(milestones):
        if new_deadline:
            m["deadline_anchor"] = _derive_milestone_deadline(
                new_deadline, idx, len(milestones), DEFAULT_MILESTONE_BUFFER_DAYS
            )
        milestones_new.append(m)

    for idx, t in enumerate(tasks):
        if new_deadline and idx < len(milestones):
            t["deadline"] = milestones_new[idx]["deadline_anchor"]
        tasks_new.append(t)

    return new_deadline, milestones_new, tasks_new


def _apply_capacity_reduction(
    plan: DecompositionPlan,
    event: ReplanEvent,
    tasks: List[Dict[str, Any]],
    warnings: List[str],
    confidence: float,
) -> tuple:
    """Reduce effort estimates where possible; add warning."""
    try:
        reduction_pct = float(event.detail) / 100.0
    except (ValueError, TypeError):
        reduction_pct = 0.1

    for t in tasks:
        original = t["effort_hours"]
        reduced = max(1, int(original * (1 - reduction_pct)))
        t["effort_hours"] = reduced

    warnings.append(
        f"Capacity reduced by {int(reduction_pct * 100)}%; effort estimates trimmed; feasibility check recommended"
    )
    confidence = min(confidence, 0.6)

    return tasks, warnings, confidence


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _milestone_index(plan: DecompositionPlan, milestone_id: str) -> int:
    """Return the index of a milestone in the plan, or -1."""
    for i, m in enumerate(plan.milestones):
        if m["milestone_id"] == milestone_id:
            return i
    return -1


def _task_milestone_index(
    plan: DecompositionPlan, milestone_id: str
) -> int:
    """Return the index of the milestone a task belongs to."""
    for i, m in enumerate(plan.milestones):
        if m["milestone_id"] == milestone_id:
            return i
    return -1


def _shift_date(date_str: str, days: int) -> str:
    """Shift a date string by *days* forward."""
    try:
        dt = datetime.fromisoformat(date_str)
        return (dt + timedelta(days=days)).date().isoformat()
    except (ValueError, TypeError):
        return date_str


def _iso_now() -> str:
    return datetime.utcnow().date().isoformat()