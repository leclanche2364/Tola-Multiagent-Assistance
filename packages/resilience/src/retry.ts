// boundedRetry — exactly one retry on provider-timeout kind;
// no retry on UNAVAILABLE; never recursive.

export type RetryFn = () => Promise<unknown>;

export interface RetryOptions {
  retries: number;
}

export interface RetryError extends Error {
  kind?: string;
  code?: string;
}

export interface RetryResult {
  success: boolean;
  callCount: number;
  error?: RetryError;
}

export async function boundedRetry(fn: RetryFn, opts: RetryOptions): Promise<RetryResult> {
  const { retries } = opts;
  let callCount = 0;
  let lastError: RetryError | undefined;

  for (let i = 0; i <= retries; i++) {
    callCount++;
    try {
      const result = await fn();
      return { success: true, callCount };
    } catch (err: any) {
      lastError = err as RetryError;
      // No retry on UNAVAILABLE
      if (err?.code === 'UNAVAILABLE') {
        return { success: false, callCount, error: lastError };
      }
      // Only retry on provider-timeout
      if (err?.kind === 'provider-timeout' && i < retries) {
        continue; // exactly one more attempt
      }
      return { success: false, callCount, error: lastError };
    }
  }
  return { success: false, callCount, error: lastError };
}
