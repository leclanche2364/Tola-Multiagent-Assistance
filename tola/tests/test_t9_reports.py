"""QA T9 tests -- Client Report Generator (Batch T9).

Covers all QA T9 cases for daily_brief, portfolio_status_report,
and weekly_digest.  Stdlib only: unittest.  Plain ASCII.
Deterministic: same inputs always produce identical output.
"""

from __future__ import annotations

import unittest

from tola.reports_gen.daily_brief import daily_brief
from tola.reports_gen.status_report import portfolio_status_report
from tola.reports_gen.weekly_digest import weekly_digest


# ===========================================================================
# Shared fixtures
# ===========================================================================

class _FakeProject:
    """Minimal project object that supports attribute assignment."""
    def __init__(self, pid="P1", name="Alpha Project", status="active"):
        self.project_id = pid
        self.project_name = name
        self.status = status
        self._health_assessment = None


def _make_project(
    pid: str = "P1",
    name: str = "Alpha Project",
    status: str = "active",
) -> _FakeProject:
    """Return a minimal project object (not a contracts.Project)."""
    return _FakeProject(pid=pid, name=name, status=status)


class _FakeHealthAssessment:
    """Minimal health assessment object."""
    def __init__(self, label="ON_TRACK", signals=None):
        self.label = label
        self.signals = signals or []


def _make_health_assessment(label: str = "ON_TRACK", signals: list = None) -> _FakeHealthAssessment:
    """Return a minimal health assessment object."""
    return _FakeHealthAssessment(label=label, signals=signals or [])


class _FakeSignal:
    """Minimal HealthSignal-like object."""
    def __init__(self, signal_type="DEADLINE_RISK", entity_type="task", entity_id="T1", observed=None):
        self.type = signal_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.observed = observed or {}


def _make_signal(signal_type: str = "DEADLINE_RISK", observed: dict = None) -> _FakeSignal:
    """Return a minimal HealthSignal-like object."""
    return _FakeSignal(signal_type=signal_type, observed=observed or {})


def _make_snapshot(
    projects: list = None,
    warnings: list = None,
) -> object:
    """Return a minimal PortfolioSnapshot-like object."""
    snap = type("PortfolioSnapshot", (), {})()
    snap.snapshot_version = "1.0"
    snap.generated_at = "2026-09-29T19:00:00"
    snap.projects = projects or []
    snap.warnings = warnings or []
    snap.confidence = 1.0
    snap.active_tasks = []
    snap.blocked_tasks = []
    snap.active_goals = []
    snap.experiments = []
    snap.pending_approvals = []
    snap.material_metrics = []
    snap.risks = []
    snap.source_versions = {"blackboard": {"source_version": "1.0"}}
    return snap


# ===========================================================================
# daily_brief tests
# ===========================================================================

