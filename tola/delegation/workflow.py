"""Delegation workflow: the full request-to-acceptance loop.

Batch T5 -- Delegation and Task Protocol.
Stdlib only.  Plain ASCII.  Deterministic: timestamps are inputs.
"""

from __future__ import annotations

from typing import Callable, Optional

from tola.delegation.protocol import (
    DelegationRecord,
    DelegationStatus,
    DelegationLedger,
)
from tola.registry.capability import agent_capability_match
from tola.registry.boundaries import enforce_boundary
from tola.registry.availability import (
    DelegationBlockedError,
    check_delegation_allowed,
    FUTURE_SPECIALIST_DEPENDENCY,
    route_marketing_work,
)


# ---------------------------------------------------------------------------
# Protocol invariant error
# ---------------------------------------------------------------------------

class ProtocolInvariantError(RuntimeError):
    """Raised when a protocol step is skipped or performed out of order."""


# ---------------------------------------------------------------------------
# Step 1: delegation_request -- builds a draft record
# ---------------------------------------------------------------------------

def delegation_request(
    task_description: str,
    domain: str,
    priority: str,
    sources: dict,
    ledger: DelegationLedger,
    delegation_id: str,
    timestamps: dict,
) -> DelegationRecord:
    """Create a draft DelegationRecord and append it to the ledger.

    Routes the task to a specialist via agent_capability_match.
    Returns the draft record with status DRAFTED.
    """
    routing = agent_capability_match(task_description)
    specialist = routing["agent_id"]

    record = DelegationRecord(
        delegation_id=delegation_id,
        specialist=specialist if specialist is not None else "unassigned",
        task_description=task_description,
        domain=domain,
        status=DelegationStatus.DRAFTED,
        priority=priority,
        timestamps=timestamps,
    )
    ledger.create(record)
    return record


# ---------------------------------------------------------------------------
# Step 2: run_capacity_query -- calls an injected capacity client
# ---------------------------------------------------------------------------

def run_capacity_query(
    delegation: DelegationRecord,
    capacity_client: Callable[[DelegationRecord], dict],
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Call the injected capacity client and update the record.

    *capacity_client* is a callable (or dict with a '__call__' key)
    that accepts a DelegationRecord and returns a capacity report dict.
    No I/O is performed inside this function.

    Updates status to AWAITING_CAPACITY, then after the query
    stores the capacity_query and status AWAITING_CAPACITY.
    """
    # Record that a capacity query was issued.
    query_record = {
        "delegation_id": delegation.delegation_id,
        "specialist": delegation.specialist,
        "domain": delegation.domain,
        "query_type": "CAPACITY_QUERY",
        "timestamps": timestamps,
    }

    # Call the injected client.
    report = capacity_client(delegation)

    # Build updated record with capacity query + report.
    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.AWAITING_CAPACITY,
        priority=delegation.priority,
        capacity_query=query_record,
        capacity_report=report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=delegation.acceptance_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=delegation.escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# Step 3: apply_capacity_report -- stores the report on the record
# ---------------------------------------------------------------------------

def apply_capacity_report(
    delegation: DelegationRecord,
    report: dict,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Apply a capacity report to the delegation record.

    Replaces any existing capacity_report and updates status.
    """
    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.AWAITING_CAPACITY,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=delegation.acceptance_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=delegation.escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# Step 4: tola_decide -- records Tola's delegation decision
# ---------------------------------------------------------------------------

def tola_decide(
    delegation: DelegationRecord,
    decision: str,
    reasoning: str,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Record Tola's decision and reasoning on the delegation.

    *decision* is a string such as 'COMMIT', 'DEFER', 'REJECT',
    or 'FUTURE_DEPENDENCY'.
    """
    decision_record = {
        "delegation_id": delegation.delegation_id,
        "decision": decision,
        "reasoning": reasoning,
        "timestamps": timestamps,
    }

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.DECIDED,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=decision_record,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=delegation.acceptance_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=delegation.escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# Step 5: commit_task -- requires decision + success criteria + boundary
# ---------------------------------------------------------------------------

def commit_task(
    delegation: DelegationRecord,
    success_criteria: list,
    boundary_check_result: dict,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Commit a delegated task.

    Protocol invariant: commit without a capacity report and a
    Tola decision must raise ProtocolInvariantError (no skipping
    steps).

    Also enforces:
      - boundary_check_result must show allowed=True.
      - delegation to non-ACTIVE agents is blocked.
    """
    # Protocol invariant: capacity report and decision must exist.
    if delegation.capacity_report is None:
        raise ProtocolInvariantError(
            "Cannot commit: capacity report is missing. "
            "Run CAPACITY_QUERY/CAPACITY_REPORT first."
        )
    if delegation.tola_decision is None:
        raise ProtocolInvariantError(
            "Cannot commit: Tola decision is missing. "
            "Run tola_decide first."
        )

    # Boundary check enforcement.
    if not boundary_check_result.get("allowed", False):
        raise ProtocolInvariantError(
            f"Cannot commit: boundary check failed: "
            f"{boundary_check_result.get('reason', 'unknown')}"
        )

    # Delegation to non-ACTIVE agents is blocked (T4-10).
    check_delegation_allowed(delegation.specialist)

    # Enforce the boundary via enforce_boundary (raises on violation).
    enforce_boundary(delegation.specialist, "delegated_task_commit")

    commit_record = {
        "delegation_id": delegation.delegation_id,
        "success_criteria": success_criteria,
        "boundary_check": boundary_check_result,
        "timestamps": timestamps,
    }

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.COMMITTED,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=delegation.tola_decision,
        success_criteria=success_criteria,
        result=delegation.result,
        acceptance_reason=delegation.acceptance_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=delegation.escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# Step 6: record_result -- records the specialist's result
# ---------------------------------------------------------------------------

def record_result(
    delegation: DelegationRecord,
    result: dict,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Record the result returned by the specialist.

    *result* must be a dict containing at minimum a 'status' key
    (e.g. 'SUCCESS', 'PARTIAL', 'FAILURE', 'BLOCKED').
    """
    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.RESULT_RECEIVED,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=result,
        acceptance_reason=delegation.acceptance_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=delegation.escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# Step 7: accept_or_reject -- final verdict
# ---------------------------------------------------------------------------

def accept_or_reject(
    delegation: DelegationRecord,
    verdict: str,
    reasoning: str,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Accept or reject the specialist result.

    *verdict* must be 'ACCEPT' or 'REJECT'.
    A result must be recorded before acceptance/rejection.
    """
    if delegation.result is None:
        raise ProtocolInvariantError(
            "Cannot accept or reject: no result has been recorded yet."
        )

    if verdict not in ("ACCEPT", "REJECT"):
        raise ProtocolInvariantError(
            f"Invalid verdict '{verdict}': must be 'ACCEPT' or 'REJECT'."
        )

    new_status = (
        DelegationStatus.ACCEPTED
        if verdict == "ACCEPT"
        else DelegationStatus.REJECTED
    )

    decision_record = {
        "delegation_id": delegation.delegation_id,
        "verdict": verdict,
        "reasoning": reasoning,
        "timestamps": timestamps,
    }

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=new_status,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=reasoning,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=delegation.escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated