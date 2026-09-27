/**
 * Schema-style input validation for every openclaw-tools mutation.
 * Each validator rejects invalid payloads before any database/write
 * action occurs.  All validators return a narrow, typed input that
 * the caller may safely pass to the BlackboardRepository.
 *
 * Conventions follow blackboard-tools src/repository/blackboard.ts
 * validation patterns (isUuid, isSha256Hex, validateAgentName).
 */
import { redactError } from "./redact.ts";

// isUuid / isSha256Hex are inlined here to keep validate.ts self-contained
// and avoid dependency on the blackboard-tools package for pure validation.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SHA256_HEX_RE = /^[0-9a-f]{64}$/i;

export function isUuid(value: string): boolean {
  return UUID_RE.test(value);
}

export function isSha256Hex(value: string): boolean {
  return SHA256_HEX_RE.test(value);
}

// ---------- agent name whitelist (Tola-safe) ----------
const TOLA_AGENT_NAMES = ["tola", "rhythm", "growth", "scholar"];

/** Validate that *name* is one of the four permitted agent identifiers. */
export function validateAgentName(
  name: string,
  field: string
): name is `tola` | `rhythm` | `growth` | `scholar` {
  if (!TOLA_AGENT_NAMES.includes(name)) {
    throw new Error(
      `${field} must be one of ${TOLA_AGENT_NAMES.join("|")} (got ${JSON.stringify(name)})`
    );
  }
  return true;
}

// ---------- UUID v4 ----------
export function validateUuid(
  value: string | null | undefined
): value is string {
  if (!value || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)) {
    return false;
  }
  return true;
}

// ---------- CreateTaskInput shape ----------
export interface CreateTaskInput {
  idempotency_key: string;
  project_id?: string | null;
  goal_id?: string | null;
  parent_task_id?: string | null;
  title: string;
  instructions?: string | null;
  context_refs?: unknown[];
  required_output?: string | null;
  success_criteria?: unknown[];
  requested_by: string;
  assigned_to: string;
  risk_class?: "A0" | "A1" | "A2" | "A3";
  model_route?: "R0" | "R1" | "R2" | "R3" | "R4" | null;
  timeout_seconds?: number;
  deadline?: string;
}

