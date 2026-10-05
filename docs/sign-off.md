# The sign-off

For whoever signs: QA, product or a developer. This page covers QA's path from acceptance
criteria to a signature, the walk of `purlin:sign`, what a sign-off records and when it counts,
and where Purlin's part ends beside a regulated sign-off system.

When everyone is done, a person signs the evidence once.

| | |
|---|---|
| Run and commit | A developer runs `purlin:test --all --commit` on the version to sign. It runs what changed, carries the rest forward, results from Windows included, and commits them. |
| `purlin:sign` | Opens with who ran the tests, where and when. Stops at each hand check, shows what the audit found, and asks for one signature. |
| The package | One file: every rule, its proofs, its tests, the results, the audit, who wrote what. Each sign-off is a file beside it. |
| The tag | The first sign-off tags the version `signed/1.4.0`. Later sign-offs are added beside it. |
| `git push` | You publish the branch and the tag. |

**Signing is optional.** A project that never signs keeps its evidence all the same. Any
project may run `purlin:sign` whenever it chooses, and several people may sign one version.
[evidence_and_signoff.md](../references/evidence_and_signoff.md) is the one definition of which
evidence counts, when a sign-off counts and what the tag means.

## From criteria to proofs

Nothing is signed while the work goes on. Product, QA and developers improve rules, proofs and
tests together on their branches. Nothing is recorded about anyone's judgment, and `Left to do`
lists only work. The sign-off is the final check, once everybody is done.

```
purlin:spec login
```

Paste the acceptance criteria as you have them. `purlin:spec` turns them into rules and proofs.

- A rule is one line saying what the software has to do.
- A proof is one line saying how a rule is shown. A test checks an exact result.
- A proof holds one case. A refusal or a boundary is a proof of its own.

`purlin:spec` prints each rule with its proofs under it, and asks whether to change any before
it saves. [spec_quality_guide.md](../references/spec_quality_guide.md) is the guideline every
draft is held to, and the one you read it against.

A criterion "a locked account cannot sign in" becomes:

```
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures
- PROOF-3 (RULE-3): After 5 wrong passwords in a row, the right password is refused with `423`
- PROOF-4 (RULE-3): 15 minutes after the fifth wrong password, the right password is answered with `200`
```

