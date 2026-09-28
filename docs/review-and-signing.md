# Review and signing

For QA, or a developer acting as QA, at the `strong` or `signed` gate.

Reviewing is not reading every rule. It is reading the rules whose next step is a person, with
the evidence already gathered. `purlin:sign` computes one list, the **queue**, and walks it.
When it leaves every rule meeting the gate it writes the evidence package, commits it, and tags
that commit `signed/<version>`; you push the tag. This page says what puts a rule in the queue,
what the walk shows you, what makes a signature count, and what the tag carries.

## The level

Every rule has a **level**, `passed`, `strong` or `signed`, meaning what the gate means. A rule
says its own with `[level: passed]`, `[level: strong]` or `[level: signed]`, and a rule with no
tag takes the gate. The gate is the ceiling. A rule needs a signature exactly when its level is
`signed`. [hard_gates.md](../references/hard_gates.md#the-level) is the one home of the level.

## The queue

```
purlin:sign
```

No arguments and no prior reading. The walk opens on one line with the queue's counts:

```
Queue: 5 rules. 2 hand checks, 3 signatures.
```

Each row says what it needs:

| Need | When | What you do |
|---|---|---|
| `hand check` | the rule's level is `strong` or `signed` and its strong cell reads `manual test` (its proof is `@manual`) | check it yourself and sign with a line saying what you saw, or add a case |
| `signature` | the rule's level is `signed`, its passed and strong cells are met, and its signed cell reads `unsigned` or `stale` | read what the walk shows and sign, or add a case |

A rule that needs both is one `hand check` row: the note it is signed with meets the signed cell
too. A rule whose level is `passed` is never in the queue. The queue exists at the gate `strong`
and above, and its `signature` rows only at `signed`. Rows come by feature, then by rule number.

| The word the signed cell reads | What happened |
|---|---|
| `unsigned` | the rule needs a signature and none binds its current hashes |
| `stale` | a signature exists and the hashes it bound do not match |

Nothing else reaches the queue. A rule reading `not audited` waits for `purlin:audit`. A rule
with no proof, no test, a failing test or a `weak` strong cell is build work, and it stays on
the board where `purlin:build` finds it. A rule whose passed cell reads `out of date` waits for
the next `purlin:test`.

Under `passed` there is no queue. `purlin:sign` prints `sign: the gate is passed, which asks for
no signature.` and `sign: purlin:init --gate strong adds the test strength, the AI audit and the
queue.`, and writes nothing.

## What the walk shows

Each stop is headed with the feature, the rule, its level and what it needs, then shows the
rule text, each proof with its `@manual` or `@env` tag, and what the audit found:

```
login RULE-3   level signed   signature
Rule
  Five failed attempts lock the account for fifteen minutes.
Proof
  PROOF-4: the sixth attempt within fifteen minutes returns 423
What the audit found
  Strong. It found nothing.
login RULE-3   sign / case / skip:
```

A `signature` row whose signature is stale adds `stale: <reason>` to its heading. What the
audit found reads `Strong. It found nothing.`, `Weak.` with each finding, `Undecided.` with the
audit's own sentence, or `Nothing yet: no audit has read this rule's text, proof and test.`

The walk reports and recommends nothing: it says what was measured and what was seen, and you
decide. To read one rule in full beforehand, with its test body, the test strength beside
`min_strength` and the model that read it, run
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review/ai_audit.py" --feature <feature> --rule RULE-N`.
[running-and-evidence.md](running-and-evidence.md#purlinaudit) says how the audit reads a rule,
and [review_criteria.md](../references/review_criteria.md) is what it reads against.

## The three answers

**Sign.** The rule, the proof and the test belong together. On a hand check the walk asks
`What did you see, in one line:` and the answer becomes the signature's note.

**Case.** Say in plain language what is missing, such as "it should also reject an expired
token". The walk asks for it in one line, and it becomes a new proof line in the spec with the
next free proof id. The test is left for the next `purlin:build`. The walk writes specs and
signatures, never code.

**Skip.** Move on and leave the cells alone. A skipped rule is in the queue again next time:
nothing is marked as seen by being seen.

Never narrow a rule or a proof to make a finding disappear. That lowers the claim instead of
strengthening the evidence. A rule from an anchor is changed in the anchor's own repository.

The walk writes nothing until it closes, then makes one signed commit for every signature,
`sign(<feature>): RULE-N ...`, or `sign(batch): ...` across features. It closes by saying what
happened and what is left:

```
Walked 5 rules: 3 signed, 1 case added, 1 skipped.
  billing RULE-2   add this proof line: reject an expired token with 401
Commits: 4f1a9c2
→ Run: purlin:build
→ Run: purlin:sign
```

The first `→` line appears when a case was added, the second when a rule was skipped.

## The tag

A signature locks one rule. The tag locks the version.

When the walk leaves every rule meeting the gate, `purlin:sign` writes the evidence package,
`.purlin/evidence/package/<version>.json`, from the committed evidence, commits it as a signed
commit, and writes a signed tag on that commit with `git tag -s` and the key you sign commits
with. The tag is `signed/<version>`, from the `VERSION` file at the project root, or the
`version` in `.purlin/config.json` where there is none; `purlin:sign --release <name>` names it
something else. The tag's message names the gate and the evidence commit below the package.

```
Evidence package committed: .purlin/evidence/package/1.4.0.json.
Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate signed.
→ Run: git push origin signed/1.4.0
```

You push it; `purlin:sign` pushes nothing. It writes no tag, and says why, when:

| Line | Why |
|---|---|
| `No tag: 3 of 42 rules do not meet the gate signed.` | a rule falls short; `purlin:status` names what blocks it |
| `No tag: login is out of date (code changed since a1b2c3d).` | a feature's evidence is older than its spec, code or tests |
| `sign: login has evidence that is not committed. Run: purlin:test --commit` | evidence is written and not committed |
| `No tag: signed/1.4.0 is already written. Name another with --release <name>.` | the tag exists; an existing tag is never moved |
| `No tag: the evidence package was not committed: <why>.` | the package could not be written or committed |

The tag holds the whole tree, so the code, the evidence, the signatures and the package are
pinned together under one name. The package is one data file describing every rule of that
version, the thing you hand to a regulated system:
[package_format.md](../references/formats/package_format.md) holds its fields, and
[regulated-workflow.md](regulated-workflow.md) says what happens to it next. Where a project has
a remote runner, pushing the tag starts one last run that reruns the tests on a clean machine
and checks every signature against the tagged code.

## Signing outside the walk

```
purlin:sign <feature> RULE-N [RULE-M ...]        one rule, or several
purlin:sign <feature>                            every row of one feature in the queue
purlin:sign --batch                              every row in the queue
purlin:sign <feature> RULE-N --note "<text>"     a hand check: what you saw
```

Use these when you already know what you are signing; they sign with no stop. Each writes one
file per rule, `specs/<category>/<feature>.signatures/<RULE-N>.<hash8>.<signer-slug>.json`, and
makes one signed commit for all of them, so a batch of forty rules is one commit and forty files
that cannot conflict with anyone else's. It prints `Signed <n> rules in <sha7>.` and each rule,
then `→ Run: purlin:sign` once every rule meets the gate, because the walk is what writes the
tag.

`--note` is the one line a person writes where no test can be read: what they did and saw for a
`@manual` proof. It lands in the signature file's `note` field.

At the gate `strong`, a named rule that is not in the queue gets `sign: a signature is required
only under the gate signed. Writing it anyway.` and is signed. At `signed`, a named rule marked
`[level: passed]` or `[level: strong]` is refused with `sign: <feature> <RULE-N> is marked
[level: <level>]; it asks for no signature.` At `signed`, a rule of a spec with no `> Scope:`
line is refused, because a signature cannot be tied to the code it governs. Under `trust:
remote`, a rule with a test whose feature has no current `ci` run is refused with `sign:
<feature> <RULE-N> has no ci test run for this code; run purlin:test --remote first`.

A checkout with no signing key gets `Commit signing is not configured, so a signature you write
would not count. Run:` and the three commands that set it up:

```
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
```

Then upload the public key to the git host, under signing keys.

## What makes a signature count

A signature file binds four hashes: the rule text, the proof descriptions, the test files
behind them, and what the audit found. It also logs the level at the time, your email, the
machine and its `os`, the gate, and the evidence file it rested on.
[signature_format.md](../references/formats/signature_format.md) holds every field. Under
`signed` two conditions decide whether it counts, and the signed cell names the one that failed:

| The signature counts when | What the cell reads when it does not |
|---|---|
| The commit that added the file is signed and the signature verifies | `unsigned`, `the signing commit is not signed` |
| The bound rule, proof, test and audit hashes still match | `stale`, `hashes changed after the signature` or `audit findings changed after the signature` |

Who signed is logged, not policed: the file names you and git names the commit's author, and
nothing compares either with anything. Below `signed` a committed signature counts.

## What stales a signature

Changing the rule text, any of its proof descriptions, or a test file behind it. So does an
audit that finds something different: a new test strength, a new `verdict` or a new finding.
Each changes what the signature was given, so the signed cell reads `stale`, the rule returns to
the queue, and a person looks again. Running the same audit again over the same code changes
nothing. Marking the rule's level differently stales nothing: the level is logged, not compared.

Changing the code alone stales nothing. The passed cell reads `out of date` until the next run
clears it, and the tag waits for that run.

Read next: [team-workflow.md](team-workflow.md) for where the queue comes from,
[regulated-workflow.md](regulated-workflow.md) for the tag and the package in a regulated
setting, [specs-and-anchors.md](specs-and-anchors.md) for writing a proof a test can prove.
