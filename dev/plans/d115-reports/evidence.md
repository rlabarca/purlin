# Lane `evidence`, round 1

Builds to `evidence_writer`, `evidence` and `reports`. Branch `lane/d115-evidence`, from
`d115/base` at `e2c3023d4`. Four commits: the writer and the reader with evidence format 8, the
reports with marker format 4, one test split, and this report.

## Tests

`python -m pytest <file> -q`, one file at a time, on Linux with Python 3.11.

| File | Before my first change | After my last, as the tree stands | After my last, with the neighbours' changes applied by hand |
|---|---|---|---|
| `dev/test_evidence_writer.py` | 84 passed, 1 failed | 22 passed, 19 failed | 40 passed, 1 failed |
| `dev/test_evidence_reader.py` | 32 passed, 1 skipped | 16 passed, 1 skipped | 16 passed, 1 skipped |
| `dev/test_fingerprint.py` | 45 passed | 21 passed | 21 passed |
| `dev/test_reports.py` | 111 passed, 1 skipped | 45 passed, 2 failed, 1 skipped | 47 passed, 1 skipped |
| Total | 272 passed, 1 failed, 2 skipped | 104 passed, 21 failed, 2 skipped | 124 passed, 1 failed, 2 skipped |

The third column is the honest check of my own code. I applied, in the working tree only and
never staged, what the contracts tell `run`, `states` and `signoff` to do to the files that read
mine: `purlin_run.py` without its `write_table` calls, with `kept_audits` read as one dict,
`write_audit` called without mutation, and `marker_results` carrying `reason` from
`reports.reason_of`; `payload.py` without `evidence_module.mutation`; `states.py`, `payload.py`
and `package.py` reading `proof_results(...)[id]['result']`; and a working
`package.only_records_between`. Every file was restored with `git checkout` before each commit.

**Skipped for a missing tool or system:**
- `dev/test_reports.py::test_dotnet_still_writes_what_the_capture_holds`: `dotnet is not on this machine`. `go`, `npm` and `node` were present, so the Go, Jest and Vitest capture checks ran and passed.
- `dev/test_evidence_reader.py::test_on_windows_the_reader_names_its_own_machine_windows` (`evidence PROOF-75`, `@env(windows)`): needs Windows.

**Waiting on another lane.** More than section 2 lists. Every test that runs `purlin_run.py --test`
fails as the tree stands until `run` merges, because `purlin_run.py` still calls
`evidence.write_table`, which K2 deletes.

- On `run` (`purlin_run.py`: the two `write_table` calls, `kept_audits` unpacked as a tuple, `write_audit` given mutation, `marker_results` without `reason`): `evidence_writer PROOF-1`, `PROOF-16`, `PROOF-90`, `PROOF-17`, `PROOF-41`, `PROOF-93`, `PROOF-94`, `PROOF-6`, `PROOF-9`, `PROOF-10`, `PROOF-38`, `PROOF-91`, `PROOF-92`, `PROOF-39`, `PROOF-50`, `PROOF-85`, `PROOF-88`, `PROOF-89`; `reports PROOF-20`, `PROOF-88`. `PROOF-93` and `PROOF-94` also need `marker_results` to hand each entry its `reason` (K3).
- On `signoff`'s `only_records_between` (it answers `False` in the stub): `evidence_writer PROOF-91`, as listed, and `PROOF-38`, which the plan did not list: a second `--commit` run starts on the evidence commit, so its section names a commit the first one does not, and only `only_records_between` keeps the file. `PROOF-92` passes on the stub.
- On `audit`: `evidence_writer PROOF-54`.
- With every neighbour change above applied, `evidence_writer PROOF-54` is the one failure.

## Section 4's row

| | Found | Left |
|---|---|---|
| Gone | 169 | 0 |
| Reworded | 13 | 0 |
| To add | 7: `evidence_writer` 90 to 94; `reports` 115, 117 | 0 |

Appendix A's script over my four files, on the committed work, last line:
`0 gone, 0 reworded, 123 right as they stand.`

