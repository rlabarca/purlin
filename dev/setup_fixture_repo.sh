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
git config user.name "Purlin Fixture Builder"

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
    "critic_llm_enabled": false,
    "agents": {
        "architect": { "model": "claude-opus-4-6", "startup_sequence": true, "recommend_next_actions": true },
        "builder": { "model": "claude-opus-4-6", "startup_sequence": true, "recommend_next_actions": true },
        "qa": { "model": "claude-sonnet-4-6", "startup_sequence": true, "recommend_next_actions": true }
    }
}
EOF

    # Override templates
    for f in HOW_WE_WORK_OVERRIDES.md BUILDER_OVERRIDES.md ARCHITECT_OVERRIDES.md QA_OVERRIDES.md; do
        echo "# $f" > ".purlin/$f"
    done

    # Minimal anchor
    cat > features/policy_critic.md <<'EOF'
# Policy: Critic Coordination Engine

> Label: "Policy: Critic Coordination Engine"
> Category: "Coordination & Lifecycle"

## 1. Purpose
Defines the Critic's role as the coordination engine.

## 2. Invariants

### 2.1 Dual-Gate Principle
Spec Gate and Implementation Gate.
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
        echo "> Web Testable: true"
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
        echo "    Given the CDD server is running"
        echo "    When the page loads"
        echo "    Then the content renders correctly"
        echo ""
        echo "### Manual Scenarios (Human Verification Required)"
        echo ""
        for scenario in "${scenarios[@]}"; do
            echo "#### Scenario: $scenario"
            echo ""
            echo "    Given the CDD dashboard is open"
            echo "    When the user views the page"
            echo "    Then the display is correct"
            echo ""
        done
    } > "features/$fname"
}

# Creates a critic.json with given role statuses
create_critic_json() {
    local dir="$1" architect="$2" builder="$3" qa="$4"
    mkdir -p "tests/$dir"
    cat > "tests/$dir/critic.json" <<EOF
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {
        "architect": "$architect",
        "builder": "$builder",
        "qa": "$qa"
    },
    "verification_effort": {
        "auto_web": 0, "auto_test_only": 0, "auto_skip": 0,
        "manual_interactive": 0, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 0, "total_manual": 0, "summary": "no QA items"
    },
    "change_scope": "full",
    "regression_scope": {}
}
EOF
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

# Creates a CRITIC_REPORT.md
create_critic_report() {
    local content="$1"
    echo "$content" > CRITIC_REPORT.md
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
echo "--- cdd_agent_configuration ---"

reset_workdir
create_base_project

# Override config with different models per agent
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "critic_llm_enabled": false,
    "agents": {
        "architect": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "startup_sequence": true,
            "recommend_next_actions": true,
            "context_guard": true,
            "context_guard_threshold": 80
        },
        "builder": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": false,
            "startup_sequence": true,
            "recommend_next_actions": false,
            "context_guard": true,
            "context_guard_threshold": 60
        },
        "qa": {
            "model": "claude-haiku-4-5-20251001",
            "effort": "low",
            "bypass_permissions": true,
            "startup_sequence": false,
            "recommend_next_actions": false,
            "context_guard": false
        }
    },
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "capabilities": {"effort": true, "permissions": true}},
        {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "capabilities": {"effort": true, "permissions": true}},
        {"id": "claude-haiku-4-5-20251001", "label": "Haiku 4.5", "capabilities": {"effort": true, "permissions": true}}
    ]
}
EOF

create_feature "cdd_agent_configuration.md" "CDD Agent Configuration" "CDD Dashboard" "policy_critic.md" "TESTING"
create_critic_json "cdd_agent_configuration" "DONE" "DONE" "TODO"
create_tests_json_pass "cdd_agent_configuration"

commit_and_tag "main/cdd_agent_configuration/mixed-models" \
    "Different models per agent for verifying model badges and capability-gated controls"

# =====================================================================
echo ""
echo "--- cdd_branch_collab ---"

reset_workdir
create_base_project
create_feature "cdd_branch_collab.md" "CDD Branch Collaboration" "CDD Dashboard" "policy_critic.md" "TESTING"

# ahead-3: simulate a branch that is 3 commits ahead
echo "collab/testbranch" > .purlin/runtime/active_branch
create_critic_json "cdd_branch_collab" "DONE" "DONE" "TODO"
create_tests_json_pass "cdd_branch_collab"

