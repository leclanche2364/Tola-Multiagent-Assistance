"""Feasibility checker for Batch T6.

Compares plan effort against a capacity_summary input
and returns a FeasibilityResult with recommendations
(drop/defer/extend) that are never auto-applied.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from tola.decomposition.planner import DecompositionPlan


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    OVERLOADED = "OVERLOADED"
    UNDERLOADED = "UNDERLOADED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


# ---------------------------------------------------------------------------
# Trim options (recommendations only, never auto-applied)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrimOption:
    """A suggested trim action.  Never auto-applied."""

    action: str  # "drop", "defer", "extend"
    target: str  # milestone_id or task_id
    reason: str
    effort_saved_hours: float = 0.0


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeasibilityResult:
    """Result of comparing plan effort against capacity."""

    status: FeasibilityStatus
    total_effort_hours: float = 0.0
    capacity_hours: float = 0.0
    utilization_pct: float = 0.0
    trim_options: List[TrimOption] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------

def plan_feasibility_check(
    plan: DecompositionPlan,
    capacity_summary: Dict[str, Any],
) -> FeasibilityResult:
    """Check whether a decomposition plan is feasible against capacity.

    *capacity_summary* is an input dict, not computed internally.
    Expected keys:
      - capacity_hours: float (total available effort hours)
      - agent_count: int (optional, for per-agent checks)
      - period_days: int (optional, planning horizon)

    Returns a FeasibilityResult with:
      - status: FEASIBLE / OVERLOADED / UNDERLOADED / INSUFFICIENT_DATA
      - trim_options: drop/defer/extend recommendations (never auto-applied)
      - warnings when inputs are missing or incomplete

    IMPORTANT: This function never modifies the plan, never writes
    to My Rhythm, and never applies trim options.  It only recommends.
    """
    # Compute total effort from the plan.
    total_effort = sum(t.get("effort_hours", 0) for t in plan.tasks)

    capacity_hours = capacity_summary.get("capacity_hours")
    if capacity_hours is None:
        return FeasibilityResult(
            status=FeasibilityStatus.INSUFFICIENT_DATA,
            total_effort_hours=total_effort,
            capacity_hours=0.0,
            utilization_pct=0.0,
            warnings=["capacity_summary missing 'capacity_hours'; cannot assess feasibility"],
            confidence=0.0,
        )

    utilization = (total_effort / capacity_hours * 100) if capacity_hours > 0 else 0.0

    trim_options: List[TrimOption] = []
    warnings: List[str] = []

    if utilization > 100:
        # Overloaded: generate trim options (never auto-apply).
        excess = total_effort - capacity_hours
        trim_options = _suggest_trim(plan, excess)
        warnings.append(
            f"Plan overloaded by {excess:.1f}h; trim options provided as recommendations only"
        )
        status = FeasibilityStatus.OVERLOADED
        confidence = 0.9
    elif utilization > 80:
        warnings.append(
            f"Plan utilization at {utilization:.1f}% is above 80% threshold; monitor capacity"
        )
        status = FeasibilityStatus.FEASIBLE
        confidence = 0.7
    else:
        status = FeasibilityStatus.FEASIBLE
        confidence = 0.95

    return FeasibilityResult(
        status=status,
        total_effort_hours=total_effort,
        capacity_hours=capacity_hours,
        utilization_pct=round(utilization, 1),
        trim_options=trim_options,
        warnings=warnings,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Trim suggestion (recommendations only)
# ---------------------------------------------------------------------------

def _suggest_trim(plan: DecompositionPlan, excess_hours: float) -> List[TrimOption]:
    """Suggest drop/defer/extend options for overloaded plans.

    These are recommendations only.  No option is auto-applied.
    """
    options: List[TrimOption] = []

    # Sort tasks by effort descending for biggest impact.
    sorted_tasks = sorted(
        plan.tasks, key=lambda t: t.get("effort_hours", 0), reverse=True
    )

    cumulative = 0.0
    for t in sorted_tasks:
        effort = t.get("effort_hours", 0)
        if cumulative >= excess_hours:
            break
        cumulative += effort
        options.append(
            TrimOption(
                action="drop",
                target=t["task_id"],
                reason=f"Dropping {t['title']} saves {effort}h",
                effort_saved_hours=effort,
            )
        )

    # Defer option: defer the last milestone.
    if plan.milestones:
        last_ms = plan.milestones[-1]
        options.append(
            TrimOption(
                action="defer",
                target=last_ms["milestone_id"],
                reason=f"Defer {last_ms['name']} to a later period",
                effort_saved_hours=0.0,
            )
        )

    # Extend option: extend the deadline.
    if plan.deadline_anchor:
        options.append(
            TrimOption(
                action="extend",
                target=plan.plan_id,
                reason=f"Extend deadline beyond {plan.deadline_anchor} to reduce pressure",
                effort_saved_hours=0.0,
            )
        )

    return options