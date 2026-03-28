#!/usr/bin/env bash
# dev/setup_fixture_repo.sh
#
# Creates the convention-path fixture repo at .purlin/runtime/fixture-repo
# with all tags declared across the project's feature specs.
#
# Each tag represents a controlled project state for one test scenario.
# Tags follow: main/<feature-name>/<scenario-slug>
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).
# Exempt from submodule safety checklist.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/.purlin/runtime/fixture-repo}"

echo "=== Purlin Fixture Repo Setup ==="
echo "Output: $OUTPUT_DIR"
echo ""

# Clean previous if exists
if [[ -d "$OUTPUT_DIR" ]]; then
    echo "Removing existing fixture repo..."
    rm -rf "$OUTPUT_DIR"
fi

# Create bare repo and working directory
mkdir -p "$(dirname "$OUTPUT_DIR")"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

git init --bare "$OUTPUT_DIR" >/dev/null 2>&1

cd "$WORK_DIR"
git init >/dev/null 2>&1
git remote add origin "$OUTPUT_DIR"
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Engineer"

TAG_COUNT=0

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

reset_workdir() {
    # Remove all tracked and untracked files, preserving .git
    git rm -rf --quiet . 2>/dev/null || true
    git clean -fdx --quiet 2>/dev/null || true
}

commit_and_tag() {
    local tag="$1"
    local message="${2:-State for $tag}"
    git add -A >/dev/null 2>&1
    git commit -m "$message" --allow-empty >/dev/null 2>&1
    git tag "$tag" >/dev/null 2>&1
    TAG_COUNT=$((TAG_COUNT + 1))
    echo "  [$TAG_COUNT] $tag"
}

# Creates a minimal valid project structure with standard files.
# After calling, the workdir has .purlin/, features/, tests/, instructions/.
create_base_project() {
    mkdir -p .purlin/runtime .purlin/cache .purlin/release
    mkdir -p features tests instructions/references

    # Minimal config
    cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "find_work": true, "auto_start": true },
        "builder": { "model": "claude-opus-4-6", "find_work": true, "auto_start": true },
        "qa": { "model": "claude-sonnet-4-6", "find_work": true, "auto_start": true }
    }
}
EOF

    # Override templates
    for f in HOW_WE_WORK_OVERRIDES.md BUILDER_OVERRIDES.md ARCHITECT_OVERRIDES.md QA_OVERRIDES.md; do
        echo "# $f" > ".purlin/$f"
    done

    # Minimal anchor (used as a prerequisite target by fixture features)
    cat > features/arch_testing.md <<'EOF'
# Architecture: Testing Standards

> Label: "Architecture: Testing Standards"
> Category: "Coordination & Lifecycle"

## 1. Purpose
Defines testing standards and conventions for the project.

## 2. Invariants

### 2.1 Test Colocation
Tests colocate with their implementation.
EOF
}

# Creates a well-formed feature file.
# Args: $1=filename $2=label $3=category $4=prerequisite(s) $5=status $6=body
create_feature() {
    local fname="$1" label="$2" category="$3" prereqs="$4" status="${5:-TODO}" body="${6:-}"
    {
        echo "# Feature: $label"
        echo ""
        echo "> Label: \"$label\""
        echo "> Category: \"$category\""
        if [[ -n "$prereqs" ]]; then
            while IFS=',' read -ra PREREQ_ARR; do
                for prereq in "${PREREQ_ARR[@]}"; do
                    echo "> Prerequisite: features/${prereq}"
                done
            done <<< "$prereqs"
        fi
        echo ""
        echo "[$status]"
        echo ""
        echo "## 1. Overview"
        echo ""
        echo "Fixture state for $label."
        echo ""
        echo "## 2. Requirements"
        echo ""
        echo "### 2.1 Basic"
        echo ""
        echo "- Implements $label functionality."
        echo ""
        if [[ -n "$body" ]]; then
            echo "$body"
            echo ""
        fi
        echo "## 3. Scenarios"
        echo ""
        echo "### Automated Scenarios"
        echo ""
        echo "#### Scenario: Basic operation"
        echo ""
        echo "    Given the system is configured"
        echo "    When the feature runs"
        echo "    Then it produces correct output"
        echo ""
        echo "### Manual Scenarios (Human Verification Required)"
        echo ""
        echo "None."
    } > "features/$fname"
}

# Creates a feature with manual scenarios
create_feature_with_manual() {
    local fname="$1" label="$2" category="$3" prereqs="$4" status="${5:-TODO}"
    shift 5
    local scenarios=("$@")
    {
        echo "# Feature: $label"
        echo ""
        echo "> Label: \"$label\""
        echo "> Category: \"$category\""
        if [[ -n "$prereqs" ]]; then
            while IFS=',' read -ra PREREQ_ARR; do
                for prereq in "${PREREQ_ARR[@]}"; do
                    echo "> Prerequisite: features/${prereq}"
                done
            done <<< "$prereqs"
        fi
        echo ""
        echo "[$status]"
        echo ""
        echo "## 1. Overview"
        echo ""
        echo "Fixture state for $label."
        echo ""
        echo "## 2. Requirements"
        echo ""
        echo "### 2.1 Basic"
        echo ""
        echo "- Implements $label functionality."
        echo ""
        echo "## 3. Scenarios"
        echo ""
        echo "### Automated Scenarios"
        echo ""
        echo "#### Scenario: Basic operation"
        echo ""
        echo "    Given the system is configured"
        echo "    When the feature runs"
        echo "    Then it produces correct output"
        echo ""
        echo "### Manual Scenarios (Human Verification Required)"
        echo ""
        for scenario in "${scenarios[@]}"; do
            echo "#### Scenario: $scenario"
            echo ""
            echo "    Given the system is ready"
            echo "    When the user verifies"
            echo "    Then the behavior is correct"
            echo ""
        done
    } > "features/$fname"
}

# Creates a web-testable feature
create_web_feature() {
    local fname="$1" label="$2" category="$3" prereqs="$4" status="${5:-TODO}"
    shift 5
    local scenarios=("$@")
    {
        echo "# Feature: $label"
        echo ""
        echo "> Label: \"$label\""
        echo "> Category: \"$category\""
        echo "> Web Test: http://localhost:9086"
        if [[ -n "$prereqs" ]]; then
            while IFS=',' read -ra PREREQ_ARR; do
                for prereq in "${PREREQ_ARR[@]}"; do
                    echo "> Prerequisite: features/${prereq}"
                done
            done <<< "$prereqs"
        fi
        echo ""
        echo "[$status]"
        echo ""
        echo "## 1. Overview"
        echo ""
        echo "Fixture state for $label."
        echo ""
        echo "## 2. Requirements"
        echo ""
        echo "### 2.1 Basic"
        echo ""
        echo "- Web dashboard feature."
        echo ""
        echo "## 3. Scenarios"
        echo ""
        echo "### Automated Scenarios"
        echo ""
        echo "#### Scenario: Basic rendering"
        echo ""
        echo "    Given the dev server is running"
        echo "    When the page loads"
        echo "    Then the content renders correctly"
        echo ""
        echo "### Manual Scenarios (Human Verification Required)"
        echo ""
        for scenario in "${scenarios[@]}"; do
            echo "#### Scenario: $scenario"
            echo ""
            echo "    Given the web app is open"
            echo "    When the user views the page"
            echo "    Then the display is correct"
            echo ""
        done
    } > "features/$fname"
}

