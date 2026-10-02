#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npm install --no-audit --no-fund >/dev/null 2>&1 || true
for p in packages/*/; do
  if [ -f "$p/package.json" ]; then
    (cd "$p" && npm install --no-audit --no-fund >/dev/null 2>&1 || true)
  fi
done
echo "install:all done"