# QA Overrides

> Project-specific QA rules. Add verification protocols, environment constraints, and domain-specific testing procedures here.

## HARD PROHIBITION: Purlin Submodule Is Read-Only

**You are working in a project that uses Purlin as a git submodule (located at `purlin/`).
You MUST NEVER create, modify, or delete any file inside the `purlin/` directory.**

This is unconditional. No exception exists in any scenario.

Prohibited without exception:
- Editing any file under `purlin/` (instructions, tools, features, scripts, or any other path)
- Running `git add`, `git commit`, or any git operation that stages or commits files from `purlin/`
- Creating new files inside `purlin/`

What IS permitted:
- **Executing** scripts from `purlin/tools/` (e.g., `purlin/tools/critic/run.sh`)
- Modifying the `## User Testing Discoveries` section of this project's own `features/` files
- Recording discoveries and making status commits

If the framework itself needs to change, communicate that need to the user.
Changes to Purlin must be made in the Purlin repository.
