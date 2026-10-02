/**
 * Action Policy — Batch 05 (§Server-side action policy).
 *
 * Closed action catalog + consequence-based policy evaluation.
 * Policy is derived from action kind and the *validated* payload, never
 * from model-supplied risk labels. Unknown actions fail closed (DENY).
 *
 * Decisions are exactly: "ALLOW" | "REQUIRE_APPROVAL" | "DENY".
 */
export type Decision = "ALLOW" | "REQUIRE_APPROVAL" | "DENY";

export type ActionDomain =
  | "blackboard"
  | "delegation"
  | "myrhythm"
  | "intensiq"
  | "messaging"
  | "publication"
  | "payments"
  | "deletion"
  | "credentials"
  | "security"
  | "configuration"
  | "plugins"
  | "skills"
  | "automations";

/** How the action affects the outside world or durable state. */
export type Consequence =
  | "read"                       // internal read, no state change
  | "internal_reversible_write"  // internal, auditable, reversible
  | "private_external_write"     // external, non-public, may need envelope
  | "public_communication"       // visible to the world
  | "money"                      // financial commitment
  | "irreversible_deletion"      // cannot be undone
  | "fixed_external_commitment"  // contractual/scheduled commitments
  | "production_capability"      // changes live capability/config
  | "permanent_deny";            // catalog-level: never allowed

export interface ActionDef {
  domain: ActionDomain;
  name: string;
  consequence: Consequence;
}

/** Reasons are machine-readable: `code:detail`. */
export interface PolicyResult {
  decision: Decision;
  reason: string;
}

/**
 * The closed catalog. Adding an entry here is a policy change and must
 * go through operator review — the engine itself never grows the surface
 * from model input.
 */
