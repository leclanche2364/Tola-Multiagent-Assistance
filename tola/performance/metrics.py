"""PerformanceMetrics ledger -- pure in-memory store, no I/O.

Batch T20 -- Tola Performance Model.
All timestamps are injected inputs; no clock reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Event-kind constants (named, not magic strings)
# ---------------------------------------------------------------------------

DELEGATION = "DELEGATION"
REVIEW = "REVIEW"
RECOVERY = "RECOVERY"
BRIEFING = "BRIEFING"
ESCALATION = "ESCALATION"
COST = "COST"
LATENCY = "LATENCY"
USER_CORRECTION = "USER_CORRECTION"

KNOWN_KINDS = frozenset({
    DELEGATION, REVIEW, RECOVERY, BRIEFING,
    ESCALATION, COST, LATENCY, USER_CORRECTION,
})


@dataclass(frozen=True)
class Event:
    kind: str
    payload: dict[str, Any]
    timestamp: str


# ---------------------------------------------------------------------------
# PerformanceMetrics -- ledger
# ---------------------------------------------------------------------------

class PerformanceMetrics:
    """Pure record store over in-memory lists."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    # -- recording ----------------------------------------------------------

    def record_event(self, kind: str, payload: dict[str, Any], timestamp: str) -> None:
        if kind not in KNOWN_KINDS:
            raise ValueError(f"Unknown event kind: {kind!r}")
        self._events.append(Event(kind=kind, payload=dict(payload), timestamp=timestamp))

    # -- access -------------------------------------------------------------

    @property
    def events(self) -> list[Event]:
        return list(self._events)

    def _events_of_kind(self, kind: str) -> list[Event]:
        return [e for e in self._events if e.kind == kind]

    # -- computed metrics ---------------------------------------------------

    def delegation_success_rate(self) -> float:
        """Fraction of DELEGATION events with payload['success'] == True."""
        delegations = self._events_of_kind(DELEGATION)
        if not delegations:
            return 0.0
        successes = sum(1 for e in delegations if e.payload.get("success") is True)
        return successes / len(delegations)

    def first_pass_completion(self) -> float:
        """Fraction of delegations completed without retry (zero retries)."""
        delegations = self._events_of_kind(DELEGATION)
        if not delegations:
            return 0.0
        no_retry = sum(1 for e in delegations if e.payload.get("retry_count", 0) == 0)
        return no_retry / len(delegations)

    def retry_count(self, delegation_id: str) -> int:
        """Exact retry count for a specific delegation id."""
        for e in self._events_of_kind(DELEGATION):
            if e.payload.get("delegation_id") == delegation_id:
                return int(e.payload.get("retry_count", 0))
        raise KeyError(f"No DELEGATION event for id {delegation_id!r}")

    def escalation_accuracy(self) -> dict[str, int]:
        """Return {'correct': n, 'incorrect': n} for ESCALATION events."""
        escalations = self._events_of_kind(ESCALATION)
        correct = sum(1 for e in escalations if e.payload.get("correct") is True)
        incorrect = sum(1 for e in escalations if e.payload.get("correct") is False)
        return {"correct": correct, "incorrect": incorrect}

    def trend(self, metric: str, start: str, end: str) -> list[Event]:
        """Return events of *metric* kind with start <= timestamp <= end (inclusive).

        Timestamps are strings compared lexicographically (ISO-8601).
        """
        matching = [e for e in self._events_of_kind(metric) if start <= e.timestamp <= end]
        return matching

    # -- cost / latency -----------------------------------------------------

    def cost_total(self) -> float:
        return sum(float(e.payload.get("amount", 0)) for e in self._events_of_kind(COST))

    def cost_average(self) -> float:
        costs = self._events_of_kind(COST)
        if not costs:
            return 0.0
        return self.cost_total() / len(costs)

    def latency_total_ms(self) -> float:
        return sum(float(e.payload.get("ms", 0)) for e in self._events_of_kind(LATENCY))

    def latency_average_ms(self) -> float:
        lats = self._events_of_kind(LATENCY)
        if not lats:
            return 0.0
        return self.latency_total_ms() / len(lats)

    def sample_count(self, kind: str) -> int:
        return len(self._events_of_kind(kind))