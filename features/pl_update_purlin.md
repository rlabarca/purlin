# Feature: Intelligent Purlin Update Agent Skill

> Label: "/pl-update-purlin: Intelligent Purlin Update"
> Category: "Agent Skills"
> Prerequisite: features/submodule_bootstrap.md

## 1. Overview

The `/pl-update-purlin` agent skill provides intelligent synchronization of the Purlin submodule to consumer projects. Unlike the previous script-based approach, this agent skill uses AI to understand changes semantically, preserve user customizations, intelligently merge conflicts, and provide migration guidance for structural changes.

This skill replaces `tools/sync_upstream.sh` with a smarter, interactive approach that:
- Analyzes upstream changes semantically (not just textually)
- Preserves user customizations in `.purlin/` overrides
- Tracks and updates top-level scripts (`run_builder.sh`, launcher scripts, etc.)
- Provides migration plans for breaking changes
- Handles multi-file updates atomically
- Offers context-aware merge strategies

---

## 2. Requirements

### 2.1 Command Interface

```
/pl-update-purlin [--dry-run] [--auto-approve]
```

- **--dry-run** (optional): Show what would be updated without making changes
- **--auto-approve** (optional): Skip confirmation prompts for non-conflicting changes (conflicts still require approval)

### 2.2 Auto-Fetch and Remote Check

The skill MUST:
1. Run `git -C <submodule_dir> fetch --tags` to retrieve latest upstream commits and tags
2. Compare local submodule HEAD against remote tracking branch (e.g., `origin/main`)
3. Determine how many commits behind the local submodule is
4. If already current with remote, proceed directly to local sync check (Section 2.3)
5. If behind:
   - Proceed to release analysis (Section 2.2.1)
   - Then to user modification detection (Section 2.2.2)
   - Display update preview (Section 2.2.3)
   - Prompt for confirmation
6. If user confirms:
   - Advance submodule to latest (detached HEAD: checkout remote SHA; branch: merge --ff-only)
   - Proceed to intelligent analysis (Section 2.4)
7. If user declines:
   - Print "Skipping update. You can run sync again later."
   - Exit gracefully

#### 2.2.1 GitHub Release Analysis

The skill MUST analyze GitHub releases between current and target versions:

1. **Current Version Detection:**
   - Read current submodule HEAD SHA
   - Find the most recent git tag at or before current HEAD: `git -C <submodule_dir> describe --tags --abbrev=0 HEAD`
   - If no tag found, use "v0.0.0" as baseline

2. **Target Version Detection:**
   - Get latest remote HEAD SHA
   - Find most recent tag at or before remote HEAD: `git -C <submodule_dir> describe --tags --abbrev=0 origin/main`
   - This is the target version

3. **Release List Retrieval:**
   - Get all tags between current and target: `git -C <submodule_dir> tag --merged origin/main --no-merged HEAD --sort=-version:refname`
   - For each tag in chronological order (oldest to newest):
     - Extract version number (e.g., "v0.7.0" from tag name)
     - Fetch release notes from GitHub API or parse from annotated tag message

4. **Release Summary Display:**
   Display in this format:
   ```
   === Purlin Updates Available ===

   Current version: v0.6.0
   Latest version:  v0.8.0

   --- Release: v0.7.0 (2026-02-26) ---
   • Remote collaboration via collab sessions
   • Spec Map enhancements with topological ordering
   • Auto-fetch and update prompt for upstream sync
   • 5 other changes

   --- Release: v0.8.0 (2026-02-27) ---
   • Intelligent agent-based upstream sync (/pl-update-purlin)
   • Enhanced conflict resolution with smart merge
   • 3 other changes

   Total: 2 releases, X commits
   ```

5. **Release Notes Parsing:**
   - If GitHub API is available (via `gh` CLI), fetch release notes: `gh release view <tag> --repo <owner/repo> --json body`
   - Otherwise, parse from annotated tag: `git -C <submodule_dir> tag -l --format='%(contents)' <tag>`
   - Summarize to 3-5 key bullet points per release, truncate if longer

#### 2.2.2 User Modification Detection

The skill MUST detect and report ALL user customizations:

1. **`.purlin/` Folder Analysis:**
   - For each file in `.purlin/`:
     - **Override files** (`*_OVERRIDES.md`):
       - Check if file is non-empty (has content beyond template comments)
       - If customized, report: "Has custom rules (N lines added)"
     - **config.json**:
       - Compare against original from `purlin-config-sample/config.json`
       - Report changed keys with old → new values
       - Example: `"cdd_port": 8086 → 9000`, `"architect.model": "claude-sonnet-4-5" → "claude-opus-4"`
     - **.upstream_sha**:
       - Always report current SHA (no modification check needed)

