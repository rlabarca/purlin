# Working together

For a team where more than one person decides what the software must do: product, developers
and QA. It holds at every gate.

Purlin holds one thing everyone shares, the spec. Product, developers and QA all work in Claude
Code on a checkout of the repository, and `purlin:drift` is how each catches up after a pull.
Every change to a spec is a commit, so git says who wrote each line.

## Product

**What you need.** A checkout and the plugin. Describe a feature in plain language, a sentence,
a ticket or a list of acceptance criteria, and `purlin:spec` turns it into rules, shows them
with their proofs, and asks whether to change any before it saves the spec. It never starts
building.

**What you see.** The dashboard's **rollup** says how many rules meet the gate out of how many
there are, plus one count per bucket, and `.purlin/tests.md` is the table of the latest committed
evidence. After a pull, `purlin:drift pm` tells you
which rules it added, changed or removed:

```
Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).
3 rules added: login RULE-7, RULE-8; export RULE-2.
1 rule removed: cart RULE-4.
```

## QA

**What you need.** A checkout and the plugin. You write and review the proofs: a proof says in
plain language how a rule is shown, and `references/spec_quality_guide.md` is the guideline an
AI draft is held to. `purlin:sign` walks the queue, the rules whose next step is a person, one
rule at a time, showing what the audit found. At each stop you answer `sign`, `case` or `skip`.
A signature is a signed commit `purlin:sign` makes.

**What you work.** The queue, never the whole rule list. It exists at `strong` and above. A rule
reaches it only when the cell that blocks it is one a person answers: a strong cell reading
`manual test` (a `hand check`), or, at `signed`, a signed cell reading `unsigned` or `stale` (a
`signature`). Everything else is work for the build or the audit and stays on the board.

Adding a case is plain language. Say "it should also reject an expired token" and the proof line
is written into the spec with the next free proof id; the test arrives on the next
`purlin:build`. When the queue is empty and every rule meets the gate, `purlin:sign` writes the
tag `signed/<version>` and you push it. [review-and-signing.md](review-and-signing.md) is the
walk in full.

## The developer

**What you need.** A checkout and the plugin, loaded from the marketplace or with
`claude --plugin-dir <checkout>`.

**What you run**, in this order, at the start of a session:

```
purlin:drift eng            what changed since your last pull
purlin:anchor sync <name>   when a pin is behind
purlin:spec <name>          when a rule is missing or wrong
purlin:build <name>         the code and its marked tests
purlin:test                 the tests the change touched; --commit commits the evidence
purlin:audit                the tests, then the AI audit; --commit commits what it found
```

Then you push.

**What you see.**

```
Since your last pull, 14 hours ago (a1b2c3d..4f5e6a7, 9 commits).
2 files changed under login's scope: RULE-2, RULE-5 are behind them.
1 changed file is under no spec's scope: src/auth/mfa.js.
1 rule has no test: login RULE-7.
anchor security_baseline is behind its source (now 3c4d5e6). Run: purlin:anchor sync security_baseline.
1 feature is out of date: export.
```

You may also be the person who signs. Signing is logged, not policed: the signature names you,
git names whoever wrote the test, and Purlin decides neither.

## A rule from a pinned anchor

A rule that came from a pinned anchor belongs to the anchor repository, whoever wrote it. A
change to it is a pull request against that repository, and `purlin:anchor sync` brings it back
once it merges.

## Drift, one view per role

`purlin:drift` reports what changed since the last git action that brought changes into your
checkout: the newest pull, merge, rebase, checkout, clone or reset in git's log of HEAD. It
writes nothing and judges nothing.

| Role | What it reports |
|------|-----------------|
| `pm` | Rules added, rules changed, rules removed |
| `eng` | Code changed and the rules behind it, changed files under no spec's scope, rules with no test, anchors behind their source, features out of date |
| `qa` | Test files changed and the features they cover; at `strong` and above, signatures gone stale and why, and the size of the queue |

Run it right after you pull, merge, rebase or check out someone else's branch. With no role
named, `purlin:drift` infers one from the files the session touched and says which it chose.
`--since <N>` reads the last N commits and `--since <YYYY-MM-DD>` every commit since that date.

## Next

- Writing the rules themselves: [specs-and-anchors.md](specs-and-anchors.md)
- Bringing an existing codebase in: [spec-from-code.md](spec-from-code.md)
- The gate that decides what every rule must have: [team-workflow.md](team-workflow.md)
