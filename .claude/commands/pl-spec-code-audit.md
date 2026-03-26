**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

Call the `EnterPlanMode` tool immediately before doing anything else. Do not read any files or run any commands until plan mode is active.

---

## Purpose

Bidirectional spec-code audit with role-aware remediation. Two modes: **triage** (default, fast, in-agent) and **deep** (parallel subagent waves with scenario-by-scenario comparison and transitive anchor constraint validation). Both modes produce a prioritized gap table, then remediate gaps within your role's authority and escalate cross-role gaps through established mechanisms.

**Role behavior:**
- **PM mode:** Fixes spec-side gaps directly (edit feature files). Escalates code-side gaps to Engineer mode by adding actionable notes in companion files (`features/<name>.impl.md`).
- **Engineer mode:** Fixes code-side gaps directly (edit code/tests). Escalates spec-side gaps to PM mode by recording `[DISCOVERY]` or `[SPEC_PROPOSAL]` entries in companion files.

---

## Argument Parsing

Parse `$ARGUMENTS`:
- **No argument or empty:** Mode is `triage`.
- **`--deep`:** Mode is `deep`.
- **Anything else:** Abort with: `Error: Unknown argument '<arg>'. Valid: --deep`

---

## Path Resolution

> See `instructions/references/path_resolution.md`. Produces `TOOLS_ROOT`.
> **Companion files:** See `instructions/references/active_deviations.md` for deviation format and PM review protocol.

---

## Scope Confirmation

Before loading project state (Phase 0), auto-detect code directories:

1. Scan the project root for common code directory patterns: `src/`, `lib/`, `app/`, `tools/`, `dev/`, `scripts/`, `.claude/commands/`, `tests/`.
2. Check `.purlin/config.json` for an optional `audit_code_paths` array. If present, use it as the default scope instead of auto-detection.
3. Present the detected scope to the user and ask for confirmation:
   - Code directories found (only those that exist on disk)
   - File patterns per directory (e.g., `*.py`, `*.sh`, `*.md` for `.claude/commands/`)
   - Feature spec count from the dependency graph
4. Default is confirm (proceed). If the user requests adjustments, accept additions/removals, re-display, and re-confirm.
5. The confirmed scope is session-scoped (not persisted). For persistent scope, use `audit_code_paths` in `.purlin/config.json`.
6. The confirmed scope constrains code discovery in all subsequent phases (triage light scan, deep mode source discovery, Phase 0.5 code inventory).

---

## Phase 0: Triage (Parent Agent -- Both Modes)

Parent loads project state, builds the transitive prerequisite constraint map, and constructs the dispatch plan. Reads only metadata and anchor node constraint sections -- never feature scenarios or source code in this phase.

### Step 0.1 -- Load Project State

1. Run `${TOOLS_ROOT}/cdd/scan.sh --only features,deps` and read the JSON output.
2. Read `.purlin/cache/dependency_graph.json` -- note all prerequisite relationships and root anchor nodes.
3. For each feature, read the feature spec directly to check section completeness and scenario count.

### Step 0.2 -- Build Transitive Prerequisite Map

For each feature in the dependency graph, walk all `> Prerequisite:` chains recursively (BFS) to collect the full set of ancestor anchor nodes. Output: `{feature_name: [list of all ancestor anchor filenames]}`.

### Step 0.3 -- Collect Anchor Constraints

For each unique anchor node in the transitive map, read the anchor file and extract:
- All `FORBIDDEN:` patterns (line + pattern text)
- All numbered invariant statements (from `## Invariants` or numbered subsections under requirements)
- All named constraints (conditional rules from subsections)

Output: `{anchor_name: {forbidden: [...], invariants: [...], constraints: [...]}}`

### Step 0.4 -- Check Resume State

Check for existing `.purlin/cache/audit_state.json`. If found, report resume status and skip to the next incomplete step (deep mode: resume from the next incomplete wave; triage mode: resume from Phase 2 synthesis if triage scan was completed).

---

## Mode-Dependent Dispatch

### If mode is `triage`:

**Lightweight code inventory** (before feature-level scanning): Run a lightweight code inventory using the confirmed scope. Enumerate code files (Step 0.5.1) and build an ownership map using only heuristics H1, H2, H4, and H5 (no import tracing -- that requires reading source). Orphan findings are reported as a single summary line in the gap table (total orphan count and top-3 by severity), not per-file entries. Full per-file code inventory analysis requires `--deep`.

