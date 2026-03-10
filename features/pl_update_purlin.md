# Feature: Intelligent Purlin Update Agent Skill

> Label: "/pl-update-purlin Intelligent Purlin Update"
> Category: "Agent Skills"
> Prerequisite: features/project_init.md
> Prerequisite: features/config_layering.md

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
2. For each `.claude/commands/pl-*.md` in consumer project (excluding `pl-edit-base.md`):
   - Compare local file against old upstream version: `git -C <submodule> show <old_sha>:.claude/commands/<file>`
   - If they differ, flag as "locally modified"
3. For each launcher script (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`):
   - If file content differs from what init.sh would have generated at the old version, flag

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

### Manual Scenarios (Human Verification Required)

#### Scenario: Complex Three-Way Merge
    Given a command file has been modified both upstream and locally in conflicting ways
    When /pl-update-purlin offers "Smart merge" option
    Then a human must verify the proposed merge preserves intended functionality

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
The skill MUST minimize agent reasoning on the fast path. When no conflicts exist:
- Do NOT analyze release notes or changelog content
- Do NOT compare override files against defaults
- Do NOT generate migration plans
- Do NOT scan instruction file headers for structural changes
- Let `init.sh` handle all mechanical file operations

Heavy analysis activates ONLY when the conflict scan (Section 2.4) flags files.

---

## 5. Future Enhancements

### 5.1 Auto-Test After Update
After update, optionally run `/pl-verify` to ensure system still works.

### 5.2 Update Notifications
Check for updates on startup and notify user if behind (non-blocking).

### 5.3 Version Pinning
Allow pinning to specific Purlin versions to prevent auto-updates.
