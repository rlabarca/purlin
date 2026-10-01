# The setup lane, round 2

Written by the `setup` lane on 2026-10-01, on `lane/d115-setup` from `d115/base` at
`301bcb468`. Specs: `scaffold`, `update`.

## Tests

`python -m pytest dev/test_init_scaffold.py dev/test_init_update.py -q`

| | Passed | Failed | Skipped | Errors |
|---|---|---|---|---|
| Before the first change | 265 | 1 | 1 | 9 |
| After the last change | 64 | 0 | 9 | 0 |

Before: the failure was the typescript walk, which expected `Nothing left to do. To release a
version: purlin:test --release`; the nine errors were the python walk, whose fixture ran the
release step and the gates; the skip was the C# walk, with no `dotnet` here.

Skipped after, for a missing tool or system, each for integration to run:

| Test | Proof | Why |
|---|---|---|
| `dev/test_init_scaffold.py::TestTheEvidenceFolder::test_on_windows_the_readme_is_the_bytes_purlin_ships` | `scaffold PROOF-136` | Windows |
| `dev/test_init_scaffold.py::TestTheIgnoreFile::test_on_windows_a_crlf_gitignore_is_the_same_after_a_second_run` | `scaffold PROOF-130` | Windows |
| `dev/test_init_scaffold.py::TestTheMarketplacePath::test_on_windows_no_file_names_the_copy` | `scaffold PROOF-132` | Windows |
| `dev/test_init_scaffold.py::TestEachLanguageIsSetUp::test_a_csharp_project_runs_its_marked_test` | `scaffold PROOF-95` | `dotnet` is not installed here |
| `dev/test_init_scaffold.py::TestRunCommitAndSignOff::test_the_sign_off_makes_a_signed_commit_naming_the_signer` | `scaffold PROOF-119` | `ssh-keygen` is not on this machine |
| `dev/test_init_scaffold.py::TestRunCommitAndSignOff::test_the_first_sign_off_writes_the_signed_tag` | `scaffold PROOF-93` | `ssh-keygen` is not on this machine |
| `dev/test_init_update.py::test_on_windows_a_second_run_finds_nothing_and_changes_nothing` | `update PROOF-117` | Windows |
| `dev/test_init_update.py::test_on_windows_every_backup_keeps_the_bytes_from_before` | `update PROOF-118` | Windows |
| `dev/test_init_update.py::test_on_windows_the_conftest_keeps_import_os_and_its_ending` | `update PROOF-120` | Windows |

The two sign-off proofs could not run here. The same walk, taken by hand to `purlin:sign --show`
with the fake model, refused nothing and printed the overview (`Signing 0.1.0 at <sha7>.`,
`1 rule on Linux/Unix: 1 passes its tests, no hand check.`, `The audit: 1 strong, 0 weak, 0 not
audited.`); only the SSH signature needs `ssh-keygen`. The typescript walk (`scaffold
PROOF-94`) ran and passed: `npm` is here.

Waiting on another lane: none.

`evidence_writer PROOF-63` in `dev/test_evidence_writer.py` was rerun after the ignore
template changed: the whole file passes, 41 passed.

## Section 4's row

| | Gone | Reworded | Right | Added |
|---|---|---|---|---|
| As found | 220 (111 scaffold, 108 update, 1 `dev/test_init_e2e_wiring.sh`) | 31 | 37 | |
| As left | 0 | 0 | 73 | 5 to add: `scaffold` 171, 172, 173; `update` 162, 163 |

Appendix A's script over `dev/test_init_scaffold.py dev/test_init_update.py`, last line:
`0 gone, 0 reworded, 73 right as they stand.` 73 is every proof of the two specs, 33 and 40,
each named by exactly one test comment (`grep -c` per proof gives 1 for each).

Six Windows proofs that shared a test with another proof now have a test of their own, so each
test carries one comment: `scaffold PROOF-130`, `132`, `136`; `update PROOF-117`, `118`,
`120`.

## Reworded comments

Both test files were rewritten whole, so every line now blames to this lane's commits; the line
is where the comment stands now.