# Creates a tests.json with PASS status
create_tests_json_pass() {
    local dir="$1"
    mkdir -p "tests/$dir"
    cat > "tests/$dir/tests.json" <<'EOF'
{"status": "PASS", "tests_run": 1, "tests_passed": 1, "tests_failed": 0}
EOF
}

# Creates a tests.json with FAIL status
create_tests_json_fail() {
    local dir="$1"
    mkdir -p "tests/$dir"
    cat > "tests/$dir/tests.json" <<'EOF'
{"status": "FAIL", "tests_run": 1, "tests_passed": 0, "tests_failed": 1}
EOF
}

# Creates feature_status.json
create_feature_status() {
    local file="$1"
    mkdir -p .purlin/cache
    echo "$file" > .purlin/cache/feature_status.json
}

# Creates a dependency graph
create_dep_graph() {
    local content="$1"
    mkdir -p .purlin/cache
    echo "$content" > .purlin/cache/dependency_graph.json
}

# Creates a companion file with builder decisions
create_companion() {
    local fname="$1" content="$2"
    echo "$content" > "features/$fname"
}

# =====================================================================
# FIXTURE GENERATION BY FEATURE NAMESPACE
# =====================================================================

echo ""
echo "--- collab_whats_different ---"

reset_workdir
create_base_project
create_feature "feature_changed.md" "Changed Feature" "Test" "arch_testing.md" "TESTING"
create_feature "feature_same.md" "Same Feature" "Test" "arch_testing.md" "COMPLETE"
echo "collab/testbranch" > .purlin/runtime/active_branch
create_tests_json_pass "feature_changed"
create_tests_json_pass "feature_same"

commit_and_tag "main/collab_whats_different/divergent-branches" \
    "Main and collab branches with different file changes for testing diff extraction"

# =====================================================================
echo ""
echo "--- config_layering ---"

reset_workdir
create_base_project

# local-override-present
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "builder": { "model": "claude-opus-4-6" }
    }
}
EOF
cat > .purlin/config.local.json <<'EOF'
{
    "agents": {
        "builder": { "model": "claude-sonnet-4-6" }
    }
}
EOF
create_feature "config_layering.md" "Config Layering" "Install" "arch_testing.md" "TESTING"
create_tests_json_pass "config_layering"

commit_and_tag "main/config_layering/local-override-present" \
    "Project with config.local.json overriding values from config.json"

# config-json-only
rm -f .purlin/config.local.json

commit_and_tag "main/config_layering/config-json-only" \
    "Project with config.json only, no local override file"

# =====================================================================
echo ""
echo "--- impl_notes_companion ---"

reset_workdir
create_base_project
create_feature "noted_feature.md" "Noted Feature" "Test" "arch_testing.md" "TESTING"
create_tests_json_pass "noted_feature"

cat > features/noted_feature.impl.md <<'IMPL'
# Implementation Notes: Noted Feature

*   **[DEVIATION]** Used polling instead of WebSocket. (Severity: HIGH)
*   **[DISCOVERY]** Config file can be empty, need fallback handling. (Severity: HIGH)
*   **[AUTONOMOUS]** Chose 5-second polling interval. (Severity: WARN)
IMPL

commit_and_tag "main/impl_notes_companion/companion-with-decisions" \
    "Project with features having DEVIATION, DISCOVERY, and AUTONOMOUS tags in companion files"

# =====================================================================
echo ""
echo "--- pl_context_guard ---"

reset_workdir
create_base_project

cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "context_guard": true },
        "builder": { "model": "claude-opus-4-6", "context_guard": true },
        "qa": { "model": "claude-sonnet-4-6", "context_guard": false }
    }
}
EOF

create_feature "pl_context_guard.md" "Context Guard" "Agent Skills" "arch_testing.md" "TESTING"
create_tests_json_pass "pl_context_guard"

commit_and_tag "main/pl_context_guard/mixed-thresholds" \
    "Project with different context guard thresholds and enabled states per role"

# mixed-states: different context_guard enabled booleans per role (no thresholds)
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "context_guard": true },
        "builder": { "model": "claude-opus-4-6", "context_guard": true },
        "qa": { "model": "claude-sonnet-4-6", "context_guard": false }
    }
}
EOF

commit_and_tag "main/pl_context_guard/mixed-states" \
    "Project with different context guard enabled states per role"

# =====================================================================
echo ""
echo "--- pl_help ---"

reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done
if [[ -d "$PROJECT_ROOT/references" ]]; then
    mkdir -p "references/"
    cp -r "$PROJECT_ROOT/references/"* "references/" 2>/dev/null || true
fi

# architect-main-branch
commit_and_tag "main/pl_help/architect-main-branch" \
    "Project on main branch, default config"

# builder-collab-branch
echo "collab/v2" > .purlin/runtime/active_branch
commit_and_tag "main/pl_help/builder-collab-branch" \
    "Project with .purlin/runtime/active_branch containing collab/v2 for builder"

# qa-collab-branch
echo "collab/v2" > .purlin/runtime/active_branch
commit_and_tag "main/pl_help/qa-collab-branch" \
    "Project with .purlin/runtime/active_branch containing collab/v2"

# =====================================================================
echo ""
echo "--- pl_session_resume ---"

reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done
if [[ -d "$PROJECT_ROOT/references" ]]; then
    mkdir -p "references/"
    cp -r "$PROJECT_ROOT/references/"* "references/" 2>/dev/null || true
fi

# builder-mid-feature
cat > .purlin/cache/session_checkpoint.md <<'CHECKPOINT'
# Session Checkpoint

**Role:** Engineer
**Timestamp:** 2026-01-15T10:30:00Z
**Branch:** collab/purlincollab

## Current Work

**Feature:** features/sample_feature.md
**In Progress:** Implementing sample_feature requirements

### Done
- Read feature spec
- Created initial implementation

### Next
1. Write unit tests
2. Verify locally
3. Commit status tag

## Uncommitted Changes
None

## Notes
All prerequisites are satisfied.

## Engineer Context
**Protocol Step:** 2
**Delivery Plan:** No delivery plan
**Work Queue:**
1. [HIGH] sample_feature.md
**Pending Decisions:** None
CHECKPOINT

create_feature "sample_feature.md" "Sample Feature" "Test" "arch_testing.md" "TODO"

commit_and_tag "main/pl_session_resume/builder-mid-feature" \
    "Checkpoint file showing builder at protocol step 2 for a feature"

# qa-mid-verification
cat > .purlin/cache/session_checkpoint.md <<'CHECKPOINT'
# Session Checkpoint

**Role:** QA
**Timestamp:** 2026-01-15T14:00:00Z
**Branch:** collab/purlincollab

## Current Work

**Feature:** features/sample_feature.md
**In Progress:** Verifying manual scenarios

### Done
- Scenarios 1-5 passed

