# The gate

The gate is the one project setting: the last step every rule must reach before a version is
finished. It is defined here and nowhere else. A skill, a doc or a script that needs it links
to this page rather than restating it.

**A gate is a setting, and at `signed` a marker too:**

1. The setting saying what has to be true of every rule. Every run, every audit and
   `purlin:status` end on the summary and `Left to do`, which say how far the rules have gone
   and what is left before the version is finished.
2. At the gate `signed`, a marker that says one commit is finished, which anyone can check.
   That marker is the tag: `purlin:sign` writes the signed tag `signed/<version>` when nothing
   is left to do and every result came from committed work. Below `signed` no tag is written
   at all. What the tag means, formally, is below under "What `signed/<version>` means".

## The three steps

A rule goes through up to three steps, `passed`, `strong` and `signed`, each containing the one
before, and the answer to each is a **cell**. `gate` in `.purlin/config.json` says how many of
the three the project asks, and every rule is asked what the gate asks. `purlin:init` asks the one
question that sets it: `What must be true of every rule before a version is finished?`

| Gate | Who it fits | Cells that exist | What every rule must have |
|------|-------------|------------------|---------------------------|
| `passed` | A developer working alone | passed | Every test tied to the rule ran and passed, each current section answering for the proofs it lists. A pass from either source counts. A rule with a `@manual` proof is checked by hand |
| `strong` | A team: product, developers and QA | + strong | At least one proof, and a strong cell that is met: the AI audit read its current rule, proof and test and found nothing, and where mutation testing is on the test strength is at or above `min_strength`. Evidence from either source counts |
| `signed` | The same team, with a person's signature on each rule | + signed | A counting signature |

**Test strength is one share per feature**, in every language: the share of the feature's breaks
its tests caught, and every rule of the feature is judged on it. With mutation testing on, a
feature whose share could not be measured leaves its rules `weak` with the reason
`strength not measured: <reason>`, and the reason names the command that fixes it. An engine
that cannot run on this system counts as none, and the AI audit alone decides.

Each gate derives a default you can override:

| Derived | `passed` | `strong` | `signed` |
|---------|----------|----------|----------|
| `min_strength`, with mutation testing on | unused | 70 | 80 |

`purlin:init --gate <gate>` changes the gate later. Raising it adds what is missing. Lowering
it changes the setting and deletes nothing.

Under `passed` no strength is measured and no signature is asked for; a hand check is still
signed, because it stands for the test. Mutation testing is asked about only at `strong` and
`signed`, and is off by default. The breaks run on a person's machine and nowhere else: a
runner reruns the tests, and evidence either source wrote counts, so the strength a person
measured is the strength every reader sees.

## When a version is finished

A version is finished when nothing is left to do: every rule has reached every step up to the
gate, and at `signed` the tag is written. The terminal, the dashboard, a remote runner's test
step and the evidence package say it the same way, with the summary and `Left to do`:

```
40 rules. 35 pass their tests. 30 are strong. 20 are signed.
Left to do:
  5 rules to audit: purlin:audit
  10 rules to sign: purlin:sign
```

**The summary** names the steps up to the gate and no others: `<N> rules. <p> pass their
tests.`, then ` <s> are strong.` at `strong` and `signed`, then ` <g> are signed.` at `signed`.
Each step contains the next. `p` counts the rules whose passed cell reads `passed` and, where a
proof is `@manual`, that are checked by hand; `s` counts those of them whose strong cell reads
`strong`; `g` counts those of them whose signed cell reads `signed`. A rule is counted once,
under the feature that owns it.

**`Left to do`** gives each rule at most one kind, the first that applies, in this order. A
line carries a count and a command and names no rule; a run names each rule where it reports
the problem. A kind at zero is left out, and the first line is the next step. `to_correct`
counts test comments, not rules, and is carried by the project.

