// Automations package entry — Batch 10.
// Exports manifest loader, reconciler, adapter, and all 8 workflow modules.
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

// Batch 10 — workflow modules
export { BlackboardReconcilerWorkflow } from "./workflows/blackboard-reconciler.ts";
export { TolaBriefWorkflow } from "./workflows/tola-brief.ts";
export { GrowthAnomalyWorkflow } from "./workflows/growth-anomaly.ts";
export { RhythmCapacityWorkflow } from "./workflows/rhythm-capacity.ts";
export { ScholarProgressWorkflow } from "./workflows/scholar-progress.ts";
export { TolaPortfolioWorkflow } from "./workflows/tola-portfolio.ts";
export { NightlyIntegrityWorkflow } from "./workflows/nightly-integrity.ts";
export { ReadonlyOpsCheckWorkflow } from "./workflows/readonly-ops-check.ts";

export type {
  WorkflowContext,
  WorkflowModule,
  WorkflowResult,
  WorkflowStatus,
  RunClaim,
  RunRelease,
  AnalyticsPort,
  DelegateStub,
} from "./workflows/types.ts";
