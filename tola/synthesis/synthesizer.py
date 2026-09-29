# Synthesizer module for Batch T11 - Cross-Agent Synthesis.
# Plain ASCII. Stdlib only. Deterministic.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tola.synthesis.attribution import (
    EvidenceItem,
    EvidenceSource,
    attribute,
)


# ---------------------------------------------------------------------------
# Named rules (constants)
# ---------------------------------------------------------------------------

# Rule 1: Growth opportunities are constrained by Rhythm capacity.
# A capacity shortfall is noted in the decision but the opportunity
# is not suppressed.
RULE_GROWTH_CONSTRAINED_BY_CAPACITY = (
    "Growth opportunities are constrained by Rhythm capacity"
)

# Rule 2: Scholar protected requirements are preserved verbatim
# in decisions and can never be outweighed.
RULE_SCHOLAR_PROTECTED_PRESERVED = (
    "Scholar protected requirements are preserved verbatim"
)

# Rule 3: Conflicting evidence between specialists is listed in
# unresolved_conflicts; the decision text says "conflict unresolved"
# and never fabricates certainty.
RULE_CONFLICT_SURFACED_NOT_FABRICATED = (
    "Conflicting evidence is surfaced rather than fabricated"
)

# Rule 4: Missing specialist input generates a structured request
# (agent_id + what is needed) rather than a guess.
RULE_MISSING_INPUT_GENERATES_REQUEST = (
    "Missing specialist input generates a structured request"
)

# Rule 5: Decision and rationale lines each carry source attribution.
RULE_ATTRIBUTION_TRACEABLE = (
    "Decision and rationale carry source attribution"
)


# ---------------------------------------------------------------------------
# SynthesisResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SynthesisResult:
    """Result of cross-agent portfolio synthesis."""

    decision: str
    rationale: List[str]
    unresolved_conflicts: List[str]
    missing_inputs: List[Dict[str, str]]
    attribution: List[str]


# ---------------------------------------------------------------------------
# Synthesis engine
# ---------------------------------------------------------------------------

