# Feature: Unified Version-Aware Update

> Label: "Tool: Unified Version-Aware Update"
> Category: "Install, Update & Scripts"

## 1. Overview

A single `purlin:update` command that detects the consumer project's current Purlin installation model and version, computes the migration path to the current plugin version, and executes each step in order. The command is idempotent — interrupted runs resume from the last completed step, and running on an already-current project produces "Already up to date."

After migration steps complete, the skill runs post-migration feature file organization (idempotent housekeeping on every invocation).

---

## 2. Requirements

### 2.1 Command Interface

```
purlin:update [--dry-run] [--auto-approve]
```

- `--dry-run`: Show the migration plan without modifying files.
- `--auto-approve`: Skip confirmation prompts.

### 2.2 Three-Layer Architecture

The update flow uses three layers:

1. **Version Detector** (`scripts/migration/version_detector.py`): Examines the consumer project and emits a structured fingerprint.
2. **Migration Registry** (`scripts/migration/migration_registry.py`): Ordered list of migration steps with preconditions, `plan()` (dry-run), and `execute()` methods.
3. **Skill orchestration** (`skills/update/SKILL.md`): Calls detector, computes path, shows plan, executes steps, runs post-migration organization, produces summary.

### 2.3 Version Detection

The version detector examines the consumer project directory and produces a fingerprint: `{model, era, version_hint, migration_version, submodule_path}`.

#### 2.3.1 Distribution Model Detection

Signals are checked in priority order:

| Priority | Signal | Model |
|----------|--------|-------|
| 1 | `.claude/settings.json` has `enabledPlugins` containing `purlin` | `plugin` |
| 2 | `.gitmodules` contains a purlin submodule entry | `submodule` |
| 3 | `.purlin/` exists but no submodule or plugin declaration | `fresh` |
| 4 | No Purlin-related artifacts found | `none` |

#### 2.3.2 Migration Version

`_migration_version` is read from `.purlin/config.json` ONLY — never from `config.local.json`. The migration version is project-level state that must be committed and survive `git reset`. `config.local.json` is gitignored.

#### 2.3.3 Fingerprint Schema

```json
{
  "model": "submodule" | "plugin" | "fresh" | "none",
  "era": "pre-unified-legacy" | "pre-unified-modern" | "pre-unified-with-pm" | "unified" | "unified-partial" | "plugin" | null,
  "version_hint": "v0.7.x" | "v0.8.0-v0.8.3" | "v0.8.4" | "v0.8.5" | "v0.9.x" | null,
  "migration_version": <integer> | null,
  "submodule_path": <string> | null
}
```

### 2.4 Migration Registry

#### 2.4.1 Step Interface

Each migration step is a Python class with:
- `step_id: int` — the `_migration_version` value this step stamps on completion.
- `name: str` — human-readable name.
- `preconditions(fingerprint, project_root) -> (bool, str)` — checks if this step can run.
- `plan(fingerprint, project_root) -> list[str]` — dry-run: returns list of actions.
- `execute(fingerprint, project_root, auto_approve=False) -> bool` — runs the migration. Stamps `_migration_version` on completion.

#### 2.4.2 Step Definitions

| Step | `_migration_version` | Name | Key Actions |
|------|---------------------|------|-------------|
| 1 | 1 | Unified Agent Model | Consolidate 4-role config into `agents.purlin`. Clean old role-specific launchers. |
| 2 | 2 | Submodule to Plugin | Remove submodule. Clean stale artifacts. Declare plugin in `.claude/settings.json`. Migrate config. |
| 3 | 3 | Plugin Refresh | Force-remove purlin/ dir, .gitmodules, symlinks. Delete ALL stale artifacts (pl-* glob, CRITIC_REPORT.md, old override files, .purlin/release/). Rewrite CLAUDE.md (strip old boilerplate). |
| 4 | 4 | Figma to Design Invariant | Scan ALL feature .md files for Figma references. Create `i_design_*` invariants in `_invariants/`. Move companion design data (brief.json) to `_invariants/`. Strip Figma metadata from feature files. Add prerequisite references. |
| 5 | 5 | Remove Override System | Parse test priority tiers from PURLIN_OVERRIDES.md / QA_OVERRIDES.md into config.json. Strip submodule-era boilerplate. Delete override files. |
| 6 | 6 | Mode to Sync | Remove mode system artifacts (state files, session tracking, config keys). Create `.purlin/sync_ledger.json`. Update `.gitignore` for sync tracking. |

#### 2.4.3 Path Computation

Steps with `step_id > migration_version` (or 0 if null) and `<= CURRENT_MIGRATION_VERSION` are included. Steps whose preconditions fail are **skipped** (not halted) — this allows plugin-model projects to skip submodule-only steps and reach Steps 3-5.

Re-detection runs between each step so later steps see updated state (e.g., Step 4 sees `migration_version: 3` after Step 3 completes).

