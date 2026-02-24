**Purlin command owner: Architect**

If you are not operating as the Purlin Architect, respond: "This is an Architect command. Ask your Architect agent to run /pl-spec-gap-analysis instead." and stop.

---

Call the `EnterPlanMode` tool immediately before doing anything else. Do not read any files or run any commands until plan mode is active.

---

## Purpose

Systematically scan all feature files and their prerequisite chains for gaps between specification and implementation. Produce a single prioritized table for human review. No changes are made — all findings are written to the plan file for discussion before any remediation begins.

---

## Analysis Protocol

### Step 1 — Load Project State

1. Run `tools/cdd/status.sh` and read `CRITIC_REPORT.md`.
2. Read `.purlin/cache/dependency_graph.json` — note all prerequisite relationships and root anchor nodes.
3. Note which features have non-DONE Architect status, non-DONE Builder status, or non-CLEAN QA status.

### Step 2 — Per-Feature Deep Scan

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
| **Dependency currency** | Prerequisite anchor node has lifecycle status TODO or was recently modified — dependent feature may need re-validation |
| **Spec-reality alignment** | Implementation Notes document decisions that contradict or significantly extend existing scenarios without corresponding spec updates |
| **Notes depth** | Complex feature (5+ scenarios or visual spec) with stub-only or absent Implementation Notes |

### Step 3 — Classify Each Gap

For every gap found, assign:

**Severity:**

| Severity | Criteria |
|---|---|
| CRITICAL | INFEASIBLE escalation active; spec-blocking circular dependency; open BUG with no resolution path |
| HIGH | Spec Gate FAIL; open BUG or SPEC_DISPUTE entry; unacknowledged `[DEVIATION]` or `[DISCOVERY]` |
| MEDIUM | Missing prerequisite link; traceability gap (coverage < 1.0); unacknowledged `[AUTONOMOUS]` decision; dependency currency failure (prerequisite updated, dependent not re-validated); spec-reality misalignment documented in impl notes |
| LOW | Stub-only Implementation Notes on a complex feature; vague scenario wording; missing companion file for a large feature; cosmetic spec inconsistencies |

**Owner:**
- `ARCHITECT` — the spec needs to be updated (to match reality, clarify ambiguity, add missing anchors, revise scenarios)
- `BUILDER` — code or tests need to be updated (to match spec, add missing test coverage, resolve INFEASIBLE)

### Step 4 — Build the Gap Table

Sort all findings: CRITICAL → HIGH → MEDIUM → LOW, then alphabetically by filename within each group. Number rows sequentially starting at 1.

Write the following to the plan file:

---

### Spec-Code Gap Analysis — `<timestamp>`

**Total features scanned:** N
**Gaps found:** N (CRITICAL: N · HIGH: N · MEDIUM: N · LOW: N)

| # | Feature Name | File | Severity | Gap Description | Recommendation | Owner |
|---|---|---|---|---|---|---|
| 1 | ... | ... | CRITICAL | ... | ... | ARCHITECT / BUILDER |

---

If no gaps are found, write: "No spec-code gaps detected across all N features."

### Step 5 — Exit Plan Mode

After writing the gap table to the plan file, call `ExitPlanMode`.

Do not commit, edit any file, or take any other action. This is a fully read-only analysis. Remediation happens in separate sessions after the user reviews and discusses the table.
