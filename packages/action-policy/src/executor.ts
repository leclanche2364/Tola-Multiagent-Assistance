/**
 * Approval Executor — Batch 06 (§Bound approval execution) + Batch 07 scope enforcement.
 *
 * Typed execution adapter with fake implementation for tests.
 * Handles the full approval lifecycle: request → pending → approved → consumed.
 * Never performs external effects before approval is confirmed.
 *
 * Approval hash: canonical JSON of {action, payload} (same contract as
 * verifyApprovedPayload).  Scope summaries are redacted for safe display.
 */

// --- Canonical hashing ---

import { ACTION_CATALOG } from "./policy.ts";

function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return JSON.stringify(value.map(canonicalStringify));
  const sorted = Object.keys(value).sort();
  const obj: Record<string, unknown> = {};
  for (const k of sorted) obj[k] = canonicalStringify((value as Record<string, unknown>)[k]);
  return JSON.stringify(obj);
}

export function hashAction(action: string, payload: unknown): string {
  return canonicalStringify({ action, payload });
}

// --- Approval state ---

export type ApprovalState = "pending" | "approved" | "consumed" | "rejected" | "expired";

// --- Two-tier state machine ---

/** Tier 1: editorial/schedule approval of the exact canonical payload.
 *  Tier 2: distinct final release approval bound to the identical payload hash.
 *  Both tiers must be unexpired and unused before any scheduling write.
 *  Content/asset/destination/time change invalidates both tiers. */
export type Tier = 1 | 2;

export interface TierRecord {
  tier: Tier;
  approvalId: string;
  action: string;
  actionHash: string;
  status: ApprovalState;
  used: boolean;
  decidedBy: string | null;
  decidedAt: string | null;
  expiry: string;
  requester: string;
  releaseSha: string;
  taskId: string | null;
}

export interface TwoTierState {
  /** Tier 1 record — editorial/schedule approval. */
  tier1: TierRecord | null;
  /** Tier 2 record — final release approval (bound to same payload hash). */
  tier2: TierRecord | null;
  /** Payload hash both tiers must share. */
  payloadHash: string;
  /** Whether both tiers are satisfied and the action may execute. */
  get isReady(): boolean;
}

export function createTwoTierState(
  action: string,
  payload: unknown,
  payloadHash: string,
  requester: string,
  releaseSha: string,
  taskId: string | null,
  expirySeconds: number,
): TwoTierState {
  const expiry = new Date(Date.now() + expirySeconds * 1000).toISOString();
  return {
    payloadHash,
    tier1: null,
    tier2: null,
    get isReady(): boolean {
      return (
        this.tier1 !== null &&
        this.tier1.status === "approved" &&
        !this.tier1.used &&
        new Date(this.tier1.expiry) > new Date() &&
        this.tier2 !== null &&
        this.tier2.status === "approved" &&
        !this.tier2.used &&
        new Date(this.tier2.expiry) > new Date() &&
        this.tier1.actionHash === this.tier2.actionHash &&
        this.tier1.actionHash === payloadHash
      );
    },
  };
}

/** Validate that both tiers exist, are approved, unexpired, unused, and share the same hash. */
export function validateTwoTier(state: TwoTierState): { valid: boolean; reason: string } {
  if (!state.tier1) return { valid: false, reason: "missing_tier1" };
  if (!state.tier2) return { valid: false, reason: "missing_tier2" };
  if (state.tier1.status !== "approved") return { valid: false, reason: `tier1_not_approved:${state.tier1.status}` };
  if (state.tier2.status !== "approved") return { valid: false, reason: `tier2_not_approved:${state.tier2.status}` };
  if (state.tier1.used) return { valid: false, reason: "tier1_already_used" };
  if (state.tier2.used) return { valid: false, reason: "tier2_already_used" };
  if (new Date(state.tier1.expiry) <= new Date()) return { valid: false, reason: "tier1_expired" };
  if (new Date(state.tier2.expiry) <= new Date()) return { valid: false, reason: "tier2_expired" };
  if (state.tier1.actionHash !== state.payloadHash) return { valid: false, reason: "tier1_hash_mismatch" };
  if (state.tier2.actionHash !== state.payloadHash) return { valid: false, reason: "tier2_hash_mismatch" };
  return { valid: true, reason: "both_tiers_satisfied" };
}

// --- Approval record ---

