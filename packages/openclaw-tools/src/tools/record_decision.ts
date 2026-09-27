import { BlackboardRepository, type DecisionRow } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
import { validateRecordDecisionInput } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function recordDecision(
  db: BlackboardRepository,
  input: {
    task_id?: string | null;
    made_by: "tola" | "rhythm" | "growth" | "scholar";
    decision_type: string;
    rationale?: string | null;
    payload?: Record<string, unknown>;
  }
): Promise<{ decision: DecisionRow }> {
  try {
    const validated = validateRecordDecisionInput({
      task_id: input.task_id,
      made_by: input.made_by,
      decision_type: input.decision_type,
      rationale: input.rationale,
      payload: input.payload,
    });
    // Remove explicit null from rationale to match repository expectation
    const clean = {
      task_id: validated.task_id,
      made_by: validated.made_by,
      decision_type: validated.decision_type,
      rationale: validated.rationale === null ? undefined : validated.rationale,
      payload: validated.payload,
    } as const;
    const decision: DecisionRow = await db.recordDecision(clean);
    return { decision };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `record_decision validation or write failed: ${redacted.message}`,
      redacted.detail
    );
  }
}