Every proof of the three specs has exactly one test comment: `evidence_writer` 41 of 41,
`evidence` 38 of 38, `reports` 44 of 44. No test carries two comments: `evidence PROOF-1` and
`PROOF-71` shared one test and now have one each.

K15's greps over every file I own find nothing (`gate`, `--release`, `passed/`, `tests.md`,
`mutation`, `mutmut`, `stryker`, `min_strength`, `audit_parallel`, `purlin:export`,
`does not apply`, `settled:`, `purlin-package/3`, `hard_gates`, and `undecided`).

### Reworded comments

- `dev/test_evidence_writer.py:196 evidence_writer PROOF-1 fixed`: the section's exact keys now include `email`.
- `dev/test_evidence_writer.py:513 evidence_writer PROOF-6 stated`: renamed to `test_a_run_deletes_both_files_of_gone_writes_feat_and_names_each`. It surfaced once the tests around it were deleted.
- `dev/test_evidence_writer.py:588 evidence_writer PROOF-9 fixed`: the assertion that `.purlin/tests.md` is untracked is gone; it asserts `?? .purlin/evidence/local/feat.json` in git status.
- `dev/test_evidence_writer.py:605 evidence_writer PROOF-10 fixed`: the evidence commit changes exactly `.purlin/evidence/local/feat.json`, no table.
- `dev/test_evidence_writer.py:880 evidence_writer PROOF-12 fixed`: no mutation is written or read; `audit` is `{'rules': {...}}` and the `RULE-2` entry's text is asserted unchanged in the file.
- `dev/test_evidence_writer.py:904 evidence_writer PROOF-54 fixed`: the test installs its own fake answering `no break: the code has nothing to change` as `claude-fake-1`, asserts `claude` resolves under its own `tmp_path`, and asserts `breaks` `PROOF-1` reads `not made`.
- `dev/test_evidence_writer.py:996 evidence_writer PROOF-63 fixed`: setup runs without `--gate`, and git is asked about the evidence file and the run log alone.
- `dev/test_evidence_reader.py:81 evidence PROOF-17 stated`: renamed to `test_only_a_ci_file_reads_the_ci_file_no_local_file_and_no_warning`.
- `dev/test_evidence_reader.py:127 evidence PROOF-20 stated`: renamed, and asserts that no `solaris` section is listed.
- `dev/test_evidence_reader.py:243 evidence PROOF-24 stated`: renamed to `test_loading_checking_and_asking_leaves_the_same_files_and_bytes`.
- `dev/test_reports.py:278 reports PROOF-7 stated`: renamed to `test_four_python_tests_read_pass_fail_skip_fail_in_their_order`.
- `dev/test_reports.py:629 reports PROOF-82 stated`: renamed to `test_a_path_holding_a_space_is_one_argument_then_the_report_path`.
- `dev/test_reports.py:714 reports PROOF-19 stated`: renamed to `test_a_marker_naming_a_feature_no_spec_has_is_printed_and_exits_1`.

### Added

`dev/test_evidence_writer.py:237 PROOF-90`, `:654 PROOF-91`, `:669 PROOF-92`, `:412 PROOF-93`,
`:427 PROOF-94`; `dev/test_reports.py:323 PROOF-115`, `:333 PROOF-117`.

## Tests deleted

