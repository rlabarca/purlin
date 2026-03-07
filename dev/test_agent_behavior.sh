#!/usr/bin/env bash
# dev/test_agent_behavior.sh
#
# Agent Behavior Test Harness
# Tests agent startup, resume, and help behavior using claude --print
# in single-turn mode against fixture repo states.
#
# See features/agent_behavior_tests.md for full specification.
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

# --- Defaults ---
MODEL="claude-haiku-4-5-20251001"
FIXTURE_REPO=""
WRITE_RESULTS=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE_TOOL="$PROJECT_ROOT/tools/test_support/fixture.sh"

# --- Counters ---
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0
TEST_DETAILS_JSON="[]"

# --- Current fixture dir (for cleanup tracking) ---
CURRENT_FIXTURE_DIR=""
PREVIOUS_FIXTURE_DIR=""

usage() {
    cat <<'USAGE'
Usage: test_agent_behavior.sh --fixture-repo <path-or-url> [options]

Agent behavior test harness. Runs claude --print against fixture repo
states to verify agent startup, resume, and help behavior.

Options:
  --fixture-repo <url>   Path or URL to fixture repo (required)
  --model <model>        Claude model (default: claude-haiku-4-5-20251001)
  --write-results        Write tests.json to tests/agent_behavior_tests/
  -h, --help             Show this help

Examples:
  # Run with local fixture repo
  ./dev/test_agent_behavior.sh --fixture-repo /tmp/purlin-behavior-fixtures

  # Run with specific model and write results
  ./dev/test_agent_behavior.sh --fixture-repo /tmp/purlin-behavior-fixtures \
      --model claude-sonnet-4-6 --write-results
USAGE
    exit 1
}

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fixture-repo) FIXTURE_REPO="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --write-results) WRITE_RESULTS=true; shift ;;
        -h|--help) usage ;;
        *) echo "Error: Unknown option: $1" >&2; usage ;;
    esac
done

if [[ -z "$FIXTURE_REPO" ]]; then
    echo "Error: --fixture-repo is required" >&2
    usage
fi

# --- Helper Functions ---

construct_prompt() {
    # Build the 4-layer system prompt from fixture instruction files.
    # Args: $1 = fixture checkout dir, $2 = role (BUILDER, ARCHITECT, QA)
    # Prints: path to temp file containing concatenated prompt
    local fixture_dir="$1"
    local role="$2"
    local prompt_file
    prompt_file="$(mktemp)"

    local layers=(
        "$fixture_dir/instructions/HOW_WE_WORK_BASE.md"
        "$fixture_dir/instructions/${role}_BASE.md"
        "$fixture_dir/.purlin/HOW_WE_WORK_OVERRIDES.md"
        "$fixture_dir/.purlin/${role}_OVERRIDES.md"
    )

    for layer in "${layers[@]}"; do
        if [[ -f "$layer" ]]; then
            cat "$layer" >> "$prompt_file"
            printf '\n\n' >> "$prompt_file"
        fi
    done

    echo "$prompt_file"
}

run_claude_test() {
    # Run claude --print with constructed system prompt.
    # Args: $1 = prompt file, $2 = trigger message, $3 = working dir
    # Prints: Claude's text response (extracted from JSON)
    local prompt_file="$1"
    local trigger="$2"
    local work_dir="${3:-$PWD}"

    local raw_output
    raw_output=$(cd "$work_dir" && claude --print \
        --no-session-persistence \
        --model "$MODEL" \
        --append-system-prompt-file "$prompt_file" \
        --output-format json \
        "$trigger" 2>/dev/null) || true

    # Extract text from JSON response
    local text
    text=$(echo "$raw_output" | jq -r '.result // empty' 2>/dev/null) || true

    if [[ -z "$text" ]]; then
        # Fallback: try raw output if jq parsing fails
        text="$raw_output"
    fi

    echo "$text"
}

assert_contains() {
    # Assert that output contains a pattern (case-insensitive).
    # Args: $1 = output, $2 = pattern
    # Returns: 0 if found, 1 if not
    local output="$1"
    local pattern="$2"

    if echo "$output" | grep -qi "$pattern"; then
        return 0
    else
        return 1
    fi
}

assert_not_contains() {
    # Assert that output does NOT contain a pattern (case-insensitive).
    local output="$1"
    local pattern="$2"

    if echo "$output" | grep -qi "$pattern"; then
        return 1
    else
        return 0
    fi
}

