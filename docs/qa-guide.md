# From criteria to a signature

For a QA person who turns acceptance criteria into proofs and signs the rules they cover.

The path has five steps: your criteria become proofs, the developer adds the tests, you walk the
rules waiting for a person, you sign them, and after each pull you read what changed. Every step
runs in Claude Code on a checkout of the repository.

## Your criteria become proofs

```
purlin:spec login
```

Paste the acceptance criteria as you have them. `purlin:spec` turns them into rules, one line
each saying what the software has to do, and proofs, one line each saying how a rule is shown:
what is done, what is observed and the value that settles it. It prints each rule with its
proofs under it and asks whether to change any before it saves. A proof holds one case, in at
most 60 words; a refusal or a boundary is a proof of its own.
[spec_quality_guide.md](../references/spec_quality_guide.md) is the guideline every draft is held
to, and the one you read it against.

A criterion "a locked account cannot sign in" becomes:

```
- RULE-3: Lock the account for 15 minutes after 5 consecutive failures
- PROOF-3 (RULE-3): After 5 wrong passwords in a row, the right password is refused with `423`
- PROOF-4 (RULE-3): 15 minutes after the fifth wrong password, the right password is answered with `200`
```

A proof that only a person can judge, such as wording against a brand voice guide, carries
`@manual`. `purlin:spec` commits the spec and ends on
`Spec saved: login. Next: purlin:build login`.

## What the developer adds

`purlin:build login` writes the code and one test per proof, with a comment on the line above
each test naming the proof it carries out, `# purlin: login PROOF-3`. `purlin:test` runs those
tests. A `@manual` proof has no test: its rule waits for you as `to test by hand`.

## The walk

```
purlin:sign
```

The walk stops at each rule waiting for a person, `to test by hand` or `to sign`. It shows the
rule, each proof, the test tied to each proof that is not `@manual`, and what the audit found:

```
Proof
  PROOF-3: After 5 wrong passwords in a row, the right password is refused with `423`
    tied to tests/test_login.py::test_locked_after_five
  PROOF-4: 15 minutes after the fifth wrong password, the right password is answered with `200`
    tied to no test
```

`tied to no test` means no test carries that proof out yet. At each stop you answer `sign`, `case` or `skip`. A case
is a missing situation in plain language: it is written into the spec as a new proof line with
the next free number, and the next `purlin:build` writes its test. A skipped rule waits again
next time. [review-and-signing.md](review-and-signing.md) is the walk in full.

## The signature

A signature is one file per rule, written in a signed commit that `purlin:sign` makes with your
key. It counts when that commit's signature verifies. It is made over the rule, its proofs,
its test files, the files the spec's `> Scope:` names, what the audit found and the machine each
system's results came from.

A hand check's signature is made over the rule's and its proofs' wording alone: a change to the
code, a test or the machines does not end it, and a change to that wording does. Every other
signature covers the rule's test files whole and the machine each system's results came from,
so editing another test in the same file, or running the same tests on another computer, ends
it.

## What ends a signature

When a signature ends, the rule is left to do as `to sign`, or `to test by hand` for a hand
check, and the status and every test run print one line naming the rule, the signer and the
cause:

```
login RULE-3: the signature by quinn.qa@labconnect.example ended because a test file behind it changed: tests/test_login.py.
```

Read the cause, look at what changed, and sign again when the rule still holds.

## Drift after a pull

```
purlin:drift qa
```

Run it right after you pull, merge or check out someone else's branch. It names the proofs
added, changed and moved, with the old and new text of each changed proof, the test files that
changed and the features they cover, each signature that ended and why, and what waits for you.
It names a number written twice and which line moves, and a test comment whose proof's wording
changed since the comment was written. Drift reads only your checkout and never fetches; where
it names a number written twice it says how old your copy of the default branch is.

## Where the risk is

No rule carries a level of its own: every rule at the gate is asked the same things, and the
weight of a risk goes into its proofs. The quality guide's paragraph
[Where the risk is](../references/spec_quality_guide.md#where-the-risk-is) says which proofs a
risk asks for.

Read next: [review-and-signing.md](review-and-signing.md) for the walk and the tag,
[working-together.md](working-together.md) for what each role runs.
