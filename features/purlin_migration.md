# Feature: Purlin Migration Module

> Label: "Install, Update & Scripts: Purlin Migration Module"
> Category: "Install, Update & Scripts"
> Prerequisite: features/purlin_agent_launcher.md
> Prerequisite: features/purlin_scan_engine.md

## 1. Overview

When consumer projects run `/pl-update-purlin`, the migration module detects old 4-role config and offers to migrate to the purlin unified agent model. Migration includes: config schema update, override file consolidation, spec file role renames, companion file restructuring, and launcher generation. All spec modifications use the `[Migration]` exemption tag to prevent lifecycle resets. Old launchers and config are preserved during the transition period.

---

## 2. Requirements

### 2.1 Detection

On `/pl-update-purlin`, determine migration state by checking `.purlin/config.local.json` first, then `.purlin/config.json`:

- **Fast path:** If `_migration_version` key exists at the config top level → migration is `complete`, skip.
- **Full migration needed:** If `agents.purlin` is absent AND `agents.architect` or `agents.builder` exists → migration is `needed`.
- **Partial state (v0.8.4 upgrade gap):** If `agents.purlin` exists but `_migration_version` is absent, check for incomplete migration:
  - If old agents (`architect` or `builder`) exist without `"_deprecated": true` → `partial`.
  - If `agents.purlin` is missing required fields (`find_work`, `auto_start`, or `default_mode`) → `partial`.
  - Otherwise → `complete` (stamp `_migration_version: 1` for future fast path).
- **Fresh install:** If neither old (`architect`/`builder`) nor new (`purlin`) agent config exists → `fresh`, skip (init.sh handles it).

**Why partial detection is needed:** When users on v0.8.4 upgrade, their old `/pl-update-purlin` skill lacks the migration step. The new `init.sh` generates `pl-run.sh`, whose first-run flow creates a minimal `agents.purlin` (only `model` + `effort`). Without partial detection, this minimal entry permanently prevents the full migration from running.

### 2.2 Config Migration

**Full migration** (status `needed`):
- Create `agents.purlin` section by cloning `agents.builder` config (model, effort, bypass_permissions).
- Add `find_work: true`, `auto_start: false`, `default_mode: null` fields.
- Mark old entries with `"_deprecated": true` (old launchers still read them during transition).
- Do NOT delete old entries — they're needed until transition is complete.

**Enrichment** (status `partial`):
- If `agents.purlin` exists but is missing any of `find_work`, `auto_start`, `default_mode`, or `bypass_permissions`: backfill from `agents.builder` (if present) or from defaults (`bypass_permissions: false`, `find_work: true`, `auto_start: false`, `default_mode: null`).
- Mark old agents with `"_deprecated": true` if not already marked.
- Log: `"Enriched partial agents.purlin (backfilled N missing keys)"`.

**Migration marker:** After successful full migration or enrichment, write `"_migration_version": 1` at the config top level (same file where `agents.purlin` was written). This is the authoritative signal for the fast-path detection in Section 2.1.

### 2.3 Override File Consolidation

Merge the old role-specific override files into a single `.purlin/PURLIN_OVERRIDES.md`:

- `BUILDER_OVERRIDES.md` content → `## Engineer Mode` section.
- `PM_OVERRIDES.md` content → `## PM Mode` section.
- `QA_OVERRIDES.md` content → `## QA Mode` section.
- `ARCHITECT_OVERRIDES.md` content → split by keyword heuristic: technical keywords (arch, code, implementation, testing, script, tool, build) → `## Engineer Mode`; spec/design keywords (spec, design, requirement, visual, UX, stakeholder) → `## PM Mode`.
- `HOW_WE_WORK_OVERRIDES.md` content → `## General (all modes)` header at top.
- Do NOT delete old override files — they're needed for old launchers during transition.

### 2.4 Spec File Role Renames

- In all `features/*.md` files, replace old role references with new:
  - "Architect" → "PM" (when referring to spec/design authority)
  - "Builder" → "Engineer" (when referring to implementation)
  - "the Architect" → "PM mode"
  - "the Builder" → "Engineer mode"
- In `features/*.discoveries.md`: replace `Action Required: Architect` → `PM`, `Action Required: Builder` → `Engineer`.
- In `features/*.impl.md`: replace role references in prose (not in Active Deviations table which uses new format).
- ALL spec modification commits MUST include the `[Migration]` tag to prevent lifecycle resets.
- Example commit: `chore(migration): rename role references in feature specs [Migration]`

### 2.5 Companion File Restructuring

