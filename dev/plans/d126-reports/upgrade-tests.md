# The three upgrade tests on a real 0.9.5 project

Each was run by an agent that built none of the code, on its own fresh copy of a real 0.9.5
project (54 specs, 476 rules, 523 proof lines, 542 test markers; pytest through `uv` from a
subfolder, vitest in three tiers), from `README.md` and `docs/upgrading.md` alone. The copies
are beside this repository under `purlin-wt/`: `RLabGenMusic-upgrade`, `-upgrade-2`,
`-upgrade-3`. The original was never touched.

| | Test 1, before decision 126 | Test 2, after the twenty | Test 3, after the five |
|---|---|---|---|
| Status before the upgrade | 162 lines | 3 lines | 3 lines |
| The upgrade | 15 s, 151 stray backup files | 15 s, 0 stray files | 9 s, 0 stray files |
| Kind-of-test tags left in the specs | 438 | 438 | 0 |
| First full run, untouched | 57 of 476 rules; 434 markers with no result | 474 of 476; 533 tied, 0 not tied | 475 of 476; 533 tied, 0 not tied |
| Rules not passing in that run | the upgrade's own faults | 2, the project's unstable tests | 1, the project's unstable test |
| Hand repairs no page describes | five kinds | none | none |
| Reached `Tests: met` by the output alone | no | yes, 476 of 476 | yes, 476 of 476 |
| Every printed next step the right one | no | no (two were wrong) | yes, but one (below, 5) |

The project has three or four unstable tests of its own (`project_history`,
`project_workspace`, `stem_workbench`): each fails on some full runs and passes when its
feature is run alone.

A run of the upgraded project with the code before and after decision 126 gave the same
answer: 499 markers tied to the same tests, 471 of 476 rules, the same five not passing.

## Open after test 3, none fixed

None stopped the upgrade.

1. The terminal prints `1 spec names no files, so its tests run every time: patch_graph`; the
   dashboard does not show that line.
2. With one rule failing, the dashboard's count boxes show no failing count and the failing
   spec stood about four screens down; the terminal lists it first.
3. The warning for tests that still carry a 0.9.5 marker names two of nine and names neither
   the feature nor the rule. The whole list is only in the update's own output.
4. The update names such a marker at one line (`parameter_lfo.test.ts:153`) and the status at
   the next (`:154`).
5. After a failure in the first full run the printed step is `purlin:build <feature>`; for a
   timeout, running the feature alone is the better first step, and only the upgrade page
   says so.
6. `To sign it: purlin:sign` is printed after a `--commit` run of one feature, while most
   results were taken on an earlier commit. Whether `purlin:sign` then refuses was not tried.
7. The test skill does not say how `--commit` is passed.
8. `CLAUDE.md` is listed eighth under `Purlin left these for you:`; the page says it is the
   one to change first.
9. 86 lines of `[proof:...]` stay in Python docstrings, some naming a lettered id that was
   renumbered.
10. The vitest proposal cites the script `test` (`vitest run --project unit`) beside a
    command with no `--project`; `test:all` is the one it matches.
11. `<n> features whose results are not committed` shows only once nothing else is left.
12. `Every file the update changed is kept as it was under .purlin/runtime/update-backup/`:
    a deleted file is only in git, at the commit the line before names.
13. The apply run prints the whole pending list again before its totals.
14. A 0.9.5 project's status replaces its `purlin-report.html` before any upgrade runs.
15. The warning for leftover markers is added by the status and is not in the evidence
    package (`d126-reports/run2.md` holds the change that would put it there).
