# Review and approval

For QA, or an engineer acting as QA, at the `recorded` or `approved` gate.

Reviewing is not reading every rule. It is reading the rules something has changed about, in
risk order, with the evidence already gathered. `purlin:review` computes that list and walks
it. This page says what puts a rule on the list, what the brief shows you, and what makes an
approval count.

## The review list

```
purlin:review
```

No arguments and no prior reading. The skill asks for the list, prints the count by risk and
the first few rows, then starts the walk.

```
Review list: 12 rules across 4 features
  high 3   medium 6   low 3

  login       RULE-3   high     stale: rule text changed
  login       RULE-7   high     no negative case
  billing     RULE-2   high     recorded, never reviewed
```

A rule is on the list when any one of these holds:

| Reason | What happened |
|--------|---------------|
| Stale | the rule text, the proof text or the test body changed after the approval |
| Reviewed, not approved | a brief exists for the current hashes and nobody has acted on it |
| Recorded, never reviewed | the rule has a counting record and no approval of any age |
| No negative case | every proof for the rule asserts a success path |

High risk first, then medium, then low; within a level, the oldest record first. Under
`approved`, low risk is auto-approved by CI and appears only when auto-approval declined.

A rule flagged `re-verify pending` is never on the list. Only the code changed, the approval
stands, and CI clears it on the next run. Nobody is asked to look at one. A rule whose approval
is current is off the list too, whatever its risk, until that approval goes stale.

Arguments narrow the walk and never widen it: `purlin:review <feature>`,
`purlin:review <feature> RULE-N`, `purlin:review --risk high`, `purlin:review --origin design`.
Plain language reaches the same place: "what needs reviewing", "show me the high risk ones".

## The brief

At each stop the walk shows a brief. The brief answers one question - does this test prove this
rule? - and it gathers the evidence in layers, cheapest first, stopping when it has enough for
the rule's risk.

The brief is written beside the approval it informs as `<RULE-N>.<hash8>.brief.json`. That file
is evidence: CI commits it, the rule reads Reviewed because it exists, and your approval names
it. Reading the brief again for the same hashes leaves the file as it was unless what the brief
found changed. The `.brief.txt` beside it is a local view, and `.gitignore` keeps it out of every
commit.

| Layer | What it reads | Runs at |
|-------|---------------|---------|
| The free checks on the proof text | the proof description and its tier tag alone | every risk |
| The free checks on the test body | the marked test body, no execution | every risk |
| Test strength | `test_strength` from the latest record, against `min_strength` | medium and high |
| The model review | the criteria plus this rule's evidence | when `ai_review_at` says so |

The first two layers are free in both senses: nothing runs and nothing is charged. They read a
spec written before any code exists, which is why a proof can be wrong before a test is ever
written.

**Findings on the proof text.** `no_expected_value` when the description names no literal,
number, quoted string or named constant. `vague_verb` when it says "works" or "correctly" with
no value beside it. `missing_trigger` when nothing runs before the assertion. `tier_mismatch`
when an `@e2e` proof is described as a function call. Those four keep a rule out of Proof
ready. `implementation_coupling` names a private symbol, a selector or a source path instead of
an observable; `happy_path_only` means no proof of this rule names a rejection, an error or a
boundary. Those two are advisory, except that `happy_path_only` is blocking at high risk.

**Findings on the test body.** `no_assertion`, `tautology`, `assert_true_literal`,
`bare_except`, `logic_mirroring` and `mock_of_target`. A finding here is structural: no model
judgment overrides it and no edit to the spec clears it. Only editing the test does.

**Test strength** is the share of the deliberate breaks made to the code that the tests caught,
as an integer percent, or `n/a` when no engine ran. It says one thing: the tests noticed when
the behaviour changed. It does not say the tests prove the right rule. A rule can reach 90
percent on a proof that observes the wrong thing, and a correct proof of a small rule can sit
at 0 percent because nothing broke. Read it beside the findings, never instead of them.

**The model review** runs when `ai_review_at` allows it: never at `tested`, at high risk under
`recorded`, at medium and high under `approved`. It is built from the review criteria verbatim
plus this rule's evidence, so it judges by the same sentences you do.

