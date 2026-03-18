# Feature: Phase Analyzer

> Label: "Tool: Phase Analyzer"
> Category: "Install, Update & Scripts"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A dependency-aware analysis tool (`tools/delivery/phase_analyzer.py`) that reads the delivery plan and dependency graph to determine correct phase execution order and identify parallelization opportunities. The tool detects when phases are ordered incorrectly relative to their feature dependencies, computes a topologically-sorted execution order, and groups independent phases into parallel execution sets. Output is structured JSON to stdout, suitable for consumption by the continuous phase builder orchestration loop.

---

## 2. Requirements

### 2.1 Inputs

- **Delivery plan:** Read from `.purlin/cache/delivery_plan.md`. Extract PENDING phases and their feature lists.
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
  ]
}
```

- `parallel_groups` is ordered: groups with no intra-phase dependencies come first, followed by groups that depend on earlier groups.
- A group with a single feature has `parallel: false`. A group with 2+ independent features has `parallel: true`.
- The `depends_on` field lists features from earlier groups that this group's features transitively depend on. Omitted when the group has no intra-phase dependencies.

---

## 3. Scenarios

### Automated Scenarios

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
    Given .purlin/cache/delivery_plan.md does not exist
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

### Manual Scenarios (Human Verification Required)
None.
