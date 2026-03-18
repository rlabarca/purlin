#!/usr/bin/env bash
# dev/test_agent_interactions.sh
#
# AFT Agent Interaction Test Harness
# Tests agent interaction scenarios using claude --print with
# session-based multi-turn support against fixture repo states.
#
# See features/aft_agent.md for full specification.
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

# --- Defaults ---
MODEL="claude-haiku-4-5-20251001"
FIXTURE_REPO=""
WRITE_RESULTS=false
SCENARIO_FILTER=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE_TOOL="$PROJECT_ROOT/tools/test_support/fixture.sh"

# --- Counters ---
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
TESTS_TOTAL=0
TEST_DETAILS_JSON="[]"

# --- Session state ---
CURRENT_FIXTURE_DIR=""
SESSION_ID=""

usage() {
    cat <<'USAGE'
Usage: test_agent_interactions.sh [options]

AFT Agent interaction test harness. Runs claude --print against fixture
repo states to verify agent interaction scenarios (single-turn and
multi-turn).

Options:
  --fixture-repo <url>   Path or URL to fixture repo (default: .purlin/runtime/fixture-repo)
                         Auto-created via dev/setup_fixture_repo.sh if missing
  --model <model>        Claude model (default: claude-haiku-4-5-20251001)
  --scenario <name>      Run only the named scenario (e.g., instruction-audit-halt)
  --write-results        Write tests.json to tests/aft_agent/
  -h, --help             Show this help

Examples:
  # Run all scenarios
  ./dev/test_agent_interactions.sh

  # Run single scenario
  ./dev/test_agent_interactions.sh --scenario instruction-audit-halt

  # Run with specific model and write results
  ./dev/test_agent_interactions.sh --model claude-sonnet-4-6 --write-results
USAGE
    exit 1
}

# --- Argument Parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --fixture-repo) FIXTURE_REPO="$2"; shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --scenario) SCENARIO_FILTER="$2"; shift 2 ;;
        --write-results) WRITE_RESULTS=true; shift ;;
        -h|--help) usage ;;
        *) echo "Error: Unknown option: $1" >&2; usage ;;
    esac
done

if [[ -z "$FIXTURE_REPO" ]]; then
    FIXTURE_REPO="$PROJECT_ROOT/.purlin/runtime/fixture-repo"
fi

# Auto-create fixture repo if it doesn't exist
if [[ ! -d "$FIXTURE_REPO" ]]; then
    echo "Fixture repo not found at: $FIXTURE_REPO"
    echo "Auto-creating via dev/setup_fixture_repo.sh..."
    bash "$SCRIPT_DIR/setup_fixture_repo.sh" "$FIXTURE_REPO"
    echo ""
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

construct_release_prompt() {
    # Build system prompt including release step agent_instructions.
    # Args: $1 = fixture checkout dir, $2 = role, $3 = step_id
    # Prints: path to temp file containing full prompt with step instructions
    local fixture_dir="$1"
    local role="$2"
    local step_id="$3"

    # Start with standard 4-layer prompt
    local prompt_file
    prompt_file=$(construct_prompt "$fixture_dir" "$role")

    # Find global_steps.json: fixture first, then project fallback
    local steps_file="$fixture_dir/tools/release/global_steps.json"
    if [[ ! -f "$steps_file" ]]; then
        steps_file="$fixture_dir/.purlin/release/local_steps.json"
    fi
    if [[ ! -f "$steps_file" ]]; then
        steps_file="$PROJECT_ROOT/tools/release/global_steps.json"
    fi

    if [[ -f "$steps_file" ]]; then
        local instructions
        instructions=$(jq -r --arg id "$step_id" \
            '.steps[] | select(.id == $id) | .agent_instructions // empty' \
            "$steps_file" 2>/dev/null) || true

        if [[ -n "$instructions" ]]; then
            printf '\n\n## Release Step Instructions\n\n%s\n' "$instructions" >> "$prompt_file"
        fi
    fi

    echo "$prompt_file"
}

