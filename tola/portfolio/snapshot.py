"""PortfolioSnapshot synthesis layer for Batch T2.

Builds a compact snapshot from authoritative sources without
inventing state.  Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tola.portfolio.contracts import (
    Approval,
    Commitment,
    Deadline,
    Experiment,
    Goal,
    Metric,
    Project,
    Risk,
    Task,
    Outcome,
)

# ---------------------------------------------------------------------------
# Snapshot dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PortfolioSnapshot:
    """Compact synthesis of the current portfolio state.

    All fields are summaries or references, never a dump of raw rows.
    """

    snapshot_version: str = "1.0"
    generated_at: str = ""
    projects: List[Project] = field(default_factory=list)
    active_goals: List[Goal] = field(default_factory=list)
    current_priorities: List[Dict[str, Any]] = field(default_factory=list)
    deadlines: List[Deadline] = field(default_factory=list)
    commitments: List[Commitment] = field(default_factory=list)
    capacity_summary: Dict[str, Any] = field(default_factory=dict)
    active_tasks: List[Task] = field(default_factory=list)
    blocked_tasks: List[Task] = field(default_factory=list)
    experiments: List[Experiment] = field(default_factory=list)
    material_metrics: List[Metric] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    pending_decisions: List[Any] = field(default_factory=list)
    pending_approvals: List[Approval] = field(default_factory=list)
    agent_state: Dict[str, Any] = field(default_factory=dict)
    recent_outcomes: List[Any] = field(default_factory=list)
    stalled_work: List[Any] = field(default_factory=list)
    source_versions: Dict[str, Dict[str, str]] = field(default_factory=dict)
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def portfolio_snapshot_build(sources: Dict[str, List[Any]]) -> PortfolioSnapshot:
    """Build a compact PortfolioSnapshot from authoritative source dicts.

    *sources* maps source names (e.g. "blackboard", "local_doc") to
    lists of entity dicts or objects with provenance fields.
    """
    now = datetime.now(timezone.utc).isoformat()

    projects: List[Project] = []
    goals: List[Goal] = []
    tasks: List[Task] = []
    deadlines: List[Deadline] = []
    commitments: List[Commitment] = []
    experiments: List[Experiment] = []
    metrics: List[Metric] = []
    risks: List[Risk] = []
    approvals: List[Approval] = []
    source_versions: Dict[str, Dict[str, str]] = {}
    warnings: List[str] = []

    for source_name, entities in sources.items():
        source_version = ""
        count = 0
        for entity in entities:
            count += 1
            if isinstance(entity, dict):
                ev = entity.get("source_version", "")
                if not source_version and ev:
                    source_version = ev
                cls = _entity_class(entity.get("entity_type", ""))
                if cls is Project:
                    projects.append(_dict_to_project(entity))
                elif cls is Goal:
                    goals.append(_dict_to_goal(entity))
                elif cls is Task:
                    tasks.append(_dict_to_task(entity))
                elif cls is Deadline:
                    deadlines.append(_dict_to_deadline(entity))
                elif cls is Commitment:
                    commitments.append(_dict_to_commitment(entity))
                elif cls is Experiment:
                    experiments.append(_dict_to_experiment(entity))
                elif cls is Metric:
                    metrics.append(_dict_to_metric(entity))
                elif cls is Risk:
                    risks.append(_dict_to_risk(entity))
                elif cls is Approval:
                    approvals.append(_dict_to_approval(entity))
            elif hasattr(entity, "source_version"):
                if not source_version and entity.source_version:
                    source_version = entity.source_version
                if isinstance(entity, Project):
                    projects.append(entity)
                elif isinstance(entity, Goal):
                    goals.append(entity)
                elif isinstance(entity, Task):
                    tasks.append(entity)
                elif isinstance(entity, Deadline):
                    deadlines.append(entity)
                elif isinstance(entity, Commitment):
                    commitments.append(entity)
                elif isinstance(entity, Experiment):
                    experiments.append(entity)
                elif isinstance(entity, Metric):
                    metrics.append(entity)
                elif isinstance(entity, Risk):
                    risks.append(entity)
                elif isinstance(entity, Approval):
                    approvals.append(entity)

        source_versions[source_name] = {
            "entity_count": count,
            "source_version": source_version or "unknown",
            "fetched_at": now,
        }

    # Critical-source check: blackboard is the primary source.
    if not sources.get("blackboard") and not sources.get("SOURCE_BLACKBOARD"):
        warnings.append(
            "Critical source 'blackboard' is missing; confidence reduced."
        )

    # Staleness check: any source with unknown version or zero entities.
    for sname, sver in source_versions.items():
        if sver["source_version"] == "unknown":
            warnings.append(
                f"Source '{sname}' has no version info; confidence reduced."
            )

    confidence = _compute_confidence(source_versions, warnings)

    # Build summaries (compact, counts not raw rows).
    capacity_summary = _build_capacity_summary(tasks, commitments)
    active_tasks = [t for t in tasks if t.status not in ("done", "closed", "cancelled")]
    blocked_tasks = [t for t in tasks if t.status == "blocked"]
    pending_approvals_list = [a for a in approvals if a.status == "pending"]

    # Current priorities: top-N by strategic_priority from projects + goals.
    current_priorities = _build_priorities(projects, goals)

    # Pending decisions: extract from sources where decision_type is set.
    pending_decisions = _extract_pending_decisions(sources)

    # Agent state: summary of agent assignments.
    agent_state = _build_agent_state(tasks, commitments)

    # Recent outcomes: last 5 outcomes by fetched_at.
    recent_outcomes = _extract_recent_outcomes(sources)

    # Stalled work: tasks with no progress beyond a threshold.
    stalled_work = _identify_stalled_work(tasks, sources)

    return PortfolioSnapshot(
        snapshot_version="1.0",
        generated_at=now,
        projects=projects,
        active_goals=goals,
        current_priorities=current_priorities,
        deadlines=deadlines,
        commitments=commitments,
        capacity_summary=capacity_summary,
        active_tasks=active_tasks,
        blocked_tasks=blocked_tasks,
        experiments=experiments,
        material_metrics=metrics,
        risks=risks,
        pending_decisions=pending_decisions,
        pending_approvals=pending_approvals_list,
        agent_state=agent_state,
        recent_outcomes=recent_outcomes,
        stalled_work=stalled_work,
        source_versions=source_versions,
        confidence=confidence,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def portfolio_snapshot_refresh(
    snapshot: PortfolioSnapshot, sources: Dict[str, List[Any]]
) -> PortfolioSnapshot:
    """Refresh a snapshot from current sources, preserving version history."""
    previous_versions = dict(snapshot.source_versions)
    new_snapshot = portfolio_snapshot_build(sources)

    # Merge version history: keep previous entries, overlay new ones.
    merged_versions = dict(previous_versions)
    merged_versions.update(new_snapshot.source_versions)

    # Preserve warnings from both old and new.
    combined_warnings = list(snapshot.warnings) + list(new_snapshot.warnings)

    # Deduplicate warnings.
    seen = set()
    unique_warnings = []
    for w in combined_warnings:
        if w not in seen:
            seen.add(w)
            unique_warnings.append(w)

    # Use the newer generated_at.
    return PortfolioSnapshot(
        snapshot_version=new_snapshot.snapshot_version,
        generated_at=new_snapshot.generated_at,
        projects=new_snapshot.projects,
        active_goals=new_snapshot.active_goals,
        current_priorities=new_snapshot.current_priorities,
        deadlines=new_snapshot.deadlines,
        commitments=new_snapshot.commitments,
        capacity_summary=new_snapshot.capacity_summary,
        active_tasks=new_snapshot.active_tasks,
        blocked_tasks=new_snapshot.blocked_tasks,
        experiments=new_snapshot.experiments,
        material_metrics=new_snapshot.material_metrics,
        risks=new_snapshot.risks,
        pending_decisions=new_snapshot.pending_decisions,
        pending_approvals=new_snapshot.pending_approvals,
        agent_state=new_snapshot.agent_state,
        recent_outcomes=new_snapshot.recent_outcomes,
        stalled_work=new_snapshot.stalled_work,
        source_versions=merged_versions,
        confidence=new_snapshot.confidence,
        warnings=unique_warnings,
    )


# ---------------------------------------------------------------------------
# Get accessor
# ---------------------------------------------------------------------------

def portfolio_snapshot_get(snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
    """Return the snapshot as-is (accessor)."""
    return snapshot


# ---------------------------------------------------------------------------
# Diff (material changes only)
# ---------------------------------------------------------------------------

def portfolio_snapshot_diff(
    old: PortfolioSnapshot, new: PortfolioSnapshot
) -> Dict[str, List[Any]]:
    """Return only material changes between two snapshots.

    Material changes are:
    - New or changed deadlines (by entity_id + due_date).
    - New or changed risks (by risk_id, status flip, or severity change).
    - Status flips on tasks/goals/projects.
    - New blockers or pending approvals that were not present before.

    Immaterial churn (timestamp-only updates, unchanged re-fetches,
    generated_at changes) is excluded.
    """
    changes: Dict[str, List[Any]] = {}

    # Deadlines: compare by (entity_type, entity_id, due_date).
    old_dl_keys = {(d.entity_type, d.entity_id, d.due_date) for d in old.deadlines}
    new_dl_keys = {(d.entity_type, d.entity_id, d.due_date) for d in new.deadlines}
    new_deadlines = [d for d in new.deadlines if (d.entity_type, d.entity_id, d.due_date) not in old_dl_keys]
    removed_deadlines = [d for d in old.deadlines if (d.entity_type, d.entity_id, d.due_date) not in new_dl_keys]
    if new_deadlines:
        changes["new_deadlines"] = new_deadlines
    if removed_deadlines:
        changes["removed_deadlines"] = removed_deadlines

    # Risks: compare by risk_id; material if new, status flip, or severity change.
    old_risks = {r.risk_id: r for r in old.risks}
    new_risks = {r.risk_id: r for r in new.risks}
    material_risks = []
    for rid, nr in new_risks.items():
        if rid not in old_risks:
            material_risks.append(nr)
        else:
            or_ = old_risks[rid]
            if or_.status != nr.status or or_.severity != nr.severity:
                material_risks.append(nr)
    if material_risks:
        changes["material_risks"] = material_risks

    # Status flips on tasks.
    old_tasks = {t.task_id: t for t in old.active_tasks}
    new_tasks = {t.task_id: t for t in new.active_tasks}
    status_flips = []
    for tid, nt in new_tasks.items():
        if tid in old_tasks and old_tasks[tid].status != nt.status:
            status_flips.append(nt)
    if status_flips:
        changes["status_flips"] = status_flips

    # New pending approvals.
    old_approval_ids = {a.approval_id for a in old.pending_approvals}
    new_pending = [a for a in new.pending_approvals if a.approval_id not in old_approval_ids]
    if new_pending:
        changes["new_pending_approvals"] = new_pending

    # New blocked tasks.
    old_blocked_ids = {t.task_id for t in old.blocked_tasks}
    new_blocked = [t for t in new.blocked_tasks if t.task_id not in old_blocked_ids]
    if new_blocked:
        changes["new_blocked_tasks"] = new_blocked

    # New pending decisions.
    old_decision_keys = set()
    for d in old.pending_decisions:
        if isinstance(d, dict):
            old_decision_keys.add((d.get("task_id", ""), d.get("decision_type", "")))
        elif hasattr(d, "task_id"):
            old_decision_keys.add((d.task_id, d.decision_type))
    new_pending_decisions = []
    for d in new.pending_decisions:
        key = (d.get("task_id", ""), d.get("decision_type", "")) if isinstance(d, dict) else (getattr(d, "task_id", ""), getattr(d, "decision_type", ""))
        if key not in old_decision_keys:
            new_pending_decisions.append(d)
    if new_pending_decisions:
        changes["new_pending_decisions"] = new_pending_decisions

    # Confidence drop.
    if new.confidence < old.confidence:
        changes["confidence_drop"] = {
            "old": old.confidence,
            "new": new.confidence,
            "warnings": new.warnings,
        }

    return changes


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def portfolio_snapshot_validate(snapshot: PortfolioSnapshot) -> Dict[str, Any]:
    """Structural + provenance validation.

    Reduces confidence and appends warnings when a critical source is
    missing or stale.  Never invents state to fill gaps.
    """
    issues: List[str] = []
    confidence = snapshot.confidence

    # Structural checks.
    if not snapshot.snapshot_version:
        issues.append("Missing snapshot_version.")
        confidence -= 0.2

    if not snapshot.generated_at:
        issues.append("Missing generated_at timestamp.")
        confidence -= 0.2

    # Source-versions checks.
    if not snapshot.source_versions:
        issues.append("No source_versions recorded; provenance untraceable.")
        confidence -= 0.3
    else:
        for sname, sver in snapshot.source_versions.items():
            ver = sver.get("source_version", "")
            if ver == "unknown" or not ver:
                issues.append(f"Source '{sname}' has unknown or empty version.")
                confidence -= 0.1
            count = sver.get("entity_count", 0)
            if count == 0:
                issues.append(f"Source '{sname}' contributed zero entities.")
                confidence -= 0.05

    # Critical source missing.
    has_blackboard = any(
        "blackboard" in sname.lower() for sname in snapshot.source_versions
    )
    if not has_blackboard:
        issues.append("Critical source 'blackboard' is missing from source_versions.")
        confidence -= 0.25

    # Confidence floor.
    confidence = max(0.0, min(1.0, confidence))

    # Merge with existing warnings (avoid duplicates).
    all_warnings = list(snapshot.warnings)
    for issue in issues:
        if issue not in all_warnings:
            all_warnings.append(issue)

    return {
        "valid": len(issues) == 0,
        "confidence": round(confidence, 2),
        "warnings": all_warnings,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _entity_type_from_dict(entity: Dict[str, Any]) -> str:
    """Return the entity type string from a dict, or empty string."""
    # Check common keys.
    for key in ("entity_type", "type", "model"):
        if key in entity:
            val = entity[key]
            if isinstance(val, str):
                return val.lower()
    return ""


def _entity_class(entity_type: str) -> type:
    """Map entity type string to contracts class."""
    mapping = {
        "project": Project,
        "goal": Goal,
        "task": Task,
        "deadline": Deadline,
        "commitment": Commitment,
        "experiment": Experiment,
        "metric": Metric,
        "risk": Risk,
        "approval": Approval,
    }
    return mapping.get(entity_type, object)


def _dict_to_project(d: Dict[str, Any]) -> Project:
    return Project(
        project_id=str(d.get("project_id", "")),
        project_name=str(d.get("project_name", "")),
        description=d.get("description"),
        status=str(d.get("status", "active")),
        strategic_priority=int(d.get("strategic_priority", 5)),
        owner_agent_id=d.get("owner_agent_id"),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_goal(d: Dict[str, Any]) -> Goal:
    return Goal(
        goal_id=str(d.get("goal_id", "")),
        project_id=str(d.get("project_id", "")),
        goal_name=str(d.get("goal_name", "")),
        description=d.get("description"),
        status=str(d.get("status", "open")),
        owner_agent_id=d.get("owner_agent_id"),
        due_date=d.get("due_date"),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_task(d: Dict[str, Any]) -> Task:
    return Task(
        task_id=str(d.get("task_id", "")),
        idempotency_key=str(d.get("idempotency_key", "")),
        title=str(d.get("title", "")),
        instructions=d.get("instructions"),
        parent_task_id=d.get("parent_task_id"),
        project_id=d.get("project_id"),
        goal_id=d.get("goal_id"),
        required_output=d.get("required_output"),
        success_criteria=d.get("success_criteria", []) or [],
        requested_by=str(d.get("requested_by", "")),
        assigned_to=str(d.get("assigned_to", "")),
        status=str(d.get("status", "pending")),
        risk_class=str(d.get("risk_class", "A0")),
        model_route=d.get("model_route"),
        allowed_tools=d.get("allowed_tools", []) or [],
        timeout_seconds=d.get("timeout_seconds"),
        deadline=d.get("deadline"),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_deadline(d: Dict[str, Any]) -> Deadline:
    return Deadline(
        deadline_id=str(d.get("deadline_id", "")),
        entity_type=str(d.get("entity_type", "")),
        entity_id=str(d.get("entity_id", "")),
        due_date=str(d.get("due_date", "")),
        urgency=str(d.get("urgency", "normal")),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_commitment(d: Dict[str, Any]) -> Commitment:
    return Commitment(
        commitment_id=str(d.get("commitment_id", "")),
        task_id=str(d.get("task_id", "")),
        agent_name=str(d.get("agent_name", "")),
        commitment_type=str(d.get("commitment_type", "")),
        details=d.get("details"),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_experiment(d: Dict[str, Any]) -> Experiment:
    return Experiment(
        experiment_id=str(d.get("experiment_id", "")),
        project_id=d.get("project_id"),
        goal_id=d.get("goal_id"),
        title=str(d.get("title", "")),
        description=d.get("description"),
        status=str(d.get("status", "planned")),
        hypothesis=d.get("hypothesis"),
        result=d.get("result"),
        decision_required=bool(d.get("decision_required", False)),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_metric(d: Dict[str, Any]) -> Metric:
    return Metric(
        metric_id=str(d.get("metric_id", "")),
        project_id=d.get("project_id"),
        goal_id=d.get("goal_id"),
        metric_name=str(d.get("metric_name", "")),
        metric_value=float(d.get("metric_value", 0.0)),
        unit=d.get("unit"),
        source=d.get("source"),
        snapshot_at=d.get("snapshot_at"),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_risk(d: Dict[str, Any]) -> Risk:
    return Risk(
        risk_id=str(d.get("risk_id", "")),
        entity_type=str(d.get("entity_type", "")),
        entity_id=str(d.get("entity_id", "")),
        title=str(d.get("title", "")),
        description=d.get("description"),
        severity=str(d.get("severity", "medium")),
        status=str(d.get("status", "open")),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _dict_to_approval(d: Dict[str, Any]) -> Approval:
    return Approval(
        approval_id=str(d.get("approval_id", "")),
        task_id=d.get("task_id"),
        requested_by=str(d.get("requested_by", "")),
        approval_type=str(d.get("approval_type", "")),
        payload=d.get("payload", {}) or {},
        status=str(d.get("status", "pending")),
        decided_by=d.get("decided_by"),
        decided_at=d.get("decided_at"),
        source_system=str(d.get("source_system", "")),
        source_id=str(d.get("source_id", "")),
        fetched_at=d.get("fetched_at") or datetime.now(timezone.utc),
        source_version=str(d.get("source_version", "")),
    )


def _compute_confidence(
    source_versions: Dict[str, Dict[str, Any]], warnings: List[str]
) -> float:
    """Compute confidence from source health."""
    base = 1.0
    for sname, sver in source_versions.items():
        ver = sver.get("source_version", "")
        if ver == "unknown" or not ver:
            base -= 0.1
        if sver.get("entity_count", 0) == 0:
            base -= 0.05
    # Deduct for each warning.
    base -= 0.05 * len(warnings)
    return max(0.0, min(1.0, round(base, 2)))


def _build_capacity_summary(tasks: List[Task], commitments: List[Commitment]) -> Dict[str, Any]:
    """Build a compact capacity summary (counts, not raw rows)."""
    total = len(tasks)
    active = sum(1 for t in tasks if t.status not in ("done", "closed", "cancelled"))
    blocked = sum(1 for t in tasks if t.status == "blocked")
    by_status: Dict[str, int] = {}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    return {
        "total_tasks": total,
        "active_tasks": active,
        "blocked_tasks": blocked,
        "by_status": by_status,
        "total_commitments": len(commitments),
    }


def _build_priorities(projects: List[Project], goals: List[Goal]) -> List[Dict[str, Any]]:
    """Build current priorities from project strategic_priority and goal status."""
    priorities: List[Dict[str, Any]] = []
    for p in sorted(projects, key=lambda x: x.strategic_priority):
        priorities.append(
            {
                "type": "project",
                "id": p.project_id,
                "name": p.project_name,
                "priority": p.strategic_priority,
                "status": p.status,
            }
        )
    for g in goals:
        if g.status == "open":
            priorities.append(
                {
                    "type": "goal",
                    "id": g.goal_id,
                    "name": g.goal_name,
                    "project_id": g.project_id,
                    "status": g.status,
                }
            )
    return priorities


def _extract_pending_decisions(sources: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Extract pending decisions from sources."""
    decisions: List[Dict[str, Any]] = []
    for source_name, entities in sources.items():
        for entity in entities:
            if isinstance(entity, dict):
                etype = entity.get("entity_type", "")
                if etype == "decision" and entity.get("status") != "decided":
                    decisions.append(entity)
    return decisions


