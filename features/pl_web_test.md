# Feature: Web Test Command

> Label: "Agent Skills: QA: /pl-web-test Web Test"
> Category: "Agent Skills: QA"
> Prerequisite: features/arch_testing.md
> Prerequisite: features/design_artifact_pipeline.md

[Complete]

## 1. Overview

The `/pl-web-test` skill provides automated execution of Manual Scenarios and Visual Specification checklist items for web-application features using Playwright MCP browser control tools with Figma-triangulated verification. The LLM interprets Gherkin steps and visual checklist items, translates them into Playwright MCP actions (navigate, click, type, screenshot, evaluate JS), and judges results -- no step-definition code is needed. The LLM IS the step-definition engine.

When Figma MCP is available and a visual spec screen has a Figma reference, the skill performs three-source triangulated verification: comparing the Figma design (via MCP), the spec (Token Map + checklists), and the running app (via Playwright) to detect BUGs, STALE specs, and SPEC_DRIFT.

This is an alternative *execution method* for Manual Scenarios and Visual Specs, not a new classification. The Automated/Manual/Visual taxonomy in feature specs stays unchanged. Features opt in via a `> Web Test:` metadata annotation. Non-web features (CLI tools, file-based systems) remain manual via `/pl-verify`.

---

## 2. Requirements

### 2.1 Feature Metadata

- Feature files MAY include a `> Web Test: <url>` blockquote metadata line (e.g., `> Web Test: http://localhost:9086`), placed alongside other `>` metadata (Label, Category, Prerequisite).
- The URL declares where the feature's web UI is accessible for automated verification.
- Features without this annotation are not eligible for `/pl-web-test` and continue using `/pl-verify` (manual).
- Feature files MAY include a `> Web Start: <command>` blockquote metadata line (e.g., `> Web Start: /pl-server`). When present and the server is not reachable during pre-flight, the skill invokes this command to start the server before proceeding.
- Runtime configuration (port files, auth tokens) is handled internally by the web test tool, not via per-feature metadata. The tool reads `.purlin/runtime/server.port` for dynamic port resolution automatically.

### 2.2 Skill File

- The skill file MUST be created at `.claude/commands/pl-web-test.md`.
- The skill MUST be shared ownership: Engineer and QA (both roles may invoke it).
- The skill MUST include a role guard that rejects invocation by PM mode.
- Arguments: `[feature_name ...] [url_override]` -- optional feature names and/or a URL override.

### 2.3 Discovery

- If explicit feature names are provided as arguments, use those.
- If no arguments, auto-discover web-testable features: run `tools/cdd/scan.sh`, read `/pl-status`, identify TESTING features, read each spec for `> Web Test:` metadata.
- Only features with `> Web Test:` are eligible. Skip all others silently.
- If no web-testable features are found, inform the user and suggest `/pl-verify` instead.

### 2.4 Pre-flight

- For each eligible feature, extract: base URL from `> Web Test:` (or URL override argument), Manual Scenarios under `### Manual Scenarios`, Visual Specification items under `## Visual Specification`, and regression scope from `tests/<feature_name>/tests.json`.
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

### 2.6 Dynamic Port Resolution and Server Liveness

- **Port resolution order:** (1) URL override from command argument, (2) runtime port file at `.purlin/runtime/server.port`, (3) port from `> Web Test:` URL.
- The tool reads `.purlin/runtime/server.port` automatically (no per-feature metadata needed). If the file exists and contains a valid port number, replace the port in the `> Web Test:` URL with the runtime port. If the file does not exist or is empty, fall through to the `> Web Test:` URL as-is.
- **Liveness check:** Before navigating, attempt an HTTP request (via `browser_navigate` or `curl`) to the resolved URL. If the server is not reachable:
  - If `> Web Start:` is declared, invoke the start command, wait for the port file to appear (up to 10 seconds), re-read the port, and retry the liveness check.
  - If `> Web Start:` is not declared or the server is still not reachable after auto-start, report the error with the resolved URL and stop verification for this feature (do not fail the entire run -- continue with other features).
- **Stale server detection:** When using a runtime port file, verify the resolved URL responds with expected content (e.g., a non-error HTTP status). A server responding on the hardcoded port that differs from the port file port is treated as stale -- the port file port takes precedence.

### 2.7 Browser Setup

