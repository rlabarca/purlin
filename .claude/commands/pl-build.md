**Purlin mode: Engineer**

Purlin agent: This skill activates Engineer mode. If another mode is active, confirm switch first.

---

## Path Resolution

> See `instructions/references/path_resolution.md`. Produces `TOOLS_ROOT`.
> **Commit format:** See `instructions/references/commit_conventions.md`.
> **File ownership:** See `instructions/references/file_classification.md`.
> **Companion files:** See `instructions/references/active_deviations.md` for deviation format and PM review protocol.

---

## Scope

If an argument was provided, implement the named feature from `features/<arg>.md`.
If no argument was provided, run `/pl-status` to get the current work list. Pick the highest-priority Engineer work item and begin implementing it.
Check `features/tombstones/` first and process any pending tombstones before regular feature work. Processing a tombstone: read it, delete all listed files (test directories, regression JSON, QA scenarios), delete the companion artifacts alongside it (`features/tombstones/<name>.impl.md`, `features/tombstones/<name>.discoveries.md`), delete the tombstone file itself, regenerate the dependency graph, and commit.

If a delivery plan exists at `.purlin/delivery_plan.md`, scope work to the current phase only. When `auto_start` is `false` (default), halt after completing a phase (see Step 4.E). When `auto_start` is `true`, auto-advance to the next PENDING phase (see Step 4.E).

---

## Execution Group Dispatch (delivery plan with 2+ features)

If a delivery plan exists and has PENDING phases:

1. **Build execution groups:** Read `.purlin/cache/dependency_graph.json` and the delivery plan. For each pair of PENDING phases, check if any feature in Phase A depends (transitively) on any feature in Phase B. Group phases with no cross-dependencies into execution groups. Phases are authoring units; groups are scheduling units.
2. **Identify the current group:** The first group containing non-COMPLETE phases is the active execution group.
3. **Dispatch the group:**
   - Mark all phases in the group as IN_PROGRESS in the delivery plan.
   - Collect all features across all member phases.
   - Check pairwise feature independence within the group using the dependency graph.
   - For independent features (2+): announce "Features X and Y are independent -- building in parallel." Spawn one `engineer-worker` sub-agent per feature (see `.claude/agents/engineer-worker.md`). Each sub-agent runs in an isolated worktree and executes Steps 0-2 only.
   - For dependent features or single features: use the sequential per-feature loop below.
   - Merge returned branches using the **Robust Merge Protocol** (below).
   - After all features complete, run B2 across all group features.
4. **Coupling detection (advisory):** Use Grep to scan test files for shared source imports and `git log` for commit file overlap between parallel features. Report findings as advisory warnings -- they do NOT block parallel dispatch. The merge protocol is the safety net.
5. **Phase completion within groups:** Individual phases within a group complete independently. If one phase's features all pass while another has a stuck feature, the completed phase is marked COMPLETE and QA can verify it immediately. The incomplete phase becomes a singleton group on the next session.
6. **Group boundary:** When all phases in a group are COMPLETE, check `auto_start`:
   - `auto_start: false` (default): STOP the session (see Step 4.E).
   - `auto_start: true`: advance to the next execution group.
7. **Worktree branch naming:** Encode the phase in the branch name: `worktree-phase<N>-<feature_stem>`.

If the delivery plan has only 1 PENDING phase with 1 feature, skip group analysis and use the sequential per-feature loop directly.

### Robust Merge Protocol

After all parallel `engineer-worker` sub-agents complete, merge branches sequentially:

1. For each returned branch: `git rebase HEAD <branch>`.
2. On rebase conflict: check if ALL conflicting files are in the **safe list**:
   - **Safe files:** `.purlin/delivery_plan.md`, `.purlin/cache/scan.json`, `.purlin/cache/*`.
   - Safe: auto-resolve by keeping main's version (`git checkout --ours <file>`, `git add <file>`, `git rebase --continue`).
   - Unsafe (any non-safe file in conflict): `git rebase --abort`, fall back to sequential for THIS feature only.
