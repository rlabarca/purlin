# Purlin commands

The eleven skills below. Six are the core loop; the rest support it. This page is the one home
of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md` and the
README table carry the sentence in the Purpose column below, and nothing repeats it in its own
words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "what is waiting on a person" reaches `purlin:sign`. Every
command ends by naming the next step, computed from the cells it found.

`purlin:test --remote` is the one command that pushes, and it pushes a run branch of its own,
never the branch you are on. Every other push is yours: `purlin:sign` ends on the line
`Run: git push origin signed/<version>`, and pushing it is your act.

Three commands carry the three evidence levels: `purlin:test` runs level 1 and writes what it
saw, `purlin:audit` runs level 2 and writes what it found, and `purlin:sign` is level 3.
`references/hard_gates.md` says which levels a project asks for. **The folder an evidence file
sits in is its source**: `purlin:test` and `purlin:audit` write yours under
`.purlin/evidence/local/`, and commit it only with `--commit`; the CI job runs the same run
script in an arm of its own and writes its section under `.purlin/evidence/ci/`, which it
always commits. That arm is the workflow's to pass and nobody types it. Both sources count at
every gate, `signed` included; the one setting that asks for a `ci` run before a signature is
`trust: remote`.

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs | A developer's agent, or product or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset | A developer, on every change. With no name it reads `sync_status` and names the specs with rules that have no passing test |
| `purlin:test [feature ...] [--all]` | Run the marked tests and print each rule's passed cell | A developer, constantly. Seconds; tests only. It writes the evidence, commits it with `--commit`, and never pushes |
| `purlin:audit [feature ...] [--all]` | Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence | A developer, any time. It writes the evidence, commits it with `--commit`, and never pushes |
| `purlin:sign [feature] [RULE-N ...]` | Walk the queue, or sign a rule, a feature or a batch as a signed commit | Anyone with commit signing set up; the signature names them. With no argument it walks the queue |
| `purlin:drift [role]` | Report what changed since your last pull, by role | Everyone, after a pull, a merge, a rebase, a checkout, a clone or a reset |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Set a project up for Purlin, and change the gate later | A developer, once. Four questions at most |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current | A developer, or product in Claude Code |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate | Anyone with a checkout, any time; with a name, to see one spec's rules |
| `purlin:export` | Write the evidence package for a version, the data file a regulated system of record reviews | Anyone, any time; `purlin:sign` writes it too, into the commit the tag names |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies | A developer, once, on a codebase that has no specs |

## Syntax

```
Purlin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Specifying
  ──────
  purlin:spec <name>              Write or edit a feature spec
  purlin:spec-from-code [dir]     Write the specs an existing codebase implies

  Building
  ──────
  purlin:build [name]             Write a spec's code and its marked tests
  purlin:test                     Run the features the change touched, write the evidence
  purlin:test <feature> [...]     The same, for the features named
  purlin:test --all               The same, for every feature
  purlin:test --commit            The same, then commit the evidence
  purlin:test --remote            Let the git host's runner do the run

  Proving
  ──────
  purlin:audit [feature ...]      Tests, breaks and the AI audit, into the evidence
  purlin:audit --all              The same, reading every rule again
  purlin:audit --commit           The same, then commit the evidence
  purlin:sign                     Walk the queue, then write the tag
  purlin:sign --release <name>    Name the tag something other than the version
  purlin:sign <feature> [RULE-N ...]  Sign, as a signed commit
  purlin:sign --batch             Sign every rule in the queue
  purlin:sign <feature> RULE-N --note "<text>"  Sign a hand check with what you saw

  Reporting
  ──────
  purlin:status                   Every rule's cells, and what blocks the gate
  purlin:status <name>            One spec: its rules and their cells
  purlin:drift [pm|eng|qa]        What changed since your last pull
  purlin:drift --since <N|date>   A window other than since your last pull
  purlin:export                   The evidence package for the version
  purlin:export --release <name>  The same, for another version name
  purlin:export --commit          The same, then commit the package
  purlin:export --check <file>    Check a package against its fingerprint

  Project
  ──────
  purlin:init                     The gate, the test command, mutation testing and trust
  purlin:init --gate <level>      passed, strong or signed, afterwards
  purlin:init --mutation          Turn mutation testing on without the question
  purlin:init --add <framework>   Add one more framework's entry to the tests setting
  purlin:init --update            Bring the project up to the installed plugin
  purlin:init --update --dry-run  List what the update would do, and write nothing
  purlin:anchor create <name>     A local anchor
  purlin:anchor add <url> --path <file>   Pin an anchor from another repository
  purlin:anchor sync [name|--all] [--check]   Advance a pin

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## What each command writes