| Kind | When it applies | The line | Command |
|------|-----------------|----------|---------|
| `no_proof` | at `strong` and `signed`, no proof line names the rule | `<n> rules to write a proof for` | `purlin:spec` |
| `to_correct` | at every gate, a comment above a test names nothing a spec has, or names a rule that has proofs; each such comment counts once | `<n> test comments to correct` | `purlin:build` |
| `to_fix` | the passed cell reads `failed` or `partial` | `<n> rules to fix` | `purlin:build` |
| `no_test` | the passed cell reads `no test` | `<n> rules to write a test for` | `purlin:build` |
| `to_test` | the passed cell reads `not run` or `out of date`, and this machine can run it | `<n> rules to test` | `purlin:test` |
| `to_test_remote` | the passed cell reads `not run` for a system this machine is not | `<n> rules to test on <systems>` | `purlin:test --remote` |
| `to_test_by_hand` | a proof is `@manual` and the rule is not checked by hand, at any gate | `<n> rules to test by hand` | `purlin:sign` |
| `to_audit` | at `strong` and `signed`, the strong cell reads `not audited` | `<n> rules to audit` | `purlin:audit` |
| `to_measure` | with mutation testing on, the strong cell reads `weak` only because its feature's strength could not be measured | `<n> rules to measure` | `purlin:audit` |
| `to_strengthen` | the strong cell reads `weak`, and not because its spec names no code files | `<n> rules to strengthen` | `purlin:build` |
| `no_scope` | at `signed`, the rule is not signed and its spec names no files; at `strong` and `signed` with mutation testing on, its strong cell reads `weak` because its spec names no code files | `<n> rules to tie to their files` | `purlin:spec` |
| `to_sign` | at `signed`, the signed cell does not read `signed` | `<n> rules to sign` | `purlin:sign` |
| `to_tag` | at `signed`, every other kind is at zero and no `signed/*` tag points at HEAD | `the version to tag` | `purlin:sign` |

A count of 1 reads `1 rule to fix`, `1 rule to tie to its files`, `1 test comment to correct`,
and so on. The systems read `Linux/Unix`, `macOS` and `Windows`, in that order, joined by `, `
and ` and `.

**When nothing is left**, the summary is followed by one line. At `passed` and `strong` it is
`Nothing left to do.` and names no command. At `signed` it names the release step:
`Nothing left to do. Push the tag to release it: git push origin signed/<version>`.

**Purlin refuses nothing a person does.** A person may sign, commit or push at any time. What
Purlin will not do is state that a version is finished when it is not: the tag is the one
statement it withholds, and the lines under "What `signed/<version>` means" say why.

## Which evidence counts

**The evidence is one file per feature per source.** `purlin:test` runs the marked tests and
writes this system's section of `.purlin/evidence/local/<feature>.json` and the table
`.purlin/tests.md`. `purlin:audit` runs the tests and the breaks and writes the same section
plus what the audit found, under `audit`, into the same file. Neither commits unless you add
`--commit`, which makes two commits under your own identity: first the specs, the marked tests
and the settings the results describe, then the evidence, naming the first
(`references/commit_conventions.md`). Neither ever pushes. A remote run writes its own section
under `.purlin/evidence/ci/` and always commits it. A teammate reads the files on the git host
without running anything.

**The folder is the source.** A file's own `source` field must say the same word as the
folder it sits in, and a file where the two disagree is ignored with one warning naming it.

| Source | The folder | Counts under |
|--------|------------|--------------|
| `ci` | `.purlin/evidence/ci/<feature>.json`, written by a remote runner | `passed`, `strong`, `signed` |
| `local` | `.purlin/evidence/local/<feature>.json`, written by `purlin:test` and `purlin:audit` on anyone's machine | `passed`, `strong`, `signed` |

**A result counts wherever it ran, and records where.** Each section names its machine: the
host's name for a person's run, and `remote runner, <system>` for a remote runner's, with the
name the host lent the runner kept beside it. The breaks a person measured are the breaks a
runner would measure.