Process ALL features in-agent (no subagents). For each feature:

1. Read the feature file -- check spec completeness across all 12 gap dimensions (see Gap Dimensions Table below).
2. Read companion file (`features/<name>.impl.md`) if it exists -- check builder decisions, notes depth.
3. Read the feature spec directly to check section completeness and scenario count, and check `.purlin/cache/scan.json` for feature status.
4. **Anchor constraint surface check**: For each ancestor anchor in the transitive map, verify the feature's scenarios reference or account for the anchor's invariants. Flag invariants with zero scenario coverage.
5. **Light code scan** (if implementation exists): Read up to 3 primary source files (discovered via test imports or companion file Tool Location within the confirmed scope). Grep for FORBIDDEN patterns from all transitive ancestors. Flag violations.
6. Skip scenario-by-scenario deep comparison.

After processing all features individually, perform a **cross-feature requirement hygiene pass** (dimension 11):
- **Duplicate detection:** Compare scenario titles and Given/When/Then signatures across all features. Flag pairs where two scenarios in different features target the same endpoint, function, or UI element with the same preconditions and assertions.
- **Conflict detection:** Compare requirements sections and scenario assertions across features that share a prerequisite anchor or target the same component. Flag contradictory assertions (e.g., different expected status codes, incompatible state transitions, contradictory anchor invariants).
- **Unused detection:** Cross-reference the dependency graph to find features with no implementation (no `tests/<name>/` directory, no source files discovered), no test coverage, and not listed as a prerequisite by any other feature. Flag these as orphaned specs.

After the cross-feature pass, save results to `.purlin/cache/audit_state.json` and proceed directly to Phase 2 (Synthesis).

### If mode is `deep`:

#### Step D.1 -- Classify Features

Classify features into three processing tracks:
- **Spec-only track**: Anchor nodes (`arch_*`, `design_*`, `policy_*`) + features with zero automated scenarios.
- **Code-comparison track**: All features with automated scenarios.
- **Orphan scan track**: All "orphaned executable" and "orphaned skill file" entries from Phase 0.5 (see below). Grouped into batches of up to 15 orphaned files per batch.

#### Step D.2 -- Batch Features

Batch features using first-fit-decreasing bin packing:
- Target: 50-75 scenarios per code-comparison batch, max 4-5 features per batch.
- Solo batch for any feature with 50+ scenarios.
- All spec-only features go in a single batch.
- Orphan scan batches: group up to 15 orphaned files per batch.

#### Step D.3 -- Assign Waves

Assign batches to waves of up to 5 concurrent subagents. Write the dispatch manifest to the plan file (wave/agent/feature/scenario-count table). Include the transitive prerequisite map and collected anchor constraints in each subagent's prompt payload so subagents don't need to re-derive them.

**Aggressive parallelism mandate:** All 5 subagent slots per wave MUST be filled whenever batches remain. Spec-only, code-comparison, and orphan scan batches are mixed freely within the same wave -- never sequentially by track. If fewer than 5 batches exist in a wave, remaining slots MUST be used for orphan scan batches or rescue batches from prior waves. The goal is to minimize total wall-clock time by never leaving a subagent slot idle when work remains.

Then proceed to Phase 0.5 (Code Inventory), then Phase 1.

---

## Phase 0.5: Code Inventory (Deep Mode Full / Triage Lightweight)

Phase 0.5 runs in the parent agent after Phase 0 and before dispatching subagents (Phase 1). It builds a complete code-to-feature ownership map and identifies orphaned code.

### Step 0.5.1 -- Enumerate Code Files

- Use the confirmed scope from Scope Confirmation (already established before Phase 0).
- Glob all files matching code extensions: `.py`, `.sh`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.rb`.
- For `.claude/commands/`: include `.md` files (skill files are executable behavior).
- Apply exclusions: `__pycache__/`, `node_modules/`, `vendor/`, `dist/`, `build/`, `.purlin/cache/`, `.purlin/runtime/`, binary files (`.pyc`, `.o`, `.so`), and files with `# DO NOT EDIT` or `// DO NOT EDIT` headers (auto-generated).
- Output: `code_inventory[]` -- list of `{path, extension, size_bytes}`.

