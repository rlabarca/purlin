# Purlin commands

The eleven skills below. Six are the core loop; the rest support it. This page is the one home
of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md` and the
README table carry the sentence in the Purpose column below, and nothing repeats it in its own
words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "sign off the release" reaches `purlin:sign`. Every
run, every audit and `purlin:status` end on the summary and `Left to do`, whose first line is
the next step and its command (`references/hard_gates.md`, "When a version is finished").

`purlin:test --remote` is the one command that pushes, and it pushes a run branch of its own,
never the branch you are on. Every other push is yours: the release run at `passed`, and the first
sign-off at `signed`, end on the line
`Nothing left to do. Push the tag to release it: git push origin <tag>`, and pushing it is your
act.

`purlin:test` runs the tests and writes what it saw, and `purlin:test --release` makes a release:
the evidence and the package committed at one commit, and at the gate `passed` the tag
`passed/<version>`. `purlin:audit` adds what the audit found, a tool nothing waits on. At the gate
`signed`, `purlin:sign` walks what a person has to look at and signs the package; the first
sign-off writes `signed/<version>`. `references/hard_gates.md` defines the two gates and the
release. **The folder an evidence file
sits in is its source**: `purlin:test` and `purlin:audit` write yours under
`.purlin/evidence/local/`, and commit it only with `--commit`; the CI job runs the same run
script and writes its section under `.purlin/evidence/ci/`, which it always commits. That job
is the workflow's to run and nobody types it. Both sources count at every gate, `signed`
included.

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs | A developer's agent, or product or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset | A developer, on every change. With no name it reads `sync_status` and names the specs with rules that have no passing test. It repairs a marker comment that is nearly right, and ends by running `purlin:test` |
| `purlin:test [feature ...] [--all] [--release [<version>]] [--arm-timeout <seconds>]` | Run the marked tests and print each rule's passed cell | A developer, constantly. Seconds; tests only. The first run in a project with no test command suggests one for each test tool it recognises and runs once you confirm it. It writes the evidence, commits it with `--commit`, and never pushes. With `--release`, on a release branch, it runs every test, commits the evidence and the package, and at the gate `passed` tags the release |
| `purlin:audit [feature ...] [--all] [--arm-timeout <seconds>]` | Run the tests, the breaks where mutation testing is on, and the AI audit, then write what it found into the evidence | A developer, any time, at either gate. It writes the evidence, commits it with `--commit`, and never pushes. Nothing waits on it |
| `purlin:sign [--release <version>]` | Walk what a person has to look at in a release, then sign its evidence package in a signed commit | Anyone with a key to sign with, at the gate `signed`, after `purlin:test --release`; the sign-off names them, and several people may sign. The first sign-off writes `signed/<version>` |
| `purlin:drift [role]` | Report what changed since your last pull, by role | Everyone, after a pull, a merge, a rebase, a checkout, a clone or a reset |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Set a project up for Purlin, and change the gate later | A developer, once. Three questions at most: the gate, at `signed` whether to break the code on purpose, and whether to commit what it wrote |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current | A developer, or product in Claude Code |
| `purlin:status [name]` | Show every rule's cells and what blocks the gate | Anyone with a checkout, any time; with a name, to see one spec's rules |
| `purlin:export` | Write the evidence package for a version, the data file a regulated system of record reviews | Anyone, any time, at any gate; `purlin:test --release` writes it too, into the release commit |
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
  purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature

  Releasing
  ──────
  purlin:test --release [<version>]  Run every test, commit the evidence and the package, and tag the release at the gate passed
  purlin:sign                     Walk the release's stops, then sign its evidence package
  purlin:sign --release <version>  The same, for the version named
  purlin:sign --show              The overview and every stop, asking nothing
  purlin:sign --answers <file>    The walk, with the answers a file gives

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
  purlin:init                     The gate, and mutation testing at signed
  purlin:init --gate <gate>       passed or signed, afterwards
  purlin:init --mutation          Turn mutation testing on without the question
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
| `purlin:test` | Each suite's report under `.purlin/runtime/reports/`, which is not committed, and this system's section of `.purlin/evidence/local/<feature>.json` and `.purlin/tests.md`. `--commit` makes two commits: the specs of the features run, the test files carrying their markers and `.purlin/config.json` as `purlin: specs, tests and settings for <feature>, ...`, then the evidence as `purlin: evidence at <sha7>`; it never pushes. On the first run it writes the `tests` entry you confirm into `.purlin/config.json`. `--remote` pushes the run branch `run/<branch>-<sha7>`, waits for the git host's run through `gh` on GitHub or `az` on Azure DevOps, pulls the runner's own section home under `.purlin/evidence/ci/<feature>.json`, and deletes the branch; what the runner runs is in `references/hard_gates.md`, "Where a runner runs". `--release` commits the evidence as `--commit` does, then `.purlin/evidence/package/<version>.json` alone as `purlin: evidence at <sha7>`, and at the gate `passed` the unsigned tag `passed/<version>` on that commit, which a person pushes; it refuses, and writes no package and no tag, as `references/hard_gates.md`, "The release", says |
| `purlin:audit` | The same section, plus what the audit found under `audit`, in `.purlin/evidence/local/<feature>.json`, which `--commit` commits in the same two commits; it never pushes |
| `purlin:sign` | `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, in a signed commit `sign(<version>): <signer email>`, once the signer answers yes. The first sign-off of a version also writes the signed tag `signed/<version>` on that commit, which a person pushes. `--show` writes nothing. The skill writes the answers it collects to `.purlin/runtime/signoff-answers.json`, which is not committed. At the gate `passed`, and on any refusal, it writes nothing |
| `purlin:export` | `.purlin/evidence/package/<version>.json`, which `--commit` commits as `purlin: evidence at <sha7>`; it never pushes |
| `purlin:init` | `.purlin/`, `specs/`, `.purlin/config.json` with an empty `tests` setting, a block in `.gitignore`, `.purlin/evidence/` with its README, `purlin-report.html` at the project root, mutmut's config block where mutation testing is on, and the workflow when a proof names another system and the git host is GitHub or Azure DevOps. It commits the files it wrote in one commit, `chore(init): set up Purlin at the gate <gate>`, once you agree or with `--yes`. `--update` commits what it applied as `chore(update): migrate to <VERSION> (<ids>)` |
| `purlin:anchor` | `specs/_anchors/<name>.md`, creating `specs/_anchors/` with the first anchor |
| `purlin:status` | `.purlin/report-data.js`, the data the dashboard reads, which git ignores |
| `purlin:drift` | Nothing. It reads only this checkout and never fetches |

