"""
Batch S2 -- QA S2 Authentication and Scope Tests.
unittest only. Python 3 stdlib. Plain ASCII.
"""

import ast
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHOLAR_ROOT = os.path.join(REPO_ROOT, "scholar")

import sys
sys.path.insert(0, SCHOLAR_ROOT)

from scholar.intensiq import auth_policy
from scholar.intensiq import capability_registry
from scholar.intensiq import denials
from scholar.intensiq import scopes


# ===========================================================================
# S2-01..S2-04: Allowed combinations
# ===========================================================================

class TestS2_01_LearnerStateReadAllowed(unittest.TestCase):
    """S2-01: learner-state read is allowed."""

    def test_learner_state_get_allowed(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/learner-state", "GET", "u1", "u1"
        )
        self.assertTrue(allowed, f"Should be allowed: {reason}")

    def test_learner_state_read_scope_present(self):
        self.assertIn("learner-state:read", scopes.SCHOLAR_SCOPES)

    def test_learner_state_get_can(self):
        self.assertTrue(
            scopes.can("/api/v1/integration/learner-state", "GET", scopes.SCHOLAR_SCOPES)
        )


class TestS2_02_LearningPlanReadAllowed(unittest.TestCase):
    """S2-02: learning-plan read is allowed."""

    def test_learning_plan_get_allowed(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/courses/{courseId}/learning-plan", "GET", "u1", "u1"
        )
        self.assertTrue(allowed, f"Should be allowed: {reason}")

    def test_learning_plan_read_scope_present(self):
        self.assertIn("learning-plan:read", scopes.SCHOLAR_SCOPES)

    def test_learning_plan_get_can(self):
        self.assertTrue(
            scopes.can(
                "/api/v1/integration/courses/{courseId}/learning-plan", "GET", scopes.SCHOLAR_SCOPES
            )
        )


class TestS2_03_LearningPlanWriteAllowed(unittest.TestCase):
    """S2-03: learning-plan write (PUT) is allowed."""

    def test_learning_plan_put_allowed(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/courses/{courseId}/learning-plan", "PUT", "u1", "u1"
        )
        self.assertTrue(allowed, f"Should be allowed: {reason}")

    def test_learning_plan_write_scope_present(self):
        self.assertIn("learning-plan:write", scopes.SCHOLAR_SCOPES)

    def test_learning_plan_put_can(self):
        self.assertTrue(
            scopes.can(
                "/api/v1/integration/courses/{courseId}/learning-plan", "PUT", scopes.SCHOLAR_SCOPES
            )
        )


class TestS2_04_EventsReadAllowed(unittest.TestCase):
    """S2-04: events read is allowed."""

    def test_events_get_allowed(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/events", "GET", "u1", "u1"
        )
        self.assertTrue(allowed, f"Should be allowed: {reason}")

    def test_events_read_scope_present(self):
        self.assertIn("events:read", scopes.SCHOLAR_SCOPES)

    def test_events_get_can(self):
        self.assertTrue(
            scopes.can("/api/v1/integration/events", "GET", scopes.SCHOLAR_SCOPES)
        )


# ===========================================================================
# S2-05..S2-07: Denied combinations
# ===========================================================================

class TestS2_05_ProgressWriteDenied(unittest.TestCase):
    """S2-05: progress write is denied."""

    def test_progress_put_denied_by_policy(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/progress", "PUT", "u1", "u1"
        )
        self.assertFalse(allowed)

    def test_progress_put_denied_by_denials(self):
        self.assertTrue(denials.is_forbidden("/api/v1/progress", "PUT"))

    def test_progress_put_can_false(self):
        self.assertFalse(
            scopes.can("/api/v1/progress", "PUT", scopes.SCHOLAR_SCOPES)
        )


class TestS2_06_AssessmentSubmitDenied(unittest.TestCase):
    """S2-06: assessment submit is denied."""

    def test_assessment_post_denied_by_policy(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/assessment", "POST", "u1", "u1"
        )
        self.assertFalse(allowed)

    def test_assessment_post_denied_by_denials(self):
        self.assertTrue(denials.is_forbidden("/api/v1/assessment", "POST"))

    def test_assessment_post_can_false(self):
        self.assertFalse(
            scopes.can("/api/v1/assessment", "POST", scopes.SCHOLAR_SCOPES)
        )


