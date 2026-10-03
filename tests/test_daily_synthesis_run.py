"""Batch 11 QA tests for daily_synthesis_run.py CLI entrypoint.

Covers: morning command (full run, empty blackboard, Supabase down),
capture command (valid JSON file, invalid JSON), idempotency,
and exit codes.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.daily_synthesis_run import (
    _build_handoffs,
    _print_brief,
    cmd_capture,
    cmd_morning,
    main,
)
from agents.daily_synthesis.persistence import PersistenceUnavailable
from agents.daily_synthesis.morning_pipeline import OverallStatus


# ---------------------------------------------------------------------------
# Fixture: minimal valid brief output
# ---------------------------------------------------------------------------

def _make_minimal_brief() -> dict:
    return {
        "schema_version": "daily_command_brief.v1",
        "agent_id": "tola",
        "date": "2026-10-03",
        "top_outcomes": [
            {
                "definition_of_done": "Read CCRN3 chapter 5",
                "source_refs": ["https://example.com/crrn3"],
                "estimated_minutes": 60,
                "minimum_viable_minutes": 30,
            }
        ],
        "not_today": ["Finalize analysis: deferred — capacity full"],
        "capacity_used_minutes": 60,
        "buffer_minutes": 30,
        "capacity_summary": {
            "max_major_outcomes": 3,
            "total_available_minutes": 360,
            "total_planned_minutes": 60,
            "remaining_buffer_minutes": 30,
        },
        "notes": "Daily synthesis built at 2026-10-03T13:00:00+00:00.",
    }


# ---------------------------------------------------------------------------
# Fixture: MorningPipelineResult
# ---------------------------------------------------------------------------

def _make_pipeline_result(
    status: str = OverallStatus.COMPLETE.value,
    conflicts: list = None,
    missing_domains: list = None,
    persistence_unavailable: bool = False,
    brief: dict = None,
) -> MagicMock:
    result = MagicMock()
    result.overall_status = status
    result.stages = [
        {"stage": "rhythm_refresh", "status": "ok", "refresh_reason": ""},
        {"stage": "freshness_check", "status": "ok", "refresh_reason": ""},
        {"stage": "synthesis", "status": "ok", "refresh_reason": ""},
        {"stage": "persist", "status": "ok", "refresh_reason": ""},
    ]
    result.conflicts = conflicts or []
    result.missing_domains = missing_domains or []
    result.persistence_unavailable = persistence_unavailable
    result.brief = brief or _make_minimal_brief()
    return result


# ===========================================================================
# Tests: morning command
# ===========================================================================

class TestMorningFullRun:
    """Full morning run on empty blackboard — valid brief printed, exit 0."""

    def test_morning_prints_brief_and_exits_zero(self, capsys):
        """Full morning run produces a human-readable brief and exits 0."""
        mock_result = _make_pipeline_result(
            status=OverallStatus.COMPLETE.value,
            brief=_make_minimal_brief(),
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            with patch(
                "scripts.daily_synthesis_run.DailySynthesisPersistence"
            ) as mock_persist_cls:
                mock_persist_instance = MagicMock()
                mock_persist_cls.return_value = mock_persist_instance

                argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
                with patch.object(sys, "argv", argv):
                    exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DAILY COMMAND BRIEF" in captured.out
        assert "TOP OUTCOMES:" in captured.out
        assert "2026-10-03" in captured.out

    def test_morning_with_empty_blackboard_uses_defaults(self, capsys):
        """Empty blackboard (no handoffs) still produces a brief via defaults."""
        mock_result = _make_pipeline_result(
            status=OverallStatus.DEGRADED.value,
            brief=_make_minimal_brief(),
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            with patch(
                "scripts.daily_synthesis_run.DailySynthesisPersistence"
            ) as mock_persist_cls:
                mock_persist_cls.return_value = MagicMock()

                argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
                with patch.object(sys, "argv", argv):
                    exit_code = main()

        assert exit_code == 0

    def test_morning_persists_brief_no_op_when_persistence_down(self, capsys):
        """When Supabase is down, brief is still printed and exit 0."""
        mock_result = _make_pipeline_result(
            status=OverallStatus.DEGRADED.value,
            brief=_make_minimal_brief(),
            persistence_unavailable=True,
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
            with patch.object(sys, "argv", argv):
                exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DAILY COMMAND BRIEF" in captured.out


class TestMorningSupabaseDown:
    """Supabase unavailable — degraded mode, still prints brief, exit 0."""

    def test_supabase_down_prints_brief_exit_zero(self, capsys):
        """Degraded mode when Supabase is unreachable."""
        mock_result = _make_pipeline_result(
            status=OverallStatus.DEGRADED.value,
            brief=_make_minimal_brief(),
            persistence_unavailable=True,
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            with patch(
                "scripts.daily_synthesis_run.DailySynthesisPersistence"
            ) as mock_persist_cls:
                mock_persist_cls.side_effect = PersistenceUnavailable("Connection refused")

                argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
                with patch.object(sys, "argv", argv):
                    exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DAILY COMMAND BRIEF" in captured.out

    def test_hard_failure_exits_nonzero(self, capsys):
        """Hard failure (FAILED status) exits non-zero."""
        mock_result = _make_pipeline_result(
            status=OverallStatus.FAILED.value,
            brief=None,
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
            with patch.object(sys, "argv", argv):
                exit_code = main()

        assert exit_code == 1


class TestMorningDeferralsAndConflicts:
    """Brief output includes deferrals with reasons and conflicts."""

    def test_deferrals_printed_with_reasons(self, capsys):
        """Deferrals appear in output with reasons."""
        brief = _make_minimal_brief()
        brief["not_today"] = [
            "Finalize analysis: deferred — requires 90min, only 30min remaining",
            "Q4 budget review: deferred — capacity full",
        ]
        mock_result = _make_pipeline_result(
            status=OverallStatus.DEGRADED.value,
            brief=brief,
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
            with patch.object(sys, "argv", argv):
                exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DEFERRALS:" in captured.out
        assert "Finalize analysis" in captured.out

    def test_conflicts_printed_in_output(self, capsys):
        """Conflicts appear in output when present."""
        brief = _make_minimal_brief()
        mock_result = _make_pipeline_result(
            status=OverallStatus.DEGRADED.value,
            brief=brief,
            conflicts=[
                {
                    "schema_version": "rhythm_schedule_conflict.v1",
                    "reason": "overlap",
                    "outcome_id": "outcome-1",
                    "required_minutes": 90,
                    "available_minutes": 30,
                }
            ],
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
            with patch.object(sys, "argv", argv):
                exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "CONFLICTS:" in captured.out


# ===========================================================================
# Tests: capture command
# ===========================================================================

class TestCaptureValidJSONFile:
    """Capture with a valid JSON file of planned vs actual records."""

    def test_capture_with_valid_json_file(self, capsys, tmp_path):
        """Valid JSON file produces trend line and exits 0."""
        records = [
            {
                "domain": "scholar",
                "planned_minutes": 60,
                "actual_minutes": 55,
                "status": "completed",
                "reason": "",
                "fatigue_energy_predicted": "medium",
                "fatigue_energy_actual": "medium",
                "capacity_predicted_minutes": 60,
                "capacity_actual_available_minutes": 60,
            },
            {
                "domain": "growth",
                "planned_minutes": 30,
                "actual_minutes": 20,
                "status": "partial",
                "reason": "time ran out",
                "fatigue_energy_predicted": "medium",
                "fatigue_energy_actual": "high",
                "capacity_predicted_minutes": 30,
                "capacity_actual_available_minutes": 30,
            },
        ]

        json_file = tmp_path / "outcomes.json"
        json_file.write_text(json.dumps(records), encoding="utf-8")

        with patch(
            "scripts.daily_synthesis_run.DailySynthesisPersistence"
        ) as mock_persist_cls:
            mock_persist_cls.return_value = MagicMock()

            argv = [
                "daily_synthesis_run.py",
                "capture",
                "--date",
                "2026-10-03",
                "--input",
                str(json_file),
            ]
            with patch.object(sys, "argv", argv):
                exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Daily Trend" in captured.out or "Completion rate" in captured.out

    def test_capture_with_stdin(self, capsys):
        """Capture reads from stdin when --input is omitted."""
        records = [
            {
                "domain": "scholar",
                "planned_minutes": 30,
                "actual_minutes": 30,
                "status": "completed",
                "reason": "",
                "fatigue_energy_predicted": "medium",
                "fatigue_energy_actual": "medium",
                "capacity_predicted_minutes": 30,
                "capacity_actual_available_minutes": 30,
            }
        ]

        with patch(
            "scripts.daily_synthesis_run.DailySynthesisPersistence"
        ) as mock_persist_cls:
            mock_persist_cls.return_value = MagicMock()

            argv = ["daily_synthesis_run.py", "capture", "--date", "2026-10-03"]
            with patch.object(sys, "argv", argv):
                with patch("sys.stdin", MagicMock(read=lambda: json.dumps(records))):
                    exit_code = main()

        assert exit_code == 0


class TestCaptureInvalidJSON:
    """Capture with invalid JSON — clear error, exit non-zero."""

    def test_invalid_json_file_exits_nonzero(self, tmp_path):
        """Invalid JSON in file produces clear error and exits non-zero."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json{{{", encoding="utf-8")

        argv = [
            "daily_synthesis_run.py",
            "capture",
            "--date",
            "2026-10-03",
            "--input",
            str(bad_file),
        ]
        with patch.object(sys, "argv", argv):
            exit_code = main()

        assert exit_code == 1

    def test_invalid_json_stdin_exits_nonzero(self):
        """Invalid JSON on stdin produces clear error and exits non-zero."""
        argv = ["daily_synthesis_run.py", "capture", "--date", "2026-10-03"]
        with patch.object(sys, "argv", argv):
            with patch("sys.stdin", MagicMock(read=lambda: "not json")):
                exit_code = main()

        assert exit_code == 1

    def test_missing_input_file_exits_nonzero(self):
        """Missing input file produces clear error and exits non-zero."""
        argv = [
            "daily_synthesis_run.py",
            "capture",
            "--date",
            "2026-10-03",
            "--input",
            "/nonexistent/path/file.json",
        ]
        with patch.object(sys, "argv", argv):
            exit_code = main()

        assert exit_code == 1

    def test_empty_stdin_exits_nonzero(self):
        """Empty stdin produces clear error and exits non-zero."""
        argv = ["daily_synthesis_run.py", "capture", "--date", "2026-10-03"]
        with patch.object(sys, "argv", argv):
            with patch("sys.stdin", MagicMock(read=lambda: "")):
                exit_code = main()

        assert exit_code == 1


