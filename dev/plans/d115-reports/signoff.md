# Lane `signoff`, round 1

Specs: `signatures` (44 proofs), `package` (38 proofs). Branch `lane/d115-signoff`, from
`d115/base` at `e2c3023d4`.

## Tests

`python -m pytest <files> -q`, one process.

| When | Files | Passed | Failed | Errors | Skipped |
|---|---|---|---|---|---|
| Before my first change | `test_signatures.py`, `test_export.py`, `test_tag.py` | 19 | 39 | 60 | 0 |
| After my last change | `test_signatures.py`, `test_export.py` | 76 | 5 | 0 | 1 |

Before, by file: `test_signatures.py` 11 passed, 21 failed, 19 errors; `test_export.py` 8 passed,
11 failed, 32 errors; `test_tag.py` 7 failed, 9 errors.

**Skipped for a missing tool or system:** `package PROOF-39`
(`test_on_windows_two_clones_give_the_same_bytes`), tagged `@env(windows)`, skips off Windows.
`ssh-keygen` was absent from the cloud container; I installed `openssh-client` there with
`apt-get`, so no test skipped for it and every signing test ran with real SSH-signed commits and
tags. Integration's Mac run of both files whole still stands.

**Waiting on another lane**, each failing for that reason alone:

| Proof | Test | Waits on | What it gets today |
|---|---|---|---|
| `signatures PROOF-242` | `test_a_proof_with_nothing_to_check_shows_its_reason` | `evidence`: a proof entry reading `nothing to check` | the payload reads the anchor rule as not passing, so the sign-off refuses with `1 rule does not pass` |
| `package PROOF-72` | `test_a_proof_with_nothing_to_check_carries_its_reason` | `evidence`, as above | the same refusal |
| `package PROOF-69` | `test_the_project_is_named_by_its_own_files` | `states`: `project.project_name` | the stub answers the folder's name, `work` |
| `package PROOF-75` | `test_a_test_names_who_last_changed_it` | `states`: `wording.test_last_change` | the stub answers None, so `changed_by` is null. I checked the span the package hands it with a stand-in: `(tests/test_login.py, 6, 8)` and `(…, 11, 13)`, the comment line to the test's last line |
| `package PROOF-5` | `test_a_rule_with_no_proof_is_left_to_write_one_for` | `states`: `summary.rule_kind` counting `no_proof` with no gate | not in the plan's list of waits. Today `no_proof` is counted at the gate `signed` alone, so with no gate the rule reads `no test`, which blocks, and the sign-off refuses with `1 rule does not pass at <sha7>: login RULE-3` |

## Section 4's row

| | Gone | Reworded | Right | Added |
|---|---|---|---|---|
| As found (`test_signatures.py`, `test_export.py`) | 57 | 46 | 6 | |
| As found, `test_tag.py` | 16 | 0 | 0 | |
| As left | 0 | 0 | 82 | 30 |

The 30 added are the proofs no comment named: `signatures` 223 to 230, 232 to 238, 240 to 243;
`package` 65 to 72, 74, 75, 76. Every proof of both specs has exactly one comment: 44 of 44 and
38 of 38.

Appendix A's script over my files, its last line:
`0 gone, 0 reworded, 82 right as they stand.`

## Every reworded comment

Both files were rewritten whole, so each test below is new code at a new line; the old line is
where the comment stood at `d115/base`. Each `fixed` names what the test now sets up, does and
asserts that it did not.

