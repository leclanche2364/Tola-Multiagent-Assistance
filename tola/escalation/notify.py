"""Escalation routing -- pure routing, no I/O.

Batch T8 -- Escalation Matrix and Stop Rules.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from tola.escalation.matrix import (
    EscalationDecision,
    EscalationLevel,
)


# ---------------------------------------------------------------------------
# Routing result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoutingResult:
    """Result of routing an escalation decision."""

    recipient_agent: str
    recipient_class: str
    message_skeleton: str


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

# Escalation level -> (recipient_agent, recipient_class, template).
ROUTING_TABLE: dict = {
    EscalationLevel.NOTE: (
        "owning_specialist",
        "OWNING_SPECIALIST",
        "NOTE: {reason}. Evidence: {evidence}. No immediate action required.",
    ),
    EscalationLevel.FLAG: (
        "owning_specialist",
        "OWNING_SPECIALIST",
        "FLAG: {reason}. Evidence: {evidence}. Review required within 24h.",
    ),
    EscalationLevel.PAUSE: (
        "tola",
        "TOLA",
        "PAUSE: {reason}. Evidence: {evidence}. Pause work and assess.",
    ),
    EscalationLevel.STOP_AND_ESCALATE: (
        "habeeb",
        "HABEEB",
        "STOP_AND_ESCALATE: {reason}. Evidence: {evidence}. Immediate user attention required.",
    ),
}


# ---------------------------------------------------------------------------
# route_escalation
# ---------------------------------------------------------------------------

def route_escalation(
    decision: EscalationDecision,
) -> RoutingResult:
    """Route an escalation decision to the correct recipient.

    Pure routing -- no I/O, no message sending.
    Deterministic: same decision -> same routing result.

    Tola -> Habeeb for STOP_AND_ESCALATE.
    Tola -> owning specialist for NOTE/FLAG.
    Tola self-routes for PAUSE.
    """
    level = decision.level
    recipient_agent, recipient_class, template = ROUTING_TABLE.get(
        level, ("tola", "TOLA", "UNKNOWN: {reason}")
    )

    message = template.format(
        reason=decision.reason,
        evidence="; ".join(decision.evidence) if decision.evidence else "none",
    )

    return RoutingResult(
        recipient_agent=recipient_agent,
        recipient_class=recipient_class,
        message_skeleton=message,
    )