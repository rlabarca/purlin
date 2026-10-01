# Round 1, integrated

Written by the integration agent on 2026-10-01. The six round 1 lanes are merged, in the order
`evidence`, `states`, `signoff`, `spot`, `audit`, `run`, each rebased onto the merged line and
merged fast-forward. `d115/base` is the merged line. Round 2's lanes read this file first.

## The sweep

`bash dev/run_tests.sh` on the Mac, with `dotnet`, `go`, `npm`, `sqlite3`, `ssh-keygen` and
playwright present.

| | Passed | Failed | Skipped |
|---|---|---|---|
| Pytest, every `dev/test_*.py` | 1,670 | 30 | 3 |
| Shell suites | 3 | 1 | 0 |

The 3 skipped are the tests tagged `@env(windows)`: `config_engine`'s move onto a file held open,
`evidence PROOF-75` and `package PROOF-39`. Nothing skipped for a missing tool.

### Failures in the files round 1 owns: 4

| Test | Proof | Why | Clears when |
|---|---|---|---|
| `dev/test_run_script.py::TestTheRunnerOnFirstNeed::test_remote_with_no_runner_file_writes_it_and_runs_nothing` | `run_script PROOF-272` | named wait | `remote` builds `ensure_runner` (K11) |
| `dev/test_run_script.py::TestTheRunnerOnFirstNeed::test_commit_runner_commits_the_runner_file_alone` | `run_script PROOF-273` | named wait | `remote`, the same |
| `dev/test_states.py::TestStatusTable::test_the_three_samples_show_the_same_cells_in_the_table_and_page` | `states PROOF-58` | named wait | `dashboard` rebuilds the page and its fixtures at schema 14 |
| `dev/test_export.py::TestMet::test_a_rule_with_no_proof_is_left_to_write_one_for` | `package PROOF-5` | **not a named wait: two specs disagree, for the owner** | see "For the owner", 1 |

No round 1 test sets a project up through `scaffold.py` and fails for it:
`evidence_writer PROOF-63` runs `scaffold.py --yes` and passes today. It reads setup's ignore
file, so `setup` reruns it after its change.

### Failures in the files round 2 owns: 26 tests and 1 shell suite

| File | Failed | Lane | What it still expects |
|---|---|---|---|
| `dev/test_init_scaffold.py` | 8 | `setup` | the two gates, the release step and its tags, `Nothing left to do.` |
| `dev/test_mcp_server.py` | 6 | `mcp` | the project's name from the settings (`Purlin status: proj`); the settings tool's old keys; and `TestPackageHygiene::test_the_package_imports_nothing_outside_the_standard_library`, which names `facts.py: import package` (see "What round 2 must be told", 1) |
| `dev/test_schema_spec_format.py` | 1 | `mcp` | the old `> Scope:` warning beside the information line |
| `dev/test_purlin_report.py` | 4 | `dashboard` | a rule unfolded under its row (playwright times out on the click) and the payload of schema 13 |
| `dev/test_report_refresh.py` | 4 | `dashboard` | `release.py`, `sign.py --release`, the payload's `gate` |
| `dev/test_consumer_ci.py` | 1 | `remote` | the payload's old keys |
| `dev/test_purlin_docs.py` | 1 | `docs` | lines the run no longer prints, quoted in the docs |
| `dev/test_skill_status.py` | 1 | `words` | a row in the status skill for each kind of `Left to do` line as it now reads |
| `dev/test_e2e_anchor_rules.sh` | 1 suite | `anchors` | `the table does not end with nothing left to do` |

Every other round 2 test file passes on the merged line as it stands. That is fewer failures
than the plan expected, and it does not mean those files are done: appendix A's script still
counts their comments as gone or reworded, and section 4's rows for round 2 hold.

## Section 5's three checks

1. Appendix A's script over the fifteen test files round 1 owns:
   `0 gone, 0 reworded, 424 right as they stand.`
