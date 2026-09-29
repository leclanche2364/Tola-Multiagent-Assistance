# Batch T26 -- Daily Executive Reconciliation
# test_t26_reconciliation.py: QA T26 tests T26-01..T26-07.
# Stdlib only: unittest.  Plain ASCII.  Deterministic.

from __future__ import annotations

import unittest
from datetime import date, timedelta

from tola.reconciliation.snapshot import (
    MAX_SOURCE_AGE,
    STALE_SOURCE,
    DISCREPANCY,
    reconcile_snapshot,
    SnapshotReport,
)
from tola.reconciliation.cycle import (
    run_daily_cycle,
    DailyReconciliationResult,
)


# ===========================================================================
# Fixtures
# ===========================================================================

REF_DATE = "2026-09-29"
REF_DT = date(2026, 9, 29)


def make_task(
    tid: str,
    status: str = "active",
    label: str = "",
    due_date: str = "",
) -> dict:
    return {
        "id": tid,
        "status": status,
        "label": label,
        "due_date": due_date,
    }


def make_risk(
    rid: str,
    status: str = "new",
    label: str = "",
) -> dict:
    return {
        "id": rid,
        "status": status,
        "label": label,
    }


def make_decision(
    did: str,
    due_date: str = "",
    label: str = "",
) -> dict:
    return {
        "id": did,
        "due_date": due_date,
        "label": label,
    }


def make_source(name: str, fetched_at: str) -> dict:
    return {"name": name, "fetched_at": fetched_at}


def make_current_snapshot(
    tasks: list[dict] | None = None,
    risks: list[dict] | None = None,
    decisions: list[dict] | None = None,
    approvals: list[dict] | None = None,
    deadlines: list[dict] | None = None,
    metrics: list[dict] | None = None,
    capacity: dict | None = None,
    sources: list[dict] | None = None,
) -> dict:
    snap: dict = {
        "active_tasks": tasks or [],
        "risks": risks or [],
        "pending_decisions": decisions or [],
        "pending_approvals": approvals or [],
        "deadlines": deadlines or [],
        "material_metrics": metrics or [],
        "capacity_summary": capacity or {},
    }
    if sources is not None:
        snap["_sources"] = sources
    return snap


def make_state(
    previous: dict | None = None,
    current: dict | None = None,
    last_seen: dict | None = None,
    processed_events: set | None = None,
    reference_date: str = REF_DATE,
) -> dict:
    return {
        "previous_snapshot": previous or {},
        "current_snapshot": current or make_current_snapshot(),
        "last_seen": last_seen or {},
        "processed_events": processed_events or set(),
        "reference_date": reference_date,
    }


# ===========================================================================
# T26-01: No material change -> silent
# ===========================================================================

class TestT26_01_SilentWhenNothingChanged(unittest.TestCase):
    def test_no_change_no_messages(self):
        prev = make_current_snapshot(
            tasks=[make_task("t1", "active")],
        )
        cur = make_current_snapshot(
            tasks=[make_task("t1", "active")],
        )
        state = make_state(previous=prev, current=cur)
        result = run_daily_cycle(state, REF_DATE)
        self.assertTrue(result.silent)
        self.assertEqual(len(result.messages), 0)
        self.assertEqual(len(result.actions), 0)

    def test_empty_snapshots_silent(self):
        state = make_state(
            previous={},
            current={},
        )
        result = run_daily_cycle(state, REF_DATE)
        self.assertTrue(result.silent)
        self.assertEqual(len(result.messages), 0)


# ===========================================================================
# T26-02: New risk -> appropriate action
# ===========================================================================

