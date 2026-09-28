# The gate

The gate is the one project setting: what must be true of every rule before a version is
proven. It is defined here and nowhere else. A skill, a doc or a script that needs it links to
this page rather than restating it.

**A gate is two things**, and both must exist for it to mean anything:

1. The setting saying what has to be true of every rule.
2. A marker that says one commit met it, which anyone can check. That marker is the tag:
   `purlin:sign` writes the signed tag `signed/<version>` when every rule meets the gate, and
   no tag is written while one falls short. What the tag means, formally, is below under
   "What `signed/<version>` means".

Setting the first without the second is a preference, not a gate. Where a project has a
remote runner, the push of that tag starts a run that reruns the marked tests on a clean
machine and checks every committed signature and every `ci/` evidence file against the tagged
code, so the tag is a claim someone else can test rather than one you have to take on trust.

## The three levels

A rule answers up to three questions, one per level, and each answer is a **cell**. `gate` in
`.purlin/config.json` says how many of the three the project asks. A rule **meets the gate**
when every cell up to its level is met. `purlin:init` asks the one question that sets it:
`What must be true of every rule before a version is proven?`

| Gate | Who it fits | Cells that exist | What every rule must have |
|------|-------------|------------------|---------------------------|
| `passed` | A developer working alone | passed | Every rule's passed cell is met, on every operating system a current section covered. A pass from either source counts |
| `strong` | A team: product, developers and QA | + strong | Every rule whose level is `strong` or `signed` has a strong cell that is met: the AI audit read its current rule, proof and test and found nothing, and where mutation testing is on the test strength is at or above `min_strength`. Evidence from either source counts |
| `signed` | The same team, with a person's signature on each rule | + signed | Every rule whose level is `signed` has a counting signature |

Each level derives defaults you can override:

| Derived | `passed` | `strong` | `signed` |
|---------|----------|----------|----------|
| `min_strength`, with mutation testing on | unused | 70 | 80 |
| The level of an unmarked rule | `passed` | `strong` | `signed` |

`purlin:init --gate <level>` changes the level later. Raising it adds what is missing and asks
before each write. Lowering it changes the setting and deletes nothing.

Under `passed` no strength is measured, no level above `passed` is read, no queue exists and no
signature is asked for. Mutation testing is a question of its own, off by default, and no gate
turns it on. The breaks run on a person's machine and nowhere else: a runner reruns the tests
and checks the evidence, and evidence either source wrote counts, so the strength a person
measured is the strength every reader sees.

## The level

Every rule has a **level**, `passed`, `strong` or `signed`, meaning what the gate means: its
tests; its tests and the audit; its tests, the audit and a signature. A rule marked
`[level: passed]`, `[level: strong]` or `[level: signed]` asks for what it names, and a rule
with no mark takes the project's gate. The gate is the ceiling: a mark above the gate is read
as the gate, and `purlin:status` says how many rules are marked above it.

The level decides three things and nothing else decides them:

- **Which cells block.** A rule meets the gate when its passed cell is met, its strong cell is
  met if its level is `strong` or `signed`, and its signed cell is met if its level is
  `signed`. A cell above the rule's level is still shown and does not block.
- **Whether the AI audit reads it.** Under the gate `strong` or `signed` the audit reads every
  rule whose level is `strong` or `signed`, and no other. Under the gate `passed` it reads
  every rule, and what it finds blocks nothing.
- **Whether it needs a signature.** A rule needs one exactly when its level is `signed`.

The **queue** is the one list of the rules that wait on a person, each row saying what it
needs. A `hand check` is a rule whose level is `strong` or `signed` and whose strong cell reads
`manual test`. A `signature` is a rule whose level is `signed`, whose passed and strong cells
are met, and that does not have a counting signature. A rule that needs both is one
`hand check` row, and a rule whose level is `passed` is never in the queue.

## Which evidence counts

**The evidence is one file per feature per source.** `purlin:test` runs the marked tests and
writes this operating system's section of `.purlin/evidence/local/<feature>.json` and the
table `.purlin/tests.md`. `purlin:audit` runs the tests and the breaks and writes the same
section plus what the audit found, under `audit`, into the same file. Neither commits unless
you add `--commit`, which commits the evidence under your own identity as
`purlin: evidence at <sha7>`. Neither ever pushes. A remote run writes its own section under
`.purlin/evidence/ci/` and always commits it. A teammate reads the files on the git host
without running anything.

