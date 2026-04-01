---
name: spec-from-code
description: Reverse-engineer 3-section specs from existing code
---

Scan an existing codebase and generate specs in 3-section format (`## What it does`, `## Rules`, `## Proof`). Uses parallel exploration, interactive taxonomy review, and dependency-ordered generation with durable state for cross-session continuity.

## Usage

```
purlin:spec-from-code [directory]    Scan a directory (default: src/ or lib/ or .)
purlin:spec-from-code --resume       Resume from last incomplete phase
```

## Resume Check

Before starting, check for `.purlin/cache/sfc_state.json`.

- If it exists: read it and resume from the last incomplete phase. Skip phases whose `status` is `"complete"`. Do not re-ask questions whose answers are preserved in prior artifacts (`sfc_inventory.md`, `sfc_taxonomy.md`).
- If it does not exist: begin from Phase 1.

---

## Phase 1 — Parallel Exploration

1. Ask the user (via `AskUserQuestion`) which directories to scan:
   - Offer common defaults: `src/`, `lib/`, `app/`
   - Offer common exclusions: `node_modules/`, `vendor/`, `.purlin/`, `dist/`, `build/`

2. Create `.purlin/cache/sfc_state.json`:

```json
{
  "phase": 1,
  "status": "in_progress",
  "started_at": "<ISO 8601>",
  "directories": { "include": [], "exclude": [] },
  "completed_categories": []
}
```

3. Launch up to 3 Explore sub-agents in parallel (Agent tool, subagent_type: `Explore`):

   - **Agent A (Structure):** "Scan the following directories for: directory tree structure, entry points (main/index files), route definitions, CLI entry points, config files, and file types present. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary."

   - **Agent B (Domain):** "Analyze the following directories for: frameworks used, domain concepts and terminology, tech stack (languages, key dependencies from package manifests), module boundaries, and public API surfaces. Also identify test characteristics for each module: does it require database setup, network calls, external APIs, browser automation, or manual human judgment? Flag modules that would need slow, e2e, or manual test tiers. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary."

   - **Agent C (Comments):** "Scan the following directories for: significant code comments (TODO, FIXME, HACK, architectural decision comments), module-level docstrings, and inline documentation. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary with file locations."

4. Synthesize all sub-agent results into `.purlin/cache/sfc_inventory.md`:
   - Directory map with annotations
   - Detected tech stack summary
   - Preliminary feature candidates (module-level granularity)
   - Cross-cutting concerns detected (auth, logging, error handling, config patterns)
   - Code comments index (significant comments with file locations)
   - Test tier flags per module (from Agent B: which modules need slow, e2e, or manual tiers)

5. Update state: `phase: 1, status: "complete"`.

6. Commit: `git commit -m "chore(sfc): codebase survey complete (Phase 1)"`

---

## Phase 2 — Interactive Taxonomy

1. Read `.purlin/cache/sfc_inventory.md`.

2. **Check for existing specs:** If specs already exist (glob `specs/**/*.md`), read them to extract existing category names and naming conventions. The proposed taxonomy MUST reuse existing category names where applicable. Only propose new categories when no existing one fits.

3. Propose a category taxonomy grouping feature candidates into logical categories. For each category, list: name, feature count, and per-feature name + one-line description.

4. Present categories in batches of 2–3 via `AskUserQuestion`. Let the user:
   - Rename categories
   - Merge or split categories
   - Add missed features
   - Remove false positives

5. **Near-duplicate detection:** After the taxonomy is drafted but before presenting anchors, compare proposed features *within each category* for rule similarity. Two features are near-duplicates when they would have substantially the same behavioral constraints (same rules, different implementations — e.g., three proof plugins that all do "parse markers, emit JSON, feature-scoped overwrite"). For each cluster of 2+ near-duplicates:
   - Ask the user via `AskUserQuestion`: "These N features share similar behavior: `<names>`. Consolidate into one spec with per-implementation rules, or keep separate?"
   - If consolidated: merge into a single spec whose rules cover the shared behavior and add per-implementation rules only where behavior diverges (e.g., marker syntax differences).
   - If kept separate: proceed, but note the overlap so the user is aware.