A judgment call takes a proof tagged `@manual`. It is a hand check, and the walk stops at it.
[specs-and-anchors.md](specs-and-anchors.md#judgment-calls) says when to tag one.

`purlin:build login` writes the code and one test per proof. The comment on the line above
each test names the proof it carries out: `# purlin: login PROOF-3`.

After each pull, `purlin:drift` names the proofs added, changed and moved. It quotes both
wordings of a changed proof.

No rule carries a level of its own. Every rule is asked the same things, and the weight of a
risk goes into its proofs: a critical computation or data flow carries more proofs.

## The hand-off

QA runs no tests. The developer runs the tests, on their machine and through the project's
own run for any other operating system, and commits the results that come back:

```
purlin:test --all --commit
```

That run covers every feature. It runs what changed since the last results, and every anchor.
It carries the rest forward: each result is recorded again on this commit, with the commit it
was taken at. [The run before a sign-off](running-and-evidence.md#the-run-before-a-sign-off)
says which features run.

That commit is ready for sign-off. The status reads `Tests: met` and ends on
`Every rule passes its tests on the committed evidence. Optional: sign this version with purlin:sign`.
The developer pushes the branch, and the signer pulls it.

## purlin:sign

```
purlin:sign [--version <version>]
purlin:sign --show
purlin:sign --answers <file>
purlin:sign --check <file>
```

The version is read from the `VERSION` file at the project root, then `package.json`, then
`pyproject.toml`, then the first `*.csproj` at the root. `--version` names it instead.

### What it refuses

Before it shows anything, `purlin:sign` checks the commit it is asked to sign. Each refusal is
one line naming the cause and the command to run. It writes nothing and exits 1.

| What it prints | Why |
|---|---|
| `No sign-off: 2 files are changed and not committed. Commit them or set them aside, then run purlin:sign again.` | tracked files are changed and not committed; for one it reads `1 file is`. A file git does not track stops nothing |
| `No sign-off: the evidence is written and not committed. Run purlin:test --commit, then purlin:sign.` | a run wrote results that are not in git |
| `No sign-off: 9 tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.` | a test still carries a marker from Purlin 0.9.5, so its result counts for no rule; for one it reads `1 test still carries` and ends `see it, rewrite it`. `purlin:status` names each |
| `No version: nothing in this project states one. Run purlin:sign --version <version>, or write it to a VERSION file.` | no version is stated and none is named |
| `No sign-off: signed/2.1.0 names a commit that holds no evidence package for 2.1.0, so purlin:sign did not write it. Delete it: git tag -d signed/2.1.0, and git push origin --delete signed/2.1.0 if it was pushed. Then run purlin:sign again.` | a tag of that name was written by hand; nothing is signed while it stands. The push half is printed only where the checkout has a remote |
| `No sign-off: signed/2.1.0 is at 8de0b6e, which this checkout does not hold. Pull, then run purlin:sign.` | the version is already signed on a commit you have not pulled |
| `No sign-off: signed/2.1.0 is at 8de0b6e, and the code has changed since. To sign this code, name a new version: purlin:sign --version <version>.` | the version is already signed, over other code; a tag that exists is never moved |
| `No sign-off: these results are not recorded on this version of the code, 1cf829e: login on Windows. Run purlin:test on Windows, then purlin:sign.` | a result was recorded before the code last changed; the line names the features and the system, and the run that records them on this version |
| `No sign-off: these results are not recorded on this version of the code, 1cf829e: login on macOS. Run purlin:test --all --commit, then purlin:sign.` | a commit changed a file after this machine's results were recorded, as a `--commit` run of one feature does; `purlin:test --all --commit` runs what changed and carries the rest onto this version |
| `No sign-off: these results were taken while files were changed and not committed: login on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.` | a committed result was taken over files that were changed and not committed |
| `No sign-off: 1 rule has no test at 1cf829e: login RULE-3. Run purlin:build login, then purlin:sign.` | a rule has no test, with or without a proof line |
| `No sign-off: 1 rule does not pass at 1cf829e: login RULE-2. Run purlin:status to see what is left, then purlin:sign.` | a rule fails or has not run |
| `No sign-off: origin/main holds 1 commit that 1cf829e does not, as this checkout last fetched it. Pull, then run purlin:sign.` | the branch's copy on the host holds commits the checkout lacks; `purlin:sign` fetches nothing |
| `No sign-off: .purlin/evidence/package/2.1.0.json does not match its fingerprint: <why>. Restore it as it was signed, or name a new version: purlin:sign --version <version>.` | the committed package was changed after it was signed |
| `quinn.qa@labconnect.example has already signed 0.1.0 over this package; nothing was written.` | one sign-off per signer per package |
| `No sign-off: the commit was signed with the key ending ...8kuw, not the key this checkout names, ending ...JJ8w, so it was taken back and no tag was written. A global gpg.ssh.program or signing key is the usual cause. Run git config gpg.ssh.program ssh-keygen, then purlin:sign again.` | another key signed the commit than the one this checkout names; this one comes after the last question, and the commit is taken back |

Two things are listed in the package and stop no sign-off: what the audit found, whatever its
word, and a rule whose tests pass with no proof line.

A rule with no test stops it, and `purlin:build` writes the test. A signed version means every
rule had a passing test or a hand check.

### The walk

The walk opens with who ran the tests, where and when, and on which commit: one line per run.
Then it shows an overview of the package:

```text
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.
Signing 0.1.0 at 1cf829e.
  19 rules on Linux/Unix: 18 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak.
The audit's findings: 1 weak. list / go on: 
```

Results an earlier run took and `purlin:test --all` carried forward have a line of their own.
It names who took them, on which machine, and the newest of the runs they came from:

```text
Carried forward from earlier runs by dana.dev@labconnect.example on dana-laptop, the newest at 2026-09-30 08:05 UTC on 9b2e7c4: 12 rules on Linux/Unix.
```

The audit's line is there only where the audit read a rule. The question is there only where
it found a rule weak, or a proof was settled with its test unchanged. `list` prints each weak
rule with its findings, then asks `go on: `. `go on`, or an empty line, moves on. The findings
are a list you can read. They add no stop.

A proof settled with its test unchanged is listed after the weak rules' findings, whatever its
rule reads, and the question counts it:

```text
The audit's findings: 1 weak, 1 proof settled with its test unchanged. list / go on: list
  login RULE-1   PROOF-1 reads the status alone.
  login RULE-2: PROOF-2 was settled with its test unchanged: it was judged to assert what the proof names.
go on: 
```

A planted bug once got past that proof's test. `purlin:build` read the test against the proof,
judged that it already asserts what the proof names and left it as it was, so the finding was
cleared by that judgment and not by a stronger test. Purlin records the judgment and does not
check it, so you see it here.

The walk stops only at hand checks, one stop each, by feature and then rule number. A stop
shows:

- the rule;
- each proof, with the tests tied to it;
- the result on each system, with the machine it ran on, and for a result carried forward
  the commit it was taken at, as in
  `Linux/Unix: passed on dana-laptop; PROOF-3 carried forward from 9b2e7c4`;
- what the audit found, where it found the rule weak;
- the rule's last note, where an earlier sign-off holds one.

The last note names the version it was signed at and how many commits have come since. You
judge whether it still holds. Where the rule or the proof was reworded since, a line above the
note says so:

```text
Last note
  The rule's wording changed since this note.
  noted at the sign-off of 0.1.0 by pat.product@labconnect.example, 3 commits since: I read the SST and EDTA rejection messages myself; both are clear.
```

Then the walk asks what you saw:

```text
login RULE-2   hand check
Rule
  The error messages follow the brand voice guide
Proof
  PROOF-5: Read the error messages against the brand voice guide @manual
Results
  No test runs for this rule: you check it here.
login RULE-2   what did you see, in one line, or Enter for no note, or stop: 
```

The line you type is the hand check's note. The note is asked for and not required: an empty
answer is recorded as `no note`. `stop` ends the walk and signs nothing:

```text
Stopped at login RULE-2: nothing was signed. After the fix, run purlin:test --all --commit, then purlin:sign.
```

Where an anchor's proof found nothing to check, the stop's result line says so, and you see
the rule was not exercised:
`  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens`

### The signature

After the last stop the walk asks once:

```text
Sign the evidence package for 0.1.0 as quinn.qa@labconnect.example? [y/N] y
Signed 0.1.0 as quinn.qa@labconnect.example with the key ending ...4f2a.
Tagged signed/0.1.0 at e0deb2e.
Push the branch and the tag: git push origin main signed/0.1.0
```

On `y` it makes one signed commit, `sign(0.1.0): quinn.qa@labconnect.example`. The commit
carries the package and your sign-off file. The signed tag `signed/0.1.0` is written on that
commit.

Any other answer prints `Nothing was signed.` and writes nothing. Where git cannot make the
commit, the walk prints
`The sign-off commit was not made: <git's message>. Nothing was signed; run purlin:sign again.`

Where the commit is made and git cannot write the tag, the walk prints
`No tag: git could not write signed/0.1.0: <git's reason>. Fix that, then run purlin:sign again to write it.`
The next `purlin:sign` writes the tag on the signed commit and signs nothing twice.

You push the branch and the tag. Purlin pushes nothing. The status then reads
`Sign-off: signed 0.1.0 at e0deb2e`. After the next change to the code it reads
`Sign-off: signed 0.1.0, 1 commit since`.

### Several signers

Any person with a key may sign. Several may sign one version, each once. A later signer pulls
the tagged commit and runs `purlin:sign`. Their own file is added over the same package, and
the tag stays where the first put it:

```text
signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin main
```

Purlin creates evidence and enforces no policy about who signs. A sign-off counts whoever wrote
it.

### Through the agent

The agent's shell has no terminal for you to answer in. So `purlin:sign` in Claude Code makes
the walk in two calls.

1. It runs `purlin:sign --show`. That prints the run lines, the overview, the audit's findings
   and every stop. It asks nothing, writes nothing and needs no key. It ends on
   `Answer each stop, then run purlin:sign --answers <file>.`
2. The agent asks you each stop and writes your answers to
   `.purlin/runtime/signoff-answers.json`. Then it runs `purlin:sign --answers` with that file:

```json
{"audit": "go on",
 "stops": {"login RULE-2": {"answer": "note", "note": "the wording matches the guide"}},
 "sign": "quinn.qa@labconnect.example"}
```

The agent asks the last question as
`Sign the evidence package for 0.1.0 as quinn.qa@labconnect.example? Type that address to sign:`
The script signs only where `sign` holds the signer's own address, typed by the person signing.
Any other value ends on
`Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json must hold quinn.qa@labconnect.example, typed by the person signing.`

The walk then runs with those answers and prints the same lines. A stop with no answer in the
file refuses, with nothing written.

### A key to sign with

Purlin signs with an SSH key, any key. A checkout with none gets the commands that set one up.
It writes nothing and exits 1. The `ssh-keygen` line shows only while that key file does not
exist:

```text
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

## What is recorded

**The evidence package**, `.purlin/evidence/package/<version>.json`, is one data file. It
describes every rule at the signed commit. It holds:

- `met`, whether every rule's tests pass, the total of rules, the count whose tests pass, what
  the audit found, and each line of `Left to do` with its kind, count, words and command;
- the version of Purlin that wrote it, the project, the version, the tag and the commit the
  evidence was taken at;
- the runs: who ran the tests, on which machine and system, when and on which commit, and
  whether a later run carried the results forward;
- for every rule of every feature: its words exactly as the spec has them, its proofs, the
  tests behind each proof, each result with its operating system, source, time, commit, runner
  and machine, whether it is recorded on this code, each proof whose result was carried
  forward with the run that took it, each proof that found nothing to check with its reason,
  and what the audit found with the model;
- for every rule, its authors, read from git: who first wrote the rule and each proof, who last
  changed each proof and each test, with the commits. Nobody does anything extra for it;
- every rule with a hand check;
- a fingerprint of the package itself.

Every time is UTC. The same commit always gives the same bytes.
[package_format.md](../references/formats/package_format.md) has every field.

`purlin:sign --check <file>` recomputes the fingerprint of a package you were handed:

```text
The package matches its fingerprint.
```

For a file changed after it was written, it prints
`The package does not match its fingerprint: <why>.` and exits 1.

**The sign-off** is a file beside the package,
`.purlin/evidence/package/<version>.signoffs/<signer>.json`, added in the signed commit. It
carries:

- the package's fingerprint;
- the signer's email and name as git holds them, the key's fingerprint and the time. The key
  recorded is the key that signed the commit. Where another key signed it, as a global
  `gpg.ssh.program` can cause, the sign-off is taken back and names both keys;
- what the walk showed: the overview, the runs, each hand check walked, whether the audit's
  list was opened, and every note typed.

It records no judgment and no answer word.
[signature_format.md](../references/formats/signature_format.md) holds every field.

**How each is checked.** The package is checkable alone, by its fingerprint:
`purlin:sign --check <file>`. The sign-off file is not. It carries no hash of itself and no
signature inside it. It names the package's fingerprint, and the signed commit that added it
binds the sign-off, the package and the code.
[evidence_and_signoff.md](../references/evidence_and_signoff.md#when-a-sign-off-counts) is the
one definition.

**The signed tag**, `signed/<version>`, is written by the first sign-off on its commit, with
the key `user.signingkey` names. It pins the code, every evidence file, the package and the
sign-offs under one name. It is never moved.

The status reads `signed` only where a sign-off of that version counts, and the tag names a
commit that holds the package or this checkout holds no tag of that name. A tag written by hand reads `not signed`, with one warning, and
`purlin:sign` refuses to sign that version until the tag is deleted.

After a `git pull` the tag may be missing: a pull fetches no tags. The status then reads the
sign-off from its files and names `git fetch --tags`:
`signed/0.1.0 is not in this checkout: the sign-off of 0.1.0 at f099b41 is read from its files. Run git fetch --tags, or purlin:sign if no one wrote the tag.`

Changing a test command in `.purlin/config.json` ends the results, as changing the code does.
Changing `version` alone does not.

## When a sign-off counts

A sign-off counts when all of these hold, each read from git or from the file:

- the last commit that touched its file carries a signature, made with any key;
- that signature verifies over the commit; where it does not, the reason reads
  `the signature on the commit that added it does not verify`;
- its package hash equals the fingerprint of the package committed for that version, computed
  over the package as it stands. A package changed after it was signed no longer matches.

A sign-off is read as `HEAD` holds it. A sign-off file changed and not committed does not count.

The key is not compared with the signer. Purlin records who signed and the fingerprint of the
key they signed with. Anyone with an SSH key can sign.

## Beside a regulated system

Purlin supplies evidence. It does not claim compliance.

| | |
|---|---|
| Purlin produces | Evidence for each rule: its tests and their results, what the audit found, who wrote what, who ran the tests and who signed. |
| You hand over | The evidence package: one file for the version, made by `purlin:sign`, with its sign-offs. |
| Your system of record | The validated system your company uses for approval, such as Veeva. It holds the document, decides who approves, and carries the approval that counts. |

**What you hand over.** The package and its sign-offs, from the tagged commit. The package's
`met` comes second, after the schema. The receiving system decides how the package is shown,
read and filed. It also decides which signers were entitled.

**The signed commit is the record.** The package is checkable alone, with
`purlin:sign --check <file>`. A sign-off file is not: take the signed commit that added it as
the record. The sign-off records no approve or reject answer and no stated meaning of the
signature.

**Approval before a test runs.** Purlin has no approval step before a test runs. It signs once,
at the end. Approval of the proofs is a required review when they are merged, or your system of
record's. Purlin does record two things:

- who wrote and who last changed each proof, read from git into the evidence package;
- that a result stops counting when its proof is reworded. The rule reads `out of date` until
  its tests run again.

**What a Purlin sign-off is.** An engineering attestation. A person was shown the evidence
package of one version and looked at each hand check. They typed what they saw where they had
something to say, and signed the package's fingerprint in one signed commit. The sign-off is
evidence itself, filed beside the package.

**A requirement's number** from the regulated system reaches the evidence in the rule's own
words. Write the number into the rule, at the end of its sentence, and it travels with the rule
into the package.

Purlin does nothing else with the number. It reaches the package because the rule's words do. So
the receiving system can trace the number to the rule, its proofs, its tests, its results and
its authors, and to the sign-offs over the package that holds them.

**A version is signed on a branch of its own** where the team wants one, such as
`release/1.2.0`, cut from the default branch once its specs are done. New specs land on the
default branch and wait for the next version. A fix lands on the release branch. The developer
runs and commits the tests again there, and the fix is merged back.

## Read next

- [running-and-evidence.md](running-and-evidence.md) for the evidence a sign-off reads.
- [specs-and-anchors.md](specs-and-anchors.md) for writing a proof a test can prove.
- [audit.md](audit.md) for what the audit's findings mean.
