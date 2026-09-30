# The release and the sign-off

For QA, product or a developer who releases a version, at either gate.

A release is a commit, its evidence package and a tag. `purlin:test --release` runs every test,
commits the evidence and the package, and at the gate `passed` tags the release
`passed/<version>`, unsigned. At the gate `signed` it writes no tag: `purlin:sign` walks the
package with you, and the first sign-off writes `signed/<version>`. Later sign-offs are added
over the same package and the tag does not move. This page says what the release run checks,
what the walk shows you, what a sign-off records and when it counts.
[hard_gates.md](../references/hard_gates.md) is the one home of the gate and of the tags.

## While specs change

Nothing is signed while product, QA and the developers improve rules, proofs and tests together
on their branches. `Left to do` lists only work: specs to repair, proofs and tests to write,
tests to fix, and, where the audit ran, rules to strengthen. The AI audit and mutation testing
are tools you run with `purlin:audit`; nothing waits on them, at either gate. When nothing is
left, the last line names the release step:

```text
Nothing left to do. To release a version: purlin:test --release
Nothing left to do. To release a version: purlin:test --release, then purlin:sign
```

the first at the gate `passed`, the second at `signed`.

## The release run

Release a version on a release branch, such as `release/1.2.0`, cut from the default branch once
its specs are done. New specs land on the default branch and wait for the next version; a fix
lands on the release branch and is merged back.

```
purlin:test --release [<version>]
```

It runs every test and commits the evidence, as `purlin:test --all --commit` does. Evidence may
be committed on any branch; a release uses only the evidence at the release commit. Then it
checks that commit, in this order, and stops at the first check that fails, prints one line,
writes nothing more and exits 1:

| What it prints | Why |
|---|---|
| `No release: <feature> cannot be counted: <reason>. Run purlin:spec <feature>, then purlin:test --release.` | the feature's spec writes a number twice or holds a line left from a merge conflict |
| `No release: 2 rules do not pass at 8de0b6e: sample_age RULE-2; stability RULE-1. Run purlin:status to see what is left, then purlin:test --release.` | a rule fails, has no test, has not run, or waits on a run on another system, or a test comment names nothing |
| `No release: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:test --release.` | `git status` lists a change |
| `No release: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:test --release.` | the branch's copy on the host, as this checkout last fetched it, holds commits the checkout lacks; the release run does not fetch |
| `No version: nothing in this project states one. Run purlin:test --release <version>, or write it to a VERSION file.` | no version is stated and none is named |
| `No release: passed/1.2.0 is already written. Run purlin:test --release <version> to name another.` | the gate's tag exists; a tag that exists is never moved |
| `No release: the evidence package was not committed: <why>.` | the package could not be written or committed |
| `No tag: git could not write passed/1.2.0: <git's own message>.` | git refused the tag |

A weak rule, a rule not audited and a rule with no proof are listed in the package, and none of
them stops a release.

The version is read from the `VERSION` file at the project root, then the `version` of
`package.json`, then `[project]` and then `[tool.poetry]` `version` in `pyproject.toml`, then
`<Version>` in a `*.csproj` at the root; `purlin:test --release <version>` names it instead.

The run then writes the evidence package, `.purlin/evidence/package/<version>.json`, and commits
it alone as `purlin: evidence at <sha7>`. At the gate `passed` it writes the tag
`passed/<version>` on that commit, unsigned:

```text
Evidence package committed: .purlin/evidence/package/1.2.0.json.
Tagged passed/1.2.0 at 3c9d2e1.
Nothing left to do. Push the tag to release it: git push origin passed/1.2.0
```

At the gate `signed` it writes no tag and ends on the next step:

```text
Evidence package committed: .purlin/evidence/package/1.2.0.json.
Run purlin:sign to sign it; the first signature writes signed/1.2.0.
```

The tag's message reads `Released at the gate passed.` or `Released at the gate signed.`, then
`Commit: <sha>` and `Gate: <gate>`. You push the tag; Purlin pushes nothing. A package for a
version whose tag is not yet written is written again by the next release run.

## A hand check at the gate `passed`

A hand check is a proof marked `@manual`, which no test runs. At `passed` nobody signs, so
nothing records one. The release goes ahead, prints one line before the package line, and the
package lists those rules as not checked:

```text
2 rules are checked by hand, and the gate passed records no hand check: accession_screen RULE-1, sample_age RULE-6. The package lists them as not checked.
```

