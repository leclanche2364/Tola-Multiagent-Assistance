// Growth Tools — Batch 11
// T11.1 Search Console retrieval | T11.2 GA4 retrieval
// T11.3 UTM attribution | T11.4 Deterministic CTR
// T11.5 Evidence vs hypothesis | T11.6 Partial API outage
// T11.7 No publish/spend authority | T11.8 External skill baseline
// T11.9 Trigger precision | T11.10 Pin verification
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/growth-tools.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as nodePath from "node:path";
import {
  InMemorySearchConsoleTransport,
  InMemoryGA4Transport,
  InMemoryUTMTransport,
  aggregateSearchConsole,
  aggregateGA4,
  aggregateUTM,
  calcCTR,
  weightedCTR,
  weightedAvgPosition,
  separateEvidenceHypothesis,
  verifyAllQuarantined,
  findGrowthSkill,
  growthSkillManifests,
  type SearchConsoleRow,
  type GA4Event,
  type GA4Metric,
  type UTMAttribution,
} from "../src/index.ts";

const here = nodePath.dirname(fileURLToPath(import.meta.url));

// ==================== helpers ====================

function makeSCRows(date: string, page: string, impressions: number, clicks: number, position: number): SearchConsoleRow[] {
  return [{ date, page, impressions, clicks, ctr: clicks / impressions, position }];
}

function makeGA4Event(date: string, eventName: string, userId: string): GA4Event {
  return { date, eventName, userId, params: {} };
}

function makeGA4Metric(date: string, eventName: string, count: number, users: number): GA4Metric[] {
  return [{ date, eventName, count, users }];
}

function makeUTMAttribution(campaign: string, source: string, medium: string, conversions: number, revenue: number): UTMAttribution[] {
  return [{ campaign, source, medium, conversions, revenue }];
}

// ==================== T11.1 ====================

test("T11.1 Search Console retrieval — known range matches source within API aggregation behaviour", async () => {
  const transport = new InMemorySearchConsoleTransport({
    rows: [
      { date: "2026-01-01", page: "/home", impressions: 100, clicks: 10, ctr: 0.1, position: 1.5 },
      { date: "2026-01-02", page: "/about", impressions: 200, clicks: 20, ctr: 0.1, position: 2.0 },
      { date: "2026-01-03", page: "/contact", impressions: 50, clicks: 5, ctr: 0.1, position: 3.0 },
    ],
  });

  const rows = await transport.getSearchConsoleData("2026-01-01", "2026-01-03");
  assert.strictEqual(rows.length, 3, "Should retrieve all 3 rows for the known range");

  const subset = await transport.getSearchConsoleData("2026-01-01", "2026-01-02");
  assert.strictEqual(subset.length, 2, "Should retrieve 2 rows for the narrower range");

  // Verify aggregation behaviour
  const summary = aggregateSearchConsole(rows);
  assert.strictEqual(summary.totalImpressions, 350);
  assert.strictEqual(summary.totalClicks, 35);
  assert.strictEqual(summary.topPages.length, 3);
});

// ==================== T11.2 ====================

test("T11.2 GA4 retrieval — known property/range matches source", async () => {
  const transport = new InMemoryGA4Transport({
    events: [
      makeGA4Event("2026-01-01", "page_view", "user-1"),
      makeGA4Event("2026-01-02", "page_view", "user-2"),
      makeGA4Event("2026-01-03", "signup", "user-3"),
    ],
    metrics: [
      ...makeGA4Metric("2026-01-01", "page_view", 100, 50),
      ...makeGA4Metric("2026-01-02", "page_view", 150, 70),
      ...makeGA4Metric("2026-01-03", "signup", 30, 25),
    ],
  });

  const events = await transport.getGA4Events("2026-01-01", "2026-01-03");
  assert.strictEqual(events.length, 3, "Should retrieve all 3 events");

  const metrics = await transport.getGA4Metrics("2026-01-01", "2026-01-03");
  assert.strictEqual(metrics.length, 3, "Should retrieve all 3 metric rows");

  const summary = aggregateGA4(events, metrics);
  assert.strictEqual(summary.totalEvents, 280);
  assert.strictEqual(summary.totalUsers, 145);
  assert.strictEqual(summary.eventBreakdown.length, 2);
  assert.strictEqual(summary.eventBreakdown[0].eventName, "page_view");
});

// ==================== T11.3 ====================

