// skill-integrity — skill revision hash check.
// Extends skill-governance policy types via import, not rewrite.

import type { SkillManifest, ProposalRecord } from '../../skill-governance/src/manifest.ts';
import { activateByRevision } from '../../skill-governance/src/policy.ts';
import { TamperDetectedError } from './faults.ts';

export interface RecordedHashes {
  [skillId: string]: { revision: string; hash: string };
}

export interface SkillProposal {
  skillId: string;
  revision: string;
  hash: string;
  approved: boolean;
}

export function verifySkillRevision(
  proposal: SkillProposal,
  recordedHashes: RecordedHashes,
): { activated: boolean; reason: string } {
  // Reject invalid/unapproved revision
  if (!proposal.approved) {
    return { activated: false, reason: `Skill ${proposal.skillId} revision ${proposal.revision} not approved — rejected` };
  }
  // Detect directory tampering (hash mismatch)
  const recorded = recordedHashes[proposal.skillId];
  if (recorded && recorded.hash !== proposal.hash) {
    throw new TamperDetectedError(
      `Hash mismatch for skill ${proposal.skillId}: expected ${recorded.hash}, got ${proposal.hash}`
    );
  }
  // Verify against policy activation
  // Use activateByRevision logic: only approved revision can activate
  // We check if the proposal revision matches the recorded approved revision
  if (recorded && recorded.revision !== proposal.revision) {
    return { activated: false, reason: `Revision ${proposal.revision} does not match approved revision ${recorded.revision}` };
  }
  return { activated: true, reason: `Skill ${proposal.skillId} revision ${proposal.revision} verified and activated` };
}
