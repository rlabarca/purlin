# Decision 127, lane `run3`: the report

Branch `lane/d127-run3`, one commit of work on `main` at `c4c548587`, then this report.
Acceptance: `bash dev/run_tests.sh --fast` ended `1071 passed, 9 skipped`, `Suites: 1 passed,
0 failed`. Nothing is pushed, tagged or signed.

## What was built, per item

**A. A full run says which test files it left out.** `scripts/run/purlin_run.py`,
`unmarked_line`. A `--test` or `--audit` run with `--all` prints, on the line after
`Markers:`, `12 test files carry no marker and were not run.`
(`1 test file carries no marker and was not run.`). It counts the files the `files` patterns
match that hold no marker. Nothing is printed at zero, on a run without `--all`, or on `--ci`.

**C. The 0.9.5-marker warning names every test, with its rule.**
`scripts/mcp/purlin/status.py`. `old_markers(project_root)` returns
`(file, line, feature, rule)`, sorted by file then line; `feature` and `rule` are None where
the marker names none. The terminal prints the opening line, one line per test, the first 20
and then `  and <n> more`, then the `For each` line. The dashboard's data carries the plan's
one line, last of `warnings`. `old_marker_line` and `old_marker_lines` now take what
`old_markers` found.

**6. The closing line agrees with the sign-off.** What `purlin:sign` refuses:
`scripts/review/sign.py` builds the package and refuses with `No sign-off: these results were
not taken on this version of the code` where any section holding a result for a rule names a
commit after which a commit changes a path outside `.purlin/` (or the `tests` setting), or
holds a slow result a plain run kept. It then refuses with `No sign-off: these results were
taken while files were changed and not committed` where such a section reads `dirty` true.
`facts.results_to_retake` reads the same from the working tree; `summary.closing_line` words
the line; `status.sync_status` sets it before it writes the dashboard's data. Each test asks
`sign.refusal` about the same project, so the two are held together.

**7. The test skill says how `--commit` is passed.** Step 1 says each option goes on the
command line before `--project-root`, and gives the hand-off whole.

**11. The status skill says when the uncommitted-results line shows.** Step 3.

**14. A pending 0.9.5 project's status writes nothing.** `sync_status` answers the three
lines before it reads the project or refreshes anything.

## Rules and proofs, word for word

`specs/mcp/states.md`: `Highest-Rule` 132 to 136, `Highest-Proof` 315 to 322.

- RULE-131 reworded: While a test file git tracks still holds a marker Purlin 0.9.5 wrote that `purlin:init --update` leaves as it was, a `[proof:...]` tag in a test's title or a `pytest.mark.proof` mark, the status prints one warning, the last of its warnings, from the status command and from the `sync_status` tool alike: `<n> tests still carry a marker from Purlin 0.9.5, which is not read:`, then one line per test in order of file and line, then `For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.`; one test opens `1 test still carries`
- RULE-132 reworded: its end, `in its status or in its dashboard data`, is gone, since no data file is written.
- RULE-133: Each test's line of that warning reads `  <file>:<line>  <feature> <rule>`: the line the old tag or mark is on in the file as it stands, then the feature and the rule read from the marker itself; a marker that names no rule shows the feature alone
- RULE-134: Over 20 such tests, the warning lists the first 20 and then `  and <n> more`
- RULE-135: The dashboard data the status writes carries that warning as one line, the last of its warnings: `<n> tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each.`, opening `1 test still carries` for one
- RULE-136: The status of a project Purlin 0.9.5 set up, while its upgrade is pending, writes no file: `purlin-report.html` and `.purlin/report-data.js` stay byte for byte as they were, and where the project has neither, neither is written
- PROOF-308, 309, 310, 311 and 312 reworded to the lines the terminal now prints; PROOF-313 reworded and moved to RULE-135; PROOF-315 reworded, its data-file half gone. Each test changed on its kept line.
- PROOF-316 (RULE-133): A project tracks `tests/login.test.ts`, where a `// purlin: login PROOF-1` comment stands on line 2 above a first test, and a second test's title opens on line 7 and is joined on line 8 to the tag `[proof:login:PROOF-1b:RULE-1:unit]`; the status holds the line `  tests/login.test.ts:8  login RULE-1`
- PROOF-317 (RULE-133): A project tracks `tests/login.test.ts`, whose line 2 holds the title tag `[proof:login:PROOF-1b:unit]`, and `tests/test_login.py`, whose line 4 holds `@pytest.mark.proof("login", "PROOF-2b")`; the status holds, one after another, the opening line for 2 tests, `  tests/login.test.ts:2  login`, `  tests/test_login.py:4  login` and the `For each` line
- PROOF-318 (RULE-134): 22 marks in `tests/test_login.py`, on lines 4, 9 and every fifth line to 109; after the opening line the status holds the 20 lines for lines 4 to 99, then `  and 2 more`, then the `For each` line
- PROOF-319 (RULE-135): one mark; the last entry of `warnings` in `.purlin/report-data.js` is `1 test still carries a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each.`
- PROOF-320 (RULE-136): A project holds the settings file Purlin 0.9.5 wrote, a `purlin-report.html` and a `.purlin/report-data.js` of its own, both ignored by git; the status command prints its three lines, and every file under the project outside `.git` holds the bytes it held before
- PROOF-321 (RULE-136): the same through the `sync_status` tool
- PROOF-322 (RULE-136): The same project with neither file has neither after the status command

