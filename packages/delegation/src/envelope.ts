/**
 * Task envelope schema — Batch 8 (§11.1).
 *
 * Every delegated task is wrapped in an envelope that carries the metadata
 * needed for routing, idempotency, timeout/recovery, and scope control.
 */
export interface Envelope {
  taskRef: string; // task_id uuid
  runId: string; // run_id uuid
  idempotencyKey: string; // caller-provided uuid for idempotency guard
  route: "R0" | "R1" | "R2" | "R3" | "R4";
  modelId: string | null; // null = deterministic (R0)
  allowedWriteScope: string[]; // e.g. ["create:task", "write:file", ...]
  deadline: string; // ISO-8601 deadline for timeout/retry
  timeoutSeconds: number;
  expectedResultShape: "complete" | "partial" | "blocked" | "needs_approval" | "malformed";
}

/** Minimal fixture for test scaffolding. */
export function makeEnvelope(
  overrides: Partial<Envelope> = {}
): Envelope {
  const base: Envelope = {
    taskRef: "00000000-0000-0000-0000-000000000000",
    runId: "00000000-0000-0000-0000-000000000000",
    idempotencyKey: "00000000-0000-0000-0000-000000000000",
    route: "R1",
    modelId: "nvidia/nemotron-3.5-lightning",
    allowedWriteScope: ["create:task"],
    deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    timeoutSeconds: 120,
    expectedResultShape: "complete",
  };
  return { ...base, ...overrides };
}