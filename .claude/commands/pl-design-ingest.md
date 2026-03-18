**Purlin command owner: PM**

If you are not operating as the Purlin PM, respond: "This is a PM command. Ask your PM agent to run /pl-design-ingest instead." and stop.

---

Read `instructions/references/visual_spec_convention.md` before processing.

Ingest a design artifact into a feature's Visual Specification section. This command processes external design artifacts (images, PDFs, Figma URLs, live web page URLs) into structured markdown descriptions mapped to the project's design token system.

**Input:** The argument specifies the artifact source. Accepted forms:
- A local file path to an image (PNG, JPG, SVG) or PDF
- A Figma public URL
- A live web page URL (prefix with "live:" if ambiguous)
- The keyword "reprocess" followed by a feature name and screen name to re-process an existing artifact

**Workflow:**

1. **Determine target:** Ask which feature file and which screen within it this artifact belongs to (if not already specified).

2. **Store artifact:**
   - Local file: Copy to `features/design/<feature_stem>/` with a descriptive name. Create the directory if needed.
   - URL: Record the URL directly in the Reference line (no download).

3. **Read design anchors:** Glob for all `features/design_*.md` files. Read each one to understand the project's design token system (color tokens, font tokens, spacing scale, theme behavior).

4. **Process artifact:**
   - Image/PDF: Read the file using the Read tool (multimodal). Analyze visual content. Extract observable design tokens.
   - Live web page: Fetch using WebFetch. Extract visual state, CSS patterns, component structure. Map CSS properties to project tokens.
   - Figma URL with MCP available: Call Figma MCP tools to extract component tree structure, auto-layout properties, design variables (colors, spacing, typography), component variants and states, and annotations.
     3.1: Call `get_design_context` to extract annotations. Present behavioral notes to user: "I found these behavioral notes in the Figma annotations: [list]. I'll use these to draft scenarios -- let me know if any are outdated."
     3.2: Compare extracted Figma variable names against design anchor token list. Auto-generate identity Token Map entries for matches (with or without `var()` / `--` prefix normalization). Report identity vs. manual mapping counts.
     Auto-generate the Token Map by mapping Figma design variable names to project tokens. Also generate `brief.json` (see step 5.1).
   - Figma URL without MCP: Record the URL. Walk the user through Figma MCP setup: (1) run `claude mcp add --transport http figma https://mcp.figma.com/mcp`, (2) restart Claude, (3) run the `/mcp` command, select the Figma MCP, and complete OAuth in the browser. Ask the user to provide an exported image or screenshot in the meantime. If provided, process as image. If not, create a placeholder Token Map noting manual processing is needed and append: "For higher fidelity, install Figma MCP."

5. **Generate Token Map and checklists:**
   - Create a Token Map mapping design token names (from Figma or observed from artifacts) to the project's token system:
     ```markdown
     - **Token Map:**
       - `surface` -> `var(--project-bg)`
       - `primary` -> `var(--project-accent)`
     ```
   - For identity mappings (Figma name matches project token), auto-generate entries without user input. Report identity vs. manual counts.
   - If annotations contain behavioral notes, draft Gherkin scenario outlines from them. Present to user for review.
   - Generate measurable visual acceptance checklist items (`- [ ]`) derived from design properties (dimensions, spacing, colors, typography, layout).
   - Do NOT generate prose descriptions. The Token Map + checklists replace the previous Description paragraph.

5.1. **Generate brief.json (Figma MCP only):**
   When processing a Figma URL with MCP available, also generate `features/design/<feature_stem>/brief.json` containing:
   - `figma_url`: The source Figma URL
   - `figma_last_modified`: The design's `lastModified` timestamp from MCP
   - `screens`: Per-screen structured data (node ID, dimensions, components, layout)
   - `tokens`: Figma design variable names and their resolved values
   - `code_connect` (optional): When MCP response includes Code Connect data, include component-to-source mappings. Each entry maps a component name to `source_file`, `props`, and `figma_node_id`. Report: "Code Connect data found for N components." Omit key silently if no Code Connect data present.

5.2. **Extract Figma dev status (Figma MCP only):**
   When processing a Figma URL with MCP available:
   - Read the frame's dev mode status (Design, Ready for Dev, Completed) via MCP.
   - If available, include in `brief.json` as `figma_dev_status` (`"ready_for_dev"`, `"completed"`, or `null`).
   - Include the Figma file version ID in `brief.json` as `figma_version_id`.
   - Report: "Figma dev status: <status>".
   - If unavailable, set `figma_dev_status` to `null` and omit `> Figma Status:` from the feature spec.

6. **Update feature file:**
   - If no `## Visual Specification` section exists, create one with the `> **Design Anchor:**` declaration.
   - Insert or update the `### Screen:` subsection with Reference, Processed date (today), Token Map, and draft checklist items.
   - Do NOT insert a `- **Description:**` field.
   - If Figma dev status was extracted (step 5.2), add `> Figma Status: <status>` to the feature spec's blockquote metadata (after Prerequisite lines).

7. **Dev Resources linking (Figma MCP only, optional):**
   After ingestion, offer to attach the feature spec URL to the Figma node via the Dev Resources API. This creates bidirectional traceability visible in Figma Dev Mode. Ask user: "Would you like to link this spec back to the Figma component via Dev Resources?" Only proceed with user confirmation. Skip silently if declined or if Dev Resources API is unavailable.

8. **Commit:** Commit artifact file (if local) + brief.json (if generated) + feature spec update together: `spec(<feature_stem>): ingest design artifact for <screen_name>`.

**Token mapping rule:** When no `design_*.md` anchor exists, use literal values in the Token Map (e.g., `` `primary` -> `#2196F3` ``) and append a note: "No design anchor found -- Token Map uses literal values. Create a design_*.md anchor to enable token mapping."
