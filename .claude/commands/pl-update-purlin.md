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
   - For each `.claude/commands/pl-*.md` in consumer project (excluding `pl-edit-base.md` which is NEVER synced to consumer projects):
     - Compare local file against old upstream version (`git -C <submodule> show <old_sha>:.claude/commands/<file>`)
     - If they differ, flag as "locally modified" for post-update merge
   - For each launcher script (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`):
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

**Options:**
- `--dry-run`: Show what would change without modifying files
- `--auto-approve`: Skip confirmation prompts for non-conflicting changes

**Example usage:**
```
/pl-update-purlin
/pl-update-purlin --dry-run
```

**Implementation:** See `features/pl_update_purlin.md`