# Create feature_status.json showing branch sync state
cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "branch_collab_branches": [
        {"name": "testbranch", "active": true, "sync_state": "AHEAD", "commits_ahead": 3, "commits_behind": 0}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_branch_collab/ahead-3" \
    "Branch 3 commits ahead of collaboration branch"

# behind-2
cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "branch_collab_branches": [
        {"name": "testbranch", "active": true, "sync_state": "BEHIND", "commits_ahead": 0, "commits_behind": 2}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_branch_collab/behind-2" \
    "Branch 2 commits behind collaboration branch"

# diverged
cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "branch_collab_branches": [
        {"name": "testbranch", "active": true, "sync_state": "DIVERGED", "commits_ahead": 2, "commits_behind": 1}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_branch_collab/diverged" \
    "Both branch and collaboration branch have unique commits"

# same
cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "branch_collab_branches": [
        {"name": "testbranch", "active": true, "sync_state": "SAME", "commits_ahead": 0, "commits_behind": 0}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_branch_collab/same" \
    "Branch at same position as collaboration branch"

# =====================================================================
echo ""
echo "--- cdd_isolated_teams ---"

reset_workdir
create_base_project
create_feature "cdd_isolated_teams.md" "CDD Isolated Teams" "CDD Dashboard" "policy_critic.md" "TESTING"
create_critic_json "cdd_isolated_teams" "DONE" "DONE" "TODO"
create_tests_json_pass "cdd_isolated_teams"

# two-worktrees: two worktrees at AHEAD and SAME states
cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "isolated_sessions": [
        {"name": "feat1", "branch": "isolated/feat1", "sync_state": "AHEAD", "commits_ahead": 2, "commits_behind": 0, "dirty": false},
        {"name": "ui", "branch": "isolated/ui", "sync_state": "SAME", "commits_ahead": 0, "commits_behind": 0, "dirty": false}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_isolated_teams/two-worktrees" \
    "Two worktrees at AHEAD and SAME states for verifying Sessions table"

# delivery-phase-active
mkdir -p .purlin/cache
cat > .purlin/cache/delivery_plan.md <<'EOF'
# Delivery Plan

## Phase 1: Core [COMPLETE]
- feature_a.md

## Phase 2: UI [IN_PROGRESS]
- feature_b.md
- feature_c.md

## Phase 3: Polish [PENDING]
- feature_d.md
EOF

cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "isolated_sessions": [
        {"name": "feat1", "branch": "isolated/feat1", "sync_state": "AHEAD", "commits_ahead": 1, "commits_behind": 0, "dirty": false, "delivery_phase": "Phase 2 of 3"}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_isolated_teams/delivery-phase-active" \
    "Worktree with an active delivery plan for verifying Phase N/M orange badge"

# two-worktrees-mixed
rm -f .purlin/cache/delivery_plan.md
cat > .purlin/cache/feature_status.json <<'EOF'
{
    "features": [],
    "isolated_sessions": [
        {"name": "feat1", "branch": "isolated/feat1", "sync_state": "AHEAD", "commits_ahead": 3, "commits_behind": 0, "dirty": true},
        {"name": "bugfix", "branch": "isolated/bugfix", "sync_state": "BEHIND", "commits_ahead": 0, "commits_behind": 1, "dirty": false}
    ],
    "generated_at": "2026-01-01T00:00:00Z"
}
EOF

commit_and_tag "main/cdd_isolated_teams/two-worktrees-mixed" \
    "Two worktrees with different sync states and uncommitted changes"

# =====================================================================
echo ""
echo "--- cdd_lifecycle ---"

reset_workdir
create_base_project

# mixed-statuses: features in TODO, TESTING, and COMPLETE
create_feature "feature_todo.md" "Feature Todo" "Test" "policy_critic.md" "TODO"
create_feature "feature_testing.md" "Feature Testing" "Test" "policy_critic.md" "TESTING"
create_feature "feature_complete.md" "Feature Complete" "Test" "policy_critic.md" "COMPLETE"

create_critic_json "feature_todo" "DONE" "TODO" "N/A"
create_critic_json "feature_testing" "DONE" "DONE" "TODO"
create_critic_json "feature_complete" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feature_testing"
create_tests_json_pass "feature_complete"

commit_and_tag "main/cdd_lifecycle/mixed-statuses" \
    "Project with features in TODO, TESTING, and COMPLETE lifecycle states"

# all-complete
reset_workdir
create_base_project
create_feature "feature_a.md" "Feature A" "Test" "policy_critic.md" "COMPLETE"
create_feature "feature_b.md" "Feature B" "Test" "policy_critic.md" "COMPLETE"
create_feature "feature_c.md" "Feature C" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feature_a" "DONE" "DONE" "CLEAN"
create_critic_json "feature_b" "DONE" "DONE" "CLEAN"
create_critic_json "feature_c" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feature_a"
create_tests_json_pass "feature_b"
create_tests_json_pass "feature_c"

commit_and_tag "main/cdd_lifecycle/all-complete" \
    "Project where every feature is at COMPLETE lifecycle state"

# =====================================================================
echo ""
echo "--- cdd_qa_effort_display ---"

reset_workdir
create_base_project

# Features with AUTO vs TODO QA states
create_web_feature "feature_auto.md" "Feature Auto" "CDD Dashboard" "policy_critic.md" "TESTING" "Web Dashboard Check"
create_feature "feature_todo_qa.md" "Feature Manual" "Process" "policy_critic.md" "TESTING"
create_tests_json_pass "feature_auto"
create_tests_json_pass "feature_todo_qa"

# AUTO: web-testable with manual scenarios -> auto_web
mkdir -p tests/feature_auto
cat > tests/feature_auto/critic.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"},
    "verification_effort": {
        "auto_web": 1, "auto_test_only": 0, "auto_skip": 0,
        "manual_interactive": 0, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 1, "total_manual": 0, "summary": "1 auto-web"
    },
    "change_scope": "full"
}
EOF

# TODO: non-web with manual scenarios -> manual_interactive
mkdir -p tests/feature_todo_qa
cat > tests/feature_todo_qa/critic.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"},
    "verification_effort": {
        "auto_web": 0, "auto_test_only": 0, "auto_skip": 0,
        "manual_interactive": 1, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 0, "total_manual": 1, "summary": "1 manual-interactive"
    },
    "change_scope": "full"
}
EOF

commit_and_tag "main/cdd_qa_effort_display/auto-and-todo" \
    "Features with AUTO vs TODO QA states for verifying green vs yellow distinction"

# =====================================================================
echo ""
echo "--- cdd_spec_map ---"

reset_workdir
create_base_project

# Features with varying scenario counts: 0, 5, 20+
cat > features/feature_zero.md <<'FEAT'
# Feature: Zero Scenarios

> Label: "Zero Scenarios"
> Category: "Test"
> Prerequisite: features/policy_critic.md

[COMPLETE]

## 1. Overview
Feature with no scenarios.

## 2. Requirements
### 2.1 Basic
- None.

## 3. Scenarios
### Automated Scenarios
None.
### Manual Scenarios (Human Verification Required)
None.
FEAT

# 5 scenarios
{
    echo "# Feature: Five Scenarios"
    echo ""
    echo "> Label: \"Five Scenarios\""
    echo "> Category: \"Test\""
    echo "> Prerequisite: features/policy_critic.md"
    echo ""
    echo "[TESTING]"
    echo ""
    echo "## 1. Overview"
    echo "Feature with 5 scenarios."
    echo ""
    echo "## 2. Requirements"
    echo "### 2.1 Basic"
    echo "- Has 5 scenarios."
    echo ""
    echo "## 3. Scenarios"
    echo "### Automated Scenarios"
    for i in $(seq 1 5); do
        echo ""
        echo "#### Scenario: Test scenario $i"
        echo ""
        echo "    Given precondition $i"
        echo "    When action $i"
        echo "    Then result $i"
    done
    echo ""
    echo "### Manual Scenarios (Human Verification Required)"
    echo "None."
} > features/feature_five.md

# 22 scenarios
{
    echo "# Feature: Many Scenarios"
    echo ""
    echo "> Label: \"Many Scenarios\""
    echo "> Category: \"Test\""
    echo "> Prerequisite: features/policy_critic.md"
    echo ""
    echo "[TODO]"
    echo ""
    echo "## 1. Overview"
    echo "Feature with 22 scenarios."
    echo ""
    echo "## 2. Requirements"
    echo "### 2.1 Basic"
    echo "- Has 22 scenarios."
    echo ""
    echo "## 3. Scenarios"
    echo "### Automated Scenarios"
    for i in $(seq 1 22); do
        echo ""
        echo "#### Scenario: Test scenario $i"
        echo ""
        echo "    Given precondition $i"
        echo "    When action $i"
        echo "    Then result $i"
    done
    echo ""
    echo "### Manual Scenarios (Human Verification Required)"
    echo "None."
} > features/feature_many.md

create_critic_json "feature_zero" "DONE" "DONE" "CLEAN"
create_critic_json "feature_five" "DONE" "DONE" "TODO"
create_critic_json "feature_many" "DONE" "TODO" "N/A"
create_tests_json_pass "feature_zero"
create_tests_json_pass "feature_five"

commit_and_tag "main/cdd_spec_map/varied-scenarios" \
    "Project with features having 0, 5, and 20+ scenarios for spec map rendering"

# =====================================================================
echo ""
echo "--- cdd_startup_controls ---"

reset_workdir
create_base_project
create_feature "sample_feature.md" "Sample Feature" "Test" "policy_critic.md" "TODO"

# Copy real instruction files for behavior testing
for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
    if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
        cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
    fi
done
if [[ -d "$PROJECT_ROOT/instructions/references" ]]; then
    cp -r "$PROJECT_ROOT/instructions/references/"* "instructions/references/" 2>/dev/null || true
fi

# startup-print-sequence (default config)
commit_and_tag "main/cdd_startup_controls/startup-print-sequence" \
    "Default config (startup_sequence: true, recommend_next_actions: true)"

# all-disabled
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "startup_sequence": false, "recommend_next_actions": false },
        "builder": { "model": "claude-opus-4-6", "startup_sequence": false, "recommend_next_actions": false },
        "qa": { "model": "claude-sonnet-4-6", "startup_sequence": false, "recommend_next_actions": false }
    }
}
EOF
commit_and_tag "main/cdd_startup_controls/all-disabled" \
    "Project with startup_sequence false for all roles"

# expert-mode
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "startup_sequence": false, "recommend_next_actions": false },
        "builder": { "model": "claude-opus-4-6", "startup_sequence": false, "recommend_next_actions": false },
        "qa": { "model": "claude-sonnet-4-6", "startup_sequence": false, "recommend_next_actions": false }
    }
}
EOF
commit_and_tag "main/cdd_startup_controls/expert-mode" \
    "Config with startup_sequence: false, recommend_next_actions: false"