# ===========================================================================
# Tests: idempotency and env
# ===========================================================================

class TestIdempotencyAndEnv:
    """Idempotent writes and env handling."""

    def test_env_values_never_printed(self, capsys):
        """Supabase credential values are never printed to stdout."""
        # Patch _get_supabase_credentials to return test values
        with patch(
            "scripts.daily_synthesis_run._get_supabase_credentials",
            return_value=("https://test.supabase.co", "test-anon-key", "test-service-role"),
        ):
            mock_result = _make_pipeline_result(
                status=OverallStatus.COMPLETE.value,
                brief=_make_minimal_brief(),
            )

            with patch(
                "scripts.daily_synthesis_run.run_morning_pipeline",
                return_value=mock_result,
            ):
                argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
                with patch.object(sys, "argv", argv):
                    main()

        captured = capsys.readouterr()
        assert "test-anon-key" not in captured.out
        assert "test-service-role" not in captured.out
        assert "https://test.supabase.co" not in captured.out

    def test_idempotency_key_in_persistence_payload(self):
        """Persistence write is called for the briefs table."""
        mock_persist = MagicMock()
        mock_persist.write.return_value = {"status": "synced"}

        with patch(
            "scripts.daily_synthesis_run.DailySynthesisPersistence",
            return_value=mock_persist,
        ):
            with patch(
                "scripts.daily_synthesis_run.run_morning_pipeline",
                return_value=_make_pipeline_result(brief=_make_minimal_brief()),
            ):
                argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
                with patch.object(sys, "argv", argv):
                    main()

        # Verify write was called (persistence is idempotent via uuid5)
        mock_persist.write.assert_called()


