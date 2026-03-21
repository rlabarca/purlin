**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-build instead." and stop.

---

## Path Resolution

Read `.purlin/config.json` and extract `tools_root` (default: `"tools"`). Resolve project root via `PURLIN_PROJECT_ROOT` env var or by climbing from CWD until `.purlin/` is found. Set `TOOLS_ROOT = <project_root>/<tools_root>`.

---

## Scope

If an argument was provided, implement the named feature from `features/<arg>.md`.
If no argument was provided, read `CRITIC_REPORT.md` (or `${TOOLS_ROOT}/cdd/status.sh --role builder` output), identify the highest-priority Builder action item, and begin implementing it.
Check `features/tombstones/` first and process any pending tombstones before regular feature work.

If a delivery plan exists at `.purlin/delivery_plan.md`, scope work to the current phase only. Each phase is a separate session -- halt after completing a phase (see Step 4.E).

---

## Parallel B1 Check (delivery plan phases with 2+ features)

If a delivery plan exists and the current phase has 2+ features:

1. Run `python3 ${TOOLS_ROOT}/delivery/phase_analyzer.py --intra-phase <current_phase>`.
2. If a `parallel: true` group exists with 2+ features:
   - Announce: "Features X and Y are independent -- building in parallel."
   - Launch one Agent call per feature with `isolation: "worktree"`, each running Steps 0-2 only (see `instructions/references/phased_delivery.md` Section 10.13).
   - Each agent prompt: "Implement feature X ONLY. Steps 0-2 only. No tests, no web tests, no status tags. Do NOT modify the delivery plan."
   - Merge returned branches: `git merge <branch> --no-edit`. On conflict: `git merge --abort`, then re-run that feature sequentially.
   - After all groups complete, proceed to B2 (full verification on merged code).
3. If no `parallel: true` groups exist, or the phase has only 1 feature: use the existing sequential per-feature loop below.

---

## Per-Feature Implementation Protocol

### Step 0 -- Pre-Flight (MANDATORY)

*   **Re-Verification Detection:** Check the Critic's `reset_context` for this feature. If `has_passing_tests: true` AND `scenario_diff.has_diff: false` AND `requirements_changed: false`, this is a re-verification task, NOT a new implementation task. Run existing tests, confirm they pass, and re-tag (skip to Step 3 -> Step 4). Do NOT re-implement existing code.
*   **Anchor Review:** Check session-preloaded anchor constraints. Identify FORBIDDEN patterns and INVARIANTs applicable to this feature. If an anchor's domain intersects but is not listed in `> Prerequisite:` links, log `[DISCOVERY: missing Prerequisite link to <anchor_name>]` in the companion file.
*   **Visual Design Sources:** When the feature has a `## Visual Specification`, read in priority: Token Map (in spec) -> `brief.json` (at `features/design/<stem>/brief.json`) -> Figma MCP (last resort, read-only).
*   **Web Test Readiness:** When the feature has `## Visual Specification` AND web test metadata (`> Web Test:` or `> AFT Web:`), check for Playwright MCP availability now (look for `browser_navigate` in the available tool list). If MCP is not available, attempt auto-setup: verify package via `npx @playwright/mcp@latest --help`, then run `claude mcp add playwright -- npx @playwright/mcp --headless`. If setup succeeds, inform the user a session restart is needed and HALT -- do not begin implementation without MCP ready. If the feature has `## Visual Specification` but NO web test metadata, log `[DISCOVERY: feature has Visual Specification but no web test URL -- visual verification cannot be automated]` in the companion file and continue.
*   **Companion File:** Read `features/<name>.impl.md` if it exists. Also read prerequisite companion files.
*   **Prerequisite Stability:** For each `> Prerequisite:` link to a non-anchor feature, check if that feature is in `[TODO]` status. If so, read its full spec (`features/<prereq>.md`) to understand the unstable contract. Log `[CLARIFICATION] Prerequisite <name> is in TODO -- reviewed spec for stability` in the companion file.
*   **Verify Status:** Confirm the target feature is in the expected state per CDD status.
*   **New Scenario Detection:** Diff `#### Scenario:` headings against existing tests. New headings without coverage = real work. When `tests.json` reports `total: 0` or is missing, treat as "no tests exist."

