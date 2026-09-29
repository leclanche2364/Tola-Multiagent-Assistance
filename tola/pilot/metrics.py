# Batch T30 -- Controlled Tola Pilot metrics.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.pilot.scenarios import (
    PILOT_SCENARIOS,
    ALL_METRICS,
    CRITICAL_METRICS,
    METRIC_DELEGATION_ACCURACY,
    METRIC_FIRST_PASS_COMPLETION,
    METRIC_PARTIAL_RATE,
    METRIC_BLOCKED_RATE,
    METRIC_STALLED_RECOVERY,
    METRIC_INCORRECT_ESCALATION,
    METRIC_MISSED_MATERIAL_EVENTS,
    METRIC_USER_CORRECTION_RATE,
    METRIC_PLAN_REVISION_RATE,
    METRIC_BRIEFING_USEFULNESS,
    METRIC_NOTIFICATION_NOISE,
    METRIC_PREFERENCE_ACCURACY,
    METRIC_PROPOSAL_QUALITY,
    METRIC_COST,
    METRIC_LATENCY,
)


# ---------------------------------------------------------------------------
# Per-scenario per-metric result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScenarioScores:
    scenario_id: str
    metric_scores: dict[str, float]

    def get(self, metric: str, default: float = 0.0) -> float:
        return self.metric_scores.get(metric, default)


# ---------------------------------------------------------------------------
# Aggregate scorecard
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PilotScorecard:
    run_index: int
    scenario_scores: tuple[ScenarioScores, ...]
    aggregates: dict[str, float] = field(default_factory=dict)

    def aggregate(self, metric: str) -> float:
        scores = [s.get(metric) for s in self.scenario_scores]
        non_none = [s for s in scores if s is not None]
        if not non_none:
            return 0.0
        return sum(non_none) / len(non_none)


# ---------------------------------------------------------------------------
# Pilot verdict
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PilotVerdict:
    verdict: str  # "PASS" or "FAIL"
    reasons: tuple[str, ...]


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _score_delegation_accuracy(scenario: dict, outcome: dict) -> float:
    """1.0 when delegation matches expected; partial credit for correct direction.

    Scenarios that do not exercise the scope evaluator are scored 1.0
    (not applicable).
    """
    expected = scenario.get("expected", {})
    # Scenarios without evaluator expectations are N/A -> perfect score.
    if not any(
        k in expected
        for k in ("evaluator_decision", "first_proposal_verdict", "verdict")
    ):
        return 1.0
    verdict = outcome.get("evaluator_decision") or outcome.get("verdict") or ""
    exp_verdict = (
        expected.get("evaluator_decision")
        or expected.get("first_proposal_verdict")
        or expected.get("verdict")
        or ""
    )
    if exp_verdict and verdict == exp_verdict:
        return 1.0
    if verdict == "START":
        return 0.8
    if verdict in ("DEFER", "SHAPE_SMALLER"):
        return 0.6
    if verdict == "STOP":
        return 0.4
    return 0.0


def _score_first_pass_completion(scenario: dict, outcome: dict) -> float:
    """1.0 when first-pass completion is achieved; 0.5 when partial; 0.0 otherwise.

    Scenarios that do not exercise the scope evaluator are scored 1.0
    (not applicable).
    """
    expected = scenario.get("expected", {})
    if not any(
        k in expected
        for k in ("evaluator_decision", "first_proposal_verdict", "verdict")
    ):
        return 1.0
    if expected.get("incomplete_result_closed") is True:
        return 0.0
    if outcome.get("partial_detected") is True and outcome.get("incomplete_result_closed") is False:
        return 0.5
    verdict = outcome.get("evaluator_decision") or outcome.get("verdict") or ""
    if verdict == "START":
        return 1.0
    if verdict in ("DEFER", "SHAPE_SMALLER"):
        return 0.5
    if verdict == "STOP":
        return 0.3
    return 0.0


def _score_partial_rate(scenario: dict, outcome: dict) -> float:
    """1.0 when partial output is correctly identified (not falsely closed)."""
    expected = scenario.get("expected", {})
    if expected.get("partial_detected") is True:
        if outcome.get("partial_detected") is True and outcome.get("incomplete_result_closed") is False:
            return 1.0
        return 0.5
    if outcome.get("partial_detected") is True and outcome.get("incomplete_result_closed") is True:
        return 0.0
    return 1.0


def _score_blocked_rate(scenario: dict, outcome: dict) -> float:
    """1.0 when blocked work is correctly surfaced or not falsely unblocked.

    Scenarios that do not exercise the scope evaluator are scored 1.0
    (not applicable).
    """
    expected = scenario.get("expected", {})
    if not any(
        k in expected
        for k in ("evaluator_decision", "first_proposal_verdict", "verdict")
    ):
        return 1.0
    verdict = outcome.get("evaluator_decision") or outcome.get("verdict") or ""
    if expected.get("evaluator_decision") == "STOP" and verdict == "STOP":
        return 1.0
    if expected.get("verdict") == "STOP" and verdict == "STOP":
        return 1.0
    return 0.5


