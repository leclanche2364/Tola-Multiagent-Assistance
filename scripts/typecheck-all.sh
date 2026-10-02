#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
rc=0
for p in packages/*/; do
  if [ -f "$p/package.json" ] && node -e "process.exit(require('./$p/package.json').scripts?.typecheck?0:1)" 2>/dev/null; then
    echo "typecheck: $p"
    (cd "$p" && npm run typecheck >/dev/null) || rc=1
  fi
done
exit $rc