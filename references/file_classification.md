# File Classification

> Every project file falls into one of three buckets: **Spec**, **Code**, or **Other**.
> The write guard (`write-guard.sh`) and sync tracker use this classification to route
> writes through skills and track sync state. INVARIANT and QA are specialized subtypes.
> When adding a new file type, update this file — do not add it inline to other definitions.

## CODE

Executable, interpreted, or controls agent behavior at runtime.

- Source code (`*.py`, `*.sh`, `*.js`, `*.ts`, `*.go`, etc.)
- Scripts and DevOps tooling (`scripts/`, `dev/`)
- Tests and test infrastructure (`tests/`)
- Application config (`package.json`, `pyproject.toml`, `tsconfig.json`, etc.)
- Skill files (`skills/*/SKILL.md`) — agent instructions that are code
- Agent definitions (`agents/*.md`)
- Hooks (`hooks/scripts/*.sh`)
- Build/CI configuration (`.github/`, `Makefile`, `Dockerfile`, etc.)
- Technical anchors (`features/**/arch_*.md`)
- Companion files (`features/**/*.impl.md`)
- Process config (`.purlin/config.json`, `.purlin/toolbox/*.json`)

## SPEC

Defines WHAT the system should do, not HOW.

- Feature specs (`features/**/*.md`, excluding `*.impl.md`, `*.discoveries.md`, `arch_*.md`)
- Design anchors (`features/**/design_*.md`)
- Policy anchors (`features/**/policy_*.md`)
- Visual design artifacts (Figma exports, design images)
- Prose documentation (`README.md`)

## QA-OWNED

Verification artifacts and test lifecycle management.

- Discovery sidecars (`features/**/*.discoveries.md`) — QA owns lifecycle (OPEN → RESOLVED → PRUNED)
- QA scenario tags (`@auto`/`@manual` suffixes on scenario headings)
- Regression test JSON (`tests/qa/scenarios/*.json`, `tests/*/regression.json`)
- QA verification scripts (`tests/qa/*.sh`)

## Recording Rights

Some files are owned by one classification but can be written to by any user:

| File | Owner | Who can record |
|------|-------|---------------|
| `features/**/*.impl.md` | CODE | Anyone writes; PM reads and acknowledges |
| `features/**/*.discoveries.md` | QA (lifecycle) | Anyone can add new OPEN entries |
| `features/**/*.md` QA Scenarios section | SPEC (initial) | QA adds `@auto`/`@manual` tags |

## OTHER (Freely editable, no feature tracking)

Files explicitly excepted from code tracking via `write_exceptions` in `.purlin/config.json`. These are the third bucket in the three-bucket model — neither spec nor code.

- Documentation (`docs/`)
- Project readme (`README.md`)
- Changelog (`CHANGELOG.md`)
- License (`LICENSE`)
- Git config (`.gitignore`, `.gitattributes`)

**Behavior:**
- Freely editable without a skill — no active_skill marker needed.
- Not tracked against any feature — no sync drift, no orphan scanning.
- Shown informationally in `purlin:status` and `purlin:whats-different`.
- Managed via `purlin:classify add|remove|list`.

**Default exceptions** are seeded by `purlin:init` and stored in `.purlin/config.json`:
```json
{
  "write_exceptions": ["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore", ".gitattributes"]
}
```

Projects can add or remove exceptions at any time via `purlin:classify`.

## INVARIANT (External, immutable)

Externally-sourced constraint documents that no local user can modify.

- Invariant files (`features/_invariants/i_*.md`)
- Changes ONLY via `purlin:invariant sync`, `purlin:invariant add`, or `purlin:invariant add-figma`
- The write guard blocks ALL write attempts with:
  "This is an externally-sourced invariant. Changes come only from the external source via purlin:invariant sync."

See `references/invariant_model.md` for the full invariant model.

## Custom File Classifications (Project-Specific)

Projects can override or extend the default classification rules by adding a `## Purlin File Classifications` section to their CLAUDE.md file. This is the standard way to teach the write guard about project-specific file types.

### Format

```markdown
## Purlin File Classifications
- `docs/` → SPEC
- `config/` → CODE
- `static/assets/` → CODE
```

### Rules

- Valid classifications: `CODE`, `SPEC`, `QA`.
- INVARIANT cannot be assigned via CLAUDE.md — invariant files are managed exclusively by `purlin:invariant`.
- **Plugin isolation:** Custom rules use prefix matching only, so they only affect project-relative paths. Purlin plugin files (which receive absolute paths from the write guard when outside the project root) are immune to project-level custom rules. Consumer projects can freely reclassify their own `scripts/`, `docs/`, etc.
- Patterns use prefix matching: `docs/` matches any file path starting with or containing `docs/`.
- Custom rules are evaluated **before** built-in rules, so they can override defaults.
- One rule per line, using the exact `- \`pattern\` → CLASSIFICATION` format.

### When this is needed

When the write guard blocks a write with "has no file classification rule", it means the file type is UNKNOWN. The agent will ask which classification this file type should have, then persist the answer in CLAUDE.md. From that point forward, the guard enforces the custom rule mechanically.

## Quick Reference for Write Guard

Before writing a file, check:

| Target file matches... | Write guard behavior |
|------------------------|---------------------|
| System files (`.purlin/`, `.claude/`) | **ALLOWED** — always writable |
| Any INVARIANT pattern above | **BLOCKED** — use `purlin:invariant` with bypass lock |
| Any SPEC pattern above (`features/`) | **ALLOWED** with active_skill marker; **BLOCKED** without |
| Any OTHER pattern above | **ALLOWED** — freely editable, no skill needed |
| Any CODE/QA pattern above | **ALLOWED** with active_skill marker; **BLOCKED** without |
| UNKNOWN (no rule matches) | **BLOCKED** — ask user, add to CLAUDE.md |
