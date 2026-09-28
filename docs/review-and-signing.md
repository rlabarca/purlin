# Review and signing

For QA, or an engineer acting as QA, at the `strong` or `signed` gate.

Reviewing is not reading every rule. It is reading the rules whose next step is a person, with
the evidence already gathered. `purlin:sign` computes one list, the **queue**, and walks it. When it
leaves every rule meeting the gate it writes the tag `signed/<version>`, and a person pushes it.
This page says what puts a rule in the queue, what the brief shows you, what makes a signature
count, and what the tag stands for.

`queue` is the word for what `purlin:sign` walks. The dashboard shows the same list as its
Queue tab, and `tab` belongs to the page.

## The level

Every rule has a **level**, `passed`, `strong` or `signed`, meaning what the gate means. A rule
says its own with a tag, `[level: passed]`, `[level: strong]` or `[level: signed]`, and a rule
with no tag takes the project's gate as its level. The gate is the ceiling: a mark above it is
read as the gate. The level decides three things:

- **the evidence the rule needs.** Level `passed` asks that its tests pass. Level `strong` asks
  that an audit also proved them worth trusting. Level `signed` asks for both and a signature.
- **whether the AI audit runs on it.** It runs on every rule whose level is `strong` or
  `signed` and on no other.
- **whether it needs a signature.** A rule needs one exactly when its level is `signed`.

## The queue

```
purlin:sign
```

No arguments and no prior reading. The skill computes the queue, prints one line with its
counts, then starts the walk.

```
Queue: 5 rules. 2 hand checks, 3 signatures.
```

The queue is one list of the rules that wait on a person. Each row says what it needs:

| Need | When | What you do |
|---|---|---|
| `hand check` | the rule's level is `strong` or `signed` and its strong cell reads `manual test` (every proof is `@manual`) or `unsettled` (the AI audit ran and could not settle whether the test proves the proof) | check it yourself and sign with a `--note` saying what you saw, or add a case |
| `signature` | the rule's level is `signed`, its passed and strong cells are met, and its signed cell reads `unsigned` or `stale` | read the brief and sign, or add a case |

A rule that needs both is one `hand check` row. A rule whose level is `passed` is never in the
queue. The queue exists at the gate `strong` and above, and its `signature` rows only at
`signed`, because no rule has a signed cell below it.

| The word the signed cell reads | What happened |
|---|---|
| `unsigned` | the rule needs a signature and none binds its hashes |
| `stale` | a signature exists and the hashes it bound no longer match |

Nothing else reaches the queue. A rule whose strong cell reads `not audited` waits for
`purlin:audit` rather than for you: its level is `strong` or `signed` and no audit has run on
this code yet. A rule with no proof written, a rule with no test, a failing rule and a weak rule
are all build work, and they stay on the board where `purlin:build` finds them. A rule whose
passed cell reads `out of date` is not in the queue: the signature stands, and the next run
clears the cell.

Rows come by feature, then by rule number. Arguments narrow the walk and never widen it:
`purlin:sign <feature>`, `purlin:sign <feature> RULE-N`. Plain language reaches the same place:
"what is waiting on a person", "show me the ones marked `signed`".

Under `passed` there is no queue at all: `purlin:sign` says the gate is `passed`, says what
`purlin:init --gate strong` would add, and stops.

## The brief

At each stop the walk shows a brief. The brief is the machine's report on one rule, and it
reports three things:

1. the test strength beside `min_strength`;
2. what the audit observed, each observation in one sentence naming the proofs it concerns;
3. whether the audit could settle the question.

**The brief recommends nothing.** It does not say the rule is ready, and it does not say what to
do. It says what was measured and what was seen, and you decide. That is the whole division of
labour: the machine observes, the person attests.

The brief writes no file. What the audit found is written into the feature's evidence,
`.purlin/evidence/local/<feature>.json`, as the rule's audit entry for its current hashes.
Your signature names that file and binds what the audit found, so what you were shown is
recoverable afterwards and a later audit that found something else stales the signature.
Reading the rule again for the same hashes leaves the entry as it was unless what it found
changed.

| Layer | What it reads | Runs at |
|-------|---------------|---------|
| Test strength | `test_strength` from the newest counting record, against `min_strength` | every level |
| The AI audit | the review criteria, the rule, its proofs and the source of each test | level `strong` or `signed` |

**Test strength** is the share of the deliberate breaks made to the code that the tests caught,
as an integer percent, or `n/a` when no engine ran. It says one thing: the tests noticed when
the behaviour changed. It does not say the tests prove the right rule. A rule can reach 90
percent on a proof that observes the wrong thing, and a correct proof of a small rule can sit
at 0 percent because nothing broke. Read it beside what the audit observed, never instead of it.

**The AI audit** runs on every rule whose level is `strong` or `signed` and on no other. It is
built from the review criteria verbatim and this rule's evidence, so it observes by the same
sentences you read. The criteria list what it looks for: no proof of a rule names a rejection, an error or a
boundary; a description names no literal, number or quoted string; a test body asserts nothing,
or asserts a literal against itself; a proof about a flow reads as a function call. Where the audit
settled and still observed something, the strong cell reads `weak` with that sentence as its
reason. It is asked to state what the test observes against what the proof names, and to say
when it cannot tell. When it cannot tell, the strong cell reads `unsettled`, and the
rule waits for you rather than for another run. Until the audit has run at all, the cell reads
`not audited`, and the rule waits for `purlin:audit`. Where no model could be reached at all
the brief says so and settles nothing: the strength answers on its own, and the cell does not
read `unsettled` for a question nobody asked.

## The three answers

