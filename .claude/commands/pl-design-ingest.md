**Purlin mode: PM**

Purlin agent: This skill activates PM mode. If another mode is active, confirm switch first.

---

## Retirement Notice

`/pl-design-ingest` is retired. Its responsibilities have been split across other commands:

| Old responsibility | New home |
|-------------------|----------|
| Figma connection & setup | `/pl-invariant add-figma` |
| Annotation extraction | `/pl-invariant add-figma` + `/pl-invariant sync` (stored as advisory in pointer file) |
| brief.json generation | `/pl-spec` (during Visual Spec authoring for features referencing a Figma invariant) |
| Token Map generation | `/pl-spec` (PM maps tokens when writing the Visual Specification) |
| Visual acceptance checklists | `/pl-spec` (PM authors checklists from brief.json data) |
| Design Anchor declaration | Standard `> Prerequisite:` to `i_design_*.md` invariant |
| Local file ingestion (images, PDFs) | PM adds files to `features/design/` and references them in local `design_*.md` anchors via `/pl-anchor` |
| Web URL references | PM adds references to local `design_*.md` anchors via `/pl-anchor` |
| Staleness detection | `/pl-invariant sync` (version check) + scan (brief vs pointer version) |
| Dev Resources linking | Dropped (low-value ceremony) |

---

## Redirect Logic

When this skill is invoked, detect the user's intent and redirect:

1. **Figma URL argument:** Redirect to `/pl-invariant add-figma <url>`.
   ```
   /pl-design-ingest is retired. Figma designs are now managed as invariants.
   Use: /pl-invariant add-figma <figma-url>
   ```

2. **Local file argument (image, PDF):** Guide the user to add the file manually.
   ```
   /pl-design-ingest is retired. For local design assets:
   1. Copy the file to features/design/<feature_stem>/
   2. Reference it in a local design_*.md anchor via /pl-anchor design_<name>
   3. Add the Visual Specification in the feature spec via /pl-spec
   ```

3. **"reprocess" keyword:** Redirect to `/pl-invariant sync` for Figma-sourced designs, or `/pl-spec` for local artifact re-processing.
   ```
   /pl-design-ingest reprocess is retired.
   - Figma designs: /pl-invariant sync <invariant-file>
   - Local artifacts: /pl-spec <feature> (update the Visual Specification)
   ```

4. **No argument:** Print the retirement notice and redirect table above.

---

## Three-Tier Design Model

For reference, the current design model:

| Tier | Source | Local File | Invariant? | How to Set Up |
|------|--------|-----------|-----------|---------------|
| Git markdown | External git repo | `i_design_*.md` (full content) | Yes | `/pl-invariant add <repo-url>` |
| Figma | Figma document | `i_design_*.md` (thin pointer) | Yes | `/pl-invariant add-figma <url>` |
| Local | Project team | `design_*.md` (full content) | No | `/pl-anchor design_<name>` + manual asset placement |