**The folder is the source.** A file's own `source` field must say the same word as the
folder it sits in, and a file where the two disagree is ignored with one warning naming it.
What keeps the `ci/` folder honest is the tag run: it reads the commit that last changed each
file under `ci/` and fails the job where the identity is not the runner's own. The git host
itself does not guard the folder.

| Source | The folder | Counts under |
|--------|------------|--------------|
| `ci` | `.purlin/evidence/ci/<feature>.json`, written by the CI identity through the git host's API | `passed`, `strong`, `signed` |
| `local` | `.purlin/evidence/local/<feature>.json`, written by `purlin:test` and `purlin:audit` on anyone's machine | `passed`, `strong`, `signed` |

**Both sources count at every gate.** What a signature locks is the evidence, not the machine
that produced it: the tests a person ran are the tests a runner runs, and the breaks they
measured are the breaks a runner would measure. A project that wants a runner's word before a
signature says so once, by answering no to init's trust question, and then `purlin:sign`
refuses a rule with a test whose feature has no current `ci` section.

A section describes the checkout while its fingerprint, over the spec, the code the spec's
`> Scope:` covers and the tests, is the one taken now. A pass that is not current makes the
passed cell read `out of date`, naming what changed, and the next run clears it.

## Where a runner runs, and when a project has one

**A project has a remote runner for two reasons and no others.** A proof in `specs/` is
tagged `@env` for an operating system your machine is not, so only a runner can prove it.
Or you answered no to init's trust question, so the tests a signature rests on run on a
clean machine. A project with neither gets no workflow: `purlin:sign` writes the tag, you
push it, and nothing runs remotely.

Where a workflow exists it triggers on two things: a push to a `run/*` branch, which is the
branch `purlin:test --remote` creates and deletes around one run, and a push of a
`signed/<version>` tag, which is what `purlin:sign` writes. `purlin:test --remote` is the one
push Purlin makes, and it pushes a run branch rather than the branch you are on. Every other
push is yours.

| The run | What starts it | What it writes |
|---------|----------------|----------------|
| A remote run | `purlin:test --remote` pushes `run/<branch>-<sha7>` | Its own section of each feature's `.purlin/evidence/ci/<feature>.json`, committed on that branch at every gate. `purlin:test --remote` pulls it home and deletes the branch |
| A tag run | a person pushes `signed/<version>` | Nothing. It reruns the marked tests on a clean machine |

Both runs end with `gate_check.py --check --verify`.

**What the check verifies.** Every signature must still bind the rule, proof, test and audit
it names, so a tag cannot stand over code that changed after it was signed. Every file under
`.purlin/evidence/ci/` must have been committed by the runner's own identity, read off the
commit that last changed it, so a person cannot write evidence as the runner's. A file that
fails either is named under `Evidence` and the job fails.

| Git host | How the runner's identity is read |
|----------|-----------------------------------|
| GitHub | the commit's committer `noreply@github.com` and author `github-actions[bot]`, with a signature that does not contradict them |
| Azure DevOps | `push.pushedBy.id` of the commit, from `_apis/git/repositories/<repo>/commits/<sha>`, against the run's own `authenticatedUser.id` from `_apis/connectionData`, both asked with `SYSTEM_ACCESSTOKEN`. The committer's name is never read |

On Azure DevOps a different id, a commit with no `push`, HTTP 401 or 403, or no answer within
30 seconds fails the file. Off a runner there is no token: the gate check prints `ci/ provenance
is checked by the tag run; this machine has no token.` and counts the files as not checked,
neither passed nor failed. The live behaviour on Azure DevOps is confirmed by a hand-run check
on a machine with Azure DevOps access.

A squash merge or a rebase that rewrites a `ci/` commit breaks the check on either host: the
commit that last changed the file is then a person's.

The breaks run only on a person's machine. Test strength is what `purlin:audit` measures there,
and evidence either source wrote counts at every gate.

## When a signature counts

**Signing is logged, not policed.** Purlin keeps a log you can prove and trace: where the
tests ran, and who signed that the rule, the proof, the test and what the audit found belong
together. It does not decide who may sign. The signature file names the signer, the machine it
was made on and that machine's operating system, and git names the commit's author.

Under `signed` a signature counts when two things are true:

- The commit that added the signature file is cryptographically signed and the signature
  verifies.
- The signature's bound hashes still match the current rule text, proof text, test body and
  what the audit found.

