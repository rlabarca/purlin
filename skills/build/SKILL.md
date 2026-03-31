---
name: build
description: Implement features from specs with full CDD lifecycle. Writes CODE and TEST files
---

## Session Identity

When starting work on a feature, you MUST update the terminal identity with a short task label (3-4 words max) derived from the feature name or plan. Do NOT leave the label as the project name — always derive a work-specific label.

```bash
source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<task label>"
```

Examples: `(main) add auth flow`, `(dev/0.8.6) fix scan engine`.

---

## Scope

If an argument was provided, resolve the feature file via `features/**/<arg>.md` and implement it.
If no argument was provided, run `purlin:status` to get the current work list. Pick the highest-priority Engineer work item and begin implementing it.
Check `features/_tombstones/` first and process any pending tombstones before regular feature work. Processing a tombstone: read it, delete all listed files (test directories, regression JSON, QA scenarios), delete the companion artifacts alongside it (`features/_tombstones/<name>.impl.md`, `features/_tombstones/<name>.discoveries.md`), delete the tombstone file itself, regenerate the dependency graph, and commit.

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

## Active Skill Marker

Before any file writes, set the active skill marker to authorize writes through the write guard:

```bash
mkdir -p .purlin/runtime && echo "build" > .purlin/runtime/active_skill
```

Set this at skill start (before Step 0). Clear it at skill end (after Step 4 completes or on any early exit):

```bash
rm -f .purlin/runtime/active_skill
```

When using Execution Group Dispatch, set the marker before spawning workers and clear it after the merge protocol completes. Each worker in a worktree has its own `.purlin/runtime/` directory.

---

## Per-Feature Implementation Protocol

### Step 0 -- Pre-Flight (MANDATORY)

