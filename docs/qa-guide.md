# From criteria to a sign-off

For a QA person who turns acceptance criteria into proofs and signs the release they cover.

The path has five steps: your criteria become proofs, the developer adds the tests, after each
pull you read what changed, the release run commits the evidence package, and at the gate
`signed` you walk the package and sign it. Every step runs in Claude Code on a checkout of the
repository. Nothing is signed while the specs change; the sign-off is the final check, once
everybody is done.

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
tests. A `@manual` proof has no test: at the gate `signed` you check it by hand in the sign-off
walk and type what you saw.

## Drift after a pull

```
purlin:drift qa
```

Run it right after you pull, merge or check out someone else's branch. It names the proofs
added, changed and moved, with the old and new text of each changed proof, the test files that
changed and the features they cover, and what is left to do. It names a number written twice and
which line moves, and a test comment whose proof's wording changed since the comment was written;
`purlin:spec` renumbers either when you say yes. Drift reads only your checkout and never
fetches; where it names a number written twice it says how old your copy of the default branch
is.

## The release

```
purlin:test --release
```

On the release branch, once `Left to do` is empty, the release run runs every test, commits the
evidence and the evidence package, `.purlin/evidence/package/<version>.json`. At the gate `signed`
it ends on `Run purlin:sign to sign it; the first signature writes signed/<version>.`
[review-and-signing.md](review-and-signing.md) lists what it checks first.

## The sign-off

```
purlin:sign
```

The walk opens on an overview of the package: the rules, the systems they ran on, what the audit
found, and the stops. It stops only where you have something to look at: each hand check, each
weak rule and each rule never audited. A stop shows the rule, each proof with the test tied to it
and the test's body, the results on each system and what the audit found:

```
Proof
  PROOF-3: After 5 wrong passwords in a row, the right password is refused with `423`
    tied to tests/test_login.py::test_locked_after_five
      def test_locked_after_five():
          assert sign_in_after_wrong(5).status == 423
```

At a hand check you type, in one line, what you saw. At any other stop you answer `continue`,
`note` or `stop`; `stop` signs nothing, so you can fix what you found and run the release again.
The rules the audit found strong are a list you can open, or walk in full. After the last stop
the walk asks once whether to sign; `y` makes one signed commit with your key, and the first
sign-off of a version writes the tag `signed/<version>`. Others may sign the same package after
you; the tag does not move. [review-and-signing.md](review-and-signing.md) is the walk in full.

## What the package records

The evidence package describes every rule of the version at the release commit: its words, its
proofs, its tests, each result on each system with its machine, what the audit found, and the
rules checked by hand. Your sign-off sits beside it, in its own file, and records what the walk
showed you, which rules one by one and which only in the list, and every note you typed. It
records no judgment. [package_format.md](../references/formats/package_format.md) and
[signature_format.md](../references/formats/signature_format.md) hold every field.

## Where the risk is

No rule carries a level of its own: every rule is asked the same things, and the weight of a
risk goes into its proofs. The quality guide's paragraph
[Where the risk is](../references/spec_quality_guide.md#where-the-risk-is) says which proofs a
risk asks for.

Read next: [review-and-signing.md](review-and-signing.md) for the release run and the walk,
[working-together.md](working-together.md) for what each role runs.
