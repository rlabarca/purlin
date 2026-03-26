# Feature: Purlin Migration Module

> Label: "Install, Update & Scripts: Purlin Migration Module"
> Category: "Install, Update & Scripts"
> Prerequisite: features/purlin_agent_launcher.md
> Prerequisite: features/purlin_scan_engine.md

## 1. Overview

The migration module manages version-to-version upgrades for consumer projects using Purlin as a submodule. When `/pl-update-purlin` runs, it detects the project's current migration state and applies any pending upgrades. Each upgrade is tracked by a `_migration_version` integer in config — the module only runs upgrades newer than the current version.

All spec modifications during migration use the `[Migration]` exemption tag to prevent lifecycle resets.

### Version Registry

| `_migration_version` | Upgrade | Source → Target | What changes |
|---|---|---|---|
| 1 | Unified Agent Model | v0.8.x → v0.9.x | 4-role config → single `agents.purlin`; 5 override files → 1; role renames in specs; companion restructuring; old launchers removed |
| _(future)_ | | | |

---

## 2. Requirements

### 2.1 Detection Framework

On `/pl-update-purlin`, determine migration state by checking `.purlin/config.local.json` first, then `.purlin/config.json`:

- **Fast path:** If `_migration_version` key exists and equals the latest version → `complete`, skip.
- **Version gap:** If `_migration_version` exists but is less than the latest → run upgrades from current+1 to latest.
- **No marker:** Inspect config structure to determine state (see version-specific detection below).
- **Fresh install:** If neither old nor new agent config exists → `fresh`, skip (init.sh handles it).

After any successful migration, write `_migration_version: <latest>` to config. This is the authoritative fast-path signal.

### 2.2 v0.8.x → v0.9.x: Unified Agent Model (`_migration_version: 1`)

This upgrade converts the 4-role agent model (Architect, Builder, QA, PM with separate launchers and configs) to the unified Purlin agent with three operating modes.

**Detection (no marker present):**

- If `agents.purlin` is absent AND `agents.architect` or `agents.builder` exists → `needed`.
- **Partial state (v0.8.4 upgrade gap):** If `agents.purlin` exists but is incomplete:
  - Old agents (`architect` or `builder`) still present in config → `partial`.
  - `agents.purlin` missing required fields (`find_work`, `auto_start`, or `default_mode`) → `partial`.
  - Otherwise → `complete` (stamp `_migration_version: 1`).

**Why partial detection is needed:** Users on v0.8.4 have a `/pl-update-purlin` skill that predates migration. Their first update advances the submodule and generates `pl-run.sh`, whose first-run flow creates a minimal `agents.purlin` (only `model` + `effort`). Without partial detection, this minimal entry permanently prevents the full migration from running. The fix: `/pl-update-purlin` checks migration state before its "Already up to date" early exit — if migration is pending, it skips to config sync and runs migration even when the submodule is current.

**Steps (all idempotent):**

#### 2.2.1 Config Migration

**Full migration** (status `needed`):
- Create `agents.purlin` by cloning `agents.builder` config (model, effort, bypass_permissions).
- Add `find_work: true`, `auto_start: false`, `default_mode: null`.
- Remove old agent entries (`architect`, `builder`, `qa`, `pm`) from config.

**Enrichment** (status `partial`):
- Backfill missing keys from `agents.builder` (if present) or defaults (`bypass_permissions: false`, `find_work: true`, `auto_start: false`, `default_mode: null`).
- Remove old agent entries from config.
- Log: `"Enriched partial agents.purlin (backfilled N missing keys)"`.

#### 2.2.2 Override File Consolidation

Merge five role-specific override files into `.purlin/PURLIN_OVERRIDES.md`:

- `BUILDER_OVERRIDES.md` content → `## Engineer Mode` section.
- `PM_OVERRIDES.md` content → `## PM Mode` section.
- `QA_OVERRIDES.md` content → `## QA Mode` section.
- `ARCHITECT_OVERRIDES.md` content → split by keyword heuristic: technical keywords → `## Engineer Mode`; spec/design keywords → `## PM Mode`.
- `HOW_WE_WORK_OVERRIDES.md` content → `## General (all modes)` header at top.
- After creating `PURLIN_OVERRIDES.md`, delete the old override files.

