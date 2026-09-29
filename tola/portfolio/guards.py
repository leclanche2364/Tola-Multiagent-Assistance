"""Guard functions for Batch T1 -- rejecting conversation-only facts as
authoritative operational state.

A conversation-only fact (source=SOURCE_CONVERSATION or missing provenance)
must never be treated as authoritative operational state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from tola.portfolio.contracts import Source


class GuardViolation(Exception):
    """Raised when a fact fails the authoritative-state guard."""


@dataclass(frozen=True)
class Provenance:
    source_system: str = ""
    source_id: str = ""
    fetched_at: Optional[datetime] = None
    source_version: str = ""


def reject_conversation_only(source: str) -> None:
    """Reject SOURCE_CONVERSATION as authoritative operational state.

    Raises GuardViolation if *source* equals SOURCE_CONVERSATION.
    """
    if source == Source.SOURCE_CONVERSATION.value:
        raise GuardViolation(
            "Conversation-only facts (source=conversation) must not be "
            "treated as authoritative operational state."
        )


def require_provenance(
    source_system: str,
    source_id: str,
    fetched_at: Optional[datetime] = None,
    source_version: str = "",
) -> None:
    """Reject entities with missing or empty provenance as authoritative.

    At minimum *source_system* and *source_id* must be non-empty strings.
    *fetched_at* must be a non-None datetime.  *source_version* must be
    non-empty.

    Raises GuardViolation if any provenance field is missing or empty.
    """
    missing: list[str] = []

    if not source_system or not source_system.strip():
        missing.append("source_system")
    if not source_id or not source_id.strip():
        missing.append("source_id")
    if fetched_at is None:
        missing.append("fetched_at")
    if not source_version or not source_version.strip():
        missing.append("source_version")

    if missing:
        raise GuardViolation(
            f"Missing or empty provenance fields: {', '.join(missing)}.  "
            f"Conversation-only facts or entities without full provenance "
            f"cannot be authoritative operational state."
        )


def guard_authoritative(entity_type: str, source: str, provenance: Provenance) -> None:
    """Full guard: reject conversation-only or unprovenanced facts.

    Checks both the source enum value and the full provenance block.
    Raises GuardViolation on any failure.
    """
    reject_conversation_only(source)
    require_provenance(
        source_system=provenance.source_system,
        source_id=provenance.source_id,
        fetched_at=provenance.fetched_at,
        source_version=provenance.source_version,
    )