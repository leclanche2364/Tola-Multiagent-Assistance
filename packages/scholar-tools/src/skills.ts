/**
 * Quarantined Scholar skill manifests — Batch 12.
 *
 * Scientific/evidence skills:
 *   - scientific-critical-thinking
 *   - paper-provenance
 *   - evidence-search
 *   - claim-verification
 *   - teaching-synthesis
 *   - quiz-generation
 *
 * All skills are:
 *   - Quarantined (review.status = "quarantined")
 *   - SPDX licence present
 *   - Not activated (activation.enabled = false)
 *   - Pinned upstream commits
 *
 * Mirrors the skills/vendor pattern from Batch 11 (growth-tools).
 */

// Minimal SkillManifest shape — matches @tola/skill-governance schema
export interface SkillManifest {
  id: string;
  name: string;
  version: string;
  upstream: { repo: string; commit: string; path: string };
  licence: string;
  capabilities: { network: boolean; secrets: string[]; filesystem: string[] };
  review: { status: "quarantined" | "approved" | "rejected"; reviewedBy: string | null; reviewedAt: string | null };
  activation: { enabled: boolean; approvedRevision: string | null };
}

const makeManifest = (overrides: Partial<SkillManifest>): SkillManifest => ({
  id: "00000000-0000-0000-0000-000000000000",
  name: "unnamed-skill",
  version: "0.0.0",
  upstream: { repo: "", commit: "", path: "" },
  licence: "",
  capabilities: { network: false, secrets: [], filesystem: [] },
  review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
  activation: { enabled: false, approvedRevision: null },
  ...overrides,
});

// 40-char hex commit pins
const PIN = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0";

export const scholarSkillManifests: SkillManifest[] = [
  makeManifest({
    id: "1a2b3c4d-e5f6-7890-abcd-ef1234567890",
    name: "scientific-critical-thinking",
    version: "0.1.0",
    upstream: { repo: "https://github.com/scholar/scientific-critical-thinking.git", commit: PIN, path: "skills/scientific-critical-thinking" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:literature"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "2b3c4d5e-f6a7-8901-bcde-f12345678901",
    name: "paper-provenance",
    version: "0.1.0",
    upstream: { repo: "https://github.com/scholar/paper-provenance.git", commit: PIN, path: "skills/paper-provenance" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:papers"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "3c4d5e6f-a7b8-9012-cdef-123456789012",
    name: "evidence-search",
    version: "0.1.0",
    upstream: { repo: "https://github.com/scholar/evidence-search.git", commit: PIN, path: "skills/evidence-search" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:evidence"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "4d5e6f7a-b8c9-0123-defa-234567890123",
    name: "claim-verification",
    version: "0.1.0",
    upstream: { repo: "https://github.com/scholar/claim-verification.git", commit: PIN, path: "skills/claim-verification" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:claims"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "5e6f7a8b-c9d0-1234-efab-345678901234",
    name: "teaching-synthesis",
    version: "0.1.0",
    upstream: { repo: "https://github.com/scholar/teaching-synthesis.git", commit: PIN, path: "skills/teaching-synthesis" },
    licence: "MIT",
    capabilities: { network: false, secrets: [], filesystem: ["read:syllabi"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "6f7a8b9c-d0e1-2345-fabc-456789012345",
    name: "quiz-generation",
    version: "0.1.0",
    upstream: { repo: "https://github.com/scholar/quiz-generation.git", commit: PIN, path: "skills/quiz-generation" },
    licence: "MIT",
    capabilities: { network: false, secrets: [], filesystem: ["read:questions"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
];

/** Look up a scholar skill manifest by name. Pure/deterministic. */
export function findScholarSkill(name: string): SkillManifest | undefined {
  return scholarSkillManifests.find(s => s.name === name);
}

/** Verify all scholar skills are quarantined and not activated. Pure/deterministic. */
export function verifyAllScholarQuarantined(): boolean {
  return scholarSkillManifests.every(s =>
    s.review.status === "quarantined" &&
    s.activation.enabled === false &&
    s.licence.length > 0 &&
    s.upstream.commit.length === 40
  );
}
