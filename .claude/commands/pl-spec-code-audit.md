**Purlin command: shared (Architect, Builder)**

If you are not operating as the Purlin Architect or Purlin Builder, respond: "This command is for the Architect or Builder. Ask the appropriate agent to run /pl-spec-code-audit." and stop.

---

Call the `EnterPlanMode` tool immediately before doing anything else. Do not read any files or run any commands until plan mode is active.

---

## Purpose

Bidirectional spec-code audit with role-aware remediation. Systematically scan all feature files for spec-side gaps (missing sections, broken anchors, stale notes) AND read implementation source to detect code-side deviations (undocumented behaviors, scenario-code contradictions). Produce a prioritized gap table, then remediate gaps within your role's authority and escalate cross-role gaps through established mechanisms.

**Role behavior:**
- **Architect:** Fixes spec-side gaps directly (edit feature files). Escalates code-side gaps to the Builder by adding actionable notes in companion files (`features/<name>.impl.md`).
- **Builder:** Fixes code-side gaps directly (edit code/tests). Escalates spec-side gaps to the Architect by recording `[DISCOVERY]` or `[SPEC_PROPOSAL]` entries in companion files.

---

## Phase 1: Analysis (Read-Only -- in Plan Mode)

### Step 1 -- Load Project State

1. Run `tools/cdd/status.sh` and read `CRITIC_REPORT.md`.
2. Read `.purlin/cache/dependency_graph.json` -- note all prerequisite relationships and root anchor nodes.
3. Note which features have non-DONE Architect status, non-DONE Builder status, or non-CLEAN QA status.

### Step 2 -- Per-Feature Deep Scan

Process features in dependency order: anchor nodes (`arch_*`, `design_*`, `policy_*`) first, then features ordered from fewest to most prerequisites. For each feature:

1. Read the feature file and its companion `*.impl.md` (if it exists).
2. Read `tests/<feature_name>/critic.json` for gate status, role_status, and action items.
3. Assess the feature across these gap dimensions:

| Dimension | What to look for |
|---|---|
| **Spec completeness** | Missing required sections; vague scenarios; undefined terms; anchor nodes missing Purpose or Invariants |
| **Policy anchoring** | Missing `> Prerequisite:` links to applicable anchor nodes |
| **Traceability** | Automated scenarios with no matching test functions (`coverage < 1.0`) |
| **Builder decisions** | Unacknowledged `[DEVIATION]` or `[DISCOVERY]` tags in Implementation Notes or companion file |
| **User testing** | OPEN or SPEC_UPDATED discovery entries |
| **Dependency currency** | Prerequisite anchor node has lifecycle status TODO or was recently modified -- dependent feature may need re-validation |
| **Spec-reality alignment** | Implementation Notes document decisions that contradict or significantly extend existing scenarios without corresponding spec updates |
| **Notes depth** | Complex feature (5+ scenarios or visual spec) with stub-only or absent Implementation Notes |
| **Code divergence** | Read implementation source files for each feature (discovered via test imports or tool directory mapping). Compare code behavior against automated scenarios. Flag: (a) scenario assertions not reflected in code logic, (b) significant code paths/conditions/error handling not covered by any scenario, (c) hardcoded values or behaviors the spec says should be configurable or parameterized. |

### Step 3 -- Code Inspection Pass

For each feature that has implementation code:

1. **Discover source files:** Read `tests/<feature_name>/` test files. Extract import paths and subprocess invocations to identify primary implementation modules. Fall back to tool directory mapping from the feature's `> Label:` (e.g., "Tool: Critic" -> `tools/critic/`, "Tool: CDD Monitor" -> `tools/cdd/`).
2. **Read primary source:** Read the main implementation file(s) -- typically 1-3 files per feature. Do NOT read every file in the directory; focus on the files referenced by tests.
3. **Scenario-code comparison:** For each automated scenario, verify the described behavior exists in the source code. Note any contradictions.
4. **Undocumented behavior scan:** Identify significant code paths (error handling, edge cases, configuration branches) that are not covered by any automated or manual scenario.
5. **Skip conditions:** Skip code inspection for anchor nodes (no implementation), features with no test directory, and features where all gates PASS and all role statuses are DONE/CLEAN (unless a spec-side gap was already found in Step 2).

