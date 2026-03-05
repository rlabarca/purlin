# Implementation Notes: Context Guard

**[CLARIFICATION]** Session detection uses the `session_id` field from Claude Code's PostToolUse hook stdin JSON input as the primary session identifier. Falls back to `$PPID` (the Claude Code process PID) when stdin parsing fails or `session_id` is absent. (Severity: INFO)

**[CLARIFICATION]** Threshold reading uses python3 for JSON parsing (consistent with project conventions). The `try/except` wrapper handles missing files, malformed JSON, and IO errors with a fallback to the default value of 30. (Severity: INFO)

**[CLARIFICATION]** File locking uses `mkdir`-based mutex (atomic on POSIX) since `flock` is unavailable on macOS. The lock serializes parallel PostToolUse hook invocations that fire simultaneously when Claude Code processes multiple tool calls in a single response. Without this, parallel hooks read-increment-write the same count value, causing the counter to under-count by a factor of 3-5x. A 2-second stale lock timeout prevents deadlocks from crashed processes. (Severity: INFO)
