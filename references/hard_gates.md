# The gate

The gate is the one project setting: what has to be true of a release. It is defined here and
nowhere else. A skill, a doc or a script that needs it links to this page rather than restating
it.

Purlin creates evidence and enforces no policy about who signs. A release is refused only while a
rule's tests do not pass at the release commit, a spec cannot be read, the working tree holds
uncommitted changes, or the branch's copy on the host holds commits the checkout lacks.

## The two gates

`gate` in `.purlin/config.json` takes one of two values. `purlin:init` asks the one question that
sets it, and `purlin:init --gate <gate>` changes it later.

| Gate | Who it fits | What a release needs |
|------|-------------|----------------------|
| `passed` | A developer alone, or a team that records its sign-off elsewhere | Every rule's tests pass on the evidence committed at the release commit |
| `signed` | A team whose release a person signs | The same, and at least one person signs the evidence package |

**Every rule has two cells at both gates.** The passed cell says whether every test tied to the
rule ran and passed, each current section answering for the proofs it lists; it is the one a
release waits on. The strong cell says what the AI audit found: `strong`, `weak`, `not audited`,
`manual test`, `no proof`, or `waiting` while the passed cell is not met. Nothing waits on it.

**The audit and mutation testing are tools at either gate.** `purlin:audit` reads each rule, its
proofs and its tests, and, where `mutation_engine` is set, breaks the code on purpose to measure
test strength. What they find goes into the evidence and the package where they ran; a weak or
unaudited rule never stops a release or a sign-off. Setup asks about breaking the code at
`signed` alone, where a person reads the audit in the sign-off walk; `purlin:init --mutation`
turns it on at either gate.

**Test strength is one share per feature**, in every language: the share of the feature's breaks
its tests caught, shown on each rule of the feature as `strength 84%`. Where the engine is on and
measured nothing, the strong cell carries `strength not measured: <reason>`, naming the command
that fixes it, and its word stays the audit's. An engine that cannot run on this system counts as
none. No code is broken on purpose for an anchor: the AI audit alone judges its tests, with the
reason `the AI audit alone judges an anchor's tests`.

**A proof** is optional at `passed`, where a test marked with the rule's own id answers a rule
that has none. At `signed` a rule with no proof is left to do as `to write a proof for`, and the
release is not refused for it.

## When a version is finished

A version is finished when nothing is left to do. The terminal, the dashboard, a remote runner's
test step and the evidence package say it the same way, with the summary and `Left to do`:

```
40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.
Left to do:
  3 rules to fix: purlin:build
  2 rules to write a test for: purlin:build
  2 rules to strengthen: purlin:build
```

**The summary** is `<N> rules. <p> pass their tests.`, where `p` counts the rules whose passed
cell reads `passed`, a rule whose every proof is `@manual` among them. Where the audit has read a
rule that passes, ` The audit found <s> strong and <w> weak.` follows; with no rule audited the
sentence stops at the tests. A rule is counted once, under the spec that owns it.

**`Left to do`** lists only work. It gives each rule at most one kind, the first that applies, in
this order. A line carries a count and a command and names no rule; a run names each rule where it
reports the problem. A kind at zero is left out, and the first line is the next step. `to_correct`
counts test comments, not rules, and is carried by the project.

| Kind | When it applies | The line | Command | Stops a release |
|------|-----------------|----------|---------|-----------------|
| `to_repair` | the rule's spec writes a rule or proof number twice or holds a line left from a merge conflict, so every rule of it reads `failed`; the line counts specs, not rules | `<n> specs to repair` | `purlin:spec` | yes |
| `no_proof` | at `signed`, no proof line names the rule | `<n> rules to write a proof for` | `purlin:spec` | no |
| `to_correct` | a comment above a test names nothing a spec has, or names a rule that has proofs; each such comment counts once | `<n> test comments to correct` | `purlin:build` | yes |
| `to_fix` | the passed cell reads `failed` or `partial` | `<n> rules to fix` | `purlin:build` | yes |
| `no_test` | the passed cell reads `no test` | `<n> rules to write a test for` | `purlin:build` | yes |
| `to_test` | the passed cell reads `not run` or `out of date`, and this machine can run it | `<n> rules to test` | `purlin:test` | yes |
| `to_test_remote` | the passed cell reads `not run` for a system this machine is not | `<n> rules to test on <systems>` | `purlin:test --remote` | yes |
| `to_strengthen` | the strong cell reads `weak` | `<n> rules to strengthen` | `purlin:build` | no |

