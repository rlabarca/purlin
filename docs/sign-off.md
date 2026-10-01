# The sign-off

For whoever signs: QA, product or a developer. It covers QA's path from acceptance criteria to
a signature, the walk of `purlin:sign`, what a sign-off records and when it counts, and where
Purlin's part ends beside a regulated sign-off system.

Purlin keeps the evidence and the sign-off. A sign-off is one person's signature over the
evidence package of one version: `purlin:sign` reads the committed evidence, builds the
package, stops at each hand check, and takes one signature in a signed commit. The first
sign-off of a version writes the signed tag `signed/<version>`, so anyone can find what was
signed. Any project may run it whenever it chooses, and several people may sign one version.
[evidence_and_signoff.md](../references/evidence_and_signoff.md) is the one definition of which
evidence counts, when a sign-off counts and what the tag means.

## From criteria to proofs

While the specs change, nothing is signed and nothing is recorded about anyone's judgment:
product, QA and the developers improve rules, proofs and tests together on their branches, and
`Left to do` lists only work. The sign-off is the final check, once everybody is done.

```
purlin:spec login
```

Paste the acceptance criteria as you have them. `purlin:spec` turns them into rules, one line
each saying what the software has to do, and proofs, one line each saying how a rule is shown:
what is done, what is observed and the value that settles it. It prints each rule with its
proofs under it and asks whether to change any before it saves. A proof holds one case; a
refusal or a boundary is a proof of its own.
[spec_quality_guide.md](../references/spec_quality_guide.md) is the guideline every draft is
held to, and the one you read it against.

A criterion "a locked account cannot sign in" becomes:

```
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures
- PROOF-3 (RULE-3): After 5 wrong passwords in a row, the right password is refused with `423`
- PROOF-4 (RULE-3): 15 minutes after the fifth wrong password, the right password is answered with `200`
```

A proof that only a person can judge, such as wording against a brand voice guide, carries
`@manual`: it is a hand check, and the walk stops at it. `purlin:build login` writes the code
and one test per proof, with a comment on the line above each test naming the proof it carries
out, `# purlin: login PROOF-3`. After each pull, `purlin:drift` names the proofs added, changed
and moved, quoting both wordings of a changed proof.

No rule carries a level of its own: every rule is asked the same things, and the weight of a
risk goes into its proofs. A critical computation or data flow carries more proofs; look and
feel is not a rule.

## The hand-off

QA runs no tests. The developer runs every test, on their machine and through the remote run
for any other operating system, and commits the results that come back:

```
purlin:test --all --commit
purlin:test --remote
```

That commit is ready for sign-off: the status reads `Tests: met` and ends on
`Every rule passes its tests on the committed evidence. To sign it: purlin:sign`. The developer
pushes the branch, and the signer pulls it.

## purlin:sign

```
purlin:sign [--version <version>]
purlin:sign --show
purlin:sign --answers <file>
purlin:sign --check <file>
```

The version is read from the `VERSION` file at the project root, then `package.json`, then
`pyproject.toml`, then the first `*.csproj` at the root; `--version` names it instead.

### What it refuses

Before it shows anything, `purlin:sign` checks the commit it is asked to sign. Each refusal is
one line naming the cause and the command to run, writes nothing and exits 1:

| What it prints | Why |
|---|---|
| `No sign-off: the working tree holds changes that are not committed. Commit them, run purlin:test --all --commit, then purlin:sign.` | files are changed and not committed: commit them or set them aside |
| `No sign-off: the evidence is written and not committed. Run purlin:test --commit, then purlin:sign.` | a run wrote results that are not in git |
| `No version: nothing in this project states one. Run purlin:sign --version <version>, or write it to a VERSION file.` | no version is stated and none is named |
| `No sign-off: signed/2.1.0 is at 8de0b6e, which this checkout does not hold. Pull, then run purlin:sign.` | the version is already signed on a commit you have not pulled |
| `No sign-off: signed/2.1.0 is at 8de0b6e, and the code has changed since. To sign this code, name a new version: purlin:sign --version <version>.` | the version is already signed, over other code; a tag that exists is never moved |
| `No sign-off: these results were not taken on this version of the code, 1cf829e: audit on Windows. Run purlin:test --remote, then purlin:sign.` | a result was taken before the code last changed; the line names the features and the system, and the run that takes them again |
| `No sign-off: 1 rule does not pass at 1cf829e: login RULE-2. Run purlin:status to see what is left, then purlin:sign.` | a rule fails, has not run, or has no test, with or without a proof line |
| `No sign-off: origin/main holds 1 commit that 1cf829e does not, as this checkout last fetched it. Pull, then run purlin:sign.` | the branch's copy on the host holds commits the checkout lacks; `purlin:sign` fetches nothing |
| `quinn.qa@labconnect.example has already signed 0.1.0 over this package; nothing was written.` | one sign-off per signer per package |