A team that wants its hand checks recorded releases at the gate `signed`.

## The sign-off walk

```
purlin:sign [--release <version>]
```

Run it on the release branch, after `purlin:test --release`. At the gate `passed` it prints
`Nothing is signed at the gate passed: purlin:test --release tags the release unsigned. To sign releases, run purlin:init --gate signed.`
and exits 0. Otherwise it refuses, writes nothing and exits 1 when:

| What it prints | Why |
|---|---|
| `No sign-off: the working tree holds changes that are not committed. Commit them, then run purlin:test --release.` | `git status` lists a change |
| `No sign-off: no evidence package for 1.2.0 is committed at 8de0b6e. Run purlin:test --release.` | no release run committed a package for the version |
| `No sign-off: the evidence package for 1.2.0 describes 3c9d2e1, and 8de0b6e has changed since. Run purlin:test --release.` | a commit after the package touches anything but that version's sign-offs |
| `No sign-off: 1 rule does not pass at 8de0b6e: sample_age RULE-2. Run purlin:status to see what is left, then purlin:test --release.` | a rule's tests do not pass at this commit |
| `No sign-off: origin/release/1.2.0 holds 1 commit that 8de0b6e does not, as this checkout last fetched it. Pull, then run purlin:sign.` | the branch's copy on the host holds commits the checkout lacks |
| `quinn.qa@labconnect.example has already signed 1.2.0 over this package; nothing was written.` | one sign-off per signer per version |

It opens on an overview of the package:

```text
Signing 1.2.0: .purlin/evidence/package/1.2.0.json, at 3c9d2e1.
  40 rules on Linux/Unix and Windows: 38 pass their tests, 2 are checked by hand.
  The audit: 30 strong, 2 weak, 6 not audited.
  10 stops: 2 hand checks, 2 weak, 6 not audited.
```

or, where there is nothing to stop at, `  No stops: nothing is checked by hand, weak or not audited.`

### The strong list

The rules the audit found strong are a list, not stops. Before the stops the walk asks:

```text
30 rules the audit found strong. list / walk / go on: 
```

`list` prints them, one line per feature, such as `  sample_age RULE-2, RULE-3`, then asks
`walk / go on: `. `walk` makes each strong rule a stop after the others. `go on`, or an empty
line, leaves them in the list.

### The stops

The walk stops only where you have something to look at: each hand check, then each weak rule,
then each rule never audited, then any strong rule you chose to walk. Within each, by feature
name, then rule number, so `RULE-2` comes before `RULE-10`. A rule with a `@manual` proof and a
weak audit stops once, as a hand check.

A stop shows the rule, each proof with the test tied to it and that test's body, the result on
each system with the machine it ran on, and what the audit found:

```text
sample_age RULE-1   weak
Rule
  The age at receipt is the time from collection to receipt, across time zones
Proof
  PROOF-1: A sample received at 10:30 UTC-5, collected at 14:00 UTC, has an age of `90` minutes
    tied to tests/test_age.py::test_age_at_receipt
      def test_age_at_receipt():
          assert age_minutes('14:00Z', '10:30-05:00') == 90
Results
  Linux/Unix: passed on quinn-laptop
  Windows: passed on remote runner, Windows
What the audit found
  Weak.
  The test checks one time zone; PROOF-1 names two.
sample_age RULE-1   continue / note / stop: 
```

A proof with no test reads `    tied to no test`, and a test whose file is gone reads
`      the test's source was not found`. The answers:

- **continue** moves on.
- **note** asks `Your note, in one line: `, keeps the line, and moves on.
- **stop** ends the walk and signs nothing:
  `Stopped at sample_age RULE-1: nothing was signed. After the fix, run purlin:test --release, then purlin:sign.`

A hand check shows the rule and its proofs alone and asks what you saw:

```text
accession_screen RULE-1   what did you see, in one line, or stop: 
```

The line you type is the hand check's note. An empty line asks again; `stop` stops.

A weak rule or a rule not audited never blocks the signature. The walk shows you what was
measured and what was seen, and you decide whether to sign, add a note, or stop to fix.

### The signature

After the last stop the walk asks once:

```text
Sign the evidence package for 1.2.0 as quinn.qa@labconnect.example? [y/N] y
Signed 1.2.0 as quinn.qa@labconnect.example with the key ending ...4f2a.
Tagged signed/1.2.0 at 8de0b6e.
Nothing left to do. Push the tag to release it: git push origin signed/1.2.0
Sign-offs of 1.2.0: quinn.qa@labconnect.example.
```