### Step 0.5.2 -- Build Ownership Map

For each code file, attempt to find an owning feature using a ranked heuristic chain (first match wins):

| Priority | Heuristic | Confidence | Method |
|----------|-----------|------------|--------|
| H1 | Companion explicit reference | HIGH | Companion `.impl.md` contains `Tool Location:` or `### Source Mapping` referencing the file path |
| H2 | Spec explicit reference | HIGH | Feature spec `.md` mentions the file path in requirements or overview |
| H3 | Test import trace | HIGH | A test file in `tests/<feature>/` imports or executes the code file. **Deep mode only** -- requires reading source files. |
| H4 | Command-to-feature naming | HIGH | `.claude/commands/pl-<name>.md` maps to `features/pl_<name>.md` (dash-to-underscore convention) |
| H5 | Directory convention | MEDIUM | Feature name prefix maps to tool subdirectory (e.g., `pl_help` -> `tools/help/`) |
| H6 | Name similarity | LOW | File stem substring-matches a feature name. **Deep mode only.** |

- A file MAY have multiple owners (legitimate for shared modules).
- Triage mode uses only H1, H2, H4, H5 (no source reading). Deep mode uses all six heuristics.
- Output: `ownership_map{}` -- `{file_path: {owners: [feature_names], heuristic: "<H1-H6>", confidence: "HIGH|MEDIUM|LOW"}}`.

### Step 0.5.3 -- Classify Unowned Files (Deep Mode Only)

Files with zero owners are classified into sub-categories:

| Classification | Criteria | Severity |
|---|---|---|
| **Orphaned executable** | Defines functions or entry points, no owner | MEDIUM |
| **Orphaned skill file** | `.claude/commands/pl-*.md` with no `features/pl_*.md` | HIGH |
| **Shared infrastructure** | Imported by 3+ features' test files but no dedicated spec | LOW |
| **Dead code candidate** | Zero imports from any file AND zero owners | LOW |
| **Infrastructure file** | Matches known patterns: `__init__.py`, `conftest.py`, `*_utils.*`, `setup.py`, `setup.cfg`, `pyproject.toml`, `Makefile`, `Dockerfile` | Excluded |

- Infrastructure files are auto-excluded from gap reporting. They are included in the inventory count but never generate gap entries.
- Output: `orphaned_files[]` -- `{path, classification, import_count, nearest_feature_suggestion}`.

### False Positive Mitigation

Three mechanisms prevent noise in code ownership findings:

1. **Infrastructure file exclusion** -- Known patterns (`__init__.py`, `conftest.py`, `*_utils.*`, build system files) are auto-excluded from gap reporting.
2. **Import fan-in threshold** -- Files imported by 3+ features are classified as "shared infrastructure" (LOW severity) rather than orphaned.
3. **Confidence-weighted ownership** -- H5/H6 (MEDIUM/LOW confidence) matches suppress the gap but are noted as "weak ownership" in the audit table for human review.

---

## Phase 1: Parallel Deep Scan (Deep Mode Only -- Subagent Waves)

Launch subagents wave by wave. All subagents in a wave are launched in a single message via multiple Task tool calls (concurrent execution).

**Subagent type:** `Explore` (read-only: Glob, Grep, Read, Bash)

### Code-Comparison Subagent Protocol

Each subagent receives the following in its prompt, plus the transitive constraint payload:

For each assigned feature:
1. **Read spec**: `features/<name>.md` -- extract all `#### Scenario:` entries with Given/When/Then.
2. **Read companion**: `features/<name>.impl.md` -- note Tool Location, source mappings, decision tags.
3. **Read scan data**: `.purlin/cache/scan.json` features data -- gate statuses, traceability, action items.
4. **Discover source files**: Extract import paths from test files in `tests/<name>/`, fall back to Tool Location in companion file, fall back to directory convention mapping from feature label.
5. **Read source**: Up to 5 primary implementation files per feature.
6. **Scenario-by-scenario comparison**: For each automated scenario:
   - Find the corresponding test function.
   - Trace to the code path it exercises.
   - Verify the Given/When/Then assertions match actual code logic.
   - Flag: contradictions, missing logic, extra behavior, hardcoded values.
