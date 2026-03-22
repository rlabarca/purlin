# Feature: Phase Analyzer

> Label: "Tool: Phase Analyzer"
> Category: "Install, Update & Scripts"
> Prerequisite: features/policy_critic.md

[Complete]

## 1. Overview

A dependency-aware analysis tool (`tools/delivery/phase_analyzer.py`) that reads the delivery plan and dependency graph to determine correct phase execution order and identify parallelization opportunities. The tool detects when phases are ordered incorrectly relative to their feature dependencies, computes a topologically-sorted execution order, and groups independent phases into parallel execution sets. For intra-phase analysis, the tool also performs implementation coupling detection to warn when spec-independent features share source files, enabling the Builder to make informed parallelization decisions while relying on the merge protocol as the ultimate safety net. Output is structured JSON to stdout, suitable for consumption by the continuous phase builder orchestration loop.

---

## 2. Requirements

### 2.1 Inputs

- **Delivery plan:** Read from `.purlin/delivery_plan.md`. Extract PENDING phases and their feature lists.
- **Dependency graph:** Read from `.purlin/cache/dependency_graph.json`. Extract feature dependency edges.
- **Submodule safety:** MUST use `PURLIN_PROJECT_ROOT` (env var) for path resolution, with climbing fallback. MUST NOT assume CWD or hardcode paths.

### 2.2 Phase Extraction

- Parse delivery plan Markdown to extract phase numbers, statuses, and feature lists.
- Only PENDING phases are included in the analysis. COMPLETE and IN_PROGRESS phases are excluded.
- Each phase's feature list is the set of feature filenames listed under that phase.

### 2.3 Dependency Resolution

- Build transitive closure of feature dependencies from the dependency graph.
- For each pair of PENDING phases, check whether any feature in Phase A depends (transitively) on any feature in Phase B, or vice versa.
- A cross-phase dependency from Phase A to Phase B means Phase A MUST execute after Phase B.

### 2.4 Topological Ordering

- Topologically sort phases based on their inter-phase dependency edges.
- If the delivery plan's original ordering violates the topological order, the output MUST flag this with `reordered: true` and include a `warnings` array describing each misordering.
- If phases form a dependency cycle (should not happen if the feature dependency graph is acyclic), report an error and exit with non-zero status.

### 2.5 Parallel Grouping

- After topological sorting, group phases that have no inter-phase dependencies (in either direction) into parallel execution sets.
- Each group in the output represents phases that can execute concurrently.
- A group with a single phase has `parallel: false`. A group with multiple phases has `parallel: true`.
- Each group includes a `reason` string explaining why it is sequential or parallel.

### 2.6 Output Format

- Structured JSON to stdout. No other output to stdout (diagnostics go to stderr).
- Schema:

```json
{
  "groups": [
    {
      "phases": [6],
      "parallel": false,
      "reason": "foundation phase — no prior dependencies"
    },
    {
      "phases": [4],
      "parallel": false,
      "reason": "depends on group 1 (Phase 6)"
    },
    {
      "phases": [3, 5],
      "parallel": true,
      "reason": "no cross-dependencies between Phase 3 and Phase 5"
    }
  ],
  "reordered": true,
  "original_order": [3, 4, 5, 6],
  "warnings": [
    "Phase 3 depends on Phase 4 but was ordered before it in the delivery plan"
  ]
}
```

### 2.7 Error Handling

- If the delivery plan file does not exist, print an error to stderr and exit with non-zero status.
- If the dependency graph file does not exist, print an error to stderr and exit with non-zero status.
- If no PENDING phases exist in the delivery plan, output `{"groups": [], "reordered": false, "original_order": [], "warnings": []}` and exit with zero status.
- If a phase references a feature not present in the dependency graph, emit a warning to stderr and treat the feature as having no dependencies.

### 2.8 Generated Artifact Location

- Script lives at `tools/delivery/phase_analyzer.py` (consumer-facing tool, submodule-safe).
- No generated artifacts are written to disk. All output is to stdout.

### 2.9 Intra-Phase Feature Independence Analysis

- **CLI:** `python3 tools/delivery/phase_analyzer.py --intra-phase <phase_number>`
- Reads the delivery plan and dependency graph (same inputs as default mode).
- Extracts features for the specified phase, then checks pairwise independence using the existing `build_transitive_closure()` algorithm.
- Reuses `build_transitive_closure()`, `load_dependency_graph()`, `parse_delivery_plan()`. New function: `compute_feature_independence()` — same pattern as `group_parallel_phases()`.
- Only phases in PENDING or IN_PROGRESS status are valid targets. If the specified phase does not exist or is in COMPLETE status, print an error to stderr and exit with non-zero status.
- Output schema:

