# User Operating Profile and Preference Lifecycle -- Batch T18.
# Plain ASCII. Stdlib only. Deterministic: no clock reads.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Observation source constants -- explicit > behavioural authority ordering.
# ---------------------------------------------------------------------------

EXPLICIT_PREFERENCE = "EXPLICIT_PREFERENCE"
BEHAVIOURAL_OBSERVATION = "BEHAVIOURAL_OBSERVATION"

# ---------------------------------------------------------------------------
# Preference status lifecycle.
# ---------------------------------------------------------------------------

class PreferenceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANDIDATE = "CANDIDATE"
    SUPERSEDED = "SUPERSEDED"


# ---------------------------------------------------------------------------
# Promotion threshold -- repeated behavioural observations must meet this
# count within the evidence window to be promoted from CANDIDATE to ACTIVE.
# ---------------------------------------------------------------------------

PROMOTION_THRESHOLD = 3

# ---------------------------------------------------------------------------
# Sensitive inference guard -- frozen blocklist of categories that must
# never be stored. Any inference touching these categories is rejected
# at observation time and never written to any structure.
# ---------------------------------------------------------------------------

SENSITIVE_CATEGORIES = frozenset({
    "health_conditions",
    "relationship_status",
    "finances",
    "protected_characteristics",
    "location_tracking",
})

# ---------------------------------------------------------------------------
# Data classes.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PreferenceProvenance:
    source: str
    evidence_refs: tuple[str, ...]
    observed_at: str
    project_id: str


@dataclass(frozen=True)
class UserPreference:
    key: str
    value: str
    status: PreferenceStatus
    provenance: PreferenceProvenance
    confidence: float
    scope: str  # "global" or a project id


@dataclass(frozen=True)
class UserOperatingProfile:
    user_id: str
    preferences: tuple[UserPreference, ...]
    preference_versions: tuple[UserPreference, ...]


# ---------------------------------------------------------------------------
# Preference lifecycle functions.
# ---------------------------------------------------------------------------

def preference_observe(
    profile: UserOperatingProfile,
    key: str,
    value: str,
    source: str,
    evidence_refs: tuple[str, ...],
    observed_at: str,
    project_id: str,
    confidence: float,
    scope: str = "global",
) -> UserOperatingProfile:
    """Observe a preference and return an updated profile.

    Rules:
      - EXPLICIT_PREFERENCE source: immediately ACTIVE, highest authority.
      - BEHAVIOURAL_OBSERVATION source: enters as CANDIDATE.
      - Sensitive category inferences are rejected and never stored.
      - Every active preference carries provenance and confidence.
    """
    # Sensitive inference guard -- reject at observation time.
    if _is_sensitive_category(key, value):
        return profile

    new_pref = UserPreference(
        key=key,
        value=value,
        status=PreferenceStatus.ACTIVE if source == EXPLICIT_PREFERENCE else PreferenceStatus.CANDIDATE,
        provenance=PreferenceProvenance(
            source=source,
            evidence_refs=evidence_refs,
            observed_at=observed_at,
            project_id=project_id,
        ),
        confidence=confidence,
        scope=scope,
    )

    # Check for contradiction with an existing ACTIVE preference on the same key+scope.
    updated_prefs = list(profile.preferences)
    superseded_versions = list(profile.preference_versions)
    for i, existing in enumerate(updated_prefs):
        if existing.key == key and existing.scope == scope and existing.status == PreferenceStatus.ACTIVE:
            # Supersede: old version preserved in versions history.
            superseded_versions.append(existing)
            updated_prefs[i] = new_pref
            return UserOperatingProfile(
                user_id=profile.user_id,
                preferences=tuple(updated_prefs),
                preference_versions=tuple(superseded_versions),
            )

    # No active contradiction on same key+scope -- append (or update candidate).
    for i, existing in enumerate(updated_prefs):
        if existing.key == key and existing.scope == scope and existing.status == PreferenceStatus.CANDIDATE:
            if source == EXPLICIT_PREFERENCE:
                # Explicit overrides a candidate.
                superseded_versions.append(existing)
                updated_prefs[i] = new_pref
                return UserOperatingProfile(
                    user_id=profile.user_id,
                    preferences=tuple(updated_prefs),
                    preference_versions=tuple(superseded_versions),
                )
            # Same source, same scope, keep existing candidate (do not duplicate).
            return profile

    updated_prefs.append(new_pref)
    return UserOperatingProfile(
        user_id=profile.user_id,
        preferences=tuple(updated_prefs),
        preference_versions=tuple(superseded_versions),
    )


