# Parallel Execution Guide

How the agent builds independent features simultaneously using git worktrees.

---

## When It Happens

When a delivery plan has multiple pending features that don't depend on each other, Engineer mode can build them in parallel. Each feature gets its own isolated copy of the repository (a git worktree), so parallel builds don't interfere with each other.

This kicks in automatically during `/pl-build` when the delivery plan has 2+ independent features in the same phase.

---

## How It Works

1. The agent reads the delivery plan and dependency graph.
2. It groups pending phases that have no cross-dependencies into **execution groups**.
3. For each group, it spawns one sub-agent per independent feature, each in its own worktree.
4. Sub-agents implement their features (pre-flight, plan, implement) and commit to their worktree branches.
5. Branches merge back to the main branch sequentially.
6. The agent runs cross-feature verification to catch regressions.

### Independence Checks

The agent uses the prerequisite graph to determine which features can be parallel. If Feature A declares a dependency on Feature B, they must be built sequentially. Features without spec-level dependencies are treated as independent.

The approach is optimistic: parallel first, sequential fallback only if merge actually conflicts on source files.

### Merge Protocol

After parallel builds complete, branches merge one at a time:

- **Safe file conflicts** (delivery plan, cache files) — auto-resolved, merge continues.
- **Source file conflicts** — the conflicting feature falls back to sequential rebuild. Already-merged features are preserved.

---

## Quick Reference

| Situation | What Happens |
|-----------|--------------|
| 1 feature pending | Sequential build (no parallelism needed). |
| 2+ features, no dependencies | Parallel build via worktree sub-agents. |
| 2+ features, some dependent | Independent ones parallel, dependent ones sequential. |
| Source file merge conflict | That feature rebuilds sequentially; others preserved. |
