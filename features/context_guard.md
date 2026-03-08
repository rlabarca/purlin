# Feature: Context Guard

> Label: "Process: Context Guard"
> Category: "Process"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A Claude Code `PreCompact` hook that intercepts auto-compaction to give agents time to save their work before context is lost. When Claude Code is about to auto-compact, the hook blocks it and sends an evacuation message. The agent then saves a checkpoint via `/pl-resume save`, the user clears context with `/clear`, and the agent resumes via `/pl-resume`.

This replaces the previous PostToolUse turn-counting approach. There are no counters, no thresholds, no per-turn output. The guard is invisible until it fires.

---

## 2. Requirements

### 2.1 Hook Behavior

- A shell script (`tools/hooks/context_guard.sh`) runs as a Claude Code `PreCompact` hook.
- The hook reads the compaction type from the hook input (stdin JSON). Claude Code provides a `type` field indicating whether the compaction is `auto` (triggered by context pressure) or `manual` (triggered by user action).
- **When `type` is `auto` and guard is enabled:** The hook exits with code **2** (block compaction) and emits an evacuation message to stderr.
- **When `type` is `manual`:** The hook exits with code **0** (allow compaction) regardless of guard state.
- **When guard is disabled** for the current agent: The hook exits with code **0** (allow compaction) regardless of type.

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
- When neither source provides a role: the hook treats the guard as enabled (default behavior).

### 2.2.2 Config Reading via Resolver

- The hook uses `resolve_config.py --dump` combined with inline Python to extract per-agent `context_guard` from the resolved config.
- **Enabled chain:** per-agent `context_guard` > default `true`.

### 2.3 Evacuation Message

- When the hook blocks auto-compaction, it emits the following message to stderr:

    ```
    CONTEXT GUARD: Auto-compaction blocked. Run /pl-resume save, then /clear, then /pl-resume to continue.
    ```

- No JSON output to stdout is needed. PreCompact hooks communicate via exit code and stderr.
- The message is plain text (no ANSI color codes).

### 2.4 Hook Registration

- The hook is registered in the project-level `.claude/settings.json` under the `hooks` key, as a `PreCompact` hook with the `auto` matcher.
- The hook runs the shell script at `tools/hooks/context_guard.sh`.

### 2.5 No Counting

- The hook MUST NOT count turns, track session state, or maintain any runtime files.
- No `turn_count_*` files. No `session_meta_*` files. No counter increment logic.
- No per-turn output. The hook produces output only when blocking auto-compaction.

### 2.6 No Token Counting

- The hook MUST NOT attempt to count tokens or query context window usage. Claude Code's auto-compaction mechanism handles context pressure detection.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Auto-compaction blocked when guard enabled

    Given the context_guard is true for the current agent
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 2
    And stderr contains "CONTEXT GUARD: Auto-compaction blocked"

#### Scenario: Manual compaction allowed regardless of guard state

    Given the context_guard is true for the current agent
    When the PreCompact hook runs with type "manual"
    Then the hook exits with code 0
    And no output is produced on stderr

#### Scenario: Auto-compaction allowed when guard disabled

    Given agents.architect.context_guard is false in config
    And AGENT_ROLE is "architect"
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0
    And no output is produced on stderr

#### Scenario: Guard enabled by default when no config exists

    Given config.json does not contain a context_guard key for any agent
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 2
    And stderr contains the evacuation message

#### Scenario: Per-agent guard disabled while others remain enabled

    Given agents.builder.context_guard is false in config
    And agents.architect.context_guard is true in config
    And AGENT_ROLE is "builder"
    When the PreCompact hook runs with type "auto"
    Then the hook exits with code 0

#### Scenario: Evacuation message content is correct

    Given the context_guard is true for the current agent
    When the PreCompact hook runs with type "auto"
    Then stderr contains exactly "CONTEXT GUARD: Auto-compaction blocked. Run /pl-resume save, then /clear, then /pl-resume to continue."

### Manual Scenarios (Human Verification Required)

None.
