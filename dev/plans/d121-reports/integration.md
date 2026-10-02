# Decision 121: the integration report

Local, on `main`, from the base commit `fe512e267`. Nothing was pushed, tagged, signed or
audited, and no pull request was opened. One real `claude` call was made, by the install test
inside `purlin_run.py --test --all --commit`.

## 1. The merge

Each lane wrote only the files it owns and its report. Each was rebased onto the merged line,
its own test files were run, and it was merged fast-forward, in the plan's order: `evidence`,
`audit`, `signoff`, `surfaces`, `setup`, `words`. No conflict. The first sweep on the merged
line: 881 passed, 1 failed, 9 skipped. The one failure was the docstring line named below.

## 2. What the lanes handed to each other

| Item | What was done |
|---|---|
| The six sign-off tests in `dev/test_states.py` and `dev/test_summary.py` | Lane `surfaces`' version signs with the real walk and passes on the merged code. Kept as it is. |
| `package.audit_counts`, `sign.py` and five counts | Lane `signoff` built both to K4. Nothing to change. |
| `ai_audit.NO_AUDIT` and `is_read` | Lane `audit` built both. Nothing to change. |
| `payload.audit_summary` passing `spot-checked` and `no_bug` | Lane `surfaces` built it. Nothing to change. |
| `evidence_writer PROOF-54` | Lane `evidence`'s test answers `no break` in K3's shape and passes on lane `audit`'s code. |
| `dev/sign_project.py`, `dev/mcp_project.py`, `audit(...)` | The verdict `undecided` and `settled` are gone, since the format names neither. Both take `word`, `breaks` and `no_bug`, and write `breaks`. |
| The `_audit` docstring and the module docstring of `purlin_run.py` | Both read `while the audit ran`. |
| `evidence.audit_entry`'s docstring | No line opens with `from`. The import test passes. |
| The `tests` setting where a result holds | Added to `docs/running-and-evidence.md` twice, `references/evidence_and_signoff.md` and `references/commit_conventions.md`. |
| The package refusal in the command reference | `references/purlin_commands.md` names `the committed package not matching its fingerprint`. |
| `references/supported_frameworks.md` | The `dotnet` row and `In five cases`, with the NUnit bullet. |
| The planted bug as the third step | `references/review_criteria.md` and `planted_bug`'s Description. |
| `skill_audit`'s Description | `one model call per rule and one planted bug per proof`. |
| `stay not audited`, `while a bug was planted`, the old no-audit sentence, `git tag -s` in the sign skill, `--name` | Lane `words` had already changed each. The greps are empty. |

## 3. What the owner's decisions settle

Every rule and proof below is new or reworded by integration, word for word.

### 3a. A test that ends in an error is not a caught bug

The report reader marks a failed case its tool reports as an error. A normal run still reads
it as `fail`. The planted bug reads such a test as `not run`, with the reason.
Seen failing first: the result read `caught`.

- `planted_bug` RULE-3, reworded: A test that runs and fails with the bug in place reads `caught`; a test that is skipped, is not collected, runs past its limit or ends in an error its tool does not report as a failure there reads `not run`, which is neither caught nor survived, an error with the reason `the test ended in an error, not a failure`
- `planted_bug` PROOF-20 (RULE-3): A fixture every test of `tests/test_age.py` takes calls `minutes`, and the model answers `file: src/age.py`, `before:` `return 90`, `after:` `raise ValueError(stamp)`, so pytest reports the test of `PROOF-1` under `<error>`; the result reads `not run` with the reason `the test ended in an error, not a failure`, not `caught`
- `reports` RULE-39: A failed case its tool reports as an error and not as a failure, a `junit` case with an `error` child and no `failure` child or a `trx` result of `Error`, `Timeout` or `Aborted`, still fails its test, and is marked an error for the audit's planted bug to read apart
- `reports` PROOF-121 (RULE-39): The JUnit report written by running two Python tests, `test_fails` failing an assertion and `test_errors` whose fixture raises an error, reads both as `fail`; `test_errors` is marked an error and `test_fails` is not
- `reports` PROOF-122 (RULE-39): A `trx` document holds the results `E` `Error`, `T` `Timeout`, `B` `Aborted` and `F` `Failed`; all four read `fail`, `E`, `T` and `B` are marked an error, and `F` is not
- `ai_audit` PROOF-124 (RULE-33): The bug planted for `PROOF-2` makes its test end in an error and not a failure, so its result reads `not run`; the entry reads `spot-checked`, its `no_bug` exactly `A bug was planted for PROOF-2 and its test ended in an error, not a failure.`

