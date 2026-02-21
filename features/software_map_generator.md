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
*   **Search/Filter:** A text input MUST be provided that filters visible graph nodes by label or filename. Nodes that do not match the filter should be visually de-emphasized or hidden.
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

#### Scenario: Interactive Web View
    Given the software map server is running
    When the User opens the web UI in a browser
    Then the dependency graph is rendered with nodes and edges
    And feature nodes are visually grouped by their Category metadata
    And each node displays its Label and its filename
    And the Label is rendered in larger, bolder text than the filename
    And no node labels overlap with neighboring node labels
    And long labels wrap within their node boxes without clipping
    And the overall UI defaults to a dark color scheme with a theme toggle available
    And no legend overlay is displayed
    And the graph is zoomed to fit the viewable page area
    And a search input is visible for filtering nodes

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
*   **Test Scope:** Automated tests MUST only cover graph generation, cycle detection, and `dependency_graph.json` output. The web UI MUST NOT be tested through automated tests. The Builder MUST NOT start the server. After passing automated tests, the Builder should use the `[Ready for Verification]` status tag and instruct the User to start the server (`tools/software_map/start.sh`) and visually verify the web view.
*   **Acyclic Mandate:** The tool is the primary enforcer of the acyclic graph rule defined in the workflow.
*   **Agent Interface:** `.agentic_devops/cache/dependency_graph.json` is the single machine-readable contract. All agent tooling (Context Clear Protocol, Dependency Integrity checks, Release Protocol) MUST read this file. The generator writes to this cache location per submodule_bootstrap Section 2.12.
*   **Cycle Detection:** Uses DFS with 3-color marking (WHITE/GRAY/BLACK). External prerequisites (not in the features directory) are skipped without triggering false positives.
*   **File Watch Mode:** `serve.py` polls `features/` directory every 2 seconds using `os.scandir` mtime snapshots. No external dependencies required (no `watchdog`).
*   **Deterministic JSON:** `dependency_graph.json` uses `sort_keys=True` on `json.dump` and all arrays are pre-sorted by filename/path before serialization.
*   **Label Wrapping:** SVG label generator uses word-wrap logic (`wrapText()`) to split long labels into multiple lines within the node box. Each label line is rendered as a `<tspan>` element. Node height is dynamically computed based on the number of wrapped lines (base 44px + 18px per extra line). Max ~22 chars per line at font-size 14 in monospace.
*   **Reactive Update Testing:** The "Reactive Update on Feature Change" scenario requires the running server (`serve.py`) and is classified as Manual. File-watch regeneration is verified during Human Verification.
*   **Reactive Refresh Resilience:** Fixed two issues that could cause stale category data on reactive refresh: (1) In `generate_tree.py`, `generate_dependency_graph()` now runs BEFORE `update_outputs()` (Mermaid/README), so the critical JSON output is written even if README update fails. (2) In `serve.py`, the file watcher snapshot is only updated on successful generation — failed generations trigger retry on the next poll cycle. Builder audit (2026-02-20): full code trace confirms the reactive path is correct — watcher detects mtime changes, subprocess re-parses features (including Category), writes updated JSON, web UI fetches with cache-busting and rebuilds Cytoscape graph with new category groupings. Needs QA re-verification with server running.
*   **Start/Stop PID Path Consistency:** `start.sh` writes PID files to `.agentic_devops/runtime/`. `stop.sh` MUST read from the same runtime directory using the same project root detection logic. A path mismatch between start and stop causes orphaned server processes and port conflicts on subsequent starts.
*   **Label wrapping in node boxes:** DISCOVERY resolved -- long labels now wrap via `wrapText()` SVG logic instead of clipping. Verified 2026-02-20.
*   **Start/Stop double invocation:** DISCOVERY resolved 2026-02-20 — PID path mismatch between start.sh and stop.sh caused orphaned processes. Builder fixed path consistency. Verified: server starts on first invocation after stop.
*   **Category grouping on reactive refresh:** BUG resolved 2026-02-20 — category changes weren't reflected on reactive refresh. Builder fixed generation ordering and watcher resilience. Verified: editing Category metadata updates grouping in web UI within seconds.
*   **Purlin Branding (2026-02-21):** Implemented Section 2.5 — replaced all hardcoded CSS hex colors with `var(--purlin-*)` custom properties. Added `:root` (Blueprint dark) and `[data-theme='light']` (Architect light) theme definitions. FOUC prevention script in `<head>`. Google Fonts CDN (Montserrat headings, Inter body). Inline logo SVG mark in header, title "Purlin Software Map". Sun/moon toggle with CSS-driven icon visibility. JS `getThemeColors()` reads computed CSS custom properties for Cytoscape styles. `createNodeLabelSVG()` accepts `colors` parameter for theme-responsive SVG `fill` values. `createCytoscape()` accepts `colors` for category parent bg, borders, edges, hover highlights. On `toggleTheme()`, `renderGraph()` is called which destroys and recreates the Cytoscape instance with new colors (preserving zoom/pan via existing viewport state logic).
*   **Typography Alignment (2026-02-21):** Aligned with `design_visual_standards.md` Section 2.3. Added `--font-display` and `--font-body` CSS custom properties to both `:root` and `[data-theme='light']` blocks. Updated CDN weights to Montserrat 200,800,900 and Inter 400,500,700. Page title uses `var(--font-display)` at weight 200 (ExtraLight), `letter-spacing:0.12em;text-transform:uppercase` (wide tracking matching SVG logo treatment). Modal header h2 and modal body headings use `var(--font-display)`. Body uses `var(--font-body)`. All hardcoded `'Montserrat'` and `'Inter'` font-family values in CSS replaced with custom property references. Note: SVG node labels still use hardcoded `'Menlo'` monospace — this is correct per spec (monospace for data).
*   **Port TIME_WAIT fix (2026-02-21):** BUG resolved — set `allow_reuse_address = True` on `socketserver.TCPServer` in `serve.py` so the server can rebind to a port in TIME_WAIT state after stop/restart. Added startup verification to `start.sh` — waits 0.5s and checks if the PID is still alive, reporting an error with log path if the process exited (e.g., bind failure). Same pattern as the CDD Monitor fix.

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

## User Testing Discoveries