On `y` it writes your sign-off file and makes one signed commit,
`sign(1.2.0): quinn.qa@labconnect.example`. The first sign-off of a version writes the signed tag
`signed/<version>` on that commit with `git tag -s`. Any other answer prints `Nothing was signed.`
and writes nothing. Where git cannot make the commit, the walk prints
`The sign-off commit was not made: <git's message>. Nothing was signed; run purlin:sign again.`

## Several signers

Any person with a key may sign, and several may sign one release, each once. A later sign-off
adds its own file over the same package, and the tag stays where the first put it:

```text
signed/1.2.0 stays at 8de0b6e; this sign-off is added after it. Push it: git push
Sign-offs of 1.2.0: quinn.qa@labconnect.example, pat.product@labconnect.example.
```

Purlin creates evidence and enforces no policy about who signs: a sign-off counts whoever wrote
it.

## Through the agent

The agent's shell has no terminal for you to answer in, so `purlin:sign` in Claude Code makes
the walk in two calls. It runs `purlin:sign --show`, which prints the overview, every stop and the
strong list in full, asks nothing and writes nothing, and ends on
`Answer each stop, then run purlin:sign --answers <file>.` The agent asks you each stop, writes
your answers to `.purlin/runtime/signoff-answers.json`, and runs `purlin:sign --answers` with it:

```json
{"strong": "go on",
 "stops": {"accession_screen RULE-1": {"answer": "note", "note": "the tube is red"},
           "sample_age RULE-1": {"answer": "continue"}},
 "sign": true}
```

The walk then runs with those answers and prints the same lines. A stop with no answer refuses:

```text
No sign-off: sample_age RULE-1 has no answer in .purlin/runtime/signoff-answers.json. Answer every stop, then run purlin:sign --answers .purlin/runtime/signoff-answers.json again.
```

## What the sign-off records

One sign-off covers the whole package. It is a file,
`.purlin/evidence/package/<version>.signoffs/<signer>.json`, added in a signed commit, carrying
the package's `fingerprint`. It records the signer's email and name as git holds them, the key's
fingerprint, the time, the commit the package describes, and what the walk showed:

- the overview's numbers;
- each rule shown one by one, in the order walked, with why it stopped: `hand check`, `weak`,
  `not audited` or `strong`;
- each rule the audit found strong that you did not walk, and whether you opened the list;
- every note you typed, hand checks among them.

It records no judgment: no answer word, only what was shown and what was typed.
[signature_format.md](../references/formats/signature_format.md) holds every field.

## When a sign-off counts

A sign-off counts when all of these hold:

- the last commit that touched its file carries a signature, made with any key;
- that signature verifies over the commit; where it does not, the reason reads
  `the signature on the commit that added it does not verify`;
- its package hash equals the `fingerprint` of the package committed for that version.

The key is not compared with the signer. An SSH signature is checked with
`ssh-keygen -Y check-novalidate`, which needs no list of allowed signers, and an OpenPGP one with
`git verify-commit`.

Purlin signs with an SSH key, any key. A checkout with none gets the commands that set one up,
writes nothing and exits 1; the `ssh-keygen` line shows only while that key file does not exist:

```text
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

`purlin:sign` shows you the commands, offers to run them, and carries on once they ran.

## The tag

The tag pins the version: the code, the evidence, the package and, at `signed`, the sign-offs,
under one name.

| Tag | Written by | Signed |
|---|---|---|
| `passed/<version>` | `purlin:test --release` at the gate `passed`, on the package's commit | no |
| `signed/<version>` | the first `purlin:sign` at the gate `signed`, on its sign-off commit | yes, with the key `user.signingkey` names |

A tag that exists is never moved. The package is one data file describing every rule of that
version, the thing you hand to a regulated system:
[package_format.md](../references/formats/package_format.md) holds its fields, and
[regulated-workflow.md](regulated-workflow.md) says what happens to it next. Where a project has
a remote runner, pushing a `signed/*` tag starts a tag run, which runs the tests tied to proofs
tagged for the runner's system and writes nothing.

Read next: [regulated-workflow.md](regulated-workflow.md) for the release in a regulated setting,
[raising-the-gate-and-upgrading.md](raising-the-gate-and-upgrading.md) for the move to the gate
`signed`, [specs-and-anchors.md](specs-and-anchors.md) for writing a proof a test can prove.