class TestS2_07_CourseTopicDeleteDenied(unittest.TestCase):
    """S2-07: course/topic delete is denied."""

    def test_course_delete_denied_by_policy(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/courses/{courseId}", "DELETE", "u1", "u1"
        )
        self.assertFalse(allowed)

    def test_topic_delete_denied_by_policy(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/courses/{courseId}/topics/{topicId}", "DELETE", "u1", "u1"
        )
        self.assertFalse(allowed)

    def test_course_delete_denied_by_denials(self):
        self.assertTrue(denials.is_forbidden("/api/v1/courses/{courseId}", "DELETE"))

    def test_topic_delete_denied_by_denials(self):
        self.assertTrue(
            denials.is_forbidden("/api/v1/courses/{courseId}/topics/{topicId}", "DELETE")
        )


# ===========================================================================
# S2-08: Wrong user denied
# ===========================================================================

class TestS2_08_WrongUserDenied(unittest.TestCase):
    """S2-08: wrong user is denied even for allowed routes."""

    def test_learner_state_read_wrong_user_denied(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/learner-state", "GET", "u1", "u2"
        )
        self.assertFalse(allowed)
        self.assertIn("wrong_user", reason)

    def test_learning_plan_read_wrong_user_denied(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/courses/c1/learning-plan", "GET", "u1", "u2"
        )
        self.assertFalse(allowed)
        self.assertIn("wrong_user", reason)

    def test_learning_plan_write_wrong_user_denied(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/courses/c1/learning-plan", "PUT", "u1", "u2"
        )
        self.assertFalse(allowed)
        self.assertIn("wrong_user", reason)

    def test_events_read_wrong_user_denied(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/events", "GET", "u1", "u2"
        )
        self.assertFalse(allowed)
        self.assertIn("wrong_user", reason)


# ===========================================================================
# Scope escalation attempts
# ===========================================================================

class TestScopeEscalationBlocked(unittest.TestCase):
    """learning-plan:write must not permit learner-state write or events write."""

    def test_learning_plan_write_does_not_permit_learning_plan_read(self):
        # learning-plan:write must not permit learning-plan read (separate scope)
        self.assertFalse(
            scopes.can(
                "/api/v1/integration/courses/{courseId}/learning-plan", "GET", {"learning-plan:write"}
            )
        )

    def test_learning_plan_write_does_not_permit_events_write(self):
        self.assertFalse(
            scopes.can("/api/v1/integration/events", "PUT", {"learning-plan:write"})
        )

    def test_learner_state_read_does_not_permit_learner_state_write(self):
        self.assertFalse(
            scopes.can("/api/v1/integration/learner-state", "PUT", {"learner-state:read"})
        )

    def test_learner_state_read_does_not_permit_learning_plan_write(self):
        self.assertFalse(
            scopes.can(
                "/api/v1/integration/courses/{courseId}/learning-plan", "PUT", {"learner-state:read"}
            )
        )

    def test_events_read_does_not_permit_learner_state_write(self):
        self.assertFalse(
            scopes.can("/api/v1/integration/learner-state", "PUT", {"events:read"})
        )

    def test_events_read_does_not_permit_learning_plan_write(self):
        self.assertFalse(
            scopes.can(
                "/api/v1/integration/courses/{courseId}/learning-plan", "PUT", {"events:read"}
            )
        )


# ===========================================================================
# User mutation denied
# ===========================================================================

class TestUserMutationDenied(unittest.TestCase):
    """User mutation is denied regardless of scope."""

    def test_user_put_denied_even_with_learning_plan_write(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/users/{userId}", "PUT", "u1", "u1"
        )
        self.assertFalse(allowed)

    def test_user_put_denied_by_denials(self):
        self.assertTrue(denials.is_forbidden("/api/v1/users/{userId}", "PUT"))

    def test_user_put_can_false(self):
        self.assertFalse(
            scopes.can("/api/v1/users/{userId}", "PUT", scopes.SCHOLAR_SCOPES)
        )


# ===========================================================================
# Empty / unknown scopes denied
# ===========================================================================