- `dev/test_signatures.py:276` signatures PROOF-115 stated: renamed to say it reads as `ssh-keygen -l` prints it.
- `dev/test_signatures.py:286` signatures PROOF-116 stated.
- `dev/test_signatures.py:300` signatures PROOF-118 fixed: the GPG key id is set over committed evidence that passes, through the command line; it asserts exit 1 and the first line.
- `dev/test_signatures.py:311` signatures PROOF-21 fixed: run over committed evidence that passes with a `VERSION`; asserts the four lines and exit 1, HEAD unmoved.
- `dev/test_signatures.py:319` signatures PROOF-95 fixed: as PROOF-21, the `ssh-keygen` line left out.
- `dev/test_signatures.py:398` signatures PROOF-217 fixed: the walk signs with no stop, the package's fingerprint is changed and committed, then the reason.
- `dev/test_signatures.py:449` signatures PROOF-206 fixed: results committed at HEAD with `login RULE-2` failing; asserts the one new line ending `then purlin:sign.`
- `dev/test_signatures.py:495` signatures PROOF-207 fixed: the same host setup, now over committed evidence with no package committed; the line ends `Pull, then run purlin:sign.`
- `dev/test_signatures.py:553` signatures PROOF-208 fixed: the second run is the command line; asserts only the one line and exit 1.
- `dev/test_signatures.py:623` signatures PROOF-209 fixed: asserts `Signing 0.1.0 at <sha7>.` on the line after the last run line.
- `dev/test_signatures.py:661` signatures PROOF-211 fixed: the head `login RULE-2   hand check` and the new question.
- `dev/test_signatures.py:669` signatures PROOF-200 fixed: `PROOF-2` `@manual` and `PROOF-3` tied to `test_lockout_page`; asserts the line under `PROOF-3`.
- `dev/test_signatures.py:732` signatures PROOF-218 fixed: stops at the hand check; the new `STOPPED` line, exit 0, no commit, no file.
- `dev/test_signatures.py:742` signatures PROOF-219 fixed: an empty line at the audit's question, the hand check and the last question.
- `dev/test_signatures.py:764` signatures PROOF-214 fixed: `package_hash`, `login RULE-2` among `shown.hand_checks`, `audit_list_opened` false, the note, no answer word.
- `dev/test_signatures.py:786` signatures PROOF-75 stated.
- `dev/test_signatures.py:905` signatures PROOF-220 fixed: `RULE-1` weak and `RULE-2` a hand check; asserts `  login RULE-1   <finding>`, the stop's head with no question after it, the last line.
- `dev/test_signatures.py:928` signatures PROOF-221 fixed: the answers file gives `login RULE-2` a note; asserts the note printed after the question and in the sign-off.
- `dev/test_signatures.py:946` signatures PROOF-222 fixed: `login RULE-2` a hand check, the answers name no stop.
- `dev/test_export.py:290` package PROOF-1 fixed: the first sign-off's commit carries the package; one worktree.
- `dev/test_export.py:298` package PROOF-2 fixed: `purlin:sign --version beta`, read from the signed commit.
- `dev/test_export.py:307` package PROOF-22 fixed: as PROOF-2 with no `VERSION`.
- `dev/test_export.py:319` package PROOF-3 fixed: the sixteen keys, `purlin-package/4`, `purlin_version`, `commit`.
- `dev/test_export.py:328` package PROOF-30 fixed: `2.1.0` signed in `<s>`, then `2.2.0` signed; `commit` reads `<c>`.
- `dev/test_export.py:414` package PROOF-5 fixed: signed; the third rule's words, no proofs, no tests, one result `no test`, `left` `no_proof`, the first line of `left`. Waits on `states`.
- `dev/test_export.py:397` package PROOF-8 fixed: `met` true, `rules` 2, `steps`, `left` empty.
- `dev/test_export.py:554` package PROOF-61 fixed: signed.
- `dev/test_export.py:563` package PROOF-62 fixed: signed; `checked` reads `in the sign-offs` with no gate.
- `dev/test_export.py:403` package PROOF-63 fixed: `met` true and `left` exactly `1 rule to strengthen`.
- `dev/test_export.py:436` package PROOF-55 fixed: the keys the format lists, `met` true, no word of compliance.
- `dev/test_export.py:453` package PROOF-9 stated: read from a signed package.
- `dev/test_export.py:493` package PROOF-25 fixed: results from a remote runner alone on this machine's system; asserts each of the eight values.
- `dev/test_export.py:514` package PROOF-26 fixed: no `strength`.
- `dev/test_export.py:521` package PROOF-20 stated.
- `dev/test_export.py:527` package PROOF-29 fixed: no gate.
- `dev/test_export.py:467` package PROOF-18 fixed: signed.
- `dev/test_export.py:581` package PROOF-56 stated.
- `dev/test_export.py:590` package PROOF-57 fixed: the anchor is signed with `login`, its hand check answered.
- `dev/test_export.py:760` package PROOF-13 fixed: two clones at one commit each sign `2.1.0` with their own signer; byte for byte, `}` and a newline, no carriage return.
- `dev/test_export.py:773` package PROOF-39 fixed: as PROOF-13 with `core.autocrlf` true; skips off Windows.
- `dev/test_export.py:537` package PROOF-15 stated.
- `dev/test_export.py:794` package PROOF-32 stated: read from the signed commit.
- `dev/test_export.py:801` package PROOF-17 fixed: through `purlin:sign --check`.
- `dev/test_export.py:819` package PROOF-45 fixed: through `purlin:sign --check`.
- `dev/test_export.py:829` package PROOF-46 fixed: `purlin-package/3` against `/4`.
- `dev/test_export.py:370` package PROOF-52 fixed: the walk answered yes; exit 1, one line carrying the operating system's message, no commit, no tag.

