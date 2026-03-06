# Feature: Unified Project Init

> Label: "Tool: Project Init"
> Category: "Install, Update & Scripts"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md (Section 6: Layered Instruction Architecture)
> Prerequisite: features/submodule_bootstrap.md

[TODO]

## 1. Overview

Provides a single, idempotent entry point for initializing and refreshing a consumer project that uses Purlin as a git submodule. Supersedes `bootstrap.sh` (which refuses re-runs and overwrites config if forced) with a unified `init.sh` that auto-detects project state and does the right thing — whether it is the first run or the hundredth.

The design uses a two-script architecture: a canonical `tools/init.sh` containing all logic, and a thin `purlin_init.sh` shim at the project root that works even before the submodule is initialized.

---

## 2. Requirements

### 2.1 Script Location and Ergonomic Access

*   **Canonical Location:** `tools/init.sh` (executable, `chmod +x`).
*   **Submodule Root Symlink:** A symlink at `<submodule>/init.sh` MUST point to `tools/init.sh` for ergonomic access (e.g., `purlin/init.sh`).
*   **Project Root Detection:** The script MUST detect the consumer project root as the parent of the submodule directory, using the same detection logic as `bootstrap.sh` (Section 2.1 of `submodule_bootstrap.md`). Detection MUST work when invoked from any working directory.
*   **Submodule Path:** The script MUST detect the submodule directory name dynamically from its own location.

### 2.2 Mode Detection

The script MUST auto-detect the current project state and select the appropriate mode:

*   **Full Init Mode:** Selected when `.purlin/` does NOT exist at the project root. Performs complete project initialization (Section 2.3).
*   **Refresh Mode:** Selected when `.purlin/` ALREADY exists at the project root. Performs incremental updates only (Section 2.4).

### 2.3 Full Init Mode

When `.purlin/` is missing, the script MUST perform all of the following in order:

1.  **Override Directory Initialization:** Copy all files from `purlin-config-sample/` (in the submodule root) to `<project_root>/.purlin/`.
2.  **Config Patching:** Set the `tools_root` value in the copied `config.json` to the correct relative path from the project root to the submodule's `tools/` directory (e.g., `purlin/tools`). MUST follow the JSON safety rules from `submodule_bootstrap.md` Section 2.10 (precise sed, JSON validation with `python3 json.load()`).
3.  **Provider Detection:** Run `tools/detect-providers.sh` and merge available providers into config, per `submodule_bootstrap.md` Section 2.17.
4.  **Upstream SHA Recording:** Record the current submodule HEAD SHA to `.purlin/.upstream_sha` (40-character SHA, single line).
5.  **Launcher Script Generation:** Generate `run_architect.sh`, `run_builder.sh`, `run_qa.sh` at the project root, per `submodule_bootstrap.md` Section 2.5 (concatenation order, PURLIN_PROJECT_ROOT export, startup controls, override tolerance). All MUST be `chmod +x`.
6.  **Command File Distribution:** Copy `.claude/commands/pl-*.md` from the submodule to `<project_root>/.claude/commands/`, per `submodule_bootstrap.md` Section 2.18. `pl-edit-base.md` MUST NEVER be copied.
7.  **Features Directory:** Create `features/` at the project root if it does not exist.
8.  **Gitignore Handling:** Per `submodule_bootstrap.md` Section 2.7 (warning if `.purlin` is gitignored, recommended ignores including `.purlin/runtime/` and `.purlin/cache/`).
9.  **Shim Generation:** Generate `purlin_init.sh` at the project root (Section 2.5).
10. **CDD Convenience Symlinks:** Create symlinks at the project root (Section 2.6).
11. **Python Environment Suggestion:** Per `submodule_bootstrap.md` Section 2.16 (informational, non-blocking).
12. **Summary Output:** Print a concise summary (Section 2.7).

### 2.4 Refresh Mode

When `.purlin/` already exists, the script MUST perform only these updates:

1.  **Command File Refresh:** Copy/update `.claude/commands/pl-*.md` from the submodule to the project root. For each file:
    *   If the destination file does not exist: copy it.
    *   If the destination file exists AND is newer than the source (local modification): skip it.
    *   If the destination file exists AND is older than or same age as the source: overwrite it.
    *   `pl-edit-base.md` MUST NEVER be copied.
2.  **Upstream SHA Update:** Update `.purlin/.upstream_sha` with the current submodule HEAD SHA.
3.  **Shim Self-Update:** If `purlin_init.sh` at the project root is stale (the embedded SHA or version differs from the current submodule state), regenerate it (Section 2.5).
4.  **CDD Symlink Repair:** If either CDD convenience symlink is missing, recreate it (Section 2.6).
5.  **Refresh Summary:** Print a concise summary (Section 2.8).

