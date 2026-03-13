# Design: Design Artifact Pipeline

> Label: "Design: Design Artifact Pipeline"
> Category: "Common Design Standards"

## Purpose

Defines invariants for how external design artifacts (images, PDFs, Figma URLs, live web page URLs) are stored, referenced, processed, and inherited within the Purlin specification system. This anchor node establishes a design-system-agnostic pipeline that any consumer project can adopt regardless of their technology stack or design token format. The pipeline ensures that visual specifications are backed by structured, auditable descriptions derived from concrete design artifacts rather than memory or ad-hoc prose.

## Design Artifact Invariants

### Storage Convention

*   **Per-feature artifacts:** Stored at `features/design/<feature_stem>/` where `<feature_stem>` is the feature filename without the `.md` extension (e.g., `features/design/cdd_status_monitor/dashboard-layout.png`).
*   **Shared artifacts:** Cross-feature design standards (brand guides, global style references, design system exports) are stored at `features/design/_shared/`.
*   **No new top-level directories:** All design artifacts live within the existing `features/` directory tree. Projects MUST NOT create separate top-level directories for design assets.
*   **Naming convention:** `features/design/<feature_stem>/<descriptive-name>.<ext>` -- use lowercase, hyphen-separated descriptive names. The name should describe the content (e.g., `dashboard-layout.png`, `settings-panel-dark.pdf`), not a version or date.

### Reference Format

Each `### Screen:` subsection in a `## Visual Specification` section MUST include:

*   `- **Reference:**` -- The path to a local artifact file, a Figma URL (`[Figma](<url>)`), a live web page URL (`[Live](<url>)`), or `N/A` when no reference exists.
*   `- **Processed:**` -- The date (YYYY-MM-DD) when the referenced artifact was last ingested and the Token Map was generated, or `N/A` if not yet processed.
*   `- **Token Map:**` -- An explicit mapping from Figma design token names to the project's design token system. Each entry is formatted as `` `<figma-token>` -> `<project-token>` ``. This is the PM's primary value-add: bridging Figma's naming world and the project's token world.

### Token Map Format

The Token Map replaces prose descriptions. It provides a structured, auditable bridge between the design tool and the codebase:

```markdown
- **Token Map:**
  - `surface` -> `var(--project-bg)`
  - `on-surface` -> `var(--project-text)`
  - `primary` -> `var(--project-accent)`
  - `spacing-md` -> `var(--project-spacing-md)`
```

*   Each entry maps a Figma design variable name (left) to the project's corresponding token (right).
*   The project token format is defined by the `design_*.md` anchor (CSS custom properties, SCSS variables, Tailwind classes, SwiftUI color assets, etc.).
*   When no design anchor exists, the right side uses literal values (e.g., `` `primary` -> `#2196F3` ``).

### Design Brief Cache

During ingestion, the PM extracts a compact design brief from Figma and stores it locally at `features/design/<feature_stem>/brief.json`. This provides the Builder with structured, machine-readable design data without requiring Figma MCP access during implementation.

**Schema:**
```json
{
  "figma_url": "https://figma.com/design/...",
  "figma_last_modified": "2026-03-13T09:00:00Z",
  "screens": {
    "<Screen Name>": {
      "node_id": "<figma-node-id>",
      "dimensions": {"width": 375, "height": 812},
      "components": [
        {"name": "ComponentName", "width": 120, "height": 160, "gap": 16}
      ],
      "layout": "<layout-type>",
      "auto_layout": {"direction": "horizontal", "gap": 16, "padding": 24}
    }
  },
  "tokens": {
    "<figma-token-name>": "<resolved-value>"
  }
}
```

*   `brief.json` is generated once by the PM during ingestion (when the PM is already reading Figma via MCP).
*   `figma_last_modified` is embedded for staleness detection.
*   The Builder reads `brief.json` as the primary design data source, falling back to Figma MCP only when the brief is missing, ambiguous, or incomplete.
*   QA reads Figma MCP directly during verification for the freshest data. `brief.json` is a QA fallback if MCP is unavailable.

### Processing Mandate

*   Every referenced artifact MUST have a corresponding `- **Token Map:**` in the Visual Specification section. The binary file (or URL) is the audit reference; the Token Map and checklists are the working documents that agents use.
*   Unprocessed artifacts (reference exists but no Token Map) are flagged as HIGH-priority PM action items by the Critic.
*   The Builder reads Figma MCP directly for layout and structure details. The Token Map provides the token bridge; visual acceptance checklists provide measurable criteria. Prose descriptions are NOT used.

