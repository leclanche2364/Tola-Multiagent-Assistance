import { BlackboardRepository, type TaskRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { redactError } from "../redact.ts";

export async function listTasks(
  db: BlackboardRepository
): Promise<TaskRow[]> {
  try {
    return await db.listActiveTasks();
  } catch (err: unknown) {
    throw new BlackboardError(
      "UNAVAILABLE",
      `failed to list tasks: ${(err as Error).message}`,
      redactError(err).detail
    );
  }
}