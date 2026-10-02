# Decision 126, second round, lane `run2`: the report

Branch `lane/d126-run2`, one commit of work on `main` at `0c5f99486`, then this report.
Acceptance: `bash dev/run_tests.sh --fast` ended `1038 passed, 9 skipped`, `Suites: 1 passed,
0 failed`. Nothing is pushed, tagged or signed.

## What was built

**4. A marker 0.9.5 wrote that is still in a test.** `scripts/mcp/purlin/status.py` gains
`old_markers(project_root)`, the `(file, line)` places, and `old_marker_line(project_root)`,
the one warning. `sync_status` adds the line to the payload's `warnings`, last, before it
writes the dashboard's data file and before it prints. So the status command, the
`sync_status` tool, the status every run ends on, and the dashboard data the status writes all
carry the same line. No other file of code changed.

How a marker is found: each file git tracks whose extension the update reads is handed to
`update.rewrite_markers(text, ext)`, the update's own public reader, and the places it answers
as left are the places counted. The status and the update's `left <file>:<line> as it was`
therefore name the same lines. Two filters are this lane's:

- Python: a place counts only where `pytest.mark.proof` is code, read with `tokenize`. The
  update also names a line of a comment or a docstring that holds `pytest.mark.proof(`.
- JavaScript and TypeScript: a place counts only where the test run's own reader
  (`markers.js_tests`) finds the tag in a test's title. The update also names a tag in any
  other string.

## Rules and proofs, word for word

`specs/mcp/states.md`: `Highest-Rule` 130 to 132, `Highest-Proof` 307 to 315.

- RULE-131: While a test file git tracks still holds a marker Purlin 0.9.5 wrote that `purlin:init --update` leaves as it was, a `[proof:...]` tag in a test's title or a `pytest.mark.proof` mark, the status carries one warning, the last of its warnings, from the status command and from the `sync_status` tool alike, and the dashboard data the status writes carries it as the last of its warnings: `<n> tests still carry a marker from Purlin 0.9.5, which is not read: <file>:<line>, <file>:<line>, and <n-2> more. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.`, the places in order of file and line; one or two are named with no `and <n> more`, and one opens `1 test still carries`
- RULE-132: A `[proof:...]` tag or a `pytest.mark.proof` in a comment, in a docstring, in a string that is no test's title or in a file git does not track is no such marker, and a project Purlin 0.9.5 set up carries no such warning while its upgrade is pending, in its status or in its dashboard data
- PROOF-308 (RULE-131): A project already on this version tracks `tests/login.test.ts`, whose line 2 holds the title tag `[proof:login:PROOF-1b:RULE-1:unit]`, and `tests/test_login.py`, whose lines 4 and 9 each hold a `@pytest.mark.proof` mark naming `PROOF-2b` and `PROOF-2c`; the status command prints the line `3 tests still carry a marker from Purlin 0.9.5, which is not read: tests/login.test.ts:2, tests/test_login.py:4, and 1 more. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.` exactly once
- PROOF-309 (RULE-131): For that same project the `sync_status` tool answers exactly the text the status command prints, that line included
- PROOF-310 (RULE-131): With the mark on line 9 of `tests/test_login.py` taken out, the status holds the line `2 tests still carry a marker from Purlin 0.9.5, which is not read: tests/login.test.ts:2, tests/test_login.py:4. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.`
- PROOF-311 (RULE-131): With `tests/login.test.ts` deleted as well, the status holds the line `1 test still carries a marker from Purlin 0.9.5, which is not read: tests/test_login.py:4. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.`
- PROOF-312 (RULE-131): The spec `login` of the three-marker project also holds a line under `## Rules` with no number, which the status warns of; the line that opens `3 tests still carry` is the line after that warning, and the one blank line after it is the last above `2 rules. 0 pass their tests.`
- PROOF-313 (RULE-131): After the status of the three-marker project, the last entry of `warnings` in `.purlin/report-data.js` is the line that opens `3 tests still carry`
- PROOF-314 (RULE-132): A project already on this version tracks `tests/test_login.py`, whose docstring holds `@pytest.mark.proof("login", "PROOF-2b", "RULE-2")` at the start of a line and whose comment holds `pytest.mark.proof(`, and `tests/login.test.ts`, which holds `[proof:login:PROOF-1b:RULE-1:unit]` in a `//` comment and in a string passed to `expect`; `tests/test_new.py`, which git does not track, holds a real `@pytest.mark.proof("login", "PROOF-2b", "RULE-2")` above a test. The status holds no line with `a marker from Purlin 0.9.5`
- PROOF-315 (RULE-132): A project holds the settings file Purlin 0.9.5 wrote, with no `tests` key, and tracks `tests/test_login.py` with a `@pytest.mark.proof("login", "PROOF-2b", "RULE-2")` mark above a test; the status command prints its three lines and nothing else, and `.purlin/report-data.js` holds no `a marker from Purlin 0.9.5`

`specs/run/run_script.md`: `Highest-Rule` 111 to 112, `Highest-Proof` 301 to 302.

- RULE-112: A run that ends on the status prints the status's warning for the markers Purlin 0.9.5 wrote that are still in the tests once, in that status, and nowhere above it
- PROOF-302 (RULE-112): A project tracks `tests/test_feat.py`, whose passing test is marked for `feat PROOF-1` and whose second test, on line 7, sits under a `@pytest.mark.proof("feat", "PROOF-1b", "RULE-1")` mark on line 6; `--all --test` exits 0 and prints the line `1 test still carries a marker from Purlin 0.9.5, which is not read: tests/test_feat.py:6. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.` exactly once, below the line that opens `Purlin status:`

