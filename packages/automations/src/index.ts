// Automations package entry — Batch 09.
// Exports manifest loader, reconciler, and adapter.
// The legacy in-memory runner (runner.ts, state.ts) has been retired.

export { loadManifest, MANIFEST_PATH } from "./manifest.ts";
export type {
  AutomationManifest,
  AutomationEntry,
  Schedule,
  CronSchedule,
  EverySchedule,
  AtSchedule,
  Delivery,
} from "./manifest.ts";

export { AutomationReconciler } from "./reconciler.ts";
export type {
  ReconciliationResult,
  ReconcilerOperation,
  OpKind,
} from "./reconciler.ts";

export {
  fakeJobSource,
  type OpenClawJob,
  type OpenClawJobSource,
  type Schedule as AdapterSchedule,
} from "./adapter.ts";
