# Blackboard wiring — all agents

All agents write to the shared Supabase Blackboard through the TypeScript
`BlackboardRepository` (`packages/blackboard-tools/src/repository/blackboard.ts`,
exposed via `packages/blackboard-tools/src/index.ts`). **Supabase is the only
shared persistence.** There is no local outbox, queue or flush layer: a failed
write surfaces as an explicit `BlackboardError` (`UNAVAILABLE`, `CONFLICT`,
`VALIDATION`, `MALFORMED`) and the caller retries later with the same
`idempotency_key`. It never queues locally and never fakes success.

This replaces the retired Python `blackboard_client` SQLite-outbox package
(removed in Batch 02 of the autonomy plan; see `docs/CURRENT_SYSTEM.md`).

Rules (standing, 2026-09-29; updated 2026-10-01):

- The adapter NEVER reads env files. The caller loads credentials and
  passes `url` + `serviceKey` (REST key) in.
- Every write carries a deterministic `idempotency_key` (uuid5 of a
  stable namespace + natural key) so same-key retries are safe and
  produce exactly one authoritative effect.
- Read from the shared board, never from another agent's local files.
- Raw Postgres DB passwords are never used; REST key or linked CLI only.
- Optimistic concurrency: updates take the caller's seen `version`;
  stale versions are rejected with `CONFLICT` and the authoritative
  version is returned in the error detail.

## Integration pattern (TypeScript)

```ts
import { BlackboardRepository, SupabaseAdapter } from "@tola/blackboard-tools";

// caller loads its OWN env file and passes values in — no bundling
const repo = new BlackboardRepository(
  new SupabaseAdapter({ url, serviceKey, timeoutMs: 15_000 }),
);

await repo.createTask({
  idempotency_key: key,          // deterministic, caller-owned
  project_id,
  title,
  requested_by: "tola",
  assigned_to: "rhythm",
  risk_class: "A1",
});
// on BlackboardError UNAVAILABLE: report failure, retry later with the SAME key.
// never write the payload to a local queue or claim success without a row.
```

## Per-agent notes

- **Tola / Rhythm / Scholar** — use the pattern above with their own env files.
- **Growth** — keeps its existing local product-intelligence writer
  (`~/.openclaw/workspace-growth/product-intelligence/data/blackboard.sqlite3`)
  as a local analytics cache, explicitly NOT shared persistence and outside
  this repo. Its AGENTS.md already declares the Supabase blackboard as the
  canonical store and the local file as an outbox buffer only. Shared-board
  writes go through `BlackboardRepository` like every other agent.

## Test commands

```
cd ~/.openclaw/workspace/four-agent-repo/packages/blackboard-tools
node --experimental-strip-types --test --test-concurrency=1 tests/blackboard.test.ts
node --experimental-strip-types --test --test-concurrency=1 tests/no-local-queue.test.ts
```
