// Tola brief/review workflow — Batch 10.
// Reads authoritative state, delegates within allowlist, creates/reprioritises
// internal tasks, gates consequential commitments.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import type { DelegateStub } from "./types.ts";
import { evaluateAction } from "../../../action-policy/src/policy.ts";
import { loadManifest, MANIFEST_PATH } from "../manifest.ts";

const ALLOWED_DELEGATIONS = ["blackboard-read", "blackboard-write", "memory-search", "sessions_yield"] as const;
type AllowedDelegation = typeof ALLOWED_DELEGATIONS[number];

export class TolaBriefWorkflow implements WorkflowModule {
  readonly automationKey = "tola-morning-brief";
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

    try {
      const manifest = await loadManifest();

      // 1. Read authoritative state (manifest + schedule)
      const entries = manifest.automations;

      // 2. Delegate within allowlist only
      const delegationResults: Array<{ tool: string; ok: boolean; result?: unknown; error?: string }> = [];
      for (const tool of ALLOWED_DELEGATIONS) {
        const decision = evaluateAction(`blackboard.${tool}`, {}, { maxPayloadBytes: 16384 });
        if (decision.decision === "ALLOW") {
          const res = await this.delegate("tola", `brief-delegate:${tool}`, 30_000);
          delegationResults.push({ tool, ok: res.ok, result: res.result, error: res.error });
        } else {
          delegationResults.push({ tool, ok: false, error: `not-allowed:${decision.reason}` });
        }
      }

      // 3. Gate consequential commitments (C1 = no external writes without approval)
      const gatedActions = entries.filter(e => e.riskCeiling === "C2" || e.riskCeiling === "C3" || e.riskCeiling === "C4");
      for (const entry of gatedActions) {
        const requiresApproval = await context.approveRequired("runAutomation", { automation: entry.stableName });
        if (requiresApproval) {
          await context.notify("telegram:5647750316", `NEEDS_APPROVAL: ${entry.stableName} requires operator approval before execution`);
        }
      }

      // 4. Create/reprioritise internal tasks based on manifest state
      const taskSummaries = entries.map(e => ({
        stableName: e.stableName,
        owner: e.owner,
        riskCeiling: e.riskCeiling,
        quietPolicy: e.quietPolicy,
        status: "ready" as const,
      }));

      const summary = `Tola morning brief: ${entries.length} automations reviewed, ${delegationResults.filter(d => d.ok).length} delegations completed, ${gatedActions.length} gated commitments checked`;

      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary });
      return { status: "ok", automationKey: this.automationKey, scheduledFor, releaseSha, summary, details: { taskSummaries, delegationResults, gatedCount: gatedActions.length } };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }
}
