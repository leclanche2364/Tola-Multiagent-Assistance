/**
 * Model registry and allowlist — Batch 6 (§10.1, §10.3).
 *
 * Single source of truth for approved routes and models.
 * T6.2: unapproved model selection must be rejected.
 */
import { BlackboardError } from "../../blackboard-tools/src/adapters/supabase.ts";

export const ROUTES = ["R0", "R1", "R2", "R3", "R4"] as const;
export type Route = (typeof ROUTES)[number];

export interface RouteEntry {
  route: Route;
  model_id: string | null; // null = deterministic code, no model
  description: string;
  timeout_seconds: number; // §10.4 policy defaults
}

export const MODEL_REGISTRY: Record<Route, RouteEntry> = {
  R0: {
    route: "R0",
    model_id: null,
    description: "deterministic code: arithmetic, date logic, comparison, validation, sorting, deduplication",
    timeout_seconds: 30,
  },
  R1: {
    route: "R1",
    model_id: "inclusionai/ling-3.0-flash",
    description: "cheap extraction, transformation, summarisation",
    timeout_seconds: 120,
  },
  R2: {
    route: "R2",
    model_id: "nvidia/nemotron-3.5-lightning",
    description: "fast structured tool/API execution",
    timeout_seconds: 120,
  },
  R3: {
    route: "R3",
    model_id: "deepseek/deepseek-v4-flash-0731",
    description: "inexpensive multi-step agentic work, investigation and iteration",
    timeout_seconds: 600,
  },
  R4: {
    route: "R4",
    model_id: "z-ai/glm-5.3-flash",
    description: "orchestration, ambiguous reasoning, synthesis and planning (Tola primary)",
    timeout_seconds: 900,
  },
};

export function isRoute(value: unknown): value is Route {
  return typeof value === "string" && (ROUTES as readonly string[]).includes(value);
}

export function assertRoute(value: unknown): Route {
  if (!isRoute(value)) {
    throw new BlackboardError("VALIDATION", `invalid model route: ${JSON.stringify(value)}`);
  }
  return value;
}

/**
 * T6.2 allowlist enforcement. Only the registry model for a route (or R0's
 * deterministic mechanism) may be used for that route.
 */
export function assertApprovedModel(route: Route, modelId: string | null | undefined): void {
  const approved = MODEL_REGISTRY[route].model_id;
  if (route === "R0") {
    if (modelId !== null && modelId !== undefined) {
      throw new BlackboardError("VALIDATION", "R0 is deterministic code: no model may be attached");
    }
    return;
  }
  if (modelId !== approved) {
    throw new BlackboardError(
      "VALIDATION",
      `unapproved model for ${route}: expected ${approved}, got ${JSON.stringify(modelId)}`
    );
  }
}

export function isApprovedModel(route: Route, modelId: string | null | undefined): boolean {
  try {
    assertApprovedModel(route, modelId);
    return true;
  } catch {
    return false;
  }
}
