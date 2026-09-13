---
name: spec-from-code
description: Reverse-engineer 2-section specs from existing code
---

Scan an existing codebase and generate specs in 2-section format (`## Rules`, `## Proof`). Uses parallel exploration, interactive taxonomy review, and dependency-ordered generation with durable state for cross-session continuity.

**Pending migrations:** call `sync_status` first when this skill would write specs or proofs, and follow `references/purlin_commands.md#pending-migrations` when it opens with a pending-migrations advisory.

**Paths in this skill:** every `references/`, `templates/`, `hooks/`, `scripts/` and `agents/` path below is relative to the plugin root; see `${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md#path-resolution`.

## Usage

```
purlin:spec-from-code [directory]    Scan a directory (default: src/ or lib/ or .)
```

## Resume Check

Before starting, check for `.purlin/cache/sfc_state.json`.

- If it exists: read it and verify it has the expected shape (`{"phases": [{"name": "...", "status": "complete"|"pending"}], ...}`). If malformed or missing required fields, warn the user and offer to start fresh. If valid, resume from the last incomplete phase. Skip phases whose `status` is `"complete"`. Do not re-ask questions whose answers are preserved in prior artifacts (`sfc_inventory.md`, `sfc_taxonomy.md`).
- If it does not exist: begin from Phase 1.

---

## Phase 1: Parallel Exploration

1. List the project's top-level directories (via `ls`). Ask the user (via `AskUserQuestion`) which directories to scan: offer the ones that look like source code as defaults. Everything not selected is automatically excluded. In the question, note which directories you will skip and why (e.g., "Skipping `docs/` (documentation), `templates/` (scaffolding), `.purlin/` (runtime)"). Base the skip list on what actually exists in the project, not a hardcoded list.

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

   **a) Legacy `features/` directory:** If `features/` exists at the project root, follow
   `${CLAUDE_PLUGIN_ROOT}/references/legacy_features_migration.md`: it owns the recursive read, the `.impl.md` and `.discoveries.md` companions, the per-feature migration and the cleanup Phase 4 offers.

   **b) Non-compliant specs in `specs/`:** Glob `specs/**/*.md` and read each file. A spec is non-compliant if any of the following are true:
   - Missing `## Rules` section
   - Rules are not numbered (`RULE-N:` format)
   - Missing `## Proof` section
   - Missing `> Description:` metadata
   - Uses an outdated format (e.g., Given/When/Then scenarios instead of Rules/Proof)

   For each non-compliant spec, extract: feature name, category, existing rules (even if unnumbered), existing proofs, description, and any metadata fields already present.

   **Compliant specs** (with numbered rules, proofs, and proper sections) are left untouched: they are not migration candidates.

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
   - **`e2e_capable` flag:** true only if an e2e-capable test runner is detectable: an e2e framework (Playwright, Cypress, Puppeteer, WebdriverIO, or similar) appears in the package manifest, or an e2e config file (`playwright.config.*`, `cypress.config.*`, etc.) exists. Record the detected runner name (or `none`). This drives the `@e2e` warning in Phase 3 step 11 and the Phase 4 summary.
   - **Existing spec summary** (if migration candidates were found): list of feature names, source locations, compliance issues, and scenario/rule counts: cross-referenced with code modules discovered by the exploration agents

