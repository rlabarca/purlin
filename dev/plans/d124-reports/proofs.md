# Lane `proofs` of decision 124: the 11 proofs sharpened

Branch `lane/d124-proofs`, rebased on `main` at `2dedc6eff`. Four commits, one per spec with its
test file, then this report. No code under `scripts/` changed. No rule changed, no number was
added, and no `> Highest-*` line moved.

## The proofs, before and after

Words are counted as the text after `PROOF-N (RULE-N): `, split on spaces.

### `run_script` PROOF-88 (RULE-55): 58 words, was 58

Before: In a git checkout, `login` and `export` each scope one source file and have a passing test and evidence committed by `--test --commit`; `src/login.py` then changes. The next `--test` with no feature named exits 0, selects `login` alone, reason `code changed since <sha7>` for the commit that run started on, and leaves export's evidence byte for byte unchanged

After: `login` and `export` each scope one source file, their passing tests' evidence committed by `--test --commit`; `src/login.py` then changes. The next `--test`, no feature named, exits 0, selects `login` alone, reason `code changed since <sha7>`, that run's commit, prints `Ran pytest on 1 feature.`, the report holding login's test alone, and leaves export's evidence unchanged byte for byte

Corrected: the proposed addition took the proof to 70 words. The setup was shortened to make room:
`In a git checkout` is gone, since `--test --commit` says it, and `the suite's report` reads
`the report`.

### `run_script` PROOF-91 (RULE-101): 59 words, was 59

Before: Beside `login` and `export`, whose committed evidence is current, a new feature `invoice` with a passing test is committed, never run; the next `--test` with no feature named exits 0, selects `invoice` alone, reason `no run on <System> yet`, and prints `Skipped 2 features whose spec, code and tests match their evidence: export, login. purlin:test --all runs them too.`

After: `login` and `export` are current; `invoice`, committed with a passing test, was never run; the next `--test` exits 0, selects `invoice` alone, reason `no run on <System> yet`, prints `Skipped 2 features whose spec, code and tests match their evidence: export, login. purlin:test --all runs them too.` and `Ran pytest on 1 feature.`, the report holding invoice's test alone

Corrected: 71 words as proposed. The setup was shortened, `with no feature named` was dropped as
PROOF-93 already writes it, and `the suite's report` reads `the report`. Both printed lines are
kept whole.

### `run_script` PROOF-93 (RULE-101): 60 words, was 60

Before: `login` and `export` have current committed evidence, `login`'s scope names `src/login.py, src/auth/`, and `src/auth/token.py` is written and not added to git; the next `--test` exits 0, selects `login` alone, reason `a file is not tracked`, and prints `src/auth/token.py is under login's scope and is not tracked, so its content is not part of the evidence until you git add it.`

After: `login`, current like `export`, scopes `src/login.py, src/auth/`; `src/auth/token.py` is untracked; the next `--test` exits 0, selects `login` alone, reason `a file is not tracked`, prints `src/auth/token.py is under login's scope and is not tracked, so its content is not part of the evidence until you git add it.` and `Ran pytest on 1 feature.`, the report holding login's test alone

Corrected: 73 words as proposed. The setup is the tightest of the three and reads tersely:
`current like export` and `is untracked`. The owner may prefer to split the run-alone result into
a proof of its own; that needs a new number, which this lane did not take.

### `run_script` PROOF-117 (RULE-12): 29 words, was 23

Before: When `.purlin/evidence/ci/feat.json` on disk holds only another system's section, `--all --ci` leaves that section as it was and adds this machine's beside it

After: When `.purlin/evidence/ci/feat.json` on disk holds only another system's section, `--all --ci` leaves that section as it was and adds this machine's beside it, its `machine` this machine's host name

As proposed.

### `run_script` PROOF-271 (RULE-96): 57 words, was 46

Before: In a git checkout, `feat`'s PROOF-1 is reworded and committed after its passing marked test at `tests/test_feat.py:3` last changed; `--all --test` prints, after the `Markers:` line, a line beginning `tests/test_feat.py:3 names feat PROOF-1, whose wording changed after the test was last changed in`, and exits 0

