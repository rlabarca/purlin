# Review and signing

For QA, or a developer acting as QA, at any gate.

`purlin:sign` is how a person signs. With no argument it walks the rules left to do as
`to test by hand` or `to sign`, one at a time, with the evidence already gathered, and you
answer each. At the gate `signed`, when nothing but the tag is left and every result came from
committed work, it writes the evidence package, commits it, and tags that commit
`signed/<version>`; you push the tag. At `passed` and `strong` it signs hand checks and writes no
tag and no package. This page says what waits for a person, what the walk shows you, what makes a
signature count, and what the tag carries. [hard_gates.md](../references/hard_gates.md) is the
one home of the gate and of the tag.

## What waits for a person

Two lines of `Left to do` are a person's work, and both name `purlin:sign`:

| The line | A rule is on it when | What you do |
|---|---|---|
| `<n> rules to test by hand: purlin:sign` | a proof of the rule is `@manual` and nobody has checked it by hand; at every gate | carry the proof out yourself and sign, with a line saying what you saw when you give one |
| `<n> rules to sign: purlin:sign` | at the gate `signed`, every other kind of work on the rule is done and no signature counts for it as it stands | read what the walk shows and sign |

A rule is on one line of `Left to do` at a time, the first that applies, and every other line
names another command: a rule `to audit` waits for `purlin:audit`, a rule `to strengthen` for
`purlin:build`, a rule `to tie to its files` for `purlin:spec`.
[hard_gates.md](../references/hard_gates.md), "When a version is finished", lists every kind.

At the gate `signed` a rule's signed cell reads one of three words:

| Word | What it says |
|---|---|
| `signed` | a signature that counts matches the rule as it stands |
| `unsigned` | none does: none was made, or what one was made over changed |
| `waiting` | the strong cell below it is not met, `waiting for the audit` |

## The walk

```
purlin:sign
```

The walk opens on the two lines it walks, or on
`Nothing is waiting for someone to test by hand or to sign.` It stops at the rules in order of
feature name, then rule number, so `RULE-2` comes before `RULE-10`. Each stop is headed with the
feature, the rule and its work left, then shows the rule, each proof with its `@manual` or `@env`
tag, and what the audit found, and asks for one answer. A walk at the gate `signed` over three
rules, answered `sign`, `case` and `sign`:

```
1 rule to test by hand: purlin:sign
2 rules to sign: purlin:sign

login RULE-1   to sign
Rule
  The right email and password sign the user in
Proof
  PROOF-1: Signing in as `ada@example.com` with her password `secret` is answered with the status `200`
What the audit found
  Strong. It found nothing.
login RULE-1   sign / case / skip: sign

login RULE-2   to sign
Rule
  Five wrong passwords in a row lock the account
Proof
  PROOF-2: After five wrong passwords for `ada@example.com`, signing in with the right one is answered with the status `423`
What the audit found
  Strong. It found nothing.
login RULE-2   sign / case / skip: case
  in one line: a sign-in 15 minutes after the lock is answered with 200

login RULE-3   to test by hand
Rule
  The refusal messages follow the brand voice guide
Proof
  PROOF-3 (@manual): Read each refusal message against the brand voice guide
What the audit found
  No audit has read this rule's text, proof and test yet.
login RULE-3   sign / case / skip: sign
What did you see, in one line: Each refusal reads as the guide asks.

Walked 3 rules: 2 signed, 1 case added, 0 skipped.
  login RULE-2   add this proof line: a sign-in 15 minutes after the lock is answered with 200
Signed 2 rules as jane@acme.com with the key ending ...K0hI.
Commits: 8fbd2ea
3 rules. 3 pass their tests. 3 are strong. 2 are signed.
Left to do:
  1 rule to sign: purlin:sign
```

Under `What the audit found` a stop reads `No audit has read this rule's text, proof and test yet.`,
`Strong. It found nothing.`, or `Strong.`, `Weak.` or
`Undecided. The AI audit could not decide, so the rule reads weak until its proof or test changes.`
followed by each finding on a line of its own.