/** Validate and narrow a raw object into a CreateTaskInput. */
export function validateCreateTaskInput(
  raw: unknown
): CreateTaskInput {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] create_task: payload must be an object");
  }
  const p = raw as Record<string, unknown>;

  // idempotency_key (uuid)
  if (!validateUuid(String(p.idempotency_key))) {
    throw new Error("[VALIDATION] idempotency_key must be a UUIDv4");
  }

  // title (1..300 chars)
  const title = String(p.title);
  if (title.length < 1 || title.length > 300) {
    throw new Error("[VALIDATION] title must be 1..300 chars");
  }

  // requested_by agent whitelist
  validateAgentName(String(p.requested_by), "requested_by");

  // assigned_to agent whitelist
  validateAgentName(String(p.assigned_to), "assigned_to");

  // project_id optional UUID
  if (p.project_id !== undefined && p.project_id !== null) {
    if (!validateUuid(String(p.project_id))) {
      throw new Error("[VALIDATION] project_id must be a UUIDv4");
    }
  }

  // goal_id optional UUID
  if (p.goal_id !== undefined && p.goal_id !== null) {
    if (!validateUuid(String(p.goal_id))) {
      throw new Error("[VALIDATION] goal_id must be a UUIDv4");
    }
  }

  // parent_task_id optional UUID
  if (p.parent_task_id !== undefined && p.parent_task_id !== null) {
    if (!validateUuid(String(p.parent_task_id))) {
      throw new Error("[VALIDATION] parent_task_id must be a UUIDv4");
    }
  }

  // instructions optional string
  if (p.instructions !== undefined && typeof p.instructions !== "string") {
    throw new Error("[VALIDATION] instructions must be a string");
  }

  // context_refs optional unknown[]
  if (p.context_refs !== undefined && !Array.isArray(p.context_refs)) {
    throw new Error("[VALIDATION] context_refs must be an array");
  }

  // required_output optional string
  if (
    p.required_output !== undefined &&
    p.required_output !== null &&
    typeof p.required_output !== "string"
  ) {
    throw new Error("[VALIDATION] required_output must be a string");
  }

  // success_criteria optional unknown[]
  if (p.success_criteria !== undefined && !Array.isArray(p.success_criteria)) {
    throw new Error("[VALIDATION] success_criteria must be an array");
  }

  // risk_class optional enum
  if (p.risk_class !== undefined && !["A0", "A1", "A2", "A3"].includes(p.risk_class as string)) {
    throw new Error("[VALIDATION] risk_class must be A0|A1|A2|A3");
  }

  // model_route optional enum
  if (
    p.model_route !== undefined &&
    p.model_route !== null &&
    !["R0", "R1", "R2", "R3", "R4", null].includes(p.model_route as string)
  ) {
    throw new Error("[VALIDATION] model_route must be R0|R1|R2|R3|R4|null");
  }

  // timeout_seconds optional number
  if (
    p.timeout_seconds !== undefined &&
    (typeof p.timeout_seconds !== "number" || !Number.isFinite(p.timeout_seconds))
  ) {
    throw new Error("[VALIDATION] timeout_seconds must be a finite number");
  }

  // deadline optional ISO string
  if (p.deadline !== undefined && p.deadline !== null && typeof p.deadline === "string") {
    if (Number.isNaN(Date.parse(p.deadline))) {
      throw new Error("[VALIDATION] deadline must be an ISO-8601 timestamp");
    }
  }

  return {
    idempotency_key: String(p.idempotency_key),
    project_id: p.project_id === undefined || p.project_id === null ? null : String(p.project_id),
    goal_id: p.goal_id === undefined || p.goal_id === null ? null : String(p.goal_id),
    parent_task_id: p.parent_task_id === undefined || p.parent_task_id === null ? null : String(p.parent_task_id),
    title,
    instructions: p.instructions ?? null,
    context_refs: p.context_refs ?? [],
    required_output: p.required_output ?? null,
    success_criteria: p.success_criteria ?? [],
    requested_by: String(p.requested_by),
    assigned_to: String(p.assigned_to),
    risk_class: p.risk_class as CreateTaskInput["risk_class"],
    model_route: (p.model_route ?? null) as CreateTaskInput["model_route"],
    timeout_seconds: p.timeout_seconds as number | undefined,
    deadline: p.deadline === undefined ? undefined : (p.deadline as string),
  };
}

// ---------- TaskPatch ----------
export interface TaskPatch {
  title?: string;
  instructions?: string | null;
  assigned_to?: string | null;
  status?:
    | "pending"
    | "in_progress"
    | "blocked"
    | "needs_approval"
    | "completed"
    | "failed"
    | "cancelled";
  risk_class?: "A0" | "A1" | "A2" | "A3";
  model_route?: "R0" | "R1" | "R2" | "R3" | "R4" | null;
  required_output?: string | null;
}

