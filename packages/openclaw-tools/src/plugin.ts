/**
 * OpenClaw Tool Plugin — Batch 04.
 *
 * Uses defineToolPlugin from openclaw/plugin-sdk/tool-plugin to register
 * Tola-approved Blackboard tools as a native OpenClaw plugin.
 *
 * All mutations are audited via the repository's internal audit path.
 * Errors are redacted before reaching the model (T5.5 error redaction).
 * No credentials, secrets, or raw provider errors surface to the model.
 */
import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";
import { BlackboardRepository } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { redactError } from "./redact.ts";
import {
  validateCreateTaskInput,
  validateTaskPatch,
  validateAssignTask,
  validateUpdateTaskStatus,
  validateRecordDecisionInput,
  validateRequestApprovalInput,
  validateRecordEventInput,
  validateGetProject,
  validateListGoals,
  validateGetGoal,
  validateGetTask,
  validateListProjects,
} from "./validate.ts";
import { BlackboardError, SupabaseAdapter } from "@tola/blackboard-tools/src/adapters/supabase.ts";

// Strict object schema: rejects unexpected fields at the runtime boundary.
const SO = <T extends Parameters<typeof Type.Object>[0]>(props: T) =>
  Type.Object(props, { additionalProperties: false } as never);

// ---------- repository binding ----------

interface PluginConfig {
  supabaseUrl: string;
  supabaseKey: string;
  timeoutMs?: number;
}

const emptyConfig: Record<string, never> = {} as Record<string, never>;
void emptyConfig;

/**
 * Build the repository from plugin config (never hard-coded, never logged).
 * Supplied via the plugin's Gateway config entry; SecretRefs are resolved by
 * the host before config reaches the plugin.
 */
function getRepo(config: PluginConfig): BlackboardRepository {
  if (!config || typeof config.supabaseUrl !== "string" || typeof config.supabaseKey !== "string") {
    throw new BlackboardError(
      "UNAVAILABLE",
      "plugin config missing supabaseUrl/supabaseKey (configure via SecretRef in the Gateway config entry)",
    );
  }
  return new BlackboardRepository(
    new SupabaseAdapter({
      url: config.supabaseUrl,
      serviceKey: config.supabaseKey,
      timeoutMs: config.timeoutMs,
    }),
  );
}

// ---------- tool implementations ----------

async function listProjectsTool(db: BlackboardRepository) {
  validateListProjects();
  try {
    return await db.listProjects();
  } catch (err) {
    throw new BlackboardError(
      "UNAVAILABLE",
      `failed to list projects: ${redactError(err).message}`,
      redactError(err).detail
    );
  }
}

async function getProjectTool(db: BlackboardRepository, params: { project_id: string }) {
  validateGetProject(params.project_id);
  try {
    return await db.getProject(params.project_id);
  } catch (err) {
    throw new BlackboardError(
      "NOT_FOUND",
      `project ${params.project_id} not found`,
      redactError(err).detail
    );
  }
}

async function listGoalsTool(db: BlackboardRepository, params: { project_id?: string | null }) {
  validateListGoals(params.project_id);
  try {
    return await db.listGoals(params.project_id ?? undefined);
  } catch (err) {
    throw new BlackboardError(
      "UNAVAILABLE",
      `failed to list goals: ${redactError(err).message}`,
      redactError(err).detail
    );
  }
}

async function getGoalTool(db: BlackboardRepository, params: { goal_id: string }) {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(params.goal_id)) {
    throw new BlackboardError("VALIDATION", "goal_id must be a UUIDv4");
  }
  try {
    return await db.getGoal(params.goal_id);
  } catch (err) {
    throw new BlackboardError(
      "NOT_FOUND",
      `goal ${params.goal_id} not found`,
      redactError(err).detail
    );
  }
}

async function createTaskTool(db: BlackboardRepository, params: unknown) {
  let input: ReturnType<typeof validateCreateTaskInput>;
  try {
    input = validateCreateTaskInput(params);
    const repoInput: Parameters<BlackboardRepository["createTask"]>[0] = {
      ...input,
      instructions: input.instructions ?? undefined,
      required_output: input.required_output ?? undefined,
    };
    const task = await db.createTask(repoInput);
    return { task, input };
  } catch (err) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `create_task failed: ${redacted.message}`,
      redacted.detail
    );
  }
}

async function listTasksTool(db: BlackboardRepository) {
  try {
    return await db.listActiveTasks();
  } catch (err) {
    throw new BlackboardError(
      "UNAVAILABLE",
      `failed to list tasks: ${redactError(err).message}`,
      redactError(err).detail
    );
  }
}

