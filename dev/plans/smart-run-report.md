# Decision 129, lane `smart-run`: the report

Branch `lane/smart-run`, one commit of work on `main` at `1ce6c2ad7`, then this report.
Acceptance: `bash dev/run_tests.sh` ended `1268 passed, 9 skipped`,
`Suites: 4 passed, 0 failed`. Nothing is pushed, tagged or signed.

## What was built

**`purlin:test --all` runs what changed and carries the rest forward.**
`fingerprint.carry_plan` decides, per feature, whether this machine runs it and which
sections are carried. `purlin_run.py` runs the first set, then `carry_forward` records each
carried section again on the run's commit through `evidence.write_carried`.

A feature runs here when:

- it is an anchor;
- its `local` evidence holds no section for this system;
- that section was taken over another spec, code or tests;
- that section was taken while files were changed and not committed;
- that section holds, for a proof this system can run, a result that is not a pass;
- an untracked file sits under its scope or beside its tests;
- its spec names no files.

Every other feature is carried: no test of it starts.

**A carried section.** Its `commit` becomes the run's own. Each proof entry holds `carried`:
the `commit`, `at`, `machine` and `email` of the run that took the result. An entry already
carried keeps what it names, so a second carry still names the first run. The section's `at`,
`runner`, `email`, `machine`, `dirty`, `fingerprint` and `rules` stay as they were. A section
that already counts on the run's commit is left byte for byte as it was.

**Another system's section.** Every section of a feature's two files is carried by the same
test, fingerprint equal and `dirty` false, whether or not the feature runs here. A file under
`ci/` that the run wrote goes into the evidence commit with the `local/` files.

**`--clean`.** `purlin_run.py --clean --test` runs every test of every feature and carries
nothing. It is refused beside `--audit`, `--ci` and `--feature`.

**The sign-off.** `same_code` no longer excludes a carried result. A result counts where its
section names the commit being signed, or one from which only `.purlin/` changed. A project
tested in part is refused as before. The package's results and runs say what was carried.

**Where a person reads it.** The run's `Ran` line; the spec's view of `purlin:status`; the
rule page of the dashboard; the sign-off's opening lines and each hand check's stop.

**One field, one word.** The evidence field `kept` is now `carried`. A slow result a plain run
keeps is the same thing as a result `--all` carries, so both use the one field and both count
at a sign-off.

## Rules and proofs, word for word

### `specs/dashboard/purlin_report.md`

`Highest-Rule` 85 to 86, `Highest-Proof` 282 to 286.

Added: RULE-86: On a rule's screen a proof whose results a run carried forward shows, straight after its result, the row `Carried from`, holding for each operating system the system's short word, `Win`, `Mac` or `Lin`, and the first 7 characters of the commit the results were taken at, each pair on one line at every width from 390 to 1500 pixels and at 7 to 1 contrast in both themes; a proof whose own run took its results shows no such row, and a rule with no proof shows the row after `Last run`

Added: PROOF-283 (RULE-86): Open the regulated sample's `login RULE-1` with its proof's results carried from `a1b2c3d` on Linux/Unix and `9b2e7c4` on Windows, at 1500, 1280, 1024, 768 and 390 pixels wide; at each width the proof's row after `Result` is `Carried from`, reading `Lin a1b2c3d Win 9b2e7c4`, each pair on 1 line

Added: PROOF-284 (RULE-86): Open the regulated sample's `login RULE-1` with no result of its proof carried; the proof shows no row labelled `Carried from`

Added: PROOF-285 (RULE-86): Open that rule with its proof's results carried from `a1b2c3d` on Linux/Unix and `9b2e7c4` on Windows, in the dark theme and in the light; `Carried from`, `Lin`, `a1b2c3d`, `Win` and `9b2e7c4` each measure at least 7 to 1 against the ground under them

Added: PROOF-286 (RULE-86): Open the solo sample with no proof lines, where the tests marked for `login RULE-1` were carried from `a1b2c3d` on macOS; the rule's last two rows are `Last run` and `Carried from`, the second reading `Mac a1b2c3d`


### `specs/export/package.md`

`Highest-Rule` 37 to 38, `Highest-Proof` 83 to 85.

Reworded: RULE-32: The package carries `runs`, one entry per group of counted results sharing a source, a system, who took them, a machine and whether they were carried forward, local first and then by system, each naming `by`, the email of the run that took them, `machine`, `os`, `source`, `at`, `commit`, the count of `rules` and `carried`; a group of carried results names the person, machine, time and commit of the newest run they were taken in

