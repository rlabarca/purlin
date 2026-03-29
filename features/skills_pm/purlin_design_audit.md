# Feature: Design Audit Command

> Label: "Agent Skills: PM: purlin:design-audit Design Audit"
> Category: "Agent Skills: PM"
> Prerequisite: design_artifact_pipeline.md

[TODO]

## 1. Overview

The `purlin:design-audit` command provides the PM and PM with a comprehensive audit of all design artifacts and visual specifications across the project. It validates reference integrity, detects staleness, checks anchor consistency, and produces a summary report. This command provides a deeper, on-demand analysis that PM mode can run during design reviews or before releases.

---

## 2. Requirements

### 2.1 Role Guard
- The command is shared between PM and PM. The PM is the primary consumer; PM mode retains access for release checks and gap analysis.
- Engineer and QA agents MUST be rejected with: "This is a PM command. Ask your PM or PM agent to run purlin:design-audit instead."

### 2.2 Inventory Scan
- Scan all `features/*.md` files for `## Visual Specification` sections.
- For each section, extract per-screen data: `### Screen:` name, `- **Reference:**` path/URL, `- **Processed:**` date, `- **Token Map:**` presence and entries, and checklist items (`- [ ]` / `- [x]`).
- Also glob `features/i_design_*.md` to collect all design invariants. Read each pointer's `> Version:`, `> Source:`, `> Synced-At:`, and `> Scope:` metadata.
- Also scan for `brief.json` at `features/_design/<feature_stem>/brief.json` for each feature with a Figma reference.
- If Figma MCP is available, also extract annotation count per screen via `get_design_context`. Report as informational metadata (not a pass/fail check).

### 2.3 Reference Integrity
- **Local files:** Verify the referenced file exists on disk. Missing files are reported as CRITICAL.
- **URLs (Figma, Live):** Validate URL syntax only (no live connectivity check without MCP). Malformed URLs are reported as WARNING.
- **No reference:** Screens with a `- **Token Map:**` but no `- **Reference:**` are reported as WARNING (Token Map exists without a backing artifact).
- **No Token Map:** Screens with a `- **Reference:**` but no `- **Token Map:**` are reported as HIGH (unprocessed artifact).

### 2.4 Staleness Check
- For local artifact files: compare the file's modification time against the `- **Processed:**` date.
- If the artifact file is newer than the processed date, flag the screen as STALE.
- Screens with `- **Processed:** N/A` that have a local reference are flagged as UNPROCESSED (same as no Token Map).

### 2.5 Figma Staleness Detection (MCP)
- When Figma MCP tools are available and a screen references a Figma URL, read the design's `lastModified` timestamp via MCP.
- Compare against the `- **Processed:**` date. If the Figma design was modified after the Token Map was generated, flag as STALE.
- When Figma MCP is not available, Figma URL screens report staleness as N/A (no connectivity check).

### 2.5.1 Brief Staleness Detection
- For features with a Figma reference, check for `brief.json` at `features/_design/<feature_stem>/brief.json`.
- If `brief.json` exists, compare `figma_last_modified` in the brief against the spec's `- **Processed:**` date. If the brief is newer, flag the spec as STALE (the Figma design has been updated since last ingestion).
- If `brief.json` is missing and the screen has a Figma reference, report as WARNING: "No brief.json found -- Engineer has no local design data cache."

### 2.6 Design-Spec Conflict Detection (MCP)
- When Figma MCP tools are available, extract design variable names and values from the Figma design.
- Compare against the Token Map entries in the Visual Specification.
- Flag discrepancies as `DESIGN_CONFLICT` warnings with specific differences listed (e.g., "Token Map maps `primary` to `var(--accent)`, but Figma design variable `primary` has been renamed to `brand-primary`").
- Also compare Figma design variable resolved values against `brief.json` token values (if present) to detect drift between the two caches.

### 2.6.1 Invariant Pointer Sync Status
For each design invariant (`features/i_design_*.md`) collected in the inventory scan:
- **Figma-sourced:** Fetch current version ID via MCP and compare against the pointer's `> Version:`. If different: `STALE_INVARIANT`.
- **Git-sourced:** Run `git ls-remote` and compare SHA against `> Source-SHA:`. If different: `STALE_INVARIANT`.
- For each stale invariant, check cascade impact: how many features depend on it (directly or transitively).
- Compare `brief.json` version against pointer version: if the pointer is newer than the brief, flag as `STALE_BRIEF`.

