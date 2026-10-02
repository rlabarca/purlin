# Decision 126, lane `run`: the report

Branch `lane/d126-run`, one commit of work on `main` at `a84988cdd`, then this report.
Acceptance: `bash dev/run_tests.sh --fast` ended `1000 passed, 9 skipped`, `Suites: 1 passed,
0 failed`. Nothing is pushed, tagged or signed.

## What was built, per finding

**2. A title with an escaped apostrophe, or joined from several strings.**
`scripts/mcp/purlin/markers.py`: `js_tests` reads the title through `_js_title`. `\'`, `\"` and
every other JavaScript escape are read as the character; string pieces joined with `+` are one
title, across lines and comments; white space at either end is cut, since the report reader
cuts it too. A title that is not one plain string, a template holding `${}` or a variable,
makes a test with `plain` false: a marker above it is untied, ties to no later test, and is
listed in `FileMarkers.unreadable`. `scripts/run/reports.py` prints the plan's line for it,
once per test. Every function the reader had keeps its name and arguments; `Test` gains the
keyword `plain` and `FileMarkers` the list `unreadable`.
Other languages checked: Python, C# and Go tests are named by an identifier, so none has the
fault.

**4b. `--all` and the file list.** Why it dropped the list: by design. `main` computed
`narrow = len(selected) < len(features)` and handed `{files}` nothing for a run over every
feature (`run_script RULE-58`, "runs every suite whole"). pytest started from the top folder
with no path finds no `pipeline/pyproject.toml`; given `pipeline/tests/...` paths it finds it.
Now every run hands each suite its marked files. The limit kept: a command over 30,000
characters is started with no file list, and the run says so (Windows refuses a command line
over 32,767 characters, Linux one argument over 131,072 bytes, and the whole command is one
argument to bash). `references/supported_frameworks.md` documents it and what a project with
its test settings in a subfolder adds.

**7. `Check that their tests ran and were not skipped`, when they ran.** `reports.ran_as` finds,
for a marked test with no result, a passing or failing case in the same file whose name
differs from the title only by white space, quotes, backslashes or `+`. The run names each
such marker with both names in place of the skipped-tests sentence, five then a count.

**6. The status before the upgrade.** `status.sync_status` answers three lines for a project
0.9.5 set up while `update.pending` is not empty; the MCP tool and `purlin_status.py` answer
the same. See the first call below.

**19. A line as each suite starts.** `Running <suite>: <the command as run>`, flushed, in place
of `Running the <suite> suite.`

**13. A changed `tests` setting.** `fingerprint.setting_changed` shows it without a change to
the evidence format: the settings file at the commit a section names holds another `tests`
setting than the disk, and the feature's marker files as they are now, hashed with the earlier
setting, give the `tests` part the section stored. The run prints the line before it selects;
the status prints it under the table.

**14. What `--commit` left.** After the two commits the run lists what git still shows outside
`.purlin/`, 10 then `and <n> more`, then the plan's sentence. Checked against `purlin:sign`:
`scripts/review/sign.py` refuses with `No sign-off: these results were taken while files were
changed and not committed` when a section's `dirty` is true, and `dirty` is any line of
`git status --porcelain` outside `.purlin/`, untracked files included. The sentence is true as
written. The list therefore names untracked files too, not only tracked ones.

**18. The commit subject.** Over 5 features: `purlin: specs, tests and settings for <n>
features`, the features in the body, one per line.

## Rules and proofs, word for word

`specs/run/reports.md`: `Highest-Rule` 39 to 41, `Highest-Proof` 125 to 129.

