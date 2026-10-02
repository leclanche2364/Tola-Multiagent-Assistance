// Automation manifest loader and schema validation — Batch 09.
// Reads docs/current-state/automations.json and validates it against the
// native OpenClaw automation manifest schema.

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

// ---------------------------------------------------------------------------
// Typed manifest schema (mirrors docs/current-state/automations.json)
// ---------------------------------------------------------------------------

export type CronSchedule = {
  kind: "cron";
  expr: string;
  tz?: string;
};

export type EverySchedule = {
  kind: "every";
  everyMs: number;
  anchorMs?: number;
};

export type AtSchedule = {
  kind: "at";
  at: string;
};

export type Schedule = CronSchedule | EverySchedule | AtSchedule;

export type Delivery = {
  mode: "announce" | "none";
  channel: string;
  to: string;
  accountId?: string;
};

export type AutomationEntry = {
  stableName: string;
  owner: string;
  schedule: Schedule;
  mode: "isolated" | "command";
  prompt: string;
  timeoutMs: number;
  tools: string[];
  riskCeiling: string;
  delivery: Delivery;
  quietPolicy: "always" | "notify-on-change" | "notify-on-failure" | "notify-on-drift";
  failureDestination: string;
};

export interface AutomationManifest {
  $schema: string;
  version: string;
  updatedAt: string;
  timezone: string;
  automations: AutomationEntry[];
}

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

const VALID_RISK_CEILINGS = new Set(["C1", "C2", "C3", "C4"]);
const VALID_MODES = new Set(["isolated", "command"]);
const VALID_QUIET_POLICIES = new Set([
  "always",
  "notify-on-change",
  "notify-on-failure",
  "notify-on-drift",
]);

function validateEntry(e: AutomationEntry, index: number): string[] {
  const errors: string[] = [];
  if (!e.stableName) errors.push(`[${index}] missing stableName`);
  if (!e.owner) errors.push(`[${index}] missing owner`);
  if (!e.schedule) errors.push(`[${index}] missing schedule`);
  if (!VALID_MODES.has(e.mode)) errors.push(`[${index}] invalid mode "${e.mode}"`);
  if (!e.prompt) errors.push(`[${index}] missing prompt`);
  if (e.timeoutMs <= 0) errors.push(`[${index}] timeoutMs must be positive`);
  if (!Array.isArray(e.tools) || e.tools.length === 0)
    errors.push(`[${index}] tools must be a non-empty array`);
  if (!VALID_RISK_CEILINGS.has(e.riskCeiling))
    errors.push(`[${index}] invalid riskCeiling "${e.riskCeiling}"`);
  if (!e.delivery) errors.push(`[${index}] missing delivery`);
  if (!VALID_QUIET_POLICIES.has(e.quietPolicy))
    errors.push(`[${index}] invalid quietPolicy "${e.quietPolicy}"`);
  if (!e.failureDestination) errors.push(`[${index}] missing failureDestination`);
  const s = e.schedule;
  if (s.kind === "cron" && !s.expr) errors.push(`[${index}] cron schedule missing expr`);
  if (s.kind === "every" && s.everyMs <= 0)
    errors.push(`[${index}] every schedule everyMs must be positive`);
  if (s.kind === "at" && !s.at) errors.push(`[${index}] at schedule missing at`);
  return errors;
}

// ---------------------------------------------------------------------------
// Loader
// ---------------------------------------------------------------------------

const MANIFEST_PATH = fileURLToPath(
  new URL("../../../docs/current-state/automations.json", import.meta.url)
);

export async function loadManifest(path?: string): Promise<AutomationManifest> {
  const raw = await readFile(path ?? MANIFEST_PATH, "utf-8");
  const parsed = JSON.parse(raw);

  if (!parsed || typeof parsed !== "object")
    throw new Error("manifest must be a JSON object");
  if (!parsed.automations || !Array.isArray(parsed.automations))
    throw new Error("manifest.automations must be an array");

  const allErrors: string[] = [];
  for (let i = 0; i < parsed.automations.length; i++) {
    const entryErrors = validateEntry(parsed.automations[i] as AutomationEntry, i);
    allErrors.push(...entryErrors);
  }
  if (allErrors.length > 0) {
    const err = new Error(`manifest validation failed:\n  ${allErrors.join("\n  ")}`);
    (err as any).validationErrors = allErrors;
    throw err;
  }

  return parsed as AutomationManifest;
}

export { MANIFEST_PATH };