A rule the audit found weak, a rule never audited and a rule whose tests pass with no proof
line are listed in the package, and none of them stops a sign-off. A rule with no test stops
it, and `purlin:build` writes the test: a signed version means every rule had a passing test or
a hand check.

### The walk

The walk opens by naming who ran the tests, where, when and on which commit, one line per run,
then an overview of the package:

```text
Tests run by dana.dev@labconnect.example on dana-laptop at 2026-10-01 12:17 UTC on 1cf829e: 19 rules on Linux/Unix.
Signing 0.1.0 at 1cf829e.
  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.
  The audit: 17 strong, 1 weak, 1 not audited.
The audit's findings: 1 weak. list / go on: 
```

A remote runner's run reads `Tests run by a remote runner at <time> on <commit>: ...`. The
audit's line is there only where the audit read a rule, and the question only where it found a
rule weak. `list` prints each weak rule with its findings, then asks `go on: `; `go on`, or an
empty line, moves on. The findings are a list you can read; they add no stop.

The walk stops only at hand checks, one stop each, by feature and then rule number. A stop
shows the rule, each proof with the tests tied to it, the result on each system with the
machine it ran on, and what the audit found where it found the rule weak, then asks what you
saw:

```text
login RULE-2   hand check
Rule
  The error messages follow the brand voice guide
Proof
  PROOF-5: Read the error messages against the brand voice guide @manual
Results
  Linux/Unix: passed on dana-laptop
login RULE-2   what did you see, in one line, or Enter for no note, or stop: 
```

The line you type is the hand check's note. The note is asked for and not required: an empty
answer is recorded as `no note`. `stop` ends the walk and signs nothing:

```text
Stopped at login RULE-2: nothing was signed. After the fix, run purlin:test --all --commit, then purlin:sign.
```

Where an anchor's proof found nothing to check, the stop's result line says so, as
`  Linux/Unix: passed on dana-laptop; nothing to check for PROOF-3: this project has no screens`,
so you see the rule was not exercised.

### The signature

After the last stop the walk asks once:

```text
Sign the evidence package for 0.1.0 as quinn.qa@labconnect.example? [y/N] y
Signed 0.1.0 as quinn.qa@labconnect.example with the key ending ...4f2a.
Tagged signed/0.1.0 at e0deb2e.
Push the branch and the tag: git push origin main signed/0.1.0
```

On `y` it makes one signed commit, `sign(0.1.0): quinn.qa@labconnect.example`, carrying the
package and your sign-off file, and writes the signed tag `signed/0.1.0` on that commit. Any
other answer prints `Nothing was signed.` and writes nothing. Where git cannot make the commit,
the walk prints
`The sign-off commit was not made: <git's message>. Nothing was signed; run purlin:sign again.`
You push the branch and the tag; Purlin pushes nothing. The status then reads
`Sign-off: signed 0.1.0 at e0deb2e`, and after the next change to the code,
`Sign-off: signed 0.1.0, 1 commit since`.

### Several signers

Any person with a key may sign, and several may sign one version, each once. A later signer
pulls the tagged commit, runs `purlin:sign`, and adds their own file over the same package; the
tag stays where the first put it:

```text
signed/0.1.0 stays at e0deb2e; this sign-off is added after it. Push it: git push origin main
```

Purlin creates evidence and enforces no policy about who signs: a sign-off counts whoever wrote
it.

### Through the agent

The agent's shell has no terminal for you to answer in, so `purlin:sign` in Claude Code makes
the walk in two calls. It runs `purlin:sign --show`, which prints the run lines, the overview,
the audit's findings and every stop, asks nothing, writes nothing and needs no key, and ends on
`Answer each stop, then run purlin:sign --answers <file>.` The agent asks you each stop, writes
your answers to `.purlin/runtime/signoff-answers.json`, and runs `purlin:sign --answers` with
it:

```json
{"audit": "go on",
 "stops": {"login RULE-2": {"answer": "note", "note": "the wording matches the guide"}},
 "sign": true}
```

