# Lane `states`, round 1

Branch `lane/d115-states`, from `d115/base` at `e2c3023d4`. Specs `states` (72 proofs) and
`summary` (16 proofs).

## Tests

`python -m pytest dev/test_states.py dev/test_summary.py dev/test_backing_tests.py dev/test_failing.py -q`

| When | Passed | Failed | Skipped |
|---|---|---|---|
| Before the first change | 127 | 71 | 1 |
| After the last change | 84 | 3 | 1 |

The 3 that fail are the tests waiting on another lane, and nothing else:

- `states PROOF-274` (`TestNothingToCheck::test_an_anchor_proof_with_nothing_to_check_passes_with_its_reason`)
  and `states PROOF-278` (`TestNothingToCheck::test_a_feature_proof_with_nothing_to_check_reads_not_run`),
  on `evidence`: today's `evidence.proof_results` drops a `nothing to check` result.
- `states PROOF-169` (`TestTheSignOff::test_a_commit_of_evidence_alone_after_the_tag_still_reads_signed_at`),
  on `signoff`'s `package.only_records_between`, a stub answering `False`.

The 1 that skips: `states PROOF-58` (`TestStatusTable::test_the_three_samples_show_the_same_cells_in_the_table_and_page`),
playwright is not installed here; it also waits on round 2's `dashboard`.

Checked by hand in a scratch folder, not committed: with a stand-in `proof_results` answering K2's
`{proof: {'result', 'reason'}}` and a stand-in `only_records_between` built to K7's docstring,
all 88 tests pass but the one that skips. So 274, 278 and 169 should pass once `evidence` and
`signoff` are merged.

`summary PROOF-50` is listed as waiting on `only_records_between`; it passes today, because a
commit changing `src/age.py` reads `1 commit since` with the stub's `False` as with the real one.

The deliberate break: `facts.tests_fact` made to answer `met` always. `summary PROOF-53` and
`summary PROOF-52` failed; `git checkout -- scripts/mcp/purlin/facts.py` restored it and both
passed again.

## Section 4's row

| | Gone | Reworded | To add | Right |
|---|---|---|---|---|
| As found | 129 | 40 | 16 | 32 |
| As left | 0 | 0 | 0 | 88 |

Appendix A's script over the four files, on the committed work, prints its last line:
`0 gone, 0 reworded, 88 right as they stand.`

Every proof has one test comment, counted against the spec: `states` 72 of 72, `summary` 16 of 16,
no proof named twice. Added: `states PROOF-265`, `266`, `269`, `270`, `271`, `274`, `276`, `277`,
`278`, `279`, `280`; `summary PROOF-48`, `50`, `52`, `53`, `54`.

K15's greps over the twelve files find only `to_strengthen`, the kind `summary RULE-23` names.

## Reworded comments

Each `fixed` drops what the helpers no longer take (`gate=`, `strength=`, a `cfg` for
`rule_cells`) and then asserts what the proof names now; the line says what else changed.