A test whose own body raises is a failure to pytest, and still reads `caught`. Go has no
error result. An `exit` suite cannot tell the two apart, so a file that exits with any code
but 0 still reads `caught`.

### 3b. `purlin:anchor add --path`

Reproduced: with `--path` given as an absolute path, or as `../../../../../private_notes.md`,
`add` copied a spec-shaped file from outside the fetched source into `specs/_anchors/`.
Nothing was written outside the project, since the name is checked. Now refused before
anything is fetched; `sync` reads no path that leaves the source, a link included.

- `upstream` RULE-41: `add` and `sync` read no file outside the fetched source: `add` refuses a `--path` that is absolute or holds `..` before anything is fetched, and a path that leads out of the source by a link reads as not in the source
- `upstream` PROOF-63 (RULE-41): The folder around the project holds `private_notes.md`, a spec in Purlin's format, and the published anchor is added with `--path ../../../../../private_notes.md`, which names that file from the fetched source; it exits 2, the answer reads `error`, and `specs/_anchors/` stays empty
- `upstream` PROOF-64 (RULE-41): The published anchor is added with `--path` naming `private_notes.md` by its absolute path; it exits 2, the answer's error reads `not added. --path takes a path inside the source, with no .. and no leading /. Run purlin:anchor add <source> --path <path> --name private_notes.`, and `specs/_anchors/` stays empty

### 3c. A tag passed over stays out of the package

`payload.build_payload` takes `tag_warnings`, and the package is built with it false. The
warning stays on the status and the dashboard. Seen failing first: the two packages differed.

- `package` PROOF-81 (RULE-8): Two clones of one repository at the same commit each sign `2.1.0`, and the second also holds the tag `signed/9.9.9`, written by hand with `git tag`; the two committed packages are the same byte for byte, and neither's `warnings` names `signed/9.9.9`

### 3d. `evidence PROOF-86`

The test now holds the later entry in each file in turn. It fails under a reader that takes
the first file read and under one that takes the last.

- `evidence` PROOF-86 (RULE-16), reworded: Both files hold an entry for RULE-1 with the hashes `r`, `p`, `t` and `c`: `local` reads `strong` at `2026-09-01T00:00:00Z` and `ci` reads `weak` at `2026-09-02T00:00:00Z`; asked for RULE-1 with those hashes, the reader returns the `weak` entry, naming the source `ci`; with the two times exchanged it returns the `strong` entry, naming `local`

### 3e. Two proofs the lanes proposed

- `reports` PROOF-123 (RULE-38): A shell test file that exits 0 holds `# purlin: login PROOF-1` on line 3, inside a here document, and `# purlin: login PROOF-2` as a comment on line 5; one marker is read, `PROOF-2` at line 5, and the evidence holds no `pass` for `PROOF-1`
- `run_script` PROOF-286 (RULE-106): In a git checkout whose evidence lists `feat`'s slow `PROOF-2` as `pass` with `kept`, `--all --test --commit` runs with nothing changed since; the slow test is started, and the evidence lists `PROOF-2` as `pass` and holds no `kept`

### 3f. The compiled copy kept from the first run

Without the fix the new test failed in 2 runs of 3; with it, it passed in 3 of 3.

- `planted_bug` RULE-14: The file the bug changes is given a later time than it had, so the test, which already ran once in the copy, runs the changed code and not a compiled copy kept from that first run
- `planted_bug` PROOF-21 (RULE-14): The model answers `file: src/age.py`, `before:` `return 90`, `after:` `return 91`, a change that keeps the file's size, and the test of `PROOF-1` expects `90`; the result reads `caught`, not `survived`

### 3g. `ai_audit PROOF-110`, split

- `ai_audit` PROOF-110 (RULE-43), reworded: `claude` exits with the code 1 at every call and the audit reads two rules that pass, with no spot test firing on either; both entries read `spot-checked`, and the audit prints `The model could not be reached: claude exited with an error. 2 rules are spot-checked alone. Run purlin:audit again.` once
- `ai_audit` PROOF-123 (RULE-35): `claude` exits with the code 1 at every call and the audit reads two rules that pass, with no spot test firing on either; its last line reads `The audit found 0 of 2 rules strong (0%): 0 strong, 2 spot-checked.`

