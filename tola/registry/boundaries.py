"""Boundary enforcement and profile version audit for Batch T4.

Hard enforcement:
  - Reject Growth direct schedule writes (T4-04)
  - Reject Tola My Rhythm writes (T4-05)
  - Reject Scholar taking product-growth authority (T4-06)
  - Profile version changes are auditable via PROFILE_VERSION_HISTORY (T4-08)
Plain ASCII.  Stdlib only.  Deterministic.
"""

from __future__ import annotations

from typing import Any

from tola.registry.profiles import (
    PROFILE_VERSION_HISTORY,
    update_profile_version,
)
from tola.registry.capability import agent_boundary_check


# ---------------------------------------------------------------------------
# Enforce a boundary decision, raising on violation
# ---------------------------------------------------------------------------

class BoundaryViolation(Exception):
    """Raised when an action violates a frozen specialist boundary."""


def enforce_boundary(agent_id: str, action: str) -> dict:
    """Enforce a hard boundary check.

    Returns the boundary-check result dict if allowed.
    Raises BoundaryViolation if the action is forbidden.

    Covers T4-04, T4-05, T4-06.
    """
    result = agent_boundary_check(agent_id, action)
    if not result["allowed"]:
        raise BoundaryViolation(result["reason"])
    return result


# ---------------------------------------------------------------------------
# Profile version audit (T4-08)
# ---------------------------------------------------------------------------

def record_profile_version_change(
    agent_id: str,
    new_version: str,
    changed_by: str,
    change_reason: str,
    timestamp: str,
) -> dict:
    """Record a profile version change and return the audit entry.

    The underlying update_profile_version appends to PROFILE_VERSION_HISTORY.
    This wrapper provides a clean boundary for callers.

    Raises KeyError if *agent_id* is not registered.
    """
    if agent_id not in PROFILE_VERSION_HISTORY and agent_id not in (
        "tola", "rhythm", "growth", "scholar", "marketing"
    ):
        raise KeyError(f"Unknown agent_id '{agent_id}'")

    updated = update_profile_version(
        agent_id=agent_id,
        new_version=new_version,
        changed_by=changed_by,
        change_reason=change_reason,
        timestamp=timestamp,
    )

    return {
        "agent_id": agent_id,
        "new_version": updated.version,
        "last_updated_at": updated.last_updated_at,
        "history_entry_count": len(PROFILE_VERSION_HISTORY),
    }


def get_profile_version_history() -> list[dict[str, Any]]:
    """Return a copy of the profile version audit log."""
    return list(PROFILE_VERSION_HISTORY)