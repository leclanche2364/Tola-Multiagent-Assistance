#!/usr/bin/env python3
"""Tola Daily Synthesis — runnable entrypoint (Batch 11).

CLI entrypoint for the morning pipeline and capture commands.
Reads Supabase credentials from repo .env only inside this script.
All env names appear only in comments; values are never printed.

Usage:
    python3 scripts/daily_synthesis_run.py morning [--date YYYY-MM-DD]
    python3 scripts/daily_synthesis_run.py capture [--date YYYY-MM-DD] [--input FILE]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Env loading — Supabase credentials read from repo .env ONLY here
# SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"


def _load_env() -> dict[str, str]:
    """Parse repo .env file into a dict. Values never printed."""
    result: dict[str, str] = {}
    if _ENV_PATH.exists():
        with open(_ENV_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    result[key.strip()] = value.strip()
    return result


def _get_supabase_credentials() -> tuple[str, str, str]:
    """Return (url, anon_key, service_role_key) from repo .env."""
    env = _load_env()
    url = env.get("SUPABASE_URL", "")
    anon = env.get("SUPABASE_ANON_KEY", "")
    service = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    return url, anon, service


# ---------------------------------------------------------------------------
# Imports after env loading — keep env names out of import-time tracebacks
# ---------------------------------------------------------------------------

sys.path.insert(0, str(_REPO_ROOT))

from agents.daily_synthesis.persistence import (
    DailySynthesisPersistence,
    PersistenceUnavailable,
)
from agents.daily_synthesis.morning_pipeline import (
    MorningPipelineResult,
    OverallStatus,
    run_morning_pipeline,
)
from agents.daily_synthesis.learning_loop import (
    BriefOutcome,
    ExecutionRecord,
    OutcomeStatus,
    record_outcome,
    summarise,
)
from agents.daily_synthesis.contracts import ValidationError


# ---------------------------------------------------------------------------
# Handoff producers with fixture/default state
# ---------------------------------------------------------------------------

def _make_capacity_handoff() -> dict[str, Any]:
    """Build a rhythm_capacity_handoff.v1 from capacity_handoff.py defaults."""
    from agents.rhythm.capacity_handoff import (
        CapacityWindow,
        FixedCommitment,
        RecoveryData,
        assemble_capacity_handoff,
    )

    return assemble_capacity_handoff(
        agent_id="tola",
        rhythm_id="r1",
        shifts=[],
        fixed_commitments=[],
        available_windows=[
            {
                "start": "09:00",
                "end": "12:00",
                "duration_minutes": 180,
                "work_type": "deep",
                "confidence": 0.9,
                "constraints": [],
            },
            {
                "start": "14:00",
                "end": "17:00",
                "duration_minutes": 180,
                "work_type": "medium",
                "confidence": 0.8,
                "constraints": [],
            },
        ],
        recovery=RecoveryData(status="adequate", fatigue_risk="low", recovery_buffer_minutes=30),
        notes="Default capacity handoff for daily synthesis morning run",
    )


def _make_scholar_handoff() -> dict[str, Any]:
    """Build a scholar_handoff.v1 from scholar/handoff.py defaults."""
    from agents.scholar.handoff import produce_handoff

    return produce_handoff(agent_id="tola", energy_level="medium")


def _make_growth_handoff() -> dict[str, Any]:
    """Build a growth_handoff.v1 from growth_handoff.py fixture."""
    from agents.daily_synthesis.growth_handoff import produce_growth_handoff

    fixture_path = _REPO_ROOT / "agents" / "daily_synthesis" / "fixtures" / "growth_fresh.json"
    return produce_growth_handoff(
        agent_id="tola",
        source=str(fixture_path),
        project_id="growth",
    )


def _make_project_handoffs() -> list[dict[str, Any]]:
    """Build project_status_handoff.v1 payloads from project_status_handoff.py fixtures."""
    from agents.daily_synthesis.project_status_handoff import produce_project_status_handoff

    fixture_dir = _REPO_ROOT / "agents" / "daily_synthesis" / "fixtures"
    handoffs: list[dict[str, Any]] = []

    # Use a fresh fixture if available; otherwise build a minimal valid handoff
    fresh_fixture = fixture_dir / "projects_fresh.json"
    if fresh_fixture.exists():
        with open(fresh_fixture, "r", encoding="utf-8") as fh:
            projects_state = json.load(fh)
        for project_id in projects_state:
            try:
                h = produce_project_status_handoff(
                    agent_id="tola",
                    source=projects_state,
                    project_id=project_id,
                )
                handoffs.append(h)
            except (ValidationError, KeyError):
                continue
    else:
        # Minimal default handoff so the pipeline has something to work with
        try:
            h = produce_project_status_handoff(
                agent_id="tola",
                source={"Shiftlyx": {"current_phase": "development", "next_action": "Continue work"}},
                project_id="Shiftlyx",
            )
            handoffs.append(h)
        except (ValidationError, KeyError):
            pass

    return handoffs


def _build_handoffs() -> dict[str, Any]:
    """Build handoffs from producers with fixture/default state.

    Graceful empty-blackboard behaviour: if a producer fails, that
    domain is simply absent from the handoffs dict — the pipeline
    will use defaults or mark the domain as missing.
    """
    handoffs: dict[str, Any] = {}

    producers = [
        ("rhythm", _make_capacity_handoff),
        ("scholar", _make_scholar_handoff),
        ("growth", _make_growth_handoff),
    ]

    for domain, producer in producers:
        try:
            result = producer()
            if isinstance(result, dict):
                handoffs[domain] = result
        except Exception:
            # Graceful — skip this domain, pipeline handles missing domains
            pass

    # Project handoffs are a list, not a single dict
    try:
        project_hs = _make_project_handoffs()
        if project_hs:
            for ph in project_hs:
                handoffs[ph.get("project_id", "projects")] = ph
    except Exception:
        pass

    return handoffs


# ---------------------------------------------------------------------------
# morning command
# ---------------------------------------------------------------------------

def _print_brief(brief: dict[str, Any], result: MorningPipelineResult) -> None:
    """Print the Daily Command Brief as a clean human-readable plan."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("DAILY COMMAND BRIEF")
    lines.append("=" * 60)

    date_str = brief.get("date", "")
    status = result.overall_status
    lines.append(f"Date: {date_str}  |  Status: {status}")
    lines.append("")

    # Top outcomes
    top_outcomes = brief.get("top_outcomes", [])
    if top_outcomes:
        lines.append("TOP OUTCOMES:")
        for i, outcome in enumerate(top_outcomes, 1):
            mins = outcome.get("estimated_minutes", "?")
            lines.append(f"  {i}. {outcome.get('definition_of_done', '')} ({mins}min)")
    else:
        lines.append("TOP OUTCOMES: (none selected)")

    lines.append("")

    # Schedule windows
    capacity_summary = brief.get("capacity_summary", {})
    if capacity_summary:
        lines.append("SCHEDULE WINDOWS:")
        lines.append(f"  Total available: {capacity_summary.get('total_available_minutes', '?')} min")
        lines.append(f"  Planned: {capacity_summary.get('total_planned_minutes', '?')} min")
        lines.append(f"  Buffer: {capacity_summary.get('remaining_buffer_minutes', '?')} min")

    lines.append("")

    # Deferrals
    not_today = brief.get("not_today", [])
    if not_today:
        lines.append("DEFERRALS:")
        for item in not_today:
            lines.append(f"  - {item}")
    else:
        lines.append("DEFERRALS: (none)")

    lines.append("")

    # Conflicts
    if result.conflicts:
        lines.append("CONFLICTS:")
        for conflict in result.conflicts:
            lines.append(f"  - {conflict.get('reason', 'unknown')}: {conflict.get('outcome_id', '')}")

    # Missing domains
    if result.missing_domains:
        lines.append("")
        lines.append("MISSING DOMAINS:")
        for domain in result.missing_domains:
            lines.append(f"  - {domain}")

    if result.persistence_unavailable:
        lines.append("")
        lines.append("NOTE: Persistence unavailable (Supabase down) — brief not saved.")

    lines.append("=" * 60)
    print("\n".join(lines))