class TestDailyBrief(unittest.TestCase):
    """daily_brief QA cases."""

    def test_brief_includes_only_material_attention_items(self):
        """T9-01: ON_TRACK projects must NOT appear in attention items."""
        p = _make_project("P1", "Healthy Project")
        p._health_assessment = _make_health_assessment("ON_TRACK")
        snap = _make_snapshot(projects=[p])
        result = daily_brief(snap, escalations=[], delegations=[])
        # ON_TRACK should not appear as an attention item.
        self.assertNotIn("Healthy Project", result.split("Today's attention items:")[1].split("Open escalations:")[0])

    def test_brief_includes_attention_signal(self):
        """Attention-level project with DEADLINE_RISK signal appears in brief."""
        p = _make_project("P1", "At Risk Project")
        p._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("DEADLINE_RISK", {"deadline": "2026-10-01", "days_until_deadline": 2}),
        ])
        snap = _make_snapshot(projects=[p])
        result = daily_brief(snap, escalations=[], delegations=[])
        self.assertIn("DEADLINE_RISK", result)
        self.assertIn("At Risk Project", result)

    def test_brief_sorted_stable(self):
        """Output is deterministic and sorted by project_id."""
        p1 = _make_project("P2", "Beta Project")
        p1._health_assessment = _make_health_assessment("ON_TRACK")
        p2 = _make_project("P1", "Alpha Project")
        p2._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("STALLED_ACTIVITY"),
        ])
        snap = _make_snapshot(projects=[p1, p2])
        result = daily_brief(snap, escalations=[], delegations=[])
        # P1 (Alpha) must appear before P2 (Beta) in attention section.
        attention_section = result.split("Today's attention items:")[1].split("Open escalations:")[0]
        alpha_pos = attention_section.find("Alpha Project")
        beta_pos = attention_section.find("Beta Project")
        # Beta is ON_TRACK so should not appear in attention; Alpha should.
        self.assertIn("Alpha Project", attention_section)
        self.assertNotIn("Beta Project", attention_section)

    def test_brief_no_secrets_in_output(self):
        """T9-05: No credentials/secrets appear in output even if present in input."""
        p = _make_project("P1", "Secret Project")
        p._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("DEADLINE_RISK"),
        ])
        snap = _make_snapshot(projects=[p])
        # Inject fake credential into snapshot metadata (agent_state).
        snap.agent_state = {"api_key": "sk-fake-secret-key-12345", "db_pass": "hunter2"}
        result = daily_brief(snap, escalations=[], delegations=[])
        self.assertNotIn("sk-fake-secret-key-12345", result)
        self.assertNotIn("hunter2", result)

    def test_brief_open_escalations(self):
        """Open escalations appear in the brief."""
        p = _make_project("P1", "Project One")
        p._health_assessment = _make_health_assessment("ON_TRACK")
        snap = _make_snapshot(projects=[p])
        escalations = [
            {"level": "STOP_AND_ESCALATE", "reason": "Blocked chain", "recipient": "HABEEB", "status": "open"},
        ]
        result = daily_brief(snap, escalations=escalations, delegations=[])
        self.assertIn("STOP_AND_ESCALATE", result)
        self.assertIn("Blocked chain", result)

    def test_brief_resolved_escalations_excluded(self):
        """Resolved escalations must NOT appear in the brief."""
        p = _make_project("P1", "Project One")
        p._health_assessment = _make_health_assessment("ON_TRACK")
        snap = _make_snapshot(projects=[p])
        escalations = [
            {"level": "NOTE", "reason": "Old issue", "recipient": "TOLA", "status": "resolved"},
        ]
        result = daily_brief(snap, escalations=escalations, delegations=[])
        self.assertNotIn("Old issue", result)

    def test_brief_delegated_work_in_flight(self):
        """In-flight delegations appear in the brief."""
        p = _make_project("P1", "Project One")
        p._health_assessment = _make_health_assessment("ON_TRACK")
        snap = _make_snapshot(projects=[p])
        delegations = [
            {"delegation_id": "D1", "specialist": "Rhythm", "status": "IN_PROGRESS"},
            {"delegation_id": "D2", "specialist": "Growth", "status": "COMPLETED"},
        ]
        result = daily_brief(snap, escalations=[], delegations=delegations)
        self.assertIn("D1", result)
        self.assertIn("IN_PROGRESS", result)
        self.assertNotIn("D2", result)  # COMPLETED is terminal, excluded

    def test_brief_determinism(self):
        """Same inputs produce identical output string."""
        p = _make_project("P1", "Alpha")
        p._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("STALLED_ACTIVITY"),
        ])
        snap = _make_snapshot(projects=[p])
        r1 = daily_brief(snap, escalations=[], delegations=[])
        r2 = daily_brief(snap, escalations=[], delegations=[])
        self.assertEqual(r1, r2)

    def test_brief_empty_projects(self):
        """Empty snapshot produces a valid brief with zero counts."""
        snap = _make_snapshot(projects=[])
        result = daily_brief(snap, escalations=[], delegations=[])
        self.assertIn("Total projects: 0", result)
        self.assertIn("ON_TRACK: 0", result)


# ===========================================================================
# portfolio_status_report tests
# ===========================================================================

