# Developing Purlin

This repository is the Purlin plugin framework, and it uses Purlin to develop itself. The agent
definition (`agents/purlin.md`) applies here in full; this file carries the overrides and
extensions specific to developing the framework.

## Design and copy

The look follows `design/readme.md` and the wording follows `references/writing_style.md`; each
is the authority for its half. They bind the dashboard, the CLI output, the docs and this file.

- **Two surfaces, one system.** Warm navy, cream, blush and copper for the brand, the docs and
  the dashboard, which sets no surface; `data-surface="product"` for the slate product ground.
  Green, amber, red and teal mean pass, warn, fail and neutral on both. No other accent, no gradient, no shadow, no icon set beyond the unicode
  glyphs `▶ ▼ ▲ → ◐ ◑`, and no emoji anywhere, CLI output included.
- **Machine text is monospace, human text is sans.** Commands, rule ids, paths and shas in
  Courier New; prose in Arial. Sentence case; command names lowercase with the colon.
- **Tokens only.** Reference the semantic aliases in `design/tokens/theme-dark.css` and
  `theme-light.css`, never a raw palette value. Both themes ship.
- **Copy voice** follows `references/writing_style.md`: plain and declarative, second person for
  the reader, third person for the system, exact numbers, limits stated, no superlatives.
- Docs diagrams are plain mermaid. The two screenshots, the board and one rule, are taken by
  `dev/capture_doc_screenshots.py` from the rebuilt dashboard and the fixtures; the logo is
  `design/assets/logo.svg`.

## Format reference versioning

The files in `references/formats/` are versioned contracts: external tools, anchor authors and
consumer projects depend on them. Each carries a `> Format-Version: N` line at the top; check the
file for the current number. **Bump it** when a required field is added or removed, when the
structure changes, or when an optional field is added, because a consumer may need to handle it.
Do not bump for clarified wording, a new example or a typo.

**When you change spec, proof, anchor, marker, evidence, signature or package parsing or
emission:**

1. Make the code change, in `scripts/mcp/purlin/`, `scripts/review/`, `scripts/run/`,
   `scripts/anchor/`, `scripts/export/` or a skill definition.
2. Update the matching file in `references/formats/`, bumping `> Format-Version:` by 1 when the
   change is structural.
3. Update `references/spec_quality_guide.md` when the change affects how a rule is written.
4. Grep `docs/`, `skills/`, `references/` and `agents/purlin.md` for the format and fix what is
   now stale.
5. Commit the format change in the same commit as the code change. Never let the two drift.

| File | What it governs |
|------|-----------------|
| `spec_format.md` | The 2-section spec, parsed by `sync_status` |
| `anchor_format.md` | The anchor, local and remote, parsed by `sync_status` and `purlin:anchor sync` |
| `marker_format.md` | The marker comment above a test, the `tests` setting, the four report formats and the tie, read by `purlin_run.py` and `sync_status` |
| `signature_format.md` | The sign-off `purlin:sign` writes over the evidence package, read by `purlin:sign` and `sync_status` |
| `package_format.md` | The evidence package `purlin:sign` builds, commits and checks, handed to a regulated sign-off system as evidence |
| `evidence_format.md` | The evidence file per feature per source and its fingerprint, written by `purlin:test`, `purlin:audit` and a project's own run on another system, read by `sync_status` and `purlin:sign` |

## Skill and reference deduplication

**Never duplicate logic across skills or agent instructions.** When the same concept appears in
two places, it lives in one reference file and both point at it. Skills that need the same
behaviour call each other rather than reimplement it: `purlin:build` and `purlin:audit` delegate
test execution to `scripts/run/purlin_run.py`, which `purlin:test` owns.

Before adding instructions to a skill, check whether another skill already has the logic, whether
a reference already covers it, and whether it is reusable across two or more skills. If any answer
is yes, point at the one home instead. When you modify a skill, grep the others for the same
concept and consolidate any duplicate in the same commit.

| Reference | What it is the one home of |
|-----------|---------------------------|
| `references/glossary.md` | The word this project uses for each concept, its one definition, and the chain |
| `references/purlin_commands.md` | Every command's syntax, its one purpose sentence, and what it writes |
| `references/evidence_and_signoff.md` | The two facts, what is left to do, which evidence counts for a sign-off, when a sign-off counts, what `signed/<version>` means |
| `references/review_criteria.md` | Which rules the audit reads and what sets its verdict; the heuristic spot tests and the research behind them; the planted bug; the instructions the model is sent |
| `references/spec_quality_guide.md` | Writing a rule, the guideline for a good proof, reading the cell that blocks it |
| `references/drift_criteria.md` | Drift's range and its one view, config field ownership, project root ownership |
| `references/commit_conventions.md` | Every commit message prefix and shape |
| `references/supported_frameworks.md` | Test framework detection, the `tests` entry the first test run suggests for each, and what each needs added |
| `references/rule_examples.md` | Worked rules and proofs |
| `references/writing_style.md` | How Purlin writes: voice, person, casing, numbers, machine text |

## Releasing a new version

The version string lives in one file: `VERSION` at the root. Never hand-edit any other literal.

1. `bash dev/bump_version.sh <semver>` writes `VERSION` and propagates it everywhere.
2. Commit `VERSION` and every file the script touched in the same commit.
3. Run `purlin:test --all --commit` and `python3 dev/windows_run.py`, then `purlin:sign`. The first
   sign-off writes the signed tag `signed/<version>`.
4. The owner pushes the tag: `git push origin signed/<version>`.

Derived locations, with the script's header comment as the authoritative list:
`.claude-plugin/plugin.json` (what the plugin loader reports) and `.purlin/config.json` (this
repository's own project stamp).
Add a row there and `--check` guards it in the same edit. `scripts/mcp/purlin/__init__.py` reads
`VERSION` at runtime through `_read_version()`, so it carries no literal (`purlin_version` RULE-2),
and docs name the `VERSION` file rather than restating a number.

`.github/workflows/version-check.yml` runs `bash dev/bump_version.sh --check` on every push or
pull request touching a version-bearing file, then the `purlin_version` proofs. The job log prints
`VERSION` beside each derived location marked `ok`, `DRIFT`, `FAIL` or `absent`. Run the same
command locally before committing a bump. `specs/instructions/purlin_version.md` covers all three
locations plus the script itself.

## Tool folder separation

Everything here ships: `.claude-plugin/marketplace.json` declares the plugin source as `./`, so an
install carries `scripts/`, `dev/`, `specs/`, `references/`, `docs/`, `skills/`, `agents/`,
`design/` and `templates/`. The line below is not what ships; it is what a consumer may depend on.

- **`scripts/`** is the consumer-facing surface. A consumer project, a shipped skill, an agent
  definition or a reference may name a path under it, and its layout is held stable across
  releases. It is the only directory a consumer may depend on.
- **`dev/`** holds this repository's own maintenance, build and release scripts and its proofs.
  A path into `dev/`, or into this repository's own `specs/`, never appears in a prose line of a
  skill, an agent definition or a reference: a consumer's checkout has neither, so such a citation
  is an instruction that cannot be followed. No proof checks this line across those files; the
  review of each change holds it.
