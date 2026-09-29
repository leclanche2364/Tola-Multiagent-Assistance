# Batch T29 -- Monthly Deep Operating-System Review.
# Plain ASCII. Stdlib only. Deterministic: no clock reads.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Rule constants (named, matching QA T29 thresholds)
# ---------------------------------------------------------------------------

DRAIN_VALUE_MAX = 2          # value_score <= this is low-value
DRAIN_TIME_MIN_HOURS = 10    # time_spent_hours >= this is high-time

COST_ANOMALY_FACTOR = 2.0    # cost > factor x baseline is anomalous

AUTOMATION_CANDIDATE_MIN = 5  # frequency >= this triggers automation candidate

# ---------------------------------------------------------------------------
# Recommendation / finding kinds
# ---------------------------------------------------------------------------

REDUCE_OR_SUNSET = "REDUCE_OR_SUNSET"
REDUCE_OR_REMOVE = "REDUCE_OR_REMOVE"
KEEP = "KEEP"
AUTOMATE = "AUTOMATE"
PROPOSAL = "PROPOSAL"

# ---------------------------------------------------------------------------
# Result dataclasses (frozen / immutable)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Recommendation:
    """A single evidence-backed recommendation.

    Immutable.  Deterministic: same inputs -> same output.
    """
    id: str
    kind: str            # REDUCE_OR_SUNSET | REDUCE_OR_REMOVE | KEEP | AUTOMATE | PROPOSAL
    subject: str
    status: str          # always PROPOSAL for protected areas; otherwise action-level
    expected_benefit: str
    evidence: tuple[str, ...]

@dataclass(frozen=True)
class Finding:
    """A single evidence-backed finding (not a recommendation)."""
    id: str
    kind: str
    subject: str
    evidence: tuple[str, ...]

@dataclass(frozen=True)
class MonthlyReviewResult:
    """Result of a monthly deep operating-system review.

    Immutable.  Deterministic: same inputs -> same output.
    No mutation: recommendations only.
    """
    recommendations: tuple[Recommendation, ...]
    findings: tuple[Finding, ...]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nonempty_evidence(evidence: list[str]) -> tuple[str, ...]:
    """Return evidence as a non-empty tuple; raises on empty."""
    cleaned = tuple(e for e in evidence if e)
    if not cleaned:
        raise ValueError("Every recommendation must carry non-empty evidence.")
    return cleaned


def _assert_recommendation_valid(rec: Recommendation) -> None:
    """Assert recommendation has non-empty expected_benefit and evidence."""
    if not rec.expected_benefit or not rec.expected_benefit.strip():
        raise ValueError(f"Recommendation {rec.id} has empty expected_benefit.")
    if not rec.evidence:
        raise ValueError(f"Recommendation {rec.id} has empty evidence.")

# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------

def _classify_project_drain(project: dict) -> Recommendation | None:
    """T29-01: low-value AND high-time -> REDUCE_OR_SUNSET."""
    value_score = project.get("value_score", 0)
    time_spent = project.get("time_spent_hours", 0)
    if value_score <= DRAIN_VALUE_MAX and time_spent >= DRAIN_TIME_MIN_HOURS:
        return Recommendation(
            id=f"drain-{project.get('id', '')}",
            kind=REDUCE_OR_SUNSET,
            subject=project.get("name", project.get("id", "")),
            status="ACTION",
            expected_benefit=f"Reclaim {time_spent}h/month by reducing or sunsetting low-value project.",
            evidence=_nonempty_evidence([
                f"value_score={value_score} (<= DRAIN_VALUE_MAX={DRAIN_VALUE_MAX})",
                f"time_spent_hours={time_spent} (>= DRAIN_TIME_MIN_HOURS={DRAIN_TIME_MIN_HOURS})",
            ]),
        )
    return None


def _classify_automation_useful(auto: dict) -> Recommendation:
    """T29-02: useful automation -> KEEP (no removal recommendation)."""
    return Recommendation(
        id=f"keep-auto-{auto.get('id', '')}",
        kind=KEEP,
        subject=auto.get("name", auto.get("id", "")),
        status="KEEP",
        expected_benefit="Useful automation retained; no reduction needed.",
        evidence=_nonempty_evidence([
            f"kind=useful",
            f"run_count={auto.get('run_count', 0)}",
            f"value_signals={auto.get('value_signals', [])}",
        ]),
    )


def _classify_automation_noisy(auto: dict) -> Recommendation:
    """T29-03: noisy automation -> REDUCE_OR_REMOVE with evidence."""
    run_count = auto.get("run_count", 0)
    noise_signals = auto.get("noise_signals", [])
    evidence_parts = [f"run_count={run_count}"]
    for ns in noise_signals:
        evidence_parts.append(f"noise_signal={ns}")
    return Recommendation(
        id=f"reduce-auto-{auto.get('id', '')}",
        kind=REDUCE_OR_REMOVE,
        subject=auto.get("name", auto.get("id", "")),
        status="ACTION",
        expected_benefit="Reduce or remove noisy automation to lower operational noise.",
        evidence=_nonempty_evidence(evidence_parts),
    )


