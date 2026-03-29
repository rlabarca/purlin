---
name: update
description: Available to all agents and modes
---

**Purlin command: shared (all roles)**
**Purlin mode: shared**

Available to all agents and modes.

**Intelligent Purlin Update**

Update the Purlin submodule to the latest release tag (or a specified version) with automatic artifact refresh and conflict detection.

**Path Resolution:**

Resolve the project root:
- Use `PURLIN_PROJECT_ROOT` env var if set and `.purlin/` exists there.
- Otherwise, detect from the current working directory by climbing until `.purlin/` is found.

Set `<project_root>` to the resolved path. The submodule directory is `<project_root>/purlin` (or the configured submodule path). All paths below (`.purlin/`, `purlin-config-sample/`, launcher scripts, etc.) are relative to `<project_root>`.

> **Output standards:** See `${CLAUDE_PLUGIN_ROOT}/references/output_standards.md`.

**Behavior:**

0. **Standalone Mode Guard:**
   - Before any work, check if this is the Purlin repository itself (not a consumer project)
   - Detection: `.purlin/.upstream_sha` does not exist AND `purlin-config-sample/` exists at the project root
   - If both true, print: `purlin:update is only for consumer projects using Purlin as a submodule.` and exit

1. **Fetch and Version Check:**
   - Run `git -C <submodule_dir> fetch --tags`
   - **Resolve the update target:**
     - If `<version>` argument was provided (first positional arg, not a flag): use it directly as the target ref. Validate: `git -C <submodule_dir> rev-parse --verify <version>`. If invalid, abort: `"Version '<version>' not found in submodule. Check the tag or branch name."`
     - If no `<version>` argument: find the latest release tag reachable from `origin/main`: `git -C <submodule_dir> describe --tags --abbrev=0 origin/main`. This targets the most recent tag — NOT `origin/main` HEAD. Consumer projects only pull tagged releases by default.
     - Resolve the target to a SHA: `git -C <submodule_dir> rev-parse <resolved_target>`
   - Compare local submodule HEAD against the resolved target SHA
   - If already at the resolved target AND `.purlin/.upstream_sha` matches HEAD:
     - Check if migration is pending: run migration detection per `features/purlin_migration.md` §2.1 (check `_migration_version`, `agents.purlin` completeness, old agent deprecation status)
     - If migration state is `needed` or `partial`: print "Already at latest version. Running pending migration..." and skip to step 6 (Config Sync)
     - Otherwise: print "Already up to date." and exit
   - If behind: show current version -> target version and commit count. If `<version>` was explicitly provided, note: `"(explicit target: <version>)"`
   - Prompt: "Update to <version>? (y/n)" (skip if `--auto-approve`)

2. **Pre-Update Conflict Scan:**
   - Read old SHA from `.purlin/.upstream_sha`
   - First, run `git -C <submodule> diff-tree --no-commit-id --name-status -r <old_sha> <new_sha> -- .claude/commands/ .claude/agents/` to identify which command and agent files changed upstream (single invocation). Also check launcher-relevant paths (e.g., `tools/init.sh`).
   - Also check if `tools/mcp/manifest.json` changed: `git -C <submodule> diff-tree --no-commit-id --name-status -r <old_sha> <new_sha> -- tools/mcp/manifest.json`. Record whether the MCP manifest changed (used in step 4b).
   - **If no command files, agent files, or launcher scripts changed upstream, skip the remainder of this step** -- no local modifications can conflict. (The MCP manifest check above is independent and does not affect this early-exit.)
   - For command files (`skills/*/SKILL.md`) that appear in BOTH the consumer project AND the diff-tree output (excluding N/A which is NEVER synced to consumer projects):
     - Compare local file against old upstream version (`git -C <submodule> show <old_sha>:.claude/commands/<file>`)
     - If they differ, flag as "locally modified" for post-update merge
   - For agent files (`.claude/agents/*.md`) that appear in BOTH the consumer project AND the diff-tree output:
     - Compare local file against old upstream version (`git -C <submodule> show <old_sha>:.claude/agents/<file>`)
     - If they differ, flag as "locally modified" for post-update merge
   - Legacy role-specific launchers (`pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`) are fully retired — skip launcher conflict checks.