export const ACTION_CATALOG: readonly ActionDef[] = Object.freeze([
  // --- Blackboard (typed tool surface, Batch 04) ---
  { domain: "blackboard", name: "listProjects", consequence: "read" },
  { domain: "blackboard", name: "getProject", consequence: "read" },
  { domain: "blackboard", name: "listGoals", consequence: "read" },
  { domain: "blackboard", name: "getGoal", consequence: "read" },
  { domain: "blackboard", name: "listTasks", consequence: "read" },
  { domain: "blackboard", name: "getTask", consequence: "read" },
  { domain: "blackboard", name: "getApproval", consequence: "read" },
  { domain: "blackboard", name: "getTaskRun", consequence: "read" },
  { domain: "blackboard", name: "createTask", consequence: "internal_reversible_write" },
  { domain: "blackboard", name: "assignTask", consequence: "internal_reversible_write" },
  { domain: "blackboard", name: "updateTaskStatus", consequence: "internal_reversible_write" },
  { domain: "blackboard", name: "recordDecision", consequence: "internal_reversible_write" },
  { domain: "blackboard", name: "recordEvent", consequence: "internal_reversible_write" },
  { domain: "blackboard", name: "requestApproval", consequence: "internal_reversible_write" },

  // --- Delegation (spawn specialists) ---
  { domain: "delegation", name: "spawnSpecialist", consequence: "internal_reversible_write" },
  { domain: "delegation", name: "sendToSpecialist", consequence: "internal_reversible_write" },
  { domain: "delegation", name: "endSpecialist", consequence: "internal_reversible_write" },

  // --- My Rhythm (scheduling, personal) ---
  { domain: "myrhythm", name: "readSchedule", consequence: "read" },
  { domain: "myrhythm", name: "createBlock", consequence: "internal_reversible_write" },
  { domain: "myrhythm", name: "moveBlock", consequence: "internal_reversible_write" },
  { domain: "myrhythm", name: "deleteBlock", consequence: "internal_reversible_write" },

  // --- IntenSIQ (research/clinical adjacent) ---
  { domain: "intensiq", name: "searchEvidence", consequence: "read" },
  { domain: "intensiq", name: "saveFinding", consequence: "internal_reversible_write" },

  // --- Messaging (external communication) ---
  { domain: "messaging", name: "sendPrivateMessage", consequence: "private_external_write" },
  { domain: "messaging", name: "postPublicMessage", consequence: "public_communication" },
  { domain: "messaging", name: "sendEmail", consequence: "private_external_write" },

  // --- Publication ---
  { domain: "publication", name: "publishContent", consequence: "public_communication" },
  { domain: "publication", name: "draftContent", consequence: "internal_reversible_write" },

  // --- Payments / money ---
  { domain: "payments", name: "checkBalance", consequence: "read" },
  { domain: "payments", name: "makePayment", consequence: "money" },
  { domain: "payments", name: "createSubscription", consequence: "money" },
  { domain: "payments", name: "issueRefund", consequence: "money" },

  // --- Deletion ---
  { domain: "deletion", name: "deleteDraft", consequence: "internal_reversible_write" },
  { domain: "deletion", name: "purgeRecords", consequence: "irreversible_deletion" },
  { domain: "deletion", name: "deleteExternalResource", consequence: "irreversible_deletion" },

  // --- Credentials / security (never agent-operated) ---
  { domain: "credentials", name: "rotateCredential", consequence: "production_capability" },
  { domain: "credentials", name: "grantCredentialAccess", consequence: "permanent_deny" },
  { domain: "security", name: "modifyPermissions", consequence: "permanent_deny" },
  { domain: "security", name: "selfApprove", consequence: "permanent_deny" },
  { domain: "security", name: "approveAction", consequence: "permanent_deny" },

  // --- Configuration / capability ---
  { domain: "configuration", name: "readConfig", consequence: "read" },
  { domain: "configuration", name: "mutatePolicy", consequence: "permanent_deny" },
  { domain: "configuration", name: "applyLiveConfig", consequence: "production_capability" },
  { domain: "plugins", name: "installPlugin", consequence: "production_capability" },
  { domain: "plugins", name: "enablePlugin", consequence: "production_capability" },
  { domain: "plugins", name: "removePlugin", consequence: "production_capability" },

  // --- Skills ---
  { domain: "skills", name: "proposeSkill", consequence: "internal_reversible_write" },
  { domain: "skills", name: "applySkill", consequence: "production_capability" },
  { domain: "skills", name: "mutateApprovedSkill", consequence: "permanent_deny" },

  // --- Automations ---
  { domain: "automations", name: "readAutomations", consequence: "read" },
  { domain: "automations", name: "createAutomation", consequence: "production_capability" },
  { domain: "automations", name: "modifyAutomation", consequence: "production_capability" },
  { domain: "automations", name: "runAutomation", consequence: "fixed_external_commitment" },
] as const);

const INDEX: ReadonlyMap<string, ActionDef> = new Map(
  ACTION_CATALOG.map((a) => [`${a.domain}.${a.name}`, a] as const),
);

/** Operator-owned pre-authorisation envelope. */
export interface PreAuthorisation {
  /** Actions covered, e.g. ["messaging.sendPrivateMessage"]. */
  actions: string[];
  /** Maximum number of uses. */
  quantityLimit: number;
  /** Uses already consumed. */
  used: number;
  /** Window the quantity applies to. */
  window: { start: string; end: string }; // ISO timestamps
  /** Allowed destinations (recipients/URLs/repos). Empty = none. */
  destinations: string[];
  /** Envelope expiry. */
  expiresAt: string;
}

/** Operator-owned configuration — never model-supplied. */
export interface PolicyConfig {
  envelopes: PreAuthorisation[];
  /** Hard ceiling on serialised payload size in bytes. */
  maxPayloadBytes: number;
  /** Current time (injectable for tests). */
  now?: () => string;
}

export const DEFAULT_POLICY_CONFIG: PolicyConfig = {
  envelopes: [],
  maxPayloadBytes: 16 * 1024,
  now: () => new Date().toISOString(),
};

/** Model-supplied fields that must never influence the decision. */
const FORBIDDEN_MODEL_FIELDS = ["risk", "riskClass", "risk_class", "approved", "decision", "policy", "override"];

