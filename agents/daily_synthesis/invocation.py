"""Natural-language invocation router and daily synthesis orchestrator.

Batch 8: intent router maps natural-language commands to reusable workflow.
run_daily_synthesis() orchestrates the full pipeline with degraded-mode
safety and proposal-mode output.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from agents.daily_synthesis.contracts import ValidationError
from agents.daily_synthesis.freshness import (
    FreshnessStatus,
    HandoffRecord,
    RefreshPlan,
    build_refresh_plan,
    evaluate_freshness,
)
from agents.daily_synthesis.refresh import execute_refresh
from agents.daily_synthesis.synthesis import build_brief
from agents.daily_synthesis.persistence import (
    DailySynthesisPersistence,
    PersistenceUnavailable,
)


# ---------------------------------------------------------------------------
# Intent enum
# ---------------------------------------------------------------------------

class Intent(enum.Enum):
    PLAN_TODAY = "plan_today"
    PLAN_TOMORROW = "plan_tomorrow"
    REFRESH_PLAN = "refresh_plan"
    WHAT_SHOULD_I_WORK_ON = "what_should_i_work_on"
    CAPACITY_LIMITED_PLAN = "capacity_limited_plan"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    intent: Intent
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: str = "high"


# ---------------------------------------------------------------------------
# Phrasing groups — match on meaning, not exact phrase
# ---------------------------------------------------------------------------

_PLAN_TODAY_PHRASES = [
    "plan today", "today's plan", "what should i do today",
    "plan my day", "today plan", "what's on my plate today",
    "give me today's plan", "what should i work on today",
    "sort today out", "today's schedule", "today plan",
    "what do i need to do today", "today's to-do",
    "plan for today", "today agenda", "today",
]

_PLAN_TOMORROW_PHRASES = [
    "plan tomorrow", "tomorrow's plan", "what should i do tomorrow",
    "plan for tomorrow", "tomorrow plan", "what's on my plate tomorrow",
    "tomorrow's schedule", "what do i need to do tomorrow",
    "tomorrow agenda", "tomorrow",
]

_REFRESH_PLAN_PHRASES = [
    "refresh my plan", "update plan", "replan", "refresh today",
    "regenerate plan", "new plan", "refresh", "regenerate",
    "update my plan", "rebuild plan", "refresh plan",
    "new daily plan", "re-do today", "refresh everything",
]

_WORK_ON_PHRASES = [
    "what should i work on", "what's my priority", "what's next",
    "what should i focus on", "what's the most important thing",
    "what should i do now", "what's my next action",
    "what should i tackle", "what's the priority",
    "what's first", "what should i do", "what comes next",
    "what's the best use of my time", "where should i focus",
    "what's my focus", "what should i prioritize",
]

_CAPACITY_LIMITED_PHRASES = [
    "i only have a couple of hours", "short on time",
    "limited capacity", "only a few hours", "i'm short on time",
    "quick plan", "i only have time for", "couple of hours",
    "limited time", "tight schedule", "not much time",
    "i only have an hour", "i only have a little time",
    "running low on time", "tight on time", "crunched for time",
    "i've only got a couple of hours", "barely any time",
    "only a couple of hours", "just a couple of hours",
    "a couple of hours",
]

_INTENT_MAP: dict[Intent, list[str]] = {
    Intent.PLAN_TODAY: _PLAN_TODAY_PHRASES,
    Intent.PLAN_TOMORROW: _PLAN_TOMORROW_PHRASES,
    Intent.REFRESH_PLAN: _REFRESH_PLAN_PHRASES,
    Intent.WHAT_SHOULD_I_WORK_ON: _WORK_ON_PHRASES,
    Intent.CAPACITY_LIMITED_PLAN: _CAPACITY_LIMITED_PHRASES,
}

_CAPACITY_HINT_RE = re.compile(
    r"\b(couple of hours|few hours|short on time|limited time|"
    r"tight schedule|not much time|only (a )?(couple|few|one) "
    r"(hours?|hrs?|minute|min))",
    re.IGNORECASE,
)


def route_intent(command: str) -> IntentResult:
    """Map a natural-language command to an Intent.

    Matches on meaning using keyword/phrase groups. Multiple phrasings
    per intent are supported. Unknown input returns Intent.UNKNOWN
    with confidence 'low' — never guesses.
    """
    normalized = command.strip().lower()

    if not normalized:
        return IntentResult(intent=Intent.UNKNOWN, confidence="low")

    # Check for capacity-limited language
    has_capacity_hint = bool(_CAPACITY_HINT_RE.search(normalized))

    # Score each intent
    scores: dict[Intent, int] = {
        intent: 0 for intent in Intent if intent != Intent.UNKNOWN
    }

    for intent, phrases in _INTENT_MAP.items():
        for phrase in phrases:
            if phrase in normalized:
                scores[intent] += 1

    # Find best match
    best_intent = max(scores, key=scores.get)
    if scores[best_intent] == 0:
        return IntentResult(intent=Intent.UNKNOWN, confidence="low")

    # If capacity hint present, ensure it's recorded in parameters
    parameters: dict[str, Any] = {}
    if has_capacity_hint:
        parameters["capacity_hint"] = "limited"

    # If capacity hint present and best match is a planning or work-on
    # intent, upgrade to capacity_limited_plan
    if has_capacity_hint and best_intent in (
        Intent.PLAN_TODAY,
        Intent.WHAT_SHOULD_I_WORK_ON,
    ):
        best_intent = Intent.CAPACITY_LIMITED_PLAN

    confidence = "high" if scores[best_intent] >= 1 else "medium"

    return IntentResult(
        intent=best_intent, parameters=parameters, confidence=confidence
    )


# ---------------------------------------------------------------------------
# Refresh unavailable stub
# ---------------------------------------------------------------------------

def refresh_unavailable_stub(
    agent_id: str, state: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Default producer stub for unavailable refresh hooks.

    Raises RuntimeError — honest failure, never fabricates data.
    """
    raise RuntimeError(
        f"refresh unavailable: no producer configured for agent {agent_id}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _domain_from_schema(schema_version: str) -> str:
    """Map schema_version to domain name."""
    mapping = {
        "rhythm_capacity_handoff.v1": "rhythm",
        "scholar_handoff.v1": "scholar",
        "growth_handoff.v1": "growth",
        "project_status_handoff.v1": "projects",
    }
    return mapping.get(schema_version, "unknown")


def _incomplete_result(
    missing: list[str],
    decision_metadata: dict[str, Any],
    notes: str,
) -> dict[str, Any]:
    """Return an explicit incomplete status listing what's missing."""
    return {
        "schema_version": "daily_command_brief.v1",
        "status": "incomplete",
        "missing": missing,
        "decision_metadata": decision_metadata,
        "top_outcomes": [],
        "not_today": [],
        "notes": notes,
    }


def _resolve_date(planning_window: str) -> str:
    """Resolve planning_window to a date string (YYYY-MM-DD)."""
    if len(planning_window) == 10 and planning_window[4] == "-":
        return planning_window
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Orchestrating entrypoint
# ---------------------------------------------------------------------------

def run_daily_synthesis(
    planning_window: str,
    capacity_hint: Optional[int] = None,
    handoffs: Optional[dict[str, Any]] = None,
    persistence: Optional[DailySynthesisPersistence] = None,
    states: Optional[dict[str, dict[str, Any]]] = None,
    producers: Optional[dict[str, Callable]] = None,
) -> dict[str, Any]:
    """Orchestrate the daily synthesis pipeline.

    If handoffs not supplied: load latest valid handoffs via persistence,
    then freshness check, then targeted refresh for stale domains.
    Then synthesis → daily_command_brief.v1.

    Degraded mode: Supabase/persistence unavailable → proceed with
    handoffs already in memory if provided, mark persistence_unavailable
    in decision metadata; if no usable handoffs at all → return explicit
    incomplete status listing what's missing. Never fabricate.

    Proposal-mode flag: output is a proposal by default; auto-scheduling
    NOT implemented this batch.
    """
    states = states or {}
    producers = producers or {}
    now = datetime.now(timezone.utc).isoformat()
    date_str = _resolve_date(planning_window)

    decision_metadata: dict[str, Any] = {
        "intent": "unknown",
        "persistence_status": "available",
        "refresh_plan": {},
        "proposal_mode": True,
        "auto_scheduling": False,
    }

    # --- Check persistence availability ---
    persistence_unavailable = False
    if persistence is not None:
        try:
            persistence.read("handoffs")
        except PersistenceUnavailable:
            persistence_unavailable = True

    # Mark degraded when persistence is unavailable
    if persistence_unavailable:
        decision_metadata["persistence_status"] = "persistence_unavailable"

    # --- Load handoffs if not provided ---
    if handoffs is None:
        if persistence is None or persistence_unavailable:
            return _incomplete_result(
                missing=["handoffs"],
                decision_metadata=decision_metadata,
                notes=(
                    "Persistence unavailable and no in-memory handoffs "
                    "provided."
                ),
            )

        try:
            result = persistence.read("handoffs")
        except PersistenceUnavailable:
            decision_metadata["persistence_status"] = "persistence_unavailable"
            return _incomplete_result(
                missing=["handoffs"],
                decision_metadata=decision_metadata,
                notes=(
                    "Persistence unavailable and no in-memory handoffs "
                    "provided."
                ),
            )

        if result.get("status") != "ok":
            decision_metadata["persistence_status"] = "persistence_unavailable"
            return _incomplete_result(
                missing=["handoffs"],
                decision_metadata=decision_metadata,
                notes=(
                    "Persistence read failed and no in-memory handoffs "
                    "provided."
                ),
            )

        # Group handoffs by domain (from schema_version)
        handoffs = {}
        for row in result.get("rows", []):
            payload = row.get("payload", {})
            domain = _domain_from_schema(payload.get("schema_version", ""))
            handoffs[domain] = payload

    # Guard: no usable handoffs at all
    if not handoffs:
        return _incomplete_result(
            missing=["handoffs"],
            decision_metadata=decision_metadata,
            notes="No handoffs available after loading — nothing to synthesize.",
        )

    # --- Freshness check ---
    freshness_handoffs: dict[str, HandoffRecord] = {}
    for domain, payload in handoffs.items():
        source_updated_at = (
            payload.get("source_updated_at")
            or payload.get("timestamp")
            or payload.get("generated_at")
        )
        handoff_record = HandoffRecord(
            domain=domain,
            payload=payload,
            source_updated_at=source_updated_at,
        )
        freshness_handoffs[domain] = evaluate_freshness(
            handoff_record, state=states.get(domain)
        )

    refresh_plan = build_refresh_plan(
        freshness_handoffs, states=states
    )
    decision_metadata["refresh_plan"] = {
        "domains_to_refresh": refresh_plan.domains_to_refresh,
        "all_fresh": refresh_plan.all_fresh,
        "domain_reasons": refresh_plan.domain_reasons,
    }

    # --- Execute targeted refresh for stale domains ---
    if refresh_plan.domains_to_refresh:
        refresh_report = execute_refresh(
            plan=refresh_plan,
            producers=producers,
            current_handoffs=handoffs,
            states=states,
        )

        # Swap in new handoffs for successful refreshes
        for domain in refresh_report.refreshed_domains:
            refresh_result = refresh_report.results[domain]
            if refresh_result.success and refresh_result.new_handoff:
                handoffs[domain] = refresh_result.new_handoff

        # Record failed refreshes in metadata (honest — no fabrication)
        if refresh_report.failed_domains:
            decision_metadata["refresh_failures"] = {
                d: refresh_report.results[d].error
                for d in refresh_report.failed_domains
            }

    # --- Extract handoffs by domain ---
    capacity_handoff = handoffs.get("rhythm", {})
    scholar_handoff = handoffs.get("scholar", {})
    growth_handoff = handoffs.get("growth", {})
    project_handoffs = [
        v
        for v in handoffs.values()
        if isinstance(v, dict)
        and v.get("schema_version") == "project_status_handoff.v1"
    ]

    # Apply capacity_hint if provided and no rhythm handoff exists
    if capacity_hint is not None and not capacity_handoff:
        capacity_handoff = {
            "schema_version": "rhythm_capacity_handoff.v1",
            "agent_id": "tola",
            "rhythm_id": "r1",
            "capacity_used_minutes": 0,
            "capacity_total_minutes": capacity_hint,
            "recovery_buffer_minutes": max(5, capacity_hint // 6),
        }

    # Provide minimal valid defaults for missing handoffs
    if not capacity_handoff:
        capacity_handoff = {
            "schema_version": "rhythm_capacity_handoff.v1",
            "agent_id": "tola",
            "rhythm_id": "r1",
            "capacity_used_minutes": 0,
            "capacity_total_minutes": 240,
            "recovery_buffer_minutes": 30,
        }

    if not scholar_handoff:
        scholar_handoff = {
            "schema_version": "scholar_handoff.v1",
            "agent_id": "scholar",
            "current_batch_id": "batch-0",
            "exact_action": "No scholar handoff available",
            "estimated_minutes": 30,
            "definition_of_done": "No scholar handoff provided",
        }

    if not growth_handoff:
        growth_handoff = {
            "schema_version": "growth_handoff.v1",
            "agent_id": "growth",
            "project_id": "growth",
            "action": "growth_handoff",
            "estimated_minutes": 1,
            "definition_of_done": "No growth handoff provided",
            "next_actions": [],
        }

    # --- Synthesis ---
    try:
        brief = build_brief(
            capacity_handoff=capacity_handoff,
            scholar_handoff=scholar_handoff,
            growth_handoff=growth_handoff,
            project_handoffs=project_handoffs,
            now=now,
        )
    except (ValidationError, Exception) as exc:
        return _incomplete_result(
            missing=["synthesis"],
            decision_metadata=decision_metadata,
            notes=f"Synthesis failed: {exc}",
        )

    # --- Persist the brief (no-op-safe when unavailable) ---
    if persistence is not None:
        persistence.write(
            "briefs",
            {
                "schema_version": "daily_command_brief.v1",
                "agent_id": "tola",
                "date": date_str,
                "top_outcomes": brief.get("top_outcomes", []),
                "not_today": brief.get("not_today", []),
                "capacity_used_minutes": brief.get(
                    "capacity_used_minutes", 0
                ),
                "buffer_minutes": brief.get("buffer_minutes", 0),
            },
        )

    # --- Build final result ---
    return {
        **brief,
        "decision_metadata": decision_metadata,
        "proposal_mode": True,
    }
