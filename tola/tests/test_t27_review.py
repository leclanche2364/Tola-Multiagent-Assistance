# QA T27 -- Weekly Executive Review
# Stdlib only.  Plain ASCII.  Deterministic.

from __future__ import annotations

import unittest

from tola.review.weekly import (
    WeeklyReview,
    WeekBriefing,
    build_weekly_briefing,
    run_weekly_review,
    MAX_NEXT_WEEK_PRIORITIES,
    BRIEFING_MAX_LINES,
)


# ===========================================================================
# Fixtures
# ===========================================================================

NOW = "2026-09-29T10:00:00"


def make_project(
    pid: str,
    name: str = "",
    status: str = "active",
    score: int = 0,
    deadline: str = "",
    risk: str = "",
    blocked_by: list | None = None,
    depends_on: list | None = None,
    owner: str = "unassigned",
) -> dict:
    p: dict = {
        "id": pid,
        "name": name or pid,
        "status": status,
        "owner": owner,
    }
    if deadline:
        p["deadline"] = deadline
    if risk:
        p["risk"] = risk
    if blocked_by:
        p["blocked_by"] = blocked_by
    if depends_on:
        p["depends_on"] = depends_on
    return p


def make_capacity(load: float = 0, overload: bool = False) -> dict:
    return {"load": load, "overload": overload}


def make_growth_opportunity(
    gid: str,
    name: str = "",
    material: bool = False,
    impact: str = "low",
    evidence: str = "",
) -> dict:
    return {
        "id": gid,
        "name": name or gid,
        "material": material,
        "impact": impact,
        "evidence": evidence,
    }


def make_scholar_obligation(
    sid: str,
    name: str = "",
    due_date: str = "",
    requirement: str = "",
) -> dict:
    return {
        "id": sid,
        "name": name or sid,
        "due_date": due_date,
        "requirement": requirement,
    }


def make_stalled(
    sid: str,
    label: str = "",
    status: str = "stalled",
    owner: str = "unassigned",
) -> dict:
    return {
        "id": sid,
        "label": label or sid,
        "status": status,
        "owner": owner,
    }


def make_experiment(
    eid: str,
    name: str = "",
    status: str = "new",
    awaiting_action: bool = True,
    owner: str = "unassigned",
) -> dict:
    return {
        "id": eid,
        "name": name or eid,
        "status": status,
        "awaiting_action": awaiting_action,
        "owner": owner,
    }


def make_decision(
    did: str,
    label: str = "",
    status: str = "open",
    awaiting_action: bool = True,
    owner: str = "unassigned",
) -> dict:
    return {
        "id": did,
        "label": label or did,
        "status": status,
        "awaiting_action": awaiting_action,
        "owner": owner,
    }


def make_risk(
    rid: str,
    label: str = "",
    status: str = "new",
    severity: str = "medium",
) -> dict:
    return {
        "id": rid,
        "label": label or rid,
        "status": status,
        "severity": severity,
    }


def make_deferred(
    did: str,
    deferred: bool = True,
    dormant_reason: str = "low priority",
    review_after: str = "",
    revive_reason: str = "",
) -> dict:
    d: dict = {
        "id": did,
        "deferred": deferred,
        "dormant_reason": dormant_reason,
    }
    if review_after:
        d["review_after"] = review_after
    if revive_reason:
        d["revive_reason"] = revive_reason
    return d


# ===========================================================================
# T27-01: Multiple projects -> coherent portfolio priorities
# ===========================================================================

