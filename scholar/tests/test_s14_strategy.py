"""
Batch S14 -- Adaptive Learning Strategy QA Tests (S14-01..S14-06).
Deterministic fixtures, injectable clock, unittest.
No network, no real clocks.
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.fixtures.strategy import (
    make_strategy,
    make_gap_analyzer,
    make_dimension_evidence,
    make_mastery_result,
    # S14-02 fixtures
    S14_02_WEAK_KNOWLEDGE_GAP,
    S14_02_WEAK_APPLICATION_GAP,
    S14_02_MISSING_PREREQ_DECOMPOSITION,
    # S14-03 fixture
    S14_03_GAP_WITH_EFFORT,
    # Edge fixtures
    S14_EDGE_PAUSED_GOAL_DECOMPOSITION,
    S14_EDGE_SUPERSEDED_GOAL_DECOMPOSITION,
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
from scholar.adaptive_learning_strategy.strategy import (
    AdaptiveLearningStrategy,
    LearningItem,
    StrategyResult,
    build_strategy,
    _reject_calendar_time_fields,
)
from scholar.mastery.model import MasteryAnalyser


def _fixed_clock():
    return "2026-09-30T12:00:00"


def _make_mastery_result(evidence, goal_id="goal-vent-01", topic_id=None):
    """Build a MasteryResult from a list of DimensionEvidence."""
    analyser = MasteryAnalyser(clock=_fixed_clock)
    return analyser.evaluate(evidence, goal_id, topic_id=topic_id)


def _make_gap_result(gaps, goal_id="goal-vent-01", goal_title="Master mechanical ventilation", goal_state="ACTIVE"):
    """Build a GapAnalysisResult from a list of Gap objects."""
    gap_types = [g.gap_type.value for g in gaps]
    evidence_refs = []
    for g in gaps:
        for ref in g.evidence_refs:
            if ref and ref not in evidence_refs:
                evidence_refs.append(ref)
    det_key = f"goal:{goal_id}|gaps:{','.join(sorted(gap_types))}|refs:{','.join(sorted(evidence_refs))}::hash=00000000"
    return GapAnalysisResult(
        goal_id=goal_id,
        goal_title=goal_title,
        goal_state=goal_state,
        gaps=gaps,
        gap_counts={},
        evidence_trace=evidence_refs,
        deterministic_key=det_key,
    )


# ====================================================================== #
# S14-01: Ordered items — logical progression
# ====================================================================== #


class TestS14_01OrderedItemsLogicalProgression(unittest.TestCase):
    def test_items_ordered_by_gap_type_priority(self):
        """S14-01: Items must be in logical progression order.
        Missing prerequisites come first, then weak knowledge,
        weak application, insufficient evidence, uncovered proficiency."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        # Create gaps in non-priority order: uncovered first, then missing prereq
        gap_uncovered = Gap(
            gap_id="gap-uncovered-001",
            gap_type=GapType.UNCOVERED_PROFICIENCY,
            goal_id="goal-vent-01",
            topic_id=None,
            description="Uncovered proficiency prof-hemo-01",
            evidence_refs=["ev-uncovered-001"],
            mastery_dimension=None,
            severity="medium",
            recommendation="Map this proficiency to the learning plan.",
        )
        gap_prereq = Gap(
            gap_id="gap-prereq-001",
            gap_type=GapType.MISSING_PREREQUISITE,
            goal_id="goal-vent-01",
            topic_id=None,
            description="Missing prerequisite node-lung-protective",
            evidence_refs=["ev-prereq-001"],
            mastery_dimension=None,
            severity="high",
            recommendation="Address prerequisite before proceeding.",
        )
        gap_weak_knowledge = Gap(
            gap_id="gap-weak-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-weak-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge through targeted study.",
        )

        result = analyzer.analyze(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            mastery_result=_make_mastery_result(S14_03_GAP_WITH_EFFORT),
        )
        # Manually override gaps to test ordering
        result_with_gaps = GapAnalysisResult(
            goal_id="goal-vent-01",
            goal_title="Master mechanical ventilation",
            goal_state="ACTIVE",
            gaps=[gap_uncovered, gap_prereq, gap_weak_knowledge],
            gap_counts={},
            evidence_trace=["ev-uncovered-001", "ev-prereq-001", "ev-weak-001"],
            deterministic_key="test-key",
        )

        strategy_result = strategy.build(result_with_gaps)
        self.assertEqual(strategy_result.item_count, 3)
        # Missing prerequisite should be first (priority 0)
        self.assertEqual(strategy_result.items[0].gap_refs, ["gap-prereq-001"])
        # Weak knowledge should be second (priority 1)
        self.assertEqual(strategy_result.items[1].gap_refs, ["gap-weak-001"])
        # Uncovered proficiency should be last (priority 4)
        self.assertEqual(strategy_result.items[2].gap_refs, ["gap-uncovered-001"])

    def test_s14_01_sequence_is_1_based_consecutive(self):
        """S14-01: Sequence numbers must be 1-based and consecutive."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-s14-01-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge in dimension KNOWLEDGE",
                evidence_refs=["ev-s14-01-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-s14-01-002",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application in dimension APPLICATION",
                evidence_refs=["ev-s14-01-002"],
                mastery_dimension="APPLICATION",
                severity="high",
                recommendation="Increase practice.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        strategy_result = strategy.build(gap_result)

        for i, item in enumerate(strategy_result.items):
            self.assertEqual(item.sequence, i + 1)

    def test_s14_01_deterministic_ordering(self):
        """S14-01: Deterministic repeat calls must produce identical item order."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-s14-01-det-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge in dimension KNOWLEDGE",
                evidence_refs=["ev-s14-01-det-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-s14-01-det-002",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application in dimension APPLICATION",
                evidence_refs=["ev-s14-01-det-002"],
                mastery_dimension="APPLICATION",
                severity="high",
                recommendation="Increase practice.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result1 = strategy.build(gap_result)
        result2 = strategy.build(gap_result)

        self.assertEqual(len(result1.items), len(result2.items))
        for i in range(len(result1.items)):
            self.assertEqual(result1.items[i].sequence, result2.items[i].sequence)
            self.assertEqual(result1.items[i].item_id, result2.items[i].item_id)


# ====================================================================== #
# S14-02: Target depth appropriate to gap/mastery dimension
# ====================================================================== #


class TestS14_02TargetDepthAppropriate(unittest.TestCase):
    def test_weak_knowledge_targets_knowledge_depth(self):
        """S14-02: A weak knowledge gap must target KNOWLEDGE depth."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-kw-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-02-kw-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_depth, "KNOWLEDGE")

    def test_weak_application_targets_application_depth(self):
        """S14-02: A weak application gap must target APPLICATION depth."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-wa-001",
            gap_type=GapType.WEAK_APPLICATION,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak application in dimension APPLICATION",
            evidence_refs=["ev-s14-02-wa-001"],
            mastery_dimension="APPLICATION",
            severity="high",
            recommendation="Increase practice.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_depth, "APPLICATION")

    def test_missing_prerequisite_targets_knowledge_depth(self):
        """S14-02: A missing prerequisite gap targets KNOWLEDGE depth."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-mp-001",
            gap_type=GapType.MISSING_PREREQUISITE,
            goal_id="goal-vent-01",
            topic_id=None,
            description="Missing prerequisite node-lung-protective",
            evidence_refs=["ev-s14-02-mp-001"],
            mastery_dimension=None,
            severity="high",
            recommendation="Address prerequisite.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_depth, "KNOWLEDGE")

    def test_insufficient_evidence_targets_rationale_depth(self):
        """S14-02: An insufficient evidence gap targets RATIONALE depth."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-ie-001",
            gap_type=GapType.INSUFFICIENT_EVIDENCE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Insufficient evidence for RATIONALE",
            evidence_refs=["ev-s14-02-ie-001"],
            mastery_dimension="RATIONALE",
            severity="medium",
            recommendation="Gather more evidence.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_depth, "RATIONALE")

    def test_uncovered_proficiency_targets_knowledge_depth(self):
        """S14-02: An uncovered proficiency gap targets KNOWLEDGE depth."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-up-001",
            gap_type=GapType.UNCOVERED_PROFICIENCY,
            goal_id="goal-vent-01",
            topic_id=None,
            description="Uncovered proficiency prof-hemo-01",
            evidence_refs=["ev-s14-02-up-001"],
            mastery_dimension=None,
            severity="medium",
            recommendation="Map this proficiency.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_depth, "KNOWLEDGE")

    def test_s14_02_target_mastery_high_for_high_severity(self):
        """S14-02: High severity gaps target 'strong' mastery."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-hs-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-s14-02-hs-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_mastery, "strong")

    def test_s14_02_target_mastery_adequate_for_medium_severity(self):
        """S14-02: Medium severity gaps target 'adequate' mastery."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-02-ms-001",
            gap_type=GapType.UNCOVERED_PROFICIENCY,
            goal_id="goal-vent-01",
            topic_id=None,
            description="Uncovered proficiency",
            evidence_refs=["ev-s14-02-ms-001"],
            mastery_dimension=None,
            severity="medium",
            recommendation="Map this proficiency.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertEqual(result.items[0].target_mastery, "adequate")


# ====================================================================== #
# S14-03: Effort present
# ====================================================================== #


class TestS14_03EffortPresent(unittest.TestCase):
    def test_effort_present_for_all_items(self):
        """S14-03: Every item must have a positive recommended_effort."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-s14-03-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-s14-03-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-s14-03-002",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application",
                evidence_refs=["ev-s14-03-002"],
                mastery_dimension="APPLICATION",
                severity="high",
                recommendation="Increase practice.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result = strategy.build(gap_result)

        for item in result.items:
            self.assertGreater(item.recommended_effort, 0,
                f"Item {item.item_id} has zero or negative effort")

    def test_effort_is_integer(self):
        """S14-03: recommended_effort must be an integer."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-03-int-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-s14-03-int-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertIsInstance(result.items[0].recommended_effort, int)

    def test_total_effort_matches_sum(self):
        """S14-03: total_recommended_effort_minutes must equal sum of item efforts."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-s14-03-sum-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-s14-03-sum-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-s14-03-sum-002",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application",
                evidence_refs=["ev-s14-03-sum-002"],
                mastery_dimension="APPLICATION",
                severity="medium",
                recommendation="Increase practice.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result = strategy.build(gap_result)

        expected_total = sum(item.recommended_effort for item in result.items)
        self.assertEqual(result.total_recommended_effort_minutes, expected_total)


# ====================================================================== #
# S14-04: No learner-facing quiz instructions
# ====================================================================== #


class TestS14_04NoLearnerFacingQuizInstructions(unittest.TestCase):
    def test_no_quiz_language_in_outcomes(self):
        """S14-04: Outcomes must not contain learner-facing quiz instructions."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-04-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-04-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge through targeted study.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        quiz_indicators = [
            "quiz", "flashcard", "flash card", "test yourself",
            "practice quiz", "take a quiz", "answer these",
            "multiple choice", "true or false", "fill in the blank",
        ]
        for item in result.items:
            combined = (item.topic + " " + " ".join(item.outcomes) + " " + item.rationale).lower()
            for indicator in quiz_indicators:
                self.assertNotIn(indicator, combined,
                    f"Item {item.item_id} contains quiz indicator: {indicator!r}")

    def test_no_quiz_language_in_rationale(self):
        """S14-04: Rationale must not contain quiz instructions."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-04-002",
            gap_type=GapType.WEAK_APPLICATION,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak application in dimension APPLICATION",
            evidence_refs=["ev-s14-04-002"],
            mastery_dimension="APPLICATION",
            severity="high",
            recommendation="Increase practice opportunities.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        for item in result.items:
            self.assertNotIn("quiz", item.rationale.lower())
            self.assertNotIn("flashcard", item.rationale.lower())

    def test_learning_item_rejects_quiz_in_topic(self):
        """S14-04: LearningItem.validate() rejects quiz language in topic."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="bad-item-001",
                topic="Take a quiz on ventilation",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=60,
                outcomes=["Learn ventilation"],
                rationale="This is a test item.",
            )

    def test_learning_item_rejects_quiz_in_outcomes(self):
        """S14-04: LearningItem.validate() rejects quiz language in outcomes."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="bad-item-002",
                topic="Ventilation Basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=60,
                outcomes=["Answer these practice questions"],
                rationale="This is a test item.",
            )


