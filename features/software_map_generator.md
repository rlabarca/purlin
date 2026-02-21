# Feature: Software Map Generator

> Label: "Tool: Software Map"
> Category: "DevOps Tools"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/design_visual_standards.md

## 1. Overview
Generates a visual and machine-readable representation of the project's feature dependency graph. Provides both a web UI for human review and a canonical JSON output for agent consumption.

## 2. Requirements

### 2.1 Core Graph Generation
*   **Tree Generation:** Recursively parses `> Prerequisite:` links in all feature files in `features/`.
*   **Cycle Detection:** Must identify and flag circular dependencies.
*   **Mermaid Export:** Generates Mermaid diagrams for documentation and the interactive web view.

### 2.2 Machine-Readable Output (Agent Interface)
*   **Canonical File:** The generator MUST produce a `dependency_graph.json` file at `.agentic_devops/cache/dependency_graph.json`.
*   **Schema:** The JSON file MUST contain the following structure:
    ```json
    {
      "generated_at": "<ISO 8601 timestamp>",
      "features": [
        {
          "file": "<relative path to feature file>",
          "label": "<Label from metadata>",
          "category": "<Category from metadata>",
          "prerequisites": ["<relative path>", "..."]
        }
      ],
      "cycles": ["<description of any detected cycles>"],
      "orphans": ["<files with no prerequisite links>"]
    }
    ```
*   **Deterministic Output:** Given the same set of feature files, the JSON output MUST be identical (sorted keys, sorted arrays by file path).
*   **Agent Contract:** This file is the ONLY interface agents should use to query the dependency graph. Agents MUST NOT scrape the web UI or parse Mermaid files.

### 2.3 Reactive Generation
*   **File Watch Mode:** When the web server is running (`start.sh`), the tool MUST watch `features/` for file changes (create, modify, delete).
*   **Auto-Regenerate:** When a change is detected, the tool MUST automatically re-run the graph generation, updating both the Mermaid exports and `dependency_graph.json`.
*   **Manual Trigger:** Running `generate_tree.py` directly MUST always regenerate all outputs regardless of whether changes were detected.

