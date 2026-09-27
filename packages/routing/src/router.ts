/**
 * Baseline route classifier — Batch 6 (§10.2 decision order).
 *
 * Deterministic rules classifier. Jev Router promotion happens only after
 * the T6.1 accuracy gate passes against this baseline (§10.4 amendment).
 * Uncertain -> R4 (decision order rule 6).
 */
import type { Route } from "./registry.ts";

export interface RoutingInput {
  title: string;
  instructions?: string | null;
  /** Structured signals describing the task's nature. */
  signals?: string[];
}

export interface RoutingDecision {
  route: Route;
  reason: string;
}

// Signal vocabulary (declared in fixtures and by callers).
const R0_SIGNALS = ["deterministic", "arithmetic", "date_logic", "comparison", "validation", "sorting", "deduplication"];
const R1_SIGNALS = ["extraction", "transformation", "summarisation"];
const R2_SIGNALS = ["tool_op", "api_call", "structured_output", "single_step_tool"];
const R3_SIGNALS = ["agentic", "multi_step", "investigation", "iteration", "tool_loop"];
const R4_SIGNALS = ["ambiguous", "planning", "prioritisation", "synthesis", "orchestration"];

function firstMatch(signals: string[], vocab: string[]): string | null {
  for (const s of signals) {
    if (vocab.includes(s)) return s;
  }
  return null;
}

/**
 * Classify per §10.2 order:
 * 1. deterministic -> R0
 * 2. extraction/transformation/summarisation -> R1
 * 3. strict tool/API op -> R2
 * 4. multi-step agentic -> R3
 * 5. ambiguous planning/synthesis -> R4
 * 6. uncertain -> R4
 *
 * R2 beats R3 when the task is a single strict tool op even inside a loop
 * context; R3 beats R4 when investigation is concrete rather than ambiguous.
 */
export function classifyRoute(input: RoutingInput): RoutingDecision {
  const signals = (input.signals ?? []).map((s) => s.toLowerCase());

  const r0 = firstMatch(signals, R0_SIGNALS);
  if (r0) return { route: "R0", reason: `deterministic signal: ${r0}` };

  const r1 = firstMatch(signals, R1_SIGNALS);
  if (r1) return { route: "R1", reason: `extraction/transformation/summarisation signal: ${r1}` };

  const r2 = firstMatch(signals, R2_SIGNALS);
  const r3 = firstMatch(signals, R3_SIGNALS);
  if (r2 && !r3) return { route: "R2", reason: `strict tool operation signal: ${r2}` };
  if (r2 && r3) {
    // A strict tool op embedded in a multi-step loop: R3 owns the loop.
    return { route: "R3", reason: `multi-step agentic loop (${r3}) wrapping tool ops (${r2})` };
  }
  if (r3) return { route: "R3", reason: `multi-step investigation signal: ${r3}` };

  const r4 = firstMatch(signals, R4_SIGNALS);
  if (r4) return { route: "R4", reason: `planning/synthesis signal: ${r4}` };

  // Input length is not complexity (§10.3): never classify on length.
  return { route: "R4", reason: "uncertain -> R4 by default (§10.2 rule 6)" };
}
