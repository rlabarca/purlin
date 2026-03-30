# Feature: Purlin Mode System

> Label: "Tool: Purlin Mode System"
> Category: "Framework Core"
> Prerequisite: purlin_resume.md

## 1. Overview

The mode system is the core behavioral mechanism of the Purlin unified agent. Three modes (Engineer, PM, QA) define write-access boundaries and workflow protocols. Modes are activated by skill invocations or the explicit `purlin:mode` command. A mode guard prevents file writes outside the active mode's access list. Cross-mode capabilities allow QA to run tests without switching to Engineer mode.

---

## 2. Requirements

### 2.1 Mode Activation

- Skills MUST declare their mode via `**Purlin mode: <mode>**` header.
- Invoking a mode-activating skill MUST activate that mode.
- `purlin:mode <pm|engineer|qa>` MUST explicitly switch mode.
- Until a mode is activated (open mode), the agent MUST NOT write to any file.

### 2.2 Mode Write Access

- **Engineer mode** write access: all code, tests, scripts, app config, `features/arch_*.md`, `features/*.impl.md`, `features/*.discoveries.md` (recording only), skill files, instruction files.
- **PM mode** write access: `features/*.md` (behavioral specs), `features/design_*.md`, `features/policy_*.md`, design artifacts.
- **QA mode** write access: `features/*.discoveries.md` (lifecycle), QA scenario tags (`@auto`/`@manual`), regression JSON, `tests/qa/`.
- Each mode MUST NOT write to files outside its access list.

### 2.3 Mode Guard

- Before any file write, the agent MUST check if the target file is in the current mode's write-access list.
- If no mode is active: suggest the appropriate mode.
- If wrong mode is active: suggest switching.
- **Narration is not activation.** Stating an intent to switch modes ("Let me do this as PM") does NOT change the active mode. The mode switch MUST be executed (badge updated, terminal identity set, mode announced) before any writes to that mode's files. The agent MUST NOT write to a different mode's files based on a planned or described switch that hasn't been executed.

#### 2.3.1 File Write Guard (PreToolUse: Write|Edit|NotebookEdit)

The file-write mode guard is a `PreToolUse` hook on `Write`, `Edit`, and `NotebookEdit` tools. It classifies the target file path against the active mode's write-access list and blocks unauthorized writes.

#### 2.3.2 Bash Command Guard (PreToolUse: Bash)

A separate `PreToolUse` hook on `Bash` commands enforces default-mode read-only safety:
- **When no mode is active (default):** Blocks Bash commands matching known write/destructive patterns: `rm`, `mv`, `cp`, `mkdir`, `touch`, `chmod`, `git add`, `git commit`, `git push`, `git reset`, `git checkout`, `git stash`, shell redirects (`>`, `>>`), `sed -i`, `tee`, and similar.
- **When a mode IS active:** Allows all Bash commands through. Full per-mode classification of shell commands is inherently fragile, so mode-active sessions rely on the file-write guard for enforcement.
- The blocked-command error directs the agent to activate a mode first.

#### 2.3.3 Hook Blocking Invariant (stderr required for exit code 2)

Claude Code `PreToolUse` hooks block tool calls via exit code 2. However, **exit code 2 alone is not sufficient** — the error message MUST be written to **stderr** (`>&2`), not stdout. Claude Code ignores stdout for exit-code-2 hooks and only feeds stderr to the agent. If stderr is empty, the tool call proceeds despite the non-zero exit code.

**Invariant:** Every `echo ... ; exit 2` pair in a guard hook script MUST use `echo "..." >&2`. Omitting `>&2` silently disables the guard — the hook runs, returns exit 2, but the write goes through anyway because stderr is empty.

This applies to all PreToolUse hook scripts: `mode-guard.sh`, `bash-guard.sh`, and any future guard hooks.

### 2.4 Pre-Switch Check

- Before switching modes, if uncommitted work exists: prompt to commit first.
- The commit MUST use the current mode's prefix convention.

### 2.5 Cross-Mode Test Execution

