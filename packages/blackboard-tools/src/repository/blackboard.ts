// BlackboardRepository — Supabase direct (V1, Supabase-only persistence).
// Semantics per spec §9.6–§9.8: in-memory read cache, online writes with idempotency,
// optimistic concurrency with explicit CONFLICT, audit events on mutations.

import { BlackboardError, SupabaseAdapter, type PostgrestResponse } from "../adapters/supabase.ts";

// ---------- row types ----------

export interface AgentRow {
  agent_id: string;
  agent_name: "tola" | "rhythm" | "growth" | "scholar";
  role: string;
  status: "active" | "paused" | "retired";
  config: Record<string, unknown>;
}

export interface ProjectRow {
  project_id: string;
  project_name: string;
  description: string | null;
  status: "active" | "paused" | "completed" | "archived";
  strategic_priority: number;
  owner_agent_id: string | null;
  version: number;
}

export interface GoalRow {
  goal_id: string;
  project_id: string;
  goal_name: string;
  description: string | null;
  status: "open" | "in_progress" | "blocked" | "achieved" | "dropped";
  owner_agent_id: string | null;
  due_date: string | null;
  version: number;
}

export interface TaskRow {
  task_id: string;
  idempotency_key: string;
  parent_task_id: string | null;
  project_id: string | null;
  goal_id: string | null;
  title: string;
  instructions: string | null;
  context_refs: unknown[];
  required_output: string | null;
  success_criteria: unknown[];
  requested_by: string;
  assigned_to: string;
  status: "pending" | "in_progress" | "blocked" | "needs_approval" | "completed" | "failed" | "cancelled";
  risk_class: "A0" | "A1" | "A2" | "A3";
  model_route: "R0" | "R1" | "R2" | "R3" | "R4" | null;
  version: number;
}

export interface TaskRunRow {
  run_id: string;
  task_id: string;
  idempotency_key: string;
  attempt: number;
  status: "running" | "success" | "partial" | "blocked" | "needs_approval" | "failed";
  summary: string | null;
  outputs: unknown[];
  evidence_refs: unknown[];
  tool_actions: unknown[];
  blockers: unknown[];
  verification: Record<string, unknown>;
  started_at: string;
  finished_at: string | null;
}

export interface ModelRunRow {
  model_run_id: string;
  task_run_id: string | null;
  model_route: "R0" | "R1" | "R2" | "R3" | "R4";
  model_id: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
  status: "completed" | "failed" | "timeout";
  created_at: string;
}

export interface DecisionRow {
  decision_id: string;
  task_id: string | null;
  made_by: string;
  decision_type: string;
  rationale: string | null;
  payload: Record<string, unknown>;
}

export interface MetricRow {
  metric_id: string;
  project_id: string | null;
  goal_id: string | null;
  metric_name: string;
  metric_value: number;
  unit: string | null;
  source: string | null;
  idempotency_key: string | null;
}

export interface ScheduleConstraintRow {
  constraint_id: string;
  agent_name: string | null;
  constraint_type: "shift" | "block" | "recurring" | "one_off" | "blackout";
  title: string;
  starts_at: string;
  ends_at: string;
  version: number;
}

export interface ApprovalRow {
  approval_id: string;
  task_id: string | null;
  requested_by: string;
  approval_type: string;
  payload: Record<string, unknown>;
  status: "pending" | "approved" | "rejected" | "expired";
  decided_by: string | null;
  decided_at: string | null;
}

export interface AgentEventRow {
  event_id: string;
  agent_name: string;
  task_id: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface SkillRow {
  skill_id: string;
  skill_name: string;
  owner_agent_id: string | null;
  origin_type: "native" | "external" | "generated";
  source_repository: string | null;
  source_version: string | null;
  licence: string | null;
  local_revision: number;
  status: "quarantined" | "reviewing" | "testing" | "approved" | "active" | "rejected" | "retired";
  approved_by: string | null;
  approved_at: string | null;
  content_hash: string;
}

// ---------- write inputs ----------

export interface CreateTaskInput {
  idempotency_key: string; // caller-provided stable operation id (uuid)
  project_id?: string | null;
  goal_id?: string | null;
  parent_task_id?: string | null;
  title: string;
  instructions?: string;
  context_refs?: unknown[];
  required_output?: string;
  success_criteria?: unknown[];
  requested_by: string;
  assigned_to: string;
  risk_class?: TaskRow["risk_class"];
  model_route?: TaskRow["model_route"];
  timeout_seconds?: number;
  deadline?: string;
}

export interface TaskPatch {
  title?: string;
  instructions?: string;
  assigned_to?: string;
  status?: TaskRow["status"];
  risk_class?: TaskRow["risk_class"];
  model_route?: TaskRow["model_route"];
  required_output?: string;
}

export interface SkillPromotionInput {
  skill_name: string;
  origin_type: SkillRow["origin_type"];
  content_hash: string; // required: sha256 hex
  source_repository: string;
  source_version: string;
  licence?: string;
  local_revision: number;
  owner_agent_id?: string | null;
}

// ---------- cache (in-memory only, §9.6) ----------

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

const TTL_PROJECT_GOAL_MS = 5 * 60_000; // ~5 minutes
const TTL_TASKS_MS = 60_000; // ~60 seconds

export class BlackboardRepository {
  private db: SupabaseAdapter;
  private projectCache = new Map<string, CacheEntry<ProjectRow>>();
  private goalCache = new Map<string, CacheEntry<GoalRow>>();
  private tasksCache: CacheEntry<TaskRow[]> | null = null;
  private cacheStats = { projectHits: 0, goalHits: 0, taskHits: 0, projectMisses: 0, goalMisses: 0, taskMisses: 0 };

  constructor(db: SupabaseAdapter) {
    this.db = db;
  }

  cacheStatsSnapshot(): typeof this.cacheStats {
    return { ...this.cacheStats };
  }

  // ---------- reads (read-through cache) ----------

  async getProject(projectId: string): Promise<ProjectRow> {
    const hit = this.projectCache.get(projectId);
    if (hit && hit.expiresAt > Date.now()) {
      this.cacheStats.projectHits++;
      return hit.value;
    }
    this.cacheStats.projectMisses++;
    const { rows } = await this.db.request<ProjectRow>("GET", "projects", {
      query: { project_id: `eq.${projectId}`, select: "*", limit: "1" },
    });
    if (rows.length === 0) throw new BlackboardError("NOT_FOUND", `project ${projectId} not found`);
    const row = rows[0];
    this.projectCache.set(projectId, { value: row, expiresAt: Date.now() + TTL_PROJECT_GOAL_MS });
    return row;
  }

  async listProjects(): Promise<ProjectRow[]> {
    const { rows } = await this.db.request<ProjectRow>("GET", "projects", {
      query: { select: "*", order: "created_at.desc" },
    });
    return rows;
  }

  async getGoal(goalId: string): Promise<GoalRow> {
    const hit = this.goalCache.get(goalId);
    if (hit && hit.expiresAt > Date.now()) {
      this.cacheStats.goalHits++;
      return hit.value;
    }
    this.cacheStats.goalMisses++;
    const { rows } = await this.db.request<GoalRow>("GET", "goals", {
      query: { goal_id: `eq.${goalId}`, select: "*", limit: "1" },
    });
    if (rows.length === 0) throw new BlackboardError("NOT_FOUND", `goal ${goalId} not found`);
    const row = rows[0];
    this.goalCache.set(goalId, { value: row, expiresAt: Date.now() + TTL_PROJECT_GOAL_MS });
    return row;
  }

  async listGoals(projectId?: string): Promise<GoalRow[]> {
    const query: Record<string, string> = { select: "*", order: "created_at.desc" };
    if (projectId) query.project_id = `eq.${projectId}`;
    const { rows } = await this.db.request<GoalRow>("GET", "goals", { query });
    return rows;
  }

  async getTask(taskId: string): Promise<TaskRow> {
    const { rows } = await this.db.request<TaskRow>("GET", "tasks", {
      query: { task_id: `eq.${taskId}`, select: "*", limit: "1" },
    });
    if (rows.length === 0) throw new BlackboardError("NOT_FOUND", `task ${taskId} not found`);
    return rows[0];
  }

