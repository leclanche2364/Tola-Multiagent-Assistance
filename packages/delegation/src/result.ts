/**
 * Structured result schema — Batch 8 (§11.2).
 *
 * Every task run produces a result object. The "status" field drives the
 * Tola-side review logic in review.ts. Any "complete" status that claims
 * an external write must have a non-null evidence ref to prevent duplicate
 * external effects on retry.
 */
export interface Result {
  runId: string;
  status: "complete" | "partial" | "blocked" | "needs_approval" | "malformed";
  evidence?: string | null; // uri/ref to external artifact; required when status="complete" and external write occurred
  modelRoute: "R0" | "R1" | "R2" | "R3" | "R4";
  modelId: string | null;
  output?: unknown;
  error?: string | null;
  /** Milliseconds elapsed since run start */
  latencyMs?: number | null;
}

/** Result constructor with default status. */
export function makeResult(
  overrides: Partial<Result> = {}
): Result {
  const base: Result = {
    runId: "00000000-0000-0000-0000-000000000000",
    status: "complete" as const,
    evidence: undefined,
    modelRoute: "R1",
    modelId: "nvidia/nemotron-3.5-lightning",
  };
  return { ...base, ...overrides };
}