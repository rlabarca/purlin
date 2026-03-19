# Feature: Intelligent Purlin Update Agent Skill

> Label: "/pl-update-purlin Intelligent Purlin Update"
> Category: "Agent Skills"
> Prerequisite: features/project_init.md
> Prerequisite: features/config_layering.md
> Test Fixtures: https://github.com/rlabarca/weather1

## 1. Overview

The `/pl-update-purlin` agent skill updates the Purlin submodule in consumer projects.
It fetches the latest upstream, advances the submodule, runs `init.sh --quiet` to refresh
all project-root artifacts, syncs config, and handles conflicts only when they exist.

Design principle: **fast path first**. The common case (no conflicts, no local modifications)
should complete in seconds with minimal agent reasoning. Heavy analysis (three-way diffs,
merge strategies) only activates when locally modified files conflict with upstream changes.

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-update-purlin [--dry-run] [--auto-approve]
```

- **--dry-run** (optional): Show what would be updated without making changes
- **--auto-approve** (optional): Skip confirmation prompts for non-conflicting changes (conflicts still require approval)

### 2.2 Standalone Mode Guard

The skill MUST detect when invoked in the standalone Purlin repo (not a consumer project) and refuse to proceed.

*   **Detection:** Check that `.purlin/.upstream_sha` does not exist AND `purlin-config-sample/` exists at the project root. The combination confirms this IS the Purlin repo, not just an un-bootstrapped consumer project (which would lack `purlin-config-sample/`).
*   **Error Message:** Print: `/pl-update-purlin is only for consumer projects using Purlin as a submodule.`
*   **No Side Effects:** The guard MUST fire before any fetch, analysis, or file modification.

### 2.3 Fetch and Version Check

The skill MUST:
1. Run `git -C <submodule_dir> fetch --tags` to retrieve latest upstream commits and tags
2. Compare local submodule HEAD against remote tracking branch (e.g., `origin/main`)
3. Determine how many commits behind the local submodule is
4. If already current with remote AND `.purlin/.upstream_sha` matches HEAD:
   - Print "Already up to date." and exit
5. If behind:
   - Detect current version: `git -C <submodule_dir> describe --tags --abbrev=0 HEAD`
   - Detect target version: `git -C <submodule_dir> describe --tags --abbrev=0 origin/main`
   - Display: `"Current: <current_version> -> Latest: <target_version> (<N> commits)"`
   - Prompt: "Update? (y/n)" (skip if `--auto-approve`)
6. If user declines: print "Skipping update." and exit

### 2.4 Pre-Update Conflict Scan

Before advancing the submodule, the skill MUST identify locally modified files that may
conflict with upstream changes. This scan is lightweight -- it only flags files, deferring
full analysis to Section 2.7.

1. Read old SHA from `.purlin/.upstream_sha`
2. Read new SHA (the target remote commit determined in Section 2.3)
3. Run `git -C <submodule> diff-tree --no-commit-id --name-status -r <old_sha> <new_sha> -- .claude/commands/` to identify upstream-changed command files in a single invocation. Also check launcher-relevant paths (`tools/init.sh`) in the same or a second `diff-tree` call.
4. **Early exit:** If diff-tree returns zero changes in `.claude/commands/` and no launcher-relevant paths changed, skip the per-file comparison entirely -- no local modifications can conflict. Proceed directly to Section 2.5.
5. For each `.claude/commands/pl-*.md` that appears in BOTH the consumer project AND the upstream diff-tree output (excluding `pl-edit-base.md`):
   - Compare local file against old upstream version: `git -C <submodule> show <old_sha>:.claude/commands/<file>`
   - If they differ, flag as "locally modified"
6. For each launcher script (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`):
   - Only check if launcher-relevant paths appeared in the diff-tree output
   - If file content differs from what init.sh would have generated at the old version, flag as "locally modified"

**CDD Symlink Exclusion:** `pl-cdd-start.sh` and `pl-cdd-stop.sh` are **symlinks** managed
exclusively by `init.sh` (see `project_init.md` Section 2.6). The skill MUST NOT read,
compare, copy, or modify these files under any circumstance. They are refreshed automatically
by the init step (Section 2.6).

### 2.5 Advance Submodule

Advance the submodule to the latest remote commit:
- Detached HEAD: `git -C <submodule_dir> checkout <remote_sha>`
- If this fails, abort with error and leave the submodule unchanged

