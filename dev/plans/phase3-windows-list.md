# The Windows list

The owner accepted this list as it stands on 2026-09-29 (decisions 82, 95 and 97), less the row
for upstream RULE-7, which went with anchors made from plain text. Wave W marks from it, with
rule, proof and test names brought up to date after the lanes of phase 3 merged: where a split
moved a row's test to another rule, the row names that rule, and the wave marks under it. No
proof on the list is marked yet. "Question <n>" is owner question OQ<n> of `phase3-plan.md`
section 8, now answered (decision 97).

## Summary

- The sort found 90 rules. 7 are left off, 5 are added, and 2 of the kept rules become one when
  the approved readings are applied, and upstream RULE-7 went with anchors made from plain text
  (decision 97). **86 rules are on the list.**
- Left off: 1 rule whose every test reads a text file, 1 rule only Purlin's maintainers run, the
  2 rules about console characters that another rule covers, and the 3 rules decision 95 makes
  Mac only.
- Added: the 3 rules where the upgrade rewrites spec lines, and the 2 checks that depend on how
  git treats line endings.
- Each rule on the list gets one new proof ending `@env(windows)`, tied by a second comment to
  the test named in its row. The Mac keeps proving the proof it already has.
- 13 proofs get `@env(macos)` (decision 95, which took W3's first option: each test that cannot
  run on Windows has its proof tagged for macOS): the 11 proofs of the walk from setup to a
  signed tag, the 1 proof of the C# wiring check, and the 1 proof of the file link. The
  TypeScript and C# walk is deleted by reading Q16 and was tied to no proof. They are proven on
  this Mac, and this repository's runner file, written on a Mac, gets no Mac machine (decision
  97).