2. **Top-Level Scripts Analysis:**
   - For each tracked script (`run_builder.sh`, `run_architect.sh`, `run_qa.sh`):
     - Compare against what bootstrap.sh would have generated at current submodule version
     - If differs, report: "Modified: <script> (custom logic added)"

3. **Command Files Analysis:**
   - For each `.claude/commands/pl-*.md` in consumer project:
     - Compare against submodule version at current SHA
     - If differs, report: "Modified: pl-<name>.md"

4. **Modification Report Format:**
   ```
   === Your Customizations ===

   Configuration (.purlin/config.json):
     • cdd_port: 8086 → 9000
     • architect.model: "claude-sonnet-4-5" → "claude-opus-4"
     • builder.effort: "medium" → "high"

   Overrides:
     ✓ ARCHITECT_OVERRIDES.md: 45 lines of custom rules
     ✓ BUILDER_OVERRIDES.md: Empty (no customizations)
     ✓ QA_OVERRIDES.md: 12 lines of custom rules
     ✓ HOW_WE_WORK_OVERRIDES.md: 23 lines of custom workflow

   Scripts:
     ⚠ run_builder.sh: Modified (custom environment setup)

   Commands:
     ⚠ pl-status.md: Modified (custom output format)
   ```

#### 2.2.3 Preservation Strategy Preview

After displaying modifications, the skill MUST show what will be preserved vs. changed:

```
=== Update Strategy ===

Will be PRESERVED:
  ✓ All override files (.purlin/*_OVERRIDES.md)
  ✓ Custom config values in .purlin/config.json
  ✓ Modified command files (you'll be prompted to merge)
  ✓ Modified top-level scripts (you'll be prompted to merge)

Will be UPDATED:
  → Base instruction files (purlin/instructions/*)
  → Purlin tools (purlin/tools/*)
  → Unmodified command files
  → Unmodified top-level scripts

Will REQUIRE REVIEW:
  ⚠ run_builder.sh (modified) - merge strategies will be offered
  ⚠ pl-status.md (modified) - merge strategies will be offered

New config keys from upstream:
  + architect.review_mode: false (default will be added)
  + builder.auto_test: true (default will be added)
```

Then prompt:
```
Continue with update? (y/n)
```

### 2.3 SHA Comparison and Early Exit

The skill MUST:
1. Read old SHA from `.purlin/.upstream_sha`
2. If file missing, print error and exit (project not bootstrapped)
3. Read current submodule HEAD SHA
4. If old SHA equals current SHA:
   - Print "Already up to date — no changes since last sync."
   - Exit successfully (no further work needed)

### 2.4 Intelligent Change Analysis

When changes exist between old and current SHA, the skill MUST analyze:

#### 2.4.1 Instruction Changes
- Detect changes in `instructions/` directory
- Identify structural changes (section headers modified/removed)
- Flag changes that might affect user overrides
- Summarize semantic impact (new sections, removed features, restructured content)

#### 2.4.2 Tool Changes
- Detect changes in `tools/` directory
- Identify new tools, modified tools, deprecated tools
- Flag breaking changes to tool interfaces

#### 2.4.3 Command File Changes
- Detect changes in `.claude/commands/` directory
- **Exclusion**: `pl-edit-base.md` MUST NEVER be synced to consumer projects
- For each changed/new command file:
  - **Unmodified files**: Auto-copy and report `Updated: <filename>`
  - **Modified files**: Analyze the diff, offer merge strategies, require user approval
  - **New files**: Auto-copy and report `Added: <filename> (new command)`
  - **Deleted upstream**: Report `DELETED upstream: <filename> (manual cleanup may be required)`

#### 2.4.4 Top-Level Script Changes
The skill MUST track and intelligently update these files:
- `run_builder.sh`
- `run_architect.sh`
- `run_qa.sh`
- Any launcher scripts in project root

For each changed top-level script:
1. Compare current version against what was at old SHA
2. If user has local modifications:
   - Show diff of user changes vs. upstream changes
   - Offer merge strategies: "overwrite", "keep local", "manual merge"
   - Require user approval
3. If unmodified: auto-update and report

#### 2.4.5 `.purlin/` Folder Intelligence
The skill MUST preserve user customizations in:
- `.purlin/ARCHITECT_OVERRIDES.md`
- `.purlin/BUILDER_OVERRIDES.md`
- `.purlin/QA_OVERRIDES.md`
- `.purlin/HOW_WE_WORK_OVERRIDES.md`
- `.purlin/config.json`

