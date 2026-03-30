# Feature: Plugin Architecture Migration

> Label: "Tool: Plugin Architecture Migration"
> Category: "Framework Core"
> Prerequisite: purlin_resume.md
> Prerequisite: purlin_scan_engine.md
> Prerequisite: purlin_instruction_architecture.md
> Prerequisite: submodule_command_path_resolution.md

## 1. Overview

Migrates Purlin from git submodule distribution to the Claude Code plugin system. The repo itself becomes the plugin -- no separate distribution repo. This eliminates the submodule onboarding friction (multi-step init, symlink management, path resolution), replaces the 504-line launcher with a `purlin:resume` skill, wraps the scan engine in a persistent MCP server, and enables mechanical mode guard enforcement via hooks.

The migration is phased (0-7). This spec covers Phases 0-2: plugin scaffold, skill migration, and MCP server + script migration. Phases 3-7 (hooks, references/templates/cleanup, integration testing, consumer upgrade, release) are covered by subsequent spec updates.

**Authoritative design source:** `PLUGIN_MIGRATION_ANALYSIS.md` at project root contains the full analysis, rationale, and file-by-file change manifest.

---

## 2. Requirements

### 2.1 Phase 0: Plugin Scaffold

Three files establish the plugin identity. No existing files are moved or deleted.

#### 2.1.1 Plugin Manifest

- `.claude-plugin/plugin.json` MUST exist as the plugin manifest.
- Required fields: `name` ("purlin"), `version` (start at "0.9.0"), `description`, `author`.
- The `userConfig` section MUST declare optional configuration keys: `figma_access_token` (for Figma MCP integration), `default_model` (model preference).
- The manifest MUST NOT declare dependencies on other plugins.

#### 2.1.2 Plugin Settings

- `settings.json` at repo root MUST contain `{ "agent": "purlin" }` to activate the main agent definition when the plugin is enabled.
- This file is distinct from `.claude/settings.json` (which is project-level). The plugin `settings.json` is plugin-level configuration.

#### 2.1.3 Main Agent Definition

- `agents/purlin.md` MUST contain the full Purlin agent system prompt (current content of `instructions/PURLIN_BASE.md`).
- The file MUST include YAML frontmatter with: `name: purlin`, `description`, `model: claude-opus-4-6[1m]`, `effort: high`.
- The agent body MUST update all internal references: `${TOOLS_ROOT}/` becomes `${CLAUDE_PLUGIN_ROOT}/scripts/`, `references/` becomes `${CLAUDE_PLUGIN_ROOT}/references/`, `/pl-*` skill references become `purlin:*`.
- During the transition period (Phases 0-2), the old `instructions/PURLIN_BASE.md` is NOT deleted. Both exist in parallel.

### 2.2 Phase 1: Skill Migration

All 36 existing skills move from `.claude/commands/pl-*.md` to `skills/<name>/SKILL.md`. Three new skills are created.

#### 2.2.1 Skill File Format

- Each skill MUST be at `skills/<name>/SKILL.md` where `<name>` is the command name without the `pl-` prefix (e.g., `pl-build.md` becomes `skills/build/SKILL.md`).
- Special case: `pl-update-purlin.md` becomes `skills/update/SKILL.md` (the `purlin` suffix is dropped since the plugin namespace provides context).
- Each SKILL.md MUST include YAML frontmatter with `name` and `description` fields. The `name` field is the skill's invocation name (e.g., `build`, `verify`). The user invokes it as `purlin:<name>`.

#### 2.2.2 Content Transforms

Four mechanical transforms MUST be applied to every migrated skill:

1. **Frontmatter addition:** Add YAML frontmatter block (`---` delimited) with `name` and `description` fields before the existing content.
2. **Cross-reference transform:** Replace all `/pl-<name>` skill references with `purlin:<name>` throughout the body. This includes inline references, usage examples, protocol steps, and cross-skill invocations.
3. **Script path transform:** Replace `${TOOLS_ROOT}/` with `${CLAUDE_PLUGIN_ROOT}/scripts/` in all script path references.
4. **Reference path transform:** Replace `references/` with `${CLAUDE_PLUGIN_ROOT}/references/` in all reference document paths.

