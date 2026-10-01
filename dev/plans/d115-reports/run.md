# Lane `run`, round 1

Builds to `run_script`. Branch `lane/d115-run`, from `d115/base` at `e2c3023d4`.

## Tests

`python -m pytest dev/test_run_script.py dev/test_mutation_adapters.py -q` before the first
change: 90 failed, 204 passed, 3 skipped, 2 errors (298 tests in both files).

`python -m pytest dev/test_run_script.py -q` after the last change: 7 failed, 52 passed,
1 skipped (60 tests). `dev/test_mutation_adapters.py` is deleted.

Skipped for a missing tool:

- `run_script PROOF-155`, `test_a_sql_script_with_a_statement_that_errors_fails`: `sqlite3` is
  not installed here.

The 7 failures, each waiting on another lane, by proof:

| Proof | Test | Waits on | What it needs |
|---|---|---|---|
| `run_script PROOF-271` | `test_a_reworded_proof_is_named_after_the_markers_line` | `states` | `wording.stale_comments` filled; the run already prints each entry's `text` after `Markers:` |
| `run_script PROOF-87` | `test_a_test_with_no_assertion_is_left_to_strengthen` | `spot`, `audit` | `audit_run.run` writing a `weak` entry from the spot test; `summary` counting `to_strengthen` |
| `run_script PROOF-274` | `test_an_anchor_test_with_nothing_to_check_is_not_missing` | `evidence` | `reports.Case.reason`; the run reads it with `getattr(case, 'reason', None)`. Checked here with a `Case` stand-in carrying the reason: the run exits 0 and the marker result carries `reason` |
| `run_script PROOF-272` | `test_remote_with_no_runner_file_writes_it_and_runs_nothing` | `remote` (round 2) | `remote.ensure_runner` and `run_remote` |
| `run_script PROOF-273` | `test_commit_runner_commits_the_runner_file_alone` | `remote` (round 2) | the same |
| `run_script PROOF-222` | `test_a_file_not_yet_written_is_named_and_the_tests_still_run` | `states` | the status printing `status.NOT_WRITTEN_ONE` in place of the old per-file warning (K6); the rest of the proof passes now |
| `run_script PROOF-95` | `test_nothing_changed_runs_nothing_and_ends_on_the_sign_off` | `states` | `summary.LAST_LINE` as the status's last line; the rest of the proof passes now |

`PROOF-222` and `PROOF-95` are not on the waits the lane prompt lists: both end on a line the
status prints, which `states` builds (K6, `summary RULE-18`, `states RULE-123`).

The two `PROOF-272` and `PROOF-273` tests take `gh` off the path and send a push to a bare
repository on disk (`url.<bare>.pushInsteadOf`), so neither reaches the network against today's
`remote.py` or round 2's.

## Section 4's row

| | Gone | Reworded | To add |
|---|---|---|---|
| As found | 161 | 19 | 5: `run_script` 270 to 274 |
| As left | 0 | 0 | 0 |

Comments gone: 161 removed. 153 tests carried only gone comments and are deleted; 4 tests kept a
right comment and lost a gone one (`PROOF-225`, `PROOF-227`, `PROOF-232`, `PROOF-233`). No gone
test showed one of the five proofs to add, so none was changed to show one; `PROOF-270` is a new
test in `TestTheTwoCommits`.

Comments added: `run_script PROOF-270`, `PROOF-271`, `PROOF-272`, `PROOF-273`, `PROOF-274`.

The last line appendix A's script prints for `dev/test_run_script.py`:
`0 gone, 0 reworded, 61 right as they stand.`

`grep -c "purlin: run_script PROOF-" dev/test_run_script.py` is 61, the spec's 61 proofs, each
named once. K15's greps over the five files this lane owns find nothing.

## The reworded comments

- `dev/test_run_script.py:182 run_script PROOF-3 stated`
- `dev/test_run_script.py:264 run_script PROOF-7 stated`
- `dev/test_run_script.py:442 run_script PROOF-103 stated`
- `dev/test_run_script.py:455 run_script PROOF-105 fixed`: the project is no longer set to the
  gate `signed`.
- `dev/test_run_script.py:468 run_script PROOF-222 fixed`: asserts the line
  `login: 1 file its scope names is not written yet: src/gone.py. Run purlin:build login, or correct the path with purlin:spec login.`
  in place of the `> Scope: names ... finds no file in git` warning.
- `dev/test_run_script.py:560 run_script PROOF-12 fixed`: the checkout is no longer set to a
  gate.
- `dev/test_run_script.py:579 run_script PROOF-117 stated`
- `dev/test_run_script.py:626 run_script PROOF-17 fixed`: no gate, and no signature folder
  checked.
