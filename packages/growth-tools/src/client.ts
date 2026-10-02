/**
 * Growth Tools — typed read-only adapters (Batch 11).
 *
 * Three pluggable transports with in-memory mocks:
 *   - Google Search Console
 *   - GA4
 *   - UTM / product-analytics
 *
 * All adapters are read-only. Aggregation happens in aggregation.ts
 * BEFORE any model call; functions return compact structured summaries,
 * never raw dumps.
 */

// ======================== types ========================

export interface SearchConsoleRow {
  date: string;
  page: string;
  impressions: number;
  clicks: number;
  ctr: number;
  position: number;
}

export interface GA4Event {
  date: string;
  eventName: string;
  userId: string;
  params: Record<string, string>;
}

export interface GA4Metric {
  date: string;
  eventName: string;
  count: number;
  users: number;
}

export interface UTMParam {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content?: string;
  utm_term?: string;
}

export interface UTMAttribution {
  campaign: string;
  source: string;
  medium: string;
  conversions: number;
  revenue: number;
}

export interface AggregatedSearchConsoleSummary {
  totalImpressions: number;
  totalClicks: number;
  weightedCTR: number;
  avgPosition: number;
  topPages: Array<{ page: string; impressions: number; clicks: number; ctr: number }>;
  dateRange: { start: string; end: string };
}

export interface AggregatedGA4Summary {
  totalEvents: number;
  totalUsers: number;
  eventBreakdown: Array<{ eventName: string; count: number; users: number }>;
  dateRange: { start: string; end: string };
}

export interface AggregatedUTMSummary {
  campaigns: Array<{ campaign: string; source: string; medium: string; conversions: number; revenue: number }>;
  totalConversions: number;
  totalRevenue: number;
}

// ======================== transport interfaces ========================

export interface SearchConsoleTransport {
  getSearchConsoleData(startDate: string, endDate: string): Promise<SearchConsoleRow[]>;
}

export interface GA4Transport {
  getGA4Events(startDate: string, endDate: string): Promise<GA4Event[]>;
  getGA4Metrics(startDate: string, endDate: string): Promise<GA4Metric[]>;
}

export interface UTMTransport {
  getUTMAttribution(startDate: string, endDate: string): Promise<UTMAttribution[]>;
}

// ======================== in-memory mock transports ========================

export class InMemorySearchConsoleTransport implements SearchConsoleTransport {
  private _rows: SearchConsoleRow[] = [];

  constructor(opts?: { rows?: SearchConsoleRow[] }) {
    this._rows = opts?.rows ?? [];
  }

  async getSearchConsoleData(startDate: string, endDate: string): Promise<SearchConsoleRow[]> {
    return this._rows.map(r => ({ ...r })).filter(r => r.date >= startDate && r.date <= endDate);
  }

  get rows(): readonly SearchConsoleRow[] {
    return this._rows;
  }
}

export class InMemoryGA4Transport implements GA4Transport {
  private _events: GA4Event[] = [];
  private _metrics: GA4Metric[] = [];

  constructor(opts?: { events?: GA4Event[]; metrics?: GA4Metric[] }) {
    this._events = opts?.events ?? [];
    this._metrics = opts?.metrics ?? [];
  }

  async getGA4Events(startDate: string, endDate: string): Promise<GA4Event[]> {
    return this._events.map(e => ({ ...e })).filter(e => e.date >= startDate && e.date <= endDate);
  }

  async getGA4Metrics(startDate: string, endDate: string): Promise<GA4Metric[]> {
    return this._metrics.map(m => ({ ...m })).filter(m => m.date >= startDate && m.date <= endDate);
  }

  get events(): readonly GA4Event[] { return this._events; }
  get metrics(): readonly GA4Metric[] { return this._metrics; }
}

export class InMemoryUTMTransport implements UTMTransport {
  private _attributions: UTMAttribution[] = [];

  constructor(opts?: { attributions?: UTMAttribution[] }) {
    this._attributions = opts?.attributions ?? [];
  }

  async getUTMAttribution(startDate: string, endDate: string): Promise<UTMAttribution[]> {
    return this._attributions;
  }

  get attributions(): readonly UTMAttribution[] { return this._attributions; }
}
