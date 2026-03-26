# Builder Agent Guide

A practical guide for using the Builder agent in Purlin.

---

## 1. Overview

The Builder is Purlin's implementation agent. It reads feature specs and translates them into working code, tests, and scripts. The Builder is the sole author of all implementation artifacts in the project.

The Builder agent:

- **Implements features** by reading specs from `features/` and writing code.
- **Writes automated tests** with a rigorous quality rubric (6 checks, 5 anti-pattern scans).
- **Runs web tests** via Playwright for features with visual specifications.
- **Documents decisions** in companion files when it deviates from or extends a spec.
- **Manages phased delivery** for large-scope work across multiple features.
- **Never writes specs.** Feature files, anchor nodes, and instruction files belong to the Architect and PM. If the Builder finds a spec gap, it records a discovery -- it does not edit the spec.

The Builder discovers its own work. At startup, it identifies features in TODO state and proposes an implementation plan. You approve, and it begins.

---

## 2. Getting Started

### Launching a Builder Session

```bash
./pl-run-builder.sh
```

### What Happens at Startup

The Builder prints a command table, then checks its startup configuration:

- **Find Work only** (default): The Builder identifies TODO features, proposes a delivery plan if needed, and waits for your approval before starting.
- **Find Work + Auto Start**: The Builder proposes a work plan and begins implementing immediately without waiting for approval.
- **Find Work disabled**: The Builder waits for your direct instruction.

---

## 3. The Build Workflow

When the Builder implements a feature, it follows a four-step protocol.

### Step 0 -- Pre-Flight

Before writing any code, the Builder:

1. Reads the companion file (`features/<name>.impl.md`) if one exists, to understand prior implementation decisions.
2. Checks anchor node constraints (FORBIDDEN patterns and invariants).
3. Reads visual design sources: Token Map from the spec, then `brief.json`, then Figma MCP as a last resort.
4. Checks Playwright MCP availability for features with web test metadata.
5. Detects whether this is new work or re-verification of existing code.

### Step 1 -- Plan

The Builder states which feature it is implementing and outlines its approach, referencing companion file notes and anchor constraints.

### Step 2 -- Implement

The Builder writes code and tests, then documents any non-obvious decisions in the companion file using structured tags:

| Tag | Severity | When to Use |
|-----|----------|-------------|
| `[CLARIFICATION]` | INFO | Interpreted ambiguous spec language |
| `[AUTONOMOUS]` | WARN | Spec was silent; filled the gap with judgment |
| `[DEVIATION]` | HIGH | Intentionally diverged from spec (blocks completion) |
| `[DISCOVERY]` | HIGH | Found an unstated requirement (blocks completion) |
| `[INFEASIBLE]` | CRITICAL | Cannot implement as specified; halts work |
| `[SPEC_PROPOSAL]` | HIGH | Proposes a new anchor node or spec change |

HIGH and CRITICAL tags route to the Architect as action items.

### Step 3 -- Verify

The Builder runs `/pl-unit-test` to execute tests against a quality rubric. For features with visual specifications and web test metadata, it also runs `/pl-web-test` via Playwright.

### Step 4 -- Status Tag

A separate commit (never bundled with implementation) that marks the feature's lifecycle state:

- **`[Complete]`** -- All scenarios are unit tests, all pass, no manual verification needed. QA never sees this feature.
- **`[Ready for Verification]`** -- The feature has QA scenarios that require manual verification. QA picks it up next.

Each tag includes a scope declaration that tells QA how much re-testing is needed:

| Scope | Meaning |
|-------|---------|
| `full` | Behavioral change or new scenarios -- test everything |
| `targeted:A,B` | Only specific scenarios affected |
| `cosmetic` | Non-functional change -- skip QA if prior clean pass exists |
| `dependency-only` | Prerequisite update -- test only affected scenarios |

---

## 4. Unit Testing

The Builder runs `/pl-unit-test` which enforces a strict quality rubric.

### The 6-Point Quality Gate

Every test must pass all six checks:

1. **Deletion test** -- If the implementation were deleted, would the test fail?
2. **Behavioral verification** -- Does the test import, call, or execute the implementation?
3. **Value assertions** -- Does every test have at least one value-verifying assertion?
4. **Anti-pattern free** -- Does every test pass all 5 anti-pattern checks?
5. **Representative inputs** -- Do tests use realistic data, not empty strings or single items?
6. **No self-mocking** -- Are mocks limited to external dependencies (network, filesystem)?

### 5 Anti-Patterns to Avoid

| Pattern | Bad | Good |
|---------|-----|------|
| Prose inspection | Read a `.md` file, check for string | Import and call implementation |
| Structural presence | Assert a key exists | Assert the key's specific value |
| Mock-dominated | Mock the code under test | Execute real code with controlled inputs |
| Tautological assertion | Type-check a typed function | Assert a specific computed value |
| Input neglect | Empty strings, single items | Realistic data matching real usage |

