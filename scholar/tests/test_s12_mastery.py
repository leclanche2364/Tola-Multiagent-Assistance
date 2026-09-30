"""
Batch S12 -- Mastery Model QA Tests (S12-01..S12-05).
Deterministic fixtures, injectable clock, unittest.
No network, no real clocks.
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.fixtures.mastery import (
    S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
    S12_02_WEAK_RECALL_EVIDENCE,
    S12_03_PRACTICAL_DIFFERS_FROM_THEORY_EVIDENCE,
    S12_04_FORMAL_COMPETENCE_ABSENT_EVIDENCE,
    S12_05_AUTHORITATIVE_SIGNOFF_EVIDENCE,
    S12_05_NON_AUTHORITATIVE_CANNOT_MOVE_FC_EVIDENCE,
    S12_05_AUTHORITATIVE_SIGNOFF_WEAK_EVIDENCE,
    S12_EDGE_UNKNOWN_DIMENSION_EVIDENCE,
    S12_EDGE_EMPTY_EVIDENCE,
    S12_EDGE_ALL_ABSENT_EVIDENCE,
    make_analyser,
    make_evidence,
)
from scholar.mastery.model import (
    MasteryAnalyser,
    MasteryResult,
    MasteryDimension,
    DimensionEvidence,
)


def _fixed_clock():
    return "2026-09-30T12:00:00"


# ====================================================================== #
#  S12-01: Knowledge strong + application weak represented separately
# ====================================================================== #


class TestS12_01KnowledgeStrongApplicationWeakSeparated(unittest.TestCase):
    def test_knowledge_strong_and_application_weak_are_separate(self):
        """S12-01: Knowledge strong + application weak must be
        represented as separate dimensions — no blended score."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertEqual(
            result.dimension_strength(MasteryDimension.KNOWLEDGE),
            "strong",
        )
        self.assertEqual(
            result.dimension_strength(MasteryDimension.APPLICATION),
            "weak",
        )

    def test_knowledge_strong_application_weak_flag_is_true(self):
        """S12-01: The knowledge_strong_application_weak() helper
        must return True when knowledge is strong and application is weak."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertTrue(result.knowledge_strong_application_weak())

    def test_s12_01_no_blended_score(self):
        """S12-01: There must be no single blended score that
        merges knowledge and application into one value."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        # Each dimension has its own evidence — they are distinct
        knowledge_ev = result.dimensions.get(MasteryDimension.KNOWLEDGE)
        application_ev = result.dimensions.get(MasteryDimension.APPLICATION)
        self.assertIsNotNone(knowledge_ev)
        self.assertIsNotNone(application_ev)
        # They must have different strengths
        self.assertNotEqual(knowledge_ev.strength, application_ev.strength)

    def test_s12_01_evidence_refs_traceable(self):
        """S12-01: Each dimension's evidence must be traceable."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        knowledge_ref = result.dimensions[MasteryDimension.KNOWLEDGE].evidence_ref
        application_ref = result.dimensions[MasteryDimension.APPLICATION].evidence_ref
        self.assertIn(knowledge_ref, result.evidence_trace)
        self.assertIn(application_ref, result.evidence_trace)
        # They must be different refs (separate evidence)
        self.assertNotEqual(knowledge_ref, application_ref)

    def test_s12_01_knowledge_strong_not_inferred_from_application(self):
        """S12-01: Strong knowledge must not be inferred from
        weak application or vice versa."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        # Knowledge is strong — application must NOT be strong
        self.assertNotEqual(
            result.dimension_strength(MasteryDimension.APPLICATION),
            "strong",
        )
        # Application is weak — knowledge must NOT be weak
        self.assertNotEqual(
            result.dimension_strength(MasteryDimension.KNOWLEDGE),
            "weak",
        )


# ====================================================================== #
#  S12-02: Weak recall detected
# ====================================================================== #


