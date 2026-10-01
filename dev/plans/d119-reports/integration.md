# Integration, decision 119

On local `main`, from the base commit `49ca1c26e`. Nothing pushed, tagged, signed or audited.
The numbers, the fixes, every line a lane chose and what is left are in the top section of
`dev/plans/handoff.md`; this report holds what that section does not.

## The merge

Each lane wrote only the files it owns and its report, with one addition: lane `surfaces`
changed one fixture in `dev/test_ai_audit.py` (`email` in place of `hostname`), a file no lane's
list names. `solo.json`, `dev/test_drift.py`, `dev/test_states.py`, `dev/test_specs_reader.py`
and `version-check.yml` were owned and needed no change.

Order: `docs-a`, `run`, `surfaces`, `words`, `own`, `anchors`, `docs-b`. Each was rebased onto
the merged line, its own test files were run, and it was merged fast-forward. No conflict.

| Lane | Its own tests after the rebase |
|---|---|
| `docs-a` | 4 passed, 1 failed: `purlin_docs PROOF-17`, waiting on `words`; it passes from `words` on |
| `run` | 152 passed, 4 skipped |
| `surfaces` | 208 passed, 7 skipped |
| `words` | 31 passed |
| `own` | 4 passed |
| `anchors` | 244 passed; the two shell suites 7 and 10 passed |
| `docs-b` | 4 passed |

The install test's four slow tests were left out of `docs-a`'s rerun: they start the real
`claude`.

## Commits made here

1. `fix(windows_run)`: an argument is refused in one line, exit 2, before anything starts; one
   test with no test comment, since no proof of `windows_run` names it.
2. `docs`: the agent never pushes on its own, and may run a project's own start command after
   the person's yes.
3. `docs`: the two deck lines.
4. `chore(three-levels)`: the plan's greps.
5. `purlin: evidence at b4aac49`, made by `--test --all --commit`.
6. `chore(three-levels)`: `.purlin/evidence/ci/host.json`, removed by the plain run and not
   carried by the commit of the run after it.
7. `chore(three-levels)`: the handoff and this report.
8. `purlin: evidence at <sha7>`, made by a plain `--test --commit` after commit 7: the anchor
   `security_no_dangerous_patterns` covers every file, so commit 7 put its 8 rules out of date.

No spec was edited. No test was changed to fit a number.

## The dashboard, looked at

This repository's data, light and dark, 1500 and 390 pixels, the board and one rule waiting on
Windows (`ai_audit RULE-3`). The header reads `main at d7e12ce, written 16:33 EDT`, `TESTS not
met`, `SIGN-OFF not signed`; the boxes read `0 NO PROOF` and `390 PASSING, 410 RULES TOTAL`. No
sideways scroll and no text cut at any of the four. The rule's page reads `NOT RUN`, `Mac`,
`Win`, `Windows: no run yet`, and its proof carries `@env(windows)`. The page draws no
`Left to do` line and no command, so the payload's `run purlin:test on Windows` shows in the
terminal alone and no page source changed. At 390 pixels a long test name breaks inside a word.

## Not done here

The reading pass and `python3 dev/windows_run.py` are the coordinator's. Appendix A's script as
written prints `0 gone, 5 reworded`; the handoff says why.