- `dev/test_run_script.py:639 run_script PROOF-102 fixed`: no `mutation_engine` and no break
  asserted; asserts no model call, no `audit` in the ci file, exit 0.
- `dev/test_run_script.py:659 run_script PROOF-109 fixed`: no gate, and the model's calls are no
  longer asserted.
- `dev/test_run_script.py:674 run_script PROOF-87 fixed`: the test is one with no assertion, and
  the model's answer and its finding are no longer set up or asserted.
- `dev/test_run_script.py:736 run_script PROOF-165 fixed`: the change to `src/feat.py` is left
  uncommitted, as the proof has it.
- `dev/test_run_script.py:820 run_script PROOF-58 fixed`: asserts the heading, the `1 failed`
  line and `--- end of pytest output ---`, in that order, before `Purlin status:`; no
  `Evidence is missing` check.
- `dev/test_run_script.py:853 run_script PROOF-171 fixed`: the proof is tagged for this machine's
  system and no gate is set.
- `dev/test_run_script.py:1045 run_script PROOF-95 fixed`: ends on
  `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`.
- `dev/test_run_script.py:1064 run_script PROOF-96 stated`
- `dev/test_run_script.py:1104 run_script PROOF-193 stated`
- `dev/test_run_script.py:1123 run_script PROOF-98 stated`
- `dev/test_run_script.py:1414 run_script PROOF-257 fixed`: the settings are edited by rewriting
  the file, not by setting `audit_parallel`.

## Tests deleted

`dev/test_mutation_adapters.py`, whole (90 tests), with `dev/fixtures/mutation/` and
`setup.cfg`.

From `dev/test_run_script.py`, 153 tests:

`test_the_copy_mutmut_leaves_is_never_collected`, `test_two_actions_are_refused`, `test_all_and_a_feature_together_are_refused`, `test_audit_remote_is_refused_and_names_the_test_command`, `test_a_flag_the_run_does_not_know_is_refused`, `test_feature_with_no_name_after_it_is_refused`, `test_an_arm_timeout_that_is_not_a_number_is_refused`, `test_a_project_root_with_no_folder_after_it_is_refused`, `test_h_prints_the_usage_and_exits_0`, `test_ci_with_commit_is_refused`, `test_test_remote_with_commit_is_refused`, `test_a_remote_run_with_commit_names_the_command_without_it`, `test_test_remote_is_accepted`, `test_test_commit_is_accepted`, `test_audit_commit_is_accepted`, `test_a_missing_project_root_exits_two`, `test_a_sql_script_whose_statements_succeed_passes`, `test_a_marker_with_no_entry_is_named`, `test_the_list_is_bounded_and_counted`, `test_a_test_the_report_leaves_out_is_named`, `test_a_marker_with_no_test_after_it_is_named`, `test_several_foreign_proofs_are_counted_in_one_line`, `test_a_foreign_env_proof_is_not_reported_missing`, `test_the_table_and_the_summary_are_printed`, `test_a_passing_rule_no_audit_read_leaves_nothing_to_do`, `test_at_passed_a_rule_with_no_test_is_left_to_write_one`, `test_a_project_with_no_specs_says_so`, `test_a_suite_with_no_report_names_its_setting`, `test_a_problem_in_the_setting_names_its_fix`, `test_the_first_line_names_the_suite_it_starts`, `test_the_markers_are_counted_next`, `test_the_suites_run_are_named_before_the_table`, `test_the_ci_arm_commits_its_one_path`, `test_at_passed_the_ci_arm_does_the_same`, `test_at_signed_the_ci_arm_does_the_same`, `test_a_failing_test_fails_the_ci_arm`, `test_a_marker_naming_no_spec_does_not_fail_the_ci_arm`, `test_the_section_lists_only_the_proofs_tagged_for_its_system`, `test_a_feature_with_no_proof_tagged_for_its_system_gets_no_file`, `test_the_log_is_written`, `test_the_audit_writes_the_log_too`, `test_the_breaks_are_asked_for_each_features_scope_files`, `test_an_audit_never_uses_the_git_hosts_api`, `test_a_tag_run_writes_nothing_and_says_so`, `test_a_run_on_the_branch_that_keeps_it_commits`, `test_with_mutation_on_the_audit_measures_and_writes_the_score`, `test_at_passed_the_breaks_run_where_mutation_is_on`, `test_a_ci_run_at_signed_measures_nothing_and_audits_nothing`, `test_with_mutation_off_the_audit_alone_decides`, `test_an_engine_that_measured_nothing_says_why`, `test_every_feature_with_a_rule_being_read_is_measured`, `test_a_feature_with_no_rule_being_read_is_not_measured`, `test_the_breaks_are_asked_for_no_anchor`, `test_an_anchors_evidence_holds_no_mutation_score`, `test_one_call_per_rule_four_at_a_time_by_default`, `test_the_setting_decides_how_many_run_at_once`, `test_a_setting_out_of_range_is_read_as_four_with_one_warning`, `test_sixteen_is_taken_as_it_is`, `test_seventeen_reads_as_four_with_the_warning`, `test_zero_reads_as_four_with_the_warning`, `test_a_fraction_reads_as_four_with_the_warning`, `test_a_word_reads_as_four_with_the_warning`, `test_the_line_is_printed_before_the_first_call`, `test_nothing_to_read_says_so_and_calls_nothing`, `test_a_rule_that_matches_its_last_audit_is_skipped`, `test_all_reads_every_rule_again`, `test_a_rule_whose_test_failed_is_not_read`, `test_with_no_feature_named_every_feature_is_audited`, `test_an_anchors_rule_is_read_as_the_anchors`, `test_no_claude_on_the_path`, `test_a_model_that_exits_1`, `test_a_model_past_its_time_limit`, `test_a_model_that_answers_with_no_settled_line`, `test_two_causes_in_one_run_print_one_line_each`, `test_two_causes_in_one_run_give_each_cell_its_own`, `test_the_next_audit_tries_again`, `test_at_the_gate_passed_it_blocks_nothing`, `test_the_audit_ends_in_the_order_the_design_gives`, `test_the_skipped_rules_take_their_place`, `test_a_finding_blocks_nothing_at_signed`, `test_a_rule_found_weak_then_found_strong_is_left_to_release`, `test_at_signed_the_audit_exits_on_what_it_answers_for`, `test_a_failing_test_still_exits_one_at_passed`, `test_committed_evidence_makes_the_passed_cell_read_passed`, `test_uncommitted_evidence_makes_the_passed_cell_read_passed`, `test_a_code_change_committed_leaves_the_cell_out_of_date`, `test_a_test_edit_leaves_the_cell_out_of_date`, `test_darwin_reads_macos`, `test_win32_reads_windows`, `test_linux_reads_linux`, `test_any_other_system_reads_linux`, `test_this_windows_machine_reads_windows`, `test_only_the_last_60_lines_are_printed`, `test_a_killed_suite_prints_its_tail`, `test_a_suite_that_printed_nothing_says_so`, `test_a_killed_test_file_names_the_longer_limit_to_run`, `test_a_killed_audit_names_the_audit_to_run`, `test_an_arm_that_passed_prints_no_tail`, `test_ci_writes_the_whole_run_to_the_log_in_the_tree`, `test_the_audit_keeps_every_line_past_sixty_in_the_log`, `test_an_empty_project_root_exits_2_and_runs_nothing`, `test_a_narrow_run_hands_the_suite_only_its_features_test_files`, `test_a_test_edit_selects_its_feature`, `test_a_spec_that_names_no_files_is_selected`, `test_a_spec_that_names_no_files_is_selected_every_time`, `test_the_file_once_committed_selects_it_as_a_code_change`, `test_the_run_after_that_has_nothing_to_run`, `test_the_skipped_line_names_ten_and_counts_the_rest`, `test_nothing_changed_over_a_failing_test_exits_one`, `test_a_run_over_every_feature_runs_the_suite_whole`, `test_ci_with_no_feature_named_runs_every_feature`, `test_the_audit_with_nothing_selected_still_reads_every_rule`, `test_a_second_audit_reads_nothing`, `test_a_spec_edit_selects_and_reads_that_feature_alone`, `test_an_audit_that_reads_nothing_exits_0`, `test_pytest_is_suggested_its_own_entry`, `test_vitest_is_suggested_its_own_entry`, `test_jest_is_suggested_its_own_entry`, `test_dotnet_is_suggested_its_own_entry`, `test_go_is_suggested_its_own_entry`, `test_sql_is_suggested_its_own_entry`, `test_shell_is_suggested_its_own_entry`, `test_a_tests_folder_with_no_test_file_is_not_pytest`, `test_every_tool_found_is_suggested_in_the_order`, `test_each_format_and_report`, `test_each_set_of_globs`, `test_a_yarn_project_is_told_the_yarn_command`, `test_a_pnpm_project_is_told_the_pnpm_command`, `test_a_project_that_runs_its_doctests_keeps_running_them`, `test_a_spec_naming_the_option_adds_nothing`, `test_sql_is_told_it_runs_through_sqlite3`, `test_pytest_needs_nothing_added`, `test_the_key_test_framework_stops_the_run`, `test_the_key_spec_dir_stops_the_run`, `test_the_key_pre_push_stops_the_run`, `test_the_key_report_stops_the_run`, `test_the_key_digest_stops_the_run`, `test_a_proof_file_under_specs_stops_the_run`, `test_a_receipt_file_under_specs_stops_the_run`, `test_a_rule_with_no_test_is_named`, `test_a_proof_for_another_system_with_no_test_is_named`, `test_a_rule_whose_only_proof_has_no_test_names_that_proof`, `test_a_feature_not_run_is_not_named`, `test_the_first_commit_is_named_for_the_work`, `test_the_run_lists_each_file_of_the_first_commit`, `test_the_work_is_committed_before_the_evidence`, `test_a_clean_checkout_gets_one_commit`, `test_nothing_to_run_commits_the_settings_alone`, `test_nothing_to_run_with_nothing_changed_commits_nothing`, `test_the_audit_reads_no_rule_of_it`, `test_a_passing_release_is_tagged_at_passed`, `test_a_refused_release_exits_1`, `test_release_beside_a_feature_is_refused`.