7. **Transitive anchor constraint validation**: For each ancestor anchor node (from the payload):
   - **FORBIDDEN scan**: Grep all source files for each FORBIDDEN pattern. Report violations with file:line.
   - **Invariant coverage**: For each invariant statement, determine if any scenario or code path addresses it. Flag invariants with zero coverage in both scenarios and code.
   - **Constraint compliance**: For each named constraint, check if the code's behavior aligns. Flag contradictions.
8. **Undocumented behavior scan**: Error handlers, config branches, edge cases in code with no scenario coverage.
9. **Spec completeness**: All 12 gap dimensions (see Gap Dimensions Table).

### Spec-Only Subagent Protocol

Simplified scan:
- Read feature file and companion.
- Check spec completeness, policy anchoring, builder decisions, notes depth.
- For anchor nodes: verify Purpose and Invariants sections are substantive.
- **Cross-anchor consistency**: If this anchor is a prerequisite of other anchors, check for contradictions between their invariant sets.
- Skip code comparison entirely.

### Orphan Scan Subagent Protocol

For each assigned orphaned file:
1. Read the file and extract public functions, classes, and entry points.
2. Assess complexity (line count, function count, import fan-out).
3. Identify the nearest feature by directory proximity and name similarity.
4. Return structured output using `=== ORPHAN: <path> ===` ... `=== END ORPHAN ===` format with classification (orphaned executable, orphaned skill, dead code candidate), public API summary, import fan-in count, and nearest feature suggestion.

### Structured Output Format

Each subagent returns (code-comparison and spec-only):
```
=== FEATURE: <name> ===
Mode: deep | Scenarios scanned: N | Source files read: file1, file2
Transitive anchors checked: anchor1, anchor2, ...
GAPS:
- [SEVERITY] [DIMENSION] [OWNER] description
  Evidence: specific file:line or scenario reference
  Anchor source: <anchor_name> invariant N (if applicable)
  Suggested fix: concrete action
NO_GAPS (if clean)
=== END FEATURE ===
```

Orphan scan subagents return:
```
=== ORPHAN: <path> ===
Classification: orphaned executable | orphaned skill | dead code candidate
Public API: function1(), function2(arg)
Line count: N | Function count: N | Import fan-in: N
Nearest feature: <feature_name> (by directory proximity / name similarity)
=== END ORPHAN ===
```

### Wave Execution

- After each wave completes, save accumulated results to `.purlin/cache/audit_state.json`.
- If auto-compaction occurs, save state and instruct user to resume with `/pl-spec-code-audit --deep`.
- If a subagent returns incomplete results (missing features), create a rescue batch for the next wave.
- If a subagent fails entirely, re-queue the batch.

---

## Phase 2: Synthesis (Parent Agent -- Both Modes)

### Step 2.1 -- Parse and Classify Gaps

1. Parse all gap findings (from in-agent triage scan or subagent structured output blocks).
2. Deduplicate gaps (same implementation file flagged by overlapping feature batches or transitive anchors).
3. **Cross-feature requirement hygiene pass** (deep mode only -- triage mode already performed this in Phase 0): Compare all per-feature gap findings and scenario data to detect duplicate requirements, conflicting requirements, and unused/orphaned specs (see dimension 11 in the Gap Dimensions Table). Add any cross-feature gaps to the findings list.
4. Classify each gap:

**Severity:**

| Severity | Criteria |
|---|---|
| CRITICAL | INFEASIBLE escalation active; spec-blocking circular dependency; open BUG with no resolution path |
| HIGH | Spec Gate FAIL; open BUG or SPEC_DISPUTE entry; unacknowledged `[DEVIATION]` or `[DISCOVERY]`; code behavior directly contradicts a scenario assertion; FORBIDDEN pattern violation from any transitive ancestor; conflicting requirements across features (contradictory assertions on same endpoint/component); orphaned skill file (`.claude/commands/pl-*.md` with no corresponding feature spec) |
| MEDIUM | Missing prerequisite link; traceability gap (coverage < 1.0); dependency currency failure (prerequisite updated, dependent not re-validated); spec-reality misalignment; significant undocumented code path; invariant with zero coverage in scenarios and code; duplicate requirements across features (identical scenarios targeting same endpoint/function); orphaned executable code with significant behavior (entry points, state mutation, I/O operations) |
| LOW | Stub-only companion file on a complex feature; vague scenario wording; missing companion file for a large feature; cosmetic spec inconsistencies; minor undocumented behavior; unused/orphaned feature spec with no implementation, no tests, and no dependents; dead code candidate (zero imports, zero owners); shared infrastructure code (3+ importers, no dedicated spec) |

