# Batch T25 -- Executive Heartbeat
# test_t25_heartbeat.py: QA T25 tests T25-01..T25-08.
# Stdlib only: unittest.  Plain ASCII.  Deterministic.

from __future__ import annotations

import unittest

from tola.heartbeat.policy import (
    IDLE_COST,
    WAKE_COST,
    THRESHOLDS,
)
from tola.heartbeat.heartbeat import (
    HeartbeatResult,
    run_heartbeat,
    idle_cost_within_target,
)


# ===========================================================================
# Fixtures
# ===========================================================================

NOW = "2026-09-29T12:00:00"


def make_condition(
    kind: str,
    cid: str,
    severity: str = "medium",
    material: bool = True,
    age_days: int | None = None,
    **extra: dict,
) -> dict:
    """Build a minimal condition dict for heartbeat sweep."""
    c: dict = {
        "kind": kind,
        "id": cid,
        "severity": severity,
        "material": material,
    }
    if age_days is not None:
        c["age_days"] = age_days
    c.update(extra)
    return c


# ===========================================================================
# T25-01: Nothing material -> no LLM wake
# ===========================================================================

class TestT25_01_NoMaterialNoWake(unittest.TestCase):
    def test_empty_conditions(self):
        result = run_heartbeat([], NOW)
        self.assertFalse(result.wake)
        self.assertEqual(len(result.findings), 0)
        self.assertEqual(result.cost_units, IDLE_COST)

    def test_non_material_conditions(self):
        conds = [
            make_condition("INFO", "i1", severity="low", material=False),
            make_condition("LOG", "l1", severity="low", material=False),
        ]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)
        self.assertEqual(len(result.findings), 0)
        self.assertEqual(result.cost_units, IDLE_COST)

    def test_idle_cost_within_target_on_quiet(self):
        result = run_heartbeat([], NOW)
        self.assertTrue(idle_cost_within_target(result))


# ===========================================================================
# T25-02: Overdue material task -> wake
# ===========================================================================

class TestT25_02_OverdueTaskWake(unittest.TestCase):
    def test_overdue_material_task_wakes(self):
        conds = [make_condition("OVERDUE_TASK", "ot-1", severity="high", age_days=-1)]
        result = run_heartbeat(conds, NOW)
        self.assertTrue(result.wake)
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0]["kind"], "OVERDUE_TASK")
        self.assertGreater(result.cost_units, IDLE_COST)

    def test_overdue_task_cost_is_wake_cost(self):
        conds = [make_condition("OVERDUE_TASK", "ot-1", severity="high", age_days=-1)]
        result = run_heartbeat(conds, NOW)
        self.assertEqual(result.cost_units, WAKE_COST)


# ===========================================================================
# T25-03: Long-standing blocker -> wake
# ===========================================================================

class TestT25_03_LongStandingBlockerWake(unittest.TestCase):
    def test_blocker_older_than_limit_wakes(self):
        # BLOCKER_AGE_LIMIT is 3; 4 days exceeds it
        conds = [make_condition("BLOCKER", "blk-1", severity="high", age_days=4)]
        result = run_heartbeat(conds, NOW)
        self.assertTrue(result.wake)
        self.assertEqual(len(result.findings), 1)

    def test_blocker_at_limit_does_not_wake(self):
        # Exactly at limit (3 days) should not wake
        conds = [make_condition("BLOCKER", "blk-2", severity="high", age_days=3)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)
        self.assertEqual(len(result.findings), 0)

    def test_young_blocker_no_wake(self):
        conds = [make_condition("BLOCKER", "blk-3", severity="high", age_days=1)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)


# ===========================================================================
# T25-04: Approval beyond threshold -> wake
# ===========================================================================

class TestT25_04_ApprovalBeyondThresholdWake(unittest.TestCase):
    def test_approval_older_than_limit_wakes(self):
        # APPROVAL_AGE_LIMIT is 5; 6 days exceeds it
        conds = [make_condition("APPROVAL_PENDING", "apr-1", severity="high", age_days=6)]
        result = run_heartbeat(conds, NOW)
        self.assertTrue(result.wake)
        self.assertEqual(len(result.findings), 1)

    def test_approval_at_limit_no_wake(self):
        conds = [make_condition("APPROVAL_PENDING", "apr-2", severity="high", age_days=5)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)

    def test_approval_young_no_wake(self):
        conds = [make_condition("APPROVAL_PENDING", "apr-3", severity="high", age_days=1)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)


# ===========================================================================
# T25-05: Unreviewed experiment -> wake
# ===========================================================================

class TestT25_05_UnreviewedExperimentWake(unittest.TestCase):
    def test_experiment_older_than_limit_wakes(self):
        # EXPERIMENT_REVIEW_AGE is 7; 8 days exceeds it
        conds = [make_condition("EXPERIMENT_UNREVIEWED", "exp-1", severity="high", age_days=8)]
        result = run_heartbeat(conds, NOW)
        self.assertTrue(result.wake)
        self.assertEqual(len(result.findings), 1)

    def test_experiment_at_limit_no_wake(self):
        conds = [make_condition("EXPERIMENT_UNREVIEWED", "exp-2", severity="high", age_days=7)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)

    def test_recent_experiment_no_wake(self):
        conds = [make_condition("EXPERIMENT_UNREVIEWED", "exp-3", severity="high", age_days=2)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)


