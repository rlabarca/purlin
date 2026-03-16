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
MAX_TURNS=""
MAX_BUDGET_USD=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --continuous) CONTINUOUS=true; shift ;;
        --max-turns) MAX_TURNS="$2"; shift 2 ;;
        --max-budget-usd) MAX_BUDGET_USD="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# --- Prompt assembly ---
PROMPT_FILE=$(mktemp)
cleanup() {
    rm -f "$PROMPT_FILE"
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

# Build pass-through args for claude --print
PASSTHROUGH_ARGS=()
[ -n "$MAX_TURNS" ] && PASSTHROUGH_ARGS+=(--max-turns "$MAX_TURNS")
[ -n "$MAX_BUDGET_USD" ] && PASSTHROUGH_ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

# Tracking variables (file-based retry counts for bash 3 compat)
PHASES_COMPLETED=0
PARALLEL_GROUPS_USED=0
TOTAL_RETRIES=0
FAILURES=()
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
- "Ready to go?" / "Ready to resume?" (approval prompt) -> action: "approve"
- Context exhaustion / checkpoint saved mid-phase -> action: "retry"
- Partial progress (features done but phase incomplete) -> action: "retry"
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

# --- Validate: delivery plan exists ---
if [ ! -f "$DELIVERY_PLAN" ]; then
    echo "Error: No delivery plan found at .purlin/cache/delivery_plan.md" >&2
    exit 1
fi

# --- Run phase analyzer ---
echo "Running phase analyzer..." >&2
ANALYZER_JSON=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>/dev/null)
ANALYZER_RC=$?

if [ $ANALYZER_RC -ne 0 ]; then
    echo "Error: Phase analyzer failed (exit code $ANALYZER_RC)." >&2
    # Re-run to capture stderr
    PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 1>/dev/null 2>&2
    exit 1
fi

if [ -z "$ANALYZER_JSON" ]; then
    echo "Error: Phase analyzer produced no output." >&2
    exit 1
fi

# Extract group count
GROUPS_COUNT=$(printf '%s' "$ANALYZER_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['groups']))")

if [ "$GROUPS_COUNT" = "0" ]; then
    echo "No pending phases to execute." >&2
    exit 0
fi

echo "Phase analyzer found $GROUPS_COUNT execution group(s)." >&2

# ================================================================
# Main orchestration loop
# ================================================================

OUTER_BREAK=false
GROUP_IDX=0

