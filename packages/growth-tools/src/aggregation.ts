/**
 * Deterministic aggregation layer — Batch 11 (Growth Tools).
 *
 * Aggregation happens BEFORE any model call.
 * Functions return compact structured summaries, never raw dumps.
 */

import type {
  SearchConsoleRow,
  GA4Event,
  GA4Metric,
  UTMAttribution,
  AggregatedSearchConsoleSummary,
  AggregatedGA4Summary,
  AggregatedUTMSummary,
} from "./client.ts";

// ======================== Search Console aggregation ========================

/** Compute weighted CTR from impressions and clicks. Pure/deterministic. */
export function weightedCTR(rows: SearchConsoleRow[]): number {
  const totalImp = rows.reduce((s, r) => s + r.impressions, 0);
  const totalClicks = rows.reduce((s, r) => s + r.clicks, 0);
  if (totalImp === 0) return 0;
  return totalClicks / totalImp;
}

/** Compute average position weighted by impressions. Pure/deterministic. */
export function weightedAvgPosition(rows: SearchConsoleRow[]): number {
  const totalImp = rows.reduce((s, r) => s + r.impressions, 0);
  if (totalImp === 0) return 0;
  const weighted = rows.reduce((s, r) => s + r.position * r.impressions, 0);
  return weighted / totalImp;
}

/** Aggregate search console rows into a compact summary. Pure/deterministic. */
export function aggregateSearchConsole(rows: SearchConsoleRow[]): AggregatedSearchConsoleSummary {
  if (rows.length === 0) {
    return {
      totalImpressions: 0, totalClicks: 0, weightedCTR: 0, avgPosition: 0,
      topPages: [], dateRange: { start: "", end: "" },
    };
  }
  const dates = rows.map(r => r.date).sort();
  const totalImp = rows.reduce((s, r) => s + r.impressions, 0);
  const totalClicks = rows.reduce((s, r) => s + r.clicks, 0);
  const ctr = weightedCTR(rows);
  const avgPos = weightedAvgPosition(rows);

  const pageMap = new Map<string, { impressions: number; clicks: number; ctr: number }>();
  for (const r of rows) {
    const existing = pageMap.get(r.page) ?? { impressions: 0, clicks: 0, ctr: 0 };
    existing.impressions += r.impressions;
    existing.clicks += r.clicks;
    existing.ctr = existing.impressions > 0 ? existing.clicks / existing.impressions : 0;
    pageMap.set(r.page, existing);
  }
  const topPages = Array.from(pageMap.entries())
    .sort((a, b) => b[1].impressions - a[1].impressions)
    .slice(0, 5)
    .map(([page, data]) => ({ page, ...data }));

  return {
    totalImpressions: totalImp,
    totalClicks: totalClicks,
    weightedCTR: Math.round(ctr * 10000) / 10000,
    avgPosition: Math.round(avgPos * 100) / 100,
    topPages,
    dateRange: { start: dates[0], end: dates[dates.length - 1] },
  };
}

// ======================== GA4 aggregation ========================

/** Aggregate GA4 events/metrics into a compact summary. Pure/deterministic. */
export function aggregateGA4(events: GA4Event[], metrics: GA4Metric[]): AggregatedGA4Summary {
  const totalEvents = metrics.reduce((s, m) => s + m.count, 0);
  const totalUsers = metrics.reduce((s, m) => s + m.users, 0);
  const eventMap = new Map<string, { count: number; users: number }>();
  for (const m of metrics) {
    const existing = eventMap.get(m.eventName) ?? { count: 0, users: 0 };
    existing.count += m.count;
    existing.users += m.users;
    eventMap.set(m.eventName, existing);
  }
  const eventBreakdown = Array.from(eventMap.entries())
    .map(([eventName, data]) => ({ eventName, ...data }))
    .sort((a, b) => b.count - a.count);

  const dates = metrics.map(m => m.date).sort();
  return {
    totalEvents, totalUsers, eventBreakdown,
    dateRange: { start: dates[0] ?? "", end: dates[dates.length - 1] ?? "" },
  };
}

// ======================== UTM aggregation ========================

/** Aggregate UTM attributions into a compact summary. Pure/deterministic. */
export function aggregateUTM(attributions: UTMAttribution[]): AggregatedUTMSummary {
  const campaigns = attributions.map(a => ({
    campaign: a.campaign, source: a.source, medium: a.medium,
    conversions: a.conversions, revenue: a.revenue,
  }));
  const totalConversions = campaigns.reduce((s, c) => s + c.conversions, 0);
  const totalRevenue = campaigns.reduce((s, c) => s + c.revenue, 0);
  return { campaigns, totalConversions, totalRevenue };
}

// ======================== Evidence vs hypothesis ========================

export interface EvidenceItem {
  source: string;
  metric: string;
  value: number;
  date: string;
}

export interface HypothesisItem {
  cause: string;
  confidence: string;
  supportingEvidence?: string;
}

/** Separate observed metrics (evidence) from suspected causes (hypothesis). Pure/deterministic. */
export function separateEvidenceHypothesis(
  evidence: EvidenceItem[],
  hypotheses: HypothesisItem[],
): { evidence: EvidenceItem[]; hypotheses: HypothesisItem[] } {
  return {
    evidence: evidence.map(e => ({ ...e })),
    hypotheses: hypotheses.map(h => ({ ...h })),
  };
}

// ======================== CTR calculation ========================

/** Calculate CTR from clicks and impressions. Pure/deterministic. */
export function calcCTR(clicks: number, impressions: number): number {
  if (impressions === 0) return 0;
  return clicks / impressions;
}
