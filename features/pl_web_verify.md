# Feature: Web Verify Command

> Label: "/pl-web-verify Web Verify"
> Category: "Agent Skills"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

The `/pl-web-verify` skill provides automated execution of Manual Scenarios and Visual Specification checklist items for web-application features using Playwright MCP browser control tools. The LLM interprets Gherkin steps and visual checklist items, translates them into Playwright MCP actions (navigate, click, type, screenshot, evaluate JS), and judges results -- no step-definition code is needed. The LLM IS the step-definition engine.

This is an alternative *execution method* for Manual Scenarios and Visual Specs, not a new classification. The Automated/Manual/Visual taxonomy in feature specs stays unchanged. Features opt in via a `> Web Testable:` metadata annotation. Non-web features (CLI tools, file-based systems) remain manual via `/pl-verify`.

---

## 2. Requirements

### 2.1 Feature Metadata

- Feature files MAY include a `> Web Testable: <url>` blockquote metadata line (e.g., `> Web Testable: http://localhost:9086`), placed alongside other `>` metadata (Label, Category, Prerequisite).
- The URL declares where the feature's web UI is accessible for automated verification.
- Features without this annotation are not eligible for `/pl-web-verify` and continue using `/pl-verify` (manual).

### 2.2 Skill File

- The skill file MUST be created at `.claude/commands/pl-web-verify.md`.
- The skill MUST be shared ownership: Builder and QA (both roles may invoke it).
- The skill MUST include a role guard that rejects invocation by the Architect.
- Arguments: `[feature_name ...] [url_override]` -- optional feature names and/or a URL override.

### 2.3 Discovery

- If explicit feature names are provided as arguments, use those.
- If no arguments, auto-discover web-testable features: run `tools/cdd/status.sh`, read `CRITIC_REPORT.md`, identify TESTING features, read each spec for `> Web Testable:` metadata.
- Only features with `> Web Testable:` are eligible. Skip all others silently.
- If no web-testable features are found, inform the user and suggest `/pl-verify` instead.

### 2.4 Pre-flight

- For each eligible feature, extract: base URL from `> Web Testable:` (or URL override argument), Manual Scenarios under `### Manual Scenarios`, Visual Specification items under `## Visual Specification`, and regression scope from `tests/<feature_name>/critic.json`.
- Respect `targeted:` scoping (only verify named scenarios/screens).
- Respect `cosmetic` scope (skip feature).
- Respect `dependency-only` scope (verify only listed scenarios).
- If a feature has neither manual scenarios nor visual specification items, skip it with a note.

### 2.5 Playwright MCP Auto-Setup

- The skill MUST check for Playwright MCP tool availability (check for `browser_navigate` in the tool list).
- Playwright MUST run in **headless mode** (`--headless` flag). Headless mode runs the browser invisibly in the background, avoids disrupting the user's screen, and is 20-30% faster than headed mode. Screenshots, DOM evaluation, and all Playwright MCP actions work identically in headless mode.
- If Playwright MCP is not available, attempt auto-setup: verify package accessibility via `npx @playwright/mcp@latest --help`, then configure via `claude mcp add playwright -- npx @playwright/mcp --headless`.
- After auto-setup, inform the user a session restart is required to load the new MCP server, then stop.
- If auto-setup fails, print the error with manual setup instructions and stop.
- If Playwright MCP IS available but was previously configured without `--headless`, the skill MUST detect this and instruct the user to reconfigure: `claude mcp remove playwright && claude mcp add playwright -- npx @playwright/mcp --headless`, then restart the session.

### 2.6 Browser Setup

- Navigate to the base URL via Playwright MCP `browser_navigate`.
- Verify the page loads successfully.
- If the page fails to load, report the error and suggest the user verify the server is running.

### 2.7 Manual Scenario Execution

