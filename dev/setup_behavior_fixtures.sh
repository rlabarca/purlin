#!/usr/bin/env bash
# dev/setup_behavior_fixtures.sh
#
# Creates a local bare git repository with fixture tags for the
# agent behavior test harness (dev/test_agent_behavior.sh).
#
# Each tag represents a controlled project state for one test scenario.
# Tags follow the convention: main/<feature-name>/<scenario-slug>
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default output location
OUTPUT_DIR="${1:-/tmp/purlin-behavior-fixtures}"

echo "Setting up behavior test fixtures at: $OUTPUT_DIR"

# Clean previous if exists
if [[ -d "$OUTPUT_DIR" ]]; then
    echo "Removing existing fixture repo..."
    rm -rf "$OUTPUT_DIR"
fi

# Create bare repo and working directory
BARE_DIR="$OUTPUT_DIR"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

git init --bare "$BARE_DIR" >/dev/null 2>&1

cd "$WORK_DIR"
git init >/dev/null 2>&1
git remote add origin "$BARE_DIR"
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Builder"

# --- Helper: create a base project structure ---
create_base_project() {
    # Copies instruction files from current project to simulate a real project state.
    # Args: none (operates on current WORK_DIR)

    mkdir -p instructions/references .purlin/runtime .purlin/cache features tests

    # Copy real instruction files (the test verifies the actual instruction content)
    for f in HOW_WE_WORK_BASE.md BUILDER_BASE.md ARCHITECT_BASE.md QA_BASE.md; do
        if [[ -f "$PROJECT_ROOT/instructions/$f" ]]; then
            cp "$PROJECT_ROOT/instructions/$f" "instructions/$f"
        fi
    done

    # Copy reference files needed by startup protocol
    if [[ -d "$PROJECT_ROOT/instructions/references" ]]; then
        cp -r "$PROJECT_ROOT/instructions/references/"* "instructions/references/" 2>/dev/null || true
    fi

    # Copy override templates
    for f in HOW_WE_WORK_OVERRIDES.md BUILDER_OVERRIDES.md ARCHITECT_OVERRIDES.md QA_OVERRIDES.md; do
        if [[ -f "$PROJECT_ROOT/.purlin/$f" ]]; then
            cp "$PROJECT_ROOT/.purlin/$f" ".purlin/$f"
        else
            echo "# $f" > ".purlin/$f"
        fi
    done

    # Minimal feature file for CDD to find
    cat > features/sample_feature.md <<'FEAT'
# Feature: Sample Feature

> Label: "Sample Feature"
> Category: "Test"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A sample feature for testing.

## 2. Requirements

### 2.1 Basic

- Does something.

## 3. Scenarios

### Automated Scenarios

None.

### Manual Scenarios (Human Verification Required)

None.
FEAT

    # Minimal policy_critic.md anchor
    cat > features/policy_critic.md <<'POLICY'
# Policy: Critic Coordination Engine

> Label: "Policy: Critic Coordination Engine"
> Category: "Coordination & Lifecycle"

[Complete]

## 1. Purpose

Defines the Critic's role as the coordination engine.

## 2. Invariants

### 2.1 Dual-Gate Principle
Spec Gate and Implementation Gate.
POLICY

    # Minimal CRITIC_REPORT.md
    cat > CRITIC_REPORT.md <<'REPORT'
# Critic Quality Gate Report

Generated: 2026-01-01T00:00:00Z

## Summary

| Feature | Spec Gate | Implementation Gate | User Testing |
|---------|-----------|--------------------:|-------------|
| features/sample_feature.md | PASS | PASS | CLEAN |

## Action Items by Role

### Architect

No action items.

### Builder

No action items.

### QA

No action items.
REPORT

    # Minimal dependency graph
    cat > .purlin/cache/dependency_graph.json <<'GRAPH'
{
  "cycles": [],
  "features": [
    {
      "category": "Test",
      "file": "features/sample_feature.md",
      "label": "Sample Feature",
      "prerequisites": ["policy_critic.md"]
    }
  ],
  "generated_at": "2026-01-01T00:00:00Z",
  "orphans": []
}
GRAPH
}

# --- Helper: set config ---
set_config() {
    local startup_sequence="${1:-true}"
    local recommend_next_actions="${2:-true}"

    cat > .purlin/config.json <<CONFIG
{
    "tools_root": "tools",
    "agents": {
        "architect": {
            "model": "claude-haiku-4-5-20251001",
            "startup_sequence": ${startup_sequence},
            "recommend_next_actions": ${recommend_next_actions}
        },
        "builder": {
            "model": "claude-haiku-4-5-20251001",
            "startup_sequence": ${startup_sequence},
            "recommend_next_actions": ${recommend_next_actions}
        },
        "qa": {
            "model": "claude-haiku-4-5-20251001",
            "startup_sequence": ${startup_sequence},
            "recommend_next_actions": ${recommend_next_actions}
        }
    }
}
CONFIG
}

