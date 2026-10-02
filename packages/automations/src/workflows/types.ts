// Workflow types — Batch 10.
// Common interfaces shared by all 8 autonomous workflows.

// ---------------------------------------------------------------------------
// Claim & record
// ---------------------------------------------------------------------------

export interface RunClaim {
  automationKey: string;
  scheduledFor: string; // ISO-8601
  releaseSha: string;
  openclawJobId: string;
  claimedBy: string;
}

export interface RunRelease {
  automationKey: string;
  scheduledFor: string;
  releaseSha: string;
  openclawJobId: string;
  outcome: "succeeded" | "failed" | "skipped";
  summary: string;
}

// ---------------------------------------------------------------------------
// Workflow context (injected into every workflow)
// ---------------------------------------------------------------------------

export interface WorkflowContext {
  /** Atomically claim this run before work begins. */
  claim: (run: RunClaim) => Promise<{ claimed: boolean; occurrenceId?: string; reason?: string }>;
  /** Record the release outcome after work completes. */
  record: (release: RunRelease) => Promise<void>;
  /** Check whether an action requires approval before execution. */
  approveRequired: (action: string, payload: unknown) => Promise<boolean>;
  /** Verify that a side-effect actually took hold. */
  verify: (check: string) => Promise<boolean>;
  /** Reconcile uncertain outcomes (e.g. unknown external state). */
  reconcile: (issue: string) => Promise<"resolved" | "needs-approval" | "deferred">;
  /** Notify on failure or drift only. */
  notify: (channel: string, message: string) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Workflow result (uniform across all 8 workflows)
// ---------------------------------------------------------------------------

export type WorkflowStatus = "ok" | "no-change" | "needs-approval" | "failed" | "skipped";

export interface WorkflowResult {
  status: WorkflowStatus;
  automationKey: string;
  scheduledFor: string;
  releaseSha: string;
  summary: string;
  details?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Typed workflow module interface
// ---------------------------------------------------------------------------

export interface WorkflowModule {
  readonly automationKey: string;
  readonly owner: string;
  readonly riskCeiling: string;
  run(context: WorkflowContext, scheduledFor: string, releaseSha: string, openclawJobId: string): Promise<WorkflowResult>;
}

// ---------------------------------------------------------------------------
// Analytics port (Growth workflow — fake fixture for offline tests)
// ---------------------------------------------------------------------------

export interface AnalyticsPort {
  getMetrics(brandId: string, from: string, to: string, metrics: string[]): Promise<Record<string, unknown>>;
  getBestTime(brandId: string, network: string, from: string, to: string, tz: string): Promise<Array<{ day: string; hour: number; score: number }>>;
}

// ---------------------------------------------------------------------------
// Delegate stub (for test-only no-live-spawn)
// ---------------------------------------------------------------------------

export type DelegateStub = (agentId: string, prompt: string, timeoutMs: number) => Promise<{ ok: boolean; result?: unknown; error?: string }>;