## Every test deleted

`dev/test_tag.py`, whole: `test_a_commit_of_its_own_the_host_lacks_is_released`,
`test_a_hand_check_at_passed_is_named_and_listed_not_checked`,
`test_a_host_copy_ahead_refuses_the_release`, `test_a_named_version_names_the_release`,
`test_a_package_with_no_tag_yet_is_written_again`,
`test_a_rule_whose_test_fails_refuses_the_release`,
`test_a_spec_that_cannot_be_counted_refuses_the_release`,
`test_a_tag_already_written_refuses_the_release`, `test_a_weak_or_unaudited_rule_does_not_refuse`,
`test_at_passed_the_package_is_committed_and_tagged`,
`test_at_signed_the_package_is_committed_and_no_tag_written`, `test_git_refusing_the_tag_is_named`,
`test_no_version_refuses_the_release`, `test_nothing_is_fetched_or_pushed`,
`test_the_version_file_names_the_release`, `test_work_not_committed_refuses_the_release`.

`dev/test_signatures.py`, each carrying only gone comments: `test_a_key_literal_gives_its_fingerprint`,
`test_a_commit_signed_with_the_signers_key_counts`, `test_a_signed_commit_by_another_author_counts`,
`test_anyone_with_a_key_signs`, `test_the_script_runs_as_a_command`, `test_at_passed_nothing_is_signed`,
`test_uncommitted_work_is_refused`, `test_no_package_is_refused`,
`test_a_commit_after_the_package_is_refused`, `test_a_weak_stop_shows_the_test_and_the_results`,
`test_the_strong_list_opens_on_list`, `test_walk_makes_each_strong_rule_a_stop_after_the_others`,
`test_a_proof_for_one_system_shows_its_tag`, `test_a_proof_no_test_carries_out_says_so`,
`test_no_audit_yet`, `test_strong_with_no_finding`, `test_strong_with_a_finding`,
`test_weak_with_a_finding`, `test_undecided_with_a_finding`,
`test_the_first_sign_off_writes_the_tag_on_its_commit`, `test_a_later_sign_off_leaves_the_tag`,
`test_help_exits_zero`, `test_an_unknown_option_after_another_exits_two`,
`test_an_unknown_option_alone_exits_two`, `test_a_root_that_is_not_a_directory_exits_two`,
`test_a_settings_file_that_cannot_be_read_stops_it`. The rest of the old names were rewritten
under new names for the proofs they kept, listed above.