Reworded: RULE-33: Each result carries `same_code`, true when every commit from the one its section names to the package's `commit` changes only files under `.purlin/` and leaves the `tests` setting as it was; a result a run carried forward into such a section reads true

Added: RULE-38: Each result carries `carried`, one entry per proof of the rule whose result the section's own run did not take, by proof number, naming the `proof` and the `commit`, `at`, `machine` and `email` of the run that took it; `[]` where the section's own run took every result

Reworded: PROOF-65 (RULE-32): `dana.dev@labconnect.example` runs every test on `dana-laptop`, a Linux machine, and commits them; the package's `runs` holds one entry reading `by` `dana.dev@labconnect.example`, `machine` `dana-laptop`, `os` `linux`, `source` `local`, the run's time and commit, `rules` `2` and `carried` `false`

Added: PROOF-85 (RULE-32): Dana's run records three rules' results, of which `feat RULE-2`'s was taken by `pat.product@labconnect.example` on `pat-laptop` at the commit `<c>` and carried forward; `runs` holds Dana's entry with `rules` `3` and `carried` `false`, then one reading `by` Pat's address, `machine` `pat-laptop`, `commit` `<c>`, `rules` `1` and `carried` `true`

Reworded: PROOF-68 (RULE-33): The tests run and are committed at `<c>`, then a commit changes `README.md`, which no spec covers; `purlin:sign` prints only `No sign-off: these results are not recorded on this version of the code, <sha7>: login on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.`

Reworded: PROOF-77 (RULE-33): The tests run and are committed at `<c>`, then a commit changes the `run` command of the `tests` setting in `.purlin/config.json`; `purlin:sign` prints only one line beginning `No sign-off: these results are not recorded on this version of the code` and exits 1

Reworded: PROOF-78 (RULE-33): `login`'s committed results name a commit on another branch, which `HEAD` does not descend from, the two trees holding the same files; `purlin:sign` prints only one line beginning `No sign-off: these results are not recorded on this version of the code` and exits 1

Reworded: PROOF-79 (RULE-33): `feat`'s section, recorded on `HEAD`'s code, lists its slow `PROOF-2` as `pass` with `carried` naming the earlier commit `<c>`, and every other result was taken on `HEAD`'s code; `purlin:sign --show` exits 0 and prints no line beginning `No sign-off`

Added: PROOF-84 (RULE-38): `feat`'s section, recorded on `HEAD`'s code, lists `PROOF-2` as carried from the commit `<c>`, taken at `2026-09-13T11:00:00Z` on `pat-laptop` by `pat.product@labconnect.example`; in the signed package `RULE-2`'s one result reads `carried` as that one entry for `PROOF-2`, `same_code` `true` and a `commit` other than `<c>`, and `RULE-1`'s reads `carried` `[]`


### `specs/mcp/server.md`

`Highest-Rule` 44 to 45, `Highest-Proof` 185 to 188.

Added: RULE-45: Under the lines of a proof whose results a run carried forward, one line per operating system reads `      carried forward from <sha7> on <System>`, the first 7 characters of the commit the results were taken at and the system as `Linux/Unix`, `macOS` or `Windows`; a rule no proof line names gets the line under its own tests, and a proof whose own run took its results gets none

Added: PROOF-186 (RULE-45): `PROOF-1`'s one result, in this machine's current section, is marked carried from the commit `a1b2c3d4...`; the lines under `  RULE-1  passed  not audited` are `    PROOF-1  passed  tests/test_login.py::test_proof_1` and `      carried forward from a1b2c3d on <System>`, the system as `Linux/Unix`, `macOS` or `Windows`

Added: PROOF-187 (RULE-45): `PROOF-1`'s test passed in a current section this machine's own run took; the spec's view holds no line with `carried forward`

Added: PROOF-188 (RULE-45): `RULE-1` has no proof, and the one test marked with its id holds a result carried from the commit `a1b2c3d4...`; the view's last two lines are `    RULE-1  tests/test_login.py::test_rule_1` and `      carried forward from a1b2c3d on <System>`


### `specs/mcp/states.md`

`Highest-Rule` 137 to 138, `Highest-Proof` 325 to 326.

Added: RULE-138: Each proof of a rule entry carries `carried`, `{system: commit}`: for each operating system whose current section holds every result of the proof as carried forward, the full commit the newest of them was taken at; a system whose own run took a result is left out, and a rule with no proof carries the same for the tests marked with its own id