A section describes the checkout while its fingerprint, over the spec, the code the spec's
`> Scope:` covers and the tests, is the one taken now. A pass that is not current makes the
passed cell read `out of date`, naming what changed, and the next run clears it.

## Where a runner runs, and when a project has one

**A project has a remote runner for one reason:** a proof in `specs/` is tagged `@env` for a
system your machine is not, so only a runner can prove it. A project with no such proof gets no
workflow: at the gate `signed`, `purlin:sign` writes the tag, you push it, and nothing runs
remotely.

Purlin runs tests remotely on GitHub and Azure DevOps. On any other git host the settings read `ci: none`, and setup prints `This git host cannot run tests remotely. Everything on this machine works.`

**Which machine proves which proof.** A remote runner runs only the tests tied to proofs tagged
`@env` for its own system. A person's own machine, Mac or Windows, proves every proof with no
`@env` and every proof tagged for its own system, and never one tagged for another. A runner
file names a remote machine only for a system some proof is tagged for that the machine running
setup is not.

Where a workflow exists it triggers on two things: a push to a `run/*` branch, which is the
branch `purlin:test --remote` creates and deletes around one run, and a push of a
`signed/<version>` tag. `purlin:test --remote` is the one push Purlin makes, and it pushes a
run branch rather than the branch you are on. Every other push is yours.

| The run | What starts it | What it writes |
|---------|----------------|----------------|
| A remote run | `purlin:test --remote` pushes `run/<branch>-<sha7>` | Its own section of each feature's `.purlin/evidence/ci/<feature>.json`, committed on that branch at every gate. `purlin:test --remote` pulls it home and deletes the branch |
| A tag run | a person pushes `signed/<version>` | Nothing. On a clean machine it runs the tests a remote runner runs ("Which machine proves which proof", above), and nothing else |

A run on a ref that is neither a `run/*` branch nor a `signed/*` tag prints
`This run is on <ref>, which is neither a run branch nor a signed tag: the tests ran and nothing is written.`

The test step ends on the summary and `Left to do`, and that ending is what you read. The job
fails only when a test whose result it records fails or could not run; a rule not yet audited
or signed never fails it.

## When a signature counts

**Signing is logged, not policed.** Purlin keeps a log you can prove and trace: where the
tests ran, and who signed that the rule, the proof, the test, the code and what the audit
found belong together. It does not decide who may sign; the system of record decides who was
entitled. The signature file names the signer as git holds them, name and email, the time and
the fingerprint of the key, and not the machine it was signed on.

A signature is made over the rule, its proof, its test, the code the feature's `> Scope:`
lists, what the audit found, and the machine the tests ran on for each system. At every gate
it counts when two things are true:

- The commit that added the signature file carries a signature. Purlin checks that it is
  present and looks no further: any key will do.
- What it was made over is unchanged. Run again on the same machine with nothing changed, the
  signature still counts. A result from a system the signature did not cover is added beside
  the others and ends nothing; a new machine for a system it covered ends it. A remote runner
  is named by its kind, so a second remote run ends nothing.

A signature that no longer matches ends with no message: its cell reads `unsigned`, and the
rule is left to do as `to sign`. A signature counts on whatever commit carries it, on any
branch. An anchor's rule is signed once in each feature it applies to, a change to that
feature's files ends that one signature, and the rule counts as signed when it is signed in
every one of them.

Before signing starts `purlin:sign` confirms only that there is a key to sign with. With none
it shows the commands that set one up, offers to run them, and carries on. When it finishes it
prints `Signed 3 rules as jane@acme.com with the key ending ...Xy4Q.`

## What `signed/<version>` means

This is the one definition of the tag. Every other page points here.

