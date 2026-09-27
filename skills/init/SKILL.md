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

## The one question

Ask one question and nothing else: **what must be true of every rule before a version is
proven?** There are three answers, one per evidence level. That answer is the **gate**.

| Gate | Who it fits | What every rule must have | Signatures |
|------|-------------|---------------------------|------------|
| `passed` | one person working alone | a passing tagged test for every proof, from any source | none |
| `strong` | a team of PM, designers, engineers and QA | that, and a strong cell that is met on every rule whose bar is `strong`: an audit at this commit, test strength at or above `min_strength`, nothing the audit observed outstanding, no hold | none required; anyone may sign to clear a rule reading `manual test`, `unsettled` or `held` |
| `signed` | the same team under GxP or a similar obligation | everything `strong` requires, plus a current signature on every rule that needs one, in a signed commit | required on the rules `sign_at` names; the signature names who signed |

The answer sets four defaults, each changeable afterwards: `min_strength` unused, 70, 80; the
default bar `passed`, `strong`, `strong`; `sign_at` unset, unset, `strong`; origin tags
optional, optional, required.

`purlin:sign` is what says a version met the gate: it walks the two lists and writes the
annotated tag `signed/<version>`, which a person pushes. The gate is the standard that tag
stands for; `references/hard_gates.md` defines what it means.

## The three honest exceptions

Init asks nothing else. It reads the language and the test framework from the tree and the git
host from the remote URL. Three questions remain because no answer can be read from anywhere:

1. An empty repository has nothing to detect, so init asks which language the project will be.
2. `signed` needs to know which rules need a signature, so init asks `Which rules need a
   signature?` and writes `sign_at`.
3. Whether this machine is trusted for the tests and the signing is a judgment, not a fact in
   the tree, so init asks it.