- Navigate to the resolved URL (after dynamic port resolution) via Playwright MCP `browser_navigate`.
- Verify the page loads successfully.
- If the page fails to load (after liveness pre-flight passed), report the error and skip this feature.

### 2.8 Manual Scenario Execution

- For each in-scope manual scenario, read the Given/When/Then steps.
- Translate each step into Playwright MCP actions: `browser_navigate`, `browser_click`, `browser_type`, `browser_hover`, `browser_wait`, `browser_screenshot`, `browser_evaluate`.
- Execute actions sequentially following Gherkin step order.
- At each Then/And verification point: take a screenshot and/or evaluate DOM/JS state.
- Use vision analysis of screenshots combined with DOM state to determine PASS or FAIL.
- Record results with evidence (screenshot observations, DOM values, JS evaluation results).
- For steps requiring something outside the browser (file system, environment, email): use Bash tools when feasible, or mark as INCONCLUSIVE with a reason note recommending manual verification.

### 2.9 Figma MCP Pre-Check (Visual Spec Only)

Before visual spec verification, check for Figma MCP tool availability:
- Check for Figma MCP tools (e.g., `get_file`, `get_node`) in the available tool list.
- If Figma MCP is available and a visual spec screen has a Figma reference (`[Figma](<url>)`), extract the Figma node ID from the reference URL for use in triangulated verification (Section 2.9.1).
- If Figma MCP is NOT available, proceed with spec-only visual verification (no triangulation). Note in the output: "Figma MCP not available -- triangulated verification skipped. Install Figma MCP for three-source comparison."
- Figma MCP access is read-only. QA MUST NOT write to Figma.

### 2.9.1 Figma-Triangulated Visual Spec Verification

When Figma MCP is available and a visual spec screen has a Figma reference, perform three-source comparison for each checklist item and Token Map entry:

**Step 1 -- Read all three sources:**

| Source | What QA reads | How |
|--------|--------------|-----|
| **Figma** | Component tree, dimensions, colors, fonts, spacing | Figma MCP (`get_file`, `get_node`) using the node ID from the Reference URL |
| **Spec** | Token Map + checklist items | Read from `features/<name>.md` |
| **App** | Computed styles, DOM structure, rendered pixels | Playwright MCP (`browser_evaluate`, `browser_screenshot`) |

Fetch ONLY the specific Figma node referenced in the Reference URL (using the `node-id` parameter), not the entire file. This reduces response size from ~50K tokens to ~2-5K tokens per screen.

**Step 2 -- Structured comparison (per checklist item):**

For each measurable checklist item (e.g., `- [ ] Card width 120px`):
1. Read the corresponding property from Figma via MCP.
2. Read the expected value from the checklist.
3. Read the actual value from the app via `browser_evaluate("getComputedStyle(el).property")`.
4. Compare all three and assign a verdict:

| Figma | Spec | App | Verdict | Action |
|-------|------|-----|---------|--------|
| Match | Match | Match | PASS | All three agree |
| Changed | Stale | Match old | STALE | Figma updated, spec not re-ingested. PM action item. |
| Match | Match | Differs | BUG | Code doesn't match spec. Engineer action item. |
| Changed | Changed | Differs | BUG | Spec is current but code is wrong. Engineer action item. |
| Changed | Stale | Match Figma | SPEC_DRIFT | Code matches Figma but not spec. PM action item. |

**Step 3 -- Token verification:**

For each Token Map entry (e.g., `surface -> var(--weather-bg)`):
1. Read the Figma design variable value via MCP.
2. Read the project token from the spec.
3. Read the app's computed CSS property value via `browser_evaluate`.
4. Compare all three. Token drift (Figma value != App value for the mapped token) is flagged.

**Step 4 -- Visual judgment (non-measurable items):**

For checklist items that cannot be measured via computed styles (e.g., `- [ ] Subtle left-edge shadow`):
1. Take screenshot via Playwright.
2. Read the Figma frame/node via MCP.
3. Vision-compare the screenshot against the Figma render for the item.

### 2.9.2 Spec-Only Visual Spec Verification (Fallback)

When Figma MCP is NOT available, or a screen has no Figma reference:

