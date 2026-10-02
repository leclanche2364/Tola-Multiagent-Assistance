// Nightly integrity/cost check workflow — Batch 10.
// Verifies Supabase connection health, checks for failed webhook deliveries,
// reports total cost. Failure-only notification.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import type { DelegateStub } from "./types.ts";

export class NightlyIntegrityWorkflow implements WorkflowModule {
  readonly automationKey = "nightly-integrity-cost-check";
  readonly owner = "tola";
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

    let allPassed = true;
    const checks: Array<{ name: string; passed: boolean; detail?: string }> = [];

    try {
      // 1. Verify Supabase connection health
      const supabaseCheck = await this.delegate("tola", "check-supabase-health", 10_000);
      const supabaseHealthy = supabaseCheck.ok;
      checks.push({ name: "supabase-connection", passed: supabaseHealthy, detail: supabaseHealthy ? "connected" : supabaseCheck.error });
      if (!supabaseHealthy) allPassed = false;

      // 2. Check for failed webhook deliveries in last 24h
      const webhookCheck = await this.delegate("tola", "check-webhook-failures-24h", 10_000);
      const webhookHealthy = webhookCheck.ok;
      checks.push({ name: "webhook-deliveries", passed: webhookHealthy, detail: webhookHealthy ? "all deliveries successful" : webhookCheck.error });
      if (!webhookHealthy) allPassed = false;

      // 3. Report total cost incurred today
      const costCheck = await this.delegate("tola", "report-daily-cost", 10_000);
      const costOk = costCheck.ok;
      checks.push({ name: "daily-cost", passed: costOk, detail: costOk ? "cost reported" : costCheck.error });
      if (!costOk) allPassed = false;

      // 4. Failure-only notification
      if (!allPassed) {
        const failedChecks = checks.filter(c => !c.passed).map(c => `${c.name}: ${c.detail}`).join("; ");
        await context.notify("telegram:5647750316", `INTEGRITY CHECK FAILED: ${failedChecks}`);
      }

      const summary = allPassed ? "All integrity checks passed" : `Integrity check: ${checks.filter(c => !c.passed).length} failure(s)`;
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: allPassed ? "succeeded" : "failed", summary });
      return { status: allPassed ? "ok" : "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: { checks } };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
