"""Escalation Matrix and Stop Rules for Batch T8.

Stdlib only.  Plain ASCII.  Deterministic: timestamps are inputs,
no clock reads.  Same context always produces the same decision.
"""

from __future__ import annotations

# Re-export public symbols for convenience.
from tola.escalation.matrix import (
    EscalationLevel,
    EscalationDecision,
    EscalationMatrix,
)
from tola.escalation.stop_rules import (
    StopDecision,
    should_stop,
)
from tola.escalation.notify import (
    route_escalation,
)