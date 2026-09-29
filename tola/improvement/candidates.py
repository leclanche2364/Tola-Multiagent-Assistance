"""Candidate promotion for T21 Improvement Ledger.

promote(observation) -> Candidate.
A Candidate must link to at least one underlying observation id
(LINK_MIN=1) and retain its evidence chain.
candidate_from(insufficient) raises ValueError.

A single observation only becomes a candidate when its kind warrants
it: corrections and failures qualify on their own; successes require
a pattern flag + MIN_PATTERN=3 supporting observations.

Plain ASCII. Stdlib only. No I/O. No clock reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tola.improvement.ledger import Observation


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LINK_MIN = 1
MIN_PATTERN = 3


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    """An improvement candidate linked to underlying observations."""

    id: str
    kind: str
    observation_ids: tuple[str, ...]
    evidence_refs: dict[str, Any]


# ---------------------------------------------------------------------------
# CandidateStore
# ---------------------------------------------------------------------------

class CandidateStore:
    """In-memory store of candidates built from observations."""

    def __init__(self) -> None:
        self._candidates: dict[str, Candidate] = {}

    def promote(
        self,
        observation: Observation,
        supporting: tuple[Observation, ...] = (),
    ) -> Candidate:
        """Promote an Observation (or group) to a Candidate.

        Delegates to candidate_from().  Raises ValueError if
        observations are insufficient (LINK_MIN=1 for corrections
        and failures; MIN_PATTERN=3 for reusable successes).
        """
        c = candidate_from(observation, supporting)
        self._candidates[c.id] = c
        return c

    def list_candidates(self) -> tuple[Candidate, ...]:
        return tuple(self._candidates.values())

    def get(self, candidate_id: str) -> Candidate | None:
        return self._candidates.get(candidate_id)

    def count(self) -> int:
        return len(self._candidates)


def candidate_from(
    observation: Observation,
    supporting: tuple[Observation, ...] = (),
) -> Candidate:
    """Build a Candidate from an observation, raising if insufficient.

    USER_CORRECTION and DELEGATION failures: require at least
    LINK_MIN=1 observation (the observation itself always qualifies).
    Reusable successes: require MIN_PATTERN=3 supporting observations.
    """
    kind = observation.kind
    payload = observation.evidence.get("event_payload", {})
    ctx = observation.evidence.get("context_refs", {})
    is_failure = payload.get("success") is False
    is_reusable_success = (
        kind == "DELEGATION"
        and payload.get("success") is True
        and ctx.get("reusable_pattern") is True
    )

    if kind == "USER_CORRECTION" or is_failure:
        return Candidate(
            id=observation.id,
            kind=kind,
            observation_ids=(observation.id,),
            evidence_refs=_merge_evidence(observation, supporting),
        )

    if is_reusable_success and len(supporting) + 1 >= MIN_PATTERN:
        return Candidate(
            id=observation.id,
            kind=kind,
            observation_ids=(observation.id,) + tuple(s.id for s in supporting),
            evidence_refs=_merge_evidence(observation, supporting),
        )

    raise ValueError(
        f"Insufficient observations for candidate: kind={kind!r}, "
        f"supporting={len(supporting)}, need LINK_MIN={LINK_MIN} "
        f"(corrections/failures) or MIN_PATTERN={MIN_PATTERN} (successes)"
    )


def _merge_evidence(
    primary: Observation,
    supporting: tuple[Observation, ...],
) -> dict[str, Any]:
    """Merge evidence from primary and supporting observations."""
    refs: dict[str, Any] = {
        "primary_event_payload": primary.evidence.get("event_payload", {}),
        "primary_context_refs": primary.evidence.get("context_refs", {}),
        "supporting_ids": tuple(s.id for s in supporting),
    }
    if supporting:
        refs["supporting_evidence"] = [s.evidence for s in supporting]
    return refs