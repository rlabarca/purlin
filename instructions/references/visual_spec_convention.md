# Visual Specification Convention

> This file is loaded on-demand by `/pl-spec`, `/pl-design-ingest`, `/pl-design-audit`,
> and `/pl-verify` commands when working with features that have visual specifications.

## 9.1 Purpose
Feature files MAY contain a `## Visual Specification` section for features with visual/UI components. This section provides checklist-based visual acceptance criteria with optional design asset references, distinct from functional Gherkin scenarios.

## 9.2 Section Format
The section is placed before `## User Testing Discoveries` (or at the end of the file if no discoveries section exists):

```markdown
## Visual Specification

> **Design Anchor:** features/<project_design_anchor>.md
> **Inheritance:** Colors, typography, and theme switching per anchor.

### Screen: <Screen Name>
- **Reference:** `features/design/<stem>/<file>` | [Figma](<url>) | [Live](<url>) | N/A
- **Processed:** YYYY-MM-DD | N/A
- **Description:** <Structured prose description of the visual design, mapped to the anchor's token system>
- [ ] <Visual acceptance criterion 1>
- [ ] <Visual acceptance criterion 2>
```

**Reference types:** local file path (to a stored design artifact), Figma URL, live web page URL (`[Live](<url>)`), or `N/A` when no reference exists.

**Key properties:**
*   **Optional** -- only present when the feature has a visual/UI component.
*   **Per-screen subsections** -- one feature can have multiple screens, each as a `### Screen:` subsection.
*   **Design anchor declaration** -- the `> **Design Anchor:**` blockquote establishes which `design_*.md` anchor governs visual properties (colors, fonts, theme behavior) for this feature.
*   **Design asset references** -- local artifact paths, Figma URLs, live web page URLs, or "N/A" when no reference exists.
*   **Processed date** -- records when the artifact was last converted to a structured markdown description. Used by the Critic for staleness detection.
*   **Structured description** -- the working document that agents use. Derived from the referenced artifact and mapped to the project's design token system.
*   **Checklist format** -- not Gherkin. Subjective visual checks are better as checkboxes than Given/When/Then.
*   **Separate from functional scenarios** -- QA can batch all visual checks across features instead of interleaving with functional verification.

## 9.3 Ownership and Traceability
*   The `## Visual Specification` section is **Architect-owned** (like the rest of the spec). QA does NOT modify it.
*   Visual specification items are **exempt from Gherkin traceability**. They do not require automated scenarios or test functions.
*   The Critic detects visual spec sections and generates separate QA action items for visual verification.

## 9.4 Design Asset Storage
*   Design assets referenced by visual specs may be stored as project-local files (e.g., `docs/mockups/`) or as external URLs (e.g., Figma links).
*   Local file paths are relative to the project root.
*   There is no mandatory storage location -- projects choose what fits their workflow.

## 9.5 Verification Methods
Visual checklist items are verified by the QA Agent during the visual verification pass (QA_BASE Section 5.4). The QA Agent MAY use screenshot-assisted verification: the user provides screenshots and the agent auto-checks items verifiable from a static image (layout, positioning, typography, color). Items requiring interaction, temporal observation, or implementation inspection are confirmed manually by the human tester.

## 9.6 Visual vs Functional Classification
When a feature has UI components, the Architect MUST classify each acceptance criterion:

*   **Visual Specification** (checklist item): Verifiable from a static screenshot -- layout, colors, typography, element presence/absence, spacing. No interaction required.
*   **Manual Scenario** (Gherkin): Requires user interaction (clicks, hovers, typing), temporal observation (waiting for refresh/animation), or multi-step functional verification (start server, trigger action, observe result).

The goal is to **minimize Manual Scenarios** by moving all static visual checks to the Visual Specification section. Manual Scenarios should only test behavior that cannot be verified from a screenshot.

## 9.7 Design Artifact Pipeline
Design artifacts (images, PDFs, Figma exports, live web page captures) are stored within the `features/` directory tree using a structured convention:

*   **Per-feature storage:** `features/design/<feature_stem>/` where `<feature_stem>` is the feature filename without `.md`.
*   **Shared storage:** `features/design/_shared/` for cross-feature design standards (brand guides, global style references).
*   **Naming:** `features/design/<feature_stem>/<descriptive-name>.<ext>` -- lowercase, hyphen-separated.

**Processing mandate:** Every referenced artifact MUST have a corresponding `- **Description:**` in the Visual Specification section. The binary file (or URL) is the audit reference; the markdown description is the working document agents use. The `/pl-design-ingest` command automates this processing workflow.

**Supported input types:** Local images (PNG, JPG, SVG), local PDFs, Figma public URLs, Figma exports (stored locally), Figma design token exports (`.tokens.css`, `.tokens.json`), and live web page URLs (`[Live](<url>)`).

## 9.8 Design Inheritance
Visual Specifications operate under an inheritance model:

*   **Anchor provides:** Colors, fonts, spacing scale, theme behavior -- all visual properties defined in the project's `design_*.md` anchor(s).
*   **Feature provides:** Layout, structure, component arrangement, screen-specific elements -- extracted from the design artifact.
*   **Processing rule:** When converting an artifact to a description, the Architect maps observed visuals to the project's design token system. A blue rectangle in a wireframe becomes "a button styled per the project's accent color token" -- not a literal blue color.

**Design-system agnosticism:** The pipeline does not prescribe any specific design token format. The project's `design_*.md` anchor defines the token system (CSS custom properties, SCSS variables, Tailwind classes, SwiftUI color assets, Android XML resources, etc.). The `/pl-design-ingest` command dynamically reads whatever `design_*.md` anchors exist at runtime.

**Conflict resolution:** The anchor always wins for visual properties. To deviate from anchor standards, update the anchor first (which triggers cascading resets to all dependent features via the dependency graph).