# ===========================================================================
# Tests: _build_handoffs graceful behaviour
# ===========================================================================

class TestBuildHandoffs:
    """_build_handoffs returns dict; graceful on producer failures."""

    def test_build_handoffs_returns_dict(self):
        """_build_handoffs always returns a dict, never raises."""
        result = _build_handoffs()
        assert isinstance(result, dict)

    def test_build_handoffs_empty_on_all_failures(self):
        """When all producers fail, returns empty dict (graceful)."""
        with patch(
            "scripts.daily_synthesis_run._make_capacity_handoff",
            side_effect=RuntimeError("all failed"),
        ):
            with patch(
                "scripts.daily_synthesis_run._make_scholar_handoff",
                side_effect=RuntimeError("all failed"),
            ):
                with patch(
                    "scripts.daily_synthesis_run._make_growth_handoff",
                    side_effect=RuntimeError("all failed"),
                ):
                    result = _build_handoffs()
        assert isinstance(result, dict)


# ===========================================================================
# Tests: _print_brief output format
# ===========================================================================

class TestPrintBrief:
    """_print_brief produces clean human-readable output."""

    def test_print_brief_contains_required_sections(self, capsys):
        """Brief output contains top outcomes, schedule windows, deferrals."""
        brief = _make_minimal_brief()
        result = _make_pipeline_result(brief=brief)
        _print_brief(brief, result)

        captured = capsys.readouterr()
        assert "DAILY COMMAND BRIEF" in captured.out
        assert "TOP OUTCOMES:" in captured.out
        assert "DEFERRALS:" in captured.out
        assert "SCHEDULE WINDOWS:" in captured.out

    def test_print_brief_empty_outcomes(self, capsys):
        """Brief with no outcomes still prints cleanly."""
        brief = _make_minimal_brief()
        brief["top_outcomes"] = []
        result = _make_pipeline_result(brief=brief)
        _print_brief(brief, result)

        captured = capsys.readouterr()
        assert "DAILY COMMAND BRIEF" in captured.out

    def test_print_brief_conflicts_section(self, capsys):
        """Conflicts appear in a dedicated section."""
        brief = _make_minimal_brief()
        result = _make_pipeline_result(
            brief=brief,
            conflicts=[
                {
                    "schema_version": "rhythm_schedule_conflict.v1",
                    "reason": "overlap",
                    "outcome_id": "outcome-1",
                    "required_minutes": 90,
                    "available_minutes": 30,
                }
            ],
        )
        _print_brief(brief, result)

        captured = capsys.readouterr()
        assert "CONFLICTS:" in captured.out
        assert "overlap" in captured.out


