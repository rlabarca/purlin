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
- Creating or modifying discovery sidecar files (`features/<name>.discoveries.md`) in this project
- Recording discoveries and making status commits

If the framework itself needs to change, communicate that need to the user.
Changes to Purlin must be made in the Purlin repository.

## Test Priority Tiers

Classify features for QA verification ordering. QA verifies smoke first,
standard next, full-only last. Features not listed default to standard.

| Feature | Tier |
|---------|------|
<!-- Example:
| login_flow | smoke |
| dashboard_core | smoke |
| user_settings | standard |
| tooltip_animations | full-only |
-->

### Smoke Tier Behavior (Optional Customization)

<!-- Uncomment to customize smoke-only mode behavior:
For smoke-tier features in "just smoke" mode, QA may:
- Verify only the first scenario per feature (quick sanity)
- Skip visual items (focus on behavioral correctness)
-->

### Time Estimation Multipliers (Optional)

<!-- Uncomment to override default per-item time estimates:
- manual_interactive: 2 minutes (default)
- manual_visual: 1 minute (default)
- manual_hardware: 5 minutes (default)
-->

## Content Guidance
This file carries project-specific verification rules and domain context. Workflow procedures and multi-step protocols belong in skill files (`.claude/commands/pl-*.md`), not here.