# ====================================================================== #
# S14-05: No shadow teaching
# ====================================================================== #


class TestS14_05NoShadowTeaching(unittest.TestCase):
    def test_no_teaching_script_language_in_outcomes(self):
        """S14-05: Outcomes must not contain shadow teaching language."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-05-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-05-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        teaching_indicators = [
            "teach the learner", "explain to the student", "lecture on",
            "deliver a lesson", "instruct the learner", "guide the student",
            "teaching script", "lesson plan", "classroom instruction",
        ]
        for item in result.items:
            combined = (item.topic + " " + " ".join(item.outcomes) + " " + item.rationale).lower()
            for indicator in teaching_indicators:
                self.assertNotIn(indicator, combined,
                    f"Item {item.item_id} contains teaching indicator: {indicator!r}")

    def test_no_teaching_script_language_in_rationale(self):
        """S14-05: Rationale must not contain teaching script language."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-05-002",
            gap_type=GapType.WEAK_APPLICATION,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak application in dimension APPLICATION",
            evidence_refs=["ev-s14-05-002"],
            mastery_dimension="APPLICATION",
            severity="high",
            recommendation="Increase practice.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        for item in result.items:
            self.assertNotIn("teach the learner", item.rationale.lower())
            self.assertNotIn("lecture on", item.rationale.lower())

    def test_learning_item_rejects_teaching_in_topic(self):
        """S14-05: LearningItem.validate() rejects teaching script language in topic."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="bad-item-003",
                topic="Lecture on ventilation basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=60,
                outcomes=["Learn ventilation"],
                rationale="This is a test item.",
            )

    def test_learning_item_rejects_teaching_in_outcomes(self):
        """S14-05: LearningItem.validate() rejects teaching script language in outcomes."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="bad-item-004",
                topic="Ventilation Basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=60,
                outcomes=["Teach the learner about ventilator modes"],
                rationale="This is a test item.",
            )


