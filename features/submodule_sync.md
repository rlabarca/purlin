# Feature: Submodule Upstream Sync [REMOVED]

> Label: "Tool: Upstream Sync [REMOVED - use /pl-update-purlin]"
> Category: "Install, Update & Scripts"
> Prerequisite: features/submodule_bootstrap.md
> **Status**: REMOVED — Replaced by features/pl_update_purlin.md

## 1. Overview
**REMOVED**: This feature described the original script-based sync approach (`tools/sync_upstream.sh`). The script has been fully removed and replaced by the intelligent agent skill `/pl-update-purlin` (see features/pl_update_purlin.md).

The script-based approach had fundamental limitations:
- No intelligence about user customizations in `.purlin/` folder
- No tracking of top-level scripts (run_builder.sh, etc.)
- Binary decisions only (auto-copy or warn) with no smart merging
- No semantic understanding of changes

**Replacement**: The `/pl-update-purlin` agent skill provides all functionality of the removed script plus intelligent merge strategies, migration plans, preservation of user customizations, and comprehensive tracking of all Purlin-managed files.

---

## Original Spec (For Historical Reference)

This tool fetches the latest upstream Purlin commits, offers to update the local submodule, audits what changed, and updates the sync marker. It provides a human-readable changelog of instruction and tool changes so the project maintainer can assess the impact on their overrides.

## 2. Requirements

### 2.1 Script Location
*   **Path:** `tools/sync_upstream.sh` (executable, `chmod +x`).
*   **Invocation:** Intended to be run from the consumer project root, or from any directory (the script MUST resolve paths relative to its own location).

### 2.2 Auto-Fetch and Update Prompt
*   **Fetch:** The script MUST run `git -C <submodule_dir> fetch` to retrieve the latest upstream commits before any comparison.
*   **Local vs Remote Check:** After fetching, compare the local submodule HEAD against its remote tracking branch (e.g., `origin/main`). Determine how many commits the local submodule is behind.
*   **Already Current:** If the local submodule HEAD is at or ahead of the remote tracking branch, print "Submodule is up to date with remote." and proceed directly to the SHA comparison (Section 2.3).
*   **Update Available:** If the local submodule is behind, print: `"Submodule is N commit(s) behind remote. Update to latest?"` and prompt the user for confirmation (y/n).
    *   If the user confirms: run `git -C <submodule_dir> merge --ff-only <remote_tracking_branch>` to advance the submodule to the latest commit, then proceed to SHA comparison.
    *   If the user declines: print "Skipping update. Running sync against current local state." and proceed to SHA comparison using the existing local HEAD (the script still runs the changelog/sync logic against whatever is checked out locally).
*   **Detached HEAD:** If the submodule is in detached HEAD state (typical for submodules), use `git -C <submodule_dir> log --oneline HEAD..<remote_tracking_branch>` to count commits behind, and use `git -C <submodule_dir> checkout <remote_tracking_branch_sha>` (detached) instead of merge to advance.

### 2.3 SHA Comparison
*   **Old SHA:** Read from `.purlin/.upstream_sha` (relative to the project root). If the file does not exist, print an error and exit with a non-zero status code.
*   **Current SHA:** Read the current HEAD SHA of the submodule directory (after any update from Section 2.2).
*   **Up-to-Date Check:** If old SHA equals current SHA, print "Already up to date — no changes since last sync." and exit successfully.

### 2.4 Changelog Display
*   **Instruction Changes:** Run `git -C <submodule_dir> diff <old_sha>..HEAD -- instructions/` and display the output under a clear "Instruction Changes" header.
*   **Tool Changes:** Run `git -C <submodule_dir> diff <old_sha>..HEAD -- tools/` and display the output under a "Tool Changes" header.
*   **Contextual Notes:**
    - For tool changes: Note that these are automatic (tools are used directly from the submodule).
    - For base instruction changes: Note that these are automatic (read at launch time by the launcher scripts).
    - Flag any structural changes that might affect overrides (e.g., renamed section headers, removed sections).

### 2.5 SHA Update
*   **Write New SHA:** After displaying the changelog, update `.purlin/.upstream_sha` with the current submodule HEAD SHA.

### 2.6 Project Root Detection
*   **Detection Logic:** The script MUST detect the project root using the same approach as `bootstrap.sh` (climbing from script location through the submodule directory to the parent project).