Test results are written to `tests/<feature>/tests.json` with `status`, `passed`, `failed`, and `total` fields.

---

## 5. Web Testing

For features with `> Web Test: <url>` metadata and a `## Visual Specification` section, the Builder runs `/pl-web-test` using Playwright MCP.

### What It Does

1. Navigates to the feature's URL.
2. Reads the visual specification checklist from the spec.
3. Checks each item against the running application (computed CSS styles, layout, content).
4. When Figma MCP is available, performs three-source triangulation: Figma design values, spec Token Map values, and actual app values.

### Verdicts

| Verdict | Meaning | Routed To |
|---------|---------|-----------|
| PASS | All sources agree | -- |
| BUG | App does not match spec | Builder |
| STALE | Figma updated after spec was written | PM |
| DRIFT | App matches Figma but not the spec | PM |

The Builder iterates until zero BUG and zero DRIFT verdicts before committing the status tag.

---

## 6. Delivery Plans

When the Builder has multiple features to implement, it uses phased delivery to organize the work.

### When Phasing Kicks In

- 2+ HIGH-complexity features, or
- 3+ features of any complexity mix, or
- A single feature with 5+ unimplemented scenarios

### Phase Structure

Each phase groups related features (sized by testability, parallelism, and
context budget -- there is no hard per-phase cap) and follows three sub-phases:

- **B1 (Build)** -- Implement and test each feature locally.
- **B2 (Test)** -- Re-run all tests across phase features to catch cross-feature regressions.
- **B3 (Fix)** -- Diagnose and fix any B2 failures. Analyze root cause before changing code.

### Parallel Execution

When a phase has 2+ independent features (no spec-level dependencies), the Builder spawns parallel `builder-worker` sub-agents, each in an isolated git worktree. After workers complete, branches merge back sequentially. Conflicts on safe files (delivery plan, cache) auto-resolve; conflicts on source files trigger sequential fallback for that feature.

See the [Parallel Execution Guide](parallel-execution-guide.md) for details.

---

## 7. Companion Files

The Builder creates `features/<name>.impl.md` alongside the spec to document implementation knowledge. These files are the durable channel between Builder and Architect.

### What Goes In Them

- Decision tags (`[CLARIFICATION]`, `[DEVIATION]`, etc.) with rationale.
- Test quality audit results (rubric score, test count, anti-pattern scan).
- Visual verification results.
- Any tribal knowledge that would be lost between sessions.

### What Does Not Go In Them

- The implementation itself (that is in the code).
- Spec content (that stays in the feature file).
- Temporary debugging notes.

---

## 8. Day-to-Day Tips

### Checking What Needs Building

```
/pl-status
```

Shows all features with their lifecycle states. Features with Builder=TODO are ready for implementation.

### Finding Feature Context

```
/pl-find caching
```

Searches specs for a topic. Useful when implementing a feature that may interact with other parts of the system.

### When You Cannot Implement a Spec

```
/pl-infeasible feature-name
```

Records an `[INFEASIBLE]` tag in the companion file and halts work on that feature. The Architect sees it as a CRITICAL action item and must revise the spec.

### Proposing Spec Changes

```
/pl-propose topic
```

Records a `[SPEC_PROPOSAL]` in the companion file suggesting a new anchor node or spec modification. The Architect picks it up on their next session.

### Fixing QA Bugs

When QA records a `[BUG]` discovery, it appears as a Builder action item. Fix the code, update the discovery status to RESOLVED in the same commit, and re-run tests.

---

## 9. Command Reference

| Command | Description |
|---------|-------------|
| `/pl-build [name]` | Implement pending features or a specific feature. Core workflow. |
| `/pl-unit-test [name]` | Run unit tests with quality rubric gate. |
| `/pl-web-test [name]` | Run Playwright visual verification for web features. |
| `/pl-delivery-plan` | Create or review a phased delivery plan. |
| `/pl-infeasible <name>` | Escalate a feature as unimplementable. |
| `/pl-propose <topic>` | Suggest a spec change to the Architect. |
| `/pl-spec-code-audit` | Bidirectional spec-code consistency audit. |
| `/pl-status` | Check feature status and action items. |
| `/pl-find <topic>` | Search specs for where a topic is discussed. |
| `/pl-fixture` | [Test fixture](testing-workflow-guide.md) convention and workflow. |
| `/pl-server` | Dev server lifecycle management. |
| `/pl-agent-config` | View or modify agent model and startup settings. |
| `/pl-override-edit` | Edit `BUILDER_OVERRIDES.md`. |
| `/pl-whats-different` | Compare branches (main checkout only). |
| `/pl-remote-push` | Push [collaboration branch](branch-collaboration-guide.md) to remote. |
| `/pl-remote-pull` | Pull remote into current branch. |
| `/pl-help` | Display the full command list. |
| `/pl-resume [save\|role]` | Save or restore session state. |
| `/pl-update-purlin` | Update the Purlin submodule. |
