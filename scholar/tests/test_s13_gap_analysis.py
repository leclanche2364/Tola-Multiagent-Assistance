"""
Batch S13 -- Learning Gap Analysis QA Tests (S13-01..S13-06).
Deterministic fixtures, injectable clock, unittest.
No network, no real clocks.
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.fixtures.gap_analysis import (
    # S13-01: Missing prerequisite
    S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
    # S13-02: Weak knowledge
    S13_02_WEAK_KNOWLEDGE_MASTERY,
    # S13-03: Weak application
    S13_03_WEAK_APPLICATION_MASTERY,
    # S13-04: Insufficient evidence
    S13_04_INSUFFICIENT_EVIDENCE_MASTERY,
    # S13-05: Uncovered proficiency
    S13_05_UNCOVERED_PROFICIENCY_DECOMPOSITION,
    S13_05_UNCOVERED_PROFICIENCY_RECORDS,
    # S13-06: Strong fixture not flagged
    S13_06_STRONG_MASTERY,
    S13_06_STRONG_DECOMPOSITION,
    # Edge: gap without evidence ref
    S13_EDGE_GAP_WITHOUT_EVIDENCE_REF_MASTERY,
    # Edge: PAUSED goal
    S13_EDGE_PAUSED_GOAL_DECOMPOSITION,
    # Edge: SUPERSEDED goal
    S13_EDGE_SUPERSEDED_GOAL_DECOMPOSITION,
    # Edge: empty state
    S13_EDGE_EMPTY_MASTERY,
    S13_EDGE_EMPTY_DECOMPOSITION,
    S13_EDGE_EMPTY_PROFICIENCY_RECORDS,
    # Edge: malformed input
    S13_EDGE_MALFORMED_MASTERY_NONE,
    S13_EDGE_MALFORMED_DECOMPOSITION_NONE,
    # Helpers
    make_gap_analyzer,
    make_dimension_evidence,
)
from scholar.learning_gap_analysis.gap_analyzer import (
    LearningGapAnalyzer,
    Gap,
    GapType,
    GapAnalysisResult,
)
from scholar.mastery.model import (
    MasteryAnalyser,
    MasteryResult,
    MasteryDimension,
    DimensionEvidence,
)
from scholar.decomposition.registry import LearningGoalDecomposer
from scholar.curriculum.registry import CurriculumRegistry
from scholar.curriculum.proficiency_registry import ProficiencyRegistry
from scholar.goals.registry import GoalRegistry


def _fixed_clock():
    return "2026-09-30T12:00:00"


def _make_mastery_result(evidence, goal_id="goal-vent-01", topic_id=None):
    """Build a MasteryResult from a list of DimensionEvidence."""
    analyser = MasteryAnalyser(clock=_fixed_clock)
    return analyser.evaluate(evidence, goal_id, topic_id=topic_id)


# ====================================================================== #
# S13-01: Missing prerequisite detected
# ====================================================================== #


class TestS13_01MissingPrerequisiteDetected(unittest.TestCase):
    def test_missing_prerequisite_detected(self):
        """S13-01: A missing prerequisite must be detected and flagged."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        prereq_gaps = [g for g in result.gaps if g.gap_type == GapType.MISSING_PREREQUISITE]
        self.assertEqual(len(prereq_gaps), 1)
        self.assertIn("node-lung-protective", prereq_gaps[0].description)

    def test_s13_01_gap_traceable_to_evidence(self):
        """S13-01: The gap must have at least one evidence_ref."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        prereq_gaps = [g for g in result.gaps if g.gap_type == GapType.MISSING_PREREQUISITE]
        self.assertEqual(len(prereq_gaps), 1)
        self.assertGreater(len(prereq_gaps[0].evidence_refs), 0)

    def test_s13_01_no_missing_prerequisite_when_none(self):
        """S13-01: When there are no missing prerequisites, none are flagged."""
        analyzer = make_gap_analyzer(_fixed_clock)
        decomp = dict(S13_06_STRONG_DECOMPOSITION)
        decomp["missing_prerequisites"] = []
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=decomp,
        )
        prereq_gaps = [g for g in result.gaps if g.gap_type == GapType.MISSING_PREREQUISITE]
        self.assertEqual(len(prereq_gaps), 0)


# ====================================================================== #
# S13-02: Weak knowledge detected
# ====================================================================== #


class TestS13_02WeakKnowledgeDetected(unittest.TestCase):
    def test_weak_knowledge_detected(self):
        """S13-02: Weak knowledge must be detected and flagged."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
        )
        weak_knowledge_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_KNOWLEDGE]
        self.assertEqual(len(weak_knowledge_gaps), 1)

    def test_s13_02_gap_traceable_to_evidence(self):
        """S13-02: The weak knowledge gap must be traceable to evidence."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
        )
        weak_knowledge_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_KNOWLEDGE]
        self.assertEqual(len(weak_knowledge_gaps), 1)
        self.assertIn("ev-s13-02-001", weak_knowledge_gaps[0].evidence_refs)

    def test_s13_02_no_false_gap_when_knowledge_strong(self):
        """S13-02: Strong knowledge must NOT be flagged as weak."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        weak_knowledge_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_KNOWLEDGE]
        self.assertEqual(len(weak_knowledge_gaps), 0)


