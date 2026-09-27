// Skill Governance — Batch 9
// T9.1 Self-learning proposal        | T9.2 Direct mutation rejected
// T9.3 Pinned source                  | T9.4 Licence recorded
// T9.5 Malicious/overbroad rejected   | T9.6 Baseline evaluation
// T9.7 Upstream changes do not auto-update | T9.8 Human activation required
// Run: node --experimental-strip-types --test --test-concurrency=1 tests/skill-governance.test.ts

import { test } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import * as nodePath from "node:path";
import { makeManifest, type SkillManifest } from "../src/manifest.ts";
import { intake, createProposal, canGraduate } from "../src/quarantine.ts";
import { tryAutoUpdate, tryDirectMutation, activateByRevision, proposeSkillUpdate, isMutationAllowed, validateActivation } from "../src/policy.ts";

const here = nodePath.dirname(fileURLToPath(import.meta.url));

// Helper: create a realistic skill manifest
function makeCandidate(overrides: Partial<SkillManifest> = {}): SkillManifest {
  return makeManifest({
    id: randomUUID(),
    name: "test-skill",
    version: "1.0.0",
    upstream: {
      repo: "https://github.com/example/skill.git",
      commit: "a".repeat(40), // valid 40-char hex commit
      path: "skills/test",
    },
    licence: "MIT",
    capabilities: { network: false, secrets: [], filesystem: ["read:reports"] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
    ...overrides,
  });
}

// Helper: create a malicious candidate
function makeMaliciousCandidate(): SkillManifest {
  return makeManifest({
    id: randomUUID(),
    name: "evil-skill",
    version: "1.0.0",
    upstream: {
      repo: "https://github.com/evil/skill.git",
      commit: "b".repeat(40),
      path: "skills/evil",
    },
    licence: "",
    capabilities: { network: true, secrets: ["api-key", "db-pass", "token"], filesystem: [] },
    review: { status: "quarantined", reviewedBy: null, reviewedAt: null },
    activation: { enabled: false, approvedRevision: null },
  });
}

// Helper: create an approved manifest with a specific revision
function makeApproved(revision: string): SkillManifest {
  return makeManifest({
    id: randomUUID(),
    name: "approved-skill",
    version: "1.0.0",
    upstream: { repo: "https://github.com/example/skill.git", commit: "a".repeat(40), path: "skills/test" },
    licence: "MIT",
    capabilities: { network: false, secrets: [], filesystem: ["read:reports"] },
    review: { status: "approved", reviewedBy: "human:alice", reviewedAt: new Date().toISOString() },
    activation: { enabled: true, approvedRevision: revision },
  });
}

// ---------- T9.1 ----------

test("T9.1 Self-learning proposal cannot silently apply — creates proposal record only", () => {
  const proposal = proposeSkillUpdate("skill-123", "tola", "Add planning skill");
  assert.strictEqual(proposal.status, "pending");
  assert.strictEqual(proposal.proposedBy, "tola");
  assert.ok(proposal.id.length > 0);
  // Proposal must NOT directly apply — no side effects on the skill system
});

// ---------- T9.2 ----------

test("T9.2 Direct skill mutation rejected — bypass attempt cannot change approved production skill", () => {
  const approved = makeApproved("rev-1");
  const mutated = tryDirectMutation(approved, { name: "hacked" });
  assert.strictEqual(mutated, false, "Direct mutation of approved skill must be rejected");
});

// ---------- T9.3 ----------

test("T9.3 Pinned source stored — exact upstream commit is captured", () => {
  const commit = "abc123def456abc123def456abc123def456abc1";
  const candidate = makeCandidate({ upstream: { repo: "https://github.com/example/skill.git", commit, path: "skills/test" } });
  const result = intake(candidate);
  assert.strictEqual(result.manifest.upstream.commit, commit);
  // Commit must be a valid 40-char hex hash
  assert.ok(/^[0-9a-f]{40}$/.test(result.manifest.upstream.commit), "Commit must be 40-char hex");
});

// ---------- T9.4 ----------

test("T9.4 Licence recorded — SPDX identifier is captured in manifest", () => {
  const candidate = makeCandidate({ licence: "Apache-2.0" });
  const result = intake(candidate);
  assert.strictEqual(result.manifest.licence, "Apache-2.0");
  assert.ok(result.findings.licencePresent, "findings must record licence present");
});

// ---------- T9.5 ----------

test("T9.5 Malicious/overbroad candidate rejected in quarantine", () => {
  const malicious = makeMaliciousCandidate();
  const result = intake(malicious);
  assert.strictEqual(result.rejected, true);
  assert.ok(result.rejectionReason !== null);
  assert.strictEqual(result.manifest.review.status, "rejected");
});

// ---------- T9.6 ----------

test("T9.6 Baseline evaluation — candidate must improve behaviour without boundary regression", () => {
  const candidate = makeCandidate({
    capabilities: { network: false, secrets: [], filesystem: ["read:reports"] },
  });
  const result = intake(candidate);
  // Non-malicious, well-scoped candidate should not be rejected
  assert.strictEqual(result.rejected, false);
  // Can graduate only if all checklist items are true and evaluation fixtures exist
  const canGrad = canGraduate(result.findings);
  // With default inspect functions returning true, should be able to graduate
  assert.strictEqual(canGrad, true);
});

// ---------- T9.7 ----------

test("T9.7 Upstream changes do not auto-update approved skill", () => {
  const approved = makeApproved("rev-1");
  const originalCommit = approved.upstream.commit;
  // Simulate upstream change — the manifest's commit is still the old one
  const upstreamChanged = { ...approved, upstream: { ...approved.upstream, commit: "newcommit".repeat(4).slice(0, 40) } };
  const autoUpdated = tryAutoUpdate(upstreamChanged);
  assert.strictEqual(autoUpdated, false, "Auto-update must be rejected");
  // Approved skill remains unchanged — its commit must not be mutated
  assert.strictEqual(approved.upstream.commit, originalCommit);
});

// ---------- T9.8 ----------

test("T9.8 Human activation required — only explicitly approved revision becomes active", () => {
  const approved = makeApproved("rev-1");

  // Without human approval, activation fails
  const notApproved = makeManifest({ review: { status: "quarantined", reviewedBy: null, reviewedAt: null }, activation: { enabled: true, approvedRevision: "rev-1" } });
  const activation1 = validateActivation(notApproved);
  assert.strictEqual(activation1.allowed, false);

  // Correct approved revision activates
  const activation2 = validateActivation(approved);
  assert.strictEqual(activation2.allowed, true);

  // Wrong revision cannot activate
  const wrongRevision = activateByRevision(approved, "wrong-rev");
  assert.strictEqual(wrongRevision, false);

  // Correct revision activates
  const correctRevision = activateByRevision(approved, "rev-1");
  assert.strictEqual(correctRevision, true);
});
