"""Tola Daily Synthesis Engine — Batch 6.

build_brief() constructs a daily_command_brief.v1 from handoff payloads.
Decision logic priority: hard deadlines → blocker removal → dependency unlock
→ protected commitments → continuity → energy fit to window → probability
of finishing a meaningful unit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime, timezone

from agents.daily_synthesis.contracts import (
    DailyCommandBrief,
    ValidationError,
    validate_payload,
)

_GENERIC_STUDY_RE = re.compile(
    r"^\s*(study CCRN3|do assignment|read an article)\s*$", re.IGNORECASE
)


@dataclass
class Candidate:
    source: str
    title: str
    estimated_minutes: int
    minimum_viable_minutes: int
    deadline: Optional[str]
    blocking_count: int
    continuity_score: float
    context_switch_cost: float
    energy_required: str
    definition_of_done: str
    source_refs: list[str]
    exact_action: Optional[str] = None
    article: Optional[str] = None
    sections: Optional[list[str]] = None
    extraction_goal: Optional[str] = None
    priority_score: float = 0.0
    defer_reason: Optional[str] = None


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _is_hard_deadline(deadline: Optional[str], now: str) -> bool:
    if not deadline:
        return False
    dl = _parse_iso(deadline)
    n = _parse_iso(now)
    if dl is None or n is None:
        return False
    return dl.date() <= n.date()


def _days_until(deadline: Optional[str], now: str) -> Optional[int]:
    if not deadline:
        return None
    dl = _parse_iso(deadline)
    n = _parse_iso(now)
    if dl is None or n is None:
        return None
    return (dl.date() - n.date()).days


def _build_scholar_candidates(
    scholar_handoff: dict[str, Any],
    available_minutes: int,
) -> list[Candidate]:
    """Build candidate(s) from scholar handoff.

    When the available window is smaller than the scholar's estimated_minutes
    and the handoff has no short_window atom, a quick-read atom is generated
    alongside the full task so the selection logic can choose the best fit.
    """
    candidates: list[Candidate] = []

    exact_action = scholar_handoff.get("exact_action", "")
    estimated_minutes = scholar_handoff.get("estimated_minutes", 30)
    definition_of_done = scholar_handoff.get("definition_of_done", "")
    source_refs = list(scholar_handoff.get("source_refs", []))
    reading_target = scholar_handoff.get("reading_target")
    current_batch_id = scholar_handoff.get("current_batch_id", "")
    has_short_window = scholar_handoff.get("short_window") is not None

    needs_short_atom = (
        available_minutes > 0
        and available_minutes < estimated_minutes
        and not has_short_window
    )

    # Always generate the full task as a candidate (may be deferred)
    article = reading_target.get("article_title") if reading_target else None
    sections = reading_target.get("exact_sections_to_read") if reading_target else None
    extraction_goal = reading_target.get("extraction_goal") if reading_target else None

    candidates.append(Candidate(
        source="scholar",
        title=f"Study: {exact_action}",
        estimated_minutes=estimated_minutes,
        minimum_viable_minutes=max(10, estimated_minutes // 2),
        deadline=None,
        blocking_count=0,
        continuity_score=0.9,
        context_switch_cost=0.5,
        energy_required="deep" if estimated_minutes >= 60 else "medium",
        definition_of_done=definition_of_done,
        source_refs=source_refs,
        exact_action=exact_action,
        article=article,
        sections=sections,
        extraction_goal=extraction_goal,
    ))

    # If window is too small and no short_window atom exists, add quick-read
    if needs_short_atom and reading_target and reading_target.get("required"):
        quick_sections = (sections[:1] if sections else []) or []
        quick_article = article or ""
        quick_goal = extraction_goal or ""

        candidates.append(Candidate(
            source="scholar",
            title=f"Quick-read: {quick_article}",
            estimated_minutes=min(15, available_minutes),
            minimum_viable_minutes=10,
            deadline=None,
            blocking_count=0,
            continuity_score=0.7,
            context_switch_cost=0.3,
            energy_required="low",
            definition_of_done=(
                f"Quick-read {quick_article} sections {quick_sections}; "
                f"extract one key claim relevant to {current_batch_id}."
            ),
            source_refs=[quick_article] if quick_article else source_refs,
            exact_action=f"Quick-read {quick_article} — extract {quick_goal}",
            article=quick_article,
            sections=quick_sections,
            extraction_goal=quick_goal,
        ))

    return candidates


def _build_growth_candidates(growth_handoff: dict[str, Any]) -> list[Candidate]:
    """Build candidates from growth handoff next_actions."""
    candidates: list[Candidate] = []
    next_actions = growth_handoff.get("next_actions", [])

    for na in next_actions:
        action = na.get("action", "")
        effort = na.get("estimated_effort_minutes", 30)

        candidates.append(Candidate(
            source="growth",
            title=action,
            estimated_minutes=effort,
            minimum_viable_minutes=max(5, effort // 3),
            deadline=None,
            blocking_count=0,
            continuity_score=0.5,
            context_switch_cost=0.4,
            energy_required="medium",
            definition_of_done=f"Completed: {action}",
            source_refs=[f"growth:{action}"],
        ))

    return candidates


def _build_project_candidates(project_handoffs: list[dict[str, Any]]) -> list[Candidate]:
    """Build candidates from project status handoffs."""
    candidates: list[Candidate] = []

    for ph in project_handoffs:
        next_action = ph.get("next_action", "")
        blocker = ph.get("blocker", "")
        deadline = ph.get("deadline")
        effort = ph.get("estimated_effort_minutes", 30)
        energy = ph.get("energy_required", "medium")
        definition_of_done = ph.get("definition_of_done", "")
        project_id = ph.get("project_id", "")

        candidates.append(Candidate(
            source="project",
            title=next_action if next_action else f"Work on {project_id}",
            estimated_minutes=effort,
            minimum_viable_minutes=max(5, effort // 3),
            deadline=deadline,
            blocking_count=1 if blocker else 0,
            continuity_score=0.6,
            context_switch_cost=0.5,
            energy_required=energy,
            definition_of_done=definition_of_done
            or f"Progress on {project_id}: {next_action}",
            source_refs=[f"project:{project_id}"],
        ))

    return candidates


def _build_admin_candidates() -> list[Candidate]:
    """Build low-energy admin candidates."""
    return [
        Candidate(
            source="admin",
            title="Process inbox and flag urgent items",
            estimated_minutes=15,
            minimum_viable_minutes=5,
            deadline=None,
            blocking_count=0,
            continuity_score=0.3,
            context_switch_cost=0.2,
            energy_required="low",
            definition_of_done="Inbox processed; urgent items flagged in task manager.",
            source_refs=[],
        ),
        Candidate(
            source="admin",
            title="Update daily log and handoff notes",
            estimated_minutes=10,
            minimum_viable_minutes=5,
            deadline=None,
            blocking_count=0,
            continuity_score=0.2,
            context_switch_cost=0.1,
            energy_required="low",
            definition_of_done="Daily log updated with today's decisions and handoff notes.",
            source_refs=[],
        ),
    ]


def _has_deep_window(capacity_handoff: dict[str, Any]) -> bool:
    return any(w.get("work_type") == "deep" for w in capacity_handoff.get("windows", []))


def _has_medium_window(capacity_handoff: dict[str, Any]) -> bool:
    return any(w.get("work_type") == "medium" for w in capacity_handoff.get("windows", []))


def _score_candidates(
    candidates: list[Candidate],
    available_minutes: int,
    capacity_handoff: dict[str, Any],
    now: str,
) -> list[Candidate]:
    """Score and sort candidates by decision logic priority."""
    now_dt = _parse_iso(now)
    now_date = now_dt.date() if now_dt else None

    for c in candidates:
        score = 0.0

        # 1. Hard deadlines (highest priority)
        if _is_hard_deadline(c.deadline, now):
            score += 1000
        elif c.deadline:
            days = _days_until(c.deadline, now)
            if days is not None:
                if days <= 0:
                    score += 800
                elif days <= 1:
                    score += 500
                elif days <= 3:
                    score += 300
                elif days <= 7:
                    score += 100

        # 2. Blocker removal
        score += c.blocking_count * 200

        # 5. Continuity
        score += c.continuity_score * 50

        # 6. Energy fit to window
        energy = c.energy_required
        has_deep = _has_deep_window(capacity_handoff)
        has_medium = _has_medium_window(capacity_handoff)

        if energy == "deep" and has_deep:
            score += 80
        elif energy == "deep" and not has_deep:
            score -= 200
        elif energy == "medium" and (has_deep or has_medium):
            score += 60
        elif energy == "medium" and not has_deep and not has_medium:
            score -= 100
        elif energy == "low":
            score += 40
        elif energy == "high" and has_deep:
            score += 50
        elif energy == "high" and not has_deep:
            score -= 50

        # 7. Probability of finishing a meaningful unit
        fit_ratio = c.estimated_minutes / max(available_minutes, 1)
        if fit_ratio <= 0.5:
            score += 100
        elif fit_ratio <= 0.8:
            score += 60
        elif fit_ratio <= 1.0:
            score += 30
        else:
            score += 10

        # Penalise context switching
        score -= c.context_switch_cost * 30

        c.priority_score = score

    candidates.sort(key=lambda c: c.priority_score, reverse=True)
    return candidates


def _validate_study_wording(candidate: Candidate, scholar_handoff: dict[str, Any]) -> None:
    """Guard: raise if a study outcome is rendered generically.

    If scholar handoff has reading_target.required=True, the candidate
    must carry exact_action and article (not generic language).
    """
    reading_target = scholar_handoff.get("reading_target")
    if reading_target is None:
        return
    if not reading_target.get("required"):
        return

    if _GENERIC_STUDY_RE.match(candidate.exact_action or ""):
        raise ValidationError(
            f"synthesis.py: generic study language rejected: "
            f"{candidate.exact_action!r}. Must carry exact_action and article."
        )

    if not candidate.exact_action or not candidate.article:
        raise ValidationError(
            "synthesis.py: study outcome must carry exact_action and article "
            "when scholar handoff requires reading."
        )


def build_brief(
    capacity_handoff: dict[str, Any],
    scholar_handoff: dict[str, Any],
    growth_handoff: dict[str, Any],
    project_handoffs: list[dict[str, Any]],
    now: str,
) -> dict[str, Any]:
    """Build a daily_command_brief.v1 from handoff payloads.

    Decision logic (priority order):
    1. Hard deadlines
    2. Blocker removal
    3. Dependency unlock
    4. Protected commitments
    5. Continuity
    6. Energy fit to window
    7. Probability of finishing a meaningful unit

    Never fills all capacity; reserves recovery_buffer_minutes.
    Prefers 1-3 outcomes; max_major_outcomes is a hard cap.
    """
    # Validate inputs against contracts
    if capacity_handoff.get("schema_version"):
        capacity_handoff = validate_payload(capacity_handoff)
    if scholar_handoff.get("schema_version"):
        scholar_handoff = validate_payload(scholar_handoff)
    if growth_handoff.get("schema_version"):
        growth_handoff = validate_payload(growth_handoff)
    for ph in project_handoffs:
        if ph.get("schema_version"):
            validate_payload(ph)

    # Compute available capacity
    capacity_total = capacity_handoff.get("capacity_total_minutes", 0)
    capacity_used = capacity_handoff.get("capacity_used_minutes", 0)
    recovery_buffer = capacity_handoff.get("recovery_buffer_minutes", 0)
    capacity_summary = capacity_handoff.get("capacity_summary", {})
    max_major_outcomes = capacity_summary.get("max_major_outcomes", 3)

    remaining_capacity = capacity_total - capacity_used - recovery_buffer
    available_minutes = max(0, remaining_capacity)

    # Build candidates from all domains
    all_candidates: list[Candidate] = []
    all_candidates.extend(_build_scholar_candidates(scholar_handoff, available_minutes))
    all_candidates.extend(_build_growth_candidates(growth_handoff))
    all_candidates.extend(_build_project_candidates(project_handoffs))
    all_candidates.extend(_build_admin_candidates())

    # Validate study wording integrity for all scholar candidates
    for c in all_candidates:
        if c.source == "scholar":
            _validate_study_wording(c, scholar_handoff)

    # Score and sort
    scored = _score_candidates(all_candidates, available_minutes, capacity_handoff, now)

    # Select top candidates respecting capacity and max outcomes
    selected: list[dict[str, Any]] = []
    total_planned_minutes = 0
    deferrals: list[str] = []

    for c in scored:
        if len(selected) >= max_major_outcomes:
            deferrals.append(
                f"{c.title}: deferred — capacity full "
                f"(max {max_major_outcomes} outcomes)"
            )
            continue

        remaining_after_planned = available_minutes - total_planned_minutes
        if c.estimated_minutes <= remaining_after_planned and remaining_after_planned > 0:
            selected.append({
                "definition_of_done": c.definition_of_done,
                "source_refs": c.source_refs,
                "estimated_minutes": c.estimated_minutes,
                "minimum_viable_minutes": c.minimum_viable_minutes,
                "deadline": c.deadline,
                "blocking_count": c.blocking_count,
                "continuity_score": c.continuity_score,
                "context_switch_cost": c.context_switch_cost,
                "energy_required": c.energy_required,
                "exact_action": c.exact_action,
                "article": c.article,
                "sections": c.sections,
                "extraction_goal": c.extraction_goal,
            })
            total_planned_minutes += c.estimated_minutes
        else:
            reason = f"{c.title}: deferred — "
            if c.estimated_minutes > remaining_after_planned:
                reason += f"requires {c.estimated_minutes}min, only {remaining_after_planned}min remaining"
            else:
                reason += "no remaining capacity"
            deferrals.append(reason)

    # Build study_detail from scholar handoff (preserve exact wording unchanged)
    reading_target = scholar_handoff.get("reading_target")
    study_detail = {
        "exact_action": scholar_handoff.get("exact_action", ""),
        "article": reading_target.get("article_title") if reading_target else None,
        "sections": reading_target.get("exact_sections_to_read") if reading_target else None,
        "extraction_goal": reading_target.get("extraction_goal") if reading_target else None,
    }

    # Guard: if scholar requires reading, study_detail must not be generic
    if reading_target and reading_target.get("required"):
        if not study_detail.get("exact_action") or not study_detail.get("article"):
            raise ValidationError(
                "synthesis.py: study outcome rendered generically — "
                "missing exact_action or article when scholar required reading."
            )

    # Build the brief dict
    brief = {
        "schema_version": "daily_command_brief.v1",
        "agent_id": capacity_handoff.get("agent_id", "tola"),
        "date": now[:10] if now else "",
        "top_outcomes": selected,
        "not_today": deferrals,
        "capacity_used_minutes": capacity_used + total_planned_minutes,
        "buffer_minutes": recovery_buffer,
        "study_detail": study_detail,
        "capacity_summary": {
            "max_major_outcomes": max_major_outcomes,
            "total_available_minutes": available_minutes,
            "total_planned_minutes": total_planned_minutes,
            "remaining_buffer_minutes": recovery_buffer,
        },
        "notes": (
            f"Daily synthesis built at {now}. "
            f"{len(selected)} outcomes selected, {len(deferrals)} deferred."
        ),
    }

    # Validate against contract (strip non-contract fields for validation)
    contract_fields = set(DailyCommandBrief.__dataclass_fields__.keys())
    contract_brief = {k: v for k, v in brief.items() if k in contract_fields}
    brief_obj = DailyCommandBrief(**contract_brief)
    validated = brief_obj.validate()

    # Add non-contract fields back
    validated["study_detail"] = study_detail
    validated["capacity_summary"] = brief["capacity_summary"]

    return validated