- For each in-scope visual spec screen, navigate to the appropriate page/view state.
- Set up required state (e.g., hover, expand, switch themes) via Playwright MCP actions.
- Take a full-page screenshot via `browser_screenshot`.
- Analyze the screenshot against each checklist item using vision.
- For interaction-dependent items (hover effects, transitions): execute the interaction, take another screenshot, then verify.
- Record PASS/FAIL per checklist item with observation notes.
- This is the previous behavior, preserved as fallback.

### 2.10 Result Recording

- Print a summary: N passed, M failed, K inconclusive out of T total (separately for manual scenarios and visual spec items).
- **Three-source reporting (when Figma MCP was used):** Print a triangulated verification report with per-item attribution:
  ```
  === Triangulated Verification: <feature_name> ===

  Screen: <Screen Name>
    [PASS]  <item>         Figma=<val> Spec=<val> App=<val>
    [BUG]   <item>         Figma=<val> Spec=<val> App=<val>   <- code wrong
    [STALE] <item>         Figma=<val> Spec=<val>             <- Figma updated
    [DRIFT] <item>         Figma=<val> Spec=<val> App=<val>   <- spec drift

  Token Map:
    [PASS]  <token> -> <project-token>   Figma=<val> App=<val>
    [DRIFT] <token> -> <project-token>   Figma=<val> App=<val>  <- token drift

  Summary: N passed, M BUG, K STALE, J DRIFT / T total
  ```
- **Verdict routing:**

  | Verdict | Discovery Type | Routes To |
  |---------|---------------|-----------|
  | BUG (App wrong) | `[BUG]` | Engineer |
  | STALE (Figma updated, spec outdated) | Staleness PM action item | PM (re-ingest) |
  | SPEC_DRIFT (App matches Figma, not spec) | `[DISCOVERY]` | PM (sync spec) |
  | TOKEN_DRIFT (Figma value != App value) | `[BUG]` or `[DISCOVERY]` | Engineer or PM depending on which changed |

- For BUG failures: record as `[BUG]` discoveries in the feature's discovery sidecar file (`features/<name>.discoveries.md`) using the standard discovery format (PURLIN_BASE.md (QA mode protocols)), including three-source comparison data in the observed behavior field.
- For STALE/DRIFT items: record as PM action items (not BUG discoveries) noting the specific drift.
- For inconclusive items: list them with recommendation for manual verification via `/pl-verify`.
- Commit discovery entries with message format: `qa(<scope>): [BUG] - web-verify findings`.

### 2.11 Completion Gate

- **QA Agent invocation:** If all scenarios and visual items pass (zero failures, zero inconclusive), prompt: "All web verification passed. Run `/pl-complete <name>` to mark done?" If confirmed, run `/pl-complete`.
- **Engineer invocation:** If all pass, print summary only. Do not mark complete. Suggest the QA agent run `/pl-complete`.

### 2.12 Fixture-Backed Testing

When a feature has `> Web Test:` metadata and the project has a fixture repo (resolved via the three-tier lookup: per-feature `> Test Fixtures:` metadata → config `fixture_repo_url` → convention path `.purlin/runtime/fixture-repo`), `/pl-web-test` can execute scenarios against fixture-provided project states rather than the live project. This solves the "complex setup" problem -- scenarios requiring specific branch states, collaboration setups, or config values get their preconditions from immutable fixture tags.

**Workflow:**

1. **Fixture detection:** During pre-flight (Section 2.4), resolve the fixture repo path using the three-tier lookup. If a fixture repo is accessible, check whether any in-scope scenario's Given steps reference a fixture tag (pattern: `fixture tag "<tag-path>"`).
2. **Fixture checkout:** For each scenario referencing a fixture tag, run `tools/test_support/fixture.sh checkout <repo-path> <tag>` to obtain the fixture state in a temp directory.
3. **Server startup against fixture:** Start the dev server against the fixture checkout via `/pl-server --project-root <fixture-dir> --port 0`. The `--port 0` flag tells the server to bind an ephemeral port. The server prints the actual bound port to stdout (e.g., `Serving on port 52341`). The skill reads this port from the server's stdout.
4. **URL construction:** Construct the test URL using `http://localhost:<ephemeral-port>`. This bypasses the `> Web Test:` static URL and the runtime port file entirely -- the ephemeral port from the fixture-backed server is the only port used.
5. **Scenario execution:** Execute the scenario's When/Then steps against the fixture-backed server using the standard Playwright MCP flow (Sections 2.8-2.9).
6. **Cleanup:** After the scenario completes (pass or fail), stop the fixture-backed server and run `tools/test_support/fixture.sh cleanup <fixture-dir>`.