2. `git diff --stat origin/d115/base..HEAD -- specs/` names nothing.
3. Three reviewers that fixed none of the tests read every `fixed` test and 11 `stated` ones
   against their proofs: 106 tests read, 101 agreed with. The five they named, and `package PROOF-5`, already known:
   - `ai_audit PROOF-34`: `'token' in second` could not fail, since the test's name holds the
     word. Fixed: it asserts the body line and that neither test holds the other's.
   - `signatures PROOF-220`: the overview was checked by the `Signing` line alone. Fixed: it
     asserts both overview lines.
   - `signatures PROOF-222`: "adds nothing" was checked by `HEAD` alone. Fixed: it asserts
     `git status` is empty.
   - `states PROOF-7`, `package PROOF-3`, `package PROOF-5`: each is a proof the code cannot
     meet as worded beside another rule. Left as the lanes built them; see "For the owner".

## What integration changed

| Commit | What |
|---|---|
| `test(evidence_writer): PROOF-78 hands build_sections the commit the run now passes` | `purlin_run.build_sections` gained `commit` (K2); `evidence`'s test called it without. |
| `chore(sign_project): the two gate names no test file imports are gone` | `FIRST_GATE` and `SIGNING_GATE` deleted from `dev/sign_project.py`. No file in round 1 or round 2 imports either. |
| `chore: .purlin/tests.md is gone with its writer` | step 5. The untracked folders `scripts/ci`, `scripts/hooks` and `scripts/proof` held only `__pycache__` and are deleted. |
| `test(ai_audit): PROOF-34 ...` and `test(signatures): PROOF-220 ..., PROOF-222 ...` | the review above. |
| `fix(states): git launched from a list, each open naming its encoding on its line, no version in the payload's example` | Round 2's own checks over the whole package found these in round 1's new code: `subprocess.run(('git',) + args` in `facts.py`, `wording.py` and `audit_run.py` (the security anchor wants a list); three `open(` calls whose `encoding=` stood on the next line, in `payload.py` and `wording.py`; `0.1.0` in `payload.py`'s docstring. No behaviour changed. |

No lane wrote a file it does not own. No rebase conflicted.

## Tests still waiting, and on what

| Proof | Waits on |
|---|---|
| `run_script PROOF-272`, `PROOF-273` | `remote` (round 2): `ensure_runner`, `run_remote` |
| `states PROOF-58` | `dashboard` (round 2): the page and `dev/fixtures/report/*.json` at schema 14 |
| `package PROOF-5` | the owner |
| `evidence PROOF-75`, `package PROOF-39`, `ai_audit PROOF-82`, every other `@env(windows)` proof | a Windows run, after the build |

Every wait a lane listed on another round 1 lane cleared on the merge with no change:
`evidence_writer PROOF-38`, `54`, `91`, `92`, `93`, `94` and the rest of its list;
`states PROOF-169`, `274`, `278`; `summary PROOF-50`; `signatures PROOF-242`;
`package PROOF-69`, `72`, `75`; `ai_audit PROOF-95`, `96`, `97`, `98`, `100`, `102`, `106`;
`run_script PROOF-87`, `95`, `222`, `271`, `274`.

On the Mac, the tests that skipped in the cloud ran and passed:
`dev/test_reports.py::test_dotnet_still_writes_what_the_capture_holds`,
`run_script PROOF-155` (`sqlite3`), and `dev/test_signatures.py` and `dev/test_export.py`
whole, with real SSH-signed commits and tags.

## For the owner

1. **`package PROOF-5` against `summary RULE-8` and `states RULE-1`.** The proof has a rule
   "with no proof and no test" in a project that "is signed", with `left` `no_proof`.
   `states RULE-1` reads such a rule `no test`, and `summary RULE-8` counts `no test` as
   `to write a test for` before it counts a missing proof, which needs "its tests passing".
   `no_test` blocks, so the sign-off refuses:
   `No sign-off: 1 rule does not pass at <sha7>: login RULE-3.` The test fails. Either the
   proof gives the rule a passing test marked with its own id, or a rule with no proof and no
   test stops blocking.
2. **`package PROOF-3` against `package RULE-3`.** The proof names `commit` "the full sha of
   the commit the tests ran at". The rule and the code give `HEAD` stepped back over package
   commits alone, which is the commit that carries the results, one after the commit the
   section names. The test asserts the rule's sha and passes.
3. **`states PROOF-7` against `states PROOF-84`.** The proof says a report "in which
   `PROOF-2`'s test passed" leaves `RULE-2` reading `no test`. The test writes a report and
   marks no test for `PROOF-2`; with a marked test and no evidence the cell reads `not run`
   (`PROOF-84`), so the proof cannot be shown with the test it names.