`dev/test_export.py`, each carrying only gone comments:
`test_it_writes_the_version_file_prints_the_state_and_commits_nothing` (its `PROOF-1` is a new
test), `test_with_no_version_it_writes_nothing_and_says_how_to_name_one`,
`test_a_project_with_no_evidence_is_not_finished`, `test_a_broken_spec_is_left_to_repair`,
`test_at_passed_the_tag_is_passed`, `test_nothing_names_who_last_changed_a_test`,
`test_evidence_not_committed_is_left_out_and_named`, `test_exporting_twice_gives_the_same_bytes`,
`test_a_second_clone_at_the_tag_gives_the_committed_bytes`,
`test_check_passes_a_package_as_written`, `test_check_refuses_carriage_returns_before_each_newline`,
`test_commit_commits_the_package_as_evidence_at_head`,
`test_a_second_commit_over_the_same_evidence_is_unchanged`,
`test_commit_leaves_a_change_staged_elsewhere_out`,
`test_a_settings_file_that_cannot_be_read_stops_the_export`,
`test_a_settings_file_that_cannot_be_read_stops_the_check`,
`test_a_project_root_that_is_not_a_folder_is_refused`, `test_an_option_with_no_value_is_refused`,
`test_an_argument_it_does_not_take_is_refused`, `test_check_beside_another_option_is_refused`,
`test_check_names_a_key_the_format_does_not_name`,
`test_check_names_top_level_keys_out_of_the_format`, `test_check_names_a_file_that_cannot_be_read`,
`test_a_project_with_no_commit_is_not_written`, `test_a_commit_git_cannot_check_out_is_not_written`,
`test_a_commit_git_refuses_is_not_committed`, `test_a_file_git_cannot_add_is_not_committed`.

Code deleted with them: `scripts/export/release.py` whole; `package.py`'s command line, its
`--commit`, `commit`, `summary_lines`, `version_name`, `state`, `gate`, `mutation_engine` and the
audit's `strength`; `sign.py`'s `--release`, the gate refusal, the package-committed refusal,
the weak, unaudited and strong stops, the strong list, `one_by_one`, `in_list`, the `Sign-offs of`
line and the test bodies printed under a tied test.

## The deliberate break

`package.only_records_between` made to answer True always: `package PROOF-68`,
`signatures PROOF-226` and `signatures PROOF-225` failed. Restored with
`git checkout -- scripts/export/package.py`.

## Lines a person reads that I chose

| Line | Where it prints |
|---|---|
| `The evidence package was not written: <why>. Nothing was signed; run purlin:sign again.` | `purlin:sign`, where the package cannot be built or written (`package RULE-23`); `<why>` is the operating system's or git's own message |
| `The audit's findings: <n> weak.` | `purlin:sign --show`, in place of the walk's question, before the list |
| `Rule`, `Proof`, `Results` and `What the audit found` as headings of a hand check's stop, with the rule's words, each proof and finding indented two spaces | a hand check's stop, walk and `--show` |
| `    tied to no test` | under a proof that is not `@manual` and has no test tied, in a stop |
| `  <System>: <word> on <machine>` | a stop's result line; `; nothing to check for <PROOF-N>: <reason>` after it is `PROOF-242`'s |
| `Usage: sign.py [--version <version>] [--show \| --answers FILE \| --check FILE] [--project-root DIR]` | standard error, exit 2 |
| `sign.py: --check needs the package file to check.`, `sign.py: --version needs the version to sign.`, `sign.py: --show, --answers and --check are three steps; name one.`, `sign.py: --check reads a file and takes no version.` | standard error, exit 2, after the usage line |

Kept as they were: `No sign-off: <file> cannot be read: <why>.` (`--answers`), the
`--check` reasons, `sign.py: <dir> is not a directory.`, `sign.py: unknown option <x>`,
`sign.py: unexpected argument <x>`, `--answers needs the file that holds them.`,
`--project-root needs a directory.`, and `No tag: git could not write <tag>: <why>.`, moved
from `release.py` as K8 says.

## Differences from section 3

1. **`package.audit` counts every rule**, strong and weak by the verdict its audit gives and
   `not_audited` otherwise. The payload's `summary.audit` counts only rules whose passed cell
   reads `passed`, and does not count a hand check as not audited; `signatures PROOF-232`
   needs the hand check counted (17 strong, 1 weak, 1 not audited of 19). The overview reads
   the package's numbers, so the walk and the package agree.
