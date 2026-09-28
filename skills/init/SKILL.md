---
name: init
description: Set a project up for Purlin, and change the gate later
---

# purlin:init

Set a project up for spec-driven development, and change the one setting later when the team or
the obligations change. **Paths.** Every `references/`, `templates/` and `scripts/` path below
is inside the plugin and is reached through `${CLAUDE_PLUGIN_ROOT}`; a project carries none of
them. When `python3` is not on PATH, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh"
<script> [args]`, which resolves the interpreter and execs it.

## The questions

Init asks these, in this order, and nothing else. Everything else it reads from the tree: the
language and the test framework from detection, the git host from the remote URL. A question
the project's `.purlin/config.json` or a flag already answers is not asked.

1. **The gate**, on every first run: `What must be true of every rule before a version is
   proven?`, with the three answers below. The default is `passed`.
2. **The test command and its report**, only where init detects no framework, as in an empty
   repository: `What command runs the tests?`, then where that command writes its report, a
   JUnit XML file, a `.trx` file or folder, `-` for a `go test -json` stream, or nothing when
   each test file passes by exiting 0. No command writes no suite, and init says so.
3. **Mutation testing**, only where an engine exists for a detected framework: `Measure test
   strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per
   run. [y/N]`. The default is no.
4. **Trust**, on every first run: whether this machine is trusted for the tests and the signing.

The first answer is the **gate**, one of three:

| Gate | What every rule must have | Signatures |
|------|---------------------------|------------|
| `passed` | its marked tests pass, from any source | none |
| `strong` | that, and a strong cell met on every rule whose level is `strong` or above: an audit of its text, proof and test that found nothing outstanding, and, with mutation testing on, test strength at or above `min_strength` | none required |
| `signed` | everything `strong` requires, plus a current signature on every rule whose level is `signed`, in a signed commit | the signature names who signed |

An unmarked rule takes the gate as its level. `purlin:sign` is what says a version met the
gate: it walks the queue, commits the evidence package and writes the signed tag
`signed/<version>` on that commit, which a person pushes. `references/hard_gates.md` defines
what the tag means.

A yes to the mutation question writes `mutation_engine: auto` and `min_strength` (null at
`passed`, 70 at `strong`, 80 at `signed`) and wires the engine: `[tool.mutmut]` into
`pyproject.toml` when that file exists and `[mutmut]` into `setup.cfg` otherwise, plus a
`mutants/` line in `.gitignore`, or a line naming Stryker for a jest, vitest or .NET project. A
no writes `mutation_engine: none` and `min_strength: null` and wires nothing; the AI audit alone
judges test strength. A config with no `mutation_engine` is read as `none`, which is off. Where
no engine exists init asks nothing, writes `none` and prints one line saying so. `--yes` takes
every default, so mutation testing stays off; `--mutation` turns it on without the question.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root . --gate <level>
```

Pass `--dry-run` to print every file init would write or edit and write none of them. Read that
list back to the person before running it for real on a project that already has code.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | Sets the gate, at setup or later. Lowering changes the setting and deletes nothing |
| `--mutation` | Turns mutation testing on without asking |
| `--yes` | Takes the default answer to every question and every write |
| `--update` | Brings a project Purlin 0.9.5 set up to the installed release. See below |
| `--add <language>` | Adds a second framework: one more entry in the `tests` setting |
| `--dry-run` | Prints the plan and writes nothing |

The first run writes without asking again: its questions are the consent. A later run, on a
project that already has `.purlin/config.json`, asks `[Y/n]` before each write, so raising the
gate writes the setting, and the gate's `min_strength` where mutation testing is on, and
touches nothing you decline. Lowering the gate rewrites the setting and deletes nothing: the
workflow, the evidence and the signatures stay where they are.

`--add <language>` is for a repository with, say, a Python service and a TypeScript client:
init appends the second framework's entry to the `tests` setting beside the first. One
`purlin:test` then runs both.

## What init writes