### Next
1. Continue with scenario 6
2. Complete remaining scenarios 7-8
3. Record any discoveries

## Uncommitted Changes
None

## Notes
No discoveries found so far.

## QA Context
**Scenario Progress:** 5 of 8 scenarios completed
**Current Scenario:** Scenario 6 - Edge case handling
**Discoveries:** None
**Verification Queue:** 1 feature remaining (sample_feature)
CHECKPOINT

commit_and_tag "main/pl_session_resume/qa-mid-verification" \
    "Checkpoint file showing QA at scenario 6 of 8 for a feature"

# full-reboot-no-launcher (checkpoint exists but simulates non-launcher start)
commit_and_tag "main/pl_session_resume/full-reboot-no-launcher" \
    "Project state with checkpoint but no system prompt (simulating non-launcher start)"

# =====================================================================
echo ""
echo "--- pl_spec_code_audit ---"

reset_workdir
create_base_project

# Feature with known spec-code divergence
create_feature "divergent_feature.md" "Divergent Feature" "Test" "arch_testing.md" "TESTING" \
    "### 2.2 Advanced
- Must support batch processing of up to 1000 items.
- Must validate input against JSON schema before processing."
create_tests_json_pass "divergent_feature"

# Create implementation that doesn't match spec
mkdir -p tools/divergent
cat > tools/divergent/process.py <<'PYEOF'
# Missing batch processing (spec says up to 1000 items)
# Missing JSON schema validation
def process_item(item):
    return {"result": item}
PYEOF

commit_and_tag "main/pl_spec_code_audit/spec-code-gaps" \
    "Project with feature specs that have known divergence from implementation code"

# =====================================================================
echo ""
echo "--- pl_web_test ---"

reset_workdir
create_base_project

create_web_feature "web_feat_a.md" "Web Feature A" "Web Features" "arch_testing.md" "TESTING" "Dashboard Layout" "Theme Toggle"
create_web_feature "web_feat_b.md" "Web Feature B" "Web Features" "arch_testing.md" "TESTING" "Data Table"
create_feature "non_web_feat.md" "Non-Web Feature" "Process" "arch_testing.md" "TESTING"

create_tests_json_pass "web_feat_a"
create_tests_json_pass "web_feat_b"
create_tests_json_pass "non_web_feat"

commit_and_tag "main/pl_web_test/web-testable-features" \
    "Project with multiple web-test-eligible features for verifying discovery and execution flow"

# =====================================================================
echo ""
echo "--- project_init ---"

# fresh-directory: empty project with no .purlin
reset_workdir
mkdir -p empty_project
touch empty_project/.gitkeep

commit_and_tag "main/project_init/fresh-directory" \
    "Empty project directory with no .purlin or purlin submodule"

# partially-initialized: has .purlin but incomplete
reset_workdir
mkdir -p .purlin
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools"
}
EOF
# Missing override files -> incomplete initialization

commit_and_tag "main/project_init/partially-initialized" \
    "Project directory with .purlin directory but incomplete initialization"

# =====================================================================
echo ""
echo "--- qa_verification_effort ---"

reset_workdir
create_base_project

# auto-only feature
create_feature "auto_only_feat.md" "Auto Only" "Test" "arch_testing.md" "TESTING"
mkdir -p tests/auto_only_feat
cat > tests/auto_only_feat/tests.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "CLEAN"},
    "verification_effort": {
        "web_test": 0, "test_only": 1, "skip": 0,
        "manual_interactive": 0, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 1, "total_manual": 0, "summary": "builder-verified"
    },
    "change_scope": "full"
}
EOF
create_tests_json_pass "auto_only_feat"

# manual feature
create_feature_with_manual "manual_feat.md" "Manual Feature" "Process" "arch_testing.md" "TESTING" "Hardware Check" "Visual Inspect"
mkdir -p tests/manual_feat
cat > tests/manual_feat/tests.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"},
    "verification_effort": {
        "web_test": 0, "test_only": 0, "skip": 0,
        "manual_interactive": 2, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 0, "total_manual": 2, "summary": "2 manual"
    },
    "change_scope": "full"
}
EOF
create_tests_json_pass "manual_feat"

# mixed feature (web-testable with manual)
create_web_feature "mixed_feat.md" "Mixed Feature" "Web Features" "arch_testing.md" "TESTING" "Web Dashboard"
mkdir -p tests/mixed_feat
cat > tests/mixed_feat/tests.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"},
    "verification_effort": {
        "web_test": 1, "test_only": 0, "skip": 0,
        "manual_interactive": 0, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 1, "total_manual": 0, "summary": "no QA items"
    },
    "change_scope": "full"
}
EOF
create_tests_json_pass "mixed_feat"

commit_and_tag "main/qa_verification_effort/varied-effort-types" \
    "Project with features having auto-only, manual, and mixed QA classifications"

# =====================================================================
echo ""
echo "--- release_audit_automation ---"
echo "  (tags use release step namespaces)"

# release_verify_deps/clean-graph
reset_workdir
create_base_project
create_feature "feat_a.md" "Feature A" "Test" "arch_testing.md" "COMPLETE"
create_feature "feat_b.md" "Feature B" "Test" "feat_a.md" "COMPLETE"
create_tests_json_pass "feat_a"
create_tests_json_pass "feat_b"
create_dep_graph '{
    "cycles": [],
    "features": [
        {"file": "features/feat_a.md", "label": "Feature A", "prerequisites": ["arch_testing.md"]},
        {"file": "features/feat_b.md", "label": "Feature B", "prerequisites": ["feat_a.md"]}
    ],
    "orphans": []
}'

commit_and_tag "main/release_verify_deps/clean-graph" \
    "Valid dependency graph, no issues"

# release_verify_deps/cycle-in-prerequisites
reset_workdir
create_base_project
create_feature "cycle_a.md" "Cycle A" "Test" "cycle_b.md"
create_feature "cycle_b.md" "Cycle B" "Test" "cycle_a.md"
create_dep_graph '{
    "cycles": [["cycle_a.md", "cycle_b.md"]],
    "features": [
        {"file": "features/cycle_a.md", "label": "Cycle A", "prerequisites": ["cycle_b.md"]},
        {"file": "features/cycle_b.md", "label": "Cycle B", "prerequisites": ["cycle_a.md"]}
    ],
    "orphans": []
}'

commit_and_tag "main/release_verify_deps/cycle-in-prerequisites" \
    "Features with circular prerequisite links"

# release_verify_deps/broken-link
reset_workdir
create_base_project
create_feature "broken_ref.md" "Broken Ref" "Test" "nonexistent_feature.md"
create_dep_graph '{
    "cycles": [],
    "features": [
        {"file": "features/broken_ref.md", "label": "Broken Ref", "prerequisites": ["nonexistent_feature.md"]}
    ],
    "orphans": []
}'

commit_and_tag "main/release_verify_deps/broken-link" \
    "Feature with prerequisite pointing to nonexistent file"

# release_verify_deps/reverse-reference
reset_workdir
create_base_project
create_feature "parent_feat.md" "Parent Feature" "Test" "arch_testing.md" "COMPLETE" \
    "See also features/child_feat.md for implementation details."