class TestT26_02_NewRiskAction(unittest.TestCase):
    def test_new_risk_surfaced(self):
        cur = make_current_snapshot(
            risks=[make_risk("r1", "new", "Server down")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        self.assertFalse(result.silent)
        risk_actions = [a for a in result.actions if a["action"] == "RISK_ACTION"]
        self.assertEqual(len(risk_actions), 1)
        self.assertEqual(risk_actions[0]["id"], "r1")

    def test_open_risk_surfaced(self):
        cur = make_current_snapshot(
            risks=[make_risk("r2", "open", "Budget overrun")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        risk_actions = [a for a in result.actions if a["action"] == "RISK_ACTION"]
        self.assertEqual(len(risk_actions), 1)

    def test_escalated_risk_surfaced(self):
        cur = make_current_snapshot(
            risks=[make_risk("r3", "escalated", "Security breach")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        risk_actions = [a for a in result.actions if a["action"] == "RISK_ACTION"]
        self.assertEqual(len(risk_actions), 1)

    def test_closed_risk_not_surfaced(self):
        cur = make_current_snapshot(
            risks=[make_risk("r4", "closed", "Fixed")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        risk_actions = [a for a in result.actions if a["action"] == "RISK_ACTION"]
        self.assertEqual(len(risk_actions), 0)


# ===========================================================================
# T26-03: Missed event -> discrepancy found
# ===========================================================================

class TestT26_03_MissedEventDiscrepancy(unittest.TestCase):
    def test_status_changed_without_processed_event(self):
        # last_seen says t1 is "active", but current says "done".
        # No processed_event covers this change.
        cur = make_current_snapshot(
            tasks=[make_task("t1", "done")],
        )
        state = make_state(
            current=cur,
            last_seen={"t1": "active"},
            processed_events=set(),
        )
        result = run_daily_cycle(state, REF_DATE)
        disc_actions = [a for a in result.actions if a["action"] == DISCREPANCY]
        self.assertEqual(len(disc_actions), 1)
        self.assertEqual(disc_actions[0]["id"], "t1")
        self.assertEqual(disc_actions[0]["last_seen"], "active")
        self.assertEqual(disc_actions[0]["current"], "done")

    def test_status_changed_with_processed_event_no_disc(self):
        # last_seen says t1 is "active", current says "done".
        # But a processed event covers this change.
        cur = make_current_snapshot(
            tasks=[make_task("t1", "done")],
        )
        state = make_state(
            current=cur,
            last_seen={"t1": "active"},
            processed_events={"t1:done"},
        )
        result = run_daily_cycle(state, REF_DATE)
        disc_actions = [a for a in result.actions if a["action"] == DISCREPANCY]
        self.assertEqual(len(disc_actions), 0)

    def test_no_change_no_discrepancy(self):
        cur = make_current_snapshot(
            tasks=[make_task("t1", "active")],
        )
        state = make_state(
            current=cur,
            last_seen={"t1": "active"},
            processed_events=set(),
        )
        result = run_daily_cycle(state, REF_DATE)
        disc_actions = [a for a in result.actions if a["action"] == DISCREPANCY]
        self.assertEqual(len(disc_actions), 0)

    def test_new_entity_not_in_last_seen_no_disc(self):
        # Entity not in last_seen is new, not a discrepancy.
        cur = make_current_snapshot(
            tasks=[make_task("t1", "active")],
        )
        state = make_state(
            current=cur,
            last_seen={},
            processed_events=set(),
        )
        result = run_daily_cycle(state, REF_DATE)
        disc_actions = [a for a in result.actions if a["action"] == DISCREPANCY]
        self.assertEqual(len(disc_actions), 0)


# ===========================================================================
# T26-04: Stalled task -> follow-up
# ===========================================================================

class TestT26_04_StalledTaskFollowUp(unittest.TestCase):
    def test_stalled_task_follow_up(self):
        cur = make_current_snapshot(
            tasks=[make_task("t1", "stalled", "Write report")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        fu_actions = [a for a in result.actions if a["action"] == "FOLLOW_UP"]
        self.assertEqual(len(fu_actions), 1)
        self.assertEqual(fu_actions[0]["id"], "t1")

    def test_blocked_task_follow_up(self):
        cur = make_current_snapshot(
            tasks=[make_task("t2", "blocked", "Await review")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        fu_actions = [a for a in result.actions if a["action"] == "FOLLOW_UP"]
        self.assertEqual(len(fu_actions), 1)

    def test_active_task_no_follow_up(self):
        cur = make_current_snapshot(
            tasks=[make_task("t3", "active", "Normal work")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        fu_actions = [a for a in result.actions if a["action"] == "FOLLOW_UP"]
        self.assertEqual(len(fu_actions), 0)

    def test_multiple_stalled_sorted_by_id(self):
        cur = make_current_snapshot(
            tasks=[
                make_task("t2", "stalled", "Task B"),
                make_task("t1", "stalled", "Task A"),
            ],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        fu_actions = [a for a in result.actions if a["action"] == "FOLLOW_UP"]
        self.assertEqual(len(fu_actions), 2)
        self.assertEqual(fu_actions[0]["id"], "t1")
        self.assertEqual(fu_actions[1]["id"], "t2")


# ===========================================================================
# T26-05: Decision due -> surfaced
# ===========================================================================

class TestT26_05_DecisionDueSurfaced(unittest.TestCase):
    def test_decision_due_today(self):
        cur = make_current_snapshot(
            decisions=[make_decision("d1", REF_DATE, "Approve budget")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        dec_actions = [a for a in result.actions if a["action"] == "SURFACE_DECISION"]
        self.assertEqual(len(dec_actions), 1)
        self.assertEqual(dec_actions[0]["id"], "d1")

    def test_decision_overdue(self):
        cur = make_current_snapshot(
            decisions=[make_decision("d2", "2026-09-28", "Approve hire")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        dec_actions = [a for a in result.actions if a["action"] == "SURFACE_DECISION"]
        self.assertEqual(len(dec_actions), 1)

    def test_decision_future_not_surfaced(self):
        cur = make_current_snapshot(
            decisions=[make_decision("d3", "2026-10-05", "Future decision")],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        dec_actions = [a for a in result.actions if a["action"] == "SURFACE_DECISION"]
        self.assertEqual(len(dec_actions), 0)

    def test_approval_due_surfaced(self):
        cur = make_current_snapshot(
            approvals=[{"id": "a1", "due_date": REF_DATE, "label": "Sign off"}],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        dec_actions = [a for a in result.actions if a["action"] == "SURFACE_DECISION"]
        self.assertEqual(len(dec_actions), 1)
        self.assertEqual(dec_actions[0]["id"], "a1")

    def test_decisions_sorted_by_due_then_id(self):
        cur = make_current_snapshot(
            decisions=[
                make_decision("d2", REF_DATE, "B"),
                make_decision("d1", REF_DATE, "A"),
            ],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        dec_actions = [a for a in result.actions if a["action"] == "SURFACE_DECISION"]
        self.assertEqual(len(dec_actions), 2)
        self.assertEqual(dec_actions[0]["id"], "d1")
        self.assertEqual(dec_actions[1]["id"], "d2")


# ===========================================================================
# T26-06: Material specialist result -> review action
# ===========================================================================

class TestT26_06_MaterialSpecialistReview(unittest.TestCase):
    def test_needs_review_metric_surfaced(self):
        cur = make_current_snapshot(
            metrics=[
                {"id": "m1", "status": "needs_review", "label": "Revenue data"}
            ],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        rev_actions = [a for a in result.actions if a["action"] == "REVIEW_MATERIAL_OUTPUT"]
        self.assertEqual(len(rev_actions), 1)
        self.assertEqual(rev_actions[0]["id"], "m1")

    def test_ok_metric_not_surfaced(self):
        cur = make_current_snapshot(
            metrics=[
                {"id": "m2", "status": "ok", "label": "Happy path"}
            ],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        rev_actions = [a for a in result.actions if a["action"] == "REVIEW_MATERIAL_OUTPUT"]
        self.assertEqual(len(rev_actions), 0)


# ===========================================================================
# T26-07: Snapshot source freshness checked
# ===========================================================================

class TestT26_07_SourceFreshness(unittest.TestCase):
    def test_stale_source_action_and_flag(self):
        stale_day = (REF_DT - timedelta(days=MAX_SOURCE_AGE + 1)).isoformat()
        cur = make_current_snapshot(
            sources=[make_source("blackboard", stale_day)],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        self.assertFalse(result.silent)
        stale_actions = [
            a for a in result.actions if a["action"] == STALE_SOURCE
        ]
        self.assertEqual(len(stale_actions), 1)
        self.assertEqual(stale_actions[0]["source"], "blackboard")

    def test_fresh_source_no_stale_action(self):
        fresh_day = REF_DATE
        cur = make_current_snapshot(
            sources=[make_source("blackboard", fresh_day)],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        stale_actions = [
            a for a in result.actions if a["action"] == STALE_SOURCE
        ]
        self.assertEqual(len(stale_actions), 0)

    def test_missing_fetched_at_marks_stale(self):
        cur = make_current_snapshot(
            sources=[{"name": "rhythm", "fetched_at": ""}],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        stale_actions = [
            a for a in result.actions if a["action"] == STALE_SOURCE
        ]
        self.assertEqual(len(stale_actions), 1)

    def test_multiple_sources_one_stale(self):
        stale_day = (REF_DT - timedelta(days=MAX_SOURCE_AGE + 1)).isoformat()
        cur = make_current_snapshot(
            sources=[
                make_source("blackboard", REF_DATE),
                make_source("rhythm", stale_day),
            ],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        stale_actions = [
            a for a in result.actions if a["action"] == STALE_SOURCE
        ]
        self.assertEqual(len(stale_actions), 1)
        self.assertEqual(stale_actions[0]["source"], "rhythm")


# ===========================================================================
# Determinism tests
# ===========================================================================

class TestT26_Determinism(unittest.TestCase):
    def test_deterministic_ordering(self):
        cur = make_current_snapshot(
            tasks=[
                make_task("t3", "stalled", "C"),
                make_task("t1", "stalled", "A"),
                make_task("t2", "stalled", "B"),
            ],
            risks=[
                make_risk("r2", "new", "Risk B"),
                make_risk("r1", "new", "Risk A"),
            ],
        )
        state = make_state(current=cur)
        result = run_daily_cycle(state, REF_DATE)
        # Follow-ups sorted by id
        fu = [a for a in result.actions if a["action"] == "FOLLOW_UP"]
        self.assertEqual([a["id"] for a in fu], ["t1", "t2", "t3"])
        # Risks sorted by id
        ra = [a for a in result.actions if a["action"] == "RISK_ACTION"]
        self.assertEqual([a["id"] for a in ra], ["r1", "r2"])

    def test_repeated_runs_produce_same_result(self):
        cur = make_current_snapshot(
            tasks=[make_task("t1", "stalled")],
            risks=[make_risk("r1", "new")],
        )
        state = make_state(current=cur)
        r1 = run_daily_cycle(state, REF_DATE)
        r2 = run_daily_cycle(state, REF_DATE)
        self.assertEqual(len(r1.actions), len(r2.actions))
        self.assertEqual(r1.actions, r2.actions)


# ===========================================================================
# Snapshot-level tests
# ===========================================================================

class TestT26_SnapshotReconcile(unittest.TestCase):
    def test_snapshot_report_changed(self):
        prev = make_current_snapshot(tasks=[make_task("t1", "active")])
        cur = make_current_snapshot(tasks=[make_task("t1", "done")])
        report = reconcile_snapshot(prev, cur, reference_date=REF_DT)
        self.assertTrue(report.changed)
        self.assertTrue(report.sources_fresh)

    def test_snapshot_report_unchanged(self):
        prev = make_current_snapshot(tasks=[make_task("t1", "active")])
        cur = make_current_snapshot(tasks=[make_task("t1", "active")])
        report = reconcile_snapshot(prev, cur, reference_date=REF_DT)
        self.assertFalse(report.changed)

    def test_snapshot_deltas_deterministic(self):
        prev = make_current_snapshot(
            tasks=[make_task("t1", "active", due_date="2026-09-28")],
        )
        cur = make_current_snapshot(
            tasks=[make_task("t1", "done", due_date="2026-09-28")],
        )
        report = reconcile_snapshot(prev, cur, reference_date=REF_DT)
        self.assertTrue(report.changed)
        # Delta should have id=t1, field=status
        status_deltas = [d for d in report.deltas if d["field"] == "status"]
        self.assertEqual(len(status_deltas), 1)
        self.assertEqual(status_deltas[0]["before"], "active")
        self.assertEqual(status_deltas[0]["after"], "done")

    def test_stale_source_marks_sources_fresh_false(self):
        stale_day = (REF_DT - timedelta(days=MAX_SOURCE_AGE + 1)).isoformat()
        prev = make_current_snapshot()
        cur = make_current_snapshot(
            sources=[make_source("blackboard", stale_day)],
        )
        report = reconcile_snapshot(prev, cur, reference_date=REF_DT)
        self.assertFalse(report.sources_fresh)
        self.assertTrue(report.changed)

    def test_stale_source_action_in_deltas(self):
        stale_day = (REF_DT - timedelta(days=MAX_SOURCE_AGE + 1)).isoformat()
        prev = make_current_snapshot()
        cur = make_current_snapshot(
            sources=[make_source("blackboard", stale_day)],
        )
        report = reconcile_snapshot(prev, cur, reference_date=REF_DT)
        stale_deltas = [
            d for d in report.deltas if d.get("action") == STALE_SOURCE
        ]
        self.assertEqual(len(stale_deltas), 1)

    def test_no_sources_no_freshness_issue(self):
        prev = make_current_snapshot()
        cur = make_current_snapshot()
        report = reconcile_snapshot(prev, cur, reference_date=REF_DT)
        self.assertTrue(report.sources_fresh)


if __name__ == "__main__":
    unittest.main()