- `dev/test_init_scaffold.py:261 scaffold PROOF-88 fixed`: run with no flag and nothing on stdin; asserts the one question by its words, `Commit the files setup wrote?`
- `dev/test_init_scaffold.py:291 scaffold PROOF-48 stated`
- `dev/test_init_scaffold.py:313 scaffold PROOF-47 stated`
- `dev/test_init_scaffold.py:323 scaffold PROOF-136 fixed`: a Windows test of its own, where it shared PROOF-47's
- `dev/test_init_scaffold.py:537 scaffold PROOF-128 stated`
- `dev/test_init_scaffold.py:368 scaffold PROOF-8 stated`
- `dev/test_init_scaffold.py:389 scaffold PROOF-61 stated`
- `dev/test_init_scaffold.py:413 scaffold PROOF-20 fixed`: asserts no line of the second run's summary begins `wrote`, and the whole tree outside `.git/` byte for byte
- `dev/test_init_scaffold.py:403 scaffold PROOF-108 stated`
- `dev/test_init_scaffold.py:337 scaffold PROOF-153 stated`
- `dev/test_init_scaffold.py:343 scaffold PROOF-154 stated`
- `dev/test_init_scaffold.py:426 scaffold PROOF-24 stated`
- `dev/test_init_scaffold.py:435 scaffold PROOF-112 fixed`: the hook reads exactly `echo mine`, as the proof has it
- `dev/test_init_scaffold.py:464 scaffold PROOF-157 fixed`: the line before the question is the last line naming a file, not the runner file's skip
- `dev/test_init_scaffold.py:479 scaffold PROOF-158 fixed`: the subject `chore(init): set up Purlin`; no `[y/N]` in the output
- `dev/test_init_scaffold.py:503 scaffold PROOF-159 stated`
- `dev/test_init_scaffold.py:492 scaffold PROOF-160 fixed`: the subject `chore(init): set up Purlin`
- `dev/test_init_scaffold.py:554 scaffold PROOF-161 stated`
- `dev/test_init_scaffold.py:522 scaffold PROOF-31 stated`
- `dev/test_init_scaffold.py:584 scaffold PROOF-33 stated`
- `dev/test_init_scaffold.py:627 scaffold PROOF-22 fixed`: no foreign proof and no runner file; the copy and this checkout each set up a pytest project as a child process
- `dev/test_init_scaffold.py:660 scaffold PROOF-132 fixed`: a Windows test of its own, where it shared PROOF-21's
- `dev/test_init_scaffold.py:646 scaffold PROOF-23 stated`
- `dev/test_init_scaffold.py:983 scaffold PROOF-37 fixed`: setup runs with nothing to answer from; asserts `Markers: 1 tied to a test, 0 not tied.` and `1 rule. 1 passes its tests.` and no release line
- `dev/test_init_scaffold.py:995 scaffold PROOF-94 fixed`: the same, for the typescript project
- `dev/test_init_scaffold.py:1006 scaffold PROOF-95 fixed`: the same, for the C# project
- `dev/test_init_scaffold.py:1018 scaffold PROOF-36 fixed`: the run ends `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`; no `.purlin/tests.md`
- `dev/test_init_scaffold.py:1031 scaffold PROOF-119 fixed`: a `VERSION` file of `0.1.0`, after the audit, answers `{"audit": "go on", "stops": {}, "sign": true}`
- `dev/test_init_scaffold.py:1042 scaffold PROOF-93 fixed`: the tag stands on the sign-off's commit, and the line is `Push the branch and the tag: git push origin main signed/0.1.0`
- `dev/test_init_update.py:547 update PROOF-30 stated`
- `dev/test_init_update.py:852 update PROOF-31 stated`

## Tests deleted

`dev/test_init_e2e_wiring.sh`, whole: it carried only `scaffold PROOF-96`, which no spec holds,
and no proof of RULE-8 names a C# project. `dev/run_tests.sh:45` still runs it; that file is
integration's.

Every test below named only proofs no spec holds. A test whose proof survives was rewritten,
often under a new name, and is not listed.