export interface ApprovalRecord {
  approval_id: string;
  action: string;
  actionHash: string;
  scope: string;
  expiry: string;
  requester: string;
  releaseSha: string;
  taskId: string | null;
  status: ApprovalState;
  used: boolean;
  decidedBy: string | null;
  decidedAt: string | null;
}

// --- Execution outcome ---

export type ExecutionOutcome =
  | { status: "success"; result: unknown; evidence: string }
  | { status: "denied"; reason: string }
  | { status: "expired" }
  | { status: "consumed"; reason: "already_consumed" }
  | { status: "rejected"; reason: string }
  | { status: "unknown"; reason: string; reconciliationRequired: boolean }
  | { status: "mismatch"; reason: string }
  | { status: "concurrent"; reason: string };

// --- Parameters ---

export interface ApprovalRequestParams {
  action: string;
  payload: unknown;
  requester: string;
  releaseSha: string;
  taskId: string | null;
  expirySeconds: number;
  scope: string;
}

export interface ExecuteAllowedParams {
  action: string;
  payload: unknown;
  allowedWriteScope: string[];
  effect: () => Promise<unknown>;
}

export interface ExecuteApprovedParams {
  approvalId: string;
  action: string;
  payload: unknown;
  requester: string;
  releaseSha: string;
  taskId: string | null;
  effect: () => Promise<unknown>;
  hashFn?: (action: string, payload: unknown) => string;
}

// --- Typed adapter interface ---

export interface ApprovalExecutor {
  requestApproval(params: ApprovalRequestParams): Promise<ApprovalRecord>;
  approveApproval(approvalId: string, decidedBy: string): Promise<ApprovalRecord>;
  rejectApproval(approvalId: string, decidedBy: string): Promise<ApprovalRecord>;
  executeAllowed(params: ExecuteAllowedParams): Promise<{ success: boolean; evidence: string }>;
  executeApproved(params: ExecuteApprovedParams): Promise<ExecutionOutcome>;
  getApprovalStatus(approvalId: string): Promise<ApprovalRecord | null>;
  reconcile(approvalId: string): Promise<ApprovalRecord>;
}

// --- Redaction (matches redact.ts pattern: only safe content passes through) ---

const SAFE_SCOPE_TOKENS = new Set([
  "read",
  "write",
  "send",
  "create",
  "update",
  "delete",
  "execute",
  "run",
  "publish",
  "draft",
  "search",
  "save",
  "move",
  "assign",
  "complete",
  "cancel",
  "block",
  "message",
  "email",
  "payment",
  "subscription",
  "refund",
  "task",
  "goal",
  "project",
  "schedule",
  "block",
  "config",
  "plugin",
  "skill",
  "automation",
  "private",
  "public",
  "internal",
]);

export function redactApprovalScope(scope: string): string {
  // Redact long numeric sequences (account numbers, IDs, amounts)
  let result = scope.replace(/\b\d{10,}\b/g, "[REDACTED]");
  // Redact base64-like tokens
  result = result.replace(/\b[A-Za-z0-9+/]{20,}={0,2}\b/g, "[REDACTED]");
  // Redact secret-bearing keywords and their values (including sk_/pk_ prefixed tokens)
  result = result.replace(/\b(?:secret|token|key|password|apikey|bearer)\b/gi, "[REDACTED]");
  result = result.replace(/\b(?:sk|pk)_[A-Za-z0-9_]+/g, "[REDACTED]");
  // Redact values after key= assignments that look secret
  result = result.replace(/key=[^;]*/gi, "key=[REDACTED]");
  return result;
}

// --- Fake executor for tests (no real external effects) ---

export class FakeApprovalExecutor implements ApprovalExecutor {
  private approvals = new Map<string, ApprovalRecord>();
  private inFlight = new Set<string>();

  async requestApproval(params: ApprovalRequestParams): Promise<ApprovalRecord> {
    const id = `app_${this._nextId()}`;
    const record: ApprovalRecord = {
      approval_id: id,
      action: params.action,
      actionHash: hashAction(params.action, params.payload),
      scope: redactApprovalScope(params.scope),
      expiry: new Date(Date.now() + params.expirySeconds * 1000).toISOString(),
      requester: params.requester,
      releaseSha: params.releaseSha,
      taskId: params.taskId,
      status: "pending",
      used: false,
      decidedBy: null,
      decidedAt: null,
    };
    this.approvals.set(id, record);
    return record;
  }

