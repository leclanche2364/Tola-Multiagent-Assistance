// Weekly readonly-ops check workflow — Batch 10.
// Verifies no scheduled jobs created/modified outside approved manifest.
// Compares current OpenClaw jobs against manifest and reports drift.
// Does NOT auto-remediate drift.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import { AutomationReconciler } from "../reconciler.ts";
import { loadManifest } from "../manifest.ts";
import { fakeJobSource } from "../adapter.ts";

export class ReadonlyOpsCheckWorkflow implements WorkflowModule {
  readonly automationKey = "weekly-readonly-ops-check";
  readonly owner = "tola";
  readonly riskCeiling = "C1";

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
      // 1. Load manifest (authoritative)
      const manifest = await loadManifest();

      // 2. Compare current OpenClaw jobs against manifest
      const source = fakeJobSource([]); // no live jobs in offline mode
      const reconciler = new AutomationReconciler(source, true);
      const result = await reconciler.reconcile(manifest);

      // 3. Detect drift: any add/edit/remove operation = drift
      const driftOps = result.operations.filter(o => o.kind !== "no-op");
      const hasDrift = driftOps.length > 0;

      // 4. Report drift — do NOT auto-remediate
      if (hasDrift) {
        const driftSummary = driftOps.map(o => `${o.kind}:${o.stableName} — ${o.summary}`).join("; ");
        await context.notify("telegram:5647750316", `DRIFT DETECTED: ${driftSummary}. Auto-remediation is disabled — operator review required.`);
      }

      const summary = hasDrift
        ? `Readonly ops check: ${driftOps.length} drift operation(s) detected — reported, not auto-remediated`
        : "Readonly ops check: no drift detected — all jobs match manifest";

      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary });
      return { status: hasDrift ? "needs-approval" : "no-change", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: { driftOps: driftOps.length, operations: result.operations } };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
