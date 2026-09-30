"""
Batch S12 -- Mastery Model.
Exports MasteryAnalyser, MasteryResult, MasteryDimension,
DimensionEvidence, and formal competence authority helpers.
Plain ASCII. Python 3 stdlib only.
"""

from scholar.mastery.model import (
    MasteryAnalyser,
    MasteryResult,
    MasteryDimension,
    DimensionEvidence,
    _is_authoritative_source,
    _AUTHORITATIVE_SOURCES,
)