**Non-fixture scenarios:** Scenarios without fixture tag references in the same feature continue using the normal port resolution flow (Section 2.6) against the live project.

**Error handling:** If fixture checkout fails (tag not found, repo unreachable), the scenario is marked INCONCLUSIVE with a note about the missing fixture. Other scenarios in the feature continue normally.

### 2.15 Legacy Cleanup and Migration

The following legacy artifacts from prior naming conventions MUST be removed or updated by Engineer mode:

1. **Rename** skill file `.claude/commands/pl-aft-web.md` to `.claude/commands/pl-web-test.md`. Update all internal references: `> AFT Web:` to `> Web Test:`, `> AFT Start:` to `> Web Start:`, `/pl-aft-web` to `/pl-web-test`.
2. **Rename** test directory `tests/pl_aft_web/` to `tests/pl_web_test/`. Update all internal references.
3. ~~`tools/critic/critic.py` and `tools/critic/test_critic.py`~~ — Removed (Critic system retired).
4. (reserved)
5. **Update** `dev/setup_fixture_repo.sh`: update fixture tag names from `pl_aft_web` to `pl_web_test` and metadata from `> AFT Web:` to `> Web Test:`.
6. **Delete** old skill file `.claude/commands/pl-web-verify.md` if it still exists.
7. **Screenshot directory:** `.purlin/runtime/aft-web/` renamed to `.purlin/runtime/web-test/`.

**Backward compatibility:** The scan engine accepts both `> AFT Web:` and `> Web Test:` during the transition period. Consumer projects using `> AFT Web:` will continue to work without immediate migration.

### 2.13 Instruction Updates

The following instruction files MUST be updated by Engineer mode to reference the new skill:

- `instructions/references/feature_format.md` -- Add `> Web Test: <url>` and `> Web Start: <command>` to blockquote metadata documentation.
- `instructions/references/visual_spec_convention.md` -- Document that `> Web Test:` enables automated visual verification via Playwright MCP. Update on-demand loader notice to include `/pl-web-test`.
- `instructions/references/visual_verification_protocol.md` -- Add Section 5.4.7: Playwright MCP automated alternative referencing `/pl-web-test`. Update on-demand loader notice to include `/pl-web-test`.
- `instructions/PURLIN_BASE.md` -- Add `/pl-web-test` to the authorized commands list (Section 3.0). Add brief reference in Section 5.4 noting the automated alternative for web-testable features.
- `instructions/PURLIN_BASE.md` -- Add `/pl-web-test` to the authorized commands list (Section 2.0). Add brief reference in Section 5.3 (Verify Locally) noting web verification as a pre-TESTING validation option.
- `instructions/references/qa_commands.md` -- Add `/pl-web-test [name]` entry to both command table variants (Main, Collab), placed after `/pl-verify`.
- `instructions/references/builder_commands.md` -- Add `/pl-web-test [name]` entry to both command table variants (Main, Collab), placed after `/pl-propose`.

### 2.14 Web Test Fixture Tags

| Tag | State Description |
|-----|-------------------|
| `main/pl_web_test/web-testable-features` | Project with multiple web-test-eligible features for verifying discovery and execution flow |

---

## 3. Scenarios

### Unit Tests

#### Scenario: Auto-discover web-testable features

    Given the Critic report shows features in TESTING state
    And some features have `> Web Test:` metadata and others do not
    When `/pl-web-test` is invoked without arguments
    Then only features with `> Web Test:` metadata are selected for verification
    And features without the annotation are silently skipped

#### Scenario: URL override from argument

    Given a feature has `> Web Test: http://localhost:9086`
    When `/pl-web-test feature_name http://localhost:3000` is invoked
    Then the URL override `http://localhost:3000` is used instead of the spec URL

#### Scenario: Playwright MCP not available triggers headless auto-setup

    Given Playwright MCP tools are not available in the current session
    When `/pl-web-test` is invoked
    Then the skill attempts to install and configure Playwright MCP with `--headless` flag
    And informs the user a session restart is required
    And stops execution (does not attempt verification)