run_claude_test() {
    # Run claude --print (single-turn, no session persistence).
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

run_claude_turn() {
    # Run a single turn of a multi-turn conversation.
    # First call (SESSION_ID empty) creates a session; subsequent calls resume it.
    # Args: $1 = prompt file, $2 = message, $3 = working dir
    # Prints: Claude's text response
    local prompt_file="$1"
    local message="$2"
    local work_dir="${3:-$PWD}"

    local session_args=()
    if [[ -n "$SESSION_ID" ]]; then
        # Subsequent turn: resume existing session
        session_args+=(--resume "$SESSION_ID")
    else
        # First turn: create named session
        SESSION_ID="aft-agent-$(date +%s)-$$"
        session_args+=(--session-id "$SESSION_ID")
        session_args+=(--append-system-prompt-file "$prompt_file")
    fi

    local raw_output
    raw_output=$(cd "$work_dir" && claude --print \
        --model "$MODEL" \
        --output-format json \
        "${session_args[@]}" \
        "$message" 2>/dev/null) || true

    local text
    text=$(echo "$raw_output" | jq -r '.result // empty' 2>/dev/null) || true

    if [[ -z "$text" ]]; then
        text="$raw_output"
    fi

    echo "$text"
}

reset_session() {
    SESSION_ID=""
}

checkout_fixture_safe() {
    # Check out a fixture tag. Prints checkout path on success.
    # Prints "SKIP:<tag>" and returns 1 if tag doesn't exist.
    local tag="$1"

    # Check if tag exists in fixture repo
    if ! git -C "$FIXTURE_REPO" rev-parse "refs/tags/$tag" >/dev/null 2>&1; then
        echo "SKIP:$tag"
        return 1
    fi

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

assert_contains() {
    # Assert that output contains a pattern (case-insensitive).
    local output="$1"
    local pattern="$2"
    echo "$output" | grep -qi "$pattern"
}

assert_not_contains() {
    # Assert that output does NOT contain a pattern (case-insensitive).
    local output="$1"
    local pattern="$2"
    ! echo "$output" | grep -qi "$pattern"
}

record_result() {
    # Record a test result (PASS, FAIL, or SKIP).
    # Args: $1 = PASS|FAIL|SKIP, $2 = description, $3 = detail (optional)
    local status="$1"
    local description="$2"
    local detail="${3:-}"

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    case "$status" in
        PASS)
            TESTS_PASSED=$((TESTS_PASSED + 1))
            echo "PASS: $description"
            ;;
        FAIL)
            TESTS_FAILED=$((TESTS_FAILED + 1))
            echo "FAIL: $description"
            if [[ -n "$detail" ]]; then
                echo "  Detail: $detail"
            fi
            ;;
        SKIP)
            TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
            echo "SKIP: $description"
            if [[ -n "$detail" ]]; then
                echo "  Reason: $detail"
            fi
            ;;
    esac

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

should_run_scenario() {
    # Check if a scenario should run based on --scenario filter.
    # Returns 0 if scenario should run, 1 if it should be skipped.
    local name="$1"
    if [[ -z "$SCENARIO_FILTER" ]]; then
        return 0  # No filter, run all
    fi
    [[ "$name" == "$SCENARIO_FILTER" ]]
}

# --- Scenario Functions ---