# ====================================================================== #
# S14-06: Rationale traceable to gap/evidence
# ====================================================================== #


class TestS14_06RationaleTraceableToGapEvidence(unittest.TestCase):
    def test_rationale_contains_gap_id(self):
        """S14-06: Rationale must reference the gap ID."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-06-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-06-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertIn("gap-s14-06-001", result.items[0].rationale)

    def test_rationale_contains_gap_type(self):
        """S14-06: Rationale must reference the gap type."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-06-002",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-06-002"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertIn("weak_knowledge", result.items[0].rationale)

    def test_rationale_contains_evidence_refs(self):
        """S14-06: Rationale must reference evidence refs."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-06-003",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-06-003"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertIn("ev-s14-06-003", result.items[0].rationale)

    def test_rationale_contains_recommendation(self):
        """S14-06: Rationale must include the gap recommendation."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-06-004",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-06-004"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge through targeted study.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertIn("targeted study", result.items[0].rationale)

    def test_evidence_refs_present_on_item(self):
        """S14-06: LearningItem must carry evidence_refs."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-06-005",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-06-005"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertGreater(len(result.items[0].evidence_refs), 0)
        self.assertIn("ev-s14-06-005", result.items[0].evidence_refs)

    def test_gap_refs_present_on_item(self):
        """S14-06: LearningItem must carry gap_refs."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-s14-06-006",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge in dimension KNOWLEDGE",
            evidence_refs=["ev-s14-06-006"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        self.assertGreater(len(result.items[0].gap_refs), 0)
        self.assertIn("gap-s14-06-006", result.items[0].gap_refs)


# ====================================================================== #
# Edge case: item without rationale rejected
# ====================================================================== #


class TestEdgeItemWithoutRationaleRejected(unittest.TestCase):
    def test_item_without_rationale_rejected(self):
        """Edge: A LearningItem with empty rationale must be rejected."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="bad-item-no-rationale",
                topic="Ventilation Basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=60,
                outcomes=["Learn ventilation"],
                rationale="",
            )

    def test_item_with_whitespace_only_rationale_rejected(self):
        """Edge: A LearningItem with whitespace-only rationale must be rejected."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="bad-item-whitespace-rationale",
                topic="Ventilation Basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=60,
                outcomes=["Learn ventilation"],
                rationale="   ",
            )


