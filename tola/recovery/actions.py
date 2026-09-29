"""Recovery action proposal for Batch T14 -- Stalled Work Recovery.

propose_recovery(pattern, context) -> RecoveryPlan.
Deterministic, bounded, safe: no action outside the allowed set.
Stdlib only.  Plain ASCII.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from tola.recovery.patterns import StallKind, StallPattern


# ---------------------------------------------------------------------------
# Allowed action set (frozen -- no action outside this set can ever be produced)
# ---------------------------------------------------------------------------

class RecoveryAction(str, Enum):
    """Bounded recovery actions for stalled work.

    The complete allowed set per the T14 plan.
    """

    REQUEST_MISSING_INFO = "REQUEST_MISSING_INFO"
    RESCOPE = "RESCOPE"
    SPLIT_TASK = "SPLIT_TASK"
    QUERY_RHYTHM = "QUERY_RHYTHM"
    REORDER_DEPENDENCIES = "REORDER_DEPENDENCIES"
    BOUNDED_REASSIGNMENT = "BOUNDED_REASSIGNMENT"
    ESCALATE = "ESCALATE"
    STOP = "STOP"


ALLOWED_ACTIONS: frozenset[str] = frozenset(
    a.value for a in RecoveryAction
)


# ---------------------------------------------------------------------------
# Recovery plan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecoveryPlan:
    """Bounded recovery proposal for a stalled delegation."""

    actions: tuple[str, ...]
    requires_approval: bool
    rationale: str


# ---------------------------------------------------------------------------
# Capability class mapping (T4 registry reuse)
# ---------------------------------------------------------------------------

# Domains grouped by capability class for bounded reassignment
CAPABILITY_CLASSES: dict[str, frozenset[str]] = {
    "scheduling": frozenset({"rhythm"}),
    "capacity": frozenset({"rhythm"}),
    "product": frozenset({"growth"}),
    "growth": frozenset({"growth"}),
    "learning": frozenset({"scholar"}),
    "scholar": frozenset({"scholar"}),
    "marketing": frozenset({"marketing"}),
}


def _same_capability_class(
    source_agent: str,
    target_agent: str,
) -> bool:
    """Check if two agents share a capability class (T4 registry)."""
    for agents in CAPABILITY_CLASSES.values():
        if source_agent in agents and target_agent in agents:
            return True
    return False


def _valid_reorder_exists(
    pattern: StallPattern,
    graph: Any,
) -> bool:
    """Check whether a valid dependency reordering exists in the T7 graph."""
    if graph is None:
        return False
    try:
        order = graph.topological_order()
        return len(order) > 0
    except ValueError:
        return False


def _propose_for_unacknowledged(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """UNACKNOWLEDGED -> REQUEST_MISSING_INFO (never reassignment first)."""
    return RecoveryPlan(
        actions=(RecoveryAction.REQUEST_MISSING_INFO.value,),
        requires_approval=False,
        rationale=(
            "No acknowledgement received. "
            "First recovery step is a targeted request for missing "
            "specialist information, not reassignment."
        ),
    )


def _propose_for_no_progress(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """NO_PROGRESS -> REQUEST_MISSING_INFO or QUERY_RHYTHM for capacity."""
    load = context.get("current_load", 0)
    if isinstance(load, (int, float)) and load >= 100:
        return RecoveryPlan(
            actions=(RecoveryAction.QUERY_RHYTHM.value,),
            requires_approval=False,
            rationale=(
                "No progress and capacity is at or above threshold. "
                "Query Rhythm for capacity assessment before any "
                "reassignment or rescope."
            ),
        )
    return RecoveryPlan(
        actions=(RecoveryAction.REQUEST_MISSING_INFO.value,),
        requires_approval=False,
        rationale=(
            "No progress events recorded. "
            "Request missing information from the specialist "
            "before escalating or reassigning."
        ),
    )


def _propose_for_blocked_dependency(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """BLOCKED_DEPENDENCY -> REORDER_DEPENDENCIES if valid reorder exists,
    otherwise ESCALATE. Never guess."""
    graph = context.get("graph")
    if graph is not None and _valid_reorder_exists(pattern, graph):
        return RecoveryPlan(
            actions=(RecoveryAction.REORDER_DEPENDENCIES.value,),
            requires_approval=False,
            rationale=(
                "A valid dependency reordering exists in the T7 graph. "
                "Reorder dependencies to unblock the stalled work."
            ),
        )
    return RecoveryPlan(
        actions=(RecoveryAction.ESCALATE.value,),
        requires_approval=True,
        rationale=(
            "No valid reordering exists for the blocked dependency. "
            "Escalate rather than guess or silently proceed."
        ),
    )


def _propose_for_capacity_shortfall(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """CAPACITY_SHORTFALL -> QUERY_RHYTHM then RESCOPE/SPLIT_TASK.
    Reassignment only BOUNDED (same capability class) and ALWAYS
    requires_approval=True."""
    source_agent = context.get("source_agent", "")
    target_agent = context.get("target_agent", "")

    actions: list[str] = [RecoveryAction.QUERY_RHYTHM.value]

    # Bounded reassignment only if same capability class
    if source_agent and target_agent:
        if _same_capability_class(source_agent, target_agent):
            actions.append(RecoveryAction.BOUNDED_REASSIGNMENT.value)
        else:
            # Different capability class -> cannot reassign, propose split
            actions.append(RecoveryAction.SPLIT_TASK.value)
    else:
        # No agent info -> propose rescope
        actions.append(RecoveryAction.RESCOPE.value)

    return RecoveryPlan(
        actions=tuple(actions),
        requires_approval=True,
        rationale=(
            "Capacity shortfall detected. Query Rhythm first, then "
            "propose bounded recovery. Reassignment requires approval "
            "and is only within the same capability class per T4 registry."
        ),
    )


def _propose_for_scope_mismatch(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """SCOPE_MISMATCH -> SPLIT_TASK or RESCOPE."""
    task_count = context.get("task_count", 0)
    if isinstance(task_count, int) and task_count > 1:
        return RecoveryPlan(
            actions=(RecoveryAction.SPLIT_TASK.value,),
            requires_approval=False,
            rationale=(
                "Task scope exceeds expected units. "
                "Split the task into smaller, manageable pieces."
            ),
        )
    return RecoveryPlan(
        actions=(RecoveryAction.RESCOPE.value,),
        requires_approval=False,
        rationale=(
            "Scope mismatch detected. Rescope the work to fit "
            "within expected boundaries."
        ),
    )


def _propose_for_deadline_missed(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """DEADLINE_MISSED -> ESCALATE or STOP. Never silent rescope."""
    return RecoveryPlan(
        actions=(RecoveryAction.ESCALATE.value,),
        requires_approval=True,
        rationale=(
            "Deadline missed. Escalate per T8 rules. "
            "Never silently rescoped or reassigned."
        ),
    )


# ---------------------------------------------------------------------------
# Pattern -> action mapping (deterministic dispatch)
# ---------------------------------------------------------------------------

_PATTERN_HANDLERS: dict[str, Any] = {
    StallKind.UNACKNOWLEDGED.value: _propose_for_unacknowledged,
    StallKind.NO_PROGRESS.value: _propose_for_no_progress,
    StallKind.BLOCKED_DEPENDENCY.value: _propose_for_blocked_dependency,
    StallKind.CAPACITY_SHORTFALL.value: _propose_for_capacity_shortfall,
    StallKind.SCOPE_MISMATCH.value: _propose_for_scope_mismatch,
    StallKind.DEADLINE_MISSED.value: _propose_for_deadline_missed,
}


def propose_recovery(
    pattern: StallPattern,
    context: dict[str, Any],
) -> RecoveryPlan:
    """Propose a bounded recovery plan for a detected stall pattern.

    Args:
        pattern: The detected StallPattern (from detect_stall_pattern).
        context: Dict with optional keys: graph, snapshot, current_load,
                 source_agent, target_agent, task_count.

    Returns:
        RecoveryPlan with actions tuple, approval flag, and rationale.

    Deterministic: same pattern + context always produces the same plan.
    All proposed actions are guaranteed to be within ALLOWED_ACTIONS.
    """
    handler = _PATTERN_HANDLERS.get(pattern.kind.value)
    if handler is None:
        return RecoveryPlan(
            actions=(RecoveryAction.ESCALATE.value,),
            requires_approval=True,
            rationale=f"Unknown stall pattern '{pattern.kind.value}'; escalate.",
        )

    plan = handler(pattern, context)

    # Validate all actions are within the allowed set (safety guard)
    for action in plan.actions:
        if action not in ALLOWED_ACTIONS:
            raise ValueError(
                f"Proposed action '{action}' is not in ALLOWED_ACTIONS. "
                f"This is a programming error."
            )

    return plan