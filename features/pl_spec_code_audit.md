# Feature: Spec-Code Audit

> Label: "/pl-spec-code-audit Spec-Code Audit"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/impl_notes_companion.md

[TODO]

## 1. Overview

The `/pl-spec-code-audit` command performs a bidirectional audit between feature specifications and implementation code, detecting gaps in both directions: spec-side deficiencies (missing sections, broken anchors, stale notes) and code-side deviations (undocumented behaviors, scenario-code contradictions, anchor invariant violations). In `--deep` mode, the audit also performs a **reverse code-to-spec scan** (Phase 0.5): it enumerates all code files in the project, builds a code-to-feature ownership map, and surfaces orphaned code with no corresponding specification -- closing the blind spot where code exists outside any feature's purview. It operates in two modes: **triage** (default, fast, runs entirely in-agent) and **deep** (parallel subagent waves with scenario-by-scenario comparison, transitive anchor constraint validation, and reverse code inventory). Both modes produce a prioritized gap table with role-scoped remediation, then execute fixes within the acting role's authority and escalate cross-role gaps through companion files.

---

## 2. Requirements

### 2.1 Role Gating

- The command is shared between Architect and Builder roles.
- Non-Architect/Builder agents (QA, PM) MUST receive: "This command is for the Architect or Builder. Ask the appropriate agent to run /pl-spec-code-audit."

### 2.2 Plan Mode Entry

- The command MUST call `EnterPlanMode` immediately upon invocation, before reading any files or running any commands.

### 2.3 Argument Parsing

- The command MUST accept an optional `$ARGUMENTS` parameter.
- No argument or empty: mode is `triage` (default).
- `--deep`: mode is `deep`.
- Any other argument MUST abort with: `Error: Unknown argument '<arg>'. Valid: --deep`

### 2.4 Path Resolution

- The command MUST read `.purlin/config.json` and extract `tools_root` (default: `"tools"`).
- Project root MUST be resolved via `PURLIN_PROJECT_ROOT` env var if set and `.purlin/` exists there; otherwise by climbing from the current working directory until `.purlin/` is found.
- All tool invocations MUST use `${TOOLS_ROOT}/...` (e.g., `${TOOLS_ROOT}/cdd/status.sh`). No hardcoded `tools/` paths.
- Path resolution MUST work in both standalone projects and projects consuming Purlin as a submodule.

### 2.5 Scope Confirmation

- Before loading project state (Phase 0), the command MUST auto-detect code directories by scanning the project root for common patterns: `src/`, `lib/`, `app/`, `tools/`, `dev/`, `scripts/`, `.claude/commands/`, `tests/`.
- The command MUST check `.purlin/config.json` for an optional `audit_code_paths` array. If present, use it as the default scope instead of auto-detection.
- The command MUST present the detected scope to the user and ask for confirmation:
  - Code directories found (only those that exist on disk)
  - File patterns per directory (e.g., `*.py`, `*.sh`, `*.md` for `.claude/commands/`)
  - Feature spec count from the dependency graph
- Default is confirm (proceed). If the user requests adjustments, accept additions/removals, re-display, and re-confirm.
- The confirmed scope is session-scoped (not persisted). For persistent scope, use `audit_code_paths` in `.purlin/config.json`.
- The confirmed scope MUST constrain code discovery in all subsequent phases (triage light scan, deep mode source discovery).

### 2.6 Phase 0 -- Project State and Constraint Loading

- The command MUST run `${TOOLS_ROOT}/cdd/status.sh` and read `CRITIC_REPORT.md` and `.purlin/cache/dependency_graph.json`.
- For each feature, the command MUST read `tests/<name>/critic.json` to extract scenario count from traceability detail.
- The command MUST build a transitive prerequisite map by walking all `> Prerequisite:` chains recursively (BFS) for every feature in the dependency graph. Output: `{feature_name: [list of all ancestor anchor filenames]}`.
- The command MUST collect anchor constraints from each unique anchor node in the transitive map: all `FORBIDDEN:` patterns (line + pattern text), numbered invariant statements, and named constraints. Output: `{anchor_name: {forbidden: [...], invariants: [...], constraints: [...]}}`.
- Phase 0 reads only metadata and anchor node constraint sections -- never feature scenarios or source code.

### 2.7 Cross-Session Resume

- After Phase 0 metadata loads (Steps 0.1-0.3), the command MUST check for `.purlin/cache/audit_state.json` at Step 0.4.
- If found, the command MUST report resume status, load transitive map and anchor constraints from the state file (skipping recomputation if already present), and skip to the next incomplete step.
- The state file MUST track: `mode`, `role`, `timestamp`, `transitive_map`, `anchor_constraints`, `dispatch_manifest` (deep mode), `accumulated_gaps`, `scan_failures`, `code_inventory` (deep mode), and `ownership_map_complete` (boolean).
- The `code_inventory` field MUST track: `total_files`, `owned_files`, `orphaned_files` (count), and `inventory_complete` (boolean).
- The `ownership_map_complete` field (boolean) MUST be persisted at the top level of the state file.
- On resume in deep mode, completed waves are skipped and the next incomplete wave resumes. If `inventory_complete` is true, Phase 0.5 is skipped entirely.
- On resume in triage mode with scan complete, the command skips to Phase 2 synthesis.
- The state file MUST be deleted after Phase 3 (Remediation) completes.