After: In a git checkout, `feat`'s PROOF-1 is reworded and committed after its passing marked test at `tests/test_feat.py:3` last changed; `--all --test` prints, on the line straight after the `Markers:` line and before `Ran pytest on 1 feature.`, a line beginning `tests/test_feat.py:3 names feat PROOF-1, whose wording changed after the test was last changed in`, and exits 0

As proposed.

### `run_script` PROOF-288 (RULE-107): 57 words, was 37

Before: That project run as `--all --test --write-tests` prints no question, prints `Wrote the tests setting to .purlin/config.json.` and then `Markers: 1 tied to a test, 0 not tied.`; `tests` holds pytest's entry alone, and it exits 0

After: That project run as `--all --test --write-tests` prints no question, prints `Wrote the tests setting to .purlin/config.json.` and then `Markers: 1 tied to a test, 0 not tied.`; `tests` holds one entry alone: name `pytest`, command `python3 -m pytest {files} --junitxml={report}`, opening `py -3` on Windows, report `.purlin/runtime/reports/pytest.xml`, format `junit`, files `**/test_*.py` and `**/*_test.py`; it exits 0

Corrected: `opening py -3 on Windows` was added. The proof carries no `@env` tag and its test runs
on Windows, where the command written opens `py -3` (PROOF-221), so the sentence as proposed was
false there.

### `run_script` PROOF-289 (RULE-107): 44 words, was 25

Before: That project run as `--all --test` and answered `y` on its input writes pytest's entry as the `tests` setting, runs the test and exits 0

After: That project run as `--all --test` and answered `y` on its input runs the test; `tests` holds one entry alone: name `pytest`, command `python3 -m pytest {files} --junitxml={report}`, opening `py -3` on Windows, report `.purlin/runtime/reports/pytest.xml`, format `junit`, files `**/test_*.py` and `**/*_test.py`; it exits 0

Corrected: the Windows words, as for PROOF-288. `runs the test` is kept from the old sentence; the
proposal gave only the part about the entry.

### `signatures` PROOF-228 (RULE-110): 55 words, was 35

Before: In a home and a checkout with no signing key, `--show` over committed evidence that passes exits 0, prints the overview, and prints no line `No key to sign with. These commands set one up:`

After: In a home and a checkout with no signing key, `--show` over committed evidence that passes exits 0, prints `  2 rules on Linux/Unix: 2 pass their tests, no hand check.` on the line after the `Signing 2.1.0 at <sha7>.` line, and prints no line `No key to sign with. These commands set one up:`

Corrected: `after` reads `on the line after`, which is what the run does and what the test checks.

### `signatures` PROOF-238 (RULE-121): 48 words, was 42

Before: A clone of a bare repository on disk holds one commit of its own the host lacks, and signs `2.1.0`; it writes `signed/2.1.0`, and afterwards the bare repository holds no tag, its `main` has not moved, and the clone has no `FETCH_HEAD`

After: A clone of a bare repository on disk holds one commit of its own the host lacks, and signs `2.1.0`; it writes the tag `signed/2.1.0` at the sign-off commit, and afterwards the bare repository holds no tag, its `main` has not moved, and the clone has no `FETCH_HEAD`

As proposed.

### `package` PROOF-52 (RULE-23): 53 words, was 36

Before: In a project where `.purlin/evidence/package` is a file and not a folder, the walk is answered yes; it exits 1, prints one line carrying the operating system's own message, and adds no commit and no tag

After: In a project where `.purlin/evidence/package` is a file and not a folder, the walk is answered yes; it exits 1, prints after what the walk showed exactly one line, `The evidence package was not written: <the operating system's own message>. Nothing was signed; run purlin:sign again.`, and adds no commit and no tag

As proposed.

### `evidence` PROOF-88 (RULE-7): 43 words, was 37

Before: A `local` section of `login` stores the fingerprint taken now; the `run` command of the `tests` setting in `.purlin/config.json` is then changed; checked against a fingerprint taken again, the section reads out of date on exactly `tests`

After: A `local` section of `login` stores the fingerprint taken now; the `run` command of the `tests` setting in `.purlin/config.json` is then changed to another of the same length; checked against a fingerprint taken again, the section reads out of date on exactly `tests`

