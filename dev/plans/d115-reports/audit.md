# Lane `audit`, round 1: report

Branch `lane/d115-audit`, from `d115/base` at `e2c3023d4`. Spec: `ai_audit` (16 rules, 37 proofs).
Files written: `scripts/review/audit_run.py`, `scripts/review/ai_audit.py`,
`references/review_criteria.md`, `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, this
report. `scripts/review/marked_tests.py` needed no change. No file under `specs/` changed.

## Tests

`python -m pytest dev/test_ai_audit.py dev/test_ai_audit_tests_named.py -q`

| When | Passed | Failed | Errors | Skipped |
|---|---|---|---|---|
| Before the first change, at `d115/base` | 18 | 9 | 55 | 0 |
| After the last change | 30 | 7 | 0 | 0 |

No test skipped; no tool was missing. PROOF-82 is tagged `@env(windows)`; its test runs on every
system and checks `claude.cmd` only on Windows, so its evidence counts only from a Windows run.

The 7 that fail all wait on another lane:

| Proof | Test | Waits on |
|---|---|---|
| `ai_audit PROOF-95` | `test_a_spot_finding_makes_the_rule_weak_though_its_bug_was_caught` | `spot` (`plain_checks.check`, `targeted_break.break_proof`), `evidence` (K2 `write_audit`, `audit_entry`) |
| `ai_audit PROOF-96` | `test_a_bug_that_survives_makes_the_rule_weak_with_its_finding` | `spot`, `evidence` |
| `ai_audit PROOF-98` | `test_the_findings_and_the_explanation_are_kept_apart` | `spot`, `evidence` |
| `ai_audit PROOF-106` | `test_the_prompt_holds_the_spot_tests_finding_after_the_test` | `spot`, `evidence` |
| `ai_audit PROOF-97` | `test_no_spot_finding_and_every_bug_caught_is_strong_whatever_claude_says` | `spot` (a caught bug needs the real `break_proof`), `evidence` |
| `ai_audit PROOF-100` | `test_a_caught_bug_is_kept_while_its_test_and_code_stand` | `evidence` |
| `ai_audit PROOF-102` | `test_an_anchors_rule_gets_no_planted_bug` | `evidence` |

Every one fails today on `write_audit() missing 2 required positional arguments: 'mutation' and
'mutation_ran'`: `audit_run` calls K2's `evidence.write_audit(project_root, source, feature, info,
entries)`, and `d115/base` still carries the old signature. The five on `spot` also need the real
spot tests and planted bug. To check my side, I ran all 37 once with K2's two signatures patched
into `scripts/run/evidence.py` and small stand-ins in `plain_checks.check` and
`targeted_break.break_proof`, none of it committed and all of it restored with `git checkout`:
37 passed. With the same set-up, making the verdict ignore a surviving bug failed PROOF-96's test
(`assert entry['verdict'] == 'weak'`), and `git checkout -- scripts/review/audit_run.py` brought
it back to 37 passed.

PROOF-97, PROOF-100 and PROOF-102 were not on the coordinator's list of waits; they wait as above.

## Section 4's row

| | Gone | Reworded | Added |
|---|---|---|---|
| As found (`test_ai_audit.py` 54, `test_ai_audit_tests_named.py` 3) | 57 | 13 | to add: 10 |
| As left | 0 | 0 | 10 added: `ai_audit` 95, 96, 97, 98, 99, 100, 102, 103, 104, 106 |

Appendix A's script over both files, last line: `0 gone, 0 reworded, 37 right as they stand.`
Each of the spec's 37 proofs has exactly one test comment.

K15's greps (`gate`, `--release`, `passed/`, `tests.md`, `mutation`, `mutmut`, `stryker`,
`min_strength`, `audit_parallel`, `purlin:export`, `does not apply`, `settled:`,
`purlin-package/3`, `hard_gates`) over the six files find nothing. No emoji.

## Reworded comments

- `dev/test_ai_audit.py:226 ai_audit PROOF-4 fixed`: the rule is checked against `audit_run.rules_to_read`, and the test asserts the entry's commit is HEAD (its code), not only its hashes.
- `dev/test_ai_audit.py:266 ai_audit PROOF-11 fixed`: no `Test strength 90%.` line; asserts the rule, proof, test and its line come after the criteria in that order.
- `dev/test_ai_audit.py:303 ai_audit PROOF-82 fixed`: the fake answers `- read to the end` and the test asserts that explanation, where it read a `strong` verdict; PROOF-13's comment, gone, left the test.
- `dev/test_ai_audit.py:354 ai_audit PROOF-55 fixed`: the answers are explanation lines, `saw RULE-1` first and `saw RULE-6` last, with no `settled:` line.
- `dev/test_ai_audit.py:417 ai_audit PROOF-38 fixed`: answer `- The test reads the status.` then `notes:`; asserts that explanation, that one note, and no verdict.
- `dev/test_ai_audit.py:696 ai_audit PROOF-23 fixed`: the reasons are the whole answer for two different rules; no verdict word in it.
- `dev/test_ai_audit.py:709 ai_audit PROOF-24 fixed`: the answer is only the reason, with no explanation.
- `dev/test_ai_audit.py:730 ai_audit PROOF-72 fixed`: the fake answers `- The test reads the status.`; asserts that explanation and that `.purlin/`, runtime included, is unchanged.
- `dev/test_ai_audit.py:794 ai_audit PROOF-29 fixed`: no strength line; asserts each printed line whole, `  Weak.`, the finding and `  Read by unknown at 2026-09-13T12:05:00Z.`.
- `dev/test_ai_audit.py:815 ai_audit PROOF-87 stated`
- `dev/test_ai_audit.py:830 ai_audit PROOF-33 fixed`: runs `--feature login --rule RULE-1` and asserts the first line is exactly `login RULE-1`.
- `dev/test_ai_audit_tests_named.py:65 ai_audit PROOF-34 fixed`: asserts both tests of `PROOF-1` read `pass` before reading their sources.
- `dev/test_ai_audit_tests_named.py:83 ai_audit PROOF-35 stated`

## Tests deleted

Each carried only a comment no spec has, and none could show a proof of `ai_audit` that had no
test.

`dev/test_ai_audit.py`: `test_a_passing_rule_with_no_entry_is_read`,
`test_a_rule_whose_test_failed_is_not_read`, `test_a_rule_whose_one_proof_is_manual_is_not_read`,
`test_an_anchors_rules_are_read_once_each_as_the_anchors`,
`test_a_passing_rule_is_read_at_the_gate_passed`, `test_a_passing_rule_is_read_at_the_gate_signed`,
`test_a_rule_whose_text_changed_is_read_again`, `test_a_rule_whose_proof_changed_is_read_again`,
`test_a_rule_whose_test_changed_is_read_again`, `test_the_test_source_is_shown_beside_the_rule`,
`test_a_manual_proof_has_no_test_where_a_test_would_be`, `test_a_rule_that_is_not_there_is_not_read`,
`test_the_strength_is_read`, `test_no_measured_strength_prints_nothing_of_strength`,
`test_a_pattern_holding_a_brace_a_slash_and_quotes`, `test_a_pattern_with_an_escaped_slash`,
`test_braces_in_comments_do_not_cut_a_body`, `test_two_one_line_tests_that_divide`,
`test_the_prompt_names_the_strength_and_no_minimum`,
`test_the_prompt_says_in_words_that_no_strength_was_measured`,
`test_an_anchors_prompt_ends_on_the_anchor_line`, `test_an_anchors_prompt_names_no_strength`,
`test_the_prompt_asks_for_observations_and_bars_a_recommendation`,
`test_the_prompt_asks_for_notes_on_a_long_or_double_proof`, `test_one_call_per_rule_and_four_at_once`,
`test_the_number_at_once_is_what_it_is_given`, `test_fewer_rules_than_the_number_all_run_together`,
`test_settled_with_nothing_found_is_strong`,
`test_settled_with_a_line_is_weak_and_the_line_is_the_finding`,
`test_not_settled_is_undecided_with_its_reason`, `test_a_finding_with_no_settled_line_is_no_answer`,
`test_an_empty_answer_is_no_answer`, `test_the_model_that_wrote_most_is_named_when_listed_first`,
`test_the_model_named_follows_the_counts_not_the_name`, `test_a_top_level_model_is_named`,
`test_a_note_is_not_a_finding`, `test_an_answer_with_no_settled_line_twice_is_no_answer`,
`test_a_second_answer_that_settles_is_the_answer`, `test_reading_a_rule_writes_no_file`,
`test_help_exits_zero_and_prints_the_usage`, `test_no_feature_exits_two`,
`test_an_unknown_feature_exits_one`, `test_each_note_follows_the_findings`,
`test_a_rule_no_audit_has_read_says_so`, `test_a_strong_answer_with_nothing_found_says_so`,
`test_a_strong_answer_with_a_finding_prints_it`, `test_an_undecided_answer_says_the_rule_reads_weak`,
`test_a_manual_proof_prints_manual_under_test`, `test_the_strength_shows_its_whole_number_part`,
`test_a_project_root_that_is_not_a_directory_exits_two`, `test_one_rule_named_prints_that_rule_alone`,
`test_a_feature_alone_prints_every_rule`.

`dev/test_ai_audit_tests_named.py`: `test_a_name_with_a_parameter_finds_its_own_test`,
`test_a_name_with_a_class_before_it_finds_its_own_test`,
`test_a_typescript_name_with_a_prefix_finds_its_own_test`.

That is 55 tests; the other 2 gone comments, `PROOF-13` and `PROOF-83`, came off tests that kept a
proof of their own (82 and 25). No test file imports `FIRST_GATE` or `SIGNING_GATE` now.

## Lines a person reads that I chose

From section 6, used as written: the cost line `The model was asked 31 times for 12 rules: $1.87 in
all, $0.16 a rule.` (with `1 time`, `1 rule`; left out where no answer carried a cost), and
`PROOF-1: no bug was planted: <why>.`, printed and not a finding.

Chosen here, printed by `audit_run.run`:

- Each rule read, its name and verdict: `login RULE-2   weak` (the `AUDIT_LIST` spacing of K8), then each finding on its own line indented two spaces, then each `  PROOF-N: no bug was planted: <why>.`
- Where the model's reading could not be reached: `2 rules were read without the model's explanation: claude is not on PATH. Run purlin:audit --all once it can be reached.` (`1 rule was read ...` for one).
- Where no rule of the features selected passes its tests, in place of the share: `The audit found no rule that passes its tests.`

