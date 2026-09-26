// BlackboardRepository — public surface.
export { BlackboardRepository } from "./repository/blackboard.ts";
export type {
  AgentRow,
  ProjectRow,
  GoalRow,
  TaskRow,
  DecisionRow,
  MetricRow,
  ScheduleConstraintRow,
  ApprovalRow,
  AgentEventRow,
  SkillRow,
  CreateTaskInput,
  TaskPatch,
  SkillPromotionInput,
} from "./repository/blackboard.ts";
export { SupabaseAdapter, BlackboardError } from "./adapters/supabase.ts";
export type { ErrorCode } from "./adapters/supabase.ts";
export { loadEnv, env, envOptional } from "./env.ts";
