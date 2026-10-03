"""Project status handoff v1 producer — validates against project_status_handoff.v1 contract.

One stable schema per project. Registry of active projects:
Shiftlyx, Revalidation Copilot, VocalGaze, IntenSIQ, OpenClaw agent system,
Florence (genuinely active only), ICU/QI work (when active).

Y-Site IV Compatibility Checker is PARKED and MUST be excluded from the
registry and from any output.

Reads state from caller-supplied dict OR a fixture file path (parameterized).
Never reads from live sources in this batch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.daily_synthesis.contracts import ProjectStatusHandoff, ValidationError


# ---------------------------------------------------------------------------
# Active project registry — Y-Site IV Compatibility Checker is PARKED
# ---------------------------------------------------------------------------

ACTIVE_PROJECTS = frozenset({
    "Shiftlyx",
    "Revalidation Copilot",
    "VocalGaze",
    "IntenSIQ",
    "OpenClaw agent system",
    "Florence",
    "ICU/QI work",
})

PARKED_PROJECTS = frozenset({
    "Y-Site IV Compatibility Checker",
})


@dataclass
class ProjectState:
    project_id: str
    current_phase: str = "unknown"
    latest_completed_milestone: str = ""
    current_work_in_progress: str = ""
    next_action: str = ""
    blocker: str = ""
    dependencies: list[str] = field(default_factory=list)
    deadline: Optional[str] = None
    estimated_effort_minutes: int = 0
    energy_required: str = "medium"
    definition_of_done: str = ""
    strategic_notes: str = ""
    specialist_recommendation: str = ""
    freshness_status: str = "unknown"


_CONTRACT_FIELDS = set(ProjectStatusHandoff.__dataclass_fields__.keys())


def _load_state(source: Any) -> dict[str, Any]:
    """Load state from a dict or a fixture file path."""
    if isinstance(source, dict):
        return source
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Fixture file not found: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    raise TypeError(f"source must be a dict or a file path, got {type(source).__name__}")


def _validate_project_id(project_id: str) -> None:
    """Reject parked projects and unknown projects."""
    if project_id in PARKED_PROJECTS:
        raise ValidationError(
            f"project_status_handoff.v1: project '{project_id}' is PARKED "
            "and must be excluded from the registry and all output."
        )
    if project_id not in ACTIVE_PROJECTS:
        raise ValidationError(
            f"project_status_handoff.v1: unknown project '{project_id}'. "
            f"Active projects are: {sorted(ACTIVE_PROJECTS)}"
        )


def _freshness_from_timestamp(ts: Optional[str]) -> str:
    """Return freshness based on timestamp age.

    fresh: <=24h, stale: >24h (any valid timestamp), unknown: missing/unparseable.
    """
    if not ts:
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if age_h <= 24:
            return "fresh"
        return "stale"
    except (ValueError, TypeError):
        return "unknown"


def produce_project_status_handoff(
    agent_id: str,
    source: Any,
    project_id: str,
) -> dict[str, Any]:
    """Produce and validate a project_status_handoff.v1 payload.

    Args:
        agent_id: Identifier for the calling agent.
        source: Dict of state or path to a fixture JSON file.
        project_id: Must be in ACTIVE_PROJECTS; PARKED projects raise ValidationError.

    Returns:
        Validated dict conforming to project_status_handoff.v1 with propose-mode extensions.
    """
    _validate_project_id(project_id)
    state = _load_state(source)

    # State may be a per-project dict or a top-level dict with project key
    # When source is a file path (Path/str), state is the loaded dict.
    # When source is already a dict, use it directly.
    if isinstance(state, dict) and project_id in state:
        project_state = state[project_id]
    elif isinstance(state, dict) and project_id not in state:
        # Project key missing — mark fields as unknown, never fabricate
        project_state = {}
    else:
        project_state = state

    ps = ProjectState(
        project_id=project_id,
        current_phase=project_state.get("current_phase", "unknown"),
        latest_completed_milestone=project_state.get("latest_completed_milestone", ""),
        current_work_in_progress=project_state.get("current_work_in_progress", ""),
        next_action=project_state.get("next_action", ""),
        blocker=project_state.get("blocker", ""),
        dependencies=project_state.get("dependencies", []),
        deadline=project_state.get("deadline"),
        estimated_effort_minutes=project_state.get("estimated_effort_minutes", 0),
        energy_required=project_state.get("energy_required", "medium"),
        definition_of_done=project_state.get("definition_of_done", ""),
        strategic_notes=project_state.get("strategic_notes", ""),
        specialist_recommendation=project_state.get("specialist_recommendation", ""),
        freshness_status=_freshness_from_timestamp(project_state.get("last_updated")),
    )

    handoff = ProjectStatusHandoff(
        schema_version="project_status_handoff.v1",
        agent_id=agent_id,
        project_id=project_id,
        status=ps.current_phase,
        summary=(
            f"{project_id}: {ps.current_phase}. "
            f"Last milestone: {ps.latest_completed_milestone or 'none yet'}. "
            f"Next: {ps.next_action or 'none scheduled'}."
        ),
        next_action=ps.next_action if ps.next_action else "",
    )

    result = handoff.validate()

    # Attach propose-mode extensions
    result["current_phase"] = ps.current_phase
    result["latest_completed_milestone"] = ps.latest_completed_milestone
    result["current_work_in_progress"] = ps.current_work_in_progress
    result["next_action"] = ps.next_action
    result["blocker"] = ps.blocker
    result["dependencies"] = ps.dependencies
    result["deadline"] = ps.deadline
    result["estimated_effort_minutes"] = ps.estimated_effort_minutes
    result["energy_required"] = ps.energy_required
    result["definition_of_done"] = ps.definition_of_done
    result["strategic_notes"] = ps.strategic_notes
    result["specialist_recommendation"] = ps.specialist_recommendation
    result["freshness_status"] = ps.freshness_status

    return result
