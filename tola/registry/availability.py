"""Availability and delegation checks for Batch T4.

Implements:
  - DelegationBlockedError for non-ACTIVE agents (T4-10)
  - FUTURE_SPECIALIST_DEPENDENCY record for ineligible marketing work (T4-12)
  - Marketing Agent activation gate (T4-13)
Plain ASCII.  Stdlib only.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from tola.registry.profiles import (
    PROFILES,
    AvailabilityStatus,
    ACTIVE,
    FUTURE_NOT_AVAILABLE,
)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

class DelegationBlockedError(Exception):
    """Raised when delegation is attempted to a non-ACTIVE agent."""


class MarketingActivationError(Exception):
    """Raised when Marketing Agent activation prerequisites are unmet."""


# ---------------------------------------------------------------------------
# FUTURE_SPECIALIST_DEPENDENCY record (T4-12)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FutureSpecialistDependency:
    """Record that work requires a future specialist not yet available."""

    work_description: str
    required_domain: str
    intended_agent_id: str
    reason: str
    status: str = "DEFERRED"


FUTURE_SPECIALIST_DEPENDENCY = FutureSpecialistDependency


# ---------------------------------------------------------------------------
# Delegation check (T4-10)
# ---------------------------------------------------------------------------

def check_delegation_allowed(agent_id: str) -> bool:
    """Return True only if the agent is ACTIVE.

    Raises DelegationBlockedError if the agent is not ACTIVE.
    Covers T4-10.
    """
    profile = PROFILES.get(agent_id)
    if profile is None:
        raise DelegationBlockedError(
            f"Agent '{agent_id}' is not registered; delegation blocked."
        )
    if profile.availability_status != ACTIVE:
        raise DelegationBlockedError(
            f"Agent '{agent_id}' has availability_status "
            f"'{profile.availability_status.value}'; delegation to "
            f"non-ACTIVE agents is blocked (T4-10)."
        )
    return True


# ---------------------------------------------------------------------------
# Marketing work routing (T4-11, T4-12)
# ---------------------------------------------------------------------------

# Marketing sub-domains eligible for Growth under the current contract
MARKETING_ELIGIBLE_FOR_GROWTH = frozenset({
    "funnel analysis",
    "conversion analysis",
    "retention analysis",
    "product metrics",
    "experiment design",
    "acquisition analysis",
    "growth recommendation",
})


def route_marketing_work(task_description: str) -> dict:
    """Route marketing work to Growth or record a FUTURE_SPECIALIST_DEPENDENCY.

    If the work is eligible under Growth's current contract, routes to Growth.
    Otherwise records a FUTURE_SPECIALIST_DEPENDENCY and never fakes execution.
    Covers T4-11 and T4-12.
    """
    lowered = task_description.lower().strip()

    # Check if Growth can own this under its current contract
    for eligible in MARKETING_ELIGIBLE_FOR_GROWTH:
        if eligible in lowered:
            return {
                "routed_to": "growth",
                "record_type": "ROUTED_TO_ACTIVE_SPECIALIST",
                "reason": (
                    f"Marketing work '{task_description}' is eligible under "
                    f"Growth's current contract -> routed to Growth (T4-11)."
                ),
            }

    # Ineligible marketing work: record dependency, never fake execution
    dep = FutureSpecialistDependency(
        work_description=task_description,
        required_domain="marketing",
        intended_agent_id="marketing",
        reason=(
            "Marketing work is not eligible under Growth's current contract. "
            "Marketing Agent is FUTURE_NOT_AVAILABLE. Work deferred until "
            "Marketing Agent activation prerequisites are met (T4-12)."
        ),
        status="DEFERRED",
    )
    return {
        "routed_to": None,
        "record_type": "FUTURE_SPECIALIST_DEPENDENCY",
        "dependency": {
            "work_description": dep.work_description,
            "required_domain": dep.required_domain,
            "intended_agent_id": dep.intended_agent_id,
            "reason": dep.reason,
            "status": dep.status,
        },
        "reason": dep.reason,
    }


# ---------------------------------------------------------------------------
# Marketing Agent activation gate (T4-13)
# ---------------------------------------------------------------------------

def record_future_specialist_dependency(
    work_description: str,
    required_domain: str,
    intended_agent_id: str,
    reason: str,
) -> FutureSpecialistDependency:
    """Create and return a FUTURE_SPECIALIST_DEPENDENCY record.

    Used when marketing work cannot be owned by Growth under the
    current contract.  Never fakes execution.
    """
    dep = FutureSpecialistDependency(
        work_description=work_description,
        required_domain=required_domain,
        intended_agent_id=intended_agent_id,
        reason=reason,
        status="DEFERRED",
    )
    return dep


def validate_marketing_activation() -> dict:
    """Check whether Marketing Agent can become ACTIVE.

    All activation_requirements must be complete.  Returns a dict with
    keys: can_activate (bool), missing (list[str]), status (str).
    Covers T4-13.
    """
    profile = PROFILES["marketing"]

    if profile.availability_status == ACTIVE:
        return {
            "can_activate": True,
            "missing": [],
            "status": "ACTIVE",
            "reason": "Marketing Agent is already ACTIVE.",
        }

    missing = list(profile.activation_requirements)

    return {
        "can_activate": False,
        "missing": missing,
        "status": profile.availability_status.value,
        "reason": (
            f"Marketing Agent cannot become ACTIVE until all "
            f"activation_requirements are complete. "
            f"Missing: {', '.join(missing)} (T4-13)."
        ),
    }