A `@manual` proof adds no kind: a person checks it in the sign-off walk. A count of 1 reads
`1 spec to repair`, `1 rule to fix`, `1 test comment to correct`, and so on. The systems read
`Linux/Unix`, `macOS` and `Windows`, in that order, joined by `, ` and ` and `.

**When nothing is left**, the summary is followed by one line naming the release step:
`Nothing left to do. To release a version: purlin:test --release` at `passed`, and
`Nothing left to do. To release a version: purlin:test --release, then purlin:sign` at `signed`.
Where HEAD carries a `passed/*` or `signed/*` tag, it reads
`Nothing left to do. Push the tag to release it: git push origin <tag>`.

## The release

A release is a commit, its evidence package and a tag, made on a release branch cut from the
default branch once that version's specs are done. `purlin:test --release [<version>]` runs every
test and commits the evidence as `purlin:test --all --commit` does, then checks the release
commit, in this order, stopping at the first that fails with one line and exit 1:

- **Every spec can be counted.** For each spec that writes a number twice or holds a line left
  from a merge conflict:
  `No release: <feature> cannot be counted: <reason>. Run purlin:spec <feature>, then purlin:test --release.`
- **Every rule's tests pass.** A rule whose kind stops a release, and a test comment to correct,
  are named:
  `No release: 2 rules do not pass at 8de0b6e: sample_age RULE-2; stability RULE-1. Run purlin:status to see what is left, then purlin:test --release.`
- **The working tree is committed.**
  `No release: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:test --release.`
- **The branch on the host holds nothing the checkout lacks.** Where the checked-out branch has
  an upstream, or else an `origin/<branch>`, and that ref, as this checkout last fetched it, holds
  commits HEAD does not:
  `No release: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:test --release.`
  Nothing fetches. On a release branch the ref is that release branch's, so the default branch
  moving on does not stop the release.
- **A version is stated**, and the gate's tag for it is not already written.
  `No version: nothing in this project states one. Run purlin:test --release <version>, or write it to a VERSION file.`
  or `No release: passed/1.2.0 is already written. Run purlin:test --release <version> to name another.`

**The version** is read from the `VERSION` file at the project root, then the `version` of
`package.json`, then `[project]` and then `[tool.poetry]` `version` in `pyproject.toml`, then
`<Version>` in the first `*.csproj` at the root. `--release <version>` names it instead.

Then it writes `.purlin/evidence/package/<version>.json` from the evidence at that commit
(`references/formats/package_format.md`), commits it alone as `purlin: evidence at <sha7>`, and
prints `Evidence package committed: .purlin/evidence/package/<version>.json.` A package for the
same version with no tag of the gate yet is written again over the old one.

- **At `passed`** it writes the tag `passed/<version>` on that commit, unsigned, and prints
  `Tagged passed/<version> at <sha7>.`, then
  `Nothing left to do. Push the tag to release it: git push origin passed/<version>`. Where a
  rule has a `@manual` proof it first prints
  `2 rules are checked by hand, and the gate passed records no hand check: accession_screen RULE-1, sample_age RULE-6. The package lists them as not checked.`
- **At `signed`** it writes no tag and prints
  `Run purlin:sign to sign it; the first signature writes signed/<version>.`

The release run fetches nothing and pushes nothing. A person pushes the tag.

## Which evidence counts

**A release uses only the evidence at the release commit.** Evidence may be committed on any
branch at any time; the release run reads what its own commit holds.

