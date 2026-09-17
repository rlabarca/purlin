# Review and signing

For QA, or an engineer acting as QA, at the `strong` or `signed` gate.

Reviewing is not reading every rule. It is reading the rules whose next step is a person, in
risk order, with the evidence already gathered. `purlin:sign` computes that list and walks it.
This page says what puts a rule on the list, what the brief shows you, and what makes a
signature count.

## The review list

```
purlin:sign
```

No arguments and no prior reading. The skill asks for the list, prints the count by risk and
the first few rows, then starts the walk.

```
Review list: 12 rules need a person, across 4 features
  high 3   medium 6   low 3

  login       RULE-3   high     stale: the rule text changed after the signature
  login       RULE-7   high     manual audit: the model review did not settle
  billing     RULE-2   high     unsigned
```

A rule is on the list when the cell that blocks it is one only a person can answer:

| The blocking cell | The word it reads | What happened |
|---|---|---|
| strong | `manual test` | every proof of the rule is `@manual`, so a person runs the test |
| strong | `manual audit` | no brief binds the current hashes, or the model review could not settle |
| strong | `held` | someone committed a hold saying the test does not prove the proof |
| signed | `unsigned` | the rule is at or above `sign_at` and no signature binds its hashes |
| signed | `stale` | a signature exists and the hashes it bound no longer match |
| signed | `held` | someone committed a hold saying the test does not prove the proof |

Nothing else reaches it. A drafted rule, a rule with no test, a failing rule and a weak rule are
all build work, and they stay on the board where `purlin:build` finds them. A rule whose passed
cell reads `code changed` is not on the list either: only the code moved, the signature stands,
and CI clears the cell on the next run.

Rows are grouped by risk with high first, and within a group the stale and held rules come
before the rest. Arguments narrow the walk and never widen it: `purlin:sign <feature>`,
`purlin:sign <feature> RULE-N`. Plain language reaches the same place: "what is waiting on a
person", "show me the high risk ones".

Under the `strong` gate the list is the `manual test`, `manual audit` and `held` rules alone,
because no rule has a signed cell there. Under `passed` there is no list at all: `purlin:sign` says the gate is
`passed`, says what `purlin:init --gate strong` would add, and stops.

## The brief

At each stop the walk shows a brief. The brief is the machine's report on one rule, and it
reports four things:

1. the test strength beside `min_strength`;
2. the free-check findings on the proof text;
3. the free-check findings on the test body;
4. what the model review observed, and whether it could settle the question.

**The brief recommends nothing.** It does not say the rule is ready, and it does not say what to
do. It says what was measured and what was seen, each in one sentence naming the proofs it
concerns, and you decide. That is the whole division of labour: the machine observes, the
person attests.

The brief is written under `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json` and committed
by CI beside the records. That file is evidence: your signature names it, so what you were shown
is recoverable afterwards. Reading the brief again for the same hashes leaves the file as it was
unless what it found changed. The `.brief.txt` beside it is a local view, and `.gitignore` keeps
it out of every commit.

| Layer | What it reads | Runs at |
|-------|---------------|---------|
| The free checks on the proof text | the proof description and its tier tag alone | every risk |
| The free checks on the test body | the marked test body, no execution | every risk |
| Test strength | `test_strength` from the newest counting record, against `min_strength` | medium and high |
| The model review | the criteria plus this rule's evidence | when `ai_review_at` says so |

The first two layers are free in both senses: nothing runs and nothing is charged. They read a
spec written before any code exists, which is why a proof can be wrong before a test is ever
written.

**Findings on the proof text.** `no_expected_value` when the description names no literal,
number, quoted string or named constant. `vague_verb` when it says "works" or "correctly" with
no value beside it. `missing_trigger` when nothing runs before the assertion. `tier_mismatch`
when an `@e2e` proof is described as a function call. Those four keep the spec status at
`drafted`. `implementation_coupling` names a private symbol, a selector or a source path
instead of an observable; `happy_path_only` means no proof of this rule names a rejection, an
error or a boundary. Those two are advisory, except that `happy_path_only` blocks at high risk.

**Findings on the test body.** `no_assertion`, `tautology`, `assert_true_literal`,
`bare_except`, `logic_mirroring` and `mock_of_target`. A finding here is structural: no model
judgment overrides it and no edit to the spec clears it. Only editing the test does.

**Test strength** is the share of the deliberate breaks made to the code that the tests caught,
as an integer percent, or `n/a` when no engine ran. It says one thing: the tests noticed when
the behaviour changed. It does not say the tests prove the right rule. A rule can reach 90
percent on a proof that observes the wrong thing, and a correct proof of a small rule can sit
at 0 percent because nothing broke. Read it beside the findings, never instead of them.

**The model review** runs when `ai_review_at` allows it: never at `passed`, at high risk under
`strong`, at medium and high under `signed`. It is built from the review criteria verbatim plus
this rule's evidence, so it observes by the same sentences you read. It is asked to state what
the test observes against what the proof names, and to say when it cannot tell. When it cannot
tell, the strong cell reads `manual audit` with the reason `review not settled`, and the rule
waits for you rather than for another run.

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

Never narrow a rule or a proof to make a finding disappear. That lowers the claim instead of
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

The first `→` line appears when a case was added, the second when a rule is still on the list.
With nothing left, the line names the next step for the gate: the pull request under `signed`,
`purlin:status` under `strong`.

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
whose strong cell reads `manual test` or `manual audit`, and it lands in the signature file's
`note` field.

If your email is not in `signers` in `.purlin/config.json`, the skill stops and says
`sign: <email> is not on the signer list. Add it by pull request, or ask someone on it.` With no
list at all under the `signed` gate it says
`sign: signer list missing: run purlin:init --gate signed`.

Under the `strong` gate a signature is not required by anything, so a bare signature says
`sign: a signature is required only under the gate signed. Writing it anyway.` and writes it.
The file still clears a `manual test`, `manual audit` or `held` cell, from anyone: at `strong`
the signer list is not read. Under `signed` the signer rules apply in full. Under `passed` nothing is written at all:
the skill says the gate is `passed`, names what `purlin:init --gate strong` would add, and
stops.

## What makes a signature count

A signature file binds three hashes - the rule text, the proof descriptions, and the test files
behind them - plus the pinned design for an `origin: design` rule, the risk at the time, your
email, the brief you read and the record you rested on. These conditions decide whether it
counts, and the signed cell names the one that failed:

| The signature counts when | What the cell reads when it does not |
|---|---|
| The commit that added the file is signed and the host verifies it | `the signing commit is not signed` |
| The author's email is on `signers` as of that commit | `the signer is not on the list` |
| That author did not author the last commit to the test file | `the signer last touched the test` |
| The bound rule, proof, test and risk hashes still match | `hashes changed after the signature` |
| Under `signed`, the commit is on the protected branch | `the signing commit is not on <branch>` |

The last of them is why a signature living only on a side branch does not let a change merge.

## What stales a signature

Changing the rule text, any of its proof descriptions, the body of a test behind it, the pinned
design for a design rule, or the rule's risk. Each of those changes what the signature was given
about, so the signed cell reads `stale`, the rule returns to the review list, and a person looks
again.

Changing the code alone stales nothing. The passed cell reads `code changed` until CI runs again
and clears it, and no person is asked to look.

Read next: [team-workflow.md](team-workflow.md) for where the review list comes from,
[regulated-workflow.md](regulated-workflow.md) for the signer list and signing,
[specs-and-anchors.md](specs-and-anchors.md) for writing a proof that a test can prove.
