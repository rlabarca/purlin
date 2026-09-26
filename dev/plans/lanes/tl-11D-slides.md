# Lane 11D: the three gate slides under decision 29

The deck is `https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is`, three slides,
`project/slides/passed.html`, `strong.html` and `signed.html`. This file is the content; the
orchestrator republishes. Nothing about the layout changes: the same row markup, the same
48 / 150 / 560 column widths, the same `LOCAL` copper and `REMOTE` teal pills, the same pinned
footer at `bottom:64px`. It replaces `dev/plans/lanes/tl-10B-slides.md` where the two differ,
and the optional fourth slide at the end of that file stands unchanged.

One thing moved under these slides, and it is why the `strong` and `signed` lists change:

- `purlin:audit` writes the record again. It writes one record per feature it audited and the
  briefs beside them, into `.purlin/records/local/` and `.purlin/briefs/local/`, and commits
  both itself as `purlin: record for <sha7>`. It never pushes. **At `strong` that record
  counts**, so a rule reads `strong` without waiting for a runner. **At `signed` only CI's
  tests and CI's audit count**, from `.purlin/records/ci/`, and the same local run is a
  preview there.

The `passed` list is unchanged. It is written out below so the three lists read as one set.

Machine text stays in Courier New. Where a "what happens" cell carries machine text, it is one
inline span inside the Arial cell:
`<span style="font-family:'Courier New', monospace">gate strong: n of n</span>`.

---

## Slide `passed`

Eyebrow `Gate passed`, headline `Did the rules pass their tests?`, both unchanged.
**Four steps, unchanged.**

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
**Six steps.** Rows 1, 5 and 6 change; rows 2 to 4 stand.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | LOCAL | `spec, build, test, audit` | The passed loop, then the audit. Its record counts here. |
| 2 | LOCAL | `git push, pull request` | You push. You open it. |
| 3 | REMOTE | `pull request run` | Tests, breaks, review. Comment. No commit. |
| 4 | LOCAL | `merge` | Once the check is green. |
| 5 | REMOTE | `run on main` | Records and briefs committed. What signed will need. |
| 6 | REMOTE | `purlin:test --remote` | Optional: another operating system, or a ci record. |

Closing line and footer unchanged:

> **Red** means a rule is weak, or waits on a person.

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

Speaker notes, replacing the old ones:

> At strong any audit counts, your own or CI's. The audit commits its record; it never pushes.

---

## Slide `signed`

Eyebrow `Gate signed`, headline `Did a person sign it?`, both unchanged.
**Five steps.** Row 1 changes; rows 2 to 5 stand.

| # | Label | Command | What happens |
|---|-------|---------|--------------|
| 1 | REMOTE | `the strong steps, on CI` | Only CI's tests and audit count here. |
| 2 | LOCAL | `purlin:sign` | Walk the review list. Signed commits. |
| 3 | LOCAL | `git push, pull request` | The signer pushes and opens it. |
| 4 | LOCAL | `merge` | The signatures reach main. |
| 5 | REMOTE | `run on main` | Gate check reads signed. Green. |

Closing line and footer unchanged:

> **Red** means a rule needs a signature and has none, or it went stale.

> LOCAL is your machine. REMOTE is CI on your git host. Only you push.

Speaker notes, replacing the old ones:

> At signed only CI's tests and audit count. A local run is a preview. CI never writes a
> signature.

---

## What row 1 of the `signed` slide costs

Row 1 carried the `LOCAL` pill and read `the strong steps`. Under decision 29 that is the one
line on the three slides that would now be wrong: the strong steps on a person's machine write
a record this gate does not read. The row keeps its place in the list and changes its pill to
`REMOTE`, so the slide says where the evidence comes from before it says who signs it.
