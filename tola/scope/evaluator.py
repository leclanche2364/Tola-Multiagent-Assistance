# Scope evaluator for Batch T16.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Verdict(str, Enum):
    START = "START"
    SHAPE_SMALLER = "SHAPE_SMALLER"
    DEFER = "DEFER"
    STOP = "STOP"
    NEEDS_USER_DECISION = "NEEDS_USER_DECISION"


@dataclass(frozen=True)
class ScopeDecision:
    verdict: Verdict
    reasoning: List[str] = field(default_factory=list)
    opportunity_cost: str = ""
    smallest_version: str = ""
    stop_condition: str = ""
    displaces: List[str] = field(default_factory=list)


# Evaluation dimension rubric keys (named constants).
DIM_ACTIVE_GOAL = "active_goal_alignment"
DIM_EXPECTED_VALUE = "expected_value"
DIM_APPETITE = "appetite"
DIM_DEPENDENCIES = "dependencies"
DIM_OPPORTUNITY_COST = "opportunity_cost"
DIM_AMBIGUITY = "ambiguity"


def _get_active_goals(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return active goals from context; empty list when absent."""
    return context.get("active_goals", [])


def _proposal_matches_goal(proposal: Dict[str, Any], goal: Dict[str, Any]) -> bool:
    """Check whether proposal serves a registered active goal."""
    proposal_tags = set(proposal.get("tags", []))
    goal_tags = set(goal.get("tags", []))
    goal_name = goal.get("name", "")
    goal_id = goal.get("id", "")
    proposal_goal_refs = set(proposal.get("goal_refs", []))
    if goal_id in proposal_goal_refs or goal_name in proposal.get("goal_refs", []):
        return True
    if proposal_tags & goal_tags:
        return True
    return False


def _is_aligned(proposal: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """True when proposal serves at least one registered active goal."""
    active_goals = _get_active_goals(context)
    if not active_goals:
        return False
    return any(_proposal_matches_goal(proposal, g) for g in active_goals)


def _expected_value(proposal: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Return evidence-based expected value from context."""
    evidence = proposal.get("evidence", context.get("evidence", ""))
    value_score = proposal.get("expected_value", context.get("expected_value_score", 0))
    return f"expected_value={value_score}; evidence={evidence}"


def _value_tier(value_score: float) -> str:
    if value_score >= 0.7:
        return "high"
    if value_score >= 0.4:
        return "medium"
    return "low"


def _appetite(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return remaining capacity from Rhythm summary in context."""
    return context.get("capacity_summary", context.get("appetite", {}))


def _has_capacity(context: Dict[str, Any]) -> bool:
    """True when context signals remaining capacity."""
    cap = _appetite(context)
    if isinstance(cap, dict):
        remaining = cap.get("remaining_capacity", cap.get("available_slots", 0))
        if isinstance(remaining, (int, float)) and remaining > 0:
            return True
        active = cap.get("active_tasks", 0)
        max_tasks = cap.get("max_parallel_tasks", 0)
        if isinstance(active, int) and isinstance(max_tasks, int) and active < max_tasks:
            return True
    return False


def _missing_dependencies(proposal: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
    """Return list of missing dependencies, empty when none."""
    required = proposal.get("dependencies", [])
    available = set(context.get("available_dependencies", []))
    return [dep for dep in required if dep not in available]


def _opportunity_cost(proposal: Dict[str, Any], context: Dict[str, Any]) -> str:
    """What this proposal displaces from current committed work."""
    committed = context.get("current_priorities", context.get("committed_work", []))
    displaces = proposal.get("displaces", [])
    if displaces:
        return f"displaces={displaces}; current_priorities={committed}"
    if committed:
        return f"displaces=current_priority_items={committed}"
    return "displaces=none"


def _smallest_viable_version(proposal: Dict[str, Any]) -> str:
    """Return the smallest viable version of the proposal."""
    sv = proposal.get("smallest_viable_version", "")
    if sv:
        return sv
    scope = proposal.get("scope", "")
    if scope:
        return f"Reduce scope to: {scope}"
    return "Reduce scope to minimal viable slice"


def _stop_condition(proposal: Dict[str, Any]) -> str:
    """Return the stop condition for a STOP verdict."""
    return proposal.get("stop_condition", "Do not start; revisit when alignment or value changes")


def _revisit_condition(proposal: Dict[str, Any], context: Dict[str, Any]) -> str:
    """Return revisit condition for DEFER verdicts."""
    cap = _appetite(context)
    trigger = proposal.get("revisit_trigger", "")
    if trigger:
        return trigger
    if isinstance(cap, dict):
        threshold = cap.get("capacity_threshold", "remaining_capacity > 0")
        return f"Revisit when {threshold}"
    return "Revisit when capacity opens"


def evaluate_scope(
    proposal: Dict[str, Any],
    context: Dict[str, Any],
) -> ScopeDecision:
    """Evaluate a proposed piece of work against active goals, capacity,
    and opportunity cost. Returns a bounded ScopeDecision.

    Evaluation dimensions (rubric):
    - active_goal_alignment: proposal serves a registered active goal
    - expected_value: evidence-based, from context
    - appetite: remaining capacity from Rhythm summary in context
    - dependencies: missing dependencies block the proposal
    - opportunity_cost: what it displaces from current committed work
    - ambiguity: consequential + ambiguous -> NEEDS_USER_DECISION
    """
    reasoning: List[str] = []
    displaces: List[str] = []

    # Dimension: active goal alignment.
    aligned = _is_aligned(proposal, context)
    reasoning.append(f"{DIM_ACTIVE_GOAL}: aligned={aligned}; active_goals={_get_active_goals(context)}")

    # Dimension: expected value.
    value_score = proposal.get("expected_value", context.get("expected_value_score", 0))
    tier = _value_tier(value_score)
    reasoning.append(f"{DIM_EXPECTED_VALUE}: expected_value={value_score}; evidence={proposal.get('evidence', context.get('evidence', ''))}; tier={tier}")

    # Dimension: appetite / capacity.
    cap = _appetite(context)
    has_cap = _has_capacity(context)
    reasoning.append(f"{DIM_APPETITE}: has_capacity={has_cap}; remaining_capacity={cap.get('remaining_capacity', cap.get('available_slots', 'N/A'))}; active_tasks={cap.get('active_tasks', 'N/A')}; max_parallel_tasks={cap.get('max_parallel_tasks', 'N/A')}")

    # Dimension: dependencies.
    missing = _missing_dependencies(proposal, context)
    reasoning.append(f"{DIM_DEPENDENCIES}: missing={missing}")

    # Dimension: opportunity cost.
    oc = _opportunity_cost(proposal, context)
    reasoning.append(f"{DIM_OPPORTUNITY_COST}: {oc}")
    displaces = proposal.get("displaces", [])
    if not displaces and "current_priorities" in oc:
        cp = context.get("current_priorities", context.get("committed_work", []))
        displaces = list(cp) if isinstance(cp, list) else [str(cp)]

    # Dimension: ambiguity.
    is_ambiguous = proposal.get("ambiguous", False)
    is_consequential = proposal.get("consequential", False)
    reasoning.append(f"{DIM_AMBIGUITY}: ambiguous={is_ambiguous}; consequential={is_consequential}")

    # --- Verdict logic ---
    # Consequential + ambiguous -> NEEDS_USER_DECISION (never guessed).
    if is_consequential and is_ambiguous:
        return ScopeDecision(
            verdict=Verdict.NEEDS_USER_DECISION,
            reasoning=reasoning,
            opportunity_cost=oc,
            smallest_version=_smallest_viable_version(proposal),
            stop_condition="",
            displaces=displaces,
        )

    # Oversized (declares a smallest viable version -> acknowledges the
    # full scope exceeds appetite) -> SHAPE_SMALLER, ahead of other stops.
    if aligned and proposal.get("smallest_viable_version"):
        return ScopeDecision(
            verdict=Verdict.SHAPE_SMALLER,
            reasoning=reasoning + [
                f"Scope exceeds available appetite (remaining_capacity={cap.get('remaining_capacity', cap.get('available_slots', 'N/A'))}); smallest viable version required",
            ],
            opportunity_cost=oc,
            smallest_version=_smallest_viable_version(proposal),
            stop_condition="",
            displaces=displaces,
        )

    # Missing dependencies -> blocked (STOP).
    if missing:
        return ScopeDecision(
            verdict=Verdict.STOP,
            reasoning=reasoning + [f"Blocked by missing dependencies: {missing}"],
            opportunity_cost=oc,
            smallest_version="",
            stop_condition=f"Resolve dependencies: {missing}",
            displaces=displaces,
        )

    # Aligned + high value + capacity -> START.
    if aligned and tier == "high" and has_cap:
        return ScopeDecision(
            verdict=Verdict.START,
            reasoning=reasoning,
            opportunity_cost=oc,
            smallest_version="",
            stop_condition="",
            displaces=displaces,
        )

    # Aligned + high value but no capacity now -> DEFER.
    if aligned and tier == "high" and not has_cap:
        return ScopeDecision(
            verdict=Verdict.DEFER,
            reasoning=reasoning + [f"No capacity now; value intact; {_revisit_condition(proposal, context)}"],
            opportunity_cost=oc,
            smallest_version="",
            stop_condition="",
            displaces=displaces,
        )

    # Oversized (aligned but scope exceeds capacity) -> SHAPE_SMALLER.
    if aligned and tier in ("high", "medium") and not has_cap:
        return ScopeDecision(
            verdict=Verdict.SHAPE_SMALLER,
            reasoning=reasoning + [f"Scope exceeds available appetite (remaining_capacity={cap.get('remaining_capacity', cap.get('available_slots', 'N/A'))}); smallest viable version required"],
            opportunity_cost=oc,
            smallest_version=_smallest_viable_version(proposal),
            stop_condition="",
            displaces=displaces,
        )

    # Low value or not aligned -> STOP.
    if not aligned or tier == "low":
        return ScopeDecision(
            verdict=Verdict.STOP,
            reasoning=reasoning + [f"Not aligned or low value (tier={tier}, aligned={aligned})"],
            opportunity_cost=oc,
            smallest_version="",
            stop_condition=_stop_condition(proposal),
            displaces=displaces,
        )

    # Fallback: medium value, not aligned -> STOP.
    return ScopeDecision(
        verdict=Verdict.STOP,
        reasoning=reasoning + [f"Does not meet START criteria (aligned={aligned}, tier={tier}, has_cap={has_cap})"],
        opportunity_cost=oc,
        smallest_version="",
        stop_condition=_stop_condition(proposal),
        displaces=displaces,
    )