```json
{
  "phase": 3,
  "features": ["feature_a.md", "feature_b.md", "feature_c.md"],
  "parallel_groups": [
    {"features": ["feature_a.md", "feature_b.md"], "parallel": true},
    {"features": ["feature_c.md"], "parallel": false, "depends_on": ["feature_a.md"]}
  ],
  "coupling_warnings": []
}
```

- `parallel_groups` is ordered: groups with no intra-phase dependencies come first, followed by groups that depend on earlier groups.
- A group with a single feature has `parallel: false`. A group with 2+ independent features has `parallel: true`.
- The `depends_on` field lists features from earlier groups that this group's features transitively depend on. Omitted when the group has no intra-phase dependencies.
- The `coupling_warnings` array is populated by the implementation coupling detection system (Section 2.10).

### 2.10 Implementation Coupling Detection (Intra-Phase)

When running `--intra-phase`, the analyzer MUST additionally check for implementation-level coupling between features that are spec-independent. This detection is **advisory** — coupling warnings inform the Builder but do NOT block parallel execution. The robust merge protocol (per `subagent_parallel_builder.md` Section 2.4) is the safety net; sequential fallback occurs only when merge actually fails.

#### 2.10.1 Philosophy: Optimistic Parallelism

Spec-level dependencies (prerequisite graph) remain the only **hard gate** on parallelization. All implementation coupling signals are **soft** — they produce warnings but the analyzer still reports features as parallel. The Builder sees the warnings, proceeds with parallel execution, and relies on the merge protocol to handle conflicts. This avoids over-conservative sequentialization while giving the Builder situational awareness.

#### 2.10.2 Coupling Detection Tiers

The analyzer checks coupling signals in order from least conservative (cheapest, most permissive) to most conservative (most expensive, most likely to flag false positives). Detection stops at the first tier that reports **no coupling** for a given feature pair.

| Tier | Signal | Method | Cost |
|------|--------|--------|------|
| 1 | Spec-level dependency | Prerequisite graph (existing Section 2.9 logic) | Cheap |
| 2 | Test file source imports | Parse `tests/<feature>/tests.json` for `test_file`/`test_files`, then parse Python import statements from each test file to extract imported source modules. Two features are coupled if their imported source module sets overlap. | Moderate |
| 3 | Git commit file overlap | Find commits matching `feat(<feature_stem>)` in git log, extract the set of files modified across those commits. Two features are coupled if their modified file sets overlap. | Expensive |

**Decision logic for each feature pair:**

1. **Tier 1 — Spec dependency** (hard gate): If a prerequisite link exists between the features, they MUST be sequential. No further checks. This is existing behavior.
2. **Tier 2 — Test imports**: If both features have `tests.json` with test file references, parse the test files for Python imports (or use parent directory for shell test files) and compute the set of imported source modules for each feature. If the sets are disjoint → no coupling detected at this tier → skip Tier 3 and report parallel with no warning.
3. **Tier 3 — Git history**: If Tier 2 detected coupling (overlapping imports) or if Tier 2 could not run (no `tests.json` for one or both features), check git commit history. Find commits whose message matches `feat(<feature_stem>)` or status commits referencing the feature file. Extract the set of modified files. If the sets are disjoint → no coupling → report parallel with no warning. If overlap exists → report parallel WITH a coupling warning.

**Tier skip rule:** If Tier 2 says "no coupling" (disjoint source imports), Tier 3 is skipped entirely. The rationale: test imports are a precise signal about which source modules a feature exercises. If two features' tests don't share source modules, git history overlap (which may include incidental file touches like docs or configs) is noise.

**No-data fallback:** If a feature has no `tests.json` AND no matching git commits (never implemented), coupling detection cannot run for pairs involving that feature. The analyzer reports parallel with no coupling warning — same as current behavior.

#### 2.10.3 Source Module Extraction

For **Python test files** (`.py`):
- Parse `import` and `from ... import` statements.
- Exclude standard library modules and test framework imports (`pytest`, `unittest`, `mock`).
- Resolve relative imports against the test file's location.
- The resulting set of module file paths is the feature's **implementation surface**.

For **shell test files** (`.sh`, `.bats`):
- Use the test file's parent directory as a proxy for the implementation surface.
- All non-test files (`*` excluding `test_*`) in that directory are included in the surface.

#### 2.10.4 Output Extension

The `--intra-phase` output includes a `coupling_warnings` array at the top level:

```json
{
  "phase": 2,
  "features": ["feature_a.md", "feature_b.md"],
  "parallel_groups": [
    {"features": ["feature_a.md", "feature_b.md"], "parallel": true}
  ],
  "coupling_warnings": [
    {
      "features": ["feature_a.md", "feature_b.md"],
      "tier": 2,
      "shared_files": ["tools/critic/critic.py"],
      "detail": "test files for both features import from tools/critic/critic"
    }
  ]
}
```

