# Strengthening, part b: run_script and signatures

Branch `lane/d124-strong-b`. Seven proofs, each with one planted bug that survived the audit.
All seven were the first of the three ways: the test did not yet assert what the proof names.
No proof was left unchanged and no sharper proof sentence was needed to write an assertion.

Each recorded bug was planted in a scratch copy of the repository by replacing its `before`
lines with its `after` lines. Each `before` was in its file exactly once. Each strengthened test
failed there and passes on the unchanged code. Nothing under `scripts/`, no rule and no proof
changed. `dev/test_run_script.py` (73 tests) and `dev/test_signatures.py` (76 tests) pass whole.

The settle step, `purlin:audit <feature> RULE-N --settle`, was not run: it is left to the
session that owns the evidence.

## run_script

| Rule | Proof | Which | What changed | Seen failing with the bug |
|------|-------|-------|--------------|---------------------------|
| RULE-102 | PROOF-126 | assertion written | The expected JSON array is pytest's entry written out in the test, field by field (`name`, `run`, `report`, `format` `junit`, `files`), in place of the entry read from `frameworks.entry_for`, the code under test. | yes: the printed entry read `"format": "trx"` |
| RULE-103 | PROOF-138 | assertion written | The same three comparisons (the whole output, the files under `.purlin/`, exit 1) now run on two settings files: the one kept in `dev/fixtures/upgrade-0.9.5`, stamped `0.9.2`, and the one stamped `0.9.5` the test had. The test first checks the kept file has no `tests` key and a stamp other than `0.9.5`. | yes: the run printed the no-test-command lines for the kept file |
| RULE-63 | PROOF-133 | assertion written | One project holds what all seven tools leave, written in reverse order. The array that one run suggests is compared, in order, with the page's entries. The two comparisons the test had stay. | yes: the run suggested shell before sql |

Notes:

- PROOF-126 names "pytest's entry" without its fields. The fields in the test are the ones
  the proofs of the written setting already give (`_pytest_entry_in_words`), with the
  `python3` command the proof's second line names.
- PROOF-138: the audit's case, a stamp other than `0.9.5`, is inside the proof's case. The
  settings file this repository keeps of a 0.9.5 project carries `0.9.2`, the release that
  first set that project up, so "as Purlin 0.9.5 wrote it" does not mean a `0.9.5` stamp.

## signatures

| Rule | Proof | Which | What changed | Seen failing with the bug |
|------|-------|-------|--------------|---------------------------|
| RULE-106 | PROOF-214 | assertion written | The answer-word check reads every key of the sign-off file, at any depth, beside every value. | yes: `shown` held the key `y` |
| RULE-110 | PROOF-220 | assertion written | No line from the stop `login RULE-2   hand check` on ends `: ` or `] `, which is how every question the walk asks ends. | yes: `Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] ` was found under the stop |
| RULE-115 | PROOF-230 | assertion written | The lines printed between the first question and `go on: ` are compared with the one finding line: once, and nothing beside it. | yes: the line was printed twice |
| RULE-132 | PROOF-258 | assertion written | The line holds `login`, then rule numbers alone joined by `, `, with `RULE-2` among them as a whole number. | yes: the line read `login RULE-s RULE-1, RULE-2` |

Notes:

- PROOF-258: the line the code prints is `No sign-off: 2 rules do not pass at <sha>: login
  RULE-1, RULE-2. Run purlin:status to see what is left, then purlin:sign.` The words
  `login RULE-2` are never side by side in it, so the assertion reads the name and its list of
  numbers. The proof could give the whole line, as PROOF-256 and PROOF-257 do. A sentence for
  `purlin:spec`, if the owner wants it: "`specs/auth/login.md` holds two lines numbered
  `RULE-2`, and its results are committed at `HEAD`; the walk prints the one line `No sign-off:
  2 rules do not pass at <sha>: login RULE-1, RULE-2. Run purlin:status to see what is left,
  then purlin:sign.`, writes no file and exits 1".
- The audit's other remarks on these proofs (PROOF-126 reads only the last lines, PROOF-214
  finds `login RULE-2` with `in`, PROOF-220 reads "no commit" from the status) are not
  findings and were left as they are.
