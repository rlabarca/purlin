# Feature File Format Reference

> This file is loaded on-demand by `/pl-spec` and `/pl-anchor` commands.
> It contains heading format rules and Critic parser requirements.

The Critic's parser enforces specific Markdown heading formats. Wrong heading levels or
section names cause Spec Gate failures that are not obvious from the error message.

## Template Files

**MANDATE:** When creating a new feature file or anchor node, you MUST copy from the template as the starting point. Do NOT create feature files from memory or scratch. When updating an existing feature file, consult the template to verify section structure is correct. The template is the authoritative reference for required sections, heading formats, and section order.

Copy from `{tools_root}/feature_templates/`:
- `_feature.md` -- regular feature file
- `_anchor.md` -- anchor node (arch_*, design_*, policy_*)

**No Implementation Notes section:** Feature files do NOT contain an `## Implementation Notes` section. All implementation knowledge belongs in companion files (`features/<name>.impl.md`). See HOW_WE_WORK_BASE Section 4.3 and BUILDER_BASE Section 5.2 for the companion file convention.

## Blockquote Metadata

Feature files use `>` blockquote lines at the top for metadata. Supported metadata fields:

- `> Label: "Human-Readable Name"` -- display name for CDD dashboard.
- `> Category: "Category Name"` -- grouping for CDD dashboard.
- `> Prerequisite: features/<name>.md` -- dependency link to an anchor node or foundation feature.
- `> Web Testable: <url>` -- declares the feature's web UI is accessible at `<url>` for automated verification via `/pl-web-verify`. Features without this annotation use `/pl-verify` (manual). Example: `> Web Testable: http://localhost:9086`.

## Category and Label Consistency

When creating a new feature file, the Architect MUST scan existing features to ensure the new
file uses a consistent category and label. Do NOT invent a new category when an existing one
applies.

**How to scan:** Read `.purlin/cache/dependency_graph.json` and extract the `category` and
`label` fields from each entry. Identify the naming patterns below and match the new feature
to the best-fitting category.

**Established naming conventions by category:**

| Category | Label Pattern | Example |
|---|---|---|
| Agent Skills | `/pl-<command> Descriptive Name` | `/pl-help Purlin Help` |
| CDD Dashboard | `CDD <Feature Name>` or `CDD: <Feature Name>` | `CDD Monitor`, `CDD: QA Effort Breakdown` |
| Coordination & Lifecycle | `Policy: <Name>` or `<Descriptive Name>` | `Policy: Critic Coordination Engine`, `Handoff Checklist System` |
| Common Design Standards | `Design: <Name>` | `Design: Visual Standards` |
| Install, Update & Scripts | `Tool: <Name>` | `Tool: Agent Launchers`, `Tool: Config Layering` |
| Process | `Process: <Name>` | `Process: Context Guard` |
| Release Process | `Release Step: <Name>` or `Tool: <Name>` | `Release Step: Push to Remote Repository` |
| Test Infrastructure | `Dev: <Name>` or `Tool: <Name>` | `Dev: Agent Behavior Tests`, `Tool: Test Fixture Repo` |

**Rules:**
1. **Prefer existing categories.** Only create a new category when no existing one fits.
2. **Match the label prefix pattern** of the chosen category (e.g., Agent Skills labels always start with the slash command name).
3. **Slash command features** (`/pl-*`) always belong in "Agent Skills" with the label format `/pl-<command> Descriptive Name`.
4. If unsure between two categories, choose the one with more existing members (higher gravity).

## Regular Feature Files

**Required section headings** (Critic checks for these words, case-insensitive, substring match):
- A heading containing `overview`
- A heading containing `requirements`
- A heading containing `scenarios`

**Scenario heading format -- MUST use four-hash `####`:**

    #### Scenario: Title of the scenario

        Given <precondition>
        When <action>
        Then <expected outcome>

NOT valid: `**Scenario: Title**`, `### Scenario: Title`, `- Scenario: Title`

**Manual scenario block:**

    ### Manual Scenarios (Human Verification Required)

    #### Scenario: Title

        Given ...

    (Use "None." if no manual scenarios.)

## Anchor Nodes (arch_*, design_*, policy_*)

**Required section headings** (Critic checks for these words, case-insensitive, substring match):
- A heading containing `purpose`
- A heading containing `invariants`

Note: `## 1. Overview` does NOT satisfy the `purpose` check. The heading text must contain
the word "purpose" -- e.g., `## Purpose`, `## 1. Purpose`.

Scenario classification and gherkin quality checks are automatically skipped for anchor nodes.
