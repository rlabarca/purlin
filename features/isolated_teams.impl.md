## Implementation Notes

See [isolated_teams.md](isolated_teams.md) for the feature specification.

**Bash 3.2 compatibility (macOS):** The launcher script heredoc MUST NOT use bash 4.0+ features. macOS ships `/bin/bash` 3.2.57 which does not support `${var^}` (case modification). The role label capitalization uses a POSIX-compatible `case` statement instead. This also produces semantically correct labels ("QA" instead of "Qa").
