// Typed Supabase PostgREST adapter — the only persistence adapter (V1, Supabase-only).
// Errors are explicit: no false success. See openclaw_four_agent_system_v1_1.md §9.7/§9.8.

export type ErrorCode =
  | "UNAVAILABLE" // network failure / timeout / 5xx — operation did not land
  | "MALFORMED" // response could not be parsed — operation outcome unknown, surface loudly
  | "AUTH" // 401/403
  | "NOT_FOUND"
  | "CONFLICT" // optimistic-concurrency violation
  | "VALIDATION" // repository-level input rejection
  | "AUDIT_FAILED"; // authority write landed but audit append failed

export class BlackboardError extends Error {
  code: ErrorCode;
  detail?: unknown;

  constructor(code: ErrorCode, message: string, detail?: unknown) {
    super(`[${code}] ${message}`);
    this.code = code;
    this.detail = detail;
  }
}

export interface SupabaseAdapterOptions {
  url: string; // e.g. https://<ref>.supabase.co/rest/v1
  serviceKey: string;
  timeoutMs?: number;
}

export interface PostgrestResponse<T> {
  rows: T[];
  count: number | null;
  status: number;
}

const REDACT_HEADERS = new Set(["apikey", "authorization", "prefer"]);

export class SupabaseAdapter {
  private url: string;
  private serviceKey: string;
  private timeoutMs: number;

  constructor(opts: SupabaseAdapterOptions) {
    this.url = opts.url.replace(/\/$/, "");
    this.serviceKey = opts.serviceKey;
    this.timeoutMs = opts.timeoutMs ?? 10_000;
  }

  async request<T = Record<string, unknown>>(
    method: "GET" | "POST" | "PATCH" | "DELETE",
    path: string,
    opts: {
      query?: Record<string, string>;
      body?: unknown;
      prefer?: string;
      searchParams?: URLSearchParams; // raw, for complex filters
    } = {},
  ): Promise<PostgrestResponse<T>> {
    const params = opts.searchParams ?? new URLSearchParams(opts.query ?? {});
    const url = `${this.url}/${path}${params.toString() ? `?${params.toString()}` : ""}`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    const headers: Record<string, string> = {
      apikey: this.serviceKey,
      authorization: `Bearer ${this.serviceKey}`,
      "content-type": "application/json",
      accept: "application/json",
    };
    if (opts.prefer) headers.prefer = opts.prefer;

    let res: Response;
    try {
      res = await fetch(url, {
        method,
        headers,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        signal: controller.signal,
      });
    } catch (err: unknown) {
      clearTimeout(timer);
      throw new BlackboardError(
        "UNAVAILABLE",
        `authoritative store unreachable: ${(err as Error).message}`,
      );
    }
    clearTimeout(timer);

    const text = await res.text();

    if (res.status === 401 || res.status === 403) {
      throw new BlackboardError("AUTH", `supabase rejected credentials (HTTP ${res.status})`);
    }
    if (res.status >= 500) {
      throw new BlackboardError("UNAVAILABLE", `supabase server error (HTTP ${res.status})`, safeSlice(text));
    }

    let rows: T[] = [];
    if (text.length > 0) {
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        // T4.6: malformed response must never masquerade as success.
        throw new BlackboardError("MALFORMED", `unparseable response (HTTP ${res.status})`, safeSlice(text));
      }
      if (!Array.isArray(parsed)) {
        if (res.ok) {
          // Some endpoints return a single object or an OpenAPI error shape.
          if (parsed !== null && typeof parsed === "object" && parsed !== null) {
            const maybe = parsed as Record<string, unknown>;
            if ("message" in maybe || "code" in maybe) {
              throw new BlackboardError("MALFORMED", `unexpected error body (HTTP ${res.status})`, maybe);
            }
            rows = [parsed as T];
          } else {
            throw new BlackboardError("MALFORMED", `unexpected response shape (HTTP ${res.status})`);
          }
        } else {
          throw new BlackboardError("MALFORMED", `unexpected error body (HTTP ${res.status})`, parsed);
        }
      } else {
        rows = parsed as T[];
      }
    }

    if (!res.ok) {
      // PostgREST 4xx business errors (e.g. FK violation surfaces as 4xx error JSON).
      const first = rows[0] as Record<string, unknown> | undefined;
      if (first && typeof first.message === "string") {
        throw new BlackboardError("VALIDATION", `supabase rejected request (HTTP ${res.status})`, first);
      }
      throw new BlackboardError("VALIDATION", `supabase rejected request (HTTP ${res.status})`, safeSlice(text));
    }

    const countHeader = res.headers.get("content-profile");
    const countVal = res.headers.get("content-range");
    let count: number | null = null;
    if (countVal) {
      const m = /^(\d+)-(\d+)\/(\d+|\*)$/.exec(countVal);
      if (m && m[3] !== "*") count = Number(m[3]);
    }
    void countHeader;
    return { rows, count, status: res.status };
  }

  redactedConfig(): Record<string, unknown> {
    return { url: this.url, serviceKey: `${redactKey(this.serviceKey)}`, timeoutMs: this.timeoutMs };
  }
}

function safeSlice(text: string): string {
  return text.length > 300 ? `${text.slice(0, 300)}...` : text;
}

function redactKey(key: string): string {
  if (key.length <= 12) return "***";
  return `${key.slice(0, 6)}...${key.slice(-4)}`;
}

export { REDACT_HEADERS };
