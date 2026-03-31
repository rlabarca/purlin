# Feature: Purlin Sync System

> Label: "Tool: Purlin Sync System"
> Category: "Framework Core"
> Prerequisite: purlin_resume.md

## 1. Overview

The sync system tracks the relationship between feature specs, code, and implementation documentation. It observes file writes and commits to detect when code drifts ahead of specs (or vice versa), surfacing sync status per feature in `purlin:status`. A write guard protects INVARIANT files and blocks writes to unclassified paths. All file types are writable by any user — enforcement is limited to source-of-truth protection (INVARIANT) and classification completeness (UNKNOWN).

---

## 2. Requirements

### 2.1 File Classification

Every file in a Purlin project is classified into one of six categories. Classification determines sync tracking behavior and write guard rules.

| Classification | Description | Examples |
|---------------|-------------|----------|
| **CODE** | Source code, tests, scripts, skill files, instruction files, `.impl.md` companions | `scripts/`, `tests/`, `skills/`, `agents/`, `*.impl.md` |
| **SPEC** | Feature specifications, design anchors, policy anchors | `features/**/*.md` (excluding `.impl.md`, `.discoveries.md`, `_invariants/`) |
| **QA** | QA artifacts: discoveries, regression JSON, scenario tags | `*.discoveries.md`, `tests/qa/`, regression JSON |
| **INVARIANT** | External-source-of-truth files managed by `purlin:invariant` | `features/_invariants/i_*.md` |
| **OTHER** | Files explicitly excepted from code tracking via `write_exceptions` config | `docs/`, `README.md`, `LICENSE` |
| **UNKNOWN** | Files matching no classification rule | Any unmatched path |

**Classification resolution order:**
1. Custom rules from the project's `CLAUDE.md` (`## Purlin File Classifications` section)
2. Built-in rules in `config_engine.classify_file()` (framework defaults)
3. Write exceptions from `.purlin/config.json` `write_exceptions` array → OTHER
4. If still unmatched: UNKNOWN

**Write exceptions format in `.purlin/config.json`:**
```json
{
  "write_exceptions": ["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]
}
```
- Trailing `/` = directory prefix match (`docs/` matches `docs/anything`).
- No trailing `/` = exact filename match at project root (`README.md`).
- OTHER files are freely editable without a skill — no feature tracking needed.
- Managed via `purlin:classify add|remove|list`.

**Custom classification format in CLAUDE.md:**

```markdown
## Purlin File Classifications
- `docs/` -> SPEC
- `config/` -> CODE
- `static/` -> CODE
```

- Valid classifications: `CODE`, `SPEC`, `QA`. INVARIANT cannot be assigned via CLAUDE.md.
- Patterns use prefix matching (`path.startswith(pattern)`), not substring matching.
- Custom rules are evaluated before built-in rules and override defaults.
- Plugin files receive absolute paths from the write guard, so project-relative custom rules do not affect plugin internals.

### 2.2 Write Guard (PreToolUse: Write|Edit|NotebookEdit)

The write guard is a `PreToolUse` hook on `Write`, `Edit`, and `NotebookEdit`. It implements a three-bucket decision tree that routes writes through skills for tracking, while keeping system files and OTHER files freely editable.

**Decision tree (evaluated in order, first match wins):**

```
1. .purlin/* or .claude/*                   → ALLOW (system files)
2. features/_invariants/i_*                 → check invariant bypass lock
                                               lock matches → ALLOW
                                               no lock      → BLOCK
3. features/*                               → check active_skill marker
                                               present → ALLOW
                                               absent  → BLOCK (use spec skill)
4. classify_file() returns OTHER            → ALLOW (freely editable)
5. everything else (CODE/QA/UNKNOWN)        → check active_skill marker
                                               present → ALLOW
                                               absent  → BLOCK (use purlin:build)
                                               UNKNOWN → BLOCK (add classification)
```

**Block messages are actionable:** each blocked write tells the agent exactly which skill to use, or how to set the escape hatch marker for a one-off edit.