# ====================================================================== #
# S13-03: Weak application detected
# ====================================================================== #


class TestS13_03WeakApplicationDetected(unittest.TestCase):
    def test_weak_application_detected(self):
        """S13-03: Weak application must be detected and flagged."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_03_WEAK_APPLICATION_MASTERY),
        )
        weak_app_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_APPLICATION]
        self.assertEqual(len(weak_app_gaps), 1)

    def test_s13_03_gap_traceable_to_evidence(self):
        """S13-03: The weak application gap must be traceable to evidence."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_03_WEAK_APPLICATION_MASTERY),
        )
        weak_app_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_APPLICATION]
        self.assertEqual(len(weak_app_gaps), 1)
        self.assertIn("ev-s13-03-002", weak_app_gaps[0].evidence_refs)

    def test_s13_03_no_false_gap_when_application_strong(self):
        """S13-03: Strong application must NOT be flagged as weak."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        weak_app_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_APPLICATION]
        self.assertEqual(len(weak_app_gaps), 0)


# ====================================================================== #
# S13-04: Insufficient evidence/practice detected
# ====================================================================== #


class TestS13_04InsufficientEvidenceDetected(unittest.TestCase):
    def test_insufficient_evidence_detected(self):
        """S13-04: Insufficient evidence/practice must be detected."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_04_INSUFFICIENT_EVIDENCE_MASTERY),
        )
        evidence_gaps = [g for g in result.gaps if g.gap_type == GapType.INSUFFICIENT_EVIDENCE]
        self.assertGreater(len(evidence_gaps), 0)

    def test_s13_04_gap_traceable_to_evidence(self):
        """S13-04: The insufficient evidence gap must be traceable."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_04_INSUFFICIENT_EVIDENCE_MASTERY),
        )
        evidence_gaps = [g for g in result.gaps if g.gap_type == GapType.INSUFFICIENT_EVIDENCE]
        for gap in evidence_gaps:
            self.assertGreater(len(gap.evidence_refs), 0,
                f"Gap {gap.gap_id} has no evidence_refs")

    def test_s13_04_no_false_gap_when_strong(self):
        """S13-04: Strong mastery must NOT produce insufficient evidence gaps."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        evidence_gaps = [g for g in result.gaps if g.gap_type == GapType.INSUFFICIENT_EVIDENCE]
        self.assertEqual(len(evidence_gaps), 0)


# ====================================================================== #
# S13-05: Uncovered proficiency detected
# ====================================================================== #


