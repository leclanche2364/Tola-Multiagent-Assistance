"""Refresh executor interface for Daily Synthesis v1.2.

Takes a refresh plan, calls producer functions from Batches 2–4
(parameterized state, fixture-based in tests), and swaps in the
new handoff as "latest valid" only after contract validation passes.
Old version retained as history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from agents.daily_synthesis.contracts import validate_payload, ValidationError
from agents.daily_synthesis.freshness import (
    FreshnessStatus,
    HandoffRecord,
    RefreshPlan,
)


@dataclass
class RefreshResult:
    """Result of executing a refresh for a single domain."""

    domain: str
    success: bool
    new_handoff: Optional[dict[str, Any]] = None
    previous_handoff: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    freshness_status: FreshnessStatus = FreshnessStatus.FAILED


@dataclass
class RefreshExecutionReport:
    """Report of a full refresh execution."""

    results: dict[str, RefreshResult] = field(default_factory=dict)
    refreshed_domains: list[str] = field(default_factory=list)
    failed_domains: list[str] = field(default_factory=list)
    skipped_domains: list[str] = field(default_factory=list)


def execute_refresh(
    plan: RefreshPlan,
    producers: dict[str, callable],
    current_handoffs: dict[str, dict[str, Any]],
    states: Optional[dict[str, dict[str, Any]]] = None,
    agent_id: str = "tola",
) -> RefreshExecutionReport:
    """Execute a refresh plan.

    For each stale domain in the plan:
    1. Call the producer function (parameterized with state).
    2. Validate the result against its contract.
    3. If valid, store as new "latest valid" handoff; old version kept as history.
    4. If invalid or errored, record failure — never silently treat as fresh.

    Args:
        plan: RefreshPlan from build_refresh_plan.
        producers: domain -> producer function mapping.
            Each producer accepts agent_id and state kwargs.
        current_handoffs: domain -> latest valid handoff dict (history base).
        states: optional domain -> state dict for state-sensitive producers.
        agent_id: Agent identifier for produced handoffs.

    Returns:
        RefreshExecutionReport with per-domain results.
    """
    states = states or {}
    report = RefreshExecutionReport()

    for domain in plan.domains_to_refresh:
        producer = producers.get(domain)
        previous = current_handoffs.get(domain)

        if producer is None:
            result = RefreshResult(
                domain=domain,
                success=False,
                previous_handoff=previous,
                error=f"no producer registered for {domain}",
                freshness_status=FreshnessStatus.FAILED,
            )
            report.results[domain] = result
            report.failed_domains.append(domain)
            continue

        # Call producer
        try:
            new_payload = producer(agent_id=agent_id, state=states.get(domain))
        except Exception as exc:
            result = RefreshResult(
                domain=domain,
                success=False,
                previous_handoff=previous,
                error=f"producer error: {exc}",
                freshness_status=FreshnessStatus.FAILED,
            )
            report.results[domain] = result
            report.failed_domains.append(domain)
            continue

        # Validate contract
        try:
            if isinstance(new_payload, dict):
                validate_payload(new_payload)
            else:
                validate_payload(dict(new_payload))
        except (ValidationError, Exception) as exc:
            result = RefreshResult(
                domain=domain,
                success=False,
                previous_handoff=previous,
                error=f"contract validation failed: {exc}",
                freshness_status=FreshnessStatus.FAILED,
            )
            report.results[domain] = result
            report.failed_domains.append(domain)
            continue

        # Success — swap in new handoff as latest valid, old retained as history
        result = RefreshResult(
            domain=domain,
            success=True,
            new_handoff=new_payload if isinstance(new_payload, dict) else dict(new_payload),
            previous_handoff=previous,
            freshness_status=FreshnessStatus.FRESH,
        )
        report.results[domain] = result
        report.refreshed_domains.append(domain)

    # Domains not in the plan were skipped (fresh)
    for domain in current_handoffs:
        if domain not in plan.domains_to_refresh:
            report.skipped_domains.append(domain)

    return report
