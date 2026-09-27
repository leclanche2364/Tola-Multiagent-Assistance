/**
 * SkillManifest schema — Batch 9 (§Skill Governance).
 *
 * Every skill in the system is described by a manifest that captures
 * identity, provenance, capabilities, review state, and activation state.
 */
export interface SkillManifest {
  /** Unique identifier for the skill. */
  id: string;
  /** Human-readable name. */
  name: string;
  /** Semantic version string. */
  version: string;
  /** Upstream source metadata — exact commit pinned. */
  upstream: {
    repo: string;
    commit: string;
    path: string;
  };
  /** SPDX licence identifier (required). */
  licence: string;
  /** Declared capabilities — explicit and justified. */
  capabilities: {
    network: boolean;
    secrets: string[];
    filesystem: string[];
  };
  /** Review state — governs whether the skill can be activated. */
  review: {
    status: "quarantined" | "approved" | "rejected";
    reviewedBy: string | null;
    reviewedAt: string | null;
  };
  /** Activation state — only approvedRevision can be active. */
  activation: {
    enabled: boolean;
    approvedRevision: string | null;
  };
}

/** Findings checklist produced during quarantine intake. */
export interface IntakeFindings {
  scriptsDepsInspected: boolean;
  networkRequirementsIdentified: boolean;
  secretRequirementsIdentified: boolean;
  behaviouralInstructionsReviewed: boolean;
  unnecessaryCapabilitiesFlagged: boolean;
  licencePresent: boolean;
  commitPinned: boolean;
  evaluationFixturesExist: boolean;
}

/** Proposal record — self-learning proposals create these, never direct apply. */
export interface ProposalRecord {
  id: string;
  skillId: string;
  proposedBy: string;
  reason: string;
  status: "pending" | "rejected";
  createdAt: string;
}

/** Result of a quarantine intake. */
export interface IntakeResult {
  manifest: SkillManifest;
  findings: IntakeFindings;
  rejected: boolean;
  rejectionReason: string | null;
}

/** Minimal fixture for test scaffolding. */
export function makeManifest(overrides: Partial<SkillManifest> = {}): SkillManifest {
  const base: SkillManifest = {
    id: "00000000-0000-0000-0000-000000000000",
    name: "unnamed-skill",
    version: "0.0.0",
    upstream: { repo: "", commit: "", path: "" },
    licence: "",
    capabilities: { network: false, secrets: [], filesystem: [] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  };
  return { ...base, ...overrides };
}
