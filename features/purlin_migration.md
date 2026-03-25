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

- On `/pl-update-purlin`, check if `agents.purlin` exists in `.purlin/config.json` or `config.local.json`.
- If absent AND `agents.architect` or `agents.builder` exists: migration is needed.
- If `agents.purlin` already exists: migration is complete, skip.
- If neither old nor new config exists: fresh install, skip migration (init.sh handles it).

### 2.2 Config Migration

- Create `agents.purlin` section by cloning `agents.builder` config (model, effort, bypass_permissions).
- Add `find_work: true`, `auto_start: false`, `default_mode: null` fields.
- Mark old entries with `"_deprecated": true` (old launchers still read them during transition).
- Do NOT delete old entries — they're needed until transition is complete.

### 2.3 Override File Consolidation

- If `.purlin/BUILDER_OVERRIDES.md` has content: create `.purlin/PURLIN_OVERRIDES.md` with content under `## Engineer Mode` header.
- If `.purlin/PM_OVERRIDES.md` has content: append under `## PM Mode`.
- If `.purlin/QA_OVERRIDES.md` has content: append under `## QA Mode`.
- If `.purlin/ARCHITECT_OVERRIDES.md` has content: merge into appropriate mode section (technical → Engineer, spec → PM).
- Add `## General (all modes)` header at top with content from `HOW_WE_WORK_OVERRIDES.md` if it exists.
- Do NOT delete old override files — they're needed for old launchers during transition.

### 2.4 Spec File Role Renames

- In all `features/*.md` files, replace role references:
  - "Architect" → "PM" (when referring to spec/design authority)
  - "Builder" → "Engineer" (when referring to implementation)
  - "the Architect" → "PM mode"
  - "the Builder" → "Engineer mode"
- In `features/*.discoveries.md`: replace `Action Required: Architect` → `PM`, `Builder` → `Engineer`.
- In `features/*.impl.md`: replace role references in prose (not in Active Deviations table which uses new format).
- ALL spec modification commits MUST include the `[Migration]` tag to prevent lifecycle resets.
- Example commit: `chore(migration): rename role references in feature specs [Migration]`

### 2.5 Companion File Restructuring

- For each `features/*.impl.md`, check if an Active Deviations table exists.
- If absent: insert the table template at the top (before existing content).
- Parse existing `[DEVIATION]`, `[DISCOVERY]`, `[INFEASIBLE]`, `[SPEC_PROPOSAL]` tags and populate table rows with PM status `PENDING`.
- Preserve all existing prose content below the table.

### 2.6 Launcher Generation

- Generate `pl-run.sh` at project root (or trigger init.sh refresh to generate it).
- Do NOT delete old launchers — they still work during transition.

### 2.7 CLI Restrictions

- `--dry-run` — Show what would change without modifying any files.
- `--skip-overrides` — Don't merge override files.
- `--skip-companions` — Don't restructure companion files.
- `--skip-specs` — Don't rename roles in spec files.
- `--auto-approve` — Skip confirmation prompts.
- `--purlin-only` — Only add purlin config section, skip all other migration.
- `--complete-transition` — Remove old launchers, deprecated config entries, and old override files.

### 2.8 Idempotency

- Running migration twice MUST NOT corrupt files.
- Check for Active Deviations table existence before inserting.
- Check config key names before renaming.
- Check for PURLIN_OVERRIDES.md existence before creating.
- `--complete-transition` is safe to run multiple times.

### 2.9 Migration Commit Convention

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

### QA Scenarios

#### Scenario: Complete transition removes old artifacts

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

#### Scenario: End-to-end migration preserves feature completeness

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
