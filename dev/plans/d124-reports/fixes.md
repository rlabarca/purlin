# Fixes: three proofs tightened, a timeout covered, a dead end closed

Branch `lane/d124-fixes`, from `main` at `2e8e3fb83`, with `lane/d124-strong-a` and
`lane/d124-strong-b` merged first; both merged clean. No `purlin:test`, `purlin:audit` or
`purlin:sign` was run on this repository, nothing was pushed, and nothing under `.purlin/` is
staged.

## 1. Three proofs tightened

### `signatures` PROOF-258 (RULE-132)

Before:

> `specs/auth/login.md` holds two lines numbered `RULE-2`, and its results are committed at `HEAD`; the walk prints one line beginning `No sign-off:` and naming `login RULE-2`, writes no file and exits 1

After:

> `specs/auth/login.md` holds two lines numbered `RULE-2`, and its results are committed at `HEAD`; the walk prints the one line `No sign-off: 2 rules do not pass at <sha>: login RULE-1, RULE-2. Run purlin:status to see what is left, then purlin:sign.`, writes no file and exits 1

The test, `dev/test_signatures.py::TestTheRefusals::test_a_spec_that_holds_a_number_twice_is_refused_in_one_whole_line`,
is renamed and now compares everything the walk prints with that one line, the sha being the
first seven characters of `HEAD`. The three pattern checks it replaces are each inside the
comparison.

### `ai_audit` PROOF-34 (RULE-40)

Before:

> The tests `test_valid_credentials_return_200` and `test_a_token_comes_back` in one file are both marked for `PROOF-1` and both passed; what the audit reads for `RULE-1` lists exactly those two, the first shown with its own source, `== 200`, and the second with its own, `token`, neither holding the other's

After:

> The tests `test_valid_credentials_return_200` and `test_a_token_comes_back` in `tests/test_login.py` are both marked for `PROOF-1` and both passed; what the audit reads for `RULE-1` lists exactly those two, each named with `tests/test_login.py`, the first shown with its own source, `== 200`, and the second with its own, `token`, neither holding the other's

The test already asserted the file, from lane A. It is renamed to
`test_two_tests_of_one_proof_each_show_their_file_and_own_source`, in the same commit as the
proof.

### `run_script` PROOF-93 (RULE-101), split

Before, one proof:

> `login`, current like `export`, scopes `src/login.py, src/auth/`; `src/auth/token.py` is untracked; the next `--test` exits 0, selects `login` alone, reason `a file is not tracked`, prints `src/auth/token.py is under login's scope and is not tracked, so its content is not part of the evidence until you git add it.` and `Ran pytest on 1 feature.`, the report holding login's test alone

After, two:

> PROOF-93 (RULE-101): `login`, current like `export`, scopes `src/login.py, src/auth/`; `src/auth/token.py` is untracked; the next `--test` exits 0, selects `login` alone, reason `a file is not tracked`, and prints `src/auth/token.py is under login's scope and is not tracked, so its content is not part of the evidence until you git add it.`

> PROOF-290 (RULE-55): `login`, current like `export`, scopes `src/login.py, src/auth/`; `src/auth/token.py` is untracked; the next `--test` with no feature named prints `Ran pytest on 1 feature.`, and the report holds login's test alone

The one test is split in two: `test_an_untracked_file_selects_its_feature_alone_and_is_named`
carries PROOF-93 and `test_an_untracked_file_runs_its_feature_alone` carries PROOF-290. No
assertion was dropped. `> Highest-Proof:` went from 289 to 290.

## 2. A timeout is covered

RULE-1 of `ai_audit` is unchanged: "a proof it plants a bug for with no result recorded" holds
the timeout as it holds the other three ways. One proof is added under it, after PROOF-122.
`> Highest-Proof:` went from 159 to 160.

> PROOF-160 (RULE-1): With the limit lowered to 1 second and a `claude` that takes 3 seconds to answer, `RULE-2`'s entry reads `spot-checked` with the reason `No bug was planted: the model could not be reached: claude timed out after 1 s.`, and nothing has changed since; the audit run again, with a `claude` that answers at once, reads `RULE-2` and starts `claude` exactly `1` time

The test is `dev/test_ai_audit.py::TestWhichRulesAreRead::test_a_rule_whose_call_timed_out_is_read_again_with_one_call`.
It uses the fake `claude` with `sleep=3` and sets `MODEL_TIMEOUT` to 1, as the test of PROOF-25
does, and takes about 3 seconds. No code under `scripts/review/` changed: the code already reads
such a rule again.

Seen failing first: in a scratch copy, line 527 of `scripts/review/ai_audit.py` was changed from
`found['why'] = TIMED_OUT % MODEL_TIMEOUT` to `found['why'] = None`, the bug the audit recorded
for PROOF-122. The new test failed there, on the reason: it read `No bug was planted: the
model's answer for PROOF-2 could not be used: it holds none.` The three cases of PROOF-122's
test passed in that copy, as lane A reported. On the unchanged code the new test passes.

## 3. A dead end is closed

The fault, reproduced in a test before any code changed: `login` and `export` current, then
`src/login.py` changed and a `--test --commit` whose test tool could not start. The next
`--test` printed `Nothing to run: every feature's spec, code and tests match its evidence.
purlin:test --all runs them anyway.` and, under `Left to do:`, `1 rule to test: purlin:test`.

