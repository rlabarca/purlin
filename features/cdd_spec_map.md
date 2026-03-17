# Feature: CDD Spec Map View

> Label: "CDD Spec Map"
> Category: "CDD Dashboard"
> Prerequisite: features/cdd_status_monitor.md
> Prerequisite: features/design_visual_standards.md
> Prerequisite: features/cdd_modal_base.md
> AFT Web: http://localhost:9086
> AFT Start: /pl-cdd

[TODO]

## 1. Overview
The Spec Map view within the CDD Dashboard renders an interactive dependency graph of all feature files. It provides visual exploration of the project's feature relationships, category groupings, and prerequisite chains. This feature absorbs all visualization and generation requirements from the retired `software_map_generator.md`.

The Spec Map view is activated via the view mode toggle in the dashboard shell (defined in `cdd_status_monitor.md` Section 2.2.1). The dashboard shell owns the unified header, search box, theme system, and feature detail modal; this feature owns the graph rendering, generation, and reactive update logic. The feature detail modal opened from graph node clicks inherits shared modal infrastructure (width, font size control, close behavior, theme integration) from `cdd_modal_base.md`.

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
*   **Viewport Containment:** The Spec Map canvas MUST fill exactly the available viewport area below the dashboard header -- no more, no less. The canvas MUST NOT cause page-level scrollbars or overflow the viewable area under any circumstances. Specifically:
    *   The `#map-view` container MUST use `overflow: hidden` to prevent any content from escaping its bounds.
    *   The Cytoscape container (`#cy`) MUST be sized to exactly fill `#map-view` without overflowing. Use `position: absolute; inset: 0` (pinned to all four edges of the parent) instead of `width: 100%; height: 100%`, as percentage-based sizing can produce subpixel overflow at non-default browser zoom levels.
    *   The layout chain from `<body>` to `#cy` MUST be a strict flex containment hierarchy: each ancestor uses `flex: 1; overflow: hidden; min-height: 0` so that the Cytoscape container is always exactly the remaining space after the header.
    *   `min-height: 0` MUST be set on all flex children in the chain (`body > .content-area > .view-panel > #map-view`) to prevent flex items from exceeding their container when content is larger than available space.
    *   On browser zoom changes (Cmd+Plus/Minus, pinch-to-zoom), the canvas MUST resize to fit the new viewport dimensions. No manual resize handler is needed if CSS containment is correct -- the browser reflows flex layout automatically. Cytoscape's `cy.resize()` is called on the `window` `resize` event to sync the canvas.
*   **Graph Display:** The dependency graph MUST be rendered as an interactive diagram with feature nodes and directed edges representing prerequisite links. Uses Cytoscape.js for rendering.
*   **Edge Arrows:** Edges MUST render with arrowheads at the target (dependent/child) end. Arrow direction: prerequisite → dependent (arrows point TO the child node).
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
        2.  Compute the topological layer of each category from inter-category edges. Categories that are pure prerequisites (no incoming inter-category edges) are assigned layer 0; categories depending only on layer-0 categories are layer 1; and so on.
        3.  Place the most-connected category first, then greedily place each subsequent category near its weighted centroid of already-placed neighbors.
        4.  The greedy placement MUST respect topological layer ordering: a category at layer N MUST be placed above (lower Y-coordinate) all categories at layer N+1 or higher. The spiral search target position for a category MUST be constrained to Y-values below the bottom edge of all its prerequisite categories.
        5.  Use spiral search for non-overlapping positions within the layer-constrained region.
    *   **No new CDN dependencies.** The layout uses the dagre library (already loaded) for Level 1 and a custom placement algorithm for Level 2.

### 2.4 Node Color Model
All feature nodes share a single, uniform appearance. The ONLY color distinction is anchor node borders.