**Owner:** Assign based on what needs to change, not who is running the command:
- `ARCHITECT` -- the spec needs to be updated (to match reality, clarify ambiguity, add missing anchors, revise scenarios)
- `BUILDER` -- code or tests need to be updated (to match spec, add missing test coverage, resolve INFEASIBLE)

**Action:** Based on who is running the command and the Owner assignment:
- If Owner matches your role -> `FIX` (you will remediate directly)
- If Owner is the other role -> `ESCALATE` (you will record it for the other role via companion files)

### Step 2.2 -- Build the Audit Table

Sort all findings: CRITICAL -> HIGH -> MEDIUM -> LOW, then alphabetically by feature name within each group. Number rows sequentially starting at 1.

Write the following to the plan file:

---

### Spec-Code Audit -- `<timestamp>`

**Role:** PM | Engineer
**Mode:** triage | deep
**Total features scanned:** N
**Transitive anchor constraints checked:** N invariants across M anchors
**Gaps found:** N (CRITICAL: N . HIGH: N . MEDIUM: N . LOW: N)
**Will fix:** N | **Will escalate:** N

| # | Feature | Severity | Dimension | Gap Description | Evidence | Anchor Source | Action | Planned Remediation |
|---|---|---|---|---|---|---|---|---|
| 1 | feature_name | HIGH | Anchor invariant | Code violates invariant 2.3 from design_visual_standards | src/foo.py:42 | design_visual_standards invariant 2.3 | FIX | ... |
| 2 | feature_name | MEDIUM | Code divergence | Scenario says X, code does Y | tests/foo/test.py:15 vs tools/foo.py:88 | — | ESCALATE | ... |

---

**Remediation Plan:**

For each FIX item, describe the specific edit scoped to the acting role's artifacts:
- **PM FIX edits** target feature specs (`features/*.md`) and anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) only -- which section to add/revise, what scenario language to change, which prerequisite link to add.
- **Engineer FIX edits** target source code and tests only -- which implementation file to modify, what logic to correct, which test to add or update.
For each ESCALATE item, describe the companion file entry that will be written.

If no gaps are found, write: "No spec-code gaps detected across all N features." and call `ExitPlanMode`.

### Step 2.3 -- Exit Plan Mode

After writing the audit table and remediation plan, call `ExitPlanMode`. Wait for user approval before proceeding to Phase 3.

---

## Gap Dimensions Table

| Dimension | What to look for |
|---|---|
| **Spec completeness** | Missing required sections; vague scenarios; undefined terms; anchor nodes missing Purpose or Invariants |
| **Policy anchoring** | Missing `> Prerequisite:` links to applicable anchor nodes |
| **Traceability** | Automated scenarios with no matching test functions (`coverage < 1.0`) |
| **Engineer decisions** | Unacknowledged `[DEVIATION]` or `[DISCOVERY]` tags in companion file |
| **User testing** | OPEN or SPEC_UPDATED discovery entries |
| **Dependency currency** | Prerequisite anchor node has lifecycle status TODO or was recently modified |
| **Spec-reality alignment** | Implementation Notes document decisions that contradict or extend scenarios without spec updates |
| **Notes depth** | Complex feature (5+ scenarios or visual spec) with stub-only or absent companion file |
| **Code divergence** | Scenario assertions not reflected in code; significant code paths with no scenario coverage; hardcoded values the spec says should be configurable |
| **Anchor invariant drift** | Code violates invariants or constraints from transitive ancestor anchors (not just direct prerequisites). Includes FORBIDDEN pattern violations. |
| **Requirement hygiene** | Duplicate scenarios across features targeting the same endpoint/function with identical assertions; conflicting assertions across features sharing a prerequisite anchor or targeting the same component; orphaned specs with no implementation, no test coverage, and not listed as a prerequisite by any other feature |
| **Code ownership** | Orphaned code files in audit scope not referenced by any feature spec, companion file, or test import chain; orphaned skill files (`.claude/commands/pl-*.md` with no corresponding `features/pl_*.md`); shared infrastructure (3+ importers, no dedicated spec); dead code candidates (zero imports, zero owners). Deep mode provides per-file analysis; triage mode reports summary counts only. Symmetric complement of Requirement hygiene's "unused spec" detection: Requirement hygiene finds specs without code; Code ownership finds code without specs. |

