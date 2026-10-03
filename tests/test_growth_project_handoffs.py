"""Batch 4 QA tests for growth_handoff and project_status_handoff producers.

Covers: fresh state, stale state, missing state (marked unknown, never
fabricated), blocker present, deadline present, no next action (valid
empty handoff), completed milestone progression, and parked-project
exclusion (Y-Site injection attempt must be rejected/omitted).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the repo root is on sys.path so imports resolve
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.daily_synthesis.contracts import (
    GrowthHandoff,
    ProjectStatusHandoff,
    ValidationError,
    validate_payload,
)
from agents.daily_synthesis.growth_handoff import produce_growth_handoff
from agents.daily_synthesis.project_status_handoff import (
    ACTIVE_PROJECTS,
    PARKED_PROJECTS,
    produce_project_status_handoff,
)

FIXTURES = Path(__file__).resolve().parent.parent / "agents" / "daily_synthesis" / "fixtures"


# ---------------------------------------------------------------------------
# Growth handoff — fresh state
# ---------------------------------------------------------------------------

class TestGrowthFreshState:
    def test_growth_fresh_validates(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_fresh.json",
        )
        assert result["schema_version"] == "growth_handoff.v1"
        assert result["agent_id"] == "tola"
        assert result["project_id"] == "growth"
        assert result["data_freshness"]["overall_status"] == "fresh"
        assert len(result["next_actions"]) == 2
        assert result["next_actions"][0]["freshness_status"] == "fresh"

    def test_growth_fresh_contract_validates(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_fresh.json",
        )
        validated = validate_payload(result)
        assert validated["schema_version"] == "growth_handoff.v1"


# ---------------------------------------------------------------------------
# Growth handoff — stale state
# ---------------------------------------------------------------------------

class TestGrowthStaleState:
    def test_growth_stale_marks_overall_stale(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_stale.json",
        )
        assert result["data_freshness"]["overall_status"] == "stale"
        assert result["data_freshness"]["metrics_freshness"] == "stale"

    def test_growth_stale_contract_validates(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_stale.json",
        )
        validated = validate_payload(result)
        assert validated["schema_version"] == "growth_handoff.v1"


# ---------------------------------------------------------------------------
# Growth handoff — missing state (unknown, never fabricated)
# ---------------------------------------------------------------------------

class TestGrowthMissingState:
    def test_growth_missing_marks_unknown(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_missing.json",
        )
        assert result["data_freshness"]["overall_status"] == "unknown"
        assert result["data_freshness"]["metrics_freshness"] == "unknown"
        assert result["latest_metrics"]["revenue"] is None
        assert result["latest_metrics"]["mrr"] is None
        assert result["active_experiments"] == []
        assert result["awaiting_analysis"] == []
        assert result["execution_tasks"] == []
        assert result["blockers"] == []
        assert result["deadlines"] == []
        assert result["next_actions"] == []

    def test_growth_missing_never_fabricates_fields(self):
        """Missing state must not fabricate values — all optional fields stay None/empty."""
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_missing.json",
        )
        assert result["latest_metrics"]["revenue"] is None
        assert result["latest_metrics"]["active_users"] is None
        # Contract requires estimated_minutes > 0; empty handoffs get minimum 1
        assert result["estimated_minutes"] == 1
        assert result["action"] == ""


# ---------------------------------------------------------------------------
# Growth handoff — blocker present
# ---------------------------------------------------------------------------

class TestGrowthBlockerPresent:
    def test_growth_blocker_passes_through(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_blocker.json",
        )
        assert len(result["blockers"]) == 1
        assert "API rate limit" in result["blockers"][0]
        assert result["next_actions"] == []

    def test_growth_blocker_contract_validates(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_blocker.json",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Growth handoff — deadline present
# ---------------------------------------------------------------------------

class TestGrowthDeadlinePresent:
    def test_growth_deadline_passes_through(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_deadline.json",
        )
        assert len(result["deadlines"]) == 1
        assert "campaign deadline" in result["deadlines"][0]
        assert len(result["next_actions"]) == 1

    def test_growth_deadline_contract_validates(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_deadline.json",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Growth handoff — no next action (valid empty handoff)
# ---------------------------------------------------------------------------

class TestGrowthNoNextAction:
    def test_growth_empty_next_actions_valid(self):
        """A handoff with no next actions is a valid empty handoff."""
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_no_next_action.json",
        )
        assert result["next_actions"] == []
        assert result["action"] == ""
        # Contract requires estimated_minutes > 0; empty handoffs get minimum 1
        assert result["estimated_minutes"] == 1
        # Contract fields still present and valid
        assert result["schema_version"] == "growth_handoff.v1"
        assert result["agent_id"] == "tola"

    def test_growth_empty_contract_validates(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_no_next_action.json",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Growth handoff — completed milestone progression
# ---------------------------------------------------------------------------

class TestGrowthCompletedMilestone:
    def test_growth_milestone_progression(self):
        result = produce_growth_handoff(
            agent_id="tola",
            source=FIXTURES / "growth_completed_milestone.json",
        )
        assert len(result["active_experiments"]) == 1
        assert result["active_experiments"][0]["name"] == "onboarding_flow_v3"
        assert result["next_actions"][0]["action"] == "Begin next experiment: pricing_page_v2"
        assert result["data_freshness"]["overall_status"] == "fresh"


# ---------------------------------------------------------------------------
# Growth handoff — cross-domain rejection (Tola decides priority)
# ---------------------------------------------------------------------------

class TestGrowthCrossDomainRejection:
    def test_cross_domain_action_rejected(self):
        """Module must not rank cross-domain; only within growth domain."""
        bad_state = {
            "latest_metrics": {},
            "active_experiments": [],
            "awaiting_analysis": [],
            "execution_tasks": [],
            "blockers": [],
            "deadlines": [],
            "next_actions": [
                {
                    "action": "Write scholar article on CCRN3",
                    "estimated_effort_minutes": 30,
                    "freshness_status": "fresh",
                    "domain": "scholar",
                }
            ],
        }
        with pytest.raises(ValidationError, match="cross-domain"):
            produce_growth_handoff(agent_id="tola", source=bad_state)


# ---------------------------------------------------------------------------
# Project status handoff — fresh state
# ---------------------------------------------------------------------------

class TestProjectFreshState:
    def test_project_fresh_validates(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_fresh.json",
            project_id="Shiftlyx",
        )
        assert result["schema_version"] == "project_status_handoff.v1"
        assert result["project_id"] == "Shiftlyx"
        assert result["current_phase"] == "development"
        assert result["freshness_status"] == "fresh"
        assert result["next_action"] == "Complete dashboard wireframe review"

    def test_project_fresh_contract_validates(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_fresh.json",
            project_id="Shiftlyx",
        )
        validated = validate_payload(result)
        assert validated["schema_version"] == "project_status_handoff.v1"


# ---------------------------------------------------------------------------
# Project status handoff — stale state
# ---------------------------------------------------------------------------

class TestProjectStaleState:
    def test_project_stale_marks_freshness(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_stale.json",
            project_id="Shiftlyx",
        )
        assert result["freshness_status"] == "stale"
        assert result["current_phase"] == "stalled"
        assert result["blocker"] == "Waiting on vendor API deprecation decision"

    def test_project_stale_contract_validates(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_stale.json",
            project_id="Shiftlyx",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Project status handoff — missing state (unknown, never fabricated)
# ---------------------------------------------------------------------------

class TestProjectMissingState:
    def test_project_missing_marks_unknown(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_missing.json",
            project_id="Shiftlyx",
        )
        assert result["current_phase"] == "unknown"
        assert result["freshness_status"] == "unknown"
        assert result["latest_completed_milestone"] == ""
        assert result["next_action"] == ""
        assert result["estimated_effort_minutes"] == 0
        # No fabricated values — all defaults are empty/zero/unknown

    def test_project_missing_contract_validates(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_missing.json",
            project_id="Shiftlyx",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Project status handoff — blocker present
# ---------------------------------------------------------------------------

class TestProjectBlockerPresent:
    def test_project_blocker_passes_through(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_blocker.json",
            project_id="Shiftlyx",
        )
        assert "Design team blocked" in result["blocker"]
        assert result["next_action"] == ""

    def test_project_blocker_contract_validates(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_blocker.json",
            project_id="Shiftlyx",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Project status handoff — deadline present
# ---------------------------------------------------------------------------

class TestProjectDeadlinePresent:
    def test_project_deadline_passes_through(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_deadline.json",
            project_id="Shiftlyx",
        )
        assert result["deadline"] == "2026-10-15"
        assert result["next_action"] == "Complete dashboard wireframe review"

    def test_project_deadline_contract_validates(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_deadline.json",
            project_id="Shiftlyx",
        )
        validate_payload(result)


# ---------------------------------------------------------------------------
# Project status handoff — no next action (valid empty handoff)
# ---------------------------------------------------------------------------

class TestProjectNoNextAction:
    def test_project_empty_next_action_valid(self):
        """A project handoff with no next action is valid."""
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_blocker.json",
            project_id="Shiftlyx",
        )
        assert result["next_action"] == ""
        assert result["schema_version"] == "project_status_handoff.v1"


# ---------------------------------------------------------------------------
# Project status handoff — completed milestone progression
# ---------------------------------------------------------------------------

class TestProjectCompletedMilestone:
    def test_project_milestone_progression(self):
        result = produce_project_status_handoff(
            agent_id="tola",
            source=FIXTURES / "projects_fresh.json",
            project_id="Shiftlyx",
        )
        assert result["latest_completed_milestone"] == "v2.4 API integration"
        assert result["current_phase"] == "development"
        assert result["current_work_in_progress"] == "Dashboard redesign"


# ---------------------------------------------------------------------------
# Project status handoff — parked-project exclusion (Y-Site injection)
# ---------------------------------------------------------------------------

class TestParkedProjectExclusion:
    def test_y_site_injection_rejected(self):
        """Y-Site IV Compatibility Checker is PARKED — must raise ValidationError."""
        with pytest.raises(ValidationError, match="PARKED"):
            produce_project_status_handoff(
                agent_id="tola",
                source=FIXTURES / "projects_parked_injection.json",
                project_id="Y-Site IV Compatibility Checker",
            )

    def test_y_site_not_in_active_registry(self):
        """Y-Site must not be in ACTIVE_PROJECTS."""
        assert "Y-Site IV Compatibility Checker" not in ACTIVE_PROJECTS

    def test_y_site_not_in_parked_registry_excluded_from_output(self):
        """Even if fixture contains Y-Site data, it must never appear in output."""
        # Attempting to produce for a parked project raises before any output
        with pytest.raises(ValidationError, match="PARKED"):
            produce_project_status_handoff(
                agent_id="tola",
                source=FIXTURES / "projects_parked_injection.json",
                project_id="Y-Site IV Compatibility Checker",
            )

    def test_valid_project_not_parked(self):
        """Active projects should work fine."""
        for project in ACTIVE_PROJECTS:
            # Just verify the project is accepted (may fail on missing fixture,
            # but should NOT raise a PARKED error)
            try:
                produce_project_status_handoff(
                    agent_id="tola",
                    source=FIXTURES / "projects_fresh.json",
                    project_id=project,
                )
            except FileNotFoundError:
                # Fixture may not have this project — that's fine, not a PARKED error
                pass


# ---------------------------------------------------------------------------
# Registry integrity tests
# ---------------------------------------------------------------------------

class TestRegistryIntegrity:
    def test_active_projects_contains_expected(self):
        assert "Shiftlyx" in ACTIVE_PROJECTS
        assert "Revalidation Copilot" in ACTIVE_PROJECTS
        assert "VocalGaze" in ACTIVE_PROJECTS
        assert "IntenSIQ" in ACTIVE_PROJECTS
        assert "OpenClaw agent system" in ACTIVE_PROJECTS
        assert "Florence" in ACTIVE_PROJECTS
        assert "ICU/QI work" in ACTIVE_PROJECTS

    def test_parked_projects_excluded(self):
        assert "Y-Site IV Compatibility Checker" in PARKED_PROJECTS

    def test_no_overlap_between_active_and_parked(self):
        assert ACTIVE_PROJECTS.isdisjoint(PARKED_PROJECTS)

    def test_all_active_projects_are_valid_ids(self):
        for project in ACTIVE_PROJECTS:
            result = produce_project_status_handoff(
                agent_id="tola",
                source=FIXTURES / "projects_fresh.json",
                project_id=project,
            )
            assert result["schema_version"] == "project_status_handoff.v1"
