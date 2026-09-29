# Batch T25 -- Executive Heartbeat
# tola/heartbeat/policy.py: materiality policy as named constants and THRESHOLDS.

from __future__ import annotations


# ---------------------------------------------------------------------------
# Signal kinds
# ---------------------------------------------------------------------------

NO_SIGNAL = "NO_SIGNAL"
WAKE = "WAKE"
ACTION_ONLY = "ACTION_ONLY"


class SignalKind:
    """Named constants for heartbeat signal kinds."""

    NO_SIGNAL = NO_SIGNAL
    WAKE = WAKE
    ACTION_ONLY = ACTION_ONLY


# ---------------------------------------------------------------------------
# Cost constants
# ---------------------------------------------------------------------------

IDLE_COST = 1
WAKE_COST = 50


# ---------------------------------------------------------------------------
# Thresholds (age in days)
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "OVERDUE_TASK": 0,          # any overdue material task wakes
    "BLOCKER_AGE_LIMIT": 3,     # blocker open longer than 3 days wakes
    "APPROVAL_AGE_LIMIT": 5,    # approval pending beyond 5 days wakes
    "EXPERIMENT_REVIEW_AGE": 7, # unreviewed experiment older than 7 days wakes
    "SNAPSHOT_MAX_AGE": 3,      # PortfolioSnapshot older than 3 days -> REFRESH_SNAPSHOT
    "SNAPSHOT_HARD_LIMIT": 7,   # beyond 7 days -> wake instead of refresh-only
}


# ---------------------------------------------------------------------------
# Materiality policy lookup
# ---------------------------------------------------------------------------

def materiality_policy() -> dict:
    """Return a copy of the THRESHOLDS dict for callers that need it."""
    return dict(THRESHOLDS)
