# Implementation Notes: CDD Software Map View

*   **Graph module location:** `tools/cdd/graph.py` — contains all graph generation logic ported from `tools/software_map/generate_tree.py`. Importable by `serve.py`.
*   **Companion file exclusion:** `parse_features()` in `graph.py` skips `*.impl.md` files. The filter checks `filename.endswith(".impl.md")` before the general `.endswith(".md")` check. This ensures only primary feature specs appear as graph nodes.
*   **Status messages to stderr:** All `print()` calls in `graph.py` use `file=sys.stderr` so that the `--cli-graph` mode can pipe clean JSON to stdout without interleaved status messages.
*   **Endpoints added to CDD serve.py:** `/dependency_graph.json` (serves cached JSON, 404 if missing), `/feature?file=<path>` (raw feature content, path traversal protection), `/impl-notes?file=<path>` (companion .impl.md content, 404 if none), `/config.json` (project config).
*   **File watcher:** Poll-based watcher using `os.scandir` mtime snapshots at 2-second intervals. Runs in a daemon thread. On change detection, calls `graph.run_full_generation()`. On generation failure, retains old snapshot so the next poll cycle retries.
*   **CLI modes:** `serve.py --cli-graph` regenerates and outputs dependency_graph.json to stdout. `status.sh --graph` is the shell wrapper.
*   **Server startup sequence:** (1) Run initial graph generation, (2) start file watcher thread, (3) start HTTP server. Initial generation failure is non-fatal (warning to stderr).
*   **Path traversal protection:** Both `/feature` and `/impl-notes` endpoints resolve paths via `os.path.normpath` and verify the result starts with the features directory. Returns 403 on violation.
*   **Dependency graph cache path:** `DEPENDENCY_GRAPH_PATH` constant in `serve.py` points to `.purlin/cache/dependency_graph.json`, consistent with `graph.py`'s output location.
*   **Test output:** Tests write to `tests/cdd_software_map/tests.json` with `{"status": "PASS", ...}` format.
*   **Theme-Responsive Graph (2026-02-21):** `createNodeLabelSVG()` now accepts a `colors` parameter for SVG `fill` values instead of hardcoded `#E8E8E8`/`#888`. `buildCytoscapeElements()` passes `colors` through. `createCytoscape()` accepts `colors` and uses `c.surface`, `c.border`, `c.dim` for category parent bg, border, edge colors. `renderGraph()` calls `getThemeColors()` and passes colors through the chain. On `toggleTheme()`, `renderGraph()` is called to rebuild the entire Cytoscape instance with updated theme colors (preserving zoom/pan).
