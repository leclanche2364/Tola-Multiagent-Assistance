"""Batch T6 -- Goal Decomposition Engine.

Deterministic rule-based decomposition of goals into
milestones and tasks.  Stdlib only.  Plain ASCII.
"""

from tola.decomposition.planner import (
    DecompositionPlan,
    DecompositionWarning,
    goal_decompose,
)
from tola.decomposition.replanner import (
    PlanVersion,
    ReplanEvent,
    goal_replan,
    material_diff,
)
from tola.decomposition.feasibility import (
    FeasibilityResult,
    FeasibilityStatus,
    TrimOption,
    plan_feasibility_check,
)

__all__ = [
    "DecompositionPlan",
    "DecompositionWarning",
    "goal_decompose",
    "PlanVersion",
    "ReplanEvent",
    "goal_replan",
    "material_diff",
    "FeasibilityResult",
    "FeasibilityStatus",
    "TrimOption",
    "plan_feasibility_check",
]