### 2.4.1 Refresh Mode Exclusions

Refresh mode MUST NEVER modify:

*   `.purlin/config.json` or `.purlin/config.local.json`
*   `.purlin/*_OVERRIDES.md`
*   `.purlin/release/` (any file)
*   `.gitignore`
*   `features/` directory
*   Launcher scripts (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`) — UNLESS the `--regenerate-launchers` flag is passed (Section 2.9).

### 2.5 Project-Root Shim (`purlin_init.sh`)

The script MUST generate a `purlin_init.sh` file at the project root with the following properties:

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

*   `purlin_cdd_start.sh` -> `<submodule>/tools/cdd/start.sh`
*   `purlin_cdd_stop.sh` -> `<submodule>/tools/cdd/stop.sh`

The symlinks MUST use relative paths (not absolute) so they remain valid after repository relocation. If a symlink already exists and points to the correct target, leave it unchanged. If it exists but points to the wrong target, replace it.

### 2.7 Full Init Output

The full init summary MUST be concise — no verbose logs, just the essentials:

```
Purlin initialized.

  purlin_init.sh          Run anytime to refresh
  ./run_architect.sh      Start Architect session
  ./run_builder.sh        Start Builder session
  ./run_qa.sh             Start QA session
  ./purlin_cdd_start.sh   Start CDD dashboard
  ./purlin_cdd_stop.sh    Stop CDD dashboard

Next: git add -A && git commit -m "init purlin"
```

Provider detection results and command file counts MAY be included on additional lines if non-trivial (e.g., providers found, N commands copied).

### 2.8 Refresh Output

The refresh summary MUST be a single line when nothing special happened:

```
Purlin refreshed. (N commands updated, M skipped)
```

If CDD symlinks were repaired or the shim was updated, append a brief note.

### 2.9 CLI Flags

*   **`--regenerate-launchers`:** When passed, refresh mode ALSO regenerates launcher scripts (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`), overwriting existing ones. Without this flag, launchers are never touched in refresh mode.
*   **`--quiet`:** Suppresses all non-error output. Intended for scripted use (e.g., called by `/pl-update-purlin`). Errors still print to stderr.

### 2.10 Bootstrap Deprecation Shim

The existing `tools/bootstrap.sh` MUST be modified to:

1.  Print a deprecation notice: `"bootstrap.sh is deprecated. Use init.sh instead."` (to stderr).
2.  Delegate to `tools/init.sh` by `exec`-ing it with all original arguments.

This preserves backward compatibility — existing consumer projects with `bootstrap.sh` in their workflows will still work but see the deprecation notice.

### 2.11 Idempotency

Running the script multiple times MUST produce the same result. Specifically:

*   Full init followed by another run MUST enter refresh mode (not fail or re-initialize).
*   Refresh mode followed by another refresh MUST produce no file changes (verified by `git diff` showing nothing new).
*   CDD symlinks, command files, and SHA marker MUST be stable across repeated runs when the submodule has not changed.

### 2.12 Integration with `/pl-update-purlin`

After a successful submodule update (step 10 in the `/pl-update-purlin` workflow: atomic update), the skill MUST run `tools/init.sh --quiet` to refresh commands, symlinks, shim, and SHA. This replaces the skill's manual post-update copy logic with the canonical refresh mechanism. The skill's step 7 (command file changes with three-way diff) remains for conflict resolution on modified files. The skill's step 12 summary MUST note that init/refresh ran.

### 2.13 Automated Verification Test Script

A comprehensive test script MUST be created at `tools/test_init.sh` (executable, `chmod +x`) that exercises all init and refresh scenarios in a simulated submodule sandbox. This script replaces the role of `tools/test_bootstrap.sh` for init-related verification.

#### 2.13.1 Sandbox Architecture

*   **Temporary Directory:** The test creates a temporary directory acting as a consumer project root, with a git-initialized repo.
*   **Submodule Simulation:** A clone (or copy) of the current Purlin repository is placed inside the sandbox at a submodule-like path (e.g., `my-project/purlin/`). Any uncommitted tool/script changes MUST be overlaid onto the clone so tests exercise the latest code.
*   **Git Setup:** The sandbox repo MUST have the simulated submodule registered in `.gitmodules` and have an initial commit, so `git submodule` commands work correctly within the sandbox.
*   **Cleanup:** The test MUST clean up all temporary directories on exit via `trap`, even on test failure.