**The evidence is one file per feature per source.** `purlin:test` runs the marked tests and
writes this system's section of `.purlin/evidence/local/<feature>.json` and the table
`.purlin/tests.md`. `purlin:audit` runs the tests and the breaks and writes the same section plus
what the audit found, under `audit`, into the same file. Neither commits unless you add
`--commit`, which makes two commits under your own identity: first the specs, the marked tests
and the settings the results describe, then the evidence, naming the first
(`references/commit_conventions.md`). Neither ever pushes. A remote run writes its own section
under `.purlin/evidence/ci/` and always commits it. A teammate reads the files on the git host
without running anything.

**The folder is the source.** A file's own `source` field must say the same word as the folder it
sits in, and a file where the two disagree is ignored with one warning naming it.

| Source | The folder | Counts under |
|--------|------------|--------------|
| `ci` | `.purlin/evidence/ci/<feature>.json`, written by a remote runner | `passed`, `signed` |
| `local` | `.purlin/evidence/local/<feature>.json`, written by `purlin:test` and `purlin:audit` on anyone's machine | `passed`, `signed` |

**A result counts wherever it ran, and records where.** Each section names its machine: the
host's name for a person's run, and `remote runner, <system>` for a remote runner's, with the name
the host lent the runner kept beside it. The breaks a person measured are the breaks a runner
would measure.

A section describes the checkout while its fingerprint, over the spec, the code the spec's
`> Scope:` covers and the tests, is the one taken now. A pass that is not current makes the passed
cell read `out of date`, naming what changed, and the next run clears it. An anchor's code is
every file of the project but Purlin's own records, `.purlin/evidence/` (the package and its
sign-offs among them) and `.purlin/tests.md`, so any other change to the project makes its
results out of date.

## Where a runner runs, and when a project has one

**A project has a remote runner for one reason:** a proof in `specs/` is tagged `@env` for a
system your machine is not, so only a runner can prove it. A project with no such proof gets no
workflow, and nothing runs remotely.

Purlin runs tests remotely on GitHub and Azure DevOps. On any other git host the settings read `ci: none`, and setup prints `This git host cannot run tests remotely. Everything on this machine works.`

**Which machine proves which proof.** A remote runner runs only the tests tied to proofs tagged
`@env` for its own system. A person's own machine, Mac or Windows, proves every proof with no
`@env` and every proof tagged for its own system, and never one tagged for another. A runner file
names a remote machine only for a system some proof is tagged for that the machine running setup
is not.

Where a workflow exists it triggers on two things: a push to a `run/*` branch, which is the branch
`purlin:test --remote` creates and deletes around one run, and a push of a `signed/<version>` tag.
A `passed/<version>` tag starts no run. `purlin:test --remote` is the one push Purlin makes, and
it pushes a run branch rather than the branch you are on. Every other push is yours.

| The run | What starts it | What it writes |
|---------|----------------|----------------|
| A remote run | `purlin:test --remote` pushes `run/<branch>-<sha7>` | Its own section of each feature's `.purlin/evidence/ci/<feature>.json`, committed on that branch at every gate. `purlin:test --remote` pulls it home and deletes the branch |
| A tag run | a person pushes `signed/<version>` | Nothing. On a clean machine it runs the tests a remote runner runs ("Which machine proves which proof", above), and nothing else |

A run on a ref that is neither a `run/*` branch nor a `signed/*` tag prints
`This run is on <ref>, which is neither a run branch nor a signed tag: the tests ran and nothing is written.`

The test step ends on the summary and `Left to do`, and that ending is what you read. The job
fails only when a test whose result it records fails or could not run; a rule the audit has not
read never fails it.

## When a sign-off counts

**Signing is logged, not policed.** Purlin keeps a record you can prove and trace: where the
tests ran, what the signer was shown, and who signed the package. It does not decide who may
sign; any role may, and several people may sign one release. The system of record decides who
was entitled.

