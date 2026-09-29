# Persona Consolidation and Memory Mapping -- Batch T19.
# Plain ASCII. Stdlib only. Deterministic. No file I/O. No clock reads.

from __future__ import annotations

# Re-export public API for convenience.
from tola.consolidation.mapper import (
    BLACKBOARD_PROFILE,
    USER_MD,
    MEMORY_MD,
    DATED_NOTES,
    MemoryMap,
)
from tola.consolidation.consolidate import (
    ConsolidationResult,
    daily_consolidate,
    weekly_consolidate,
    reconstruct_session,
)
from tola.consolidation.rules import (
    CONFLICT_RESOLUTION_ORDER,
    RECENCY_WINDOW_DAYS,
    PROMOTION_EVIDENCE_WINDOW_DAYS,
    validate_zone_placement,
    validate_conflict_resolution,
    validate_recency_window,
)