4. **K6 against `states RULE-61`.** K6 gives a rule's `audit` in the payload `explanation` and
   `breaks`. The rule names seven fields and says "exactly", so the payload carries neither.
   `ai_audit.py --feature` prints an entry's explanation from the payload, so it prints none,
   and the dashboard cannot show a planted bug. The evidence file and the package carry both.
5. **An audit entry is written when the model cannot be reached** (`audit`). The rule then
   reads `strong` on the spot tests alone, every planted bug `not made`, and is not read again
   until `--all`. The owner may prefer no entry.
6. **A `dirty` section is not refused by the sign-off** (`signoff`). K7 says a dirty result
   does not count; no spec or contract gives the refusal's words, so none is printed.
7. **The sign-off file's `schema` stays `purlin-signoff/1`** though `shown` changed shape at
   format 15 (`signoff`).
8. **On a detached `HEAD` a later sign-off ends `Push it: git push origin`** with nothing
   after it (`signoff`, `signatures RULE-118`).
9. **`authors` costs one `git log -L` per proof**: about 80 seconds for this repository's 831
   proofs at a sign-off (`signoff`).
10. **The status is 1.4 seconds slower** on this repository, 2.6 s to 4.0 s (`states`, inside
    K4's 3 seconds).
11. **`→ Run: purlin:init --update` still prints** above the status's ending while an upgrade
    is pending. No decision cuts it and no proof holds it (`states`).
12. **The spot tests' calls** (`spot`): which checks each language is read for (Go not for 3
    or 5; shell for 1, 2 and 6; any other language for 6 alone); check 6 names the first
    backticked value; the checks as narrowed after one pass over this repository, which leaves
    18 findings, all from check 6, for round 2's step 9; the copy holds no `.git`, so a test
    that needs git reads `caught`; the guard runs `git status --porcelain -z` without `-uall`.
13. **The share's percent is rounded down**: 2 of 3 reads `66%` (`audit`).
14. **`--ignore=mutants`** stays in the suggested pytest command, as `run_script PROOF-126`,
    `221` and `262` hold it (`run`, K15).
15. **Cut by `run` on decision 112, with no proof holding them:** the doctest switch in the
    suggested pytest command; the sentence on installing `sqlite3` on a Windows runner; reading
    the 0.9.5 keys and the proof and receipt files under `specs/` to tell an older Purlin, which
    is now read off a settings file with no `tests` alone.
16. **Four unmarked tests stay** in `dev/test_reports.py`, the `..._still_writes_what_the_capture_holds`
    checks for Jest, Vitest, dotnet and Go. They name no proof (`evidence`).
17. **The `--commit-runner` refusal has no test**: `run_script` has no proof of it (`run`).

## Lines a person reads that a lane chose

Word for word from the six reports.

**`evidence`.** None printed.

**`states`.**

| Line | Where it prints |
|---|---|
| `no screens here` (the reason alone, as the run gave it) | the passed cell's reason on a feature's proof that found nothing to check; carried in the payload among the cell's reasons, which the dashboard's rule page shows |

**`signoff`.**

| Line | Where it prints |
|---|---|
| `The evidence package was not written: <why>. Nothing was signed; run purlin:sign again.` | `purlin:sign`, where the package cannot be built or written; `<why>` is the operating system's or git's own message |
| `The audit's findings: <n> weak.` | `purlin:sign --show`, in place of the walk's question, before the list |
| `Rule`, `Proof`, `Results` and `What the audit found` as headings, with the rule's words, each proof and finding indented two spaces | a hand check's stop, in the walk and `--show` |
| `    tied to no test` | under a proof that is not `@manual` and has no test tied, in a stop |
| `  <System>: <word> on <machine>` | a stop's result line |
| `Usage: sign.py [--version <version>] [--show \| --answers FILE \| --check FILE] [--project-root DIR]` | standard error, exit 2 |
| `sign.py: --check needs the package file to check.` | standard error, exit 2, after the usage line |
| `sign.py: --version needs the version to sign.` | the same |
| `sign.py: --show, --answers and --check are three steps; name one.` | the same |
| `sign.py: --check reads a file and takes no version.` | the same |

**`spot`.**