# ===========================================================================
# T25-06: Stale PortfolioSnapshot -> refresh action without wake;
#          beyond hard limit -> wake
# ===========================================================================

class TestT25_06_StaleSnapshot(unittest.TestCase):
    def test_snapshot_beyond_max_age_action_only(self):
        # SNAPSHOT_MAX_AGE is 3; 4 days triggers REFRESH_SNAPSHOT, no wake
        conds = [make_condition("SNAPSHOT_STALE", "snap-1", severity="medium", age_days=4)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)
        self.assertIn("REFRESH_SNAPSHOT", result.actions)
        self.assertEqual(result.cost_units, IDLE_COST)

    def test_snapshot_beyond_hard_limit_wakes(self):
        # SNAPSHOT_HARD_LIMIT is 7; 8 days wakes
        conds = [make_condition("SNAPSHOT_STALE", "snap-2", severity="high", age_days=8)]
        result = run_heartbeat(conds, NOW)
        self.assertTrue(result.wake)
        self.assertEqual(len(result.findings), 1)

    def test_snapshot_within_max_age_no_action(self):
        conds = [make_condition("SNAPSHOT_STALE", "snap-3", severity="medium", age_days=2)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(result.wake)
        self.assertEqual(len(result.actions), 0)


# ===========================================================================
# T25-07: Repeated identical unresolved condition does not spam
# ===========================================================================

class TestT25_07_AntiSpam(unittest.TestCase):
    def test_identical_condition_suppressed_on_second_run(self):
        conds = [make_condition("OVERDUE_TASK", "ot-dup", severity="high", age_days=-1)]
        state: dict = {}

        result1 = run_heartbeat(conds, NOW, state=state)
        self.assertTrue(result1.wake)
        self.assertEqual(len(result1.findings), 1)

        # Same conditions, same state -> suppressed
        result2 = run_heartbeat(conds, NOW, state=state)
        self.assertFalse(result2.wake)
        self.assertEqual(len(result2.findings), 0)

    def test_severity_escalation_rewakes(self):
        # First run: medium severity
        conds = [make_condition("BLOCKER", "blk-escalate", severity="medium", age_days=5)]
        state: dict = {}

        result1 = run_heartbeat(conds, NOW, state=state)
        self.assertTrue(result1.wake)

        # Second run: severity escalated to critical (same kind/id, new fingerprint)
        conds2 = [make_condition("BLOCKER", "blk-escalate", severity="critical", age_days=5)]
        result2 = run_heartbeat(conds2, NOW, state=state)
        self.assertTrue(result2.wake)
        self.assertEqual(len(result2.findings), 1)

    def test_new_condition_wakes(self):
        # First run has one condition; second run adds a different one
        state: dict = {}
        conds1 = [make_condition("OVERDUE_TASK", "ot-1", severity="high", age_days=-1)]
        result1 = run_heartbeat(conds1, NOW, state=state)
        self.assertTrue(result1.wake)

        conds2 = [make_condition("OVERDUE_TASK", "ot-2", severity="high", age_days=-1)]
        result2 = run_heartbeat(conds2, NOW, state=state)
        self.assertTrue(result2.wake)
        self.assertEqual(len(result2.findings), 1)


# ===========================================================================
# T25-08: Idle heartbeat cost remains within target
# ===========================================================================

class TestT25_08_IdleCost(unittest.TestCase):
    def test_idle_cost_equals_idle_constant(self):
        result = run_heartbeat([], NOW)
        self.assertEqual(result.cost_units, IDLE_COST)

    def test_idle_cost_within_target(self):
        result = run_heartbeat([], NOW)
        self.assertTrue(idle_cost_within_target(result))

    def test_idle_cost_within_target_on_action_only(self):
        # REFRESH_SNAPSHOT is action-only, should not inflate cost
        conds = [make_condition("SNAPSHOT_STALE", "snap-cost", severity="medium", age_days=4)]
        result = run_heartbeat(conds, NOW)
        self.assertTrue(idle_cost_within_target(result))

    def test_wake_cost_exceeds_idle_target(self):
        conds = [make_condition("OVERDUE_TASK", "ot-cost", severity="high", age_days=-1)]
        result = run_heartbeat(conds, NOW)
        self.assertFalse(idle_cost_within_target(result))


# ===========================================================================
# Determinism
# ===========================================================================

class TestT25_Determinism(unittest.TestCase):
    def test_deterministic_across_runs(self):
        conds = [
            make_condition("OVERDUE_TASK", "ot-det", severity="high", age_days=-1),
            make_condition("BLOCKER", "blk-det", severity="medium", age_days=1),
        ]
        r1 = run_heartbeat(conds, NOW)
        r2 = run_heartbeat(conds, NOW)
        self.assertEqual(r1.wake, r2.wake)
        self.assertEqual(len(r1.findings), len(r2.findings))
        self.assertEqual(r1.cost_units, r2.cost_units)

    def test_no_clock_reads(self):
        # Verify run_heartbeat does not read the clock; it only uses now_iso input.
        # Passing a fixed now_iso always yields the same result.
        conds = [make_condition("OVERDUE_TASK", "ot-clock", severity="high", age_days=-1)]
        r1 = run_heartbeat(conds, "2026-01-01T00:00:00")
        r2 = run_heartbeat(conds, "2026-06-15T00:00:00")
        # Age is supplied directly; now_iso is not used for age computation.
        self.assertEqual(r1.wake, r2.wake)
        self.assertEqual(len(r1.findings), len(r2.findings))
