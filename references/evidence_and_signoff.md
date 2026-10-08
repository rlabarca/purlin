# Evidence and sign-off

Purlin keeps two things: the evidence of what the tests saw, and the sign-off a person adds over
it. Everything else it prints is information. This page is the one home of the two facts, of
which evidence counts for a sign-off, of when a sign-off counts and of what `signed/<version>`
means. A skill, a doc or a script that needs one of them links here rather than restating it.

Purlin creates evidence and enforces no policy: it does not decide who may sign, and nothing in
it stops a commit, a push or a merge.

## The two facts

Every surface shows the same two facts: the status's opening lines, the dashboard's first two boxes and
the evidence package.

```
Purlin status: labconnect, plugin <version>
Tests: not met
Sign-off: signed 0.1.0, 4 commits since
```

**The tests** read `met` when every rule passes its tests on the committed evidence, and
`not met` while any kind of work that blocks is left, as the table under "What is left to do"
marks. A rule checked by hand alone reads `checked at sign-off`, is counted under no kind of
work and never stops the tests reading `met`.

**The sign-off** reads one of three things, for the newest version whose sign-off counts, found
by its `signed/*` tag on `HEAD` or an ancestor of it, or by its sign-off files where this
checkout holds no such tag:

| It reads | When |
|----------|------|
| `signed 0.1.0 at a1b2c3d` | the tag's commit is this code: every commit since it changes only Purlin's own records under `.purlin/` and leaves the `tests` setting as it was |
| `signed 0.1.0, 4 commits since` | the code has changed since the tag, by that many commits; for one, `1 commit since` |
| `not signed` | no version has a sign-off that counts |

Neither fact is a bar a rule clears, and no setting changes what either means. Any project may
run `purlin:sign` whenever it chooses.

**Every rule has two cells.** The passed cell says whether every test tied to the rule ran and
passed, and the strong cell says what the audit found; `references/glossary.md` lists the words
each can read. A rule that passes with a proof a model grades reads `graded`, not `passed`, and
counts as passing everywhere. The passed cell lists one platform per system a current section
covers, and reads `partial` where two of them disagree. Nothing waits on the strong cell.

## What is left to do

The terminal, the dashboard and the evidence package say what is left the same way, with the
summary and `Left to do`:

```
40 rules. 35 pass their tests. The audit found 30 of 35 rules strong (85%): 30 strong, 2 weak, 3 spot-checked.
Left to do:
  3 rules to fix: purlin:build
  2 rules to write a test for: purlin:build
  2 rules to strengthen: purlin:build
```

**The summary** is `<N> rules. <p> pass their tests.`, where `p` counts the rules whose passed
cell reads `passed` or `graded`. Where one reads `graded` the sentence says how many:
`40 rules. 40 pass their tests, 6 of them graded by an AI.`, or `1 of them graded by an AI.`
Where a rule's passed cell reads `checked at sign-off`,
` 1 is checked at sign-off.` follows, or ` <h> are checked at sign-off.` for more than one:
`10 rules. 9 pass their tests. 1 is checked at sign-off.` Where the audit has read a
rule that passes, ` The audit found <s> of <a> rules strong (<n>%): <s> strong` follows, `a`
counting the rules that pass their tests, have a tested proof and are not an anchor's, read by
the audit or not, then
`, <n> weak`, `, <n> spot-checked`, `, <n> out of date` and `, <n> not audited`, each only where
it is not zero. Those counts take in an anchor's rules. Where `a` counts no rule, the part is
` The audit found <counts>.`, as `The audit found 8 spot-checked.` A rule is counted once, under
the spec that owns it.

**`Left to do`** lists only work. It gives each rule at most one kind, the first that applies, in
this order. A line carries a count and a command and names no rule; a run names each rule where it
reports the problem. A kind at zero is left out, and the first line is the next step.