### 2.8 Triage Mode (Default)

- Triage mode MUST process all features in-agent without launching subagents.
- Before feature-level scanning, triage mode MUST run a lightweight code inventory (see Section 2.17, Step 0.5.1 and Step 0.5.2) using only heuristics H1, H2, H4, and H5 (no import tracing -- that requires reading source). Orphan findings are reported as a single summary line in the gap table (total orphan count and top-3 by severity), not per-file entries. Full per-file code inventory analysis requires `--deep`.
- For each feature, the command MUST:
  - Read the feature file and check spec completeness across all 12 gap dimensions (see Section 2.13).
  - Read companion file if it exists and check builder decisions and notes depth.
  - Read `tests/<name>/critic.json` for gate status and traceability.
  - Perform an anchor constraint surface check: for each ancestor anchor in the transitive map, verify the feature's scenarios reference or account for the anchor's invariants. Flag invariants with zero scenario coverage.
  - Perform a light code scan (if implementation exists): read up to 3 primary source files (discovered via test imports or companion file Tool Location) and grep for FORBIDDEN patterns from all transitive ancestors. Flag violations.
- Triage mode MUST skip scenario-by-scenario deep comparison.
- After processing all features individually, the command MUST perform a cross-feature requirement hygiene pass (dimension 11):
  - **Duplicate detection:** Compare scenario titles and Given/When/Then signatures across all features. Flag pairs where two scenarios in different features target the same endpoint, function, or UI element with the same preconditions and assertions.
  - **Conflict detection:** Compare requirements sections and scenario assertions across features that share a prerequisite anchor or target the same component. Flag contradictory assertions (e.g., different expected status codes, incompatible state transitions, contradictory anchor invariants).
  - **Unused detection:** Cross-reference the dependency graph to find features with no implementation (no `tests/<name>/` directory, no source files discovered), no test coverage, and not listed as a prerequisite by any other feature. Flag these as orphaned specs.
- After the cross-feature pass, results MUST be saved to `.purlin/cache/audit_state.json`.

### 2.9 Deep Mode

- Deep mode MUST classify features into three processing tracks:
  - **Spec-only track:** Anchor nodes (`arch_*`, `design_*`, `policy_*`) and features with zero automated scenarios.
  - **Code-comparison track:** All features with automated scenarios.
  - **Orphan scan track:** All "orphaned executable" and "orphaned skill file" entries from Phase 0.5 (Section 2.17). These are grouped into one or more orphan scan batches.
- Deep mode MUST batch features using first-fit-decreasing bin packing: 50-75 scenarios per code-comparison batch, max 4-5 features per batch. Features with 50+ scenarios get a solo batch (solo takes precedence over batch grouping when a feature meets the threshold). All spec-only features go in a single batch.
- Orphan scan batches MUST group up to 15 orphaned files per batch.
- Batches MUST be assigned to waves of up to 5 concurrent subagents.
- **Aggressive parallelism mandate:** The command MUST maximize subagent concurrency at every opportunity. All 5 subagent slots per wave MUST be filled whenever batches remain. Spec-only, code-comparison, and orphan scan batches MUST be mixed freely within the same wave -- never sequentially by track. If fewer than 5 batches exist in a wave, remaining slots MUST be used for orphan scan batches or rescue batches from prior waves. The goal is to minimize total wall-clock time by never leaving a subagent slot idle when work remains.
- A dispatch manifest MUST be written to the plan file (wave/agent/feature/scenario-count table).
- The transitive prerequisite map and collected anchor constraints MUST be included in each subagent's prompt payload so subagents do not need to re-derive them.

### 2.10 Phase 1 -- Parallel Deep Scan (Deep Mode Only)

- Subagents MUST be launched wave by wave. All subagents in a wave MUST be launched in a single message via multiple Agent tool calls (concurrent execution). The command MUST NOT wait for one subagent to complete before launching others in the same wave.
- Subagent type MUST be `Explore` (read-only).
- **Code-comparison subagents** MUST, for each assigned feature:
  - Read the feature spec and extract all `#### Scenario:` entries with Given/When/Then.
  - Read the companion file and note Tool Location, source mappings, and decision tags.
  - Read `tests/<name>/critic.json` for gate statuses and traceability.
  - Discover source files via test imports, companion file Tool Location, or directory convention mapping.
  - Read up to 5 primary implementation files per feature.
  - Perform scenario-by-scenario comparison: find the corresponding test function, trace to the code path, verify assertions match actual code logic, and flag contradictions, missing logic, extra behavior, or hardcoded values.
  - Perform transitive anchor constraint validation: grep all source files for each FORBIDDEN pattern from ancestor anchors, check invariant coverage, and check constraint compliance.
  - Scan for undocumented behavior (error handlers, config branches, edge cases with no scenario coverage).
  - Check spec completeness across all 12 gap dimensions.