156 tests, every comment of each naming a proof no spec has; none showed a proof of mine that had
no test. Helpers only they used went with them: `NAMELESS_HOST`, `_removed_by`, `_table_lines`,
`_edited`, `FIRST_MUTATION`, `NO_REPORT`, `NOT_INSTALLED`, `_ignore_patterns`, `ON_WINDOWS`,
`HELD`, `WRITTEN` (writer); `_both_audited` (reader); `_assert_skipped_folder_not_counted`,
`_api`, `JS_TEST`, `NOW`, `_SYSTEM_WORD` (fingerprint); `_no_suite`, `_passed_word` (reports).
- `dev/test_evidence_writer.py::test_the_runner_is_the_slug_of_the_git_email`
- `dev/test_evidence_writer.py::test_a_run_on_a_host_with_no_name_names_the_machine_unknown`
- `dev/test_evidence_writer.py::test_a_rule_whose_one_test_passed_reads_passed`
- `dev/test_evidence_writer.py::test_a_rule_waiting_on_another_system_reads_not_run`
- `dev/test_evidence_writer.py::test_a_rule_whose_proof_has_no_test_reads_no_test`
- `dev/test_evidence_writer.py::test_a_proof_tagged_for_this_system_that_passed_reads_passed`
- `dev/test_evidence_writer.py::test_a_failure_outweighs_a_proof_owed_by_another_system`
- `dev/test_evidence_writer.py::test_a_rule_whose_one_test_was_skipped_reads_not_run`
- `dev/test_evidence_writer.py::test_a_proof_owed_by_another_system_with_no_test_is_not_run`
- `dev/test_evidence_writer.py::test_a_skipped_test_of_a_proof_owed_here_is_missing`
- `dev/test_evidence_writer.py::test_a_manual_proof_is_listed_missing_and_manual`
- `dev/test_evidence_writer.py::test_a_ci_section_lists_only_the_proofs_tagged_for_its_system`
- `dev/test_evidence_writer.py::test_a_test_proves_only_the_proof_tagged_for_the_system_it_ran_on`
- `dev/test_evidence_writer.py::test_a_rule_with_no_proof_and_a_failing_marked_test_reads_failed`
- `dev/test_evidence_writer.py::test_a_rule_with_no_proof_and_one_failing_marked_test_of_two_fails`
- `dev/test_evidence_writer.py::test_a_run_writes_its_section_beside_the_others_as_they_were`
- `dev/test_evidence_writer.py::test_an_audit_write_drops_the_rules_the_spec_dropped`
- `dev/test_evidence_writer.py::test_a_feature_run_removes_the_evidence_of_a_feature_with_no_spec`
- `dev/test_evidence_writer.py::test_an_audit_run_removes_the_evidence_of_a_feature_with_no_spec`
- `dev/test_evidence_writer.py::test_a_second_run_that_saw_the_same_thing_leaves_the_file_alone`
- `dev/test_evidence_writer.py::test_a_section_that_differs_only_in_when_it_ran_is_not_written`
- `dev/test_evidence_writer.py::test_a_section_over_another_fingerprint_replaces_the_one_on_disk`
- `dev/test_evidence_writer.py::test_a_row_counts_the_features_newest_section`
- `dev/test_evidence_writer.py::test_the_table_opens_on_the_newest_commit_and_its_columns`
- `dev/test_evidence_writer.py::test_a_dirty_newest_section_is_named_in_the_heading`
- `dev/test_evidence_writer.py::test_the_table_ends_on_whose_run_each_row_is`
- `dev/test_evidence_writer.py::test_a_table_with_no_evidence_says_no_feature_has_run`
- `dev/test_evidence_writer.py::test_an_older_section_in_the_other_source_does_not_answer`
- `dev/test_evidence_writer.py::test_a_feature_run_leaves_the_other_rows_as_they_were`
- `dev/test_evidence_writer.py::test_a_rule_with_a_skipped_test_is_not_counted_passed`
- `dev/test_evidence_writer.py::test_an_audit_run_writes_and_does_not_commit`
- `dev/test_evidence_writer.py::test_several_features_name_the_folder`
- `dev/test_evidence_writer.py::test_the_results_commit_names_the_work_commit`
- `dev/test_evidence_writer.py::test_the_work_is_committed_first_and_each_file_named`
- `dev/test_evidence_writer.py::test_the_work_commit_names_every_feature_run`
- `dev/test_evidence_writer.py::test_outside_git_the_files_are_written_and_nothing_is_committed`
- `dev/test_evidence_writer.py::test_an_audit_replaces_the_entry_it_read_again`
- `dev/test_evidence_writer.py::test_an_audit_without_mutation_testing_keeps_the_score`
- `dev/test_evidence_writer.py::test_a_first_audit_without_mutation_testing_writes_null`
- `dev/test_evidence_writer.py::test_a_score_that_differs_only_in_why_nothing_was_measured_replaces_it`
- `dev/test_evidence_writer.py::test_an_entry_with_another_proof_hash_replaces_it`
- `dev/test_evidence_writer.py::test_an_entry_with_another_test_hash_replaces_it`
- `dev/test_evidence_writer.py::test_an_entry_with_another_verdict_replaces_it`
- `dev/test_evidence_writer.py::test_an_entry_with_other_findings_replaces_it`
- `dev/test_evidence_writer.py::test_an_entry_sent_other_criteria_replaces_it`
- `dev/test_evidence_writer.py::test_an_audit_entry_carries_the_notes_the_audit_gave`
- `dev/test_evidence_writer.py::test_an_audit_entry_with_no_notes_has_no_notes_field`
- `dev/test_evidence_writer.py::test_the_ignore_lines_init_gives_name_neither_file`
- `dev/test_evidence_writer.py::test_this_repositorys_own_ignore_file_names_neither_file`
- `dev/test_evidence_reader.py::test_a_file_under_ci_that_is_not_json_names_the_remote_run`
- `dev/test_evidence_reader.py::test_a_file_that_is_not_an_object_is_ignored_with_one_warning`
- `dev/test_evidence_reader.py::test_a_system_that_names_itself_win32_is_windows`
- `dev/test_evidence_reader.py::test_a_system_that_names_itself_darwin_is_macos`
- `dev/test_evidence_reader.py::test_a_code_and_a_rule_edit_put_it_out_of_date_on_spec_and_code`
- `dev/test_evidence_reader.py::test_an_audit_entry_for_another_rule_hash_does_not_answer`
- `dev/test_evidence_reader.py::test_an_audit_entry_for_another_proof_hash_does_not_answer`
- `dev/test_evidence_reader.py::test_a_later_ci_audit_entry_wins`
- `dev/test_evidence_reader.py::test_a_later_local_audit_entry_wins`
- `dev/test_evidence_reader.py::test_local_wins_a_tie_for_the_newest_section`
- `dev/test_evidence_reader.py::test_windows_reads_windows_and_win`
- `dev/test_evidence_reader.py::test_macos_reads_macos_and_mac`
- `dev/test_evidence_reader.py::test_linux_reads_linux_unix_and_lin`
- `dev/test_evidence_reader.py::test_an_unknown_system_word_reads_as_linux`
- `dev/test_evidence_reader.py::test_a_proof_whose_tests_all_passed_has_passed`
- `dev/test_evidence_reader.py::test_a_proof_not_run_here_reads_not_run`
- `dev/test_fingerprint.py::test_a_reworded_anchor_rule_leaves_a_feature_as_it_was`
- `dev/test_fingerprint.py::test_manual_added_to_a_proof_changes_spec_alone`
- `dev/test_fingerprint.py::test_an_edit_to_a_scoped_file_changes_code_alone`
- `dev/test_fingerprint.py::test_an_edit_to_a_file_outside_the_scope_changes_nothing`
- `dev/test_fingerprint.py::test_a_glob_reaches_a_matching_file_directly_in_its_folder`
- `dev/test_fingerprint.py::test_a_glob_does_not_reach_a_file_it_does_not_match`
- `dev/test_fingerprint.py::test_an_entry_holding_a_question_mark_is_a_glob`
- `dev/test_fingerprint.py::test_an_entry_holding_a_bracket_is_a_glob`
- `dev/test_fingerprint.py::test_a_file_git_does_not_track_is_listed_as_unmatched`
- `dev/test_fingerprint.py::test_a_marked_file_no_suite_names_is_not_counted`
- `dev/test_fingerprint.py::test_a_javascript_marker_is_counted`
- `dev/test_fingerprint.py::test_a_marked_file_under_node_modules_is_not_counted`
- `dev/test_fingerprint.py::test_a_marked_file_under_bin_is_not_counted`
- `dev/test_fingerprint.py::test_a_marked_file_under_obj_is_not_counted`
- `dev/test_fingerprint.py::test_a_marked_file_under_mutants_is_not_counted`
- `dev/test_fingerprint.py::test_a_marked_file_under_a_dot_folder_is_not_counted`
- `dev/test_fingerprint.py::test_an_added_file_joins_the_fingerprint`
- `dev/test_fingerprint.py::test_a_name_no_spec_defines_raises`
- `dev/test_fingerprint.py::test_the_parts_that_differ_are_named_in_order`
- `dev/test_fingerprint.py::test_a_missing_stored_fingerprint_differs_on_all_three`
- `dev/test_fingerprint.py::test_a_stored_fingerprint_that_is_text_differs_on_all_three`
- `dev/test_fingerprint.py::test_two_equal_fingerprints_differ_on_no_part`
- `dev/test_fingerprint.py::test_a_feature_with_no_evidence_is_selected_as_never_run_here`
- `dev/test_fingerprint.py::test_a_rewritten_tests_table_leaves_an_anchor_as_it_was`
- `dev/test_fingerprint.py::test_a_run_with_no_feature_named_selects_an_anchor_after_an_edit`
- `dev/test_reports.py::test_a_comment_naming_no_id_is_not_a_marker`
- `dev/test_reports.py::test_a_marker_after_code_in_a_python_file_is_not_read`
- `dev/test_reports.py::test_a_marker_in_a_python_string_is_not_read`
- `dev/test_reports.py::test_a_marker_in_a_here_document_is_not_read`
- `dev/test_reports.py::test_two_stars_cross_any_number_of_folders`
- `dev/test_reports.py::test_a_question_mark_is_one_character_and_never_a_slash`
- `dev/test_reports.py::test_two_stars_may_be_no_folder_at_the_top`
- `dev/test_reports.py::test_two_stars_may_be_no_folder_in_the_middle`
- `dev/test_reports.py::test_a_file_no_suite_matches_is_not_read`
- `dev/test_reports.py::test_with_no_suite_a_marked_test_is_not_run`
- `dev/test_reports.py::test_with_no_suite_the_status_sends_the_rule_to_be_tested`
- `dev/test_reports.py::test_with_no_suite_a_file_of_no_test_language_is_not_read`
- `dev/test_reports.py::test_go_declares_its_test_functions_in_order`
- `dev/test_reports.py::test_csharp_declares_every_other_test_attribute`
- `dev/test_reports.py::test_a_title_that_is_not_a_literal_declares_no_test`
- `dev/test_reports.py::test_a_go_function_not_shaped_as_a_test_declares_none`
- `dev/test_reports.py::test_a_trx_warning_passes`
- `dev/test_reports.py::test_a_trx_completed_passes`
- `dev/test_reports.py::test_a_trx_passed_but_run_aborted_passes`
- `dev/test_reports.py::test_a_line_of_the_stream_that_is_not_json_is_left_alone`
- `dev/test_reports.py::test_a_vitest_class_is_the_file_path`
- `dev/test_reports.py::test_a_go_package_is_read_against_go_mod`
- `dev/test_reports.py::test_a_python_case_of_no_marked_file_is_tied_to_nothing`
- `dev/test_reports.py::test_a_trx_case_of_no_marked_class_is_tied_to_nothing`
- `dev/test_reports.py::test_a_go_case_of_no_package_is_tied_to_nothing`
- `dev/test_reports.py::test_a_parametrised_test_passes_when_every_value_passes`
- `dev/test_reports.py::test_a_theory_with_one_failing_row_fails`
- `dev/test_reports.py::test_a_table_of_passing_rows_passes`
- `dev/test_reports.py::test_a_jest_title_is_narrowed_by_its_outer_parts`
- `dev/test_reports.py::test_a_csharp_test_is_narrowed_by_its_class`
- `dev/test_reports.py::test_a_marker_above_a_decorator_is_tied`
- `dev/test_reports.py::test_a_failing_test_fails_each_of_its_markers_once`
- `dev/test_reports.py::test_the_tied_markers_beside_an_untied_one_still_pass`
- `dev/test_reports.py::test_a_passing_test_is_pass`
- `dev/test_reports.py::test_a_failing_test_is_fail`
- `dev/test_reports.py::test_a_skipped_test_is_missing`
- `dev/test_reports.py::test_a_run_over_one_feature_gives_its_test_file`
- `dev/test_reports.py::test_a_run_over_every_feature_gives_no_test_file`
- `dev/test_reports.py::test_the_command_runs_through_bash`
- `dev/test_reports.py::test_an_old_report_folder_is_deleted_before_the_suite_runs`
- `dev/test_reports.py::test_a_suite_leaving_an_empty_report_folder_is_missing_evidence`
- `dev/test_reports.py::test_two_markers_naming_no_spec_are_each_named`
- `dev/test_reports.py::test_a_marker_naming_a_proof_no_spec_has_fails_the_run`
- `dev/test_reports.py::test_a_marker_naming_a_rule_no_spec_has_fails_the_run`
- `dev/test_reports.py::test_a_marker_naming_a_rule_that_has_proofs_fails_the_run`
- `dev/test_reports.py::test_a_run_with_only_well_formed_markers_exits_0`
- `dev/test_reports.py::test_a_suite_with_no_files_is_left_out`
- `dev/test_reports.py::test_a_suite_with_no_files_names_its_problem`
- `dev/test_reports.py::test_an_entry_that_is_not_an_object_is_left_out`
- `dev/test_reports.py::test_a_suite_named_twice_keeps_the_first`
- `dev/test_reports.py::test_a_report_that_cannot_be_read_is_missing_evidence`
- `dev/test_reports.py::test_a_wrong_command_line_exits_2`
- `dev/test_reports.py::test_a_file_no_suite_reads_is_not_listed`
- `dev/test_reports.py::test_purlin_in_capitals`
- `dev/test_reports.py::test_no_space_after_the_colon`
- `dev/test_reports.py::test_purlin_misspelled_by_one_letter`
- `dev/test_reports.py::test_a_marker_naming_what_exists_is_not_a_near_miss`
- `dev/test_reports.py::test_a_comment_naming_no_id_has_no_fix`
- `dev/test_reports.py::test_an_id_that_is_neither_proof_nor_rule_has_no_fix`
- `dev/test_reports.py::test_a_proof_id_one_character_off`
- `dev/test_reports.py::test_a_misspelled_proof_word`
- `dev/test_reports.py::test_a_proof_word_in_lower_case`
- `dev/test_reports.py::test_a_rule_with_one_proof_is_offered_its_proof`
- `dev/test_reports.py::test_a_rule_with_two_proofs_is_not_offered`
- `dev/test_reports.py::test_a_rule_with_no_proof_is_offered_itself`
- `dev/test_reports.py::test_a_feature_one_character_from_two_is_not_a_near_miss`

