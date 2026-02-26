# Feature: CDD Spec Map View

> Label: "Tool: CDD Spec Map"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md


## 1. Overview
The Spec Map view within the CDD Dashboard renders an interactive dependency graph of all feature files. It provides visual exploration of the project's feature relationships, category groupings, and prerequisite chains. This feature absorbs all visualization and generation requirements from the retired `software_map_generator.md`.

The Spec Map view is activated via the view mode toggle in the dashboard shell (defined in `cdd_status_monitor.md` Section 2.2.1). The dashboard shell owns the unified header, search box, theme system, and feature detail modal; this feature owns the graph rendering, generation, and reactive update logic.

## 2. Requirements

### 2.1 Graph Generation
*   **Tree Generation:** Recursively parses `> Prerequisite:` links in all feature files in `features/`.
*   **Cycle Detection:** Must identify and flag circular dependencies.
*   **Mermaid Export:** Generates Mermaid diagrams for documentation and reference. Mermaid files are written to `.purlin/cache/feature_graph.mmd`.

### 2.2 Reactive Generation
*   **File Watch Mode:** When the CDD Dashboard server is running, the tool MUST watch `features/` for file changes (create, modify, delete).
*   **Auto-Regenerate:** When a change is detected, the tool MUST automatically re-run the graph generation, updating both the Mermaid exports and `dependency_graph.json`.
*   **Manual Trigger:** Running the graph generation via CLI (`tools/cdd/status.sh --graph`) MUST always regenerate all outputs regardless of whether changes were detected.
*   **Poll Interval:** File watch uses `os.scandir` mtime polling at 2-second intervals. No external dependencies required (no `watchdog`).