`dev/test_init_scaffold.py`, 105: `test_at_signed_a_project_with_code_is_asked_three_questions`, `test_at_passed_a_project_with_code_is_asked_the_gate_alone`, `test_a_later_run_asks_nothing_before_it_writes`, `test_the_gate_flag_answers_the_question_without_asking`, `test_the_gate_is_remembered_when_no_flag_names_one`, `test_an_unreadable_answer_falls_back_to_passed`, `test_a_gate_flag_that_is_no_gate_is_refused`, `test_the_gate_question_offers_two_choices`, `test_at_passed_the_mutation_question_is_not_asked`, `test_at_signed_the_mutation_question_is_asked`, `test_the_config_holds_the_six_keys`, `test_the_template_carries_five_keys_in_order`, `test_audit_parallel_keeps_a_value_in_range`, `test_audit_parallel_out_of_range_is_put_back_to_4`, `test_a_child_run_and_an_in_process_run_agree`, `test_a_key_outside_the_seven_is_not_written_back`, `test_a_project_with_tests_is_asked_nothing_about_them`, `test_yes_turns_it_on_and_wires_the_engine`, `test_no_turns_it_off_and_wires_nothing`, `test_at_signed_a_framework_with_no_engine_is_told_why`, `test_at_passed_a_framework_with_no_engine_is_told_nothing`, `test_on_windows_a_pytest_project_is_told_mutmut_does_not_run`, `test_a_value_the_config_carries_is_kept_without_asking`, `test_yes_leaves_it_off`, `test_yes_with_no_gate_takes_passed`, `test_the_flag_turns_it_on_without_asking`, `test_no_minimum_is_written_with_mutation_on`, `test_a_second_run_keeps_the_readme`, `test_a_readme_the_project_edited_stays_edited`, `test_a_second_setup_keeps_the_dashboard_page_as_it_is`, `test_at_passed_the_readme_names_no_audit`, `test_the_readme_opens_on_what_a_run_leaves`, `test_no_folder_for_anchors_is_made`, `test_nothing_is_written_into_a_vitest_suite`, `test_nothing_is_written_into_a_jest_suite`, `test_a_vitest_project_is_told_how_to_install_stryker`, `test_a_jest_project_is_told_how_to_install_stryker`, `test_a_csharp_project_with_no_dotnet_is_told_to_install_it`, `test_a_csharp_project_with_no_stryker_tool_is_told_to_add_it`, `test_an_installed_stryker_prints_no_line`, `test_a_csharp_project_under_dev_fixtures_is_left_out`, `test_a_csharp_project_at_the_root_keeps_its_dotnet_line`, `test_a_javascript_sample_is_left_out`, `test_each_fixture_folder_name_is_left_out_at_any_depth`, `test_raising_the_gate_writes_the_setting_and_no_workflow`, `test_raising_to_signed_keeps_the_workflow`, `test_lowering_writes_the_setting_and_deletes_nothing`, `test_a_project_with_no_foreign_proof_gets_no_workflow`, `test_at_passed_the_skip_line_says_every_test`, `test_at_passed_the_reason_names_the_test`, `test_at_signed_the_reason_names_the_proof`, `test_two_foreign_systems_are_one_reason`, `test_with_no_remote_nothing_is_written`, `test_with_no_remote_no_heading_is_printed`, `test_with_a_prerequisite_missing_no_heading_is_printed`, `test_a_missing_prerequisite_is_named_and_nothing_is_written`, `test_under_the_runner_file_it_names_where_it_runs`, `test_under_the_runner_file_it_names_its_triggers`, `test_a_remote_with_no_branch_yet_still_gets_the_workflow`, `test_gh_installed_is_named_and_the_workflow_written`, `test_gh_missing_is_named_and_the_workflow_still_written`, `test_az_installed_is_named_and_the_pipeline_written`, `test_az_missing_is_named_and_the_pipeline_still_written`, `test_an_azure_remote_gets_the_pipeline`, `test_the_matrix_names_only_the_systems_this_machine_is_not`, `test_one_foreign_system_is_the_whole_matrix`, `test_the_purlin_release_is_pinned`, `test_the_triggers_are_a_run_branch_and_the_signing_tag`, `test_the_last_step_is_the_test_run`, `test_the_azure_pipeline_has_the_same_triggers`, `test_the_azure_pipeline_ends_on_the_test_run`, `test_a_github_ssh_remote_reads_github`, `test_a_github_https_remote_reads_github`, `test_a_dev_azure_com_remote_reads_azure`, `test_a_visualstudio_com_remote_reads_azure`, `test_a_host_that_is_neither_says_what_still_works`, `test_no_remote_reads_no_host`, `test_the_summary_names_the_four_files_it_writes`, `test_the_dashboard_is_copied`, `test_the_gitignore_is_named_once`, `test_each_ignored_entry_has_its_comment_above_it`, `test_the_gitignore_says_the_evidence_is_tracked`, `test_the_engine_block_joins_a_pyproject_once`, `test_without_a_pyproject_setup_cfg_gets_the_block_once`, `test_the_mutmut_copy_is_ignored_once`, `test_with_no_spec_over_code_it_ends_on_spec_from_code`, `test_with_no_spec_and_no_code_it_sends_you_to_write_one`, `test_with_a_spec_it_ends_on_what_is_left_to_do`, `test_a_root_that_does_not_exist_exits_2`, `test_a_missing_root_is_named_and_nothing_is_made`, `test_a_fresh_project_set_up_from_the_copy_does_not_name_it`, `test_a_project_set_up_from_this_checkout_does_not_name_it`, `test_nested_code_is_source_and_a_test_directory_is_the_selection`, `test_a_nested_tests_folder_is_the_selection_and_bench_is_not`, `test_docs_and_examples_are_not_source`, `test_src_and_tests_still_win_over_other_directories`, `test_modules_at_the_root_are_named_one_by_one`, `test_no_python_anywhere_falls_back_to_the_root`, `test_a_package_folder_is_the_source_where_there_is_no_src`, `test_a_go_module_runs_through_the_command_its_first_run_suggests`, `test_the_audit_writes_into_the_evidence_and_commits_it`, `test_a_runner_s_run_on_the_signed_tag_writes_nothing`, `test_a_runner_s_run_on_a_run_branch_writes_its_evidence`, `test_the_release_at_passed_writes_the_passed_tag`, `test_the_release_at_signed_writes_no_tag`

