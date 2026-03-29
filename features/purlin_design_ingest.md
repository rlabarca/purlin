# Feature: Design Ingest Command (Retired)

> Label: "Agent Skills: PM: purlin:design-ingest Design Ingest"
> Category: "Agent Skills: PM"

[Complete]

## 1. Overview

`purlin:design-ingest` is **retired**. Its responsibilities have been split across purpose-built commands following the introduction of the invariant system and the three-tier design model.

This spec documents the retirement redirect behavior. The command remains as a skill file that detects user intent and routes to the correct replacement command.

### 1.1 Responsibility Split

| Old responsibility | New home |
|-------------------|----------|
| Figma connection & setup | `purlin:invariant add-figma` |
| Annotation extraction | `purlin:invariant add-figma` + `purlin:invariant sync` (stored as advisory in pointer file) |
| brief.json generation | `purlin:spec` (during Visual Spec authoring for features referencing a Figma invariant) |
| Token Map generation | `purlin:spec` (PM maps tokens when writing the Visual Specification) |
| Visual acceptance checklists | `purlin:spec` (PM authors checklists from brief.json data) |
| Design Anchor declaration | Standard `> Prerequisite:` to `i_design_*.md` invariant |
| Local file ingestion (images, PDFs) | PM adds files to `features/design/` manually, references via `purlin:anchor` |
| Web URL references | PM adds references to local `design_*.md` anchors via `purlin:anchor` |
| Staleness detection | `purlin:invariant sync` (version check) + scan (brief vs pointer version) |
| Dev Resources linking | Dropped (low-value ceremony) |

### 1.2 Three-Tier Design Model

| Tier | Source | Local File | Invariant? | How to Set Up |
|------|--------|-----------|-----------|---------------|
| Git markdown | External git repo | `i_design_*.md` (full content) | Yes | `purlin:invariant add <repo-url>` |
| Figma | Figma document | `i_design_*.md` (thin pointer) | Yes | `purlin:invariant add-figma <url>` |
| Local | Project team | `design_*.md` (full content) | No | `purlin:anchor design_<name>` + manual asset placement |

---

## 2. Requirements

### 2.1 Role Guard
- The command activates PM mode. If another mode is active, confirm switch first.

### 2.2 Redirect Logic
When invoked, the command detects the user's intent from the argument and redirects:

1. **Figma URL argument:** Redirect to `purlin:invariant add-figma <url>`.
2. **Local file argument (image, PDF):** Guide the user to copy the file to `features/design/<feature_stem>/`, reference it in a `design_*.md` anchor via `purlin:anchor`, and add the Visual Specification via `purlin:spec`.
3. **"reprocess" keyword:** Redirect to `purlin:invariant sync` for Figma-sourced designs, or `purlin:spec` for local artifact re-processing.
4. **No argument:** Print the retirement notice and responsibility split table.

---

## 3. Scenarios

### QA Scenarios

#### Scenario: Figma URL redirects to purlin:invariant add-figma

    Given the PM invokes purlin:design-ingest with a Figma URL
    Then the command prints a retirement notice
    And redirects to purlin:invariant add-figma with the URL

#### Scenario: Local file argument shows manual workflow guidance

    Given the PM invokes purlin:design-ingest with a local image path
    Then the command prints a retirement notice
    And shows the three-step manual workflow (copy, anchor, spec)

#### Scenario: Reprocess keyword redirects appropriately

    Given the PM invokes purlin:design-ingest with "reprocess"
    Then the command prints a retirement notice
    And suggests purlin:invariant sync for Figma-sourced designs
    And suggests purlin:spec for local artifact re-processing

#### Scenario: No argument shows full retirement table

    Given the PM invokes purlin:design-ingest with no arguments
    Then the command prints the retirement notice
    And shows the responsibility split table
    And shows the three-tier design model reference