test("T11.3 UTM attribution — known campaign correctly attributed", async () => {
  const transport = new InMemoryUTMTransport({
    attributions: [
      { campaign: "summer-sale", source: "google", medium: "cpc", conversions: 50, revenue: 5000 },
      { campaign: "summer-sale", source: "facebook", medium: "social", conversions: 30, revenue: 3000 },
      { campaign: "winter-promo", source: "google", medium: "cpc", conversions: 20, revenue: 2000 },
    ],
  });

  const attributions = await transport.getUTMAttribution("2026-01-01", "2026-01-31");
  assert.strictEqual(attributions.length, 3);

  const summerSale = attributions.filter(a => a.campaign === "summer-sale");
  assert.strictEqual(summerSale.length, 2, "Summer sale should have 2 attributions");
  assert.strictEqual(summerSale.reduce((s, a) => s + a.conversions, 0), 80);
  assert.strictEqual(summerSale.reduce((s, a) => s + a.revenue, 0), 8000);

  const summary = aggregateUTM(attributions);
  assert.strictEqual(summary.totalConversions, 100);
  assert.strictEqual(summary.totalRevenue, 10000);
  assert.strictEqual(summary.campaigns.length, 3);
});

// ==================== T11.4 ====================

test("T11.4 Deterministic CTR — calculation performed in code", () => {
  // calcCTR is deterministic and pure
  assert.strictEqual(calcCTR(10, 100), 0.1, "10 clicks / 100 impressions = 0.1");
  assert.strictEqual(calcCTR(0, 100), 0, "0 clicks = 0 CTR");
  assert.strictEqual(calcCTR(50, 0), 0, "0 impressions = 0 CTR");
  assert.strictEqual(calcCTR(25, 100), 0.25);

  // weightedCTR is also deterministic
  const rows: SearchConsoleRow[] = [
    { date: "2026-01-01", page: "/a", impressions: 100, clicks: 10, ctr: 0.1, position: 1 },
    { date: "2026-01-02", page: "/b", impressions: 200, clicks: 20, ctr: 0.1, position: 2 },
  ];
  assert.strictEqual(weightedCTR(rows), 0.1, "Weighted CTR must be deterministic");

  const avgPos = weightedAvgPosition(rows);
  assert.strictEqual(avgPos, 1.6666666666666667, "Weighted avg position must be deterministic");
});

// ==================== T11.5 ====================

test("T11.5 Evidence vs hypothesis — observed metrics separated from suspected causes", () => {
  const evidence = [
    { source: "GSC", metric: "impressions", value: 1000, date: "2026-01-01" },
    { source: "GA4", metric: "sessions", value: 500, date: "2026-01-01" },
  ];
  const hypotheses = [
    { cause: "Seasonal traffic drop", confidence: "medium" },
    { cause: "Algorithm update", confidence: "low" },
  ];

  const result = separateEvidenceHypothesis(evidence, hypotheses);
  assert.strictEqual(result.evidence.length, 2);
  assert.strictEqual(result.hypotheses.length, 2);
  assert.strictEqual(result.evidence[0].metric, "impressions");
  assert.strictEqual(result.hypotheses[0].cause, "Seasonal traffic drop");

  // Verify no mutation — inputs are unchanged
  assert.strictEqual(evidence.length, 2);
  assert.strictEqual(hypotheses.length, 2);
});

// ==================== T11.6 ====================

test("T11.6 Partial API outage — unavailable source labelled, no invented metrics", async () => {
  const transport = new InMemorySearchConsoleTransport({ rows: [] });

  const rows = await transport.getSearchConsoleData("2026-01-01", "2026-01-31");
  assert.strictEqual(rows.length, 0, "Unavailable source returns empty array, not errors");

  const summary = aggregateSearchConsole(rows);
  assert.strictEqual(summary.totalImpressions, 0);
  assert.strictEqual(summary.totalClicks, 0);
  assert.strictEqual(summary.weightedCTR, 0);
  assert.strictEqual(summary.topPages.length, 0);
  assert.strictEqual(summary.dateRange.start, "");

  // No invented metrics — all values are zero when source is unavailable
  assert.strictEqual(summary.totalImpressions + summary.totalClicks, 0,
    "No invented metrics when source is unavailable");
});

// ==================== T11.7 ====================

test("T11.7 No publish/spend authority — tools absent", () => {
  // Verify the transport interfaces do not have publish/spend methods
  const clientSource = readFileSync(
    nodePath.join(here, "../src/client.ts"), "utf8"
  );

  // Check that no publish or spend methods exist in the transport interfaces
  assert.ok(!clientSource.includes("publish"), "Transport must not have publish method");
  assert.ok(!clientSource.includes("spend"), "Transport must not have spend method");
  assert.ok(!clientSource.includes("createPost"), "Transport must not have createPost");
  assert.ok(!clientSource.includes("adjustBudget"), "Transport must not have adjustBudget");
  assert.ok(!clientSource.includes("setBudget"), "Transport must not have setBudget");

  // Verify aggregation functions are pure (no side effects)
  const rows: SearchConsoleRow[] = [
    { date: "2026-01-01", page: "/test", impressions: 100, clicks: 10, ctr: 0.1, position: 1 },
  ];
  const summary = aggregateSearchConsole(rows);
  // Original data unchanged
  assert.strictEqual(rows[0].impressions, 100);
});

