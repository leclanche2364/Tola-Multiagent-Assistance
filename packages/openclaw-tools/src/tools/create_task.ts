import { BlackboardRepository } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
import { validateCreateTaskInput } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function createTask(
  db: BlackboardRepository,
  input: Parameters<BlackboardRepository["createTask"]>[0]
): Promise<{
  task: Awaited<ReturnType<BlackboardRepository["createTask"]>>;
  input: Parameters<BlackboardRepository["createTask"]>[0];
}> {
  try {
    const validated = validateCreateTaskInput(input);
    const task = await db.createTask(
      validated as Parameters<BlackboardRepository["createTask"]>[0]
    );
    return {
      task,
      input: validated as Parameters<BlackboardRepository["createTask"]>[0],
    };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `create_task validation or write failed: ${redacted.message}`,
      redacted.detail
    );
  }
}