def _build_agent_state(tasks: List[Task], commitments: List[Commitment]) -> Dict[str, Any]:
    """Build a compact agent state summary."""
    agent_tasks: Dict[str, int] = {}
    for t in tasks:
        if t.assigned_to:
            agent_tasks[t.assigned_to] = agent_tasks.get(t.assigned_to, 0) + 1
    agent_commitments: Dict[str, int] = {}
    for c in commitments:
        agent_commitments[c.agent_name] = agent_commitments.get(c.agent_name, 0) + 1
    return {
        "agents_with_tasks": agent_tasks,
        "agents_with_commitments": agent_commitments,
    }


def _extract_recent_outcomes(sources: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Extract the 5 most recent outcomes from sources."""
    outcomes: List[Dict[str, Any]] = []
    for source_name, entities in sources.items():
        for entity in entities:
            if isinstance(entity, dict) and entity.get("entity_type") == "outcome":
                outcomes.append(entity)
    # Sort by fetched_at descending, take last 5.
    outcomes.sort(
        key=lambda x: x.get("fetched_at", ""),
        reverse=True,
    )
    return outcomes[:5]


def _identify_stalled_work(tasks: List[Task], sources: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Identify stalled tasks (status unchanged, no recent progress)."""
    stalled: List[Dict[str, Any]] = []
    for t in tasks:
        if t.status in ("blocked", "pending") and t.deadline:
            stalled.append(
                {
                    "task_id": t.task_id,
                    "title": t.title,
                    "status": t.status,
                    "deadline": t.deadline,
                    "reason": "stalled_no_progress",
                }
            )
    return stalled