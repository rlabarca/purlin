<!-- purlin:start -->
# Purlin

This project uses the Purlin agentic workflow with role-restricted agents
(Architect, Builder, QA, PM). Each role has strict write-access boundaries.

## Role Boundaries

- **Architect / PM**: Spec and design only. NEVER write code, scripts, tests,
  or app config.
- **Builder**: Code, scripts, and tests only. NEVER write feature specs,
  instruction files, or anchor nodes.
- **QA**: Verification and discovery files only. NEVER write app code or
  feature specs.

## Context Recovery

If you cannot see "Role Definition: The <Role>" in your system prompt,
**do not write any files**. Run `/pl-resume` immediately to reload your
role instructions and confirm your identity.

## Commands

Run `/pl-help` for the full command reference.
<!-- purlin:end -->