These transforms MUST be applied consistently -- no skill should retain old-style references after migration.

#### 2.2.3 New Skills

Three new skills MUST be created:

- **`skills/resume/SKILL.md`** -- Session entry point replacing `pl-run.sh`. See `PLUGIN_MIGRATION_ANALYSIS.md` Section 12 for the full `purlin:resume` specification. Handles checkpoint recovery, mode activation, worktree entry, YOLO toggling, terminal identity, and session naming.
- **`skills/init/SKILL.md`** -- Project initialization replacing `tools/init.sh`. Creates `.purlin/` directory structure, writes initial config, copies override template. Simplified from the 808-line init script because plugin paths eliminate submodule detection.
- **`skills/upgrade/SKILL.md`** -- Submodule-to-plugin migration for consumer projects. See `PLUGIN_MIGRATION_ANALYSIS.md` Section 14 for the full `purlin:upgrade` specification. Removes submodule, cleans stale artifacts, declares plugin, migrates config.

#### 2.2.4 Old File Deletion

- All 36 `.claude/commands/pl-*.md` files MUST be deleted after their content is migrated to `skills/`.
- The `.claude/commands/` directory MUST be empty after Phase 1 (it may still exist as a directory).

### 2.3 Phase 2: MCP Server and Script Migration

The scan engine and supporting scripts move from `tools/` to `scripts/` and the core CDD modules are refactored into importable Python modules wrapped by an MCP server.

#### 2.3.1 MCP Server

- `scripts/mcp/purlin_server.py` MUST implement an MCP stdio server using JSON-RPC protocol.
- The server MUST use ONLY Python stdlib (no external dependencies). All Purlin Python tools already meet this constraint.
- The server MUST expose these tools:

| MCP Tool | Purpose | Source Module |
|---|---|---|
| `purlin_scan` | Full project scan, returns structured JSON | `scan_engine.py` |
| `purlin_status` | Interpreted work items organized by mode | `scan_engine.py` |
| `purlin_graph` | Dependency graph with cycle detection | `graph_engine.py` |
| `purlin_classify` | File path classification (CODE/SPEC/QA/INVARIANT) | `config_engine.py` |
| `purlin_mode` | Get/set current operating mode | `config_engine.py` |
| `purlin_config` | Read/write `.purlin/config.json` | `config_engine.py` |

- The server MUST support in-memory caching of scan results to avoid re-computation on repeated calls within the same session.
- The server MUST handle graceful shutdown on SIGTERM/SIGINT.

#### 2.3.2 Refactored Modules

Existing scripts MUST be refactored from standalone scripts into importable Python modules:

- `tools/cdd/scan.py` (1100+ lines) becomes `scripts/mcp/scan_engine.py` -- refactored to expose a `run_scan()` function callable from the MCP server. Retains CLI interface for backward compatibility during transition.
- `tools/cdd/graph.py` becomes `scripts/mcp/graph_engine.py` -- same pattern.
- `tools/cdd/invariant.py` becomes `scripts/mcp/invariant_engine.py` -- same pattern.
- `tools/config/resolve_config.py` becomes `scripts/mcp/config_engine.py` -- simplified path resolution (no submodule climbing needed in plugin model). Also provides the `classify_file()` function for mode guard.
- `tools/bootstrap.py` becomes `scripts/mcp/bootstrap.py` -- remove submodule detection logic.

Each refactored module MUST:
- Be importable (expose functions, not just `if __name__ == '__main__'` blocks).
- Continue to work as standalone scripts (preserve CLI for transition).
- Use `PURLIN_PROJECT_ROOT` env var first, then simplified fallback (no submodule climbing).

#### 2.3.3 Script Directory Structure

Supporting scripts move from `tools/` to `scripts/`:

