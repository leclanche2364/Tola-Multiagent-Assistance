# skills/vendor

## Purpose

Stores pinned upstream copies of third-party growth skills. Each vendor skill is a verbatim snapshot at a specific commit — never modified, never forked, never auto-updated.

## Lifecycle Rules

- **Pinned upstream copies.** Exact commit hash stored; no drift allowed.
- **Read-only.** Vendor skills cannot be mutated by any governed flow.
- **Never directly activated.** Vendor skills must be copied through quarantine → approved before use.
- **No auto-update.** Upstream changes do not affect the vendor copy; a new intake is required to pick up changes.
- **Licence recorded.** Every vendor skill must have a valid SPDX licence identifier.

## Growth Skills

- analytics
- attribution
- seo-audit
- cro
- ab-testing
- onboarding
- signup
- aso
