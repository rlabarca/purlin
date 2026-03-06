# Implementation Notes: Skill -- /pl-help

### Command Table Source
The skill reads the role-appropriate command table from `instructions/references/{role}_commands.md` and prints the correct variant based on the current branch (main, collaboration, or isolated). This is the same logic used by the Startup Print Sequence and `/pl-resume`.

### Role Detection
Uses the same 3-tier fallback as `/pl-resume`: explicit argument, system prompt inference, then user prompt.