### Step 4 -- Classify Each Gap

For every gap found, assign:

**Severity:**

| Severity | Criteria |
|---|---|
| CRITICAL | INFEASIBLE escalation active; spec-blocking circular dependency; open BUG with no resolution path |
| HIGH | Spec Gate FAIL; open BUG or SPEC_DISPUTE entry; unacknowledged `[DEVIATION]` or `[DISCOVERY]`; code behavior directly contradicts a scenario assertion |
| MEDIUM | Missing prerequisite link; traceability gap (coverage < 1.0); unacknowledged `[AUTONOMOUS]` decision; dependency currency failure (prerequisite updated, dependent not re-validated); spec-reality misalignment documented in impl notes; significant undocumented code path (error handling, branching logic) with no scenario coverage |
| LOW | Stub-only Implementation Notes on a complex feature; vague scenario wording; missing companion file for a large feature; cosmetic spec inconsistencies; minor undocumented behavior (logging, cosmetic defaults) unlikely to affect correctness |

**Owner:** Assign based on what needs to change, not who is running the command:
- `ARCHITECT` -- the spec needs to be updated (to match reality, clarify ambiguity, add missing anchors, revise scenarios)
- `BUILDER` -- code or tests need to be updated (to match spec, add missing test coverage, resolve INFEASIBLE)

**Action:** Based on who is running the command and the Owner assignment:
- If Owner matches your role -> `FIX` (you will remediate directly)
- If Owner is the other role -> `ESCALATE` (you will record it for the other role via companion files)

### Step 5 -- Build the Audit Table

Sort all findings: CRITICAL -> HIGH -> MEDIUM -> LOW, then alphabetically by filename within each group. Number rows sequentially starting at 1.

Write the following to the plan file:

---

### Spec-Code Audit -- `<timestamp>`

**Role:** Architect | Builder
**Total features scanned:** N
**Gaps found:** N (CRITICAL: N . HIGH: N . MEDIUM: N . LOW: N)
**Will fix:** N | **Will escalate:** N

| # | Feature | Severity | Dimension | Gap Description | Action | Planned Remediation |
|---|---|---|---|---|---|---|
| 1 | feature_name | HIGH | Code divergence | Code does X but scenario says Y | FIX | Update scenario to match implemented behavior |
| 2 | feature_name | MEDIUM | Traceability | Scenario "Foo" has no test | ESCALATE | Record [DISCOVERY] in companion file |

---

**Remediation Plan:**

For each FIX item, describe the specific edit scoped to the acting role's artifacts:
- **Architect FIX edits** target feature specs (`features/*.md`) and anchor nodes (`arch_*.md`, `design_*.md`, `policy_*.md`) only — which section to add/revise, what scenario language to change, which prerequisite link to add.
- **Builder FIX edits** target source code and tests only — which implementation file to modify, what logic to correct, which test to add or update.
For each ESCALATE item, describe the companion file entry that will be written.

If no gaps are found, write: "No spec-code gaps detected across all N features." and call `ExitPlanMode`.

### Step 6 -- Exit Plan Mode

After writing the audit table and remediation plan, call `ExitPlanMode`. Wait for user approval before proceeding to Phase 2.

---

## Phase 2: Remediation (After User Approval)

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
4. Run `tools/cdd/status.sh` after committing to update the Critic report (the Critic's Builder Decision Audit will surface these as Builder action items).

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
1. Run `tools/cdd/status.sh` to regenerate the Critic report.
2. Summarize what was done: N items fixed, N items escalated, any items deferred with rationale.