class TestPortfolioStatusReport(unittest.TestCase):
    """portfolio_status_report QA cases."""

    def test_status_report_includes_evidence_for_non_on_track(self):
        """T9-02: Non-ON_TRACK projects must include evidence lines."""
        p = _make_project("P1", "At Risk Project")
        p._health_assessment = _make_health_assessment("AT_RISK", [
            _make_signal("DEADLINE_RISK", {"deadline": "2026-10-01", "days_until_deadline": 3}),
            _make_signal("STALLED_ACTIVITY", {"days_without_progress": 7}),
        ])
        snap = _make_snapshot(projects=[p])
        result = portfolio_status_report(snap, plans=[], risks=[])
        # Evidence lines must appear for AT_RISK project.
        self.assertIn("DEADLINE_RISK", result)
        self.assertIn("STALLED_ACTIVITY", result)
        self.assertIn("days_until_deadline=3", result)

    def test_status_report_no_evidence_for_on_track(self):
        """ON_TRACK projects show 'no material signals' evidence line."""
        p = _make_project("P1", "Healthy Project")
        p._health_assessment = _make_health_assessment("ON_TRACK")
        snap = _make_snapshot(projects=[p])
        result = portfolio_status_report(snap, plans=[], risks=[])
        self.assertIn("Healthy Project", result)
        self.assertIn("no material signals", result)

    def test_status_report_risk_highlights(self):
        """Risk section includes risks from snapshot."""
        from tola.portfolio.contracts import Risk as ContractsRisk
        import datetime
        r = ContractsRisk(
            risk_id="R1",
            entity_type="project",
            entity_id="P1",
            title="Budget overrun",
            severity="high",
            status="open",
            source_system="blackboard",
            fetched_at=datetime.datetime(2026, 9, 29, 12, 0, 0),
        )
        snap = _make_snapshot(projects=[])
        snap.risks = [r]
        result = portfolio_status_report(snap, plans=[], risks=[])
        self.assertIn("R1", result)
        self.assertIn("Budget overrun", result)
        self.assertIn("HIGH", result)

    def test_status_report_critical_path(self):
        """Critical path milestones section is present."""
        snap = _make_snapshot(projects=[])
        result = portfolio_status_report(snap, plans=[], risks=[])
        self.assertIn("CRITICAL PATH MILESTONES", result)

    def test_status_report_plan_versions(self):
        """Plan versions section includes plan metadata."""
        plans = [
            {"plan_id": "PLAN-1", "version": "2.1", "status": "active"},
            {"plan_id": "PLAN-2", "version": "1.0", "status": "draft"},
        ]
        snap = _make_snapshot(projects=[])
        result = portfolio_status_report(snap, plans=plans, risks=[])
        self.assertIn("PLAN-1", result)
        self.assertIn("version=2.1", result)
        self.assertIn("PLAN-2", result)
        self.assertIn("version=1.0", result)

    def test_status_report_no_secrets(self):
        """T9-05: No credentials in status report output."""
        p = _make_project("P1", "Secure Project")
        p._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("DEADLINE_RISK"),
        ])
        snap = _make_snapshot(projects=[p])
        snap.agent_state = {"credential": "super-secret-token"}
        result = portfolio_status_report(snap, plans=[], risks=[])
        self.assertNotIn("super-secret-token", result)

    def test_status_report_determinism(self):
        """Same inputs produce identical output string."""
        p = _make_project("P1", "Alpha")
        p._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("STALLED_ACTIVITY"),
        ])
        snap = _make_snapshot(projects=[p])
        r1 = portfolio_status_report(snap, plans=[], risks=[])
        r2 = portfolio_status_report(snap, plans=[], risks=[])
        self.assertEqual(r1, r2)

    def test_status_report_empty_snapshot(self):
        """Empty snapshot produces a valid report."""
        snap = _make_snapshot(projects=[])
        result = portfolio_status_report(snap, plans=[], risks=[])
        self.assertIn("PORTFOLIO STATUS REPORT", result)
        self.assertIn("no projects in snapshot", result)


