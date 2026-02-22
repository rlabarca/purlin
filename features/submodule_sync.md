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
*   **Old SHA:** Read from `.agentic_devops/.upstream_sha` (relative to the project root). If the file does not exist, print an error and exit with a non-zero status code.
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
*   **Write New SHA:** After displaying the changelog, update `.agentic_devops/.upstream_sha` with the current submodule HEAD SHA.

### 2.5 Project Root Detection
*   **Detection Logic:** The script MUST detect the project root using the same approach as `bootstrap.sh` (climbing from script location through the submodule directory to the parent project).

## 3. Scenarios

### Automated Scenarios

#### Scenario: Detect Upstream Changes
    Given the submodule has been updated to a newer commit
    And .agentic_devops/.upstream_sha contains the old SHA
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then the diff of instructions/ between old and new SHA is displayed
    And the diff of tools/ between old and new SHA is displayed
    And .agentic_devops/.upstream_sha is updated to the current SHA

#### Scenario: Already Up to Date
    Given .agentic_devops/.upstream_sha matches the current submodule HEAD
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then "Already up to date" is printed
    And the script exits with status 0

#### Scenario: Missing Upstream SHA File
    Given .agentic_devops/.upstream_sha does not exist
    When the user runs "agentic-dev/tools/sync_upstream.sh"
    Then an error message is printed indicating the file is missing
    And the script exits with a non-zero status

#### Scenario: Contextual Notes for Changes
    Given upstream changes include modifications to instructions/ and tools/
    When the sync report is displayed
    Then a note explains that tool changes are automatic
    And a note explains that base instruction changes are automatic
    And structural changes that may affect overrides are flagged

### Manual Scenarios (Human Verification Required)
None. All scenarios for this feature are fully automated.

## 4. Implementation Notes
See [submodule_sync.impl.md](submodule_sync.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