### 2.6.2 Invariant-Governed Design Compliance
Enforce a three-tier weight model for invariant design constraints:

| Aspect | Weight | Rationale |
|--------|--------|-----------|
| Colors / design tokens | **Strict** — hardcoded hex values flagged as HIGH | Colors are objective, machine-verifiable |
| Typography (font families, weights, sizes) | **Strict** — must match brief.json, flagged as HIGH | Measurable properties from design data |
| Spacing / layout | **Moderate** — warned as MEDIUM, not blocked | Subjective tolerance acceptable |

- Scan feature code for FORBIDDEN patterns from design invariants.
- Surface invariant `## Design Invariants` statements as compliance context.
- Violations are reported as `INVARIANT_VIOLATION` in the audit report.

### 2.7 Anchor Consistency Check
- Read the project's `design_*.md` anchor nodes and `i_design_*.md` invariant pointers.
- Scan all Token Map entries for consistency with the anchor's token system:
  - Token Map right-side values (project tokens) that do not match any token declared in the anchor.
  - Hardcoded hex colors or literal values on the right side of Token Map entries that should reference anchor token names.
  - Checklist items containing hardcoded values that should use token references.
- Flag each inconsistency as WARNING with a suggestion to use the corresponding anchor token name.

### 2.8 Audit Report
- Print a summary table with columns: Feature, Screen, Reference Status, Staleness, Brief Status, Invariant, Anchor Consistency, Design Conflict, Dev Status, Annotations (optional -- shown when Figma MCP is available, otherwise omitted). The Dev Status column shows CURRENT, DRIFT, or N/A. The Annotations column shows the annotation count per screen or "N/A" when Figma MCP is not available. Both Dev Status and Annotations are informational metadata only -- they do not affect pass/fail status.
- Reference Status values: OK, MISSING (critical), MALFORMED_URL, NO_REF, UNPROCESSED.
- Staleness values: CURRENT, STALE, N/A (URL reference or no processed date).
- Brief Status values: CURRENT, STALE, MISSING, N/A (non-Figma reference).
- Invariant values: CURRENT, STALE_INVARIANT, STALE_BRIEF, INVARIANT_VIOLATION, N/A.
- Anchor Consistency values: CLEAN, N warnings.
- Dev Status values: CURRENT, DRIFT, N/A (no Figma Status metadata, no MCP, or no Figma reference).
- After the per-feature table, print a **Design Invariants** summary table showing each invariant's source, version, sync status, and dependent feature count.
- For STALE items, offer to re-process via `purlin:spec <feature>` (update Visual Specification). For STALE_INVARIANT items, offer `purlin:invariant sync <invariant-file>`. For STALE_BRIEF items, offer `purlin:spec <feature>` (regenerate brief). For INVARIANT_VIOLATION items, report file:line evidence and suggest fix.

### 2.10 Figma Dev Status Consistency Check
For features with `> Figma Status:` metadata and a Figma reference, check the current dev status via Figma MCP (when available).

- Compare the current Figma dev status against the spec's `> Figma Status:` value.
- Discrepancies are flagged as INFO (not errors) with a suggestion to update the spec.
- Add a "Dev Status" column to the audit report table. Values: CURRENT (matches), DRIFT (mismatch), N/A (no Figma Status metadata, no MCP, or no Figma reference).

### 2.11 Version ID Drift Detection
When `brief.json` contains a `figma_version_id` field, compare against the current Figma file version via MCP.

- Different version IDs flag the screen as STALE (more precise than timestamp comparison).
- This supplements timestamp-based staleness detection and takes precedence when both are available.
- When Figma MCP is not available, version ID comparison is skipped (reported as N/A).

### 2.9 Exit Codes
- If any CRITICAL issues are found (missing local references), the audit reports "CRITICAL issues found -- resolve before release."
- If only WARNINGs exist, the audit reports "Warnings found -- review recommended."
- If no issues are found, the audit reports "All design artifacts clean."

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Inventory Scan Discovers All Visual Specs

    Given three feature files exist with Visual Specification sections
    And one feature file exists without a Visual Specification section
    When PM mode runs purlin:design-audit
    Then the audit scans all four feature files
    And the report includes entries for the three features with visual specs
    And the feature without a visual spec is not listed

