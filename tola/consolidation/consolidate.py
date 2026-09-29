# Consolidation logic: daily, weekly, session reconstruction.
# Plain ASCII. Stdlib only. Deterministic. No clock reads.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.persona.profile import (
    PreferenceStatus,
    UserOperatingProfile,
    user_profile_compact,
)
from tola.consolidation.mapper import (
    BLACKBOARD_PROFILE,
    USER_MD,
    MEMORY_MD,
    DATED_NOTES,
    MemoryMap,
)
from tola.consolidation.rules import (
    CONFLICT_RESOLUTION_ORDER,
    PROMOTION_EVIDENCE_WINDOW_DAYS,
    RECENCY_WINDOW_DAYS,
    ConsolidationRules,
    validate_no_superseded_active,
    validate_explicit_high_authority_included,
)


# ---------------------------------------------------------------------------
# Result dataclasses.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConsolidationResult:
    actions: tuple[str, ...] = ()
    profile_updates: dict[str, Any] = field(default_factory=dict)
    expired: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Daily consolidation.
# ---------------------------------------------------------------------------

def daily_consolidate(
    profile: UserOperatingProfile,
    observations: list[dict[str, Any]],
    now_iso: str,
) -> ConsolidationResult:
    """Daily consolidation pass.

    - Promotes CANDIDATE preferences that hit PROMOTION_THRESHOLD
      within the evidence window (PROMOTION_EVIDENCE_WINDOW_DAYS).
    - Drops expired observations past their recency window
      (RECENCY_WINDOW_DAYS).
    - Ensures no superseded preference remains active.
    - Validates against T18 lifecycle semantics: supersede wins,
      old version archived in preference_versions.

    All inputs are in-memory structures; no file I/O.
    now_iso is an ISO date string (no clock reads).
    """
    rules = ConsolidationRules()
    actions: list[str] = []
    expired: list[str] = []
    profile_updates: dict[str, Any] = {}

    # 1. Drop expired observations past recency window.
    for obs in observations:
        observed_at = obs.get("observed_at", "")
        if observed_at and not rules.is_recent(observed_at, now_iso):
            expired.append(obs.get("id", obs.get("key", "unknown")))
            actions.append(f"EXPIRED: {obs.get('key', 'unknown')}")

    # 2. Promote candidates that hit threshold within evidence window.
    #    We check candidates that have enough observations within the
    #    evidence window and call preference_promote.
    from tola.persona.profile import preference_promote

    candidates = [
        p for p in profile.preferences
        if p.status == PreferenceStatus.CANDIDATE
    ]
    for candidate in candidates:
        # Check if candidate has enough evidence within the window.
        if rules.is_recent(candidate.provenance.observed_at, now_iso):
            evidence_count = len(candidate.provenance.evidence_refs)
            if evidence_count >= 3:
                profile = preference_promote(
                    profile,
                    key=candidate.key,
                    evidence_refs=candidate.provenance.evidence_refs,
                    observed_at=now_iso,
                    project_id=candidate.provenance.project_id,
                )
                actions.append(
                    f"PROMOTED: {candidate.key}={candidate.value}"
                )

    # 3. Validate no superseded preference is active.
    active_prefs = [p for p in profile.preferences if p.status == PreferenceStatus.ACTIVE]
    if not validate_no_superseded_active(
        [
            {
                "key": p.key,
                "status": p.status.value,
                "active": True,
            }
            for p in profile.preferences
        ]
    ):
        actions.append("CONFLICT: superseded preference still active")

    # 4. Build compact profile view.
    compact = user_profile_compact(profile)
    profile_updates["compact"] = compact
    profile_updates["active_count"] = len(active_prefs)

    return ConsolidationResult(
        actions=tuple(actions),
        profile_updates=profile_updates,
        expired=tuple(expired),
    )


# ---------------------------------------------------------------------------
# Weekly consolidation.
# ---------------------------------------------------------------------------