3. Loop up to 20 rebase iterations for multi-commit branches.
4. After successful rebase: fast-forward merge (`git merge <branch> --no-edit`).
5. On merge conflict: same safe-file auto-resolve, then complete merge. Unsafe conflict = sequential fallback.
6. Already-merged features from other branches are preserved -- only the failing feature falls back.

---

## Per-Feature Implementation Protocol

### Step 0 -- Pre-Flight (MANDATORY)

*   **Spec Existence Check:** If a feature name was provided as an argument, verify `features/<name>.md` exists. If it does NOT exist:
    1. Inform the user: `"No spec exists for '<name>'. In Purlin, specs come before code."`
    2. Offer: `"Switch to PM mode to create the spec? (/pl-spec <name>)"`
    3. If confirmed: switch to PM mode and invoke `/pl-spec <name>`. STOP — do not continue with /pl-build.
    4. If declined: STOP — do not implement without a spec.
*   **Re-Verification Detection:** Check scan results for this feature's `reset_context`. If `has_passing_tests: true` AND `scenario_diff.has_diff: false` AND `requirements_changed: false`, this is a re-verification task, NOT a new implementation task. Run existing tests, confirm they pass, and re-tag (skip to Step 3 -> Step 4). Do NOT re-implement existing code.
*   **Anchor Review:** Check session-preloaded anchor constraints. Identify FORBIDDEN patterns and INVARIANTs applicable to this feature. If an anchor's domain intersects but is not listed in `> Prerequisite:` links, log `[DISCOVERY: missing Prerequisite link to <anchor_name>]` in the companion file.
*   **Visual Design Sources:** When the feature has a `## Visual Specification`, read in priority: Token Map (in spec) -> `brief.json` (at `features/design/<stem>/brief.json`) -> Figma MCP (last resort, read-only).
*   **Web Test Readiness:** When the feature has `## Visual Specification` AND web test metadata (`> Web Test:` or `> AFT Web:`), check for Playwright MCP availability now (look for `browser_navigate` in the available tool list). If MCP is not available, attempt auto-setup: verify package via `npx @playwright/mcp@latest --help`, then run `claude mcp add playwright -- npx @playwright/mcp --headless`. If setup succeeds, inform the user a session restart is needed and HALT -- do not begin implementation without MCP ready. If the feature has `## Visual Specification` but NO web test metadata, log `[DISCOVERY: feature has Visual Specification but no web test URL -- visual verification cannot be automated]` in the companion file and continue.
*   **Companion File:** Read `features/<name>.impl.md` if it exists. Also read prerequisite companion files.
*   **Prerequisite Stability:** For each `> Prerequisite:` link to a non-anchor feature, check if that feature is in `[TODO]` status. If so, read its full spec (`features/<prereq>.md`) to understand the unstable contract. Log `[CLARIFICATION] Prerequisite <name> is in TODO -- reviewed spec for stability` in the companion file.
*   **Verify Status:** Confirm the target feature is in the expected state per CDD status.
*   **Role-Blocked Detection (delivery plan only):** When a delivery plan is active, check if the feature is role-blocked: `architect: TODO`, `builder: BLOCKED`, or `builder: INFEASIBLE`. If role-blocked, skip this feature with: `"Skipping <feature> -- <role> <status> (role-blocked)"`. Proceed to the next feature in the phase. See Phase Deferral Protocol below.
*   **New Scenario Detection:** Diff `#### Scenario:` headings against existing tests. New headings without coverage = real work. When `tests.json` reports `total: 0` or is missing, treat as "no tests exist."

### Step 1 -- Acknowledge and Plan

*   State which feature you are implementing.
*   Briefly outline your plan, referencing any companion file notes that influenced your strategy.

### Step 2 -- Implement and Document