The walk then runs with those answers and prints the same lines. A stop with no answer in the
file refuses, with nothing written.

### A key to sign with

Purlin signs with an SSH key, any key. A checkout with none gets the commands that set one up,
writes nothing and exits 1; the `ssh-keygen` line shows only while that key file does not exist:

```text
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

## What is recorded

**The evidence package**, `.purlin/evidence/package/<version>.json`, is one data file
describing every rule at the signed commit. It holds:

- `met`, whether every rule's tests pass, the total of rules, the count whose tests pass, what
  the audit found, and each line of `Left to do` with its kind, count, words and command;
- the version of Purlin that wrote it, the project, the version, the tag and the commit the
  evidence was taken at;
- the runs: who ran the tests, on which machine and system, when and on which commit;
- for every rule of every feature: its words exactly as the spec has them, its proofs, the
  tests behind each proof, each result with its operating system, source, time, commit, runner
  and machine, whether it was taken on this code, each proof that found nothing to check with
  its reason, and what the audit found with the model;
- for every rule, its authors, read from git: who first wrote the rule and each proof, who last
  changed each proof and each test, with the commits. Nobody does anything extra for it;
- every rule with a hand check;
- a fingerprint of the package itself.

Every time is UTC. The same commit always gives the same bytes.
[package_format.md](../references/formats/package_format.md) has every field, and
`purlin:sign --check <file>` recomputes the fingerprint of a package you were handed:

```text
The package matches its fingerprint.
```

or, for a file changed after it was written,
`The package does not match its fingerprint: <why>.`, with exit 1.

**The sign-off** is a file beside the package,
`.purlin/evidence/package/<version>.signoffs/<signer>.json`, added in the signed commit. It
carries the package's fingerprint, the signer's email and name as git holds them, the key's
fingerprint and the time, and what the walk showed: the overview, the runs, each hand check
walked, whether the audit's list was opened, and every note typed. It records no judgment and
no answer word. [signature_format.md](../references/formats/signature_format.md) holds every
field.

**The signed tag**, `signed/<version>`, is written by the first sign-off on its commit, with
the key `user.signingkey` names. It pins the code, every evidence file, the package and the
sign-offs under one name, and it is never moved.

## When a sign-off counts

A sign-off counts when all of these hold, each read from git or from the file:

- the last commit that touched its file carries a signature, made with any key;
- that signature verifies over the commit; where it does not, the reason reads
  `the signature on the commit that added it does not verify`;
- its package hash equals the fingerprint of the package committed for that version.

The key is not compared with the signer. Purlin records who signed and the fingerprint of the
key they signed with, and anyone with an SSH key can sign.

## Beside a regulated system

Purlin makes no claim that software is compliant with any regulation. For a team whose software
is signed off in a regulated document and sign-off system, such as Veeva, Purlin sits upstream
and produces evidence: what each rule claims, how that is shown, what ran, who ran it, what the
audit found, who wrote and last changed each rule, proof and test, and who signed, tied to one
commit. A person hands that evidence to the regulated system, which holds the controlled
document, the authority to sign it off and the signature that counts under the regulation.

**What you hand over.** The package and its sign-offs, from the tagged commit. The package's
`met` comes second, after the schema. How the package is shown, read and filed is the receiving
system's to decide, and so is which signers were entitled.

**What a Purlin sign-off is.** An engineering attestation: a person was shown the evidence
package of one version, looked at each hand check, typed what they saw where they had something
to say, and signed the package's fingerprint in one signed commit. It is evidence itself, filed
beside the package.

**A requirement's number** from the regulated system reaches the evidence in the rule's own
words:

```
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures (URS-042)
```

Purlin does nothing with the number. It reaches the package because the rule's words do, so the
receiving system can trace `URS-042` to the rule, its proofs, its tests, its results and its
authors, and to the sign-offs over the package that holds them.

**A version is signed on a branch of its own** where the team wants one, such as
`release/1.2.0`, cut from the default branch once its specs are done. New specs land on the
default branch and wait for the next version; a fix lands on the release branch, the developer
runs and commits the tests again there, and the fix is merged back.

Read next: [running-and-evidence.md](running-and-evidence.md) for the evidence a sign-off
reads, [specs-and-anchors.md](specs-and-anchors.md) for writing a proof a test can prove,
[audit.md](audit.md) for what the audit's findings mean.
