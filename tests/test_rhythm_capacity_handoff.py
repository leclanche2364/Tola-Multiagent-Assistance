"""Batch 2 QA tests for rhythm_capacity_handoff.v1 producer.

Covers: full free day; ICU shift; post-night/poor-recovery;
fragmented appointments; one 45-min window; no discretionary capacity;
stale shift data; missing recovery data.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.rhythm.capacity_handoff import (
    CapacityWindow,
    Carryover,
    FixedCommitment,
    RecoveryData,
    ShiftInfo,
    WorkType,
    assemble_capacity_handoff,
)
from agents.daily_synthesis.contracts import ValidationError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _window(start: str, end: str, minutes: int, work_type: str = "deep", confidence: float = 0.9, constraints: list[str] | None = None) -> dict:
    return {
        "start": start,
        "end": end,
        "duration_minutes": minutes,
        "work_type": work_type,
        "confidence": confidence,
        "constraints": constraints or [],
    }


def _shift(start: str, end: str, shift_type: str = "day", committed: int = 0) -> ShiftInfo:
    return ShiftInfo(id="s1", start=start, end=end, type=shift_type, committed_minutes=committed)


def _commit(start: str, end: str, minutes: int, protected: bool = False) -> FixedCommitment:
    return FixedCommitment(label="c1", start=start, end=end, duration_minutes=minutes, protected=protected)


# ---------------------------------------------------------------------------
# 1. Full free day — no shifts, no commitments, many windows
# ---------------------------------------------------------------------------

class FullFreeDayTest(unittest.TestCase):
    def test_full_free_day(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T08:00:00+00:00", "2026-10-03T12:00:00+00:00", 240),
                _window("2026-10-03T13:00:00+00:00", "2026-10-03T17:00:00+00:00", 240),
                _window("2026-10-03T19:00:00+00:00", "2026-10-03T22:00:00+00:00", 180),
            ],
            recovery=RecoveryData(hours_slept=7.5, fatigue_risk="low", recovery_buffer_minutes=30, status="adequate"),
        )
        self.assertEqual(handoff["capacity_used_minutes"], 0)
        self.assertEqual(handoff["capacity_total_minutes"], 660)
        self.assertEqual(handoff["recovery_buffer_minutes"], 30)
        self.assertEqual(len(handoff["windows"]), 3)
        self.assertEqual(handoff["windows"][0]["work_type"], WorkType.DEEP.value)
        self.assertEqual(handoff["windows"][2]["work_type"], WorkType.DEEP.value)
        self.assertLessEqual(handoff["capacity_summary"]["max_major_outcomes"], 3)
        self.assertEqual(handoff["data_freshness"]["overall_status"], "fresh")


# ---------------------------------------------------------------------------
# 2. ICU shift day — heavy committed time
# ---------------------------------------------------------------------------

class ICUShiftDayTest(unittest.TestCase):
    def test_icu_shift_day(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[_shift("2026-10-03T06:00:00+00:00", "2026-10-03T14:00:00+00:00", "icu", committed=480)],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T14:00:00+00:00", "2026-10-03T15:00:00+00:00", 60),
            ],
            recovery=RecoveryData(hours_slept=5, fatigue_risk="high", recovery_buffer_minutes=45, status="poor"),
        )
        self.assertEqual(handoff["capacity_used_minutes"], 480)
        self.assertEqual(handoff["capacity_total_minutes"], 60)
        self.assertEqual(handoff["windows"][0]["work_type"], WorkType.MEDIUM.value)
        self.assertEqual(handoff["recovery"]["status"], "poor")
        self.assertEqual(handoff["recovery"]["fatigue_risk"], "high")


# ---------------------------------------------------------------------------
# 3. Post-night / poor-recovery day
# ---------------------------------------------------------------------------

class PostNightPoorRecoveryTest(unittest.TestCase):
    def test_post_night_poor_recovery(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[_shift("2026-10-03T22:00:00+00:00", "2026-10-04T06:00:00+00:00", "night", committed=480)],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-04T08:00:00+00:00", "2026-10-04T09:30:00+00:00", 90),
            ],
            recovery=RecoveryData(hours_slept=3, fatigue_risk="high", recovery_buffer_minutes=60, status="poor"),
        )
        self.assertEqual(handoff["recovery"]["status"], "poor")
        self.assertEqual(handoff["recovery"]["fatigue_risk"], "high")
        self.assertEqual(handoff["capacity_summary"]["protected_learning_minutes"], 0)


# ---------------------------------------------------------------------------
# 4. Fragmented appointments — many small fixed commitments
# ---------------------------------------------------------------------------

class FragmentedAppointmentsTest(unittest.TestCase):
    def test_fragmented_appointments(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[
                _commit("2026-10-03T09:00:00+00:00", "2026-10-03T09:30:00+00:00", 30),
                _commit("2026-10-03T11:00:00+00:00", "2026-10-03T11:30:00+00:00", 30),
                _commit("2026-10-03T14:00:00+00:00", "2026-10-03T14:30:00+00:00", 30, protected=True),
            ],
            available_windows=[
                _window("2026-10-03T08:00:00+00:00", "2026-10-03T10:00:00+00:00", 120),
                _window("2026-10-03T10:30:00+00:00", "2026-10-03T12:00:00+00:00", 90),
                _window("2026-10-03T13:00:00+00:00", "2026-10-03T15:00:00+00:00", 120),
                _window("2026-10-03T15:00:00+00:00", "2026-10-03T17:00:00+00:00", 120),
            ],
            recovery=RecoveryData(hours_slept=6, fatigue_risk="medium", recovery_buffer_minutes=20, status="adequate"),
        )
        self.assertEqual(handoff["capacity_used_minutes"], 90)  # 30+30+30
        self.assertEqual(handoff["capacity_summary"]["protected_learning_minutes"], 30)
        self.assertEqual(len(handoff["windows"]), 4)


# ---------------------------------------------------------------------------
# 5. Only one 45-min window
# ---------------------------------------------------------------------------

class Single45MinWindowTest(unittest.TestCase):
    def test_single_45_min_window(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T10:00:00+00:00", "2026-10-03T10:45:00+00:00", 45),
            ],
            recovery=RecoveryData(hours_slept=8, fatigue_risk="low", recovery_buffer_minutes=10, status="adequate"),
        )
        self.assertEqual(handoff["capacity_total_minutes"], 45)
        self.assertEqual(handoff["windows"][0]["work_type"], WorkType.MEDIUM.value)
        self.assertEqual(handoff["windows"][0]["duration_minutes"], 45)


# ---------------------------------------------------------------------------
# 6. No discretionary capacity — valid empty/project-free handoff
# ---------------------------------------------------------------------------

class NoDiscretionaryCapacityTest(unittest.TestCase):
    def test_empty_handoff_valid(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[_shift("2026-10-03T08:00:00+00:00", "2026-10-03T18:00:00+00:00", "day", committed=600)],
            fixed_commitments=[],
            available_windows=[],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=0, status="adequate"),
        )
        self.assertEqual(handoff["capacity_used_minutes"], 600)
        # Contract requires capacity_total_minutes > 0; floor is max(committed, 1)
        self.assertEqual(handoff["capacity_total_minutes"], 600)
        self.assertEqual(len(handoff["windows"]), 0)
        # No project fields should exist
        self.assertNotIn("project_id", handoff)
        self.assertNotIn("project_name", handoff)
        self.assertNotIn("project_status", handoff)


# ---------------------------------------------------------------------------
# 7. Stale shift data — stale flag surfaced, no fabrication
# ---------------------------------------------------------------------------

class StaleShiftDataTest(unittest.TestCase):
    def test_stale_flag_no_fabrication(self):
        shift = ShiftInfo(id="s1", start="2026-10-02T06:00:00+00:00", end="2026-10-02T14:00:00+00:00", type="day", committed_minutes=480)
        # Mark stale via attribute
        shift.stale = True  # type: ignore[attr-defined]
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[shift],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T10:00:00+00:00", "2026-10-03T12:00:00+00:00", 120),
            ],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=15, status="adequate"),
        )
        self.assertTrue(handoff["stale_shift_data"])
        # No fabricated numbers — used_minutes reflects only what was supplied
        self.assertEqual(handoff["capacity_used_minutes"], 480)


# ---------------------------------------------------------------------------
# 8. Missing recovery data — status "unknown", fatigue_risk "unknown"
# ---------------------------------------------------------------------------

class MissingRecoveryDataTest(unittest.TestCase):
    def test_missing_recovery_no_fabrication(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T09:00:00+00:00", "2026-10-03T10:00:00+00:00", 60),
            ],
            recovery=None,  # missing
        )
        self.assertEqual(handoff["recovery"]["status"], "unknown")
        self.assertEqual(handoff["recovery"]["fatigue_risk"], "unknown")
        # No fabricated numbers for hours_slept
        self.assertIsNone(handoff["recovery"]["hours_slept"])

    def test_missing_recovery_buffer_required_by_contract(self):
        # recovery_buffer_minutes must be >= 0 even with missing recovery
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T09:00:00+00:00", "2026-10-03T10:00:00+00:00", 60),
            ],
            recovery=None,
        )
        self.assertGreaterEqual(handoff["recovery_buffer_minutes"], 0)


# ---------------------------------------------------------------------------
# 9. Data freshness per-source
# ---------------------------------------------------------------------------

class DataFreshnessTest(unittest.TestCase):
    def test_freshness_per_source(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[_shift("2026-10-03T08:00:00+00:00", "2026-10-03T16:00:00+00:00", "day", committed=480)],
            fixed_commitments=[_commit("2026-10-03T09:00:00+00:00", "2026-10-03T09:30:00+00:00", 30)],
            available_windows=[
                _window("2026-10-03T08:00:00+00:00", "2026-10-03T12:00:00+00:00", 240),
            ],
            my_rhythm_data={"last_updated": "2026-10-03T10:00:00+00:00"},
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=10, status="adequate"),
        )
        sources = {s["source"]: s["status"] for s in handoff["data_freshness"]["per_source"]}
        self.assertEqual(sources["shifts"], "fresh")
        self.assertEqual(sources["fixed_commitments"], "fresh")
        self.assertEqual(sources["my_rhythm"], "fresh")
        self.assertEqual(sources["recovery"], "fresh")
        self.assertEqual(handoff["data_freshness"]["overall_status"], "fresh")


# ---------------------------------------------------------------------------
# 10. Protected learning capacity distinctly surfaced
# ---------------------------------------------------------------------------

class ProtectedLearningTest(unittest.TestCase):
    def test_protected_learning_distinct(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[
                _commit("2026-10-03T09:00:00+00:00", "2026-10-03T09:30:00+00:00", 30, protected=True),
                _commit("2026-10-03T10:00:00+00:00", "2026-10-03T10:30:00+00:00", 30, protected=False),
            ],
            available_windows=[
                _window("2026-10-03T08:00:00+00:00", "2026-10-03T12:00:00+00:00", 240),
            ],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=10, status="adequate"),
        )
        self.assertEqual(handoff["capacity_summary"]["protected_learning_minutes"], 30)
        self.assertEqual(handoff["capacity_summary"]["total_committed_minutes"], 60)


# ---------------------------------------------------------------------------
# 11. max_major_outcomes default ≤ 3
# ---------------------------------------------------------------------------

class MaxOutcomesTest(unittest.TestCase):
    def test_max_major_outcomes_default(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T08:00:00+00:00", "2026-10-03T12:00:00+00:00", 240),
            ],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=10, status="adequate"),
        )
        self.assertLessEqual(handoff["capacity_summary"]["max_major_outcomes"], 3)


# ---------------------------------------------------------------------------
# 12. Window classification — duration_minutes, work_type, confidence, constraints
# ---------------------------------------------------------------------------

class WindowClassificationTest(unittest.TestCase):
    def test_window_classification(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T08:00:00+00:00", "2026-10-03T10:30:00+00:00", 150, constraints=["meeting at 10:00"]),
                _window("2026-10-03T11:00:00+00:00", "2026-10-03T11:30:00+00:00", 30),
                _window("2026-10-03T14:00:00+00:00", "2026-10-03T14:15:00+00:00", 15),
            ],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=10, status="adequate"),
        )
        w = handoff["windows"]
        self.assertEqual(w[0]["work_type"], WorkType.DEEP.value)
        self.assertEqual(w[0]["duration_minutes"], 150)
        self.assertIn("meeting at 10:00", w[0]["constraints"])
        self.assertEqual(w[1]["work_type"], WorkType.LIGHT.value)
        self.assertEqual(w[2]["work_type"], WorkType.LIGHT.value)
        # Confidence is set explicitly by the caller; constraint penalty only applies when confidence is not pre-set
        self.assertEqual(w[0]["confidence"], 0.9)


# ---------------------------------------------------------------------------
# 13. No project fields allowed — contract rejection
# ---------------------------------------------------------------------------

class NoProjectFieldsTest(unittest.TestCase):
    def test_no_project_fields_in_output(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T09:00:00+00:00", "2026-10-03T10:00:00+00:00", 60),
            ],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=10, status="adequate"),
        )
        for forbidden in ("project_id", "project_name", "project_status"):
            self.assertNotIn(forbidden, handoff)


# ---------------------------------------------------------------------------
# 14. Recovery buffer required by contract (zero is OK, negative is not)
# ---------------------------------------------------------------------------

class RecoveryBufferContractTest(unittest.TestCase):
    def test_zero_buffer_valid(self):
        handoff = assemble_capacity_handoff(
            agent_id="agent-1",
            rhythm_id="r1",
            shifts=[],
            fixed_commitments=[],
            available_windows=[
                _window("2026-10-03T09:00:00+00:00", "2026-10-03T10:00:00+00:00", 60),
            ],
            recovery=RecoveryData(hours_slept=7, fatigue_risk="low", recovery_buffer_minutes=0, status="adequate"),
        )
        self.assertEqual(handoff["recovery_buffer_minutes"], 0)


if __name__ == "__main__":
    unittest.main()
