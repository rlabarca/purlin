# Lane `dashboard`, round 2

Built on `lane/d115-dashboard` from round 1's merged line, locally, with playwright from `.venv`.
Not pushed: integration reads the branch.

## Tests

`python -m pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_report_refresh.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before the first change | 179 | 8 | 0 |
| After the last | 70 | 0 | 0 |

Before: `test_purlin_report.py` 160 passed and 4 failed, `test_purlin_report_board_layout.py`
16 passed, `test_report_refresh.py` 3 passed and 4 failed. Nothing skipped for a missing tool.
No test waits on another lane.

`states PROOF-58` in `dev/test_states.py` passes: `dev/test_states.py` whole, 67 passed.
`dev/test_signatures.py`, `dev/test_export.py`, `dev/test_security.py` and
`dev/test_mcp_server.py` fail only what `round1.md` already lists (`package PROOF-5` and the
six of `mcp`).

Broken on purpose once: the `Tests` box given the wrong word in `app.js`; `PROOF-223` and
`PROOF-225` failed; restored.

## Section 4's row

| | Gone | Reworded | To add |
|---|---|---|---|
| As found | 125 | 28 | 9, and 3 for decision 117 |
| As left | 0 | 0 | 0 |

Appendix A's script over the three files: `0 gone, 0 reworded, 68 right as they stand.`
Each of the spec's 68 proofs has exactly one test comment.

## The reworded comments

Line numbers as the files stand now.

- `dev/test_purlin_report.py:253 purlin_report PROOF-3 fixed`: builds the page itself and asserts 0 hex colours outside the token block, with no exception list.
- `dev/test_purlin_report.py:320 purlin_report PROOF-9 stated`
- `dev/test_purlin_report.py:330 purlin_report PROOF-124 stated`
- `dev/test_purlin_report.py:340 purlin_report PROOF-32 fixed`: reads the `Last run` row itself and asserts `ci` then an age; the row is text, no link.
- `dev/test_purlin_report.py:361 purlin_report PROOF-92 stated`
- `dev/test_purlin_report.py:508 purlin_report PROOF-40 fixed`: `Strong` reads `2 of 4`, no percentage.
- `dev/test_purlin_report.py:553 purlin_report PROOF-97 stated`
- `dev/test_purlin_report.py:657 purlin_report PROOF-117 stated`
- `dev/test_purlin_report.py:671 purlin_report PROOF-15 fixed`: the strong row reads `STRONG` alone.
- `dev/test_purlin_report.py:717 purlin_report PROOF-20 fixed`: schema 14 in the notice; no step box, no top-bar box and no table.
- `dev/test_purlin_report.py:761 purlin_report PROOF-22 stated`
- `dev/test_purlin_report.py:773 purlin_report PROOF-138 fixed`: presses the text `Back to the board`; asserts 5 spec rows and no rule screen, no tab.
- `dev/test_purlin_report.py:809 purlin_report PROOF-144 fixed`: gives the audit the finding and the explanation the proof names and asserts the three lines in order.
- `dev/test_purlin_report.py:950 purlin_report PROOF-63 fixed`: the words are `strong` and `audit` alone; no gate; no filter buttons walked.
- `dev/test_purlin_report.py:962 purlin_report PROOF-103 fixed`: the words are `proof`, `strong` and `audit`.
- `dev/test_purlin_report.py:1039 purlin_report PROOF-65 fixed`: the project's settings hold `version` and `tests`; the line carries no badge and the dot's hover reads `passed`.
- `dev/test_purlin_report.py:1152 purlin_report PROOF-66 fixed`: the board with its first spec open, then the first rule's screen; no unfolded proofs.
- `dev/test_purlin_report.py:1161 purlin_report PROOF-104 fixed`: the same, light.
- `dev/test_purlin_report.py:1211 purlin_report PROOF-155 fixed`: read on the rule's screen.
- `dev/test_purlin_report.py:1229 purlin_report PROOF-180 fixed`: read on the rule's screen, each line named.
- `dev/test_purlin_report.py:1243 purlin_report PROOF-69 fixed`: read on the rule's screen; no button count.
- `dev/test_purlin_report.py:1276 purlin_report PROOF-108 fixed`: asserts the heading, `receipt` then `RULE-1`, in place of a tab.
- `dev/test_purlin_report.py:1288 purlin_report PROOF-109 fixed`: the same for `checkout_design`.
- `dev/test_purlin_report.py:1313 purlin_report PROOF-165 stated`
- `dev/test_purlin_report.py:1381 purlin_report PROOF-203 fixed`: the section stands below the boxes, not below filter buttons.
- `dev/test_purlin_report_board_layout.py:59 purlin_report PROOF-75 fixed`: login open, then `RULE-1`'s screen, on the sample as it is; the values measured are the counts, labels, boxes and rule ids of the page as built.
- `dev/test_report_refresh.py:68 purlin_report PROOF-59 fixed`: `purlin:sign --answers <file> --version 1.0.0`, no release step; asserts `signed 1.0.0 at` the tagged commit's first 7 characters.
- `dev/test_report_refresh.py:121 purlin_report PROOF-61 stated`

Added: `PROOF-223`, `225`, `227`, `228`, `229`, `232` in `dev/test_purlin_report.py`;
`PROOF-230`, `231`, `233` in `dev/test_report_refresh.py`; and for decision 117 `PROOF-234`,
`235`, `236` in `dev/test_purlin_report.py`.

## The spec, for decision 117 alone

`specs/dashboard/purlin_report.md` gains `RULE-78` and `PROOF-234` to `PROOF-236`;
`> Highest-Rule: 78`, `> Highest-Proof: 236`. Nothing else under `specs/` changed.

## Tests deleted

- `test_purlin_report.py::test_the_build_is_reproducible (PROOF-1)`
- `test_purlin_report.py::test_the_page_is_one_file_under_the_line_budget (PROOF-2)`
- `test_purlin_report.py::test_the_board_opens_on_the_boxes_under_the_gate (PROOF-7)`
- `test_purlin_report.py::test_a_passed_project_with_no_proof_line_shows_no_proofs_column (PROOF-123)`
- `test_purlin_report.py::test_an_audited_passed_project_with_no_proof_line_drops_proofs (PROOF-125)`
- `test_purlin_report.py::test_a_signed_project_keeps_proofs_with_no_proof_line (PROOF-126)`
- `test_purlin_report.py::test_a_rule_that_ran_on_linux_and_macos_shows_both (PROOF-91)`
- `test_purlin_report.py::test_the_board_draws_no_system_box (PROOF-93)`
- `test_purlin_report.py::test_the_board_opens_in_the_dark_theme (PROOF-12)`
- `test_purlin_report.py::test_the_theme_button_swaps_back_to_dark (PROOF-129)`
- `test_purlin_report.py::test_the_pressed_theme_button_reads_dark_theme (PROOF-183)`
- `test_purlin_report.py::test_the_board_sits_on_the_brand_navy (PROOF-30)`
- `test_purlin_report.py::test_the_passed_gate_has_one_box (PROOF-80)`
- `test_purlin_report.py::test_a_step_every_rule_reached_is_green (PROOF-81)`
- `test_purlin_report.py::test_the_total_is_the_payloads_count (PROOF-171)`
- `test_purlin_report.py::test_one_rule_reads_rule_total (PROOF-172)`
- `test_purlin_report.py::test_an_audited_passed_project_has_passing_and_strong (PROOF-174)`
- `test_purlin_report.py::test_a_proof_no_test_runs_is_named_beside_the_total (PROOF-84)`
- `test_purlin_report.py::test_a_strength_nobody_measured_is_not_shown (PROOF-176)`
- `test_purlin_report.py::test_a_percentage_says_what_it_is (PROOF-177)`
- `test_purlin_report.py::test_every_step_box_carries_its_hover (PROOF-45)`
- `test_purlin_report.py::test_the_no_proof_box_names_the_specs_it_counts (PROOF-98)`
- `test_purlin_report.py::test_the_no_proof_box_at_zero_is_green (PROOF-115)`
- `test_purlin_report.py::test_the_write_a_proof_filter_leaves_the_rules_with_no_proof (PROOF-116)`
- `test_purlin_report.py::test_a_band_has_two_ends_on_one_line (PROOF-77)`
- `test_purlin_report.py::test_a_narrow_band_puts_its_count_beneath_its_name (PROOF-95)`
- `test_purlin_report.py::test_a_folded_band_opens_again_on_space (PROOF-143)`
- `test_purlin_report.py::test_an_open_feature_row_closes_on_the_next_press (PROOF-127)`
- `test_purlin_report.py::test_a_spec_with_no_description_shows_none (PROOF-118)`
- `test_purlin_report.py::test_to_strengthen_leaves_the_rules_to_strengthen (PROOF-13)`
- `test_purlin_report.py::test_to_test_leaves_the_rules_to_test (PROOF-85)`
- `test_purlin_report.py::test_choosing_another_button_moves_the_choice (PROOF-14)`
- `test_purlin_report.py::test_choosing_the_chosen_button_again_shows_every_rule (PROOF-87)`
- `test_purlin_report.py::test_choosing_to_correct_leaves_every_rule_showing (PROOF-181)`
- `test_purlin_report.py::test_the_buttons_are_the_lines_of_what_is_left (PROOF-35)`
- `test_purlin_report.py::test_the_passed_gate_offers_its_one_line_as_a_button (PROOF-86)`
- `test_purlin_report.py::test_a_buttons_count_is_the_payloads_not_the_pages (PROOF-130)`
- `test_purlin_report.py::test_with_nothing_left_the_last_line_stands_above_the_table (PROOF-83)`
- `test_purlin_report.py::test_a_button_leaves_as_many_rules_as_its_count (PROOF-46)`
- `test_purlin_report.py::test_a_chosen_button_names_its_command (PROOF-119)`
- `test_purlin_report.py::test_the_command_line_is_text (PROOF-120)`
- `test_purlin_report.py::test_with_no_button_chosen_no_command_line_shows (PROOF-134)`
- `test_purlin_report.py::test_the_rule_screen_has_one_row_per_cell_the_gate_reaches (PROOF-53)`
- `test_purlin_report.py::test_the_rule_screen_links_to_the_git_host (PROOF-16)`
- `test_purlin_report.py::test_a_rule_with_no_remote_has_no_links (PROOF-136)`
- `test_purlin_report.py::test_the_working_tree_notice_shows_on_the_board (PROOF-88)`
- `test_purlin_report.py::test_the_open_rule_is_the_last_tab (PROOF-24)`
- `test_purlin_report.py::test_the_open_rules_tab_stays_clickable (PROOF-137)`
- `test_purlin_report.py::test_the_link_back_reads_board (PROOF-25)`
- `test_purlin_report.py::test_coming_back_to_an_old_tab_reloads_it (PROOF-27)`
- `test_purlin_report.py::test_the_freshness_line_is_a_button_styled_as_the_theme_button (PROOF-28)`
- `test_purlin_report.py::test_old_data_says_it_is_old_and_how_to_refresh (PROOF-178)`
- `test_purlin_report.py::test_fresh_data_says_how_to_refresh (PROOF-179)`
- `test_purlin_report.py::test_pressing_the_freshness_line_reloads (PROOF-139)`
- `test_purlin_report.py::test_the_age_recomputes_every_minute_from_the_same_payload (PROOF-29)`
- `test_purlin_report.py::test_the_docs_screenshots_come_from_the_fixtures (PROOF-23)`
- `test_purlin_report.py::test_the_audit_panel_reads_an_undecided_audit (PROOF-54)`
- `test_purlin_report.py::test_the_audit_panel_reads_a_strong_audit (PROOF-145)`
- `test_purlin_report.py::test_the_audit_panel_with_no_strength_measured (PROOF-146)`
- `test_purlin_report.py::test_the_top_bar_states_the_signed_tag (PROOF-55)`
- `test_purlin_report.py::test_the_top_bar_names_no_signed_tag (PROOF-148)`
- `test_purlin_report.py::test_the_top_bar_at_passed_shows_no_tag (PROOF-150)`
- `test_purlin_report.py::test_a_spec_that_names_no_files_says_so (PROOF-62)`
- `test_purlin_report.py::test_a_failed_rule_at_passed_shows_no_higher_word (PROOF-99)`
- `test_purlin_report.py::test_a_partial_rule_at_passed_shows_no_higher_word (PROOF-100)`
- `test_purlin_report.py::test_a_rule_not_run_at_passed_shows_no_higher_word (PROOF-101)`
- `test_purlin_report.py::test_a_rule_out_of_date_at_passed_shows_no_higher_word (PROOF-102)`
- `test_purlin_report.py::test_a_failing_test_marked_with_the_rules_id_shows_failed (PROOF-152)`
- `test_purlin_report.py::test_the_contrast_check_names_a_text_under_7_to_1 (PROOF-105)`
- `test_purlin_report.py::test_every_rule_opens_folded (PROOF-68)`
- `test_purlin_report.py::test_a_failed_proof_draws_its_rules_count_in_the_warn_tone (PROOF-153)`
- `test_purlin_report.py::test_enter_unfolds_a_rule_and_keeps_the_focus (PROOF-154)`
- `test_purlin_report.py::test_enter_again_folds_the_rule (PROOF-156)`
- `test_purlin_report.py::test_reopening_a_spec_folds_its_rules (PROOF-157)`
- `test_purlin_report.py::test_a_rule_with_no_proof_shows_the_test_marked_with_its_id (PROOF-158)`
- `test_purlin_report.py::test_with_no_proof_line_the_button_counts_tests (PROOF-159)`
- `test_purlin_report.py::test_with_no_proof_line_a_rule_with_no_test_has_no_button (PROOF-160)`
- `test_purlin_report.py::test_a_filter_that_hides_a_rule_hides_its_proofs (PROOF-70)`
- `test_purlin_report.py::test_the_rule_screen_draws_the_proofs_the_board_drew (PROOF-106)`
- `test_purlin_report.py::test_the_rules_cell_is_the_specs_own_count (PROOF-71)`
- `test_purlin_report.py::test_a_real_projects_anchor_lists_its_rules_alone (PROOF-110)`
- `test_purlin_report.py::test_a_real_projects_two_rule_1s_open_their_own_screens (PROOF-111)`
- `test_purlin_report.py::test_a_waiting_cell_is_neutral (PROOF-79)`
- `test_purlin_report.py::test_a_waiting_cell_says_what_it_waits_for (PROOF-164)`
- `test_purlin_report.py::test_a_rule_that_reached_no_step_carries_no_badge (PROOF-166)`
- `test_purlin_report.py::test_a_failed_rule_at_passed_carries_failed_alone (PROOF-168)`
- `test_purlin_report.py::test_a_step_not_reached_draws_no_badge (PROOF-169)`
- `test_purlin_report.py::test_a_strong_audit_with_a_finding_reads_strong_then_it (PROOF-187)`
- `test_purlin_report.py::test_a_share_of_85_7_reads_85_on_the_board_and_the_rule (PROOF-188)`
- `test_purlin_report.py::test_the_tag_chip_names_its_commit_in_its_hover (PROOF-197)`
- `test_purlin_report.py::test_a_spec_no_audit_read_says_so_in_its_hover (PROOF-190)`
- `test_purlin_report.py::test_no_signed_tag_says_what_writes_one (PROOF-192)`
- `test_purlin_report.py::test_a_filter_no_rule_is_left_under_says_so (PROOF-193)`
- `test_purlin_report.py::test_a_rule_with_no_test_names_the_build (PROOF-194)`
- `test_purlin_report.py::test_a_proof_no_run_listed_tests_for_says_so (PROOF-195)`
- `test_purlin_report.py::test_an_open_rule_gone_from_the_data_says_so (PROOF-196)`
- `test_purlin_report.py::test_a_filter_keeps_the_anchors_it_accepts (PROOF-205)`
- `test_purlin_report.py::test_a_filter_that_leaves_no_anchor_hides_the_section (PROOF-206)`
- `test_purlin_report.py::test_an_anchors_row_opens_and_closes (PROOF-207)`
- `test_purlin_report.py::test_an_anchors_strong_cell_shows_no_strength (PROOF-209)`
- `test_purlin_report.py::test_a_spec_to_repair_has_its_filter_button (PROOF-215)`
- `test_purlin_report.py::test_no_signed_column_at_the_gate_signed (PROOF-218)`
- `test_purlin_report.py::test_an_audited_project_shows_the_strong_column (PROOF-219)`
- `test_purlin_report.py::test_a_project_no_audit_read_shows_no_strong_column (PROOF-220)`
- `test_purlin_report.py::test_a_hand_check_at_signed_is_checked_in_the_walk (PROOF-221)`
- `test_purlin_report.py::test_a_hand_check_at_passed_is_listed_as_not_checked (PROOF-222)`
- `test_purlin_report_board_layout.py::test_every_heading_starts_where_its_cells_start (PROOF-33)`
- `test_purlin_report_board_layout.py::test_no_text_on_the_board_is_set_under_thirteen_pixels (PROOF-41)`
- `test_purlin_report_board_layout.py::test_every_column_fits_from_1024_up (PROOF-42)`
- `test_purlin_report_board_layout.py::test_no_heading_overflows_and_no_count_breaks (PROOF-140)`
- `test_purlin_report_board_layout.py::test_nothing_on_the_table_is_aligned_right (PROOF-141)`
- `test_purlin_report_board_layout.py::test_a_long_tests_value_is_one_line_from_1024_up (PROOF-142)`
- `test_purlin_report_board_layout.py::test_every_screen_fits_every_width_in_the_light_theme (PROOF-112)`
- `test_purlin_report_board_layout.py::test_a_long_tests_value_is_one_line_at_every_width (PROOF-113)`
- `test_purlin_report_board_layout.py::test_three_boxes_to_a_row_at_768 (PROOF-76)`
- `test_purlin_report_board_layout.py::test_every_box_on_one_row_at_1024 (PROOF-161)`
- `test_purlin_report_board_layout.py::test_two_boxes_to_a_row_at_390 (PROOF-162)`
- `test_purlin_report_board_layout.py::test_a_narrow_board_is_blocks_of_labelled_pairs (PROOF-163)`
- `test_purlin_report_board_layout.py::test_the_boxes_in_a_row_are_one_height (PROOF-175)`
- `test_purlin_report_board_layout.py::test_the_total_is_one_line_at_every_width (PROOF-173)`
- `test_purlin_report_board_layout.py::test_a_narrow_anchors_section_is_blocks_of_labelled_pairs (PROOF-208)`
- `test_report_refresh.py::test_status_writes_the_data_file (PROOF-56)`
- `test_report_refresh.py::test_a_test_run_writes_the_data_file (PROOF-57)`
- `test_report_refresh.py::test_an_audit_writes_the_data_file (PROOF-58)`
- `test_report_refresh.py::test_status_after_an_edit_by_hand_writes_the_new_rule (PROOF-151)`

Helpers deleted with them, in `dev/test_purlin_report.py`: `with_only_a_comment_to_correct`,
`stamp_ago`, `chip_labels`, `chip_counts`, `KINDS`, `chip_for`, `pressed`, `panel_heads`,
`box_hovers`, `COMMAND_LINE`, `freshness_hover`, `UNDECIDED`, `top_bar`,
`_no_tag_below_signed`, `_login_rule_1_reads`, `TOGGLES`, `toggles`, `unfolded`, `toggle_for`,
`_bare_login_toggles`, `_anchor_project`, `anchor_payload`, `BASE_COLUMNS`.

## Lines a person reads that this lane chose

| Line | Where it prints |
|---|---|
| `PROOF-3: its tests missed a bug planted at src/auth/lockout.py:27.` | the `Audit` panel on a rule's page, once per planted bug whose result is `survived` |
| `Before` and `After` | the two labels under that line, each beside the lines the audit recorded, set in the monospace face |
| `Tests` and `Sign-off` | the labels of the top bar's two boxes (`purlin_report RULE-7` names them) |
| each sentence of the audit's `explanation`, as the audit wrote it | the `Audit` panel, after the findings, for a strong and a weak rule alike |

Section 6's `detached at a1b2c3d, written 10:42` and the information line as a notice in the
neutral tone, below the warnings and above the boxes, with no heading, are used as written.

Tones chosen, no words: `Tests` reads in the pass tone when `met` and the warn tone when
`not met`; `Sign-off` in the pass tone for `signed <version> at <commit>`, the warn tone for
`signed <version>, <n> commits since` and the neutral tone for `not signed`.

## Differences from section 3's contracts

- **K13, a project with no page.** `refresh` writes `purlin-report.html` where the project's
  copy differs, and where there is none only if git ignores the path or the root is no git
  checkout. K13 says an absent page is always written. The helpers' projects
  (`dev/mcp_project.py`, `dev/sign_project.py`, `dev/run_project.py`) do not ignore the page, so
  an untracked page there reads as uncommitted work: the payload's `dirty` turns true and
  `purlin:sign` refuses the second sign-off. A project `purlin:init` set up ignores it
  (`scaffold RULE-67`), so a fresh clone gets its page on the first `purlin:status`, as
  section 9 intends.
- **K6, a rule's `audit`.** The page and the fixtures are built to nine fields, `explanation`
  and `breaks` among them (decision 117). The payload in this branch still writes seven;
  another agent adds the two. Until then a real project's `Audit` panel shows neither.
- `report_data.write_page(project_root)` is added and called by `refresh`.

## What the look found, and what was fixed

Looked at with playwright, headless, dark and light, at 1500, 1024 and 390 pixels, the three
fixtures, the board and seven rule pages: 60 screenshots.

- At 390 the `Sign-off` box cut `signed 0.1.0, 4 commits since` with an ellipsis. Fixed: under
  600 pixels each box sets its label above its value, and the value shows whole.
- A planted bug's lines kept their indent and broke in two at 390. Fixed: the shared indent is
  taken off, and a line too long for its box scrolls inside the box.
- No sideways scroll at any width. No count, label, box value or rule id on two lines. The
  contrast proofs pass in both themes over all three fixtures.
- At 1024 the two boxes and the theme button sit on a second row of the top bar: the header
  line and the boxes together are wider than the bar. Left as it is; whole items wrap.

## Left open, for the owner or integration

1. **`PROOF-198` says the notices stand "above the first box".** The test reads that as the
   first step box. The top bar's two boxes are above the notices.
2. **No proof holds the information notices or the detached line.** Both are built to
   section 6 and looked at on the team fixture; `purlin_report` has no rule for either.
3. **A hand check whose rule the audit found weak shows no note.** The payload carries the
   notes as the strong cell's reasons only while that cell reads `checked at sign-off`.
4. **The strong row repeats the findings the `Audit` panel lists beneath it**, since the
   payload gives them as the cell's reasons. On a rule with a planted bug that is a long row.
5. **A hand check's `Audit` panel reads `No audit has read this rule's text, proof and test
   yet.`**, as `RULE-39` words it for a rule with no audit entry.
6. **The solo fixture now has a failing rule**, invoice `RULE-2`, as `PROOF-225` describes the
   sample: 2 of 5 pass, where 3 did. The regulated fixture reads `signed 0.1.0, 4 commits
   since`. All three are stamped `2026-10-01T10:42:13Z` on `main` at `a1b2c3d`. Their counts,
   sentences and `left` were worked out by `states` and `summary`, not typed.
7. **The page shows no list of what is left to do**: the filter buttons are cut and no rule
   puts the list anywhere else. The `Tests` box says `not met` and no more.
8. **`dev/capture_doc_screenshots.py`** now opens login for the board and login `RULE-3` for
   the rule. No proof holds it since `PROOF-23` went; integration runs it at step 12.
9. **`docs/dashboard.md`** describes the filters, the tabs and the gate chip; that is `docs`'.

## Not staged

`scripts/report/purlin-report.html` is rebuilt in the worktree and not committed. The
screenshots are in the session's scratch folder, `dashboard-lane/`.

## Cost

This session cannot read its own spend.