record_result() {
    # Record a test result.
    # Args: $1 = PASS|FAIL, $2 = description, $3 = detail (optional)
    local status="$1"
    local description="$2"
    local detail="${3:-}"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    if [[ "$status" == "PASS" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo "PASS: $description"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "FAIL: $description"
        if [[ -n "$detail" ]]; then
            echo "  Detail: $detail"
        fi
    fi

    # Append to JSON details
    local entry
    if [[ -n "$detail" ]]; then
        entry=$(jq -n --arg t "$description" --arg s "$status" --arg d "$detail" \
            '{test: $t, status: $s, detail: $d}')
    else
        entry=$(jq -n --arg t "$description" --arg s "$status" \
            '{test: $t, status: $s}')
    fi
    TEST_DETAILS_JSON=$(echo "$TEST_DETAILS_JSON" | jq ". + [$entry]")
}

checkout_fixture() {
    # Check out a fixture tag. Prints the checkout path.
    local tag="$1"
    PREVIOUS_FIXTURE_DIR="$CURRENT_FIXTURE_DIR"
    local path
    path=$(bash "$FIXTURE_TOOL" checkout "$FIXTURE_REPO" "$tag")
    CURRENT_FIXTURE_DIR="$path"
    echo "$path"
}

cleanup_fixture() {
    # Clean up a fixture checkout directory.
    local path="$1"
    bash "$FIXTURE_TOOL" cleanup "$path"
    if [[ "$CURRENT_FIXTURE_DIR" == "$path" ]]; then
        CURRENT_FIXTURE_DIR=""
    fi
}

# --- Scenario Functions ---
# Each function:
#   1. Checks out the appropriate fixture
#   2. Constructs the system prompt
#   3. Runs claude --print
#   4. Asserts expected patterns
#   5. Cleans up

scenario_startup_print_sequence() {
    echo ""
    echo "--- Scenario 1: Startup Print Sequence Appears First ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/cdd_startup_controls/startup-print-sequence")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")
    output=$(run_claude_test "$prompt_file" "Begin Builder session." "$fixture_dir")

    if assert_contains "$output" "━━━"; then
        record_result "PASS" "Startup Print Sequence: command table present"
    else
        record_result "FAIL" "Startup Print Sequence: command table present" \
            "Expected Unicode horizontal rule (━━━) in output"
    fi

    if assert_contains "$output" "Purlin Builder"; then
        record_result "PASS" "Startup Print Sequence: Builder header present"
    else
        record_result "FAIL" "Startup Print Sequence: Builder header present" \
            "Expected 'Purlin Builder' in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_expert_mode() {
    echo ""
    echo "--- Scenario 2: Expert Mode Bypasses Orientation ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/cdd_startup_controls/expert-mode")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")
    output=$(run_claude_test "$prompt_file" "Begin Builder session." "$fixture_dir")

    if assert_contains "$output" "startup_sequence disabled"; then
        record_result "PASS" "Expert Mode: disabled message present"
    else
        record_result "FAIL" "Expert Mode: disabled message present" \
            "Expected 'startup_sequence disabled' in output"
    fi

    if assert_not_contains "$output" "Action Items\|Work Plan\|Feature Queue"; then
        record_result "PASS" "Expert Mode: no work plan present"
    else
        record_result "FAIL" "Expert Mode: no work plan present" \
            "Output should NOT contain work plan sections"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_guided_mode() {
    echo ""
    echo "--- Scenario 3: Guided Mode Presents Work Plan ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/cdd_startup_controls/guided-mode")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")
    output=$(run_claude_test "$prompt_file" "Begin Builder session." "$fixture_dir")

    if assert_contains "$output" "━━━"; then
        record_result "PASS" "Guided Mode: command table present"
    else
        record_result "FAIL" "Guided Mode: command table present" \
            "Expected command table in output"
    fi

    # Guided mode should attempt to present action items or work plan
    if assert_contains "$output" "action\|work plan\|feature\|TODO\|implement"; then
        record_result "PASS" "Guided Mode: work plan or action items present"
    else
        record_result "FAIL" "Guided Mode: work plan or action items present" \
            "Expected work plan content in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_orient_only_mode() {
    echo ""
    echo "--- Scenario 4: Orient-Only Mode Skips Work Plan ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/cdd_startup_controls/orient-only-mode")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")
    output=$(run_claude_test "$prompt_file" "Begin Builder session." "$fixture_dir")

    if assert_contains "$output" "━━━"; then
        record_result "PASS" "Orient-Only Mode: command table present"
    else
        record_result "FAIL" "Orient-Only Mode: command table present" \
            "Expected command table in output"
    fi

    # Orient-only should gather state but not present a work plan
    if assert_not_contains "$output" "Ready to go.*adjust the plan"; then
        record_result "PASS" "Orient-Only Mode: no work plan prompt"
    else
        record_result "FAIL" "Orient-Only Mode: no work plan prompt" \
            "Output should NOT contain 'Ready to go' prompt"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_builder_mid_feature_resume() {
    echo ""
    echo "--- Scenario 5: Builder Mid-Feature Resume ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/pl_session_resume/builder-mid-feature")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")
    output=$(run_claude_test "$prompt_file" "/pl-resume" "$fixture_dir")

    if assert_contains "$output" "my_feature\|sample_feature"; then
        record_result "PASS" "Builder Resume: checkpoint feature name echoed"
    else
        record_result "FAIL" "Builder Resume: checkpoint feature name echoed" \
            "Expected checkpoint feature name in output"
    fi

    if assert_contains "$output" "Context Restored\|Resume Point\|Checkpoint"; then
        record_result "PASS" "Builder Resume: recovery summary present"
    else
        record_result "FAIL" "Builder Resume: recovery summary present" \
            "Expected recovery summary in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_qa_mid_verification_resume() {
    echo ""
    echo "--- Scenario 6: QA Mid-Verification Resume ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/pl_session_resume/qa-mid-verification")
    prompt_file=$(construct_prompt "$fixture_dir" "QA")
    output=$(run_claude_test "$prompt_file" "/pl-resume" "$fixture_dir")

    if assert_contains "$output" "scenario\|verification\|6 of 8\|6/8"; then
        record_result "PASS" "QA Resume: scenario progress echoed"
    else
        record_result "FAIL" "QA Resume: scenario progress echoed" \
            "Expected scenario progress info in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_full_reboot_resume() {
    echo ""
    echo "--- Scenario 7: Full Reboot Without Launcher ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/pl_session_resume/full-reboot-no-launcher")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")
    output=$(run_claude_test "$prompt_file" "/pl-resume" "$fixture_dir")

    if assert_contains "$output" "Role\|Builder\|Architect\|QA"; then
        record_result "PASS" "Full Reboot: role detection occurs"
    else
        record_result "FAIL" "Full Reboot: role detection occurs" \
            "Expected role reference in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_architect_main_help() {
    echo ""
    echo "--- Scenario 8: Architect Re-displays Command Table ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/pl_help/architect-main-branch")
    prompt_file=$(construct_prompt "$fixture_dir" "ARCHITECT")
    output=$(run_claude_test "$prompt_file" "/pl-help" "$fixture_dir")

    if assert_contains "$output" "━━━"; then
        record_result "PASS" "Architect Help: command table present"
    else
        record_result "FAIL" "Architect Help: command table present" \
            "Expected command table in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_builder_isolated_help() {
    echo ""
    echo "--- Scenario 9: Builder Re-displays Command Table on Isolated Branch ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/pl_help/builder-isolated-branch")
    prompt_file=$(construct_prompt "$fixture_dir" "BUILDER")

    # The fixture should be on an isolated branch
    output=$(run_claude_test "$prompt_file" "/pl-help" "$fixture_dir")

    if assert_contains "$output" "Isolated\|isolated"; then
        record_result "PASS" "Builder Isolated Help: isolated variant detected"
    else
        record_result "FAIL" "Builder Isolated Help: isolated variant detected" \
            "Expected 'Isolated' in output for isolated branch variant"
    fi

    if assert_contains "$output" "pl-isolated-push\|pl-isolated-pull"; then
        record_result "PASS" "Builder Isolated Help: isolation commands present"
    else
        record_result "FAIL" "Builder Isolated Help: isolation commands present" \
            "Expected isolation-specific commands in output"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_qa_collab_help() {
    echo ""
    echo "--- Scenario 10: QA Re-displays Command Table on Collaboration Branch ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture "main/pl_help/qa-collab-branch")
    prompt_file=$(construct_prompt "$fixture_dir" "QA")
    output=$(run_claude_test "$prompt_file" "/pl-help" "$fixture_dir")

    if assert_contains "$output" "Branch\|collab"; then
        record_result "PASS" "QA Collab Help: branch collaboration variant detected"
    else
        record_result "FAIL" "QA Collab Help: branch collaboration variant detected" \
            "Expected 'Branch' in output for collab variant"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

# --- Summary and Results ---

print_summary() {
    echo ""
    echo "========================================="
    echo "${TESTS_PASSED}/${TESTS_TOTAL} tests passed"
    echo "========================================="
}

write_results() {
    if [[ "$WRITE_RESULTS" != true ]]; then
        return
    fi

    local out_dir="$PROJECT_ROOT/tests/agent_behavior_tests"
    mkdir -p "$out_dir"

    local status="PASS"
    if [[ "$TESTS_FAILED" -gt 0 ]]; then
        status="FAIL"
    fi

    local results
    results=$(jq -n \
        --arg status "$status" \
        --argjson tests_run "$TESTS_TOTAL" \
        --argjson failures "$TESTS_FAILED" \
        --argjson details "$TEST_DETAILS_JSON" \
        '{
            status: $status,
            tests_run: $tests_run,
            failures: $failures,
            errors: 0,
            details: $details
        }')

    echo "$results" > "$out_dir/tests.json"
    echo "Results written to $out_dir/tests.json"
}

# --- Main ---
main() {
    echo "Agent Behavior Test Harness"
    echo "Model: $MODEL"
    echo "Fixture repo: $FIXTURE_REPO"
    echo ""

    # Run all scenarios
    scenario_startup_print_sequence
    scenario_expert_mode
    scenario_guided_mode
    scenario_orient_only_mode
    scenario_builder_mid_feature_resume
    scenario_qa_mid_verification_resume
    scenario_full_reboot_resume
    scenario_architect_main_help
    scenario_builder_isolated_help
    scenario_qa_collab_help

    print_summary
    write_results

    if [[ "$TESTS_FAILED" -gt 0 ]]; then
        exit 1
    fi
}

main
