# Architecture: Automated Feedback Tests

> Label: "Architecture: Automated Feedback Tests"
> Category: "Automated Feedback Tests"

[TODO]

## Purpose

Defines the Automated Feedback Test (AFT) pattern -- the abstract contract that all automated feedback test tools must satisfy. AFTs are tools that script interactions with a target system, observe results, compare against expectations, and report structured pass/fail with evidence. They feed results back into the discovery system when failures are found. This anchor node ensures consistent behavior across all AFT implementations (web, API, LLM, mobile) and establishes the invariants that govern their use by Builder and QA agents.

## Automated Feedback Test Invariants

### Core Pattern

An AFT is a tool that:

1. **Scripts interactions** with a target system (web UI, API, LLM, mobile app)
2. **Observes results** (DOM state, HTTP responses, LLM output, screen state)
3. **Compares against expectations** (Gherkin Then steps, visual checklists, response schemas, design references)
4. **Reports structured pass/fail** with evidence (screenshots, response bodies, diffs)
5. **Feeds back into the discovery system** (BUG/DISCOVERY entries when failures are found)

### Design Reference Comparison (Visual AFTs)

AFTs that target visual systems (web UI, mobile apps) SHOULD compare their output against original design references when available:

- **Reference images** (`features/design/` artifacts) -- fast, local multimodal comparison
- **Figma MCP** (when available) -- authoritative three-source triangulated verification (design + spec + app)
- This is the primary mechanism for the Builder to "look at the designs" like a real developer, ensuring what was built matches the intended look and feel

### Execution Tiers

AFTs operate in three tiers with different triggers, owners, and performance profiles:

| Tier | When | Who | What Runs | Speed |
|------|------|-----|-----------|-------|
| Unit | During build (Step 3) | Builder (auto) | pytest/jest, in-process | Seconds |
| AFT Spot | During build (Step 3) | Builder (selective) | AFT:Web for visual features only | Minutes |
| Regression | User-chosen intervals | QA (end-to-end) | All AFTs (Agent, Web, full) | External terminal |

**Tier rules:**

- **Unit:** Always runs during Builder Step 3. Covers import-and-call, exit code, and value assertions.
- **AFT Spot:** Runs during Builder Step 3 ONLY for features with `> AFT Web:` metadata AND a Visual Specification section. All other features skip AFT during build.
- **Regression:** QA-owned end-to-end. QA authors the harness scripts, composes the regression set, and prints a clear copy-pasteable command for the user to run in an external terminal. Results feed back via `tests.json`. The Builder's only role in regression is consuming results to fix code.

### Execution Constraints

- AFTs MUST be headless/non-interactive (no human in the loop during execution)
- AFTs MUST produce machine-readable results (pass/fail per scenario/checklist item)
- AFTs MUST respect regression scoping (targeted, cosmetic, dependency-only)
- Features opt in to a specific AFT via metadata (e.g., `> AFT Web:` for web AFT)

### Implementation Family

| AFT Type | Metadata Tag | Target System | Tooling | Status |
|----------|-------------|---------------|---------|--------|
| Web UI | `> AFT Web: <url>` | Browser-rendered UI | Playwright MCP | **Implemented** (`/pl-aft-web`) |
| Agent Interaction | `> AFT Agent: <role>` | Agent conversation flow | `claude --print` + session scripting | **Implemented** (`aft_agent.md`) |
| REST/GraphQL API | `> AFT API: <base-url>` | HTTP endpoints | HTTP client + schema validation | Planned |
| LLM Interaction | `> AFT LLM: <model-id>` | Language model | Scripted prompts + response evaluation | Planned |
| iOS App | `> AFT iOS: <bundle-id>` | iOS simulator/device | XCUITest / Appium MCP | Planned |
| Android App | `> AFT Android: <package>` | Android emulator/device | UIAutomator / Appium MCP | Planned |

Each implementation is a separate feature spec with `> Prerequisite: features/arch_automated_feedback_tests.md`.

### Naming Convention

All AFT tools follow the pattern `pl-aft-<type>`:

| AFT Type | Command Name | Feature File | Command File |
|----------|-------------|-------------|--------------|
| Web UI | `/pl-aft-web` | `features/pl_aft_web.md` | `.claude/commands/pl-aft-web.md` |
| Agent | N/A (harness script) | `features/aft_agent.md` | N/A (project-specific `dev/` script) |
| REST API | `/pl-aft-api` | `features/pl_aft_api.md` | `.claude/commands/pl-aft-api.md` |
| LLM | `/pl-aft-llm` | `features/pl_aft_llm.md` | `.claude/commands/pl-aft-llm.md` |
| iOS | `/pl-aft-ios` | `features/pl_aft_ios.md` | `.claude/commands/pl-aft-ios.md` |
| Android | `/pl-aft-android` | `features/pl_aft_android.md` | `.claude/commands/pl-aft-android.md` |

### FORBIDDEN

No grepable FORBIDDEN patterns defined for this anchor. All constraints below are behavioral and verified via testing and QA review, not automated pattern scanning.

### Behavioral Constraints (Non-Grepable)

- AFTs MUST NOT require human interaction during execution (that is manual verification, not an AFT). Verification: QA review of test scripts.
- AFTs MUST NOT start or stop application servers as part of the test execution itself. Test infrastructure that starts a server BEFORE the AFT runs (e.g., `> AFT Start:` metadata) is permitted -- the server lifecycle is harness-owned, not AFT-owned. Verification: QA review of test scripts.

### Assertion Quality Invariant

For any assertion checking that the agent detected a problem, there MUST exist a fixture state where that assertion would fail because no problem exists. This is verified by including negative (canary) tests alongside positive tests:

- **Positive test:** Agent runs against a fixture with a known defect. Assertion passes because the agent reports the defect.
- **Negative test:** Agent runs against a clean fixture (no defect). The same assertion pattern MUST fail (i.e., the agent does not report a nonexistent defect).

If an assertion passes on both the defective and clean fixtures, it is too loose -- it matches incidental output rather than the specific defect. Such assertions MUST be tightened to Tier 2 or Tier 3 (see `features/aft_agent.md` Section 2.10).

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
