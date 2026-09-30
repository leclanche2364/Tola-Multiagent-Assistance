"""
Batch S3 -- Learner-State Fixtures.
Deterministic fixture dicts for S3 QA.
Plain ASCII. Python 3 stdlib only.
"""

SIMPLE_COURSE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.8, "date": "2026-09-29"}
            ],
            "recent_study_activity": ["reading"],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-1",
}

MULTI_TOPIC_COURSE = {
    "schema_version": "1.0",
    "state_version": "2",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1", "Goal 2"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.3,
            "next_action": "study",
            "practice_units": 2,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.6, "date": "2026-09-28"}
            ],
            "recent_study_activity": ["reading"],
        },
        {
            "id": "topic-2",
            "progress": 0.8,
            "next_action": "practice",
            "practice_units": 5,
            "recent_assessments": [
                {"id": "a2", "status": "completed", "score": 0.9, "date": "2026-09-29"}
            ],
            "recent_study_activity": ["practice"],
        },
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-2",
}

INCOMPLETE_PROGRESS = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.1,
            "next_action": "start",
            "practice_units": 1,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-3",
}

HIGH_PROGRESS = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.95,
            "next_action": "assess",
            "practice_units": 10,
            "recent_assessments": [
                {"id": "a1", "status": "completed", "score": 0.95, "date": "2026-09-30"}
            ],
            "recent_study_activity": ["practice", "review"],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-4",
}

STALE_LEARNER_STATE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-01-01T00:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-5",
}

REASONING_EVIDENCE_PRESENT = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [
        {"id": "r1", "type": "clinical_reasoning", "summary": "Patient shows improvement"}
    ],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-6",
}

COMPETENCY_EVIDENCE_AUTHORITATIVE = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [
        {
            "source": "supervisor_signoff",
            "authoritative": True,
            "competency": "clinical_assessment",
        }
    ],
    "revision_items": [],
    "cursor": "cursor-7",
}

COMPETENCY_EVIDENCE_NO_AUTHORITY = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [
        {
            "source": "self_assessment",
            "authoritative": False,
            "competency": "clinical_assessment",
        }
    ],
    "revision_items": [],
    "cursor": "cursor-8",
}

MISSING_SECTIONS = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [],
            "recent_study_activity": [],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "cursor": "cursor-9",
}

ASSESSMENTS_WITH_ANSWER_KEYS = {
    "schema_version": "1.0",
    "state_version": "1",
    "as_of": "2026-09-30T12:00:00",
    "course": "Critical Care Foundations",
    "course_goals": ["Goal 1"],
    "proficiency_context": [],
    "topics": [
        {
            "id": "topic-1",
            "progress": 0.5,
            "next_action": "review",
            "practice_units": 3,
            "recent_assessments": [
                {
                    "id": "a1",
                    "status": "completed",
                    "score": 0.8,
                    "date": "2026-09-29",
                    "answer_key": "A",
                    "correct_answer": "B",
                    "solution": "Explanation text",
                }
            ],
            "recent_study_activity": ["reading"],
        }
    ],
    "reasoning_evidence": [],
    "competency_evidence": [],
    "revision_items": [],
    "cursor": "cursor-10",
}
