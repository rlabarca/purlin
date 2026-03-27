# Implementation Notes Companion Files

> Label: "Shared Agent Definitions: Impl Notes Companion"
> Category: "Shared Agent Definitions"

## Overview

As feature files grow, their Implementation Notes sections consume increasing proportions of file size (up to 27% in worst cases). When agents scan feature files for requirements and scenarios, this wastes context window on implementation notes they don't need for that task. This feature extracts Implementation Notes into separate companion files (`features/<name>.impl.md`), providing clean separation while preserving conceptual colocation -- knowledge is one directory listing away from its spec.

## Requirements

### 2.1 File Naming Convention
- Companion files MUST use the naming pattern `features/<name>.impl.md` alongside `features/<name>.md`.
- Example: `features/project_init.md` has companion `features/project_init.impl.md`.

### 2.2 Companion File Resolution
Companion files are resolved by naming convention: for a feature file `features/<name>.md`, the companion is `features/<name>.impl.md`. Feature files do NOT reference companion files -- companion files are standalone, discovered purely by naming convention. This aligns with PURLIN_BASE.md Section 4.3: "companion files are standalone -- feature files do NOT reference them."

When a companion file exists, the feature file's `## Implementation Notes` section MAY contain a stub or be absent entirely. The companion is resolved by convention, not by parsing links.

### 2.3 Companion File Structure
The companion file contains the extracted implementation notes content. The file has no metadata headers (no Label, Category, or Prerequisite lines). It begins with a heading and contains the implementation knowledge directly.

```markdown
# Implementation Notes: <Feature Label>
<content>
```

### 2.4 Exclusion Rules
- Companion files (`*.impl.md`) and discovery sidecar files (`*.discoveries.md`) are NOT feature files.
- They MUST NOT appear in the dependency graph.
- They MUST NOT be processed by spec validation gates.
- They MUST NOT appear in lifecycle tracking.
- They MUST NOT be detected as feature files by the orphan cleanup tool.

### 2.5 Status Reset Exemption
- Edits to `<name>.impl.md` or `<name>.discoveries.md` do NOT reset the parent feature's lifecycle status to TODO.
- Only edits to the feature spec file (`<name>.md`) trigger status resets.
- This ensures Engineer decisions, tribal knowledge updates, and QA discovery recording do not invalidate completed features.

### 2.6 Companion File Resolution
- The scan and audit tools MUST resolve companion file content when evaluating implementation decisions, traceability overrides, and section completeness.
- Companion files are resolved by naming convention: for `features/<name>.md`, check whether `features/<name>.impl.md` exists on disk. If it does, read the companion file content.
- When no companion file exists (backward compatibility), inline `## Implementation Notes` content is used.
- A feature with a companion file on disk is NOT considered to have "empty notes" for section completeness purposes, regardless of what the inline stub contains.

### 2.7 Orphan Detection
- If `<name>.md` is flagged as orphaned, `<name>.impl.md` and `<name>.discoveries.md` MUST also be flagged.
- If `<name>.impl.md` or `<name>.discoveries.md` exists but `<name>.md` does not, it MUST be flagged as orphaned by the orphan cleanup tool.

### 2.8 Companion File Commit Covenant

Per `features/policy_spec_code_sync.md`, every engineer code commit for a feature MUST include a companion file update.

- The minimum entry is a `[IMPL]` line describing what was implemented. See `features/active_deviations.md` §2.4 for tag definitions.
- The old exemption ("if all changes match the spec exactly: no companion entry required") is removed. Every code change gets documented.
- Multiple rapid commits for the same feature MAY batch their entries into a single companion update committed with the last commit in the batch.
- The companion file gate in `/pl-build` Step 4 enforces this mechanically: it checks whether the companion file has new entries from the current session, not whether deviations exist.

### 2.9 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/impl_notes_companion/companion-with-decisions` | Project with features having DEVIATION, DISCOVERY, and AUTONOMOUS tags in companion files |

## 3. Scenarios

### Automated Scenarios

##### Scenario: Feature Scanning Excludes Companion Files
Given a features directory with `project_init.md` and `project_init.impl.md`
When the scan processes feature files
Then only `project_init.md` is processed
And `project_init.impl.md` is not treated as a feature file

#### Scenario: Companion File Resolution for Audit
Given a feature file with a stub `## Implementation Notes` referencing `project_init.impl.md`
And a companion file `features/project_init.impl.md` with engineer decisions
When the spec-code audit evaluates implementation decisions
Then decisions from the companion file are parsed and audited

#### Scenario: Backward Compatible Inline Notes
Given a feature file with inline `## Implementation Notes` (no companion file reference)
When the spec-code audit evaluates implementation decisions
Then the inline content is used for decision parsing (unchanged behavior)

#### Scenario: Stub With Companion Reference Not Flagged as Empty
Given a feature file with a stub `## Implementation Notes` containing a companion file link
When the audit checks section completeness
Then the section is NOT flagged as "Implementation Notes empty"

#### Scenario: Orphan Detection Flags Companion Without Parent
Given a companion file `features/old_feature.impl.md` without a corresponding `features/old_feature.md`
When the orphan cleanup tool scans `features/*.impl.md` files and no corresponding `features/<name>.md` parent exists
Then `old_feature.impl.md` is flagged as orphaned

#### Scenario: Companion commit covenant blocks status tag without entry

    Given Engineer mode has committed code for feature "project_init"
    And features/project_init.impl.md has no new entries from this session
    When /pl-build Step 4 runs the Companion File Gate
    Then the status tag commit is BLOCKED
    And the message requires companion file entries before proceeding

#### Scenario: [IMPL] entry satisfies companion commit covenant

    Given Engineer mode has committed code for feature "project_init"
    And features/project_init.impl.md contains a new [IMPL] entry
    When /pl-build Step 4 runs the Companion File Gate
    Then the gate passes and the status tag commit proceeds

#### Scenario: Batched companion update across rapid commits

    Given Engineer makes 3 commits for feature "project_init" in quick succession
    And writes all companion entries in one update with the third commit
    When /pl-build Step 4 runs
    Then the gate passes (companion file was updated during the session)

### Manual Scenarios

None

## Implementation Notes
*   This is a new feature. Implementation notes will be populated during development.
