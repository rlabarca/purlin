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
5.  **Launcher Script Generation:** Generate `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh` at the project root. Each launcher concatenates base + role instruction files with overrides and exports `PURLIN_PROJECT_ROOT`. All MUST be `chmod +x`.
6.  **Command File Distribution:** Copy `.claude/commands/pl-*.md` from the submodule to `<project_root>/.claude/commands/`. `pl-edit-base.md` MUST NEVER be copied. If a destination file is newer than the source (local modification), skip it.
7.  **Features Directory:** Create `features/` at the project root if it does not exist.
8.  **Gitignore Handling:** Warn if `.purlin` appears in `.gitignore`. Append recommended ignores (including `.purlin/runtime/` and `.purlin/cache/`) if not already present.
9.  **Shim Generation:** Generate `pl-init.sh` at the project root (Section 2.5).
10. **CDD Convenience Symlinks:** Create symlinks at the project root (Section 2.6).
11. **Python Environment Suggestion:** If `.venv/` does not exist, print an optional venv setup suggestion. Informational and non-blocking.
12. **Summary Output:** Print a concise summary (Section 2.7).

### 2.4 Refresh Mode

When `.purlin/` already exists, the script MUST perform only these updates:

1.  **Command File Refresh:** Copy/update `.claude/commands/pl-*.md` from the submodule to the project root. For each file:
    *   If the destination file does not exist: copy it.
    *   If the destination file exists AND is newer than the source (local modification): skip it.
    *   If the destination file exists AND is older than or same age as the source: overwrite it.
    *   `pl-edit-base.md` MUST NEVER be copied.
2.  **Upstream SHA Update:** Update `.purlin/.upstream_sha` with the current submodule HEAD SHA.
3.  **Shim Self-Update:** If `pl-init.sh` at the project root is stale (the embedded SHA or version differs from the current submodule state), regenerate it (Section 2.5).
4.  **CDD Symlink Repair:** If either CDD convenience symlink is missing, recreate it (Section 2.6).
5.  **Refresh Summary:** Print a concise summary (Section 2.8).

### 2.4.1 Refresh Mode Exclusions

Refresh mode MUST NEVER modify:

*   `.purlin/config.json` or `.purlin/config.local.json`
*   `.purlin/*_OVERRIDES.md`
*   `.purlin/release/` (any file)
*   `.gitignore`
*   `features/` directory
*   Launcher scripts (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`) — UNLESS the `--regenerate-launchers` flag is passed (Section 2.9).

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

The symlinks MUST use relative paths (not absolute) so they remain valid after repository relocation. If a symlink already exists and points to the correct target, leave it unchanged. If it exists but points to the wrong target, replace it.

### 2.7 Full Init Output

The full init summary MUST be concise — no verbose logs, just the essentials:

```
Purlin initialized.

  pl-init.sh              Run anytime to refresh
  ./pl-run-architect.sh   Start Architect session
  ./pl-run-builder.sh     Start Builder session
  ./pl-run-qa.sh          Start QA session
  ./pl-cdd-start.sh       Start CDD dashboard
  ./pl-cdd-stop.sh        Stop CDD dashboard

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

*   **`--regenerate-launchers`:** When passed, refresh mode ALSO regenerates launcher scripts (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`), overwriting existing ones. Without this flag, launchers are never touched in refresh mode.
*   **`--quiet`:** Suppresses all non-error output. Intended for scripted use (e.g., called by `/pl-update-purlin`). Errors still print to stderr.

### 2.10 Idempotency

Running the script multiple times MUST produce the same result. Specifically:

*   Full init followed by another run MUST enter refresh mode (not fail or re-initialize).
*   Refresh mode followed by another refresh MUST produce no file changes (verified by `git diff` showing nothing new).
*   CDD symlinks, command files, and SHA marker MUST be stable across repeated runs when the submodule has not changed.

### 2.11 Integration with `/pl-update-purlin`

After a successful submodule update (step 10 in the `/pl-update-purlin` workflow: atomic update), the skill MUST run `tools/init.sh --quiet` to refresh commands, symlinks, shim, and SHA. This replaces the skill's manual post-update copy logic with the canonical refresh mechanism. The skill's step 7 (command file changes with three-way diff) remains for conflict resolution on modified files. The skill's step 12 summary MUST note that init/refresh ran.

### 2.12 Automated Verification Test Script

A comprehensive test script MUST be created at `tools/test_init.sh` (executable, `chmod +x`) that exercises all init and refresh scenarios in a simulated submodule sandbox.

#### 2.12.1 Sandbox Architecture

*   **Temporary Directory:** The test creates a temporary directory acting as a consumer project root, with a git-initialized repo.
*   **Submodule Simulation:** A clone (or copy) of the current Purlin repository is placed inside the sandbox at a submodule-like path (e.g., `my-project/purlin/`). Any uncommitted tool/script changes MUST be overlaid onto the clone so tests exercise the latest code.
*   **Git Setup:** The sandbox repo MUST have the simulated submodule registered in `.gitmodules` and have an initial commit, so `git submodule` commands work correctly within the sandbox.
*   **Cleanup:** The test MUST clean up all temporary directories on exit via `trap`, even on test failure.

#### 2.12.2 Required Test Scenarios

The test script MUST include assertions for all of the following. Each test MUST print a clear PASS/FAIL result with a descriptive label.

**Full Init Tests:**

1.  **Fresh init creates `.purlin/`:** Run `init.sh` in a clean sandbox. Assert `.purlin/` exists with `config.json`, all `*_OVERRIDES.md` templates, and `.upstream_sha`.
2.  **Config JSON validity:** Assert the patched `config.json` is valid JSON via `python3 -c "import json; json.load(open(...))"`.
3.  **Config `tools_root` is correct:** Assert `config.json` contains the expected `tools_root` value for the submodule path.
4.  **Launcher scripts created:** Assert `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh` exist and are executable.
5.  **Launcher scripts export PURLIN_PROJECT_ROOT:** Assert each launcher contains `export PURLIN_PROJECT_ROOT`.
6.  **Command files copied:** Assert `.claude/commands/` exists and contains `pl-*.md` files.
7.  **`pl-edit-base.md` excluded:** Assert `.claude/commands/pl-edit-base.md` does NOT exist.
8.  **`features/` directory created:** Assert `features/` exists at the project root.
9.  **Shim generated:** Assert `pl-init.sh` exists and is executable.
10. **Shim contains metadata:** Assert `pl-init.sh` header contains the submodule remote URL, SHA, and version tag (or "untagged").
11. **CDD symlinks created:** Assert `pl-cdd-start.sh` and `pl-cdd-stop.sh` exist as symlinks pointing to the correct targets.
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
25. **`--regenerate-launchers` regenerates scripts:** Modify `pl-run-architect.sh` content. Run `init.sh --regenerate-launchers`. Assert `pl-run-architect.sh` was overwritten with fresh content.
26. **Refresh without `--regenerate-launchers` preserves launchers:** Modify `pl-run-architect.sh` content. Run `init.sh` (no flag). Assert `pl-run-architect.sh` was NOT overwritten.

**Standalone Guard Tests:**

27. **Standalone guard refuses init in Purlin repo:** Run `init.sh` from within the Purlin repo itself (where the computed `$PROJECT_ROOT` is not a git repository). Assert stderr contains an error about init.sh being for consumer projects only. Assert non-zero exit status. Assert no files created outside the repo.

**Ergonomic Symlink Tests:**

28. **Submodule root symlink exists:** Assert `<submodule>/pl-init.sh` is a symlink to `tools/init.sh`.
29. **Submodule root symlink works:** Run `<submodule>/pl-init.sh`. Assert it behaves identically to `<submodule>/tools/init.sh`.

#### 2.12.3 Test Output Format

*   Each test prints: `PASS: <description>` or `FAIL: <description>` followed by diagnostic details on failure.
*   At the end, print a summary: `N/M tests passed`. Exit with non-zero status if any test failed.
*   Tests MUST run independently where possible — a failure in one test MUST NOT prevent subsequent tests from running (use per-test `set +e` / `set -e` or subshell isolation).

### 2.13 Standalone Mode Guard

The script MUST detect when it is being run inside the standalone Purlin repo (where Purlin IS the project, not a submodule) and refuse to proceed.

*   **Detection:** After computing `PROJECT_ROOT` (the parent of `SUBMODULE_DIR`), check whether `$PROJECT_ROOT` is a git repository (e.g., `git -C "$PROJECT_ROOT" rev-parse --git-dir`). In a consumer project, the parent directory IS the consumer's git repo root. In standalone mode, the Purlin repo's parent is NOT a git repository, so the check fails. If `$PROJECT_ROOT` is not a git repository, print an error and exit non-zero.
*   **Error Message:** The error MUST be printed to stderr and explain that `init.sh` is for consumer projects only, not for the Purlin repository itself.
*   **No Side Effects:** The guard MUST fire before any file creation or modification. No files outside the Purlin repo may be created or modified.

### 2.14 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/project_init/fresh-directory` | Empty project directory with no .purlin or purlin submodule |
| `main/project_init/partially-initialized` | Project directory with .purlin directory but incomplete initialization (missing override files) |

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
    And pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh exist at the project root and are executable
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

#### Scenario: Idempotent Repeated Runs

    Given Purlin is added as a submodule at "purlin/"
    And the user has already run "purlin/tools/init.sh" once (full init completed)
    When the user runs "purlin/tools/init.sh" a second time
    Then refresh mode is selected (not full init)
    And running git diff after the second run shows no changes

#### Scenario: --regenerate-launchers Flag

    Given .purlin/ already exists at the project root
    And pl-run-architect.sh exists at the project root
    When the user runs "purlin/tools/init.sh --regenerate-launchers"
    Then pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh are regenerated
    And the regenerated scripts match current launcher spec (concatenation order, PURLIN_PROJECT_ROOT export)

#### Scenario: --quiet Flag Suppresses Output

    Given .purlin/ already exists at the project root
    When the user runs "purlin/tools/init.sh --quiet"
    Then no output is written to stdout
    And the refresh completes successfully

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

#### Scenario: Fresh Clone Collaborator Flow

    Given a sandbox consumer project has been initialized with Purlin (full init completed)
    And pl-init.sh has been committed to the repository
    And the sandbox is re-cloned without --recurse-submodules (simulating a collaborator fresh clone)
    When the collaborator runs "./pl-init.sh" in the re-cloned sandbox
    Then git submodule update --init is triggered for the submodule
    And .purlin/ exists with config.json and override templates
    And launcher scripts (pl-run-architect.sh, pl-run-builder.sh, pl-run-qa.sh) exist and are executable
    And .claude/commands/ contains pl-*.md files
    And CDD convenience symlinks exist
    And the collaborator environment matches a normal full init

### Manual Scenarios (Human Verification Required)

None.