  async listActiveTasks(): Promise<TaskRow[]> {
    const hit = this.tasksCache;
    if (hit && hit.expiresAt > Date.now()) {
      this.cacheStats.taskHits++;
      return hit.value;
    }
    this.cacheStats.taskMisses++;
    const { rows } = await this.db.request<TaskRow>("GET", "tasks", {
      query: {
        select: "*",
        status: "in.(pending,in_progress,blocked,needs_approval)",
        order: "created_at.desc",
      },
    });
    this.tasksCache = { value: rows, expiresAt: Date.now() + TTL_TASKS_MS };
    return rows;
  }

  async listScheduleConstraints(fromIso: string, toIso: string): Promise<ScheduleConstraintRow[]> {
    this.requireValidIso(fromIso, "starts_at");
    this.requireValidIso(toIso, "ends_at");
    const sp = new URLSearchParams({
      select: "*",
      starts_at: `lt.${toIso}`,
      ends_at: `gt.${fromIso}`,
      order: "starts_at.asc",
    });
    const { rows } = await this.db.request<ScheduleConstraintRow>("GET", "schedule_constraints", { searchParams: sp });
    return rows;
  }

  async getApproval(approvalId: string): Promise<ApprovalRow> {
    const { rows } = await this.db.request<ApprovalRow>("GET", "approvals", {
      query: { approval_id: `eq.${approvalId}`, select: "*", limit: "1" },
    });
    if (rows.length === 0) throw new BlackboardError("NOT_FOUND", `approval ${approvalId} not found`);
    return rows[0];
  }

  async listApprovals(status: ApprovalRow["status"] = "pending"): Promise<ApprovalRow[]> {
    const { rows } = await this.db.request<ApprovalRow>("GET", "approvals", {
      query: { status: `eq.${status}`, select: "*", order: "created_at.desc" },
    });
    return rows;
  }

  // ---------- writes ----------

  async createTask(input: CreateTaskInput): Promise<TaskRow> {
    this.validateTaskInput(input);
    const body = {
      idempotency_key: input.idempotency_key,
      project_id: input.project_id ?? null,
      goal_id: input.goal_id ?? null,
      parent_task_id: input.parent_task_id ?? null,
      title: input.title,
      instructions: input.instructions ?? null,
      context_refs: input.context_refs ?? [],
      required_output: input.required_output ?? null,
      success_criteria: input.success_criteria ?? [],
      requested_by: input.requested_by,
      assigned_to: input.assigned_to,
      risk_class: input.risk_class ?? "A0",
      model_route: input.model_route ?? null,
      timeout_seconds: input.timeout_seconds ?? null,
      deadline: input.deadline ?? null,
    };

    // Idempotent insert: duplicate idempotency_key is ignored, then we read back
    // the existing row so replaying the same operation has one authoritative effect.
    const res = await this.db.request<TaskRow>("POST", "tasks", {
      body,
      query: { on_conflict: "idempotency_key" },
      prefer: "resolution=ignore-duplicates,return=representation",
    });

    if (res.rows.length === 1 && res.rows[0].idempotency_key === input.idempotency_key) {
      const task = res.rows[0];
      await this.audit(input.requested_by, task.task_id, "task.created", { title: task.title });
      this.invalidateTaskCaches();
      return task;
    }

    // Replay or silent conflict-ignore: fetch the authoritative row.
    const existing = await this.db.request<TaskRow>("GET", "tasks", {
      query: { idempotency_key: `eq.${input.idempotency_key}`, select: "*", limit: "1" },
    });
    if (existing.rows.length === 0) {
      throw new BlackboardError("MALFORMED", "insert reported success but row is not readable");
    }
    return existing.rows[0];
  }

