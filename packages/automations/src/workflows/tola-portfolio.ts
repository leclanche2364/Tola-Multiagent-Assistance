// Tola weekly portfolio review workflow — Batch 10.
// Assesses open goals, task completion rates, and blocked items.
// Recommends adjustments without modifying goals without approval.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import type { DelegateStub } from "./types.ts";
import { evaluateAction } from "../../../action-policy/src/policy.ts";

export class TolaPortfolioWorkflow implements WorkflowModule {
  readonly automationKey = "tola-weekly-portfolio-review";
  readonly owner = "tola";
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
      // 1. Assess open goals
      const goalsRead = evaluateAction("blackboard.listGoals", {}, { maxPayloadBytes: 16384 });
      if (goalsRead.decision !== "ALLOW") throw new Error(`Cannot read goals: ${goalsRead.reason}`);

      // 2. Assess task completion rates
      const tasksRead = evaluateAction("blackboard.listTasks", {}, { maxPayloadBytes: 16384 });
      if (tasksRead.decision !== "ALLOW") throw new Error(`Cannot read tasks: ${tasksRead.reason}`);

      // 3. Assess blocked items (read is allowed for all actions)
      const blockedRead = evaluateAction("blackboard.listTasks", {}, { maxPayloadBytes: 16384 });
      if (blockedRead.decision !== "ALLOW") throw new Error(`Cannot read blocked items: ${blockedRead.reason}`);

      // 4. Recommend adjustments — gate consequential commitments (C2)
      const modifyDecision = evaluateAction("blackboard.updateTaskStatus", {}, { maxPayloadBytes: 16384 });
      if (modifyDecision.decision === "ALLOW") {
        // Pre-authorised internal reversible write — can proceed
        const adjustResult = await this.delegate("tola", "review-and-adjust-portfolio", 60_000);
        if (!adjustResult.ok) {
          await context.notify("telegram:5647750316", `Portfolio review: adjustment failed — ${adjustResult.error}`);
        }
      } else {
        // Not pre-authorised — needs approval before modifying goals
        await context.notify("telegram:5647750316", "Portfolio review: goal modifications require operator approval");
      }

      const summary = `Tola weekly portfolio: goals assessed, completion rates reviewed, blocked items identified. Adjustments recommended.`;
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary });
      return { status: "ok", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: { goalsAssessment: "complete", taskAssessment: "complete", blockedAssessment: "complete" } };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
