#!/usr/bin/env bash
# dev/setup_version_fixtures.sh
#
# Creates deterministic consumer project snapshots for each Purlin version era,
# tagged in the fixture repository. Used to test purlin:update version detection
# and migration paths.
#
# Creates 7 fixture tags:
#   main/purlin_update/submodule-v0-7-x
#   main/purlin_update/submodule-v0-8-0-v0-8-3
#   main/purlin_update/submodule-v0-8-4
#   main/purlin_update/submodule-v0-8-4-partial
#   main/purlin_update/submodule-v0-8-5
#   main/purlin_update/plugin-v0-9-0
#   main/purlin_update/fresh-project
#
# Usage:
#   ./dev/setup_version_fixtures.sh [--no-push] [--force]
#
# Options:
#   --no-push    Don't auto-push tags to remote fixture repo
#   --force      Overwrite existing tags
#
# Prerequisites:
#   - Fixture repo must be initialized (run purlin:fixture init first)
#
# Classification: Purlin-dev-specific (dev/, not consumer-facing).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FIXTURE_TOOL="$PROJECT_ROOT/scripts/test_support/fixture.sh"
WORK_DIR=""
NO_PUSH=false
FORCE=false

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-push) NO_PUSH=true; shift ;;
        --force) FORCE=true; shift ;;
        --help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

cleanup() {
    if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

WORK_DIR="$(mktemp -d -t purlin-version-fixtures-XXXXXX)"

echo "━━━ setup_version_fixtures ━━━━━━━━━━━━━"
echo "Work dir: $WORK_DIR"
echo ""

# --- Shared consumer content ---

write_consumer_features() {
    local dir="$1"
    mkdir -p "$dir/features" "$dir/tests"

    cat > "$dir/features/user_auth.md" <<'SPEC'
# Feature: User Authentication

> Label: "User Authentication"
> Category: "Core"

[TODO]

## 1. Overview

Handles user login, logout, and session management.

## 2. Requirements

### 2.1 Login

- Users can log in with email and password.
SPEC

    cat > "$dir/features/dashboard.md" <<'SPEC'
# Feature: Dashboard

> Label: "Dashboard"
> Category: "UI"
> Prerequisite: features/user_auth.md

[TODO]

## 1. Overview

Main dashboard view showing user metrics.
SPEC
}

write_purlin_overrides() {
    local dir="$1"
    cat > "$dir/.purlin/PURLIN_OVERRIDES.md" <<'OVERRIDES'
# Project Overrides

## General (all modes)

This is a consumer project using Purlin for spec-driven development.

## Engineer Mode

Use Jest for unit tests.
OVERRIDES
}

# Build fixture tag flags
tag_flags=()
[[ "$NO_PUSH" == true ]] && tag_flags+=(--no-push)
[[ "$FORCE" == true ]] && tag_flags+=(--force)

# ==================================================================
# Fixture 1: submodule-v0.7.x
# Era: pre-unified-legacy
# Signal: agents.architect with startup_sequence
# ==================================================================
echo "[1/7] Creating submodule-v0.7.x fixture..."

FIX1="$WORK_DIR/submodule-v07x"
mkdir -p "$FIX1/.purlin/cache" "$FIX1/.claude/commands" "$FIX1/.claude/agents"

write_consumer_features "$FIX1"
write_purlin_overrides "$FIX1"

# .gitmodules with purlin submodule
cat > "$FIX1/.gitmodules" <<'GM'
[submodule "purlin"]
	path = purlin
	url = git@github.com:rlabarca/purlin.git
GM

# v0.7.x config: agents.architect with startup_sequence
cat > "$FIX1/.purlin/config.json" <<'CONFIG'
{
    "tools_root": "purlin/tools",
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "context_window_tokens": 200000}
    ],
    "agents": {
        "architect": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "startup_sequence": ["scan", "status", "suggest_mode"]
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "find_work": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "find_work": true
        }
    }
}
CONFIG

echo "abc123" > "$FIX1/.purlin/.upstream_sha"

# v0.7.x had role-specific launchers at project root
for role in architect builder qa; do
    cat > "$FIX1/run_${role}.sh" <<LAUNCHER
#!/usr/bin/env bash
# Legacy v0.7.x launcher for $role
echo "Starting $role agent..."
LAUNCHER
    chmod +x "$FIX1/run_${role}.sh"
done

