# Decision 128, lane `dashboard4`: the report

Branch `lane/d128-dashboard4`, items 6 and 8 of `dev/plans/d128-plan.md`.

## What was built

**8. The count boxes stand above the warnings at every width.** The board reads, from the top:
the top bar, the count boxes, the notices (the uncommitted-tree line, the warnings, then the
lines of information), the anchors, the specs. `render` no longer draws the notices before the
board; `renderBoard` draws them after the boxes' section, in a `<section class="notices">` whose
last notice drops its own margin so the gap to the next table is the section's. Nothing else
moves: the grouping, the tones and the swap that puts the spec table above the anchors where a
spec fails and no anchor does are as they were.

**6. The same on the dashboard.** An anchor's `Tests` cell ends with `· <n> out of date`, the
count of its rules whose passed cell reads `out of date`, after `by hand`, `partial` and
`failing`, in the warn tone (the tone `out of date` already has everywhere on the page). A
feature's row never carries the part. The page counts it from the rules' passed cells, which
the data already carries: no new key, schema 16 stands.

Files: `scripts/report/src/app.js`, `board.js`, `styles.css`, the rebuilt
`scripts/report/purlin-report.html`, `specs/dashboard/purlin_report.md`,
`dev/test_purlin_report.py`, `docs/dashboard.md`. Two commits, one per item.

## Rules and proofs, word for word

`> Highest-Rule:` 85 before and after. `> Highest-Proof:` 279 before, 282 after.

Reworded: RULE-9, RULE-22, PROOF-198 (its test changed in the same commit). Added: PROOF-280,
PROOF-281, PROOF-282.

- RULE-9: A column exists only where the project reaches it: `Spec`, `Rules` and `Tests` always, `Proofs` wherever the project writes at least one proof line, and `Strong` last wherever a rule has an audit entry. Each count cell names what it counts beside the number: `Proofs` the proof total, then `<k> no test`, a `@manual` proof counting as no gap; `Tests` `<passed> of <rules>`, then `<k> by hand`, `<k> partial` and `<k> failing`, and on an anchor's row last `<k> out of date`, the anchor's rules whose passed cell reads `out of date`, in the warn tone; a feature's `Strong` `<s> of <n>`, `<n>` the spec's rules that pass their tests and have a tested proof
- RULE-22: The board draws the notice that the working tree has uncommitted changes, `The working tree has uncommitted changes, so what is on this board is not what a commit would carry.`, then the warnings the data carries, each a notice of its own, whole, but those RULE-81 draws as one, below the boxes and above the anchors and the spec table, at every width from 390 to 1500 pixels; a rule's screen draws neither
- PROOF-198 (RULE-22): Open the board with the regulated sample, whose data reports an uncommitted working tree and one spec warning; the notices read, in order, the uncommitted-tree sentence and that warning's text whole, and both stand below the last box and above the anchors' section
- PROOF-280 (RULE-9): Open the board with the regulated sample after the one rule of the anchor checkout_design reads `out of date`; its `Tests` cell reads `0 of 1 · 1 out of date`, the last part in the warn tone, and export, a feature one of whose two rules reads `out of date`, reads `1 of 2`
- PROOF-281 (RULE-9): Open the board with the regulated sample after the anchor checkout_design is given 4 rules more beside its passing one, reading `checked at sign-off`, `partial`, `failed` and `out of date`; its `Tests` cell reads `1 of 5 · 1 by hand · 1 partial · 1 failing · 1 out of date`
- PROOF-282 (RULE-22): Open the board at 1500, 1280, 1024, 768 and 390 by 900 pixels, in both themes, with the regulated sample, whose data reports an uncommitted working tree, given the 4 notices a real project showed and 41 more specs, the last of them the only one with a rule that reads `failed`; at every width and in both themes the 5 notices stand below the boxes and above both tables, and the boxes and the `Failing` box end above the bottom of the screen

## Seen failing first

The four tests were run against `main`'s page before any change, and all four failed:
PROOF-280 read `0 of 1` for `0 of 1 · 1 out of date`; PROOF-281 read
`1 of 5 · 1 by hand · 1 partial · 1 failing` with no last part; PROOF-198 and PROOF-282 found the
boxes ending at 370.6 pixels with the first notice starting at 89.

## On the copy of the real project