`specs/mcp/summary.md`: `Highest-Rule` 26 to 29, `Highest-Proof` 63 to 69.

- RULE-18 reworded: after the line, `unless purlin:sign would refuse the results as they stand, where RULE-27 or RULE-28 gives the line; where the tests are not met or this code is signed there is no last line`
- RULE-27: Where the last line would name `purlin:sign` and the evidence holds, for some rule, a result that was not taken on this version of the code, one taken at a commit after which a commit changes a path outside `.purlin/`, or a slow result a plain run kept, the last line reads `Every rule passes its tests on the committed evidence. Before a sign-off, run <command>: a sign-off counts only results taken on this version of the code.`; `<command>` is `purlin:test --all --commit` for results taken on this machine and `purlin:test on <systems>` for a project's own run on another system, joined by ` and ` where both apply. `purlin:sign` refuses that project with `No sign-off: these results were not taken on this version of the code`
- RULE-28: Where every result was taken on this version of the code and one was taken while files were changed and not committed, the last line reads `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results taken with nothing uncommitted.`; `purlin:sign` refuses that project with `No sign-off: these results were taken while files were changed and not committed`
- RULE-29: The dashboard data the status writes carries, under `last_line`, the last line the status prints
- PROOF-64 (RULE-27): two passing rules, then a commit adding `notes.txt`: the status ends on the line naming `purlin:test --all --commit`, and `purlin:sign`'s refusal opens `No sign-off: these results were not taken on this version of the code`
- PROOF-65 (RULE-18): nothing committed since: the status ends on `To sign it: purlin:sign`, and the sign-off refuses for neither reason
- PROOF-66 (RULE-27): a result marked `kept`
- PROOF-67 (RULE-27): results from a run on Windows before the later commit: `run purlin:test on Windows`
- PROOF-68 (RULE-28): a section reading `dirty` true
- PROOF-69 (RULE-29): `last_line` in `.purlin/report-data.js` is the status's last line

`specs/run/run_script.md`: `Highest-Rule` 112 to 113, `Highest-Proof` 302 to 307.

- RULE-113: A `--test` or `--audit` run with `--all` prints, on the line after `Markers:`, `<n> test files carry no marker and were not run.`, `1 test file carries no marker and was not run.` for one, counting the test files the `files` patterns of the `tests` setting match that carry no marker; the files of a suite started with no file list, or whose command names no `{files}`, are run and not counted. With none, and on a run without `--all`, it prints no such line
- PROOF-302 reworded to the three lines the run's status now prints; its test changed on its kept line.
- PROOF-303 (RULE-113): one marked passing test beside 12 unmarked files whose test fails: exit 0, `12 test files carry no marker and were not run.` on the line after `Markers: 1 tied to a test, 0 not tied.`, and the suite's command names no `test_plain` file
- PROOF-304 (RULE-113): one such file reads `1 test file carries no marker and was not run.`
- PROOF-305 (RULE-113): none: no `no marker` in the output
- PROOF-306 (RULE-113): the twelve, `--feature feat --test`: no `no marker`
- PROOF-307 (RULE-113): a suite whose command names `tests` and no `{files}`: the unmarked test runs, and no `no marker`

