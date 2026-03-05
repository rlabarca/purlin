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
- The script increments an integer counter stored in `.purlin/runtime/turn_count`.
- The counter file contains only the integer count (no other data).

### 2.2 Threshold Configuration

- The threshold is read from `.purlin/config.json` at key `context_guard_threshold`.
- Default threshold when the key is absent: **30 turns**.
- The threshold represents approximately 60-70% of usable context (~30 turns at ~3-5K tokens per turn ≈ 90-150K tokens consumed, out of ~170K usable context after system prompt).

### 2.3 Session Detection

- A new session is detected when the turn count file's modification timestamp is older than the current shell session start time, OR when the file does not exist.
- On new session detection, the counter resets to 0 before incrementing.
- Session start time is determined by checking the process start time of the parent Claude Code process, or by using a session marker file (`.purlin/runtime/session_id`) that the hook creates on first invocation.

### 2.4 Warning Output

- When the counter exceeds the configured threshold, the hook outputs a JSON object to stdout with the warning in the `hookSpecificOutput.additionalContext` field. This is the only output format that Claude Code surfaces to the agent in PostToolUse hooks — plain `echo`/stdout text is visible in the user's terminal but NOT to the agent.
- The warning message: `[CONTEXT GUARD] Turn ${N}/${THRESHOLD}. Run /pl-resume save, then /clear, then /pl-resume to continue.`
- The warning fires on every turn after the threshold is exceeded (not just the first crossing), to ensure the agent sees it even if earlier warnings were lost to context compression.

### 2.5 Hook Registration

- The hook is registered in the project-level `.claude/settings.json` under the `hooks` key, as a `PostToolUse` hook.
- The hook runs the shell script at `tools/hooks/context_guard.sh`.

### 2.6 No Token Counting

- The hook MUST NOT attempt to count tokens or query context window usage. Claude Code hooks do not expose token counters. Turn count is the proxy metric.

---

## 3. Scenarios

### Automated Scenarios

#### Scenario: Counter increments on each invocation

    Given the turn count file does not exist
    When the context guard script runs 3 times
    Then the turn count file contains "3"

#### Scenario: Warning fires when threshold exceeded

    Given the context_guard_threshold is set to 5 in config.json
    And the turn count is currently 5
    When the context guard script runs
    Then stdout contains "[CONTEXT GUARD] Turn 6/5"

#### Scenario: Counter resets on new session

    Given the turn count file exists with value "25" and a stale timestamp
    When the context guard script runs in a new session
    Then the turn count file contains "1"

#### Scenario: Default threshold when config key absent

    Given config.json does not contain context_guard_threshold
    When the context guard script reads the threshold
    Then the threshold value is 30

#### Scenario: Warning repeats after threshold

    Given the context_guard_threshold is set to 2
    And the turn count is currently 3
    When the context guard script runs
    Then stdout contains "[CONTEXT GUARD] Turn 4/2"

### Manual Scenarios (Human Verification Required)

None.

## User Testing Discoveries

### [BUG] Context guard not preventing agent context overbounding (Discovered: 2026-03-04)
- **Scenario:** Warning fires when threshold exceeded (Section 3)
- **Observed Behavior:** The hook is registered and the script is running (turn count increments correctly), but agents are still overbounding context. The warning is either not firing in time or not being acted upon. `context_guard_threshold` is not set in config, so the default of 30 applies -- this may be too late to prevent degradation.
- **Expected Behavior:** The warning should fire early enough that the agent can save state and clear context before attention degrades. The Builder should investigate: (1) whether 30 turns is an appropriate default; (2) whether the warning output is visible to the agent; (3) whether session resets are occurring unexpectedly.
- **Action Required:** Builder
- **Status:** RESOLVED
- **Resolution:** Root cause was PostToolUse hook output format. Plain stdout from PostToolUse hooks is NOT surfaced to the agent — only JSON with `hookSpecificOutput.additionalContext` is visible. Changed hook output from `echo` to JSON format with `additionalContext` field. Warning is now confirmed visible to the agent.