The tests are in `dev/test_mcp_server.py` (`TestMarkersFrom095StillInATest`) and
`dev/test_run_script.py` (`TestAMarkerFrom095StillInATest`).

## Seen failing first

Against `main`'s `status.py` (the lane's stashed), 7 of the 9 new tests failed: `states`
PROOF-308 to 313 and `run_script` PROOF-302. `states` PROOF-314 and PROOF-315 pass on `main`:
each says a line is absent. PROOF-314 did fail against the lane's first version, which
counted a lettered tag in a string passed to `expect`; the title filter came from that.

## The things to settle

- **Where the line stands.** Last of the status's warnings, on the line above the blank line
  before the summary sentence, so it reads nearest `Left to do`. The spec warnings keep their
  order above it.
- **What it costs.** On the real copy (422 tracked files), the status took 6.54, 6.40, 6.38
  and 6.47 seconds from `main` and 6.38, 6.39, 6.42 and 6.49 from this lane, run in turn on a
  machine with a load average near 5. `old_marker_line` alone took 0.034 seconds, three times.
  It adds one `git ls-files` and reads only the tracked test files that hold `[proof:` or
  `pytest.mark.proof`.
- **The MCP tool and `purlin_status.py`.** The same text: `diff` of the two on the real copy
  is empty, and PROOF-309 holds them to it.
- **A docstring or a comment.** Neither counts (PROOF-314). The hand-repaired copy,
  `RLabGenMusic-upgrade-2`, keeps `[proof:...]` in the docstrings of its Python tests and
  prints no such line.
- **A pending 0.9.5 project.** Its three lines alone, and no such warning in its data file
  (PROOF-315). A fresh copy of the original 0.9.5 project printed exactly its three lines.

## On the copy of the real project

A `cp -Rc` copy of `RLabGenMusic-upgrade-2` at `12f71c4`, the upgrade's own commit.

- `purlin_status.py --project-root <copy>`: 74 lines, one more than `main` prints, and that
  line is
  `9 tests still carry a marker from Purlin 0.9.5, which is not read: packages/sunvox-project/test/generated_track.unit.test.ts:334, packages/web/test/parameter_lfo.test.ts:154, and 7 more. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.`
  The nine places are six title tags in four TypeScript files and three
  `@pytest.mark.proof` marks in two Python files, the nine the tester rewrote by hand in
  `38b85f2`.
- `purlin_run.py --test --project-root <copy>`, no `--commit`: 178 seconds, 54 of 54
  features selected, `Markers: 533 tied to a test, 0 not tied.`, then the status, which holds
  that same line once, on line 144 of 152. The run ended `476 rules. 475 pass their tests.`
  with `1 test comment to correct` and `1 rule to fix`, and exited 1 for that failing test,
  one of the project's own.
- The dashboard, the copy's `purlin-report.html` on the data file this lane's status wrote,
  with playwright at 1500 and 390 wide, both colour schemes: the line is one notice
  (`div.notice`), one of three, between the test comment to correct and the scope line. The
  page's width equals the window's at both sizes (1500 of 1500, 390 of 390), and the notice's
  text is no wider than its box (1221 of 1221, 283 of 283): no sideways scroll. The page
  needed no change.

## Lines chosen

None. The warning is the plan's, word for word. The one-marker form keeps `For each,` since
the plan gives `1 test still carries` as the only difference.

## Calls the plan did not make

1. **The update is called, not copied.** `status.py` already imported `scripts/init/update.py`
   on every status, to ask `pending`, so the import is not new and the call costs 0.034
   seconds on the real copy. `rewrite_markers` and `TEST_EXTENSIONS` are what is called; no
   name with a leading underscore.
2. **What counts is what the update leaves.** A marker the update can still rewrite, a title
   tag or a mark naming a numbered proof, is not counted: for those the status already ends on
   `→ Run: purlin:init --update`, and `write the proof with purlin:spec` would be the wrong
   instruction. After an upgrade there are none.
3. **A `pytestmark = pytest.mark.proof(...)` line and a mark whose arguments the update cannot
   read count**, each as one place. 0.9.5 read both, and the update leaves both.
4. **A tag in a string that is no test's title does not count**, though the update names it:
   0.9.5 read titles only.
5. **The warning is added in the status, not in the payload.** `scripts/mcp/purlin/payload.py`
   is not this lane's. The data file `purlin:sign` and `purlin:audit` write on their own,
   through `report_data.refresh(project_root)`, and the evidence package's `warnings`
   therefore do not hold the line; the next status or run writes it back to the dashboard.
   To make it hold everywhere, in `payload.build_payload`, after
   `warnings.extend(passed_over)`:

   ```python
   if not (project_module.set_up_by_095(project_root)
           and status_module._update_pending(project_root)):
       old = status_module.old_marker_line(project_root)
       if old:
           warnings.append(old)
   ```

   and the block that appends it in `status.sync_status` goes. That would put the line in the
   evidence package too, which is the owner's call.
6. **A project that has a `tests` setting and declined a migration shows the warning** beside
   its table and `→ Run: purlin:init --update`. Only the three-line status leaves it out.
7. **No doc or skill changed.** `skills/status/SKILL.md` already says the status's warnings
   are printed as they are, and the line says what to do. No file under `references/formats/`
   changed.
8. `--ci` runs end on the status too, so they print the line as well.

## Left, or waiting on another lane

- `docs/upgrading.md`, lane `update2`'s, could say under `What you will see` that the status
  repeats the markers the upgrade left until each is rewritten.
- Call 5, if the owner wants the line in every data file and in the package.
- Not run: the full `bash dev/run_tests.sh`, `dev/windows_run.py`.