`specs/skills/skill_test.md`: `Highest-Rule` 23 to 24, `Highest-Proof` 55 to 57.

- RULE-24: `skills/test/SKILL.md` gives the hand-off as the run script takes it: one line that names `scripts/run/purlin_run.py` with `--test`, `--all` and `--commit`
- PROOF-56 and PROOF-57: the shipped file has such a line; a copy without `--test --all --commit` is reported.

`specs/skills/skill_status.md`: `Highest-Rule` 16 to 17, `Highest-Proof` 40 to 42.

- RULE-17: The skill says when the line `<n> features whose results are not committed` shows: only once nothing else stops the tests being met
- PROOF-41 and PROOF-42: exactly one sentence holds both phrases; a copy without the second holds none.

## Seen failing first

Against the code before each change: `states` PROOF-308 to 313 and 316 to 322 (13 failed;
PROOF-314 and 315 pass either way, each saying a line is absent); `summary` PROOF-64, 66, 67,
68 and 69 (PROOF-65 is the other direction and passes on `main`); `run_script` PROOF-302,
303 and 304 (305 and 306 say a line is absent), and PROOF-307 against this lane's first
version, which counted the files of a suite run whole; `skill_test` PROOF-56 and 57 and
`skill_status` PROOF-41 and 42 against `main`'s skill files. PROOF-316 failed on `main` for
the line's shape only: `main` already gave line 8.

## On the real copies

- **C**, a copy of `RLabGenMusic-upgrade-3` at `e607e7c`:

  ```
  9 tests still carry a marker from Purlin 0.9.5, which is not read:
    packages/sunvox-project/test/generated_track.unit.test.ts:334  generated_track RULE-1
    packages/web/test/parameter_lfo.test.ts:154  parameter_lfo RULE-4
    packages/web/test/parameter_lfo.test.ts:203  parameter_lfo RULE-6
    packages/web/test/sample_controls.test.ts:78  sample_controls RULE-3
    packages/web/test/stem_order.browser.test.tsx:188  stem_order RULE-5
    packages/web/test/stem_order.browser.test.tsx:271  master_solo RULE-3
    pipeline/tests/test_layered_voice.py:97  layered_voice RULE-10
    pipeline/tests/test_percussive_match.py:179  percussive_match RULE-7
    pipeline/tests/test_percussive_match.py:213  percussive_match RULE-7
  For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.
  ```

  The data file holds `9 tests still carry a marker from Purlin 0.9.5, which is not read. Run
  purlin:status to see each.` Seven lines match the update log's `left <file>:<line>`. Two do
  not: the log reads `parameter_lfo.test.ts:153` and `:202`. See the first call below.
- **A**, a copy at its HEAD `cf23472`, `--test --all`, no `--commit`: 203 seconds,
  `Markers: 542 tied to a test, 0 not tied.`, and no such line. The patterns match 95 test
  files and all 95 carry a marker, so the count is 0. The run ended `476 rules. 475 pass
  their tests.`, exit 1, for `project_workspace` RULE-8, one of the project's unstable tests.
- **6**, the same copy before that run: `476 rules. 476 pass their tests.` and the last line
  `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test
  --all --commit: a sign-off counts only results taken on this version of the code.` 41 of 54
  features hold results taken at `e607e7c`, `4366261` or `7cb0200`. `sign.refusal` on that
  copy answers `No sign-off: these results were not taken on this version of the code,
  cf23472: bus_chain, ...`. `main` printed `To sign it: purlin:sign` there.
