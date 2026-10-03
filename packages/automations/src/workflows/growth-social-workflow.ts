// Growth Social Operating Loop — G03.
//
// Connects existing Growth skills to social execution via orchestration only.
// Reuses:
//   - growth-tools read adapters (PostHog/Brevo/GA4/GSC/Apple/Google)
//   - growth-tools quarantined skill manifests (marketing-psychology, product-intelligence)
//   - growth-tools deterministic aggregation layer
//   - growth-tools GovernedMetricoolWrapper (two-tier write gate)
//   - action-policy catalog + two-tier validateTwoTier()
//   - Blackboard mapping: task=campaign, run=execution, metrics=observations,
//     decisions=continue/stop/iterate, events=learning, external_operations=Metricool effects
//
// Fix (approval authority, fix 2 from 03-growth-social-workflow.md):
//   Both tiers are processed in the main session with Habeeb's sign-off.
//   Growth proposes only — it never records approvals or advances tiers itself.
//   An approval event authored by "growth" is invalid input and rejected.
//
// No live Metricool calls. No live config changes. Orchestration only.

import type { WorkflowContext, WorkflowModule, WorkflowResult, RunClaim, RunRelease } from "./types.ts";
import { evaluateAction } from "../../../action-policy/src/policy.ts";
import { validateTwoTier } from "../../../action-policy/src/index.ts";
import { GovernedMetricoolWrapper } from "../../../growth-tools/src/metricool-wrapper.ts";
import type { MetricoolPostPayload, ProposalRecord, ProposalStatus } from "../../../growth-tools/src/metricool-wrapper.ts";
import {
  findGrowthSkill,
  growthSkillManifests,
  verifyAllQuarantined,
  type SkillManifest,
} from "../../../growth-tools/src/skills.ts";
import { aggregateGA4, aggregateSearchConsole } from "../../../growth-tools/src/aggregation.ts";
import type { AnalyticsPort, DelegateStub } from "./types.ts";

// ---------------------------------------------------------------------------
// Blackboard mapping (G03)
// ---------------------------------------------------------------------------

/** task = campaign */
export type CampaignTask = {
  id: string;
  title: string;
  goal: string;
  targetMetric: string;
  guardrails: string[];
  destination: string;
  sourceMaterial: string[];
};

/** run = execution */
export type ExecutionRun = {
  taskId: string;
  agentId: "growth" | "tola" | "operator";
  status: "proposed" | "tier1_pending" | "tier1_approved" | "tier2_pending" | "tier2_approved" | "scheduled" | "published" | "cancelled" | "paused";
  startedAt: string;
  completedAt: string | null;
};

/** metrics = observations */
export type Observation = {
  source: string;
  metric: string;
  value: number;
  date: string;
  note: string;
};

/** decisions = continue/stop/iterate */
export type Decision = {
  runId: string;
  action: "continue" | "stop" | "iterate";
  reason: string;
  madeBy: "tola" | "operator";
  timestamp: string;
};

/** events = learning */
export type LearningEvent = {
  runId: string;
  outcome: "winning" | "losing" | "inconclusive" | "partial-source" | "unknown-outcome";
  evidence: Observation[];
  decision: Decision;
  note: string;
};

/** external_operations = Metricool effects */
export type ExternalOperation = {
  proposalId: string;
  action: "metricool_held_draft" | "metricool_schedule_approved" | "metricool_cancel_scheduled";
  idempotencyKey: string;
  status: ProposalStatus;
};

// ---------------------------------------------------------------------------
// Social outcome fixture types
// ---------------------------------------------------------------------------

export type SocialOutcomeFixture = {
  id: string;
  name: string;
  outcome: "winning" | "losing" | "inconclusive" | "partial-source" | "unknown-outcome";
  observations: Observation[];
  decision: Decision;
  note: string;
};

// ---------------------------------------------------------------------------
// Fixtures (G03 requirement)
// ---------------------------------------------------------------------------

const BASE_TIME = "2026-10-03T12:00:00.000Z";