while [ "$GROUP_IDX" -lt "$GROUPS_COUNT" ] && [ "$OUTER_BREAK" = "false" ]; do

    # Extract group info via python
    IS_PARALLEL=$(printf '%s' "$ANALYZER_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['groups'][$GROUP_IDX]['parallel'])")
    PHASE_LIST=$(printf '%s' "$ANALYZER_JSON" | python3 -c "import json,sys; print(' '.join(str(p) for p in json.load(sys.stdin)['groups'][$GROUP_IDX]['phases']))")

    if [ "$IS_PARALLEL" = "True" ]; then
        # ============================================================
        # PARALLEL EXECUTION
        # ============================================================
        PARALLEL_GROUPS_USED=$((PARALLEL_GROUPS_USED + 1))
        echo "Executing parallel group: Phases $PHASE_LIST" >&2

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

            INITIAL_MSG="Begin Builder session. CONTINUOUS MODE -- you are assigned to Phase ${PHASE_NUM} ONLY. Work exclusively on Phase ${PHASE_NUM} features. Do not wait for approval. Do not modify the delivery plan."

            (
                cd "$WT_DIR" || exit 1
                export PURLIN_PROJECT_ROOT="$WT_DIR"
                claude --print "${CLI_ARGS[@]}" "${PASSTHROUGH_ARGS[@]}" \
                    --append-system-prompt-file "$PROMPT_FILE" \
                    "$INITIAL_MSG" > "$LOG_FILE" 2>&1
            ) &

            WT_PIDS+=($!)
            WT_DIRS+=("$WT_DIR")
            WT_BRANCHES+=("$WT_BRANCH")
            WT_LOGS+=("$LOG_FILE")
            WT_PHASES+=("$PHASE_NUM")
        done

        # Wait for all parallel builders to complete
        for pid in "${WT_PIDS[@]}"; do
            wait "$pid" 2>/dev/null
        done

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

        # Evaluate using the last parallel log
        PLAN_HASH_BEFORE=$(get_plan_hash)
        LAST_LOG="${WT_LOGS[${#WT_LOGS[@]}-1]}"
        EVAL_OUTPUT=$(run_evaluator "$LAST_LOG")

        if [ $? -ne 0 ] || [ -z "$EVAL_OUTPUT" ]; then
            log_eval "Evaluator failed, using fallback"
            EVAL_OUTPUT=$(evaluator_fallback "$PLAN_HASH_BEFORE")
        fi

        ACTION="${EVAL_OUTPUT%%|*}"
        REASON="${EVAL_OUTPUT#*|}"
        log_eval "Parallel group — Action: $ACTION — $REASON"

        # Update delivery plan centrally for each phase in the group
        for PHASE_NUM in $PHASE_LIST; do
            update_plan_phase_status "$PHASE_NUM"
            PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        done

        case "$ACTION" in
            continue)
                GROUP_IDX=$((GROUP_IDX + 1))
                ;;
            stop)
                OUTER_BREAK=true
                ;;
            *)
                GROUP_IDX=$((GROUP_IDX + 1))
                ;;
        esac

    else
        # ============================================================
        # SEQUENTIAL EXECUTION
        # ============================================================
        PHASE_NUM=$(echo "$PHASE_LIST" | awk '{print $1}')
        echo "Executing sequential Phase $PHASE_NUM..." >&2

        SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
        LOG_FILE="${RUNTIME_DIR}/continuous_build_phase_${PHASE_NUM}.log"
        INITIAL_MSG="Begin Builder session. CONTINUOUS MODE -- proceed immediately with work plan, do not wait for approval."
        RUN_ACTION="run"

        # Inner loop for evaluate-act cycle (handles approve and retry)
        while true; do
            PLAN_HASH_BEFORE=$(get_plan_hash)

            # Execute Builder based on action type
            case "$RUN_ACTION" in
                run|retry)
                    claude --print --session-id "$SESSION_ID" \
                        "${CLI_ARGS[@]}" "${PASSTHROUGH_ARGS[@]}" \
                        --append-system-prompt-file "$PROMPT_FILE" \
                        "$INITIAL_MSG" > "$LOG_FILE" 2>&1
                    ;;
                resume)
                    claude --resume "$SESSION_ID" --print \
                        "${CLI_ARGS[@]}" "${PASSTHROUGH_ARGS[@]}" \
                        "Approved. Proceed." >> "$LOG_FILE" 2>&1
                    ;;
            esac

            # Run evaluator
            EVAL_OUTPUT=$(run_evaluator "$LOG_FILE")

            if [ $? -ne 0 ] || [ -z "$EVAL_OUTPUT" ]; then
                log_eval "Evaluator failed for Phase $PHASE_NUM, using fallback"
                EVAL_OUTPUT=$(evaluator_fallback "$PLAN_HASH_BEFORE")
            fi

            ACTION="${EVAL_OUTPUT%%|*}"
            REASON="${EVAL_OUTPUT#*|}"
            log_eval "Phase $PHASE_NUM — Action: $ACTION — $REASON"

            case "$ACTION" in
                continue)
                    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
                    GROUP_IDX=$((GROUP_IDX + 1))
                    break
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
                        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
                    else
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
# Exit Summary
# ================================================================

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "" >&2
echo "=== Continuous Build Summary ===" >&2
echo "Phases completed: $PHASES_COMPLETED" >&2
echo "Execution groups: $GROUPS_COUNT ($PARALLEL_GROUPS_USED parallel)" >&2
echo "Retries consumed: $TOTAL_RETRIES" >&2
if [ ${#FAILURES[@]} -gt 0 ]; then
    echo "Failures: ${FAILURES[*]}" >&2
fi
echo "Total duration: ${DURATION}s" >&2
echo "================================" >&2

if [ ${#FAILURES[@]} -gt 0 ]; then
    exit 1
fi
exit 0