# guided-mode
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "startup_sequence": true, "recommend_next_actions": true },
        "builder": { "model": "claude-opus-4-6", "startup_sequence": true, "recommend_next_actions": true },
        "qa": { "model": "claude-sonnet-4-6", "startup_sequence": true, "recommend_next_actions": true }
    }
}
EOF

# Add a TODO feature and CRITIC_REPORT so guided mode has work items
create_feature "todo_feature.md" "Todo Feature" "Test" "policy_critic.md" "TODO"
cat > CRITIC_REPORT.md <<'REPORT'
# Critic Quality Gate Report

Generated: 2026-01-01T00:00:00Z

## Summary

| Feature | Spec Gate | Implementation Gate | User Testing |
|---------|-----------|--------------------:|-------------|
| features/todo_feature.md | PASS | FAIL | CLEAN |

## Action Items by Role

### Architect

No action items.

### Builder

- **[HIGH]** (todo_feature): Review and implement spec changes for todo_feature

### QA

No action items.
REPORT

commit_and_tag "main/cdd_startup_controls/guided-mode" \
    "Config with startup_sequence: true, recommend_next_actions: true"

# orient-only-mode
cat > .purlin/config.json <<'EOF'
{
    "tools_root": "tools",
    "agents": {
        "architect": { "model": "claude-opus-4-6", "startup_sequence": true, "recommend_next_actions": false },
        "builder": { "model": "claude-opus-4-6", "startup_sequence": true, "recommend_next_actions": false },
        "qa": { "model": "claude-sonnet-4-6", "startup_sequence": true, "recommend_next_actions": false }
    }
}
EOF
commit_and_tag "main/cdd_startup_controls/orient-only-mode" \
    "Config with startup_sequence: true, recommend_next_actions: false"

