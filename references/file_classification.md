# File Classification

> This file defines which files are CODE, SPEC, or QA-owned. All mode write-access
> rules in PURLIN_BASE.md and skill files reference this classification. When adding
> a new file type, update this file — do not add it inline to mode definitions.

## CODE (Engineer-owned)

Executable, interpreted, or controls agent behavior at runtime.

- Source code (`*.py`, `*.sh`, `*.js`, `*.ts`, `*.go`, etc.)
- Scripts and DevOps tooling (`tools/`, `dev/`)
- Tests and test infrastructure (`tests/`)
- Application config (`package.json`, `pyproject.toml`, `tsconfig.json`, etc.)
- Skill files (`.claude/commands/*.md`) — agent instructions that are code
- Instruction files (`instructions/*.md`)
- Agent definitions (`.claude/agents/*.md`)
- Hooks (`tools/hooks/*.sh`)
- Build/CI configuration (`.github/`, `Makefile`, `Dockerfile`, etc.)
- Launcher scripts (`pl-run*.sh`)
- Technical anchors (`features/arch_*.md`)
- Companion files (`features/*.impl.md`)
- Process config (`.purlin/config.json`, `.purlin/toolbox/*.json`)
- Override files (`.purlin/PURLIN_OVERRIDES.md`)

## SPEC (PM-owned)

Defines WHAT the system should do, not HOW.

- Feature specs (`features/*.md`, excluding `*.impl.md`, `*.discoveries.md`, `arch_*.md`)
- Design anchors (`features/design_*.md`)
- Policy anchors (`features/policy_*.md`)
- Visual design artifacts (Figma exports, design images)
- Prose documentation (`README.md`)

## QA-OWNED

Verification artifacts and test lifecycle management.

- Discovery sidecars (`features/*.discoveries.md`) — QA owns lifecycle (OPEN → RESOLVED → PRUNED)
- QA scenario tags (`@auto`/`@manual` suffixes on scenario headings)
- Regression test JSON (`tests/qa/scenarios/*.json`, `tests/*/regression.json`)
- QA verification scripts (`tests/qa/*.sh`)

## Cross-Mode Recording Rights

Some files are OWNED by one mode but can be RECORDED TO by others:

| File | Owner | Who can record |
|------|-------|---------------|
| `features/*.impl.md` | Engineer | Engineer writes; PM reads and acknowledges |
| `features/*.discoveries.md` | QA (lifecycle) | Any mode can add new OPEN entries |
| `features/*.md` QA Scenarios section | PM (initial) | QA adds `@auto`/`@manual` tags |
| `.purlin/PURLIN_OVERRIDES.md` | Engineer | Any mode can edit any section via `purlin:override-edit` |

## INVARIANT (External, immutable)

Externally-sourced constraint documents that no local mode can modify.

- Invariant files (`features/i_*.md`)
- NO mode (Engineer, PM, QA) can write to these files
- Changes ONLY via `purlin:invariant sync`, `purlin:invariant add`, or `purlin:invariant add-figma`
- The mode guard blocks ALL write attempts with:
  "This is an externally-sourced invariant. Changes come only from the external source via purlin:invariant sync."

See `references/invariant_model.md` for the full invariant model.

## Quick Reference for Mode Guard

Before writing a file, check:

| Target file matches... | Required mode |
|------------------------|---------------|
| Any CODE pattern above | Engineer |
| Any SPEC pattern above | PM |
| Any QA-OWNED pattern above | QA |
| Any INVARIANT pattern above | **BLOCKED** — use `purlin:invariant` |
| Cross-mode recording exception | Current mode OK |
