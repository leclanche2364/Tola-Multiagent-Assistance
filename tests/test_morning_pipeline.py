"""Batch 9 QA tests for morning_pipeline.py.

Covers Batch 10 degradation scenarios:
- All sources healthy → complete brief
- One agent unavailable → degraded, skip domain, mark missing
- Supabase unavailable → persistence_unavailable, no SQLite fallback
- Stale Scholar → Scholar-only targeted refresh
- Schedule conflict returned by producer → conflict surfaced, never silently dropped
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.daily_synthesis.morning_pipeline import (
    MorningPipelineResult,
    OverallStatus,
    run_morning_pipeline,
)
from agents.daily_synthesis.persistence import PersistenceUnavailable
from agents.daily_synthesis.freshness import FreshnessStatus


# ---------------------------------------------------------------------------
# Fixture producers
# ---------------------------------------------------------------------------

def _fresh_capacity():
    return {
        "schema_version": "rhythm_capacity_handoff.v1",
        "agent_id": "tola",
        "rhythm_id": "r1",
        "capacity_used_minutes": 60,
        "capacity_total_minutes": 240,
        "recovery_buffer_minutes": 30,
        "source_updated_at": "2026-10-03T12:00:00+00:00",
    }


def _fresh_scholar():
    return {
        "schema_version": "scholar_handoff.v1",
        "agent_id": "scholar",
        "current_batch_id": "batch-42",
        "exact_action": "Read CCRN3 chapter 5",
        "estimated_minutes": 60,
        "definition_of_done": "Chapter 5 notes written",
        "reading_target": {
            "required": True,
            "article_title": "CRRN3 Deep Dive",
            "exact_sections_to_read": ["section 5.1"],
            "extraction_goal": "extract key definitions",
        },
        "source_refs": ["https://example.com/crrn3"],
        "source_updated_at": "2026-10-03T12:00:00+00:00",
    }


def _fresh_growth():
    return {
        "schema_version": "growth_handoff.v1",
        "agent_id": "growth",
        "project_id": "growth",
        "action": "growth_handoff",
        "estimated_minutes": 150,
        "definition_of_done": "Growth handoff produced",
        "next_actions": [
            {"action": "Finalize analysis", "estimated_effort_minutes": 60},
        ],
        "blockers": [],
        "deadlines": [],
        "source_updated_at": "2026-10-03T12:00:00+00:00",
    }


def _fresh_project():
    return {
        "schema_version": "project_status_handoff.v1",
        "agent_id": "tola",
        "project_id": "Shiftlyx",
        "status": "development",
        "summary": "Shiftlyx: development",
        "next_action": "Complete wireframe",
        "blocker": "",
        "deadline": "2026-10-15",
        "estimated_effort_minutes": 120,
        "energy_required": "high",
        "definition_of_done": "Wireframe reviewed",
        "source_updated_at": "2026-10-03T12:00:00+00:00",
    }


def _stale_scholar():
    return {
        "schema_version": "scholar_handoff.v1",
        "agent_id": "scholar",
        "current_batch_id": "batch-42",
        "exact_action": "Read CCRN3 chapter 5",
        "estimated_minutes": 60,
        "definition_of_done": "Chapter 5 notes written",
        "reading_target": {
            "required": True,
            "article_title": "CRRN3 Deep Dive",
            "exact_sections_to_read": ["section 5.1"],
            "extraction_goal": "extract key definitions",
        },
        "source_refs": ["https://example.com/crrn3"],
        "source_updated_at": "2026-10-01T12:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Scenario 1: All sources healthy → complete brief
# ---------------------------------------------------------------------------

class TestAllHealthy:
    def test_complete_status_with_all_domains(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
            "growth": lambda agent_id, state=None: _fresh_growth(),
            "projects": lambda agent_id, state=None: _fresh_project(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.overall_status == OverallStatus.COMPLETE.value
        assert result.brief is not None
        assert result.brief["schema_version"] == "daily_command_brief.v1"
        assert result.conflicts == []
        assert result.missing_domains == []
        assert result.persistence_unavailable is False

    def test_all_stages_logged(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
            "growth": lambda agent_id, state=None: _fresh_growth(),
            "projects": lambda agent_id, state=None: _fresh_project(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        stage_names = [s["stage"] for s in result.stages]
        assert "rhythm_refresh" in stage_names
        assert "freshness_check" in stage_names
        assert "synthesis" in stage_names
        assert "persist" in stage_names

    def test_no_missing_domains_when_all_healthy(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.missing_domains == []


# ---------------------------------------------------------------------------
# Scenario 2: One agent unavailable → degraded, skip domain, mark missing
# ---------------------------------------------------------------------------

class TestOneAgentUnavailable:
    def test_scholar_unavailable_marks_missing_and_degraded(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: (_ for _ in ()).throw(
                RuntimeError("refresh unavailable: no producer configured for agent scholar")
            ),
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.overall_status == OverallStatus.DEGRADED.value
        assert "scholar" in result.missing_domains
        assert result.brief is not None

    def test_growth_unavailable_still_produces_valid_brief(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
            "growth": lambda agent_id, state=None: (_ for _ in ()).throw(
                RuntimeError("refresh unavailable: no producer configured for agent growth")
            ),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.overall_status == OverallStatus.DEGRADED.value
        assert "growth" in result.missing_domains
        assert result.brief is not None

    def test_stage_logs_show_unavailable_status(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: (_ for _ in ()).throw(
                RuntimeError("refresh unavailable")
            ),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        scholar_stage = [s for s in result.stages if s["stage"] == "scholar_refresh"]
        assert len(scholar_stage) == 1
        assert scholar_stage[0]["status"] == "unavailable"


# ---------------------------------------------------------------------------
# Scenario 3: Supabase unavailable → persistence_unavailable, no SQLite fallback
# ---------------------------------------------------------------------------

class TestSupabaseUnavailable:
    def test_persistence_unavailable_flag_set(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        mock_persistence = MagicMock()
        mock_persistence.write.side_effect = PersistenceUnavailable("Supabase unreachable")

        result = run_morning_pipeline(
            planning_date="2026-10-03",
            persistence=mock_persistence,
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.persistence_unavailable is True
        assert result.overall_status == OverallStatus.DEGRADED.value

    def test_no_sqlite_fallback(self):
        """When Supabase is unavailable, there is no SQLite fallback —
        persistence_unavailable is set and the brief is still produced."""
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
        }
        mock_persistence = MagicMock()
        mock_persistence.write.side_effect = PersistenceUnavailable("Connection refused")

        result = run_morning_pipeline(
            planning_date="2026-10-03",
            persistence=mock_persistence,
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.persistence_unavailable is True
        # Brief still produced — no SQLite fallback
        assert result.brief is not None
        assert result.brief["schema_version"] == "daily_command_brief.v1"

    def test_persist_stage_logs_unavailable(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
        }
        mock_persistence = MagicMock()
        mock_persistence.write.side_effect = PersistenceUnavailable("Supabase down")

        result = run_morning_pipeline(
            planning_date="2026-10-03",
            persistence=mock_persistence,
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        persist_stage = [s for s in result.stages if s["stage"] == "persist"]
        assert len(persist_stage) == 1
        assert persist_stage[0]["status"] == "persistence_unavailable"


# ---------------------------------------------------------------------------
# Scenario 4: Stale Scholar → Scholar-only targeted refresh
# ---------------------------------------------------------------------------

class TestStaleScholar:
    def test_refresh_plan_targets_only_scholar(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _stale_scholar(),
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        # Freshness check stage should list scholar as needing refresh
        freshness_stage = [s for s in result.stages if s["stage"] == "freshness_check"][0]
        assert "scholar" in freshness_stage["details"].get("domains_to_refresh", [])

    def test_stale_scholar_refreshed_if_producer_succeeds(self):
        fresh_scholar_after_refresh = _fresh_scholar()

        def scholar_producer(agent_id, state=None):
            return fresh_scholar_after_refresh

        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": scholar_producer,
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        # Scholar should have been refreshed (not in missing_domains)
        assert "scholar" not in result.missing_domains
        assert result.overall_status == OverallStatus.COMPLETE.value

    def test_stale_scholar_unavailable_returns_degraded(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: (_ for _ in ()).throw(
                RuntimeError("refresh unavailable")
            ),
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert "scholar" in result.missing_domains
        assert result.overall_status == OverallStatus.DEGRADED.value


# ---------------------------------------------------------------------------
# Scenario 5: Schedule conflict returned by producer → conflict surfaced
# ---------------------------------------------------------------------------

class TestScheduleConflict:
    def _conflict_producer(self, agent_id, state=None):
        return {
            "schema_version": "rhythm_schedule_conflict.v1",
            "agent_id": "tola",
            "outcome_id": "outcome-1",
            "reason": "overlap",
            "required_minutes": 90,
            "available_minutes": 30,
            "possible_alternatives": ["split_task", "reduce_scope", "defer"],
        }

    def test_conflict_surfaced_in_result(self):
        producers = {
            "rhythm": self._conflict_producer,
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
            "growth": lambda agent_id, state=None: _fresh_growth(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert len(result.conflicts) > 0
        conflict = result.conflicts[0]
        assert conflict["schema_version"] == "rhythm_schedule_conflict.v1"
        assert conflict["reason"] == "overlap"

    def test_conflict_never_silently_dropped(self):
        """Conflict must be surfaced for Tola resolution, never silently dropped."""
        producers = {
            "rhythm": self._conflict_producer,
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert len(result.conflicts) > 0
        # The conflict should appear in stage logs too
        conflict_stages = [s for s in result.stages if "conflict" in s["stage"]]
        assert len(conflict_stages) > 0

    def test_degraded_when_conflict_present(self):
        producers = {
            "rhythm": self._conflict_producer,
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.overall_status == OverallStatus.DEGRADED.value


# ---------------------------------------------------------------------------
# Envelope validation
# ---------------------------------------------------------------------------

class TestEnvelopeValidation:
    def test_result_has_all_required_fields(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
            "scholar": lambda agent_id, state=None: _fresh_scholar(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        validated = result.validate()
        for field in MorningPipelineResult.REQUIRED:
            assert field in validated

    def test_overall_status_is_valid_enum(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.overall_status in {e.value for e in OverallStatus}

    def test_stages_contain_required_keys(self):
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        for stage in result.stages:
            assert "stage" in stage
            assert "status" in stage
            assert "refresh_reason" in stage


# ---------------------------------------------------------------------------
# Default producers (honest-failure stubs)
# ---------------------------------------------------------------------------

class TestDefaultProducers:
    def test_default_producers_raise_honestly(self):
        """When no producers are provided, default stubs raise RuntimeError."""
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            now="2026-10-03T13:00:00+00:00",
        )
        assert result.overall_status == OverallStatus.FAILED.value
        assert "rhythm" in result.missing_domains
        assert len(result.conflicts) == 0

    def test_injectable_producers_used(self):
        """Injectable producers override defaults."""
        producers = {
            "rhythm": lambda agent_id, state=None: _fresh_capacity(),
        }
        result = run_morning_pipeline(
            planning_date="2026-10-03",
            producers=producers,
            now="2026-10-03T13:00:00+00:00",
        )
        # rhythm was refreshed successfully, but scholar/growth/projects are missing
        assert "rhythm" not in result.missing_domains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])