6. **Detect anchor/invariant candidates** from cross-cutting concerns. Classify by type prefix:

   | Prefix | Domain |
   |--------|--------|
   | `api_` | API contracts, REST conventions |
   | `security_` | Auth, access control, secrets |
   | `design_` | Visual standards, layout |
   | `brand_` | Voice, naming, identity |
   | `platform_` | Platform constraints, browser support |
   | `schema_` | Data models, validation |
   | `legal_` | Privacy, data handling, compliance |
   | `prodbrief_` | User stories, UX requirements |

   **Security anchor detection (mandatory):** In addition to the general cross-cutting scan above, specifically grep the scanned directories for dangerous patterns:
   - `eval(`, `exec(` — arbitrary code execution
   - `os.system(` — unquoted shell execution
   - `subprocess` calls with `shell=True` — shell injection vector
   - Hardcoded strings resembling credentials (`password`, `secret`, `api_key`, `token = "..."`)
   - Direct file path manipulation from user input without sanitization

   Then:
   - If **any dangerous patterns are found**: propose a `security_` anchor with FORBIDDEN rules as negative assertions verifying these patterns don't exist in unsafe contexts.
   - If **no dangerous patterns are found**: propose a `security_` anchor anyway (e.g., `security_no_dangerous_patterns`) with rules confirming the codebase is clean — "No eval/exec calls", "No subprocess with shell=True", etc. Proving the absence of dangerous patterns is itself a valuable assertion.

   The security anchor MUST always be proposed. Proofs should be grep-based negative assertions (e.g., `grep -r "eval(" scripts/` returns zero matches).

   Ask the user (via `AskUserQuestion`) to confirm, rename, or remove proposed anchors.

7. Write the validated taxonomy to `.purlin/cache/sfc_taxonomy.md`:
   - Ordered anchor list (with type prefix and description)
   - Ordered category list with features
   - Per-feature: proposed file name, description, and anchor references

8. Update state: `phase: 2, status: "complete"`.

9. Commit: `git commit -m "chore(sfc): taxonomy review complete (Phase 2)"`

---

## Phase 3 — Spec Generation

**Resume logic:** If resuming Phase 3, read `completed_categories` from the state file. Skip those categories. Continue with the first incomplete category.

### Step 1 — Generate Anchor Specs

For each approved anchor from the taxonomy:

1. Create `specs/<category>/<prefix_name>.md` using 3-section format:

```markdown
# Anchor: <prefix_name>

> Scope: <file patterns this anchor governs>

## What it does

<One paragraph: what cross-cutting concern this anchor defines.>

## Rules

- RULE-1: <Constraint that applies to all features requiring this anchor>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <How to verify compliance>
- PROOF-2 (RULE-2): <How to verify compliance>
```

2. Commit each anchor individually: `git commit -m "spec(sfc): create anchor <name>"`

### Step 2 — Generate Feature Specs per Category

Process categories in dependency order: categories with fewer anchor dependencies first.

For each category:

1. **Deep code reading:** If the category spans 5+ source files, launch an Explore sub-agent (Agent tool, subagent_type: `Explore`) to read the relevant source. For smaller categories, read files directly.

2. **Validate references before writing each spec:**

   **Scope validation:** Before writing `> Scope:`, verify each file path exists on disk. If a file was detected in Phase 1 exploration but has since been deleted or moved, exclude it from the Scope line. Do not write broken scope references.

   **Requires validation:** Before writing `> Requires:`, verify each referenced spec or anchor either (a) already exists on disk as `specs/**/<name>.md` from a prior category or anchor generation, or (b) is listed in the taxonomy and queued for generation in a later category. If a reference would be broken (neither exists nor queued), remove it from `> Requires:` and log a warning to the user: "Skipped > Requires: `<name>` — spec not found. Add manually after creation."

3. For each feature in the category, write `specs/<category>/<name>.md`:

```markdown
<!-- Generated by purlin:spec-from-code. Review and refine. -->
# Feature: <name>

> Requires: <anchor_name> (if applicable)
> Scope: <source files>

## What it does

<One paragraph describing the feature.>

## Rules

- RULE-1: <Behavioral constraint extracted from code>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion>
- PROOF-2 (RULE-2): <Observable assertion>

## Implementation Notes

<!-- Include this section only if significant code comments were found -->
Extracted from source:
- TODO: <description> (file:line)
- Architectural decision: <description> (file:line)
- Known issue: <description> (file:line)
```

4. **Validate generated specs (mandatory before user review):** Read back every spec just written for this category. For each spec, verify:
   - `## What it does` contains at least one full sentence (not empty, not just whitespace)
   - `## Rules` contains at least one `RULE-N:` line
   - `## Proof` contains at least one `PROOF-N (RULE-N):` line

   If any section is empty or missing content:
   - Re-read the source files listed in the spec's `> Scope:` line
   - Fill the empty section immediately based on the source code
   - Do NOT present specs with empty sections to the user for confirmation