*   Write code and tests.
*   **Knowledge Colocation:** Record non-obvious discoveries in `features/<name>.impl.md` (never in the feature `.md`). Create the companion file if needed.
*   **Engineer Decision Tags:** Use these in companion files (`features/<name>.impl.md`):
    *   `[CLARIFICATION]` (INFO) -- Interpreted ambiguous spec language.
    *   `[AUTONOMOUS]` (WARN) -- Spec was silent; you filled the gap.
    *   `[DEVIATION]` (HIGH) -- Intentionally diverged from spec. Blocks `[Complete]` until PM acknowledges.
    *   `[DISCOVERY]` (HIGH) -- Found unstated requirement. Blocks `[Complete]` until PM acknowledges.
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

*   **Pre-check -- Clean Working Tree Gate:**
    *   Run `git status --short`. Check for:
        *   **Uncommitted tracked changes:** All files modified during this build MUST be committed before the status tag. If uncommitted changes exist, commit them with the appropriate `feat()`/`fix()`/`test()` prefix.
        *   **Untracked files:** For each untracked file, determine: is it a generated artifact (cache, log, build output) or a file that should be tracked? Generated artifacts → add to `.gitignore` and commit the gitignore change. Trackable files → `git add` and commit. Do NOT leave untracked files behind.
    *   The status tag commit MUST be on a clean working tree. No dangling changes.
*   **Pre-check -- Companion File Gate (Mechanical):**
    *   Check: were code commits made for this feature during this session?
    *   If yes: does the companion file (`features/<name>.impl.md`) have new entries from this session? (Check file modification time or diff against the pre-build state.)
    *   If the companion file has NO new entries: **BLOCK the status tag commit.** Write at least `[IMPL]` entries describing what was implemented. For deviations from spec, use the appropriate deviation tag (`[DEVIATION]`, `[DISCOVERY]`, etc.) instead of or in addition to `[IMPL]`.
    *   This is a mechanical check — "did the companion file get updated?" — not a judgment call about whether the code deviated from the spec. Every code change gets documented.
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
    | `cosmetic` | Non-functional change (formatting, logging). Verify scan results show ZERO HIGH/CRITICAL items first. |
    | `dependency-only` | Prerequisite update, no direct code changes. |

*   **C. Commit:** `git commit --allow-empty -m "status(scope): TAG [Scope: <type>]"`
*   **D. Verify:** Run `${TOOLS_ROOT}/cdd/scan.sh --only features,plan` and confirm expected state.
*   **E. Group check:** If a delivery plan exists, check phase completion status:
    *   **Phase fully complete** (all features done): Mark phase COMPLETE, record commit hash, commit plan update.
    *   **Phase complete with deferrals** (all non-blocked features done, only role-blocked features remain): Apply the Phase Deferral Protocol -- mark phase COMPLETE with `**Deferred:**` annotation, re-queue blocked features to a later phase, announce the deferral. See `instructions/references/phased_delivery.md` Section 10.14.
    *   **Phase still has actionable features:** Continue the per-feature loop.
    *   When the entire execution group is complete (all member phases COMPLETE, including those completed with deferrals), check `auto_start`:
        *   **`auto_start: false` (default):** STOP the session:
            ```
            Execution group complete (Phases N, M of T) -- [short label]
            Recommended: run QA to verify completed phases. Relaunch Engineer for next group.
            ```
        *   **`auto_start: true`:** Auto-advance to the next execution group. If the next group has 2+ features total, the Execution Group Dispatch is mandatory (see bright-line rule). Begin dispatch or sequential loop for the next group. Continue until all groups are complete or context is exhausted.

---

## Bright-Line Rules (always active)

These rules are authoritative. They apply to all Engineer work regardless of context.

