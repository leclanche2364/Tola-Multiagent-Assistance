"""Rhythm schedule_outcomes module — Batch 7+ build.

schedule_outcomes(plan_to_rhythm, capacity_handoff) assigns outcomes to windows.
resolve_conflict(conflict, decision) applies Tola's conflict resolution decision.
"""

from __future__ import annotations

from typing import Any

from agents.daily_synthesis.contracts import (
    RhythmScheduleConflict,
    validate_payload,
)


def schedule_outcomes(
    plan_to_rhythm: dict[str, Any],
    capacity_handoff: dict[str, Any],
) -> dict[str, Any]:
    """Schedule outcomes from a daily_plan_to_rhythm.v1 plan into capacity windows.

    Returns either a schedule dict or a rhythm_schedule_conflict.v1 dict.
    Rhythm changes WHEN only — never alters outcome content, priority, or exact_action.
    """
    plan = validate_payload(plan_to_rhythm)

    agent_id = plan.get("agent_id")
    outcomes = plan.get("schedule_slots", [])
    windows = capacity_handoff.get("windows", [])
    recovery_buffer = capacity_handoff.get("recovery_buffer_minutes", 0)
    capacity_summary = capacity_handoff.get("capacity_summary", {})
    max_major_outcomes = capacity_summary.get("max_major_outcomes", 3)

    if not outcomes:
        return {
            "schema_version": "rhythm_schedule_outcomes.v1",
            "scheduled": [],
            "notes": "No outcomes to schedule",
        }

    # Sort windows by start time for deterministic assignment
    windows_sorted = sorted(windows, key=lambda w: w["start"])

    # Track remaining capacity per window
    window_slots: list[dict[str, Any]] = []
    for w in windows_sorted:
        effective = max(w["duration_minutes"] - recovery_buffer, 0)
        window_slots.append({
            "start": w["start"],
            "end": w["end"],
            "duration_minutes": w["duration_minutes"],
            "work_type": w["work_type"],
            "effective_minutes": effective,
            "hard_appointments": [],
        })

    scheduled: list[dict[str, Any]] = []
    scheduled_ids: set[str] = set()

    for i, outcome in enumerate(outcomes):
        outcome_id = outcome.get("id", f"outcome-{i}")
        duration = outcome.get("duration_minutes", 0)
        energy = outcome.get("energy", "medium")
        is_hard = outcome.get("is_hard_appointment", False)
        learning_detail = outcome.get("learning_detail", {})
        dependencies = outcome.get("dependencies", [])
        priority = outcome.get("priority", 0)

        # Check dependencies are already scheduled
        for dep_id in dependencies:
            if dep_id not in scheduled_ids:
                return _make_conflict(
                    agent_id=agent_id,
                    outcome_id=outcome_id,
                    reason="dependency_blocked",
                    required_minutes=duration,
                    available_minutes=_total_effective(window_slots),
                    possible_alternatives=["defer"],
                )

        # Check max_major_outcomes (context-switch limit from capacity_summary)
        if len(scheduled) >= max_major_outcomes:
            return _make_conflict(
                agent_id=agent_id,
                outcome_id=outcome_id,
                reason="capacity_exceeded",
                required_minutes=duration,
                available_minutes=_total_effective(window_slots),
                possible_alternatives=["defer", "reduce_scope"],
            )

        # Try to find a compatible window
        assigned = False
        conflict_reason = "capacity_exceeded"
        for ws in window_slots:
            fits, reason = _window_fits(ws, duration, energy, is_hard)
            if fits:
                ws["effective_minutes"] -= duration
                if is_hard:
                    ws["hard_appointments"].append(outcome_id)
                scheduled_ids.add(outcome_id)
                scheduled.append({
                    "outcome_id": outcome_id,
                    "window_start": ws["start"],
                    "window_end": ws["end"],
                    "assigned_minutes": duration,
                    "learning_detail": learning_detail,
                    "priority": priority,
                })
                assigned = True
                break
            conflict_reason = reason or conflict_reason

        if not assigned:
            return _make_conflict(
                agent_id=agent_id,
                outcome_id=outcome_id,
                reason=conflict_reason,
                required_minutes=duration,
                available_minutes=_total_effective(window_slots),
                possible_alternatives=["split_task", "reduce_scope", "defer"],
            )

    return {
        "schema_version": "rhythm_schedule_outcomes.v1",
        "scheduled": scheduled,
        "notes": f"Scheduled {len(scheduled)} outcomes",
    }


def resolve_conflict(
    conflict: dict[str, Any],
    decision: str,
) -> dict[str, Any]:
    """Apply Tola's conflict resolution decision.

    decision ∈ {split, reduce_scope, defer, select_alternative}
    Returns an updated plan directive. Tola owns the decision; Rhythm only executes.
    """
    valid_decisions = {"split", "reduce_scope", "defer", "select_alternative"}
    if decision not in valid_decisions:
        raise ValueError(
            f"Invalid decision: {decision!r}. Must be one of {valid_decisions}"
        )

    outcome_id = conflict.get("outcome_id")
    alternatives = conflict.get("possible_alternatives", [])

    if decision == "split":
        return {
            "action": "split",
            "outcome_id": outcome_id,
            "notes": "Task split at internal boundaries; exact_action preserved in each part",
        }
    elif decision == "reduce_scope":
        return {
            "action": "reduce_scope",
            "outcome_id": outcome_id,
            "notes": "Task scope reduced; exact_action preserved",
        }
    elif decision == "defer":
        return {
            "action": "defer",
            "outcome_id": outcome_id,
            "notes": "Task deferred to next available window",
        }
    elif decision == "select_alternative":
        alt = alternatives[0] if alternatives else "defer"
        return {
            "action": "select_alternative",
            "outcome_id": outcome_id,
            "alternative": alt,
            "notes": f"Selected alternative: {alt}",
        }

    # Should not reach here
    return {
        "action": "defer",
        "outcome_id": outcome_id,
        "notes": "Default fallback",
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _total_effective(window_slots: list[dict[str, Any]]) -> int:
    return sum(ws["effective_minutes"] for ws in window_slots)


def _window_fits(
    ws: dict[str, Any],
    duration: int,
    energy: str,
    is_hard: bool,
) -> tuple[bool, str]:
    """Check if an outcome can fit in a window. Returns (fits, reason_if_not)."""
    if is_hard and ws["hard_appointments"]:
        return False, "overlap"
    if duration > ws["effective_minutes"]:
        return False, "capacity_exceeded"
    if energy == "deep" and ws["work_type"] != "deep":
        return False, "capacity_exceeded"
    return True, ""


def _make_conflict(
    agent_id: str | None,
    outcome_id: str,
    reason: str,
    required_minutes: int,
    available_minutes: int,
    possible_alternatives: list[str],
) -> dict[str, Any]:
    """Build a rhythm_schedule_conflict.v1 dict."""
    conflict = RhythmScheduleConflict(
        agent_id=agent_id,
        outcome_id=outcome_id,
        reason=reason,
        required_minutes=required_minutes,
        available_minutes=available_minutes,
        possible_alternatives=possible_alternatives,
    )
    return conflict.validate()