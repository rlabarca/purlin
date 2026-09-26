# Lane 9B: the board fits a laptop, and a row says when its tests did not run

Plan: `dev/plans/three-levels.md` (Part A, decisions 23 and 24). Rules:
`dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md`. Worktree
`/Users/richlabarca/LocalCode/purlin-wt/9B`, branch `lane/9B` off `lane/8B`. **Do not push.
Do not open a pull request.** Your work stays committed on your branch. Lane 9A works in
parallel on `payload.py`, `specs.py`, the vocabulary guard and the counts test; touch none of
those. It also adds `remote_url` to the payload and `solo.json`; you need nothing from it.

## 1. The board fits 1100px without a sideways scroll

After lane 7A the column floors sum to 1288px, so at 1100px `Strong` and `Signed` are off
screen and a laptop reader never sees the signed column. Bring the sum under 1080px without
losing a column: move the age (`13 hours old`) out of the `Last run` cell into its tooltip
and keep the three operating-system boxes and the source word (`ci`, `developer`, `local`)
on one line, so `Last run` needs no more than 190px; take `Spec` to 150px. Re-check every
floor is still wide enough for its widest content in the regulated fixture and in this
repository's own payload. At 1440 nothing should look different except the age moving. Keep
the horizontal scroll as the fallback under the new sum. Screenshot 1100 and 1440 in both
themes with playwright and look at them.

## 2. A `Tests` cell says when its tests did not run

The `Tests` cell counts `passed`, `failing` and `no test`; a rule whose passed cell reads
`not run` or `code changed` is in none, so a feature whose CI record is stale reads `0 passed`
in the idle tone while the reason sits only on the rule's row. Add a fourth part, `n not run`
in the warn tone, counting rules whose passed cell reads `not run` or `code changed`, rendered
only when non-zero like the others. Then a feature with 24 rules behind changed code reads
`0 passed · 24 not run`. The rule screen and the `why` on the cell already say which of the
two it is.

## Tests and spec

`dev/test_purlin_report.py` and `dev/test_purlin_report_board_layout.py`: the floors, the
`Last run` text, the tooltip carrying the age, the fourth part; the 1100px assertion now
checks that `Signed`'s header is inside the viewport. `specs/dashboard/purlin_report.md`: the
column-floor rule and the `Tests` rule follow. `docs/dashboard.md`: the `Last run` and
`Tests` sentences follow. Rebuild with `python3 dev/build_report.py` (1200-line limit holds)
and recapture the five screenshots.

## Acceptance

```
python3 dev/build_report.py
pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_vocabulary.py
wc -l scripts/report/purlin-report.html
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the new
floor sum, and what the four screenshots showed.