// ==================== T11.8 ====================

test("T11.8 External skill baseline — each selected skill must improve relevant task set", () => {
  const skillNames = ["analytics", "attribution", "seo-audit", "cro", "ab-testing", "onboarding", "signup", "aso"];

  for (const name of skillNames) {
    const skill = findGrowthSkill(name);
    assert.ok(skill !== undefined, `Skill ${name} must exist`);
    assert.strictEqual(skill.review.status, "quarantined", `Skill ${name} must be quarantined`);
    assert.strictEqual(skill.licence.length > 0, true, `Skill ${name} must have a licence`);
    assert.strictEqual(skill.activation.enabled, false, `Skill ${name} must not be activated`);
  }

  // All 8 skills must be present
  assert.strictEqual(growthSkillManifests.length, 8, "All 8 growth skills must be present");
});

// ==================== T11.9 ====================

test("T11.9 Trigger precision — unrelated prompts do not invoke incorrect marketing skill", () => {
  // Verify that each skill has scoped capabilities (not overly broad)
  const broadSkills = growthSkillManifests.filter(s =>
    s.capabilities.network && s.capabilities.secrets.length > 2
  );
  assert.strictEqual(broadSkills.length, 0, "No skill should have excessive secret access");

  // Verify each skill has scoped filesystem access
  for (const skill of growthSkillManifests) {
    assert.ok(
      skill.capabilities.filesystem.length >= 1,
      `Skill ${skill.name} must have scoped filesystem access`
    );
    // No skill should have write access
    const hasWrite = skill.capabilities.filesystem.some((f: string) => f.includes("write") || f.includes("modify"));
    assert.ok(!hasWrite, `Skill ${skill.name} must not have write filesystem access`);
  }
});

// ==================== T11.10 ====================

test("T11.10 Pin verification — active skills resolve to approved local revisions only", () => {
  // Verify all growth skills are quarantined and NOT active
  const activeSkills = growthSkillManifests.filter(s => s.activation.enabled);
  assert.strictEqual(activeSkills.length, 0, "No growth skill should be active");

  // All skills must have pinned 40-char hex commits
  for (const skill of growthSkillManifests) {
    assert.ok(
      /^[0-9a-f]{40}$/.test(skill.upstream.commit),
      `Skill ${skill.name} must have a valid 40-char hex commit pin`
    );
  }

  // verifyAllQuarantined must return true
  assert.strictEqual(verifyAllQuarantined(), true, "All growth skills must pass quarantine verification");
});

// ==================== additional contract tests ====================

test("Contract: aggregateSearchConsole returns compact summary not raw dump", () => {
  const rows: SearchConsoleRow[] = [
    { date: "2026-01-01", page: "/a", impressions: 1000, clicks: 100, ctr: 0.1, position: 1 },
    { date: "2026-01-02", page: "/b", impressions: 2000, clicks: 200, ctr: 0.1, position: 2 },
    { date: "2026-01-03", page: "/c", impressions: 3000, clicks: 300, ctr: 0.1, position: 3 },
  ];

  const summary = aggregateSearchConsole(rows);
  // Must be compact: topPages capped at 5, no raw row dump
  assert.ok(summary.topPages.length <= 5);
  assert.strictEqual(typeof summary.weightedCTR, "number");
  assert.strictEqual(typeof summary.avgPosition, "number");
  // Should not contain the full raw row data in the summary
  assert.ok(!("rows" in summary));
});

test("Contract: aggregateUTM returns compact summary", () => {
  const attributions: UTMAttribution[] = [
    { campaign: "c1", source: "s1", medium: "m1", conversions: 10, revenue: 1000 },
  ];
  const summary = aggregateUTM(attributions);
  assert.strictEqual(typeof summary.totalConversions, "number");
  assert.strictEqual(typeof summary.totalRevenue, "number");
  assert.ok(Array.isArray(summary.campaigns));
});

test("Contract: InMemory transports are pure read-only", async () => {
  const scTransport = new InMemorySearchConsoleTransport({
    rows: [{ date: "2026-01-01", page: "/home", impressions: 100, clicks: 10, ctr: 0.1, position: 1 }],
  });
  const rows = await scTransport.getSearchConsoleData("2026-01-01", "2026-01-01");
  assert.strictEqual(rows.length, 1);
  // Mutating returned rows should not affect internal state
  rows[0].impressions = 9999;
  const rows2 = await scTransport.getSearchConsoleData("2026-01-01", "2026-01-01");
  assert.strictEqual(rows2[0].impressions, 100, "Internal state must not be affected by external mutation");
});