#### Scenario: Headed Playwright MCP detected triggers reconfiguration

    Given Playwright MCP tools are available in the current session
    But the MCP server was configured without `--headless`
    When `/pl-web-test` is invoked
    Then the skill instructs the user to reconfigure with headless mode
    And stops execution until the session is restarted with headless configuration

#### Scenario: Dynamic port resolution from runtime port file

    Given a feature has `> Web Test: http://localhost:9086`
    And `.purlin/runtime/server.port` contains `52288`
    When `/pl-web-test` resolves the URL for that feature
    Then the resolved URL is `http://localhost:52288`
    And port `9086` from the metadata is not used

#### Scenario: Runtime port file missing falls back to metadata URL

    Given a feature has `> Web Test: http://localhost:9086`
    And `.purlin/runtime/server.port` does not exist
    When `/pl-web-test` resolves the URL for that feature
    Then the resolved URL is `http://localhost:9086`

#### Scenario: Server auto-start when not reachable

    Given a feature has `> Web Test: http://localhost:9086`
    And the feature has `> Web Start: /pl-server`
    And no server is reachable at the resolved URL
    When `/pl-web-test` performs the liveness check
    Then the skill invokes `/pl-server` to start the server
    And waits up to 10 seconds for the port file to appear
    And re-reads the port file for the new port
    And retries the liveness check at the updated URL

#### Scenario: Server not reachable and no start command

    Given a feature has `> Web Test: http://localhost:9086`
    And the feature does not have `> Web Start:` metadata
    And no server is reachable at the resolved URL
    When `/pl-web-test` performs the liveness check
    Then the skill reports the error with the resolved URL
    And skips verification for this feature
    And continues with the next feature in the queue

#### Scenario: URL override takes precedence over port file

    Given a feature has `> Web Test: http://localhost:9086`
    And `.purlin/runtime/server.port` contains `52288`
    When `/pl-web-test feature_name http://localhost:3000` is invoked
    Then the resolved URL is `http://localhost:3000`
    And neither the metadata port nor the port file port is used

#### Scenario: Manual scenario PASS recorded correctly

    Given a web-testable feature has a manual scenario with Given/When/Then steps
    And Playwright MCP is available
    When `/pl-web-test` executes the scenario
    And all Then/And verification points pass (screenshot + DOM confirm expected state)
    Then the scenario is recorded as PASS with evidence notes

#### Scenario: Manual scenario FAIL creates BUG discovery

    Given a web-testable feature has a manual scenario
    When `/pl-web-test` executes the scenario
    And a Then verification point fails (observed state differs from expected)
    Then a `[BUG]` discovery is recorded in the feature's discovery sidecar file
    And the discovery includes observed behavior from the screenshot/DOM analysis
    And the discovery is committed to git

#### Scenario: Inconclusive step handled gracefully

    Given a manual scenario contains a step requiring non-browser verification (e.g., email check)
    When `/pl-web-test` cannot automate that step
    Then the step is marked INCONCLUSIVE
    And the summary recommends manual verification via `/pl-verify`
    And the inconclusive step is NOT recorded as a failure

#### Scenario: Visual spec items verified via screenshot analysis (no Figma MCP)

    Given a web-testable feature has a `## Visual Specification` with checklist items
    And Figma MCP tools are not available
    When `/pl-web-test` navigates to the screen and takes a screenshot
    Then each checklist item is analyzed against the screenshot using vision
    And PASS/FAIL is recorded per item with observation notes
    And the output notes "Figma MCP not available -- triangulated verification skipped"

#### Scenario: Figma-triangulated verification with all sources agreeing

    Given a web-testable feature has a Visual Specification with a Figma reference
    And the Token Map maps "primary" to "var(--accent)"
    And a checklist item states "Card width 120px"
    And Figma MCP is available
    When `/pl-web-test` performs triangulated verification
    Then the Figma node width is read via MCP
    And the app computed width is read via browser_evaluate
    And all three sources agree on 120px
    And the item is recorded as PASS with three-source attribution

#### Scenario: Figma-triangulated verification detects BUG

    Given a web-testable feature has a Visual Specification with a Figma reference
    And a checklist item states "Icon 48x48"
    And Figma reports 48px and spec says 48px but app computes 32px
    When `/pl-web-test` performs triangulated verification
    Then the item is recorded as BUG with three-source attribution
    And a [BUG] discovery is created routing to Engineer

