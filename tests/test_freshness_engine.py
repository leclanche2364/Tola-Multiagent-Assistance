"""Batch 5 QA tests for the freshness engine and refresh executor.

Covers six mixed scenarios plus the Scholar semantic-staleness special test.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from agents.daily_synthesis.freshness import (
    FreshnessStatus,
    HandoffRecord,
    RefreshPlan,
    evaluate_freshness,
    evaluate_rhythm_freshness,
    evaluate_growth_freshness,
    evaluate_projects_freshness,
    evaluate_scholar_freshness,
    build_refresh_plan,
    RHYTHM_FRESHNESS_WINDOW_HOURS,
    GROWTH_FRESHNESS_WINDOW_HOURS,
)
from agents.daily_synthesis.refresh import (
    RefreshExecutionReport,
    execute_refresh,
)
from agents.daily_synthesis.contracts import validate_payload, ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime.now(timezone.utc)


def _ts(hours_ago: float) -> str:
    dt = NOW - timedelta(hours=hours_ago)
    return dt.isoformat()


def _rhythm_fresh_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="rhythm",
        payload={"schema_version": "rhythm_capacity_handoff.v1", "agent_id": "tola"},
        source_updated_at=_ts(0.5),
        freshness_status=FreshnessStatus.FRESH,
    )


def _rhythm_stale_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="rhythm",
        payload={"schema_version": "rhythm_capacity_handoff.v1", "agent_id": "tola"},
        source_updated_at=_ts(25),
        freshness_status=FreshnessStatus.STALE,
    )


def _growth_fresh_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="growth",
        payload={"schema_version": "growth_handoff.v1", "agent_id": "tola"},
        source_updated_at=_ts(1),
        freshness_status=FreshnessStatus.FRESH,
    )


def _growth_stale_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="growth",
        payload={"schema_version": "growth_handoff.v1", "agent_id": "tola"},
        source_updated_at=_ts(25),
        freshness_status=FreshnessStatus.STALE,
    )


def _projects_fresh_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="projects",
        payload={"schema_version": "project_status_handoff.v1", "agent_id": "tola"},
        source_updated_at=_ts(1),
        freshness_status=FreshnessStatus.FRESH,
    )


def _projects_stale_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="projects",
        payload={"schema_version": "project_status_handoff.v1", "agent_id": "tola"},
        source_updated_at=_ts(25),
        freshness_status=FreshnessStatus.STALE,
    )


def _scholar_fresh_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="scholar",
        payload={
            "schema_version": "scholar_handoff.v1",
            "agent_id": "tola",
            "current_batch_id": "batch_0",
            "timestamp": _ts(0.5),
        },
        source_updated_at=_ts(0.5),
        freshness_status=FreshnessStatus.FRESH,
    )


def _scholar_stale_handoff() -> HandoffRecord:
    return HandoffRecord(
        domain="scholar",
        payload={
            "schema_version": "scholar_handoff.v1",
            "agent_id": "tola",
            "current_batch_id": "batch_0",
            "timestamp": _ts(25),
        },
        source_updated_at=_ts(25),
        freshness_status=FreshnessStatus.STALE,
    )


def _missing_handoff(domain: str) -> HandoffRecord:
    return HandoffRecord(
        domain=domain,
        payload={},
        source_updated_at=None,
        freshness_status=FreshnessStatus.MISSING,
    )


# ---------------------------------------------------------------------------
# Per-domain evaluator tests
# ---------------------------------------------------------------------------


class TestRhythmFreshness:
    def test_rhythm_fresh_under_2h(self):
        h = HandoffRecord(domain="rhythm", payload={}, source_updated_at=_ts(0.5))
        assert evaluate_rhythm_freshness(h) == FreshnessStatus.FRESH

    def test_rhythm_aging_2h_to_24h(self):
        h = HandoffRecord(domain="rhythm", payload={}, source_updated_at=_ts(3))
        assert evaluate_rhythm_freshness(h) == FreshnessStatus.AGING

    def test_rhythm_stale_over_24h(self):
        h = HandoffRecord(domain="rhythm", payload={}, source_updated_at=_ts(25))
        assert evaluate_rhythm_freshness(h) == FreshnessStatus.STALE

    def test_rhythm_missing_no_timestamp(self):
        h = HandoffRecord(domain="rhythm", payload={}, source_updated_at=None)
        assert evaluate_rhythm_freshness(h) == FreshnessStatus.MISSING


class TestGrowthFreshness:
    def test_growth_fresh_under_24h(self):
        h = HandoffRecord(domain="growth", payload={}, source_updated_at=_ts(1))
        assert evaluate_growth_freshness(h) == FreshnessStatus.FRESH

    def test_growth_stale_over_24h(self):
        h = HandoffRecord(domain="growth", payload={}, source_updated_at=_ts(25))
        assert evaluate_growth_freshness(h) == FreshnessStatus.STALE

    def test_growth_missing_no_timestamp(self):
        h = HandoffRecord(domain="growth", payload={}, source_updated_at=None)
        assert evaluate_growth_freshness(h) == FreshnessStatus.MISSING


class TestProjectsFreshness:
    def test_projects_fresh_under_24h(self):
        h = HandoffRecord(domain="projects", payload={}, source_updated_at=_ts(1))
        assert evaluate_projects_freshness(h) == FreshnessStatus.FRESH

    def test_projects_stale_over_24h(self):
        h = HandoffRecord(domain="projects", payload={}, source_updated_at=_ts(25))
        assert evaluate_projects_freshness(h) == FreshnessStatus.STALE

    def test_projects_missing_no_timestamp(self):
        h = HandoffRecord(domain="projects", payload={}, source_updated_at=None)
        assert evaluate_projects_freshness(h) == FreshnessStatus.MISSING


# ---------------------------------------------------------------------------
# Scholar semantic staleness — QA plan special rule
# ---------------------------------------------------------------------------


class TestScholarSemanticStaleness:
    def test_valid_schema_older_batch_than_completion_event_is_stale(self):
        """Special rule: current_batch older than latest completion event → stale."""
        state = {
            "batches": [
                {
                    "batch_id": "batch_0",
                    "articles": [
                        {
                            "title": "Article A",
                            "status": "complete",
                            "completion_events": [
                                {
                                    "timestamp": "2026-10-03T13:00:00+00:00",
                                    "action": "complete",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        # Handoff timestamp is older than the completion event
        handoff = HandoffRecord(
            domain="scholar",
            payload={
                "schema_version": "scholar_handoff.v1",
                "agent_id": "tola",
                "current_batch_id": "batch_0",
                "timestamp": "2026-10-03T12:00:00+00:00",
            },
            source_updated_at="2026-10-03T12:00:00+00:00",
        )
        result = evaluate_scholar_freshness(handoff, state=state)
        assert result == FreshnessStatus.STALE

    def test_valid_schema_newer_batch_than_completion_event_is_fresh(self):
        """When handoff is newer than completion events, it is fresh."""
        state = {
            "batches": [
                {
                    "batch_id": "batch_0",
                    "articles": [
                        {
                            "title": "Article A",
                            "status": "complete",
                            "completion_events": [
                                {
                                    "timestamp": "2026-10-03T11:00:00+00:00",
                                    "action": "complete",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        handoff = HandoffRecord(
            domain="scholar",
            payload={
                "schema_version": "scholar_handoff.v1",
                "agent_id": "tola",
                "current_batch_id": "batch_0",
                "timestamp": "2026-10-03T13:00:00+00:00",
            },
            source_updated_at="2026-10-03T13:00:00+00:00",
        )
        result = evaluate_scholar_freshness(handoff, state=state)
        assert result == FreshnessStatus.FRESH

    def test_scholar_missing_timestamp_is_missing(self):
        handoff = HandoffRecord(
            domain="scholar",
            payload={},
            source_updated_at=None,
        )
        result = evaluate_scholar_freshness(handoff)
        assert result == FreshnessStatus.MISSING


# ---------------------------------------------------------------------------
# Six mixed scenarios — targeted refresh plan tests
# ---------------------------------------------------------------------------


class TestMixedScenario1_RhymeStale_ScholarFresh:
    """Scenario: Rhythm stale + Scholar fresh → refresh only rhythm."""

    def test_refresh_plan_targets_only_rhythm(self):
        handoffs = {
            "rhythm": _rhythm_stale_handoff(),
            "scholar": _scholar_fresh_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert plan.domains_to_refresh == ["rhythm"]
        assert "rhythm" in plan.domain_reasons
        assert "scholar" not in plan.domain_reasons


class TestMixedScenario2_ScholarStale_RhythmFresh:
    """Scenario: Scholar stale + Rhythm fresh → refresh only scholar."""

    def test_refresh_plan_targets_only_scholar(self):
        handoffs = {
            "scholar": _scholar_stale_handoff(),
            "rhythm": _rhythm_fresh_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert plan.domains_to_refresh == ["scholar"]
        assert "scholar" in plan.domain_reasons
        assert "rhythm" not in plan.domain_reasons


class TestMixedScenario3_GrowthStaleOnly:
    """Scenario: Growth stale only → refresh only growth."""

    def test_refresh_plan_targets_only_growth(self):
        handoffs = {
            "growth": _growth_stale_handoff(),
            "rhythm": _rhythm_fresh_handoff(),
            "scholar": _scholar_fresh_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert plan.domains_to_refresh == ["growth"]
        assert "growth" in plan.domain_reasons


class TestMixedScenario4_OneProjectStaleOnly:
    """Scenario: One project stale only → refresh only projects."""

    def test_refresh_plan_targets_only_projects(self):
        handoffs = {
            "projects": _projects_stale_handoff(),
            "rhythm": _rhythm_fresh_handoff(),
            "growth": _growth_fresh_handoff(),
            "scholar": _scholar_fresh_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert plan.domains_to_refresh == ["projects"]
        assert "projects" in plan.domain_reasons


class TestMixedScenario5_EverythingFresh:
    """Scenario: everything fresh → no refresh needed."""

    def test_refresh_plan_all_fresh(self):
        handoffs = {
            "rhythm": _rhythm_fresh_handoff(),
            "growth": _growth_fresh_handoff(),
            "projects": _projects_fresh_handoff(),
            "scholar": _scholar_fresh_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert plan.domains_to_refresh == []
        assert plan.all_fresh is True


class TestMixedScenario6_AllSourcesStale:
    """Scenario: all sources stale → refresh all domains."""

    def test_refresh_plan_targets_all(self):
        handoffs = {
            "rhythm": _rhythm_stale_handoff(),
            "growth": _growth_stale_handoff(),
            "projects": _projects_stale_handoff(),
            "scholar": _scholar_stale_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert set(plan.domains_to_refresh) == {"rhythm", "growth", "projects", "scholar"}
        assert plan.all_fresh is False


# ---------------------------------------------------------------------------
# Failed refresh surfaced honestly
# ---------------------------------------------------------------------------


class TestFailedRefresh:
    def test_refresh_attempt_error_returns_failed_status(self):
        """A refresh that errors returns failed status, never silently treated as fresh."""

        def bad_producer(agent_id, state=None):
            raise RuntimeError("simulated producer failure")

        plan = RefreshPlan(domains_to_refresh=["rhythm"])
        plan.domain_reasons["rhythm"] = "rhythm is stale"

        report = execute_refresh(
            plan,
            producers={"rhythm": bad_producer},
            current_handoffs={},
        )

        assert "rhythm" in report.failed_domains
        assert report.results["rhythm"].success is False
        assert report.results["rhythm"].freshness_status == FreshnessStatus.FAILED
        assert "simulated producer failure" in report.results["rhythm"].error

    def test_contract_failure_returns_failed_not_fresh(self):
        """Contract validation failure → failed status, never fresh."""

        def bad_producer(agent_id, state=None):
            return {"schema_version": "rhythm_capacity_handoff.v1"}  # missing required fields

        plan = RefreshPlan(domains_to_refresh=["rhythm"])
        plan.domain_reasons["rhythm"] = "rhythm is stale"

        report = execute_refresh(
            plan,
            producers={"rhythm": bad_producer},
            current_handoffs={},
        )

        assert report.results["rhythm"].success is False
        assert report.results["rhythm"].freshness_status == FreshnessStatus.FAILED


# ---------------------------------------------------------------------------
# Targeted refresh — never broad fan-out
# ---------------------------------------------------------------------------


class TestTargetedRefreshNoFanOut:
    def test_only_stale_domains_refreshed(self):
        """When one domain is stale, only that domain is refreshed."""

        def rhythm_producer(agent_id, state=None):
            return {
                "schema_version": "rhythm_capacity_handoff.v1",
                "agent_id": agent_id,
                "rhythm_id": "r1",
                "capacity_used_minutes": 120,
                "capacity_total_minutes": 480,
                "recovery_buffer_minutes": 30,
            }

        plan = RefreshPlan(domains_to_refresh=["rhythm"])
        plan.domain_reasons["rhythm"] = "rhythm is stale"

        report = execute_refresh(
            plan,
            producers={"rhythm": rhythm_producer},
            current_handoffs={},
        )

        assert report.refreshed_domains == ["rhythm"]
        assert report.results["rhythm"].success is True
        assert report.results["rhythm"].freshness_status == FreshnessStatus.FRESH


# ---------------------------------------------------------------------------
# Refresh reason logging per domain
# ---------------------------------------------------------------------------


class TestRefreshReasonLogging:
    def test_refresh_reason_logged_per_domain(self):
        handoffs = {
            "rhythm": _rhythm_stale_handoff(),
            "growth": _growth_fresh_handoff(),
        }
        plan = build_refresh_plan(handoffs)
        assert "rhythm" in plan.domain_reasons
        assert "growth" not in plan.domain_reasons
        assert "rhythm" in plan.domains_to_refresh
        assert "growth" not in plan.domains_to_refresh


# ---------------------------------------------------------------------------
# evaluate_freshness integration tests
# ---------------------------------------------------------------------------


class TestEvaluateFreshnessIntegration:
    def test_evaluate_freshness_sets_status(self):
        h = HandoffRecord(
            domain="rhythm",
            payload={},
            source_updated_at=_ts(0.5),
        )
        result = evaluate_freshness(h)
        assert result.freshness_status == FreshnessStatus.FRESH

    def test_evaluate_freshness_unknown_domain_is_missing(self):
        h = HandoffRecord(domain="unknown", payload={}, source_updated_at=_ts(1))
        result = evaluate_freshness(h)
        assert result.freshness_status == FreshnessStatus.MISSING

    def test_evaluate_freshness_failed_on_error(self):
        # Patch the evaluator dict entry directly so evaluate_freshness
        # calls the raising function.
        def _boom(handoff, **kwargs):
            raise Exception("boom")

        with patch.dict("agents.daily_synthesis.freshness.FRESHNESS_EVALUATORS", {"rhythm": _boom}):
            h = HandoffRecord(domain="rhythm", payload={}, source_updated_at=_ts(1))
            result = evaluate_freshness(h)
        assert result.freshness_status == FreshnessStatus.FAILED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