As proposed.

## The tests

Changed, each seen failing first:

| Proof | Test, as it is now named | What changed | Seen failing |
|---|---|---|---|
| `run_script` PROOF-271 | `test_a_reworded_proof_is_named_straight_after_markers_before_ran` | Checks `Ran pytest on 1 feature.` is printed once and after the named line | With the comparison turned round, `assert (1 == 1 and 3 > 4)` |
| `run_script` PROOF-288 | `test_write_tests_writes_pytests_one_entry_unasked_and_runs` | Expects the entry field by field, written in the test, with `py -3` on Windows | With the expected command opening `python2`, the two entries differed on `run` |
| `run_script` PROOF-289 | `test_answered_y_pytests_one_entry_is_written_and_the_test_runs` | The same expected entry | The same |
| `package` PROOF-52 | `test_a_package_folder_that_is_a_file_ends_on_one_line_no_commit_no_tag` | Checks the project holds no tag; the proof said so and the test did not | With `none` expected in the tag list, `assert '' == 'none\n'` |

Renamed only, since each already shows its new sentence:

| Proof | Was | Now |
|---|---|---|
| `run_script` PROOF-88 | `test_a_code_edit_runs_only_the_feature_that_covers_the_file` | `test_a_code_edit_selects_and_runs_alone_the_feature_that_covers_it` |
| `run_script` PROOF-91 | `test_a_feature_with_no_evidence_is_selected` | `test_a_feature_with_no_evidence_is_selected_and_run_alone` |
| `run_script` PROOF-93 | `test_an_untracked_file_selects_the_feature_and_is_named` | `test_an_untracked_file_runs_its_feature_alone_and_is_named` |
| `run_script` PROOF-117 | `test_another_systems_section_is_left_as_it_was` | `test_another_systems_section_is_left_and_this_hosts_is_added` |
| `signatures` PROOF-228 | `test_show_needs_no_key` | `test_show_with_no_key_prints_the_overview_after_the_signing_line` |
| `signatures` PROOF-238 | `test_it_fetches_nothing_and_pushes_nothing` | `test_it_tags_the_sign_off_commit_and_fetches_and_pushes_nothing` |
| `evidence` PROOF-88 | `test_a_changed_test_command_puts_the_section_out_of_date_on_tests` | `test_a_test_command_changed_to_one_as_long_is_out_of_date_on_tests` |

## Calls the plan did not make

- **60 words by shortening the setup.** PROOF-88, 91 and 93 stood at 58 to 60 words before the
  addition. The setup was shortened and every printed line and result kept. `the suite's report`
  reads `the report` in all three.
- **The Windows words in PROOF-288 and 289**, as above.
- **The helper `_pytest_entry()` is removed** from `dev/test_run_script.py`. It read the expected
  entry from `references/supported_frameworks.md`; nothing uses it now. PROOF-133's test still
  holds that page to the suggested entries.
- **The second case stays in the test of `evidence` PROOF-88.** The test changes the command to
  a longer one, then to one of the same length. The proof now names the second alone. The first
  assertion was left: it checks a right thing.
- **Spec and test in one commit**, prefix `spec(<name>):`, so no commit stands between a
  rewording and its test.

## What was run

- The four test files: 213 passed, 2 skipped, before the rebase and again after it.
- `bash dev/run_tests.sh --fast`, before the rebase: 927 passed, 9 skipped, `Suites: 1 passed, 0
  failed`. It was not run again after the rebase onto decision 125's one commit.
- `python3 scripts/run/purlin_run.py --test --feature run_script --feature signatures --feature
  package --feature evidence --project-root .`: exit 0, and no line names a test comment to
  correct. The evidence it wrote was restored with `git checkout -- .purlin/evidence` and not
  staged.

## What is left

- Nothing waits on another lane.
- The committed evidence names the seven old test names and, in the audit's findings for
  `run_script` PROOF-288 and 289, the removed helper. Integration's `--test --all --commit`
  rewrites the first; the second stands until those rules are audited again.
- The four rewordings put the audit's entries for their rules out of date, as any rewording does.