- RULE-6 reworded: "with a literal title" is now "whose title is one plain string".
- RULE-40: A JavaScript or TypeScript title is read as the string it makes: `\'` and `\"` are read as the quote, string pieces joined with `+` are read as one title, and white space at either end is cut
- RULE-41: A JavaScript or TypeScript test whose title is not one plain string, a template holding `${}` or a variable, has no result matched to it: a marker above it is counted as not tied and ties to no later test, and the run prints `<file>:<line>: the test's title is not one plain string, so its result cannot be matched. Write it as one string.`, the line the test's own
- PROOF-126 (RULE-40): A report names the passing case `bus > a tap after the node's own gain`, and the test file writes that title in single quotes with its apostrophe as `\'`; the evidence lists the marker above it as `pass`
- PROOF-127 (RULE-40): A report names the passing case `bus > every route is forwarded to it`, and the test file writes the title over two lines as `'every route is ' + 'forwarded to it ' + ''`; the evidence lists the marker above it as `pass`
- PROOF-128 (RULE-41): On line 4 of `tests/login.test.ts` a test titled by a template holding `${name}` sits under the marker `login PROOF-1`; the run prints `tests/login.test.ts:4: the test's title is not one plain string, so its result cannot be matched. Write it as one string.` and `Markers: 0 tied to a test, 1 not tied.`, and exits 1
- PROOF-129 (RULE-41): A test titled by the variable `title` sits under the marker `login PROOF-1`, above a passing test `second` under `login PROOF-2`; the evidence lists `PROOF-1` as `missing` with no test and `PROOF-2` as `pass`
- PROOF-20 reworded: `printing `Running the pytest suite.` alone` is now `printing one line that begins `Running `, the one that begins `Running pytest: ``; its test changed on its kept line.

`specs/run/run_script.md`: `Highest-Rule` 107 to 111, `Highest-Proof` 291 to 301.

- RULE-58 reworded: Every run, `--all` included, gives each suite's `{files}` only the test files that carry a marker of a feature it runs, and starts no suite that has none; where the command with its files would be longer than 30,000 characters the suite is started with no file list, and the run prints `The <suite> suite has <n> test files, more than one command line holds, so it runs with no file list.`
- RULE-108: A marker with no result whose test the report holds, passing or failing, in the marker's own file under a name that differs from the test's title only by white space, quotes or joined pieces is named under `Evidence is missing` as `<feature> <id> at <file>:<line>: its test ran, and the report names it differently. The title reads "<title>" and the report reads "<name>". Write the title as the report reads, then run purlin:test.`, and not in the line that says to check that its test was not skipped; five such markers are named and the rest counted
- RULE-109: As each suite starts the run prints `Running <suite>: <the command as run>`, on its output before the suite's command starts; for an `exit` suite, whose command runs once per file, the line reads `Running <suite>: <its command>, once for each of <n> files`, or `, for 1 file`
- RULE-110: A `--test` or `--audit` run that finds the `tests` setting changed since the evidence was taken prints `The tests setting changed, so every result is out of date.` once, before it says what it selected
- RULE-111: After the commits of `--commit`, where git still lists a changed or untracked file outside `.purlin/`, the run prints `1 file is still not committed:` or `<n> files are still not committed:`, then up to 10 of them, each on its own line indented two spaces, then `  and <n> more` for the rest, then `Commit them, then run purlin:test --all --commit again: a sign-off needs results taken with nothing uncommitted.`; with none left it prints no such line
- PROOF-292 (RULE-108): A marked test is titled `adds two numbers`, and the suite's report holds the passing case `adds  two numbers`, with two spaces, in that file; the run exits 1 and prints `Evidence is missing: feat PROOF-1 at tests/feat.test.ts:1: its test ran, and the report names it differently. The title reads "adds two numbers" and the report reads "adds  two numbers". Write the title as the report reads, then run purlin:test.`
- PROOF-293 (RULE-108): In that same run no line holds `Check that its test ran and was not skipped`
- PROOF-294 (RULE-58): A project keeps its pytest settings, `pythonpath = ["."]`, in `pipeline/pyproject.toml`; its one marked test, in `pipeline/tests/`, imports a module that sits in `pipeline/`. `--all --test` exits 0 and the evidence lists the test's proof as `pass`
- PROOF-295 (RULE-58): A pytest suite's 160 marked test files have paths long enough that the command naming them all passes 30,000 characters; `--all --test` prints `The pytest suite has 160 test files, more than one command line holds, so it runs with no file list.`, the suite's command names no test file, and the evidence lists the proof as `pass`
- PROOF-296 (RULE-109): A suite's command waits for the file `go` before it writes its report; while it waits, the run's output already holds the line `Running slow: ` followed by that command with the report's path filled in, and the run finishes once `go` is written
- PROOF-297 (RULE-109): A shell suite whose command is `bash {files}` holds two marked scripts; `--all --test` prints `Running shell: bash {files}, once for each of 2 files`
- PROOF-298 (RULE-110): In a git checkout of `login` and `export` whose evidence `--all --test --commit` committed, the pytest command in the `tests` setting gains ` -v`; `--test` with no feature named prints `The tests setting changed, so every result is out of date.` exactly once, before the line that begins `Selected 2 of 2 features`
- PROOF-299 (RULE-111): In a git checkout where the spec `feat` and `src/other.py` are both edited, `--all --test --commit` prints `1 file is still not committed:`, then `  src/other.py`, then `Commit them, then run purlin:test --all --commit again: a sign-off needs results taken with nothing uncommitted.`, after `Evidence committed.`
- PROOF-300 (RULE-111): In a git checkout where 12 tracked files, `notes/n01.txt` to `notes/n12.txt`, are edited, `--all --test --commit` prints `12 files are still not committed:`, then `  notes/n01.txt` to `  notes/n10.txt`, then `  and 2 more`
- PROOF-301 (RULE-111): In a git checkout where only the spec `feat` is edited, `--all --test --commit` prints no line holding `still not committed`
- PROOF-94, PROOF-95, PROOF-193 and PROOF-98 reworded: each named `Running the <suite> suite.` and now names a line that begins `Running <suite>: `; each test changed on its kept line.

