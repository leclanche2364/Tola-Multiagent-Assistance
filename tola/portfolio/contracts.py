"""Portfolio data contracts for Tola Batch T1.

Typed frozen dataclasses with provenance fields and entity-specific
authoritative-source enums.  Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Authoritative-source enum (shared)
# ---------------------------------------------------------------------------

class Source(Enum):
    """Single authoritative source for each portfolio entity type."""

    SOURCE_BLACKBOARD = "blackboard"
    SOURCE_LOCAL_DOC = "local_doc"
    SOURCE_USER_EXPLICIT = "user_explicit"
    SOURCE_CONVERSATION = "conversation"


# ---------------------------------------------------------------------------
# Provenance mixin fields (frozen dataclasses inherit these)
# ---------------------------------------------------------------------------

PROVENANCE_FIELDS = ("source_system", "source_id", "fetched_at", "source_version")


# ---------------------------------------------------------------------------
# Entity contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Project:
    project_id: str
    project_name: str
    description: Optional[str] = None
    status: str = "active"
    strategic_priority: int = 5
    owner_agent_id: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Goal:
    goal_id: str
    project_id: str
    goal_name: str
    description: Optional[str] = None
    status: str = "open"
    owner_agent_id: Optional[str] = None
    due_date: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Milestone:
    milestone_id: str
    goal_id: str
    title: str
    description: Optional[str] = None
    status: str = "pending"
    due_date: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Task:
    task_id: str
    idempotency_key: str
    title: str
    instructions: Optional[str] = None
    parent_task_id: Optional[str] = None
    project_id: Optional[str] = None
    goal_id: Optional[str] = None
    required_output: Optional[str] = None
    success_criteria: list = field(default_factory=list)
    requested_by: str = ""
    assigned_to: str = ""
    status: str = "pending"
    risk_class: str = "A0"
    model_route: Optional[str] = None
    allowed_tools: list = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    deadline: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Commitment:
    commitment_id: str
    task_id: str
    agent_name: str
    commitment_type: str
    details: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Deadline:
    deadline_id: str
    entity_type: str
    entity_id: str
    due_date: str
    urgency: str = "normal"
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    project_id: Optional[str] = None
    goal_id: Optional[str] = None
    title: str = ""
    description: Optional[str] = None
    status: str = "planned"
    hypothesis: Optional[str] = None
    result: Optional[str] = None
    decision_required: bool = False
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Metric:
    metric_id: str
    project_id: Optional[str] = None
    goal_id: Optional[str] = None
    metric_name: str = ""
    metric_value: float = 0.0
    unit: Optional[str] = None
    source: Optional[str] = None
    snapshot_at: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Risk:
    risk_id: str
    entity_type: str
    entity_id: str
    title: str = ""
    description: Optional[str] = None
    severity: str = "medium"
    status: str = "open"
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Decision:
    decision_id: str
    task_id: Optional[str] = None
    made_by: str = ""
    decision_type: str = ""
    rationale: Optional[str] = None
    payload: dict = field(default_factory=dict)
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Approval:
    approval_id: str
    task_id: Optional[str] = None
    requested_by: str = ""
    approval_type: str = ""
    payload: dict = field(default_factory=dict)
    status: str = "pending"
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""


@dataclass(frozen=True)
class Outcome:
    outcome_id: str
    task_id: Optional[str] = None
    experiment_id: Optional[str] = None
    status: str = "pending"
    summary: Optional[str] = None
    evidence_refs: list = field(default_factory=list)
    source_system: str = ""
    source_id: str = ""
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    source_version: str = ""