#### 2.2.3 Spec File Role Renames

- In all `features/*.md`: "Architect" → "PM", "Builder" → "Engineer", "the Architect" → "PM mode", "the Builder" → "Engineer mode".
- In `features/*.discoveries.md`: `Action Required: Architect` → `PM`, `Action Required: Builder` → `Engineer`.
- In `features/*.impl.md`: replace role references in prose (not in Active Deviations table).
- ALL commits MUST include the `[Migration]` tag to prevent lifecycle resets.

#### 2.2.4 Companion File Restructuring

- For each `features/*.impl.md`, insert Active Deviations table if absent.
- Parse existing `[DEVIATION]`, `[DISCOVERY]`, `[INFEASIBLE]`, `[SPEC_PROPOSAL]` tags into table rows with PM status `PENDING`.
- Preserve all existing prose content below the table.

#### 2.2.5 CLAUDE.md Update

- If `CLAUDE.md` references old 4-role model but not "Purlin" or "unified agent": add Purlin agent description using `purlin-config-sample/CLAUDE.md.purlin` as template.
- If already mentions "Purlin": skip. If no `CLAUDE.md` exists: skip.

#### 2.2.6 Launcher Cleanup

- Generate `pl-run.sh` at project root (or trigger init.sh refresh).
- Delete old launchers: `pl-run-architect.sh`, `pl-run-builder.sh`, `pl-run-qa.sh`, `pl-run-pm.sh`.
- After migration, `pl-run.sh` is the only launcher.

### 2.3 CLI Flags

- `--dry-run` — Show what would change without modifying any files.
- `--skip-overrides` — Don't merge override files.
- `--skip-companions` — Don't restructure companion files.
- `--skip-specs` — Don't rename roles in spec files.
- `--auto-approve` — Skip confirmation prompts.
- `--purlin-only` — Only add purlin config section, skip all other migration.
- `--complete-transition` — Manual cleanup fallback. Removes old launchers, old config entries, and old override files. Useful if migration was run with skip flags that prevented automatic cleanup.

### 2.4 Idempotency

- Running migration twice MUST NOT corrupt files.
- Check for Active Deviations table existence before inserting.
- Check config key names before renaming.
- Check for PURLIN_OVERRIDES.md existence before creating.
- `--complete-transition` is safe to run multiple times (no-op if artifacts already removed).
- **Partial repair pass:** When `detect_migration_needed()` returns `partial`, the full migration pipeline runs. Each step is already idempotent — `consolidate_overrides()` checks output existence, `rename_spec_roles()` no-ops if already renamed, `restructure_companions()` checks for existing table. The config enrichment path backfills only missing keys.
- `_migration_version` is written after successful migration or repair. Once present, detection returns `complete` on the fast path without inspecting agent key sets.

### 2.5 Migration Commit Convention

- All commits that modify feature spec files during migration MUST include `[Migration]` in the commit message.
- This tag signals to scan.py's exemption tag awareness that the modification is non-behavioral.
- scan.py MUST recognize `[Migration]` as an exempt tag alongside `[Spec-FMT]` and `[QA-Tags]`.
- If the migration modifies spec behavioral content (not just role renames), the `[Migration]` tag MUST NOT be used for that commit.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Migration detected when old config present

    Given config.json has agents.builder but no agents.purlin
    When /pl-update-purlin runs
    Then migration is detected as needed

#### Scenario: Migration skipped when already migrated

    Given config.json has agents.purlin
    When /pl-update-purlin runs
    Then migration is skipped

#### Scenario: Config migration creates purlin section and removes old

    Given config.json has agents.builder with model "claude-opus-4-6"
    When migration runs config step
    Then agents.purlin is created with model "claude-opus-4-6"
    And agents.purlin has default_mode null
    And agents.builder is removed from config

#### Scenario: Override files consolidated

    Given BUILDER_OVERRIDES.md contains "use pytest"
    And QA_OVERRIDES.md contains "smoke tier table"
    When migration runs override consolidation
    Then PURLIN_OVERRIDES.md exists
    And it contains "## Engineer Mode" with "use pytest"
    And it contains "## QA Mode" with "smoke tier table"

