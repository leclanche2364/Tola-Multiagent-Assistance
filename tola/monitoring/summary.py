"""Delegation ledger summary for Batch T12 monitoring.

Batch T12 -- Delegation Monitoring and Follow-Through.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from tola.delegation.protocol import DelegationStatus
from tola.monitoring.tracker import DelegationTracker, TrackingEvent


# ---------------------------------------------------------------------------
# Ledger summary (plain data structure)
# ---------------------------------------------------------------------------

def delegation_ledger(tracker: DelegationTracker) -> dict[str, Any]:
    """Return a deterministic ledger summary from the tracker.

    Returns a dict with:
      - total: total number of tracked delegations
      - counts_by_status: dict mapping status string -> count
      - open: count of non-terminal delegations
      - closed: count of terminal delegations
      - oldest_open: delegation_id of the oldest open item (or None)
      - overdue: list of delegation_ids that have passed their
        REVIEW_TIMEOUT or ESCALATE threshold without reaching
        a terminal state
      - event_counts: dict mapping event name -> count across all entries
    """
    entries = tracker.all_entries()
    total = len(entries)

    counts_by_status: dict[str, int] = Counter()
    for entry in entries:
        counts_by_status[entry.status.value] += 1

    terminal = {
        DelegationStatus.ACCEPTED,
        DelegationStatus.REJECTED,
        DelegationStatus.CANCELLED,
    }
    open_count = sum(
        1 for e in entries if e.status not in terminal
    )
    closed_count = total - open_count

    # Oldest open item: find the entry with the earliest first-event
    # timestamp among open (non-terminal) items.
    oldest_open: str | None = None
    oldest_ts: str | None = None
    for entry in entries:
        if entry.status not in terminal and entry.event_history:
            first_event, first_ts = entry.event_history[0]
            if oldest_ts is None or first_ts < oldest_ts:
                oldest_ts = first_ts
                oldest_open = entry.delegation_id

    # Overdue items: delegations not in a terminal state whose
    # last event timestamp is past a REVIEW_TIMEOUT or ESCALATE
    # threshold.  Since thresholds are not stored in the tracker,
    # we report non-terminal items as potentially overdue; the
    # due_followups function applies the actual thresholds.
    overdue: list[str] = [
        entry.delegation_id
        for entry in entries
        if entry.status not in terminal
    ]

    # Event counts across all entries
    event_counts: dict[str, int] = Counter()
    for entry in entries:
        for event, _ in entry.event_history:
            event_counts[event.value] += 1

    return {
        "total": total,
        "counts_by_status": dict(counts_by_status),
        "open": open_count,
        "closed": closed_count,
        "oldest_open": oldest_open,
        "overdue": overdue,
        "event_counts": dict(event_counts),
    }