### Design Anchor Declaration

Each `## Visual Specification` section MUST include a `> **Design Anchor:**` blockquote line declaring which `design_*.md` anchor governs visual properties for that feature. This establishes the inheritance relationship.

Format:
```
> **Design Anchor:** features/<project_design_anchor>.md
> **Inheritance:** Colors, typography, and theme switching per anchor.
```

### Inheritance Rule

*   Feature Visual Specifications **inherit** visual properties (colors, fonts, spacing scale, theme behavior) from the project's `design_*.md` anchor(s) declared in the `> **Design Anchor:**` line.
*   Feature artifacts provide **layout and structure** -- component arrangement, screen-specific elements, information hierarchy.
*   When processing a rough wireframe or sketch, the PM MUST map observed design tokens to the project's design token system as defined in the anchor via the Token Map. For example, a Figma token named `surface` is mapped to the project's `var(--bg)` token -- not a literal hex color.
*   **Conflict resolution:** The anchor always wins for visual properties. To deviate from anchor standards, update the anchor first (which triggers cascading resets to all dependent features).

### Supported Input Types

| Input Type | Reference Format | Processing Method |
|------------|-----------------|-------------------|
| Local image (PNG, JPG, SVG) | `` `features/design/<stem>/<file>` `` | Read via Claude's multimodal Read tool |
| Local PDF | `` `features/design/<stem>/<file>.pdf` `` | Read via Claude's PDF Read tool |
| Figma public URL | `[Figma](<url>)` | Record URL; prompt for exported image or screenshot to process |
| Figma export (image/PDF) | `` `features/design/<stem>/<exported-file>` `` | Stored locally, processed as image/PDF |
| Figma design tokens | `` `features/design/<stem>/<name>.tokens.css` `` or `.tokens.json` | Stored alongside visual exports for reference |
| Live web page URL | `[Live](<url>)` | Fetch via WebFetch to extract current visual state |
| Figma frame (MCP) | `[Figma](<url>)` | Read via Figma MCP; extract metadata, tokens, layout; auto-generate description |

### Design-System Agnosticism

*   This pipeline does NOT prescribe any specific design token format. The project's `design_*.md` anchor defines the token system: CSS custom properties, SCSS variables, Tailwind classes, SwiftUI color assets, Android XML resources, or any other convention.
*   The processing step maps observed visuals to whatever token system the anchor declares. References to tokens in descriptions use the anchor's own naming (e.g., `var(--accent)`, `text-primary`, `Color.accentColor`).
*   The `/pl-design-ingest` command dynamically reads whatever `design_*.md` anchors exist in the consumer project at runtime -- it does not depend on any specific anchor.

### Staleness Detection

*   For local artifacts, the Critic compares the file's modification time (`mtime`) against the `- **Processed:**` date.
*   If the artifact file is newer than the processed date, the Token Map is flagged as STALE.
*   Stale Token Maps produce LOW-priority PM action items prompting re-processing via `/pl-design-ingest` with the re-process flag.
*   For `brief.json`, the Critic compares `figma_last_modified` against the spec's `- **Processed:**` date. If the brief is newer than the spec, the spec is flagged as STALE.

### Figma Integration Tiers

*   **Tier 1 (Manual):** Public Figma URLs are recorded in `- **Reference:**` lines. The PM manually creates the Token Map by viewing the URL and mapping observed design tokens to the project's token system. No `brief.json` is generated.
*   **Tier 2 (Export):** Designers export Figma frames as PNG/SVG/PDF. Exports are stored locally per the storage convention. If CSS or design tokens are exported from Figma dev mode, they are stored alongside as `<name>.tokens.css` or `<name>.tokens.json`. The PM creates the Token Map from these exports.
*   **Tier 3 (MCP -- Live API):** When Figma MCP is available, the PM reads design data directly via MCP protocol. The `[Figma](<url>)` reference format is preserved for audit trail. MCP enables: extracting component metadata, layout properties, design variables/tokens, auto-layout constraints, and annotations. At Tier 3, the PM also generates `brief.json` from the MCP data. Tier 3 supplements Tiers 1/2 -- projects without Figma MCP fall back gracefully to Tier 1 or Tier 2 processing.

### Figma MCP Role Access

