/// Automation state store — persistence seam for cycle-idempotency (T14.5).
// The store tracks which periods each automation has already run, keyed on
// (automationId, periodString). On restart, the store is persisted so the new
// runner instance does not re-run completed periods (no double-run).

import type { AutomationDefinition } from "./registry";
export type { AutomationDefinition };

export type PeriodString = string; // e.g. "2026-09-27" or "2026-W39"

export interface AutomationStateStore {
  /** Has this automation already run for the given period? */
  hasRun(automationId: string, period: PeriodString): Promise<boolean>;
  /** Mark the given automation as having run for the period. */
  markRun(automationId: string, period: PeriodString): Promise<void>;
  /** Get the set of periods already run for an automation. */
  getRunsFor(automationId: string): Promise<PeriodString[]>;
  /** Clear all persisted state (for testing/reset). */
  clear(): Promise<void>;
}

export class InMemoryAutomationStateStore implements AutomationStateStore {
  private store: Map<string, Set<PeriodString>> = new Map(); // automationId → set of periods

  async hasRun(automationId: string, period: PeriodString): Promise<boolean> {
    const periods = this.store.get(automationId);
    return periods !== undefined && periods.has(period);
  }

  async markRun(automationId: string, period: PeriodString): Promise<void> {
    let periods = this.store.get(automationId);
    if (!periods) {
      periods = new Set();
      this.store.set(automationId, periods);
    }
    periods.add(period);
  }

  async getRunsFor(automationId: string): Promise<PeriodString[]> {
    const periods = this.store.get(automationId);
    return periods !== undefined ? Array.from(periods) : [];
  }

  async clear(): Promise<void> {
    this.store.clear();
  }
}