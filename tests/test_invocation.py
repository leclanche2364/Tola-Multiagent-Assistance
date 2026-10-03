"""Batch 8 QA tests for natural-language invocation router and
run_daily_synthesis orchestrator.

Covers: intent routing (all five phrasing groups), degraded mode,
stale Scholar refresh, one agent unavailable, Supabase unavailable,
unknown input, and proposal-mode flag.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.daily_synthesis.invocation import (
    Intent,
    IntentResult,
    route_intent,
    run_daily_synthesis,
    refresh_unavailable_stub,
)
from agents.daily_synthesis.persistence import PersistenceUnavailable
from agents.daily_synthesis.freshness import FreshnessStatus


# ---------------------------------------------------------------------------
# Fixture handoffs
# ---------------------------------------------------------------------------

def _capacity(total=240, used=60, buffer=30, source_updated_at=None):
    h = {
        "schema_version": "rhythm_capacity_handoff.v1",
        "agent_id": "tola",
        "rhythm_id": "r1",
        "capacity_used_minutes": used,
        "capacity_total_minutes": total,
        "recovery_buffer_minutes": buffer,
    }
    if source_updated_at is not None:
        h["source_updated_at"] = source_updated_at
    return h


def _scholar(exact_action="Read CCRN3 chapter 5", estimated_minutes=60, source_updated_at=None):
    h = {
        "schema_version": "scholar_handoff.v1",
        "agent_id": "scholar",
        "current_batch_id": "batch-42",
        "exact_action": exact_action,
        "estimated_minutes": estimated_minutes,
        "definition_of_done": "Chapter 5 notes written",
        "reading_target": {
            "required": True,
            "article_title": "CRRN3 Deep Dive",
            "exact_sections_to_read": ["section 5.1"],
            "extraction_goal": "extract key definitions",
        },
        "source_refs": ["https://example.com/crrn3"],
    }
    if source_updated_at is not None:
        h["source_updated_at"] = source_updated_at
    return h


def _growth(next_actions=None, source_updated_at=None):
    h = {
        "schema_version": "growth_handoff.v1",
        "agent_id": "growth",
        "project_id": "growth",
        "action": "growth_handoff",
        "estimated_minutes": 150,
        "definition_of_done": "Growth handoff produced",
        "next_actions": next_actions or [
            {"action": "Finalize analysis", "estimated_effort_minutes": 60},
        ],
        "blockers": [],
        "deadlines": [],
    }
    if source_updated_at is not None:
        h["source_updated_at"] = source_updated_at
    return h


def _project(project_id="Shiftlyx", next_action="Complete wireframe", source_updated_at=None):
    h = {
        "schema_version": "project_status_handoff.v1",
        "agent_id": "tola",
        "project_id": project_id,
        "status": "development",
        "summary": f"{project_id}: development",
        "next_action": next_action,
        "blocker": "",
        "deadline": "2026-10-15",
        "estimated_effort_minutes": 120,
        "energy_required": "high",
        "definition_of_done": "Wireframe reviewed",
    }
    if source_updated_at is not None:
        h["source_updated_at"] = source_updated_at
    return h


# ---------------------------------------------------------------------------
# Intent Router Tests
# ---------------------------------------------------------------------------


class TestPlanTodayPhrasings:
    """All five phrasing groups for plan_today route to the same intent."""

    @pytest.mark.parametrize(
        "command",
        [
            "plan today",
            "today's plan",
            "what should i do today",
            "plan my day",
            "sort today out",
            "what's on my plate today",
            "give me today's plan",
            "what should i work on today",
            "today's schedule",
            "plan for today",
            "today agenda",
            "today",
        ],
    )
    def test_routes_to_plan_today(self, command):
        result = route_intent(command)
        assert result.intent == Intent.PLAN_TODAY


class TestPlanTomorrowPhrasings:
    """All phrasings for plan_tomorrow route correctly."""

    @pytest.mark.parametrize(
        "command",
        [
            "plan tomorrow",
            "tomorrow's plan",
            "what should i do tomorrow",
            "plan for tomorrow",
            "tomorrow plan",
            "tomorrow's schedule",
            "tomorrow agenda",
            "tomorrow",
        ],
    )
    def test_routes_to_plan_tomorrow(self, command):
        result = route_intent(command)
        assert result.intent == Intent.PLAN_TOMORROW


class TestRefreshPlanPhrasings:
    """All phrasings for refresh_plan route correctly."""

    @pytest.mark.parametrize(
        "command",
        [
            "refresh my plan",
            "update plan",
            "replan",
            "refresh today",
            "regenerate plan",
            "new plan",
            "refresh",
            "rebuild plan",
            "refresh plan",
            "new daily plan",
            "refresh everything",
        ],
    )
    def test_routes_to_refresh_plan(self, command):
        result = route_intent(command)
        assert result.intent == Intent.REFRESH_PLAN


class TestWhatShouldIWorkOnPhrasings:
    """All phrasings for what_should_i_work_on route correctly."""

    @pytest.mark.parametrize(
        "command",
        [
            "what should i work on",
            "what's my priority",
            "what's next",
            "what should i focus on",
            "what's the most important thing",
            "what should i do now",
            "what's my next action",
            "what should i tackle",
            "what's the priority",
            "what's first",
            "what should i do",
            "what comes next",
            "what's the best use of my time",
            "where should i focus",
            "what's my focus",
            "what should i prioritize",
        ],
    )
    def test_routes_to_work_on(self, command):
        result = route_intent(command)
        assert result.intent == Intent.WHAT_SHOULD_I_WORK_ON


class TestCapacityLimitedPlanPhrasings:
    """All phrasings for capacity_limited_plan route correctly."""

    @pytest.mark.parametrize(
        "command",
        [
            "i only have a couple of hours, sort today out",
            "short on time",
            "limited capacity",
            "only a few hours",
            "i'm short on time",
            "quick plan",
            "couple of hours",
            "limited time",
            "tight schedule",
            "not much time",
            "i only have an hour",
            "barely any time",
            "only a couple of hours",
            "just a couple of hours",
            "a couple of hours",
        ],
    )
    def test_routes_to_capacity_limited(self, command):
        result = route_intent(command)
        assert result.intent == Intent.CAPACITY_LIMITED_PLAN


class TestUnknownInput:
    """Unknown input returns unknown intent, never a guessed run."""

    def test_empty_string_is_unknown(self):
        result = route_intent("")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == "low"

    def test_whitespace_only_is_unknown(self):
        result = route_intent("   ")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == "low"

    def test_gibberish_is_unknown(self):
        result = route_intent("asdfghjkl")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == "low"

    def test_random_text_is_unknown(self):
        result = route_intent("the quick brown fox jumps")
        assert result.intent == Intent.UNKNOWN
        assert result.confidence == "low"


class TestCapacityHintUpgrade:
    """Capacity-limited language upgrades plan_today / work_on to capacity_limited_plan."""

    def test_couple_of_hours_upgrades_plan_today(self):
        result = route_intent("i only have a couple of hours, plan today")
        assert result.intent == Intent.CAPACITY_LIMITED_PLAN
        assert result.parameters.get("capacity_hint") == "limited"

    def test_short_on_time_upgrades_work_on(self):
        result = route_intent("short on time, what should i work on")
        assert result.intent == Intent.CAPACITY_LIMITED_PLAN
        assert result.parameters.get("capacity_hint") == "limited"

    def test_no_capacity_hint_stays_plan_today(self):
        result = route_intent("plan today")
        assert result.intent == Intent.PLAN_TODAY
        assert "capacity_hint" not in result.parameters


class TestRouterWorksWithShortCommand:
    """Router works with a single short command string — no long prompt needed."""

    def test_single_word_capacity_hint(self):
        result = route_intent("sort today out")
        assert result.intent == Intent.PLAN_TODAY

    def test_short_refresh(self):
        result = route_intent("refresh")
        assert result.intent == Intent.REFRESH_PLAN

    def test_short_work_on(self):
        result = route_intent("what's next")
        assert result.intent == Intent.WHAT_SHOULD_I_WORK_ON


# ---------------------------------------------------------------------------
# run_daily_synthesis Tests
# ---------------------------------------------------------------------------


class TestNormalPipeline:
    """Full pipeline with handoffs provided directly."""

    def test_returns_valid_brief(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
                "projects": _project(),
            },
        )
        assert result["schema_version"] == "daily_command_brief.v1"
        assert isinstance(result["top_outcomes"], list)
        assert isinstance(result["not_today"], list)
        assert result["proposal_mode"] is True
        assert result["decision_metadata"]["auto_scheduling"] is False

    def test_proposal_mode_flag(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
        )
        assert result["proposal_mode"] is True


class TestOneAgentUnavailable:
    """One agent unavailable → degraded but valid result."""

    def test_missing_scholar_still_produces_brief(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "growth": _growth(),
                "projects": _project(),
            },
        )
        # Should still produce a valid brief with defaults for missing scholar
        assert result["schema_version"] == "daily_command_brief.v1"
        assert isinstance(result["top_outcomes"], list)

    def test_missing_growth_still_produces_brief(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "projects": _project(),
            },
        )
        assert result["schema_version"] == "daily_command_brief.v1"
        assert isinstance(result["top_outcomes"], list)

    def test_missing_projects_still_produces_brief(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
        )
        assert result["schema_version"] == "daily_command_brief.v1"


class TestSupabaseUnavailableNoHandoffs:
    """Supabase unavailable + no in-memory handoffs → explicit incomplete status."""

    def test_returns_incomplete_listing_missing(self):
        mock_persistence = MagicMock()
        mock_persistence.read.side_effect = PersistenceUnavailable(
            "Connection refused"
        )

        result = run_daily_synthesis(
            planning_window="2026-10-03",
            persistence=mock_persistence,
        )

        assert result["status"] == "incomplete"
        assert "handoffs" in result["missing"]
        assert result["decision_metadata"]["persistence_status"] == "persistence_unavailable"
        assert result["top_outcomes"] == []

    def test_no_sqlite_fallback(self):
        mock_persistence = MagicMock()
        mock_persistence.read.side_effect = PersistenceUnavailable(
            "Connection refused"
        )

        result = run_daily_synthesis(
            planning_window="2026-10-03",
            persistence=mock_persistence,
        )

        # No SQLite fallback — only persistence_unavailable
        assert result["decision_metadata"]["persistence_status"] == "persistence_unavailable"


class TestSupabaseUnavailableWithInMemoryHandoffs:
    """Supabase unavailable but handoffs in memory → proceed, mark degraded."""

    def test_proceeds_with_in_memory_handoffs(self):
        mock_persistence = MagicMock()
        mock_persistence.read.side_effect = PersistenceUnavailable(
            "Connection refused"
        )

        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
            persistence=mock_persistence,
        )

        assert result["schema_version"] == "daily_command_brief.v1"
        assert result["decision_metadata"]["persistence_status"] == "persistence_unavailable"
        assert isinstance(result["top_outcomes"], list)


class TestStaleScholarRefresh:
    """Stale Scholar state → targeted Scholar-only refresh in the refresh plan."""

    def test_refresh_plan_targets_only_scholar(self):
        stale_scholar = _scholar(source_updated_at="2026-10-01T12:00:00+00:00")

        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(source_updated_at="2026-10-03T10:00:00+00:00"),
                "scholar": stale_scholar,
                "growth": _growth(source_updated_at="2026-10-03T10:00:00+00:00"),
                "projects": _project(source_updated_at="2026-10-03T10:00:00+00:00"),
            },
        )

        refresh_plan = result["decision_metadata"]["refresh_plan"]
        assert "scholar" in refresh_plan.get("domains_to_refresh", [])
        assert "rhythm" not in refresh_plan.get("domains_to_refresh", [])
        assert "growth" not in refresh_plan.get("domains_to_refresh", [])

    def test_refresh_plan_targets_only_stale_domains(self):
        stale_rhythm = _capacity(source_updated_at="2026-10-01T12:00:00+00:00")

        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": stale_rhythm,
                "scholar": _scholar(source_updated_at="2026-10-03T10:00:00+00:00"),
                "growth": _growth(source_updated_at="2026-10-03T10:00:00+00:00"),
            },
        )

        refresh_plan = result["decision_metadata"]["refresh_plan"]
        assert "rhythm" in refresh_plan.get("domains_to_refresh", [])
        assert "scholar" not in refresh_plan.get("domains_to_refresh", [])


class TestRefreshUnavailableStub:
    """refresh_unavailable_stub raises RuntimeError — honest failure."""

    def test_stub_raises_runtime_error(self):
        with pytest.raises(RuntimeError):
            refresh_unavailable_stub("agent-1")

    def test_stub_never_fabricates(self):
        with pytest.raises(RuntimeError):
            refresh_unavailable_stub("agent-1", state={"key": "value"})


class TestNoLongPromptRequired:
    """Router works with a single short command string."""

    def test_short_command_routes(self):
        result = route_intent("plan today")
        assert result.intent == Intent.PLAN_TODAY

    def test_two_word_command_routes(self):
        result = route_intent("refresh plan")
        assert result.intent == Intent.REFRESH_PLAN


class TestDegradedWithPartialHandoffs:
    """One agent unavailable → degraded but valid result."""

    def test_only_rhythm_and_growth_still_valid(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "growth": _growth(),
            },
        )
        assert result["schema_version"] == "daily_command_brief.v1"
        assert isinstance(result["top_outcomes"], list)


class TestProposalMode:
    """Output is a proposal by default; auto-scheduling NOT implemented."""

    def test_proposal_mode_true(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
        )
        assert result["proposal_mode"] is True

    def test_auto_scheduling_false(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
        )
        assert result["decision_metadata"]["auto_scheduling"] is False


class TestCapacityHintInMetadata:
    """Capacity hint from intent routing appears in decision metadata."""

    def test_capacity_hint_passed_through(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            capacity_hint=120,
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
        )
        assert result["schema_version"] == "daily_command_brief.v1"
        assert isinstance(result["top_outcomes"], list)


class TestNoFabricationOnMissingHandoffs:
    """When no handoffs at all, returns explicit incomplete — never fabricates."""

    def test_empty_handoffs_returns_incomplete(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={},
        )
        assert result["status"] == "incomplete"
        assert "handoffs" in result["missing"]

    def test_none_handoffs_no_persistence_returns_incomplete(self):
        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs=None,
            persistence=None,
        )
        assert result["status"] == "incomplete"
        assert "handoffs" in result["missing"]


class TestPersistenceNoOpWhenUnavailable:
    """Persistence write is no-op-safe when unavailable."""

    def test_write_failure_does_not_crash(self):
        mock_persistence = MagicMock()
        mock_persistence.write.return_value = {
            "status": "persistence_unavailable",
        }

        result = run_daily_synthesis(
            planning_window="2026-10-03",
            handoffs={
                "rhythm": _capacity(),
                "scholar": _scholar(),
                "growth": _growth(),
            },
            persistence=mock_persistence,
        )

        # Synthesis still succeeds despite persistence failure
        assert result["schema_version"] == "daily_command_brief.v1"
        mock_persistence.write.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])