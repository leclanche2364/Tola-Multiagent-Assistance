"""Evidence-gated strength/weakness claims.

Batch T20 -- Tola Performance Model.
A claim is stored ONLY when the referenced metric has sample_count >= MIN_SAMPLE.
Deterministic; no clock reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tola.performance.metrics import PerformanceMetrics

MIN_SAMPLE = 5


@dataclass(frozen=True)
class Claim:
    kind: str          # "strength" or "weakness"
    statement: str
    metric_kind: str
    metric_value: Any
    sample_count: int


class ClaimStore:
    """Stores claims only when evidence gate is satisfied."""

    def __init__(self, metrics: PerformanceMetrics) -> None:
        self._metrics = metrics
        self._claims: list[Claim] = []

    def claim(self, kind: str, statement: str, metric_kind: str) -> Claim:
        """Create and store a claim if evidence gate passes.

        Raises ValueError if sample_count < MIN_SAMPLE or metric_kind unknown.
        """
        sample_count = self._metrics.sample_count(metric_kind)
        if sample_count < MIN_SAMPLE:
            raise ValueError(
                f"Insufficient evidence for {metric_kind!r}: "
                f"sample_count={sample_count}, MIN_SAMPLE={MIN_SAMPLE}"
            )
        value = self._metric_value(metric_kind)
        c = Claim(
            kind=kind,
            statement=statement,
            metric_kind=metric_kind,
            metric_value=value,
            sample_count=sample_count,
        )
        self._claims.append(c)
        return c

    def _metric_value(self, metric_kind: str) -> Any:
        """Fetch the current computed value for a metric kind."""
        dispatcher = {
            "DELEGATION": self._metrics.delegation_success_rate,
            "REVIEW": lambda: self._metrics.sample_count(REVIEW),
            "RECOVERY": lambda: self._metrics.sample_count(RECOVERY),
            "BRIEFING": lambda: self._metrics.sample_count(BRIEFING),
            "ESCALATION": lambda: self._metrics.escalation_accuracy(),
            "COST": lambda: self._metrics.cost_total(),
            "LATENCY": lambda: self._metrics.latency_total_ms(),
        }
        if metric_kind not in dispatcher:
            raise ValueError(f"Unknown metric kind: {metric_kind!r}")
        return dispatcher[metric_kind]()

    def list_claims(self) -> list[Claim]:
        """Return stored claims with their provenance (metric values & counts)."""
        return list(self._claims)