3. **Advance Submodule:**
   - `git -C <submodule_dir> checkout <resolved_target_sha>` (detached HEAD to the tag SHA or explicit version from step 1)
   - If this fails, abort with error

3b. **Post-Advance Prerequisite Validation (init_preflight_checks.md §2.6):**
   - After advancing the submodule, run `<submodule>/tools/init.sh --preflight-only` to check tool prerequisites using the NEW init.sh version
   - If any **required** tool (git) is missing: print a warning with install instructions. Do NOT block the update — the submodule is already advanced and the refresh must complete to keep the project consistent.
   - If any **recommended** tool (claude) is missing: print a note with the install command (`npm install -g @anthropic-ai/claude-code`) and note that MCP servers will not be installed.
   - If any **optional** tool (node/npx) is missing: print a note with the install command and explain that Playwright web testing will be unavailable.
   - If all prerequisites are met: produce no prerequisite output.
   - Include the prerequisite status in the summary report (step 9).
   - Key difference from init.sh's own preflight: during updates, missing required tools produce warnings rather than hard exits, because the submodule is already advanced.

4. **Init Refresh:**
   - Run `<submodule>/tools/init.sh --quiet` to refresh all project-root artifacts
   - This handles: command files (unmodified ones auto-copied), launcher scripts, shim (`pl-init.sh`), and `.purlin/.upstream_sha`
   - Init's timestamp logic preserves locally modified command files — conflict resolution happens in step 5

4b. **MCP Manifest Diff (only if step 2 detected manifest change):**
   - If `tools/mcp/manifest.json` did NOT change between old and new SHA, skip this step entirely and produce no MCP-related output.
   - If the manifest changed:
     1. Read old manifest: `git -C <submodule> show <old_sha>:tools/mcp/manifest.json`
     2. Read new manifest from disk (after submodule advance): `<submodule>/tools/mcp/manifest.json`
     3. Compute diff by server `name`:
        - **Added servers** (in new, not in old): Report in summary as newly available. These are installed automatically by `init.sh` during the init refresh step.
        - **Removed servers** (in old, not in new): Print advisory: `"MCP server '<name>' was removed from Purlin manifest. Remove manually: claude mcp remove <name>"`. Do NOT auto-remove.
        - **Changed servers** (in both, but different `transport`, `command`, `args`, or `url`): Print advisory with reconfiguration command: `"MCP server '<name>' config changed upstream. Reconfigure: claude mcp remove <name> && <new add command>"`.
     4. If ANY MCP changes occurred (added, removed, or changed), append to the summary: `"Restart Claude Code to load MCP changes."`

5. **Conflict Resolution (only if step 2 found locally modified files):**
   - For each flagged command or agent file where upstream ALSO changed the file:
     - Show three-way diff: old upstream, new upstream, local
     - Offer: "Accept upstream", "Keep current", or "Smart merge"
   - For each flagged command or agent file where upstream did NOT change: no action needed
   - For each flagged launcher script: same three-way approach
   - **Deleted-upstream commands** (file no longer in upstream):
     - Unmodified locally: auto-delete, report "Removed: <filename>"
     - Modified locally: prompt user before deleting, preserve if declined
   - **Skip this step entirely if no conflicts were flagged** — do not scan or analyze files unnecessarily

6. **Config Sync:**
   - Run `sync_config()` via the MCP `purlin_config` tool
   - If `config.local.json` doesn't exist, creates it from `config.json`; otherwise adds missing keys with shared defaults
   - Reports new keys added or "Local config is up to date"

