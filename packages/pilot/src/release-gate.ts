/**
 * Release gate — Batch 16 spec §13.
 *
 * V1 can be frozen as production only if all critical gates pass
 * AND there is no unresolved S0/S1 defect (security, duplication,
 * skill-governance, or state-consistency).
 *
 * Pure function — no side effects, no I/O.
 */

import type { Severity } from "./weekly-rollup.js";

/** Result of a single critical gate check */
export type GateResult = {
  /** Gate identifier */
  gateId: string;
  /** Whether this gate passed */
  passed: boolean;
  /** Optional detail message */
  detail?: string;
};

/** A defect report */
export type Defect = {
  /** Defect identifier */
  defectId: string;
  /** Severity level per spec §13 */
  severity: Severity;
  /** Category: security, duplication, skill-governance, state-consistency */
  category: string;
  /** Whether this defect is resolved */
  resolved: boolean;
  /** Optional description */
  description?: string;
};

/** Outcome of the release gate check */
export type GateOutcome = {
  /** Can V1 be frozen as production? */
  canFreezeV1: boolean;
  /** Which critical gates failed (if any) */
  failedGates: GateResult[];
  /** Unresolved high-severity defects (S0 or S1) */
  unresolvedHighSeverityDefects: Defect[];
  /** Human-readable summary */
  summary: string;
};

/**
 * Check whether V1 can be frozen as production.
 *
 * Rules (spec §13):
 * - All critical gates must pass.
 * - No unresolved S0 or S1 defect may exist.
 * - S2 and S3 defects do not block freezing.
 *
 * @param params.criticalGates array of gate results
 * @param params.defects array of defect reports
 * @returns GateOutcome with canFreezeV1 and blocking details
 */
export function checkReleaseGate({
  criticalGates,
  defects,
}: {
  criticalGates: GateResult[];
  defects: Defect[];
}): GateOutcome {
  const failedGates = criticalGates.filter((g) => !g.passed);

  const unresolvedHighSeverityDefects = defects.filter(
    (d) => (d.severity === "S0" || d.severity === "S1") && !d.resolved,
  );

  const canFreezeV1 = failedGates.length === 0 && unresolvedHighSeverityDefects.length === 0;

  const parts: string[] = [];
  if (canFreezeV1) {
    parts.push("All critical gates pass and no unresolved S0/S1 defects.");
  } else {
    if (failedGates.length > 0) {
      parts.push(`Failed critical gates: ${failedGates.map((g) => g.gateId).join(", ")}`);
    }
    if (unresolvedHighSeverityDefects.length > 0) {
      parts.push(
        `Unresolved S0/S1 defects: ${unresolvedHighSeverityDefects.map((d) => d.defectId).join(", ")}`,
      );
    }
  }

  return {
    canFreezeV1,
    failedGates,
    unresolvedHighSeverityDefects,
    summary: parts.join(" "),
  };
}