*   **Uniform Background:** All feature nodes (anchor and non-anchor alike) MUST use the same background color: `--purlin-surface` at low opacity. No per-category background colors, no per-category tinting.
*   **Uniform Border (Regular Nodes):** Non-anchor feature nodes MUST use `--purlin-border` as their border color. All regular nodes look identical.
*   **Anchor Node Border (Only Distinction):** Anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) MUST render with a border color of `--purlin-status-good` (green), a thicker border width (3px vs 2px), and higher border opacity than regular nodes. This is the sole visual distinction between node types.
*   **No Category Color Palette:** The implementation MUST NOT use a per-category color palette for node backgrounds or borders. Category membership is conveyed entirely through spatial grouping (bounding boxes with dashed borders and category labels). Color is not used for category identity.
*   **Label Text Colors:** Node label text (friendly name) uses `--purlin-primary`. Filename text uses `--purlin-dim`. Both are theme-dependent and uniform across all nodes.
*   **Both Themes:** All of the above applies identically in both Blueprint (dark) and Architect (light) themes.

### 2.5 Double-Click Category Zoom
*   **Zoom to Category:** When the User double-clicks on a category bounding box (the group container, not an individual feature node), the graph MUST animate a zoom-to-fit that maximizes the view of that category box within the viewport.
*   **Zoom Target:** The viewport MUST be adjusted so the category box fills as much of the viewable area as possible while remaining fully visible (with reasonable padding).
*   **Interaction State:** A double-click zoom MUST update the interaction state to "modified" so that subsequent auto-refresh cycles preserve the zoom level rather than re-fitting to the full graph.

### 2.6 Double-Click Background Recenter
*   **Trigger:** When the User double-clicks on the graph canvas background (not on a node, edge, or category bounding box), the graph MUST recenter and zoom-to-fit, identical to clicking the "Recenter Graph" button.
*   **Behavior:** Same as the Recenter Graph button (Section 2.3): (1) reset zoom and pan to fit the graph to the viewable area, (2) reset all manually-moved node positions to the packed layout positions, and (3) reset the interaction state to "unmodified" for both zoom/pan and node positions.
*   **No conflict with category zoom:** Double-click on a category bounding box triggers the category zoom (Section 2.5). Double-click on the background triggers the full recenter. The target element determines which behavior fires.

### 2.7 Edge Click Pass-Through
*   **Non-Interactive Edges:** Edges (the lines and arrows connecting nodes) MUST NOT be interactive click targets. Clicks on edges MUST pass through to the layer below (the canvas background or any element underneath).
*   **Hover Behavior Preserved:** Edge highlighting during node hover (Section 2.3) is unaffected. Edges may still change appearance as part of hover highlighting, but they MUST NOT capture click or tap events.

### 2.8 Cytoscape.js Theme Integration
*   **JS Theme Color Map:** Cytoscape styles are JS objects, not CSS. The implementation MUST maintain a JavaScript theme color map that reads CSS custom properties (`--purlin-surface`, `--purlin-border`, `--purlin-primary`, `--purlin-dim`, `--purlin-status-good`) and applies them to all node and edge styles.
*   **Style Update on Toggle:** On theme toggle, call `cy.style().update()` or regenerate the Cytoscape instance with updated colors. All node backgrounds, borders, and label colors MUST update to reflect the new theme.
*   **SVG Node Labels:** The `createNodeLabelSVG()` function MUST accept theme colors as parameters (using `--purlin-primary` for the friendly name, `--purlin-dim` for the filename) and regenerate all node labels on theme switch. No hardcoded color values in SVG generation.

### 2.9 Search Filtering
*   **Match Logic:** When the user types in the dashboard search input (owned by `cdd_status_monitor.md` Section 2.2.1), the Spec Map MUST perform a case-insensitive substring match against both the node's friendly name (Label) and its filename.
*   **Matching Nodes -- No Change:** Matching nodes MUST remain completely unchanged -- same background, border, text color, and opacity as their default state. No highlighting, no color change, no border change. They look exactly as they do with no search active.
*   **Non-Matching Nodes -- Dim:** Non-matching nodes (and their edges) MUST be visibly dimmed (reduced opacity) so that matching nodes stand out by contrast.
*   **Category Container Opacity:** Category parent nodes (bounding boxes) MUST NOT be dimmed if any of their child feature nodes match the search. In Cytoscape.js, parent node opacity cascades to children -- so dimming a category container would visually hide matching children inside it. A category container MUST only be dimmed when ALL of its children are non-matching.
*   **Distinction from Status View:** The Status view hides non-matching rows entirely. The Spec Map MUST dim rather than hide, because removing nodes from a graph would destroy spatial context and layout stability.
*   **Empty Search:** When the search input is empty or cleared, all nodes and edges MUST return to full color and opacity (their default state).

