# Review and signing

For QA, or an engineer acting as QA, at the `strong` or `signed` gate.

Reviewing is not reading every rule. It is reading the rules whose next step is a person, the
ones with the higher bar first, with the evidence already gathered. `purlin:sign` computes two
lists and walks them: the Review list, then the Sign list. When it leaves every rule meeting
the gate it writes the tag `signed/<version>`, and a person pushes it. This page says what puts
a rule on each list, what the brief shows you, what makes a signature count, and what the tag
stands for.

`list` is the word for what `purlin:sign` walks. The dashboard shows the same two as its Review
tab and its Sign tab, and `tab` belongs to the page.

## The bar

Every rule has a **bar**, `passed` or `strong`: the evidence that rule must have before anyone
can sign it. A rule says its own with a tag, `[bar: passed]` or `[bar: strong]`, and a rule
with no tag takes the project's gate as its bar. The bar decides three things:

- **the evidence the rule needs.** Bar `passed` asks that its tests pass. Bar `strong` asks
  that an audit proved them worth trusting.
- **whether the AI audit runs on it.** It runs on every rule whose bar is `strong` and on no
  other.
- **whether it needs a signature.** Under `signed`, a rule needs one when the project's
  `sign_at` is `all`, or when its own bar is `strong`.

A rule that has met its bar has **cleared** it, and a rule that has cleared its bar and is
still waiting for a signature is **signable**. That is the whole of what `signable` means.

## Review

```
purlin:sign
```

No arguments and no prior reading. The skill asks for the two lists, prints one line holding
both counts, then starts the walk with Review.

```
Review: 7 rules. Sign: 5 rules.
```

A rule is on the Review list when its strong cell reads one of three words, each of them work
only a person can do:

| The word | What happened | What you do |
|---|---|---|
| `manual test` | every proof of the rule is `@manual`, so no test can be written | run the test yourself and sign with a note |
| `unsettled` | the AI audit ran and could not settle whether the test proves the proof | judge it yourself: sign, add a case, or hold |
| `held` | someone committed a hold saying the test does not prove the proof | write the case, or lift the hold by signing |

Nothing else reaches it. A rule whose strong cell reads `not audited` waits for `purlin:audit`
rather than for you: its bar is `strong` and no audit has run on this code yet. A drafted rule,
a rule with no test, a failing rule and a weak rule are all build work, and they stay on the
board where `purlin:build` finds them. A rule whose passed cell reads `code changed` is on
neither list: only the code moved, the signature stands, and the next run clears the cell.

Rows come bar `strong` first, then by feature and rule id. Arguments narrow the walk and never
widen it: `purlin:sign <feature>`, `purlin:sign <feature> RULE-N`. Plain language reaches the
same place: "what is waiting on a person", "show me the ones with the strong bar".

Under `passed` there is no list at all: `purlin:sign` says the gate is `passed`, says what
`purlin:init --gate strong` would add, and stops.

## Sign

The Sign list is the signable rules that no counting signature covers yet: they have cleared
their bar, they need a signature, and their signed cell reads `unsigned`, `stale` or `held`. It
exists at `signed` and nowhere else, because no rule has a signed cell below it.

| The word the signed cell reads | What happened |
|---|---|
| `unsigned` | the rule needs a signature and none binds its hashes |
| `stale` | a signature exists and the hashes it bound no longer match |
| `held` | someone committed a hold saying the test does not prove the proof |

The walk reaches Sign after Review, because a rule a person has not judged is not a rule to
sign. `sign_at` decides which rules need a signature at all: `strong` asks for one on the rules
whose bar is `strong`, and `all` asks for one on every rule. `purlin:init` sets it at the
`signed` gate and `--update` asks again.

## The brief

At each stop the walk shows a brief. The brief is the machine's report on one rule, and it
reports three things:

1. the test strength beside `min_strength`;
2. what the audit observed, each observation in one sentence naming the proofs it concerns;
3. whether the audit could settle the question.

