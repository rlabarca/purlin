---
name: init
description: Set a project up for Purlin, and change the gate later
---

# purlin:init

Set a project up for spec-driven development, and change the one setting later when the team or
the obligations change.

**Paths.** Every `references/`, `templates/`, `hooks/` and `scripts/` path below is inside the
plugin and is reached through `${CLAUDE_PLUGIN_ROOT}`; a project carries none of them. When
`python3` is not on PATH, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh" <script>
[args]`, which resolves the interpreter and execs it.

## The questions

Init asks these, in this order, and nothing else. Everything else it reads from the tree: the
language and the test framework from detection, the git host from the remote URL.

1. **The gate**, always: `What must be true of every rule before a version is proven?`
2. **The test framework**, only in an empty repository, where there is nothing to detect.
   The default is `shell`.
3. **Mutation testing**, only where an engine exists for a detected framework: `Measure test
   strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per
   run. [y/N]`. The default is no.
4. **Trust**, always: whether this machine is trusted for the tests and the signing.

The first answer is the **gate**, one of three:

| Gate | What every rule must have | Signatures |
|------|---------------------------|------------|
| `passed` | a passing tagged test for every proof, from any source | none |
| `strong` | that, and a strong cell met on every rule whose level is `strong` or above: an audit of its text, proof and test that found nothing outstanding, and, with mutation testing on, test strength at or above `min_strength` | none required |
| `signed` | everything `strong` requires, plus a current signature on every rule whose level is `signed`, in a signed commit | the signature names who signed |

An unmarked rule takes the gate as its level. `purlin:sign` is what says a version met the
gate: it walks the queue and writes the annotated tag `signed/<version>`, which a person pushes.
`references/hard_gates.md` defines what the tag means.

A yes to the mutation question writes `mutation_engine: auto` and `min_strength` (null at
`passed`, 70 at `strong`, 80 at `signed`) and wires the engine: `[tool.mutmut]` into
`pyproject.toml` when that file exists and `[mutmut]` into `setup.cfg` otherwise, or a line
naming Stryker for a node or .NET project. A no writes `mutation_engine: none` and `min_strength:
null` and wires nothing; the AI audit alone judges test strength. Where no engine exists init
asks nothing, writes `none` and prints one line saying so. `--yes` takes every default, so
mutation testing stays off; `--mutation` turns it on without the question.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root . --gate <level>
```

Pass `--dry-run` to print every file init would write or edit and write none of them. Read that
list back to the person before running it for real on a project that already has code.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | Sets the gate, at setup or later. Raising adds what is missing and asks before each write. Lowering changes the setting and deletes nothing |
| `--mutation` | Turns mutation testing on without asking |
| `--yes` | Takes the default answer to every question |
| `--update` | Brings a project set up by an older Purlin to the installed one. See below |
| `--add <language>` | Adds a second language: its test framework and its proof plugin |
| `--dry-run` | Prints the plan and writes nothing |

Raising the gate is additive: it writes the setting, and the gate's `min_strength` where
mutation testing is on, asks before each write and touches nothing else. Lowering the gate
rewrites the setting and deletes nothing: the workflow, the evidence and the signatures stay
where they are.

Raising the gate writes no workflow. A runner is added for its own two reasons, below, and not
because the gate moved.

`--add <language>` is for a repository with, say, a Python service and a TypeScript client:
init detects the second framework, installs its proof plugin beside the first, and writes both
into `.purlin/config.json`. One `purlin:test` then runs both.

## What init writes

It writes `.purlin/config.json` with the answers and what they derive; `specs/` for the
two-section specs; and `.purlin/evidence/` with one README saying what the folder holds. It
installs the proof plugin for the detected framework, and the engine only when mutation testing
is on. It adds a `.gitignore` block for `.purlin/runtime/`, where test runs put their proof
files, and copies the dashboard page so it opens from disk. It installs no git hook at all:
nothing runs at commit time and nothing runs at push time. It installs the Claude Code hook
that refreshes the local dashboard data. It leaves `.purlin/evidence/` and `.purlin/tests.md`
tracked, then prints every file it wrote or edited, one per line.

That Claude Code hook is the only hook init installs. It writes no git hook at all: nothing
runs at push time, and a push is free, to any branch, for anyone.

Where a runner is called for, the workflow triggers on two things and nothing else: a push of a
`signed/**` tag, and a push to a `run/*` branch, the branch `purlin:test --remote` creates and
deletes around one run. A pull request starts nothing. The job is named `purlin`. The tag run
reruns the tagged tests on a clean machine, checks that every signature still
binds the rule, the proof, the test and the audit it names, checks that every file
under `.purlin/evidence/ci/` was committed by the runner's own identity, and ends with
`scripts/ci/gate_check.py --check --verify`, which fails the job when the gate is not met or
the evidence does not hold. No breaks run on the runner.

The config it writes carries these nine keys and no other. `audit_parallel`, how many AI audit
calls run at once, is 4 and is not asked; change it in the file, from 1 to 16.

```json
{
  "version": "0.10.0",
  "gate": "strong",
  "mutation_engine": "none",
  "min_strength": null,
  "audit_parallel": 4,
  "test_framework": "auto",
  "sql_engine": null,
  "ci": "github",
  "trust": "local"
}
```

