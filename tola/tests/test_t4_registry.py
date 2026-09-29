"""QA T4 tests -- Agent Capability and Boundary Registry.

Covers T4-01..T4-13 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest, datetime.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

import datetime
import unittest

from tola.registry.profiles import (
    ACTIVE,
    FUTURE_NOT_AVAILABLE,
    DISABLED,
    DEGRADED,
    PROFILES,
    PROFILE_VERSION_HISTORY,
    AgentProfile,
    update_profile_version,
)
from tola.registry.capability import (
    agent_capability_get,
    agent_capability_match,
    agent_boundary_check,
    agent_current_load_get,
    ROUTING_TABLE,
)
from tola.registry.boundaries import (
    BoundaryViolation,
    enforce_boundary,
    record_profile_version_change,
    get_profile_version_history,
)
from tola.registry.availability import (
    DelegationBlockedError,
    MarketingActivationError,
    check_delegation_allowed,
    FutureSpecialistDependency,
    FUTURE_SPECIALIST_DEPENDENCY,
    record_future_specialist_dependency,
    route_marketing_work,
    validate_marketing_activation,
)


# ===========================================================================
# Fixtures
# ===========================================================================

FIXTURE_TIMESTAMP = "2026-09-29T12:00:00"


# ===========================================================================
# T4-01: Scheduling/capacity task maps to Rhythm
# ===========================================================================

class TestT4_01_SchedulingCapacityRoutesToRhythm(unittest.TestCase):
    def test_scheduling_maps_to_rhythm(self):
        result = agent_capability_match("scheduling")
        self.assertEqual(result["agent_id"], "rhythm")
        self.assertGreater(result["confidence"], 0.0)

    def test_capacity_maps_to_rhythm(self):
        result = agent_capability_match("capacity")
        self.assertEqual(result["agent_id"], "rhythm")

    def test_schedule_maps_to_rhythm(self):
        result = agent_capability_match("schedule")
        self.assertEqual(result["agent_id"], "rhythm")

    def test_rhythm_direct_domain_maps_to_rhythm(self):
        result = agent_capability_match("rhythm")
        self.assertEqual(result["agent_id"], "rhythm")

    def test_routing_table_contains_scheduling(self):
        self.assertIn("scheduling", ROUTING_TABLE)
        self.assertEqual(ROUTING_TABLE["scheduling"], "rhythm")

    def test_routing_table_contains_capacity(self):
        self.assertIn("capacity", ROUTING_TABLE)
        self.assertEqual(ROUTING_TABLE["capacity"], "rhythm")


# ===========================================================================
# T4-02: Funnel/product analysis maps to Growth
# ===========================================================================

class TestT4_02_FunnelProductRoutesToGrowth(unittest.TestCase):
    def test_funnel_maps_to_growth(self):
        result = agent_capability_match("funnel analysis")
        self.assertEqual(result["agent_id"], "growth")

    def test_product_maps_to_growth(self):
        result = agent_capability_match("product analysis")
        self.assertEqual(result["agent_id"], "growth")

    def test_growth_maps_to_growth(self):
        result = agent_capability_match("growth")
        self.assertEqual(result["agent_id"], "growth")

    def test_acquisition_maps_to_growth(self):
        result = agent_capability_match("acquisition")
        self.assertEqual(result["agent_id"], "growth")

    def test_conversion_maps_to_growth(self):
        result = agent_capability_match("conversion")
        self.assertEqual(result["agent_id"], "growth")

    def test_retention_maps_to_growth(self):
        result = agent_capability_match("retention")
        self.assertEqual(result["agent_id"], "growth")

    def test_experiment_maps_to_growth(self):
        result = agent_capability_match("experiment design")
        self.assertEqual(result["agent_id"], "growth")


# ===========================================================================
# T4-03: Learning-gap work maps to Scholar
# ===========================================================================

class TestT4_03_LearningGapRoutesToScholar(unittest.TestCase):
    def test_learning_maps_to_scholar(self):
        result = agent_capability_match("learning gap")
        self.assertEqual(result["agent_id"], "scholar")

    def test_scholar_maps_to_scholar(self):
        result = agent_capability_match("scholar")
        self.assertEqual(result["agent_id"], "scholar")

    def test_curriculum_maps_to_scholar(self):
        result = agent_capability_match("curriculum planning")
        self.assertEqual(result["agent_id"], "scholar")

    def test_evidence_maps_to_scholar(self):
        result = agent_capability_match("evidence synthesis")
        self.assertEqual(result["agent_id"], "scholar")

    def test_study_maps_to_scholar(self):
        result = agent_capability_match("study requirements")
        self.assertEqual(result["agent_id"], "scholar")

    def test_gap_maps_to_scholar(self):
        result = agent_capability_match("gap detection")
        self.assertEqual(result["agent_id"], "scholar")


# ===========================================================================
# T4-04: Growth direct schedule write rejected
# ===========================================================================

class TestT4_04_GrowthScheduleWriteRejected(unittest.TestCase):
    def test_growth_direct_schedule_write_rejected(self):
        result = agent_boundary_check("growth", "direct_schedule_write")
        self.assertFalse(result["allowed"])
        self.assertIn("growth", result["reason"].lower())
        self.assertIn("schedule", result["reason"].lower())

    def test_growth_rhythm_schedule_write_rejected(self):
        result = agent_boundary_check("growth", "rhythm_schedule_write")
        self.assertFalse(result["allowed"])

    def test_growth_schedule_write_via_enforce_raises(self):
        with self.assertRaises(BoundaryViolation):
            enforce_boundary("growth", "direct_schedule_write")

    def test_growth_forbidden_actions_include_schedule_write(self):
        profile = PROFILES["growth"]
        self.assertIn("direct_schedule_write", profile.forbidden_actions)


# ===========================================================================
# T4-05: Tola direct My Rhythm write rejected
# ===========================================================================

class TestT4_05_TolaMyRhythmWriteRejected(unittest.TestCase):
    def test_tola_direct_my_rhythm_write_rejected(self):
        result = agent_boundary_check("tola", "direct_my_rhythm_write")
        self.assertFalse(result["allowed"])
        self.assertIn("tola", result["reason"].lower())
        self.assertIn("rhythm", result["reason"].lower())

    def test_tola_my_rhythm_write_rejected(self):
        result = agent_boundary_check("tola", "my_rhythm_write")
        self.assertFalse(result["allowed"])

    def test_tola_rhythm_direct_write_rejected(self):
        result = agent_boundary_check("tola", "rhythm_direct_write")
        self.assertFalse(result["allowed"])

    def test_tola_rhythm_schedule_write_rejected(self):
        result = agent_boundary_check("tola", "rhythm_schedule_write")
        self.assertFalse(result["allowed"])

    def test_tola_enforce_direct_my_rhythm_write_raises(self):
        with self.assertRaises(BoundaryViolation):
            enforce_boundary("tola", "direct_my_rhythm_write")

    def test_tola_forbidden_actions_include_my_rhythm_write(self):
        profile = PROFILES["tola"]
        self.assertIn("direct_my_rhythm_write", profile.forbidden_actions)


# ===========================================================================
# T4-06: Scholar cannot take product-growth authority
# ===========================================================================

class TestT4_06_ScholarProductGrowthRejected(unittest.TestCase):
    def test_scholar_product_growth_analysis_rejected(self):
        result = agent_boundary_check("scholar", "product_growth_analysis")
        self.assertFalse(result["allowed"])
        self.assertIn("scholar", result["reason"].lower())
        self.assertIn("product_growth", result["reason"].lower())

    def test_scholar_funnel_analysis_rejected(self):
        result = agent_boundary_check("scholar", "funnel_analysis")
        self.assertFalse(result["allowed"])
        self.assertIn("scholar", result["reason"].lower())
        self.assertIn("funnel", result["reason"].lower())

    def test_scholar_growth_recommendation_rejected(self):
        result = agent_boundary_check("scholar", "growth_recommendation")
        self.assertFalse(result["allowed"])
        self.assertIn("scholar", result["reason"].lower())
        self.assertIn("product-growth", result["reason"].lower())

    def test_scholar_acquisition_analysis_rejected(self):
        result = agent_boundary_check("scholar", "acquisition_analysis")
        self.assertFalse(result["allowed"])
        self.assertIn("scholar", result["reason"].lower())
        self.assertIn("product-growth", result["reason"].lower())

    def test_scholar_enforce_product_growth_raises(self):
        with self.assertRaises(BoundaryViolation):
            enforce_boundary("scholar", "product_growth_analysis")

    def test_scholar_forbidden_actions_include_growth(self):
        profile = PROFILES["scholar"]
        forbidden_strs = " ".join(profile.forbidden_actions).lower()
        self.assertIn("product_growth", forbidden_strs)

    def test_scholar_forbidden_actions_include_growth(self):
        profile = PROFILES["scholar"]
        forbidden_strs = " ".join(profile.forbidden_actions).lower()
        self.assertIn("product_growth", forbidden_strs)


# ===========================================================================
# T4-07: Unknown domain follows safe escalation path
# ===========================================================================

class TestT4_07_UnknownDomainEscalation(unittest.TestCase):
    def test_unknown_domain_returns_none_agent(self):
        result = agent_capability_match("quantum knitting patterns")
        self.assertIsNone(result["agent_id"])

    def test_unknown_domain_confidence_is_zero(self):
        result = agent_capability_match("quantum knitting patterns")
        self.assertEqual(result["confidence"], 0.0)

    def test_unknown_domain_reason_mentions_escalation(self):
        result = agent_capability_match("quantum knitting patterns")
        self.assertIn("escalation", result["reason"].lower())

    def test_unknown_domain_reason_never_guess(self):
        result = agent_capability_match("quantum knitting patterns")
        # The reason string itself contains "never guess" as guidance
        self.assertIn("never guess", result["reason"].lower())

    def test_empty_string_unknown_domain(self):
        result = agent_capability_match("")
        self.assertIsNone(result["agent_id"])

    def test_nonsense_domain_unknown(self):
        result = agent_capability_match("flurbomatic widget")
        self.assertIsNone(result["agent_id"])


# ===========================================================================
# T4-08: Capability profile version changes are auditable
# ===========================================================================

class TestT4_08_ProfileVersionAudit(unittest.TestCase):
    def setUp(self):
        # Clear history for deterministic test
        PROFILE_VERSION_HISTORY.clear()

    def test_version_change_appends_to_history(self):
        record_profile_version_change(
            agent_id="rhythm",
            new_version="1.1.0",
            changed_by="tola",
            change_reason="T4 audit test",
            timestamp=FIXTURE_TIMESTAMP,
        )
        self.assertEqual(len(PROFILE_VERSION_HISTORY), 1)

    def test_version_history_contains_correct_fields(self):
        record_profile_version_change(
            agent_id="growth",
            new_version="1.1.0",
            changed_by="tola",
            change_reason="boundary update",
            timestamp=FIXTURE_TIMESTAMP,
        )
        entry = PROFILE_VERSION_HISTORY[0]
        self.assertEqual(entry["agent_id"], "growth")
        self.assertEqual(entry["old_version"], "1.0.0")
        self.assertEqual(entry["new_version"], "1.1.0")
        self.assertEqual(entry["changed_by"], "tola")
        self.assertEqual(entry["reason"], "boundary update")
        self.assertEqual(entry["timestamp"], FIXTURE_TIMESTAMP)

    def test_multiple_version_changes_accumulate(self):
        record_profile_version_change(
            agent_id="rhythm",
            new_version="1.1.0",
            changed_by="tola",
            change_reason="first change",
            timestamp=FIXTURE_TIMESTAMP,
        )
        record_profile_version_change(
            agent_id="scholar",
            new_version="1.1.0",
            changed_by="tola",
            change_reason="second change",
            timestamp=FIXTURE_TIMESTAMP,
        )
        self.assertEqual(len(PROFILE_VERSION_HISTORY), 2)

    def test_get_profile_version_history_returns_copy(self):
        record_profile_version_change(
            agent_id="tola",
            new_version="1.1.0",
            changed_by="tola",
            change_reason="test",
            timestamp=FIXTURE_TIMESTAMP,
        )
        history = get_profile_version_history()
        history.clear()
        # Original log is unaffected
        self.assertEqual(len(PROFILE_VERSION_HISTORY), 1)

    def test_update_profile_version_returns_new_profile(self):
        updated = update_profile_version(
            agent_id="rhythm",
            new_version="1.2.0",
            changed_by="tola",
            change_reason="version bump test",
            timestamp=FIXTURE_TIMESTAMP,
        )
        self.assertEqual(updated.version, "1.2.0")
        self.assertEqual(updated.last_updated_at, FIXTURE_TIMESTAMP)

    def test_profile_version_history_empty_before_changes(self):
        self.assertEqual(len(PROFILE_VERSION_HISTORY), 0)


# ===========================================================================
# T4-09: Planned Marketing Agent is visible with FUTURE_NOT_AVAILABLE
# ===========================================================================

class TestT4_09_MarketingAgentVisibleButUnavailable(unittest.TestCase):
    def test_marketing_agent_registered(self):
        self.assertIn("marketing", PROFILES)

    def test_marketing_availability_status_is_future_not_available(self):
        profile = PROFILES["marketing"]
        self.assertEqual(profile.availability_status, FUTURE_NOT_AVAILABLE)

    def test_marketing_agent_id_is_marketing(self):
        profile = PROFILES["marketing"]
        self.assertEqual(profile.agent_id, "marketing")

    def test_marketing_domain_is_marketing(self):
        profile = PROFILES["marketing"]
        self.assertEqual(profile.domain, "marketing")

    def test_marketing_activation_requirements_populated(self):
        profile = PROFILES["marketing"]
        self.assertGreater(len(profile.activation_requirements), 0)

    def test_marketing_allowed_tools_empty(self):
        profile = PROFILES["marketing"]
        self.assertEqual(len(profile.allowed_tools), 0)

    def test_marketing_skills_empty(self):
        profile = PROFILES["marketing"]
        self.assertEqual(len(profile.skills), 0)

    def test_marketing_version_is_1_0_0(self):
        profile = PROFILES["marketing"]
        self.assertEqual(profile.version, "1.0.0")

    def test_marketing_last_updated_at_is_date_string(self):
        profile = PROFILES["marketing"]
        self.assertEqual(profile.last_updated_at, "2026-09-29")

    def test_agent_capability_get_returns_marketing_profile(self):
        result = agent_capability_get("marketing")
        self.assertIsNotNone(result)
        self.assertEqual(result["availability_status"], "FUTURE_NOT_AVAILABLE")

    def test_agent_capability_get_returns_active_profiles(self):
        for aid in ("tola", "rhythm", "growth", "scholar"):
            result = agent_capability_get(aid)
            self.assertIsNotNone(result)
            self.assertEqual(result["availability_status"], "ACTIVE")


# ===========================================================================
# T4-10: Delegation to unavailable Marketing Agent is blocked
# ===========================================================================

class TestT4_10_DelegationBlockedForNonActiveAgents(unittest.TestCase):
    def test_delegation_to_marketing_raises_blocked_error(self):
        with self.assertRaises(DelegationBlockedError) as cm:
            check_delegation_allowed("marketing")
        self.assertIn("marketing", str(cm.exception))
        self.assertIn("FUTURE_NOT_AVAILABLE", str(cm.exception))

    def test_delegation_to_marketing_message_mentions_t4_10(self):
        try:
            check_delegation_allowed("marketing")
        except DelegationBlockedError as e:
            self.assertIn("T4-10", str(e))

    def test_delegation_to_unknown_agent_raises_blocked_error(self):
        with self.assertRaises(DelegationBlockedError):
            check_delegation_allowed("nonexistent_agent")

    def test_delegation_to_active_agent_succeeds(self):
        # Should not raise
        check_delegation_allowed("tola")
        check_delegation_allowed("rhythm")
        check_delegation_allowed("growth")
        check_delegation_allowed("scholar")

    def test_delegation_to_disabled_agent_raises(self):
        # Simulate a DISABLED agent by checking a known non-ACTIVE status
        # We test the general mechanism: non-ACTIVE -> blocked
        # Since we cannot mutate PROFILES (frozen), we verify the
        # check works for the marketing agent which is FUTURE_NOT_AVAILABLE
        with self.assertRaises(DelegationBlockedError):
            check_delegation_allowed("marketing")


# ===========================================================================
# T4-11: Eligible marketing work routes to Growth
# ===========================================================================

class TestT4_11_EligibleMarketingWorkRoutesToGrowth(unittest.TestCase):
    def test_funnel_analysis_routes_to_growth(self):
        result = route_marketing_work("funnel analysis for Q3")
        self.assertEqual(result["routed_to"], "growth")
        self.assertEqual(result["record_type"], "ROUTED_TO_ACTIVE_SPECIALIST")

    def test_conversion_analysis_routes_to_growth(self):
        result = route_marketing_work("conversion analysis for landing page")
        self.assertEqual(result["routed_to"], "growth")

    def test_retention_analysis_routes_to_growth(self):
        result = route_marketing_work("retention analysis for cohort")
        self.assertEqual(result["routed_to"], "growth")

    def test_product_metrics_routes_to_growth(self):
        result = route_marketing_work("product metrics dashboard review")
        self.assertEqual(result["routed_to"], "growth")

    def test_experiment_design_routes_to_growth(self):
        result = route_marketing_work("experiment design for onboarding flow")
        self.assertEqual(result["routed_to"], "growth")

    def test_acquisition_analysis_routes_to_growth(self):
        result = route_marketing_work("acquisition analysis for paid channels")
        self.assertEqual(result["routed_to"], "growth")

    def test_growth_recommendation_routes_to_growth(self):
        result = route_marketing_work("growth recommendation for retention")
        self.assertEqual(result["routed_to"], "growth")

    def test_eligible_work_reason_mentions_contract(self):
        result = route_marketing_work("funnel analysis for Q3")
        self.assertIn("contract", result["reason"].lower())
        self.assertIn("growth", result["reason"].lower())


# ===========================================================================
# T4-12: Unsupported marketing work becomes FUTURE_SPECIALIST_DEPENDENCY
# ===========================================================================

class TestT4_12_UnsupportedMarketingWorkDeferred(unittest.TestCase):
    def test_unsupported_marketing_work_returns_dependency(self):
        result = route_marketing_work("paid acquisition campaign launch")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")
        self.assertIsNone(result["routed_to"])

    def test_dependency_record_has_required_fields(self):
        result = route_marketing_work("paid acquisition campaign launch")
        dep = result["dependency"]
        self.assertEqual(dep["required_domain"], "marketing")
        self.assertEqual(dep["intended_agent_id"], "marketing")
        self.assertEqual(dep["status"], "DEFERRED")
        self.assertIsNotNone(dep["reason"])

    def test_dependency_reason_mentions_future_specialist(self):
        result = route_marketing_work("paid acquisition campaign launch")
        self.assertIn("future", result["reason"].lower())

    def test_dependency_reason_mentions_deferred(self):
        result = route_marketing_work("paid acquisition campaign launch")
        self.assertIn("deferred", result["reason"].lower())

    def test_unsupported_work_never_fakes_execution(self):
        result = route_marketing_work("SEO execution for new pages")
        self.assertNotEqual(result["record_type"], "ROUTED_TO_ACTIVE_SPECIALIST")
        self.assertIsNone(result["routed_to"])
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")

    def test_content_distribution_routes_to_dependency(self):
        result = route_marketing_work("content distribution for blog")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")

    def test_community_growth_routes_to_dependency(self):
        result = route_marketing_work("community growth initiative")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")

    def test_campaign_operations_routes_to_dependency(self):
        result = route_marketing_work("campaign operations for launch")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")

    def test_paid_acquisition_routes_to_dependency(self):
        result = route_marketing_work("paid acquisition where authorised")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")

    def test_partnership_outreach_routes_to_dependency(self):
        result = route_marketing_work("partnership outreach execution")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")

    def test_lifecycle_crm_routes_to_dependency(self):
        result = route_marketing_work("lifecycle CRM marketing campaign")
        self.assertEqual(result["record_type"], "FUTURE_SPECIALIST_DEPENDENCY")


# ===========================================================================
# T4-13: Marketing Agent cannot become ACTIVE until prerequisites complete
# ===========================================================================

class TestT4_13_MarketingActivationGate(unittest.TestCase):
    def test_marketing_cannot_activate_before_prerequisites(self):
        result = validate_marketing_activation()
        self.assertFalse(result["can_activate"])
        self.assertEqual(result["status"], "FUTURE_NOT_AVAILABLE")

    def test_marketing_activation_lists_missing_requirements(self):
        result = validate_marketing_activation()
        self.assertGreater(len(result["missing"]), 0)

    def test_marketing_activation_lists_all_seven_requirements(self):
        result = validate_marketing_activation()
        self.assertEqual(len(result["missing"]), 7)

    def test_marketing_activation_reason_mentions_t4_13(self):
        result = validate_marketing_activation()
        self.assertIn("T4-13", result["reason"])

    def test_marketing_activation_reason_mentions_requirements(self):
        result = validate_marketing_activation()
        self.assertIn("activation_requirements", result["reason"].lower())

    def test_marketing_activation_missing_contract(self):
        result = validate_marketing_activation()
        self.assertIn("contract", result["missing"][0].lower())

    def test_marketing_activation_missing_capability_profile(self):
        result = validate_marketing_activation()
        missing_strs = " ".join(result["missing"]).lower()
        self.assertIn("capability", missing_strs)

    def test_marketing_activation_missing_boundaries(self):
        result = validate_marketing_activation()
        missing_strs = " ".join(result["missing"]).lower()
        self.assertIn("boundary", missing_strs)

    def test_marketing_activation_missing_allowed_tools(self):
        result = validate_marketing_activation()
        missing_strs = " ".join(result["missing"]).lower()
        self.assertIn("tool", missing_strs)

    def test_marketing_activation_missing_security_review(self):
        result = validate_marketing_activation()
        missing_strs = " ".join(result["missing"]).lower()
        self.assertIn("security", missing_strs)

    def test_marketing_activation_missing_batch_qa(self):
        result = validate_marketing_activation()
        missing_strs = " ".join(result["missing"]).lower()
        self.assertIn("qa", missing_strs)

    def test_marketing_activation_missing_delegation_tests(self):
        result = validate_marketing_activation()
        missing_strs = " ".join(result["missing"]).lower()
        self.assertIn("delegation", missing_strs)


# ===========================================================================
# Additional structural tests
# ===========================================================================

class TestT4_Structure(unittest.TestCase):
    """Structural checks on the registry module."""

    def test_all_active_agents_have_active_status(self):
        for aid in ("tola", "rhythm", "growth", "scholar"):
            profile = PROFILES[aid]
            self.assertEqual(
                profile.availability_status, ACTIVE,
                f"{aid} should be ACTIVE",
            )

    def test_marketing_is_future_not_available(self):
        profile = PROFILES["marketing"]
        self.assertEqual(profile.availability_status, FUTURE_NOT_AVAILABLE)

    def test_all_profiles_have_version(self):
        for aid, profile in PROFILES.items():
            self.assertIsNotNone(profile.version)
            self.assertGreater(len(profile.version), 0)

    def test_all_profiles_have_last_updated_at(self):
        for aid, profile in PROFILES.items():
            self.assertIsNotNone(profile.last_updated_at)
            self.assertGreater(len(profile.last_updated_at), 0)

    def test_all_profiles_have_activation_requirements(self):
        for aid, profile in PROFILES.items():
            self.assertIsNotNone(profile.activation_requirements)

    def test_marketing_activation_requirements_not_empty(self):
        profile = PROFILES["marketing"]
        self.assertGreater(len(profile.activation_requirements), 0)

    def test_non_marketing_activation_requirements_empty(self):
        for aid in ("tola", "rhythm", "growth", "scholar"):
            profile = PROFILES[aid]
            self.assertEqual(len(profile.activation_requirements), 0)

    def test_agent_capability_get_returns_dict(self):
        result = agent_capability_get("tola")
        self.assertIsInstance(result, dict)
        self.assertIn("agent_id", result)
        self.assertIn("domain", result)
        self.assertIn("responsibilities", result)
        self.assertIn("allowed_tools", result)
        self.assertIn("forbidden_actions", result)
        self.assertIn("skills", result)
        self.assertIn("availability_status", result)
        self.assertIn("activation_requirements", result)
        self.assertIn("version", result)
        self.assertIn("last_updated_at", result)

    def test_agent_capability_get_returns_none_for_unknown(self):
        result = agent_capability_get("unknown_agent")
        self.assertIsNone(result)

    def test_agent_boundary_check_returns_dict_with_allowed_and_reason(self):
        result = agent_boundary_check("tola", "blackboard_read")
        self.assertIn("allowed", result)
        self.assertIn("reason", result)
        self.assertIsInstance(result["allowed"], bool)

    def test_agent_current_load_get_default_zero(self):
        self.assertEqual(agent_current_load_get("tola"), 0)

    def test_agent_current_load_get_from_state(self):
        load_state = {"tola": 3, "rhythm": 7}
        self.assertEqual(agent_current_load_get("tola", load_state), 3)
        self.assertEqual(agent_current_load_get("rhythm", load_state), 7)
        self.assertEqual(agent_current_load_get("growth", load_state), 0)

    def test_agent_current_load_get_with_none_state(self):
        self.assertEqual(agent_current_load_get("tola", None), 0)

    def test_routing_table_is_non_empty(self):
        self.assertGreater(len(ROUTING_TABLE), 0)

    def test_routing_table_maps_scheduling_to_rhythm(self):
        self.assertEqual(ROUTING_TABLE.get("scheduling"), "rhythm")

    def test_routing_table_maps_product_to_growth(self):
        self.assertEqual(ROUTING_TABLE.get("product"), "growth")

    def test_routing_table_maps_learning_to_scholar(self):
        self.assertEqual(ROUTING_TABLE.get("learning"), "scholar")

    def test_enforce_boundary_allows_valid_action(self):
        result = enforce_boundary("tola", "blackboard_read")
        self.assertTrue(result["allowed"])

    def test_enforce_boundary_rejects_invalid_action(self):
        with self.assertRaises(BoundaryViolation):
            enforce_boundary("growth", "direct_schedule_write")

    def test_future_specialist_dependency_is_dataclass(self):
        dep = FutureSpecialistDependency(
            work_description="test work",
            required_domain="marketing",
            intended_agent_id="marketing",
            reason="test",
        )
        self.assertEqual(dep.work_description, "test work")
        self.assertEqual(dep.required_domain, "marketing")
        self.assertEqual(dep.intended_agent_id, "marketing")
        self.assertEqual(dep.status, "DEFERRED")

    def test_availability_status_enum_values(self):
        self.assertEqual(ACTIVE.value, "ACTIVE")
        self.assertEqual(FUTURE_NOT_AVAILABLE.value, "FUTURE_NOT_AVAILABLE")
        self.assertEqual(DISABLED.value, "DISABLED")
        self.assertEqual(DEGRADED.value, "DEGRADED")


if __name__ == "__main__":
    unittest.main()