`cp -Rc` of `RLabGenMusic-upgrade-3` at `4366261` in the scratch folder, data written by this
worktree's `scripts/run/purlin_status.py --project-root <copy>` (11.3 s), the page copied to the
copy byte for byte the built one. The board: `No proof 0`, `Passing 475 / 476 RULES TOTAL`,
`Failing 1`; 4 notices below them; `SPECS` above `ANCHORS`, first row `project_workspace`
`10 of 11 · 1 failing`. The anchors read `honest_answers 4 of 4` and `rlab_design_system 11 of 11`.

A second copy, with one line added to the tracked `packages/web/src/api.ts` and no commit: the
status gives 442 of 476 passing and 5 notices (the uncommitted tree added). The anchors read
`honest_answers 0 of 4 · 4 out of date` and `rlab_design_system 0 of 11 · 11 out of date`, the
part in amber. The terminal on `main` still prints `0 of 11` there; lane `run4` adds its part.

## What the page looked like

Playwright from the `.venv`, 900 high, both themes, which measure the same. Sideways scroll 0
and no value on two lines at every width on both copies. Pixels from the top, first count box,
`Failing` box, notices, first spec row:

| Width | First box | `Failing` box | Notices (copy / touched) | First spec row (copy / touched) |
|---|---|---|---|---|
| 1500 | 89 to 222 | 89 to 222 | 262 to 600 / 262 to 674 | 780 to 835 / 854 to 910 |
| 1280 | 89 to 222 | 89 to 222 | 262 to 600 / 262 to 674 | 780 to 835 / 854 to 910 |
| 1024 | 89 to 222 | 89 to 222 | 262 to 620 / 262 to 694 | 800 to 856 / 875 to 930 |
| 768 | 145 to 278 | 145 to 278 | 318 to 737 / 318 to 832 | 899 to 983 / 994 to 1077 |
| 390 | 195 to 328 | 344 to 456 | 496 to 1178 / 496 to 1292 | 1340 to 1453 / 1454 to 1568 |

The boxes and the `Failing` box are on the first screen at every width; before this change the
boxes started at 467 at 1500 and 1019 at 390. The first spec row is on the first screen at 1500,
1280 and 1024 on the copy, at 1500 and 1280 on the touched copy, and below it at 768 and 390, as
it was before: the notices that stood above the boxes now stand above the row.

## The docs' screenshots

`dashboard-board.png` changes: the regulated sample carries the uncommitted-tree notice and one
warning, and they now stand below the boxes. A render of `main`'s page and this page from the
same sample differ on the board and are byte for byte the same on the rule screen, so
`dashboard-rule.png` does not change for this lane. A fresh run of
`dev/capture_doc_screenshots.py` also gives a rule image that differs from the committed one, a
difference `main`'s page has too; the images were put back and nothing under `docs/images/` is
staged. The coordinator retakes them.

## Lines chosen

- The cell part `<n> out of date`, as the plan's contract gives it, in the warn tone.
- `docs/dashboard.md`: the count boxes part now comes before the notices part; the notices part
  opens `Notices sit below the count boxes and above the anchors, one per line, so the counts
  stay on the first screen however many notices there are.`; the `Tests` row adds
  `An anchor's cell ends with how many of its rules are out of date, as 0 of 11 · 11 out of date`;
  the anchors part reads `between the notices and the spec table`; the board image's text names
  the notices.

## Calls made that the plan did not

1. **The spec table still stands above the anchors where a spec fails and no anchor does**
   (RULE-84, lane `dashboard3`'s call). The plan's order names the anchors before the specs; I
   read it as the order with no failing spec and kept RULE-84, so the failing row stays on the
   first screen at 1500. To drop it, set `specsFirst` to false in `renderBoard` and retire
   RULE-84's third clause with PROOF-269 and PROOF-278.
2. **The out-of-date part counts the rules' passed cells on the page**, not a rollup key the
   terminal may add, so this lane needs nothing from `run4` to draw it. Both count the same
   cells, so the page and the terminal read the same characters once `run4` lands.
3. **Its tone is the warn tone**, the tone `out of date` has on every other part of the page.
4. RULE-63 ("between the boxes and the spec table") is left as it is: it still holds.

## What is left

Nothing in this lane. The terminal's matching part is lane `run4`'s item 6.

## Acceptance

`python3 -m pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_report_refresh.py dev/test_purlin_docs.py`: 121 passed.
`bash dev/run_tests.sh`: 1212 passed, 9 skipped; `Suites: 4 passed, 0 failed`.