# Old-style command files
for cmd in build verify spec status; do
    echo "# /pl-${cmd}" > "$FIX1/.claude/commands/pl-${cmd}.md"
done

cat > "$FIX1/CLAUDE.md" <<'CM'
# My Project

This project uses the Purlin submodule.

## Agents

Run `run_architect.sh` to start the architect agent.
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/submodule-v0-7-x" \
    --from-dir "$FIX1" --message "v0.7.x submodule consumer" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Fixture 2: submodule-v0.8.0-v0.8.3
# Era: pre-unified-modern
# Signal: agents.architect with find_work, no agents.pm
# ==================================================================
echo "[2/7] Creating submodule-v0.8.0-v0.8.3 fixture..."

FIX2="$WORK_DIR/submodule-v080"
mkdir -p "$FIX2/.purlin/cache" "$FIX2/.claude/commands" "$FIX2/.claude/agents"

write_consumer_features "$FIX2"
write_purlin_overrides "$FIX2"

cat > "$FIX2/.gitmodules" <<'GM'
[submodule "purlin"]
	path = purlin
	url = git@github.com:rlabarca/purlin.git
GM

# v0.8.0-v0.8.3: agents.architect with find_work, no pm
cat > "$FIX2/.purlin/config.json" <<'CONFIG'
{
    "tools_root": "purlin/tools",
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "context_window_tokens": 200000}
    ],
    "agents": {
        "architect": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": false,
            "auto_start": false
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": true
        }
    }
}
CONFIG

echo "def456" > "$FIX2/.purlin/.upstream_sha"

# v0.8.x had pl-run-*.sh launchers
for role in architect builder qa; do
    cat > "$FIX2/pl-run-${role}.sh" <<LAUNCHER
#!/usr/bin/env bash
# v0.8.x launcher for $role
echo "Starting $role..."
LAUNCHER
    chmod +x "$FIX2/pl-run-${role}.sh"
done

# pl-cdd scripts (v0.8.0-era feature)
for cmd in start stop; do
    cat > "$FIX2/pl-cdd-${cmd}.sh" <<SCRIPT
#!/usr/bin/env bash
echo "CDD ${cmd}"
SCRIPT
    chmod +x "$FIX2/pl-cdd-${cmd}.sh"
done

for cmd in build verify spec status mode help; do
    echo "# /pl-${cmd}" > "$FIX2/.claude/commands/pl-${cmd}.md"
done

cat > "$FIX2/CLAUDE.md" <<'CM'
# My Project

This project uses the Purlin submodule for spec-driven development.
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/submodule-v0-8-0-v0-8-3" \
    --from-dir "$FIX2" --message "v0.8.0-v0.8.3 submodule consumer" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Fixture 3: submodule-v0.8.4
# Era: pre-unified-with-pm
# Signal: agents.pm exists, no agents.purlin
# ==================================================================
echo "[3/7] Creating submodule-v0.8.4 fixture..."

FIX3="$WORK_DIR/submodule-v084"
mkdir -p "$FIX3/.purlin/cache" "$FIX3/.claude/commands" "$FIX3/.claude/agents"

write_consumer_features "$FIX3"
write_purlin_overrides "$FIX3"

cat > "$FIX3/.gitmodules" <<'GM'
[submodule "purlin"]
	path = purlin
	url = git@github.com:rlabarca/purlin.git
GM

# v0.8.4: agents.pm exists, no agents.purlin
cat > "$FIX3/.purlin/config.json" <<'CONFIG'
{
    "tools_root": "purlin/tools",
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "context_window_tokens": 200000}
    ],
    "agents": {
        "architect": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": false,
            "auto_start": false
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": true
        },
        "pm": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": false,
            "auto_start": false
        }
    }
}
CONFIG

echo "ghi789" > "$FIX3/.purlin/.upstream_sha"

# v0.8.4 had 4 role launchers
for role in architect builder qa pm; do
    cat > "$FIX3/pl-run-${role}.sh" <<LAUNCHER
#!/usr/bin/env bash
echo "Starting $role..."
LAUNCHER
    chmod +x "$FIX3/pl-run-${role}.sh"
done

for cmd in build verify spec status mode help complete discovery; do
    echo "# /pl-${cmd}" > "$FIX3/.claude/commands/pl-${cmd}.md"
done

cat > "$FIX3/CLAUDE.md" <<'CM'
# My Project

This project uses the Purlin submodule for spec-driven development.

## Agents