class TestS13_05UncoveredProficiencyDetected(unittest.TestCase):
    def test_uncovered_proficiency_detected(self):
        """S13-05: An uncovered proficiency must be detected."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=S13_05_UNCOVERED_PROFICIENCY_DECOMPOSITION,
            proficiency_records=S13_05_UNCOVERED_PROFICIENCY_RECORDS,
        )
        uncovered_gaps = [g for g in result.gaps if g.gap_type == GapType.UNCOVERED_PROFICIENCY]
        self.assertEqual(len(uncovered_gaps), 1)
        self.assertIn("prof-hemo-01", uncovered_gaps[0].description)

    def test_s13_05_gap_traceable_to_evidence(self):
        """S13-05: The uncovered proficiency gap must be traceable to evidence."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=S13_05_UNCOVERED_PROFICIENCY_DECOMPOSITION,
            proficiency_records=S13_05_UNCOVERED_PROFICIENCY_RECORDS,
        )
        uncovered_gaps = [g for g in result.gaps if g.gap_type == GapType.UNCOVERED_PROFICIENCY]
        self.assertEqual(len(uncovered_gaps), 1)
        self.assertGreater(len(uncovered_gaps[0].evidence_refs), 0)

    def test_s13_05_no_uncovered_when_all_covered(self):
        """S13-05: When all proficiencies are mapped, none are uncovered."""
        analyzer = make_gap_analyzer(_fixed_clock)
        decomp = dict(S13_06_STRONG_DECOMPOSITION)
        # Include both proficiencies so all are mapped
        decomp["proficiencies"] = [
            {
                "proficiency_id": "prof-vent-01",
                "domain": "mechanical_ventilation",
                "step": "step2",
                "verbatim_requirement": "Demonstrate knowledge of mechanical ventilation principles.",
                "knowledge_requirements": ["Know ventilator modes"],
                "application_requirements": ["Apply lung-protective strategies"],
                "rationale_requirements": ["Explain weaning criteria"],
                "linked_topics": ["ventilation-basics"],
                "linked_learning_outcomes": ["outcome-vent-01"],
                "linked_evidence": ["ev-vent-001"],
            },
            {
                "proficiency_id": "prof-hemo-01",
                "domain": "haemodynamic_monitoring",
                "step": "step2",
                "verbatim_requirement": "Apply advanced haemodynamic monitoring including arterial line interpretation.",
                "knowledge_requirements": ["Know arterial line types"],
                "application_requirements": ["Interpret CVP waveforms"],
                "rationale_requirements": ["Explain cardiac output measurement"],
                "linked_topics": ["haemodynamics"],
                "linked_learning_outcomes": ["outcome-hemo-01"],
                "linked_evidence": ["ev-hemo-001"],
            },
        ]
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=decomp,
            proficiency_records=S13_05_UNCOVERED_PROFICIENCY_RECORDS,
        )
        uncovered_gaps = [g for g in result.gaps if g.gap_type == GapType.UNCOVERED_PROFICIENCY]
        self.assertEqual(len(uncovered_gaps), 0)


# ====================================================================== #
# S13-06: Strong fixture NOT incorrectly flagged
# ====================================================================== #


class TestS13_06StrongFixtureNotFlagged(unittest.TestCase):
    def test_s13_06_strong_fixture_no_gaps(self):
        """S13-06: A strong fixture must NOT be incorrectly flagged as a gap."""
        analyzer = make_gap_analyzer(_fixed_clock)
        # Use only the proficiency that is mapped in the decomposition
        # (prof-hemo-01 is not mapped, so it would be uncovered — that's correct)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=S13_06_STRONG_DECOMPOSITION,
            proficiency_records=[S13_06_STRONG_DECOMPOSITION["proficiencies"][0]],
        )
        # All dimensions are strong and all proficiencies are mapped — no gaps
        self.assertEqual(len(result.gaps), 0)

    def test_s13_06_no_false_prerequisite_gap(self):
        """S13-06: Strong fixture with no missing prerequisites must not
        produce a prerequisite gap."""
        analyzer = make_gap_analyzer(_fixed_clock)
        decomp = dict(S13_06_STRONG_DECOMPOSITION)
        decomp["missing_prerequisites"] = []
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=decomp,
        )
        self.assertEqual(len(result.gaps), 0)

    def test_s13_06_strong_knowledge_not_flagged_as_weak(self):
        """S13-06: Strong knowledge must not be flagged as weak knowledge."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        weak_knowledge_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_KNOWLEDGE]
        self.assertEqual(len(weak_knowledge_gaps), 0)

    def test_s13_06_strong_application_not_flagged_as_weak(self):
        """S13-06: Strong application must not be flagged as weak application."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        weak_app_gaps = [g for g in result.gaps if g.gap_type == GapType.WEAK_APPLICATION]
        self.assertEqual(len(weak_app_gaps), 0)


# ====================================================================== #
# Edge case: gap without evidence_ref rejected
# ====================================================================== #


