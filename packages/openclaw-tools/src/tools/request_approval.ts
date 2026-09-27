import { BlackboardRepository, type ApprovalRow } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
import { validateRequestApprovalInput } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function requestApproval(
  db: BlackboardRepository,
  input: {
    task_id?: string | null;
    requested_by: "tola" | "rhythm" | "growth" | "scholar";
    approval_type: string;
    payload?: Record<string, unknown>;
  }
): Promise<{ approval: ApprovalRow }> {
  try {
    const validated = validateRequestApprovalInput(input);
    const approval: ApprovalRow = await db.requestApproval(validated);
    return { approval };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `request_approval validation or write failed: ${redacted.message}`,
      redacted.detail
    );
  }
}