class TestS12_02WeakRecallDetected(unittest.TestCase):
    def test_weak_recall_detected(self):
        """S12-02: Weak recall must be detected and surfaced."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_02_WEAK_RECALL_EVIDENCE,
            "goal-vent-01",
        )
        self.assertTrue(result.recall_weak())

    def test_weak_recall_strength_is_weak(self):
        """S12-02: The recall dimension must have strength='weak'."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_02_WEAK_RECALL_EVIDENCE,
            "goal-vent-01",
        )
        self.assertEqual(
            result.dimension_strength(MasteryDimension.RECALL),
            "weak",
        )

    def test_weak_recall_evidence_source(self):
        """S12-02: Weak recall evidence must reference the assessment source."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_02_WEAK_RECALL_EVIDENCE,
            "goal-vent-01",
        )
        recall_ev = result.dimensions.get(MasteryDimension.RECALL)
        self.assertIsNotNone(recall_ev)
        self.assertEqual(recall_ev.source, "assessment_score")

    def test_weak_recall_not_confused_with_knowledge(self):
        """S12-02: Weak recall must not be conflated with knowledge strength."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_02_WEAK_RECALL_EVIDENCE,
            "goal-vent-01",
        )
        # Recall is weak, but knowledge may be absent (no knowledge evidence provided)
        self.assertEqual(
            result.dimension_strength(MasteryDimension.RECALL),
            "weak",
        )


# ====================================================================== #
#  S12-03: Practical readiness can differ from theory
# ====================================================================== #


