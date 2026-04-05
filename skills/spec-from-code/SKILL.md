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

- If it exists: read it and verify it has the expected shape (`{"phases": [{"name": "...", "status": "complete"|"pending"}], ...}`). If malformed or missing required fields, warn the user and offer to start fresh. If valid, resume from the last incomplete phase. Skip phases whose `status` is `"complete"`. Do not re-ask questions whose answers are preserved in prior artifacts (`sfc_inventory.md`, `sfc_taxonomy.md`).
- If it does not exist: begin from Phase 1.

---

## Phase 1 — Parallel Exploration

1. List the project's top-level directories (via `ls`). Ask the user (via `AskUserQuestion`) which directories to scan — offer the ones that look like source code as defaults. Everything not selected is automatically excluded. In the question, note which directories you will skip and why (e.g., "Skipping `docs/` (documentation), `templates/` (scaffolding), `.purlin/` (runtime)"). Base the skip list on what actually exists in the project, not a hardcoded list.

2. Create `.purlin/cache/sfc_state.json`:

```json
{
  "phase": 1,
  "status": "in_progress",
  "started_at": "<ISO 8601>",
  "directories": { "include": [] },
  "completed_categories": []
}
```

3. **Existing spec detection:** Scan for specs that can be used as migration context. Check two locations:

   **a) Legacy `features/` directory:** If `features/` exists at the project root:
   - Read all `.md` files recursively (excluding `.impl.md` companion files)
   - For each spec, extract: feature name, category (subdirectory), description, scenarios (Given/When/Then blocks), and any behavioral constraints
   - If `.impl.md` companion files exist, note them for `## Implementation Notes`

   **b) Non-compliant specs in `specs/`:** Glob `specs/**/*.md` and read each file. A spec is non-compliant if any of the following are true:
   - Missing `## Rules` section
   - Rules are not numbered (`RULE-N:` format)
   - Missing `## Proof` section
   - Missing `> Description:` metadata
   - Uses an outdated format (e.g., Given/When/Then scenarios instead of Rules/Proof)

   For each non-compliant spec, extract: feature name, category, existing rules (even if unnumbered), existing proofs, description, and any metadata fields already present.

   **Compliant specs** (with numbered rules, proofs, and proper sections) are left untouched — they are not migration candidates.

   Save all migration candidates to `.purlin/cache/sfc_existing.md` with per-feature entries: name, source location (`features/` or `specs/`), original content summary, and list of compliance issues.

   Print summary:
   - `Found N specs to migrate: X from features/, Y non-compliant in specs/.`
   - If nothing found: `No existing specs found. Generating from code.`

4. Launch up to 3 Explore sub-agents in parallel (Agent tool, subagent_type: `Explore`):

   - **Agent A (Structure):** "Scan the following directories for: directory tree structure, entry points (main/index files), route definitions, CLI entry points, config files, and file types present. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary."

   - **Agent B (Domain):** "Analyze the following directories for: frameworks used, domain concepts and terminology, tech stack (languages, key dependencies from package manifests), module boundaries, and public API surfaces. Also identify test characteristics for each module: does it require database setup, network calls, external APIs, browser automation, or manual human judgment? Flag modules that would need integration, e2e, or manual test tiers. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary."

   - **Agent C (Comments):** "Scan the following directories for: significant code comments (TODO, FIXME, HACK, architectural decision comments), module-level docstrings, and inline documentation. Directories: `<include>`. Exclude: `<exclude>`. Return a structured summary with file locations."

5. Synthesize all sub-agent results into `.purlin/cache/sfc_inventory.md`:
   - Directory map with annotations
   - Detected tech stack summary
   - Preliminary feature candidates (module-level granularity)
   - Cross-cutting concerns detected (auth, logging, error handling, config patterns)
   - Code comments index (significant comments with file locations)
   - Test tier flags per module (from Agent B: which modules need integration, e2e, or manual tiers)
   - **Existing spec summary** (if migration candidates were found): list of feature names, source locations, compliance issues, and scenario/rule counts — cross-referenced with code modules discovered by the exploration agents

6. Update state: `phase: 1, status: "complete"`.

7. Commit per `references/commit_conventions.md`: `chore(sfc): codebase survey complete (Phase 1)`

---

## Phase 2 — Interactive Taxonomy