5. Ask the user (via `AskUserQuestion`) to confirm the generated specs for this category look correct before proceeding to the next.

6. Commit the category batch: `git commit -m "spec(sfc): generate <category_name> specs"`

7. **Per-category sync check:** After committing, call `sync_status` and check the output for the specs just generated. If sync_status reports any warnings (unnumbered rules, missing `## Rules` section, structural problems), fix them immediately — edit the spec, re-commit — before moving to the next category. Do not accumulate broken specs across categories.

8. Update state: add category name to `completed_categories`.

---

## Phase 4 — Finalize

1. Call `sync_status` to show the initial coverage state.

2. Summarize results:

```
Generated N specs in M categories.
Anchor specs: K
Features with implementation notes: J

Next:
  purlin:status      — see what needs tests
  purlin:unit-test   — write proof-marked tests
  purlin:find <name> — review a specific spec
  purlin:spec <name> — refine a generated spec
```

3. Delete temporary files:
   - `.purlin/cache/sfc_state.json`
   - `.purlin/cache/sfc_inventory.md`
   - `.purlin/cache/sfc_taxonomy.md`

4. Commit cleanup: `git commit -m "chore(sfc): finalize spec-from-code (Phase 4)"`

---

## Guidelines

- **Extract behavior, not implementation.** Rules describe what the code must do, not how it does it.
- **One feature per module boundary.** Spec the public interface, not internal helpers.
- **Conservative rule count.** Start with 2–5 rules per feature. Users can add more via `purlin:spec`.
- **Mark generated specs.** Add `<!-- Generated by purlin:spec-from-code. Review and refine. -->` at the top.
- **Anchors for cross-cutting concerns only.** Auth middleware is an anchor. A single utility function is not.
- **Implementation Notes are optional.** Only include when source comments contain TODOs, architectural decisions, or known issues worth preserving.
- **Observable assertion quality.** Proof descriptions must specify concrete inputs and expected outputs so an agent can write the test without interpretation. Avoid vague verbs like "test", "verify", "check" without specifying *what* is asserted.

  Bad: `PROOF-1 (RULE-1): Test the login`
  Bad: `PROOF-1 (RULE-1): Verify authentication works`
  Good: `PROOF-1 (RULE-1): POST {"user": "alice", "pass": "wrong"} to /login; verify 401 response`
  Good: `PROOF-1 (RULE-1): Grep src/ for eval(); verify zero matches`

### Tier Assignment

When writing `## Proof` descriptions in Phase 3, assign a tier tag based on what the proof actually requires to execute. Proofs without a tag are `default` tier.

| Heuristic | Tier | Example |
|-----------|------|---------|
| Pure logic, no I/O, no external dependencies | default (no tag) | Validate input format, compute hash, parse config |
| Needs database, network, filesystem, or external service | `@slow` | API roundtrip, database query, file system operations |
| Needs browser, full app stack, or UI rendering | `@e2e` | Playwright login flow, screenshot comparison, full page render |
| Requires human judgment — visual, UX, brand voice | `@manual` | Review copy against brand guide, verify layout feels balanced |

Append the tier tag to the end of the proof description line:

```
- PROOF-1 (RULE-1): Parse config file and return default values
- PROOF-2 (RULE-2): POST to /api/users with mock database; verify 201 response @slow
- PROOF-3 (RULE-3): Load checkout page in browser; verify 3-click flow @e2e
- PROOF-4 (RULE-4): Review error messages against brand voice guide @manual
```

If Phase 1 Agent B flagged a module as requiring external dependencies (database, network, external APIs), all proofs for features in that module should default to `@slow` unless the specific proof can be unit-tested in isolation without those dependencies.

### Manual Proof Detection

When generating proofs in Phase 3, detect features whose source code involves visual output, UI rendering, or UX flows. Heuristics:
- Source files in `views/`, `pages/`, `templates/`, `layouts/` directories
- React/Vue/Svelte component files with layout or styling logic
- CSS/SCSS files referenced in `> Scope:`
- Any code producing HTML output

For these features, tag visual/UX proofs as `@manual` instead of writing automated proof descriptions that cannot actually be automated:

Bad: `PROOF-3 (RULE-3): Verify the layout matches the design`
Good: `PROOF-3 (RULE-3): Compare rendered page against Figma design @manual`

If a feature's scope includes only UI/visual files, default all its proofs to `@manual` unless a specific proof can be asserted programmatically (e.g., checking for required HTML attributes).