- For each in-scope manual scenario, read the Given/When/Then steps.
- Translate each step into Playwright MCP actions: `browser_navigate`, `browser_click`, `browser_type`, `browser_hover`, `browser_wait`, `browser_screenshot`, `browser_evaluate`.
- Execute actions sequentially following Gherkin step order.
- At each Then/And verification point: take a screenshot and/or evaluate DOM/JS state.
- Use vision analysis of screenshots combined with DOM state to determine PASS or FAIL.
- Record results with evidence (screenshot observations, DOM values, JS evaluation results).
- For steps requiring something outside the browser (file system, environment, email): use Bash tools when feasible, or mark as INCONCLUSIVE with a reason note recommending manual verification.

### 2.8 Visual Spec Verification

- For each in-scope visual spec screen, navigate to the appropriate page/view state.
- Set up required state (e.g., hover, expand, switch themes) via Playwright MCP actions.
- Take a full-page screenshot via `browser_screenshot`.
- Analyze the screenshot against each checklist item using vision.
- For interaction-dependent items (hover effects, transitions): execute the interaction, take another screenshot, then verify.
- Record PASS/FAIL per checklist item with observation notes.

### 2.9 Result Recording

- Print a summary: N passed, M failed, K inconclusive out of T total (separately for manual scenarios and visual spec items).
- For failures: record as `[BUG]` discoveries in the feature's `## User Testing Discoveries` section using the standard discovery format (QA_BASE Section 4.3), including observed behavior from screenshot/DOM analysis and expected behavior from the spec.
- For inconclusive items: list them with recommendation for manual verification via `/pl-verify`.
- Commit discovery entries with message format: `qa(<scope>): [BUG] - web-verify findings`.

### 2.10 Completion Gate

- **QA Agent invocation:** If all scenarios and visual items pass (zero failures, zero inconclusive), prompt: "All web verification passed. Run `/pl-complete <name>` to mark done?" If confirmed, run `/pl-complete`.
- **Builder invocation:** If all pass, print summary only. Do not mark complete. Suggest the QA agent run `/pl-complete`.

### 2.11 Instruction Updates

The following instruction files MUST be updated by the Builder to reference the new skill:

- `instructions/references/feature_format.md` -- Add `> Web Testable: <url>` to blockquote metadata documentation.
- `instructions/references/visual_spec_convention.md` -- Document that `> Web Testable:` enables automated visual verification via Playwright MCP. Update on-demand loader notice to include `/pl-web-verify`.
- `instructions/references/visual_verification_protocol.md` -- Add Section 5.4.7: Playwright MCP automated alternative referencing `/pl-web-verify`. Update on-demand loader notice to include `/pl-web-verify`.
- `instructions/QA_BASE.md` -- Add `/pl-web-verify` to the authorized commands list (Section 3.0). Add brief reference in Section 5.4 noting the automated alternative for web-testable features.
- `instructions/BUILDER_BASE.md` -- Add `/pl-web-verify` to the authorized commands list (Section 2.0). Add brief reference in Section 5.3 (Verify Locally) noting web verification as a pre-TESTING validation option.
- `instructions/references/qa_commands.md` -- Add `/pl-web-verify [name]` entry to all three command table variants (Main, Collab, Isolated), placed after `/pl-verify`.
- `instructions/references/builder_commands.md` -- Add `/pl-web-verify [name]` entry to all three command table variants (Main, Collab, Isolated), placed after `/pl-propose`.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto-discover web-testable features

    Given the Critic report shows features in TESTING state
    And some features have `> Web Testable:` metadata and others do not
    When `/pl-web-verify` is invoked without arguments
    Then only features with `> Web Testable:` metadata are selected for verification
    And features without the annotation are silently skipped

#### Scenario: URL override from argument

    Given a feature has `> Web Testable: http://localhost:9086`
    When `/pl-web-verify feature_name http://localhost:3000` is invoked
    Then the URL override `http://localhost:3000` is used instead of the spec URL

#### Scenario: Playwright MCP not available triggers headless auto-setup

    Given Playwright MCP tools are not available in the current session
    When `/pl-web-verify` is invoked
    Then the skill attempts to install and configure Playwright MCP with `--headless` flag
    And informs the user a session restart is required
    And stops execution (does not attempt verification)

