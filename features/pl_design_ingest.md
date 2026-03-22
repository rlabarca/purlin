# Feature: Design Ingest Command

> Label: "/pl-design-ingest Design Ingest"
> Category: "Agent Skills"
> Prerequisite: features/design_artifact_pipeline.md

[Complete]

## 1. Overview

The `/pl-design-ingest` command provides the PM with a structured workflow for ingesting external design artifacts (images, PDFs, Figma URLs, live web page URLs) into the Purlin specification system. It stores artifacts per the pipeline convention, processes them into a Token Map and visual acceptance checklists mapped to the project's design token system, and generates a `brief.json` design data cache when Figma MCP is available. It updates the target feature's Visual Specification section. This command dynamically reads whatever `design_*.md` anchors exist in the consumer project -- it does not depend on any specific design anchor.

---

## 2. Requirements

### 2.1 Role Guard
- The command is PM-only. The PM is the sole consumer of design ingestion.
- All other agents (Architect, Builder, QA) MUST be rejected with: "This is a PM command. Ask your PM agent to run /pl-design-ingest instead."

### 2.2 Input Modes
The command accepts one of the following inputs:
- **(a) Local file path** to an image (PNG, JPG, SVG) or PDF.
- **(b) Figma public URL** -- the URL itself is recorded as the reference (no download).
- **(c) Live web page URL** -- recorded as `[Live](<url>)` in the reference line.
- **(d) Re-process flag** for an existing artifact that has been updated. The command re-reads the artifact and regenerates the description.

### 2.3 Target Determination
- The Architect specifies which feature file and which screen within it the artifact targets.
- If the target feature has no `## Visual Specification` section, the command creates one.
- If the target screen subsection (`### Screen: <name>`) does not exist, the command creates it.

### 2.4 Artifact Storage
- For local file inputs: copy the file to `features/design/<feature_stem>/` with a descriptive name per the pipeline storage convention.
- For URL inputs (Figma, live web page): the URL itself is the reference. No file is downloaded or stored locally.
- The `features/design/<feature_stem>/` directory is created if it does not exist.

### 2.5 Processing Workflow
The command processes the artifact according to its type:

- **Image/PDF:** Read using Claude's multimodal Read tool. Analyze the visual content. Extract observable design tokens (colors, spacing, typography) and map them to the project's token system via the Token Map.
- **Live web page URL:** Fetch the page using WebFetch to extract the current visual state. Extract observable CSS patterns, component structure, and computed styles. Map observed values to the project's token system via the Token Map.
- **Figma URL with MCP available:** Call Figma MCP tools to extract: component tree structure, auto-layout properties, design variables (colors, spacing, typography), component variants and states, and annotations/comments. Processing proceeds in two sub-steps:
  1. **Annotation extraction:** Call `get_design_context` on the frame. Extract annotations containing behavioral notes (states, interactions, edge cases). Present extracted behavioral notes to the user: "I found these behavioral notes in the Figma annotations: [list]. I'll use these to draft scenarios -- let me know if any are outdated." If annotations contain behavioral notes, draft Gherkin scenario outlines from them and present to the user for confirmation before finalizing.
  2. **Identity token detection:** After extracting design variables via MCP, compare each variable name against the project's design anchor token list. For matches (with or without `var()` / `--` prefix normalization), auto-generate identity Token Map entries. Report: "N of M Figma variables match project tokens (identity mappings). K require manual mapping."
  Generate the Token Map automatically by mapping Figma design variable names to the project's token system. For identity mappings (Figma name matches project token), auto-generate entries without user input. Also generate `brief.json` (see Section 2.5.1).
- **Figma URL without MCP:** Record the URL. Prompt the user to provide an exported image or screenshot to process. If the user provides one, process it as an image. If not, record the URL with a placeholder Token Map noting it needs manual processing. Add note: "For higher fidelity, install Figma MCP: `claude mcp add --transport http figma https://mcp.figma.com/mcp`"

After reading the artifact, the command:
1. Reads all `design_*.md` anchor nodes present in the project's `features/` directory.
2. Generates a Token Map mapping design token names to the project's token system.
3. Generates visual acceptance checklist items derived from measurable design properties (dimensions, spacing, colors, typography, layout).
4. For live web pages: additionally maps observable CSS properties and component structure against the anchor's token system.

### 2.5.1 Design Brief Generation (Figma MCP Only)
When processing a Figma URL with MCP available, the command MUST also generate a `brief.json` at `features/design/<feature_stem>/brief.json`. This compact, machine-readable file provides the Builder with structured design data without requiring Figma MCP access during implementation.

