**Purlin command owner: Builder**

If you are not operating as the Purlin Builder, respond: "This is a Builder command. Ask your Builder agent to run /pl-build instead." and stop.

---

## Scope

If an argument was provided, implement the named feature from `features/<arg>.md`.
If no argument was provided, read `CRITIC_REPORT.md` (or `tools/cdd/status.sh --role builder` output), identify the highest-priority Builder action item, and begin implementing it.
Check `features/tombstones/` first and process any pending tombstones before regular feature work.

If a delivery plan exists at `.purlin/delivery_plan.md`, scope work to the current phase only. Each phase is a separate session -- halt after completing a phase (see Step 4.E).

---

## Parallel B1 Check (delivery plan phases with 2+ features)

If a delivery plan exists and the current phase has 2+ features:

1. Run `python3 tools/delivery/phase_analyzer.py --intra-phase <current_phase>`.
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
*   **Companion File:** Read `features/<name>.impl.md` if it exists. Also read prerequisite companion files.
*   **Verify Status:** Confirm the target feature is in the expected state per CDD status.
*   **Fixture Detection:** If the spec contains a fixture tag section (`### 2.x ... Fixture Tags`), run `/pl-fixture` for setup.
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

*   **Tests:** Run feature-specific tests. Results to `tests/<feature_name>/tests.json` with `{"status": "PASS", "passed": N, "failed": 0, "total": N}`. `total` MUST be > 0. File MUST be produced by an actual test runner (anti-stub mandate).
*   **Test Quality Self-Audit:** Audit each test against `features/policy_test_quality.md`: (1) Deletion test -- would it fail if implementation deleted? (2) Anti-pattern scan (AP-1 through AP-5). (3) Value assertion check. Record audit in companion file under `### Test Quality Audit`.
*   **Web test (if eligible):** For features with `> Web Test:`, run `/pl-web-test` and iterate until zero BUG verdicts.
*   **Self-Test Completeness:** Validate `tests.json`: required fields present, `total > 0`, no inconsistencies.
*   If tests fail, fix and repeat from Step 2.

### Step 4 -- Status Tag Commit (SEPARATE COMMIT)

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
*   **D. Verify:** Run `tools/cdd/status.sh` and confirm expected state.
*   **E. Phase check:** If a delivery plan exists and this feature completes the current phase: update plan to COMPLETE, record commit hash, commit plan update. Then STOP the session:
    ```
    Phase N of M complete -- [short label]
    Recommended: run QA to verify Phase N. Relaunch Builder for Phase N+1.
    ```
