# Raising the gate, and upgrading

For the engineer who set the project up, when the team grows, the obligations change, or a new
Purlin release lands.

Two things change over a project's life and neither needs a new setup: the gate, which says
what CI must see before a change can merge, and the version of Purlin the project is wired for.
`purlin:init` does both, with `--gate` and `--update`.

## Changing the gate

```
purlin:init --gate passed
purlin:init --gate strong
purlin:init --gate signed
```

Each value names one more level of evidence, and each level is one cell on every rule: `passed`
asks whether the tagged tests passed, `strong` asks whether those tests are worth trusting, and
`signed` asks whether a person said the rule, the proof and the test belong together. A cell
above the gate does not exist, which is why raising the gate is what makes a column, a filter or
a tile appear.

Raising the gate is additive. Init adds what is missing, asks before each write, and touches
nothing else. Lowering the gate rewrites one setting in `.purlin/config.json` and deletes
nothing: the workflow, the records, the briefs and the signatures all stay where they are, and
CI simply stops requiring them. So a team can drop to `passed` for a spike and come back up
without losing a file.

Add `--dry-run` to any of them to print every file init would write or edit and write none of
them. Read that list back to the team before running it for real on a project that already has
code.

## What each raise writes

Init starts from what the project already has, so a raise writes only the missing half.

**To `passed`.** The setting alone, plus what every project gets: `.purlin/config.json`,
`specs/`, `.purlin/records/` with a README naming what writes the files in it and saying that
nobody edits one by hand, the
proof plugin for the detected test framework, the break engine for the language, a `.gitignore`
block for `.purlin/runtime/`, the dashboard page copied so it opens from disk, the offer of a
`pre-push` hook, and the Claude Code hook that refreshes the local dashboard data. No CI
workflow is written at this gate unless you ask for one: with a remote, init prints the three
reasons a remote runner is worth having and asks `Run the tests on a remote runner too? [y/n]`.
The only branch rule printed here is the third one: no force push, no deletion.

**To `strong`.** On top of that: the CI workflow at `.github/workflows/purlin.yml`, because a
gate is a job plus a branch rule and without the job there is nothing for the rule to require.
The workflow starts on a pull request, on
a push to your default branch and on a push to a `run/*` branch, and every run of it ends with
`scripts/ci/gate_check.py --check`, which fails the job when the gate is not met. `designs/`
with a README, if it is missing. The two remaining branch rules, printed for you to apply on
the git host: require a pull request and the `purlin` check with the Actions app as the only
bypass, and restrict `.purlin/records/ci/**` and `.purlin/briefs/ci/**` to the Actions app. If any
proof in `specs/` carries `@env(windows)` or `@env(macos)`, the workflow gets a matrix: a Linux
job always, plus one job for each other operating system named. With no such tag there is one
Linux job.

The breaks turn on with this raise, locally and in CI, and `min_strength` becomes 70. Below it
`purlin:audit` runs the tests alone, nothing measures a strength, and no record is written at
all.

**To `signed`.** On top of that: the signer emails, which init asks for with `Who may sign a
rule?` and writes to `signers` in `.purlin/config.json`; the commit-signing setup printed once
per signer; the question `Which rules need a signature?`, whose answers are `strong`, the
rules whose bar is strong and the rest meeting the gate on their tests, and `all`, every rule
whatever its bar; and a list of every rule that still carries no origin tag, which
`purlin:spec <feature>` tags in one pass.

The derived defaults move too: `min_strength` becomes 80, and `sign_at` takes the answer you
gave, `strong` by default. A rule whose bar is `passed` under `sign_at: strong` needs no
signature: it meets the gate once its tests pass, and a signature written anyway still counts.

Every rule's **bar** is `strong` at both of the upper gates unless the rule carries a
`[bar: passed]` tag, so raising the gate is also what turns the AI audit on. Before 0.10.0 a
rule carried a three-level tag in place of a bar; `--update` rewrites it, the two higher
levels to `[bar: strong]` and the lowest to `[bar: passed]`, and the signature hashes follow
the bar as they followed the old tag.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | sets the gate, at setup or later |
| `--upstream-check` | adds a scheduled job that opens a pull request or an issue when an anchor pin falls behind |
| `--add <language>` | wires a second language: its test framework, its proof plugin, its break engine |
| `--update` | brings a project set up by an older Purlin onto the installed one |
| `--dry-run` | prints the plan and writes nothing |

Before any workflow is written, init checks the prerequisites: a remote exists, its URL names
GitHub or Azure DevOps, and the protected branch is on that remote. The first that fails is
named in one line with what to do, and no workflow is written. The host CLI, `gh` or `az`, is
reported as present or absent either way.

Init ends by printing every file it wrote or edited, one per line, then the next step it read
from the state of the project.

## After the raise

Three things are true the moment the gate reaches `strong`, and it is worth saying them to
the team in the same message:

1. A record is now the evidence, and two hands write one. `purlin:audit` writes one record per
   feature it audited and the briefs beside them into `.purlin/records/local/` and
   `.purlin/briefs/local/` and commits them itself; CI writes the same files into the `ci/`
   folders on a push to the protected branch and on the run branch `purlin:test --remote`
   creates. Both count at `strong`. A pull request run does the tests, posts the comment and
   commits nothing. `purlin:test` still commits the test results, and they still count towards
   the passed cell.
2. Apply the branch rules init printed. Purlin never changes a repository's settings, so until
   someone applies them the gate is a preference rather than a control.
3. The status table and the board grow a column, a tile and a filter per level, so nobody
   configures a view. `Strength` joins the status table and `Strong` joins the board at this
   gate; `Signed` appears at the next.

