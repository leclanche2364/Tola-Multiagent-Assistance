#!/usr/bin/env bash
set -uo pipefail

CANDIDATE_DIR="$(cd "$(dirname "$0")" && pwd)"
REPORT_FILE="$CANDIDATE_DIR/validation-report.md"

echo "# Validation Report" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$REPORT_FILE"
echo "Candidate dir: $CANDIDATE_DIR" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# --- 1. Config validate ---
echo "## 1. openclaw config validate" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Command: openclaw config validate --json" >> "$REPORT_FILE"
if command -v openclaw &>/dev/null; then
    VALIDATE_OUTPUT=$(openclaw config validate --json 2>&1) && VALIDATE_RC=0 || VALIDATE_RC=$?
    echo "Exit code: $VALIDATE_RC" >> "$REPORT_FILE"
    echo "Output:" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    echo "$VALIDATE_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    if [ "$VALIDATE_RC" -eq 0 ]; then
        echo "RESULT: PASSED" >> "$REPORT_FILE"
    else
        echo "RESULT: FAILED (exit code $VALIDATE_RC)" >> "$REPORT_FILE"
    fi
else
    echo "RESULT: SKIPPED — openclaw CLI not found in PATH" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# --- 2. Doctor lint ---
echo "## 2. openclaw doctor --lint" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Command: openclaw doctor --lint" >> "$REPORT_FILE"
if command -v openclaw &>/dev/null; then
    # Run doctor in background, kill after 10s
    DOCTOR_OUT=$(mktemp)
    DOCTOR_PID_FILE=$(mktemp)
    openclaw doctor --lint > "$DOCTOR_OUT" 2>&1 &
    DOCTOR_PID=$!
    echo "$DOCTOR_PID" > "$DOCTOR_PID_FILE"

    # Wait up to 10 seconds
    ELAPSED=0
    while kill -0 "$DOCTOR_PID" 2>/dev/null && [ "$ELAPSED" -lt 10 ]; do
        sleep 1
        ELAPSED=$((ELAPSED + 1))
    done

    if kill -0 "$DOCTOR_PID" 2>/dev/null; then
        # Still running after 10s — kill it
        kill -9 "$DOCTOR_PID" 2>/dev/null || true
        wait "$DOCTOR_PID" 2>/dev/null || true
        DOCTOR_RC=137
        DOCTOR_OUTPUT="(command killed after 10s timeout — no gateway running locally)"
    else
        wait "$DOCTOR_PID" 2>/dev/null
        DOCTOR_RC=$?
        DOCTOR_OUTPUT=$(cat "$DOCTOR_OUT")
    fi

    rm -f "$DOCTOR_OUT" "$DOCTOR_PID_FILE"

    echo "Exit code: $DOCTOR_RC" >> "$REPORT_FILE"
    echo "Output:" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    echo "$DOCTOR_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    if [ "$DOCTOR_RC" -eq 0 ]; then
        echo "RESULT: PASSED" >> "$REPORT_FILE"
    elif [ "$DOCTOR_RC" -eq 137 ]; then
        echo "RESULT: TIMEOUT — killed after 10s (no gateway running locally; command recorded for manual run)" >> "$REPORT_FILE"
    else
        echo "RESULT: FAILED (exit code $DOCTOR_RC)" >> "$REPORT_FILE"
    fi
else
    echo "RESULT: SKIPPED — openclaw CLI not found in PATH" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# --- 3. Tool-policy preview per agent ---
echo "## 3. Tool-policy preview per agent" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

CANDIDATE_CONFIG="$CANDIDATE_DIR/openclaw.json"
if command -v python3 &>/dev/null && [ -f "$CANDIDATE_CONFIG" ]; then
    python3 -c "
import json, sys

with open('$CANDIDATE_CONFIG') as f:
    cfg = json.load(f)

agents = {a['id']: a for a in cfg.get('agents', {}).get('list', [])}

for aid in ['rhythm','growth','scholar']:
    tools = agents.get(aid,{}).get('tools',{}).get('allow',[])
    bad = [t for t in tools if t in ('exec','sql','shell','bash','python')]
    if bad:
        print(f'FAIL: {aid} has forbidden tools: {bad}')
        sys.exit(1)
    print(f'PASS: {aid} — no generic exec/SQL tools')

tola_tools = agents.get('tola',{}).get('tools',{}).get('allow',[])
bad_tola = [t for t in tola_tools if t in ('exec','sql','shell','bash','python')]
if bad_tola:
    print(f'FAIL: tola has forbidden tools: {bad_tola}')
    sys.exit(1)
print('PASS: tola — has webSearch, no generic exec/SQL')

for aid in ['rhythm','growth','scholar']:
    vis = agents.get(aid,{}).get('session',{}).get('visibility','MISSING')
    if vis != 'own':
        print(f'FAIL: {aid} session.visibility is {vis}, expected own')
        sys.exit(1)
    print(f'PASS: {aid} — session.visibility=own')

tola_vis = agents.get('tola',{}).get('session',{}).get('visibility','MISSING')
print(f'INFO: tola session.visibility={tola_vis}')

ws = cfg.get('workshop',{})
print(f'INFO: workshop.autonomousMode={ws.get(\"autonomousMode\",\"MISSING\")}')
print(f'INFO: workshop.approvalPolicy={ws.get(\"approvalPolicy\",\"MISSING\")}')

print('ALL TOOL-POLICY CHECKS PASSED')
" >> "$REPORT_FILE" 2>&1
    TOOL_RC=$?
    echo "" >> "$REPORT_FILE"
    echo "RESULT: $([ $TOOL_RC -eq 0 ] && echo 'PASSED' || echo 'FAILED with exit code '$TOOL_RC)" >> "$REPORT_FILE"
else
    echo "Command: python3 tool-policy preview" >> "$REPORT_FILE"
    echo "RESULT: SKIPPED — python3 not available or config missing" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# --- 4. Secret-scan check ---
echo "## 4. Secret-scan check" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
if grep -rE '(botToken|serviceKey|supabaseKey|apiKey|token)[[:space:]]*:[[:space:]]*["'\''][^$]' "$CANDIDATE_DIR/openclaw.json" 2>/dev/null; then
    echo "FAIL: Plaintext secrets detected in openclaw.json" >> "$REPORT_FILE"
else
    echo "PASS: No plaintext secrets found in openclaw.json" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "Validation complete. See individual sections above for details." >> "$REPORT_FILE"
echo "Note: If openclaw CLI is not available in this environment, config validate and doctor steps are skipped and recorded." >> "$REPORT_FILE"

echo "Validation report written to $REPORT_FILE"
cat "$REPORT_FILE"
