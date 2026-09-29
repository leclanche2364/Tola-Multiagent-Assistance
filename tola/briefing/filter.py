"""AttentionFilter -- classify events into attention levels.

Batch T17 -- Founder Briefing and Attention Filter.
Stdlib only.  Plain ASCII.  Deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Attention levels (ordered lowest -> highest)
# ---------------------------------------------------------------------------

class AttentionLevel(str, Enum):
    SILENT = "SILENT"
    DIGEST = "DIGEST"
    NOTIFY = "NOTIFY"
    DECISION_REQUIRED = "DECISION_REQUIRED"
    URGENT = "URGENT"


# Frozen frozenset of all valid levels.
ALL_ATTENTION_LEVELS: FrozenSet[str] = frozenset(
    {l.value for l in AttentionLevel}
)


# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AttentionDecision:
    """Result of classifying an event into an attention level.

    Immutable.  Deterministic: same inputs -> same output.
    """

    level: AttentionLevel
    reason: str


# ---------------------------------------------------------------------------
# Rubric constants (named strings used in classify_attention)
# ---------------------------------------------------------------------------

# Routine internal acknowledgement / agent chatter -> SILENT.
ROUTINE_ACK_KINDS: FrozenSet[str] = frozenset(
    {"ack", "heartbeat", "pulse", "internal_ack", "agent_chatter"}
)

# Non-urgent state changes -> DIGEST.
NON_URGENT_STATE_KINDS: FrozenSet[str] = frozenset(
    {"health_label_change", "progress_note", "ledger_update", "status_note"}
)

# Material changes -> NOTIFY.
MATERIAL_CHANGE_KINDS: FrozenSet[str] = frozenset(
    {
        "project_blocked",
        "project_dormant",
        "escalation_raised",
        "deadline_at_risk",
        "decision_superseded",
    }
)

# True decision request -> DECISION_REQUIRED.
DECISION_KINDS: FrozenSet[str] = frozenset({"decision_request"})

# Urgent conditions -> URGENT.
URGENT_KINDS: FrozenSet[str] = frozenset(
    {"escalate_stop", "missed_hard_deadline", "stop_rule_trigger"}
)


# ---------------------------------------------------------------------------
# classify_attention
# ---------------------------------------------------------------------------

def classify_attention(
    event: Dict[str, object],
    context: Optional[Dict[str, object]] = None,
) -> AttentionDecision:
    """Classify a single event into an AttentionLevel.

    Parameters
    ----------
    event : dict
        Must contain a ``kind`` key (str).  May contain ``detail``,
        ``timestamp``, and other metadata.  Timestamps are inputs only;
        no clock reads.
    context : dict or None
        Optional context for collapsing repeated chatter.
        Recognised keys: ``chatter_history`` (list of prior event kinds).

    Returns
    -------
    AttentionDecision
        Frozen, deterministic.
    """
    kind = str(event.get("kind", ""))
    chatter_history: List[str] = (context or {}).get("chatter_history", [])

    # 1. Urgent conditions always win.
    if kind in URGENT_KINDS:
        return AttentionDecision(
            level=AttentionLevel.URGENT,
            reason=f"Urgent condition: kind='{kind}'.",
        )

    # 2. True decision request.
    if kind in DECISION_KINDS:
        return AttentionDecision(
            level=AttentionLevel.DECISION_REQUIRED,
            reason=f"Decision request: kind='{kind}'.",
        )

    # 3. Material changes.
    if kind in MATERIAL_CHANGE_KINDS:
        return AttentionDecision(
            level=AttentionLevel.NOTIFY,
            reason=f"Material change: kind='{kind}'.",
        )

    # 4. Non-urgent state changes.
    if kind in NON_URGENT_STATE_KINDS:
        return AttentionDecision(
            level=AttentionLevel.DIGEST,
            reason=f"Non-urgent state change: kind='{kind}'.",
        )

    # 5. Routine acknowledgement / agent chatter.
    if kind in ROUTINE_ACK_KINDS:
        # Collapse: if same kind already seen in chatter_history,
        # keep SILENT but note the collapse.
        same_kind_count = sum(1 for k in chatter_history if k == kind)
        if same_kind_count > 0:
            return AttentionDecision(
                level=AttentionLevel.SILENT,
                reason=(
                    f"Routine acknowledgement collapsed "
                    f"(count={same_kind_count + 1})."
                ),
            )
        return AttentionDecision(
            level=AttentionLevel.SILENT,
            reason=f"Routine acknowledgement: kind='{kind}'.",
        )

    # 6. Unknown kind -> DIGEST as safe default.
    return AttentionDecision(
        level=AttentionLevel.DIGEST,
        reason=f"Unrecognised kind '{kind}' treated as non-urgent.",
    )


# ---------------------------------------------------------------------------
# collapse_chatter -- collapse repeated routine events within a window
# ---------------------------------------------------------------------------

def collapse_chatter(
    events: List[Dict[str, object]],
    context: Optional[Dict[str, object]] = None,
) -> Tuple[List[Dict[str, object]], int]:
    """Collapse repeated routine acknowledgement events.

    Returns
    -------
    (filtered_events, silence_count)
        filtered_events has at most one digest line per collapsed group.
        silence_count is the number of events collapsed into silence.
    """
    context = context or {}
    chatter_history: List[str] = context.get("chatter_history", [])
    filtered: List[Dict[str, object]] = []
    silence_count = 0

    for ev in events:
        kind = str(ev.get("kind", ""))
        if kind in ROUTINE_ACK_KINDS:
            same_kind_count = sum(1 for k in chatter_history if k == kind)
            if same_kind_count > 0:
                # Collapse: do not add to filtered, count as silence.
                silence_count += 1
                continue
            # First occurrence in this window: keep as digest.
            chatter_history.append(kind)
            # Promote to digest so it surfaces as one line.
            promoted = dict(ev)
            promoted["kind"] = "progress_note"
            filtered.append(promoted)
        else:
            filtered.append(ev)

    return filtered, silence_count