### 2.7 Command File Sync
*   **Change Detection:** Detect command files changed or added between `<old_sha>` and `HEAD` by running `git -C <submodule_dir> diff --name-only <old_sha>..HEAD -- .claude/commands/`.
*   **Exclusion — `pl-edit-base.md`:** This file MUST NEVER be synced to consumer projects. It is Purlin-internal and allows modification of base instruction files. Skip it in all sync operations — do not auto-copy, do not warn, do not report it as a change.
*   **Auto-Update (unmodified):** For each changed or new command file, compare the consumer's current copy against what the file was at `<old_sha>` in the submodule. If the content matches (consumer has not modified it), auto-copy the updated file unconditionally and report: `Updated: <filename>`.
*   **Modified Warning:** If the consumer's copy differs from the `<old_sha>` version (consumer has local modifications), print a warning and skip the file. Do NOT overwrite. Report: `WARNING: <filename> has local modifications — manual review required`.
*   **New Commands:** If the command file does not yet exist in the consumer project, copy it unconditionally and report: `Added: <filename> (new command)`.
*   **Deleted Upstream:** If a file was deleted upstream between old and current SHA, print an informational note: `DELETED upstream: <filename> (manual cleanup may be required)`. Do not delete the consumer's copy automatically.
*   **Summary:** Print a summary line: `N command file(s) updated. N new command(s) added. N require manual review.`
*   **No-Change Case:** If no command files changed between SHAs, print `(no command file changes)`.

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto-Fetch and Update When Behind
    Given the submodule's local HEAD is behind the remote tracking branch
    And .purlin/.upstream_sha contains the old SHA
    When the user runs "tools/sync_upstream.sh"
    Then the script fetches from the submodule's remote
    And reports how many commits the submodule is behind
    And prompts the user to update
    When the user confirms the update
    Then the submodule is advanced to the latest remote commit
    And the changelog is displayed
    And .purlin/.upstream_sha is updated to the new SHA

#### Scenario: User Declines Update
    Given the submodule's local HEAD is behind the remote tracking branch
    When the user runs "tools/sync_upstream.sh"
    And the user declines the update prompt
    Then the script proceeds with the current local HEAD
    And runs the changelog/sync logic against the local state

#### Scenario: Submodule Already Current With Remote
    Given the submodule's local HEAD matches the remote tracking branch
    And .purlin/.upstream_sha differs from the current submodule HEAD
    When the user runs "tools/sync_upstream.sh"
    Then "Submodule is up to date with remote." is printed
    And the changelog is displayed for changes since the last sync
    And .purlin/.upstream_sha is updated to the current SHA

#### Scenario: Already Up to Date (No Changes Since Last Sync)
    Given .purlin/.upstream_sha matches the current submodule HEAD
    When the user runs "tools/sync_upstream.sh"
    Then "Already up to date — no changes since last sync." is printed
    And the script exits with status 0

#### Scenario: Missing Upstream SHA File
    Given .purlin/.upstream_sha does not exist
    When the user runs "tools/sync_upstream.sh"
    Then an error message is printed indicating the file is missing
    And the script exits with a non-zero status

#### Scenario: Contextual Notes for Changes
    Given upstream changes include modifications to instructions/ and tools/
    When the sync report is displayed
    Then a note explains that tool changes are automatic
    And a note explains that base instruction changes are automatic
    And structural changes that may affect overrides are flagged

#### Scenario: Command Files Auto-Updated
    Given the submodule has been updated and pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md matches the old submodule version (unmodified)
    When the user runs "tools/sync_upstream.sh"
    Then pl-status.md is auto-copied from the submodule to .claude/commands/
    And the sync report prints "Updated: pl-status.md"

#### Scenario: New Command File Added Upstream
    Given the submodule has been updated and pl-graph.md is a new file
    And the consumer project does not yet have .claude/commands/pl-graph.md
    When the user runs "tools/sync_upstream.sh"
    Then pl-graph.md is copied to .claude/commands/
    And the sync report prints "Added: pl-graph.md (new command)"

#### Scenario: Locally Modified Command File Warns
    Given the submodule has been updated and pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md has been locally modified (differs from old submodule version)
    When the user runs "tools/sync_upstream.sh"
    Then pl-status.md is NOT overwritten
    And the sync report prints a WARNING about local modifications

#### Scenario: No Command File Changes
    Given the submodule update did not change any .claude/commands/ files
    When the user runs "tools/sync_upstream.sh"
    Then the Command File Updates section prints "(no command file changes)"

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

