**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-design-audit instead." and stop.

---

Read `instructions/references/visual_spec_convention.md` before auditing.

Audit all design artifacts and visual specifications across the project for integrity, staleness, and anchor consistency.

**Workflow:**

1. **Inventory scan:** Glob for all `features/*.md` files. Read each one and extract `## Visual Specification` sections. For each `### Screen:` subsection, extract:
   - Screen name
   - Reference path/URL (from `- **Reference:**`)
   - Processed date (from `- **Processed:**`)
   - Whether a Description exists (from `- **Description:**`)
   - Checklist item count

2. **Reference integrity:** For each screen:
   - Local file references: verify the file exists on disk. Missing = CRITICAL.
   - URL references (Figma, Live): validate URL syntax only. Malformed = WARNING.
   - Description without reference: WARNING.
   - Reference without description: HIGH (unprocessed artifact).

3. **Staleness check:** For local artifact files:
   - Read the file's modification time.
   - Compare against the Processed date.
   - If file is newer than processed date: STALE.

4. **Anchor consistency:** Read all `features/design_*.md` anchor nodes. Scan descriptions for:
   - Hardcoded hex colors that match or approximate a token value in the anchor.
   - Hardcoded font family names that should reference a font token.
   - Hardcoded spacing values matching an anchor's spacing scale.
   - Flag each as WARNING with the suggested token name.

5. **Report:** Print a summary table:
   ```
   Feature              | Screen           | Ref Status  | Staleness | Anchor
   ---------------------|------------------|-------------|-----------|-------
   cdd_status_monitor   | Web Dashboard    | OK          | CURRENT   | CLEAN
   my_feature           | Settings Panel   | MISSING     | N/A       | N/A
   ```

6. **Offer remediation:** For STALE items, offer to re-ingest via `/pl-design-ingest reprocess <feature> <screen>`.

7. **Summary:** Report overall status:
   - CRITICAL issues found: "CRITICAL issues found -- resolve before release."
   - Warnings only: "Warnings found -- review recommended."
   - Clean: "All design artifacts clean."
