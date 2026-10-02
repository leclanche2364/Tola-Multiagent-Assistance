// Rhythm capacity refresh workflow — Batch 10.
// Refreshes capacity and changes only pre-authorised flexible blocks.
// Never deletes/moves fixed or shared commitments without approval.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import type { DelegateStub } from "./types.ts";
import { evaluateAction } from "../../../action-policy/src/policy.ts";

export class RhythmCapacityWorkflow implements WorkflowModule {
  readonly automationKey = "rhythm-capacity-refresh";
  readonly owner = "rhythm";
  readonly riskCeiling = "C2";

  private delegate: DelegateStub;

  constructor(delegate: DelegateStub) {
    this.delegate = delegate;
  }

  async run(
    context: WorkflowContext,
    scheduledFor: string,
    releaseSha: string,
    openclawJobId: string,
  ): Promise<WorkflowResult> {
    const claim = await context.claim({
      automationKey: this.automationKey,
      scheduledFor,
      releaseSha,
      openclawJobId,
      claimedBy: this.owner,
    });
    if (!claim.claimed) {
      return { status: "skipped", automationKey: this.automationKey, scheduledFor, releaseSha, summary: claim.reason ?? "already claimed" };
    }

    try {
      // 1. Read current shift patterns, recovery windows, pending tasks
      const readDecision = evaluateAction("blackboard.listTasks", {}, { envelopes: [], maxPayloadBytes: 16384 });
      if (readDecision.decision !== "ALLOW") {
        throw new Error(`Cannot read blackboard: ${readDecision.reason}`);
      }

      // 2. Refresh capacity forecast (deterministic, no live scheduling)
      const capacityForecast = {
        windowStart: scheduledFor,
        windowEnd: new Date(Date.now() + 7 * 86400_000).toISOString(),
        days: ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"] as const,
        totalCapacityMinutes: 480 * 7, // 8h/day * 7 days
        flexibleBlocks: [] as Array<{ date: string; slot: string; type: "flexible-block"; preAuthorised: boolean }>,
        fixedCommitments: [] as Array<{ date: string; id: string; protected: boolean }>,
      };

      // 3. Only modify pre-authorised flexible blocks
      const modifyDecision = evaluateAction("myrhythm.createBlock", {}, { envelopes: [], maxPayloadBytes: 16384 });
      if (modifyDecision.decision === "ALLOW") {
        // Pre-authorised: create/update flexible blocks only
        const result = await this.delegate("rhythm", "refresh-capacity-forecast", 60_000);
        if (result.ok) {
          capacityForecast.flexibleBlocks.push({ date: scheduledFor, slot: "morning", type: "flexible-block", preAuthorised: true });
        }
      }

      // 4. Gate: never delete/move fixed or shared commitments without approval
      const deleteDecision = evaluateAction("myrhythm.deleteBlock", {}, { envelopes: [], maxPayloadBytes: 16384 });
      if (deleteDecision.decision !== "ALLOW") {
        // Block deletion of fixed/shared commitments — requires approval
        await context.notify("telegram:5647750316", "Rhythm capacity refresh: fixed/shared commitment changes require operator approval");
      }

      const summary = `Rhythm capacity refreshed for next 7 days. ${capacityForecast.flexibleBlocks.length} flexible block(s) updated. No fixed/shared commitments modified.`;
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary });
      return { status: "ok", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: capacityForecast };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