class TestT27_01_CoherentPriorities(unittest.TestCase):
    """T27-01: Multiple projects produce deterministic ranked priorities."""

    def test_multi_project_ranked_by_materiality(self):
        inputs = {
            "projects": [
                make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P2", "Beta", status="active", risk="low", deadline="2026-12-01"),
                make_project("P3", "Gamma", status="stalled", risk="medium", deadline="2026-10-05"),
            ],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        # P1 is blocked+high risk+near deadline -> highest score.
        # P3 is stalled+medium risk+near deadline -> second.
        # P2 is active+low risk+far deadline -> third.
        self.assertEqual(len(review.portfolio_priorities), 3)
        self.assertEqual(review.portfolio_priorities[0]["id"], "P1")
        self.assertEqual(review.portfolio_priorities[1]["id"], "P3")
        self.assertEqual(review.portfolio_priorities[2]["id"], "P2")

    def test_stable_tiebreak_by_id(self):
        # Two projects with identical scores -> tiebreak by id.
        inputs = {
            "projects": [
                make_project("P2", "Beta", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01"),
            ],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(review.portfolio_priorities[0]["id"], "P1")
        self.assertEqual(review.portfolio_priorities[1]["id"], "P2")

    def test_determinism(self):
        inputs = {
            "projects": [
                make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P2", "Beta", status="active", risk="low"),
            ],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        r1 = run_weekly_review(inputs, NOW)
        r2 = run_weekly_review(inputs, NOW)
        self.assertEqual(r1.portfolio_priorities, r2.portfolio_priorities)
        self.assertEqual(r1.next_week_priorities, r2.next_week_priorities)


# ===========================================================================
# T27-02: Rhythm capacity incorporated
# ===========================================================================

class TestT27_02_Capacity(unittest.TestCase):
    """T27-02: Overloaded capacity produces capacity_request entries."""

    def test_overload_creates_capacity_request(self):
        inputs = {
            "projects": [make_project("P1", "Alpha")],
            "capacity": make_capacity(load=120, overload=True),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.capacity_requests), 1)
        self.assertEqual(review.capacity_requests[0]["kind"], "CAPACITY_REQUEST")

    def test_no_overload_no_capacity_request(self):
        inputs = {
            "projects": [make_project("P1", "Alpha")],
            "capacity": make_capacity(load=50, overload=False),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.capacity_requests), 0)

    def test_high_load_overload_threshold(self):
        inputs = {
            "projects": [make_project("P1", "Alpha")],
            "capacity": make_capacity(load=101, overload=False),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.capacity_requests), 1)


# ===========================================================================
# T27-03: Material Growth opportunity incorporated
# ===========================================================================

class TestT27_03_GrowthOpportunity(unittest.TestCase):
    """T27-03: Material growth opportunities are incorporated; immaterial ones are not."""

    def test_material_growth_incorporated(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [
                make_growth_opportunity("G1", "Upsell flow", material=True, impact="high"),
            ],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.growth_opportunities), 1)
        self.assertEqual(review.growth_opportunities[0]["id"], "G1")

    def test_immaterial_growth_not_incorporated(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [
                make_growth_opportunity("G2", "Minor tweak", material=False, impact="low"),
            ],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.growth_opportunities), 0)

    def test_material_but_low_impact_not_incorporated(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [
                make_growth_opportunity("G3", "Low impact", material=True, impact="low"),
            ],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.growth_opportunities), 0)


# ===========================================================================
# T27-04: Scholar obligations incorporated
# ===========================================================================

class TestT27_04_ScholarObligations(unittest.TestCase):
    """T27-04: Scholar obligations with near-term deadlines are incorporated."""

    def test_deadline_driven_scholar_incorporated(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [
                make_scholar_obligation("S1", "Curriculum review", due_date="2026-10-05"),
            ],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.scholar_obligations), 1)
        self.assertEqual(review.scholar_obligations[0]["id"], "S1")

    def test_far_future_scholar_not_incorporated(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [
                make_scholar_obligation("S2", "Annual review", due_date="2027-03-01"),
            ],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.scholar_obligations), 0)

    def test_scholar_no_deadline_not_incorporated(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [
                make_scholar_obligation("S3", "Ongoing reading"),
            ],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.scholar_obligations), 0)


# ===========================================================================
# T27-05: Stalled work surfaced
# ===========================================================================

class TestT27_05_StalledWork(unittest.TestCase):
    """T27-05: Stalled work is surfaced in the review."""

    def test_stalled_task_surfaced(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [make_stalled("T1", "Write report")],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.stalled_work), 1)
        self.assertEqual(review.stalled_work[0]["id"], "T1")
        self.assertEqual(review.stalled_work[0]["follow_up"], "STALLED_FOLLOW_UP")

    def test_multiple_stalled_sorted_by_id(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [
                make_stalled("T2", "Task B"),
                make_stalled("T1", "Task A"),
            ],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.stalled_work), 2)
        self.assertEqual(review.stalled_work[0]["id"], "T1")
        self.assertEqual(review.stalled_work[1]["id"], "T2")

    def test_no_stalled_work_empty(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.stalled_work), 0)


# ===========================================================================
# T27-06: Experiments/decisions awaiting action surfaced
# ===========================================================================

