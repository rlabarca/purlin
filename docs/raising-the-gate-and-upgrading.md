# Raising the gate, and upgrading

For the developer who set the project up, when the team grows, the obligations change, or a new
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
asks whether the marked tests passed, `strong` asks whether the audit finds those tests sound,
and `signed` asks whether a person signed the rule, the proof and the test together. A cell
above the gate does not exist, which is why raising the gate is what makes a column, a filter or
a tile appear. [hard_gates.md](../references/hard_gates.md) is the one home of the gate.

Raising the gate is additive. On a project that already has a config, init asks before each
write and touches nothing else. Lowering the gate rewrites one setting in `.purlin/config.json`
and deletes nothing: the evidence and the signatures stay where they are, and the cells above
the new gate are not read. A team can drop to `passed` for a spike and come back up without
losing a file.

The gate does not decide whether a project has a remote runner. A runner is written for its own
two reasons, below, so a project can sit at `signed` with no CI at all.

Add `--dry-run` to print every file init would write or edit and write none of them. Read that
list to the team before running it for real on a project that already has code.

## What each raise writes

Init starts from what the project already has, so a raise writes only what is missing.

**At every gate.** `.purlin/config.json` with the gate, the mutation answer, the trust answer,
`audit_parallel` at 4 and the `tests` setting for the detected test framework; `specs/` and
`specs/_anchors/`; `.purlin/evidence/` with its README; a `.gitignore` block for
`.purlin/runtime/`, the dashboard data and the dashboard page; the page itself, copied to
`purlin-report.html`; and, where mutation testing is on, the break engine's config block.

**To `strong`.** `min_strength` becomes 70 where mutation testing is on. What `purlin:audit`
finds now blocks: a rule whose level is `strong` or `signed` meets the gate only when the audit
read its current text, proof and test and found nothing. A rule whose proof is `@manual` joins
the queue as a hand check.

**To `signed`.** `min_strength` becomes 80 where mutation testing is on. Init prints the
commit-signing setup each signer runs once, under `Each signer runs this once, then uploads the
public key to the git host:`. A rule needs a signature exactly when its level is `signed`; a
rule marked `[level: passed]` or `[level: strong]` meets the gate on its lower cells.

Every rule's level is the gate unless the rule carries a `[level: ...]` tag, so raising the
gate raises every unmarked rule with it.

| Flag | What it does |
|------|--------------|
| `--gate <level>` | sets the gate, at setup or later |
| `--mutation` | turns mutation testing on without asking |
| `--add <language>` | adds one more entry to the `tests` setting |
| `--update` | brings a project set up by an older Purlin onto the installed one |
| `--dry-run` | prints the plan and writes nothing |
| `--yes` | takes every default, so mutation testing stays off |

