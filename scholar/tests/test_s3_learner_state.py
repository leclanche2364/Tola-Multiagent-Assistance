"""
Batch S3 -- Learner-State QA Tests (S3-01..S3-09).
Plain ASCII. Python 3 stdlib only.
"""

import unittest

from scholar.learner_state.aggregate import (
    Absent,
    LearnerState,
    build_learner_state,
    is_stale,
)
from scholar.learner_state.reader import LearnerStateReader
from scholar.fixtures.learner_states import (
    SIMPLE_COURSE,
    MULTI_TOPIC_COURSE,
    INCOMPLETE_PROGRESS,
    HIGH_PROGRESS,
    STALE_LEARNER_STATE,
    REASONING_EVIDENCE_PRESENT,
    COMPETENCY_EVIDENCE_AUTHORITATIVE,
    COMPETENCY_EVIDENCE_NO_AUTHORITY,
    MISSING_SECTIONS,
    ASSESSMENTS_WITH_ANSWER_KEYS,
)


class TestS3_01_Course(unittest.TestCase):
    def test_course_matches_source(self):
        state = build_learner_state(SIMPLE_COURSE)
        self.assertEqual(state.course, "Critical Care Foundations")

    def test_course_matches_source_multi_topic(self):
        state = build_learner_state(MULTI_TOPIC_COURSE)
        self.assertEqual(state.course, "Critical Care Foundations")


class TestS3_02_Goals(unittest.TestCase):
    def test_goals_match_source(self):
        state = build_learner_state(SIMPLE_COURSE)
        self.assertEqual(state.course_goals, ["Goal 1"])

    def test_goals_match_source_multiple(self):
        state = build_learner_state(MULTI_TOPIC_COURSE)
        self.assertEqual(state.course_goals, ["Goal 1", "Goal 2"])


class TestS3_03_TopicProgress(unittest.TestCase):
    def test_topic_progress_matches_source(self):
        state = build_learner_state(MULTI_TOPIC_COURSE)
        self.assertEqual(state.topics[0]["progress"], 0.3)
        self.assertEqual(state.topics[1]["progress"], 0.8)

    def test_topic_next_action_matches_source(self):
        state = build_learner_state(MULTI_TOPIC_COURSE)
        self.assertEqual(state.topics[0]["next_action"], "study")
        self.assertEqual(state.topics[1]["next_action"], "practice")

    def test_topic_practice_units_matches_source(self):
        state = build_learner_state(MULTI_TOPIC_COURSE)
        self.assertEqual(state.topics[0]["practice_units"], 2)
        self.assertEqual(state.topics[1]["practice_units"], 5)


class TestS3_04_Practice(unittest.TestCase):
    def test_practice_units_matches_source(self):
        state = build_learner_state(SIMPLE_COURSE)
        self.assertEqual(state.topics[0]["practice_units"], 3)

    def test_practice_units_incomplete(self):
        state = build_learner_state(INCOMPLETE_PROGRESS)
        self.assertEqual(state.topics[0]["practice_units"], 1)


class TestS3_05_AssessmentsRedaction(unittest.TestCase):
    def test_answer_key_dropped(self):
        state = build_learner_state(ASSESSMENTS_WITH_ANSWER_KEYS)
        assessment = state.topics[0]["recent_assessments"][0]
        self.assertNotIn("answer_key", assessment)
        self.assertNotIn("correct_answer", assessment)
        self.assertNotIn("solution", assessment)

    def test_id_status_score_date_preserved(self):
        state = build_learner_state(ASSESSMENTS_WITH_ANSWER_KEYS)
        assessment = state.topics[0]["recent_assessments"][0]
        self.assertEqual(assessment["id"], "a1")
        self.assertEqual(assessment["status"], "completed")
        self.assertEqual(assessment["score"], 0.8)
        self.assertEqual(assessment["date"], "2026-09-29")


class TestS3_06_ReasoningEvidence(unittest.TestCase):
    def test_reasoning_evidence_included(self):
        state = build_learner_state(REASONING_EVIDENCE_PRESENT)
        self.assertEqual(len(state.reasoning_evidence), 1)
        self.assertEqual(state.reasoning_evidence[0]["id"], "r1")

    def test_reasoning_evidence_absent_when_not_provided(self):
        # When the source omits reasoning_evidence entirely, it becomes Absent.
        raw = {
            "schema_version": "1.0",
            "state_version": "1",
            "as_of": "2026-09-30T12:00:00",
            "course": "X",
            "course_goals": [],
            "proficiency_context": [],
            "topics": [],
            "competency_evidence": [],
            "revision_items": [],
            "cursor": "",
        }
        state = build_learner_state(raw)
        self.assertIsInstance(state.reasoning_evidence, Absent)
        self.assertFalse(state.reasoning_evidence.present)


