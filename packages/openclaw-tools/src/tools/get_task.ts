import { BlackboardRepository, type TaskRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { validateGetTask } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function getTask(
  db: BlackboardRepository,
  taskId: string
): Promise<TaskRow> {
  validateGetTask(taskId);
  try {
    return await db.getTask(taskId);
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "NOT_FOUND",
      `task ${taskId} not found`,
      redacted.detail
    );
  }
}