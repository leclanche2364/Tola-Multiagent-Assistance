"""
Batch S3 -- Learner-State Reader.
LearnerStateReader with injectable fetch callable (no network).
Plain ASCII. Python 3 stdlib only.
"""

from typing import Any, Callable

from scholar.learner_state.aggregate import LearnerState, build_learner_state


class LearnerStateReader:
    def __init__(self, fetch: Callable[[str], dict]) -> None:
        self._fetch = fetch

    def read(self, course_id: str) -> LearnerState:
        raw = self._fetch(course_id)
        return build_learner_state(raw)