*   **PM:** Full MCP access (read and write). Reads Figma for ingestion; writes to Figma during design iteration with human approval.
*   **Builder:** Read-only MCP access. Reads Figma for layout/structure details when `brief.json` is insufficient. Primary design data source is `brief.json` + Token Map (local, no network).
*   **QA:** Read-only MCP access. Reads Figma directly during verification for triangulated comparison (Figma vs Spec vs App). Fresh MCP data is preferred over `brief.json` for verification accuracy.
*   **Architect:** No Figma MCP access. Does not evaluate visual design decisions.

### Figma MCP Auto-Setup

*   When an agent encounters a Figma URL and Figma MCP tools are not available in the current session, the agent checks for Figma-related tools in the tool list.
*   If not available, the agent provides setup instructions: `claude mcp add --transport http figma https://mcp.figma.com/mcp`
*   OAuth requires human browser interaction -- the agent informs the user and provides instructions for the one-time authorization flow.
*   After setup, a session restart is required for MCP tools to become available.

### Figma Staleness Detection (MCP)

*   When Figma MCP is available and a screen references a Figma URL, the agent reads the design's `lastModified` timestamp via MCP.
*   The timestamp is compared against the `- **Processed:**` date in the Visual Specification.
*   If the Figma design was modified after the processed date, the screen is flagged as STALE.
*   This enables automated staleness detection for Figma-sourced designs (not possible for URLs alone without MCP).

### Figma as Design Authority

*   When a Visual Specification is derived from a Figma reference via MCP, the Figma design is the authority for visual properties.
*   The Token Map and checklists in the Visual Specification are the working documents for agents; Figma is the source of truth for audits, disputes, and triangulated verification.
*   Non-visual specs (calculations, performance, data behaviors) live in Requirements and Scenarios -- they are NOT governed by Figma.
*   Visual specs live in the Visual Specification section, derived from Figma.
*   Requirements/Scenarios govern behavior; Visual Specification governs appearance.
*   Conflicts between the Token Map and Figma design variables are flagged by `/pl-design-audit` as `DESIGN_CONFLICT` warnings.

### Triangulated Verification

QA verification uses three independent sources to detect discrepancies:

| Source | What QA reads | How |
|--------|--------------|-----|
| **Figma** | Component tree, dimensions, colors, fonts, spacing, auto-layout | Figma MCP (`get_file`, `get_node`) using the Reference URL |
| **Spec** | Token Map + checklist items | Read from `features/<name>.md` |
| **App** | Computed styles, DOM structure, rendered pixels | Playwright MCP (`browser_evaluate`, `browser_screenshot`) or user-provided screenshot |

**Verdict matrix (per checklist item):**

| Figma | Spec | App | Verdict | Action |
|-------|------|-----|---------|--------|
| Match | Match | Match | PASS | All three agree |
| Changed | Stale | Match old | STALE | Figma updated but spec not re-ingested. PM action item. |
| Match | Match | Differs | BUG | Code doesn't match spec. Builder action item. |
| Changed | Changed | Differs | BUG | Spec is current but code is wrong. Builder action item. |
| Changed | Stale | Match Figma | SPEC_DRIFT | Code matches Figma but not spec. PM action item. |

**Token verification:** For each Token Map entry, QA compares the Figma design variable value, the spec's project token mapping, and the app's computed CSS property value. Drift between any pair is flagged.

**Non-web-testable features:** Triangulated verification still works using manual screenshots. QA reads Figma via MCP, the user provides a screenshot, and QA vision-compares the screenshot against Figma + spec checklists. Exact computed style values are replaced by vision-based approximation.

### Figma Write Policy

*   Only the PM agent MAY use Figma MCP write capabilities (generate designs, modify components, push layouts).
*   Builder and QA MUST treat Figma as read-only via MCP.
*   Architect does not access Figma MCP.
*   The PM writes to Figma during design iteration with the human; the human sees all MCP tool calls and can reject them.
*   The Builder MUST NOT write to Figma -- design changes flow through SPEC_DISPUTE to the PM or Architect.

### Live Web Page Processing

*   Live web page URLs are recorded as `[Live](<url>)` in reference lines.
*   Processing extracts the current visual state of an existing web page -- useful for reverse-engineering a live UI into a visual spec, or establishing a baseline before redesign.
*   The processing step additionally extracts observable CSS patterns, component structure, and computed styles to compare against the anchor's token system.

## Scenarios

No automated or manual scenarios. This is a policy anchor node -- its "scenarios" are
process invariants enforced by instruction files and tooling.
