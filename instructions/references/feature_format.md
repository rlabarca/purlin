# Feature File Format Reference

> This file is loaded on-demand by `/pl-spec` and `/pl-anchor` commands.
> It contains heading format rules and parser requirements.

The scan parser enforces specific Markdown heading formats. Wrong heading levels or
section names cause Spec Gate failures that are not obvious from the error message.

## Template Files

**MANDATE:** When creating a new feature file or anchor node, you MUST copy from the template as the starting point. Do NOT create feature files from memory or scratch. When updating an existing feature file, consult the template to verify section structure is correct. The template is the authoritative reference for required sections, heading formats, and section order.

Copy from `{tools_root}/feature_templates/`:
- `_feature.md` -- regular feature file
- `_anchor.md` -- anchor node (arch_*, design_*, policy_*)

**No Implementation Notes section:** Feature files do NOT contain an `## Implementation Notes` section. All implementation knowledge belongs in companion files (`features/<name>.impl.md`). See HOW_WE_WORK_BASE Section 4.3 and BUILDER_BASE Section 5.2 for the companion file convention.

## Blockquote Metadata

Feature files use `>` blockquote lines at the top for metadata. Supported metadata fields:

- `> Label: "Human-Readable Name"` -- display name for status reports.
- `> Category: "Category Name"` -- grouping for status reports.
- `> Prerequisite: features/<name>.md` -- dependency link to an anchor node or foundation feature.
- `> Web Test: <url>` -- declares the feature's web UI is accessible at `<url>` for automated web testing via `/pl-web-test`. Features without this annotation use `/pl-verify` (manual). Example: `> Web Test: http://localhost:9086`. Legacy `> AFT Web:` is accepted for backward compatibility.
- `> Web Start: <command>` -- auto-start command for the target system. When the server at the `Web Test` URL is not reachable, this command is executed to start it before verification. Example: `> Web Start: /pl-server`. Legacy `> AFT Start:` is accepted for backward compatibility.
- `> Owner: PM` or `> Owner: Architect` -- declares which role owns design decisions and dispute resolution for this feature. Default when absent: Architect. Anchor nodes (`arch_*`, `design_*`, `policy_*`) are always Architect-owned; the tag is ignored if present on an anchor. The Owner tag is sticky -- it persists through edits by any agent. Architect can edit PM-owned features (spec gate fixes, prerequisite additions) without changing ownership. This tag is used to route SPEC_DISPUTEs: disputes on `> Owner: PM` features or referencing Visual Specification screens route to PM; all others route to Architect.
- `> Figma Status: <status>` -- Figma design's dev mode status at time of last ingestion. Values: `Design`, `Ready for Dev`, `Completed`. Set by PM during `/pl-design-ingest`. Advisory gate for Builder work queue: a LOW-priority PM action item is generated when a feature is in Builder TODO state with `Figma Status: Design`.
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
| Tools | `Tool: <Descriptive Name>` | `Tool: Config Layering` |
| Coordination & Lifecycle | `Policy: <Name>` or `<Descriptive Name>` | `Handoff Checklist System` |
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

**Required section headings** (the scan checks for these words, case-insensitive, substring match):
- A heading containing `overview`
- A heading containing `requirements`
- A heading containing `scenarios`

**Scenario heading format -- MUST use four-hash `####`:**

    #### Scenario: Title of the scenario

        Given <precondition>
        When <action>
        Then <expected outcome>

NOT valid: `**Scenario: Title**`, `### Scenario: Title`, `- Scenario: Title`

**Scenario section headings (new names):**

    ### Unit Tests

    #### Scenario: Title
        ...

    ### QA Scenarios

    #### Scenario: Title
        ...
    #### Scenario: Title @auto
        ...
    #### Scenario: Title @manual
        ...

    (Use "None." if no QA scenarios.)

**Scenario classification tags (`@auto`, `@manual`):** QA Scenarios start **untagged** when the Architect or PM writes them. On QA's first verification pass, every untagged scenario gets classified:

*   **`@auto`** — QA determined the scenario can be automated and authored regression JSON for it. On future sessions, the harness runner executes it without human involvement. Example: `#### Scenario: Widget renders correctly @auto`
*   **`@manual`** — QA determined the scenario requires human judgment, or the user declined automation. QA never re-proposes automation for `@manual` scenarios. Example: `#### Scenario: Hardware calibration check @manual`

**Lifecycle:** `untagged` (Architect/PM writes) → QA proposes automation → `@auto` (if feasible and approved) or `@manual` (if declined or infeasible). No scenario stays untagged after QA's first pass.

**Architects and PMs MUST NOT add `@auto` or `@manual` tags.** These are QA-authored classification outputs, not spec inputs. Write scenarios untagged; QA classifies them.

**Gradual migration:** The scan accepts BOTH old (`### Automated Scenarios`, `### Manual Scenarios (Human Verification Required)`) and new (`### Unit Tests`, `### QA Scenarios`) headings. Agents rename to the new format when touching a spec.

## Test Priority Tier Classification

**MANDATE:** When creating or refining a feature spec, the Architect MUST evaluate whether the feature warrants a non-default tier classification in `QA_OVERRIDES.md` under `## Test Priority Tiers`.

**Tier decision prompt (ask yourself):**
1. **If this feature breaks, is the app unusable?** Can agents start up? Can the scan run? Can projects initialize? If yes → `smoke`.
2. **Is this an edge case, polish, or rarely-used path?** If yes → `full-only`.
3. **Neither extreme?** Leave unclassified (defaults to `standard`).

Features that are prerequisites for many others, or that gate the entire workflow (scan, config, init, launchers), are strong smoke candidates. Features not listed in the tier table default to `standard` — only add entries for `smoke` or `full-only`.

## Anchor Nodes (arch_*, design_*, policy_*)

**Required section headings** (the scan checks for these words, case-insensitive, substring match):
- A heading containing `purpose`
- A heading containing `invariants`

Note: `## 1. Overview` does NOT satisfy the `purpose` check. The heading text must contain
the word "purpose" -- e.g., `## Purpose`, `## 1. Purpose`.

Scenario classification and gherkin quality checks are automatically skipped for anchor nodes.

## Regression Guidance Section (Optional)

Feature files MAY contain a `## Regression Guidance` section with bullet points describing
behaviors that are regression-worthy. PM or Architect adds these hints during spec authoring
to signal which behaviors deserve independent regression coverage by QA.

**Placement:** After `## Visual Specification` (if present) or after `## 3. Scenarios`,
as the last content section before end-of-file.

**Format:**

    ## Regression Guidance
    - <Behavior description: what to verify and why it is fragile>
    - <Another behavior>

**Example:**

    ## Regression Guidance
    - Idempotent repeated runs: verify no file changes on second init
    - Launcher script repair after manual deletion
    - Config and overrides untouched during refresh mode

**Scan interaction:** The scan detects this section and, when the feature reaches
`builder: "DONE"`, generates MEDIUM-priority QA action items with category
`regression_guidance_pending`. The Builder ignores this section entirely.

## Fixture Tag Section Format

Features that use test fixtures declare their fixture tags in a dedicated subsection within
Requirements. The scan parses this section to validate that declared tags exist in the
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
tag table is needed -- the scan resolves tags across all feature files in the project.