create_feature "child_feat.md" "Child Feature" "Test" "parent_feat.md" "TESTING"
create_tests_json_pass "parent_feat"
create_tests_json_pass "child_feat"

commit_and_tag "main/release_verify_deps/reverse-reference" \
    "Parent feature body-referencing child"

# release_zero_queue/all-clean
reset_workdir
create_base_project
create_feature "clean_a.md" "Clean A" "Test" "arch_testing.md" "COMPLETE"
create_feature "clean_b.md" "Clean B" "Test" "arch_testing.md" "COMPLETE"
create_tests_json_pass "clean_a"
create_tests_json_pass "clean_b"

commit_and_tag "main/release_zero_queue/all-clean" \
    "All features DONE/CLEAN"

# release_zero_queue/builder-todo
reset_workdir
create_base_project
create_feature "todo_feat.md" "TODO Feature" "Test" "arch_testing.md" "TODO"

commit_and_tag "main/release_zero_queue/builder-todo" \
    "Feature with builder: TODO"

# release_zero_queue/qa-open-items
reset_workdir
create_base_project
cat > features/qa_open_feat.md <<'FEAT'
# Feature: QA Open Feature

> Label: "QA Open Feature"
> Category: "Test"
> Prerequisite: features/arch_testing.md

[TESTING]

## 1. Overview
Feature with open QA items.

## 2. Requirements
### 2.1 Basic
- Something.

## 3. Scenarios
### Automated Scenarios
#### Scenario: Basic
    Given setup
    When action
    Then result

### Manual Scenarios (Human Verification Required)
None.

## User Testing Discoveries

### [BUG] Crash on empty input
- **Status:** OPEN
- **Found by:** QA
- **Date:** 2026-01-20
- **Description:** Application crashes when input is empty.
FEAT
create_tests_json_pass "qa_open_feat"

commit_and_tag "main/release_zero_queue/qa-open-items" \
    "Feature with qa: HAS_OPEN_ITEMS"

# release_submodule_safety/clean
reset_workdir
create_base_project
mkdir -p tools/sample_tool
cat > tools/sample_tool/tool.py <<'PYEOF'
import os, json

def get_project_root():
    root = os.environ.get("PURLIN_PROJECT_ROOT")
    if root:
        return root
    # Climbing fallback
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "features")):
            return d
        d = os.path.dirname(d)
    return None

def load_config():
    root = get_project_root()
    try:
        with open(os.path.join(root, ".purlin", "config.json")) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {"tools_root": "tools"}
PYEOF

commit_and_tag "main/release_submodule_safety/clean" \
    "All tools submodule-safe"

# release_submodule_safety/missing-env-check
reset_workdir
create_base_project
mkdir -p tools/bad_tool
cat > tools/bad_tool/tool.py <<'PYEOF'
import os, json
# Missing PURLIN_PROJECT_ROOT check
def get_root():
    return os.path.dirname(os.path.abspath(__file__))
PYEOF

commit_and_tag "main/release_submodule_safety/missing-env-check" \
    "Python tool without PURLIN_PROJECT_ROOT check"

# release_submodule_safety/artifact-in-tools
reset_workdir
create_base_project
mkdir -p tools/leaky_tool
cat > tools/leaky_tool/run.sh <<'SHEOF'
#!/usr/bin/env bash
echo $$ > tools/leaky_tool/server.pid
SHEOF

commit_and_tag "main/release_submodule_safety/artifact-in-tools" \
    "Script writing .pid inside tools/"

# release_submodule_safety/unguarded-json-load
reset_workdir
create_base_project
mkdir -p tools/unsafe_tool
cat > tools/unsafe_tool/config.py <<'PYEOF'
import json
def load():
    with open(".purlin/config.json") as f:
        return json.load(f)
PYEOF

commit_and_tag "main/release_submodule_safety/unguarded-json-load" \
    "Bare json.load without try/except"

# release_doc_consistency/clean-docs
reset_workdir
create_base_project
create_feature "feat_alpha.md" "Feature Alpha" "Test" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_alpha"
cat > README.md <<'EOF'
# Test Project

## Features
- Feature Alpha
EOF

commit_and_tag "main/release_doc_consistency/clean-docs" \
    "README matches current features"

# release_doc_consistency/stale-reference
reset_workdir
create_base_project
create_feature "feat_current.md" "Current Feature" "Test" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_current"
cat > README.md <<'EOF'
# Test Project

## Features
- Current Feature
- Old Deleted Feature (see features/old_deleted.md)
EOF

commit_and_tag "main/release_doc_consistency/stale-reference" \
    "README references deleted file"

# release_instruction_audit/clean
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

commit_and_tag "main/release_instruction_audit/clean" \
    "All overrides consistent with base"

# release_instruction_audit/contradiction
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

cat > .purlin/BUILDER_OVERRIDES.md <<'EOF'
# Engineer Overrides

## Contradiction
The Engineer MUST NOT commit code. This contradicts the base rule requiring immediate commits.
EOF

commit_and_tag "main/release_instruction_audit/contradiction" \
    "Override negating base rule"

# release_instruction_audit/stale-path
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

cat > .purlin/BUILDER_OVERRIDES.md <<'EOF'
# Engineer Overrides

## Stale Reference
See `tools/deleted_tool/run.sh` for the build script.
EOF

commit_and_tag "main/release_instruction_audit/stale-path" \
    "Override referencing deleted file"

# release_instruction_audit/base-conflict
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

# Include global_steps.json for release step testing
if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

# Override directly contradicts a base instruction
cat > .purlin/BUILDER_OVERRIDES.md <<'EOF'
# Engineer Overrides

## Status Commits
The Engineer MUST NOT make status tag commits. Status changes are tracked implicitly.
This contradicts the base rule requiring separate status tag commits.
EOF

commit_and_tag "main/release_instruction_audit/base-conflict" \
    "Override rule directly contradicts base instruction"

# release_instruction_audit/base-error
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

# Include global_steps.json for release step testing
if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

# Base layer has a genuine error: references a non-existent tool path
# and uses a deprecated lifecycle label. The override is correct and
# cannot fix the base error without modifying the base itself.
cat > instructions/BUILDER_BASE.md <<'EOF'
# Engineer Base Instructions

## 1. Executive Summary
Your mandate is to translate specifications into high-quality code.

## 2. Build Protocol
Run `tools/legacy_build_engine/compile.sh` to build the project.
This path is hardcoded in the base layer.

## 3. Feature Status Lifecycle
Features move through DRAFT -> REVIEW -> SHIPPED.
The SHIPPED status is used by the base framework.

## 4. Verification
After building, run `tools/legacy_build_engine/verify.sh` for verification.
EOF

# Override is clean — no contradictions, just normal overrides
cat > .purlin/BUILDER_OVERRIDES.md <<'EOF'
# Engineer Overrides

## Build Environment
Use Node.js 20+ for all build operations.
EOF

commit_and_tag "main/release_instruction_audit/base-error" \
    "Base layer references non-existent tools/legacy_build_engine/ — cannot fix via override"

# =====================================================================
echo ""
echo "--- release_checklist_core ---"

reset_workdir
create_base_project

