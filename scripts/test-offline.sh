#!/usr/bin/env bash
# Offline TS tests: run every tests/*.test.ts across packages.
# *.live.test.ts suites are credential-dependent and self-skip with an
# explicit reason when .env/credentials are absent, so this is offline-safe.
set -euo pipefail
cd "$(dirname "$0")/.."
rc=0
for p in packages/*/; do
  if [ -f "$p/package.json" ] && node -e "process.exit(require('./$p/package.json').scripts?.test?0:1)" 2>/dev/null; then
    echo "test: $p"
    (cd "$p" && npm test >/dev/null) || rc=1
  fi
done
exit $rc