/** Strips model-supplied policy fields; returns them if any were present. */
export function stripModelSuppliedPolicy(
  payload: Record<string, unknown>,
): { clean: Record<string, unknown>; stripped: string[] } {
  const stripped: string[] = [];
  const clean: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(payload)) {
    if (FORBIDDEN_MODEL_FIELDS.includes(k.toLowerCase())) {
      stripped.push(k);
    } else {
      clean[k] = v;
    }
  }
  return { clean, stripped };
}

function inWindow(iso: string, start: string, end: string): boolean {
  return start <= iso && iso <= end;
}

export function evaluateAction(
  action: string,
  payload: unknown,
  config: PolicyConfig = DEFAULT_POLICY_CONFIG,
): PolicyResult {
  const now = (config.now ?? DEFAULT_POLICY_CONFIG.now!)();

  // Unknown actions fail closed.
  const def = INDEX.get(action);
  if (!def) {
    return { decision: "DENY", reason: `unknown_action:${action}` };
  }

  // Catalog-level permanent denials.
  if (def.consequence === "permanent_deny") {
    return { decision: "DENY", reason: `permanent_deny:${action}` };
  }

  // Payload must be an object.
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    return { decision: "DENY", reason: "invalid_payload:not_an_object" };
  }

  // Oversized actions fail closed.
  const size = JSON.stringify(payload).length;
  if (size > config.maxPayloadBytes) {
    return { decision: "DENY", reason: `oversized_payload:${size}>${config.maxPayloadBytes}` };
  }

  // Strip and note model-supplied policy fields — they never grant anything.
  const { stripped } = stripModelSuppliedPolicy(payload as Record<string, unknown>);

  switch (def.consequence) {
    case "read":
    case "internal_reversible_write":
      return {
        decision: "ALLOW",
        reason: `auto:${def.consequence}` + (stripped.length ? `;ignored_model_fields:${stripped.join(",")}` : ""),
      };

    case "private_external_write": {
      const env = findEnvelope(action, config, now);
      if (!env) {
        return { decision: "REQUIRE_APPROVAL", reason: "no_valid_envelope" };
      }
      const dest = typeof (payload as Record<string, unknown>).destination === "string"
        ? (payload as Record<string, unknown>).destination as string
        : "";
      if (!env.destinations.includes(dest)) {
        return { decision: "REQUIRE_APPROVAL", reason: `destination_not_preauthorised:${dest || "(none)"}` };
      }
      return { decision: "ALLOW", reason: `envelope:${env.actions[0]}` };
    }

    case "public_communication":
    case "money":
    case "irreversible_deletion":
    case "fixed_external_commitment":
    case "production_capability":
      return { decision: "REQUIRE_APPROVAL", reason: `gated:${def.consequence}` };

    default:
      // Unknown consequence — fail closed.
      return { decision: "DENY", reason: `unknown_consequence:${String(def.consequence)}` };
  }
}

function findEnvelope(action: string, config: PolicyConfig, now: string): PreAuthorisation | null {
  for (const env of config.envelopes) {
    if (!env.actions.includes(action)) continue;
    if (env.expiresAt <= now) continue;
    if (!inWindow(now, env.window.start, env.window.end)) continue;
    if (env.used >= env.quantityLimit) continue;
    return env;
  }
  return null;
}

/**
 * Record an envelope use after an allowed action executes.
 * Returns false if the envelope is exhausted (caller must not have executed).
 */
export function consumeEnvelope(env: PreAuthorisation): boolean {
  if (env.used >= env.quantityLimit) return false;
  env.used += 1;
  return true;
}

/**
 * Detect execution of an altered approved payload: the approved hash must
 * match the payload about to run. Any mismatch is a permanent deny.
 */
export function verifyApprovedPayload(
  approvedHash: string,
  payload: unknown,
  hashFn: (p: unknown) => string,
): PolicyResult {
  if (hashFn(payload) !== approvedHash) {
    return { decision: "DENY", reason: "altered_approved_payload" };
  }
  return { decision: "ALLOW", reason: "approved_payload_match" };
}