mkdir -p .purlin/release
cat > .purlin/release/config.json <<'EOF'
{
    "steps": [
        {"id": "purlin.verify_deps", "enabled": true},
        {"id": "purlin.verify_zero_queue", "enabled": true},
        {"id": "purlin.doc_consistency", "enabled": false},
        {"id": "purlin.submodule_safety", "enabled": true},
        {"id": "purlin.instruction_audit", "enabled": false},
        {"id": "purlin.push_to_remote", "enabled": true}
    ]
}
EOF

commit_and_tag "main/release_checklist_core/mixed-enabled-disabled" \
    "Project with release steps in various enabled/disabled states"

# =====================================================================
echo ""
echo "--- release_checklist_ui ---"

reset_workdir
create_base_project

mkdir -p .purlin/release
cat > .purlin/release/config.json <<'EOF'
{
    "steps": [
        {"id": "purlin.verify_deps", "enabled": true},
        {"id": "purlin.verify_zero_queue", "enabled": true},
        {"id": "purlin.doc_consistency", "enabled": true},
        {"id": "purlin.submodule_safety", "enabled": true},
        {"id": "purlin.instruction_audit", "enabled": true},
        {"id": "purlin.framework_doc", "enabled": true},
        {"id": "purlin.push_to_remote", "enabled": false},
        {"id": "purlin.record_version", "enabled": false}
    ]
}
EOF

commit_and_tag "main/release_checklist_ui/mixed-enabled" \
    "7 enabled and 2 disabled steps for verifying drag handles, step numbering, dimming"

# =====================================================================
echo ""
echo "--- release_doc_consistency_check ---"

reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

# Create contradictory lifecycle definitions
cat > instructions/LIFECYCLE_REF.md <<'EOF'
# Feature Lifecycle Reference

States: TODO -> TESTING -> COMPLETE
Status is driven by git commit tags.
EOF

cat > .purlin/BUILDER_OVERRIDES.md <<'EOF'
# Engineer Overrides

## Lifecycle
States: DRAFT -> REVIEW -> DONE -> DEPLOYED
Features transition through four states.
EOF

commit_and_tag "main/release_doc_consistency_check/inconsistent-docs" \
    "Project with instruction files containing contradictory lifecycle definitions"

# release_doc_consistency_check/coverage-gaps
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_dashboard.md" "Dashboard" "UI" "arch_testing.md" "COMPLETE"
create_feature "feat_api.md" "API Gateway" "Backend" "arch_testing.md" "COMPLETE"
create_feature "feat_monitoring.md" "Monitoring" "Observability" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_dashboard"
create_tests_json_pass "feat_api"
create_tests_json_pass "feat_monitoring"

# README only covers Dashboard -- missing API Gateway and Monitoring
cat > README.md <<'EOF'
# Test Project

## Features
- Dashboard: Interactive dashboard for viewing project status.

## Getting Started
Run `npm start` to launch the application.
EOF

commit_and_tag "main/release_doc_consistency_check/coverage-gaps" \
    "README only covers 1 of 3 features"

# release_doc_consistency_check/new-section-needed
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_auth.md" "Authentication" "Security" "arch_testing.md" "COMPLETE"
create_feature "feat_monitoring.md" "System Monitoring" "Observability" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_auth"
create_tests_json_pass "feat_monitoring"

# README has Features section but no Observability section
cat > README.md <<'EOF'
# Test Project

## Features
- Authentication: User authentication and authorization.

## Security
Authentication uses JWT tokens with configurable expiry.
EOF

commit_and_tag "main/release_doc_consistency_check/new-section-needed" \
    "Gap requires new ## heading for monitoring/observability"

# release_doc_consistency_check/clean
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_dashboard.md" "Dashboard" "UI" "arch_testing.md" "COMPLETE"
create_feature "feat_api.md" "API Gateway" "Backend" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_dashboard"
create_tests_json_pass "feat_api"

# README covers all features
cat > README.md <<'EOF'
# Test Project

## Features
- Dashboard: Interactive dashboard for viewing project status.
- API Gateway: Backend API routing and gateway services.

## Getting Started
Run `npm start` to launch the application.
EOF

commit_and_tag "main/release_doc_consistency_check/clean" \
    "README fully covers all features"

# =====================================================================
echo ""
echo "--- release_record_version_notes ---"

# release_record_version_notes/no-tags
reset_workdir
create_base_project

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_init.md" "Project Init" "Core" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_init"

cat > README.md <<'EOF'
# Test Project

## Features
- Project initialization and setup.

## Releases
No releases yet.
EOF

commit_and_tag "main/release_record_version_notes/no-tags" \
    "Repo with commits but no release version tags"

# release_record_version_notes/prior-tag
reset_workdir
create_base_project

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_core.md" "Core System" "Core" "arch_testing.md" "COMPLETE"
create_feature "feat_new.md" "New Feature" "Core" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_core"
create_tests_json_pass "feat_new"

cat > README.md <<'EOF'
# Test Project

## Features
- Core System: Foundation project setup.
- New Feature: Recently added functionality.

## Releases
### v1.0.0 — 2026-01-15
- Initial release with Core System.
EOF

commit_and_tag "main/release_record_version_notes/prior-tag" \
    "Repo with v1.0.0 tag and later commits"

# release_record_version_notes/no-releases-heading
reset_workdir
create_base_project

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_basic.md" "Basic Feature" "Core" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_basic"

# README without ## Releases section
cat > README.md <<'EOF'
# Test Project

## Features
- Basic Feature: Core functionality.

## Getting Started
Run `./start.sh` to begin.
EOF

commit_and_tag "main/release_record_version_notes/no-releases-heading" \
    "README lacks ## Releases section"

# release_record_version_notes/clean
reset_workdir
create_base_project

if [[ -f "$PROJECT_ROOT/tools/release/global_steps.json" ]]; then
    mkdir -p tools/release
    cp "$PROJECT_ROOT/tools/release/global_steps.json" tools/release/global_steps.json
fi

create_feature "feat_core.md" "Core System" "Core" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_core"

cat > README.md <<'EOF'
# Test Project

## Features
- Core System: Foundation project setup.

## Releases
### v1.0.0 — 2026-01-15
- Initial release with Core System.
EOF

commit_and_tag "main/release_record_version_notes/clean" \
    "Clean repo with valid tags and Releases heading"

# =====================================================================
echo ""
echo "--- release_submodule_safety_audit ---"

# clean-submodule
reset_workdir
create_base_project

mkdir -p tools/safe_tool
cat > tools/safe_tool/tool.py <<'PYEOF'
import os, json

def get_project_root():
    root = os.environ.get("PURLIN_PROJECT_ROOT")
    if root:
        return root
    d = os.path.dirname(os.path.abspath(__file__))
    candidate = None
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "features")):
            candidate = d
        d = os.path.dirname(d)
    return candidate