At the tagged commit nothing is left to do at the gate `signed`: every rule's passed cell is
met over evidence current for its spec, its code and its tests, every rule's strong cell is
met, and every rule has a counting signature. At the gate `signed` a rule whose spec names no
files in `> Scope:` cannot be signed, because a signature cannot be tied to the code it
governs.

`purlin:sign` writes the tag only at the gate `signed`, as a signed tag (`git tag -s`), and
never over a tag that is already there. It writes it only when both hold:

- **Nothing is left to do.** While anything is, the tag is not written and the summary and
  `Left to do` say what is left.
- **Every result came from committed work.** `git status --porcelain` lists no path outside
  `.purlin/`, and no evidence file is uncommitted. Otherwise it prints one of these:
  - `No tag: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:sign.`
  - `No tag: <feature> has results that are not committed. Run purlin:test --commit.`

**The version** is read from the `VERSION` file at the project root, then the `version` of
`package.json`, then `[project]` and then `[tool.poetry]` `version` in `pyproject.toml`, then
`<Version>` in the first `*.csproj` at the root. With none of them `purlin:sign` asks for one
and offers to write it to `VERSION`; `--release <name>` names the tag something else.

The tagged commit carries the evidence package, `.purlin/evidence/package/<version>.json`,
written from the evidence below it (`references/formats/package_format.md`). Once the tag is
written `purlin:sign` prints `Tagged signed/<version> at <sha7>.` and then
`Nothing left to do. Push the tag to release it: git push origin signed/<version>`, and a
person pushes it. Below `signed` `purlin:sign` writes no tag and no package.

## CI writes no signature file

A runner runs the tests named under "Which machine proves which proof", above, and, on a run
branch, writes its section of the evidence. It signs nothing. A signature directory holds only
files a person wrote.

What a runner cannot settle it says out loud. A `@manual` proof makes the strong cell read
`manual test`, and the rule is left to do as `to test by hand` until a person checks it and
signs with `purlin:sign`, at any gate, writing what they saw with `--note` when they give one.
An AI audit that could not tell whether the test observes what the proof names makes the cell
read `weak`, with the reason `the AI audit could not decide`; that is build work, and the next
`purlin:audit` reads the rule again. A rule that no audit has reached reads `not audited`, and
what moves it is `purlin:audit`, not a person.

## What is not a gate

- Writing code without invoking a skill.
- Writing a test with no marker comment above it. It runs; `sync_status` does not count it.
- Committing without running an audit.
- A rule whose passed cell reads `out of date`. The spec, the code or the tests moved; the next
  run clears it.
- A proof tagged `@env` for a system this machine is not. It is listed as
  `<System>: no run yet`, and a remote run proves it.
- Pushing a branch. A push is a person's act, to any branch, and Purlin runs nothing at push
  time or at commit time.

## Platforms

Each section of the evidence names the system it ran on, and answers only for the proofs it
lists: a proof a section does not list is neither passed, failed nor `not run` there. The passed
cell lists one **platform** per system a current section covers, each with its own word, its
source and when it ran, and the cell's own word rolls them up. Where two systems that each have
a current section disagree the cell reads `partial`: a rule whose tests pass on Linux/Unix and
fail on Windows is neither passed nor failed, `partial` is not met, and the rule is left to do
as `to fix`, as a failure is. A system a proof is tagged `@env` for with no current section
makes the cell read `not run`, with the reason `<System>: no run yet`, for example
`Windows: no run yet`. Test strength does not depend on the system: the paragraph under the
gate table says how it is measured.

## What stands behind an instruction

`.purlin/config.json` is a file in the repository, and an agent can edit it. Every NEVER in
`agents/purlin.md`, the rule that an agent does not push among them, is an instruction to the
agent and not a mechanism that stops it. What stands behind the gate runs outside the agent's
turn: at the gate `signed`, `purlin:sign` writes `signed/<version>` only when nothing is left
to do and every result came from committed work, and where a project has a remote runner the
tag run reruns the tests on a clean machine.
