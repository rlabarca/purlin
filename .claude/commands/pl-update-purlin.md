**Purlin command: shared (all roles)**

**Intelligent Purlin Update**

Update the Purlin submodule with semantic change analysis, smart conflict resolution, and preservation of user customizations.

**Behavior:**

0. **Standalone Mode Guard:**
   - Before any other work, check if this is the Purlin repository itself (not a consumer project)
   - Detection: `.purlin/.upstream_sha` does not exist AND `purlin-config-sample/` exists at the project root
   - If both conditions are true, print: `/pl-update-purlin is only for consumer projects using Purlin as a submodule.`
   - Exit immediately without making any changes

1. **Fetch and Check Remote:**
   - Run `git -C <submodule_dir> fetch --tags` to retrieve latest upstream commits and release tags
   - Compare local submodule HEAD against remote tracking branch
   - If already current: skip to SHA comparison check
   - If behind: proceed to release analysis

2. **Release Analysis:**
   - Detect current version from git tags: `git describe --tags --abbrev=0 HEAD`
   - Detect target version: `git describe --tags --abbrev=0 origin/main`
   - List all releases between current and target
   - For each release: show version, date, and 3-5 key changes
   - Example output:
     ```
     === Purlin Updates Available ===
     Current version: v0.6.0
     Latest version:  v0.8.0

     --- Release: v0.7.0 (2026-02-26) ---
     • Remote collaboration via collab sessions
     • Spec Map enhancements
     • Auto-fetch upstream sync
     • 5 other changes

     --- Release: v0.8.0 (2026-02-27) ---
     • Intelligent agent-based sync
     • Smart conflict resolution
     • 3 other changes

     Total: 2 releases, 15 commits
     ```

3. **User Modification Detection:**
   - Scan `.purlin/config.json` for changed values vs. defaults
   - Check override files for custom content
   - Check top-level scripts for modifications
   - Check command files for local changes
   - Report all customizations:
     ```
     === Your Customizations ===

     Configuration (.purlin/config.json):
       • cdd_port: 8086 → 9000
       • architect.model: "sonnet-4-5" → "opus-4"

     Overrides:
       ✓ ARCHITECT_OVERRIDES.md: 45 lines of custom rules
       ✓ QA_OVERRIDES.md: 12 lines of custom rules

     Scripts:
       ⚠ pl-run-builder.sh: Modified (custom setup)

     Commands:
       ⚠ pl-status.md: Modified
     ```

4. **Preservation Strategy Preview:**
   - Show what will be preserved (overrides, config values, modified files)
   - Show what will be auto-updated (base files, tools, unmodified files)
   - Show what will require review (modified scripts/commands with conflicts)
   - List new config keys that will be added with defaults
   - Prompt: "Continue with update? (y/n)"

5. **SHA Comparison:**
   - Read old SHA from `.purlin/.upstream_sha`
   - If old SHA equals current SHA: print "Already up to date" and exit
   - Otherwise, proceed with intelligent analysis

6. **Update Execution:**
   - If user confirmed, advance submodule to latest version
   - Proceed with intelligent change analysis

7. **Intelligent Change Analysis:**
   - **Instruction changes:** Detect structural changes (section headers), flag impacts on overrides
   - **Tool changes:** Identify new/modified/deprecated tools, flag breaking changes
   - **Command file changes:** For each changed `.claude/commands/*.md`:
     - Unmodified files: auto-copy
     - Modified files: show three-way diff (old upstream, new upstream, local), offer merge strategies
     - New files: auto-copy
     - Deleted upstream (unmodified locally): auto-delete, report "Removed: <filename> (no longer in upstream)"
     - Deleted upstream (modified locally): show local modifications, prompt user; delete on confirmation or preserve with warning
     - **pl-edit-base.md is NEVER synced** (silently excluded)
   - **Top-level script changes:** Check for both current naming (`pl-run-*.sh`, `pl-init.sh`, `pl-cdd-*.sh`) AND legacy naming (`run_*.sh`, `purlin_init.sh`, `purlin_cdd_*.sh`). If legacy-named scripts exist at the project root without current-named equivalents, generate current-named replacements. Port user modifications from legacy scripts to new-named versions if present (use merge strategies from step 8). Track and update `pl-run-builder.sh`, `pl-run-architect.sh`, `pl-run-qa.sh`
     - If user modified: show diff, offer merge strategies
     - If unmodified: auto-update
   - **.purlin/ folder intelligence:**
     - Detect structural changes affecting overrides
     - Suggest updates to override files when base structure changes
     - After update, run `sync_config()` to add new keys from `config.json` (shared) to `config.local.json` (local) without overwriting existing values
     - Warn if deprecated keys found in user's local config

