#!/usr/bin/env bash
# dev/setup_upgrade_fixture.sh
#
# Creates a test consumer project that uses Purlin as a git submodule.
# Used to test the purlin:upgrade skill (submodule -> plugin migration).
#
# The fixture creates a fully functional consumer project with:
#   - A real git submodule pointing to the local Purlin repo
#   - Feature specs, config, overrides (consumer-owned artifacts)
#   - Old-style .claude/commands/pl-*.md stubs (init-installed skills)
#   - Old-style .claude/agents/*.md stubs
#   - pl-run.sh launcher script
#   - .claude/settings.json with old submodule hooks
#   - .purlin/.upstream_sha version tracker
#
# Usage:
#   ./dev/setup_upgrade_fixture.sh [OUTPUT_DIR]
#
# Default output: /tmp/purlin-upgrade-fixture
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).
# Exempt from submodule safety checklist.

set -euo pipefail

if [[ "${1:-}" == "--help" ]]; then
    cat <<'HELP'
Usage: setup_upgrade_fixture.sh [OUTPUT_DIR]

Creates a test consumer project with Purlin as a git submodule,
ready for testing purlin:upgrade.

Arguments:
  OUTPUT_DIR    Where to create the fixture (default: /tmp/purlin-upgrade-fixture)

The fixture is a standalone git repo with committed state. You can
cd into it and run purlin:upgrade to test the migration.
HELP
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-/tmp/purlin-upgrade-fixture}"

echo "=== Purlin Upgrade Fixture Setup ==="
echo "Source: $PROJECT_ROOT"
echo "Output: $OUTPUT_DIR"
echo ""

# Clean previous
if [[ -d "$OUTPUT_DIR" ]]; then
    echo "Removing existing fixture..."
    rm -rf "$OUTPUT_DIR"
fi

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# =====================================================================
# Step 1: Init consumer project repo
# =====================================================================
echo "[1/8] Initializing consumer project repo..."

git init >/dev/null 2>&1
git config user.email "fixture@purlin.dev"
git config user.name "Purlin Fixture Engineer"

# =====================================================================
# Step 2: Add Purlin as a git submodule
# =====================================================================
echo "[2/8] Adding Purlin submodule..."

# Use the local repo as the submodule source.
# protocol.file.allow=always is needed for local file:// URLs in modern Git.
git -c protocol.file.allow=always submodule add "$PROJECT_ROOT" purlin >/dev/null 2>&1
git -C purlin checkout dev/0.8.6 >/dev/null 2>&1 || true

# =====================================================================
# Step 3: Create consumer project structure
# =====================================================================
echo "[3/8] Creating consumer project structure..."

mkdir -p features tests .purlin/runtime .purlin/cache

# Consumer feature specs
cat > features/user_auth.md <<'SPEC'
# Feature: User Authentication

> Label: "User Authentication"
> Category: "Core"

[TODO]

## 1. Overview

Handles user login, logout, and session management.

## 2. Requirements

### 2.1 Login

- Users can log in with email and password.
- Failed login attempts are rate-limited.

### 2.2 Session

- Sessions expire after 24 hours of inactivity.

## 3. Scenarios

### Unit Tests

#### Test: Login with valid credentials

    Given a registered user with email "test@example.com"
    When they submit valid credentials
    Then a session token is returned

### QA Scenarios

#### Scenario: Rate limiting

    Given a user has failed login 5 times
    When they attempt login again within 15 minutes
    Then the attempt is blocked with a rate limit message
SPEC

cat > features/dashboard.md <<'SPEC'
# Feature: Dashboard

> Label: "Dashboard"
> Category: "UI"
> Prerequisite: features/user_auth.md

[TODO]

## 1. Overview

Main dashboard view showing user metrics and recent activity.

## 2. Requirements

### 2.1 Layout

- Top navigation bar with user avatar and logout button.
- Left sidebar with navigation links.
- Main content area with metric cards.

## 3. Scenarios