- **Spec-only subagents** MUST:
  - Read the feature file and companion.
  - Check spec completeness, policy anchoring, builder decisions, and notes depth.
  - For anchor nodes: verify Purpose and Invariants sections are substantive.
  - Check cross-anchor consistency if the anchor is a prerequisite of other anchors.
  - Skip code comparison entirely.
- **Orphan scan subagents** MUST, for each assigned orphaned file:
  - Read the file and extract public functions, classes, and entry points.
  - Assess complexity (line count, function count, import fan-out).
  - Identify the nearest feature by directory proximity and name similarity.
  - Return structured output using `=== ORPHAN: <path> ===` ... `=== END ORPHAN ===` format with classification (orphaned executable, orphaned skill, dead code candidate), public API summary, import fan-in count, and nearest feature suggestion.
- Each subagent MUST return structured output in the format: `=== FEATURE: <name> ===` ... `=== END FEATURE ===` (or `=== ORPHAN: <path> ===` ... `=== END ORPHAN ===` for orphan batches) with gaps listed as `[SEVERITY] [DIMENSION] [OWNER]` entries including Evidence, Anchor source, and Suggested fix fields.
- After each wave completes, accumulated results MUST be saved to `.purlin/cache/audit_state.json`.
- If auto-compaction occurs, the command MUST save state and instruct the user to resume with `/pl-spec-code-audit --deep`.
- If a subagent returns incomplete results, a rescue batch MUST be created for the next wave.
- If a subagent fails entirely, the batch MUST be re-queued.

### 2.11 Phase 2 -- Synthesis

- The command MUST parse all gap findings from in-agent triage scan or subagent structured output.
- In deep mode, the command MUST perform the cross-feature requirement hygiene pass (dimension 11) at this stage, since subagents operate on individual feature batches and cannot detect cross-feature issues. The same duplicate, conflict, and unused checks described in Section 2.8 apply.
- The command MUST deduplicate gaps where the same implementation file is flagged by overlapping feature batches or transitive anchors.
- Each gap MUST be classified by severity (CRITICAL, HIGH, MEDIUM, LOW), owner (ARCHITECT or BUILDER), and action (FIX if owner matches acting role, ESCALATE otherwise). See Section 2.14 for severity criteria.
- The command MUST build an audit table sorted CRITICAL to LOW, then alphabetically by feature name. Rows are numbered sequentially.
- The audit table MUST include columns: #, Feature, Severity, Dimension, Gap Description, Evidence, Anchor Source, Action, Planned Remediation.
- The table header MUST include: Role, Mode, Total features scanned, Transitive anchor constraints checked (N invariants across M anchors), Gaps found (with per-severity counts), Will fix count, and Will escalate count.

### 2.12 Role-Scoped Remediation Plan

- The remediation plan MUST contain role-scoped FIX descriptions:
  - **Architect FIX edits** target feature specs (`features/*.md`) and anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) only -- which section to add/revise, what scenario language to change, which prerequisite link to add.
  - **Builder FIX edits** target source code and tests only -- which implementation file to modify, what logic to correct, which test to add or update.
- For each ESCALATE item, the plan MUST describe the companion file entry that will be written.
- If no gaps are found, the command MUST output "No spec-code gaps detected across all N features." and call `ExitPlanMode`.
- After writing the audit table and remediation plan, the command MUST call `ExitPlanMode` and wait for user approval.

### 2.13 Gap Dimensions

The command MUST assess each feature against these 12 dimensions (dimensions 1-10 are per-feature; dimensions 11-12 are cross-feature/project-wide):

| # | Dimension | Description |
|---|---|---|
| 1 | Spec completeness | Missing required sections; vague scenarios; undefined terms; anchor nodes missing Purpose or Invariants |
| 2 | Policy anchoring | Missing `> Prerequisite:` links to applicable anchor nodes |
| 3 | Traceability | Automated scenarios with no matching test functions (`coverage < 1.0`) |
| 4 | Builder decisions | Unacknowledged `[DEVIATION]` or `[DISCOVERY]` tags in companion file |
| 5 | User testing | OPEN or SPEC_UPDATED discovery entries |
| 6 | Dependency currency | Prerequisite anchor node has lifecycle status TODO or was recently modified |
| 7 | Spec-reality alignment | Implementation Notes document decisions that contradict or extend scenarios without spec updates |
| 8 | Notes depth | Complex feature (5+ scenarios or visual spec) with stub-only or absent companion file |
| 9 | Code divergence | Scenario assertions not reflected in code; significant code paths with no scenario coverage; hardcoded values the spec says should be configurable |
| 10 | Anchor invariant drift | Code violates invariants or constraints from transitive ancestor anchors (not just direct prerequisites). Includes FORBIDDEN pattern violations. |
| 11 | Requirement hygiene | Cross-feature analysis: **Duplicate** -- two or more features define scenarios or requirements that specify the same behavior for the same component (identical or near-identical Given/When/Then targeting the same endpoint, function, or UI element). **Conflicting** -- two features specify contradictory behavior for the same component (e.g., feature A says endpoint returns 200, feature B says it returns 404; or two anchors define incompatible invariants for the same domain). **Unused** -- a feature or scenario that has no implementation code, no test, and is not a prerequisite of any other feature (orphaned spec with no path to implementation). |
| 12 | Code ownership | **Orphaned code** -- code files in audit scope not referenced by any feature spec, companion file, or test import chain. **Orphaned skills** -- `.claude/commands/pl-*.md` command files with no corresponding `features/pl_*.md` feature spec. **Shared infrastructure** -- heavily-imported code (3+ feature importers) with no dedicated spec. **Dead code candidates** -- zero imports from any file AND zero feature owners. Deep mode provides per-file analysis; triage mode reports summary counts only. This is the symmetric complement of Dimension 11's "unused spec" detection: Dimension 11 finds specs without code; Dimension 12 finds code without specs. |