## Lines a person reads that I chose

None printed. My modules print no new line: `Evidence written to ...`, `Evidence committed.`,
`Evidence unchanged.`, `Removed ...` and the reader's warnings are as they were and as the specs
quote them. The new prose is in the two format files: `references/formats/marker_format.md`
gains a section "Nothing to check" and a skip-reason row for each report format;
`references/formats/evidence_format.md` gains `email`, `reason`, `nothing to check`, `breaks`,
`explanation`, the `test_hash` of K5, the retention over the same code, and loses the table,
`audit.mutation` and `undecided`.

## Differences from section 3's contracts

1. **`email` is added by `write_section`, not `build_section`.** K2 keeps `build_section`'s
   signature, and that function has no project folder to ask git. `write_section(project_root,
   'local', ...)` adds `email` from `git config user.email`, or `unknown`, where the section has
   none. A `ci` section gets none. `git_email(project_root)` is new and public.
2. **Retention is a parameter of `merge_section`.** `merge_section(..., rule_ids,
   same_code=None)` takes a function of `(older, newer)`; `write_section` passes one that calls
   `package.only_records_between(project_root, older, newer)` (imported when first needed, from
   `scripts/export/`). Two sections naming the same commit are the same code without the call,
   which is `only_records_between`'s own first case. `merge_for_host`, the remote runner's
   merge, has no project folder and passes none, so a `ci` section is kept only over the same
   commit.
