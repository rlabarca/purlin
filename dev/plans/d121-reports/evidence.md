# Lane `evidence`, decision 121

Branch `lane/d121-evidence`, one code commit, `ecfb08ffe`, on `main` at `fe512e267`. Nothing
pushed, no audit, no sign-off, no full sweep.

Each spec's `> Highest-*` on the tree matched the plan's table, so every number is the plan's.

## Test numbers

`python3 -m pytest dev/test_run_script.py dev/test_evidence_writer.py dev/test_evidence_reader.py dev/test_fingerprint.py dev/test_reports.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before, on `main` | 187 | 4 | 1 |
| After | 203 | 2 | 1 |

14 tests added: 13 marked, 1 with no marker (item 1). The three red tests of
`dev/test_evidence_reader.py` pass.

**Still red, both waiting on lane `audit`:**

- `evidence_writer PROOF-54`, `dev/test_evidence_writer.py::test_an_audit_run_writes_the_entry_for_the_rule_it_read`.
  It is written to the plan's words: the fake model's reply is in K3's shape
  (`=== PROOF-1 ===`, `no break: the code has nothing to change`, `=== reading ===`), and it
  expects `code_hash`, `verdict` `spot-checked` and the one `no_bug` sentence
  `No bug was planted: the model found no change that would break PROOF-1: the code has nothing to change.`
  Today it stops at `code_hash`, which the audit writes as `''`.
- `run_script PROOF-87`, `dev/test_run_script.py::TestTheAuditExitCode::test_a_test_with_no_assertion_is_left_to_strengthen`.
  Not in the brief's list of expected red, and red on `main` before this lane. The audit writes
  no `code_hash`, the entry reads out of date, the base commit hides it, and the last line is
  no longer `  1 rule to strengthen: purlin:build`. Not changed here: it clears when `audit`
  hands `code_hash` over (and `surfaces` takes the hiding line out).

`dev/test_states.py`, `test_export.py`, `test_signatures.py`, `test_collaboration.py` and
`test_summary.py` were also run on this branch: 179 passed, 1 skipped.

## 1. A kept slow result (plan 2.1, K1)

**Reproduced first.** `run_script PROOF-281`'s test, on `main`'s code:

```
>       assert slow.get('kept') == {'commit': taken['commit'], 'at': taken['at'], ...
E       AssertionError: {'env': None, 'id': 'PROOF-2', 'manual': False, 'result': 'pass', ...}
E       assert None == {'commit': 'bda3219a7b32c17b35c6111d9d2cfe84d18638ae', 'at': '2026-10-01T22:55:38Z', 'machine': 'Richs-MacBook-Pro.local', 'email': 'dev@example.com'}
```

The assertions before it passed: the section's `commit` was the new one and `PROOF-2` read
`pass`, with no key saying it ran at `<c>`. That is the re-stamping.

**Changed.**

- `purlin_run.keep_slow_results`: a held entry given an earlier result carries `kept`, copied
  from the entry it was kept from where that one has it, else filled from that section's
  `commit`, `at`, `machine` and `email`. A kept `fail` and a kept `nothing to check` carry it
  too.
- `evidence.build_section` (the writer): writes `kept` on the entry it lists
  (`KEPT_KEYS`, `_with_kept`).
- `evidence._same_observation`: compares `dirty`; leaves `kept` out, in one direction. A run
  that carried a result over equals the section that took it, so the file stays as it was with
  no `kept` in it (`run_script PROOF-279`, `evidence_writer PROOF-91` hold). A section on disk
  that holds an entry as `kept` is replaced by a run that took that result itself.

**The one direction is a call of this lane.** With `kept` left out both ways, as plan 2.1
words it, `purlin:test --all --commit` on the same code as a section holding a kept result
would compare equal, leave the file with `kept` in it, and the sign-off would keep refusing
after the very command it names. `dev/test_run_script.py::TestSlowProofs::test_a_full_run_takes_a_kept_result_again`
holds this and carries no marker, since the plan gives it no proof. A proof for it, if wanted,
under `run_script RULE-106`: "After that plain run, `--all --test --commit` with nothing
changed starts the slow test, and the evidence lists `PROOF-2` as `pass` with no `kept`".

**Rules and proofs, word for word.**

- `run_script` RULE-106: A run that leaves a slow proof's test out keeps the result the section it replaces holds for that proof where that section was taken over the same spec, code and tests, and marks it `kept` with the `commit`, `at`, `machine` and `email` of the run that took it, so the status keeps counting it and the sign-off does not; where it was taken over others, the proof reads `not run`
- `run_script` PROOF-281 (RULE-106): In a git checkout, `--all --test --commit` passes `feat`'s slow `PROOF-2` at the commit `<c>`; `README.md`, which no scope names, is changed and committed; `--feature feat --test --commit` runs; the evidence lists `PROOF-2` as `pass` with `kept` naming the commit `<c>`, and the section's own `commit` is the new one
- `evidence_writer` RULE-31: A section that saw the same results over the same fingerprint, on the same machine and with the same `dirty`, as the one on disk leaves the file byte for byte as it was, `at` included, where every commit since the one the section names changes only paths under `.purlin/`, so a second run finds nothing new to commit; any other section replaces it, with its own `at`, `commit`, `dirty` and `email`
- `evidence_writer` PROOF-97 (RULE-31): `--all --test` runs while `notes.txt` is written and not added to git, and the section's `dirty` is true; `notes.txt` is deleted and `--all --test` runs again on the same commit; the section's `dirty` is false
- `evidence_writer` PROOF-98 (RULE-19): In a git checkout where the spec `feat` and `src/other.py` are both edited and not committed, `--all --test --commit` commits `specs/a/feat.md` and not `src/other.py`, which `git status` still lists as changed, and the section's `dirty` is true

PROOF-97 failed on `main`'s code (the section kept `dirty` true); PROOF-98 needed no code.

## 2. The `tests` setting (plan 2.3, K6)

`fingerprint.tests_hash` adds the line `tests-setting <sha256>` where `.purlin/config.json`
holds `tests` (`tests_setting_line`, new): the sha256 of the setting as JSON with sorted keys
and no spaces, read from the working tree. A project with no `tests` key hashes as before.
Every section of a project that has the key goes out of date on `tests` once, as plan 8 step 3
says.

- `evidence` RULE-7: The `tests` part covers every tracked test file, one a suite of the `tests` setting names, carrying a marker for the feature, and the `tests` setting itself; editing such a file or that setting changes `tests` and no other part; a marker for another feature is not counted, and neither is the settings file's `version`
- `evidence` PROOF-88 (RULE-7): A `local` section of `login` stores the fingerprint taken now; the `run` command of the `tests` setting in `.purlin/config.json` is then changed; checked against a fingerprint taken again, the section reads out of date on exactly `tests`
- `evidence` PROOF-89 (RULE-7): A `local` section of `login` stores the fingerprint taken now; the `version` in `.purlin/config.json` is then changed from `0.10.0` to `0.10.1`; checked against a fingerprint taken again, the section reads current

**Left open, not built.** An anchor's `code` part is every tracked file but
`.purlin/evidence`, so it covers `.purlin/config.json` whole. A changed `version` alone
therefore puts every anchor's sections out of date on `code`, today and after this lane. Plan
2.3 says a change to `version` alone ends no result; that holds for a feature and not for an
anchor. No decision names it, so it is left.

## 3. A marker inside a string or a here document

No code change: `markers.py` already reads it so. One rule and one proof now hold it.

- `reports` RULE-38: A marker-shaped line inside a string of a test file, or inside a here document of a shell file, is not a marker and ties nothing
- `reports` PROOF-119 (RULE-38): A Python test file holds `# purlin: login PROOF-1` on line 2, inside a triple-quoted string, and `# purlin: login PROOF-2` as a comment on line 5 above the passing `test_ok`; one marker is read, `PROOF-2` at line 5, and the evidence holds no `pass` for `PROOF-1`
- `reports` PROOF-120 (RULE-33): `login`'s `RULE-1` has `PROOF-1`, and a passing test on line 3 is marked `purlin: login RULE-1`; the run prints `tests/test_login.py:3 names login RULE-1, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.`, exits 1, and the evidence holds no `pass` under `RULE-1`

In PROOF-120's test the comment is on line 3 and the test on line 4: the line the run prints is
the comment's. The proof has no test for the here document half of RULE-38.

## 4. The audit entry's `code_hash` and the four-part comparison in the reader

The reader was the base commit's (B2). This lane wrote the rule, the proofs and the tests.

- `evidence` RULE-16: The audit entry for a rule is the one either source holds, a current one before one out of date and then the later `at`; it is current while its `rule_hash`, `proof_hash`, `test_hash` and `code_hash` all equal the ones asked for, whatever its `commit`, and otherwise names each part that differs, `rule`, `proof`, `test` or `code`
- `evidence` PROOF-22 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p`, `t` and `c`, whose commit is not the repository's HEAD; asked for RULE-1 with `r`, `p`, `t` and `c`, the reader returns it, naming the source `local` and carrying that commit
- `evidence` PROOF-58 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p`, `t` and `c`; asked for RULE-1 with `r`, `p`, `t2` and `c`, the reader returns the entry as out of date on exactly `test`
- `evidence` PROOF-86 (RULE-16): Both files hold an entry for RULE-1 with the hashes `r`, `p`, `t` and `c`: `ci` reads `strong` at `2026-09-01T00:00:00Z` and `local` reads `weak` at `2026-09-02T00:00:00Z`; asked for RULE-1 with those hashes, the reader returns the `weak` entry, naming the source `local`
- `evidence` PROOF-87 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p`, `t` and `c`; asked for RULE-1 with `r`, `p`, `t` and `c2`, the reader returns the entry as out of date on exactly `code`
- `evidence_writer` RULE-12: `--audit` writes one `audit.rules` entry for each rule the audit read, carrying the rule, proof, test and code hashes it read, its `verdict`, `strong`, `weak` or `spot-checked`, its `findings`, its `no_bug`, its `breaks`, its `explanation`, the `model` that answered, the sha256 of the `criteria` it was sent, `at` and `commit`, and leaves every other rule's entry as it was
- `evidence_writer` RULE-14: An audit entry that repeats the one already there, with the same four hashes, `verdict`, `findings`, `no_bug`, `model` and `criteria`, is left as it was, `at` and `commit` included; an entry that differs in any of them, the model that answered included, replaces it
- `evidence_writer` PROOF-54 (RULE-12): In a git checkout whose model `claude-fake-1` answers `no break: the code has nothing to change` for `PROOF-1`, `--all --audit` writes an entry for `RULE-1` with the four hashes status gives it, `verdict` `spot-checked`, empty `findings`, one `no_bug` sentence, `breaks` reading `PROOF-1` `not made`, `model` `claude-fake-1`, the criteria's sha256 and HEAD's sha as `commit`

**PROOF-86 is weaker than it reads.** `local` is both the later entry and the source read
first, so a reader that took the first source and ignored `at` would pass it. The test fails
when the last source read wins. A case that tells the two apart has `ci` the later one; the
proof's words are the plan's and were not changed.

**`kept_audits` stays at three hashes.** `evidence_writer` RULE-26 ("each audit entry whose
rule, proof and test are the rule's current ones") is not reworded by the plan, so a run over a
conflicted file still keeps an entry by its rule, proof and test hashes; one whose `code_hash`
differs is kept and reads out of date. The docstrings saying "three hashes" in
`scripts/run/evidence.py` are true and stand.

## 5. An NUnit `[TestCase]` slow test

`markers.Test` gains `rows`, set by `cs_tests` for a method under `[TestCase]` or
`[TestCaseSource]` (`_CS_ROWS_RE`), alone or beside another attribute. `frameworks.leave_out`
for `dotnet` sends such a test to `started` and names it in no filter. Before, the run added
`--filter 'FullyQualifiedName!=Shop.Tests.CartTests.ChecksOut'`, which matches no row, printed
`Left out 1 slow proof`, and the test ran all the same.

- `run_script` RULE-105, second sentence: Where a suite's command is none of these tools', already carries that option, the option would also leave out a test that is not slow, or the test is one NUnit names row by row, under `[TestCase]` or `[TestCaseSource]`, the slow test is started, its result counts, and the run prints `Started 1 slow test in the <suite> suite: its command gives Purlin no way to leave one test out.`, or `<n> slow tests` for any other count
- `run_script` PROOF-285 (RULE-105): A slow test declared under `[TestCase(1)]` in a dotnet suite is started: the command the run starts for that suite carries no `--filter`, and the run prints `Started 1 slow test in the dotnet suite: its command gives Purlin no way to leave one test out.` and no `Left out` line

Its test starts no real `dotnet`: the suite's command is `bash ./dotnet test --logger trx
--results-directory {report}`, and `./dotnet` is a script that writes down its arguments.

## 6. Three proofs with no code change

- `run_script` PROOF-282 (RULE-100): In a git checkout whose one marked test fails, `--all --test` exits 1; with nothing changed, `--test` with no feature named prints `Nothing to run`, starts no suite, and exits 1
- `run_script` PROOF-283 (RULE-12): `feat`'s `PROOF-2` is tagged for this machine's system and its test fails; `--all --ci` exits 1, and `.purlin/evidence/ci/feat.json` lists `PROOF-2` as `fail` and reads `RULE-1` `failed`
- `run_script` PROOF-284 (RULE-98): Started in a Purlin project as `--all --test --project-root ''`, the run exits 2, prints `purlin: --project-root needs a directory, not an empty value.`, and writes nothing under that project's `.purlin/`

## 7. The format

`references/formats/evidence_format.md`, `> Format-Version: 11`, in the commit of its code.
`schema` stays `purlin-evidence/2`. The lines chosen, word for word:

- The `dirty` row: whether the working tree had changes that were not committed, outside `.purlin/`. It decides no cell: the fingerprint does. A run over a tree whose `dirty` differs replaces the section
- The new `kept` row: optional: present only on an entry whose result this run did not take, a slow proof's test it left out. It names the run that took the result: `commit`, the full sha, `at`, `machine` and `email`, as that run's section held them
- Under the slow bullet: The entry then keeps that result and carries `kept`: the `commit`, `at`, `machine` and `email` of the section the result was taken in, or the `kept` that entry already carried. The section's own `commit`, `at`, `machine` and `email` are this run's.
- A reader counts a kept `pass` as a `pass`, so the status keeps counting it. The sign-off counts no kept result, whatever commit it names: it asks for `purlin:test --all --commit`, which takes the result again and writes the entry with no `kept`.
- The `tests` row: every tracked test file carrying a marker for the feature, each as `<path> <blob>`, and, where `.purlin/config.json` holds `tests`, the line `tests-setting <sha256>`, the sha256 of that setting as JSON with sorted keys and no spaces. A test file is one a suite of the `tests` setting names. The setting is read from the working tree, so changing a suite's command puts every feature's sections out of date on `tests`; the file's layout and its other keys, `version` included, change nothing
- "How a writer merges", first bullet, gains: Its entry is marked `kept`.
- "Retention": A run that sees the same results over the same fingerprint on the same `machine`, with the same `dirty`, as the section already there leaves the file byte for byte as it was, `at`, `commit` and `email` included, ... and the new paragraph: `kept` is left out of that comparison in one direction: a result the run carried over is the result the section on disk already holds, so the file stays as it was, with no `kept` in it. A result the run took itself replaces an entry the section on disk holds as `kept`.
- The example gains a third proof entry, `PROOF-3`, with `kept`.

No line the run prints was added or changed.

## Each proof fails when the code is broken

Each run once, then `git checkout -- <file>`:

| Proof | The break | Its test |
|---|---|---|
| `run_script` 281 | `keep_slow_results` writes no `kept` | fails |
| `run_script` 282 | `_nothing_to_run` exits 0 | fails |
| `run_script` 283 | the `--ci` arm returns 0 | fails |
| `run_script` 284 | the empty `--project-root` is let through | fails |
| `run_script` 285 | `leave_out` ignores `rows` | fails |
| `evidence_writer` 97 | `_same_observation` leaves `dirty` out | fails |
| `evidence_writer` 98 | the section's `dirty` is always false | fails |
| `evidence` 22 | the parts compared the wrong way round | fails |
| `evidence` 58 | an entry out of date is not returned | fails |
| `evidence` 86 | the last source read wins | fails |
| `evidence` 87 | `code` left out of `AUDIT_PARTS` | fails |
| `evidence` 88 | `tests_hash` adds no setting line | fails |
| `evidence` 89 | the whole settings file is hashed | fails |
| `reports` 119 | a string's lines are read as comments | fails |
| `reports` 120 | `RULE_HAS_PROOFS` is not reported | fails |
| the test with no marker | `kept` left out both ways | fails |

`evidence_writer` PROOF-54 could not be shown this way: it is red until lane `audit` lands.

## Edits needed in files this lane does not own

1. `references/supported_frameworks.md`, which no lane's list names. Line 197, the `dotnet`
   row, last sentence. Before: `A test whose name carries its arguments, as NUnit's `TestCase`
   does, is not matched: it runs, and its result counts`. After: `A test NUnit names row by
   row, under `[TestCase]` or `[TestCaseSource]`, cannot be named by one filter, so it is
   started`. And the list under it: `In four cases` becomes `In five cases`, with the bullet
   `- the test is one NUnit names row by row, under `[TestCase]` or `[TestCaseSource]`;`.
2. Lane `signoff`, `package._results`: `kept` is as K1 gives it. A field the earlier section
   did not hold is written as `''`, never left out.
3. Lane `signoff`, `package.only_records_between`: the writer's `same_code_in` calls it, so
   once it reads a changed `tests` setting as a change to the code, the writer follows with no
   edit here.
4. Lane `words`: the sentences of plan 6.7 on `kept` and the `tests` setting are theirs; none
   of this lane's files quotes them.

## Left open

- A proof for the full run that takes a kept result again (item 1).
- An anchor's `code` part and the settings file's `version` (item 2).
- PROOF-86's case (item 4).
- `run_script PROOF-87`, red until `audit` and `surfaces` land.