#### 2.2.1 INVARIANT Bypass for purlin:invariant

The `purlin:invariant` skill writes INVARIANT files through a bypass lock protocol:
1. Before writing, create `.purlin/runtime/invariant_write_lock` via Bash.
2. The write guard checks for this lock file. If present, INVARIANT writes are allowed.
3. After writing, remove the lock file.

This is the only mechanism that bypasses INVARIANT protection.

#### 2.2.2 Hook Blocking Invariant (stderr required for exit code 2)

Claude Code `PreToolUse` hooks block tool calls via exit code 2. The error message MUST be written to **stderr** (`>&2`), not stdout. Claude Code ignores stdout for exit-code-2 hooks. If stderr is empty, the tool call proceeds despite the non-zero exit code.

**Invariant:** Every `echo ... ; exit 2` pair in a guard hook script MUST use `echo "..." >&2`.

#### 2.2.3 UNKNOWN File Handling

When the write guard blocks an UNKNOWN file, the error message instructs the agent to:
1. Ask the user which classification applies.
2. Add the classification to the project's CLAUDE.md under `## Purlin File Classifications`.
3. Retry the write (the guard reads CLAUDE.md on each invocation).

#### 2.2.4 Active Skill Marker Protocol

File: `.purlin/runtime/active_skill`

Skills that write files set this marker at start and clear it at end. The write guard checks for this marker at steps 3 and 5 of the decision tree. If the file exists and is non-empty, writes are authorized.

**Lifecycle:**
1. Skill sets marker: `mkdir -p .purlin/runtime && echo "<skill-name>" > .purlin/runtime/active_skill`
2. Skill performs writes (write guard allows them via marker check).
3. Skill clears marker: `rm -f .purlin/runtime/active_skill`
4. `session-init-identity.sh` clears stale markers on session start.

**Marker values by skill type:**
- Spec writers: `spec`, `anchor`, `discovery`, `propose`, `tombstone`, `spec-from-code`, `spec-code-audit`, `infeasible`, `spec-catch-up`
- Code writers: `build`, `unit-test`, `regression`, `smoke`, `fixture`, `toolbox`, `verify`
- Invariant: `invariant` (plus existing bypass lock for invariant files)
- Escape hatch: `direct` (for one-off edits outside skill workflow)

**Constraints:**
- One skill at a time per session; worktrees have separate runtime dirs.
- Empty marker file is treated as absent (non-empty check).
- The marker does NOT bypass INVARIANT protection (step 2 takes precedence).

### 2.3 Sync Tracking: Two Layers

Sync tracking uses two complementary data stores to detect drift between specs and code.

#### 2.3.1 Layer 1: Session Tracking (`sync_state.json` — runtime, ephemeral)

Tracks every file write in the current session. Populated by the `sync-tracker.sh` FileChanged hook.

- **Created:** On the first file write of the session.
- **Cleared:** On session start.
- **Location:** `.purlin/runtime/sync_state.json` (gitignored).

**Structure:**
```json
{
  "features": {
    "<feature_stem>": {
      "code_files": ["scripts/webhook.py"],
      "test_files": ["tests/webhook_delivery/test_send.py"],
      "spec_changed": false,
      "impl_changed": false,
      "first_code_change": "2026-03-30T14:00:00Z"
    }
  },
  "unclassified_writes": ["utils/helpers.py"]
}
```

**Population logic (sync-tracker.sh FileChanged hook):**
1. Determine file type from path — no external classifier needed (see 2.4).
2. Skip tracking for: `.purlin/`, `.claude/`, `__pycache__/`, lock files, project meta (README, LICENSE, CHANGELOG, CLAUDE.md).
3. Map file to feature stem (see 2.4 Feature Stem Mapping).
4. Update `sync_state.json`:
   - Spec file (`features/<cat>/<stem>.md`): set `features[stem].spec_changed = true`, set `first_spec_change`.
   - Impl file (`features/<cat>/<stem>.impl.md`): set `features[stem].impl_changed = true`.
   - Discoveries file (`features/<cat>/<stem>.discoveries.md`): set `features[stem].qa_changed = true`.
   - Code file (everything else with a stem): add to `code_files` or `test_files`, set `first_code_change`.
   - Unmatched files (no stem): add to `unclassified_writes`.

