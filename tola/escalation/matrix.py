"""EscalationMatrix -- deterministic escalation level mapping.

Batch T8 -- Escalation Matrix and Stop Rules.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Escalation levels (ordered lowest -> highest)
# ---------------------------------------------------------------------------

class EscalationLevel(str, Enum):
    NOTE = "NOTE"
    FLAG = "FLAG"
    PAUSE = "PAUSE"
    STOP_AND_ESCALATE = "STOP_AND_ESCALATE"


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

# T3 health labels -> escalation level mapping.
BLOCKED_LABEL = "BLOCKED"
AT_RISK_LABEL = "AT_RISK"
ATTENTION_LABEL = "ATTENTION"
ON_TRACK_LABEL = "ON_TRACK"
DORMANT_LABEL = "DORMANT"

# Blocked dependency chain length that triggers STOP_AND_ESCALATE.
BLOCKED_CHAIN_LENGTH_THRESHOLD = 3

# Repeated boundary violation count that triggers STOP_AND_ESCALATE.
BOUNDARY_VIOLATION_REPEAT_THRESHOLD = 2

# Stalled delegation days threshold (reuse from T5).
STALLED_DELEGATION_DAYS = 5

# Materiality threshold -- items below this materiality score
# are considered cosmetic and do NOT trigger escalation stop.
MATERIALITY_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Decision dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EscalationDecision:
    """Result of evaluating an escalation trigger."""

    level: EscalationLevel
    reason: str
    evidence: List[str]
    recipient_class: str  # e.g. "HABEEB", "OWNING_SPECIALIST", "TOLA"


@dataclass(frozen=True)
class TriggerContext:
    """Immutable input for escalation evaluation.

    All fields are inputs -- no clock reads, no I/O.
    Deterministic: same context -> same decision.
    """

    health_label: Optional[str] = None
    t7_propagation_result: Optional[str] = None
    t5_delegation_status: Optional[str] = None
    t4_boundary_violations: Optional[List[str]] = None
    blocked_chain_length: int = 0
    boundary_violation_count: int = 0
    materiality_score: float = 1.0
    explicit_user_stop: bool = False
    delegation_to_inactive_specialist: bool = False


# ---------------------------------------------------------------------------
# EscalationMatrix
# ---------------------------------------------------------------------------

class EscalationMatrix:
    """Maps trigger conditions to deterministic EscalationDecisions.

    The matrix is a pure function: no side effects, no I/O,
    no clock reads.  Same TriggerContext always produces the
    same EscalationDecision.
    """

    # T3 health label -> escalation level.
    HEALTH_LABEL_MAP: Dict[str, EscalationLevel] = {
        BLOCKED_LABEL: EscalationLevel.STOP_AND_ESCALATE,
        AT_RISK_LABEL: EscalationLevel.FLAG,
        ATTENTION_LABEL: EscalationLevel.NOTE,
        ON_TRACK_LABEL: EscalationLevel.NOTE,
        DORMANT_LABEL: EscalationLevel.FLAG,
    }

    # T7 propagation result -> escalation level.
    PROPAGATION_MAP: Dict[str, EscalationLevel] = {
        "CRITICAL": EscalationLevel.STOP_AND_ESCALATE,
        "HIGH": EscalationLevel.FLAG,
        "MEDIUM": EscalationLevel.NOTE,
        "LOW": EscalationLevel.NOTE,
    }

    # T5 delegation status -> escalation level.
    DELEGATION_STATUS_MAP: Dict[str, EscalationLevel] = {
        "REJECTED": EscalationLevel.FLAG,
        "STALLED": EscalationLevel.PAUSE,
        "FUTURE_DEPENDENCY": EscalationLevel.PAUSE,
        "COMPLETED": EscalationLevel.NOTE,
    }

    # Recipient class per escalation level.
    RECIPIENT_BY_LEVEL: Dict[EscalationLevel, str] = {
        EscalationLevel.NOTE: "OWNING_SPECIALIST",
        EscalationLevel.FLAG: "OWNING_SPECIALIST",
        EscalationLevel.PAUSE: "TOLA",
        EscalationLevel.STOP_AND_ESCALATE: "HABEEB",
    }

    @staticmethod
    def evaluate_escalation(
        context: TriggerContext,
    ) -> EscalationDecision:
        """Evaluate the escalation level for a given trigger context.

        Returns a deterministic EscalationDecision.
        """
        reasons: List[str] = []
        evidence: List[str] = []
        highest_level = EscalationLevel.NOTE

        # 1. Explicit user stop always wins.
        if context.explicit_user_stop:
            return EscalationDecision(
                level=EscalationLevel.STOP_AND_ESCALATE,
                reason="Explicit user stop honoured.",
                evidence=["explicit_user_stop=True"],
                recipient_class="HABEEB",
            )

        # 2. T4 boundary violations always STOP_AND_ESCALATE.
        if context.t4_boundary_violations:
            violations = context.t4_boundary_violations
            count = len(violations)
            reasons.append(
                f"Boundary violation(s) detected: {count} violation(s)."
            )
            evidence.append(f"boundary_violations={violations}")
            if count >= BOUNDARY_VIOLATION_REPEAT_THRESHOLD:
                reasons.append(
                    f"Repeated boundary violations (count={count}) "
                    f"exceed threshold {BOUNDARY_VIOLATION_REPEAT_THRESHOLD}."
                )
            highest_level = EscalationLevel.STOP_AND_ESCALATE

        # 3. Delegation to non-ACTIVE specialist.
        if context.delegation_to_inactive_specialist:
            reasons.append(
                "Delegation attempted to non-ACTIVE specialist."
            )
            evidence.append("delegation_to_inactive_specialist=True")
            highest_level = max(
                highest_level, EscalationLevel.STOP_AND_ESCALATE,
                key=lambda l: list(EscalationLevel).index(l),
            )

        # 4. T3 health label mapping.
        if context.health_label:
            label = context.health_label
            mapped = EscalationMatrix.HEALTH_LABEL_MAP.get(label)
            if mapped:
                reasons.append(f"T3 health label '{label}' maps to {mapped.value}.")
                evidence.append(f"health_label={label}")
                if mapped.value != "NOTE":
                    highest_level = max(
                        highest_level, mapped,
                        key=lambda l: list(EscalationLevel).index(l),
                    )

        # 5. T7 propagation result mapping.
        if context.t7_propagation_result:
            result = context.t7_propagation_result
            mapped = EscalationMatrix.PROPAGATION_MAP.get(result)
            if mapped:
                reasons.append(
                    f"T7 propagation result '{result}' maps to {mapped.value}."
                )
                evidence.append(f"propagation_result={result}")
                if mapped.value != "NOTE":
                    highest_level = max(
                        highest_level, mapped,
                        key=lambda l: list(EscalationLevel).index(l),
                    )

        # 6. T5 delegation status mapping.
        if context.t5_delegation_status:
            status = context.t5_delegation_status
            mapped = EscalationMatrix.DELEGATION_STATUS_MAP.get(status)
            if mapped:
                reasons.append(
                    f"T5 delegation status '{status}' maps to {mapped.value}."
                )
                evidence.append(f"delegation_status={status}")
                if mapped.value != "NOTE":
                    highest_level = max(
                        highest_level, mapped,
                        key=lambda l: list(EscalationLevel).index(l),
                    )

        # 7. Blocked dependency chain length.
        if context.blocked_chain_length >= BLOCKED_CHAIN_LENGTH_THRESHOLD:
            reasons.append(
                f"Blocked dependency chain length ({context.blocked_chain_length}) "
                f"exceeds threshold {BLOCKED_CHAIN_LENGTH_THRESHOLD}."
            )
            evidence.append(
                f"blocked_chain_length={context.blocked_chain_length}"
            )
            highest_level = max(
                highest_level, EscalationLevel.STOP_AND_ESCALATE,
                key=lambda l: list(EscalationLevel).index(l),
            )

        # 8. Materiality below threshold -- do-not-escalate for minor items.
        if context.materiality_score < MATERIALITY_THRESHOLD:
            reasons.append(
                f"Materiality score ({context.materiality_score}) below "
                f"threshold ({MATERIALITY_THRESHOLD}).  Minor item -- no stop."
            )
            evidence.append(
                f"materiality_score={context.materiality_score}"
            )
            # Cap at FLAG even if other signals are present for minor items.
            if highest_level == EscalationLevel.STOP_AND_ESCALATE:
                highest_level = EscalationLevel.FLAG

        # Determine recipient.
        recipient = EscalationMatrix.RECIPIENT_BY_LEVEL.get(
            highest_level, "TOLA"
        )

        return EscalationDecision(
            level=highest_level,
            reason="; ".join(reasons) if reasons else "No escalation trigger.",
            evidence=evidence,
            recipient_class=recipient,
        )