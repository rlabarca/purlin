**Purlin command: shared (Architect, Builder)**

If you are not operating as the Purlin Architect or Purlin Builder, respond: "This command is for the Architect or Builder. Ask the appropriate agent to run /pl-spec-code-audit." and stop.

---

Call the `EnterPlanMode` tool immediately before doing anything else. Do not read any files or run any commands until plan mode is active.

---

## Purpose

Bidirectional spec-code audit with role-aware remediation. Two modes: **triage** (default, fast, in-agent) and **deep** (parallel subagent waves with scenario-by-scenario comparison and transitive anchor constraint validation). Both modes produce a prioritized gap table, then remediate gaps within your role's authority and escalate cross-role gaps through established mechanisms.

**Role behavior:**
- **Architect:** Fixes spec-side gaps directly (edit feature files). Escalates code-side gaps to the Builder by adding actionable notes in companion files (`features/<name>.impl.md`).
- **Builder:** Fixes code-side gaps directly (edit code/tests). Escalates spec-side gaps to the Architect by recording `[DISCOVERY]` or `[SPEC_PROPOSAL]` entries in companion files.

---

## Argument Parsing

Parse `$ARGUMENTS`:
- **No argument or empty:** Mode is `triage`.
- **`--deep`:** Mode is `deep`.
- **Anything else:** Abort with: `Error: Unknown argument '<arg>'. Valid: --deep`

---

## Path Resolution

1. Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`).
2. Resolve project root: use `PURLIN_PROJECT_ROOT` env var if set and `.purlin/` exists there, otherwise climb from the current working directory until `.purlin/` is found.
3. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

All tool invocations use `${TOOLS_ROOT}/...` (e.g., `${TOOLS_ROOT}/cdd/status.sh`).

---

## Phase 0: Triage (Parent Agent -- Both Modes)

Parent loads project state, builds the transitive prerequisite constraint map, and constructs the dispatch plan. Reads only metadata and anchor node constraint sections -- never feature scenarios or source code in this phase.

### Step 0.1 -- Load Project State

1. Run `${TOOLS_ROOT}/cdd/status.sh` and read `CRITIC_REPORT.md`.
2. Read `.purlin/cache/dependency_graph.json` -- note all prerequisite relationships and root anchor nodes.
3. For each feature, read `tests/<name>/critic.json` to extract scenario count from traceability detail.

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

Process ALL features in-agent (no subagents). For each feature:

1. Read the feature file -- check spec completeness across all 10 gap dimensions (see Gap Dimensions Table below).
2. Read companion file (`features/<name>.impl.md`) if it exists -- check builder decisions, notes depth.
3. Read `tests/<name>/critic.json` -- check gate status, traceability.
4. **Anchor constraint surface check**: For each ancestor anchor in the transitive map, verify the feature's scenarios reference or account for the anchor's invariants. Flag invariants with zero scenario coverage.
5. **Light code scan** (if implementation exists): Read up to 3 primary source files (discovered via test imports or companion file Tool Location). Grep for FORBIDDEN patterns from all transitive ancestors. Flag violations.
6. Skip scenario-by-scenario deep comparison.

After processing all features, save results to `.purlin/cache/audit_state.json` and proceed directly to Phase 2 (Synthesis).

### If mode is `deep`:

#### Step D.1 -- Classify Features

Classify features into two processing tracks:
- **Spec-only track**: Anchor nodes (`arch_*`, `design_*`, `policy_*`) + features with zero automated scenarios.
- **Code-comparison track**: All features with automated scenarios.

#### Step D.2 -- Batch Features

Batch features using first-fit-decreasing bin packing:
- Target: 50-75 scenarios per code-comparison batch, max 4-5 features per batch.
- Solo batch for any feature with 50+ scenarios.
- All spec-only features go in a single batch.

#### Step D.3 -- Assign Waves

Assign batches to waves of up to 5 concurrent subagents. Write the dispatch manifest to the plan file (wave/agent/feature/scenario-count table). Include the transitive prerequisite map and collected anchor constraints in each subagent's prompt payload so subagents don't need to re-derive them.

Then proceed to Phase 1.

---

## Phase 1: Parallel Deep Scan (Deep Mode Only -- Subagent Waves)

Launch subagents wave by wave. All subagents in a wave are launched in a single message via multiple Task tool calls (concurrent execution).

**Subagent type:** `Explore` (read-only: Glob, Grep, Read, Bash)

### Code-Comparison Subagent Protocol

Each subagent receives the following in its prompt, plus the transitive constraint payload:

For each assigned feature:
1. **Read spec**: `features/<name>.md` -- extract all `#### Scenario:` entries with Given/When/Then.
2. **Read companion**: `features/<name>.impl.md` -- note Tool Location, source mappings, decision tags.
3. **Read critic data**: `tests/<name>/critic.json` -- gate statuses, traceability, action items.
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
9. **Spec completeness**: All 10 gap dimensions (see Gap Dimensions Table).

### Spec-Only Subagent Protocol

Simplified scan:
- Read feature file and companion.
- Check spec completeness, policy anchoring, builder decisions, notes depth.
- For anchor nodes: verify Purpose and Invariants sections are substantive.
- **Cross-anchor consistency**: If this anchor is a prerequisite of other anchors, check for contradictions between their invariant sets.
- Skip code comparison entirely.