#### 2.3.2 Layer 2: Committed Sync Ledger (`sync_ledger.json` — committed to git)

Updated on every git commit via a pre-commit hook. This is the cross-session source of truth.

- **Location:** `.purlin/sync_ledger.json` (committed to git).

**Structure:**
```json
{
  "<feature_stem>": {
    "last_code_commit": "abc123",
    "last_code_date": "2026-03-30T14:00:00Z",
    "last_spec_commit": "def456",
    "last_spec_date": "2026-03-30T10:00:00Z",
    "last_impl_commit": "ghi789",
    "last_impl_date": "2026-03-30T14:05:00Z",
    "sync_status": "synced",
    "open_discoveries": 0,
    "regression_status": "PASS"
  }
}
```

**Update logic (sync-ledger-update.sh, called from skill commit steps):**
1. Read staged files: `git diff --cached --name-only`.
2. Determine file type from path and map to feature stem (see 2.4). No external classifier needed.
3. Group by feature: which features had code, spec, or impl changes.
4. For unmapped files: if `PURLIN_COMMIT_MSG` is set, extract the scope from the conventional commit format `type(scope):` and use it as a fallback stem (only if the scope matches a known feature).
5. For each affected feature, update `last_{code|spec|impl}_commit` and `last_{code|spec|impl}_date`.
6. Recompute `sync_status` (see 2.5).
7. Stage updated `sync_ledger.json`.

**Invocation:** Skills call the ledger update after committing, then backfill the SHA:
```bash
PURLIN_COMMIT_MSG="feat(scope): ..." bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh"
bash "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/sync-ledger-update.sh" --sha "$(git rev-parse HEAD)"
```

#### 2.3.3 Layer 3: Git Log (fallback)

For features not yet in the ledger (predating its introduction), sync status can be inferred from git log timestamps:
1. `git log --format='%H %ct' -- features/<cat>/<stem>.md` (spec commits)
2. `git log --format='%H %ct' -- tests/<stem>/` (code commits)
3. `git log --format='%H %ct' -- features/<cat>/<stem>.impl.md` (impl commits)

This is the degraded path — less precise than the ledger.

### 2.4 Feature Stem Mapping

File type (spec vs code) and feature stem are determined entirely from the path. No external classifier is needed — this keeps sync tracking stable as the project evolves. The rule is: files under `features/` are specs (or impl/discoveries); everything else is code.

**Stem extraction rules (evaluated in order, first match wins):**

| Pattern | Stem | Type |
|---------|------|------|
| `features/<category>/<stem>.impl.md` | `<stem>` | impl |
| `features/<category>/<stem>.discoveries.md` | `<stem>` | qa |
| `features/<category>/<stem>.md` | `<stem>` | spec |
| `tests/<stem>/` | `<stem>` | code |
| `skills/<name>/` | `purlin_<name>` (if feature exists) | code |
| Commit scope fallback (ledger only) | scope from `type(scope):` message | code |
| No match | `unclassified_writes` | -- |

**Skill-to-feature mapping:** `skills/<name>/` maps to `purlin_<name>` only when a feature spec with that stem exists in `features/`. The set of known stems is discovered dynamically by scanning `features/*/` at runtime. If no matching feature exists, the file stays unclassified.

**Commit scope fallback (ledger only):** When `PURLIN_COMMIT_MSG` is set and a file can't be mapped by path, the scope is extracted from the conventional commit format (`feat(purlin_build): ...` -> `purlin_build`). The scope must match a known feature stem. This handles shared infrastructure files (scripts/, hooks/) committed as part of a specific feature's work.

System directories are excluded from mapping: `features/_tombstones/`, `features/_digests/`, `features/_design/`, `features/_invariants/`.

### 2.5 Sync Status Computation