| Source | Destination | Notes |
|---|---|---|
| `tools/terminal/identity.sh` | `scripts/terminal/identity.sh` | Moved as-is |
| `tools/toolbox/resolve.py` | `scripts/toolbox/resolve.py` | Simplified paths |
| `tools/toolbox/manage.py` | `scripts/toolbox/manage.py` | Simplified paths |
| `tools/toolbox/community.py` | `scripts/toolbox/community.py` | Simplified paths |
| `tools/toolbox/purlin_tools.json` | `scripts/toolbox/purlin_tools.json` | Moved as-is |
| `tools/worktree/manage.sh` | `scripts/worktree/manage.sh` | Moved as-is |
| `tools/test_support/*` | `scripts/test_support/*` | Moved as-is |
| `tools/smoke/smoke.py` | `scripts/smoke/smoke.py` | Moved as-is |

#### 2.3.4 MCP Configuration

- `.mcp.json` MUST be updated to declare the Purlin MCP server:
  ```json
  {
    "mcpServers": {
      "purlin": {
        "command": "python3",
        "args": ["scripts/mcp/purlin_server.py"],
        "cwd": "${CLAUDE_PLUGIN_ROOT}"
      }
    }
  }
  ```
- Existing MCP server entries (Playwright, Figma) MUST be preserved if present.

#### 2.3.5 Old File Deletion

After migration, the following files MUST be deleted from `tools/`:
- `tools/cdd/scan.py`, `tools/cdd/graph.py`, `tools/cdd/invariant.py`, `tools/cdd/scan.sh`
- `tools/config/resolve_config.py`
- `tools/bootstrap.py`, `tools/resolve_python.sh`
- `tools/terminal/identity.sh`
- `tools/toolbox/*.py`, `tools/toolbox/purlin_tools.json`
- `tools/worktree/manage.sh`
- `tools/test_support/*`
- `tools/smoke/smoke.py`
- `tools/init.sh` (replaced by `purlin:init` skill)

Files NOT deleted in Phase 2 (handled in later phases):
- `tools/hooks/merge-worktrees.sh` (moved to `hooks/scripts/` in Phase 3)
- `tools/mcp/manifest.json`, `tools/feature_templates/` (moved in Phase 4)

### 2.4 Phase 3: Hook Implementation

Seven hook scripts provide mechanical enforcement and lifecycle automation that was previously prompt-level or launcher-managed.

#### 2.4.1 Hook Manifest

- `hooks/hooks.json` MUST declare all hook handlers with correct event types and script paths.
- Required hook events: `SessionStart`, `SessionEnd`, `PreToolUse`, `PermissionRequest`, `PreCompact`, `FileChanged`.

#### 2.4.2 Hook Scripts

| Script | Event | Purpose |
|---|---|---|
| `hooks/scripts/session-start.sh` | SessionStart (clear + compact) | Inject context reminder: "Purlin active, run purlin:resume" |
| `hooks/scripts/session-end-merge.sh` | SessionEnd | Merge worktrees, cleanup session state |
| `hooks/scripts/mode-guard.sh` | PreToolUse (Write/Edit/NotebookEdit) | Query MCP `purlin_classify`, block wrong-mode writes with exit code 2 |
| `hooks/scripts/permission-manager.sh` | PermissionRequest | Read YOLO flag from config, auto-approve if set |
| `hooks/scripts/pre-compact-checkpoint.sh` | PreCompact | Auto-save session checkpoint before context compaction |
| `hooks/scripts/companion-debt-tracker.sh` | FileChanged | Track companion file debt when code files change |

- `hooks/scripts/session-end-merge.sh` is adapted from `tools/hooks/merge-worktrees.sh` with updated paths for the plugin layout.
- `hooks/scripts/mode-guard.sh` MUST query the Purlin MCP server's `purlin_classify` tool to classify files. If the MCP server is unavailable, it MUST fall back to reading `references/file_classification.json` (machine-readable classification).
- All hook scripts MUST be executable (`chmod +x`).
- All hook scripts MUST exit 0 on success. `mode-guard.sh` MUST exit 2 to block forbidden writes.

