# Consolidation rule constants and small validators.
# Plain ASCII. Stdlib only. Deterministic. No clock reads.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Recency and evidence windows (input values, no clock reads).
# ---------------------------------------------------------------------------

RECENCY_WINDOW_DAYS = 30
PROMOTION_EVIDENCE_WINDOW_DAYS = 7

# ---------------------------------------------------------------------------
# Conflict resolution order (highest to lowest authority).
# ---------------------------------------------------------------------------

CONFLICT_RESOLUTION_ORDER = (
    "EXPLICIT_PREFERENCE",       # explicit user input always wins
    "PROMOTED_OBSERVATION",      # promoted behavioural pattern
    "CANDIDATE",                 # unconfirmed behavioural observation
)

# ---------------------------------------------------------------------------
# Zone authority ordering (highest to lowest).
# ---------------------------------------------------------------------------

ZONE_AUTHORITY_ORDER = (
    "BLACKBOARD_PROFILE",   # authoritative shared profile
    "USER_MD",              # compact stable preferences
    "MEMORY_MD",            # durable lessons/decisions
    "DATED_NOTES",          # recent observations (lowest authority)
)


# ---------------------------------------------------------------------------
# Validators (pure, deterministic).
# ---------------------------------------------------------------------------

def validate_zone_placement(zone: str, item_type: str) -> bool:
    """Return True if item_type is allowed in zone.

    Recent observations must NOT go in MEMORY_MD.
    Durable lessons must NOT go in DATED_NOTES.
    """
    from tola.consolidation.mapper import ZONE_FORBIDDEN
    forbidden = ZONE_FORBIDDEN.get(zone, set())
    return item_type not in forbidden


def validate_conflict_resolution(
    blackboard_has_profile: bool,
    local_has_profile: bool,
) -> str:
    """Return the winning source label.

    Blackboard profile outranks local mappings.
    """
    if blackboard_has_profile:
        return "BLACKBOARD_PROFILE"
    if local_has_profile:
        return "LOCAL"
    return "NONE"


def validate_no_superseded_active(
    preferences: list[dict[str, Any]],
) -> bool:
    """Return True if no superseded preference is marked ACTIVE.

    Superseded items must have status SUPERSEDED or be in preference_versions.
    """
    for pref in preferences:
        status = pref.get("status", "")
        if status == "SUPERSEDED" and pref.get("active", False):
            return False
    return True


def validate_explicit_high_authority_included(
    compact: dict[str, str],
    explicit_prefs: list[UserPreference],
) -> bool:
    """Return True if every explicit high-authority preference is in compact."""
    for pref in explicit_prefs:
        key = pref.key
        if key and key not in compact:
            return False
    return True


def validate_recency_window(
    observed_at: str,
    now_iso: str,
    window_days: int = RECENCY_WINDOW_DAYS,
) -> bool:
    """Return True if observed_at is within window_days of now_iso.

    Both are ISO-8601 date strings (YYYY-MM-DD or full datetime).
    Deterministic: no clock reads, pure string/date arithmetic.
    """
    from datetime import date, datetime

    def _parse_iso(s: str) -> date:
        # Try full datetime first, then date-only.
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {s!r}")

    obs_date = _parse_iso(observed_at[:10] if "T" not in observed_at else observed_at[:10])
    now_date = _parse_iso(now_iso[:10] if "T" not in now_iso else now_iso[:10])
    delta = (now_date - obs_date).days
    return delta <= window_days


@dataclass(frozen=True)
class ConsolidationRules:
    """Immutable rule set for consolidation passes."""

    recency_window_days: int = RECENCY_WINDOW_DAYS
    promotion_evidence_window_days: int = PROMOTION_EVIDENCE_WINDOW_DAYS
    conflict_order: tuple[str, ...] = CONFLICT_RESOLUTION_ORDER
    zone_authority: tuple[str, ...] = ZONE_AUTHORITY_ORDER

    def is_recent(self, observed_at: str, now_iso: str) -> bool:
        return validate_recency_window(observed_at, now_iso, self.recency_window_days)

    def zone_wins(self, zone_a: str, zone_b: str) -> str:
        """Return the higher-authority zone."""
        try:
            idx_a = self.zone_authority.index(zone_a)
            idx_b = self.zone_authority.index(zone_b)
        except ValueError:
            return zone_a
        return zone_a if idx_a <= idx_b else zone_b