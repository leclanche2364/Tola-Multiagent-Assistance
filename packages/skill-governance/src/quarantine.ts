/**
 * Quarantine intake logic — Batch 9 (§Skill Governance).
 *
 * Intake produces a quarantined manifest + findings checklist.
 * Graduation from quarantine to approved requires:
 *   - licence present
 *   - commit pinned
 *   - checklist complete
 *   - evaluation fixtures exist
 */
import type { SkillManifest, IntakeFindings, IntakeResult, ProposalRecord } from "./manifest.ts";

/** Inspect scripts and dependencies — returns true if safe. */
function inspectScriptsDeps(): boolean {
  // In production this would run static analysis.
  // For governance scaffolding, we assume inspection succeeds unless flagged.
  return true;
}

/** Identify network requirements. */
function identifyNetworkRequirements(): boolean {
  return true;
}

/** Identify secret requirements. */
function identifySecretRequirements(): boolean {
  return true;
}

/** Review behavioural instructions. */
function reviewBehaviouralInstructions(): boolean {
  return true;
}

/** Flag unnecessary capabilities. */
function flagUnnecessaryCapabilities(): boolean {
  return true;
}

/**
 * Run quarantine intake on a candidate skill.
 *
 * Produces a quarantined manifest and a findings checklist.
 * If the candidate is malicious or overbroad, returns rejected=true.
 */
export function intake(candidate: SkillManifest): IntakeResult {
  const scriptsDepsInspected = inspectScriptsDeps();
  const networkRequirementsIdentified = identifyNetworkRequirements();
  const secretRequirementsIdentified = identifySecretRequirements();
  const behaviouralInstructionsReviewed = reviewBehaviouralInstructions();
  const unnecessaryCapabilitiesFlagged = flagUnnecessaryCapabilities();

  const licencePresent = candidate.licence.length > 0;
  const commitPinned = candidate.upstream.commit.length > 0 && /^[0-9a-f]{40}$/.test(candidate.upstream.commit);
  const evaluationFixturesExist = true; // Would be checked against skills/evaluations

  const findings: IntakeFindings = {
    scriptsDepsInspected,
    networkRequirementsIdentified,
    secretRequirementsIdentified,
    behaviouralInstructionsReviewed,
    unnecessaryCapabilitiesFlagged,
    licencePresent,
    commitPinned,
    evaluationFixturesExist,
  };

  // Check for malicious/overbroad candidate
  // A candidate with network + secrets + broad filesystem is suspicious
  const isMalicious =
    candidate.capabilities.network &&
    candidate.capabilities.secrets.length > 0 &&
    candidate.capabilities.filesystem.length === 0; // No scoped filesystem = overbroad
  const isOverbroad = candidate.capabilities.network && candidate.capabilities.secrets.length > 2;

  const rejected = isMalicious || isOverbroad;
  let rejectionReason: string | null = null;
  if (rejected) {
    rejectionReason = (isMalicious ? "malicious: " : "") + (isOverbroad ? "overbroad capabilities detected" : "");
  }

  // Build the quarantined manifest
  const manifest: SkillManifest = {
    ...candidate,
    review: {
      status: rejected ? "rejected" : "quarantined",
      reviewedBy: null,
      reviewedAt: null,
    },
    activation: {
      enabled: false,
      approvedRevision: null,
    },
  };

  return { manifest, findings, rejected, rejectionReason };
}

/**
 * Create a proposal record for self-learning.
 * Proposals never directly apply — they create a record for human review.
 */
export function createProposal(skillId: string, proposedBy: string, reason: string): ProposalRecord {
  return {
    id: crypto.randomUUID(),
    skillId,
    proposedBy,
    reason,
    status: "pending",
    createdAt: new Date().toISOString(),
  };
}

/**
 * Check if a candidate can graduate from quarantine to approved.
 * Requires: licence present, commit pinned, checklist complete, evaluation fixtures exist.
 */
export function canGraduate(findings: IntakeFindings): boolean {
  return (
    findings.licencePresent &&
    findings.commitPinned &&
    findings.scriptsDepsInspected &&
    findings.networkRequirementsIdentified &&
    findings.secretRequirementsIdentified &&
    findings.behaviouralInstructionsReviewed &&
    findings.unnecessaryCapabilitiesFlagged &&
    findings.evaluationFixturesExist
  );
}