scenario_instruction_audit_halt() {
    local name="instruction-audit-halt"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Instruction Audit Detects Base Conflict ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture_safe "main/release_instruction_audit/base-conflict") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_instruction_audit/base-conflict"
        return 0
    }

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.instruction_audit")
    output=$(run_claude_test "$prompt_file" \
        "Execute the instruction audit release step. Report any contradictions found." \
        "$fixture_dir")

    if assert_contains "$output" "contradict\|conflict\|inconsisten"; then
        record_result "PASS" "$name: contradiction detected"
    else
        record_result "FAIL" "$name: contradiction detected" \
            "Expected agent to identify contradiction in overrides"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_doc_coverage_gaps() {
    local name="doc-coverage-gaps"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Doc Consistency Finds Coverage Gaps ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture_safe "main/release_doc_consistency_check/coverage-gaps") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_doc_consistency_check/coverage-gaps"
        return 0
    }

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.doc_consistency_check")
    output=$(run_claude_test "$prompt_file" \
        "Execute the documentation consistency check release step." \
        "$fixture_dir")

    if assert_contains "$output" "gap\|missing\|not covered\|absent"; then
        record_result "PASS" "$name: coverage gaps identified"
    else
        record_result "FAIL" "$name: coverage gaps identified" \
            "Expected agent to identify missing feature coverage in README"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_doc_new_section_multi_turn() {
    local name="doc-new-section"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Doc Consistency New Section (Multi-Turn) ---"
    local fixture_dir prompt_file output1 output2

    fixture_dir=$(checkout_fixture_safe "main/release_doc_consistency_check/new-section-needed") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_doc_consistency_check/new-section-needed"
        return 0
    }

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.doc_consistency_check")
    reset_session

    # Turn 1: Agent presents gap table
    output1=$(run_claude_turn "$prompt_file" \
        "Execute the documentation consistency check release step." \
        "$fixture_dir")

    if assert_contains "$output1" "gap\|section\|missing\|table"; then
        record_result "PASS" "$name: turn 1 presents gaps"
    else
        record_result "FAIL" "$name: turn 1 presents gaps" \
            "Expected agent to present gap table in first turn"
    fi

    # Turn 2: User approves adding content
    output2=$(run_claude_turn "$prompt_file" \
        "Yes, add the new section for the monitoring features." \
        "$fixture_dir")

    if assert_contains "$output2" "add\|creat\|section\|heading"; then
        record_result "PASS" "$name: turn 2 responds to approval"
    else
        record_result "FAIL" "$name: turn 2 responds to approval" \
            "Expected agent to acknowledge section creation"
    fi

    reset_session
    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_version_notes_no_tags() {
    local name="version-notes-no-tags"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Version Notes With No Tags ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture_safe "main/release_record_version_notes/no-tags") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_record_version_notes/no-tags"
        return 0
    }

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.record_version_notes")
    output=$(run_claude_test "$prompt_file" \
        "Execute the Record Version & Release Notes step." \
        "$fixture_dir")

    if assert_contains "$output" "no.*tag\|everything.*new\|first.*release\|no.*previous"; then
        record_result "PASS" "$name: handles no-tags state"
    else
        record_result "FAIL" "$name: handles no-tags state" \
            "Expected agent to handle absence of version tags"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_version_notes_prior_tag() {
    local name="version-notes-prior-tag"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Version Notes With Prior Tag ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture_safe "main/release_record_version_notes/prior-tag") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_record_version_notes/prior-tag"
        return 0
    }

    # Set up git history with a version tag and subsequent commits
    (
        cd "$fixture_dir"
        git config user.email "test@aft.dev"
        git config user.name "AFT Test"
        git tag v1.0.0 HEAD 2>/dev/null || true
        echo "new feature file" > new_feature.txt
        git add new_feature.txt
        git commit -m "feat: add new monitoring dashboard" 2>/dev/null || true
        echo "bugfix file" > bugfix.txt
        git add bugfix.txt
        git commit -m "fix: resolve crash on empty config" 2>/dev/null || true
    )

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.record_version_notes")
    output=$(run_claude_test "$prompt_file" \
        "Execute the Record Version & Release Notes step." \
        "$fixture_dir")

    if assert_contains "$output" "v1.0.0\|since.*tag\|release.*note\|commit"; then
        record_result "PASS" "$name: references prior tag"
    else
        record_result "FAIL" "$name: references prior tag" \
            "Expected agent to reference v1.0.0 tag and commits since it"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_version_notes_no_heading() {
    local name="version-notes-no-heading"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Version Notes Without Releases Heading ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture_safe "main/release_record_version_notes/no-releases-heading") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_record_version_notes/no-releases-heading"
        return 0
    }

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.record_version_notes")
    output=$(run_claude_test "$prompt_file" \
        "Execute the Record Version & Release Notes step." \
        "$fixture_dir")

    if assert_contains "$output" "creat\|add.*Releases\|heading\|section"; then
        record_result "PASS" "$name: plans to create Releases heading"
    else
        record_result "FAIL" "$name: plans to create Releases heading" \
            "Expected agent to mention creating ## Releases heading"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