6. **Generate environment anchor (mandatory):** Extract project-level environment data and write `specs/_anchors/project_environment.md`. This anchor captures what's needed to compile, run, and configure the project: information that no individual feature spec carries.

   **Extract from:**
   - **Runtime & framework:** `package.json` (engines field, main framework), `go.mod`, `pyproject.toml`, `Cargo.toml`, `Gemfile`, etc.
   - **Key dependencies with versions:** Read the lock file (`package-lock.json`, `yarn.lock`, `poetry.lock`, `go.sum`) for pinned versions of direct dependencies. Don't list every transitive dep: list the top-level deps that appear in import statements.
   - **Build config:** `next.config.js`, `webpack.config.js`, `tsconfig.json`, `Makefile`, `CMakeLists.txt`, `Dockerfile`, etc. Capture the build command and key overrides (output dir, asset prefix, compilation targets).
   - **Environment variables:** Grep scanned directories for `process.env.`, `import.meta.env.`, `os.environ`, `os.Getenv`, `System.getenv`, `ENV[`. Collect every env var name. Group into: required (app fails without), optional (has fallback), and secret (API keys, tokens: note the name but not the value).

   **Write the anchor:**
   ```markdown
   # Anchor: project_environment

   > Description: Runtime, dependencies, build config, and environment variable inventory.
   > Global: true
   > Scope: package.json, next.config.js, .env*

   ## Rules
   - RULE-1: Runtime is <language> <version> with <framework> <version>
   - RULE-2: Key dependencies: <name>@<version>, <name>@<version>, ...
   - RULE-3: Build command: <command>; key config: <asset prefix, output mode, etc.>
   - RULE-4: Required env vars: <list with descriptions>
   - RULE-5: Dev/prod split: <which env vars differ between environments>

   ## Proof
   - PROOF-1 (RULE-1): Read package.json engines and main framework version; verify match
   - PROOF-2 (RULE-2): Read lock file; verify listed dependency versions match
   - PROOF-3 (RULE-3): Read build config; verify build command and key overrides
   - PROOF-4 (RULE-4): Grep source for env var usage; verify all listed vars are present
   - PROOF-5 (RULE-5): Read .env files or env var references; verify dev/prod differences documented
   ```

   Present the environment anchor for review. Commit: `spec(sfc): create anchor project_environment`

7. Update state: `phase: 1, status: "complete"`.

8. Commit per `references/commit_conventions.md`: `chore(sfc): codebase survey complete (Phase 1)`

---

## Phase 2: Interactive Taxonomy

1. Read `.purlin/cache/sfc_inventory.md`.

2. **Check for existing specs:** If specs already exist (glob `specs/**/*.md`), read them to extract existing category names and naming conventions. The proposed taxonomy MUST reuse existing category names where applicable. Only propose new categories when no existing one fits.

   **Check for migration candidates:** If `.purlin/cache/sfc_existing.md` exists (created in Phase 1), read it. Existing specs (from `features/` or non-compliant `specs/`) are the primary seed for the taxonomy: use their category names and feature names as starting points. When presenting the taxonomy, annotate each feature as `(migrating)` if it has an existing spec to migrate, or `(new)` if discovered only from code. This lets the user see what's being preserved vs. what's net-new.

3. Propose a category taxonomy grouping feature candidates into logical categories. Follow the categorization rules in `references/spec_quality_guide.md` ("Spec Categories"):
   - Executable code (scripts, hooks, server) → category matches the source directory (e.g., `hooks/`, `mcp/`, `proof/`)
   - Cross-cutting contracts and format definitions → `_anchors/`
   - Reference docs and instruction files, where a project has them → `instructions/`
   - End-to-end lifecycle flows → the feature spec they validate, with the proofs tagged `@e2e`; `integration/` is legacy

   Explain this categorization to the user when presenting the taxonomy. For each category, list: name, feature count, and per-feature name + one-line description.

4. Present categories in batches of 2 to 3 via `AskUserQuestion`. For each batch, show the proposed categories and end with the approval block:

   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ⚡ REVIEW CATEGORIES: Does this grouping look right?

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

5. **Near-duplicate detection:** After the taxonomy is drafted but before presenting anchors, compare proposed features *within each category* for rule similarity. Two features are near-duplicates when they would have substantially the same behavioral constraints (same rules, different implementations: e.g., three proof plugins that all do "parse markers, emit JSON, feature-scoped overwrite"). For each cluster of 2+ near-duplicates:
   - Ask the user via `AskUserQuestion`: "These N features share similar behavior: `<names>`. Consolidate into one spec with per-implementation rules, or keep separate?"
   - If consolidated: merge into a single spec whose rules cover the shared behavior and add per-implementation rules only where behavior diverges (e.g., marker syntax differences).
   - If kept separate: proceed, but note the overlap so the user is aware.

6. **Single-feature category check:** Scan the proposed taxonomy for categories containing exactly one feature. A category folder must never hold a single spec. For each single-feature category:
   - Default: merge the feature into the closest related category (by domain or shared file scope) and note the merge when presenting the taxonomy.
   - If no existing category fits, ask the user via `AskUserQuestion`: "Category `<name>` would contain only `<feature>`. Merge into `<closest category>`, or keep it standalone?" If kept standalone, plan the spec at `specs/<name>.md` directly: do NOT create a folder for it. (Specs at the `specs/` root display under "other" in the dashboard.)

