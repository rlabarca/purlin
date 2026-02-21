# Implementation Notes Companion Files

> Label: "Impl Notes Companion"
> Category: "Coordination & Lifecycle"
> Prerequisite: instructions/HOW_WE_WORK_BASE.md

## Overview

As feature files grow, their Implementation Notes sections consume increasing proportions of file size (up to 27% in worst cases). When agents scan feature files for requirements and scenarios, this wastes context window on implementation notes they don't need for that task. This feature extracts Implementation Notes into separate companion files (`features/<name>.impl.md`), providing clean separation while preserving conceptual colocation -- knowledge is one directory listing away from its spec.

## Requirements

### 2.1 File Naming Convention
- Companion files MUST use the naming pattern `features/<name>.impl.md` alongside `features/<name>.md`.
- Example: `features/critic_tool.md` has companion `features/critic_tool.impl.md`.

### 2.2 Feature File Stub Format
When a companion file exists, the feature file's `## Implementation Notes` section is reduced to a stub containing a link:

```markdown
## Implementation Notes
See [<name>.impl.md](<name>.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.
```

### 2.3 Companion File Structure
The companion file contains the extracted implementation notes content. The file has no metadata headers (no Label, Category, or Prerequisite lines). It begins with a heading and contains the implementation knowledge directly.

```markdown
# Implementation Notes: <Feature Label>
<content>
```

### 2.4 Exclusion Rules
- Companion files (`*.impl.md`) are NOT feature files.
- They MUST NOT appear in the dependency graph.
- They MUST NOT be processed by the Spec Gate or Implementation Gate.
- They MUST NOT appear in the CDD lifecycle tracking.
- They MUST NOT be detected as feature files by the orphan cleanup tool.

### 2.5 Status Reset Exemption
- Edits to `<name>.impl.md` do NOT reset the parent feature's lifecycle status to TODO.
- Only edits to the feature spec file (`<name>.md`) trigger status resets.
- This ensures Builder decisions and tribal knowledge updates do not invalidate completed features.

### 2.6 Companion File Resolution in Critic
- The Critic's Implementation Gate MUST resolve companion file content when evaluating builder decisions, traceability overrides, and section completeness.
- When the inline `## Implementation Notes` stub contains a companion file reference (link to `<name>.impl.md`), the Critic reads the companion file.
- When no companion file reference exists (backward compatibility), the Critic uses inline content as before.
- A stub with a companion file reference is NOT considered "empty notes" for section completeness purposes.

### 2.7 Orphan Detection
- If `<name>.md` is flagged as orphaned, `<name>.impl.md` MUST also be flagged.
- If `<name>.impl.md` exists but `<name>.md` does not, it MUST be flagged as orphaned.

### 2.8 CDD Dashboard Feature Modal
- When a companion `.impl.md` file exists for a feature, the CDD Dashboard feature detail modal shows tabs: "Specification" and "Implementation Notes".
- When no companion file exists, the modal shows content without tabs (same as current behavior).
- Tab content is lazy-loaded and cached for instant switching.

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
When the cleanup tool detects orphaned features
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