  async updateTask(taskId: string, expectedVersion: number, patch: TaskPatch, actingAgent: string): Promise<TaskRow> {
    if (!Number.isInteger(expectedVersion) || expectedVersion < 1) {
      throw new BlackboardError("VALIDATION", "expectedVersion must be a positive integer");
    }
    this.validateAgentName(actingAgent, "acting agent");
    const allowed: TaskPatch = {};
    if (patch.title !== undefined) allowed.title = patch.title;
    if (patch.instructions !== undefined) allowed.instructions = patch.instructions;
    if (patch.assigned_to !== undefined) {
      this.validateAgentName(patch.assigned_to, "assigned_to");
      allowed.assigned_to = patch.assigned_to;
    }
    if (patch.status !== undefined) allowed.status = patch.status;
    if (patch.risk_class !== undefined) allowed.risk_class = patch.risk_class;
    if (patch.model_route !== undefined) allowed.model_route = patch.model_route;
    if (patch.required_output !== undefined) allowed.required_output = patch.required_output;
    if (Object.keys(allowed).length === 0) {
      throw new BlackboardError("VALIDATION", "empty patch: nothing to update");
    }
    const body = { ...allowed, version: expectedVersion + 1 };

    // Optimistic concurrency: the WHERE clause pins the expected version.
    const res = await this.db.request<TaskRow>("PATCH", "tasks", {
      searchParams: new URLSearchParams({ task_id: `eq.${taskId}`, version: `eq.${expectedVersion}`, select: "*" }),
      body,
      prefer: "return=representation",
    });

    if (res.rows.length === 1) {
      const task = res.rows[0];
      await this.audit(actingAgent, task.task_id, "task.updated", { patch: allowed, version: task.version });
      this.invalidateTaskCaches();
      return task;
    }

    // Zero rows: either stale version (CONFLICT) or the task is gone (NOT_FOUND).
    const probe = await this.db.request<TaskRow>("GET", "tasks", {
      query: { task_id: `eq.${taskId}`, select: "version,task_id", limit: "1" },
    });
    if (probe.rows.length === 0) throw new BlackboardError("NOT_FOUND", `task ${taskId} not found`);
    throw new BlackboardError(
      "CONFLICT",
      `stale write: expected version ${expectedVersion}, authoritative version is ${probe.rows[0].version}`,
      { taskId, authoritativeVersion: probe.rows[0].version },
    );
  }

  async recordDecision(input: {
    task_id?: string | null;
    made_by: string;
    decision_type: string;
    rationale?: string;
    payload?: Record<string, unknown>;
  }): Promise<DecisionRow> {
    this.validateAgentName(input.made_by, "made_by");
    if (!input.decision_type || input.decision_type.length > 120) {
      throw new BlackboardError("VALIDATION", "decision_type required (max 120 chars)");
    }
    const res = await this.db.request<DecisionRow>("POST", "decisions", {
      body: {
        task_id: input.task_id ?? null,
        made_by: input.made_by,
        decision_type: input.decision_type,
        rationale: input.rationale ?? null,
        payload: input.payload ?? {},
      },
      prefer: "return=representation",
    });
    const row = this.expectOne(res, "decisions");
    await this.audit(input.made_by, input.task_id ?? null, "decision.recorded", { decision_type: input.decision_type });
    return row;
  }

  async recordMetric(input: {
    idempotency_key?: string | null;
    project_id?: string | null;
    goal_id?: string | null;
    metric_name: string;
    metric_value: number;
    unit?: string;
    source?: string;
  }): Promise<MetricRow> {
    if (!input.metric_name || input.metric_name.length > 120) {
      throw new BlackboardError("VALIDATION", "metric_name required (max 120 chars)");
    }
    if (typeof input.metric_value !== "number" || !Number.isFinite(input.metric_value)) {
      throw new BlackboardError("VALIDATION", "metric_value must be a finite number");
    }
    const res = await this.db.request<MetricRow>("POST", "metrics", {
      body: {
        idempotency_key: input.idempotency_key ?? null,
        project_id: input.project_id ?? null,
        goal_id: input.goal_id ?? null,
        metric_name: input.metric_name,
        metric_value: input.metric_value,
        unit: input.unit ?? null,
        source: input.source ?? null,
      },
      ...(input.idempotency_key ? { query: { on_conflict: "idempotency_key" } } : {}),
      prefer: "return=representation",
    });
    const row = this.expectOne(res, "metrics");
    return row;
  }

