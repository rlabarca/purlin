# Working together

For a team where more than one person decides what the software must do: PMs, designers, QA
and engineers.

Purlin holds one artifact everyone shares, the spec, and gives each person a way into it that
matches how much git they want to touch. Every rule carries an `[origin: ...]` tag naming its
owner, and that tag is what keeps four people editing one file without stepping on each other.

## The PM

**What you need.** Nothing installed and no checkout. Requirements reach a spec two ways.

**With an assistant** that can read the repository and open a pull request, such as Claude
Desktop with the git host connected: describe the feature, and it drafts or edits the spec,
tags the rules `[origin: pm]`, and opens the pull request. You read the rendered diff and
merge. It never silently rewrites a rule owned by an engineer or QA; it leaves a pull request
comment proposing the change instead.

**Without one**: write the criteria wherever you already write them, hand them to an engineer,
and their agent runs `purlin:spec`. You review that pull request like any other.

**What you see.** After CI runs, the pull request carries a comment with the state of every
rule and a link to the `purlin-dashboard` build artifact. Tag each rule with the id of the
criterion it came from, `[criterion: US-12]`, and `purlin:drift pm` tells you which criteria
still have no rule:

```
drift pm: 3 things to look at

  criterion ACC-14           no rule carries it
  login RULE-3 (origin: pm)  text changed on this branch; signature stale
  login RULE-9               added by an engineer, origin: eng, derived from RULE-3
  design_tokens (anchor)     pinned 4 commits behind its source
```

## The designer

**What you need.** An export and a way to open a pull request, or an assistant that opens one
for you. No checkout and no git.

**What you do.** Put the exports in `designs/<feature>/`. `purlin:spec` reads the images and
drafts rules about what a person would see, tagged `[origin: design]`, and a design anchor
pins the files by hash.

**What you see.** `purlin:drift design` names what moved and which of your rules have a stale
signature because a mock was re-exported. The brief pairs your mock with the screenshot the test
captured. The whole flow is in [design-in-specs.md](design-in-specs.md).

## QA

**What you need.** One of three, by preference.

- **A checkout with Claude Code.** `purlin:sign` computes the list of rules whose next step is
  a person, orders it by risk, and walks it one brief at a time. At each stop you sign, add a
  case in plain language, hold or skip.
- **An assistant with the repository connected.** It reads the same rollup, opens pull
  requests carrying proof edits, and batches signatures into one commit.
- **No AI at all.** Open the `purlin-dashboard` artifact from the pull request and review the
  diff by hand.

Anyone with the repository URL can print the same rollup without cloning it whole:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report/scan.py" --repo <url> [--ref <branch|tag>]
```

**What you work.** The review list, never the whole rule list. A rule reaches it only when the
cell that blocks it is one a person answers: a strong cell reading `needs a person`, or a signed
cell reading `unsigned`, `stale` or `held`. A rule with no test, a failing rule and a weak rule
are build work and stay on the board. A rule whose passed cell reads `code changed` is not on
the list either: only the code moved, the signature stands, and CI clears it on the next run.

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
purlin:test                 seconds, tests only
purlin:audit                tests, breaks, and the record
```

Then push. Rules you add are tagged `[origin: eng]`, and the PM sees them as derived rather
than as requirements nobody asked for.

**What you see.**

```
drift eng: 14 files since the last record (a1b2c3d)

  src/auth/login.js          RULE-2, RULE-5 behind this change
  src/auth/mfa.js            no spec covers this file
  login RULE-7               no test carries PROOF-7
  billing RULE-3             no risk tag; the gate needs one
  design_tokens (anchor)     pinned 4 commits behind
  export                     code changed: the code moved, the signatures stand
```

You may also be the person who signs. Under the `strong` gate that is fine. Under `signed` the
signer list decides, and a signature never counts when its author is the author of the commit
that last touched the test.

## The owner rule

A rule tagged `[origin: pm]`, `[origin: design]` or `[origin: qa]` belongs to that person.
Anyone may add a rule beside it, tagged with their own origin, and say in the pull request why
the neighbouring rule looks wrong. Nobody rewrites or deletes someone else's rule. The
proposal goes in a pull request comment naming the rule id and the replacement text, and the
owner takes it or leaves it.

A rule tagged `[origin: eng]`, or carrying no origin at all, is the engineer's to edit.

A rule that came from a pinned anchor belongs to the anchor repository, whoever wrote it.
`purlin:anchor propose <name>` drafts that change where the rule lives.

## Drift, one view per role

`purlin:drift` is the same data filtered four ways, not four computations. It writes nothing.

| Role | What it reports |
|------|-----------------|
| `pm` | Criteria with no rule carrying them, `origin: pm` rules whose text changed, rules an engineer added, pins behind |
| `design` | Design files that changed, and `origin: design` rules whose signature went stale because a mock was re-exported |
| `qa` | Signatures gone stale, how long the review list is, how many rules need a person, rules whose every proof asserts a success path |
| `eng` | Files touched and the rules behind them, rules with no test, risk or origin tags the gate requires and the spec lacks, pins behind, rules whose passed cell reads `code changed` |

Run it at four moments: at the start of a session, after an anchor pin or a design export
moved, before QA opens the review list, and before a release. Those are the four times the
tree has moved ahead of the specs without anyone being told.

With no role named, `purlin:drift` infers one from the files the session touched and says
which it chose in the first line. `--since <N>` or `--since <YYYY-MM-DD>` reads a window other
than since the last record.

## Next

- Writing the rules themselves: [specs-and-anchors.md](specs-and-anchors.md)
- Bringing an existing codebase in: [spec-from-code.md](spec-from-code.md)
- The gate that decides what CI must see: [team-workflow.md](team-workflow.md)
