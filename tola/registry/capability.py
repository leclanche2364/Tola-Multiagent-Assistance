"""Capability routing and boundary checks for Batch T4.

Implements agent_capability_get, agent_capability_match,
agent_boundary_check, and agent_current_load_get.
Plain ASCII.  Stdlib only.  Deterministic: no clock reads.
"""

from __future__ import annotations

from typing import Optional

from tola.registry.profiles import PROFILES, AvailabilityStatus


# ---------------------------------------------------------------------------
# Routing table: task domain -> agent_id
# ---------------------------------------------------------------------------

ROUTING_TABLE: dict[str, str] = {
    "scheduling": "rhythm",
    "capacity": "rhythm",
    "schedule": "rhythm",
    "rhythm": "rhythm",
    "product": "growth",
    "growth": "growth",
    "funnel": "growth",
    "acquisition": "growth",
    "conversion": "growth",
    "retention": "growth",
    "experiment": "growth",
    "marketing": "growth",
    "learning": "scholar",
    "scholar": "scholar",
    "curriculum": "scholar",
    "evidence": "scholar",
    "study": "scholar",
    "gap": "scholar",
}

# Domains that only Rhythm may own (hard boundary)
_RHYTHM_OWNED = frozenset({"scheduling", "capacity", "schedule", "rhythm"})
# Domains that only Growth may own (hard boundary)
_GROWTH_OWNED = frozenset({
    "product", "growth", "funnel", "acquisition",
    "conversion", "retention", "experiment", "marketing",
})
# Domains that only Scholar may own (hard boundary)
_SCHOLAR_OWNED = frozenset({
    "learning", "scholar", "curriculum", "evidence", "study", "gap",
})


def agent_capability_get(agent_id: str) -> Optional[dict]:
    """Return the capability profile dict for *agent_id*, or None.

    Covers T4-01..T4-03 via agent_capability_match; this accessor
    returns the raw profile for a known agent.
    """
    profile = PROFILES.get(agent_id)
    if profile is None:
        return None
    return {
        "agent_id": profile.agent_id,
        "domain": profile.domain,
        "responsibilities": list(profile.responsibilities),
        "allowed_tools": list(profile.allowed_tools),
        "forbidden_actions": list(profile.forbidden_actions),
        "skills": list(profile.skills),
        "availability_status": profile.availability_status.value,
        "activation_requirements": list(profile.activation_requirements),
        "version": profile.version,
        "last_updated_at": profile.last_updated_at,
    }


def agent_capability_match(task_description_or_domain: str) -> dict:
    """Route a task description or domain string to the owning agent.

    Returns a dict with keys:
        agent_id (str or None)
        confidence (float)
        reason (str)

    Routing rules (QA T4-01..T4-03, T4-07, T4-11):
        scheduling/capacity -> Rhythm
        funnel/product analysis -> Growth
        learning-gap -> Scholar
        eligible marketing work -> Growth
        unknown domain -> None + safe escalation reason (never guess)
    """
    lowered = task_description_or_domain.lower().strip()

    # Exact domain match first
    if lowered in ROUTING_TABLE:
        agent_id = ROUTING_TABLE[lowered]
        return {
            "agent_id": agent_id,
            "confidence": 1.0,
            "reason": f"Exact domain match: {lowered} -> {agent_id}",
        }

    # Keyword containment routing
    for domain_keyword, agent_id in (
        ("schedul", "rhythm"),
        ("capacit", "rhythm"),
        ("rhythm", "rhythm"),
        ("funnel", "growth"),
        ("product", "growth"),
        ("growth", "growth"),
        ("acquisition", "growth"),
        ("conversion", "growth"),
        ("retention", "growth"),
        ("experiment", "growth"),
        ("market", "growth"),
        ("learn", "scholar"),
        ("scholar", "scholar"),
        ("curriculum", "scholar"),
        ("evidence", "scholar"),
        ("study", "scholar"),
        ("gap", "scholar"),
    ):
        if domain_keyword in lowered:
            return {
                "agent_id": agent_id,
                "confidence": 0.9,
                "reason": f"Keyword '{domain_keyword}' matched in task description -> {agent_id}",
            }

    # Unknown domain: safe escalation, never guess
    return {
        "agent_id": None,
        "confidence": 0.0,
        "reason": (
            "Unknown domain: task description does not match any "
            "registered specialist domain. Safe escalation required "
            "(return None + reason, never guess)."
        ),
    }


def agent_boundary_check(agent_id: str, action: str) -> dict:
    """Check whether *agent_id* is allowed to perform *action*.

    Returns {"allowed": bool, "reason": str}.
    Covers T4-04 (Growth direct schedule write), T4-05 (Tola My Rhythm
    write), T4-06 (Scholar product-growth authority).
    """
    profile = PROFILES.get(agent_id)
    if profile is None:
        return {
            "allowed": False,
            "reason": f"Unknown agent_id '{agent_id}': no profile registered.",
        }

    action_lower = action.lower().strip()

    # Check forbidden actions
    for forbidden in profile.forbidden_actions:
        if forbidden.lower() == action_lower or action_lower.startswith(forbidden.lower()):
            return {
                "allowed": False,
                "reason": (
                    f"Action '{action}' is forbidden for agent '{agent_id}' "
                    f"(domain: {profile.domain})."
                ),
            }

    # Hard boundary overrides (frozen authority)
    # T4-04: Growth must not write directly to schedule
    if agent_id == "growth" and action_lower in (
        "direct_schedule_write",
        "rhythm_schedule_write",
        "schedule_write",
        "rhythm_direct_write",
    ):
        return {
            "allowed": False,
            "reason": (
                "Growth cannot perform direct schedule writes. "
                "Scheduling authority is frozen to Rhythm (T4-04)."
            ),
        }

    # T4-05: Tola must not write directly to My Rhythm
    if agent_id == "tola" and action_lower in (
        "direct_my_rhythm_write",
        "my_rhythm_write",
        "rhythm_direct_write",
        "rhythm_schedule_write",
    ):
        return {
            "allowed": False,
            "reason": (
                "Tola must never write directly to My Rhythm. "
                "Use CAPACITY_QUERY -> CAPACITY_REPORT -> TASK_COMMITTED "
                "protocol (T4-05)."
            ),
        }

    # T4-06: Scholar cannot take product-growth authority
    if agent_id == "scholar" and action_lower in (
        "product_growth_analysis",
        "funnel_analysis",
        "growth_recommendation",
        "acquisition_analysis",
        "conversion_analysis",
        "retention_analysis",
        "product_metrics_write",
    ):
        return {
            "allowed": False,
            "reason": (
                "Scholar cannot claim product-growth authority. "
                "Product/growth analysis is frozen to Growth (T4-06)."
            ),
        }

    return {
        "allowed": True,
        "reason": f"Action '{action}' is within '{agent_id}' boundary.",
    }


def agent_current_load_get(agent_id: str, load_state: Optional[dict] = None) -> int:
    """Return the current load for *agent_id*.

    *load_state* is an optional dict mapping agent_id -> int load.
    If *load_state* is None or *agent_id* is absent, returns 0 (T4 default).
    Deterministic: no clock reads.
    """
    if load_state is None:
        return 0
    return int(load_state.get(agent_id, 0))