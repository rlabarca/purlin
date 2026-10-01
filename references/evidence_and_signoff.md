# Evidence and sign-off

Purlin keeps two things: the evidence of what the tests saw, and the sign-off a person adds over
it. Everything else it prints is information. This page is the one home of the two facts, of
which evidence counts for a sign-off, of when a sign-off counts and of what `signed/<version>`
means. A skill, a doc or a script that needs one of them links here rather than restating it.

Purlin creates evidence and enforces no policy: it does not decide who may sign, and nothing in
it stops a commit, a push or a merge.

## The two facts

Every surface shows the same two facts: the status's opening lines, the dashboard's two boxes and
the evidence package.

```
Purlin status: labconnect, plugin <version>
Tests: not met
Sign-off: signed 0.1.0, 4 commits since
```

**The tests** read `met` when every rule passes its tests on the committed evidence, and
`not met` otherwise. They read `not met` while any kind of work that blocks is left: a spec to
repair, a test comment to correct, a rule to fix, a rule to write a test for, a rule to test here
or on another system, or results written and not committed.

**The sign-off** reads one of three things, from the newest `signed/*` tag on `HEAD` or an
ancestor of it:

| It reads | When |
|----------|------|
| `signed 0.1.0 at a1b2c3d` | the tag's commit is this code: every commit since it changes only Purlin's own records under `.purlin/` |
| `signed 0.1.0, 4 commits since` | the code has changed since the tag, by that many commits; for one, `1 commit since` |
| `not signed` | no `signed/*` tag is on `HEAD` or behind it |

Neither fact is a bar a rule clears, and no setting changes what either means. Any project may
run `purlin:sign` whenever it chooses.

**Every rule has two cells.** The passed cell says whether every test tied to the rule ran and
passed, each current section answering for the proofs it lists. The strong cell says what the
audit found: `strong`, `weak`, `not audited`, `checked at sign-off` for a hand check, `no proof`,
or `waiting` while the passed cell is not met. Nothing waits on the strong cell.

## What is left to do

The terminal, the dashboard and the evidence package say what is left the same way, with the
summary and `Left to do`:

```
40 rules. 35 pass their tests. The audit found 30 of 35 rules strong (85%).
Left to do:
  3 rules to fix: purlin:build
  2 rules to write a test for: purlin:build
  2 rules to strengthen: purlin:build
```

**The summary** is `<N> rules. <p> pass their tests.`, where `p` counts the rules whose passed
cell reads `passed`, a rule whose every proof is `@manual` among them. Where the audit has read a
rule that passes, ` The audit found <s> of <p> rules strong (<n>%).` follows. A rule is counted
once, under the spec that owns it.

**`Left to do`** lists only work. It gives each rule at most one kind, the first that applies, in
this order. A line carries a count and a command and names no rule; a run names each rule where it
reports the problem. A kind at zero is left out, and the first line is the next step.

| Kind | When it applies | The line | Command | Stops the tests being met |
|------|-----------------|----------|---------|---------------------------|
| `to_repair` | the rule's spec writes a rule or proof number twice or holds a line left from a merge conflict, so every rule of it reads `failed`; the line counts specs | `<n> specs to repair` | `purlin:spec` | yes |
| `no_proof` | the rule's tests pass and no proof line names it | `<n> rules to write a proof for` | `purlin:spec` | no |
| `to_correct` | a comment above a test names nothing a spec has, names a rule that has proofs, or names a proof whose wording changed after the test was last changed; the line counts comments | `<n> test comments to correct` | `purlin:build` | yes |
| `to_fix` | the passed cell reads `failed` or `partial` | `<n> rules to fix` | `purlin:build` | yes |
| `no_test` | the passed cell reads `no test` | `<n> rules to write a test for` | `purlin:build` | yes |
| `to_test` | the passed cell reads `not run` or `out of date`, and this machine can run it | `<n> rules to test` | `purlin:test` | yes |
| `to_test_remote` | the passed cell reads `not run` for a system this machine is not | `<n> rules to test on <systems>` | `purlin:test --remote` | yes |
| `to_commit` | a feature's results are written and not committed, once no other work stops the tests being met; the line counts features | `<n> features whose results are not committed` | `purlin:test --commit` | yes |
| `to_strengthen` | the strong cell reads `weak` | `<n> rules to strengthen` | `purlin:build` | no |