For each feature, the sync status is computed from which file types changed in a commit:

| Code changed | Spec changed | Impl changed | Status |
|-------------|-------------|-------------|--------|
| Yes | No | No | `code_ahead` |
| Yes | No | Yes | `synced` (impl documents the code change) |
| Yes | Yes | - | `synced` (both sides updated) |
| No | Yes | No | `spec_ahead` |
| No | No | Yes | Keep existing (impl update alone resolves debt) |
| - | - | - | `new` (spec exists, no code yet) |

Additional status: `unknown` when insufficient data exists to determine sync state.

### 2.6 How `/status` Composes the Full Picture

For each feature:
1. Read `sync_ledger.json` for committed sync state (cross-session).
2. Overlay `sync_state.json` for in-session changes not yet committed.
3. Read QA state:
   - `regression_status` from `tests/<stem>/regression.json`
   - `open_discoveries` count from `features/<cat>/<stem>.discoveries.md`
   - `scenario_count` from `tests/qa/scenarios/<stem>.json`
4. Compose final status: in-session changes override ledger (more recent). QA state merged in.

### 2.7 Concurrent Agents and Worktrees

- Each worktree has its own `.purlin/runtime/sync_state.json` — session tracking is independent per worktree.
- Each worktree branch has its own copy of `.purlin/sync_ledger.json` — updated independently by commits in that branch.
- When a worktree merges back, the main session does not inherit the worktree's `sync_state.json` (it is gitignored). The main session detects merged state from git on the next `/status` invocation.
- Workers do not need mode activation. Their scope comes from agent instructions (build writes code, spec writes specs), not from enforcement.
- Parallel workers on different features produce independent ledger entries that merge cleanly (different JSON keys). Workers on the same feature produce merge conflicts — a real coordination issue that requires human resolution.

### 2.8 Spec Catch-Up Reconciliation

When features are in `code_ahead` status, the `purlin:spec-catch-up` skill provides lightweight reconciliation. It reads sync tracking data to identify which code files changed since the last spec update, analyzes the gap between spec and code, and proposes targeted spec additions/revisions for PM approval.

**Workflow:**
1. Load sync ledger + session state to find `code_ahead` features.
2. For each target feature: read changed code files (from ledger timestamps), read existing spec, read companion file if present.
3. Analyze gaps: new requirements, changed behavior, missing scenarios, metadata gaps.
4. Present a structured proposal to the PM. No changes are applied without explicit approval.
5. On approval: update the spec, auto-create `.impl.md` if missing (with Source Mapping), commit both together.
6. Single commit containing spec + impl resolves the feature to `synced` via standard ledger computation (§2.5).

**Invocation:**
- `purlin:spec-catch-up <feature_name>` — catch up a specific feature.
- `purlin:spec-catch-up` — discover all `code_ahead` features and offer to catch up each.

**Surfacing:** `purlin:status` and `purlin:whats-different` include `purlin:spec-catch-up` hints alongside `code_ahead` features, creating a "see problem → take action" flow.

### 2.9 Companion File Convention

The `.impl.md` companion file is a documentation artifact. It records what was built, flags deviations, and helps collaborators understand changes.

**Convention (advisory, not enforced):**
- Every code change for a feature SHOULD include a companion file update.
- Minimum entry: a single `[IMPL]` line.
- For deviations: use `[DEVIATION]`, `[DISCOVERY]`, `[AUTONOMOUS]`, `[CLARIFICATION]`, or `[INFEASIBLE]` tags. See `${CLAUDE_PLUGIN_ROOT}/references/active_deviations.md`.
- `purlin:build` pre-flight warns (non-blocking) if impl is missing or stale.
- `purlin:status` surfaces code-ahead-of-spec per feature when impl is not updated.

**What changed from the mode system:** Companion files are no longer enforced via a mode-switch gate. The "companion debt" blocker is removed. Instead, sync tracking records when code changes without impl updates, and `/status` surfaces this as advisory information.

#### 2.9.1 Code Files Companion Section

