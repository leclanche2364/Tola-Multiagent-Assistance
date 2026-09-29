"""Delegation escalation paths.

Batch T5 -- Delegation and Task Protocol.
Stdlib only.  Plain ASCII.  Deterministic: timestamps are inputs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from tola.delegation.protocol import (
    DelegationRecord,
    DelegationStatus,
    DelegationLedger,
)
from tola.registry.boundaries import BoundaryViolation
from tola.registry.availability import (
    DelegationBlockedError,
    FUTURE_SPECIALIST_DEPENDENCY,
    record_future_specialist_dependency,
    route_marketing_work,
    validate_marketing_activation,
)

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

STALLED_DELEGATION_DAYS_THRESHOLD = 5


# ---------------------------------------------------------------------------
# Escalation: boundary violation
# ---------------------------------------------------------------------------

def escalate_boundary_violation(
    delegation: DelegationRecord,
    violation_reason: str,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Escalate a delegation that violated a specialist boundary.

    Updates the record status to REJECTED and records the
    escalation reason.  The boundary violation is not suppressed.
    """
    escalation_reason = (
        f"Boundary violation escalated: {violation_reason}. "
        f"Delegation {delegation.delegation_id} to specialist "
        f"'{delegation.specialist}' in domain '{delegation.domain}' "
        f"rejected at {timestamps.get('now', 'unknown')}."
    )

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.REJECTED,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=escalation_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# Escalation: rejected result (with re-delegation option)
# ---------------------------------------------------------------------------

def escalate_rejected_result(
    delegation: DelegationRecord,
    rejection_reason: str,
    re_delegate: bool = False,
    new_specialist: Optional[str] = None,
    ledger: Optional[DelegationLedger] = None,
    timestamps: dict = None,
) -> DelegationRecord:
    """Handle a rejected specialist result.

    If *re_delegate* is True and *ledger* and *new_specialist* are
    provided, creates a new draft delegation for the same task.
    Otherwise marks the original as REJECTED with the reason.
    """
    ts = timestamps or {}

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.REJECTED,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=rejection_reason,
        timestamps={**delegation.timestamps, **ts},
        escalation_reason=rejection_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)

    if re_delegate and ledger is not None and new_specialist is not None:
        new_id = f"{delegation.delegation_id}-redelegate-1"
        new_ts = {**ts, "redelegation_at": ts.get("now", "unknown")}
        new_record = DelegationRecord(
            delegation_id=new_id,
            specialist=new_specialist,
            task_description=delegation.task_description,
            domain=delegation.domain,
            status=DelegationStatus.DRAFTED,
            priority=delegation.priority,
            timestamps=new_ts,
            re_delegation_count=delegation.re_delegation_count + 1,
        )
        ledger.create(new_record)
        return new_record

    return updated


# ---------------------------------------------------------------------------
# Escalation: stalled delegation (no result after N days)
# ---------------------------------------------------------------------------

def escalate_stalled_delegation(
    delegation: DelegationRecord,
    days_without_result: int,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Detect and escalate a stalled delegation.

    If *days_without_result* exceeds STALLED_DELEGATION_DAYS_THRESHOLD,
    the delegation is marked REJECTED with a stalled escalation reason.
    """
    if days_without_result < STALLED_DELEGATION_DAYS_THRESHOLD:
        # Not yet stalled; return unchanged.
        return delegation

    escalation_reason = (
        f"Delegation {delegation.delegation_id} stalled: "
        f"{days_without_result} days without result, "
        f"exceeding threshold of {STALLED_DELEGATION_DAYS_THRESHOLD} days. "
        f"Escalated at {timestamps.get('now', 'unknown')}."
    )

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=delegation.specialist,
        task_description=delegation.task_description,
        domain=delegation.domain,
        status=DelegationStatus.REJECTED,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=delegation.tola_decision,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=escalation_reason,
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason=escalation_reason,
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated


# ---------------------------------------------------------------------------
# FUTURE_SPECIALIST_DEPENDENCY handling via T4 registry
# ---------------------------------------------------------------------------

def handle_future_specialist_dependency(
    delegation: DelegationRecord,
    task_description: str,
    required_domain: str,
    intended_agent_id: str,
    ledger: DelegationLedger,
    timestamps: dict,
) -> DelegationRecord:
    """Handle work that requires a future specialist not yet available.

    Uses the T4 registry (route_marketing_work / FutureSpecialistDependency)
    to record the dependency without faking execution.  The delegation
    status becomes FUTURE_DEPENDENCY.
    """
    # Use T4 registry to create the dependency record.
    dep = record_future_specialist_dependency(
        work_description=task_description,
        required_domain=required_domain,
        intended_agent_id=intended_agent_id,
        reason=(
            f"Task requires {intended_agent_id} which is not yet ACTIVE. "
            f"Work deferred until activation prerequisites are met."
        ),
    )

    # Also run through the marketing routing gate for consistency.
    routing = route_marketing_work(task_description)

    decision_record = {
        "delegation_id": delegation.delegation_id,
        "decision": "FUTURE_DEPENDENCY",
        "reasoning": (
            f"Task requires {intended_agent_id} in domain "
            f"'{required_domain}'. Agent is FUTURE_NOT_AVAILABLE. "
            f"Dependency recorded: {dep.work_description}. "
            f"Routing check: {routing['record_type']}. "
            f"Never faking execution."
        ),
        "timestamps": timestamps,
    }

    updated = DelegationRecord(
        delegation_id=delegation.delegation_id,
        specialist=intended_agent_id,
        task_description=task_description,
        domain=required_domain,
        status=DelegationStatus.FUTURE_DEPENDENCY,
        priority=delegation.priority,
        capacity_query=delegation.capacity_query,
        capacity_report=delegation.capacity_report,
        tola_decision=decision_record,
        success_criteria=delegation.success_criteria,
        result=delegation.result,
        acceptance_reason=(
            f"Deferred as FUTURE_SPECIALIST_DEPENDENCY: "
            f"{dep.reason}"
        ),
        timestamps={**delegation.timestamps, **timestamps},
        escalation_reason="FUTURE_SPECIALIST_DEPENDENCY",
        re_delegation_count=delegation.re_delegation_count,
    )
    ledger.create(updated)
    return updated