### 2.6 Init Refresh

After advancing the submodule, run `<submodule>/tools/init.sh --quiet` to refresh all
project-root artifacts:

*   Command files (new/updated `.claude/commands/pl-*.md` are copied; locally modified files are preserved by init's timestamp logic)
*   CDD convenience symlinks (repaired if missing or corrupted)
*   Launcher scripts (`pl-run-*.sh` regenerated)
*   Project-root shim (`pl-init.sh` updated with new SHA and version)
*   `.purlin/.upstream_sha` (updated to current submodule HEAD)

This delegates the mechanical copy/symlink/shim work to the canonical init script.

### 2.7 Conflict Resolution

**This step runs ONLY if Section 2.4 flagged locally modified files.** If no files were
flagged, skip this section entirely.

For each flagged file:
1. Retrieve old upstream version: `git -C <submodule> show <old_sha>:<path>`
2. Retrieve new upstream version: `git -C <submodule> show HEAD:<path>` (or current file for commands already copied by init)
3. If upstream did NOT change the file between old and new SHA: no action needed (local changes are safe)
4. If upstream DID change the file (true conflict):
   - Show three-way diff: old upstream, new upstream, local
   - Offer merge strategies:
     - "Accept upstream" -- Replace with new version
     - "Keep current" -- Preserve user version
     - "Smart merge" -- Agent proposes a merged version preserving user intent
   - Wait for user decision

**Deleted-upstream commands:**
- If a command file exists locally but was deleted upstream:
  - Unmodified locally: auto-delete, report "Removed: <filename>"
  - Modified locally: prompt user before deleting

**Exclusion:** `pl-edit-base.md` MUST NEVER be synced to consumer projects. Silently exclude it from all analysis and reports.

### 2.8 Config Sync

After init refresh, run the config resolver's `sync_config()` function:

1. Import `sync_config` from `tools/config/resolve_config.py`
2. Call `sync_config(project_root)` which:
   - If `config.local.json` doesn't exist, creates it as a copy of `config.json` (shared)
   - If `config.local.json` exists, walks `config.json` for missing keys and adds them with shared defaults
3. Display the sync result

This step runs unconditionally after every successful update.

### 2.9 Stale Artifact Cleanup

Check for legacy-named scripts at the consumer project root:
- `run_architect.sh` (renamed to `pl-run-architect.sh`)
- `run_builder.sh` (renamed to `pl-run-builder.sh`)
- `run_qa.sh` (renamed to `pl-run-qa.sh`)
- `purlin_init.sh` (renamed to `pl-init.sh`)
- `purlin_cdd_start.sh` (renamed to `pl-cdd-start.sh`)
- `purlin_cdd_stop.sh` (renamed to `pl-cdd-stop.sh`)

If any found, prompt to remove. If declined, print "Stale files preserved." Skip entirely
if none found. In `--dry-run` mode, list but do not delete.

### 2.10 Summary Report

After successful update, display a brief summary:

```
Purlin updated: <old_version> -> <new_version>
* N command files updated, M skipped (locally modified)
* Init refresh completed
* Config sync: <result>
```

If conflicts were resolved in Section 2.7, note them. If stale artifacts were cleaned, note them.

### 2.11 Dry Run Mode

When `--dry-run` is specified:
- Perform fetch and version check
- Run conflict scan
- Show what would be changed
- Do NOT modify any files, advance the submodule, or update `.purlin/.upstream_sha`

### 2.12 Project Root Detection

The skill uses `PURLIN_PROJECT_ROOT` (env var) for project root detection, with directory-climbing as fallback.

### 2.13 Customization Impact Analysis (Optional)

After the summary report (Section 2.10), the skill MUST offer an optional deep analysis of
how the update affects consumer-specific customizations. This step is entirely opt-in and
runs zero analysis unless accepted.

**Trigger:** After the summary report is displayed, prompt: "Would you like me to check if
this update affects your customizations?"

**Skip conditions:**
- `--auto-approve`: Skip the prompt entirely (automation contexts). Do not run analysis.
- User declines: Exit immediately. Do not run analysis.
- `--dry-run`: The prompt is still offered. Analysis is read-only and safe to run.

**If accepted, run all four dimensions:**

#### A. Override Header Drift

For each `.purlin/*_OVERRIDES.md` that exists in the consumer project, extract all `## `
headers referenced in the override content (e.g., section references, "see Section X" links).
Compare the referenced headers against the old and new upstream base files to detect stale
references where headers were renamed or removed.

Override-to-base mapping:

| Override file | Upstream base file |
|---|---|
| `HOW_WE_WORK_OVERRIDES.md` | `instructions/HOW_WE_WORK_BASE.md` |
| `ARCHITECT_OVERRIDES.md` | `instructions/ARCHITECT_BASE.md` |
| `BUILDER_OVERRIDES.md` | `instructions/BUILDER_BASE.md` |
| `QA_OVERRIDES.md` | `instructions/QA_BASE.md` |
| `PM_OVERRIDES.md` | `instructions/PM_BASE.md` |

For each mapping:
1. Retrieve old base: `git -C <submodule> show <old_sha>:instructions/<base_file>`
2. Retrieve new base: `git -C <submodule> show <new_sha>:instructions/<base_file>`
3. Extract `## ` headings from both versions
4. Identify headings present in old but absent in new (removed/renamed)
5. Cross-reference against the override file's content
6. Report any stale references found

#### B. Config Key Drift

Compare old vs new upstream `purlin-config-sample/config.json`:
1. Retrieve old config: `git -C <submodule> show <old_sha>:purlin-config-sample/config.json`
2. Retrieve new config: `git -C <submodule> show <new_sha>:purlin-config-sample/config.json`
3. Identify keys removed or renamed between old and new
4. Cross-reference against consumer's `.purlin/config.local.json`
5. Report orphaned keys (keys in local config that no longer exist upstream)
6. Note changed default values for existing keys

#### C. Command Behavioral Changes (Informational)

For locally modified command files where the user chose "Keep current" in Section 2.7 (or
where upstream changed without conflict), summarize what changed upstream between old and
new SHA. This is informational only -- no re-merge is offered.

1. For each qualifying file, diff old vs new upstream versions
2. Summarize the nature of the changes (new steps added, steps removed, behavioral shifts)
3. Present as an informational list

#### D. Feature Template Format Changes

If the feature file format section in `instructions/ARCHITECT_BASE.md` changed between old
and new SHA, report what shifted so the user can evaluate whether their existing feature
files need alignment.

1. Extract Section 10 ("Feature File Format") from old and new `ARCHITECT_BASE.md`
2. If content differs, summarize the changes
3. If no changes, omit this dimension from the report

**Output format:**
- Group findings by dimension (A through D)
- Omit dimensions that found no issues
- If all four dimensions are clean: "No customization impacts detected."

### 2.14 Regression Testing

Regression tests verify the update agent correctly handles submodule update scenarios.
- **Approach:** Agent behavior harness (`claude --print` with fixtures against external fixture repo)
- **Scenarios covered:** Clean update, conflict detection, dry-run mode
- **Fixture tags:** See Integration Test Fixture Tags section

### 2.15 MCP Manifest Diff

During the pre-update conflict scan (Section 2.4), the skill MUST also check if
`tools/mcp/manifest.json` changed between the old and new submodule SHA.

**Detection:**

1.  Run `git -C <submodule> diff-tree --no-commit-id --name-status -r <old_sha> <new_sha> -- tools/mcp/manifest.json` to detect manifest changes.
2.  If unchanged, skip this section entirely and produce no MCP-related output.

**If the manifest changed:**

1.  Read old manifest: `git -C <submodule> show <old_sha>:tools/mcp/manifest.json`
2.  Read new manifest from disk (after submodule advance in Section 2.5).
3.  Compute the diff between old and new server lists by `name`:
    *   **Added servers:** Present in new manifest but not in old. These are installed automatically by `init.sh` during the init refresh step (Section 2.6). The update skill reports them in the summary.
    *   **Removed servers:** Present in old manifest but not in new. Print an advisory: `"MCP server '<name>' was removed from Purlin manifest. Remove manually: claude mcp remove <name>"`. Do NOT auto-remove.
    *   **Changed servers:** Present in both but with different `transport`, `command`, `args`, or `url`. Print an advisory with reconfiguration command: `"MCP server '<name>' config changed upstream. Reconfigure: claude mcp remove <name> && <new add command>"`. Where `<new add command>` is the appropriate `claude mcp add` invocation for the new server entry.

**Restart notice:** If any MCP changes occurred (added, removed, or changed), append to the summary report (Section 2.10): `"Restart Claude Code to load MCP changes."`

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto-Fetch and Update When Behind
    Given the submodule's local HEAD is behind the remote tracking branch by 3 commits
    And .purlin/.upstream_sha contains the old SHA
    When /pl-update-purlin is invoked
    Then the skill fetches from the submodule's remote
    And displays current version, target version, and commit count
    And prompts for confirmation
    When the user confirms
    Then the submodule is advanced to the latest remote commit
    And init.sh --quiet is executed
    And config sync runs

#### Scenario: Already Up to Date
    Given the submodule's local HEAD matches the remote tracking branch
    And .purlin/.upstream_sha matches current HEAD
    When /pl-update-purlin is invoked
    Then "Already up to date." is printed
    And the skill exits successfully

#### Scenario: No Changes Since Last Sync
    Given .purlin/.upstream_sha matches the current submodule HEAD
    When /pl-update-purlin is invoked
    Then "Already up to date." is printed
    And the skill exits successfully

#### Scenario: Unmodified Command Files Auto-Updated
    Given pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md matches the old upstream version
    When /pl-update-purlin is invoked and update completes
    Then init.sh auto-copies pl-status.md from submodule
    And the report includes the updated file count

#### Scenario: Modified Command File with No Upstream Change
    Given the consumer modified .claude/commands/pl-status.md locally
    And upstream did NOT change pl-status.md between old and new SHA
    When /pl-update-purlin is invoked and update completes
    Then pl-status.md is preserved with local modifications
    And no merge prompt is shown

#### Scenario: Modified Command File with Upstream Conflict
    Given pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md has local modifications
    When /pl-update-purlin is invoked and update completes
    Then the skill shows a three-way diff (old upstream, new upstream, local)
    And offers merge strategies: "Accept upstream", "Keep current", "Smart merge"
    And waits for user decision

#### Scenario: Init Refresh Handles CDD Symlinks
    Given the submodule has been advanced to a newer commit
    When init.sh --quiet runs as part of the update
    Then pl-cdd-start.sh and pl-cdd-stop.sh are verified as correct symlinks
    And the skill does NOT directly read, compare, or modify these files

#### Scenario: Top-Level Script Updated Automatically
    Given pl-run-builder.sh changed upstream
    And the consumer's pl-run-builder.sh matches the old version
    When /pl-update-purlin is invoked
    Then init.sh regenerates pl-run-builder.sh

#### Scenario: Top-Level Script with Local Changes
    Given pl-run-builder.sh changed upstream
    And the consumer has modified pl-run-builder.sh locally
    When /pl-update-purlin is invoked
    Then the skill shows the diff between user changes and upstream changes
    And offers merge strategies
    And waits for user approval

#### Scenario: New Config Keys Added Upstream
    Given upstream added new config key "agents.architect.review_mode" in config.json
    And consumer's config.local.json doesn't have this key
    When /pl-update-purlin is invoked and the update completes
    Then the config sync step adds the new key to config.local.json with the shared default
    And the user is informed: "Added new config keys: agents.architect.review_mode"
    And existing local config values are preserved

#### Scenario: Stale Artifacts Detected and Cleaned
    Given the consumer project has run_builder.sh at the project root (legacy naming)
    And the current Purlin version expects pl-run-builder.sh instead
    When /pl-update-purlin completes the update
    Then the skill detects run_builder.sh as a stale artifact
    And prompts the user to remove it
    When the user confirms
    Then the stale file is deleted

#### Scenario: Dry Run Shows Changes Without Applying
    Given the submodule is behind the remote
    When /pl-update-purlin --dry-run is invoked
    Then the version difference is shown
    And locally modified files are identified
    But no files are modified
    And .purlin/.upstream_sha remains unchanged

#### Scenario: pl-edit-base.md Excluded from Sync
    Given pl-edit-base.md changed upstream
    When /pl-update-purlin is invoked
    Then pl-edit-base.md is silently excluded
    And does not appear in any reports or counts

#### Scenario: Unmodified Deleted-Upstream Command Auto-Removed
    Given pl-old-command.md exists in `.claude/commands/` and matches the old upstream version
    And the new upstream version no longer includes pl-old-command.md
    When /pl-update-purlin is invoked
    Then pl-old-command.md is auto-deleted from `.claude/commands/`
    And the report shows "Removed: pl-old-command.md"

#### Scenario: Modified Deleted-Upstream Command Requires Confirmation
    Given pl-old-command.md exists in `.claude/commands/` with local modifications
    And the new upstream version no longer includes pl-old-command.md
    When /pl-update-purlin is invoked
    Then the skill prompts the user before deleting
    When the user confirms
    Then pl-old-command.md is deleted

#### Scenario: Standalone Mode Guard Prevents Update in Purlin Repo
    Given the current project IS the Purlin repository (not a consumer project)
    And .purlin/.upstream_sha does not exist
    And purlin-config-sample/ exists at the project root
    When /pl-update-purlin is invoked
    Then the skill prints: "/pl-update-purlin is only for consumer projects using Purlin as a submodule."
    And the skill exits without making any changes

#### Scenario: Fast Path Completes Without Conflict Analysis
    Given the submodule is behind by 5 commits
    And no command files or launcher scripts have been locally modified
    When /pl-update-purlin is invoked and the user confirms
    Then the submodule is advanced
    And init.sh --quiet runs
    And config sync runs
    And the conflict resolution step (Section 2.7) is skipped entirely
    And the summary is displayed

#### Scenario: Diff-Tree Early Exit Skips Per-File Scan
    Given the submodule is behind by 2 commits
    And upstream changed zero files in .claude/commands/ and zero launcher-relevant paths
    When /pl-update-purlin runs the pre-update conflict scan
    Then git diff-tree is invoked once
    And no per-file git show comparisons are executed
    And the conflict scan completes with zero flagged files

#### Scenario: Diff-Tree Narrows Per-File Scan
    Given the submodule is behind by 5 commits
    And upstream changed 2 of 30 command files
    And the consumer has locally modified 3 command files
    When /pl-update-purlin runs the pre-update conflict scan
    Then only the 2 upstream-changed files are checked for local modifications
    And the remaining 28 command files are not compared

#### Scenario: Go-Deeper Offered After Summary
    Given the update completed successfully
    And the summary report has been displayed
    When the skill reaches the customization impact check
    Then it prompts: "Would you like me to check if this update affects your customizations?"

#### Scenario: Go-Deeper Skipped When Declined
    Given the update completed successfully
    And the go-deeper prompt is displayed
    When the user declines
    Then no override, config, command, or template analysis is performed
    And the skill exits

#### Scenario: Go-Deeper Skipped With Auto-Approve
    Given /pl-update-purlin is invoked with --auto-approve
    And the update completed successfully
    When the skill reaches the customization impact check
    Then the go-deeper prompt is not displayed
    And no impact analysis is performed

#### Scenario: Go-Deeper Detects Override Header Drift
    Given upstream renamed "## 7. Strategic Protocols" to "## 7. Operational Protocols" in ARCHITECT_BASE.md
    And the consumer's ARCHITECT_OVERRIDES.md references "Strategic Protocols"
    When the user accepts the go-deeper analysis
    Then the report includes a stale reference warning for ARCHITECT_OVERRIDES.md
    And identifies the renamed heading

#### Scenario: Go-Deeper Detects Orphaned Config Keys
    Given upstream removed the key "dashboard.legacy_mode" from purlin-config-sample/config.json
    And the consumer's config.local.json contains "dashboard.legacy_mode"
    When the user accepts the go-deeper analysis
    Then the report flags "dashboard.legacy_mode" as an orphaned key

#### Scenario: Go-Deeper Summarizes Skipped Command Changes
    Given the consumer kept their local version of pl-status.md during conflict resolution
    And upstream changed pl-status.md between old and new SHA
    When the user accepts the go-deeper analysis
    Then the report includes an informational summary of what changed upstream in pl-status.md

#### Scenario: Go-Deeper Available in Dry-Run Mode
    Given /pl-update-purlin is invoked with --dry-run
    And the dry-run summary has been displayed
    When the skill reaches the customization impact check
    Then it prompts the user for go-deeper analysis
    And analysis runs read-only if accepted

#### Scenario: Go-Deeper Reports No Impacts When Clean
    Given no overrides reference changed headers
    And no config keys were removed or renamed upstream
    And no command files were skipped or kept locally
    And the feature template format did not change
    When the user accepts the go-deeper analysis
    Then the report shows: "No customization impacts detected."

#### Scenario: New MCP Server Detected on Update

    Given the submodule is behind by 3 commits
    And the new upstream manifest adds a server "new-tool" not in the old manifest
    When /pl-update-purlin is invoked and the update completes
    Then init.sh installs "new-tool" during the refresh step
    And the summary report includes "new-tool" as a newly available MCP server
    And the summary includes "Restart Claude Code to load MCP changes."

#### Scenario: Removed MCP Server Generates Advisory

    Given the submodule is behind by 2 commits
    And the old manifest contains server "deprecated-tool" which is absent from the new manifest
    When /pl-update-purlin is invoked and the update completes
    Then the summary includes: "MCP server 'deprecated-tool' was removed from Purlin manifest. Remove manually: claude mcp remove deprecated-tool"
    And "deprecated-tool" is NOT auto-removed
    And the summary includes "Restart Claude Code to load MCP changes."

#### Scenario: Changed MCP Server Configuration Advisory

    Given the submodule is behind by 1 commit
    And server "playwright" exists in both old and new manifests
    And the new manifest changes playwright's args from ["@playwright/mcp"] to ["@playwright/mcp", "--headless"]
    When /pl-update-purlin is invoked and the update completes
    Then the summary includes an advisory that "playwright" config changed upstream
    And the advisory includes the reconfiguration command
    And the summary includes "Restart Claude Code to load MCP changes."

#### Scenario: No MCP Output When Manifest Unchanged

    Given the submodule is behind by 5 commits
    And tools/mcp/manifest.json is identical between old and new SHA
    When /pl-update-purlin is invoked and the update completes
    Then no MCP-related output appears in the summary
    And no "Restart Claude Code" notice is shown for MCP reasons

### Manual Scenarios (Human Verification Required)

#### Scenario: Complex Three-Way Merge
    Given a command file has been modified both upstream and locally in conflicting ways
    When /pl-update-purlin offers "Smart merge" option
    Then a human must verify the proposed merge preserves intended functionality

#### Scenario: Go-Deeper Override Drift Analysis Accuracy
    Given the consumer has multiple override files with various section references
    And upstream renamed or removed several headings across base files
    When the user accepts the go-deeper analysis
    Then a human must verify the reported stale references are accurate
    And confirm no false positives or missed references

---

## 4. Implementation Notes

### 4.1 Agent Context
The skill is implemented as a Claude Code slash command that:
1. Uses bash tools for git operations and file detection
2. Uses Read/Edit/Write tools for file manipulation
3. Uses AI reasoning for merge strategies (only when conflicts exist)
4. Uses interactive prompts for user decisions

### 4.2 Three-Way Diff Algorithm
For modified files:
1. `old_upstream = git show <old_sha>:<path>`
2. `new_upstream = git show HEAD:<path>`
3. `current_local = cat <consumer_path>`
4. Compare: if `current_local == old_upstream`, auto-update; else, offer merge

### 4.3 Performance Principle
The skill MUST minimize agent reasoning on the fast path. On the mandatory path (Sections 2.3 through 2.10):
- Use `git diff-tree` to identify upstream-changed files before scanning local files. If upstream changed zero tracked files, skip the conflict scan entirely.
- Do NOT analyze release notes or changelog content
- Do NOT compare override files against defaults
- Do NOT generate migration plans
- Do NOT scan instruction file headers for structural changes
- Let `init.sh` handle all mechanical file operations

Heavy analysis activates ONLY when the conflict scan (Section 2.4) flags files.

### 4.4 Go-Deeper Analysis Principle
Section 2.13 is the only place where override-vs-base comparison, header scanning, config
semantic analysis, and feature template format diffing occurs. These activities MUST NOT
appear in the mandatory fast path (Sections 2.3 through 2.10). The go-deeper analysis is
entirely opt-in and zero-cost when declined.

---

## 5. Future Enhancements

### 5.1 Auto-Test After Update
After update, optionally run `/pl-verify` to ensure system still works.

### 5.2 Update Notifications
Check for updates on startup and notify user if behind (non-blocking).

### 5.3 Version Pinning
Allow pinning to specific Purlin versions to prevent auto-updates.

### 5.4 Automatic Go-Deeper on Breaking Changes
When upstream includes a `BREAKING_CHANGES.md` file covering the update range, automatically
trigger the customization impact analysis (Section 2.13) without prompting. The breaking
changes file would serve as a signal that the update warrants deeper inspection.