### 2.3 Interactive Graph View
*   **Scope:** The graph view is for human consumption only. Agents must use `dependency_graph.json` via `tools/cdd/status.sh --graph`.
*   **Graph Display:** The dependency graph MUST be rendered as an interactive diagram with feature nodes and directed edges representing prerequisite links. Uses Cytoscape.js for rendering.
*   **Category Grouping:** Feature nodes MUST be visually grouped by their `Category` metadata (as defined in each feature file's `> Category:` line). Each group MUST be clearly delineated (e.g., via labeled bounding boxes or distinct spatial clusters) so that the category structure is immediately apparent.
*   **Node Labels:** Each feature node MUST display both its friendly name (the `Label` from the feature file metadata) and its filename. Both pieces of information must be visible without requiring hover or click interaction.
*   **Label Typography:** The friendly name (Label) MUST be rendered in larger, bolder text than the filename. This establishes a clear visual hierarchy where the human-readable name is the primary identifier and the filename is secondary.
*   **Label Non-Overlap:** Node labels (both friendly name and filename) MUST NOT visually overlap with labels of neighboring nodes or with each other. The layout engine must provide sufficient spacing, padding, or collision avoidance to ensure all text remains fully legible at the default zoom-to-fit level.
*   **Label Wrapping:** Long labels MUST wrap within their containing node box rather than being clipped. The full text of both the friendly name and filename MUST remain visible at the default zoom-to-fit level.
*   **No Legend:** The graph MUST NOT display a legend overlay. Node semantics are conveyed through category grouping and direct labeling.
*   **Zoom-to-Fit on Load:** On initial page load (or when switching to the Spec Map view), the graph MUST be automatically zoomed and centered to fit the viewable page area. The graph tracks whether the user has manually modified zoom or pan:
    *   If the user has NOT modified zoom or pan since the last fit (initial load, view switch, or Recenter), auto-refresh cycles MUST re-fit the graph to the viewable area.
    *   If the user HAS modified zoom or pan, auto-refresh cycles MUST preserve the current zoom level and pan position.
*   **Recenter Graph Button:** A "Recenter Graph" button MUST be displayed in the bottom-right corner of the Spec Map canvas. When clicked, it MUST (1) reset zoom and pan to fit the graph to the viewable area, (2) reset all manually-moved node positions to the packed layout positions, and (3) reset the interaction state to "unmodified" for both zoom/pan and node positions, so that subsequent auto-refresh cycles re-fit and re-layout rather than preserve.
*   **Node Position Persistence:** The graph tracks whether the user has manually dragged any node (category group box or individual feature node). Node positions are persisted to `localStorage`, keyed by a content hash derived from the current set of nodes and their category assignments.
    *   If the user has NOT manually moved any node, auto-refresh cycles re-run the layout algorithm normally.
    *   If the user HAS manually moved one or more nodes, auto-refresh cycles restore the saved positions. Existing nodes retain their saved coordinates; any newly-added nodes are placed by the layout algorithm.
    *   **Substantive Change Invalidation:** Saved positions are discarded when any node is added, removed, or reassigned to a different category since the positions were last persisted. The graph runs a fresh full layout, and the position interaction state resets to "unmodified."
*   **Inactivity Timeout:** After a continuous period of 5 minutes with no user interaction on the graph (no drag, pan, zoom, or node interaction), both node positions and zoom/pan are reset to packed layout and auto-fit state. Both interaction states reset to "unmodified."
*   **Hover Highlighting:** When the User hovers over a feature node, the node's immediate neighbors (direct prerequisites and direct dependents, one edge away) MUST be visually highlighted. Non-adjacent nodes should be de-emphasized.
*   **Dynamic Category Label Sizing:** Category group labels MUST scale inversely with the current zoom level so they remain readable at all zoom levels.
    *   Effective font size in model coordinates = `baseFontSize / currentZoom`, clamped to `[12px, 80px]`.
    *   At zoom ~0.15 (typical fit-all for the full graph), labels render at approximately 12 screen pixels (readable).
    *   At zoom 1.0 or higher, labels remain at 12px in model coordinates (same as current behavior).
    *   The category parent node's top padding MUST scale proportionally to accommodate larger labels at low zoom, preventing label overlap with child nodes.
    *   Label size updates MUST be triggered on zoom events (rAF-debounced), after `cy.fit()`, and after layout runs.
*   **Two-Level Category Packing Layout:** The graph layout MUST use a two-level approach instead of a single-pass dagre layout across all nodes.
    *   **Level 1 -- Intra-category layout:** Each category's nodes are laid out independently using dagre (top-to-bottom direction), considering only intra-category edges. This preserves clean hierarchical prerequisite flow within each category.
    *   **Level 2 -- Inter-category packing:** Category bounding boxes are placed using a nearest-neighbor heuristic weighted by inter-category edge count. Categories with more cross-category edges are placed adjacent to each other. The algorithm:
        1.  Compute inter-category edge weights (number of edges between each pair of categories).
        2.  Place the most-connected category first, then greedily place each subsequent category near its weighted centroid of already-placed neighbors.
        3.  Use spiral search for non-overlapping positions.
    *   **No new CDN dependencies.** The layout uses the dagre library (already loaded) for Level 1 and a custom placement algorithm for Level 2.

### 2.4 Cytoscape.js Theme Integration
*   **JS Theme Color Map:** Cytoscape styles are JS objects, not CSS. The implementation MUST maintain a JavaScript theme color map that switches based on the current theme.
*   **Style Update on Toggle:** On theme toggle, call `cy.style().update()` or regenerate the Cytoscape instance with updated colors.
*   **SVG Node Labels:** The `createNodeLabelSVG()` function uses hardcoded `fill` values for text. It MUST accept theme colors as parameters and regenerate all node labels on theme switch.

### 2.5 Machine-Readable Output
*   **Canonical File:** The generator MUST produce a `dependency_graph.json` file at `.purlin/cache/dependency_graph.json`.
*   **Schema:**
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
*   **Agent Contract:** This file is the ONLY interface agents should use to query the dependency graph. Agents MUST NOT scrape the web UI or parse Mermaid files. CLI access is via `tools/cdd/status.sh --graph`.
*   **API Endpoint:** The dependency graph is served via the `/dependency_graph.json` endpoint defined in `cdd_status_monitor.md` Section 2.4.

## 3. Scenarios

### Automated Scenarios
These scenarios are validated by the Builder's automated test suite.

#### Scenario: Update Feature Graph
    Given a new feature file is added with prerequisites
    When the graph generation is run
    Then dependency_graph.json is regenerated with the new feature
    And the Mermaid export files are regenerated

#### Scenario: Agent Reads Dependency Graph
    Given dependency_graph.json exists at .purlin/cache/dependency_graph.json
    When an agent needs to query the dependency graph
    Then the agent reads dependency_graph.json directly
    And the agent does NOT use the web UI or parse Mermaid files

#### Scenario: Dependency Graph Excludes Companion Files
    Given a features directory with critic_tool.md and critic_tool.impl.md
    When the graph generation is run
    Then only critic_tool.md appears as a node
    And critic_tool.impl.md is not included

### Manual Scenarios (Human Verification Required)
These scenarios MUST NOT be validated through automated tests. The Builder must instruct the User to start the CDD Dashboard server (`tools/cdd/start.sh`) and verify the web UI visually.

#### Scenario: Reactive Update on Feature Change
    Given the CDD Dashboard server is running
    And the Spec Map view is active
    When a feature file is created, modified, or deleted
    Then the tool automatically regenerates the Mermaid exports
    And the tool automatically regenerates dependency_graph.json

#### Scenario: Feature Detail Modal via Graph Node
    Given the User is viewing the Spec Map view
    When the User clicks a feature node
    Then the shared feature detail modal opens showing the rendered markdown content
    And the modal has an X button in the top-right corner
    When the User clicks the X button or clicks outside the modal or presses Escape
    Then the modal closes

#### Scenario: Hover Highlighting
    Given the User is viewing the Spec Map view
    When the User hovers over a feature node
    Then the node's direct prerequisites and direct dependents are highlighted
    And non-adjacent nodes are visually de-emphasized

#### Scenario: Zoom Preserved on Refresh When Modified
    Given the User has zoomed or panned the graph in the Spec Map view
    When the dashboard auto-refreshes
    Then the current zoom level and pan position are preserved

#### Scenario: Zoom Resets on Refresh When Unmodified
    Given the User has not modified zoom or pan since the last fit
    When the dashboard auto-refreshes
    Then the graph is re-fitted to the viewable area

#### Scenario: Recenter Graph Button Resets View and Interaction State
    Given the User has zoomed or panned the graph
    When the User clicks the Recenter Graph button
    Then the zoom and pan are reset to fit the graph in the viewable area
    And the interaction state is reset to unmodified
    When the dashboard next auto-refreshes
    Then the graph is re-fitted to the viewable area rather than preserving the previous zoom/pan

#### Scenario: Node Position Preserved on Refresh When Manually Moved
    Given the User has dragged one or more nodes to new positions in the Spec Map view
    When the dashboard auto-refreshes and the graph has not changed substantively
    Then each moved node is restored to its saved position

#### Scenario: Node Positions Discarded When Graph Changes Substantively
    Given the User has manually moved one or more nodes
    When a feature file is added, removed, or a node's category assignment changes
    Then the saved node positions are discarded
    And the graph re-runs the full packed layout algorithm
    And the position interaction state resets to unmodified

#### Scenario: Recenter Graph Button Resets Node Positions
    Given the User has manually moved one or more nodes
    When the User clicks the Recenter Graph button
    Then all node positions are reset to the packed layout positions
    And the position interaction state resets to unmodified
    And subsequent auto-refresh cycles re-layout rather than restore saved positions

#### Scenario: Inactivity Timeout Redraws Graph and Resets Zoom
    Given the User has manually moved nodes or modified zoom and pan
    When 5 minutes pass with no user interaction on the graph
    Then all node positions are reset to the packed layout positions
    And zoom and pan are reset to fit the graph in the viewable area
    And both position and zoom interaction states reset to unmodified

#### Scenario: Category Labels Readable at Overview Zoom
    Given the User is viewing the Spec Map view with the graph zoomed to fit all nodes
    When the zoom level is approximately 0.15 (typical fit-all)
    Then category group labels render at approximately 12 screen pixels (readable)
    And when the User zooms in to 1.0 or higher
    Then category labels do not grow beyond 12px in model coordinates

#### Scenario: Categories Packed Into Viewport
    Given the User is viewing the Spec Map view
    When the graph layout runs
    Then category groups fill the viewport area efficiently rather than stacking vertically
    And categories with the most cross-category edges are placed adjacent to each other
    And no category bounding boxes overlap

#### Scenario: Prerequisite Hierarchy Preserved Within Categories
    Given the User is viewing the Spec Map view
    When the graph layout runs
    Then within each category group nodes flow top-to-bottom following prerequisite order
    And anchor nodes appear above the features that depend on them

## Visual Specification

### Screen: CDD Dashboard -- Spec Map View
- **Reference:** N/A
- [ ] Dependency graph rendered with feature nodes and directed edges
- [ ] Feature nodes visually grouped by Category metadata with clear delineation
- [ ] Each node displays both Label (friendly name) and filename
- [ ] Label rendered in larger, bolder text than the filename
- [ ] No node labels overlap with neighboring labels
- [ ] Long labels wrap within node boxes without clipping (all text visible at default zoom)
- [ ] No legend overlay displayed
- [ ] Graph is zoomed and centered to fit the viewable page area on initial load
- [ ] "Recenter Graph" button is displayed in the bottom-right corner of the Spec Map canvas
- [ ] Theme toggle switches all colors including graph nodes, edges, category groups, and modals
- [ ] SVG node labels update text colors on theme switch
- [ ] Theme persists across auto-refresh cycles
- [ ] Search/filter input (in dashboard header) filters graph nodes by label or filename
- [ ] Manually-moved node positions persist across page refresh when the graph has not changed substantively
- [ ] "Recenter Graph" button resets manually-moved node positions to packed layout in addition to resetting zoom
- [ ] Category labels readable at overview zoom (~0.15) without squinting
- [ ] Category labels do not become disproportionately large when zoomed in past 1.0
- [ ] Category groups packed efficiently into viewport (minimal whitespace between groups)
- [ ] High-affinity categories (many cross-category edges) placed close together
- [ ] Intra-category prerequisite hierarchy preserved (anchor nodes above dependents, top-to-bottom flow)

## User Testing Discoveries
