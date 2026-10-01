# Lane `words`, round 2

Run locally on the Mac, in the worktree `purlin-wt/d115-words`, on `lane/d115-words` from round
1's merged line at `301bcb468`. Not pushed: integration reads the branch locally.

## Tests

`python -m pytest dev/test_skill_*.py dev/test_purlin_agent.py dev/test_vocabulary.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before the first change, 13 files | 242 | 1 | 0 |
| After the last, 11 files | 21 | 0 | 0 |

The one failure before was `dev/test_skill_status.py::TestNextStep::test_every_kind_of_left_to_do_line_has_a_row_running_its_command`,
which round 1 listed. No test skipped for a missing tool. No test waits on another lane.

Each spec's proofs against its test comments: `skill_anchor` 2 and 2, `skill_audit` 2 and 2,
`skill_build` 1 and 1, `skill_drift` 2 and 2, `skill_init` 3 and 3, `skill_sign` 2 and 2,
`skill_spec` 1 and 1, `skill_spec_from_code` 1 and 1, `skill_status` 3 and 3, `skill_test` 2
and 2, `purlin_agent` 2 and 2: 21 proofs, 21 tests.

Broken on purpose, twice, each restored with `git checkout -- agents/purlin.md`: with
`purlin:test --all --commit` taken out of the agent definition, `purlin_agent PROOF-49` failed;
with `in the main checkout` taken out of the worktree sentence, `PROOF-50` failed.

## Section 4's row

| | Gone | Reworded | Right | To add |
|---|---|---|---|---|
| As found, with `test_skill_export.py` | 235 | 4 | 1 | 16 |
| As found, the eleven files kept | 219 | 4 | 1 | 16 |
| As left | 0 | 0 | 21 | 0 |

Appendix A's script over the eleven files prints `0 gone, 0 reworded, 21 right as they stand.`

Added, 16: `skill_audit` 56, 59; `skill_build` 51; `skill_drift` 43, 46; `skill_sign` 63, 64;
`skill_spec` 62; `skill_spec_from_code` 167; `skill_status` 37, 38, 39; `skill_test` 52, 55;
`purlin_agent` 49, 50.

## The reworded comments

- `dev/test_skill_anchor.py:19 skill_anchor PROOF-2 fixed`: the test asserted the two run lines
  for `add` and `sync`; it now asserts the skill's text holds each of the six files the proof
  names and that `must_name` reports nothing.
- `dev/test_skill_anchor.py:26 skill_anchor PROOF-16 fixed`: the test asserted two sentences of
  the `sync` section; it now asserts the five commands the proof names and that nothing is
  reported.
- `dev/test_skill_init.py:42 skill_init PROOF-2 fixed`: the run line was asserted with
  `--project-root` and `--gate`; it is now asserted with `--project-root` alone, on one line with
  the interpreter lookup and the script.
- `dev/test_skill_init.py:60 skill_init PROOF-42 fixed`: the test asserted the two references; it
  now asserts `.purlin/config.json`, `.purlin/evidence/` and `specs/` as well.

`skill_init PROOF-24` was right as it stood. Its test is rewritten in the same shape: it runs
`scaffold.py --help`, asserts exit 0, and asserts every flag on the skill's run lines and in its
flag table is one the usage lists.

## Tests deleted

243 tests stood in the 13 files; all 243 names are gone, and 21 new tests stand in their place.
No test is kept for a proof no spec holds, and none shows that a removed thing is absent.

**`dev/test_purlin_agent.py`**, 11 of 11: `test_the_frontmatter_names_the_agent`, `test_the_core_loop_is_stated_once_in_order`, `test_the_four_nevers_each_forbid_their_own_thing`, `test_the_routing_table_covers_the_three_roles`, `test_it_reads_the_state_before_it_answers`, `test_the_first_call_names_the_project_root`, `test_it_stays_under_its_ceiling`, `test_a_copy_of_exactly_135_lines_is_not_refused`, `test_it_says_what_a_rename_moves`, `test_it_says_every_run_ends_on_left_to_do`, `test_it_says_how_a_release_is_made`

**`dev/test_skill_anchor.py`**, 17 of 17: `test_the_skill_opens_with_its_name_and_a_one_line_description`, `test_the_command_reference_has_a_row_for_the_command`, `test_the_script_is_given_with_add_and_with_sync`, `test_the_sync_section_names_the_check_drift_runs`, `test_every_closing_outcome_names_the_next_step`, `test_the_skill_holds_at_most_160_lines`, `test_a_skill_of_exactly_160_lines_passes`, `test_a_pin_is_a_commit_never_a_branch`, `test_a_pinned_rule_is_never_edited_in_place`, `test_a_change_goes_to_the_source_repository`, `test_a_local_rule_goes_in_a_local_anchor_or_each_feature`, `test_an_anchor_repository_is_for_two_or_more_projects`, `test_an_anchor_carries_no_scope_and_names_no_spec`, `test_a_rule_not_checkable_everywhere_goes_in_each_feature`, `test_the_first_anchor_creates_the_folder`, `test_the_source_is_a_spec_in_a_repository`, `test_a_new_anchor_is_committed_with_the_create_prefix`

**`dev/test_skill_audit.py`**, 21 of 21: `test_the_frontmatter_names_the_skill_on_one_line`, `test_the_command_reference_has_a_row_with_a_purpose`, `test_one_line_runs_the_run_script_with_audit`, `test_one_sentence_says_nobody_runs_the_runner_arm`, `test_it_closes_on_the_first_line_of_left_to_do`, `test_it_stays_under_its_ceiling`, `test_a_copy_of_exactly_105_lines_is_not_refused`, `test_a_copy_of_106_lines_is_refused_with_its_count`, `test_both_sources_count_under_every_gate`, `test_both_evidence_folders_are_named`, `test_the_passed_row_reads_with_the_ai_audit_and_measures_nothing`, `test_the_signed_row_runs_what_passed_runs_and_counts_both`, `test_the_audit_line_comes_before_the_ending`, `test_the_commit_sentence_names_the_evidence_subject`, `test_nothing_the_audit_found_sets_the_exit_code`, `test_the_audit_is_a_tool_nothing_waits_on`, `test_the_arm_timeout_is_in_the_usage_and_passed_on`, `test_the_audit_is_written_into_the_local_file`, `test_one_sentence_says_what_a_file_keeps`, `test_remote_belongs_to_purlin_test`, `test_the_first_sync_status_names_the_project_root`

**`dev/test_skill_build.py`**, 17 of 17: `test_the_frontmatter_names_the_skill_and_the_reference_lists_it`, `test_it_reads_the_state_and_runs_the_tests_through_the_test_skill`, `test_it_closes_by_naming_the_next_step_for_each_outcome`, `test_it_stays_under_its_ceiling`, `test_the_commit_it_asks_for_is_named_in_full`, `test_changeset_is_never_left_out`, `test_decisions_and_review_are_left_out_when_empty`, `test_the_conventions_render_a_build_commit`, `test_it_keeps_the_scope_in_the_commit_with_the_code`, `test_it_looks_for_an_existing_test_before_it_writes_one`, `test_its_example_shows_the_marker_above_a_test`, `test_a_rule_with_no_proof_is_marked_with_its_own_id`, `test_it_reads_the_state_at_the_project_root`, `test_every_anchor_holds_across_the_project`, `test_it_repairs_the_comments_that_are_nearly_markers`, `test_the_test_run_sets_the_test_command`, `test_a_number_written_twice_goes_to_renumbering`

**`dev/test_skill_drift.py`**, 16 of 16: `test_the_frontmatter_names_the_skill_on_one_line`, `test_the_command_reference_carries_a_row_for_drift`, `test_it_infers_the_role_and_says_which`, `test_it_says_drift_reads_only_this_checkout`, `test_it_says_which_line_keeps_a_number_written_twice`, `test_it_sends_a_number_written_twice_to_the_renumbering`, `test_the_data_comes_from_the_drift_tool`, `test_it_points_at_the_criteria_for_what_a_line_means`, `test_it_says_to_restate_nothing_and_invent_nothing`, `test_it_says_to_print_the_lines_as_they_come`, `test_it_repeats_no_definition_from_the_criteria`, `test_it_closes_by_naming_the_next_step`, `test_every_kind_of_line_has_its_next_step`, `test_it_stays_under_its_ceiling`, `test_a_skill_of_exactly_150_lines_is_let_through`, `test_a_skill_of_151_lines_is_reported`

**`dev/test_skill_export.py`** (file deleted), 16 of 16: `test_the_frontmatter_names_the_skill_on_one_line`, `test_the_command_reference_has_a_row_for_export`, `test_each_form_of_the_command_has_a_line`, `test_a_line_runs_the_export_script`, `test_it_makes_no_claim_of_compliance`, `test_it_calls_the_package_evidence_for_review`, `test_the_table_of_states_names_the_two_states`, `test_the_not_finished_row_says_left_holds_left_to_do`, `test_the_last_heading_names_the_next_step`, `test_each_stop_short_names_the_next_step`, `test_each_state_names_the_next_step`, `test_every_outcome_row_gives_a_directive`, `test_it_names_the_release_run`, `test_it_quotes_the_no_version_line`, `test_it_stays_under_its_ceiling`, `test_the_system_of_record_holds_the_document_authority_and_signature`

**`dev/test_skill_init.py`**, 23 of 23: `test_the_frontmatter_names_the_skill_on_one_line`, `test_the_command_reference_has_a_row_for_init`, `test_one_line_runs_the_script_with_the_root_and_the_gate`, `test_the_five_flags_are_handed_to_the_reader`, `test_the_yes_row_says_it_commits`, `test_run_it_says_how_the_answers_reach_the_script`, `test_every_flag_handed_is_one_the_script_takes`, `test_it_closes_with_a_directive_for_each_state`, `test_it_is_at_most_250_lines`, `test_it_names_the_three_questions_in_order`, `test_the_second_question_is_asked_only_where_it_runs`, `test_the_gate_table_lists_the_two_answers_in_order`, `test_setup_at_signed_asks_the_three_questions_the_skill_quotes`, `test_setup_at_passed_asks_the_gate_then_the_commit`, `test_the_third_question_is_the_commit`, `test_the_gate_question_offers_the_two_gates_in_order`, `test_no_answer_to_the_second_question_leaves_mutation_off`, `test_it_shows_the_six_settings`, `test_setup_writes_the_keys_the_skill_shows`, `test_one_sentence_says_audit_parallel_is_not_asked`, `test_one_sentence_says_it_writes_the_evidence_folder`, `test_it_writes_an_empty_tests_setting_and_installs_nothing`, `test_it_points_at_the_two_references`

**`dev/test_skill_sign.py`**, 16 of 16: `test_the_frontmatter_names_the_skill_on_one_line`, `test_the_command_reference_carries_a_row_for_sign`, `test_it_closes_by_naming_the_next_step`, `test_it_stays_under_its_ceiling`, `test_a_sign_off_counts_on_two_conditions`, `test_it_says_whose_sign_off_counts`, `test_it_shows_the_key_commands_and_offers_to_run_them`, `test_it_never_pushes`, `test_with_no_version_it_asks_and_offers_to_write_one`, `test_it_quotes_the_no_version_line`, `test_a_rule_is_never_narrowed_to_lose_an_observation`, `test_each_stop_shows_each_proofs_tied_test`, `test_it_shows_first_and_asks_about_each_stop`, `test_it_writes_the_answers_then_walks_with_them`, `test_at_passed_nothing_is_signed`, `test_the_first_sign_off_writes_the_tag`

**`dev/test_skill_spec.py`**, 30 of 30: `test_the_skill_opens_with_its_name_and_a_one_line_description`, `test_the_command_reference_has_a_row_for_the_command`, `test_a_new_rule_counts_from_the_highest_ever_held`, `test_it_writes_the_highest_rule_into_the_spec`, `test_it_reads_the_state_at_the_project_root`, `test_the_intake_table_says_what_to_do_with_each_input`, `test_a_change_is_made_in_place_and_nothing_is_renumbered`, `test_after_a_merge_drift_names_the_line_that_moves`, `test_two_pins_resolve_to_the_newer`, `test_the_guide_lets_a_proof_name_a_library_s_public_names`, `test_the_guide_lets_one_proof_name_a_list_of_like_inputs`, `test_the_guide_s_stuck_row_names_the_runner_file`, `test_it_closes_by_naming_the_build`, `test_it_stays_under_its_ceiling`, `test_a_skill_of_exactly_210_lines_is_accepted`, `test_it_writes_the_scope_on_every_spec`, `test_it_prints_the_rules_and_asks_before_it_saves`, `test_it_drafts_every_proof_against_the_guideline`, `test_it_writes_each_proof_as_one_case`, `test_the_guide_says_one_proof_one_case`, `test_a_new_proof_counts_from_the_highest_ever_held`, `test_it_writes_the_highest_proof_into_the_spec`, `test_the_spec_is_committed_before_the_closing_line`, `test_a_warned_field_is_taken_out`, `test_the_number_on_the_default_branch_keeps_it`, `test_a_moved_rule_has_its_audit_read_again`, `test_every_conflict_line_is_taken_out`, `test_the_guide_puts_the_weight_of_a_risk_into_proofs`, `test_renumbering_shows_the_dry_run_and_asks`, `test_a_comment_on_another_branch_is_named_not_touched`

**`dev/test_skill_spec_from_code.py`**, 31 of 31: `test_the_frontmatter_names_the_skill_and_describes_it_on_one_line`, `test_the_command_reference_has_a_row_with_the_purpose`, `test_it_passes_the_project_root_and_sends_a_bare_project_to_init`, `test_it_makes_a_branch_on_a_detached_head_before_the_first_commit`, `test_it_names_the_first_of_three_next_steps_that_applies`, `test_it_stays_under_its_ceiling`, `test_a_skill_of_exactly_130_lines_is_accepted`, `test_it_offers_the_marker_and_writes_no_new_test`, `test_the_survey_walks_the_tree_once`, `test_the_taxonomy_lists_each_feature_with_its_files`, `test_it_stops_on_the_list_until_the_person_agrees`, `test_it_writes_one_spec_at_a_time_after_the_shared_rules`, `test_project_rules_go_once_into_an_anchor_the_rest_into_each_spec`, `test_each_spec_is_committed_with_the_comments_it_adds`, `test_the_position_file_holds_the_list_and_what_is_written`, `test_the_report_gives_one_line_per_feature`, `test_the_report_ends_on_the_files_with_no_rule`, `test_the_conventions_put_the_comments_in_the_spec_commit`, `test_a_test_is_left_untied_for_five_reasons`, `test_a_commented_out_test_or_a_benchmark_is_not_a_test`, `test_every_rule_is_written_from_what_its_test_expects`, `test_it_says_at_hand_over_that_every_rule_is_a_draft`, `test_code_no_caller_can_reach_gets_no_rule`, `test_it_says_what_a_caller_reaches_in_each_language`, `test_no_implementation_is_copied_into_a_rule`, `test_it_writes_no_evidence_and_no_signature`, `test_an_unobservable_behaviour_goes_to_the_description`, `test_the_spec_it_writes_carries_its_highest_rule`, `test_the_taxonomy_step_says_how_many_features_is_normal`, `test_a_proof_a_test_already_shows_never_names_the_test`, `test_the_suites_own_helpers_are_code_no_caller_reaches`

**`dev/test_skill_status.py`**, 15 of 15: `test_the_frontmatter_names_the_skill_and_describes_it_in_one_line`, `test_the_command_reference_has_a_row_for_status_with_its_purpose`, `test_it_prints_the_lines_the_tool_returned_and_never_recounts`, `test_the_first_call_names_the_project_root`, `test_a_number_written_twice_is_sent_to_the_renumbering`, `test_the_last_section_is_headed_as_the_next_step`, `test_the_last_section_names_the_first_line_of_left_to_do`, `test_every_row_gives_a_directive_but_nothing_left_to_do`, `test_every_kind_of_left_to_do_line_has_a_row_running_its_command`, `test_the_skill_is_at_most_100_lines`, `test_a_skill_of_exactly_100_lines_passes`, `test_a_skill_of_101_lines_is_refused`, `test_the_skill_shows_the_named_form`, `test_the_command_reference_names_the_form_with_a_name`, `test_the_with_a_name_section_says_what_it_prints`

**`dev/test_skill_test.py`**, 27 of 27: `test_the_shipped_frontmatter_names_the_skill_on_one_line`, `test_the_shipped_command_reference_has_a_row_for_the_skill`, `test_the_shipped_skill_runs_the_script_with_test`, `test_the_shipped_skill_gives_each_exit_code_its_meaning_on_one_line`, `test_the_shipped_skill_says_a_run_cannot_make_an_audit_or_signature`, `test_the_shipped_closing_section_directs_every_outcome`, `test_the_shipped_skill_is_at_most_120_lines`, `test_a_copy_of_exactly_120_lines_is_not_reported`, `test_a_copy_of_121_lines_is_reported_with_its_count`, `test_the_shipped_skill_names_the_two_files_the_run_writes`, `test_the_shipped_skill_names_the_two_commits_in_order`, `test_the_shipped_skill_names_the_two_lines_a_commit_prints`, `test_the_shipped_skill_says_it_never_pushes`, `test_the_shipped_skill_says_the_run_ends_on_the_summary`, `test_the_shipped_skill_says_the_first_line_left_is_the_next_step`, `test_the_shipped_paragraph_gives_the_four_reasons`, `test_the_shipped_paragraph_runs_only_the_test_files`, `test_the_shipped_usage_lists_all`, `test_the_shipped_usage_names_the_release_run`, `test_the_shipped_paragraph_carries_the_whole_nothing_line`, `test_the_shipped_row_for_a_suggestion_asks_writes_and_runs_again`, `test_the_run_with_no_tool_prints_the_line_the_row_matches`, `test_the_shipped_row_carries_the_comparison`, `test_the_shipped_row_runs_the_line_a_tool_needs_once_agreed`, `test_the_shipped_step_names_the_program_to_install`, `test_the_arm_timeout_is_in_the_usage_and_passed_on`, `test_the_first_sync_status_names_the_project_root`

**`dev/test_vocabulary.py`** (file deleted), 3 of 3: `test_no_removed_spelling_comes_back`, `test_a_spelling_split_by_a_line_break_is_caught`, `test_one_line_hits_are_left_to_the_pass_over_lines`
Helpers deleted from `dev/skill_checks.py`, each used only by a deleted test: `CEILINGS`,
`COMMANDS`, `ROLES`, `BASH`, `frontmatter`, `field`, `runs_on`, `sections`, `section`, `carries`,
`in_order`, `frontmatter_problems`, `command_rows`, `closing_outcomes`, `next_step_problems`,
`undirected_outcome_problems`, `NOTHING_LEFT`, `sentence_with`, `on_copy`, `replace`, `refusals`,
`frontmatter_refusals`, `next_step_refusals`, `ceiling_problems`, `skill_ceiling_problems`,
`table_rows`, `resub`, `swap_first`. It no longer imports `purlin_run`.

## Lines a person reads that this lane chose

Section 6's lines for this lane are used as written: the agent's worktree sentence, the
`project_root` sentence in the agent and in every skill but drift's, where it stands under the
tool call, the three lines of `references/writing_style.md`, `CLAUDE.md`'s step 3, and the ten
`RELEASE_NOTES.md` lines, followed by the format numbers.

Chosen here:

| Line | Where it shows |
|---|---|
| `Show the two facts, every rule's cells and what is left to do` | the status skill's description, and its Purpose in `references/purlin_commands.md` |
| `Run the tests, the heuristic spot tests, one planted bug per proof and the model's reading, then write what it found into the evidence` | the audit skill's, the same two places |
| `Build the evidence package from the committed evidence, walk its hand checks with a person, then sign it in a signed commit` | the sign skill's, the same |
| `Report what changed since your last pull` | the drift skill's, the same |
| `Set a project up for Purlin` | the init skill's, the same |
| `→ Run: purlin:sign`, when a person chooses to sign | the status and test skills, the next step after `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` |
| `→ Run: purlin:test --commit` | the status and test skills, after `<n> features whose results are not committed` |
| `→ Ask the person, then run: purlin:test --remote --commit-runner` | the test skill, after the runner file is written |
| `→ Ask the person for the new version, then run: purlin:sign --version <version>` | the sign skill, after the refusal that names a new version |
| `→ Run:` the command it names | the sign skill, after a refusal naming a test run |
| `→ Run: purlin:build <feature>, then purlin:test --all --commit` | the sign skill, after `Stopped at` |
| `→ Fix what it named, then run: purlin:sign` | the sign skill, after the commit or the package could not be written |
| `Specs and marked tests: → Run: purlin:test, which suggests the test commands on its first run.` | the init skill's closing list |
| `A rule reads weak: → Run: purlin:build <feature>, then purlin:audit again.` | the audit skill's closing list |
| `The hand-off is run and commit: purlin:test --all --commit runs every test and commits the specs, tests and settings, then the evidence that names them, and purlin:test --remote does the same for the proofs tagged for a system this machine is not.` | `agents/purlin.md`, "The core loop" |
| `purlin:drift → purlin:spec → purlin:build → purlin:test → purlin:test --all --commit → purlin:sign` | `agents/purlin.md`, the loop |
| `"it is ready for sign-off", "hand it to QA"` routed to `purlin:test --all --commit`; `"what do we hand to the system of record?"` routed to the evidence package `purlin:sign` committed | `agents/purlin.md`, "Routing" |
| The headings `The two facts`, `What is left to do`, `Which evidence counts`, `Where a runner runs`, `When a sign-off counts`, `What signed/<version> means`, `What stops nothing`, `Platforms`, `What stands behind an instruction` | `references/evidence_and_signoff.md` |
| `The tag binds the signing alone: it says what was signed and by whom, and makes no claim about who was entitled to sign.` | `references/evidence_and_signoff.md`, the tag's definition |
| New glossary words: `settings`, `the two facts`, `test comment to correct`, `information`, `hand-off`, `this version of the code`, `nothing to check`, `heuristic spot test`, `planted bug`, `explanation`, `checkout` | `references/glossary.md` |
| `"Purlin plants one bug per proof"` and `"4 of 5 rules strong (80%)"` | `references/writing_style.md`, two examples that named breaking the code and test strength |
| `- Poor: "The settings screen meets the contrast standard."` `- Good: "Every screen in the project meets the contrast standard."` | `references/spec_quality_guide.md`, "A rule for the whole project", the pair that teaches decision 107 |
| `In more words:` | `RELEASE_NOTES.md`, between section 6's lines and the longer entries under them |