- `dev/test_states.py:189 states PROOF-5 fixed` one case, a section in the `ci` folder, where a helper ran four over two gates.
- `dev/test_states.py:151 states PROOF-139 fixed` no gate; asserts `passed`, `no proof` and `left` `no_proof`.
- `dev/test_states.py:171 states PROOF-3 stated`
- `dev/test_states.py:198 states PROOF-7 fixed` runs on the shared project, no gate.
- `dev/test_states.py:431 states PROOF-13 fixed` the strength of 48 and its assertion gone.
- `dev/test_states.py:441 states PROOF-159 fixed` no gate.
- `dev/test_states.py:454 states PROOF-160 fixed` no gate.
- `dev/test_states.py:482 states PROOF-19 fixed` asserts `checked at sign-off` with no reason, in place of `manual test`.
- `dev/test_states.py:464 states PROOF-71 fixed` no gate.
- `dev/test_states.py:579 states PROOF-73 fixed` exactly seven fields; `strength` gone.
- `dev/test_states.py:328 states PROOF-51 fixed` no gate.
- `dev/test_states.py:344 states PROOF-52 fixed` no gate.
- `dev/test_states.py:358 states PROOF-53 fixed` no gate.
- `dev/test_states.py:382 states PROOF-54 fixed` `rule_cells` takes no settings.
- `dev/test_states.py:397 states PROOF-50 fixed` no gate; asserts the path is `.purlin/evidence/ci/login.json`.
- `dev/test_states.py:412 states PROOF-66 fixed` one case, where a helper ran it at two gates.
- `dev/test_states.py:623 states PROOF-27 fixed` no gate, no strength; asserts the fourth rule reads `strong`.
- `dev/test_states.py:509 states PROOF-262 fixed` no gate; no assertion on blocking kinds, which the proof no longer names.
- `dev/test_states.py:494 states PROOF-264 fixed` asserts `checked at sign-off`.
- `dev/test_states.py:651 states PROOF-31 fixed` schema 14 and the eighteen keys.
- `dev/test_states.py:690 states PROOF-84 stated`
- `dev/test_states.py:746 states PROOF-98 fixed` asserts `met` true, `not signed` and the last line naming `purlin:sign`.
- `dev/test_states.py:756 states PROOF-213 fixed` no gate.
- `dev/test_states.py:1163 states PROOF-58 stated`
- `dev/test_states.py:1182 states PROOF-43 stated`
- `dev/test_states.py:1193 states PROOF-100 stated`
- `dev/test_states.py:1215 states PROOF-212 fixed` the file holds `{"version": "0.10.0",`.
- `dev/test_states.py:1237 states PROOF-168 fixed` reads `signoff`'s version, commit and word, in place of `tag`.
- `dev/test_states.py:1247 states PROOF-169 fixed` a commit of evidence alone after the tag still reads `signed 1.2.0 at <sha7>`.
- `dev/test_states.py:1259 states PROOF-170 fixed` reads `signoff.version`.
- `dev/test_states.py:1350 states PROOF-238 stated`
- `dev/test_summary.py:134 summary PROOF-4 stated`
- `dev/test_summary.py:145 summary PROOF-43 fixed` 50 rules, 42 strong and 8 weak read the share sentence.
- `dev/test_summary.py:130 summary PROOF-5 stated`
- `dev/test_summary.py:171 summary PROOF-8 stated`
- `dev/test_summary.py:197 summary PROOF-29 stated`
- `dev/test_summary.py:298 summary PROOF-44 fixed` a project on committed evidence ends on `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`.
- `dev/test_summary.py:232 summary PROOF-15 fixed` the rule is `to_fix`, in place of `no_proof`.
- `dev/test_summary.py:269 summary PROOF-47 fixed` a project on committed evidence; the status opens `Tests: met`.
- `dev/test_summary.py:186 summary PROOF-40 stated`

None moved.

## Tests deleted

127 tests, each naming only proofs no spec has. No test was kept for a proof no spec holds.