**The brief recommends nothing.** It does not say the rule is ready, and it does not say what to
do. It says what was measured and what was seen, and you decide. That is the whole division of
labour: the machine observes, the person attests.

The brief is written under `.purlin/briefs/<source>/<feature>/<RULE-N>.<hash8>.brief.json` and
committed beside the records. That file is evidence: your signature names it and binds what it
said, so what you were shown is recoverable afterwards and a later audit that saw something
else stales the signature. Reading the brief again for the same hashes leaves the file as it was
unless what it found changed. The `.brief.txt` beside it is a local view, and `.gitignore` keeps
it out of every commit.

| Layer | What it reads | Runs at |
|-------|---------------|---------|
| Test strength | `test_strength` from the newest counting record, against `min_strength` | every bar |
| The AI audit | the review criteria, the rule, its proofs and the source of each test | bar `strong` |

**Test strength** is the share of the deliberate breaks made to the code that the tests caught,
as an integer percent, or `n/a` when no engine ran. It says one thing: the tests noticed when
the behaviour changed. It does not say the tests prove the right rule. A rule can reach 90
percent on a proof that observes the wrong thing, and a correct proof of a small rule can sit
at 0 percent because nothing broke. Read it beside what the audit observed, never instead of it.

**The AI audit** runs on every rule whose bar is `strong` and on no other. It is built from the
review criteria verbatim and this rule's evidence, so it observes by the same sentences you
read. The criteria list what it looks for: no proof of a rule names a rejection, an error or a
boundary; a description names no literal, number or quoted string; a test body asserts nothing,
or asserts a literal against itself; an `@e2e` proof reads as a function call. Where the audit
settled and still observed something, the strong cell reads `weak` with that sentence as its
reason. It is asked to state what the test observes against what the proof names, and to say
when it cannot tell. When it cannot tell, the strong cell reads `unsettled`, and the
rule waits for you rather than for another run. Until the audit has run at all, the cell reads
`not audited`, and the rule waits for `purlin:audit`. Where no model could be reached at all
the brief says so and settles nothing: the strength answers on its own, and the cell does not
read `unsettled` for a question nobody asked.

For a rule tagged `origin: design`, the brief shows the pinned mock from `designs/<feature>/`
beside the screenshot the test captured under `.purlin/runtime/attachments/`. Judge what a
person would see: the text, the order, the states present. See
[design-in-specs.md](design-in-specs.md).

## The four answers

**Sign.** The rule, the proof and the test belong together. The walk writes the signature file
and makes the signed commit, `sign(<feature>): RULE-N`. Collect several and commit them
together at the end.

**Add a case.** Say in plain language what is missing - "it should also reject an expired
token" - and the walk writes a new proof line into the spec with the next free proof id. The
test is left for the next `purlin:build`. The walk writes specs and signatures, never code.

**Hold.** The test does not prove the proof as written - it calls two helpers apart where the
proof names the function that joins them - and a new proof line would not fix that. Name the
missing case and the walk commits a hold, `hold(<feature>): RULE-N`. The machine cannot see
that gap, which is why a hold is the one thing that stops a rule reaching `strong` on the
measurements alone. Changing the test ends the hold.

**Skip.** Move on and leave the cells alone. A skipped rule is on the list again next time,
which is the intended behaviour: nothing is marked as seen by being seen.

Never narrow a rule or a proof to make an observation disappear. That lowers the claim instead of
strengthening the evidence. On a rule that came from an anchor it is not yours to change at
all: `purlin:anchor propose <name>` drafts that change where the rule lives.

The walk closes by saying what happened and what is left:

```
Walked 12 rules: 8 signed, 1 case added, 1 held, 2 skipped.
  billing RULE-2   add this proof line: reject an expired token with 401
Commits: 4f1a9c2, 9b3e07d
→ Run: purlin:build
→ Run: purlin:sign
```

The first `→` line appears when a case was added, the second when a rule is still on a list.

