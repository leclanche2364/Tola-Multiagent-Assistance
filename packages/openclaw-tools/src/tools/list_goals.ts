import { BlackboardRepository, type GoalRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { validateListGoals } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function listGoals(
  db: BlackboardRepository,
  projectId?: string | null
): Promise<GoalRow[]> {
  validateListGoals(projectId);
  try {
    return await db.listGoals(projectId ?? undefined);
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "UNAVAILABLE",
      `failed to list goals${projectId ? ` for project ${projectId}` : ""}: ${redacted.message}`,
      redacted.detail
    );
  }
}
