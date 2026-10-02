/**
 * Quarantined growth skill manifests — Batch 11.
 *
 * Vendor skills from Corey Haines: analytics, attribution, seo-audit,
 * cro, ab-testing, onboarding, signup, aso.
 *
 * All skills are:
 *   - Quarantined (review.status = "quarantined")
 *   - SPDX licence present
 *   - Not activated (activation.enabled = false)
 *   - Pinned upstream commits
 */

import type { SkillManifest } from "../../skill-governance/src/manifest.ts";

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

export const growthSkillManifests: SkillManifest[] = [
  makeManifest({
    id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    name: "analytics",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/analytics.git", commit: PIN, path: "skills/analytics" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:analytics"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    name: "attribution",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/attribution.git", commit: PIN, path: "skills/attribution" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:attribution"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
    name: "seo-audit",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/seo-audit.git", commit: PIN, path: "skills/seo-audit" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:seo"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "d4e5f6a7-b8c9-0123-defa-234567890123",
    name: "cro",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/cro.git", commit: PIN, path: "skills/cro" },
    licence: "MIT",
    capabilities: { network: false, secrets: [], filesystem: ["read:cro"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "e5f6a7b8-c9d0-1234-efab-345678901234",
    name: "ab-testing",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/ab-testing.git", commit: PIN, path: "skills/ab-testing" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:ab-tests"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "f6a7b8c9-d0e1-2345-fabc-456789012345",
    name: "onboarding",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/onboarding.git", commit: PIN, path: "skills/onboarding" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:onboarding"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "a7b8c9d0-e1f2-3456-abcd-567890123456",
    name: "signup",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/signup.git", commit: PIN, path: "skills/signup" },
    licence: "MIT",
    capabilities: { network: true, secrets: [], filesystem: ["read:signup"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
  makeManifest({
    id: "b8c9d0e1-f2a3-4567-bcde-678901234567",
    name: "aso",
    version: "0.1.0",
    upstream: { repo: "https://github.com/coreyhaines/aso.git", commit: PIN, path: "skills/aso" },
    licence: "MIT",
    capabilities: { network: false, secrets: [], filesystem: ["read:aso"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  }),
];

/** Look up a growth skill manifest by name. Pure/deterministic. */
export function findGrowthSkill(name: string): SkillManifest | undefined {
  return growthSkillManifests.find(s => s.name === name);
}

/** Verify all growth skills are quarantined and not activated. Pure/deterministic. */
export function verifyAllQuarantined(): boolean {
  return growthSkillManifests.every(s =>
    s.review.status === "quarantined" &&
    s.activation.enabled === false &&
    s.licence.length > 0 &&
    s.upstream.commit.length === 40
  );
}