def cmd_morning(args: argparse.Namespace) -> int:
    """Run the morning pipeline and print the Daily Command Brief."""
    planning_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load Supabase credentials from repo .env
    url, anon_key, _service_role = _get_supabase_credentials()

    # Build persistence (no-op-safe if Supabase down)
    persistence: Optional[DailySynthesisPersistence] = None
    if url and anon_key:
        try:
            persistence = DailySynthesisPersistence(base_url=url, api_key=anon_key)
        except Exception:
            persistence = None

    # Build handoffs from producers with fixture/default state
    handoffs = _build_handoffs()

    # Build producers from pre-built handoffs so run_morning_pipeline
    # can use them directly (morning_pipeline uses producers, not handoffs).
    def _producer_for(handoff_dict):
        def _producer(agent_id, state=None):
            return handoff_dict
        return _producer

    producers_map = {}
    for domain, hb in handoffs.items():
        if isinstance(hb, dict):
            producers_map[domain] = _producer_for(hb)
        elif isinstance(hb, list):
            # project handoffs are a list — use the first valid one
            for ph in hb:
                if isinstance(ph, dict):
                    producers_map[domain] = _producer_for(ph)
                    break

    # Run morning pipeline
    result = run_morning_pipeline(
        planning_date=planning_date,
        persistence=persistence,
        producers=producers_map if producers_map else None,
        now=datetime.now(timezone.utc).isoformat(),
    )

    # Print brief
    if result.brief:
        _print_brief(result.brief, result)
    else:
        print("Daily Command Brief: (no brief generated — pipeline failed)")

    # Persist brief (no-op-safe)
    if persistence is not None and result.brief is not None:
        try:
            persist_payload = {
                "schema_version": "daily_command_brief.v1",
                "agent_id": "tola",
                "date": planning_date,
                "top_outcomes": result.brief.get("top_outcomes", []),
                "not_today": result.brief.get("not_today", []),
                "capacity_used_minutes": result.brief.get("capacity_used_minutes", 0),
                "buffer_minutes": result.brief.get("buffer_minutes", 0),
            }
            persistence.write("briefs", persist_payload)
        except PersistenceUnavailable:
            pass
        except Exception:
            pass

    # Exit 0 on complete/degraded, non-zero only on hard failure
    if result.overall_status == OverallStatus.FAILED.value:
        return 1
    return 0