3. **How the reason reaches `marker_results`.** K3 says its entries gain `reason` but not where
   it is read. `reports.tie` now hands each case's outcome as `reports.Outcome`, a `str` that
   also carries `.reason`, so `result_of` and every caller comparing outcomes work unchanged.
   `reports.reason_of(outcomes)` answers the reason where every case of a test skipped, else
   None. `run` would write, in `marker_results`:
   `'reason': reports_module.reason_of(done.outcomes.get((path, test.line), []))`.
   An `exit` suite gives none.
4. **Names added to `scripts/mcp/purlin/evidence.py`:** `NOTHING_TO_CHECK = 'nothing to
   check'`, `NOTHING_TO_CHECK_PREFIX = 'nothing to check:'` and `nothing_reason(reason)`, the
   text after the prefix, stripped, or None. `proof_results` orders the results `fail`, `not
   run`, `nothing to check`, `pass`, worst first.
5. **`build_section` reads `info['is_anchor']`**, which `specs.scan_specs` already gives, to read
   a `nothing to check` proof as passed on an anchor and as not run elsewhere.
6. **`audit_entry`** writes `breaks` (`{}` where `found` has none) and `explanation` (`[]`
   where none) always, and `notes` only where there are some, as K2 says.

## Left unbuilt, open calls, failures in files I do not own

