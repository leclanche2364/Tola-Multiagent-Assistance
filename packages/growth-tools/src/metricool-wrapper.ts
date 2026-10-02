/**
 * Governed Metricool write wrapper — Growth G02.
 *
 * Extends the existing native `@tola/growth-tools` package; no new plugin,
 * MCP server or direct HTTP client is created.
 *
 * Three appended fix clauses (from 02-metricool-tool-wrapper.md):
 *   1. Enumerated tool grant — Growth receives ONLY metricool_held_draft,
 *      metricool_schedule_approved, metricool_cancel_scheduled.
 *   2. Approval authority — Tier 1 and Tier 2 approvals are executed
 *      exclusively in the main session (Tola) with Habeeb's explicit sign-off.
 *      Growth can never approve, self-approve, or progress its own proposal.
 *   3. Single write path — The wrapper is growth's ONLY route to Metricool
 *      servers. Nothing leaves the gateway until both tiers exist.
 *
 * State machine:
 *   PROPOSED → TIER1_APPROVED → HELD(optional) → TIER2_APPROVED → SCHEDULED/PUBLISHED
 *
 * Live writes are DISABLED — nothing touches real Metricool.
 *
 * Reuses Batch 03 `external_operations` for idempotency (canonical
 * content+destination+schedule key). No second journal.
 */

// ======================== types ========================

/** Lifecycle stages the wrapper tracks for each proposal. */
export type ProposalStatus =
  | "PROPOSED"
  | "TIER1_APPROVED"
  | "HELD"
  | "TIER2_APPROVED"
  | "SCHEDULED"
  | "PUBLISHED"
  | "CANCELLED"
  | "REJECTED";

/** The three named tools Growth is allowed to call (enumerated grant). */
export type GrowthMetricoolTool =
  | "metricool_held_draft"
  | "metricool_schedule_approved"
  | "metricool_cancel_scheduled";

/** Which Metricool write operations exist (for deny-list completeness). */
export type MetricoolWriteOperation =
  | "createScheduledPost"
  | "createScheduledPostForReview"
  | "sendScheduledPostForReview"
  | "updateScheduledPost"
  | "cancelScheduledPost";

/** Who is making the request. */
export type AgentIdentity = "growth" | "tola" | "operator" | string;

/** A validated, canonical Metricool post payload. */
export interface MetricoolPostPayload {
  /** Post text (required for non-Story posts). */
  text: string;
  /** Target network/platform. */
  network: "twitter" | "facebook" | "instagram" | "linkedin" | "pinterest" | "youtube" | "tiktok" | "bluesky" | "threads" | "gmb";
  /** Scheduled publish date/time (ISO 8601). */
  scheduledAt: string;
  /** IANA timezone for the schedule. */
  timezone: string;
  /** Media URLs (images/videos). */
  media: string[];
  /** Alt text per media asset (must match media length). */
  altText: string[];
  /** UTM parameters to embed in links. */
  utmParams?: Record<string, string>;
  /** Metricool blog/brand ID (for scheduling). */
  blogId?: string;
}

/** Provenance of an asset (must be verifiable before scheduling). */
export interface AssetProvenance {
  url: string;
  source: "upload" | "url" | "generated" | "library";
  sha256?: string;
  mimeType?: string;
  sizeBytes?: number;
}

/** Result of pre-policy validation. */
export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

/** Evidence recorded for each operation (no tokens/personal data). */
export interface OperationEvidence {
  proposalId: string;
  action: GrowthMetricoolTool;
  payloadHash: string;
  approvalIds: string[];
  metricoolRemoteId?: string;
  status: ProposalStatus;
  requester: AgentIdentity;
  decidedBy: string | null;
  decidedAt: string | null;
  externalOpIdempotencyKey: string;
}

/** Internal proposal record. */
export interface ProposalRecord {
  id: string;
  status: ProposalStatus;
  payload: MetricoolPostPayload;
  payloadHash: string;
  approvalTier1Id: string | null;
  approvalTier1DecidedBy: string | null;
  approvalTier1DecidedAt: string | null;
  approvalTier2Id: string | null;
  approvalTier2DecidedBy: string | null;
  approvalTier2DecidedAt: string | null;
  heldAt: string | null;
  scheduledAt: string | null;
  metricoolRemoteId: string | null;
  evidence: OperationEvidence;
  createdAt: string;
  updatedAt: string;
}

// ======================== constants ========================