**Strategy:**
1. Check if upstream base instructions changed in ways that affect overrides
2. If structural changes detected (e.g., section headers renamed):
   - Analyze user overrides to see if they reference the changed sections
   - Suggest updates to override files to match new structure
   - Provide migration guidance
3. For `config.json`:
   - Check if new keys added upstream
   - Offer to merge new keys while preserving user values
   - Warn if deprecated keys found in user config

### 2.5 Interactive Merge Strategies

When conflicts or complex changes are detected, the skill offers:

1. **Three-way merge view**: Show old upstream, new upstream, and current user version
2. **Merge options**:
   - "Accept upstream" — Replace with new version
   - "Keep current" — Preserve user version
   - "Manual merge" — Open files for user to merge manually
   - "Smart merge" — Agent proposes a merged version preserving user intent

### 2.6 Migration Plan Generation

For breaking changes, the skill generates a migration plan:

```markdown
## Migration Plan: Purlin Update <old_sha>..<new_sha>

### Breaking Changes
1. Section "Workflow Rules" renamed to "Process Guidelines" in HOW_WE_WORK.md
   - Action: Update ARCHITECT_OVERRIDES.md references
   - Files affected: .purlin/ARCHITECT_OVERRIDES.md line 42

2. Tool `validate.sh` signature changed: new --strict flag required
   - Action: Update calls in custom scripts
   - Files affected: custom_validation.sh

### Recommended Updates
...
```

### 2.7 Atomic Update Execution

All changes MUST be applied atomically:
1. Validate all planned changes first
2. Create backup of current state (git stash if needed)
3. Apply all changes
4. If any step fails, rollback to backup
5. Update `.purlin/.upstream_sha` only after all changes succeed

### 2.8 Update Summary Report

After successful update, display:

```
=== Purlin Update Complete ===

Updated: <old_sha_short> → <new_sha_short>

Changes Applied:
  ✓ 3 command files updated
  ✓ 1 new command added (pl-new-feature.md)
  ✓ run_builder.sh updated
  ⚠ 2 files require manual review:
    - .purlin/ARCHITECT_OVERRIDES.md (structural changes detected)
    - custom_script.sh (breaking tool signature change)

Migration Plan: .purlin/migration_plan_<timestamp>.md

Next Steps:
  1. Review migration plan: cat .purlin/migration_plan_<timestamp>.md
  2. Update affected override files
  3. Test changes with: /pl-verify
```

### 2.9 Dry Run Mode

When `--dry-run` is specified:
- Perform all analysis
- Show what would be changed
- Display migration plan
- Do NOT modify any files
- Do NOT update `.purlin/.upstream_sha`

### 2.10 Project Root Detection

The skill uses the same project root detection as `sync_upstream.sh`:
- Climb from script location through submodule directory to parent project

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto-Fetch and Update When Behind
    Given the submodule's local HEAD is behind the remote tracking branch by 3 commits
    And .purlin/.upstream_sha contains the old SHA
    When /pl-update-purlin is invoked
    Then the skill fetches from the submodule's remote
    And displays "Submodule is 3 commit(s) behind remote. Update to latest? (y/n)"
    When the user confirms
    Then the submodule is advanced to the latest remote commit
    And intelligent change analysis begins

#### Scenario: Already Up to Date with Remote
    Given the submodule's local HEAD matches the remote tracking branch
    And .purlin/.upstream_sha differs from current HEAD
    When /pl-update-purlin is invoked
    Then "Submodule is up to date with remote." is printed
    And intelligent change analysis proceeds

#### Scenario: No Changes Since Last Sync
    Given .purlin/.upstream_sha matches the current submodule HEAD
    When /pl-update-purlin is invoked
    Then "Already up to date — no changes since last sync." is printed
    And the skill exits successfully

#### Scenario: Unmodified Command Files Auto-Updated
    Given pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md matches the old version
    When /pl-update-purlin is invoked
    Then pl-status.md is auto-copied from submodule
    And the report shows "✓ Updated: pl-status.md"

#### Scenario: Modified Command File Requires Review
    Given pl-status.md changed upstream
    And the consumer's .claude/commands/pl-status.md has local modifications
    When /pl-update-purlin is invoked
    Then the skill shows a three-way diff (old upstream, new upstream, local)
    And offers merge strategies: "Accept upstream", "Keep current", "Smart merge"
    And waits for user decision

