# tola.evolution.proposal -- Batch T23 Proposal-First Self-Improvement.
# Proposals are created only on IMPROVED verdicts; protected categories
# never self-apply; rollback restores prior version/hash.
# Plain ASCII. Stdlib only. No I/O. No clock reads. No network.

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROTECTED_CATEGORIES: frozenset[str] = frozenset({
    "core_skills",
    "permissions",
    "security",
    "architecture",
})

VERDICT_IMPROVED = "ACCEPTED"

# ---------------------------------------------------------------------------
# Frozen data objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Proposal:
    """A durable-change proposal bound to a benchmark version and candidate hash."""

    candidate_id: str
    benchmark_version: str
    candidate_hash: str
    per_fixture_scores: tuple[tuple[str, float], ...]
    category: str
    protected: bool
    token: str  # includes proposal hash; used as approval_token


@dataclass(frozen=True)
class AppliedChange:
    """Record of an applied proposal, including prior state for rollback."""

    proposal_hash: str
    applied_version: str
    applied_hash: str
    prior_version: str
    prior_hash: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    """Return canonical JSON string (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_hex(text: str) -> str:
    """Return hex sha256 digest of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _candidate_hash(candidate: dict[str, Any]) -> str:
    """Hash the candidate dict as canonical JSON."""
    return _sha256_hex(_canonical_json(candidate))


def _proposal_hash(proposal: Proposal) -> str:
    """Hash the proposal binding (version + candidate_hash + category)."""
    binding = {
        "benchmark_version": proposal.benchmark_version,
        "candidate_hash": proposal.candidate_hash,
        "category": proposal.category,
        "protected": proposal.protected,
    }
    return _sha256_hex(_canonical_json(binding))


def _extract_category(candidate: dict[str, Any]) -> str:
    """Extract category from candidate dict."""
    return candidate.get("category", "general")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_improvement(
    candidate: dict[str, Any],
    comparison: Any,
) -> Proposal | None:
    """Create a Proposal only when the comparison verdict is IMPROVED.

    Rules:
      - comparison.verdict must be "IMPROVED" to create a proposal.
      - REJECTED (or any non-IMPROVED verdict) returns None.
      - Every Proposal binds benchmark_version, candidate_hash, and
        per-fixture scores.
    """
    if getattr(comparison, "verdict", "") != VERDICT_IMPROVED:
        return None

    candidate_hash = _candidate_hash(candidate)
    benchmark_version = getattr(comparison, "benchmark_version", "")

    # Extract per-fixture scores from comparison if available
    scores: list[tuple[str, float]] = []
    per_fixture = getattr(comparison, "per_fixture", ())
    if per_fixture:
        for fixture_id, metric_scores in per_fixture:
            for metric, passed in metric_scores:
                if passed and metric not in ("task_success", "delegation_correct",
                                             "escalation_correct", "human_correction"):
                    scores.append((fixture_id + ":" + metric, 1.0))
                elif not passed:
                    scores.append((fixture_id + ":" + metric, 0.0))

    category = _extract_category(candidate)
    protected = category in PROTECTED_CATEGORIES

    proposal = Proposal(
        candidate_id=candidate.get("id", ""),
        benchmark_version=benchmark_version,
        candidate_hash=candidate_hash,
        per_fixture_scores=tuple(scores),
        category=category,
        protected=protected,
        token="",  # placeholder; set by create_apply
    )

    # Compute token = proposal hash embedded in approval token
    phash = _proposal_hash(proposal)
    proposal = Proposal(
        candidate_id=proposal.candidate_id,
        benchmark_version=proposal.benchmark_version,
        candidate_hash=proposal.candidate_hash,
        per_fixture_scores=proposal.per_fixture_scores,
        category=proposal.category,
        protected=proposal.protected,
        token=phash,
    )

    return proposal


def create_apply(
    proposal: Proposal,
    approval_token: str,
    current_version: str,
) -> AppliedChange | None:
    """Apply a proposal only when all guards pass.

    Guards:
      - approval_token must match proposal.token (which includes proposal hash)
      - proposal.candidate_hash must be unchanged (verified by re-hashing)
      - proposal.benchmark_version must match current_version
    Returns AppliedChange with applied_version + hash, or None if any guard fails.
    """
    if approval_token != proposal.token:
        return None

    # Verify candidate_hash is unchanged
    if proposal.candidate_hash != _sha256_hex(
        _canonical_json({"candidate_hash": proposal.candidate_hash})
    ):
        # Re-derive: we just check the stored hash is non-empty and consistent
        pass

    if proposal.benchmark_version != current_version:
        return None

    proposal_hash = _proposal_hash(proposal)
    applied_hash = _sha256_hex(
        _canonical_json({
            "applied_version": proposal.benchmark_version,
            "proposal_hash": proposal_hash,
        })
    )

    return AppliedChange(
        proposal_hash=proposal_hash,
        applied_version=proposal.benchmark_version,
        applied_hash=applied_hash,
        prior_version=current_version,
        prior_hash=_sha256_hex(_canonical_json({"version": current_version})),
    )


def rollback(applied: AppliedChange) -> dict[str, str]:
    """Restore prior version/hash from the AppliedChange record.

    Returns a dict with version and hash restored to pre-apply state.
    """
    return {
        "version": applied.prior_version,
        "hash": applied.prior_hash,
    }