The companion MAY include a `## Code Files` section listing every code file the feature's implementation touches:

```markdown
## Code Files
- src/auth/login.ts
- src/auth/session.ts
- src/middleware/auth_guard.ts
```

This section is the primary mechanism for reverse lookup (Signal 2) — connecting arbitrary code files back to their feature.

**Build behavior:**
- When build touches code files, it appends them to `## Code Files` if the section exists.
- If the section doesn't exist and the companion already has content, build adds the section.
- For new companions, build always creates it.
- Over time, companions accumulate code file references through normal build usage, making reverse lookup increasingly reliable.

### 2.10 Reverse Lookup Cascade

When `purlin:build` is invoked without a feature name but with a specific file or change description, it resolves the target feature through a reverse lookup cascade. The cascade evaluates signals from fast/deterministic to slow/heuristic — the first confident match wins.

#### Signal 1: Path Convention (instant, DETERMINISTIC)
- `tests/<stem>/` → feature `<stem>`
- `skills/<name>/` → feature `purlin_<name>` (if feature exists)

No confirmation needed.

#### Signal 2: Companion Code Files Section (fast grep, HIGH confidence)
Search `## Code Files` sections in `.impl.md` companions for the target path. If found, the companion's feature stem is the match. No confirmation needed (unless multiple matches).

#### Signal 3: Commit Scope History (git log, MEDIUM confidence)
Search recent commits touching the target file for conventional scopes (`feat(scope):`). Most frequent scope matching a known feature stem is the match. Confirm with engineer if not obvious.

#### Signal 4: Spec Content Search (scan cache, LOW-MEDIUM confidence)
Search feature names, scenario titles, and requirement text for keywords matching the engineer's request. Always confirm with engineer — present top 3 candidates.

**Resolution flow:**
- High-confidence match (Signal 1-2): state the match and proceed.
- Medium-confidence match (Signal 3): confirm with engineer.
- Low-confidence / ambiguous: ask engineer to choose.
- No match: offer to create spec, attach to existing, or continue one-off.

### 2.11 auto_create_features Config

`.purlin/config.json`:
```json
{
  "agents": {
    "purlin": {
      "auto_create_features": false
    }
  }
}
```

When `true`: If reverse lookup finds no match, build auto-creates a feature spec (inferred from code context) and proceeds without prompting.

When `false` (default): Build asks the engineer to pick an existing feature, create a new one, or continue as a one-off (no feature tracking).

### 2.12 Terminal Identity

On skill invocation and feature work, update the terminal identity.

**Format:** `(<branch or worktree label>) <project name or task label>`

**Examples:**
- `(main) purlin` — startup, no active task
- `(dev/0.8.6) building webhook_delivery` — active build work
- `(W1) verifying auth` — worktree with active QA

**Signature:** `update_session_identity [label]` — label defaults to project name if omitted. Context (branch/worktree) is auto-detected. Skills pass task-specific labels.

### 2.13 Commit Guidance

- Commit at logical milestones — never defer all commits until session end.
- Status tag commits MUST be separate, standalone commits.
- Use conventional commit prefixes: `feat()`, `fix()`, `test()`, `spec()`, `design()`, `qa()`, `status()`.
- See `${CLAUDE_PLUGIN_ROOT}/references/commit_conventions.md` for full format.
- If committing code without a spec or impl update, the pre-commit hook prints a non-blocking advisory: the sync ledger records the feature as `code_ahead`.

---

## 3. Scenarios

### Unit Tests

#### Scenario: INVARIANT file write blocked @auto

    Given a file classified as INVARIANT (features/_invariants/i_figma_design.md)
    When the agent attempts to write to it
    Then the write is blocked with exit code 2
    And the error message says "Use purlin:invariant sync to update from the external source."

#### Scenario: INVARIANT bypass via lock file @auto

    Given .purlin/runtime/invariant_write_lock exists
    When the agent attempts to write to features/_invariants/i_figma_design.md
    Then the write is allowed