- QA mode MUST be able to invoke `purlin:unit-test`, `purlin:web-test`, `purlin:fixture`, `purlin:server` for verification without activating Engineer mode.
- QA cross-mode execution MUST NOT allow modifying application code.
- If QA discovers a test failure, it MUST record a `[BUG]` discovery, not fix the code.

### 2.6 Dual Skill Headers

- All skill files MUST have both legacy (`**Purlin command owner:**`) and new (`**Purlin mode:**`) headers.
- Legacy agents match on line 1 (old format). The Purlin agent matches on line 2 (new format).
- New purlin-only skills MUST have `**Purlin command: Purlin agent only**` on line 1 so legacy agents skip them.
- **Validation:** The scan engine's Untracked File Audit catches new skill files without corresponding feature specs. Dual-header compliance is enforced by convention; no automated scan validates header format across all skill files.

### 2.7 Work Discovery Delegation

- `purlin:status` is the SINGLE SOURCE of work discovery. It calls `scan.sh` and interprets the results into mode-specific work items.
- Workflow skills (`purlin:build`, `purlin:verify`, `purlin:spec`) MUST delegate work discovery to `purlin:status`, not call `scan.sh` directly or implement their own detection logic.
- Only `purlin:status`, `purlin:resume` (startup protocol), and audit skills (`purlin:spec-code-audit`, `purlin:verify`) call `scan.sh` directly.
- **Mode-specific routing rules:**
  - `spec_modified_after_completion: true` → Engineer ONLY. QA MUST NOT treat this as a blocker or show it in QA work items. If the Engineer has re-validated and re-tagged, QA proceeds normally.
  - `regression_status: FAIL` → Engineer (fix the code). QA blocks completion but does not fix.
  - `test_status: FAIL` → Engineer.
  - Features in TESTING with QA scenarios → QA.
  - Unacknowledged deviations → PM.
  - Incomplete spec sections → PM.
- Skill files MUST NOT reference `CRITIC_REPORT.md`, `critic.json`, `scan.sh`, or `tests/<name>/critic.json`. These are old Critic system artifacts replaced by `scan.sh` and `purlin:status`.
- Action items use mode-based naming: "PM action items", "Engineer action items", "QA action items".

### 2.8 Companion File Commit Covenant (Engineer)

Per `features/policy_spec_code_sync.md`, every engineer code commit for a feature MUST include a companion file update. This applies to ALL code changes — not just deviations from the spec. The minimum entry is a single `[IMPL]` line.

- This is NOT optional. It is how PM discovers what was built. Skipping it creates silent spec drift.
- For deviations, use the appropriate deviation tag (`[DEVIATION]`, `[DISCOVERY]`, `[AUTONOMOUS]`, `[CLARIFICATION]`, `[INFEASIBLE]`) instead of or in addition to `[IMPL]`.
- Scan.py surfaces unacknowledged deviation entries to PM via `purlin:status`. `[IMPL]` entries are informational and are not surfaced to PM.
- **Five mechanical enforcement gates:**
  1. `purlin:build` Step 4 — Clean Working Tree Gate: ALL modified files must be committed. Untracked files must be either `git add`'d or `.gitignore`'d. No dangling changes allowed before the status tag.
  2. `purlin:build` Step 4 — Companion File Gate: Mechanical check — did the companion file get new entries this session? If code was committed for a feature and the companion file has no new entries: **BLOCK.** No judgment call about whether the change "matches the spec."
  3. Mode switch out of Engineer: Mechanical check — does companion debt exist for any feature? If yes: **BLOCK.** No skip escape. The engineer writes entries (at minimum `[IMPL]` lines) or the switch does not proceed.
  4. Scan — `scan_companion_debt()`: Compares code commit timestamps against companion file modification timestamps. Surfaces debt missed by Gates 1-5 (session crashes, manual git commits).
  5. `FileChanged` hook — Real-time companion debt tracker: A `FileChanged` hook tracks code file changes against companion files in `.purlin/runtime/companion_debt.json`. When a code file mapped to a feature changes, it records debt. When the corresponding `.impl.md` companion file changes, it clears the debt for that feature. The mode switch protocol (Gate 3) reads this file for its mechanical check. Format: `{ "feature_stem": { "files": ["path1", ...], "first_seen": "ISO" } }`.

