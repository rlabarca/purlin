# Lane `remote`, round 2

Written by the `remote` lane on 2026-10-01, on `lane/d115-remote` from `d115/base` at
`301bcb468`. Spec: `host`, 56 rules' worth of ids, 42 proofs.

## Tests

`python -m pytest dev/test_host.py dev/test_host_pathspec.py dev/test_remote.py dev/test_consumer_ci.py -q`

| | Passed | Failed | Skipped |
|---|---|---|---|
| Before my first change | 111 | 1 | 0 |
| After my last change | 41 | 0 | 1 |

- The failure before: `test_consumer_ci.py::test_purlin_reads_the_fixture_as_one_feature_with_a_linux_proof`
  (the payload's `gate` key). Its comment was gone; the test is deleted.
- The skip after: `dev/test_host.py::test_on_windows_gh_cmd_is_found_and_the_run_goes_round`,
  `host PROOF-117`, tagged `@env(windows)`: it runs on Windows alone. No test skipped for a
  missing tool.
- No test of mine waits on another lane.
- `dev/test_run_script.py::TestTheRunnerOnFirstNeed`, `run_script PROOF-272` and `PROOF-273`:
  both pass through my code, with the test unchanged. The whole of `dev/test_run_script.py`:
  59 passed, 1 skipped.

## Section 4's row

| | Gone | Reworded | To add | Right |
|---|---|---|---|---|
| As found | 79 | 23 | 4: `host` 140 to 143 | 15 |
| As left | 0 | 0 | 0 | 42 |

Appendix A's script over my four files, last line:
`0 gone, 0 reworded, 42 right as they stand.` Every one of the 42 proofs of `host` has exactly
one test comment.

Added: `host PROOF-140`, `141`, `143` in `dev/test_host.py`, `PROOF-142` in
`dev/test_consumer_ci.py`. `PROOF-117` was right as it stood but shared one test with
`PROOF-24`; it now has a test of its own (one proof, one test), skipped off Windows.

## The reworded comments

| Where | Proof | How |
|---|---|---|
| `dev/test_host.py:288` | `host PROOF-5` | stated |
| `dev/test_host.py:315` | `host PROOF-54` | stated |
| `dev/test_host.py:368` | `host PROOF-22` | stated |
| `dev/test_host.py:385` | `host PROOF-91` | stated |
| `dev/test_host.py:397` | `host PROOF-94` | stated |
| `dev/test_host.py:413` | `host PROOF-58` | stated |
| `dev/test_host.py:452` | `host PROOF-7` | stated |
| `dev/test_host.py:483` | `host PROOF-8` | fixed |
| `dev/test_host.py:533` | `host PROOF-62` | stated |
| `dev/test_host.py:561` | `host PROOF-99` | stated |
| `dev/test_host.py:583` | `host PROOF-39` | stated |
| `dev/test_host.py:608` | `host PROOF-100` | stated |
| `dev/test_host.py:652` | `host PROOF-32` | stated |
| `dev/test_host.py:681` | `host PROOF-97` | stated |
| `dev/test_host.py:761` | `host PROOF-63` | fixed |
| `dev/test_host.py:776` | `host PROOF-53` | fixed |
| `dev/test_host.py:1040` | `host PROOF-101` | stated |
| `dev/test_host.py:1047` | `host PROOF-107` | fixed |
| `dev/test_host.py:1057` | `host PROOF-105` | stated |
| `dev/test_remote.py:239` | `host PROOF-79` | stated |
| `dev/test_remote.py:254` | `host PROOF-81` | stated |
| `dev/test_remote.py:272` | `host PROOF-83` | stated |
| `dev/test_consumer_ci.py:84` | `host PROOF-47` | fixed |

What changed in each `fixed`:

- `PROOF-8`: the test checked the change's content by its `feature` field; it now asserts the
  `rawtext` content is the file's text exactly.
- `PROOF-63`: the project gains a GitHub `origin`, since the run now reads the git host before
  it reads the tree; the one-line refusal and no push are asserted as before.
- `PROOF-53`: the project's `origin` is `https://gitlab.com/acme/widgets.git` in place of the
  cut `ci: none` setting, and the test asserts the new line exactly.
- `PROOF-107`: asserts `This run is on topic, which is not a run branch: the tests ran and
  nothing is written.` and that the run does not commit.
- `PROOF-47`: the assertion that the pipeline triggers on `signed/*` is gone; it asserts
  `pr: none` and the last step. The trigger is `PROOF-142`'s.

The `stated` ones carry the proof's values in the test's name, docstring or an added
assertion: `PROOF-5` the five methods and `acme/widgets`; `PROOF-22` the one printed line
exactly; `PROOF-58` the count of moves sent; `PROOF-62` that the one change is an `edit`, with
the two unit checks of `azure_change` taken out; `PROOF-39` the two pushes counted; `PROOF-79`
the order of its two lines. The test of `PROOF-83` and every `test_remote.py` test now run in
a project folder carrying its runner file, in place of `/project`.

## Tests deleted

`dev/test_host.py`: `test_the_tree_entry_carries_the_file_and_its_permission`,
`test_the_ci_commit_carries_every_file_in_one_tree`,
`test_a_file_that_is_not_text_gets_a_blob_of_its_own`,
`test_the_reset_time_is_read_when_there_is_no_retry_after`,
`test_a_fourth_refusal_is_raised_with_its_status`,
`test_a_429_asking_for_a_pause_is_waited_out_too`,
`test_the_ref_update_is_retried_when_the_branch_moved`,
`test_a_refusal_that_is_not_a_moved_branch_is_raised_at_once`,
`test_no_repository_name_writes_no_commit`,
`test_the_azure_push_retries_when_the_object_id_is_stale`,
`test_the_section_is_merged_into_what_the_branch_holds`,
`test_with_no_workspace_variable_every_project_is_its_own`,
`test_the_azure_project_that_is_the_workspace_pushes`,
`test_a_detached_head_has_nothing_to_push`,
`test_the_run_branch_names_the_branch_and_the_commit`,
`test_a_green_run_says_what_it_pushed_and_what_it_waits_for`,
`test_the_run_is_looked_up_by_its_branch_before_it_is_watched`,
`test_the_evidence_comes_home_at_the_gate_passed`,
`test_the_evidence_comes_home_at_the_gate_signed`,
`test_the_lookup_is_asked_again_while_the_run_registers`,
`test_a_run_that_never_registers_is_reported_and_the_branch_deleted`,
`test_a_failed_push_starts_no_run`,
`test_a_run_branch_that_cannot_be_deleted_is_named_with_its_command`,
`test_a_command_that_cannot_be_started_is_named_with_the_error`,
`test_a_settings_file_that_cannot_be_read_pushes_nothing`,
`test_off_a_runner_every_commit_is_the_persons_own`,
`test_any_other_branch_commits_nothing`, `test_a_tag_run_commits_nothing_and_says_so`,
`test_the_last_part_of_an_azure_ref_alone_commits_nothing`.

`dev/test_host_pathspec.py`: `test_git_is_handed_a_forward_slash_pathspec`,
`test_the_commit_carries_the_new_file_and_the_deletion`.

`dev/test_remote.py`: `test_the_ssh_form_names_the_organisation_and_the_project`,
`test_a_user_part_before_the_host_is_ignored`,
`test_a_percent_encoded_project_in_the_https_form_is_decoded`,
`test_a_remote_in_no_azure_form_is_refused_before_the_push`,
`test_the_lookup_names_the_organisation_the_project_and_the_run_branch`,
`test_the_wait_on_azure_devops_is_announced_after_the_push`,
`test_the_poll_names_the_run_the_organisation_and_the_project`,
`test_a_run_not_registered_at_first_is_asked_for_again`,
`test_a_canceled_run_is_brought_home_red`, `test_a_partly_succeeded_run_is_brought_home_red`,
`test_no_run_within_a_minute_deletes_the_branch_and_fails`,
`test_without_az_the_run_is_neither_found_nor_pulled`.

`dev/test_consumer_ci.py`: `test_the_fixture_workflow_is_what_the_template_renders`,
`test_the_template_still_carries_the_placeholders`,
`test_a_project_with_no_env_tag_gets_no_workflow`,
`test_a_proof_tagged_for_another_system_gets_a_workflow_for_that_reason`,
`test_proofs_tagged_for_two_other_systems_are_named_together`,
`test_tests_tagged_for_two_other_systems_are_named_together_at_passed`,
`test_a_tag_naming_this_machines_own_system_gets_no_workflow`,
`test_the_workflow_is_shaped_like_a_workflow`,
`test_the_workflow_ends_on_the_test_step_and_uploads_nothing`, `test_the_job_is_named_purlin`,
`test_the_matrix_is_the_one_operating_system_the_spec_names`,
`test_the_matrix_follows_a_fixed_order`, `test_two_named_systems_get_two_jobs_and_no_linux_one`,
`test_a_name_that_is_no_operating_system_adds_no_job`,
`test_the_workflow_clones_the_release_the_project_pins`,
`test_the_fixture_is_complete_and_every_file_is_tracked`,
`test_the_config_is_the_shape_this_release_reads`,
`test_purlin_reads_the_fixture_as_one_feature_with_a_linux_proof`,
`test_the_fixtures_own_test_file_names_nothing_of_purlin`,
`test_the_fixtures_own_test_file_runs_by_itself`,
`test_the_sqlite_step_comes_just_before_the_test_step`,
`test_a_windows_runner_gets_sqlite3_when_a_tracked_file_names_it`,
`test_a_macos_runner_installs_nothing`,
`test_a_project_where_only_the_runner_file_names_sqlite3_installs_nothing`,
`test_a_windows_runner_that_has_sqlite3_installs_nothing`,
`test_an_azure_windows_agent_gets_sqlite3_on_its_search_path`,
`test_the_runner_file_opens_on_why_it_exists`, `test_the_runner_file_says_whom_the_matrix_holds`,
`test_the_runner_file_says_what_starts_a_run`,
`test_the_runner_file_says_the_job_is_capped_at_ninety_minutes`,
`test_the_runner_file_says_no_breaks_and_no_audit_run_there`,
`test_the_runner_file_says_each_test_command_has_an_hour`.

`dev/fixtures/consumer-ci/**` is deleted whole: no proof reads it, and its settings carried
`gate`, `mutation_engine`, `audit_parallel` and `ci`.

## What I built

- `remote.ensure_runner(project_root, commit=False, out=None, host=None)` and
  `remote.run_remote(project_root, args=None)` (K11). The run's order: the settings file, the
  git host from `workflow.host_of`, the branch, the tree (the runner file alone may be
  uncommitted under `--commit-runner`), the Azure DevOps URL, the runner file, `gh` or `az`, the
  push. The runner file is written before the `gh` check, so `run_script PROOF-272` and `273`
  pass with no `gh` on the path.
- `cfg`, the `ci` setting and its refusal `CI_NONE` are gone from `remote.py`.
- `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml` and
  `.github/workflows/purlin.yml` start on a push to `run/**` (`run/*` on Azure DevOps) alone.
  The `signed/*` tag trigger (decision 109) and the sqlite3 step (decision 112) are cut; the
  comments lose the gate, `references/hard_gates.md` and `purlin:init`. This repository's
  runner file is re-rendered from the template for Windows at `v0.10.0`.
- `host.py` loses the tag run (`is_a_tag_run`, `TAG_RUN`, `SIGNED_TAG_PREFIX`, `REF_TAGS`);
  `NOT_A_RUN_REF` reads as `PROOF-107` has it.
- `workflow.py` loses `wanted`, `no_reason`, `foreign_reason`, the six reason lines (three of
  them worded for a gate), `prerequisites`, `NO_REMOTE`, `UNKNOWN_HOST`, `CLI_PRESENT`,
  `CLI_ABSENT`. It gains `HOST_WORDS` and `host_word(host)`. `host_of` now closes the input of
  the one git process it starts and sets `GIT_TERMINAL_PROMPT=0` and
  `AZURE_EXTENSION_USE_DYNAMIC_INSTALL=no`, since it is a process `--remote` starts
  (`host RULE-52`, `PROOF-83`).
- `ci.py`: docstring only.

No format file is mine in K14.

The deliberate break: `ensure_runner` made never to write. `host PROOF-140`, `141`, `143` and
`run_script PROOF-272`, `273` failed; restored with `git checkout -- scripts/run/remote.py`.

K15's greps over my files find nothing. No `open(` in my files lacks `encoding=` but
`host.py`'s binary read (`'rb'`), as before. `dev/test_security.py` and
`dev/test_vocabulary.py` pass with my change.

## Lines a person reads that I chose

| Line | Where it prints |
|---|---|
| `No proof in specs/ is tagged @env for a system, so there is no runner to write and nothing was pushed. Tag a proof @env(<system>) with purlin:spec, then run purlin:test --remote again.` | `purlin:test --remote` where there is no runner file and no proof in `specs/` carries an `@env` tag; exit 1 |
| `The runner file <path> was not committed: git <add\|commit> failed. Nothing was pushed; run purlin:test --remote --commit-runner again.` | `--commit-runner` where git refuses the add or the commit; exit 1 |
| the runner file's text, whole, between `RUNNER_WRITTEN` and `RUNNER_NEXT` | `purlin:test --remote` on first need; `host RULE-54` and K11 say "the file" |
| the comment lines of both templates, rewritten as above | the runner file |

The lines `host` and section 6 fix are used as written.

## Differences from section 3's contracts

- `ensure_runner` takes a fourth argument, `host=None`, so `run_remote` passes the host it
  already read rather than starting a second git process.
- With `commit=True` and no runner file, `ensure_runner` prints `RUNNER_WRITTEN` and the file,
  then commits and prints `RUNNER_COMMITTED`; it leaves out `RUNNER_NEXT`, which tells the
  person to do what is being done.
- The matrix holds the systems tagged that this machine is not, or, where every tag names this
  machine's own system, every system tagged.

## Left open, and failures in files I do not own

1. **`setup`'s files call what I removed.** `scripts/init/scaffold.py` calls
   `workflow.prerequisites`, `workflow.wanted`, `workflow.no_reason` and
   `workflow.UNKNOWN_HOST`; `scripts/init/update.py` calls `wanted`, `no_reason` and
   `prerequisites` in `_apply_workflows`. Setup's own specs cut the runner file it wrote
   (`scaffold RULE-81`, `update RULE-53`: "no runner file is written"), so `setup` deletes these
   calls. `dev/test_init_scaffold.py` and `dev/test_init_update.py` run together: 1 failed and
   9 errors on `d115/base`; 250 failed and 9 errors with my branch, the new failures
   `AttributeError: module 'workflow' has no attribute 'wanted'`. Integration checks
   this clears when `setup` is merged after me. `dev/test_init_update.py:2012` calls
   `workflow.wanted` too.
2. **`host PROOF-53` says "starts no process".** The git host is now read from `origin` each
   time (decision 109, K11), which is one `git remote get-url origin`. The test asserts that this
   read is the only process started, and no push. The proof is not built to as worded in that
   one word; the owner may want "starts no push".
3. **A first `--remote` in a project with no `@env` tag** writes nothing and exits 1 with the
   line above. No spec or decision says what it does there.
4. **`run_script RULE-96`**: a `--remote` run prints no stale test comment lines after a
   `Markers:` line; `purlin_run.py` (`run`'s) returns into `remote.run_remote` before any of
   that. Not mine to change; `run_script` has no proof of it for `--remote`.
5. `purlin_run.py`'s `_ci` docstring still says "A tag run runs the tests and writes nothing",
   and `scripts/run/purlin_run.py:53` describes `remote.run_remote` as it is now. `run`'s file.
6. `host PROOF-118` is tagged `@env(windows)` and its test runs, and passes, on Linux too, by
   giving `host.py` a Windows `os.path`. Left as it was: it was right as it stood.

## What the session cost

This session cannot read its own spend.
