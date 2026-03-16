**Purlin command owner: PM, Architect**

If you are not operating as the Purlin PM or Architect, respond: "This is a PM/Architect command. Ask your PM or Architect agent to run /pl-design-audit instead." and stop.

---

Read `instructions/references/visual_spec_convention.md` before auditing.

Audit all design artifacts and visual specifications across the project for integrity, staleness, anchor consistency, and Figma design-spec conflicts.

**Workflow:**

1. **Inventory scan:** Glob for all `features/*.md` files. Read each one and extract `## Visual Specification` sections. For each `### Screen:` subsection, extract:
   - Screen name
   - Reference path/URL (from `- **Reference:**`)
   - Processed date (from `- **Processed:**`)
   - Whether a Token Map exists (from `- **Token Map:**`)
   - Checklist item count
   Also check for `brief.json` at `features/design/<feature_stem>/brief.json` for each feature with a Figma reference.
   If Figma MCP tools are available, also extract annotation count per screen via `get_design_context`. Report as informational metadata (not a pass/fail check).

2. **Reference integrity:** For each screen:
   - Local file references: verify the file exists on disk. Missing = CRITICAL.
   - URL references (Figma, Live): validate URL syntax only. Malformed = WARNING.
   - Token Map without reference: WARNING.
   - Reference without Token Map: HIGH (unprocessed artifact).

3. **Staleness check:** For local artifact files:
   - Read the file's modification time.
   - Compare against the Processed date.
   - If file is newer than processed date: STALE.

3.1. **Brief staleness:** For features with Figma references and a `brief.json`:
   - Compare `figma_last_modified` in the brief against the spec's Processed date.
   - If the brief is newer: STALE (Figma was updated since last ingestion).
   - If `brief.json` is missing and screen has Figma reference: WARNING ("No brief.json found").

4. **Anchor consistency:** Read all `features/design_*.md` anchor nodes. Scan Token Map entries and checklists for:
   - Token Map right-side values that don't match any anchor token.
   - Hardcoded hex colors or literal values in Token Map entries that should reference anchor tokens.
   - Hardcoded values in checklist items that should use token references.
   - Flag each as WARNING with the suggested token name.

5. **Figma staleness (MCP):** For screens referencing Figma URLs:
   - If Figma MCP tools are available: read the design's `lastModified` timestamp via MCP.
   - Compare against the Processed date. If Figma was modified after Processed, flag as STALE.
   - If Figma MCP is not available: report staleness as N/A for Figma screens (no connectivity check).

6. **Design-spec conflict detection (MCP):** For screens referencing Figma URLs when MCP is available:
   - Extract design variable names and values from the Figma design via MCP.
   - Compare against the Token Map entries in the Visual Specification.
   - Flag discrepancies as DESIGN_CONFLICT warnings (e.g., "Token Map maps `primary` to `var(--accent)`, but Figma design variable `primary` has been renamed to `brand-primary`").
   - Also compare Figma design variable resolved values against `brief.json` token values if present.

7. **Report:** Print a summary table. The Annotations column is optional — show it when Figma MCP is available, omit otherwise. Annotation count is informational metadata only (not a pass/fail check).
   ```
   Feature              | Screen           | Ref Status  | Staleness | Brief   | Anchor | Design Conflict | Annotations
   ---------------------|------------------|-------------|-----------|---------|--------|-----------------|------------
   cdd_status_monitor   | Web Dashboard    | OK          | CURRENT   | N/A     | CLEAN  | CLEAN           | N/A
   my_feature           | Settings Panel   | MISSING     | N/A       | N/A     | N/A    | N/A             | N/A
   figma_feature        | Figma Screen     | OK          | STALE     | CURRENT | CLEAN  | 1 warning       | 3
   ```

8. **Offer remediation:** For STALE items, offer to re-ingest via `/pl-design-ingest reprocess <feature> <screen>`.

9. **Summary:** Report overall status:
   - CRITICAL issues found: "CRITICAL issues found -- resolve before release."
   - Warnings only: "Warnings found -- review recommended."
   - Clean: "All design artifacts clean."