A hand check adds no kind: a person looks at it in the sign-off walk. A count of 1 reads
`1 spec to repair`, `1 rule to fix`, `1 test comment to correct`,
`1 feature whose results are not committed`, and so on. The systems read `Linux/Unix`, `macOS`
and `Windows`, in that order, joined by `, ` and ` and `.

**When the tests are met and this code is not signed**, the status ends on one line:
`Every rule passes its tests on the committed evidence. To sign it: purlin:sign`.

## Which evidence counts

**The evidence is one file per feature per source.** `purlin:test` runs the marked tests and
writes this system's section of `.purlin/evidence/local/<feature>.json`. `purlin:audit` runs the
tests and writes the same section plus what the audit found, under `audit`, into the same file.
Neither commits unless you add `--commit`, which makes two commits under your own identity: first
the specs, the marked tests and the settings the results describe, then the evidence, naming the
first (`references/commit_conventions.md`). Neither ever pushes. A remote run writes its own
section under `.purlin/evidence/ci/` and always commits it. A teammate reads the files on the git
host without running anything.

**The folder is the source.** A file's own `source` field must say the same word as the folder it
sits in, and a file where the two disagree is ignored with one warning naming it. Both sources
count: `ci`, written by a remote runner, and `local`, written by `purlin:test` and `purlin:audit`
on anyone's machine.

**A result counts wherever it ran, and records where.** Each section names the commit of the code
it describes, who ran it, as git's email, and the machine: the host's name for a person's run,
and `remote runner, <system>` for a remote runner's.

**For the status**, a section counts while its fingerprint, over the spec, the code the spec's
`> Scope:` covers and the tests, is the one taken now. A pass that is not current makes the passed
cell read `out of date`, naming what changed, and the next run clears it. An anchor's code is
every file of the project but Purlin's own records under `.purlin/evidence/`, so any other change
to the project makes its results out of date.

**For a sign-off**, a result counts only when it was taken on this exact version of the code: its
section is current, the run saw no uncommitted change, and every commit from the section's commit
to `HEAD` changes only paths under `.purlin/`. A result from a remote run counts on the same
terms. Where one does not, `purlin:sign` refuses and names the run that takes it again:
`purlin:test --all --commit` for this machine's results, `purlin:test --remote` for another
system's. The developer's hand-off is therefore run and commit: every test, here and on the
remote runner for any other system, then the commit of the results that come back.

**An anchor's rule with nothing to check passes, and says so.** Where every test tied to a proof
of an anchor skipped with a reason starting `nothing to check:`, the rule reads `passed`, and the
status, the dashboard and the evidence package show the reason, as in
`security_no_dangerous_patterns RULE-3 passes with nothing to check here: this project has no screens.`
On a feature's own rule the same skip reads `not run`, its reason kept.

## Where a runner runs

**A project has a remote runner for one reason:** a proof in `specs/` is tagged `@env` for a
system your machine is not, so only a runner can prove it. Setup writes no runner file. The first
`purlin:test --remote` writes it for the project's git host, GitHub or Azure DevOps, shows it and
asks before committing it; `purlin:test --remote --commit-runner` commits it and runs.

**Which machine proves which proof.** A remote runner runs only the tests tied to proofs tagged
`@env` for its own system. A person's own machine proves every proof with no `@env` and every
proof tagged for its own system, and never one tagged for another.

The runner starts on one thing: a push to a `run/*` branch, the branch `purlin:test --remote`
creates and deletes around one run. It writes its own section of each feature's
`.purlin/evidence/ci/<feature>.json` and commits it on that branch; `purlin:test --remote` pulls
it home and deletes the branch. That is the one push Purlin makes, and it pushes a run branch
rather than the branch you are on. Every other push is yours.

## When a sign-off counts

