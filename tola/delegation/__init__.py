"""Batch T5 -- Delegation and Task Protocol.

Provides the full specialist delegation loop:
  request -> CAPACITY_QUERY -> CAPACITY_REPORT -> Tola decision
  -> TASK_COMMITTED -> specialist work -> result -> acceptance/rejection.

Every step produces a record.  Stdlib only.  Plain ASCII.
Deterministic: timestamps are inputs, no clock reads in logic.
"""

from tola.delegation.protocol import (
    DelegationRecord,
    DelegationLedger,
    DelegationStatus,
)
from tola.delegation.workflow import (
    delegation_request,
    run_capacity_query,
    apply_capacity_report,
    tola_decide,
    commit_task,
    record_result,
    accept_or_reject,
)
from tola.delegation.escalation import (
    escalate_boundary_violation,
    escalate_rejected_result,
    escalate_stalled_delegation,
    handle_future_specialist_dependency,
    STALLED_DELEGATION_DAYS_THRESHOLD,
)

__all__ = [
    "DelegationRecord",
    "DelegationLedger",
    "DelegationStatus",
    "delegation_request",
    "run_capacity_query",
    "apply_capacity_report",
    "tola_decide",
    "commit_task",
    "record_result",
    "accept_or_reject",
    "escalate_boundary_violation",
    "escalate_rejected_result",
    "escalate_stalled_delegation",
    "handle_future_specialist_dependency",
    "STALLED_DELEGATION_DAYS_THRESHOLD",
]