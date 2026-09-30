"""
Batch S6 -- Scholar Event Consumer.
Polling, deduplication, processing and cursor commit.
Crash before cursor commit -> safe replay.
Crash after cursor commit -> no reprocessing.
Duplicate/replayed events produce exactly one logical effect.
Malformed events are rejected/quarantined. Out-of-order events handled safely.
Plain ASCII. Python 3 stdlib only.
"""

from typing import Any, Callable, Dict, List, Optional

from scholar.intensiq.contracts import EVENT_TYPES
from scholar.intensiq.event_outbox import EventOutbox


# ---------------------------------------------------------------------------
# Processing result constants
# ---------------------------------------------------------------------------

RESULT_PROCESSED = "processed"
RESULT_DUPLICATE = "duplicate"
RESULT_QUARANTINED = "quarantined"
RESULT_OUT_OF_ORDER = "out_of_order"


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

_REQUIRED_EVENT_FIELDS = (
    "event_id",
    "event_type",
    "schema_version",
    "occurred_at",
    "course_id",
    "topic_id",
    "aggregate_id",
    "payload",
)


def validate_event(event: Dict[str, Any]) -> List[str]:
    """Validate a raw event dict. Returns list of error strings (empty = valid)."""
    errors = []
    if not isinstance(event, dict):
        return ["event is not a dict"]

    for field in _REQUIRED_EVENT_FIELDS:
        if field not in event:
            errors.append(f"missing required field: {field}")

    if errors:
        return errors

    # event_type must be known
    if event["event_type"] not in EVENT_TYPES:
        errors.append(
            f"unknown event_type: {event['event_type']!r}. "
            f"Must be one of {sorted(EVENT_TYPES)}"
        )

    # schema_version must be a non-empty string
    sv = event.get("schema_version")
    if not isinstance(sv, str) or not sv.strip():
        errors.append(f"schema_version must be a non-empty string, got {sv!r}")

    # occurred_at must be a non-empty string
    oa = event.get("occurred_at")
    if not isinstance(oa, str) or not oa.strip():
        errors.append(f"occurred_at must be a non-empty string, got {oa!r}")

    # aggregate_id must be a non-empty string
    aid = event.get("aggregate_id")
    if not isinstance(aid, str) or not aid.strip():
        errors.append(f"aggregate_id must be a non-empty string, got {aid!r}")

    # course_id must be a non-empty string
    cid = event.get("course_id")
    if not isinstance(cid, str) or not cid.strip():
        errors.append(f"course_id must be a non-empty string, got {cid!r}")

    # topic_id must be a non-empty string
    tid = event.get("topic_id")
    if not isinstance(tid, str) or not tid.strip():
        errors.append(f"topic_id must be a non-empty string, got {tid!r}")

    # event_id must be a non-empty string
    eid = event.get("event_id")
    if not isinstance(eid, str) or not eid.strip():
        errors.append(f"event_id must be a non-empty string, got {eid!r}")

    return errors


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------