8. **Merge Strategies (for conflicts):**
   - "Accept upstream" - Replace with new version
   - "Keep current" - Preserve user version
   - "Smart merge" - AI proposes merged version preserving user intent
   - "Manual merge" - Mark for manual resolution

9. **Structural Change Migration Plan:**
   - For breaking changes, generate `.purlin/migration_plan_<timestamp>.md`
   - **Structural change detection:** Compare markdown section headers (`## `, `### `) between old and new upstream instruction files. When headers are renamed, removed, or restructured, scan all `.purlin/*_OVERRIDES.md` files for references to the changed section names.
   - If an override file references a renamed or removed section header, warn: `"⚠ <override_file> references changed section '<old_header>'"` and suggest specific line updates showing the old → new header name.
   - Include in the migration plan: breaking changes with affected files and line numbers, recommended updates, and commands to verify

10. **Atomic Update:**
   - Validate all planned changes first
   - Create backup (git stash if needed)
   - Apply all changes
   - If any step fails, rollback
   - Update `.purlin/.upstream_sha` only on success

11. **Post-Update Init Refresh:**
   - After the atomic update completes successfully, run `tools/init.sh --quiet` to refresh all project-root artifacts
   - This refreshes: command files (new/updated `.claude/commands/pl-*.md`), CDD convenience symlinks, project-root shim (`pl-init.sh`), and `.purlin/.upstream_sha`
   - Init's timestamp logic preserves locally modified files — the three-way diff in step 7 handles content conflicts for modified files
   - Note in the summary report that init/refresh ran (e.g., "Init refresh completed")

12. **Config Sync After Update:**
   - After init refresh completes, run the config resolver's `sync_config()` function
   - Execute: `python3 -c "from tools.config.resolve_config import sync_config; added = sync_config('<project_root>'); print('Added new config keys: ' + ', '.join(added) if added else 'Local config is up to date')"` (adjust path for submodule layout)
   - If `config.local.json` doesn't exist, `sync_config()` creates it as a copy of `config.json` (shared) and reports: "Created config.local.json from team defaults"
   - If `config.local.json` exists, walks `config.json` for missing keys, adds them with shared defaults
   - Display the sync result in the update summary
   - This step runs unconditionally after every successful update

13. **Stale Artifact Cleanup:**
   - After update, detect artifacts from previous Purlin versions that are no longer needed
   - Detection targets the **consumer project root** only; files inside the submodule directory are managed by git and are never candidates for stale artifact cleanup
   - Compare files installed by the old version against what the new version expects; identify orphaned artifacts
   - Known stale artifacts (all at project root):
     - `run_architect.sh` (renamed to `pl-run-architect.sh`)
     - `run_builder.sh` (renamed to `pl-run-builder.sh`)
     - `run_qa.sh` (renamed to `pl-run-qa.sh`)
     - `purlin_init.sh` (renamed to `pl-init.sh`)
     - `purlin_cdd_start.sh` (renamed to `pl-cdd-start.sh`)
     - `purlin_cdd_stop.sh` (renamed to `pl-cdd-stop.sh`)
   - Report format:
     ```
     Stale artifacts detected from previous Purlin version:
       • run_builder.sh (renamed to pl-run-builder.sh)
       • <other stale file> (<reason>)

     Remove these files? (y/n)
     ```
   - Always prompt before deleting; if confirmed, remove and report each deletion
   - If declined: "Stale files preserved — you can remove them manually later."
   - In `--dry-run` mode: list stale artifacts but do not delete

14. **Summary Report:**
   ```
   === Purlin Update Complete ===

   Updated: <old_sha> → <new_sha>

   Changes Applied:
     ✓ Init refresh completed
     ✓ 3 command files updated
     ✓ 1 new command added
     ✓ pl-run-builder.sh updated
     ⚠ 2 files require manual review

   Migration Plan: .purlin/migration_plan_<timestamp>.md
   ```

**Options:**
- `--dry-run`: Show what would change without modifying files; list stale artifacts but do not delete
- `--auto-approve`: Skip confirmation prompts for non-conflicting changes

**Example usage:**
```
/pl-update-purlin
/pl-update-purlin --dry-run
```

**Implementation:** See `features/pl_update_purlin.md`
