import { BlackboardRepository, type TaskRow } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
import { validateAssignTask } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function assignTask(
  db: BlackboardRepository,
  input: {
    task_id: string;
    agent_name: "tola" | "rhythm" | "growth" | "scholar";
  }
): Promise<{ task: TaskRow }> {
  try {
    const validated = validateAssignTask(input);
    // We delegate to the repository's createTask-like flow or use a
    // direct update.  For assign_task we simply set the status to
    // in_progress and assign the agent.  We reuse the repository's
    // updateTask with a minimal patch.
    const task = await db.updateTask(
      validated.task_id,
      1, // expectedVersion — first write, start at version 1
      {
        title: undefined,
        instructions: undefined,
        assigned_to: validated.agent_name,
        status: "in_progress",
        risk_class: undefined,
        model_route: undefined,
        required_output: undefined,
      },
      validated.agent_name
    );
    return { task };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `failed to assign task: ${redacted.message}`,
      redacted.detail
    );
  }
}