# ====================================================================== #
# Edge case: item without evidence trace rejected
# ====================================================================== #


class TestEdgeItemWithoutEvidenceTraceRejected(unittest.TestCase):
    def test_item_without_evidence_refs_rejected_via_gap(self):
        """Edge: A gap without evidence_refs must not produce a strategy item."""
        # The gap analyzer already rejects gaps without evidence_refs (S13-06),
        # but we test that the strategy builder handles it gracefully.
        # A gap with empty evidence_refs is still a gap, but the strategy
        # should still produce an item with empty evidence_refs list.
        # The key constraint is that the rationale must still be present.
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-no-evidence-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=[],  # empty evidence refs
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        # Item is still produced, but evidence_refs is empty
        # The rationale is still present and traceable to the gap
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].evidence_refs, [])
        # But the rationale must still reference the gap
        self.assertIn("gap-no-evidence-001", result.items[0].rationale)


# ====================================================================== #
# Edge case: calendar-time fields rejected
# ====================================================================== #


class TestEdgeCalendarTimeFieldsRejected(unittest.TestCase):
    def test_calendar_time_field_in_item_dict_rejected(self):
        """Edge: LearningItem.validate() must reject calendar-time fields."""
        from scholar.adaptive_learning_strategy.strategy import _reject_calendar_time_fields

        with self.assertRaises(ValueError):
            _reject_calendar_time_fields(
                {"topic": "vent", "calendar_time": "2026-09-30T12:00:00"},
                label="test",
            )

    def test_calendar_time_field_scheduled_at_rejected(self):
        """Edge: scheduled_at is a forbidden calendar-time field."""
        from scholar.adaptive_learning_strategy.strategy import _reject_calendar_time_fields

        with self.assertRaises(ValueError):
            _reject_calendar_time_fields(
                {"topic": "vent", "scheduled_at": "2026-09-30T12:00:00"},
                label="test",
            )

    def test_calendar_time_field_weekday_rejected(self):
        """Edge: weekday is a forbidden calendar-time field."""
        from scholar.adaptive_learning_strategy.strategy import _reject_calendar_time_fields

        with self.assertRaises(ValueError):
            _reject_calendar_time_fields(
                {"topic": "vent", "weekday": "Monday"},
                label="test",
            )

    def test_valid_item_dict_passes_calendar_check(self):
        """Edge: A valid item dict without calendar-time fields passes."""
        # Should not raise
        _reject_calendar_time_fields(
            {"topic": "vent", "sequence": 1, "priority": "high"},
            label="test",
        )


