"use strict";
/// Automation runner — executes one cycle per due automation.
// Idempotency: keyed on (automationId, periodString).
// - Second run for same period → {skipped:'already-run'}, no workflow exec.
// - Task run recorded via repo BEFORE workflow execution.
// - No-change suppression: {changed:false} → completed/no-change, no notification.
// - Outage: workflow throws or {degraded:true} → failed/partial, NO retry in same cycle.
Object.defineProperty(exports, "__esModule", { value: true });
exports.AutomationRunner = void 0;
// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------
class AutomationRunner {
    repo; // BlackboardRepository-like (provides startTaskRun + completeTaskRun)
    clock;
    store;
    workflows;
    /**
     * @param repo          BlackboardRepository-like for task-run persistence.
     * @param clock         provides the current time for period computation.
     * @param store         persistence seam for "already-run" periods (T14.5).
     * @param workflows     map of automationId → async workflow function.
     */
    constructor(repo, clock, store, workflows) {
        this.repo = repo;
        this.clock = clock;
        this.store = store;
        this.workflows = workflows;
    }
    /** Run one cycle for the given automationId. */
    async runDue(automationId) {
        // ---- 1. Compute period string from clock ----
        const now = this.clock();
        const period = this.periodFor(now, automationId);
        // ---- 2. Idempotency check: already run this period? ----
        const alreadyRun = await this.store.hasRun(automationId, period);
        if (alreadyRun) {
            return { status: "skipped", reason: "already-run" };
        }
        // ---- 3. Record a task run via the repo BEFORE executing the workflow ----
        const idempotencyKey = `auto-${automationId}-${period}`;
        const taskRun = await this.repo.startTaskRun({
            task_id: `auto-${automationId}-task`,
            idempotency_key: idempotencyKey,
            attempt: 1,
        });
        // ---- 4. Execute the workflow for this automation ----
        const workflow = this.workflows[automationId];
        if (!workflow) {
            await this.repo.completeTaskRun({
                run_id: taskRun.run_id,
                status: "failed",
                summary: `No workflow found for automation ${automationId}`,
            });
            await this.store.markRun(automationId, period);
            return {
                status: "failed",
                taskRunId: taskRun.run_id,
                summary: `No workflow for ${automationId}`,
                error: "missing-workflow",
            };
        }
        let result;
        try {
            result = await workflow(automationId);
        }
        catch (err) {
            // Outage: workflow threw — record partial state, no retry in same cycle.
            await this.repo.completeTaskRun({
                run_id: taskRun.run_id,
                status: "partial",
                summary: `Workflow threw: ${err.message || "unknown error"}`,
            });
            await this.store.markRun(automationId, period);
            return {
                status: "failed",
                taskRunId: taskRun.run_id,
                summary: `Workflow threw: ${err.message || "unknown error"}`,
                error: err.message,
            };
        }
        // ---- 5b. Workflow returned a result ----
        if (result.degraded) {
            // Outage / degraded path — record partial, no retry in same cycle.
            await this.repo.completeTaskRun({
                run_id: taskRun.run_id,
                status: "partial",
                summary: result.summary || "Workflow degraded",
            });
            await this.store.markRun(automationId, period);
            return {
                status: "failed",
                taskRunId: taskRun.run_id,
                summary: result.summary || "Workflow degraded",
                error: "degraded",
            };
        }
        if (result.changed === false) {
            // No-change suppression — record as completed, no notification.
            await this.repo.completeTaskRun({
                run_id: taskRun.run_id,
                status: "success",
                summary: result.summary || "No changes",
            });
            await this.store.markRun(automationId, period);
            return {
                status: "no-change",
                taskRunId: taskRun.run_id,
                summary: result.summary || "No changes",
            };
        }
        // ---- 5c. Normal success with changes ----
        await this.repo.completeTaskRun({
            run_id: taskRun.run_id,
            status: "success",
            summary: result.summary || "Changes applied",
        });
        await this.store.markRun(automationId, period);
        return {
            status: "ok",
            taskRunId: taskRun.run_id,
            summary: result.summary || "Changes applied",
        };
    }
    // ---- Period computation ---------------------------------------------------
    periodFor(now, automationId) {
        if (/daily/i.test(automationId)) {
            // Daily: "YYYY-MM-DD"
            return now.toISOString().split("T")[0];
        }
        // Weekly: ISO week number, format "2026-W39"
        const year = now.getFullYear();
        const jan1 = new Date(year, 0, 1);
        const dayOfYear = Math.floor((now.getTime() - jan1.getTime()) / 86400000);
        const jan4 = new Date(year, 0, 4);
        const offsetToJan4 = (jan4.getDay() + 6) % 7; // 0=Mon .. 6=Sun
        const jan4Week = Math.ceil((jan4.getDate() + offsetToJan4) / 7);
        // Week number for now: approximate but ISO-compatible
        const weekNum = Math.ceil((dayOfYear + offsetToJan4) / 7);
        return `2026-W${String(weekNum).padStart(2, "0")}`;
    }
}
exports.AutomationRunner = AutomationRunner;
