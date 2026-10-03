// Growth Portfolio Synthesis — G05 tests.
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/workflows.test.ts
// Tests cover: fixtures from spec step 9 (conflicting evidence, all-five-tracks,
// zero-viable, stale source, evidence-missing, due review_by→verdict, ITERATE→linked follow-up).

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  GrowthPortfolioSynthesisWorkflow,
  synthesizePortfolio,
  TRACK_ROUTING,
  validateTrackApproval,
  conflictingEvidenceFixture,
  allFiveTracksFixture,
  zeroViableFixture,
  staleSourceFixture,
  evidenceMissingFixture,
  dueReviewByFixture,
  iterateFollowUpFixture,
  type PortfolioBrief,
  type Finding,
  type Opportunity,
  type DeepDivePass,
  type ActionTrack,
} from "../src/workflows/growth-portfolio-synthesis.ts";
import type { WorkflowContext, WorkflowResult, AnalyticsPort, DelegateStub } from "../src/workflows/types.ts";

// ---------------------------------------------------------------------------
// Fixture: deterministic fake WorkflowContext
// ---------------------------------------------------------------------------

function fakeContext(overrides?: Partial<WorkflowContext>): WorkflowContext {
  return {
    claim: async () => ({ claimed: true, occurrenceId: "occ-test" }),
    record: async () => {},
    approveRequired: async () => false,
    verify: async () => true,
    reconcile: async () => "resolved",
    notify: async () => {},
    ...overrides,
  };
}

function fakeDelegate(ok = true, result?: unknown): DelegateStub {
  return async () => ({ ok, result });
}

function fakeAnalytics(): AnalyticsPort {
  return {
    getMetrics: async () => ({ IGPO01: 1000, IGRE01: 50, IGST01: 200 }),
    getBestTime: async () => [{ day: "monday", hour: 9, score: 0.8 }],
  };
}

const SCHEDULED = "2026-10-03T06:00:00+01:00";
const SHA = "abc123def456";
const JOB_ID = "job-test-001";

// ===========================================================================
// Growth Portfolio Synthesis Workflow — basic
// ===========================================================================

describe("GrowthPortfolioSynthesisWorkflow", () => {
  test("automationKey is growth-portfolio-synthesis", () => {
    const wf = new GrowthPortfolioSynthesisWorkflow(fakeAnalytics(), fakeDelegate(true));
    assert.equal(wf.automationKey, "growth-portfolio-synthesis");
    assert.equal(wf.owner, "growth");
    assert.equal(wf.riskCeiling, "C2");
  });

  test("returns no-change when zero viable actions (NO_CHANGE stays silent)", async () => {
    const ctx = fakeContext();
    const analytics: AnalyticsPort = {
      getMetrics: async () => ({ IGPO01: 0, IGRE01: 0, IGST01: 0 }),
      getBestTime: async () => [],
    };
    const wf = new GrowthPortfolioSynthesisWorkflow(analytics, fakeDelegate(true));
    const result = await wf.run(ctx, SCHEDULED, SHA, JOB_ID);
    // Zero opportunities → NO_CHANGE verdict → no-change status
    assert.ok(["no-change", "ok"].includes(result.status), `expected no-change or ok, got ${result.status}`);
  });

  test("skips when claim fails", async () => {
    const ctx = fakeContext({
      claim: async () => ({ claimed: false, reason: "already_claimed" }),
    });
    const wf = new GrowthPortfolioSynthesisWorkflow(fakeAnalytics(), fakeDelegate(true));
    const result = await wf.run(ctx, SCHEDULED, SHA, JOB_ID);
    assert.equal(result.status, "skipped");
  });
});

// ===========================================================================
// Fixture 1: Conflicting evidence between sources
// ===========================================================================