# =====================================================================
echo ""
echo "--- cdd_status_monitor ---"

reset_workdir
create_base_project

# mixed-states: features in TODO, DONE, FAIL, CLEAN
create_feature "feat_todo.md" "Feature TODO" "CDD Dashboard" "policy_critic.md" "TODO"
create_feature "feat_done.md" "Feature DONE" "CDD Dashboard" "policy_critic.md" "TESTING"
create_feature "feat_fail.md" "Feature FAIL" "CDD Dashboard" "policy_critic.md" "TESTING"
create_feature "feat_clean.md" "Feature CLEAN" "CDD Dashboard" "policy_critic.md" "COMPLETE"

create_critic_json "feat_todo" "DONE" "TODO" "N/A"
create_critic_json "feat_done" "DONE" "DONE" "TODO"
create_critic_json "feat_fail" "DONE" "FAIL" "FAIL"
create_critic_json "feat_clean" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_done"
create_tests_json_fail "feat_fail"
create_tests_json_pass "feat_clean"

commit_and_tag "main/cdd_status_monitor/mixed-states" \
    "Features in TODO, DONE, FAIL, and CLEAN states for badge colors and sorting"

# tombstone-present
mkdir -p features/tombstones
cat > features/tombstones/old_feature.md <<'EOF'
# Tombstone: Old Feature

**Retired:** 2026-01-01
**Reason:** Feature replaced by new_feature.

## Files to Delete
- tools/old_feature/

## Dependencies to Check
- features/new_feature.md references old_feature utilities
EOF

commit_and_tag "main/cdd_status_monitor/tombstone-present" \
    "A tombstone file exists at features/tombstones/ for testing red styling"

# empty-active: all features complete
rm -rf features/tombstones
reset_workdir
create_base_project
create_feature "feat_a.md" "Feature A" "CDD Dashboard" "policy_critic.md" "COMPLETE"
create_feature "feat_b.md" "Feature B" "CDD Dashboard" "policy_critic.md" "COMPLETE"
create_critic_json "feat_a" "DONE" "DONE" "CLEAN"
create_critic_json "feat_b" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_a"
create_tests_json_pass "feat_b"

commit_and_tag "main/cdd_status_monitor/empty-active" \
    "All features complete, Active section empty for empty-state badge behavior"

# =====================================================================
echo ""
echo "--- collab_whats_different ---"