2. **A proof's `written_by` follows the proof's line through its edits** (`git log -L`), not
   K7's "the oldest commit whose diff adds the line's words". `package PROOF-74` says a proof
   Quinn wrote and Pat reworded reads `written_by` Quinn, which the words alone cannot give,
   and the spec holds. A rule's `written_by` is K7's: the oldest commit `git log -S` finds
   adding its words, which holds through a renumber (`PROOF-76`). `changed` is the newest
   commit on the proof's line, which is what `git blame` names for a committed line.
3. **`met` is worked out in `package.py`** as no `left` kind in `summary.BLOCKING`, not by
   calling `facts.tests_fact`, whose stub answers `not met`. Same definition; integration may
   point it at `facts.tests_fact` once `states` merges.
4. **A later sign-off signs the package `HEAD` holds** for the version and does not build it
   again, so its commit carries its own file alone (`signatures RULE-120`) and the first
   signer's file keeps counting even where results were committed after the tag.
5. **`results[]` lists only the sections that hold a result for the rule**, by its rule word or
   its proofs' entries. A remote runner's section that ran one rule no longer adds `no test`
   to every other rule; `runs[].rules` counts the same way (`package PROOF-66`).
6. **A rule's `audit` in the package** carries `verdict`, `findings`, `notes`, `explanation`,
   `breaks`, `model`, `criteria`, `at`, `commit` and `source`, as K2 and K6 name them, and no
   `strength`. `explanation` and `breaks` read empty until `evidence` writes them.
7. **The helpers moved from `release.py`** (`tag_exists`, `write_tag`, `uncommitted_work`,
   `behind_host`, `behind_words`, `NO_TAG_GIT`) are all in `sign.py`; `write_tag` always signs.
8. **A sign-off's `notes`** are `{feature, rule, note}`, one per hand check walked; `kind` went
   with the other stops.
9. **`runs` groups every section the package lists**, current or not. The sign-off refuses a
   result not on this code before it walks, so at a sign-off every run is on this code.
10. `package PROOF-3` names `commit` "the commit the tests ran at"; by `RULE-3` it is `HEAD`
    stepped back over package commits alone, which is the commit that carries the results. The
    test asserts that sha, taken before signing.

## Left open, unbuilt, or failing elsewhere

- **The sign-off's `schema` stays `purlin-signoff/1`** though `shown` changed shape at format
  15. No decision or contract says to change the string; left for the owner.
- **A `dirty` section is not refused.** K7 says a result counts when current, not `dirty` and
  `same_code`. `same_code` is refused by `NO_SIGNOFF_NOT_THIS_CODE`; a result that is not
  current makes its rule fail the payload's cells and is refused as `NO_SIGNOFF_FAILING`; no
  spec or contract gives the words for a dirty one, so none is printed. Left open.
- **On a detached `HEAD` a later sign-off ends `Push it: git push origin`** with nothing after
  it, since `signatures RULE-118` leaves the branch out and names nothing in its place.
- **K15's grep over my files finds one line**: `dev/test_export.py` carries `purlin-package/3`,
  because `package PROOF-46` fixes that word in its own text. The proof holds.
- **Cost of `authors`**: one `git log -L` per proof, about 0.1 seconds each here; for this
  repository's 831 proofs a sign-off would spend about 80 seconds on it.
- **Files I do not own that now fail or read stale**, from deleting `release.py` and changing
  `sign.py`'s command line:
  - `scripts/run/purlin_run.py` lines 55, 1198 and 1205 import and name `release.py`
    (`run`, K10 removes `--release`).
  - `dev/test_report_refresh.py` lines 105 to 110 import `release` and line 119 calls
    `sign.main` with `--release` (`dashboard`).
  - `skills/sign/SKILL.md` lines 37 and 99 pass `--release`; `skills/export/SKILL.md` and
    `dev/test_skill_export.py` name `package.py`'s command line; `references/purlin_commands.md`
    lines 147 and 148 describe the old exits of `sign.py` and `package.py`;
    `references/commit_conventions.md` names `purlin:export` and `--release` (`words`).
  - `signature_format.md` now points at `references/evidence_and_signoff.md`, which `words`
    writes in round 2.

## Session cost

Not readable from inside the session.
