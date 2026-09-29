# QA T29 -- Monthly Operating-System Review tests.
# Stdlib only: unittest.  Plain ASCII. Deterministic.

from __future__ import annotations

import unittest

from tola.review.monthly_review import (
    MonthlyReviewResult,
    Recommendation,
    Finding,
    run_monthly_review,
    DRAIN_VALUE_MAX,
    DRAIN_TIME_MIN_HOURS,
    COST_ANOMALY_FACTOR,
    AUTOMATION_CANDIDATE_MIN,
    REDUCE_OR_SUNSET,
    REDUCE_OR_REMOVE,
    KEEP,
    AUTOMATE,
    PROPOSAL,
)

# ===========================================================================
# Fixtures
# ===========================================================================

NOW = "2026-09-29T21:23:00+01:00"


def make_project(
    pid: str,
    name: str = "",
    value_score: int = 3,
    time_spent_hours: float = 5.0,
    outcomes_count: int = 1,
) -> dict:
    return {
        "id": pid,
        "name": name or pid,
        "value_score": value_score,
        "time_spent_hours": time_spent_hours,
        "outcomes_count": outcomes_count,
    }


def make_automation(
    aid: str,
    name: str = "",
    kind: str = "useful",
    run_count: int = 10,
    value_signals: list | None = None,
    noise_signals: list | None = None,
) -> dict:
    a: dict = {
        "id": aid,
        "name": name or aid,
        "kind": kind,
        "run_count": run_count,
    }
    if value_signals is not None:
        a["value_signals"] = value_signals
    if noise_signals is not None:
        a["noise_signals"] = noise_signals
    return a


def make_agent(
    aid: str,
    name: str = "",
    queue_depth: int = 0,
    wait_time_avg: float = 0.0,
    failure_rate: float = 0.0,
) -> dict:
    return {
        "id": aid,
        "name": name or aid,
        "queue_depth": queue_depth,
        "wait_time_avg": wait_time_avg,
        "failure_rate": failure_rate,
    }


def make_cost(
    cid: str,
    agent_id: str = "",
    skill: str = "",
    monthly_cost: float = 100.0,
    baseline_monthly_cost: float = 100.0,
) -> dict:
    c: dict = {
        "id": cid,
        "agent_id": agent_id or cid,
        "skill": skill,
        "monthly_cost": monthly_cost,
        "baseline_monthly_cost": baseline_monthly_cost,
    }
    return c


def make_manual_process(
    pid: str,
    name: str = "",
    frequency_per_month: int = 1,
) -> dict:
    return {
        "id": pid,
        "name": name or pid,
        "frequency_per_month": frequency_per_month,
    }


def make_proposal(
    pid: str,
    name: str = "",
    expected_benefit: str = "Proposal under review.",
    evidence: list | None = None,
) -> dict:
    p: dict = {
        "id": pid,
        "name": name or pid,
        "expected_benefit": expected_benefit,
        "evidence": evidence or ["protected category"],
    }
    return p


# ===========================================================================
# T29-01: Low-value/high-time project identified as resource drain
# ===========================================================================

class TestT29_01_DrainIdentified(unittest.TestCase):
    """T29-01: project with value_score <= DRAIN_VALUE_MAX AND
    time_spent_hours >= DRAIN_TIME_MIN_HOURS -> REDUCE_OR_SUNSET."""

    def test_drain_identified(self):
        inputs = {
            "projects": [
                make_project("p1", "Low Value Project", value_score=1, time_spent_hours=15),
            ],
            "automations": [],
            "agents": [],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        recs = result.recommendations
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].kind, REDUCE_OR_SUNSET)
        self.assertEqual(recs[0].subject, "Low Value Project")
        self.assertIn("value_score=1", recs[0].evidence[0])
        self.assertIn("time_spent_hours=15", recs[0].evidence[1])


# ===========================================================================
# T29-02: Useful automation retained (KEEP, no removal rec)
# ===========================================================================

class TestT29_02_UsefulAutomationRetained(unittest.TestCase):
    """T29-02: useful automation -> KEEP recommendation, no removal."""

    def test_useful_retained_no_removal(self):
        inputs = {
            "projects": [],
            "automations": [
                make_automation("a1", "Helpful Bot", kind="useful", run_count=50,
                                value_signals=["saves 3h/week", "zero errors"]),
            ],
            "agents": [],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        recs = result.recommendations
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].kind, KEEP)
        self.assertNotIn(REDUCE_OR_REMOVE, [r.kind for r in recs])
        self.assertNotIn(REDUCE_OR_SUNSET, [r.kind for r in recs])


# ===========================================================================
# T29-03: Noisy/low-value automation flagged for reduction/removal
# ===========================================================================

