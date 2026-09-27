"use strict";
/// Automation definitions for Batch 14 proactive automations.
// Each automation has an owner agent, schedule kind, workflow reference, and description.
Object.defineProperty(exports, "__esModule", { value: true });
exports.AUTOMATIONS = void 0;
// ── Five initial automations ──────────────────────────────────────────
exports.AUTOMATIONS = [
    // T14.1: Growth daily anomaly check
    {
        id: "growth-daily-anomaly",
        ownerAgentId: "growth",
        scheduleKind: "daily",
        workflowRef: "growth/anomaly-check",
        description: "Daily lightweight anomaly check for growth agent",
    },
    // T14.2: Growth weekly detailed review
    {
        id: "growth-weekly-review",
        ownerAgentId: "growth",
        scheduleKind: "weekly",
        workflowRef: "growth/weekly-review",
        description: "Weekly detailed review for growth agent",
    },
    // T14.3: Tola weekly portfolio review
    {
        id: "tola-weekly-review",
        ownerAgentId: "tola",
        scheduleKind: "weekly",
        workflowRef: "tola/portfolio-review",
        description: "Weekly portfolio review for tola agent",
    },
    // T14.4: Scholar weekly progress review with enabledWhen predicate
    {
        id: "scholar-weekly-progress",
        ownerAgentId: "scholar",
        scheduleKind: "weekly",
        workflowRef: "scholar/progress-review",
        description: "Weekly progress review for scholar agent if state quality is sufficient",
        enabledWhen: (state) => {
            // InIntenSIQ state quality must be sufficient for the review to proceed.
            // Encode: only run when state.quality >= "medium" (or whatever the predicate decides).
            return (state.quality ?? "low") !== "low";
        },
    },
    // T14.5: Rhythm — explicitly absent. No autonomous weekly rewrite initially.
    // Encoded as a comment below; no entry in AUTOMATIONS so the runner
    // will never find an automation with ownerId "rhythm" for a weekly schedule
    // unless one is explicitly added later.
];
// Default export for convenience — pick growth-daily-anomaly as the first.
exports.default = exports.AUTOMATIONS;