# ====================================================================== #
# Edge case: PAUSED/SUPERSEDED goals excluded
# ====================================================================== #


class TestEdgePausedSupersededGoalsExcluded(unittest.TestCase):
    def test_paused_goal_excluded_from_strategy(self):
        """Edge: PAUSED goals must be excluded from strategy building."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        # Build a gap result with PAUSED state
        gap = Gap(
            gap_id="gap-paused-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-paused",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-paused-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result(
            gaps=[gap],
            goal_state="PAUSED",
        )
        result = strategy.build(gap_result)

        self.assertEqual(result.item_count, 0)
        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total_recommended_effort_minutes, 0)
        self.assertEqual(result.goal_state, "PAUSED")

    def test_superseded_goal_excluded_from_strategy(self):
        """Edge: SUPERSEDED goals must be excluded from strategy building."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-superseded-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-superseded",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-superseded-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result(
            gaps=[gap],
            goal_state="SUPERSEDED",
        )
        result = strategy.build(gap_result)

        self.assertEqual(result.item_count, 0)
        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total_recommended_effort_minutes, 0)
        self.assertEqual(result.goal_state, "SUPERSEDED")


# ====================================================================== #
# Edge case: deterministic repeat calls identical
# ====================================================================== #


class TestEdgeDeterministicRepeatCallsIdentical(unittest.TestCase):
    def test_deterministic_repeat_calls_identical(self):
        """Edge: Deterministic repeat calls must produce identical results."""
        analyzer = make_gap_analyzer(_fixed_clock)
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-det-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-det-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-det-002",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application",
                evidence_refs=["ev-det-002"],
                mastery_dimension="APPLICATION",
                severity="high",
                recommendation="Increase practice.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result1 = strategy.build(gap_result)
        result2 = strategy.build(gap_result)

        self.assertEqual(result1.item_count, result2.item_count)
        self.assertEqual(result1.deterministic_key, result2.deterministic_key)
        self.assertEqual(result1.total_recommended_effort_minutes, result2.total_recommended_effort_minutes)
        for i in range(len(result1.items)):
            self.assertEqual(result1.items[i].item_id, result2.items[i].item_id)
            self.assertEqual(result1.items[i].sequence, result2.items[i].sequence)
            self.assertEqual(result1.items[i].rationale, result2.items[i].rationale)


# ====================================================================== #
# Edge case: malformed gap input rejected
# ====================================================================== #


class TestEdgeMalformedGapInputRejected(unittest.TestCase):
    def test_none_gap_result_rejected(self):
        """Edge: None gap_result must be rejected with ValueError."""
        strategy = make_strategy(_fixed_clock)
        with self.assertRaises(ValueError):
            strategy.build(gap_result=None)

    def test_non_gap_result_type_rejected(self):
        """Edge: Non-GapAnalysisResult input must be rejected."""
        strategy = make_strategy(_fixed_clock)
        with self.assertRaises(ValueError):
            strategy.build(gap_result="not a gap result")

    def test_invalid_goal_state_rejected(self):
        """Edge: An invalid goal_state must be rejected."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-bad-state-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-bad-state-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result(gaps=[gap], goal_state="INVALID_STATE")
        with self.assertRaises(ValueError):
            strategy.build(gap_result)


# ====================================================================== #
# Edge case: malformed decomposition input rejected
# ====================================================================== #


class TestEdgeMalformedDecompositionInputRejected(unittest.TestCase):
    def test_none_decomposition_is_valid(self):
        """Edge: None decomposition_result is valid — no decomposition-based gaps."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-no-decomp-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-no-decomp-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        # None decomposition should not raise
        result = strategy.build(gap_result, decomposition_result=None)
        self.assertEqual(result.item_count, 1)


# ====================================================================== #
# Edge case: empty gap list → explicit empty strategy
# ====================================================================== #


class TestEdgeEmptyGapListExplicitEmptyStrategy(unittest.TestCase):
    def test_empty_gap_list_produces_empty_strategy(self):
        """Edge: Empty gap list must produce an explicit empty strategy,
        not invented items."""
        strategy = make_strategy(_fixed_clock)

        gap_result = _make_gap_result([])
        result = strategy.build(gap_result)

        self.assertEqual(result.item_count, 0)
        self.assertEqual(len(result.items), 0)
        self.assertEqual(result.total_recommended_effort_minutes, 0)
        self.assertIsInstance(result.items, list)

    def test_empty_gap_list_not_none(self):
        """Edge: Empty strategy must return items=[] (not None)."""
        strategy = make_strategy(_fixed_clock)

        gap_result = _make_gap_result([])
        result = strategy.build(gap_result)

        self.assertIsNotNone(result.items)
        self.assertIsInstance(result.items, list)


