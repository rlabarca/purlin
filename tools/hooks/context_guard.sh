#!/usr/bin/env bash
# context_guard.sh — PreCompact hook that blocks auto-compaction
# to give agents time to save their work before context is lost.
#
# When Claude Code is about to auto-compact:
#   - Guard enabled: exit 2 (block) + stderr evacuation message
#   - Guard disabled: exit 0 (allow)
# When user triggers manual compaction:
#   - Always exit 0 (allow) regardless of guard state
#
# No counters, no thresholds, no runtime files. The hook is stateless.

set -uo pipefail

# Read hook input from stdin (Claude Code sends JSON with type field)
INPUT=$(cat 2>/dev/null || echo '{}')

# Extract compaction type from hook input
COMPACT_TYPE=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('type', 'auto'))
except:
    print('auto')" 2>/dev/null || echo "auto")

# Manual compaction is always allowed
if [[ "$COMPACT_TYPE" == "manual" ]]; then
    exit 0
fi

# Project root: PURLIN_PROJECT_ROOT > CWD
PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"
RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"

# Role detection for per-agent config
if [[ -z "${AGENT_ROLE:-}" ]] && [[ -f "$RUNTIME_DIR/agent_role" ]]; then
    AGENT_ROLE=$(cat "$RUNTIME_DIR/agent_role" 2>/dev/null || echo "")
fi

# Read per-agent context_guard config via resolver
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="$SCRIPT_DIR/../config/resolve_config.py"

GUARD_ENABLED=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import json, subprocess, sys, os
role = os.environ.get('AGENT_ROLE', '')
try:
    raw = subprocess.check_output(
        [sys.executable, '$RESOLVER', '--dump'],
        env={**os.environ, 'PURLIN_PROJECT_ROOT': '$PROJECT_ROOT'},
        stderr=subprocess.DEVNULL
    )
    cfg = json.loads(raw)
except:
    cfg = {}
agent = cfg.get('agents', {}).get(role, {}) if role else {}
enabled = agent.get('context_guard', True)
print('true' if enabled else 'false')
" 2>/dev/null || echo "true")

# When guard is disabled, allow compaction
if [[ "$GUARD_ENABLED" != "true" ]]; then
    exit 0
fi

# Guard is enabled and this is auto-compaction: block it
echo "CONTEXT GUARD: Auto-compaction blocked. Run /pl-resume save, then /clear, then /pl-resume to continue." >&2
exit 2
