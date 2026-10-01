# Purlin commands

The ten skills below. Six are the core loop; the rest support it. This page is the one home
of the skill one-liners: the frontmatter `description` of `skills/<name>/SKILL.md` and the
README table carry the sentence in the Purpose column below, and nothing repeats it in its own
words.

Plain language reaches every command. The syntax here is canonical, never required: "run the
tests" reaches `purlin:test` and "sign it off" reaches `purlin:sign`. Every run, every audit and
`purlin:status` end on the summary and `Left to do`, whose first line is the next step and its
command (`references/evidence_and_signoff.md`, "What is left to do").

No Purlin command pushes. Every push is yours: a sign-off ends on a line starting `Push`, with
the `git push origin` command, and pushing is your act.

`purlin:test` runs the tests and writes what it saw. Which tests a run starts:

- `purlin:test`, with or without a feature named, never starts the test of a slow proof, one
  tagged `@slow`. It prints `Left out <n> slow proofs`, naming each, and keeps the result a slow
  proof already has while that result still counts.
- `purlin:test --all` starts every test, slow ones included.
- A test that also carries the comment of a proof that is not slow is started all the same. So
  is a slow test a suite's command cannot leave out, which the run names;
  `references/supported_frameworks.md` says how each test tool leaves a test out.

`purlin:audit` runs the tests the same way and adds what the audit found, a tool nothing waits
on.

The hand-off is `purlin:test --all --commit`, and the project's own run for the proofs tagged
for another system (`references/evidence_and_signoff.md`, "A run on another system"). That run
is `scripts/run/purlin_run.py --ci --commit`, which a pipeline runs and nobody types.

`purlin:sign` builds the evidence package from the committed evidence, walks its hand checks
with a person and signs it; the first sign-off of a version writes `signed/<version>`.
`references/evidence_and_signoff.md` defines the two facts and the sign-off.

**The folder an evidence file sits in is its source**: `purlin:test` and `purlin:audit` write
yours under `.purlin/evidence/local/`, and commit it only with `--commit`; the project's own run
on another system writes its section under `.purlin/evidence/ci/`. Both sources count.

Every Purlin tool call, `sync_status`, `drift` and `purlin_config`, names `project_root`, the top
folder of the git checkout you are working in. A call that names none is refused:
`sync_status needs project_root: pass the top folder of the git checkout you are working in.`