Printed by `ai_audit.py --feature`: under `What the audit found`, each sentence of the entry's
`explanation` after the findings, indented four spaces.

Sent to the model, not printed: the reading prompt ends on `Findings:` and one `- <finding>` line
each, or `none`; the planted bug's request opens with `BUG_INSTRUCTION`, which gives K9's answer
shape.

## Differences from section 3's contracts

- **`targeted_break.break_proof(..., proof, ...)`.** K9 gives `ask(request)` a request holding
  `rule` and `rule_text`, but `break_proof`'s arguments carry neither. `audit_run` passes `proof` as
  `{'id', 'text', 'rule', 'rule_text'}`, so `break_proof` can fill the request. `spot` should read
  them from there.
- **`ai_audit.ask_for_bug(project_root, request, spent=None, runner=None)`.** Two optional
  arguments beyond K9: `spent`, a list that gains `{'cost_usd', 'seconds'}` per call so
  `audit_run` can write the cost file, and `runner` for a test. `audit_run` hands `break_proof`
  `functools.partial(ask_for_bug, project_root, spent=...)`, which takes `ask(request)` as K9 says.
  The request's `files` may be paths, which `ask_for_bug` reads from the project, or dicts with
  `path` and `text`.
- **`ai_audit.reading_for(..., findings=())`, `is_read(..., code_changed=False)`,
  `audit_all(..., parallel=AUDIT_PARALLEL)`.** Arguments added with defaults; `run`'s old callers
  in `purlin_run.py` go with K10.