async function getTaskTool(db: BlackboardRepository, params: { task_id: string }) {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(params.task_id)) {
    throw new BlackboardError("VALIDATION", "task_id must be a UUIDv4");
  }
  try {
    return await db.getTask(params.task_id);
  } catch (err) {
    throw new BlackboardError(
      "NOT_FOUND",
      `task ${params.task_id} not found`,
      redactError(err).detail
    );
  }
}

async function assignTaskTool(db: BlackboardRepository, params: unknown) {
  let input: ReturnType<typeof validateAssignTask>;
  try {
    input = validateAssignTask(params);
    if (typeof input.expected_version !== "number" || !Number.isInteger(input.expected_version) || input.expected_version < 1) {
      throw new BlackboardError("VALIDATION", "assign_task: expected_version must be a positive integer");
    }
    const task = await db.updateTask(input.task_id, input.expected_version, { assigned_to: input.agent_name }, input.agent_name);
    return { task };
  } catch (err) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `assign_task failed: ${redacted.message}`,
      redacted.detail
    );
  }
}

async function updateTaskStatusTool(db: BlackboardRepository, params: unknown) {
  let input: ReturnType<typeof validateUpdateTaskStatus>;
  try {
    input = validateUpdateTaskStatus(params);
    if (typeof input.expected_version !== "number" || !Number.isInteger(input.expected_version) || input.expected_version < 1) {
      throw new BlackboardError("VALIDATION", "update_task_status: expected_version must be a positive integer");
    }
    const task = await db.updateTask(input.task_id, input.expected_version, { status: input.new_status }, input.acting_agent);
    return { task };
  } catch (err) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `update_task_status failed: ${redacted.message}`,
      redacted.detail
    );
  }
}

async function recordDecisionTool(db: BlackboardRepository, params: unknown) {
  let input: ReturnType<typeof validateRecordDecisionInput>;
  try {
    input = validateRecordDecisionInput(params);
    const decision = await db.recordDecision({
      ...input,
      rationale: input.rationale ?? undefined,
    });
    return { decision };
  } catch (err) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `record_decision failed: ${redacted.message}`,
      redacted.detail
    );
  }
}

async function recordEventTool(db: BlackboardRepository, params: unknown) {
  let input: ReturnType<typeof validateRecordEventInput>;
  try {
    input = validateRecordEventInput(params);
    return { event: await db.recordAgentEvent(input) };
  } catch (err) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `record_event failed: ${redacted.message}`,
      redacted.detail
    );
  }
}

async function requestApprovalTool(db: BlackboardRepository, params: unknown) {
  let input: ReturnType<typeof validateRequestApprovalInput>;
  try {
    input = validateRequestApprovalInput(params);
    return { approval: await db.requestApproval(input) };
  } catch (err) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `request_approval failed: ${redacted.message}`,
      redacted.detail
    );
  }
}

async function getApprovalTool(db: BlackboardRepository, params: { approval_id: string }) {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(params.approval_id)) {
    throw new BlackboardError("VALIDATION", "approval_id must be a UUIDv4");
  }
  try {
    return await db.getApproval(params.approval_id);
  } catch (err) {
    throw new BlackboardError(
      "NOT_FOUND",
      `approval ${params.approval_id} not found`,
      redactError(err).detail
    );
  }
}

async function getTaskRunTool(db: BlackboardRepository, params: { task_id: string }) {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(params.task_id)) {
    throw new BlackboardError("VALIDATION", "task_id must be a UUIDv4");
  }
  try {
    return { task: await db.getTask(params.task_id) };
  } catch (err) {
    throw new BlackboardError(
      "NOT_FOUND",
      `task ${params.task_id} not found`,
      redactError(err).detail
    );
  }
}

// ---------- test internals (not part of the agent surface) ----------

/** Test-only access to the tool implementations; not exposed via the plugin contract. */
export const __testInternals = {
  listProjectsTool,
  getProjectTool,
  listGoalsTool,
  getGoalTool,
  createTaskTool,
  listTasksTool,
  getTaskTool,
  assignTaskTool,
  updateTaskStatusTool,
  recordDecisionTool,
  recordEventTool,
  requestApprovalTool,
  getApprovalTool,
  getTaskRunTool,
};

// ---------- plugin definition ----------

