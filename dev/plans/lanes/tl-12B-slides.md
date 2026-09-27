# Lane 12B: the three gate slides under decision 30

The deck is `https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is`, three slides,
`project/slides/passed.html`, `strong.html` and `signed.html`. This file is the content; the
orchestrator republishes. Nothing about the layout changes: the same row markup, the same
48 / 150 / 560 column widths, the same `LOCAL` copper and `REMOTE` teal pills, the same pinned
footer at `bottom:64px`. It replaces `dev/plans/lanes/tl-11D-slides.md` where the two differ,
and the optional fourth slide at the end of `tl-10B-slides.md` stands unchanged.

Two things moved under these slides:

- **Every rule has a bar**, `passed` or `strong`: the evidence that rule must have before it
  can be signed. A rule says its own with a tag, `[bar: passed]` or `[bar: strong]`; a rule
  with no tag takes the project's gate as its bar. The AI audit runs on every rule whose bar
  is `strong` and on no other. Risk is retired.
- **The review list is two lists.** `Review` holds the rules whose strong cell reads
  `manual test`, `unsettled` or `held`; `Sign` holds the rules that have cleared their bar and
  are waiting for a signature. `purlin:sign` walks Review, then Sign.

The word `not audited` is new and it belongs on the `strong` slide: a rule whose bar is
`strong` reads `not audited` until an audit has run on this code. It waits for `purlin:audit`,
not for a person.

Machine text stays in Courier New. Where a "what happens" cell carries machine text, it is one
inline span inside the Arial cell:
`<span style="font-family:'Courier New', monospace">not audited</span>`.

---

## Slide `passed`

Eyebrow `Gate passed`, headline `Did the rules pass their tests?`, both unchanged.
**Four steps, unchanged.** Every rule's bar is `passed` at this gate, and clearing it is
passing the tests, which the slide already says.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `purlin:spec` | Rules and proofs written. |
| 2 | LOCAL | `purlin:build` | Code and tagged tests written. |
| 3 | LOCAL | `purlin:test` | Each rule: passed, failed, no test. Results committed. |
| 4 | LOCAL | `git push` | You push. Nothing else does. |

Closing line, footer and speaker notes unchanged:

> **Red** means a test failed or a rule has no test.

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

> At passed the evidence is the test results purlin:test commits, and its last line is the
> check. No record, no signature, no script.

---

## Slide `strong`

Eyebrow `Gate strong`, headline `Are the tests worth trusting?`, both unchanged.
**Six steps.** Row 1 changes; rows 2 to 6 stand as `tl-11D-slides.md` leaves them.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `spec, build, test, audit` | The passed loop, then the audit. It clears `not audited`; its record counts here. |
| 2 | LOCAL | `git push, pull request` | You push. You open it. |
| 3 | REMOTE | `pull request run` | Tests, breaks, review. Comment. No commit. |
| 4 | LOCAL | `merge` | Once the check is green. |
| 5 | REMOTE | `run on main` | Records and briefs committed. What signed will need. |
| 6 | REMOTE | `purlin:test --remote` | Optional: another operating system, or a ci record. |

Closing line, replacing the old one:

> **Red** means a rule is weak, not audited, or waiting on a person.

Footer unchanged:

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

Speaker notes, replacing the old ones:

> At strong any audit counts, your own or CI's. A rule whose bar is strong reads not audited
> until one has run on this code; the audit is what clears it, not a person.

---

## Slide `signed`

Eyebrow `Gate signed`, headline `Did a person sign it?`, both unchanged.
**Five steps.** Row 2 changes; rows 1, 3, 4 and 5 stand as `tl-11D-slides.md` leaves them.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | REMOTE | `the strong steps, on CI` | Only CI's tests and audit count here. |
| 2 | LOCAL | `purlin:sign` | Walk Review, then Sign. Signed commits. |
| 3 | LOCAL | `git push, pull request` | The signer pushes and opens it. |
| 4 | LOCAL | `merge` | The signatures reach main. |
| 5 | REMOTE | `run on main` | Gate check reads signed. Green. |

Closing line, replacing the old one:

> **Red** means a rule has not cleared its bar, or it needs a signature and has none, or the
> one it had went stale.

Footer unchanged:

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

Speaker notes, replacing the old ones:

> Review is what the machine could not finish: a manual test, an audit that could not settle,
> a hold. Sign is what has cleared its bar and is waiting for a name. Only CI's tests and
> audit count here, and CI never writes a signature.

---

## What row 2 of the `signed` slide costs

Row 2 read `Walk the review list`. There is no one review list any more: `purlin:sign` walks
Review, then Sign, and the order is load-bearing, because a rule a person has not judged is
not a rule to sign. The row keeps its place, its `LOCAL` pill and its command, and says the
two names in the order the walk takes them.

## Where `not audited` sits on the `strong` slide

The brief asked for `not audited` on the `strong` slide's step 6. Step 6 is the optional
remote run, and what clears `not audited` is the audit in step 1, so the sentence sits on row
1 instead and the closing line carries the word for the slide as a whole. Row 6 is unchanged.