| Kind | When it applies | The line | Command | Stops the tests being met |
|------|-----------------|----------|---------|---------------------------|
| `to_repair` | the rule's spec writes a rule or proof number twice, holds a line left from a merge conflict, or carries an `@ai` or `@graded` tag that names no model, a model's name that cannot be read or a `@graded` with no `@ai` (`references/formats/spec_format.md`, "The AI tags"), so every rule of it reads `failed`; the line counts specs | `<n> specs to repair` | `purlin:spec` | yes |
| `no_proof` | the rule's tests pass and no proof line names it | `<n> rules to write a proof for` | `purlin:spec` | no |
| `to_correct` | a comment above a test names nothing a spec has, names a rule that has proofs, or names a proof whose wording changed after the test was last changed; the line counts comments | `<n> test comments to correct` | `purlin:build` | yes |
| `to_fix` | the passed cell reads `failed` or `partial` | `<n> rules to fix` | `purlin:build` | yes |
| `no_test` | the passed cell reads `no test`: a proof of the rule has no test, or the rule has no proof and no test, with the reason `no proof written` | `<n> rules to write a test for` | `purlin:build` | yes |
| `to_test` | the passed cell reads `not run` or `out of date`, and this machine can run it | `<n> rules to test` | `purlin:test` | yes |
| `to_run_slow` | a proof tagged `@slow` reads `not run`: no run that starts its test has answered for the spec, code and tests as they stand; the line counts proofs, and a rule that waits for such proofs alone is counted here and not under `to_test`. An AI proof, one tagged `@ai`, is a slow proof, and one no run has tried on any model is counted here | `<n> slow proofs to run` | `purlin:test --all` | yes |
| `to_test_model` | an AI proof a run has tried holds no counting result on a model its tag names: no entry for the model, a model run that is `not run`, or fewer model runs than are asked now; one line per model, a rule counted on each model it waits for | `<n> rules to test on <model>` | `purlin:test --all` | yes |
| `to_test_remote` | the passed cell reads `not run` for a system this machine is not | `<n> rules to test on <systems>` | `run purlin:test on <systems>` | yes |
| `to_commit` | a feature's results are written and not committed, once no other work stops the tests being met; the line counts features | `<n> features whose results are not committed` | `purlin:test --commit` | yes |
| `to_strengthen` | the strong cell reads `weak` | `<n> rules to strengthen` | `purlin:build` | no |

A hand check adds no kind: a person looks at it in the sign-off walk. A count of 1 reads
`1 spec to repair`, `1 rule to fix`, `1 test comment to correct`,
`1 feature whose results are not committed`, `1 rule to test on claude-opus-5-5`, and so on. The systems read `Linux/Unix`, `macOS`
and `Windows`, in that order, joined by `, ` and ` and `.

`run purlin:test on <systems>` is an instruction, not a command line: no command takes a system.
It is met by `purlin:test` on a machine of that system, or by the project's own run there
("A run on another system", below).

**When the tests are met and this code is not signed**, the status ends on one line:
`Every rule passes its tests on the committed evidence. Optional: sign this version with purlin:sign`.
A sign-off is optional. Nothing waits on it, and a project that never signs still reads
`Tests: met`.

**Where `purlin:sign` would refuse those results as they stand**, that line names the run to
make first. For a result not recorded on this version of the code, one whose section names a
commit after which a commit changes a file outside `.purlin/`, it reads
`Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results recorded on this version of the code.`
For a result from a project's own run on another system the command reads
`purlin:test on <systems>`. For a result taken while files were changed and not committed the
line ends `a sign-off counts only results taken with nothing uncommitted.`

## Which evidence counts

**The evidence is one file per feature per source.** `purlin:test` runs the marked tests and
writes this system's section of `.purlin/evidence/local/<feature>.json`. `purlin:audit` runs the
tests and writes the same section plus what the audit found, under `audit`, into the same file.
Neither commits unless you add `--commit`, which makes two commits under your own identity: first
the specs, the marked tests and the settings the results describe, then the evidence, naming the
first (`references/commit_conventions.md`). Neither ever pushes. A run on another system writes
its own section under `.purlin/evidence/ci/` and commits it with `--commit`. A teammate reads
the files on the git host without running anything.

**The folder is the source.** A file's own `source` field must say the same word as the folder it
sits in, and a file where the two disagree is ignored with one warning naming it. Both sources
count: `ci`, written by a project's own run on another system, and `local`, written by
`purlin:test` and `purlin:audit` on anyone's machine.

