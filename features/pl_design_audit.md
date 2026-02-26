# Feature: Design Audit Command

> Label: "Agent Skills: /pl-design-audit"
> Category: "Agent Skills"
> Prerequisite: features/design_artifact_pipeline.md
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The `/pl-design-audit` command provides the Architect with a comprehensive audit of all design artifacts and visual specifications across the project. It validates reference integrity, detects staleness, checks anchor consistency, and produces a summary report. This command complements the Critic's automated visual spec checks with a deeper, on-demand analysis that the Architect can run during design reviews or before releases.

---

## 2. Requirements

### 2.1 Role Guard
- The command is Architect-only. Non-Architect agents MUST be rejected with: "This is an Architect command. Ask your Architect agent to run /pl-design-audit instead."

### 2.2 Inventory Scan
- Scan all `features/*.md` files for `## Visual Specification` sections.
- For each section, extract per-screen data: `### Screen:` name, `- **Reference:**` path/URL, `- **Processed:**` date, `- **Description:**` presence and content, and checklist items (`- [ ]` / `- [x]`).

### 2.3 Reference Integrity
- **Local files:** Verify the referenced file exists on disk. Missing files are reported as CRITICAL.
- **URLs (Figma, Live):** Validate URL syntax only (no live connectivity check without MCP). Malformed URLs are reported as WARNING.
- **No reference:** Screens with a `- **Description:**` but no `- **Reference:**` are reported as WARNING (description exists without a backing artifact).
- **No description:** Screens with a `- **Reference:**` but no `- **Description:**` are reported as HIGH (unprocessed artifact).

### 2.4 Staleness Check
- For local artifact files: compare the file's modification time against the `- **Processed:**` date.
- If the artifact file is newer than the processed date, flag the screen as STALE.
- Screens with `- **Processed:** N/A` that have a local reference are flagged as UNPROCESSED (same as no description).

### 2.5 Anchor Consistency Check
- Read the project's `design_*.md` anchor nodes.
- Scan all `- **Description:**` content for literal values that should reference the anchor's design tokens:
  - Hardcoded hex colors (e.g., `#38BDF8`) that match or approximate an anchor token value.
  - Hardcoded font names (e.g., `Montserrat`) that should reference a font token.
  - Hardcoded spacing values that match an anchor's spacing scale (if defined).
- Flag each literal value as WARNING with a suggestion to use the corresponding token name.

### 2.6 Audit Report
- Print a summary table with columns: Feature, Screen, Reference Status, Staleness, Anchor Consistency.
- Reference Status values: OK, MISSING (critical), MALFORMED_URL, NO_REF, UNPROCESSED.
- Staleness values: CURRENT, STALE, N/A (URL reference or no processed date).
- Anchor Consistency values: CLEAN, N warnings.
- For STALE items, offer to re-ingest by running `/pl-design-ingest` with the re-process flag.

### 2.7 Exit Codes
- If any CRITICAL issues are found (missing local references), the audit reports "CRITICAL issues found -- resolve before release."
- If only WARNINGs exist, the audit reports "Warnings found -- review recommended."
- If no issues are found, the audit reports "All design artifacts clean."

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Inventory Scan Discovers All Visual Specs

    Given three feature files exist with Visual Specification sections
    And one feature file exists without a Visual Specification section
    When the Architect runs /pl-design-audit
    Then the audit scans all four feature files
    And the report includes entries for the three features with visual specs
    And the feature without a visual spec is not listed

#### Scenario: Missing Local Reference Detected

    Given a feature has a Visual Specification screen referencing "features/design/my_feature/mockup.png"
    And the file does not exist on disk
    When the Architect runs /pl-design-audit
    Then the screen is reported with Reference Status MISSING
    And the overall audit reports CRITICAL issues

#### Scenario: Stale Description Detected

    Given a feature has a Visual Specification screen with Processed date 2025-01-15
    And the referenced local artifact was modified on 2025-02-01
    When the Architect runs /pl-design-audit
    Then the screen is reported as STALE
    And the audit offers to re-ingest the artifact

#### Scenario: Unprocessed Artifact Detected

    Given a feature has a Visual Specification screen with a Reference to a local file
    And the screen has no Description field
    When the Architect runs /pl-design-audit
    Then the screen is reported as UNPROCESSED
    And a HIGH-priority item is generated

#### Scenario: Anchor Consistency Hardcoded Color Warning

    Given a design anchor defines "--purlin-accent: #38BDF8"
    And a feature's Visual Specification Description contains the literal text "#38BDF8"
    When the Architect runs /pl-design-audit
    Then the Description is flagged with an anchor consistency WARNING
    And the suggestion says to use "var(--purlin-accent)" instead

#### Scenario: Clean Audit Report

    Given all features with Visual Specifications have valid references, current descriptions, and no literal values
    When the Architect runs /pl-design-audit
    Then the audit reports "All design artifacts clean"
    And no CRITICAL or WARNING items are listed

### Manual Scenarios (Human Verification Required)

None.
