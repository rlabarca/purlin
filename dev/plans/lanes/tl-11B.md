# Lane 11B: the board's six columns, the Partial tile, the hovers; the pages and slides follow

Plan: `dev/plans/three-levels.md` (Part A, decisions 23 to 29). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md`. Worktree
`/Users/richlabarca/LocalCode/purlin-wt/11B`, branch `lane/11B` off `lane/11A` **after lane
11A has landed**. **Do not push. Do not open a pull request.**

The user's words: the `Spec status` column is redundant; `developer · 9 days old` under three
boxes is too much; every when, who and platform detail goes into hovers; the columns
disappear from the right as the gate goes down. The fixtures lane 11A wrote (schema 6) are
your contract.

## The board (`scripts/report/src/`)

- `app.js`: `SCHEMA = 6`; `BUCKETS` gains `partial` between `failing` and `passed`, tone
  warn; `CELL_TONES` gains `partial` warn.
- `board.js` columns: `Spec | Rules | Proofs | Tests | Strong | Signed`. `Proofs` reads
  `<n>` and `· <k> without a test` in the warn tone when not zero, hover listing those proof
  ids. `Tests` reads `<passed> of <rules>`, then `· <k> partial` (warn) and `· <k> failing`
  (fail) when not zero; its hover lists each platform the spec's runs covered: `linux · ci ·
  9 days ago · 22 passed · 1 failed · 1 not run`, one line per platform, newest run first.
  `Strong` (at `strong` and above): `<n> of <rules> · <strength>%`, hover: the audit's
  source and age, the minimum. `Signed` (at `signed`): `<n> of <rules>`, hover: each signer
  with the date of their newest signature, and the stale count. `Spec status`, `Strength`
  and `Last run` columns are gone; the OS boxes are gone from the board (the rule screen
  keeps them, coloured by result, with the same hover text).
- Tiles: `Untested`, `Failing`, `Partial`, `Passing`, then `Strong`, then `Signed` and the
  `Stale` flag card; each tile's hover carries the project's platform lines (Passing), the
  audit source and age (Strong), the signers (Signed). Filters gain `Partial`. The headline
  gains `· <k> partial` after failing.
- Column floors: keep the board inside 1100px; recompute the sum and say it in the report.
- `rule.js`: the passed cell row lists the platforms as boxes with the hover; the signed row
  shows signer and date. `review.js` unchanged unless a word moved.
- Hovers are `title` attributes with `·` separators and one line per item (`&#10;`), so
  they work in the PDF-free, script-free page; no custom popover.

## Tests and spec

`dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`: the six columns, the
`Proofs` suffix, the `Tests` suffixes, the hover texts, the Partial tile and filter, no
`Last run` column, the 1100px fit. `specs/dashboard/purlin_report.md`: the column rules,
the tile rule, the hover rule. Rebuild (`dev/build_report.py`, 1200-line limit), recapture
the five screenshots and look at them.

## Pages and slides

- `docs/dashboard.md` rewritten to the six columns, the six tiles and the hovers.
- `docs/how-purlin-works.md`, `docs/team-workflow.md`, `docs/regulated-workflow.md`,
  `docs/running-and-records.md`, `docs/raising-the-gate-and-upgrading.md`, `README.md`,
  `docs/index.md`: decision 29's rules in plain words: at `strong` your own audit counts;
  at `signed` only CI's tests and audit count; the record folders `ci/` and `local/`; what
  `partial` means; the three reasons for a remote runner stay as they are. Check each claim
  against lane 11A's code and name the line.
- `dev/plans/lanes/tl-11B-slides.md`: the three step lists updated (the `strong` slide's
  step 1 says the local audit counts; its step 5 says CI's record is what `signed` will need;
  the `signed` slide says only CI's tests and audit count there), in the deck's shape.

## Acceptance

```
python3 dev/build_report.py
pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_vocabulary.py dev/test_skills.py
bash dev/run_tests.sh
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the floor
sum, what the screenshots showed, the code lines the pages were checked against, and the
full contents of `tl-11B-slides.md`.