### 2.10 Machine-Readable Output
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

### 2.11 Web-Verify Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/cdd_spec_map/varied-scenarios` | Project with features having 0, 5, and 20+ scenarios for verifying spec map rendering |

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
    And the modal occupies 70% of the viewport width
    And metadata tags are displayed in a dedicated area above the markdown body
    And a font size adjustment control is visible in the modal header
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
    And categories containing prerequisite nodes are placed above categories containing their dependent nodes
    And no category bounding boxes overlap

#### Scenario: Prerequisite Hierarchy Preserved Across Categories
    Given the Spec Map view displays features with cross-category prerequisite links
    When the graph layout runs
    Then features that are prerequisites appear above their dependents even when in different categories
    And no child feature node has a lower Y-position than its parent prerequisite node in another category

#### Scenario: Prerequisite Hierarchy Preserved Within Categories
    Given the User is viewing the Spec Map view
    When the graph layout runs
    Then within each category group nodes flow top-to-bottom following prerequisite order
    And anchor nodes appear above the features that depend on them

#### Scenario: Uniform Node Appearance with Anchor Border Distinction
    Given the User is viewing the Spec Map view
    When the graph renders all feature nodes
    Then all nodes have the same background color (--purlin-surface at low opacity)
    And all regular (non-anchor) nodes have the same border color (--purlin-border)
    And no per-category color palette is applied to backgrounds or borders
    And anchor nodes (arch_*, design_*, policy_*) have a green border (--purlin-status-good) instead
    And the green anchor border is visible in both Blueprint (dark) and Architect (light) themes

#### Scenario: Double-Click Category Zooms to Fit
    Given the User is viewing the Spec Map view
    When the User double-clicks on a category bounding box
    Then the graph animates a zoom that maximizes the view of that category box within the viewport
    And the category box fills as much of the viewable area as possible while remaining fully visible
    And the interaction state is set to modified so auto-refresh preserves the zoom level

#### Scenario: Spec Map Canvas Does Not Overflow Viewport

    Given the User is viewing the Spec Map view
    When the graph is rendered with any number of nodes
    Then the Cytoscape canvas fills exactly the available viewport area below the header
    And no page-level scrollbars appear on the body or html elements
    And changing the browser zoom level causes the canvas to resize to the new viewport dimensions
    And the Cytoscape canvas never extends beyond the visible screen area

#### Scenario: Double-Click Background Recenters Graph

    Given the User is viewing the Spec Map view
    And the User has zoomed or panned the graph away from the default fit
    When the User double-clicks on the canvas background (not on a node or category box)
    Then the graph recenters and zooms to fit all nodes in the viewable area
    And all manually-moved node positions are reset to the packed layout positions
    And the interaction state is reset to unmodified for both zoom/pan and node positions
    And subsequent auto-refresh cycles re-fit and re-layout the graph

#### Scenario: Search Dims Non-Matching Nodes
    Given the User is viewing the Spec Map view
    When the User types a search term in the dashboard search input
    Then nodes whose Label or filename contain the search term (case-insensitive) are completely unchanged from their default appearance
    And nodes that do not match are visibly dimmed (reduced opacity)
    And edges connected only to non-matching nodes are also dimmed
    And matching nodes have no highlighting, no color change, and no border change applied
    When the User clears the search input
    Then all nodes and edges return to full color and opacity

#### Scenario: Clicks on Edges Pass Through
    Given the User is viewing the Spec Map view
    When the User clicks or double-clicks on an edge (line or arrow between nodes)
    Then the event passes through to the element below (canvas background or category bounding box)
    And no edge selection, tooltip, or modal is triggered
    And double-clicking an edge over a category bounding box triggers the category zoom
    And edge hover highlighting during node hover still functions normally

#### Scenario: Font Size Persists Across Node Clicks (auto-web)
    Given the User is viewing the Spec Map view
    And the User clicks a feature node to open the modal
    And the User adjusts the font size slider
    When the User closes the modal
    And the User clicks a different feature node
    Then the font size slider retains the previously set position

