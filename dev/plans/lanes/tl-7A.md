# Lane 7A: the board is readable

Plan: `dev/plans/three-levels.md` (Part A and decision 23). Rules: `dev/plans/lanes/tl-_rules.md`
(in full). Read all of `design/readme.md`. Worktree `/Users/richlabarca/LocalCode/purlin-wt/7A`,
branch `lane/7A` off `three-levels`.

The user looked at the board with this repository's own data, in dark mode, and could not read
it. The orchestrator reproduced every point in Chrome at 1440 by 900. Fix all four; the words in
the cells are lane 7B's (it renames `needs a person`), so touch no cell word, `CELL_TONES`,
filter label or `why` token, and do not edit `scripts/report/src/filters.js` or `review.js`
beyond what item 1 needs.

## What is wrong, and what to do

1. **The smallest text cannot be read in dark mode.** The dashboard renders on the product
   surface (`data-surface="product"`), where `design/tokens/theme-dark.css` sets
   `--text-muted` to `--slate-500` (#64738B) on `--slate-900`; the board uses it at `--ui-xs`
   (11px) for the column headers (`.th`) and at `--ui-sm` (13px) for every zero in the count
   cells (`.trio i`), the `mac` box (`.os.none`), the carets and the group counts. Fix in two
   places: (a) in `theme-dark.css`'s product block raise `--text-muted` one step to
   `--slate-400` and `--text-secondary` to `--slate-300` (add `--slate-300` to `palette.css`
   if it is missing, between 400 and 200, and mirror the step in `theme-light.css`'s product
   block so light mode keeps its contrast order); (b) in `styles.css` no text on the board is
   smaller than `--ui-sm`: `.th`, `.tile-l`, `.flag-l` and `.pill` move from `--ui-xs` to
   `--ui-sm`, and the count cells and `Last run` text move to `--ui-base`. Both themes ship;
   tokens only; no colour literal outside `palette.css`.
2. **`Tests` and `Spec status` are unlabelled triples.** Replace `counts()`'s `n · n · n` with
   one labelled count per part and only the parts that are not zero, the first part always:
   `24 passed`, then `· 2 failing` in the fail tone, then `· 1 no test` in the warn tone;
   `24 ready`, then `· 2 drafted` in the idle tone. When every rule is drafted the first part
   is `0 ready`. The number and its word are one mono span in the part's tone; the separator
   is secondary. The same renderer serves the `Signed` cell (`5 of 24`, then `· 1 stale`).
3. **`STRENGTH` runs into `STRONG`, and the `Strong` bar overflows into `Signed`.** The header
   and the rows share `--cols`, so the grid is one; the label is wider than a 0.6fr column.
   Give every column a floor with `minmax()` (`Rules` 56px, `Spec status` and `Tests` 150px,
   `Last run` 260px, `Strength` 92px, `Strong` and `Signed` 130px), let `.tbl` scroll
   horizontally under its sum instead of squeezing, make the `ratio()` bar flexible
   (`flex:1; min-width:32px; max-width:80px`) so it never leaves its cell, and right-align
   `Rules` and `Strength` in the header and the cell alike. Header labels stay uppercase but
   at `--ui-sm` with `--tracking-label`.
4. **Headers and columns must read as aligned.** After 3, take a screenshot at 1440 and at
   1100 wide in both themes and check by eye that each header sits over its column's content
   and nothing touches its neighbour. Put what you saw in your report.

Then `python3 dev/build_report.py`; the 1200-line limit (`purlin_report` RULE-2) holds.
Regenerate the five `docs/images/dashboard-*.png` with `dev/capture_doc_screenshots.py` and
look at each.

## Tests and spec

`dev/test_purlin_report.py` and `dev/test_purlin_report_board_layout.py`: the assertions that
read the count cells, the header labels and the column widths follow; add one test that no
element on the board computes to a font size under 13px in dark mode, one that the `Strength`
and `Strong` header boxes do not overlap at 1100px, and one that a zero part is not rendered.
`specs/dashboard/purlin_report.md`: the rules for the columns (RULE-8, RULE-9 and the ones
that name the triples) say the labelled form; add a rule for the minimum text size and one
for the column floors. Keep every marker aligned.

## Acceptance

```
python3 dev/build_report.py
pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_vocabulary.py
wc -l scripts/report/purlin-report.html
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima and what the two screenshots
showed.
