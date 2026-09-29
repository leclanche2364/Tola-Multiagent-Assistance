# Batch T27 -- Weekly Executive Review
# tola/review/weekly.py: run_weekly_review + WeeklyReview.

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_NEXT_WEEK_PRIORITIES = 5
BRIEFING_MAX_LINES = 20


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WeeklyReview:
    """Result of a weekly executive review.

    Immutable.  Deterministic: same inputs -> same output.
    """

    portfolio_priorities: list[dict] = field(default_factory=list)
    capacity_requests: list[dict] = field(default_factory=list)
    growth_opportunities: list[dict] = field(default_factory=list)
    scholar_obligations: list[dict] = field(default_factory=list)
    stalled_work: list[dict] = field(default_factory=list)
    experiments_awaiting: list[dict] = field(default_factory=list)
    decisions_awaiting: list[dict] = field(default_factory=list)
    risks: list[dict] = field(default_factory=list)
    next_week_priorities: list[dict] = field(default_factory=list)
    follow_ups: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class WeekBriefing:
    """Concise plain-ASCII briefing lines.

    Immutable.  Deterministic.
    """

    lines: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso_date(s: str) -> Any:
    """Parse an ISO date string (YYYY-MM-DD or full ISO)."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _materiality_score(project: dict) -> int:
    """Score a project by material signals.

    Higher score = more material.  Stable tiebreak by id.
    """
    score = 0
    status = project.get("status", "")
    if status in ("blocked", "stalled"):
        score += 40
    if project.get("deadline"):
        d = _parse_iso_date(project["deadline"])
        if d is not None:
            ref = date(2026, 9, 29)
            delta = (d - ref).days
            if delta <= 0:
                score += 30
            elif delta <= 7:
                score += 20
            elif delta <= 14:
                score += 10
    risk = project.get("risk", "")
    if risk in ("high", "critical"):
        score += 25
    elif risk == "medium":
        score += 10
    if project.get("blocked_by"):
        score += 15
    if project.get("depends_on"):
        score += 5
    return score


def _rank_projects(projects: list[dict]) -> list[dict]:
    """Rank projects by materiality score, stable tiebreak by id."""
    scored = []
    for p in projects:
        pid = p.get("id", "")
        score = _materiality_score(p)
        scored.append((score, pid, p))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item[2] for item in scored]


def _is_material_growth(opportunity: dict) -> bool:
    """Return True if a growth opportunity is material enough to incorporate."""
    if not opportunity.get("material", False):
        return False
    impact = opportunity.get("impact", "low")
    return impact in ("high", "medium")


def _is_scholar_deadline_driven(obligation: dict) -> bool:
    """Return True if a Scholar obligation has a near-term deadline."""
    due = obligation.get("due_date", "")
    if not due:
        return False
    d = _parse_iso_date(due)
    if d is None:
        return False
    ref = date(2026, 9, 29)
    delta = (d - ref).days
    return delta <= 14


def _has_deferred_flag(item: dict) -> bool:
    """Return True if item is explicitly deferred."""
    return bool(item.get("deferred"))


def _has_revive_reason(item: dict) -> bool:
    """Return True if item has an explicit revive_reason."""
    return bool(item.get("revive_reason"))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_weekly_review(inputs: dict, now_iso: str) -> WeeklyReview:
    """Run the weekly executive review pipeline.

    Parameters
    ----------
    inputs : dict
        Keys: projects[], capacity (Rhythm capacity summary),
        growth_opportunities[], scholar_obligations[], stalled[],
        experiments[], decisions[], risks[], deferred[].
    now_iso : str
        ISO timestamp for the review run (input only, no clock reads).

    Returns
    -------
    WeeklyReview
        Deterministic, frozen result.
    """
    projects = inputs.get("projects", [])
    capacity = inputs.get("capacity", {}) or {}
    growth_opps = inputs.get("growth_opportunities", [])
    scholar_obs = inputs.get("scholar_obligations", [])
    stalled = inputs.get("stalled", [])
    experiments = inputs.get("experiments", [])
    decisions = inputs.get("decisions", [])
    risks = inputs.get("risks", [])
    deferred = inputs.get("deferred", [])

    # Process risks for the review.
    processed_risks = []
    for r in risks:
        processed_risks.append(
            {
                "id": r.get("id", ""),
                "label": r.get("label", ""),
                "status": r.get("status", ""),
                "severity": r.get("severity", ""),
            }
        )

    # Step 1: Portfolio priorities -- rank by materiality.
    ranked = _rank_projects(projects)
    portfolio_priorities = []
    for rank, p in enumerate(ranked, start=1):
        portfolio_priorities.append(
            {
                "rank": rank,
                "id": p.get("id", ""),
                "name": p.get("name", ""),
                "score": _materiality_score(p),
                "status": p.get("status", ""),
            }
        )

    # Step 2: Incorporate capacity -- overloaded -> capacity_request.
    capacity_requests = []
    load = capacity.get("load", 0)
    overload = capacity.get("overload", False)
    is_overloaded = overload or (isinstance(load, (int, float)) and load > 100)
    if is_overloaded:
        capacity_requests.append(
            {
                "id": "capacity",
                "kind": "CAPACITY_REQUEST",
                "load": load,
                "overload": overload,
                "message": "Rhythm capacity overloaded; reduce load or add capacity.",
            }
        )

    # Step 3: Incorporate material growth opportunities.
    material_growth = []
    for opp in growth_opps:
        if _is_material_growth(opp):
            material_growth.append(
                {
                    "id": opp.get("id", ""),
                    "name": opp.get("name", ""),
                    "impact": opp.get("impact", ""),
                    "evidence": opp.get("evidence", ""),
                }
            )

    # Step 4: Incorporate Scholar obligations (deadline-driven).
    scholar_incorporated = []
    for obl in scholar_obs:
        if _is_scholar_deadline_driven(obl):
            scholar_incorporated.append(
                {
                    "id": obl.get("id", ""),
                    "name": obl.get("name", ""),
                    "due_date": obl.get("due_date", ""),
                    "requirement": obl.get("requirement", ""),
                }
            )

    # Step 5: Surface stalled work (sorted by id for determinism).
    stalled_work = []
    for item in sorted(stalled, key=lambda x: x.get("id", "")):
        stalled_work.append(
            {
                "id": item.get("id", ""),
                "label": item.get("label", ""),
                "status": item.get("status", "stalled"),
                "follow_up": "STALLED_FOLLOW_UP",
            }
        )

    # Step 6: Surface experiments/decisions awaiting action.
    experiments_awaiting = []
    for exp in experiments:
        if exp.get("awaiting_action", False) or exp.get("status") in ("new", "needs_review"):
            experiments_awaiting.append(
                {
                    "id": exp.get("id", ""),
                    "name": exp.get("name", ""),
                    "status": exp.get("status", ""),
                    "awaiting_action": True,
                }
            )

    decisions_awaiting = []
    for dec in decisions:
        if dec.get("awaiting_action", False) or dec.get("status") in ("open", "pending"):
            decisions_awaiting.append(
                {
                    "id": dec.get("id", ""),
                    "label": dec.get("label", ""),
                    "status": dec.get("status", ""),
                    "awaiting_action": True,
                }
            )

    # Step 7: Build next_week_priorities (capped, ordered by rank).
    # Exclude deferred items unless they have revive_reason.
    active_priorities = []
    for p in ranked:
        pid = p.get("id", "")
        # Check if this project is in the deferred list without revive_reason.
        is_deferred = False
        for d in deferred:
            if d.get("id") == pid and _has_deferred_flag(d) and not _has_revive_reason(d):
                is_deferred = True
                break
        if is_deferred:
            continue
        active_priorities.append(p)

    next_week_priorities = []
    for rank, p in enumerate(active_priorities[:MAX_NEXT_WEEK_PRIORITIES], start=1):
        next_week_priorities.append(
            {
                "rank": rank,
                "id": p.get("id", ""),
                "name": p.get("name", ""),
                "status": p.get("status", ""),
            }
        )

    # Step 8: Build follow-ups.
    # Every next action must have owner and follow_up type.
    follow_ups = []
    priority_idx = 0
    for p in active_priorities:
        pid = p.get("id", "")
        pname = p.get("name", "")
        # Check deferred with revive_reason -> flag REVIVED_WITH_REASON.
        revived = False
        for d in deferred:
            if d.get("id") == pid and _has_deferred_flag(d) and _has_revive_reason(d):
                revived = True
                break

        owner = p.get("owner", "unassigned")
        follow_up_type = "REVIVED_WITH_REASON" if revived else "NEXT_ACTION"
        follow_ups.append(
            {
                "id": pid,
                "name": pname,
                "owner": owner,
                "follow_up": follow_up_type,
                "priority_rank": priority_idx + 1,
            }
        )
        priority_idx += 1

    # Add follow-ups for stalled work.
    for item in stalled_work:
        owner = item.get("owner", "unassigned")
        follow_ups.append(
            {
                "id": item["id"],
                "name": item.get("label", ""),
                "owner": owner,
                "follow_up": "STALLED_FOLLOW_UP",
            }
        )

    # Add follow-ups for capacity requests.
    for cr in capacity_requests:
        follow_ups.append(
            {
                "id": cr["id"],
                "name": "Rhythm capacity overload",
                "owner": "rhythm",
                "follow_up": "CAPACITY_REQUEST",
            }
        )

    # Add follow-ups for experiments awaiting action.
    for exp in experiments_awaiting:
        owner = exp.get("owner", "unassigned")
        follow_ups.append(
            {
                "id": exp["id"],
                "name": exp.get("name", ""),
                "owner": owner,
                "follow_up": "EXPERIMENT_REVIEW",
            }
        )

    # Add follow-ups for decisions awaiting action.
    for dec in decisions_awaiting:
        owner = dec.get("owner", "unassigned")
        follow_ups.append(
            {
                "id": dec["id"],
                "name": dec.get("label", ""),
                "owner": owner,
                "follow_up": "DECISION_FOLLOW_UP",
            }
        )

    return WeeklyReview(
        portfolio_priorities=portfolio_priorities,
        capacity_requests=capacity_requests,
        growth_opportunities=material_growth,
        scholar_obligations=scholar_incorporated,
        stalled_work=stalled_work,
        experiments_awaiting=experiments_awaiting,
        decisions_awaiting=decisions_awaiting,
        risks=processed_risks,
        next_week_priorities=next_week_priorities,
        follow_ups=follow_ups,
    )


def build_weekly_briefing(review: WeeklyReview) -> WeekBriefing:
    """Build a concise plain-ASCII weekly briefing from a WeeklyReview.

    Max BRIEFING_MAX_LINES lines.  No empty or boilerplate lines.
    Deterministic.
    """
    lines: list[str] = []

    # Headline.
    lines.append("WEEKLY EXECUTIVE REVIEW")

    # Top priorities (one line each).
    for p in review.next_week_priorities:
        lines.append(
            f"Priority {p['rank']}: {p['name']} ({p['id']}) - {p['status']}"
        )

    # Capacity note.
    if review.capacity_requests:
        for cr in review.capacity_requests:
            lines.append(
                f"Capacity: load={cr['load']} overload={cr['overload']}"
            )

    # Decisions needed.
    if review.decisions_awaiting:
        for dec in review.decisions_awaiting:
            lines.append(
                f"Decision needed: {dec['label']} ({dec['id']})"
            )

    # Risks.
    for risk in review.risks:
        lines.append(f"Risk: {risk.get('label', risk.get('id', ''))} ({risk.get('status', '')})")

    # Follow-up count.
    fu_count = len(review.follow_ups)
    lines.append(f"Follow-ups: {fu_count}")

    # Cap at BRIEFING_MAX_LINES; drop trailing boilerplate if over.
    if len(lines) > BRIEFING_MAX_LINES:
        lines = lines[:BRIEFING_MAX_LINES]

    # Remove any empty lines (safety).
    lines = [l for l in lines if l.strip()]

    return WeekBriefing(lines=lines)