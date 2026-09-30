"""
Batch S10 -- Learning-Goal Decomposition QA Tests.
S10-01..S10-05 plus edge cases (PAUSED/SUPERSEDED goals,
evidence requirements, deterministic repeat, malformed goal rejection).
Plain ASCII. Python 3 stdlib only. No network. No real clocks.
"""

import unittest

from scholar.decomposition.registry import (
    LearningGoalDecomposer,
    DecompositionResult,
)
from scholar.curriculum.registry import CurriculumRegistry
from scholar.curriculum.proficiency_registry import ProficiencyRegistry
from scholar.goals.registry import GoalRegistry
from scholar.fixtures.curriculum import (
    HANDBOOK_SOURCE_V1,
    HANDBOOK_SOURCE_V2,
    HANDBOOK_NODE_VENT_BASICS,
    HANDBOOK_NODE_SEPSIS_BASICS,
    OUTCOME_VENT_01,
    OUTCOME_VENT_02,
    OUTCOME_SEPSIS_01,
    LINK_SEPSIS_TO_VENT,
    LINK_VENT_BASICS_TO_LUNG_PROTECTIVE,
    INTENSIQ_MAPPING_VENT,
    INTENSIQ_MAPPING_SEPSIS,
)
from scholar.fixtures.proficiency import (
    STEP2_PROFICIENCY_SOURCE_V1,
    STEP3_PROFICIENCY_SOURCE_V1,
    PROFICIENCY_VENT_V1,
    PROFICIENCY_HEMO_V1,
    TOPIC_LINK_VENT_TO_LUNG,
    TOPIC_LINK_VENT_TO_WEANING,
    TOPIC_LINK_HEMO_TO_ARTERIAL,
    TOPIC_LINK_VENT_PREREQ,
    EVIDENCE_LINK_VENT_SUPPORTS,
    EVIDENCE_LINK_VENT_CONTRADICTS,
    EVIDENCE_LINK_HEMO_REQUIRES,
    EVIDENCE_LINK_VENT_INFORMS,
)
from scholar.fixtures.goals import (
    DIRECT_USER_SOURCE_V1,
    DIRECT_USER_SOURCE_V2,
    TOLA_SOURCE_V1,
    GOAL_VENT_DIRECT_V1,
    GOAL_VENT_TOLA_V1,
    GOAL_HEMO_DIRECT_V1,
)
from scholar.fixtures.decomposition import (
    VENT_GOAL_TARGET,
    MULTI_DOMAIN_GOAL_TARGET,
    UNREALISTIC_HORIZON_GOAL_TARGET,
    UNKNOWN_PROFICIENCY_GOAL_TARGET,
    VENT_GOAL_PAUSED,
    VENT_GOAL_SUPERSEDED,
    VENT_GOAL_WITH_EVIDENCE,
    MALFORMED_GOAL_MISSING_TITLE,
    MALFORMED_GOAL_NON_STRING_TITLE,
    MALFORMED_GOAL_EMPTY_ID,
    make_decomposer,
)


def _fake_now():
    from datetime import datetime
    return datetime(2026, 9, 30, 12, 0, 0)


def _build_decomposer(clock=None):
    """Build a LearningGoalDecomposer with fully populated registries."""
    clock = clock or _fake_now

    cr = CurriculumRegistry(clock=clock)
    cr.add_source(**HANDBOOK_SOURCE_V1)
    cr.add_source(**HANDBOOK_SOURCE_V2)
    cr.add_node(**HANDBOOK_NODE_VENT_BASICS)
    cr.add_node(**HANDBOOK_NODE_SEPSIS_BASICS)
    cr.add_outcome(**OUTCOME_VENT_01)
    cr.add_outcome(**OUTCOME_VENT_02)
    cr.add_outcome(**OUTCOME_SEPSIS_01)
    cr.add_topic_link(**LINK_SEPSIS_TO_VENT)
    cr.add_topic_link(**LINK_VENT_BASICS_TO_LUNG_PROTECTIVE)
    cr.map_intensiq_topic(**INTENSIQ_MAPPING_VENT)
    cr.map_intensiq_topic(**INTENSIQ_MAPPING_SEPSIS)

    pr = ProficiencyRegistry(clock=clock)
    pr.add_source(**STEP2_PROFICIENCY_SOURCE_V1)
    pr.add_source(**STEP3_PROFICIENCY_SOURCE_V1)
    pr.ingest_proficiency(**PROFICIENCY_VENT_V1)
    pr.ingest_proficiency(**PROFICIENCY_HEMO_V1)
    pr.add_topic_link(**TOPIC_LINK_VENT_TO_LUNG)
    pr.add_topic_link(**TOPIC_LINK_VENT_TO_WEANING)
    pr.add_topic_link(**TOPIC_LINK_HEMO_TO_ARTERIAL)
    pr.add_topic_link(**TOPIC_LINK_VENT_PREREQ)
    pr.add_evidence_link(**EVIDENCE_LINK_VENT_SUPPORTS)
    pr.add_evidence_link(**EVIDENCE_LINK_VENT_CONTRADICTS)
    pr.add_evidence_link(**EVIDENCE_LINK_HEMO_REQUIRES)
    pr.add_evidence_link(**EVIDENCE_LINK_VENT_INFORMS)

    gr = GoalRegistry(clock=clock)
    gr.add_source(**DIRECT_USER_SOURCE_V1)
    gr.add_source(**DIRECT_USER_SOURCE_V2)
    gr.add_source(**TOLA_SOURCE_V1)
    gr.create_goal(**GOAL_VENT_DIRECT_V1)
    gr.create_goal(**GOAL_HEMO_DIRECT_V1)

    return LearningGoalDecomposer(
        curriculum_registry=cr,
        proficiency_registry=pr,
        goal_registry=gr,
        clock=clock,
    )


