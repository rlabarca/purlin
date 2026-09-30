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

**What you see.** The dashboard's boxes count the rules that reached each step the gate asks
for, `Passing`, then `Strong` from the gate `strong` up and `Signed` at `signed`, with a
`No proof` box first from `strong` up. `.purlin/tests.md` is the table of the newest run of
each feature, written from every evidence file on disk, committed or not. After a pull,
`purlin:drift pm` tells you which rules it added, changed or removed:

```
Since your last pull, 0 seconds ago (b9f91d5..1af085f, 2 commits).
2 rules added: export RULE-1; login RULE-4.
1 rule changed: login RULE-2.
```

## QA

**What you need.** A checkout and the plugin. You write and review the proofs: a proof says in
plain language how a rule is shown, and `references/spec_quality_guide.md` is the guideline an
AI draft is held to.

**What you work.** `purlin:sign` walks the rules left to do as `to test by hand` or `to sign`,
one rule at a time, showing the rule, its proofs and what the audit found. A rule is
`to test by hand` at every gate while a `@manual` proof of it is not checked, and `to sign` at
the gate `signed` once its tests pass and its audit is strong. Everything else is work for the
build or the audit, and `Left to do` names the command for it. At each stop you answer `sign`,
`case` or `skip`. A signature is a signed commit `purlin:sign` makes.

Adding a case is plain language. Say "it should also reject an expired token" and the proof
line is written into the spec with the next free proof id; the test arrives on the next
`purlin:build`. At the gate `signed`, when nothing is left but the tag, `purlin:sign` writes
the tag `signed/<version>` and you push it. [review-and-signing.md](review-and-signing.md) is
the walk in full.

## The developer

**What you need.** A checkout and the plugin.

**What you run**, in this order, at the start of a session:

```
purlin:drift eng            what changed since your last pull
purlin:anchor sync <name>   when a pin is behind
purlin:spec <name>          when a rule is missing or wrong
purlin:build <name>         the code and its marked tests
purlin:test                 the tests the change touched; --commit commits the work and the evidence
purlin:audit                the tests, then the AI audit; --commit commits the work and what it found
```

Then you push.

**What you see.** After a pull, `purlin:drift eng` names what moved and the command for each:

```
Since your last pull, 0 seconds ago (b9f91d5..1af085f, 2 commits).
1 file changed under export's scope: RULE-1 is behind it. Run purlin:test export.
1 file changed under login's scope: RULE-1, RULE-2, RULE-3, RULE-4 are behind it. Run purlin:test login.
1 changed file is under no spec's scope: src/mfa.py. Add each to a spec's > Scope: line with purlin:spec.
3 rules have no test: export RULE-1; security_baseline RULE-1, RULE-2. Run purlin:build.
anchor security_baseline: the pin 71abd36 is behind its source, now b3a6387. Run purlin:anchor sync security_baseline.
1 feature is out of date: login. Run purlin:test.
```

You may also be the person who signs. Signing is logged, not policed: the signature records
your name and email as git holds them and the fingerprint of your key, and Purlin does not
decide who may sign.

## A rule from a pinned anchor

A rule that came from a pinned anchor belongs to the anchor repository, whoever wrote it. A
change to it is a pull request against that repository, and `purlin:anchor sync` brings it back
once it merges.

## Drift, one view per role

`purlin:drift` reports what changed since the last git action that brought changes into your
checkout: the newest pull, merge, rebase, checkout or reset in git's log of HEAD. After a clone
with nothing later, it reads the last 20 commits, or every commit when there are fewer. It
writes nothing and judges nothing.

| Role | What it reports |
|------|-----------------|
| `pm` | Rules added, rules changed, rules removed |
| `eng` | Code changed and the rules behind it, changed files under no spec's scope, rules with no test, anchors behind their source, features out of date |
| `qa` | Test files changed and the features they cover, then the `to test by hand` and `to sign` lines of `Left to do` |

The `qa` view prints those lines at every gate; at `passed` only a rule to test by hand waits
for a person:

```
Since your last pull, 1 second ago (b9f91d5..1af085f, 2 commits).
1 test file changed, covering login.
1 rule to test by hand: purlin:sign
```

Every view ends with `<n> spec files have changes that are not committed.` when a spec file
differs from the last commit or is not tracked. Run it right after you pull, merge, rebase or
check out someone else's branch. With no role named, `purlin:drift` infers one from the files
the session touched and says which it chose. `--since <N>` reads the last N commits and
`--since <YYYY-MM-DD>` every commit since that date.

## Next

- Writing the rules themselves: [specs-and-anchors.md](specs-and-anchors.md)
- Bringing an existing codebase in: [spec-from-code.md](spec-from-code.md)
- The gate that decides what every rule must have: [team-workflow.md](team-workflow.md)
