# Raising the gate, and upgrading

For the engineer who set the project up, when the team grows, the obligations change, or a new
Purlin release lands.

Two things change over a project's life and neither needs a new setup: the gate, which says
what CI must see before a change can merge, and the version of Purlin the project is wired for.
`purlin:init` does both, with `--gate` and `--update`.

## Changing the gate

```
purlin:init --gate tested
purlin:init --gate recorded
purlin:init --gate approved
```

Raising the gate is additive. Init adds what is missing, asks before each write, and touches
nothing else. Lowering the gate rewrites one setting in `.purlin/config.json` and deletes
nothing: the workflow, the records and the approvals all stay where they are, and CI simply
stops requiring them. So a team can drop to `tested` for a spike and come back up without
losing a file.

Add `--dry-run` to any of them to print every file init would write or edit and write none of
them. Read that list back to the team before running it for real on a project that already has
code.

## What each raise writes

Init starts from what the project already has, so a raise writes only the missing half.

**To `tested`.** The setting alone, plus what every project gets: `.purlin/config.json`,
`specs/`, `.purlin/records/` with a README saying verify writes it and nobody edits it by
hand, the proof plugin for the detected test framework, the break engine for the language, a
`.gitignore` block for `.purlin/runtime/`, the dashboard page copied so it opens from disk, the
offer of a `pre-push` hook, and the Claude Code hook that refreshes the local dashboard data.
There is no CI workflow at this gate; `purlin:init --ci` adds one anyway if you want the
check without the requirement.

**To `recorded`.** On top of that: the CI workflow at `.github/workflows/purlin.yml`, because
the gate cannot be met without a run that writes records. `designs/` with a README, if it is
missing. The branch rules printed for you to apply on the git host. If any proof in `specs/`
carries `@env(windows)` or `@env(macos)`, the workflow gets a matrix: a Linux job always, plus
one job for each other operating system named. With no such tag there is one Linux job.

**To `approved`.** On top of that: the approver emails, which init asks for and writes to
`approvers` in `.purlin/config.json`; the commit-signing setup printed once per approver; and a
list of every rule that still carries no risk or origin tag, which `purlin:spec <feature>` tags
in one pass. The derived defaults move too, so `min_strength` becomes 80 and the model review
runs at medium risk as well as high.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | sets the gate, at setup or later |
| `--ci` | writes the CI workflow under `tested`, where it is otherwise skipped |
| `--ci --upstream-check` | adds a scheduled job that opens a pull request or an issue when an anchor pin falls behind |
| `--add <language>` | wires a second language: its test framework, its proof plugin, its break engine |
| `--update` | brings a project set up by an older Purlin onto the installed one |
| `--dry-run` | prints the plan and writes nothing |

Init ends by printing every file it wrote or edited, one per line, then the next step it read
from the state of the project.

## After the raise

Three things are true the moment the gate reaches `recorded`, and it is worth saying them to
the team in the same message:

1. Stop committing records. Only a record CI wrote counts now. Your local `purlin:verify` is a
   preflight, not evidence.
2. Apply the branch rules init printed. Purlin never changes a repository's settings, so until
   someone applies them the gate is a preference rather than a control.
3. The status table and the dashboard grow columns as the artifacts appear, so nobody
   configures a view. A records column appears once records exist; an approvals column once
   approvals do.

At `approved`, add a fourth: approval commits reach the default branch by pull request like any
other change, and a merge waits for them.

[team-workflow.md](team-workflow.md) and [regulated-workflow.md](regulated-workflow.md)
describe the two higher gates in full.

## Upgrading to a new Purlin

```
purlin:init --update
```

Run it after the plugin updates: after a marketplace install refreshed
`~/.claude/plugins/cache/purlin/purlin/<version>/`, or after you pulled the checkout you load
with `claude --plugin-dir <checkout>`. It detects what an older Purlin left behind and offers
each change separately. It reads both older layouts: the one v0.9.5 left, and the one the 0.10
development branch left, so a project part-way through either is a case it handles rather than
a case it refuses.

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
| `workflows` | replaces the retired workflows with `purlin.yml` |
| `plugin-copies` | refreshes the proof plugin copies under `.purlin/plugins/` |
| `records` | creates `.purlin/records/`, where verify commits one file per run |

An operating-system tag is rewritten only where the intended system is unambiguous; anything
else is left for you to decide. The gate question is asked once, during the `config` migration,
with the same three answers a new project is asked:

```
What must be true before CI lets a change merge?
  tested    every rule has a passing tagged test
  recorded  CI writes a record at this commit, at or above the minimum strength
  approved  recorded, plus a current approval on every high and medium risk rule
```

## What it asks, and what it keeps

Every migration asks before it writes. Answer them one at a time, or pass the "yes to
everything" answer when you have read the `--check` output and want the whole set applied.

Every file the update rewrites is copied beside itself first, as `<name>.local-<sha8>.bak`, so
the version you had is on disk next to the version you now have. A file this release deletes
rather than rewrites is not copied: it is already in git history, which is the better copy.

Nothing under `specs/` loses a rule, a proof or an approval. The update rewrites tags and
sources inside a spec; it never removes a claim.

Exit codes: 0 when nothing is pending or the run applied what was, 1 for `--check` with
something pending, 2 when the directory is not a Purlin project.

## Coming from v0.9.5

A v0.9.5 project meets the update with committed proof files, committed verification files, a
committed dashboard data file, a pre-commit hook, the older workflows, and settings for things
this release does not have. The single command above handles all of it. What is worth knowing
before you run it:

- The grading scores and the reviewer agent that produced them are gone. `purlin:review` is
  where a person now looks at a rule, and [review-and-approval.md](review-and-approval.md)
  describes what it shows.
- Evidence moved from files written beside the specs to records under `.purlin/records/`, one
  per verify run, committed. [running-and-records.md](running-and-records.md) has the shape.
- Operating-system scoping is now `@env(windows|macos|linux)` and a CI matrix, with no registry
  to maintain and no per-system evidence file.
- The dashboard is a build artifact CI publishes and a page that opens from disk, with no data
  file in the tree. See [dashboard.md](dashboard.md).

Read next: [getting-started.md](getting-started.md) if you are setting a project up for the
first time, [team-workflow.md](team-workflow.md) and
[regulated-workflow.md](regulated-workflow.md) for the two higher gates.