#### 2.13.2 Required Test Scenarios

The test script MUST include assertions for all of the following. Each test MUST print a clear PASS/FAIL result with a descriptive label.

**Full Init Tests:**

1.  **Fresh init creates `.purlin/`:** Run `init.sh` in a clean sandbox. Assert `.purlin/` exists with `config.json`, all `*_OVERRIDES.md` templates, and `.upstream_sha`.
2.  **Config JSON validity:** Assert the patched `config.json` is valid JSON via `python3 -c "import json; json.load(open(...))"`.
3.  **Config `tools_root` is correct:** Assert `config.json` contains the expected `tools_root` value for the submodule path.
4.  **Launcher scripts created:** Assert `run_architect.sh`, `run_builder.sh`, `run_qa.sh` exist and are executable.
5.  **Launcher scripts export PURLIN_PROJECT_ROOT:** Assert each launcher contains `export PURLIN_PROJECT_ROOT`.
6.  **Command files copied:** Assert `.claude/commands/` exists and contains `pl-*.md` files.
7.  **`pl-edit-base.md` excluded:** Assert `.claude/commands/pl-edit-base.md` does NOT exist.
8.  **`features/` directory created:** Assert `features/` exists at the project root.
9.  **Shim generated:** Assert `purlin_init.sh` exists and is executable.
10. **Shim contains metadata:** Assert `purlin_init.sh` header contains the submodule remote URL, SHA, and version tag (or "untagged").
11. **CDD symlinks created:** Assert `purlin_cdd_start.sh` and `purlin_cdd_stop.sh` exist as symlinks pointing to the correct targets.
12. **CDD symlinks use relative paths:** Assert the symlink targets are relative (not absolute).
13. **Output is concise:** Assert stdout contains "Purlin initialized" and the expected summary lines.

**Refresh Mode Tests:**

14. **Re-run enters refresh mode:** Run `init.sh` a second time. Assert no error, and that `.purlin/config.json` was NOT re-created (modification time unchanged).
15. **Idempotent second run:** After the second run, assert `git diff` shows no changes in the sandbox (excluding untracked test artifacts).
16. **New command files copied on refresh:** Create a new `pl-test-new.md` in the submodule's `.claude/commands/`. Run refresh. Assert it appears at the project root.
17. **Locally modified commands preserved:** Touch a project-root command file to make it newer than the submodule version. Run refresh. Assert the file was NOT overwritten.
18. **`pl-edit-base.md` excluded on refresh:** Assert `pl-edit-base.md` is not copied during refresh.
19. **Upstream SHA updated on refresh:** Modify the submodule HEAD (e.g., create a commit). Run refresh. Assert `.purlin/.upstream_sha` contains the new SHA.
20. **Config and overrides untouched on refresh:** Record checksums of `.purlin/config.json` and all `*_OVERRIDES.md` before refresh. Run refresh. Assert checksums match.
21. **CDD symlinks repaired on refresh:** Delete one CDD symlink. Run refresh. Assert it is recreated.
22. **Shim self-update on refresh:** Modify the submodule HEAD (new commit). Run refresh. Assert `purlin_init.sh` header contains the updated SHA.

**CLI Flag Tests:**

23. **`--quiet` suppresses output:** Run `init.sh --quiet` in refresh mode. Assert stdout is empty.
24. **`--quiet` still completes:** After `--quiet` run, assert `.purlin/.upstream_sha` was updated (refresh completed).
25. **`--regenerate-launchers` regenerates scripts:** Modify `run_architect.sh` content. Run `init.sh --regenerate-launchers`. Assert `run_architect.sh` was overwritten with fresh content.
26. **Refresh without `--regenerate-launchers` preserves launchers:** Modify `run_architect.sh` content. Run `init.sh` (no flag). Assert `run_architect.sh` was NOT overwritten.

**Deprecation Shim Tests:**

27. **`bootstrap.sh` prints deprecation notice:** Run `bootstrap.sh`. Assert stderr contains "deprecated" and "init.sh".
28. **`bootstrap.sh` delegates to `init.sh`:** Run `bootstrap.sh` in a clean sandbox. Assert the same artifacts are created as a direct `init.sh` run.

**Ergonomic Symlink Tests:**

29. **Submodule root symlink exists:** Assert `<submodule>/init.sh` is a symlink to `tools/init.sh`.
30. **Submodule root symlink works:** Run `<submodule>/init.sh`. Assert it behaves identically to `<submodule>/tools/init.sh`.

#### 2.13.3 Test Output Format

