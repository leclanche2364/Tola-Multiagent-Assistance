"""Morning pipeline for Tola Daily Synthesis — Batch 9.

Scheduled morning chain: Rhythm refresh → freshness check →
targeted refreshes → synthesis → persist.

Produces a morning_pipeline_result.v1 envelope with stage logs,
conflict surfacing, and degradation tracking.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from agents.daily_synthesis.contracts import (
    ValidationError,
    validate_payload,
)
from agents.daily_synthesis.freshness import (
    FreshnessStatus,
    HandoffRecord,
    RefreshPlan,
    build_refresh_plan,
    evaluate_freshness,
)
from agents.daily_synthesis.invocation import (
    run_daily_synthesis,
)
from agents.daily_synthesis.persistence import (
    DailySynthesisPersistence,
    PersistenceUnavailable,
)
from agents.daily_synthesis.refresh import (
    execute_refresh,
)


# ---------------------------------------------------------------------------
# Result envelope: morning_pipeline_result.v1
# ---------------------------------------------------------------------------


class OverallStatus(str, enum.Enum):
    COMPLETE = "complete"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass
class MorningPipelineResult:
    overall_status: str
    stages: list[dict[str, Any]] = field(default_factory=list)
    brief: Optional[dict[str, Any]] = None
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    missing_domains: list[str] = field(default_factory=list)
    persistence_unavailable: bool = False

    REQUIRED = [
        "overall_status",
        "stages",
        "brief",
        "conflicts",
        "missing_domains",
        "persistence_unavailable",
    ]

    def validate(self) -> dict[str, Any]:
        if self.overall_status not in {e.value for e in OverallStatus}:
            raise ValidationError(
                f"morning_pipeline_result.v1: invalid overall_status {self.overall_status!r}"
            )
        return {
            "schema_version": "morning_pipeline_result.v1",
            "overall_status": self.overall_status,
            "stages": self.stages,
            "brief": self.brief,
            "conflicts": self.conflicts,
            "missing_domains": self.missing_domains,
            "persistence_unavailable": self.persistence_unavailable,
        }


# ---------------------------------------------------------------------------
# Stage logger
# ---------------------------------------------------------------------------

def _stage_log(
    stage_name: str,
    status: str,
    refresh_reason: str = "",
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "stage": stage_name,
        "status": status,
        "refresh_reason": refresh_reason,
        "details": details or {},
    }


# ---------------------------------------------------------------------------
# Default producer stubs
# ---------------------------------------------------------------------------

def _default_producer(agent_id: str) -> Callable[[str, Optional[dict[str, Any]]], dict[str, Any]]:
    """Return a producer stub that raises RuntimeError — honest failure."""
    def _stub(agent_id_: str = agent_id, state: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        raise RuntimeError(f"refresh unavailable: no producer configured for agent {agent_id_}")
    return _stub


def _default_producers() -> dict[str, Callable]:
    return {
        "rhythm": _default_producer("rhythm"),
        "scholar": _default_producer("scholar"),
        "growth": _default_producer("growth"),
        "projects": _default_producer("projects"),
    }


# ---------------------------------------------------------------------------
# Domain → producer-key mapping
# ---------------------------------------------------------------------------

_DOMAIN_PRODUCER_KEY = {
    "rhythm": "rhythm",
    "scholar": "scholar",
    "growth": "growth",
    "projects": "projects",
}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_morning_pipeline(
    planning_date: str,
    persistence: Optional[DailySynthesisPersistence] = None,
    producers: Optional[dict[str, Callable]] = None,
    now: Optional[str] = None,
) -> MorningPipelineResult:
    """Run the scheduled morning pipeline.

    Stages (in order):
    1. Rhythm refresh → rhythm_capacity_handoff
    2. Freshness check across all domains
    3. Scholar/Growth/project targeted refreshes if stale
    4. Tola synthesis (reuses run_daily_synthesis)
    5. daily_command_brief.v1 output
    6. Persist (no-op-safe)

    Args:
        planning_date: Date string (YYYY-MM-DD).
        persistence: Optional DailySynthesisPersistence instance.
        producers: domain → producer callable mapping.
            Defaults to honest-failure stubs.
        now: Optional ISO timestamp for determinism in tests.

    Returns:
        MorningPipelineResult with stage logs and envelope.
    """
    producers = producers or _default_producers()
    now = now or datetime.now(timezone.utc).isoformat()
    stages: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    missing_domains: list[str] = []
    persistence_unavailable = False
    handoffs: dict[str, dict[str, Any]] = {}

    # --- Stage 1: Rhythm refresh → rhythm_capacity_handoff ---
    rhythm_producer = producers.get("rhythm") or _default_producer("rhythm")
    try:
        rhythm_handoff = rhythm_producer(agent_id="tola", state=None)
        if isinstance(rhythm_handoff, dict):
            validate_payload(rhythm_handoff)
        handoffs["rhythm"] = rhythm_handoff
        stages.append(_stage_log("rhythm_refresh", "ok", ""))
    except RuntimeError:
        stages.append(_stage_log("rhythm_refresh", "unavailable", "producer not configured"))
        missing_domains.append("rhythm")
    except ValidationError as exc:
        stages.append(_stage_log("rhythm_refresh", "failed", f"contract validation: {exc}"))
        missing_domains.append("rhythm")
    except Exception as exc:
        stages.append(_stage_log("rhythm_refresh", "failed", str(exc)))
        missing_domains.append("rhythm")

    # --- Produce handoffs for all other registered domains ---
    # so the freshness check can evaluate them.
    for domain in ["scholar", "growth", "projects"]:
        if domain in handoffs:
            continue
        producer = producers.get(domain)
        if producer is None:
            continue
        try:
            h = producer(agent_id="tola", state=None)
            if isinstance(h, dict):
                validate_payload(h)
            handoffs[domain] = h
        except RuntimeError:
            stages.append(_stage_log(f"{domain}_refresh", "unavailable", "producer not configured"))
            missing_domains.append(domain)
        except ValidationError as exc:
            stages.append(_stage_log(f"{domain}_refresh", "failed", f"contract validation: {exc}"))
            missing_domains.append(domain)
        except Exception as exc:
            stages.append(_stage_log(f"{domain}_refresh", "failed", str(exc)))
            missing_domains.append(domain)

    # --- Stage 2: Freshness check ---
    freshness_records: dict[str, HandoffRecord] = {}
    for domain, payload in handoffs.items():
        source_updated_at = (
            payload.get("source_updated_at")
            or payload.get("timestamp")
            or payload.get("generated_at")
        )
        record = HandoffRecord(
            domain=domain,
            payload=payload,
            source_updated_at=source_updated_at,
        )
        freshness_records[domain] = evaluate_freshness(record)

    refresh_plan = build_refresh_plan(freshness_records)
    stages.append(_stage_log("freshness_check", "ok", "", {
        "domains_to_refresh": refresh_plan.domains_to_refresh,
        "all_fresh": refresh_plan.all_fresh,
        "domain_reasons": refresh_plan.domain_reasons,
    }))

    # --- Stage 3: Targeted refreshes for stale domains ---
    if refresh_plan.domains_to_refresh:
        refresh_report = execute_refresh(
            plan=refresh_plan,
            producers=producers,
            current_handoffs=handoffs,
        )

        for domain in refresh_report.refreshed_domains:
            result = refresh_report.results[domain]
            if result.success and result.new_handoff:
                handoffs[domain] = result.new_handoff
                stages.append(_stage_log(
                    f"{domain}_refresh", "ok",
                    refresh_plan.domain_reasons.get(domain, ""),
                ))

        for domain in refresh_report.failed_domains:
            result = refresh_report.results[domain]
            is_unavailable = result.error and (
                "no producer configured" in result.error
                or "refresh unavailable" in result.error
            )
            stage_status = "unavailable" if is_unavailable else "failed"
            stages.append(_stage_log(
                f"{domain}_refresh", stage_status,
                result.error or f"{domain} refresh failed",
            ))
            if domain not in missing_domains:
                missing_domains.append(domain)

        # Check for schedule conflicts in results
        for domain, result in refresh_report.results.items():
            if result.new_handoff and isinstance(result.new_handoff, dict):
                schema = result.new_handoff.get("schema_version", "")
                if schema == "rhythm_schedule_conflict.v1":
                    conflicts.append(result.new_handoff)
                    stages.append(_stage_log(
                        f"{domain}_conflict", "conflict",
                        "schedule conflict returned by producer",
                        {"conflict": result.new_handoff},
                    ))

    # --- Stage 4 & 5: Tola synthesis → daily_command_brief.v1 ---
    # Pass persistence=None to run_daily_synthesis so it doesn't
    # handle persistence internally — we manage that in Stage 6.
    try:
        brief = run_daily_synthesis(
            planning_window=planning_date,
            persistence=None,
            handoffs=handoffs if handoffs else None,
            states=None,
            producers={
                _DOMAIN_PRODUCER_KEY.get(d, d): producers.get(d, _default_producer(d))
                for d in producers
            },
        )
        if isinstance(brief, dict):
            if brief.get("status") == "incomplete":
                stages.append(_stage_log("synthesis", "degraded", brief.get("notes", "")))
            else:
                stages.append(_stage_log("synthesis", "ok", ""))
        else:
            stages.append(_stage_log("synthesis", "ok", ""))
    except Exception as exc:
        brief = None
        stages.append(_stage_log("synthesis", "failed", str(exc)))

    # --- Stage 6: Persist (no-op-safe) ---
    if persistence is not None and brief is not None:
        try:
            date_str = planning_date if len(planning_date) == 10 else now[:10]
            persist_payload = {
                "schema_version": "daily_command_brief.v1",
                "agent_id": "tola",
                "date": date_str,
                "top_outcomes": brief.get("top_outcomes", []) if isinstance(brief, dict) else [],
                "not_today": brief.get("not_today", []) if isinstance(brief, dict) else [],
                "capacity_used_minutes": 0,
                "buffer_minutes": 0,
            }
            persistence.write("briefs", persist_payload)
            stages.append(_stage_log("persist", "ok", ""))
        except PersistenceUnavailable:
            persistence_unavailable = True
            stages.append(_stage_log("persist", "persistence_unavailable", "Supabase unavailable, no SQLite fallback"))
        except Exception as exc:
            persistence_unavailable = True
            stages.append(_stage_log("persist", "failed", str(exc)))
    else:
        if persistence is None and brief is not None:
            stages.append(_stage_log("persist", "skipped", "no persistence configured"))

    # --- Determine overall status ---
    # Unavailable agents → DEGRADED; hard failures → FAILED;
    # missing domains / conflicts / persistence issues → DEGRADED.
    has_hard_failure = any(
        s["status"] == "failed" for s in stages
    )
    if has_hard_failure:
        overall = OverallStatus.FAILED.value
    elif missing_domains or conflicts or persistence_unavailable:
        overall = OverallStatus.DEGRADED.value
    else:
        overall = OverallStatus.COMPLETE.value

    result = MorningPipelineResult(
        overall_status=overall,
        stages=stages,
        brief=brief,
        conflicts=conflicts,
        missing_domains=missing_domains,
        persistence_unavailable=persistence_unavailable,
    )
    return result