### Structured Output Format

Each subagent returns:
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

### Wave Execution

- After each wave completes, save accumulated results to `.purlin/cache/audit_state.json`.
- If context guard threshold is approaching, save state and instruct user to resume with `/pl-spec-code-audit --deep`.
- If a subagent returns incomplete results (missing features), create a rescue batch for the next wave.
- If a subagent fails entirely, re-queue the batch.

---

## Phase 2: Synthesis (Parent Agent -- Both Modes)

### Step 2.1 -- Parse and Classify Gaps

1. Parse all gap findings (from in-agent triage scan or subagent structured output blocks).
2. Deduplicate gaps (same implementation file flagged by overlapping feature batches or transitive anchors).
3. Classify each gap:

**Severity:**

| Severity | Criteria |
|---|---|
| CRITICAL | INFEASIBLE escalation active; spec-blocking circular dependency; open BUG with no resolution path |
| HIGH | Spec Gate FAIL; open BUG or SPEC_DISPUTE entry; unacknowledged `[DEVIATION]` or `[DISCOVERY]`; code behavior directly contradicts a scenario assertion; FORBIDDEN pattern violation from any transitive ancestor |
| MEDIUM | Missing prerequisite link; traceability gap (coverage < 1.0); dependency currency failure (prerequisite updated, dependent not re-validated); spec-reality misalignment; significant undocumented code path; invariant with zero coverage in scenarios and code |
| LOW | Stub-only companion file on a complex feature; vague scenario wording; missing companion file for a large feature; cosmetic spec inconsistencies; minor undocumented behavior |

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

**Role:** Architect | Builder
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
- **Architect FIX edits** target feature specs (`features/*.md`) and anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) only -- which section to add/revise, what scenario language to change, which prerequisite link to add.
- **Builder FIX edits** target source code and tests only -- which implementation file to modify, what logic to correct, which test to add or update.
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
| **Builder decisions** | Unacknowledged `[DEVIATION]` or `[DISCOVERY]` tags in companion file |
| **User testing** | OPEN or SPEC_UPDATED discovery entries |
| **Dependency currency** | Prerequisite anchor node has lifecycle status TODO or was recently modified |
| **Spec-reality alignment** | Implementation Notes document decisions that contradict or extend scenarios without spec updates |
| **Notes depth** | Complex feature (5+ scenarios or visual spec) with stub-only or absent companion file |
| **Code divergence** | Scenario assertions not reflected in code; significant code paths with no scenario coverage; hardcoded values the spec says should be configurable |
| **Anchor invariant drift** | Code violates invariants or constraints from transitive ancestor anchors (not just direct prerequisites). Includes FORBIDDEN pattern violations. |

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

On re-invocation: if state file exists, report resume status, skip Phase 0, resume from next incomplete step. Deleted after Phase 3 completes.

---

## Phase 3: Remediation (After User Approval)

After the user approves the plan, execute the remediation. Process FIX items first, then ESCALATE items.

### If Running as Architect

**FIX (spec-side gaps you own):**
1. Edit the feature file directly -- add missing sections, refine vague scenarios, add prerequisite links, update stale spec content.
2. For acknowledged builder decisions (`[DEVIATION]`, `[DISCOVERY]`): update the spec to reflect the decision, then mark the tag as acknowledged in the companion file.
3. Commit each logical group of spec fixes.

**ESCALATE (code-side gaps for the Builder):**
1. Open (or create) the companion file `features/<feature_name>.impl.md`.
2. Add a clearly tagged entry under the implementation notes:

```
### Audit Finding -- <date>
[DISCOVERY] <description of the code gap>
**Source:** /pl-spec-code-audit
**Severity:** <severity>
**Details:** <what the code does vs what the spec expects, or what code path lacks scenario coverage>
**Suggested fix:** <concrete suggestion for the Builder>
```

3. Commit all escalation entries together.
4. Run `${TOOLS_ROOT}/cdd/status.sh` after committing to update the Critic report (the Critic's Builder Decision Audit will surface these as Builder action items).

### If Running as Builder

**FIX (code-side gaps you own):**
1. Fix code to match scenario assertions -- correct contradictions, add missing error handling, update hardcoded values.
2. Add or update automated tests to close traceability gaps.
3. Update the companion file's implementation notes to document what changed and why.
4. Commit each logical group of code fixes.

**ESCALATE (spec-side gaps for the Architect):**
1. Open (or create) the companion file `features/<feature_name>.impl.md`.
2. Add a `[DISCOVERY]` or `[SPEC_PROPOSAL]` entry:

```
### Audit Finding -- <date>
[DISCOVERY] <description of the spec gap>
**Source:** /pl-spec-code-audit
**Severity:** <severity>
**Details:** <what is missing or inconsistent in the spec>
**Suggested spec change:** <concrete proposal for the Architect>
```

3. Commit all escalation entries together.
4. The Critic will surface these as Architect action items at the next Architect session.

### Post-Remediation

After all items are processed:
1. Run `${TOOLS_ROOT}/cdd/status.sh` to regenerate the Critic report.
2. Delete `.purlin/cache/audit_state.json` if it exists.
3. Summarize what was done: N items fixed, N items escalated, any items deferred with rationale.