*   **Companion file edits do NOT reset status.** Only edits to the feature spec (`<name>.md`) trigger resets.
*   **Status tag MUST be a separate commit** from implementation work.
*   **`tests.json` MUST be produced by an actual test runner** -- never hand-written. Required fields: `status`, `passed`, `failed`, `total`. `total` MUST be > 0. See `/pl-unit-test` Section 5 for the full reporting protocol (including inline harness execution).
*   **`[Verified]` tag is QA-only.** Engineer mode MUST NOT include `[Verified]` in `[Complete]` commits.
*   **Chat is not a communication channel.** Use `/pl-propose` to record findings.
*   **Cross-cutting triage:** (A) When a user instruction implies a convention or constraint beyond the current feature ("from now on...", "always...", "never...", or scope exceeds this task), ask whether to record a `[SPEC_PROPOSAL: NEW_ANCHOR]` via `/pl-propose` or treat as one-off (`[CLARIFICATION]`). (B) When a fix reveals an undocumented technical constraint (platform requirements, environment rules, infrastructure patterns) not captured in any anchor node, log a `[SPEC_PROPOSAL: NEW_ANCHOR]` in the companion file via `/pl-propose` describing the constraint, the proposed anchor type and name, and the invariants it should establish. Use `[DISCOVERY]` only when the constraint fits within an existing anchor node's scope and just needs to be noted for PM mode's awareness.
*   **Re-verification, not re-implementation:** When scan results show `lifecycle_reset` with `has_passing_tests: true` and no scenario diff, run existing tests and re-tag. Do NOT re-implement existing code.
*   **Test quality:** Invoke `/pl-unit-test` for the complete testing protocol. The skill carries the quality rubric gate (6 checks), anti-pattern scan (AP-1 through AP-5), and result reporting rules. Do not execute the testing workflow from memory.
*   **Web test TBD resolution:** If a feature has `> Web Test: TBD` or `> Web Start: TBD`, Engineer mode MUST replace `TBD` with the actual URL and start command after building the server (e.g., `> Web Test: http://localhost:3000`, `> Web Start: npm run dev`). This spec edit resets the feature to TODO, but since tests already pass, Engineer mode follows the re-verification fast path (run tests, re-tag). Commit the metadata update before running `/pl-web-test`.
*   **Design alignment verification (web test):** Features with `> Web Test:` or `> AFT Web:` metadata (non-TBD) MUST pass `/pl-web-test` (zero BUG verdicts AND zero DRIFT verdicts) before status tag. When Figma MCP is available and the feature's `## Visual Specification` has Figma references, `/pl-web-test` performs Figma-triangulated verification -- Engineer mode MUST iterate until the live app matches the Figma design (no BUG or DRIFT). STALE verdicts (Figma updated but spec not yet re-ingested) are NOT Engineer blockers. For each STALE verdict, create a `[DISCOVERY]` entry in the feature's discovery sidecar (`features/<name>.discoveries.md`) with `Action Required: PM` and status `OPEN`. These are routed directly to PM. Engineer mode proceeds with the status tag -- STALE does not block completion. Features with a `## Visual Specification` section but NO web test metadata (`> Web Test:` / `> AFT Web:`) MUST log `[DISCOVERY: feature has Visual Specification but no web test URL -- design alignment verification cannot be automated]` in the companion file.
*   **Status tag pre-check gate:** Before composing any status tag commit, verify: (1) if the feature has `> Web Test:` or `> AFT Web:` metadata, confirm `/pl-web-test` passed with zero BUG/DRIFT verdicts this session; (2) if the feature has `## Visual Specification` but no web test metadata, confirm the DISCOVERY has been logged. Do NOT proceed with the status tag until these checks pass.
*   **Regression feedback:** When processing regression `regression.json` results and a test failure is caused by a stale scenario assertion (not a code bug), create a `[BUG]` discovery with `Action Required: QA` and title prefix `test-scenario:`. Do NOT modify scenario JSON files or harness scripts -- these are QA-owned.
*   **Regression handoff:** When regression-related work completes (result processing, harness framework building, or fixture tag creation), print the appropriate handoff message per `features/regression_testing.md` Section 2.12 before concluding the session.
*   **Execution group dispatch is mandatory for multi-feature groups.** When an execution group contains 2+ independent features (across all its member phases), MUST read `dependency_graph.json`, check pairwise independence, and spawn `engineer-worker` sub-agents for independent features BEFORE beginning Step 0 for any feature. Sequential processing of independent features without checking the dependency graph is a protocol violation.

---

## Server Lifecycle

For dev server management during web test verification, invoke `/pl-server`. The skill handles port management, state tracking, cleanup, and user visibility.