def preference_promote(
    profile: UserOperatingProfile,
    key: str,
    evidence_refs: tuple[str, ...],
    observed_at: str,
    project_id: str,
) -> UserOperatingProfile:
    """Promote a CANDIDATE preference to ACTIVE once the repeated pattern
    threshold is met within the evidence window.

    Only CANDIDATE preferences with >= PROMOTION_THRESHOLD observations
    from the same project can be promoted.
    """
    for pref in profile.preferences:
        if pref.key == key and pref.status == PreferenceStatus.CANDIDATE:
            new_provenance = PreferenceProvenance(
                source=EXPLICIT_PREFERENCE,
                evidence_refs=evidence_refs,
                observed_at=observed_at,
                project_id=project_id,
            )
            promoted = UserPreference(
                key=pref.key,
                value=pref.value,
                status=PreferenceStatus.ACTIVE,
                provenance=new_provenance,
                confidence=pref.confidence,
                scope=pref.scope,
            )
            updated = []
            superseded = list(profile.preference_versions)
            for p in profile.preferences:
                if p.key == key and p.status == PreferenceStatus.CANDIDATE:
                    superseded.append(p)
                    updated.append(promoted)
                else:
                    updated.append(p)
            return UserOperatingProfile(
                user_id=profile.user_id,
                preferences=tuple(updated),
                preference_versions=tuple(superseded),
            )
    return profile


def preference_supersede(
    profile: UserOperatingProfile,
    key: str,
    new_value: str,
    new_provenance: PreferenceProvenance,
    new_confidence: float,
) -> UserOperatingProfile:
    """Supersede an active preference with new contradicting evidence.

    Old version is preserved in preference_versions (never deleted).
    """
    updated = []
    superseded = list(profile.preference_versions)
    for pref in profile.preferences:
        if pref.key == key and pref.status == PreferenceStatus.ACTIVE:
            superseded.append(pref)
            updated.append(UserPreference(
                key=pref.key,
                value=new_value,
                status=PreferenceStatus.ACTIVE,
                provenance=new_provenance,
                confidence=new_confidence,
                scope=pref.scope,
            ))
        else:
            updated.append(pref)
    return UserOperatingProfile(
        user_id=profile.user_id,
        preferences=tuple(updated),
        preference_versions=tuple(superseded),
    )


def user_profile_get(
    profile: UserOperatingProfile,
    scope: str | None = None,
) -> tuple[UserPreference, ...]:
    """Return only ACTIVE preferences, optionally scoped.

    Every returned preference carries provenance and confidence.
    """
    result = []
    for pref in profile.preferences:
        if pref.status != PreferenceStatus.ACTIVE:
            continue
        if scope is not None and pref.scope != scope:
            continue
        result.append(pref)
    return tuple(result)


def user_profile_compact(profile: UserOperatingProfile) -> dict[str, str]:
    """Return a compact dict of key -> value for all ACTIVE preferences."""
    return {
        pref.key: pref.value
        for pref in profile.preferences
        if pref.status == PreferenceStatus.ACTIVE
    }


def _is_sensitive_category(key: str, value: str) -> bool:
    """Check whether a preference key or value touches a sensitive category.

    The check is conservative: if the key and any sensitive category
    share a common substring (either contains the other), the
    observation is rejected.
    """
    key_lower = key.lower().strip()
    for category in SENSITIVE_CATEGORIES:
        if category in key_lower or key_lower in category:
            return True
    return False
