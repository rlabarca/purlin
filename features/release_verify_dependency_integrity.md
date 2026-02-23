# Feature: Purlin Verify Dependency Integrity

> Label: "Release Step: Purlin Verify Dependency Integrity"
> Category: "Release Process"
> Prerequisite: features/policy_release.md
> Prerequisite: features/release_checklist_core.md

## 1. Overview

This feature defines the `purlin.verify_dependency_integrity` release step: a structural validation that confirms the feature dependency graph is acyclic and all `> Prerequisite:` links resolve to existing feature files. A corrupted or cyclic graph can silently mask feature ordering issues and incorrect cascade behavior across the CDD lifecycle.

## 2. Requirements

### 2.1 Graph File Check

The Architect reads `.purlin/cache/dependency_graph.json`. If the file is absent or its modification time predates the most recently modified feature file, the Architect runs `tools/cdd/status.sh --graph` to regenerate it before proceeding.

### 2.2 Cycle Detection

The Architect inspects the dependency graph for cycles. A cycle exists when a chain of `Prerequisite:` links eventually returns to a node already visited. Any cycle found is a CRITICAL error and MUST halt the release.

### 2.3 Broken Link Detection

For each `> Prerequisite:` link in the graph, the Architect confirms the referenced file exists in `features/`. A link to a non-existent file is a broken link. Any broken link MUST be reported and blocks the release until corrected.

### 2.4 Pass Condition

The graph is valid when: (1) no cycles are detected, and (2) all prerequisite links resolve. The Architect reports the total node count and confirms graph integrity before proceeding to the next step. No files are modified (regenerating the cache file is not a modification to spec state).

### 2.5 Step Metadata

| Field | Value |
|-------|-------|
| ID | `purlin.verify_dependency_integrity` |
| Friendly Name | `Purlin Verify Dependency Integrity` |
| Code | null |
| Agent Instructions | "Read `.purlin/cache/dependency_graph.json`. Confirm the graph is acyclic and all prerequisite references resolve to existing feature files. If the file is stale or missing, run `tools/cdd/status.sh --graph` to regenerate it. Report any cycles or broken links." |

## 3. Scenarios

### Automated Scenarios
None. All verification is manual (Architect-executed release step).

### Manual Scenarios (Architect Execution)

#### Scenario: Graph is current and valid
Given `.purlin/cache/dependency_graph.json` is up to date and contains no cycles or broken links,
When the Architect executes the `purlin.verify_dependency_integrity` step,
Then the Architect reports the total node count and confirms graph integrity,
And proceeds to the next release step.

#### Scenario: Graph file is stale or absent
Given `.purlin/cache/dependency_graph.json` is missing or older than the most recently modified feature file,
When the Architect executes the `purlin.verify_dependency_integrity` step,
Then the Architect runs `tools/cdd/status.sh --graph` to regenerate the cache file,
And proceeds with the freshly generated graph.

#### Scenario: Cycle detected in dependency graph
Given a chain of `> Prerequisite:` links forms a cycle in the feature graph,
When the Architect executes the `purlin.verify_dependency_integrity` step,
Then the Architect reports the specific cycle path (list of feature files forming the cycle),
And halts the release until the cycle is broken.

#### Scenario: Broken prerequisite link detected
Given a feature file declares a `> Prerequisite:` link to a file that does not exist in `features/`,
When the Architect executes the `purlin.verify_dependency_integrity` step,
Then the Architect reports the specific broken link (source file and missing target path),
And halts the release until the link is corrected.

## Implementation Notes

This step is a structural read-only check. The Architect does not modify feature files as part of this step. Regenerating the dependency cache via `tools/cdd/status.sh --graph` is permissible and does not count as a spec modification.

The dependency graph is computed and cached by `tools/cdd/status.sh --graph`. Manual graph file edits are not supported; the cache is always regenerated from source feature files.