def load_config():
    root = get_project_root()
    config_path = os.path.join(root, ".purlin", "config.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {"tools_root": "tools"}

def write_output(data):
    root = get_project_root()
    out = os.path.join(root, ".purlin", "runtime", "output.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f)
PYEOF

commit_and_tag "main/release_submodule_safety_audit/clean-submodule" \
    "Project where all tool paths resolve correctly for submodule consumption"

# violations-present
reset_workdir
create_base_project

mkdir -p tools/violating_tool
cat > tools/violating_tool/bad.py <<'PYEOF'
import os, json

# Violation 1: hardcoded path assumption
ROOT = os.path.dirname(os.path.abspath(__file__))

# Violation 2: bare json.load
def load():
    with open("features/config.json") as f:
        return json.load(f)

# Violation 3: artifact in tools/
def run():
    with open("tools/violating_tool/output.log", "w") as f:
        f.write("result")
PYEOF

commit_and_tag "main/release_submodule_safety_audit/violations-present" \
    "Project with hardcoded paths, artifacts in tools/, and bare json.load() calls"

# release_submodule_safety_audit/warning-only
reset_workdir
create_base_project

mkdir -p tools/warn_tool
cat > tools/warn_tool/tool.py <<'PYEOF'
import os, json

def get_project_root():
    root = os.environ.get("PURLIN_PROJECT_ROOT")
    if root:
        return root
    d = os.path.dirname(os.path.abspath(__file__))
    candidate = None
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "features")):
            candidate = d
        d = os.path.dirname(d)
    return candidate

def load_config():
    root = get_project_root()
    config_path = os.path.join(root, ".purlin", "config.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        # WARNING: Missing IOError/OSError in exception handler
        return {"tools_root": "tools"}

def write_output(data):
    root = get_project_root()
    out = os.path.join(root, ".purlin", "runtime", "output.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f)
PYEOF

commit_and_tag "main/release_submodule_safety_audit/warning-only" \
    "Tool with json.load WARNING but no CRITICAL violations"

# release_submodule_safety_audit/clean (alias for clean-submodule with spec-canonical tag name)
reset_workdir
create_base_project

mkdir -p tools/safe_tool
cat > tools/safe_tool/tool.py <<'PYEOF'
import os, json

def get_project_root():
    root = os.environ.get("PURLIN_PROJECT_ROOT")
    if root:
        return root
    d = os.path.dirname(os.path.abspath(__file__))
    candidate = None
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "features")):
            candidate = d
        d = os.path.dirname(d)
    return candidate

def load_config():
    root = get_project_root()
    config_path = os.path.join(root, ".purlin", "config.json")
    try:
        with open(config_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return {"tools_root": "tools"}

def write_output(data):
    root = get_project_root()
    out = os.path.join(root, ".purlin", "runtime", "output.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(data, f)
PYEOF

commit_and_tag "main/release_submodule_safety_audit/clean" \
    "No submodule safety violations"

# =====================================================================
echo ""
echo "--- release_verify_dependency_integrity ---"

# acyclic-graph
reset_workdir
create_base_project
create_feature "layer1.md" "Layer 1" "Test" "arch_testing.md" "COMPLETE"
create_feature "layer2.md" "Layer 2" "Test" "layer1.md" "COMPLETE"
create_feature "layer3.md" "Layer 3" "Test" "layer2.md" "COMPLETE"
create_tests_json_pass "layer1"
create_tests_json_pass "layer2"
create_tests_json_pass "layer3"
create_dep_graph '{
    "cycles": [],
    "features": [
        {"file": "features/layer1.md", "label": "Layer 1", "prerequisites": ["arch_testing.md"]},
        {"file": "features/layer2.md", "label": "Layer 2", "prerequisites": ["layer1.md"]},
        {"file": "features/layer3.md", "label": "Layer 3", "prerequisites": ["layer2.md"]}
    ],
    "orphans": []
}'

commit_and_tag "main/release_verify_dependency_integrity/acyclic-graph" \
    "Project with a valid acyclic dependency graph"

# circular-dependency
reset_workdir
create_base_project
create_feature "loop_a.md" "Loop A" "Test" "loop_c.md"
create_feature "loop_b.md" "Loop B" "Test" "loop_a.md"
create_feature "loop_c.md" "Loop C" "Test" "loop_b.md"
create_dep_graph '{
    "cycles": [["loop_a.md", "loop_b.md", "loop_c.md"]],
    "features": [
        {"file": "features/loop_a.md", "label": "Loop A", "prerequisites": ["loop_c.md"]},
        {"file": "features/loop_b.md", "label": "Loop B", "prerequisites": ["loop_a.md"]},
        {"file": "features/loop_c.md", "label": "Loop C", "prerequisites": ["loop_b.md"]}
    ],
    "orphans": []
}'

commit_and_tag "main/release_verify_dependency_integrity/circular-dependency" \
    "Project with a circular dependency cycle in prerequisite links"

# =====================================================================
echo ""
echo "--- release_verify_zero_queue ---"

# all-clean
reset_workdir
create_base_project
create_feature "done_a.md" "Done A" "Test" "arch_testing.md" "COMPLETE"
create_feature "done_b.md" "Done B" "Test" "arch_testing.md" "COMPLETE"
create_tests_json_pass "done_a"
create_tests_json_pass "done_b"

commit_and_tag "main/release_verify_zero_queue/all-clean" \
    "Project where all features have DONE/CLEAN status across all roles"

# features-with-open-items
reset_workdir
create_base_project
create_feature "open_feat.md" "Open Feature" "Test" "arch_testing.md" "TODO"
create_feature "done_feat.md" "Done Feature" "Test" "arch_testing.md" "COMPLETE"
create_tests_json_pass "done_feat"

commit_and_tag "main/release_verify_zero_queue/features-with-open-items" \
    "Project with features having TODO/BUG items blocking release"

# =====================================================================
echo ""
echo "--- spec_code_audit_role_clarity ---"

reset_workdir
create_base_project

create_feature "audit_target.md" "Audit Target" "Test" "arch_testing.md" "TESTING" \
    "### 2.2 Role Gating
- Only PM may invoke /pl-spec.
- Only Engineer may invoke /pl-build.
- Only QA may invoke /pl-verify."
create_tests_json_pass "audit_target"

# Implementation that doesn't match spec
mkdir -p tools/commands
cat > tools/commands/spec.sh <<'SHEOF'
#!/usr/bin/env bash
# Missing role gate check
echo "Running spec command..."
SHEOF

commit_and_tag "main/spec_code_audit_role_clarity/features-needing-audit" \
    "Project with features whose implementation code does not match spec"

# =====================================================================
echo ""
echo "--- test_fixture_repo ---"

# repo-with-tags: a fixture repo that itself contains tags (meta-fixture)
reset_workdir
create_base_project

# Create a nested bare repo inside this fixture
NESTED_BARE="$(mktemp -d)"
git init --bare "$NESTED_BARE" >/dev/null 2>&1

NESTED_WORK="$(mktemp -d)"
cd "$NESTED_WORK"
git init >/dev/null 2>&1
git remote add origin "$NESTED_BARE"
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Engineer"

echo "content for tag 1" > file1.txt
git add -A >/dev/null 2>&1
git commit -m "State for tag 1" >/dev/null 2>&1
git tag "main/test_feature/scenario-one" >/dev/null 2>&1