## What each command shows at each gate

Every rule carries both cells at both gates, and the commands print the same at either, but for
three things. `Left to do` carries `to write a proof for` at `signed` alone. The line under a
finished project names `purlin:test --release` at `passed`, and `purlin:test --release, then
purlin:sign` at `signed`. `purlin:sign` signs only at `signed`. The summary adds what the audit
found, and the `Strong` column shows, only where the audit has read a rule; the audit prints its
one line, `AI audit: <n> rules read, <s> strong, <w> weak.`, then the summary. The breaks run
wherever `mutation_engine` is set.

`purlin:drift qa` prints the lines of `Left to do` that stop a release beside what changed. Every
view of `purlin:drift` names each number a spec
writes twice and which line moves, and says how old this checkout's copy of the default branch
is; it never fetches.

## Exit codes

| Command | 0 | 1 | 2 |
|---------|---|---|---|
| `scripts/run/purlin_run.py --test`, `--audit` | everything asked happened | a tied test failed or did not run; evidence is missing; a marker names nothing a spec has; a spec under `specs/` writes a number twice or holds a line left from a merge conflict, after every test ran; no settings file; the settings file cannot be read; a project set up by 0.9.5 and not upgraded; no test command; for `--release`, the release was refused or git could not write the tag. A weak or unaudited rule never exits 1 | a bad command line |
| `scripts/run/purlin_run.py --ci` | the tests tied to the proofs tagged for this runner's system passed | one of those failed or could not run, and nothing else | a bad command line |
| `scripts/review/sign.py` | signed, stopped, answered no, or the gate is `passed` | a refusal: work not committed, no package committed for the version, the package describing an earlier commit, a rule that does not pass, the branch's copy on the host holding commits HEAD lacks, the signer has already signed, no version, or a stop with no answer in the answers file; no key; the commit was not made; git could not write the tag; the settings file cannot be read | a bad command line |
| `scripts/export/package.py` | written, or the check matched | the check did not match; the project states no version; the package could not be written; the settings file cannot be read | a bad command line |
| `scripts/review/ai_audit.py` | a rule was printed | the rule is not in the project; the settings file cannot be read | a bad command line |
| `scripts/init/scaffold.py` | set up | the settings file cannot be read | a bad command line, not a git repository, or no such project root |
| `scripts/init/update.py` | nothing pending, or applied | the settings file cannot be read | no project |
| `scripts/mcp/purlin/markers.py --near-misses` | always | never | a bad command line |

