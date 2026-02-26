# Feature: Design Ingest Command

> Label: "Agent Skills: /pl-design-ingest"
> Category: "Agent Skills"
> Prerequisite: features/design_artifact_pipeline.md

[TODO]

## 1. Overview

The `/pl-design-ingest` command provides the Architect with a structured workflow for ingesting external design artifacts (images, PDFs, Figma URLs, live web page URLs) into the Purlin specification system. It stores artifacts per the pipeline convention, processes them into structured markdown descriptions mapped to the project's design token system, and updates the target feature's Visual Specification section. This command dynamically reads whatever `design_*.md` anchors exist in the consumer project -- it does not depend on any specific design anchor.

---

## 2. Requirements

### 2.1 Role Guard
- The command is Architect-only. Non-Architect agents MUST be rejected with: "This is an Architect command. Ask your Architect agent to run /pl-design-ingest instead."

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

- **Image/PDF:** Read using Claude's multimodal Read tool. Analyze the visual content.
- **Live web page URL:** Fetch the page using WebFetch to extract the current visual state. Extract observable CSS patterns, component structure, and computed styles.
- **Figma URL:** Record the URL. Prompt the user to provide an exported image or screenshot to process. If the user provides one, process it as an image. If not, record the URL with a placeholder description noting it needs manual processing.

After reading the artifact, the command:
1. Reads all `design_*.md` anchor nodes present in the project's `features/` directory.
2. Generates a structured markdown description covering:
   - Layout hierarchy and component inventory
   - Spacing relationships (mapped to the anchor's spacing scale if one is defined)
   - Color observations (mapped to the project's design token names from the anchor)
   - Typography observations (mapped to the project's font stack tokens from the anchor)
   - Structural elements specific to this feature
3. For live web pages: additionally documents observable CSS patterns and component structure compared against the anchor's token system.

### 2.6 Feature File Update
- Insert or update the `## Visual Specification` section in the target feature file.
- Within the section, insert or update the target `### Screen:` subsection with:
  - `- **Reference:**` pointing to the stored artifact path or URL.
  - `- **Processed:**` set to the current date (YYYY-MM-DD).
  - `- **Description:**` containing the generated structured prose.
  - Draft visual acceptance checklist items (`- [ ]`) derived from the description.
- If the feature file does not yet have a `> **Design Anchor:**` declaration, add one referencing the most relevant `design_*.md` anchor found in the project.

### 2.7 Commit Protocol
- The command commits the artifact file (if local) and the feature spec update together in a single commit.
- Commit message format: `spec(<feature_stem>): ingest design artifact for <screen_name>`.

### 2.8 Design-System Agnostic Token Resolution
- The command reads the project's `design_*.md` anchors at runtime to discover the token system.
- Color values observed in artifacts are mapped to the nearest token name declared in the anchor.
- Font observations are mapped to the anchor's font stack tokens.
- If no design anchor exists in the project, the description uses literal observations without token mapping, and a note is added: "No design anchor found -- descriptions use literal values. Create a `design_*.md` anchor to enable token mapping."

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Ingest Local Image Artifact

    Given a feature file "features/my_feature.md" exists with no Visual Specification section
    And a design image "mockup.png" exists at a local path
    When the Architect runs /pl-design-ingest with the image path targeting my_feature screen "Main Dashboard"
    Then the image is copied to "features/design/my_feature/mockup.png"
    And the feature file is updated with a Visual Specification section
    And the section contains a "Screen: Main Dashboard" subsection
    And the Reference line points to the stored artifact path
    And the Processed date is set to today
    And a structured Description is generated
    And draft checklist items are created

#### Scenario: Ingest Figma URL

    Given a feature file "features/my_feature.md" exists
    When the Architect runs /pl-design-ingest with a public Figma URL targeting screen "Settings Panel"
    Then the Figma URL is recorded in the Reference line as [Figma](<url>)
    And the user is prompted for an exported image or screenshot
    And if no export is provided the Description notes manual processing is needed

#### Scenario: Ingest Live Web Page URL

    Given a feature file "features/my_feature.md" exists
    And a design anchor "features/design_visual_standards.md" exists with color tokens
    When the Architect runs /pl-design-ingest with a live web page URL targeting screen "Current UI"
    Then the URL is recorded in the Reference line as [Live](<url>)
    And the page content is fetched via WebFetch
    And the Description includes observable CSS patterns and component structure
    And color observations are mapped to the design anchor's token names

#### Scenario: Re-Process Updated Artifact

    Given a feature file "features/my_feature.md" has a Visual Specification with screen "Main Dashboard"
    And the screen has a Reference to "features/design/my_feature/dashboard-layout.png"
    And the image file has been updated since the Processed date
    When the Architect runs /pl-design-ingest with the re-process flag for my_feature screen "Main Dashboard"
    Then the image is re-read and a new Description is generated
    And the Processed date is updated to today
    And the previous Description is replaced

#### Scenario: Anchor Inheritance Token Mapping

    Given a design anchor "features/design_visual_standards.md" defines color tokens including "--accent: #38BDF8"
    And a design artifact shows a blue button
    When the artifact is processed by /pl-design-ingest
    Then the Description maps the blue button color to "var(--accent)" (not the literal hex value)
    And typography observations reference the anchor's font token names

#### Scenario: No Design Anchor Fallback

    Given no design_*.md anchor files exist in the project's features/ directory
    When the Architect runs /pl-design-ingest with a local image
    Then the Description uses literal color and font observations
    And a note is appended: "No design anchor found -- descriptions use literal values"

### Manual Scenarios (Human Verification Required)

None.