echo "content for tag 2" > file2.txt
git add -A >/dev/null 2>&1
git commit -m "State for tag 2" >/dev/null 2>&1
git tag "main/test_feature/scenario-two" >/dev/null 2>&1

echo "content for tag 3" > file3.txt
git add -A >/dev/null 2>&1
git commit -m "State for tag 3" >/dev/null 2>&1
git tag "main/test_feature/scenario-three" >/dev/null 2>&1

git push origin --all >/dev/null 2>&1
git push origin --tags >/dev/null 2>&1

# Go back to main working directory
cd "$WORK_DIR"

# Store the nested bare repo path in a known location
mkdir -p .purlin/runtime
# Copy the nested bare repo into the fixture as a directory
cp -r "$NESTED_BARE" .purlin/runtime/nested-fixture-repo
rm -rf "$NESTED_BARE" "$NESTED_WORK"

create_feature "test_fixture_repo.md" "Test Fixture Repo" "Test Infrastructure" "arch_testing.md" "TESTING"

commit_and_tag "main/test_fixture_repo/repo-with-tags" \
    "Bare git fixture repo with 3 example tags at known commits"

# empty-repo
EMPTY_BARE="$(mktemp -d)"
git init --bare "$EMPTY_BARE" >/dev/null 2>&1
cp -r "$EMPTY_BARE" .purlin/runtime/nested-fixture-repo-empty
rm -rf "$EMPTY_BARE"

commit_and_tag "main/test_fixture_repo/empty-repo" \
    "Bare git fixture repo initialized but containing no tags"

# repo-with-duplicate-tag: a fixture repo with a pre-existing tag for overwrite testing
reset_workdir
create_base_project

DUP_BARE="$(mktemp -d)"
git init --bare "$DUP_BARE" >/dev/null 2>&1

DUP_WORK="$(mktemp -d)"
cd "$DUP_WORK"
git init >/dev/null 2>&1
git remote add origin "$DUP_BARE"
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Engineer"

echo "original content" > file.txt
git add -A >/dev/null 2>&1
git commit -m "State for existing tag" >/dev/null 2>&1
git tag "main/test_feature/existing-state" >/dev/null 2>&1

git push origin --all >/dev/null 2>&1
git push origin --tags >/dev/null 2>&1

cd "$WORK_DIR"
cp -r "$DUP_BARE" .purlin/runtime/nested-fixture-repo-duplicate
rm -rf "$DUP_BARE" "$DUP_WORK"

create_feature "test_fixture_repo.md" "Test Fixture Repo" "Test Infrastructure" "arch_testing.md" "TESTING"

commit_and_tag "main/test_fixture_repo/repo-with-duplicate-tag" \
    "Bare git fixture repo with a pre-existing tag for overwrite testing"

# =====================================================================
echo ""
echo "--- workflow_checklist_system ---"

reset_workdir
create_base_project

mkdir -p .purlin/cache
cat > .purlin/cache/handoff_checklist.json <<'EOF'
{
    "checklist_id": "isolated-push-v1",
    "steps": [
        {"id": "dirty_check", "label": "Working tree clean", "status": "passed"},
        {"id": "tests_pass", "label": "All tests pass", "status": "failed", "message": "2 tests failed"},
        {"id": "branch_ahead", "label": "Branch ahead of collab", "status": "passed"},
        {"id": "merge_ff", "label": "Fast-forward merge possible", "status": "passed"}
    ],
    "result": "BLOCKED",
    "timestamp": "2026-01-20T12:00:00Z"
}
EOF

commit_and_tag "main/workflow_checklist_system/mixed-step-statuses" \
    "Project with checklist containing passed, failed, and skipped steps"

# =====================================================================
echo ""
echo "--- git_operation_cache ---"

# --- Tag 1: fresh-repo-no-cache ---
reset_workdir
create_base_project

# 5 features: 2 Complete, 1 Testing, 2 TODO
create_feature "alpha.md" "Alpha" "Core" "arch_testing.md" "COMPLETE"
create_feature "beta.md" "Beta" "Core" "arch_testing.md" "COMPLETE"
create_feature "gamma.md" "Gamma" "Core" "arch_testing.md" "TESTING"
create_feature "delta.md" "Delta" "Core" "arch_testing.md" "TODO"
create_feature "epsilon.md" "Epsilon" "Core" "arch_testing.md" "TODO"

# Status commits for Complete/Testing features
git add -A >/dev/null 2>&1
git commit -m "feat: add five features" >/dev/null 2>&1
git commit --allow-empty -m "status(alpha): [Complete features/alpha.md] [Scope: full]" >/dev/null 2>&1
git commit --allow-empty -m "status(beta): [Complete features/beta.md] [Scope: full]" >/dev/null 2>&1
git commit --allow-empty -m "status(gamma): [Ready for Verification features/gamma.md] [Scope: full]" >/dev/null 2>&1

# Ensure NO cache files exist
rm -rf .purlin/cache/status_commit_cache.json .purlin/cache/git_status_snapshot.txt 2>/dev/null || true

git add -A >/dev/null 2>&1
git commit -m "chore: ensure no cache files" --allow-empty >/dev/null 2>&1
git tag "main/git_operation_cache/fresh-repo-no-cache" >/dev/null 2>&1
TAG_COUNT=$((TAG_COUNT + 1))
echo "  [$TAG_COUNT] main/git_operation_cache/fresh-repo-no-cache"

# --- Tag 2: populated-cache-current-head ---
CURRENT_HEAD="$(git rev-parse HEAD)"
CURRENT_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > .purlin/cache/status_commit_cache.json <<CEOF
{
    "generated_at": "$CURRENT_TS",
    "git_head": "$CURRENT_HEAD",
    "entries": {
        "features/alpha.md": {
            "status": "COMPLETE",
            "commit_hash": "$CURRENT_HEAD",
            "spec_content_hash": "abc123placeholder"
        },
        "features/beta.md": {
            "status": "COMPLETE",
            "commit_hash": "$CURRENT_HEAD",
            "spec_content_hash": "def456placeholder"
        },
        "features/gamma.md": {
            "status": "TESTING",
            "commit_hash": "$CURRENT_HEAD"
        }
    }
}
CEOF

git add -A >/dev/null 2>&1
git commit -m "chore: add populated cache matching HEAD" >/dev/null 2>&1
git tag "main/git_operation_cache/populated-cache-current-head" >/dev/null 2>&1
TAG_COUNT=$((TAG_COUNT + 1))
echo "  [$TAG_COUNT] main/git_operation_cache/populated-cache-current-head"

# --- Tag 3: populated-cache-stale-head ---
cat > .purlin/cache/status_commit_cache.json <<'CEOF'
{
    "generated_at": "2026-01-01T00:00:00Z",
    "git_head": "0000000000000000000000000000000000000000",
    "entries": {
        "features/alpha.md": {
            "status": "COMPLETE",
            "commit_hash": "0000000000000000000000000000000000000000"
        }
    }
}
CEOF

git add -A >/dev/null 2>&1
git commit -m "chore: add stale cache with wrong HEAD" >/dev/null 2>&1
git tag "main/git_operation_cache/populated-cache-stale-head" >/dev/null 2>&1
TAG_COUNT=$((TAG_COUNT + 1))
echo "  [$TAG_COUNT] main/git_operation_cache/populated-cache-stale-head"

