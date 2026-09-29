"""Delegation protocol: record dataclass, ledger, and status enum.

Batch T5 -- Delegation and Task Protocol.
Stdlib only.  Plain ASCII.  Deterministic: timestamps are inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------

class DelegationStatus(str, Enum):
    """Lifecycle states for a delegation record."""

    DRAFTED = "DRAFTED"
    AWAITING_CAPACITY = "AWAITING_CAPACITY"
    DECIDED = "DECIDED"
    COMMITTED = "COMMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FUTURE_DEPENDENCY = "FUTURE_DEPENDENCY"


# ---------------------------------------------------------------------------
# Delegation record (frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DelegationRecord:
    """Immutable record of one delegation through the full loop.

    All timestamps are explicit inputs (ISO date strings), never
    read from the system clock.  Deterministic.
    """

    delegation_id: str
    specialist: str
    task_description: str
    domain: str
    status: DelegationStatus
    priority: str
    capacity_query: Optional[dict] = None
    capacity_report: Optional[dict] = None
    tola_decision: Optional[dict] = None
    success_criteria: Optional[list] = None
    result: Optional[dict] = None
    acceptance_reason: Optional[str] = None
    timestamps: dict = field(default_factory=dict)
    escalation_reason: Optional[str] = None
    re_delegation_count: int = 0


# ---------------------------------------------------------------------------
# Delegation Ledger (append-only list store)
# ---------------------------------------------------------------------------

class DelegationLedger:
    """Append-only store for DelegationRecord instances."""

    def __init__(self) -> None:
        self._records: list[DelegationRecord] = []

    # -- write (append only) ----------------------------------------

    def create(self, record: DelegationRecord) -> DelegationRecord:
        """Append a new record and return it."""
        self._records.append(record)
        return record

    # -- read -------------------------------------------------------

    def query(
        self,
        delegation_id: Optional[str] = None,
        specialist: Optional[str] = None,
        status: Optional[DelegationStatus] = None,
        domain: Optional[str] = None,
    ) -> list[DelegationRecord]:
        """Filter records by the given fields.  All filters are AND."""
        results = list(self._records)
        if delegation_id is not None:
            results = [r for r in results if r.delegation_id == delegation_id]
        if specialist is not None:
            results = [r for r in results if r.specialist == specialist]
        if status is not None:
            results = [r for r in results if r.status == status]
        if domain is not None:
            results = [r for r in results if r.domain == domain]
        return results

    def all(self) -> list[DelegationRecord]:
        """Return a copy of all records."""
        return list(self._records)

    def count(self) -> int:
        """Return the number of records in the ledger."""
        return len(self._records)

    def get_by_id(self, delegation_id: str) -> Optional[DelegationRecord]:
        """Return the first record matching *delegation_id*, or None."""
        for r in self._records:
            if r.delegation_id == delegation_id:
                return r
        return None