#### Scenario: Metadata Extraction from Graph Node (auto-web)
    Given the User is viewing the Spec Map view
    And a feature node has Label, Category, and multiple Prerequisites
    When the User clicks that feature node
    Then each metadata tag is displayed on its own row in the dedicated metadata area
    And tag names are highlighted
    And no metadata blockquotes appear in the rendered markdown body

#### Scenario: Spec Map Modal Width (auto-web)
    Given the User is viewing the Spec Map view
    When the User clicks a feature node
    Then the modal width is 70% of the viewport width

#### Scenario: Spec Map Modal Metadata (auto-web)
    Given the User is viewing the Spec Map view
    When the User clicks a feature node
    Then the metadata area displays tag names in a highlight color distinct from value text

#### Scenario: Spec Map Modal Font Slider (auto-web)
    Given the User is viewing the Spec Map view
    When the User clicks a feature node and opens the modal
    And the User adjusts the font size slider
    Then all text elements in the modal body scale together

### Manual Scenarios (Human Verification Required)

None.

## Visual Specification

### Screen: CDD Dashboard -- Spec Map View
- **Reference:** N/A
- [ ] Spec Map canvas fills exactly the viewport area below the header -- no scrollbars, no overflow
- [ ] Canvas resizes correctly at different browser zoom levels (Cmd+Plus/Minus)
- [ ] Dependency graph rendered with feature nodes and directed edges
- [ ] Feature nodes visually grouped by Category metadata with clear delineation
- [ ] Each node displays both Label (friendly name) and filename
- [ ] Label rendered in larger, bolder text than the filename
- [ ] No node labels overlap with neighboring labels
- [ ] Long labels wrap within node boxes without clipping (all text visible at default zoom)
- [ ] No legend overlay displayed
- [ ] Graph is zoomed and centered to fit the viewable page area on initial load
- [ ] "Recenter Graph" button is displayed in the bottom-right corner of the Spec Map canvas
- [ ] All feature nodes have the same background color (--purlin-surface at low opacity) -- no per-category tinting
- [ ] All regular (non-anchor) feature nodes have the same border color (--purlin-border)
- [ ] Anchor nodes (arch_*, design_*, policy_*) have a distinct green border (--purlin-status-good) in both themes
- [ ] Regular feature nodes do NOT have green borders or any category-specific coloring
- [ ] Theme toggle switches all colors including graph nodes, edges, category groups, and modals
- [ ] SVG node labels update text colors on theme switch (--purlin-primary for name, --purlin-dim for filename)
- [ ] Theme persists across auto-refresh cycles
- [ ] Search input dims non-matching nodes and edges (reduced opacity) while matching nodes remain completely unchanged
- [ ] Matching nodes retain their exact default appearance -- no highlighting, no color change, no border change
- [ ] Clearing the search input restores all nodes and edges to full color and opacity
- [ ] Manually-moved node positions persist across page refresh when the graph has not changed substantively
- [ ] "Recenter Graph" button resets manually-moved node positions to packed layout in addition to resetting zoom
- [ ] Category labels readable at overview zoom (~0.15) without squinting
- [ ] Category labels do not become disproportionately large when zoomed in past 1.0
- [ ] Category groups packed efficiently into viewport (minimal whitespace between groups)
- [ ] High-affinity categories (many cross-category edges) placed close together
- [ ] Intra-category prerequisite hierarchy preserved (anchor nodes above dependents, top-to-bottom flow)
- [ ] Edges render with visible arrowheads pointing to the dependent (child) node
- [ ] Cross-category prerequisite nodes always appear above their dependents (inter-category hierarchy preserved)
- [ ] Double-clicking a category box zooms the view to maximize that category within the viewport
- [ ] Double-clicking the canvas background recenters and zoom-to-fits (same as Recenter Graph button)
- [ ] Clicking on edges (lines/arrows) does not select them or trigger any interaction
- [ ] Modal from graph node click occupies 70% viewport width (inherited from cdd_modal_base.md)
- [ ] Metadata tags displayed with highlighted names in dedicated area above markdown body
- [ ] Font size control works identically to Status view modal
- [ ] Modal renders correctly in both Blueprint and Architect themes with font size control

