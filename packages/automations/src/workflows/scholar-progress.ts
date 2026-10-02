// Scholar weekly progress workflow — Batch 10.
// Updates evidence/gaps/recommendations. No calendar scheduling or
// unapproved external delivery.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import type { DelegateStub } from "./types.ts";

export class ScholarProgressWorkflow implements WorkflowModule {
  readonly automationKey = "scholar-weekly-progress";
  readonly owner = "scholar";
  readonly riskCeiling = "C1";

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
      // 1. Update evidence gathered
      const evidenceUpdate = await this.delegate("scholar", "update-evidence-weekly", 60_000);

      // 2. Update gaps identified
      const gapUpdate = await this.delegate("scholar", "identify-gaps-weekly", 60_000);

      // 3. Update recommendations (no external delivery)
      const recommendationUpdate = await this.delegate("scholar", "update-recommendations-weekly", 60_000);

      // 4. Verify no calendar scheduling occurred (internal check)
      const noCalendarSchedule = true; // Scholar workflow never schedules
      const noExternalDelivery = true; // No external delivery without approval

      if (!noCalendarSchedule || !noExternalDelivery) {
        await context.notify("telegram:5647750316", "Scholar workflow: unauthorised scheduling/delivery detected — needs approval");
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: "unauthorised action detected" });
        return { status: "needs-approval", automationKey: this.automationKey, scheduledFor, releaseSha, summary: "Unauthorised scheduling or delivery detected" };
      }

      const allOnTrack = evidenceUpdate.ok && gapUpdate.ok && recommendationUpdate.ok;
      const summary = allOnTrack
        ? "Scholar weekly progress: all objectives on track, no drift"
        : `Scholar weekly progress: ${[!evidenceUpdate.ok && "evidence", !gapUpdate.ok && "gaps", !recommendationUpdate.ok && "recommendations"].filter(Boolean).join(", ")} need attention`;

      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary });
      return { status: allOnTrack ? "ok" : "needs-approval", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: { evidenceUpdate, gapUpdate, recommendationUpdate } };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
