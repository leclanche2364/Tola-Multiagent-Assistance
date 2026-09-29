"""DelegationTracker -- register delegations and record events.

Batch T12 -- Delegation Monitoring and Follow-Through.
Stdlib only.  Plain ASCII.  Deterministic: timestamps are inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from tola.delegation.protocol import DelegationStatus


# ---------------------------------------------------------------------------
# Event enum (T12 tracking events)
# ---------------------------------------------------------------------------

class TrackingEvent(str, Enum):
    """Events that can be recorded against a delegation."""

    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PROGRESS_NOTED = "PROGRESS_NOTED"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Valid transitions derived from the T5 status machine
# ---------------------------------------------------------------------------

# Each status maps to the set of events that are valid FROM that status.
# Events drive the next status; invalid transitions raise ValueError.
_VALID_TRANSITIONS: dict[DelegationStatus, dict[TrackingEvent, DelegationStatus]] = {
    DelegationStatus.DRAFTED: {
        TrackingEvent.ASSIGNED: DelegationStatus.COMMITTED,
    },
    DelegationStatus.COMMITTED: {
        TrackingEvent.ACKNOWLEDGED: DelegationStatus.IN_PROGRESS,
        TrackingEvent.CANCELLED: DelegationStatus.CANCELLED,
    },
    DelegationStatus.IN_PROGRESS: {
        TrackingEvent.ACKNOWLEDGED: DelegationStatus.IN_PROGRESS,
        TrackingEvent.PROGRESS_NOTED: DelegationStatus.IN_PROGRESS,
        TrackingEvent.RESULT_RECEIVED: DelegationStatus.RESULT_RECEIVED,
        TrackingEvent.CANCELLED: DelegationStatus.CANCELLED,
    },
    DelegationStatus.RESULT_RECEIVED: {
        TrackingEvent.RESULT_RECEIVED: DelegationStatus.RESULT_RECEIVED,
        TrackingEvent.ACCEPTED: DelegationStatus.ACCEPTED,
        TrackingEvent.REJECTED: DelegationStatus.REJECTED,
        TrackingEvent.CANCELLED: DelegationStatus.CANCELLED,
    },
    DelegationStatus.ACCEPTED: {},
    DelegationStatus.REJECTED: {},
    DelegationStatus.CANCELLED: {},
    DelegationStatus.FUTURE_DEPENDENCY: {},
    DelegationStatus.AWAITING_CAPACITY: {},
    DelegationStatus.DECIDED: {},
}


# ---------------------------------------------------------------------------
# Tracking entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrackingEntry:
    """Immutable record of one delegation's tracking state."""

    delegation_id: str
    status: DelegationStatus
    event_history: list[tuple[TrackingEvent, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DelegationTracker
# ---------------------------------------------------------------------------

class DelegationTracker:
    """Tracks delegations through acknowledgement, progress, and completion.

    Deterministic: timestamps are inputs, never read from the clock.
    Invalid state transitions raise ValueError; history is never silently
    rewritten.
    """

    def __init__(self) -> None:
        self._entries: dict[str, TrackingEntry] = {}

    # -- write --------------------------------------------------------

    def register_delegation(
        self,
        delegation: object,
    ) -> TrackingEntry:
        """Register a delegation and return the initial tracking entry.

        *delegation* must have a ``delegation_id`` attribute and a
        ``status`` attribute (a DelegationStatus enum value).
        The initial event is ASSIGNED at the delegation's
        ``requested_at`` timestamp (or ``created_at`` if that key
        is absent from timestamps).
        """
        delegation_id = getattr(delegation, "delegation_id", str(id(delegation)))
        status = getattr(delegation, "status", DelegationStatus.DRAFTED)
        timestamps = getattr(delegation, "timestamps", {})
        ts = timestamps.get("requested_at") or timestamps.get("created_at") or ""

        entry = TrackingEntry(
            delegation_id=delegation_id,
            status=status,
            event_history=[(TrackingEvent.ASSIGNED, ts)],
        )
        self._entries[delegation_id] = entry
        return entry

    def record_event(
        self,
        delegation_id: str,
        event: TrackingEvent,
        timestamp: str,
    ) -> TrackingEntry:
        """Record an event against a delegation.

        Raises ValueError if the delegation is unknown or the
        transition is invalid for the current status.
        """
        if delegation_id not in self._entries:
            raise ValueError(
                f"Unknown delegation_id '{delegation_id}': cannot record event."
            )
        entry = self._entries[delegation_id]
        valid = _VALID_TRANSITIONS.get(entry.status, {})
        if event not in valid:
            raise ValueError(
                f"Invalid transition: status={entry.status.value}, "
                f"event={event.value}"
            )
        new_status = valid[event]
        updated = TrackingEntry(
            delegation_id=delegation_id,
            status=new_status,
            event_history=entry.event_history + [(event, timestamp)],
        )
        self._entries[delegation_id] = updated
        return updated

    # -- read --------------------------------------------------------

    def status(self, delegation_id: str) -> TrackingEntry:
        """Return the current tracking entry for *delegation_id*.

        Raises ValueError if the delegation is unknown.
        """
        if delegation_id not in self._entries:
            raise ValueError(f"Unknown delegation_id '{delegation_id}'.")
        return self._entries[delegation_id]

    def all_entries(self) -> list[TrackingEntry]:
        """Return a copy of all tracking entries."""
        return list(self._entries.values())

    def count(self) -> int:
        """Return the number of tracked delegations."""
        return len(self._entries)