reset_workdir
create_base_project
create_feature "feature_changed.md" "Changed Feature" "Test" "policy_critic.md" "TESTING"
create_feature "feature_same.md" "Same Feature" "Test" "policy_critic.md" "COMPLETE"
echo "collab/testbranch" > .purlin/runtime/active_branch
create_critic_json "feature_changed" "DONE" "DONE" "TODO"
create_critic_json "feature_same" "DONE" "DONE" "CLEAN"
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
    "context_guard_threshold": 80,
    "agents": {
        "builder": { "model": "claude-opus-4-6", "context_guard_threshold": 80 }
    }
}
EOF
cat > .purlin/config.local.json <<'EOF'
{
    "context_guard_threshold": 50,
    "agents": {
        "builder": { "model": "claude-sonnet-4-6", "context_guard_threshold": 40 }
    }
}
EOF
create_feature "config_layering.md" "Config Layering" "Install" "policy_critic.md" "TESTING"
create_critic_json "config_layering" "DONE" "DONE" "TODO"
create_tests_json_pass "config_layering"

commit_and_tag "main/config_layering/local-override-present" \
    "Project with config.local.json overriding values from config.json"

# config-json-only
rm -f .purlin/config.local.json

commit_and_tag "main/config_layering/config-json-only" \
    "Project with config.json only, no local override file"

# =====================================================================
echo ""
echo "--- critic_tool ---"

# spec-gate-fail: feature missing required sections
reset_workdir
create_base_project
cat > features/broken_feature.md <<'EOF'
# Feature: Broken Feature

> Label: "Broken Feature"
> Category: "Test"

[TODO]

This feature is missing Overview, Requirements, and Scenarios sections.
EOF
create_feature "good_feature.md" "Good Feature" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "good_feature" "DONE" "DONE" "CLEAN"
create_tests_json_pass "good_feature"

commit_and_tag "main/critic_tool/spec-gate-fail" \
    "Project with a feature missing required sections"

# traceability-gap
reset_workdir
create_base_project
create_feature "traced_feature.md" "Traced Feature" "Test" "policy_critic.md" "TESTING"
# No matching test files -> traceability gap
create_critic_json "traced_feature" "DONE" "DONE" "TODO"

commit_and_tag "main/critic_tool/traceability-gap" \
    "Feature with automated scenarios but no matching test files"

# cascade-reset: anchor + 3 dependent features
reset_workdir
create_base_project

cat > features/arch_data.md <<'EOF'
# Architecture: Data Layer

> Label: "Arch: Data Layer"
> Category: "Architecture"

## Purpose
Defines data layer constraints.

## 2. Invariants

### 2.1 Data Access
All data access through repository pattern.
EOF

create_feature "dep_a.md" "Dependent A" "Test" "arch_data.md" "COMPLETE"
create_feature "dep_b.md" "Dependent B" "Test" "arch_data.md" "COMPLETE"
create_feature "dep_c.md" "Dependent C" "Test" "arch_data.md,policy_critic.md" "TESTING"
create_critic_json "dep_a" "DONE" "DONE" "CLEAN"
create_critic_json "dep_b" "DONE" "DONE" "CLEAN"
create_critic_json "dep_c" "DONE" "DONE" "TODO"
create_tests_json_pass "dep_a"
create_tests_json_pass "dep_b"
create_tests_json_pass "dep_c"

commit_and_tag "main/critic_tool/cascade-reset" \
    "Anchor node + 3 dependent features for testing status cascade on anchor edit"

# mixed-discoveries: features with BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE
reset_workdir
create_base_project

cat > features/buggy_feature.md <<'FEAT'
# Feature: Buggy Feature

> Label: "Buggy Feature"
> Category: "Test"
> Prerequisite: features/policy_critic.md

[TESTING]

## 1. Overview
Feature with various discovery types.

## 2. Requirements
### 2.1 Basic
- Does things.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Basic operation
    Given setup
    When action
    Then result

### Manual Scenarios (Human Verification Required)

#### Scenario: Manual check
    Given system ready
    When user checks
    Then correct

## User Testing Discoveries

### [BUG] Button does not respond on mobile
- **Status:** OPEN
- **Found by:** QA
- **Date:** 2026-01-15
- **Description:** Tap target too small on mobile devices.

### [DISCOVERY] Missing loading spinner
- **Status:** OPEN
- **Found by:** QA
- **Date:** 2026-01-16
- **Description:** No loading indicator during async operations.

### [INTENT_DRIFT] Sort order misleading
- **Status:** SPEC_UPDATED
- **Found by:** QA
- **Date:** 2026-01-14
- **Description:** Alphabetical sort is technically correct but users expect recency.

### [SPEC_DISPUTE] Error message wording
- **Status:** OPEN
- **Found by:** User
- **Date:** 2026-01-17
- **Description:** User disagrees with the error message text.
FEAT

create_critic_json "buggy_feature" "DONE" "TODO" "FAIL"
create_tests_json_pass "buggy_feature"

commit_and_tag "main/critic_tool/mixed-discoveries" \
    "Features with BUG, DISCOVERY, INTENT_DRIFT, SPEC_DISPUTE entries"

# builder-decisions
reset_workdir
create_base_project
create_feature "decided_feature.md" "Decided Feature" "Test" "policy_critic.md" "TESTING"
create_critic_json "decided_feature" "DONE" "DONE" "TODO"
create_tests_json_pass "decided_feature"

