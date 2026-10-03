"""Growth handoff v1 producer — validates against growth_handoff.v1 contract.

Producer for growth domain only. Tola decides priority; this module never
ranks cross-domain. Fields: latest metrics, active experiments, experiments
awaiting analysis, execution tasks (campaign/Metricool), blockers, deadlines,
high-value next actions with estimated effort + freshness metadata.

Reads state from caller-supplied dict OR a fixture file path (parameterized).
Never reads from live sources in this batch.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.daily_synthesis.contracts import GrowthHandoff, ValidationError


@dataclass
class LatestMetrics:
    revenue: Optional[float] = None
    mrr: Optional[float] = None
    active_users: Optional[int] = None
    conversion_rate: Optional[float] = None
    churn_rate: Optional[float] = None
    last_updated: Optional[str] = None


@dataclass
class Experiment:
    name: str
    status: str  # active, awaiting_analysis, completed
    variant: str = ""
    start_date: str = ""
    end_date: str = ""
    metric_impact: Optional[float] = None


@dataclass
class ExecutionTask:
    title: str
    platform: str  # campaign, metricool, etc.
    status: str  # pending, in_progress, completed
    due_date: Optional[str] = None
    estimated_minutes: int = 30


@dataclass
class NextAction:
    action: str
    estimated_effort_minutes: int
    freshness_status: str  # fresh, stale, unknown
    domain: str = "growth"  # locked to growth domain


_CONTRACT_FIELDS = set(GrowthHandoff.__dataclass_fields__.keys())


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


def _compute_freshness(last_updated: Optional[str]) -> str:
    """Return freshness status based on timestamp age.

    fresh: <=24h, stale: >24h (any valid timestamp), unknown: missing/unparseable.
    """
    if not last_updated:
        return "unknown"
    try:
        ts = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if age_h <= 24:
            return "fresh"
        return "stale"
    except (ValueError, TypeError):
        return "unknown"


def _validate_next_actions(next_actions: list[dict[str, Any]]) -> None:
    """Ensure all next actions are within the growth domain only."""
    for action in next_actions:
        domain = action.get("domain", "growth")
        if domain != "growth":
            raise ValidationError(
                f"growth_handoff.v1: cross-domain action rejected: "
                f"domain={domain!r}. Tola decides priority; module only ranks within growth domain."
            )


def produce_growth_handoff(
    agent_id: str,
    source: Any,
    project_id: str = "growth",
) -> dict[str, Any]:
    """Produce and validate a growth_handoff.v1 payload.

    Args:
        agent_id: Identifier for the calling agent.
        source: Dict of state or path to a fixture JSON file.
        project_id: Locked to "growth" for this domain.

    Returns:
        Validated dict conforming to growth_handoff.v1 with propose-mode extensions.
    """
    state = _load_state(source)

    latest_metrics = state.get("latest_metrics", {})
    active_experiments = state.get("active_experiments", [])
    awaiting_analysis = state.get("awaiting_analysis", [])
    execution_tasks = state.get("execution_tasks", [])
    blockers = state.get("blockers", [])
    deadlines = state.get("deadlines", [])
    next_actions_raw = state.get("next_actions", [])

    # Build next actions with freshness metadata; preserve original domain for validation
    next_actions: list[dict[str, Any]] = []
    for na in next_actions_raw:
        original_domain = na.get("domain", "growth")
        action_entry: dict[str, Any] = {
            "action": na.get("action", ""),
            "estimated_effort_minutes": na.get("estimated_effort_minutes", 30),
            "freshness_status": na.get("freshness_status", _compute_freshness(na.get("last_updated"))),
            "domain": original_domain,
        }
        next_actions.append(action_entry)

    _validate_next_actions(next_actions)

    # Compute overall freshness from metrics timestamp
    metrics_freshness = _compute_freshness(latest_metrics.get("last_updated"))
    if not next_actions:
        overall_freshness = "unknown"
    elif metrics_freshness == "stale" or any(
        na["freshness_status"] == "stale" for na in next_actions
    ):
        overall_freshness = "stale"
    elif metrics_freshness == "unknown":
        overall_freshness = "unknown"
    else:
        overall_freshness = "fresh"

    total_effort = sum(na["estimated_effort_minutes"] for na in next_actions)
    # Contract requires estimated_minutes > 0; use 1 as minimum for empty handoffs
    estimated_minutes = total_effort if total_effort > 0 else 1

    handoff = GrowthHandoff(
        schema_version="growth_handoff.v1",
        agent_id=agent_id,
        project_id=project_id,
        action="growth_handoff" if next_actions else "",
        estimated_minutes=estimated_minutes,
        definition_of_done="Growth handoff produced with latest metrics, active experiments, and next actions.",
        source_refs=[f"experiment:{e['name']}" for e in active_experiments + awaiting_analysis],
    )

    result = handoff.validate()

    # Attach propose-mode extensions
    result["latest_metrics"] = {
        "revenue": latest_metrics.get("revenue"),
        "mrr": latest_metrics.get("mrr"),
        "active_users": latest_metrics.get("active_users"),
        "conversion_rate": latest_metrics.get("conversion_rate"),
        "churn_rate": latest_metrics.get("churn_rate"),
        "last_updated": latest_metrics.get("last_updated"),
    }
    result["active_experiments"] = [
        {
            "name": e.get("name", ""),
            "status": e.get("status", ""),
            "variant": e.get("variant", ""),
            "start_date": e.get("start_date", ""),
            "end_date": e.get("end_date", ""),
            "metric_impact": e.get("metric_impact"),
        }
        for e in active_experiments
    ]
    result["awaiting_analysis"] = [
        {
            "name": e.get("name", ""),
            "status": e.get("status", ""),
            "variant": e.get("variant", ""),
            "start_date": e.get("start_date", ""),
            "end_date": e.get("end_date", ""),
            "metric_impact": e.get("metric_impact"),
        }
        for e in awaiting_analysis
    ]
    result["execution_tasks"] = [
        {
            "title": t.get("title", ""),
            "platform": t.get("platform", ""),
            "status": t.get("status", ""),
            "due_date": t.get("due_date"),
            "estimated_minutes": t.get("estimated_minutes", 30),
        }
        for t in execution_tasks
    ]
    result["blockers"] = blockers
    result["deadlines"] = deadlines
    result["next_actions"] = next_actions
    result["data_freshness"] = {
        "overall_status": overall_freshness,
        "metrics_freshness": metrics_freshness,
        "next_actions_count": len(next_actions),
    }

    return result
