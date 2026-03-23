# Parallel Execution in the Builder

How the Builder parallelizes feature implementation within a delivery plan phase.

---

## When It Happens

When a delivery plan phase (or execution group) has 2+ independent features, the Builder determines independence by reading `.purlin/cache/dependency_graph.json` and checking pairwise dependencies between features. If no cross-dependencies exist, the Builder spawns one `builder-worker` sub-agent per feature in the independent set. Each worker runs in an isolated git worktree.

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
1. Builder enters a multi-feature phase (or execution group)
2. Reads dependency_graph.json and delivery plan
3. Computes pairwise independence for features in the group
4. For each set of independent features (2+):
   a. Spawns one builder-worker sub-agent per feature (isolated worktree)
   b. Each worker runs Steps 0-2 (pre-flight, plan, implement)
   c. Workers commit to their worktree branches
5. Merges branches back using the robust merge protocol
6. Proceeds to verification (B2)
```

---

## Merge Protocol

After parallel workers complete, branches are merged sequentially using rebase-before-merge:

1. For each worker branch: `git rebase HEAD <branch>`
2. On conflict, check if all conflicting files are **safe files** (delivery plan, critic report, cache files).
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
| Phase has 1 feature | Sequential build (no independence check needed) |
| Phase has 2+ features, all spec-independent | Parallel build via builder-worker sub-agents |
| Phase has 2+ features, some spec-dependent | Mixed: independent features parallel, dependent features sequential |
| Merge conflict on source file | Sequential fallback for that feature only |
| Merge conflict on safe file | Auto-resolved, parallel continues |
