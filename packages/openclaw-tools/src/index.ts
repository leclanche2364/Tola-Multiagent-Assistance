/**
 * OpenClaw Tools — Batch 5 public surface.
 *
 * Exported names are the narrow, typed tools that agents may call.
 * No raw SQL, no generic HTTP, no arbitrary table/query surface.
 * Every mutation goes through schema validation and audits.
 *
 * Specialist visibility (T5.6): only the names below are visible to
 * non-Tola profiles.  The plugin gateway filters any additional keys.
 */
export {
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

export type {
  CreateTaskInput,
  TaskPatch,
  SkillPromotionInput,
} from "@tola/blackboard-tools/src/repository/blackboard.ts";
export type {
  ProjectRow,
  GoalRow,
  TaskRow,
  ApprovalRow,
} from "@tola/blackboard-tools/src/repository/blackboard.ts";
export type { ErrorCode } from "@tola/blackboard-tools/src/adapters/supabase.ts";

export { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
export { redactError } from "./redact.ts";