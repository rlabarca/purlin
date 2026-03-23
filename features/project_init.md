# Feature: Unified Project Init

> Label: "Tool: Project Init"
> Category: "Install, Update & Scripts"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 6: Layered Instruction Architecture)

[TODO]

## 1. Overview

Provides a single, idempotent entry point for initializing and refreshing a consumer project that uses Purlin as a git submodule. The unified `init.sh` auto-detects project state and does the right thing — whether it is the first run or the hundredth.

The design uses a two-script architecture: a canonical `tools/init.sh` containing all logic, and a thin `pl-init.sh` shim at the project root that works even before the submodule is initialized.

---

## 2. Requirements

### 2.1 Script Location and Ergonomic Access

*   **Canonical Location:** `tools/init.sh` (executable, `chmod +x`).
*   **Submodule Root Symlink:** A symlink at `<submodule>/pl-init.sh` MUST point to `tools/init.sh` for ergonomic access (e.g., `purlin/pl-init.sh`). The `pl-` prefix follows the same naming convention used by consumer-facing symlinks.
*   **Project Root Detection:** The script MUST detect the consumer project root as the parent of the submodule directory. Detection MUST work when invoked from any working directory.
*   **Submodule Path:** The script MUST detect the submodule directory name dynamically from its own location.

### 2.2 Mode Detection

The script MUST auto-detect the current project state and select the appropriate mode:

*   **Full Init Mode:** Selected when `.purlin/` does NOT exist at the project root. Performs complete project initialization (Section 2.3).
*   **Refresh Mode:** Selected when `.purlin/` ALREADY exists at the project root. Performs incremental updates only (Section 2.4).

### 2.3 Full Init Mode

When `.purlin/` is missing, the script MUST perform all of the following in order:

1.  **Override Directory Initialization:** Copy all files from `purlin-config-sample/` (in the submodule root) to `<project_root>/.purlin/`.
2.  **Config Patching:** Set the `tools_root` value in the copied `config.json` to the correct relative path from the project root to the submodule's `tools/` directory (e.g., `purlin/tools`). MUST use precise `sed` that replaces only the value portion and validate with `python3 json.load()`.
3.  **Provider Detection:** Run `tools/detect-providers.sh` and merge available providers into config. For each provider reported as `available: true`, merge its `models` array into the installed config under `llm_providers.<provider>`. Non-blocking if the script fails or is missing.
4.  **Upstream SHA Recording:** Record the current submodule HEAD SHA to `.purlin/.upstream_sha` (40-character SHA, single line).
5.  **Launcher Script Generation:** Generate `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, and `pl-run-pm.sh` at the project root. Each launcher concatenates base + role instruction files with overrides and exports `PURLIN_PROJECT_ROOT`. All MUST be `chmod +x`.
6.  **Command File Distribution:** Copy `.claude/commands/pl-*.md` from the submodule to `<project_root>/.claude/commands/`. `pl-edit-base.md` MUST NEVER be copied. If a destination file is newer than the source (local modification), skip it.
6b. **Agent File Distribution:** Copy `.claude/agents/*.md` from the submodule to `<project_root>/.claude/agents/`. If the destination directory does not exist, create it. If a destination file is newer than the source (local modification), skip it. Same skip logic as command files.
7.  **Features Directory:** Create `features/` at the project root if it does not exist.
8.  **Gitignore Handling:** Warn if `.purlin` appears in `.gitignore`. Read `purlin-config-sample/gitignore.purlin` from the submodule and merge patterns into the consumer's `.gitignore`. For each non-comment, non-blank line in the template, append it if not already present.
9.  **Shim Generation:** Generate `pl-init.sh` at the project root (Section 2.5).
10. **CDD Convenience Symlinks:** Create symlinks at the project root (Section 2.6).
11. **Python Environment Suggestion:** If `.venv/` does not exist, print an optional venv setup suggestion. Informational and non-blocking.
12. **Claude Code Hook Installation:** Ensure `.claude/settings.json` contains the Purlin session-recovery hook (Section 2.15).
13. **MCP Server Installation:** Install required MCP servers from the framework manifest (Section 2.16).
14. **Post-Init Staging:** After all artifacts are created, the script MUST stage exactly the files it created or modified using explicit `git add` calls. The script MUST NOT suggest or use `git add -A` or `git add .`.
15. **Summary Output:** Print a concise summary (Section 2.7).

### 2.4 Refresh Mode

When `.purlin/` already exists, the script MUST perform only these updates:

1.  **Command File Refresh:** Copy/update `.claude/commands/pl-*.md` from the submodule to the project root. For each file:
    *   If the destination file does not exist: copy it.
    *   If the destination file exists AND is newer than the source (local modification): skip it.
    *   If the destination file exists AND is older than or same age as the source: overwrite it.
    *   `pl-edit-base.md` MUST NEVER be copied.
1b. **Agent File Refresh:** Copy/update `.claude/agents/*.md` from the submodule to `<project_root>/.claude/agents/`. Same skip logic as command files: skip locally modified (newer) files, overwrite older or same-age files. If the destination directory does not exist, create it.
2.  **Upstream SHA Update:** Update `.purlin/.upstream_sha` with the current submodule HEAD SHA.
3.  **Shim Self-Update:** If `pl-init.sh` at the project root is stale (the embedded SHA or version differs from the current submodule state), regenerate it (Section 2.5).
4.  **CDD Symlink Repair:** If either CDD convenience symlink is missing, recreate it (Section 2.6).
5.  **Launcher Regeneration:** Regenerate all launcher scripts (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) at the project root, overwriting any existing versions. Additionally, stale launchers from previous naming conventions (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) MUST be removed if they exist. Launchers are generated artifacts — not customization points — so always regenerating ensures they stay current with the latest template and config resolution logic.
6.  **Claude Code Hook Installation:** Ensure `.claude/settings.json` contains the Purlin session-recovery hook (Section 2.15).
7.  **Gitignore Pattern Sync:** Read `<submodule>/purlin-config-sample/gitignore.purlin`. For each pattern not already present in the consumer's `.gitignore`, append it under a `# Added by Purlin refresh` header. Never remove or modify existing entries.
8.  **MCP Server Installation:** Install required MCP servers from the framework manifest (Section 2.16).
9.  **Refresh Summary:** Print a concise summary (Section 2.8).

### 2.4.1 Refresh Mode Exclusions

Refresh mode MUST NEVER modify:

*   `.purlin/config.json` or `.purlin/config.local.json`
*   `.purlin/*_OVERRIDES.md`
*   `.purlin/release/` (any file)
*   `features/` directory

Note: `.gitignore` is governed by the additive-only rule in Section 2.4 Step 7 -- Purlin may append missing recommended patterns but MUST NOT remove or alter existing entries.

### 2.5 Project-Root Shim (`pl-init.sh`)

The script MUST generate a `pl-init.sh` file at the project root with the following properties:

*   **Executable:** Marked `chmod +x`.
*   **Header Metadata:** The file header MUST embed:
    *   The submodule's git remote URL (extracted from `.gitmodules` or `git remote get-url origin` within the submodule).
    *   The pinned SHA (current submodule HEAD, full 40-character SHA).
    *   The version tag (output of `git -C <submodule> describe --tags --abbrev=0 HEAD`, or `"untagged"` if no tag exists).
    *   The submodule path (e.g., `purlin`).
*   **Behavior:**
    1.  Determine script directory.
    2.  Check if the canonical `<submodule>/tools/init.sh` exists.
    3.  If not: run `git submodule update --init <submodule>` to initialize the submodule.
    4.  If the canonical script now exists: `exec` it, forwarding all arguments.
    5.  If still missing after init attempt: print an error and exit with non-zero status.
*   **Self-Contained:** The shim MUST work without the submodule being initialized (that is its primary purpose for collaborators doing fresh clones).
*   **Committed:** The shim is intended to be committed to the consumer project's repository.

### 2.6 CDD Convenience Symlinks

On both full init and refresh, the script MUST create these symlinks at the project root:

*   `pl-cdd-start.sh` -> `<submodule>/tools/cdd/start.sh`
*   `pl-cdd-stop.sh` -> `<submodule>/tools/cdd/stop.sh`

The symlinks MUST use relative paths (not absolute) so they remain valid after repository relocation. If a symlink already exists and points to the correct target, leave it unchanged. If it exists but points to the wrong target, replace it. If a **regular file** (not a symlink) exists at the target path, replace it with the correct symlink — this handles the case where a file was inadvertently copied instead of symlinked (e.g., by an update agent or manual copy).

### 2.7 Full Init Output

The full init summary MUST be concise — no verbose logs, just the essentials:

```
Purlin initialized. Files staged.

  pl-init.sh              Run anytime to refresh
  ./pl-run-architect.sh   Start Architect session
  ./pl-run-builder.sh     Start Builder session
  ./pl-run-qa.sh          Start QA session
  ./pl-run-pm.sh          Start PM session
  ./pl-cdd-start.sh       Start CDD dashboard
  ./pl-cdd-stop.sh        Stop CDD dashboard

Next: git commit -m "init purlin"
```

Provider detection results and command file counts MAY be included on additional lines if non-trivial (e.g., providers found, N commands copied).

### 2.8 Refresh Output

The refresh summary MUST be a single line when nothing special happened:

```
Purlin refreshed. (N commands updated, M skipped)
```

If CDD symlinks were repaired or the shim was updated, append a brief note.

### 2.9 CLI Flags

*   **`--quiet`:** Suppresses all non-error output. Intended for scripted use (e.g., called by `/pl-update-purlin`). Errors still print to stderr.

### 2.10 Idempotency

Running the script multiple times MUST produce the same result. Specifically:

*   Full init followed by another run MUST enter refresh mode (not fail or re-initialize).
*   Refresh mode followed by another refresh MUST produce no file changes (verified by `git diff` showing nothing new).
*   CDD symlinks, command files, and SHA marker MUST be stable across repeated runs when the submodule has not changed.

### 2.11 Integration with `/pl-update-purlin`

After a successful submodule update (step 10 in the `/pl-update-purlin` workflow: atomic update), the skill MUST run `tools/init.sh --quiet` to refresh commands, symlinks, shim, and SHA. This replaces the skill's manual post-update copy logic with the canonical refresh mechanism. The skill's step 7 (command file changes with three-way diff) remains for conflict resolution on modified files. The skill's step 12 summary MUST note that init/refresh ran.

### 2.12 Unit Test Script

A unit test script MUST exist at `tools/test_init.sh` (executable, `chmod +x`) that exercises core init scenarios in a simulated submodule sandbox. This script covers the fast, structural assertions listed under `### Unit Tests` in Section 3. Behavioral integration tests (refresh mode, idempotency, collaborator flow, hook merging, MCP installation) are QA-owned regression tests covered under `### QA Scenarios` in Section 3 and described in Section 2.17.

#### 2.12.1 Sandbox Architecture

*   **Temporary Directory:** The test creates a temporary directory acting as a consumer project root, with a git-initialized repo.
*   **Submodule Simulation:** A clone (or copy) of the current Purlin repository is placed inside the sandbox at a submodule-like path (e.g., `my-project/purlin/`). Any uncommitted tool/script changes MUST be overlaid onto the clone so tests exercise the latest code.
*   **Git Setup:** The sandbox repo MUST have the simulated submodule registered in `.gitmodules` and have an initial commit, so `git submodule` commands work correctly within the sandbox.
*   **Cleanup:** The test MUST clean up all temporary directories on exit via `trap`, even on test failure.

#### 2.12.2 Test Output Format

*   Each test prints: `PASS: <description>` or `FAIL: <description>` followed by diagnostic details on failure.
*   At the end, print a summary: `N/M tests passed`. Exit with non-zero status if any test failed.
*   Tests MUST run independently where possible -- a failure in one test MUST NOT prevent subsequent tests from running (use per-test `set +e` / `set -e` or subshell isolation).

### 2.13 Standalone Mode Guard

The script MUST detect when it is being run inside the standalone Purlin repo (where Purlin IS the project, not a submodule) and refuse to proceed.

*   **Detection:** After computing `PROJECT_ROOT` (the parent of `SUBMODULE_DIR`), check whether `$PROJECT_ROOT` is a git repository (e.g., `git -C "$PROJECT_ROOT" rev-parse --git-dir`). In a consumer project, the parent directory IS the consumer's git repo root. In standalone mode, the Purlin repo's parent is NOT a git repository, so the check fails. If `$PROJECT_ROOT` is not a git repository, print an error and exit non-zero.
*   **Error Message:** The error MUST be printed to stderr and explain that `init.sh` is for consumer projects only, not for the Purlin repository itself.
*   **No Side Effects:** The guard MUST fire before any file creation or modification. No files outside the Purlin repo may be created or modified.

### 2.15 Claude Code Session Recovery Hook

On both full init and refresh, the script MUST ensure that `.claude/settings.json` at the project root contains the Purlin session-recovery hook. This hook enables automatic context restoration after `/clear` by injecting a system reminder that instructs the agent to run `/pl-resume`.

**Hook definition (to be installed inside `hooks.SessionStart` array):**

```json
{
  "matcher": "clear",
  "hooks": [
    {
      "type": "command",
      "command": "echo 'IMPORTANT: Context was cleared. Run /pl-resume immediately to restore session context.'"
    }
  ]
}
```

**Merge strategy (idempotent):**

1.  If `.claude/settings.json` does not exist: create it with `{"hooks": {"SessionStart": [<hook>]}}`.
2.  If `.claude/settings.json` exists but has no `hooks` key: add the `hooks` key with the `SessionStart` array.
3.  If `hooks` exists but has no `SessionStart` key: add the `SessionStart` array containing the hook.
4.  If `hooks.SessionStart` exists but no entry has `"matcher": "clear"`: append the hook entry to the array.
5.  If an entry with `"matcher": "clear"` already exists: leave it unchanged.

**Constraints:**

*   MUST NOT modify or remove any existing hooks, settings, or configuration in the file.
*   MUST validate the result is valid JSON before writing.
*   The merge logic SHOULD be implemented in Python (consistent with `resolve_config.py` for JSON manipulation).

### 2.16 MCP Server Installation

On both full init and refresh, the script MUST install MCP servers declared in the framework's manifest. This provides automatic setup of required MCP integrations (e.g., Playwright, Figma) without manual `claude mcp add` commands.

**Manifest location:** `<submodule>/tools/mcp/manifest.json` (framework-owned, read-only to consumers).

**Manifest schema:**

```json
{
  "version": 1,
  "servers": [
    {
      "name": "string",
      "transport": "stdio | http",
      "command": "string (stdio only)",
      "args": ["string (stdio only)"],
      "url": "string (http only)",
      "post_install_notes": "string | null"
    }
  ]
}
```

**Required servers (initial manifest):**

| Name | Transport | Config | Notes |
|------|-----------|--------|-------|
| `playwright` | stdio | `command: "npx"`, `args: ["@playwright/mcp", "--headless"]` | None |
| `figma` | http | `url: "https://mcp.figma.com/mcp"` | OAuth. After restarting Claude Code, run /mcp, select figma, and complete browser authentication. |

**Installation behavior:**

1.  **CLI guard:** Check `command -v claude` first. If unavailable (CI, non-Claude users), skip MCP setup with an informational message. Never fail init.
2.  **Manifest guard:** If `<submodule>/tools/mcp/manifest.json` does not exist, skip MCP setup with an informational message. Never fail init.
3.  **Per-server processing:** For each server in the manifest:
    *   Check if already installed (skip if present).
    *   For `stdio` transport: `claude mcp add <name> <command> <args...>`
    *   For `http` transport: `claude mcp add --transport http <name> <url>`
    *   If installation fails, report the error and continue to next server. Individual failures are non-fatal.
4.  **Idempotent:** Running multiple times installs zero servers on subsequent runs if all are already present.
5.  **Quiet mode:** When `--quiet` is active, MCP output is suppressed.
6.  **Summary output:** After the existing init summary, append an MCP section showing:
    *   Installed count and skipped count (e.g., "MCP servers: 2 installed, 0 skipped")
    *   Any `post_install_notes` for newly installed servers
    *   A restart notice if any server was installed: "Restart Claude Code to load MCP servers."

### 2.14 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/project_init/fresh-directory` | Empty project directory with no .purlin or purlin submodule |
| `main/project_init/partially-initialized` | Project directory with .purlin directory but incomplete initialization (missing override files) |

### 2.17 Regression Testing

The init/refresh behavioral integration tests are QA-owned regression tests. The regression approach uses the sandbox architecture (Section 2.12.1) to simulate consumer project environments, exercising multi-step workflows: init followed by state manipulation followed by refresh.

*   **Scenarios covered:** All `### QA Scenarios` in Section 3, including refresh mode behavior, idempotency verification, hook merge strategy, MCP installation, collaborator fresh-clone flow, and gitignore sync.
*   **Harness type:** `custom_script` -- the sandbox-based test approach does not map to `agent_behavior` or `web_test` harness types. QA authors a custom regression script that reuses the sandbox architecture from Section 2.12.1.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Full Init Creates All Artifacts

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then .purlin/ is created with config.json, all override templates, and .upstream_sha
    And config.json contains the correct tools_root for the submodule path
    And config.json is valid JSON (parseable by python3 json.load)
    And pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh, pl-run-pm.sh exist at the project root and are executable
    And .claude/commands/ contains pl-*.md files from the submodule (excluding pl-edit-base.md)
    And features/ directory exists at the project root
    And pl-init.sh exists at the project root and is executable

#### Scenario: Full Init Creates CDD Convenience Symlinks

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then pl-cdd-start.sh exists at the project root as a symlink to purlin/tools/cdd/start.sh
    And pl-cdd-stop.sh exists at the project root as a symlink to purlin/tools/cdd/stop.sh
    And both symlinks use relative paths

#### Scenario: Shim Contains Repo URL, SHA, and Version

    Given Purlin is added as a submodule at "purlin/"
    And the submodule remote URL is "https://github.com/rlabarca/purlin.git"
    And the submodule HEAD is at SHA "abc1234..." with tag "v0.9.0"
    When the user runs "purlin/tools/init.sh"
    Then pl-init.sh contains the remote URL in its header comments
    And pl-init.sh contains the SHA in its header comments
    And pl-init.sh contains "v0.9.0" in its header comments

#### Scenario: Full Init Copies Agent Files

    Given Purlin is added as a submodule at "purlin/"
    And the submodule has .claude/agents/builder-worker.md and verification-runner.md
    When the user runs "purlin/tools/init.sh"
    Then .claude/agents/ exists at the project root
    And .claude/agents/builder-worker.md is copied from the submodule
    And .claude/agents/verification-runner.md is copied from the submodule

#### Scenario: Full Init Stages Only Created Files

    Given Purlin is added as a submodule at "purlin/"
    And the project root contains pre-existing untracked files (e.g., src/app.py)
    When the user runs "purlin/tools/init.sh"
    Then only Purlin-created files are staged (git add)
    And pre-existing untracked files are NOT staged
    And the summary suggests "git commit" without "git add -A"

#### Scenario: Full Init Installs Complete Gitignore Patterns

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then .gitignore contains all patterns from purlin-config-sample/gitignore.purlin

#### Scenario: Full Init Installs Session Recovery Hook

    Given Purlin is added as a submodule at "purlin/"
    And no .claude/settings.json exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then .claude/settings.json exists and is valid JSON
    And it contains a SessionStart hook with matcher "clear"
    And the hook command echoes the pl-resume recovery instruction

#### Scenario: Standalone Mode Guard Prevents Init in Purlin Repo

    Given Purlin is the project (not a submodule)
    And the computed PROJECT_ROOT (parent of the script's directory) is not a git repository
    When the user runs "tools/init.sh"
    Then the script prints an error to stderr explaining init.sh is for consumer projects only
    And the script exits with non-zero status
    And no files are created or modified outside the Purlin repo

#### Scenario: Ergonomic Symlink at Submodule Root

    Given Purlin is the submodule at "purlin/"
    When the user inspects "purlin/pl-init.sh"
    Then it is a symlink pointing to "tools/init.sh"
    And running "purlin/pl-init.sh" behaves identically to running "purlin/tools/init.sh"

### QA Scenarios

#### Scenario: Shim Initializes Submodule on Fresh Clone

    Given a consumer project was cloned without --recurse-submodules
    And the submodule directory exists but is empty (not initialized)
    And pl-init.sh exists at the project root (previously committed)
    When the user runs "./pl-init.sh"
    Then git submodule update --init is run for the submodule
    And tools/init.sh is executed (delegated via exec)

#### Scenario: Refresh Mode Copies New and Updated Commands

    Given .purlin/ already exists at the project root
    And the submodule has a new command file pl-new-cmd.md in .claude/commands/
    And an existing command file pl-status.md in the submodule is newer than the project root copy
    When the user runs "purlin/tools/init.sh"
    Then pl-new-cmd.md is copied to <project_root>/.claude/commands/
    And pl-status.md is overwritten with the newer submodule version

#### Scenario: Refresh Mode Preserves Locally Modified Commands

    Given .purlin/ already exists at the project root
    And .claude/commands/pl-status.md at the project root has a modification timestamp newer than the submodule version
    When the user runs "purlin/tools/init.sh"
    Then pl-status.md is NOT overwritten
    And the refresh summary reports the skip

#### Scenario: Refresh Mode Excludes pl-edit-base.md

    Given .purlin/ already exists at the project root
    And the submodule has .claude/commands/pl-edit-base.md
    When the user runs "purlin/tools/init.sh"
    Then pl-edit-base.md is NOT copied to the project root
    And pl-edit-base.md does not appear in any counts or reports

#### Scenario: Refresh Mode Updates Upstream SHA

    Given .purlin/ already exists at the project root
    And .purlin/.upstream_sha contains an older SHA
    When the user runs "purlin/tools/init.sh"
    Then .purlin/.upstream_sha is updated to the current submodule HEAD SHA

#### Scenario: Shim Self-Update on Refresh

    Given .purlin/ already exists at the project root
    And pl-init.sh at the project root has an older pinned SHA than the current submodule HEAD
    When the user runs "purlin/tools/init.sh"
    Then pl-init.sh is regenerated with the current SHA and version

#### Scenario: Refresh Mode Never Touches Config or Overrides

    Given .purlin/ already exists at the project root
    And .purlin/config.json has been customized by the user
    And .purlin/ARCHITECT_OVERRIDES.md has custom content
    When the user runs "purlin/tools/init.sh"
    Then .purlin/config.json is unchanged
    And .purlin/ARCHITECT_OVERRIDES.md is unchanged
    And no file in .purlin/release/ is modified

#### Scenario: CDD Symlinks Created on Refresh if Missing

    Given .purlin/ already exists at the project root
    And pl-cdd-start.sh does NOT exist at the project root
    When the user runs "purlin/tools/init.sh"
    Then pl-cdd-start.sh is created as a symlink to purlin/tools/cdd/start.sh
    And pl-cdd-stop.sh is created as a symlink to purlin/tools/cdd/stop.sh

#### Scenario: CDD Regular File Replaced with Symlink on Refresh

    Given .purlin/ already exists at the project root
    And pl-cdd-start.sh exists at the project root as a regular file (not a symlink)
    When the user runs "purlin/tools/init.sh"
    Then pl-cdd-start.sh is replaced with a symlink to purlin/tools/cdd/start.sh
    And the symlink uses a relative path

#### Scenario: Launchers Always Regenerated on Refresh

    Given .purlin/ already exists at the project root
    And pl-run-architect.sh exists at the project root with outdated content
    When the user runs "purlin/tools/init.sh"
    Then pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh, pl-run-pm.sh are regenerated with current template content
    And all four launchers are executable

#### Scenario: Idempotent Repeated Runs

    Given Purlin is added as a submodule at "purlin/"
    And the user has already run "purlin/tools/init.sh" once (full init completed)
    When the user runs "purlin/tools/init.sh" a second time
    Then refresh mode is selected (not full init)
    And running git diff after the second run shows no changes

#### Scenario: Refresh Removes Stale Launchers

    Given .purlin/ already exists at the project root
    And stale launcher scripts run_architect.sh, run_builder.sh, run_qa.sh exist at the project root
    When the user runs "purlin/tools/init.sh"
    Then run_architect.sh, run_builder.sh, run_qa.sh are removed
    And only pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh exist as launchers

#### Scenario: --quiet Flag Suppresses Output

    Given .purlin/ already exists at the project root
    When the user runs "purlin/tools/init.sh --quiet"
    Then no output is written to stdout
    And the refresh completes successfully

#### Scenario: Refresh Mode Copies New Agent Files

    Given .purlin/ already exists at the project root
    And the submodule has a new agent file builder-worker.md in .claude/agents/
    And no .claude/agents/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then .claude/agents/ is created at the project root
    And builder-worker.md is copied to .claude/agents/

#### Scenario: Refresh Mode Preserves Locally Modified Agent Files

    Given .purlin/ already exists at the project root
    And .claude/agents/builder-worker.md at the project root has been locally modified (newer timestamp)
    When the user runs "purlin/tools/init.sh"
    Then builder-worker.md is NOT overwritten

#### Scenario: Refresh Mode Appends New Gitignore Patterns

    Given .purlin/ already exists at the project root
    And .gitignore exists but does not contain "CRITIC_REPORT.md"
    And purlin-config-sample/gitignore.purlin contains "CRITIC_REPORT.md"
    When the user runs "purlin/tools/init.sh"
    Then .gitignore now contains "CRITIC_REPORT.md"
    And all pre-existing .gitignore entries are preserved unchanged

#### Scenario: Refresh Mode Does Not Duplicate Existing Patterns

    Given .purlin/ already exists at the project root
    And .gitignore already contains all patterns from purlin-config-sample/gitignore.purlin
    When the user runs "purlin/tools/init.sh"
    Then .gitignore is unchanged (no duplicate entries appended)

#### Scenario: Fresh Clone Collaborator Flow

    Given a sandbox consumer project has been initialized with Purlin (full init completed)
    And pl-init.sh has been committed to the repository
    And the sandbox is re-cloned without --recurse-submodules (simulating a collaborator fresh clone)
    When the collaborator runs "./pl-init.sh" in the re-cloned sandbox
    Then git submodule update --init is triggered for the submodule
    And .purlin/ exists with config.json and override templates
    And launcher scripts (pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh, pl-run-pm.sh) exist and are executable
    And .claude/commands/ contains pl-*.md files
    And CDD convenience symlinks exist
    And the collaborator environment matches a normal full init

#### Scenario: Hook Merges Into Existing Settings

    Given .purlin/ already exists at the project root
    And .claude/settings.json exists with custom hooks (e.g., a PostToolUse hook)
    When the user runs "purlin/tools/init.sh"
    Then .claude/settings.json contains the Purlin SessionStart clear hook
    And the pre-existing custom hook is unchanged

#### Scenario: Refresh Removes Stale PreToolUse Architect Hook

    Given .purlin/ already exists at the project root
    And .claude/settings.json contains a PreToolUse hook with the AGENT_ROLE architect check
    When the user runs "purlin/tools/init.sh" in refresh mode
    Then the PreToolUse architect hook entry is removed from .claude/settings.json
    And any other PreToolUse hooks the user added are preserved
    And the SessionStart hooks remain intact

#### Scenario: Hook Installation Is Idempotent

    Given .purlin/ already exists at the project root
    And .claude/settings.json already contains the Purlin SessionStart clear hook
    When the user runs "purlin/tools/init.sh"
    Then .claude/settings.json is unchanged (no duplicate entries)

#### Scenario: Full Init Installs MCP Servers from Manifest

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    And tools/mcp/manifest.json declares servers "playwright" and "figma"
    And the claude CLI is available on PATH
    When the user runs "purlin/tools/init.sh"
    Then both MCP servers are installed via claude mcp add
    And the summary includes installed count and post-install notes for figma
    And the summary includes "Restart Claude Code to load MCP servers."

#### Scenario: MCP Installation Is Idempotent

    Given Purlin is added as a submodule at "purlin/"
    And the user has already run "purlin/tools/init.sh" once (MCP servers installed)
    When the user runs "purlin/tools/init.sh" a second time
    Then zero MCP servers are installed (all skipped as already present)
    And the summary shows 0 installed, 2 skipped

#### Scenario: MCP Setup Skipped When Claude CLI Unavailable

    Given Purlin is added as a submodule at "purlin/"
    And the claude CLI is NOT available on PATH
    When the user runs "purlin/tools/init.sh"
    Then MCP server installation is skipped with an informational message
    And init completes successfully (non-zero exit is NOT produced)

#### Scenario: MCP Setup Skipped When Manifest Missing

    Given Purlin is added as a submodule at "purlin/"
    And tools/mcp/manifest.json does not exist in the submodule
    When the user runs "purlin/tools/init.sh"
    Then MCP server installation is skipped with an informational message
    And init completes successfully

#### Scenario: Refresh Mode Installs Missing MCP Servers

    Given .purlin/ already exists at the project root
    And the submodule manifest declares server "playwright"
    And "playwright" is not currently installed as an MCP server
    When the user runs "purlin/tools/init.sh"
    Then "playwright" is installed via claude mcp add
    And the refresh summary includes MCP installation results