### 2.14 Severity Classification

| Severity | Criteria |
|---|---|
| CRITICAL | INFEASIBLE escalation active; spec-blocking circular dependency; open BUG with no resolution path |
| HIGH | Spec Gate FAIL; open BUG or SPEC_DISPUTE entry; unacknowledged `[DEVIATION]` or `[DISCOVERY]`; code behavior directly contradicts a scenario assertion; FORBIDDEN pattern violation from any transitive ancestor; conflicting requirements across features (contradictory assertions for the same component); orphaned skill file (`.claude/commands/pl-*.md` with no corresponding feature spec) |
| MEDIUM | Missing prerequisite link; traceability gap; dependency currency failure; spec-reality misalignment; significant undocumented code path; invariant with zero coverage in scenarios and code; duplicate requirements across features (same behavior specified in multiple places); orphaned executable code with significant behavior (entry points, state mutation, I/O operations) |
| LOW | Stub-only companion file on a complex feature; vague scenario wording; missing companion file; cosmetic spec inconsistencies; minor undocumented behavior; unused/orphaned feature spec with no implementation or dependents; dead code candidate (zero imports, zero owners); shared infrastructure code (3+ importers, no dedicated spec) |

### 2.15 Phase 3 -- Remediation (Post-Approval)

- After user approval, the command MUST execute FIX items first, then ESCALATE items.
- **Architect FIX:** Edit feature files directly (add missing sections, refine scenarios, add prerequisite links). For acknowledged builder decisions: update the spec and mark the tag as acknowledged in the companion file. Commit each logical group.
- **Architect ESCALATE:** Create or update companion files with tagged `[DISCOVERY]` entries including Source, Severity, Details, and Suggested fix. Commit together. Run `${TOOLS_ROOT}/cdd/status.sh` afterward.
- **Builder FIX:** Fix code to match scenario assertions. Add or update automated tests. Update companion file notes. Commit each logical group.
- **Builder ESCALATE:** Create or update companion files with `[DISCOVERY]` or `[SPEC_PROPOSAL]` entries. Commit together. Critic surfaces these at next Architect session.
- **Dimension 12 (Code ownership) remediation:**
  - **Architect FIX:** Create a new feature spec (via `/pl-spec`) for orphaned code that represents significant unspecified behavior, or add the file to an existing feature's companion Source Mapping section if it belongs to an existing feature.
  - **Architect ESCALATE to Builder:** If code appears dead (zero imports, zero owners, no entry points), record `[DISCOVERY]` in the nearest feature's companion file suggesting removal.
  - **Builder ESCALATE to Architect:** If the Builder discovers code that has no spec, record `[SPEC_PROPOSAL]` in the companion file requesting spec creation for the orphaned code.
- Post-remediation: run `${TOOLS_ROOT}/cdd/status.sh`, delete `.purlin/cache/audit_state.json`, and summarize results (N fixed, N escalated, N deferred).

### 2.16 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/pl_spec_code_audit/spec-code-gaps` | Project with feature specs that have known divergence from implementation code |

### 2.17 Phase 0.5 -- Code Inventory (Deep Mode Full / Triage Lightweight)

Phase 0.5 runs in the parent agent after Phase 0 (Section 2.6) and before dispatching subagents (Phase 1). It builds a complete code-to-feature ownership map and identifies orphaned code.

#### Step 0.5.1 -- Enumerate Code Files

- Use the confirmed scope from Section 2.5 (already established before Phase 0).
- Glob all files matching code extensions: `.py`, `.sh`, `.js`, `.ts`, `.go`, `.rs`, `.java`, `.rb`.
- For `.claude/commands/`: include `.md` files (skill files are executable behavior).
- Apply exclusions: `__pycache__/`, `node_modules/`, `vendor/`, `dist/`, `build/`, `.purlin/cache/`, `.purlin/runtime/`, binary files (`.pyc`, `.o`, `.so`), and files with `# DO NOT EDIT` or `// DO NOT EDIT` headers (auto-generated).
- Output: `code_inventory[]` -- list of `{path, extension, size_bytes}`.

#### Step 0.5.2 -- Build Ownership Map

- For each code file, attempt to find an owning feature using a ranked heuristic chain (first match wins):

