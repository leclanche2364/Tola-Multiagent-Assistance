# MemoryMap model -- four zones as named constants.
# Plain ASCII. Stdlib only. Deterministic. No file I/O.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Zone constants -- authoritative placement.
# ---------------------------------------------------------------------------

BLACKBOARD_PROFILE = "BLACKBOARD_PROFILE"
USER_MD = "USER_MD"
MEMORY_MD = "MEMORY_MD"
DATED_NOTES = "DATED_NOTES"

ALL_ZONES = (BLACKBOARD_PROFILE, USER_MD, MEMORY_MD, DATED_NOTES)


# ---------------------------------------------------------------------------
# Placement rules (pure constants, no I/O).
# ---------------------------------------------------------------------------

# Items that belong in each zone by content type.
ZONE_CONTENT_TYPES = {
    BLACKBOARD_PROFILE: {"shared_profile", "operating_profile"},
    USER_MD: {"stable_preference", "compact_preference", "explicit_preference"},
    MEMORY_MD: {"durable_lesson", "durable_decision", "tola_lesson"},
    DATED_NOTES: {"recent_observation", "dated_note", "temporal_observation"},
}

# Types that are FORBIDDEN in each zone (rejection rules).
ZONE_FORBIDDEN = {
    MEMORY_MD: {"recent_observation", "dated_note", "temporal_observation"},
    DATED_NOTES: {"durable_lesson", "durable_decision", "tola_lesson"},
    USER_MD: {"recent_observation", "dated_note", "temporal_observation"},
    BLACKBOARD_PROFILE: {"recent_observation", "dated_note", "temporal_observation"},
}


class MemoryMap:
    """In-memory mapping of content items to consolidation zones.

    No file I/O. Operates on supplied content structures only.
    All methods are deterministic and pure.
    """

    def __init__(self) -> None:
        # zone -> list of items (dicts with at least a 'type' key).
        self._zones: dict[str, list[dict[str, Any]]] = {
            zone: [] for zone in ALL_ZONES
        }

    # ------------------------------------------------------------------
    # Core placement
    # ------------------------------------------------------------------

    def map_content(self, zone: str, items: list[dict[str, Any]]) -> list[str]:
        """Place items into a zone, validating placement rules.

        Returns a list of rejection messages (empty if all accepted).

        Placement rules:
          - A recent observation placed in MEMORY.md is rejected.
          - A durable lesson placed in dated notes is flagged.
          - Items with a type forbidden in the target zone are rejected.
        """
        if zone not in ALL_ZONES:
            return [f"Unknown zone: {zone!r}"]

        rejections: list[str] = []
        for item in items:
            item_type = item.get("type", "")
            # Check forbidden types for this zone.
            forbidden = ZONE_FORBIDDEN.get(zone, set())
            if item_type in forbidden:
                rejections.append(
                    f"Rejected: {item_type!r} cannot be placed in {zone}."
                )
                continue
            # Check that the type is recognised for the zone.
            allowed = ZONE_CONTENT_TYPES.get(zone, set())
            if item_type and item_type not in allowed and item_type not in forbidden:
                # Unrecognised type: allow but flag.
                rejections.append(
                    f"Warning: {item_type!r} is not a standard type for zone {zone}."
                )
            self._zones[zone].append(item)
        return rejections

    def get_zone(self, zone: str) -> tuple[dict[str, Any], ...]:
        """Return items in a zone as a frozen tuple."""
        if zone not in ALL_ZONES:
            return ()
        return tuple(self._zones[zone])

    def get_all(self) -> dict[str, tuple[dict[str, Any], ...]]:
        """Return all zones as a dict of zone -> tuple of items."""
        return {zone: self.get_zone(zone) for zone in ALL_ZONES}

    # ------------------------------------------------------------------
    # Conflict resolution helpers
    # ------------------------------------------------------------------

    @staticmethod
    def resolve_conflict(
        blackboard_item: dict[str, Any] | None,
        local_item: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Resolve a conflict between blackboard and local mappings.

        Blackboard profile outranks local mappings (BLACKBOARD_PROFILE wins).
        If blackboard_item is present, it wins. Otherwise local_item is used.
        """
        if blackboard_item is not None:
            return blackboard_item
        return local_item

    @staticmethod
    def validate_placement(zone: str, item_type: str) -> bool:
        """Return True if item_type is allowed in zone."""
        forbidden = ZONE_FORBIDDEN.get(zone, set())
        return item_type not in forbidden


# ---------------------------------------------------------------------------
# Determinism helper: sort items by a stable key for reproducible ordering.
# ---------------------------------------------------------------------------

def _stable_sort_key(item: dict[str, Any]) -> tuple:
    """Sort key for deterministic ordering of mapped items."""
    return (
        item.get("type", ""),
        item.get("key", ""),
        item.get("zone", ""),
        item.get("observed_at", ""),
    )