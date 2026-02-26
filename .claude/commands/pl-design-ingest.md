**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-design-ingest instead." and stop.

---

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
   - Image/PDF: Read the file using the Read tool (multimodal). Analyze visual content.
   - Live web page: Fetch using WebFetch. Extract visual state, CSS patterns, component structure.
   - Figma URL: Record the URL. Ask the user to provide an exported image or screenshot. If provided, process as image. If not, create a placeholder Description noting manual processing is needed.

5. **Generate description:** Create a structured markdown description covering:
   - Layout hierarchy and component inventory
   - Spacing relationships (mapped to anchor spacing scale if defined)
   - Color observations (mapped to project's design token names from anchor)
   - Typography observations (mapped to project's font stack tokens from anchor)
   - Structural elements specific to this feature
   - For live web pages: observable CSS patterns compared against anchor tokens

6. **Update feature file:**
   - If no `## Visual Specification` section exists, create one with the `> **Design Anchor:**` declaration.
   - Insert or update the `### Screen:` subsection with Reference, Processed date (today), Description, and draft checklist items.

7. **Commit:** Commit artifact file (if local) + feature spec update together: `spec(<feature_stem>): ingest design artifact for <screen_name>`.

**Token mapping rule:** When no `design_*.md` anchor exists, use literal observations and append a note: "No design anchor found -- descriptions use literal values. Create a design_*.md anchor to enable token mapping."
