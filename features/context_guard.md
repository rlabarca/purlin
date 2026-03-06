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

- Per-agent settings are supported. Each agent entry in `config.json` may contain:
    - `context_guard` (boolean): Enables or disables the guard for that agent. Default: `true`.
    - `context_guard_threshold` (integer): The turn threshold for that agent. Default: inherited from global.
- **Threshold resolution order:** `agents.<role>.context_guard_threshold` > global `context_guard_threshold` > hardcoded `45`.
- **Enabled resolution order:** `agents.<role>.context_guard` > default `true`.
- The global `context_guard_threshold` top-level key is retained for backward compatibility and serves as the fallback when no per-agent threshold is configured.
- The threshold represents approximately 75-85% of usable context (~45 turns at ~3-5K tokens per turn ≈ 135-225K tokens consumed, out of ~200K usable context after system prompt).

### 2.2.1 Agent Role Detection

- The hook reads the `AGENT_ROLE` environment variable to determine which agent's config to use.
- `AGENT_ROLE` is set by the launcher scripts (see `agent_launchers_common.md` Section 2.1).
- Valid values: `architect`, `builder`, `qa`.
- When `AGENT_ROLE` is not set (e.g., direct `claude` invocation without a launcher): the hook falls back to global config behavior — global `context_guard_threshold` with the guard always enabled.

### 2.2.2 Config Reading via Resolver

- The hook uses `resolve_config.py --dump` combined with inline Python to extract nested per-agent values from the resolved config.
- This avoids modifying the `--key` CLI mode of `resolve_config.py`, which only supports top-level keys.
- **Fallback chain:** per-agent `context_guard_threshold` > global `context_guard_threshold` > hardcoded 45.
- **Enabled chain:** per-agent `context_guard` > default `true`.

### 2.3 Session Detection

- A new session is detected when the turn count file's modification timestamp is older than the current shell session start time, OR when the file does not exist.
- On new session detection, the counter resets to 0 before incrementing.
- Session start time is determined by checking the process start time of the parent Claude Code process, or by using a session marker file (`.purlin/runtime/session_id`) that the hook creates on first invocation.

### 2.4 Context Status Output

- The hook outputs a JSON object to stdout on **every tool call** (not just when the threshold is exceeded). This provides continuous visibility into the context budget usage.
- Output uses the `hookSpecificOutput.additionalContext` field — the only format Claude Code surfaces to the agent in PostToolUse hooks. Plain `echo`/stdout text is visible in the user's terminal but NOT to the agent.
- **Format (normal):** `CONTEXT GUARD: ${COUNT} / ${THRESHOLD} used` where COUNT = turns consumed (incremented before output).
    - Example at turn 5 of 45: `CONTEXT GUARD: 5 / 45 used`
    - Interpretation: higher COUNT means closer to the limit.
- **Format (exceeded):** When COUNT >= THRESHOLD, append evacuation instructions.
    - Example at turn 48 of 45: `CONTEXT GUARD: 48 / 45 used -- Run /pl-resume save, then /clear, then /pl-resume to continue.`
- **No silent exits:** The hook MUST produce output on every tool call when the guard is enabled. Early exits for subagent detection or other conditions MUST still output the context guard status. The only exception is when `context_guard` is explicitly set to `false` for the current agent.
- **When guard is disabled** (`context_guard: false` for the current agent): No JSON output is produced. The counter still increments in the background so that re-enabling the guard mid-session shows an accurate count.
- **Context cost:** ~8-12 tokens per message. At 45 turns = ~360-540 tokens (<0.3% of usable context).

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

#### Scenario: Status output on every turn when guard enabled

    Given the context_guard_threshold is set to 10 in config.json
    And the turn count is currently 2
    When the context guard script runs
    Then stdout contains JSON with additionalContext "CONTEXT GUARD: 3 / 10 used"

#### Scenario: Exceeded threshold appends evacuation instructions

    Given the context_guard_threshold is set to 5 in config.json
    And the turn count is currently 5
    When the context guard script runs
    Then stdout contains "CONTEXT GUARD: 6 / 5 used -- Run /pl-resume save, then /clear, then /pl-resume to continue."