**A runner, at any gate.** Init writes a CI workflow for two reasons and no other: a proof in
`specs/` is tagged `@env` for an operating system this machine is not, or you answered no to
the trust question. The workflow's matrix is `ubuntu-latest`, then one job for each other
operating system the `@env` tags name. Before it writes one, init checks that a git remote
exists and that its URL names GitHub or Azure DevOps; the first that fails is named in one line,
and no workflow is written. It reports the host CLI, `gh` or `az`, as present or absent either
way. [running-and-evidence.md](running-and-evidence.md#when-a-project-has-a-runner) has the
runner in full.

Init ends by printing every file it wrote or edited, one per line, then the next step it read
from the state of the project.

## After the raise

Three things are true the moment the gate reaches `strong`, and it is worth saying them to the
team in the same message:

1. What the audit finds is part of the evidence. `purlin:audit` writes it into each feature's
   `.purlin/evidence/local/<feature>.json`, and `--commit` commits it. `purlin:test` still
   writes the test sections, and they still answer the passed cell.
2. `purlin:audit` is part of the loop. Run it before you push, the way you run `purlin:test`
   while you work: a rule no audit has read reads `not audited` and does not meet the gate.
3. The status table and the board grow a column, a tile and a filter, so nobody configures a
   view. `Strong` joins both at this gate, and `Signed` joins both at the next.

At `signed`, add one more: `purlin:sign` closes its walk by writing the evidence package and the
tag `signed/<version>` when every rule meets the gate, and a person pushes the tag.
[review-and-signing.md](review-and-signing.md#the-tag) has the tag.

[team-workflow.md](team-workflow.md) and [regulated-workflow.md](regulated-workflow.md)
describe the two higher gates in full.

## Upgrading to a new Purlin

```
purlin:init --update
```

Run it after the plugin updates: after a marketplace install refreshed
`~/.claude/plugins/cache/purlin/purlin/<version>/`, or after you pulled the checkout you load
with `claude --plugin-dir <checkout>`. Its migrations read the layout Purlin 0.9.5 left and
land the project on this release's. [RELEASE_NOTES.md](../RELEASE_NOTES.md) says what an upgrade
from 0.9.5 changes.

While a migration is pending, `purlin:status` and every skill that reads it carry `→ Run:
purlin:init --update`, and a skill stops and asks before doing its own work
([purlin_commands.md](../references/purlin_commands.md#pending-migrations)).

```
purlin:init --update --dry-run
```

prints the pending list, one migration per line with the files it touches, writes nothing, and
exits 1 while anything is pending. That is the form to run as a preflight step in CI.

## What the update does

The migrations run in this order, because the tags are rewritten before the workflow matrix is
rendered from them:

| Migration | What it changes |
|-----------|-----------------|
| `design-refs` | deletes each spec's Figma `> Source:` with its `> Pinned:`, and its `> Visual-Reference:` and `> Visual-Hash:` lines |
| `os-tags` | rewrites the 0.9.5 Windows tag in `specs/` to `@env(windows)` |
| `kind-tags` | drops the tag naming the kind of test from every proof line in `specs/` |
| `untracked-files` | deletes the proof files 0.9.5 committed beside the specs and untracks the dashboard data |
| `hooks` | removes the git hooks 0.9.5 installed |
| `config` | writes `.purlin/config.json` at this release's shape, asks the gate, mutation and trust questions, and names every key it drops |
| `evidence` | creates `.purlin/evidence/` with one README saying what it holds |
| `workflows` | removes the workflows 0.9.5 wrote, and writes `purlin.yml` only where the project has a reason for a runner |
| `markers` | rewrites each 0.9.5 marker in the project's tests as one comment above the same test |
| `plugins` | removes the test plugins 0.9.5 copied into the project and the wiring that loaded them |

The `config` migration asks the gate question a new project is asked, offering the gate the
config names as the default:

```
What must be true of every rule before a version is proven?
  passed  every rule's tagged tests pass
  strong  tests pass and the audit finds them sound
  signed  strong, and a person signs each rule
```

Where the config names no `mutation_engine` and an engine exists for the project's frameworks,
the mutation question follows, and the default is no:

```
Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N]
```

The trust question comes last:

```
Do you trust your own machine for the tests and the signing? [y/n]
```

It then says `set the gate to <gate> and dropped <n> keys this release does not read: <keys>`,
and names the `tests` setting it wrote from the frameworks the old config listed and the tree
carries.

The `workflows` migration asks before it writes the new workflow from the template, and says in
one line that it runs on a push to a `run/*` branch and on a push of a `signed/*` tag, and ends
with the gate check.

A spec with no `> Scope:` line is not a migration. The update names each one and changes
nothing: `2 specs have no > Scope: line: a, b. Run purlin:spec <name> to add one. The line is
optional below the gate signed and required at signed.`

## What it asks, and what it keeps

Every migration asks `Apply <id>, which will <what it does>? [y/N]` before it writes. Answer
them one at a time, or pass `--yes` once you have read the `--dry-run` output and want the whole
set applied with every default.

Before the update rewrites or removes a file, it copies the bytes beside it as
`<name>.local-<sha8>.bak` and prints `kept the previous bytes at <path>`. The proof files 0.9.5
committed beside the specs are deleted without a copy: git history holds them. Nothing under
`specs/` loses a rule or a proof; the update rewrites tags and sources inside a spec and never
removes a claim.

Everything the run applied lands in one commit, `chore(update): migrate to <VERSION> (<ids>)`,
naming each migration it applied. It ends on `→ Next: run purlin:status to see where every rule
stands.`, or names the migrations still pending when you skipped one.

Exit codes: 0 when nothing is pending or the run applied what was, 1 for `--dry-run` with
something pending, 2 when the directory has no `.purlin/`.

Read next: [getting-started.md](getting-started.md) if you are setting a project up for the
first time, [team-workflow.md](team-workflow.md) and
[regulated-workflow.md](regulated-workflow.md) for the two higher gates.
