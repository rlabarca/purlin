# Lane 10B: the three gate slides, as the code now behaves

The deck is `https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is`, three slides,
`project/slides/passed.html`, `strong.html` and `signed.html`. This file is the content;
the orchestrator republishes. Nothing about the layout changes: the same row markup, the
same 48 / 150 / 560 column widths, the same `LOCAL` copper and `REMOTE` teal pills, the
same pinned footer at `bottom:64px`.

Three things moved under these slides, and they are why the passed and strong lists change:

- `purlin:audit --commit` is gone, and so is the record a person writes. `purlin:test`
  writes `.purlin/tests/<feature>.json` and `.purlin/tests.md` and commits both itself as
  `purlin: tests at <sha7>`. That is the evidence at `passed`.
- Nobody runs a script at `passed`. `purlin:test`'s last line, `gate passed: <n> of <rules>`,
  is the check; `gate_check.py --check` is CI's step and belongs on no slide.
- A remote run is `purlin:test --remote`, not `purlin:audit --remote`.

Machine text stays in Courier New. Where a "what happens" cell carries machine text, it is
one inline span inside the Arial cell:
`<span style="font-family:'Courier New', monospace">gate passed: n of n</span>`.

---

## Slide `passed`

Eyebrow `Gate passed`, headline `Did the rules pass their tests?`, both unchanged.
**Four steps, down from six.** Two rows come out: `purlin:audit --commit` and
`gate_check.py --check`.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `purlin:spec` | Rules and proofs written. |
| 2 | LOCAL | `purlin:build` | Code and tagged tests written. |
| 3 | LOCAL | `purlin:test` | Each rule: passed, failed, no test. Results committed. |
| 4 | LOCAL | `git push` | You push. Nothing else does. |

Closing line, replacing the old one:

> **Red** means a test failed or a rule has no test.

Footer, unchanged:

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

Speaker notes, replacing the old ones:

> At passed the evidence is the test results purlin:test commits, and its last line is the
> check. No record, no signature, no script.

---

## Slide `strong`

Eyebrow `Gate strong`, headline `Are the tests worth trusting?`, both unchanged.
**Six steps, as now.** Rows 1 and 6 change; rows 2 to 5 stand.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `spec, build, test, audit` | The passed loop. Audit previews; it writes nothing. |
| 2 | LOCAL | `git push, pull request` | You push. You open it. |
| 3 | REMOTE | `pull request run` | Tests, breaks, review. Comment. No commit. |
| 4 | LOCAL | `merge` | Once the check is green. |
| 5 | REMOTE | `run on main` | Records and briefs committed. This counts. |
| 6 | REMOTE | `purlin:test --remote` | Optional: a counting record before merge. |

Closing line, footer and speaker notes unchanged:

> **Red** means a rule is weak, or waits on a person.

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

> At strong only a record CI wrote counts.

---

## Slide `signed`

Eyebrow `Gate signed`, headline `Did a person sign it?`, both unchanged.
**Five steps, unchanged.** Nothing on this slide named a retired command; it is written out
here so the three lists read as one set.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `the strong steps` | Records and briefs on main. |
| 2 | LOCAL | `purlin:sign` | Walk the review list. Signed commits. |
| 3 | LOCAL | `git push, pull request` | The signer pushes and opens it. |
| 4 | LOCAL | `merge` | The signatures reach main. |
| 5 | REMOTE | `run on main` | Gate check reads signed. Green. |

Closing line, footer and speaker notes unchanged:

> **Red** means a rule needs a signature and has none, or it went stale.

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

> At signed a person adds a signature; CI never writes one.

---

## One optional fourth slide, the orchestrator's call

The `passed` list now has no REMOTE row, so the footer defines a label that slide never
shows, and the three reasons a remote runner is worth having are nowhere in the deck. A
fourth slide answers both. Take it or leave it; the three lists above stand either way.

Eyebrow `The remote runner`, headline `Why let the git host run them?`, then three rows in
the same markup with the number column carrying 1, 2, 3 and **no** LOCAL or REMOTE pill,
so the row reads as a reason rather than a step:

| # | Reason | What it gets you |
|---|--------|------------------|
| 1 | `another operating system` | Your machine cannot run a test tagged for Windows or Linux. |
| 2 | `a clean machine` | Exactly the code you pushed, on a machine nobody touched. |
| 3 | `no merge while red` | The git host refuses the merge while a test fails. |

Closing line:

> Teammates see your results without one, from the test results `purlin:test` commits.

Footer, unchanged. Speaker notes:

> Three reasons and no others. At passed init asks; at strong and above it always writes
> the workflow.
