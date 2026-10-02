// OpenClaw job adapter interface — Batch 09.
// Defines the typed contract for reading current OpenClaw jobs.
// Tests use a fake listing; production would call the OpenClaw Gateway.
// No live CLI calls are made from this package.

export type CronSchedule = { kind: "cron"; expr: string; tz?: string };
export type EverySchedule = { kind: "every"; everyMs: number; anchorMs?: number };
export type AtSchedule = { kind: "at"; at: string };
export type Schedule = CronSchedule | EverySchedule | AtSchedule;

export type Delivery = {
  mode: "announce" | "none";
  channel: string;
  to: string;
  accountId?: string;
};

export type OpenClawJob = {
  id: string;
  name: string;
  enabled: boolean;
  schedule: Schedule;
  mode: "isolated" | "command" | string;
  agentId: string | null;
  delivery: Delivery | null;
};

export interface OpenClawJobSource {
  /** List current OpenClaw jobs. Returns an empty array when no jobs exist. */
  listJobs(): Promise<OpenClawJob[]>;
}

// ---------------------------------------------------------------------------
// Fake listing for tests (no live CLI)
// ---------------------------------------------------------------------------

export function fakeJobSource(jobs: OpenClawJob[]): OpenClawJobSource {
  return { listJobs: async () => [...jobs] };
}
