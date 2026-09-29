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
test frameworks from detection, the git host from the remote URL. A question the project's
`.purlin/config.json` or a flag already answers is not asked.

1. **The gate**, on every first run: `What must be true of every rule before a version is
   proven?`, with the three answers below. The default is `passed`.
2. **Mutation testing**, only at `strong` and `signed`, and only where an engine exists for a
   framework the tree carries: `Measure test strength by breaking the code on purpose? It needs
   <engine> and takes minutes to hours per run. [y/N]`. The default is no.

The first answer is the **gate**, one of three:

| Gate | What every rule must have | Signatures |
|------|---------------------------|------------|
| `passed` | its marked tests pass, from any source | none |
| `strong` | that, and an audit of its text, proof and test that found nothing outstanding, and, with mutation testing on, test strength at or above `min_strength` | none required |
| `signed` | everything `strong` requires, plus a current signature, in a signed commit | the signature names who signed |

At `signed`, `purlin:sign` writes the signed tag `signed/<version>` once nothing is left to do,
and a person pushes it. `references/hard_gates.md` defines what the tag means.

A yes to the mutation question writes `mutation_engine: auto` and `min_strength` (70 at
`strong`, 80 at `signed`) and wires the engine: `[tool.mutmut]` into `pyproject.toml` when that
file exists and `[mutmut]` into `setup.cfg` otherwise, plus a `mutants/` line in `.gitignore`,
or a line naming Stryker for a jest, vitest or .NET project. A no writes
`mutation_engine: none` and `min_strength: null` and wires nothing; the AI audit alone judges
test strength. A config with no `mutation_engine` is read as `none`, which is off. Where no
engine exists init asks nothing, writes `none` and, at `strong` and `signed`, prints one line
saying so. `--yes` takes every default, so mutation testing stays off; `--mutation` turns it on
without the question, at any gate.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root . --gate <gate>
```

| Flag | What it does |
|------|--------------|
| `--gate <gate>` | Sets the gate, at setup or later. Lowering changes the setting and deletes nothing |
| `--mutation` | Turns mutation testing on without asking |
| `--yes` | Takes the default answer to every question and every write |
| `--update` | Brings a project Purlin 0.9.5 set up to the installed release. See below |
| `--add <language>` | Adds one framework's entry to the `tests` setting |

The first run writes without asking again: its questions are the consent. A later run, on a
project that already has `.purlin/config.json`, asks `[Y/n]` before each write, so raising the
gate writes the setting, and the gate's `min_strength` where mutation testing is on, and
touches nothing you decline. Lowering the gate rewrites the setting and deletes nothing: the
workflow, the evidence and the signatures stay where they are.

`--add <language>` appends that framework's entry to the `tests` setting beside the ones
already there, once however many times it is added. One `purlin:test` then runs them all.

## What init writes

It writes `.purlin/` and `specs/`; `.purlin/config.json` with the answers and what they
derive; a block in `.gitignore`; and `.purlin/evidence/` with one README saying what the folder
holds. The folder for anchors, `specs/_anchors/`, is made when the first anchor is written. It
installs nothing in the project's tests and asks nothing about them: it writes the `tests`
setting as an empty list, and the first `purlin:test` suggests the entry for the test tool it
recognises, the command with the flag that writes the report Purlin reads, and writes it once
the person agrees. `references/supported_frameworks.md` shows every entry, and
`references/formats/marker_format.md` is the contract. The `.gitignore` block covers
`.purlin/runtime/`, where a run's reports and log land, `.purlin/report-data.js`, and
`purlin-report.html`, the dashboard page init copies to the project root so it opens from
disk. `.purlin/evidence/` and `.purlin/tests.md` stay tracked. It wires the engine only when
mutation testing is on, and writes a workflow only for the one reason below. It commits
nothing, and prints every file it wrote, kept or skipped, one per line.

Where a runner is called for, the workflow triggers on two things: a push of a `signed/**` tag,
and a push to a `run/*` branch, the branch `purlin:test --remote` creates and deletes around
one run. The job is named `purlin`, and its last step is the test run: the job fails only when
a test fails or could not run. No breaks and no AI audit run on the runner.

The config it writes carries these seven keys and no other; `version` is the plugin's `VERSION`
file. `audit_parallel`, how many AI audit calls run at once, is 4 and is not asked; change it in
the file, from 1 to 16.

```json
{
  "version": "<the plugin's VERSION file>",
  "gate": "strong",
  "mutation_engine": "none",
  "min_strength": null,
  "audit_parallel": 4,
  "tests": [],
  "ci": "github"
}
```

`ci` is the git host read from the remote URL, `github` or `azure`, and `none` where there is
no remote or it names neither. Where it names neither, init prints `The origin remote is neither
GitHub nor Azure DevOps. Everything on this machine works with any host; only purlin:test
--remote needs one of those two.` Read and change the file with the `purlin_config` tool
rather than by hand, so a key the installed Purlin does not read is reported instead of kept.

## The remote runner

A remote runner is written for one reason and no other: a proof in `specs/` is tagged `@env`
for an operating system this machine is not. Init prints it:

```
A remote runner is written because:
  A proof in specs/ is tagged @env for windows, which this machine is not, so only a runner can prove it.
```

At `passed` the reason reads `A test is tagged @env for windows, which this machine is not, so
only a runner can run it.` With no such proof, init writes no workflow and prints one line
starting `No remote runner:`. Teammates read the evidence `purlin:test --commit` commits.

Before a workflow is written init checks two prerequisites: a remote exists, and its URL names
GitHub or Azure DevOps. The first that fails is printed in one line naming what to do, and no
workflow is written. The host CLI, `gh` or `az`, is reported installed or not either way. The
same checks run under `--update`.

## What each gate brings

Mutation testing is the answer to its own question, not the gate's. Where a workflow is called
for, it gets a matrix of one job per operating system the `@env` tags in `specs/` name, each
running the same tests and writing its own section.

Under `signed`, every rule needs a signature, and init asks nothing about it and names nobody:
anyone can sign, and a signature names its signer. Init prints no signing setup. `purlin:sign`
checks for a key to sign with and, when there is none, shows the commands that set one up.

## What the runner runs

The workflow init writes clones Purlin at the release the project pins and runs the run
script's own CI arm from that checkout: the same script a person runs, at a version that
changes only when someone edits the workflow or, on GitHub, sets the `PURLIN_REF` repository
variable.
Nobody types that arm; the workflow carries it.

| The run | What it does |
|---------|--------------|
| a `signed/**` tag | Reruns the marked tests on a clean machine and commits nothing |
| a `run/*` branch | Runs the marked tests, then commits its own section of each feature's `.purlin/evidence/ci/` file onto that branch through the git host's API, at every gate |

The runner writes no signature.

## Bringing a 0.9.5 project forward

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` reads the layout Purlin 0.9.5 leaves in a project and lists each pending migration
with the files it touches. It asks `Apply <migration>, which will <what it does>?` for each,
and in this order it: removes a spec's Figma `> Source:`, its `> Pinned:`, its
`> Visual-Reference:` and its `> Visual-Hash:` lines; rewrites the Windows tag to
`@env(windows)`; drops the kind of test from every proof line; deletes the per-run files 0.9.5
committed beside the specs and `.purlin/cache/`, and untracks `.purlin/report-data.js`; removes
the `pre-commit` and `pre-push` scripts 0.9.5 put in `.git/hooks/`; rewrites
`.purlin/config.json` to the seven keys, asking the gate question, and the mutation question at
`strong` and `signed` where the old config names no engine, writing the `tests` setting from the
frameworks the old config named and the tree carries, and naming every key it drops; creates
`.purlin/evidence/` with its README; replaces `purlin-report.html` at the project root, the link
0.9.5 left or a copy that differs, with the page init copies; replaces a workflow that committed
per-run files with the runner file init writes for the git host, `.github/workflows/purlin.yml`
or `purlin.azure-pipelines.yml`, where a proof names another operating system; rewrites each
0.9.5 marker in the project's tests as one comment above the same test; and removes the files
0.9.5 copied into the project for its test frameworks, with the lines that loaded them.

Every file it rewrites is backed up beside the original as `<name>.local-<sha8>.bak`. It
commits what it applied in one commit, `chore(update): migrate to <version> (<migrations>)`.
It changes no spec that has no `> Scope:` line and names each one instead: the line is
optional below `signed` and required at `signed`. While a migration is pending `sync_status`
prints `→ Run: purlin:init --update` above its summary, and a test run stops and names it.

## When you are done

Say what was written. The script ends on the lines `purlin:status` ends on, the summary and
`Left to do`, whose first line is the next step, or, with no spec yet, on
`→ Run: purlin:spec to write the first spec.` Name the next step from what the tree shows:

- No specs and no code: `→ Run: purlin:spec "<one sentence about what the software must do>"`.
- Code but no specs: `→ Run: purlin:spec-from-code`.
- Specs but no tests: `→ Run: purlin:build <name>`.
- Gate raised to `signed` and a spec names no files in `> Scope:`: `→ Run: purlin:spec <name>`.