`specs/run/evidence_writer.md`: `Highest-Rule` 33, unchanged; `Highest-Proof` 98 to 99.

- RULE-19 reworded: after the subject, "or, over 5 features, `purlin: specs, tests and settings for <n> features` with the features in the body, one per line".
- PROOF-99 (RULE-19): In a git checkout where the specs `f1` to `f6` were edited and not committed, a `--all --test --commit` run makes a commit whose subject is `purlin: specs, tests and settings for 6 features` and whose body is the six lines `f1` to `f6`

`specs/mcp/states.md`: `Highest-Rule` 128 to 130, `Highest-Proof` 303 to 307.

- RULE-129: The status of a project Purlin 0.9.5 set up, while its upgrade is pending, is three lines and nothing else, from the status command and from the `sync_status` tool alike: its first line, `This project was set up by Purlin 0.9.5. Nothing here counts until it is brought to <version>.` and `→ Run: purlin:init --update`
- RULE-130: The status prints `The tests setting changed, so every result is out of date.` once, under the table, where the `tests` setting changed since the evidence was taken and nothing else in a feature's tests did
- PROOF-304 (RULE-129): A project holds one spec and the settings file Purlin 0.9.5 wrote, with no `tests` key; the status command prints exactly `Purlin status: <project>, plugin <version>`, `This project was set up by Purlin 0.9.5. Nothing here counts until it is brought to <version>.` and `→ Run: purlin:init --update`
- PROOF-305 (RULE-129): For that same project the `sync_status` tool answers those same three lines and nothing else
- PROOF-306 (RULE-130): In a git checkout of `login` and `export` whose evidence `--all --test --commit` committed, the pytest command in the `tests` setting gains ` -v`; the status holds the line `The tests setting changed, so every result is out of date.` exactly once
- PROOF-307 (RULE-130): In that checkout with the setting as it was and login's test file edited instead, the status holds no line reading `The tests setting changed, so every result is out of date.`

## Seen failing first

Each new test was run against `main`'s `scripts/` (the lane's stashed) and failed there:
`reports` PROOF-126 to 129; `run_script` PROOF-292 to 300; `evidence_writer` PROOF-99; `states`
PROOF-304 to 306. Two pass on `main` and are the other direction of their rule: `run_script`
PROOF-301 and `states` PROOF-307, each saying a line is absent.

## On the copy of the real project

A `cp -Rc` copy of the upgraded project, with five hand repairs undone: two titles with `\'`
back in `bus_chain.integration.test.ts`, three joined titles ending `+ ''` back in
`dev_proxy.test.ts`, the leading space back in `effect_calibration.integration.test.ts`, and
`-c pipeline/pyproject.toml` out of the pytest command. `--test --all`, no `--commit`.

| | `main`'s run script | this lane's |
|---|---|---|
| pytest | 13 files fail to collect, `No module named 'rgm'` | runs with its 13 marked files and passes |
| `Evidence is missing` | 108 markers | none |
| rules passing, of 476 | 368 | 470, and 472 on a rerun of three features |