---

## Cross-Session Resume Protocol

**State artifact:** `.purlin/cache/audit_state.json`

Saved after each wave (deep mode) or after triage scan completes with:
- `mode`: "triage" or "deep"
- `role`: acting role
- `timestamp`: ISO 8601
- `transitive_map`: the computed prerequisite map (avoid recomputation on resume)
- `anchor_constraints`: collected constraint payload
- `dispatch_manifest`: per-wave completion status (deep mode only)
- `accumulated_gaps`: gap findings so far
- `scan_failures`: features that failed and need retry
- `code_inventory`: tracks `total_files`, `owned_files`, `orphaned_files` (count), and `inventory_complete` (boolean)
- `ownership_map_complete`: boolean (top-level field)

On re-invocation: if state file exists, report resume status, skip Phase 0, resume from next incomplete step. If `inventory_complete` is true, Phase 0.5 is skipped entirely. Deleted after Phase 3 completes.

---

## Phase 3: Remediation (After User Approval)

After the user approves the plan, execute the remediation. Process FIX items first, then ESCALATE items.

### If Running as PM

**FIX (spec-side gaps you own):**
1. Edit the feature file directly -- add missing sections, refine vague scenarios, add prerequisite links, update stale spec content.
2. For acknowledged builder decisions (`[DEVIATION]`, `[DISCOVERY]`): update the spec to reflect the decision, then mark the tag as acknowledged in the companion file.
3. Commit each logical group of spec fixes.

**ESCALATE (code-side gaps for Engineer mode):**
1. Open (or create) the companion file `features/<feature_name>.impl.md`.
2. Add a clearly tagged entry under the implementation notes:

```
### Audit Finding -- <date>
[DISCOVERY] <description of the code gap>
**Source:** /pl-spec-code-audit
**Severity:** <severity>
**Details:** <what the code does vs what the spec expects, or what code path lacks scenario coverage>
**Suggested fix:** <concrete suggestion for Engineer mode>
```

3. Commit all escalation entries together.
4. Run `${TOOLS_ROOT}/cdd/scan.sh` after committing to refresh project state (the scan will surface these as Engineer action items).

### If Running as Engineer

**FIX (code-side gaps you own):**
1. Fix code to match scenario assertions -- correct contradictions, add missing error handling, update hardcoded values.
2. Add or update automated tests to close traceability gaps.
3. Update the companion file's implementation notes to document what changed and why.
4. Commit each logical group of code fixes.

**ESCALATE (spec-side gaps for PM mode):**
1. Open (or create) the companion file `features/<feature_name>.impl.md`.
2. Add a `[DISCOVERY]` or `[SPEC_PROPOSAL]` entry:

```
### Audit Finding -- <date>
[DISCOVERY] <description of the spec gap>
**Source:** /pl-spec-code-audit
**Severity:** <severity>
**Details:** <what is missing or inconsistent in the spec>
**Suggested spec change:** <concrete proposal for PM mode>
```

3. Commit all escalation entries together.
4. The scan will surface these as PM action items at the next PM session.

### Dimension 12 (Code Ownership) Remediation

- **PM FIX:** Create a new feature spec (via `/pl-spec`) for orphaned code that represents significant unspecified behavior, or add the file to an existing feature's companion Source Mapping section if it belongs to an existing feature.
- **PM ESCALATE to Engineer:** If code appears dead (zero imports, zero owners, no entry points), record `[DISCOVERY]` in the nearest feature's companion file suggesting removal.
- **Engineer ESCALATE to PM:** If Engineer mode discovers code that has no spec, record `[SPEC_PROPOSAL]` in the companion file requesting spec creation for the orphaned code.

### Post-Remediation

After all items are processed:
1. Run `${TOOLS_ROOT}/cdd/scan.sh` to refresh project state.
2. Delete `.purlin/cache/audit_state.json` if it exists.
3. Summarize what was done: N items fixed, N items escalated, any items deferred with rationale.
