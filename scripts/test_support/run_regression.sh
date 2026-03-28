#!/usr/bin/env bash
# tools/test_support/run_regression.sh
#
# Meta-Runner: discovers and runs all scenario JSON files.
# Consumer-facing, submodule-safe.
# See features/regression_testing.md Section 2.9 for full specification.
#
# Usage:
#   tools/test_support/run_regression.sh [--scenarios-dir <path>]

set -o pipefail

# --- Project root detection (submodule-safe) ---
resolve_project_root() {
    if [[ -n "${PURLIN_PROJECT_ROOT:-}" ]]; then
        echo "$PURLIN_PROJECT_ROOT"
        return
    fi
    # Climbing fallback: try submodule path (further) before standalone (nearer)
    local dir
    dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local candidate=""
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/features" ]]; then
            candidate="$dir"
        fi
        dir="$(dirname "$dir")"
    done
    if [[ -n "$candidate" ]]; then
        echo "$candidate"
        return
    fi
    echo "Error: Could not detect project root" >&2
    return 1
}

PROJECT_ROOT="$(resolve_project_root)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_RUNNER="$SCRIPT_DIR/harness_runner.py"

# Defaults
SCENARIOS_DIR="${PROJECT_ROOT}/tests/qa/scenarios"

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --scenarios-dir)
            shift
            if [[ $# -eq 0 ]]; then
                echo "Error: --scenarios-dir requires a path" >&2
                exit 1
            fi
            SCENARIOS_DIR="$1"
            shift
            ;;
        -h|--help)
            echo "Usage: run_regression.sh [--scenarios-dir <path>]"
            echo ""
            echo "Discovers and runs all scenario JSON files in the scenarios directory."
            echo "Default scenarios directory: tests/qa/scenarios/"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Verify harness runner exists
if [[ ! -f "$HARNESS_RUNNER" ]]; then
    echo "Error: harness_runner.py not found at $HARNESS_RUNNER" >&2
    exit 1
fi

# Discover scenario files
if [[ ! -d "$SCENARIOS_DIR" ]]; then
    echo "No scenarios directory found at $SCENARIOS_DIR"
    echo "No scenarios to run."
    exit 0
fi

scenario_files=()
while IFS= read -r -d '' file; do
    scenario_files+=("$file")
done < <(find "$SCENARIOS_DIR" -name '*.json' -type f -print0 | sort -z)

if [[ ${#scenario_files[@]} -eq 0 ]]; then
    echo "No scenario files found in $SCENARIOS_DIR"
    exit 0
fi

echo "Regression Suite: ${#scenario_files[@]} scenario file(s) found"
echo ""

# Run each scenario file
total_features=0
passed_features=0
failed_features=0
results=()

for scenario_file in "${scenario_files[@]}"; do
    feature_name="$(basename "$scenario_file" .json)"
    ((total_features++)) || true

    echo "--- Running: $feature_name ---"

    if python3 "$HARNESS_RUNNER" "$scenario_file" --project-root "$PROJECT_ROOT" 2>&1; then
        ((passed_features++)) || true
        # Read the regression.json for summary
        tests_json="$PROJECT_ROOT/tests/$feature_name/regression.json"
        if [[ -f "$tests_json" ]]; then
            summary="$(python3 -c "
import json
try:
    d = json.load(open('$tests_json'))
    print(f\"{d.get('passed', '?')}/{d.get('total', '?')}\")
except Exception:
    print('?/?')
" 2>/dev/null)"
            results+=("PASS  $feature_name ($summary)")
        else
            results+=("PASS  $feature_name")
        fi
    else
        ((failed_features++)) || true
        tests_json="$PROJECT_ROOT/tests/$feature_name/regression.json"
        if [[ -f "$tests_json" ]]; then
            summary="$(python3 -c "
import json
try:
    d = json.load(open('$tests_json'))
    print(f\"{d.get('passed', '?')}/{d.get('total', '?')}\")
except Exception:
    print('?/?')
" 2>/dev/null)"
            results+=("FAIL  $feature_name ($summary)")
        else
            results+=("FAIL  $feature_name")
        fi
    fi

    echo ""
done

# Print summary
echo "Regression Summary:"
for r in "${results[@]}"; do
    echo "  $r"
done
echo ""

total_passed=0
total_tests=0
for scenario_file in "${scenario_files[@]}"; do
    feature_name="$(basename "$scenario_file" .json)"
    tests_json="$PROJECT_ROOT/tests/$feature_name/regression.json"
    if [[ -f "$tests_json" ]]; then
        p="$(python3 -c "import json; d=json.load(open('$tests_json')); print(d.get('passed',0))" 2>/dev/null || echo 0)"
        t="$(python3 -c "import json; d=json.load(open('$tests_json')); print(d.get('total',0))" 2>/dev/null || echo 0)"
        ((total_passed += p)) || true
        ((total_tests += t)) || true
    fi
done

echo "Total: $total_passed/$total_tests passed ($total_features features tested, $failed_features failure(s))"

if [[ "$failed_features" -gt 0 ]]; then
    exit 1
fi
exit 0
