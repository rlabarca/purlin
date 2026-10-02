# Strengthening, lane A

Branch `lane/d124-strong-a`, from `main` at `2e8e3fb83`. Step 2 of "Strengthening a weak rule" for
eight proofs. No code under `scripts/` changed, no rule or proof changed, and no test lost an
assertion. `purlin:test` and `purlin:audit --settle` were not run: they are the next step.

Each recorded bug was planted in a scratch copy of the repository by replacing its `before` lines
with its `after` lines. Every `before` was in its file exactly once.

| Feature | Rule | Proof | Which of the three | Seen failing with the bug |
|---------|------|-------|--------------------|---------------------------|
| `ai_audit` | RULE-1 | PROOF-122 | already asserts what the proof names | no: passes, 3 of 3 |
| `ai_audit` | RULE-3 | PROOF-14 | already asserts what the proof names | yes, with no change |
| `ai_audit` | RULE-4 | PROOF-55 | assertion written | yes |
| `ai_audit` | RULE-40 | PROOF-34 | assertion written | yes |
| `planted_bug` | RULE-10 | PROOF-12 | already asserts what the proof names | no: passes |
| `specs` | RULE-17 | PROOF-19 | assertion written | yes |
| `evidence` | RULE-7 | PROOF-88 | assertion written | yes |
| `evidence_writer` | RULE-16 | PROOF-41 | already asserts what the proof names | no: passes |

## Assertions written

**`ai_audit` PROOF-55**, `dev/test_ai_audit.py::TestTheCall::test_six_rules_are_each_asked_once_and_answered_in_order`.
Two findings, one change. The spot test said the test mocks `audit_all()`, and the bug starts
`claude` twice only when the audit starts it itself. The second half of the test no longer
replaces `audit_all`. It writes a `claude` first on PATH that answers the later rule sooner with
`saw RULE-N` and keeps one file per start, runs the whole audit over six rules, and asserts the
starts read exactly `RULE-1` to `RULE-6`, one each. The check that each entry holds `saw RULE-N`
for its own rule is kept. The first half, which hands the real `audit_all` a stand-in runner, is
unchanged. With the bug: 12 starts, the test fails. Without: passes.

**`ai_audit` PROOF-34**, `dev/test_ai_audit_tests_named.py::TestEachTestShowsItsOwnSource::test_two_passing_tests_of_one_proof_each_show_their_own_source`.
The proof's two tests are "in one file" and the reading "lists exactly those two". The test now
asserts each listed test reads `PROOF-1`, `tests/test_login.py` and not manual, and that the
request holds the line `Test for PROOF-1: tests/test_login.py::<name>` once for each name. With
the bug the file reads `None` and the test fails. The proof does not spell the file's name; the
assertion takes it from the proof's own setup. A sentence that names it, if wanted:
"The tests `test_valid_credentials_return_200` and `test_a_token_comes_back` in
`tests/test_login.py` are both marked for `PROOF-1` and both passed; what the audit reads for
`RULE-1` lists exactly those two, each named with `tests/test_login.py`, the first shown with its
own source, `== 200`, and the second with its own, `token`, neither holding the other's".

**`specs` PROOF-19**, `dev/test_specs_reader.py::TestRuleText::test_a_line_break_in_a_rule_keeps_its_hash`.
Five forms of the break after `expire` join the three: a bare carriage return, a bare carriage
return with the next line indented, and a space left before `\n`, `\r\n` and `\r`. Each hash is
compared with the unbroken rule's. With the bug the bare carriage return gives another hash and
the test fails.

**`evidence` PROOF-88**, `dev/test_evidence_reader.py::test_a_test_command_changed_to_one_as_long_is_out_of_date_on_tests`.
The fingerprint is stored with `python3 -m pytest -x {files}`, read as current, then the command
is changed to `python3 -m pytest -X {files}`, the same length, and the section must read out of
date on exactly `tests`. With the bug it reads current and the test fails.

## Nothing changed

**`ai_audit` PROOF-122.** The proof names three ways the model is not reached: `claude` exited
with an error, was not on PATH, gave no answer. The test tries all three and asserts the next run
reads `RULE-2` and starts `claude` exactly 1 time. The bug is on a fourth way, a `claude` that
runs past its limit, which the proof's case does not name, so none of the three reaches it.
`ai_audit` PROOF-25 holds the timeout's reason for RULE-39; no proof holds that a rule left
`spot-checked` by a timeout is read again. If that is wanted it is a proof to add with
`purlin:spec`, not a change to this test.

**`ai_audit` PROOF-14.** The test as it stands on `main` already fails with the bug in place. It
sends a request holding `café → 日本`, keeps the bytes that arrive on standard input and compares
them with the request; `encoding='ascii'` puts `?` there. The entry was recorded against an
earlier test (commit `818e27dcc`), before that check was written. A settle will read `caught`.

**`planted_bug` PROOF-12.** The model's claim about the result is wrong. With `return ''` the
whole file runs in the copy and the test of `PROOF-2` fails, but `_run_tests` reads only the
proof's own entries, and a run's `failures` hold only a suite that timed out or left no report,
never a failing test. The result for `PROOF-1` is still `survived`, which is what the proof
names, and the test compares it. That another proof's test is not started is `planted_bug`
PROOF-50's case.

**`evidence_writer` PROOF-41.** The bug sits on a path no run reaches. `evidence.local_machine()`
is only the default of `build_section(machine=None)`, and `purlin_run.py` always passes
`machine=machine_name()`, its own function. A `--all --test` run writes the host name with the bug
in place, so the proof's result holds and the test, which compares `machine` with
`platform.node()`, is right to pass.

## Runs

`dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_specs_reader.py` and
`dev/test_evidence_reader.py`, each whole: 128 passed, 1 skipped (the Windows-only test).

## Next

`purlin:test` for `ai_audit`, `specs` and `evidence`, then `purlin:audit <feature> RULE-N --settle`
for all eight rules. Expected: `caught` for PROOF-14, PROOF-55, PROOF-34, PROOF-19 and PROOF-88;
"did not break what the proof says" and a new bug for PROOF-122, PROOF-12 and PROOF-41.
