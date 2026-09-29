"""Batch T14 -- Stalled Work Recovery.

Deterministic recovery actions for stalled work patterns.
Every stalled pattern maps to a bounded, safe recovery action.
Tola never silently reassigns, rewrites goals, or fabricates progress.
Stdlib only.  Plain ASCII.  No network, no clock reads.
"""

from __future__ import annotations

from .patterns import StallPattern, detect_stall_pattern
from .actions import (
    RecoveryPlan,
    RecoveryAction,
    propose_recovery,
    ALLOWED_ACTIONS,
)