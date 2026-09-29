"""Agent operating profiles for Batch T4.

Defines availability-status enum and frozen profiles for TOLA,
RHYTHM, GROWTH, SCHOLAR, and MARKETING (future).
Plain ASCII.  Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AvailabilityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FUTURE_NOT_AVAILABLE = "FUTURE_NOT_AVAILABLE"
    DISABLED = "DISABLED"
    DEGRADED = "DEGRADED"


# Re-export convenience aliases kept for T4-09 and plan §7 shape
ACTIVE = AvailabilityStatus.ACTIVE
FUTURE_NOT_AVAILABLE = AvailabilityStatus.FUTURE_NOT_AVAILABLE
DISABLED = AvailabilityStatus.DISABLED
DEGRADED = AvailabilityStatus.DEGRADED
AVAILABLE = AvailabilityStatus.ACTIVE


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    domain: str
    responsibilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    skills: tuple[str, ...]
    availability_status: AvailabilityStatus
    activation_requirements: tuple[str, ...]
    version: str
    last_updated_at: str  # ISO date string, deterministic input only


# ---------------------------------------------------------------------------
# Frozen profiles (v1.0)
# ---------------------------------------------------------------------------

PROFILES: dict[str, AgentProfile] = {
    "tola": AgentProfile(
        agent_id="tola",
        domain="portfolio_executive",
        responsibilities=(
            "portfolio priorities",
            "cross-project trade-offs",
            "delegation",
            "goal-to-plan decomposition",
            "specialist selection",
            "success criteria",
            "plan review",
            "scope control",
            "project health assessment",
            "outcome verification",
            "stalled-work recovery",
            "materiality and attention decisions",
            "deciding when Rhythm must be queried",
            "accept/revise/stop/extend specialist work",
        ),
        allowed_tools=(
            "blackboard_read",
            "blackboard_write",
            "delegation_dispatch",
            "plan_review",
            "outcome_verify",
            "capacity_query",
            "portfolio_snapshot",
            "preference_observe",
            "improvement_proposal",
        ),
        forbidden_actions=(
            "direct_my_rhythm_write",
            "delegate_to_inactive_agent",
            "claim_specialist_domain",
            "silently_change_security_policy",
            "silently_change_tool_permissions",
            "silently_change_approval_boundaries",
            "silently_change_model_routing",
            "silently_change_external_integrations",
            "fabricate_portfolio_state",
            "close_incomplete_work_as_success",
        ),
        skills=(
            "portfolio-state-synthesis",
            "priority-triage",
            "goal-to-plan",
            "delegation-planner",
            "plan-critic",
            "cross-agent-synthesis",
            "outcome-verifier",
            "stalled-work-recovery",
            "scope-control",
            "decision-quality-check",
            "founder-briefing",
            "portfolio-review",
            "risk-and-dependency-scan",
            "follow-through",
            "persona-awareness",
            "preference-consolidation",
            "self-performance-review",
            "improvement-candidate-generator",
        ),
        availability_status=ACTIVE,
        activation_requirements=(),
        version="1.0.0",
        last_updated_at="2026-09-29",
    ),
    "rhythm": AgentProfile(
        agent_id="rhythm",
        domain="scheduling_and_capacity",
        responsibilities=(
            "work-shift truth",
            "realistic capacity",
            "schedule feasibility",
            "exact time placement",
            "My Rhythm writes",
            "dynamic replanning",
        ),
        allowed_tools=(
            "rhythm_schedule_read",
            "rhythm_schedule_write",
            "rhythm_capacity_query",
            "rhythm_capacity_report",
            "rhythm_replan",
        ),
        forbidden_actions=(
            "own_portfolio_priorities",
            "own_delegation_decisions",
            "own_success_criteria",
            "own_plan_review",
            "own_outcome_verification",
            "own_materiality_decisions",
            "product_growth_analysis",
            "learning_gap_detection",
        ),
        skills=(
            "shift-scheduling",
            "capacity-modeling",
            "time-placement",
            "dynamic-replanning",
            "conflict-detection",
        ),
        availability_status=ACTIVE,
        activation_requirements=(),
        version="1.0.0",
        last_updated_at="2026-09-29",
    ),
    "growth": AgentProfile(
        agent_id="growth",
        domain="product_and_growth",
        responsibilities=(
            "product/growth analysis",
            "acquisition intelligence",
            "activation intelligence",
            "conversion intelligence",
            "retention intelligence",
            "experiment design and analysis",
            "product metrics",
            "growth recommendations",
            "marketing work eligible under current Growth contract",
        ),
        allowed_tools=(
            "growth_analysis",
            "growth_experiment_design",
            "growth_metrics_read",
            "growth_recommendation_write",
            "funnel_analysis",
            "product_metrics_read",
            "marketing_work_under_contract",
        ),
        forbidden_actions=(
            "direct_schedule_write",
            "rhythm_schedule_placement",
            "learning_gap_detection",
            "curriculum_planning",
            "claim_specialist_domain_scheduling",
            "claim_specialist_domain_learning",
        ),
        skills=(
            "funnel-analysis",
            "experiment-design",
            "product-metrics",
            "growth-recommendation",
            "acquisition-analysis",
            "conversion-analysis",
            "retention-analysis",
        ),
        availability_status=ACTIVE,
        activation_requirements=(),
        version="1.0.0",
        last_updated_at="2026-09-29",
    ),
    "scholar": AgentProfile(
        agent_id="scholar",
        domain="learning_intelligence",
        responsibilities=(
            "learning intelligence",
            "curriculum planning",
            "evidence synthesis",
            "study requirements",
            "learning-gap detection",
        ),
        allowed_tools=(
            "scholar_learning_read",
            "scholar_curriculum_write",
            "scholar_gap_detect",
            "scholar_evidence_synthesize",
        ),
        forbidden_actions=(
            "product_growth_analysis",
            "funnel_analysis",
            "acquisition_execution",
            "schedule_placement",
            "claim_specialist_domain_scheduling",
            "claim_specialist_domain_growth",
        ),
        skills=(
            "learning-gap-detection",
            "curriculum-planning",
            "evidence-synthesis",
            "study-requirements",
        ),
        availability_status=ACTIVE,
        activation_requirements=(),
        version="1.0.0",
        last_updated_at="2026-09-29",
    ),
    "marketing": AgentProfile(
        agent_id="marketing",
        domain="marketing",
        responsibilities=(
            "acquisition execution",
            "SEO / ASO execution",
            "content distribution",
            "community growth",
            "campaign operations",
            "lifecycle / CRM marketing",
            "paid acquisition where explicitly authorised",
            "partnership / outreach execution",
        ),
        allowed_tools=(),
        forbidden_actions=(
            "direct_schedule_write",
            "product_growth_analysis_without_contract",
            "learning_gap_detection",
            "claim_specialist_domain_scheduling",
            "claim_specialist_domain_growth",
            "claim_specialist_domain_learning",
        ),
        skills=(),
        availability_status=FUTURE_NOT_AVAILABLE,
        activation_requirements=(
            "agent contract complete",
            "capability profile complete",
            "boundary rules complete",
            "allowed tools complete",
            "security review complete",
            "batch QA complete",
            "Tola delegation tests complete",
        ),
        version="1.0.0",
        last_updated_at="2026-09-29",
    ),
}

# ---------------------------------------------------------------------------
# Audit log: appended on every profile version change (T4-08)
# ---------------------------------------------------------------------------

PROFILE_VERSION_HISTORY: list[dict[str, Any]] = []


def update_profile_version(
    agent_id: str,
    new_version: str,
    changed_by: str,
    change_reason: str,
    timestamp: str,
) -> AgentProfile:
    """Return a new profile with bumped version and append audit entry.

    Deterministic: *timestamp* is an explicit input, never read from
    the system clock.
    """
    profile = PROFILES[agent_id]
    updated = AgentProfile(
        agent_id=profile.agent_id,
        domain=profile.domain,
        responsibilities=profile.responsibilities,
        allowed_tools=profile.allowed_tools,
        forbidden_actions=profile.forbidden_actions,
        skills=profile.skills,
        availability_status=profile.availability_status,
        activation_requirements=profile.activation_requirements,
        version=new_version,
        last_updated_at=timestamp,
    )
    PROFILES[agent_id] = updated
    PROFILE_VERSION_HISTORY.append(
        {
            "agent_id": agent_id,
            "old_version": profile.version,
            "new_version": new_version,
            "changed_by": changed_by,
            "reason": change_reason,
            "timestamp": timestamp,
        }
    )
    return updated