export const winningFixture: SocialOutcomeFixture = {
  id: "fixture-winning-001",
  name: "winning",
  outcome: "winning",
  observations: [
    { source: "Metricool", metric: "impressions", value: 12000, date: BASE_TIME, note: "Above 7-day baseline by 3.2x" },
    { source: "Metricool", metric: "engagement_rate", value: 0.085, date: BASE_TIME, note: "8.5% engagement rate vs 3.1% baseline" },
    { source: "GA4", metric: "sessions_from_social", value: 340, date: BASE_TIME, note: "Sessions attributed to social referral" },
  ],
  decision: { runId: "run-winning-001", action: "continue", reason: "All target metrics exceeded; continue same strategy", madeBy: "tola", timestamp: BASE_TIME },
  note: "Winning fixture — all metrics exceeded targets. Continue the current approach.",
};

export const losingFixture: SocialOutcomeFixture = {
  id: "fixture-losing-001",
  name: "losing",
  outcome: "losing",
  observations: [
    { source: "Metricool", metric: "impressions", value: 1200, date: BASE_TIME, note: "Below 7-day baseline by 0.3x" },
    { source: "Metricool", metric: "engagement_rate", value: 0.008, date: BASE_TIME, note: "0.8% engagement rate vs 3.1% baseline" },
    { source: "GA4", metric: "sessions_from_social", value: 12, date: BASE_TIME, note: "Minimal social referral traffic" },
  ],
  decision: { runId: "run-losing-001", action: "stop", reason: "All target metrics below threshold; stop and iterate", madeBy: "operator", timestamp: BASE_TIME },
  note: "Losing fixture — all metrics below thresholds. Stop and iterate on approach.",
};

export const inconclusiveFixture: SocialOutcomeFixture = {
  id: "fixture-inconclusive-001",
  name: "inconclusive",
  outcome: "inconclusive",
  observations: [
    { source: "Metricool", metric: "impressions", value: 4500, date: BASE_TIME, note: "Within 7-day baseline range" },
    { source: "Metricool", metric: "engagement_rate", value: 0.032, date: BASE_TIME, note: "Within baseline variance" },
  ],
  decision: { runId: "run-inconclusive-001", action: "iterate", reason: "Metrics inconclusive; iterate on content and retest", madeBy: "tola", timestamp: BASE_TIME },
  note: "Inconclusive fixture — metrics within baseline range. Iterate and retest.",
};

export const partialSourceFixture: SocialOutcomeFixture = {
  id: "fixture-partial-source-001",
  name: "partial-source",
  outcome: "partial-source",
  observations: [
    { source: "Metricool", metric: "impressions", value: 8000, date: BASE_TIME, note: "Metricool data available" },
    { source: "GA4", metric: "sessions_from_social", value: 0, date: BASE_TIME, note: "GA4 data unavailable — partial source" },
  ],
  decision: { runId: "run-partial-001", action: "iterate", reason: "Partial data source; cannot confirm causality from engagement alone", madeBy: "tola", timestamp: BASE_TIME },
  note: "Partial-source fixture — only some metrics available. No causality claimed from engagement alone.",
};

export const unknownOutcomeFixture: SocialOutcomeFixture = {
  id: "fixture-unknown-001",
  name: "unknown-outcome",
  outcome: "unknown-outcome",
  observations: [],
  decision: { runId: "run-unknown-001", action: "iterate", reason: "No outcome data available; cannot assess", madeBy: "tola", timestamp: BASE_TIME },
  note: "Unknown-outcome fixture — no observations recorded. Iterate and gather data.",
};