At `signed`, add two more: only CI's tests and CI's audit count there, so a local record
becomes a preview, and signing commits reach the default branch by pull request like any other
change, with a merge waiting for them.

[team-workflow.md](team-workflow.md) and [regulated-workflow.md](regulated-workflow.md)
describe the two higher gates in full.

## Upgrading to a new Purlin

```
purlin:init --update
```

Run it after the plugin updates: after a marketplace install refreshed
`~/.claude/plugins/cache/purlin/purlin/<version>/`, or after you pulled the checkout you load
with `claude --plugin-dir <checkout>`. It detects what an older Purlin left behind and offers
each change separately. The layout it reads is the one v0.9.5 left, and it lands the project
straight on the current one.

While anything is pending, every skill says so before doing its own work: `purlin:status` and
the rest open with a pending-migrations advisory naming each migration, its count, the files it
counted, and `→ Run: purlin:init --update`. A spec written against a reading the installed
plugin has moved on from is a spec written against an answer the next release drops, which is
why the advisory interrupts rather than waits.

```
purlin:init --update --check
```

prints the same list and writes nothing, and exits 1 while anything is pending. That is the
form to run as a preflight step in CI.

## What the update does

Eight migrations, applied in this order, because the tags are rewritten before the setting that
mapped them is dropped and before the workflow matrix is rendered from them:

| Migration | What it changes |
|-----------|-----------------|
| `os-tags` | rewrites the retired operating-system tags in `specs/` to `@env(<os>)` |
| `design-sources` | points design sources at `designs/<feature>/` |
| `untracked-files` | drops the proof files that used to be committed and untracks the dashboard data |
| `hooks` | drops the pre-commit hook and repoints the pre-push shim |
| `config` | writes `.purlin/config.json` at the current shape and sets the gate |
| `workflows` | replaces the retired workflows, and re-renders a `purlin.yml` written before the triggers changed |
| `plugin-copies` | refreshes the proof plugin copies under `.purlin/plugins/` |
| `records` | creates `.purlin/records/` for the records an audit commits |

The `workflows` migration reads each file under `.github/workflows/`. A workflow an earlier
release wrote under its own name, or one naming something this release moved, is replaced
outright. A `purlin.yml` that carries no `scripts/ci/gate_check.py` step was written before CI
started deciding where evidence lands, so its triggers still start a run on every branch and no
run of it ends with the gate; the update backs it up beside itself, asks before it writes, and
renders it again from the template with your default branch in the triggers. It then says in
one line that the new file runs on a pull request, on a push to that branch and on a push to a
`run/*` branch, and ends with the gate check. A `purlin.yml` that already has the step is left
alone.

An operating-system tag is rewritten only where the intended system is unambiguous; anything
else is left for you to decide. The gate question is asked once, during the `config` migration,
with the same three answers a new project is asked:

```
What must be true before CI lets a change merge?
  passed  every rule has a passing tagged test, from any source
  strong  every rule has a record an audit wrote, at the minimum test strength
  signed  strong, plus a signature from a person on the rule
```

Under `signed` a second question follows:

```
Which rules need a signature?
  strong  the rules whose bar is strong; the rest meet the gate on their tests
  all     every rule, whatever its bar
```

The `config` migration also drops the settings that named the old gate values and the old list
of people who could sign, and writes `signers` in their place when you answer `signed`.

## What it asks, and what it keeps

Every migration asks before it writes. Answer them one at a time, or pass the "yes to
everything" answer when you have read the `--check` output and want the whole set applied.

Every file the update rewrites is copied beside itself first, as `<name>.local-<sha8>.bak`, so
the version you had is on disk next to the version you now have. A file this release deletes
rather than rewrites is not copied: it is already in git history, which is the better copy.

Nothing under `specs/` loses a rule or a proof. The update rewrites tags and sources inside a
spec; it never removes a claim.

The one thing it does not carry forward is the old evidence a person wrote. The files v0.9.5
left beside the specs bound hashes this release computes differently, and the words they were
written in are gone, so the update drops them rather than converting them into something nobody
attested to. After the update, `purlin:sign` walks the Review and Sign tabs and the people on the signer
list sign again. The old files stay in git history, which is where an inspection reads them.

Exit codes: 0 when nothing is pending or the run applied what was, 1 for `--check` with
something pending, 2 when the directory is not a Purlin project.

## Coming from v0.9.5

A v0.9.5 project meets the update with committed proof files, committed evidence files, a
committed dashboard data file, a pre-commit hook, the older workflows, and settings for things
this release does not have. The single command above handles all of it. What is worth knowing
before you run it:

- The grading scores and the reviewer agent that produced them are gone. `purlin:sign` is where
  a person now looks at a rule, and [review-and-signing.md](review-and-signing.md) describes
  what it shows.
- Evidence moved from files written beside the specs to the test results under
  `.purlin/tests/`, which `purlin:test` commits, and the records under `.purlin/records/`, one
  per audit run, filed under `ci/` or `local/` by source, with the briefs beside them under
  `.purlin/briefs/`.
  [running-and-records.md](running-and-records.md) has both shapes.
- Operating-system scoping is now `@env(windows|macos|linux)` and a CI matrix, with no registry
  to maintain and no per-system evidence file.
- The dashboard is a build artifact CI publishes and a page that opens from disk, with no data
  file in the tree. See [dashboard.md](dashboard.md).

Read next: [getting-started.md](getting-started.md) if you are setting a project up for the
first time, [team-workflow.md](team-workflow.md) and
[regulated-workflow.md](regulated-workflow.md) for the two higher gates.
