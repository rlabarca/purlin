# Raising the gate, and upgrading

For the developer who set the project up, when the team grows, the obligations change, or a new
Purlin release lands.

Two things change over a project's life and neither needs a new setup: the gate, which says what
must be true of every rule before a version is finished, and the release of Purlin the project is
set up for. `purlin:init` changes both, with `--gate` and `--update`.

## Changing the gate

```
purlin:init --gate passed
purlin:init --gate signed
```

The gate is two answers. `passed`: every rule's tests pass on the evidence committed at the
release commit. `signed`: the same, and at least one person signs the evidence package. Every
rule carries two cells at either gate, `passed` and `strong`; the gate reads the first, and the
second says what the audit found, where it ran. [hard_gates.md](../references/hard_gates.md) is
the one home of the gate.

Changing the gate writes the setting and keeps every file an earlier run wrote: the evidence, the
packages and the sign-offs stay where they are. A team can drop to `passed` for a spike and come
back to `signed` without losing a file.

Raised from `passed` to `signed`, with the commit question answered `y`:

```
Gate signed. Suites pytest.
No git host found.
kept .purlin/
kept specs/
wrote .purlin/config.json
kept .gitignore
kept .purlin/evidence/
kept .purlin/evidence/README.md
kept purlin-report.html
skipped the runner file (every proof runs on this operating system, so nothing has to run remotely)
Commit the files setup wrote? [y/N] y
Committed 35a89f7, the files setup wrote:
  .purlin/config.json

3 rules. 3 pass their tests.
Nothing left to do. To release a version: purlin:test --release, then purlin:sign
```

Setup names every path it wrote, kept, copied or skipped, one per line. Once it wrote a file git
does not ignore it asks `Commit the files setup wrote? [y/N]`: an empty answer or anything but `y`
or `yes` commits nothing, and a yes commits exactly those files as
`chore(init): set up Purlin at the gate <gate>`. It ends on the summary and `Left to do` of the
project as it now is.

| Flag | What it does |
|------|--------------|
| `--gate <gate>` | sets the gate, `passed` or `signed`, without asking |
| `--mutation` | turns mutation testing on without asking, at either gate |
| `--yes` | takes the default answer to every question, so mutation testing stays off, and commits the files setup wrote |
| `--update` | brings a project an older Purlin set up onto the installed one |

## What each gate writes

**At either gate.** `.purlin/config.json` with exactly six keys: `version`, `gate`,
`mutation_engine`, `audit_parallel` at 4, `tests` and `ci`. A first setup writes `tests` empty,
and the first test run suggests an entry for each test tool it recognises; a `tests` setting the
project already carries is kept. Setup also writes `specs/`, `.purlin/evidence/` with its README,
a block in `.gitignore` naming `/purlin-report.html` and `.purlin/runtime/`, and the dashboard
page, copied to `purlin-report.html`.

**The audit and mutation testing.** Both are tools you run with `purlin:audit`, at either gate,
and nothing waits on them. What the audit finds is part of the evidence: `purlin:audit` writes it
into each feature's `.purlin/evidence/local/<feature>.json`, and `--commit` commits it. A rule
the audit found weak is left to do as `to strengthen`, which never stops a release. Setup asks
`Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N]`
only at `signed`, where a person reads the audit at the sign-off, only where an engine that runs
on this operating system exists for a framework the project carries, and only while the settings
name no `mutation_engine`. The answer is kept, so changing the gate later does not ask again;
`--mutation` turns it on at either gate. With it on, setup writes the engine's configuration:

```
Gate signed. Suites pytest.
No git host found.
kept .purlin/
kept specs/
wrote .purlin/config.json
wrote setup.cfg
wrote .gitignore
```

**At `passed`.** `purlin:test --release` runs every test, commits the evidence and the evidence
package, and tags the release `passed/<version>`, unsigned. A rule with a `@manual` proof is
listed in the package as not checked.