### Unit Tests

#### Test: Dashboard loads metrics

    Given an authenticated user
    When they navigate to /dashboard
    Then metric cards display current data

### QA Scenarios

#### Scenario: Responsive layout

    Given a browser window at 768px width
    When the dashboard loads
    Then the sidebar collapses to a hamburger menu
SPEC

cat > features/api_endpoints.md <<'SPEC'
# Feature: API Endpoints

> Label: "REST API"
> Category: "Core"

[TESTING]

## 1. Overview

RESTful API for CRUD operations on user data.

## 2. Requirements

### 2.1 Endpoints

- GET /api/users — list users
- POST /api/users — create user
- GET /api/users/:id — get user
- PUT /api/users/:id — update user
- DELETE /api/users/:id — delete user

## 3. Scenarios

### Unit Tests

#### Test: List users returns paginated results

    Given 50 users exist in the database
    When GET /api/users?page=1&limit=10 is called
    Then 10 users are returned with pagination metadata
SPEC

# Companion file
cat > features/api_endpoints.impl.md <<'IMPL'
# API Endpoints — Companion File

[IMPL] Created Express router with all 5 CRUD endpoints.
[IMPL] Added Zod validation schemas for request bodies.
[DEVIATION] Used cursor-based pagination instead of offset-based. Reason: better performance with large datasets. PM review: pending.
IMPL

# =====================================================================
# Step 4: Create .purlin config (old submodule style)
# =====================================================================
echo "[4/8] Creating .purlin config..."

cat > .purlin/config.json <<'CONFIG'
{
    "tools_root": "purlin/tools",
    "models": [
        {
            "id": "claude-opus-4-6",
            "label": "Opus 4.6",
            "context_window_tokens": 200000
        },
        {
            "id": "claude-sonnet-4-6",
            "label": "Sonnet 4.6",
            "context_window_tokens": 200000
        }
    ],
    "agents": {
        "architect": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": false,
            "auto_start": false,
            "_deprecated": true
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": true,
            "_deprecated": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": true,
            "_deprecated": true
        },
        "pm": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": false,
            "auto_start": false,
            "_deprecated": true
        },
        "purlin": {
            "model": "claude-opus-4-6[1m]",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": false,
            "auto_start": false,
            "default_mode": null
        }
    },
    "acknowledged_warnings": ["claude-opus-4-6[1m]"]
}
CONFIG

cat > .purlin/PURLIN_OVERRIDES.md <<'OVERRIDES'
# Project Overrides

## General (all modes)

This is a consumer project using Purlin for spec-driven development.

## Engineer Mode

### Test Framework
Use Jest for unit tests, Playwright for E2E.

## PM Mode

### Design System
Use Tailwind CSS for styling. Component library: shadcn/ui.

## QA Mode

No project-specific QA overrides.
OVERRIDES

echo "abc123def" > .purlin/.upstream_sha

# =====================================================================
# Step 5: Create old-style .claude artifacts
# =====================================================================
echo "[5/8] Creating old .claude artifacts..."

mkdir -p .claude/commands .claude/agents

# Old skill files (stubs — init script installed these from the submodule)
for skill in build verify spec status mode resume help complete discovery; do
    cat > ".claude/commands/pl-${skill}.md" <<SKILL
# /pl-${skill}

