/**
 * Error redaction — no secret keys, stack traces, or provider messages
 * ever surface to the model.  Only safe, sanitised error codes and
 * messages are returned.
 */
export function redactError(error: unknown): {
  code: string;
  message: string;
  detail?: unknown;
} {
  // Only error classes with a known, safe error code may pass their message
  // through (BlackboardError messages are composed by our own code).  Anything
  // else — raw provider errors, unknown objects, strings — gets a generic
  // message so no secrets/stacks/provider text can reach the model (T5.5).
  const SAFE_CODES = new Set([
    "UNAVAILABLE",
    "MALFORMED",
    "AUTH",
    "NOT_FOUND",
    "CONFLICT",
    "VALIDATION",
    "AUDIT_FAILED",
  ]);
  if (error instanceof Error) {
    const code = (error as { code?: unknown }).code;
    if (typeof code === "string" && SAFE_CODES.has(code)) {
      return { code, message: error.message || "An unexpected error occurred", detail: undefined };
    }
    return { code: "UNKNOWN", message: "An unexpected error occurred", detail: undefined };
  }
  if (typeof error === "object" && error !== null) {
    const e = error as Record<string, unknown>;
    const code = typeof e.code === "string" && SAFE_CODES.has(e.code) ? e.code : "UNKNOWN";
    if (code !== "UNKNOWN") {
      const msg = typeof e.message === "string" ? e.message : "An unexpected error occurred";
      return { code, message: msg, detail: undefined };
    }
    return { code: "UNKNOWN", message: "An unexpected error occurred", detail: undefined };
  }
  return {
    code: "UNKNOWN",
    message: "An unexpected error occurred",
  };
}