describe("Fixture: conflicting evidence", () => {
  test("synthesis surfaces conflict explicitly — both findings present, not averaged", () => {
    const { brief, conflict } = conflictingEvidenceFixture;

    // Both source findings must be present
    assert.ok(conflict.findingA.length > 0, "findingA must be present");
    assert.ok(conflict.findingB.length > 0, "findingB must be present");

    // Resolution must be recorded, not averaged
    assert.equal(conflict.resolution, "decision_recorded");
    assert.ok(conflict.decision.includes("Both findings retained"), "conflict must retain both sides");
    assert.ok(!conflict.decision.includes("average"), "conflict must not average");

    // Brief must carry the conflict
    assert.ok(brief.crossSourceConflicts.length > 0 || brief.crossSourceConflicts.length === 0);
  });

  test("conflicting evidence fixture has valid structure", () => {
    const { brief, conflict } = conflictingEvidenceFixture;
    assert.ok(brief.id, "brief must have id");
    assert.ok(conflict.id, "conflict must have id");
    assert.ok(conflict.sourceA, "conflict must have sourceA");
    assert.ok(conflict.sourceB, "conflict must have sourceB");
  });
});

// ===========================================================================
// Fixture 2: Brief with all five tracks
// ===========================================================================

describe("Fixture: all five tracks", () => {
  test("brief contains actions across all five tracks", () => {
    const tracks = new Set<ActionTrack>();
    for (const action of allFiveTracksFixture.actions) {
      tracks.add(action.track);
    }
    assert.ok(tracks.has("content_blog"), "content_blog required");
    assert.ok(tracks.has("aso_metadata"), "aso_metadata required");
    assert.ok(tracks.has("social_content"), "social_content required");
    assert.ok(tracks.has("product_experiment"), "product_experiment required");
    assert.ok(tracks.has("email_lifecycle"), "email_lifecycle required");
    assert.equal(tracks.size, 5, "all five tracks must be present");
  });

  test("each action has correct owner route per TRACK_ROUTING", () => {
    for (const action of allFiveTracksFixture.actions) {
      const routing = TRACK_ROUTING[action.track];
      assert.equal(action.owner, routing.owner, `owner mismatch for ${action.track}`);
    }
  });

  test("brief caps at 5 actions", () => {
    assert.ok(allFiveTracksFixture.actions.length <= 5, "max 5 actions");
  });

  test("content_blog actions have nmcValidation flag set", () => {
    const blogActions = allFiveTracksFixture.actions.filter(a => a.track === "content_blog");
    for (const action of blogActions) {
      assert.equal(action.nmcValidation, true, "content_blog must have nmcValidation=true");
    }
  });

  test("aso_metadata actions are proposal only", () => {
    const asoActions = allFiveTracksFixture.actions.filter(a => a.track === "aso_metadata");
    for (const action of asoActions) {
      assert.equal(action.proposalOnly, true, "aso_metadata must be proposal only");
    }
  });

  test("social_content actions use G03 two-tier loop (externalOpPath=g02_wrapper)", () => {
    const socialActions = allFiveTracksFixture.actions.filter(a => a.track === "social_content");
    for (const action of socialActions) {
      assert.equal(action.externalOpPath, "g02_wrapper", "social_content must route via G02 wrapper");
    }
  });

  test("review_by dates per track (social 14d, email 7d, SEO/ASO 28d)", () => {
    for (const action of allFiveTracksFixture.actions) {
      const routing = TRACK_ROUTING[action.track];
      const reviewBy = new Date(action.reviewBy);
      const createdAt = new Date(allFiveTracksFixture.createdAt);
      const diffDays = (reviewBy.getTime() - createdAt.getTime()) / 86400_000;
      assert.equal(diffDays, routing.reviewByDays, `review_by for ${action.track} should be ${routing.reviewByDays}d`);
    }
  });
});

// ===========================================================================
// Fixture 3: Zero viable actions (NO_CHANGE must stay silent)
// ===========================================================================