- **Failures in files I do not own, until their lanes merge.** Each reads what K2 removes or
  reshapes:
  - `scripts/run/purlin_run.py` (`run`): `evidence_writer.write_table` at lines 1183 and 1510;
    `entries, mutation = evidence_writer.kept_audits(...)` at line 802, which now answers one
    dict; `write_audit(..., mutation, mutation is not None)` at 805 and the mutation write at
    1469 to 1476; `marker_results` without `reason`. As the tree stands every `--test` run ends
    in an `AttributeError` after it writes the evidence.
  - `scripts/mcp/purlin/payload.py` (`states`) line 302 calls `evidence_module.mutation`, which
    K2 deletes: every payload with a feature that is not an anchor raises `AttributeError`, so
    `sync_status` and the status fail until `states` merges. `states.py`, `payload.py` and
    `scripts/export/package.py` (`signoff`) compare `proof_results(...)` values to `'pass'` and
    `'fail'`; they now get `{'result': ..., 'reason': ...}`, so those comparisons read nothing
    until each lane reads `['result']`.
- **Stale text in files I do not own**, per CLAUDE.md's step 4, for the lane that owns each:
  `.purlin/tests.md` or `audit.mutation` is still named in `docs/how-purlin-works.md`,
  `docs/running-and-evidence.md`, `docs/working-together.md`, `docs/dashboard.md`,
  `docs/specs-and-anchors.md`, `docs/getting-started.md` (`docs`); `skills/test/SKILL.md`,
  `skills/init/SKILL.md`, `references/commit_conventions.md`, `references/purlin_commands.md`,
  `references/glossary.md`, `references/hard_gates.md` (`words`);
  `references/formats/anchor_format.md` (`anchors`); `templates/gitignore.purlin` (`setup`),
  which `evidence_writer`'s `> Scope:` names.