## Core

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:spec <name>` | Turn a requirement in any form into rules and proofs | A developer's agent, or product or QA in Claude Code, at intake and whenever a rule turns out to be wrong |
| `purlin:build [name]` | Load a spec's rules, write the code and the marked tests, commit the changeset | A developer, on every change. With no name it reads `sync_status` and names the specs with rules that have no passing test. It repairs a marker comment that is nearly right, corrects a test whose proof was reworded, and ends by running `purlin:test` |
| `purlin:test [feature ...] [--all] [--commit] [--arm-timeout <seconds>]` | Run the marked tests and print each rule's passed cell | A developer, constantly. Seconds; tests only, and never a slow proof's without `--all`. The first run in a project with no test command suggests one for each test tool it recognises and runs once you confirm it. It writes the evidence, commits it with `--commit`, and never pushes. `purlin:test --all --commit` is the hand-off to a sign-off |
| `purlin:audit [feature ...] [--all] [--commit] [--arm-timeout <seconds>]` | Run the tests, the heuristic spot tests, one planted bug per proof and the model's reading, then write what it found into the evidence | A developer, by hand, any time. It writes the evidence, commits it with `--commit`, and never pushes. Nothing waits on it |
| `purlin:sign [--version <version>]` | Build the evidence package from the committed evidence, walk its hand checks with a person, then sign it in a signed commit | Anyone with a key to sign with, in any project, at any time, after the hand-off; the sign-off names them, and several people may sign. The first sign-off of a version writes `signed/<version>` |
| `purlin:drift` | Report what changed since your last pull | Everyone, after a pull, a merge, a rebase, a checkout, a clone or a reset |

## Supporting

| Command | Purpose | Who runs it, and when |
|---------|---------|------------------------|
| `purlin:init` | Set a project up for Purlin | A developer, once. One question: whether to commit what it wrote |
| `purlin:anchor <cmd>` | Create anchors, pull them from another repository, and keep the pins current | A developer, or product in Claude Code |
| `purlin:status [name]` | Show the two facts, every rule's cells and what is left to do | Anyone with a checkout, any time; with a name, to see one spec's rules. After merging work from a worktree, in the main checkout |
| `purlin:spec-from-code [dir]` | Read an existing codebase and write the specs it already implies | A developer, once, on a codebase that has no specs. Optional |

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
  purlin:test --all               The same, for every feature, slow proofs included
  purlin:test --commit            The same, then commit the work and the evidence
  purlin:test --all --commit      The hand-off: every feature, and the results committed

  Proving
  ──────
  purlin:audit [feature ...]      Tests, spot tests, planted bugs and the model's reading, into the evidence
  purlin:audit --all              The same, reading every passing rule again
  purlin:audit --commit           The same, then commit the work and the evidence
  purlin:audit --arm-timeout <seconds>  Give each suite, and each planted bug's test run, longer

  Signing
  ──────
  purlin:sign                     Build the evidence package, walk its hand checks, then sign it
  purlin:sign --version <version>  The same, for the version named
  purlin:sign --show              The overview and every stop, asking nothing
  purlin:sign --answers <file>    The walk, with the answers a file gives
  purlin:sign --check <file>      Check a package file against its fingerprint

  Reporting
  ──────
  purlin:status                   The two facts, every rule's cells, the summary and Left to do
  purlin:status <name>            One spec: its rules and their cells
  purlin:drift                    What changed since your last pull
  purlin:drift --since <N|date>   A window other than since your last pull

  Project
  ──────
  purlin:init                     Set the project up
  purlin:init --update            Bring a 0.9.5 project up to the installed plugin
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
| `purlin:test` | Each suite's report under `.purlin/runtime/reports/`, which is not committed, and this system's section of `.purlin/evidence/local/<feature>.json`. `--commit` makes two commits: the specs of the features run, the test files carrying their markers and `.purlin/config.json` as `purlin: specs, tests and settings for <feature>, ...`, then the evidence as `purlin: evidence at <sha7>`; it never pushes. On the first run it writes the `tests` entry you confirm into `.purlin/config.json`. |
| `purlin:audit` | The same section, plus what the audit found under `audit`, in `.purlin/evidence/local/<feature>.json`, which `--commit` commits in the same two commits; it never pushes. What the model cost goes to `.purlin/runtime/audit_run.json`, which is not committed. A planted bug is made in a copy of the project and nowhere else |
| `purlin:sign` | Once the signer answers yes, one signed commit `sign(<version>): <signer email>`. The first sign-off of a version carries `.purlin/evidence/package/<version>.json` and `.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, and writes the signed tag `signed/<version>` on that commit, which a person pushes; a later sign-off adds its own file alone. `--show` and `--check` write nothing. The skill writes the answers it collects to `.purlin/runtime/signoff-answers.json`, which is not committed. On any refusal it writes nothing |
| `purlin:init` | `.purlin/`, `specs/`, `.purlin/config.json` holding `version` and an empty `tests` setting, a block in `.gitignore`, `.purlin/evidence/` with its README, and `purlin-report.html` at the project root. It commits the files it wrote in one commit, `chore(init): set up Purlin`, once you agree or with `--yes`. `--update` commits what it applied as `chore(update): migrate to <VERSION> (<ids>)` |
| `purlin:anchor` | `specs/_anchors/<name>.md`, creating `specs/_anchors/` with the first anchor |
| `purlin:status` | `.purlin/report-data.js`, the data the dashboard reads, and `purlin-report.html`, its page, where the project's copy is missing or differs from the plugin's; git ignores both. `purlin:test`, `purlin:audit` and `purlin:sign` write the same two when they finish |
| `purlin:drift` | Nothing. It reads only this checkout and never fetches |

## Exit codes

| Command | 0 | 1 | 2 |
|---------|---|---|---|
| `scripts/run/purlin_run.py --test`, `--audit` | everything asked happened | a tied test failed or did not run; evidence is missing; a marker names nothing a spec has; a spec under `specs/` writes a number twice or holds a line left from a merge conflict, after every test ran; no settings file; the settings file cannot be read; a project set up by 0.9.5 and not upgraded; no test command; for `--audit`, a file of the project changed while a bug was planted. A weak or unaudited rule never exits 1, and neither does a test comment to correct | a bad command line |
| `scripts/run/purlin_run.py --ci` | the tests tied to the proofs tagged for this machine's system passed | one of those failed or could not run, and nothing else | a bad command line |
| `scripts/review/sign.py` | signed, shown, checked and matching, stopped, or answered no | a refusal: tracked files changed and not committed, evidence not committed, no version, the version's tag on a commit this checkout does not hold or on other code, results not taken on this version of the code, results taken while files were changed and not committed, a rule with no test, a rule that does not pass, the branch's copy on the host holding commits HEAD lacks, the signer has already signed, or a stop with no answer in the answers file; no key; the package was not written; the commit was not made; git could not write the tag; `--check` did not match | a bad command line |
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

A run names each rule where it reports the problem:

- `<feature> <RULE-N> fails: <file>::<test>. Run purlin:build <feature>.`
- `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`,
  where some of the rule's proofs have no test.
- `<feature> <RULE-N> has no test. Run purlin:build <feature>.`, where none of them has one.
- `<file>:<line> names <feature> <ID>, which no spec has. Correct the comment, or run purlin:build to repair it.`

`scripts/review/ai_audit.py --rule` names a rule no spec has:
`<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.`

`purlin:sign` refuses a sign-off with one line beginning `No sign-off:` or `No version:`, exits 1
and writes nothing; `skills/sign/SKILL.md` gives each line in the order it is checked.

`scripts/mcp/purlin/wording.py [--project-root <dir>] [--file <path> ...]` is what `purlin:build`
runs to list the test comments to correct. It prints one line per comment, then
`<n> test comments to correct.`, `1 test comment to correct.` or `No test comment to correct.`,
and exits 0.

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