1. Read `.purlin/cache/sfc_inventory.md`.

2. **Check for existing specs:** If specs already exist (glob `specs/**/*.md`), read them to extract existing category names and naming conventions. The proposed taxonomy MUST reuse existing category names where applicable. Only propose new categories when no existing one fits.

   **Check for migration candidates:** If `.purlin/cache/sfc_existing.md` exists (created in Phase 1), read it. Existing specs (from `features/` or non-compliant `specs/`) are the primary seed for the taxonomy — use their category names and feature names as starting points. When presenting the taxonomy, annotate each feature as `(migrating)` if it has an existing spec to migrate, or `(new)` if discovered only from code. This lets the user see what's being preserved vs. what's net-new.

3. Propose a category taxonomy grouping feature candidates into logical categories. Follow the categorization rules in `references/spec_quality_guide.md` ("Spec Categories"):
   - Executable code (scripts, hooks, server) → category matches the source directory (e.g., `hooks/`, `mcp/`, `proof/`)
   - Cross-cutting contracts and format definitions → `schema/`
   - Reference docs, skill definitions, and agent definitions (`references/`, `skills/`, `agents/`) → `instructions/`
   - End-to-end lifecycle flows → `integration/`

   Explain this categorization to the user when presenting the taxonomy. For each category, list: name, feature count, and per-feature name + one-line description.

4. Present categories in batches of 2–3 via `AskUserQuestion`. For each batch, show the proposed categories and end with the approval block:

   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚡ REVIEW CATEGORIES — Does this grouping look right?

     [y] Approve these categories
     [rename] Rename a category
     [merge] Merge two categories
     [split] Split a category
     [add] Add a missed feature
     [remove] Remove a false positive

   Waiting for your response...
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

   Do NOT proceed to the next batch without an explicit response.

5. **Near-duplicate detection:** After the taxonomy is drafted but before presenting anchors, compare proposed features *within each category* for rule similarity. Two features are near-duplicates when they would have substantially the same behavioral constraints (same rules, different implementations — e.g., three proof plugins that all do "parse markers, emit JSON, feature-scoped overwrite"). For each cluster of 2+ near-duplicates:
   - Ask the user via `AskUserQuestion`: "These N features share similar behavior: `<names>`. Consolidate into one spec with per-implementation rules, or keep separate?"
   - If consolidated: merge into a single spec whose rules cover the shared behavior and add per-implementation rules only where behavior diverges (e.g., marker syntax differences).
   - If kept separate: proceed, but note the overlap so the user is aware.

6. **Detect anchor candidates** from cross-cutting concerns. Use the following heuristics per anchor type to actively search for candidates — do not rely on passive observation alone:

   | Prefix | Domain | Detection heuristics |
   |--------|--------|---------------------|
   | `api_` | API contracts, REST conventions | Shared route patterns, middleware chains, response envelope formats, error response shapes, pagination conventions. Look for: express Router, Flask blueprints, API versioning patterns |
   | `security_` | Auth, access control, secrets | Auth middleware, password hashing, token validation, input sanitization, CORS config, rate limiting. Look for: bcrypt, JWT, helmet, csrf, rate-limit imports |
   | `design_` | Visual standards, layout | Shared UI component libraries, CSS token files, theme configs, layout patterns. Look for: styled-components, tailwind config, design token files, shared component directories |
   | `schema_` | Data models, validation | Database models, ORM definitions, migration files, validation schemas, shared types. Look for: sequelize/prisma/sqlalchemy models, zod/joi schemas, TypeScript interfaces in shared dirs |
   | `platform_` | Platform constraints, browser support | Browser compat configs, polyfills, platform-specific code paths, accessibility helpers. Look for: browserslist, babel config, a11y utilities |
   | `brand_` | Voice, naming, identity | Copy constants, i18n files, terminology glossaries, tone-of-voice docs. Look for: locales/, i18n imports, string constant files |
   | `prodbrief_` | User stories, UX requirements | User flow definitions, feature flags, A/B test configs, analytics event schemas. Look for: feature flag configs, analytics track calls, user journey comments |
   | `legal_` | Privacy, data handling, compliance | Cookie consent, privacy policy references, data retention configs, GDPR helpers. Look for: consent managers, data deletion utilities, PII handling |

   **Architecture choices should be anchors.** If the codebase uses a specific pattern consistently across multiple features (middleware auth, write-through caching, event-driven architecture), that pattern should become an anchor — not be buried in individual feature specs. After detecting candidates, group them: "These N features all use `<pattern>` → propose anchor: `<prefix>_<name>`." Present the grouping evidence to the user for confirmation.

   **Security anchor detection (mandatory):** In addition to the heuristic scan above, specifically grep the scanned directories for dangerous patterns:
   - `eval(`, `exec(` — arbitrary code execution
   - `os.system(` — unquoted shell execution
   - `subprocess` calls with `shell=True` — shell injection vector
   - Hardcoded strings resembling credentials (`password`, `secret`, `api_key`, `token = "..."`)
   - Direct file path manipulation from user input without sanitization

   Then:
   - If **any dangerous patterns are found**: propose a `security_` anchor with FORBIDDEN rules as negative assertions verifying these patterns don't exist in unsafe contexts.
   - If **no dangerous patterns are found**: propose a `security_` anchor anyway (e.g., `security_no_dangerous_patterns`) with rules confirming the codebase is clean — "No eval/exec calls", "No subprocess with shell=True", etc. Proving the absence of dangerous patterns is itself a valuable assertion.

   The security anchor MUST always be proposed. Proofs should be grep-based negative assertions (e.g., `grep -r "eval(" scripts/` returns zero matches).

   Present proposed anchors and ask for approval:

   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚡ REVIEW ANCHORS — <N> cross-cutting constraints detected

     [y] Approve all anchors
     [rename] Rename an anchor
     [remove] Remove an anchor
     [add] Add a missing anchor

   Waiting for your response...
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

   Use `AskUserQuestion` to pause. Do NOT proceed without an explicit response.