### 3h. A hand check reads the audit's word

- `states` RULE-16, reworded: A rule with a `@manual` proof reads `checked at sign-off` in its strong cell, unless its audit reads `weak` or `spot-checked` or is out of date, where the cell reads as any other rule's does, and raises the `manual` flag
- `states` PROOF-291 (RULE-16): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, and its current audit entry reads `spot-checked` with the `no_bug` sentence `No bug was planted: PROOF-2 needs Windows, and this machine is macOS.`; the strong cell reads `spot-checked` with the one reason `The spot tests found nothing. ` followed by that sentence, and the rule raises the `manual` flag
- `states` PROOF-292 (RULE-16): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, and its audit entry reads `strong` and was written for another rule text; the strong cell reads `out of date` with the first reason `rule changed since <sha7>`
- `states` PROOF-293 (RULE-16): A rule has `PROOF-1` marked `@manual` and `PROOF-2` whose test passes, and its current audit entry reads `strong`; the strong cell reads `checked at sign-off`

### 3i. The upgrade asks before it removes a workflow

The `workflows` migration keeps its question. Applied, it prints the line of each workflow
that names a proof file and asks about that file. `--yes` is a yes to no one file: each is
kept and named. A kept workflow alone holds no update pending, so it stops no test run.

- `update` RULE-53, reworded: The files 0.9.5 kept that this release does not use are removed: the proof and run files beside the specs, the `.purlin/cache/` folder and the plugin copies under `.purlin/`; the dashboard data is untracked, left on disk and named in `.gitignore`; a file of any other name is left alone
- `update` RULE-55, reworded: The update removes no workflow on its own: for each file under `.github/workflows/` that names a proof file it prints the line that does and asks `Remove <path>? [y/N]`, backing up what it removes; `--yes` answers for none, and a workflow not removed is kept, named with what to do, and alone holds no update pending
- `update` PROOF-164 (RULE-55), reworded: The sample 0.9.5 project holds `purlin-proofs.yml` and `ci.yml`, which runs `pytest`; with every question answered `y`, the update prints `.github/workflows/purlin-proofs.yml:9 names a proof file: - run: git add '*.proofs-*.json'`, asks `Remove .github/workflows/purlin-proofs.yml? [y/N] ` and removes it with a backup holding its bytes; `ci.yml` is as it was, and the output holds `removed 1 workflow that committed proof files`
- `update` PROOF-166 (RULE-55): The same project is updated with `--yes`; no question is asked, `purlin-proofs.yml` is byte for byte as it was and still tracked, the output holds `.github/workflows/purlin-proofs.yml: kept. It names a proof file and may be the old Purlin workflow; remove it by hand if it is.`, and no migration is pending afterwards
- `update` PROOF-167 (RULE-55): With the question `Remove .github/workflows/purlin-proofs.yml?` answered `n` and every other `y`, the update of the same project leaves `purlin-proofs.yml` byte for byte as it was, and prints the same `kept` line for it and no `removed` line

### 3j. The sign-off refuses a tag it did not write

Where `signed/<version>` exists for the version being signed and its commit holds no evidence
package for that version, the command stops first and writes nothing. Seen failing first: the
walk went on to its questions. The tests of `signatures` PROOF-224 and PROOF-225 typed their
tag by hand; they now sign for real, and their proofs' words stand.

- `signatures` RULE-135: The command refuses, with one line and nothing written, where `signed/<version>` exists for the version it is to sign and names a commit holding no evidence package for that version: the line names the tag, why it is no sign-off, and `git tag -d`, with `git push origin --delete` where the checkout has a remote; a tag that is the version's sign-off refuses nothing
- `signatures` PROOF-266 (RULE-135): A project with passing committed evidence and no remote carries the tag `signed/2.1.0`, written by hand with `git tag`; the walk for `2.1.0` prints only `No sign-off: signed/2.1.0 names a commit that holds no evidence package for 2.1.0, so purlin:sign did not write it. Delete it: git tag -d signed/2.1.0. Then run purlin:sign again.`, adds no commit and exits 1
- `signatures` PROOF-267 (RULE-135): A project with a remote named `origin` carries the tag `signed/2.1.0`, written by hand with `git tag`; the one line the walk for `2.1.0` prints ends `Delete it: git tag -d signed/2.1.0, and git push origin --delete signed/2.1.0 if it was pushed. Then run purlin:sign again.`
- `signatures` PROOF-268 (RULE-135): `jane@acme.com` signs `2.1.0` by the walk, which writes `signed/2.1.0`; `omar@example.org` then signs `2.1.0`; that walk exits 0, prints no line starting `No sign-off:`, and the folder `2.1.0.signoffs` holds `jane.json` and `omar.json`