`dev/test_init_update.py`, 101: `test_a_root_without_purlin_has_nothing_pending`, `test_every_pending_entry_says_what_it_does_and_to_which_files`, `test_yes_takes_the_default_of_the_gate_and_mutation_questions`, `test_an_empty_answer_declines_a_migration`, `test_an_ignored_cache_is_deleted`, `test_a_committed_cache_is_deleted_from_git_and_from_disk`, `test_a_cache_the_gitignore_does_not_name_is_deleted_too`, `test_the_config_is_the_gate_shape`, `test_the_config_is_the_gate_shape_at_signed`, `test_retired_keys_are_gone`, `test_no_remote_writes_ci_none`, `test_another_host_writes_ci_none`, `test_an_azure_remote_writes_ci_azure`, `test_a_ci_the_project_named_is_kept`, `test_an_audit_parallel_the_project_named_is_kept`, `test_a_dashboard_switch_set_on_is_not_written_back`, `test_a_dashboard_switch_set_off_is_not_written_back_either`, `test_the_gate_defaults_to_passed`, `test_the_gate_question_takes_the_answer_you_type`, `test_an_answer_that_is_not_a_gate_leaves_the_default`, `test_the_gate_the_project_named_is_the_default`, `test_the_gate_strong_is_now_passed`, `test_min_strength_is_taken_out`, `test_the_gate_offered_where_the_hook_was_strict_is_passed`, `test_the_gate_question_prints_its_two_choices`, `test_a_framework_the_tree_carries_is_kept`, `test_auto_writes_what_detection_finds`, `test_no_framework_named_writes_what_detection_finds`, `test_the_jest_title_tags_become_comments`, `test_the_xunit_trait_becomes_a_comment`, `test_the_sql_comment_becomes_the_marker`, `test_each_rewritten_test_file_is_backed_up`, `test_the_plugin_copies_go`, `test_a_conftest_holding_only_the_wiring_is_deleted`, `test_the_jest_config_keeps_its_other_reporter`, `test_the_vitest_config_keeps_its_other_reporter`, `test_the_package_json_keeps_its_other_reporter`, `test_each_file_the_wiring_leaves_is_backed_up`, `test_the_picture_reference_of_the_feature_is_removed`, `test_each_design_rewrite_is_backed_up`, `test_a_figma_uri_source_goes_with_its_pin`, `test_a_git_source_and_its_pin_stay`, `test_every_dropped_key_is_named`, `test_a_config_with_no_key_to_drop_prints_no_dropped_line`, `test_the_mutation_question_defaults_to_no`, `test_yes_turns_it_on`, `test_no_engine_means_no_question`, `test_on_windows_a_pytest_project_is_not_asked_to_break_its_code`, `test_at_passed_no_mutation_question_is_asked`, `test_at_passed_no_engine_is_named`, `test_a_mutation_setting_already_written_is_kept`, `test_a_spec_with_no_scope_is_named_and_left_alone`, `test_the_scope_advice_is_given_again_when_nothing_is_pending`, `test_two_specs_with_no_scope_are_named_in_one_line`, `test_an_anchor_with_no_scope_gets_no_advice`, `test_the_retired_windows_tag_becomes_env`, `test_prose_that_is_not_a_tag_is_left_alone`, `test_the_kind_of_test_is_dropped_from_every_proof_line`, `test_an_env_tag_after_the_kind_of_test_is_kept`, `test_hooks_another_tool_wrote_are_left_byte_for_byte`, `test_one_purlin_yml_replaces_the_retired_workflow`, `test_an_azure_remote_gets_the_pipeline_where_init_writes_it`, `test_declining_the_workflow_leaves_it_unwritten`, `test_a_project_with_no_remote_gets_no_workflow`, `test_a_host_init_writes_no_workflow_for_gets_none`, `test_no_proof_for_another_system_means_no_workflow`, `test_the_runner_file_names_only_the_systems_this_machine_is_not`, `test_an_older_copy_of_the_page_is_replaced`, `test_a_project_with_no_page_is_left_without_one`, `test_a_spec_two_migrations_rewrite_has_a_backup_from_each`, `test_the_config_backup_holds_what_it_said_before`, `test_a_backup_is_not_written_twice`, `test_on_a_machine_read_as_windows_only_the_backups_are_left`, `test_status_says_it_even_when_the_config_is_already_clean`, `test_the_run_ends_as_the_status_ends`, `test_a_run_that_leaves_work_names_the_update_above_the_summary`, `test_a_run_over_no_spec_ends_on_the_two_no_spec_lines`, `test_the_pending_list_opens_on_its_count`, `test_each_pending_migration_is_listed_with_its_files`, `test_a_long_file_list_ends_on_how_many_more`, `test_the_files_beside_the_specs_are_counted`, `test_the_removed_hooks_are_counted`, `test_the_rewritten_system_tags_are_counted`, `test_the_specs_that_lose_the_kind_of_test_are_counted`, `test_the_removed_workflows_are_counted`, `test_the_runner_reason_at_passed`, `test_the_runner_reason_at_signed`, `test_the_runner_reason_for_two_systems`, `test_the_runner_file_written_is_named`, `test_the_runner_file_says_when_it_runs`, `test_the_evidence_readme_written_is_named`, `test_the_replaced_page_is_named`, `test_the_removed_plugin_copies_are_counted`, `test_a_tests_setting_with_no_suite_says_so`, `test_the_commit_is_named_on_one_line`, `test_each_backup_is_named_on_a_line_of_its_own`, `test_each_file_rewritten_names_the_fields_it_lost`, `test_an_anchor_one_spec_named_is_named_with_that_spec`, `test_each_file_that_lost_a_line_is_backed_up`, `test_an_anchor_three_specs_named_is_named_with_all_three`, `test_a_global_anchor_named_by_a_spec_gets_no_line`