- `dev/test_states.py::test_a_local_section_counts_at_passed`
- `dev/test_states.py::test_a_ci_section_counts_at_signed`
- `dev/test_states.py::test_a_local_section_counts_at_signed`
- `dev/test_states.py::test_a_section_listing_no_marked_test_leaves_no_proof_written`
- `dev/test_states.py::test_at_passed_a_rule_with_a_test_and_no_proof_waits_for_nothing`
- `dev/test_states.py::test_a_section_taken_over_other_code_is_out_of_date`
- `dev/test_states.py::test_a_ci_section_meets_level_one`
- `dev/test_states.py::test_a_committed_local_section_counts_at_signed`
- `dev/test_states.py::test_an_uncommitted_run_counts_at_signed`
- `dev/test_states.py::test_a_spec_edit_leaves_it_out_of_date`
- `dev/test_states.py::test_a_rule_no_test_backs_reads_no_test`
- `dev/test_states.py::test_a_proof_with_no_test_comes_before_a_partial_run`
- `dev/test_states.py::test_a_proof_waiting_on_another_system_reads_not_run`
- `dev/test_states.py::test_a_section_answers_only_for_the_proofs_it_lists`
- `dev/test_states.py::test_a_measured_strength_is_a_reason_and_no_minimum_is_read`
- `dev/test_states.py::test_with_no_score_the_cell_says_no_mutation_score_was_measured`
- `dev/test_states.py::test_a_loosely_worded_proof_decides_nothing_by_its_wording`
- `dev/test_states.py::test_a_field_the_format_does_not_name_decides_nothing`
- `dev/test_states.py::test_a_rule_no_audit_read_is_not_audited`
- `dev/test_states.py::test_an_undecided_entry_gives_its_sentence`
- `dev/test_states.py::test_an_undecided_entry_that_says_nothing`
- `dev/test_states.py::test_an_undecided_rule_is_left_to_strengthen`
- `dev/test_states.py::test_at_signed_a_rule_no_audit_read_is_not_audited`
- `dev/test_states.py::test_a_proof_with_a_test_raises_no_manual_flag`
- `dev/test_states.py::test_with_mutation_off_a_strength_left_behind_is_not_compared`
- `dev/test_states.py::test_a_strength_not_measured_for_a_reason_keeps_the_audits_word`
- `dev/test_states.py::test_the_reason_strength_was_not_measured_follows_the_findings`
- `dev/test_states.py::test_a_could_not_run_record_ends_when_the_rule_changes`
- `dev/test_states.py::test_a_rule_carries_its_audit_at_signed`
- `dev/test_states.py::test_a_rule_no_audit_entry_answers_carries_none_at_passed`
- `dev/test_states.py::test_a_rule_no_audit_entry_answers_carries_none_at_signed`
- `dev/test_states.py::test_an_entry_naming_its_model_is_carried_at_passed`
- `dev/test_states.py::test_an_entry_naming_its_model_is_carried_at_signed`
- `dev/test_states.py::test_the_notes_an_audit_wrote_are_carried`
- `dev/test_states.py::test_two_systems_that_passed_are_named_in_one_reason`
- `dev/test_states.py::test_a_file_whose_source_field_agrees_is_read`
- `dev/test_states.py::test_a_persons_own_section_answers_for_its_platform_at_signed`
- `dev/test_states.py::test_a_persons_own_section_alone_passes_at_signed`
- `dev/test_states.py::test_at_signed_the_rollup_counts_the_four_buckets_then_the_flags`
- `dev/test_states.py::test_at_passed_a_rule_carries_both_cells`
- `dev/test_states.py::test_at_signed_a_rule_carries_both_cells`
- `dev/test_states.py::test_the_table_counts_strong_over_every_rule`
- `dev/test_states.py::test_a_row_counts_strong_over_its_rules`
- `dev/test_states.py::test_a_rule_whose_test_fails_waits_in_its_strong_cell`
- `dev/test_states.py::test_a_project_with_no_remote_has_a_null_remote_url`
- `dev/test_states.py::test_the_remote_url_is_the_origin`
- `dev/test_states.py::test_a_feature_with_no_evidence_names_its_spec`
- `dev/test_states.py::test_a_rule_carries_its_proofs_and_no_origin`
- `dev/test_states.py::test_a_feature_says_its_evidence_is_no_longer_current`
- `dev/test_states.py::test_the_rollup_counts_the_buckets_the_gate_reaches`
- `dev/test_states.py::test_the_proof_counts_call_out_a_proof_with_no_test`
- `dev/test_states.py::test_a_marker_below_the_last_test_backs_nothing`
- `dev/test_states.py::test_the_summary_and_what_is_left_ride_in_the_payload`
- `dev/test_states.py::test_a_comment_naming_nothing_is_left_to_correct`
- `dev/test_states.py::test_the_system_words_ride_in_the_payload`
- `dev/test_states.py::test_a_section_that_names_no_machine_names_none`
- `dev/test_states.py::test_each_rule_names_the_one_kind_it_waits_for`
- `dev/test_states.py::test_the_fixtures_carry_exactly_the_keys_the_builder_writes`
- `dev/test_states.py::test_every_fixture_has_the_key_set_the_builder_writes`
- `dev/test_states.py::test_the_tag_key_is_present_in_every_fixture`
- `dev/test_states.py::test_a_manual_proof_reads_hand_check`
- `dev/test_states.py::test_an_env_proof_reads_its_own_systems_sections_alone`
- `dev/test_states.py::test_a_spec_reads_its_own_rule_count`
- `dev/test_states.py::test_the_tests_cell_counts_a_partial_rule`
- `dev/test_states.py::test_with_no_rule_audited_the_table_shows_no_strong_column`
- `dev/test_states.py::test_once_the_audit_found_a_rule_strong_the_table_adds_the_column`
- `dev/test_states.py::test_a_passed_project_with_no_proof_line_is_shown_no_proof_count`
- `dev/test_states.py::test_retired_config_keys_print_the_update_directive`
- `dev/test_states.py::test_an_updated_project_prints_no_update_line`
- `dev/test_states.py::test_an_updated_project_prints_it_once_a_key_returns`
- `dev/test_states.py::test_a_set_up_project_over_code_is_sent_to_spec_from_code`
- `dev/test_states.py::test_a_set_up_project_over_no_code_is_sent_to_write_a_spec`
- `dev/test_states.py::test_a_project_not_set_up_is_sent_to_set_it_up`
- `dev/test_states.py::test_the_repository_own_specs_print_the_table`
- `dev/test_states.py::test_no_tag_reads_none`
- `dev/test_states.py::test_at_passed_the_payload_names_a_passed_tag`
- `dev/test_states.py::test_a_spec_with_no_scope_line_is_incomplete`
- `dev/test_states.py::test_a_scope_naming_nothing_that_exists_is_incomplete`
- `dev/test_states.py::test_a_scope_naming_a_file_that_exists_is_complete`
- `dev/test_states.py::test_an_anchor_is_never_incomplete`
- `dev/test_states.py::test_at_passed_with_breaking_on_it_says_why_nothing_was_measured`
- `dev/test_states.py::test_at_signed_with_breaking_on_it_says_why_nothing_was_measured`
- `dev/test_states.py::test_status_names_one_spec_at_passed`
- `dev/test_states.py::test_status_names_one_spec_at_signed`
- `dev/test_states.py::test_status_names_two_specs_at_passed`
- `dev/test_states.py::test_status_names_two_specs_at_signed`
- `dev/test_states.py::test_status_says_nothing_when_every_spec_names_its_files_at_passed`
- `dev/test_states.py::test_status_says_nothing_when_every_spec_names_its_files_at_signed`
- `dev/test_states.py::test_a_gate_not_accepted_is_read_as_passed_with_its_fix`
- `dev/test_states.py::test_an_audit_parallel_not_accepted_is_read_as_4_with_its_fix`
- `dev/test_states.py::test_a_key_this_release_does_not_read_is_named`
- `dev/test_states.py::test_a_spec_changed_and_not_committed_is_listed`
- `dev/test_states.py::test_the_anchor_lines_open_on_anchors`
- `dev/test_states.py::test_a_source_with_no_pin_is_named`
- `dev/test_states.py::test_a_source_that_could_not_be_read_names_the_fix`
- `dev/test_states.py::test_an_anchor_counts_its_rules_in_its_own_row`
- `dev/test_states.py::test_the_audit_alone_judges_an_anchors_tests`
- `dev/test_states.py::test_an_anchors_strong_cell_shows_no_strength`
- `dev/test_states.py::test_a_project_with_no_anchor_has_no_label_line`
- `dev/test_states.py::test_a_line_left_from_a_conflict_fails_the_spec`
- `dev/test_states.py::test_one_spec_is_named_with_its_cause`
- `dev/test_states.py::test_two_specs_read_plural`
- `dev/test_states.py::test_a_spec_with_no_scope_line_keeps_its_own_line`
- `dev/test_summary.py::test_at_passed_it_names_the_tests_alone`
- `dev/test_summary.py::test_with_no_rule_audited_the_sentence_names_no_audit`
- `dev/test_summary.py::test_one_rule_left_reads_singular`
- `dev/test_summary.py::test_zero_reads_plural`
- `dev/test_summary.py::test_the_lines_follow_the_order_of_the_work`
- `dev/test_summary.py::test_three_comments_naming_nothing_read_plural`
- `dev/test_summary.py::test_a_comment_to_correct_comes_before_a_rule_to_fix`
- `dev/test_summary.py::test_a_kind_at_zero_has_no_line`
- `dev/test_summary.py::test_with_nothing_left_the_ending_is_two_lines`
- `dev/test_summary.py::test_at_signed_it_names_the_release_run_and_the_sign_off`
- `dev/test_summary.py::test_a_release_tag_on_head_names_the_push`
- `dev/test_summary.py::test_a_failing_rule_is_only_to_fix`
- `dev/test_summary.py::test_at_passed_a_rule_with_nothing_wants_a_test`
- `dev/test_summary.py::test_out_of_date_is_to_test`
- `dev/test_summary.py::test_a_rule_one_proof_of_which_no_test_backs_wants_a_test`
- `dev/test_summary.py::test_a_proof_listed_with_no_test_named_wants_a_test`
- `dev/test_summary.py::test_a_rule_checked_by_hand_passes_and_adds_no_work`
- `dev/test_summary.py::test_two_systems_are_named_in_their_words_and_order`
- `dev/test_summary.py::test_this_machines_own_system_is_never_named_on_the_line`
- `dev/test_summary.py::test_two_broken_specs_read_plural`
- `dev/test_backing_tests.py::test_a_newer_section_naming_another_test_moves_the_hash`
- `dev/test_backing_tests.py::test_every_operating_system_s_section_counts`
- `dev/test_failing.py::test_failures_from_two_sources_and_two_systems_are_each_named`
- `dev/test_failing.py::test_an_env_proof_failing_on_another_system_here_is_not_run`

