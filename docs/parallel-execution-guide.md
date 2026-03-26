# Parallel Execution in the Builder

How the Builder parallelizes feature implementation across delivery plan phases using execution groups.

---

## When It Happens

When a delivery plan has PENDING phases, the Builder forms **execution groups** -- sets of phases with no cross-dependencies that can be scheduled together. Within each execution group, independent features are dispatched to parallel sub-agents.

The Builder reads `.purlin/cache/dependency_graph.json` and the delivery plan to determine which phases can be grouped and which features within a group are independent. If no cross-dependencies exist between features, the Builder spawns one `builder-worker` sub-agent per feature. Each worker runs in an isolated git worktree.

---

## Execution Groups

Phases are authoring units; execution groups are scheduling units. The Builder forms groups by checking whether any feature in one PENDING phase depends (transitively) on any feature in another PENDING phase. Phases with no cross-dependencies are combined into a single execution group.

For example, if Phases 2 and 3 are both PENDING and share no feature dependencies, they form one execution group. All features across both phases are collected and dispatched together.

Individual phases within a group complete independently. If one phase's features all pass while another has a stuck feature, the completed phase is marked COMPLETE and QA can verify it immediately. The incomplete phase becomes a singleton group on the next session.

When the entire execution group is complete, the Builder checks `auto_start`:
- **`auto_start: false` (default):** The Builder stops the session and recommends running QA to verify completed phases, then relaunching Builder for the next group.
- **`auto_start: true`:** The Builder auto-advances to the next execution group.

If a delivery plan has only 1 PENDING phase with 1 feature, the Builder skips group analysis and uses the sequential per-feature loop directly.

---

## Independence Checks

The Builder uses the prerequisite graph in `dependency_graph.json` to assess whether features can be built in parallel.

### Spec-Level Dependencies (Hard Gate)

Checks the prerequisite graph (`dependency_graph.json`). If Feature A declares `> Prerequisite: features/feature_b.md`, they must be sequential. This is the only check that **blocks** parallelism.

### Key Principle: Optimistic Parallelism

Features without spec-level cross-dependencies are treated as independent. The Builder proceeds with parallel execution and relies on the merge protocol to handle any resulting conflicts. Sequential fallback happens only when merge actually fails -- not when coupling is predicted.

---

## Execution Flow

```
1. Builder reads dependency_graph.json and delivery plan
2. Groups PENDING phases by cross-dependency analysis (execution groups)
3. Identifies the active execution group (first group with non-COMPLETE phases)
4. Marks all phases in the group as IN_PROGRESS
5. Collects all features across all member phases
6. Checks pairwise feature independence within the group
7. For each set of independent features (2+):
   a. Spawns one builder-worker sub-agent per feature (isolated worktree)
   b. Each worker runs Steps 0-2 (pre-flight, plan, implement)
   c. Workers commit to their worktree branches
8. Merges branches back using the robust merge protocol
9. Runs verification (B2) across all group features
```

---

## Merge Protocol

After parallel workers complete, branches are merged sequentially using rebase-before-merge:

1. For each worker branch: `git rebase HEAD <branch>`
2. On conflict, check if all conflicting files are **safe files** (delivery plan, cache files).
   - Safe conflict: auto-resolve with `git checkout --ours`, continue rebase.
   - Unsafe conflict: abort rebase, fall back to **sequential rebuild** for that feature only.
3. After rebase: fast-forward merge.
4. Already-merged features are preserved -- only the conflicting feature rebuilds sequentially.

---

## Sub-Agent Constraints

| Agent | Runs | Cannot |
|-------|------|--------|
| `builder-worker` | Steps 0-2, single feature, isolated worktree | Run Step 3/4, modify delivery plan, spawn nested agents |
| `verification-runner` | `/pl-unit-test`, writes `tests.json` | Edit implementation files, spawn agents |

---

## Quick Reference

| Situation | What Happens |
|-----------|--------------|
| 1 PENDING phase, 1 feature | Sequential build (no group analysis needed) |
| 2+ PENDING phases, no cross-dependencies | Phases grouped into one execution group, features dispatched in parallel |
| 2+ PENDING phases, some cross-dependent | Independent phases grouped; dependent phases form separate groups |
| Group has 2+ features, all spec-independent | Parallel build via builder-worker sub-agents |
| Group has 2+ features, some spec-dependent | Mixed: independent features parallel, dependent features sequential |
| Merge conflict on source file | Sequential fallback for that feature only |
| Merge conflict on safe file | Auto-resolved, parallel continues |
| Execution group complete, `auto_start: false` | Builder stops, recommends QA then relaunch |
| Execution group complete, `auto_start: true` | Builder auto-advances to next group |