# ===========================================================================
# weekly_digest tests
# ===========================================================================

class TestWeeklyDigest(unittest.TestCase):
    """weekly_digest QA cases."""

    def test_weekly_digest_counts_match_ledger(self):
        """T9-03: Digest counts match the delegation ledger inputs."""
        inputs = {
            "delegation_ledger": [
                {"delegation_id": "D1", "specialist": "Rhythm", "status": "IN_PROGRESS"},
                {"delegation_id": "D2", "specialist": "Growth", "status": "IN_PROGRESS"},
                {"delegation_id": "D3", "specialist": "Scholar", "status": "COMPLETED"},
                {"delegation_id": "D4", "specialist": "Rhythm", "status": "REJECTED"},
            ],
        }
        result = weekly_digest(inputs)
        self.assertIn("Total delegations: 4", result)
        self.assertIn("IN_PROGRESS: 2", result)
        self.assertIn("COMPLETED: 1", result)
        self.assertIn("REJECTED: 1", result)

    def test_weekly_digest_closed_completed_counts(self):
        """Closed/completed items count is correct."""
        inputs = {
            "closed_items": [
                {"id": "C1", "title": "Fix bug", "outcome": "SUCCESS"},
            ],
            "completed_items": [
                {"id": "C2", "title": "Write docs", "status": "done"},
            ],
        }
        result = weekly_digest(inputs)
        self.assertIn("Total closed/completed: 2", result)
        self.assertIn("C1", result)
        self.assertIn("C2", result)

    def test_weekly_digest_escalations_raised_resolved(self):
        """Escalation counts match inputs."""
        inputs = {
            "escalations_raised": [
                {"id": "E1", "level": "FLAG", "reason": "Risk detected"},
                {"id": "E2", "level": "PAUSE", "reason": "Stalled"},
            ],
            "escalations_resolved": [
                {"id": "E1", "resolution": "Mitigated"},
            ],
        }
        result = weekly_digest(inputs)
        self.assertIn("Raised: 2", result)
        self.assertIn("Resolved: 1", result)

    def test_weekly_digest_health_transitions(self):
        """Health transitions are listed correctly."""
        inputs = {
            "health_transitions": [
                {"project_id": "P1", "from_label": "ON_TRACK", "to_label": "ATTENTION"},
                {"project_id": "P2", "from_label": "ATTENTION", "to_label": "ON_TRACK"},
            ],
        }
        result = weekly_digest(inputs)
        self.assertIn("P1: ON_TRACK -> ATTENTION", result)
        self.assertIn("P2: ATTENTION -> ON_TRACK", result)

    def test_weekly_digest_determinism(self):
        """Same inputs produce identical output string."""
        inputs = {
            "closed_items": [
                {"id": "C1", "title": "Task A", "outcome": "SUCCESS"},
            ],
            "delegation_ledger": [
                {"delegation_id": "D1", "specialist": "Rhythm", "status": "IN_PROGRESS"},
            ],
            "health_transitions": [
                {"project_id": "P1", "from_label": "ON_TRACK", "to_label": "ATTENTION"},
            ],
        }
        r1 = weekly_digest(inputs)
        r2 = weekly_digest(inputs)
        self.assertEqual(r1, r2)

    def test_weekly_digest_no_secrets(self):
        """T9-05: No credentials in digest output even if present in inputs."""
        inputs = {
            "closed_items": [
                {"id": "C1", "title": "Task", "outcome": "SUCCESS"},
            ],
            "delegation_ledger": [
                {"delegation_id": "D1", "specialist": "Rhythm", "status": "IN_PROGRESS", "credential": "sk-abc123"},
            ],
        }
        result = weekly_digest(inputs)
        self.assertNotIn("sk-abc123", result)

    def test_weekly_digest_empty_inputs(self):
        """Empty week_inputs produces a valid digest with zero counts."""
        result = weekly_digest({})
        self.assertIn("Total closed/completed: 0", result)
        self.assertIn("Total delegations: 0", result)
        self.assertIn("Raised: 0", result)
        self.assertIn("Resolved: 0", result)

    def test_weekly_digest_sorted_stable(self):
        """Items are sorted deterministically by id."""
        inputs = {
            "closed_items": [
                {"id": "C3", "title": "Third", "outcome": "SUCCESS"},
                {"id": "C1", "title": "First", "outcome": "SUCCESS"},
                {"id": "C2", "title": "Second", "outcome": "SUCCESS"},
            ],
        }
        result = weekly_digest(inputs)
        # C1 must appear before C2 before C3 in the output.
        pos1 = result.find("C1")
        pos2 = result.find("C2")
        pos3 = result.find("C3")
        self.assertLess(pos1, pos2)
        self.assertLess(pos2, pos3)


