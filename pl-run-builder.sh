#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/purlin"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"

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
AGENT_STARTUP="true"
AGENT_RECOMMEND="true"

if [ -f "$RESOLVER" ]; then
    eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"
fi

# --- Validate startup controls ---
if [ "$AGENT_STARTUP" = "false" ] && [ "$AGENT_RECOMMEND" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: startup_sequence=false with recommend_next_actions=true is not a valid combination. Set recommend_next_actions to false or enable startup_sequence." >&2
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
    claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "Begin Builder session."
    exit $?
fi

# ================================================================
# CONTINUOUS MODE
# ================================================================

RUNTIME_DIR="$SCRIPT_DIR/.purlin/runtime"
DELIVERY_PLAN="$SCRIPT_DIR/.purlin/cache/delivery_plan.md"
PHASE_ANALYZER="$CORE_DIR/tools/delivery/phase_analyzer.py"
HAIKU_MODEL="claude-haiku-4-5-20251001"

# Tracking variables (file-based retry counts for bash 3 compat)
PHASES_COMPLETED=0
PARALLEL_GROUPS_USED=0
GROUPS_EXECUTED=0
TOTAL_RETRIES=0
FAILURES=()
PLAN_AMENDED=false
INITIAL_PENDING_COUNT=0
START_TIME=$(date +%s)

# Evaluator JSON schema
EVALUATOR_SCHEMA='{"type":"object","properties":{"action":{"type":"string","enum":["continue","retry","approve","stop"]},"reason":{"type":"string"}},"required":["action","reason"]}'

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
- "Phase N of M complete" + delivery plan updated -> action: "continue"
- Builder amended the delivery plan (new/split/modified phases) + phase complete -> action: "continue"
- "Ready to go?" / "Ready to resume?" (approval prompt) -> action: "approve"
- Context exhaustion / checkpoint saved mid-phase -> action: "retry"
- Partial progress (features done but phase incomplete) -> action: "retry"
- Builder output mentions plan amendment but current phase not complete -> action: "retry"
- Error requiring human input (INFEASIBLE, missing fixture) -> action: "stop"
- All phases complete / delivery plan deleted -> action: "stop" (with success reason)
- No meaningful progress detected -> action: "stop"

Return a JSON object with "action" and "reason" fields.
EVAL_EOF

    local eval_result
    eval_result=$(claude --print --model "$HAIKU_MODEL" --json-schema "$EVALUATOR_SCHEMA" < "$eval_msg_file" 2>/dev/null)
    local eval_rc=$?
    rm -f "$eval_msg_file"

    if [ $eval_rc -ne 0 ] || [ -z "$eval_result" ]; then
        return 1
    fi

    local parsed
    parsed=$(printf '%s' "$eval_result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data['action'] + '|' + data['reason'])
except (json.JSONDecodeError, KeyError):
    sys.exit(1)
" 2>/dev/null) || return 1

    echo "$parsed"
    return 0
}

# --- Helper: evaluator fallback (delivery plan hash check) ---
evaluator_fallback() {
    local plan_hash_before="$1"
    local plan_hash_after
    plan_hash_after=$(get_plan_hash)

    if [ "$plan_hash_before" != "$plan_hash_after" ]; then
        echo "continue|evaluator fallback: delivery plan changed"
    else
        echo "stop|evaluator fallback: delivery plan unchanged"
    fi
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
        printf "editing %.50s" "$fname"
        return
    fi
    local cmd_match
    cmd_match=$(echo "$tail_content" | grep -oE 'running [a-zA-Z0-9_ -]+' | tail -1)
    if [ -n "$cmd_match" ]; then
        printf "%.50s" "$cmd_match"
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

# --- Helper: update delivery plan phase status after parallel group ---
update_plan_phase_status() {
    local phase_num="$1"
    local commit_hash
    commit_hash=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || echo "--")

    [ -f "$DELIVERY_PLAN" ] || return 0

    python3 -c "
import re, sys

with open('$DELIVERY_PLAN', 'r') as f:
    content = f.read()

# Update status from PENDING/IN_PROGRESS to COMPLETE
content = re.sub(
    r'(## Phase $phase_num -- .+?) \[(?:PENDING|IN_PROGRESS)\]',
    r'\1 [COMPLETE]',
    content
)

# Update completion commit
content = re.sub(
    r'(\*\*Completion Commit:\*\*) --',
    r'\1 $commit_hash',
    content,
    count=1
)

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
# Terminal Canvas Engine (Section 2.16)
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
            printf '\033[%dA\033[J' "$lines" >&2
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
            printf '\033[36m%s\033[0m Starting bootstrap session... \033[2m%ss\033[0m\n' "$s" "$elapsed" >&2
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

            if [ "$prev_lines" -gt 0 ]; then
                printf '\033[%dA\033[J' "$prev_lines" >&2
            fi
            printf '\033[36m%s\033[0m \033[1;37mPhase %s -- %s\033[0m   \033[33mrunning\033[0m  \033[2m%s\033[0m   %s  %s\n' \
                "$s" "$phase_num" "$phase_label" "$elapsed_str" "$fsize" "$activity" >&2
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

            # Heavier updates every 15 seconds (~150 iterations)
            heavy_counter=$((heavy_counter + 1))
            do_heavy=false
            if [ "$heavy_counter" -ge 150 ]; then
                heavy_counter=0
                do_heavy=true
            fi

            OUTPUT="[$TIMESTAMP] Parallel group (${#P_PHASES[@]} phases):"$'\n'
            LINE_COUNT=1

            for i in "${!P_PHASES[@]}"; do
                PNUM="${P_PHASES[$i]}"
                LFILE="${P_LOGS[$i]}"
                PID_VAL="${P_PIDS[$i]}"

                PLABEL=$(sed -n "s/## Phase ${PNUM} -- \(.*\) \[.*/\1/p" "$DELIVERY_PLAN" 2>/dev/null | head -1)
                [ -z "$PLABEL" ] && PLABEL="Phase ${PNUM}"

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
                FSIZE="${P_FSIZE[$i]}"

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

                if kill -0 "$PID_VAL" 2>/dev/null; then
                    OUTPUT+="             \033[33mPhase ${PNUM} -- ${PLABEL}   running  ${ELAPSED}   ${FSIZE}  ${P_ACTIVITY[$i]}\033[0m"$'\n'
                else
                    if [ "$FSIZE" = "0K" ]; then
                        OUTPUT+="             \033[31mPhase ${PNUM} -- ${PLABEL}   done     ${ELAPSED}   ${FSIZE}\033[0m"$'\n'
                    else
                        OUTPUT+="             \033[32mPhase ${PNUM} -- ${PLABEL}   done     ${ELAPSED}   ${FSIZE}\033[0m"$'\n'
                    fi
                fi
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
render_approval_table() {
    # Renders the delivery plan summary table for the approval checkpoint.
    # Uses phase analyzer JSON output for structured data.
    local analyzer_json
    analyzer_json=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>/dev/null)

    python3 -c "
import json, re, sys, os

plan_path = sys.argv[1]
is_tty = sys.argv[2] == 'true'

try:
    analyzer = json.loads(sys.argv[3])
except (json.JSONDecodeError, IndexError):
    analyzer = {'groups': []}

# Read delivery plan for labels and features
with open(plan_path) as f:
    plan_content = f.read()

phases_info = {}
for m in re.finditer(r'## Phase (\d+) -- (.+?) \[(PENDING|IN_PROGRESS|COMPLETE)\]', plan_content):
    pnum = int(m.group(1))
    label = m.group(2).strip()
    feat_m = re.search(r'## Phase {} -- .*?\n\*\*Features:\*\* (.*?)(?:\n|\$)'.format(pnum), plan_content)
    features = feat_m.group(1).strip() if feat_m else '--'
    phases_info[pnum] = {'label': label, 'features': features}

# Build group index: phase_num -> (group_idx, parallel flag)
group_map = {}
for gi, group in enumerate(analyzer.get('groups', [])):
    for p in group.get('phases', []):
        group_map[p] = (gi, group.get('parallel', False))

# Terminal width
try:
    cols = int(os.popen('tput cols 2>/dev/null').read().strip() or 80)
except Exception:
    cols = 80

total_phases = len(phases_info)
parallel_groups = []
seen_groups = set()
for gi, group in enumerate(analyzer.get('groups', [])):
    if group.get('parallel', False) and gi not in seen_groups:
        seen_groups.add(gi)
        parallel_groups.append(group['phases'])

# ANSI helpers
BOLD_CYAN = '\033[1;36m' if is_tty else ''
GREEN = '\033[32m' if is_tty else ''
RESET = '\033[0m' if is_tty else ''

out = []
out.append(f'{BOLD_CYAN}=== Delivery Plan ({total_phases} phases) ==={RESET}')
out.append('')

# Header
hdr = f'  {\"#\":<4s} {\"Label\":<29s} {\"Features\":<40s} {\"Complexity\":<13s} {\"Exec Group\"}'
out.append(f'{BOLD_CYAN}{hdr}{RESET}')
sep = f'  {\"---\":<4s} {\"----------------------------\":<29s} {\"---------------------------------------\":<40s} {\"------------\":<13s} {\"-------------------\"}'
out.append(f'{GREEN}{sep}{RESET}')

for pnum in sorted(phases_info.keys()):
    info = phases_info[pnum]
    label = info['label'][:28]
    features = info['features'][:39]
    complexity = '--'
    exec_group = '--'
    if pnum in group_map:
        gi, par = group_map[pnum]
        if par:
            others = [str(p) for p in analyzer['groups'][gi]['phases'] if p != pnum]
            exec_group = f'{gi} (parallel w/ {\", \".join(others)})'
        else:
            exec_group = f'{gi} (sequential)'
    out.append(f'  {pnum:<4d} {label:<29s} {features:<40s} {complexity:<13s} {exec_group}')

out.append('')
if parallel_groups:
    pg_strs = ['+'.join(str(p) for p in pg) for pg in parallel_groups]
    out.append(f'Parallel groups: {len(parallel_groups)} (Phases {(\", Phases \").join(pg_strs)})')
out.append(f'Review at .purlin/cache/delivery_plan.md')
out.append(f'{BOLD_CYAN}================================{RESET}')

print('\n'.join(out), file=sys.stderr)
" "$DELIVERY_PLAN" "$([ -t 2 ] && echo true || echo false)" "$analyzer_json"
}

# --- Bootstrap session when no delivery plan exists (Section 2.15) ---
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
    start_bootstrap_canvas

    BOOTSTRAP_SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    claude --print --session-id "$BOOTSTRAP_SESSION_ID" \
        "${CLI_ARGS[@]}" \
        --append-system-prompt-file "$BOOTSTRAP_PROMPT_FILE" \
        "Begin Builder session." > "$BOOTSTRAP_LOG" 2>&1
    BOOTSTRAP_RC=$?

    # Stop the bootstrap canvas
    stop_canvas
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

        # Render the approval checkpoint table (Section 2.15)
        render_approval_table
        printf "Proceed? [Y/n] " >&2
        read -r APPROVAL 2>/dev/null || APPROVAL=""

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
    # Reset trap so second SIGINT forces immediate exit
    trap - INT
}
trap graceful_stop INT