**A result counts wherever it ran, and records where.** Each section names the commit of the code
it describes, who ran it, as git's email, and the machine, which is the host's name under both
sources.

**For the status**, a section counts while its fingerprint, over the spec, the code the spec's
`> Scope:` covers and the tests, is the one taken now. A pass that is not current makes the passed
cell read `out of date`, naming what changed, and the next run clears it. An anchor's code is
every file of the project but Purlin's own records under `.purlin/evidence/`, so any other change
to the project makes its results out of date. Changing a test command in `.purlin/config.json`
ends the results, as changing the code does. Changing `version` alone does not.

**For a sign-off**, a result counts only when it is recorded on this exact version of the code:
its section is current, the run saw no uncommitted change, and every commit from the section's
commit to `HEAD` changes only paths under `.purlin/` and leaves the test commands as they were.
A result from a run on another system counts on the same terms. Where one does not,
`purlin:sign` refuses and names the run that records it: `purlin:test --all --commit` for this
machine's results, and `purlin:test on <System>` for another system's, the same instruction as
in `Left to do`. A project tested in part is refused, so a tag always covers the whole project.

**`purlin:test --all --commit` runs what changed and carries the rest forward.** It runs each
feature whose spec, code or tests changed since its results were taken, each feature whose
results are not all passes, and every anchor. Every other feature it carries forward: its
results are recorded again on this commit, each marked `carried` with the commit, the time, the
machine and the person of the run that took it, and none of its tests run. A result from
another system is carried the same way, from whichever machine took it, and so is a slow
proof's. A carried result counts for a sign-off like one taken now, and the evidence, the
package, the status, the dashboard and the sign-off walk say which commit it was taken at.
`purlin:test --clean` runs every test and carries nothing. A plain `purlin:test` that leaves a
slow proof's test out carries its result the same way while nothing its spec covers changed.
`references/formats/evidence_format.md`, "Carried forward", gives the test a section must meet.

The developer's hand-off is therefore run and commit: `purlin:test --all --commit` here, the
project's own run for any other system whose results changed, then the commit of the results
that come back.

**An AI proof counts per model.** A proof tagged `@ai(<model>, ...)` is run several times on
each model it names, and passes when every model run on every model passed
(`references/formats/evidence_format.md`, "The models of an AI proof"). The tests are not `met`
while a model it names has no counting result. A model that gave no answer reads `not run`,
never `failed`. `purlin:sign` refuses while one has no counting result on the commit to sign:
`No sign-off: these results are not recorded on this version of the code, <sha7>: <feature> on <model>. Run purlin:test --all --commit, then purlin:sign.`

**An anchor's rule with nothing to check passes, and says so.** Where every test tied to a proof
of an anchor skipped with a reason starting `nothing to check:`, the rule reads `passed`, and the
status, the dashboard and the evidence package show the reason, as in
`security_no_dangerous_patterns RULE-3: nothing to check here. It passes: this project has no screens.`
On a feature's own rule the same skip reads `not run`, its reason kept.

## A run on another system

**Purlin runs the tests where you are.** It starts no run on another machine, drives no pipeline
and adds no file for a git host to a project. A project needs a run somewhere else for one
reason: a proof in `specs/` is tagged `@env` for a system the machines at hand are not.

**Which machine proves which proof.** An untagged proof is proven by `purlin:test` on any
machine. A proof tagged `@env(<system>)` is proven only by a run on that system: `purlin:test`
on a person's machine of that system, or the project's own run there.

**The project's own run** is a file for its git host, written for that project and kept in it,
usually by the agent on request. Whatever the git host, it does five things:

1. It runs on the system the proofs are tagged for, on a full checkout of the commit to prove.
2. It installs what the project's tests need, and fetches Purlin at the version
   `.purlin/config.json` names.
3. It sets a git name and email, then runs
   `python3 <purlin>/scripts/run/purlin_run.py --ci --commit`. That run starts only the tests of
   the proofs tagged for its system, writes that system's section of
   `.purlin/evidence/ci/<feature>.json` for each feature it covered, and commits those files
   alone as `purlin: evidence at <sha7>`. It exits 1 only when one of those tests failed or
   could not run.
