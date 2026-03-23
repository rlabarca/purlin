# Architecture: Testing

> Label: "Architecture: Testing"
> Category: "Test Infrastructure"

## Purpose

Defines the testing pattern -- the abstract contract that all automated test tools must satisfy. Test tools script interactions with a target system, observe results, compare against expectations, and report structured pass/fail with evidence. They feed results back into the discovery system when failures are found. This anchor node ensures consistent behavior across all test implementations and establishes the invariants that govern their use by Builder and QA agents.

## Testing Invariants

### Core Pattern

A test tool:

1. **Scripts interactions** with a target system (web UI, API, agent conversation, etc.)
2. **Observes results** (DOM state, HTTP responses, agent output, screen state)
3. **Compares against expectations** (Gherkin Then steps, visual checklists, response schemas, design references)
4. **Reports structured pass/fail** with evidence (screenshots, response bodies, diffs)
5. **Feeds back into the discovery system** (BUG/DISCOVERY entries when failures are found)

### Design Reference Comparison (Visual Tests)

Tests that target visual systems (web UI, mobile apps) SHOULD compare their output against original design references when available:

- **Reference images** (`features/design/` artifacts) -- fast, local multimodal comparison
- **Figma MCP** (when available) -- authoritative three-source triangulated verification (design + spec + app)
- This is the primary mechanism for the Builder to "look at the designs" like a real developer, ensuring what was built matches the intended look and feel

### Testing Tiers

Tests operate in three tiers with different triggers, owners, and performance profiles:

| Tier | When | Who | What Runs | Speed |
|------|------|-----|-----------|-------|
| Unit | During build (Step 3) | Builder (auto) | pytest/jest, in-process | Seconds |
| Spot Check | During build (Step 3) | Builder (selective) | `/pl-web-test` for visual web features only | Minutes |
| Regression | User-chosen intervals | QA (end-to-end) | All regression tests (agent, web, full) | External terminal |

**Tier rules:**

- **Unit:** Always runs during Builder Step 3. Covers import-and-call, exit code, and value assertions. Protocol: `/pl-unit-test`.
- **Fixture scope:** The Builder does NOT set up fixtures during unit testing (Step 3). Fixture-backed testing is regression-tier (QA-owned).
- **Spot Check:** Runs during Builder Step 3 ONLY for features with `> Web Test:` metadata AND a Visual Specification section. All other features skip spot checks during build.
- **Regression:** QA-owned end-to-end. QA authors the harness scripts, composes the regression set, and prints a clear copy-pasteable command for the user to run in an external terminal. Results feed back via `tests.json`. The Builder's only role in regression is consuming results to fix code.

### Execution Constraints

- Tests MUST be headless/non-interactive (no human in the loop during execution)
- Tests MUST produce machine-readable results (pass/fail per scenario/checklist item)
- Tests MUST respect regression scoping (targeted, cosmetic, dependency-only)
- Features opt in to web testing via `> Web Test:` metadata

### Regression Testing Convention

Features that require regression testing beyond unit tests declare their regression requirements in a `### Regression Testing` section within the feature's Requirements. This section is the Architect's declaration of what regression tests should exist. The test scripts themselves are the Builder's implementation.

The `### Regression Testing` section describes:
- **Approach:** The testing methodology (agent behavior harness, web UI automation, API contract checks, etc.)
- **Scenarios covered:** Which behavioral scenarios the regression tests verify
- **Fixture tags:** References to fixture tags used by the regression tests (if applicable)

The Critic detects features with `### Regression Testing` sections or `> Web Test:` metadata and flags missing regression results as QA action items ("regression coverage gap").

### Regression Test Naming Contract

Regression test scripts MUST follow this naming convention to enable automated discovery:
- **Scenario declarations:** `tests/qa/scenarios/<feature_stem>_<scenario_slug>.json`
- **Harness scripts:** `dev/<test_type>_<feature_stem>.sh` (Purlin-dev) or `tests/qa/<test_type>_<feature_stem>.sh` (consumer)
- **Results:** Written to the feature's `tests/<feature_stem>/tests.json` via the `--write-results` convention.

### Test Classification Heuristic