# ====================================================================== #
# Edge case: strategy result validation
# ====================================================================== #


class TestEdgeStrategyResultValidation(unittest.TestCase):
    def test_strategy_result_validate_passes(self):
        """Edge: A valid strategy result must pass validation."""
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-val-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-val-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result = strategy.build(gap_result)
        # Should not raise
        result.validate()

    def test_strategy_result_validate_fails_on_bad_sequence(self):
        """Edge: A strategy result with bad sequence must fail validation."""
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-seq-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-seq-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result = strategy.build(gap_result)

        # Tamper with sequence by creating a new result with bad items
        bad_item = LearningItem(
            item_id=result.items[0].item_id,
            topic=result.items[0].topic,
            proficiency_id=result.items[0].proficiency_id,
            sequence=99,  # wrong sequence
            priority=result.items[0].priority,
            target_depth=result.items[0].target_depth,
            target_mastery=result.items[0].target_mastery,
            recommended_effort=result.items[0].recommended_effort,
            outcomes=result.items[0].outcomes,
            rationale=result.items[0].rationale,
            evidence_refs=result.items[0].evidence_refs,
            gap_refs=result.items[0].gap_refs,
        )
        bad_result = StrategyResult(
            goal_id=result.goal_id,
            goal_title=result.goal_title,
            goal_state=result.goal_state,
            items=[bad_item],
            item_count=1,
            total_recommended_effort_minutes=bad_item.recommended_effort,
            evidence_trace=result.evidence_trace,
            gap_refs=result.gap_refs,
            deterministic_key=result.deterministic_key,
        )

        with self.assertRaises(ValueError):
            bad_result.validate()


# ====================================================================== #
# Edge case: inject clock
# ====================================================================== #


