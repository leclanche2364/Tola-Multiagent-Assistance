"""
Batch S1 -- QA S1 Tests: IntenSIQ Capability Contract.
unittest only. Python 3 stdlib. Plain ASCII.
"""

import ast
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHOLAR_ROOT = os.path.join(REPO_ROOT, "scholar")

# ---------------------------------------------------------------------------
# Helpers: import S1 modules
# ---------------------------------------------------------------------------

import sys
sys.path.insert(0, SCHOLAR_ROOT)

from scholar.intensiq import capability_registry
from scholar.intensiq import contracts
from scholar.intensiq import denials


# ---------------------------------------------------------------------------
# Field lists from plan sections 8.1-8.3 (hard-coded to match the plan)
# ---------------------------------------------------------------------------

LEARNER_STATE_FIELDS = [
    "schema_version", "state_version", "as_of", "course", "course_goals",
    "proficiency_context", "topics", "reasoning_evidence", "competency_evidence",
    "revision_items", "cursor",
]

# topics sub-fields per plan 8.1
TOPIC_SUB_FIELDS = [
    "progress", "next_action", "practice_units",
    "recent_assessments", "recent_study_activity",
]

LEARNING_PLAN_FIELDS = [
    "plan_id", "goal_id", "course_id", "version", "expected_previous_version",
    "status", "objective", "target_date", "proficiency_refs",
    "ordered_learning_items", "weekly_minutes", "minimum_session_minutes",
    "review_policy", "mastery_targets", "rationale", "created_by", "updated_at",
]

EVENT_FIELDS = [
    "event_id", "event_type", "schema_version", "occurred_at",
    "course_id", "topic_id", "aggregate_id", "payload",
]

EXPECTED_EVENT_TYPES = frozenset({
    "study_session.recorded",
    "practice_unit.completed",
    "assessment.submitted",
    "reasoning_session.completed",
    "recording.transcription_completed",
    "course_goals.updated",
    "learning_plan.updated",
    "topic.progress_changed",
    "proficiency_context.updated",
})


class TestS1_01_ExistingEndpointsClassified(unittest.TestCase):
    """S1-01: Existing IntenSIQ endpoints classified correctly per plan."""

    def test_registry_is_list(self):
        self.assertIsInstance(capability_registry.CAPABILITY_REGISTRY, list)
        self.assertGreater(len(capability_registry.CAPABILITY_REGISTRY), 0)

    def test_existing_read_routes_classified(self):
        """All 9 existing read routes from the plan are READ_EXISTING."""
        read_routes = [
            ("/api/v1/courses", "GET"),
            ("/api/v1/courses/{courseId}/topics", "GET"),
            ("/api/v1/courses/{courseId}/topics/{topicId}/content", "GET"),
            ("/api/v1/goals", "GET"),
            ("/api/v1/progress", "GET"),
            ("/api/v1/practice", "GET"),
            ("/api/v1/tests", "GET"),
            ("/api/v1/cases", "GET"),
            ("/api/v1/study-materials", "GET"),
            ("/api/v1/recordings", "GET"),
            ("/api/v1/reasoning", "GET"),
        ]
        for route, verb in read_routes:
            entry = capability_registry.classify(route, verb)
            self.assertIsNotNone(entry, f"Missing registry entry for {verb} {route}")
            self.assertEqual(
                entry["classification"], "READ_EXISTING",
                f"{verb} {route} should be READ_EXISTING",
            )

    def test_all_registry_entries_have_required_keys(self):
        for entry in capability_registry.CAPABILITY_REGISTRY:
            for key in ("route", "verb", "classification", "rationale"):
                self.assertIn(key, entry, f"Entry missing key '{key}': {entry}")

    def test_classification_values_valid(self):
        valid = {"READ_EXISTING", "WRITE_EXISTING", "NOT_FOR_SCHOLAR", "NEW_INTEGRATION_NEEDED"}
        for entry in capability_registry.CAPABILITY_REGISTRY:
            self.assertIn(
                entry["classification"], valid,
                f"Invalid classification '{entry['classification']}' for {entry['route']}",
            )

    def test_rationale_non_empty(self):
        for entry in capability_registry.CAPABILITY_REGISTRY:
            self.assertTrue(
                len(entry["rationale"]) > 0,
                f"Empty rationale for {entry['route']} {entry['verb']}",
            )