The Builder MUST evaluate unit test suites for potential reclassification to the regression tier. When a test script under `### Unit Tests` exhibits behavioral/integration characteristics, the Builder proposes reclassification to the Architect via `[SPEC_PROPOSAL]` in the companion file.

**Behavioral signals (2+ present indicate regression-tier work):**

| Signal | Detection |
|--------|-----------|
| **Scale** | Test script exceeds 500 lines or has 50+ assertions |
| **Sandbox creation** | Test creates temporary directories, clones repositories, or simulates deployment environments |
| **Execution time** | Test takes >30 seconds wall clock to complete |
| **Process lifecycle** | Test starts/stops external processes (servers, git operations beyond simple commands) |
| **Multi-step flows** | Test exercises sequences of operations with state carried between steps (init then modify then verify) |
| **Environment manipulation** | Test modifies PATH, environment variables, or filesystem state outside the test directory |

**Builder action when 2+ signals are detected:**

Record a `[SPEC_PROPOSAL]` entry in the feature's companion file:

```
[SPEC_PROPOSAL] Test reclassification: unit tests exhibit regression-tier characteristics
- Signals detected: <list>
- Recommendation: Move N scenarios from Unit Tests to QA Scenarios @auto
- Rationale: <brief explanation of why these are behavioral, not unit>
Proposed anchor: No new anchor (arch_testing.md Section "Test Classification Heuristic")
```

The Critic surfaces this as a HIGH-priority Architect action item. The Architect then updates the feature spec's scenario sections accordingly.

**Timing:** The Builder runs this heuristic after completing `/pl-unit-test` for a feature. It is a post-test checkpoint, not a gate -- the Builder does not halt work. The proposal is informational and routes through the normal Critic cycle.

### Backward Compatibility

During the transition from `> AFT Web:` to `> Web Test:` metadata, the Critic parser and `/pl-web-test` tool MUST accept both forms. Consumer projects should migrate to `> Web Test:` at their convenience. The `> AFT Web:` form is deprecated and will be removed in a future release.

### FORBIDDEN

No grepable FORBIDDEN patterns defined for this anchor. All constraints below are behavioral and verified via testing and QA review, not automated pattern scanning.

### Behavioral Constraints (Non-Grepable)

- Tests MUST NOT require human interaction during execution (that is manual verification, not a test). Verification: QA review of test scripts.
- Tests MUST NOT start or stop application servers as part of the test execution itself. Test infrastructure that starts a server BEFORE the test runs (e.g., `> Web Start:` metadata) is permitted -- the server lifecycle is harness-owned, not test-owned. Verification: QA review of test scripts.

### Assertion Quality Invariant

For any assertion checking that the agent detected a problem, there MUST exist a fixture state where that assertion would fail because no problem exists. This is verified by including negative (canary) tests alongside positive tests:

- **Positive test:** Agent runs against a fixture with a known defect. Assertion passes because the agent reports the defect.
- **Negative test:** Agent runs against a clean fixture (no defect). The same assertion pattern MUST fail (i.e., the agent does not report a nonexistent defect).

If an assertion passes on both the defective and clean fixtures, it is too loose -- it matches incidental output rather than the specific defect. Such assertions MUST be tightened to Tier 2 or Tier 3.

### Assertion Modification Discipline

When QA modifies an assertion pattern in a test harness, the commit message MUST include one of the following tags:

| Tag | Meaning | When to Use |
|-----|---------|-------------|
| `[assertion-intent]` | Old assertion tested phrasing; new assertion tests behavioral intent. | Upgrading from Tier 1 to Tier 2/3, or rephrasing to match intent rather than exact words. |
| `[assertion-fix]` | Old assertion had a bug (wrong pattern, inverted logic, missing escape). | Correcting a defective assertion that was producing false positives or false negatives. |
| `[assertion-broaden]` | Old assertion too narrow for model variance; broader pattern still verifies intent. | Relaxing a pattern to accommodate acceptable phrasing variation. Commit message MUST explain why the broader pattern still verifies the intended behavior. |

Non-tagged assertion modification commits are non-compliant. The Critic's Implementation Gate MAY flag untagged assertion commits as a traceability gap (future enhancement).

## Scenarios

No automated or manual scenarios. This is an architectural anchor node -- its "scenarios" are
process invariants enforced by instruction files and tooling.