class TestT29_03_NoisyAutomationFlagged(unittest.TestCase):
    """T29-03: noisy automation -> REDUCE_OR_REMOVE with evidence."""

    def test_noisy_flagged_with_evidence(self):
        inputs = {
            "projects": [],
            "automations": [
                make_automation("a2", "Noisy Logger", kind="noisy", run_count=200,
                                noise_signals=["spammy output", "high CPU", "no value"]),
            ],
            "agents": [],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        recs = result.recommendations
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].kind, REDUCE_OR_REMOVE)
        self.assertIn("run_count=200", recs[0].evidence[0])
        self.assertIn("noise_signal=spammy output", recs[0].evidence[1])


# ===========================================================================
# T29-04: Agent bottleneck detected from evidence
# ===========================================================================

class TestT29_04_BottleneckDetected(unittest.TestCase):
    """T29-04: agent with queue/wait/failure evidence beyond threshold -> finding."""

    def test_bottleneck_from_queue(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [
                make_agent("ag1", "Slow Agent", queue_depth=25, wait_time_avg=5.0, failure_rate=0.05),
            ],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        findings = result.findings
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "BOTTLENECK")
        self.assertIn("queue_depth=25", findings[0].evidence[0])

    def test_bottleneck_from_wait(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [
                make_agent("ag2", "Stalled Agent", queue_depth=3, wait_time_avg=60.0, failure_rate=0.05),
            ],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        findings = result.findings
        self.assertEqual(len(findings), 1)
        self.assertIn("wait_time_avg=60.0", findings[0].evidence[0])

    def test_bottleneck_from_failure(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [
                make_agent("ag3", "Flaky Agent", queue_depth=3, wait_time_avg=5.0, failure_rate=0.5),
            ],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        findings = result.findings
        self.assertEqual(len(findings), 1)
        self.assertIn("failure_rate=0.5", findings[0].evidence[0])

    def test_no_bottleneck_below_threshold(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [
                make_agent("ag4", "Healthy Agent", queue_depth=2, wait_time_avg=10.0, failure_rate=0.01),
            ],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        self.assertEqual(len(result.findings), 0)


# ===========================================================================
# T29-05: Cost anomaly detected with factor and both numbers
# ===========================================================================

class TestT29_05_CostAnomaly(unittest.TestCase):
    """T29-05: cost > COST_ANOMALY_FACTOR x baseline -> anomaly finding."""

    def test_cost_anomaly_with_factor(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [],
            "costs": [
                make_cost("c1", "agent-x", "embedding-skill", monthly_cost=600.0, baseline_monthly_cost=250.0),
            ],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        findings = result.findings
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "COST_ANOMALY")
        evidence_text = " ".join(findings[0].evidence)
        self.assertIn("monthly_cost=600.0", evidence_text)
        self.assertIn("baseline_monthly_cost=250.0", evidence_text)
        self.assertIn("2.40x", evidence_text)

    def test_no_anomaly_within_factor(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [],
            "costs": [
                make_cost("c2", "agent-y", "search-skill", monthly_cost=200.0, baseline_monthly_cost=250.0),
            ],
            "manual_processes": [],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        self.assertEqual(len(result.findings), 0)


# ===========================================================================
# T29-06: Repeated manual process -> automation candidate
# ===========================================================================

class TestT29_06_ManualProcessAutomationCandidate(unittest.TestCase):
    """T29-06: frequency >= AUTOMATION_CANDIDATE_MIN -> AUTOMATE recommendation."""

    def test_manual_process_automation_candidate(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [],
            "costs": [],
            "manual_processes": [
                make_manual_process("mp1", "Weekly Report Compilation", frequency_per_month=8),
            ],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        recs = result.recommendations
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].kind, AUTOMATE)
        self.assertIn("frequency_per_month=8", recs[0].evidence[0])

    def test_manual_process_below_threshold_no_rec(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [],
            "costs": [],
            "manual_processes": [
                make_manual_process("mp2", "Monthly Audit", frequency_per_month=2),
            ],
            "architecture_or_security_proposals": [],
        }
        result = run_monthly_review(inputs, NOW)
        self.assertEqual(len(result.recommendations), 0)


# ===========================================================================
# T29-07: Architecture/security proposal stays proposal, not action
# ===========================================================================

class TestT29_07_ProtectedProposal(unittest.TestCase):
    """T29-07: architecture/security proposals -> status=PROPOSAL, never actioned."""

    def test_protected_stays_proposal(self):
        inputs = {
            "projects": [],
            "automations": [],
            "agents": [],
            "costs": [],
            "manual_processes": [],
            "architecture_or_security_proposals": [
                make_proposal("arch-1", "Core Skill Restructure", expected_benefit="Better structure.",
                              evidence=["architecture change"]),
            ],
        }
        result = run_monthly_review(inputs, NOW)
        recs = result.recommendations
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].kind, PROPOSAL)
        self.assertEqual(recs[0].status, PROPOSAL)


# ===========================================================================
# T29-08: All recommendations carry expected_benefit + evidence
# ===========================================================================

class TestT29_08_AllRecommendationsHaveBenefitAndEvidence(unittest.TestCase):
    """T29-08: every recommendation has non-empty expected_benefit and evidence."""

    def test_all_recs_have_benefit_and_evidence(self):
        inputs = {
            "projects": [
                make_project("p1", "Drain Me", value_score=1, time_spent_hours=20),
            ],
            "automations": [
                make_automation("a1", "Good Bot", kind="useful", run_count=30),
                make_automation("a2", "Noisy Bot", kind="noisy", run_count=100,
                                noise_signals=["spam"]),
            ],
            "agents": [],
            "costs": [],
            "manual_processes": [
                make_manual_process("mp1", "Frequent Task", frequency_per_month=10),
            ],
            "architecture_or_security_proposals": [
                make_proposal("arch-1", "Security Upgrade"),
            ],
        }
        result = run_monthly_review(inputs, NOW)
        for rec in result.recommendations:
            self.assertTrue(rec.expected_benefit and rec.expected_benefit.strip(),
                            f"{rec.id} has empty expected_benefit")
            self.assertTrue(rec.evidence, f"{rec.id} has empty evidence")


# ===========================================================================
# Determinism
# ===========================================================================

class TestDeterminism(unittest.TestCase):
    """Same inputs produce identical results across runs."""

    def test_deterministic(self):
        inputs = {
            "projects": [
                make_project("p1", "Drain Me", value_score=1, time_spent_hours=20),
                make_project("p2", "Valued Project", value_score=4, time_spent_hours=3),
            ],
            "automations": [
                make_automation("a1", "Good Bot", kind="useful", run_count=30),
                make_automation("a2", "Noisy Bot", kind="noisy", run_count=100,
                                noise_signals=["spam", "cpu"]),
            ],
            "agents": [
                make_agent("ag1", "Bottleneck Agent", queue_depth=15, wait_time_avg=10.0, failure_rate=0.05),
            ],
            "costs": [
                make_cost("c1", "agent-x", "embedding-skill", monthly_cost=600.0, baseline_monthly_cost=250.0),
            ],
            "manual_processes": [
                make_manual_process("mp1", "Frequent Task", frequency_per_month=10),
            ],
            "architecture_or_security_proposals": [
                make_proposal("arch-1", "Security Upgrade"),
            ],
        }
        r1 = run_monthly_review(inputs, NOW)
        r2 = run_monthly_review(inputs, NOW)

        # Same recommendation count and order.
        self.assertEqual(len(r1.recommendations), len(r2.recommendations))
        self.assertEqual(len(r1.findings), len(r2.findings))

        for rec1, rec2 in zip(r1.recommendations, r2.recommendations):
            self.assertEqual(rec1.id, rec2.id)
            self.assertEqual(rec1.kind, rec2.kind)
            self.assertEqual(rec1.evidence, rec2.evidence)

        for f1, f2 in zip(r1.findings, r2.findings):
            self.assertEqual(f1.id, f2.id)
            self.assertEqual(f1.evidence, f2.evidence)


# ===========================================================================
# No mutation: result is recommendations only (no side effects)
# ===========================================================================

class TestNoMutation(unittest.TestCase):
    """Inputs are not mutated by run_monthly_review."""

    def test_inputs_unchanged(self):
        projects = [make_project("p1", "Drain Me", value_score=1, time_spent_hours=20)]
        automations = [make_automation("a1", "Good Bot", kind="useful", run_count=30)]
        agents = [make_agent("ag1", "Bottleneck", queue_depth=15)]
        costs = [make_cost("c1", "agent-x", "skill", monthly_cost=600.0, baseline_monthly_cost=250.0)]
        manual_processes = [make_manual_process("mp1", "Frequent", frequency_per_month=10)]
        proposals = [make_proposal("arch-1", "Security Upgrade")]

        inputs = {
            "projects": projects,
            "automations": automations,
            "agents": agents,
            "costs": costs,
            "manual_processes": manual_processes,
            "architecture_or_security_proposals": proposals,
        }

        # Snapshot inputs.
        import copy
        snapshot = copy.deepcopy(inputs)

        run_monthly_review(inputs, NOW)

        self.assertEqual(inputs, snapshot)


if __name__ == "__main__":
    unittest.main()