| Line | Where it prints |
|---|---|
| `Python`, `JavaScript`, `TypeScript`, `C#`, `Go`, `shell`; any other language by its extension without the dot, as `The test checks nothing is not read in rb tests.` | the language in `NOT_READ`, once per check and language |
| `the answer named no change` (K9's) | the `why` of a planted bug `not made`, printed by the audit in `PROOF-1: no bug was planted: <why>.` |
| `../outside.py is outside the copy of the project` | the same |
| `README.md is not a file the feature's scope names` | the same |
| `src/gone.py is not in the project` | the same |
| `the lines before the change are not in src/age.py` | the same |
| `the lines before the change are in src/age.py 2 times, not once` | the same |
| `the change leaves src/age.py as it was` | the same |

**`audit`.**

| Line | Where it prints |
|---|---|
| `login RULE-2   weak`, then each finding indented two spaces, then each `  PROOF-N: no bug was planted: <why>.` | `audit_run.run`, one block per rule read |
| `2 rules were read without the model's explanation: claude is not on PATH. Run purlin:audit --all once it can be reached.`; for one, `1 rule was read ...` | `audit_run.run`, where the model's reading could not be reached |
| `The audit found no rule that passes its tests.` | `audit_run.run`, in place of the share |
| each sentence of the entry's `explanation`, indented four spaces | `ai_audit.py --feature`, under `What the audit found`, after the findings |

Section 6's two lines are used as written: `The model was asked 31 times for 12 rules: $1.87
in all, $0.16 a rule.` and `PROOF-1: no bug was planted: <why>.`

**`run`.** None. Section 6's `purlin: --commit-runner belongs to --test --remote. Run
purlin:test --remote --commit-runner` prints to standard error with the usage line, with no
full stop after the command.

## Differences from the contracts, as built

**K2 and K3, `evidence`.**
- `email` is added by `write_section`, not `build_section`; `evidence.git_email(project_root)` is new.
- Retention is `merge_section(..., rule_ids, same_code=None)`; `write_section` hands it
  `package.only_records_between`. `merge_for_host` hands none, so a `ci` section is kept only
  over the same commit.
- `reports.tie` gives each outcome as `reports.Outcome`, a `str` carrying `.reason`;
  `reports.reason_of(outcomes)` reads it.
- `scripts/mcp/purlin/evidence.py` gains `NOTHING_TO_CHECK`, `NOTHING_TO_CHECK_PREFIX` and
  `nothing_reason(reason)`. `proof_results` orders `fail`, `not run`, `nothing to check`, `pass`.
- `build_section` reads `info['is_anchor']`. `audit_entry` always writes `breaks` and
  `explanation`. `markers.SKIP_DIRS` loses `mutants`.

**K4, K5, K6, `states`.**
- A rule's `audit` holds seven fields, without `explanation` and `breaks` ("For the owner", 4).
- `payload.build_payload` starts `warnings` empty: K1's settings warning waits for `mcp`.
- `EARLIER_WEAK` is defined and used nowhere.
- `signoff_fact` answers `SIGNED_AT` for a tag on `HEAD` without asking; `since` is the count
  of commits from the tag in every case, 1 where one evidence commit follows the tag and the
  word still reads `signed <v> at <sha7>`.
- The passed cell carries `nothing_to_check`, `[{proof, reason}]`.
- `states.section_results` reads both a bare word and K2's dict from `proof_results`. The bare
  word no longer occurs; the branch is left in.
- A comment whose proof did not exist at the test's last change is not named stale.
- `test_hash_kind` reads `manual`, then `file`, then `test`, then `none`.
- Added: `facts.is_signed_here`, `since_word`, `distance`, `records_only_since`,
  `commits_since`, `version_order`, `git_line`; `states.read_sections`, `section_results`;
  `summary.opening`; `status.not_written_lines`, `nothing_lines`; `wording.proof_words`,
  `test_source`, `count_line`; `payload.branch_name`.
- Changed: `states.rule_cells(inp)`, `states.feature_rollup(rule_results)`,
  `summary.rule_kind(rule, here_os, broken=None)`, `board.columns_for(proofs, audited)`,
  `board.row_cells(name, rollup, proofs, audited)`, `board.shows_proofs(proofs)`,
  `status.columns_for(proofs, audited)`, `payload.audit_summary(audit)`.

**K7, K8, `signoff`.**
- `package.audit` counts every rule, a hand check as not audited; the payload's
  `summary.audit` counts passing rules alone. The walk reads the package's numbers.
- A proof's `written_by` follows the proof's line through its edits (`git log -L`), as
  `package PROOF-74` needs; a rule's is K7's.
- `met` is worked out in `package.py` to `facts.tests_fact`'s definition, without calling it.
- A later sign-off signs the package `HEAD` holds and does not build it again.
- `results[]` and `runs[].rules` list only the sections holding a result for the rule.
- A rule's `audit` in the package carries `criteria` and `source` as well.
- The helpers from `release.py` are all in `sign.py`; `write_tag` always signs.
- A sign-off's `notes` are `{feature, rule, note}`. `runs` groups every section the package lists.

**K9, `spot` and `audit`.**
- `plain_checks.check_project(project_root, features=None, out=None)` and
  `targeted_break.break_proofs(project_root, jobs, ask, out=None, timeout=None)` are added.
  `audit_run.run` calls neither: it calls `check` and `break_proof` itself, prints `NOT_READ`
  once per check and language, and prints `STOPPED` on `ProjectChanged`. `planted_bug PROOF-7`
  and `PROOF-13` and `plain_checks PROOF-28` are shown through `spot`'s two functions.
- `break_proof(..., timeout=None)`; `proof` is `{'id', 'text', 'rule', 'rule_text'}`, and both
  lanes agree on it. `ModelUnreachable` is caught by its class name. `parse_answer` is public.
- `ai_audit.ask_for_bug(project_root, request, spent=None, runner=None)`;
  `reading_for(..., findings=())`, `is_read(..., code_changed=False)`,
  `audit_all(..., parallel=AUDIT_PARALLEL)`.
- `break_key`'s `code_part` is `fingerprint.code_part` for the feature. A rule's last planted
  bugs are read from the newest entry in either evidence file, whatever its hashes.
- `.purlin/runtime/audit_could_not_run.json` is no longer written. `evidence.could_not_run`,
  `why_not_audited` and `run/evidence.write_could_not_run` still stand, with nothing writing
  the file.

**K10, `run`.**
- `audit_run.run(project_root, features, selected, again=args.all, out=sys.stdout)`. The share
  is the audit's last line; the run then prints the status, as `run_script RULE-11` has it.
- `purlin_run.build_sections(..., os_name, commit, proofs=None)` takes the code's commit.
- The run reads a skipped test's reason in its own pass (`skip_reasons`, `purlin_run.reason_of`)
  beside `reports.reason_of`; both give the same answer. One could fold into the other.
- `wording.stale_comments(project_root, features, scanned=scan)`; not called for `--ci`.

## Left unbuilt

Nothing a round 1 spec names is left unbuilt but `package PROOF-5`. `dev/test_wording.py`,
which `states` was allowed to add, was not added: `wording.py` is shown through `states`,
`run_script`, and `package`'s tests.

## What each lane's session cost

No session could read its own spend: all six reports say so. The coordinator reads the balance
from the account.

## What a round 2 lane may assume, checked against what was built

Confirmed, all in `d115/base`: K2's evidence file, format 8; K3's reasons and `nothing to
check`; `wording.py`, `project.py` and `facts.py` working; the status's three opening lines,
the kinds of work and the last line; payload schema 14 with its eighteen keys;
`package.only_records_between` and `same_code`; `purlin:sign` with `--version`, `--show`,
`--answers` and `--check`, and no `--release`; `purlin_run.py` with no `--release`, with
`--commit-runner`, and with `--audit` calling `audit_run.run`; `report_data.refresh` called by
`purlin:status` (`status.sync_status`), by `purlin:test` and `purlin:audit` through that same
call at the end of the run, and by `purlin:sign`.

Corrections and additions:

- A rule's `audit` in the payload has seven fields, not K6's nine: no `explanation`, no `breaks`.
- The payload's `warnings` does not carry K1's settings warning yet.
- `scripts/export/release.py`, `dev/test_tag.py`, `dev/test_mutation_adapters.py`,
  `dev/fixtures/mutation/`, `setup.cfg` and `.purlin/tests.md` are gone. `package.py` has no
  command line.
- `gate.py` and `scripts/run/mutation/` still stand: `server.py` and `update.py` import the
  first, `scaffold.py` the second.
- `dev/sign_project.py` no longer holds `FIRST_GATE` or `SIGNING_GATE`.

## What round 2 must be told that the plan does not say

1. **`mcp`: `scripts/mcp/purlin/facts.py` imports `package`** from `scripts/export/`, as K6
   requires (`signoff_fact` asks `package.only_records_between`).
   `dev/test_mcp_server.py::TestPackageHygiene::test_the_package_imports_nothing_outside_the_standard_library`
   lists only `purlin` and `config_engine` as the plugin's own, so it fails. `package` is the
   plugin's own module and belongs in that test's `local`. `facts.py` is not `mcp`'s to change.
2. **`mcp`: K1's settings warning has one line waiting for it** in `payload.build_payload`,
   which is `states`' file and frozen in round 2. `mcp` names the `config_engine` function in
   its report, and integration adds the line.
3. **`mcp`: `specs.spec_mistakes` still warns** `<spec>: > Scope: names <x>, which finds no
   file in git.` beside the information line of `states RULE-123`. Until it stops, a spec ahead
   of its code prints both.
4. **`remote`: the run calls `remote.run_remote(project_root, args)`**, two arguments, with
   `args.commit_runner`. `remote.py` still takes a third, `cfg`.
   `run_script PROOF-272` and `PROOF-273` are in `dev/test_run_script.py`, which is frozen:
   `remote` runs them and builds until they pass. They take `gh` off the path and push to a
   bare repository on disk.
5. **`dashboard`: the payload** carries `nothing_to_check` on a passed cell, `[{proof, reason}]`;
   a hand check reads `checked at sign-off`, where `app.js` reads `manual test`; a rule's
   `audit` has no `explanation` and no `breaks`. `states PROOF-58` in `dev/test_states.py`
   compares the status table with the page over the three fixtures and is `dashboard`'s to turn
   green: today the page shows `1 of 2 · 48%` and `· no scope` where the table shows `1 of 2`.
   `dev/test_report_refresh.py` imports `release` and calls `sign.main` with `--release`.
6. **`setup`: `evidence_writer PROOF-63`** in `dev/test_evidence_writer.py` runs
   `scaffold.py --yes` and reads the ignore file setup writes; `setup` reruns it after its
   change. `templates/gitignore.purlin` still names `.purlin/tests.md`.
   `dev/test_init_scaffold.py:1984` expects `Nothing left to do. To release a version: ...`,
   and one test checks a project's `setup.cfg`.
7. **`words`:** `skills/sign/SKILL.md` lines 37 and 99 pass `--release`; `skills/export/` and
   `dev/test_skill_export.py` name `package.py`'s command line, which is gone;
   `references/purlin_commands.md` lines 147 and 148 describe the old exits of `sign.py` and
   `package.py`; `references/commit_conventions.md` names `purlin:export`, `--release` and
   `.purlin/tests.md`; `dev/skill_checks.py:199` reads `Nothing left to do.`;
   `references/formats/signature_format.md` already points at
   `references/evidence_and_signoff.md`, which `words` writes. The build skill names
   `python3 scripts/mcp/purlin/wording.py`, which works as K4 gives it. The audit's printed
   lines above are what the audit skill describes.
8. **`anchors`:** `references/formats/anchor_format.md` still names `.purlin/tests.md` or
   `audit.mutation`. `dev/test_e2e_anchor_rules.sh` expects the table to end on
   `nothing left to do`. The security anchor's argument-vector check reads every file under
   `scripts/`; it passes on the merged line.
9. **`docs`:** `.purlin/tests.md` or `audit.mutation` is named in `how-purlin-works.md`,
   `running-and-evidence.md`, `working-together.md`, `dashboard.md`, `specs-and-anchors.md`
   and `getting-started.md`.
10. **Every lane:** `dev/run_project.py`, frozen, still gives the default pytest suite
    `--ignore=mutants`. Three checks read the whole package and will catch a round 2 lane the
    way they caught round 1: a `subprocess` call takes a list written out, `['git'] + list(args)`
    and never a tuple; an `open(` names `encoding=` on the same line; no module under
    `scripts/mcp/purlin/` holds a version number in a string, a docstring included.
