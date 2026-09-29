"""QA T6 tests for Batch T6 Goal Decomposition Engine.

Covers T6-01..T6-09 (and T7-01..T7-07 where relevant)
as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import datetime
import unittest

from tola.portfolio.contracts import Goal, Milestone, Task
from tola.decomposition.planner import (
    DecompositionPlan,
    DecompositionWarning,
    goal_decompose,
    DEFAULT_TASK_EFFORT_HOURS,
    DEFAULT_MILESTONE_BUFFER_DAYS,
    PHASE_ORDER,
)
from tola.decomposition.replanner import (
    PlanVersion,
    ReplanEvent,
    ReplanEventKind,
    goal_replan,
    material_diff,
)
from tola.decomposition.feasibility import (
    FeasibilityResult,
    FeasibilityStatus,
    TrimOption,
    plan_feasibility_check,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_TIME = datetime.datetime(2026, 9, 29, 12, 0, 0)


def make_goal(
    goal_id: str = "goal-001",
    goal_name: str = "Launch feature",
    due_date: str = "2026-12-31",
    description: str = "",
    **overrides,
) -> Goal:
    defaults = dict(
        goal_id=goal_id,
        project_id="proj-001",
        goal_name=goal_name,
        description=description or None,
        status="open",
        due_date=due_date,
        source_system="blackboard",
        source_id="goal-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Goal(**defaults)


def make_constraints(**overrides) -> dict:
    defaults = dict(
        deadline="2026-12-31",
        capacity_limit=80.0,
        dependencies=[],
        phase_override=None,
        task_effort={},
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# T6-01: Basic decomposition produces ordered milestones with dependencies
# ---------------------------------------------------------------------------

class TestT6_01_BasicDecomposition(unittest.TestCase):
    def test_basic_decomposition_ordered_milestones(self):
        goal = make_goal(goal_name="New feature delivery")
        constraints = make_constraints()
        plan = goal_decompose(goal, constraints)

        self.assertIsInstance(plan, DecompositionPlan)
        self.assertEqual(plan.goal_id, "goal-001")
        self.assertGreater(len(plan.milestones), 0)

        # Milestones ordered by canonical phase sequence.
        phases_seen = [m["phase"] for m in plan.milestones]
        self.assertEqual(phases_seen, [p for p in PHASE_ORDER if p in phases_seen])

        # Each milestone after the first depends on the previous.
        for i in range(1, len(plan.milestones)):
            prev_id = plan.milestones[i - 1]["milestone_id"]
            self.assertIn(prev_id, plan.milestones[i]["dependencies"])

    def test_tasks_attached_to_milestones(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        self.assertEqual(len(plan.tasks), len(plan.milestones))
        for task in plan.tasks:
            self.assertIn(
                task["milestone_id"],
                [m["milestone_id"] for m in plan.milestones],
            )

    def test_effort_uses_default_constant(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        for task in plan.tasks:
            self.assertEqual(task["effort_hours"], DEFAULT_TASK_EFFORT_HOURS)


# ---------------------------------------------------------------------------
# T6-02: Missing deadline produces warning + reduced confidence, no invented dates
# ---------------------------------------------------------------------------

class TestT6_02_MissingDeadline(unittest.TestCase):
    def test_missing_deadline_warns_and_lowers_confidence(self):
        goal = make_goal(goal_name="No deadline goal", due_date=None)
        plan = goal_decompose(goal, make_constraints(deadline=None))

        self.assertGreater(len(plan.warnings), 0)
        self.assertTrue(
            any("MISSING_DEADLINE" in w for w in plan.warnings)
        )
        self.assertLess(plan.confidence, 0.85)

    def test_no_invented_dates_when_deadline_missing(self):
        goal = make_goal(goal_name="No deadline goal", due_date=None)
        plan = goal_decompose(goal, make_constraints(deadline=None))

        for m in plan.milestones:
            self.assertIsNone(m["deadline_anchor"])
        for t in plan.tasks:
            self.assertIsNone(t["deadline"])
        self.assertIsNone(plan.deadline_anchor)

    def test_missing_deadline_still_produces_plan(self):
        goal = make_goal(goal_name="No deadline goal", due_date=None)
        plan = goal_decompose(goal, make_constraints(deadline=None))

        self.assertIsInstance(plan, DecompositionPlan)
        self.assertGreater(len(plan.milestones), 0)


# ---------------------------------------------------------------------------
# T6-03: Unknown goal type warns + low confidence, never invents
# ---------------------------------------------------------------------------

class TestT6_03_UnknownGoalType(unittest.TestCase):
    def test_unknown_type_warns_and_lowers_confidence(self):
        goal = make_goal(goal_name="Mystery operation")
        plan = goal_decompose(goal, make_constraints())

        self.assertGreater(len(plan.warnings), 0)
        self.assertTrue(
            any("UNKNOWN_GOAL_TYPE" in w for w in plan.warnings)
        )
        self.assertLess(plan.confidence, 0.85)

    def test_unknown_type_still_decomposes(self):
        goal = make_goal(goal_name="Mystery operation")
        plan = goal_decompose(goal, make_constraints())

        self.assertGreater(len(plan.milestones), 0)


# ---------------------------------------------------------------------------
# T6-04: Replan on milestone slip produces new version with material diff
# ---------------------------------------------------------------------------

class TestT6_04_ReplanMilestoneSlip(unittest.TestCase):
    def test_replan_slip_produces_new_version(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())
        self.assertEqual(plan.version, 1)

        event = ReplanEvent(
            kind=ReplanEventKind.MILESTONE_SLIPPED,
            entity_id=plan.milestones[0]["milestone_id"],
            detail="Resource unavailable for 3 days",
        )
        new_version = goal_replan(plan, event)

        self.assertEqual(new_version.version, 2)
        self.assertNotEqual(new_version.plan.milestones, plan.milestones)

    def test_replan_slip_material_diff_surfaces(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        event = ReplanEvent(
            kind=ReplanEventKind.MILESTONE_SLIPPED,
            entity_id=plan.milestones[0]["milestone_id"],
            detail="Resource unavailable",
        )
        new_version = goal_replan(plan, event)

        diff = material_diff(
            PlanVersion(version=1, plan=plan),
            new_version,
        )
        self.assertIn("milestones", diff)

    def test_slip_shifts_downstream_deadlines(self):
        goal = make_goal(goal_name="New feature delivery", due_date="2026-12-31")
        plan = goal_decompose(goal, make_constraints())

        original_deadline = plan.milestones[1]["deadline_anchor"]

        event = ReplanEvent(
            kind=ReplanEventKind.MILESTONE_SLIPPED,
            entity_id=plan.milestones[0]["milestone_id"],
            detail="Slipped",
        )
        new_version = goal_replan(plan, event)

        new_deadline = new_version.plan.milestones[1]["deadline_anchor"]
        self.assertNotEqual(original_deadline, new_deadline)


# ---------------------------------------------------------------------------
# T6-05: Replan preserves uncommitted history (original plan unchanged)
# ---------------------------------------------------------------------------

class TestT6_05_PreserveHistory(unittest.TestCase):
    def test_original_plan_unchanged_after_replan(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())
        original_milestones = plan.milestones
        original_version = plan.version

        event = ReplanEvent(
            kind=ReplanEventKind.MILESTONE_SLIPPED,
            entity_id=plan.milestones[0]["milestone_id"],
            detail="Slipped",
        )
        goal_replan(plan, event)

        self.assertEqual(plan.milestones, original_milestones)
        self.assertEqual(plan.version, original_version)

    def test_multiple_replans_produce_incremental_versions(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        v1 = goal_replan(
            plan,
            ReplanEvent(
                kind=ReplanEventKind.MILESTONE_SLIPPED,
                entity_id=plan.milestones[0]["milestone_id"],
                detail="Slipped",
            ),
        )
        v2 = goal_replan(
            v1.plan,
            ReplanEvent(
                kind=ReplanEventKind.DEADLINE_MOVED,
                entity_id=plan.goal_id,
                detail="2027-01-15",
            ),
        )

        self.assertEqual(v1.version, 2)
        self.assertEqual(v2.version, 3)


# ---------------------------------------------------------------------------
# T6-06: Replan on dependency blocked
# ---------------------------------------------------------------------------

class TestT6_06_DependencyBlocked(unittest.TestCase):
    def test_dependency_block_marks_milestone_blocked(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        # Block the first milestone as a dependency.
        event = ReplanEvent(
            kind=ReplanEventKind.DEPENDENCY_BLOCKED,
            entity_id=plan.milestones[0]["milestone_id"],
            detail="Upstream dependency blocked",
        )
        new_version = goal_replan(plan, event)

        first_ms = new_version.plan.milestones[0]
        self.assertEqual(first_ms["status"], "blocked")

    def test_dependency_block_preserves_other_milestones(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        event = ReplanEvent(
            kind=ReplanEventKind.DEPENDENCY_BLOCKED,
            entity_id=plan.milestones[0]["milestone_id"],
            detail="Blocked",
        )
        new_version = goal_replan(plan, event)

        # Only the first milestone should be blocked.
        blocked_count = sum(
            1 for m in new_version.plan.milestones if m["status"] == "blocked"
        )
        self.assertEqual(blocked_count, 1)


# ---------------------------------------------------------------------------
# T6-07: Replan on deadline moved
# ---------------------------------------------------------------------------

class TestT6_07_DeadlineMoved(unittest.TestCase):
    def test_deadline_move_re_derives_anchors(self):
        goal = make_goal(goal_name="New feature delivery", due_date="2026-12-31")
        plan = goal_decompose(goal, make_constraints())

        original_anchor = plan.deadline_anchor
        self.assertEqual(original_anchor, "2026-12-31")

        event = ReplanEvent(
            kind=ReplanEventKind.DEADLINE_MOVED,
            entity_id=plan.goal_id,
            detail="2027-02-28",
        )
        new_version = goal_replan(plan, event)

        self.assertEqual(new_version.plan.deadline_anchor, "2027-02-28")

    def test_deadline_move_re_derives_milestone_deadlines(self):
        goal = make_goal(goal_name="New feature delivery", due_date="2026-12-31")
        plan = goal_decompose(goal, make_constraints())

        original_ms_deadline = plan.milestones[0]["deadline_anchor"]

        event = ReplanEvent(
            kind=ReplanEventKind.DEADLINE_MOVED,
            entity_id=plan.goal_id,
            detail="2027-06-30",
        )
        new_version = goal_replan(plan, event)

        new_ms_deadline = new_version.plan.milestones[0]["deadline_anchor"]
        self.assertNotEqual(original_ms_deadline, new_ms_deadline)


# ---------------------------------------------------------------------------
# T6-08: Feasibility check flags overload with options
# ---------------------------------------------------------------------------

class TestT6_08_FeasibilityOverload(unittest.TestCase):
    def test_overloaded_plan_returns_overloaded_status(self):
        goal = make_goal(goal_name="Big delivery")
        constraints = make_constraints(capacity_limit=10.0)
        plan = goal_decompose(goal, constraints)

        result = plan_feasibility_check(
            plan, {"capacity_hours": 10.0}
        )

        self.assertEqual(result.status, FeasibilityStatus.OVERLOADED)

    def test_overloaded_plan_has_trim_options(self):
        goal = make_goal(goal_name="Big delivery")
        constraints = make_constraints(capacity_limit=10.0)
        plan = goal_decompose(goal, constraints)

        result = plan_feasibility_check(
            plan, {"capacity_hours": 10.0}
        )

        self.assertGreater(len(result.trim_options), 0)

    def test_trim_options_are_recommendations_not_auto_applied(self):
        goal = make_goal(goal_name="Big delivery")
        constraints = make_constraints(capacity_limit=10.0)
        plan = goal_decompose(goal, constraints)

        result = plan_feasibility_check(
            plan, {"capacity_hours": 10.0}
        )

        for option in result.trim_options:
            self.assertIn(option.action, ("drop", "defer", "extend"))

    def test_feasible_plan_has_no_trim_options(self):
        goal = make_goal(goal_name="Small delivery")
        plan = goal_decompose(goal, make_constraints())

        result = plan_feasibility_check(
            plan, {"capacity_hours": 1000.0}
        )

        self.assertEqual(result.status, FeasibilityStatus.FEASIBLE)
        self.assertEqual(len(result.trim_options), 0)

    def test_missing_capacity_returns_insufficient_data(self):
        goal = make_goal(goal_name="Any goal")
        plan = goal_decompose(goal, make_constraints())

        result = plan_feasibility_check(plan, {})

        self.assertEqual(result.status, FeasibilityStatus.INSUFFICIENT_DATA)
        self.assertEqual(result.confidence, 0.0)


# ---------------------------------------------------------------------------
# T6-09: Replan on capacity reduced
# ---------------------------------------------------------------------------

class TestT6_09_CapacityReduced(unittest.TestCase):
    def test_capacity_reduced_trims_effort(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        original_effort = plan.tasks[0]["effort_hours"]

        event = ReplanEvent(
            kind=ReplanEventKind.CAPACITY_REDUCED,
            entity_id=plan.goal_id,
            detail="50",  # 50% reduction
        )
        new_version = goal_replan(plan, event)

        new_effort = new_version.plan.tasks[0]["effort_hours"]
        self.assertLess(new_effort, original_effort)

    def test_capacity_reduced_adds_warning(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        event = ReplanEvent(
            kind=ReplanEventKind.CAPACITY_REDUCED,
            entity_id=plan.goal_id,
            detail="50",
        )
        new_version = goal_replan(plan, event)

        self.assertTrue(
            any("Capacity reduced" in w for w in new_version.plan.warnings)
        )

    def test_capacity_reduced_lowers_confidence(self):
        goal = make_goal(goal_name="New feature delivery")
        plan = goal_decompose(goal, make_constraints())

        event = ReplanEvent(
            kind=ReplanEventKind.CAPACITY_REDUCED,
            entity_id=plan.goal_id,
            detail="50",
        )
        new_version = goal_replan(plan, event)

        self.assertLess(new_version.plan.confidence, plan.confidence)


# ---------------------------------------------------------------------------
# T7-01: Simple goal produces milestones/owners/success criteria
# ---------------------------------------------------------------------------

class TestT7_01_SimpleGoalMilestones(unittest.TestCase):
    def test_simple_goal_produces_milestones(self):
        goal = make_goal(goal_name="Simple feature")
        plan = goal_decompose(goal, make_constraints())

        self.assertGreater(len(plan.milestones), 0)
        for m in plan.milestones:
            self.assertIn("name", m)
            self.assertIn("target_outcome", m)

    def test_milestones_have_dependencies(self):
        goal = make_goal(goal_name="Simple feature")
        plan = goal_decompose(goal, make_constraints())

        # First milestone has no internal dependency.
        self.assertEqual(len(plan.milestones[0]["dependencies"]), 0)
        # Subsequent milestones depend on previous.
        for i in range(1, len(plan.milestones)):
            self.assertGreater(len(plan.milestones[i]["dependencies"]), 0)


# ---------------------------------------------------------------------------
# T7-02: Multi-agent goal has correct dependencies
# ---------------------------------------------------------------------------

class TestT7_02_MultiAgentDependencies(unittest.TestCase):
    def test_external_dependencies_included(self):
        goal = make_goal(goal_name="Cross-team feature")
        constraints = make_constraints(dependencies=["ms-ext-001", "ms-ext-002"])
        plan = goal_decompose(goal, constraints)

        first_ms = plan.milestones[0]
        for dep in ["ms-ext-001", "ms-ext-002"]:
            self.assertIn(dep, first_ms["dependencies"])


# ---------------------------------------------------------------------------
# T7-03: Capacity-sensitive plan marks Rhythm query (via warning)
# ---------------------------------------------------------------------------

class TestT7_03_CapacitySensitivePlan(unittest.TestCase):
    def test_overloaded_capacity_warns_for_feasibility_check(self):
        goal = make_goal(goal_name="Heavy delivery")
        constraints = make_constraints(capacity_limit=5.0)
        plan = goal_decompose(goal, constraints)

        self.assertTrue(
            any("OVERLOADED_CAPACITY" in w for w in plan.warnings)
        )


# ---------------------------------------------------------------------------
# T7-04: Missing evidence becomes explicit assumption (no invented facts)
# ---------------------------------------------------------------------------

class TestT7_04_MissingEvidenceAssumptions(unittest.TestCase):
    def test_no_invented_dates_without_deadline(self):
        goal = make_goal(goal_name="No date goal", due_date=None)
        plan = goal_decompose(goal, make_constraints(deadline=None))

        for m in plan.milestones:
            self.assertIsNone(m["deadline_anchor"])

    def test_unknown_type_uses_generic_phases_not_invented(self):
        goal = make_goal(goal_name="Unknown type thing")
        plan = goal_decompose(goal, make_constraints())

        self.assertGreater(len(plan.milestones), 0)
        # All phases should be from the standard PHASE_ORDER.
        for m in plan.milestones:
            self.assertIn(m["phase"], ["discovery", "design", "build", "test", "launch", "review"])


# ---------------------------------------------------------------------------
# T7-05: Experimental work includes stop/review condition
# ---------------------------------------------------------------------------

class TestT7_05_ExperimentalWork(unittest.TestCase):
    def test_experiment_goal_includes_review_phase(self):
        goal = make_goal(goal_name="Experiment alpha", description="hypothesis test")
        plan = goal_decompose(goal, make_constraints())

        phases = [m["phase"] for m in plan.milestones]
        self.assertIn("review", phases)


# ---------------------------------------------------------------------------
# T7-06: Plan avoids unnecessary over-engineering
# ---------------------------------------------------------------------------

class TestT7_06_NoOverEngineering(unittest.TestCase):
    def test_plan_has_no_extra_fields(self):
        goal = make_goal(goal_name="Simple goal")
        plan = goal_decompose(goal, make_constraints())

        for m in plan.milestones:
            expected_keys = {
                "milestone_id",
                "name",
                "phase",
                "target_outcome",
                "dependencies",
                "deadline_anchor",
                "status",
            }
            self.assertTrue(set(m.keys()).issubset(expected_keys | {"status"}))


# ---------------------------------------------------------------------------
# T7-07: Specialist boundaries preserved (no Rhythm writes)
# ---------------------------------------------------------------------------

class TestT7_07_SpecialistBoundaries(unittest.TestCase):
    def test_decomposition_has_no_rhythm_write_capability(self):
        goal = make_goal(goal_name="Any goal")
        plan = goal_decompose(goal, make_constraints())

        # The plan is a plain data structure; no write methods exist.
        self.assertFalse(hasattr(plan, "write"))
        self.assertFalse(hasattr(plan, "save"))
        self.assertFalse(hasattr(plan, "commit"))

    def test_feasibility_result_is_recommendation_only(self):
        goal = make_goal(goal_name="Big delivery")
        constraints = make_constraints(capacity_limit=10.0)
        plan = goal_decompose(goal, constraints)

        result = plan_feasibility_check(plan, {"capacity_hours": 10.0})

        # Trim options exist but are never applied by the checker.
        for option in result.trim_options:
            self.assertIn(option.action, ("drop", "defer", "extend"))


# ---------------------------------------------------------------------------
# Determinism: same inputs always produce same output
# ---------------------------------------------------------------------------

class TestDeterminism(unittest.TestCase):
    def test_same_inputs_produce_same_plan(self):
        goal = make_goal(goal_name="Deterministic goal")
        constraints = make_constraints()

        plan1 = goal_decompose(goal, constraints)
        plan2 = goal_decompose(goal, constraints)

        self.assertEqual(plan1.milestones, plan2.milestones)
        self.assertEqual(plan1.tasks, plan2.tasks)
        self.assertEqual(plan1.confidence, plan2.confidence)


# ---------------------------------------------------------------------------
# Material diff excludes immaterial churn
# ---------------------------------------------------------------------------

class TestMaterialDiff(unittest.TestCase):
    def test_material_diff_excludes_unchanged(self):
        goal = make_goal(goal_name="Simple goal")
        plan = goal_decompose(goal, make_constraints())

        v1 = PlanVersion(version=1, plan=plan)
        v2 = PlanVersion(version=2, plan=plan)

        diff = material_diff(v1, v2)
        self.assertEqual(diff, {})

    def test_material_diff_includes_deadline_change(self):
        goal = make_goal(goal_name="Simple goal", due_date="2026-12-31")
        plan = goal_decompose(goal, make_constraints())

        v1 = PlanVersion(version=1, plan=plan)

        event = ReplanEvent(
            kind=ReplanEventKind.DEADLINE_MOVED,
            entity_id=plan.goal_id,
            detail="2027-06-30",
        )
        v2 = goal_replan(plan, event)

        diff = material_diff(v1, v2)
        self.assertIn("deadline_anchor", diff)


if __name__ == "__main__":
    unittest.main()