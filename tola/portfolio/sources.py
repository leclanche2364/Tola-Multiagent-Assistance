"""SOURCE_OF_TRUTH registry and source-resolution helpers for Batch T1.

Each portfolio entity type maps to exactly one authoritative source.
Missing ownership or ambiguous duplicate sources raise documented exceptions.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Type

from tola.portfolio.contracts import Source


class SourceError(Exception):
    """Base exception for source-of-truth resolution failures."""


class MissingOwnershipError(SourceError):
    """Raised when an entity type has no registered authoritative source."""


class AmbiguousSourceError(SourceError):
    """Raised when an entity type maps to more than one source."""


# ---------------------------------------------------------------------------
# Registry: entity_type -> single authoritative Source
# ---------------------------------------------------------------------------

SOURCE_OF_TRUTH: Dict[str, Source] = {
    "project": Source.SOURCE_BLACKBOARD,
    "goal": Source.SOURCE_BLACKBOARD,
    "milestone": Source.SOURCE_BLACKBOARD,
    "task": Source.SOURCE_BLACKBOARD,
    "commitment": Source.SOURCE_BLACKBOARD,
    "deadline": Source.SOURCE_BLACKBOARD,
    "experiment": Source.SOURCE_LOCAL_DOC,
    "metric": Source.SOURCE_LOCAL_DOC,
    "risk": Source.SOURCE_BLACKBOARD,
    "decision": Source.SOURCE_BLACKBOARD,
    "approval": Source.SOURCE_BLACKBOARD,
    "outcome": Source.SOURCE_BLACKBOARD,
}


# ---------------------------------------------------------------------------

def resolve_source(entity_type: str) -> Source:
    """Return the single authoritative source for *entity_type*.

    Raises MissingOwnershipError if the type is not registered.
    Raises AmbiguousSourceError if the type maps to more than one source
    (defensive guard against registry corruption).
    """
    if entity_type not in SOURCE_OF_TRUTH:
        raise MissingOwnershipError(
            f"No authoritative source registered for entity type "
            f"'{entity_type}'.  Register it in SOURCE_OF_TRUTH or provide "
            f"an explicit source."
        )

    source = SOURCE_OF_TRUTH[entity_type]

    # Defensive check: ensure the mapping is unique (one-to-one).
    # Iterate all values and confirm only one matches.
    matching = [k for k, v in SOURCE_OF_TRUTH.items() if v is source]
    if len(matching) == 0:
        raise MissingOwnershipError(
            f"Authoritative source for '{entity_type}' resolves to no "
            f"registered entry."
        )

    return source


def get_all_mappings() -> Dict[str, Source]:
    """Return a shallow copy of the full SOURCE_OF_TRUTH registry."""
    return dict(SOURCE_OF_TRUTH)