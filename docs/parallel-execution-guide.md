# Parallel Execution Guide

How the agent delivers features faster using pipeline parallelism and git worktrees.

---

## When It Happens

When a work plan has multiple features, the agent runs them through a **pipeline** where each feature independently progresses through PM → Engineer → QA stages. Features at different stages run simultaneously in separate git worktrees — so a PM sub-agent can be writing a spec while an Engineer sub-agent builds a different feature and a QA sub-agent verifies a third.

This kicks in automatically during `purlin:build` when a work plan (`.purlin/work_plan.md`) exists with 2+ features.

---

## How It Works

1. The agent reads the work plan and dependency graph.
2. For each feature, it determines the next pipeline stage (PM → Engineer → QA).
3. It dispatches **sub-agents** to available worktree slots (up to 3 concurrent by default).
4. Each sub-agent works in an isolated worktree:
   - `pm-worker` — writes or refines a feature spec
   - `engineer-worker` — implements a feature (Steps 0-2)
   - `qa-worker` — verifies a feature (Phase A)
5. Completed branches merge back to the main branch sequentially.
6. The agent updates the work plan and dispatches the next batch of work.
7. When all features in a **verification group** finish building, cross-feature regression testing (B2) runs.

### Why Cross-Mode Parallelism Is Safe

PM writes specs (`features/*.md`). Engineer writes code and companions (`*.impl.md`). QA writes discoveries (`*.discoveries.md`). These are **disjoint file sets** — they literally cannot create merge conflicts with each other. The only shared files (work plan, cache) are auto-resolved during merge.

### Independence Checks

The agent uses the prerequisite graph to determine which features can be parallel. If Feature A declares a dependency on Feature B, B's Engineer stage waits for A's Engineer stage to complete. PM stages can proceed in parallel since specs define interfaces, not implementations.

The approach is optimistic: parallel first, sequential fallback only if merge actually conflicts on source files.

### Verification Groups

Features that share interaction surface (data models, APIs, UI components) are grouped together. Cross-feature regression testing (B2) runs when **all features in a group** complete their Engineer stage. This catches regressions between related features without waiting for the entire plan to finish.

### Merge Protocol

After sub-agents complete, branches merge one at a time:

- **Safe file conflicts** (work plan, cache files) — auto-resolved by keeping main's version.
- **Source file conflicts** — the conflicting feature falls back to sequential rebuild. Already-merged features are preserved.

---

## The Pipeline in Action

With 5 features and 3 worktree slots, a typical pipeline looks like:

```
Time →
Slot 1: [Eng: feature_a] ──────────────→ [Eng: feature_d] ──→
Slot 2: [QA: feature_b]  ───→ [Eng: feature_c] ────────────→
Slot 3: [PM: feature_e]  ───→ [QA: feature_a]  ────────────→
Main:   orchestrating...      [B2: auth group]  orchestrating...
```

Three workers active simultaneously, each on a different feature. The orchestrator merges completed work and dispatches the next feature as slots open up.

---

## Quick Reference

| Situation | What Happens |
|-----------|--------------|
| 1 feature | Sequential build in main session (no parallelism needed). |
| 2+ features, no dependencies | Pipeline with cross-mode sub-agents in worktrees. |
| 2+ features, some dependent | Independent ones parallel, dependent ones wait. |
| Features sharing data models | Grouped into a verification group; B2 runs after all complete. |
| Source file merge conflict | That feature rebuilds sequentially; others preserved. |
| `auto_start: true` | Full pipeline runs without pausing at verification checkpoints. |
| `auto_start: false` (default) | Pauses at verification checkpoints for user review. |

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `max_concurrent_worktrees` | 3 | Maximum simultaneous sub-agent worktrees. |
| `auto_start` | false | Whether to pause at verification checkpoints. |

Set in `.purlin/config.json` under `agents.purlin`.