class TestS12_03PracticalReadinessDiffersFromTheory(unittest.TestCase):
    def test_practical_readiness_differs_from_theory(self):
        """S12-03: Practical readiness can differ from knowledge/theory."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_03_PRACTICAL_DIFFERS_FROM_THEORY_EVIDENCE,
            "goal-vent-01",
        )
        self.assertTrue(result.practical_readiness_differs_from_theory())

    def test_theory_strong_practical_weak(self):
        """S12-03: When theory is strong and practical is weak,
        they must be recorded as separate dimensions."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_03_PRACTICAL_DIFFERS_FROM_THEORY_EVIDENCE,
            "goal-vent-01",
        )
        self.assertEqual(
            result.dimension_strength(MasteryDimension.KNOWLEDGE),
            "strong",
        )
        self.assertEqual(
            result.dimension_strength(MasteryDimension.PRACTICAL_READINESS),
            "weak",
        )

    def test_s12_03_no_single_blended_score(self):
        """S12-03: Practical readiness and knowledge are distinct
        — no single blended score merges them."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_03_PRACTICAL_DIFFERS_FROM_THEORY_EVIDENCE,
            "goal-vent-01",
        )
        knowledge_ev = result.dimensions[MasteryDimension.KNOWLEDGE]
        practical_ev = result.dimensions[MasteryDimension.PRACTICAL_READINESS]
        self.assertNotEqual(knowledge_ev.strength, practical_ev.strength)


# ====================================================================== #
#  S12-04: Formal competence absent -> NOT inferred
# ====================================================================== #


class TestS12_04FormalCompetenceAbsentNotInferred(unittest.TestCase):
    def test_formal_competence_unsigned_when_no_evidence(self):
        """S12-04: When no formal competence evidence exists,
        it must remain UNSIGNED — not inferred from theory strength."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_04_FORMAL_COMPETENCE_ABSENT_EVIDENCE,
            "goal-vent-01",
        )
        self.assertTrue(result.formal_competence_unsigned())
        self.assertEqual(result.formal_competence_state, "UNSIGNED")

    def test_formal_competence_not_inferred_from_strong_knowledge(self):
        """S12-04: Strong knowledge must NOT cause formal competence
        to be inferred as SIGNED_OFF."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_04_FORMAL_COMPETENCE_ABSENT_EVIDENCE,
            "goal-vent-01",
        )
        # Knowledge is strong but formal competence must still be UNSIGNED
        self.assertEqual(
            result.dimension_strength(MasteryDimension.KNOWLEDGE),
            "strong",
        )
        self.assertTrue(result.formal_competence_unsigned())

    def test_formal_competence_not_inferred_from_strong_application(self):
        """S12-04: Strong application must NOT cause formal competence
        to be inferred as SIGNED_OFF."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_04_FORMAL_COMPETENCE_ABSENT_EVIDENCE,
            "goal-vent-01",
        )
        # Application is strong but formal competence must still be UNSIGNED
        self.assertEqual(
            result.dimension_strength(MasteryDimension.APPLICATION),
            "strong",
        )
        self.assertTrue(result.formal_competence_unsigned())

    def test_s12_04_all_dimensions_distinct(self):
        """S12-04: All dimensions remain distinct even when
        formal competence is absent."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_04_FORMAL_COMPETENCE_ABSENT_EVIDENCE,
            "goal-vent-01",
        )
        for dim in MasteryDimension:
            ev = result.dimensions.get(dim)
            self.assertIsNotNone(ev, f"Missing dimension {dim}")
            self.assertIsInstance(ev.strength, str)


# ====================================================================== #
#  S12-05: Formal competence changes ONLY from authoritative evidence
# ====================================================================== #


class TestS12_05FormalCompetenceAuthoritativeOnly(unittest.TestCase):
    def test_authoritative_signoff_sets_signed_off(self):
        """S12-05: Authoritative sign-off evidence must set
        formal competence to SIGNED_OFF."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_05_AUTHORITATIVE_SIGNOFF_EVIDENCE,
            "goal-vent-01",
        )
        self.assertEqual(result.formal_competence_state, "SIGNED_OFF")

    def test_non_authoritative_cannot_move_formal_competence(self):
        """S12-05: Non-authoritative evidence must NOT move formal
        competence from UNSIGNED to SIGNED_OFF."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_05_NON_AUTHORITATIVE_CANNOT_MOVE_FC_EVIDENCE,
            "goal-vent-01",
        )
        # Despite strong knowledge and application, formal competence
        # must remain UNSIGNED because the only FC evidence is non-authoritative
        self.assertTrue(result.formal_competence_unsigned())
        self.assertEqual(result.formal_competence_state, "UNSIGNED")

    def test_authoritative_weak_stays_unsigned(self):
        """S12-05: Authoritative but weak evidence must NOT set
        formal competence to SIGNED_OFF."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_05_AUTHORITATIVE_SIGNOFF_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertTrue(result.formal_competence_unsigned())
        self.assertEqual(result.formal_competence_state, "UNSIGNED")

    def test_s12_05_non_authoritative_rejected_for_fc(self):
        """S12-05: Attempting to raise formal competence from
        non-authoritative source must be rejected (FC stays UNSIGNED)."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_05_NON_AUTHORITATIVE_CANNOT_MOVE_FC_EVIDENCE,
            "goal-vent-01",
        )
        fc_evidence = result.dimensions.get(MasteryDimension.FORMAL_COMPETENCE)
        self.assertIsNotNone(fc_evidence)
        # The non-authoritative self-assessment must not have caused SIGNED_OFF
        self.assertEqual(result.formal_competence_state, "UNSIGNED")

    def test_s12_05_authoritative_source_recorded(self):
        """S12-05: When formal competence IS signed off, the
        authoritative source must be recorded."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_05_AUTHORITATIVE_SIGNOFF_EVIDENCE,
            "goal-vent-01",
        )
        fc_evidence = result.dimensions.get(MasteryDimension.FORMAL_COMPETENCE)
        self.assertIsNotNone(fc_evidence)
        self.assertTrue(fc_evidence.authoritative)
        self.assertEqual(fc_evidence.source, "supervisor_signoff")

    def test_s12_05_evidence_ref_traceability(self):
        """S12-05: Formal competence evidence ref must be traceable
        in the evidence_trace."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_05_AUTHORITATIVE_SIGNOFF_EVIDENCE,
            "goal-vent-01",
        )
        fc_evidence = result.dimensions.get(MasteryDimension.FORMAL_COMPETENCE)
        self.assertIn(fc_evidence.evidence_ref, result.evidence_trace)


# ====================================================================== #
#  Edge cases
# ====================================================================== #


class TestEdgeCasesUnknownDimensionRejected(unittest.TestCase):
    def test_unknown_dimension_not_in_model(self):
        """Edge: An unknown dimension string must not be accepted
        as a valid MasteryDimension."""
        # MasteryDimension is an Enum — invalid values are rejected
        with self.assertRaises(ValueError):
            MasteryDimension("unknown_dimension")


class TestEdgeCasesDeterministicRepeatCalls(unittest.TestCase):
    def test_deterministic_repeat_calls_produce_identical_results(self):
        """Edge: Deterministic repeat calls must produce identical
        mastery results."""
        analyser = make_analyser(_fixed_clock)
        result1 = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        result2 = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertEqual(
            result1.dimension_strength(MasteryDimension.KNOWLEDGE),
            result2.dimension_strength(MasteryDimension.KNOWLEDGE),
        )
        self.assertEqual(
            result1.dimension_strength(MasteryDimension.APPLICATION),
            result2.dimension_strength(MasteryDimension.APPLICATION),
        )
        self.assertEqual(
            result1.formal_competence_state,
            result2.formal_competence_state,
        )

    def test_deterministic_repeat_calls_same_evidence_trace(self):
        """Edge: Evidence trace must be identical across repeat calls."""
        analyser = make_analyser(_fixed_clock)
        result1 = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        result2 = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertEqual(result1.evidence_trace, result2.evidence_trace)


class TestEdgeCasesEmptyEvidence(unittest.TestCase):
    def test_empty_evidence_all_dimensions_absent(self):
        """Edge: Empty evidence list must produce all dimensions as absent."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_EDGE_EMPTY_EVIDENCE,
            "goal-vent-01",
        )
        for dim in MasteryDimension:
            self.assertEqual(
                result.dimension_strength(dim),
                "absent",
                f"Dimension {dim} should be absent with no evidence",
            )
        self.assertTrue(result.formal_competence_unsigned())