export function validateTaskPatch(
  raw: unknown
): TaskPatch {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] task_patch: payload must be an object");
  }
  const p = raw as Record<string, unknown>;
  const result: Partial<TaskPatch> = {};

  if (p.title !== undefined) {
    if (typeof p.title !== "string") {
      throw new Error("[VALIDATION] patch title must be a string");
    }
    if (p.title.length < 1 || p.title.length > 300) {
      throw new Error("[VALIDATION] patch title must be 1..300 chars");
    }
    result.title = p.title;
  }
  if (p.instructions !== undefined) {
    if (typeof p.instructions !== "string") {
      throw new Error("[VALIDATION] patch instructions must be a string");
    }
    result.instructions = p.instructions;
  }
  if (p.assigned_to !== undefined) {
    if (typeof p.assigned_to !== "string") {
      throw new Error("[VALIDATION] patch assigned_to must be a string");
    }
    validateAgentName(p.assigned_to, "assigned_to");
    result.assigned_to = p.assigned_to;
  }
  if (p.status !== undefined) {
    if (
      ![
        "pending",
        "in_progress",
        "blocked",
        "needs_approval",
        "completed",
        "failed",
        "cancelled",
      ].includes(p.status as string)
    ) {
      throw new Error("[VALIDATION] status must be a valid task status");
    }
    result.status = p.status as TaskPatch["status"];
  }
  if (p.risk_class !== undefined) {
    if (!["A0", "A1", "A2", "A3"].includes(p.risk_class as string)) {
      throw new Error("[VALIDATION] risk_class must be A0|A1|A2|A3");
    }
    result.risk_class = p.risk_class as TaskPatch["risk_class"];
  }
  if (p.model_route !== undefined) {
    if (p.model_route !== null && !["R0", "R1", "R2", "R3", "R4", null].includes(p.model_route as string)) {
      throw new Error("[VALIDATION] model_route must be R0|R1|R2|R3|R4|null");
    }
    result.model_route = p.model_route as TaskPatch["model_route"];
  }
  if (p.required_output !== undefined) {
    if (typeof p.required_output !== "string") {
      throw new Error("[VALIDATION] patch required_output must be a string");
    }
    result.required_output = p.required_output;
  }
  if (Object.keys(result as object).length === 0) {
    throw new Error("[VALIDATION] empty patch: nothing to update");
  }
  // Omit undefined entries to get a complete Partial<TaskPatch>
  return { ...result } as TaskPatch;
}

// ---------- recordDecision input ----------
export interface RecordDecisionInput {
  task_id?: string | null;
  made_by: string;
  decision_type: string;
  rationale?: string | null;
  payload?: Record<string, unknown>;
}

export function validateRecordDecisionInput(
  raw: unknown
): RecordDecisionInput {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] record_decision: payload must be an object");
  }
  const p = raw as Record<string, unknown>;

  validateAgentName(String(p.made_by), "made_by");

  if (
    typeof p.decision_type !== "string" ||
    p.decision_type.length < 1 ||
    p.decision_type.length > 120
  ) {
    throw new Error("[VALIDATION] decision_type required, 1..120 chars");
  }

  if (p.rationale !== undefined && typeof p.rationale !== "string") {
    throw new Error("[VALIDATION] rationale must be a string");
  }

  if (p.payload !== undefined && typeof p.payload !== "object") {
    throw new Error("[VALIDATION] payload must be an object");
  }

  return {
    task_id: p.task_id === undefined ? null : String(p.task_id),
    made_by: String(p.made_by),
    decision_type: String(p.decision_type),
    rationale: p.rationale ?? null,
    payload: (p.payload ?? {}) as Record<string, unknown>,
  };
}

// ---------- requestApproval input ----------
export interface RequestApprovalInput {
  task_id?: string | null;
  requested_by: string;
  approval_type: string;
  payload?: Record<string, unknown>;
}

export function validateRequestApprovalInput(
  raw: unknown
): RequestApprovalInput {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] request_approval: payload must be an object");
  }
  const p = raw as Record<string, unknown>;

  validateAgentName(String(p.requested_by), "requested_by");

  if (
    typeof p.approval_type !== "string" ||
    p.approval_type.length < 1 ||
    p.approval_type.length > 120
  ) {
    throw new Error("[VALIDATION] approval_type required, 1..120 chars");
  }

  if (p.payload !== undefined && typeof p.payload !== "object") {
    throw new Error("[VALIDATION] payload must be an object");
  }

  return {
    task_id: p.task_id === undefined ? null : String(p.task_id),
    requested_by: String(p.requested_by),
    approval_type: String(p.approval_type),
    payload: (p.payload ?? {}) as Record<string, unknown>,
  };
}

// ---------- recordEvent input ----------
export interface RecordEventInput {
  agent_name: string;
  task_id?: string | null;
  event_type: string;
  payload?: Record<string, unknown>;
}