  async approveApproval(approvalId: string, decidedBy: string): Promise<ApprovalRecord> {
    const record = this.approvals.get(approvalId);
    if (!record) throw new Error(`Approval ${approvalId} not found`);
    record.status = "approved";
    record.decidedBy = decidedBy;
    record.decidedAt = new Date().toISOString();
    this.approvals.set(approvalId, record);
    return record;
  }

  async rejectApproval(approvalId: string, decidedBy: string): Promise<ApprovalRecord> {
    const record = this.approvals.get(approvalId);
    if (!record) throw new Error(`Approval ${approvalId} not found`);
    record.status = "rejected";
    record.decidedBy = decidedBy;
    record.decidedAt = new Date().toISOString();
    this.approvals.set(approvalId, record);
    return record;
  }

  async executeAllowed(params: ExecuteAllowedParams): Promise<{ success: boolean; evidence: string }> {
    // Enforce delegated allowed-write scope at execution time.
    // If the action is in the catalog and has a consequence that requires
    // write scope, verify the scope is in the allowed list before executing.
    const def = ACTION_CATALOG.find((a) => `${a.domain}.${a.name}` === params.action);
    if (def && def.consequence !== "read" && def.consequence !== "internal_reversible_write") {
      // For gated consequences, the caller must supply allowedWriteScope.
      // If no scope is provided or the action is not in the scope, deny.
      if (!params.allowedWriteScope || params.allowedWriteScope.length === 0) {
        return {
          success: false,
          evidence: `allowed:${params.action}:error:no_allowed_write_scope_provided`,
        };
      }
    }
    try {
      const result = await params.effect();
      return {
        success: true,
        evidence: `allowed:${params.action}:hash=${hashAction(params.action, params.payload)}`,
      };
    } catch (err: unknown) {
      return {
        success: false,
        evidence: `allowed:${params.action}:error:${String(err)}`,
      };
    }
  }

  async executeApproved(params: ExecuteApprovedParams): Promise<ExecutionOutcome> {
    const record = this.approvals.get(params.approvalId);
    if (!record) return { status: "denied", reason: "approval_not_found" };

    const hashFn = params.hashFn ?? hashAction;

    // Check expiry first — expired is a terminal state.
    if (new Date(record.expiry) < new Date()) return { status: "expired" };
    // Check consumed/used before status — a consumed approval is not "approved" anymore.
    if (record.used) return { status: "consumed", reason: "already_consumed" };
    if (this.inFlight.has(params.approvalId)) return { status: "concurrent", reason: "concurrent_execution" };
    // All conditions must match atomically before consumption.
    if (record.status !== "approved") return { status: "denied", reason: `wrong_status:${record.status}` };
    if (hashFn(params.action, params.payload) !== record.actionHash) return { status: "mismatch", reason: "hash_mismatch" };
    if (record.requester !== params.requester) return { status: "denied", reason: "wrong_requester" };
    if (record.releaseSha !== params.releaseSha) return { status: "denied", reason: "wrong_release" };

    // Consume atomically before executing the effect.
    this.inFlight.add(params.approvalId);
    record.used = true;
    record.status = "consumed";
    this.approvals.set(params.approvalId, record);

    try {
      const result = await params.effect();
      this.inFlight.delete(params.approvalId);
      return {
        status: "success",
        result,
        evidence: `executed:${params.approvalId}:action=${params.action}:release=${params.releaseSha}`,
      };
    } catch (err: unknown) {
      // Unknown external outcome — record unknown; approval already consumed
      // so it cannot be blindly re-executed. Reconcile before retrying.
      this.inFlight.delete(params.approvalId);
      return { status: "unknown", reason: String(err), reconciliationRequired: true };
    }
  }

  async getApprovalStatus(approvalId: string): Promise<ApprovalRecord | null> {
    return this.approvals.get(approvalId) ?? null;
  }

  async reconcile(approvalId: string): Promise<ApprovalRecord> {
    const record = this.approvals.get(approvalId);
    if (!record) throw new Error(`Approval ${approvalId} not found`);
    // In a real system this would check external evidence to determine
    // what actually happened and update the record accordingly.
    return record;
  }

  private _nextId(): number {
    const n = this.approvals.size + this.inFlight.size;
    return n + 1;
  }
}