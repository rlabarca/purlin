#!/usr/bin/env bash
# context_guard.sh — PreCompact hook that saves a checkpoint before auto-compaction.
#
# The hook is side-effects-only — it cannot block or prevent compaction.
# It performs a mechanical checkpoint save as a best-effort safety net.
#
# When Claude Code is about to auto-compact:
#   - Guard enabled: save checkpoint file + attempt git commit of staged changes
#   - Guard disabled: exit 0 (no action)
# When user triggers manual compaction:
#   - Always exit 0 (no action) regardless of guard state
#
# The hook MUST always exit with code 0.
# No counters, no thresholds, no runtime files beyond the checkpoint file.

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

# Manual compaction is always allowed without action
if [[ "$COMPACT_TYPE" == "manual" ]]; then
    exit 0
fi

# Project root: PURLIN_PROJECT_ROOT > CLAUDE_PROJECT_DIR > CWD
PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"
CACHE_DIR="$PROJECT_ROOT/.purlin/cache"

# Role detection for per-agent config
if [[ -z "${AGENT_ROLE:-}" ]] && [[ -f "$RUNTIME_DIR/agent_role" ]]; then
    AGENT_ROLE=$(cat "$RUNTIME_DIR/agent_role" 2>/dev/null || echo "")
fi
ROLE="${AGENT_ROLE:-unknown}"

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

# When guard is disabled, allow compaction without action
if [[ "$GUARD_ENABLED" != "true" ]]; then
    exit 0
fi

# --- Guard is enabled and this is auto-compaction: perform mechanical save ---

# Ensure cache directory exists
mkdir -p "$CACHE_DIR" 2>/dev/null || true

# Step 1: Attempt git commit of any staged changes
if git -C "$PROJECT_ROOT" diff --cached --quiet 2>/dev/null; then
    : # Nothing staged, skip
else
    git -C "$PROJECT_ROOT" commit -m "[auto] context guard checkpoint before compaction" 2>&1 >/dev/null || {
        echo "Context Guard: git commit failed (pre-commit hook or other error)" >&2
    }
fi

# Step 2: Write checkpoint file (unique per agent instance to support concurrent agents)
UNIQUE_ID="${PPID:-$$}"
CHECKPOINT_FILE="$CACHE_DIR/session_checkpoint_${ROLE}_${UNIQUE_ID}.md"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
BRANCH=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
GIT_STATUS=$(git -C "$PROJECT_ROOT" status --short 2>/dev/null || echo "")

{
    echo "**Role:** $ROLE"
    echo "**Timestamp:** $TIMESTAMP"
    echo "**Branch:** $BRANCH"
    echo "**Source:** PreCompact hook (auto-compaction safety net)"
    if [[ -z "$GIT_STATUS" ]]; then
        echo "**Uncommitted Changes:** None"
    else
        echo "**Uncommitted Changes:**"
        echo "$GIT_STATUS"
    fi
} > "$CHECKPOINT_FILE"

# Step 3: Status line to stderr
echo "Context Guard: checkpoint saved for $ROLE" >&2

exit 0
