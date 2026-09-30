"""
Batch S4 -- Versioned Learning Plan QA Tests (S4-01..S4-07 + malformed-input edge cases).
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.intensiq.learning_plan import LearningPlanService
from scholar.intensiq.contracts import validate_learning_plan
from scholar.fixtures.learning_plans import (
    PLAN_V1,
    PLAN_V2,
    PLAN_V1_DIFFERENT_GOAL,
    PLAN_WITH_CALENDAR_FIELD,
    PLAN_WRONG_CREATOR,
    PLAN_MISSING_REQUIRED,
    PLAN_NON_POSITIVE_VERSION,
    PLAN_NEGATIVE_EXPECTED_PREV,
)


# ====================================================================== #
#  S4-01 Create: new plan written
# ====================================================================== #

class TestS4_01_Create(unittest.TestCase):
    def test_create_writes_plan(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertIsNotNone(result)
        self.assertEqual(result["course_id"], "critical-care-101")
        self.assertEqual(result["version"], 1)

    def test_create_sets_version_to_1(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertEqual(result["version"], 1)

    def test_create_sets_expected_previous_version_to_0(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertEqual(result["expected_previous_version"], 0)

    def test_create_preserves_goal_id(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertEqual(result["goal_id"], "goal-1")

    def test_create_injects_creator(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertEqual(result["created_by"], "scholar")

    def test_create_injects_updated_at(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        fixed_now = "2026-09-30T10:00:00"
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar", now=fixed_now)
        self.assertEqual(result["updated_at"], fixed_now)

    def test_create_stores_for_get(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        stored = svc.get("course-1")
        self.assertIsNotNone(stored)
        self.assertEqual(stored["plan_id"], "plan-1")

    def test_create_does_not_mutate_input(self):
        original = _copy(PLAN_V1)
        original_version = original["version"]
        original_epv = original["expected_previous_version"]
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", original, creator="scholar")
        self.assertEqual(original["version"], original_version)
        self.assertEqual(original["expected_previous_version"], original_epv)


# ====================================================================== #
#  S4-02 Read: stored plan returned unchanged
# ====================================================================== #

class TestS4_02_Read(unittest.TestCase):
    def test_get_returns_stored_plan_unchanged(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        stored = svc.get("course-1")
        self.assertEqual(stored["plan_id"], "plan-1")
        self.assertEqual(stored["goal_id"], "goal-1")
        self.assertEqual(stored["status"], "active")
        self.assertEqual(stored["objective"], "Build mechanical ventilation proficiency")
        self.assertEqual(stored["weekly_minutes"], 300)
        self.assertEqual(stored["minimum_session_minutes"], 30)

    def test_get_returns_none_when_absent(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.get("nonexistent")
        self.assertIsNone(result)

    def test_get_returns_full_plan_after_create(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        stored = svc.get("course-1")
        required_fields = [
            "plan_id", "goal_id", "course_id", "version",
            "expected_previous_version", "status", "objective", "target_date",
            "proficiency_refs", "ordered_learning_items", "weekly_minutes",
            "minimum_session_minutes", "review_policy", "mastery_targets",
            "rationale", "created_by", "updated_at",
        ]
        for f in required_fields:
            self.assertIn(f, stored, f"Missing field: {f}")


# ====================================================================== #
#  S4-03 Version increment: correct
# ====================================================================== #

class TestS4_03_VersionIncrement(unittest.TestCase):
    def test_second_put_increments_version(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        result_v2 = svc.put("course-1", _copy(PLAN_V2), creator="scholar")
        self.assertEqual(result_v2["version"], 2)

    def test_version_increment_is_sequential(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        svc.put("course-1", _copy(PLAN_V2), creator="scholar")
        v3 = _copy(PLAN_V2)
        v3["expected_previous_version"] = 2
        result_v3 = svc.put("course-1", v3, creator="scholar")
        self.assertEqual(result_v3["version"], 3)

    def test_expected_previous_version_matches_current(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        result_v2 = svc.put("course-1", _copy(PLAN_V2), creator="scholar")
        self.assertEqual(result_v2["expected_previous_version"], 1)
        self.assertEqual(result_v2["version"], 2)

    def test_different_courses_have_independent_versions(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        svc.put("course-2", _copy(PLAN_V1_DIFFERENT_GOAL), creator="scholar")
        self.assertEqual(svc.get("course-1")["version"], 1)
        self.assertEqual(svc.get("course-2")["version"], 1)


# ====================================================================== #
#  S4-04 Stale write: rejected
# ====================================================================== #

class TestS4_04_StaleWrite(unittest.TestCase):
    def test_stale_write_raises_value_error(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        # Write version 1 with stale expected_previous_version
        stale = _copy(PLAN_V2)
        stale["expected_previous_version"] = 0
        stale["version"] = 2
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", stale, creator="scholar")
        self.assertIn("Stale plan", str(ctx.exception))

    def test_stale_write_does_not_overwrite(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        original_v2 = _copy(PLAN_V2)
        original_v2["expected_previous_version"] = 0
        original_v2["version"] = 2
        try:
            svc.put("course-1", original_v2, creator="scholar")
        except ValueError:
            pass
        stored = svc.get("course-1")
        self.assertEqual(stored["version"], 1)

    def test_fresh_write_succeeds(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        fresh = _copy(PLAN_V2)
        # expected_previous_version will be set by service to 1
        result = svc.put("course-1", fresh, creator="scholar")
        self.assertEqual(result["version"], 2)


# ====================================================================== #
#  S4-05 Calendar fields: rejected
# ====================================================================== #

class TestS4_05_CalendarFields(unittest.TestCase):
    def test_scheduled_at_field_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", _copy(PLAN_WITH_CALENDAR_FIELD), creator="scholar")
        self.assertIn("Calendar-time", str(ctx.exception))

    def test_start_time_nested_rejected(self):
        bad = _copy(PLAN_V1)
        bad["ordered_learning_items"] = [
            {"item_id": "x", "start_time": "2026-10-01T09:00:00"}
        ]
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", bad, creator="scholar")
        self.assertIn("Calendar-time", str(ctx.exception))

    def test_session_times_rejected(self):
        bad = _copy(PLAN_V1)
        bad["review_policy"] = {"session_times": ["09:00"]}
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", bad, creator="scholar")
        self.assertIn("Calendar-time", str(ctx.exception))

    def test_valid_plan_without_calendar_fields_accepted(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertEqual(result["version"], 1)


# ====================================================================== #
#  S4-06 Wrong creator: policy enforced
# ====================================================================== #

class TestS4_06_WrongCreator(unittest.TestCase):
    def test_wrong_creator_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", _copy(PLAN_WRONG_CREATOR), creator="scholar")
        self.assertIn("created_by", str(ctx.exception))

    def test_correct_creator_accepted(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        self.assertEqual(result["version"], 1)

    def test_validate_directly_rejects_wrong_creator(self):
        with self.assertRaises(ValueError):
            validate_learning_plan(PLAN_WRONG_CREATOR, creator="scholar")


# ====================================================================== #
#  S4-07 Goal link: preserved across versions
# ====================================================================== #

class TestS4_07_GoalLinkPreserved(unittest.TestCase):
    def test_goal_id_preserved_on_update(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        update = _copy(PLAN_V2)
        # Simulate a PUT where caller might try to change goal_id
        update["goal_id"] = "goal-999"
        result = svc.put("course-1", update, creator="scholar")
        self.assertEqual(result["goal_id"], "goal-1")

    def test_goal_id_preserved_on_multiple_updates(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        svc.put("course-1", _copy(PLAN_V1), creator="scholar")
        update = _copy(PLAN_V2)
        result_v2 = svc.put("course-1", update, creator="scholar")
        self.assertEqual(result_v2["goal_id"], "goal-1")
        update2 = _copy(PLAN_V2)
        update2["expected_previous_version"] = 2
        update2["goal_id"] = "goal-999"
        result_v3 = svc.put("course-1", update2, creator="scholar")
        self.assertEqual(result_v3["goal_id"], "goal-1")

    def test_different_goal_initial_plan_accepted(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        result = svc.put("course-2", _copy(PLAN_V1_DIFFERENT_GOAL), creator="scholar")
        self.assertEqual(result["goal_id"], "goal-2")


# ====================================================================== #
#  Malformed-input edge cases
# ====================================================================== #

class TestMalformedInputEdgeCases(unittest.TestCase):
    def test_missing_required_field_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", _copy(PLAN_MISSING_REQUIRED), creator="scholar")
        self.assertIn("Missing required fields", str(ctx.exception))

    def test_non_positive_version_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", _copy(PLAN_NON_POSITIVE_VERSION), creator="scholar")
        self.assertIn("version must be a positive int", str(ctx.exception))

    def test_negative_expected_previous_version_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", _copy(PLAN_NEGATIVE_EXPECTED_PREV), creator="scholar")
        self.assertIn("expected_previous_version must be a non-negative int", str(ctx.exception))

    def test_validate_directly_rejects_calendar_fields(self):
        with self.assertRaises(ValueError):
            validate_learning_plan(PLAN_WITH_CALENDAR_FIELD, creator="scholar")

    def test_validate_directly_rejects_missing_fields(self):
        bad = {k: v for k, v in PLAN_V1.items() if k != "weekly_minutes"}
        with self.assertRaises(ValueError):
            validate_learning_plan(bad, creator="scholar")

    def test_validate_directly_rejects_non_int_version(self):
        bad = _copy(PLAN_V1)
        bad["version"] = "2"
        with self.assertRaises(ValueError):
            validate_learning_plan(bad, creator="scholar")

    def test_validate_directly_rejects_float_version(self):
        bad = _copy(PLAN_V1)
        bad["version"] = 1.5
        with self.assertRaises(ValueError):
            validate_learning_plan(bad, creator="scholar")

    def test_empty_plan_id_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        bad = _copy(PLAN_V1)
        bad["plan_id"] = ""
        with self.assertRaises(ValueError):
            svc.put("course-1", bad, creator="scholar")

    def test_none_creator_field_rejected(self):
        svc = LearningPlanService(clock=lambda: _fake_now())
        bad = _copy(PLAN_V1)
        bad["created_by"] = None
        with self.assertRaises(ValueError):
            svc.put("course-1", bad, creator="scholar")

    def test_calendar_field_in_nested_dict_rejected(self):
        bad = _copy(PLAN_V1)
        bad["mastery_targets"] = [{"name": "test", "end_time": "2026-10-01T10:00:00"}]
        svc = LearningPlanService(clock=lambda: _fake_now())
        with self.assertRaises(ValueError) as ctx:
            svc.put("course-1", bad, creator="scholar")
        self.assertIn("Calendar-time", str(ctx.exception))


# ====================================================================== #
#  Helpers
# ====================================================================== #

def _fake_now():
    """Deterministic UTC timestamp for testing."""
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


def _copy(d):
    """Shallow copy for top-level dict used in tests."""
    import copy
    return copy.deepcopy(d)


if __name__ == "__main__":
    unittest.main()