- `features`: The pair of features with detected coupling.
- `tier`: Which detection tier found the coupling (2 or 3).
- `shared_files`: The list of source files or modules shared between the features.
- `detail`: Human-readable explanation of the coupling signal.

Note: `parallel_groups` still reports `parallel: true` for spec-independent features even when coupling is detected. The warnings are advisory. The Builder and merge protocol decide whether to proceed.

#### 2.10.5 Integration Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/phase_analyzer/coupling-via-imports` | Two features with test files that import from the same source module |
| `main/phase_analyzer/coupling-via-git` | Two features with git commits that modified the same file, but disjoint test imports |
| `main/phase_analyzer/no-coupling-data` | Feature with no tests.json and no matching git commits |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Analyze Delivery Plan with Correct Ordering
    Given a delivery plan with Phases 1, 2, 3 in PENDING status
    And the dependency graph shows Phase 2 features depend on Phase 1 features
    And Phase 3 features depend on Phase 2 features
    When phase_analyzer.py is run
    Then the output contains 3 groups each with one phase
    And the groups are ordered [1], [2], [3]
    And reordered is false
    And warnings is empty

#### Scenario: Detect Incorrect Phase Ordering
    Given a delivery plan with Phases 3, 4, 5, 6 in PENDING status
    And Phase 3 features depend on Phase 4 features
    And Phase 4 features depend on Phase 6 features
    When phase_analyzer.py is run
    Then reordered is true
    And the groups are reordered so Phase 6 executes first, then Phase 4, then Phase 3 and Phase 5
    And warnings contains a message about Phase 3 depending on Phase 4

#### Scenario: Group Independent Phases for Parallel Execution
    Given a delivery plan with Phases A, B, C in PENDING status
    And Phase A and Phase B have no cross-dependencies
    And Phase C depends on both Phase A and Phase B
    When phase_analyzer.py is run
    Then the first group contains Phases A and B with parallel true
    And the second group contains Phase C with parallel false

#### Scenario: All Phases Independent
    Given a delivery plan with Phases 1, 2, 3 in PENDING status
    And no features in any phase depend on features in any other phase
    When phase_analyzer.py is run
    Then the output contains 1 group with all three phases
    And parallel is true

#### Scenario: All Phases Dependent (Fully Sequential)
    Given a delivery plan with Phases 1, 2, 3 in PENDING status
    And Phase 2 depends on Phase 1
    And Phase 3 depends on Phase 2
    When phase_analyzer.py is run
    Then the output contains 3 groups each with one phase
    And parallel is false for all groups

#### Scenario: No Delivery Plan Exists
    Given .purlin/delivery_plan.md does not exist
    When phase_analyzer.py is run
    Then it prints an error to stderr
    And exits with non-zero status

#### Scenario: No Pending Phases
    Given a delivery plan exists with all phases in COMPLETE status
    When phase_analyzer.py is run
    Then the output contains an empty groups array
    And exits with zero status

#### Scenario: Feature Not in Dependency Graph
    Given a delivery plan references feature "foo.md" in Phase 1
    And "foo.md" is not present in the dependency graph
    When phase_analyzer.py is run
    Then it emits a warning to stderr about the missing feature
    And treats "foo.md" as having no dependencies
    And completes successfully

#### Scenario: Transitive Dependency Detection
    Given Phase 1 contains feature A
    And Phase 2 contains feature B
    And feature B depends on feature C which depends on feature A
    When phase_analyzer.py is run
    Then Phase 2 is placed after Phase 1 in the execution order
    And the reason references the transitive dependency chain

#### Scenario: COMPLETE and IN_PROGRESS Phases Excluded
    Given a delivery plan with Phase 1 COMPLETE, Phase 2 IN_PROGRESS, Phase 3 PENDING
    When phase_analyzer.py is run
    Then only Phase 3 appears in the output groups
    And Phase 1 and Phase 2 are excluded from analysis

#### Scenario: Submodule Path Resolution
    Given PURLIN_PROJECT_ROOT is set to a consumer project root
    And the delivery plan and dependency graph are at the consumer project paths
    When phase_analyzer.py is run
    Then it reads files relative to PURLIN_PROJECT_ROOT
    And does not assume CWD or hardcode framework paths

#### Scenario: Intra-Phase Two Independent Features
    Given Phase 2 contains feature_a.md and feature_b.md
    And no transitive dependency exists between them
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups contains one group with both features and parallel true

#### Scenario: Intra-Phase Two Dependent Features
    Given Phase 2 contains feature_a.md and feature_b.md
    And feature_b.md transitively depends on feature_a.md
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups contains two sequential groups