#### Scenario: Figma-triangulated verification detects STALE spec

    Given a web-testable feature has a Visual Specification with a Figma reference
    And a checklist item states "heading-lg font"
    And Figma has been updated to use "heading-xl" but spec still says "heading-lg"
    When `/pl-web-test` performs triangulated verification
    Then the item is recorded as STALE
    And the output notes Figma was updated but spec was not re-ingested
    And a PM action item is generated for re-ingestion

#### Scenario: Figma-triangulated verification detects token drift

    Given a web-testable feature has a Token Map with "spacing-md" -> "var(--spacing-md)"
    And Figma reports spacing-md resolved value is 20px
    And the app's computed --spacing-md value is 16px
    When `/pl-web-test` performs token verification
    Then the token entry is recorded as DRIFT
    And the output shows Figma=20px App=16px

#### Scenario: Three-source report format

    Given `/pl-web-test` has completed triangulated verification for a feature
    When results are printed
    Then the output includes a "Triangulated Verification" section
    And each item shows Figma, Spec, and App values
    And the Token Map section shows per-token comparison
    And a summary line shows counts by verdict type

#### Scenario: Regression scope respected

    Given a feature's `tests.json` has `regression_scope: "targeted:Scenario A"`
    When `/pl-web-test` is invoked for that feature
    Then only "Scenario A" is executed
    And all other manual scenarios and visual items are skipped

#### Scenario: Cosmetic scope skips feature

    Given a feature's `tests.json` has `regression_scope: "cosmetic"`
    When `/pl-web-test` is invoked for that feature
    Then the feature is skipped entirely with a note

#### Scenario: QA completion gate prompts for completion

    Given the invoking agent is QA
    And all scenarios and visual items passed with zero failures and zero inconclusive
    When results are presented
    Then the skill prompts to run `/pl-complete <name>`

#### Scenario: Engineer completion gate is summary only

    Given the invoking agent is Engineer
    And all scenarios and visual items passed
    When results are presented
    Then only a summary is printed
    And the skill suggests QA run `/pl-complete`

#### Scenario: Instruction files updated with web-verify references

    Given the skill file has been created
    When instruction updates are applied per Section 2.13
    Then `/pl-web-test` appears in both QA and Engineer authorized command lists
    And `/pl-web-test [name]` appears in all variants of both command tables
    And `> Web Test:` is documented in feature_format.md
    And visual_spec_convention.md references the automated alternative
    And visual_verification_protocol.md has a Section 5.4.7 for Playwright MCP

#### Scenario: Fixture-backed server started for scenario with fixture tag

    Given a feature has `> Web Test: http://localhost:9086`
    And the feature has `> Test Fixtures: https://github.com/org/fixtures.git`
    And a scenario's Given step references fixture tag "main/feature/scenario-one"
    When `/pl-web-test` processes that scenario
    Then the fixture tag is checked out to a temp directory
    And a dev server is started with `--project-root <fixture-dir> --port 0`
    And the ephemeral port from the server's stdout is used for navigation
    And the static URL port (9086) is NOT used

#### Scenario: Fixture checkout failure marks scenario inconclusive

    Given a feature has `> Test Fixtures: https://github.com/org/fixtures.git`
    And a scenario references fixture tag "main/feature/nonexistent-tag"
    When `/pl-web-test` attempts to check out the fixture
    Then the checkout fails (tag not found)
    And the scenario is marked INCONCLUSIVE
    And other scenarios in the feature continue normally

#### Scenario: Fixture cleanup after scenario completion

    Given a fixture-backed scenario has completed (pass or fail)
    When `/pl-web-test` moves to the next scenario
    Then the fixture-backed dev server has been stopped
    And the fixture checkout directory has been removed

#### Scenario: Legacy pl-web-verify references fully removed

    Given the pl-web-test skill file exists at `.claude/commands/pl-web-test.md`
    When a search is performed for "pl-web-verify" or "Web Testable" across all non-release-note files
    Then zero matches are found
    And the old skill file `.claude/commands/pl-web-verify.md` does not exist
    And the test directory is `tests/pl_web_test/` (not `tests/pl_web_verify/`)

### QA Scenarios

None.


## Regression Guidance
- Auto-discovery respects targeted/cosmetic scope from tests.json
- Server auto-start via Web Start metadata when server unreachable
- Old skill name (pl-web-verify) fully renamed -- zero references remain
- Role guard rejects PM invocation