The walk says what was measured and what was seen, and you decide. Before anything is written,
`purlin:sign` reads each rule in full with `scripts/review/ai_audit.py`: the rule, its proofs,
each test's source, the test strength beside `min_strength` where it was measured, and what the
last audit found with the model that read it.
[review_criteria.md](../references/review_criteria.md) is what the audit reads a rule against.

## The three answers

**Sign.** The rule, the proof and the test belong together. At a hand check the walk then asks
`What did you see, in one line:`, and the line becomes the signature's note; an empty line signs
with no note.

**Case.** Say in plain language what is missing, such as "a sign-in 15 minutes after the lock is
answered with 200". The walk asks for it on one line and closes with
`add this proof line:` and the case. `purlin:sign` writes it into the spec as a new proof line
with the next free proof id and leaves its test for the next `purlin:build`. It writes specs and
signatures, never code.

**Skip.** Move on and leave the rule as it is. A skipped rule is still `to sign` or
`to test by hand` after the walk, and no file records the skip.

Never narrow a rule or a proof to make a finding disappear: that lowers the claim instead of
strengthening the evidence.

The walk writes nothing until it closes, then makes one signed commit for every signature it
carries, `sign(<feature>): RULE-N ...`, or `sign(batch): ...` across features. It closes with
`Walked <n> rules: ...`, each case to add, `Signed <n> rules as <email> with the key ending
...<last 4>.` and the commit, then ends on the summary and `Left to do`, or, at the gate `signed`,
on what the tag says.

## Signing outside the walk

```
purlin:sign <feature> RULE-N [RULE-M ...]        one rule, or several
purlin:sign <feature>                            every waiting rule of one feature
purlin:sign --all                                every waiting rule
purlin:sign <feature> RULE-N --note "<text>"     a hand check, with what you saw
```

These sign with no stop, at every gate. A rule named by id is signed whatever work it has left.
Each writes one file per rule,
`specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, and makes one signed
commit for all of them, so forty rules are one commit and forty files that cannot conflict with
anyone else's. An anchor's rule gets one file for each feature it applies to. A hand check signed
by name:

```
Signed 1 rule as jane@acme.com with the key ending ...K0hI.
  login RULE-3
3 rules. 3 pass their tests. 3 are strong. 1 is signed.
Left to do:
  2 rules to sign: purlin:sign
```

A rule no spec has is named last, just above the summary, and the rules named beside it are
signed all the same; the command exits 1:

```
Signed 1 rule as jane@acme.com with the key ending ...K0hI.
  login RULE-1
login RULE-9 is not a rule any spec has. Run purlin:status login to see its rules.
3 rules. 3 pass their tests. 3 are strong. 2 are signed.
Left to do:
  1 rule to sign: purlin:sign
```

The walk is what writes the tag. Once `--all` or a named rule has signed the last rule,
`Left to do` reads `the version to tag: purlin:sign`, and `purlin:sign` with no argument writes
it.

At the gate `signed` a rule of a spec that names no files in `> Scope:` is signed all the same,
and its signature does not count until the spec names them. Its line says so and names the
command that adds them:

```
Signed 1 rule as jane@acme.com with the key ending ...K0hI.
  login RULE-1   does not count until the spec names its files: purlin:spec login
3 rules. 2 pass their tests. 2 are strong. 0 are signed.
Left to do:
  1 rule to test by hand: purlin:sign
  2 rules to tie to their files: purlin:spec
```

Purlin signs with an SSH key, any key. A checkout with none gets the commands that set one up,
writes no signature and exits 1; the `ssh-keygen` line shows only while that key file does not
exist:

```
No key to sign with. These commands set one up:
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
  git config gpg.format ssh
  git config user.signingkey ~/.ssh/id_ed25519.pub
