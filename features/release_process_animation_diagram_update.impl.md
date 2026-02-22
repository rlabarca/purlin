# Implementation Notes: Process Animation Diagram Update

## Dependency Installation

*   **`mmdc` (Mermaid CLI):** Install globally via npm: `npm install -g @mermaid-js/mermaid-cli`. Requires Node.js 18+. The script MUST NOT attempt auto-installation — it only checks and errors with the install command.
*   **ImageMagick `convert`:** Auto-installed by the script when absent. On macOS: `brew install imagemagick`. On Debian/Linux: `apt-get install -y imagemagick`. On unsupported platforms: the script exits with a clear error instructing the user to install manually.
*   **Python 3.8+:** Required for the script itself. No installation logic — the script checks and exits if the version is too old.

## Mermaid Diagram Layout

*   Target topology: hub-spoke with `CRITIC` as the center node. This is best achieved with Mermaid's `graph TB` direction, using explicit edge declarations to guide placement. Mermaid does not have a native radial layout, so the hub-spoke is approximated via edge structure: define CRITIC-to-all connections first, then the four leaf nodes (ARCH, BLDR, QA, FEAT) around it.
*   If pure TB layout does not produce a satisfying hub-spoke appearance, alternative fallback: use `graph LR` (left-right) with a two-column structure (ARCH/BLDR on left, QA/FEAT on right, CRITIC in center column).
*   `mmdc` renders to SVG or PNG. Use PNG (`-o frame.png`) for ImageMagick compositing. Set explicit dimensions with `-w 800 -H 460` (width 800, height 460) to match the diagram area.
*   Mermaid's `dark` theme with the Blueprint Dark init block (Section 2.5 of the spec) provides the correct base colors. Node highlight classes are injected per-frame via Mermaid `classDef` and `class` statements appended to the base diagram string before each `mmdc` invocation.

## Animation Sequence is Source of Truth

The 16-frame sequence defined in spec Section 2.7 is the **source of truth**. The Builder MUST encode this sequence as a Python data structure (list of dicts) in the script, derived directly from the spec table. If the spec changes, the script data structure MUST be updated to match. Never reverse-engineer the spec from the script.

## Per-Frame Generation Strategy

1. **Build frame `.mmd` file:** Concatenate the base diagram Mermaid string with per-frame `classDef` and `class` annotations, and per-frame edge overrides (solid sky-blue arrows for active connections, using `linkStyle` directives). Write to a temp `.mmd` file.
2. **Render PNG via mmdc:** `mmdc -i frame_N.mmd -o frame_N.png -w 800 -H 460 -b transparent`. The `-b transparent` flag keeps the diagram background from overriding the Blueprint Dark fill.
3. **Composite caption via ImageMagick:** Create an 800×40px caption strip (`convert -size 800x40 xc:#162531 ...`) and composite it below the 800×460px diagram PNG to produce an 800×500px frame PNG.
4. **Assemble GIF:** Use `convert -delay <delay> frame_*.png -loop 0 assets/workflow-animation.gif`. The `-delay` value must be set per-frame using ImageMagick's per-image `-delay` syntax. `duration_ms` in the spec is divided by 10 to get centiseconds (ImageMagick's delay unit).

## Intermediate File Cleanup

*   Use `tempfile.mkdtemp()` to create a temporary directory for all intermediate files (`.mmd` sources, per-frame PNGs, caption strips).
*   Wrap the entire generation pipeline in a `try/finally` block. The `finally` clause calls `shutil.rmtree(tmpdir, ignore_errors=True)` to guarantee cleanup even on failure.

## Inter Font Fallback for ImageMagick

*   ImageMagick's `-font` flag requires the font to be registered in ImageMagick's font database. Inter is not always available.
*   Detection strategy: run `convert -list font | grep -i inter` and check exit code / output. If Inter is found, use `-font Inter`. If not, fall back to `-font sans-serif` (or the best available system sans-serif font).
*   Alternatively, use `-font` with a direct path to the Inter `.ttf` file if the project bundles it under `assets/fonts/`. This is the most reliable cross-platform approach.