7. **Security anchor gate (mandatory, not skippable):** Before proceeding to Phase 3, verify that at least one `security_` prefixed anchor exists in the confirmed taxonomy. If none was confirmed:
   - Run the FORBIDDEN pattern grep anyway (`eval(`, `exec(`, `os.system(`, `shell=True`, hardcoded credentials)
   - If zero dangerous patterns found: propose `security_no_dangerous_patterns` with rules confirming absence
   - If patterns found: propose `security_<name>` with FORBIDDEN rules
   - Present to user for confirmation via `AskUserQuestion`
   - Phase 3 cannot begin without at least one security anchor confirmed or explicitly rejected by the user

8. Write the validated taxonomy to `.purlin/cache/sfc_taxonomy.md`:
   - Ordered anchor list (with type prefix and description)
   - Ordered category list with features
   - Per-feature: proposed file name, description, and anchor references

9. Update state: `phase: 2, status: "complete"`.

10. Commit per `references/commit_conventions.md`: `chore(sfc): taxonomy review complete (Phase 2)`

---

## Phase 3 — Spec Generation

**Resume logic:** If resuming Phase 3, read `completed_categories` from the state file. Skip those categories. Continue with the first incomplete category.

### Step 1 — Generate Anchor Specs

For each approved anchor from the taxonomy:

1. Create `specs/<category>/<prefix_name>.md` using 3-section format:

