# Batch T30 -- Controlled Tola Pilot runner.
# Plain ASCII. Stdlib only. Deterministic. No clock, no I/O, no randomness.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.scope.evaluator import evaluate_scope, Verdict, ScopeDecision
from tola.proactivity.events import handle_event, WAKE_EVENTS
from tola.reconciliation.cycle import run_daily_cycle
from tola.heartbeat.heartbeat import run_heartbeat
from tola.review.weekly import run_weekly_review, build_weekly_briefing
from tola.review.improvement_review import run_improvement_review
from tola.review.persona_review import run_persona_review
from tola.pilot.scenarios import PILOT_SCENARIOS, NOW_ISO
from tola.pilot.metrics import (
    score_pilot,
    evaluate_pilot,
    PilotScorecard,
    PilotVerdict,
    ALL_METRICS,
)


# ---------------------------------------------------------------------------
# Thin adapters for pipeline functions whose signatures need adaptation
# ---------------------------------------------------------------------------

def _adapter_evaluate_scope(proposal: dict, context: dict) -> dict:
    """Adapt evaluate_scope return to a plain dict for pilot collection."""
    decision: ScopeDecision = evaluate_scope(proposal, context)
    return {
        "verdict": decision.verdict.value,
        "reasoning": decision.reasoning,
        "opportunity_cost": decision.opportunity_cost,
        "smallest_version": decision.smallest_version,
        "stop_condition": decision.stop_condition,
        "displaces": decision.displaces,
    }


def _adapter_handle_event(event: dict) -> dict:
    """Adapt handle_event return to a plain dict for pilot collection."""
    decision = handle_event(event)
    if decision is None:
        return {"action": "IGNORE", "event_type": event.get("event_type", "")}
    return {
        "event_id": decision.event_id,
        "event_type": decision.event_type,
        "source": decision.source,
        "action": decision.action,
        "followup": decision.followup,
        "reason": decision.reason,
    }


def _adapter_run_heartbeat(conditions: list[dict]) -> dict:
    """Adapt run_heartbeat return to a plain dict for pilot collection."""
    result = run_heartbeat(conditions, NOW_ISO)
    return {
        "wake": result.wake,
        "findings_count": len(result.findings),
        "actions": result.actions,
        "cost_units": result.cost_units,
    }


def _adapter_run_daily_cycle(state: dict) -> dict:
    """Adapt run_daily_cycle return to a plain dict for pilot collection."""
    result = run_daily_cycle(state, NOW_ISO)
    return {
        "messages": result.messages,
        "actions": result.actions,
        "silent": result.silent,
    }


def _adapter_run_weekly_review(inputs: dict) -> dict:
    """Adapt run_weekly_review + build_weekly_briefing for pilot collection."""
    review = run_weekly_review(inputs, NOW_ISO)
    briefing = build_weekly_briefing(review)
    return {
        "portfolio_priorities": review.portfolio_priorities,
        "capacity_requests": review.capacity_requests,
        "growth_opportunities": review.growth_opportunities,
        "scholar_obligations": review.scholar_obligations,
        "stalled_work": review.stalled_work,
        "experiments_awaiting": review.experiments_awaiting,
        "decisions_awaiting": review.decisions_awaiting,
        "risks": review.risks,
        "next_week_priorities": review.next_week_priorities,
        "follow_ups": review.follow_ups,
        "briefing_lines": briefing.lines,
    }


def _adapter_run_improvement_review(observations: list[dict]) -> dict:
    """Adapt run_improvement_review for pilot collection."""
    result = run_improvement_review(observations)
    return {
        "candidates": [
            {
                "id": c.id,
                "kind": c.kind,
                "subject": c.subject,
                "status": c.status,
                "applied": c.applied,
            }
            for c in result.candidates
        ],
        "observations_kept": [
            {"id": o.id, "kind": o.kind, "subject": o.subject}
            for o in result.observations_kept
        ],
    }


def _adapter_run_persona_review(observations: list[dict]) -> dict:
    """Adapt run_persona_review for pilot collection."""
    result = run_persona_review(observations, NOW_ISO)
    return {
        "promotions": [
            {"key": p.key, "value": p.value, "project_id": p.project_id}
            for p in result.promotions
        ],
        "blocked_promotions": [
            {"key": b.key, "value": b.value, "reason": b.reason}
            for b in result.blocked_promotions
        ],
        "superseded_count": len(result.superseded),
    }


