# Implementation Notes Companion Files

> Label: "Impl Notes Companion"
> Category: "Coordination & Lifecycle"
> Prerequisite: features/policy_critic.md

## Overview

As feature files grow, their Implementation Notes sections consume increasing proportions of file size (up to 27% in worst cases). When agents scan feature files for requirements and scenarios, this wastes context window on implementation notes they don't need for that task. This feature extracts Implementation Notes into separate companion files (`features/<name>.impl.md`), providing clean separation while preserving conceptual colocation -- knowledge is one directory listing away from its spec.

## Requirements

### 2.1 File Naming Convention
- Companion files MUST use the naming pattern `features/<name>.impl.md` alongside `features/<name>.md`.
- Example: `features/critic_tool.md` has companion `features/critic_tool.impl.md`.

### 2.2 Companion File Resolution
Companion files are resolved by naming convention: for a feature file `features/<name>.md`, the companion is `features/<name>.impl.md`. Feature files do NOT reference companion files -- companion files are standalone, discovered purely by naming convention. This aligns with HOW_WE_WORK_BASE Section 4.3: "companion files are standalone -- feature files do NOT reference them."

When a companion file exists, the feature file's `## Implementation Notes` section MAY contain a stub or be absent entirely. The Critic resolves the companion by convention, not by parsing links.

### 2.3 Companion File Structure
The companion file contains the extracted implementation notes content. The file has no metadata headers (no Label, Category, or Prerequisite lines). It begins with a heading and contains the implementation knowledge directly.

```markdown
# Implementation Notes: <Feature Label>
<content>
```

### 2.4 Exclusion Rules
- Companion files (`*.impl.md`) and discovery sidecar files (`*.discoveries.md`) are NOT feature files.
- They MUST NOT appear in the dependency graph.
- They MUST NOT be processed by the Spec Gate or Implementation Gate.
- They MUST NOT appear in the CDD lifecycle tracking.
- They MUST NOT be detected as feature files by the orphan cleanup tool.

### 2.5 Status Reset Exemption
- Edits to `<name>.impl.md` or `<name>.discoveries.md` do NOT reset the parent feature's lifecycle status to TODO.
- Only edits to the feature spec file (`<name>.md`) trigger status resets.
- This ensures Engineer decisions, tribal knowledge updates, and QA discovery recording do not invalidate completed features.

### 2.6 Companion File Resolution in Critic
- The Critic's Implementation Gate MUST resolve companion file content when evaluating builder decisions, traceability overrides, and section completeness.
- The Critic resolves companion files by naming convention: for `features/<name>.md`, it checks whether `features/<name>.impl.md` exists on disk. If it does, the Critic reads the companion file content.
- When no companion file exists (backward compatibility), the Critic uses inline `## Implementation Notes` content as before.
- A feature with a companion file on disk is NOT considered to have "empty notes" for section completeness purposes, regardless of what the inline stub contains.

### 2.7 Orphan Detection
- If `<name>.md` is flagged as orphaned, `<name>.impl.md` and `<name>.discoveries.md` MUST also be flagged.
- If `<name>.impl.md` or `<name>.discoveries.md` exists but `<name>.md` does not, it MUST be flagged as orphaned.

### 2.8 CDD Dashboard Feature Modal
- When a companion `.impl.md` file exists for a feature, the CDD Dashboard feature detail modal shows tabs: "Specification" and "Implementation Notes".
- When no companion file exists, the modal shows content without tabs (same as current behavior).
- Tab content is lazy-loaded and cached for instant switching.

### 2.10 Companion File API Endpoint

The CDD Dashboard exposes companion file content via:

*   **Endpoint:** `GET /impl-notes?file=<feature_path>`
*   **Response (200):** Raw markdown content of the companion file.
*   **Response (404):** No companion file exists for the given feature path.
*   **Path resolution:** The `file` parameter is the feature filename (e.g., `critic_tool.md`). The endpoint resolves the companion as `features/<stem>.impl.md`.

### 2.9 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/impl_notes_companion/companion-with-decisions` | Project with features having DEVIATION, DISCOVERY, and AUTONOMOUS tags in companion files |

## 3. Scenarios

### Automated Scenarios

##### Scenario: Feature Scanning Excludes Companion Files
Given a features directory with `critic_tool.md` and `critic_tool.impl.md`
When the Critic scans for feature files
Then only `critic_tool.md` is processed
And `critic_tool.impl.md` is not treated as a feature file

#### Scenario: Companion File Resolution for Implementation Gate
Given a feature file with a stub `## Implementation Notes` referencing `critic_tool.impl.md`
And a companion file `features/critic_tool.impl.md` with builder decisions
When the Critic runs the Implementation Gate
Then builder decisions from the companion file are parsed and audited

#### Scenario: Backward Compatible Inline Notes
Given a feature file with inline `## Implementation Notes` (no companion file reference)
When the Critic runs the Implementation Gate
Then the inline content is used for builder decision parsing (unchanged behavior)

#### Scenario: Stub With Companion Reference Not Flagged as Empty
Given a feature file with a stub `## Implementation Notes` containing a companion file link
When the Critic checks section completeness
Then the section is NOT flagged as "Implementation Notes empty"

#### Scenario: CDD Excludes Companion Files
Given a features directory with `critic_tool.md` and `critic_tool.impl.md`
When the CDD monitor scans for feature lifecycle status
Then only `critic_tool.md` is included in the status report
And `critic_tool.impl.md` does not appear as a feature

#### Scenario: Dependency Graph Excludes Companion Files
Given a features directory with `critic_tool.md` and `critic_tool.impl.md`
When the CDD Dashboard generates the dependency graph
Then only `critic_tool.md` appears as a node
And `critic_tool.impl.md` is not included

#### Scenario: Orphan Detection Flags Companion Without Parent
Given a companion file `features/old_feature.impl.md` without a corresponding `features/old_feature.md`
When the Critic scans `features/*.impl.md` files and no corresponding `features/<name>.md` parent exists, the companion is flagged as an orphan in the Critic report
Then `old_feature.impl.md` is flagged as orphaned

#### Scenario: Companion File Served via API
Given a feature `critic_tool.md` with a companion file `critic_tool.impl.md`
When the CDD Dashboard requests `/impl-notes?file=features/critic_tool.md`
Then the companion file content is returned with status 200

#### Scenario: No Companion File Returns 404
Given a feature `policy_critic.md` without a companion file
When the CDD Dashboard requests `/impl-notes?file=features/policy_critic.md`
Then a 404 status is returned

### Manual Scenarios

None

## Implementation Notes
*   This is a new feature. Implementation notes will be populated during development.