7. **Detect anchor candidates** from cross-cutting concerns. Work through the per-prefix detection heuristics in `references/spec_quality_guide.md` ("When to Create Anchors"), which lists what to grep for under each of the eight prefixes and how to group the hits into a proposed anchor.

   **API surface anchor (mandatory when API calls detected):** If Phase 1 exploration found HTTP client usage (fetch, axios, http.get, requests, net/http, etc.), generate an `api_surface` anchor listing every external endpoint the codebase calls. For each endpoint, capture: HTTP method, full path (including any base path prefix), and parameter shapes (query params, body fields). Trace from the HTTP call sites back to the URL construction: the relative path handed to the client is not the full path.

   **Domain schema anchors (mandatory when shared types detected):** If Phase 1 found shared type definitions (TypeScript interfaces, Python dataclasses, Go structs, SQL schemas) consumed by 3+ features, generate a `schema_` anchor for each major domain entity. Its rules carry the **critical field names**: the ones that appear in transformations, display logic, or conditional gates across features. Do not list every field; list the ones that would cause wrong behavior if an engineer used the wrong name.

   Either one takes this shape:

   ```markdown
   # Anchor: <prefix>_<name>
   > Description: <the cross-cutting contract this anchor fixes>
   ## Rules
   - RULE-1: <the constraint, carrying the exact names an engineer would otherwise guess>
   ```

   **Security anchor (mandatory):** a `security_` anchor is always proposed, whether or not the grep finds anything. Step 8 is the gate and carries the pattern list. Its proofs are grep-based negative assertions (`grep -r "eval(" scripts/` returns zero matches).

   Present the proposed anchors in the approval-block shape from step 4, headed `⚡ REVIEW ANCHORS: <N> cross-cutting constraints detected`, offering `[y] Approve all anchors`, `[rename] Rename an anchor`, `[remove] Remove an anchor` and `[add] Add a missing anchor`. Use `AskUserQuestion` to pause. Do NOT proceed without an explicit response.

8. **Security anchor gate (mandatory, not skippable):** Before proceeding to Phase 3, verify that at least one `security_` prefixed anchor exists in the confirmed taxonomy. If none was confirmed:
   - Run the FORBIDDEN pattern grep anyway (`eval(`, `exec(`, `os.system(`, `shell=True`, hardcoded credentials)
   - If zero dangerous patterns found: propose `security_no_dangerous_patterns` with rules confirming absence
   - If patterns found: propose `security_<name>` with FORBIDDEN rules
   - Present to user for confirmation via `AskUserQuestion`
   - Phase 3 cannot begin without at least one security anchor confirmed or explicitly rejected by the user

9. Write the validated taxonomy to `.purlin/cache/sfc_taxonomy.md`:
   - Ordered anchor list (with type prefix and description)
   - Ordered category list with features
   - Per-feature: proposed file name, description, and anchor references

10. Update state: `phase: 2, status: "complete"`.

11. Commit per `references/commit_conventions.md`: `chore(sfc): taxonomy review complete (Phase 2)`

---

## Phase 3: Spec Generation

**Resume logic:** If the Resume Check found a state file, read `completed_categories` from it. Skip those categories. Continue with the first incomplete category.

### Step 1: Generate Anchor Specs

For each approved anchor from the taxonomy:

1. Create `specs/<category>/<prefix_name>.md` using 2-section format:

```markdown
# Anchor: <prefix_name>

> Description: <What cross-cutting concern this anchor defines>
> Scope: <file patterns this anchor governs>

## Rules

- RULE-1: <Constraint that applies to all features requiring this anchor>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <How to verify compliance>
- PROOF-2 (RULE-2): <How to verify compliance>
```

2. Commit each anchor individually per `references/commit_conventions.md`: `spec(sfc): create anchor <name>`

### Step 2: Generate Feature Specs per Category

Process categories in dependency order: categories with fewer anchor dependencies first.

For each category:

1. **Deep code reading:** If the category spans 5+ source files, launch an Explore sub-agent (Agent tool, subagent_type: `Explore`) to read the relevant source. For smaller categories, read files directly.

