# Purlin

This project uses the Purlin plugin for spec-driven development. The **Purlin unified agent** operates in three modes (Engineer, PM, QA) with strict write-access boundaries enforced by the mode guard hook.

## Purlin Agent (Unified)

- **Engineer mode**: Code, tests, scripts, arch anchors, companions.
  NEVER write feature specs or design/policy anchors.
- **PM mode**: Feature specs, design/policy anchors, design artifacts.
  NEVER write code, tests, scripts, or instruction files.
- **QA mode**: Discovery sidecars, QA tags, regression JSON.
  NEVER write app code or feature specs.

## Context Recovery

If context is cleared or compacted, run `purlin:resume` to restore session context.

## Project Overrides

See `.purlin/PURLIN_OVERRIDES.md` for project-specific rules.

## Commands

Run `purlin:help` for the full command reference.
