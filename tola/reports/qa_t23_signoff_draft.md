# QA T23 Signoff Draft -- Proposal-First Self-Improvement

Date: 2026-09-29
Batch: T23

## Per-Case Results

### T23-01: Better candidate creates proposal, not auto-apply
- **Status**: PASS
- **Detail**: `propose_improvement()` returns a `Proposal` (frozen dataclass) when `comparison.verdict` is "ACCEPTED" (improved). The proposal binds `benchmark_version`, `candidate_hash` (sha256 of canonical JSON), and per-fixture scores. No `AppliedChange` is created on proposal alone; `apply_or_reject()` with no token returns `SKIP_UNAPPROVED`, leaving production unchanged.

### T23-02: Worse candidate rejected
- **Status**: PASS
- **Detail**: When `comparison.verdict` is not "ACCEPTED" (e.g., "REJECTED" or "REVIEW"), `propose_improvement()` returns `None`. A worse candidate (degraded metrics) produces no proposal and no state change.

### T23-03: Permission/security change cannot self-apply
- **Status**: PASS
- **Detail**: A proposal with `category` in `PROTECTED_CATEGORIES` (`permissions`, `security`) has `protected=True`. `apply_or_reject()` returns `BLOCK_PROTECTED` when the token lacks the `:protected_approval` suffix. With the suffix, the guard passes and returns `APPLY`.

### T23-04: Core Skill mutation remains pending until approval
- **Status**: PASS
- **Detail**: A proposal with `category="core_skills"` is protected. Without a token or with a wrong token, `apply_or_reject()` returns `SKIP_UNAPPROVED`. With the correct token (including `:protected_approval` suffix), it returns `APPLY`. The proposal remains pending until explicit protected approval.

### T23-05: Proposal is bound to evaluated version/hash
- **Status**: PASS
- **Detail**: `Proposal.benchmark_version` equals `BENCHMARK_VERSION` ("1.0.0"). `Proposal.candidate_hash` equals `sha256(canonical_json(candidate_dict))`. Re-running `propose_improvement()` with the same inputs produces the same hash (deterministic).

### T23-06: Approved proposal applies correct version
- **Status**: PASS
- **Detail**: `apply_or_reject()` returns `APPLY` when the token matches and version is current. `create_apply()` returns an `AppliedChange` with `applied_version` equal to `BENCHMARK_VERSION` and a non-empty `applied_hash`.

### T23-07: Unapproved proposal leaves production unchanged
- **Status**: PASS
- **Detail**: `apply_or_reject()` with no token or wrong token returns `SKIP_UNAPPROVED`. `create_apply()` returns `None` in both cases. Production state is unchanged.

### T23-08: Rollback path tested
- **Status**: PASS
- **Detail**: `rollback(applied)` returns a dict with `version` and `hash` restored to the pre-apply state (`prior_version`, `prior_hash` from `AppliedChange`). Round-trip apply-then-rollback returns state to the previous hash. Version mismatch returns `SKIP_STALE`.

## Deviations

- None. All T23-01..T23-08 cases pass. 775 total tests (T1..T23), 0 failures, 0 errors.

## Notes

- `PROTECTED_CATEGORIES` is a frozen frozenset: `core_skills`, `permissions`, `security`, `architecture`.
- The approval token mechanism embeds the proposal hash; protected categories require the `:protected_approval` suffix.
- All files use Python stdlib only (hashlib, json, dataclasses). No network, no clock reads, no LLM calls.
- Plain ASCII in every file.