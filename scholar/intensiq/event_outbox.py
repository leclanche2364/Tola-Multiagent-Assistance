"""
Batch S5 -- Durable Learning Event Outbox.
Immutable event store with cursor pagination and replay-safe retrieval.
Plain ASCII. Python 3 stdlib only.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from scholar.intensiq.contracts import EVENT_TYPES, LearningEvent


SCHEMA_VERSION = "1.0"


class EventOutbox:
    """Durable, replay-safe learning event outbox.

    Events are immutable once written. Cursor pagination uses event IDs
    so there is no loss or duplication across pages. Replay always
    returns prior events unchanged.
    """

    def __init__(self, clock: Optional[callable] = None) -> None:
        self._events: List[Dict[str, Any]] = []
        self._clock = clock or datetime.utcnow

    # ------------------------------------------------------------------ #
    #  Write
    # ------------------------------------------------------------------ #

    def append(
        self,
        event_type: str,
        aggregate_id: str,
        course_id: str,
        topic_id: str,
        payload: Any,
        schema_version: str = SCHEMA_VERSION,
        occurred_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append a new immutable event.

        Raises ValueError on:
        - unknown event_type
        - missing required fields
        - empty string for any required string field
        """
        if event_type not in EVENT_TYPES:
            raise ValueError(
                f"Unknown event_type: {event_type!r}. "
                f"Must be one of {sorted(EVENT_TYPES)}"
            )

        resolved_now = occurred_at or self._clock().isoformat()

        # Validate required string fields are non-empty
        for name, val in (
            ("event_type", event_type),
            ("aggregate_id", aggregate_id),
            ("course_id", course_id),
            ("topic_id", topic_id),
        ):
            if not isinstance(val, str) or not val.strip():
                raise ValueError(
                    f"{name} must be a non-empty string, got {val!r}"
                )

        event_id = str(uuid.uuid4())
        event: Dict[str, Any] = {
            "event_id": event_id,
            "event_type": event_type,
            "schema_version": schema_version,
            "occurred_at": resolved_now,
            "course_id": course_id,
            "topic_id": topic_id,
            "aggregate_id": aggregate_id,
            "payload": payload,
        }

        # Append-only: never overwrite
        self._events.append(event)
        return event

    # ------------------------------------------------------------------ #
    #  Read / Replay
    # ------------------------------------------------------------------ #

    def get(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Return a single event by ID, or None."""
        for ev in self._events:
            if ev["event_id"] == event_id:
                return ev
        return None

    def replay(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Return events after *cursor*, up to *limit*.

        Returns (events, next_cursor).
        - cursor=None  -> start from beginning
        - cursor=""    -> start from beginning (empty string treated as None)
        - next_cursor  -> event_id of the last returned event, or None
                          when there are no more events

        Raises ValueError if cursor is a non-empty string that does not
        match any known event_id.
        """
        if cursor is not None and cursor != "":
            # Validate cursor exists
            found = False
            for ev in self._events:
                if ev["event_id"] == cursor:
                    found = True
                    break
            if not found:
                raise ValueError(
                    f"Unknown cursor: {cursor!r}. "
                    "Cursor must match a previously returned event_id."
                )

        # Slice events after cursor
        if cursor and cursor != "":
            start_idx = None
            for i, ev in enumerate(self._events):
                if ev["event_id"] == cursor:
                    start_idx = i + 1
                    break
            slice_events = self._events[start_idx:]
        else:
            slice_events = list(self._events)

        # Apply limit
        if limit is not None:
            if not isinstance(limit, int) or limit < 1:
                raise ValueError(
                    f"limit must be a positive int, got {limit!r}"
                )
            slice_events = slice_events[:limit]

        # Determine next_cursor
        next_cursor = None
        if slice_events:
            next_cursor = slice_events[-1]["event_id"]

        return slice_events, next_cursor

    def count(self) -> int:
        """Return total number of stored events."""
        return len(self._events)

    # ------------------------------------------------------------------ #
    #  Mutation guard
    # ------------------------------------------------------------------ #

    def _reject_mutation(self, method_name: str) -> None:
        raise ValueError(
            f"Events are immutable. {method_name} is not allowed on "
            "a durable event outbox."
        )

    def update(self, event_id: str, **kwargs: Any) -> None:
        """Reject all mutation attempts."""
        self._reject_mutation("update")

    def delete(self, event_id: str) -> None:
        """Reject all deletion attempts."""
        self._reject_mutation("delete")

    def clear(self) -> None:
        """Reject all clear attempts."""
        self._reject_mutation("clear")

    # ------------------------------------------------------------------ #
    #  Bulk helpers for testing / recovery
    # ------------------------------------------------------------------ #

    def append_batch(
        self,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Append multiple events atomically (same clock, same batch).

        Each event dict must contain event_type, aggregate_id, course_id,
        topic_id, and optionally payload, schema_version, occurred_at.
        """
        results = []
        for ev in events:
            results.append(
                self.append(
                    event_type=ev["event_type"],
                    aggregate_id=ev["aggregate_id"],
                    course_id=ev["course_id"],
                    topic_id=ev["topic_id"],
                    payload=ev.get("payload"),
                    schema_version=ev.get("schema_version", SCHEMA_VERSION),
                    occurred_at=ev.get("occurred_at"),
                )
            )
        return results

    def all_events(self) -> List[Dict[str, Any]]:
        """Return a shallow copy of all events in insertion order."""
        return list(self._events)