Read and change the file with the `purlin_config`
tool rather than by hand, so a key the installed Purlin no longer reads is reported instead of
silently kept.

## Who writes the evidence

`purlin:test` writes each feature's evidence under `.purlin/evidence/local/`, `purlin:audit`
adds what the audit found, and `--commit` on either commits it. A file's source is the folder
it sits in: `.purlin/evidence/ci/`, written by a remote runner, or `.purlin/evidence/local/`,
which is anyone's. Both count at every gate.

## The trust question

Ask it exactly like this, with `y` as the default:

```
Do you trust your own machine for the tests and the signing? [y/n]
```

A yes writes `"trust": "local"`, a no writes `"trust": "remote"`. `--update` asks again.

Under `local` the whole chain runs here: test, audit, sign, tag, push. Nothing runs anywhere
else, and a project that answers yes and tags no proof for another operating system has no CI
at all. That is the ordinary case, at every gate, `signed` included: the tag is your word that
every rule met the gate on your machine.

Under `remote` a signature rests on a run this machine did not make. `purlin:sign` refuses a
rule whose tests have no current `ci` run for this code, so `purlin:test --remote` runs
first.

## The remote runner

A remote runner is written for two reasons and no others, and init prints the ones that hold:

```
A remote runner is written for two reasons:
  A proof in specs/ is tagged @env for windows, which this machine is not, so only a runner can prove it.
  You chose not to trust this machine for signing, so the tests a signature rests on run on a clean one.
```

With neither, no workflow is written at any gate and init says `No remote runner: every proof
runs on this operating system and you trust this machine, so nothing has to run remotely.`
Teammates see your results without one, from the test results `purlin:test` commits.

Before any workflow is written init checks two prerequisites: a remote exists, and its URL
names GitHub or Azure DevOps. The first that fails is printed in one line naming what to do,
and no workflow is written. No branch is checked, because a signature counts on whatever
commit carries it. The host CLI, `gh` or `az`, is reported present or absent either way. The
same checks run under `--update`.

## What each gate brings

Under every gate, init leaves the level tag optional, and mutation testing is the answer to its
own question, not the gate's. Where a workflow is called for, and `specs/` carries `@env(windows)`
or `@env(macos)` proofs, it gets a matrix: a Linux job always, plus one job per other operating
system named, each running the same tests and writing its own section. With no such proof there
is one Linux job.

Under `signed`, a rule needs a signature exactly when its level is `signed`, and init asks nothing
about it. It prints the commit-signing setup. It asks for no names: signing is
logged, not policed, and a signature names its signer.

Anchor pins are added on demand. When something is missing later the tool that needs it says
so: `purlin:drift` reports a pin behind, and `purlin:audit` says when the engine is not
installed.

## Branch rules

Init prints none, and Purlin asks for none. A push is free, to any branch, for anyone, and
nothing runs at push time. The marker that a version met the gate is the tag `purlin:sign`
writes, not a branch setting on the git host.

## Commit signing under `signed`

A signature counts when the commit that added it is signed and verifies and its bound hashes
still match, whoever signed and on whatever branch. Print these three commands once per
signer:

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Then tell them to upload the same public key to the git host as a signing key, so the host
shows the commit as signed. No git-host reviewer setting and no owners file is needed.

## What the runner runs

A project has no copy of Purlin in it, so the workflow init writes clones Purlin at a pinned
tag and runs the run script's own CI arm from that checkout: the same script a person runs, at
a version that changes only when someone edits the workflow. Nobody types that arm; the
workflow carries it.

| The run | What it does |
|---------|--------------|
| a `signed/**` tag | Reruns the tagged tests on a clean machine, checks every signature against the tagged code, checks that every file under `.purlin/evidence/ci/` was committed by the runner's identity, runs the gate check, and commits nothing |
| a `run/*` branch | Runs the tagged tests, then commits its own section of each feature's `.purlin/evidence/ci/` file onto that branch through the git host's API, at every gate |

The runner writes no signature, ever, and it posts no comment and uploads no artifact: the
dashboard is the page that opens from disk.

## Bringing an older project forward

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` detects the layout 0.9.5 left and offers each change separately. It removes a
spec's Figma source, its pinned timestamp, its `> Visual-Reference:` and its `> Visual-Hash:`
lines and names each spec; untracks and deletes the proof files and the run files 0.9.5
committed beside the specs; untracks the committed dashboard data; removes the git hooks 0.9.5
installed and says why; drops every config key this release does not read and names each one;
asks the gate, mutation and trust questions once each; creates `.purlin/evidence/` with its
README; rewrites the Windows tag to `@env(windows)` and drops the kind of test from every proof
line. It changes no spec that has no `> Scope:` line and names each one instead: the line is
optional below `signed` and required at `signed`. Every write asks first, every file it replaces
is backed up beside the original, and while the update is pending `sync_status` opens with
`→ Run: purlin:init --update`.

## When you are done

Say what was written, then name the next step from what the tree shows, not from a script:

- No specs yet: `→ Next: purlin:spec "<one sentence about what the software must do>"`.
- Specs but no tests: `→ Next: purlin:build <name>`.
- Code but no specs: `→ Next: purlin:spec-from-code`.
- Gate raised to `signed` with untagged rules: name them and point at `purlin:spec <name>`.