### 2.4 Interactive View
*   **Scope:** The web view is for human consumption only. Agents must use `dependency_graph.json`.
*   **Graph Display:** The dependency graph MUST be rendered as an interactive diagram with feature nodes and directed edges representing prerequisite links.
*   **Category Grouping:** Feature nodes MUST be visually grouped by their `Category` metadata (as defined in each feature file's `> Category:` line). Each group MUST be clearly delineated (e.g., via labeled bounding boxes or distinct spatial clusters) so that the category structure is immediately apparent.
*   **Node Labels:** Each feature node MUST display both its friendly name (the `Label` from the feature file metadata) and its filename. Both pieces of information must be visible without requiring hover or click interaction.
*   **Label Typography:** The friendly name (Label) MUST be rendered in larger, bolder text than the filename. This establishes a clear visual hierarchy where the human-readable name is the primary identifier and the filename is secondary.
*   **Label Non-Overlap:** Node labels (both friendly name and filename) MUST NOT visually overlap with labels of neighboring nodes or with each other. The layout engine must provide sufficient spacing, padding, or collision avoidance to ensure all text remains fully legible at the default zoom-to-fit level.
*   **Label Wrapping:** Long labels MUST wrap within their containing node box rather than being clipped. The full text of both the friendly name and filename MUST remain visible at the default zoom-to-fit level.
*   **Theme-Responsive Color Scheme:** The software map MUST use a theme-responsive color scheme with dark (Blueprint) as default (dark background with light text and edges). All UI elements (graph background, category groups, nodes, modals, search input, controls) MUST be styled consistently with a dark theme.
*   **No Legend:** The graph MUST NOT display a legend overlay. Node semantics are conveyed through category grouping and direct labeling.
*   **Zoom-to-Fit on Load:** On initial page load, the graph MUST be automatically zoomed and centered to fit the viewable page area. On auto-refresh cycles, the current zoom level and pan position MUST be preserved.
*   **Search/Filter:** A text input MUST be provided that filters visible graph nodes by label or filename. Nodes that do not match the filter should be visually de-emphasized or hidden. Placeholder text MUST use `var(--purlin-dim)` to ensure readable contrast in both themes.
*   **Feature Detail Modal:** Clicking a feature node MUST open a scrollable modal window that renders the feature file's markdown content. The modal MUST have a close button (X) in the top-right corner. Clicking outside the modal MUST also close it.
*   **Hover Highlighting:** When the User hovers over a feature node, the node's immediate neighbors (direct prerequisites and direct dependents, one edge away) MUST be visually highlighted. Non-adjacent nodes should be de-emphasized.

### 2.5 Branding & Theme
*   **Logo:** The Purlin logo (`assets/purlin-logo.svg`) MUST be displayed inline in the top-left of the page header, adjacent to the title text. The logo uses CSS classes for theme-responsive fill colors (~24px height).
*   **Title:** The page title MUST read "Purlin Software Map" (replacing any previous title).
*   **Project Name:** The active project name MUST be displayed on a second line below the title, per `design_visual_standards.md` Section 2.6. The project name's left edge MUST align with the left edge of the "P" in the title above. Font: `var(--font-body)` Inter Medium 500, 14px, color `var(--purlin-primary)`. Omitted if `project_name` is absent from config.
*   **Theme Toggle:** A sun/moon icon toggle MUST appear in the top-right header area. Clicking the toggle switches between Blueprint (dark, default) and Architect (light) themes.
*   **CSS Tokens:** All CSS colors MUST use `var(--purlin-*)` custom properties. No hardcoded hex colors in CSS.
*   **Cytoscape.js Theme Integration:** Cytoscape styles are JS objects, not CSS. The implementation MUST maintain a JavaScript theme color map that switches based on the current theme. On theme toggle, call `cy.style().update()` or regenerate the Cytoscape instance with updated colors.
*   **SVG Node Labels:** The `createNodeLabelSVG()` function uses hardcoded `fill` values for text. It MUST accept theme colors as parameters and regenerate all node labels on theme switch.
*   **Default Theme:** Dark (Blueprint).
*   **Persistence:** `localStorage` key `purlin-theme`, value `light` or `dark`.
*   **FOUC Prevention:** A synchronous `<script>` in `<head>` reads `localStorage` and sets `data-theme` on `<html>` before first paint.
*   **Typography:** Per `design_visual_standards.md` Section 2.3. Tool title uses `var(--font-display)` (Montserrat ExtraLight 200, wide tracking `0.12em`, `uppercase`). Section headers use `var(--font-body)` (Inter Bold 700, `uppercase`, wide tracking `0.1em`). Body/UI text uses `var(--font-body)` (Inter 400-500). Code/data retains monospace. CDN loads: Montserrat weights 200,800,900; Inter weights 400,500,700.

## 3. Scenarios

### Automated Scenarios
These scenarios are validated by the Builder's automated test suite.

#### Scenario: Update Feature Graph
    Given a new feature file is added with prerequisites
    When the software map generator is run
    Then dependency_graph.json is regenerated with the new feature
    And the Mermaid export files are regenerated

#### Scenario: Agent Reads Dependency Graph
    Given dependency_graph.json exists at .agentic_devops/cache/dependency_graph.json
    When an agent needs to query the dependency graph
    Then the agent reads dependency_graph.json directly
    And the agent does NOT use the web UI or parse Mermaid files

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder MUST NOT start the server. The Builder must instruct the User to start the server (`tools/software_map/start.sh`) and verify the web UI visually.

#### Scenario: Reactive Update on Feature Change
    Given the software map server is running
    When a feature file is created, modified, or deleted
    Then the tool automatically regenerates the Mermaid exports
    And the tool automatically regenerates dependency_graph.json

#### Scenario: Feature Detail Modal
    Given the User is viewing the web UI
    When the User clicks a feature node
    Then a scrollable modal opens showing the rendered markdown content
    And the modal has an X button in the top-right corner
    When the User clicks the X button or clicks outside the modal
    Then the modal closes

#### Scenario: Hover Highlighting
    Given the User is viewing the web UI
    When the User hovers over a feature node
    Then the node's direct prerequisites and direct dependents are highlighted
    And non-adjacent nodes are visually de-emphasized

#### Scenario: Server Start/Stop Lifecycle
    Given the Software Map server is not running
    When the User runs tools/software_map/start.sh
    Then the server starts on the configured port on the first invocation
    And a PID file is written to .agentic_devops/runtime/software_map.pid
    When the User runs tools/software_map/stop.sh
    Then the server process is terminated
    And the PID file is removed
    When the User runs tools/software_map/start.sh again
    Then the server starts successfully on the first invocation without requiring a second run

#### Scenario: Zoom Persistence on Refresh
    Given the User has zoomed or panned the graph
    When the dashboard auto-refreshes
    Then the current zoom level and pan position are preserved

## 4. Implementation Notes
See [software_map_generator.impl.md](software_map_generator.impl.md) for implementation knowledge, builder decisions, and tribal knowledge.

## Visual Specification

### Screen: Software Map Viewer
- **Reference:** N/A
- [ ] Purlin logo visible in top-left corner beside "Purlin Software Map" title
- [ ] Active project name displayed on a second line below the title, left-aligned with the "P" in PURLIN
- [ ] Project name uses Inter Medium 500, body text size (14px), color matches the logo triangle (`--purlin-primary`)
- [ ] Project name color switches correctly between dark and light themes
- [ ] Project name shows config value when `project_name` is set; falls back to project directory name otherwise
- [ ] Sun/moon theme toggle in top-right
- [ ] Theme toggle switches all colors including graph nodes, edges, category groups, and modals
- [ ] SVG node labels update text colors on theme switch
- [ ] Theme persists across auto-refresh cycles
- [ ] Dependency graph rendered with feature nodes and directed edges
- [ ] Feature nodes visually grouped by Category metadata with clear delineation
- [ ] Each node displays both Label (friendly name) and filename
- [ ] Label rendered in larger, bolder text than the filename
- [ ] No node labels overlap with neighboring labels
- [ ] Long labels wrap within node boxes without clipping (all text visible at default zoom)
- [ ] No legend overlay displayed
- [ ] Graph is zoomed and centered to fit the viewable page area on initial load
- [ ] Search/filter text input visible for filtering nodes
- [ ] Search input placeholder text uses `--purlin-dim` color token for readable contrast in both themes

## User Testing Discoveries

### [DISCOVERY] Search bar placeholder text has insufficient contrast in both themes (Discovered: 2026-02-21)
- **Scenario:** Interactive Web View (visual specification)
- **Observed Behavior:** The "Filter nodes..." placeholder text in the search input is nearly invisible against the input background in both dark (Blueprint) and light (Architect) themes. The placeholder color does not provide enough contrast for readability.
- **Expected Behavior:** Placeholder text should be clearly readable in both themes, even if styled as secondary/hint text.
- **Action Required:** Architect (re-specify placeholder text color or input styling in design_visual_standards.md to ensure sufficient contrast)
- **Resolution:** Added `--purlin-dim` token to `design_visual_standards.md` (Blueprint: `#8B9DB0`, Architect: `#94A3B8`). Updated search/filter requirement and visual spec to reference the token for placeholder text. Builder implemented: added `--purlin-dim` to both theme blocks in index.html CSS, updated `#search::placeholder` to use `var(--purlin-dim)`.
- **Status:** RESOLVED