The brief includes:
- `figma_url`: The source Figma URL.
- `figma_last_modified`: The design's `lastModified` timestamp from MCP.
- `screens`: Per-screen data with node ID, dimensions, component inventory (name, size, spacing, layout properties), and auto-layout constraints.
- `tokens`: Figma design variable names and their resolved values.

The brief is NOT generated for non-Figma inputs (images, PDFs, live web pages) or when Figma MCP is unavailable.

### 2.5.2 Code Connect Data Extraction (Figma MCP Only)
When the MCP response includes Code Connect data (component code references, property mappings), the PM includes this data in `brief.json` under a `code_connect` key. Each entry maps a component name to its source file path, property configuration, and Figma node ID.

- Report: "Code Connect data found for N components. Included in brief.json for Builder reference."
- If no Code Connect data is present in the MCP response, the `code_connect` key is omitted from `brief.json` (no error, no warning).
- Code Connect data supplements the Token Map -- it does not replace it.

### 2.5.3 Figma Dev Status Extraction (Figma MCP Only)
During ingestion of a Figma URL with MCP available, the command reads the Figma frame's dev mode status (Design, Ready for Dev, or Completed).

- If available, set `> Figma Status: <status>` in the feature spec's blockquote metadata section.
- Include the status in `brief.json` as `figma_dev_status` (`"ready_for_dev"`, `"completed"`, or `null`).
- Include the Figma file version ID in `brief.json` as `figma_version_id` for precise staleness detection.
- Report: "Figma dev status: Ready for Dev" (or current status).
- If the dev status is unavailable (e.g., free/Pro plan without Dev Mode), omit silently -- no `> Figma Status:` line, `figma_dev_status` set to `null`.

### 2.9 Dev Resources Linking (Optional)
After ingestion of a Figma URL with MCP available, the PM may optionally attach the feature spec URL to the Figma node via the Dev Resources API. This creates bidirectional traceability visible to designers in Figma Dev Mode.

- Prompt the user for confirmation before writing to Figma.
- PM-only (consistent with the Figma Write Policy).
- If the user declines or Dev Resources API is unavailable, skip silently.

### 2.6 Feature File Update
- Insert or update the `## Visual Specification` section in the target feature file.
- Within the section, insert or update the target `### Screen:` subsection with:
  - `- **Reference:**` pointing to the stored artifact path or URL.
  - `- **Processed:**` set to the current date (YYYY-MM-DD).
  - `- **Token Map:**` containing the generated token mappings (Figma design variable names -> project tokens).
  - Draft visual acceptance checklist items (`- [ ]`) derived from measurable design properties.
- Do NOT generate a `- **Description:**` prose paragraph. The Token Map + checklists replace prose descriptions.
- **Design anchor declaration (mandatory):** If the feature file does not yet have a `> **Design Anchor:**` declaration, add one referencing the most relevant `design_*.md` anchor found in the project. On re-ingestion (re-process mode), verify the existing anchor declaration still matches the design tokens used. If a different anchor is more appropriate (e.g., anchor was added or reorganized since the original ingestion), update the declaration and report: "Updated design anchor from `<old>` to `<new>`."

### 2.7 Commit Protocol
- The command commits the artifact file (if local) and the feature spec update together in a single commit.
- Commit message format: `spec(<feature_stem>): ingest design artifact for <screen_name>`.

### 2.8 Design-System Agnostic Token Resolution
- The command reads the project's `design_*.md` anchors at runtime to discover the token system.
- Figma design variable names are mapped to the corresponding project token names declared in the anchor.
- Color tokens, font tokens, and spacing tokens are all mapped through the Token Map.
- If no design anchor exists in the project, the Token Map uses literal values (e.g., `` `primary` -> `#2196F3` ``), and a note is added: "No design anchor found -- Token Map uses literal values. Create a `design_*.md` anchor to enable token mapping."

---

## 3. Scenarios

### Unit Tests
#### Scenario: Ingest Local Image Artifact

    Given a feature file "features/my_feature.md" exists with no Visual Specification section
    And a design image "mockup.png" exists at a local path
    When the PM runs /pl-design-ingest with the image path targeting my_feature screen "Main Dashboard"
    Then the image is copied to "features/design/my_feature/mockup.png"
    And the feature file is updated with a Visual Specification section
    And the section contains a "Screen: Main Dashboard" subsection
    And the Reference line points to the stored artifact path
    And the Processed date is set to today
    And a Token Map is generated mapping observed design tokens to the project's token system
    And draft checklist items are created

#### Scenario: Ingest Figma URL Without MCP

    Given a feature file "features/my_feature.md" exists
    And Figma MCP tools are not available in the current session
    When the PM runs /pl-design-ingest with a public Figma URL targeting screen "Settings Panel"
    Then the Figma URL is recorded in the Reference line as [Figma](<url>)
    And the user is prompted for an exported image or screenshot
    And if no export is provided the Token Map notes manual processing is needed
    And a note suggests installing Figma MCP for higher fidelity