Added: PROOF-326 (RULE-138): A current `linux` section passes both rules, and its result for `PROOF-1` is marked carried from the commit `<c>`; `RULE-1`'s proof reads `carried` `{"linux": "<c>"}` and `RULE-2`'s proof reads `carried` `{}`


### `specs/mcp/summary.md`

`Highest-Rule` and `Highest-Proof` unchanged.

Reworded: RULE-27: Where the last line would name `purlin:sign` and the evidence holds, for some rule, a result that is not recorded on this version of the code, one whose section names a commit after which a commit changes a path outside `.purlin/`, the last line reads `Every rule passes its tests on the committed evidence. Before a sign-off, run <command>: a sign-off counts only results recorded on this version of the code.`; `<command>` is `purlin:test --all --commit` for results taken on this machine and `purlin:test on <systems>` for a project's own run on another system, joined by ` and ` where both apply. `purlin:sign` refuses that project with `No sign-off: these results are not recorded on this version of the code`

Reworded: RULE-28: Where every result is recorded on this version of the code and one was taken while files were changed and not committed, the last line reads `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results taken with nothing uncommitted.`; `purlin:sign` refuses that project with `No sign-off: these results were taken while files were changed and not committed`

Reworded: PROOF-64 (RULE-27): Two rules pass their tests on committed evidence; a later commit adds `notes.txt`. The status reads `Tests: met` and ends on `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results recorded on this version of the code.`, and `purlin:sign`'s refusal for the same project opens `No sign-off: these results are not recorded on this version of the code` and ends `Run purlin:test --all --commit, then purlin:sign.`

Reworded: PROOF-66 (RULE-27): Two rules pass on evidence recorded at HEAD, where the result of `PROOF-2` is marked `carried` from an earlier run; the status reads `Tests: met` and ends on `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`, and `purlin:sign`'s refusal for the same project does not open `No sign-off: these results are not recorded on this version of the code`

Reworded: PROOF-67 (RULE-27): Two rules hold passing results from a project's own run on Windows, then a commit adds `notes.txt`, then this machine's passing results are committed; the status reads `Tests: met` and ends on `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test on Windows: a sign-off counts only results recorded on this version of the code.`, and `purlin:sign`'s refusal ends `Run purlin:test on Windows, then purlin:sign.`; on a Windows machine the other system is Linux/Unix


### `specs/review/signatures.md`

`Highest-Rule` 140 to 142, `Highest-Proof` 289 to 293.

Reworded: RULE-102: The command refuses, with one line naming the cause and the command to run, nothing written and exit 1, when tracked files are changed and not committed, evidence is written and not committed, a result is not recorded on this version of the code, a result was taken while files were changed and not committed, or a rule does not pass

Added: RULE-141: For results a run carried forward, the walk's opening line reads `Carried forward from earlier runs by <who> on <machine>, the newest at <time> on <sha7>: <n> rules on <System>.`, naming who took them, on which machine, and the time and commit of the newest run among them

Added: RULE-142: At a hand check's stop, a system's result line ends `; <PROOF-N> carried forward from <sha7>` for the proofs whose result a run carried forward, the proofs of one commit together, joined by `, `

Reworded: PROOF-226 (RULE-102): `audit`'s Windows results, under the source `ci`, were taken before a commit that changed `src/audit.py`, and every other result was taken at `HEAD`; the walk prints only `No sign-off: these results are not recorded on this version of the code, <sha7>: audit on Windows. Run purlin:test on Windows, then purlin:sign.` and exits 1

Added: PROOF-292 (RULE-102): `login` and `export` pass on committed evidence; `README.md`, which no spec covers, is changed and committed; `purlin:test --all --commit` carries both forward; `purlin:sign --show` exits 0, prints no line beginning `No sign-off`, and its first line begins `Carried forward from earlier runs by`

Added: PROOF-293 (RULE-102): In that project, after the change to `README.md`, `purlin:test login --commit` runs in place of the run over every feature; `purlin:sign --show` prints only `No sign-off: these results are not recorded on this version of the code, <sha7>: export on <System>. Run purlin:test --all --commit, then purlin:sign.` and exits 1

Added: PROOF-290 (RULE-141): Two rules' results were taken by `pat.product@labconnect.example` on `pat-laptop` at 08:05 UTC on 2026-09-30 at the commit `<c>`, and a later run carried them forward onto the commit being signed; the walk's first line reads `Carried forward from earlier runs by pat.product@labconnect.example on pat-laptop, the newest at 2026-09-30 08:05 UTC on <sha7 of c>: 2 rules on Linux/Unix.`, and its second `Signing <version> at <sha7>.`