# ====================================================================== #
#  S10-01: Mechanical ventilation goal maps to relevant curriculum
# ====================================================================== #


class TestS10_01MechanicalVentilationMapsToCurriculum(unittest.TestCase):
    def test_ventilation_goal_maps_to_ventilation_node(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertGreater(len(result.curriculum_nodes), 0)
        vent_nodes = [
            cn for cn in result.curriculum_nodes
            if "ventilation" in cn["node_title"].lower()
        ]
        self.assertGreater(len(vent_nodes), 0)

    def test_ventilation_goal_maps_to_ventilation_proficiency(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        vent_profs = [
            pm for pm in result.proficiencies
            if pm["proficiency_id"] == "prof-vent-01"
        ]
        self.assertGreater(len(vent_profs), 0)

    def test_ventilation_goal_has_learning_outcomes(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        vent_node = [
            cn for cn in result.curriculum_nodes
            if cn["node_id"] == "node-vent-basics"
        ][0]
        self.assertGreater(len(vent_node["learning_outcomes"]), 0)

    def test_ventilation_goal_has_mastery_dimensions(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertGreater(len(result.mastery_dimensions), 0)

    def test_ventilation_goal_has_evidence_requirements(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertGreater(len(result.evidence_requirements), 0)

    def test_ventilation_goal_time_horizon_six_weeks(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertEqual(result.time_horizon_days, 42)

    def test_ventilation_goal_time_horizon_not_risk(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertFalse(result.time_horizon_risk)

    def test_ventilation_goal_grounded_in_s7_registry(self):
        """Mappings must come from the curriculum registry, not hard-coded."""
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for cn in result.curriculum_nodes:
            node = decomposer._curriculum.get_node(cn["node_id"])
            self.assertIsNotNone(node)
            source = decomposer._curriculum.get_source(
                cn["source_id"], version=cn["source_version"]
            )
            self.assertIsNotNone(source)

    def test_ventilation_goal_grounded_in_s8_registry(self):
        """Proficiency mappings must come from the proficiency registry."""
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for pm in result.proficiencies:
            prof = decomposer._proficiency.get_proficiency(
                pm["proficiency_id"]
            )
            self.assertIsNotNone(prof)

    def test_ventilation_goal_deterministic_key_present(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertIsNotNone(result.deterministic_key)
        self.assertGreater(len(result.deterministic_key), 0)


# ====================================================================== #
#  S10-02: Multi-domain goal decomposes correctly
# ====================================================================== #


class TestS10_02MultiDomainGoal(unittest.TestCase):
    def test_multi_domain_goal_has_multiple_domains(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-multi-01",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation and haemodynamic monitoring",
            "description": (
                "Become competent in both mechanical ventilation and "
                "advanced haemodynamic monitoring within eight weeks."
            ),
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-multi-01")
        self.assertGreater(result.domain_count, 1)
        self.assertTrue(result.is_multi_domain)

    def test_multi_domain_goal_maps_to_ventilation_and_haemodynamics(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-multi-01b",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation and haemodynamic monitoring",
            "description": (
                "Become competent in both mechanical ventilation and "
                "advanced haemodynamic monitoring within eight weeks."
            ),
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-multi-01b")
        domains = {pm["domain"] for pm in result.proficiencies}
        self.assertIn("mechanical_ventilation", domains)
        self.assertIn("haemodynamic_monitoring", domains)

    def test_single_domain_goal_is_not_multi_domain(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertIsInstance(result.is_multi_domain, bool)


# ====================================================================== #
#  S10-03: Missing prerequisite detected
# ====================================================================== #


class TestS10_03MissingPrerequisiteDetected(unittest.TestCase):
    def test_missing_prerequisite_reported(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-sepsis-only",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn sepsis recognition",
            "description": "Understand sepsis recognition and qSOFA criteria.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-sepsis-only")
        self.assertGreater(len(result.missing_prerequisites), 0)

    def test_missing_prerequisite_mentions_node_id(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-sepsis-only-2",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn sepsis recognition",
            "description": "Understand sepsis recognition and qSOFA criteria.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-sepsis-only-2")
        missing_str = " ".join(result.missing_prerequisites)
        self.assertIn("node-vent-basics", missing_str)

    def test_no_missing_prerequisite_when_all_covered(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertEqual(len(result.missing_prerequisites), 0)

    def test_prerequisite_links_are_resolved(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-sepsis-only-3",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn sepsis recognition",
            "description": "Understand sepsis recognition and qSOFA criteria.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-sepsis-only-3")
        self.assertGreater(len(result.prerequisites), 0)


# ====================================================================== #
#  S10-04: Unrealistic time horizon flagged as risk
# ====================================================================== #


class TestS10_04UnrealisticHorizonFlagged(unittest.TestCase):
    def test_unrealistic_horizon_flagged_as_risk(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-horizon-01",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 20 weeks",
            "description": "Become highly competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-horizon-01")
        self.assertIsNotNone(result.time_horizon_days)
        self.assertTrue(result.time_horizon_risk)

    def test_reasonable_horizon_not_flagged(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertFalse(result.time_horizon_risk)

    def test_no_horizon_returns_none_and_no_risk(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-no-horizon",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn mechanical ventilation",
            "description": "Understand ventilator modes.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-no-horizon")
        self.assertIsNone(result.time_horizon_days)
        self.assertFalse(result.time_horizon_risk)

    def test_horizon_days_within_limit_not_risk(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-horizon-ok",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 4 weeks",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-horizon-ok")
        self.assertEqual(result.time_horizon_days, 28)
        self.assertFalse(result.time_horizon_risk)

    def test_horizon_exactly_at_limit_not_risk(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertEqual(result.time_horizon_days, 42)
        self.assertFalse(result.time_horizon_risk)

    def test_word_number_horizon_parsed(self):
        """Time horizon with word numbers (e.g. 'six weeks') is parsed."""
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-word-horizon",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within six weeks",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-word-horizon")
        self.assertEqual(result.time_horizon_days, 42)


# ====================================================================== #
#  S10-05: Unknown proficiency no invented mapping
# ====================================================================== #


class TestS10_05UnknownProficiencyNoInventedMapping(unittest.TestCase):
    def test_unknown_proficiency_no_curriculum_nodes(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-unknown-01",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn quantum mechanics",
            "description": "Understand quantum mechanics for no obvious clinical reason.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-unknown-01")
        self.assertEqual(len(result.curriculum_nodes), 0)

    def test_unknown_proficiency_no_proficiency_mappings(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-unknown-02",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn quantum mechanics",
            "description": "Understand quantum mechanics for no obvious clinical reason.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-unknown-02")
        self.assertEqual(len(result.proficiencies), 0)

    def test_unknown_proficiency_no_invented_curriculum_nodes(self):
        """S10-05: No invented curriculum nodes for unknown proficiency."""
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-unknown-03",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn quantum mechanics",
            "description": "Understand quantum mechanics for no obvious clinical reason.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-unknown-03")
        for cn in result.curriculum_nodes:
            node = decomposer._curriculum.get_node(cn["node_id"])
            self.assertIsNotNone(node)

    def test_unknown_proficiency_zero_domains(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-unknown-04",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn quantum mechanics",
            "description": "Understand quantum mechanics for no obvious clinical reason.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-unknown-04")
        self.assertEqual(result.domain_count, 0)
        self.assertFalse(result.is_multi_domain)


# ====================================================================== #
#  Edge case: PAUSED goal decomposition still works
# ====================================================================== #


class TestEdgeCasePausedGoalDecomposition(unittest.TestCase):
    def test_paused_goal_decomposes(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**VENT_GOAL_PAUSED)
        decomposer._goals.pause_goal("goal-vent-paused")
        result = decomposer.decompose("goal-vent-paused")
        self.assertEqual(result.goal_state, "PAUSED")
        self.assertEqual(result.goal_id, "goal-vent-paused")

    def test_paused_goal_has_same_mappings_as_active(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**VENT_GOAL_PAUSED)
        decomposer._goals.pause_goal("goal-vent-paused")
        result_paused = decomposer.decompose("goal-vent-paused")
        result_active = decomposer.decompose("goal-vent-01")
        self.assertEqual(result_paused.curriculum_nodes, result_active.curriculum_nodes)
        self.assertEqual(result_paused.proficiencies, result_active.proficiencies)


# ====================================================================== #
#  Edge case: SUPERSEDED goal decomposition still works
# ====================================================================== #


class TestEdgeCaseSupersededGoalDecomposition(unittest.TestCase):
    def test_superseded_goal_decomposes(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**VENT_GOAL_SUPERSEDED)
        decomposer._goals.supersede_goal(
            goal_id="goal-vent-superseded",
            new_title="Updated mechanical ventilation goal",
            new_description="Updated description with new requirements.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        result = decomposer.decompose("goal-vent-superseded")
        self.assertEqual(result.goal_state, "SUPERSEDED")
        self.assertEqual(result.goal_id, "goal-vent-superseded")

    def test_superseded_goal_retains_mappings(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**VENT_GOAL_SUPERSEDED)
        decomposer._goals.supersede_goal(
            goal_id="goal-vent-superseded",
            new_title="Updated mechanical ventilation goal",
            new_description="Updated description with new requirements.",
            new_source_id="src-user-001",
            new_source_version="2.0",
            new_source_type="direct_user",
        )
        result = decomposer.decompose("goal-vent-superseded")
        self.assertGreater(len(result.curriculum_nodes), 0)
        self.assertGreater(len(result.proficiencies), 0)


# ====================================================================== #
#  Edge case: Evidence requirements present
# ====================================================================== #


class TestEdgeCaseEvidenceRequirementsPresent(unittest.TestCase):
    def test_evidence_requirements_not_empty_for_vent_goal(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertGreater(len(result.evidence_requirements), 0)

    def test_evidence_requirements_have_required_fields(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for er in result.evidence_requirements:
            self.assertIn("evidence_id", er)
            self.assertIn("link_type", er)
            self.assertIn("source", er)
            self.assertEqual(er["source"], "proficiency")

    def test_evidence_requirements_traceable_to_proficiency(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for er in result.evidence_requirements:
            found = False
            for pm in result.proficiencies:
                if er["evidence_id"] in pm["linked_evidence"]:
                    found = True
                    break
            self.assertTrue(found, f"Evidence {er['evidence_id']} not found in any mapped proficiency")


# ====================================================================== #
#  Edge case: Deterministic repeat calls give identical output
# ====================================================================== #


class TestEdgeCaseDeterministicRepeatCalls(unittest.TestCase):
    def test_repeat_calls_produce_identical_result(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.deterministic_key, result2.deterministic_key)

    def test_repeat_calls_produce_identical_curriculum_nodes(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.curriculum_nodes, result2.curriculum_nodes)

    def test_repeat_calls_produce_identical_proficiencies(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.proficiencies, result2.proficiencies)

    def test_repeat_calls_produce_identical_prerequisites(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.prerequisites, result2.prerequisites)

    def test_repeat_calls_produce_identical_missing_prerequisites(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.missing_prerequisites, result2.missing_prerequisites)

    def test_repeat_calls_produce_identical_mastery_dimensions(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.mastery_dimensions, result2.mastery_dimensions)

    def test_repeat_calls_produce_identical_time_horizon(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.time_horizon_days, result2.time_horizon_days)
        self.assertEqual(result1.time_horizon_risk, result2.time_horizon_risk)

    def test_repeat_calls_produce_identical_evidence_requirements(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.evidence_requirements, result2.evidence_requirements)

    def test_repeat_calls_produce_identical_domain_count(self):
        decomposer = _build_decomposer()
        result1 = decomposer.decompose("goal-vent-01")
        result2 = decomposer.decompose("goal-vent-01")
        self.assertEqual(result1.domain_count, result2.domain_count)
        self.assertEqual(result1.is_multi_domain, result2.is_multi_domain)


# ====================================================================== #
#  Edge case: Malformed goal rejected
# ====================================================================== #


class TestEdgeCaseMalformedGoalRejected(unittest.TestCase):
    def test_rejects_empty_goal_id(self):
        decomposer = _build_decomposer()
        with self.assertRaises(ValueError) as cm:
            decomposer.decompose("")
        self.assertIn("goal_id", str(cm.exception))

    def test_rejects_non_string_goal_id(self):
        decomposer = _build_decomposer()
        with self.assertRaises(ValueError):
            decomposer.decompose(12345)

    def test_rejects_nonexistent_goal_id(self):
        decomposer = _build_decomposer()
        with self.assertRaises(ValueError) as cm:
            decomposer.decompose("goal-nonexistent")
        self.assertIn("does not exist", str(cm.exception))

    def test_rejects_none_goal_id(self):
        decomposer = _build_decomposer()
        with self.assertRaises(ValueError):
            decomposer.decompose(None)


# ====================================================================== #
#  Edge case: Tola-sourced goal decomposes correctly
# ====================================================================== #


class TestEdgeCaseTolaGoalDecomposition(unittest.TestCase):
    def test_tola_goal_decomposes(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**GOAL_VENT_TOLA_V1)
        result = decomposer.decompose("goal-vent-02")
        self.assertEqual(result.goal_id, "goal-vent-02")
        self.assertEqual(result.goal_state, "ACTIVE")
        self.assertGreater(len(result.curriculum_nodes), 0)

    def test_tola_goal_has_correct_source_type(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**GOAL_VENT_TOLA_V1)
        result = decomposer.decompose("goal-vent-02")
        self.assertEqual(result.goal_title, "Mechanical ventilation proficiency for Step 2")


# ====================================================================== #
#  Edge case: STOPPED goal decomposition
# ====================================================================== #


class TestEdgeCaseStoppedGoalDecomposition(unittest.TestCase):
    def test_stopped_goal_decomposes(self):
        decomposer = _build_decomposer()
        decomposer._goals.stop_goal("goal-vent-01")
        result = decomposer.decompose("goal-vent-01")
        self.assertEqual(result.goal_state, "STOPPED")
        self.assertGreater(len(result.curriculum_nodes), 0)


# ====================================================================== #
#  Edge case: Clock injection for deterministic testing
# ====================================================================== #


class TestEdgeCaseClockInjection(unittest.TestCase):
    def test_decomposer_with_injected_clock(self):
        decomposer = _build_decomposer(clock=_fake_now)
        result = decomposer.decompose("goal-vent-01")
        self.assertIsInstance(result, DecompositionResult)
        self.assertEqual(result.goal_id, "goal-vent-01")

    def test_decomposer_without_clock_uses_default(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertIsInstance(result, DecompositionResult)


# ====================================================================== #
#  Edge case: No matching curriculum nodes for unrelated goal
# ====================================================================== #


class TestEdgeCaseNoMatchingCurriculumNodes(unittest.TestCase):
    def test_no_matching_nodes_returns_empty_list(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-no-match",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn astrophysics",
            "description": "Understand stellar evolution and galactic dynamics.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-no-match")
        self.assertEqual(len(result.curriculum_nodes), 0)


# ====================================================================== #
#  Edge case: Deterministic key changes when goal changes
# ====================================================================== #


class TestEdgeCaseDeterministicKeyChanges(unittest.TestCase):
    def test_different_goals_have_different_keys(self):
        decomposer = _build_decomposer()
        r1 = decomposer.decompose("goal-vent-01")
        decomposer._goals.create_goal(**{
            "goal_id": "goal-other",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn haemodynamic monitoring",
            "description": "Understand arterial line interpretation.",
            "source_type": "direct_user",
        })
        r2 = decomposer.decompose("goal-other")
        self.assertNotEqual(r1.deterministic_key, r2.deterministic_key)


# ====================================================================== #
#  Edge case: Multiple calls on same decomposer produce same key
# ====================================================================== #


class TestEdgeCaseMultipleCallsSameKey(unittest.TestCase):
    def test_three_calls_produce_same_key(self):
        decomposer = _build_decomposer()
        r1 = decomposer.decompose("goal-vent-01")
        r2 = decomposer.decompose("goal-vent-01")
        r3 = decomposer.decompose("goal-vent-01")
        self.assertEqual(r1.deterministic_key, r2.deterministic_key)
        self.assertEqual(r2.deterministic_key, r3.deterministic_key)


# ====================================================================== #
#  Edge case: Decomposition result fields are all present
# ====================================================================== #


class TestEdgeCaseDecompositionResultFields(unittest.TestCase):
    def test_all_fields_present(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertIsNotNone(result.goal_id)
        self.assertIsNotNone(result.goal_title)
        self.assertIsNotNone(result.goal_state)
        self.assertIsNotNone(result.curriculum_nodes)
        self.assertIsNotNone(result.proficiencies)
        self.assertIsNotNone(result.prerequisites)
        self.assertIsNotNone(result.missing_prerequisites)
        self.assertIsNotNone(result.mastery_dimensions)
        self.assertIsNotNone(result.time_horizon_days)
        self.assertIsNotNone(result.time_horizon_risk)
        self.assertIsNotNone(result.evidence_requirements)
        self.assertIsNotNone(result.domain_count)
        self.assertIsNotNone(result.is_multi_domain)
        self.assertIsNotNone(result.deterministic_key)


# ====================================================================== #
#  Edge case: Decomposition of goal version
# ====================================================================== #


class TestEdgeCaseDecomposeGoalVersion(unittest.TestCase):
    def test_decompose_with_version_parameter(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-vent-v2",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Original goal title",
            "description": "Original description.",
            "source_type": "direct_user",
        })
        decomposer._goals.supersede_goal(
            goal_id="goal-vent-v2",
            new_title="Updated goal title",
            new_description="Updated description.",
            new_source_id="src-user-001",
            new_source_version="1.0",
            new_source_type="direct_user",
        )
        r1 = decomposer.decompose("goal-vent-v2", goal_version=1)
        self.assertEqual(r1.goal_title, "Original goal title")
        r2 = decomposer.decompose("goal-vent-v2", goal_version=2)
        self.assertEqual(r2.goal_title, "Updated goal title")


# ====================================================================== #
#  Edge case: Decomposition result is frozen (immutable)
# ====================================================================== #


class TestEdgeCaseDecompositionResultImmutable(unittest.TestCase):
    def test_result_is_frozen_dataclass(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        with self.assertRaises(Exception):
            result.goal_id = "tampered"


# ====================================================================== #
#  Edge case: No invented proficiency for goal with no matching keywords
# ====================================================================== #


class TestEdgeCaseNoInventedProficiency(unittest.TestCase):
    def test_no_proficiency_for_unrelated_goal(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-unrelated",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn basket weaving",
            "description": "Master the art of basket weaving for relaxation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-unrelated")
        self.assertEqual(len(result.proficiencies), 0)
        self.assertEqual(len(result.curriculum_nodes), 0)
        self.assertEqual(len(result.evidence_requirements), 0)


# ====================================================================== #
#  Edge case: Mastery dimensions are from KNOWN_MASTERY_DIMENSIONS set
# ====================================================================== #


class TestEdgeCaseMasteryDimensionsValid(unittest.TestCase):
    def test_all_mastery_dimensions_are_known(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for dim in result.mastery_dimensions:
            self.assertIn(dim, decomposer.KNOWN_MASTERY_DIMENSIONS)


# ====================================================================== #
#  Edge case: Decomposition of goal with no time horizon
# ====================================================================== #


class TestEdgeCaseNoTimeHorizon(unittest.TestCase):
    def test_no_time_horizon_returns_none(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-no-horizon-2",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn mechanical ventilation",
            "description": "Understand ventilator modes and lung-protective strategies.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-no-horizon-2")
        self.assertIsNone(result.time_horizon_days)
        self.assertFalse(result.time_horizon_risk)


# ====================================================================== #
#  Edge case: Decomposition result is JSON-serialisable (basic types)
# ====================================================================== #


class TestEdgeCaseResultSerialisable(unittest.TestCase):
    def test_result_fields_are_basic_types(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertIsInstance(result.goal_id, str)
        self.assertIsInstance(result.goal_title, str)
        self.assertIsInstance(result.goal_state, str)
        self.assertIsInstance(result.curriculum_nodes, list)
        self.assertIsInstance(result.proficiencies, list)
        self.assertIsInstance(result.prerequisites, list)
        self.assertIsInstance(result.missing_prerequisites, list)
        self.assertIsInstance(result.mastery_dimensions, list)
        self.assertIsInstance(result.time_horizon_days, (int, type(None)))
        self.assertIsInstance(result.time_horizon_risk, bool)
        self.assertIsInstance(result.evidence_requirements, list)
        self.assertIsInstance(result.domain_count, int)
        self.assertIsInstance(result.is_multi_domain, bool)
        self.assertIsInstance(result.deterministic_key, str)


# ====================================================================== #
#  Edge case: Prerequisite detection for goal mapping to node with
#  prerequisite not in mapped set
# ====================================================================== #


class TestEdgeCasePrerequisiteDetection(unittest.TestCase):
    def test_prerequisite_detected_when_target_not_mapped(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-sepsis-prereq-test",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn sepsis recognition only",
            "description": "Understand sepsis recognition and qSOFA criteria only.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-sepsis-prereq-test")
        self.assertGreater(len(result.missing_prerequisites), 0)


# ====================================================================== #
#  Edge case: Evidence requirements include all linked evidence
# ====================================================================== #


class TestEdgeCaseEvidenceRequirementsComplete(unittest.TestCase):
    def test_evidence_requirements_include_all_linked_evidence(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        evidence_ids = {er["evidence_id"] for er in result.evidence_requirements}
        self.assertIn("evidence-vent-01", evidence_ids)
        self.assertIn("evidence-vent-02", evidence_ids)


# ====================================================================== #
#  Edge case: Decomposition of goal with digit-based time horizon
# ====================================================================== #


class TestEdgeCaseDigitTimeHorizon(unittest.TestCase):
    def test_digit_based_horizon_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-digit-horizon",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 8 weeks",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-digit-horizon")
        self.assertEqual(result.time_horizon_days, 56)


# ====================================================================== #
#  Edge case: Decomposition of goal with "within" prefix
# ====================================================================== #


class TestEdgeCaseWithinPrefixTimeHorizon(unittest.TestCase):
    def test_within_prefix_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-within-prefix",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation",
            "description": "Become competent within 6 weeks.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-within-prefix")
        self.assertEqual(result.time_horizon_days, 42)


# ====================================================================== #
#  Edge case: Decomposition of goal with digit-based days horizon
# ====================================================================== #


class TestEdgeCaseDigitDaysHorizon(unittest.TestCase):
    def test_digit_days_horizon_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-digit-days",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 30 days",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-digit-days")
        self.assertEqual(result.time_horizon_days, 30)


# ====================================================================== #
#  Edge case: Decomposition of goal with digit-based months horizon
# ====================================================================== #


class TestEdgeCaseDigitMonthsHorizon(unittest.TestCase):
    def test_digit_months_horizon_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-digit-months",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 3 months",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-digit-months")
        self.assertEqual(result.time_horizon_days, 90)


# ====================================================================== #
#  Edge case: Decomposition of goal with word-based months horizon
# ====================================================================== #


class TestEdgeCaseWordMonthsHorizon(unittest.TestCase):
    def test_word_months_horizon_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-word-months",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within three months",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-word-months")
        self.assertEqual(result.time_horizon_days, 90)


# ====================================================================== #
#  Edge case: Decomposition of goal with word-based days horizon
# ====================================================================== #


class TestEdgeCaseWordDaysHorizon(unittest.TestCase):
    def test_word_days_horizon_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-word-days",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within seven days",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-word-days")
        self.assertEqual(result.time_horizon_days, 7)


# ====================================================================== #
#  Edge case: Decomposition of goal with word-based weeks horizon
# ====================================================================== #


class TestEdgeCaseWordWeeksHorizon(unittest.TestCase):
    def test_word_weeks_horizon_parsed(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-word-weeks",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within two weeks",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-word-weeks")
        self.assertEqual(result.time_horizon_days, 14)


# ====================================================================== #
#  Edge case: Decomposition of goal with unsupported time unit (years)
# ====================================================================== #


class TestEdgeCaseUnsupportedTimeUnit(unittest.TestCase):
    def test_years_not_supported_returns_none(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-years",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 1 year",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-years")
        self.assertIsNone(result.time_horizon_days)
        self.assertFalse(result.time_horizon_risk)


# ====================================================================== #
#  Edge case: Decomposition of goal with unsupported time unit (hours)
# ====================================================================== #


class TestEdgeCaseUnsupportedHoursUnit(unittest.TestCase):
    def test_hours_not_supported_returns_none(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-hours",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 48 hours",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-hours")
        self.assertIsNone(result.time_horizon_days)
        self.assertFalse(result.time_horizon_risk)


# ====================================================================== #
#  Edge case: Decomposition of goal with unsupported time unit (minutes)
# ====================================================================== #


class TestEdgeCaseUnsupportedMinutesUnit(unittest.TestCase):
    def test_minutes_not_supported_returns_none(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-minutes",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 30 minutes",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-minutes")
        self.assertIsNone(result.time_horizon_days)
        self.assertFalse(result.time_horizon_risk)


# ====================================================================== #
#  Edge case: Decomposition of goal with unsupported time unit (seconds)
# ====================================================================== #


class TestEdgeCaseUnsupportedSecondsUnit(unittest.TestCase):
    def test_seconds_not_supported_returns_none(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-seconds",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within 60 seconds",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-seconds")
        self.assertIsNone(result.time_horizon_days)
        self.assertFalse(result.time_horizon_risk)


# ====================================================================== #
#  Edge case: Curriculum mapping has correct source provenance
# ====================================================================== #


class TestEdgeCaseCurriculumMappingProvenance(unittest.TestCase):
    def test_curriculum_mapping_has_source_id(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for cn in result.curriculum_nodes:
            self.assertIn("source_id", cn)
            self.assertIn("source_version", cn)

    def test_curriculum_mapping_has_node_kind(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for cn in result.curriculum_nodes:
            self.assertIn("node_kind", cn)
            self.assertIn("node_title", cn)


# ====================================================================== #
#  Edge case: Proficiency mapping has verbatim requirement
# ====================================================================== #


class TestEdgeCaseProficiencyMappingVerbatim(unittest.TestCase):
    def test_proficiency_mapping_has_verbatim_requirement(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        for pm in result.proficiencies:
            self.assertIn("verbatim_requirement", pm)
            self.assertGreater(len(pm["verbatim_requirement"]), 0)

    def test_proficiency_mapping_preserves_verbatim(self):
        """Verbatim requirement is preserved from S8 registry, not rewritten."""
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        vent_prof = [
            pm for pm in result.proficiencies
            if pm["proficiency_id"] == "prof-vent-01"
        ][0]
        self.assertIn("ventilator modes", vent_prof["verbatim_requirement"])


# ====================================================================== #
#  Edge case: Prerequisite link types are valid
# ====================================================================== #


class TestEdgeCasePrerequisiteLinkTypes(unittest.TestCase):
    def test_prerequisite_links_have_valid_types(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-sepsis-prereq",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn sepsis recognition",
            "description": "Understand sepsis recognition and qSOFA criteria.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-sepsis-prereq")
        for pl in result.prerequisites:
            self.assertIn(pl["link_type"], {"prerequisite", "builds_on", "maps_to", "supersedes"})


# ====================================================================== #
#  Edge case: Domain count is accurate for single-domain goal
# ====================================================================== #


class TestEdgeCaseDomainCountAccuracy(unittest.TestCase):
    def test_single_domain_goal_has_domain_count_one(self):
        decomposer = _build_decomposer()
        result = decomposer.decompose("goal-vent-01")
        self.assertGreaterEqual(result.domain_count, 1)


# ====================================================================== #
#  Edge case: Evidence requirements for goal with no mapped proficiencies
# ====================================================================== #


class TestEdgeCaseEvidenceForNoProficiencies(unittest.TestCase):
    def test_no_proficiency_has_no_evidence(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-no-profs",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Learn basket weaving",
            "description": "Master the art of basket weaving.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-no-profs")
        self.assertEqual(len(result.evidence_requirements), 0)


# ====================================================================== #
#  Edge case: Deterministic key is stable across different decomposer
#  instances with same registry state
# ====================================================================== #


class TestEdgeCaseDeterministicKeyStability(unittest.TestCase):
    def test_deterministic_key_stable_across_instances(self):
        d1 = _build_decomposer()
        d2 = _build_decomposer()
        r1 = d1.decompose("goal-vent-01")
        r2 = d2.decompose("goal-vent-01")
        self.assertEqual(r1.deterministic_key, r2.deterministic_key)


# ====================================================================== #
#  Edge case: Decomposition of PAUSED goal with injected clock
# ====================================================================== #


class TestEdgeCasePausedGoalWithInjectedClock(unittest.TestCase):
    def test_paused_goal_uses_injected_clock(self):
        decomposer = _build_decomposer(clock=_fake_now)
        decomposer._goals.create_goal(**VENT_GOAL_PAUSED)
        decomposer._goals.pause_goal("goal-vent-paused")
        result = decomposer.decompose("goal-vent-paused")
        self.assertEqual(result.goal_state, "PAUSED")


# ====================================================================== #
#  Edge case: Decomposition of goal with word-number time horizon
# ====================================================================== #


class TestEdgeCaseWordNumberTimeHorizon(unittest.TestCase):
    def test_six_weeks_parsed_as_42_days(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-word-num",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within six weeks",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-word-num")
        self.assertEqual(result.time_horizon_days, 42)

    def test_three_months_parsed_as_90_days(self):
        decomposer = _build_decomposer()
        decomposer._goals.create_goal(**{
            "goal_id": "goal-three-months",
            "source_id": "src-user-001",
            "source_version": "1.0",
            "title": "Master mechanical ventilation within three months",
            "description": "Become competent in mechanical ventilation.",
            "source_type": "direct_user",
        })
        result = decomposer.decompose("goal-three-months")
        self.assertEqual(result.time_horizon_days, 90)


if __name__ == "__main__":
    unittest.main()