```markdown
# Anchor: <prefix_name>

> Description: <What cross-cutting concern this anchor defines>
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

2. Commit each anchor individually per `references/commit_conventions.md`: `spec(sfc): create anchor <name>`

### Step 2 — Generate Feature Specs per Category

Process categories in dependency order: categories with fewer anchor dependencies first.

For each category:

1. **Deep code reading:** If the category spans 5+ source files, launch an Explore sub-agent (Agent tool, subagent_type: `Explore`) to read the relevant source. For smaller categories, read files directly.

2. **Validate references before writing each spec:**

   **Scope validation:** Before writing `> Scope:`, verify each file path exists on disk. If a file was detected in Phase 1 exploration but has since been deleted or moved, exclude it from the Scope line. Do not write broken scope references.

   **Requires validation (blocking):** Before writing `> Requires:`, glob `specs/**/<name>.md` for EACH reference. A reference is valid only if it (a) already exists on disk from a prior category or anchor generation, or (b) is listed in the taxonomy and queued for generation in a later category. If a reference would be broken (neither exists nor queued), DO NOT write the spec with the broken reference — remove it from `> Requires:` and print: `Removed > Requires: <name> — spec not found. Create it first with purlin:spec <name>, then add the reference back.`

   **Scope overlap suggestions:** After validating references, scan all existing anchors (all specs in `specs/_anchors/`). If an anchor's `> Scope:` patterns overlap with this feature's scope but the anchor is not in `> Requires:`, suggest it:
   ```
   Suggested > Requires: based on file overlap:
     api_rest_conventions — Scope overlaps with src/api/
   Add to > Requires:? [y/n]
   ```
   Global anchors (with `> Global: true`) are auto-applied and don't need `> Requires:` — note them for the user's awareness.

3. **Existing spec migration (per feature):** Before generating a spec, check if this feature has a migration candidate in `.purlin/cache/sfc_existing.md` (matched by name, or by file scope overlap if names differ). If one exists:

   **From `features/` (legacy format):**
   - Read the original `features/<category>/<name>.md` file in full
   - Read any companion `.impl.md` file if present
   - Extract scenarios (Given/When/Then), descriptions, and behavioral constraints
   - Old scenarios become RULE-N candidates; old descriptions inform `## What it does`
   - If a companion `.impl.md` exists, extract architecturally significant details for `## Implementation Notes`

   **From `specs/` (non-compliant format):**
   - Read the existing `specs/<category>/<name>.md` file in full
   - Preserve all content that is already correct: existing rules (renumber if needed), existing proofs, existing metadata (`> Scope:`, `> Stack:`, `> Requires:`)
   - Fix compliance issues: add missing `> Description:`, number unnumbered rules, add missing `## Proof` section, convert any Given/When/Then scenarios to Rules/Proof format
   - The existing spec is overwritten in place with the compliant version

   **For both sources:**
   - Use the old spec as the **primary input** — preserve the author's intent, rules, and descriptions with minimal loss
   - Compare the old spec's claims against the current code (from the deep code reading in step 1). If the code has diverged, flag the discrepancy for the user in the review step
   - Mark the generated spec: `<!-- Migrated by purlin:spec-from-code. Review and refine. -->` instead of the standard generated header

   If no migration candidate exists, generate from code alone (standard behavior).

4. For each feature in the category, write `specs/<category>/<name>.md`:

```markdown
<!-- Generated by purlin:spec-from-code. Review and refine. -->
# Feature: <name>

> Description: <One-line summary of what this feature does>
> Requires: <anchor_name> (if applicable)
> Scope: <source files>
> Stack: <language>/<framework>, <key libraries>, <patterns>

## What it does

<One paragraph describing the feature.>

## Rules

- RULE-1: <Behavioral constraint extracted from code>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion>
- PROOF-2 (RULE-2): <Observable assertion>

## Implementation Notes

Extracted from source (include when architecturally significant):
- Design pattern: <description> (file:line)
- Caching strategy: <description> (file:line)
- Concurrency model: <description> (file:line)
- Data flow: <description> (file:line)
- Key tradeoff: <description> (file:line)
- TODO/Known issue: <description> (file:line)
```

**`> Stack:` metadata:** Populate from the actual imports/dependencies in the feature's source files, not the project-level tech stack. Phase 1 Agent B detects the project stack; Phase 3 narrows it per-feature by reading source imports.

Examples:
- `> Stack: python/stdlib, subprocess (list-only), json, hashlib`
- `> Stack: node/express, axios, redis (cache), JWT auth`
- `> Stack: shell/bash, jq, curl`

5. **Tier review pass (mandatory):** Review every proof description just written for this category. For each proof, apply the tier heuristics from `references/spec_quality_guide.md` ("Tier Tags on Proofs"):
   - Does the proof shell out to git, subprocess, or call an external service? → append `@integration`
   - Does the proof need a browser or full app stack? → append `@e2e`
   - Does the proof need human judgment (visual, UX, brand)? → append `@manual`
   - Pure logic or local grep? → leave as unit (no tag)

   Do NOT present specs to the user with untagged proofs that clearly need a tier. When in doubt, tag `@integration`.