4. It pushes that commit to the branch it ran on, after a failed run as after a passing one, in
   a way that starts no further run.
5. Where it covers two systems, their jobs run one after the other, each on the branch as the
   one before left it.

How a run starts is the project's choice: by hand from a desk, on a push, on a schedule. The
results come back with `git pull`, and count on the same terms as any other result (above).

## When a sign-off counts

**Signing is logged, not policed.** Purlin keeps a record you can prove and trace: where the
tests ran, what the signer was shown, and who signed the package. It does not decide who may
sign; any role may, and several people may sign one version. The document control system decides who was
entitled.

**The evidence package** is one data file, `.purlin/evidence/package/<version>.json`, which
`purlin:sign` builds from the committed evidence. `references/formats/package_format.md` gives
every field and, under "The file name", where the version is read from;
`purlin:sign --version <version>` names it instead. `purlin:sign --check <file>` checks a
package against its fingerprint and needs no key.

**The outputs.** The first sign-off of a version commits, with the package, each test report
and each folder of what an AI produced that the signing machine still keeps
(`references/formats/package_format.md`, "Outputs"). One taken on another machine, or removed
since, is not there to commit: the package still names it, the sign-off's overview says how many
are kept, and no sign-off is refused for one. To keep every report of a release, sign on the
machine that ran `purlin:test --clean --commit`.

A **sign-off** is one file per signer per version,
`.purlin/evidence/package/<version>.signoffs/<signer-slug>.json`, added in a signed commit by
`purlin:sign` (`references/formats/signature_format.md`). It carries the package's fingerprint,
what the walk showed and every note typed. It records no judgment: no approve or reject answer
and no stated meaning of the signature.

A sign-off counts when two things are true:

- **The last commit that touched its file carries a signature, and that signature verifies over
  the commit.** The signature is the commit's `gpgsig` header, `gpgsig-sha256` in a SHA-256
  repository. An SSH signature is checked with `ssh-keygen -Y check-novalidate -n git`, which
  reads the key the signature carries: it needs no list of allowed signers, and a key deleted
  since still verifies. Any other signature verifies when `git verify-commit` exits 0. The key
  is checked against no list, and neither it nor the commit's author is compared with the
  signer.
- **Its `package_hash` equals the fingerprint computed over the package `HEAD` holds for that
  version.** The fingerprint is computed from the package's content; the `fingerprint` field
  the file stores is not taken on trust. A package changed after it was signed no longer
  matches, so every sign-off of it stops counting, and a later sign-off is refused with
  `No sign-off: .purlin/evidence/package/<version>.json does not match its fingerprint: <why>. Restore it as it was signed, or name a new version: purlin:sign --version <version>.`

| What is read | The reason it does not count |
|---|---|
| The last commit touching the file carries no signature header, or the file is not tracked | `the commit that added it is not signed` |
| That commit carries a signature that does not verify | `the signature on the commit that added it does not verify` |
| `package_hash` is not the fingerprint computed over the committed package, or that package does not match its own fingerprint | `it signs another evidence package than the one committed` |

A sign-off is read as `HEAD` holds it: the files are listed and read from `HEAD`'s tree. A file
git does not track is no sign-off, and an edit that is not committed is not read. A note is
shown only from a sign-off that counts.

**Where the status reads `signed`.** It reads `signed <version>` only where a sign-off of that
version counts, and one of two things holds:

- `signed/<version>` is on `HEAD` or an ancestor of it and names a commit that holds the package
  for that version.
- This checkout holds no tag `signed/<version>`, as after a pull, which fetches no tags, and
  `HEAD` holds the version's package. The sign-off is then read at the commit that added the
  oldest sign-off that counts, and the status adds one line:
  `signed/<version>: tag not in this checkout. The sign-off at <sha7> is read from its files. Run git fetch --tags, or purlin:sign if no one wrote the tag.`

The newest such version answers. A tag that names no such commit is passed over, with one
warning, so an older version whose sign-off counts still answers, and the status reads
`not signed` only where no version is left:

| The tag | The warning |
|---|---|
| names a commit that holds no package for its version, as a tag written by hand does | `signed/<version>: tag with no sign-off. Its commit holds no evidence package for <version>. Run git tag -d signed/<version>.` |
| names a commit that holds the package, and no sign-off of it counts | `signed/<version>: tag with no sign-off. No sign-off counts: <the reason above, or HEAD holds none>. Run purlin:sign --version <version>.` |

`purlin:sign` refuses to sign a version whose tag was written by hand until the tag is deleted.

**What binds what.** The package is checkable alone, by its fingerprint. The sign-off file is
not: it carries no hash of itself and no signature inside it. It names the package's
fingerprint, and the signed commit that added it binds the sign-off, the package and the code.
A receiving system takes the signed commit as the record.

**The sign-off walk.** `purlin:sign` refuses, and writes nothing, where a result does not
count for a sign-off ("Which evidence counts"), a rule has no test or does not pass, a file or
the evidence is changed and not committed, or the version's tag or the branch's copy on the host
stands elsewhere. `references/purlin_commands.md`, "Exit codes", lists every refusal.

Otherwise it names who ran the tests, where and when, and each model the AI proofs ran on, then
shows an overview; `references/formats/signature_format.md` gives each line it prints, under
`shown`. Where a rule reads weak, a proof was settled with its test unchanged, or a proof is
graded, it asks once whether to open a list, as
`To read before you sign: 1 weak, 1 proof graded by an AI. list / go on: `: the weak rules'
findings, the settled proofs, then each graded proof's model runs with the grader and its
reason. A graded proof adds no stop. The walk stops only at hand checks, where the signer may
type what they saw; an empty answer is recorded as `no note`. What the audit found never blocks
the sign-off, whatever its word. The first sign-off of a version is one signed commit carrying
the package and the sign-off; a later one adds its own file alone.

**A hand check** is read from the sign-offs that count:

| The rule | Passed cell | Strong cell |
|----------|-------------|-------------|
| every proof `@manual`, no sign-off has noted it | `checked at sign-off`, with the reason `no sign-off has checked it yet` | `checked at sign-off` |
| every proof `@manual`, noted by a sign-off that counts, on the wording as it is | `passed`, with the note's line as its reason | `checked at sign-off`, with the note's line |
| every proof `@manual`, noted, and the rule or the proof reworded since | `checked at sign-off`, with `the rule's wording changed since its last note` or `the proof's wording changed since its last note`, then the note's line | the same |
| a `@manual` proof beside tested proofs | as its tests make it | `checked at sign-off`, with the same reasons, unless the audit reads `weak`, `spot-checked` or `out of date` |

The note's line names the version it was signed at and how many commits have come since, as in
`noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red`.
The rule shows it there and in its stop of the next walk, under `The rule's wording changed
since this note.` where it was reworded; the reader judges whether it still holds. A note is
compared with the wording through the package of the version it was signed at.

## What `signed/<version>` means

This is the one definition of the tag. Every other page points here.

**`signed/<version>`** is written by the first counting sign-off of a version, as a signed tag
(`git tag -s`), on that sign-off's commit. It means that at the commit the package describes
every spec could be counted, every rule's tests passed on committed results taken on that exact
version of the code, and at least one person signed the package. The tag binds the signing alone:
it says what was signed and by whom, and makes no claim about who was entitled to sign. A later
sign-off adds its file after the tag, and the tag does not move. Where git cannot write the tag,
the next `purlin:sign` writes it on the signed commit and adds no second sign-off.

Its message names the version and the commit the package describes:

```
Signed <version>.

Commit: <full sha>
```

No tag is written over one that is already there; code that changed after `signed/<version>` is
signed under a new version. Nothing is pushed: the sign-off prints
`Tagged signed/<version> at <sha7>.`, then
`Push the branch and the tag: git push origin <branch> signed/<version>`, and a person pushes.

## What stands behind an instruction

`.purlin/config.json` is a file in the repository, and an agent can edit it. Every NEVER in
`agents/purlin.md`, the rule that an agent does not push among them, is an instruction to the
agent and not a mechanism that stops it. What stands behind a sign-off runs outside the agent's
turn: `purlin:sign` builds the package only from committed results recorded on this version of
the code, and a sign-off counts only in a signed commit over the committed package's fingerprint.