#### 2.4.3 Machine-Readable File Classification

- `references/file_classification.json` MUST provide a JSON representation of file classification rules for the mode guard hook fallback.
- The JSON MUST contain pattern-to-classification mappings sufficient for the mode guard to enforce write boundaries without the MCP server.

#### 2.4.4 Old Hook Cleanup

- `.claude/settings.json` MUST have old SessionStart/SessionEnd hook entries removed (plugin hooks replace them).

### 2.5 Phase 4: References, Templates, Agent Defs, Cleanup

Final structural migration: move remaining files to plugin-standard locations and delete the old directory structure.

#### 2.5.1 Reference Documents

- All 15 files from `references/*.md` MUST be moved to `references/` at repo root.
- `instructions/PURLIN_BASE.md` MUST be deleted (content is now in `agents/purlin.md`).
- The `instructions/` directory MUST be deleted entirely after all contents are moved.

#### 2.5.2 Templates

- `purlin-config-sample/` contents MUST be moved to `templates/`:
  - `config.json` → `templates/config.json`
  - `PURLIN_OVERRIDES.md` → `templates/PURLIN_OVERRIDES.md`
  - `CLAUDE.md.purlin` → `templates/CLAUDE.md` (renamed)
  - `gitignore.purlin` → `templates/gitignore.purlin`
- The `purlin-config-sample/` directory MUST be deleted.

#### 2.5.3 Agent Definitions

- `.claude/agents/engineer-worker.md` and `.claude/agents/verification-runner.md` MUST be moved to `agents/` and updated with plugin-context paths.
- `.claude/agents/` directory MUST be empty after the move.
- `.claude/commands/` directory MUST be deleted (empty since Phase 1).

#### 2.5.4 Launcher and Old Structure Cleanup

- `pl-run.sh` MUST be deleted (replaced by `purlin:resume` skill).
- Remaining `tools/` contents MUST be moved to `scripts/` or deleted. Only `dev/`-specific test files may remain in the project (under `dev/` or `tests/`, not `tools/`).
- The `tools/` directory MUST be deleted or reduced to only `__pycache__` artifacts.

#### 2.5.5 Configuration Updates

- `CLAUDE.md` MUST be updated to reference the plugin model (remove submodule/launcher references).
- `.gitignore` MUST be updated: remove submodule entries, un-ignore `.mcp.json`, add plugin cache patterns.
- `.mcp.json` MUST be finalized with the purlin MCP server entry.

### 2.6 Transition Period Constraints

During the transition (Phases 0-4), both old and new structures coexist:

- The old `.claude/commands/` files are deleted after Phase 1 skill migration.
- The old `tools/` scripts are deleted after Phase 2 script migration.
- The old `instructions/PURLIN_BASE.md` stays until Phase 4 (when `agents/purlin.md` replaces it).
- `pl-run.sh` stays until Phase 4 (when `purlin:resume` fully replaces it).
- Consumer projects using the submodule model are unaffected until they run `purlin:upgrade` (Phase 6).

### 2.5 Naming Convention

- Plugin namespace: `purlin` (all skills invoked as `purlin:<name>`).
- Skill names drop the `pl-` prefix. The plugin namespace replaces it.
- Internal consistency: all cross-references within skills use `purlin:<name>` format.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Plugin manifest is valid

    Given .claude-plugin/plugin.json exists
    When parsed as JSON
    Then it contains name "purlin"
    And it contains a version field matching semver format
    And it contains a description field
    And it contains a userConfig section

#### Scenario: Plugin settings activate main agent

    Given settings.json exists at repo root
    When parsed as JSON
    Then it contains "agent": "purlin"

#### Scenario: Main agent definition has correct frontmatter

    Given agents/purlin.md exists
    When reading the YAML frontmatter
    Then name is "purlin"
    And model is "claude-opus-4-6[1m]"
    And effort is "high"

#### Scenario: Agent definition contains no stale path references

    Given agents/purlin.md exists
    When searching for "${TOOLS_ROOT}"
    Then zero matches are found
    When searching for "references/"
    Then zero matches are found
    When searching for "/pl-" followed by a command name
    Then zero matches are found (all references use "purlin:" prefix)