> Path Resolution: See \`instructions/references/path_resolution.md\`.

This is an old-style skill file installed by pl-init.sh from the submodule.
SKILL
done

# Old agent definitions
cat > .claude/agents/purlin.md <<'AGENT'
---
name: purlin
description: Purlin unified workflow agent
model: claude-opus-4-6[1m]
---

# Purlin Agent (installed by pl-init.sh)

This agent definition was installed by the submodule init script.
AGENT

cat > .claude/agents/engineer-worker.md <<'AGENT'
---
name: engineer-worker
description: Parallel feature builder
tools: Read, Write, Edit, Bash, Glob, Grep
isolation: worktree
---

# Engineer Worker (installed by pl-init.sh)
AGENT

# Old settings.json with submodule hooks
cat > .claude/settings.json <<'SETTINGS'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "clear",
        "hooks": [
          {
            "type": "command",
            "command": "bash purlin/tools/hooks/session-start.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash purlin/tools/hooks/merge-worktrees.sh"
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": ["Bash(git *)"],
    "deny": []
  }
}
SETTINGS

# =====================================================================
# Step 6: Create pl-run.sh launcher
# =====================================================================
echo "[6/8] Creating pl-run.sh launcher..."

cat > pl-run.sh <<'LAUNCHER'
#!/usr/bin/env bash
# pl-run.sh — Purlin session launcher (submodule model)
#
# Usage: ./pl-run.sh [OPTIONS]
#
# This launcher orchestrates Purlin sessions using the git submodule
# distribution model. It is replaced by purlin:start in the plugin model.

set -euo pipefail

echo "Purlin Session Launcher v0.8.5"
echo "Submodule path: purlin/"

# ... (truncated for fixture purposes)
LAUNCHER
chmod +x pl-run.sh

# =====================================================================
# Step 7: Create CLAUDE.md and .gitignore
# =====================================================================
echo "[7/8] Creating CLAUDE.md and .gitignore..."

cat > CLAUDE.md <<'CLAUDEMD'
# My Consumer Project

This project uses the Purlin submodule for spec-driven development.

## Purlin Agent (Unified)

- **Engineer mode**: Code, tests, scripts, arch anchors, companions.
- **PM mode**: Feature specs, design/policy anchors.
- **QA mode**: Discovery sidecars, QA tags, regression JSON.

## Context Recovery

If context is cleared, run `/pl-resume` to restore.

## Project Overrides

See `.purlin/PURLIN_OVERRIDES.md` for project-specific rules.

## Commands

Run `/pl-help` for the full command reference.
CLAUDEMD

cat > .gitignore <<'GITIGNORE'
# Node
node_modules/
dist/

# Purlin (submodule model)
.purlin/cache/
.purlin/runtime/
.purlin_session.lock
.purlin_worktree_label

# OS
.DS_Store
GITIGNORE

# =====================================================================
# Step 8: Commit everything
# =====================================================================
echo "[8/8] Committing fixture state..."

git add -A >/dev/null 2>&1
git commit -m "Initial consumer project with Purlin submodule" >/dev/null 2>&1

echo ""
echo "=== Fixture Ready ==="
echo "Location: $OUTPUT_DIR"
echo ""
echo "Contents:"
echo "  features/      — 3 specs (user_auth, dashboard, api_endpoints) + 1 companion"
echo "  .purlin/       — config.json (old-style), PURLIN_OVERRIDES.md, .upstream_sha"
echo "  .claude/       — settings.json (old hooks), commands/pl-*.md (9), agents/*.md (2)"
echo "  purlin/        — git submodule (real)"
echo "  pl-run.sh      — old launcher"
echo "  CLAUDE.md      — submodule references"
echo "  .gitignore     — submodule entries"
echo ""
echo "To test upgrade:"
echo "  cd $OUTPUT_DIR"
echo "  claude --plugin-dir $PROJECT_ROOT"
echo "  # then run: purlin:upgrade"
echo ""
echo "Expected upgrade outcomes:"
echo "  ✓ purlin/ submodule removed"
echo "  ✓ pl-run.sh deleted"
echo "  ✓ .claude/commands/pl-*.md deleted"
echo "  ✓ .claude/agents/*.md deleted"
echo "  ✓ .purlin/.upstream_sha deleted"
echo "  ✓ .claude/settings.json: old hooks removed, plugin declared"
echo "  ✓ .purlin/config.json: tools_root removed, deprecated agents removed"
echo "  ✓ CLAUDE.md: updated for plugin model"
echo "  ✓ features/ preserved (3 specs + 1 companion, untouched)"