The rules still failing are not this lane's faults. 2 rules have no test, as in the first
test's final log. The rest are tests that failed on a time limit while the machine's load
average was 9 to 11, the other lanes' sweeps running: `play_bar` RULE-12 (`a pause keeps its
place`), `project_workspace` RULE-8 (`timed out waiting`), and on the first run two of
`project_history`. `project_workspace` RULE-8 failed the same way under `main`'s run script
on the same copy, with no file list. The first test's final log reads 474 on a quiet machine;
this was not repeated on a quiet machine.

The run opened on `The tests setting changed, so every result is out of date.` and each suite's
`Running <suite>: <command>` line. The vitest line is 4,310 characters, 81 files.
On a copy of the original 0.9.5 project the status is three lines, where it was 162.
`--commit` was not run on the copy, so items 14 and 18 were seen only in the sample projects.

## Lines chosen

- `<feature> <id> at <file>:<line>: its test ran, and the report names it differently. The title reads "<title>" and the report reads "<name>". Write the title as the report reads, then run purlin:test.` after `Evidence is missing: `.
- `1 more marker whose test ran is named differently in the report. Correct those above, then run purlin:test.` and `<n> more markers whose tests ran are named differently in the report. Correct those above, then run purlin:test.`
- `The <suite> suite has <n> test files, more than one command line holds, so it runs with no file list.`
- `Running <suite>: <its command>, once for each of <n> files` and `Running <suite>: <its command>, for 1 file`, for a suite whose command runs once per file.
- `1 file is still not committed:` and `<n> files are still not committed:`, above the paths; `  and <n> more`.
- `purlin: specs, tests and settings for <n> features`, the body one feature per line.

## Calls the plan did not make

1. **The three-line status needs both signs.** The plan says to print it while
   `update.pending` is not empty. `pending` is also not empty for any project with no
   `.purlin/evidence/README.md` or without the `.gitignore` lines, which is every project the
   tests build by hand: built that way, 75 tests failed, in files of all three lanes and of
   none, and the sentence `This project was set up by Purlin 0.9.5` was false for them. So the
   three lines print where `pending` is not empty and the settings hold no `tests` key, the
   sign a test run already refuses on. Any other pending project keeps its table and
   `→ Run: purlin:init --update`, as today. A 0.9.5 project that applied the `config`
   migration and declined another reads that way too. The owner may want `pending` alone; the
   change is one condition in `status.sync_status`, and the test projects would then need the
   README and the ignore lines.
2. `set_up_by_095` moved to `scripts/mcp/purlin/project.py`, one home for the run and the
   status; the run script's function calls it.
3. The dashboard's data file is still refreshed for such a project, so lane `dashboard` sees
   no change.
4. `--all` no longer runs a test file that carries no marker, and starts no suite whose files
   carry none. Such a test's failure no longer fails a `--all` run.
5. The 30,000 limit applies to every run and every system, so the same project runs the same
   way everywhere.
6. The unreadable-title line names the test's line; the differently-named line names the
   marker's line, as every other `Evidence is missing` entry does.
7. A call with a variable first argument counts as a test only where a second argument
   follows, so a helper call such as `test(value)` declares none.
8. The plan's uncommitted list says tracked files; untracked files are listed too, since they
   make the results count as taken with uncommitted changes.
9. After a run of some features the status at its end can repeat the `tests setting` line,
   for the features not run. In a run of every feature it prints once.
10. `setting_changed` says nothing where the evidence was taken over a setting no commit held.
11. `references/formats/marker_format.md` changed in the same commit as the code;
    `> Format-Version:` is not bumped, since no field or structure changed.
12. One commit holds all eight findings: they share `purlin_run.py`, `reports.py` and the two
    specs line by line.

## Left, or waiting on another lane

- `dev/test_ai_audit.py` lines 1738, 1748 and 1759 assert that `Running the pytest suite.` is
  absent. They pass and now show nothing. The file is no lane's; each should read
  `not any(line.startswith('Running pytest: ') for line in lines)`.
- `docs/upgrading.md`, lane `update`'s, says `purlin:status` "carries" the arrow line while a
  migration is pending. For a 0.9.5 project it is now the whole status after the first line.
- Lane `update` checks its rewrite with this reader. After the merge a title such as
  `'x ' + ''` reads as `x` and ties, and a marker above an unreadable title is in
  `FileMarkers.untied` and `FileMarkers.unreadable`.
- Not run: the full `bash dev/run_tests.sh`, `dev/windows_run.py`, and the real project on a
  quiet machine.