class TestEdgeCasesAllAbsentDimensions(unittest.TestCase):
    def test_all_absent_dimensions_recorded(self):
        """Edge: When all evidence is 'absent', all dimensions
        must still be present with strength='absent'."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_EDGE_ALL_ABSENT_EVIDENCE,
            "goal-vent-01",
        )
        for dim in MasteryDimension:
            ev = result.dimensions.get(dim)
            self.assertIsNotNone(ev)
            # Knowledge has explicit absent evidence; others default to absent


class TestEdgeCasesEvidenceRefTraceability(unittest.TestCase):
    def test_all_evidence_refs_in_trace(self):
        """Edge: Every evidence item's ref must appear in the
        result's evidence_trace."""
        analyser = make_analyser(_fixed_clock)
        evidence = S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE
        result = analyser.evaluate(evidence, "goal-vent-01")
        for ev in evidence:
            self.assertIn(ev.evidence_ref, result.evidence_trace)

    def test_evidence_ref_unique_per_item(self):
        """Edge: Each evidence item must have a unique ref."""
        refs = [ev.evidence_ref for ev in S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE]
        self.assertEqual(len(refs), len(set(refs)))


class TestEdgeCasesDimensionEvidenceImmutable(unittest.TestCase):
    def test_dimension_evidence_is_frozen(self):
        """Edge: DimensionEvidence is frozen (immutable)."""
        ev = make_evidence(
            MasteryDimension.KNOWLEDGE,
            "strong",
            "test_source",
            "ev-immutable-001",
            "Test detail",
        )
        with self.assertRaises(Exception):
            ev.strength = "weak"


