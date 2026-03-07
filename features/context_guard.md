# Feature: Context Guard

> Label: "Process: Context Guard"
> Category: "Process"
> Prerequisite: features/policy_critic.md

[TODO]

## 1. Overview

A Claude Code `PostToolUse` hook that monitors session turn count and triggers an automatic checkpoint warning when a configurable threshold is crossed. This provides a system-level safety net against context window exhaustion — unlike instruction-level mandates, the hook fires regardless of agent attention degradation as context fills.

---

## 2. Requirements

### 2.1 Turn Counter

- A shell script (`tools/hooks/context_guard.sh`) runs after every tool call via Claude Code's `PostToolUse` hook system.
- The script increments an integer counter stored in `.purlin/runtime/turn_count_<AGENT_ID>`, where `AGENT_ID` is the Claude Code process PID (`$PPID` from the hook script's perspective).
- `AGENT_ID` may be overridden via the `CONTEXT_GUARD_AGENT_ID` environment variable (for testing).
- Each Claude Code process gets its own counter file. No counter files are shared between processes.
- The counter file contains only the integer count (no other data).

### 2.2 Threshold Configuration

- Per-agent settings are supported. Each agent entry in `config.json` may contain:
    - `context_guard` (boolean): Enables or disables the guard for that agent. Default: `true`.
    - `context_guard_threshold` (integer): The turn threshold for that agent. Default: inherited from global.
- **Threshold resolution order:** `agents.<role>.context_guard_threshold` > global `context_guard_threshold` > hardcoded `45`.
- **Enabled resolution order:** `agents.<role>.context_guard` > default `true`.
- The global `context_guard_threshold` top-level key is retained for backward compatibility and serves as the fallback when no per-agent threshold is configured.
- The threshold represents approximately 75-85% of usable context (~45 turns at ~3-5K tokens per turn ≈ 135-225K tokens consumed, out of ~200K usable context after system prompt).

### 2.2.1 Agent Role Detection

- The hook determines the agent's role for threshold resolution using a two-tier approach:
    1. **Session-local (primary):** Read role from `session_meta_<AGENT_ID>` (persisted on first invocation of each agent session). This eliminates races where concurrent agents of different roles overwrite a shared file.
    2. **Initial source (bootstrap):** On first invocation (no `session_meta_<AGENT_ID>` exists), read `AGENT_ROLE` from the environment variable or `.purlin/runtime/agent_role` file (written by launcher scripts). Persist the resolved role into `session_meta_<AGENT_ID>` for subsequent invocations.
- Valid values: `architect`, `builder`, `qa`.
- When neither `AGENT_ROLE` nor `.purlin/runtime/agent_role` provides a role: the hook falls back to global config behavior — global `context_guard_threshold` with the guard always enabled.

### 2.2.2 Config Reading via Resolver

- The hook uses `resolve_config.py --dump` combined with inline Python to extract nested per-agent values from the resolved config.
- This avoids modifying the `--key` CLI mode of `resolve_config.py`, which only supports top-level keys.
- **Fallback chain:** per-agent `context_guard_threshold` > global `context_guard_threshold` > hardcoded 45.
- **Enabled chain:** per-agent `context_guard` > default `true`.

### 2.3 Session Detection

- Each Claude Code process is identified by its OS PID (`$PPID` from the hook script's perspective), referred to as `AGENT_ID`.
- **New process** = new PPID = no existing `turn_count_<AGENT_ID>` or `session_meta_<AGENT_ID>` files → create fresh files, start counter at 1.
- **Same process** = same PPID = existing files → read `session_id` from `session_meta_<AGENT_ID>` and compare with the `session_id` in the hook's stdin input:
    - **Match:** This is the parent Claude Code process → increment counter.
    - **Mismatch:** This is a subagent (Task tool) running under the same Claude Code process → read counter without incrementing.
- No file-age heuristics or timestamp-based detection is used.

### 2.4 Context Status Output

- The hook outputs a JSON object to stdout on **every tool call** (not just when the threshold is exceeded). This provides continuous visibility into the context budget usage.
- Output uses the `hookSpecificOutput.additionalContext` field — the only format Claude Code surfaces to the agent in PostToolUse hooks. Plain `echo`/stdout text is visible in the user's terminal but NOT to the agent.
- **Format (normal):** `CONTEXT GUARD: ${COUNT} / ${THRESHOLD} used` where COUNT = turns consumed (incremented before output).
    - Example at turn 5 of 45: `CONTEXT GUARD: 5 / 45 used`
    - Interpretation: higher COUNT means closer to the limit.
- **Format (exceeded):** When COUNT >= THRESHOLD, append evacuation instructions.
    - Example at turn 48 of 45: `CONTEXT GUARD: 48 / 45 used -- Run /pl-resume save, then /clear, then /pl-resume to continue.`
- **User-visible status line:** In addition to the JSON `additionalContext` output (agent-only), the hook MUST also emit a plain-text status line to stderr showing the same `CONTEXT GUARD: ${COUNT} / ${THRESHOLD} used` format (and the exceeded variant when applicable). This ensures the human user sees the context budget in the terminal alongside each tool call, not only in the CDD Dashboard. Stderr is used because plain stdout text would interfere with the JSON output that Claude Code parses for the agent.
- **No silent exits:** The hook MUST produce output on every tool call when the guard is enabled (both the JSON `additionalContext` for the agent AND the stderr status line for the user). Early exits for subagent detection or other conditions MUST still output the context guard status. The only exception is when `context_guard` is explicitly set to `false` for the current agent.
- **When guard is disabled** (`context_guard: false` for the current agent): No JSON output is produced. The counter still increments in the background so that re-enabling the guard mid-session shows an accurate count.
- **Context cost:** ~8-12 tokens per message. At 45 turns = ~360-540 tokens (<0.3% of usable context).

### 2.4.1 Color-Coded Stderr Output

The user-visible stderr status line uses ANSI true-color (24-bit) escape codes to signal proximity to the threshold. Colors are drawn from the project's design tokens (`design_visual_standards.md`). The JSON `additionalContext` output remains uncolored (plain text) — ANSI codes in JSON would not render correctly.

**Color zones (based on percentage of threshold consumed):**

| Zone | Condition | Color Token | Hex | ANSI Code |
|------|-----------|-------------|-----|-----------|
| Normal | COUNT < 80% of THRESHOLD | No color | — | (default terminal color) |
| Warning | COUNT >= 80% of THRESHOLD | `--purlin-status-warning` | `#FB923C` | `\033[38;2;251;146;60m` |
| Critical | COUNT >= 92% of THRESHOLD | `--purlin-status-error` | `#F87171` | `\033[38;2;248;113;113m` |

- **Boundary math:** Warning triggers at `COUNT >= THRESHOLD * 0.80` (within 20% of the limit). Critical triggers at `COUNT >= THRESHOLD * 0.92` (within 8% of the limit). Use integer arithmetic: `WARN_AT = THRESHOLD * 80 / 100`, `CRIT_AT = THRESHOLD * 92 / 100`.
- **Exceeded state** (COUNT >= THRESHOLD): Uses the Critical color. The evacuation instructions are also colored.
- **Reset code:** Every colored stderr line MUST end with `\033[0m` to reset the terminal color.
- **No color when piped:** If stderr is not a terminal (`! -t 2`), omit ANSI codes entirely (plain text fallback). This prevents garbled output when stderr is redirected to a file or pipe.

### 2.5 Hook Registration

- The hook is registered in the project-level `.claude/settings.json` under the `hooks` key, as a `PostToolUse` hook.
- The hook runs the shell script at `tools/hooks/context_guard.sh`.

### 2.6 No Token Counting

- The hook MUST NOT attempt to count tokens or query context window usage. Claude Code hooks do not expose token counters. Turn count is the proxy metric.

### 2.7 Multi-Instance Isolation

- Each Claude Code process is identified by its OS PID (`$PPID` from the hook script's perspective), overridable via `CONTEXT_GUARD_AGENT_ID` for testing.
- File naming: `turn_count_<PID>`, `session_meta_<PID>`.
- Multiple agents of the same role running concurrently in different terminals get different PIDs and track independently.
- No agent can read, write, or reset another agent's counter files (except during cleanup of dead processes per Section 2.8).

### 2.8 Stale File Cleanup

- On every hook invocation (within the lock), scan `turn_count_*` and `session_meta_*` files in `.purlin/runtime/`.
- For each file with a numeric PID suffix that is NOT the current `AGENT_ID`:
    - Check process liveness via `kill -0 $PID`.
    - If the process is dead → delete the file.
    - If the process is alive → verify process identity by comparing the stored process start time (third line of `session_meta_<PID>`) with the actual process start time (`ps -p $PID -o lstart=`). If they differ → PID was recycled → delete the file.
- `session_meta` format (three lines):
    ```
    <session_id>
    <role>
    <process_start_time>
    ```

### 2.9 Counter Reset Protocol

- Counter reset is **PPID-scoped**: only the current Claude Code process's files are affected.
- The `/pl-resume` protocol resets the counter by writing `0` to `turn_count_$PPID` (where `$PPID` is available in bash commands run by the same Claude Code process).
- No wildcard resets. No other agent's files are touched.
- After reset, the next hook invocation for this session reads 0 and increments to 1.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Counter increments on each invocation

    Given no turn_count file exists for the current AGENT_ID
    When the context guard script runs 3 times with the same PPID
    Then the turn count file turn_count_<AGENT_ID> contains "3"

#### Scenario: Status output on every turn when guard enabled

    Given the context_guard_threshold is set to 10 in config.json
    And the turn count for the current AGENT_ID is currently 2
    When the context guard script runs
    Then stdout contains JSON with additionalContext "CONTEXT GUARD: 3 / 10 used"

#### Scenario: Exceeded threshold appends evacuation instructions

    Given the context_guard_threshold is set to 5 in config.json
    And the turn count for the current AGENT_ID is currently 5
    When the context guard script runs
    Then stdout contains "CONTEXT GUARD: 6 / 5 used -- Run /pl-resume save, then /clear, then /pl-resume to continue."

#### Scenario: New process starts fresh counter

    Given a previous agent session created turn_count_<OLD_PID> with value "25"
    When the context guard script runs with a different PPID
    Then a new turn_count_<NEW_PID> file is created with value "1"
    And the old turn_count_<OLD_PID> file is unaffected

#### Scenario: Default threshold when config key absent

    Given config.json does not contain context_guard_threshold
    And AGENT_ROLE is not set
    When the context guard script reads the threshold
    Then the threshold value is 45

#### Scenario: Per-agent threshold overrides global

    Given config.json has context_guard_threshold set to 45
    And agents.builder.context_guard_threshold is set to 30
    And AGENT_ROLE is "builder"
    When the context guard script reads the threshold
    Then the threshold value is 30

#### Scenario: Per-agent guard disabled suppresses output

    Given agents.architect.context_guard is false in config.json
    And AGENT_ROLE is "architect"
    And the turn count for the current AGENT_ID is currently 10
    When the context guard script runs
    Then no JSON output is produced on stdout
    And the turn count file contains "11"

#### Scenario: Missing AGENT_ROLE falls back to global

    Given AGENT_ROLE is not set
    And config.json has context_guard_threshold set to 50
    And agents.builder.context_guard_threshold is set to 30
    When the context guard script reads the threshold
    Then the threshold value is 50

#### Scenario: Exceeded output repeats on subsequent turns

    Given the context_guard_threshold is set to 2
    And the turn count for the current AGENT_ID is currently 3
    When the context guard script runs
    Then stdout contains "CONTEXT GUARD: 4 / 2 used -- Run /pl-resume save, then /clear, then /pl-resume to continue."

#### Scenario: Per-agent threshold is used when AGENT_ROLE is set

    Given config.json has context_guard_threshold set to 45
    And agents.builder.context_guard_threshold is set to 60
    And AGENT_ROLE is "builder"
    And the turn count for the current AGENT_ID is currently 0
    When the context guard script runs
    Then stdout contains "CONTEXT GUARD: 1 / 60 used"

#### Scenario: Subagent detection via session_meta mismatch

    Given session_meta_<AGENT_ID> exists with a stored session_id
    And the hook receives a different session_id in its stdin input
    And the guard is enabled
    When the context guard script runs
    Then stdout contains JSON with additionalContext matching "CONTEXT GUARD:"
    And the turn count file is NOT incremented

#### Scenario: Counter resets via PPID-scoped reset command

    Given turn_count_<AGENT_ID> exists with value "42"
    When "0" is written to turn_count_<AGENT_ID>
    And the context guard script runs
    Then the turn count file contains "1"
    And stdout contains "CONTEXT GUARD: 1 /"

#### Scenario: User-visible status line emitted to stderr

    Given the guard is enabled for the current agent
    And the turn count for the current AGENT_ID is currently 4
    And the context_guard_threshold is set to 45
    When the context guard script runs
    Then stderr contains "CONTEXT GUARD: 5 / 45 used"
    And stdout contains JSON with additionalContext "CONTEXT GUARD: 5 / 45 used"

#### Scenario: Guard output on every tool call with no silent exits

    Given the guard is enabled for the current agent
    When the context guard script runs under any condition (new session, existing session, subagent)
    Then stdout contains JSON with additionalContext matching "CONTEXT GUARD:"
    And stderr contains a line matching "CONTEXT GUARD:"

#### Scenario: Multiple agents of same role track independently

    Given two Claude Code processes with different PPIDs both have AGENT_ROLE set to "builder"
    When each process runs the context guard script 5 times
    Then turn_count_<PID_A> contains "5"
    And turn_count_<PID_B> contains "5"
    And neither counter affected the other

#### Scenario: Reset only affects current session

    Given turn_count_<PID_A> exists with value "30"
    And turn_count_<PID_B> exists with value "20"
    When "0" is written to turn_count_<PID_A>
    Then turn_count_<PID_A> contains "0"
    And turn_count_<PID_B> still contains "20"

#### Scenario: Stale file cleanup removes dead process files

    Given turn_count_<DEAD_PID> and session_meta_<DEAD_PID> exist
    And the process with DEAD_PID is no longer running
    When the context guard script runs for a different AGENT_ID
    Then turn_count_<DEAD_PID> is deleted
    And session_meta_<DEAD_PID> is deleted

#### Scenario: PID recycling does not prevent cleanup

    Given session_meta_<PID> exists with a stored process start time
    And a different process now occupies that PID (different start time)
    When the context guard script runs stale file cleanup
    Then session_meta_<PID> is deleted
    And turn_count_<PID> is deleted

#### Scenario: Stderr output is uncolored in normal zone

    Given the context_guard_threshold is set to 50
    And the turn count for the current AGENT_ID is currently 9
    And stderr is a terminal
    When the context guard script runs
    Then stderr contains "CONTEXT GUARD: 10 / 50 used" without ANSI escape codes

#### Scenario: Stderr output is warning-colored when within 20% of limit

    Given the context_guard_threshold is set to 50
    And the turn count for the current AGENT_ID is currently 39
    And stderr is a terminal
    When the context guard script runs
    Then stderr contains the warning color code "\033[38;2;251;146;60m"
    And stderr contains "CONTEXT GUARD: 40 / 50 used"
    And stderr ends with the reset code "\033[0m"

#### Scenario: Stderr output is critical-colored when within 8% of limit

    Given the context_guard_threshold is set to 50
    And the turn count for the current AGENT_ID is currently 45
    And stderr is a terminal
    When the context guard script runs
    Then stderr contains the critical color code "\033[38;2;248;113;113m"
    And stderr contains "CONTEXT GUARD: 46 / 50 used"
    And stderr ends with the reset code "\033[0m"

#### Scenario: Exceeded threshold uses critical color

    Given the context_guard_threshold is set to 10
    And the turn count for the current AGENT_ID is currently 10
    And stderr is a terminal
    When the context guard script runs
    Then stderr contains the critical color code "\033[38;2;248;113;113m"
    And stderr contains "CONTEXT GUARD: 11 / 10 used -- Run /pl-resume save"
    And stderr ends with the reset code "\033[0m"

#### Scenario: No ANSI codes when stderr is not a terminal

    Given the context_guard_threshold is set to 50
    And the turn count for the current AGENT_ID is currently 45
    And stderr is redirected to a file
    When the context guard script runs
    Then stderr output contains no ANSI escape codes
    And stderr contains "CONTEXT GUARD: 46 / 50 used"

#### Scenario: JSON additionalContext remains uncolored regardless of zone

    Given the context_guard_threshold is set to 50
    And the turn count for the current AGENT_ID is currently 45
    And stderr is a terminal
    When the context guard script runs
    Then stdout JSON additionalContext contains "CONTEXT GUARD: 46 / 50 used" without ANSI codes

### Manual Scenarios (Human Verification Required)

None.

