# Authority and permission checks -- Batch T18.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.persona.profile import (
    PreferenceStatus,
    UserOperatingProfile,
    user_profile_get,
)


@dataclass(frozen=True)
class PermissionRecord:
    action: str
    granted_at: str
    scope: str
    approval_count: int


@dataclass(frozen=True)
class AuthorityCheck:
    allowed: bool
    reason: str
    capability_set_changed: bool


# ---------------------------------------------------------------------------
# Authority check: repeated user approval of an action never expands
# Tola's permissions. Approval is per-instance; approval counts are
# tracked but the capability set remains unchanged.
# ---------------------------------------------------------------------------

def check_authority(
    profile: UserOperatingProfile,
    action: str,
    scope: str,
    approval_count: int,
) -> AuthorityCheck:
    """Check whether Tola has authority to perform *action* in *scope*.

    Repeated approvals do NOT expand the capability set.
    The capability set is determined by the agent's registered
    permissions (from profiles), not by approval frequency.
    """
    # Tola's allowed actions come from the registry profiles.
    from tola.registry.profiles import PROFILES

    tola_profile = PROFILES.get("tola")
    if tola_profile is None:
        return AuthorityCheck(
            allowed=False,
            reason="Tola profile not found in registry.",
            capability_set_changed=False,
        )

    # Check if action is in Tola's allowed tools or forbidden actions.
    action_lower = action.lower().strip()
    for forbidden in tola_profile.forbidden_actions:
        if action_lower == forbidden.lower() or action_lower.startswith(forbidden.lower()):
            return AuthorityCheck(
                allowed=False,
                reason=f"Action '{action}' is forbidden for Tola (boundary check).",
                capability_set_changed=False,
            )

    # Check if action is in allowed tools.
    for allowed in tola_profile.allowed_tools:
        if action_lower == allowed.lower() or action_lower.startswith(allowed.lower()):
            # Authority granted -- but capability set does NOT expand
            # regardless of how many times this action has been approved.
            return AuthorityCheck(
                allowed=True,
                reason=f"Action '{action}' is within Tola's registered capability set.",
                capability_set_changed=False,
            )

    return AuthorityCheck(
        allowed=False,
        reason=f"Action '{action}' is not in Tola's registered capability set.",
        capability_set_changed=False,
    )


def get_active_preferences(
    profile: UserOperatingProfile,
    scope: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return only ACTIVE preferences with provenance and confidence.

    Each returned dict contains: key, value, provenance (source,
    evidence_refs, observed_at, project_id), confidence, and scope.
    """
    active = user_profile_get(profile, scope=scope)
    result = []
    for pref in active:
        result.append(
            {
                "key": pref.key,
                "value": pref.value,
                "provenance": {
                    "source": pref.provenance.source,
                    "evidence_refs": list(pref.provenance.evidence_refs),
                    "observed_at": pref.provenance.observed_at,
                    "project_id": pref.provenance.project_id,
                },
                "confidence": pref.confidence,
                "scope": pref.scope,
            }
        )
    return tuple(result)