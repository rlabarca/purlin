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
*   `- **Processed:**` -- The date (YYYY-MM-DD) when the referenced artifact was last converted to a structured markdown description, or `N/A` if not yet processed.
*   `- **Description:**` -- A structured prose description of the visual design, derived from the referenced artifact and mapped to the project's design token system.

### Processing Mandate

*   Every referenced artifact MUST have a corresponding `- **Description:**` in the Visual Specification section. The binary file (or URL) is the audit reference; the markdown description is the working document that agents use.
*   Unprocessed artifacts (reference exists but no description) are flagged as HIGH-priority Architect action items by the Critic.
*   Descriptions MUST be structured to cover: layout hierarchy, component inventory, spacing relationships, color observations, typography observations, and structural elements specific to the feature.

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
*   When processing a rough wireframe or sketch, the Architect MUST map observed visuals to the project's design token system as defined in the anchor. For example, a blue rectangle in a wireframe becomes "a button styled per the project's accent color token" -- not a literal blue color.
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
*   If the artifact file is newer than the processed date, the description is flagged as STALE.
*   Stale descriptions produce LOW-priority Architect action items prompting re-processing via `/pl-design-ingest` with the re-process flag.

### Figma Integration Tiers

*   **Tier 1 (Manual):** Public Figma URLs are recorded in `- **Reference:**` lines. The agent manually processes the design into markdown by viewing the URL and describing what they see, mapped to the anchor's token system.
*   **Tier 2 (Export):** Designers export Figma frames as PNG/SVG/PDF. Exports are stored locally per the storage convention. If CSS or design tokens are exported from Figma dev mode, they are stored alongside as `<name>.tokens.css` or `<name>.tokens.json`.
*   **Tier 3 (MCP -- Live API):** When Figma MCP is available, agents read design data directly via MCP protocol. The `[Figma](<url>)` reference format is preserved for audit trail. MCP enables: extracting component metadata, layout properties, design variables/tokens, auto-layout constraints, and annotations. Tier 3 supplements Tiers 1/2 -- projects without Figma MCP fall back gracefully to Tier 1 or Tier 2 processing.

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
*   Written descriptions in the Visual Specification are the working document for agents; Figma is the source of truth for audits and disputes.
*   Non-visual specs (calculations, performance, data behaviors) live in Requirements and Scenarios -- they are NOT governed by Figma.
*   Visual specs live in the Visual Specification section, derived from Figma.
*   Requirements/Scenarios govern behavior; Visual Specification governs appearance.
*   Conflicts between written behavioral specs and Figma visual specs are flagged by `/pl-design-audit` as `DESIGN_CONFLICT` warnings.

### Figma Write Policy

*   Only the PM agent MAY use Figma MCP write capabilities (generate designs, modify components, push layouts).
*   Architect, Builder, and QA MUST treat Figma as read-only via MCP.
*   The PM writes to Figma during design iteration with the human; the human sees all MCP tool calls and can reject them.
*   The Builder MUST NOT write to Figma -- design changes flow through SPEC_DISPUTE to the PM or Architect.

### Live Web Page Processing

*   Live web page URLs are recorded as `[Live](<url>)` in reference lines.
*   Processing extracts the current visual state of an existing web page -- useful for reverse-engineering a live UI into a visual spec, or establishing a baseline before redesign.
*   The processing step additionally extracts observable CSS patterns, component structure, and computed styles to compare against the anchor's token system.

## Scenarios

No automated or manual scenarios. This is a policy anchor node -- its "scenarios" are
process invariants enforced by instruction files and tooling.
