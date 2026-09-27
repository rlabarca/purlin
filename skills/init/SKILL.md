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

Ask one question and nothing else: **what must be true before CI lets a change merge?** There
are three answers, one per evidence level. That answer is the **gate**.

| Gate | Who it fits | What CI requires before merge | Signatures |
|------|-------------|-------------------------------|------------|
| `passed` | one person working alone | every rule's passed cell is met: a passing tagged test, from any source | none |
| `strong` | a team of PM, designers, engineers and QA | every rule whose bar is `strong` has a strong cell that is met: a record at this commit, test strength at or above `min_strength`, no finding and no hold | none required; anyone may sign to clear a rule reading `manual test`, `unsettled` or `held` |
| `signed` | the same team under GxP or a similar obligation | everything `strong` requires, plus a current signature on every rule that needs one, in a signed commit by someone on the signer list | required: the signer list decides who |

The answer sets four defaults, each changeable afterwards: `min_strength` unused, 70, 80; the
default bar `passed`, `strong`, `strong`; `sign_at` unset, unset, `strong`; origin tags
optional, optional, required.

## The three honest exceptions

Init asks nothing else. It reads the language and the test framework from the tree and the git
host from the remote URL. Three questions remain because no answer can be read from anywhere:

1. An empty repository has nothing to detect, so init asks which language the project will be.
2. `signed` needs names, so init asks for the signer emails.
3. At `passed` with a remote, a remote runner is a choice, so init explains it and asks.

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
| `--upstream-check` | Adds a scheduled job that opens a pull request or an issue when an anchor pin falls behind |
| `--add <language>` | Adds a second language: its test framework, its proof plugin, its breaks engine |
| `--dry-run` | Prints the plan and writes nothing |

Raising the gate is additive. `--gate strong` on a project set up as `passed` writes the CI
workflow, creates `designs/` if it is missing, turns the breaks on, and prints the branch rules;
it asks before each write and touches nothing else. `--gate signed` on top of that asks for the
signer emails, asks which rules need a signature, and lists the rules with no origin tag. Lowering the gate rewrites the
setting and deletes nothing: the workflow, the records and the signatures stay, and CI stops
requiring them.

`--add <language>` is for a repository with, say, a Python service and a TypeScript client:
init detects the second framework, installs its proof plugin beside the first, adds its breaks
engine, and writes both into `.purlin/config.json`. One `purlin:test` then runs both.

## What init writes

It writes `.purlin/config.json` with the gate, the git host, the test framework, the breaks
engine and the derived defaults; `specs/` for the two-section specs; and `.purlin/records/` with
a README saying an audit writes the files in it, under `ci/` or `local/`, and nobody edits them by hand. It installs the proof
plugin for the detected framework and the breaks engine for the language, writing
`[tool.mutmut]` into `pyproject.toml` when that file exists and `[mutmut]` into `setup.cfg`
otherwise. It adds a `.gitignore` block for `.purlin/runtime/`, where test runs put their proof
files, and copies the dashboard page so it opens from disk. It offers a `pre-push` hook that
runs the tagged tests, the same run `purlin:test` makes, and refuses a push from an agent
session, and installs the Claude Code hook that refreshes the local dashboard data. It creates
`designs/` with a README at `strong` and `signed`, where it also writes the CI workflow and
ignores `.purlin/briefs/**/*.brief.txt`, the local rendering beside the brief JSON an audit commits,
then prints every file it wrote or edited, one per line.

The workflow runs where the evidence it writes is decided. It triggers on a pull request, on a
push to the project's own default branch and on a push to a `run/*` branch, the branch
`purlin:test --remote` creates and deletes around one run; a push to any other branch starts
nothing. A pull request run does the tests, posts the comment and uploads the dashboard, and
commits nothing; a run on the default branch or on a run branch commits its records and briefs
there. Every run ends with `Check the gate`, which runs `scripts/ci/gate_check.py --check` and
fails the job when the gate is not met.

The config it writes looks like this, and every key after `gate` has a default the gate
implies:

```json
{
  "version": "0.10.0",
  "gate": "strong",
  "min_strength": 70,
  "mutation_engine": "mutmut",
  "sql_engine": null,
  "ci": "github",
  "test_framework": "pytest"
}
```

`signers` and `sign_at` join it under `signed` and nowhere else; init asks for both there. Read and change the file with the `purlin_config`
tool rather than by hand, so a key the installed Purlin no longer reads is reported instead of
silently kept.

## Who writes the evidence

`purlin:test` commits the test results under `.purlin/tests/` and `purlin:audit` writes the
record. A record's source is the folder it sits in: `.purlin/records/ci/`, which the git host
reserves for the build identity, or `.purlin/records/local/`, which is anyone's. Under `passed`
and `strong` both count; under `signed` only `ci` does.

## The remote runner

At `passed`, with a remote, init prints this and nothing else, then asks:

```
A remote runner is worth having for three reasons:
  Your tests need another operating system.
  Proof from a clean machine that ran exactly the pushed code.
  No merge while red.
Teammates see your results without one, from the test results purlin:test commits.
Run the tests on a remote runner too? [y/n]
```

Those are the three reasons and there are no others. Explain each one only if asked:

- **Your tests need another operating system.** This machine cannot run a test tagged for
  Windows or Linux; the runner can, so those rules stop reading `not run`.
- **Proof from a clean machine.** A laptop may carry uncommitted edits or leftover files. The
  runner runs exactly the code that was pushed, which is what `strong` and `signed` trust.
- **No merge while red.** The git host refuses the merge while a test fails or a rule has no
  test, so nobody has to remember to check.

A yes writes the workflow; a no writes nothing and says `run purlin:init again to add it`. At
`strong` and above the workflow is always written and the same three reasons say why.

Before any workflow is written init checks the prerequisites: a remote exists, its URL names
GitHub or Azure DevOps, and the protected branch is on that remote. The first that fails is
printed in one line naming what to do, and no workflow is written. The host CLI, `gh` or `az`,
is reported present or absent either way, and a remote nobody here can reach is reported
unchecked rather than failed. The same checks run under `--update`.

## What each gate brings

Under every gate, init creates the records folder and its retention rule, and leaves the bar,
origin and criterion tags optional. Under `strong` and `signed`, init also writes `designs/` and the CI workflow (`purlin.yml`),
because the gate cannot be met without a CI run that writes records. When `specs/` carries
`@env(windows)` or `@env(macos)` proofs, the workflow gets a matrix: a Linux job always, plus
one job per other operating system named, each running the same tests and writing its own
record. With no such proof there is one Linux job.

Under `signed`, init asks for the signer emails, writes them to `signers`, asks which rules
need a signature and writes the answer to `sign_at`, prints the commit-signing setup, and
lists every rule with no origin tag so `purlin:spec <name>` can tag them in one pass.

The question it asks is `Which rules need a signature?`, with one line each:

```
strong  the rules whose bar is strong; the rest meet the gate on their tests
all     every rule, whatever its bar
``` Without a signer list the gate cannot be met: the CI gate prints
`→ signer list missing: run purlin:init --gate signed` and exits 1, and `purlin:sign` says the
same and writes nothing.

Anchor pins, the upstream-check job and the dashboard artifact are added on demand. When one
is missing later the tool that needs it says so: `purlin:drift` reports a pin behind,
`purlin:status` says the gate cannot be met without a workflow, and `purlin:audit` says the
breaks engine is unavailable.

## The branch rules

Init prints these; the git host enforces them. Purlin never changes a repository's settings.
**GitHub**, three rulesets so each bypass stays narrow:

1. Require a pull request and require the `purlin` workflow's checks, with the Actions app as
   the only bypass actor. Every run ends with the gate check, so a green check means the gate
   held.
2. Restrict file paths on `.purlin/records/ci/**` and `.purlin/briefs/ci/**`, with the Actions
   app as the only bypass actor, so a person cannot push a record as CI's. The `local/` folders beside them are anyone's.
3. Block force pushes and restrict deletions, with no bypass actor at all.

Under `passed`, print only the third.

**Azure DevOps**, the same three: require a pull request with the purlin pipeline as a build
validation policy, which also ends with the gate check; grant Contribute on those two paths to
the build service alone; deny Force Push and Delete branch for everyone.

## Commit signing under `signed`

A signature counts when the commit that added it is signed, its author email is on the signer
list as of that commit, and that author did not author the commit that last touched the test.
Print these three commands once per signer:

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Then tell them to upload the same public key to the git host as a signing key, so the host
shows the commit as signed. No git-host reviewer setting and no owners file is needed.

The signer list lives in `.purlin/config.json` and changes by pull request like any other file,
so git history records who could sign and when. A signature is judged against the list as it
stood in the commit that added it.

## What CI runs

A project has no copy of Purlin in it, so the workflow init writes clones Purlin at a pinned
tag and runs the run script's own CI arm from that checkout: the same script a person runs, at
a version that changes only when someone edits the workflow. Nobody types that arm; the
workflow carries it. At `passed` the job runs the tagged tests, posts the rollup as a pull
request comment, publishes the dashboard and writes no record. At `strong` and above it audits
what it ran, writes the briefs, and commits them with its record through the git host's API in
one commit. The dashboard and its data go out as the `purlin-dashboard` build artifact linked
from that comment. CI never writes a signature. On a pull request from a fork the API token
cannot write, so the run happens, the comment posts, no commit is made, and the job says so.

## Bringing an older project forward

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init/scaffold.py" --update --project-root .
```

`--update` detects the older layout and offers each change separately. It untracks and deletes
the proof files and the evidence files that used to be committed, untracks the committed
dashboard data, rewrites the hooks, retires the config keys that no longer exist, asks the gate
question once with the three answers above, and rewrites an operating-system tag to `@env(...)`
only where the intended system is unambiguous. Every write asks first, every file it replaces
is backed up beside the original, and while the update is pending `sync_status` opens with
`→ Run: purlin:init --update`.

## When you are done

Say what was written, then name the next step from what the tree shows, not from a script:

- No specs yet: `→ Next: purlin:spec "<one sentence about what the software must do>"`.
- Specs but no tests: `→ Next: purlin:build <name>`.
- Code but no specs: `→ Next: purlin:spec-from-code`.
- Gate raised to `signed` with untagged rules: name them and point at `purlin:spec <name>`.