## Differences from section 3's contracts

- **K16, `must_name(skill, commands=(), paths=())`**: the signature and the problem line are as
  given. It searches with the file's line wrapping collapsed, so a command the prose wraps over
  two lines is named. Added beside it: `not_named(text, names)`, `same_line(rel, names)`,
  `sentences_with(rel, names)`, `flat(text)` and `copy_without(rel, name)`, which reads a skill as
  a copy with every occurrence of a name taken out, wrapped ones included.
- **K12**: every skill and the agent carry section 6's sentence. The drift skill shows the call
  as `drift(project_root="<the top folder of the git checkout>")`.
- Nothing else in section 3 is produced by this lane.

## What the skills say that round 2's other lanes build

The skills describe the product as the specs and contracts have it. These lines are true once
the named lane lands, and not before:

- `remote`: the three runner lines of K11 and `purlin:test --remote --commit-runner`, in the test
  skill, `references/purlin_commands.md` and `references/commit_conventions.md` (the commit
  `ci: the Purlin runner for <GitHub or Azure DevOps>`); the runner starting on a push to a
  `run/*` branch alone.
- `anchors`: drift's one view with no role; the status and drift saying an anchor is behind
  without pulling.
- `setup`: one question, the settings of `version` and `tests`, no runner file, the commit
  `chore(init): set up Purlin`, the three refusals quoted in the init skill from
  `scaffold RULE-82`. The init skill hands a reader `--project-root`, `--yes` and `--update`
  alone, so `skill_init PROOF-24` passes on today's script and on `setup`'s.
