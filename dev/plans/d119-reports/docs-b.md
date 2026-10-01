# Lane `docs-b`: the plain-language pass over `docs/audit.md` and `docs/dashboard.md`

Branch `lane/d119-docs-b`. Files written: `docs/audit.md`, `docs/dashboard.md`, this report.

## Tests

`python3 -m pytest dev/test_purlin_docs.py -q`: 4 passed, 0 failed, 0 skipped before; the same
after. No test deleted, rewritten or added: the lane owns no test file. `purlin_docs PROOF-21`
and `PROOF-22` pass.

Broken on purpose once: the Foster et al. line taken out of `Sources` in `docs/audit.md`.
`test_every_link_of_the_audit_page_appears_again_under_sources` failed, 1 failed and 3 passed.
Restored with `git checkout -- docs/audit.md`, 4 passed.

The plan's section 8 greps over the two pages find nothing. Neither page named a remote run, a
runner or a pinned anchor before the pass, so nothing was removed for that and "remote anchor"
is written nowhere: neither page names the kind.

## Word counts (`wc -w`)

| Page | Before | After |
|---|---|---|
| `docs/audit.md` | 1074 | 1050 |
| `docs/dashboard.md` | 1711 | 1745 |

`docs/audit.md`: the list under `Sources` is 16 entries and about half the page; it is kept
whole. The text above it is shorter, and gains three facts (below).

`docs/dashboard.md` is not shorter. Its long sentences became short ones, lists and fenced
examples, and it gains four facts the page draws and the doc left out (below). Left for the
owner: whether the page should also lose detail, which is a call about what a reader needs.

## Three before and after pairs

1. `docs/dashboard.md`, the header line.
   Before: "the checkout state the data describes and when it was written, as `main at a1b2c3d,
   written 06:42 EDT`: the branch, the first 7 characters of the commit the command ran on, and
   the time, 24-hour, in your own timezone, which the line names by your browser's short name
   for it, or by its offset, as `GMT+5:30`, where it has none."
   After: "That is the branch, the first 7 characters of the commit the command ran on, and the
   time. The time is 24-hour and in your own timezone. The line names the zone by your browser's
   short name for it, or by its offset, as `GMT+5:30`, where the browser has none."
2. `docs/dashboard.md`, the light theme.
   Before: "The light theme is ink on paper: a paper tan ground, cards one step lighter, navy
   text, and green, amber, red and teal darkened until every text on the page, in any colour,
   measures at least 7 to 1 against the ground under it."
   After: "The light theme is ink on paper: a paper tan ground, cards one step lighter, and navy
   text. Every text on it, in any colour, measures at least 7 to 1 against the ground under it.
   Green, amber, red and teal are darkened to reach that."
3. `docs/audit.md`, when the AI cannot be reached.
   Before: "Where the AI cannot be reached, the spot tests still report what they find as
   `weak`, a rule that passed them alone stays `not audited`, and the audit says to run
   `purlin:audit` again."
   After: "If the AI cannot be reached, a rule the spot tests flag is still `weak`. Every other
   rule stays `not audited`, and the audit tells you to run `purlin:audit` again."

## Lines a person reads that this lane chose

All in the two pages; none prints from code. The headings changed or added:

- `docs/audit.md`: `## What it does not do` (new, from the closing paragraph of "What you can
  count on"); `## Fast enough to run every day` (was `## Fast enough, safe enough`). No page
  links to either heading.
- `docs/audit.md`, step 2 uses the slide's example, "such as a sample age off by one hour", and
  the Google and Meta sentences use the slide's words, "only in changed code", "a few targeted
  ones", "Purlin follows both".
- `docs/dashboard.md`: no heading changed. The band is shown as the spec's proof words it,
  `▼ BILLING 2 specs 4 of 5 rules pass`.

## Facts added, each checked against the code

`docs/dashboard.md`, against `scripts/report/src/rule.js` and `specs/dashboard/purlin_report.md`:

- A slow proof not yet run: the row reads `not run` with `slow: runs with purlin:test --all`,
  and the proof carries the tag `@slow` (RULE-15, PROOF-238).
- A proof shows its tags `@manual`, `@slow` and `@env(windows)`. The page said only "the
  operating system its `@env` names".
- The rule's screen has the rows `Spec`, the spec's path, and `Last run`, the newest run's
  source and age (RULE-17; `renderRule`).
- The Audit panel ends on `Read by`, the model and the time.

`docs/audit.md`, against `specs/review/ai_audit.md` and `references/review_criteria.md`:

- The audit reads only rules whose tests pass (RULE-1, RULE-35).
- No bug is planted for an anchor's rule; the spot tests alone decide it (RULE-37).

## Statements the code does not hold

- `docs/dashboard.md` said the Audit panel's `Read by` line "shows its time the same way" as the
  header line. The header line shows the time alone; `Read by` shows the date and the time
  (`moment()` in `scripts/report/src/app.js`). The page now says "the model and the time, in
  your timezone like the header line", which is true of both and names no format.

Found and not written into the page, for the reading pass:

- A rule the audit wrote `strong` that still carries findings reads `Strong.` alone, then the
  findings (`auditPanel`). The spec's RULE-39 and the page name only `Strong. It found nothing.`
  and `Weak.`
- The Audit panel also shows the audit file's path, where the data carries one, under `Read by`.
- On the rule's screen the cells' words are drawn as `NOT RUN`, `PASSED`, `FAILED`; the page
  writes them lowercase, as it did before the pass.

## Differences from the plan

None. Nothing left unbuilt. No failure seen in a file this lane does not own.

`purlin_docs PROOF-17`, every relative link under `docs/` naming a file and heading that exist,
has no test in `dev/test_purlin_docs.py` on this branch. The three relative links of
`docs/dashboard.md` and the one of `docs/audit.md` are unchanged; `docs-a` owns the pages they
point at, and `working-together.md#more-than-one-checkout` depends on that heading staying.
