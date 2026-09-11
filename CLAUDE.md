# Developing Purlin

This repo IS the Purlin plugin framework — and it uses Purlin to develop itself. The agent definition (`agents/purlin.md`) applies here: spec-driven development, rule-proof coverage, all of it. This CLAUDE.md provides **project-specific overrides and extensions** for developing the framework.

## Format Reference Versioning

The files in `references/formats/` are **versioned contracts**. External tools, anchor authors, and consumer projects depend on them. Each format file has a `> Format-Version: N` line at the top.

**When to bump the version:**
- Adding or removing a REQUIRED field → bump
- Changing the structure (new sections, renamed sections) → bump
- Adding an OPTIONAL field → bump (consumers may need to handle it)
- Clarifying documentation, adding examples, fixing typos → do NOT bump

**Procedure when changing spec/proof/anchor parsing or emission:**
1. Make the code change (in `scripts/mcp/purlin_server.py`, `scripts/proof/`, or skill definitions)
2. Update the corresponding format file in `references/formats/` to match
3. If the change is structural (new field, removed field, changed structure): bump `> Format-Version:` by 1
4. Update `references/spec_quality_guide.md` if the change affects quality guidance
5. Grep for references to the changed format in `docs/`, `skills/`, and `agents/purlin.md` — update any that are now stale
6. Commit the format change in the SAME commit as the code change — never let them drift

**Format files and what they govern:**
- `spec_format.md` — parsed by `sync_status` (rule extraction, metadata)
- `anchor_format.md` — anchor format (local and externally-referenced), parsed by `sync_status` + `purlin:anchor sync`
- `proofs_format.md` — emitted by proof plugins, read by `sync_status`

Each file has its own `> Format-Version: N` line — check the file directly for the current version.

## Skill and Reference Deduplication (CRITICAL)

**Never duplicate logic across skills or agent instructions.** When the same concept (proof markers, commit formats, test quality rules, framework detection, failure diagnosis) appears in multiple skills, it MUST live in a single reference file in `references/` and be pointed to from each skill. Skills that need the same behavior should call each other rather than reimplement — e.g., `purlin:build` and `purlin:verify` delegate test execution to `purlin:test` instead of inlining their own `pytest`/`jest`/`bash` commands.

**Before adding instructions to a skill, check:**
1. Does another skill already have this logic? → Reference it or call that skill
2. Does a reference file already cover this? → Point to it, don't repeat it
3. Is this reusable across 2+ skills? → Put it in `references/`, reference from each skill

**Authoritative reference files:**
- `references/formats/proofs_format.md` — proof marker syntax (pytest, Jest, Shell)
- `references/audit_criteria.md` — test quality rules, HOLLOW/WEAK/STRONG criteria, scoring
- `references/commit_conventions.md` — all commit message prefixes and formats
- `references/spec_quality_guide.md` — rule writing, tier assignment, failure diagnosis
- `references/drift_criteria.md` — file classification, config field ownership, drift detection
- `references/supported_frameworks.md` — test framework detection heuristics

**When modifying a skill:** grep all other skills for the same concept. If you find duplicates, consolidate into the reference file and update all skills to point to it in the same commit.

## Releasing a New Version

The version string lives in **one file**: `VERSION` at the project root. Never hand-edit any
other version literal.

**When tagging a release or updating RELEASE_NOTES.md with a new version:**
1. `bash dev/bump_version.sh <semver>`: writes `VERSION` and propagates it to every derived
   location in one step
2. Commit `VERSION` and every file the script touched in the SAME commit
3. Tag and push

**Derived locations** (the script's header comment is the authoritative list; add a row there
and `--check` starts guarding it in the same edit):

| Location | Why it carries a literal |
|----------|--------------------------|
| `templates/config.json` | stamped into new projects by `purlin:init` |
| `.claude-plugin/plugin.json` | what the Claude plugin loader reports |
| `.purlin/config.json` | this repo's own project stamp; the dashboard reports it |

`scripts/mcp/purlin_server.py` reads `VERSION` at runtime via `_read_version()`, so there is no
literal and no change needed. Docs that describe the config `version` field cite the `VERSION` file by name
rather than restating a number (`purlin_version` RULE-8), so no doc table can go stale.

**CI record:** `.github/workflows/version-check.yml` runs `bash dev/bump_version.sh --check` on
every push or PR that touches a version-bearing file, then runs the `purlin_version` proofs. The
job log prints `VERSION` alongside each derived location marked `ok` / `DRIFT` / `absent`, so
what the version was and what disagreed is recorded per commit. Run the same command locally
before committing a bump. The `purlin_version` spec (`specs/instructions/purlin_version.md`)
covers all four locations plus the script itself (RULE-6/7/8).

## Tool Folder Separation

*   **`scripts/`** — Consumer-facing framework tooling. Consumer projects depend on this directory; it is the only directory included in the distributed framework contract.
*   **`dev/`** — Purlin-repository maintenance scripts. Scripts here are specific to developing, building, and releasing the Purlin framework itself. They are NOT designed for consumer use.
