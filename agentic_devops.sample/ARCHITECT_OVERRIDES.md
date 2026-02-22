# Architect Overrides (Project-Specific)

> This file extends the base Architect instructions from the framework.
> Add project-specific rules, domain context, and custom protocols below.

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

## Instruction File Scope Clarification

The base Architect instructions refer to "refining instruction files." In this project, that means
the `.agentic_devops/` override files (e.g., `ARCHITECT_OVERRIDES.md`, `HOW_WE_WORK_OVERRIDES.md`).
It does NOT mean `purlin/instructions/` — those are inside the submodule and are read-only.

## Project-Specific Mandates
<!-- Add project-specific Architect rules here -->

## Domain Context
<!-- Describe the project's domain, key entities, and constraints -->

## Custom Protocols
<!-- Add any project-specific protocols that extend the base workflow -->