class TestT27_06_ExperimentsDecisionsAwaiting(unittest.TestCase):
    """T27-06: Experiments and decisions awaiting action are surfaced."""

    def test_experiment_awaiting_action_surfaced(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [make_experiment("E1", "A/B test", status="new")],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.experiments_awaiting), 1)
        self.assertEqual(review.experiments_awaiting[0]["id"], "E1")

    def test_decision_awaiting_action_surfaced(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [make_decision("D1", "Approve budget", status="open")],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.decisions_awaiting), 1)
        self.assertEqual(review.decisions_awaiting[0]["id"], "D1")

    def test_experiment_not_awaiting_not_surfaced(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [make_experiment("E2", "Done test", status="complete", awaiting_action=False)],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.experiments_awaiting), 0)

    def test_decision_pending_status_surfaced(self):
        inputs = {
            "projects": [],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [make_decision("D2", "Choose vendor", status="pending")],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertEqual(len(review.decisions_awaiting), 1)


# ===========================================================================
# T27-07: Next actions have owners/follow-ups
# ===========================================================================

class TestT27_07_OwnersFollowUps(unittest.TestCase):
    """T27-07: Every next action has owner and follow_up type."""

    def test_every_follow_up_has_owner(self):
        inputs = {
            "projects": [
                make_project("P1", "Alpha", owner="tola-build"),
                make_project("P2", "Beta", owner="tola-growth"),
            ],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        for fu in review.follow_ups:
            self.assertIn("owner", fu, f"Follow-up missing owner: {fu}")
            self.assertIn("follow_up", fu, f"Follow-up missing follow_up type: {fu}")
            self.assertTrue(fu["owner"], f"Follow-up has empty owner: {fu}")

    def test_follow_up_types_present(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", owner="team-a")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [make_stalled("T1", "Task", owner="team-b")],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        types = set(fu["follow_up"] for fu in review.follow_ups)
        self.assertIn("NEXT_ACTION", types)
        self.assertIn("STALLED_FOLLOW_UP", types)

    def test_no_next_action_lacks_owner(self):
        # Explicit check: no next action lacks owner.
        inputs = {
            "projects": [make_project("P1", "Alpha")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        for fu in review.follow_ups:
            self.assertTrue(fu.get("owner"), f"Owner missing for follow-up: {fu}")


# ===========================================================================
# T27-08: User briefing concise and understandable
# ===========================================================================

class TestT27_08_BriefingConcise(unittest.TestCase):
    """T27-08: Briefing is concise (<= max lines, no empty lines)."""

    def test_briefing_within_max_lines(self):
        inputs = {
            "projects": [
                make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01"),
            ],
            "capacity": make_capacity(load=120, overload=True),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        briefing = build_weekly_briefing(review)
        self.assertLessEqual(len(briefing.lines), BRIEFING_MAX_LINES)

    def test_briefing_no_empty_lines(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        briefing = build_weekly_briefing(review)
        for line in briefing.lines:
            self.assertTrue(line.strip(), f"Empty line found in briefing: {line!r}")

    def test_briefing_plain_ascii(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        briefing = build_weekly_briefing(review)
        for line in briefing.lines:
            for ch in line:
                self.assertTrue(
                    ord(ch) < 128,
                    f"Non-ASCII character {ch!r} in briefing line: {line!r}",
                )

    def test_briefing_determinism(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        b1 = build_weekly_briefing(run_weekly_review(inputs, NOW))
        b2 = build_weekly_briefing(run_weekly_review(inputs, NOW))
        self.assertEqual(b1.lines, b2.lines)


# ===========================================================================
# T27-09: Dormant deferred work not revived without reason
# ===========================================================================

class TestT27_09_DormantGuard(unittest.TestCase):
    """T27-09: Deferred items excluded unless revived with revive_reason."""

    def test_dormant_item_absent_from_priorities(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="active")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [make_deferred("P1", deferred=True, dormant_reason="low priority")],
        }
        review = run_weekly_review(inputs, NOW)
        # P1 should be excluded from next_week_priorities.
        priority_ids = [p["id"] for p in review.next_week_priorities]
        self.assertNotIn("P1", priority_ids)

    def test_dormant_item_absent_from_follow_ups(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="active")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [make_deferred("P1", deferred=True, dormant_reason="low priority")],
        }
        review = run_weekly_review(inputs, NOW)
        # P1 should not appear in follow_ups as NEXT_ACTION.
        for fu in review.follow_ups:
            if fu["id"] == "P1":
                self.assertNotEqual(fu["follow_up"], "NEXT_ACTION")

    def test_revived_with_reason_present(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="active")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [
                make_deferred("P1", deferred=True, dormant_reason="low priority", revive_reason="Strategic shift")
            ],
        }
        review = run_weekly_review(inputs, NOW)
        # P1 should appear in next_week_priorities.
        priority_ids = [p["id"] for p in review.next_week_priorities]
        self.assertIn("P1", priority_ids)
        # Follow-up should be flagged REVIVED_WITH_REASON.
        revived_fus = [fu for fu in review.follow_ups if fu["id"] == "P1" and fu["follow_up"] == "REVIVED_WITH_REASON"]
        self.assertEqual(len(revived_fus), 1)

    def test_dormant_without_revive_reason_excluded(self):
        # Same item with deferred=True but no revive_reason -> excluded.
        inputs = {
            "projects": [make_project("P1", "Alpha", status="active")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [make_deferred("P1", deferred=True, dormant_reason="low priority")],
        }
        review = run_weekly_review(inputs, NOW)
        priority_ids = [p["id"] for p in review.next_week_priorities]
        self.assertNotIn("P1", priority_ids)


# ===========================================================================
# Determinism: full pipeline
# ===========================================================================

class TestT27_Determinism(unittest.TestCase):
    """Full pipeline determinism."""

    def test_determinism_full_run(self):
        inputs = {
            "projects": [
                make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P2", "Beta", status="active", risk="low"),
                make_project("P3", "Gamma", status="stalled", risk="medium", deadline="2026-10-05"),
            ],
            "capacity": make_capacity(load=120, overload=True),
            "growth_opportunities": [
                make_growth_opportunity("G1", "Upsell", material=True, impact="high"),
                make_growth_opportunity("G2", "Low", material=False, impact="low"),
            ],
            "scholar_obligations": [
                make_scholar_obligation("S1", "Review", due_date="2026-10-05"),
                make_scholar_obligation("S2", "Long-term", due_date="2027-03-01"),
            ],
            "stalled": [make_stalled("T1", "Write report", owner="team-a")],
            "experiments": [make_experiment("E1", "A/B test", status="new", owner="team-b")],
            "decisions": [make_decision("D1", "Approve", status="open", owner="team-c")],
            "risks": [make_risk("R1", "Server down", status="new", severity="high")],
            "deferred": [
                make_deferred("P2", deferred=True, dormant_reason="low priority"),
            ],
        }
        r1 = run_weekly_review(inputs, NOW)
        r2 = run_weekly_review(inputs, NOW)
        self.assertEqual(r1.portfolio_priorities, r2.portfolio_priorities)
        self.assertEqual(r1.capacity_requests, r2.capacity_requests)
        self.assertEqual(r1.growth_opportunities, r2.growth_opportunities)
        self.assertEqual(r1.scholar_obligations, r2.scholar_obligations)
        self.assertEqual(r1.stalled_work, r2.stalled_work)
        self.assertEqual(r1.experiments_awaiting, r2.experiments_awaiting)
        self.assertEqual(r1.decisions_awaiting, r2.decisions_awaiting)
        self.assertEqual(r1.risks, r2.risks)
        self.assertEqual(r1.next_week_priorities, r2.next_week_priorities)
        self.assertEqual(r1.follow_ups, r2.follow_ups)

    def test_next_week_priorities_capped(self):
        # More than MAX_NEXT_WEEK_PRIORITIES active projects.
        projects = [
            make_project(f"P{i}", f"Project {i}", status="active", deadline="2026-10-01")
            for i in range(1, 8)
        ]
        inputs = {
            "projects": projects,
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertLessEqual(len(review.next_week_priorities), MAX_NEXT_WEEK_PRIORITIES)

    def test_capped_priorities_ordered_by_rank(self):
        inputs = {
            "projects": [
                make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P2", "Beta", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P3", "Gamma", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P4", "Delta", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P5", "Epsilon", status="blocked", risk="high", deadline="2026-10-01"),
                make_project("P6", "Zeta", status="blocked", risk="high", deadline="2026-10-01"),
            ],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        self.assertLessEqual(len(review.next_week_priorities), MAX_NEXT_WEEK_PRIORITIES)
        # Ranks should be 1..5.
        ranks = [p["rank"] for p in review.next_week_priorities]
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))


# ===========================================================================
# Plain ASCII check
# ===========================================================================

class TestT27_PlainAscii(unittest.TestCase):
    """All output strings are plain ASCII."""

    def test_weekly_review_plain_ascii(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        # Check all string values in the review.
        for fu in review.follow_ups:
            for key, val in fu.items():
                if isinstance(val, str):
                    for ch in val:
                        self.assertTrue(ord(ch) < 128, f"Non-ASCII in follow-up {key}: {ch!r}")

    def test_briefing_plain_ascii(self):
        inputs = {
            "projects": [make_project("P1", "Alpha", status="blocked", risk="high", deadline="2026-10-01")],
            "capacity": make_capacity(load=50),
            "growth_opportunities": [],
            "scholar_obligations": [],
            "stalled": [],
            "experiments": [],
            "decisions": [],
            "risks": [],
            "deferred": [],
        }
        review = run_weekly_review(inputs, NOW)
        briefing = build_weekly_briefing(review)
        for line in briefing.lines:
            for ch in line:
                self.assertTrue(ord(ch) < 128, f"Non-ASCII in briefing: {ch!r}")


if __name__ == "__main__":
    unittest.main()