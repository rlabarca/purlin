---
name: design-audit
description: Audit design artifacts and visual specifications for integrity and staleness
---

Read `${CLAUDE_PLUGIN_ROOT}/references/visual_spec_convention.md` before auditing.

Audit all design artifacts and visual specifications across the project for integrity, staleness, anchor consistency, and Figma design-spec conflicts.

**Workflow:**

1. **Inventory scan:** Glob for all `features/**/*.md` files (excluding `_`-prefixed system folders, `.impl.md`, and `.discoveries.md`). Read each one and extract `## Visual Specification` sections. For each `### Screen:` subsection, extract:
   - Screen name
   - Reference path/URL (from `- **Reference:**`)
   - Processed date (from `- **Processed:**`)
   - Whether a Token Map exists (from `- **Token Map:**`)
   - Checklist item count
   Also check for `brief.json` at `features/_design/<feature_stem>/brief.json` for each feature with a Figma reference.
   If Figma MCP tools are available, also extract annotation count per screen via `get_design_context` (fileKey + nodeId from reference URL). Report as informational metadata (not a pass/fail check).
   **Invariant inventory:** Also glob `features/_invariants/i_design_*.md` to collect all design invariants. Read each pointer's `> Version:`, `> Source:`, `> Synced-At:`, and `> Scope:` metadata. These are checked in steps 3.2 and 4.1.

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

3.2. **Invariant pointer sync status:** For each `i_design_*.md` invariant pointer found in step 1:
   - **Figma-sourced** (`> Source: figma`): If Figma MCP is available, fetch the current Figma file version ID via `get_metadata` (fileKey from `> Figma-URL:`) and compare against the pointer's `> Version:`. If different: STALE_INVARIANT. If MCP unavailable: report as UNKNOWN.
   - **Git-sourced** (`> Source:` is a URL): Run `git ls-remote <source-url> HEAD` and compare SHA against `> Source-SHA:`. If different: STALE_INVARIANT.
   - For each stale invariant, check how many features depend on it (via `> Prerequisite:` or global scope). Report cascade impact.
   - **Brief vs pointer version:** For features with a `brief.json` referencing a Figma invariant, compare `brief.json`'s `figma_version_id` against the pointer's `> Version:`. If pointer is newer than brief: STALE_BRIEF (brief needs regeneration via `purlin:spec`).

4. **Anchor consistency:** Read all `features/**/design_*.md` local anchor nodes AND `features/_invariants/i_design_*.md` invariant pointers. Scan Token Map entries and checklists for:
   - Token Map right-side values that don't match any anchor or invariant token.
   - Hardcoded hex colors or literal values in Token Map entries that should reference anchor tokens.
   - Hardcoded values in checklist items that should use token references.
   - Flag each as WARNING with the suggested token name.

4.1. **Invariant-governed design compliance:** For features with `> Prerequisite:` links to `i_design_*.md` invariants:
   - Check enforcement weight per the invariant system's design enforcement tiers:
     - **Colors / design tokens:** Strict — hardcoded hex values that should be design tokens flagged as HIGH.
     - **Typography:** Strict — font families, weights, sizes must match brief.json. Flagged as HIGH.
     - **Spacing / layout:** Moderate — warned as MEDIUM, not blocked.
   - If the invariant has `## FORBIDDEN Patterns`, grep feature code for violations. Flag as INVARIANT_VIOLATION (HIGH).
   - Surface the invariant's `## Design Invariants` statements as compliance context.

5. **Figma staleness (MCP):** For screens referencing Figma URLs:
   - If Figma MCP tools are available: read the design's `lastModified` timestamp via `get_metadata` (fileKey from reference URL).
   - Compare against the Processed date. If Figma was modified after Processed, flag as STALE.
   - If Figma MCP is not available: report staleness as N/A for Figma screens (no connectivity check).

