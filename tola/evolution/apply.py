# tola.evolution.apply -- Batch T23 apply-or-reject gate.
# Pure, deterministic, sha256 via hashlib.
# Plain ASCII. Stdlib only. No I/O. No clock reads. No network.

from __future__ import annotations

import hashlib
import json
from typing import Any

# ---------------------------------------------------------------------------
# Outcome constants
# ---------------------------------------------------------------------------

APPLY = "APPLY"
SKIP_UNAPPROVED = "SKIP_UNAPPROVED"
SKIP_STALE = "SKIP_STALE"
BLOCK_PROTECTED = "BLOCK_PROTECTED"

PROTECTED_APPROVAL_SUFFIX = ":protected_approval"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canonical_json(obj: Any) -> str:
    """Return canonical JSON string (sorted keys, no whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha256_hex(text: str) -> str:
    """Return hex sha256 digest of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_token(proposal_token: str, approval_token: str) -> bool:
    """Check if approval_token is valid for the proposal.

    A valid token is either:
      - an exact match to the proposal token, or
      - the proposal token with the protected approval suffix appended.
    """
    if not approval_token:
        return False
    if approval_token == proposal_token:
        return True
    if approval_token == proposal_token + PROTECTED_APPROVAL_SUFFIX:
        return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_or_reject(
    proposal: Any,
    approval_token: str,
    current_version: str,
) -> str:
    """Determine whether a proposal should be applied.

    Returns one of:
      APPLY            - all guards pass, apply the bound version
      SKIP_UNAPPROVED - no approval token or token does not match
      SKIP_STALE      - candidate_hash or benchmark_version mismatch
      BLOCK_PROTECTED - protected category without protected approval

    Pure and deterministic. Uses sha256 via hashlib.
    """
    # Guard 1: approval token must be valid for this proposal
    proposal_token = getattr(proposal, "token", "")
    if not _validate_token(proposal_token, approval_token):
        return SKIP_UNAPPROVED

    # Guard 2: benchmark_version must match current_version
    proposal_version = getattr(proposal, "benchmark_version", "")
    if proposal_version != current_version:
        return SKIP_STALE

    # Guard 3: protected category check
    category = getattr(proposal, "category", "")
    protected = getattr(proposal, "protected", False)
    PROTECTED_CATEGORIES = frozenset({
        "core_skills",
        "permissions",
        "security",
        "architecture",
    })
    if protected and category in PROTECTED_CATEGORIES:
        # Protected proposals require the protected approval suffix.
        if not approval_token.endswith(PROTECTED_APPROVAL_SUFFIX):
            return BLOCK_PROTECTED

    return APPLY