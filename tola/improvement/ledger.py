"""ImprovementLedger -- pure in-memory store for T21.

Observe events and produce Observation objects or None.
Corrections and failures always produce observations.
Reusable success patterns may produce observations (opt-in flag).
One-off noise returns None.  Every observation retains root-cause
evidence verbatim.  Idempotency: duplicate observe() calls with the
same dedup key return the same Observation, not a duplicate.

Plain ASCII. Stdlib only. No I/O. No clock reads.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Event-kind constants (named, not magic strings)
# ---------------------------------------------------------------------------

USER_CORRECTION = "USER_CORRECTION"
DELEGATION = "DELEGATION"
BRIEFING = "BRIEFING"


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Observation:
    """A single learning observation with verbatim root-cause evidence."""

    id: str
    kind: str
    subject: str
    evidence: dict[str, Any]
    timestamp: str


# ---------------------------------------------------------------------------
# ImprovementLedger
# ---------------------------------------------------------------------------

class ImprovementLedger:
    """Pure in-memory observation store.

    observe(event, context) -> Observation | None.
    Rules are applied as named constants below.
    """

    def __init__(self) -> None:
        self._observations: dict[str, Observation] = {}

    # -- dedup helpers ------------------------------------------------------

    @staticmethod
    def _dedup_key(event_id: str, kind: str, subject: str) -> str:
        """Deterministic dedup key from event id + kind + subject."""
        raw = f"{event_id}|{kind}|{subject}"
        return hashlib.sha256(raw.encode("ascii")).hexdigest()

    # -- observation rules --------------------------------------------------

    def observe(
        self,
        event: dict[str, Any],
        context: dict[str, Any],
    ) -> Observation | None:
        """Apply T21 rules and store or return None.

        Rules:
          - USER_CORRECTION event -> always generates a learning observation.
          - DELEGATION event with success=False -> always generates an
            observation (failure is signal).
          - DELEGATION success with reusable-pattern flag in context ->
            may generate an observation (opt-in; returns observation when
            flag is truthy).
          - One-off noise (single success, no pattern flag, or trivial kinds
            like BRIEFING with no anomaly) -> returns None, never auto-becomes
            a candidate.
        """
        kind = event.get("kind", "")
        event_id = event.get("id", "")
        subject = event.get("subject", "")
        timestamp = context.get("timestamp", event.get("timestamp", ""))

        # USER_CORRECTION: always generates an observation.
        if kind == USER_CORRECTION:
            key = self._dedup_key(event_id, kind, subject)
            if key in self._observations:
                return self._observations[key]
            evidence = {
                "event_payload": dict(event),
                "context_refs": dict(context),
            }
            obs = Observation(
                id=key,
                kind=kind,
                subject=subject,
                evidence=evidence,
                timestamp=timestamp,
            )
            self._observations[key] = obs
            return obs

        # DELEGATION failure: always generates an observation.
        if kind == DELEGATION and event.get("success") is False:
            key = self._dedup_key(event_id, kind, subject)
            if key in self._observations:
                return self._observations[key]
            evidence = {
                "event_payload": dict(event),
                "context_refs": dict(context),
            }
            obs = Observation(
                id=key,
                kind=kind,
                subject=subject,
                evidence=evidence,
                timestamp=timestamp,
            )
            self._observations[key] = obs
            return obs

        # DELEGATION success with reusable-pattern flag -> may generate.
        if kind == DELEGATION and event.get("success") is True:
            if context.get("reusable_pattern") is True:
                key = self._dedup_key(event_id, kind, subject)
                if key in self._observations:
                    return self._observations[key]
                evidence = {
                    "event_payload": dict(event),
                    "context_refs": dict(context),
                }
                obs = Observation(
                    id=key,
                    kind=kind,
                    subject=subject,
                    evidence=evidence,
                    timestamp=timestamp,
                )
                self._observations[key] = obs
                return obs

        # One-off noise: BRIEFING with no anomaly, single success without
        # pattern flag, or any trivial kind -> returns None.
        return None

    # -- access -------------------------------------------------------------

    @property
    def observations(self) -> dict[str, Observation]:
        return dict(self._observations)

    def get(self, obs_id: str) -> Observation | None:
        return self._observations.get(obs_id)

    def count(self) -> int:
        return len(self._observations)