### 2.9 PID-Scoped Mode State

- Mode state MUST be scoped to the session PID to prevent concurrent terminals from clobbering each other's mode.
- When `PURLIN_SESSION_ID` is set, the mode file MUST be `.purlin/runtime/current_mode_${PURLIN_SESSION_ID}`.
- When `PURLIN_SESSION_ID` is not set (manual invocation), the mode file MUST fall back to `.purlin/runtime/current_mode` (unscoped).
- `get_mode()` MUST read the PID-scoped file first, then fall back to the unscoped file. **Authoritative empty file:** If the PID-scoped file EXISTS but is empty or contains an invalid mode, `get_mode()` MUST return `None` (no mode active) and MUST NOT fall back to the unscoped file. This ensures that `plan-exit-mode-clear` (which empties the file to clear mode) is not bypassed by a stale unscoped file.
- `set_mode()` MUST write to the PID-scoped file when `PURLIN_SESSION_ID` is set, and the unscoped file otherwise. Setting mode to `None` writes an empty string (preserving the file's existence as an authoritative signal).
- The SessionEnd hook MUST clean up PID-scoped mode files (same as it cleans up PID-scoped checkpoints).
- Hook scripts (mode guard, plan-exit-mode-clear) MUST read from the PID-scoped file when `PURLIN_SESSION_ID` is available.
- **Migration:** The unscoped `current_mode` file continues to work for sessions without `PURLIN_SESSION_ID`. No migration step required.

### 2.9.1 Subagent Mode Isolation

When the main Purlin session spawns worker subagents (`pm-worker`, `engineer-worker`, `qa-worker`, `verification-runner`) via the Agent tool with `isolation: "worktree"`, each subagent runs in its own Claude Code worktree under `.claude/worktrees/`. These worktrees are separate from the main agent's `.purlin/worktrees/` and do not participate in the session lock protocol.

#### Problem: MCP Server vs Hook Path Divergence

The Purlin MCP server (`purlin_server.py`) is a single persistent process. It resolves `PURLIN_PROJECT_ROOT` at startup to the **main project root**. When a subagent in a worktree calls `purlin_mode(mode: "engineer")`, `set_mode()` writes to the main project's `.purlin/runtime/`. Meanwhile, the `mode-guard.sh` PreToolUse hook runs as a subprocess in the **subagent's CWD** (the worktree) and reads from `${PURLIN_PROJECT_ROOT:-$(pwd)}/.purlin/runtime/`. These are different filesystem paths — the MCP tool writes to one location and the hook reads from another.

Without correction, the mode guard in a worktree subagent will never find the mode set by the MCP tool, and will block all writes with "Default mode is read-only."

#### Solution: Agent-ID-Scoped Mode Files in the Main Project Root

Both the MCP server and the mode guard MUST use the same base path (the main project root) with agent-ID-scoped mode filenames to isolate concurrent subagents. This avoids depending on CWD consistency across processes.

**Mode isolation requirements:**

- The `purlin_mode` MCP tool MUST accept an optional `agent_id` parameter. When provided, `set_mode()` MUST write to `.purlin/runtime/current_mode_${agent_id}` in the main project root. When omitted, existing behavior is preserved (uses `PURLIN_SESSION_ID` or unscoped fallback).
- The `mode-guard.sh` hook MUST extract `agent_id` from the PreToolUse hook input JSON (field is present when running inside a subagent per Claude Code hook spec). When `agent_id` is present, the hook MUST read mode from `.purlin/runtime/current_mode_${agent_id}` **in the main project root** (not the worktree CWD). The main project root is derived from the hook input's `transcript_path` or by walking up from CWD to find `.purlin/`.
- `bash-guard.sh` MUST apply the same agent_id extraction logic.
- Concurrent subagents MUST NOT share a mode file. Each subagent's `agent_id` is unique (assigned by Claude Code), guaranteeing file isolation.
- Each subagent MUST activate its own mode via `purlin_mode(mode: "<mode>", agent_id: "<id>")` before any writes. The agent definition instructions ("PM mode only", "Engineer mode only") are necessary but not sufficient — the mode guard enforces mechanically, not by instruction.

**Subagent agent definition requirements:**

- All worker agent definitions (`pm-worker.md`, `engineer-worker.md`, `qa-worker.md`) MUST include an explicit mode activation step as step 1 of their workflow: "Activate your mode by calling `purlin_mode(mode: \"<mode>\")` before writing any files."
- Whether `agent_id` must be passed as a parameter depends on the open question below. If Claude Code does NOT expose `agent_id` as an environment variable to subagent MCP processes, the instruction MUST include the `agent_id` parameter. If it does, the MCP server can derive it automatically.
- `engineer-worker.md` frontmatter `skills` field MUST reference `purlin:build` (not legacy `pl-build`).

**Hook input fields used (per Claude Code hook spec):**

- `session_id` — always present, used as fallback identifier.
- `agent_id` — present when running inside a subagent. Used as the primary mode file key.
- `agent_type` — present when running inside a subagent or `--agent` mode.
- `cwd` — the working directory of the calling agent.

**How subagents discover their agent_id:**

Subagents do not inherently know their own `agent_id`. The resolution depends on Claude Code's environment propagation:
1. **Best case — MCP server derives it automatically:** Claude Code exposes `agent_id` (or equivalent) as an environment variable to subagent processes. The MCP server reads it and uses it for mode file scoping. No parameter needed from the subagent.
2. **Fallback — explicit parameter:** If no environment variable is available, the `purlin_mode` tool's `agent_id` parameter is required. The subagent agent definitions must instruct workers to pass a unique identifier (e.g., their session_id, which IS available to the agent in its own context).
3. **Degraded mode (single-worker only):** If neither approach is feasible, the subagent writes to the unscoped file. This works for single-worker dispatch but creates race conditions in parallel. The mode guard still provides partial protection by reading the agent-scoped file first (if `agent_id` is in hook input) and falling back to unscoped.

**Recommended implementation:**
1. `purlin_mode` MCP tool writes to the agent-scoped file ONLY when `agent_id` is provided (not to the unscoped file — dual-write reintroduces the race condition). When `agent_id` is absent, writes to the unscoped file (existing behavior for main session).
2. `mode-guard.sh` reads the agent-scoped file first (if `agent_id` present in hook input). If no agent-scoped file exists, falls back to unscoped. This ensures single-worker scenarios and main session work without changes, while parallel workers get correct isolation.
3. The global `_current_mode` cache in `config_engine.py` MUST be removed or scoped by agent_id. As a single MCP server process handles calls from all agents, the in-memory cache will be corrupted by concurrent subagents overwriting each other's state. Either use a dict keyed by agent_id, or always read from disk (mode files are small, I/O cost is negligible).

**Implementation prerequisites (not yet done):**
- `purlin_mode` tool input schema must add optional `agent_id` parameter.
- `config_engine.set_mode()` and `get_mode()` must accept an `agent_id` argument for scoped file access.
- `config_engine._current_mode` global must become a dict or be removed.
- `mode-guard.sh` and `bash-guard.sh` must parse `agent_id` from the PreToolUse hook input JSON.
- `bash-guard.sh` must be registered in `hooks/hooks.json` under PreToolUse with matcher `Bash`.
- `plan-exit-mode-clear.sh` must resolve project root independently of CWD (walk up to find `.purlin/` or use `CLAUDE_PLUGIN_ROOT` parent path).

**Open question (requires Claude Code verification):**

Does Claude Code provide `agent_id` or a unique session identifier as an environment variable to subagent processes (not just in hook input)? If yes, the MCP server can read it directly without requiring a parameter. If no, the `agent_id` parameter on `purlin_mode` is required, and subagent agent definitions must instruct workers to pass it. **This must be verified before implementation by testing with `claude --debug`.**

**Cleanup:**

- Agent-scoped mode files (`.purlin/runtime/current_mode_${agent_id}`) in the main project root MUST be cleaned up by the SessionEnd hook or SubagentStop hook.
- The main session's SessionEnd hook SHOULD clean up stale `current_mode_*` files in `.purlin/runtime/` (any file matching the pattern that is older than the current session).

### 2.10 Commit Attribution

- Engineer commits: `feat()`, `fix()`, `test()` prefixes.
- PM commits: `spec()`, `design()` prefixes.
- QA commits: `qa()`, `status()` prefixes.
- All commits MUST include `Purlin-Mode: <mode>` trailer.

### 2.11 iTerm Terminal Identity

- On mode activation, the agent MUST set the iTerm badge and terminal title following the format defined in `features/purlin_worktree_identity.md` (sections 2.3–2.4). The badge is the mode name (`Engineer`, `PM`, `QA`, or `Purlin` in open mode), with the worktree label appended when `.purlin_worktree_label` exists (e.g., `Engineer (W1)`).
- `<project>` is derived from the working directory name (basename of the project root).
- The agent MUST use iTerm2 proprietary escape sequences: badge via `\033]1337;SetBadgeFormat=<base64>\a`, remote control name via `\033]1337;SetMark\a` or the appropriate `\033]0;<name>\a` title sequence.

---

## 3. Scenarios

### Unit Tests

#### Scenario: Skill activates correct mode

    Given the agent is in open mode (no mode active)
    When the user invokes purlin:build
    Then Engineer mode is activated
    And the agent can write to code files

#### Scenario: Mode guard blocks write in wrong mode @auto

    Given the agent is in QA mode
    When the agent attempts to write to src/app.py
    Then the write is blocked
    And the agent suggests switching to Engineer mode

#### Scenario: Cross-mode QA runs tests without switching

    Given the agent is in QA mode
    When the user invokes purlin:unit-test
    Then tests are executed
    And QA mode remains active (not switched to Engineer)
    And no application code files are modified

#### Scenario: Pre-switch companion file gate blocks without skip

    Given the agent is in Engineer mode
    And code was committed for feature "auth_flow" without updating the companion file
    When the user invokes purlin:spec (PM mode skill)
    Then the mode switch is BLOCKED
    And the agent lists "auth_flow" as having companion debt
    And no "skip" option is offered
    And the agent does NOT switch to PM mode until companion entries are written

#### Scenario: Build status tag blocked by untracked files

    Given the agent completed code changes for feature "scan_engine"
    And a new file tools/cdd/scan_helper.py exists but is untracked
    When purlin:build reaches Step 4 (status tag commit)
    Then the status tag commit is BLOCKED
    And the agent either adds the file to git or adds it to .gitignore

#### Scenario: Build status tag blocked by missing companion entry (mechanical)

    Given the agent completed code changes for feature "auth_flow"
    And no companion file entry was written (regardless of whether changes deviate from spec)
    When purlin:build reaches Step 4 (status tag commit)
    Then the status tag commit is BLOCKED
    And the agent requires at least [IMPL] entries before proceeding

#### Scenario: Narrated mode switch does not grant write access

    Given the agent is in Engineer mode
    And the user asks to update a feature spec
    When the agent says "Let me do this as PM" but does not execute purlin:mode pm
    Then the agent MUST NOT write to features/*.md
    And the mode guard blocks the write
    And the iTerm badge still shows "Engineer"

#### Scenario: Pre-switch commit prompt

    Given the agent is in Engineer mode with uncommitted changes
    When the user invokes purlin:spec (PM mode skill)
    Then the agent prompts to commit the uncommitted work
    And waits for user confirmation before switching

#### Scenario: Dual skill header for legacy compatibility

    Given pl-build.md skill file
    When a legacy Engineer agent reads the file
    Then line 1 contains "Purlin command owner: Engineer"
    And the legacy agent recognizes it as a Engineer command

#### Scenario: Purlin-only skill blocked by legacy agents

    Given pl-mode.md skill file
    When a legacy Engineer agent reads the file
    Then line 1 contains "Purlin command: Purlin agent only"
    And the legacy agent skips this command

#### Scenario: Consolidated toolbox skill subcommands

    Given the agent is in any mode
    When the user invokes purlin:toolbox list
    Then the toolbox list protocol executes
    And old purlin:release file does not exist

#### Scenario: pl-anchor dual-mode activation

    Given the agent is in open mode
    When the user invokes purlin:anchor arch_data_layer
    Then Engineer mode is activated (arch_* target)

#### Scenario: pl-anchor activates PM for design anchors

    Given the agent is in open mode
    When the user invokes purlin:anchor design_visual_standards
    Then PM mode is activated (design_* target)

#### Scenario: Commit attribution with mode trailer

    Given the agent is in Engineer mode
    When the agent commits code changes
    Then the commit message starts with "feat(" or "fix(" or "test("
    And the commit body contains "Purlin-Mode: Engineer"

#### Scenario: Terminal identity set on mode activation

    Given the agent is in open mode on branch "main"
    When the user activates Engineer mode
    Then the terminal identity is set to "Eng(main) | <project>"

#### Scenario: Terminal identity in open mode

    Given the agent has just started with no mode active on branch "main"
    Then the terminal identity is "Purlin(main) | <project>"

#### Scenario: Terminal identity updates on mode switch

    Given the agent is in PM mode on branch "main"
    When the user switches to QA mode
    Then the terminal identity changes to "QA(main) | <project>"

#### Scenario: Regression evaluate documents failure in companion file

    Given feature "skill_behavior_regression" has regression_status FAIL
    When purlin:regression evaluate is invoked
    Then features/skill_behavior_regression.impl.md contains a [DISCOVERY] entry
    And the entry includes the scenario name that failed
    And the entry includes the expected assertion pattern
    And the entry includes the actual output

#### Scenario: Concurrent terminals have independent mode state @auto

    Given terminal A has PURLIN_SESSION_ID=1000 in Engineer mode
    And terminal B has PURLIN_SESSION_ID=2000 in PM mode
    When terminal A switches to QA mode
    Then terminal B's mode is still PM
    And .purlin/runtime/current_mode_1000 contains "qa"
    And .purlin/runtime/current_mode_2000 contains "pm"

#### Scenario: PID-scoped mode file cleaned up on session end

    Given terminal with PURLIN_SESSION_ID=1000 in Engineer mode
    And .purlin/runtime/current_mode_1000 exists
    When the session ends (SessionEnd hook fires)
    Then .purlin/runtime/current_mode_1000 is deleted

#### Scenario: Bash guard blocks destructive commands in default mode @auto

    Given no mode is active (default read-only)
    When the agent runs a Bash command containing "rm -rf build/"
    Then the command is blocked with exit code 2
    And the error message suggests activating a mode first

#### Scenario: Bash guard allows all commands when mode is active @auto

    Given Engineer mode is active
    When the agent runs a Bash command containing "rm -rf build/"
    Then the command is allowed through (exit code 0)

#### Scenario: Empty PID-scoped mode file means mode cleared @auto

    Given PURLIN_SESSION_ID=1000
    And .purlin/runtime/current_mode_1000 exists but is empty
    And .purlin/runtime/current_mode contains "engineer" (stale unscoped)
    When get_mode() is called
    Then it returns None (no mode active)
    And it does NOT fall back to the unscoped file

#### Scenario: FileChanged hook records companion debt for code changes

    Given Engineer mode is active
    When a code file tests/auth_flow/test_login.py is modified
    Then .purlin/runtime/companion_debt.json contains an entry for "auth_flow"
    And the entry lists the changed file path

#### Scenario: FileChanged hook clears debt when companion file updated

    Given .purlin/runtime/companion_debt.json has debt for "auth_flow"
    When features/framework_core/auth_flow.impl.md is modified
    Then the "auth_flow" entry is removed from companion_debt.json

#### Scenario: Concurrent subagents have isolated mode state

    Given the main session spawns pm-worker (agent_id=abc) and engineer-worker (agent_id=def) in parallel
    When pm-worker activates PM mode and engineer-worker activates Engineer mode
    Then .purlin/runtime/current_mode_abc contains "pm" (in main project root)
    And .purlin/runtime/current_mode_def contains "engineer" (in main project root)
    And mode-guard.sh for pm-worker reads agent_id=abc from hook input and checks current_mode_abc
    And mode-guard.sh for engineer-worker reads agent_id=def from hook input and checks current_mode_def

#### Scenario: Subagent mode guard enforces correct boundaries

    Given pm-worker (agent_id=abc) has activated PM mode
    And .purlin/runtime/current_mode_abc contains "pm"
    When pm-worker attempts to write to src/app.py (CODE-owned)
    Then the mode guard extracts agent_id=abc from PreToolUse hook input
    And reads mode "pm" from .purlin/runtime/current_mode_abc
    And the write is blocked with "CODE-owned, not writable in PM mode"

#### Scenario: MCP server and mode guard agree on mode file path

    Given engineer-worker calls purlin_mode(mode: "engineer", agent_id: "def")
    When mode-guard.sh fires for a Write call from the same subagent
    Then the hook extracts agent_id=def from PreToolUse input
    And reads .purlin/runtime/current_mode_def (same file the MCP tool wrote)
    And the mode is "engineer" (not stale, not from another subagent)

#### Scenario: Subagent without agent_id falls back to unscoped mode file

    Given a single subagent is spawned without agent_id in hook input
    When the subagent calls purlin_mode(mode: "engineer") and attempts a Write
    Then mode-guard.sh falls back to reading .purlin/runtime/current_mode (unscoped)
    And the write is allowed (single-worker, no race condition)

### QA Scenarios

#### Scenario: Open mode prevents writes @auto

    Given the agent has just started with no mode active
    When the user asks to "edit the config file"
    Then the agent suggests activating Engineer mode first
    And does not write to any file

#### Scenario: No skill references old Critic system @auto

    Given the project after scan.sh migration
    When searching all skills/*/SKILL.md files
    Then no file contains "status.sh" (except tombstones)
    And no file contains "CRITIC_REPORT.md"
    And no file contains "critic.json"

#### Scenario: Old consolidated skills are deleted @auto

    Given the project after skill consolidation
    When checking .claude/commands/
    Then pl-release.md does not exist
    And pl-release-check.md does not exist
    And pl-release-run.md does not exist
    And pl-release-step.md does not exist
    And pl-regression-run.md does not exist
    And pl-regression-author.md does not exist
    And pl-regression-evaluate.md does not exist
    And pl-remote-push.md does not exist
    And pl-remote-pull.md does not exist
    And pl-remote-add.md does not exist
    And pl-edit-base.md does not exist

## Regression Guidance

**Automated regression suite:** `tests/qa/scenarios/purlin_mode_system.json` (5 scenarios, 45 assertions)
- `write-guard-enforcement` — Full mode-file compatibility matrix (Engineer/PM/QA/default x CODE/SPEC/QA/INVARIANT)
- `bash-guard-enforcement` — Destructive command blocking in default mode, all-allow in active modes
- `mode-state-persistence` — PID-scoped persistence, concurrent isolation, authoritative empty file
- `file-classification-rules` — classify_file() correctness for all file types
- `implicit-mode-detection-rules` — Agent definition regression guard (proactive mode-switching language)

**Additional manual verification:**
- Verify all 33 skill files have both legacy and new headers
- Verify no skill file has ONLY the new header (breaks legacy agents)
- Verify cross-mode test execution does not leave QA in Engineer mode
- Verify purlin:anchor mode activation depends on target prefix, not the skill itself
- Verify iTerm badge and remote control name update on every mode switch
- Verify open mode sets badge to "Purlin", not blank
- Verify the agent cannot write to another mode's files by narrating a switch without executing it
- Verify concurrent terminals with different PURLIN_SESSION_ID values have independent mode state
- Verify SessionEnd cleans up PID-scoped mode files
- Verify sessions without PURLIN_SESSION_ID fall back to unscoped current_mode file
- Verify parallel subagents (pm-worker + engineer-worker) write to separate agent-ID-scoped mode files in the main project root
- Verify mode-guard.sh extracts agent_id from PreToolUse hook input and reads the correct mode file
- Verify MCP server and mode guard agree on mode file path (both use main project root + agent_id)
- Verify single-worker fallback: subagent without agent_id in hook input uses unscoped mode file
- Verify engineer-worker.md references `purlin:build` (not legacy `pl-build`) in skills frontmatter
