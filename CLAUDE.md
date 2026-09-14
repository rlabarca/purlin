# Developing Purlin

This repository is the Purlin plugin framework, and it uses Purlin to develop itself. The agent
definition (`agents/purlin.md`) applies here in full; this file carries the overrides and
extensions specific to developing the framework.

## Design and copy

Every visual surface and every line of prose follows `design/readme.md`, which is the authority.
It binds the dashboard, the CLI output, the pull request comment, the docs and this file.

- **Two surfaces, one system.** Warm navy, cream, blush and copper for the brand and the docs;
  `data-surface="product"` for the dashboard. Green, amber, red and teal mean pass, warn, fail
  and neutral on both. No other accent, no gradient, no shadow, no icon set beyond the unicode
  glyphs `▶ ▼ ▲ →`, and no emoji anywhere, CLI output and pull request comments included.
- **Machine text is monospace, human text is sans.** Commands, rule ids, paths, shas and gates in
  Courier New; prose in Arial. Sentence case; command names lowercase with the colon.
- **Tokens only.** Reference the semantic aliases in `design/tokens/theme-dark.css` and
  `theme-light.css`, never a raw palette value. Both themes ship.
- **Copy voice** follows "Content fundamentals": plain and declarative, second person for the
  reader, third person for the system, exact numbers, limits stated, no superlatives.
- Docs diagrams are mermaid with the init block from `docs/_mermaid.md`; screenshots come from
  the rebuilt dashboard; the logo is `design/assets/logo.svg`.

## Format reference versioning

The files in `references/formats/` are versioned contracts: external tools, anchor authors and
consumer projects depend on them. Each carries a `> Format-Version: N` line at the top; check the
file for the current number. **Bump it** when a required field is added or removed, when the
structure changes, or when an optional field is added, because a consumer may need to handle it.
Do not bump for clarified wording, a new example or a typo.

**When you change spec, proof, anchor, record or approval parsing or emission:**

1. Make the code change, in `scripts/mcp/purlin/`, `scripts/proof/`, `scripts/review/`,
   `scripts/run/` or a skill definition.
2. Update the matching file in `references/formats/`, bumping `> Format-Version:` by 1 when the
   change is structural.
3. Update `references/spec_quality_guide.md` when the change affects how a rule is written.
4. Grep `docs/`, `skills/` and `agents/purlin.md` for the format and fix what is now stale.
5. Commit the format change in the same commit as the code change. Never let the two drift.

| File | What it governs |
|------|-----------------|
| `spec_format.md` | The 2-section spec, parsed by `sync_status` |
| `anchor_format.md` | The anchor, local and pinned, parsed by `sync_status` and `purlin:anchor sync` |
| `proofs_format.md` | The proof files the test plugins emit, read by `sync_status` |
| `record_format.md` | The record `purlin:verify` writes, read by `sync_status` and the gate check |
| `approval_format.md` | The approval `purlin:approve` writes, read by `sync_status` and the gate check |

## Skill and reference deduplication

**Never duplicate logic across skills or agent instructions.** When the same concept appears in
two places, it lives in one reference file and both point at it. Skills that need the same
behaviour call each other rather than reimplement it: `purlin:build` and `purlin:verify` delegate
test execution to `scripts/run/purlin_run.py`, which `purlin:test` owns.

Before adding instructions to a skill, check whether another skill already has the logic, whether
a reference already covers it, and whether it is reusable across two or more skills. If any answer
is yes, point at the one home instead. When you modify a skill, grep the others for the same
concept and consolidate any duplicate in the same commit.

| Reference | What it is the one home of |
|-----------|---------------------------|
| `references/glossary.md` | The word this project uses for each concept, and every retired spelling |
| `references/purlin_commands.md` | Every command's syntax, its one purpose sentence, and what it writes |
| `references/hard_gates.md` | The gate, which records count, the branch rules, the approver list |
| `references/review_criteria.md` | The review list, the brief's layers, the four verdicts |
| `references/spec_quality_guide.md` | Writing a rule, assigning a tier, diagnosing a failure |
| `references/drift_criteria.md` | File classification, config field ownership, drift by role |
| `references/commit_conventions.md` | Every commit message prefix and shape |
| `references/supported_frameworks.md` | Test framework detection |
| `references/proof_plugin_contract.md` | The checklist for a proof plugin and how to prove one |
| `references/rule_examples.md` | Worked rules and proofs |

## Releasing a new version

The version string lives in one file: `VERSION` at the root. Never hand-edit any other literal.

1. `bash dev/bump_version.sh <semver>` writes `VERSION` and propagates it everywhere.
2. Commit `VERSION` and every file the script touched in the same commit.
3. Tag and push.

Derived locations, with the script's header comment as the authoritative list:
`templates/config.json` (stamped into new projects by `purlin:init`), `.claude-plugin/plugin.json`
(what the plugin loader reports), and `.purlin/config.json` (this repository's own project stamp).
Add a row there and `--check` guards it in the same edit. `scripts/mcp/purlin/__init__.py` reads
`VERSION` at runtime through `_read_version()`, so it carries no literal, and docs name the
`VERSION` file rather than restating a number (`purlin_version` RULE-8).

`.github/workflows/version-check.yml` runs `bash dev/bump_version.sh --check` on every push or
pull request touching a version-bearing file, then the `purlin_version` proofs. The job log prints
`VERSION` beside each derived location marked `ok`, `DRIFT` or `absent`. Run the same command
locally before committing a bump. `specs/instructions/purlin_version.md` covers all four locations
plus the script itself.

## Tool folder separation

Everything here ships: `.claude-plugin/marketplace.json` declares the plugin source as `./`, so an
install carries `scripts/`, `dev/`, `specs/`, `references/`, `docs/`, `skills/`, `agents/`,
`tools/` and `templates/`. The line below is not what ships; it is what a consumer may depend on.

- **`scripts/`** is the consumer-facing surface. A consumer project, a shipped skill, an agent
  definition or a reference may name a path under it, and its layout is held stable across
  releases. It is the only directory a consumer may depend on.
- **`dev/`** holds this repository's own maintenance, build and release scripts and its proofs.
  A path into `dev/`, or into this repository's own `specs/`, never appears in a prose line of a
  skill, an agent definition or a reference: a consumer's checkout has neither, so such a citation
  is an instruction that cannot be followed. `purlin_skills` and `purlin_references` hold that
  scope.