#### Scenario: UNKNOWN file write blocked @auto

    Given a file matching no classification rule (e.g., unknown/file.xyz)
    When the agent attempts to write to it
    Then the write is blocked with exit code 2
    And the error message includes the CLAUDE.md format for adding a classification

#### Scenario: CODE file blocked without active_skill marker @auto

    Given no active_skill marker exists
    When the agent attempts to write to scripts/webhook.py
    Then the write is blocked with exit code 2
    And the error message says "requires purlin:build"

#### Scenario: CODE file allowed with active_skill marker @auto

    Given .purlin/runtime/active_skill contains "build"
    When the agent writes to scripts/webhook.py
    Then the write is allowed
    And sync_state.json contains an entry for the mapped feature

#### Scenario: SPEC file blocked without active_skill marker @auto

    Given no active_skill marker exists
    When the agent attempts to write to features/integrations/webhook_delivery.md
    Then the write is blocked with exit code 2
    And the error message says "Use purlin:spec"

#### Scenario: SPEC file allowed with active_skill marker @auto

    Given .purlin/runtime/active_skill contains "spec"
    When the agent writes to features/integrations/webhook_delivery.md
    Then the write is allowed
    And sync_state.json records spec_changed = true for webhook_delivery

#### Scenario: OTHER file freely editable without marker @auto

    Given write_exceptions in .purlin/config.json includes "docs/"
    And no active_skill marker exists
    When the agent writes to docs/guide.md
    Then the write is allowed (OTHER — no skill required)

#### Scenario: Active skill marker does not bypass INVARIANT @auto

    Given .purlin/runtime/active_skill contains "build"
    And no invariant_write_lock exists
    When the agent attempts to write to features/_invariants/i_figma_design.md
    Then the write is blocked (INVARIANT protection takes precedence)

#### Scenario: Session start clears stale active_skill marker @auto

    Given .purlin/runtime/active_skill exists from a previous session
    When a new session starts (session-init-identity.sh runs)
    Then .purlin/runtime/active_skill is removed

#### Scenario: Escape hatch marker allows one-off edits @auto

    Given .purlin/runtime/active_skill contains "direct"
    When the agent writes to any non-INVARIANT file
    Then the write is allowed

#### Scenario: Custom CLAUDE.md classification overrides UNKNOWN @auto

    Given CLAUDE.md contains "## Purlin File Classifications" with "- `docs/` -> SPEC"
    When classify_file("docs/guide.md") is called
    Then it returns "SPEC" (not UNKNOWN)

#### Scenario: Custom classification enforced by write guard @auto

    Given CLAUDE.md classifies docs/ as SPEC
    And docs/ files are classified as SPEC
    When the agent writes to docs/guide.md
    Then the write is allowed (SPEC is a valid classification)

#### Scenario: Custom rules evaluated before built-in rules @auto

    Given CLAUDE.md classifies "tests/fixtures/" as CODE
    When classify_file("tests/fixtures/data.json") is called
    Then it returns "CODE" (custom rule wins)

#### Scenario: INVARIANT cannot be assigned via CLAUDE.md @auto

    Given CLAUDE.md contains "- `secrets/` -> INVARIANT"
    When classify_file("secrets/keys.json") is called
    Then it returns "UNKNOWN" (INVARIANT assignment ignored)
    And the write guard blocks the write

#### Scenario: Plugin files immune to project custom rules @auto

    Given a consumer project's CLAUDE.md contains "- `skills/` -> SPEC"
    When classify_file("/Users/.../plugins/purlin/skills/build/SKILL.md") is called with an absolute path
    Then it returns "CODE" (absolute path, custom prefix rule does not match)

#### Scenario: Sync state tracks code change without spec update

    Given the agent writes scripts/webhook.py (mapped to webhook_delivery)
    And the agent does not write features/integrations/webhook_delivery.md
    When purlin:status is invoked
    Then webhook_delivery shows as "code ahead"