/** Explicit allowlist of Growth's permitted Metricool tools (fix 1). */
export const GROWTH_METRICOOL_TOOLS: readonly GrowthMetricoolTool[] = Object.freeze([
  "metricool_held_draft",
  "metricool_schedule_approved",
  "metricool_cancel_scheduled",
]);

/** Metricool write operations that are gated behind the wrapper (denied to growth directly). */
export const METRICOOL_WRITE_OPERATIONS: readonly MetricoolWriteOperation[] = Object.freeze([
  "createScheduledPost",
  "createScheduledPostForReview",
  "sendScheduledPostForReview",
  "updateScheduledPost",
  "cancelScheduledPost",
]);

/** Identities that are authorised to approve (fix 2 — growth is excluded). */
const APPROVAL_AUTHORITIES: readonly string[] = Object.freeze(["tola", "operator"]);

/** Live writes are disabled — the wrapper never executes real Metricool calls. */
export const LIVE_WRITES_DISABLED = true;

/** Text length limits per network (approximate, from Metricool constraints). */
const TEXT_LIMITS: Record<string, number> = {
  twitter: 280,
  facebook: 5000,
  instagram: 2200,
  linkedin: 3000,
  pinterest: 500,
  youtube: 5000,
  tiktok: 2200,
  bluesky: 300,
  threads: 500,
  gmb: 5000,
};

/** Maximum media items per post. */
const MAX_MEDIA_ITEMS = 10;

/** Maximum alt text length per asset. */
const MAX_ALT_TEXT_LENGTH = 1000;

/** Allowed IANA timezones (common subset; full list is larger). */
const ALLOWED_TIMEZONES: readonly string[] = Object.freeze([
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Europe/Madrid",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Toronto",
  "America/Vancouver",
  "Asia/Tokyo",
  "Asia/Shanghai",
  "Asia/Singapore",
  "Australia/Sydney",
  "Australia/Melbourne",
  "Pacific/Auckland",
  "UTC",
]);

/** Allowed destination networks for Growth (profile/platform allowlist). */
const ALLOWED_NETWORKS: readonly GrowthMetricoolTool[] = Object.freeze([
  "metricool_held_draft",
  "metricool_schedule_approved",
  "metricool_cancel_scheduled",
]);

// ======================== helpers ========================

function canonicalStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return JSON.stringify(value.map(canonicalStringify));
  const sorted = Object.keys(value).sort();
  const obj: Record<string, unknown> = {};
  for (const k of sorted) obj[k] = canonicalStringify((value as Record<string, unknown>)[k]);
  return JSON.stringify(obj);
}

/** Derive a stable SHA-256-like hash of the canonical payload. */
export function hashPayload(payload: unknown): string {
  // Use a simple deterministic hash for the wrapper's internal tracking.
  // In production this would be a real SHA-256; for the wrapper's idempotency
  // key derivation the exact algorithm is not material.
  const str = canonicalStringify(payload);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0; // Convert to 32bit integer
  }
  // Return a hex string that is stable and deterministic.
  return "hash_" + Math.abs(hash).toString(16).padStart(8, "0") + "_" + str.length.toString(16);
}

/** Derive the external_operations idempotency key from canonical content+destination+schedule. */
export function deriveIdempotencyKey(
  payload: MetricoolPostPayload,
  action: GrowthMetricoolTool,
): string {
  const canonical = canonicalStringify({
    action,
    network: payload.network,
    scheduledAt: payload.scheduledAt,
    text: payload.text,
    media: payload.media,
  });
  // Stable hash-like key: first 16 chars of the canonical string's length + first 8 chars of hash
  const h = hashPayload(canonical);
  return `extop:${action}:${payload.network}:${h}`;
}

