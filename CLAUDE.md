# Purlin

This project uses the Purlin agentic workflow. The **Purlin unified agent**
operates in three modes (Engineer, PM, QA) with strict write-access boundaries.
Legacy role-specific agents (PM, Engineer, QA, PM) are also supported
during the transition period.

## Purlin Agent (Unified)

- **Engineer mode**: Code, tests, scripts, arch anchors, companions, instructions.
  NEVER write feature specs or design/policy anchors.
- **PM mode**: Feature specs, design/policy anchors, design artifacts.
  NEVER write code, tests, scripts, or instruction files.
- **QA mode**: Discovery sidecars, QA tags, regression JSON.
  NEVER write app code or feature specs.

## Legacy Role Boundaries

- **PM / PM**: Spec and design only. NEVER write code, scripts, tests,
  or app config.
- **Engineer**: Code, scripts, and tests only. NEVER write feature specs,
  instruction files, or anchor nodes.
- **QA**: Verification and discovery files only. NEVER write app code or
  feature specs.

## Context Recovery

If you cannot see "Role Definition: The <Role>" in your system prompt,
**do not write any files**. Run `/pl-resume` immediately to reload your
role instructions and confirm your identity.

## Commands

Run `/pl-help` for the full command reference.