- `mcp`: the refusal of a tool call that names no `project_root`, quoted in
  `references/purlin_commands.md`.
- `dashboard`: the page written with its data, in `references/purlin_commands.md` and the
  release notes.

## Left unbuilt, left open, and failures in files this lane does not own

1. **`dev/test_purlin_docs.py`, 3 new failures, `docs`' file.** Before this lane 1 failed, after
   it 4. `TestCommandTable::test_each_row_carries_the_references_purpose_sentence` and
   `test_every_command_of_the_reference_has_a_row`: `README.md`'s command table still carries
   the old Purpose sentences for status, audit, sign, drift and init, and a row for
   `purlin:export`. `TestLinks::test_every_relative_link_names_a_file_and_a_heading`: `README.md`
   and seven pages under `docs/` link to `references/hard_gates.md`, three of them to
   `#where-a-runner-runs-and-when-a-project-has-one`. The page is now
   `references/evidence_and_signoff.md` and that heading is `Where a runner runs`.
2. **Three files of `remote` name `references/hard_gates.md` in a comment**:
   `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml`,
   `.github/workflows/purlin.yml`, and the fixture `dev/fixtures/consumer-ci/.github/workflows/purlin.yml`.
3. **`dev/test_init_update.py:9` names `dev/test_vocabulary.py`** in its docstring; the file is
   deleted. `setup`'s file.