#### Scenario: Intra-Phase Mixed Independence
    Given Phase 3 contains feature_a.md, feature_b.md, feature_c.md
    And feature_a.md and feature_b.md are independent
    And feature_c.md depends on feature_a.md
    When phase_analyzer.py --intra-phase 3 is run
    Then the first group is parallel with feature_a.md and feature_b.md
    And the second group is sequential with feature_c.md

#### Scenario: Intra-Phase Non-Existent Phase
    Given the delivery plan has Phases 1 and 2 only
    When phase_analyzer.py --intra-phase 5 is run
    Then an error is printed to stderr and exit status is 1

#### Scenario: Intra-Phase Single Feature
    Given Phase 1 contains only feature_a.md
    When phase_analyzer.py --intra-phase 1 is run
    Then parallel_groups contains one group with parallel false

#### Scenario: Coupling detected via shared test imports (Tier 2)
    Given Phase 2 contains feature_a.md and feature_b.md
    And no transitive spec dependency exists between them
    And tests/feature_a/tests.json has test_file "tools/critic/test_a.py"
    And tests/feature_b/tests.json has test_file "tools/critic/test_b.py"
    And both test files import from "tools/critic/critic.py"
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups reports both features as parallel true
    And coupling_warnings contains one entry with tier 2
    And shared_files includes "tools/critic/critic.py"

#### Scenario: No coupling when test imports are disjoint
    Given Phase 2 contains feature_a.md and feature_b.md
    And tests/feature_a/tests.json has test_file "tools/critic/test_a.py" importing "tools/critic/critic.py"
    And tests/feature_b/tests.json has test_file "tools/cdd/test_b.py" importing "tools/cdd/monitor.py"
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups reports both features as parallel true
    And coupling_warnings is empty

#### Scenario: Tier 2 no-coupling skips Tier 3 entirely
    Given Phase 2 contains feature_a.md and feature_b.md
    And their test file imports are disjoint (Tier 2 says no coupling)
    And their git commit histories overlap on a shared config file
    When phase_analyzer.py --intra-phase 2 is run
    Then coupling_warnings is empty
    And Tier 3 git analysis was not performed

#### Scenario: Coupling detected via git history (Tier 3) when no tests exist
    Given Phase 2 contains feature_a.md and feature_b.md
    And neither feature has a tests.json file
    And git log contains commits "feat(feature_a): ..." modifying tools/shared/utils.py
    And git log contains commits "feat(feature_b): ..." also modifying tools/shared/utils.py
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups reports both features as parallel true
    And coupling_warnings contains one entry with tier 3
    And shared_files includes "tools/shared/utils.py"

#### Scenario: Coupling via git history when Tier 2 detects overlap
    Given Phase 2 contains feature_a.md and feature_b.md
    And both features have test files importing from the same source module
    When phase_analyzer.py --intra-phase 2 is run
    Then Tier 3 is also checked for additional context
    And coupling_warnings contains an entry with the highest-signal tier

#### Scenario: No coupling data available for never-implemented feature
    Given Phase 2 contains feature_a.md and feature_b.md
    And feature_a.md has no tests.json and no matching git commits
    And feature_b.md has tests.json with test imports
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups reports both features as parallel true
    And coupling_warnings is empty

#### Scenario: Shell test files use directory proximity for surface detection
    Given Phase 2 contains feature_a.md and feature_b.md
    And feature_a.md has test_file "tools/release/test_a.sh"
    And feature_b.md has test_file "tools/release/test_b.sh"
    When phase_analyzer.py --intra-phase 2 is run
    Then the implementation surface for both features includes non-test files in tools/release/
    And coupling_warnings contains an entry if they share that directory

#### Scenario: Coupling warnings do not change parallel grouping
    Given Phase 2 contains feature_a.md, feature_b.md, feature_c.md
    And all three are spec-independent
    And feature_a.md and feature_b.md have Tier 2 coupling (shared imports)
    And feature_c.md has no coupling with either
    When phase_analyzer.py --intra-phase 2 is run
    Then parallel_groups contains one group with all three features and parallel true
    And coupling_warnings contains one entry for feature_a.md and feature_b.md
    And feature_c.md does not appear in any coupling warning

### QA Scenarios

None.

## Regression Guidance
- Cycle detection: dependency cycles produce error exit, not silent misordering
- Parallel grouping: only truly independent phases grouped together
- PURLIN_PROJECT_ROOT used for path resolution (submodule safe)
- Only PENDING phases included; COMPLETE and IN_PROGRESS excluded
- Empty plan (no PENDING phases) exits successfully with empty groups
- Coupling warnings are advisory only — they never change parallel_groups decisions