- **14**, a fresh copy of `RLabGenMusic`: the status printed its three lines; no file under
  the copy changed; `purlin-report.html` and `.purlin/report-data.js` compare equal to the
  original's with `cmp` (sha256 `6084f989...` and `0db68c54...` before and after). `main`'s
  status on a second copy replaced both.

## Lines chosen

- `Every rule passes its tests on the committed evidence. Before a sign-off, run <command>: a sign-off counts only results taken on this version of the code.` The plan's line ends `taken on this commit`. A run with `--commit` takes its results on one commit and commits them in the next, so results a sign-off counts are never taken on HEAD itself; `this version of the code` is the sign-off's own refusal's words.
- `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results taken with nothing uncommitted.`
- `<command>` for results from another system: `purlin:test on <systems>`; both: `purlin:test --all --commit and purlin:test on Windows`.

## Calls the plan did not make

1. **The status keeps the tag's own line, and the upgrade's line is the one to change.** The
   plan says to print the line the upgrade prints. The two differ because the upgrade prints
   the line in the file as it was before its own rewrite: it put one comment above each of two
   earlier tests in `parameter_lfo.test.ts`, so the tag it named at 153 is on 154 in the file
   it wrote. Printing 153 would name a line that does not hold the tag, and would drift
   further with each edit. So `old_markers` gives the line in the file as it stands (RULE-133,
   PROOF-316), and the contract's `(file, line)` holds. The change that makes the upgrade
   agree is lane `update3`'s file, in `_apply_markers` of `scripts/init/update.py`:

   ```python
   for rel, (new, count, left) in sorted(found.items()):
       if count and rel in files:
           # Rewritten: each marker left is named by its line in the file as written.
           left = rewrite_markers(new, os.path.splitext(rel)[1].lower())[2]
       for number, lettered in left:
   ```

   Tried without changing the file: on the real file before the upgrade, `rewrite_markers`
   gives 153 and 202, and read again from the text it wrote, 154 and 203.
2. **The closing line also covers results taken with files uncommitted** (RULE-28), the
   sign-off's next refusal, whose remedy is the same run.
3. **The closing line is set in the status, not in the payload** (`payload.py` is lane
   `dashboard3`'s). The data file `purlin:sign` and `purlin:audit` write on their own keeps
   `To sign it: purlin:sign`; the next status writes the corrected line. To hold everywhere,
   `payload.build_payload` would call `summary.closing_line(summary.last_line(left, signoff),
   facts.results_to_retake(project_root, feature_entries))`.
4. `facts.results_to_retake` reads which sections speak for a rule as
   `scripts/export/package.py` does, in ten lines of its own, since that file's readers are
   private and need a built package. `summary.RUN_AGAIN` holds the two commands
   `sign.RUN_AGAIN` holds.
5. **A suite run whole is not counted under A.** Where a suite is started with no file list
   (over 30,000 characters) or its command names no `{files}`, its unmarked files do run.
6. A `--ci` run prints no such line under A.
7. One test with two old tags on one line is one line of the warning, naming the first.
8. `dev/test_run_script.py`'s `_touched_project` gained the `.gitignore` setup writes: without
   it the run's own files made every result one taken with files uncommitted, and the status
   now says so.
9. Two rules for the skills (`skill_test` RULE-24, `skill_status` RULE-17), so items 7 and 11
   each start from a failing test.
10. One commit holds every item: they share `status.py`, the two skills and the specs.
11. No file under `references/formats/` changed.

## Left, or waiting on another lane

- Call 1, in `scripts/init/update.py`.
- `docs/upgrading.md` line 238 (lane `update3`) still shows the warning as one line.
- `references/formats/marker_format.md` line 243 lists what a run prints after `Markers:`
  and could name the new line; no lane owns the file this round.
- `scripts/mcp/purlin/payload.py` line 76, the example `last_line`, is unchanged and still a
  line the status prints.
- Purlin's own status on `main` will read `Before a sign-off, run purlin:test --all --commit`
  until integration step 2, since commits after the last evidence changed `dev/plans/`.
- Not run: the full `bash dev/run_tests.sh`, `dev/windows_run.py`.