class TestS1_02_ForbiddenWritesUnavailable(unittest.TestCase):
    """S1-02: Progress/practice/assessment mutations and deletes are NOT_FOR_SCHOLAR or is_forbidden True."""

    def test_progress_write_not_for_scholar(self):
        entry = capability_registry.classify("/api/v1/progress", "PUT")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NOT_FOR_SCHOLAR")

    def test_practice_write_not_for_scholar(self):
        entry = capability_registry.classify("/api/v1/practice", "PUT")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NOT_FOR_SCHOLAR")

    def test_assessment_submit_not_for_scholar(self):
        entry = capability_registry.classify("/api/v1/assessment", "POST")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NOT_FOR_SCHOLAR")

    def test_course_delete_not_for_scholar(self):
        entry = capability_registry.classify("/api/v1/courses/{courseId}", "DELETE")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NOT_FOR_SCHOLAR")

    def test_topic_delete_not_for_scholar(self):
        entry = capability_registry.classify("/api/v1/courses/{courseId}/topics/{topicId}", "DELETE")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NOT_FOR_SCHOLAR")

    def test_user_mutation_not_for_scholar(self):
        entry = capability_registry.classify("/api/v1/users/{userId}", "PUT")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NOT_FOR_SCHOLAR")

    def test_is_forbidden_progress_write(self):
        self.assertTrue(denials.is_forbidden("/api/v1/progress", "PUT"))

    def test_is_forbidden_practice_write(self):
        self.assertTrue(denials.is_forbidden("/api/v1/practice", "PUT"))

    def test_is_forbidden_assessment_submit(self):
        self.assertTrue(denials.is_forbidden("/api/v1/assessment", "POST"))

    def test_is_forbidden_course_delete(self):
        self.assertTrue(denials.is_forbidden("/api/v1/courses/{courseId}", "DELETE"))

    def test_is_forbidden_topic_delete(self):
        self.assertTrue(denials.is_forbidden("/api/v1/courses/{courseId}/topics/{topicId}", "DELETE"))

    def test_is_forbidden_user_mutation(self):
        self.assertTrue(denials.is_forbidden("/api/v1/users/{userId}", "PUT"))

    def test_is_forbidden_read_not_forbidden(self):
        self.assertFalse(denials.is_forbidden("/api/v1/progress", "GET"))
        self.assertFalse(denials.is_forbidden("/api/v1/goals", "GET"))

    def test_is_forbidden_unknown_route(self):
        self.assertFalse(denials.is_forbidden("/api/v1/unknown", "DELETE"))

    def test_forbidden_verbs_structure(self):
        self.assertIsInstance(denials.FORBIDDEN_VERBS, frozenset)
        for v in ("PUT", "POST", "DELETE", "PATCH"):
            self.assertIn(v, denials.FORBIDDEN_VERBS)

    def test_endpoints_structure(self):
        self.assertIsInstance(denials.ENDPOINTS, frozenset)
        self.assertIn("/api/v1/progress", denials.ENDPOINTS)