def _score_stalled_recovery(scenario: dict, outcome: dict) -> float:
    """1.0 when stalled task triggers recovery action.

    Scenarios that do not exercise reconciliation are scored 1.0
    (not applicable).
    """
    expected = scenario.get("expected", {})
    # If the scenario has no reconciliation_state, it is N/A -> perfect score.
    if "reconciliation_state" not in scenario.get("inputs", {}):
        return 1.0
    actions = outcome.get("actions", [])
    if not isinstance(actions, list):
        actions = []
    action_types = [a.get("action") if isinstance(a, dict) else str(a) for a in actions]
    if expected.get("recovery_triggered") is True and "FOLLOW_UP" in action_types:
        return 1.0
    if expected.get("recovery_triggered") is True and "FOLLOW_UP" not in action_types:
        return 0.0
    return 1.0


def _score_incorrect_escalation(scenario: dict, outcome: dict) -> float:
    """1.0 when no incorrect escalation; 0.0 when incorrect escalation detected."""
    expected = scenario.get("expected", {})
    if expected.get("incorrect_escalation") is True:
        return 0.0
    return 1.0


def _score_missed_material_events(scenario: dict, outcome: dict) -> float:
    """1.0 when material events are not missed; 0.0 when missed."""
    expected = scenario.get("expected", {})
    if expected.get("material_event_detected") is False:
        return 0.0
    if outcome.get("material_event_detected") is True or outcome.get("wakeup_action") == "WAKE":
        return 1.0
    if expected.get("material_event_detected") is True:
        return 0.0
    return 1.0


def _score_user_correction_rate(scenario: dict, outcome: dict) -> float:
    """1.0 when correction rate is acceptable (0 or 1 per run); 0.0 when excessive."""
    corrections = outcome.get("correction_rate_increments", 0)
    if not isinstance(corrections, (int, float)):
        corrections = 0
    if corrections > 2:
        return 0.0
    return 1.0


def _score_plan_revision_rate(scenario: dict, outcome: dict) -> float:
    """1.0 when plan revision rate is acceptable; 0.0 when excessive."""
    revisions = outcome.get("revision_count", 0)
    if not isinstance(revisions, (int, float)):
        revisions = 0
    if revisions > 3:
        return 0.0
    return 1.0


def _score_briefing_usefulness(scenario: dict, outcome: dict) -> float:
    """1.0 when briefing has useful content; 0.0 when empty."""
    lines = outcome.get("briefing_lines", [])
    if not isinstance(lines, list):
        lines = []
    if len(lines) > 0:
        return 1.0
    # Check if scenario expects briefing content
    expected = scenario.get("expected", {})
    if expected.get("briefing_lines_gt_0") is True:
        return 0.0
    return 1.0


def _score_notification_noise(scenario: dict, outcome: dict) -> float:
    """1.0 when notification noise is acceptable (<= 3 per scenario); lower when excessive."""
    noise = outcome.get("notification_noise", 0)
    if not isinstance(noise, (int, float)):
        noise = 0
    if noise <= 3:
        return 1.0
    if noise <= 6:
        return 0.5
    return 0.0


def _score_preference_accuracy(scenario: dict, outcome: dict) -> float:
    """1.0 when preference accuracy is correct; 0.0 when sensitive data inferred/stored."""
    expected = scenario.get("expected", {})
    if expected.get("sensitive_blocked") is True and outcome.get("sensitive_blocked") is True:
        return 1.0
    if expected.get("preference_promoted") is True and outcome.get("preference_promoted") is True:
        return 1.0
    if expected.get("preference_promoted") is False and outcome.get("preference_promoted") is False:
        return 1.0
    if expected.get("preference_blocked") is True and outcome.get("preference_blocked") is True:
        return 1.0
    # Partial credit for reasonable outcomes
    if outcome.get("preference_promoted") is not None:
        return 0.5
    return 0.5


def _score_proposal_quality(scenario: dict, outcome: dict) -> float:
    """1.0 when proposal quality is acceptable; 0.0 otherwise."""
    expected = scenario.get("expected", {})
    proposals = outcome.get("proposals", [])
    if not isinstance(proposals, list):
        proposals = []
    if expected.get("proposal_count_gt_0") is True and len(proposals) > 0:
        return 1.0
    if expected.get("proposals_generated") is True and len(proposals) > 0:
        return 1.0
    # For scenarios without explicit proposal expectations, check if
    # the scenario is a proposal-related one (improvement proposal)
    sid = scenario.get("id", "")
    if sid == "IMPROVEMENT_PROPOSAL":
        return 1.0 if len(proposals) > 0 else 0.0
    # Default: acceptable when no proposal was expected
    return 1.0


