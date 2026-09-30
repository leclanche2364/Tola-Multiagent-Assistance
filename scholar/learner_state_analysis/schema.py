"""
Batch S11 -- Ling Output Schema Validation.
Validates that Ling model output conforms to the expected
structure for learner-state analysis.  Rejects malformed
output (S11-05).
Plain ASCII. Python 3 stdlib only.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LingSchemaErrorDetail:
    """A single schema validation error."""
    field: str
    message: str
    value: Any = None


@dataclass(frozen=True)
class LingOutputSchema:
    """Validated Ling output for learner-state analysis.

    Fields:
    - summary: a short deterministic summary of the analysis
    - evidence_refs: list of evidence reference IDs the
      interpretation is traceable to
    - interpretation: the Ling model's interpretation
      (must reference evidence_refs)
    - uncertainty: explicit uncertainty statement where
      evidence is missing or weak
    - strengths: list of observed strengths
    - gaps: list of observed gaps
    """

    summary: str
    evidence_refs: List[str]
    interpretation: str
    uncertainty: str
    strengths: List[str]
    gaps: List[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LingOutputSchema":
        """Build from a dict, raising LingSchemaError for missing
        or invalid fields."""
        errors: List[LingSchemaError] = []

        # summary: required, non-empty string
        summary = data.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            errors.append(
                LingSchemaErrorDetail(
                    field="summary",
                    message="summary must be a non-empty string",
                    value=summary,
                )
            )

        # evidence_refs: required, list of non-empty strings
        evidence_refs = data.get("evidence_refs")
        if not isinstance(evidence_refs, list):
            errors.append(
                LingSchemaErrorDetail(
                    field="evidence_refs",
                    message="evidence_refs must be a list",
                    value=evidence_refs,
                )
            )
        else:
            for i, ref in enumerate(evidence_refs):
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(
                        LingSchemaErrorDetail(
                            field=f"evidence_refs[{i}]",
                            message="each evidence_ref must be a non-empty string",
                            value=ref,
                        )
                    )

        # interpretation: required, non-empty string
        interpretation = data.get("interpretation")
        if not isinstance(interpretation, str) or not interpretation.strip():
            errors.append(
                LingSchemaErrorDetail(
                    field="interpretation",
                    message="interpretation must be a non-empty string",
                    value=interpretation,
                )
            )

        # uncertainty: required, non-empty string
        uncertainty = data.get("uncertainty")
        if not isinstance(uncertainty, str) or not uncertainty.strip():
            errors.append(
                LingSchemaErrorDetail(
                    field="uncertainty",
                    message="uncertainty must be a non-empty string",
                    value=uncertainty,
                )
            )

        # strengths: required, list of strings
        strengths = data.get("strengths")
        if not isinstance(strengths, list):
            errors.append(
                LingSchemaErrorDetail(
                    field="strengths",
                    message="strengths must be a list",
                    value=strengths,
                )
            )
        else:
            for i, s in enumerate(strengths):
                if not isinstance(s, str):
                    errors.append(
                        LingSchemaErrorDetail(
                            field=f"strengths[{i}]",
                            message="each strength must be a string",
                            value=s,
                        )
                    )

        # gaps: required, list of strings
        gaps = data.get("gaps")
        if not isinstance(gaps, list):
            errors.append(
                LingSchemaErrorDetail(
                    field="gaps",
                    message="gaps must be a list",
                    value=gaps,
                )
            )
        else:
            for i, g in enumerate(gaps):
                if not isinstance(g, str):
                    errors.append(
                        LingSchemaErrorDetail(
                            field=f"gaps[{i}]",
                            message="each gap must be a string",
                            value=g,
                        )
                    )

        if errors:
            raise LingSchemaError(errors)

        return cls(
            summary=summary.strip(),
            evidence_refs=[r.strip() for r in evidence_refs],
            interpretation=interpretation.strip(),
            uncertainty=uncertainty.strip(),
            strengths=[s.strip() for s in strengths],
            gaps=[g.strip() for g in gaps],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "evidence_refs": self.evidence_refs,
            "interpretation": self.interpretation,
            "uncertainty": self.uncertainty,
            "strengths": self.strengths,
            "gaps": self.gaps,
        }


class LingSchemaError(Exception):
    """Raised when Ling output fails schema validation."""

    def __init__(self, errors: List[LingSchemaErrorDetail]) -> None:
        self.errors = errors
        super().__init__(
            f"Ling output schema validation failed: "
            f"{len(errors)} error(s)"
        )


def validate_ling_output(raw: Any) -> LingOutputSchema:
    """Validate raw Ling output against the schema.

    Returns a validated LingOutputSchema on success.
    Raises LingSchemaError on failure.
    """
    if not isinstance(raw, dict):
        raise LingSchemaError(
            [
                LingSchemaErrorDetail(
                    field="root",
                    message="Ling output must be a dict",
                    value=raw,
                )
            ]
        )
    return LingOutputSchema.from_dict(raw)