#### 2.4.4 Version Stamping

`_stamp_version()` writes to `.purlin/config.json` ONLY. Never stamps `config.local.json`.

### 2.5 Step 3: Plugin Refresh (Detail)

This is the most common step for existing projects and the most comprehensive cleanup. It runs for any project at `migration_version < 3`.

**Stale artifact cleanup:**
- `purlin/` directory (force-remove even if git deinit fails)
- `.gitmodules` (delete entirely — only submodule was purlin)
- `.git/modules/purlin/` cache
- ALL `pl-*` files/symlinks at project root (glob match)
- `purlin-start.sh`, `purlin-stop.sh`
- `CRITIC_REPORT.md`
- `.purlin/ARCHITECT_OVERRIDES.md`, `.purlin/BUILDER_OVERRIDES.md`, `.purlin/PM_OVERRIDES.md`, `.purlin/HOW_WE_WORK_OVERRIDES.md`
- `.purlin/gitignore.purlin`, `.purlin/.upstream_sha`
- `.purlin/release/` directory
- `.claude/commands/pl-*.md`, `.claude/agents/*.md`

**CLAUDE.md rewrite:**
- Strip `<!-- purlin:start -->...<!-- purlin:end -->` block (old 4-role boilerplate)
- Strip `## Project Rules (migrated from Purlin overrides)` section
- If nothing remains, write minimal plugin reference

### 2.6 Step 4: Figma to Design Invariant (Detail)

Scans ALL `.md` files in `features/` (not just `design_*` files) for Figma references. Old Purlin versions (<=0.8.5) put Figma references in feature specs instead of design anchors.

**Figma detection patterns (first match wins):**
- Full URL: `> Figma-URL: https://figma.com/...`
- Markdown link: `[text](https://figma.com/...)`
- File key metadata: `> **Figma File:** <key>`
- Companion `brief.json` with `figma_file_key`

**For design_*.md files (Figma-sourced anchors):**
- Create `i_design_<stem>.md` in `_invariants/`
- Update prerequisite references in dependent features
- Delete the original design_*.md file

**For regular feature files (Figma ref was inline):**
- Create `i_design_<stem>.md` in `_invariants/`
- Strip Figma metadata lines from the feature file
- Add `> Prerequisite: features/_invariants/i_design_<stem>.md` to the feature
- Keep existing prerequisites intact

**For both:**
- Move companion design data (`features/design/<stem>/` or `features/_design/<stem>/`) into `features/_invariants/<stem>/` alongside the invariant file
- Clean up empty design parent directories

### 2.7 Step 5: Remove Override System (Detail)

Removes PURLIN_OVERRIDES.md and QA_OVERRIDES.md. Extracts test priority tiers to `config.json`. Strips submodule-era boilerplate before migrating any remaining content to CLAUDE.md.

**Boilerplate filter strips:**
- `# Purlin Agent Overrides` heading
- `## General (all modes)`, `## Engineer Mode`, `## PM Mode`, `## QA Mode` template sections
- `HARD PROHIBITION` and `Read-Only` sections
- Lines containing submodule keywords (purlin/, pl-run.sh, etc.)
- HTML comments, blockquote template instructions

Only genuinely project-specific content survives the filter and is appended to CLAUDE.md.

### 2.8 Step 6: Mode to Sync (Detail)

Removes the mode system (role-based write guards) and creates sync tracking artifacts. The mode system is replaced by lightweight sync observation — drift detection instead of write prevention.

**Mode artifact cleanup:**
- `.purlin/runtime/current_mode*` — mode state files (including per-agent variants like `current_mode_<agent_id>`)
- `.purlin/runtime/session_writes.json` — old companion debt tracker input
- `.purlin/runtime/companion_debt.json` — old companion debt state

**Sync ledger creation:**
- `.purlin/sync_ledger.json` — empty `{}`, committed to git. Tracks per-feature sync state across commits.

**Config cleanup:**
- Remove `default_mode` and `mode_on_start` from top-level config and from `agents.purlin` (if present).

**Gitignore update:**
- Add `.purlin/runtime/sync_state.json` (session-scoped, not committed)
- Remove `.purlin/runtime/session_writes.json` (if present)

**Note:** Hook file updates (mode-guard.sh → write-guard.sh, companion-debt-tracker.sh → sync-tracker.sh) ship with the plugin update itself. Consumer projects don't manage hook scripts — those come from the plugin directory. This step only handles consumer-side artifacts.

### 2.9 Post-Migration: Feature File Organization

Runs on EVERY `purlin:update` invocation (not just migration). Idempotent.

1. Rename legacy special folders: `features/tombstones/` → `features/_tombstones/`, `features/digests/` → `features/_digests/`, `features/design/` → `features/_design/`.
2. Scan `features/` root for `.md` files not in a category subfolder.
3. For each root-level file: extract `> Category:` metadata, slugify to folder name (lowercase, spaces to underscores), create folder, move file + companions.
4. Invariant files (`i_*` prefix) go to `_invariants/`.
5. Files with no `> Category:` metadata are skipped with a warning.
6. Drift detection: scan subfolders, compare slugified category to folder name, warn on mismatches (no auto-move).