7. **Migration Module (if needed):**
   - After config sync, check if migration to the Purlin unified agent model is needed:
     - **Fast path:** If `_migration_version` exists in config: skip (already complete)
     - If `agents.purlin` is absent AND `agents.architect` or `agents.builder` exists: migration is `needed`
     - If `agents.purlin` exists but `_migration_version` absent: check for incomplete migration (old agents not deprecated, or `agents.purlin` missing `find_work`/`auto_start`/`default_mode`). If incomplete: `partial` — run repair pass
     - If fully complete: skip (stamp `_migration_version: 1` for future fast path)
   - If needed or partial, run: `python3 <submodule>/tools/migration/migrate.py --project-root <project_root>` with any applicable flags passed through (`--dry-run`, `--auto-approve`, `--skip-overrides`, `--skip-companions`, `--skip-specs`, `--purlin-only`, `--complete-transition`)
   - Report migration results in the summary
   - See `features/purlin_migration.md` for the full migration protocol

7c. **Toolbox Migration (if needed):**
   - After config sync and agent migration, check if migration from the old release steps system to the Agentic Toolbox is needed:
     - Detection: `.purlin/release/config.json` or `.purlin/release/local_steps.json` exists AND `.purlin/toolbox/.migrated_from_release` does NOT exist
     - If detected, run: `python3 <submodule>/tools/migration/migrate_release_to_toolbox.py --project-root <project_root>`
     - Report migration results (tools migrated count)
     - The old `.purlin/release/` directory is preserved for one cycle (safety net)
   - If neither condition is met, skip silently

8. **Stale Artifact Cleanup:**
   - **Known stale root scripts:** Check for legacy-named scripts at project root (`run_architect.sh`, `run_builder.sh`, `run_qa.sh`, `purlin_init.sh`, `pl-cdd-start.sh`, `pl-cdd-stop.sh`)
   - If found, prompt: "Remove these files? You can remove them manually later if you prefer."
   - **Orphaned command files:** After init refresh, compare `skills/*/SKILL.md` files against `<submodule>/.claude/commands/`. Any local skill not present in the submodule is orphaned. Auto-delete unmodified orphans (report "Removed orphaned command: <file>"). Prompt before deleting modified orphans. Non-purlin skill files are consumer-owned and not touched.
   - Check if `.purlin/release/` still exists AND `.purlin/toolbox/.migrated_from_release` exists (migration completed). If both true, prompt: `"Found legacy release config at .purlin/release/. This has been migrated to .purlin/toolbox/. Delete the old directory?"` Only delete on explicit user confirmation.
   - In `--dry-run` mode, list stale artifacts but do not delete

9. **Summary:**
   ```
   Purlin updated: <old_version> -> <new_version>
   * N command files updated, M skipped (locally modified)
   * Init refresh completed
   * Config sync: <result>
   ```
   **If any command files were skipped** (locally modified), warn the user: "M command files were skipped because they have local modifications. These files may contain outdated workflow protocols. Run `diff <local_file> <submodule_source>` to review upstream changes and consider merging manually."
   **MCP changes (from step 4b):** If MCP manifest changes were detected, include in summary:
   - List added MCP servers as newly available
   - Include `claude mcp remove <name>` advisory for each removed server
   - Include reconfiguration advisory for each changed server
   - Append: "Restart Claude Code to load MCP changes."
   If no MCP manifest changes were detected, produce no MCP-related output in the summary.

10. **Customization Impact Check (Optional):**
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
- `<version>` (optional, positional): A specific tag (e.g., `v0.8.5`) or branch (e.g., `origin/feature-xyz`) to update to. If omitted, targets the latest release tag on `origin/main`.
- `--dry-run`: Show what would change without modifying files
- `--auto-approve`: Skip confirmation prompts for non-conflicting changes

**Example usage:**
```
purlin:update                    # Update to latest release tag
purlin:update v0.8.5             # Update to specific version
purlin:update --dry-run          # Preview what would change
purlin:update v0.8.6 --dry-run   # Preview update to specific version
```

**Implementation:** See `features/purlin_update_purlin.md`
