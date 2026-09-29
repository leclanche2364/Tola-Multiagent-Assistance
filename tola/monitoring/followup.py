"""Follow-up rules for delegation monitoring.

Batch T12 -- Delegation Monitoring and Follow-Through.
Stdlib only.  Plain ASCII.  Deterministic: timestamps are inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from tola.delegation.protocol import DelegationStatus
from tola.monitoring.tracker import DelegationTracker, TrackingEvent


# ---------------------------------------------------------------------------
# Named threshold constants
# ---------------------------------------------------------------------------

ACK_TIMEOUT = "ack_timeout"
PROGRESS_TIMEOUT = "progress_timeout"
REVIEW_TIMEOUT = "review_timeout"
ESCALATE = "ESCALATE"
NUDGE = "NUDGE"
FLAG = "FLAG"


# ---------------------------------------------------------------------------
# Follow-up action
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FollowUpAction:
    """A single follow-up action triggered by a stalled delegation."""

    delegation_id: str
    action: str
    reason: str
    current_status: str
    last_event: str
    timestamp: str


# ---------------------------------------------------------------------------
# due_followups
# ---------------------------------------------------------------------------

def due_followups(
    tracker: DelegationTracker,
    now_iso: str,
    thresholds: dict[str, str],
) -> list[FollowUpAction]:
    """Return follow-up actions for delegations that have stalled.

    Rules (all deterministic, thresholds named):
      1. No acknowledgement within ACK_TIMEOUT -> NUDGE specialist.
      2. IN_PROGRESS beyond PROGRESS_TIMEOUT without progress event -> NUDGE + FLAG.
      3. RESULT_RECEIVED but unreviewed beyond REVIEW_TIMEOUT -> FLAG to Tola.
      4. Missed deadline -> ESCALATE (routes via T8 escalation levels).

    *now_iso* is an ISO timestamp string (input, never read from clock).
    *thresholds* maps rule names to ISO timestamp strings representing
    the deadline for that rule.
    """
    actions: list[FollowUpAction] = []

    for entry in tracker.all_entries():
        did = entry.delegation_id
        history = entry.event_history
        if not history:
            continue

        # Skip terminal delegations entirely.
        terminal = {
            DelegationStatus.ACCEPTED,
            DelegationStatus.REJECTED,
            DelegationStatus.CANCELLED,
        }
        if entry.status in terminal:
            continue

        last_event, last_ts = history[-1]

        # --- Rule 1: No acknowledgement within ACK_TIMEOUT ---
        ack_events = [e for e, _ in history if e == TrackingEvent.ACKNOWLEDGED]
        if not ack_events:
            ack_deadline = thresholds.get(ACK_TIMEOUT)
            if ack_deadline and now_iso >= ack_deadline:
                actions.append(
                    FollowUpAction(
                        delegation_id=did,
                        action=NUDGE,
                        reason="No acknowledgement within ACK_TIMEOUT.",
                        current_status=entry.status.value,
                        last_event=last_event.value,
                        timestamp=last_ts,
                    )
                )

        # --- Rule 2: IN_PROGRESS beyond PROGRESS_TIMEOUT without progress event ---
        if entry.status == DelegationStatus.IN_PROGRESS:
            progress_events = [
                e for e, _ in history if e == TrackingEvent.PROGRESS_NOTED
            ]
            prog_deadline = thresholds.get(PROGRESS_TIMEOUT)
            if prog_deadline and now_iso >= prog_deadline:
                if not progress_events:
                    actions.append(
                        FollowUpAction(
                            delegation_id=did,
                            action=f"{NUDGE}+{FLAG}",
                            reason="IN_PROGRESS beyond PROGRESS_TIMEOUT without progress event.",
                            current_status=entry.status.value,
                            last_event=last_event.value,
                            timestamp=last_ts,
                        )
                    )

        # --- Rule 3: RESULT_RECEIVED but unreviewed beyond REVIEW_TIMEOUT ---
        if entry.status == DelegationStatus.RESULT_RECEIVED:
            review_deadline = thresholds.get(REVIEW_TIMEOUT)
            if review_deadline and now_iso >= review_deadline:
                actions.append(
                    FollowUpAction(
                        delegation_id=did,
                        action=FLAG,
                        reason="RESULT_RECEIVED but unreviewed beyond REVIEW_TIMEOUT.",
                        current_status=entry.status.value,
                        last_event=last_event.value,
                        timestamp=last_ts,
                    )
                )

        # --- Rule 4: Missed deadline -> ESCALATE ---
        esc_deadline = thresholds.get(ESCALATE)
        if esc_deadline and now_iso >= esc_deadline:
            actions.append(
                FollowUpAction(
                    delegation_id=did,
                    action=ESCALATE,
                    reason="Missed deadline; overdue escalation.",
                    current_status=entry.status.value,
                    last_event=last_event.value,
                    timestamp=last_ts,
                )
            )

    return actions