#### Scenario: Figma MCP Auto-Setup When Processing Figma URL

    Given a Figma URL is provided for ingestion
    And Figma MCP tools are not available in the current session
    When /pl-design-ingest attempts to process the URL
    Then the skill provides MCP installation instructions
    And falls back to Tier 1/2 processing (prompt for export)

#### Scenario: Figma MCP Extracts Design Context Directly

    Given a Figma URL is provided for ingestion
    And Figma MCP tools are available
    When /pl-design-ingest processes the URL
    Then design metadata is extracted via MCP (layout, tokens, components)
    And the Token Map is auto-generated mapping Figma design variables to project tokens
    And a brief.json is generated at features/design/<feature_stem>/brief.json
    And the brief.json contains figma_url, figma_last_modified, screens, and tokens
    And the Reference identifies the Figma source (as [Figma](<url>) or compact node reference)

#### Scenario: Ingest Live Web Page URL

    Given a feature file "features/my_feature.md" exists
    And a design anchor "features/design_visual_standards.md" exists with color tokens
    When the PM runs /pl-design-ingest with a live web page URL targeting screen "Current UI"
    Then the URL is recorded in the Reference line as [Live](<url>)
    And the page content is fetched via WebFetch
    And the Token Map maps observable CSS properties to the design anchor's token names
    And checklist items are derived from the page's measurable visual properties

#### Scenario: Re-Process Updated Artifact

    Given a feature file "features/my_feature.md" has a Visual Specification with screen "Main Dashboard"
    And the screen has a Reference to "features/design/my_feature/dashboard-layout.png"
    And the image file has been updated since the Processed date
    When the PM runs /pl-design-ingest with the re-process flag for my_feature screen "Main Dashboard"
    Then the image is re-read and a new Token Map is generated
    And the Processed date is updated to today
    And the previous Token Map is replaced
    And checklist items are updated to reflect the new design

#### Scenario: Anchor Inheritance Token Mapping

    Given a design anchor "features/design_visual_standards.md" defines color tokens including "--accent: #38BDF8"
    And a Figma design uses a variable named "primary" with value #38BDF8
    When the artifact is processed by /pl-design-ingest
    Then the Token Map maps "primary" to "var(--accent)" (not the literal hex value)
    And all design token entries reference the anchor's token names

#### Scenario: No Design Anchor Fallback

    Given no design_*.md anchor files exist in the project's features/ directory
    When the PM runs /pl-design-ingest with a local image
    Then the Token Map uses literal values for token mappings
    And a note is appended: "No design anchor found -- Token Map uses literal values"

#### Scenario: Identity Token Auto-Detection During Figma Ingestion

    Given a Figma design has variables named "--app-bg" and "--app-text"
    And a design anchor defines tokens "--app-bg" and "--app-text"
    And Figma MCP tools are available
    When the PM runs /pl-design-ingest with the Figma URL
    Then the Token Map contains identity entries auto-generated without user input
    And the PM reports "2 of 2 Figma variables match project tokens (identity mappings). 0 require manual mapping."
    And each identity entry maps the Figma name to its var() equivalent

#### Scenario: Code Connect Data Extracted Into Brief

    Given a Figma design has Code Connect mappings published for component "Card"
    And the MCP response includes code reference data
    When /pl-design-ingest processes the Figma URL
    Then brief.json contains a "code_connect" key
    And the "Card" entry includes source_file, props, and figma_node_id
    And the PM reports "Code Connect data found for 1 component"

#### Scenario: Annotation Extraction Pre-Populates Behavioral Context

    Given a Figma frame has annotations describing empty state and loading behavior
    And Figma MCP tools are available
    When the PM runs /pl-design-ingest with the Figma URL
    Then the PM presents extracted behavioral notes before probing
    And draft Gherkin scenario outlines are generated from the annotations
    And probing questions skip topics already covered by annotations

#### Scenario: Figma Dev Status Extracted During Ingestion

    Given a Figma frame is marked "Ready for Dev" in Dev Mode
    And Figma MCP tools are available
    When /pl-design-ingest processes the Figma URL
    Then the feature spec contains "> Figma Status: Ready for Dev"
    And brief.json contains "figma_dev_status": "ready_for_dev"
    And brief.json contains a "figma_version_id" field

#### Scenario: Dev Status Not Available Silently Omitted

    Given a Figma frame has no dev status set
    When /pl-design-ingest processes the Figma URL
    Then the feature spec does NOT contain a "> Figma Status:" line
    And brief.json contains "figma_dev_status": null

### QA Scenarios
None.