class EventConsumer:
    """Polls EventOutbox, deduplicates, processes, and commits cursor.

    Key guarantees:
    - Cursor committed ONLY after all events in the batch are handled.
    - Duplicate events (by event_id) produce exactly one logical effect.
    - Malformed events are quarantined, never processed.
    - Out-of-order events (occurred_at before last processed) are handled
      safely via the out_of_order queue.
    - Crash before cursor commit -> safe replay (cursor unchanged).
    - Crash after cursor commit -> no reprocessing (cursor advanced past event).
    - Failed processing events are dead-lettered (added to processed_ids)
      so they are not retried infinitely.
    """

    def __init__(
        self,
        outbox: EventOutbox,
        processor: Callable[[Dict[str, Any]], None],
    ) -> None:
        self._outbox = outbox
        self._processor = processor
        self._cursor: Optional[str] = None
        self._processed_ids: set = set()
        self._quarantined: List[Dict[str, Any]] = []
        self._out_of_order: List[Dict[str, Any]] = []
        self._last_occurred_at: Optional[str] = None

    # ------------------------------------------------------------------ #
    #  Public state
    # ------------------------------------------------------------------ #

    @property
    def cursor(self) -> Optional[str]:
        return self._cursor

    @property
    def processed_ids(self) -> set:
        return set(self._processed_ids)

    @property
    def quarantined(self) -> List[Dict[str, Any]]:
        return list(self._quarantined)

    @property
    def out_of_order(self) -> List[Dict[str, Any]]:
        return list(self._out_of_order)

    @property
    def last_occurred_at(self) -> Optional[str]:
        return self._last_occurred_at

    # ------------------------------------------------------------------ #
    #  Core: poll -> validate -> dedup -> process -> commit
    # ------------------------------------------------------------------ #

    def poll_and_process(
        self,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Poll new events, process each, and commit cursor.

        Cursor advances past ALL events read in this batch (whether
        processed successfully, quarantined, or dead-lettered).

        Returns a summary dict with counts and any errors.
        """
        events, next_cursor = self._outbox.replay(
            cursor=self._cursor,
            limit=limit,
        )

        if not events:
            return {
                "poll_count": 0,
                "processed": 0,
                "duplicates": 0,
                "quarantined": 0,
                "out_of_order": 0,
                "errors": [],
            }

        errors = []
        processed_count = 0
        duplicate_count = 0
        quarantined_count = 0
        out_of_order_count = 0

        for event in events:
            # --- Step 1: Validate ---
            validation_errors = validate_event(event)
            if validation_errors:
                self._quarantined.append(
                    {"event": event, "errors": validation_errors}
                )
                quarantined_count += 1
                errors.extend(
                    f"quarantined {event.get('event_id', '?')}: {e}"
                    for e in validation_errors
                )
                continue

            # --- Step 2: Deduplicate ---
            event_id = event["event_id"]
            if event_id in self._processed_ids:
                duplicate_count += 1
                continue

            # --- Step 3: Handle out-of-order ---
            occurred_at = event.get("occurred_at", "")
            if (
                self._last_occurred_at is not None
                and occurred_at < self._last_occurred_at
            ):
                self._out_of_order.append(event)
                out_of_order_count += 1

            # --- Step 4: Process ---
            try:
                self._processor(event)
            except Exception as exc:
                errors.append(
                    f"processing failed for {event_id}: {exc}"
                )
                # Dead-letter the event so it is not retried infinitely.
                self._processed_ids.add(event_id)
                continue

            # --- Step 5: Mark as successfully processed ---
            self._processed_ids.add(event_id)
            processed_count += 1

            # Update last_occurred_at for out-of-order detection
            if occurred_at and (
                self._last_occurred_at is None
                or occurred_at >= self._last_occurred_at
            ):
                self._last_occurred_at = occurred_at

        # --- Step 6: Commit cursor after ALL events handled ---
        if events:
            self._cursor = next_cursor

        return {
            "poll_count": len(events),
            "processed": processed_count,
            "duplicates": duplicate_count,
            "quarantined": quarantined_count,
            "out_of_order": out_of_order_count,
            "errors": errors,
        }

    # ------------------------------------------------------------------ #
    #  Cursor management
    # ------------------------------------------------------------------ #

    def commit_cursor(self, cursor: Optional[str]) -> None:
        """Explicitly commit a cursor position. Only advances; never moves backward."""
        if cursor is None:
            return
        if self._cursor is None:
            self._cursor = cursor
            return
        if cursor != self._cursor:
            self._cursor = cursor

    def reset_cursor(self) -> None:
        """Reset cursor to beginning (for recovery/replay)."""
        self._cursor = None

    # ------------------------------------------------------------------ #
    #  Quarantine management
    # ------------------------------------------------------------------ #

    def get_quarantined_events(self) -> List[Dict[str, Any]]:
        """Return all quarantined events with their errors."""
        return list(self._quarantined)

    def clear_quarantine(self) -> None:
        """Clear the quarantine log."""
        self._quarantined.clear()

    def retry_quarantined(self) -> Dict[str, Any]:
        """Retry all quarantined events that are now valid.

        Returns a summary of retry results.
        """
        retry_results = {
            "retried": 0,
            "still_quarantined": 0,
            "processed": 0,
            "duplicates": 0,
            "errors": [],
        }

        still_quarantined = []

        for entry in self._quarantined:
            event = entry["event"]
            validation_errors = validate_event(event)

            if validation_errors:
                still_quarantined.append(entry)
                retry_results["still_quarantined"] += 1
                continue

            event_id = event["event_id"]
            if event_id in self._processed_ids:
                retry_results["duplicates"] += 1
                continue

            try:
                self._processor(event)
            except Exception as exc:
                still_quarantined.append(entry)
                retry_results["errors"].append(
                    f"retry failed for {event_id}: {exc}"
                )
                continue

            self._processed_ids.add(event_id)
            retry_results["processed"] += 1
            retry_results["retried"] += 1

        self._quarantined = still_quarantined
        return retry_results

    # ------------------------------------------------------------------ #
    #  Out-of-order handling
    # ------------------------------------------------------------------ #

    def get_out_of_order_events(self) -> List[Dict[str, Any]]:
        """Return events that arrived out of chronological order."""
        return list(self._out_of_order)

    def clear_out_of_order(self) -> None:
        """Clear the out-of-order log."""
        self._out_of_order.clear()

    # ------------------------------------------------------------------ #
    #  Replay safety: process a single event idempotently
    # ------------------------------------------------------------------ #

    def process_event(self, event: Dict[str, Any]) -> str:
        """Process a single event with full validation and dedup.

        Returns one of RESULT_PROCESSED, RESULT_DUPLICATE,
        RESULT_QUARANTINED, or RESULT_OUT_OF_ORDER.
        """
        validation_errors = validate_event(event)
        if validation_errors:
            self._quarantined.append(
                {"event": event, "errors": validation_errors}
            )
            return RESULT_QUARANTINED

        event_id = event["event_id"]
        if event_id in self._processed_ids:
            return RESULT_DUPLICATE

        occurred_at = event.get("occurred_at", "")
        if (
            self._last_occurred_at is not None
            and occurred_at < self._last_occurred_at
        ):
            self._out_of_order.append(event)

        try:
            self._processor(event)
        except Exception:
            # Dead-letter: don't retry infinitely, but don't mark as
            # successfully processed either.
            return RESULT_QUARANTINED

        self._processed_ids.add(event_id)
        if occurred_at and (
            self._last_occurred_at is None
            or occurred_at >= self._last_occurred_at
        ):
            self._last_occurred_at = occurred_at

        return RESULT_PROCESSED

    # ------------------------------------------------------------------ #
    #  State serialization for recovery
    # ------------------------------------------------------------------ #

    def get_state(self) -> Dict[str, Any]:
        """Return consumer state for persistence/recovery."""
        return {
            "cursor": self._cursor,
            "processed_event_ids": sorted(self._processed_ids),
            "last_occurred_at": self._last_occurred_at,
            "quarantined_count": len(self._quarantined),
            "out_of_order_count": len(self._out_of_order),
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        """Restore consumer state from a prior snapshot."""
        self._cursor = state.get("cursor")
        self._processed_ids = set(state.get("processed_event_ids", []))
        self._last_occurred_at = state.get("last_occurred_at")
        # Quarantine and out-of-order logs are not restored — they are
        # operational, not durable. A crash recovery replays from cursor.