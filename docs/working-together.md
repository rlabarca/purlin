# Working together

For a team where more than one person decides what the software must do: PMs, designers, QA
and engineers.

Purlin holds one artifact everyone shares, the spec, and gives each person a way into it that
matches how much git they want to touch. Every change to it arrives as a pull request, so git
says who wrote each line.

## The PM

**What you need.** Nothing installed and no checkout. Requirements reach a spec two ways.

**With an assistant** that can read the repository and open a pull request, such as Claude
Desktop with the git host connected: describe the feature, and it drafts or edits the spec
and opens the pull request. You read the rendered diff and merge.

**Without one**: write the criteria wherever you already write them, hand them to an engineer,
and their agent runs `purlin:spec`. You review that pull request like any other.

**What you see.** The state of every rule. With a checkout, the dashboard's **rollup** says how
many rules meet the gate out of how many there are, plus one count per bucket; without one,
`.purlin/tests.md` on the git host carries the latest test results. `purlin:drift pm` tells
you which anchor pins are behind their source:

```
drift pm: 1 thing to look at

  design_tokens (anchor)     pinned 4 commits behind its source
```

## The designer

**What you need.** An export and a way to open a pull request, or an assistant that opens one
for you. No checkout and no git.

**What you do.** Hand the exports to `purlin:spec`. It reads the images and drafts rules about
what a person would see.

## QA

**What you need.** One of three, by preference.

- **A checkout with Claude Code.** `purlin:sign` computes the queue, the rules whose next step is
  a person, and walks it one brief at a time. At each stop you sign, add a case in plain
  language, or skip.
- **An assistant with the repository connected.** It reads the specs and the committed test
  results, opens pull requests carrying proof edits, and batches signatures into one commit.
- **No AI at all.** Read `.purlin/tests.md` on the git host and review the diff by hand.

**What you work.** The queue, never the whole rule list. A rule reaches it only when the cell
that blocks it is one a person answers: a strong cell reading `manual test` or `unsettled` (a
`hand check`), or a signed cell reading `unsigned` or `stale` (a `signature`). A rule with no
test, a failing rule, a weak rule and a rule reading `not audited` are all work for the machine
or the build, and they stay on the board. A rule whose passed cell reads `out of date` is not
in the queue: the signature stands, and the next run clears the cell.

When the queue is empty and every rule meets the gate, `purlin:sign` writes the tag
`signed/<version>` and you push it. That tag is the whole claim: this version is proven, as
[hard_gates.md](../references/hard_gates.md) defines it.

Adding a case is plain language. Say "it should also reject an expired token" and the proof
line is written into the spec with the next free proof id; the test arrives on the next
`purlin:build`. The walk and what makes a signature count are in
[review-and-signing.md](review-and-signing.md).

## The engineer

**What you need.** A checkout and the plugin, loaded either from the marketplace or with
`claude --plugin-dir <checkout>`.

**What you run**, in this order, at the start of a session:

```
purlin:drift eng            what moved that the specs have not caught up with
purlin:anchor sync <name>   when a pin is behind
purlin:spec <name>          when a rule is missing or wrong
purlin:build <name>         code and tagged tests
purlin:test                 seconds, tests only, and it commits the results
purlin:audit                tests, breaks, and what it observed
```

Then push, which is free and starts nothing.

**What you see.**

```
drift eng: 14 files since the last record (a1b2c3d)

  src/auth/login.js          RULE-2, RULE-5 behind this change
  src/auth/mfa.js            no spec covers this file
  login RULE-7               no test carries PROOF-7
  design_tokens (anchor)     pinned 4 commits behind
  export                     out of date: the code moved, the signatures stand
```

You may also be the person who signs, at either gate. Signing is logged, not policed: the
signature names you, git names whoever wrote the test, and Purlin decides neither.

## A rule from a pinned anchor

A rule that came from a pinned anchor belongs to the anchor repository, whoever wrote it.
A change to it is a pull request against that repository, and `purlin:anchor sync` brings it
back once it merges.

## Drift, one view per role

`purlin:drift` is the same data filtered three ways, not three computations. It writes nothing.

| Role | What it reports |
|------|-----------------|
| `pm` | Pins behind their source |
| `qa` | Signatures gone stale, how long the queue is, the rules reading `manual test`, `unsettled` and `not audited`, rules whose every proof asserts a success path |
| `eng` | Files touched and the rules behind them, rules with no test, pins behind, rules whose passed cell reads `out of date` |

Run it at four moments: at the start of a session, after an anchor pin moved, before QA walks
the queue, and before a release. Those are the four times the tree has moved ahead of
the specs without anyone being told.

With no role named, `purlin:drift` infers one from the files the session touched and says
which it chose in the first line. `--since <N>` or `--since <YYYY-MM-DD>` reads a window other
than since the last record.

## Next

- Writing the rules themselves: [specs-and-anchors.md](specs-and-anchors.md)
- Bringing an existing codebase in: [spec-from-code.md](spec-from-code.md)
- The gate that decides what every rule must have: [team-workflow.md](team-workflow.md)
