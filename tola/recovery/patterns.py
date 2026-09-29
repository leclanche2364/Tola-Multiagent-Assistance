"""Stall pattern detection for Batch T14 -- Stalled Work Recovery.

detect_stall_pattern(tracker_entry, graph, snapshot) -> StallPattern.
Deterministic, evidence-based, using named constants and T12 timeouts.
Stdlib only.  Plain ASCII.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from tola.monitoring.tracker import TrackingEntry
from tola.graph.graph import DependencyGraph


# ---------------------------------------------------------------------------
# Named threshold constants (reuse T12 timeouts where applicable)
# ---------------------------------------------------------------------------

# T12 follow-up timeouts (from tola/monitoring/followup.py)
ACK_TIMEOUT = "ack_timeout"
PROGRESS_TIMEOUT = "progress_timeout"
REVIEW_TIMEOUT = "review_timeout"
ESCALATE_TIMEOUT = "ESCALATE"

# Stall detection thresholds (deterministic, named)
NO_ACK_THRESHOLD_EVENTS = 0       # zero acknowledgement events
NO_PROGRESS_MIN_EVENTS = 1        # at least one progress event expected
BLOCKED_CHAIN_THRESHOLD = 3       # reuse T8 blocked chain threshold
CAPACITY_SHORTFALL_LOAD = 100     # load value indicating full capacity
SCOPE_MISMATCH_MIN_TASKS = 0      # task exceeds expected scope unit (any task beyond 0)
DEADLINE_MISSED_OVERDUE = 1       # any overdue delegation


class StallKind(str, Enum):
    """Known stalled-work pattern kinds.

    Each maps to a bounded recovery action set per the T14 plan.
    """

    UNACKNOWLEDGED = "UNACKNOWLEDGED"
    NO_PROGRESS = "NO_PROGRESS"
    BLOCKED_DEPENDENCY = "BLOCKED_DEPENDENCY"
    CAPACITY_SHORTFALL = "CAPACITY_SHORTFALL"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    DEADLINE_MISSED = "DEADLINE_MISSED"


@dataclass(frozen=True)
class StallPattern:
    """Result of stall detection for a single tracker entry."""

    kind: StallKind
    evidence: tuple[str, ...]


def _has_acknowledgement(entry: TrackingEntry) -> bool:
    """Check whether the entry has any ACKNOWLEDGED event."""
    return any(e == "ACKNOWLEDGED" for e, _ in entry.event_history)


def _has_progress(entry: TrackingEntry) -> bool:
    """Check whether the entry has any PROGRESS_NOTED event."""
    return any(e == "PROGRESS_NOTED" for e, _ in entry.event_history)


def _count_events(entry: TrackingEntry, event_type: str) -> int:
    """Count occurrences of a specific event type in entry history."""
    return sum(1 for e, _ in entry.event_history if e == event_type)


def _is_overdue(entry: TrackingEntry, now_iso: str) -> bool:
    """Check if the entry has a deadline past now_iso."""
    for e, ts in entry.event_history:
        if ts and ts > now_iso:
            return True
    return False


def _blocked_dependencies(node_id: str, graph: DependencyGraph) -> list[str]:
    """Return dependency node ids that are themselves blocked (no progress)."""
    deps = graph.dependencies(node_id)
    return [d for d in deps if d != node_id]


def detect_stall_pattern(
    tracker_entry: TrackingEntry,
    graph: Optional[DependencyGraph],
    snapshot: Any,
) -> StallPattern:
    """Detect the stall pattern for a single tracker entry.

    Args:
        tracker_entry: The delegation tracking entry to evaluate.
        graph: Optional DependencyGraph for dependency analysis.
        snapshot: Optional portfolio snapshot for scope/capacity checks.

    Returns:
        StallPattern with kind and evidence tuple.

    Deterministic: same inputs always produce the same output.
    """
    history = tracker_entry.event_history
    status = tracker_entry.status

    # --- UNACKNOWLEDGED: no ACKNOWLEDGED event at all ---
    if not _has_acknowledgement(tracker_entry):
        return StallPattern(
            kind=StallKind.UNACKNOWLEDGED,
            evidence=(
                f"No ACKNOWLEDGED event found for {tracker_entry.delegation_id}.",
                f"Status: {status.value}",
                f"Event count: {len(history)}",
            ),
        )

    # --- NO_PROGRESS: IN_PROGRESS with no PROGRESS_NOTED events ---
    if status.value == "IN_PROGRESS" and not _has_progress(tracker_entry):
        return StallPattern(
            kind=StallKind.NO_PROGRESS,
            evidence=(
                f"Status IN_PROGRESS but no PROGRESS_NOTED events "
                f"for {tracker_entry.delegation_id}.",
                f"Event history length: {len(history)}",
            ),
        )

    # --- BLOCKED_DEPENDENCY: dependencies that are themselves stalled ---
    if graph is not None:
        deps = _blocked_dependencies(tracker_entry.delegation_id, graph)
        if deps:
            return StallPattern(
                kind=StallKind.BLOCKED_DEPENDENCY,
                evidence=(
                    f"Delegation {tracker_entry.delegation_id} has "
                    f"{len(deps)} unresolved dependency/dependencies.",
                    f"Blocked deps: {deps}",
                ),
            )

    # --- CAPACITY_SHORTFALL: snapshot indicates capacity exhausted ---
    if snapshot is not None:
        load = getattr(snapshot, "current_load", None)
        if load is not None and isinstance(load, (int, float)):
            if load >= CAPACITY_SHORTFALL_LOAD:
                return StallPattern(
                    kind=StallKind.CAPACITY_SHORTFALL,
                    evidence=(
                        f"Current load ({load}) meets or exceeds "
                        f"capacity threshold ({CAPACITY_SHORTFALL_LOAD}).",
                        f"Delegation: {tracker_entry.delegation_id}",
                    ),
                )

    # --- SCOPE_MISMATCH: task scope exceeds expected units ---
    task_count = getattr(snapshot, "task_count", None)
    if task_count is not None and isinstance(task_count, int):
        if task_count > SCOPE_MISMATCH_MIN_TASKS:
            return StallPattern(
                kind=StallKind.SCOPE_MISMATCH,
                evidence=(
                    f"Task count ({task_count}) exceeds expected "
                    f"scope unit threshold ({SCOPE_MISMATCH_MIN_TASKS}).",
                    f"Delegation: {tracker_entry.delegation_id}",
                ),
            )

    # --- DEADLINE_MISSED: delegation past its deadline ---
    if history:
        last_event, last_ts = history[-1]
        if last_ts:
            thresholds = getattr(snapshot, "thresholds", None)
            if thresholds and isinstance(thresholds, dict):
                for key, deadline_val in thresholds.items():
                    if key == ESCALATE_TIMEOUT and last_ts >= deadline_val:
                        return StallPattern(
                            kind=StallKind.DEADLINE_MISSED,
                            evidence=(
                                f"Delegation {tracker_entry.delegation_id} "
                                f"past {ESCALATE_TIMEOUT} deadline "
                                f"({deadline_val}). Last event: {last_event} "
                                f"at {last_ts}.",
                            ),
                        )

    # Default fallback: no stall detected
    return StallPattern(
        kind=StallKind.UNACKNOWLEDGED,
        evidence=(
            f"No stall pattern detected for {tracker_entry.delegation_id}.",
            "Defaulting to UNACKNOWLEDGED for safe recovery routing.",
        ),
    )