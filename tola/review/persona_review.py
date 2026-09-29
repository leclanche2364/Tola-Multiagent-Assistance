# Batch T28 -- Weekly Persona Review.
# Plain ASCII. Stdlib only. Deterministic: no clock reads.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Rule constants (consistent with T18 persona/profile.py)
# ---------------------------------------------------------------------------

PROMOTION_THRESHOLD = 3

CONTRADICTION_BLOCK = "CONTRADICTION_BLOCK"

SENSITIVE_CATEGORIES = frozenset({
    "health_conditions",
    "relationship_status",
    "finances",
    "protected_characteristics",
    "location_tracking",
})

# ---------------------------------------------------------------------------
# Observation kind constants (aligned with T18/T21)
# ---------------------------------------------------------------------------

EXPLICIT_PREFERENCE = "EXPLICIT_PREFERENCE"
BEHAVIOURAL_OBSERVATION = "BEHAVIOURAL_OBSERVATION"

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Promotion:
    """A preference promoted from CANDIDATE to ACTIVE."""
    key: str
    value: str
    evidence_refs: tuple[str, ...]
    observed_at: str
    project_id: str

@dataclass(frozen=True)
class BlockedPromotion:
    """A candidate that could not be promoted, with reason."""
    key: str
    value: str
    reason: str
    evidence_refs: tuple[str, ...]

@dataclass(frozen=True)
class SupersededEntry:
    """A prior preference superseded by a newer one."""
    superseded_id: str
    prior_key: str
    prior_value: str
    new_value: str
    observed_at: str

@dataclass(frozen=True)
class PersonaReviewResult:
    """Result of a weekly persona review."""
    promotions: tuple[Promotion, ...]
    blocked_promotions: tuple[BlockedPromotion, ...]
    superseded: tuple[SupersededEntry, ...]

# ---------------------------------------------------------------------------
# Trace function for superseded chains
# ---------------------------------------------------------------------------

def trace(superseded_id: str, superseded: tuple[SupersededEntry, ...]) -> tuple[str, ...]:
    """Return the full chain old -> new for a superseded entry.

    Walks the superseded list following new->old links and returns
    the chain from oldest to newest value.
    """
    chain: list[str] = []
    current_id = superseded_id
    visited: set[str] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        found = None
        for entry in superseded:
            if entry.superseded_id == current_id:
                found = entry
                break
        if found is None:
            break
        chain.append(f"{found.prior_value} -> {found.new_value}")
        current_id = found.prior_key + "|" + found.prior_value
    return tuple(chain)

# ---------------------------------------------------------------------------
# Core review function
# ---------------------------------------------------------------------------

def _is_sensitive(key: str) -> bool:
    """Check whether a preference key touches a sensitive category."""
    key_lower = key.lower().strip()
    for category in SENSITIVE_CATEGORIES:
        if category in key_lower or key_lower in category:
            return True
    return False


def _direction_of(obs: dict[str, Any]) -> str:
    """Return the observation direction: 'positive' or 'negative'."""
    return obs.get("direction", "positive")


def run_persona_review(
    observations: list[dict[str, Any]],
    now_iso: str,
) -> PersonaReviewResult:
    """Run the weekly persona review.

    Parameters
    ----------
    observations : list of dicts with keys: key, value, source,
        direction, evidence_refs, observed_at, project_id, confidence.
    now_iso : str
        ISO timestamp for the review run (input only, no clock reads).

    Returns
    -------
    PersonaReviewResult
        promotions, blocked_promotions, superseded.
    """
    promotions: list[Promotion] = []
    blocked_promotions: list[BlockedPromotion] = []
    superseded: list[SupersededEntry] = []

    # Group observations by (key, value) candidate.
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for obs in observations:
        key = obs.get("key", "")
        value = obs.get("value", "")
        pair = (key, value)
        if pair not in candidates:
            candidates[pair] = []
        candidates[pair].append(obs)

    for pair, obs_list in candidates.items():
        key, value = pair
        positive_obs = [o for o in obs_list if _direction_of(o) == "positive"]
        negative_obs = [o for o in obs_list if _direction_of(o) != "positive"]

        # Sensitive blocklist: never promote or extend profile.
        if _is_sensitive(key):
            blocked_promotions.append(BlockedPromotion(
                key=key,
                value=value,
                reason="SENSITIVE_BLOCKLIST",
                evidence_refs=tuple(o.get("evidence_refs", ("",)) for o in obs_list),
            ))
            continue

        # Contradiction check: if any opposite-direction evidence exists,
        # block promotion and record a blocked_promotion with reason.
        if positive_obs and negative_obs:
            blocked_promotions.append(BlockedPromotion(
                key=key,
                value=value,
                reason=CONTRADICTION_BLOCK,
                evidence_refs=tuple(o.get("evidence_refs", ("",)) for o in obs_list),
            ))
            continue

        # Promotion: >= PROMOTION_THRESHOLD positive observations.
        if len(positive_obs) >= PROMOTION_THRESHOLD:
            primary = positive_obs[0]
            promotions.append(Promotion(
                key=key,
                value=value,
                evidence_refs=tuple(o.get("evidence_refs", ("",)) for o in positive_obs),
                observed_at=primary.get("observed_at", now_iso),
                project_id=primary.get("project_id", ""),
            ))

    return PersonaReviewResult(
        promotions=tuple(promotions),
        blocked_promotions=tuple(blocked_promotions),
        superseded=tuple(superseded),
    )


def record_supersession(
    result: PersonaReviewResult,
    prior_key: str,
    prior_value: str,
    new_value: str,
    observed_at: str,
) -> PersonaReviewResult:
    """Record a superseded preference and return updated result.

    The superseded entry remains historically traceable via trace().
    """
    superseded_id = f"{prior_key}|{prior_value}|{observed_at}"
    new_entry = SupersededEntry(
        superseded_id=superseded_id,
        prior_key=prior_key,
        prior_value=prior_value,
        new_value=new_value,
        observed_at=observed_at,
    )
    updated_superseded = result.superseded + (new_entry,)
    return PersonaReviewResult(
        promotions=result.promotions,
        blocked_promotions=result.blocked_promotions,
        superseded=updated_superseded,
    )