### 3k. A version change alone ends nothing for an anchor

An anchor's `code` part took the settings file in whole. It now leaves the file out, and the
`tests` part, which already covered the `tests` setting for every spec, ends the results when
a test command changes. The fingerprint's structure is unchanged, so no format number moved.

- `evidence` RULE-30, reworded: An anchor's `code` part covers every file git tracks but the records Purlin writes and the settings file `.purlin/config.json`, whose `tests` setting the `tests` part covers, so an edit to any other tracked file changes it and an untracked file does not
- `evidence` PROOF-84 (RULE-32), reworded: its ending reads `the records and the settings file aside @env(windows)`
- `evidence` PROOF-90 (RULE-30): Beside the anchor `security`, the `version` in `.purlin/config.json` is changed from `0.10.0` to `0.10.1` and nothing else; all three parts of the fingerprint of `security` are as they were
- `evidence` PROOF-91 (RULE-30): Beside the anchor `security`, the `run` command of the `tests` setting in `.purlin/config.json` is changed; the fingerprint of `security` differs from the one taken before in `tests` alone

### 3l. The Audit box, and the check on the Strong column

**The check.** The page drew the `Strong` column, box and panel where `summary.audit` counted
a rule `strong`, `weak`, `spot_checked` or `out_of_date`. So a project whose every result is
`spot-checked` or out of date already had them. One case was narrower than the rules' words:
a rule that carries an audit entry and no longer passes, or a hand check found strong, is in
none of those counts. The page and the status table now also answer yes where any rule
carries an entry. `RULE-8`, `RULE-9`, `RULE-15` and `RULE-39` already read `wherever a rule
has an audit entry` and are not reworded.

For a spot-checked rule and one out of date: the `Strong` column's cell counts neither, so a
spec of three such rules reads `0 of 3`; the lower `Strong` box counts neither; the rule's row
on the board carries no `STRONG` badge; the rule's screen reads `SPOT-CHECKED` or
`OUT OF DATE` with its reasons, and the `Audit` panel.

