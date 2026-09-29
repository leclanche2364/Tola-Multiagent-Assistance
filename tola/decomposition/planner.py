"""Goal decomposition planner for Batch T6.

Deterministic rule-based decomposition: a goal becomes ordered
milestones based on goal.type/phase metadata and constraint
inputs (deadline, capacity limits, dependency list).  No LLM
calls, no I/O.  Plain ASCII, stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from tola.portfolio.contracts import Goal, Milestone, Task

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MILESTONE_BUFFER_DAYS = 7
DEFAULT_TASK_EFFORT_HOURS = 8
DEFAULT_PLAN_CONFIDENCE = 0.85
LOW_CONFIDENCE_THRESHOLD = 0.5

PHASE_ORDER = ["discovery", "design", "build", "test", "launch", "review"]

TYPE_PHASE_MAP = {
    "feature": ["design", "build", "test", "launch"],
    "bugfix": ["build", "test", "launch"],
    "research": ["discovery", "design", "review"],
    "infra": ["design", "build", "test"],
    "ops": ["build", "test", "launch"],
    "experiment": ["discovery", "design", "build", "review"],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class DecompositionWarning(str, Enum):
    MISSING_DEADLINE = "missing_deadline"
    UNKNOWN_GOAL_TYPE = "unknown_goal_type"
    MISSING_CONSTRAINTS = "missing_constraints"
    NO_PHASE_MATCH = "no_phase_match"
    OVERLOADED_CAPACITY = "overloaded_capacity"


@dataclass(frozen=True)
class DecompositionPlan:
    plan_id: str
    goal_id: str
    goal_name: str
    goal_type: Optional[str]
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    deadline_anchor: Optional[str] = None
    confidence: float = DEFAULT_PLAN_CONFIDENCE
    warnings: List[str] = field(default_factory=list)
    version: int = 1
    created_at: str = ""

    def material_changes_from(self, other: "DecompositionPlan") -> Dict[str, Any]:
        """Return only material differences vs another plan version."""
        changes: Dict[str, Any] = {}
        if self.milestones != other.milestones:
            changes["milestones"] = {
                "added": [m for m in self.milestones if m not in other.milestones],
                "removed": [m for m in other.milestones if m not in self.milestones],
            }
        if self.tasks != other.tasks:
            changes["tasks"] = {
                "added": [t for t in self.tasks if t not in other.tasks],
                "removed": [t for t in other.tasks if t not in self.tasks],
            }
        if self.deadline_anchor != other.deadline_anchor:
            changes["deadline_anchor"] = {
                "old": other.deadline_anchor,
                "new": self.deadline_anchor,
            }
        if abs(self.confidence - other.confidence) > 0.01:
            changes["confidence"] = {
                "old": other.confidence,
                "new": self.confidence,
            }
        if self.warnings != other.warnings:
            changes["warnings"] = {
                "added": [w for w in self.warnings if w not in other.warnings],
                "removed": [w for w in other.warnings if w not in self.warnings],
            }
        return changes


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

def goal_decompose(
    goal: Goal,
    constraints: Optional[Dict[str, Any]] = None,
) -> DecompositionPlan:
    """Decompose a Goal into ordered milestones and tasks.

    Deterministic rule-based decomposition using goal.type/phase
    metadata from the Goal contract and constraint inputs.

    Rules:
    1. Milestones are ordered by phase sequence (discovery ->
       design -> build -> test -> launch -> review).
    2. Each milestone gets a deadline anchor derived from the
       goal deadline minus a reserved buffer (constant).
    3. Tasks attach to milestones with effort estimates from
       constraint inputs or a named default constant.
    4. Dependencies between milestones follow phase order
       (each milestone depends on the previous one).
    5. Missing deadline produces a warning and reduced confidence
       but never invents a date.
    6. Unknown goal type produces a warning and low confidence
       but still decomposes using a generic phase list.

    *constraints* may contain:
      - deadline: str (ISO date)
      - capacity_limit: float (total effort hours available)
      - dependencies: list of milestone ids this plan depends on
      - phase_override: list of phase names to use instead of default
      - task_effort: dict mapping milestone index to effort hours
    """
    constraints = constraints or {}
    warnings: List[str] = []
    confidence = DEFAULT_PLAN_CONFIDENCE

    goal_type = getattr(goal, "goal_name", None)
    goal_type_raw = _infer_goal_type(goal)

    # Missing deadline check.
    deadline_str = getattr(goal, "due_date", None) or constraints.get("deadline")
    if not deadline_str:
        warnings.append(
            "DecompositionWarning.MISSING_DEADLINE: goal has no due_date and no deadline in constraints"
        )
        confidence = min(confidence, LOW_CONFIDENCE_THRESHOLD)

    # Unknown goal type check.
    known_types = list(TYPE_PHASE_MAP.keys())
    if goal_type_raw not in known_types:
        warnings.append(
            "DecompositionWarning.UNKNOWN_GOAL_TYPE: goal type could not be inferred; using default phase order"
        )
        confidence = min(confidence, LOW_CONFIDENCE_THRESHOLD)

    # Determine phases.
    phase_override = constraints.get("phase_override")
    if phase_override:
        phases = [p for p in phase_override if p in PHASE_ORDER]
    else:
        phases = TYPE_PHASE_MAP.get(goal_type_raw, PHASE_ORDER)

    if not phases:
        warnings.append(
            "DecompositionWarning.NO_PHASE_MATCH: no valid phases found; cannot decompose"
        )
        return DecompositionPlan(
            plan_id=f"plan-{goal.goal_id}",
            goal_id=goal.goal_id,
            goal_name=goal.goal_name,
            goal_type=goal_type_raw,
            deadline_anchor=deadline_str,
            confidence=confidence,
            warnings=warnings,
            version=1,
            created_at=_iso_now(),
        )

    # Build milestones in phase order.
    milestones: List[Dict[str, Any]] = []
    tasks: List[Dict[str, Any]] = []
    prev_milestone_id: Optional[str] = None

    for idx, phase in enumerate(phases):
        milestone_id = f"ms-{goal.goal_id}-{idx + 1:03d}"
        milestone_name = f"{phase.title()} milestone"

        # Deadline anchor: goal deadline minus buffer, shifted per phase.
        milestone_deadline = None
        if deadline_str:
            milestone_deadline = _derive_milestone_deadline(
                deadline_str, idx, len(phases), DEFAULT_MILESTONE_BUFFER_DAYS
            )

        deps = []
        if prev_milestone_id:
            deps.append(prev_milestone_id)

        # Add external dependencies from constraints.
        external_deps = constraints.get("dependencies", [])
        if idx == 0 and external_deps:
            deps.extend(external_deps)

        milestone = {
            "milestone_id": milestone_id,
            "name": milestone_name,
            "phase": phase,
            "target_outcome": f"Complete {phase} work for goal {goal.goal_name}",
            "dependencies": deps,
            "deadline_anchor": milestone_deadline,
            "status": "pending",
        }
        milestones.append(milestone)

        # Attach tasks to milestone.
        effort_hours = constraints.get("task_effort", {}).get(
            str(idx), DEFAULT_TASK_EFFORT_HOURS
        )
        task = {
            "task_id": f"task-{goal.goal_id}-{idx + 1:03d}",
            "milestone_id": milestone_id,
            "title": f"{phase.title()} work for {goal.goal_name}",
            "effort_hours": effort_hours,
            "dependencies": [],
            "deadline": milestone_deadline,
            "status": "pending",
        }
        tasks.append(task)

        prev_milestone_id = milestone_id

    # Capacity check warning (informational only, no auto-trim).
    capacity_limit = constraints.get("capacity_limit")
    if capacity_limit is not None:
        total_effort = sum(t["effort_hours"] for t in tasks)
        if total_effort > capacity_limit:
            warnings.append(
                f"DecompositionWarning.OVERLOADED_CAPACITY: total effort {total_effort}h exceeds capacity {capacity_limit}h; feasibility check recommended"
            )

    plan = DecompositionPlan(
        plan_id=f"plan-{goal.goal_id}",
        goal_id=goal.goal_id,
        goal_name=goal.goal_name,
        goal_type=goal_type_raw,
        milestones=milestones,
        tasks=tasks,
        deadline_anchor=deadline_str,
        confidence=round(confidence, 2),
        warnings=warnings,
        version=1,
        created_at=_iso_now(),
    )

    return plan


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _infer_goal_type(goal: Goal) -> str:
    """Infer goal type from goal_name or description heuristics."""
    name = (goal.goal_name or "").lower()
    desc = (goal.description or "").lower()
    combined = f"{name} {desc}"

    tokens = combined.split()

    if any(t == w for t in tokens for w in ["bug", "fix", "defect", "issue"]):
        return "bugfix"
    if any(t == w for t in tokens for w in ["research", "investigate", "explore", "spike"]):
        return "research"
    if any(t == w for t in tokens for w in ["infra", "infrastructure", "platform", "migration"]):
        return "infra"
    if any(t == w for t in tokens for w in ["ops", "operat", "deploy", "runbook", "monitor"]):
        return "ops"
    if any(t == w for t in tokens for w in ["experiment", "hypothesis", "pilot"]):
        return "experiment"
    if any(t == w for t in tokens for w in ["feature", "new", "add", "implement", "build"]):
        return "feature"
    return "unknown"


def _derive_milestone_deadline(
    goal_deadline: str,
    phase_index: int,
    total_phases: int,
    buffer_days: int,
) -> str:
    """Derive a milestone deadline from the goal deadline.

    Distributes the goal deadline backwards across phases,
    reserving buffer_days at the end.  Deterministic: no clock
    reads; all arithmetic on the input string.
    """
    try:
        goal_dt = datetime.fromisoformat(goal_deadline)
    except (ValueError, TypeError):
        return goal_deadline

    total_buffer = buffer_days + (total_phases - phase_index - 1) * 2
    milestone_dt = goal_dt
    # Subtract buffer and phase spacing.
    from datetime import timedelta
    milestone_dt = milestone_dt - timedelta(days=total_buffer)
    return milestone_dt.date().isoformat()


def _iso_now() -> str:
    """Return UTC now as ISO date string.  Used only for metadata,
    never for logic decisions."""
    return datetime.utcnow().date().isoformat()