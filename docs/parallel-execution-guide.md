# Parallel Execution in the Builder

How the Builder parallelizes feature implementation within a delivery plan phase.

---

## When It Happens

When a delivery plan phase has 2+ features, the Builder runs the phase analyzer before starting any implementation:

```
python3 tools/delivery/phase_analyzer.py --intra-phase <phase_number>
```

If the analyzer returns a `parallel: true` group, the Builder spawns one `builder-worker` sub-agent per feature in that group. Each worker runs in an isolated git worktree.

---

## Independence Checks

The analyzer uses a tiered system to assess whether features can be built in parallel.

### Tier 1: Spec-Level Dependencies (Hard Gate)

Checks the prerequisite graph (`dependency_graph.json`). If Feature A declares `> Prerequisite: features/feature_b.md`, they must be sequential. This is the only tier that **blocks** parallelism.

### Tier 2: Test File Import Overlap (Soft Signal)

Reads `tests/<feature>/tests.json` to find each feature's test files, then parses Python imports to determine which source modules the tests exercise. If two features' test files both import from the same source module (e.g., both test `tools/critic/critic.py`), a **coupling warning** is emitted.

- Checked first among soft signals (cheapest, most precise).
- If no overlap is found, Tier 3 is skipped entirely.

### Tier 3: Git Commit File Overlap (Soft Signal)

Searches `git log` for commits matching `feat(<feature_stem>)` and compares the sets of files modified. If two features' prior commits touched the same files, a coupling warning is emitted.

- Only runs when Tier 2 detected overlap or couldn't run (no `tests.json`).
- More conservative than Tier 2; may flag incidental shared files (docs, configs).

### Key Principle: Optimistic Parallelism

Coupling warnings are **advisory only**. They never change the `parallel: true` grouping. The Builder sees the warnings, proceeds with parallel execution, and relies on the merge protocol to handle any resulting conflicts. Sequential fallback happens only when merge actually fails -- not when coupling is predicted.

---

## Execution Flow

```
1. Builder enters a multi-feature phase
2. Runs phase_analyzer.py --intra-phase N
3. For each parallel group:
   a. Spawns one builder-worker per feature (isolated worktree)
   b. Each worker runs Steps 0-2 (pre-flight, plan, implement)
   c. Workers commit to their worktree branches
4. Merges branches back using the robust merge protocol
5. Proceeds to verification (B2)
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

## Coupling Warnings in Practice

The analyzer output includes a `coupling_warnings` array:

```json
{
  "coupling_warnings": [
    {
      "features": ["qa_verification_effort.md", "critic_role_status.md"],
      "tier": 2,
      "shared_files": ["tools/critic/critic.py"],
      "detail": "test files for both features import from tools/critic/critic"
    }
  ]
}
```

When the Builder sees coupling warnings, it still proceeds with parallel execution. The warning serves as a heads-up that merge conflicts are likely. If the merge protocol encounters unsafe conflicts on the shared files, it falls back to sequential for the affected feature -- no manual intervention needed.

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
| Phase has 1 feature | Sequential build (no analyzer needed) |
| Phase has 2+ features, all spec-independent | Parallel build with coupling warnings if applicable |
| Phase has 2+ features, some spec-dependent | Mixed: independent features parallel, dependent features sequential |
| Coupling warning emitted | Parallel proceeds anyway; merge protocol is safety net |
| Merge conflict on source file | Sequential fallback for that feature only |
| Merge conflict on safe file | Auto-resolved, parallel continues |