- `purlin_report` RULE-7, reworded: The top bar holds three boxes, as the payload gives them. Two state the two facts: `Tests` reading `met` where every rule's tests pass on the committed evidence and `not met` otherwise, and `Sign-off` reading `signed <version> at <commit>`, `signed <version>, <n> commits since` or `not signed`. The third, `Audit`, is information and no fact: it reads `not audited` in the neutral tone where no audit has read a rule, and otherwise `<s> of <n> strong`, as the summary counts them, in the pass tone where no rule is weak and the warn tone where one is, its hover the audit's counts, one to a line, then `Last audit: <date>`
- `purlin_report` RULE-44, reworded: In a project no audit has read, the top bar's `Audit` box, reading `not audited`, is the one text the page shows that uses `strong` or `audit` at any casing: no other box, column, hover, empty state or rule screen does, nor uses `proof` where the project writes no proof line, and a rule shows its text, its tests and one status out of `passed`, `failed`, `partial`, `no test`, `not run` and `out of date`
- `purlin_report` PROOF-223 (RULE-7), reworded: its ending reads `the top bar holds exactly three boxes, `Tests` reading `met`, `Sign-off` reading `signed 0.1.0 at a1b2c3d` and `Audit` reading `3 of 7 strong``
- `purlin_report` PROOF-63, PROOF-103 and PROOF-65 (RULE-44), reworded: each `no text or hover contains` reads `no text or hover but the top bar's `Audit` box contains`; PROOF-65's `no text contains` reads `no text but the top bar's `Audit` box contains`
- `purlin_report` PROOF-241 (RULE-7): Open the board with the solo sample, which no audit has read; the `Audit` box reads `not audited` in the neutral tone, the tone `not signed` reads in beside it, and the column headings read exactly `Spec`, `Rules`, `Proofs`, `Tests`
- `purlin_report` PROOF-242 (RULE-7): Open the board with the regulated sample, whose audit found 3 rules strong and 3 weak and left 1 not audited, its newest entry written on `2026-09-12`; the `Audit` box reads `3 of 7 strong` in the warn tone, and its hover reads the four lines `3 strong`, `3 weak`, `1 not audited` and `Last audit: 2026-09-12`
- `purlin_report` PROOF-243 (RULE-9): Open the board with the solo sample after login's `RULE-1`, its one audit entry, is given the verdict `spot-checked`; the headings end with `Strong`, login's `Strong` cell reads `0 of 3`, the `Strong` box reads 0, the `Audit` box reads `0 of 2 strong` in the pass tone, and the rule's screen carries the `Audit` panel reading `Spot-checked.`
- `states` PROOF-294 (RULE-121): Over a spec of two rules, `RULE-2` passes and the audit finds it `strong`, and its test then fails; the status report's header still ends with `Strong`, and the spec's `Strong` cell reads `0 of 2`

`PROOF-225` keeps its words: its test reads the first two boxes. The payload gained no field
and stays at schema 15: the box reads `summary.audit`, the counts the summary line prints.
The deck's notes do not describe the top bar, so the deck is unchanged.

## 4. Lines a person reads, chosen at integration

| Line | Where it prints |
|---|---|
| `the test ended in an error, not a failure` | a planted bug's `why` in the evidence |
| `A bug was planted for PROOF-2 and its test ended in an error, not a failure.` | the audit, under the rule; the strong cell's reason; the `Audit` panel |
| `<name>: not added. --path takes a path inside the source, with no .. and no leading /. Run purlin:anchor add <source> --path <path> --name <name>.` | `purlin:anchor add` |
| `.github/workflows/purlin-proofs.yml:9 names a proof file: - run: git add '*.proofs-*.json'` | `purlin:init --update`, before its question |
| `Remove .github/workflows/purlin-proofs.yml? [y/N] ` | `purlin:init --update` |
| `<path>: kept. It names a proof file and may be the old Purlin workflow; remove it by hand if it is.` | `purlin:init --update`, among its report lines |
| `Apply workflows, which will remove each workflow that names a proof file, asking for each? [y/N] ` | `purlin:init --update` |
| `No sign-off: signed/2.1.0 names a commit that holds no evidence package for 2.1.0, so purlin:sign did not write it. Delete it: git tag -d signed/2.1.0, and git push origin --delete signed/2.1.0 if it was pushed. Then run purlin:sign again.` | `purlin:sign`; the push half only where the checkout has a remote |
| `AUDIT` `not audited`, `AUDIT` `34 of 40 strong` | the dashboard's top bar |
| `34 strong`, `4 weak`, `2 spot-checked`, `Last audit: 2026-09-13` | the `Audit` box's hover |

The docs sentences added are in `docs/dashboard.md` ("The third box"), `docs/upgrading.md`
("The workflows"), `docs/sign-off.md`, `docs/specs-and-anchors.md`, `docs/audit.md`,
`docs/running-and-evidence.md`, the sign, init, audit and anchor skills, and
`references/evidence_and_signoff.md`.

## 5. The checks

| Check | Result |
|---|---|
| `bash dev/run_tests.sh` | 906 passed, 0 failed, 9 skipped; 4 suites passed, 0 failed |
| What skipped | 9 tests only Windows can show: `test_config_engine` 1, `test_evidence_reader` 1, `test_export` 1, `test_init_scaffold` 3, `test_init_update` 3 |
| `purlin_run.py --test` | exit 0; 910 markers tied, 0 not tied; 408 of 433 rules pass; left: 1 rule to test, 5 slow proofs, 19 rules to test on Windows |
| `purlin_run.py --test --all --commit` | exit 0; 910 tied, 0 not tied; 39 specs, 433 rules, 910 proofs; 413 pass; no rule `failed`, `partial` or `no test`; no warning; committed as `purlin: evidence at 71ad335` |
| Appendix A's script over every `dev/test_*` | `0 gone, 6 reworded, 904 right as they stand.` The six are the five slow proofs and `purlin_report PROOF-66`, the same six as at decision 120's end |
| The plan's three greps | each empty, once two test helpers named `_code_changed` were renamed |
| `dev/test_purlin_agent.py` after `words` | 6 passed |
| `check_deck.py`, `check_overlap.py`, `DECK_ROOT` a scratch folder | every slide ends at 920 of 920; no overlap. Not published |
| The docs screenshots | retaken and committed: both now show the `Audit` box |
| Formats | evidence 11, package 11, signature 16, as the lanes left them; anchor 12, marker 4, spec 23. No number moved at integration: each edit there clarified words |

**The state named was not reached by one rule.** The run ends:

```
433 rules. 413 pass their tests.
Left to do:
  1 rule to test: purlin:test
  19 rules to test on Windows: run purlin:test on Windows