*   **Feature Resolution (mandatory before any writes):**
    1. **Feature name provided:** Resolve via `features/**/<name>.md`.
       - If found: proceed with that spec.
       - If NOT found: inform `"No spec exists for '<name>'. In Purlin, specs come before code."` Offer: `"Create one? (purlin:spec <name>)"`. If confirmed: invoke `purlin:spec <name>`, then STOP. If declined: STOP.
    2. **No feature name, but request targets specific file(s):** Run the Reverse Lookup Cascade (first confident match wins):
       - **Signal 1 — Path Convention** (DETERMINISTIC): `tests/<stem>/` → feature `<stem>`. `skills/<name>/` → feature `purlin_<name>`. No confirmation needed.
       - **Signal 2 — Companion Code Files** (HIGH confidence): Grep `## Code Files` sections in `features/**/*.impl.md` for the target path. If single match: proceed. Multiple matches: ask engineer to pick.
       - **Signal 3 — Commit Scope History** (MEDIUM confidence): `git log --oneline -20 -- <target_file>`. Extract `feat(<scope>):` patterns. Most frequent scope matching a known feature stem = match. Confirm with engineer if ambiguous.
       - **Signal 4 — Spec Content Search** (LOW-MEDIUM confidence): Use `purlin_scan` cached data to keyword-match the engineer's request against feature names, scenario titles, and requirement text. Always confirm. Present top 3 candidates.
    3. **No feature name, no specific file:** Run `purlin:status`, pick the highest-priority Engineer work item (existing behavior).
    4. **Resolution outcomes:**
       - High-confidence single match → state it and proceed: `"This belongs to feature '<name>'. Proceeding."`
       - Ambiguous / multiple matches → ask engineer to pick.
       - No match + `auto_create_features: true` (from `.purlin/config.json` `agents.purlin.auto_create_features`) → generate a feature spec from context (infer requirements from the code change, generate scenarios from the engineer's description, place in appropriate category folder) and proceed.
       - No match + `auto_create_features: false` (default) → offer three options: (a) Attach to an existing spec (show closest matches), (b) Create a new spec via `purlin:spec <name>`, (c) Continue as one-off (no feature tracking — marker still authorizes writes but no companion or sync tracking).
*   **Sync Ledger Check:** Read `.purlin/sync_ledger.json` for the target feature's entry (if the file exists). Surface relevant drift:
    *   If `sync_status` is `spec_ahead` (spec updated since last code change): warn `"Spec updated since last implementation — review spec changes before building."` This is advisory, not blocking.
    *   If `open_discoveries > 0`: warn `"Feature has N open discovery/ies — review before implementing."`
    *   If `sync_status` is `code_ahead` or `code_ahead_no_impl`: note that prior code changes exist without spec/impl updates — this is expected when resuming work.
    *   If the feature has no ledger entry or the ledger doesn't exist yet, skip silently (new features and projects without the ledger are normal).
*   **Re-Verification Detection:** Check scan results for this feature's `reset_context`. If `has_passing_tests: true` AND `scenario_diff.has_diff: false` AND `requirements_changed: false`, this is a re-verification task, NOT a new implementation task. Run existing tests, confirm they pass, and re-tag (skip to Step 3 -> Step 4). Do NOT re-implement existing code.
*   **Constraint Collection (MANDATORY):** Call `purlin_constraints` with the feature stem. This returns all constraint files governing the feature in one call: `anchors` (from transitive prerequisite tree), `scoped_invariants` (i_* files in the tree), and `global_invariants` (apply to all non-anchor features). **Read every file listed.** Anchors and invariants contain binding constraints that MUST be followed during implementation. Also read each ancestor spec listed in `ancestors` — especially those in `[TODO]` status, whose contracts may be unstable.
    If an anchor's domain intersects the feature but is NOT in the prerequisite tree, log `[DISCOVERY: missing Prerequisite link to <anchor_name>]` in the companion file.
*   **FORBIDDEN Pre-Scan:** From each constraint file (anchors + invariants from the collection above), extract `## FORBIDDEN Patterns`. For each pattern, grep the feature's code files (excluding paths classified as OTHER via `write_exceptions`). If violations found, **block the build**:
       ```
       INVARIANT VIOLATION -- build blocked
       i_policy_security.md (INV-3): No eval() in user-facing code
       Pattern: eval\(
       Found: tools/auth/handler.py:42
       Fix: Replace eval() with ast.literal_eval() or json.loads()
       ```
       Do NOT proceed to Step 1 until all FORBIDDEN violations are resolved.
*   **Behavioral Reminders:** Surface non-FORBIDDEN constraint statements from anchors and invariants as awareness reminders (not blockers).
*   **Figma Brief Staleness** (design invariants only): If the feature has a `brief.json` at `features/_design/<stem>/brief.json`, compare its version against the Figma invariant pointer's `> Version:`. Warn if stale.
*   **Visual Design Sources:** When the feature has a `## Visual Specification`, read in priority: Token Map (in spec) -> `brief.json` (at `features/_design/<stem>/brief.json`) -> Figma MCP (last resort, read-only).
*   **Web Test Readiness:** When the feature has `## Visual Specification` AND web test metadata (`> Web Test:` or `> AFT Web:`), check for Playwright MCP availability now (look for `browser_navigate` in the available tool list). If MCP is not available, attempt auto-setup: verify package via `npx @playwright/mcp@latest --help`, then run `claude mcp add playwright -- npx @playwright/mcp --headless`. If setup succeeds, inform the user a session restart is needed and HALT -- do not begin implementation without MCP ready. If the feature has `## Visual Specification` but NO web test metadata, log `[DISCOVERY: feature has Visual Specification but no web test URL -- visual verification cannot be automated]` in the companion file and continue.
*   **Companion File:** Read `<name>.impl.md (in the same folder as the spec)` if it exists. Also read prerequisite companion files.
*   **Prerequisite Stability:** For each non-anchor ancestor from the constraint collection that is in `[TODO]` status, log `[CLARIFICATION] Prerequisite <name> is in TODO -- reviewed spec for stability` in the companion file.
*   **Verify Status:** Confirm the target feature is in the expected state per CDD status.
*   **Role-Blocked Detection (delivery plan only):** When a delivery plan is active, check if the feature is role-blocked: `architect: TODO`, `builder: BLOCKED`, or `builder: INFEASIBLE`. If role-blocked, skip this feature with: `"Skipping <feature> -- <role> <status> (role-blocked)"`. Proceed to the next feature in the phase. See Phase Deferral Protocol below.
*   **New Scenario Detection:** Diff `#### Scenario:` headings against existing tests. New headings without coverage = real work. When `tests.json` reports `total: 0` or is missing, treat as "no tests exist."

### Step 1 -- Acknowledge and Plan

*   **Update terminal identity:** Derive a short task label (3-4 words max) from the feature name or delivery plan context. Call: `source ${CLAUDE_PLUGIN_ROOT}/scripts/terminal/identity.sh && update_session_identity "<task label>"`. Examples: `(main) add auth flow`, `(dev/0.8.6) fix scan engine`.
*   State which feature you are implementing.
*   Briefly outline your plan, referencing any companion file notes that influenced your strategy.

### Step 2 -- Implement and Document

*   Write code and tests. When tests need controlled project state (git history, branch topologies, config combinations), use fixture tags declared in the spec. Create fixtures as immutable git tags in a bare repo at `.purlin/runtime/fixture-repo` (or per `fixture_repo_url` in config). For simple state (one file, one env var), use inline setup instead.
*   **Knowledge Colocation:** Record non-obvious discoveries in `<name>.impl.md (in the same folder as the spec)` (never in the feature `.md`). Create the companion file if needed. See `${CLAUDE_PLUGIN_ROOT}/references/formats/companion_format.md` for the canonical companion file format.
*   **Companion Code Files Section:** When writing code files, maintain a `## Code Files` section in the companion (`<name>.impl.md`):
    *   If companion has `## Code Files` → append new file paths not already listed.
    *   If companion exists but has no `## Code Files` section → add the section listing all code files touched this session.
    *   If creating a new companion → always include `## Code Files` with the files being written.
    *   This section is the primary mechanism for reverse lookup (Signal 2) and should list every file the feature's implementation touches.
*   **Engineer Decision Tags:** Use these in companion files (`<name>.impl.md (in the same folder as the spec)`):
    *   `[CLARIFICATION]` (INFO) -- Interpreted ambiguous spec language.
    *   `[AUTONOMOUS]` (WARN) -- Spec was silent; you filled the gap.
    *   `[DEVIATION]` (HIGH) -- Intentionally diverged from spec. Blocks `[Complete]` until PM acknowledges.
    *   `[DISCOVERY]` (HIGH) -- Found unstated requirement. Blocks `[Complete]` until PM acknowledges.
    *   `[INFEASIBLE]` (CRITICAL) -- Cannot implement as specced. Halt work, skip to next feature.
    Format: `**[TAG]** <description> (Severity: <level>)`
    Cross-feature: file `[DISCOVERY]` in the **target feature's** companion file, not the originating feature.
*   **Invariant References in Companion Entries:** When code addresses a specific invariant constraint, companion entries SHOULD reference it: `[IMPL] Implemented correlation ID header per i_arch_api_standards.md INV-2`. When code deviates from an invariant, use `[DEVIATION]` referencing the invariant — but note that invariant deviations escalate as **invariant conflict** (harder than regular spec deviation, since invariants are immutable and externally-sourced). The deviation is surfaced to PM as "invariant conflict" rather than "spec deviation."
*   **Bug Fix Resolution:** When fixing an OPEN `[BUG]` in the discovery sidecar, update status from `OPEN` to `RESOLVED` in the same commit.
*   **Commit:** `git commit -m "feat(scope): implement FEATURE_NAME"`. No status tag in this commit.
*   **Sync Ledger Update:** After the commit succeeds, update the sync ledger:
    ```bash
    PURLIN_COMMIT_MSG="feat(scope): implement FEATURE_NAME" bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh"
    bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh" --sha "$(git rev-parse HEAD)"
    ```
    This records which features had code/spec changes and backfills the commit SHA. The `PURLIN_COMMIT_MSG` allows scope-based mapping for files that can't be mapped by path alone.

### Step 3 -- Verify Locally

*   **Unit tests:** Invoke `purlin:unit-test` for the complete testing protocol
    (quality rubric, anti-pattern checks, result reporting). The skill writes
    `tests/<feature_name>/tests.json` upon successful rubric gate passage.
*   **Design alignment verification (if eligible):** For features with
    `> Web Test:` or `> AFT Web:`, run `purlin:web-test` and iterate until zero
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
*   **Pre-check -- Companion File Gate (Advisory):**
    *   Check: were code commits made for this feature during this session?
    *   If yes: does the companion file (`<name>.impl.md (in the same folder as the spec)`) have new entries from this session? (Check file modification time or diff against the pre-build state.)
    *   If the companion file has NO new entries: **WARN** that companion debt exists. Recommend writing `[IMPL]` entries describing what was implemented. For deviations from spec, use the appropriate deviation tag (`[DEVIATION]`, `[DISCOVERY]`, etc.) instead of or in addition to `[IMPL]`.
    *   Allow the status tag commit to proceed. Companion debt is tracked in `purlin:status` and surfaced via the sync ledger. Debt can be reconciled in bulk via `purlin:spec-code-audit`.
*   **Pre-check -- Web Test Gate:**
    *   If the feature has `> Web Test:` or `> AFT Web:` metadata, confirm `purlin:web-test` passed with zero BUG and zero DRIFT verdicts this session before proceeding. If web test has not been run, block the status tag commit and run `purlin:web-test` first.
    *   If the feature has `## Visual Specification` but no `> Web Test:` or `> AFT Web:` metadata, confirm a DISCOVERY about missing web test URL has been logged in the companion file. If the DISCOVERY is not recorded, block the status tag commit until it is.
*   **Pre-check -- Spec & Plan Alignment Audit:**
    *   **Spec audit (always, when a feature spec exists):** Re-read `the feature spec`. Walk through each requirement in the Requirements section and each scenario in the Scenarios section. For each, verify the implementation addresses it. Check:
        *   **Unimplemented requirements:** Any requirement with no corresponding code or test. Log as `[DISCOVERY]` in the companion file if found.
        *   **Scenario coverage:** Each scenario's Given/When/Then should be exercised by a test. Missing coverage = block until addressed or logged as `[DEVIATION]` with justification.
        *   **Undocumented deviations:** Any implementation behavior that contradicts or extends the spec without a companion file entry. If found, write the appropriate tag (`[DEVIATION]`, `[AUTONOMOUS]`, `[CLARIFICATION]`) before proceeding.
    *   **Plan audit (when a design plan was used for this work):** If the session used a design plan document (e.g., a `*_PLAN.md` file, a delivery plan phase spec, or a plan referenced in the checkpoint), re-read the plan's relevant section. For each deliverable listed in the plan:
        *   Verify the deliverable exists and matches the plan's description.
        *   Check for items the plan specified that were skipped or only partially done. Log gaps as `[DISCOVERY]` in the companion file.
        *   Check for work done beyond the plan's scope — not a blocker, but note in companion as `[CLARIFICATION]` if non-trivial.
    *   This audit is **non-blocking** for clean results but **blocks on unlogged gaps.** The gate ensures every deviation between intent (spec/plan) and outcome (code) is documented in the companion file before the status tag. It does NOT require zero deviations — it requires zero *undocumented* deviations.
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
*   **C2. Sync Ledger:** `bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh" --sha "$(git rev-parse HEAD)"`
*   **D. Verify:** Run `purlin_scan` with `only: "features,plan"` and confirm expected state.
*   **E. Group check:** If a delivery plan exists, check phase completion status:
    *   **Phase fully complete** (all features done): Mark phase COMPLETE, record commit hash, commit plan update.
    *   **Phase complete with deferrals** (all non-blocked features done, only role-blocked features remain): Apply the Phase Deferral Protocol -- mark phase COMPLETE with `**Deferred:**` annotation, re-queue blocked features to a later phase, announce the deferral. See `${CLAUDE_PLUGIN_ROOT}/references/phased_delivery.md` Section 10.14.
    *   **Phase still has actionable features:** Continue the per-feature loop.
    *   When the entire execution group is complete (all member phases COMPLETE, including those completed with deferrals), check `auto_start`:
        *   **`auto_start: false` (default):** STOP the session:
            ```
            Execution group complete (Phases N, M of T) -- [short label]
            Recommended: run QA to verify completed phases. Relaunch Engineer for next group.
            ```
        *   **`auto_start: true`:** Auto-advance to the next execution group. If the next group has 2+ features total, the Execution Group Dispatch is mandatory (see bright-line rule). Begin dispatch or sequential loop for the next group. Continue until all groups are complete or context is exhausted.

---

> **Hard gates (companion file minimum, status tag pre-checks, FORBIDDEN pre-scan, re-verification fast path, etc.) are defined in the agent definition §14. They apply regardless of whether this skill was invoked.** This skill provides orchestration: step-by-step execution, parallel dispatch, merge protocol, and output formatting.

---

## Spec-Then-Build Chaining

When the engineer's request implies both spec and code changes (keywords: "update the spec", "change the requirement", "add a scenario and build it"):

1. Build detects spec change intent in the request.
2. Reverse lookup resolves the feature (or engineer provides it).
3. Build chains: clear its own marker → invoke `purlin:spec <feature>` (spec sets/clears its own marker) → re-set build marker → continue with implementation against the updated spec.
4. This avoids requiring the engineer to manually invoke two separate skills.

---

## Server Lifecycle

For dev server management during web test verification, invoke `purlin:server`. The skill handles port management, state tracking, cleanup, and user visibility.
