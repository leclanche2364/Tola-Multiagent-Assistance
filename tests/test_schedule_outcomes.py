"""Batch 8 QA tests for schedule_outcomes and resolve_conflict."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.rhythm.schedule_outcomes import (
    resolve_conflict,
    schedule_outcomes,
)
from agents.daily_synthesis.contracts import ValidationError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _plan(**overrides):
    defaults = dict(
        schema_version="daily_plan_to_rhythm.v1",
        agent_id="agent-1",
        plan_id="plan-1",
        rhythm_id="r1",
        learning_detail={"exact_action": "read article X", "article": "X"},
        schedule_slots=[],
    )
    defaults.update(overrides)
    return defaults


def _handoff(**overrides):
    defaults = dict(
        schema_version="rhythm_capacity_handoff.v1",
        agent_id="agent-1",
        rhythm_id="r1",
        capacity_used_minutes=0,
        capacity_total_minutes=120,
        recovery_buffer_minutes=10,
        capacity_summary={
            "max_major_outcomes": 3,
            "total_available_minutes": 110,
            "total_committed_minutes": 0,
            "total_recovery_minutes": 10,
            "protected_learning_minutes": 0,
        },
        windows=[
            {
                "start": "2026-10-03T09:00:00+00:00",
                "end": "2026-10-03T09:50:00+00:00",
                "duration_minutes": 50,
                "work_type": "deep",
                "confidence": 0.9,
                "constraints": [],
            },
        ],
    )
    defaults.update(overrides)
    return defaults


def _outcome(**overrides):
    defaults = dict(
        id="o1",
        duration_minutes=30,
        energy="medium",
        is_hard_appointment=False,
        learning_detail={"exact_action": "read article X"},
        priority=1,
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# 1. 60-min task vs 40-min window → conflict with alternatives
# ---------------------------------------------------------------------------

class TaskTooLargeForWindowTest(unittest.TestCase):
    def test_60_min_task_40_min_window_conflict(self):
        plan = _plan(schedule_slots=[_outcome(duration_minutes=60)])
        handoff = _handoff(
            capacity_total_minutes=40,
            capacity_used_minutes=0,
            recovery_buffer_minutes=0,
            capacity_summary={
                "max_major_outcomes": 3,
                "total_available_minutes": 40,
                "total_committed_minutes": 0,
                "total_recovery_minutes": 0,
                "protected_learning_minutes": 0,
            },
            windows=[
                {
                    "start": "2026-10-03T09:00:00+00:00",
                    "end": "2026-10-03T09:40:00+00:00",
                    "duration_minutes": 40,
                    "work_type": "deep",
                    "confidence": 0.9,
                    "constraints": [],
                },
            ],
        )
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_conflict.v1")
        self.assertEqual(result["outcome_id"], "o1")
        self.assertEqual(result["reason"], "capacity_exceeded")
        self.assertEqual(result["required_minutes"], 60)
        self.assertEqual(result["available_minutes"], 40)
        self.assertIn("split_task", result["possible_alternatives"])
        self.assertIn("reduce_scope", result["possible_alternatives"])
        self.assertIn("defer", result["possible_alternatives"])


# ---------------------------------------------------------------------------
# 2. Deep task only has light window → conflict
# ---------------------------------------------------------------------------

class DeepTaskLightWindowTest(unittest.TestCase):
    def test_deep_task_light_window_conflict(self):
        plan = _plan(schedule_slots=[_outcome(duration_minutes=30, energy="deep")])
        handoff = _handoff(
            windows=[
                {
                    "start": "2026-10-03T09:00:00+00:00",
                    "end": "2026-10-03T09:30:00+00:00",
                    "duration_minutes": 30,
                    "work_type": "light",
                    "confidence": 0.9,
                    "constraints": [],
                },
            ],
        )
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_conflict.v1")
        self.assertEqual(result["reason"], "capacity_exceeded")


# ---------------------------------------------------------------------------
# 3. Hard appointment overlap → conflict
# ---------------------------------------------------------------------------

class HardAppointmentOverlapTest(unittest.TestCase):
    def test_hard_appointment_overlap_conflict(self):
        plan = _plan(schedule_slots=[
            _outcome(id="o1", duration_minutes=30, is_hard_appointment=True),
            _outcome(id="o2", duration_minutes=30, is_hard_appointment=True),
        ])
        handoff = _handoff(
            recovery_buffer_minutes=0,
            windows=[
                {
                    "start": "2026-10-03T09:00:00+00:00",
                    "end": "2026-10-03T10:00:00+00:00",
                    "duration_minutes": 60,
                    "work_type": "deep",
                    "confidence": 0.9,
                    "constraints": [],
                },
            ],
        )
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_conflict.v1")
        self.assertEqual(result["outcome_id"], "o2")
        self.assertEqual(result["reason"], "overlap")


# ---------------------------------------------------------------------------
# 4. Two selected outcomes can't both fit → one conflict, no silent drop
# ---------------------------------------------------------------------------

class TwoOutcomesOneFitsTest(unittest.TestCase):
    def test_two_outcomes_only_one_fits_no_silent_drop(self):
        plan = _plan(schedule_slots=[
            _outcome(id="o1", duration_minutes=30),
            _outcome(id="o2", duration_minutes=30),
        ])
        handoff = _handoff(
            recovery_buffer_minutes=0,
            windows=[
                {
                    "start": "2026-10-03T09:00:00+00:00",
                    "end": "2026-10-03T09:30:00+00:00",
                    "duration_minutes": 30,
                    "work_type": "deep",
                    "confidence": 0.9,
                    "constraints": [],
                },
            ],
        )
        result = schedule_outcomes(plan, handoff)
        # o1 fits, o2 cannot → conflict for o2, not silent drop
        self.assertEqual(result["schema_version"], "rhythm_schedule_conflict.v1")
        self.assertEqual(result["outcome_id"], "o2")
        # o1 is NOT silently dropped — it's scheduled before this conflict


# ---------------------------------------------------------------------------
# 5. Regression risk 1: Rhythm must not pick a different project/outcome
#    than given (prioritiser regression)
# ---------------------------------------------------------------------------

class PrioritiserRegressionTest(unittest.TestCase):
    def test_rhythm_preserves_outcome_id_and_content(self):
        plan = _plan(schedule_slots=[
            _outcome(
                id="o-specific",
                duration_minutes=30,
                learning_detail={"exact_action": "review CCRN3 chapter 5"},
                priority=5,
            ),
        ])
        handoff = _handoff()
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_outcomes.v1")
        self.assertEqual(len(result["scheduled"]), 1)
        s = result["scheduled"][0]
        self.assertEqual(s["outcome_id"], "o-specific")
        self.assertEqual(s["learning_detail"]["exact_action"], "review CCRN3 chapter 5")
        self.assertEqual(s["priority"], 5)


# ---------------------------------------------------------------------------
# 6. Regression risk 7: context-switch limit from capacity_summary
#    respected without justification otherwise
# ---------------------------------------------------------------------------

class ContextSwitchLimitTest(unittest.TestCase):
    def test_max_major_outcomes_respected(self):
        plan = _plan(schedule_slots=[
            _outcome(id=f"o-{i}", duration_minutes=10) for i in range(4)
        ])
        handoff = _handoff(
            capacity_summary={
                "max_major_outcomes": 2,
                "total_available_minutes": 100,
                "total_committed_minutes": 0,
                "total_recovery_minutes": 0,
                "protected_learning_minutes": 0,
            },
            windows=[
                {
                    "start": "2026-10-03T09:00:00+00:00",
                    "end": "2026-10-03T10:00:00+00:00",
                    "duration_minutes": 60,
                    "work_type": "deep",
                    "confidence": 0.9,
                    "constraints": [],
                },
                {
                    "start": "2026-10-03T10:00:00+00:00",
                    "end": "2026-10-03T11:00:00+00:00",
                    "duration_minutes": 60,
                    "work_type": "deep",
                    "confidence": 0.9,
                    "constraints": [],
                },
            ],
        )
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_conflict.v1")
        self.assertEqual(result["outcome_id"], "o-2")
        self.assertEqual(result["reason"], "capacity_exceeded")


# ---------------------------------------------------------------------------
# 7. resolve_conflict tests
# ---------------------------------------------------------------------------

class ResolveConflictTest(unittest.TestCase):
    def test_split_returns_split_action(self):
        conflict = {"outcome_id": "o1", "possible_alternatives": ["split_task", "defer"]}
        result = resolve_conflict(conflict, "split")
        self.assertEqual(result["action"], "split")
        self.assertEqual(result["outcome_id"], "o1")

    def test_reduce_scope_returns_reduce_scope_action(self):
        conflict = {"outcome_id": "o1", "possible_alternatives": ["reduce_scope"]}
        result = resolve_conflict(conflict, "reduce_scope")
        self.assertEqual(result["action"], "reduce_scope")

    def test_defer_returns_defer_action(self):
        conflict = {"outcome_id": "o1"}
        result = resolve_conflict(conflict, "defer")
        self.assertEqual(result["action"], "defer")

    def test_select_alternative_returns_select_alternative(self):
        conflict = {"outcome_id": "o1", "possible_alternatives": ["defer", "split_task"]}
        result = resolve_conflict(conflict, "select_alternative")
        self.assertEqual(result["action"], "select_alternative")
        self.assertEqual(result["alternative"], "defer")

    def test_invalid_decision_raises(self):
        conflict = {"outcome_id": "o1"}
        with self.assertRaises(ValueError):
            resolve_conflict(conflict, "invalid_decision")


# ---------------------------------------------------------------------------
# 8. Learning detail preserved unchanged
# ---------------------------------------------------------------------------

class LearningDetailPreservedTest(unittest.TestCase):
    def test_exact_learning_detail_unchanged(self):
        detail = {"exact_action": "read CCRN3 section 5.1", "article": "CRRN3 Deep Dive"}
        plan = _plan(schedule_slots=[_outcome(id="o1", learning_detail=detail)])
        handoff = _handoff()
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_outcomes.v1")
        s = result["scheduled"][0]
        self.assertEqual(s["learning_detail"], detail)


# ---------------------------------------------------------------------------
# 9. Valid full schedule
# ---------------------------------------------------------------------------

class ValidScheduleTest(unittest.TestCase):
    def test_two_outcomes_fit_in_windows(self):
        plan = _plan(schedule_slots=[
            _outcome(id="o1", duration_minutes=30),
            _outcome(id="o2", duration_minutes=20),
        ])
        handoff = _handoff(
            recovery_buffer_minutes=0,
            windows=[
                {
                    "start": "2026-10-03T09:00:00+00:00",
                    "end": "2026-10-03T09:50:00+00:00",
                    "duration_minutes": 50,
                    "work_type": "deep",
                    "confidence": 0.9,
                    "constraints": [],
                },
            ],
        )
        result = schedule_outcomes(plan, handoff)
        self.assertEqual(result["schema_version"], "rhythm_schedule_outcomes.v1")
        self.assertEqual(len(result["scheduled"]), 2)


if __name__ == "__main__":
    unittest.main()