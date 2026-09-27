# skills/manifests

## Purpose

Structured metadata describing every skill in the system. Each manifest is a `SkillManifest` record that captures identity, provenance, capabilities, review state, and activation state.

## Lifecycle Rules

- **Structured metadata.** Manifests capture: id, name, version, upstream source (repo + commit + path), licence (SPDX id), capabilities (network, secrets, filesystem), review status, and activation state.
- **Single source of truth.** All governance decisions reference the manifest.
- **Immutable once reviewed.** Review fields are append-only; status transitions are recorded, not overwritten.
- **Capabilities are explicit.** Network access, secrets, and filesystem access must be declared and justified.
- **Licence is required.** No skill can have a manifest without a valid SPDX licence identifier.
