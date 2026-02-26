**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run `/pl-spec-from-code`." and stop.

---

## Purpose

Reverse-engineer feature specs from an existing codebase. Scans source directories, proposes a category taxonomy interactively, and generates feature files, anchor nodes, and companion files. Uses a 5-phase, context-managed approach with durable state artifacts for cross-session continuity.

---

## Resume Check

Before starting, check for an existing state file at `.purlin/cache/sfc_state.json`.

- If the file exists, read it and resume from the last incomplete phase. Skip all phases whose status is `complete`. Do NOT re-ask questions whose answers are preserved in the taxonomy or inventory files from prior phases.
- If the file does not exist, begin from Phase 0.

---

## Phase 0 — Initialization

1. Prompt the user (via `AskUserQuestion`) to specify which directories contain application source code:
   - Offer common defaults: `src/`, `lib/`, `app/`
   - Offer common exclusions: `node_modules/`, `vendor/`, `.purlin/`, `tools/`, `dist/`, `build/`
2. Create the state file at `.purlin/cache/sfc_state.json`:
   ```json
   {
     "phase": 0,
     "status": "in_progress",
     "started_at": "<ISO 8601 timestamp>",
     "directories": { "include": [...], "exclude": [...] },
     "completed_categories": []
   }
   ```
3. Update state: set `phase: 0, status: "complete"`.
4. Commit: `git commit -m "chore(sfc): initialize spec-from-code state (Phase 0)"`

---

## Phase 1 — Codebase Survey

1. Read the state file to get directory include/exclude lists.
2. Launch up to 3 Explore sub-agents in parallel using the `Task` tool (subagent_type: `Explore`):
   - **Agent A (Structure):** "Scan the following directories for: directory tree structure, entry points (main/index files), file types present, route definitions, CLI entry points, and config files. Directories to scan: <include_list>. Exclude: <exclude_list>. Return a structured summary."
   - **Agent B (Domain):** "Analyze the following directories for: key source files, frameworks used, domain concepts and terminology, tech stack (languages, frameworks, key dependencies from package manifests), module boundaries, and public API surfaces. Directories: <include_list>. Exclude: <exclude_list>. Return a structured summary."
   - **Agent C (Comments & Docs):** "Scan the following directories for: significant code comments (TODO, FIXME, HACK, architectural decision comments, module-level docstrings), existing documentation files (READMEs, docs/), and any inline documentation. Directories: <include_list>. Exclude: <exclude_list>. Return a structured summary with file locations."
3. Synthesize all sub-agent results into `.purlin/cache/sfc_inventory.md` containing:
   - Directory map with annotations
   - Detected tech stack summary
   - Preliminary feature candidates (module-level granularity)
   - Cross-cutting concerns detected
   - Code comments index (significant comments with file locations)
4. Update state: `phase: 1, status: "complete"`.
5. Commit: `git commit -m "chore(sfc): codebase survey complete (Phase 1)"`

---

## Phase 2 — Taxonomy Review

1. Read `.purlin/cache/sfc_inventory.md`.
2. Propose a category taxonomy grouping feature candidates into logical categories. For each category, present: name, feature count, and per-feature name + one-line description.
3. Ask the user (via `AskUserQuestion`, in batches of 2-3 categories) to validate each category: confirm the name, confirm feature membership, and identify missed features. Adjust based on feedback.
4. Propose anchor nodes derived from detected cross-cutting concerns, classified by type:
   - `arch_*` for technical constraints
   - `design_*` for visual/UX standards
   - `policy_*` for governance rules
5. Ask the user to validate the proposed anchor nodes.
6. Write the validated taxonomy to `.purlin/cache/sfc_taxonomy.md` containing:
   - Ordered anchor node list (with type prefix and description)
   - Ordered category list with features
   - Per-feature: proposed file name, description, and anchor node references
7. Update state: `phase: 2, status: "complete"`.
8. Commit: `git commit -m "chore(sfc): taxonomy review complete (Phase 2)"`

---

## Phase 3 — Feature Generation

**Resume logic:** If resuming Phase 3, read `completed_categories` from the state file and skip those categories. Continue with the first incomplete category.

### Step 1: Generate Anchor Nodes

For each approved anchor node from the taxonomy:
1. Read the canonical template at `tools/feature_templates/_anchor.md`.
2. Create the anchor node file in `features/` using the correct prefix (`arch_`, `design_`, or `policy_`).
3. Include:
   - Proper heading (`# Architecture:`, `# Policy:`, or `# Design:` matching prefix type)
   - `> Label:` and `> Category:` metadata
   - Purpose section
   - Invariants section (populated from detected cross-cutting concerns)
4. Commit each anchor node individually: `git commit -m "feat(sfc): create anchor node <name>"`

### Step 2: Generate Features per Category

Process categories in dependency order (categories with fewer anchor node dependencies first).

For each category:
1. If the category spans more than 5 source files, use an Explore sub-agent (Task tool, subagent_type: `Explore`) to read the relevant source. Otherwise read directly.
2. Read the canonical template at `tools/feature_templates/_feature.md`.
3. For each feature in the category:
   - Create the feature file in `features/` from the template.
   - Include: `> Label:`, `> Category:`, and `> Prerequisite:` metadata linking to relevant anchor nodes.
   - Include: Overview paragraph, Requirements organized into numbered subsections, Gherkin scenarios describing current code behavior.
   - Add the draft notice to the Scenarios section:
     ```
     > **[Draft]** These scenarios were auto-generated from existing code by /pl-spec-from-code. Review and refine before marking as final.
     ```
   - Set status marker: `[TODO]`
   - If significant code comments were found for this feature's source files (TODOs, architectural decisions, known issues), create a companion file at `features/<name>.impl.md` with:
     - A `### Source Mapping` section listing which source files implement the feature
     - Extracted comments with source file references
4. Ask the user (via `AskUserQuestion`) to confirm the generated features look correct before proceeding.
5. Commit the entire category batch: `git commit -m "feat(sfc): generate <category_name> features"`
6. Update state: add category name to `completed_categories`.
7. Commit state update: `git commit -m "chore(sfc): mark <category_name> complete in state"`

---

## Phase 4 — Finalization

1. Run `tools/cdd/status.sh` to generate the initial Critic report and dependency graph.
2. Summarize the results:
   - Total features created
   - Total anchor nodes created
   - Total companion files created
   - Any immediate Critic findings
3. Delete temporary files:
   - `.purlin/cache/sfc_state.json`
   - `.purlin/cache/sfc_inventory.md`
   - `.purlin/cache/sfc_taxonomy.md`
4. Commit cleanup: `git commit -m "chore(sfc): finalize and clean up temporary files (Phase 4)"`
5. Print recommended next steps:
   - "Run `/pl-spec-code-audit` to validate the generated specs against the actual code and identify any gaps the import missed."
   - "Review generated features in dependency order (anchor nodes first) and refine the draft scenarios."
   - "Once specs are refined, have the Builder run `/pl-build` to begin implementation verification."