#### Scenario: All 36 skills migrated to SKILL.md format

    Given the skills/ directory exists
    When listing skills/*/SKILL.md files
    Then exactly 39 files exist (36 migrated + 3 new)

#### Scenario: Each skill has valid frontmatter

    Given any skills/<name>/SKILL.md file
    When reading the YAML frontmatter
    Then it contains a "name" field matching the directory name
    And it contains a "description" field

#### Scenario: No stale /pl- cross-references in skills

    Given all skills/*/SKILL.md files
    When searching for "/pl-" as a skill invocation pattern
    Then zero matches are found
    And all skill cross-references use "purlin:" prefix

#### Scenario: No stale TOOLS_ROOT references in skills

    Given all skills/*/SKILL.md files
    When searching for "${TOOLS_ROOT}"
    Then zero matches are found
    And all script paths use "${CLAUDE_PLUGIN_ROOT}/scripts/"

#### Scenario: No stale instruction reference paths in skills

    Given all skills/*/SKILL.md files
    When searching for "references/"
    Then zero matches are found
    And all reference paths use "${CLAUDE_PLUGIN_ROOT}/references/"

#### Scenario: New start skill exists with correct content

    Given skills/resume/SKILL.md exists
    When reading the content
    Then it describes session entry (checkpoint recovery, mode activation, worktree)
    And it references purlin:mode for mode switching
    And it references purlin:resume save for checkpoint save and purlin:resume merge-recovery for merge recovery

#### Scenario: New init skill exists

    Given skills/init/SKILL.md exists
    When reading the content
    Then it describes project initialization
    And it creates .purlin/ directory structure

#### Scenario: New upgrade skill exists

    Given skills/upgrade/SKILL.md exists
    When reading the content
    Then it describes submodule-to-plugin migration
    And it includes --dry-run support

#### Scenario: Old command files deleted

    Given Phase 1 is complete
    When listing .claude/commands/pl-*.md files
    Then zero files are found

#### Scenario: MCP server script exists

    Given scripts/mcp/purlin_server.py exists
    When checking the file
    Then it implements MCP stdio protocol
    And it imports scan_engine, graph_engine, invariant_engine, config_engine

#### Scenario: MCP server uses only stdlib

    Given scripts/mcp/purlin_server.py exists
    When checking import statements
    Then all imports are Python stdlib modules or local purlin modules
    And no pip-installed packages are imported

#### Scenario: Scan engine is importable

    Given scripts/mcp/scan_engine.py exists
    When importing the module
    Then run_scan() function is available
    And the module can still run as a CLI script

#### Scenario: MCP configuration declares purlin server

    Given .mcp.json exists
    When parsed as JSON
    Then mcpServers contains a "purlin" entry
    And the purlin entry points to scripts/mcp/purlin_server.py

#### Scenario: Old tools/ scripts deleted after Phase 2

    Given Phase 2 is complete
    When checking tools/cdd/scan.py
    Then the file does not exist
    When checking tools/config/resolve_config.py
    Then the file does not exist
    When checking tools/bootstrap.py
    Then the file does not exist

#### Scenario: Migrated scripts preserve functionality

    Given scripts/mcp/scan_engine.py exists
    When running as a CLI script with --help or standard arguments
    Then it produces the same output format as the original tools/cdd/scan.py

#### Scenario: Hook manifest declares all handlers

    Given hooks/hooks.json exists
    When parsed as JSON
    Then it declares handlers for SessionStart, SessionEnd, PreToolUse, PermissionRequest, PreCompact, and FileChanged

#### Scenario: All hook scripts exist and are executable

    Given hooks/scripts/ directory exists
    When listing all .sh files
    Then session-start.sh, session-end-merge.sh, mode-guard.sh, permission-manager.sh, pre-compact-checkpoint.sh, and companion-debt-tracker.sh all exist
    And all are executable