*   Each test prints: `PASS: <description>` or `FAIL: <description>` followed by diagnostic details on failure.
*   At the end, print a summary: `N/M tests passed`. Exit with non-zero status if any test failed.
*   Tests MUST run independently where possible — a failure in one test MUST NOT prevent subsequent tests from running (use per-test `set +e` / `set -e` or subshell isolation).

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Full Init Creates All Artifacts

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then .purlin/ is created with config.json, all override templates, and .upstream_sha
    And config.json contains the correct tools_root for the submodule path
    And config.json is valid JSON (parseable by python3 json.load)
    And run_architect.sh, run_builder.sh, run_qa.sh exist at the project root and are executable
    And .claude/commands/ contains pl-*.md files from the submodule (excluding pl-edit-base.md)
    And features/ directory exists at the project root
    And purlin_init.sh exists at the project root and is executable

#### Scenario: Full Init Creates CDD Convenience Symlinks

    Given Purlin is added as a submodule at "purlin/"
    And no .purlin/ directory exists at the project root
    When the user runs "purlin/tools/init.sh"
    Then purlin_cdd_start.sh exists at the project root as a symlink to purlin/tools/cdd/start.sh
    And purlin_cdd_stop.sh exists at the project root as a symlink to purlin/tools/cdd/stop.sh
    And both symlinks use relative paths

#### Scenario: Shim Contains Repo URL, SHA, and Version

    Given Purlin is added as a submodule at "purlin/"
    And the submodule remote URL is "https://github.com/rlabarca/purlin.git"
    And the submodule HEAD is at SHA "abc1234..." with tag "v0.9.0"
    When the user runs "purlin/tools/init.sh"
    Then purlin_init.sh contains the remote URL in its header comments
    And purlin_init.sh contains the SHA in its header comments
    And purlin_init.sh contains "v0.9.0" in its header comments

#### Scenario: Shim Initializes Submodule on Fresh Clone

    Given a consumer project was cloned without --recurse-submodules
    And the submodule directory exists but is empty (not initialized)
    And purlin_init.sh exists at the project root (previously committed)
    When the user runs "./purlin_init.sh"
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
    And purlin_init.sh at the project root has an older pinned SHA than the current submodule HEAD
    When the user runs "purlin/tools/init.sh"
    Then purlin_init.sh is regenerated with the current SHA and version

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
    And purlin_cdd_start.sh does NOT exist at the project root
    When the user runs "purlin/tools/init.sh"
    Then purlin_cdd_start.sh is created as a symlink to purlin/tools/cdd/start.sh
    And purlin_cdd_stop.sh is created as a symlink to purlin/tools/cdd/stop.sh

#### Scenario: Idempotent Repeated Runs

    Given Purlin is added as a submodule at "purlin/"
    And the user has already run "purlin/tools/init.sh" once (full init completed)
    When the user runs "purlin/tools/init.sh" a second time
    Then refresh mode is selected (not full init)
    And running git diff after the second run shows no changes

#### Scenario: --regenerate-launchers Flag

    Given .purlin/ already exists at the project root
    And run_architect.sh exists at the project root
    When the user runs "purlin/tools/init.sh --regenerate-launchers"
    Then run_architect.sh, run_builder.sh, run_qa.sh are regenerated
    And the regenerated scripts match current launcher spec (concatenation order, PURLIN_PROJECT_ROOT export)

#### Scenario: --quiet Flag Suppresses Output

    Given .purlin/ already exists at the project root
    When the user runs "purlin/tools/init.sh --quiet"
    Then no output is written to stdout
    And the refresh completes successfully

#### Scenario: Bootstrap Deprecation Shim

    Given tools/bootstrap.sh exists
    When the user runs "purlin/tools/bootstrap.sh"
    Then a deprecation notice is printed to stderr mentioning init.sh
    And tools/init.sh is executed (delegated via exec)

#### Scenario: Ergonomic Symlink at Submodule Root

    Given Purlin is the submodule at "purlin/"
    When the user inspects "purlin/init.sh"
    Then it is a symlink pointing to "tools/init.sh"
    And running "purlin/init.sh" behaves identically to running "purlin/tools/init.sh"

### Manual Scenarios (Human Verification Required)

#### Scenario: Fresh Clone Collaborator Flow

    Given a collaborator has cloned a consumer project (without --recurse-submodules)
    And purlin_init.sh was committed to the repository
    When the collaborator runs "./purlin_init.sh"
    Then the submodule is initialized and populated
    And all Purlin artifacts (launchers, commands, symlinks) are created or refreshed
    And the collaborator can immediately run ./run_architect.sh