## Mermaid CSS Class Injection Pattern

To highlight nodes per-frame, append the following to the base `.mmd` string before rendering:

```
classDef active fill:#38BDF8,stroke:#38BDF8,color:#0B131A
classDef warning fill:#F97316,stroke:#F97316,color:#0B131A
classDef success fill:#34D399,stroke:#34D399,color:#0B131A
class ARCH active
class FEAT warning
```

Only include `classDef` declarations for classes actually used in the current frame to keep the diagram string minimal.

## Edge Override Pattern

Mermaid does not allow per-edge color overrides inline in the same declaration; use `linkStyle` directives with edge index numbers. Since the base diagram defines all edges as dotted (`-.->`) with known indices, the script must know which index corresponds to each logical connection and override only the active ones per frame using:

```
linkStyle 2 stroke:#38BDF8,stroke-width:2px
```

Edge indices are 0-based and correspond to the order of edge declarations in the base diagram. Document the index-to-connection mapping in the script as a constant dict for maintainability.

## Test File Location

Tests live in `tests/release_process_animation_diagram_update/test_workflow_animation.py` (the Critic's primary scan location). The test file imports from `dev/generate_workflow_animation.py` via path manipulation. The script itself lives in `dev/` per the Purlin-dev convention.

## Hub-Spoke Layout Fix (BUG resolved 2026-02-22, revised 2026-02-22)

Original fix (subgraph with all 3 agents + `direction LR`) put all agents on the same horizontal row — not triangular. QA re-reported as still flat. Second fix: moved ARCH out of the subgraph and added structural-only edges `ARCH -.-> BLDR` and `ARCH -.-> QA` to force ARCH onto a higher Dagre tier. Layout is now a diamond: ARCH (top apex) → BLDR/QA (middle flanking) → CRITIC (center-below hub) → FEAT (bottom). The extra structural edges (indices 0-1 in EDGE_INDEX) are never highlighted in any animation frame. EDGE_INDEX values shifted +2 to account for the new edges.

## Frame Duration Fix (DISCOVERY SPEC_UPDATED 2026-02-22)

Original durations (2000ms/3000ms) were too fast to read. Spec updated to double all values: frames 1-15 now 4000ms, frame 16 now 6000ms. Simple value change in the FRAMES data structure.

## Caption Panel Fix (BUG resolved 2026-02-22)

The original compositing used `-append -background '#0B131A' -flatten` which didn't reliably handle the diagram PNG dimensions. Two issues: (1) mmdc may output at retina scale (2x DPI), producing larger PNGs than expected; (2) `-flatten` behavior with `-append` is IM-version-dependent. Fixed by: (a) adding `--scale 1` to mmdc to prevent DPI scaling; (b) adding an explicit ImageMagick resize step (`-resize 800x460!`) after mmdc rendering to guarantee exact diagram dimensions; (c) using `-alpha remove -alpha off` instead of `-flatten` for robust transparency handling; (d) adding a post-composite resize+alpha-remove step to guarantee the final 800x500 frame dimensions.

## Pruned Discoveries

- **Hub-spoke layout (BUG, resolved 2026-02-22):** Mermaid's Dagre engine flattened nodes horizontally; fixed by using an invisible subgraph to arrange agents in top tier with Critic/CDD and features/ below. See "Hub-Spoke Layout Fix" above.
- **Caption panel missing (BUG, resolved 2026-02-22):** mmdc retina scaling and ImageMagick `-flatten` behavior caused caption compositing to fail; fixed by pinning `--scale 1`, explicit resize, and `-alpha remove`. See "Caption Panel Fix" above.

## Traceability Overrides

- traceability_override: "Generator produces GIF on success" -> test_generator_produces_gif_on_success
- traceability_override: "README embedding is idempotent" -> test_readme_embedding_is_idempotent