It writes `.purlin/`, `specs/` and `specs/_anchors/`; `.purlin/config.json` with the answers
and what they derive; a block in `.gitignore`; and `.purlin/evidence/` with one README saying
what the folder holds. It installs nothing in the project's tests. For each framework it
detects it writes one entry of the `tests` setting: the framework's own command, with the flag
that writes the report Purlin reads already in it, where the report lands, its format and the
globs its test files live under. It says in one line what a framework needs added before it
can write that report: Jest needs the package `jest-junit`, installed with
`npm install --save-dev jest-junit`. `references/supported_frameworks.md` shows every entry,
and `references/formats/marker_format.md` is the contract. The `.gitignore` block covers
`.purlin/runtime/`, where a run's reports and log land, `.purlin/report-data.js`, and
`purlin-report.html`, the dashboard page init copies to the project root so it opens from
disk. `.purlin/evidence/` and `.purlin/tests.md` stay tracked. It wires the engine only when
mutation testing is on, and writes a CI workflow only for the two reasons below. It commits
nothing, and prints every file it wrote, kept or skipped, one per line.

Where a runner is called for, the workflow triggers on two things: a push of a `signed/**` tag,
and a push to a `run/*` branch, the branch `purlin:test --remote` creates and deletes around
one run. The job is named `purlin`, and every run ends with
`scripts/ci/gate_check.py --check --verify`, which fails the job when the gate is not met or a
committed signature does not match the code. No breaks and no AI audit run on the runner.

The config it writes carries these eight keys and no other; `tests` below is what a pytest
project gets, and `version` is the plugin's `VERSION` file. `audit_parallel`, how many AI audit
calls run at once, is 4 and is not asked; change it in the file, from 1 to 16.

```json
{
  "version": "<the plugin's VERSION file>",
  "gate": "strong",
  "mutation_engine": "none",
  "min_strength": null,
  "audit_parallel": 4,
  "tests": [{"name": "pytest", "format": "junit",
             "run": "python3 -m pytest --ignore=mutants {files} --junitxml={report}",
             "report": ".purlin/runtime/reports/pytest.xml",
             "files": ["**/test_*.py", "**/*_test.py"]}],
  "ci": "github",
  "trust": "local"
}
```

Read and change the file with the `purlin_config` tool rather than by hand, so a key the
installed Purlin does not read is reported instead of kept.

## The trust question

Init asks it exactly like this, with `y` as the default, the first at the gate `passed` and the
second from `strong` up:

```
Do you trust your own machine for the tests? [y/n]
Do you trust your own machine for the tests and the signing? [y/n]
```

A yes writes `"trust": "local"` and prints `Trust local: your own runs count.` at `passed`, and
`Trust local: your own runs count, and purlin:sign signs what you ran.` from `strong` up. A no
writes `"trust": "remote"`. `--update` asks again, in the words of the gate it sets.

Under `local` the whole chain runs here: test, audit, sign, tag, push. A project that answers
yes and tags no proof for another operating system has no CI at all. That is the ordinary
case, at every gate, `signed` included: the tag is your word that every rule met the gate on
your machine.

Under `remote` a signature rests on a run this machine did not make. `purlin:sign` refuses a
rule whose tests have no current `ci` run for this code, so `purlin:test --remote` runs first.

## The remote runner

A remote runner is written for two reasons and no others, and init prints the ones that hold:

```
A remote runner is written because:
  A proof in specs/ is tagged @env for windows, which this machine is not, so only a runner can prove it.
  You chose not to trust this machine for signing, so the tests a signature rests on run on a clean one.
```

At `passed` the second reads `You chose not to trust this machine for the tests, so they run on a
clean one.` With neither, init writes no workflow and prints `No remote runner: every test runs on
this operating system and you trust this machine, so nothing has to run remotely.`, with `every
proof` from `strong` up. Teammates read the evidence `purlin:test --commit` commits.

Before a workflow is written init checks two prerequisites: a remote exists, and its URL names
GitHub or Azure DevOps. The first that fails is printed in one line naming what to do, and no
workflow is written. The host CLI, `gh` or `az`, is reported installed or not either way. The
same checks run under `--update`.