6. **Design-spec conflict detection (MCP):** For screens referencing Figma URLs when MCP is available:
   - Extract design variable names, types, and resolved values via `get_variable_defs` (fileKey from reference URL).
   - Compare variable names against the Token Map entries in the Visual Specification:
     - Variable renamed in Figma but not in Token Map: DESIGN_CONFLICT (e.g., "Token Map maps `primary` to `var(--accent)`, but Figma variable `primary` has been renamed to `brand-primary`").
     - Variable added in Figma but missing from Token Map: DESIGN_GAP (new token not yet mapped).
     - Variable removed from Figma but still in Token Map: DESIGN_CONFLICT (stale mapping).
   - Also compare resolved variable values against `brief.json` token values if present. Value drift (same name, different resolved value) is flagged as DESIGN_DRIFT.

6.1. **Figma dev status consistency (MCP):** For features with `> Figma Status:` metadata and a Figma reference when MCP is available:
   - Read the current dev status via `get_metadata` (fileKey from reference URL).
   - Compare against the spec's `> Figma Status:` value.
   - Discrepancies flagged as INFO with suggestion to update the spec.
   - Report in the "Dev Status" column: CURRENT (matches), DRIFT (mismatch), N/A (no metadata/MCP/reference).

6.2. **Version ID drift (MCP):** For screens where `brief.json` contains `figma_version_id`:
   - Read the current Figma file version via `get_metadata` (fileKey from reference URL).
   - Compare against `figma_version_id` in `brief.json`.
   - Different versions flag the screen as STALE (more precise than timestamp).
   - This supplements timestamp-based detection and takes precedence when both are available.

6.3. **Visual drift detection (MCP, optional):** For screens referencing Figma URLs when MCP is available AND the feature has `> Web Test:` metadata:
   - Fetch the Figma frame screenshot via `get_screenshot` (fileKey + nodeId from reference URL).
   - If Playwright MCP is also available, navigate to the web test URL and take a browser screenshot via `browser_take_screenshot`.
   - Compare the two screenshots using vision analysis. Flag significant visual discrepancies as VISUAL_DRIFT with a brief description of what differs (layout shift, color mismatch, missing element, etc.).
   - This step is **informational** — VISUAL_DRIFT is reported as a WARNING, not a blocking issue. It supplements metadata-based staleness detection with actual visual comparison.
   - Skip this step if either Figma MCP or Playwright MCP is unavailable, or if the feature lacks a web test URL.

7. **Report:** Print a summary table. The Annotations column is optional — show it when Figma MCP is available, omit otherwise. Annotation count is informational metadata only (not a pass/fail check).
   ```
   Feature              | Screen           | Ref Status  | Staleness | Brief   | Anchor | Design Conflict | Dev Status | Invariant       | Annotations
   ---------------------|------------------|-------------|-----------|---------|--------|-----------------|------------|-----------------|------------
   my_feature           | Settings Panel   | MISSING     | N/A       | N/A     | N/A    | N/A             | N/A        | N/A             | N/A
   figma_feature        | Figma Screen     | OK          | STALE     | CURRENT | CLEAN  | 1 warning       | DRIFT      | STALE_INVARIANT | 3
   local_feature        | Dashboard        | OK          | CURRENT   | N/A     | CLEAN  | N/A             | N/A        | N/A             | N/A
   ```

   **Invariant column values:** CURRENT (pointer version matches source), STALE_INVARIANT (source has newer version), STALE_BRIEF (brief older than pointer), INVARIANT_VIOLATION (FORBIDDEN pattern hit), N/A (no design invariant).

7.1. **Invariant status summary:** After the per-feature table, print a separate invariant summary:
   ```
   DESIGN INVARIANTS (N total)
   Invariant                          Source  Version  Sync Status   Dependent Features
   i_design_visual_standards.md       figma   v456     STALE         3 features
   i_design_tokens.md                 git     v1.2.0   CURRENT       5 features
   ```

8. **Offer remediation:**
   - For STALE items (local artifacts): offer to update the Visual Specification via `purlin:spec <feature>`.
   - For STALE_INVARIANT: offer to sync via `purlin:invariant sync <invariant-file>`.
   - For STALE_BRIEF: offer to regenerate brief via `purlin:spec <feature>` (re-read Figma frames).
   - For INVARIANT_VIOLATION: report file:line evidence and suggest fix.

9. **Summary:** Report overall status:
   - CRITICAL issues found: "CRITICAL issues found -- resolve before release."
   - Warnings only: "Warnings found -- review recommended."
   - Clean: "All design artifacts clean."
