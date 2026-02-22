# Builder Overrides (Project-Specific)

> This file extends the base Builder instructions from the framework.
> Add project-specific build rules, tech stack constraints, and environment protocols below.

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
- Modifying this project's own source code, tests, and implementation files
- Creating and editing this project's own `features/` specs

If the framework itself needs to change, communicate that need to the user.
Changes to Purlin must be made in the Purlin repository.

## Tech Stack Constraints
<!-- Define the project's language, framework, and dependency rules -->

## Build & Environment Overrides
<!-- Add project-specific build commands, environment variables, and deployment protocols -->

## Testing Overrides
<!-- Add project-specific testing frameworks, coverage requirements, or test conventions -->
