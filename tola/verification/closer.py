# verify_and_close -- integrate T12 DelegationTracker.
# Batch T13. Stdlib only. Plain ASCII. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tola.verification.criteria import SuccessCriterion, build_criteria
from tola.verification.verifier import (
    VerificationOutcome,
    VerificationResult,
    verify_outcome,
)
from tola.monitoring.tracker import DelegationTracker, TrackingEvent
from tola.delegation.protocol import DelegationStatus


class CloseDecision(str, Enum):
    CLOSED = "CLOSED"
    RETURN_TO_SPECIALIST = "RETURN_TO_SPECIALIST"
    FLAGGED_TOLA = "FLAGGED_TOLA"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CloseResult:
    decision: str
    delegation_id: str
    previous_status: str
    new_status: str
    outcome: str
    missing_criteria: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    return_to_specialist_request: dict[str, Any] = field(default_factory=dict)


def verify_and_close(
    tracker: DelegationTracker,
    delegation_id: str,
    criteria: list[SuccessCriterion],
    evidence: dict[str, Any],
) -> CloseResult:
    """Verify outcome and decide on closing via T12 tracker.

    Only VERIFIED results may move RESULT_RECEIVED -> ACCEPTED.
    NOT_VERIFIED / PARTIALLY_VERIFIED produce a structured
    return-to-specialist request listing missing criteria.
    UNVERIFIABLE flags Tola. Never closes on assertion alone.
    """
    result = verify_outcome(criteria, evidence)

    # Read current tracker status
    entry = tracker.status(delegation_id)
    previous_status = entry.status.value

    if result.outcome == VerificationOutcome.VERIFIED.value:
        # Only VERIFIED can advance RESULT_RECEIVED -> ACCEPTED
        if previous_status == DelegationStatus.RESULT_RECEIVED.value:
            tracker.record_event(
                delegation_id,
                TrackingEvent.ACCEPTED,
                evidence.get("timestamp", ""),
            )
        return CloseResult(
            decision=CloseDecision.CLOSED.value,
            delegation_id=delegation_id,
            previous_status=previous_status,
            new_status=DelegationStatus.ACCEPTED.value,
            outcome=result.outcome,
            reasons=result.reasons,
        )

    if result.outcome == VerificationOutcome.UNVERIFIABLE.value:
        return CloseResult(
            decision=CloseDecision.FLAGGED_TOLA.value,
            delegation_id=delegation_id,
            previous_status=previous_status,
            new_status=previous_status,
            outcome=result.outcome,
            missing_criteria=result.missing,
            reasons=result.reasons,
        )

    # NOT_VERIFIED or PARTIALLY_VERIFIED -- return to specialist
    missing_list = list(result.missing)
    return_to_request = {
        "delegation_id": delegation_id,
        "action": "return_to_specialist",
        "missing_criteria": missing_list,
        "reason": "Not all success criteria met",
        "outcome": result.outcome,
    }

    return CloseResult(
        decision=CloseDecision.RETURN_TO_SPECIALIST.value,
        delegation_id=delegation_id,
        previous_status=previous_status,
        new_status=previous_status,
        outcome=result.outcome,
        missing_criteria=missing_list,
        reasons=result.reasons,
        return_to_specialist_request=return_to_request,
    )