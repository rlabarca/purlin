# Raising the gate, and upgrading

For the engineer who set the project up, when the team grows, the obligations change, or a new
Purlin release lands.

Two things change over a project's life and neither needs a new setup: the gate, which says
what must be true of every rule before a version is proven, and the version of Purlin the
project is wired for. `purlin:init` does both, with `--gate` and `--update`.

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
nothing: the records, the briefs and the signatures all stay where they are, and the gate check
simply stops reading them. So a team can drop to `passed` for a spike and come back up without
losing a file.

Raising the gate never writes a CI workflow. A runner is added for its own two reasons, which
are below, and not because the gate moved: a project can sit at `signed` with no CI at all.

Add `--dry-run` to any of them to print every file init would write or edit and write none of
them. Read that list back to the team before running it for real on a project that already has
code.

## What each raise writes

Init starts from what the project already has, so a raise writes only the missing half.

**To `passed`.** The setting alone, plus what every project gets: `.purlin/config.json` with
the gate and the trust answer, `specs/`, `.purlin/records/` with a README naming what writes
the files in it and saying that nobody edits one by hand, the proof plugin for the detected
test framework, the break engine for the language, a `.gitignore` block for `.purlin/runtime/`,
the dashboard page copied so it opens from disk, and the Claude Code hook that refreshes the
local dashboard data. Nothing to apply on the git host, and no git hook.

**To `strong`.** On top of that: `designs/` with a README, if it is missing, and the breaks,
which turn on with this raise. `min_strength` becomes 70. Below it `purlin:audit` runs the
tests alone, nothing measures a strength, and no record is written at all. From here up the
audit writes one record per feature and the briefs beside them, and commits them.

**To `signed`.** On top of that: the commit-signing setup printed once, for each person who
signs; the question `Which rules need a signature?`, whose answers are `strong`, the
rules whose bar is strong and the rest meeting the gate on their tests, and `all`, every rule
whatever its bar; and a list of every rule that still carries no origin tag, which
`purlin:spec <feature>` tags in one pass. From here `purlin:sign` closes its walk by writing
the tag `signed/<version>` whenever every rule meets the gate.

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
| `--add <language>` | wires a second language: its test framework, its proof plugin, its break engine |
| `--update` | brings a project set up by an older Purlin onto the installed one |
| `--dry-run` | prints the plan and writes nothing |

**A runner, at any gate.** Init writes a CI workflow for two reasons and no other: a proof in
`specs/` is tagged `@env` for an operating system this machine is not, or you answered no to
the trust question. Where one is called for and `specs/` carries `@env(windows)` or
`@env(macos)`, the workflow gets a matrix: a Linux job always, plus one job for each other
operating system named. Before it is written, init checks the prerequisites: a remote exists,
its URL names GitHub or Azure DevOps, and the branch the project works on is on that remote.
The first that fails is named in one line with what to do, and no workflow is written. The host
CLI, `gh` or `az`, is reported as present or absent either way.

Init ends by printing every file it wrote or edited, one per line, then the next step it read
from the state of the project.

## After the raise

Three things are true the moment the gate reaches `strong`, and it is worth saying them to
the team in the same message:

1. A record is now the evidence. `purlin:audit` writes one record per feature it audited and
   the briefs beside them into `.purlin/records/local/` and `.purlin/briefs/local/` and commits
   them itself, on this machine, and it counts. A remote runner writes the same files into the
   `ci/` folders where the project has one, and those count too. `purlin:test` still commits
   the test results, and they still count towards the passed cell.
2. `purlin:audit` is now part of the loop. Run it before you push, the way you run
   `purlin:test` while you work: a rule with no record reads `not audited` and does not meet
   the gate.
3. The status table and the board grow a column, a tile and a filter per level, so nobody
   configures a view. The table and the board carry the same columns, so `Strong` joins both at
   this gate, and `Signable` and `Signed` join both at the next.

At `signed`, add one more: `purlin:sign` closes by writing the tag `signed/<version>` when
every rule meets the gate, and a person pushes it. No tag while any rule falls short, so the
tag is the claim; [hard_gates.md](../references/hard_gates.md) defines it.

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

Eleven migrations, applied in this order, because the tags are rewritten before the setting that
mapped them is dropped and before the workflow matrix is rendered from them:

| Migration | What it changes |
|-----------|-----------------|
| `os-tags` | rewrites the retired operating-system tags in `specs/` to `@env(<os>)` |
| `rule-tags` | rewrites each rule's retired three-level tag as `[bar: passed]` or `[bar: strong]` |
| `design-sources` | points design sources at `designs/<feature>/` |
| `untracked-files` | drops the proof files that used to be committed and untracks the dashboard data |
| `hooks` | removes the git hooks an older Purlin installed, and says why |
| `signer-key` | drops the key an older release used to name who may sign from `.purlin/config.json`, and says so in one line; nothing reads it, because a signature names its signer and no list says who may sign |
| `config` | writes `.purlin/config.json` at the current shape and sets the gate |
| `workflows` | replaces the retired workflows, and re-renders a `purlin.yml` written before the triggers changed |
| `plugin-copies` | refreshes the proof plugin copies under `.purlin/plugins/` |
| `records` | creates `.purlin/records/` for the records an audit commits |
| `record-folders` | moves every record and brief into `.purlin/records/ci/` or `local/`, by who committed it |

The `workflows` migration reads each file under `.github/workflows/`. A workflow an earlier
release wrote under its own name, or one naming something this release moved, is replaced
outright. A `purlin.yml` whose triggers still name a pull request or a branch was written
before the tag became the marker, so the update backs it up beside itself, asks before it
writes, and renders it again from the template. It then says in one line that the new file runs
on a push of a `signed/**` tag and on a push to a `run/*` branch, that its job is named
`purlin`, and that it ends with the gate check.

An operating-system tag is rewritten only where the intended system is unambiguous; anything
else is left for you to decide. The gate question is asked once, during the `config` migration,
with the same three answers a new project is asked:

```
What must be true of every rule before a version is proven?
  passed  every rule has a passing tagged test, from any source
  strong  every rule has a record an audit wrote, at the minimum test strength
  signed  strong, plus a signature from a person on the rule
```

The trust question follows it:

```
Do you trust your own machine for the tests and the signing? [y/n]
```

Under `signed` a second question follows:

```
Which rules need a signature?
  strong  the rules whose bar is strong; the rest meet the gate on their tests
  all     every rule, whatever its bar
```

The `config` migration also drops the settings that named the old gate values and the old list
of people who could sign, and writes nothing in their place: no key names who may sign.

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
attested to. After the update, `purlin:sign` walks the Review and Sign lists and the people who sign sign
again. The old files stay in git history, which is where an inspection reads them.

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
- The dashboard is a page that opens from disk, with no data file in the tree. See
  [dashboard.md](dashboard.md).

Read next: [getting-started.md](getting-started.md) if you are setting a project up for the
first time, [team-workflow.md](team-workflow.md) and
[regulated-workflow.md](regulated-workflow.md) for the two higher gates.