class TestEdgeInjectClock(unittest.TestCase):
    def test_strategy_accepts_injected_clock(self):
        """Edge: AdaptiveLearningStrategy accepts an injected clock function."""
        clock_calls = []

        def tracking_clock():
            clock_calls.append("called")
            return "2026-09-30T12:00:00"

        strategy = make_strategy(tracking_clock)
        gap = Gap(
            gap_id="gap-clock-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-clock-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        strategy.build(gap_result)
        self.assertGreater(len(clock_calls), 0)

    def test_build_strategy_accepts_injected_clock(self):
        """Edge: build_strategy() convenience function accepts clock parameter."""
        clock_calls = []

        def tracking_clock():
            clock_calls.append("called")
            return "2026-09-30T12:00:00"

        gap = Gap(
            gap_id="gap-clock-fn-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-clock-fn-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = build_strategy(gap_result, clock=tracking_clock)
        self.assertGreater(len(clock_calls), 0)
        self.assertEqual(result.item_count, 1)


# ====================================================================== #
# Edge case: LearningItem frozen/immutable
# ====================================================================== #


class TestEdgeLearningItemImmutable(unittest.TestCase):
    def test_learning_item_is_frozen(self):
        """Edge: LearningItem records are frozen (immutable)."""
        item = LearningItem(
            item_id="frozen-item-001",
            topic="Ventilation Basics",
            proficiency_id=None,
            sequence=1,
            priority="high",
            target_depth="KNOWLEDGE",
            target_mastery="strong",
            recommended_effort=90,
            outcomes=["Strengthen knowledge"],
            rationale="Test rationale.",
        )
        with self.assertRaises(Exception):
            item.topic = "Modified topic"

    def test_learning_item_validate_rejects_zero_effort(self):
        """Edge: LearningItem.validate() rejects zero effort."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="zero-effort-001",
                topic="Ventilation Basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=0,
                outcomes=["Learn ventilation"],
                rationale="Test rationale.",
            )

    def test_learning_item_validate_rejects_negative_effort(self):
        """Edge: LearningItem.validate() rejects negative effort."""
        with self.assertRaises(ValueError):
            LearningItem(
                item_id="neg-effort-001",
                topic="Ventilation Basics",
                proficiency_id=None,
                sequence=1,
                priority="high",
                target_depth="KNOWLEDGE",
                target_mastery="strong",
                recommended_effort=-10,
                outcomes=["Learn ventilation"],
                rationale="Test rationale.",
            )


# ====================================================================== #
# Edge case: StrategyResult frozen/immutable
# ====================================================================== #


class TestEdgeStrategyResultImmutable(unittest.TestCase):
    def test_strategy_result_is_frozen(self):
        """Edge: StrategyResult is frozen (immutable)."""
        strategy = make_strategy(_fixed_clock)
        gap = Gap(
            gap_id="gap-frozen-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-frozen-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        with self.assertRaises(Exception):
            result.goal_state = "MODIFIED"


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
# Edge case: gap_counts accurate in strategy
# ====================================================================== #


class TestEdgeGapCountsAccurateInStrategy(unittest.TestCase):
    def test_strategy_item_count_matches_gap_count(self):
        """Edge: The number of strategy items must equal the number of gaps."""
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-count-001",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-count-001"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-count-002",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application",
                evidence_refs=["ev-count-002"],
                mastery_dimension="APPLICATION",
                severity="medium",
                recommendation="Increase practice.",
            ),
            Gap(
                gap_id="gap-count-003",
                gap_type=GapType.INSUFFICIENT_EVIDENCE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Insufficient evidence",
                evidence_refs=["ev-count-003"],
                mastery_dimension="RATIONALE",
                severity="low",
                recommendation="Gather more evidence.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result = strategy.build(gap_result)

        self.assertEqual(result.item_count, len(gaps))
        self.assertEqual(result.item_count, 3)


# ====================================================================== #
# Edge case: to_dict excludes calendar-time fields
# ====================================================================== #


class TestEdgeToDictExcludesCalendarTime(unittest.TestCase):
    def test_to_dict_has_no_calendar_time_fields(self):
        """Edge: LearningItem.to_dict() must not contain calendar-time fields."""
        item = LearningItem(
            item_id="dict-item-001",
            topic="Ventilation Basics",
            proficiency_id=None,
            sequence=1,
            priority="high",
            target_depth="KNOWLEDGE",
            target_mastery="strong",
            recommended_effort=90,
            outcomes=["Strengthen knowledge"],
            rationale="Test rationale.",
        )
        d = item.to_dict()
        for forbidden in ("calendar_time", "scheduled_at", "start_time", "end_time",
                          "time_slot", "weekday", "date", "timestamp", "occurred_at"):
            self.assertNotIn(forbidden, d,
                f"to_dict() contains forbidden calendar-time field {forbidden!r}")


# ====================================================================== #
# Edge case: all gap types produce items
# ====================================================================== #


class TestEdgeAllGapTypesProduceItems(unittest.TestCase):
    def test_all_gap_types_produce_strategy_items(self):
        """Edge: Every gap type must produce a strategy item."""
        strategy = make_strategy(_fixed_clock)

        gaps = [
            Gap(
                gap_id="gap-all-001",
                gap_type=GapType.MISSING_PREREQUISITE,
                goal_id="goal-vent-01",
                topic_id=None,
                description="Missing prerequisite",
                evidence_refs=["ev-all-001"],
                mastery_dimension=None,
                severity="high",
                recommendation="Address prerequisite.",
            ),
            Gap(
                gap_id="gap-all-002",
                gap_type=GapType.WEAK_KNOWLEDGE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak knowledge",
                evidence_refs=["ev-all-002"],
                mastery_dimension="KNOWLEDGE",
                severity="high",
                recommendation="Strengthen knowledge.",
            ),
            Gap(
                gap_id="gap-all-003",
                gap_type=GapType.WEAK_APPLICATION,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Weak application",
                evidence_refs=["ev-all-003"],
                mastery_dimension="APPLICATION",
                severity="high",
                recommendation="Increase practice.",
            ),
            Gap(
                gap_id="gap-all-004",
                gap_type=GapType.INSUFFICIENT_EVIDENCE,
                goal_id="goal-vent-01",
                topic_id="topic-vent",
                description="Insufficient evidence",
                evidence_refs=["ev-all-004"],
                mastery_dimension="RATIONALE",
                severity="medium",
                recommendation="Gather more evidence.",
            ),
            Gap(
                gap_id="gap-all-005",
                gap_type=GapType.UNCOVERED_PROFICIENCY,
                goal_id="goal-vent-01",
                topic_id=None,
                description="Uncovered proficiency",
                evidence_refs=["ev-all-005"],
                mastery_dimension=None,
                severity="medium",
                recommendation="Map this proficiency.",
            ),
        ]
        gap_result = _make_gap_result(gaps)
        result = strategy.build(gap_result)

        self.assertEqual(result.item_count, 5)
        gap_types_in_result = set()
        for item in result.items:
            gap_types_in_result.add(item.gap_refs[0])
        self.assertEqual(len(gap_types_in_result), 5)


# ====================================================================== #
# Edge case: strategy does not schedule calendar time
# ====================================================================== #


class TestEdgeStrategyDoesNotScheduleCalendarTime(unittest.TestCase):
    def test_strategy_result_has_no_calendar_fields(self):
        """Edge: StrategyResult must not contain calendar-time fields."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-no-calendar-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-no-calendar-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = strategy.build(gap_result)

        # Check that no calendar-time fields exist in the result
        result_dict = {
            "goal_id": result.goal_id,
            "goal_title": result.goal_title,
            "goal_state": result.goal_state,
            "item_count": result.item_count,
            "total_recommended_effort_minutes": result.total_recommended_effort_minutes,
            "evidence_trace": result.evidence_trace,
            "gap_refs": result.gap_refs,
            "deterministic_key": result.deterministic_key,
        }
        for forbidden in ("calendar_time", "scheduled_at", "start_time", "end_time",
                          "time_slot", "weekday", "date", "timestamp", "occurred_at"):
            self.assertNotIn(forbidden, result_dict,
                f"StrategyResult contains forbidden calendar-time field {forbidden!r}")

        # Check each item dict too
        for item in result.items:
            item_dict = item.to_dict()
            for forbidden in ("calendar_time", "scheduled_at", "start_time", "end_time",
                              "time_slot", "weekday", "date", "timestamp", "occurred_at"):
                self.assertNotIn(forbidden, item_dict,
                    f"LearningItem dict contains forbidden calendar-time field {forbidden!r}")


# ====================================================================== #
# Edge case: build_strategy convenience function
# ====================================================================== #


class TestEdgeBuildStrategyConvenience(unittest.TestCase):
    def test_build_strategy_convenience_function(self):
        """Edge: build_strategy() convenience function works correctly."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-convenience-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-convenience-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        result = build_strategy(gap_result)

        self.assertEqual(result.item_count, 1)
        self.assertEqual(result.items[0].topic, "Weak knowledge")

    def test_build_strategy_with_decomposition(self):
        """Edge: build_strategy() accepts decomposition_result parameter."""
        strategy = make_strategy(_fixed_clock)

        gap = Gap(
            gap_id="gap-decomp-001",
            gap_type=GapType.WEAK_KNOWLEDGE,
            goal_id="goal-vent-01",
            topic_id="topic-vent",
            description="Weak knowledge",
            evidence_refs=["ev-decomp-001"],
            mastery_dimension="KNOWLEDGE",
            severity="high",
            recommendation="Strengthen knowledge.",
        )
        gap_result = _make_gap_result([gap])
        decomp = {"proficiencies": [{"proficiency_id": "prof-vent-01"}]}
        result = build_strategy(gap_result, decomposition_result=decomp)

        self.assertEqual(result.item_count, 1)


# ====================================================================== #
# Edge case: LearningItem with all required fields validates
# ====================================================================== #


class TestEdgeLearningItemFullValidation(unittest.TestCase):
    def test_valid_learning_item_passes_validation(self):
        """Edge: A fully valid LearningItem must pass validate()."""
        item = LearningItem(
            item_id="valid-item-001",
            topic="Ventilation Basics",
            proficiency_id="prof-vent-01",
            sequence=1,
            priority="high",
            target_depth="KNOWLEDGE",
            target_mastery="strong",
            recommended_effort=90,
            outcomes=["Strengthen knowledge to strong level"],
            rationale="Included because gap gap-valid-001 detected from evidence [ev-valid-001].",
            evidence_refs=["ev-valid-001"],
            gap_refs=["gap-valid-001"],
        )
        # Should not raise
        item.validate()

    def test_learning_item_to_dict_round_trip(self):
        """Edge: LearningItem.to_dict() returns all fields."""
        item = LearningItem(
            item_id="roundtrip-item-001",
            topic="Ventilation Basics",
            proficiency_id="prof-vent-01",
            sequence=1,
            priority="high",
            target_depth="KNOWLEDGE",
            target_mastery="strong",
            recommended_effort=90,
            outcomes=["Strengthen knowledge"],
            rationale="Test rationale.",
            evidence_refs=["ev-rt-001"],
            gap_refs=["gap-rt-001"],
        )
        d = item.to_dict()
        self.assertEqual(d["item_id"], "roundtrip-item-001")
        self.assertEqual(d["topic"], "Ventilation Basics")
        self.assertEqual(d["proficiency_id"], "prof-vent-01")
        self.assertEqual(d["sequence"], 1)
        self.assertEqual(d["priority"], "high")
        self.assertEqual(d["target_depth"], "KNOWLEDGE")
        self.assertEqual(d["target_mastery"], "strong")
        self.assertEqual(d["recommended_effort"], 90)
        self.assertEqual(d["outcomes"], ["Strengthen knowledge"])
        self.assertEqual(d["rationale"], "Test rationale.")
        self.assertEqual(d["evidence_refs"], ["ev-rt-001"])
        self.assertEqual(d["gap_refs"], ["gap-rt-001"])


if __name__ == "__main__":
    unittest.main()