```

The one rule is `evidence RULE-32`. Its only proof, `PROOF-84`, is tagged `@env(windows)`, and
its Windows result is out of date since 3k changed the spec, the code and the test. `summary`
RULE-8 counts an `out of date` rule under `to test`, whatever systems its proofs name, so the
line names `purlin:test`, which cannot clear it here. The Windows run clears it. It is listed
for the owner below.

## 6. The dashboard, looked at

`/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/0b911df6-a4da-4d86-9e09-dc4ed8c6bce2/scratchpad/d121-integration-look/`,
62 screenshots: this repository's own data, the regulated sample with a spot-checked rule, one
out of date and the longest top bar values, and the solo sample; dark and light; every screen
at 1500 and 390, the top bar at 1500, 1280, 1024, 768 and 390.

- No sideways scroll, no value, pill, label or rule id on two lines, nothing cut, and every
  text at 7 to 1 (4.5 to 1 for the dark theme's fail red and accent copper), on all 30 boards
  and every rule screen.
- The three boxes sit on one row at 1500. At 1280 and 1024, with `signed 0.1.0, 4 commits
  since` and `34 of 40 strong`, they move as a group to a second row. At 768 `Audit` takes a
  row of its own. At 390 they stack.
- The strong row reads `SPOT-CHECKED` and `OUT OF DATE` with their reasons; the `Audit` panel
  opens on `Out of date:` and keeps the last result.
- The long path breaks after `_` at 390: `specs/billing/exports/regulated_`, then
  `export_of_signed_invoices.md`.
- This repository reads `AUDIT not audited`, in teal: its evidence holds no audit entry.

## 7. Measured, and left alone

**The cost of verifying sign-offs on each status.** On this repository, which holds no
sign-off: 10 ms to read the sign-off and 10 ms for the hand notes, of a status that takes
4,450 ms. In a scratch project: 183 ms with one sign-off, 311 ms with two, 391 ms with three,
so about 100 ms for each sign-off `HEAD` holds.

## 8. Left unbuilt

- The real Windows run and the second cost measurement: the coordinator's.
- `ai_audit` PROOF-111 is 61 words. It is decision 120's and was not touched.
- No proof holds the path break at 390 pixels.

## 9. Calls for the owner

1. A rule whose every proof is tagged for another system reads `1 rule to test: purlin:test` once its result there goes out of date, though only a run on that system clears it.
2. Under `--yes` the upgrade removes no workflow, and the upgrade has no flag that says yes for one file, so a person who upgrades without typing answers removes the old workflow by hand.
3. A workflow the person kept is asked about again on a later upgrade only while another migration is pending.
4. The sign-off refuses a hand-typed tag only where the tag's commit holds no evidence package; a tag whose sign-off stopped counting is still left to a later signer, because deleting it would not help the same signer.
5. Git keeps no record of which tags a remote holds, so the refusal says `if it was pushed` and names the remote wherever the checkout has one.
6. The `Audit` box is green at `0 of 12 strong` when no rule is weak, since its tone follows weak rules alone.
7. A hand check found `strong` still reads `checked at sign-off`, so the summary counts it under no audit word, while one found `spot-checked` is counted.
8. An `exit` suite cannot tell an error from a failure, so a planted bug that makes a shell test exit with any code but 0 reads `caught`.
9. A test whose own body raises an exception it did not expect is a failure to pytest, and reads `caught`.
10. Verifying every sign-off costs about 100 ms a sign-off on each status.
11. At 1280 pixels the three boxes take a second row when the sign-off and the audit both read their longest values.
