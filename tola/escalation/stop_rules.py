"""Stop Rules -- deterministic stop/do-not-stop decisions.

Batch T8 -- Escalation Matrix and Stop Rules.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from tola.escalation.matrix import (
    EscalationLevel,
    TriggerContext,
    BLOCKED_CHAIN_LENGTH_THRESHOLD,
    BOUNDARY_VIOLATION_REPEAT_THRESHOLD,
    STALLED_DELEGATION_DAYS,
    MATERIALITY_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Stop decision
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StopDecision:
    """Result of evaluating stop rules against a context."""

    stop: bool
    rule_id: str
    reason: str


# ---------------------------------------------------------------------------
# Do-not-stop list (healthy work must never trigger a stop)
# ---------------------------------------------------------------------------

# Health labels that are always safe -- stop rules must NOT fire.
DO_NOT_STOP_LABELS = frozenset({"ON_TRACK", "ATTENTION"})

# Delegation statuses that indicate healthy progress.
DO_NOT_STOP_DELEGATION_STATUSES = frozenset({"COMPLETED", "IN_PROGRESS"})

# Rule IDs that are cosmetic / no-material-impact and must not stop.
COSMETIC_RULE_IDS = frozenset({
    "minor_format_issue",
    "cosmetic_change",
    "no_material_impact",
    "style_note",
})


# ---------------------------------------------------------------------------
# Stop rules (module-level functions for direct import)
# ---------------------------------------------------------------------------

def should_stop(context: TriggerContext) -> StopDecision:
    """Evaluate all stop rules against the context."""
    return StopRules.should_stop(context)


# ---------------------------------------------------------------------------
# Stop rules
# ---------------------------------------------------------------------------

class StopRules:
    """Deterministic stop-rule evaluation.

    Each rule is a pure function of the TriggerContext.
    No I/O, no clock reads, no randomness.
    """

    @staticmethod
    def should_stop(context: TriggerContext) -> StopDecision:
        """Evaluate all stop rules against the context.

        Returns StopDecision(stop=True, rule_id, reason) when a
        stop rule fires.  Returns StopDecision(stop=False, ...)
        when no rule fires (including for healthy ON_TRACK work).
        """
        # Rule 0: Explicit user stop -- always honoured.
        if context.explicit_user_stop:
            return StopDecision(
                stop=True,
                rule_id="explicit_user_stop",
                reason="User explicitly requested stop.",
            )

        # Rule 1: Blocked dependency chain length exceeds threshold.
        if context.blocked_chain_length >= BLOCKED_CHAIN_LENGTH_THRESHOLD:
            return StopDecision(
                stop=True,
                rule_id="blocked_chain_exceeds_threshold",
                reason=(
                    f"Blocked dependency chain length "
                    f"({context.blocked_chain_length}) exceeds "
                    f"threshold ({BLOCKED_CHAIN_LENGTH_THRESHOLD})."
                ),
            )

        # Rule 2: Repeated boundary violations.
        if context.t4_boundary_violations and len(context.t4_boundary_violations) >= BOUNDARY_VIOLATION_REPEAT_THRESHOLD:
            return StopDecision(
                stop=True,
                rule_id="repeated_boundary_violations",
                reason=(
                    f"Boundary violations count "
                    f"({len(context.t4_boundary_violations)}) meets "
                    f"repeat threshold ({BOUNDARY_VIOLATION_REPEAT_THRESHOLD})."
                ),
            )

        # Rule 3: Delegation to non-ACTIVE specialist attempted.
        if context.delegation_to_inactive_specialist:
            return StopDecision(
                stop=True,
                rule_id="delegation_to_inactive_specialist",
                reason="Delegation to non-ACTIVE specialist is forbidden.",
            )

        # Rule 4: Materiality below threshold -- do-not-escalate rule.
        # Minor items (cosmetic / no-material-impact) must NOT trigger stop.
        if context.materiality_score < MATERIALITY_THRESHOLD:
            return StopDecision(
                stop=False,
                rule_id="do_not_escalate_minor_item",
                reason=(
                    f"Materiality score ({context.materiality_score}) "
                    f"below threshold ({MATERIALITY_THRESHOLD}).  "
                    f"Minor item -- stop rules do not fire."
                ),
            )

        # Rule 5: Healthy ON_TRACK/ATTENTION work -- stop rules must NOT fire.
        # This is the false-positive guard.
        if context.health_label in DO_NOT_STOP_LABELS:
            return StopDecision(
                stop=False,
                rule_id="healthy_work_no_stop",
                reason=(
                    f"Health label '{context.health_label}' is on the "
                    f"do-not-stop list.  Stop rules do not fire for healthy work."
                ),
            )

        # Rule 5b: Material health labels that imply stop.
        # BLOCKED and DORMANT are inherently material.
        MATERIAL_STOP_LABELS = frozenset({"BLOCKED", "DORMANT"})
        if context.health_label in MATERIAL_STOP_LABELS:
            return StopDecision(
                stop=True,
                rule_id="material_health_label_triggers_stop",
                reason=(
                    f"Health label '{context.health_label}' is material "
                    f"and triggers stop."
                ),
            )

        # Rule 6: Healthy delegation status -- no stop.
        if context.t5_delegation_status in DO_NOT_STOP_DELEGATION_STATUSES:
            return StopDecision(
                stop=False,
                rule_id="healthy_delegation_status_no_stop",
                reason=(
                    f"Delegation status '{context.t5_delegation_status}' "
                    f"is on the do-not-stop list."
                ),
            )

        # Rule 7: Cosmetic / no-material-impact items -- do not stop.
        # (Covered by materiality threshold above; this is a named alias.)
        # No separate action needed -- materiality check handles it.

        # No stop rule fired.
        return StopDecision(
            stop=False,
            rule_id="no_stop_rule_fired",
            reason="No stop rule matched.  Work may continue.",
        )

    @staticmethod
    def is_do_not_stop_label(label: str) -> bool:
        """Check if a health label is on the do-not-stop list."""
        return label in DO_NOT_STOP_LABELS

    @staticmethod
    def is_cosmetic_rule(rule_id: str) -> bool:
        """Check if a rule ID is cosmetic (should not trigger stop)."""
        return rule_id in COSMETIC_RULE_IDS