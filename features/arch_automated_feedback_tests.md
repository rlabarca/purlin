# Architecture: Automated Feedback Tests

> Label: "Architecture: Automated Feedback Tests"
> Category: "Automated Feedback Tests"

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

### Execution Constraints

- AFTs are invoked by the Builder during verification (Step 3) and by QA for integration testing
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

## Scenarios

No automated or manual scenarios. This is an architectural anchor node -- its "scenarios" are
process invariants enforced by instruction files and tooling.