def synthesize_portfolio_decision(
    inputs: Dict[str, Any],
) -> SynthesisResult:
    """Synthesize a portfolio decision from specialist inputs.

    *inputs* is a dict keyed by specialist name:
      - "growth": dict with "evidence" (list of str) and
        "opportunities" (list of str)
      - "rhythm": dict with "capacity_summary" (dict) and
        "capacity_shortfall" (bool)
      - "scholar": dict with "obligations" (list of str) and
        "protected_requirements" (list of str)
      - "deadlines": dict with "active_deadlines" (list of str)
        and "deadline_conflicts" (list of str)

    Returns a SynthesisResult with decision, rationale,
    unresolved_conflicts, missing_inputs, and attribution lines.
    """
    rationale: List[str] = []
    unresolved_conflicts: List[str] = []
    missing_inputs: List[Dict[str, str]] = []
    attribution: List[str] = []
    decision_parts: List[str] = []

    # --- Check for missing specialist inputs ---
    required_specialists = ["growth", "rhythm", "scholar", "deadlines"]
    for specialist in required_specialists:
        if specialist not in inputs or inputs[specialist] is None:
            missing_inputs.append(
                {
                    "agent_id": specialist,
                    "what_is_needed": "specialist input for portfolio synthesis",
                }
            )

    # --- Growth evidence and opportunities ---
    growth = inputs.get("growth") or {}
    growth_evidence = growth.get("evidence", []) or []
    growth_opportunities = growth.get("opportunities", []) or []

    growth_tags: List[str] = []
    for ev in growth_evidence:
        tag = "growth:{ref}".format(ref=_make_ref("growth", ev))
        growth_tags.append(tag)
        attribution.append(
            _make_attribution_line("growth", ev, tag)
        )

    for opp in growth_opportunities:
        tag = "growth:{ref}".format(ref=_make_ref("growth", opp))
        growth_tags.append(tag)
        attribution.append(
            _make_attribution_line("growth", opp, tag)
        )

    # --- Rhythm capacity ---
    rhythm = inputs.get("rhythm") or {}
    capacity_summary = rhythm.get("capacity_summary", {}) or {}
    capacity_shortfall = bool(rhythm.get("capacity_shortfall", False))

    rhythm_tags: List[str] = []
    for key, val in capacity_summary.items():
        claim = "capacity {key}={val}".format(key=key, val=val)
        tag = "rhythm:{ref}".format(ref=_make_ref("rhythm", claim))
        rhythm_tags.append(tag)
        attribution.append(
            _make_attribution_line("rhythm", claim, tag)
        )

    # Rule 1: capacity shortfall constrains but does not suppress
    if capacity_shortfall:
        constraint_note = (
            "capacity shortfall constrains growth opportunities; "
            "opportunities noted but not suppressed"
        )
        rationale.append(
            _make_rationale_line(constraint_note, rhythm_tags)
        )
        decision_parts.append(
            "capacity shortfall: growth opportunities preserved"
        )
        for opp in growth_opportunities:
            decision_parts.append(
                "growth opportunity noted: {opp}".format(opp=opp)
            )

    # --- Scholar protected requirements ---
    scholar = inputs.get("scholar") or {}
    protected = scholar.get("protected_requirements", []) or []
    obligations = scholar.get("obligations", []) or []

    scholar_tags: List[str] = []
    for req in protected:
        tag = "scholar:{ref}".format(ref=_make_ref("scholar", req))
        scholar_tags.append(tag)
        attribution.append(
            _make_attribution_line("scholar", req, tag)
        )

    for obl in obligations:
        tag = "scholar:{ref}".format(ref=_make_ref("scholar", obl))
        scholar_tags.append(tag)
        attribution.append(
            _make_attribution_line("scholar", obl, tag)
        )

    # Rule 2: protected requirements preserved verbatim, never outweighed
    for req in protected:
        decision_parts.append(
            "scholar protected requirement preserved: {req}".format(req=req)
        )
    for obl in obligations:
        decision_parts.append(
            "scholar obligation noted: {obl}".format(obl=obl)
        )

    # --- Deadlines ---
    deadlines = inputs.get("deadlines") or {}
    active_deadlines = deadlines.get("active_deadlines", []) or []
    deadline_conflicts = deadlines.get("deadline_conflicts", []) or []

    deadline_tags: List[str] = []
    for dl in active_deadlines:
        tag = "deadlines:{ref}".format(ref=_make_ref("deadlines", dl))
        deadline_tags.append(tag)
        attribution.append(
            _make_attribution_line("deadlines", dl, tag)
        )

    for dc in deadline_conflicts:
        tag = "deadlines:{ref}".format(ref=_make_ref("deadlines", dc))
        deadline_tags.append(tag)
        attribution.append(
            _make_attribution_line("deadlines", dc, tag)
        )

    # --- Conflicting evidence detection ---
    # Rule 3: if growth opportunities conflict with scholar protected
    # requirements, list as unresolved conflict.
    conflict_found = False
    for opp in growth_opportunities:
        for req in protected:
            if _conflict_detected(opp, req):
                conflict_found = True
                conflict_msg = (
                    "Conflict between growth opportunity '{opp}' and "
                    "scholar protected requirement '{req}': conflict "
                    "unresolved".format(opp=opp, req=req)
                )
                unresolved_conflicts.append(conflict_msg)
                decision_parts.append(
                    "growth opportunity '{opp}' vs scholar requirement "
                    "'{req}': conflict unresolved".format(
                        opp=opp, req=req,
                    )
                )
    # Also check: growth evidence vs scholar protected requirements
    if not conflict_found:
        for ev in growth_evidence:
            for req in protected:
                if _conflict_detected(ev, req):
                    conflict_found = True
                    conflict_msg = (
                        "Conflict between growth evidence '{ev}' and "
                        "scholar protected requirement '{req}': conflict "
                        "unresolved".format(ev=ev, req=req)
                    )
                    unresolved_conflicts.append(conflict_msg)
                    decision_parts.append(
                        "growth evidence '{ev}' vs scholar requirement "
                        "'{req}': conflict unresolved".format(
                            ev=ev, req=req,
                        )
                    )
    # Check for competing-domain signals (growth push vs scholar
    # pull) even without keyword overlap.
    if not conflict_found and growth_opportunities and protected:
        for opp in growth_opportunities:
            for req in protected:
                opp_lower = opp.lower()
                req_lower = req.lower()
                growth_signals = [
                    "enter", "expand", "launch", "run",
                    "immediately", "now",
                ]
                scholar_signals = [
                    "do not defer", "not defer",
                    "preserve", "must not",
                ]
                has_growth_signal = any(
                    s in opp_lower for s in growth_signals
                )
                has_scholar_signal = any(
                    s in req_lower for s in scholar_signals
                )
                if has_growth_signal and has_scholar_signal:
                    conflict_found = True
                    conflict_msg = (
                        "Conflict between growth opportunity '{opp}' and "
                        "scholar protected requirement '{req}': conflict "
                        "unresolved".format(opp=opp, req=req)
                    )
                    unresolved_conflicts.append(conflict_msg)
                    decision_parts.append(
                        "growth opportunity '{opp}' vs scholar requirement "
                        "'{req}': conflict unresolved".format(
                            opp=opp, req=req,
                        )
                    )

    # --- Decision assembly ---
    if not decision_parts:
        if missing_inputs:
            decision = "Insufficient inputs to decide"
        else:
            decision = "No action required"
    else:
        decision = "; ".join(decision_parts)

    # --- Rationale lines carry attribution ---
    # Always add specialist rationale lines for each domain
    # that contributed evidence.
    if growth_evidence:
        rationale.append(
            _make_rationale_line(
                "Synthesis based on growth evidence",
                growth_tags,
            )
        )
    if capacity_summary:
        rationale.append(
            _make_rationale_line(
                "Capacity summary considered",
                rhythm_tags,
            )
        )
    if protected or obligations:
        rationale.append(
            _make_rationale_line(
                "Scholar obligations and requirements considered",
                scholar_tags,
            )
        )
    if active_deadlines:
        rationale.append(
            _make_rationale_line(
                "Deadlines considered",
                deadline_tags,
            )
        )

    # --- Add missing-input rationale ---
    for mi in missing_inputs:
        rationale.append(
            "Missing input from {agent_id}: {what}".format(
                agent_id=mi["agent_id"],
                what=mi["what_is_needed"],
            )
        )

    # --- Unresolved conflicts rationale ---
    for uc in unresolved_conflicts:
        rationale.append(uc)

    return SynthesisResult(
        decision=decision,
        rationale=rationale,
        unresolved_conflicts=unresolved_conflicts,
        missing_inputs=missing_inputs,
        attribution=attribution,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_ref(agent_id: str, text: str) -> str:
    """Create a deterministic reference string from agent and text."""
    # Use a simple hash-like deterministic ref from the text content.
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return "{agent}-{hash}".format(agent=agent_id[:4], hash=h)


def _make_attribution_line(
    agent_id: str, claim: str, tag: str
) -> str:
    """Format an attribution line."""
    return "{agent_id}: {claim} [{tag}]".format(
        agent_id=agent_id, claim=claim, tag=tag,
    )


def _make_rationale_line(text: str, tags: List[str]) -> str:
    """Format a rationale line with source tags."""
    if not tags:
        return text
    tag_str = " ".join(tags)
    return "{text} ({tag_str})".format(text=text, tag_str=tag_str)


def _conflict_detected(opportunity: str, requirement: str) -> bool:
    """Heuristic: detect if a growth opportunity conflicts with a
    scholar protected requirement.

    Simple keyword overlap check: if both share a significant word
    (3+ chars) that is not a common stop word, flag as conflict.
    """
    stop_words = {
        "the", "and", "for", "with", "from", "this", "that",
        "are", "not", "has", "was", "but", "can", "all",
        "its", "our", "you", "your", "may", "will", "must",
    }
    opp_words = {
        w.lower().strip(".,;:!?()[]")
        for w in opportunity.split()
        if len(w) >= 3 and w.lower() not in stop_words
    }
    req_words = {
        w.lower().strip(".,;:!?()[]")
        for w in requirement.split()
        if len(w) >= 3 and w.lower() not in stop_words
    }
    overlap = opp_words & req_words
    return len(overlap) >= 2