| Priority | Heuristic | Confidence | Method |
|----------|-----------|------------|--------|
| H1 | Companion explicit reference | HIGH | Companion `.impl.md` contains `Tool Location:` or `### Source Mapping` referencing the file path |
| H2 | Spec explicit reference | HIGH | Feature spec `.md` mentions the file path in requirements or overview |
| H3 | Test import trace | HIGH | A test file in `tests/<feature>/` imports or executes the code file. **Deep mode only** -- requires reading source files. |
| H4 | Command-to-feature naming | HIGH | `.claude/commands/pl-<name>.md` maps to `features/pl_<name>.md` (dash-to-underscore convention) |
| H5 | Directory convention | MEDIUM | Feature name prefix maps to tool subdirectory (e.g., `cdd_status_monitor` -> `tools/cdd/`) |
| H6 | Name similarity | LOW | File stem substring-matches a feature name. **Deep mode only.** |

- A file MAY have multiple owners (legitimate for shared modules).
- Triage mode uses only H1, H2, H4, H5 (no source reading). Deep mode uses all six heuristics.
- Output: `ownership_map{}` -- `{file_path: {owners: [feature_names], heuristic: "<H1-H6>", confidence: "HIGH|MEDIUM|LOW"}}`.

#### Step 0.5.3 -- Classify Unowned Files (Deep Mode Only)

- Files with zero owners are classified into sub-categories:

| Classification | Criteria | Severity |
|---|---|---|
| **Orphaned executable** | Defines functions or entry points, no owner | MEDIUM |
| **Orphaned skill file** | `.claude/commands/pl-*.md` with no `features/pl_*.md` | HIGH |
| **Shared infrastructure** | Imported by 3+ features' test files but no dedicated spec | LOW |
| **Dead code candidate** | Zero imports from any file AND zero owners | LOW |
| **Infrastructure file** | Matches known patterns: `__init__.py`, `conftest.py`, `*_utils.*`, `setup.py`, `setup.cfg`, `pyproject.toml`, `Makefile`, `Dockerfile` | Excluded |

- Infrastructure files are auto-excluded from gap reporting. They are included in the inventory count but never generate gap entries.
- Output: `orphaned_files[]` -- `{path, classification, import_count, nearest_feature_suggestion}`.

#### False Positive Mitigation

Three mechanisms prevent noise in code ownership findings:

1. **Infrastructure file exclusion** -- Known patterns (`__init__.py`, `conftest.py`, `*_utils.*`, build system files) are auto-excluded from gap reporting.
2. **Import fan-in threshold** -- Files imported by 3+ features are classified as "shared infrastructure" (LOW severity) rather than orphaned.
3. **Confidence-weighted ownership** -- H5/H6 (MEDIUM/LOW confidence) matches suppress the gap but are noted as "weak ownership" in the audit table for human review.

### 2.18 Aggressive Subagent Parallelism

The command MUST maximize subagent parallelism throughout all phases to minimize wall-clock audit time:

- **Phase 0.5 ownership map:** In deep mode, if the code inventory exceeds 50 files, the ownership map construction (Step 0.5.2) MUST be parallelized by dispatching up to 5 Explore subagents, each assigned a partition of the code inventory. Each subagent reads its assigned files and returns ownership results. The parent agent merges results.
- **Phase 1 wave packing:** All 5 subagent slots per wave MUST be filled whenever batches remain. Spec-only, code-comparison, and orphan scan batches are mixed freely within the same wave. Empty slots MUST be filled with rescue batches from prior waves or remaining orphan scan batches.
- **Inter-wave launch:** The next wave MUST be dispatched immediately when the current wave's results are collected. No manual approval between waves.
- **Triage mode exception:** Triage runs entirely in-agent (no subagents) for speed on small projects. However, if the project has more than 30 features, triage mode MAY dispatch up to 3 Explore subagents for the per-feature scan phase, partitioning features across subagents.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Role gate rejects non-Architect/Builder invocation

    Given a QA agent session
    When the agent invokes /pl-spec-code-audit
    Then the command responds with "This command is for the Architect or Builder. Ask the appropriate agent to run /pl-spec-code-audit."
    And no analysis is performed

#### Scenario: Default invocation uses triage mode

    Given an Architect agent session
    When the agent invokes /pl-spec-code-audit with no arguments
    Then the command runs in triage mode
    And no subagents are launched
    And all features are processed in-agent

#### Scenario: Deep flag activates deep mode

    Given an Architect agent session
    When the agent invokes /pl-spec-code-audit --deep
    Then the command runs in deep mode
    And features are batched for parallel subagent waves

#### Scenario: Invalid argument produces error

    Given an Architect agent session
    When the agent invokes /pl-spec-code-audit --invalid
    Then the command responds with "Error: Unknown argument '--invalid'. Valid: --deep"
    And no analysis is performed

#### Scenario: Path resolution reads tools_root from config

    Given .purlin/config.json contains tools_root set to "purlin/tools"
    When the command resolves tool paths
    Then all tool invocations use the resolved TOOLS_ROOT path
    And no hardcoded "tools/" paths are used