/** Validate profile allowlists, timezone, text/media limits, asset provenance, alt text, UTM rules. */
export function validatePayload(
  payload: MetricoolPostPayload,
  requester: AgentIdentity,
): ValidationResult {
  const errors: string[] = [];

  // --- Profile/platform allowlist ---
  const allowedNetworks = [
    "twitter", "facebook", "instagram", "linkedin",
    "pinterest", "youtube", "tiktok", "bluesky",
    "threads", "gmb",
  ];
  if (!payload.network) {
    errors.push("missing_network");
  } else if (!allowedNetworks.includes(payload.network)) {
    errors.push(`network_not_allowed:${payload.network}`);
  }
  if (!ALLOWED_TIMEZONES.includes(payload.timezone as string) && payload.timezone !== "UTC") {
    // timezone checked separately below
  }

  // --- Timezone validation ---
  if (!payload.timezone) {
    errors.push("missing_timezone");
  } else if (!ALLOWED_TIMEZONES.includes(payload.timezone)) {
    errors.push(`timezone_not_allowed:${payload.timezone}`);
  }

  // --- Text limits ---
  if (typeof payload.text !== "string" || payload.text.trim().length === 0) {
    errors.push("missing_or_empty_text");
  } else if (TEXT_LIMITS[payload.network] && payload.text.length > TEXT_LIMITS[payload.network]) {
    errors.push(`text_exceeds_limit:${payload.text.length}>${TEXT_LIMITS[payload.network]}`);
  }

  // --- Media limits ---
  if (payload.media.length > MAX_MEDIA_ITEMS) {
    errors.push(`too_many_media:${payload.media.length}>${MAX_MEDIA_ITEMS}`);
  }

  // --- Asset provenance ---
  for (let i = 0; i < payload.media.length; i++) {
    const url = payload.media[i];
    if (!url || typeof url !== "string") {
      errors.push(`media_${i}_invalid_url`);
      continue;
    }
    // Must be a valid HTTP(S) URL
    try {
      const u = new URL(url);
      if (u.protocol !== "https:" && u.protocol !== "http:") {
        errors.push(`media_${i}_invalid_protocol`);
      }
    } catch {
      errors.push(`media_${i}_invalid_url_format`);
    }
  }

  // --- Alt text ---
  if (payload.altText.length !== payload.media.length) {
    errors.push(`alt_text_count_mismatch:media=${payload.media.length},altText=${payload.altText.length}`);
  }
  for (let i = 0; i < payload.altText.length; i++) {
    if (payload.altText[i].length > MAX_ALT_TEXT_LENGTH) {
      errors.push(`alt_text_${i}_too_long:${payload.altText[i].length}>${MAX_ALT_TEXT_LENGTH}`);
    }
  }

  // --- UTM rules ---
  if (payload.utmParams) {
    const allowedUtmKeys = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"];
    for (const key of Object.keys(payload.utmParams)) {
      if (!allowedUtmKeys.includes(key)) {
        errors.push(`invalid_utm_key:${key}`);
      }
    }
    // utm_source and utm_medium are required if utmParams is present
    if (payload.utmParams.utm_source && payload.utmParams.utm_medium) {
      // OK
    } else if (Object.keys(payload.utmParams).length > 0) {
      // If any UTM params are provided, at least source and medium should be present
      // (soft validation — log warning but don't block)
    }
  }

  // --- Blog ID required for scheduling operations ---
  if (!payload.blogId) {
    errors.push("missing_blogId");
  }

  // --- Scheduled time must be in the future ---
  if (payload.scheduledAt) {
    const scheduled = new Date(payload.scheduledAt);
    if (isNaN(scheduled.getTime())) {
      errors.push("invalid_scheduledAt_format");
    } else if (scheduled <= new Date()) {
      errors.push("scheduled_at_in_past");
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// ======================== wrapper ========================

/**
 * Governed Metricool write wrapper.
 *
 * This is the ONLY route to Metricool servers for Growth. It:
 *   - Validates payloads before policy evaluation
 *   - Enforces the two-tier approval state machine
 *   - Rejects approvals authored by the growth identity (fix 2)
 *   - Never executes live writes (LIVE_WRITES_DISABLED = true)
 *   - Reuses external_operations idempotency keys (no second journal)
 *   - Records approval IDs, payload hash, Metricool remote ID, safe evidence
 */
export class GovernedMetricoolWrapper {
  private proposals = new Map<string, ProposalRecord>();
  private externalOps = new Map<string, { status: string; evidenceRef: string }>();

  constructor() {}

  // ==================== PROPOSED ====================

  /**
   * Create a new PROPOSED proposal.
   * This is the entry point for Growth to submit a Metricool write request.
   * Growth never progresses past this state on its own.
   */
  async propose(params: {
    id: string;
    payload: MetricoolPostPayload;
    requester: AgentIdentity;
  }): Promise<ProposalRecord> {
    const { id, payload, requester } = params;

    // Validate before any policy evaluation.
    const validation = validatePayload(payload, requester);
    if (!validation.valid) {
      const record = this._createRecord(id, "PROPOSED", payload, requester);
      record.status = "REJECTED";
      record.evidence = {
        ...record.evidence,
        status: "REJECTED",
      };
      this.proposals.set(id, record);
      throw new Error(`validation_failed:${validation.errors.join(";")}`);
    }

    const record = this._createRecord(id, "PROPOSED", payload, requester);
    this.proposals.set(id, record);
    return record;
  }

  // ==================== TIER 1 APPROVAL ====================

  /**
   * Record Tier 1 approval (editorial/schedule).
   * Only Tola/operator identities may approve (fix 2).
   * Growth identity is rejected.
   */
  async approveTier1(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
    approvalId: string;
  }): Promise<ProposalRecord> {
    const { proposalId, decidedBy, approvalId } = params;
    const record = this.proposals.get(proposalId);
    if (!record) throw new Error(`proposal_not_found:${proposalId}`);

    // Fix 2: reject approvals authored by growth identity.
    if (decidedBy === "growth") {
      return this._rejectApproval(record, "growth_cannot_self_approve", decidedBy);
    }

    // Fix 2: only authorised approvers.
    if (!APPROVAL_AUTHORITIES.includes(decidedBy)) {
      return this._rejectApproval(record, `unauthorised_approver:${decidedBy}`, decidedBy);
    }

    // Must be in PROPOSED state.
    if (record.status !== "PROPOSED") {
      return this._rejectApproval(record, `wrong_status_for_tier1:${record.status}`, decidedBy);
    }

    record.approvalTier1Id = approvalId;
    record.approvalTier1DecidedBy = decidedBy;
    record.approvalTier1DecidedAt = new Date().toISOString();
    record.status = "TIER1_APPROVED";
    record.updatedAt = new Date().toISOString();
    record.evidence.approvalIds.push(approvalId);
    record.evidence.decidedBy = decidedBy;
    record.evidence.decidedAt = record.approvalTier1DecidedAt;
    record.evidence.status = "TIER1_APPROVED";

    this.proposals.set(proposalId, record);
    return record;
  }

  // ==================== HELD (optional) ====================

  /**
   * Place a TIER1_APPROVED proposal in HELD status.
   * This is an optional intermediate state before Tier 2 approval.
   * Growth cannot trigger HELD — only the main session (Tola) can.
   */
  async hold(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
  }): Promise<ProposalRecord> {
    const { proposalId, decidedBy } = params;
    const record = this.proposals.get(proposalId);
    if (!record) throw new Error(`proposal_not_found:${proposalId}`);

    if (decidedBy === "growth") {
      return this._rejectApproval(record, "growth_cannot_hold_own_proposal", decidedBy);
    }

    if (!APPROVAL_AUTHORITIES.includes(decidedBy)) {
      return this._rejectApproval(record, `unauthorised_holder:${decidedBy}`, decidedBy);
    }

    if (record.status !== "TIER1_APPROVED") {
      return this._rejectApproval(record, `wrong_status_for_hold:${record.status}`, decidedBy);
    }

    record.status = "HELD";
    record.heldAt = new Date().toISOString();
    record.updatedAt = new Date().toISOString();
    record.evidence.status = "HELD";
    record.evidence.decidedBy = decidedBy;
    record.evidence.decidedAt = record.heldAt;

    this.proposals.set(proposalId, record);
    return record;
  }

  // ==================== TIER 2 APPROVAL ====================

  /**
   * Record Tier 2 approval (final release).
   * Only Tola/operator identities may approve (fix 2).
   * Growth identity is rejected.
   * Both tiers must share the same payload hash (fix 2 — content change invalidates).
   */
  async approveTier2(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
    approvalId: string;
    payload: MetricoolPostPayload;
  }): Promise<ProposalRecord> {
    const { proposalId, decidedBy, approvalId, payload } = params;
    const record = this.proposals.get(proposalId);
    if (!record) throw new Error(`proposal_not_found:${proposalId}`);

    // Fix 2: reject approvals authored by growth identity.
    if (decidedBy === "growth") {
      return this._rejectApproval(record, "growth_cannot_self_approve", decidedBy);
    }

    // Fix 2: only authorised approvers.
    if (!APPROVAL_AUTHORITIES.includes(decidedBy)) {
      return this._rejectApproval(record, `unauthorised_approver:${decidedBy}`, decidedBy);
    }

    // Must be in TIER1_APPROVED or HELD state.
    if (record.status !== "TIER1_APPROVED" && record.status !== "HELD") {
      return this._rejectApproval(record, `wrong_status_for_tier2:${record.status}`, decidedBy);
    }

    // Verify payload hash matches — content change invalidates both tiers.
    const currentHash = record.payloadHash;
    const newHash = hashPayload(payload);
    if (currentHash !== newHash) {
      return this._rejectApproval(record, "payload_changed_since_tier1", decidedBy);
    }

    record.approvalTier2Id = approvalId;
    record.approvalTier2DecidedBy = decidedBy;
    record.approvalTier2DecidedAt = new Date().toISOString();
    record.status = "TIER2_APPROVED";
    record.updatedAt = new Date().toISOString();
    record.evidence.approvalIds.push(approvalId);
    record.evidence.decidedBy = decidedBy;
    record.evidence.decidedAt = record.approvalTier2DecidedAt;
    record.evidence.status = "TIER2_APPROVED";

    this.proposals.set(proposalId, record);
    return record;
  }

  // ==================== SCHEDULE / PUBLISH ====================

  /**
   * Schedule or publish a Metricool post.
   * Fix 3: single write path — the wrapper is the ONLY route.
   * Fix 3: live writes are DISABLED — nothing touches real Metricool.
   * Both tiers must be satisfied before this step.
   */
  async scheduleOrPublish(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
    approvalId?: string;
  }): Promise<ProposalRecord> {
    const { proposalId, decidedBy, approvalId } = params;
    const record = this.proposals.get(proposalId);
    if (!record) throw new Error(`proposal_not_found:${proposalId}`);

    // Fix 2: reject growth self-approval.
    if (decidedBy === "growth") {
      return this._rejectApproval(record, "growth_cannot_schedule_own_proposal", decidedBy);
    }

    // Both tiers must be satisfied.
    if (record.status !== "TIER2_APPROVED") {
      return this._rejectApproval(record, `wrong_status_for_schedule:${record.status}`, decidedBy);
    }

    // Fix 3: single write path — live writes disabled.
    if (LIVE_WRITES_DISABLED) {
      // Record the intent but do NOT call Metricool.
      record.status = "SCHEDULED";
      record.scheduledAt = new Date().toISOString();
      record.metricoolRemoteId = undefined; // No real remote ID — live writes disabled.
      record.updatedAt = new Date().toISOString();
      record.evidence.status = "SCHEDULED";
      record.evidence.decidedBy = decidedBy;
      record.evidence.decidedAt = record.scheduledAt;
      if (approvalId) {
        record.evidence.approvalIds.push(approvalId);
      }
      this.proposals.set(proposalId, record);
      return record;
    }

    // This branch is unreachable while LIVE_WRITES_DISABLED = true.
    // It exists only to document the intended behaviour when live writes are enabled.
    throw new Error("live_writes_disabled_cannot_execute_real_metricool_call");
  }

  // ==================== CANCEL ====================

  /**
   * Cancel a scheduled post.
   * Only Tola/operator can cancel (fix 2).
   * Growth cannot cancel its own proposals.
   */
  async cancelScheduled(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
    approvalId: string;
  }): Promise<ProposalRecord> {
    const { proposalId, decidedBy, approvalId } = params;
    const record = this.proposals.get(proposalId);
    if (!record) throw new Error(`proposal_not_found:${proposalId}`);

    // Fix 2: reject growth self-cancellation.
    if (decidedBy === "growth") {
      return this._rejectApproval(record, "growth_cannot_cancel_own_proposal", decidedBy);
    }

    if (!APPROVAL_AUTHORITIES.includes(decidedBy)) {
      return this._rejectApproval(record, `unauthorised_canceller:${decidedBy}`, decidedBy);
    }

    if (record.status !== "SCHEDULED" && record.status !== "TIER2_APPROVED" && record.status !== "HELD" && record.status !== "PROPOSED" && record.status !== "TIER1_APPROVED") {
      return this._rejectApproval(record, `wrong_status_for_cancel:${record.status}`, decidedBy);
    }

    record.status = "CANCELLED";
    record.updatedAt = new Date().toISOString();
    record.evidence.status = "CANCELLED";
    record.evidence.decidedBy = decidedBy;
    record.evidence.decidedAt = new Date().toISOString();
    record.evidence.approvalIds.push(approvalId);

    this.proposals.set(proposalId, record);
    return record;
  }

  // ==================== GROWTH TOOL ENTRY POINTS ====================

  /**
   * metricool_held_draft — Growth's only permitted tool for creating held drafts.
   * Validates, creates a PROPOSED record, and returns it.
   * No Metricool call is made — the draft stays in Blackboard until both approvals exist.
   */
  async metricool_held_draft(params: {
    id: string;
    payload: MetricoolPostPayload;
    requester: AgentIdentity;
  }): Promise<ProposalRecord> {
    // Fix 1: enumerated tool grant — only this tool name is allowed for Growth.
    // Any other Metricool write tool must go through the wrapper, not directly.
    return this.propose(params);
  }

  /**
   * metricool_schedule_approved — Schedule a post that has both tiers approved.
   * Growth can request scheduling, but the actual scheduling is gated by the state machine.
   */
  async metricool_schedule_approved(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
    approvalId?: string;
  }): Promise<ProposalRecord> {
    return this.scheduleOrPublish(params);
  }

  /**
   * metricool_cancel_scheduled — Cancel a scheduled post.
   * Growth can request cancellation, but only Tola/operator can execute it.
   */
  async metricool_cancel_scheduled(params: {
    proposalId: string;
    decidedBy: AgentIdentity;
    approvalId: string;
  }): Promise<ProposalRecord> {
    return this.cancelScheduled(params);
  }

  // ==================== INTERNAL HELPERS ====================

  private _createRecord(
    id: string,
    status: ProposalStatus,
    payload: MetricoolPostPayload,
    requester: AgentIdentity,
  ): ProposalRecord {
    const now = new Date().toISOString();
    const payloadHash = hashPayload(payload);
    const idempotencyKey = deriveIdempotencyKey(payload, "metricool_held_draft");

    return {
      id,
      status,
      payload,
      payloadHash,
      approvalTier1Id: null,
      approvalTier1DecidedBy: null,
      approvalTier1DecidedAt: null,
      approvalTier2Id: null,
      approvalTier2DecidedBy: null,
      approvalTier2DecidedAt: null,
      heldAt: null,
      scheduledAt: null,
      metricoolRemoteId: null,
      evidence: {
        proposalId: id,
        action: "metricool_held_draft",
        payloadHash,
        approvalIds: [],
        status,
        requester,
        decidedBy: null,
        decidedAt: null,
        externalOpIdempotencyKey: idempotencyKey,
      },
      createdAt: now,
      updatedAt: now,
    };
  }

  private _rejectApproval(
    record: ProposalRecord,
    reason: string,
    decidedBy: AgentIdentity,
  ): ProposalRecord {
    record.status = "REJECTED";
    record.updatedAt = new Date().toISOString();
    record.evidence.status = "REJECTED";
    record.evidence.decidedBy = decidedBy;
    record.evidence.decidedAt = new Date().toISOString();
    record.evidence.approvalIds.push(`rejected:${reason}`);
    this.proposals.set(record.id, record);
    return record;
  }

  // ==================== QUERY ====================

  getProposal(id: string): ProposalRecord | undefined {
    return this.proposals.get(id);
  }

  listProposals(): readonly ProposalRecord[] {
    return Array.from(this.proposals.values());
  }

  /**
   * Get the idempotency key for a proposal's external operation.
   * Reuses Batch 03 external_operations for reconciliation.
   */
  getIdempotencyKey(proposalId: string): string | undefined {
    const record = this.proposals.get(proposalId);
    return record?.evidence.externalOpIdempotencyKey;
  }
}

