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
MAX_BUDGET_USD=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --continuous) CONTINUOUS=true; shift ;;
        --max-budget-usd) MAX_BUDGET_USD="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# --- Prompt assembly ---
PROMPT_FILE=$(mktemp)
PARALLEL_PROMPT_FILE=""
BOOTSTRAP_PROMPT_FILE=""
cleanup() {
    rm -f "$PROMPT_FILE"
    [ -n "$PARALLEL_PROMPT_FILE" ] && rm -f "$PARALLEL_PROMPT_FILE"
    [ -n "$BOOTSTRAP_PROMPT_FILE" ] && rm -f "$BOOTSTRAP_PROMPT_FILE"
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

# Build pass-through args for claude --print
PASSTHROUGH_ARGS=()
[ -n "$MAX_BUDGET_USD" ] && PASSTHROUGH_ARGS+=(--max-budget-usd "$MAX_BUDGET_USD")

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

# --- Bootstrap session when no delivery plan exists (Section 2.15) ---
if [ ! -f "$DELIVERY_PLAN" ]; then
    echo "No delivery plan found. Starting bootstrap session..." >&2
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

    BOOTSTRAP_SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    claude --print --session-id "$BOOTSTRAP_SESSION_ID" \
        "${CLI_ARGS[@]}" "${PASSTHROUGH_ARGS[@]}" \
        --append-system-prompt-file "$BOOTSTRAP_PROMPT_FILE" \
        "Begin Builder session." > "$BOOTSTRAP_LOG" 2>&1
    BOOTSTRAP_RC=$?
    rm -f "$BOOTSTRAP_PROMPT_FILE"
    BOOTSTRAP_PROMPT_FILE=""

    # Outcome detection via file-existence checking, not output parsing
    if [ -f "$DELIVERY_PLAN" ]; then
        # Plan created -> validate with phase analyzer dry-run
        echo "Bootstrap created a delivery plan. Validating..." >&2
        VALIDATE_OUTPUT=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>&1)
        VALIDATE_RC=$?

        if [ $VALIDATE_RC -ne 0 ]; then
            echo "Plan validation failed:" >&2
            echo "$VALIDATE_OUTPUT" | head -20 >&2
            echo "The plan has been committed for manual editing." >&2
            echo "Fix the plan at .purlin/cache/delivery_plan.md and re-run --continuous." >&2
            exit 0
        fi

        # Print plan summary and prompt for approval
        PHASE_SUMMARY=$(python3 -c "
import re
with open('$DELIVERY_PLAN') as f:
    content = f.read()
phases = re.findall(r'## Phase \d+ -- .+? \[(PENDING|IN_PROGRESS|COMPLETE)\]', content)
pending = sum(1 for s in phases if s == 'PENDING')
print(f'{len(phases)} phases ({pending} pending)')
" 2>/dev/null || echo "unknown")

        echo "" >&2
        echo "Delivery plan created ($PHASE_SUMMARY). Review at .purlin/cache/delivery_plan.md." >&2
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

# ================================================================
# Main orchestration loop (re-analyzes before each execution group)
# ================================================================

OUTER_BREAK=false

while [ "$OUTER_BREAK" = "false" ]; do

    # Re-run phase analyzer before each execution group
    echo "Running phase analyzer..." >&2
    ANALYZER_JSON=$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$PHASE_ANALYZER" 2>/dev/null)
    ANALYZER_RC=$?

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
        echo "No pending phases to execute." >&2
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

            INITIAL_MSG="Begin Builder session. CONTINUOUS MODE -- you are assigned to Phase ${PHASE_NUM} ONLY. Work exclusively on Phase ${PHASE_NUM} features. Do not wait for approval."

            (
                cd "$WT_DIR" || exit 1
                export PURLIN_PROJECT_ROOT="$WT_DIR"
                claude --print "${CLI_ARGS[@]}" "${PASSTHROUGH_ARGS[@]}" \
                    --append-system-prompt-file "$PARALLEL_PROMPT_FILE" \
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

        # Process plan amendment files from parallel builders
        apply_plan_amendments

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

            # Detect plan amendments by sequential Builder
            PLAN_HASH_AFTER=$(get_plan_hash)
            if [ "$PLAN_HASH_BEFORE" != "$PLAN_HASH_AFTER" ]; then
                PLAN_AMENDED=true
            fi

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
                    update_plan_phase_status "$PHASE_NUM"
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
echo "Execution groups: $GROUPS_EXECUTED ($PARALLEL_GROUPS_USED parallel)" >&2
echo "Retries consumed: $TOTAL_RETRIES" >&2
if [ "$PLAN_AMENDED" = "true" ]; then
    echo "Note: delivery plan was amended during execution" >&2
fi
if [ ${#FAILURES[@]} -gt 0 ]; then
    echo "Failures: ${FAILURES[*]}" >&2
fi
echo "Total duration: ${DURATION}s" >&2
echo "================================" >&2

if [ ${#FAILURES[@]} -gt 0 ]; then
    exit 1
fi
exit 0