#### Scenario: Missing Local Reference Detected

    Given a feature has a Visual Specification screen referencing "features/_design/my_feature/mockup.png"
    And the file does not exist on disk
    When PM mode runs purlin:design-audit
    Then the screen is reported with Reference Status MISSING
    And the overall audit reports CRITICAL issues

#### Scenario: Stale Description Detected

    Given a feature has a Visual Specification screen with Processed date 2025-01-15
    And the referenced local artifact was modified on 2025-02-01
    When PM mode runs purlin:design-audit
    Then the screen is reported as STALE
    And the audit offers to re-ingest the artifact

#### Scenario: Unprocessed Artifact Detected

    Given a feature has a Visual Specification screen with a Reference to a local file
    And the screen has no Token Map
    When the PM runs purlin:design-audit
    Then the screen is reported as UNPROCESSED
    And a HIGH-priority item is generated

#### Scenario: Anchor Consistency Hardcoded Color Warning

    Given a design anchor defines "--purlin-accent: #38BDF8"
    And a feature's Token Map maps "accent" to the literal text "#38BDF8"
    When the PM runs purlin:design-audit
    Then the Token Map entry is flagged with an anchor consistency WARNING
    And the suggestion says to use "var(--purlin-accent)" instead

#### Scenario: Brief Staleness Detected

    Given a feature has a Figma reference with Processed date 2026-01-15
    And brief.json exists with figma_last_modified 2026-02-20
    When purlin:design-audit runs
    Then the screen is flagged as STALE
    And the Brief Status column shows STALE
    And remediation suggests purlin:spec to update the Visual Specification

#### Scenario: Missing Brief Warning

    Given a feature has a Figma reference
    And no brief.json exists at features/_design/<feature_stem>/brief.json
    When purlin:design-audit runs
    Then the Brief Status column shows MISSING
    And a WARNING is reported: "No brief.json found"

#### Scenario: Figma Modification Detected as Stale via MCP

    Given a screen references a Figma URL with Processed date 2026-01-15
    And Figma MCP reports the design was last modified 2026-02-20
    When purlin:design-audit runs
    Then the screen is flagged as STALE
    And remediation suggests purlin:spec to update the Visual Specification

#### Scenario: Design-Spec Conflict Detected via MCP

    Given a screen's Token Map maps "primary" to "var(--accent)"
    And Figma MCP shows the design variable "primary" has been renamed to "brand-primary"
    When purlin:design-audit runs
    Then a DESIGN_CONFLICT warning is flagged
    And the warning identifies the specific token name mismatch

#### Scenario: Figma Dev Status Drift Detected

    Given a feature spec has "> Figma Status: Design"
    And Figma MCP shows the frame is now "Ready for Dev"
    When purlin:design-audit runs
    Then the Dev Status column shows DRIFT
    And an INFO item suggests updating the spec

#### Scenario: Version ID Staleness Detected

    Given brief.json has figma_version_id "v123"
    And Figma MCP reports current version "v456"
    When purlin:design-audit runs
    Then the screen is flagged as STALE via version comparison

#### Scenario: Clean Audit Report

    Given all features with Visual Specifications have valid references, current descriptions, and no literal values
    When PM mode runs purlin:design-audit
    Then the audit reports "All design artifacts clean"
    And no CRITICAL or WARNING items are listed

#### Scenario: Invariant pointer sync detects stale git-sourced invariant

    Given a design invariant i_design_visual_standards.md has Source-SHA "abc123"
    And git ls-remote reports the source repo HEAD is "def456"
    When purlin:design-audit runs
    Then the Invariant column shows STALE_INVARIANT
    And remediation suggests purlin:invariant sync i_design_visual_standards.md

#### Scenario: Invariant-governed compliance flags hardcoded color as HIGH

    Given a design invariant defines color token "--brand-primary: #2196F3"
    And feature code contains a hardcoded hex value "#2196F3" instead of the token reference
    When purlin:design-audit runs invariant-governed compliance checks
    Then the violation is flagged as INVARIANT_VIOLATION
    And the severity is HIGH (strict tier: colors)

#### Scenario: Design invariants summary table shown after per-feature table

    Given the project has 2 design invariants (1 git-sourced, 1 Figma-sourced)
    When purlin:design-audit completes the report
    Then a Design Invariants summary table follows the per-feature table
    And each row shows the invariant source, version, sync status, and dependent feature count

### Manual Scenarios (Human Verification Required)

None.
