"""QA T2 tests -- PortfolioSnapshot Builder.

Covers T2-01..T2-07 as defined in tola_testing_plan_v1_1.md.
Stdlib only: unittest, datetime, dataclasses.  Plain ASCII.
"""

from __future__ import annotations

import datetime
import unittest

from tola.portfolio.contracts import (
    Approval,
    Commitment,
    Deadline,
    Experiment,
    Goal,
    Metric,
    Project,
    Risk,
    Task,
)
from tola.portfolio.snapshot import (
    PortfolioSnapshot,
    portfolio_snapshot_build,
    portfolio_snapshot_diff,
    portfolio_snapshot_get,
    portfolio_snapshot_refresh,
    portfolio_snapshot_validate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_TIME = datetime.datetime(2026, 9, 29, 12, 0, 0)


def make_project(**overrides) -> Project:
    defaults = dict(
        project_id="proj-001",
        project_name="Alpha",
        source_system="blackboard",
        source_id="proj-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Project(**defaults)


def make_goal(**overrides) -> Goal:
    defaults = dict(
        goal_id="goal-001",
        project_id="proj-001",
        goal_name="Launch",
        source_system="blackboard",
        source_id="goal-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Goal(**defaults)


def make_task(**overrides) -> Task:
    defaults = dict(
        task_id="task-001",
        idempotency_key="idk-001",
        title="Write report",
        source_system="blackboard",
        source_id="task-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Task(**defaults)


def make_deadline(**overrides) -> Deadline:
    defaults = dict(
        deadline_id="dl-001",
        entity_type="task",
        entity_id="task-001",
        due_date="2026-10-01",
        source_system="blackboard",
        source_id="dl-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Deadline(**defaults)


def make_risk(**overrides) -> Risk:
    defaults = dict(
        risk_id="risk-001",
        entity_type="project",
        entity_id="proj-001",
        title="Scope creep",
        source_system="blackboard",
        source_id="risk-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Risk(**defaults)


def make_approval(**overrides) -> Approval:
    defaults = dict(
        approval_id="app-001",
        requested_by="tola",
        approval_type="scope",
        source_system="blackboard",
        source_id="app-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Approval(**defaults)


def make_experiment(**overrides) -> Experiment:
    defaults = dict(
        experiment_id="exp-001",
        title="Dark mode",
        source_system="local_doc",
        source_id="exp-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Experiment(**defaults)


def make_metric(**overrides) -> Metric:
    defaults = dict(
        metric_id="met-001",
        metric_name="conversion_rate",
        metric_value=0.42,
        source_system="local_doc",
        source_id="met-src-001",
        fetched_at=FIXTURE_TIME,
        source_version="v1.0",
    )
    defaults.update(overrides)
    return Metric(**defaults)


def build_sources(**extra) -> dict:
    """Return a standard source dict for snapshot building."""
    sources = {
        "blackboard": [
            make_project(),
            make_goal(),
            make_task(),
            make_deadline(),
            make_risk(),
            make_approval(status="pending"),
        ],
        "local_doc": [
            make_experiment(),
            make_metric(),
        ],
    }
    sources.update(extra)
    return sources


# ===========================================================================
# T2-01: Full fixture snapshot contains all required entities.
# ===========================================================================

class TestT2_01_AllEntitiesPresent(unittest.TestCase):
    def test_snapshot_contains_all_sections(self):
        snap = portfolio_snapshot_build(build_sources())
        self.assertTrue(len(snap.projects) > 0)
        self.assertTrue(len(snap.active_goals) > 0)
        self.assertTrue(len(snap.deadlines) > 0)
        self.assertTrue(len(snap.risks) > 0)
        self.assertTrue(len(snap.pending_approvals) > 0)
        self.assertTrue(len(snap.experiments) > 0)
        self.assertTrue(len(snap.material_metrics) > 0)
        self.assertTrue(len(snap.active_tasks) > 0)

    def test_snapshot_has_required_fields(self):
        snap = portfolio_snapshot_build(build_sources())
        self.assertEqual(snap.snapshot_version, "1.0")
        self.assertTrue(len(snap.generated_at) > 0)
        self.assertIsInstance(snap.source_versions, dict)
        self.assertIsInstance(snap.capacity_summary, dict)
        self.assertIsInstance(snap.current_priorities, list)
        self.assertIsInstance(snap.commitments, list)
        self.assertIsInstance(snap.blocked_tasks, list)
        self.assertIsInstance(snap.agent_state, dict)
        self.assertIsInstance(snap.recent_outcomes, list)
        self.assertIsInstance(snap.stalled_work, list)

    def test_snapshot_has_confidence_and_warnings(self):
        snap = portfolio_snapshot_build(build_sources())
        self.assertIsInstance(snap.confidence, float)
        self.assertIsInstance(snap.warnings, list)


# ===========================================================================
# T2-02: Source versions stored.
# ===========================================================================

class TestT2_02_SourceVersionsStored(unittest.TestCase):
    def test_source_versions_contains_blackboard(self):
        snap = portfolio_snapshot_build(build_sources())
        self.assertIn("blackboard", snap.source_versions)

    def test_source_versions_contains_local_doc(self):
        snap = portfolio_snapshot_build(build_sources())
        self.assertIn("local_doc", snap.source_versions)

    def test_source_versions_has_entity_count(self):
        snap = portfolio_snapshot_build(build_sources())
        bv = snap.source_versions["blackboard"]
        self.assertGreater(bv["entity_count"], 0)
        self.assertIn("source_version", bv)
        self.assertIn("fetched_at", bv)

    def test_source_versions_has_local_doc_version(self):
        snap = portfolio_snapshot_build(build_sources())
        lv = snap.source_versions["local_doc"]
        self.assertEqual(lv["source_version"], "v1.0")


# ===========================================================================
# T2-03: Stale source clearly marked.
# ===========================================================================

class TestT2_03_StaleSourceMarked(unittest.TestCase):
    def test_unknown_source_version_reduces_confidence(self):
        sources = build_sources()
        # Use a dict with unknown/empty version.
        sources["stale_source"] = [
            {
                "entity_type": "project",
                "project_id": "proj-stale",
                "project_name": "Stale",
                "source_system": "stale_source",
                "source_id": "stale-src",
                "source_version": "",
                "fetched_at": FIXTURE_TIME.isoformat(),
            }
        ]
        snap = portfolio_snapshot_build(sources)
        self.assertLess(snap.confidence, 1.0)
        self.assertTrue(
            any("stale_source" in w for w in snap.warnings)
        )

    def test_missing_critical_source_reduces_confidence(self):
        sources = {"local_doc": build_sources()["local_doc"]}
        snap = portfolio_snapshot_build(sources)
        self.assertLess(snap.confidence, 1.0)
        self.assertTrue(
            any("blackboard" in w.lower() for w in snap.warnings)
        )


# ===========================================================================
# T2-04: Diff reports only material changes.
# ===========================================================================

class TestT2_04_DiffMaterialChanges(unittest.TestCase):
    def test_no_changes_returns_empty_dict(self):
        snap = portfolio_snapshot_build(build_sources())
        diff = portfolio_snapshot_diff(snap, snap)
        self.assertEqual(diff, {})

    def test_new_deadline_is_material(self):
        old = portfolio_snapshot_build(build_sources())
        new_sources = build_sources()
        new_sources["blackboard"].append(
            make_deadline(deadline_id="dl-002", due_date="2026-12-01")
        )
        new_snap = portfolio_snapshot_build(new_sources)
        diff = portfolio_snapshot_diff(old, new_snap)
        self.assertIn("new_deadlines", diff)
        self.assertEqual(len(diff["new_deadlines"]), 1)

    def test_timestamp_only_change_is_immaterial(self):
        old = portfolio_snapshot_build(build_sources())
        new_snap = portfolio_snapshot_build(build_sources())
        new_snap = PortfolioSnapshot(
            snapshot_version=new_snap.snapshot_version,
            generated_at="2099-01-01T00:00:00+00:00",
            projects=new_snap.projects,
            active_goals=new_snap.active_goals,
            current_priorities=new_snap.current_priorities,
            deadlines=new_snap.deadlines,
            commitments=new_snap.commitments,
            capacity_summary=new_snap.capacity_summary,
            active_tasks=new_snap.active_tasks,
            blocked_tasks=new_snap.blocked_tasks,
            experiments=new_snap.experiments,
            material_metrics=new_snap.material_metrics,
            risks=new_snap.risks,
            pending_decisions=new_snap.pending_decisions,
            pending_approvals=new_snap.pending_approvals,
            agent_state=new_snap.agent_state,
            recent_outcomes=new_snap.recent_outcomes,
            stalled_work=new_snap.stalled_work,
            source_versions=new_snap.source_versions,
            confidence=new_snap.confidence,
            warnings=new_snap.warnings,
        )
        diff = portfolio_snapshot_diff(old, new_snap)
        self.assertNotIn("generated_at", str(diff))

    def test_new_risk_is_material(self):
        old = portfolio_snapshot_build(build_sources())
        new_sources = build_sources()
        new_sources["blackboard"].append(
            make_risk(risk_id="risk-002", title="New risk")
        )
        new_snap = portfolio_snapshot_build(new_sources)
        diff = portfolio_snapshot_diff(old, new_snap)
        self.assertIn("material_risks", diff)

    def test_status_flip_is_material(self):
        old = portfolio_snapshot_build(build_sources())
        new_sources = build_sources()
        new_sources["blackboard"][2] = make_task(
            task_id="task-001", status="in_progress"
        )
        new_snap = portfolio_snapshot_build(new_sources)
        diff = portfolio_snapshot_diff(old, new_snap)
        self.assertIn("status_flips", diff)

    def test_new_blocker_is_material(self):
        old = portfolio_snapshot_build(build_sources())
        new_sources = build_sources()
        new_sources["blackboard"][2] = make_task(
            task_id="task-002", status="blocked"
        )
        new_snap = portfolio_snapshot_build(new_sources)
        diff = portfolio_snapshot_diff(old, new_snap)
        self.assertIn("new_blocked_tasks", diff)

    def test_new_pending_approval_is_material(self):
        old = portfolio_snapshot_build(build_sources())
        new_sources = build_sources()
        new_sources["blackboard"].append(
            make_approval(approval_id="app-002", status="pending")
        )
        new_snap = portfolio_snapshot_build(new_sources)
        diff = portfolio_snapshot_diff(old, new_snap)
        self.assertIn("new_pending_approvals", diff)


# ===========================================================================
# T2-05: Snapshot remains compact instead of copying all raw rows.
# ===========================================================================

class TestT2_05_CompactSnapshot(unittest.TestCase):
    def test_snapshot_does_not_dump_all_raw_rows(self):
        """Build from sources with many raw rows; snapshot should
        contain summaries/references, not every raw field."""
        many_tasks = [
            make_task(task_id=f"task-{i:03d}", title=f"Task {i}")
            for i in range(50)
        ]
        sources = {"blackboard": many_tasks}
        snap = portfolio_snapshot_build(sources)
        # active_tasks should be a subset (not all 50 if some are done).
        # The key check: capacity_summary has counts, not 50 task objects.
        self.assertIsInstance(snap.capacity_summary, dict)
        self.assertIn("total_tasks", snap.capacity_summary)
        self.assertEqual(snap.capacity_summary["total_tasks"], 50)

    def test_projects_are_entity_references_not_raw_rows(self):
        snap = portfolio_snapshot_build(build_sources())
        for p in snap.projects:
            self.assertIsInstance(p, Project)
            # Should not carry raw source rows.
            self.assertTrue(hasattr(p, "project_id"))

    def test_deadlines_are_summaries_not_full_source_rows(self):
        snap = portfolio_snapshot_build(build_sources())
        self.assertLessEqual(len(snap.deadlines), 10)


# ===========================================================================
# T2-06: Clear chat context and rebuild from sources: equivalent snapshot.
# ===========================================================================

class TestT2_06_RebuildEquivalence(unittest.TestCase):
    def test_rebuild_from_same_sources_produces_equivalent_snapshot(self):
        sources = build_sources()
        snap1 = portfolio_snapshot_build(sources)
        snap2 = portfolio_snapshot_build(sources)
        # Same entity counts per section.
        self.assertEqual(len(snap1.projects), len(snap2.projects))
        self.assertEqual(len(snap1.active_goals), len(snap2.active_goals))
        self.assertEqual(len(snap1.deadlines), len(snap2.deadlines))
        self.assertEqual(len(snap1.risks), len(snap2.risks))
        self.assertEqual(len(snap1.active_tasks), len(snap2.active_tasks))
        self.assertEqual(len(snap1.pending_approvals), len(snap2.pending_approvals))
        self.assertEqual(snap1.confidence, snap2.confidence)

    def test_get_accessor_returns_same_snapshot(self):
        snap = portfolio_snapshot_build(build_sources())
        retrieved = portfolio_snapshot_get(snap)
        self.assertIs(retrieved, snap)


# ===========================================================================
# T2-07: Missing critical source reduces confidence rather than inventing state.
# ===========================================================================

class TestT2_07_MissingSourceReducesConfidence(unittest.TestCase):
    def test_missing_blackboard_reduces_confidence(self):
        sources = {"local_doc": build_sources()["local_doc"]}
        snap = portfolio_snapshot_build(sources)
        self.assertLess(snap.confidence, 1.0)
        self.assertTrue(len(snap.warnings) > 0)

    def test_validate_reports_missing_critical_source(self):
        sources = {"local_doc": build_sources()["local_doc"]}
        snap = portfolio_snapshot_build(sources)
        result = portfolio_snapshot_validate(snap)
        self.assertLess(result["confidence"], 1.0)
        self.assertTrue(len(result["issues"]) > 0)

    def test_validate_does_not_invent_state(self):
        """Missing source: snapshot should have empty project list,
        not fabricated projects."""
        sources: dict = {}
        snap = portfolio_snapshot_build(sources)
        self.assertEqual(len(snap.projects), 0)
        self.assertEqual(len(snap.active_goals), 0)
        self.assertEqual(len(snap.active_tasks), 0)
        self.assertLess(snap.confidence, 1.0)

    def test_validate_passes_with_full_sources(self):
        snap = portfolio_snapshot_build(build_sources())
        result = portfolio_snapshot_validate(snap)
        self.assertTrue(result["valid"])
        self.assertEqual(result["confidence"], 1.0)


# ===========================================================================
# Refresh tests
# ===========================================================================

class TestRefresh(unittest.TestCase):
    def test_refresh_preserves_version_history(self):
        sources = build_sources()
        snap1 = portfolio_snapshot_build(sources)
        snap2 = portfolio_snapshot_refresh(snap1, sources)
        self.assertIn("blackboard", snap2.source_versions)
        self.assertIn("local_doc", snap2.source_versions)

    def test_refresh_merges_warnings(self):
        sources = {"local_doc": build_sources()["local_doc"]}
        snap1 = portfolio_snapshot_build(sources)
        snap2 = portfolio_snapshot_refresh(snap1, sources)
        self.assertGreater(len(snap2.warnings), 0)


# ===========================================================================
# Validate tests
# ===========================================================================

class TestValidate(unittest.TestCase):
    def test_validate_returns_dict_with_expected_keys(self):
        snap = portfolio_snapshot_build(build_sources())
        result = portfolio_snapshot_validate(snap)
        self.assertIn("valid", result)
        self.assertIn("confidence", result)
        self.assertIn("warnings", result)
        self.assertIn("issues", result)

    def test_validate_empty_snapshot_has_issues(self):
        snap = PortfolioSnapshot()
        result = portfolio_snapshot_validate(snap)
        self.assertFalse(result["valid"])
        self.assertLess(result["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()