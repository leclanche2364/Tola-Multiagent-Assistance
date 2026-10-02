# Candidate config — post-incident note (2026-10-02)

Per-agent `tools.allow` and `session.visibility` blocks were REMOVED from this candidate after the 2026-10-02 live outage (see `docs/current-state/postmortems/2026-10-02-config-allowlist-outage.md`). Root cause: `tools.allow` is a global deny-by-default allowlist in the live runtime; the allowlists stripped exec/message/read/spawn from every agent.

**Do not re-add per-agent tool allowlists without a smoke-tested rehearsal on a disposable agent.** If hardening is revisited, use deny-lists or scoped blocks that cannot strip base tools.

Still-valid contents of this candidate: agent descriptions, model routing, workspace paths, subagent defaults (maxSpawnDepth/maxChildren/maxConcurrent), sandbox settings. Apply only via an explicit, diff-reviewed plan with per-agent post-restart smoke tests.