## Lines a person reads that this lane chose

| Line | Where it prints |
|---|---|
| `# Dashboard page, rewritten with its data, never committed` | the comment above `/purlin-report.html` in the `.gitignore` block setup writes (`templates/gitignore.purlin`) |
| `# .purlin/evidence/ is tracked on purpose: it is the evidence of each run,` / `# for somebody who did not make it to read.` | the last two lines of that block |
| `config: write .purlin/config.json with version and tests alone` | the upgrade's pending list, the `config` migration |
| `workflows: remove the workflows that committed proof files` | the upgrade's pending list, the `workflows` migration |
| `  removed from .purlin/config.json: <keys>`, the keys in the file's order, `test_framework` among them | the upgrade's `config` migration, for every key but `version` and `tests` |
| `  removed <n> workflow(s) that committed proof files; the first purlin:test --remote writes the runner file` | the upgrade's `workflows` migration |

Setup's summary no longer opens on `Gate <gate>. Suites <names>.` or a git host line; it opens
on the first `wrote` or `kept` line. Nothing replaced those lines.

## Differences from section 3's contracts

None. K1: setup and the upgrade write `.purlin/config.json` with `version` then `tests` and no
other key; neither script imports `gate.py`, and `scripts/run/mutation/` is deleted.
`templates/config.json` is `{"tests": []}`: `version` is read from `VERSION` each time, so the
template carries none. No format file of K14 is this lane's.

