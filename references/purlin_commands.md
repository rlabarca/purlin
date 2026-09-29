# Purlin commands

The eleven skills below. Six are the core loop; the rest support it. This page is the one home
of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md` and the
README table carry the sentence in the Purpose column below, and nothing repeats it in its own
words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "what is waiting on a person" reaches `purlin:sign`. Every
run, every audit and `purlin:status` end on the summary and `Left to do`, whose first line is
the next step and its command (`references/hard_gates.md`, "When a version is finished").

`purlin:test --remote` is the one command that pushes, and it pushes a run branch of its own,
never the branch you are on. Every other push is yours: at the gate `signed`, `purlin:sign` ends
on the line `Nothing left to do. Push the tag to release it: git push origin signed/<version>`,
and pushing it is your act.

Three commands carry the three steps: `purlin:test` runs the tests and writes what it saw,
`purlin:audit` adds what the audit found, and `purlin:sign` records a person's signature.
`references/hard_gates.md` says which steps a project asks for. **The folder an evidence file
sits in is its source**: `purlin:test` and `purlin:audit` write yours under
`.purlin/evidence/local/`, and commit it only with `--commit`; the CI job runs the same run
script in an arm of its own and writes its section under `.purlin/evidence/ci/`, which it
always commits. That arm is the workflow's to pass and nobody types it. Both sources count at
every gate, `signed` included.

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs | A developer's agent, or product or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset | A developer, on every change. With no name it reads `sync_status` and names the specs with rules that have no passing test. It repairs a marker comment that is nearly right, and ends by running `purlin:test` |
| `purlin:test [feature ...] [--all]` | Run the marked tests and print each rule's passed cell | A developer, constantly. Seconds; tests only. The first run in a project with no test command suggests one and runs once you confirm it. It writes the evidence, commits it with `--commit`, and never pushes |
| `purlin:audit [feature ...] [--all]` | Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence | A developer, any time. It writes the evidence, commits it with `--commit`, and never pushes |
| `purlin:sign [feature] [RULE-N ...] [--all]` | Sign a rule, a feature or every rule that waits for a person, as a signed commit | Anyone with a key to sign with; the signature names them. With no argument it walks the rules waiting for someone to test by hand or to sign. It works at every gate |
| `purlin:drift [role]` | Report what changed since your last pull, by role | Everyone, after a pull, a merge, a rebase, a checkout, a clone or a reset |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Set a project up for Purlin, and change the gate later | A developer, once. Two questions at most: the gate, and at `strong` and `signed` whether to break the code on purpose |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current | A developer, or product in Claude Code |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate | Anyone with a checkout, any time; with a name, to see one spec's rules |
| `purlin:export` | Write the evidence package for a version, the data file a regulated system of record reviews | Anyone, any time, at any gate; at the gate `signed`, `purlin:sign` writes it too, into the commit the tag names |
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
  purlin:test --commit            The same, then commit the work and the evidence
  purlin:test --remote            Let the git host's runner do the run

  Proving
  ──────
  purlin:audit [feature ...]      Tests, breaks and the AI audit, into the evidence
  purlin:audit --all              The same, reading every rule again
  purlin:audit --commit           The same, then commit the work and the evidence
  purlin:sign                     Walk the rules waiting for a person, then write the tag at the gate signed
  purlin:sign --release <name>    Name the tag something other than the version
  purlin:sign <feature> [RULE-N ...]  Sign, as a signed commit
  purlin:sign --all               Sign every rule waiting to be tested by hand or signed
  purlin:sign <feature> RULE-N --note "<text>"  Sign a hand check with what you saw

  Reporting
  ──────
  purlin:status                   Every rule's cells, the summary and Left to do
  purlin:status <name>            One spec: its rules and their cells
  purlin:drift [pm|eng|qa]        What changed since your last pull
  purlin:drift --since <N|date>   A window other than since your last pull
  purlin:export                   The evidence package for the version
  purlin:export --release <name>  The same, for another version name
  purlin:export --commit          The same, then commit the package
  purlin:export --check <file>    Check a package against its fingerprint

  Project
  ──────
  purlin:init                     The gate, and mutation testing at strong and signed
  purlin:init --gate <gate>       passed, strong or signed, afterwards
  purlin:init --mutation          Turn mutation testing on without the question
  purlin:init --add <framework>   Add one more framework's entry to the tests setting
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
| `purlin:build` | Code, test files with a marker comment above each test, the repairs to marker comments it asked about, and the commit carrying the changeset |
| `purlin:test` | Each suite's report under `.purlin/runtime/reports/`, which is not committed, and this system's section of `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`. `--commit` makes two commits: the specs of the features run, the test files carrying their markers and `.purlin/config.json` as `purlin: specs, tests and settings for <feature>, ...`, then the evidence as `purlin: evidence at <sha7>`; it never pushes. On the first run it writes the `tests` entry you confirm into `.purlin/config.json`. `--remote` pushes the run branch `run/<branch>-<sha7>`, waits for the git host's run through `gh` on GitHub or `az` on Azure DevOps, pulls the runner's own section home under `.purlin/evidence/ci/<feature>.json`, and deletes the branch |
| `purlin:audit` | The same section, plus what the audit found under `audit`, in `.purlin/evidence/local/<feature>.json`, which `--commit` commits in the same two commits; it never pushes |
| `purlin:sign` | `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, in a signed commit, one file per feature an anchor's rule applies to. Proof lines in a spec when the walk adds a case. `VERSION` when you name the version and agree to write it. At the gate `signed` alone, the signed tag `signed/<version>` when nothing is left to do and every result came from committed work, on a signed commit carrying the evidence package `.purlin/evidence/package/<version>.json`, which a person pushes |
| `purlin:export` | `.purlin/evidence/package/<version>.json`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes |
| `purlin:init` | `.purlin/`, `specs/`, `.purlin/config.json` with an empty `tests` setting, a block in `.gitignore`, `.purlin/evidence/` with its README, `purlin-report.html` at the project root, mutmut's config block where mutation testing is on, and the workflow when a proof names another system and the git host is GitHub or Azure DevOps. It commits nothing. `--update` commits what it applied as `chore(update): migrate to <VERSION> (<ids>)` |
| `purlin:anchor` | `specs/_anchors/<name>.md`, creating `specs/_anchors/` with the first anchor |
| `purlin:status` | `.purlin/report-data.js`, the data the dashboard reads, which git ignores |
| `purlin:drift` | Nothing |

