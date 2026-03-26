**Purlin mode: PM**

Legacy agents: If you are not the PM or Architect, respond: "This is a PM/Architect command. Ask your PM or Architect agent to run /pl-spec instead." and stop.
Purlin agent: This skill activates PM mode. If another mode is active, confirm switch first.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Required Reading

Before authoring or refining any spec, read `instructions/references/spec_authoring_guide.md` for shared authoring principles, role focus, and anchor classification guidance. This guide applies to both PM and Architect.

---

Given the topic provided as an argument:

1. Run `/pl-find <topic>` logic first to determine if a spec already exists or needs updating.
2. If updating: open the existing feature file, review its current state, identify gaps, and propose targeted additions or revisions. Apply changes after user confirmation.
3. If creating: follow the template and format rules below.
4. After editing, commit the change and run `${TOOLS_ROOT}/cdd/scan.sh` to refresh project state.

---

## Feature File Template

When creating a new feature file, use this structure:

```markdown
# Feature: <Name>

> Label: "<Category>: <Label>"
> Category: "<Category>"
> Owner: <PM or Architect -- omit line if Architect (default)>
> Prerequisite: features/<anchor_node>.md

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

**No Implementation Notes section.** Feature files do NOT contain `## Implementation Notes`. All implementation knowledge belongs in companion files (`features/<name>.impl.md`).

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
- `> Prerequisite: features/<name>.md` -- dependency link
- `> Web Test: <url>` -- web UI for automated web testing
- `> Web Start: <command>` -- auto-start for web test target
- `> Owner: PM` or `> Owner: Architect` -- design authority (default: Architect)
- `> Test Fixtures: <url>` -- non-default fixture repo URL

---

## Category and Label Conventions

**Before assigning a category,** scan `.purlin/cache/dependency_graph.json` for existing categories.

| Category | Label Pattern | Example |
|---|---|---|
| Agent Skills | `/pl-<command> Descriptive Name` | `/pl-help Purlin Help` |
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
| Has design artifacts in `features/design/` | `design_artifact_pipeline.md` |
