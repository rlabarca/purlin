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
- `> Web Test: <url>` -- declares the feature's web UI is accessible at `<url>` for automated web testing via `/pl-web-test`. Features without this annotation use `/pl-verify` (manual). Example: `> Web Test: http://localhost:9086`. Legacy `> AFT Web:` is accepted for backward compatibility.
- `> Web Start: <command>` -- auto-start command for the target system. When the server at the `Web Test` URL is not reachable, this command is executed to start it before verification. Example: `> Web Start: /pl-cdd`. Legacy `> AFT Start:` is accepted for backward compatibility.
- `> Owner: PM` or `> Owner: Architect` -- declares which role owns design decisions and dispute resolution for this feature. Default when absent: Architect. Anchor nodes (`arch_*`, `design_*`, `policy_*`) are always Architect-owned; the tag is ignored if present on an anchor. The Owner tag is sticky -- it persists through edits by any agent. Architect can edit PM-owned features (spec gate fixes, prerequisite additions) without changing ownership. The Critic uses this tag to route SPEC_DISPUTEs: disputes on `> Owner: PM` features or referencing Visual Specification screens route to PM; all others route to Architect.
- `> Figma Status: <status>` -- Figma design's dev mode status at time of last ingestion. Values: `Design`, `Ready for Dev`, `Completed`. Set by PM during `/pl-design-ingest`. Advisory gate for Builder work queue: the Critic generates a LOW-priority PM action item when a feature is in Builder TODO state with `Figma Status: Design`.
- `> Test Fixtures: <url>` -- non-default fixture repo URL (local path or remote URL). Most features use the convention path (`.purlin/runtime/fixture-repo`) and do not need this field. Only add when the feature's fixtures live in a different repo.

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
| Process | `Process: <Name>` | `Process: Spec-Code Audit Role Clarity` |
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

## Fixture Tag Section Format

Features that use test fixtures declare their fixture tags in a dedicated subsection within
Requirements. The Critic parses this section to validate that declared tags exist in the
fixture repo.

**Heading convention:** Use a three-hash heading with a numbered subsection:

    ### 2.x Integration Test Fixture Tags

or:

    ### 2.x Web Test Fixture Tags

**Table format:**

    | Tag | State Description |
    |-----|-------------------|
    | `main/feature_name/slug` | Description of the project state this tag represents |

**Tag naming:** `<project-ref>/<feature-name>/<slug>`. The slug is Architect-chosen (2-4
words, kebab-case) and describes the fixture state, not the scenario title. Examples:
`ahead-3`, `empty-repo`, `expert-mode`.

**Placement:** The fixture tag section is the last subsection in Requirements, immediately
before the `---` separator that precedes the Scenarios section.

**Cross-feature tag references:** When a scenario in feature A needs a fixture tag declared
in feature B, the scenario's Given step references the full tag path. No duplication of the
tag table is needed -- the Critic resolves tags across all feature files in the project.