Added: PROOF-291 (RULE-142): `login RULE-2`, a hand check, has `PROOF-3`, whose result a run on `dana-laptop` carried forward from the commit `<c>`; the first line under `Results` at its stop reads `  Linux/Unix: passed on dana-laptop; PROOF-3 carried forward from <sha7 of c>`


### `specs/run/evidence_writer.md`

`Highest-Rule` and `Highest-Proof` unchanged.

Reworded: RULE-19: With `--commit`, before the results, the run commits the specs of the features it ran, every feature's under `--all`, the test files carrying their markers and `.purlin/config.json`, where any of them changed, under the person's own git identity with the subject `purlin: specs, tests and settings for <feature>[, <feature>…]`, or, over 5 features, `purlin: specs, tests and settings for <n> features` with the features in the body, one per line, and prints `Committed <sha7>, the work these results describe:` then each file that commit changed on a line of its own, indented two spaces; where none changed it makes no commit and prints no such line

Reworded: RULE-32: With `--commit` the run's second commit carries the files under `.purlin/evidence/local/`, any evidence file the run removed and any file under `.purlin/evidence/ci/` in which it carried a section forward, under the person's own git identity, with the subject `purlin: evidence at <sha7>`, where `<sha7>` names the run's first commit, or HEAD when that made none, and prints `Evidence committed.`; where nothing is new it prints `Evidence unchanged.` and makes no commit; it never pushes or prints a push command

Reworded: PROOF-92 (RULE-31): After `--all --test --commit`, a change to `README.md`, which no scope names, is committed; `--clean --test` then writes `feat`'s section with the new HEAD as its `commit` and a new `at`, its results and fingerprint as they were

Reworded: PROOF-85 (RULE-23): Two branches each commit a section for this system into `feat`'s evidence file, one naming the machine `build-8` and one `build-9`; their merge conflicts and is resolved to the `build-9` side; a `--feature feat --test` run then rewrites that section, which names this machine


### `specs/run/run_script.md`

`Highest-Rule` 113 to 118, `Highest-Proof` 307 to 322.

Reworded: RULE-101: Before it runs anything, a run with no feature named and no `--all` prints `Selected <n> of <m> features:` with each feature's reasons, then `Skipped <k> features whose spec, code and tests match their evidence:` with their names and `purlin:test --clean runs them too.`, then one line for each untracked file that selected a feature, saying its content is not part of the evidence until it is added to git

Reworded: RULE-100: When such a run selects nothing it prints `Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --clean runs them anyway.`, runs no test, writes no evidence, ends on the status, and exits 1 where a rule's tests fail in the evidence it stands on and 0 otherwise; with `--commit` it still commits the specs, marked tests and settings that changed, then the evidence an earlier run wrote

Reworded: RULE-104: `--test` and `--audit` without `--all` never start a test whose every comment names a proof tagged `@slow`, whichever features they run, and `--all`, `--clean` and `--ci` start it like any other test of a feature they run. The run prints `Left out 1 slow proof: <feature PROOF-N>. purlin:test --all runs it when it is due.` or `Left out <n> slow proofs: <each>. purlin:test --all runs them when they are due.`, lists each as `not run` in the evidence with its test named, and never names it under `Evidence is missing`

Reworded: RULE-106: A run that leaves a slow proof's test out keeps the result the section it replaces holds for that proof where that section was taken over the same spec, code and tests, and marks it `carried` with the `commit`, `at`, `machine` and `email` of the run that took it; where it was taken over others, the proof reads `not run`

Reworded: RULE-59: `--clean` runs every feature whatever its evidence says, and `--ci` with no feature named runs every feature that has a proof tagged for this machine's system

Added: RULE-114: Under `--test` and `--audit`, `--all` runs a feature when its own evidence holds no section for this operating system, when that section was taken over another spec, code or tests or while files were changed and not committed, when it holds a result that is not a pass for a proof this system can run, when an untracked file git does not ignore sits under its `> Scope:` or beside one of its marker files, when its spec names no files, and when it is an anchor; it starts no test of any other feature

Added: RULE-115: A feature `--all` does not run is carried forward: where a commit since the one its section names changes a file outside `.purlin/`, the section is written again with the run's own `commit`, each of its results marked `carried` with the `commit`, `at`, `machine` and `email` of the run that took it, a result already marked keeping what it names, and its `at`, `machine`, `email`, `runner`, `dirty`, `fingerprint` and `rules` as they were; otherwise its file is left byte for byte as it was