#### Scenario: Transitive prerequisite map walks full ancestor chain

    Given feature A has Prerequisite arch_data.md
    And arch_data.md has Prerequisite policy_security.md
    When the command builds the transitive prerequisite map
    Then feature A's ancestor list includes both arch_data.md and policy_security.md

#### Scenario: Anchor constraint collection extracts FORBIDDEN patterns

    Given anchor node arch_data.md contains a FORBIDDEN pattern "direct SQL queries"
    When the command collects anchor constraints
    Then arch_data.md's constraint entry includes the FORBIDDEN pattern "direct SQL queries"

#### Scenario: Anchor constraint collection extracts invariants

    Given anchor node policy_critic.md contains numbered invariants in an Invariants section
    When the command collects anchor constraints
    Then policy_critic.md's constraint entry includes all numbered invariant statements

#### Scenario: Triage mode checks spec completeness across all gap dimensions

    Given a feature file exists with a missing Prerequisite link to an applicable anchor
    When triage mode processes the feature
    Then a gap is recorded with dimension "Policy anchoring"

#### Scenario: Triage mode performs light code scan for FORBIDDEN patterns

    Given a feature has implementation code
    And a transitive ancestor anchor defines FORBIDDEN pattern "os.system"
    And a source file contains "os.system" on line 42
    When triage mode performs the light code scan
    Then a gap is recorded with dimension "Anchor invariant drift"
    And the evidence includes the file path and line number

#### Scenario: Triage mode skips scenario-by-scenario comparison

    Given a feature has 10 automated scenarios
    When triage mode processes the feature
    Then individual scenario-to-code comparison is not performed
    And only surface-level checks are applied

#### Scenario: Deep mode classifies anchor nodes into spec-only track

    Given the project has anchor node arch_data.md
    When deep mode classifies features
    Then arch_data.md is placed in the spec-only track
    And it is not included in code-comparison batches

#### Scenario: Deep mode batches features by scenario count

    Given feature A has 30 scenarios and feature B has 40 scenarios
    When deep mode batches features
    Then feature A and feature B are placed in the same batch (total 70 scenarios within 50-75 target)

#### Scenario: Deep mode creates solo batch for large features

    Given feature C has 75 scenarios
    When deep mode batches features
    Then feature C is placed in a solo batch
    And no other features share its batch

#### Scenario: Deep mode limits concurrent subagents to 5 per wave

    Given 8 batches are created
    When deep mode assigns batches to waves
    Then wave 1 contains at most 5 batches
    And wave 2 contains the remaining batches

#### Scenario: Deep mode subagents receive transitive constraint payload

    Given the transitive prerequisite map and anchor constraints are computed in Phase 0
    When deep mode launches a code-comparison subagent
    Then the subagent prompt includes the transitive map for its assigned features
    And the subagent prompt includes the collected anchor constraints

#### Scenario: Deep mode subagents perform scenario-by-scenario comparison

    Given a code-comparison subagent is assigned a feature with 5 automated scenarios
    When the subagent processes the feature
    Then each scenario is compared against its corresponding test function and code path
    And contradictions between scenario assertions and code logic are flagged

#### Scenario: Spec-only subagents check cross-anchor consistency

    Given anchor node arch_data.md is a prerequisite of anchor node arch_api.md
    And arch_data.md and arch_api.md have overlapping invariant domains
    When a spec-only subagent processes arch_data.md
    Then the subagent checks for contradictions between arch_data.md and arch_api.md invariants

#### Scenario: Subagent returns structured output format

    Given a code-comparison subagent finishes analyzing a feature
    When the subagent returns results
    Then the output contains "=== FEATURE: <name> ===" header
    And each gap entry includes severity, dimension, owner, evidence, and suggested fix
    And the output ends with "=== END FEATURE ==="

#### Scenario: Wave results saved to audit state file

    Given deep mode wave 1 with 3 subagents completes
    When all subagent results are collected
    Then accumulated results are saved to .purlin/cache/audit_state.json
    And the dispatch manifest marks wave 1 as complete

#### Scenario: Failed subagent batch is re-queued

    Given deep mode wave 1 has 4 subagents
    And subagent 3 fails entirely (returns no results)
    When wave 1 completes
    Then the batch assigned to subagent 3 is re-queued for the next wave

#### Scenario: Synthesis deduplicates overlapping gaps

    Given two subagents both flag the same FORBIDDEN violation in file tools/critic/run.py line 15
    When Phase 2 synthesis parses all results
    Then only one gap entry appears in the audit table for that violation

#### Scenario: Audit table includes Evidence and Anchor Source columns

    Given a gap is found for a FORBIDDEN pattern violation from arch_data.md invariant 2.3
    When the audit table is built
    Then the gap row includes the file:line reference in the Evidence column
    And the gap row includes "arch_data.md invariant 2.3" in the Anchor Source column

#### Scenario: Architect remediation plan describes only spec edits

    Given the /pl-spec-code-audit command file exists
    When the Architect reads the remediation plan instructions
    Then the instructions explicitly state that Architect FIX edits target feature specs and anchor nodes only

