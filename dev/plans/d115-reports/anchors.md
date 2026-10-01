# Lane `anchors`, round 2

Written by the `anchors` lane on 2026-10-01, on `lane/d115-anchors` from `d115/base` at
`301bcb468`. Specs built to: `upstream`, `drift`, `renumber`, `security_no_dangerous_patterns`.

## Tests

`python -m pytest dev/test_upstream.py dev/test_upstream_notes.py dev/test_drift.py
dev/test_renumber.py dev/test_security.py -q`, on Linux, git 2.43, Python 3.11:

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before my first change | 220 | 0 | 0 |
| After my last change | 94 | 0 | 0 |

The shell suites I own, run one at a time:

| Suite | Before | After |
|---|---|---|
| `dev/test_e2e_anchor_authority.sh` | 7 passed | 7 passed |
| `dev/test_e2e_anchor_rules.sh` | failed: `the table does not end with nothing left to do` | every check passed |
| `dev/test_e2e_external_refs.sh` | 10 passed, case 11 skipped | 10 passed, case 11 skipped; 11 passed after `bash dev/setup-external-refs.sh`, whose folder `dev/external-refs/` git ignores and I removed after |

No test skipped for a missing tool. No test waits on another lane.

## Section 4's row

| | Gone | Reworded | To add | Right as they stand |
|---|---|---|---|---|
| As found | 137 | 28 | 7: `upstream` 60; `drift` 82 to 86, 88 | 62 |
| As left | 0 | 0 | 0 | 97 |

