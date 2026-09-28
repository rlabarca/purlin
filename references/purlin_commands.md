# Purlin commands

The skills below, and no permission system. Six are the core loop; the rest support it. This
page is the one home of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md` and
the README table carry the sentence in the Purpose column below, and nothing repeats it in its
own words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "what is waiting on a person" reaches `purlin:sign`. Every command ends
by naming the next step, computed from the cells it found.

Nothing here pushes on its own except `purlin:test --remote`, which a person asked for by
name and which pushes a run branch of its own, never the branch you are on. Everywhere else a
push is a person's act, free, to any branch: a command commits, prints `Run: git push` and
stops. No command opens a pull request, and nothing runs at push time.

Three commands carry the three evidence levels: `purlin:test` runs level 1 and writes what it
saw, `purlin:audit` runs level 2 and reports, and `purlin:sign` is level 3.
`references/hard_gates.md` says which levels a project asks for. **The folder an evidence file
sits in is its source**: `purlin:test` and `purlin:audit` write yours under
`.purlin/evidence/local/`, and commit it only with `--commit`; the CI job runs the same run
script in an arm of its own and writes its section under `.purlin/evidence/ci/`, which it
always commits. That arm is the workflow's to pass and nobody types it. Both
sources count at every gate, `signed` included; the one setting that asks for a `ci` run
before a signature is `trust: remote`.

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs | An engineer's agent, or a PM or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Load a spec's rules, write the code and the tagged tests, commit the changeset | An engineer, on every change. With no name it reads the board |
| `purlin:test [feature]` | Run the tagged tests and print each rule's passed cell | An engineer, constantly. Seconds; tests only. It writes the evidence, commits it with `--commit`, and never pushes |
| `purlin:audit [feature]` | Run the tests and the breaks, then write the audit into the evidence | An engineer locally, any time. It writes the evidence, commits it with `--commit`, and never pushes |
| `purlin:sign [feature] [RULE-N]` | Walk the queue, or sign a rule, a feature or a batch as a signed commit | Anyone with commit signing set up; the signature names them. With no argument it walks the queue |
| `purlin:drift [role]` | Report what changed since your last pull, by role | Everyone, after a pull, a merge, a rebase or a checkout |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Set a project up for Purlin, and change the gate later | An engineer, once. One question |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current | An engineer, or a PM in Claude Code |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate | Anyone with a checkout, any time; with a name, to see one spec's rules |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies | An engineer, once, on a codebase that predates Purlin |

## Syntax

```
Purlin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Specifying
  ──────
  purlin:spec <name>              Scaffold or edit a feature spec
  purlin:spec-from-code [dir]     Reverse-engineer specs from existing code

  Building
  ──────
  purlin:build [name]             Implement a spec's rules and their tests
  purlin:test [feature ...]       Run the tagged tests and write the evidence
  purlin:test --commit            The same, then commit the evidence
  purlin:test --remote            Let the git host's runner do the run

  Proving
  ──────
  purlin:audit [feature ...]      Tests, breaks, and what they found, into the evidence
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

  Project
  ──────
  purlin:init                     One question: what a version must reach
  purlin:init --gate <level>      passed, strong or signed, afterwards
  purlin:init --add <language>    Wire another language's test framework
  purlin:init --update            Bring the project up to the installed plugin
  purlin:anchor create <name>     A local anchor
  purlin:anchor add <url> --path <file>   Pin an anchor from another repository
  purlin:anchor sync [name|--all] [--check]   Advance a pin

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## What each command writes

| Command | Writes |
|---------|--------|
| `purlin:spec`, `purlin:spec-from-code` | `specs/<category>/<name>.md` |
| `purlin:build` | Code, test files, and the commit carrying the changeset |
| `purlin:test` | `.purlin/runtime/proofs/`, which is not committed, and this operating system's section of `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes. `--remote` pushes the run branch `run/<branch>-<sha7>`, waits for the git host's run through `gh` on GitHub or `az` on Azure DevOps, pulls the runner's own section home under `.purlin/evidence/ci/<feature>.json`, and deletes the branch |
| `purlin:audit` | The same section, plus what the audit found under `audit`, in `.purlin/evidence/local/<feature>.json`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes |
| `purlin:sign` | `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, in a signed commit. Proof lines in a spec when the walk adds a case. The signed tag `signed/<version>` when the walk closes with every rule meeting the gate and every feature's evidence committed, which a person pushes |
| `purlin:init` | `.purlin/`, `specs/`, the test wiring, and the workflow when a proof names another operating system or the trust answer was no |
| `purlin:anchor` | `specs/_anchors/<name>.md` |
| `purlin:status`, `purlin:drift` | Nothing |

## What each command shows at each gate

A command prints only what the gate asks for. Under `passed` there is no strength, no level, no
queue and no signature anywhere in the output, and `purlin:audit` runs no breaks. Under
`strong` the strength, the strong cell, the level and the queue's hand checks appear. Under
`signed` the signed cell, the Signed column and the queue's signatures appear, and `purlin:sign`
writes the tag when every rule meets the gate. An audit `purlin:audit` wrote counts at every
gate.

`purlin:sign` under `passed` says the gate is `passed`, names what `purlin:init --gate strong`
would add, and stops. `purlin:drift qa` reports only the tests that changed.

## Path resolution

Every `references/`, `templates/`, `scripts/` and `agents/` path a skill or an agent names is
relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`: `references/purlin_commands.md` means
`${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`. The paths are written bare because the
reader is the agent, which resolves them once.

Everything else is relative to the project root: `specs/`, `.purlin/`, and the
project's own source and test files. A consumer project carries no `references/`, no `scripts/`
and no `templates/` of its own, so the two roots never collide over one path. A shell script
that needs the same answer outside a skill reads `${CLAUDE_PLUGIN_ROOT}` where it is set and
otherwise looks in the two install locations `docs/getting-started.md` names.

## Pending migrations

When `sync_status` opens with a pending-migrations advisory, stop before doing the skill's work,
print the advisory and its directive, and ask whether to run `purlin:init --update` now. A spec
written against a reading the installed plugin has moved on from is written against an answer
the next release drops.

The advisory names one migration per line with its count and the files it counted, and ends with
`→ Run: purlin:init --update`. `purlin:init --update --check` prints the same list as JSON and
writes nothing, which is what a preflight in CI runs.