#### Scenario: Builder remediation plan describes only code edits

    Given the /pl-spec-code-audit command file exists
    When the Builder reads the remediation plan instructions
    Then the instructions explicitly state that Builder FIX edits target source code and tests only

#### Scenario: Cross-session resume from interrupted deep mode wave

    Given deep mode wave 1 completed and wave 2 was interrupted
    And .purlin/cache/audit_state.json records wave 1 as complete with accumulated gaps
    When the agent invokes /pl-spec-code-audit --deep
    Then the command reads the state file and resumes from wave 2
    And the transitive map and anchor constraints are loaded from the state file (not recomputed)
    And wave 1 results are preserved in the accumulated gaps

#### Scenario: Cross-session resume from completed triage scan

    Given triage mode completed its scan and saved results
    And .purlin/cache/audit_state.json exists with accumulated gaps
    When the agent invokes /pl-spec-code-audit
    Then the command skips Phase 0 and proceeds to Phase 2 synthesis
    And all previously scanned results are used

#### Scenario: Audit state file deleted after remediation

    Given Phase 3 remediation completes
    And .purlin/cache/audit_state.json exists
    When post-remediation cleanup runs
    Then the audit state file is deleted
    And ${TOOLS_ROOT}/cdd/status.sh is executed

#### Scenario: No gaps produces clean report and exits plan mode

    Given all features are scanned and no gaps are found
    When Phase 2 synthesis completes
    Then the command outputs "No spec-code gaps detected across all N features."
    And ExitPlanMode is called

#### Scenario: FORBIDDEN pattern violation classified as HIGH severity

    Given a source file violates a FORBIDDEN pattern from a transitive ancestor anchor
    When the gap is classified
    Then the gap severity is HIGH
    And the gap dimension is "Anchor invariant drift"

#### Scenario: Missing prerequisite link classified as MEDIUM severity

    Given a feature is missing a Prerequisite link to an applicable anchor node
    When the gap is classified
    Then the gap severity is MEDIUM
    And the gap dimension is "Policy anchoring"

#### Scenario: Architect escalates code-side gap via companion file

    Given an Architect runs the audit and finds a code-side gap owned by the Builder
    When the Architect processes the ESCALATE item
    Then a [DISCOVERY] entry is added to the companion file
    And the entry includes Source, Severity, Details, and Suggested fix fields
    And ${TOOLS_ROOT}/cdd/status.sh is run after committing

#### Scenario: Builder escalates spec-side gap via companion file

    Given a Builder runs the audit and finds a spec-side gap owned by the Architect
    When the Builder processes the ESCALATE item
    Then a [DISCOVERY] or [SPEC_PROPOSAL] entry is added to the companion file
    And the entry includes Source, Severity, Details, and Suggested spec change fields

#### Scenario: Duplicate requirements detected across features

    Given feature A defines a scenario "Create Branch Pushes and Checks Out"
    And feature B defines a scenario "Branch Creation Pushes and Checks Out"
    And both scenarios target the same endpoint POST /branch-collab/create with identical assertions
    When the cross-feature requirement hygiene pass runs
    Then a gap is recorded with dimension "Requirement hygiene"
    And the gap description identifies the duplicate pair (feature A and feature B)
    And the gap severity is MEDIUM

#### Scenario: Conflicting requirements detected across features

    Given feature A specifies that POST /api/config returns 200 with the current config
    And feature B specifies that POST /api/config returns 404 when config is absent
    And both features target the same endpoint under the same preconditions
    When the cross-feature requirement hygiene pass runs
    Then a gap is recorded with dimension "Requirement hygiene"
    And the gap description identifies the conflicting assertions
    And the gap severity is HIGH

#### Scenario: Unused feature spec detected

    Given feature orphan_spec.md exists with 3 automated scenarios
    And no tests/<name>/ directory exists for orphan_spec
    And no other feature lists orphan_spec.md as a prerequisite
    And no implementation source files are discovered for orphan_spec
    When the cross-feature requirement hygiene pass runs
    Then a gap is recorded with dimension "Requirement hygiene"
    And the gap description identifies orphan_spec.md as an unused spec
    And the gap severity is LOW

#### Scenario: Scope confirmation auto-detects existing code directories

    Given a project with src/ and tools/ directories but no lib/
    When scope confirmation runs
    Then the presented scope includes src/ and tools/
    And lib/ is not listed

#### Scenario: Config-defined scope overrides auto-detection

    Given .purlin/config.json contains audit_code_paths ["src/", ".claude/commands/"]
    When scope confirmation runs
    Then the presented scope matches the config array

#### Scenario: User accepts default scope

    Given scope confirmation presents detected directories
    When the user confirms with default
    Then the command proceeds to Phase 0 with the detected scope

#### Scenario: User adjusts scope

    Given scope confirmation presents detected directories without .claude/commands/
    When the user adds .claude/commands/ to the scope
    Then the updated scope includes .claude/commands/
    And the command re-displays and re-confirms

#### Scenario: Confirmed scope constrains triage code scan

    Given the confirmed scope includes only src/ and tools/
    When triage mode performs light code scan
    Then source files are discovered only from src/ and tools/