The last line appendix A's script prints for `dev/test_upstream.py dev/test_upstream_notes.py
dev/test_drift.py dev/test_renumber.py dev/test_security.py`:
`0 gone, 0 reworded, 97 right as they stand.`

Every proof of the four specs has one test comment: `drift` 35 of 35, `upstream` 29 of 29,
`renumber` 12 of 12, `security_no_dangerous_patterns` 21 of 21. The three `@env(windows)`
proofs of `upstream`, `PROOF-46`, `48` and `50`, keep their comment on the test they share with
`PROOF-1`, `8` and `11`, as found.

Added: `upstream PROOF-60`; `drift PROOF-82`, `83`, `84`, `85`, `86`, `88`.

## The reworded comments

| Comment | How | What changed, for a `fixed` |
|---|---|---|
| `dev/test_upstream_notes.py:22 upstream PROOF-23` | stated | |
| `dev/test_drift.py:262 drift PROOF-29` | stated | |
| `dev/test_drift.py:324 drift PROOF-9` | stated | |
| `dev/test_drift.py:340 drift PROOF-10` | fixed | asserts the range runs to HEAD, the third commit, as "from the first commit to HEAD" names |
| `dev/test_drift.py:369 drift PROOF-12` | fixed | reads the one view in place of the PM view |
| `dev/test_drift.py:395 drift PROOF-38` | fixed | reads the one view in place of the PM view |
| `dev/test_drift.py:834 drift PROOF-66` | fixed | the pull now changes a spec and a source file, and drift is asked twice, with no role |
| `dev/test_drift.py:485 drift PROOF-17` | fixed | reads the one view, and asserts the row's anchor name and its sha7 equal to the new commit's first 7 characters |
| `dev/test_drift.py:524 drift PROOF-19` | fixed | reads the one view in place of the engineer view |
| `dev/test_drift.py:538 drift PROOF-40` | fixed | reads the one view in place of the engineer view |
| `dev/test_drift.py:590 drift PROOF-20` | fixed | reads the one view, and asserts the line `anchor policy: the source could not be read (begins with "-"). ...` the proof now names |
| `dev/test_drift.py:885 drift PROOF-27` | fixed | asserts the report carries exactly `since` and `view` |
| `dev/test_drift.py:894 drift PROOF-49` | fixed | asserts the view's eleven keys, `anchors_behind` among them and `specs_uncommitted` gone |
| `dev/test_drift.py:922 drift PROOF-67` | fixed | reads the one view in place of the PM and QA views |
| `dev/test_drift.py:931 drift PROOF-68` | fixed | reads the one view in place of the PM and QA views |
| `dev/test_drift.py:942 drift PROOF-69` | fixed | reads the one view in place of the PM and QA views |
| `dev/test_drift.py:655 drift PROOF-70` | fixed | reads the one view in place of every view |
| `dev/test_drift.py:662 drift PROOF-71` | fixed | reads the one view in place of every view |
| `dev/test_drift.py:692 drift PROOF-73` | fixed | reads the one view in place of every view |
| `dev/test_drift.py:736 drift PROOF-75` | fixed | the line now reads `whose wording changed after the test was last changed in <sha7>` and ends `Run purlin:build login to make the test show it; the line clears once the test changes.`; the file is a marked test whose body is committed with it |
| `dev/test_drift.py:747 drift PROOF-76` | fixed | asserts the one line naming `tests/test_login.py:1` ends with the proof's quoted words, in the one view |
| `dev/test_renumber.py:219 renumber PROOF-8` | stated | |
| `dev/test_security.py:264 security_no_dangerous_patterns PROOF-1` | fixed | reads `.py`, `.sh` and `.js` files alone, the three the proof names; `.ts`, `.php` and `.cs` are gone |
| `dev/test_security.py:284 security_no_dangerous_patterns PROOF-2` | fixed | reads `.py` and `.js` files alone |
| `dev/test_security.py:306 security_no_dangerous_patterns PROOF-3` | fixed | reads `.py` files alone for `os.system(`, and asserts the form is found with a space before the `(` |
| `dev/test_security.py:329 security_no_dangerous_patterns PROOF-4` | fixed | reads `.py`, `.sh` and `.js` files alone |
| `dev/test_security.py:350 security_no_dangerous_patterns PROOF-5` | fixed | reads `.py` and `.js` files alone |
| `dev/test_security.py:553 security_no_dangerous_patterns PROOF-10` | stated | |

## Tests deleted

Each names a proof no spec has, and none could show a proof to add.

- `dev/test_upstream.py` (17): `test_a_call_with_no_arguments_exits_2_naming_the_project_root`,
  `test_a_project_root_that_is_no_folder_is_named_with_the_flag`,
  `test_a_source_with_crlf_endings_syncs_to_a_copy_with_no_carriage_return`,
  `test_add_counts_one_rule_in_the_singular`, `test_add_counts_two_rules_in_the_plural`,
  `test_add_from_the_command_line_prints_where_the_copy_went`,
  `test_add_refuses_a_description_in_words`, `test_add_refuses_a_text_file_in_the_project`,
  `test_check_exits_2_for_an_anchor_that_does_not_exist`,
  `test_check_reaches_a_shared_source_once`, `test_help_names_both_commands`,
  `test_json_on_a_current_pin_is_one_object`,
  `test_sync_by_name_reports_an_anchor_from_words_as_error`,
  `test_sync_fetches_a_shared_source_once`, `test_sync_from_the_command_line_prints_the_delta`,
  `test_sync_in_a_project_with_no_anchor_says_so`, `test_sync_reports_a_removed_rule`; and the
  helper `_project_root_help`. Three tests kept lost a gone second comment: `PROOF-47`, `49`, `51`.
- `dev/test_drift.py` (48): `test_a_count_is_accepted_and_git_is_run`,
  `test_a_merge_is_measured_from_main_before_it`,
  `test_a_plain_commit_after_the_merge_is_not_an_action`,
  `test_a_rebase_is_measured_from_before_its_first_step`,
  `test_a_checkout_is_measured_from_the_branch_it_left`,
  `test_a_reset_after_a_pull_is_the_newest_action`,
  `test_a_repository_with_no_action_measures_its_last_twenty`,
  `test_a_repository_of_three_commits_measures_all_three`,
  `test_a_repository_of_one_commit_names_the_last_commit`,
  `test_every_view_opens_by_naming_the_pull`,
  `test_every_view_opens_by_naming_a_merge_with_conflicts`,
  `test_a_change_to_no_spec_names_no_rule`, `test_code_changed_under_a_directory_scope`,
  `test_a_scope_with_no_rule_behind_it`, `test_changed_files_under_no_scope`,
  `test_rules_no_test_has_run_for_are_named`, `test_one_rule_no_test_has_run_for_is_named`,
  `test_rules_with_a_passing_run_are_not_named`,
  `test_a_feature_with_a_run_is_out_of_date_and_one_without_is_not`,
  `test_two_features_out_of_date_are_named_together`,
  `test_a_deleted_file_a_file_entry_names_counts`,
  `test_a_deleted_file_under_a_folder_entry_counts`,
  `test_a_deleted_file_a_glob_matches_counts`,
  `test_a_deleted_file_no_scope_covers_joins_the_uncovered`,
  `test_a_covered_file_removed_after_the_pull_is_not_uncovered`,
  `test_an_anchor_with_rules_of_its_own_goes_behind`, `test_an_anchor_still_at_its_pin_is_not_named`,
  `test_an_azure_devops_source_out_of_reach_reads_error`,
  `test_a_description_in_words_reads_error`,
  `test_a_source_naming_the_fd_transport_is_refused`,
  `test_a_source_carrying_a_newline_is_refused`,
  `test_a_source_holding_ext_and_a_dash_inside_is_not_refused`,
  `test_three_anchors_of_one_source_list_it_once`,
  `test_the_row_names_the_spec_not_the_repository`,
  `test_test_files_changed_and_what_they_cover`, `test_a_rule_to_write_a_test_for`,
  `test_the_rules_to_fix_and_not_the_rest`, `test_nothing_that_stops_a_release_prints_nothing`,
  `test_the_qa_view_carries_the_items_it_printed`,
  `test_one_spec_edited_ends_every_view_with_one`,
  `test_a_spec_edited_and_one_not_tracked_end_every_view_with_two`,
  `test_specs_all_committed_print_no_such_line`,
  `test_the_engineer_view_carries_its_fixed_keys`, `test_the_qa_view_carries_its_fixed_keys`,
  `test_the_qa_role_narrows_the_answer_to_its_view`,
  `test_the_report_text_has_no_indent_and_no_space_after_a_separator`,
  `test_no_default_branch`, `test_a_comment_whose_proof_is_unchanged`; and the helpers
  `_marked`, `_evidence_file`, `_deleted_under`, `ONE_DELETED`, `_anchor_rows`, `_not_a_spec`,
  `_left`, `_qa_view_left`, `_qa_lines_left`, `_write_crlf`, `_edited_spec`,
  `_every_view_holds`. Fifteen more were renamed to state their proof and are listed above.
- `dev/test_security.py` (68): every planted case for TypeScript, PHP and C#; the shell,
  JavaScript and Python cases of the proofs the anchor cut (`PROOF-8`, `12`, `13`, `15` to `19`,
  `23`, `25` to `27`, `30`, `32`, `33`, `37` to `46`, `49` to `91`):
  `test_a_comment_writing_shell_true_is_found`, `test_a_comparison_is_not_counted`,
  `test_a_count_hands_its_commits_after_end_of_options`,
  `test_a_date_hands_its_commit_after_end_of_options`,
  `test_a_javascript_comment_naming_eval_is_not_counted`,
  `test_a_javascript_word_containing_eval_is_not_counted`,
  `test_a_launch_imported_by_name_given_a_list_is_not_counted`,
  `test_a_launch_imported_under_an_alias_given_a_string_is_found`,
  `test_a_name_beginning_with_token_is_found`, `test_a_password_field_in_javascript_is_found`,
  `test_a_password_in_single_quotes_is_found`, `test_a_php_comment_naming_system_is_not_counted`,
  `test_a_python_word_containing_eval_is_not_counted`,
  `test_a_shell_comment_naming_eval_is_not_counted`,
  `test_a_shell_word_containing_eval_is_not_counted`, `test_a_token_field_in_typescript_is_found`,
  `test_a_token_in_a_shell_file_is_found`, `test_an_empty_api_key_is_not_counted`,
  `test_an_empty_password_field_in_javascript_is_not_counted`,
  `test_an_empty_password_in_a_python_dict_is_not_counted`,
  `test_csharp_argument_list_is_not_counted`, `test_csharp_arguments_set_to_a_string_is_found`,
  `test_csharp_use_shell_execute_false_is_not_counted`,
  `test_csharp_use_shell_execute_true_is_found`,
  `test_csharp_use_shell_execute_true_unspaced_is_found`,
  `test_javascript_child_process_exec_is_found`,
  `test_javascript_eval_before_a_trailing_comment_is_found`, `test_javascript_eval_is_found`,
  `test_javascript_exec_sync_is_found`, `test_javascript_new_function_is_found`,
  `test_javascript_shell_false_is_not_counted`, `test_javascript_shell_true_is_found`,
  `test_javascript_spawn_given_a_string_argument_is_found`,
  `test_javascript_spawn_given_one_command_string_is_found`,
  `test_javascript_spawn_with_an_args_array_is_not_counted`, `test_php_backticks_are_found`,
  `test_php_eval_is_found`, `test_php_exec_is_found`, `test_php_passthru_with_a_space_is_found`,
  `test_php_proc_open_given_a_string_is_found`, `test_php_proc_open_given_an_array_is_not_counted`,
  `test_php_shell_exec_is_found`, `test_php_system_is_found`,
  `test_popen_imported_by_name_given_a_string_is_found`,
  `test_python_eval_before_a_trailing_comment_is_found`, `test_python_exec_with_a_space_is_found`,
  `test_python_os_system_with_a_space_is_found`,
  `test_python_popen_given_a_list_written_in_place_is_not_counted`,
  `test_python_popen_given_a_name_is_found_with_its_line`,
  `test_python_popen_given_a_star_is_found_with_its_line`,
  `test_python_popen_given_a_string_is_found`, `test_python_popen_given_an_f_string_is_found`,
  `test_python_run_given_a_name_is_found`, `test_python_run_given_a_star_is_not_counted`,
  `test_python_shell_true_with_spaces_is_found`,
  `test_run_imported_by_name_given_a_string_is_found`, `test_shell_backticks_are_found`,
  `test_shell_eval_after_and_and_is_found`, `test_shell_eval_after_if_is_found`,
  `test_shell_eval_at_the_start_of_a_line_is_found`,
  `test_shell_eval_in_a_substitution_is_found`, `test_shell_eval_indented_is_found`,
  `test_typescript_child_process_exec_is_found`, `test_typescript_eval_is_found`,
  `test_typescript_exec_file_sync_given_a_name_is_found`, `test_typescript_exec_sync_is_found`,
  `test_typescript_new_function_is_found`, `test_typescript_shell_true_is_found`; and the
  helpers `_assert_launch_found_at`, `_each_revision_follows_end_of_options`, with the
  TypeScript, PHP and C# rows of every pattern table.

## What was built

- **`scripts/mcp/purlin/drift.py`.** No role: `drift(project_root, since=None)` answers exactly
  `since` and `view`, the view exactly the eleven keys of `drift RULE-42`. The engineer and QA
  views and every line the status already prints go: code changed under a scope, files under no
  scope, rules with no test, features out of date, `Left to do`, and the spec files not
  committed. Drift no longer builds the payload. The stale test comments are
  `wording.stale_comments`' entries for the proofs or test files the range changed (K4), so
  `drift RULE-35` holds as `wording.py` defines the test's last change. A checkout that leaves
  HEAD where it stood is passed over (`PROOF-86`). A number written twice at either end of the
  range is left out of the rules and proofs added, changed and moved (`PROOF-85`). The range's
  spec files are read with `git diff ... -- specs/` and its test files with the marked files as
  paths, and `rev-list` is handed HEAD's sha after `--end-of-options`.
- **`scripts/spec/renumber.py`.** Step 3 moves a comment to the `now_under` that
  `wording.stale_comments` names, so the comment is read where its test was last changed
  (`renumber RULE-6`).
- **`scripts/anchor/upstream.py`.** Unchanged: every proof passed on the merged line.
  `upstream PROOF-60` is the status's own pin line, and the status reads the source without
  pulling.
- **`references/formats/anchor_format.md`, format 12.** The template's rule reads "For every
  <X> in the project, <Y holds>"; a section on writing a rule for a project with nothing to
  check and the `nothing to check:` skip; the status and drift check the source and pull
  nothing; `purlin:anchor sync` commits nothing; `.purlin/tests.md`, the gate and the release
  are gone.
- **`references/drift_criteria.md`, criteria 13.** One view and its eleven keys; the checkout
  that brought nothing in; the test comment line in K4's words, defined by `wording.py`; the
  settings `version` and `tests` alone; every tool call names `project_root`.
- **`dev/test_e2e_anchor_rules.sh`.** Commits the results with `--test --commit` before the
  last status read, then checks `Tests: met` and the last line
  `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`.
- Every settings file my tests and suites write holds `version` and `tests` alone.

The deliberate break: in `compute_drift` the stale comment lines were left out of the view.
Three tests failed, `drift PROOF-75`, `76` and `84`; `git checkout -- scripts/mcp/purlin/drift.py`
restored it and the file passed again.

## Lines a person reads that I chose

No line the code prints is new. Two check labels in `dev/test_e2e_anchor_rules.sh`, printed as
`    ok: <label>` or `    FAIL: <label>` when the suite runs:

- `the status says the tests are met`
- `the table ends on the line that names the sign-off`

The prose of the two format files is mine; the lines it quotes are the specs' and section 6's.

## Differences from section 3's contracts

- **K12.** `compute_drift(project_root, since=None, network=True)` loses `data`, since nothing
  in the view reads the payload. `drift.VIEW_KEYS` is added. `comments_changed` takes the
  range in place of the changed files. `comment_reworded` and `COMMENT_CHANGED`,
  `COMMENT_CHECK` and `COMMENT_MOVE` go; the renumber helper reads `wording.py`.
- **A rule written twice** is also left out of `rules_changed`, `rules_added` and
  `rules_removed`. `drift RULE-31` names proofs alone; a rule written twice would otherwise read
  as changed the same way.

## Left open, and failures in files I do not own

1. **`scripts/mcp/purlin/server.py` (`mcp`) no longer imports.** It reads `drift_module.ROLES`
   for the `role` property's `enum` and calls `drift_module.drift(..., role=...)`. Both go with
   K12's "the MCP drift tool loses its role argument". Until `mcp` lands, every test file that
   imports the server fails to collect: `dev/test_mcp_server.py`, `dev/test_purlin_output.py`,
   `dev/test_purlin_version.py`, and `dev/test_states.py` (`states`', frozen). The fix is two
   lines in `server.py`: drop the `role` property and the `role=` argument.
2. **`dev/test_skill_drift.py` (`words`)**: `test_it_repeats_no_definition_from_the_criteria`
   fails because `dev/skill_checks.py` looks for the `eng` and `qa` tables in
   `references/drift_criteria.md`, which criteria 13 no longer holds. It passes on the base.
3. **Stale mentions of drift's roles**, for `words` and `docs`: `skills/drift/SKILL.md` lines
   20 to 22 and 53; `references/purlin_commands.md` lines 40, 91 and 136;
   `references/glossary.md` line 156; `agents/purlin.md` lines 94, 98 and 111;
   `docs/working-together.md` lines 20, 55 and 65; `docs/team-workflow.md`, `docs/qa-guide.md`
   and `docs/getting-started.md` line 183; `README.md` line 130.
4. **`wording.py` (`states`) hands git commits with no `--end-of-options`** in two fallback
   paths: `git show <sha>:<path>` where the batched read missed a spec that moved folder, and
   `git rev-list --topo-order --max-count=1 <shas>` for commits made in the same second. Drift
   now runs `wording.py` (its scope names it), so `security_no_dangerous_patterns PROOF-10`
   would fail in a project where either path is taken. No test takes either today.
5. **`renumber.py`'s `git grep` and `git blame` take a branch ref with no `--end-of-options`**:
   git 2.43 refuses that option in both. The refs come from `git for-each-ref` under
   `refs/heads/` and `refs/remotes/`, so each begins `refs/` and never `-`. No proof covers it;
   left as found.
6. **Drift's diff names every marked test file as a path**: on Windows a project with thousands
   of marked files could pass the command line's length limit. No proof covers it.

No proof was left unbuilt, and no proof could not be built to as worded. No file under `specs/`
changed. No file outside the list I own was committed.

One slip, corrected: a command of mine moved `dev/test_states.py` over `/dev/null` in this
session's container. I restored the file with `git checkout -- dev/test_states.py` and
recreated `/dev/null`; `git status` showed no change to it before any commit.

## What the session cost

The session cannot read its own spend.