  async requestApproval(input: {
    task_id?: string | null;
    requested_by: string;
    approval_type: string;
    payload?: Record<string, unknown>;
  }): Promise<ApprovalRow> {
    this.validateAgentName(input.requested_by, "requested_by");
    if (!input.approval_type || input.approval_type.length > 120) {
      throw new BlackboardError("VALIDATION", "approval_type required (max 120 chars)");
    }
    const res = await this.db.request<ApprovalRow>("POST", "approvals", {
      body: {
        task_id: input.task_id ?? null,
        requested_by: input.requested_by,
        approval_type: input.approval_type,
        payload: input.payload ?? {},
      },
      prefer: "return=representation",
    });
    const row = this.expectOne(res, "approvals");
    await this.audit(input.requested_by, input.task_id ?? null, "approval.requested", {
      approval_type: input.approval_type,
    });
    return row;
  }

  async getScheduleConstraintsBetween(fromIso: string, toIso: string): Promise<ScheduleConstraintRow[]> {
    return this.listScheduleConstraints(fromIso, toIso);
  }

  async recordAgentEvent(input: {
    agent_name: string;
    task_id?: string | null;
    event_type: string;
    payload?: Record<string, unknown>;
  }): Promise<AgentEventRow> {
    this.validateAgentName(input.agent_name, "agent_name");
    if (!input.event_type || input.event_type.length > 120) {
      throw new BlackboardError("VALIDATION", "event_type required (max 120 chars)");
    }
    const res = await this.db.request<AgentEventRow>("POST", "agent_events", {
      body: {
        agent_name: input.agent_name,
        task_id: input.task_id ?? null,
        event_type: input.event_type,
        payload: input.payload ?? {},
      },
      prefer: "return=representation",
    });
    return this.expectOne(res, "agent_events");
  }

  async listAgentEventsForTask(taskId: string): Promise<AgentEventRow[]> {
    const { rows } = await this.db.request<AgentEventRow>("GET", "agent_events", {
      query: { task_id: `eq.${taskId}`, select: "*", order: "created_at.asc" },
    });
    return rows;
  }

  // ---------- task runs (Batch 6) ----------

  async startTaskRun(input: {
    task_id: string;
    idempotency_key: string;
    attempt?: number;
    summary?: string | null;
  }): Promise<TaskRunRow> {
    if (!isUuid(input.task_id)) {
      throw new BlackboardError("VALIDATION", "task_id must be a uuid");
    }
    if (!isUuid(input.idempotency_key)) {
      throw new BlackboardError("VALIDATION", "idempotency_key must be a uuid");
    }
    const attempt = input.attempt ?? 1;
    if (!Number.isInteger(attempt) || attempt < 1) {
      throw new BlackboardError("VALIDATION", "attempt must be a positive integer");
    }
    const res = await this.db.request<TaskRunRow>("POST", "task_runs", {
      body: {
        task_id: input.task_id,
        idempotency_key: input.idempotency_key,
        attempt,
        summary: input.summary ?? null,
      },
      prefer: "return=representation",
    });
    return this.expectOne(res, "task_runs");
  }

  async completeTaskRun(input: {
    run_id: string;
    status: TaskRunRow["status"];
    summary?: string | null;
  }): Promise<TaskRunRow> {
    if (!isUuid(input.run_id)) {
      throw new BlackboardError("VALIDATION", "run_id must be a uuid");
    }
    const allowed: TaskRunRow["status"][] = ["running", "success", "partial", "blocked", "needs_approval", "failed"];
    if (!allowed.includes(input.status)) {
      throw new BlackboardError("VALIDATION", "invalid task run status");
    }
    const res = await this.db.request<TaskRunRow>("PATCH", "task_runs", {
      searchParams: new URLSearchParams({ run_id: `eq.${input.run_id}` }),
      body: {
        status: input.status,
        summary: input.summary ?? null,
        finished_at: new Date().toISOString(),
      },
      prefer: "return=representation",
    });
    return this.expectOne(res, "task_runs");
  }

