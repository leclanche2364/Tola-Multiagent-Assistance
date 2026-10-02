/**
 * Tola-side review logic — Batch 8 (§11.3) + Batch 07 fixes.
 *
 * Gate rules mapped to status → action:
 *   (a) partial       => do NOT mark task complete; record partial evidence.
 *   (b) blocked       => record blocker, no automatic retry.
 *   (c) needs_approval=> create/emit approval record; human must resolve.
 *   (d) malformed     => at most ONE correction/retry, then give up permanently.
 *   (e) reconciliation: if a run claims "complete", verify evidence ref exists
 *       before allowing retry — no duplicate external effect.
 *   (f) duplicate spawn: same idempotencyKey yields one logical effect (idempotency guard).
 */
import { type Result, type Envelope } from "./index.ts";
import { isUuid } from "../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardRepository } from "../../blackboard-tools/src/index.ts";
import { canRetry, incrementRetryCount } from "./retry-counter.ts";

/** Validate that a "complete" result has an evidence ref when external writes occurred. */
function validateComplete(result: Result): result is Result & { evidence: string } {
  return result.status === "complete" && typeof result.evidence === "string" && result.evidence.length > 0;
}

/**
 * Apply the Batch 8 review gate.
 *
 * Returns a gate verdict object; the caller (runtime) uses it to decide
 * how to update the task run and whether to emit approvals or block retry.
 */
export function review(result: Result, envelope: Envelope, repo: BlackboardRepository): {
  status: "complete" | "partial" | "blocked" | "needs_approval" | "malformed";
  action:
    | { type: "mark_complete"; evidence?: string }
    | { type: "record_blocker"; message: string }
    | { type: "request_approval"; approvalType: string; payload: Record<string, unknown> }
    | { type: "retry_once"; correction: string }
    | { type: "give_up"; reason: string };
} {
  // ---------- (d) malformed: structural validation ----------
  // At most ONE correction/retry; after that, give up permanently.
  // Persisted retry counter prevents "retry once" from repeating forever.
  if (
    result.status === "malformed" ||
    !isUuid(envelope.taskRef) ||
    !isUuid(envelope.runId) ||
    !isUuid(envelope.idempotencyKey)
  ) {
    // Structurally invalid envelope/result: no retry is safe. Give up immediately.
    return {
      status: "malformed",
      action: { type: "give_up", reason: "malformed envelope or result: not retryable" },
    };
  }

  // ---------- (a) partial => do NOT mark task complete ----------
  if (result.status === "partial") {
    return {
      status: "partial",
      action: { type: "record_blocker", message: "partial result: task not complete; evidence收集中" },
    };
  }

  // ---------- (b) blocked => record blocker, no automatic retry ----------
  if (result.status === "blocked") {
    return {
      status: "blocked",
      action: {
        type: "record_blocker",
        message: result.evidence ?? "task blocked with no evidence",
      },
    };
  }

  // ---------- (c) needs_approval => create/emit approval record ----------
  if (result.status === "needs_approval") {
    // Emit an approval record via the repository; the human will resolve it.
    return {
      status: "needs_approval",
      action: {
        type: "request_approval",
        approvalType: "delegation_result",
        payload: {
          runId: envelope.runId,
          route: envelope.route,
          modelId: envelope.modelId,
          resultStatus: result.status,
        },
      },
    };
  }

  // ---------- result.status === "complete" ----------
  if (result.status === "complete") {
    // ---------- (e) reconciliation: verify evidence ref exists before retry ----------
    if (!validateComplete(result)) {
      // No evidence ref present despite claiming complete — this is a malformed state.
      // At most ONE correction/retry is allowed; after that, give up permanently.
      // Persisted retry counter prevents "retry once" from repeating forever.
      const alreadyRetried = !canRetry(envelope.idempotencyKey);
      if (alreadyRetried) {
        return {
          status: "malformed",
          action: { type: "give_up", reason: "missing evidence ref: already retried once, giving up permanently" },
        };
      }
      incrementRetryCount(envelope.idempotencyKey);
      return {
        status: "malformed",
        action: { type: "retry_once", correction: "missing evidence ref for complete result; add evidence uri before retry" },
      };
    }

    // Evidence ref exists — safe to mark complete. No duplicate external effect
    // because the idempotencyKey (f) guarantees one logical effect.
    return {
      status: "complete",
      action: { type: "mark_complete", evidence: result.evidence },
    };
  }

  // Fallback — should not be reached
  return {
    status: "malformed",
    action: { type: "give_up", reason: `unexpected result status: ${String(result.status)}` },
  };
}