#### Scenario: Code inventory enumerates all files in confirmed scope

    Given a project with confirmed scope including tools/ and .claude/commands/
    And tools/ contains 5 .py files and 2 .sh files
    And .claude/commands/ contains 3 pl-*.md files
    When Phase 0.5 Step 0.5.1 runs
    Then the code inventory contains all 10 files
    And each entry includes path, extension, and size_bytes

#### Scenario: Ownership map uses companion Tool Location (H1)

    Given a companion file features/cdd_status_monitor.impl.md contains "Tool Location: tools/cdd/status.sh"
    And tools/cdd/status.sh exists in the code inventory
    When Phase 0.5 Step 0.5.2 runs
    Then tools/cdd/status.sh is owned by cdd_status_monitor with heuristic H1 and confidence HIGH

#### Scenario: Ownership map uses spec path reference (H2)

    Given feature spec features/release_checklist_core.md mentions "tools/release/run_step.py" in its requirements section
    And tools/release/run_step.py exists in the code inventory
    When Phase 0.5 Step 0.5.2 runs
    Then tools/release/run_step.py is owned by release_checklist_core with heuristic H2 and confidence HIGH

#### Scenario: Ownership map uses test import tracing (H3)

    Given tests/critic_tool/test_critic.py imports tools.critic.run
    And tools/critic/run.py exists in the code inventory
    When Phase 0.5 Step 0.5.2 runs in deep mode
    Then tools/critic/run.py is owned by critic_tool with heuristic H3 and confidence HIGH

#### Scenario: Command file maps to feature by naming convention (H4)

    Given .claude/commands/pl-spec-code-audit.md exists in the code inventory
    And features/pl_spec_code_audit.md exists
    When Phase 0.5 Step 0.5.2 runs
    Then .claude/commands/pl-spec-code-audit.md is owned by pl_spec_code_audit with heuristic H4 and confidence HIGH

#### Scenario: Orphaned code file detected and reported as dimension 12

    Given tools/orphan_script.py exists in the code inventory
    And no feature spec, companion file, or test import references tools/orphan_script.py
    And tools/orphan_script.py defines 2 public functions
    When Phase 0.5 Step 0.5.3 classifies unowned files
    Then tools/orphan_script.py is classified as "orphaned executable"
    And a gap is recorded with dimension "Code ownership" and severity MEDIUM

#### Scenario: Orphaned skill file detected as HIGH severity

    Given .claude/commands/pl-orphan-skill.md exists in the code inventory
    And no features/pl_orphan_skill.md exists
    When Phase 0.5 Step 0.5.3 classifies unowned files
    Then .claude/commands/pl-orphan-skill.md is classified as "orphaned skill file"
    And a gap is recorded with dimension "Code ownership" and severity HIGH

#### Scenario: Dead code candidate classified as LOW severity

    Given tools/unused_helper.py exists in the code inventory
    And no feature spec, companion file, or test import references tools/unused_helper.py
    And no other code file in the project imports tools/unused_helper.py
    When Phase 0.5 Step 0.5.3 classifies unowned files
    Then tools/unused_helper.py is classified as "dead code candidate"
    And a gap is recorded with dimension "Code ownership" and severity LOW

#### Scenario: Shared infrastructure not flagged as orphaned

    Given tools/shared/helpers.py exists in the code inventory
    And tools/shared/helpers.py is imported by test files for 4 different features
    And no feature spec directly references tools/shared/helpers.py
    When Phase 0.5 Step 0.5.3 classifies unowned files
    Then tools/shared/helpers.py is classified as "shared infrastructure"
    And the gap severity is LOW (not MEDIUM)

#### Scenario: Infrastructure files excluded from gap reporting

    Given tools/__init__.py and tools/conftest.py exist in the code inventory
    When Phase 0.5 Step 0.5.3 classifies unowned files
    Then tools/__init__.py and tools/conftest.py are classified as "infrastructure file"
    And no gap entries are generated for either file

#### Scenario: Triage mode reports orphan count as summary only

    Given triage mode runs the lightweight code inventory
    And 8 orphaned files are detected using H1, H2, H4, H5 heuristics
    When the gap table is built
    Then a single summary gap entry is created for dimension "Code ownership"
    And the entry reports total orphan count (8) and the top-3 by severity
    And no per-file orphan entries appear in the triage gap table

#### Scenario: Orphan scan subagent extracts function signatures in deep mode

    Given an orphan scan subagent is assigned tools/orphan_script.py
    And tools/orphan_script.py defines functions "run_backup()" and "cleanup_logs(path)"
    When the orphan scan subagent processes the file
    Then the output includes "=== ORPHAN: tools/orphan_script.py ===" header
    And the public API summary lists "run_backup()" and "cleanup_logs(path)"
    And the output includes the nearest feature suggestion
    And the output ends with "=== END ORPHAN ==="

#### Scenario: Deep mode fills all subagent slots per wave

    Given deep mode has 3 code-comparison batches, 1 spec-only batch, and 2 orphan scan batches
    When wave 1 is dispatched
    Then all 5 subagent slots are filled
    And the remaining batch is queued for wave 2

### QA Scenarios

None.
