# Implementation Notes: Context Guard

**[CLARIFICATION]** Session detection uses the `session_id` field from Claude Code's PostToolUse hook stdin JSON input as the primary session identifier. Falls back to `$PPID` (the Claude Code process PID) when stdin parsing fails or `session_id` is absent. (Severity: INFO)

**[CLARIFICATION]** Threshold reading uses python3 for JSON parsing (consistent with project conventions). The `try/except` wrapper handles missing files, malformed JSON, and IO errors with a fallback to the default value of 30. (Severity: INFO)

**[DISCOVERY]** PostToolUse hooks require JSON output with `hookSpecificOutput.additionalContext` for agent visibility. Acknowledged — spec Section 2.4 updated to specify JSON output format requirement. Plain `echo`/stdout is NOT surfaced to the agent in PostToolUse hooks — it only appears in the user's terminal. The original implementation used plain `echo` which is why agents never saw the warning despite the counter working correctly. Fixed by outputting JSON with the warning in `additionalContext`. This is a Claude Code platform behavior that should be documented in the spec's Section 2.4. (Severity: HIGH)

**[DISCOVERY]** ~~Spec Section 2.2 says default threshold is 45 turns, but the automated scenario "Default threshold when config key absent" (Section 3) still says "Then the threshold value is 30". Code and tests updated to match Section 2.2 (45). The Architect needs to update the scenario's expected value from 30 to 45. (Severity: HIGH)~~ **ACKNOWLEDGED** — Scenario updated to expect 45.

**[CLARIFICATION]** File locking uses `mkdir`-based mutex (atomic on POSIX) since `flock` is unavailable on macOS. The lock serializes parallel PostToolUse hook invocations that fire simultaneously when Claude Code processes multiple tool calls in a single response. Without this, parallel hooks read-increment-write the same count value, causing the counter to under-count by a factor of 3-5x. A 2-second stale lock timeout prevents deadlocks from crashed processes. (Severity: INFO)