4. **K15's grep for `gate` needs a word boundary.** Over this lane's files, `\bgates?\b` and
   `gated` find nothing outside `RELEASE_NOTES.md`. A plain `gate` finds `delegate` and
   `propagates` in `CLAUDE.md`. Three English uses were reworded to keep the grep empty:
   `Password-gated` and `The gate type` in `references/rule_examples.md`, and
   `conditional gate`, `conditional gates` and `role and permission gates` in
   `references/spec_quality_guide.md`. `does not apply` was reworded twice the same way, to
   `has no way to set a pulled rule aside`.
5. **The upgrade's steps in `RELEASE_NOTES.md` carry no migration ids.** They are written from
   `update`'s rules, in nine steps. `setup` owns the ids; where it keeps today's, the owner may
   want them back in the notes.
6. **`→ Run: purlin:init --update`** is still described in the status skill and
   `references/purlin_commands.md`, since the status still prints it (round 1, "For the owner",
   11).
7. **The `Strong` column.** The status skill says it shows `<n> of <rules>` where the audit read
   a rule. Nothing in this lane's specs holds it; it is as `board.py` builds it today.
8. **`references/review_criteria.md` is `audit`'s.** The audit skill and the glossary point at
   it for each check and name the six checks in short; they restate none of its findings' words
   but the three the audit prints.
9. **Call left open: whether `skills/spec-from-code` leaves the command reference.** Decision
   109 keeps it "out of the core docs". It stays a row under "Supporting" in
   `references/purlin_commands.md`, marked optional, because the reference is the one home of
   every skill's one-liner. `docs` decides for `README.md`.
10. **Call left open: the status skill's first paragraph** says the skill "writes no file you
    commit; it refreshes the dashboard's data, which git ignores", where it said "This skill
    writes nothing". No proof holds either.

No proof of the eleven specs was left unbuilt, and none could not be built to as worded.

## What the session cost

Not readable from inside the session. It ran locally, so no cloud credit was spent.
