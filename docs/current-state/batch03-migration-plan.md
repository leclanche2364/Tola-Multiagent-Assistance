# Batch 03 — Migration plan (dry-run only, NOT applied)

Status: **plan only**. No migration has been applied to any live Supabase
project (including the linked dev project). Applying requires Habeeb's
explicit approval per the credential discipline rules.

## What the migration adds

File: `supabase/migrations/20261001180000_batch03_automation_approval_safety.sql`
(additive; the applied v1 migration is untouched, per "never edit an applied migration").

1. **`automation_occurrences`** — stable `automation_key` + `scheduled_for`
   with a uniqueness rule (one effect per scheduled occurrence), `openclaw_job_id`,
   `release_sha`, status (`pending|claimed|succeeded|failed|skipped`),
   `claimed_by/claimed_at`, timestamps.
2. **`claim_automation_occurrence()` / `finish_automation_occurrence()`** —
   SECURITY DEFINER transactional RPCs. Concurrent claimants race on the row
   lock: exactly one gets `claimed`, everyone else gets `already_claimed`.
   A `failed` occurrence may be re-claimed (retry path); `succeeded` may not.
3. **`approvals` extended** — `action_type`, `payload_hash`, `expires_at`,
   `consumed_at`, `consumed_by` (requester `requested_by` already exists).
4. **`consume_approval()`** — single-use, single-transaction consumption:
   locks the row (`FOR UPDATE`), then checks existence → already consumed →
   approval status → expiry (auto-flags `expired`) → canonical payload hash.
   A second caller always gets `already_consumed`; a mismatched payload never
   consumes. Emits an `approval.consumed` audit event.
5. **`external_operations`** — journal keyed by unique `idempotency_key` with
   `pending|succeeded|failed|unknown` state and `evidence_ref`.
   `set_operation_state()` enforces: an `unknown` result cannot transition
   without evidence (returns `blocked:unknown_requires_evidence`), and a
   `succeeded` op replays as `noop:succeeded` — never a second effect.
6. **Access control** — RLS enabled (deny-all) on the three tables, DML
   revoked from `anon`/`authenticated`, RPC execute granted to `service_role`
   only. Agents call narrow RPCs; they never hold generic table-write
   authority or raw database credentials.

## Test evidence

`supabase/tests/test_batch03.sql` (transactional, rollback at end) covers:
duplicate claim (T3.1), distinct occurrences both running (T3.2), approval
happy path + double-use rejection (T3.3), expired approval (T3.4), altered
payload (T3.5), unauthorised anon write (T3.6), unknown-replay blocking +
no-op replay (T3.7), failed-occurrence re-claim (T3.8).

## Rollback statement

The migration is fully additive. Rollback is:

```sql
drop function if exists public.claim_automation_occurrence(text, timestamptz, text, text, text);
drop function if exists public.finish_automation_occurrence(uuid, text, text);
drop function if exists public.consume_approval(uuid, text, text, text);
drop function if exists public.set_operation_state(text, text, text);
drop table if exists public.external_operations;
drop table if exists public.automation_occurrences;
alter table public.approvals
  drop column if exists action_type, drop column if exists payload_hash,
  drop column if exists expires_at,   drop column if exists consumed_at,
  drop column if exists consumed_by;
alter table public.approvals disable row level security;
```

No existing column is dropped or modified, so rollback cannot lose data.
Safe-forward: `supabase db push` applies migrations in filename order; the
batch file is additive-only so re-running from zero (fresh DB) converges.
