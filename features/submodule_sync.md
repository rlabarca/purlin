# Feature: Submodule Upstream Sync

> Label: "Tool: Upstream Sync"
> Category: "Install, Update & Scripts"
> Prerequisite: features/submodule_bootstrap.md

## 1. Overview
After a consumer project updates its Purlin submodule (`git submodule update`), this tool audits what changed upstream and updates the sync marker. It provides a human-readable changelog of instruction and tool changes so the project maintainer can assess the impact on their overrides.

## 2. Requirements

### 2.1 Script Location
*   **Path:** `tools/sync_upstream.sh` (executable, `chmod +x`).
*   **Invocation:** Intended to be run from the consumer project root, or from any directory (the script MUST resolve paths relative to its own location).

### 2.2 SHA Comparison
*   **Old SHA:** Read from `.purlin/.upstream_sha` (relative to the project root). If the file does not exist, print an error and exit with a non-zero status code.
*   **Current SHA:** Read the current HEAD SHA of the submodule directory.
*   **Up-to-Date Check:** If old SHA equals current SHA, print "Already up to date" and exit successfully.

### 2.3 Changelog Display
*   **Instruction Changes:** Run `git -C <submodule_dir> diff <old_sha>..HEAD -- instructions/` and display the output under a clear "Instruction Changes" header.
*   **Tool Changes:** Run `git -C <submodule_dir> diff <old_sha>..HEAD -- tools/` and display the output under a "Tool Changes" header.
*   **Contextual Notes:**
    - For tool changes: Note that these are automatic (tools are used directly from the submodule).
    - For base instruction changes: Note that these are automatic (read at launch time by the launcher scripts).
    - Flag any structural changes that might affect overrides (e.g., renamed section headers, removed sections).

### 2.4 SHA Update
*   **Write New SHA:** After displaying the changelog, update `.purlin/.upstream_sha` with the current submodule HEAD SHA.

### 2.5 Project Root Detection
*   **Detection Logic:** The script MUST detect the project root using the same approach as `bootstrap.sh` (climbing from script location through the submodule directory to the parent project).

### 2.6 Command File Sync
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

#### Scenario: Detect Upstream Changes
    Given the submodule has been updated to a newer commit
    And .purlin/.upstream_sha contains the old SHA
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then the diff of instructions/ between old and new SHA is displayed
    And the diff of tools/ between old and new SHA is displayed
    And .purlin/.upstream_sha is updated to the current SHA

#### Scenario: Already Up to Date
    Given .purlin/.upstream_sha matches the current submodule HEAD
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then "Already up to date" is printed
    And the script exits with status 0

#### Scenario: Missing Upstream SHA File
    Given .purlin/.upstream_sha does not exist
    When the user runs "agentic-dev/tools/sync_upstream.sh"
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
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then pl-status.md is auto-copied from the submodule to .claude/commands/
    And the sync report prints "Updated: pl-status.md"

#### Scenario: New Command File Added Upstream
    Given the submodule has been updated and pl-graph.md is a new file
    And the consumer project does not yet have .claude/commands/pl-graph.md
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then pl-graph.md is copied to .claude/commands/
    And the sync report prints "Added: pl-graph.md (new command)"

#### Scenario: Locally Modified Command File Warns
    Given the submodule has been updated and pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md has been locally modified (differs from old submodule version)
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then pl-status.md is NOT overwritten
    And the sync report prints a WARNING about local modifications

#### Scenario: No Command File Changes
    Given the submodule update did not change any .claude/commands/ files
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then the Command File Updates section prints "(no command file changes)"

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

