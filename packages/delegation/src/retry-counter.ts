// Malformed-result retry counter — Batch 07
// Persists retry counts in-memory so "retry once" cannot repeat forever.
// The review() function checks this counter before allowing a retry.

const retryCounts = new Map<string, number>();

export function getRetryCount(idempotencyKey: string): number {
  return retryCounts.get(idempotencyKey) ?? 0;
}

export function incrementRetryCount(idempotencyKey: string): number {
  const current = retryCounts.get(idempotencyKey) ?? 0;
  retryCounts.set(idempotencyKey, current + 1);
  return current + 1;
}

export function resetRetryCount(idempotencyKey: string): void {
  retryCounts.delete(idempotencyKey);
}

export function canRetry(idempotencyKey: string): boolean {
  return getRetryCount(idempotencyKey) < 1;
}