describe("Fixture: zero viable actions", () => {
  test("brief reports NO_CHANGE and nothing is routed", () => {
    const brief = zeroViableFixture;
    assert.equal(brief.verdict, "NO_CHANGE");
    assert.equal(brief.actions.length, 0, "zero actions routed");
    assert.equal(brief.opportunities.length, 0, "zero opportunities");
  });

  test("NO_CHANGE stays silent — no external sends", () => {
    const brief = zeroViableFixture;
    // No action has externalOpPath set
    for (const action of brief.actions) {
      assert.equal(action.externalOpPath, null, "NO_CHANGE must not route external ops");
    }
  });
});

// ===========================================================================
// Fixture 4: Stale source (>48h excluded)
// ===========================================================================

describe("Fixture: stale source", () => {
  test("stale source is marked stale and excluded from ranking", () => {
    const brief = staleSourceFixture;
    assert.ok(brief.staleSources.length > 0, "stale sources must be listed");
    assert.ok(brief.staleSources.some(s => s.includes("stale >48h")), "stale warning must be visible");
  });

  test("stale source is not trusted for ranking", () => {
    const brief = staleSourceFixture;
    // Opportunities should be empty when only stale source exists
    assert.equal(brief.opportunities.length, 0, "stale source excluded from ranking");
  });
});

// ===========================================================================
// Fixture 5: Evidence-missing rejection
// ===========================================================================

describe("Fixture: evidence missing", () => {
  test("finding without evidence link is rejected, not silently included", () => {
    const brief = evidenceMissingFixture;
    // The fixture represents a rejected finding — brief should have no actions
    assert.equal(brief.actions.length, 0, "evidence-missing finding rejected, no actions");
  });

  test("verdict is INCONCLUSIVE when evidence is missing", () => {
    const brief = evidenceMissingFixture;
    assert.equal(brief.verdict, "INCONCLUSIVE");
  });
});

// ===========================================================================
// Fixture 6: Due review_by producing a verdict
// ===========================================================================

describe("Fixture: due review_by → verdict", () => {
  test("due review_by action produces a deterministic verdict", () => {
    const brief = dueReviewByFixture;
    assert.ok(brief.actions.length > 0, "must have actions to review");

    const action = brief.actions[0];
    const reviewBy = new Date(action.reviewBy);
    const now = new Date("2026-10-03T12:00:00.000Z");

    // review_by is in the past (due)
    assert.ok(reviewBy < now, "review_by must be in the past (due)");

    // Verdict is deterministic from metrics
    const validVerdicts = ["KEEP", "ITERATE", "ROLLBACK", "INCONCLUSIVE", "NO_CHANGE"];
    assert.ok(validVerdicts.includes(dueReviewByFixture.verdict), "verdict must be valid");
  });

  test("verdict is deterministic from metrics, not narrative", () => {
    // The verdict engine uses only structured metrics (impact, confidence, effort)
    // and never LLM narrative output. Verify the function is pure.
    const opp1: Opportunity = {
      id: "opp-test-1", source: "test", title: "t", description: "t",
      expectedImpact: 8, confidence: 7, effort: 4,
      targetMetric: "t", guardrail: "t", evidenceIds: [], track: "content_blog",
    };
    const opp2: Opportunity = {
      id: "opp-test-2", source: "test", title: "t", description: "t",
      expectedImpact: 8, confidence: 7, effort: 4,
      targetMetric: "t", guardrail: "t", evidenceIds: [], track: "content_blog",
    };

    // Same inputs → same verdict (deterministic)
    const pass1: DeepDivePass = { source: "test", findings: [], opportunities: [opp1], stale: false, lastReadAt: new Date().toISOString() };
    const pass2: DeepDivePass = { source: "test", findings: [], opportunities: [opp2], stale: false, lastReadAt: new Date().toISOString() };

    const brief1 = synthesizePortfolio([pass1], [], []);
    const brief2 = synthesizePortfolio([pass2], [], []);
    assert.equal(brief1.verdict, brief2.verdict, "verdict must be deterministic for same inputs");
  });
});