cat > features/decided_feature.impl.md <<'IMPL'
# Implementation Notes: Decided Feature

*   **[DEVIATION]** Used REST instead of GraphQL because the client library is more mature. (Severity: HIGH)
*   **[DISCOVERY]** The API returns paginated results even for small datasets. Need scenario coverage. (Severity: HIGH)
*   **[AUTONOMOUS]** Added request timeout of 30s since spec was silent on timeout. (Severity: WARN)
*   **[CLARIFICATION]** Interpreted "recent items" as last 7 days. (Severity: INFO)
*   **[DEVIATION]** Stored cache in memory instead of Redis. Acknowledged. (Severity: HIGH)
IMPL

commit_and_tag "main/critic_tool/builder-decisions" \
    "Companion files with acknowledged/unacknowledged DEVIATION and DISCOVERY tags"

# =====================================================================
echo ""
echo "--- impl_notes_companion ---"

reset_workdir
create_base_project
create_feature "noted_feature.md" "Noted Feature" "Test" "policy_critic.md" "TESTING"
create_critic_json "noted_feature" "DONE" "DONE" "TODO"
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
    "context_guard_threshold": 80,
    "agents": {
        "architect": { "model": "claude-opus-4-6", "context_guard": true, "context_guard_threshold": 90 },
        "builder": { "model": "claude-opus-4-6", "context_guard": true, "context_guard_threshold": 60 },
        "qa": { "model": "claude-sonnet-4-6", "context_guard": false, "context_guard_threshold": 80 }
    }
}
EOF

create_feature "pl_context_guard.md" "Context Guard" "Agent Skills" "policy_critic.md" "TESTING"
create_critic_json "pl_context_guard" "DONE" "DONE" "TODO"
create_tests_json_pass "pl_context_guard"

commit_and_tag "main/pl_context_guard/mixed-thresholds" \
    "Project with different context guard thresholds and enabled states per role"

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
if [[ -d "$PROJECT_ROOT/instructions/references" ]]; then
    cp -r "$PROJECT_ROOT/instructions/references/"* "instructions/references/" 2>/dev/null || true
fi

# architect-main-branch
commit_and_tag "main/pl_help/architect-main-branch" \
    "Project on main branch, default config"

# builder-isolated-branch
commit_and_tag "main/pl_help/builder-isolated-branch" \
    "Project on isolated/feat1 branch"

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
if [[ -d "$PROJECT_ROOT/instructions/references" ]]; then
    cp -r "$PROJECT_ROOT/instructions/references/"* "instructions/references/" 2>/dev/null || true
fi

# builder-mid-feature
cat > .purlin/cache/session_checkpoint.md <<'CHECKPOINT'
# Session Checkpoint

**Role:** Builder
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

## Builder Context
**Protocol Step:** 2
**Delivery Plan:** No delivery plan
**Work Queue:**
1. [HIGH] sample_feature.md
**Pending Decisions:** None
CHECKPOINT

create_feature "sample_feature.md" "Sample Feature" "Test" "policy_critic.md" "TODO"

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
create_feature "divergent_feature.md" "Divergent Feature" "Test" "policy_critic.md" "TESTING" \
    "### 2.2 Advanced
- Must support batch processing of up to 1000 items.
- Must validate input against JSON schema before processing."
create_critic_json "divergent_feature" "DONE" "DONE" "TODO"
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
echo "--- pl_web_verify ---"

reset_workdir
create_base_project

create_web_feature "web_feat_a.md" "Web Feature A" "CDD Dashboard" "policy_critic.md" "TESTING" "Dashboard Layout" "Theme Toggle"
create_web_feature "web_feat_b.md" "Web Feature B" "CDD Dashboard" "policy_critic.md" "TESTING" "Data Table"
create_feature "non_web_feat.md" "Non-Web Feature" "Process" "policy_critic.md" "TESTING"

create_critic_json "web_feat_a" "DONE" "DONE" "TODO"
create_critic_json "web_feat_b" "DONE" "DONE" "TODO"
create_critic_json "non_web_feat" "DONE" "DONE" "TODO"
create_tests_json_pass "web_feat_a"
create_tests_json_pass "web_feat_b"
create_tests_json_pass "non_web_feat"

commit_and_tag "main/pl_web_verify/web-testable-features" \
    "Project with multiple web-testable features for verifying discovery and execution flow"

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
create_feature "auto_only_feat.md" "Auto Only" "Test" "policy_critic.md" "TESTING"
mkdir -p tests/auto_only_feat
cat > tests/auto_only_feat/critic.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "CLEAN"},
    "verification_effort": {
        "auto_web": 0, "auto_test_only": 1, "auto_skip": 0,
        "manual_interactive": 0, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 1, "total_manual": 0, "summary": "1 auto-test-only"
    },
    "change_scope": "full"
}
EOF
create_tests_json_pass "auto_only_feat"