## What each gate brings

Under every gate, init leaves the level tag optional, and mutation testing is the answer to its
own question, not the gate's. Where a workflow is called for, and `specs/` carries
`@env(windows)` or `@env(macos)` proofs, it gets a matrix: `ubuntu-latest` always, plus one job
per other operating system named, each running the same tests and writing its own section.
With no such proof there is one Linux job.

Under `signed`, a rule needs a signature exactly when its level is `signed`, and init asks
nothing about it. It prints the commit-signing setup and asks for no names: signing is logged,
not policed, and a signature names its signer.

## Commit signing under `signed`

A signature counts when the commit that added it is signed and verifies and its bound hashes
still match, whoever signed and on whatever branch. Init prints `Each signer runs this once,
then uploads the public key to the git host:` and these three commands:

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Tell each signer to upload the same public key to the git host as a signing key, so the host
shows the commit as signed.

## What the runner runs

The workflow init writes clones Purlin at the release the project pins and runs the run
script's own CI arm from that checkout: the same script a person runs, at a version that
changes only when someone edits the workflow or, on GitHub, sets the `PURLIN_REF` repository
variable.
Nobody types that arm; the workflow carries it.

| The run | What it does |
|---------|--------------|
| a `signed/**` tag | Reruns the marked tests on a clean machine, checks every signature against the tagged code, checks that every file under `.purlin/evidence/ci/` was committed by the runner's identity, runs the gate check, and commits nothing |
| a `run/*` branch | Runs the marked tests, then commits its own section of each feature's `.purlin/evidence/ci/` file onto that branch through the git host's API, at every gate |

The runner writes no signature.

## Bringing a 0.9.5 project forward

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` reads the layout Purlin 0.9.5 leaves in a project and lists each pending migration
with the files it touches. With `--dry-run` it prints that list, writes nothing and exits 1
while anything is pending. Otherwise it asks `Apply <migration>, which will <what it does>?` for
each, and in this order it: removes a spec's Figma `> Source:`, its `> Pinned:`, its
`> Visual-Reference:` and its `> Visual-Hash:` lines; rewrites the Windows tag to
`@env(windows)`; drops the kind of test from every proof line; deletes the per-run files 0.9.5
committed beside the specs and untracks `.purlin/report-data.js`; removes the `pre-commit` and
`pre-push` scripts 0.9.5 put in `.git/hooks/`; rewrites `.purlin/config.json` to the eight keys,
asking the gate and trust questions, and the mutation question where the old config names no
engine, writing the `tests` setting from the frameworks the old config named and the tree
carries, and naming every key it drops; creates `.purlin/evidence/` with its README; replaces
`purlin-report.html` at the project root, the link 0.9.5 left or a copy that differs, with the
page init copies; replaces a workflow that committed per-run files with the runner file init
writes for the git host, `.github/workflows/purlin.yml` or `purlin.azure-pipelines.yml`, where
the project has one of the two reasons; rewrites each 0.9.5 marker in the project's tests as one
comment above the same test; and removes the files 0.9.5 copied into the project for its test
frameworks, with the lines that loaded them.

Every file it rewrites is backed up beside the original as `<name>.local-<sha8>.bak`. It
commits what it applied in one commit, `chore(update): migrate to <version> (<migrations>)`.
It changes no spec that has no `> Scope:` line and names each one instead: the line is
optional below `signed` and required at `signed`. While a migration is pending `sync_status`
opens with `→ Run: purlin:init --update`.

## When you are done

Say what was written. The script's last line is the next step, computed from `sync_status`:
`→ Next: run purlin:spec to write the first spec.` when there are no specs, otherwise the
status table's own `→ Next:` line. Name the next step from what the tree shows:

- No specs and no code: `→ Next: purlin:spec "<one sentence about what the software must do>"`.
- Code but no specs: `→ Next: purlin:spec-from-code`.
- Specs but no tests: `→ Next: purlin:build <name>`.
- Gate raised to `signed` and a spec names no files in `> Scope:`: `→ Next: purlin:spec <name>`.