# ---------------------------------------------------------------------------
# capture command
# ---------------------------------------------------------------------------

class CaptureInputError(Exception):
    """Raised when capture input cannot be read or parsed."""


def _read_capture_input(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Read planned-vs-actual records from a JSON file or stdin.

    For cron use: non-interactive, reads file or stdin, no prompts.
    Raises CaptureInputError on any failure so callers can return
    a proper exit code.
    """
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            raise CaptureInputError(f"input file not found: {input_path}")
        with open(input_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        # Read from stdin (non-interactive for cron)
        raw = sys.stdin.read()
        if not raw.strip():
            raise CaptureInputError("no input provided (expected JSON via --input or stdin)")
        data = json.loads(raw)

    # Accept either a list of records or a dict with "records" key
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "records" in data:
        return data["records"]
    if isinstance(data, dict) and "outcomes" in data:
        return data["outcomes"]

    raise CaptureInputError("input JSON must be a list of records or a dict with 'records'/'outcomes' key")


def cmd_capture(args: argparse.Namespace) -> int:
    """Capture per-brief execution outcomes and print the daily trend line."""
    planning_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Read records
    try:
        records = _read_capture_input(args)
    except (json.JSONDecodeError, ValueError, CaptureInputError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not isinstance(records, list) or len(records) == 0:
        print("Error: no execution records provided", file=sys.stderr)
        return 1

    # Build a minimal brief from the first record's domain context
    # so record_outcome has something to validate against
    first = records[0]
    brief: dict[str, Any] = {
        "schema_version": "daily_command_brief.v1",
        "date": planning_date,
        "top_outcomes": [
            {
                "definition_of_done": first.get("domain", "unknown") + " outcome",
                "estimated_minutes": first.get("planned_minutes", 30),
                "source_refs": [],
            }
        ],
        "not_today": [],
        "capacity_used_minutes": 0,
        "buffer_minutes": 0,
    }

    # Validate and record each outcome via learning_loop.record_outcome
    try:
        outcome = record_outcome(brief, records, now_iso)
    except ValidationError as exc:
        print(f"Error: validation failed — {exc}", file=sys.stderr)
        return 1

    # Persist outcome records (idempotent via uuid5 keys in persistence)
    url, anon_key, _service_role = _get_supabase_credentials()
    if url and anon_key:
        try:
            persistence = DailySynthesisPersistence(base_url=url, api_key=anon_key)
            for rec in records:
                payload = {
                    "schema_version": "planned_vs_completed_record.v1",
                    "agent_id": "tola",
                    "domain": rec.get("domain", ""),
                    "planned_minutes": rec.get("planned_minutes", 0),
                    "actual_minutes": rec.get("actual_minutes", 0),
                    "status": rec.get("status", "completed"),
                    "reason": rec.get("reason", ""),
                    "fatigue_energy_predicted": rec.get("fatigue_energy_predicted", "medium"),
                    "fatigue_energy_actual": rec.get("fatigue_energy_actual", "medium"),
                    "capacity_predicted_minutes": rec.get("capacity_predicted_minutes", 0),
                    "capacity_actual_available_minutes": rec.get("capacity_actual_available_minutes", 0),
                }
                persistence.write("outcomes", payload)
        except PersistenceUnavailable:
            pass
        except Exception:
            pass

    # Print daily trend line
    print(f"--- Daily Trend: {planning_date} ---")
    print(f"  Completion rate: {outcome.completion_rate:.0%}")
    print(f"  Estimation error: {outcome.estimation_error_minutes:+d} min")
    print(f"  Capacity delta: {outcome.capacity_delta:+d} min")
    if outcome.partial_reasons:
        print(f"  Partial reasons: {'; '.join(outcome.partial_reasons)}")
    if outcome.skip_reasons:
        print(f"  Skip reasons: {'; '.join(outcome.skip_reasons)}")
    if outcome.fatigue_mismatches:
        print(f"  Fatigue mismatches: {'; '.join(outcome.fatigue_mismatches)}")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tola Daily Synthesis — morning pipeline and capture CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # morning subcommand
    morning_parser = subparsers.add_parser("morning", help="Run the morning pipeline and print the Daily Command Brief")
    morning_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Planning date (YYYY-MM-DD). Defaults to today.",
    )

    # capture subcommand
    capture_parser = subparsers.add_parser("capture", help="Capture execution outcomes and print the daily trend line")
    capture_parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Planning date (YYYY-MM-DD). Defaults to today.",
    )
    capture_parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to JSON file with planned vs actual records. If omitted, reads from stdin.",
    )

    args = parser.parse_args()

    if args.command == "morning":
        return cmd_morning(args)
    elif args.command == "capture":
        return cmd_capture(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())