**Signing is logged, not policed.** Purlin keeps a record you can prove and trace: where the
tests ran, what the signer was shown, and who signed the package. It does not decide who may
sign; any role may, and several people may sign one version. The system of record decides who was
entitled.

**The evidence package** is one data file, `.purlin/evidence/package/<version>.json`
(`references/formats/package_format.md`), which `purlin:sign` builds from the committed evidence:
every rule's words, proofs, tests and results, what the audit found, who ran the tests and where,
who wrote and last changed each rule, proof and test, the hand checks, and a fingerprint of its
own bytes. `purlin:sign --check <file>` checks a package against its fingerprint.

**The version** is read from the `VERSION` file at the project root, then the `version` of
`package.json`, then `[project]` and then `[tool.poetry]` `version` in `pyproject.toml`, then
`<Version>` in the first `*.csproj` at the root. `purlin:sign --version <version>` names it
instead.

A **sign-off** is one file,
`.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, added in a signed commit by
`purlin:sign` (`references/formats/signature_format.md`). It carries the package's fingerprint,
the commit the package describes, the signer's name and email as git holds them, the time, the
key's fingerprint, what the walk showed, and every note typed. It records no judgment. One file
per signer per version.

A sign-off counts when two things are true:

- The last commit touching its file carries a signature, and that signature verifies over the
  commit. The key is not compared with the signer. An SSH signature is checked with
  `ssh-keygen -Y check-novalidate`, which needs no list of allowed signers, and an OpenPGP one
  with `git verify-commit`. Otherwise it does not count, with
  `the commit that added it is not signed` or
  `the signature on the commit that added it does not verify`.
- Its `package_hash` equals the `fingerprint` of the package committed for that version.

**The sign-off walk.** `purlin:sign` refuses, and writes nothing, while tracked files are
changed and not committed, the evidence is written and not committed, a result was not taken on
this version of the code or was taken while files were changed and not committed, a rule has no
test, a rule does not pass, the version's tag is on other code, or the branch's
copy on the host holds commits the checkout lacks. Otherwise it names who ran the tests, where
and when, shows an overview, offers the audit's findings as a list where a rule reads weak, and
stops only at hand checks, where the signer may type what they saw; an empty answer is recorded
as `no note`. A weak rule or a rule not audited never blocks the sign-off. The first sign-off of
a version is one signed commit carrying the package and the sign-off; a later one adds its own
file alone.

**A hand check** reads `checked at sign-off` everywhere else. Once a sign-off holds a note for
it, the rule also shows its last note, with the version it was signed at and how many commits
have come since, as in
`noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`;
the reader judges whether it still holds.

## What `signed/<version>` means

This is the one definition of the tag. Every other page points here.

**`signed/<version>`** is written by the first counting sign-off of a version, as a signed tag
(`git tag -s`), on that sign-off's commit. It means that at the commit the package describes
every spec could be counted, every rule's tests passed on committed results taken on that exact
version of the code, and at least one person signed the package. The tag binds the signing alone:
it says what was signed and by whom, and makes no claim about who was entitled to sign. A later
sign-off adds its file after the tag, and the tag does not move.

Its message names the version and the commit the package describes:

```
Signed <version>.

Commit: <full sha>
```

No tag is written over one that is already there; code that changed after `signed/<version>` is
signed under a new version. Nothing is pushed: a person pushes the branch and the tag, with the
`git push origin` line the sign-off prints.

## What stops nothing

- Writing code without invoking a skill.
- Writing a test with no marker comment above it. It runs; `sync_status` does not count it.
- Committing without running an audit. The audit is a tool; nothing waits on it.
- A weak rule, or a rule the audit has not read.
- A rule whose passed cell reads `out of date`. The spec, the code or the tests moved; the next
  run clears it.
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

## What stands behind an instruction

`.purlin/config.json` is a file in the repository, and an agent can edit it. Every NEVER in
`agents/purlin.md`, the rule that an agent does not push among them, is an instruction to the
agent and not a mechanism that stops it. What stands behind a sign-off runs outside the agent's
turn: `purlin:sign` builds the package only from committed results taken on this version of the
code, and a sign-off counts only in a signed commit over the committed package's fingerprint.