A run that stops before running anything writes nothing and names the command that fixes it:

- `No .purlin/config.json here, so nothing ran. Run purlin:init to write it.`
- `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`
- `This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.`
- `No test command is set in .purlin/config.json, so nothing ran.`, when it recognises a test
  tool, then for each tool it recognises `Suggested for <name>: <run>` followed by what that
  tool needs added where it needs something, then
  `Suggested tests setting: <the entries as one JSON array on one line>`.
- `No test command is set and no test tool Purlin knows was found, so nothing ran. The agent reads the project and proposes a command for you to confirm.`
- `purlin:test --remote waits for the run with the GitHub CLI, gh, which is not installed, so nothing was pushed. Install gh, then run purlin:test --remote again.`
- `purlin:test --remote waits for the run with the Azure CLI, az, which is not installed, so nothing was pushed. Install az with its azure-devops extension, then run purlin:test --remote again.`

A run names each rule where it reports the problem:

- `<feature> <RULE-N> fails: <file>::<test>. Run purlin:build <feature>.`
- `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`,
  where some of the rule's proofs have no test.
- `<feature> <RULE-N> has no test. Run purlin:build <feature>.`, where none of them has one.
- `<file>:<line> names <feature> <ID>, which no spec has. Correct the comment, or run purlin:build to repair it.`

`scripts/review/ai_audit.py --rule` names a rule no spec has:
`<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`

`purlin:test --release` refuses a release with one line and exits 1, writing no package and no
tag; `references/hard_gates.md`, "The release", gives each line in the order it is checked.
`purlin:sign` refuses a sign-off the same way, and writes nothing:

- `Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`, exit 0.
- `No sign-off: no evidence package for <version> is committed at <sha7>. Run purlin:test --release.`
- `No sign-off: the evidence package for <version> describes <sha7>, and <sha7> has changed since. Run purlin:test --release.`
- `<signer email> has already signed <version> over this package; nothing was written.`

`markers.py --near-misses --project-root <dir>` is what `purlin:build` runs to find a marker
comment that is nearly right. It prints one JSON array of `{"file", "line", "text", "fix",
"why"}`: `purlin` misspelled by one letter or in capitals, no space after the colon, a
`purlin:` comment that cannot be read, and a feature name or a `PROOF`/`RULE` id one edit from
one that exists. Where the nearest id is a rule with exactly one proof, the fix names that
proof; a rule with two or more proofs gives no near miss. A test run does not look for them.

## Path resolution

Every `references/`, `templates/`, `scripts/` and `agents/` path a skill or an agent names is
relative to the plugin root, `${CLAUDE_PLUGIN_ROOT}`: `references/purlin_commands.md` means
`${CLAUDE_PLUGIN_ROOT}/references/purlin_commands.md`. The paths are written bare because the
reader is the agent, which resolves them once.

Every Purlin script a skill runs is started as
`sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" "${CLAUDE_PLUGIN_ROOT}/scripts/<path>" <args>`,
which finds Python 3 the way the plugin's server does, `py -3` on Windows included.

Everything else is relative to the project root: `specs/`, `.purlin/`, and the project's own
source and test files. A consumer project carries no `references/`, no `scripts/` and no
`templates/` of its own, so the two roots never collide over one path.

## Pending migrations

When `sync_status` carries the line `→ Run: purlin:init --update`, stop before doing the skill's
work, say so, and ask whether to run `purlin:init --update` now. A spec written against a
layout the installed plugin does not read is written against an answer it drops.

`purlin:init --update` names one migration per line with its id, what it does and the files it
counted, ends with `→ Run: purlin:init --update`, and asks before applying each one.
