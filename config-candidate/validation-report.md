# Validation Report

Generated: 2026-10-02T06:05:44Z
Candidate dir: /private/tmp/autonomy-verify/config-candidate

## 1. openclaw config validate

Command: openclaw config validate --json
Exit code: 0
Output:
```
{"valid":true,"path":"/Users/habeebodubunmi/.openclaw/openclaw.json","warnings":[]}
```
RESULT: PASSED

## 2. openclaw doctor --lint

Command: openclaw doctor --lint
Exit code: 137
Output:
```
(command killed after 10s timeout — no gateway running locally)
```
RESULT: TIMEOUT — killed after 10s (no gateway running locally; command recorded for manual run)

## 3. Tool-policy preview per agent

PASS: rhythm — no generic exec/SQL tools
PASS: growth — no generic exec/SQL tools
PASS: scholar — no generic exec/SQL tools
PASS: tola — has webSearch, no generic exec/SQL
PASS: rhythm — session.visibility=own
PASS: growth — session.visibility=own
PASS: scholar — session.visibility=own
INFO: tola session.visibility=all
INFO: workshop.autonomousMode=propose
INFO: workshop.approvalPolicy=pending
ALL TOOL-POLICY CHECKS PASSED

RESULT: PASSED

## 4. Secret-scan check

PASS: No plaintext secrets found in openclaw.json

## Summary

Validation complete. See individual sections above for details.
Note: If openclaw CLI is not available in this environment, config validate and doctor steps are skipped and recorded.
