# Feature: Purlin Sync System

> Label: "Tool: Purlin Sync System"
> Category: "Framework Core"
> Prerequisite: purlin_resume.md

## 1. Overview

The sync system tracks the relationship between feature specs, code, and implementation documentation. It observes file writes and commits to detect when code drifts ahead of specs (or vice versa), surfacing sync status per feature in `purlin:status`. A write guard protects INVARIANT files and blocks writes to unclassified paths. All file types are writable by any user — enforcement is limited to source-of-truth protection (INVARIANT) and classification completeness (UNKNOWN).

---

## 2. Requirements

### 2.1 File Classification

Every file in a Purlin project is classified into one of five categories. Classification determines sync tracking behavior and write guard rules.

| Classification | Description | Examples |
|---------------|-------------|----------|
| **CODE** | Source code, tests, scripts, skill files, instruction files, `.impl.md` companions | `scripts/`, `tests/`, `skills/`, `agents/`, `*.impl.md` |
| **SPEC** | Feature specifications, design anchors, policy anchors | `features/**/*.md` (excluding `.impl.md`, `.discoveries.md`, `_invariants/`) |
| **QA** | QA artifacts: discoveries, regression JSON, scenario tags | `*.discoveries.md`, `tests/qa/`, regression JSON |
| **INVARIANT** | External-source-of-truth files managed by `purlin:invariant` | `features/_invariants/i_*.md` |
| **UNKNOWN** | Files matching no classification rule | Any unmatched path |

**Classification resolution order:**
1. Custom rules from the project's `CLAUDE.md` (`## Purlin File Classifications` section)
2. Built-in rules in `config_engine.classify_file()` (framework defaults)
3. If still unmatched: UNKNOWN

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

The write guard is a `PreToolUse` hook on `Write`, `Edit`, and `NotebookEdit`. It classifies the target file and enforces two rules:

1. **INVARIANT files are blocked.** Error message: `"Use purlin:invariant sync to update from the external source."`
2. **UNKNOWN files are blocked.** Error message: `"Add a rule to CLAUDE.md: \`<path>\` -> CODE (or SPEC)."`

All other classifications (CODE, SPEC, QA) are allowed unconditionally. There is no role-based access control.

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
1. Classify file via `classify_file()`.
2. Skip tracking for: `.purlin/`, `.claude/`, `__pycache__/`, lock files, project meta (README, LICENSE, CHANGELOG, CLAUDE.md). Skip INVARIANT and QA classifications.
3. Map file to feature stem (see 2.4 Feature Stem Mapping).
4. Update `sync_state.json`:
   - CODE file: add to `features[stem].code_files`, set `first_code_change` if not set.
   - SPEC file: set `features[stem].spec_changed = true`, set `first_spec_change`.
   - `.impl.md` file: set `features[stem].impl_changed = true`.
   - Unmatched code files: add to `unclassified_writes`.

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

**Update logic (sync-ledger-update.sh pre-commit hook):**
1. Read staged files: `git diff --cached --name-only`.
2. Classify each staged file and map to feature stem.
3. Group by feature: which features had CODE, SPEC, or IMPL changes.
4. For each affected feature, update `last_{code|spec|impl}_commit` and `last_{code|spec|impl}_date`.
5. Recompute `sync_status` (see 2.5).
6. Update `open_discoveries` (count from `.discoveries.md`).
7. Update `regression_status` (from `regression.json`).
8. Stage updated `sync_ledger.json`.

A post-commit companion backfills commit SHA fields (SHA is unknown during pre-commit) using `git rev-parse HEAD`.

#### 2.3.3 Layer 3: Git Log (fallback)

For features not yet in the ledger (predating its introduction), sync status can be inferred from git log timestamps:
1. `git log --format='%H %ct' -- features/<cat>/<stem>.md` (spec commits)
2. `git log --format='%H %ct' -- tests/<stem>/` (code commits)
3. `git log --format='%H %ct' -- features/<cat>/<stem>.impl.md` (impl commits)

This is the degraded path — less precise than the ledger.

### 2.4 Feature Stem Mapping

Files are mapped to feature stems for sync tracking using these rules:

| Pattern | Stem |
|---------|------|
| `features/<category>/<stem>.md` | `<stem>` |
| `features/<category>/<stem>.impl.md` | `<stem>` |
| `features/<category>/<stem>.discoveries.md` | `<stem>` |
| `tests/<stem>/` | `<stem>` |
| `skills/<name>/SKILL.md` | Attempt match via skill-to-feature mapping |
| Other code files | `unclassified_writes` (no feature association) |

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

### 2.8 Companion File Convention

The `.impl.md` companion file is a documentation artifact. It records what was built, flags deviations, and helps collaborators understand changes.

**Convention (advisory, not enforced):**
- Every code change for a feature SHOULD include a companion file update.
- Minimum entry: a single `[IMPL]` line.
- For deviations: use `[DEVIATION]`, `[DISCOVERY]`, `[AUTONOMOUS]`, `[CLARIFICATION]`, or `[INFEASIBLE]` tags. See `${CLAUDE_PLUGIN_ROOT}/references/active_deviations.md`.
- `purlin:build` pre-flight warns (non-blocking) if impl is missing or stale.
- `purlin:status` surfaces code-ahead-of-spec per feature when impl is not updated.

**What changed from the mode system:** Companion files are no longer enforced via a mode-switch gate. The "companion debt" blocker is removed. Instead, sync tracking records when code changes without impl updates, and `/status` surfaces this as advisory information.

### 2.9 Terminal Identity

On skill invocation and feature work, update the terminal identity.

**Format:** `(<branch or worktree label>) <project name or task label>`

**Examples:**
- `(main) purlin` — startup, no active task
- `(dev/0.8.6) building webhook_delivery` — active build work
- `(W1) verifying auth` — worktree with active QA

**Signature:** `update_session_identity [label]` — label defaults to project name if omitted. Context (branch/worktree) is auto-detected. Skills pass task-specific labels.

### 2.10 Commit Guidance

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

#### Scenario: CODE file write allowed and tracked @auto

    Given the agent writes to scripts/webhook.py
    Then the write is allowed
    And sync_state.json contains an entry for the mapped feature

#### Scenario: SPEC file write allowed and tracked @auto

    Given the agent writes to features/integrations/webhook_delivery.md
    Then the write is allowed
    And sync_state.json records spec_changed = true for webhook_delivery

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