  async listTaskRunsForTask(taskId: string): Promise<TaskRunRow[]> {
    if (!isUuid(taskId)) {
      throw new BlackboardError("VALIDATION", "task_id must be a uuid");
    }
    const { rows } = await this.db.request<TaskRunRow>("GET", "task_runs", {
      query: { task_id: `eq.${taskId}`, select: "*", order: "started_at.asc" },
    });
    return rows;
  }

  async recordModelRun(input: {
    task_run_id?: string | null;
    model_route: "R0" | "R1" | "R2" | "R3" | "R4";
    model_id?: string | null;
    input_tokens?: number | null;
    output_tokens?: number | null;
    cost_usd?: number | null;
    latency_ms?: number | null;
    status?: "completed" | "failed" | "timeout";
  }): Promise<ModelRunRow> {
    if (!/^(R0|R1|R2|R3|R4)$/.test(input.model_route)) {
      throw new BlackboardError("VALIDATION", "model_route must be R0|R1|R2|R3|R4");
    }
    if (input.task_run_id !== undefined && input.task_run_id !== null && !isUuid(input.task_run_id)) {
      throw new BlackboardError("VALIDATION", "task_run_id must be a uuid");
    }
    if (input.status !== undefined && !["completed", "failed", "timeout"].includes(input.status)) {
      throw new BlackboardError("VALIDATION", "status must be completed|failed|timeout");
    }
    const res = await this.db.request<ModelRunRow>("POST", "model_runs", {
      body: {
        task_run_id: input.task_run_id ?? null,
        model_route: input.model_route,
        model_id: input.model_id ?? null,
        input_tokens: input.input_tokens ?? null,
        output_tokens: input.output_tokens ?? null,
        cost_usd: input.cost_usd ?? null,
        latency_ms: input.latency_ms ?? null,
        status: input.status ?? "completed",
      },
      prefer: "return=representation",
    });
    return this.expectOne(res, "model_runs");
  }

  async listModelRunsForTaskRun(taskRunId: string): Promise<ModelRunRow[]> {
    if (!isUuid(taskRunId)) {
      throw new BlackboardError("VALIDATION", "task_run_id must be a uuid");
    }
    const { rows } = await this.db.request<ModelRunRow>("GET", "model_runs", {
      query: { task_run_id: `eq.${taskRunId}`, select: "*", order: "created_at.asc" },
    });
    return rows;
  }

  // ---------- skills ----------

  async registerSkill(input: SkillPromotionInput): Promise<SkillRow> {
    this.validateSkillMetadata(input); // T4.4 gate: reject incomplete provenance before any write
    const res = await this.db.request<SkillRow>("POST", "skill_registry", {
      body: {
        skill_name: input.skill_name,
        owner_agent_id: input.owner_agent_id ?? null,
        origin_type: input.origin_type,
        source_repository: input.source_repository,
        source_version: input.source_version,
        licence: input.licence ?? null,
        local_revision: input.local_revision,
        content_hash: input.content_hash,
        // status defaults to 'quarantined' at the DB level; we set it explicitly for clarity
        status: "quarantined",
      },
      prefer: "return=representation",
    });
    return this.expectOne(res, "skill_registry");
  }

  async promoteSkill(skillName: string, approvedBy: string): Promise<SkillRow> {
    this.validateAgentName(approvedBy, "approved_by");
    // Promotion requires the skill to already carry complete provenance metadata.
    const current = await this.db.request<SkillRow>("GET", "skill_registry", {
      query: { skill_name: `eq.${skillName}`, select: "*", order: "local_revision.desc", limit: "1" },
    });
    if (current.rows.length === 0) throw new BlackboardError("NOT_FOUND", `skill ${skillName} not registered`);
    const row = current.rows[0];
    try {
      this.validateSkillMetadata({
        skill_name: row.skill_name,
        origin_type: row.origin_type,
        content_hash: row.content_hash,
        source_repository: row.source_repository ?? "",
        source_version: row.source_version ?? "",
        local_revision: row.local_revision,
      });
    } catch (err) {
      throw new BlackboardError(
        "VALIDATION",
        `skill ${skillName} cannot be promoted: incomplete source/revision/hash metadata`,
        (err as BlackboardError).detail,
      );
    }
    const res = await this.db.request<SkillRow>("PATCH", "skill_registry", {
      searchParams: new URLSearchParams({ skill_id: `eq.${row.skill_id}`, select: "*" }),
      body: { status: "approved", approved_by: approvedBy, approved_at: new Date().toISOString() },
      prefer: "return=representation",
    });
    const updated = this.expectOne(res, "skill_registry");
    await this.audit(approvedBy, null, "skill.promoted", { skill_name: skillName, local_revision: row.local_revision });
    return updated;
  }