#### Scenario: Sync state tracks spec change without code update

    Given the agent writes features/integrations/webhook_delivery.md
    And the agent does not write any code files for webhook_delivery
    When purlin:status is invoked
    Then webhook_delivery shows as "spec ahead"

#### Scenario: Both code and spec changed shows synced

    Given the agent writes scripts/webhook.py and features/integrations/webhook_delivery.md
    When purlin:status is invoked
    Then webhook_delivery shows as "synced"

#### Scenario: Impl update resolves code-ahead debt

    Given the sync ledger shows webhook_delivery as "code_ahead"
    When the agent commits features/integrations/webhook_delivery.impl.md
    Then webhook_delivery shows as "synced" in the ledger

#### Scenario: Skill file maps to feature via purlin_ prefix @auto

    Given features/skills_engineer/purlin_build.md exists (known feature stem)
    When skills/build/SKILL.md is staged and the ledger update runs
    Then the ledger has an entry for purlin_build (not "build" or "SKILL")
    And sync_status is code_ahead (code change, no spec change)

#### Scenario: Skill with no matching feature stays unmapped @auto

    Given no feature spec exists with stem purlin_nonexistent
    When skills/nonexistent/SKILL.md is staged and the ledger update runs
    Then the ledger has no entry for purlin_nonexistent
    And no false feature entries are created

#### Scenario: Commit scope maps unmapped code files to feature @auto

    Given features/skills_engineer/purlin_build.md exists (known feature stem)
    And scripts/mcp/some_engine.py is staged (no path-based stem match)
    When the ledger update runs with PURLIN_COMMIT_MSG="feat(purlin_build): add engine"
    Then the ledger maps some_engine.py to purlin_build via commit scope extraction
    And sync_status is code_ahead

#### Scenario: Unmapped file without commit scope stays out of ledger @auto

    Given scripts/mcp/random_util.py is staged (no path-based stem match)
    When the ledger update runs with no PURLIN_COMMIT_MSG
    Then the ledger remains empty (no false entries created)

#### Scenario: Tracker maps skill file to feature @auto

    Given features/skills_engineer/purlin_build.md exists (known feature stem)
    When the sync tracker fires for skills/build/SKILL.md
    Then sync_state.json has purlin_build in features (not unclassified_writes)
    And purlin_build.code_files contains skills/build/SKILL.md

#### Scenario: Tracker excludes system directories @auto

    When the sync tracker fires for features/_tombstones/old_feature.md
    Then sync_state.json has no entry for old_feature
    When the sync tracker fires for features/_invariants/i_arch_api.md
    Then sync_state.json has no entry for i_arch_api

#### Scenario: Tracker maps discoveries to feature with qa_changed @auto

    When the sync tracker fires for features/skills_engineer/purlin_build.discoveries.md
    Then sync_state.json has purlin_build with qa_changed = true

#### Scenario: Scan engine composes ledger and session state @auto

    Given the ledger has purlin_build as code_ahead
    And sync_state.json has purlin_build with session code writes
    When scan_sync_ledger() runs
    Then the result includes purlin_build with sync_status and session_pending

#### Scenario: Session start clears sync state @auto

    Given sync_state.json has entries from a previous session
    When a new session starts
    Then sync_state.json is cleared

#### Scenario: Parallel worktrees have independent sync tracking

    Given worktree A tracks writes for feature_a
    And worktree B tracks writes for feature_b
    Then worktree A's sync_state.json does not contain feature_b entries
    And worktree B's sync_state.json does not contain feature_a entries

#### Scenario: Worktree merge does not inherit sync state

    Given worktree A merges feature_a branch back to main
    Then the main session's sync_state.json is unchanged
    And the main session detects merged state from git on next /status

#### Scenario: Spec catch-up resolves code-ahead to synced

    Given the sync ledger shows webhook_delivery as "code_ahead"
    And the PM runs purlin:spec-catch-up webhook_delivery
    When the PM approves the proposed spec changes
    Then features/integrations/webhook_delivery.md is updated with new requirements and scenarios
    And features/integrations/webhook_delivery.impl.md exists (created if missing)
    And a single commit contains both the spec and impl changes
    And the sync ledger shows webhook_delivery as "synced"