export function validateRecordEventInput(
  raw: unknown
): RecordEventInput {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] record_event: payload must be an object");
  }
  const p = raw as Record<string, unknown>;

  validateAgentName(String(p.agent_name), "agent_name");

  if (
    typeof p.event_type !== "string" ||
    p.event_type.length < 1 ||
    p.event_type.length > 120
  ) {
    throw new Error("[VALIDATION] event_type required, 1..120 chars");
  }

  if (p.payload !== undefined && typeof p.payload !== "object") {
    throw new Error("[VALIDATION] payload must be an object");
  }

  return {
    agent_name: String(p.agent_name),
    task_id: p.task_id === undefined ? null : String(p.task_id),
    event_type: String(p.event_type),
    payload: (p.payload ?? {}) as Record<string, unknown>,
  };
}

// ---------- listProjects query ----------
export function validateListProjects(): void {}

// ---------- getProject input ----------
export function validateGetProject(projectId: string): projectId is string {
  if (!validateUuid(projectId)) {
    throw new Error("[VALIDATION] project_id must be a UUIDv4");
  }
  return true;
}

// ---------- listGoals projectId? ----------
export function validateListGoals(
  projectId?: string | null
): void {
  if (projectId !== undefined && projectId !== null) {
    if (!validateUuid(projectId)) {
      throw new Error("[VALIDATION] project_id must be a UUIDv4");
    }
  }
}

// ---------- getGoal input ----------
export function validateGetGoal(goalId: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(goalId)) {
    throw new Error("[VALIDATION] goal_id must be a UUIDv4");
  }
  return goalId;
}

// ---------- getTask / getTaskRun input ----------
export function validateGetTask(taskId: string): string {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(taskId)) {
    throw new Error("[VALIDATION] task_id must be a UUIDv4");
  }
  return taskId;
}

// ---------- assignTask input ----------
export interface AssignTaskInput {
  task_id: string;
  agent_name: "tola" | "rhythm" | "growth" | "scholar";
}

export function validateAssignTask(
  raw: unknown
): AssignTaskInput {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] assign_task: payload must be an object");
  }
  const p = raw as Record<string, unknown>;

  if (typeof p.task_id !== "string") {
    throw new Error("[VALIDATION] assign_task: task_id required");
  }
  if (!validateUuid(p.task_id)) {
    throw new Error("[VALIDATION] assign_task: task_id must be a UUIDv4");
  }

  if (typeof p.agent_name !== "string") {
    throw new Error("[VALIDATION] assign_task: agent_name required");
  }
  validateAgentName(p.agent_name, "agent_name");

  return {
    task_id: p.task_id,
    agent_name: p.agent_name as AssignTaskInput["agent_name"],
  };
}

// ---------- updateTaskStatus input ----------
export interface UpdateTaskStatusInput {
  task_id: string;
  new_status:
    | "pending"
    | "in_progress"
    | "blocked"
    | "needs_approval"
    | "completed"
    | "failed"
    | "cancelled";
  acting_agent: "tola" | "rhythm" | "growth" | "scholar";
}

export function validateUpdateTaskStatus(
  raw: unknown
): UpdateTaskStatusInput {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("[VALIDATION] update_task_status: payload must be an object");
  }
  const p = raw as Record<string, unknown>;

  if (typeof p.task_id !== "string") {
    throw new Error("[VALIDATION] update_task_status: task_id required");
  }
  if (!validateUuid(p.task_id)) {
    throw new Error("[VALIDATION] update_task_status: task_id must be a UUIDv4");
  }

  if (
    ![
      "pending",
      "in_progress",
      "blocked",
      "needs_approval",
      "completed",
      "failed",
      "cancelled",
    ].includes(p.new_status as string)
  ) {
    throw new Error(
      "[VALIDATION] new_status must be one of pending|in_progress|blocked|needs_approval|completed|failed|cancelled"
    );
  }

  if (typeof p.acting_agent !== "string") {
    throw new Error("[VALIDATION] update_task_status: acting_agent required");
  }
  validateAgentName(p.acting_agent, "acting_agent");

  return {
    task_id: p.task_id,
    new_status: p.new_status as UpdateTaskStatusInput["new_status"],
    acting_agent: p.acting_agent as UpdateTaskStatusInput["acting_agent"],
  };
}