def _classify_bottleneck(agent: dict) -> Finding | None:
    """T29-04: agent with queue/wait/failure evidence beyond threshold -> bottleneck finding."""
    queue_depth = agent.get("queue_depth", 0)
    wait_time = agent.get("wait_time_avg", 0)
    failure_rate = agent.get("failure_rate", 0.0)

    # Bottleneck threshold: queue_depth > 10 OR wait_time > 30 OR failure_rate > 0.25
    BOTTLENECK_QUEUE_MAX = 10
    BOTTLENECK_WAIT_MAX = 30
    BOTTLENECK_FAILURE_MAX = 0.25

    evidence_parts = []
    triggered = False
    if queue_depth > BOTTLENECK_QUEUE_MAX:
        evidence_parts.append(f"queue_depth={queue_depth} (> {BOTTLENECK_QUEUE_MAX})")
        triggered = True
    if wait_time > BOTTLENECK_WAIT_MAX:
        evidence_parts.append(f"wait_time_avg={wait_time} (> {BOTTLENECK_WAIT_MAX})")
        triggered = True
    if failure_rate > BOTTLENECK_FAILURE_MAX:
        evidence_parts.append(f"failure_rate={failure_rate} (> {BOTTLENECK_FAILURE_MAX})")
        triggered = True

    if triggered:
        return Finding(
            id=f"bottleneck-{agent.get('id', '')}",
            kind="BOTTLENECK",
            subject=agent.get("name", agent.get("id", "")),
            evidence=tuple(evidence_parts),
        )
    return None


def _classify_cost_anomaly(cost: dict) -> Finding | None:
    """T29-05: cost > COST_ANOMALY_FACTOR x baseline -> anomaly finding."""
    current = cost.get("monthly_cost", 0)
    baseline = cost.get("baseline_monthly_cost", 0)
    agent_id = cost.get("agent_id", cost.get("id", ""))
    skill = cost.get("skill", "")

    if baseline > 0 and current > COST_ANOMALY_FACTOR * baseline:
        return Finding(
            id=f"cost-anomaly-{agent_id}",
            kind="COST_ANOMALY",
            subject=f"{agent_id} / {skill}" if skill else agent_id,
            evidence=_nonempty_evidence([
                f"monthly_cost={current}",
                f"baseline_monthly_cost={baseline}",
                f"factor={current / baseline:.2f}x (threshold: {COST_ANOMALY_FACTOR}x)",
            ]),
        )
    return None


def _classify_manual_process(proc: dict) -> Recommendation | None:
    """T29-06: frequency >= AUTOMATION_CANDIDATE_MIN -> AUTOMATE recommendation."""
    frequency = proc.get("frequency_per_month", 0)
    if frequency >= AUTOMATION_CANDIDATE_MIN:
        return Recommendation(
            id=f"automate-{proc.get('id', '')}",
            kind=AUTOMATE,
            subject=proc.get("name", proc.get("id", "")),
            status="ACTION",
            expected_benefit=f"Automate repeated manual process ({frequency}/month) to reduce effort.",
            evidence=_nonempty_evidence([
                f"frequency_per_month={frequency} (>= AUTOMATION_CANDIDATE_MIN={AUTOMATION_CANDIDATE_MIN})",
            ]),
        )
    return None


def _classify_protected_proposal(proposal: dict) -> Recommendation:
    """T29-07: architecture/security proposals -> status=PROPOSAL, never actioned."""
    return Recommendation(
        id=f"proposal-{proposal.get('id', '')}",
        kind=PROPOSAL,
        subject=proposal.get("name", proposal.get("id", "")),
        status=PROPOSAL,
        expected_benefit=proposal.get("expected_benefit", "Proposal under review; no action taken."),
        evidence=_nonempty_evidence(proposal.get("evidence", ["protected category"])),
    )

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_monthly_review(inputs: dict, now_iso: str) -> MonthlyReviewResult:
    """Run the monthly deep operating-system review pipeline.

    Parameters
    ----------
    inputs : dict
        Keys: projects[], automations[], agents[], costs[],
              manual_processes[], architecture_or_security_proposals[].
    now_iso : str
        ISO timestamp for the review run (input only, no clock reads).

    Returns
    -------
    MonthlyReviewResult
        Immutable, deterministic.  Recommendations only (no mutation).
    """
    projects = inputs.get("projects", [])
    automations = inputs.get("automations", [])
    agents = inputs.get("agents", [])
    costs = inputs.get("costs", [])
    manual_processes = inputs.get("manual_processes", [])
    proposals = inputs.get("architecture_or_security_proposals", [])

    recommendations: list[Recommendation] = []
    findings: list[Finding] = []

    # Projects: drain detection (T29-01).
    for p in projects:
        rec = _classify_project_drain(p)
        if rec is not None:
            recommendations.append(rec)

    # Automations: useful (T29-02) or noisy (T29-03).
    for a in automations:
        kind = a.get("kind", "")
        if kind == "useful":
            recommendations.append(_classify_automation_useful(a))
        elif kind == "noisy":
            recommendations.append(_classify_automation_noisy(a))

    # Agents: bottleneck detection (T29-04).
    for ag in agents:
        finding = _classify_bottleneck(ag)
        if finding is not None:
            findings.append(finding)

    # Costs: anomaly detection (T29-05).
    for c in costs:
        finding = _classify_cost_anomaly(c)
        if finding is not None:
            findings.append(finding)

    # Manual processes: automation candidate (T29-06).
    for mp in manual_processes:
        rec = _classify_manual_process(mp)
        if rec is not None:
            recommendations.append(rec)

    # Architecture/security proposals: protected (T29-07).
    for prop in proposals:
        recommendations.append(_classify_protected_proposal(prop))

    # Validate every recommendation has expected_benefit + evidence (T29-08).
    for rec in recommendations:
        _assert_recommendation_valid(rec)

    return MonthlyReviewResult(
        recommendations=tuple(recommendations),
        findings=tuple(findings),
    )