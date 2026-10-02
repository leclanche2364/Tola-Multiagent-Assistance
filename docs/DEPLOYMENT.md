# OpenClaw Release Deployment — Batch 11

## Overview

The deploy tool (`packages/deploy`) provides an atomic release deployment
for OpenClaw. It follows a **dry-run-first** philosophy: all validation,
build, and reconciliation steps run in a staging directory before any
live changes are considered.

## Approval Boundary

| Phase | Who | What |
|-------|-----|------|
| **Dry-run** | Automation agent | Runs in staging; never touches live workspace or DB |
| **Apply** | Human operator only | Requires explicit `--apply` flag and operator authority |

The tool **must never** be run against the live machine by the automation
agent. Apply mode is behind a typed `DeployAdapter` interface — the real
adapter documents/subcommands the lifecycle, and tests use a fake adapter.

## Dry-Run Steps

1. **Install locked dependencies** — `npm ci` in staging directory
2. **Run the complete gate** — `scripts/gate.sh` in staging
3. **Build/validate plugin** — `npm run plugin:build && npm run plugin:validate`
4. **Validate config** — `config-candidate/validate.sh`
5. **Show migration plan** — lists pending Supabase migrations
6. **Reconcile automations** — reconciler dry-run mode from `packages/automations`

## Apply Steps (Operator Only)

1. **Back up** current config and workspace metadata
2. **Apply migrations** — via `DeployAdapter.applyMigration()`
3. **Activate/reload plugin** — via `DeployAdapter.reloadPlugin()`
4. **Apply config** — via `DeployAdapter.applyConfig()`
5. **Reconcile jobs** — live mode via `DeployAdapter.reconcileJobs(false)`
6. **Run canaries** — via `DeployAdapter.runCanaries()`

## Rollback

On any failed readiness check or canary failure:

1. **Roll back migrations** — `DeployAdapter.rollbackMigration()`
2. **Restore previous config/workspace metadata** — `DeployAdapter.restoreConfig()`
3. **DB migrations** are left in a documented safe-forward/rollback state
4. The deployments table is append-only; no rows are deleted

## Deployment Record

The `deployments` table (repo-only migration) records:

- `deployed_sha` — the exact commit SHA deployed
- `tag` — the release tag
- `component_versions` — JSON map of component versions
- `deployed_at` — timestamp
- `phase` — `dry-run` or `apply`
- `success` — whether the deployment succeeded
- `rollback_performed` — whether rollback was triggered

## Usage

```bash
# Dry-run (default — safe for automation agent)
node packages/deploy/src/deploy-cli.mjs <sha>

# Apply mode (requires operator authority — never run by automation)
node packages/deploy/src/deploy-cli.mjs <sha> --apply
```

## Feature Branch

All deployment work is on `feat/autonomy-supabase-only`. No pushes to
`main` or other branches.