2. **Validate references before writing each spec:**

   **Scope validation:** Before writing `> Scope:`, verify each file path exists on disk. If a file was detected in Phase 1 exploration but has since been deleted or moved, exclude it from the Scope line. Do not write broken scope references.

   **Requires validation (blocking):** Before writing `> Requires:`, glob `specs/**/<name>.md` for EACH reference. A reference is valid only if it (a) already exists on disk from a prior category or anchor generation, or (b) is listed in the taxonomy and queued for generation in a later category. If a reference would be broken (neither exists nor queued), DO NOT write the spec with the broken reference: remove it from `> Requires:` and print: `Removed > Requires: <name>. Spec not found. Create it first with purlin:spec <name>, then add the reference back.`

   **Scope overlap suggestions:** After validating references, scan all existing anchors (all specs in `specs/_anchors/`). If an anchor's `> Scope:` patterns overlap with this feature's scope but the anchor is not in `> Requires:`, suggest it:
   ```
   Suggested > Requires: based on file overlap:
     api_rest_conventions: Scope overlaps with src/api/
   Add to > Requires:? [y/n]
   ```
   Global anchors (with `> Global: true`) are auto-applied and don't need `> Requires:`: note them for the user's awareness.

3. **Existing spec migration (per feature):** Before generating a spec, check if this feature has a migration candidate in `.purlin/cache/sfc_existing.md` (matched by name, or by file scope overlap if names differ). If one exists:

   **From `features/` (legacy format):** follow `references/legacy_features_migration.md`, which carries the legacy read and the `.impl.md` / `.discoveries.md` companion extraction.

   **From `specs/` (non-compliant format):**
   - Read the existing `specs/<category>/<name>.md` file in full
   - Preserve all content that is already correct: existing rules (renumber if needed), existing proofs, existing metadata (`> Scope:`, `> Stack:`, `> Requires:`)
   - Fix compliance issues: add missing `> Description:`, number unnumbered rules, add missing `## Proof` section, convert any Given/When/Then scenarios to Rules/Proof format
   - The existing spec is overwritten in place with the compliant version

   **For both sources:**
   - Use the old spec as the **primary input**: preserve the author's intent, rules, and descriptions with minimal loss
   - Compare the old spec's claims against the current code (from the deep code reading in step 1). If the code has diverged, flag the discrepancy for the user in the review step
   - Mark the generated spec: `<!-- Migrated by purlin:spec-from-code. Review and refine. -->` instead of the standard generated header

   If no migration candidate exists, generate from code alone (standard behavior).

4. **Data contract extraction (mandatory for ALL features):** For every feature, trace data across system boundaries and capture the contracts that an engineer would get wrong in a rebuild. Capture the **exact field names** on every boundary: a rule that names the mechanism instead of the field is the number one rebuild risk. Apply all five categories below to every feature, not just UI, and follow `references/spec_quality_guide.md` ("Data contract extraction") for what to trace in each and how the rule reads.

   **a) Inbound contracts:** what data enters, in what shape

   **b) Outbound contracts:** what data leaves, in what shape

   **c) Transformation rules:** what logic converts between inbound and outbound

   **d) State transitions and initialization ordering:** lifecycle states, init and teardown order

   **e) Access contracts:** who can see or do what