### Step 1 -- Acknowledge and Plan

*   State which feature you are implementing.
*   Briefly outline your plan, referencing any companion file notes that influenced your strategy.

### Step 2 -- Implement and Document

*   Write code and tests.
*   **Knowledge Colocation:** Record non-obvious discoveries in `features/<name>.impl.md` (never in the feature `.md`). Create the companion file if needed.
*   **Builder Decision Tags:** Use these in companion files (`features/<name>.impl.md`):
    *   `[CLARIFICATION]` (INFO) -- Interpreted ambiguous spec language.
    *   `[AUTONOMOUS]` (WARN) -- Spec was silent; you filled the gap.
    *   `[DEVIATION]` (HIGH) -- Intentionally diverged from spec. Blocks `[Complete]` until Architect acknowledges.
    *   `[DISCOVERY]` (HIGH) -- Found unstated requirement. Blocks `[Complete]` until Architect acknowledges.
    *   `[INFEASIBLE]` (CRITICAL) -- Cannot implement as specced. Halt work, skip to next feature.
    Format: `**[TAG]** <description> (Severity: <level>)`
    Cross-feature: file `[DISCOVERY]` in the **target feature's** companion file, not the originating feature.
*   **Bug Fix Resolution:** When fixing an OPEN `[BUG]` in the discovery sidecar, update status from `OPEN` to `RESOLVED` in the same commit.
*   **Commit:** `git commit -m "feat(scope): implement FEATURE_NAME"`. No status tag in this commit.

### Step 3 -- Verify Locally

*   **Unit tests:** Invoke `/pl-unit-test` for the complete testing protocol
    (quality rubric, anti-pattern checks, result reporting). The skill writes
    `tests/<feature_name>/tests.json` upon successful rubric gate passage.
*   **Design alignment verification (if eligible):** For features with
    `> Web Test:` or `> AFT Web:`, run `/pl-web-test` and iterate until zero
    BUG and DRIFT verdicts (see bright-line rules). When the feature has
    Figma-referenced Visual Specifications, this step verifies the
    implementation matches the Figma design.
*   If tests fail, fix and repeat from Step 2.

### Step 4 -- Status Tag Commit (SEPARATE COMMIT)

*   **Pre-check -- Web Test Gate:**
    *   If the feature has `> Web Test:` or `> AFT Web:` metadata, confirm `/pl-web-test` passed with zero BUG and zero DRIFT verdicts this session before proceeding. If web test has not been run, block the status tag commit and run `/pl-web-test` first.
    *   If the feature has `## Visual Specification` but no `> Web Test:` or `> AFT Web:` metadata, confirm a DISCOVERY about missing web test URL has been logged in the companion file. If the DISCOVERY is not recorded, block the status tag commit until it is.
*   **A. Determine tag:**
    *   Zero manual scenarios + all verification passes: `[Complete features/FILENAME.md]` (COMPLETE). Do NOT include `[Verified]` -- reserved for QA.
    *   Has manual scenarios: `[Ready for Verification features/FILENAME.md]` (TESTING).
*   **B. Declare scope:** Append `[Scope: ...]` to commit message.

    | Scope | When |
    |-------|------|
    | `full` | Behavioral change, new scenarios. Default. |
    | `targeted:A,B` | Only specific scenarios affected. Names must match `#### Scenario:` titles. |
    | `cosmetic` | Non-functional change (formatting, logging). Verify Critic has ZERO HIGH/CRITICAL items first. |
    | `dependency-only` | Prerequisite update, no direct code changes. |

*   **C. Commit:** `git commit --allow-empty -m "status(scope): TAG [Scope: <type>]"`
*   **D. Verify:** Run `${TOOLS_ROOT}/cdd/status.sh` and confirm expected state.
*   **E. Phase check:** If a delivery plan exists and this feature completes the current phase: update plan to COMPLETE, record commit hash, commit plan update. Then STOP the session:
    ```
    Phase N of M complete -- [short label]
    Recommended: run QA to verify Phase N. Relaunch Builder for Phase N+1.
    ```