- **Architect**: Design and planning
- **Builder**: Implementation
- **QA**: Verification
- **PM**: Feature specs
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/submodule-v0-8-4" \
    --from-dir "$FIX3" --message "v0.8.4 submodule consumer" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Fixture 4: submodule-v0.8.4-partial
# Era: unified-partial
# Signal: agents.purlin with only model+effort, agents.builder still present
# ==================================================================
echo "[4/7] Creating submodule-v0.8.4-partial fixture..."

FIX4="$WORK_DIR/submodule-v084-partial"
mkdir -p "$FIX4/.purlin/cache" "$FIX4/.claude/commands" "$FIX4/.claude/agents"

write_consumer_features "$FIX4"
write_purlin_overrides "$FIX4"

cat > "$FIX4/.gitmodules" <<'GM'
[submodule "purlin"]
	path = purlin
	url = git@github.com:rlabarca/purlin.git
GM

# Partial: agents.purlin has only model+effort, builder still present
cat > "$FIX4/.purlin/config.json" <<'CONFIG'
{
    "tools_root": "purlin/tools",
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6",
            "effort": "high"
        },
        "builder": {
            "model": "claude-opus-4-6",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true
        },
        "qa": {
            "model": "claude-sonnet-4-6",
            "effort": "medium"
        }
    }
}
CONFIG

echo "jkl012" > "$FIX4/.purlin/.upstream_sha"

cat > "$FIX4/pl-run.sh" <<'LAUNCHER'
#!/usr/bin/env bash
echo "Purlin launcher (partial migration state)"
LAUNCHER
chmod +x "$FIX4/pl-run.sh"

for cmd in build verify spec status mode help; do
    echo "# /pl-${cmd}" > "$FIX4/.claude/commands/pl-${cmd}.md"
done

cat > "$FIX4/CLAUDE.md" <<'CM'
# My Project

This project uses the Purlin submodule for spec-driven development.
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/submodule-v0-8-4-partial" \
    --from-dir "$FIX4" --message "v0.8.4 partial migration" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Fixture 5: submodule-v0.8.5
# Era: unified
# Signal: agents.purlin complete, _migration_version: 1
# ==================================================================
echo "[5/7] Creating submodule-v0.8.5 fixture..."

FIX5="$WORK_DIR/submodule-v085"
mkdir -p "$FIX5/.purlin/cache" "$FIX5/.claude/commands" "$FIX5/.claude/agents"

write_consumer_features "$FIX5"
write_purlin_overrides "$FIX5"

cat > "$FIX5/.gitmodules" <<'GM'
[submodule "purlin"]
	path = purlin
	url = git@github.com:rlabarca/purlin.git
GM

# v0.8.5: unified agent, _migration_version: 1
cat > "$FIX5/.purlin/config.json" <<'CONFIG'
{
    "tools_root": "purlin/tools",
    "models": [
        {"id": "claude-opus-4-6", "label": "Opus 4.6", "context_window_tokens": 200000}
    ],
    "_migration_version": 1,
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6[1m]",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false,
            "default_mode": null
        }
    },
    "acknowledged_warnings": ["claude-opus-4-6[1m]"]
}
CONFIG

echo "mno345" > "$FIX5/.purlin/.upstream_sha"

# v0.8.5 had a single unified launcher
cat > "$FIX5/pl-run.sh" <<'LAUNCHER'
#!/usr/bin/env bash
echo "Purlin Session Launcher v0.8.5"
LAUNCHER
chmod +x "$FIX5/pl-run.sh"

# Unified agent + worker
cat > "$FIX5/.claude/agents/purlin.md" <<'AGENT'
---
name: purlin
description: Purlin unified workflow agent
model: claude-opus-4-6[1m]
---

# Purlin Agent (installed by pl-init.sh)
AGENT

cat > "$FIX5/.claude/agents/engineer-worker.md" <<'AGENT'
---
name: engineer-worker
description: Parallel feature builder
tools: Read, Write, Edit, Bash, Glob, Grep
isolation: worktree
---

# Engineer Worker
AGENT

for cmd in build verify spec status mode help complete discovery; do
    echo "# /pl-${cmd}" > "$FIX5/.claude/commands/pl-${cmd}.md"
done