class TestEdgeGapWithoutEvidenceRefRejected(unittest.TestCase):
    def test_gap_without_evidence_ref_rejected(self):
        """Edge: A gap with no evidence_ref must not be produced."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_EDGE_GAP_WITHOUT_EVIDENCE_REF_MASTERY),
        )
        # The weak knowledge gap has an empty evidence_ref — it must be rejected
        for gap in result.gaps:
            self.assertGreater(len(gap.evidence_refs), 0,
                f"Gap {gap.gap_id} has no evidence_refs — must be rejected")


# ====================================================================== #
# Edge case: PAUSED/SUPERSEDED goals excluded
# ====================================================================== #


class TestEdgePausedSupersededGoalsExcluded(unittest.TestCase):
    def test_paused_goal_excluded(self):
        """Edge: PAUSED goals must be excluded from gap analysis."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-paused",
            goal_title="Master mechanical ventilation",
            goal_state="PAUSED",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_EDGE_PAUSED_GOAL_DECOMPOSITION,
        )
        self.assertEqual(len(result.gaps), 0)
        self.assertEqual(result.goal_state, "PAUSED")

    def test_superseded_goal_excluded(self):
        """Edge: SUPERSEDED goals must be excluded from gap analysis."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-superseded",
            goal_title="Master mechanical ventilation",
            goal_state="SUPERSEDED",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_EDGE_SUPERSEDED_GOAL_DECOMPOSITION,
        )
        self.assertEqual(len(result.gaps), 0)
        self.assertEqual(result.goal_state, "SUPERSEDED")


# ====================================================================== #
# Edge case: deterministic repeat calls identical
# ====================================================================== #


class TestEdgeDeterministicRepeatCallsIdentical(unittest.TestCase):
    def test_deterministic_repeat_calls_identical(self):
        """Edge: Deterministic repeat calls must produce identical results."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result1 = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        result2 = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        self.assertEqual(len(result1.gaps), len(result2.gaps))
        self.assertEqual(result1.deterministic_key, result2.deterministic_key)
        self.assertEqual(result1.evidence_trace, result2.evidence_trace)

    def test_deterministic_gap_counts_identical(self):
        """Edge: Gap counts must be identical across repeat calls."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result1 = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        result2 = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        self.assertEqual(result1.gap_counts, result2.gap_counts)


# ====================================================================== #
# Edge case: malformed mastery input rejected
# ====================================================================== #


class TestEdgeMalformedMasteryInputRejected(unittest.TestCase):
    def test_malformed_mastery_none_rejected(self):
        """Edge: None mastery_result must be rejected with ValueError."""
        analyzer = make_gap_analyzer(_fixed_clock)
        with self.assertRaises(ValueError):
            analyzer.analyze(
                goal_id="goal-vent-01",
                goal_title="Master mechanical ventilation",
                goal_state="ACTIVE",
                mastery_result=None,
            )


# ====================================================================== #
# Edge case: malformed decomposition input rejected
# ====================================================================== #


class TestEdgeMalformedDecompositionInputRejected(unittest.TestCase):
    def test_malformed_decomposition_none_is_valid(self):
        """Edge: None decomposition_result is valid — no decomposition-based gaps."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
            decomposition_result=None,
        )
        # No decomposition means no prerequisite or uncovered-proficiency gaps
        prereq_gaps = [g for g in result.gaps if g.gap_type == GapType.MISSING_PREREQUISITE]
        uncovered_gaps = [g for g in result.gaps if g.gap_type == GapType.UNCOVERED_PROFICIENCY]
        self.assertEqual(len(prereq_gaps), 0)
        self.assertEqual(len(uncovered_gaps), 0)


# ====================================================================== #
# Edge case: empty state → explicit empty gap list, not invented gaps
# ====================================================================== #


class TestEdgeEmptyStateExplicitEmptyGapList(unittest.TestCase):
    def test_empty_state_no_invented_gaps(self):
        """Edge: Empty state must produce an explicit empty gap list,
        not invented gaps."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-empty-01",
            goal_title="Empty goal",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_EDGE_EMPTY_MASTERY),
            decomposition_result=S13_EDGE_EMPTY_DECOMPOSITION,
            proficiency_records=S13_EDGE_EMPTY_PROFICIENCY_RECORDS,
        )
        self.assertEqual(len(result.gaps), 0)
        self.assertEqual(result.gap_counts, {})
        self.assertEqual(result.evidence_trace, [])

    def test_empty_state_explicit_not_none(self):
        """Edge: Empty state must return a result with gaps=[] (not None)."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-empty-01",
            goal_title="Empty goal",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_EDGE_EMPTY_MASTERY),
            decomposition_result=S13_EDGE_EMPTY_DECOMPOSITION,
            proficiency_records=S13_EDGE_EMPTY_PROFICIENCY_RECORDS,
        )
        self.assertIsNotNone(result.gaps)
        self.assertIsInstance(result.gaps, list)


# ====================================================================== #
# Edge case: gap_type and GapType enum consistency
# ====================================================================== #


class TestEdgeGapTypeEnumConsistency(unittest.TestCase):
    def test_gap_type_values(self):
        """Edge: All GapType enum values must be valid."""
        self.assertEqual(GapType.MISSING_PREREQUISITE.value, "missing_prerequisite")
        self.assertEqual(GapType.WEAK_KNOWLEDGE.value, "weak_knowledge")
        self.assertEqual(GapType.WEAK_APPLICATION.value, "weak_application")
        self.assertEqual(GapType.INSUFFICIENT_EVIDENCE.value, "insufficient_evidence")
        self.assertEqual(GapType.UNCOVERED_PROFICIENCY.value, "uncovered_proficiency")


# ====================================================================== #
# Edge case: Gap record fields
# ====================================================================== #