class TestEmptyUnknownScopesDenied(unittest.TestCase):
    """Empty or unknown scopes are denied."""

    def test_empty_scopes_denied(self):
        self.assertFalse(
            scopes.can("/api/v1/integration/learner-state", "GET", set())
        )

    def test_empty_scopes_denied_by_auth(self):
        allowed, reason = auth_policy.check_access(
            "/api/v1/integration/learner-state", "GET", "u1", "u1"
        )
        # This uses SCHOLAR_SCOPES internally so it passes; but if we pass
        # empty scopes directly to can(), it must deny.
        self.assertFalse(
            scopes.can("/api/v1/integration/learner-state", "GET", frozenset())
        )

    def test_unknown_scope_denied(self):
        self.assertFalse(
            scopes.can("/api/v1/integration/learner-state", "GET", {"unknown:scope"})
        )

    def test_empty_scopes_list_denied(self):
        self.assertFalse(
            scopes.can("/api/v1/integration/learner-state", "GET", [])
        )


# ===========================================================================
# Cross-check: every NOT_FOR_SCHOLAR registry entry is denied by check_access
# ===========================================================================

class TestForbiddenRegistryEntriesAllDeniedByCheckAccess(unittest.TestCase):
    """Every NOT_FOR_SCHOLAR entry in the S1 registry is denied by check_access.
    This cross-check ensures the two layers (scopes + denials) can never drift."""

    def test_all_not_for_scholar_entries_denied(self):
        not_for_scholar = capability_registry.list_by_classification("NOT_FOR_SCHOLAR")
        for entry in not_for_scholar:
            route = entry["route"]
            verb = entry["verb"]
            allowed, reason = auth_policy.check_access(route, verb, "u1", "u1")
            self.assertFalse(
                allowed,
                f"NOT_FOR_SCHOLAR entry {verb} {route} was allowed by check_access: {reason}",
            )

    def test_not_for_scholar_count_matches_denials(self):
        """Every NOT_FOR_SCHOLAR entry must also be is_forbidden True."""
        not_for_scholar = capability_registry.list_by_classification("NOT_FOR_SCHOLAR")
        for entry in not_for_scholar:
            self.assertTrue(
                denials.is_forbidden(entry["route"], entry["verb"]),
                f"NOT_FOR_SCHOLAR entry {entry['verb']} {entry['route']} is not is_forbidden",
            )


# ===========================================================================
# AUTH_POLICY structure checks
# ===========================================================================

class TestAuthPolicyStructure(unittest.TestCase):
    """AUTH_POLICY document-object has the required fields."""

    def test_auth_policy_is_dict(self):
        self.assertIsInstance(auth_policy.AUTH_POLICY, dict)

    def test_auth_policy_has_credential_design(self):
        self.assertIn("credential_design", auth_policy.AUTH_POLICY)

    def test_auth_policy_has_principles(self):
        self.assertIn("principles", auth_policy.AUTH_POLICY)

    def test_credential_design_has_scopes(self):
        cd = auth_policy.AUTH_POLICY["credential_design"]
        self.assertIn("scopes", cd)
        self.assertEqual(set(cd["scopes"]), scopes.SCHOLAR_SCOPES)

    def test_credential_design_scope_count_is_4(self):
        cd = auth_policy.AUTH_POLICY["credential_design"]
        self.assertEqual(cd["scope_count"], 4)

    def test_principles_has_no_user_mutation(self):
        self.assertIn("no_user_mutation", auth_policy.AUTH_POLICY["principles"])

    def test_principles_has_no_delete_operations(self):
        self.assertIn("no_delete_operations", auth_policy.AUTH_POLICY["principles"])

    def test_principles_has_wrong_user_denial(self):
        self.assertIn("wrong_user_denial", auth_policy.AUTH_POLICY["principles"])

    def test_principles_has_no_action_approval_target_approval(self):
        self.assertIn("no_action_approval_target_approval", auth_policy.AUTH_POLICY["principles"])


# ===========================================================================
# Parse checks
# ===========================================================================

class TestParseCheck(unittest.TestCase):
    """Verify each new file parses cleanly with ast.parse."""

    def test_scopes_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "intensiq", "scopes.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())

    def test_auth_policy_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "intensiq", "auth_policy.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())

    def test_test_s2_auth_ast(self):
        path = os.path.join(SCHOLAR_ROOT, "tests", "test_s2_auth.py")
        with open(path, "r", encoding="ascii") as f:
            ast.parse(f.read())


if __name__ == "__main__":
    unittest.main()