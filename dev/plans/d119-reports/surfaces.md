# Lane `surfaces`, decision 119

Branch `lane/d119-surfaces`, one commit of code, tests, fixtures and the format, then this report.

## Test numbers

`python3 -m pytest dev/test_summary.py dev/test_export.py dev/test_signatures.py dev/test_init_scaffold.py dev/test_init_update.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before, with `dev/test_ai_audit.py` | 209 | 0 | 7 |
| After, the five files | 170 | 0 | 7 |
| After, `dev/test_ai_audit.py`, `dev/test_states.py`, `dev/test_purlin_report*.py` | 176 | 0 | 0 |

Nothing failed before the build: the old tests still passed on the old code, against proofs the
base commit had reworded. No test waits on lane `run`: every test here writes its own sections.

Appendix A's script over the five files: `0 gone, 0 reworded, 177 right as they stand.`
Section 8's two greps over the lane's files: empty.

The break: `RUN_AGAIN['ci']` changed to `purlin:test at %s`; the test of `signatures PROOF-226`
failed; restored. The file was not yet committed, so it was restored from a copy in the scratch
folder, not with `git checkout --`.

## Tests

- Deleted, 1: `dev/test_init_scaffold.py`, `TestNoRunnerFile` (`scaffold PROOF-173`).
- Rewritten, 7: `dev/test_summary.py` 3 (`summary PROOF-8`, `33`, `56`); `dev/test_export.py` 3
  (`package PROOF-25`, `66`, `67`) and `section`; `dev/test_signatures.py` 1
  (`signatures PROOF-226`) and `section`.
- Added: none.
- `dev/test_ai_audit.py`: the one fixture in `_rules_evidence` carries
  `'email': 'ada@example.com'` in place of `hostname`. Nothing else in that file changed.
- `dev/test_init_update.py`: no change was needed. No proof of `update` names the workflow line.

## Code

- `scripts/mcp/purlin/summary.py`: the command of `to_test_remote` is `run purlin:test on %s`,
  filled with the same systems as the words (K5). The key keeps its name.
- `scripts/export/package.py`: `REMOTE_RUNNER` and `RUN_REMOTE_LINE` are gone; `_by` answers the
  section's email or `unknown` under both sources; `run_lines` prints `RUN_LINE` for every run (K6).
- `scripts/review/sign.py`: `RUN_AGAIN['ci']` is `purlin:test on %s`, filled with the systems of
  the `ci` results named (K6).
- `scripts/init/update.py`: `_apply_workflows` prints K7's line and nothing after it. What it
  removes is unchanged (plan section 7).
- `scripts/init/scaffold.py`: the docstring alone; it names no runner file.
- `references/formats/package_format.md`: 9 to 10, in the same commit.
- `dev/fixtures/report/regulated.json`, `team.json`: each `machines` value is a host's name.
  `solo.json` held nothing to change.

## Lines a person reads

As the plan has them:

- `  22 rules to test on Windows: run purlin:test on Windows`, and `1 rule ...` for one.
- `No sign-off: these results were not taken on this version of the code, 1cf829e: audit on Windows. Run purlin:test on Windows, then purlin:sign.`
- `Tests run by runner@example.com on build-7 at 2026-10-01 12:17 UTC on 1cf829e: 20 rules on Windows.`
- `removed 1 workflow that committed proof files`

Chosen here:

- Two systems in the sign-off's refusal are joined with ` and `, in the order the results are
  named: `Run purlin:test on Linux/Unix and Windows, then purlin:sign.` It prints from
  `scripts/review/sign.py`, `_results_fill`. The status joins its systems the same way.
- The fixtures' machine names: `build-7` for Linux/Unix, `build-8` for Windows, `build-9` for
  macOS. They show in the dashboard's per-system boxes.

## Differences from the plan

- Section 5 gives the format's `to_test_remote` command as `purlin:test on <System>`. The payload
  holds `run purlin:test on <systems>` (K5 and `summary RULE-23`), so the format says that.
- The plan counts 4 test files for this lane and names 3 fixtures; the lane also checked
  `dev/test_init_update.py` (no change) and changed one fixture in `dev/test_ai_audit.py`, as the
  lane's prompt asked.

## Open, or for another lane

- The walk's line for a run under `ci` has no proof: `signatures PROOF-227` covers a local run
  alone. It was checked by hand, and no test was added, since a test needs a proof.
- K7's line has no proof either. `update` has no proof that reads it.
- The payload's `command` for `to_test_remote` now carries the word `run`. The dashboard shows
  the payload's `command`; whether the page reads well with it is for the dashboard's owner to
  look at. The page source under `scripts/report/src` holds no remote-run phrase.
- No report fixture holds a `to_test_remote` line, so none shows the new command.
- The screenshots may show a fixture's machine name; integration step 6 retakes them.
- Failures in files this lane does not own: none seen. `scripts/run/` and
  `scripts/mcp/purlin/evidence.py` still hold `remote runner`; they are lane `run`'s.