- For each `features/*.impl.md`, check if an Active Deviations table exists.
- If absent: insert the table template at the top (before existing content).
- Parse existing `[DEVIATION]`, `[DISCOVERY]`, `[INFEASIBLE]`, `[SPEC_PROPOSAL]` tags and populate table rows with PM status `PENDING`.
- Preserve all existing prose content below the table.

### 2.6 CLAUDE.md Update

- If the consumer project has a `CLAUDE.md` that references the old 4-role model (Architect, Builder, QA, PM) but does not mention the Purlin unified agent:
  - Add a section describing the Purlin agent alongside existing role boundaries.
  - Reference: use `purlin-config-sample/CLAUDE.md.purlin` as the canonical template.
- If `CLAUDE.md` already mentions "Purlin" or "unified agent": skip.
- If no `CLAUDE.md` exists: skip (init.sh creates it from the sample).

### 2.7 Launcher Generation

- Generate `pl-run.sh` at project root (or trigger init.sh refresh to generate it).
- Do NOT delete old launchers — they still work during transition.

### 2.8 CLI Restrictions

- `--dry-run` — Show what would change without modifying any files.
- `--skip-overrides` — Don't merge override files.
- `--skip-companions` — Don't restructure companion files.
- `--skip-specs` — Don't rename roles in spec files.
- `--auto-approve` — Skip confirmation prompts.
- `--purlin-only` — Only add purlin config section, skip all other migration.
- `--complete-transition` — Remove old launchers, deprecated config entries, and old override files.

### 2.9 Idempotency

- Running migration twice MUST NOT corrupt files.
- Check for Active Deviations table existence before inserting.
- Check config key names before renaming.
- Check for PURLIN_OVERRIDES.md existence before creating.
- `--complete-transition` is safe to run multiple times.
- **Partial repair pass:** When `detect_migration_needed()` returns `partial`, the full migration pipeline runs. Each step is already idempotent — `consolidate_overrides()` checks output existence, `rename_spec_roles()` no-ops if already renamed, `restructure_companions()` checks for existing table. The config enrichment path backfills only missing keys.
- `_migration_version` is written after successful migration or repair. Once present, detection returns `complete` on the fast path without inspecting agent key sets.

### 2.10 Migration Commit Convention

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

#### Scenario: Config migration creates purlin section

    Given config.json has agents.builder with model "claude-opus-4-6"
    When migration runs config step
    Then agents.purlin is created with model "claude-opus-4-6"
    And agents.purlin has default_mode null
    And agents.builder has _deprecated true

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
    And config.local.json has agents.builder without _deprecated flag
    And no _migration_version key exists in config
    When /pl-update-purlin runs migration step
    Then detect_migration_needed returns "partial"
    And agents.purlin is enriched with find_work, auto_start, default_mode, bypass_permissions
    And agents.builder is marked _deprecated true
    And _migration_version is set to 1

#### Scenario: Migration marker prevents re-detection

    Given config.local.json has _migration_version set to 1
    And agents.purlin has full key set
    When /pl-update-purlin runs migration step
    Then detect_migration_needed returns "complete"
    And migration is skipped

#### Scenario: Previously migrated config gets marker stamped

    Given agents.purlin has full 6-key config (model, effort, bypass_permissions, find_work, auto_start, default_mode)
    And agents.builder has _deprecated true
    And no _migration_version key exists
    When /pl-update-purlin runs migration step
    Then detect_migration_needed returns "complete"
    And _migration_version is stamped as 1 for future fast path

### QA Scenarios

#### Scenario: Complete transition removes old artifacts @auto

    Given migration has run and old launchers still exist
    When /pl-update-purlin --complete-transition runs
    Then pl-run-architect.sh is deleted
    And pl-run-builder.sh is deleted
    And pl-run-qa.sh is deleted
    And pl-run-pm.sh is deleted
    And agents.architect is removed from config
    And agents.builder is removed from config
    And ARCHITECT_OVERRIDES.md is deleted
    And BUILDER_OVERRIDES.md is deleted

#### Scenario: End-to-end migration preserves feature completeness @auto

    Given a consumer project with 20 COMPLETE features using old 4-role model
    When full migration runs (config + overrides + specs + companions)
    And scan.py evaluates the project
    Then all 20 features still show lifecycle COMPLETE
    And spec_modified_after_completion is false for all 20

## Regression Guidance
- Verify [Migration] tag is recognized by scan.py exemption logic
- Verify migration does not modify spec behavioral content (only role names)
- Verify old launchers still work after migration (before --complete-transition)
- Verify config.local.json is handled (not just config.json)
- Verify migration handles missing override files gracefully (not all projects have all 4)