5. **Draft and evaluate rules (mandatory):** Before writing the spec file, draft all candidate rules as full `RULE-N:` lines and evaluate each against the three tests below, which are the ones `references/spec_quality_guide.md` ("The rebuild test") states in full. This step applies to ALL features, not just UI, and it is the only place in this skill that states them: later steps re-apply these three rather than restating a fourth wording.

   **Draft:** Combine candidate rules from standard extraction (step 1's code reading) and data contract extraction (step 4). Write each as a `RULE-N:` line.

   **Evaluate each rule:**
   - **Rebuild test:** "If an engineer rebuilt this feature from only these rules, would they get this wrong without this rule?" If the answer is "no, they'd figure it out" or "QA would catch it": cut the rule.
   - **Behavior test:** "Does this describe what the feature does, or how the code does it?" If it names a library, hook, CSS value, or internal function: rewrite it as the observable behavior the code produces, or cut it.
   - **Overlap test:** "Would this rule always pass or fail together with another rule?" If yes: merge them.

   **Result:** A final rule list where every rule passes all three tests. This list goes into the spec file in step 6.

6. For each feature in the category, write `specs/<category>/<name>.md`:

```markdown
<!-- Generated by purlin:spec-from-code. Review and refine. -->
# Feature: <name>

> Description: <One-line summary of what this feature does>
> Requires: <anchor_name> (if applicable)
> Scope: <source files>
> Stack: <language>/<framework>, <key libraries>, <patterns>

## Rules

- RULE-1: <Behavioral constraint extracted from code>
- RULE-2: <Another constraint>

## Proof

- PROOF-1 (RULE-1): <Observable assertion>
- PROOF-2 (RULE-2): <Observable assertion>

## Implementation Notes

Extracted from source, when architecturally significant. Architecture decisions, library choices, caching strategies and design patterns go here and never in `## Rules`: they inform a rebuilding engineer but are not testable constraints.
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

7. **Tier review pass (mandatory):** Review every proof description just written for this category. For each proof, apply the tier heuristics from `references/spec_quality_guide.md` ("Tier Tags on Proofs"):
   - Does the proof shell out to git, subprocess, or call an external service? → append `@integration`
   - Does the proof need a browser or full app stack? → append `@e2e`
   - Does the proof need human judgment (visual, UX, brand)? → append `@manual`
   - Pure logic or local grep? → leave as unit (no tag)

   Do NOT present specs to the user with untagged proofs that clearly need a tier. When in doubt, tag `@integration`.

   **Platform tag review (mandatory):** a tier says what kind of test a proof is; `@on(...)` says
   where it has to run, and they are independent. For each proof ask whether its rule names a
   platform: a Windows-only path API, an APFS rename, a tool the host either has or does not. If
   it does, append `@on(<platform-id>[, <id>])` beside the tier and name the ids from the project's
   `platforms` registry (the family ids `windows`, `macos` and `linux` always resolve). Never
   append `@on(...)` to a proof any host could verify: an `@on` proof with no result on that
   platform reads AWAITING RUNNER and leaves the coverage denominator, so a stray tag hides the
   rule rather than strengthening it. See `references/formats/spec_format.md` ("Platform tags").

   **Inverse check (mandatory):** After assigning tier tags, verify each description matches its tag per `references/spec_quality_guide.md` ("E2E proof descriptions"). Every `@e2e` proof must read as an observable flow, arrange → act → observe through the real running app, and must not name a source file or internal function. Rewrite any proof of the form "Assert `<file>` does X" or "Assert `<internalFn>` uses Y" as a boundary observation (the outbound network request, the rendered output, the storage state after a real flow). If a proof tagged `@e2e` could pass without launching the app, either rewrite it as a flow or retag it to the tier it actually exercises.

8. **No test-only specs:** Never generate a spec whose purpose is to be a container for tests. If integration or e2e tests validate a feature's behavior, those tests should prove rules in that feature's spec, not in a separate spec. When code analysis reveals e2e test files, map their assertions to the feature spec they exercise and add rules there.

9. **Rebuild-risk filter and coverage check (mandatory):** Before presenting specs, apply three filters:

   **Filter 1: Drop implementation noise:** Review every rule just written. For each rule, ask: "Does this describe *what* the feature must do, or *how* the code does it?" Remove rules that specify:
   - CSS pixel values, margins, padding (visual polish: QA catches these)
   - Specific CSS techniques (`::before pseudo-element`, `rx={h/2}` for SVG)
   - Library or framework choices ("uses recharts", "uses `useMediaQuery`")
   - Token/variable names ("uses `--surface-primary`"): instead say what the behavior is ("follows the active theme")

   **Filter 2: Verify contract coverage:** Verify the spec covers the applicable contract boundaries from `references/spec_quality_guide.md` ("Coverage dimensions"). The spec MUST have rules for each boundary the feature touches:
   - Inbound contracts: exact field names from APIs, config, or upstream modules (from step 4a)
   - Outbound contracts: event names, payload shapes, and trigger conditions (from step 4b)
   - Transformation rules: field mappings, formulas, and formatting logic (from step 4c)
   - State transitions: lifecycle states and transition rules (from step 4d, if applicable)
   - Access contracts: permission/flag/mode gates (from step 4e, if applicable)

   **Filter 3: tier by rebuild risk.** Re-apply step 5's three tests to the final list and cut every rule that fails one, ranking what is left by `references/spec_quality_guide.md` ("Rebuild risk tiers"). Fix any IMPLEMENTATION or NOISE rule here rather than deferring it to review time.

10. **Validate generated specs (mandatory before user review):** Read back every spec just written for this category. For each spec, verify:
   - `> Description:` carries at least one full sentence (not empty, not just whitespace)
   - `## Rules` contains at least one `RULE-N:` line
   - `## Proof` contains at least one `PROOF-N (RULE-N):` line
   - **FORBIDDEN proof precision:** If any proof uses grep-based negative assertions, verify the grep pattern targets assignment patterns, not bare keywords. If a pattern would match comments or variable names, refine it per `references/spec_quality_guide.md` ("FORBIDDEN Grep Precision").
   - **Edge case specificity:** If any proof describes a boundary condition or edge case, verify the description includes the triggering test input, not just the expected outcome. If a proof says "verify X works correctly" without specifying the input, rewrite it per `references/spec_quality_guide.md` ("Edge Case Proof Specificity").
   - **Proof implementation-coupling:** No proof description names a source file or an internal function/symbol as the thing being asserted. Such proofs force unit-style tests that import internals and audit WEAK per `references/audit_criteria.md` ("E2E Proof Tier Integrity": tier mismatch, source-constant assertion). Rewrite them as boundary observations per `references/spec_quality_guide.md` ("E2E proof descriptions") before presenting to the user.

   If any section is empty or missing content:
   - Re-read the source files listed in the spec's `> Scope:` line
   - Fill the empty section immediately based on the source code
   - Do NOT present specs with empty sections to the user for confirmation

11. Present the generated specs for this category and ask for approval, in the approval-block shape from Phase 2 step 4, headed `⚡ REVIEW SPECS: <category_name> (<N> specs generated)` and offering `[y] Approve and commit this category`, `[n] Discard and regenerate` and `[edit] I want to change specific specs`. If the category's proofs include any `@e2e` tag AND the Phase 1 inventory's `e2e_capable` flag is false, put this warning above the options (omit it otherwise):

   ```
   ⚠ <K> proofs tagged @e2e but no e2e runner detected: they cannot execute
     until one is wired in (Playwright, Cypress, an MCP-driven browser, etc.).
     See references/supported_frameworks.md ("End-to-end (browser) proofs").
   ```

   Use `AskUserQuestion` to pause. Do NOT auto-approve or proceed without an explicit response.

12. Commit the category batch per `references/commit_conventions.md`: `spec(sfc): generate <category_name> specs`

13. **Per-category sync check:** After committing, call `sync_status` and check the output for the specs just generated. If sync_status reports any warnings (unnumbered rules, missing `## Rules` section, structural problems), fix them immediately (edit the spec, re-commit) before moving to the next category. Do not accumulate broken specs across categories.

14. Update state: add category name to `completed_categories`.

---

## Phase 4: Finalize

1. Call `sync_status` to show the initial coverage state.

2. **Migration cleanup (if applicable):** If `features/` was detected and specs were migrated from
   it, run the cleanup step of `references/legacy_features_migration.md`, which asks before deleting anything. Non-compliant specs in `specs/` are overwritten in place: no cleanup needed.

3. Summarize results:

```
Generated N specs in M categories.
Anchor specs: K
Migrated: L (X from features/, Y updated in specs/)
Features with implementation notes: J

Next:
  purlin:status     : see what needs tests
  purlin:test  : write proof-marked tests
  purlin:spec <name>: refine a generated spec
```

   If any generated proofs are tagged `@e2e` and the Phase 1 `e2e_capable` flag is false, append to the summary:

```
⚠ <K> proofs tagged @e2e but no e2e runner detected: they cannot execute until
  one is wired in. See references/supported_frameworks.md ("End-to-end (browser) proofs").
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

For audit criteria (what makes a proof STRONG vs WEAK vs HOLLOW), see **`references/audit_criteria.md`**. Write proof descriptions that will pass audit the first time: avoid patterns listed as HOLLOW (mocking the thing being tested, asserting existence instead of behavior, no assertions).

Additional spec-from-code-specific guidelines:

- **Do not use the `(assumed)` tag.** Rules extracted from code are observed behavior, not assumptions. The code IS the specific value: `timeout=500` is a fact, not an assumption.
- **One feature per module boundary.** Spec the public interface, not internal helpers.
- If Phase 1 Agent B flagged a module as requiring external dependencies, default its proofs to `@integration` unless the specific proof can be unit-tested in isolation.