Added: RULE-116: `--all` carries forward the same way each section another system or another source wrote, where it was taken over the spec, code and tests as they are now with nothing uncommitted, whether or not the feature runs here, leaves any other such section as it was, and `--commit` commits each file it wrote under `.purlin/evidence/ci/` with the rest

Added: RULE-117: A run that carried features forward ends its `Ran` line ` and carried <n> forward. purlin:test --clean runs every test.` in place of the full stop, and prints `Carried the <System> results of <n> features forward.`, `1 feature` for one, for each other system it carried a section of; a run that carried none prints neither

Added: RULE-118: `--clean` goes with `--test`, runs every test of every feature and carries nothing forward, so no result it writes holds `carried`; beside `--audit` or `--ci` it is refused with `purlin: --clean goes with --test.`, and beside `--feature` with `purlin: name features or --clean, not both.`, each exiting 2 with the usage line

Reworded: RULE-17: `--test` and `--audit` take no result into `.purlin/evidence/ci/`: only `--ci` writes a section there, and all another run changes in that folder is a section it carries forward as RULE-116 says

Reworded: PROOF-91 (RULE-101): `login` and `export` are current; `invoice`, committed with a passing test, was never run; the next `--test` exits 0, selects `invoice` alone, reason `no run on <System> yet`, prints `Skipped 2 features whose spec, code and tests match their evidence: export, login. purlin:test --clean runs them too.` and `Ran pytest on 1 feature.`, the report holding invoice's test alone

Reworded: PROOF-275 (RULE-104): `feat`'s PROOF-2 is tagged `@slow` and its pytest test writes the file `started`; `--feature feat --test` exits 0, prints `Left out 1 slow proof: feat PROOF-2. purlin:test --all runs it when it is due.` and no `Evidence is missing`, writes no `started` file, and the evidence lists PROOF-2 as `not run` under `tests/test_feat.py::test_slow`

Reworded: PROOF-281 (RULE-106): In a git checkout, `--all --test --commit` passes `feat`'s slow `PROOF-2` at the commit `<c>`; `README.md`, which no scope names, is changed and committed; `--feature feat --test --commit` runs; the evidence lists `PROOF-2` as `pass` with `carried` naming the commit `<c>`, and the section's own `commit` is the new one

Reworded: PROOF-286 (RULE-106): In a git checkout whose evidence lists `feat`'s slow `PROOF-2` as `pass` with `carried`, `--clean --test --commit` runs with nothing changed since; the slow test is started, and the evidence lists `PROOF-2` as `pass` and holds no `carried`

Reworded: PROOF-98 (RULE-59): In a git checkout of `login` and `export` with committed evidence and nothing changed, `--clean --test` exits 0, prints no `Selected` line and no `Nothing to run` line, prints a line that begins `Running pytest: `, and the suite's report holds both tests, `test_export` and `test_login`

Added: PROOF-308 (RULE-114): In a git checkout of `login` and `export`, each scoping one source file, whose evidence `--test --commit` committed, `src/login.py` is changed and committed; `--all --test --commit` exits 0, and the suite's report holds `test_login` alone

Added: PROOF-309 (RULE-114): In that checkout `export`'s test is changed to fail and `--all --test --commit` exits 1; run again with nothing changed, it exits 1 and the suite's report holds `test_export` alone

Added: PROOF-310 (RULE-114): In a git checkout of the feature `export` and the anchor `shared`, each with one passing test, `--all --test --commit` runs twice with nothing changed between; the second run's report holds `test_shared` alone

Added: PROOF-311 (RULE-114): `--feature export --test` runs while `notes.txt` is written and not committed, and the note and the evidence are then committed; `--all --test --commit` then runs `test_export` alone, and `export`'s section reads `dirty` `false`

Added: PROOF-312 (RULE-115): In a checkout of `login` and `export` whose evidence was committed at `<c>`, `README.md`, which no scope names, is changed and committed; `--all --test --commit` starts no suite; `export`'s section names the new commit, its one result holds `carried` with `<c>` and the first run's `at`, `machine` and `email`, and the section's `at`, `machine`, `email`, `runner`, `dirty`, `fingerprint` and `rules` are as they were

Added: PROOF-313 (RULE-115): After that run `README.md` is changed and committed again and `--all --test --commit` runs again; `export`'s section names the newest commit, and its result's `carried` still names `<c>`

