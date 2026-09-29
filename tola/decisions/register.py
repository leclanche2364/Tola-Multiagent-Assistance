# Decision Register for Batch T15.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


REQUIRED_FIELDS = (
    "decision",
    "reason",
    "evidence",
    "alternatives",
    "tradeoff",
    "owner",
    "date",
    "expected_outcome",
)

OPTIONAL_FIELDS = (
    "review_date",
    "revisit_trigger",
)


@dataclass(frozen=True)
class DecisionRecord:
    decision: str
    reason: str
    evidence: str
    alternatives: str
    tradeoff: str
    owner: str
    date: str
    expected_outcome: str
    review_date: Optional[str] = None
    revisit_trigger: Optional[Dict[str, Any]] = None
    superseded_by: Optional[str] = None
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(self, "id", self._generate_id())

    def _generate_id(self) -> str:
        parts = [self.date, self.owner, self.decision[:40]]
        raw = "|".join(parts)
        h = 0
        for ch in raw:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return f"DEC-{h:08X}"

    def is_superseded(self) -> bool:
        return self.superseded_by is not None


def register_decision(record: DecisionRecord) -> DecisionRecord:
    for field_name in REQUIRED_FIELDS:
        value = getattr(record, field_name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValueError(f"Missing required field: {field_name}")
    if isinstance(record.evidence, str) and record.evidence.strip() == "":
        raise ValueError("Evidence must be non-empty")
    return record


def supersede_decision(
    register: Dict[str, DecisionRecord],
    old_id: str,
    new_record: DecisionRecord,
) -> DecisionRecord:
    if old_id not in register:
        raise KeyError(f"Decision id not found: {old_id}")
    old = register[old_id]
    if old.is_superseded():
        raise ValueError(f"Decision already superseded: {old_id}")
    updated_old = old._replace(superseded_by=new_record.id)
    register[old_id] = updated_old
    register[new_record.id] = new_record
    return new_record


def get_decision(register: Dict[str, DecisionRecord], decision_id: str) -> DecisionRecord:
    return register[decision_id]


def list_decisions(register: Dict[str, DecisionRecord]) -> List[DecisionRecord]:
    return list(register.values())