"use strict";
/// Automation state store — persistence seam for cycle-idempotency (T14.5).
// The store tracks which periods each automation has already run, keyed on
// (automationId, periodString). On restart, the store is persisted so the new
// runner instance does not re-run completed periods (no double-run).
Object.defineProperty(exports, "__esModule", { value: true });
exports.InMemoryAutomationStateStore = void 0;
class InMemoryAutomationStateStore {
    store = new Map(); // automationId → set of periods
    async hasRun(automationId, period) {
        const periods = this.store.get(automationId);
        return periods !== undefined && periods.has(period);
    }
    async markRun(automationId, period) {
        let periods = this.store.get(automationId);
        if (!periods) {
            periods = new Set();
            this.store.set(automationId, periods);
        }
        periods.add(period);
    }
    async getRunsFor(automationId) {
        const periods = this.store.get(automationId);
        return periods !== undefined ? Array.from(periods) : [];
    }
    async clear() {
        this.store.clear();
    }
}
exports.InMemoryAutomationStateStore = InMemoryAutomationStateStore;