cat > "$FIX5/.claude/settings.json" <<'SETTINGS'
{
    "hooks": {
        "SessionStart": [{"hooks": [{"type": "command", "command": "bash purlin/tools/hooks/session-start.sh"}]}],
        "SessionEnd": [{"hooks": [{"type": "command", "command": "bash purlin/tools/hooks/merge-worktrees.sh"}]}]
    },
    "permissions": {"allow": ["Bash(git *)"], "deny": []}
}
SETTINGS

cat > "$FIX5/CLAUDE.md" <<'CM'
# My Project

This project uses the Purlin submodule for spec-driven development.

## Purlin Agent (Unified)

- **Engineer mode**: Code, tests, scripts, arch anchors, companions.
- **PM mode**: Feature specs, design/policy anchors.
- **QA mode**: Discovery sidecars, QA tags, regression JSON.

## Context Recovery

If context is cleared, run `purlin:resume` to restore.
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/submodule-v0-8-5" \
    --from-dir "$FIX5" --message "v0.8.5 submodule consumer" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Fixture 6: plugin-v0.9.0
# Era: plugin
# Signal: enabledPlugins in settings.json, _migration_version: 2
# ==================================================================
echo "[6/7] Creating plugin-v0.9.0 fixture..."

FIX6="$WORK_DIR/plugin-v090"
mkdir -p "$FIX6/.purlin/cache" "$FIX6/.claude"

write_consumer_features "$FIX6"
write_purlin_overrides "$FIX6"

# Plugin model: no submodule, no .gitmodules
cat > "$FIX6/.purlin/config.json" <<'CONFIG'
{
    "_migration_version": 2,
    "agents": {
        "purlin": {
            "model": "claude-opus-4-6[1m]",
            "effort": "high",
            "bypass_permissions": true,
            "find_work": true,
            "auto_start": false,
            "default_mode": null
        }
    },
    "acknowledged_warnings": ["claude-opus-4-6[1m]"]
}
CONFIG

cat > "$FIX6/.claude/settings.json" <<'SETTINGS'
{
    "enabledPlugins": {"purlin@purlin": true},
    "extraKnownMarketplaces": {
        "purlin": {
            "source": "settings",
            "plugins": [{"name": "purlin", "source": {"source": "github", "repo": "rlabarca/purlin"}}]
        }
    },
    "permissions": {"allow": ["Bash(git *)"], "deny": []}
}
SETTINGS

cat > "$FIX6/CLAUDE.md" <<'CM'
# My Project

This project uses the Purlin plugin for spec-driven development.

## Purlin Agent (Unified)

- **Engineer mode**: Code, tests, scripts, arch anchors, companions.
- **PM mode**: Feature specs, design/policy anchors.
- **QA mode**: Discovery sidecars, QA tags, regression JSON.

## Context Recovery

If context is cleared, run `purlin:resume` to restore.
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/plugin-v0-9-0" \
    --from-dir "$FIX6" --message "v0.9.0 plugin consumer" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Fixture 7: fresh-project
# Era: none (fresh)
# Signal: .purlin/ exists, no submodule, no plugin
# ==================================================================
echo "[7/7] Creating fresh-project fixture..."

FIX7="$WORK_DIR/fresh-project"
mkdir -p "$FIX7/.purlin/cache"

write_consumer_features "$FIX7"

# Minimal config — no migration_version, no agents
cat > "$FIX7/.purlin/config.json" <<'CONFIG'
{
    "fixture_repo_url": "git@github.com:org/fixtures.git"
}
CONFIG

cat > "$FIX7/CLAUDE.md" <<'CM'
# My Project

New project, not yet configured for Purlin.
CM

bash "$FIXTURE_TOOL" add-tag "main/purlin_update/fresh-project" \
    --from-dir "$FIX7" --message "Fresh project, no version markers" "${tag_flags[@]+"${tag_flags[@]}"}"

# ==================================================================
# Summary
# ==================================================================
echo ""
echo "━━━ 7 fixtures created ━━━━━━━━━━━━━━━━"
echo "  ✓ main/purlin_update/submodule-v0-7-x"
echo "  ✓ main/purlin_update/submodule-v0-8-0-v0-8-3"
echo "  ✓ main/purlin_update/submodule-v0-8-4"
echo "  ✓ main/purlin_update/submodule-v0-8-4-partial"
echo "  ✓ main/purlin_update/submodule-v0-8-5"
echo "  ✓ main/purlin_update/plugin-v0-9-0"
echo "  ✓ main/purlin_update/fresh-project"
echo ""
echo "Verify: bash $FIXTURE_TOOL list | grep purlin_update"
