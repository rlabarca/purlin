# Integration, decision 120 (2026-10-01)

Local only, on `main`: no push, no tag, no pull request, no `purlin:audit`, no `purlin:sign`.
`python3 dev/windows_run.py` was not started. Nothing under `dev/plans/` was deleted.

## The merge

Each lane wrote only its own files and its report; no file is in two lanes. Order: `leftovers`,
`signnote`, `prose`, `dark`. Each was rebased onto the merged line with no conflict, its own
test files were run, and it was merged fast-forward.

| Lane | Its test files, after the rebase |
|---|---|
| `leftovers` | 177 passed, 1 skipped |
| `signnote` | 54 passed |
| `prose` | 34 passed (its five files, `dev/test_purlin_docs.py`, `dev/test_plain_checks.py`) |
| `dark` | 72 passed |

No lane's spec text contradicts decision 120, so no spec was edited at integration.

## The edits the lanes handed over, one commit each

- `docs: the audit skill quotes the stop as the product prints it, changed while a bug was planted`:
  `skills/audit/SKILL.md`.
- `test: the test projects run pytest with no extra argument`: `dev/run_project.py` drops
  `extra='--ignore=mutants'`. `dev/test_run_script.py` and `dev/test_states.py`, the two files
  that use the helper: 136 passed.
- `chore: hand_notes is public in payload.py, since sign.py reads it from another module`:
  `payload._hand_notes` is `payload.hand_notes`; the caller in `payload.py` holds the result in
  `notes`; `sign.last_notes` calls the new name.
- The deck was left alone.
- `chore: remove the evidence from another system of five features with no proof tagged for Windows`:
  `.purlin/evidence/ci/reports.json`, `drift.json`, `evidence_writer.json`, `signatures.json`,
  `specs.json`. Each held `remote runner`, and none of the five specs has a proof ending
  `@env(windows)`. The ten files left (`ai_audit`, `config_engine`, `evidence`, `package`,
  `run_script`, `scaffold`, `server`, `states`, `update`, `upstream`) hold no `remote runner`,
  and each spec has at least one such proof.
- Not handed over, done: `.purlin/evidence/README.md` also held `remote runner`. It is now the
  bytes of `templates/evidence-readme.md`.

## The numbers

| | Result |
|---|---|
| `bash dev/run_tests.sh` | 819 passed, 0 failed, 9 skipped; 4 suites passed, 0 failed |
| `purlin_run.py --test` | 823 markers tied, 0 not tied; 400 of 411 rules pass; left: 5 slow proofs, 6 rules to test on Windows |
| `purlin_run.py --test --all --commit` | 823 markers tied, 0 not tied; 39 specs, 411 rules, 823 proofs; 405 rules pass; `purlin: evidence at e79e00d` |
| Appendix A's script | `0 gone, 6 reworded, 817 right as they stand.` |

Spec totals moved from 410 rules and 820 proofs by `signatures RULE-129` and `PROOF-249` to
`251`. No rule failed, none is partial or without a test, no spec is to repair, no test comment
is to correct, no warning is printed.

The script's sixth line is `purlin_report PROOF-66`, `reworded since 0086a46`. The test and the
proof were both changed in the lane's second commit, `24ed112`. The rebase gave both of the
lane's commits the commit time 1790892642, and the script takes the first of two equal times.
Nothing was changed for it, nor for the five slow proofs.

The built page was committed once (`chore: rebuild the dashboard page after decision 120`). A
test run had rebuilt it before that, and it was first swept into the `hand_notes` commit; that
commit was rewritten, before anything else was built on it, to hold the two code files alone.
The two docs screenshots changed with the dark tones and were committed.

## The dashboard, looked at

Playwright from `.venv`, this repository's own data, dark and light, 1500 and 390 pixels, the
board with `security_no_dangerous_patterns` open and the screen of its `RULE-1`. Screenshots are
in the session's scratch folder, `d120-look/`; the regulated sample's are in `d120-look/fixture/`.

| Screen | Texts | Under their least ratio | Copper, lowest |
|---|---|---|---|
| dark, 1500, board | 298 | 0 | 6.73 |
| dark, 1500, rule | 38 | 0 | 6.73 |
| dark, 390, board | 290 | 0 | 6.73 |
| dark, 390, rule | 38 | 0 | 6.73 |
| light, 1500, board | 298 | 0 | 7.38 |
| light, 1500, rule | 38 | 0 | 7.38 |
| light, 390, board | 290 | 0 | 7.38 |
| light, 390, rule | 38 | 0 | 7.38 |

- No page scrolls sideways, nothing runs past the right edge, nothing is cut.
- This repository has no failing rule, so its board draws no red text. On the regulated sample
  the one red text measures 7.75 in the dark theme and 7.80 in the light. The red was measured
  there, not judged by eye on this repository's data.
- Found, older than decision 120, not fixed: at 390 pixels the `SPEC` path on a rule's screen
  breaks inside a word, `specs/_anchors/security_no_dangero` then `us_patterns.md`, in both
  themes. `purlin_report RULE-75` names counts, labels, boxes and rule ids, not paths.

## Left open

- The review's fixes, `dev/plans/d120-reports/coverage-review.md`.
- The Windows run: 6 rules wait on it.
- The real-skills QA check, and the planted-bug measurement's result.
- The path that breaks at 390 pixels, above: the owner says whether a path may break.
- The lanes' own open points are in their reports and listed in `dev/plans/handoff.md`.
