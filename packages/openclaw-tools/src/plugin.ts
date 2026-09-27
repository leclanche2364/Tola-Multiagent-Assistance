/**
 * OpenClaw Tool Plugin — Batch 5.
 *
 * This module wires the typed, schema-validated tools onto a
 * BlackboardRepository instance.  Only Tola-approved tools are
 * exposed; specialist profiles cannot discover or invoke Tola-only
 * capabilities (T5.6 specialist visibility scoping).
 *
 * All mutations are audited via the repository's internal audit path.
 * Errors are redacted before reaching the model (T5.5 error redaction).
 *
 * Entry point for the OpenClaw plugin system.
 */
import {
  listProjects,
  getProject,
  listGoals,
  getGoal,
  createTask,
  listTasks,
  getTask,
  assignTask,
  updateTaskStatus,
  recordDecision,
  recordEvent,
  requestApproval,
  getApproval,
  getTaskRun,
} from "./tools/index.ts";
import type {
  BlackboardRepository,
  ProjectRow,
  GoalRow,
  TaskRow,
  ApprovalRow,
} from "@tola/blackboard-tools/src/repository/blackboard.ts";

/**
 * Plugin namespace — the OpenClaw system discovers tools by probing
 * this object's keys.  Only the entries below are visible; any
 * specialist-only tools must not appear here.
 */
export type PluginApi = {
  listProjects: () => Promise<ProjectRow[]>;
  getProject: (projectId: string) => Promise<ProjectRow>;
  listGoals: (projectId?: string | null) => Promise<GoalRow[]>;
  getGoal: (goalId: string) => Promise<GoalRow>;
  createTask: (
    input: Parameters<BlackboardRepository["createTask"]>[0]
  ) => Promise<{
    task: Awaited<ReturnType<BlackboardRepository["createTask"]>>;
    input: Parameters<BlackboardRepository["createTask"]>[0];
  }>;
  listTasks: () => Promise<TaskRow[]>;
  getTask: (taskId: string) => Promise<TaskRow>;
  assignTask: (input: {
    task_id: string;
    agent_name: "tola" | "rhythm" | "growth" | "scholar";
  }) => Promise<{ task: TaskRow }>;
  updateTaskStatus: (input: {
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
  }) => Promise<{ task: TaskRow }>;
  recordDecision: (input: {
    task_id?: string | null;
    made_by: "tola" | "rhythm" | "growth" | "scholar";
    decision_type: string;
    rationale?: string | null;
    payload?: Record<string, unknown>;
  }) => Promise<{ decision: Awaited<ReturnType<BlackboardRepository["recordDecision"]>> }>;
  recordEvent: (input: {
    agent_name: "tola" | "rhythm" | "growth" | "scholar";
    task_id?: string | null;
    event_type: string;
    payload?: Record<string, unknown>;
  }) => Promise<{ event: Awaited<ReturnType<BlackboardRepository["recordAgentEvent"]>> }>;
  requestApproval: (input: {
    task_id?: string | null;
    requested_by: "tola" | "rhythm" | "growth" | "scholar";
    approval_type: string;
    payload?: Record<string, unknown>;
  }) => Promise<{ approval: Awaited<ReturnType<BlackboardRepository["requestApproval"]>> }>;
  getApproval: (approvalId: string) => Promise<ApprovalRow>;
  getTaskRun: (taskId: string) => Promise<{ task: TaskRow }>;
};

/**
 * Create a plugin-instantiated API bound to a specific BlackboardRepository.
 * The returned object has the shape of PluginApi and delegates every
 * call to the matching typed tool function.
 */
export function createPlugin(db: BlackboardRepository): PluginApi {
  return {
    listProjects: () => listProjects(db),
    getProject: (projectId) => getProject(db, projectId),
    listGoals: (projectId) => listGoals(db, projectId),
    getGoal: (goalId) => getGoal(db, goalId),
    createTask: (input) => createTask(db, input),
    listTasks: () => listTasks(db),
    getTask: (taskId) => getTask(db, taskId),
    assignTask: (input) => assignTask(db, input),
    updateTaskStatus: (input) => updateTaskStatus(db, input),
    recordDecision: (input) => recordDecision(db, input),
    recordEvent: (input) => recordEvent(db, input),
    requestApproval: (input) => requestApproval(db, input),
    getApproval: (approvalId) => getApproval(db, approvalId),
    getTaskRun: (taskId) => getTaskRun(db, taskId),
  };
}