class TestS1_03_OnlyThreeAdditions(unittest.TestCase):
    """S1-03: Only the 3 new integration additions exist (learner-state, learning-plan, events)."""

    def test_exactly_three_new_integration_entries(self):
        new = capability_registry.list_by_classification("NEW_INTEGRATION_NEEDED")
        self.assertEqual(len(new), 3,
                         f"Expected exactly 3 NEW_INTEGRATION_NEEDED entries, found {len(new)}")

    def test_learner_state_read_is_new(self):
        entry = capability_registry.classify("/api/v1/integration/learner-state", "GET")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NEW_INTEGRATION_NEEDED")

    def test_learning_plan_get_is_new(self):
        entry = capability_registry.classify(
            "/api/v1/integration/courses/{courseId}/learning-plan", "GET/PUT"
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NEW_INTEGRATION_NEEDED")

    def test_learning_plan_put_is_new(self):
        # PUT is part of the same GET/PUT entry for this route
        entry = capability_registry.classify(
            "/api/v1/integration/courses/{courseId}/learning-plan", "GET/PUT"
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NEW_INTEGRATION_NEEDED")

    def test_events_outbox_is_new(self):
        entry = capability_registry.classify("/api/v1/integration/events", "GET")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["classification"], "NEW_INTEGRATION_NEEDED")

    def test_no_other_new_integration_routes(self):
        new = capability_registry.list_by_classification("NEW_INTEGRATION_NEEDED")
        routes = {(e["route"], e["verb"]) for e in new}
        expected = {
            ("/api/v1/integration/learner-state", "GET"),
            ("/api/v1/integration/courses/{courseId}/learning-plan", "GET/PUT"),
            ("/api/v1/integration/events", "GET"),
        }
        self.assertEqual(routes, expected, f"Unexpected new integration routes: {routes - expected}")


class TestS1_04_NoInventedContract(unittest.TestCase):
    """S1-04: Every registry entry has source/rationale; contract field lists match plan exactly."""

    def test_all_entries_have_rationale_referencing_plan(self):
        """Every registry entry carries a rationale referencing the plan."""
        for entry in capability_registry.CAPABILITY_REGISTRY:
            rationale = entry["rationale"].lower()
            self.assertTrue(
                len(rationale) > 0,
                f"Empty rationale for {entry['route']}",
            )
            # Rationale must reference plan section or handover
            has_source = (
                "plan" in rationale
                or "handover" in rationale
                or "section" in rationale
            )
            self.assertTrue(
                has_source,
                f"Rationale does not reference plan source: {entry['route']} {entry['verb']}",
            )

    def test_learner_state_contract_fields_match_plan(self):
        """LearnerStateRead fields match plan 8.1 exactly."""
        ds = contracts.LearnerStateRead
        fields = [f.name for f in ds.__dataclass_fields__.values()]
        self.assertEqual(fields, LEARNER_STATE_FIELDS,
                         f"LearnerStateRead fields {fields} != expected {LEARNER_STATE_FIELDS}")

    def test_learning_plan_contract_fields_match_plan(self):
        """LearningPlan fields match plan 8.2 exactly."""
        ds = contracts.LearningPlan
        fields = [f.name for f in ds.__dataclass_fields__.values()]
        self.assertEqual(fields, LEARNING_PLAN_FIELDS,
                         f"LearningPlan fields {fields} != expected {LEARNING_PLAN_FIELDS}")

    def test_learning_event_contract_fields_match_plan(self):
        """LearningEvent fields match plan 8.3 exactly."""
        ds = contracts.LearningEvent
        fields = [f.name for f in ds.__dataclass_fields__.values()]
        self.assertEqual(fields, EVENT_FIELDS,
                         f"LearningEvent fields {fields} != expected {EVENT_FIELDS}")

    def test_event_types_frozenset_matches_plan(self):
        """EVENT_TYPES frozenset contains exactly the 9 event types from plan 8.3."""
        self.assertEqual(contracts.EVENT_TYPES, EXPECTED_EVENT_TYPES)
        self.assertEqual(len(contracts.EVENT_TYPES), 9)

    def test_learner_state_is_frozen(self):
        self.assertTrue(contracts.LearnerStateRead.__dataclass_params__.frozen)

    def test_learning_plan_is_frozen(self):
        self.assertTrue(contracts.LearningPlan.__dataclass_params__.frozen)

    def test_learning_event_is_frozen(self):
        self.assertTrue(contracts.LearningEvent.__dataclass_params__.frozen)

    def test_registry_entry_source_references_plan_for_new_integrations(self):
        """The three NEW_INTEGRATION_NEEDED entries reference plan 8.1-8.3."""
        new = capability_registry.list_by_classification("NEW_INTEGRATION_NEEDED")
        by_route = {e["route"]: e for e in new}

        # 8.1 learner-state
        ls = by_route["/api/v1/integration/learner-state"]
        self.assertIn("8.1", ls["rationale"])

        # 8.2 learning-plan
        lp_get = by_route["/api/v1/integration/courses/{courseId}/learning-plan"]
        self.assertIn("8.2", lp_get["rationale"])

        # 8.3 events
        ev = by_route["/api/v1/integration/events"]
        self.assertIn("8.3", ev["rationale"])


class TestValidationEdgeCases(unittest.TestCase):
    """Validation edge cases for validate_learning_plan."""

    def _valid_plan_dict(self):
        return {
            "plan_id": "p1",
            "goal_id": "g1",
            "course_id": "c1",
            "version": 1,
            "expected_previous_version": 0,
            "status": "active",
            "objective": "Learn X",
            "target_date": "2026-12-01",
            "proficiency_refs": [],
            "ordered_learning_items": [],
            "weekly_minutes": 120,
            "minimum_session_minutes": 30,
            "review_policy": "spaced",
            "mastery_targets": [],
            "rationale": "test",
            "created_by": "scholar",
            "updated_at": "2026-09-30T00:00:00Z",
        }

    def test_valid_plan_passes(self):
        p = self._valid_plan_dict()
        contracts.validate_learning_plan(p)  # must not raise

    def test_missing_required_field_raises(self):
        p = self._valid_plan_dict()
        del p["plan_id"]
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_missing_multiple_fields_raises(self):
        p = self._valid_plan_dict()
        del p["version"]
        del p["created_by"]
        with self.assertRaises(ValueError) as cm:
            contracts.validate_learning_plan(p)
        self.assertIn("Missing required fields", str(cm.exception))

    def test_calendar_time_scheduled_at_rejected(self):
        p = self._valid_plan_dict()
        p["scheduled_at"] = "2026-10-01T09:00:00Z"
        with self.assertRaises(ValueError) as cm:
            contracts.validate_learning_plan(p)
        self.assertIn("calendar-time", str(cm.exception).lower())

    def test_calendar_time_calendar_time_rejected(self):
        p = self._valid_plan_dict()
        p["calendar_time"] = "2026-10-01T09:00:00Z"
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_calendar_time_session_times_rejected(self):
        p = self._valid_plan_dict()
        p["session_times"] = ["09:00-10:00"]
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_calendar_time_start_time_rejected(self):
        p = self._valid_plan_dict()
        p["start_time"] = "09:00"
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_calendar_time_end_time_rejected(self):
        p = self._valid_plan_dict()
        p["end_time"] = "10:00"
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_wrong_creator_rejected(self):
        p = self._valid_plan_dict()
        p["created_by"] = "tola"
        with self.assertRaises(ValueError) as cm:
            contracts.validate_learning_plan(p)
        self.assertIn("scholar", str(cm.exception).lower())

    def test_wrong_creator_custom_validator_rejected(self):
        # creator='rhythm' but plan says created_by='scholar' -> rejected
        p = self._valid_plan_dict()
        p["created_by"] = "scholar"
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p, creator="rhythm")

    def test_version_zero_rejected(self):
        p = self._valid_plan_dict()
        p["version"] = 0
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_version_negative_rejected(self):
        p = self._valid_plan_dict()
        p["version"] = -1
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_expected_previous_version_zero_accepted(self):
        # expected_previous_version=0 is valid for the first version
        p = self._valid_plan_dict()
        p["expected_previous_version"] = 0
        contracts.validate_learning_plan(p)  # must not raise

    def test_version_not_int_rejected(self):
        p = self._valid_plan_dict()
        p["version"] = "1"
        with self.assertRaises(ValueError):
            contracts.validate_learning_plan(p)

    def test_dataclass_plan_validates(self):
        p = contracts.LearningPlan(
            plan_id="p1", goal_id="g1", course_id="c1", version=1,
            expected_previous_version=0, status="active", objective="Learn X",
            target_date="2026-12-01", proficiency_refs=[],
            ordered_learning_items=[], weekly_minutes=120,
            minimum_session_minutes=30, review_policy="spaced",
            mastery_targets=[], rationale="test", created_by="scholar",
            updated_at="2026-09-30T00:00:00Z",
        )
        contracts.validate_learning_plan(p)  # must not raise