## What each command shows at each gate

A command prints only what the gate asks for. The summary names the steps up to the gate and
no others, and `Left to do` carries only the kinds that apply at it. Under `passed` no strength
is measured and `purlin:audit` runs no breaks; the audit prints its one line,
`AI audit: <n> rules read, <s> strong, <w> weak.`, then the summary. Under `strong` the strength
where mutation testing is on and the strong cell appear. Under `signed` the signed cell and the
Signed column appear, and `purlin:sign` writes the tag when nothing is left to do. `purlin:sign`
works at every gate: a hand check is signed at any of them. An audit `purlin:audit` wrote
counts at every gate.

`purlin:drift qa` prints the `to test by hand` and `to sign` lines of `Left to do` beside what
changed.

## Exit codes

| Command | 0 | 1 | 2 |
|---------|---|---|---|
| `scripts/run/purlin_run.py --test`, `--audit` | everything asked happened | a tied test failed or did not run; evidence is missing; a marker names nothing a spec has; no settings file; a project set up by 0.9.5 and not upgraded; no test command; for `--audit` at `strong` and `signed`, a rule read is weak or could not be audited | a bad command line |
| `scripts/run/purlin_run.py --ci` | the tests passed | a test failed or could not run, and nothing else | a bad command line |
| `scripts/review/sign.py` | written and committed, or the walk closed | no key, or the commit was not made | a bad command line |
| `scripts/init/update.py` | nothing pending, or applied | never | no project |
| `scripts/mcp/purlin/markers.py --near-misses` | always | never | a bad command line |

A run that stops before running anything writes nothing and names the command that fixes it:

- `No .purlin/config.json here, so nothing ran. Run purlin:init to write it.`
- `This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.`
- `No test command is set in .purlin/config.json, so nothing ran.`, then
  `Suggested for <name>: <run>` and `Suggested entry: <one-line JSON>`, when it recognises the
  test tool.
- `No test command is set in .purlin/config.json, and no test tool Purlin knows was found, so nothing ran. Run purlin:test to have one proposed.`

A run names each rule where it reports the problem:

- `<feature> <RULE-N> fails: <file>::<test>. Run purlin:build <feature>.`
- `<feature> <RULE-N> has no test. Run purlin:build <feature>.`
- `<file>:<line> names <feature> <ID>, which no spec has. Correct the comment, or run purlin:build to repair it.`

`markers.py --near-misses --project-root <dir>` is what `purlin:build` runs to find a marker
comment that is nearly right. It prints one JSON array of `{"file", "line", "text", "fix",
"why"}`: `purlin` misspelled by one letter or in capitals, no space after the colon, a
`purlin:` comment that cannot be read, and a feature name or a `PROOF`/`RULE` id one edit from
one that exists. A test run does not look for them.

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
