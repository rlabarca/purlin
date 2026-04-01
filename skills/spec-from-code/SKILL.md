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

   - **Agent B (Domain):** "Analyze the following directories for: frameworks used, domain concepts and terminology, tech stack (languages, key dependencies from package manifests), module boundaries, and public API surfaces. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary."

   - **Agent C (Comments):** "Scan the following directories for: significant code comments (TODO, FIXME, HACK, architectural decision comments), module-level docstrings, and inline documentation. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary with file locations."

4. Synthesize all sub-agent results into `.purlin/cache/sfc_inventory.md`:
   - Directory map with annotations
   - Detected tech stack summary
   - Preliminary feature candidates (module-level granularity)
   - Cross-cutting concerns detected (auth, logging, error handling, config patterns)
   - Code comments index (significant comments with file locations)

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

5. **Detect anchor/invariant candidates** from cross-cutting concerns. Classify by type prefix:

   | Prefix | Domain |
   |--------|--------|
   | `api_` | API contracts, REST conventions |
   | `security_` | Auth, access control, secrets |
   | `design_` | Visual standards, layout |
   | `platform_` | Platform constraints, browser support |
   | `schema_` | Data models, validation |

   Ask the user (via `AskUserQuestion`) to confirm, rename, or remove proposed anchors.

6. Write the validated taxonomy to `.purlin/cache/sfc_taxonomy.md`:
   - Ordered anchor list (with type prefix and description)
   - Ordered category list with features
   - Per-feature: proposed file name, description, and anchor references

7. Update state: `phase: 2, status: "complete"`.

8. Commit: `git commit -m "chore(sfc): taxonomy review complete (Phase 2)"`

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

2. For each feature in the category, write `specs/<category>/<name>.md`:

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

3. Ask the user (via `AskUserQuestion`) to confirm the generated specs for this category look correct before proceeding to the next.

4. Commit the category batch: `git commit -m "spec(sfc): generate <category_name> specs"`

5. Update state: add category name to `completed_categories`.

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