Added: PROOF-314 (RULE-115): In a checkout of `login` and `export` with nothing committed since their evidence, `--all --test --commit` prints `Evidence unchanged.` and no line beginning `Evidence written`, and leaves both evidence files byte for byte as they were

Added: PROOF-315 (RULE-116): `export`'s evidence under `ci` holds a section for another system, taken on `other-box` by `ci@example.com` at `<c>` over the spec, code and tests as they are; `README.md` is changed and committed; after `--all --test --commit` that section names the new commit, its `machine` reads `other-box`, its result's `carried` names `<c>`, `other-box` and `ci@example.com`, and git lists no evidence file as changed

Added: PROOF-316 (RULE-116): That section, taken over another spec, code and tests, is byte for byte as it was after `README.md` is changed and committed and `--all --test --commit` runs, and the run prints no line beginning `Carried the`

Added: PROOF-317 (RULE-117): In a checkout of `login` and `export` with committed evidence, `src/login.py` is changed and committed; `--all --test --commit` prints `Ran pytest on 1 feature and carried 1 forward. purlin:test --clean runs every test.`

Added: PROOF-318 (RULE-117): In that checkout with `README.md` changed and committed in place of `src/login.py`, `--all --test --commit` prints `Ran nothing on 0 features and carried 2 forward. purlin:test --clean runs every test.`

Added: PROOF-322 (RULE-117): `export`'s evidence under `ci` holds a section for another system over the spec, code and tests as they are; `README.md` is changed and committed; `--all --test --commit` prints `Carried the <System> results of 1 feature forward.`, the system as `Windows`, `macOS` or `Linux/Unix`

Added: PROOF-319 (RULE-118): In a checkout where `--all --test --commit` carried `login` and `export` forward, `--clean --test --commit` exits 0, the suite's report holds `test_export` and `test_login`, it prints `Ran pytest on 2 features.`, and no result in either feature's section holds `carried`

Added: PROOF-320 (RULE-118): Started as `--clean --feature feat --test`, the run exits 2 and prints `purlin: name features or --clean, not both.`, then the usage line

Added: PROOF-321 (RULE-118): Started as `--clean --ci`, the run exits 2 and prints `purlin: --clean goes with --test.`, then the usage line

## What was seen failing first

- `dev/test_run_script.py`, `TestARunOverEveryFeatureCarriesForward`: 14 tests written before
  any code. 12 failed. 2 passed at once, since they hold on the code as it was: `PROOF-314`
  (nothing committed since, files unchanged) and `PROOF-316` (another system's section over
  other code is left alone).
- `dev/test_export.py`: `PROOF-65`, `PROOF-84` and `PROOF-85` failed. `PROOF-79`, rewritten
  from a refusal to a pass, passed at once: its fixture writes `carried`, which the old code
  did not read.
- `dev/test_signatures.py` `PROOF-290` and `PROOF-291`, and `dev/test_mcp_server.py`
  `PROOF-186` and `PROOF-188`: the code was written first. The four were then run against
  `sign.py`, `package.py`, `purlin_status.py` and `payload.py` as `main` holds them, and all
  four failed. `PROOF-187`, a result with no such line, passes on both.
- `dev/test_purlin_report.py` `PROOF-283` failed with `KeyError: 'Carried from'` before the
  row was drawn. `PROOF-284` passes on both. `PROOF-285` and `PROOF-286` were written after
  the row and were not seen failing.
- `dev/test_states.py` `PROOF-326` and the two tests of `signatures` `PROOF-292` and
  `PROOF-293` were written after the code and were not seen failing.
- Six tests of the old behaviour failed after the change and were brought to what is:
  `run_script` `PROOF-91`, `PROOF-98`, `PROOF-275`, `PROOF-281`, `PROOF-286`, the
  `Nothing to run` line's test, and `evidence_writer` `PROOF-85` and `PROOF-92`.

## Format versions

- `references/formats/evidence_format.md`: 14 to 15. `kept` becomes `carried`; a new section,
  "Carried forward"; `ci/` may be written by a `--all` run that carries a section.
- `references/formats/package_format.md`: 14 to 15. Each result gains `carried`; each run
  gains `carried`; `same_code` no longer excludes a carried result.
- The schema strings, `purlin-evidence/2` and `purlin-package/4`, are unchanged.

## Every line a person reads that this lane chose