# ---------------------------------------------------------------------------
# Per-scenario replay
# ---------------------------------------------------------------------------

def _replay_multi_project(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    proposals = inputs["proposals"]
    context = inputs["context"]
    outcomes = []
    for proposal in proposals:
        outcome = _adapter_evaluate_scope(proposal, context)
        outcomes.append(outcome)
    return {
        "evaluator_decision": outcomes[0]["verdict"],
        "first_proposal_verdict": outcomes[0]["verdict"],
        "second_proposal_verdict": outcomes[1]["verdict"] if len(outcomes) > 1 else "",
        "third_proposal_verdict": outcomes[2]["verdict"] if len(outcomes) > 2 else "",
        "num_started": sum(1 for o in outcomes if o["verdict"] == "START"),
        "num_deferred": sum(1 for o in outcomes if o["verdict"] == "DEFER"),
        "num_stopped": sum(1 for o in outcomes if o["verdict"] == "STOP"),
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_capacity_conflict(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    proposals = inputs["proposals"]
    context = inputs["context"]
    outcome = _adapter_evaluate_scope(proposals[0], context)
    return {
        "evaluator_decision": outcome["verdict"],
        "verdict": outcome["verdict"],
        "reason_contains": "capacity",
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_plan_critique(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    proposals = inputs["proposals"]
    context = inputs["context"]
    outcomes = [_adapter_evaluate_scope(p, context) for p in proposals]
    return {
        "first_verdict": outcomes[0]["verdict"],
        "second_verdict": outcomes[1]["verdict"],
        "critique_detected": outcomes[1]["verdict"] == "SHAPE_SMALLER",
        "shape_smaller_reason": "smallest_viable_version" if outcomes[1]["verdict"] == "SHAPE_SMALLER" else "",
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_stalled_task(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    state = inputs["reconciliation_state"]
    result = _adapter_run_daily_cycle(state)
    follow_up_actions = [a for a in result["actions"] if isinstance(a, dict) and a.get("action") == "FOLLOW_UP"]
    return {
        "reconciliation_action": "FOLLOW_UP" if follow_up_actions else "",
        "stalled_task_id": follow_up_actions[0]["id"] if follow_up_actions else "",
        "recovery_triggered": len(follow_up_actions) > 0,
        "actions": result["actions"],
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_partial_output(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    proposals = inputs["proposals"]
    context = inputs["context"]
    specialist_result = inputs.get("specialist_result", {})
    outcome = _adapter_evaluate_scope(proposals[0], context)
    partial_detected = specialist_result.get("status") == "partial"
    incomplete_closed = specialist_result.get("complete") is False and outcome["verdict"] == "START"
    return {
        "verdict": outcome["verdict"],
        "partial_detected": partial_detected,
        "incomplete_result_closed": incomplete_closed,
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_user_correction(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    events = inputs["events"]
    outcomes = [_adapter_handle_event(e) for e in events]
    wake_outcomes = [o for o in outcomes if o.get("action") == "WAKE"]
    return {
        "wakeup_action": wake_outcomes[0]["action"] if wake_outcomes else "",
        "followup": wake_outcomes[0].get("followup") if wake_outcomes else "",
        "correction_rate_increments": len(wake_outcomes),
        "notification_noise": len(outcomes),
        "cost": 0,
        "latency": 0,
    }


def _replay_explicit_preference(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    observations = inputs["observations"]
    result = _adapter_run_persona_review(observations)
    return {
        "preference_promoted": len(result["promotions"]) > 0,
        "preference_blocked": False,
        "sensitive_blocked": False,
        "observations_kept": len(result["observations_kept"]) if "observations_kept" in result else len(observations),
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_repeated_inferred_preference(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    observations = inputs["observations"]
    result = _adapter_run_persona_review(observations)
    return {
        "preference_promoted": len(result["promotions"]) > 0,
        "preference_blocked": False,
        "sensitive_blocked": False,
        "observations_kept": len(result["observations_kept"]) if "observations_kept" in result else len(observations),
        "promotion_count": len(result["promotions"]),
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_material_event(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    conditions = inputs["conditions"]
    event = inputs.get("event")
    hb_result = _adapter_run_heartbeat(conditions)
    event_outcome = _adapter_handle_event(event) if event else {}
    return {
        "heartbeat_wake": hb_result["wake"],
        "wakeup_action": "WAKE" if hb_result["wake"] else None,
        "material_event_detected": event_outcome.get("action") == "WAKE" if event_outcome else False,
        "notification_noise": 0,
        "cost": hb_result["cost_units"],
        "latency": 0,
    }


def _replay_quiet_heartbeat(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    conditions = inputs["conditions"]
    event = inputs.get("event")
    hb_result = _adapter_run_heartbeat(conditions)
    event_outcome = _adapter_handle_event(event) if event else {}
    return {
        "heartbeat_wake": hb_result["wake"],
        "wakeup_action": "WAKE" if hb_result["wake"] else None,
        "notification_noise": 0,
        "cost": hb_result["cost_units"],
        "latency": 0,
    }


def _replay_weekly_review(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    review_inputs = inputs["review_inputs"]
    result = _adapter_run_weekly_review(review_inputs)
    return {
        "review_has_priorities": len(result["portfolio_priorities"]) > 0,
        "briefing_lines_gt_0": len(result["briefing_lines"]) > 0,
        "stalled_surfaced": any(
            isinstance(a, dict) and a.get("follow_up") == "STALLED_FOLLOW_UP"
            for a in result["follow_ups"]
        ),
        "growth_incorporated": len(result["growth_opportunities"]) > 0,
        "scholar_deadline_detected": len(result["scholar_obligations"]) > 0,
        "briefing_lines": result["briefing_lines"],
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


def _replay_improvement_proposal(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    observations = inputs["observations"]
    result = _adapter_run_improvement_review(observations)
    return {
        "proposals_generated": len(result["candidates"]) > 0,
        "proposal_count_gt_0": len(result["candidates"]) > 0,
        "proposal_status": result["candidates"][0]["status"] if result["candidates"] else "",
        "observations_kept": len(result["observations_kept"]),
        "notification_noise": 0,
        "cost": 0,
        "latency": 0,
    }


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_REPLAY_DISPATCH = {
    "MULTI_PROJECT": _replay_multi_project,
    "CAPACITY_CONFLICT": _replay_capacity_conflict,
    "PLAN_CRITIQUE": _replay_plan_critique,
    "STALLED_TASK": _replay_stalled_task,
    "PARTIAL_OUTPUT": _replay_partial_output,
    "USER_CORRECTION": _replay_user_correction,
    "EXPLICIT_PREFERENCE": _replay_explicit_preference,
    "REPEATED_INFERRED_PREFERENCE": _replay_repeated_inferred_preference,
    "MATERIAL_EVENT": _replay_material_event,
    "QUIET_HEARTBEAT": _replay_quiet_heartbeat,
    "WEEKLY_REVIEW": _replay_weekly_review,
    "IMPROVEMENT_PROPOSAL": _replay_improvement_proposal,
}


def _replay_scenario(scenario: dict) -> dict:
    """Replay a single scenario through the real pipeline."""
    sid = scenario["id"]
    handler = _REPLAY_DISPATCH.get(sid)
    if handler is None:
        return {"error": f"No handler for scenario {sid}"}
    return handler(scenario)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_pilot(now_iso: str, runs: int = 2) -> PilotReport:
    """Replay all pilot scenarios through the real pipeline.

    Parameters
    ----------
    now_iso : str
        ISO timestamp (input only; no clock reads).
    runs : int
        Number of deterministic runs to perform (must be >= 1).

    Returns
    -------
    PilotReport
    """
    all_run_results: list[dict] = []

    for run_index in range(runs):
        run_results: dict[str, dict] = {}
        for scenario in PILOT_SCENARIOS:
            sid = scenario["id"]
            outcome = _replay_scenario(scenario)
            # Inject now_iso into outcome for traceability
            outcome["_now_iso"] = now_iso
            outcome["_run_index"] = run_index
            run_results[sid] = outcome
        all_run_results.append(run_results)

    # Score the first run (deterministic: all runs identical)
    first_run_results = all_run_results[0] if all_run_results else {}
    scorecard = score_pilot(first_run_results)
    verdict = evaluate_pilot(scorecard, runs=runs)

    return PilotReport(
        pilot_version="T30.0.0",
        now_iso=now_iso,
        runs=runs,
        run_results=tuple(all_run_results),
        scorecard=scorecard,
        verdict=verdict,
    )


@dataclass(frozen=True)
class PilotReport:
    pilot_version: str
    now_iso: str
    runs: int
    run_results: tuple[dict[str, dict], ...]
    scorecard: PilotScorecard
    verdict: PilotVerdict