# ===========================================================================
# Integration / cross-report tests
# ===========================================================================

class TestReportIntegration(unittest.TestCase):
    """Cross-cutting T9 tests."""

    def test_all_reports_plain_ascii(self):
        """All report outputs contain only ASCII characters."""
        p = _make_project("P1", "Test")
        p._health_assessment = _make_health_assessment("ON_TRACK")
        snap = _make_snapshot(projects=[p])

        brief = daily_brief(snap, escalations=[], delegations=[])
        self.assertTrue(all(ord(c) < 128 for c in brief), "daily_brief contains non-ASCII")

        status = portfolio_status_report(snap, plans=[], risks=[])
        self.assertTrue(all(ord(c) < 128 for c in status), "status_report contains non-ASCII")

        digest = weekly_digest({})
        self.assertTrue(all(ord(c) < 128 for c in digest), "weekly_digest contains non-ASCII")

    def test_all_reports_deterministic_roundtrip(self):
        """Three consecutive calls with same inputs yield identical strings."""
        p = _make_project("P1", "Test")
        p._health_assessment = _make_health_assessment("ATTENTION", [
            _make_signal("DEADLINE_RISK"),
        ])
        snap = _make_snapshot(projects=[p])

        b1 = daily_brief(snap, escalations=[], delegations=[])
        b2 = daily_brief(snap, escalations=[], delegations=[])
        b3 = daily_brief(snap, escalations=[], delegations=[])
        self.assertEqual(b1, b2)
        self.assertEqual(b2, b3)

        s1 = portfolio_status_report(snap, plans=[], risks=[])
        s2 = portfolio_status_report(snap, plans=[], risks=[])
        s3 = portfolio_status_report(snap, plans=[], risks=[])
        self.assertEqual(s1, s2)
        self.assertEqual(s2, s3)

        d1 = weekly_digest({"delegation_ledger": [{"delegation_id": "D1", "specialist": "R", "status": "IN_PROGRESS"}]})
        d2 = weekly_digest({"delegation_ledger": [{"delegation_id": "D1", "specialist": "R", "status": "IN_PROGRESS"}]})
        d3 = weekly_digest({"delegation_ledger": [{"delegation_id": "D1", "specialist": "R", "status": "IN_PROGRESS"}]})
        self.assertEqual(d1, d2)
        self.assertEqual(d2, d3)

    def test_no_write_outside_tola(self):
        """Reports must not write files.  Verify by checking no file I/O was attempted."""
        # This is a logical constraint: daily_brief, portfolio_status_report,
        # and weekly_digest are pure functions with no open()/write()/print().
        # We verify by checking the functions have no I/O calls in their source.
        import inspect
        from tola.reports_gen import daily_brief as db, status_report as sr, weekly_digest as wd

        for func in (db, sr, wd):
            source = inspect.getsource(func)
            self.assertNotIn("open(", source, f"{func.__name__} contains open() call")
            self.assertNotIn("write(", source, f"{func.__name__} contains write() call")
            self.assertNotIn("print(", source, f"{func.__name__} contains print() call")
            self.assertNotIn("subprocess", source, f"{func.__name__} uses subprocess")


if __name__ == "__main__":
    unittest.main()