scenario_submodule_safety_warning() {
    local name="submodule-safety-warning"
    should_run_scenario "$name" || return 0

    echo ""
    echo "--- Scenario: Submodule Safety Warning Only ---"
    local fixture_dir prompt_file output

    fixture_dir=$(checkout_fixture_safe "main/release_submodule_safety_audit/warning-only") || {
        record_result "SKIP" "$name: fixture checkout" "Missing tag: main/release_submodule_safety_audit/warning-only"
        return 0
    }

    prompt_file=$(construct_release_prompt "$fixture_dir" "ARCHITECT" "purlin.instruction_audit")
    output=$(run_claude_test "$prompt_file" \
        "Audit the tools/ directory for submodule safety compliance." \
        "$fixture_dir")

    if assert_contains "$output" "warning\|json.load\|exception"; then
        record_result "PASS" "$name: warning detected"
    else
        record_result "FAIL" "$name: warning detected" \
            "Expected agent to flag json.load warning"
    fi

    if assert_not_contains "$output" "CRITICAL\|critical.*violation\|halt.*release"; then
        record_result "PASS" "$name: no critical violations"
    else
        record_result "FAIL" "$name: no critical violations" \
            "Should NOT report critical violations for warning-only state"
    fi

    rm -f "$prompt_file"
    cleanup_fixture "$fixture_dir"
}

# --- Summary and Results ---

print_summary() {
    echo ""
    echo "========================================="
    echo "${TESTS_PASSED}/${TESTS_TOTAL} passed, ${TESTS_SKIPPED} skipped"
    echo "========================================="
}

write_results() {
    if [[ "$WRITE_RESULTS" != true ]]; then
        return
    fi

    local out_dir="$PROJECT_ROOT/tests/aft_agent"
    mkdir -p "$out_dir"

    local status="PASS"
    if [[ "$TESTS_FAILED" -gt 0 ]]; then
        status="FAIL"
    fi

    local results
    results=$(jq -n \
        --arg status "$status" \
        --argjson passed "$TESTS_PASSED" \
        --argjson failed "$TESTS_FAILED" \
        --argjson skipped "$TESTS_SKIPPED" \
        --argjson total "$TESTS_TOTAL" \
        --argjson details "$TEST_DETAILS_JSON" \
        '{
            status: $status,
            passed: $passed,
            failed: $failed,
            skipped: $skipped,
            total: $total,
            test_file: "dev/test_agent_interactions.sh",
            details: $details
        }')

    echo "$results" > "$out_dir/tests.json"
    echo "Results written to $out_dir/tests.json"
}

# --- Main ---
main() {
    echo "AFT Agent Interaction Test Harness"
    echo "Model: $MODEL"
    echo "Fixture repo: $FIXTURE_REPO"
    if [[ -n "$SCENARIO_FILTER" ]]; then
        echo "Scenario filter: $SCENARIO_FILTER"
    fi
    echo ""

    # Run all scenarios (filtered by --scenario if provided)
    scenario_instruction_audit_halt
    scenario_doc_coverage_gaps
    scenario_doc_new_section_multi_turn
    scenario_version_notes_no_tags
    scenario_version_notes_prior_tag
    scenario_version_notes_no_heading
    scenario_submodule_safety_warning

    print_summary
    write_results

    if [[ "$TESTS_FAILED" -gt 0 ]]; then
        exit 1
    fi
}

main