**At `signed`.** A rule with no proof is left to do as a rule to write a proof for, with `purlin:spec`. The release run
commits the package and writes no tag; `purlin:sign` walks it with a person, checks for a key to
sign with and prints the commands that set one up when there is none. The first sign-off writes
the tag `signed/<version>`, and a person pushes it.
[review-and-signing.md](review-and-signing.md#the-tag) has the tags.

## A remote runner, at any gate

Setup writes a runner file for one reason, whatever the gate: a proof in `specs/` is tagged
`@env` for an operating system this machine is not. Before it writes one it checks two things, that
a git remote exists and that its URL names GitHub or Azure DevOps, and it names the git host's
program, `gh` or `az`, as installed or not. The file carries one job for each operating system a
proof is tagged `@env` for that this machine is not, triggers on a push to a `run/*` branch and on
a push of a `signed/*` tag, and ends with the test run. A project on GitHub with one proof tagged
`@env(windows)`, set up on a Mac:

```
gh is installed, so a remote run can be watched from here.
A remote runner is written because:
  A proof in specs/ is tagged @env for Windows, which this machine is not, so only a runner can prove it.
wrote .github/workflows/purlin.yml
  it runs on windows-latest, the systems a proof in specs/ is tagged @env for that this machine is not.
  it runs on a push to a run/* branch and on a push of a signed/* tag.
```

On Azure DevOps the file is `purlin.azure-pipelines.yml` at the root. With no such proof setup
prints `skipped the runner file (every proof runs on this operating system, so nothing has to run
remotely)`, and with such a proof and no remote,
`skipped the runner file (there is no git remote, so there is no runner to read it)`.
[running-and-evidence.md](running-and-evidence.md) has the remote run in full.

## Upgrading to a new Purlin

```
purlin:init --update
```

Run it after the plugin updates. Its migrations read the layout Purlin 0.9.5 left and land the
project on this release's. [RELEASE_NOTES.md](../RELEASE_NOTES.md) says what an upgrade from 0.9.5
changes.

While a migration is pending, `purlin:status` carries `→ Run: purlin:init --update` above the
summary, and a test run stops, writes nothing and exits 1:

```
This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.
```

## What the update does

The update first prints the pending list, `<n> migrations pending in <root>:`, then each
migration's id and what it does, with the files it touches under it. Then it asks before each one,
`Apply <id>, which will <what it does>? [y/N]`. Any answer but `y` or `yes` declines it, an empty
one included; a declined migration is reported as `skipped <id>` and stays pending, and the others
still run. The migrations run in this order, because the tags are rewritten before the runner file
is written from them:

| Migration | What it changes |
|-----------|-----------------|
| `design-refs` | removes each spec's Figma `> Source:` with its `> Pinned:`, and its `> Visual-Reference:` and `> Visual-Hash:` lines |
| `anchor-lines` | removes `> Requires:` and `> Global:` from every spec and `> Scope:` from every anchor, and names each anchor that specs named, with the specs and the command that moves a rule into them |
| `os-tags` | rewrites the Windows tag 0.9.5 wrote at the end of a proof line to `@env(windows)` |
| `kind-tags` | drops the tag naming the kind of test from every proof line |
| `untracked-files` | deletes the proof files 0.9.5 committed beside the specs and its cache folder, and untracks the dashboard data |
| `hooks` | deletes the git hooks 0.9.5 installed, and leaves a hook another tool wrote |
| `config` | writes `.purlin/config.json` at this release's six keys, asks the gate question, and names every key it drops |
| `evidence` | creates `.purlin/evidence/` with its README |
| `dashboard` | replaces a `purlin-report.html` at the project root that is a link or differs from the page `purlin:init` copies; a project with no page there is left without one |
| `workflows` | removes the workflow 0.9.5 wrote, and offers the runner file where `purlin:init` would write it, only where a proof is tagged `@env` for a system this machine is not |
| `markers` | rewrites each 0.9.5 marker in the project's tests as one comment above the same test |
| `plugins` | removes the test plugins 0.9.5 copied into the project and the wiring that loaded them |

The `config` migration asks the gate question a new project is asked, offering the gate the
settings name as the default:

```
What must be true of every rule before a version is finished?
  passed  every rule's tests pass
  signed  every rule's tests pass, and a person signs each release
Gate [passed]: passed
```

An empty answer takes the default. A 0.9.5 project whose hook setting blocked a push is offered
`passed`. At `signed`, where the settings name no
`mutation_engine` and an engine that runs on this operating system exists for the project's
frameworks, the mutation question follows, and its default is no. The `tests` setting is written
from the frameworks the old settings named, and a framework nothing in the tree runs is dropped
with a line saying so. The `workflows` migration asks once more before it writes the runner file:

```
Write .github/workflows/purlin.yml, one job per operating system your specs name that this machine is not? [y/N] y
```

Once the last question is answered, each migration applied prints what it did, indented two
spaces, such as:

```
  set the gate to passed and dropped 4 keys this release does not read: digest, pre_push, report, spec_dir
  wrote the tests setting: no suite; add one under "tests" in .purlin/config.json
```

A `gate` this release does not offer is written as `passed`, with `mutation_engine` kept as it
is, and the migration prints a line saying so. Each key this release does not read is taken out,
with the line `removed from .purlin/config.json: <key>`.

Before a migration rewrites a file it copies the bytes beside it as `<name>.local-<sha8>.bak` and
prints `kept the previous bytes at <path>`. A feature spec with no `> Scope:` line is not a
migration: the update names each such spec in the words the status uses, and changes nothing.

Everything the run applied lands in one commit, named on one line,
`  committed <sha> as chore(update): migrate to <VERSION> (<ids>)`. The run ends as
`purlin:status` ends: `→ Run: purlin:init --update` while a migration is still pending, then the
summary and `Left to do`. `--yes` asks nothing and applies every pending migration with the default
answers. A second run with nothing pending prints `Nothing is pending: this project is at
<VERSION>.` and changes nothing.

Exit codes: 0 when nothing is pending or the run finished; 1 when `.purlin/config.json` cannot be
read, with the sentence saying why; 2 when the folder has no `.purlin/`, with
`There is no .purlin/ under <folder>, so there is nothing to update. Run purlin:init first.`

Read next: [getting-started.md](getting-started.md) if you are setting a project up for the first
time, [team-workflow.md](team-workflow.md) and [regulated-workflow.md](regulated-workflow.md) for
the two ways a team works.