#### Scenario: Spec role renames use Migration tag

    Given features/auth_flow.md contains "the Builder implements"
    When migration runs spec rename step
    Then features/auth_flow.md contains "Engineer mode implements"
    And the commit message contains "[Migration]"

#### Scenario: Migration tag preserves lifecycle

    Given feature "auth_flow" is COMPLETE
    And migration renames role references with [Migration] tag
    When scan.py runs
    Then auth_flow has spec_modified_after_completion false

#### Scenario: Companion file gets Active Deviations table

    Given features/auth_flow.impl.md has [DEVIATION] tag but no table
    When migration runs companion restructuring
    Then features/auth_flow.impl.md starts with Active Deviations table
    And the table has a row for the existing deviation
    And existing prose content is preserved below

#### Scenario: CLAUDE.md updated to mention Purlin agent

    Given CLAUDE.md references "Architect, Builder, QA, PM" roles
    And CLAUDE.md does not mention "Purlin" or "unified agent"
    When migration runs
    Then CLAUDE.md is updated to include Purlin unified agent description
    And old role references are preserved for backward compatibility

#### Scenario: Dry run shows changes without modifying

    Given config.json needs migration
    When /pl-update-purlin --dry-run runs
    Then output describes what would change
    And no files are modified
    And no commits are created

#### Scenario: Skip flags exclude steps

    Given config.json needs migration
    When /pl-update-purlin --skip-specs --skip-companions runs
    Then config is migrated
    And override files are consolidated
    And spec files are NOT modified
    And companion files are NOT modified

#### Scenario: Idempotent re-run

    Given migration has already run once
    When /pl-update-purlin runs again
    Then no duplicate Active Deviations tables are created
    And no duplicate config entries are created
    And PURLIN_OVERRIDES.md is not duplicated

#### Scenario: Half-migrated state detected and repaired

    Given config.local.json has agents.purlin with only model and effort keys
    And config.local.json has agents.builder still present
    And no _migration_version key exists in config
    When /pl-update-purlin runs migration step
    Then detect_migration_needed returns "partial"
    And agents.purlin is enriched with find_work, auto_start, default_mode, bypass_permissions
    And agents.builder is removed from config
    And _migration_version is set to 1

#### Scenario: Migration marker prevents re-detection

    Given config.local.json has _migration_version set to 1
    And agents.purlin has full key set
    When /pl-update-purlin runs migration step
    Then detect_migration_needed returns "complete"
    And migration is skipped

#### Scenario: Previously migrated config gets marker stamped

    Given agents.purlin has full 6-key config (model, effort, bypass_permissions, find_work, auto_start, default_mode)
    And no old agent entries remain in config
    And no _migration_version key exists
    When /pl-update-purlin runs migration step
    Then detect_migration_needed returns "complete"
    And _migration_version is stamped as 1 for future fast path

### QA Scenarios

#### Scenario: Migration automatically cleans up old artifacts @auto

    Given config.json has agents.builder and agents.architect but no agents.purlin
    And BUILDER_OVERRIDES.md and ARCHITECT_OVERRIDES.md exist
    And pl-run-architect.sh and pl-run-builder.sh exist at project root
    When full migration runs
    Then agents.purlin is created
    And agents.architect and agents.builder are removed from config
    And PURLIN_OVERRIDES.md is created
    And BUILDER_OVERRIDES.md and ARCHITECT_OVERRIDES.md are deleted
    And pl-run-architect.sh and pl-run-builder.sh are deleted
    And pl-run.sh is the only launcher at project root

#### Scenario: End-to-end migration preserves feature completeness @auto

    Given a consumer project with 20 COMPLETE features using old 4-role model
    When full migration runs (config + overrides + specs + companions)
    And scan.py evaluates the project
    Then all 20 features still show lifecycle COMPLETE
    And spec_modified_after_completion is false for all 20

## Regression Guidance
- Verify [Migration] tag is recognized by scan.py exemption logic
- Verify migration does not modify spec behavioral content (only role names)
- Verify old launchers are deleted after migration (only pl-run.sh remains)
- Verify old override files are deleted after consolidation
- Verify old config entries are removed (not just deprecated)
- Verify config.local.json is handled (not just config.json)
- Verify migration handles missing override files gracefully (not all projects have all 4)
