**Purlin command: shared (all roles)**

**Intelligent Purlin Update**

Update the Purlin submodule to the latest version with automatic artifact refresh and conflict detection.

**Behavior:**

0. **Standalone Mode Guard:**
   - Before any work, check if this is the Purlin repository itself (not a consumer project)
   - Detection: `.purlin/.upstream_sha` does not exist AND `purlin-config-sample/` exists at the project root
   - If both true, print: `/pl-update-purlin is only for consumer projects using Purlin as a submodule.` and exit

1. **Fetch and Version Check:**
   - Run `git -C <submodule_dir> fetch --tags`
   - Compare local submodule HEAD against remote tracking branch (`origin/main`)
   - If already current AND `.purlin/.upstream_sha` matches HEAD: print "Already up to date." and exit
   - If behind: show current version -> target version (from `git describe --tags --abbrev=0`) and commit count
   - Prompt: "Update to <version>? (y/n)" (skip if `--auto-approve`)

2. **Pre-Update Conflict Scan:**
   - Read old SHA from `.purlin/.upstream_sha`
   - First, run `git -C <submodule> diff-tree --no-commit-id --name-status -r <old_sha> <new_sha> -- .claude/commands/` to identify which command files changed upstream (single invocation). Also check launcher-relevant paths (e.g., `tools/init.sh`).
   - **If no command files or launcher scripts changed upstream, skip the remainder of this step** -- no local modifications can conflict.
   - For files that appear in BOTH the consumer project AND the diff-tree output (excluding `pl-edit-base.md` which is NEVER synced to consumer projects):
     - Compare local file against old upstream version (`git -C <submodule> show <old_sha>:.claude/commands/<file>`)
     - If they differ, flag as "locally modified" for post-update merge
   - For each launcher script (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`):
     - Only check if launcher-relevant paths appeared in the diff-tree output
     - If file content differs from what init.sh would have generated at the old version, flag as "locally modified"
   - **IMPORTANT: `pl-cdd-start.sh` and `pl-cdd-stop.sh` are SYMLINKS managed exclusively by init.sh. NEVER read, compare, copy, or modify these files. They are refreshed automatically by the init step (step 4).**

3. **Advance Submodule:**
   - `git -C <submodule_dir> checkout <remote_sha>` (detached HEAD)
   - If this fails, abort with error

4. **Init Refresh:**
   - Run `<submodule>/tools/init.sh --quiet` to refresh all project-root artifacts
   - This handles: command files (unmodified ones auto-copied), CDD symlinks, launcher scripts, shim (`pl-init.sh`), and `.purlin/.upstream_sha`
   - Init's timestamp logic preserves locally modified command files — conflict resolution happens in step 5

5. **Conflict Resolution (only if step 2 found locally modified files):**
   - For each flagged command file where upstream ALSO changed the file:
     - Show three-way diff: old upstream, new upstream, local
     - Offer: "Accept upstream", "Keep current", or "Smart merge"
   - For each flagged command file where upstream did NOT change: no action needed
   - For each flagged launcher script: same three-way approach
   - **Deleted-upstream commands** (file no longer in upstream):
     - Unmodified locally: auto-delete, report "Removed: <filename>"
     - Modified locally: prompt user before deleting, preserve if declined
   - **Skip this step entirely if no conflicts were flagged** — do not scan or analyze files unnecessarily

6. **Config Sync:**
   - Run `sync_config()` from `tools/config/resolve_config.py`
   - If `config.local.json` doesn't exist, creates it from `config.json`; otherwise adds missing keys with shared defaults
   - Reports new keys added or "Local config is up to date"

7. **Stale Artifact Cleanup:**
   - Check for legacy-named scripts at project root (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`, `purlin_init.sh`, `purlin_cdd_start.sh`, `purlin_cdd_stop.sh`)
   - If found, prompt: "Remove these files? You can remove them manually later if you prefer."
   - In `--dry-run` mode, list stale artifacts but do not delete

8. **Summary:**
   ```
   Purlin updated: <old_version> -> <new_version>
   * N command files updated, M skipped (locally modified)
   * Init refresh completed
   * Config sync: <result>
   ```

9. **Customization Impact Check (Optional):**
   - **Skip entirely if `--auto-approve`** -- do not prompt or analyze.
   - Prompt: "Would you like me to check if this update affects your customizations?"
   - If declined, exit. If accepted, run all four sub-steps:
   - **(a) Override Header Drift:** For each `.purlin/*_OVERRIDES.md`, extract `## ` headers referenced in the override content. Compare against the old and new upstream base files (mapping: `HOW_WE_WORK_OVERRIDES.md` -> `instructions/HOW_WE_WORK_BASE.md`, `ARCHITECT_OVERRIDES.md` -> `instructions/ARCHITECT_BASE.md`, `BUILDER_OVERRIDES.md` -> `instructions/BUILDER_BASE.md`, `QA_OVERRIDES.md` -> `instructions/QA_BASE.md`, `PM_OVERRIDES.md` -> `instructions/PM_BASE.md`). Report stale references where headings were renamed or removed upstream.
   - **(b) Config Key Drift:** Compare old vs new upstream `purlin-config-sample/config.json`. Report keys removed/renamed upstream that still exist in consumer's `.purlin/config.local.json` (orphaned keys). Note changed defaults.
   - **(c) Command Behavioral Changes:** For locally modified command files where the user chose "Keep current" (or where upstream changed without conflict), summarize what changed upstream. Informational only -- no re-merge offered.
   - **(d) Feature Template Format Changes:** If Section 10 ("Feature File Format") in `instructions/ARCHITECT_BASE.md` changed between old and new SHA, report what shifted.
   - **Output:** Group findings by category (a-d). Omit categories with no issues. If all clean: "No customization impacts detected."
   - This step is safe in `--dry-run` mode (read-only analysis).

**Options:**
- `--dry-run`: Show what would change without modifying files
- `--auto-approve`: Skip confirmation prompts for non-conflicting changes

**Example usage:**
```
/pl-update-purlin
/pl-update-purlin --dry-run
```

**Implementation:** See `features/pl_update_purlin.md`
