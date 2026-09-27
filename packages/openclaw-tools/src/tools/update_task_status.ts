import { BlackboardRepository, type TaskRow } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
import { validateUpdateTaskStatus } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function updateTaskStatus(
  db: BlackboardRepository,
  input: {
    task_id: string;
    new_status: "pending" | "in_progress" | "blocked" | "needs_approval" | "completed" | "failed" | "cancelled";
    acting_agent: "tola" | "rhythm" | "growth" | "scholar";
  }
): Promise<{ task: TaskRow }> {
  try {
    const validated = validateUpdateTaskStatus({
      task_id: input.task_id,
      new_status: input.new_status,
      acting_agent: input.acting_agent,
    });
    const task = await db.updateTask(
      validated.task_id,
      1, // expectedVersion — first write assumes version 1
      {
        title: undefined,
        instructions: undefined,
        assigned_to: undefined,
        status: validated.new_status,
        risk_class: undefined,
        model_route: undefined,
        required_output: undefined,
      },
      validated.acting_agent
    );
    return { task };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `failed to update task status: ${redacted.message}`,
      redacted.detail
    );
  }
}