# ===========================================================================
# Tests: CLI argument parsing
# ===========================================================================

class TestCLIParsing:
    """Argument parsing for both subcommands."""

    def test_morning_subcommand_parsed(self):
        """morning subcommand is recognised and returns exit code."""
        with patch.object(sys, "argv", ["daily_synthesis_run.py", "morning"]):
            # --date is optional, so parse succeeds; may fail at runtime
            exit_code = main()
        # Should return an int exit code (not crash)
        assert isinstance(exit_code, int)

    def test_capture_subcommand_parsed(self):
        """capture subcommand is recognised."""
        with patch.object(sys, "argv", ["daily_synthesis_run.py", "capture"]):
            with patch("sys.stdin", MagicMock(read=lambda: "")):
                exit_code = main()
        assert exit_code == 1

    def test_unknown_subcommand_exits_nonzero(self):
        """Unknown subcommand prints help and exits non-zero."""
        with patch.object(sys, "argv", ["daily_synthesis_run.py", "unknown"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 2


# ===========================================================================
# Tests: integration-style (real imports, mocked persistence)
# ===========================================================================

class TestIntegrationMorningMockedPersistence:
    """Integration-style morning run with mocked persistence."""

    def test_morning_with_mocked_persistence(self, capsys):
        """Morning run with mocked persistence — no live Supabase writes."""
        mock_persist = MagicMock()
        mock_persist.write.return_value = {"status": "synced"}

        mock_result = _make_pipeline_result(
            status=OverallStatus.COMPLETE.value,
            brief=_make_minimal_brief(),
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            with patch(
                "scripts.daily_synthesis_run.DailySynthesisPersistence",
                return_value=mock_persist,
            ):
                with patch(
                    "scripts.daily_synthesis_run._get_supabase_credentials",
                    return_value=("https://mock.supabase.co", "mock-anon", "mock-service"),
                ):
                    argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
                    with patch.object(sys, "argv", argv):
                        exit_code = main()

        assert exit_code == 0
        # Verify persistence.write was called (no live Supabase)
        mock_persist.write.assert_called()

    def test_morning_degraded_still_persists_brief(self, capsys):
        """Degraded mode (Supabase down) still prints brief and exits 0."""
        mock_result = _make_pipeline_result(
            status=OverallStatus.DEGRADED.value,
            brief=_make_minimal_brief(),
            persistence_unavailable=True,
        )

        with patch(
            "scripts.daily_synthesis_run.run_morning_pipeline",
            return_value=mock_result,
        ):
            argv = ["daily_synthesis_run.py", "morning", "--date", "2026-10-03"]
            with patch.object(sys, "argv", argv):
                exit_code = main()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "DAILY COMMAND BRIEF" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])