```
Ran pytest on 3 features and carried 62 forward. purlin:test --clean runs every test.
Ran nothing on 0 features and carried 2 forward. purlin:test --clean runs every test.
Carried the Windows results of 9 features forward.
Skipped 2 features whose spec, code and tests match their evidence: export, login. purlin:test --clean runs them too.
Nothing to run: every feature's spec, code and tests match its evidence. purlin:test --clean runs them anyway.
Left out 1 slow proof: feat PROOF-2. purlin:test --all runs it when it is due.
Left out 2 slow proofs: feat PROOF-2, feat PROOF-3. purlin:test --all runs them when they are due.
purlin: --clean goes with --test.
purlin: name features or --clean, not both.
No sign-off: these results are not recorded on this version of the code, 1cf829e: login on macOS. Run purlin:test --all --commit, then purlin:sign.
Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results recorded on this version of the code.
Carried forward from earlier runs by dana.dev@labconnect.example on dana-laptop, the newest at 2026-09-30 08:05 UTC on 9b2e7c4: 12 rules on Linux/Unix.
  Linux/Unix: passed on dana-laptop; PROOF-3 carried forward from 9b2e7c4
      carried forward from 4f1c2ab on macOS
```

The last is the line under a proof in `purlin:status <name>`. On the dashboard's rule page the
row is labelled `Carried from` and reads `Mac 4f1c2ab`, one pair per system, each on one line.
The usage line gains `purlin_run.py --clean --test [--commit] [--write-tests] [--arm-timeout
SECONDS] [--project-root DIR]`. The syntax in `references/purlin_commands.md` reads
`purlin:test [feature ...] [--all | --clean] [--commit] [--arm-timeout <seconds>]`.

## The demo on this repository

On `demo/smart-run`, cut from the lane head, one line was added to `dev/plans/handoff.md` and
committed as `ee16c74`. Then
`python3 scripts/run/purlin_run.py --test --all --commit --project-root .`:

- **Time:** 619 seconds, 10 minutes 19 seconds, exit 0. Two other lanes were running their
  own tests on the machine at the time.
- **Ran, 19 features:** `collaboration`, `evidence`, `evidence_writer`, `install`, `package`,
  `purlin_agent`, `purlin_docs`, `purlin_output`, `purlin_report`, `purlin_version`,
  `run_script`, `schema_spec_format`, `security_no_dangerous_patterns`, `server`,
  `signatures`, `skill_sign`, `skill_test`, `states`, `summary`. One is the anchor; the rest
  cover files this lane changed or the note.
- **Carried, 20 features:** `ai_audit`, `config_engine`, `drift`, `plain_checks`,
  `planted_bug`, `renumber`, `reports`, `scaffold`, `skill_anchor`, `skill_audit`,
  `skill_build`, `skill_drift`, `skill_init`, `skill_spec`, `skill_spec_from_code`,
  `skill_status`, `specs`, `update`, `upstream`, `windows_run`.
- **Windows sections carried, 5:** `ai_audit`, `config_engine`, `scaffold`, `update`,
  `upstream`, each from `6832a12` on `runnervmfi6oq`.
- **Windows sections not carried, 5:** `evidence`, `package`, `run_script`, `server`,
  `states`. This lane changed code each of them covers, so their fingerprints differ.
- **The lines it printed:**
  `Ran pytest on 19 features and carried 20 forward. purlin:test --clean runs every test.`,
  `8 proofs need Windows; this machine is macOS. Run purlin:test on Windows.`,
  `Carried the Windows results of 5 features forward.`,
  `Evidence written to .purlin/evidence/local/ for 39 features.`, `Evidence committed.`
- **The status it ended on:** `567 rules. 559 pass their tests.`, then
  `1 rule to test: purlin:test` and `7 rules to test on Windows: run purlin:test on Windows`.
  The one rule is `evidence RULE-32`, a Windows rule whose only result is the Windows section
  now out of date; the status words it as this machine's, as it did before this lane.
- **`python3 scripts/review/sign.py --show --project-root .` printed one line, exit 1:**
  `No sign-off: these results are not recorded on this version of the code, fa789eb: evidence, package, run_script, server, states on Windows. Run purlin:test on Windows, then purlin:sign.`
  It names only the five features whose Windows results this lane's code change put out of
  date. It names no carried feature and no result of this Mac.

The branch was then deleted. Nothing from it is on the lane.

## Calls this lane made that the prompt did not

1. **A result that is not a pass runs again.** Under `--all` a feature whose section here
   holds a failed, missing or not-run result for a proof this system can run is run, though
   its fingerprint matches. Otherwise a run made without its test tool on the path would be
   carried for ever.