## Lines a person reads that this lane chose

- The passed cell's reason on a feature's proof that found nothing to check is the reason alone,
  as the run gave it: `no screens here` (`states PROOF-278` says only "its reason kept"). It is
  carried in the payload among the cell's reasons, which the dashboard's rule page shows.

Every other line is as section 3 or a spec gives it.

## Differences from section 3

- **K6, a rule's `audit`.** It holds exactly `verdict`, `findings`, `notes`, `model`, `at`,
  `commit` and `path`. K6 adds `explanation` and `breaks`; `states RULE-61` and `PROOF-73` name
  the seven and say "exactly", and the spec holds.
- **K1, the settings warning.** The payload does not yet carry K1's warning for a key this
  version does not read: K1 names no `config_engine` function for it, and none is in the tree.
  `payload.build_payload` starts `warnings` empty where it read `gate.resolve_gate(...).warnings`.
  `mcp` adds the function in round 2; one line in `build_payload` then carries it.
- **K6, `EARLIER_WEAK`.** Defined in `states.py` as K6 writes it, and used nowhere: no rule of
  `states` names it, and `states RULE-118` fixes the reasons of `waiting` and `not audited`
  exactly.
- **K6, `signoff_fact`.** Where the tag sits on HEAD itself it answers `SIGNED_AT` without asking
  `only_records_between`; `since` is the count of commits from the tag to HEAD in every case, 1
  where one evidence commit follows the tag and the word still reads `signed <v> at <sha7>`.
