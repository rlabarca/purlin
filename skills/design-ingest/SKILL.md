---
name: design-ingest
description: This skill activates PM mode. If another mode is active, confirm switch first
---

**Purlin mode: PM**

Purlin agent: This skill activates PM mode. If another mode is active, confirm switch first.

---

## Path Resolution

> **Output standards:** See `${CLAUDE_PLUGIN_ROOT}/references/output_standards.md`.

## Retirement Notice

`purlin:design-ingest` is retired. Its responsibilities have been split across other commands:

| Old responsibility | New home |
|-------------------|----------|
| Figma connection & setup | `purlin:invariant add-figma` |
| Annotation extraction | `purlin:invariant add-figma` + `purlin:invariant sync` (stored as advisory in pointer file) |
| brief.json generation | `purlin:spec` (during Visual Spec authoring for features referencing a Figma invariant) |
| Token Map generation | `purlin:spec` (PM maps tokens when writing the Visual Specification) |
| Visual acceptance checklists | `purlin:spec` (PM authors checklists from brief.json data) |
| Design Anchor declaration | Standard `> Prerequisite:` to `i_design_*.md` invariant |
| Local file ingestion (images, PDFs) | PM adds files to `features/_design/` and references them in local `design_*.md` anchors via `purlin:anchor` |
| Web URL references | PM adds references to local `design_*.md` anchors via `purlin:anchor` |
| Staleness detection | `purlin:invariant sync` (version check) + scan (brief vs pointer version) |
| Dev Resources linking | Dropped (low-value ceremony) |

---

## Redirect Logic

When this skill is invoked, detect the user's intent and redirect:

1. **Figma URL argument:** Redirect to `purlin:invariant add-figma <url>`.
   ```
   purlin:design-ingest is retired. Figma designs are now managed as invariants.
   Use: purlin:invariant add-figma <figma-url>
   ```

2. **Local file argument (image, PDF):** Guide the user to add the file manually.
   ```
   purlin:design-ingest is retired. For local design assets:
   1. Copy the file to features/_design/<feature_stem>/
   2. Reference it in a local design_*.md anchor via purlin:anchor design_<name>
   3. Add the Visual Specification in the feature spec via purlin:spec
   ```

3. **"reprocess" keyword:** Redirect to `purlin:invariant sync` for Figma-sourced designs, or `purlin:spec` for local artifact re-processing.
   ```
   purlin:design-ingest reprocess is retired.
   - Figma designs: purlin:invariant sync <invariant-file>
   - Local artifacts: purlin:spec <feature> (update the Visual Specification)
   ```

4. **No argument:** Print the retirement notice and redirect table above.

---

## Three-Tier Design Model

For reference, the current design model:

| Tier | Source | Local File | Invariant? | How to Set Up |
|------|--------|-----------|-----------|---------------|
| Git markdown | External git repo | `i_design_*.md` (full content) | Yes | `purlin:invariant add <repo-url>` |
| Figma | Figma document | `i_design_*.md` (thin pointer) | Yes | `purlin:invariant add-figma <url>` |
| Local | Project team | `design_*.md` (full content) | No | `purlin:anchor design_<name>` + manual asset placement |