```

`purlin:sign` shows you the commands, offers to run them, and carries on once they ran.

## What makes a signature count

A signature is made over six things: the rule text, its proof text, its test, the code the
feature's `> Scope:` lists, what the audit found, and the machine each system's tests ran on. The
file records the signer's email and name as git holds them, the key's fingerprint, the time, the
gate, the evidence file it rested on and the note.
[signature_format.md](../references/formats/signature_format.md) holds every field.

At every gate a signature counts when both of these hold:

| The signature counts when | What the signed cell reads when it does not |
|---|---|
| The last commit that touched its file carries a signature, made with any key | `unsigned`, with the reason `the commit that added it is not signed` |
| What it was made over still hashes to what it was made over | `unsigned`, and the rule is `to sign` again |

Purlin records who signed and with which key, and does not decide who may sign: a signature counts
whoever wrote it, and on whatever branch carries it.

## What ends a signature

A change to the rule text, a proof's text, the test, or a file the feature's `> Scope:` lists ends
every signature it covers. So does an audit that finds something different, and a run on another
machine for a system the signature covers. A signature that ends says nothing: its rule returns to
`to sign`, or, for a hand check, to `to test by hand`. After a change to `src/login.py`, the one
file `login` lists, the next test run reads:

```
Selected 1 of 1 feature: login (code changed since 1e7b7e4).
```

and ends on:

```
3 rules. 2 pass their tests. 2 are strong. 0 are signed.
Left to do:
  1 rule to test by hand: purlin:sign
  2 rules to sign: purlin:sign
```

Running the same audit again over the same code ends nothing, and neither does a result from a
system the signature does not cover. An anchor's rule is signed once in each feature it applies
to, and a change to one feature's files ends that one signature.

## The tag

A signature locks one rule. The tag locks the version.

At the gate `signed`, when the walk leaves nothing but the tag, `purlin:sign` writes the evidence
package, `.purlin/evidence/package/<version>.json`, commits it as a signed commit
`purlin: evidence at <sha7>`, and writes a signed tag on that commit with `git tag -s`, signed
with the key `user.signingkey` names. The tag is `signed/<version>`. The version is read from the
`VERSION` file at the project root, then the `version` of `package.json`, then `[project]` and
then `[tool.poetry]` `version` in `pyproject.toml`, then `<Version>` in a `*.csproj` at the root;
`purlin:sign --release <name>` tags `signed/<name>` instead. The tag's message reads
`Nothing left to do at the gate signed.`, then the commit and the gate.

```
Nothing is waiting for someone to test by hand or to sign.
Evidence package committed: .purlin/evidence/package/1.4.0.json.
Tagged signed/1.4.0 at 698261b.
Nothing left to do. Push the tag to release it: git push origin signed/1.4.0
```

You push it; `purlin:sign` pushes nothing. It writes no tag, and says why, when:

| What it prints | Why |
|---|---|
| The summary and `Left to do` | work other than the tag is left |
| `No tag: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:sign.` | `git status` lists a path outside `.purlin/` |
| `No tag: <feature> has results that are not committed. Run purlin:test --commit.` | a feature's results are written and not committed |
| `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` | no version is stated and no `--release` is given |
| `No tag: signed/1.4.0 is already written. Run purlin:sign --release <name> to name another.` | the tag exists; a tag that exists is never moved |
| `No tag: the committed evidence still has work left to do, so no evidence package was committed. Run purlin:test --commit, then purlin:sign.` | the package, read from the committed evidence, finds work left |
| `No tag: the evidence package was not committed: <why>.` | the package could not be written or committed |
| `No tag: git could not write signed/<version>: <git's own message>.` | git refused the tag |

With no version stated, `purlin:sign` asks you for one and offers to write it to a `VERSION` file.
The command exits 0 when the tag already exists and 1 for every other refusal.

The tag holds the whole tree, so the code, the evidence, the signatures and the package are pinned
together under one name. The package is one data file describing every rule of that version, the
thing you hand to a regulated system: [package_format.md](../references/formats/package_format.md)
holds its fields, and [regulated-workflow.md](regulated-workflow.md) says what happens to it next.
Where a project has a remote runner, pushing the tag starts a tag run, which runs the tests tied
to proofs tagged for the runner's system and writes nothing.

Read next: [regulated-workflow.md](regulated-workflow.md) for the tag and the package in a
regulated setting, [raising-the-gate-and-upgrading.md](raising-the-gate-and-upgrading.md) for the
move to the gate `signed`, [specs-and-anchors.md](specs-and-anchors.md) for writing a proof a test
can prove.
