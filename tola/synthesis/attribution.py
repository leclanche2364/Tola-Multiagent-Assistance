# Attribution module for Batch T11 - Cross-Agent Synthesis.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# EvidenceSource
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceSource:
    """Identifies the origin of a piece of evidence."""

    agent_id: str
    kind: str
    ref: str
    timestamp: str


# ---------------------------------------------------------------------------
# EvidenceItem
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EvidenceItem:
    """One piece of evidence with a claim and confidence."""

    source: EvidenceSource
    claim: str
    confidence: float


# ---------------------------------------------------------------------------
# Attribution helpers
# ---------------------------------------------------------------------------

def _source_tag(item: EvidenceItem) -> str:
    """Return a short source tag like 'growth:ref-123'."""
    return "{agent_id}:{ref}".format(
        agent_id=item.source.agent_id,
        ref=item.source.ref,
    )


def _claim_with_tag(item: EvidenceItem, claim: str) -> str:
    """Wrap a claim with its source tag."""
    tag = _source_tag(item)
    return "{claim} [{tag}]".format(claim=claim, tag=tag)


def attribute(evidence_items: List[EvidenceItem]) -> str:
    """Build a decision text with per-claim source tags.

    Each claim is appended with its source tag in brackets.
    Tags survive through synthesis output so attribution
    remains traceable (T11-06).
    """
    if not evidence_items:
        return ""
    parts: List[str] = []
    for item in evidence_items:
        parts.append(_claim_with_tag(item, item.claim))
    return "\n".join(parts)


def _format_decision_line(prefix: str, text: str, tags: List[str]) -> str:
    """Format a decision or rationale line with source tags."""
    tag_str = " ".join(tags)
    return "{prefix}: {text} ({tag_str})".format(
        prefix=prefix, text=text, tag_str=tag_str,
    )