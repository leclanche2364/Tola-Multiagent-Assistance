import { BlackboardRepository, type GoalRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { validateGetGoal } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function getGoal(
  db: BlackboardRepository,
  goalId: string
): Promise<GoalRow> {
  validateGetGoal(goalId);
  try {
    return await db.getGoal(goalId);
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "NOT_FOUND",
      `goal ${goalId} not found`,
      redacted.detail
    );
  }
}