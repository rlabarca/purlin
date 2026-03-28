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

echo "Setting up behavior test fixtures at: $OUTPUT_DIR" >&2

# Collect existing tags for idempotency check
EXISTING_TAGS=""
if [[ -d "$OUTPUT_DIR" ]]; then
    EXISTING_TAGS=$(git -C "$OUTPUT_DIR" tag 2>/dev/null || true)
fi

# Track created tags for stdout output
CREATED_TAGS=()

tag_exists() {
    # Check if a tag already exists in the repo
    local tag="$1"
    echo "$EXISTING_TAGS" | grep -qx "$tag" 2>/dev/null
}

# Create bare repo if it doesn't exist
BARE_DIR="$OUTPUT_DIR"
if [[ ! -d "$BARE_DIR" ]]; then
    git init --bare "$BARE_DIR" >/dev/null 2>&1
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

cd "$WORK_DIR"
git init >/dev/null 2>&1
git remote add origin "$BARE_DIR"
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Engineer"

# Seed the work dir from existing bare repo, or create initial commit
if git ls-remote --exit-code origin HEAD >/dev/null 2>&1; then
    git fetch origin >/dev/null 2>&1
    git fetch origin --tags >/dev/null 2>&1
    git checkout -b main origin/main >/dev/null 2>&1 || git checkout -b main >/dev/null 2>&1
else
    # Fresh bare repo — create initial commit
    echo "# Purlin Behavior Test Fixtures" > README.md
    git add README.md >/dev/null 2>&1
    git commit -m "initial" >/dev/null 2>&1
fi

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
    if [[ -d "$PROJECT_ROOT/references" ]]; then
        mkdir -p "references/"
        cp -r "$PROJECT_ROOT/references/"* "references/" 2>/dev/null || true
    fi

    # Copy override templates
    for f in HOW_WE_WORK_OVERRIDES.md BUILDER_OVERRIDES.md ARCHITECT_OVERRIDES.md QA_OVERRIDES.md; do
        if [[ -f "$PROJECT_ROOT/.purlin/$f" ]]; then
            cp "$PROJECT_ROOT/.purlin/$f" ".purlin/$f"
        else
            echo "# $f" > ".purlin/$f"
        fi
    done

    # Minimal feature file to find
    cat > features/sample_feature.md <<'FEAT'
# Feature: Sample Feature

> Label: "Sample Feature"
> Category: "Test"

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

    # Minimal dependency graph
    cat > .purlin/cache/dependency_graph.json <<'GRAPH'
{
  "cycles": [],
  "features": [
    {
      "category": "Test",
      "file": "features/sample_feature.md",
      "label": "Sample Feature",
      "prerequisites": []
    }
  ],
  "generated_at": "2026-01-01T00:00:00Z",
  "orphans": []
}
GRAPH
}

# --- Helper: set config ---
set_config() {
    local find_work="${1:-true}"
    local auto_start="${2:-false}"

    cat > .purlin/config.json <<CONFIG
{
    "tools_root": "tools",
    "agents": {
        "architect": {
            "model": "claude-haiku-4-5-20251001",
            "find_work": ${find_work},
            "auto_start": ${auto_start}
        },
        "builder": {
            "model": "claude-haiku-4-5-20251001",
            "find_work": ${find_work},
            "auto_start": ${auto_start}
        },
        "qa": {
            "model": "claude-haiku-4-5-20251001",
            "find_work": ${find_work},
            "auto_start": ${auto_start}
        }
    }
}
CONFIG
}

# --- Helper: commit and tag ---
commit_and_tag() {
    local tag="$1"
    local message="${2:-State for $tag}"

    if tag_exists "$tag"; then
        echo "  Skipping (already exists): $tag" >&2
        # Reset working tree for next fixture
        git checkout -- . >/dev/null 2>&1 || true
        git clean -fd >/dev/null 2>&1 || true
        return 0
    fi

    git add -A >/dev/null 2>&1
    git commit -m "$message" --allow-empty >/dev/null 2>&1
    git tag "$tag" >/dev/null 2>&1
    CREATED_TAGS+=("$tag")
}

# ===================================================================
# Fixture 1: main/pl_session_resume/builder-mid-feature
# Checkpoint file showing builder at protocol step 2
# ===================================================================
echo "Creating: main/pl_session_resume/builder-mid-feature" >&2
rm -rf ./* .purlin 2>/dev/null || true
create_base_project
set_config true true

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

commit_and_tag "main/pl_session_resume/builder-mid-feature"

# ===================================================================
# Fixture 2: main/pl_session_resume/qa-mid-verification
# Checkpoint file showing QA at scenario 6 of 8
# ===================================================================
echo "Creating: main/pl_session_resume/qa-mid-verification" >&2

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
# Fixture 3: main/pl_session_resume/full-reboot-no-launcher
# Checkpoint exists but simulates non-launcher start
# ===================================================================
echo "Creating: main/pl_session_resume/full-reboot-no-launcher" >&2

# Keep the checkpoint from previous fixture
# The "no launcher" aspect is handled by the test runner
# NOT appending role-specific instructions to the system prompt

commit_and_tag "main/pl_session_resume/full-reboot-no-launcher"

# ===================================================================
# Fixture 4: main/pl_help/architect-main-branch
# Project on main branch, default config
# ===================================================================
echo "Creating: main/pl_help/architect-main-branch" >&2

# Remove checkpoint (not relevant for help tests)
rm -f .purlin/cache/session_checkpoint.md
set_config true true

# Ensure we're on "main" (the fixture clone will be on the tag's detached HEAD,
# but the test runner can set the branch for the help variant detection)
commit_and_tag "main/pl_help/architect-main-branch"

# ===================================================================
# Fixture 5: main/pl_help/builder-collab-branch
# Project with active_branch file for builder collab variant
# ===================================================================
echo "Creating: main/pl_help/builder-collab-branch" >&2

echo "collab/v2" > .purlin/runtime/active_branch
commit_and_tag "main/pl_help/builder-collab-branch"

# ===================================================================
# Fixture 6: main/pl_help/qa-collab-branch
# Project with active_branch file
# ===================================================================
echo "Creating: main/pl_help/qa-collab-branch" >&2

echo "collab/v2" > .purlin/runtime/active_branch
commit_and_tag "main/pl_help/qa-collab-branch"

# --- Push everything to bare repo ---
if [[ ${#CREATED_TAGS[@]} -gt 0 ]]; then
    echo "Pushing to bare repo..." >&2
    git push origin --all >/dev/null 2>&1
    git push origin --tags >/dev/null 2>&1
else
    echo "No new tags created (all already exist)." >&2
fi

echo "" >&2
echo "Fixture repo at: $BARE_DIR" >&2
echo "Total tags: $(git -C "$BARE_DIR" tag 2>/dev/null | wc -l | tr -d ' ')" >&2

# Output created tag names to stdout (one per line) per 2.2.1 contract
for tag in "${CREATED_TAGS[@]}"; do
    echo "$tag"
done
