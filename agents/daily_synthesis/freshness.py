"""Freshness engine for Daily Synthesis v1.2.

Decides per-domain freshness status and produces targeted refresh plans.
Every handoff carries generated_at, source_updated_at, and freshness_status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    MISSING = "missing"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Configurable defaults (overridable via params in evaluator calls)
# ---------------------------------------------------------------------------

RHYTHM_FRESHNESS_WINDOW_HOURS: float = 2.0
GROWTH_FRESHNESS_WINDOW_HOURS: float = 24.0
PROJECTS_FRESHNESS_WINDOW_HOURS: float = 24.0


@dataclass
class HandoffRecord:
    """A handoff with freshness metadata."""

    domain: str
    payload: dict[str, Any]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_updated_at: Optional[str] = None
    freshness_status: FreshnessStatus = FreshnessStatus.MISSING
    refresh_reason: str = ""


@dataclass
class RefreshPlan:
    """Targeted refresh plan — only stale domains, with logged reasons."""

    domains_to_refresh: list[str] = field(default_factory=list)
    domain_reasons: dict[str, str] = field(default_factory=dict)
    all_fresh: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _hours_since(ts: Optional[str]) -> Optional[float]:
    dt = _parse_ts(ts)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


def _collect_completion_events(state: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for batch in state.get("batches", []):
        for article in batch.get("articles", []):
            for event in article.get("completion_events", []):
                events.append(event)
    return events


# ---------------------------------------------------------------------------
# Per-domain evaluators
# ---------------------------------------------------------------------------


def evaluate_rhythm_freshness(
    handoff: HandoffRecord,
    freshness_window_hours: float = RHYTHM_FRESHNESS_WINDOW_HOURS,
) -> FreshnessStatus:
    """Rhythm: same-day capacity handoff fresh if <2h old; aging if <24h;
    stale if older; missing if no timestamp."""
    age_h = _hours_since(handoff.source_updated_at)
    if age_h is None:
        return FreshnessStatus.MISSING
    if age_h <= freshness_window_hours:
        return FreshnessStatus.FRESH
    if age_h <= 24:
        return FreshnessStatus.AGING
    return FreshnessStatus.STALE


def evaluate_growth_freshness(
    handoff: HandoffRecord,
    freshness_window_hours: float = GROWTH_FRESHNESS_WINDOW_HOURS,
) -> FreshnessStatus:
    """Growth: daily/event-triggered. Fresh if within window; stale if older;
    missing if no timestamp."""
    age_h = _hours_since(handoff.source_updated_at)
    if age_h is None:
        return FreshnessStatus.MISSING
    if age_h <= freshness_window_hours:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


def evaluate_projects_freshness(
    handoff: HandoffRecord,
    freshness_window_hours: float = PROJECTS_FRESHNESS_WINDOW_HOURS,
) -> FreshnessStatus:
    """Projects: refresh after work occurs or when latest recorded state
    no longer reflects current implementation."""
    age_h = _hours_since(handoff.source_updated_at)
    if age_h is None:
        return FreshnessStatus.MISSING
    if age_h <= freshness_window_hours:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


def evaluate_scholar_freshness(
    handoff: HandoffRecord,
    state: Optional[dict[str, Any]] = None,
    freshness_window_hours: float = GROWTH_FRESHNESS_WINDOW_HOURS,
) -> FreshnessStatus:
    """Scholar freshness is STATE-SENSITIVE, not just time-sensitive.

    Stale when current_batch changes, section completes, article completes,
    assignment state changes, or deadline changes.

    Special rule (QA plan): a handoff whose current_batch is older than
    the latest completion event is semantically stale even if schema-valid
    and time-recent.
    """
    # Semantic staleness: completion event newer than handoff timestamp
    if state is not None:
        current_batch_id = handoff.payload.get("current_batch_id")
        completion_events = _collect_completion_events(state)
        if completion_events and current_batch_id:
            latest_completion_ts = max(
                _parse_ts(e.get("timestamp", "")) or datetime.min.replace(tzinfo=timezone.utc)
                for e in completion_events
            )
            batch_ts = _parse_ts(handoff.payload.get("timestamp", ""))
            if batch_ts is not None and latest_completion_ts > batch_ts:
                return FreshnessStatus.STALE

    # Time-based fallback
    age_h = _hours_since(handoff.source_updated_at)
    if age_h is None:
        return FreshnessStatus.MISSING
    if age_h <= freshness_window_hours:
        return FreshnessStatus.FRESH
    return FreshnessStatus.STALE


# ---------------------------------------------------------------------------
# Freshness engine
# ---------------------------------------------------------------------------

FRESHNESS_EVALUATORS: dict[str, callable] = {
    "rhythm": evaluate_rhythm_freshness,
    "growth": evaluate_growth_freshness,
    "projects": evaluate_projects_freshness,
    "scholar": evaluate_scholar_freshness,
}


def evaluate_freshness(
    handoff: HandoffRecord,
    state: Optional[dict[str, Any]] = None,
) -> HandoffRecord:
    """Evaluate freshness for a single handoff, returning it with updated status."""
    evaluator = FRESHNESS_EVALUATORS.get(handoff.domain)
    if evaluator is None:
        handoff.freshness_status = FreshnessStatus.MISSING
        handoff.refresh_reason = f"unknown domain: {handoff.domain}"
        return handoff

    try:
        if handoff.domain == "scholar":
            status = evaluator(handoff, state=state)
        else:
            status = evaluator(handoff)
    except Exception:
        handoff.freshness_status = FreshnessStatus.FAILED
        handoff.refresh_reason = f"freshness evaluation error for {handoff.domain}"
        return handoff

    handoff.freshness_status = status
    return handoff


def build_refresh_plan(
    handoffs: dict[str, HandoffRecord],
    states: Optional[dict[str, dict[str, Any]]] = None,
) -> RefreshPlan:
    """Build a targeted refresh plan — only stale domains, never broad fan-out.

    Args:
        handoffs: domain -> HandoffRecord mapping.
        states: optional domain -> state dict for state-sensitive freshness (scholar).

    Returns:
        RefreshPlan listing only domains that need refresh, with reasons.
    """
    plan = RefreshPlan()
    states = states or {}

    for domain, handoff in handoffs.items():
        evaluate_freshness(handoff, state=states.get(domain))

        status = handoff.freshness_status

        if status in (FreshnessStatus.STALE, FreshnessStatus.MISSING, FreshnessStatus.FAILED):
            plan.domains_to_refresh.append(domain)
            reason = handoff.refresh_reason or f"{domain} is {status.value}"
            plan.domain_reasons[domain] = reason

    if not plan.domains_to_refresh:
        plan.all_fresh = True

    return plan