#### Scenario: Top-Level Script Updated Automatically
    Given run_builder.sh changed upstream
    And the consumer's run_builder.sh matches the old version
    When /pl-update-purlin is invoked
    Then run_builder.sh is auto-updated
    And the report shows "✓ run_builder.sh updated"

#### Scenario: Top-Level Script with Local Changes
    Given run_builder.sh changed upstream
    And the consumer has modified run_builder.sh locally
    When /pl-update-purlin is invoked
    Then the skill shows the diff between user changes and upstream changes
    And offers merge strategies
    And waits for user approval

#### Scenario: Structural Change Migration Plan
    Given upstream renamed section "Workflow Rules" to "Process Guidelines" in HOW_WE_WORK.md
    And .purlin/ARCHITECT_OVERRIDES.md references "Workflow Rules"
    When /pl-update-purlin is invoked
    Then the skill detects the structural change
    And generates a migration plan
    And warns: "⚠ .purlin/ARCHITECT_OVERRIDES.md references changed section"
    And suggests specific line updates

#### Scenario: New Config Keys Added Upstream
    Given upstream added new config key "agents.architect.review_mode"
    And consumer's .purlin/config.json doesn't have this key
    When /pl-update-purlin is invoked
    Then the skill offers: "Add new config key 'review_mode' with default value? (y/n)"
    When user confirms
    Then config.json is updated with the new key preserving all user values

#### Scenario: Dry Run Shows Changes Without Applying
    Given multiple changes exist upstream
    When /pl-update-purlin --dry-run is invoked
    Then all changes are analyzed and displayed
    And a migration plan is shown
    But no files are modified
    And .purlin/.upstream_sha remains unchanged

#### Scenario: pl-edit-base.md Excluded from Sync
    Given pl-edit-base.md changed upstream
    When /pl-update-purlin is invoked
    Then pl-edit-base.md is silently excluded
    And does not appear in any reports or counts

### Manual Scenarios (Human Verification Required)

#### Scenario: Complex Three-Way Merge
    Given a command file has been modified both upstream and locally in conflicting ways
    When /pl-update-purlin offers "Smart merge" option
    Then a human must verify the proposed merge preserves intended functionality

#### Scenario: Breaking Tool Signature Changes
    Given a tool's command-line interface changed in a breaking way
    When migration plan suggests updating custom scripts
    Then a human must verify all custom scripts are updated correctly

---

## 4. Implementation Notes

### 4.1 Agent Context
The skill is implemented as a Claude Code slash command that:
1. Uses bash tools for git operations and file detection
2. Uses Read/Edit/Write tools for file manipulation
3. Uses AI reasoning to analyze semantic changes and generate merge strategies
4. Uses interactive prompts for user decisions

### 4.2 Change Detection Strategy
- Use `git diff --name-status <old_sha>..HEAD` to find all changed files
- For each file category (instructions, tools, commands, scripts), analyze changes separately
- Track files in top-level project root that came from Purlin (need a manifest or naming convention)

### 4.3 Three-Way Diff Algorithm
For modified files:
1. `old_upstream = git show <old_sha>:<path>`
2. `new_upstream = git show HEAD:<path>`
3. `current_local = cat <consumer_path>`
4. Compare: if `current_local == old_upstream`, auto-update; else, offer merge

### 4.4 Structural Change Detection
- For instruction files, track markdown headers (`## `, `### `)
- If headers changed, scan override files for references (simple grep)
- Flag potential breakage and suggest updates

### 4.5 Top-Level File Tracking
Create `.purlin/.tracked_files` manifest listing files synced to project root:
```
run_builder.sh
run_architect.sh
run_qa.sh
```
The skill updates this manifest on each sync.

### 4.6 Rollback Strategy
Before applying changes:
```bash
git stash push -u -m "pre-purlin-update-backup-$(date +%s)"
```
If any operation fails:
```bash
git stash pop
```

### 4.7 Migration Plan Format
Migration plans are saved to `.purlin/migration_plan_<timestamp>.md` with:
- Summary of breaking changes
- Line-by-line update suggestions
- Commands to run for verification
- Links to upstream commit diffs

---

## 5. Future Enhancements

### 5.1 Auto-Test After Update
After update, optionally run `/pl-verify` to ensure system still works.

### 5.2 Update Notifications
Check for updates on startup and notify user if behind (non-blocking).

### 5.3 Version Pinning
Allow pinning to specific Purlin versions to prevent auto-updates.

### 5.4 Conflict Resolution Learning
Learn from user merge decisions to improve future smart merge suggestions.
