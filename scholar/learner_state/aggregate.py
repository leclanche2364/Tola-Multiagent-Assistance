"""
Batch S3 -- Learner-State Aggregate.
Typed LearnerState aggregate with Absent markers, redaction,
competency-evidence sign-off logic, and freshness helper.
Plain ASCII. Python 3 stdlib only.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Absent:
    present: bool = False
    reason: str = "not_provided_by_source"


@dataclass(frozen=True)
class LearnerState:
    schema_version: Any
    state_version: Any
    as_of: Any
    course: Any
    course_goals: Any
    proficiency_context: Any
    topics: Any
    reasoning_evidence: Any
    competency_evidence: Any
    revision_items: Any
    cursor: Any

    @property
    def formal_competence(self) -> str:
        if isinstance(self.competency_evidence, Absent):
            return "UNSIGNED"
        if not isinstance(self.competency_evidence, list):
            return "UNSIGNED"
        for entry in self.competency_evidence:
            if isinstance(entry, dict) and entry.get("authoritative") is True:
                return "SIGNED_OFF"
        return "UNSIGNED"


_REDACTION_FIELDS = frozenset({
    "answer_key",
    "correct_answer",
    "solution",
})


def _redact_assessment(assessment: dict) -> dict:
    return {k: v for k, v in assessment.items() if k not in _REDACTION_FIELDS}


def _section(raw: dict, key: str) -> Any:
    if key in raw:
        return raw[key]
    return Absent(present=False, reason="not_provided_by_source")


def _process_topic(topic: dict) -> dict:
    result = {}
    for field in ("progress", "next_action", "practice_units",
                  "recent_assessments", "recent_study_activity"):
        if field in topic:
            value = topic[field]
            if field == "recent_assessments" and isinstance(value, list):
                value = [
                    _redact_assessment(a) if isinstance(a, dict) else a
                    for a in value
                ]
            result[field] = value
        else:
            result[field] = Absent(
                present=False, reason="not_provided_by_source"
            )
    for k, v in topic.items():
        if k not in result:
            result[k] = v
    return result


def build_learner_state(raw: dict) -> LearnerState:
    for key in ("schema_version", "state_version"):
        if key not in raw:
            raise ValueError(f"Missing required field: {key}")
        val = raw[key]
        if not isinstance(val, str) or not val.strip():
            raise ValueError(
                f"{key} must be a non-empty string, got {val!r}"
            )

    topics_raw = _section(raw, "topics")
    if not isinstance(topics_raw, Absent) and isinstance(topics_raw, list):
        processed = []
        for t in topics_raw:
            if isinstance(t, dict):
                processed.append(_process_topic(t))
            else:
                processed.append(t)
        topics = processed
    else:
        topics = topics_raw

    return LearnerState(
        schema_version=raw["schema_version"],
        state_version=raw["state_version"],
        as_of=_section(raw, "as_of"),
        course=_section(raw, "course"),
        course_goals=_section(raw, "course_goals"),
        proficiency_context=_section(raw, "proficiency_context"),
        topics=topics,
        reasoning_evidence=_section(raw, "reasoning_evidence"),
        competency_evidence=_section(raw, "competency_evidence"),
        revision_items=_section(raw, "revision_items"),
        cursor=_section(raw, "cursor"),
    )


def is_stale(as_of: str, now: str, max_age_minutes: int) -> bool:
    as_of_dt = datetime.fromisoformat(as_of)
    now_dt = datetime.fromisoformat(now)
    age_minutes = (now_dt - as_of_dt).total_seconds() / 60
    return age_minutes > max_age_minutes
