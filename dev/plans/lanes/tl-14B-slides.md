# Lane 14B: the three gate slides under decision 31

The deck is `https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is`, three slides,
`project/slides/passed.html`, `strong.html` and `signed.html`, plus the optional fourth. This
file is the content; the orchestrator republishes. Nothing about the layout changes: the same
row markup, the same 48 / 150 / 560 column widths, the same `LOCAL` copper and `REMOTE` teal
pills, the same pinned footer at `bottom:64px`. It replaces `dev/plans/lanes/tl-12B-slides.md`
where the two differ, and it rewrites the optional fourth slide `tl-10B-slides.md` proposed.

Three things moved under these slides:

- **The loop is local, at every gate.** `purlin:spec`, `purlin:build`, `purlin:test`,
  `purlin:audit`, `purlin:sign`, `git push`, all on one machine. A project at `signed` with no
  CI anywhere is the ordinary case, so **every row of the three gate slides carries the `LOCAL`
  pill** and no row names a pull request, a merge or a runner. A record counts whoever wrote it.
- **The tag is the marker.** When every rule meets the gate, `purlin:sign` writes the annotated
  tag `signed/<version>` and prints `Run: git push origin signed/<version>`. No tag while any
  rule falls short. The `signed` slide ends on the tag and the push.
- **A remote runner exists for two reasons and no other**: a proof tagged `@env` for an
  operating system this machine is not, or trust set to `remote`. That is the whole of the
  fourth slide, and the only place `REMOTE` appears in the deck. "No merge while red" is gone:
  nothing merges on a gate any more.

The footer changes, because the three gate slides no longer show a `REMOTE` row and a footer
must not define a label its slide never draws.

Machine text stays in Courier New. Where a "what happens" cell carries machine text, it is one
inline span inside the Arial cell:
`<span style="font-family:'Courier New', monospace">signed/1.4.0</span>`.

---

## Slide `passed`

Eyebrow `Gate passed`, headline `Did the rules pass their tests?`, both unchanged.
**Four steps, unchanged.**

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `purlin:spec` | Rules and proofs written. |
| 2 | LOCAL | `purlin:build` | Code and tagged tests written. |
| 3 | LOCAL | `purlin:test` | Each rule: passed, failed, no test. Results committed. |
| 4 | LOCAL | `git push` | You push. Nothing else does. Nothing runs when you do. |

Closing line, unchanged:

> **Red** means a test failed or a rule has no test.

Footer, replacing the old one:

> Every step is on your machine. Only you push.

Speaker notes, replacing the old ones:

> At passed the evidence is the test results purlin:test commits, and its last line is the
> check. No record, no signature, no script, and no CI unless a proof names another operating
> system.

---

## Slide `strong`

Eyebrow `Gate strong`, headline `Are the tests worth trusting?`, both unchanged.
**Five steps**, replacing the six of `tl-12B-slides.md`.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `spec, build, test` | The passed loop. Results committed. |
| 2 | LOCAL | `purlin:audit` | The breaks, then the AI audit on every rule whose bar is `strong`. |
| 3 | LOCAL | `the record` | One per feature, with the briefs beside it. Committed, never pushed. |
| 4 | LOCAL | `the strength` | Printed beside the minimum, then `gate strong: n of n`. |
| 5 | LOCAL | `git push` | You push. Your record counts. |

Closing line, replacing the old one:

> **Red** means a rule is weak, not audited, or waiting on a person.

Footer, as above:

> Every step is on your machine. Only you push.

Speaker notes, replacing the old ones:

> Any audit counts, at every gate. A rule whose bar is strong reads not audited until one has
> run on this code; the audit clears it, not a person. Nothing here needs a runner.

---

## Slide `signed`

Eyebrow `Gate signed`, headline `Did a person sign it?`, both unchanged.
**Five steps**, replacing the five of `tl-12B-slides.md`.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `the strong steps` | Tests, audit, records and briefs, on this machine. |
| 2 | LOCAL | `purlin:sign` | `Review: n rules. Sign: n rules.` Walk Review, then Sign. |
| 3 | LOCAL | `the signature` | One file per rule, in one signed commit. No machine writes one. |
| 4 | LOCAL | `the tag` | Every rule meets the gate, so `signed/1.4.0` is written. Never while one falls short. |
| 5 | LOCAL | `git push origin signed/1.4.0` | You push the tag. That is the claim. |

Closing line, replacing the old one:

> **Red** means a rule has not cleared its bar, or it needs a signature and has none, or the
> one it had went stale. No tag is written.

Footer, as above:

> Every step is on your machine. Only you push.

Speaker notes, replacing the old ones:

> Review is what the machine could not finish: a manual test, an audit that could not settle,
> a hold. Sign is what has cleared its bar and is waiting for a name. The signature binds what
> the audit observed as well, so a re-audit that sees something new stales it. The tag holds
> the whole tree: code, records, briefs and signatures under one name.

---

## The fourth slide, no longer optional

It is now the one place in the deck where `REMOTE` appears, and the one place the runner is
explained, so the footer's second label has somewhere to live. Two rows, not three.

Eyebrow `The remote runner`, headline `When does anything leave your machine?`, then two rows
in the same markup with the number column carrying 1 and 2 and **no** `LOCAL` or `REMOTE`
pill, so the row reads as a reason rather than a step:

| # | Reason | What it gets you |
|---|--------|------------------|
| 1 | `another operating system` | A proof in `specs/` is tagged `@env` for a system this machine is not, so only a runner can prove it. |
| 2 | `you said not to trust this one` | You chose not to trust this machine for signing, so the tests a signature rests on run on a clean one. |

Closing line, replacing the old one:

> With neither, `purlin:init` writes no workflow at any gate. Teammates see your results
> anyway, from the test results `purlin:test` commits.

Footer, replacing the old one:

> REMOTE is the git host's runner. It starts on a pushed tag or a run branch, and on nothing
> else.

Speaker notes, replacing the old ones:

> Two reasons and no others. Where a runner exists it runs on a pushed `signed/**` tag and on
> the `run/*` branch `purlin:test --remote` creates. The tag run reruns the tests on a clean
> machine, checks every signature and hold against the tagged code, and checks that every ci/
> record and brief came from the runner itself; a red run there is the host's word that this
> version is not proven. No pull request run, no comment, no artifact, no branch rule.

---

## What changed against `tl-12B-slides.md`, and why

- **Every `REMOTE` row left the three gate slides.** Rows 3, 4, 5 and 6 of `strong` and rows
  3, 4 and 5 of `signed` named a pull request run, a merge and a run on main. None of the
  three happens now: CI starts on a tag and on a run branch, a push is free, and the gate is
  checked where the tag is written. The rows they became are the steps a person actually
  types.
- **The `signed` slide ends on the tag rather than on a green check.** The brief asked for
  `purlin:sign` → tag → push → CI verifies → green. The tag run is a verification of evidence
  that already exists, and it only exists where a project has a runner, so putting it in the
  main sequence would make the ordinary case look like the exception. It is stated on the
  fourth slide instead.
- **The footer changed on all four slides.** The old one, `LOCAL is your machine. REMOTE is CI
  on your git host. Only you push.`, defined `REMOTE` on three slides that no longer draw it.
  The gate slides now say what is true of every row on them, and the fourth slide defines
  `REMOTE` where the word is used.
- **The `strong` slide gained a row and lost two.** Splitting `purlin:audit`, its record and
  its strength across three rows costs one row against the old six and says what the one
  command leaves behind, which is what the gate reads.