# manual feature
create_feature_with_manual "manual_feat.md" "Manual Feature" "Process" "policy_critic.md" "TESTING" "Hardware Check" "Visual Inspect"
mkdir -p tests/manual_feat
cat > tests/manual_feat/critic.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"},
    "verification_effort": {
        "auto_web": 0, "auto_test_only": 0, "auto_skip": 0,
        "manual_interactive": 2, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 0, "total_manual": 2, "summary": "2 manual-interactive"
    },
    "change_scope": "full"
}
EOF
create_tests_json_pass "manual_feat"

# mixed feature (web-testable with manual)
create_web_feature "mixed_feat.md" "Mixed Feature" "CDD Dashboard" "policy_critic.md" "TESTING" "Web Dashboard"
mkdir -p tests/mixed_feat
cat > tests/mixed_feat/critic.json <<'EOF'
{
    "spec_gate": {"status": "PASS", "details": []},
    "implementation_gate": {"status": "PASS", "details": []},
    "user_testing": {"status": "CLEAN", "details": []},
    "action_items": [],
    "role_status": {"architect": "DONE", "builder": "DONE", "qa": "TODO"},
    "verification_effort": {
        "auto_web": 1, "auto_test_only": 0, "auto_skip": 0,
        "manual_interactive": 0, "manual_visual": 0, "manual_hardware": 0,
        "total_auto": 1, "total_manual": 0, "summary": "1 auto-web"
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
create_feature "feat_a.md" "Feature A" "Test" "policy_critic.md" "COMPLETE"
create_feature "feat_b.md" "Feature B" "Test" "feat_a.md" "COMPLETE"
create_critic_json "feat_a" "DONE" "DONE" "CLEAN"
create_critic_json "feat_b" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_a"
create_tests_json_pass "feat_b"
create_dep_graph '{
    "cycles": [],
    "features": [
        {"file": "features/feat_a.md", "label": "Feature A", "prerequisites": ["policy_critic.md"]},
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
create_feature "parent_feat.md" "Parent Feature" "Test" "policy_critic.md" "COMPLETE" \
    "See also features/child_feat.md for implementation details."
create_feature "child_feat.md" "Child Feature" "Test" "parent_feat.md" "TESTING"
create_critic_json "parent_feat" "DONE" "DONE" "CLEAN"
create_critic_json "child_feat" "DONE" "DONE" "TODO"
create_tests_json_pass "parent_feat"
create_tests_json_pass "child_feat"

commit_and_tag "main/release_verify_deps/reverse-reference" \
    "Parent feature body-referencing child"

# release_zero_queue/all-clean
reset_workdir
create_base_project
create_feature "clean_a.md" "Clean A" "Test" "policy_critic.md" "COMPLETE"
create_feature "clean_b.md" "Clean B" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "clean_a" "DONE" "DONE" "CLEAN"
create_critic_json "clean_b" "DONE" "DONE" "CLEAN"
create_tests_json_pass "clean_a"
create_tests_json_pass "clean_b"

commit_and_tag "main/release_zero_queue/all-clean" \
    "All features DONE/CLEAN"

# release_zero_queue/builder-todo
reset_workdir
create_base_project
create_feature "todo_feat.md" "TODO Feature" "Test" "policy_critic.md" "TODO"
create_critic_json "todo_feat" "DONE" "TODO" "N/A"

commit_and_tag "main/release_zero_queue/builder-todo" \
    "Feature with builder: TODO"

# release_zero_queue/qa-open-items
reset_workdir
create_base_project
cat > features/qa_open_feat.md <<'FEAT'
# Feature: QA Open Feature

> Label: "QA Open Feature"
> Category: "Test"
> Prerequisite: features/policy_critic.md

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
create_critic_json "qa_open_feat" "DONE" "TODO" "FAIL"
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
create_feature "feat_alpha.md" "Feature Alpha" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feat_alpha" "DONE" "DONE" "CLEAN"
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
create_feature "feat_current.md" "Current Feature" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feat_current" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_current"
cat > README.md <<'EOF'
# Test Project

## Features
- Current Feature
- Old Deleted Feature (see features/old_deleted.md)
EOF

commit_and_tag "main/release_doc_consistency/stale-reference" \
    "README references deleted file"

# release_critic_consistency/clean
reset_workdir
create_base_project
create_feature "feat_x.md" "Feature X" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feat_x" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_x"

commit_and_tag "main/release_critic_consistency/clean" \
    "All Critic files consistent"

# release_critic_consistency/deprecated-term
reset_workdir
create_base_project
create_feature "feat_y.md" "Feature Y" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feat_y" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_y"
# A file using deprecated "quality gate" terminology
cat > CRITIC_REPORT.md <<'EOF'
# Critic Quality Gate Report

This is the quality gate report for the project.
EOF

commit_and_tag "main/release_critic_consistency/deprecated-term" \
    "File using quality gate"

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
# Builder Overrides

## Contradiction
The Builder MUST NOT commit code. This contradicts the base rule requiring immediate commits.
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
# Builder Overrides

## Stale Reference
See `tools/deleted_tool/run.sh` for the build script.
EOF

commit_and_tag "main/release_instruction_audit/stale-path" \
    "Override referencing deleted file"

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
        {"id": "purlin.critic_consistency", "enabled": true},
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
        {"id": "purlin.critic_consistency", "enabled": true},
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
echo "--- release_critic_consistency_check ---"

# consistent-docs
reset_workdir
create_base_project
create_feature "feat_p.md" "Feature P" "Test" "policy_critic.md" "COMPLETE"
create_feature "feat_q.md" "Feature Q" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feat_p" "DONE" "DONE" "CLEAN"
create_critic_json "feat_q" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_p"
create_tests_json_pass "feat_q"

cat > README.md <<'EOF'
# Test Project

Features: 2 total (2 complete).
EOF

commit_and_tag "main/release_critic_consistency_check/consistent-docs" \
    "Project where README matches Critic output and feature counts"

# stale-references
reset_workdir
create_base_project
create_feature "feat_r.md" "Feature R" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "feat_r" "DONE" "DONE" "CLEAN"
create_tests_json_pass "feat_r"

cat > README.md <<'EOF'
# Test Project

Features: 5 total (5 complete).
See features/old_removed_feature.md for details.
EOF

commit_and_tag "main/release_critic_consistency_check/stale-references" \
    "Project where README has outdated feature counts and stale references"

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
# Builder Overrides

## Lifecycle
States: DRAFT -> REVIEW -> DONE -> DEPLOYED
Features transition through four states.
EOF

commit_and_tag "main/release_doc_consistency_check/inconsistent-docs" \
    "Project with instruction files containing contradictory lifecycle definitions"

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

# =====================================================================
echo ""
echo "--- release_verify_dependency_integrity ---"

# acyclic-graph
reset_workdir
create_base_project
create_feature "layer1.md" "Layer 1" "Test" "policy_critic.md" "COMPLETE"
create_feature "layer2.md" "Layer 2" "Test" "layer1.md" "COMPLETE"
create_feature "layer3.md" "Layer 3" "Test" "layer2.md" "COMPLETE"
create_critic_json "layer1" "DONE" "DONE" "CLEAN"
create_critic_json "layer2" "DONE" "DONE" "CLEAN"
create_critic_json "layer3" "DONE" "DONE" "CLEAN"
create_tests_json_pass "layer1"
create_tests_json_pass "layer2"
create_tests_json_pass "layer3"
create_dep_graph '{
    "cycles": [],
    "features": [
        {"file": "features/layer1.md", "label": "Layer 1", "prerequisites": ["policy_critic.md"]},
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
create_feature "done_a.md" "Done A" "Test" "policy_critic.md" "COMPLETE"
create_feature "done_b.md" "Done B" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "done_a" "DONE" "DONE" "CLEAN"
create_critic_json "done_b" "DONE" "DONE" "CLEAN"
create_tests_json_pass "done_a"
create_tests_json_pass "done_b"

commit_and_tag "main/release_verify_zero_queue/all-clean" \
    "Project where all features have DONE/CLEAN status across all roles"

# features-with-open-items
reset_workdir
create_base_project
create_feature "open_feat.md" "Open Feature" "Test" "policy_critic.md" "TODO"
create_feature "done_feat.md" "Done Feature" "Test" "policy_critic.md" "COMPLETE"
create_critic_json "open_feat" "DONE" "TODO" "N/A"
create_critic_json "done_feat" "DONE" "DONE" "CLEAN"
create_tests_json_pass "done_feat"

commit_and_tag "main/release_verify_zero_queue/features-with-open-items" \
    "Project with features having TODO/BUG items blocking release"

# =====================================================================
echo ""
echo "--- spec_code_audit_role_clarity ---"

reset_workdir
create_base_project

create_feature "audit_target.md" "Audit Target" "Test" "policy_critic.md" "TESTING" \
    "### 2.2 Role Gating
- Only Architect may invoke /pl-spec.
- Only Builder may invoke /pl-build.
- Only QA may invoke /pl-verify."
create_critic_json "audit_target" "DONE" "DONE" "TODO"
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
git config user.name "Purlin Fixture Builder"

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

create_feature "test_fixture_repo.md" "Test Fixture Repo" "Test Infrastructure" "policy_critic.md" "TESTING"

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
git config user.name "Purlin Fixture Builder"

echo "original content" > file.txt
git add -A >/dev/null 2>&1
git commit -m "State for existing tag" >/dev/null 2>&1
git tag "main/test_feature/existing-state" >/dev/null 2>&1

git push origin --all >/dev/null 2>&1
git push origin --tags >/dev/null 2>&1

cd "$WORK_DIR"
cp -r "$DUP_BARE" .purlin/runtime/nested-fixture-repo-duplicate
rm -rf "$DUP_BARE" "$DUP_WORK"

create_feature "test_fixture_repo.md" "Test Fixture Repo" "Test Infrastructure" "policy_critic.md" "TESTING"

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
        {"id": "critic_clean", "label": "Critic report clean", "status": "skipped"},
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