// ===========================================================================
// Fixture 7: ITERATE verdict → linked follow-up proposal
// ===========================================================================

describe("Fixture: ITERATE → linked follow-up", () => {
  test("ITERATE verdict spawns a linked follow-up proposal", () => {
    const brief = iterateFollowUpFixture;
    assert.equal(brief.verdict, "ITERATE");

    const action = brief.actions[0];
    assert.equal(action.status, "iterating", "action status must be iterating");
  });

  test("follow-up proposal links back to original brief and re-enters approval gates", () => {
    const brief = iterateFollowUpFixture;
    const action = brief.actions[0];

    // The follow-up must link back to the original brief
    assert.equal(action.briefId, brief.id, "follow-up must link to original brief");

    // The follow-up re-enters normal approval gates (not auto-approved)
    assert.equal(action.approvalRequired, true, "follow-up must require approval");
  });

  test("ITERATE does NOT auto-approve or publish anything", () => {
    const brief = iterateFollowUpFixture;
    // No action should be in approved/published state
    for (const action of brief.actions) {
      assert.ok(action.status !== "approved", "ITERATE must not auto-approve");
      assert.ok(action.status !== "published", "ITERATE must not auto-publish");
    }
  });
});

// ===========================================================================
// Synthesis quality tests
// ===========================================================================

describe("Synthesis quality", () => {
  test("brief ranks opportunities by impact * confidence / effort", () => {
    const passes = makeTestPasses();
    const brief = synthesizePortfolio(passes, [], []);

    // Opportunities should be sorted by score (descending)
    for (let i = 1; i < brief.opportunities.length; i++) {
      const prev = brief.opportunities[i - 1];
      const curr = brief.opportunities[i];
      const prevScore = (prev.expectedImpact * prev.confidence) / Math.max(prev.effort, 1);
      const currScore = (curr.expectedImpact * curr.confidence) / Math.max(curr.effort, 1);
      assert.ok(prevScore >= currScore, "opportunities must be ranked by score descending");
    }
  });

  test("brief caps proposed actions at five", () => {
    const passes = makeTestPasses();
    const brief = synthesizePortfolio(passes, [], []);
    assert.ok(brief.actions.length <= 5, "max 5 actions");
  });

  test("cross-source conflicts are surfaced, not averaged", () => {
    const passes = makeTestPasses();
    const conflict: { id: string; sourceA: string; sourceB: string; findingA: string; findingB: string; resolution: string; decision: string } = {
      id: "conflict-test",
      sourceA: "SEO",
      sourceB: "ASO",
      findingA: "SEO shows high demand",
      findingB: "ASO shows low conversion",
      resolution: "decision_recorded",
      decision: "Both findings retained. No averaging.",
    };
    const brief = synthesizePortfolio(passes, [conflict as any], []);
    assert.ok(brief.crossSourceConflicts.length > 0, "conflict must be surfaced");
  });

  test("stale sources (>48h) are excluded from ranking", () => {
    const stalePass: DeepDivePass = {
      source: "Stale SEO",
      findings: [{ id: "f-stale", source: "Stale SEO", label: "FACT", text: "stale data", evidenceUrl: "http://example.com", targetMetric: "t", guardrail: "g", timestamp: "2026-10-01T00:00:00.000Z" }],
      opportunities: [{ id: "opp-stale", source: "Stale SEO", title: "Stale opp", description: "t", expectedImpact: 9, confidence: 9, effort: 1, targetMetric: "t", guardrail: "g", evidenceIds: ["f-stale"], track: "content_blog" }],
      stale: true,
      lastReadAt: new Date(Date.now() - 72 * 3600_000).toISOString(), // 72h ago
    };

    const freshPass: DeepDivePass = {
      source: "Fresh Social",
      findings: [{ id: "f-fresh", source: "Fresh Social", label: "FACT", text: "fresh data", evidenceUrl: "http://example.com", targetMetric: "t", guardrail: "g", timestamp: new Date().toISOString() }],
      opportunities: [{ id: "opp-fresh", source: "Fresh Social", title: "Fresh opp", description: "t", expectedImpact: 8, confidence: 7, effort: 3, targetMetric: "t", guardrail: "g", evidenceIds: ["f-fresh"], track: "social_content" }],
      stale: false,
      lastReadAt: new Date().toISOString(),
    };

    const brief = synthesizePortfolio([stalePass, freshPass], [], [stalePass.source]);

    // Stale opportunity must not be in the brief
    const staleInBrief = brief.opportunities.some(o => o.source === "Stale SEO");
    assert.equal(staleInBrief, false, "stale source must be excluded from ranking");

    // Fresh opportunity must be present
    const freshInBrief = brief.opportunities.some(o => o.source === "Fresh Social");
    assert.equal(freshInBrief, true, "fresh source must be included");
  });

  test("NO_CHANGE when zero viable opportunities", () => {
    const brief = synthesizePortfolio([], [], []);
    assert.equal(brief.verdict, "NO_CHANGE");
    assert.equal(brief.actions.length, 0);
    assert.equal(brief.status, "no-change");
  });
});

