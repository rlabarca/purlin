#!/usr/bin/env bash
# dev/regression_runner.sh
#
# Regression Runner
# Dispatches test harnesses in two modes:
#   --watch: polls for trigger files and executes harnesses continuously
#   --once <harness> [args...]: runs a single harness invocation and exits
#
# See features/regression_testing.md for full specification.
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"
TRIGGER_FILE="$RUNTIME_DIR/regression_trigger.json"
RESULT_FILE="$RUNTIME_DIR/regression_result.json"

# Defaults
MODE=""
TIMEOUT=300
HARNESS=""
HARNESS_ARGS=()

# Watch mode session tracking
EXECUTIONS=()
SESSION_PASS=0
SESSION_FAIL=0

usage() {
    cat <<'USAGE'
Usage: regression_runner.sh [options]

Regression Runner. Dispatches harnesses for regression testing.

Modes:
  --watch                 Poll for trigger files and execute harnesses
  --once <harness> [args] Run a single harness invocation and exit

Options:
  --timeout <seconds>     Per-execution timeout (default: 300)
  -h, --help              Show this help

Watch Mode:
  Polls .purlin/runtime/regression_trigger.json at 1-second intervals.
  When a trigger appears, executes the specified harness, writes
  .purlin/runtime/regression_result.json, deletes the trigger, and resumes.
  SIGINT prints a session summary and exits cleanly.

Once Mode:
  Runs the specified harness, writes a result file, and exits with
  the harness exit code.

Trigger format (.purlin/runtime/regression_trigger.json):
  {"harness": "dev/test_agent_interactions.sh", "args": ["--write-results"]}

USAGE
}

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --watch)
            MODE="watch"
            shift
            ;;
        --once)
            MODE="once"
            shift
            if [[ $# -eq 0 ]]; then
                echo "Error: --once requires a harness path" >&2
                exit 1
            fi
            HARNESS="$1"
            shift
            # Remaining args are harness args (until --timeout or help flags)
            while [[ $# -gt 0 ]] && [[ "$1" != --timeout ]] && [[ "$1" != -h ]] && [[ "$1" != --help ]]; do
                HARNESS_ARGS+=("$1")
                shift
            done
            ;;
        --timeout)
            shift
            if [[ $# -eq 0 ]]; then
                echo "Error: --timeout requires a value" >&2
                exit 1
            fi
            TIMEOUT="$1"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$MODE" ]]; then
    echo "Error: specify --watch or --once <harness>" >&2
    usage
    exit 1
fi

# Ensure runtime directory exists
mkdir -p "$RUNTIME_DIR"

# --- Execute a harness and write result ---
execute_harness() {
    local harness="$1"
    shift
    local started_at
    started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    echo "[$started_at] Executing: $harness $*"

    local exit_code=0
    local harness_path="$PROJECT_ROOT/$harness"

    if [[ ! -f "$harness_path" ]]; then
        echo "Error: harness not found: $harness_path" >&2
        exit_code=127
    else
        # Run harness with timeout using a portable approach:
        # Start harness in its own process group, then kill group on timeout.
        if command -v gtimeout &>/dev/null; then
            gtimeout "$TIMEOUT" bash "$harness_path" "$@" || exit_code=$?
        elif command -v timeout &>/dev/null; then
            timeout "$TIMEOUT" bash "$harness_path" "$@" || exit_code=$?
        else
            # macOS fallback: background job + polling kill
            bash "$harness_path" "$@" </dev/null &
            local bg_pid=$!
            local elapsed=0
            while kill -0 "$bg_pid" 2>/dev/null; do
                if [[ "$elapsed" -ge "$TIMEOUT" ]]; then
                    # Kill children first, then parent
                    pkill -TERM -P "$bg_pid" 2>/dev/null || true
                    kill -TERM "$bg_pid" 2>/dev/null || true
                    sleep 1
                    pkill -KILL -P "$bg_pid" 2>/dev/null || true
                    kill -KILL "$bg_pid" 2>/dev/null || true
                    wait "$bg_pid" 2>/dev/null || true
                    exit_code=142
                    break
                fi
                sleep 1
                ((elapsed++))
            done
            if [[ "$exit_code" -eq 0 ]]; then
                wait "$bg_pid" 2>/dev/null || exit_code=$?
            fi
        fi
    fi

    local completed_at
    completed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    # Detect regression.json path from harness --write-results convention
    local tests_json_path=""
    local summary=""
    # Look for the most recently modified regression.json under tests/
    local latest_json
    latest_json="$(find "$PROJECT_ROOT/tests" -name 'regression.json' -newer "$RESULT_FILE" 2>/dev/null | head -1 || true)"
    if [[ -n "$latest_json" ]]; then
        tests_json_path="$(python3 -c "import os; print(os.path.relpath('$latest_json', '$PROJECT_ROOT'))" 2>/dev/null || echo "$latest_json")"
        summary="$(python3 -c "
import json, sys
try:
    d = json.load(open('$latest_json'))
    print(f\"{d.get('passed', '?')}/{d.get('total', '?')} passed\")
except Exception:
    print('unknown')
" 2>/dev/null || echo "unknown")"
    fi

    # Write result file
    python3 -c "
import json
result = {
    'harness': '$harness',
    'exit_code': $exit_code,
    'started_at': '$started_at',
    'completed_at': '$completed_at',
    'tests_json_path': '$tests_json_path',
    'summary': '$summary'
}
with open('$RESULT_FILE', 'w') as f:
    json.dump(result, f, indent=2)
"
    echo "[$completed_at] Result: exit_code=$exit_code summary=$summary"

    # Track for session summary
    EXECUTIONS+=("$harness:$exit_code:$summary")
    if [[ "$exit_code" -eq 0 ]]; then
        ((SESSION_PASS++)) || true
    else
        ((SESSION_FAIL++)) || true
    fi

    return "$exit_code"
}

# --- Watch mode ---
print_session_summary() {
    echo ""
    echo "=== Regression Session Summary ==="
    echo "Total executions: ${#EXECUTIONS[@]}"
    echo "Passed: $SESSION_PASS  Failed: $SESSION_FAIL"
    echo ""
    if [[ ${#EXECUTIONS[@]} -gt 0 ]]; then
        for exec_entry in "${EXECUTIONS[@]}"; do
            IFS=':' read -r h ec sm <<< "$exec_entry"
            local status_label="PASS"
            if [[ "$ec" -ne 0 ]]; then
                status_label="FAIL"
            fi
            echo "  [$status_label] $h (exit=$ec, $sm)"
        done
    fi
    echo "=== End Summary ==="
}

if [[ "$MODE" == "watch" ]]; then
    # Trap SIGINT for clean shutdown with summary
    trap 'print_session_summary; exit 0' INT

    echo "Regression Runner: watch mode (timeout=${TIMEOUT}s)"
    echo "Polling: $TRIGGER_FILE"
    echo "Press Ctrl+C to stop and see session summary."
    echo ""

    # Create initial result file for timestamp comparison
    touch "$RESULT_FILE"

    while true; do
        if [[ -f "$TRIGGER_FILE" ]]; then
            # Parse trigger
            parsed_harness=""
            parsed_args_json="[]"
            if python3 -c "
import json, sys
try:
    d = json.load(open('$TRIGGER_FILE'))
    print(d.get('harness', ''))
    print(json.dumps(d.get('args', [])))
except (json.JSONDecodeError, KeyError, TypeError) as e:
    print('__MALFORMED__')
    print(str(e))
" > /tmp/regression_trigger_parsed.txt 2>&1; then
                parsed_harness="$(sed -n '1p' /tmp/regression_trigger_parsed.txt)"
                parsed_args_json="$(sed -n '2p' /tmp/regression_trigger_parsed.txt)"
            fi

            if [[ "$parsed_harness" == "__MALFORMED__" ]] || [[ -z "$parsed_harness" ]]; then
                echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Error: malformed trigger file, deleting"
                rm -f "$TRIGGER_FILE"
                sleep 1
                continue
            fi

            # Parse args array into positional args
            trigger_args=()
            while IFS= read -r arg; do
                [[ -n "$arg" ]] && trigger_args+=("$arg")
            done < <(python3 -c "
import json
args = json.loads('$parsed_args_json')
for a in args:
    print(a)
" 2>/dev/null)

            # Delete trigger before execution (prevent re-trigger)
            rm -f "$TRIGGER_FILE"

            if [[ ${#trigger_args[@]} -gt 0 ]]; then
                execute_harness "$parsed_harness" "${trigger_args[@]}" || true
            else
                execute_harness "$parsed_harness" || true
            fi
        fi
        sleep 1
    done
fi

# --- Once mode ---
if [[ "$MODE" == "once" ]]; then
    # Create initial result file for timestamp comparison
    touch "$RESULT_FILE"

    if [[ ${#HARNESS_ARGS[@]} -gt 0 ]]; then
        execute_harness "$HARNESS" "${HARNESS_ARGS[@]}"
    else
        execute_harness "$HARNESS"
    fi
    exit $?
fi