# ================================================================
# Main orchestration loop (re-analyzes before each execution group)
# ================================================================

OUTER_BREAK=false

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
        PARALLEL_GROUPS_USED=$((PARALLEL_GROUPS_USED + 1))

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
                claude --print "${CLI_ARGS[@]}" \
                    --append-system-prompt-file "$PARALLEL_PROMPT_FILE" \
                    "$INITIAL_MSG" > "$LOG_FILE" 2>&1
            ) &

            WT_PIDS+=($!)
            WT_DIRS+=("$WT_DIR")
            WT_BRANCHES+=("$WT_BRANCH")
            WT_LOGS+=("$LOG_FILE")
            WT_PHASES+=("$PHASE_NUM")
        done

        # Start canvas for parallel group visibility (Section 2.16)
        start_parallel_canvas "${WT_PHASES[*]}" "${WT_LOGS[*]}" "${WT_PIDS[*]}"

        # Wait for all parallel builders to complete
        for pid in "${WT_PIDS[@]}"; do
            wait "$pid" 2>/dev/null
        done

        # Check for graceful stop before merge
        if [ "$STOP_REQUESTED" = "true" ]; then
            stop_canvas
            for PHASE_NUM in $PHASE_LIST; do
                record_phase_end "$PHASE_NUM" "INTERRUPTED"
            done
            OUTER_BREAK=true
            continue
        fi

        # Stop canvas before merge (Section 2.16)
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
        start_interphase_canvas "Evaluating parallel group output..."
        PLAN_HASH_BEFORE=$(get_plan_hash)
        LAST_LOG="${WT_LOGS[${#WT_LOGS[@]}-1]}"
        EVAL_OUTPUT=$(run_evaluator "$LAST_LOG")

        if [ $? -ne 0 ] || [ -z "$EVAL_OUTPUT" ]; then
            log_eval "Evaluator failed, using fallback"
            EVAL_OUTPUT=$(evaluator_fallback "$PLAN_HASH_BEFORE")
        fi
        stop_canvas

        ACTION="${EVAL_OUTPUT%%|*}"
        REASON="${EVAL_OUTPUT#*|}"
        log_eval "Parallel group — Action: $ACTION — $REASON"

        # Update delivery plan centrally for each phase in the group
        for PHASE_NUM in $PHASE_LIST; do
            update_plan_phase_status "$PHASE_NUM"
            record_phase_end "$PHASE_NUM" "COMPLETE"
            PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        done

        case "$ACTION" in
            continue)
                # Loop back to re-analyze (fresh ordering)
                ;;
            stop)
                OUTER_BREAK=true
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
                    claude --print --session-id "$SESSION_ID" \
                        "${CLI_ARGS[@]}" \
                        --append-system-prompt-file "$PROMPT_FILE" \
                        "$INITIAL_MSG" > "$LOG_FILE" 2>&1 &
                    BUILDER_PID=$!
                    wait "$BUILDER_PID" 2>/dev/null
                    BUILDER_PID=""
                    ;;
                resume)
                    claude --resume "$SESSION_ID" --print \
                        "${CLI_ARGS[@]}" \
                        "Approved. Proceed." >> "$LOG_FILE" 2>&1 &
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
            start_interphase_canvas "Evaluating phase $PHASE_NUM output..."
            EVAL_OUTPUT=$(run_evaluator "$LOG_FILE")

            if [ $? -ne 0 ] || [ -z "$EVAL_OUTPUT" ]; then
                log_eval "Evaluator failed for Phase $PHASE_NUM, using fallback"
                EVAL_OUTPUT=$(evaluator_fallback "$PLAN_HASH_BEFORE")
            fi
            stop_canvas

            ACTION="${EVAL_OUTPUT%%|*}"
            REASON="${EVAL_OUTPUT#*|}"
            log_eval "Phase $PHASE_NUM — Action: $ACTION — $REASON"

            case "$ACTION" in
                continue)
                    update_plan_phase_status "$PHASE_NUM"
                    record_phase_end "$PHASE_NUM" "COMPLETE"
                    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
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
                    if echo "$REASON" | grep -qi "success\|complete\|all phases"; then
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