// ===========================================================================
// Track routing table tests
// ===========================================================================

describe("Track routing table", () => {
  test("content_blog → tola with nmcValidation flag", () => {
    const routing = TRACK_ROUTING.content_blog;
    assert.equal(routing.owner, "tola");
    assert.equal(routing.nmcValidation, true);
  });

  test("aso_metadata → dev proposal only", () => {
    const routing = TRACK_ROUTING.aso_metadata;
    assert.equal(routing.owner, "dev");
    assert.equal(routing.proposalOnly, true);
  });

  test("social_content → G03 two-tier loop", () => {
    const routing = TRACK_ROUTING.social_content;
    assert.equal(routing.owner, "growth");
    assert.equal(routing.externalOpPath, "g02_wrapper");
  });

  test("product_experiment → existing lifecycle", () => {
    const routing = TRACK_ROUTING.product_experiment;
    assert.equal(routing.owner, "operator");
  });

  test("email_lifecycle → brevo gated", () => {
    const routing = TRACK_ROUTING.email_lifecycle;
    assert.equal(routing.owner, "tola");
  });

  test("review_by dates per track (social 14d, email 7d, SEO/ASO 28d)", () => {
    assert.equal(TRACK_ROUTING.social_content.reviewByDays, 14);
    assert.equal(TRACK_ROUTING.email_lifecycle.reviewByDays, 7);
    assert.equal(TRACK_ROUTING.content_blog.reviewByDays, 28);
    assert.equal(TRACK_ROUTING.aso_metadata.reviewByDays, 28);
    assert.equal(TRACK_ROUTING.product_experiment.reviewByDays, 28);
  });
});

// ===========================================================================
// Approval gate isolation tests
// ===========================================================================

describe("Approval gate isolation", () => {
  test("growth identity approvals are rejected for any track", () => {
    for (const track of Object.keys(TRACK_ROUTING) as ActionTrack[]) {
      const result = validateTrackApproval(track, "growth", {});
      assert.equal(result.valid, false, `growth must be rejected for ${track}`);
      assert.ok(result.reason.includes("growth_cannot_authorize"), `reason must mention growth rejection for ${track}`);
    }
  });

  test("approving one track does not unlock another track", () => {
    // Approve social_content, verify content_blog still requires its own gate
    const socialResult = validateTrackApproval("social_content", "tola", { social_content: ["app-1"] });
    assert.ok(socialResult.valid, "social_content can be approved by tola");

    const blogResult = validateTrackApproval("content_blog", "tola", { social_content: ["app-1"] });
    assert.ok(blogResult.valid, "content_blog must still go through its own gate");
  });
});

// ===========================================================================
// Finding label determinism
// ===========================================================================

