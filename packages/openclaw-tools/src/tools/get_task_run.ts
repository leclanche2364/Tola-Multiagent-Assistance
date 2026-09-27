import { BlackboardRepository, type TaskRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { validateGetTask } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function getTaskRun(
  db: BlackboardRepository,
  taskId: string
): Promise<{ task: TaskRow }> {
  validateGetTask(taskId);
  try {
    const task = await db.getTask(taskId);
    return { task };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "NOT_FOUND",
      `task run ${taskId} not found`,
      redacted.detail
    );
  }
}