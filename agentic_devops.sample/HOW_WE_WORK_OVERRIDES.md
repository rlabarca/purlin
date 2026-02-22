# How We Work: Project-Specific Additions

> This file extends the base workflow philosophy from the framework.
> Add project-specific workflow rules, team conventions, and process additions below.

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
- Modifying this project's own `.agentic_devops/` override files
- Creating and editing this project's own `features/` specs
- Writing root-level launcher scripts

If the framework itself needs to change, communicate that need to the user.
Changes to Purlin must be made in the Purlin repository.

## Project Workflow Additions
<!-- Add project-specific workflow rules or modifications here -->

## Team Conventions
<!-- Define any team-specific conventions, naming standards, or review protocols -->