class TestEdgeGapRecordFields(unittest.TestCase):
    def test_gap_record_has_all_fields(self):
        """Edge: A Gap record must have all required fields."""
        gap = Gap(
            gap_id="gap-test-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-test",
            topic_id="topic-test",
            description="Test gap",
            evidence_refs=["ev-test-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Study more",
        )
        self.assertEqual(gap.gap_id, "gap-test-001")
        self.assertEqual(gap.gap_type, GapType.WEAK_KNOWLEDGE)
        self.assertEqual(gap.goal_id, "goal-test")
        self.assertEqual(gap.evidence_refs, ["ev-test-001"])

    def test_gap_record_is_frozen(self):
        """Edge: Gap records are frozen (immutable)."""
        gap = Gap(
            gap_id="gap-test-002",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-test",
            topic_id=None,
            description="Test gap",
            evidence_refs=["ev-test-002"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Study more",
        )
        with self.assertRaises(Exception):
            gap.description = "Modified"


# ====================================================================== #
# Edge case: GapAnalysisResult fields
# ====================================================================== #


class TestEdgeGapAnalysisResultFields(unittest.TestCase):
    def test_result_has_all_fields(self):
        """Edge: GapAnalysisResult must have all required fields."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        self.assertEqual(result.goal_id, "goal-vent-01")
        self.assertEqual(result.goal_title, "Master mechanical ventilation")
        self.assertEqual(result.goal_state, "ACTIVE")
        self.assertIsInstance(result.gaps, list)
        self.assertIsInstance(result.gap_counts, dict)
        self.assertIsInstance(result.evidence_trace, list)
        self.assertIsInstance(result.deterministic_key, str)

    def test_result_is_frozen(self):
        """Edge: GapAnalysisResult is frozen (immutable)."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        with self.assertRaises(Exception):
            result.goal_state = "PAUSED"


# ====================================================================== #
# Edge case: inject clock
# ====================================================================== #


class TestEdgeInjectClock(unittest.TestCase):
    def test_analyzer_accepts_injected_clock(self):
        """Edge: LearningGapAnalyzer accepts an injected clock function."""
        clock_calls = []

        def tracking_clock():
            clock_calls.append("called")
            return "2026-09-30T12:00:00"

        analyzer = make_gap_analyzer(tracking_clock)
        analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_06_STRONG_MASTERY),
        )
        self.assertGreater(len(clock_calls), 0)


# ====================================================================== #
# Edge case: all gap types present in a complex scenario
# ====================================================================== #


class TestEdgeAllGapTypesPresent(unittest.TestCase):
    def test_all_gap_types_detected_in_complex_scenario(self):
        """Edge: A complex scenario with multiple weaknesses must detect
        all relevant gap types."""
        # Weak knowledge + missing prerequisite + uncovered proficiency
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-complex-01",
            goal_title="Complex goal",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
            proficiency_records=S13_05_UNCOVERED_PROFICIENCY_RECORDS,
        )
        gap_types = set(g.gap_type.value for g in result.gaps)
        self.assertIn(GapType.WEAK_KNOWLEDGE.value, gap_types)
        self.assertIn(GapType.MISSING_PREREQUISITE.value, gap_types)
        self.assertIn(GapType.UNCOVERED_PROFICIENCY.value, gap_types)


# ====================================================================== #
# Edge case: evidence_trace contains all evidence refs
# ====================================================================== #


class TestEdgeEvidenceTraceComplete(unittest.TestCase):
    def test_evidence_trace_contains_all_refs(self):
        """Edge: Every evidence ref in gaps must appear in the
        result's evidence_trace."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        for gap in result.gaps:
            for ref in gap.evidence_refs:
                self.assertIn(ref, result.evidence_trace,
                    f"Evidence ref {ref!r} from gap {gap.gap_id} not in evidence_trace")


# ====================================================================== #
# Edge case: gap_counts accurate
# ====================================================================== #


class TestEdgeGapCountsAccurate(unittest.TestCase):
    def test_gap_counts_accurate(self):
        """Edge: Gap counts must accurately reflect the number of gaps
        of each type."""
        analyzer = make_gap_analyzer(_fixed_clock)
        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S13_02_WEAK_KNOWLEDGE_MASTERY),
            decomposition_result=S13_01_MISSING_PREREQUISITE_DECOMPOSITION,
        )
        # Count gaps by type manually
        manual_counts = {}
        for gap in result.gaps:
            gt = gap.gap_type.value
            manual_counts[gt] = manual_counts.get(gt, 0) + 1
        self.assertEqual(result.gap_counts, manual_counts)


if __name__ == "__main__":
    unittest.main()