The brief ends in one of four verdicts, and you use the same four words:

- **`ready`**: every free check clear, strength at or above `min_strength` or no engine ran,
  and the test proves what the proof text claims.
- **`add a case`**: what the test proves is right as far as it goes and a case is missing,
  usually the rejection behind `happy_path_only`. The proof text stays.
- **`rewrite the proof`**: the proof text is the problem, so no test written against it could
  prove the rule. Every blocking finding on the proof text lands here.
- **`needs a human`**: the checks disagree, the proof is `@manual`, or the evidence is a
  screenshot a model should not settle. Nothing is auto-approved from this verdict.

For a rule tagged `origin: design`, the brief shows the pinned mock from `designs/<feature>/`
beside the screenshot the test captured under `.purlin/runtime/attachments/`. Judge what a
person would see: the text, the order, the states present. See
[design-in-specs.md](design-in-specs.md).

## The four answers

**Approve.** The rule, the proof and the test belong together. The walk writes the approval
file and makes the signed commit. Collect several and commit them together at the end.

**Add a case.** Say in plain language what is missing - "it should also reject an expired
token" - and the walk writes a new proof line into the spec with the next free proof id. The
test is left for the next `purlin:build`. Review writes specs and approvals, never code.

**Hold.** The test does not prove the proof as written - it calls two helpers apart where the
proof names the function that joins them - and a new proof line would not fix that. Name the
missing case and the walk commits a hold with `purlin:approve <feature> RULE-N --hold "<case>"`.
CI cannot see that gap, so the hold is what stops it approving a low-risk rule on the free
checks alone; changing the test ends the hold.

**Skip.** Move on and leave the state alone. A skipped rule is on the list again next time,
which is the intended behaviour: nothing is marked as seen by being seen.

Never narrow a rule or a proof to make a finding disappear. That lowers the claim instead of
strengthening the evidence. On a rule that came from an anchor it is not yours to change at
all: `purlin:anchor propose <name>` drafts that change where the rule lives.

The walk closes by saying what happened and what is left:

```
Reviewed 12 rules: 8 approved, 1 case added, 3 skipped.
Approvals committed: 8 (signed, 1 commit)
Left on the list: 4
```

## Approving outside the walk

```
purlin:approve <feature> RULE-N [RULE-M ...]   one rule, or several
purlin:approve <feature>                       every reviewable rule of one feature
purlin:approve --batch                         everything currently approvable
```

Use `purlin:approve` when you already know what you are approving. It shows the brief for each
rule first, because approving a rule you have not read is the one thing it must not help with.
It writes one file per rule under `specs/<category>/<feature>.approvals/` and makes one signed
commit for all of them, so a batch of forty rules is one commit and forty files that cannot
conflict with anyone else's.

If your email is not in `approvers` in `.purlin/config.json`, the skill stops and says so. Add
it by pull request, or ask someone on the list.

## What makes an approval count

An approval file binds three hashes - the rule text, the proof descriptions, and the test files
behind them - plus the pinned design for an `origin: design` rule, the risk at the time, your
email, the brief you read and the record you rested on. Four conditions decide whether it
counts, and the status shows which one failed:

1. The commit that added the file is signed and the signature verifies.
2. The author's email is on the approver list as of that commit.
3. That author is not the author of the commit that last touched the test.
4. The bound hashes still match the current text.

Under `approved`, the gate also checks that the approval commit is an ancestor of the protected
branch head, so an approval living only on a side branch does not let a change merge.

## What stales an approval

Changing the rule text, any of its proof descriptions, the body of a test behind it, the
pinned design for a design rule, or the rule's risk. Each of those changes what the approval
was given about, so the rule returns to the review list and a person looks again.

Changing the code alone stales nothing. The rule is flagged `re-verify pending` and CI clears
it on the next run.

Read next: [team-workflow.md](team-workflow.md) for where the review list comes from,
[regulated-workflow.md](regulated-workflow.md) for the approver list and signing,
[specs-and-anchors.md](specs-and-anchors.md) for writing a proof that a test can prove.
