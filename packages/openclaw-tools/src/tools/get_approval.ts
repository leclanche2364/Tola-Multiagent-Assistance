import { BlackboardRepository, type ApprovalRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { redactError } from "../redact.ts";

export async function getApproval(
  db: BlackboardRepository,
  approvalId: string
): Promise<ApprovalRow> {
  try {
    return await db.getApproval(approvalId);
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "NOT_FOUND",
      `approval ${approvalId} not found`,
      redacted.detail
    );
  }
}