A signature counts on whatever commit carries it, on any branch. Below `signed` a committed
signature counts, and under `strong` what it meets is a `manual test` cell.

**Trust.** `purlin:init` asks `Do you trust your own machine for the tests and the signing?
[y/n]` and writes `trust: local` or `trust: remote`. Under `local`, the default, your own run
is the evidence and `purlin:sign` signs what you ran. Under `remote`, `purlin:sign` refuses a
rule with a test whose feature has no current `ci` section and says to run
`purlin:test --remote` first. Trust binds signing alone: it is read when a rule is signed, and
by no cell and not by the tag. `purlin:init --update` asks again.

`purlin:init --gate signed` prints the one-time signing setup each signer runs. It works with a
single QA person, works the same on both git hosts, and needs nothing configured on the git
host beyond the signer's public key.

A rule needs a signature exactly when its level is `signed`. A rule whose level is lower
still shows its signed cell, and that cell does not keep it from meeting the gate.

## What `signed/<version>` means

This is the one definition of the tag. Every other page points here.

At the tagged commit, every rule meets the gate. A rule meets the gate when the cells its
level asks for are met:

- **Its passed cell**, always, over evidence current for its spec, its code and its tests.
- **Its strong cell**, where its level is `strong` or `signed`.
- **A counting signature**, where its level is `signed`: a signature in a signed commit that
  verifies, whose bound hashes still match the rule, the proof, the test and what the audit
  found. At the gate `signed` a rule whose spec names no files in `> Scope:` has none, because
  a signature cannot be tied to the code it governs.

A rule whose level is below `signed` needs no signature and does not hold the tag back for
one. `trust: remote` is not part of the definition: it is read when a rule is signed, and by no
cell and not by the tag. `purlin:sign` writes the tag only when every rule meets the gate and
every feature's evidence is committed, as a signed tag (`git tag -s`), and never over a tag
that is already there; a person pushes it. The tagged commit carries the evidence package,
`.purlin/evidence/package/<version>.json`, written from the evidence below it
(`references/formats/package_format.md`). Where a project has a remote runner, the push starts
a run that checks the same thing against the tagged code on a clean machine.

## CI writes no signature file

A runner runs the marked tests and, on a run branch, writes its section of the evidence. It
signs nothing. A signature directory holds only files a person wrote, and the tag run checks
that every `ci/` file was committed by the runner itself.

What a runner cannot settle it says out loud. A `@manual` proof makes the strong cell read
`manual test`, and a signature file for the current hashes meets it: a committed one under
`strong`, one in a signed commit under `signed`. The signer writes the one line with `--note`.
An AI audit that could not tell whether the test observes what the proof names makes the cell
read `weak`, with the reason `the AI audit could not decide`; that is build work, and the next
`purlin:audit` reads the rule again. A rule whose level is `strong` or `signed` that no audit
has reached reads `not audited`, and what moves it is `purlin:audit`, not a person.

## What is not a gate

- Writing code without invoking a skill.
- Writing a test with no marker comment above it. It runs; `sync_status` does not count it.
- Committing without running an audit.
- A rule whose passed cell reads `out of date`. The spec, the code or the tests moved; the next
  run clears it.
- A proof tagged `@env` for an operating system this machine is not. It is listed as
  `<os>: no run yet`, and a remote run's matrix proves it.
- Pushing a branch. A push is a person's act, to any branch, and Purlin runs nothing at push
  time or at commit time.

## Platforms

Each section of the evidence names the operating system it ran on. The passed cell lists one
**platform** per operating system a current section covers, each with its own word, its
source and when it ran, and the cell's own word rolls them up. Where the platforms disagree the
cell reads `partial`: a rule whose tests pass on Linux and fail on Windows is neither passed nor
failed, `partial` is not met, and it blocks the gate exactly as a failure does. A rule with a
proof tagged `@env` for an operating system no current section covers reads `not run`, with
the reason `<os>: no run yet`. Test strength is platform independent, because the breaks are
measured once per feature.

## What stands behind an instruction

`.purlin/config.json` is a file in the repository, and an agent can edit it. Every NEVER in
`agents/purlin.md`, the rule that an agent does not push among them, is an instruction to the
agent and not a mechanism that stops it. What stands behind the gate runs outside the agent's
turn: `purlin:sign` writes `signed/<version>` only when every rule meets the gate, and where a
project has a remote runner the tag run reruns the tests on a clean machine and checks the
committed evidence against the tagged code.
