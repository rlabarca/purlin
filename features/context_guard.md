# Feature: Context Guard

> Label: "Process: Context Guard"
> Category: "Process"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A safety net that preserves agent work when Claude Code auto-compacts context. The guard operates in three layers: (1) a PreCompact hook that mechanically saves a session checkpoint before compaction proceeds, (2) instruction-based post-compaction recovery that directs the agent to restore from the checkpoint, and (3) proactive clearing as the recommended path to avoid lossy compaction entirely.

The PreCompact hook is side-effects-only -- it cannot block or prevent compaction. It runs a mechanical save as a best-effort safety net. The optimal workflow is for agents to proactively save and clear before context pressure triggers auto-compaction.

---

## 2. Requirements

### 2.1 Hook Behavior

- A shell script (`tools/hooks/context_guard.sh`) runs as a Claude Code `PreCompact` hook.
- The hook reads the compaction type from the hook input (stdin JSON). Claude Code provides a `type` field indicating whether the compaction is `auto` or `manual`.
- **When `type` is `auto` and guard is enabled:** The hook performs a mechanical checkpoint save (Section 2.3) and exits with code **0**.
- **When `type` is `manual`:** The hook exits with code **0** immediately. No checkpoint is saved (manual compaction is user-initiated and intentional).
- **When guard is disabled** for the current agent: The hook exits with code **0** immediately. No checkpoint is saved.
- The hook MUST always exit with code **0**. PreCompact does not support decision control; exit code 2 shows stderr to the user but compaction proceeds regardless.

### 2.2 Configuration

- Per-agent settings are supported. Each agent entry in `config.json` (or `config.local.json` via the resolver) may contain:
    - `context_guard` (boolean): Enables or disables the guard for that agent. Default: `true`.
- **Enabled resolution order:** `agents.<role>.context_guard` > default `true`.
- There is no threshold configuration. The guard is binary: on or off.

### 2.2.1 Agent Role Detection

- The hook determines the agent's role for configuration resolution using a two-tier approach:
    1. **Environment variable (primary):** Read `AGENT_ROLE` from the environment.
    2. **File fallback:** Read from `.purlin/runtime/agent_role` (written by launcher scripts).
- Valid values: `architect`, `builder`, `qa`.
- When neither source provides a role: the hook treats the guard as enabled and uses `unknown` as the role suffix in the checkpoint filename.

### 2.2.2 Config Reading via Resolver

- The hook uses `resolve_config.py --dump` combined with inline Python to extract per-agent `context_guard` from the resolved config.
- **Enabled chain:** per-agent `context_guard` > default `true`.

### 2.3 Mechanical Checkpoint Save

When triggered (auto-compaction with guard enabled), the hook performs these steps in order:

1. **Write a checkpoint file** to `.purlin/cache/session_checkpoint_<role>_<unique_id>.md` (where `<unique_id>` is the parent process ID to support concurrent agents of the same role) containing:
    - `**Role:** <role>`
    - `**Timestamp:** <ISO 8601>`
    - `**Branch:** <current git branch>`
    - `**Source:** PreCompact hook (auto-compaction safety net)`
    - `**Uncommitted Changes:**` followed by the output of `git status --short`, or `None` if clean.
2. **Attempt a git commit** of any staged changes with the message `[auto] context guard checkpoint before compaction`. If nothing is staged, skip. If the commit fails (e.g., pre-commit hook failure), log to stderr and continue -- do not abort.
3. **Print a brief status line** to stderr: `Context Guard: checkpoint saved for <role>`. This is visible to the user in the terminal but is NOT seen by the agent and is NOT preserved after compaction.

The checkpoint file written by the hook is intentionally minimal. It serves as a signal that auto-compaction occurred and provides git state context. The agent's own `/pl-resume save` produces a richer checkpoint with work-in-progress details -- the hook cannot replicate this because it has no access to the agent's session state.

### 2.4 Hook Registration

- The hook is registered in the project-level `.claude/settings.json` under the `hooks` key, as a `PreCompact` hook with an empty matcher (matches all compaction events; the script handles auto/manual internally).
- The hook command uses `$CLAUDE_PROJECT_DIR` for an absolute path: `"$CLAUDE_PROJECT_DIR"/tools/hooks/context_guard.sh`.

### 2.5 Post-Compaction Recovery