The one home of the decision is `summary.rule_kind`, which `payload.build_payload` calls once
for each rule and keeps as the rule's `left`. `fingerprint.selection`, the one home of the
selection, now reads it: a feature whose newest section here is current is selected where any
of its rules has `left` equal to `to_test`. The reason is built from the same entry of
`summary.KINDS` the status prints, so the two lines use one set of words.

RULE-55 before:

> With no feature named and no `--all`, `--test` and `--audit` run a feature when no section for this operating system exists in either source of its evidence, when the newest such section's fingerprint differs from the one taken now on its spec, its code or its tests, when an untracked file git does not ignore sits under its `> Scope:` or beside one of its marker files, or when its spec names no files; an anchor's code is every file git tracks but Purlin's own records, so an edit to any such file runs every anchor; every other feature is not run and its evidence is left as it was

RULE-55 after:

> With no feature named and no `--all`, `--test` and `--audit` run a feature when no section for this operating system exists in either source of its evidence, when the newest such section's fingerprint differs from the one taken now on its spec, its code or its tests, when that fingerprint matches and the status counts one of the feature's rules under `rules to test`, when an untracked file git does not ignore sits under its `> Scope:` or beside one of its marker files, or when its spec names no files; an anchor's code is every file git tracks but Purlin's own records, so an edit to any such file runs every anchor; every other feature is not run and its evidence is left as it was

The new proof, `> Highest-Proof:` going from 290 to 291:

> PROOF-291 (RULE-55): `login` and `export` are current; `src/login.py` changes, and a `--test --commit` whose test tool cannot start commits login's one result as not run, the status reading `1 rule to test: purlin:test`; the next `--test`, the tool starting again, prints `Selected 1 of 2 features: login (1 rule to test).`, exits 0, and login's `RULE-1` reads `passed`

The test is `dev/test_run_script.py::TestARunCoversWhatTheChangeTouched::test_a_result_left_to_test_selects_its_feature`.
Seen failing first, before the code change, on the line `Selected 1 of 2 features: login (1 rule
to test).`: the run printed `Nothing to run` and the status under it read `1 rule to test:
purlin:test`. It passes with the change.

Pages changed in the same commit: `skills/test/SKILL.md` and `docs/running-and-evidence.md`,
each of which lists the cases a run selects a feature in, and the header of
`scripts/run/purlin_run.py`. No file under `references/formats/` lists those cases, so none
changed and no `Format-Version` moved.

## Every line a person reads that was chosen here

- The reason on the `Selected` line: `1 rule to test`, and `<n> rules to test` for any other
  count. They are the status's own words for the same count, so
  `Selected 1 of 2 features: login (1 rule to test).` and `1 rule to test: purlin:test` say one
  thing.
- In `skills/test/SKILL.md`: "its evidence matches them and the status still counts one of its
  rules under `rules to test`, as after a run whose test tool could not start. The reason reads
  `1 rule to test`;"
- In `docs/running-and-evidence.md`: "its newest run here matches them and the status still
  counts one of its rules under `rules to test`, as after a run whose test tool could not start.
  The reason reads `1 rule to test`;"
- The proof sentences and the reworded rule above.

## Calls made that the brief did not make

- **RULE-55 is reworded; no rule is added.** RULE-55 ends "every other feature is not run", so
  a new rule beside it would have contradicted it. Its audit entry reads `out of date` after
  this.
- **PROOF-290 sits under RULE-55, not RULE-101.** What ran is RULE-55's claim; RULE-101 is
  about what is printed before anything runs. PROOF-88 holds the same pair of results for a
  code change under RULE-55.
- **The new reason is given only where the evidence is current.** A feature already selected
  for `code changed since <sha7>` or `no run on <System> yet` keeps that reason alone: every
  rule of it is to test, and the second reason would repeat the first.
- **The selection builds the status's payload once a run**, and only where at least one feature's
  evidence is current. On this repository that takes about 6 seconds of a run with no feature
  named. Reading the status's answer, in place of a second copy of its decision, is what keeps
  the two from disagreeing.
- **A rule that stays `not run` with nothing to fix by running is selected on every such run.**
  A feature's own rule whose every test skips with `nothing to check:` reads `not run` and is
  counted under `rules to test`, so its feature now runs each time until the test has something
  to check or the rule moves to an anchor. The status named `purlin:test` for it before; the run
  now does what the status says.
- **In PROOF-291's test the suite's command names its Python through the environment**
  (`"$TEST_PYTHON"`), and the tool that cannot start is `false`. The committed command then
  stays the same across the three runs, as it did in the real fault, where a change to the
  command would have put every result out of date and hidden it.
- **The one-line summaries were left as they are**: `docs/getting-started.md` ("`purlin:test`
  runs what changed") and the glossary's entry for `out of date` name two of the cases and
  already left out the untracked file and the spec that names no files.
- **PROOF-34 names a test file's path**, which the guide's "no source or test file path" would
  cut. It is the sentence lane A proposed and the owner chose; the path is what the audit shows
  a person, so it is the observed value here.
- **Each reworded proof is committed with its test**, under `spec(<feature>):`, so no commit
  leaves a test comment to correct.

## Runs

`dev/test_signatures.py`, `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`,
`dev/test_run_script.py`, `dev/test_skill_test.py` and `dev/test_purlin_docs.py`: 250 passed.
`bash dev/run_tests.sh --fast`: 970 passed, 9 skipped, 0 failed; `Suites: 1 passed, 0 failed`.

## Next

`purlin:test` for `signatures`, `ai_audit` and `run_script`, then the settle of lanes A and B.
