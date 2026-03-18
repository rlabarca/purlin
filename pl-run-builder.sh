#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/purlin"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"

# Source terminal identity helper (no-op if missing)
if [ -f "$CORE_DIR/tools/terminal/identity.sh" ]; then
    source "$CORE_DIR/tools/terminal/identity.sh"
fi

# --- Parse launcher flags ---
CONTINUOUS=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --continuous) CONTINUOUS=true; shift ;;
        *) shift ;;
    esac
done

# --- Prompt assembly ---
PROMPT_FILE=$(mktemp)
PARALLEL_PROMPT_FILE=""
BOOTSTRAP_PROMPT_FILE=""
CANVAS_PID=""
CANVAS_STATE_FILE=""
cleanup() {
    # Clear terminal identity (guarded in case helper was not sourced)
    type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity
    rm -f "$PROMPT_FILE"
    [ -n "$PARALLEL_PROMPT_FILE" ] && rm -f "$PARALLEL_PROMPT_FILE"
    [ -n "$BOOTSTRAP_PROMPT_FILE" ] && rm -f "$BOOTSTRAP_PROMPT_FILE"
    # Kill any active canvas render loop
    if [ -n "$CANVAS_PID" ] && kill -0 "$CANVAS_PID" 2>/dev/null; then
        kill "$CANVAS_PID" 2>/dev/null
    fi
    rm -f "$CANVAS_STATE_FILE" 2>/dev/null
    # Clean up any orphaned continuous-mode worktrees
    if [ "$CONTINUOUS" = "true" ]; then
        for wt_dir in "$SCRIPT_DIR"/continuous-phase-*; do
            [ -d "$wt_dir" ] || continue
            git -C "$SCRIPT_DIR" worktree remove "$wt_dir" --force 2>/dev/null
        done
        git -C "$SCRIPT_DIR" branch --list 'continuous-phase-*' 2>/dev/null | while read -r b; do
            git -C "$SCRIPT_DIR" branch -D "$(echo "$b" | xargs)" 2>/dev/null
        done
    fi
}
trap cleanup EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/BUILDER_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.purlin/BUILDER_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/BUILDER_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# Append continuous mode system prompt overrides
if [ "$CONTINUOUS" = "true" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat >> "$PROMPT_FILE" << 'CONTINUOUS_OVERRIDE'
CONTINUOUS PHASE MODE ACTIVE: You are running in non-interactive print mode.
There is no human user present. You MUST:
- NEVER ask "Ready to go?" or "Ready to resume?" or wait for approval.
- NEVER ask for user input or confirmation of any kind.
- Proceed immediately with your work plan.
- Complete the current delivery plan phase autonomously, then halt as normal.
This override takes precedence over any instruction to "wait for approval"
or "ask the user."
CONTINUOUS_OVERRIDE

    printf "\n\n" >> "$PROMPT_FILE"
    cat >> "$PROMPT_FILE" << 'SERVER_OVERRIDE'
CONTINUOUS PHASE MODE ACTIVE: You have permission to start, stop, and restart
server processes as needed for local verification. You MUST clean up (stop) any
started servers before halting at phase completion. Use dynamic ports where
possible to avoid conflicts.
SERVER_OVERRIDE

    # Create parallel-specific prompt file with amendment instructions
    PARALLEL_PROMPT_FILE=$(mktemp)
    cat "$PROMPT_FILE" > "$PARALLEL_PROMPT_FILE"
    printf "\n\n" >> "$PARALLEL_PROMPT_FILE"
    cat >> "$PARALLEL_PROMPT_FILE" << 'PARALLEL_OVERRIDE'
You are running in a parallel worktree. Do NOT modify the delivery plan directly.
If you need to add, split, or remove phases, write a plan amendment request to
.purlin/runtime/plan_amendment_phase_<N>.json instead, where <N> is your assigned
phase number. Use this JSON format:
{
  "requesting_phase": <N>,
  "amendments": [
    {"action": "add", "phase_number": <new_N>, "label": "...", "features": ["..."], "reason": "..."}
  ]
}
PARALLEL_OVERRIDE
fi

# --- Read agent config via resolver ---
export AGENT_ROLE="builder"
# Persist role to file so hooks can read it (Claude Code doesn't pass env vars to hooks)
mkdir -p "$SCRIPT_DIR/.purlin/runtime"
echo "$AGENT_ROLE" > "$SCRIPT_DIR/.purlin/runtime/agent_role"
RESOLVER="$CORE_DIR/tools/config/resolve_config.py"

AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"

if [ -f "$RESOLVER" ]; then
    eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"
fi

# --- Validate startup controls ---
if [ "$AGENT_FIND_WORK" = "false" ] && [ "$AGENT_AUTO_START" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: find_work=false with auto_start=true is not a valid combination. Set auto_start to false or enable find_work." >&2
    exit 1
fi

# --- Build common CLI args ---
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
fi

# --- Non-continuous mode: original behavior ---
if [ "$CONTINUOUS" = "false" ]; then
    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"
    claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "Begin Builder session."
    exit $?
fi

# ================================================================
# CONTINUOUS MODE
# ================================================================

RUNTIME_DIR="$SCRIPT_DIR/.purlin/runtime"
DELIVERY_PLAN="$SCRIPT_DIR/.purlin/cache/delivery_plan.md"
PHASE_ANALYZER="$CORE_DIR/tools/delivery/phase_analyzer.py"
# Evaluator model: configurable via continuous_evaluator_model in config, defaults to Haiku
HAIKU_MODEL="claude-haiku-4-5-20251001"
EVALUATOR_MODEL="$HAIKU_MODEL"
for cfg_file in "$SCRIPT_DIR/.purlin/config.local.json" "$SCRIPT_DIR/.purlin/config.json"; do
    if [ -f "$cfg_file" ]; then
        _configured_model=$(python3 -c "
import json, sys
try:
    data = json.load(open('$cfg_file'))
    m = data.get('continuous_evaluator_model', '')
    if m:
        print(m)
except (json.JSONDecodeError, IOError, OSError):
    pass
" 2>/dev/null)
        if [ -n "$_configured_model" ]; then
            EVALUATOR_MODEL="$_configured_model"
        fi
        break
    fi
done

# Tracking variables (file-based retry counts for bash 3 compat)
PHASES_COMPLETED=0
PARALLEL_GROUPS_USED=0
GROUPS_EXECUTED=0
TOTAL_RETRIES=0
FAILURES=()
PLAN_AMENDED=false
INITIAL_PENDING_COUNT=0
START_TIME=$(date +%s)

# --- Terminal width detection (Section 2.17) ---
# Main process captures width and writes to shared file. Background subshells
# read from the file instead of calling tput cols (which returns 80 in bg).
TERM_WIDTH_FILE="${RUNTIME_DIR}/term_width"
mkdir -p "$RUNTIME_DIR" 2>/dev/null

detect_term_cols() {
    local cols
    # 1. Query kernel TTY driver directly — most reliable on macOS
    cols=$(stty size </dev/tty 2>/dev/null | awk '{print $2}')
    if [ -n "$cols" ] && [ "$cols" -gt 0 ] 2>/dev/null; then echo "$cols"; return; fi
    # 2. terminfo-based fallback
    cols=$(tput cols 2>/dev/null)
    if [ -n "$cols" ] && [ "$cols" -gt 0 ] 2>/dev/null; then echo "$cols"; return; fi
    # 3. Shell variable (rarely exported but worth trying)
    if [ -n "$COLUMNS" ] && [ "$COLUMNS" -gt 0 ] 2>/dev/null; then echo "$COLUMNS"; return; fi
    # 4. Last resort
    echo 80
}

if [ -n "$PURLIN_TERM_COLS" ] && [ "$PURLIN_TERM_COLS" -gt 0 ] 2>/dev/null; then
    : # Respect explicit user override
else
    PURLIN_TERM_COLS=$(detect_term_cols)
fi
echo "$PURLIN_TERM_COLS" > "$TERM_WIDTH_FILE"
export PURLIN_TERM_COLS

update_term_width() {
    PURLIN_TERM_COLS=$(detect_term_cols)
    echo "$PURLIN_TERM_COLS" > "$TERM_WIDTH_FILE"
    export PURLIN_TERM_COLS
}
trap update_term_width WINCH

# --- Startup purge: delete stale runtime artifacts from previous run (Section 2.11) ---
purge_stale_runtime_artifacts() {
    rm -f "${RUNTIME_DIR}"/phase_*_meta 2>/dev/null
    rm -f "${RUNTIME_DIR}"/canvas_frozen_* 2>/dev/null
    rm -f "${RUNTIME_DIR}"/retry_count_* 2>/dev/null
    rm -f "${RUNTIME_DIR}"/plan_amendment_phase_*.json 2>/dev/null
    rm -f "${RUNTIME_DIR}/approval_table_lines" 2>/dev/null
    rm -f "${RUNTIME_DIR}"/continuous_build_*.log 2>/dev/null
}
purge_stale_runtime_artifacts

# --- Helper: check if all delivery plan phases are COMPLETE ---
all_phases_complete() {
    [ -f "$DELIVERY_PLAN" ] || return 1
    local total complete
    total=$(python3 -c "
import re
with open('$DELIVERY_PLAN') as f:
    content = f.read()
print(len(re.findall(r'## Phase \d+ -- .+? \[(PENDING|IN_PROGRESS|COMPLETE)\]', content)))
" 2>/dev/null || echo "0")
    complete=$(python3 -c "
import re
with open('$DELIVERY_PLAN') as f:
    content = f.read()
print(len(re.findall(r'## Phase \d+ -- .+? \[COMPLETE\]', content)))
" 2>/dev/null || echo "0")
    [ "$total" -gt 0 ] && [ "$total" = "$complete" ]
}

# --- Startup cleanup: remove stale all-COMPLETE delivery plan ---
# If every phase is COMPLETE, the previous run failed to clean up.
# Delete the plan so bootstrap can create a fresh one if needed.
if all_phases_complete; then
    echo "Removing fully-completed delivery plan from previous run." >&2
    rm -f "$DELIVERY_PLAN"
    git -C "$SCRIPT_DIR" add "$DELIVERY_PLAN" 2>/dev/null
    git -C "$SCRIPT_DIR" commit -m "chore: remove stale delivery plan (all phases already complete)" 2>/dev/null
fi

# Evaluator JSON schema
EVALUATOR_SCHEMA='{"type":"object","properties":{"action":{"type":"string","enum":["continue","retry","approve","stop"]},"success":{"type":"boolean"},"reason":{"type":"string"}},"required":["action","success","reason"]}'

# --- Helper: log evaluator decision with timestamp ---
log_eval() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] EVALUATOR: $1" >&2
}

# --- Helper: compute hash of delivery plan ---
get_plan_hash() {
    if [ -f "$DELIVERY_PLAN" ]; then
        md5 -q "$DELIVERY_PLAN" 2>/dev/null || md5sum "$DELIVERY_PLAN" 2>/dev/null | cut -d' ' -f1
    else
        echo ""
    fi
}

# --- Helper: run the LLM evaluator ---
# Returns "action|reason" on success, exits 1 on failure
run_evaluator() {
    local log_file="$1"
    local tail_output
    tail_output=$(tail -200 "$log_file" 2>/dev/null || echo "")

    local plan_content=""
    if [ -f "$DELIVERY_PLAN" ]; then
        plan_content=$(cat "$DELIVERY_PLAN")
    fi

    local eval_msg_file
    eval_msg_file=$(mktemp)
    cat > "$eval_msg_file" << EVAL_EOF
You are a build orchestration evaluator. Analyze the Builder's output and decide the next action.

## Builder Output (last 200 lines):
${tail_output}

## Current Delivery Plan:
${plan_content}

## Classification Rules:
- "Phase N of M complete" + delivery plan updated -> action: "continue", success: false
- Builder amended the delivery plan (new/split/modified phases) + phase complete -> action: "continue", success: false
- "Ready to go?" / "Ready to resume?" (approval prompt) -> action: "approve", success: false
- Context exhaustion / checkpoint saved mid-phase -> action: "retry", success: false
- Partial progress (features done but phase incomplete) -> action: "retry", success: false
- Builder output mentions plan amendment but current phase not complete -> action: "retry", success: false
- Error requiring human input (INFEASIBLE, missing fixture) -> action: "stop", success: false
- All phases complete / delivery plan deleted -> action: "stop", success: true
- No meaningful progress detected -> action: "stop", success: false

The "success" field MUST be true ONLY when action is "stop" AND all work completed successfully. For all other cases, success MUST be false.

Return a JSON object with "action", "success", and "reason" fields.
EVAL_EOF

    local eval_result eval_rc
    # 30-second timeout (Section 2.5): platform-aware fallback
    if command -v timeout >/dev/null 2>&1; then
        eval_result=$(timeout 30 claude --print --model "$EVALUATOR_MODEL" --json-schema "$EVALUATOR_SCHEMA" < "$eval_msg_file" 2>/dev/null)
        eval_rc=$?
    elif command -v gtimeout >/dev/null 2>&1; then
        eval_result=$(gtimeout 30 claude --print --model "$EVALUATOR_MODEL" --json-schema "$EVALUATOR_SCHEMA" < "$eval_msg_file" 2>/dev/null)
        eval_rc=$?
    else
        # macOS fallback: background process with kill after 30s
        claude --print --model "$EVALUATOR_MODEL" --json-schema "$EVALUATOR_SCHEMA" < "$eval_msg_file" > "${eval_msg_file}.out" 2>/dev/null &
        local eval_pid=$!
        local waited=0
        while kill -0 "$eval_pid" 2>/dev/null && [ "$waited" -lt 30 ]; do
            sleep 1
            waited=$((waited + 1))
        done
        if kill -0 "$eval_pid" 2>/dev/null; then
            kill "$eval_pid" 2>/dev/null
            wait "$eval_pid" 2>/dev/null
            eval_rc=124  # same as timeout exit code
            eval_result=""
        else
            wait "$eval_pid" 2>/dev/null
            eval_rc=$?
            eval_result=$(cat "${eval_msg_file}.out" 2>/dev/null)
        fi
        rm -f "${eval_msg_file}.out" 2>/dev/null
    fi
    rm -f "$eval_msg_file"

    if [ $eval_rc -ne 0 ] || [ -z "$eval_result" ]; then
        return 1
    fi

    local parsed
    parsed=$(printf '%s' "$eval_result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    success = 'true' if data.get('success', False) else 'false'
    print(data['action'] + '|' + success + '|' + data['reason'])
except (json.JSONDecodeError, KeyError):
    sys.exit(1)
" 2>/dev/null) || return 1

    echo "$parsed"
    return 0
}

# --- Helper: evaluator fallback (delivery plan hash check + pending phase check) ---
evaluator_fallback() {
    local plan_hash_before="$1"
    local plan_hash_after
    plan_hash_after=$(get_plan_hash)

    if [ "$plan_hash_before" != "$plan_hash_after" ]; then
        echo "continue|false|evaluator fallback: delivery plan changed"
        return 0
    fi

    # Hash unchanged does NOT mean work is done — the orchestrator may have
    # already committed plan updates before the fallback runs (parallel groups).
    # Check whether PENDING phases remain as a second signal.
    if [ -f "$DELIVERY_PLAN" ]; then
        local pending_count
        pending_count=$(grep -c '\[PENDING\]' "$DELIVERY_PLAN" 2>/dev/null || echo "0")
        if [ "$pending_count" -gt 0 ]; then
            echo "continue|false|evaluator fallback: $pending_count PENDING phase(s) remain"
            return 0
        fi
    fi

    echo "stop|false|evaluator fallback: delivery plan unchanged and no PENDING phases"
}

# --- Helper: format seconds as Xm Ys ---
format_duration() {
    local secs="$1"
    local mins=$((secs / 60))
    local rem=$((secs % 60))
    if [ "$mins" -gt 0 ]; then
        echo "${mins}m ${rem}s"
    else
        echo "${secs}s"
    fi
}

# --- Helper: extract phase label from delivery plan ---
extract_phase_label() {
    local phase_num="$1"
    sed -n "s/## Phase ${phase_num} -- \(.*\) \[.*/\1/p" "$DELIVERY_PLAN" 2>/dev/null | head -1
}

# --- Helper: extract phase features from delivery plan ---
extract_phase_features() {
    local phase_num="$1"
    python3 -c "
import re, sys
try:
    with open(sys.argv[1]) as f:
        content = f.read()
    m = re.search(r'## Phase ' + sys.argv[2] + r' -- .*?\n\*\*Features:\*\* (.*?)(?:\n|\$)', content)
    print(m.group(1).strip() if m else '--')
except Exception:
    print('--')
" "$DELIVERY_PLAN" "$phase_num" 2>/dev/null || echo "--"
}

# --- Helper: extract current activity from log file tail ---
extract_activity() {
    local log_file="$1"
    [ -f "$log_file" ] || { echo "working..."; return; }
    local tail_content
    tail_content=$(tail -20 "$log_file" 2>/dev/null) || { echo "working..."; return; }
    local fname
    fname=$(echo "$tail_content" | grep -oE '[a-zA-Z0-9_.-]+\.(md|py|sh|js|ts|json|html|css)' | tail -1)
    if [ -n "$fname" ]; then
        printf "editing %s" "$fname"
        return
    fi
    local cmd_match
    cmd_match=$(echo "$tail_content" | grep -oE 'running [a-zA-Z0-9_ -]+' | tail -1)
    if [ -n "$cmd_match" ]; then
        printf "%s" "$cmd_match"
        return
    fi
    # Log tail fallback: last non-empty, non-whitespace-only line, stripped of ANSI codes
    local last_line
    last_line=$(tail -5 "$log_file" 2>/dev/null | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' | grep -v '^[[:space:]]*$' | tail -1)
    if [ -n "$last_line" ]; then
        printf "%s" "$last_line"
        return
    fi
    echo "working..."
}

# --- Helper: record phase start metadata ---
record_phase_start() {
    local phase_num="$1"
    local label features
    label=$(extract_phase_label "$phase_num")
    features=$(extract_phase_features "$phase_num")
    cat > "${RUNTIME_DIR}/phase_${phase_num}_meta" << META_EOF
LABEL=${label}
FEATURES=${features}
STATUS=RUNNING
START_TIME=$(date +%s)
END_TIME=
META_EOF
}

# --- Helper: record phase end metadata ---
record_phase_end() {
    local phase_num="$1"
    local status="$2"
    local meta_file="${RUNTIME_DIR}/phase_${phase_num}_meta"
    [ -f "$meta_file" ] || return
    local label features start_time
    label=$(grep '^LABEL=' "$meta_file" | cut -d= -f2-)
    features=$(grep '^FEATURES=' "$meta_file" | cut -d= -f2-)
    start_time=$(grep '^START_TIME=' "$meta_file" | cut -d= -f2-)
    cat > "$meta_file" << META_EOF
LABEL=${label}
FEATURES=${features}
STATUS=${status}
START_TIME=${start_time}
END_TIME=$(date +%s)
META_EOF
}

# --- Helper: mark phases as IN_PROGRESS before launching Builders ---
mark_phases_in_progress() {
    [ -f "$DELIVERY_PLAN" ] || return 0
    local phases=("$@")
    python3 -c "
import re, sys
phases = sys.argv[1:]
with open('$DELIVERY_PLAN', 'r') as f:
    content = f.read()
for p in phases:
    content = re.sub(
        r'(## Phase ' + p + r' -- .+?) \[PENDING\]',
        r'\1 [IN_PROGRESS]',
        content
    )
with open('$DELIVERY_PLAN', 'w') as f:
    f.write(content)
" "${phases[@]}" 2>/dev/null
    git -C "$SCRIPT_DIR" add "$DELIVERY_PLAN" 2>/dev/null
    git -C "$SCRIPT_DIR" commit -m "chore: mark phases ${phases[*]} as IN_PROGRESS" 2>/dev/null
}

# --- Helper: run a command with line-buffered output to a log file ---
# Usage: run_to_log <logfile> [--append] <command> [args...]
# Fallback chain: stdbuf -oL (Linux) -> script -q /dev/null (macOS) -> unbuffered with warning
#
# macOS: script(1) creates a pseudo-TTY that forces line buffering. Output
# flows through script's stdout (redirected to the log file). The typescript
# file arg is /dev/null (discarded) to avoid duplication.
#
# IMPORTANT: In parallel subshells, the PTY master may leak to the
# controlling terminal. Callers MUST wrap parallel invocations in
# `) > /dev/null 2>&1 &` to contain any leakage (see Section 2.4).
run_to_log() {
    local LOG_FILE="$1"; shift
    local APPEND=false
    if [ "$1" = "--append" ]; then
        APPEND=true; shift
    fi

    if command -v stdbuf >/dev/null 2>&1; then
        if [ "$APPEND" = "true" ]; then
            stdbuf -oL "$@" >> "$LOG_FILE" 2>&1
        else
            stdbuf -oL "$@" > "$LOG_FILE" 2>&1
        fi
    elif command -v script >/dev/null 2>&1; then
        # macOS: script forces pseudo-TTY line buffering. stdin from /dev/null
        # prevents script consuming parent stdin (all builders are non-interactive).
        if [ "$APPEND" = "true" ]; then
            script -q /dev/null "$@" </dev/null >> "$LOG_FILE" 2>&1
        else
            script -q /dev/null "$@" </dev/null > "$LOG_FILE" 2>&1
        fi
    else
        echo "Warning: Neither stdbuf nor script available. Log monitoring will be degraded (full buffering)." >&2
        if [ "$APPEND" = "true" ]; then
            "$@" >> "$LOG_FILE" 2>&1
        else
            "$@" > "$LOG_FILE" 2>&1
        fi
    fi
}

# --- Helper: update delivery plan phase status ---
update_plan_phase_status() {
    local phase_num="$1"
    local commit_hash
    commit_hash=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || echo "--")

    [ -f "$DELIVERY_PLAN" ] || return 0

    python3 -c "
import re

with open('$DELIVERY_PLAN', 'r') as f:
    content = f.read()

# Update status from PENDING/IN_PROGRESS to COMPLETE
content = re.sub(
    r'(## Phase $phase_num -- .+?) \[(?:PENDING|IN_PROGRESS)\]',
    r'\1 [COMPLETE]',
    content
)

# Phase-aware completion commit: find the phase heading, then update the
# next Completion Commit line after it (avoids clobbering other phases).
m = re.search(r'## Phase $phase_num -- ', content)
if m:
    before = content[:m.start()]
    after = content[m.start():]
    after = re.sub(
        r'(\*\*Completion Commit:\*\*) --',
        r'\1 $commit_hash',
        after,
        count=1
    )
    content = before + after

with open('$DELIVERY_PLAN', 'w') as f:
    f.write(content)
" 2>/dev/null
}

# --- Helper: apply plan amendment files after parallel merge ---
apply_plan_amendments() {
    local any_applied=false
    for amend_file in "$RUNTIME_DIR"/plan_amendment_phase_*.json; do
        [ -f "$amend_file" ] || continue
        any_applied=true

        python3 -c "
import json, re, sys

with open('$amend_file') as f:
    request = json.load(f)

with open('$DELIVERY_PLAN') as f:
    plan_content = f.read()

for amendment in request.get('amendments', []):
    action = amendment['action']
    if action == 'add':
        phase_num = amendment.get('phase_number', 99)
        label = amendment.get('label', 'Untitled')
        features = ', '.join(amendment.get('features', []))
        reason = amendment.get('reason', '')
        new_section = '\n## Phase {} -- {} [PENDING]\n'.format(phase_num, label)
        new_section += '**Features:** {}\n'.format(features)
        new_section += '**Completion Commit:** --\n'
        new_section += '**QA Bugs Addressed:** --\n'
        if reason:
            new_section += '**Amendment Reason:** {}\n'.format(reason)
        marker = '## Plan Amendments'
        if marker in plan_content:
            plan_content = plan_content.replace(marker, new_section + '\n' + marker)
        else:
            plan_content += '\n' + new_section
    elif action == 'remove':
        phase_num = amendment.get('phase_number', 0)
        plan_content = re.sub(
            r'(## Phase {} -- .+?) \[PENDING\]'.format(phase_num),
            r'\1 [REMOVED]',
            plan_content
        )

with open('$DELIVERY_PLAN', 'w') as f:
    f.write(plan_content)
" 2>/dev/null

        rm -f "$amend_file"
    done

    if [ "$any_applied" = "true" ]; then
        PLAN_AMENDED=true
        log_eval "Applied plan amendments from parallel builders"
    fi
}

# ================================================================
# Terminal Canvas Engine (Section 2.17)
# ================================================================
# All continuous mode status output renders into an in-place terminal
# canvas on stderr. The canvas is cleared and rewritten via ANSI cursor
# control. Only the final exit summary is permanent output.

SPINNER=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)

# --- Canvas: clear the canvas from the parent process ---
canvas_clear() {
    if [ -t 2 ] && [ -n "$CANVAS_STATE_FILE" ] && [ -f "$CANVAS_STATE_FILE" ]; then
        local lines
        lines=$(cat "$CANVAS_STATE_FILE" 2>/dev/null)
        if [ -n "$lines" ] && [ "$lines" -gt 0 ] 2>/dev/null; then
            # \r ensures cursor is at column 0 (safe if killed mid-line)
            printf '\r\033[%dA\033[J' "$lines" >&2
        fi
    fi
    rm -f "$CANVAS_STATE_FILE" 2>/dev/null
}

# --- Canvas: stop the render loop and clear ---
stop_canvas() {
    if [ -n "$CANVAS_PID" ] && kill -0 "$CANVAS_PID" 2>/dev/null; then
        kill "$CANVAS_PID" 2>/dev/null
        wait "$CANVAS_PID" 2>/dev/null
    fi
    canvas_clear
    CANVAS_PID=""
}

# --- Canvas: non-TTY fallback milestone line ---
canvas_milestone() {
    echo "$1" >&2
}

# --- Canvas: start bootstrap spinner ---
start_bootstrap_canvas() {
    CANVAS_STATE_FILE="${RUNTIME_DIR}/canvas_state"
    rm -f "$CANVAS_STATE_FILE" 2>/dev/null
    if ! [ -t 2 ]; then
        canvas_milestone "Bootstrap started"
        return
    fi
    local start_secs=$SECONDS
    (
        idx=0; prev_lines=0
        while true; do
            elapsed=$((SECONDS - start_secs))
            s="${SPINNER[$((idx % 10))]}"
            if [ "$prev_lines" -gt 0 ]; then
                printf '\033[%dA\033[J' "$prev_lines" >&2
            fi
            printf '\033[36m%s\033[0m Bootstrapping for continuous delivery... \033[2m%ss\033[0m\n' "$s" "$elapsed" >&2
            prev_lines=1
            echo "$prev_lines" > "$CANVAS_STATE_FILE"
            idx=$((idx + 1))
            sleep 0.1
        done
    ) &
    CANVAS_PID=$!
}

# --- Canvas: start sequential phase spinner ---
start_sequential_canvas() {
    local phase_num="$1"
    local log_file="$2"
    CANVAS_STATE_FILE="${RUNTIME_DIR}/canvas_state"
    rm -f "$CANVAS_STATE_FILE" 2>/dev/null
    if ! [ -t 2 ]; then
        canvas_milestone "Phase $phase_num started"
        return
    fi
    local phase_label
    phase_label=$(extract_phase_label "$phase_num")
    [ -z "$phase_label" ] && phase_label="Phase $phase_num"
    local start_secs=$SECONDS
    (
        idx=0; prev_lines=0; heavy_counter=0
        activity="working..."
        fsize="0K"
        while true; do
            elapsed=$((SECONDS - start_secs))
            elapsed_str=$(format_duration "$elapsed")
            s="${SPINNER[$((idx % 10))]}"

            # Heavier updates every 15 seconds (~150 iterations)
            heavy_counter=$((heavy_counter + 1))
            if [ "$heavy_counter" -ge 150 ]; then
                heavy_counter=0
                if [ -f "$log_file" ]; then
                    bytes=$(wc -c < "$log_file" 2>/dev/null | tr -d ' ')
                    fsize="$((bytes / 1024))K"
                fi
                activity=$(extract_activity "$log_file")
            fi

            # Terminal width constraint: truncate activity first, then label
            # Read from shared file — tput cols returns 80 in background subshells
            term_cols=$(cat "$TERM_WIDTH_FILE" 2>/dev/null || echo "${PURLIN_TERM_COLS:-80}")
            disp_label="$phase_label"
            disp_activity="$activity"
            prefix_part="Phase ${phase_num} -- "
            status_part="   running  ${elapsed_str}   ${fsize}  "
            fixed_w=$((2 + ${#prefix_part} + ${#status_part}))
            avail=$((term_cols - fixed_w))
            if [ $((${#disp_label} + ${#disp_activity})) -gt "$avail" ]; then
                act_avail=$((avail - ${#disp_label}))
                if [ "$act_avail" -ge 4 ]; then
                    disp_activity="${disp_activity:0:$((act_avail - 3))}..."
                else
                    disp_activity=""
                    if [ "$avail" -ge 4 ]; then
                        disp_label="${disp_label:0:$((avail - 3))}..."
                    elif [ "$avail" -ge 0 ]; then
                        disp_label="${disp_label:0:$avail}"
                    fi
                fi
            fi

            if [ "$prev_lines" -gt 0 ]; then
                printf '\033[%dA\033[J' "$prev_lines" >&2
            fi
            printf '\033[36m%s\033[0m \033[1;37mPhase %s -- %s\033[0m   \033[33mrunning\033[0m  \033[2m%s\033[0m   %s  %s\n' \
                "$s" "$phase_num" "$disp_label" "$elapsed_str" "$fsize" "$disp_activity" >&2
            prev_lines=1
            echo "$prev_lines" > "$CANVAS_STATE_FILE"
            idx=$((idx + 1))
            sleep 0.1
        done
    ) &
    CANVAS_PID=$!
}

# --- Canvas: start inter-phase spinner (evaluator/re-analysis) ---
start_interphase_canvas() {
    local message="$1"
    CANVAS_STATE_FILE="${RUNTIME_DIR}/canvas_state"
    rm -f "$CANVAS_STATE_FILE" 2>/dev/null
    if ! [ -t 2 ]; then
        return
    fi
    local start_secs=$SECONDS
    (
        idx=0; prev_lines=0
        while true; do
            elapsed=$((SECONDS - start_secs))
            s="${SPINNER[$((idx % 10))]}"
            if [ "$prev_lines" -gt 0 ]; then
                printf '\033[%dA\033[J' "$prev_lines" >&2
            fi
            printf '\033[36m%s\033[0m %s \033[2m%ss\033[0m\n' "$s" "$message" "$elapsed" >&2
            prev_lines=1
            echo "$prev_lines" > "$CANVAS_STATE_FILE"
            idx=$((idx + 1))
            sleep 0.1
        done
    ) &
    CANVAS_PID=$!
}

# --- Canvas: start parallel group canvas ---
start_parallel_canvas() {
    # Args: WT_PHASES_STR WT_LOGS_STR WT_PIDS_STR (space-separated)
    local phases_str="$1"
    local logs_str="$2"
    local pids_str="$3"
    CANVAS_STATE_FILE="${RUNTIME_DIR}/canvas_state"
    rm -f "$CANVAS_STATE_FILE" 2>/dev/null

    if ! [ -t 2 ]; then
        canvas_milestone "Parallel group started: Phases $phases_str"
        return
    fi

    # Initialize frozen end time files (bash 3 compat)
    for pnum in $phases_str; do
        rm -f "${RUNTIME_DIR}/canvas_frozen_${pnum}" 2>/dev/null
    done

    local start_secs=$SECONDS
    (
        # Convert space-separated strings to arrays inside the subshell
        read -ra P_PHASES <<< "$phases_str"
        read -ra P_LOGS <<< "$logs_str"
        read -ra P_PIDS <<< "$pids_str"

        idx=0; prev_lines=0; heavy_counter=0

        # Arrays for cached heavy data (indexed same as P_PHASES)
        declare -a P_FSIZE
        declare -a P_ACTIVITY
        for i in "${!P_PHASES[@]}"; do
            P_FSIZE[$i]="0K"
            P_ACTIVITY[$i]="working..."
        done

        while true; do
            TIMESTAMP=$(date +%H:%M:%S)
            s="${SPINNER[$((idx % 10))]}"

            # Read terminal width each cycle for resize adaptation
            # Read from shared file — tput cols returns 80 in background subshells
            term_cols=$(cat "$TERM_WIDTH_FILE" 2>/dev/null || echo "${PURLIN_TERM_COLS:-80}")

            # Heavier updates every 15 seconds (~150 iterations)
            heavy_counter=$((heavy_counter + 1))
            do_heavy=false
            if [ "$heavy_counter" -ge 150 ]; then
                heavy_counter=0
                do_heavy=true
            fi

            # --- Pass 1: collect data and compute max widths for column alignment ---
            declare -a R_LABEL R_STATUS R_ELAPSED R_FSIZE R_ACT R_COLOR R_PNUM_STR
            MAX_LABEL_W=0
            MAX_STATUS_W=0
            MAX_ELAPSED_W=0
            MAX_FSIZE_W=0
            MAX_PNUM_W=0

            for i in "${!P_PHASES[@]}"; do
                PNUM="${P_PHASES[$i]}"
                LFILE="${P_LOGS[$i]}"
                PID_VAL="${P_PIDS[$i]}"

                R_PNUM_STR[$i]="$PNUM"
                [ ${#PNUM} -gt $MAX_PNUM_W ] && MAX_PNUM_W=${#PNUM}

                PLABEL=$(sed -n "s/## Phase ${PNUM} -- \(.*\) \[.*/\1/p" "$DELIVERY_PLAN" 2>/dev/null | head -1)
                [ -z "$PLABEL" ] && PLABEL="Phase ${PNUM}"
                R_LABEL[$i]="$PLABEL"
                [ ${#PLABEL} -gt $MAX_LABEL_W ] && MAX_LABEL_W=${#PLABEL}

                # Update heavy data on interval
                if [ "$do_heavy" = "true" ]; then
                    if [ -f "$LFILE" ]; then
                        BYTES=$(wc -c < "$LFILE" 2>/dev/null | tr -d ' ')
                        P_FSIZE[$i]="$((BYTES / 1024))K"
                    fi
                    if kill -0 "$PID_VAL" 2>/dev/null; then
                        P_ACTIVITY[$i]=$(extract_activity "$LFILE")
                    fi
                fi
                R_FSIZE[$i]="${P_FSIZE[$i]}"
                [ ${#P_FSIZE[$i]} -gt $MAX_FSIZE_W ] && MAX_FSIZE_W=${#P_FSIZE[$i]}

                # Compute elapsed
                ELAPSED=""
                PSTART=""
                META_FILE="${RUNTIME_DIR}/phase_${PNUM}_meta"
                [ -f "$META_FILE" ] && PSTART=$(grep '^START_TIME=' "$META_FILE" | cut -d= -f2-)
                if [ -n "$PSTART" ]; then
                    NOW_TS=$(date +%s)
                    if kill -0 "$PID_VAL" 2>/dev/null; then
                        SECS=$((NOW_TS - PSTART))
                    else
                        FROZEN_FILE="${RUNTIME_DIR}/canvas_frozen_${PNUM}"
                        if [ ! -f "$FROZEN_FILE" ]; then
                            echo "$NOW_TS" > "$FROZEN_FILE"
                            FEND=$NOW_TS
                        else
                            FEND=$(cat "$FROZEN_FILE")
                        fi
                        SECS=$((FEND - PSTART))
                    fi
                    MINS=$((SECS / 60))
                    REM=$((SECS % 60))
                    [ "$MINS" -gt 0 ] && ELAPSED="${MINS}m ${REM}s" || ELAPSED="${SECS}s"
                fi
                R_ELAPSED[$i]="$ELAPSED"
                [ ${#ELAPSED} -gt $MAX_ELAPSED_W ] && MAX_ELAPSED_W=${#ELAPSED}

                # Compute status and color
                if kill -0 "$PID_VAL" 2>/dev/null; then
                    R_STATUS[$i]="running"
                    R_COLOR[$i]="\033[38;5;208m"
                    R_ACT[$i]="${P_ACTIVITY[$i]}"
                else
                    R_STATUS[$i]="done"
                    R_ACT[$i]=""
                    if [ "${P_FSIZE[$i]}" = "0K" ]; then
                        R_COLOR[$i]="\033[31m"
                    else
                        R_COLOR[$i]="\033[32m"
                    fi
                fi
                [ ${#R_STATUS[$i]} -gt $MAX_STATUS_W ] && MAX_STATUS_W=${#R_STATUS[$i]}
            done

            # --- Compute effective column widths to fit terminal (Section 2.17) ---
            # 2-space indent per spec (not 13 — avoids wasting horizontal space)
            prefix_w=$((2 + 6 + MAX_PNUM_W + 4))
            status_w=$((3 + MAX_STATUS_W + 2 + MAX_ELAPSED_W + 3 + MAX_FSIZE_W + 2))
            avail=$((term_cols - prefix_w - status_w))
            # Cap label width so padded fields + label fit within term_cols
            EFF_LABEL_W=$MAX_LABEL_W
            if [ "$EFF_LABEL_W" -gt "$avail" ]; then
                [ "$avail" -ge 0 ] && EFF_LABEL_W=$avail || EFF_LABEL_W=0
            fi
            ACT_AVAIL=$((avail - EFF_LABEL_W))
            [ "$ACT_AVAIL" -lt 0 ] && ACT_AVAIL=0

            # --- Pass 2: render with aligned columns ---
            OUTPUT="[$TIMESTAMP] Parallel group (${#P_PHASES[@]} phases):"$'\n'
            LINE_COUNT=1

            for i in "${!P_PHASES[@]}"; do
                PNUM_PADDED=$(printf "%-${MAX_PNUM_W}s" "${R_PNUM_STR[$i]}")
                STATUS_PADDED=$(printf "%-${MAX_STATUS_W}s" "${R_STATUS[$i]}")
                ELAPSED_PADDED=$(printf "%-${MAX_ELAPSED_W}s" "${R_ELAPSED[$i]}")
                FSIZE_PADDED=$(printf "%-${MAX_FSIZE_W}s" "${R_FSIZE[$i]}")

                # Label: truncate to EFF_LABEL_W, then pad
                LBL="${R_LABEL[$i]}"
                if [ ${#LBL} -gt "$EFF_LABEL_W" ] && [ "$EFF_LABEL_W" -ge 4 ]; then
                    LBL="${LBL:0:$((EFF_LABEL_W - 3))}..."
                elif [ ${#LBL} -gt "$EFF_LABEL_W" ]; then
                    LBL="${LBL:0:$EFF_LABEL_W}"
                fi
                LABEL_PADDED=$(printf "%-${EFF_LABEL_W}s" "$LBL")

                # Activity: truncate to ACT_AVAIL (fills remaining terminal width)
                DISP_ACT="${R_ACT[$i]}"
                if [ ${#DISP_ACT} -gt "$ACT_AVAIL" ]; then
                    if [ "$ACT_AVAIL" -ge 4 ]; then
                        DISP_ACT="${DISP_ACT:0:$((ACT_AVAIL - 3))}..."
                    elif [ "$ACT_AVAIL" -gt 0 ]; then
                        DISP_ACT="${DISP_ACT:0:$ACT_AVAIL}"
                    else
                        DISP_ACT=""
                    fi
                fi

                OUTPUT+="  ${R_COLOR[$i]}Phase ${PNUM_PADDED} -- ${LABEL_PADDED}   ${STATUS_PADDED}  ${ELAPSED_PADDED}   ${FSIZE_PADDED}  ${DISP_ACT}\033[0m"$'\n'
                LINE_COUNT=$((LINE_COUNT + 1))
            done

            # In-place overwrite via cursor-up and clear
            if [ "$prev_lines" -gt 0 ]; then
                printf '\033[%dA\033[J' "$prev_lines" >&2
            fi
            printf '%b' "$OUTPUT" >&2
            prev_lines=$LINE_COUNT
            echo "$prev_lines" > "$CANVAS_STATE_FILE"
            idx=$((idx + 1))
            sleep 0.1
        done
    ) &
    CANVAS_PID=$!
}

# --- Canvas: render approval checkpoint table ---
# Renders with dynamic column widths and cell wrapping (max 2 lines per cell).
# Writes rendered line count to APPROVAL_TABLE_LINES_FILE for SIGWINCH re-render.
APPROVAL_TABLE_LINES_FILE="${RUNTIME_DIR}/approval_table_lines"

render_approval_table() {
    local analyzer_json
    analyzer_json=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>/dev/null)

    python3 -c "
import json, re, sys, os

plan_path = sys.argv[1]
is_tty = sys.argv[2] == 'true'
lines_file = sys.argv[3]

try:
    analyzer = json.loads(sys.argv[4])
except (json.JSONDecodeError, IndexError):
    analyzer = {'groups': []}

with open(plan_path) as f:
    plan_content = f.read()

phases_info = {}
for m in re.finditer(r'## Phase (\d+) -- (.+?) \[(PENDING|IN_PROGRESS|COMPLETE)\]', plan_content):
    pnum = int(m.group(1))
    label = m.group(2).strip()
    feat_m = re.search(r'## Phase {} -- .*?\n\*\*Features:\*\* (.*?)(?:\n|\$)'.format(pnum), plan_content)
    features = feat_m.group(1).strip() if feat_m else '--'
    phases_info[pnum] = {'label': label, 'features': features}

group_map = {}
for gi, group in enumerate(analyzer.get('groups', [])):
    for p in group.get('phases', []):
        group_map[p] = (gi, group.get('parallel', False))

try:
    cols = int(os.environ.get('PURLIN_TERM_COLS', '80'))
except (ValueError, TypeError):
    cols = 80

total_phases = len(phases_info)
parallel_groups = []
seen_groups = set()
for gi, group in enumerate(analyzer.get('groups', [])):
    if group.get('parallel', False) and gi not in seen_groups:
        seen_groups.add(gi)
        parallel_groups.append(group['phases'])

BOLD_CYAN = '\033[1;36m' if is_tty else ''
GREEN = '\033[32m' if is_tty else ''
RESET = '\033[0m' if is_tty else ''

STACKED_THRESHOLD = 60

out = []
out.append('{0}=== Delivery Plan ({1} phases) ==={2}'.format(BOLD_CYAN, total_phases, RESET)[:cols])
out.append('')

if cols < STACKED_THRESHOLD:
    # Stacked single-column layout for narrow terminals (Section 2.16)
    val_indent = 2
    for pnum in sorted(phases_info.keys()):
        info = phases_info[pnum]
        exec_group = '--'
        if pnum in group_map:
            gi, par = group_map[pnum]
            if par:
                others = [str(p) for p in analyzer['groups'][gi]['phases'] if p != pnum]
                exec_group = '{0} (parallel w/ {1})'.format(gi, ', '.join(others))
            else:
                exec_group = '{0} (sequential)'.format(gi)
        hdr_line = BOLD_CYAN + 'Phase ' + str(pnum) + RESET
        out.append(hdr_line[:cols + len(BOLD_CYAN) + len(RESET)])
        for field_name, field_val in [('Label', info['label']), ('Features', info['features']), ('Exec Group', exec_group)]:
            line = '{0}{1}: {2}'.format(' ' * val_indent, field_name, field_val)
            out.append(line[:cols])
        out.append('')
else:
    # Dynamic column widths: # = 4 fixed, remaining split proportionally
    # 2 leading spaces + 3 inter-column spaces
    fixed_overhead = 2 + 4 + 3
    remaining = max(cols - fixed_overhead, 30)
    label_w = max(int(remaining * 0.30), 8)
    feat_w = max(int(remaining * 0.45), 10)
    exec_w = max(remaining - label_w - feat_w, 8)

    def wrap_cell(text, width):
        if len(text) <= width:
            return [text]
        line1 = text[:width]
        rest = text[width:]
        if len(rest) <= width:
            return [line1, rest]
        return [line1, rest[:max(width - 3, 0)] + '...']

    hdr = '  {:<4s} {:<{}s} {:<{}s} {:<{}s}'.format('#', 'Label', label_w, 'Features', feat_w, 'Exec Group', exec_w)
    out.append('{0}{1}{2}'.format(BOLD_CYAN, hdr[:cols].ljust(cols), RESET))
    sep = '  {:<4s} {:<{}s} {:<{}s} {:<{}s}'.format('---', '-' * label_w, label_w, '-' * feat_w, feat_w, '-' * exec_w, exec_w)
    out.append('{0}{1}{2}'.format(GREEN, sep[:cols].ljust(cols), RESET))

    for pnum in sorted(phases_info.keys()):
        info = phases_info[pnum]
        label = info['label']
        features = info['features']
        exec_group = '--'
        if pnum in group_map:
            gi, par = group_map[pnum]
            if par:
                others = [str(p) for p in analyzer['groups'][gi]['phases'] if p != pnum]
                exec_group = '{0} (parallel w/ {1})'.format(gi, ', '.join(others))
            else:
                exec_group = '{0} (sequential)'.format(gi)

        label_lines = wrap_cell(label, label_w)
        feat_lines = wrap_cell(features, feat_w)
        exec_lines = wrap_cell(exec_group, exec_w)
        row_lines = max(len(label_lines), len(feat_lines), len(exec_lines))
        if row_lines > 2:
            row_lines = 2

        for row in range(row_lines):
            l = label_lines[row] if row < len(label_lines) else ''
            f = feat_lines[row] if row < len(feat_lines) else ''
            e = exec_lines[row] if row < len(exec_lines) else ''
            if row == 0:
                line = '  {:<4d} {:<{}s} {:<{}s} {:<{}s}'.format(pnum, l, label_w, f, feat_w, e, exec_w)
            else:
                line = '  {:<4s} {:<{}s} {:<{}s} {:<{}s}'.format('', l, label_w, f, feat_w, e, exec_w)
            out.append(line[:cols].ljust(cols))

out.append('')
if parallel_groups:
    pg_strs = ['+'.join(str(p) for p in pg) for pg in parallel_groups]
    out.append('Parallel groups: {0} (Phases {1})'.format(len(parallel_groups), ', Phases '.join(pg_strs)).ljust(cols))
out.append('Review at .purlin/cache/delivery_plan.md'.ljust(cols))
out.append('{0}{1}{2}'.format(BOLD_CYAN, '=' * cols, RESET))

print('\n'.join(out), file=sys.stderr)

with open(lines_file, 'w') as f:
    f.write(str(len(out)))
" "$DELIVERY_PLAN" "$([ -t 2 ] && echo true || echo false)" "$APPROVAL_TABLE_LINES_FILE" "$analyzer_json"
}

# --- SIGWINCH handler: re-render approval table on terminal resize ---
rerender_on_resize() {
    update_term_width
    local lines
    lines=$(cat "$APPROVAL_TABLE_LINES_FILE" 2>/dev/null || echo 0)
    # +1 for the "Proceed? [Y/n]" prompt line
    lines=$((lines + 1))
    if [ "$lines" -gt 0 ] && [ -t 2 ]; then
        printf '\033[%dA\033[J' "$lines" >&2
    fi
    render_approval_table
    printf "Proceed? [Y/n] " >&2
}

# --- Bootstrap session when no delivery plan exists (Section 2.16) ---
if [ ! -f "$DELIVERY_PLAN" ]; then
    BOOTSTRAP_LOG="${RUNTIME_DIR}/continuous_build_bootstrap.log"

    # Create bootstrap-specific prompt file (distinct from continuous/server overrides)
    BOOTSTRAP_PROMPT_FILE=$(mktemp)
    cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$BOOTSTRAP_PROMPT_FILE"
    printf "\n\n" >> "$BOOTSTRAP_PROMPT_FILE"
    cat "$CORE_DIR/instructions/BUILDER_BASE.md" >> "$BOOTSTRAP_PROMPT_FILE"
    if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
        printf "\n\n" >> "$BOOTSTRAP_PROMPT_FILE"
        cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$BOOTSTRAP_PROMPT_FILE"
    fi
    if [ -f "$SCRIPT_DIR/.purlin/BUILDER_OVERRIDES.md" ]; then
        printf "\n\n" >> "$BOOTSTRAP_PROMPT_FILE"
        cat "$SCRIPT_DIR/.purlin/BUILDER_OVERRIDES.md" >> "$BOOTSTRAP_PROMPT_FILE"
    fi
    printf "\n\n" >> "$BOOTSTRAP_PROMPT_FILE"
    cat >> "$BOOTSTRAP_PROMPT_FILE" << 'BOOTSTRAP_OVERRIDE'
BOOTSTRAP MODE ACTIVE: You are running in non-interactive print mode to
initialize a delivery plan for continuous execution. There is no human user
present. You MUST:
- Execute your full startup protocol (Sections 2.0-2.3) including scope
  assessment.
- If scope assessment determines phasing IS warranted: create the delivery
  plan using /pl-delivery-plan WITHOUT asking for user approval. Auto-accept
  the phased delivery option. After committing the delivery plan, HALT
  IMMEDIATELY. Do not begin Phase 1.
- If scope assessment determines phasing is NOT warranted: proceed directly
  with implementation. Complete all work autonomously.
- NEVER ask "Ready to go?" or wait for any approval.
- SIZING BIAS: Prefer MORE phases over fewer.
  Prefer SMALLER phases over larger.
  Maximize parallelization -- group independent features into separate
  phases that can run concurrently. Each phase must be completable within
  a single session without context exhaustion. When in doubt, split.
This override takes precedence over any instruction to "wait for approval"
or "ask the user."
BOOTSTRAP_OVERRIDE

    # Start bootstrap canvas spinner
    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Bootstrap"
    start_bootstrap_canvas

    BOOTSTRAP_SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    run_to_log "$BOOTSTRAP_LOG" claude --print --verbose --output-format stream-json --session-id "$BOOTSTRAP_SESSION_ID" \
        "${CLI_ARGS[@]}" \
        --append-system-prompt-file "$BOOTSTRAP_PROMPT_FILE" \
        "Begin Builder session."
    BOOTSTRAP_RC=$?

    # Stop the bootstrap canvas
    stop_canvas
    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"
    if ! [ -t 2 ]; then
        canvas_milestone "Bootstrap complete"
    fi

    rm -f "$BOOTSTRAP_PROMPT_FILE"
    BOOTSTRAP_PROMPT_FILE=""

    # Outcome detection via file-existence checking, not output parsing
    if [ -f "$DELIVERY_PLAN" ]; then
        # Plan created -> validate with phase analyzer dry-run
        VALIDATE_OUTPUT=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>&1)
        VALIDATE_RC=$?

        if [ $VALIDATE_RC -ne 0 ]; then
            echo "Plan validation failed:" >&2
            echo "$VALIDATE_OUTPUT" | head -20 >&2
            echo "The plan has been committed for manual editing." >&2
            echo "Fix the plan at .purlin/cache/delivery_plan.md and re-run --continuous." >&2
            exit 0
        fi

        # Render the approval checkpoint table (Section 2.16)
        render_approval_table
        printf "Proceed? [Y/n] " >&2

        # Live resize: trap SIGWINCH to re-render table on terminal resize
        if [ -t 2 ]; then
            trap rerender_on_resize SIGWINCH
        fi
        read -r APPROVAL 2>/dev/null || APPROVAL=""
        if [ -t 2 ]; then
            trap update_term_width WINCH
        fi

        if [ -n "$APPROVAL" ] && ! echo "$APPROVAL" | grep -qi '^y'; then
            echo "Plan declined. The plan remains committed to git for editing." >&2
            exit 0
        fi

        echo "Approved. Entering continuous orchestration loop." >&2
        # Fall through to the main orchestration loop below
    elif [ $BOOTSTRAP_RC -eq 0 ]; then
        # No plan + exit 0 -> Builder completed work directly
        echo "Bootstrap completed all work directly (phasing not warranted)." >&2
        exit 0
    else
        # No plan + non-zero exit -> bootstrap failed
        echo "Error: Bootstrap session failed. Run an interactive Builder session to investigate." >&2
        exit 1
    fi
fi

# --- Startup recovery: reset stale IN_PROGRESS phases to PENDING (Section 2.4) ---
# Orphans from a previous interrupted run — no Builder is actively working on them.
reset_stale_in_progress() {
    [ -f "$DELIVERY_PLAN" ] || return 0
    local has_stale
    has_stale=$(grep -c '\[IN_PROGRESS\]' "$DELIVERY_PLAN" 2>/dev/null)
    has_stale=${has_stale:-0}
    if [ "$has_stale" -gt 0 ]; then
        python3 -c "
import re
with open('$DELIVERY_PLAN', 'r') as f:
    content = f.read()
content = re.sub(
    r'(\[IN_PROGRESS\])',
    '[PENDING]',
    content
)
with open('$DELIVERY_PLAN', 'w') as f:
    f.write(content)
" 2>/dev/null
        git -C "$SCRIPT_DIR" add "$DELIVERY_PLAN" 2>/dev/null
        git -C "$SCRIPT_DIR" commit -m "chore: reset stale IN_PROGRESS phases to PENDING" 2>/dev/null
    fi
}
reset_stale_in_progress

# --- Track initial PENDING phase count for summary ---
INITIAL_PENDING_COUNT=$(python3 -c "
import re
with open('$DELIVERY_PLAN') as f:
    content = f.read()
print(len(re.findall(r'## Phase \d+ -- .+? \[PENDING\]', content)))
" 2>/dev/null || echo "0")

CDD_STATUS="$CORE_DIR/tools/cdd/status.sh"

# --- Graceful stop handler (SIGINT/Ctrl+C) ---
STOP_REQUESTED=false
BUILDER_PID=""

graceful_stop() {
    STOP_REQUESTED=true
    # Clear terminal identity before stopping
    type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity
    # Send SIGTERM to sequential Builder
    if [ -n "$BUILDER_PID" ] && kill -0 "$BUILDER_PID" 2>/dev/null; then
        kill "$BUILDER_PID" 2>/dev/null
    fi
    # Send SIGTERM to parallel builders
    for pid in "${WT_PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    # Stop canvas render loop
    if [ -n "$CANVAS_PID" ] && kill -0 "$CANVAS_PID" 2>/dev/null; then
        kill "$CANVAS_PID" 2>/dev/null
    fi
    # Phase status cleanup: reset IN_PROGRESS phases to PENDING (Section 2.17)
    reset_stale_in_progress
    # Reset trap so second SIGINT forces immediate exit
    trap - INT
}
trap graceful_stop INT

# ================================================================
# Main orchestration loop (re-analyzes before each execution group)
# ================================================================

OUTER_BREAK=false

# Extract total phase count for terminal identity display
TOTAL_PHASE_COUNT=$(sed -n 's/.*\*\*Total Phases:\*\* \([0-9]*\).*/\1/p' "$DELIVERY_PLAN" 2>/dev/null)
TOTAL_PHASE_COUNT=${TOTAL_PHASE_COUNT:-0}

# Set initial continuous-mode identity
type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"

while [ "$OUTER_BREAK" = "false" ]; do

    # Re-run phase analyzer before each execution group
    start_interphase_canvas "Re-analyzing delivery plan..."
    ANALYZER_JSON=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>/dev/null)
    ANALYZER_RC=$?
    stop_canvas

    if [ $ANALYZER_RC -ne 0 ]; then
        echo "Error: Phase analyzer failed (exit code $ANALYZER_RC)." >&2
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 1>/dev/null 2>&2
        FAILURES+=("analyzer_failure")
        break
    fi

    if [ -z "$ANALYZER_JSON" ]; then
        echo "Error: Phase analyzer produced no output." >&2
        FAILURES+=("analyzer_failure")
        break
    fi

    # Check if any groups remain
    GROUPS_COUNT=$(printf '%s' "$ANALYZER_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['groups']))")

    if [ "$GROUPS_COUNT" = "0" ]; then
        if ! [ -t 2 ]; then
            canvas_milestone "No pending phases to execute"
        fi
        break
    fi

    GROUPS_EXECUTED=$((GROUPS_EXECUTED + 1))

    # Always take the FIRST group (re-analysis provides fresh ordering)
    IS_PARALLEL=$(printf '%s' "$ANALYZER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['groups'][0]['parallel'])")
    PHASE_LIST=$(printf '%s' "$ANALYZER_JSON" | python3 -c "import json,sys; print(' '.join(str(p) for p in json.load(sys.stdin)['groups'][0]['phases']))")

    if [ "$IS_PARALLEL" = "True" ]; then
        # ============================================================
        # PARALLEL EXECUTION
        # ============================================================
        # Update terminal identity to show parallel phase numbers
        PHASE_DISPLAY=$(echo "$PHASE_LIST" | tr ' ' ',')
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Phases $PHASE_DISPLAY"
        PARALLEL_GROUPS_USED=$((PARALLEL_GROUPS_USED + 1))

        # Capture plan hash BEFORE any phase status changes so the evaluator
        # fallback can detect whether the plan was modified during execution.
        PLAN_HASH_BEFORE=$(get_plan_hash)

        # Pre-launch: mark all phases in this group as IN_PROGRESS (Section 2.4)
        mark_phases_in_progress $PHASE_LIST

        WT_PIDS=()
        WT_DIRS=()
        WT_BRANCHES=()
        WT_LOGS=()
        WT_PHASES=()

        for PHASE_NUM in $PHASE_LIST; do
            WT_BRANCH="continuous-phase-${PHASE_NUM}"
            WT_DIR="${SCRIPT_DIR}/${WT_BRANCH}"
            LOG_FILE="${RUNTIME_DIR}/continuous_build_phase_${PHASE_NUM}_worktree.log"

            git -C "$SCRIPT_DIR" worktree add -b "$WT_BRANCH" "$WT_DIR" HEAD 2>/dev/null
            record_phase_start "$PHASE_NUM"

            INITIAL_MSG="Begin Builder session. CONTINUOUS MODE -- you are assigned to Phase ${PHASE_NUM} ONLY. Work exclusively on Phase ${PHASE_NUM} features. Do not wait for approval."

            (
                cd "$WT_DIR" || exit 1
                export PURLIN_PROJECT_ROOT="$WT_DIR"
                run_to_log "$LOG_FILE" claude --print --verbose --output-format stream-json "${CLI_ARGS[@]}" \
                    --append-system-prompt-file "$PARALLEL_PROMPT_FILE" \
                    "$INITIAL_MSG"
            ) > /dev/null 2>&1 &

            WT_PIDS+=($!)
            WT_DIRS+=("$WT_DIR")
            WT_BRANCHES+=("$WT_BRANCH")
            WT_LOGS+=("$LOG_FILE")
            WT_PHASES+=("$PHASE_NUM")
        done

        # Start canvas for parallel group visibility (Section 2.17)
        start_parallel_canvas "${WT_PHASES[*]}" "${WT_LOGS[*]}" "${WT_PIDS[*]}"

        # Monitor parallel builders: update per-phase status as each exits (Section 2.4)
        # As soon as a Builder exits successfully, immediately mark its phase COMPLETE
        # on the main branch. This keeps CDD metrics accurate in real time.
        PERPHASE_COMPLETED=()
        while true; do
            ALL_EXITED=true
            for i in "${!WT_PIDS[@]}"; do
                pid="${WT_PIDS[$i]}"
                phase="${WT_PHASES[$i]}"
                # Skip phases already recorded
                already=false
                for done_phase in "${PERPHASE_COMPLETED[@]}"; do
                    [ "$done_phase" = "$phase" ] && already=true && break
                done
                [ "$already" = "true" ] && continue

                if ! kill -0 "$pid" 2>/dev/null; then
                    wait "$pid" 2>/dev/null
                    EXIT_CODE=$?
                    if [ $EXIT_CODE -eq 0 ]; then
                        # Immediately mark COMPLETE on main branch (Section 2.4)
                        update_plan_phase_status "$phase"
                        git -C "$SCRIPT_DIR" add "$DELIVERY_PLAN" 2>/dev/null
                        git -C "$SCRIPT_DIR" commit -m "chore: mark phase $phase as COMPLETE" 2>/dev/null
                        record_phase_end "$phase" "COMPLETE"
                        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
                    fi
                    # Non-zero exits: phase remains IN_PROGRESS per spec
                    PERPHASE_COMPLETED+=("$phase")
                else
                    ALL_EXITED=false
                fi
            done
            [ "$ALL_EXITED" = "true" ] && break
            [ "$STOP_REQUESTED" = "true" ] && break
            sleep 1
        done

        # Check for graceful stop before merge
        if [ "$STOP_REQUESTED" = "true" ]; then
            stop_canvas
            for PHASE_NUM in $PHASE_LIST; do
                # Only mark INTERRUPTED for phases not already completed
                was_completed=false
                for done_phase in "${PERPHASE_COMPLETED[@]}"; do
                    [ "$done_phase" = "$PHASE_NUM" ] && was_completed=true && break
                done
                [ "$was_completed" = "false" ] && record_phase_end "$PHASE_NUM" "INTERRUPTED"
            done
            OUTER_BREAK=true
            continue
        fi

        # Stop canvas before merge (Section 2.17)
        stop_canvas
        if ! [ -t 2 ]; then
            for PHASE_NUM in $PHASE_LIST; do
                canvas_milestone "Phase $PHASE_NUM complete"
            done
        fi

        # Merge each worktree branch back to main
        MERGE_FAILED=false
        for i in "${!WT_BRANCHES[@]}"; do
            if ! git -C "$SCRIPT_DIR" merge "${WT_BRANCHES[$i]}" --no-edit 2>/dev/null; then
                CONFLICT_FILES=$(git -C "$SCRIPT_DIR" diff --name-only --diff-filter=U 2>/dev/null)
                echo "Error: Merge conflict during parallel merge of Phase ${WT_PHASES[$i]}:" >&2
                echo "$CONFLICT_FILES" >&2
                git -C "$SCRIPT_DIR" merge --abort 2>/dev/null
                MERGE_FAILED=true
                break
            fi
        done

        # Clean up all worktrees and branches for this group
        for i in "${!WT_DIRS[@]}"; do
            git -C "$SCRIPT_DIR" worktree remove "${WT_DIRS[$i]}" --force 2>/dev/null
            git -C "$SCRIPT_DIR" branch -D "${WT_BRANCHES[$i]}" 2>/dev/null
        done

        if [ "$MERGE_FAILED" = "true" ]; then
            FAILURES+=("merge_conflict")
            OUTER_BREAK=true
            continue
        fi

        # Process plan amendment files from parallel builders
        apply_plan_amendments

        # Evaluate using the last parallel log
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Evaluating"
        start_interphase_canvas "Evaluating parallel group output..."
        LAST_LOG="${WT_LOGS[${#WT_LOGS[@]}-1]}"
        EVAL_OUTPUT=$(run_evaluator "$LAST_LOG")

        if [ $? -ne 0 ] || [ -z "$EVAL_OUTPUT" ]; then
            log_eval "Evaluator failed, using fallback"
            EVAL_OUTPUT=$(evaluator_fallback "$PLAN_HASH_BEFORE")
        fi
        stop_canvas

        ACTION="${EVAL_OUTPUT%%|*}"
        _remainder="${EVAL_OUTPUT#*|}"
        EVAL_SUCCESS="${_remainder%%|*}"
        REASON="${_remainder#*|}"
        log_eval "Parallel group — Action: $ACTION (success=$EVAL_SUCCESS) — $REASON"

        case "$ACTION" in
            continue)
                type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"
                # Loop back to re-analyze (fresh ordering)
                ;;
            stop)
                if [ "$EVAL_SUCCESS" = "true" ]; then
                    # All work done — exit cleanly
                    OUTER_BREAK=true
                else
                    # Evaluator says stop on error — but check if PENDING phases
                    # remain before giving up (guards against false-negative fallback)
                    local pending_remaining=0
                    [ -f "$DELIVERY_PLAN" ] && pending_remaining=$(grep -c '\[PENDING\]' "$DELIVERY_PLAN" 2>/dev/null || echo "0")
                    if [ "$pending_remaining" -gt 0 ]; then
                        log_eval "stop(success=false) overridden: $pending_remaining PENDING phase(s) remain — continuing"
                    else
                        OUTER_BREAK=true
                    fi
                fi
                ;;
            *)
                # Loop back to re-analyze
                ;;
        esac

    else
        # ============================================================
        # SEQUENTIAL EXECUTION
        # ============================================================
        PHASE_NUM=$(echo "$PHASE_LIST" | awk '{print $1}')

        # Pre-launch: mark phase as IN_PROGRESS (Section 2.4)
        mark_phases_in_progress "$PHASE_NUM"
        # Update terminal identity for sequential phase
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Phase ${PHASE_NUM}/${TOTAL_PHASE_COUNT}"

        record_phase_start "$PHASE_NUM"

        SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
        LOG_FILE="${RUNTIME_DIR}/continuous_build_phase_${PHASE_NUM}.log"
        INITIAL_MSG="Begin Builder session. CONTINUOUS MODE -- proceed immediately with work plan, do not wait for approval."
        RUN_ACTION="run"

        # Inner loop for evaluate-act cycle (handles approve and retry)
        while true; do
            PLAN_HASH_BEFORE=$(get_plan_hash)

            # Start sequential canvas for this phase
            start_sequential_canvas "$PHASE_NUM" "$LOG_FILE"

            # Execute Builder based on action type
            case "$RUN_ACTION" in
                run|retry)
                    run_to_log "$LOG_FILE" claude --print --verbose --output-format stream-json --session-id "$SESSION_ID" \
                        "${CLI_ARGS[@]}" \
                        --append-system-prompt-file "$PROMPT_FILE" \
                        "$INITIAL_MSG" &
                    BUILDER_PID=$!
                    wait "$BUILDER_PID" 2>/dev/null
                    BUILDER_PID=""
                    ;;
                resume)
                    run_to_log "$LOG_FILE" --append claude --resume "$SESSION_ID" --print --verbose --output-format stream-json \
                        "${CLI_ARGS[@]}" \
                        "Approved. Proceed." &
                    BUILDER_PID=$!
                    wait "$BUILDER_PID" 2>/dev/null
                    BUILDER_PID=""
                    ;;
            esac

            # Stop the sequential canvas
            stop_canvas
            if ! [ -t 2 ]; then
                canvas_milestone "Phase $PHASE_NUM complete"
            fi

            # Check for graceful stop
            if [ "$STOP_REQUESTED" = "true" ]; then
                record_phase_end "$PHASE_NUM" "INTERRUPTED"
                OUTER_BREAK=true
                break
            fi

            # Detect plan amendments by sequential Builder
            PLAN_HASH_AFTER=$(get_plan_hash)
            if [ "$PLAN_HASH_BEFORE" != "$PLAN_HASH_AFTER" ]; then
                PLAN_AMENDED=true
            fi

            # Run evaluator with inter-phase canvas
            type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Evaluating"
            start_interphase_canvas "Evaluating phase $PHASE_NUM output..."
            EVAL_OUTPUT=$(run_evaluator "$LOG_FILE")

            if [ $? -ne 0 ] || [ -z "$EVAL_OUTPUT" ]; then
                log_eval "Evaluator failed for Phase $PHASE_NUM, using fallback"
                EVAL_OUTPUT=$(evaluator_fallback "$PLAN_HASH_BEFORE")
            fi
            stop_canvas

            ACTION="${EVAL_OUTPUT%%|*}"
            _remainder="${EVAL_OUTPUT#*|}"
            EVAL_SUCCESS="${_remainder%%|*}"
            REASON="${_remainder#*|}"
            log_eval "Phase $PHASE_NUM — Action: $ACTION (success=$EVAL_SUCCESS) — $REASON"

            case "$ACTION" in
                continue)
                    update_plan_phase_status "$PHASE_NUM"
                    record_phase_end "$PHASE_NUM" "COMPLETE"
                    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
                    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"
                    break  # Exit inner loop; outer loop re-analyzes
                    ;;
                approve)
                    log_eval "Resuming session for Phase $PHASE_NUM"
                    RUN_ACTION="resume"
                    ;;
                retry)
                    RETRY_FILE="${RUNTIME_DIR}/retry_count_${PHASE_NUM}"
                    RETRY_COUNT=0
                    [ -f "$RETRY_FILE" ] && RETRY_COUNT=$(cat "$RETRY_FILE")
                    RETRY_COUNT=$((RETRY_COUNT + 1))
                    echo "$RETRY_COUNT" > "$RETRY_FILE"

                    if [ "$RETRY_COUNT" -gt 2 ]; then
                        echo "Error: Retry limit exceeded for Phase $PHASE_NUM. Manual intervention required." >&2
                        FAILURES+=("retry_limit_phase_${PHASE_NUM}")
                        OUTER_BREAK=true
                        break
                    fi

                    TOTAL_RETRIES=$((TOTAL_RETRIES + 1))
                    log_eval "Retrying Phase $PHASE_NUM (attempt $((RETRY_COUNT + 1)))"
                    SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
                    RUN_ACTION="retry"
                    ;;
                stop)
                    if [ "$EVAL_SUCCESS" = "true" ]; then
                        record_phase_end "$PHASE_NUM" "COMPLETE"
                        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
                    else
                        record_phase_end "$PHASE_NUM" "SKIPPED"
                        FAILURES+=("stop_phase_${PHASE_NUM}")
                    fi
                    OUTER_BREAK=true
                    break
                    ;;
                *)
                    echo "Error: Unknown evaluator action: $ACTION" >&2
                    OUTER_BREAK=true
                    break
                    ;;
            esac
        done
    fi
done

# --- End-of-run cleanup: delete delivery plan when all phases COMPLETE ---
# Prevents stale all-COMPLETE plans from blocking the next --continuous run.
if [ "$STOP_REQUESTED" = "false" ] && [ ${#FAILURES[@]} -eq 0 ] && all_phases_complete; then
    rm -f "$DELIVERY_PLAN"
    git -C "$SCRIPT_DIR" add "$DELIVERY_PLAN" 2>/dev/null
    git -C "$SCRIPT_DIR" commit -m "chore: remove delivery plan (all phases complete)" 2>/dev/null
fi

# ================================================================
# Exit Summary (Section 2.17)
# ================================================================

EXIT_SUMMARY_PRINTED=false

# Safety trap: if the script dies before reaching the exit summary (unexpected
# error, unhandled signal), print a minimal fallback summary so the user knows
# what happened and where to look.
print_fallback_summary() {
    local exit_code=$?
    # Always run the original cleanup (temp files, worktrees)
    cleanup 2>/dev/null
    # Skip summary if the normal exit path already printed it
    [ "$EXIT_SUMMARY_PRINTED" = "true" ] && return
    stop_canvas 2>/dev/null
    echo "" >&2
    echo "=== Continuous Build — Unexpected Exit (code $exit_code) ===" >&2
    echo "" >&2
    echo "The continuous builder exited before printing a full summary." >&2
    echo "Phases completed: ${PHASES_COMPLETED:-0}/${INITIAL_PENDING_COUNT:-?}" >&2
    if [ ${#FAILURES[@]:-0} -gt 0 ]; then
        echo "Failures: ${FAILURES[*]}" >&2
    fi
    echo "" >&2
    echo "What to do next:" >&2
    echo "  1. Check log files: .purlin/runtime/continuous_build_phase_*.log" >&2
    echo "  2. Run /pl-status to see current feature states" >&2
    echo "  3. Re-run ./pl-run-builder.sh --continuous to resume" >&2
    echo "" >&2
    # Clean up runtime artifacts
    rm -f "${RUNTIME_DIR}"/phase_*_meta "${RUNTIME_DIR}"/canvas_frozen_* \
          "${RUNTIME_DIR}"/retry_count_* "${RUNTIME_DIR}"/plan_amendment_phase_*.json \
          "${RUNTIME_DIR}/approval_table_lines" "${RUNTIME_DIR}/canvas_state" 2>/dev/null
    # Reset stale IN_PROGRESS phases so next run doesn't skip them
    reset_stale_in_progress 2>/dev/null
}
trap print_fallback_summary EXIT

# Canvas clear before exit summary (permanent output)
canvas_clear

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
DURATION_STR=$(format_duration "$DURATION")

# Determine overall status
if [ "$STOP_REQUESTED" = "true" ]; then
    OVERALL_STATUS="stopped (user interrupt)"
elif [ ${#FAILURES[@]} -gt 0 ]; then
    OVERALL_STATUS="failed (${FAILURES[0]})"
else
    OVERALL_STATUS="completed"
fi

# ANSI color helpers for exit summary
if [ -t 2 ]; then
    C_BOLD_CYAN='\033[1;36m'
    C_GREEN='\033[32m'
    C_YELLOW='\033[33m'
    C_RED='\033[31m'
    C_DIM='\033[2m'
    C_RESET='\033[0m'
else
    C_BOLD_CYAN=''
    C_GREEN=''
    C_YELLOW=''
    C_RED=''
    C_DIM=''
    C_RESET=''
fi

update_term_width  # Refresh terminal width before rendering

echo "" >&2
SUMMARY_TITLE="=== Continuous Build Summary "
SUMMARY_PAD=$(printf '%*s' "$((PURLIN_TERM_COLS - ${#SUMMARY_TITLE}))" '' | tr ' ' '=')
printf "${C_BOLD_CYAN}%s${C_RESET}\n" "${SUMMARY_TITLE}${SUMMARY_PAD}" >&2
echo "Status: $OVERALL_STATUS" >&2
printf "Duration: ${C_DIM}${DURATION_STR}${C_RESET}\n" >&2
echo "Phases: ${PHASES_COMPLETED}/${INITIAL_PENDING_COUNT} completed" >&2
echo "" >&2

# Per-phase details from metadata files and delivery plan (dynamic column widths)
python3 -c "
import os, re, sys, glob

runtime_dir = sys.argv[1]
plan_path = sys.argv[2]
is_tty = sys.argv[3] == 'true'

# Read terminal width from shared file (same as canvas engine)
term_width_file = os.path.join(runtime_dir, 'term_width')
try:
    with open(term_width_file) as f:
        cols = int(f.read().strip())
except Exception:
    try:
        cols = int(os.environ.get('PURLIN_TERM_COLS', '80'))
    except (ValueError, TypeError):
        cols = 80

# ANSI colors
GREEN = '\033[32m' if is_tty else ''
YELLOW = '\033[33m' if is_tty else ''
RED = '\033[31m' if is_tty else ''
DIM = '\033[2m' if is_tty else ''
RESET = '\033[0m' if is_tty else ''

phases = []

# From delivery plan (if exists)
if os.path.exists(plan_path):
    with open(plan_path) as f:
        content = f.read()
    for m in re.finditer(r'## Phase (\d+) -- (.+?) \[', content):
        pnum = int(m.group(1))
        label = m.group(2).strip()
        feat_m = re.search(r'## Phase {} -- .*?\n\*\*Features:\*\* (.*?)(?:\n|$)'.format(pnum), content)
        features = feat_m.group(1).strip() if feat_m else '--'
        phases.append((pnum, label, features))

# If no plan, use metadata files only
if not phases:
    for mf in sorted(glob.glob(os.path.join(runtime_dir, 'phase_*_meta'))):
        m_f = re.search(r'phase_(\d+)_meta', mf)
        if m_f:
            pnum = int(m_f.group(1))
            meta = {}
            with open(mf) as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        meta[k] = v
            phases.append((pnum, meta.get('LABEL', ''), meta.get('FEATURES', '--')))

if not phases:
    print('  (no phase data available)', file=sys.stderr)
    sys.exit(0)

# Collect phase data with status and duration
phase_data = []
for pnum, label, features in sorted(phases):
    meta_file = os.path.join(runtime_dir, 'phase_{}_meta'.format(pnum))
    status = 'PENDING'
    dur_str = ''
    if os.path.exists(meta_file):
        meta = {}
        with open(meta_file) as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    meta[k] = v
        status = meta.get('STATUS', 'PENDING')
        start_t = meta.get('START_TIME', '')
        end_t = meta.get('END_TIME', '')
        if start_t and end_t:
            try:
                secs = int(end_t) - int(start_t)
                mins = secs // 60
                rem = secs % 60
                dur_str = '{}m {}s'.format(mins, rem) if mins > 0 else '{}s'.format(secs)
            except ValueError:
                pass
    phase_data.append((pnum, label, status, dur_str, features))

# Compute dynamic column widths based on actual content
max_pnum_w = max(len(str(p[0])) for p in phase_data)
max_label_w = max(len(p[1]) for p in phase_data)
max_status_w = max(len(p[2]) for p in phase_data)
max_dur_w = max(len(p[3]) for p in phase_data) if any(p[3] for p in phase_data) else 0

# Fixed structure: '  Phase N -- LABEL   STATUS   DURATION   features: FEATURES'
# prefix = '  Phase ' + pnum + ' -- '
prefix_w = 2 + 6 + max_pnum_w + 4  # '  Phase N -- '
separator_w = 3 + max_status_w + 3 + max(max_dur_w, 1) + 3 + 10  # '   STATUS   DUR   features: '
avail_for_label_and_feat = cols - prefix_w - separator_w

# Cap label width so features get at least 15 chars
if max_label_w > avail_for_label_and_feat - 15:
    eff_label_w = max(avail_for_label_and_feat - 15, 8)
else:
    eff_label_w = max_label_w

feat_start_col = prefix_w + eff_label_w + 3 + max_status_w + 3 + max(max_dur_w, 1) + 3 + 10
avail_feat = cols - feat_start_col
if avail_feat < 5:
    avail_feat = 5

for pnum, label, status, dur_str, features in phase_data:
    if status == 'COMPLETE':
        color = GREEN
    elif status == 'INTERRUPTED':
        color = YELLOW
    elif status in ('SKIPPED', 'FAILED'):
        color = RED
    else:
        color = DIM

    disp_label = label[:eff_label_w]
    disp_feat = features

    # First line
    visible = '  Phase {:<{}} -- {:<{}}   {:<{}}   {:<{}}   features: {}'.format(
        pnum, max_pnum_w, disp_label, eff_label_w,
        status, max_status_w, dur_str, max(max_dur_w, 1), disp_feat)

    if len(visible) <= cols:
        # Pad to fill terminal width
        padded = visible.ljust(cols)
        print('{}{}{}'.format(color, padded, RESET), file=sys.stderr)
    else:
        # Truncate features to fit, with continuation line
        first_feat = disp_feat[:avail_feat]
        rest_feat = disp_feat[avail_feat:]
        line1_visible = '  Phase {:<{}} -- {:<{}}   {:<{}}   {:<{}}   features: {}'.format(
            pnum, max_pnum_w, disp_label, eff_label_w,
            status, max_status_w, dur_str, max(max_dur_w, 1), first_feat)
        print('{}{}{}'.format(color, line1_visible.ljust(cols)[:cols], RESET), file=sys.stderr)
        # Continuation line indented to features column
        if rest_feat:
            indent = ' ' * feat_start_col
            if len(rest_feat) > avail_feat:
                rest_feat = rest_feat[:max(avail_feat - 3, 0)] + '...'
            line2_visible = indent + rest_feat
            print('{}{}{}'.format(color, line2_visible.ljust(cols)[:cols], RESET), file=sys.stderr)
" "$RUNTIME_DIR" "$DELIVERY_PLAN" "$([ -t 2 ] && echo true || echo false)" >&2

echo "" >&2

# Retries
RETRY_INFO=""
for retry_file in "$RUNTIME_DIR"/retry_count_*; do
    [ -f "$retry_file" ] || continue
    RP=$(echo "$retry_file" | grep -oE '[0-9]+$')
    RC=$(cat "$retry_file")
    if [ -n "$RETRY_INFO" ]; then
        RETRY_INFO="${RETRY_INFO}, Phase ${RP}"
    else
        RETRY_INFO="${RC} (Phase ${RP})"
    fi
done
echo "Retries: ${RETRY_INFO:-0}" >&2
echo "Parallel groups: $PARALLEL_GROUPS_USED" >&2
if [ "$PLAN_AMENDED" = "true" ]; then
    echo "Note: delivery plan was amended during execution" >&2
fi

# --- Part 2: Work digest (LLM-summarized via Haiku) ---
generate_work_digest() {
    # Collect result summaries from each phase log file
    local digest_input=""
    for log_file in "$RUNTIME_DIR"/continuous_build_phase_*.log; do
        [ -f "$log_file" ] || continue
        local phase_id
        phase_id=$(echo "$log_file" | grep -oE 'phase_[0-9]+')
        # Extract the last "result" JSON object from stream-json output
        local result_text
        result_text=$(grep '"type":"result"' "$log_file" 2>/dev/null | tail -1 | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('result', data.get('content', '')))
except Exception:
    pass
" 2>/dev/null)
        if [ -n "$result_text" ]; then
            digest_input="${digest_input}
--- ${phase_id} ---
${result_text}
"
        fi
    done

    if [ -z "$digest_input" ]; then
        echo "(Work digest unavailable — no phase results found. See log files below)" >&2
        return
    fi

    local plan_content=""
    [ -f "$DELIVERY_PLAN" ] && plan_content=$(cat "$DELIVERY_PLAN")

    local digest_prompt_file
    digest_prompt_file=$(mktemp)
    cat > "$digest_prompt_file" << DIGEST_EOF
Summarize this continuous build run for a developer. Be concise (under 300 words).

Structure your response as:
1. **Overall:** One sentence — did it succeed, partially succeed, or fail?
2. **What was built:** Bullet list of the key changes across all phases (group related work, don't list every file).
3. **Issues:** Any problems, retries, escalations, INFEASIBLE tags, or DISCOVERY tags the Builders flagged. If none, say "None."
4. **Needs attention:** Anything that requires human action before the next run (manual scenarios awaiting QA, unresolved discoveries, features stuck in TODO). If none, say "None."

Do not include phase numbers or repeat the phase table. Focus on substance.

## Phase Results:
${digest_input}

## Delivery Plan:
${plan_content:-"(Plan was deleted — all phases completed)"}
DIGEST_EOF

    local digest_result digest_rc
    if command -v timeout >/dev/null 2>&1; then
        digest_result=$(timeout 30 claude --print --model "$EVALUATOR_MODEL" < "$digest_prompt_file" 2>/dev/null)
        digest_rc=$?
    elif command -v gtimeout >/dev/null 2>&1; then
        digest_result=$(gtimeout 30 claude --print --model "$EVALUATOR_MODEL" < "$digest_prompt_file" 2>/dev/null)
        digest_rc=$?
    else
        claude --print --model "$EVALUATOR_MODEL" < "$digest_prompt_file" > "${digest_prompt_file}.out" 2>/dev/null &
        local dpid=$!
        local dwaited=0
        while kill -0 "$dpid" 2>/dev/null && [ "$dwaited" -lt 30 ]; do
            sleep 1
            dwaited=$((dwaited + 1))
        done
        if kill -0 "$dpid" 2>/dev/null; then
            kill "$dpid" 2>/dev/null
            wait "$dpid" 2>/dev/null
            digest_rc=124
            digest_result=""
        else
            wait "$dpid" 2>/dev/null
            digest_rc=$?
            digest_result=$(cat "${digest_prompt_file}.out" 2>/dev/null)
        fi
        rm -f "${digest_prompt_file}.out" 2>/dev/null
    fi
    rm -f "$digest_prompt_file"

    echo "" >&2
    if [ $digest_rc -ne 0 ] || [ -z "$digest_result" ]; then
        echo "(Work digest unavailable — see log files below)" >&2
    else
        # Print digest as plain text (no ANSI color per spec)
        echo "$digest_result" >&2
    fi
}

generate_work_digest

echo "" >&2
echo "Log files: .purlin/runtime/continuous_build_phase_*.log" >&2
printf "${C_BOLD_CYAN}%s${C_RESET}\n" "$(printf '%*s' "$PURLIN_TERM_COLS" '' | tr ' ' '=')" >&2

# Mark that the full exit summary was printed (disables fallback trap)
EXIT_SUMMARY_PRINTED=true

# Post-run status refresh (Section 2.17)
if [ -f "$CDD_STATUS" ]; then
    echo "" >&2
    bash "$CDD_STATUS" 2>&1
fi

# --- Exit cleanup: delete transient runtime artifacts (Section 2.11) ---
# Log files are preserved for user inspection; purged on next startup.
rm -f "${RUNTIME_DIR}"/phase_*_meta 2>/dev/null
rm -f "${RUNTIME_DIR}"/canvas_frozen_* 2>/dev/null
rm -f "${RUNTIME_DIR}"/retry_count_* 2>/dev/null
rm -f "${RUNTIME_DIR}"/plan_amendment_phase_*.json 2>/dev/null
rm -f "${RUNTIME_DIR}/approval_table_lines" 2>/dev/null
rm -f "${RUNTIME_DIR}/canvas_state" 2>/dev/null

# Disable the fallback summary trap and run original cleanup (temp files, worktrees)
trap - EXIT
cleanup 2>/dev/null

if [ ${#FAILURES[@]} -gt 0 ] || [ "$STOP_REQUESTED" = "true" ]; then
    exit 1
fi
exit 0