- **`break_key`'s two parts.** `test_source_hash` is the sha256 of the sorted lines
  `<file> <name> <sha256 of its source>` over the proof's own tests; `code_part` is
  `fingerprint.code_part` for the feature.
- **A rule's last planted bugs** are read from the newest `audit.rules` entry in either evidence
  file, whatever hashes it was written for, since a rule whose text changed has no current entry
  but keeps its bugs (RULE-36).
- **"The feature's code changed since that entry"** (RULE-1) is `git diff --quiet <entry commit> --
  <scope pathspecs>`, the working tree included; for an anchor, every path but the records
  `fingerprint.RECORDS` excludes.
- **The share's percent is rounded down**, as the old strength line was: 2 of 3 reads `66%`. No
  spec fixes the rounding.

## Left open, unbuilt, or in a file I do not own

- **Call left open, built one way: an entry is written when the model cannot be reached.** RULE-33
  sets the verdict from the spot tests and the planted bugs alone and RULE-39 says no explanation
  is recorded, so the entry is written with `explanation` `[]`, `model` `unknown` and `criteria` the
  file's sha256. Where `claude` is not on the path every planted bug also reads `not made`, so such
  a rule reads `strong` on the spot tests alone, and is not read again until `--all`. The owner may
  prefer no entry in that case.
- **The language word in `<check> is not read in <language> tests.`** `plain_checks.check` returns
  `(check, None)` with no language, so `audit_run.language_of` names it from the test file's
  ending (`.sh` is `shell`). `spot` may prefer to give it.
- **`purlin_run.py`** (lane `run`) still calls `ai_audit.audit_all(project_root, readings,
  cfg.audit_parallel)` and reads `found['verdict']`; K10 replaces that arm with
  `audit_run.run`. **`dev/test_run_script.py`** monkeypatches `ai_audit.ask_model`, which now
  answers a dict.
- **`scripts/run/evidence.py`** (lane `evidence`): K2's `write_audit` and `audit_entry` with
  `breaks` and `explanation`, which the seven waiting tests need. `scripts/mcp/purlin/payload.py`
  (lane `states`): a rule's `audit` should carry `explanation` and `breaks` (K6) for
  `ai_audit.py --feature` to print the explanation; until then it prints none.
- **`.purlin/runtime/audit_could_not_run.json`** is no longer written by the audit; its reader
  (`purlin.evidence.could_not_run`, `why_not_audited`) is `states`' and `evidence`'s to keep or cut.
- **Stale words in files `words` owns:** `references/commit_conventions.md` still names
  `purlin:export`, `--release` and `.purlin/tests.md`; `CLAUDE.md`'s one-home table still
  describes `review_criteria.md` as holding "the heuristic spot tests and the research behind
  them; the instructions the model is sent", which still holds.
- Nothing of `ai_audit` is left unbuilt, and every proof was built to as worded.

## Cost

The session's cost is not readable from inside it.
