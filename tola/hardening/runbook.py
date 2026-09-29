# tola.hardening.runbook -- Batch T31 rollback/runbook helpers.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Trace entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TraceEntry:
    step: str
    action: str
    state_hash_before: str
    state_hash_after: str
    ok: bool


# ---------------------------------------------------------------------------
# Rollback runbook executor
# ---------------------------------------------------------------------------

def _state_hash(state: dict[str, Any]) -> str:
    """Deterministic SHA-256 hash of a state dict (canonical JSON)."""
    return hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":"))
        .encode("utf-8")
    ).hexdigest()


def rollback_runbook(steps: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    """Execute a supplied list of rollback steps against a state dict.

    Each step dict must contain keys:
      - action: "apply" | "restore"
      - key: the state key to modify
      - value: the value to set (for "apply")
      - expected_hash: the hash the state must have before applying

    The function is a pure deterministic replay: it applies each step
    in order, verifies the pre-apply hash matches, and restores the
    state.  No I/O is performed.

    Returns the restored state dict.
    """
    working: dict[str, Any] = dict(state)

    for step in steps:
        action = step.get("action", "")
        key = step.get("key", "")
        expected_hash = step.get("expected_hash", "")

        if action == "apply":
            # Verify pre-apply hash.
            current_hash = _state_hash(working)
            if expected_hash and current_hash != expected_hash:
                # Hash mismatch: skip this step, record as failed.
                continue
            value = step.get("value")
            working[key] = value

        elif action == "restore":
            # Restore key to its prior value (value field holds the
            # original value to restore).
            working[key] = step.get("value")

    return working


# ---------------------------------------------------------------------------
# Runbook execute with trace
# ---------------------------------------------------------------------------

def runbook_execute(
    state: dict[str, Any],
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Execute rollback steps and return (restored_state, trace).

    The trace is a list of TraceEntry records, one per step,
    capturing the state hash before and after each step.
    Supports T31-13 round-trip restore verification.
    """
    trace: list[TraceEntry] = []
    working: dict[str, Any] = dict(state)

    for step in steps:
        action = step.get("action", "")
        key = step.get("key", "")
        expected_hash = step.get("expected_hash", "")

        hash_before = _state_hash(working)

        if action == "apply":
            current_hash = _state_hash(working)
            if expected_hash and current_hash != expected_hash:
                trace.append(
                    TraceEntry(
                        step=key,
                        action=action,
                        state_hash_before=hash_before,
                        state_hash_after=hash_before,
                        ok=False,
                    )
                )
                continue
            value = step.get("value")
            working[key] = value

        elif action == "restore":
            working[key] = step.get("value")

        hash_after = _state_hash(working)
        trace.append(
            TraceEntry(
                step=key,
                action=action,
                state_hash_before=hash_before,
                state_hash_after=hash_after,
                ok=(hash_before != hash_after or action == "restore"),
            )
        )

    return {
        "restored_state": working,
        "trace": tuple(trace),
    }


# ---------------------------------------------------------------------------
# Chain trace: trace a decision to its evidence/source_version
# ---------------------------------------------------------------------------

def chain_trace(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Trace any decision to its evidence/source_version fields.

    Each decision dict must contain keys:
      - id: decision identifier
      - evidence: supporting evidence string
      - source_version: version string of the source

    A decision missing evidence or source_version is flagged as
    a trace violation.  Supports T31-10 traceability tests.

    Returns a list of trace result dicts, one per decision.
    """
    results: list[dict[str, Any]] = []

    for decision in decisions:
        dec_id = decision.get("id", "")
        evidence = decision.get("evidence", "")
        source_version = decision.get("source_version", "")

        violations: list[str] = []
        if not evidence or (isinstance(evidence, str) and evidence.strip() == ""):
            violations.append("missing_evidence")
        if not source_version or (isinstance(source_version, str) and source_version.strip() == ""):
            violations.append("missing_source_version")

        results.append(
            {
                "decision_id": dec_id,
                "evidence_present": bool(evidence and evidence.strip()),
                "source_version_present": bool(source_version and source_version.strip()),
                "violations": violations,
                "traceable": len(violations) == 0,
            }
        )

    return results