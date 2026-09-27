# Specialist stubs — Batch 7 (inert, allowlist testing only)

These three agent IDs exist ONLY so Tola's spawn allowlist can be tested end-to-end.
They are not live specialists yet. Batches 10–12 instantiate them for real, one at a time.

| Agent | Future role | Future channel | Status |
|---|---|---|---|
| `rhythm` | Life planning & scheduling (§4.2) | `#rhythm` | inert stub |
| `growth` | Growth intelligence (§4.3) | `#growth` | inert stub |
| `scholar` | Learning system (§4.4) | `#scholar` | inert stub |

Rules for stubs:

- No channel bindings. No cron jobs. No skills. No tool grants beyond defaults.
- If messaged directly, they reply with a single line: "stub — not yet instantiated" and nothing else.
- They never write to the Blackboard. Only Tola reviews/records their results (from Batch 8 onward).
- Stubs exist in config so `allowAgents: ["rhythm","growth","scholar"]` validates; removing a stub id from config while it remains in the allowlist is a config error.