- **K3.** The passed cell carries `nothing_to_check`, `[{proof, reason}]`, so the status prints
  `NOTHING_LINE` and the package can read the list without parsing reasons.
- **K2, `proof_results`.** `states.section_results` reads both today's answer (a word per proof)
  and K2's (`{'result', 'reason'}`), so this lane's tests run before `evidence` merges. Once it
  has, the branch for a bare word answers nothing and integration may drop it.
- **K4, where a test was last changed.** As K4 says, the lines below the comment down to the
  test's last line. A comment whose proof did not exist at that commit has no old wording to
  differ, and is not named. Same-second commits are ordered by `git rev-list --topo-order`.
- **K4, the proof's words.** Read with the line's tags, now from the spec file and then from
  `git cat-file --batch`, whitespace folded, as appendix A reads them.
- **K5, `test_hash_kind`.** Where a rule has a `@manual` proof it reads `manual`; then `file`
  where any test was covered by its whole file; then `test`; then `none`. No rule fixes the order.
- **Functions added beside the contracts:** `facts.is_signed_here`, `since_word`, `distance`,
  `records_only_since`, `commits_since`, `version_order`, `git_line`; `states.read_sections`,
  `section_results`; `summary.opening`; `status.not_written_lines`, `nothing_lines`;
  `wording.proof_words`, `test_source`, `count_line`; `payload.branch_name`.
