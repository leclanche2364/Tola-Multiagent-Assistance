# Scope gate for Batch T16.
# Plain ASCII. Stdlib only. Deterministic. No I/O.

from __future__ import annotations

from typing import Any, Dict, Tuple

from tola.scope.evaluator import ScopeDecision, Verdict, evaluate_scope


def scope_gate(
    proposal: Dict[str, Any],
    context: Dict[str, Any],
) -> Tuple[ScopeDecision, Dict[str, Any]]:
    """Convenience wrapper: evaluate scope and return decision
    plus a decision-register-ready record skeleton for STOP/DEFER
    verdicts (T15 DecisionRecord fields). Pure functions, no I/O.

    Returns (decision, register_record).
    register_record is an empty dict for START/SHAPE_SMALLER/NEEDS_USER_DECISION;
    for STOP/DEFER it contains T15 DecisionRecord fields so the verdict
    is auditable.
    """
    decision = evaluate_scope(proposal, context)
    record: Dict[str, Any] = {}

    if decision.verdict in (Verdict.STOP, Verdict.DEFER):
        record = {
            "decision": decision.verdict.value,
            "reason": "; ".join(decision.reasoning),
            "evidence": proposal.get("evidence", ""),
            "alternatives": proposal.get("alternatives", "None"),
            "tradeoff": decision.opportunity_cost,
            "owner": proposal.get("owner", "tola-scope"),
            "date": proposal.get("date", ""),
            "expected_outcome": proposal.get("expected_outcome", ""),
            "review_date": proposal.get("revisit_trigger", None),
            "revisit_trigger": {
                "kind": "SCOPE_REVISIT",
                "condition": _revisit_condition_text(decision, proposal, context),
            },
        }

    return decision, record


def _revisit_condition_text(
    decision: ScopeDecision,
    proposal: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    if decision.verdict == Verdict.DEFER:
        cap = context.get("capacity_summary", context.get("appetite", {}))
        if isinstance(cap, dict):
            threshold = cap.get("capacity_threshold", "remaining_capacity > 0")
            return f"Revisit when {threshold}"
    return proposal.get("revisit_trigger", "Revisit when conditions change")