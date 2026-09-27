/**
 * Policy enforcement — Batch 9 (§Skill Governance).
 *
 * Core enforcement rules:
 *   1. No auto-update of approved skills from upstream
 *   2. Mutation outside governed flow rejected
 *   3. Only approvedRevision can be activated
 *   4. Self-learning proposals create proposal records, never direct apply
 */
import type { SkillManifest, ProposalRecord } from "./manifest.ts";
import { createProposal } from "./quarantine.ts";

/**
 * Attempt to auto-update an approved skill from upstream.
 * Returns false — auto-update is always rejected by policy.
 */
export function tryAutoUpdate(manifest: SkillManifest): boolean {
  if (manifest.review.status === "approved") {
    // Policy violation: approved skills must not auto-update from upstream
    return false;
  }
  return false;
}

/**
 * Attempt a direct mutation on an approved skill.
 * Returns false — mutation outside governed flow is always rejected.
 */
export function tryDirectMutation(manifest: SkillManifest, mutation: Record<string, unknown>): boolean {
  if (manifest.review.status === "approved") {
    // Policy violation: direct mutation of approved production skill
    return false;
  }
  return false;
}

/**
 * Activate a skill by approved revision.
 * Only works if the manifest is approved AND the provided revision matches approvedRevision.
 */
export function activateByRevision(manifest: SkillManifest, revision: string): boolean {
  if (
    manifest.review.status !== "approved" ||
    manifest.activation.approvedRevision !== revision
  ) {
    return false;
  }
  return true;
}

/**
 * Apply a self-learning proposal — creates a proposal record, never direct apply.
 * Returns the proposal record. The caller must human-review before activation.
 */
export function proposeSkillUpdate(skillId: string, proposedBy: string, reason: string): ProposalRecord {
  // Policy: self-learning proposals create proposal records, never direct apply
  return createProposal(skillId, proposedBy, reason);
}

/**
 * Verify that a mutation is within the governed flow.
 * A mutation is allowed only if the skill is quarantined (not approved) and
 * the mutation goes through the intake→review→activation pipeline.
 */
export function isMutationAllowed(manifest: SkillManifest): boolean {
  return manifest.review.status === "quarantined";
}

/**
 * Verify that an approved revision is valid for activation.
 */
export function validateActivation(manifest: SkillManifest): { allowed: boolean; reason: string } {
  if (manifest.review.status !== "approved") {
    return { allowed: false, reason: "skill is not approved" };
  }
  if (!manifest.activation.approvedRevision) {
    return { allowed: false, reason: "no approved revision set" };
  }
  if (!manifest.activation.enabled) {
    return { allowed: false, reason: "activation not enabled" };
  }
  return { allowed: true, reason: "activation valid" };
}