- **Signatures changed in modules this lane owns:** `states.rule_cells(inp)`,
  `states.feature_rollup(rule_results)`, `summary.rule_kind(rule, here_os, broken=None)`,
  `summary.left(...)` and `summary.last_line(...)` as K6, `board.columns_for(proofs, audited)`,
  `board.row_cells(name, rollup, proofs, audited)`, `board.shows_proofs(proofs)`,
  `status.columns_for(proofs, audited)`, `payload.audit_summary(audit)`.
- **Cost (K4).** `sync_status` over this repository: 2.6 s at the base commit, 4.0 s now, 1.4 s
  slower. Blames run eight at a time; every spec at every commit is read through one
  `git cat-file --batch`.

## Left open, not built, and failures elsewhere

- **The spec-ahead line beside the old warning.** `specs.spec_mistakes` (lane `mcp`) still warns
  `<spec>: > Scope: names <x>, which finds no file in git.` for each entry, so until round 2 a
  spec ahead of its code prints that warning as well as the information line of
  `states RULE-123`. The payload puts this lane's line in `information` only.
- **`states RULE-122`, "a spec ... whose scope finds no file in git".** Read as `RULE-123`'s
  information line; the old line `1 spec's > Scope: finds no file in git yet ...` is gone. A spec
  with no `> Scope:` line keeps its line `1 spec names no files ...`.
- **`→ Run: purlin:init --update`** still prints above the ending while an upgrade is pending. No
  decision cuts it; no proof holds it now.
- **Waiting on other lanes:** `states PROOF-274`, `PROOF-278` (`evidence`); `states PROOF-169`
  (`signoff`); `states PROOF-58` (`dashboard`, and playwright).
- **Files this lane does not own that read what it changed,** found by reading, not by running
  them:
  - `scripts/review/sign.py:792` and `scripts/export/release.py:457` print
    `summary_module.RELEASE`, which K6 cuts: an `AttributeError` when reached (`signoff`).
  - `scripts/review/ai_audit.py:174` reads a feature's `test_strength`, which the payload no
    longer carries; it reads `None` (`audit`).
  - `dev/test_purlin_report.py`, `dev/test_report_refresh.py`, `dev/test_consumer_ci.py` read the
    payload's `gate`, `tag` or `test_strength`; `scripts/report/src/app.js` reads `manual test`
    (`dashboard`, `remote`).
  - `dev/test_init_scaffold.py:1984` expects `Nothing left to do. To release a version: ...`
    (`setup`); `dev/skill_checks.py:199` reads `Nothing left to do.` (`words`).
  - `dev/test_skill_status.py:262` iterates `summary.KINDS` as four-tuples, which holds.

## Cost

Not readable from inside the session.