#### Scenario: Headed Playwright MCP detected triggers reconfiguration

    Given Playwright MCP tools are available in the current session
    But the MCP server was configured without `--headless`
    When `/pl-web-verify` is invoked
    Then the skill instructs the user to reconfigure with headless mode
    And stops execution until the session is restarted with headless configuration

#### Scenario: Manual scenario PASS recorded correctly

    Given a web-testable feature has a manual scenario with Given/When/Then steps
    And Playwright MCP is available
    When `/pl-web-verify` executes the scenario
    And all Then/And verification points pass (screenshot + DOM confirm expected state)
    Then the scenario is recorded as PASS with evidence notes

#### Scenario: Manual scenario FAIL creates BUG discovery

    Given a web-testable feature has a manual scenario
    When `/pl-web-verify` executes the scenario
    And a Then verification point fails (observed state differs from expected)
    Then a `[BUG]` discovery is recorded in the feature's `## User Testing Discoveries`
    And the discovery includes observed behavior from the screenshot/DOM analysis
    And the discovery is committed to git

#### Scenario: Inconclusive step handled gracefully

    Given a manual scenario contains a step requiring non-browser verification (e.g., email check)
    When `/pl-web-verify` cannot automate that step
    Then the step is marked INCONCLUSIVE
    And the summary recommends manual verification via `/pl-verify`
    And the inconclusive step is NOT recorded as a failure

#### Scenario: Visual spec items verified via screenshot analysis

    Given a web-testable feature has a `## Visual Specification` with checklist items
    When `/pl-web-verify` navigates to the screen and takes a screenshot
    Then each checklist item is analyzed against the screenshot using vision
    And PASS/FAIL is recorded per item with observation notes

#### Scenario: Regression scope respected

    Given a feature's `critic.json` has `regression_scope: "targeted:Scenario A"`
    When `/pl-web-verify` is invoked for that feature
    Then only "Scenario A" is executed
    And all other manual scenarios and visual items are skipped

#### Scenario: Cosmetic scope skips feature

    Given a feature's `critic.json` has `regression_scope: "cosmetic"`
    When `/pl-web-verify` is invoked for that feature
    Then the feature is skipped entirely with a note

#### Scenario: QA completion gate prompts for completion

    Given the invoking agent is QA
    And all scenarios and visual items passed with zero failures and zero inconclusive
    When results are presented
    Then the skill prompts to run `/pl-complete <name>`

#### Scenario: Builder completion gate is summary only

    Given the invoking agent is Builder
    And all scenarios and visual items passed
    When results are presented
    Then only a summary is printed
    And the skill suggests QA run `/pl-complete`

#### Scenario: Instruction files updated with web-verify references

    Given the skill file has been created
    When instruction updates are applied per Section 2.11
    Then `/pl-web-verify` appears in both QA and Builder authorized command lists
    And `/pl-web-verify [name]` appears in all variants of both command tables
    And `> Web Testable:` is documented in feature_format.md
    And visual_spec_convention.md references the automated alternative
    And visual_verification_protocol.md has a Section 5.4.7 for Playwright MCP

### Manual Scenarios (Human Verification Required)

None.

## User Testing Discoveries

### [DISCOVERY] pl-web-verify uses hardcoded feature URL without server liveness or dynamic port resolution (Discovered: 2026-03-06)
- **Scenario:** NONE
- **Observed Behavior:** During web verification of `cdd_agent_configuration`, the skill navigated to `http://localhost:9086` (from the `> Web Testable:` metadata). A stale server was running on that port from a previous session — it was not the current CDD Dashboard instance. The real server was running on port 52288, as written by the server at startup to `.purlin/runtime/cdd.port`. The verification was testing against stale/incorrect state.
- **Expected Behavior:** `/pl-web-verify` should (1) read `.purlin/runtime/cdd.port` to discover the actual running port for CDD Dashboard features, (2) validate that the server at the resolved URL is the correct/current instance, (3) start the server via `/pl-cdd` if it is not running, and (4) prefer the dynamic port over the hardcoded `> Web Testable:` URL when a runtime port file exists. Feature specs should not be required to hardcode a specific port number.
- **Action Required:** Architect
- **Status:** OPEN