Each stop is headed with the rule, its level and what it needs, such as
`login RULE-3   level signed   hand check`, then shows `Rule`, `Proof` and
`What the audit found`, and asks `sign / case / skip`.

**Sign.** The rule, the proof and the test belong together. On a hand check the walk first asks
`What did you see, in one line:` and records the answer as the note. The walk writes the
signature file and makes the signed commit, `sign(<feature>): RULE-N`. Collect several and
commit them together at the end.

**Case.** Say in plain language what is missing - "it should also reject an expired token" -
and the walk writes a new proof line into the spec with the next free proof id. The test is
left for the next `purlin:build`. The walk writes specs and signatures, never code. Where the
test does not prove the proof as written, add the missing case this way or change the proof,
alone or with AI help.

**Skip.** Move on and leave the cells alone. A skipped rule is in the queue again next time,
which is the intended behaviour: nothing is marked as seen by being seen.

Never narrow a rule or a proof to make an observation disappear. That lowers the claim instead of
strengthening the evidence. On a rule that came from an anchor it is not yours to change at
all: the change is a pull request against the anchor's source repository.

The walk closes by saying what happened and what is left:

```
Walked 5 rules: 3 signed, 1 case added, 1 skipped.
  billing RULE-2   add this proof line: reject an expired token with 401
Commits: 4f1a9c2, 9b3e07d
→ Run: purlin:build
→ Run: purlin:sign
```

The first `→` line appears when a case was added, the second when a rule is still in the queue.

With nothing left and every rule meeting the gate, the walk writes the tag and the last line is
`→ Run: git push origin signed/<version>`. With a rule still short it writes no tag and says so,
`No tag: 3 of 42 rules do not meet the gate signed.`, and `purlin:status` names what blocks
them.

## The tag

A signature locks one rule. The tag locks the version.

When the walk leaves every rule meeting the gate, `purlin:sign` writes a signed tag over
the current commit (`git tag -s`, with the key you sign commits with), named `signed/<version>`
from the `VERSION` file at the project root.
`purlin:sign --release <name>` names it something else. The message carries the commit and the
gate, and the walk closes on two lines:

```
Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate signed.
→ Run: git push origin signed/1.4.0
```

A person pushes it; the skill never pushes and never moves a tag that already exists. While any
rule falls short it writes none and prints `No tag: 3 of 42 rules do not meet the gate signed.`,
so the tag is the claim: every rule met the gate at this commit, as
[hard_gates.md](../references/hard_gates.md) defines it. It holds the whole tree, so the code, the records, the briefs and the
signatures are pinned together under one name, which is what an inspection is handed.

Where a project has a runner, pushing the tag starts one last run that reruns the tagged tests
on a clean machine, checks that every signature still binds the code the tag
points at, and checks that every record and brief under `ci/` came from the runner itself. A
red run there is the host's word that this version is not proven.

## Signing outside the walk

```
purlin:sign <feature> RULE-N [RULE-M ...]        one rule, or several
purlin:sign <feature>                            every row of one feature in the queue
purlin:sign --batch                              every row in the queue
purlin:sign <feature> RULE-N --note "<text>"     a hand check: what you saw
```

Use these when you already know what you are signing. Each shows the brief for the rule first,
because signing a rule you have not read is the one thing it must not help with. It writes one
file per rule under `specs/<category>/<feature>.signatures/` and makes one signed commit for all
of them, so a batch of forty rules is one commit and forty files that cannot conflict with
anyone else's.

`--note` is the one line a person writes where no test can speak: what they did and what they
saw for a `@manual` proof, or the judgment the model could not settle. It is allowed on any rule
whose strong cell reads `manual test` or `unsettled`, and it lands in the signature file's
`note` field.

Nobody is refused for who they are. The signature file names you and git names the commit's
author; no list says who may sign.

Under the `strong` gate a signature clears a `manual test` or `unsettled` cell, so
`purlin:sign <feature>` and `purlin:sign --batch` sign every row in the queue, for that feature
or for the project. A rule you name that is not in the queue needs no signature there, so the
skill says `sign: a signature is required only under the gate signed. Writing it anyway.` and
writes it. Under `signed` both forms sign the queue's hand check and signature rows, in the
order the walk uses. Under `passed` nothing is written at all:
the skill says the gate is `passed`, names what `purlin:init --gate strong` would add, and
stops.

## What makes a signature count

A signature file binds three hashes - the rule text, the proof descriptions, and the test files
behind them - plus the level at the time, what the audit observed, your email, the machine (host name) and `os` you signed on, the brief you read and the record you rested on. Under `signed`
two conditions decide whether it counts, and the signed cell names the one that failed:

| The signature counts when | What the cell reads when it does not |
|---|---|
| The commit that added the file is signed and the signature verifies | `the signing commit is not signed` |
| The bound rule, proof, test and audit hashes still match | `stale`, `hashes changed after the signature` |

Nothing else is read: a signature counts whoever last committed to the test file, and on
whatever commit carries it. Below `signed` a committed signature counts.

## What stales a signature

Changing the rule text, any of its proof descriptions, or the body of a test behind it. So does
a re-audit that observes something
different: a new strength, a new observation sentence, or a question it could settle before and
cannot now. Each of those changes what the signature was given about, so the signed cell reads
`stale`, the rule returns to the queue, and a person looks again. Re-marking the rule's
level stales nothing: the signature records the level but does not lock it.

Changing the code alone stales nothing. The passed cell reads `out of date` until the next run
clears it, and no person is asked to look.

Read next: [team-workflow.md](team-workflow.md) for where the queue comes from,
[regulated-workflow.md](regulated-workflow.md) for signed commits and the tag,
[specs-and-anchors.md](specs-and-anchors.md) for writing a proof that a test can prove.