### 2.10 Idempotency

- Each step checks `_migration_version` before running. Steps with `step_id <= migration_version` are skipped.
- Interrupted runs resume from the last completed step (the interrupted step's version was not stamped).
- Steps whose preconditions fail are skipped (not halted), allowing later steps to run.
- Running `purlin:update` on an already-current project runs only the post-migration organize step.

### 2.11 Error Handling

| Condition | Message | Action |
|-----------|---------|--------|
| Not a Purlin project | `✗ Not a Purlin project. Run purlin:init to set up.` | Stop |
| Fresh project, no migration | `✗ Fresh project detected. Run purlin:init first.` | Stop |
| Already up to date | `✓ Already up to date.` | Run organize step only |
| Step precondition failure | `Step <id> (<name>) skipped: <reason>` | Continue to next step |
| Step execution failure | `✗ Step <id> failed.` | Stop (version not stamped, safe to retry) |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Detect plugin-based project

    Given a consumer project with enabledPlugins in .claude/settings.json
    When the version detector runs
    Then the fingerprint model is "plugin"

#### Scenario: Detect submodule project

    Given a consumer project with .gitmodules containing purlin
    When the version detector runs
    Then the fingerprint model is "submodule"

#### Scenario: Compute path from no migration to current

    Given a fingerprint with migration_version null
    When compute_path is called with target migration_version 5
    Then the path contains steps [1, 2, 3, 4, 5]

#### Scenario: Compute path from plugin v0.8.5 to current

    Given a fingerprint with migration_version 1
    When compute_path is called with target migration_version 5
    Then the path contains steps [2, 3, 4, 5]

#### Scenario: Already current produces empty path

    Given a fingerprint with migration_version 5
    When compute_path is called with target migration_version 5
    Then the path is empty

#### Scenario: Inapplicable steps are skipped not halted

    Given a plugin project (model=plugin) with migration_version null
    When migration executes
    Then steps 1 and 2 are skipped (preconditions fail: not a submodule)
    And steps 3, 4, 5 execute successfully

#### Scenario: Step 3 removes all stale artifacts

    Given a project with purlin/ dir, .gitmodules, pl-run-*.sh symlinks, CRITIC_REPORT.md, old override files
    When step 3 executes
    Then all listed artifacts are deleted
    And CLAUDE.md is rewritten without old boilerplate

#### Scenario: Step 4 extracts Figma from feature files

    Given a feature file with > **Figma File:** metadata
    When step 4 executes
    Then features/_invariants/i_design_<stem>.md is created
    And the feature file has > Prerequisite: features/_invariants/i_design_<stem>.md
    And the Figma metadata lines are removed from the feature file
    And brief.json is moved to features/_invariants/<stem>/

#### Scenario: Step 4 skips files without Figma

    Given a design_*.md anchor with no Figma reference
    When step 4 executes
    Then the anchor is NOT converted to an invariant
    And it remains in its original location

#### Scenario: Step 5 strips submodule boilerplate from overrides

    Given PURLIN_OVERRIDES.md with "HARD PROHIBITION" and empty template sections
    When step 5 executes
    Then nothing is appended to CLAUDE.md (all content was boilerplate)
    And PURLIN_OVERRIDES.md is deleted

#### Scenario: Migration version read from config.json only

    Given config.json has _migration_version: null
    And config.local.json has _migration_version: 5
    When the version detector runs
    Then migration_version is null (not 5)

#### Scenario: Post-migration organizes features by category

    Given root-level feature files with > Category: "UI" and > Category: "Architecture"
    When the organize step runs
    Then features/ui/ and features/architecture/ are created
    And files are moved with their companions

### QA Scenarios

#### @manual Scenario: Full migration from v0.8.5 submodule to current plugin

    Given a consumer project with submodule, old launchers, Figma in feature specs, override files
    When purlin:update is run interactively
    Then all applicable steps execute
    And no stale artifacts remain (purlin/, .gitmodules, pl-*, CRITIC_REPORT, overrides)
    And Figma references are in _invariants/ with brief.json
    And features are organized into category folders
    And CLAUDE.md has no submodule boilerplate

## Regression Guidance

- `_migration_version` is read from config.json ONLY. Never config.local.json.
- Steps whose preconditions fail are SKIPPED, not halted. This allows plugin projects to reach Steps 3-5.
- Step 3 uses `glob pl-*` to catch all naming conventions for old launcher scripts.
- Step 4 scans ALL .md files in features/ for Figma (not just design_* files).
- Step 5 boilerplate filter must strip submodule-era content to avoid polluting CLAUDE.md.
- Post-migration organize slugifies categories directly — no canonical table lookup.
