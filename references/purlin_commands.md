# Purlin commands

Twelve skills, no permission system. Six are the core loop; six support it. This page is the one
home of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md`, the
README table and the `agents/purlin.md` table all carry the sentence in the Purpose column
below, and nothing repeats it in its own words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "what needs a person" reaches `purlin:sign`. Every command ends
by naming the next step, computed from the cells it found.

Three commands carry the three evidence levels: `purlin:test` runs level 1, `purlin:audit` runs
level 2 and writes the record, and `purlin:sign` is level 3. `references/hard_gates.md` says
which levels a project asks for.

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Scaffold or edit a feature spec in the 2-section format | An engineer's agent, or a PM or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Inject a spec's rules into context, then implement them | An engineer, on every change. With no name it reads the board |
| `purlin:test [feature]` | Run the tagged tests and print each rule's passed cell | An engineer, constantly. Seconds; tests only |
| `purlin:audit [feature]` | Run the tests and the breaks, then write the record | An engineer locally; CI on every push and pull request |
| `purlin:sign [feature] [RULE-N]` | Walk the review list, or sign a rule, a feature or a batch as a signed commit | Anyone on the signer list. With no argument it walks the list |
| `purlin:drift [role]` | Report what changed since the last record, by role | Everyone, at session start and before a release |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Initialize a project for Purlin | An engineer, once. One question |
| `purlin:anchor <cmd>` | Create and manage anchor specs, local or pinned from elsewhere | An engineer, or a PM in Claude Code |
| `purlin:status` | Show every rule's cells and what blocks the gate | Anyone with a checkout, any time |
| `purlin:find [name]` | Find a spec by name and show its rules' cells | An engineer, to locate one |
| `purlin:rename <old> <new>` | Rename a feature across specs, tests, signatures and records | An engineer |
| `purlin:spec-from-code [dir]` | Reverse-engineer 2-section specs from existing code | An engineer, once, on a codebase that predates Purlin |

## Syntax

```
Purlin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Specifying
  ──────
  purlin:spec <name>              Scaffold or edit a feature spec
  purlin:spec <name> --resolve    Reconcile rule ids after a merge conflict
  purlin:spec-from-code [dir]     Reverse-engineer specs from existing code
  purlin:find [name]              Find a spec, or list them all

  Building
  ──────
  purlin:build [name]             Implement a spec's rules and their tests
  purlin:test [feature ...]       Run the tagged tests, unit tier
  purlin:test --all               Run every tier

  Proving
  ──────
  purlin:audit [feature ...]      Tests, breaks, and a record
  purlin:audit --ci               The CI run: the record and the briefs
  purlin:audit --remote           Push, wait for CI, pull the records it wrote
  purlin:audit --tag <name>       Pin this state as record/<name>
  purlin:sign                     Walk the review list one brief at a time
  purlin:sign <feature> [RULE-N ...]  Sign, as a signed commit
  purlin:sign --batch             Sign everything currently signable
  purlin:sign <feature> RULE-N --hold "<case>"  The test does not prove the proof
  purlin:sign <feature> RULE-N --note "<text>"  Evidence for a @manual proof

  Reporting
  ──────
  purlin:status                   Every rule's cells, and what blocks the gate
  purlin:drift [pm|design|qa|eng] What changed that the specs have not caught up with
  purlin:drift --since <N|date>   A window other than since the last record

  Project
  ──────
  purlin:init                     One question: what must be true before merge
  purlin:init --gate <level>      passed, strong or signed, afterwards
  purlin:init --ci                Add the workflow under the passed gate
  purlin:init --add <language>    Wire another language's test framework
  purlin:init --update            Bring the project up to the installed plugin
  purlin:anchor create <name>     A local anchor
  purlin:anchor add <url> --path <file>   Pin an anchor from another repository
  purlin:anchor sync [name|--all] [--check]   Advance a pin
  purlin:anchor propose <name>    Draft the change where the anchor lives
  purlin:rename <old> <new>       Rename a feature everywhere

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## What each command writes

| Command | Writes |
|---------|--------|
| `purlin:spec`, `purlin:spec-from-code` | `specs/<category>/<name>.md` |
| `purlin:build` | Code, test files, and the commit carrying the changeset |
| `purlin:test` | `.purlin/runtime/proofs/` only, which is not committed |
| `purlin:audit` | `.purlin/records/<feature>/<timestamp>-<commit7>-<runner>[-<os>].json`; under `--ci` also `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json`; the tag under `--tag` |
| `purlin:sign` | `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, or `<signer-slug>.hold.json` under `--hold`, in a signed commit. Proof lines in a spec when the walk adds a case |
| `purlin:init` | `.purlin/`, `specs/`, the test wiring, and the workflow when the gate needs one |
| `purlin:anchor` | `specs/_anchors/<name>.md`, and `designs/<anchor>/` on a sync |
| `purlin:rename` | Specs, markers, signature directories, record directories |
| `purlin:status`, `purlin:find`, `purlin:drift` | Nothing |

## What each command shows at each gate

A command prints only what the gate asks for. Under `passed` there is no strength, no risk, no
review list and no signature anywhere in the output, and `purlin:audit` runs no breaks. Under
`strong` the strength, the strong cell, the review list and risk appear, and a local
`purlin:audit` prints its strength as a preview and says only CI's record counts. Under `signed`
the signed cell, the signer list and the sign panel appear.

`purlin:sign` under `passed` says the gate is `passed`, names what `purlin:init --gate strong`
would add, and stops. `purlin:drift qa` says the same.

## Path resolution

Every `references/`, `templates/`, `scripts/` and `agents/` path a skill or an agent names is
relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`: `references/purlin_commands.md` means
`${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`. The paths are written bare because the
reader is the agent, which resolves them once.

Everything else is relative to the project root: `specs/`, `designs/`, `.purlin/`, and the
project's own source and test files. A consumer project carries no `references/`, no `scripts/`
and no `templates/` of its own, so the two roots never collide over one path. A shell script
that needs the same answer outside a skill resolves it the way the hook shims do, from the two
install locations `docs/getting-started.md` names.

## Pending migrations

When `sync_status` opens with a pending-migrations advisory, stop before doing the skill's work,
print the advisory and its directive, and ask whether to run `purlin:init --update` now. A spec
written against a reading the installed plugin has moved on from is written against an answer
the next release drops.

The advisory names one migration per line with its count and the files it counted, and ends with
`→ Run: purlin:init --update`. `purlin:init --update --check` prints the same list as JSON and
writes nothing, which is what a preflight in CI runs.