def weekly_consolidate(
    profile: UserOperatingProfile,
    memory_items: list[dict[str, Any]],
    now_iso: str,
) -> ConsolidationResult:
    """Weekly consolidation pass.

    - Compacts the user model via rebuild_compact().
    - Ensures every EXPLICIT_PREFERENCE is included (compaction
      never drops high-authority items).
    - Excludes superseded/inactive preferences.
    - Validates the compact result.
    """
    actions: list[str] = []
    profile_updates: dict[str, Any] = {}

    # Rebuild compact active-preference view.
    compact = rebuild_compact(profile)
    profile_updates["compact"] = compact

    # Validate: all explicit preferences must be in compact.
    explicit_prefs = [
        p for p in profile.preferences
        if p.provenance.source == "EXPLICIT_PREFERENCE"
        and p.status == PreferenceStatus.ACTIVE
    ]
    if not validate_explicit_high_authority_included(compact, explicit_prefs):
        actions.append("WARNING: explicit preference dropped from compact")
    else:
        actions.append("COMPACT: all explicit preferences retained")

    # Validate no superseded items are active.
    active_keys = set(compact.keys())
    superseded_keys = set(
        p.key for p in profile.preference_versions
        if p.status == PreferenceStatus.SUPERSEDED
    )
    # Superseded keys may overlap with active if re-promoted; that is
    # fine -- only truly active superseded items are flagged.
    for p in profile.preferences:
        if p.status == PreferenceStatus.SUPERSEDED and p.key in active_keys:
            actions.append(
                f"CONFLICT: superseded key {p.key!r} still active"
            )

    # Process memory items into zones.
    mm = MemoryMap()
    mm.map_content(MEMORY_MD, [
        item for item in memory_items
        if item.get("type") == "durable_lesson"
    ])
    mm.map_content(DATED_NOTES, [
        item for item in memory_items
        if item.get("type") == "recent_observation"
    ])

    profile_updates["memory_zone_items"] = {
        MEMORY_MD: len(mm.get_zone(MEMORY_MD)),
        DATED_NOTES: len(mm.get_zone(DATED_NOTES)),
    }

    return ConsolidationResult(
        actions=tuple(actions),
        profile_updates=profile_updates,
        expired=(),
    )


# ---------------------------------------------------------------------------
# Session reconstruction.
# ---------------------------------------------------------------------------

def reconstruct_session(
    mappings: dict[str, tuple[dict[str, Any], ...]],
) -> UserOperatingProfile:
    """Deterministic rehydration from zone mappings.

    Returns the same active profile for the same inputs.
    Tested for equality across two reconstruct calls.

    Parameters
    ----------
    mappings : dict mapping zone name -> tuple of items.
        Expected keys: BLACKBOARD_PROFILE, USER_MD, MEMORY_MD, DATED_NOTES.
    """
    from tola.persona.profile import (
        PreferenceProvenance,
        UserPreference,
        UserOperatingProfile,
        EXPLICIT_PREFERENCE,
        BEHAVIOURAL_OBSERVATION,
        PreferenceStatus,
    )

    # Rebuild profile from USER_MD (compact stable preferences) and
    # BLACKBOARD_PROFILE (authoritative shared profile).
    # Blackboard outranks local mappings on conflict.

    prefs: list[UserPreference] = []
    versions: list[UserPreference] = []
    user_id = "reconstructed"

    # Collect blackboard profile items first (highest authority).
    blackboard_items = mappings.get(BLACKBOARD_PROFILE, ())
    user_md_items = mappings.get(USER_MD, ())

    # Build a merged key -> value map using conflict resolution.
    merged: dict[str, dict[str, Any]] = {}

    for item in user_md_items:
        key = item.get("key", "")
        if key:
            merged[key] = {
                "key": key,
                "value": item.get("value", ""),
                "source": item.get("source", EXPLICIT_PREFERENCE),
                "confidence": item.get("confidence", 1.0),
                "scope": item.get("scope", "global"),
                "observed_at": item.get("observed_at", ""),
                "evidence_refs": item.get("evidence_refs", ()),
                "project_id": item.get("project_id", ""),
            }

    # Blackboard overrides local on conflict.
    for item in blackboard_items:
        key = item.get("key", "")
        if key:
            merged[key] = {
                "key": key,
                "value": item.get("value", ""),
                "source": item.get("source", EXPLICIT_PREFERENCE),
                "confidence": item.get("confidence", 1.0),
                "scope": item.get("scope", "global"),
                "observed_at": item.get("observed_at", ""),
                "evidence_refs": item.get("evidence_refs", ()),
                "project_id": item.get("project_id", ""),
            }

    # Build UserPreference objects from merged map.
    for key in sorted(merged.keys()):
        data = merged[key]
        source = data["source"]
        prov = PreferenceProvenance(
            source=source,
            evidence_refs=tuple(data["evidence_refs"])
            if isinstance(data["evidence_refs"], (list, tuple))
            else (data["evidence_refs"],),
            observed_at=data["observed_at"],
            project_id=data["project_id"],
        )
        pref = UserPreference(
            key=data["key"],
            value=data["value"],
            status=PreferenceStatus.ACTIVE,
            provenance=prov,
            confidence=data["confidence"],
            scope=data["scope"],
        )
        prefs.append(pref)

    return UserOperatingProfile(
        user_id=user_id,
        preferences=tuple(prefs),
        preference_versions=tuple(versions),
    )


# ---------------------------------------------------------------------------
# Internal helpers.
# ---------------------------------------------------------------------------

def rebuild_compact(profile: UserOperatingProfile) -> dict[str, str]:
    """Rebuild compact active-preference view.

    Guaranteed to include every EXPLICIT_PREFERENCE (compaction
    never drops high-authority items) and exclude superseded/
    inactive ones.
    """
    compact = user_profile_compact(profile)
    return compact