- **`evidence_writer PROOF-63`** runs `scaffold.py --yes`, now without `--gate`. It passes on
  the base; it reads setup's ignore file, so it moves with `setup` in round 2.
- **Four unmarked tests stay** in `dev/test_reports.py`:
  `test_jest_still_writes_what_the_capture_holds`, `..._vitest_...`, `..._dotnet_...`,
  `..._go_...`. They check that the captured fixtures under `dev/fixtures/reports/` are still
  what each tool writes, and name no proof. No decision cuts them and none keeps them; I left
  them as they were.
- **`markers.SKIP_DIRS` loses `mutants`**: the folder was mutmut's copy of a project, and
  decision 109 cuts mutation testing. `node_modules`, `bin` and `obj` stay; no proof of
  `reports` or `evidence` names the list any more.
- **`reports.py` still imports `NAMES_NOTHING`, `RULE_HAS_PROOFS` and `marker_problems`** from
  `markers.py` without using them; `purlin_run.py` may read them through `reports`, so I left
  them.
- No proof was left unbuilt as worded.

## Break on purpose

In `merge_section` I took out the same-code check, so a section seeing the same results was kept
whatever commit it named. With the neighbour changes applied, `evidence_writer PROOF-92` failed:
the section kept the first run's commit, not the new `HEAD`. `git checkout --
scripts/run/evidence.py` restored it, and the test passed.

## Cost

This session cannot read its own spend.