export default defineToolPlugin({
  id: "openclaw-tools",
  name: "OpenClaw Tools",
  description:
    "Tola-approved Blackboard tools bound to a Supabase repository with validation, audit, and error redaction.",
  configSchema: Type.Object(
    {
      supabaseUrl: Type.String({ description: "Supabase REST base URL." }),
      supabaseKey: Type.String({ description: "Service key. Supply via SecretRef." }),
      timeoutMs: Type.Optional(Type.Number({ description: "Request timeout in ms." })),
    },
    { additionalProperties: false } as never,
  ),
  tools: (tool) => [
    tool({
      name: "listProjects",
      description: "List all projects.",
      parameters: SO({}),
      async execute(_params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return listProjectsTool(getRepo(config));
      },
    }),
    tool({
      name: "getProject",
      description: "Get a project by ID.",
      parameters: SO({ project_id: Type.String() }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return getProjectTool(getRepo(config), params as { project_id: string });
      },
    }),
    tool({
      name: "listGoals",
      description: "List goals, optionally filtered by project.",
      parameters: SO({ project_id: Type.Optional(Type.String()) }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return listGoalsTool(getRepo(config), params as { project_id?: string | null });
      },
    }),
    tool({
      name: "getGoal",
      description: "Get a goal by ID.",
      parameters: SO({ goal_id: Type.String() }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return getGoalTool(getRepo(config), params as { goal_id: string });
      },
    }),
    tool({
      name: "createTask",
      description: "Create a new task with validated input.",
      parameters: SO({
        idempotency_key: Type.String(),
        project_id: Type.Optional(Type.String()),
        goal_id: Type.Optional(Type.String()),
        parent_task_id: Type.Optional(Type.String()),
        title: Type.String(),
        instructions: Type.Optional(Type.String()),
        context_refs: Type.Optional(Type.Array(Type.Unknown())),
        required_output: Type.Optional(Type.String()),
        success_criteria: Type.Optional(Type.Array(Type.Unknown())),
        requested_by: Type.String(),
        assigned_to: Type.String(),
        risk_class: Type.Optional(Type.String()),
        model_route: Type.Optional(Type.String()),
        timeout_seconds: Type.Optional(Type.Number()),
        deadline: Type.Optional(Type.String()),
      }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return createTaskTool(getRepo(config), params);
      },
    }),
    tool({
      name: "listTasks",
      description: "List all tasks.",
      parameters: SO({}),
      async execute(_params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return listTasksTool(getRepo(config));
      },
    }),
    tool({
      name: "getTask",
      description: "Get a task by ID.",
      parameters: SO({ task_id: Type.String() }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return getTaskTool(getRepo(config), params as { task_id: string });
      },
    }),
    tool({
      name: "assignTask",
      description: "Assign a task to an agent.",
      parameters: SO({
        task_id: Type.String(),
        agent_name: Type.String(),
        expected_version: Type.Number({ description: "Current task version for optimistic concurrency." }),
      }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return assignTaskTool(getRepo(config), params);
      },
    }),
    tool({
      name: "updateTaskStatus",
      description: "Update the status of a task.",
      parameters: SO({
        task_id: Type.String(),
        new_status: Type.String(),
        acting_agent: Type.String(),
        expected_version: Type.Number({ description: "Current task version for optimistic concurrency." }),
      }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return updateTaskStatusTool(getRepo(config), params);
      },
    }),
    tool({
      name: "recordDecision",
      description: "Record a decision for a task.",
      parameters: SO({
        task_id: Type.Optional(Type.String()),
        made_by: Type.String(),
        decision_type: Type.String(),
        rationale: Type.Optional(Type.String()),
        payload: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return recordDecisionTool(getRepo(config), params);
      },
    }),
    tool({
      name: "recordEvent",
      description: "Record an agent event for a task.",
      parameters: SO({
        agent_name: Type.String(),
        task_id: Type.Optional(Type.String()),
        event_type: Type.String(),
        payload: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return recordEventTool(getRepo(config), params);
      },
    }),
    tool({
      name: "requestApproval",
      description: "Request an approval for a task.",
      parameters: SO({
        task_id: Type.Optional(Type.String()),
        requested_by: Type.String(),
        approval_type: Type.String(),
        payload: Type.Optional(Type.Record(Type.String(), Type.Unknown())),
      }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return requestApprovalTool(getRepo(config), params);
      },
    }),
    tool({
      name: "getApproval",
      description: "Get an approval by ID.",
      parameters: SO({ approval_id: Type.String() }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return getApprovalTool(getRepo(config), params as { approval_id: string });
      },
    }),
    tool({
      name: "getTaskRun",
      description: "Get a task run by task ID.",
      parameters: SO({ task_id: Type.String() }),
      async execute(params, config, ctx) {
        ctx.signal?.throwIfAborted();
        return getTaskRunTool(getRepo(config), params as { task_id: string });
      },
    }),
  ],
});