class TestDenialTests(unittest.TestCase):
    """Additional denial edge cases."""

    def test_get_progress_not_forbidden(self):
        self.assertFalse(denials.is_forbidden("/api/v1/progress", "GET"))

    def test_get_practice_not_forbidden(self):
        self.assertFalse(denials.is_forbidden("/api/v1/practice", "GET"))

    def test_post_progress_is_forbidden(self):
        self.assertTrue(denials.is_forbidden("/api/v1/progress", "POST"))

    def test_patch_progress_is_forbidden(self):
        self.assertTrue(denials.is_forbidden("/api/v1/progress", "PATCH"))

    def test_delete_course_is_forbidden(self):
        self.assertTrue(denials.is_forbidden("/api/v1/courses/{courseId}", "DELETE"))

    def test_get_courses_not_forbidden(self):
        self.assertFalse(denials.is_forbidden("/api/v1/courses", "GET"))

    def test_forbidden_verbs_count(self):
        self.assertEqual(len(denials.FORBIDDEN_VERBS), 4)

    def test_endpoints_count(self):
        self.assertEqual(len(denials.ENDPOINTS), 6)


class TestParseCheck(unittest.TestCase):
    """Verify each new file parses cleanly with ast.parse."""

    def test_capability_registry_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "intensiq", "capability_registry.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())

    def test_contracts_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "intensiq", "contracts.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())

    def test_denials_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "intensiq", "denials.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())

    def test_test_s1_contract_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "tests", "test_s1_contract.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())


if __name__ == "__main__":
    unittest.main()