| Command | Writes |
|---------|--------|
| `purlin:spec`, `purlin:spec-from-code` | `specs/<category>/<name>.md` |
| `purlin:build` | Code, test files with a marker comment above each test, and the commit carrying the changeset |
| `purlin:test` | Each suite's report under `.purlin/runtime/reports/`, which is not committed, and this operating system's section of `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes. `--remote` pushes the run branch `run/<branch>-<sha7>`, waits for the git host's run through `gh` on GitHub or `az` on Azure DevOps, pulls the runner's own section home under `.purlin/evidence/ci/<feature>.json`, and deletes the branch |
| `purlin:audit` | The same section, plus what the audit found under `audit`, in `.purlin/evidence/local/<feature>.json`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes |
| `purlin:sign` | `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, in a signed commit. Proof lines in a spec when the walk adds a case. The signed tag `signed/<version>` when the walk closes with every rule meeting the gate and every feature's evidence committed, on a signed commit carrying the evidence package `.purlin/evidence/package/<version>.json`, which a person pushes |
| `purlin:export` | `.purlin/evidence/package/<version>.json`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes |
| `purlin:init` | `.purlin/`, `specs/`, `specs/_anchors/`, `.purlin/config.json` with its `tests` setting, a block in `.gitignore`, `.purlin/evidence/` with its README, `purlin-report.html` at the project root, mutmut's config block where mutation testing is on, and the workflow when a proof names another operating system or the trust answer was no. It commits nothing. `--update` commits what it applied as `chore(update): migrate to <VERSION> (<ids>)` |
| `purlin:anchor` | `specs/_anchors/<name>.md` |
| `purlin:status` | `.purlin/report-data.js`, the data the dashboard reads, which git ignores |
| `purlin:drift` | Nothing |

## What each command shows at each gate

A command prints only what the gate asks for. Under `passed` no strength is measured, and no
level, no queue and no signature appears in the output; `purlin:audit` runs no breaks and ends
on `Audit: <n> strong, <n> weak. Nothing blocks at the gate passed.` Under `strong` the
strength where mutation testing is on, the strong cell, the level and the queue's hand checks
appear. Under `signed` the signed cell, the Signed column and the queue's signatures appear,
and `purlin:sign` writes the tag when every rule meets the gate. An audit `purlin:audit` wrote
counts at every gate.

`purlin:sign` under `passed` prints `sign: the gate is passed, which asks for no signature.`,
names what `purlin:init --gate strong` would add, and stops. `purlin:drift qa` reports only the
tests that changed.

## Path resolution

Every `references/`, `templates/`, `scripts/` and `agents/` path a skill or an agent names is
relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`: `references/purlin_commands.md` means
`${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`. The paths are written bare because the
reader is the agent, which resolves them once.

Everything else is relative to the project root: `specs/`, `.purlin/`, and the project's own
source and test files. A consumer project carries no `references/`, no `scripts/` and no
`templates/` of its own, so the two roots never collide over one path.

## Pending migrations

When `sync_status` carries the line `→ Run: purlin:init --update`, stop before doing the skill's
work, say so, and ask whether to run `purlin:init --update` now. A spec written against a
layout the installed plugin does not read is written against an answer it drops.

`purlin:init --update` names one migration per line with its id, what it does and the files it
counted, ends with `→ Run: purlin:init --update`, and asks before applying each one.
`purlin:init --update --dry-run` prints the same list, writes nothing and exits 1 while
anything is pending, which is what a preflight in CI runs.
