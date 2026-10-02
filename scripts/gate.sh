#!/usr/bin/env bash
# Batch 07 — reproducible offline gate.
# One command: install, typecheck all TS packages, offline TS tests, Python tests,
# migration lint, plugin build + validate. Live suites self-skip without credentials.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== install:all =="
npm run install:all

echo "== typecheck:all =="
npm run typecheck:all

echo "== offline TS tests =="
npm run test:offline

echo "== Python tests =="
npm run test:python

echo "== migration lint =="
npm run lint:migrations

echo "== plugin build + validate =="
npm run plugin:validate

echo "GATE OK"