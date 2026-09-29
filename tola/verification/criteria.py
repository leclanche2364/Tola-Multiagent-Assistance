# SuccessCriteria -- named kind registry and criterion builder.
# Batch T13. Stdlib only. Plain ASCII. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CriterionKind(str, Enum):
    """Named kinds of success criteria.

    Unknown kinds are rejected at build time.
    """

    ARTIFACT_EXISTS = "ARTIFACT_EXISTS"
    FIELD_MATCH = "FIELD_MATCH"
    THRESHOLD_MET = "THRESHOLD_MET"
    CONFIRMATION_RECEIVED = "CONFIRMATION_RECEIVED"
    BOOLEAN_PROPERTY = "BOOLEAN_PROPERTY"


_KNOWN_KINDS: set[str] = {k.value for k in CriterionKind}


@dataclass(frozen=True)
class SuccessCriterion:
    """One success criterion built from a plan milestone or delegation brief."""

    criterion_id: str
    description: str
    kind: str
    check: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in _KNOWN_KINDS:
            raise ValueError(
                f"Unknown criterion kind '{self.kind}'. "
                f"Known kinds: {sorted(_KNOWN_KINDS)}"
            )


def build_criteria(
    raw: list[dict[str, Any]],
) -> list[SuccessCriterion]:
    """Build criteria from plan milestones (T6) or delegation briefs (T5).

    Each dict must contain criterion_id, description, kind, and optional check.
    Unknown kinds raise ValueError at build time.
    """
    criteria: list[SuccessCriterion] = []
    for item in raw:
        criteria.append(
            SuccessCriterion(
                criterion_id=str(item["criterion_id"]),
                description=str(item["description"]),
                kind=str(item["kind"]),
                check=dict(item.get("check", {})),
            )
        )
    return criteria