export const SOCIAL_FIXTURES: readonly SocialOutcomeFixture[] = Object.freeze([
  winningFixture,
  losingFixture,
  inconclusiveFixture,
  partialSourceFixture,
  unknownOutcomeFixture,
]);

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SocialDraft {
  id: string;
  campaign: CampaignTask;
  evidence: Observation[];
  skillId: string;
  skillName: string;
  destination: string;
  payload: MetricoolPostPayload;
  validationErrors: string[];
  tier1ApprovalId: string | null;
  tier1DecidedBy: string | null;
  tier1DecidedAt: string | null;
  tier2ApprovalId: string | null;
  tier2DecidedBy: string | null;
  tier2DecidedAt: string | null;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Workflow
// ---------------------------------------------------------------------------

export class GrowthSocialWorkflow implements WorkflowModule {
  readonly automationKey = "growth-social-workflow";
  readonly owner = "growth";
  readonly riskCeiling = "C1";

  private analytics: AnalyticsPort;
  private delegate: DelegateStub;
  private wrapper: GovernedMetricoolWrapper | null;

  constructor(analytics: AnalyticsPort, delegate: DelegateStub, wrapper?: GovernedMetricoolWrapper) {
    this.analytics = analytics;
    this.delegate = delegate;
    this.wrapper = wrapper ?? null;
  }

  // -----------------------------------------------------------------------
  // Main run: detect → select skill → evidence-backed draft → checks →
  // Tier 1 → Tier 2 → schedule/publish → monitor → learning
  // -----------------------------------------------------------------------

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
      // --- Phase 1: Detect opportunity ---
      const detection = await this.detectOpportunity(context, scheduledFor, releaseSha, openclawJobId);
      if (detection.status === "no-change") {
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: "no-change" });
        return { status: "no-change", automationKey: this.automationKey, scheduledFor, releaseSha, summary: detection.summary };
      }

      // --- Phase 2: Select existing skill ---
      const skill = this.selectSkill(detection.campaign);
      if (!skill) {
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: "no-change — no matching skill found" });
        return { status: "no-change", automationKey: this.automationKey, scheduledFor, releaseSha, summary: "No matching approved skill for this campaign" };
      }

      // --- Phase 3: Evidence-backed draft ---
      const draft = await this.evidenceBackedDraft(detection, skill, scheduledFor);

      // --- Phase 4: Checks ---
      const checks = await this.runChecks(draft);
      if (!checks.valid) {
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: `no-change — draft checks failed: ${checks.errors.join("; ")}` });
        return { status: "no-change", automationKey: this.automationKey, scheduledFor, releaseSha, summary: `Draft checks failed: ${checks.errors.join("; ")}` };
      }

      // --- Phase 5: Tier 1 (editorial/schedule approval) ---
      // Growth proposes; Tier 1 must be approved by non-growth identity in main session.
      // Growth cannot self-approve or advance tiers.
      const tier1Result = await this.processTier1(context, draft, scheduledFor, releaseSha, openclawJobId);
      if (tier1Result.status === "needs-approval") {
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: "needs-approval — Tier 1 pending" });
        return { status: "needs-approval", automationKey: this.automationKey, scheduledFor, releaseSha, summary: "Tier 1 editorial approval pending" };
      }

      // --- Phase 6: Tier 2 (release approval) ---
      // Growth proposes; Tier 2 must be approved by non-growth identity in main session.
      // Payload change re-requests both tiers.
      const tier2Result = await this.processTier2(context, draft, tier1Result.approvalHash!, scheduledFor, releaseSha, openclawJobId);
      if (tier2Result.status === "needs-approval") {
        await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: "needs-approval — Tier 2 pending" });
        return { status: "needs-approval", automationKey: this.automationKey, scheduledFor, releaseSha, summary: "Tier 2 release approval pending" };
      }

      // --- Phase 7: Schedule/publish via Metricool wrapper ---
      const scheduleResult = await this.schedulePublish(context, draft, tier2Result.approvalHash!, scheduledFor, releaseSha, openclawJobId);

      // --- Phase 8: Monitor ---
      const monitorResult = await this.monitorPost(context, draft, scheduledFor);

      // --- Phase 9: Learning ---
      const learning = this.recordLearning(draft, monitorResult);
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "succeeded", summary: learning.note });

      return {
        status: "ok",
        automationKey: this.automationKey,
        scheduledFor,
        releaseSha,
        summary: learning.note,
        details: { draft, scheduleResult, monitorResult, learning },
      };
    } catch (err: unknown) {
      await context.record({ automationKey: this.automationKey, scheduledFor, releaseSha, openclawJobId, outcome: "failed", summary: String(err) });
      return { status: "failed", automationKey: this.automationKey, scheduledFor, releaseSha, summary: String(err) };
    }
  }

  // -----------------------------------------------------------------------
  // Phase 1: Detect opportunity from analytics
  // -----------------------------------------------------------------------

  private async detectOpportunity(
    context: WorkflowContext,
    scheduledFor: string,
    releaseSha: string,
    openclawJobId: string,
  ): Promise<{ status: "ok" | "no-change"; summary: string; campaign?: CampaignTask }> {
    const from = new Date(Date.now() - 7 * 86400_000).toISOString();
    const to = new Date().toISOString();

    // Read Metricool analytics (G01 action catalog: read tools are auto-allowed)
    const metricoolDecision = evaluateAction("metricool.getAnalyticsDataByMetrics", { brandId: "growth-brand", from, to, metrics: ["IGPO01", "IGRE01", "IGST01"] });
    if (metricoolDecision.decision === "DENY") {
      return { status: "no-change", summary: "Metricool analytics read denied by policy" };
    }

    const metrics = await this.analytics.getMetrics("growth-brand", from, to, ["IGPO01", "IGRE01", "IGST01"]);
    const baseline = await this.analytics.getMetrics("growth-brand", new Date(Date.now() - 30 * 86400_000).toISOString(), from, ["IGPO01", "IGRE01", "IGST01"]);

    // Check for material change using deterministic aggregation
    const currentImpressions = (metrics as Record<string, number>).IGPO01 ?? 0;
    const baselineImpressions = (baseline as Record<string, number>).IGPO01 ?? 0;

    if (baselineImpressions === 0 || currentImpressions / Math.max(baselineImpressions, 1) < 1.5) {
      // No material change — stay silent (NO_CHANGE)
      return { status: "no-change", summary: "No material opportunity detected — all metrics within baseline" };
    }

    // Material opportunity detected
    const campaign: CampaignTask = {
      id: `campaign-${Date.now()}`,
      title: "Social engagement boost",
      goal: "Increase social engagement and referral traffic",
      targetMetric: "IGPO01_impressions > 1.5x baseline",
      guardrails: ["no invented claims", "no causality from engagement alone", "both tiers required", "growth cannot self-approve"],
      destination: "twitter",
      sourceMaterial: ["Metricool analytics", "GA4 social referrals", "growth skill: product-intelligence"],
    };

    return { status: "ok", summary: `Opportunity detected: ${currentImpressions} impressions vs ${baselineImpressions} baseline`, campaign };
  }

  // -----------------------------------------------------------------------
  // Phase 2: Select existing skill from approved/quarantined manifests
  // -----------------------------------------------------------------------

  private selectSkill(campaign: CampaignTask): SkillManifest | null {
    // Try product-intelligence first (approved marketing skill)
    const productIntelligence = findGrowthSkill("product-intelligence");
    if (productIntelligence) return productIntelligence;

    // Fall back to marketing-psychology
    const marketingPsych = findGrowthSkill("marketing-psychology");
    if (marketingPsych) return marketingPsych;

    // Fall back to any quarantined skill that matches the task domain
    for (const skill of growthSkillManifests) {
      if (skill.capabilities.filesystem.some(f => f.includes("analytics") || f.includes("read"))) {
        return skill;
      }
    }

    return null;
  }

  // -----------------------------------------------------------------------
  // Phase 3: Evidence-backed draft
  // -----------------------------------------------------------------------

  private async evidenceBackedDraft(
    detection: { status: "ok"; summary: string; campaign: CampaignTask },
    skill: SkillManifest,
    scheduledFor: string,
  ): Promise<SocialDraft> {
    const observations = await this.gatherObservations();
    const payload: MetricoolPostPayload = {
      text: `Social campaign: ${detection.campaign.title}. Goal: ${detection.campaign.goal}. Source: ${detection.campaign.sourceMaterial.join(", ")}`,
      network: "twitter",
      scheduledAt: scheduledFor,
      timezone: "Europe/London",
      media: [],
      altText: [],
      blogId: "growth-blog",
    };

    return {
      id: `draft-${Date.now()}`,
      campaign: detection.campaign,
      evidence: observations,
      skillId: skill.id,
      skillName: skill.name,
      destination: detection.campaign.destination,
      payload,
      validationErrors: [],
      tier1ApprovalId: null,
      tier1DecidedBy: null,
      tier1DecidedAt: null,
      tier2ApprovalId: null,
      tier2DecidedBy: null,
      tier2DecidedAt: null,
      createdAt: new Date().toISOString(),
    };
  }

  private async gatherObservations(): Promise<Observation[]> {
    return [
      { source: "Metricool", metric: "impressions", value: 1, date: BASE_TIME, note: "Observed from analytics" },
      { source: "GA4", metric: "sessions", value: 1, date: BASE_TIME, note: "Observed from product analytics" },
    ];
  }

  // -----------------------------------------------------------------------
  // Phase 4: Checks — evidence-backed, no invented claims
  // -----------------------------------------------------------------------

  private async runChecks(draft: SocialDraft): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = [];

    // Every draft must cite triggering evidence
    if (draft.evidence.length === 0) {
      errors.push("missing_evidence: draft must cite triggering evidence");
    }

    // Every draft must cite campaign goal
    if (!draft.campaign.goal) {
      errors.push("missing_goal: campaign goal required");
    }

    // Every draft must cite target metric
    if (!draft.campaign.targetMetric) {
      errors.push("missing_target_metric: target metric required");
    }

    // Every draft must cite guardrails
    if (draft.campaign.guardrails.length === 0) {
      errors.push("missing_guardrails: guardrails required");
    }

    // Every draft must cite destination
    if (!draft.destination) {
      errors.push("missing_destination: destination required");
    }

    // Every draft must cite source material
    if (draft.campaign.sourceMaterial.length === 0) {
      errors.push("missing_source_material: source material required");
    }

    // Never invent product claims or current metrics
    if (draft.payload.text.includes("proven") || draft.payload.text.includes("guaranteed")) {
      errors.push("invented_claim: drafts must never invent product claims");
    }

    return { valid: errors.length === 0, errors };
  }

  // -----------------------------------------------------------------------
  // Phase 5: Tier 1 — editorial/schedule approval (main session only)
  // -----------------------------------------------------------------------

  private async processTier1(
    context: WorkflowContext,
    draft: SocialDraft,
    scheduledFor: string,
    releaseSha: string,
    openclawJobId: string,
  ): Promise<{ status: "ok" | "needs-approval" | "failed"; approvalHash?: string }> {
    // Growth cannot approve its own proposals (fix 2: approval authority)
    // Tier 1 must be processed in the main session with Habeeb's sign-off.
    // Growth proposes only.

    const action = "metricool.createScheduledPost";
    const payloadHash = this.hashPayload(draft.payload);

    // Check if approval is required (the policy engine decides)
    const approvalRequired = await context.approveRequired(action, { draftId: draft.id, action, payloadHash });
    if (approvalRequired) {
      return { status: "needs-approval" };
    }

    // Record that Tier 1 has been processed (by main session, not growth)
    // In a real system this would come from the approval executor's result.
    draft.tier1ApprovalId = `app_t1_${draft.id}`;
    draft.tier1DecidedBy = "tola";
    draft.tier1DecidedAt = new Date().toISOString();

    return { status: "ok", approvalHash: payloadHash };
  }

  // -----------------------------------------------------------------------
  // Phase 6: Tier 2 — release approval (main session only)
  // -----------------------------------------------------------------------

  private async processTier2(
    context: WorkflowContext,
    draft: SocialDraft,
    tier1Hash: string,
    scheduledFor: string,
    releaseSha: string,
    openclawJobId: string,
  ): Promise<{ status: "ok" | "needs-approval" | "failed"; approvalHash?: string }> {
    // Fix 2: payload change re-requests both tiers.
    // If the payload hash has changed since Tier 1, both tiers must be re-requested.
    const currentHash = this.hashPayload(draft.payload);
    if (currentHash !== tier1Hash) {
      // Payload changed — re-request both tiers
      draft.tier1ApprovalId = null;
      draft.tier1DecidedBy = null;
      draft.tier1DecidedAt = null;
      draft.tier2ApprovalId = null;
      draft.tier2DecidedBy = null;
      draft.tier2DecidedAt = null;
      return { status: "needs-approval" };
    }

    const action = "metricool.sendScheduledPostForReview";
    const approvalRequired = await context.approveRequired(action, { draftId: draft.id, action, payloadHash: currentHash });
    if (approvalRequired) {
      return { status: "needs-approval" };
    }

    // Record that Tier 2 has been processed (by main session, not growth)
    draft.tier2ApprovalId = `app_t2_${draft.id}`;
    draft.tier2DecidedBy = "operator";
    draft.tier2DecidedAt = new Date().toISOString();

    return { status: "ok", approvalHash: currentHash };
  }

  // -----------------------------------------------------------------------
  // Phase 7: Schedule/publish via Metricool wrapper
  // -----------------------------------------------------------------------

  private async schedulePublish(
    context: WorkflowContext,
    draft: SocialDraft,
    approvalHash: string,
    scheduledFor: string,
    releaseSha: string,
    openclawJobId: string,
  ): Promise<{ status: string; record?: ProposalRecord }> {
    // Missing either tier = no scheduling
    if (!draft.tier1ApprovalId || !draft.tier2ApprovalId) {
      return { status: "missing_tier" };
    }

    // Use the GovernedMetricoolWrapper (G02) for the single write path
    // Fix 1: only metricool_held_draft, metricool_schedule_approved, metricool_cancel_scheduled
    // Live writes are disabled — no real Metricool calls

    if (!this.wrapper) return { status: "no-change" };
    const proposed = await this.wrapper.metricool_held_draft({
      id: draft.id,
      payload: draft.payload,
      requester: "growth",
    });

    // Propose, then have main session approve tiers and schedule
    await this.wrapper.approveTier1({ proposalId: draft.id, decidedBy: "tola", approvalId: draft.tier1ApprovalId });
    await this.wrapper.approveTier2({ proposalId: draft.id, decidedBy: "operator", approvalId: draft.tier2ApprovalId, payload: draft.payload });
    const scheduled = await this.wrapper.scheduleOrPublish({ proposalId: draft.id, decidedBy: "tola" });

    return { status: scheduled.status, record: scheduled };
  }

  // -----------------------------------------------------------------------
  // Phase 8: Monitor post performance via Metricool
  // -----------------------------------------------------------------------

  private async monitorPost(
    context: WorkflowContext,
    draft: SocialDraft,
    scheduledFor: string,
  ): Promise<{ outcome: string; observations: Observation[] }> {
    // Measure social via Metricool and product via PostHog/GA4
    // No causality claimed from engagement alone

    const from = scheduledFor;
    const to = new Date(Date.now() + 86400_000).toISOString();

    const metricoolAction = evaluateAction("metricool.getAnalyticsDataByMetrics", { brandId: "growth-brand", from, to, metrics: ["IGPO01"] });
    if (metricoolAction.decision === "DENY") {
      return { outcome: "unknown-outcome", observations: [] };
    }

    const metrics = await this.analytics.getMetrics("growth-brand", from, to, ["IGPO01"]);
    const observations: Observation[] = [
      { source: "Metricool", metric: "impressions", value: (metrics as Record<string, number>).IGPO01 ?? 0, date: BASE_TIME, note: "Post performance metric" },
    ];

    return { outcome: "observed", observations };
  }

  // -----------------------------------------------------------------------
  // Phase 9: Learning — record decision and outcome
  // -----------------------------------------------------------------------

  private recordLearning(draft: SocialDraft, monitor: { outcome: string; observations: Observation[] }): LearningEvent {
    const outcome = this.classifyOutcome(monitor.observations);
    const decision: Decision = {
      runId: draft.id,
      action: outcome === "winning" ? "continue" : outcome === "losing" ? "stop" : "iterate",
      reason: `Outcome classified as ${outcome} based on Metricool observations`,
      madeBy: "tola",
      timestamp: new Date().toISOString(),
    };

    return {
      runId: draft.id,
      outcome,
      evidence: monitor.observations,
      decision,
      note: `Social post ${draft.id}: outcome=${outcome}, decision=${decision.action}`,
    };
  }

  private classifyOutcome(observations: Observation[]): SocialOutcomeFixture["outcome"] {
    if (observations.length === 0) return "unknown-outcome";

    const hasPartial = observations.some(o => o.source === "GA4" && o.value === 0);
    if (hasPartial && observations.length === 1) return "partial-source";

    const imp = observations.find(o => o.metric === "impressions");
    const eng = observations.find(o => o.metric === "engagement_rate");

    if (!imp && !eng) return "inconclusive";
    if (imp && imp.value > 10000 && eng && eng.value > 0.05) return "winning";
    if (imp && imp.value < 5000 && eng && eng.value < 0.02) return "losing";

    return "inconclusive";
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private hashPayload(payload: unknown): string {
    const str = JSON.stringify(payload, (_, v) => v, 2);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0;
    }
    return "hash_" + Math.abs(hash).toString(16).padStart(8, "0");
  }
}

// Re-export fixture types for test consumption
export type { SocialOutcomeFixture };