6. **Validate generated specs (mandatory before user review):** Read back every spec just written for this category. For each spec, verify:
   - `## What it does` contains at least one full sentence (not empty, not just whitespace)
   - `## Rules` contains at least one `RULE-N:` line
   - `## Proof` contains at least one `PROOF-N (RULE-N):` line
   - **FORBIDDEN proof precision:** If any proof uses grep-based negative assertions, verify the grep pattern targets assignment patterns, not bare keywords. If a pattern would match comments or variable names, refine it per `references/spec_quality_guide.md` ("FORBIDDEN Grep Precision").
   - **Edge case specificity:** If any proof describes a boundary condition or edge case, verify the description includes the triggering test input, not just the expected outcome. If a proof says "verify X works correctly" without specifying the input, rewrite it per `references/spec_quality_guide.md` ("Edge Case Proof Specificity").

   If any section is empty or missing content:
   - Re-read the source files listed in the spec's `> Scope:` line
   - Fill the empty section immediately based on the source code
   - Do NOT present specs with empty sections to the user for confirmation

7. Present the generated specs for this category and ask for approval:

   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚡ REVIEW SPECS — <category_name> (<N> specs generated)

     [y] Approve and commit this category
     [n] Discard and regenerate
     [edit] I want to change specific specs

   Waiting for your response...
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

   Use `AskUserQuestion` to pause. Do NOT auto-approve or proceed without an explicit response.

8. Commit the category batch per `references/commit_conventions.md`: `spec(sfc): generate <category_name> specs`

9. **Per-category sync check:** After committing, call `sync_status` and check the output for the specs just generated. If sync_status reports any warnings (unnumbered rules, missing `## Rules` section, structural problems), fix them immediately — edit the spec, re-commit — before moving to the next category. Do not accumulate broken specs across categories.

10. Update state: add category name to `completed_categories`.

---

## Phase 4 — Finalize

1. Call `sync_status` to show the initial coverage state.

2. **Migration cleanup (if applicable):**

   If `features/` was detected and specs were migrated from it:
   - Ask the user via `AskUserQuestion`: `Migration complete. Remove old features/ directory? The old specs have been migrated to specs/. [y/n]`
   - If approved: delete `features/` and any companion files. Also delete old artifacts if present: `pl-*` symlinks, `*.sh` scripts at root.
   - If declined: leave `features/` in place. Print: `Keeping features/ — you can remove it manually when ready: rm -rf features/`

   Non-compliant specs in `specs/` are overwritten in place — no cleanup needed.

3. Summarize results:

```
Generated N specs in M categories.
Anchor specs: K
Migrated: L (X from features/, Y updated in specs/)
Features with implementation notes: J

Next:
  purlin:status      — see what needs tests
  purlin:unit-test   — write proof-marked tests
  purlin:spec <name> — refine a generated spec
```

4. Delete temporary files:
   - `.purlin/cache/sfc_state.json`
   - `.purlin/cache/sfc_inventory.md`
   - `.purlin/cache/sfc_taxonomy.md`
   - `.purlin/cache/sfc_existing.md` (if created)

5. Commit cleanup per `references/commit_conventions.md`: `chore(sfc): finalize spec-from-code (Phase 4)`

---

## Guidelines

For quality guidelines on writing rules, proof descriptions, tier assignment, anchor detection, FORBIDDEN patterns, `> Stack:` metadata, `> Requires:` and `> Scope:` guidance, see **`references/spec_quality_guide.md`**.

For audit criteria (what makes a proof STRONG vs WEAK vs HOLLOW), see **`references/audit_criteria.md`**. Write proof descriptions that will pass audit the first time — avoid patterns listed as HOLLOW (mocking the thing being tested, asserting existence instead of behavior, no assertions).

Additional spec-from-code-specific guidelines:

- **Do not use the `(assumed)` tag.** Rules extracted from code are observed behavior, not assumptions. The code IS the specific value — `timeout=500` is a fact, not an assumption.
- **Extract behavior, not implementation.** Rules describe what the code must do, not how it does it.
- **One feature per module boundary.** Spec the public interface, not internal helpers.
- **Mark generated specs.** Add `<!-- Generated by purlin:spec-from-code. Review and refine. -->` at the top. For migrated specs, use `<!-- Migrated by purlin:spec-from-code. Review and refine. -->` instead.
- **Implementation Notes capture architecture, not just TODOs.** Include whenever the source reveals decisions a rebuilding agent would need to replicate: design patterns, caching strategies, concurrency models, data flow, key tradeoffs. Omit only if the feature has trivially simple implementation.
- If Phase 1 Agent B flagged a module as requiring external dependencies, default its proofs to `@integration` unless the specific proof can be unit-tested in isolation.