#### Scenario: Counter resets on new session

    Given the turn count file exists with value "25" and a stale timestamp
    When the context guard script runs in a new session
    Then the turn count file contains "1"

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
    And the turn count is currently 10
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
    And the turn count is currently 3
    When the context guard script runs
    Then stdout contains "CONTEXT GUARD: 4 / 2 used -- Run /pl-resume save, then /clear, then /pl-resume to continue."

#### Scenario: Per-agent threshold is used when AGENT_ROLE is set

    Given config.json has context_guard_threshold set to 45
    And agents.builder.context_guard_threshold is set to 60
    And AGENT_ROLE is "builder"
    And the turn count is currently 0
    When the context guard script runs
    Then stdout contains "CONTEXT GUARD: 1 / 60 used"

#### Scenario: Subagent detection still outputs context guard status

    Given the turn count file was modified within the last 120 seconds
    And the session_id file contains a different session_id than the hook input
    And the guard is enabled
    When the context guard script runs
    Then stdout contains JSON with additionalContext matching "CONTEXT GUARD:"
    And the turn count file is NOT incremented

#### Scenario: Counter resets after session_id file deletion

    Given the turn count file exists with value "42"
    And the session_id file does not exist
    When the context guard script runs
    Then the turn count file contains "1"
    And stdout contains "CONTEXT GUARD: 1 /"

#### Scenario: Guard output on every tool call with no silent exits

    Given the guard is enabled for the current agent
    When the context guard script runs under any condition (new session, existing session, subagent)
    Then stdout contains JSON with additionalContext matching "CONTEXT GUARD:"

### Manual Scenarios (Human Verification Required)

None.

## User Testing Discoveries

### [BUG] Threshold shows 45 when per-agent config sets 60

**Status:** OPEN
**Date:** 2026-03-06
**Discovered by:** User (Architect session)
**Action Required:** Builder

**Observed:** Hook output shows `CONTEXT GUARD: ... / 45` despite `config.local.json` having `context_guard_threshold: 60` in the agent's config block.

**Expected:** Hook should show `... / 60` when the per-agent threshold is set to 60.

**Root Cause (probable):** The `AGENT_ROLE` environment variable may not be set when the hook runs outside of a launcher script, causing fallback to the global threshold (45). Alternatively, `resolve_config.py --dump` may not merge `config.local.json` overrides, or the inline Python extraction has a bug in the per-agent path.

**Scenario affected:** "Per-agent threshold overrides global"

---

### [BUG] Counter not resetting after /clear + /pl-resume

**Status:** OPEN
**Date:** 2026-03-06
**Discovered by:** User (Builder session)
**Action Required:** Builder

**Observed:** After running `/clear` then `/pl-resume`, the hook immediately shows an exhausted count (e.g., `42/45`) instead of resetting to 1.

**Expected:** After `/clear` + `/pl-resume`, the counter should show `1 / Y used` on the first tool call.

**Root Cause:** `/clear` does not change Claude Code's `session_id`. The hook sees the same `session_id`, doesn't detect a new session, and keeps the old `turn_count`. The `/pl-resume` restore flow resets `turn_count` to 0, but the `session_id` file must also be deleted so the hook treats the next invocation as a genuinely new session.

**Fix required:** `/pl-resume` Step 0 must delete `session_id` and all `session_id_*` files alongside resetting `turn_count`. (Spec updated in `pl_session_resume.md` Section 2.3.1.)

**Scenario affected:** "Counter resets after session_id file deletion" (new)

---

### [BUG] Hook silently exits for subagents with no output

**Status:** OPEN
**Date:** 2026-03-06
**Discovered by:** User (multiple sessions)
**Action Required:** Builder

**Observed:** Context guard message does not appear on every tool call. Some calls produce no output at all.

**Expected:** Every tool call should show `CONTEXT GUARD: X / Y used` when the guard is enabled.

**Root Cause:** Subagent detection (`IS_SUBAGENT=true`) causes `exit 0` with no JSON output. Other early-exit paths may also skip output silently.

**Fix required:** When subagent is detected, the hook should still output the current context guard status (reading the existing turn_count without incrementing) rather than exiting silently. The spec Section 2.4 has been updated to require output on every tool call with no silent exits.