A **sign-off** is one file,
`.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, added in a signed commit by
`purlin:sign` (`references/formats/signature_format.md`). It carries the package's fingerprint,
the commit the package describes, the signer's name and email as git holds them, the time, the
key's fingerprint, what the walk showed one by one and in the list, and every note typed. It
records no judgment. One file per signer per version.

A sign-off counts when two things are true:

- The last commit touching its file carries a signature, and that signature verifies over the
  commit. The key is not compared with the signer. An SSH signature is checked with
  `ssh-keygen -Y check-novalidate`, which needs no list of allowed signers, and an OpenPGP one
  with `git verify-commit`. Otherwise it does not count, with
  `the commit that added it is not signed` or
  `the signature on the commit that added it does not verify`.
- Its `package_hash` equals the `fingerprint` of the package committed for that version.

**The sign-off walk.** `purlin:sign` refuses, and writes nothing, while a rule does not pass at
HEAD, no package for the version is committed at HEAD, a commit after the package's touches
anything but that version's sign-offs, the working tree holds uncommitted changes, or the
branch's copy on the host holds commits the checkout lacks. At `passed` it prints
`Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`
Otherwise it shows an overview, then stops where a person has something to look at: each hand
check, where the signer types what they saw; each weak rule; each rule not audited; each shown
with its proofs, its tests' names and bodies, its results and the audit's finding. The rules the
audit found strong are a list the signer can open or walk. A weak or unaudited rule never blocks
the signature. Before signing starts `purlin:sign` confirms only that there is a key to sign with.

## What the tags mean

This is the one definition of the two tags. Every other page points here.

**`passed/<version>`** is written by `purlin:test --release` at the gate `passed`, unsigned
(`git tag -a`), on the commit that carries the evidence package. At that commit every spec can be
counted, every rule's tests pass on the evidence committed there, the working tree was committed,
and the branch's copy on the host, as last fetched, held no commit the checkout lacked. A rule
with a `@manual` proof is listed in the package as not checked.

**`signed/<version>`** is written at the gate `signed` by the first counting sign-off, as a signed
tag (`git tag -s`), on that sign-off's commit. It means everything `passed/<version>` means, and
that at least one person signed the package: the commits between the package and the tag touch
only that version's sign-offs. A later sign-off adds its file after the tag, and the tag does not
move.

The message of either tag names the commit the package describes and the gate:

```
Released at the gate <gate>.

Commit: <full sha>
Gate: <gate>
```

No tag is written over one that is already there. Nothing is pushed: a person pushes the tag,
`git push origin <tag>`.

## What is not a gate

- Writing code without invoking a skill.
- Writing a test with no marker comment above it. It runs; `sync_status` does not count it.
- Committing without running an audit. The audit is a tool; nothing waits on it.
- A weak rule, or a rule the audit has not read.
- A rule whose passed cell reads `out of date`. The spec, the code or the tests moved; the next
  run clears it.
- A proof tagged `@env` for a system this machine is not. It is listed as
  `<System>: no run yet`, and a remote run proves it.
- Pushing a branch. A push is a person's act, to any branch, and Purlin runs nothing at push time
  or at commit time.

## Platforms

Each section of the evidence names the system it ran on, and answers only for the proofs it
lists: a proof a section does not list is neither passed, failed nor `not run` there. The passed
cell lists one **platform** per system a current section covers, each with its own word, its
source and when it ran, and the cell's own word rolls them up. Where two systems that each have a
current section disagree the cell reads `partial`: a rule whose tests pass on Linux/Unix and fail
on Windows is neither passed nor failed, `partial` is not met, and the rule is left to do as
`to fix`, as a failure is. A system a proof is tagged `@env` for with no current section makes the
cell read `not run`, with the reason `<System>: no run yet`, for example `Windows: no run yet`.
Test strength does not depend on the system.

## What stands behind an instruction

`.purlin/config.json` is a file in the repository, and an agent can edit it. Every NEVER in
`agents/purlin.md`, the rule that an agent does not push among them, is an instruction to the
agent and not a mechanism that stops it. What stands behind the gate runs outside the agent's
turn: `purlin:test --release` writes the package and the tag only over a commit whose rules pass,
a sign-off counts only in a signed commit over the committed package's fingerprint, and where a
project has a remote runner the tag run reruns the tests on a clean machine.
