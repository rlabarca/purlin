---
name: spec
description: This skill activates PM mode. If another mode is active, confirm switch first
---

> **Hard gates (scenario format, required sections, prerequisite checklist, etc.) are defined in the agent definition §14. They apply regardless of whether this skill was invoked.** This skill provides authoring guidance: templates, format details, category conventions, and invariant advisory.

---

## Required Reading

Before authoring or refining any spec, read `${CLAUDE_PLUGIN_ROOT}/references/spec_authoring_guide.md` for shared authoring principles, role focus, and anchor classification guidance. This guide applies to PM.

---

## Session Identity

When starting spec work, you MUST update the terminal identity with a short task label (3-4 words max) derived from the topic. Do NOT leave the label as the project name — always derive a work-specific label.

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "PM" "<task label>"
```

Examples: `PM(main) | spec auth flow`, `PM(dev/0.8.6) | refine scan engine`.

---

Given the topic provided as an argument:

1. **Update terminal identity (MANDATORY):** Derive a short task label (3-4 words max) from the topic. Call: `source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "pm" "<task label>"`. Examples: `PM(main) | spec auth flow`, `PM(dev/0.8.6) | refine scan engine`. The label MUST describe the current work, not the project name.
2. Run `purlin:find <topic>` logic first to determine if a spec already exists or needs updating.
3. If updating: open the existing feature file, review its current state, identify gaps, and propose targeted additions or revisions. Apply changes after user confirmation.
4. If creating: follow the template and format rules below.
5. After editing, commit the change and run `purlin_scan` to refresh project state.

---

## Feature File Template

When creating a new feature file, use this structure:

```markdown
# Feature: <Name>

> Label: "<Category>: <Label>"
> Category: "<Category>"
> Owner: <PM -- default if omitted>
> Prerequisite: <anchor_node>.md

## 1. Overview

<One paragraph: what this feature is and why it exists.>

---

## 2. Requirements

### 2.1 <Group Name>

- <Requirement>

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: <Title>

    Given <precondition>
    When <action>
    Then <expected outcome>
    And <additional assertion>

### Manual Scenarios (Human Verification Required)

None.
```

**No Implementation Notes section.** Feature files do NOT contain `## Implementation Notes`. All implementation knowledge belongs in companion files (`features/<category_slug>/<name>.impl.md`).

**File placement:** New feature files MUST be placed in the category subfolder matching their `> Category:` metadata. See `references/feature_format.md` "Category Folder Mapping" for the slug table.

---

## Format Rules (Scan Parser Requirements)

**Required section headings** (case-insensitive substring match):
- A heading containing `overview`
- A heading containing `requirements`
- A heading containing `scenarios`

**Scenario heading format -- MUST use four-hash `####`:**
```
#### Scenario: Title of the scenario

    Given <precondition>
    When <action>
    Then <expected outcome>
```
NOT valid: `**Scenario: Title**`, `### Scenario: Title`, `- Scenario: Title`

**Manual scenario block:**
```
### Manual Scenarios (Human Verification Required)

#### Scenario: Title

    Given ...

(Use "None." if no manual scenarios.)
```

**Blockquote metadata fields:**
- `> Label:` -- display name for CDD dashboard
- `> Category:` -- grouping category
- `> Prerequisite: <name>.md` -- dependency link (bare filename, scanner resolves across subfolders)
- `> Web Test: <url>` -- web UI for automated web testing
- `> Web Start: <command>` -- auto-start for web test target
- `> Owner: PM` or `> Owner: PM` -- design authority (default: PM)
- `> Test Fixtures: <url>` -- non-default fixture repo URL

---

## Category and Label Conventions

**Before assigning a category,** scan `.purlin/cache/dependency_graph.json` for existing categories.

| Category | Label Pattern | Example |
|---|---|---|
| Agent Skills | `purlin:<command> Descriptive Name` | `purlin:help Purlin Help` |
| Coordination & Lifecycle | `Policy: <Name>` or `<Descriptive Name>` | `Policy: Lifecycle` |
| Common Design Standards | `Design: <Name>` | `Design: Visual Standards` |
| Install, Update & Scripts | `Tool: <Name>` | `Tool: Agent Launchers` |
| Process | `Process: <Name>` | `Process: Spec-Code Audit` |
| Release Process | `Release Step: <Name>` | `Release Step: Push to Remote` |
| Test Infrastructure | `Dev: <Name>` or `Tool: <Name>` | `Dev: Agent Behavior Tests` |

**Rules:** Prefer existing categories. Match label prefix pattern. Slash command features always go in "Agent Skills." If unsure, choose the category with more members.

---

## Prerequisite Checklist

When creating or updating any feature file, check each row and declare `> Prerequisite:` links:

| If the feature... | Declare |
|---|---|
| Renders HTML, CSS, or any UI output, OR has a Visual Specification | All relevant `design_*.md` anchors |
| Accesses, stores, or transforms data | All relevant `arch_*.md` anchors |
| Modifies module dependencies or communication | All relevant `arch_*.md` anchors |
| Participates in a governed process (security, compliance, release) | All relevant `policy_*.md` anchors |
| Has design artifacts in `features/_design/` | `design_artifact_pipeline.md` |
| Is governed by an operational mandate | All relevant `ops_*.md` or `i_ops_*.md` anchors/invariants |
| Has product brief requirements | All relevant `prodbrief_*.md` or `i_prodbrief_*.md` anchors/invariants |

---

## Invariant Advisory (Pre-Commit)

Before committing a new or updated spec, check for applicable invariants:

1. **Global invariants:** Read `dependency_graph.json` -> `global_invariants`. If any exist, display:
   ```
   This feature is subject to N global invariant(s):
   - i_policy_security.md (v2.1.0)
   - i_arch_coding_standards.md (v1.0.0)
   - i_ops_monitoring.md (v1.2.0)
   ```
2. **Scoped invariant suggestions:** Check for `i_*` files whose domain overlaps with this feature (e.g., a feature with a Visual Specification should consider `i_design_*` invariants). If relevant scoped invariants are not already declared as prerequisites, suggest them:
   ```
   Consider adding prerequisite:
   - i_design_accessibility.md (this feature has a Visual Specification)
   ```
3. This is **advisory only** -- it does not block the spec commit. The audit (`purlin:spec-code-audit`) catches gaps later.