## Left open, and failures in files this lane does not own

1. **`--gate` and `--mutation` are gone from `scaffold.py`**, so a test that still passes them
   now stops at argparse with exit 2. On this branch, against `d115/base` where each passed:
   - `dev/test_purlin_version.py::test_a_project_init_sets_up_is_stamped_with_the_version_file`
     (`mcp`): passes `--gate passed`.
   - `dev/test_purlin_output.py::TestNoProcessLeft::test_no_command_leaves_a_process_running`
     (`mcp`): passes `--gate`, then reads a settings file setup never wrote.
   - `dev/test_purlin_docs.py::TestQuotedLines`, 6 errors (`docs`): its fixture passes
     `--gate passed`.
   - `dev/test_skill_init.py`, 6 failures (`words`): the flags the skill hands, the gate and
     mutation questions, and the settings keys the skill shows. `skills/init/SKILL.md` still
     describes three questions, `--gate` and `--mutation`.
   - `dev/manual/check_spec.py` (integration's) passes `--gate passed`.
2. **`references/commit_conventions.md`** (`words`) still gives setup's commit as
   `chore(init): set up Purlin at the gate <gate>`; it is now `chore(init): set up Purlin`.
   `references/purlin_commands.md:102`, `references/drift_criteria.md:163` and
   `docs/running-and-evidence.md:306` still name `purlin:init --mutation` or `mutation_engine`.
3. **`dev/run_tests.sh:45`** runs the deleted `dev/test_init_e2e_wiring.sh` (integration's).
4. **The upgrade's no-scope advice stays.** `update.scope_advice` still prints the status's
   `incomplete_line` for a spec with no `> Scope:`. Decision 112 made it no longer a rule and
   no decision cuts it; its tests went with their proofs. Left for the owner.
5. **`test_framework` is named among the removed keys.** `update RULE-50` says every other key
   is removed and named, so the line names it too, though the `tests` setting is written from
   it. Before this change the line left it out.
6. **The `# retired` markers are gone from `scripts/init/update.py` and its test.** They let
   `dev/test_vocabulary.py` step over the spellings the upgrade must read; `words` deletes that
   test, and decision 44 rules out its table.
7. **The fixture `dev/fixtures/upgrade-0.9.5/` is unchanged.** Its `README.md` says
   `dev/test_init_update.py` reads it and never changes it, which holds.

No proof of `scaffold` or `update` was left unbuilt, and none was built to other words than the
spec's.

## What the session cost

This session cannot read its own spend.
