# The `mcp` lane, round 2

Written by the `mcp` lane on 2026-10-01, on `lane/d115-mcp` from `d115/base` at `301bcb46`.
Specs built to: `server`, `config_engine`, `specs`, `schema_spec_format`, `purlin_version`,
`purlin_output`.

## Tests

`python -m pytest dev/test_mcp_server.py dev/test_config_engine.py dev/test_specs_reader.py dev/test_schema_spec_format.py dev/test_purlin_version.py dev/test_purlin_output.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before the first change | 215 | 7 | 5 |
| After the last change | 101 | 2 | 3 |

**Waiting on `setup`, both failing here for one cause:** `scripts/init/scaffold.py` still imports
`purlin.gate`, which this lane deleted, so setup exits 1 with `ImportError: cannot import name
'gate'`. With `gate.py` put back for one run (and taken out again) both passed.

- `purlin_version PROOF-21`: `dev/test_purlin_version.py::test_a_project_init_sets_up_is_stamped_with_the_version_file`
- `purlin_output PROOF-6`: `dev/test_purlin_output.py::TestNoProcessLeft::test_no_command_leaves_a_process_running`

Both now run `scaffold.py --project-root <dir> --yes` with no `--gate`, as setup's one question
leaves it.

**Skipped for a missing tool or system:**

- `purlin_output PROOF-4` and `PROOF-5`: no Python 3.9 on this machine.
- `config_engine PROOF-39`: only Windows refuses a move onto a file held open.

`server PROOF-159`, `PROOF-160` and `config_engine PROOF-38`, tagged `@env(windows)`, have
tests of their own that run and pass on Linux too; their evidence counts on Windows alone.

**Kept, unmarked:** the two `TestPackageHygiene` checks in `dev/test_mcp_server.py` (`package`
added to its `local` set, as the coordinator asked) and the five `TestFrameworks` tests in
`dev/test_specs_reader.py`, which test `run`'s `frameworks.py` and name no proof. Whether the
five stay is left open: no proof holds them, and the module is not this lane's.

The break: `server._call_root` was made to answer the server's own folder for a call naming
none. `server PROOF-166` and `PROOF-167` failed; `git checkout -- scripts/mcp/purlin/server.py`
restored it and all 27 server tests passed.

## Section 4's row

| | Gone | Reworded | To add |
|---|---|---|---|
| As found | 133 | 11 | 11: `server` 164, 166 to 169; `config_engine` 45, 48 to 51; `purlin_output` 7 |
| As left | 0 | 0 | 0 |

Appendix A's script over the six files, last line: `0 gone, 0 reworded, 99 right as they stand.`
Each spec's proofs against the test comments: `server` 25 of 25, `config_engine` 19 of 19,
`specs` 12 of 12, `schema_spec_format` 27 of 27, `purlin_version` 10 of 10, `purlin_output` 6
of 6; each proof named by one comment above one test.

## Reworded comments

- `dev/test_mcp_server.py:174 server PROOF-129 fixed`: asserts the answer opens
  `Purlin status: ws,`, the copied folder's name, where it read the settings' `proj`.
- `dev/test_mcp_server.py:182 server PROOF-160 fixed`: its own test now, the same case and the
  same `Purlin status: ws,`.
- `dev/test_mcp_server.py:261 server PROOF-141 fixed`: the file holds `{` and
  `  "tests": [],}`, and the write is of `tests` as `[]`, naming `project_root`.
- `dev/test_mcp_server.py:322 server PROOF-9 fixed`: the settings hold `tests` as `[]` and the
  read is of `tests`; asserts `{"tests": []}`.
- `dev/test_mcp_server.py:329 server PROOF-134 fixed`: writes `tests` as `[{"name": "pytest"}]`;
  asserts the answer `tests is now [{"name": "pytest"}]; saved to .purlin/config.json.` and that
  the file holds that `tests` and its `version` alone.
- `dev/test_mcp_server.py:341 server PROOF-142 fixed`: the settings hold no `tests`; the read of
  `tests` answers `{\n  "tests": null\n}`.
- `dev/test_config_engine.py:247 config_engine PROOF-32 fixed`: the file holds `{` and
  `  "tests": [],}`, asserted line by line.
- `dev/test_config_engine.py:258 config_engine PROOF-33 fixed`: the file holds
  `{"version": "`, the byte 0xFF, `"}`.
- `dev/test_config_engine.py:264 config_engine PROOF-35 fixed`: the same file as PROOF-32, and
  the write refused is of `tests` as `[]`.
- `dev/test_purlin_version.py:177 purlin_version PROOF-21 fixed`: setup runs with `--yes`
  alone, no `--gate`.
- `dev/test_purlin_version.py:277 purlin_version PROOF-7 stated`: renamed
  `test_the_bump_writes_the_version_file_and_both_json_files`; asserts all three at `1.2.3`
  before and `9.8.7` after.

## Proofs added

`server PROOF-164` (a write of `gate` refused), `166` (a call naming no root), `167` (a root an
earlier call named is not used), `168`, `169` (an empty folder named); `config_engine PROOF-45`,
`48`, `49` (the name from `pyproject.toml`, from `origin`, from the folder, read through
`status.sync_status`), `50`, `51` (the settings warning); `purlin_output PROOF-7` (skills and
the agent definition). `server PROOF-160` and `config_engine PROOF-38` were split from the test
they shared with `PROOF-129` and `PROOF-8`.

## Tests deleted

135 tests. Each named a proof no spec has, or showed what decision 108 or 109 cut. Five more were renamed,
not deleted: `server PROOF-159`, `9`, `134`, `142` and `purlin_version PROOF-7`.

- `dev/test_mcp_server.py::test_a_call_naming_a_project_root_answers_for_it`
- `dev/test_mcp_server.py::test_a_ci_of_gitlab_is_refused`
- `dev/test_mcp_server.py::test_a_config_write_where_there_is_no_project_writes_nothing`
- `dev/test_mcp_server.py::test_a_gate_of_gold_is_refused`
- `dev/test_mcp_server.py::test_a_gate_of_null_is_refused`
- `dev/test_mcp_server.py::test_a_key_this_release_does_not_read_is_refused`
- `dev/test_mcp_server.py::test_a_known_setting_given_no_value_is_refused`
- `dev/test_mcp_server.py::test_a_named_root_with_no_project_says_it_came_from_the_argument`
- `dev/test_mcp_server.py::test_a_notification_the_server_does_not_know_gets_no_response`
- `dev/test_mcp_server.py::test_a_read_naming_no_key_answers_the_whole_file`
- `dev/test_mcp_server.py::test_a_read_of_a_key_stored_as_null_answers_it_as_null`
- `dev/test_mcp_server.py::test_a_root_with_no_project_says_how_to_fix_it_and_nothing_more`
- `dev/test_mcp_server.py::test_a_root_with_no_project_says_so_rather_than_reporting_nothing`
- `dev/test_mcp_server.py::test_a_save_that_fails_says_the_setting_was_not_saved`
- `dev/test_mcp_server.py::test_a_setting_purlin_does_not_know_is_written`
- `dev/test_mcp_server.py::test_a_tool_that_raises_answers_its_error_as_text`
- `dev/test_mcp_server.py::test_a_write_naming_no_key_is_refused`
- `dev/test_mcp_server.py::test_an_audit_parallel_above_16_is_refused`
- `dev/test_mcp_server.py::test_an_engine_purlin_does_not_run_is_refused`
- `dev/test_mcp_server.py::test_an_unknown_action_is_refused`
- `dev/test_mcp_server.py::test_an_unknown_tool_is_an_error`
- `dev/test_mcp_server.py::test_drift_answers_json`
- `dev/test_mcp_server.py::test_drift_answers_the_sentence`
- `dev/test_mcp_server.py::test_drift_where_there_is_no_project_says_so`
- `dev/test_mcp_server.py::test_sync_status_answers_the_sentence`
- `dev/test_mcp_server.py::test_sync_status_answers_the_table`
- `dev/test_mcp_server.py::test_the_named_project_root_is_for_that_call_alone`
- `dev/test_mcp_server.py::test_the_plugin_entry_point_names_the_package`
- `dev/test_config_engine.py::test_a_gate_of_strong_reads_as_passed_with_one_warning`
- `dev/test_config_engine.py::test_a_list_where_an_object_belongs_is_named`
- `dev/test_config_engine.py::test_a_marker_above_the_start_is_found_by_climb`
- `dev/test_config_engine.py::test_a_missing_variable_path_is_passed_over_for_climb`
- `dev/test_config_engine.py::test_adding_a_key_keeps_every_other_key_as_it_was`
- `dev/test_config_engine.py::test_changing_a_key_keeps_every_other_key_as_it_was`
- `dev/test_config_engine.py::test_each_way_has_its_own_sentence`
- `dev/test_config_engine.py::test_min_strength_is_named_as_a_key_not_read`
- `dev/test_config_engine.py::test_the_breaks_are_on_at_the_gate_passed`
- `dev/test_config_engine.py::test_the_breaks_are_on_at_the_gate_signed`
- `dev/test_config_engine.py::test_the_climb_reaches_the_marker_above_the_start`
- `dev/test_config_engine.py::test_the_variable_naming_a_file_gives_way_to_the_climb`
- `dev/test_config_engine.py::test_the_variable_naming_a_missing_path_gives_way_to_the_climb`
- `dev/test_config_engine.py::test_the_variable_naming_an_existing_folder_wins_over_a_marker`
- `dev/test_config_engine.py::test_the_whole_file_is_written_beside_and_moved_onto_it`
- `dev/test_config_engine.py::test_the_written_value_is_what_the_settings_read`
- `dev/test_config_engine.py::test_with_no_marker_the_root_is_the_working_directory`
- `dev/test_specs_reader.py::test_a_bare_windows_tag_is_ignored_and_listed`
- `dev/test_specs_reader.py::test_a_bracket_at_the_end_of_a_rule_enters_its_hash`
- `dev/test_specs_reader.py::test_a_bracket_at_the_end_of_a_rule_is_part_of_its_text`
- `dev/test_specs_reader.py::test_a_changed_word_changes_a_proofs_hash`
- `dev/test_specs_reader.py::test_a_config_that_names_no_engine_runs_no_breaks`
- `dev/test_specs_reader.py::test_a_feature_outside_the_anchors_folder_is_no_anchor`
- `dev/test_specs_reader.py::test_a_local_path_and_a_path_are_not_split`
- `dev/test_specs_reader.py::test_a_local_path_is_the_whole_source`
- `dev/test_specs_reader.py::test_a_named_engine_runs_the_breaks_at_either_gate`
- `dev/test_specs_reader.py::test_a_project_with_no_specs_folder_has_no_specs`
- `dev/test_specs_reader.py::test_a_spec_that_cannot_be_read_is_skipped`
- `dev/test_specs_reader.py::test_a_visual_hash_field_is_ignored_and_listed`
- `dev/test_specs_reader.py::test_an_unreadable_gate_falls_back_loudly`
- `dev/test_specs_reader.py::test_every_spec_is_keyed_by_its_filename_stem`
- `dev/test_specs_reader.py::test_extra_spaces_in_a_rule_keep_its_hash`
- `dev/test_specs_reader.py::test_no_carrier_means_no_warning`
- `dev/test_specs_reader.py::test_reflowing_a_proof_keeps_its_hash`
- `dev/test_specs_reader.py::test_retired_keys_are_ignored_with_one_directive`
- `dev/test_specs_reader.py::test_the_hook_setting_is_a_key_this_release_does_not_read`
- `dev/test_specs_reader.py::test_the_settings_written_out_are_the_ones_a_project_can_name`
- `dev/test_specs_reader.py::test_the_source_lines_path_wins_over_a_path_field`
- `dev/test_specs_reader.py::test_the_warning_names_five_files_and_counts_the_rest`
- `dev/test_schema_spec_format.py::test_a_bare_windows_tag_sets_no_system`
- `dev/test_schema_spec_format.py::test_a_capitalised_system_name_is_not_read`
- `dev/test_schema_spec_format.py::test_a_conflict_hunk_is_warned_of_in_one_line_naming_its_first_line`
- `dev/test_schema_spec_format.py::test_a_distribution_name_is_not_an_operating_system`
- `dev/test_schema_spec_format.py::test_a_doubled_manual_tag_reads_as_one`
- `dev/test_schema_spec_format.py::test_a_first_line_of_neither_form_is_read_by_the_file_name_and_not_warned_of`
- `dev/test_schema_spec_format.py::test_a_global_line_on_a_feature_is_warned_of`
- `dev/test_schema_spec_format.py::test_a_global_line_on_an_anchor_is_warned_of`
- `dev/test_schema_spec_format.py::test_a_heading_one_letter_off_is_neither_section`
- `dev/test_schema_spec_format.py::test_a_highest_proof_line_adds_no_proof`
- `dev/test_schema_spec_format.py::test_a_highest_proof_line_changes_no_fingerprint`
- `dev/test_schema_spec_format.py::test_a_highest_rule_line_adds_no_rule`
- `dev/test_schema_spec_format.py::test_a_highest_rule_line_leaves_the_description_above_it_whole`
- `dev/test_schema_spec_format.py::test_a_line_of_eight_equals_signs_is_not_a_conflict_line`
- `dev/test_schema_spec_format.py::test_a_long_proof_line_that_cannot_be_read_is_quoted_to_60_characters`
- `dev/test_schema_spec_format.py::test_a_manual_tag_carrying_a_value_still_reads_as_manual`
- `dev/test_schema_spec_format.py::test_a_pinned_anchor_carrying_two_lines_gets_the_one_plural_line`
- `dev/test_schema_spec_format.py::test_a_proof_line_naming_one_rule_is_a_proof_of_that_rule_alone`
- `dev/test_schema_spec_format.py::test_a_proof_line_that_cannot_be_read_is_warned_of`
- `dev/test_schema_spec_format.py::test_a_requires_line_adds_no_rule_of_the_anchor_it_names`
- `dev/test_schema_spec_format.py::test_a_rule_with_a_proof_line_and_no_test_reads_no_test_without_the_reason`
- `dev/test_schema_spec_format.py::test_a_rule_with_no_proof_line_and_no_test_reads_no_proof_written`
- `dev/test_schema_spec_format.py::test_a_rule_with_no_proof_line_is_answered_by_a_passing_test_marked_with_its_id`
- `dev/test_schema_spec_format.py::test_a_scope_entry_naming_an_untracked_file_is_warned_of`
- `dev/test_schema_spec_format.py::test_a_scope_entry_that_finds_nothing_is_warned_of`
- `dev/test_schema_spec_format.py::test_a_scope_line_on_an_anchor_is_warned_of`
- `dev/test_schema_spec_format.py::test_a_scope_whose_every_entry_finds_nothing_gets_only_the_existing_line`
- `dev/test_schema_spec_format.py::test_a_spec_proof_ending_in_a_word_that_is_not_a_tag_keeps_it`
- `dev/test_schema_spec_format.py::test_a_spec_proof_ending_manual_and_env_is_read_as_both`
- `dev/test_schema_spec_format.py::test_a_spec_proof_quoting_tags_mid_sentence_carries_no_tag`
- `dev/test_schema_spec_format.py::test_a_spec_proof_with_commas_in_its_prose_keeps_its_trailing_env_tag`
- `dev/test_schema_spec_format.py::test_a_spec_with_no_highest_proof_line_counts_from_its_proofs`
- `dev/test_schema_spec_format.py::test_a_trailing_at_word_that_is_not_a_tag_is_left_in_the_text`
- `dev/test_schema_spec_format.py::test_an_anchor_first_line_makes_a_spec_an_anchor_outside_the_anchors_folder`
- `dev/test_schema_spec_format.py::test_an_anchor_scope_entry_is_never_warned_of_as_finding_no_file`
- `dev/test_schema_spec_format.py::test_an_at_word_after_and_is_prose`
- `dev/test_schema_spec_format.py::test_an_at_word_after_or_is_prose`
- `dev/test_schema_spec_format.py::test_another_at_word_carrying_a_value_is_not_read`
- `dev/test_schema_spec_format.py::test_env_linux_is_read`
- `dev/test_schema_spec_format.py::test_env_macos_is_read`
- `dev/test_schema_spec_format.py::test_manual_then_env_is_read_as_manual_on_that_system`
- `dev/test_schema_spec_format.py::test_note_lines_are_ignored_by_the_parser`
- `dev/test_schema_spec_format.py::test_of_two_env_tags_the_last_written_is_the_system`
- `dev/test_schema_spec_format.py::test_ok`
- `dev/test_schema_spec_format.py::test_the_description_takes_its_continuation_and_not_the_next_field`
- `dev/test_schema_spec_format.py::test_the_pinned_anchor_line_starts_no_process`
- `dev/test_schema_spec_format.py::test_the_reasons_a_broken_spec_fails_are_named_in_order`
- `dev/test_schema_spec_format.py::test_the_scope_keeps_the_order_written_and_is_not_sorted`
- `dev/test_schema_spec_format.py::test_the_section_headings_are_read_in_any_case`
- `dev/test_schema_spec_format.py::test_the_stack_is_read_as_its_one_line`
- `dev/test_schema_spec_format.py::test_two_rule_lines_with_no_id_are_counted_in_the_plural`
- `dev/test_purlin_version.py::test_a_version_on_a_whole_line_comment_is_not_found`
- `dev/test_purlin_version.py::test_a_version_with_whitespace_at_either_end_passes`
- `dev/test_purlin_version.py::test_an_empty_version_file_fails`
- `dev/test_purlin_version.py::test_every_version_field_the_scripts_write_is_read_from_the_file`
- `dev/test_purlin_version.py::test_no_second_copy_of_the_version_row_exists`
- `dev/test_purlin_version.py::test_the_bump_refuses_a_non_version_and_writes_nothing`
- `dev/test_purlin_version.py::test_the_bump_skips_absent_settings_without_creating_them`
- `dev/test_purlin_version.py::test_the_check_names_a_location_with_no_version_key`
- `dev/test_purlin_version.py::test_the_check_passes_a_project_that_agrees`
- `dev/test_purlin_version.py::test_the_check_reports_absent_settings_and_passes`
- `dev/test_purlin_version.py::test_the_one_version_row_names_the_version_file`
- `dev/test_purlin_version.py::test_the_package_carries_no_version_literal`
- `dev/test_purlin_version.py::test_this_checkout_reports_its_own_version_file`
- `dev/test_purlin_version.py::test_two_numbers_are_not_a_version`
- `dev/test_purlin_version.py::test_two_versions_on_two_lines_fail`
- `dev/test_purlin_version.py::test_with_no_version_file_the_package_and_server_report_zero`
- `dev/test_purlin_output.py::test_setup_runs_on_39`

## Lines a person reads that this lane chose

| Line | Where it prints |
|---|---|
| `No Purlin project root at <folder>: .purlin/config.json is not there. Run purlin:init there, or pass the top folder of a Purlin project as project_root.` | Any tool call whose `project_root` names a folder with no settings file. `server PROOF-168` fixes its first sentence; the second is chosen. It replaces two lines that named how the root was found and `PURLIN_PROJECT_ROOT`, which no call reads now. |
| `.purlin/config.json carries <keys>, which this version does not read. Remove them from .purlin/config.json.` | `config_engine.settings_warnings`, where two or more keys are named and one has no upgrade step. K1 gives `Remove it` for one key; `them` is chosen for more. |
| `Next: commit VERSION and every file above in one commit.` | `bash dev/bump_version.sh <semver>`, last line. It ended `then tag v<semver>.`; the release tag is gone and `signed/<version>` is written by `purlin:sign`. |
| `The top folder of the git checkout you are working in, the one holding .purlin/. Every call names it.` | `tools/list`, the description of `project_root` on all three tools, read by the model. |
| `Read .purlin/config.json, or write its tests setting. The file holds version and tests.` | `tools/list`, the description of `purlin_config`. |
| `... Returns JSON with the range and one view of it, for the purlin:drift skill to print.` | `tools/list`, the end of `drift`'s description, which named three role views. |
| `Show one row per spec and the cells of every rule per feature. Reads specs/ and .purlin/evidence/, and returns the table with the next step.` | `tools/list`, `sync_status`'s description, which also named the signatures. |
| The section `A scope naming a file not yet written`, and the new wording of the `> Scope:` row, the proof paragraph and the `@manual` row | `references/formats/spec_format.md`. The two example lines are `states PROOF-279` and `PROOF-280`'s. |

`<tool> needs project_root: pass the top folder of the git checkout you are working in.`,
`gate is not a setting; .purlin/config.json holds version and tests. Nothing was saved.` and
the settings warning ending `Run purlin:init --update.` or `Remove it from .purlin/config.json.`
are section 6's, as written.

## Differences from section 3's contracts

- **K1, the settings warning.** `config_engine.settings_warnings(config)` answers a list: `[]`,
  or the one line. **The line integration adds to `payload.build_payload`**, where it starts
  `warnings`: `warnings.extend(config_engine.settings_warnings(config))`, with `config` the
  settings the payload already reads (`resolve_config(project_root)` where none is passed).
- **K1, which keys the upgrade has a step for: a call no spec makes, left for the owner.**
  `update RULE-50` takes every key but `version` and `tests` out of a 0.9.5 project's file, so
  no key list is written anywhere. `config_engine.UPGRADE_KEYS` lists the keys 0.9.5 wrote
  (`test_framework`, `spec_dir`, `pre_push`, `report`, `digest`, `audit_criteria`,
  `min_strength`) and the ones a 0.10 build wrote (`gate`, `mutation_engine`, `audit_parallel`,
  `ci`, `project_name`), as `config_engine PROOF-50` needs `gate` and `mutation_engine` there.
  Whether the upgrade from 0.9.5 does take a 0.10 build's keys out is `setup`'s.
- **K12.** `drift` is called without `role`; until `anchors` merges, drift still answers its
  role views. `server.handle_request(request)` lost its second argument, the start folder.
- **`server RULE-5`'s startup line** still names the folder the server started in, found by
  `resolve_project_root`, though no call is answered for it. The rule names a root in the
  line, and `config_engine RULE-21` keeps the resolver.
- **K15.** The words `gate`, `mutation_engine`, `min_strength` and `audit_parallel` stand in
  `config_engine.UPGRADE_KEYS` and in the tests of `server PROOF-164` and
  `config_engine PROOF-50`, which name them.
- **`scripts/mcp/purlin/__init__.py`** is unchanged. It still answers `0.0.0` where no
  `VERSION` file is found. The test that allowed that one literal (`purlin_version PROOF-4`) is
  gone with its proof, so nothing now checks for a version string under the package.

## Left open, and failures in files this lane does not own

- `gate.py` is deleted. `scripts/init/scaffold.py` and `scripts/init/update.py` still import it
  (`setup`), which fails `purlin_version PROOF-21` and `purlin_output PROOF-6` until `setup`
  merges first, as planned.
- Stale against spec format 22 and the cut gate, for `words` and `docs`: `manual test` and the
  gate in `docs/team-workflow.md:84`, `docs/specs-and-anchors.md:151`,
  `references/spec_quality_guide.md:266` and `:292`, `references/glossary.md:138` and `:143`,
  and `references/hard_gates.md:24`.
- This repository's `.purlin/config.json` still gives pytest `--ignore=mutants`
  (integration's file).
- `server RULE-36`'s refusals of a write with no key or no value and of an action neither read
  nor write keep their words but have no proof and no test.

## What the session cost

This session cannot read its own spend.
