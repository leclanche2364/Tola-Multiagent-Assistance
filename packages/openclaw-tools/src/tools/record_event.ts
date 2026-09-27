import { BlackboardRepository, type AgentEventRow } from "@tola/blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "@tola/blackboard-tools/src/adapters/supabase.ts";
import { validateRecordEventInput } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function recordEvent(
  db: BlackboardRepository,
  input: {
    agent_name: "tola" | "rhythm" | "growth" | "scholar";
    task_id?: string | null;
    event_type: string;
    payload?: Record<string, unknown>;
  }
): Promise<{ event: AgentEventRow }> {
  try {
    const validated = validateRecordEventInput(input);
    const event: AgentEventRow = await db.recordAgentEvent(validated);
    return { event };
  } catch (err: unknown) {
    const redacted = redactError(err);
    throw new BlackboardError(
      "VALIDATION",
      `record_event validation or write failed: ${redacted.message}`,
      redacted.detail
    );
  }
}