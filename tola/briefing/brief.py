"""FounderBrief -- generate plain-ASCII founder briefings.

Batch T17 -- Founder Briefing and Attention Filter.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from tola.briefing.filter import (
    AttentionDecision,
    AttentionLevel,
    classify_attention,
    collapse_chatter,
)


# ---------------------------------------------------------------------------
# Brief dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Brief:
    """Result of building a founder briefing from a list of events.

    Immutable.  Deterministic: same events + context -> same output.
    """

    urgent: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    notifications: List[str] = field(default_factory=list)
    digest: List[str] = field(default_factory=list)
    silence_count: int = 0


# ---------------------------------------------------------------------------
# Line helpers
# ---------------------------------------------------------------------------

def _implication_first(
    implication: str,
    detail: str,
) -> str:
    """Produce a two-line plain-ASCII briefing line.

    First line states what it means / what action is needed.
    Second line gives the specifics.
    """
    return f"{implication} | {detail}"


def _format_decision(ev: dict, decision: AttentionDecision) -> str:
    """Format a DECISION_REQUIRED event."""
    title = str(ev.get("title", "Untitled decision"))
    options = str(ev.get("options", "none specified"))
    return _implication_first(
        f"DECISION REQUIRED: {title}",
        f"Options: {options}",
    )


def _format_urgent(ev: dict, decision: AttentionDecision) -> str:
    """Format a URGENT event."""
    title = str(ev.get("title", "Urgent condition"))
    detail = str(ev.get("detail", ""))
    parts = [f"URGENT: {title}"]
    if detail:
        parts.append(detail)
    return _implication_first(parts[0], "; ".join(parts[1:]) if len(parts) > 1 else "No additional detail.")


def _format_notify(ev: dict, decision: AttentionDecision) -> str:
    """Format a NOTIFY event."""
    title = str(ev.get("title", "Material change"))
    detail = str(ev.get("detail", ""))
    parts = [f"NOTIFY: {title}"]
    if detail:
        parts.append(detail)
    return _implication_first(parts[0], "; ".join(parts[1:]) if len(parts) > 1 else "")


def _format_digest(ev: dict, decision: AttentionDecision) -> str:
    """Format a DIGEST event."""
    title = str(ev.get("title", "Update"))
    detail = str(ev.get("detail", ""))
    return _implication_first(f"UPDATE: {title}", detail)


def _format_silent(ev: dict, decision: AttentionDecision) -> str:
    """Format a SILENT event (collapsed chatter)."""
    return ""


# ---------------------------------------------------------------------------
# Format dispatch
# ---------------------------------------------------------------------------

_FORMATTERS: dict = {
    AttentionLevel.URGENT: _format_urgent,
    AttentionLevel.DECISION_REQUIRED: _format_decision,
    AttentionLevel.NOTIFY: _format_notify,
    AttentionLevel.DIGEST: _format_digest,
    AttentionLevel.SILENT: _format_silent,
}


# ---------------------------------------------------------------------------
# founder_brief
# ---------------------------------------------------------------------------

def founder_brief(
    events: List[dict],
    context: dict,
) -> Brief:
    """Build a founder briefing from a list of events.

    Parameters
    ----------
    events : list of dict
        Each event must have a ``kind`` key.  Timestamps are inputs only.
    context : dict
        Optional context for collapsing chatter.
        Recognised keys: ``chatter_history`` (list of prior event kinds).

    Returns
    -------
    Brief
        Fields are lists of plain-ASCII lines.  Lines lead with
        implication then detail.  Numbers/status strings are copied
        from source events exactly.
    """
    urgent: List[str] = []
    decisions: List[str] = []
    notifications: List[str] = []
    digest: List[str] = []
    silence_count = 0

    # Collapse chatter first.
    collapsed, silence_count = collapse_chatter(events, context)

    for ev in collapsed:
        decision = classify_attention(ev, context)
        formatter = _FORMATTERS.get(decision.level)
        if formatter is None:
            continue
        line = formatter(ev, decision)
        if not line:
            continue

        if decision.level == AttentionLevel.URGENT:
            urgent.append(line)
        elif decision.level == AttentionLevel.DECISION_REQUIRED:
            decisions.append(line)
        elif decision.level == AttentionLevel.NOTIFY:
            notifications.append(line)
        elif decision.level == AttentionLevel.DIGEST:
            digest.append(line)
        # SILENT lines are dropped (already counted in silence_count).

    return Brief(
        urgent=urgent,
        decisions=decisions,
        notifications=notifications,
        digest=digest,
        silence_count=silence_count,
    )