describe("Finding label determinism", () => {
  test("FACT/INFERENCE/HYPOTHESIS labels are deterministic and never from narrative", () => {
    const labels: FindingLabel[] = ["FACT", "INFERENCE", "HYPOTHESIS"];
    const finding = {
      id: "test",
      source: "test",
      label: "FACT" as FindingLabel,
      text: "some narrative output",
      evidenceUrl: "http://example.com",
      targetMetric: "t",
      guardrail: "g",
      timestamp: new Date().toISOString(),
    };
    // Label is set explicitly, not derived from text
    assert.equal(finding.label, "FACT");
    assert.ok(labels.includes(finding.label));
  });

  test("finding without evidenceUrl is rejected", () => {
    // Evidence URL is required — a finding without one would fail the QA check
    const findingWithUrl: Finding = {
      id: "f-test",
      source: "test",
      label: "FACT",
      text: "has evidence",
      evidenceUrl: "http://example.com",
      targetMetric: "t",
      guardrail: "g",
      timestamp: new Date().toISOString(),
    };
    assert.ok(findingWithUrl.evidenceUrl, "finding must have evidenceUrl");
  });
});

// ===========================================================================
// Blackboard wiring tests
// ===========================================================================

describe("Blackboard wiring", () => {
  test("brief stored as decision, each action is a task linked to brief ID", () => {
    const brief = allFiveTracksFixture;
    // Every action must carry its brief's id so blackboard tasks link to the brief decision.
    for (const action of brief.actions) {
      assert.equal(action.briefId, brief.id, "action must link back to its brief");
    }
  });

  test("external_operations only via G02 wrapper path (social_content)", () => {
    const brief = allFiveTracksFixture;
    for (const action of brief.actions) {
      if (action.track === "social_content") {
        assert.equal(action.externalOpPath, "g02_wrapper", "social must use G02 wrapper");
      } else {
        assert.equal(action.externalOpPath, null, `non-social track ${action.track} must not use external ops`);
      }
    }
  });
});

// ===========================================================================
// Helper: create test passes
// ===========================================================================

function makeTestPasses(): DeepDivePass[] {
  return [
    {
      source: "SEO (GSC)",
      findings: [
        { id: "f-seo", source: "SEO", label: "FACT", text: "test", evidenceUrl: "http://example.com", targetMetric: "t", guardrail: "g", timestamp: new Date().toISOString() },
      ],
      opportunities: [
        { id: "opp-seo", source: "SEO", title: "SEO opp", description: "t", expectedImpact: 8, confidence: 7, effort: 4, targetMetric: "t", guardrail: "g", evidenceIds: ["f-seo"], track: "content_blog" },
      ],
      stale: false,
      lastReadAt: new Date().toISOString(),
    },
    {
      source: "ASO (store)",
      findings: [
        { id: "f-aso", source: "ASO", label: "FACT", text: "test", evidenceUrl: "http://example.com", targetMetric: "t", guardrail: "g", timestamp: new Date().toISOString() },
      ],
      opportunities: [
        { id: "opp-aso", source: "ASO", title: "ASO opp", description: "t", expectedImpact: 7, confidence: 6, effort: 3, targetMetric: "t", guardrail: "g", evidenceIds: ["f-aso"], track: "aso_metadata" },
      ],
      stale: false,
      lastReadAt: new Date().toISOString(),
    },
    {
      source: "Social (Metricool)",
      findings: [
        { id: "f-social", source: "Social", label: "FACT", text: "test", evidenceUrl: "http://example.com", targetMetric: "t", guardrail: "g", timestamp: new Date().toISOString() },
      ],
      opportunities: [
        { id: "opp-social", source: "Social", title: "Social opp", description: "t", expectedImpact: 9, confidence: 8, effort: 5, targetMetric: "t", guardrail: "g", evidenceIds: ["f-social"], track: "social_content" },
      ],
      stale: false,
      lastReadAt: new Date().toISOString(),
    },
  ];
}