## Lines a person reads that this lane chose

None. The one new printed line is section 6's, word for word:
`purlin: --commit-runner belongs to --test --remote. Run purlin:test --remote --commit-runner`,
printed to standard error with the usage line when `--commit-runner` comes without `--remote`.
No test holds it: `run_script` has no proof of it, and a test is not written without a proof.

## Differences from section 3's contracts

- **K10, the `--commit-runner` refusal.** Every other refusal is printed as `purlin: <words>.`;
  this one is printed as section 6 gives it, with no full stop after the command.
- **K10, `audit_run.run`.** It is called as
  `audit_run.run(project_root, features, selected, again=args.all, out=sys.stdout)`, where
  `selected` is the features named or, with none named, every feature, as the run's audit read
  them before. `out` is the run's standard output; no contract says what it is.
- **K10 and `ai_audit RULE-35`.** `audit_run.run` prints the share last of what it prints; the
  run then prints the status table, the summary and `Left to do`, because `run_script RULE-11`
  ends every run on them. The share is the audit's last line, not the run's.
- **K3, the reason.** `reports.tie` gives outcomes alone, so the run reads each case's
  `reason` in a second pass through `reports.locate`, tying a case as `tie` ties it
  (`skip_reasons`). A test gives a reason only where it did not run and every case of it gave the
  same one. Where `evidence` makes `tie` carry the reason, that pass folds into it.
- **K2.** `write_sections` calls `evidence.kept_audits(sides, current)` as answering
  `{rule: entry}` and `evidence.write_audit(project_root, source, feature, info, entries)`, as K2
  has them. `d115/base`'s `evidence.py` still has the older signatures, so a run over an evidence
  file a merge left conflicted fails until `evidence` merges. No test of this lane reaches it.
- **K4.** `wording.stale_comments(project_root, features, scanned=scan)`, `scan` being
  `markers.scan`'s answer. It is not called for `--ci`, which `run_script RULE-96` leaves out.

## Left unbuilt, calls left open, failures in files this lane does not own

- Nothing of `run_script` is left unbuilt. Seven proofs wait on other lanes, listed above.
- `run_script PROOF-126`, `PROOF-221` and `PROOF-262` fix the suggested pytest command
  `python3 -m pytest --ignore=mutants {files} --junitxml={report}`. The command keeps
  `--ignore=mutants`, as the proofs hold, for the owner (K15). Detection no longer skips a
  `mutants/` folder, and the supported-frameworks page no longer says it does.
- The doctest switch in the suggested pytest command is cut (decision 112): `runs_doctests`
  and `DOCTEST_OPTION` leave `frameworks.py`, and its paragraph leaves the page. The page also
  loses the sentence on installing `sqlite3` on a Windows runner (decision 112) and the mutmut
  paragraph.
- An older Purlin is read off a settings file with no `tests` setting alone. The 0.9.5 keys and
  the proof and receipt files under `specs/` are no longer read: no proof holds them, and 0.9.5
  wrote no `tests` setting.
- Not this lane's, found while building: `dev/run_project.py`, frozen, still gives the default
  pytest suite `--ignore=mutants`; `scripts/run/remote.py` (`remote`) still takes a third
  argument `cfg`, which the run no longer passes; `scripts/run/mutation/` (`setup`) and
  `scripts/export/release.py` (`signoff`) are still in the tree, no longer imported by the run;
  `dev/test_init_scaffold.py` (`setup`) still checks a project's `setup.cfg`.

## What the session cost

Not readable from this session.
