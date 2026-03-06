**Purlin command: shared (Builder, QA)**

If you are operating as the Purlin Architect Agent, respond: "This is a Builder/QA command. Ask your Builder or QA agent to run /pl-web-verify instead." and stop.

---

## Arguments

`/pl-web-verify [feature_name ...] [url_override]`

- `feature_name` (optional, repeatable): One or more feature names (without `features/` prefix or `.md` suffix).
- `url_override` (optional): A URL (starts with `http://` or `https://`) that overrides the `> Web Testable:` URL from the feature spec. Applies to all specified features.
- No arguments: auto-discover web-testable features in TESTING state.

---

## Execution Protocol

### Step 1 — Discovery

**If explicit feature names were provided:**
1. For each name, read `features/<name>.md`.
2. Check for `> Web Testable: <url>` metadata. If absent, skip with: "Feature `<name>` has no `> Web Testable:` metadata. Use `/pl-verify` for manual verification."
3. Extract the base URL from the metadata (or use the URL override argument if provided).

**If no arguments were provided:**
1. Run `tools/cdd/status.sh` and read `CRITIC_REPORT.md`.
2. Identify features in TESTING state.
3. For each TESTING feature, read the spec and check for `> Web Testable: <url>` metadata.
4. Only features with `> Web Testable:` are eligible. Skip all others silently.
5. If no web-testable features are found, inform the user: "No web-testable features found in TESTING state. Use `/pl-verify` for manual verification." and stop.

### Step 2 — Playwright MCP Pre-Check

1. Check whether Playwright MCP tools are available by looking for `browser_navigate` in the available tool list.
2. **If available:**
   a. Verify headless mode by reading the MCP server configuration. Check these files in order until one contains a `playwright` MCP entry:
      - `<project_root>/.claude/settings.local.json` → key `mcpServers.playwright.args`
      - `~/.claude.json` → key `mcpServers.playwright.args`
      If neither file exists or has a playwright entry, run `claude mcp list` and parse the output for the playwright server's arguments.
   b. **If the args array does NOT contain `--headless`:** Instruct the user to reconfigure:
      ```
      Playwright MCP is configured but not in headless mode.
      Headless mode is required (runs invisibly, avoids disrupting your screen, 20-30% faster).
      Please reconfigure:
        claude mcp remove playwright && claude mcp add playwright -- npx @playwright/mcp --headless
      Then restart the Claude Code session and re-run /pl-web-verify.
      ```
      Stop execution.
   c. **If the args array contains `--headless`:** Proceed to Step 3.
3. **If NOT available:**
   a. Attempt auto-setup: run `npx @playwright/mcp@latest --help` to verify the package is accessible.
   b. If the package is accessible, run: `claude mcp add playwright -- npx @playwright/mcp --headless`
   c. Inform the user: "Playwright MCP server has been configured in headless mode. Please restart the Claude Code session to load the new MCP server, then re-run `/pl-web-verify`."
   d. Stop execution. Do NOT attempt verification without Playwright MCP.
   e. If the package is NOT accessible, print the error and provide manual setup instructions:
      ```
      Playwright MCP auto-setup failed. Manual setup:
      1. npm install -g @playwright/mcp
      2. claude mcp add playwright -- npx @playwright/mcp --headless
      3. Restart Claude Code session
      4. Re-run /pl-web-verify
      ```
   f. Stop execution.

### Step 3 — Pre-Flight (Per Feature)

For each eligible feature:

1. Read `tests/<feature_name>/critic.json` for `regression_scope`.
2. **Scope filtering:**
   - `cosmetic` -> Skip with note: "Feature `<name>`: QA skip (cosmetic change)."
   - `dependency-only` with empty scenarios -> Skip with note: "Feature `<name>`: QA skip (dependency-only, no scenarios in scope)."
   - `targeted:Scenario A,Scenario B` -> Only verify the named scenarios and visual screens.
   - `full` (or missing/default) -> Verify all manual scenarios and visual spec items.
3. Extract Manual Scenarios from `### Manual Scenarios (Human Verification Required)`.
4. Extract Visual Specification items from `## Visual Specification` (if present).
5. If a feature has neither manual scenarios nor visual spec items after scope filtering, skip it with a note.

### Step 3.5 — Dynamic Port Resolution and Liveness (Per Feature)

For each eligible feature, resolve the final URL before navigating:

1. **Determine effective URL** using this priority order:
   a. **URL override from command argument** — If the user provided a URL argument, use it as-is. Skip steps 2-4.
   b. **Runtime port file** — Read the feature spec for `> Web Port File: <path>` metadata. If present:
      - Read the file at `<PROJECT_ROOT>/<path>`.
      - If the file exists and contains a valid port number (digits only, trimmed), replace the port in the `> Web Testable:` URL with this runtime port.
      - If the file does not exist or is empty, fall through to the `> Web Testable:` URL.
   c. **Spec URL** — Use the `> Web Testable:` URL as-is (fallback).

2. **Liveness check:** Attempt to reach the resolved URL:
   - Use `curl -s -o /dev/null -w "%{http_code}" <resolved_url>` via Bash to check if the server responds.
   - A 200-level or 300-level response means the server is alive.

3. **Auto-start (if not reachable):** If the liveness check fails:
   a. Check the feature spec for `> Web Start: <command>` metadata.
   b. If present, invoke the start command (e.g., run the slash command or shell command).
   c. Wait for the port file to appear (poll every 1 second, up to 10 seconds).
   d. Re-read the port file for the updated port.
   e. Retry the liveness check at the updated URL.
   f. If still not reachable after auto-start, report the error and skip this feature (continue with others).

4. **No start command:** If the server is not reachable and no `> Web Start:` metadata exists, report: "Server not reachable at `<resolved_url>`. No `> Web Start:` command configured." and skip this feature (continue with others).

### Step 4 — Browser Setup

For each eligible feature:

1. Navigate to the **resolved URL** (from Step 3.5) via `browser_navigate`.
2. Verify the page loads (check for non-error response).
3. If the page fails to load, report: "Failed to load `<url>`. Please verify the server is running." and skip this feature.

### Step 5 — Manual Scenario Execution

For each in-scope manual scenario:

1. Read the Given/When/Then steps from the feature spec.
2. Translate each step into Playwright MCP actions:
   - **Given** (preconditions): Use `browser_navigate`, `browser_evaluate` to set up state.
   - **When** (actions): Use `browser_click`, `browser_type`, `browser_hover`, `browser_navigate`.
   - **Then/And** (verifications): Use `browser_screenshot` and `browser_evaluate` to capture state.
3. Execute actions sequentially following Gherkin step order.
4. At each Then/And verification point:
   - Take a screenshot via `browser_screenshot`.
   - Evaluate DOM/JS state via `browser_evaluate` as needed.
   - Use vision analysis of the screenshot combined with DOM state to determine PASS or FAIL.
5. Record results with evidence (screenshot observations, DOM values, JS evaluation results).
6. For steps requiring something outside the browser (file system, environment, email):
   - Use Bash tools when feasible.
   - Otherwise mark as INCONCLUSIVE with a reason note recommending manual verification via `/pl-verify`.

### Step 6 — Visual Spec Verification

For each in-scope visual spec screen:

1. Navigate to the appropriate page/view state via Playwright MCP.
2. Set up required state (hover, expand, switch themes) via `browser_click`, `browser_hover`, etc.
3. Take a full-page screenshot via `browser_screenshot`.
4. Analyze the screenshot against each checklist item using vision.
5. For interaction-dependent items (hover effects, transitions):
   - Execute the interaction via Playwright MCP.
   - Take another screenshot.
   - Verify the expected visual change.
6. Record PASS/FAIL per checklist item with observation notes.

### Step 7 — Result Recording

1. Print a summary table:
   ```
   === Web Verification Results: <feature_name> ===
   Manual Scenarios: N passed, M failed, K inconclusive / T total
   Visual Spec:      N passed, M failed / T total
   ```

2. **For failures:** Record each as a `[BUG]` discovery in the feature's `## User Testing Discoveries` section using this format:
   ```
   ### [BUG] <title> (Discovered: YYYY-MM-DD)
   - **Scenario:** <scenario name>
   - **Observed Behavior:** <what was observed from screenshot/DOM analysis>
   - **Expected Behavior:** <from the spec>
   - **Action Required:** Builder
   - **Status:** OPEN
   ```
   Commit discovery entries: `git commit -m "qa(<scope>): [BUG] - web-verify findings"`

3. **For inconclusive items:** List them with recommendation: "The following items could not be automated. Use `/pl-verify` for manual verification."

### Step 8 — Completion Gate

**Detect invoking role** by checking the system prompt for role identity markers ("Role Definition: The Builder" vs "Role Definition: The QA Agent").

**QA Agent invocation:**
- If all scenarios and visual items passed (zero failures, zero inconclusive): prompt "All web verification passed. Run `/pl-complete <name>` to mark done?"
- If confirmed, run `/pl-complete <name>`.

**Builder invocation:**
- If all passed: print summary only. Add note: "Suggest QA agent run `/pl-complete <name>` after verification."
- Do NOT mark complete.