2. **A section taken with uncommitted changes is not carried.** It runs again here; another
   system's is left as it was. Carrying it would keep the sign-off's `dirty` refusal standing
   with no run able to clear it.
3. **An untracked file under the scope, and a spec that names no files, run the feature**, as
   they select it in a plain run.
4. **A carried section keeps its own `at`, `machine`, `email` and `runner`.** Only `commit`
   moves. Where both sources hold a section for one system the newer `at` answers, and a new
   `at` on every carried section would change which one that is.
5. **`kept` is renamed `carried`** and a slow result a plain run keeps now counts at a
   sign-off, as decision 129's amendment of decision 121 says.
6. **`--clean` implies `--all`, goes with `--test` alone**, and is refused with `--feature`.
   `purlin:audit --all` carries as `purlin:test --all` does; there is no `purlin:audit --clean`.
7. **The words `taken on this version of the code` became `recorded on this version of the
   code`** in the refusal and in the status's last line, since a carried result counts and was
   not taken on this version.
8. **The three lines that named `--all` as the way to run everything were reworded**, above.
9. **The `Evidence written` line is left out** where a run wrote no file.
10. **A `--all --commit` run still commits every spec and marked test**, those of the features
    it carries too.
11. **The payload's schema stays 16.** `carried` is a new field on each proof and each rule,
    and the fixtures under `dev/fixtures/report/` are read without it.
12. **The package's `runs` put carried results in a group of their own**, named by who took
    them, with the time and commit of the newest run among them.
13. **`signatures` `PROOF-292` and `PROOF-293` have their tests in `dev/test_run_script.py`**,
    since they make a real run before the sign-off.
14. **`dev/test_install.py` ran in the demo.** `install` covers files this lane changed, so
    `--all` ran its slow proofs, which use the real `claude` program. No test this lane wrote
    reaches a model.

## What is left, and changes needed in files this lane does not own

Each is a line that still says the old thing.

- `references/purlin_commands.md:21`: `- \`purlin:test --all\` starts every test, slow ones
  included.` should read `- \`purlin:test --all\` covers every feature: it starts every test,
  slow ones included, of each feature that changed or does not pass and of every anchor, and
  carries every other feature's results forward.`
- `references/purlin_commands.md:134`: `purlin:test --all  The same, for every feature, slow
  proofs included` should read `The same, for every feature: what changed runs, the rest is
  carried forward`, with a line `purlin:test --clean  Run every test of every feature` after
  it. The `purlin:test` row of "What each command writes" should add `and, under --all, each
  section it carries forward, under \`ci/\` too`.
- `README.md:135`: the syntax should read `[--all | --clean]`.
- `references/glossary.md:114`: the entry `kept` should become `carried`: `a result an earlier
  run took and a later run recorded again on its own commit; it counts like any other and
  names the commit it was taken at`.
- `references/commit_conventions.md:163`: `taken on this version of the code` should read
  `recorded on this version of the code`.
- `agents/purlin.md:63`: `\`purlin:test --all --commit\` runs every test` should read `runs
  what changed and carries the rest forward`. Line 67: `refuses results not taken on` should
  read `refuses results not recorded on`.
- `docs/getting-started.md:198`: the line should end `purlin:test --clean runs them anyway.`
  Line 225: `\`purlin:test --all\` runs every feature, slow tests included` should read
  `covers every feature: it runs what changed and carries the rest forward`.
- `docs/specs-and-anchors.md:206`: `It runs everything, slow tests included.` should read `It
  runs what changed, slow tests included, and carries the rest forward.` Line 222: the line
  should end `purlin:test --all runs it when it is due.` Lines 238 to 240: `marked \`kept\``
  should read `marked \`carried\``, and `The status counts it. The sign-off does not: it asks
  for \`purlin:test --all --commit\`.` should read `It counts like any other result.`
- `skills/audit/SKILL.md:24`: `Run every feature` should read `Cover every feature as
  purlin:test --all does`.
- `RELEASE_NOTES.md` lines 21, 32, 33, 79 and 107 describe `--all`, `kept` and the slow
  result as they were.
- The deck, `dev/plans/deck/build_deck.py`, holds `taken on this version of the code` once.
- The status counts `evidence RULE-32`, a rule with a Windows proof alone, under
  `rules to test: purlin:test` when its Windows section is out of date. This lane did not
  change that.
- The Windows results of `evidence`, `package`, `run_script`, `server` and `states` need a
  Windows run after this lane merges.