Recovery after auto-compaction is instruction-based, not hook-based. (The SessionStart "compact" matcher has a known bug where output is not reliably injected into context.)

- Each agent role's base instructions (Section 5.4 in ARCHITECT_BASE, BUILDER_BASE, QA_BASE) contain a Context Guard Awareness section that directs the agent to run `/pl-resume save`, `/clear`, then `/pl-resume` when the evacuation signal appears.
- The reference file `instructions/references/context_guard_awareness.md` provides the canonical recovery instructions. This file is loaded on demand by the agent instructions.
- After compaction, the agent's compacted context retains the base instruction to check for and recover from checkpoints. The `/pl-resume` command detects the checkpoint file and restores session state.

### 2.6 Proactive Clearing

Proactive clearing is the recommended workflow. The PreCompact hook is a safety net for when agents do not clear proactively.

- Agents SHOULD monitor their own context usage and run `/pl-resume save` + `/clear` + `/pl-resume` before context pressure triggers auto-compaction.
- The `/pl-context-guard` command allows toggling the guard on or off per agent when proactive clearing is sufficient and the hook overhead is undesirable.

### 2.7 No Counting

- The hook MUST NOT count turns, track session state, or maintain any persistent runtime files beyond the checkpoint file.
- No `turn_count_*` files. No `session_meta_*` files. No counter increment logic.

### 2.8 No Token Counting

- The hook MUST NOT attempt to count tokens or query context window usage. Claude Code's auto-compaction mechanism handles context pressure detection.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Checkpoint saved on auto-compaction with guard enabled

    Given the context_guard is true for the current agent
    And AGENT_ROLE is "builder"
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And the file .purlin/cache/session_checkpoint_builder.md exists
    And the checkpoint contains "**Role:** builder"
    And the checkpoint contains "**Source:** PreCompact hook"

#### Scenario: No checkpoint saved on manual compaction

    Given the context_guard is true for the current agent
    When the PreCompact hook runs with type "manual"
    Then the hook exits with code 0
    And no checkpoint file is written

#### Scenario: No checkpoint saved when guard disabled

    Given agents.architect.context_guard is false in config
    And AGENT_ROLE is "architect"
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And no checkpoint file is written

#### Scenario: Guard enabled by default when no config exists

    Given config.json does not contain a context_guard key for any agent
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And a checkpoint file is written with role "unknown"

#### Scenario: Per-agent guard disabled while others remain enabled

    Given agents.builder.context_guard is false in config
    And agents.architect.context_guard is true in config
    And AGENT_ROLE is "builder"
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And no checkpoint file is written

#### Scenario: Checkpoint contains git branch

    Given the context_guard is true for the current agent
    And the current git branch is "main"
    When the PreCompact hook runs with type "auto"
    Then the checkpoint contains "**Branch:** main"

#### Scenario: Checkpoint contains uncommitted changes summary

    Given the context_guard is true for the current agent
    And there are uncommitted changes in the working tree
    When the PreCompact hook runs with type "auto"
    Then the checkpoint contains "**Uncommitted Changes:**"
    And the checkpoint contains the output of git status --short

#### Scenario: Checkpoint shows no uncommitted changes when tree is clean

    Given the context_guard is true for the current agent
    And the working tree is clean
    When the PreCompact hook runs with type "auto"
    Then the checkpoint contains "**Uncommitted Changes:** None"

#### Scenario: Staged changes are committed before checkpoint

    Given the context_guard is true for the current agent
    And there are staged changes in the index
    When the PreCompact hook runs with type "auto"
    Then a git commit is created with message containing "context guard checkpoint"
    And the checkpoint file is written after the commit

#### Scenario: Hook succeeds even when git commit fails

    Given the context_guard is true for the current agent
    And a git commit would fail (e.g., pre-commit hook error)
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And the checkpoint file is still written
    And stderr contains the commit failure message

#### Scenario: Status line emitted to stderr

    Given the context_guard is true for the current agent
    And AGENT_ROLE is "qa"
    When the PreCompact hook runs with type "auto"
    Then stderr contains "Context Guard: checkpoint saved for qa"

#### Scenario: Hook always exits with code 0

    Given the context_guard is true for the current agent
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And the hook does NOT exit with code 2

### Manual Scenarios (Human Verification Required)

None.