#### Scenario: Mode guard hook blocks wrong-mode writes

    Given mode-guard.sh is invoked with a SPEC file path
    And the current mode is "engineer"
    When the hook evaluates the write
    Then it exits with code 2 (blocking error)

#### Scenario: Machine-readable file classification exists

    Given references/file_classification.json exists
    When parsed as JSON
    Then it contains pattern-to-classification mappings
    And it classifies features/*.md as SPEC
    And it classifies features/i_*.md as INVARIANT
    And it classifies features/*.impl.md as CODE

#### Scenario: Old hooks removed from settings

    Given .claude/settings.json exists
    When checking for SessionStart/SessionEnd hook entries referencing old tools/ paths
    Then zero such entries are found

#### Scenario: All reference docs moved to references/

    Given references/ directory exists
    When listing *.md files
    Then at least 15 files exist (file_classification.md, active_deviations.md, commit_conventions.md, etc.)
    And references/ directory does not exist

#### Scenario: Templates moved from purlin-config-sample

    Given templates/ directory exists
    When listing contents
    Then config.json, PURLIN_OVERRIDES.md, CLAUDE.md, and gitignore.purlin exist
    And purlin-config-sample/ directory does not exist

#### Scenario: Agent definitions moved to agents/

    Given agents/ directory exists
    When listing *.md files
    Then purlin.md, engineer-worker.md, and verification-runner.md exist
    And .claude/agents/ directory is empty or does not exist

#### Scenario: Old launcher deleted

    Given Phase 4 is complete
    When checking for pl-run.sh at project root
    Then the file does not exist

#### Scenario: instructions/ directory is gone

    Given Phase 4 is complete
    When checking instructions/ directory
    Then the directory does not exist

#### Scenario: .gitignore updated for plugin model

    Given .gitignore exists
    When reading the file
    Then .mcp.json is NOT in the ignore list
    And .purlin/cache/ IS in the ignore list

### QA Scenarios

#### Scenario: Plugin validates with claude plugin validate @auto

    Given all Phase 0-2 files are in place
    When running claude plugin validate .
    Then validation passes with no errors

#### Scenario: Skills have consistent naming convention @auto

    Given the skills/ directory
    When listing all skill directory names
    Then no directory name starts with "pl-"
    And every directory name matches its SKILL.md frontmatter name field

#### Scenario: No orphaned old files remain @auto

    Given Phases 0-2 are complete
    When checking .claude/commands/ for pl-*.md files
    Then zero files are found
    When checking tools/cdd/ for scan.py, graph.py, invariant.py
    Then zero files are found
    When checking tools/config/ for resolve_config.py
    Then the file does not exist

#### Scenario: Cross-reference integrity across all skills @auto

    Given all skills/*/SKILL.md files
    When extracting all purlin:<name> cross-references
    Then every referenced skill name corresponds to an existing skills/<name>/SKILL.md file

#### Scenario: Complete old structure cleanup @auto

    Given Phases 0-4 are complete
    When checking the repository structure
    Then instructions/ directory does not exist
    And purlin-config-sample/ directory does not exist
    And .claude/commands/ directory is empty or does not exist
    And .claude/agents/ directory is empty or does not exist
    And pl-run.sh does not exist at project root
    And tools/ contains only __pycache__ and dev-only test files (if any)

#### Scenario: Hook scripts reference correct paths @auto

    Given hooks/scripts/*.sh files exist
    When searching for "tools/" path references
    Then zero matches are found (all paths use scripts/ or ${CLAUDE_PLUGIN_ROOT})

## Regression Guidance
- Verify skill frontmatter `name` field matches the directory name exactly
- Verify no skill content was lost during migration (diff old vs new for each skill)
- Verify MCP server handles malformed requests gracefully (returns JSON-RPC error, does not crash)
- Verify scan_engine.py produces identical JSON output to original scan.py for the same project state
- Verify .mcp.json remains valid JSON after purlin server entry is added
- Verify skills/update/SKILL.md correctly maps from pl-update-purlin.md (name change)