## Run it

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --project-root . --gate <level>
```

Pass `--dry-run` to print every file init would write or edit and write none of them. Read that
list back to the person before running it for real on a project that already has code.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | Sets the gate, at setup or later. Raising adds what is missing and asks before each write. Lowering changes the setting and deletes nothing |
| `--update` | Brings a project set up by an older Purlin to the installed one. See below |
| `--upstream-check` | Adds a scheduled job that opens an issue when an anchor pin falls behind |
| `--add <language>` | Adds a second language: its test framework, its proof plugin, its breaks engine |
| `--dry-run` | Prints the plan and writes nothing |

Raising the gate is additive. `--gate strong` on a project set up as `passed` creates
`designs/` if it is missing and turns the breaks on; it asks before each write and touches
nothing else. `--gate signed` on top of that asks which rules need a signature and lists the
rules with no origin tag. Lowering the gate rewrites the setting and
deletes nothing: the workflow, the records and the signatures stay where they are.

Raising the gate writes no workflow. A runner is added for its own two reasons, below, and not
because the gate moved.

`--add <language>` is for a repository with, say, a Python service and a TypeScript client:
init detects the second framework, installs its proof plugin beside the first, adds its breaks
engine, and writes both into `.purlin/config.json`. One `purlin:test` then runs both.

## What init writes

It writes `.purlin/config.json` with the gate, the trust answer, the git host, the test
framework, the breaks engine and the derived defaults; `specs/` for the two-section specs; and
`.purlin/records/` with a README saying an audit writes the files in it, under `ci/` or
`local/`, and nobody edits them by hand. It installs the proof plugin for the detected
framework and the breaks engine for the language, writing `[tool.mutmut]` into `pyproject.toml`
when that file exists and `[mutmut]` into `setup.cfg` otherwise. It adds a `.gitignore` block
for `.purlin/runtime/`, where test runs put their proof files, and copies the dashboard page so
it opens from disk. It installs no git hook at all: nothing runs at commit time and nothing
runs at push time. It installs the Claude Code hook that refreshes the local dashboard data. It
creates `designs/` with a README at `strong` and `signed`, and ignores
`.purlin/briefs/**/*.brief.txt`, the local rendering beside the brief JSON an audit commits,
then prints every file it wrote or edited, one per line.

That Claude Code hook is the only hook init installs. It writes no git hook at all: nothing
runs at push time, and a push is free, to any branch, for anyone.

Where a runner is called for, the workflow triggers on two things and nothing else: a push of a
`signed/**` tag, and a push to a `run/*` branch, the branch `purlin:test --remote` creates and
deletes around one run. A pull request starts nothing. The job is named `purlin`. The tag run
reruns the tagged tests on a clean machine, checks that every signature and every hold still
binds the rule, the proof, the test, the bar and the audit it names, checks that every record
and brief under `ci/` was committed by the runner's own identity, and ends with
`scripts/ci/gate_check.py --check --verify`, which fails the job when the gate is not met or
the evidence does not hold. No breaks run on the runner.

The config it writes looks like this, and every key after `gate` has a default the gate
implies:

```json
{
  "version": "0.10.0",
  "gate": "strong",
  "trust": "local",
  "min_strength": 70,
  "mutation_engine": "mutmut",
  "sql_engine": null,
  "ci": "github",
  "test_framework": "pytest"
}
```

`sign_at` joins it under `signed` and nowhere else; init asks for it there. Read and change the file with the `purlin_config`
tool rather than by hand, so a key the installed Purlin no longer reads is reported instead of
silently kept.

## Who writes the evidence

`purlin:test` commits the test results under `.purlin/tests/` and `purlin:audit` writes the
record. A record's source is the folder it sits in: `.purlin/records/ci/`, written by a remote
runner, or `.purlin/records/local/`, which is anyone's. Both count at every gate.

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
rule whose tests have no `ci` record for the current commit, so `purlin:test --remote` runs
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

Under every gate, init creates the records folder and its retention rule, and leaves the bar,
origin and criterion tags optional. Under `strong` and `signed`, init also writes `designs/`
and turns the breaks on. Where a workflow is called for, and `specs/` carries `@env(windows)`
or `@env(macos)` proofs, it gets a matrix: a Linux job always, plus one job per other operating
system named, each running the same tests and writing its own record. With no such proof there
is one Linux job.

Under `signed`, init asks `Which rules need a signature?` and writes the answer to `sign_at`:
`strong`, the rules whose bar is strong, the rest meeting the gate on their tests; or `all`,
every rule whatever its bar. It prints the commit-signing setup and lists every rule with no
origin tag so `purlin:spec <name>` can tag them in one pass. It asks for no names: signing is
logged, not policed, and a signature names its signer.

Anchor pins and the upstream-check job are added on demand. When one is missing later the tool
that needs it says so: `purlin:drift` reports a pin behind, and `purlin:audit` says the breaks
engine is unavailable.

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
| a `signed/**` tag | Reruns the tagged tests on a clean machine, checks every signature and every hold against the tagged code, checks that every record and brief under `ci/` was committed by the runner's identity, runs the gate check, and commits nothing |
| a `run/*` branch | Runs the tagged tests, and at `strong` and above audits what it ran, then commits its records and briefs onto that branch under `ci/` through the git host's API |

The runner writes no signature, ever, and it posts no comment and uploads no artifact: the
dashboard is the page that opens from disk.

## Bringing an older project forward

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` detects the older layout and offers each change separately. It untracks and deletes
the proof files and the evidence files that used to be committed, untracks the committed
dashboard data, removes the git hook an older Purlin installed and says why, retires the config keys that
no longer exist, asks the gate question and the trust question once each, and rewrites an
operating-system tag to `@env(...)` only where the intended system is unambiguous. Every write asks first, every file it replaces
is backed up beside the original, and while the update is pending `sync_status` opens with
`→ Run: purlin:init --update`.

## When you are done

Say what was written, then name the next step from what the tree shows, not from a script:

- No specs yet: `→ Next: purlin:spec "<one sentence about what the software must do>"`.
- Specs but no tests: `→ Next: purlin:build <name>`.
- Code but no specs: `→ Next: purlin:spec-from-code`.
- Gate raised to `signed` with untagged rules: name them and point at `purlin:spec <name>`.