class TestS3_07_CompetencyEvidence(unittest.TestCase):
    def test_authoritative_true_sets_signed_off(self):
        state = build_learner_state(COMPETENCY_EVIDENCE_AUTHORITATIVE)
        self.assertEqual(state.formal_competence, "SIGNED_OFF")

    def test_authoritative_false_keeps_unsigned(self):
        state = build_learner_state(COMPETENCY_EVIDENCE_NO_AUTHORITY)
        self.assertEqual(state.formal_competence, "UNSIGNED")

    def test_no_competency_evidence_keeps_unsigned(self):
        state = build_learner_state(SIMPLE_COURSE)
        self.assertEqual(state.formal_competence, "UNSIGNED")

    def test_no_inference_from_practice(self):
        state = build_learner_state(HIGH_PROGRESS)
        self.assertEqual(state.formal_competence, "UNSIGNED")


class TestS3_08_Freshness(unittest.TestCase):
    def test_as_of_preserved(self):
        state = build_learner_state(SIMPLE_COURSE)
        self.assertEqual(state.as_of, "2026-09-30T12:00:00")

    def test_state_version_preserved(self):
        state = build_learner_state(SIMPLE_COURSE)
        self.assertEqual(state.state_version, "1")

    def test_is_stale_false_within_window(self):
        self.assertFalse(is_stale("2026-09-30T12:00:00", "2026-09-30T12:30:00", 60))

    def test_is_stale_true_beyond_window(self):
        self.assertTrue(is_stale("2026-09-30T12:00:00", "2026-09-30T13:30:00", 60))

    def test_is_stale_exactly_at_boundary_not_stale(self):
        self.assertFalse(is_stale("2026-09-30T12:00:00", "2026-09-30T13:00:00", 60))

    def test_stale_state_detection(self):
        state = build_learner_state(STALE_LEARNER_STATE)
        self.assertTrue(is_stale(state.as_of, "2026-09-30T12:00:00", 60))


class TestS3_09_MissingData(unittest.TestCase):
    def test_missing_course_goals_is_absent(self):
        state = build_learner_state(MISSING_SECTIONS)
        self.assertIsInstance(state.course_goals, Absent)
        self.assertFalse(state.course_goals.present)

    def test_missing_revision_items_is_absent(self):
        state = build_learner_state(MISSING_SECTIONS)
        self.assertIsInstance(state.revision_items, Absent)
        self.assertFalse(state.revision_items.present)

    def test_missing_as_of_is_absent(self):
        raw = {
            "schema_version": "1.0",
            "state_version": "1",
            "course": "X",
            "topics": [],
        }
        state = build_learner_state(raw)
        self.assertIsInstance(state.as_of, Absent)
        self.assertFalse(state.as_of.present)

    def test_missing_topics_is_absent(self):
        raw = {
            "schema_version": "1.0",
            "state_version": "1",
            "course": "X",
        }
        state = build_learner_state(raw)
        self.assertIsInstance(state.topics, Absent)
        self.assertFalse(state.topics.present)

    def test_no_fabricated_topic_names(self):
        raw = {
            "schema_version": "1.0",
            "state_version": "1",
            "course": "X",
            "course_goals": [],
            "proficiency_context": [],
            "topics": [],
            "reasoning_evidence": [],
            "competency_evidence": [],
            "revision_items": [],
            "cursor": "",
        }
        state = build_learner_state(raw)
        self.assertEqual(state.topics, [])

    def test_no_fabricated_goals(self):
        raw = {
            "schema_version": "1.0",
            "state_version": "1",
            "course": "X",
            "course_goals": [],
            "proficiency_context": [],
            "topics": [],
            "reasoning_evidence": [],
            "competency_evidence": [],
            "revision_items": [],
            "cursor": "",
        }
        state = build_learner_state(raw)
        self.assertEqual(state.course_goals, [])


class TestMalformedRaw(unittest.TestCase):
    def test_missing_schema_version_raises(self):
        raw = {
            "state_version": "1",
            "course": "X",
            "topics": [],
        }
        with self.assertRaises(ValueError):
            build_learner_state(raw)

    def test_missing_state_version_raises(self):
        raw = {
            "schema_version": "1.0",
            "course": "X",
            "topics": [],
        }
        with self.assertRaises(ValueError):
            build_learner_state(raw)

    def test_empty_schema_version_raises(self):
        raw = {
            "schema_version": "",
            "state_version": "1",
            "course": "X",
            "topics": [],
        }
        with self.assertRaises(ValueError):
            build_learner_state(raw)


class TestReader(unittest.TestCase):
    def test_reader_returns_learner_state(self):
        reader = LearnerStateReader(lambda cid: SIMPLE_COURSE)
        state = reader.read("course-1")
        self.assertIsInstance(state, LearnerState)
        self.assertEqual(state.course, "Critical Care Foundations")

    def test_reader_preserves_cursor(self):
        reader = LearnerStateReader(lambda cid: SIMPLE_COURSE)
        state = reader.read("course-1")
        self.assertEqual(state.cursor, "cursor-1")

    def test_reader_passes_course_id_to_fetch(self):
        calls = []
        def fake_fetch(cid):
            calls.append(cid)
            return SIMPLE_COURSE
        reader = LearnerStateReader(fake_fetch)
        reader.read("my-course")
        self.assertEqual(calls, ["my-course"])


if __name__ == "__main__":
    unittest.main()