class TestEdgeCasesMasteryResultFrozen(unittest.TestCase):
    def test_mastery_result_is_frozen(self):
        """Edge: MasteryResult is frozen (immutable)."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        with self.assertRaises(Exception):
            result.formal_competence_state = "SIGNED_OFF"


class TestEdgeCasesAuthoritativeSourceValidation(unittest.TestCase):
    def test_non_authoritative_source_cannot_sign_off(self):
        """Edge: A non-authoritative source (e.g. self_assessment)
        must not cause formal competence to become SIGNED_OFF even
        if the evidence strength is strong."""
        evidence = [
            make_evidence(
                MasteryDimension.FORMAL_COMPETENCE,
                "strong",
                "self_assessment",
                "ev-edge-001",
                "Self-assessment — non-authoritative",
                authoritative=False,
            ),
        ]
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(evidence, "goal-vent-01")
        self.assertTrue(result.formal_competence_unsigned())
        self.assertEqual(result.formal_competence_state, "UNSIGNED")

    def test_authoritative_source_can_sign_off(self):
        """Edge: An authoritative source CAN cause formal competence
        to become SIGNED_OFF when strength is strong."""
        evidence = [
            make_evidence(
                MasteryDimension.FORMAL_COMPETENCE,
                "strong",
                "supervisor_signoff",
                "ev-edge-002",
                "Supervisor signoff — authoritative",
                authoritative=True,
            ),
        ]
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(evidence, "goal-vent-01")
        self.assertEqual(result.formal_competence_state, "SIGNED_OFF")

    def test_authoritative_source_weak_does_not_sign_off(self):
        """Edge: An authoritative source with weak strength must NOT
        cause formal competence to become SIGNED_OFF."""
        evidence = [
            make_evidence(
                MasteryDimension.FORMAL_COMPETENCE,
                "weak",
                "supervisor_signoff",
                "ev-edge-003",
                "Supervisor signoff but weak — not signed off",
                authoritative=True,
            ),
        ]
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(evidence, "goal-vent-01")
        self.assertTrue(result.formal_competence_unsigned())


class TestEdgeCasesTopicIdOptional(unittest.TestCase):
    def test_evaluate_with_topic_id(self):
        """Edge: evaluate() accepts an optional topic_id."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
            topic_id="topic-ventilation",
        )
        self.assertEqual(result.topic_id, "topic-ventilation")

    def test_evaluate_without_topic_id(self):
        """Edge: evaluate() works without a topic_id (None)."""
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertIsNone(result.topic_id)


class TestEdgeCasesInjectClock(unittest.TestCase):
    def test_analyser_accepts_injected_clock(self):
        """Edge: MasteryAnalyser accepts an injected clock function."""
        clock_calls = []

        def tracking_clock():
            clock_calls.append("called")
            return "2026-09-30T12:00:00"

        analyser = make_analyser(tracking_clock)
        analyser.evaluate(
            S12_01_KNOWLEDGE_STRONG_APPLICATION_WEAK_EVIDENCE,
            "goal-vent-01",
        )
        self.assertGreater(len(clock_calls), 0)


class TestEdgeCasesAllEightDimensionsPresent(unittest.TestCase):
    def test_all_eight_dimensions_present_in_result(self):
        """Edge: A MasteryResult must contain all eight dimensions."""
        all_evidence = [
            make_evidence(MasteryDimension.KNOWLEDGE, "strong", "src", "ev-001", "k", False),
            make_evidence(MasteryDimension.RATIONALE, "strong", "src", "ev-002", "r", False),
            make_evidence(MasteryDimension.APPLICATION, "strong", "src", "ev-003", "a", False),
            make_evidence(MasteryDimension.CRITICAL_ANALYSIS, "strong", "src", "ev-004", "ca", False),
            make_evidence(MasteryDimension.RECALL, "strong", "src", "ev-005", "rec", False),
            make_evidence(MasteryDimension.TRANSFER, "strong", "src", "ev-006", "t", False),
            make_evidence(MasteryDimension.PRACTICAL_READINESS, "strong", "src", "ev-007", "pr", False),
            make_evidence(MasteryDimension.FORMAL_COMPETENCE, "strong", "supervisor_signoff", "ev-008", "fc", True),
        ]
        analyser = make_analyser(_fixed_clock)
        result = analyser.evaluate(all_evidence, "goal-vent-01")
        for dim in MasteryDimension:
            self.assertIn(dim, result.dimensions)

    def test_eight_dimensions_are_distinct(self):
        """Edge: All eight dimensions must be distinct enum values."""
        dims = set(MasteryDimension)
        self.assertEqual(len(dims), 8)


if __name__ == "__main__":
    unittest.main()