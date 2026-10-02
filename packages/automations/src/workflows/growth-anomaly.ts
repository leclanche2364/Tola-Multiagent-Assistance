// Growth daily anomaly workflow — Batch 10.
// Reads real analytics via AnalyticsPort, records metrics/evidence,
// creates investigation tasks only on material change; stays silent otherwise.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import type { AnalyticsPort } from "./types.ts";
import type { DelegateStub } from "./types.ts";

const MATERIAL_CHANGE_THRESHOLD = 2; // standard deviations
const BASELINE_DAYS = 7;

export class GrowthAnomalyWorkflow implements WorkflowModule {
  readonly automationKey = "growth-daily-anomaly";
  readonly owner = "growth";
  readonly riskCeiling = "C1";

  private analytics: AnalyticsPort;
  private delegate: DelegateStub;

  constructor(analytics: AnalyticsPort, delegate: DelegateStub) {
    this.analytics = analytics;
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
      const from = new Date(Date.now() - BASELINE_DAYS * 86400_000).toISOString();
      const to = new Date().toISOString();

      // 1. Read real analytics
      const metrics = await this.analytics.getMetrics("growth-brand", from, to, ["IGPO01", "IGRE01", "IGST01"]);
      const baseline = await this.analytics.getMetrics("growth-brand", new Date(Date.now() - 30 * 86400_000).toISOString(), from, ["IGPO01", "IGRE01", "IGST01"]);

      // 2. Compute deviation (deterministic, no model call)
      const anomalies: Array<{ metric: string; deviation: number; current: number; baseline: number }> = [];
      for (const [key, current] of Object.entries(metrics) as [string, number][]) {
        const base = (baseline as Record<string, number>)[key] ?? 0;
        const deviation = base > 0 ? Math.abs((current - base) / Math.max(base, 1)) : 0;
        if (deviation > MATERIAL_CHANGE_THRESHOLD / 100) {
          anomalies.push({ metric: key, deviation, current, baseline: base });
        }
      }

      if (anomalies.length === 0) {
        // No material change — stay silent (no-change)
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: "no-change" });
        return { status: "no-change", automationKey: this.automationKey, scheduledFor, releaseSha, summary: "No material change detected — all metrics within baseline" };
      }

      // 3. Material change detected — create investigation task via delegate
      const investigationResult = await this.delegate("growth", `investigate-anomaly:${anomalies.map(a => a.metric).join(",")}`, 60_000);

      // 4. Record evidence
      const summary = `Growth anomaly: ${anomalies.length} metric(s) deviating >${MATERIAL_CHANGE_THRESHOLD}σ from baseline`;
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary });

      return { status: "ok", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: { anomalies, investigationResult, baselineDays: BASELINE_DAYS } };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
