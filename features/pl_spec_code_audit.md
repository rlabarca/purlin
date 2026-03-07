# Feature: Spec-Code Audit

> Label: "/pl-spec-code-audit Spec-Code Audit"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md
> Prerequisite: features/impl_notes_companion.md

[TODO]

## 1. Overview

The `/pl-spec-code-audit` command performs a bidirectional audit between feature specifications and implementation code, detecting gaps in both directions: spec-side deficiencies (missing sections, broken anchors, stale notes) and code-side deviations (undocumented behaviors, scenario-code contradictions, anchor invariant violations). It operates in two modes: **triage** (default, fast, runs entirely in-agent) and **deep** (parallel subagent waves with scenario-by-scenario comparison and transitive anchor constraint validation). Both modes produce a prioritized gap table with role-scoped remediation, then execute fixes within the acting role's authority and escalate cross-role gaps through companion files.

---

## 2. Requirements

### 2.1 Role Gating

- The command is shared between Architect and Builder roles.
- Non-Architect/Builder agents MUST receive: "This command is for the Architect or Builder. Ask the appropriate agent to run /pl-spec-code-audit."

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

### 2.5 Phase 0 -- Project State and Constraint Loading

- The command MUST run `${TOOLS_ROOT}/cdd/status.sh` and read `CRITIC_REPORT.md` and `.purlin/cache/dependency_graph.json`.
- For each feature, the command MUST read `tests/<name>/critic.json` to extract scenario count from traceability detail.
- The command MUST build a transitive prerequisite map by walking all `> Prerequisite:` chains recursively (BFS) for every feature in the dependency graph. Output: `{feature_name: [list of all ancestor anchor filenames]}`.
- The command MUST collect anchor constraints from each unique anchor node in the transitive map: all `FORBIDDEN:` patterns (line + pattern text), numbered invariant statements, and named constraints. Output: `{anchor_name: {forbidden: [...], invariants: [...], constraints: [...]}}`.
- Phase 0 reads only metadata and anchor node constraint sections -- never feature scenarios or source code.

### 2.6 Cross-Session Resume

- The command MUST check for `.purlin/cache/audit_state.json` before starting analysis.
- If found, the command MUST report resume status and skip to the next incomplete step.
- The state file MUST track: `mode`, `role`, `timestamp`, `transitive_map`, `anchor_constraints`, `dispatch_manifest` (deep mode), `accumulated_gaps`, and `scan_failures`.
- On resume in deep mode, completed waves are skipped and the next incomplete wave resumes.
- On resume in triage mode with scan complete, the command skips to Phase 2 synthesis.
- The state file MUST be deleted after Phase 3 (Remediation) completes.

### 2.7 Triage Mode (Default)

- Triage mode MUST process all features in-agent without launching subagents.
- For each feature, the command MUST:
  - Read the feature file and check spec completeness across all 10 gap dimensions (see Section 2.12).
  - Read companion file if it exists and check builder decisions and notes depth.
  - Read `tests/<name>/critic.json` for gate status and traceability.
  - Perform an anchor constraint surface check: for each ancestor anchor in the transitive map, verify the feature's scenarios reference or account for the anchor's invariants. Flag invariants with zero scenario coverage.
  - Perform a light code scan (if implementation exists): read up to 3 primary source files (discovered via test imports or companion file Tool Location) and grep for FORBIDDEN patterns from all transitive ancestors. Flag violations.
- Triage mode MUST skip scenario-by-scenario deep comparison.
- After processing all features, results MUST be saved to `.purlin/cache/audit_state.json`.

### 2.8 Deep Mode

- Deep mode MUST classify features into two processing tracks:
  - **Spec-only track:** Anchor nodes (`arch_*`, `design_*`, `policy_*`) and features with zero automated scenarios.
  - **Code-comparison track:** All features with automated scenarios.
- Deep mode MUST batch features using first-fit-decreasing bin packing: 50-75 scenarios per code-comparison batch, max 4-5 features per batch. Features with 50+ scenarios get a solo batch. All spec-only features go in a single batch.
- Batches MUST be assigned to waves of up to 5 concurrent subagents.
- A dispatch manifest MUST be written to the plan file (wave/agent/feature/scenario-count table).
- The transitive prerequisite map and collected anchor constraints MUST be included in each subagent's prompt payload so subagents do not need to re-derive them.

### 2.9 Phase 1 -- Parallel Deep Scan (Deep Mode Only)

- Subagents MUST be launched wave by wave. All subagents in a wave MUST be launched in a single message via multiple Task tool calls (concurrent execution).
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
  - Check spec completeness across all 10 gap dimensions.
