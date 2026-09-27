/**
 * Spawn policy — Batch 7 (§5.4 delegation rules, T7.5–T7.7).
 *
 * Codifies the Chief-of-Staff delegation constraints as checkable policy so
 * tests can prove them, and so the runtime layer can apply them consistently.
 */

export const SPAWN_ALLOWED_AGENTS = ["rhythm", "growth", "scholar"] as const;
export type SpawnAgentId = (typeof SPAWN_ALLOWED_AGENTS)[number];

export const SPAWN_POLICY = {
  requireExplicitAgentId: true, // T7.5: omitted agentId is rejected
  allowlist: SPAWN_ALLOWED_AGENTS, // T7.6: unknown/unapproved agents rejected
  maxSpawnDepth: 1, // T7.7: children can never spawn children
  maxChildrenPerAgent: 3, // §Batch7 work item 4: max three children per session
  maxConcurrent: 3, // §Batch7 work item 4: max three concurrent runs
} as const;

export type SpawnRejection =
  | { ok: true; agentId: SpawnAgentId }
  | { ok: false; code: "MISSING_AGENT_ID" | "DISALLOWED_AGENT" | "MAX_DEPTH" | "MAX_CHILDREN" | "MAX_CONCURRENT"; message: string };

/** Validate a spawn request against the policy (pure, deterministic). */
export function checkSpawn(input: {
  agentId?: string | null;
  depth?: number; // caller's current depth: 0 = top-level
  activeChildren?: number;
  runningNow?: number;
}): SpawnRejection {
  if (SPAWN_POLICY.requireExplicitAgentId && (input.agentId === undefined || input.agentId === null || input.agentId === "")) {
    return { ok: false, code: "MISSING_AGENT_ID", message: "sessions_spawn requires an explicit agentId (rhythm, growth or scholar)" };
  }
  const id = input.agentId as string;
  if (!(SPAWN_POLICY.allowlist as readonly string[]).includes(id)) {
    return { ok: false, code: "DISALLOWED_AGENT", message: `agent "${id}" is not on the spawn allowlist (rhythm, growth, scholar)` };
  }
  const depth = input.depth ?? 0;
  if (depth + 1 > SPAWN_POLICY.maxSpawnDepth) {
    return { ok: false, code: "MAX_DEPTH", message: "spawn depth 1 is the maximum: children can never spawn children" };
  }
  if ((input.activeChildren ?? 0) >= SPAWN_POLICY.maxChildrenPerAgent) {
    return { ok: false, code: "MAX_CHILDREN", message: `maximum ${SPAWN_POLICY.maxChildrenPerAgent} children per session` };
  }
  if ((input.runningNow ?? 0) >= SPAWN_POLICY.maxConcurrent) {
    return { ok: false, code: "MAX_CONCURRENT", message: `maximum ${SPAWN_POLICY.maxConcurrent} concurrent runs` };
  }
  return { ok: true, agentId: id as SpawnAgentId };
}
