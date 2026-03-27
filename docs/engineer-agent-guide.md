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
/pl-mode engineer
```

Or run an Engineer skill directly — `/pl-build`, `/pl-unit-test`, and `/pl-delivery-plan` all activate Engineer mode automatically.

At startup, Engineer mode checks for TODO features and proposes a work plan. You approve, and it begins.

---

## The Build Workflow

When implementing a feature, the agent follows four steps.

### Step 0 — Pre-Flight

Before writing code, the agent:

- Reads the companion file (`features/<name>.impl.md`) for prior decisions.
- Checks anchor node constraints (forbidden patterns, invariants).
- Loads visual design sources if the feature has a Visual Specification.
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

HIGH and CRITICAL tags show up as PM action items in `/pl-status`.

### Step 3 — Verify

Runs `/pl-unit-test` to check tests against the quality rubric. For features with visual specs, runs `/pl-web-test` via Playwright.

### Step 4 — Status Tag

A separate commit marks the feature's state:

- **`[Complete]`** — All tests pass, no manual verification needed. QA never sees this feature.
- **`[Ready for Verification]`** — Has QA scenarios that need manual or automated verification. QA picks it up.

---

## Unit Testing

`/pl-unit-test` runs tests and checks them against a quality rubric. Every test must:

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
/pl-web-test feature-name
```

This uses Playwright to navigate to the feature's URL and check each visual checklist item against the running app — CSS values, layout, content. The agent iterates until all items pass before committing the status tag.

---

## Delivery Plans

When multiple features need implementation, the agent organizes work into phases.

```
/pl-delivery-plan
```

Phasing kicks in when there are 2+ high-complexity features, 3+ features of any mix, or a single feature with 5+ scenarios.

Each phase groups related features and follows three sub-phases:

- **Build** — Implement and test each feature.
- **Test** — Re-run tests across all phase features to catch regressions.
- **Fix** — Diagnose and fix any cross-feature failures.

When a phase has independent features (no dependencies on each other), the agent can build them in parallel using isolated git worktrees. See the [Parallel Execution Guide](parallel-execution-guide.md) for details.

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
| Spec is impossible to implement | `/pl-infeasible feature-name` — halts work, creates a critical escalation. |
| Implementation differs from spec | Record a `[DEVIATION]` in the companion file — PM reviews it. |
| Spec should change | `/pl-propose topic` — suggests a spec change for PM to evaluate. |

---

## Day-to-Day Commands

| Command | What It Does |
|---------|--------------|
| `/pl-build [name]` | Implement features following the build protocol. |
| `/pl-unit-test [name]` | Run unit tests with the quality rubric. |
| `/pl-web-test [name]` | Visual verification via Playwright. |
| `/pl-delivery-plan` | Create or review a phased delivery plan. |
| `/pl-infeasible <name>` | Escalate a feature that can't be built as specified. |
| `/pl-propose <topic>` | Suggest a spec change to PM. |
| `/pl-spec-code-audit` | Audit alignment between specs and code. Detects circular dependencies. |
| `/pl-status` | Check feature states and what needs building. |
| `/pl-find <topic>` | Search specs for a topic. |
| `/pl-help` | Full command list for Engineer mode. |
