# Explain engine for Batch T15.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from typing import Dict

from tola.decisions.register import DecisionRecord


def explain_decision(register: Dict[str, DecisionRecord], decision_id: str) -> str:
    decision = register[decision_id]
    lines = []
    lines.append("Decision: " + decision.decision)
    lines.append("Reason: " + decision.reason)
    lines.append("Evidence: " + decision.evidence)
    lines.append("Alternatives considered: " + decision.alternatives)
    lines.append("Tradeoff: " + decision.tradeoff)
    lines.append("Owner: " + decision.owner)
    lines.append("Date: " + decision.date)
    lines.append("Expected outcome: " + decision.expected_outcome)
    if decision.review_date:
        lines.append("Review date: " + decision.review_date)
    else:
        lines.append("Review date: (none set)")
    if decision.revisit_trigger:
        lines.append("Revisit trigger: " + str(decision.revisit_trigger))
    else:
        lines.append("Revisit trigger: (none set)")
    if decision.is_superseded():
        lines.append("Status: SUPERSEDED by " + decision.superseded_by)
    else:
        lines.append("Status: ACTIVE")
    return "\n".join(lines)