- **Spec-only subagents** MUST:
  - Read the feature file and companion.
  - Check spec completeness, policy anchoring, builder decisions, and notes depth.
  - For anchor nodes: verify Purpose and Invariants sections are substantive.
  - Check cross-anchor consistency if the anchor is a prerequisite of other anchors.
  - Skip code comparison entirely.
- Each subagent MUST return structured output in the format: `=== FEATURE: <name> ===` ... `=== END FEATURE ===` with gaps listed as `[SEVERITY] [DIMENSION] [OWNER]` entries including Evidence, Anchor source, and Suggested fix fields.
- After each wave completes, accumulated results MUST be saved to `.purlin/cache/audit_state.json`.
- If context guard threshold is approaching, the command MUST save state and instruct the user to resume with `/pl-spec-code-audit --deep`.
- If a subagent returns incomplete results, a rescue batch MUST be created for the next wave.
- If a subagent fails entirely, the batch MUST be re-queued.

### 2.10 Phase 2 -- Synthesis

- The command MUST parse all gap findings from in-agent triage scan or subagent structured output.
- The command MUST deduplicate gaps where the same implementation file is flagged by overlapping feature batches or transitive anchors.
- Each gap MUST be classified by severity (CRITICAL, HIGH, MEDIUM, LOW), owner (ARCHITECT or BUILDER), and action (FIX if owner matches acting role, ESCALATE otherwise). See Section 2.13 for severity criteria.
- The command MUST build an audit table sorted CRITICAL to LOW, then alphabetically by feature name. Rows are numbered sequentially.
- The audit table MUST include columns: #, Feature, Severity, Dimension, Gap Description, Evidence, Anchor Source, Action, Planned Remediation.
- The table header MUST include: Role, Mode, Total features scanned, Transitive anchor constraints checked (N invariants across M anchors), Gaps found (with per-severity counts), Will fix count, and Will escalate count.

### 2.11 Role-Scoped Remediation Plan

- The remediation plan MUST contain role-scoped FIX descriptions:
  - **Architect FIX edits** target feature specs (`features/*.md`) and anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) only -- which section to add/revise, what scenario language to change, which prerequisite link to add.
  - **Builder FIX edits** target source code and tests only -- which implementation file to modify, what logic to correct, which test to add or update.
- For each ESCALATE item, the plan MUST describe the companion file entry that will be written.
- If no gaps are found, the command MUST output "No spec-code gaps detected across all N features." and call `ExitPlanMode`.
- After writing the audit table and remediation plan, the command MUST call `ExitPlanMode` and wait for user approval.

### 2.12 Gap Dimensions

The command MUST assess each feature against these 10 dimensions:

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

### 2.13 Severity Classification

| Severity | Criteria |
|---|---|
| CRITICAL | INFEASIBLE escalation active; spec-blocking circular dependency; open BUG with no resolution path |
| HIGH | Spec Gate FAIL; open BUG or SPEC_DISPUTE entry; unacknowledged `[DEVIATION]` or `[DISCOVERY]`; code behavior directly contradicts a scenario assertion; FORBIDDEN pattern violation from any transitive ancestor |
| MEDIUM | Missing prerequisite link; traceability gap; dependency currency failure; spec-reality misalignment; significant undocumented code path; invariant with zero coverage in scenarios and code |
| LOW | Stub-only companion file on a complex feature; vague scenario wording; missing companion file; cosmetic spec inconsistencies; minor undocumented behavior |

### 2.14 Phase 3 -- Remediation (Post-Approval)

- After user approval, the command MUST execute FIX items first, then ESCALATE items.
- **Architect FIX:** Edit feature files directly (add missing sections, refine scenarios, add prerequisite links). For acknowledged builder decisions: update the spec and mark the tag as acknowledged in the companion file. Commit each logical group.
- **Architect ESCALATE:** Create or update companion files with tagged `[DISCOVERY]` entries including Source, Severity, Details, and Suggested fix. Commit together. Run `${TOOLS_ROOT}/cdd/status.sh` afterward.
- **Builder FIX:** Fix code to match scenario assertions. Add or update automated tests. Update companion file notes. Commit each logical group.
- **Builder ESCALATE:** Create or update companion files with `[DISCOVERY]` or `[SPEC_PROPOSAL]` entries. Commit together. Critic surfaces these at next Architect session.
- Post-remediation: run `${TOOLS_ROOT}/cdd/status.sh`, delete `.purlin/cache/audit_state.json`, and summarize results (N fixed, N escalated, N deferred).

### 2.15 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/pl_spec_code_audit/spec-code-gaps` | Project with feature specs that have known divergence from implementation code |

---

## 3. Scenarios

### Automated Scenarios

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

### Manual Scenarios (Human Verification Required)

None.