# --- Tag 4: many-features-for-batching ---
reset_workdir
create_base_project

# Create 60+ companion files on main
for i in $(seq 1 65); do
    fname="$(printf 'feature_%03d' "$i")"
    create_feature "${fname}.md" "Feature $i" "Core" "arch_testing.md" "COMPLETE"
    cat > "features/${fname}.impl.md" <<IEOF
---
name: Feature $i Implementation
description: Impl notes for feature $i
type: project
---

## Implementation Notes

Companion file for feature $i.
IEOF
done

git add -A >/dev/null 2>&1
git commit -m "feat: add 65 features with companion files" >/dev/null 2>&1

# Create a branch with changes to all companion files
git checkout -b batch-changes >/dev/null 2>&1
for i in $(seq 1 65); do
    fname="$(printf 'feature_%03d' "$i")"
    echo "Updated companion content for batch test." >> "features/${fname}.impl.md"
done
git add -A >/dev/null 2>&1
git commit -m "chore: update all 65 companion files" >/dev/null 2>&1

# Tag on the branch
git tag "main/git_operation_cache/many-features-for-batching" >/dev/null 2>&1
TAG_COUNT=$((TAG_COUNT + 1))
echo "  [$TAG_COUNT] main/git_operation_cache/many-features-for-batching"

git checkout main >/dev/null 2>&1 || git checkout master >/dev/null 2>&1

# --- Tag 5: mixed-changes-branch ---
reset_workdir
create_base_project

create_feature "existing_a.md" "Existing A" "Core" "arch_testing.md" "COMPLETE"
create_feature "existing_b.md" "Existing B" "Core" "arch_testing.md" "COMPLETE"
create_feature "to_delete.md" "To Delete" "Core" "arch_testing.md" "TODO"
cat > "features/existing_a.impl.md" <<'IEOF'
## Implementation Notes
Original companion for A.
IEOF

git add -A >/dev/null 2>&1
git commit -m "feat: base state for mixed changes" >/dev/null 2>&1

# Branch with adds, modifies, deletes
git checkout -b mixed-changes >/dev/null 2>&1

# Modify
echo "Modified content." >> features/existing_a.md
echo "Updated companion." >> features/existing_a.impl.md

# Add new
create_feature "new_feature.md" "New Feature" "Core" "arch_testing.md" "TODO"

# Delete
git rm features/to_delete.md >/dev/null 2>&1

git add -A >/dev/null 2>&1
git commit -m "chore: mixed adds, modifies, deletes" >/dev/null 2>&1

git tag "main/git_operation_cache/mixed-changes-branch" >/dev/null 2>&1
TAG_COUNT=$((TAG_COUNT + 1))
echo "  [$TAG_COUNT] main/git_operation_cache/mixed-changes-branch"

git checkout main >/dev/null 2>&1 || git checkout master >/dev/null 2>&1

# =====================================================================
echo ""
echo "--- git_timestamp_resilience ---"

# --- Tag 1: same-second-commits ---
reset_workdir
create_base_project

create_feature "ts_alpha.md" "TS Alpha" "Core" "arch_testing.md" "TODO"
create_feature "ts_beta.md" "TS Beta" "Core" "arch_testing.md" "TODO"

git add -A >/dev/null 2>&1
git commit -m "feat: add timestamp test features" >/dev/null 2>&1

# Two status commits with identical author dates (same second)
GIT_AUTHOR_DATE="2026-01-15T12:00:00Z" GIT_COMMITTER_DATE="2026-01-15T12:00:00Z" \
    git commit --allow-empty -m "status(ts_alpha): [Complete features/ts_alpha.md] [Scope: full]" >/dev/null 2>&1
GIT_AUTHOR_DATE="2026-01-15T12:00:00Z" GIT_COMMITTER_DATE="2026-01-15T12:00:00Z" \
    git commit --allow-empty -m "status(ts_beta): [Complete features/ts_beta.md] [Scope: full]" >/dev/null 2>&1

commit_and_tag "main/git_timestamp_resilience/same-second-commits" \
    "Two status commits with identical timestamps"

# --- Tag 2: normal-ordering ---
reset_workdir
create_base_project

create_feature "ord_alpha.md" "Ord Alpha" "Core" "arch_testing.md" "TODO"
create_feature "ord_beta.md" "Ord Beta" "Core" "arch_testing.md" "TODO"

git add -A >/dev/null 2>&1
git commit -m "feat: add ordering test features" >/dev/null 2>&1

GIT_AUTHOR_DATE="2026-01-15T12:00:00Z" GIT_COMMITTER_DATE="2026-01-15T12:00:00Z" \
    git commit --allow-empty -m "status(ord_alpha): [Complete features/ord_alpha.md] [Scope: full]" >/dev/null 2>&1
GIT_AUTHOR_DATE="2026-01-15T13:00:00Z" GIT_COMMITTER_DATE="2026-01-15T13:00:00Z" \
    git commit --allow-empty -m "status(ord_beta): [Complete features/ord_beta.md] [Scope: full]" >/dev/null 2>&1

commit_and_tag "main/git_timestamp_resilience/normal-ordering" \
    "Two status commits with 1-hour gap between timestamps"

# =====================================================================
echo ""
echo "--- agent_interactions: builder role fixtures ---"

# builder_startup/todo-features
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

create_feature "feat_auth.md" "Authentication" "Security" "arch_testing.md" "TODO"
create_feature "feat_api.md" "API Gateway" "Backend" "arch_testing.md" "COMPLETE"
create_tests_json_pass "feat_api"

cat > README.md <<'EOF'
# Test Project

## Features
- Authentication: User login and session management.
- API Gateway: Backend API routing.
EOF

commit_and_tag "main/builder_startup/todo-features" \
    "Project with TODO feature for Engineer role testing"

# =====================================================================
echo ""
echo "--- agent_interactions: qa role fixtures ---"

# qa_verify/pending-verification
reset_workdir
create_base_project

for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done

create_feature_with_manual "feat_dashboard.md" "Dashboard" "UI" "arch_testing.md" "TESTING" \
    "Visual rendering check" "Responsive layout verification"
create_tests_json_pass "feat_dashboard"

cat > README.md <<'EOF'
# Test Project

## Features
- Dashboard: Interactive project status dashboard.
EOF

commit_and_tag "main/qa_verify/pending-verification" \
    "Project with TESTING feature for QA role testing"

# =====================================================================
# PUSH ALL TAGS TO BARE REPO
# =====================================================================

echo ""
echo "Pushing to bare repo..."
git push origin --all >/dev/null 2>&1
git push origin --tags >/dev/null 2>&1

echo ""
echo "=== Fixture Repo Complete ==="
echo "Location: $OUTPUT_DIR"
echo "Tags created: $TAG_COUNT"
echo ""
echo "Tags:"
git tag | sort
echo ""
echo "To list tags: git -C '$OUTPUT_DIR' tag"
echo "To verify: tools/test_support/fixture.sh list '$OUTPUT_DIR'"