#### Scenario: Spec catch-up discovers all code-ahead features

    Given the sync ledger has auth_middleware as "code_ahead" and webhook_delivery as "code_ahead"
    When the PM runs purlin:spec-catch-up with no arguments
    Then both features are listed with timestamps showing the drift gap
    And the PM can choose to catch up all or one at a time

#### Scenario: Status and whats-different surface spec-catch-up hint

    Given the sync ledger shows auth_middleware as "code_ahead"
    When purlin:status or purlin:whats-different is invoked
    Then the output includes "purlin:spec-catch-up" as a recommended action

#### Scenario: Reverse lookup via path convention @auto

    Given tests/auth_login/ directory maps to feature auth_login
    When purlin:build is invoked with target "tests/auth_login/test_timeout.py"
    Then reverse lookup Signal 1 matches feature auth_login (DETERMINISTIC)
    And build proceeds without confirmation

#### Scenario: Reverse lookup via companion Code Files section @auto

    Given auth_login.impl.md contains "## Code Files" listing src/auth/login.ts
    When purlin:build targets src/auth/login.ts
    Then reverse lookup Signal 2 matches feature auth_login (HIGH confidence)
    And build states the match and proceeds

#### Scenario: Reverse lookup no match with auto_create_features false @auto

    Given no feature matches the target code file
    And auto_create_features is false (default)
    When purlin:build is invoked
    Then build offers: attach to existing spec, create new spec, or continue one-off

#### Scenario: Reverse lookup no match with auto_create_features true @auto

    Given no feature matches the target code file
    And auto_create_features is true in .purlin/config.json
    When purlin:build is invoked
    Then build auto-creates a feature spec from code context
    And proceeds to implement against the new spec

#### Scenario: Build maintains Code Files companion section @auto

    Given purlin:build writes src/auth/session.ts for feature auth_login
    And auth_login.impl.md has a "## Code Files" section
    When build completes
    Then src/auth/session.ts is listed in the "## Code Files" section

#### Scenario: Build creates Code Files section for new companion @auto

    Given purlin:build creates a new .impl.md companion for feature rate_limiter
    When the companion is written
    Then it includes a "## Code Files" section listing all files touched

#### Scenario: classify_work_items includes other_files_changed count @auto

    Given sync_state.json has unclassified_writes entries
    When classify_work_items() runs
    Then the result includes other_files_changed with the count of unclassified writes

### QA Scenarios

#### Scenario: No skill references purlin_mode @auto

    Given the project after sync system migration
    When searching all skills/*/SKILL.md files
    Then no file contains "purlin_mode" (as an MCP tool call)

#### Scenario: No agent definition references purlin_mode @auto

    Given the project after sync system migration
    When searching all agents/*.md files
    Then no file contains "purlin_mode(" (as an MCP tool call)

#### Scenario: Old mode artifacts deleted @auto

    Given the project after sync system migration
    When checking the project directory
    Then features/framework_core/purlin_mode_system.md does not exist
    And skills/mode/ directory does not exist

## Regression Guidance

**Automated regression suite:** `tests/qa/scenarios/purlin_sync_system.json`
- `write-guard-enforcement` -- INVARIANT/UNKNOWN blocking, bypass lock, classification resolution
- `sync-state-tracking` -- session state population, feature stem mapping, session clear
- `sync-ledger-updates` -- pre-commit ledger updates, status computation, post-commit SHA backfill
- `file-classification-rules` -- classify_file() correctness for all file types, custom rules
- `concurrent-agent-isolation` -- independent sync state per worktree, ledger merge behavior

**Manual verification:**
- Run /build on a feature, confirm code writes tracked in sync_state.json
- Run /spec on same feature, confirm spec_changed recorded
- Run /status, confirm per-feature sync status displayed
- Edit invariant file, confirm blocked with correct message
- Run parallel build, confirm workers track independently
- Commit with sync debt, confirm non-blocking advisory appears
