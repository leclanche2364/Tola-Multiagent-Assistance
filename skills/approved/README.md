# skills/approved

## Purpose

Contains skills that have passed human review and are eligible for activation. Approval is an explicit human act — no automated path exists from quarantine to active status.

## Lifecycle Rules

- **Human-activated only.** A skill becomes active only when a human explicitly approves a specific revision.
- **Only approvedRevision can be activated.** The `activation.approvedRevision` field gates all runtime loading.
- **No auto-update.** Approved skills do not auto-update from upstream. Any change requires a new review cycle.
- **Mutation outside governed flow rejected.** Direct edits to approved skills are rejected by policy enforcement.
- **Self-learning proposals create proposal records, never direct apply.** The system can suggest new skills, but never silently apply them.