With nothing left and every rule meeting the gate, the walk writes the tag and the last line is
`→ Run: git push origin signed/<version>`. With a rule still short it writes no tag and says so,
`No tag: 3 of 42 rules do not meet the gate signed.`, and `purlin:status` names what blocks
them.

## The tag

A signature locks one rule. The tag locks the version.

When the walk leaves every rule meeting the gate, `purlin:sign` writes an annotated tag over
the current commit, named `signed/<version>` from the `VERSION` file at the project root.
`purlin:sign --release <name>` names it something else. The message carries the commit and the
gate, and the walk closes on two lines:

```
Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate signed.
→ Run: git push origin signed/1.4.0
```

A person pushes it; the skill never pushes and never moves a tag that already exists. While any
rule falls short it writes none and prints `No tag: 3 of 42 rules do not meet the gate signed.`,
so the tag is the claim: every rule met the gate at this commit. It holds the whole tree, so the code, the records, the briefs and the
signatures are pinned together under one name, which is what an inspection is handed.

Where a project has a runner, pushing the tag starts one last run that reruns the tagged tests
on a clean machine, checks that every signature and every hold still binds the code the tag
points at, and checks that every record and brief under `ci/` came from the runner itself. A
red run there is the host's word that this version is not proven.

## Signing outside the walk

```
purlin:sign <feature> RULE-N [RULE-M ...]        one rule, or several
purlin:sign <feature>                            every signable rule of one feature
purlin:sign --batch                              everything currently signable
purlin:sign <feature> RULE-N --hold "<case>"     the test does not prove the proof
purlin:sign <feature> RULE-N --note "<text>"     a @manual proof, or a review that did not settle
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

If your email is not in `signers` in `.purlin/config.json`, the skill stops and says
`sign: <email> is not on the signer list. Add it by pull request, or ask someone on it.` With no
list at all under the `signed` gate it says
`sign: signer list missing: run purlin:init --gate signed`.

Under the `strong` gate nothing asks for a signature, so a bare signature says
`sign: a signature is required only under the gate signed. Writing it anyway.` and writes it.
The file still clears a `manual test`, `unsettled` or `held` cell, from anyone: at `strong`
the signer list is not read. Under `signed` the signer rules apply in full. Under `passed` nothing is written at all:
the skill says the gate is `passed`, names what `purlin:init --gate strong` would add, and
stops.

## What makes a signature count

A signature file binds three hashes - the rule text, the proof descriptions, and the test files
behind them - plus the pinned design for an `origin: design` rule, the bar at the time, what
the audit observed, your email, the brief you read and the record you rested on. These conditions decide whether it
counts, and the signed cell names the one that failed:

| The signature counts when | What the cell reads when it does not |
|---|---|
| The commit that added the file is signed and the host verifies it | `the signing commit is not signed` |
| The author's email is on `signers` as of that commit | `the signer is not on the list` |
| That author did not author the last commit to the test file | `the signer last touched the test` |
| The bound rule, proof, test and bar hashes still match | `hashes changed after the signature` |
| What the audit observed is still what it observed then | `hashes changed after the signature` |
| Under `signed`, the commit is on the protected branch | `the signing commit is not on <branch>` |

## What stales a signature

Changing the rule text, any of its proof descriptions, the body of a test behind it, the pinned
design for a design rule, or the rule's bar. So does a re-audit that observes something
different: a new strength, a new observation sentence, or a question it could settle before and
cannot now. Each of those changes what the signature was given about, so the signed cell reads
`stale`, the rule returns to the Sign list, and a person looks again.

Changing the code alone stales nothing. The passed cell reads `code changed` until the next run
clears it, and no person is asked to look.

Read next: [team-workflow.md](team-workflow.md) for where the Review list comes from,
[regulated-workflow.md](regulated-workflow.md) for the signer list and signing,
[specs-and-anchors.md](specs-and-anchors.md) for writing a proof that a test can prove.