  async getSkill(skillName: string): Promise<SkillRow | null> {
    const { rows } = await this.db.request<SkillRow>("GET", "skill_registry", {
      query: { skill_name: `eq.${skillName}`, select: "*", order: "local_revision.desc", limit: "1" },
    });
    return rows[0] ?? null;
  }

  // ---------- internals ----------

  private async audit(agentName: string, taskId: string | null, eventType: string, payload: Record<string, unknown>): Promise<void> {
    try {
      await this.db.request<AgentEventRow>("POST", "agent_events", {
        body: { agent_name: agentName, task_id: taskId, event_type: eventType, payload },
        prefer: "return=representation",
      });
    } catch (err) {
      // The authority write may have landed; surface loudly, never fake success.
      throw new BlackboardError(
        "AUDIT_FAILED",
        `authority write landed but audit append failed (${eventType}): ${(err as Error).message}`,
        { taskId, eventType },
      );
    }
  }

  private expectOne<T>(res: PostgrestResponse<T>, table: string): T {
    if (res.rows.length === 0) {
      throw new BlackboardError("MALFORMED", `${table} insert returned no representation`);
    }
    return res.rows[0];
  }

  private validateTaskInput(input: CreateTaskInput): void {
    if (!input.idempotency_key || !isUuid(input.idempotency_key)) {
      throw new BlackboardError("VALIDATION", "idempotency_key must be a uuid");
    }
    if (!input.title || input.title.trim().length === 0 || input.title.length > 300) {
      throw new BlackboardError("VALIDATION", "title required (1..300 chars)");
    }
    this.validateAgentName(input.requested_by, "requested_by");
    this.validateAgentName(input.assigned_to, "assigned_to");
    if (input.project_id && !isUuid(input.project_id)) {
      throw new BlackboardError("VALIDATION", "project_id must be a uuid");
    }
    if (input.goal_id && !isUuid(input.goal_id)) {
      throw new BlackboardError("VALIDATION", "goal_id must be a uuid");
    }
  }

  private validateAgentName(name: string, field: string): void {
    if (!["tola", "rhythm", "growth", "scholar"].includes(name)) {
      throw new BlackboardError("VALIDATION", `${field} must be one of tola|rhythm|growth|scholar (got ${JSON.stringify(name)})`);
    }
  }

  private validateSkillMetadata(input: SkillPromotionInput): void {
    const missing: string[] = [];
    if (!input.skill_name) missing.push("skill_name");
    if (!isSha256Hex(input.content_hash)) missing.push("content_hash (must be 64-char sha256 hex)");
    if (!input.source_repository || input.source_repository.length === 0) missing.push("source_repository");
    if (!input.source_version || input.source_version.length === 0) missing.push("source_version");
    if (!Number.isInteger(input.local_revision) || input.local_revision < 1) missing.push("local_revision (>=1)");
    if (missing.length > 0) {
      throw new BlackboardError("VALIDATION", `skill metadata incomplete: ${missing.join("; ")}`, { missing });
    }
  }

  private requireValidIso(value: string, field: string): void {
    if (Number.isNaN(Date.parse(value))) {
      throw new BlackboardError("VALIDATION", `${field} must be an ISO-8601 timestamp`);
    }
  }

  private invalidateTaskCaches(): void {
    this.tasksCache = null;
  }
}

export function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

export function isSha256Hex(value: string): boolean {
  return /^[0-9a-f]{64}$/i.test(value);
}
