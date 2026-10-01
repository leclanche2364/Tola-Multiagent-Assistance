#!/usr/bin/env python3
"""Contract check: active docs must not reintroduce SQLite as Blackboard persistence.

Fails when any markdown doc that is not marked SUPERSEDED and not classified as
history (restore manifests, baselines, handovers, QA records) claims a local
SQLite outbox is shared application/Blackboard persistence or a primary
coordination store.

Run from the repo root:  python3 scripts/check_system_contract.py
Exit 0 = pass, 1 = violations found.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Patterns that reintroduce SQLite as the application/Blackboard persistence.
PATTERNS = [
    re.compile(r"SQLite (outbox|cache)[^.!\n]*\b(is|as|are)\b[^.\n]*(shared|primary|source of truth|coordination|application persistence)", re.I),
    re.compile(r"(shared|application)\s+(coordination state|persistence)[^.!\n]*SQLite", re.I),
]

HISTORY_HINTS = ("RESTORE_MANIFEST", "baseline/", "current-state/", "qa/", "handover", "graphify-out", "CHANGELOG")


def md_files():
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO, capture_output=True, text=True
    )
    return [REPO / p for p in out.stdout.splitlines() if p.strip()]


def main() -> int:
    violations = []
    corrections_header = re.compile(r"^#+ .*Historical corrections", re.M)
    for path in md_files():
        if not path.exists():
            continue
        rel = path.relative_to(REPO).as_posix()
        if any(h in rel for h in HISTORY_HINTS):
            continue
        text = path.read_text(errors="replace")
        head = text[:1200]
        if "SUPERSEDED" in head:
            continue  # historical, banner already points to the contract
        # Skip the contract's own 'Historical corrections' section, which
        # quotes the disproved claims verbatim. Content after the header is
        # refutation, not reintroduction.
        m = corrections_header.search(text)
        if m and "CURRENT_SYSTEM.md" in rel:
            text = text[: m.start()]
        for pat in PATTERNS:
            for match in pat.finditer(text):
                line_no = text[: match.start()].count("\n") + 1
                violations.append(f"{rel}:{line_no}: {match.group(0)[:100]}")
    if violations:
        print("FAIL: SQLite persistence reintroduced in active docs:")
        for v in violations:
            print("  " + v)
        return 1
    print("PASS: no active doc claims SQLite as shared Blackboard persistence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