# --- Helper: commit and tag ---
commit_and_tag() {
    local tag="$1"
    local message="${2:-State for $tag}"

    git add -A >/dev/null 2>&1
    git commit -m "$message" --allow-empty >/dev/null 2>&1
    git tag "$tag" >/dev/null 2>&1
}

# ===================================================================
# Fixture 1: main/cdd_startup_controls/startup-print-sequence
# Default config (startup_sequence: true, recommend_next_actions: true)
# ===================================================================
echo "Creating: main/cdd_startup_controls/startup-print-sequence"
rm -rf ./* .purlin 2>/dev/null || true
create_base_project
set_config true true
commit_and_tag "main/cdd_startup_controls/startup-print-sequence"

# ===================================================================
# Fixture 2: main/cdd_startup_controls/expert-mode
# Config with startup_sequence: false
# ===================================================================
echo "Creating: main/cdd_startup_controls/expert-mode"
set_config false false
commit_and_tag "main/cdd_startup_controls/expert-mode"

# ===================================================================
# Fixture 3: main/cdd_startup_controls/guided-mode
# Config with startup_sequence: true, recommend_next_actions: true
# ===================================================================
echo "Creating: main/cdd_startup_controls/guided-mode"
set_config true true

# Add a TODO feature so the work plan has something to show
cat > features/todo_feature.md <<'FEAT'
# Feature: Todo Feature

> Label: "Todo Feature"
> Category: "Test"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A feature in TODO state for testing guided mode.

## 2. Requirements

### 2.1 Basic

- Implement something.

## 3. Scenarios

### Automated Scenarios

None.

### Manual Scenarios (Human Verification Required)

None.
FEAT

# Update CRITIC_REPORT to show Builder action items
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

commit_and_tag "main/cdd_startup_controls/guided-mode"

# ===================================================================
# Fixture 4: main/cdd_startup_controls/orient-only-mode
# Config with startup_sequence: true, recommend_next_actions: false
# ===================================================================
echo "Creating: main/cdd_startup_controls/orient-only-mode"
set_config true false
commit_and_tag "main/cdd_startup_controls/orient-only-mode"

# ===================================================================
# Fixture 5: main/pl_session_resume/builder-mid-feature
# Checkpoint file showing builder at protocol step 2
# ===================================================================
echo "Creating: main/pl_session_resume/builder-mid-feature"
set_config true true

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

commit_and_tag "main/pl_session_resume/builder-mid-feature"

# ===================================================================
# Fixture 6: main/pl_session_resume/qa-mid-verification
# Checkpoint file showing QA at scenario 6 of 8
# ===================================================================
echo "Creating: main/pl_session_resume/qa-mid-verification"

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

# QA config
set_config true true

commit_and_tag "main/pl_session_resume/qa-mid-verification"

# ===================================================================
# Fixture 7: main/pl_session_resume/full-reboot-no-launcher
# Checkpoint exists but simulates non-launcher start
# ===================================================================
echo "Creating: main/pl_session_resume/full-reboot-no-launcher"

# Keep the checkpoint from previous fixture
# The "no launcher" aspect is handled by the test runner
# NOT appending role-specific instructions to the system prompt

commit_and_tag "main/pl_session_resume/full-reboot-no-launcher"

# ===================================================================
# Fixture 8: main/pl_help/architect-main-branch
# Project on main branch, default config
# ===================================================================
echo "Creating: main/pl_help/architect-main-branch"

# Remove checkpoint (not relevant for help tests)
rm -f .purlin/cache/session_checkpoint.md
set_config true true

# Ensure we're on "main" (the fixture clone will be on the tag's detached HEAD,
# but the test runner can set the branch for the help variant detection)
commit_and_tag "main/pl_help/architect-main-branch"

# ===================================================================
# Fixture 9: main/pl_help/builder-collab-branch
# Project with active_branch file for builder collab variant
# ===================================================================
echo "Creating: main/pl_help/builder-collab-branch"

echo "collab/v2" > .purlin/runtime/active_branch
commit_and_tag "main/pl_help/builder-collab-branch"

# ===================================================================
# Fixture 10: main/pl_help/qa-collab-branch
# Project with active_branch file
# ===================================================================
echo "Creating: main/pl_help/qa-collab-branch"

echo "collab/v2" > .purlin/runtime/active_branch
commit_and_tag "main/pl_help/qa-collab-branch"

# --- Push everything to bare repo ---
echo ""
echo "Pushing to bare repo..."
git push origin --all >/dev/null 2>&1
git push origin --tags >/dev/null 2>&1

echo ""
echo "Fixture repo created at: $BARE_DIR"
echo ""
echo "Tags created:"
git tag | sort
echo ""
echo "Usage:"
echo "  ./dev/test_agent_behavior.sh --fixture-repo $BARE_DIR"