# ================================================================
# Exit Summary (Section 2.16)
# ================================================================

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

echo "" >&2
printf "${C_BOLD_CYAN}=== Continuous Build Summary ===${C_RESET}\n" >&2
echo "Status: $OVERALL_STATUS" >&2
printf "Duration: ${C_DIM}${DURATION_STR}${C_RESET}\n" >&2
echo "Phases: ${PHASES_COMPLETED}/${INITIAL_PENDING_COUNT} completed" >&2
echo "" >&2

# Per-phase details from metadata files and delivery plan
python3 -c "
import os, re, sys, glob

runtime_dir = sys.argv[1]
plan_path = sys.argv[2]
is_tty = sys.argv[3] == 'true'

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

    # Color based on status
    if status == 'COMPLETE':
        color = GREEN
    elif status == 'INTERRUPTED':
        color = YELLOW
    elif status in ('SKIPPED', 'FAILED'):
        color = RED
    else:
        color = DIM

    print('  {}Phase {} -- {:<30s} {:<14s} {:<10s} features: {}{}'.format(
        color, pnum, label, status, dur_str, features, RESET))
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
echo "Log files: .purlin/runtime/continuous_build_phase_*.log" >&2
printf "${C_BOLD_CYAN}================================${C_RESET}\n" >&2

# Post-run status refresh (Section 2.16)
if [ -f "$CDD_STATUS" ]; then
    echo "" >&2
    bash "$CDD_STATUS" 2>&1
fi

if [ ${#FAILURES[@]} -gt 0 ] || [ "$STOP_REQUESTED" = "true" ]; then
    exit 1
fi
exit 0