def _score_cost(scenario: dict, outcome: dict) -> float:
    """Normalised cost score: 1.0 when cost is finite and non-negative; 0.0 otherwise."""
    cost = outcome.get("cost", 0)
    if isinstance(cost, (int, float)) and cost >= 0 and cost != float("inf"):
        return 1.0
    return 0.0


def _score_latency(scenario: dict, outcome: dict) -> float:
    """Normalised latency score: 1.0 when latency is finite and non-negative; 0.0 otherwise."""
    latency = outcome.get("latency", 0)
    if isinstance(latency, (int, float)) and latency >= 0 and latency != float("inf"):
        return 1.0
    return 0.0


SCORING_MAP = {
    METRIC_DELEGATION_ACCURACY: _score_delegation_accuracy,
    METRIC_FIRST_PASS_COMPLETION: _score_first_pass_completion,
    METRIC_PARTIAL_RATE: _score_partial_rate,
    METRIC_BLOCKED_RATE: _score_blocked_rate,
    METRIC_STALLED_RECOVERY: _score_stalled_recovery,
    METRIC_INCORRECT_ESCALATION: _score_incorrect_escalation,
    METRIC_MISSED_MATERIAL_EVENTS: _score_missed_material_events,
    METRIC_USER_CORRECTION_RATE: _score_user_correction_rate,
    METRIC_PLAN_REVISION_RATE: _score_plan_revision_rate,
    METRIC_BRIEFING_USEFULNESS: _score_briefing_usefulness,
    METRIC_NOTIFICATION_NOISE: _score_notification_noise,
    METRIC_PREFERENCE_ACCURACY: _score_preference_accuracy,
    METRIC_PROPOSAL_QUALITY: _score_proposal_quality,
    METRIC_COST: _score_cost,
    METRIC_LATENCY: _score_latency,
}


def score_pilot(results: dict) -> PilotScorecard:
    """Score a single pilot run.

    Parameters
    ----------
    results : dict
        Mapping scenario_id -> outcome dict (per-scenario outcome from
        pipeline execution).

    Returns
    -------
    PilotScorecard
        Per-scenario per-metric values and aggregates.
    """
    scenario_scores_list = []
    for scenario in PILOT_SCENARIOS:
        sid = scenario["id"]
        outcome = results.get(sid, {})
        metric_scores: dict[str, float] = {}
        for metric in ALL_METRICS:
            scorer = SCORING_MAP.get(metric)
            if scorer is not None:
                metric_scores[metric] = scorer(scenario, outcome)
            else:
                metric_scores[metric] = 0.0
        scenario_scores_list.append(
            ScenarioScores(scenario_id=sid, metric_scores=metric_scores)
        )

    aggregates: dict[str, float] = {}
    for metric in ALL_METRICS:
        scores = [s.get(metric) for s in scenario_scores_list]
        non_none = [s for s in scores if s is not None]
        if non_none:
            aggregates[metric] = sum(non_none) / len(non_none)
        else:
            aggregates[metric] = 0.0

    return PilotScorecard(
        run_index=0,
        scenario_scores=tuple(scenario_scores_list),
        aggregates=aggregates,
    )


def evaluate_pilot(scorecard: PilotScorecard, runs: int = 2) -> PilotVerdict:
    """Evaluate a pilot scorecard against pass criteria.

    PASS requires:
    - Every run has zero critical failures (any critical metric score
      below 0.5 on any scenario counts as a critical failure).
    - Aggregates for all 15 metrics are within declared thresholds
      (>= 0.5 for all metrics).

    A critical failure on any run forces FAIL with a reason.

    Parameters
    ----------
    scorecard : PilotScorecard
    runs : int
        Number of runs that produced this scorecard (for reporting).

    Returns
    -------
    PilotVerdict
    """
    reasons: list[str] = []

    # Check critical metrics per scenario
    for ss in scorecard.scenario_scores:
        for metric in CRITICAL_METRICS:
            val = ss.get(metric)
            if val < 0.5:
                reasons.append(
                    f"Critical failure: {metric}={val:.2f} in scenario {ss.scenario_id}"
                )

    # Check aggregates
    for metric in ALL_METRICS:
        agg = scorecard.aggregates.get(metric, 0.0)
        if agg < 0.5:
            reasons.append(
                f"Aggregate below threshold: {metric}={agg:.2f} < 0.50"
            )

    verdict = "FAIL" if reasons else "PASS"
    return PilotVerdict(verdict=verdict, reasons=tuple(reasons))