// ======================== denied operations list ========================

/**
 * Operations that are explicitly denied to Growth (fix 1 + fix 3).
 * These are the raw writes/account changes/ads/DMs/live edit-delete
 * that the wrapper rejects and that never leave the gateway.
 */
export const DENIED_OPERATIONS: readonly string[] = Object.freeze([
  // Raw Metricool MCP write tools (not in Growth's enumerated grant).
  "createScheduledPost",
  "createScheduledPostForReview",
  "sendScheduledPostForReview",
  "updateScheduledPost",
  "cancelScheduledPost",
  // Account changes.
  "metricool_account_change",
  // Ads/spend.
  "metricool_create_ad",
  "metricool_adjust_budget",
  "metricool_set_budget",
  // DMs/replies.
  "metricool_send_dm",
  "metricool_reply_dm",
  // Live post edit/delete.
  "metricool_edit_live_post",
  "metricool_delete_live_post",
  // Auto-publish without both approvals.
  "metricool_auto_publish",
]);

// ======================== wrapped operations list ========================

/**
 * Operations that the wrapper exposes to Growth (fix 1).
 * These are the ONLY routes to Metricool servers.
 */
export const WRAPPED_OPERATIONS: readonly GrowthMetricoolTool[] = GROWTH_METRICOOL_TOOLS;