- Every rule id, every test name and every rule's words below were checked against `specs/` and
  `dev/` after the lanes of phase 3 merged. Twelve rows moved to the rule a split or a reading
  gave their test, one of them now naming the test built for it (listed under "Brought up to
  date"), and the other 74 rows kept their ids and tests.
- 48 of the 86 rows carry a note under "Needs": a stand-in program with a Windows ending, a
  program the runner must have, a check of bytes or of the `\` spelling, or a new case. The
  other 38 tests run on Windows as written.

## Brought up to date

After the lanes of phase 3 merged, on 2026-09-29, each row's test was read for the proof its
marker names and the rule that proof now sits under. These rows changed; every other row's rule,
proof and test stand as written.

| Spec | Was | Now | Test's proof now | Why |
|---|---|---|---|---|
| `upstream` | RULE-9 | RULE-27 | PROOF-32 | RULE-9 split: exit 0, 1 and 2 are RULE-9, 26 and 27 |
| `scaffold` | RULE-44 | RULE-60 | PROOF-78 | RULE-44 split: `gh` or `az` reported is RULE-60 |
| `update` | RULE-8 | RULE-34 | PROOF-36 | RULE-8 split: the cache folder is RULE-34 |
| `update` | RULE-16 | RULE-35 | PROOF-83 | RULE-16 split: the wiring is RULE-35 |
| `evidence` | RULE-4 | RULE-24 | PROOF-7 | RULE-4 split: a folder entry is RULE-24 |
| `evidence` | RULE-14 | RULE-27 | PROOF-53 | RULE-14 split: the reader's own machine is RULE-27 |
| `specs` | RULE-14 | RULE-20 | PROOF-41 | RULE-14 split: an unreadable file is RULE-20 |
| `states` | RULE-35 | RULE-90 | PROOF-41 | RULE-35 split: where none is current is RULE-90 |
| `ai_audit` | RULE-7 | RULE-19 | PROOF-25 | RULE-7 split: past the limit is RULE-19 |
| `host` | RULE-26 and RULE-27 | RULE-27 | PROOF-96 | Q27: RULE-26 retired, its proof under RULE-27 |
| `mutation` | RULE-13 | RULE-30 | PROOF-47 | RULE-13 split: the report file is RULE-30 |
| `mutation` | RULE-18, a new test | RULE-32 | PROOF-79, `test_on_windows_mutmut_is_no_engine` | RULE-18 split: Windows is RULE-32, and lane `mutation` built its test |

The rows of `reports` RULE-16 and `signatures` RULE-45 keep their ids; their plain words drop the
clauses the splits moved (RULE-25 and 26, and RULE-71). The four probable faults are fixed, so the
"Needs" cells of upstream RULE-3, signatures RULE-17, host RULE-12 and mutation RULE-7 say so.
The 13 proofs to tag `@env(macos)` keep their ids.

In the tables, "Test" is the file and the test the new proof would be tied to. "Draft proof" is
the new line, at most 60 words, one case. "Needs" is empty where the test runs on Windows as
written.

## `config_engine` (specs/mcp/config_engine.md): 5 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-1 | A project's folder can be named by a setting in the environment, and that wins when the folder exists. | Windows spells folders with a drive letter and `\`, and reads environment settings with different casing. | `dev/test_config_engine.py::test_the_variable_naming_an_existing_folder_wins_over_a_marker` | On Windows, with `PURLIN_PROJECT_ROOT` naming `<tmp>\chosen`, an existing folder with no `.purlin/` marker, starting from `<tmp>\other\src` under a marker at `<tmp>\other` gives the project root `<tmp>\chosen` | |
| RULE-2 | Otherwise Purlin climbs from where it starts to the nearest folder holding `.purlin/`. | The climb has to stop at the drive's top, `C:\`, not at `/`. | `dev/test_config_engine.py::test_the_climb_reaches_the_marker_above_the_start` | On Windows, with `PURLIN_PROJECT_ROOT` unset and a `.purlin/` marker in `<tmp>\a` and none below it, starting from `<tmp>\a\b\c` gives the project root `<tmp>\a` | |
| RULE-8 | Changing one setting writes it into `.purlin/config.json`, creating the file if needed. | Windows can add a carriage return to every line of a file written as text. | `dev/test_config_engine.py::test_a_write_adds_its_key_to_the_settings_file` | On Windows, with the settings file holding `{"team": "v1"}`, setting `user_pref` to `dark` leaves it holding exactly `{"team": "v1", "user_pref": "dark"}` with no carriage return, and `.purlin/` holds no other file | Compare the file's bytes, not its parsed content. |
| RULE-10 | A setting is saved whole or not at all: the new file is written beside the old one and moved over it. | On Windows a move over a file another program holds open fails, where macOS lets it through. | `dev/test_config_engine.py::test_a_failed_move_leaves_the_previous_file_and_no_temporary` | On Windows, with the settings file holding `{"key": "val"}` and held open by another program, a write of `key` as `other` leaves it reading exactly `{"key": "val"}`, and `.purlin/` holding only `config.json` | Today the failed move is simulated. To show the Windows case, hold the file open for real during the write. |
| RULE-13 | Purlin says how it found the project's folder: by the setting, by climbing, or by guessing the current folder. | Same as RULE-1 and RULE-2: drive letters, `\` and the environment. | `dev/test_config_engine.py::test_the_variable_is_found_by_env` | On Windows, with a marker at `<tmp>\project\.purlin\` and `PURLIN_PROJECT_ROOT` naming `<tmp>\elsewhere`, an existing folder with no marker, starting from `<tmp>\project\src` gives `<tmp>\elsewhere`, found by `env` | |

Readings that touch this spec: Q67 removes RULE-5, the command line that prints settings; it was
not on the list. Q65 and Q66 change what happens when the settings file cannot be read or a save
fails; RULE-8 and RULE-10 keep their numbers and may gain proofs of their own.

## `upstream` (specs/anchor/upstream.md): 6 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-1 | Adding a shared set of rules from another repository writes a copy with its source and the exact version it came from. | Purlin starts git, and git marks the files of the copy it downloads read-only, which Windows then refuses to delete. | `dev/test_upstream.py::test_an_added_anchor_keeps_the_author_text_under_source_and_pin` | On Windows, the anchor `no_eval` is added from another repository's `specs/no_eval.md`; the answer reads `added`, the copy carries `> Source:` and `> Pinned:` lines naming that repository and its sha, and no downloaded folder is left in the temporary folder | Check that the temporary download is gone. A successful `add` leaves its checkout under `.purlin/runtime/anchors/` today; only the no-rule refusal removes it (C13). |
| RULE-3 | With no name given, the shared rules are named after their file. | Probable fault 3: the name is cut at `/` only, so a path typed with `\` gives a wrong name. | `dev/test_upstream.py::test_with_no_name_the_anchor_is_named_after_its_file` | On Windows, an anchor is added from `specs\no_secrets.md`, typed with a backslash, with no name given; the answer names it `no_secrets`, and `specs/_anchors/` then holds `no_secrets.md` alone | The test builds the path with `os.path.join`, which spells it with `\` on Windows; fault 3 is fixed (lane `upstream`). |
| RULE-8 | A check writes nothing and says whether each copy is current or behind. | Purlin starts git to ask the source; how programs are started differs. | `dev/test_upstream.py::test_check_when_behind_reports_and_changes_no_file` | On Windows, an anchor is pinned and a new version of it is published; `sync --check` reports the row `behind` with both shas, counts 1 behind, and leaves every file in the project byte for byte as it was | |
| RULE-27 (was RULE-9) | The check ends with 2 when a named anchor does not exist or a source cannot be read. | A deleted source holds read-only files Windows will not remove; exit codes pass through a different shell. | `dev/test_upstream.py::test_check_exits_2_when_the_source_is_gone` | On Windows, an anchor is pinned and its source repository is then deleted; `sync --check --json` exits 2, and the row reads `error` | |
| RULE-11 | Bringing a copy up to date rewrites it from the source and names the rules added, removed and changed. | Purlin downloads into a temporary folder and rewrites a file, both of which Windows handles differently. | `dev/test_upstream.py::test_sync_advances_the_pin_and_names_the_rule_delta` | On Windows, a new version of `no_eval` rewords `RULE-2` and adds `RULE-3`, and `sync no_eval` runs; the row reads `synced`, the summary `RULE-2 changed, RULE-3 added`, and the copy carries the new pin with no carriage return | Compare the copy's bytes. |
| RULE-22 | Adding and updating shared rules writes nothing outside the project. | Temporary folders live elsewhere on Windows, and paths are spelled differently. | `dev/test_upstream.py::test_nothing_is_written_outside_the_project_root` | On Windows, an anchor is added, a new version is published and the anchor is synced; the folder around the project still holds exactly its four entries, `policies.git`, `policies_work`, `project` and `project.git` | |

Reading Q41 changes how a plain `sync` downloads a source (once per run). RULE-15 is not on the
list; RULE-11 keeps its number.

## `package` (specs/export/package.md): 3 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-1 | Writing the evidence package commits nothing and leaves no second working copy behind. | Purlin makes and removes a temporary second working copy; Windows refuses to delete files still open or read-only. | `dev/test_export.py::test_it_writes_the_version_file_prints_the_state_and_commits_nothing` | On Windows, in a project at the gate `signed` whose `VERSION` reads `2.1.0`, the command is run with no argument; it exits 0, prints `Evidence package written to .purlin/evidence/package/2.1.0.json. State: not finished.`, and `git worktree list` shows one worktree | |
| RULE-8 | The same commit always gives the same package, byte for byte, with plain line feeds. | Windows can write a carriage return before every line feed, and git on Windows may convert line endings on checkout. | `dev/test_export.py::test_a_second_clone_at_the_tag_gives_the_committed_bytes` | On Windows, with `core.autocrlf` set to `true`, a signed and tagged project is cloned into a second folder and exported at `signed/2.1.0`; the file it writes holds exactly the bytes the tag holds, with no carriage return | Set `core.autocrlf true` in the clone. |
| RULE-9 | A package carries a fingerprint of its own content, and a check says whether the file still matches it. | A package checked out on Windows can gain carriage returns, which the check must name. | `dev/test_export.py::test_check_passes_a_package_as_written` | On Windows, a package is exported and its file checked with `--check`; it exits 0 and prints exactly the one line `The package matches its fingerprint.` | |

## `scaffold` (specs/init/scaffold.md): 8 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-13 | Setup writes a remote runner file only when a proof is marked for a system this machine is not. | Which systems count as "another" depends on the machine setup runs on. | `dev/test_init_scaffold.py::test_at_passed_the_reason_names_the_test` | On Windows, a project with a proof tagged `@env(macos)` is set up at `--gate passed`; the workflow is written, and under `A remote runner is written because:` stands the one reason `A test is tagged @env for macOS, which this machine is not, so only a runner can run it.` | |
| RULE-19 | A block setup adds to a file the project owns, such as `.gitignore`, is added once, never twice. | A project file with Windows line endings may not be recognised as already holding the block. | `dev/test_init_scaffold.py::test_the_gitignore_block_is_added_once` | On Windows, a project whose `.gitignore` reads `node_modules/` followed by a carriage return and a line feed is set up twice; the file is the same after the second run as after the first, and holds `.purlin/report-data.js` exactly once | Write the starting `.gitignore` with Windows line endings. |
| RULE-20 | Running setup a second time at the same gate changes no file. | Line endings written on Windows can differ from what the first run wrote. | `dev/test_init_scaffold.py::test_a_second_run_at_the_same_gate_changes_nothing` | On Windows, init is run twice at `--gate strong` on the same project; no line of the second run's summary begins `wrote`, and every file outside `.git/` reads byte for byte the same after the second run as before it | |
| RULE-21 | No file setup writes names the folder the plugin ran from. It also holds the fresh project set up from a marketplace copy, scaffold PROOF-97, moved under RULE-21 by Q15. | A Windows folder can be written as `C:\...` or `C:/...`; the check looks for this system's spelling alone. | `dev/test_init_scaffold.py::test_nothing_a_project_holds_names_the_plugin` | On Windows, a marketplace copy of the plugin, named by `CLAUDE_PLUGIN_ROOT`, sets up a project at `--gate strong`; no readable file outside `.git/` holds the copy's path, spelled with `\` or with `/` | Look for both spellings of the path. |
| RULE-22 | A copy installed from the marketplace sets a project up the same way as this checkout. | The plugin's folder is named through the environment and spelled the Windows way. | `dev/test_init_scaffold.py::test_the_copy_sets_a_project_up_the_same_way` | On Windows, a marketplace copy of the plugin, named by `CLAUDE_PLUGIN_ROOT`, sets up a pytest project with a proof tagged `@env(macos)` at `--gate strong`; it writes the workflow, and the same project set up from this checkout ends with the same files and output, each path aside | |
| RULE-23 | No file setup writes points at this repository's own `dev/` folder. | On Windows the folder can be written `dev\`, which the check does not look for. | `dev/test_init_scaffold.py::test_no_project_file_points_at_the_repository_s_own_dev_folder` | On Windows, init sets up a project at `--gate strong`; no readable file outside `.git/` holds `/dev/` or `\dev\`, once every `/dev/null` is set aside, and none holds a relative path starting `dev/` or `dev\` | Look for the `\` spellings. |
| RULE-60 (was RULE-44) | Where a remote on GitHub or Azure DevOps is found, setup says whether that host's program, `gh` or `az`, is installed, and writes the runner file either way. | Probable fault 1: the GitHub program is looked for as `gh`, and on Windows it is `gh.exe`, so setup says it is not installed. | `dev/test_init_scaffold.py::test_gh_installed_is_named_and_the_workflow_written` | On Windows, a project with a proof tagged `@env(macos)` on a GitHub remote is set up at `--gate strong` with `gh.cmd` on the search path; it prints `gh is installed, so a remote run can be watched from here.` and writes the workflow | The Windows skip is gone and the search path adds git's own folder, with no link (lane `scaffold`); the stand-in is `gh.cmd` on Windows, found through `shutil.which` (lane `host`, C8). |
| RULE-47 | Setup writes a README into the evidence folder, the same bytes as the one Purlin ships. | Windows can add carriage returns when copying, and git on Windows may have converted the shipped copy. | `dev/test_init_scaffold.py::test_the_first_run_writes_the_readme` | On Windows, init at `--gate passed` writes `.purlin/evidence/README.md`, byte for byte the same as the README Purlin ships and naming `local/` and `ci/`, and the summary reports it as `wrote` | |

Left off:

- RULE-34 (a run ends on the status lines or `→ Run: purlin:spec ...`): it is about printing `→` on
  a Windows console, which run_script RULE-39 covers for every command.
- RULE-36 (a project walks the three gates to the signed tag): Mac only, decision 95. The walk
  needs a Unix shell and SSH signing.
- RULE-37 (each language is set up the same way): Mac only, decision 95. Its proofs run through
  the same walk.

Changes from the readings and decisions: Q15 moves PROOF-97 from RULE-37 to RULE-21. Q16 removes
the TypeScript and C# walk, `dev/test_init_e2e_gates.sh`, which is tied to no rule. Decision 96
changes the lines RULE-44 prints for a project with no git host or one Purlin cannot use; the
lines about `gh` and `az` stay.

## `update` (specs/init/update.md): 10 on the list, 3 of them added

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-5 | The upgrade with `--yes` asks nothing and applies everything; a second run changes nothing. | git on Windows may report files as changed when only their line endings differ. | `dev/test_init_update.py::test_running_yes_twice_changes_nothing_the_second_time` | On Windows, the update is run with `--yes` a second time on the sample 0.9.5 project it already updated; it exits 0, prints `Nothing is pending`, and leaves the latest commit and `git status` exactly as the first run left them | |
| RULE-7 | Every file the upgrade rewrites is first copied beside itself, holding its old bytes. | The copy must hold the old bytes exactly, carriage returns included. | `dev/test_init_update.py::test_every_backed_up_file_keeps_its_bytes_from_before_the_run` | On Windows, after the update with `--yes` on the sample 0.9.5 project, every file that has a backup has one holding exactly the bytes the file had before the run | |
| RULE-34 (was RULE-8) | The upgrade deletes the old cache folder, `.purlin/cache/`, from git and from disk. | Windows refuses to delete read-only or open files and folders. | `dev/test_init_update.py::test_a_committed_cache_is_deleted_from_git_and_from_disk` | On Windows, with the sample 0.9.5 project's `.purlin/cache/` folder committed, the update with `--yes` leaves nothing under `.purlin/cache/` tracked and the folder gone from disk | |
| RULE-35 (was RULE-16) | The upgrade removes the lines that wired the old plugin copies into the project's test tools, each file backed up first. | Deleting files, and rewriting files that may carry Windows line endings. | `dev/test_init_update.py::test_a_conftest_holding_more_keeps_the_rest` | On Windows, a `conftest.py` holding `import os` above the plugin's `pytest_plugins` line holds `import os` alone after the update with `--yes`, with its line ending as it was | Compare bytes. |
| RULE-18 | The upgrade makes one commit, and afterwards nothing is left uncommitted but the backup copies. | git on Windows may list rewritten files as changed because of line endings. | `dev/test_init_update.py::test_nothing_is_left_uncommitted_but_the_backups` | On Windows, after the update with `--yes` on the sample 0.9.5 project, `git status` lists at least one file, and every file it lists is untracked and ends `.bak` | |
| RULE-28 | A project with no evidence folder gets one with the same README setup writes. | Same as scaffold RULE-47: the README's bytes. | `dev/test_init_update.py::test_the_evidence_folder_gets_its_readme` | On Windows, the update with `--yes` on the sample 0.9.5 project, which has no `.purlin/evidence/`, leaves `.purlin/evidence/README.md` holding exactly the bytes `purlin:init` writes there, committed, and `evidence` no longer pending | |
| RULE-29 | Each old marker in a test file becomes the new comment above the same test; a shell script's old calls become no-ops. | A shell script rewritten with Windows line endings no longer runs in bash. | `dev/test_init_update.py::test_the_shell_harness_calls_become_one_comment` | On Windows, a shell script that loads the old harness, calls it for `login` `PROOF-1` and closes it carries after the update with `--yes` `# purlin: login PROOF-1` under its first line, holds no carriage return, and exits 0 when run with bash | Check the bytes and run the rewritten script. |
| RULE-13 (added) | The old Windows tag at the end of a proof line becomes `@env(windows)`. | The upgrade rewrites spec lines as text, which on Windows adds a carriage return to every line of the spec. | `dev/test_init_update.py::test_the_retired_windows_tag_becomes_env` | On Windows, the update with `--yes` on the sample 0.9.5 project turns the `PROOF-53` line ending `@windows` into one ending ` @env(windows)`, and every other line of that spec is byte for byte as it was, line endings included | Compare the spec's other lines as bytes. |
| RULE-23 (added) | A proof line loses the old tag naming its kind of test, and the rest of the line is untouched. | Same as RULE-13: the rewrite of the spec as text. | `dev/test_init_update.py::test_an_env_tag_after_the_kind_of_test_is_kept` | On Windows, a proof line reading `Lock a file`, a kind-of-test tag and `@env(linux)` reads after the update with `--yes` exactly `- PROOF-14 (RULE-1): Lock a file @env(linux)` followed by a line feed alone | Compare bytes. |
| RULE-24 (added) | The old design reference lines are removed from a spec, and the rest of it is untouched. | Same as RULE-13: the rewrite of the spec as text. | `dev/test_init_update.py::test_the_picture_reference_of_the_feature_is_removed` | On Windows, after the update with `--yes`, the sample 0.9.5 project's spec `figma_web` has no `> Visual-Reference:` line, and every other line outside its proof lines is byte for byte as it was, line endings included | Compare bytes. |

Left off:

- RULE-20 (no emoji; the run ends as the status ends): the part that could differ on Windows is
  printing `→` on a Windows console, which run_script RULE-39 covers.
- RULE-31 (a dashboard page that is a link is replaced by a copy): Mac only, decision 95. A
  symbolic link cannot be made on Windows without Developer Mode or an administrator.

Added: RULE-13, RULE-23 and RULE-24, because each rewrites spec lines as text and says the rest of
the spec is untouched, which on Windows holds line by line and not byte for byte.

Changes from the readings: Q17 removes RULE-11 (the dashboard switch) and moves its two proofs to
the rule about the seven settings. Q18 adds a line when the upgrade's gate answer is not a gate.
Q19 moves RULE-32 (a project that still reads as set up by 0.9.5) to the run. None of the three
is on the list.

## `evidence` (specs/mcp/evidence.md): 5 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-1 | A feature's fingerprint is three hashes, of its spec, its code and its tests, read from the files on disk. | git on Windows may check files out with carriage returns; the hash must be the one git gives the committed file. | `dev/test_fingerprint.py::test_a_fingerprint_is_three_parts_of_64_hex_characters` | On Windows, with `core.autocrlf` set to `true`, `login` covers the committed file `src/login.py`; its fingerprint carries the three parts `code`, `spec` and `tests`, and `code` equals the one taken of the same commit with `core.autocrlf` set to `false` | Take the fingerprint under both settings. |
| RULE-24 (was RULE-4) | A folder the spec's scope line names reaches every tracked file under it in the code hash. | Paths are spelled with `\` and git is handed them on Windows. | `dev/test_fingerprint.py::test_a_scoped_folder_reaches_a_tracked_file_one_folder_down` | On Windows, `login` covers the folder `src`, which holds the tracked file `src/deep/token.py` one folder down; editing that file changes the fingerprint in `code` alone | |
| RULE-7 | The tests hash covers every test file that carries a comment for the feature. | Test files are found by patterns over paths spelled with `\`. | `dev/test_fingerprint.py::test_a_javascript_marker_is_counted` | On Windows, the committed file `web/login.test.js`, named by a suite's pattern `**/*.test.js`, carries `// purlin: login PROOF-2` above its test; editing it changes the fingerprint of `login` in `tests` alone | |
| RULE-8 | A file git does not track changes no hash, and is listed as not tracked. | git's answers name paths with `/` while Windows gives `\`. | `dev/test_fingerprint.py::test_untracked_files_in_the_scope_or_beside_a_marker_file_are_listed` | On Windows, `login` covers `src` and its marker file is `tests/test_login.py`; `src/new_token.py`, `tests/helper.py` and `docs/notes.md` are written and not added to git; the files listed as untracked are exactly `src/new_token.py` and `tests/helper.py` | |
| RULE-27 (was RULE-14) | The reader names the system it runs on: `windows`, `macos`, or `linux` on any other. | This is the one machine where the answer must be `windows`. | `dev/test_evidence_reader.py::test_a_system_that_names_itself_win32_is_windows` | On Windows, with nothing simulated, the reader gives the machine it runs on as `windows` | Today the test pretends to be Windows. Add a check that asks the real system. |

Decision 94 adds a warning for a scope entry that finds no file (RULE-5 area, not on the list).

## `server` (specs/mcp/server.md): 3 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-5 | The program Claude Code talks to sends only answers on its output, and its start-up line elsewhere. | Windows can add carriage returns and use a different character set on a program's output. | `dev/test_mcp_server.py::test_stdout_holds_the_answer_alone_and_the_startup_line_is_on_stderr` | On Windows, a client starts the server in a workspace folder and sends `initialize`; its output holds exactly 1 line, the answer, with no carriage return, and its error stream holds the line `Purlin MCP server v<version> started` | Check the output's bytes. |
| RULE-6 | A request can name its own project folder, and `~` stands for the home folder. | Windows finds the home folder through a different setting and spells folders with a drive letter. | `dev/test_mcp_server.py::test_a_workspace_named_from_the_home_folder_is_found` | On Windows, the server is started in an empty folder, the home folder holds the workspace `ws` with the spec `login`, and a client asks for status with the folder written as `~/ws`; the answer opens `Purlin status: proj` and names `login` | |
| RULE-22 | The plugin starts its server through `sh` and the script that finds Python. | Windows has no `sh` of its own, and its Python may be reached only as `py -3`. | `dev/test_mcp_server.py::test_the_manifest_command_starts_a_server_that_answers` | On Windows, the command the plugin gives for the `purlin` server, with the plugin's folder filled in, is run in a workspace and sent `initialize`; exactly 1 line comes back, an answer naming the server `purlin` | Needs `sh` on the search path, as Git for Windows provides. |

Readings Q68, Q69 and Q70 change the settings tool's refusals and answers; none is on the list.

## `specs` (specs/mcp/specs.md): 2 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-11 | A spec under an `_anchors` folder is a set of shared rules. | The folder is found in a path spelled with `\`. | `dev/test_specs_reader.py::test_the_anchors_folder_alone_makes_an_anchor` | On Windows, the spec `specs\_anchors\ruleset.md`, opening `# Feature: ruleset`, is read as an anchor, by its folder alone | |
| RULE-20 (was RULE-14) | A spec file that cannot be read is skipped, and the rest still answer. | Windows refuses a read by locking the file, not by the permissions macOS uses. | `dev/test_specs_reader.py::test_a_spec_that_cannot_be_read_is_skipped` | On Windows, a project holds `specs/auth/login.md` and `specs/auth/locked.md`, which another program holds locked against reading; it reads as the one spec `login` | The test locks the file with `msvcrt` where `os.name == 'nt'` and keeps `chmod` elsewhere (lane `anchors`); that branch has not run yet. |

Changes from the readings and decisions: Q44 removes RULE-4, RULE-5 and RULE-6 (the tag rules
repeated from the spec format), none on the list; RULE-7, the 0.9.5 tags read as unknown, stays. Decision 94 adds a warning for two specs with one file
name; it is schema_spec_format RULE-13, not a rule of this spec.

## `states` (specs/mcp/states.md): 4 on the list, 1 of them added

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-28 | Each feature's entry in the dashboard data names its spec, signature and evidence files. | Paths come back from Windows spelled with `\`, and the dashboard links need `/`. | `dev/test_states.py::test_a_feature_with_no_evidence_names_its_spec` | On Windows, at the gate `passed`, the feature `login` has no evidence; its entry names the spec path `specs/auth/login.md`, spelled with `/`, the category `auth` and no signature files | |
| RULE-32 | The dashboard's data file is written whole and reads back as what was written. | The file is written beside and moved into place, and Windows may add carriage returns. | `dev/test_states.py::test_the_data_file_is_a_const_assignment_and_round_trips` | On Windows, the dashboard's data file, once written, opens with `const PURLIN_DATA = `, ends with `;` and a line feed with no carriage return, and the text between reads back as the payload that was written | Check the ending's bytes. |
| RULE-47 | A signed rule shows when it was signed: the date of the commit, or the file's own time where git cannot say. | Purlin asks git for the date with a time-zone setting in the environment, which is passed differently on Windows. | `dev/test_states.py::test_the_signed_cell_carries_when_it_was_signed` | On Windows, at the gate `signed`, `RULE-2` is signed in a signed commit by `jane@acme.com`; its signed cell reads the signer `jane@acme.com` and an `at` equal to the date of that commit, in UTC as `YYYY-MM-DDTHH:MM:SSZ` | Needs `ssh-keygen` on the search path; Windows ships one. |
| RULE-90 (added; was RULE-35) | Where no section is current, every system's evidence answers for the tests a rule's test hash covers, so every checkout reads the same hash. | The hash is taken over the test files as git stores them; a Windows checkout with carriage returns must give the same hash. | `dev/test_backing_tests.py::test_a_code_change_does_not_move_the_hash` | On Windows, with `core.autocrlf` set to `true`, a project whose current section names `test_valid_credentials_return_200` for `PROOF-1` gives `RULE-1` the same test hash as the same commit checked out with `core.autocrlf` set to `false` | A new case beside this test; today no test changes the line-ending setting. |

Added: RULE-90 (split from RULE-35), because "every checkout and CI read the same hash" rests on git turning a Windows
checkout's line endings back into the stored file.

Reading Q2 folds RULE-5 into RULE-4; neither is on the list.

## `ai_audit` (specs/review/ai_audit.md): 2 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-3 | The audit asks the model through `claude`, handing it the question on its input, with 300 seconds to answer. | On Windows `claude` is `claude.cmd`, which is started differently. | `dev/test_ai_audit.py::test_the_prompt_goes_on_stdin_and_never_in_the_arguments` | On Windows, with `claude.cmd` on the search path, the audit asks `claude` about `RULE-2`; it is started exactly once, with the arguments `-p`, `--output-format` and `json`, reads the whole question from its input, and the answer reads `strong` | Uses the stand-in `claude.cmd` that already exists. |
| RULE-19 (was RULE-7) | The model counts as unreachable when `claude` runs past its limit. | Finding a program and stopping one that runs too long both work differently on Windows. | `dev/test_ai_audit.py::test_a_call_past_its_limit_is_named` | On Windows, with the limit lowered to 1 second and a `claude` that takes 3 seconds to answer, the audit's answer about `RULE-2` is only the reason `claude timed out after 1 s` | |

## `signatures` (specs/review/signatures.md): 6 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-17 | With no key to sign with, signing prints the commands that make one, and names making a key only when none exists. | Probable fault 4: Python and git look for the home folder, and so for `~/.ssh`, through different settings on Windows. | `dev/test_signatures.py::test_an_existing_key_file_is_not_made_again` | On Windows, in a home folder where `.ssh\id_ed25519` exists, in a checkout with no signing key, `login` is run; it exits 1 and prints the first line and the two `git config` lines, with no `ssh-keygen` line | The `home` fixture sets `USERPROFILE` as well as `HOME` on Windows; fault 4 is fixed (lane `signing`, `signatures.home_folder`). |
| RULE-18 | One signing is one signed commit, whatever number of rules it signs. | git signs through `ssh-keygen`, which Windows provides from its own copy. | `dev/test_signatures.py::test_one_signed_commit_carries_the_feature` | On Windows, at the gate `signed`, the command is run for `login`, whose 2 rules wait to be signed; it exits 0, writes 2 signature files, and adds exactly 1 commit carrying them and an SSH signature, under the subject `sign(login): RULE-1 RULE-2` | Needs `ssh-keygen` on the search path. |
| RULE-20 | A signature counts when the commit that added it is signed, with any key. | git checks the signature through programs that Windows provides differently. | `dev/test_signatures.py::test_a_commit_signed_with_the_signers_key_counts` | On Windows, a signature for `login RULE-1` is committed signed with the signer's own key; it counts, with no reason | Needs `ssh-keygen` on the search path. |
| RULE-45 | When nothing is left but the tag, signing writes the signed tag. | git signs the tag through `ssh-keygen`. | `dev/test_tag.py::test_the_tag_is_signed_and_names_the_commit_and_the_gate` | On Windows, at the gate `signed`, with every rule signed and `VERSION` reading `2.1.0`, the walk is run; the tag `signed/2.1.0` carries an SSH signature, and its message reads `Nothing left to do at the gate signed.`, a `Commit:` line and `Gate: signed` | Needs `ssh-keygen` on the search path. |
| RULE-50 | A signature records the signer's email, name and key. | The key is read through `ssh-keygen`. | `dev/test_signatures.py::test_it_records_the_signer_as_git_holds_them_and_the_key` | On Windows, Jane, set up in git as `Jane.Doe@Acme.com` with the name `Jane Doe`, signs `login RULE-2`; the signature reads `signer` `Jane.Doe@Acme.com`, `signer_name` `Jane Doe`, and `key_fingerprint` what `ssh-keygen -l` prints for her key | Needs `ssh-keygen` on the search path. |
| RULE-60 | The key is read from git's setting, which may name a key file by path or give the key itself. | A key path on Windows may start with `~` or a drive letter and hold `\`. | `dev/test_signatures.py::test_a_private_key_path_reads_the_public_key_beside_it` | On Windows, with `user.signingkey` naming the private key file by a path holding `\`, and its `.pub` beside it, the key fingerprint a signature would record reads what `ssh-keygen -l` prints for that key | Write the path with `\`. |

Reading Q13 removes the rule that a rule no spec has has nothing to sign (not on the list); Q11
and Q12 change signing's exit code and message when the tag is refused or a rule is not found.

## `evidence_writer` (specs/run/evidence_writer.md): 4 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-1 | A test run writes one evidence file per feature, filed under the system it ran on. | The system must be filed as `windows`, and the machine's name read the Windows way. | `dev/test_evidence_writer.py::test_a_test_run_writes_the_feature_file_with_one_section` | On Windows, in a git checkout holding one spec, `feat`, and one passing marked test, a `--all --test` run writes `.purlin/evidence/local/feat.json` with one section, keyed `windows` | |
| RULE-4 | A run replaces only its own system's section; another system's section stays byte for byte. | A file written on Windows can gain carriage returns, changing the other sections' bytes. | `dev/test_evidence_writer.py::test_a_run_writes_its_section_beside_the_others_as_they_were` | On Windows, an evidence file holds a `linux` section and an audit whose one finding carries curly quotes, and a `windows` section is written into it; the text of the `linux` section and of the audit is byte for byte what it was | Write the `windows` section in place of the `linux` one. |
| RULE-7 | A run that saw the same thing leaves the file byte for byte as it was. | Same as RULE-4: the bytes Windows writes. | `dev/test_evidence_writer.py::test_a_second_run_that_saw_the_same_thing_leaves_the_file_alone` | On Windows, in a git checkout, a `--all --test` run is made twice with nothing changed between; `.purlin/evidence/local/feat.json` after the second run is byte for byte the file the first run wrote | |
| RULE-16 | Each section names the machine its tests ran on. | Windows reports the machine's name through a different call. | `dev/test_evidence_writer.py::test_a_run_names_the_machine_its_tests_ran_on` | On Windows, a `--all --test` run writes a section whose `machine` reads this machine's name as Windows reports it | |

Reading Q21 records the lent host name only for a remote runner, so RULE-1 and RULE-16 lose
`hostname` from a local section. The drafts above already leave it out.

## `host` (specs/run/host.md): 5 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-5 | A runner commits its evidence through GitHub's web interface, in one tree, carrying each file's text. | The files and their paths are read on a Windows runner, which spells paths with `\` and may add carriage returns. | `dev/test_host.py::test_the_tree_entry_carries_the_file_and_its_permission` | On Windows, with the GitHub variables set, a CI commit of one evidence file sends one tree entry carrying the path `.purlin/evidence/ci/<feature>.json` spelled with `/`, the permission `100644` and the file's text, byte for byte the file on disk | |
| RULE-12 | `purlin:test --remote` pushes a run branch, waits on its run, brings the result back and deletes the branch. | Probable fault 1: the GitHub program is looked for as `gh`, and on Windows it is `gh.exe`, so the run says it is not installed. | `dev/test_host.py::test_a_green_run_pushes_watches_pulls_and_deletes` | On Windows, on the branch `feature-x` with a GitHub `origin`, `gh.cmd` on the search path and GitHub registering run `987`, `purlin:test --remote` starts the push, `gh run watch 987 --exit-status`, the pull and the delete of the run branch, in that order, and exits 0 | The stand-in is `gh.cmd` on Windows (C8); fault 1 is fixed (lane `host`, `shutil.which`). |
| RULE-24 | A run hands git the evidence folder spelled with `/`, so a run on Windows still finds the files it removed. | This is the case: Windows joins paths with `\`. | `dev/test_host_pathspec.py::test_a_run_that_spells_paths_the_windows_way_commits_the_removal` | On Windows, with the GitHub variables set, in a repository whose last commit holds `.purlin/evidence/ci/retired.json`, deleted on disk, a run sends a CI commit whose tree holds `retired.json` with no blob id, which deletes it | Today the Windows spelling is simulated on the Mac; on Windows it is real. |
| RULE-27 (RULE-26 retired by Q27) | A run in a folder that is not the one the job checked out commits nothing; with no such folder named every project commits. | The folders are compared as paths, which Windows spells with a drive letter, `\` and any letter case. | `dev/test_host.py::test_the_project_that_is_the_workspace_commits` | On Windows, with the GitHub variables set and `GITHUB_WORKSPACE` naming the project's own folder spelled with `\`, a CI commit of one evidence file sends its tree and its commit, and the commit's sha comes back | Write the folder with `\`. |
| RULE-31 | On Azure DevOps the run is found and waited on through `az`, and no program may wait for a password. | On Windows `az` is `az.cmd`, found and started differently, and programs are stopped differently at their time limit. | `dev/test_remote.py::test_a_succeeded_run_is_brought_home_green` | On Windows, on the branch `feature-x` with an Azure DevOps `origin` and `az.cmd` on the search path, when the poll answers `completed` and `succeeded`, `purlin:test --remote` prints `Run 42 completed: succeeded.`, pulls and then deletes the run branch, and exits 0 | Name the stand-in `az.cmd`. |

Left off: RULE-18 (the runner file's triggers and steps). Every test of it reads the runner file's
text; a Windows run shows nothing new, and the real remote run is its proof.

Changes from the readings: Q27 merges RULE-26 and RULE-27 into one rule with the five proofs
they hold today. Q28 removes RULE-21, the guess of the default branch. Q29 gives a run on a
branch that is neither a run branch nor a signed tag a line of its own. Decision 95 adds a rule
that a remote run on a system runs only the tests tied to proofs tagged for that system; it
runs on the runner but reads text, so it is not on the list.

## `mutation` (specs/run/mutation.md): 6 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-5 | The JavaScript breaking tool runs once per feature, on that feature's files alone. | Its settings file is written to a temporary folder, with paths spelled the Windows way. | `dev/test_mutation_adapters.py::test_stryker_is_given_a_config_scoped_to_the_features_files` | On Windows, a Stryker run of `calc`, scoped to `src/calc.js` and `src/util.js`, gives Stryker a config naming exactly those two files to break, spelled with `/`, `coverageAnalysis` `perTest`, `disableBail` true, the `json` reporter and a report path | Stand-ins need a `.cmd` form. |
| RULE-7 | The project's own copy of the JavaScript breaking tool is used before one on the search path. | Probable fault 2: the project's copy is looked for as `stryker`, and on Windows it is `stryker.cmd`. | `dev/test_mutation_adapters.py::test_the_projects_own_stryker_is_started_over_one_on_the_path` | On Windows, with `stryker.cmd` in the project's `node_modules/.bin/` and another Stryker on the search path, a run starts the project's own once and never starts the one on the search path | The stand-in is `stryker.cmd` on Windows; fault 2 is fixed (lane `mutation`). |
| RULE-30 (was RULE-13) | The .NET breaking tool's report is `mutation-report.json`, found by walking its output folder. | The output folder and the files are paths spelled the Windows way. | `dev/test_mutation_adapters.py::test_a_report_several_folders_down_is_read` | On Windows, a Stryker.NET run that writes `mutation-report.json` three folders down, in `StrykerOutput\2026-09-28\reports`, is measured from that report: the feature reads 60 | Stand-ins need a `.cmd` form. |
| RULE-14 | Without `dotnet`, or without the .NET breaking tool installed, there is no engine, with the command to install it. | `dotnet` is `dotnet.exe` on Windows. | `dev/test_mutation_adapters.py::test_stryker_net_answering_its_version_is_installed` | On Windows, with a `dotnet` whose `dotnet stryker --version` exits 0, a Stryker.NET run asks that first, then breaks the code, and answers engine `stryker_net`, available, with an empty reason | Stand-ins need a `.cmd` form. |
| RULE-32 (was RULE-18) | On Windows the Python breaking tool is not started and counts as no engine. | The Python tool installs on Windows and does not run there. | `dev/test_mutation_adapters.py::test_on_windows_mutmut_is_no_engine` | On Windows, with mutmut installed and on the search path, a run over `login` answers engine `none`, not available, with the reason `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`, and the feature's `missing` empty | Today the test gives the system as Windows (mutation PROOF-79); on Windows let it ask the real system. |
| RULE-22 | A breaking run past its time limit measures nothing and says to raise the limit. | Stopping a program and the programs it started works differently on Windows. | `dev/test_mutation_adapters.py::test_a_stryker_feature_that_timed_out_measures_nothing` | On Windows, with the limit at 3 seconds, a Stryker run of `calc` and `slow`, only `slow` still going at the limit, gives `calc` 64 and `slow` a score of None, and `slow`'s `missing` carries `timed out after 3 s` | Stand-ins need a `.cmd` form. The sentence reads `the engine timed out after 3 s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer` (question 11). |

Changes from the readings and decisions: decision 94 makes strength one share per feature, so
the rules that work out a share per rule went (RULE-4, 9, 10, 11 and the attribution). Q38
turned RULE-17 into matching by file, with RULE-21 folded into it. Q39 removed the fallback to
another report file; RULE-30 says only `mutation-report.json` counts.

## `reports` (specs/run/reports.md): 6 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-3 | Only files a test setting's patterns match are read for comments; `*`, `?` and `**` work on paths. | Paths found on disk on Windows are spelled with `\`. | `dev/test_reports.py::test_a_file_no_suite_matches_is_not_read` | On Windows, with one suite on `tests/*.py`, markers are read from `tests\test_a.py` and not from `other\test_b.py`, which carries a marker too | |
| RULE-10 | A test result is matched to its file through the report's file name, class or module. | A report written on Windows names files with `\`. | `dev/test_reports.py::test_a_jest_case_names_its_file` | On Windows, in a Jest report whose case `accepts` names its file `tests\login.test.js`, the passing case gives `pass` to the marker `login PROOF-1` in that file | Today the report is one captured on a Mac. Give it a report written with `\`. |
| RULE-15 | In a suite judged by its ending, each test file is one test, passing when it exits 0. | Purlin hands each file to bash, which on Windows is Git's bash, with Windows paths. | `dev/test_reports.py::test_an_exit_suite_gives_each_file_its_exit_code` | On Windows, a suite judged by its ending covers `tests/good.sh`, which exits 0, and `tests/bad.sh`, which exits 3; the evidence reads `pass` for the first's markers and `fail` for the second's, and the run exits 1 | Needs Git's bash, found from git. |
| RULE-16 | The test command is given the marked test files, each quoted. That it runs through bash from the project's folder is RULE-25 and RULE-26 since the split. | Quoting differs on Windows, where bash is Git's. | `dev/test_reports.py::test_a_path_holding_a_space_is_one_argument` | On Windows, the marked test file of `signup` is `tests/test_sign up.py`, whose name holds a space; a run over `signup` alone gives the command that path as one argument, then the report path | |
| RULE-17 | A report left from an earlier run is deleted before the suite runs. | Windows refuses to delete a file or folder that is open. | `dev/test_reports.py::test_an_old_report_folder_is_deleted_before_the_suite_runs` | On Windows, the suite's report path is a folder holding an old report of one passing case, and the command writes nothing; the run exits 1 saying `wrote no report at .purlin/runtime/reports/out`, and the folder is gone | |
| RULE-21 | The check for comments that are nearly right prints a list with each file and line. | The file names printed are paths that Windows spells with `\`. | `dev/test_reports.py::test_a_near_miss_is_listed_as_json` | On Windows, in a project whose pytest suite reads `tests/test_login.py`, where line 1 reads `# purln: login PROOF-1`, `--near-misses` prints one entry with the file `tests/test_login.py`, spelled with `/`, and exits 0 | |

Readings Q23 (three more .NET outcomes count as passed, RULE-8) and Q24 (a suggestion names only
what a comment may name) touch this spec; RULE-8 is not on the list, and Q24 may add a proof to
RULE-21.

## `run_script` (specs/run/run_script.md): 10 on the list

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-4 | A SQL script run through SQLite is one test, passing when every statement succeeds. | Starting SQLite, and the bash redirection that feeds it the script, on Windows. | `dev/test_run_script.py::test_a_sql_script_whose_statements_succeed_passes` | On Windows, in a project whose one suite runs each SQL script through `sqlite3 -bail`, a marked script creates a table and inserts one row; after `--all --test` its proof reads `pass` in the evidence and the run exits 0 | Decision 95 runs it on Windows. SQLite must be on the Windows runner's search path; today the test skips without it. |
| RULE-10 | A proof marked for another system is not counted here, and the run says it needs that system. | On Windows the other systems are macOS and Linux/Unix. | `dev/test_run_script.py::test_a_foreign_env_proof_is_listed_as_needing_its_os` | On Windows, a spec's `PROOF-2` is tagged `@env(macos)` and its marked test is skipped here; `--all --test` prints `1 proof needs macOS; this machine is Windows. Run purlin:test --remote.` and no `Evidence is missing` | The line's form is question 20's, one line per system. A proof tagged for another system with no marked test is `no test` (reading Q7), so the fixture gives `PROOF-2` a marked, skipped test. |
| RULE-12 | A runner writes its own section of the evidence and commits it; it fails only when a test failed or could not run. | The runner's system is named, and paths are handed to the commit, on Windows. | `dev/test_run_script.py::test_the_ci_arm_writes_its_section_and_commits` | On Windows, in a git checkout at the gate `strong`, on a ref that keeps evidence, `--all --ci` writes `.purlin/evidence/ci/feat.json` with one section, `windows`, whose machine is `remote runner, Windows`, prints `Evidence committed.`, and exits 0 | |
| RULE-21 | The run names its system `windows`, `macos` or `linux`. | This is the one machine where the answer must be `windows`. | `dev/test_run_script.py::test_win32_reads_windows` | On Windows, with nothing simulated, the run reads its own system as `windows` | Today the test pretends to be Windows. Add a check that asks the real system. |
| RULE-39 | The run switches its output to UTF-8 first, so a Windows console prints the table's lines instead of stopping with an error. | A Windows console defaults to a character set that has no `─` or `→`. | `dev/test_run_script.py::test_a_cp1252_console_gets_the_glyphs_and_no_traceback` | On Windows, with the console's default character set, `--all --test` over one spec and one passing marked test prints no `UnicodeEncodeError`, prints the status table's rule line `─`, and exits 0 | On Windows the default set is real; the test may drop the forced setting. |
| RULE-40 | A suite that fails or is stopped has its last 60 lines printed. | Stopping bash and the programs it started works differently on Windows. | `dev/test_run_script.py::test_a_killed_suite_prints_its_tail` | On Windows, a shell test prints `started` and then runs past a suite time limit of 1 second; it is stopped, the run exits 1, and `started` is printed under `--- shell output (last 60 lines) ---` before the status table | |
| RULE-43 | No comment is read from the copy the Python breaking tool leaves in `mutants/`. | The folder is found in paths spelled with `\`. | `dev/test_run_script.py::test_the_copy_mutmut_leaves_is_never_collected` | On Windows, a project's one marked test also has a copy under `mutants\`, and the suite's pattern `**/test_*.py` reaches both; `--all --test` exits 0 and the evidence lists exactly one test, `tests/test_feat.py::test_ok` | |
| RULE-55 | A run with no feature named runs only features whose spec, code or tests changed, or that have files git does not track. | The comparison runs through git on paths spelled with `\`. | `dev/test_run_script.py::test_an_untracked_file_selects_the_feature_and_is_named` | On Windows, `login` and `export` have current committed evidence, `login`'s scope names `src/auth/`, and `src/auth/token.py` is written and not added to git; the next `--test` selects `login` alone, with the reason `a file is not tracked` | |
| RULE-58 | A run over some features hands each suite only those features' test files. | The file list goes to bash as Windows paths. | `dev/test_run_script.py::test_a_named_feature_runs_only_its_test_files` | On Windows, in a project whose one suite runs two shell scripts, one marked for `login` and one for `export`, each writing its feature's name to a shared file, `--feature login --test` exits 0 and leaves the file reading only `login` | |
| RULE-63 | The first test run suggests an entry for every test tool it recognises. | The suggestion for pytest starts with `python3`, which a python.org install on Windows does not provide. | `dev/test_run_script.py::test_pytest_is_suggested_its_own_entry` | On Windows, in a project with no test command set and holding only a `conftest.py`, the entry the run suggests is named `pytest` | On Windows the suggested command starts `py -3 -m pytest` (question 6); run_script PROOF-221 shows it with the system given as Windows. |

Readings Q7, Q20 and Q22 change the lines of `Left to do`; RULE-10 keeps its line. Q19 moves the
check that a project still reads as set up by 0.9.5 into this spec.

## `drift` (specs/mcp/drift.md): 1 on the list, added

| Rule | In plain words | Why Windows could differ | Test | Draft proof | Needs |
|---|---|---|---|---|---|
| RULE-17 (added) | Every drift view ends by counting spec files with changes not committed. | git on Windows may report a spec as changed when only its line endings differ from what is committed. | `dev/test_drift.py::test_specs_all_committed_print_no_such_line` | On Windows, with `core.autocrlf` set to `true`, an edited spec and a new one are both committed; no view prints a line about spec files not committed, and each view's count of them reads 0 | Set `core.autocrlf true` in the test's repository. |

Added: RULE-17, because "a spec file differs from what is committed" is git's answer, and on
Windows it depends on git's line-ending setting.

## Left off: rules only Purlin's maintainers run

- `purlin_version` RULE-7 (`dev/bump_version.sh` writes the version everywhere). No project that
  uses Purlin runs it, and the maintainer works on a Mac.

## Proofs that become Mac only

Each gets `@env(macos)` (decision 95). None of their rules is on the Windows list.

| Spec | Rule | Proofs | Test |
|---|---|---|---|
| `scaffold` | RULE-36 | PROOF-36, 90, 91, 92, 93, 117, 118, 119 | the walk in `dev/test_init_scaffold.py` (`python_walk`), which makes an SSH key and signs |
| `scaffold` | RULE-37 | PROOF-37, 94, 95 | the same walk, set up in Python, TypeScript and C# |
| `scaffold` | RULE-37 | PROOF-96 | `dev/test_init_e2e_wiring.sh` |
| `update` | RULE-31 | PROOF-31 | `dev/test_init_update.py::test_the_page_linked_into_the_old_plugin_is_replaced` |

The one shell file left that sources `dev/windows_skip.sh` after reading Q16,
`dev/test_init_e2e_wiring.sh`, stops reporting success where it did not walk: on Windows it
prints its two lines and exits 1. A suite judged by its ending has no "not run", so the run
records the file as failed there. Once its proof carries `@env(macos)`, a Windows runner never
starts it; only a person running the suites by hand on Windows sees the failure.

## Least sure

1. **run_script RULE-63.** The suggested pytest command starts with `python3`. On a python.org
   install on Windows that name does not exist, so the suggestion would not run. Whether the
   suggestion should read otherwise on Windows was question 6: it starts `py -3 -m pytest`.
2. **mutation RULE-32** (was RULE-18). The Windows case is "installed, and still no engine",
   with question 12's reason. Its test, PROOF-79's, gives the system as Windows; on the runner
   it asks the real one.
3. **scaffold RULE-37 PROOF-52**, the Go module. It is not part of the walk, so it is left
   without `@env(macos)`. Tag it if "RULE-37 is Mac only" means every proof of the rule.
4. **update RULE-31 PROOF-112 and PROOF-113.** They make no link, so they are left untagged.
5. **The signing rules** (signatures RULE-18, 20, 45, 50; states RULE-47). They rely on Windows'
   own `ssh-keygen`, which refuses a private key file that other accounts can read. A key made in
   a temporary folder may need its permissions narrowed before it signs.
6. **server RULE-22.** It assumes `sh` is on the Windows runner's search path, as Git for Windows
   provides it.
7. **run_script RULE-4.** SQLite may not be on a Windows runner; the runner file or the test has
   to put it there.
8. **evidence RULE-27 (was RULE-14) and run_script RULE-21.** Their tests pretend to be Windows today, so the
   Windows proof needs a new check that asks the real system.
