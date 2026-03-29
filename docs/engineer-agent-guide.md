# Engineer Mode Guide

How to use Engineer mode to implement features, write tests, and manage delivery.

---

## What Engineer Mode Does

Engineer mode reads feature specs and turns them into working code, tests, and scripts. It's the only mode that writes implementation files.

Engineer mode:

- Implements features by reading specs from `features/` and writing code.
- Writes automated tests against a quality rubric.
- Runs visual verification via Playwright for web features.
- Documents implementation decisions in companion files when it deviates from a spec.
- Manages phased delivery for large-scope work across multiple features.
- Never writes specs. If it finds a gap, it records a finding — it doesn't edit the spec.

### Entering Engineer Mode

From any session:

```
purlin:mode engineer
```

Or run an Engineer skill directly — `purlin:build`, `purlin:unit-test`, and `purlin:delivery-plan` all activate Engineer mode automatically.

At startup, Engineer mode checks for TODO features and proposes a work plan. You approve, and it begins.

---

## The Build Workflow

When implementing a feature, the agent follows four steps.

### Step 0 — Pre-Flight

Before writing code, the agent:

- Reads the companion file (`features/<name>.impl.md`) for prior decisions.
- Checks anchor node constraints (forbidden patterns, invariants).
- Loads visual design sources if the feature has a Visual Specification — reads the Token Map and checks `brief.json` staleness. See the [Design Guide](design-guide.md) for details.
- Detects whether this is new work or re-verification of existing code.

### Step 1 — Plan

States which feature it's implementing and outlines the approach, referencing any relevant companion file notes and anchor constraints.

### Step 2 — Implement

Writes code and tests. When it makes a decision the spec doesn't cover, it records it in the companion file:

| Tag | When Used |
|-----|-----------|
| `[CLARIFICATION]` | Interpreted ambiguous spec language. |
| `[AUTONOMOUS]` | Spec was silent — filled the gap with judgment. |
| `[DEVIATION]` | Intentionally diverged from spec. |
| `[DISCOVERY]` | Found an unstated requirement. |
| `[INFEASIBLE]` | Cannot implement as specified — halts work. |

HIGH and CRITICAL tags show up as PM action items in `purlin:status`.

### Step 3 — Verify

Runs `purlin:unit-test` to check tests against the quality rubric. For features with visual specs, runs `purlin:web-test` via Playwright.

### Step 4 — Status Tag

A separate commit marks the feature's state:

- **`[Complete]`** — All tests pass, no manual verification needed. QA never sees this feature.
- **`[Ready for Verification]`** — Has QA scenarios that need manual or automated verification. QA picks it up.

---

## Unit Testing

`purlin:unit-test` runs tests and checks them against a quality rubric. Every test must:

1. **Fail if the implementation is deleted** — tests that pass without their code are worthless.
2. **Actually call the implementation** — no reading source files and checking strings.
3. **Assert specific values** — not just that something exists or has the right type.
4. **Use realistic inputs** — not empty strings or single items.
5. **Only mock external dependencies** — network, filesystem, not the code under test.

Test results land in `tests/<feature>/tests.json`.

---

## Web Testing

For features with a Visual Specification section and `> Web Test:` metadata:

```
purlin:web-test feature-name
```

This uses Playwright to navigate to the feature's URL and check each visual checklist item against the running app — CSS values, layout, content. The agent iterates until all items pass before committing the status tag. Token Map entries are verified against computed styles: use `var(--purlin-accent)` not hardcoded hex values.

---

## Work Plans and Pipeline Delivery

When multiple features need implementation, the agent creates a work plan and delivers features through a pipeline.

```
purlin:delivery-plan
```

The work plan is a flat, priority-ordered list of features — no numbered phases or sizing caps. Each feature independently progresses through PM → Engineer → QA stages. Independent features at different stages run in parallel via cross-mode sub-agents in isolated worktrees.

Features that share interaction surface (data models, APIs, UI components) are grouped into **verification groups**. When all features in a group finish building, cross-feature regression testing runs:

- **B1 (Build)** — Implement and test each feature (runs per-feature, potentially in parallel).
- **B2 (Test)** — Re-run tests across all verification group features to catch regressions.
- **B3 (Fix)** — Diagnose and fix any cross-feature failures.

See the [Parallel Execution Guide](parallel-execution-guide.md) for details on cross-mode parallelism.

---

## Companion Files

The agent creates `features/<name>.impl.md` alongside the spec to document implementation decisions. This is the durable communication channel between Engineer and PM.

**What goes in:** Decision tags with rationale, test quality results, visual verification results.

**What doesn't:** The implementation itself (that's in the code), spec content (that's in the feature file), or temporary debugging notes.

---

## Communicating with PM Mode

Engineer mode has three ways to flag issues for PM:

| Situation | What to Do |
|-----------|------------|
| Spec is impossible to implement | `purlin:infeasible feature-name` — halts work, creates a critical escalation. |
| Implementation differs from spec | Record a `[DEVIATION]` in the companion file — PM reviews it. |
| Spec should change | `purlin:propose topic` — suggests a spec change for PM to evaluate. |

---

## Day-to-Day Commands

| Command | What It Does |
|---------|--------------|
| `purlin:build [name]` | Implement features following the build protocol. |
| `purlin:unit-test [name]` | Run unit tests with the quality rubric. |
| `purlin:web-test [name]` | Visual verification via Playwright. |
| `purlin:delivery-plan` | Create or review a pipeline work plan. |
| `purlin:infeasible <name>` | Escalate a feature that can't be built as specified. |
| `purlin:propose <topic>` | Suggest a spec change to PM. |
| `purlin:spec-code-audit [--deep]` | Audit alignment between specs and code. `--deep` runs parallel bidirectional analysis. |
| `purlin:spec-from-code` | Reverse-engineer feature specs from existing code. |
| `purlin:tombstone <feature>` | Retire a feature with a tombstone record. |
| `purlin:server` | Start, stop, or restart the dev server for web testing. |
| `purlin:status` | Check feature states and what needs building. |
| `purlin:find <topic>` | Search specs for a topic. |
| `purlin:help` | Full command list for Engineer mode. |
