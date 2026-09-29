# What the thirteen lanes brought back

Every lane is merged into main. This file is the input of the integration step.

## L1 core

Acceptance passed in the lane: False. Commits: 353275b99 feat(states): every rule takes the gate, a hand check needs no note, an anchor rule is signed per feature; 5762e1f08 feat(summary): a cell a rule does not carry is no longer counted as reached; 6c00bf238 feat(skill_status): status ends on the summary and Left to do

### Waits on other lanes

- dev/test_states.py::TestPayload::test_an_anchor_rule_is_signed_once_in_each_feature (states PROOF-148, PROOF-149, RULE-76) | lane: L5 signing | needs: signatures.is_current comparing the stored signed_hash with signed_hash(entry), whose first line is applies_to (section 2.4, section 7 item 3). Today's is_current ignores applies_to, so login's signature also binds the rule under billing and under the anchor. Passes with the contract stood in.
- dev/test_states.py::TestTheFixturesAreTheContract::test_the_fixtures_carry_exactly_the_keys_the_builder_writes (states PROOF-82, RULE-70) and ::test_every_fixture_has_the_key_set_the_builder_writes (PROOF-96, PROOF-29; RULE-27, RULE-25) | lane: L10 dashboard | needs: dev/fixtures/report/{solo,team,regulated}.json: in fixtures only '.features[].rules[].cells.*.machine', '.features[].rules[].cells.*.os', '.gate.trust'; in the builder only '.features[].rules[].cells.*.key_fingerprint', '.features[].rules[].cells.*.signer_name'. Every fixture rule should also carry every cell up to its gate, since no rule is marked lower.
- dev/test_states.py::TestStatusTable::test_an_updated_project_prints_it_only_once_a_key_returns (states PROOF-104, PROOF-105, RULE-41) | lane: L9 upgrade | needs: scripts/init/update.py:462 stops reading resolved.trust (L9 deletes _ask_trust). The same cause fails 70 tests in dev/test_init_update.py.
- dev/test_specs_reader.py::TestGate::test_trust_is_local_or_remote_and_defaults_to_local and ::test_the_settings_written_out_are_the_ones_a_project_can_name (unmarked) | lane: L13 schema | needs: delete the trust test and drop 'trust' from the as_dict key list, since resolve_gate no longer returns trust (L1 plan, decision 75). L13's plan does not list this.
- dev/test_gate_check.py (17) | lane: L7 runner | needs: the file is deleted with scripts/ci/gate_check.py (section 7 item 1)
- dev/test_tag.py (11), dev/test_signatures.py (7 failed, 1 error) | lane: L5 signing | needs: stale, level and trust tests go; the tag and the walk read `left`; the frozen dev/sign_project.py SPEC/tagged fixture assume a `[level: passed]` rule (see contradictions)
- dev/test_export.py (5 failed, 5 errors) | lane: L6 package | needs: package drops level, meets_gate, trust; errors come from the frozen `tagged` fixture in dev/sign_project.py (see contradictions)
- dev/test_run_script.py: test_a_passed_level_is_read_only_at_the_gate_passed, test_a_passed_level_meets_the_strong_line_on_its_tests, test_changed_findings_stale_the_signature_and_the_run_says_so | lane: L3 run | needs: the level clause of _audit and RULE-49's level half deleted; WENT_STALE and RULE-53 deleted
- dev/test_purlin_report.py: test_a_rule_row_draws_only_the_badges_its_level_asks_for, test_a_rule_screen_shows_only_what_its_level_asks_for, test_the_gate_and_its_count_are_two_chips (seen in the purlin_run full run, not in --fast) | lane: L10 dashboard | needs: levelTag/levelSource and the count chip deleted (L10 plan)

### Contradictions and calls the lane did not make

- WHAT: The frozen helper dev/sign_project.py sets SPEC with RULE-1 marked `[level: passed]`, and `signed_project()` audits RULE-2 only. Its `tagged` fixture asserts that `tag_if_met` writes `signed/2.1.0`. Under decision 73 RULE-1 is asked for its audit and signature, so the tag is refused and the fixture fails at dev/sign_project.py:425. dev/test_tag.py, dev/test_export.py, dev/test_signatures.py, dev/test_gate_check.py and any other importer inherit this. No lane may edit the helper.
  DECISIONS: 73 (every rule is asked what the gate asks) against section 0 and section 8 (the helper modules are frozen for the fan-out)
  LEFT AS: Untouched. Options: (a) integration edits dev/sign_project.py so SPEC is EVERY_RULE_SIGNED and signed_project audits both rules; (b) L5 and L6 build their own projects in their own test files and stop using `signed_project` and `tagged`.
- WHAT: Step R deletes the payload keys `meets_gate`, `met`, `queue`, `hand_checks`, `stale`, `asks_*` and possibly `blocked_by`, and 'changes no spec text'. Several states rules and their proofs, all in L1's files, name those keys: RULE-24 with PROOF-28 (meets_gate, blocked_by), RULE-25 with PROOF-29, 90 and 141 (met, stale, queue, hand_checks, asks_*), and RULE-27 with PROOF-31 (top-level `queue`). They describe what the payload carries today and pass. After R they fail.
  DECISIONS: section 1 R ('It changes no spec text') against section 0 (no lane deletes a payload key another lane reads)
  LEFT AS: RULE-24 unchanged; RULE-25 and RULE-27 still list the keys. Options: R also edits specs/mcp/states.md and dev/test_states.py when it deletes the keys, or a follow-up L1 pass after R.
- WHAT: An anchor's rule that no feature requires, and that no global flag makes apply to every feature, has no consumer. Decision 76 says only that the rule counts as signed when signed in every feature it applies to.
  DECISIONS: 76
  LEFT AS: Kept as today: with no consumer, the anchor's own listing is signed by any counting signature that binds it as listed under the anchor. Options: keep; or read such a rule as unsigned until some feature applies it.
- WHAT: For an anchor's rule listed under the anchor itself, the plan defines only the signed cell ('met only when every consumer has a counting signature'). It does not say whether the hand check of a `@manual` anchor rule, meaning the strong cell reading `strong` and `hand_checked`, needs every consumer too, or only one.
  DECISIONS: 76, 78
  LEFT AS: Chosen, one notion for both: the anchor's own listing counts a signature only once every consumer has one, so the hand check and `hand_checked` also wait for every consumer. Listed under a feature, that feature's own signature settles both. Option: let any one consumer's signature be the hand check and keep the all-consumers rule for the signed cell alone.
- WHAT: L1 removes `trust` from gate.resolve_gate. dev/test_specs_reader.py, which L13 owns, has two unmarked tests that read GateConfig.trust and expect 'trust' in as_dict(), and L13's plan does not remove them. scripts/init/update.py:462 (L9) reads `resolved.trust`; L9's plan does delete that line.
  DECISIONS: 75
  LEFT AS: resolve_gate returns no trust, as L1's entry says. The two L13 tests and 70 L9 tests fail until those lanes merge. L13 needs to be told.

### Departures

- PROOF-58's specific fixture strings (`2 of 3 · 86%`, `1 of 3`, `0 of 2 · 48%`) were dropped. The fixtures are L10's and will change, and they carried the levels. The board cells' `<n> of <rules>` is now proved by the new PROOF-142 over a stated rollup, rendered by board.py. PROOF-58 keeps only "the table and the board module render the same cells".
- PROOF-26 (RULE-22) is proved at the unit level: rule_cells gets a signature shaped as L5's counts returns it, `counts` false with the reason `the commit that added it is not signed`. The reason string is L5's, and a whole-project test would wait on L5's counts.
- Several proofs I had to touch because they said "meet(s) the gate" or named a level were split to one case each (decision 71). That produced PROOF-117 to 149 beyond the plan's list, for example PROOF-9, 17, 32, 56, 74, 75, 78 and 93. Tests keep their bodies and carry the new markers. PROOF-53 was shortened to 60 words.
- `need` and the queue: `_need` is deleted, but the queue is still built until step R. `need` now comes from the rule's `left`: `to_test_by_hand` gives `hand check`, `to_sign` gives `signature`. As a result, an unchecked `@manual` rule at the gate `passed` now gives a queue row whose `word` is null. Before, the queue was empty below `strong`.
- `level` in the payload now always equals the gate and `level_marked` is always null. Both keys stay until step R, as section 0 requires.
- `flags.stale` and the rollup's `stale` count are still computed ("signature files exist and none binds") for their other readers until step R. No cell reads `stale`.
- `HAND_CHECK_WORDS` is kept because scripts/ci/gate_check.py (L7) reads it. Only its routing into the queue is gone.
- `gate.level_of`, `TRUST_VALUES` and `DEFAULT_TRUST` are kept but unused by L1 (section 0). `board.headline`, `bucket_line`, `queue_line` and `needs_a_person` are kept for step R. `headline` still holds the words "meet the gate", and R deletes it.
- The status table's sort now reads each feature's count of rules with a non-null `left`, not `met - rules` (interfaces file: "L1 changes this when met goes").
- dev/test_states.py gained its own helpers `_listed`, `_sign` and `_bound`. They write and shape format-11 signatures carrying `applies_to`, `signed_hash`, `code_hash`, `machines`, the four hashes and `key_fingerprint`, named `<RULE>.<signed_hash[:8]>.<slug>.json`, so the tests hold under L5's is_current. The frozen `mcp_project.Project.signature` writes the old format and names files by the old triple hash, so two per-feature signatures would collide.

### For integration

- Merge order: after L5, L9, L10 and L13 merge, rerun dev/test_states.py whole. The 4 failures listed under waits_on_other_lanes should clear. I checked the anchor test against a scratch stand-in of L5's contract and it passes.
- The frozen helper dev/sign_project.py (SPEC with `[level: passed]`, signed_project, tagged) must be settled at integration; see contradictions. Without that, test_tag, test_export, test_signatures and test_gate_check cannot pass whatever those lanes do.
- For step R, the names L1 left in place for other readers: payload `queue` with `_sorted_queue` and `queue_row`, rule `need` (now from `left`), `level` (the gate), `level_marked` (null), `meets_gate`, `blocked_by`, `flags.stale`, rollup `met`/`queue`/`hand_checks`/`stale`/`asks_*`, `states.HAND_CHECK`, `states.SIGNATURE`, `states.HAND_CHECK_WORDS` (gate_check reads it), `states.asked_keys`, `gate.level_of`, `gate.TRUST_VALUES`, `gate.DEFAULT_TRUST`, `board.headline` (still holds "meet the gate"), `board.bucket_line`, `board.queue_line`, `board.needs_a_person`, `board.bucket_counts`. When R deletes the payload keys, specs/mcp/states.md RULE-24, RULE-25 and RULE-27 with PROOF-28, 29, 31, 90 and 141 and their tests in dev/test_states.py must change in the same step (see contradictions).
- The integration sweep for 'meets the gate', 'level:', 'queue' and 'stale' will still find, in L1's files: states.md RULE-25 and RULE-27 key names (`queue`, `stale`), states.py and payload.py comments on the transitional queue and `stale` flag, board.py `headline` and `queue_line`. All go with step R.
- `hand_checked`, the signed cell and RULE-76 compare signatures through signatures.is_current(signature, entry), where entry now carries applies_to, code_hash and machines. For an anchor's own listing it is called once per consumer, with that consumer's applies_to and code_hash. L5's final is_current must compare signed_hash per section 2.4 and section 7 item 3 for per-feature anchor signing to work.
- Rebuild nothing for this lane beyond what integration already rebuilds; no generated file was staged.
- No shell suite belongs to this lane.
- skills/status/SKILL.md is 100 of 100 lines.
- The status report now sorts rows by how many listed rules carry a non-null `left`.

### Deleted

- dev/test_queue.py, whole: its tests proved the queue rules RULE-29, 30, 31, 53 and 54, which are deleted.
- In states.py: `_need`, `_cell_blocks`, `_what_moved`, `AUDIT_MOVED`, `HASHES_MOVED`, the level branches of `_bucket` and `_blocked_by`, the reading of `level_marked`, the `stale` word and its reasons in the signed cell, and the `machine` and `os` fields of the signed cell.
- In payload.py: the reading of `rule_meta` and the note-requiring `hand_checked`.
- In summary.py: the transitional clause that counted a missing cell as reached.
- In gate.py: the reading, validation, warning and return of `trust`.
- In board.py: the reading of `asks_strong` and `asks_signed`.
- The level-based tests in dev/test_states.py (classes TestLevels and TestALevelAsksItsOwnQuestions, the PROOF-55 test, the fixture queue-row test) and dev/test_summary.py PROOF-27.

### Looked at

Nothing visual changed in this lane, so nothing was looked at with playwright. board.py's Strong and Signed cells now read `<n> of <rules>`. On the dashboard that text is drawn by scripts/report/src/board.js (L10), which this lane does not own. The only visible change here is the status table in the terminal. Its self-run output was read, and the rows line up under their headings, for example "states  54 (+6 shared)  128  55 of 60 · 5 failing  0 of 60 · n/a  0 of 60".

## L2 evidence

Acceptance passed in the lane: True. Commits: b040ce4f4 feat(evidence): a proof passes only when every tied test ran, and each system has its words; a9ba36976 feat(evidence_writer): where the tests ran, not run for another system, notes, and two commits

### Waits on other lanes

- dev/test_evidence_writer.py::test_a_commit_run_makes_the_two_commits (evidence_writer PROOF-50, RULE-19) | lane: L3 run | needs: `--commit` in purlin_run.py must collect the spec of each feature run, the test files carrying their markers and .purlin/config.json, call `work = evidence_writer.commit_work(project_root, paths)`, then call `evidence_writer.commit_local(project_root, work, removed)` without wrapping either call in print()
- dev/test_run_script.py::TestTheLastLines::test_the_audit_ends_in_the_order_the_design_gives | lane: L3 run | needs: purlin_run._audit must call evidence_writer.commit_local(...) without print(). It prints its own line and returns None, so today an extra line reading None appears after `Evidence committed.`
- dev/test_run_script.py::TestTheLastLines::test_the_skipped_rules_and_the_stale_line_take_their_places | lane: L3 run | needs: Same as above: the call to commit_local in _audit (and in the plain --test arm and in _nothing_selected) must not be wrapped in print()

### Contradictions and calls the lane did not make

- WHAT: The plan raises the evidence schema string to `purlin-evidence/2` (L2 entry, contract 2.5), and the reader ignores any other schema (clean release, no old spelling accepted). But the frozen helper modules dev/mcp_project.py and dev/sign_project.py write evidence with the literal 'purlin-evidence/1', and so do other lanes' test files dev/test_drift.py (L11) and dev/test_host.py (L7). I measured it: with SCHEMA set to /2, dev/test_states.py, dev/test_signatures.py, dev/test_drift.py and dev/test_host.py alone gave `84 failed, 149 passed, 1 error`. No lane may edit the frozen helpers during the fan-out, so the change cannot be made without breaking every lane's sweep once this lane merges.
  DECISIONS: Plan L2 entry and contract 2.5 (schema `purlin-evidence/2`, Format-Version 3 to 4); section 0 and section 8 (the helpers are frozen); decision 44 (no reader accepts an old spelling).
  LEFT AS: SCHEMA stays 'purlin-evidence/1' in scripts/mcp/purlin/evidence.py, in evidence_format.md, in evidence RULE-12, PROOF-18 and its test, and in evidence_writer RULE-1 and PROOF-1. Format-Version is raised to 4 for the new fields (machine, hostname, notes). The options: (a) integration or step R changes it to /2 in one change: SCHEMA in scripts/mcp/purlin/evidence.py; the example and table row in evidence_format.md; evidence RULE-12, PROOF-18 and its parametrised case (which uses /2 as the wrong schema and would use /1); evidence_writer RULE-1, PROOF-1 and the literal in test_a_test_run_writes_the_feature_file_with_one_section; the literals in dev/mcp_project.py (lines 146, 220), dev/sign_project.py (208), dev/test_drift.py (514) and dev/test_host.py (106). This lane's test helpers already use reader.SCHEMA. Then the integration rerun rewrites .purlin/evidence. (b) The owner drops the schema bump and keeps /1 with Format-Version 4.

### Departures

1. The evidence schema string stays `purlin-evidence/1`. Contract 2.5 and the plan say `purlin-evidence/2`. The reason is under contradictions.
2. build_section gains two keyword parameters, `machine=None` and `hostname=None`, after `at=None`. The plan names the fields but not how they are passed. With nothing passed, `machine` is `platform.node() or 'unknown'` and `hostname` is `platform.node()`. The current purlin_run call therefore writes correct local sections before L3 merges. A new helper, `local_machine()`, returns `platform.node() or 'unknown'`.
3. `_same_observation` ignores `hostname` (with commit, dirty and at) and compares `machine`. The contract says hostname is "never compared". Decision 77 says a run on another machine replaces the results.
4. `commit_work(project_root, paths)` prints `Committed <sha7>, the work these results describe:`, then each file that commit changed, indented two spaces. It returns the new commit's full sha. When nothing among `paths` changed, it prints nothing and returns HEAD's sha. Outside git it returns ''. The features in the subject come from the spec paths in `paths` (`specs/**/<feature>.md`), in the order given, without repeats.
5. `commit_local(project_root, work_sha, removed=())` now prints its own line and returns None, following the plan's wording "printing the lines in section 2.6". Before, it returned the line for the caller to print. The subject is `purlin: evidence at <work_sha[:7]>`.
6. `.purlin/tests.md` `Last run` shows the system as Windows/macOS/Linux/Unix, not the stored word. This applies contract 2.8, "wherever a person reads a system", to a file a person reads. No other test reads that column.
7. An audit entry's `notes` are not part of the check that an entry repeats the one on disk. The contract says nothing about that comparison, so it stays as it is today, and RULE-14 is unchanged. As a result, when a rule is audited again with the same hashes, verdict, findings, model and criteria but new notes, the old entry and its notes stay. `notes` is written only when the audit gave some.
8. `proof_results` now returns `not run` as a value. Before, it returned only pass and fail. Callers in other lanes are affected; see for_integration.
9. The `sys.platform` fallback in host_os is deleted. There was no separate "evidence-only --commit path" in the files this lane owns to delete: commit_local became the second of the two commits. The path that commits only earlier evidence (purlin_run._nothing_selected) is L3's file.

### For integration

- L3 must call `work = evidence_writer.commit_work(root, paths)`, then `evidence_writer.commit_local(root, work, removed)`. Neither call is wrapped in print(): both print their own lines, and commit_local returns None.
  - Today purlin_run prints an extra line reading None at three calls: the plain --test arm, _audit and _nothing_selected. This is the cause of the 2 run_script failures and of evidence_writer PROOF-50.
  - `paths` must be the spec path of each feature run (`specs/<cat>/<feature>.md`), because the subject's feature list comes from those paths, plus the marked test files and `.purlin/config.json`.
- L3 (and L7 for --ci) pass `machine=` and `hostname=` to build_section as keywords.
  - For a ci section, machine must be `remote runner, <Windows|macOS|Linux/Unix>` (reader.os_word gives the word).
  - Until then --ci sections carry the runner's host name as machine.
- Callers of `proof_results` now receive `not run` for a proof listed missing or not run:
  - states.proof_result, states._section_passes and states._failing_where (L1): the semantics are right, but check them.
  - payload._machines (L1) tests `results.get(proof_id)` for truth, so a section where a proof only reads `not run` now counts as a source of `machines`. It likely should test `== 'pass'` or `in ('pass', 'fail')`.
  - package._results (L6) falls back to `'passed' if seen`, which would read `not run` as passed when a section has no `rules` entry.
- Sections now carry `machine`, so the payload's rule `machines` are no longer `{}`. The fixtures of dev/fixtures/report (L10) may need `machines` entries for the key-path test of states PROOF-82. It did not fail in this sweep.
- The schema string change from /1 to /2 (see contradictions) is left for integration or step R.
- Format docs that are now stale and not this lane's to edit:
  - references/commit_conventions.md lines 13, 43 to 51 (L12): the two commit subjects.
  - references/hard_gates.md line 83 and references/purlin_commands.md lines 110 and 111 (L12).
  - skills/test/SKILL.md line 57 (L3).
  - skills/audit/SKILL.md line 46 (L4).
  - docs/getting-started.md line 150, docs/how-purlin-works.md line 72, docs/running-and-evidence.md lines 90 and 141, docs/team-workflow.md line 57: the docs phase.
- The integration rerun (`purlin_run.py --test --all --commit`) is needed so every committed section carries machine and hostname.
- No generated file was staged.

### Deleted

- The `sys.platform` fallback of host_os(), and the `('linux', 'linux')` prefix it no longer needs.
- `missing` for a skipped test of a proof tagged for another system.
- commit_local returning its line for the caller to print. It now prints the line itself as the second of the two commits.
- The sentence "The tag run checks who committed each `ci/` file." in evidence_format.md.
- The `[level: ...]` tag the writer tests wrote into their specs, and the wording about levels in PROOF-9 and PROOF-12.

### Looked at

Nothing visual: this lane changes no page.

## L3 run

Acceptance passed in the lane: False. Commits: edd4d1427 feat(run_script): stop before a test, name each rule, commit the work first; da6f8ec2d feat(skill_test): the stops before a test, the two commits, the ending; 7156cdbf1 test(run_script): the required-rules suite reads the summary, no level tag

### Waits on other lanes

- every test in dev/test_run_script.py and dev/test_reports.py that runs the script and writes evidence (90 and 7 on the committed code), dev/test_e2e_required_rules.sh, and, outside this lane, dev/test_evidence_writer.py (12), dev/test_report_refresh.py (2), dev/test_init_scaffold.py::test_a_go_module_runs_through_the_command_init_writes | lane: L2 evidence | needs: `evidence_writer.build_section(..., machine=<str>, hostname=<str>)` to take the two keyword arguments named in section 2.5. The run passes `machine` as `platform.node() or 'unknown'` on a person's machine and `remote runner, <os_word>` under --ci, and `hostname` as `platform.node()`.
- run_script PROOF-142, PROOF-143, PROOF-96, PROOF-17, PROOF-86, PROOF-107 and the `_touched_project` tests that use --commit | lane: L2 evidence | needs: `evidence_writer.commit_work(project_root, paths)`, which commits the paths, prints `Committed <sha7>, the work these results describe:` and each path, and returns the first commit's sha or None when nothing was committed; and `commit_local(project_root, work_sha, removed)`, which commits the evidence as `purlin: evidence at <sha7 of work_sha>`. purlin_run prints whatever commit_local returns when that is a string, so either printing inside it or returning the line works.
- dev/test_run_script.py::TestHostOs::test_any_other_system_reads_linux (run_script PROOF-124) | lane: L2 evidence | needs: `evidence.host_os()` returns `linux` for any platform that is not Windows or macOS
- dev/test_run_script.py::TestTheCiArmCommitsItsSection::test_the_ci_arm_writes_its_section (run_script PROOF-12) | lane: L2 evidence | needs: `build_section` to write the `machine` field it is given into the section

### Contradictions and calls the lane did not make

- WHAT: `frameworks.suggest(project_root)` "returns the entry" and decision 80 says it "suggests one". Scaffold RULE-7, which moves to run_script, gave one entry to each framework detected. For a project with, say, pytest and vitest, nothing says which to suggest.
  DECISIONS: Options: (a) the first detected, as built; (b) one `Suggested for` pair per framework and a JSON list in `Suggested entry`, which is a change to the contract lines.
  LEFT AS: suggest returns the entry of the first framework detected, in registry order (pytest, vitest, jest, dotnet, go, sql, shell). RULE-63 and PROOF-129 say so. A second suite is written by hand; supported_frameworks.md says so.
- WHAT: Scaffold RULE-32 (`--add <framework>` keeps what was detected and records it once) is listed as moving to run_script. It describes a scaffold flag, and the run has no equivalent. Scaffold RULE-9's second half (a node project with mutation testing on is told that Stryker measures the breaks) is about init's mutation question, not the run.
  DECISIONS: Options: (a) L8 keeps RULE-32 and the Stryker half in scaffold, if `--add` and that line stay in scaffold.py; (b) both are retired with the init test questions.
  LEFT AS: Neither was added to run_script. RULE-64 carries only the jest and sql halves of RULE-9. supported_frameworks.md no longer mentions `--add`.
- WHAT: The contract gives no line for a marker that names a rule that has proofs. It only shows `<file>:<line> names <feature> <ID>, which no spec has.` for a name nothing matches.
  DECISIONS: Options: keep as built, or give it a line in the new shape with advice that fits it (name one of its proofs, or run purlin:build).
  LEFT AS: That case prints today's line, `purlin: <feature> <id> at <file>:<line> names a rule that has proofs; name one of them`, and still fails the run. The old closing lines `Remove the comment...` and `Remove each comment...` (FIX_ONE/FIX_MANY) are deleted. reports RULE-19 and marker_format.md say so.
- WHAT: No wording was fixed for two things the lane prints. First, the `why` sentences of `markers.py --near-misses`. Second, where the moved scaffold RULE-9 line (what a tool needs added) goes in the run's output.
  DECISIONS: The owner, or L12 in writing_style, may want to fix the wording.
  LEFT AS: The `why` sentences read, for example, "`purln` is one letter from `purlin`.", "There is no space after the colon." and "`logn` is one character from the feature `login`.". The needs line is today's frameworks.NEEDS text, printed after `Suggested entry:`.

### Departures

1. How `build_section` receives the two new fields. Section 2.5 fixes the fields, not the function's shape. I pass `machine=` and `hostname=` as keyword arguments named after the fields. Until L2 merges, every run that writes evidence stops on a TypeError.

2. The machine a remote runner names. purlin_run builds `remote runner, <Windows|macOS|Linux/Unix>` itself from `evidence.os_word(os_name)`. It does not ask ci.py or host.py (L7) for the runner's kind, because no function name for that was fixed.

3. The problem lines are printed before the status, in this order: after the `Evidence is missing` lines, and before `Evidence written` and the commit lines. A failing rule names every one of its failing tests on this machine, joined with `, `. The contract shows one `<file>::<test>`; with one failing test the line reads exactly as the contract gives it.

4. The first commit happens before the sections are built. With `--commit`, `commit_work` runs after the tests and before the evidence is built, so the evidence names the work commit. In a run that selects nothing, `--commit` still calls `commit_work` with only `.purlin/config.json`.

5. The order of the stops. No settings file and set-up-by-0.9.5 are checked first, before the settings are read. The no-test-command check comes after the check for no specs. The stop happens whenever no valid suite is left, so a `tests` setting whose entries are all malformed stops the same way, after the lines naming each malformed entry.

6. The audit's exit code changed with the contract. A rule that was weak in an earlier audit and is skipped this time no longer makes `--audit` exit 1 (PROOF-125). A run that selects nothing now starts the audit with exit code 1 where the evidence holds a failing test, at every gate. `project_counts` is replaced by `failed_rules` and a new `weak_rules`, and the run no longer reads `blocked_by`.

7. The FileMarkers class no longer has a `malformed` attribute. `comment_markers` returns a list of markers instead of `(markers, malformed)`, and a new `comment_lines` is shared with the near-miss finder. No file outside this lane used them.

8. PROOF-57's arrow assertion is gone. The test used to check that output carried `→`, which it found only because the status printed `→ Run: purlin:init --update`. The proof now checks the table's `─` and nothing else.

9. The tag-run proof asserts less. PROOF-68 now checks only that a line begins `Tag run: nothing is written.`, because the rest of that line belongs to L7's host.no_commit_line and still speaks of checking evidence.

### For integration

- **After L2 merges, rerun the lane on the merged tree.** Check that `build_section` accepts `machine` and `hostname` as keywords, that `commit_work` exists and returns the first commit's sha or None, and that commit_local's line is printed exactly once. Then run `python -m pytest dev/test_run_script.py dev/test_reports.py dev/test_skill_test.py -q` and `bash dev/test_e2e_required_rules.sh`. The expected result is all green. With a stand-in for L2 it was 1 failure: PROOF-124, the freebsd case of host_os.
- **Shell suite.** `dev/test_e2e_required_rules.sh` is rewritten: no level tag, and it reads the summary sentence. It passed with the stand-in.
- **Docs, which no lane owns this phase, now quote old lines:** docs/running-and-evidence.md:107 (`A remote runner runs it: purlin:init adds one.`), 143 (`signatures went stale`), and 191-192 (`names a proof no spec has` / `Remove the comment...`).
- **The tag-run line.** L7's host.no_commit_line still says "checks the evidence already committed". PROOF-68 now reads only its first sentence, `Tag run: nothing is written.`
- **L8 and scaffold.** L8 deletes scaffold RULE-6, 7, 9 and 32. RULE-7 and the jest/sql half of RULE-9 now live in run_script RULE-63 and RULE-64; see the contradiction about RULE-32 and Stryker. The run_script scope now also lists frameworks.py and supported_frameworks.md, so scaffold's scope must drop them. test_init_scaffold's go-module test expects init to write the go entry, which L8's `"tests": []` changes.
- **L11.** purlin:build can call `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses --project-root <dir>`. It prints one JSON array and exits 0; a bad command line exits 2 with `Usage: markers.py --near-misses [--project-root DIR]`.
- **L12.** purlin_commands.md needs the run's new exit-1 causes and `markers.py --near-misses`. commit_conventions.md needs the first commit subject, `purlin: specs, tests and settings for <feature>`.
- **Step R.** frameworks.entries_for is still used by scaffold.py and update.py.
- **Generated files.** Rebuild at integration; nothing generated is staged.
- **Visual check.** Nothing in this lane is visual, so there was nothing to look at with playwright.

### Deleted

- In scripts/run/purlin_run.py: `NO_SUITES`, `WENT_STALE` and the stale-signature count in `_audit` (with its signatures import). Also `project_counts`, replaced by `failed_rules`, and the level and `short_of_audit` clause of the audit's exit code.
- In scripts/run/reports.py: `NOT_A_MARKER`, `malformed_lines`, `NO_SUCH_FEATURE`, `NO_SUCH_PROOF`, `NO_SUCH_RULE`, `FIX_ONE` and `FIX_MANY`.
- In scripts/mcp/purlin/markers.py: the `malformed` attribute of FileMarkers and the malformed half of `comment_markers`/`parse_comment`.
- In specs/run/run_script.md: RULE-53, PROOF-76, PROOF-85 and PROOF-110.
- In dev/test_run_script.py: the tests that went with those, TestAFreshAuditStalesASignature and the level tests.

### Looked at

Nothing visual in this lane: no page, no dashboard. skills/test/SKILL.md is 118 of 120 lines.

## L4 audit

Acceptance passed in the lane: True. Commits: 0bf0aa825 feat(ai_audit): read the same rules at every gate, and keep notes apart; a3145aca2 spec(skill_spec): one proof, one case; 9f5fb6057 spec(skill_spec_from_code): rules from what the tests expect, no level; b859a2588 spec(skill_audit): the audit ends on the summary and Left to do

### Waits on other lanes

- dev/test_run_script.py::TestWhichRulesTheAuditReads::test_a_passed_level_is_read_only_at_the_gate_passed (run_script PROOF-76) | lane: L3 run | needs: Deleting this test with the level clause of RULE-49, as the L3 plan says. ai_audit.is_read no longer reads a level, so a [level: passed] rule is read under strong too.
- dev/test_run_script.py::TestTheAuditExitCode::test_a_passed_level_meets_the_strong_line_on_its_tests | lane: L3 run | needs: Deleting it with the level clause of _audit (decision 73). It uses _many(level='passed') and expects no model call, but the rule is now read.
- dev/test_run_script.py::TestWhichRulesTheAuditReads::test_a_rule_taken_from_an_anchor_is_read_only_as_the_anchors | lane: L3 run | needs: Changing the assertion 'shared RULE-1 (' in anchor[0]. Per the L4 plan the prompt header is now the bare line 'shared RULE-1', with no '(level X)'. A line match such as re.search(r'^shared RULE-1$', prompt, re.M) works.
- dev/test_run_script.py::TestWhenTheModelCannotBeReached::test_two_causes_in_one_run_print_one_line_each | lane: L3 run | needs: Its fake claude script checks 'if "feat RULE-1 (" in sys.stdin.read()', which no longer matches, so both rules get the same cause. It needs a line match on 'feat RULE-1' instead, for example '"\nfeat RULE-1\n" in sys.stdin.read()'.

### Contradictions and calls the lane did not make

- WHAT: What `purlin:audit --commit` commits. The L3 plan gives `--commit` both commits, the work and then `purlin: evidence at <sha7>`, but only says so for the test run. The current _audit calls commit_local alone.
  DECISIONS: Decision 80 (two commits in one step), contract 2.6
  LEFT AS: The audit skill says only what holds either way: --commit "commits under your own identity and ends on the evidence, with the subject `purlin: evidence at <sha7>`". If L3 gives the audit the first commit too, the sentence could name both commits, as purlin:test's does.
- WHAT: references/review_criteria.md, "What a person does with what the audit found", still says `purlin:sign` takes each of sign it, add a case and skip it. After decision 74 the sign walk reads only rules whose kind is `to_test_by_hand` or `to_sign`, so a weak rule no longer reaches it.
  DECISIONS: Decision 74; L5's walk
  LEFT AS: Unchanged. How the walk treats a finding is L5's to settle. The paragraph can then be cut to "Sign it" or pointed at `Left to do`.

### Departures

1. ai_audit.is_read keeps a `gate` parameter, now `gate=None` and not read, because purlin_run._audit (L3) still calls is_read(rule, gate, again=...). Step R can drop it once L3 stops passing it.

2. The answer shape for notes is not in any contract, so I defined it inside my own files. The prompt shows a `notes:` line after the findings, and the parser treats every `- ` line after `notes:` as a note.
- audit_one now returns {'verdict', 'findings', 'notes', 'model', 'criteria'}, with notes always a list.
- parse_answer keeps its (findings, settled) shape.
- There is a new answer_notes(answer).
- L2's evidence_writer.audit_entry is expected to write found.get('notes') as the optional audit.rules[].notes of contract 2.5.

3. render() does not print notes. No output line for them is given in the contract.

4. Changes the plan did not list, made because the text sat in my own files and described retired things (levels, queue, stale, trust, notes being required):
- review_criteria.md: "The three levels" became "What each gate asks of the audit", "Who is in the queue" is deleted, and "The proof shows more than one thing" moved from findings to notes. The criteria hash therefore changes.
- spec_quality_guide.md: "Choosing the level" is deleted, the `stale` row is folded into `unsigned`, and the manual-proof paragraph follows decision 84 (a note is optional).
- skills/spec/SKILL.md: the level-tag table and its paragraphs are deleted, and "stales" becomes "ends".
- skills/audit/SKILL.md:
  - `trust: remote` is gone.
  - The "two reasons" for a runner is now one reason, per decision 75.
  - The gate lines `Nothing blocks at the gate passed.`, `Audit: <n> strong, <n> weak.` and `gate strong met: ...` are gone; P0b had already removed them from the code.
  - The exit codes follow contract 2.6.

5. The spec-from-code report step drops "how many rules already have a passing test", because decision 81 says no test is run first.

6. skill_spec's Scope now includes references/spec_quality_guide.md, because RULE-7 makes a claim about the guide.

### For integration

1. Four tests in dev/test_run_script.py (L3) fail until L3 merges. Two go with the level clause (PROOF-76 of RULE-49, and test_a_passed_level_meets_the_strong_line_on_its_tests). Two look for "RULE-1 (" in the prompt, which is now the bare line "<feature> <RULE-N>": test_a_rule_taken_from_an_anchor_is_read_only_as_the_anchors and test_two_causes_in_one_run_print_one_line_each. If L3 did not update the last two, integration must change them to match the bare line.

2. Step R: drop the unused `gate` parameter of ai_audit.is_read once purlin_run no longer passes it.

3. L2: evidence_writer.audit_entry should copy found['notes'], which ai_audit now returns, into audit.rules[].notes.

4. CLAUDE.md line 71 says the guide covers "choosing its level"; that section is gone. The owner's file, so I left it; report it with the gate_check row.

5. Other files outside this lane still name what my files dropped:
- references/glossary.md line 131 names "choosing a level" in the guide (L12).
- docs/index.md line 61 says the same (docs phase).
- references/hard_gates.md still has "## The three levels" (L12).

6. The criteria text changed, so its sha256 changed. Old audit entries keep their recorded criteria hash, and nothing compares it.

7. Rebuild and commit the generated evidence and report at integration as planned; this lane staged none.

### Deleted

- The level condition in ai_audit.is_read, the 'level' key of the reading, "(level X)" in the prompt header and "level X" in the printed rule.
- ai_audit PROOF-3's level case and its test.
- The "The proof shows more than one thing" finding in review_criteria.md, which is now a note, and the sections "The three levels" and "Who is in the queue".
- The guide's "Choosing the level" section and its `stale` table row.
- The spec skill's level-tag table and its paragraphs.
- In the spec-from-code skill: the [level: passed] instruction, the tags on its example rules, the paragraph on why passed, and the "Do not write [level: strong]" bullet.
- skill_spec_from_code RULE-5, PROOF-5, their two tests and the spec_from_code_tag_problems helper.
- The audit skill's `trust: remote` sentence, the old gate and ending lines, the queue row and its next-step table.
- The [level: passed] tags in ai_audit (3), mutation (1), skill_audit (1), skill_spec (1) and skill_spec_from_code (1).

### Looked at

Nothing visual in this lane. All changes are Python, markdown skills, references, specs and tests. Skill line counts against their ceilings: audit 105/105, spec 165/210, spec-from-code 108/130.

## L5 signing

Acceptance passed in the lane: False. Commits: eae179fe0 feat(signatures): what a signature is made over, format 11, the walk and the tag; 95b7ff4c8 feat(skill_sign): the walk, the key and the version in the sign skill

### Waits on other lanes

- dev/test_signatures.py::TestAnyBranch::test_a_signature_on_a_side_branch_counts_there, and all 11 failures and errors in dev/test_tag.py (TestTheTag x5, TestNoTag x4, TestThePackage x2) | lane: L1 core | needs: states.rule_cells (through _binds) and payload's hand_checked must call signatures.is_current(signature, entry) with an entry that carries applies_to, code_hash and machines, meaning the full payload rule entry. Today payload._rule_entry passes rule_cells an `inp` holding only rule_hash, proof_hash, test_hash and audit_hash, so signed_hash(inp) never matches and every signed cell reads stale or unsigned. hand_checked must also need no note (decision 84), and `stale` must go. With a stand-in for exactly this, all 110 owned tests pass.
- dev/test_tag.py tag-writing tests (package write_for_tag) | lane: L6 package | needs: package.write_for_tag and version_name must accept sign.tag_name returning None. Tagging works in my tests only because tag_if_met checks the version first. Package state and not_for_approval are no longer asserted in my tests.

### Contradictions and calls the lane did not make

- WHAT: The plan (L5, decisions 67 and 77) says signatures RULE-22 is deleted. RULE-22 is the rule that `--help` exits 0 and an unknown option exits 2, which has nothing to do with those decisions. The rule on who may sign is RULE-21.
  DECISIONS: 67, 77
  LEFT AS: Kept RULE-22 with its tag removed. Kept RULE-21, rewritten, with its proof cut to one case: anyone with a key signs. Options: delete RULE-21 instead, or keep both as done.
- WHAT: The plan says RULE-23 is rewritten. Its text (a signature counts on whatever commit carries it, on a side branch at the gate signed) is still true under the gpgsig check.
  DECISIONS: 67, 77
  LEFT AS: Left the RULE-23 text unchanged.
- WHAT: The exit table in 2.6 gives sign.py exit 1 only for no key or a commit not made. It gives no line or code for naming a rule no spec has, or for a bare feature or `--all` with nothing waiting.
  DECISIONS: 2.6 exit codes
  LEFT AS: Kept today's line `sign: nothing here needs a signature. Run purlin:status to see what blocks the gate.` and exit 1 for both. Options: exit 0 with `Nothing is waiting for someone to test by hand or to sign.` and the ending (a closed walk), or exit 2 for a named rule that does not exist.

### Departures

- I built write_signature with a new shape: `(project_root, entry, signer_email, evidence_path=None, gate=None, note=None, signer_name=None, key=None)`. The contract leaves its arguments open. The frozen helper `dev/sign_project.sign_one` still calls the old positional shape. No test calls it any more; step R should delete it.
- signature_path takes `(project_root, feature, rule, signed_hash, slug)`.
- tag_if_met prints exactly the rows of section 2.6. While work is left it prints the summary ending. When it tags, it prints the package line, `Tagged signed/<v> at <sha7>.` and the RELEASE line. For the refusals it prints the refusal line.
- The walk ends like this:
  - At `signed` it ends on what tag_if_met printed, so its last line is always the ending's last line or a refusal that names a command.
  - Below `signed` it prints summary.ending of a freshly built payload.
- Named-rule signing and `--all` also end on the summary ending, after the `Signed ... with the key ending ...` line and the list of rules. The plan says this only of the walk.
- The walk's stop header is now `<feature> <RULE-N>   to sign` or `to test by hand`, taken from the kind name. The contract gives no header; the old one showed the level and the queue need.
- The walk's close keeps `Walked ...` and `Commits: <sha7>`, and adds the Signed line. The `→ Run: purlin:build` and `→ Run: purlin:sign` lines are gone, per decision 79.
- signing_configured needs `gpg.format` to be `ssh` as well as a readable SSH key, because `git commit -S` needs both.
- RULE-51 (the tag half) and RULE-52 (the out-of-date names) are deleted. Contract 2.6 makes work left print the summary ending, which covers them through `no_scope` and `to_test`.
- RULE-50 is rewritten to what the signature records: email, name and key. Decision 77 contradicts its old text about the machine and os.
- skill_sign has one rule more than the plan lists: RULE-10, for the key offer of decision 77.
- My tests write evidence with a helper of their own. It uses the reader's SCHEMA constant and adds machine and hostname. The frozen `Project.evidence` hard-codes `purlin-evidence/1`, which L2 makes unreadable.
- My tests set up keys without an allowed-signers file. The allowed-signers setup lives in the frozen dev/sign_project.py (signing_key, ci_signing_key), so I could not delete it there.
- A named rule no spec has, and a bare feature or `--all` with nothing waiting, keep today's line and exit 1. See contradictions.

### For integration

- **L1 must pass the full rule entry to signatures.is_current.** That means applies_to, code_hash and machines, in states._binds and in payload's hand_checked. Without it every signature reads unsigned after this merge. The stand-in I verified with is in scratch/phase1/signing/standin.py: it adds those three keys to the rule_cells input, and computes hand_checked after the entry is built, with no note needed.
- **L2's evidence schema breaks the frozen fixtures.** dev/sign_project.py (frozen) writes evidence as `purlin-evidence/1` in Project._read_evidence. After L2 moves to `/2`, every test using Project.evidence or Project.audit on a fresh file (test_export, test_ai_audit, test_backing_tests, test_failing, test_report_refresh) reads no evidence. Integration or R must switch it to purlin_evidence.SCHEMA.
- **The frozen fixtures also assume levels.** The `signed_project`, `_signed_project` and `tagged` fixtures in dev/sign_project.py assume RULE-1 is marked `[level: passed]`, audit only RULE-2, and use allowed-signers and `commit.gpgsign true`. After L1 and L13 they cannot reach a tag; test_export depends on them.
- **Step R deletes these names.** All are still in my files or the frozen helper for other lanes:
  - sign.triple_for (test_export)
  - signatures.triple_hash (ai_audit.py, dev/test_run_script.py, dev/mcp_project.py)
  - signatures.commit_is_signed (package._signatures)
  - sign.queued (named for the queue; dev/sign_project.sign_the_queue calls it; rename both)
  - dev/sign_project.sign_one (broken shape, now unused)
  - signing_key and ci_signing_key allowed-signers setup
- **sign.SIGNING_SETUP is now two lines.** scaffold.print_signed (L8 deletes it) still reads it, and test_init_scaffold `test_no_gate_asks_who_may_sign` expects `git config commit.gpgsign true`.
- **`--batch` is now `--all`.** Update test_report_refresh (L10), dev/init_e2e_walk.sh (L8) and references/purlin_commands.md (L12).
- **Shell suites.** dev/test_e2e_build_changeset.sh (L11) still expects `Queue: 0 rules...` and `Run: git push origin signed/`. The walk now prints `Nothing is waiting for someone to test by hand or to sign.` and `Nothing left to do. Push the tag to release it: git push origin signed/<v>`.
- **Stale references to the old signature format:**
  - references/commit_conventions.md (L12): `%G?`, `Every rule meets the gate signed.`, the settings `version` fallback, `Run: git push`.
  - references/hard_gates.md and glossary (L12).
  - docs/ (no owner this phase).
  - CLAUDE.md format table row for signature_format (read by gate_check, which L7 deletes). That file is the owner's.
- **Generated files:** rebuild the page and evidence at integration. This lane staged none.

### Deleted

- From sign.py: machine_name, has_a_ci_run, untrusted, _allowed, NO_CI_RUN, marked_below, MARKED_BELOW, _committed_only, _tied_only, names_no_files, NAMES_NO_FILES, NO_TAG_NO_FILES, out_of_date, NO_TAG_OUT_OF_DATE, short_of_the_gate, NO_TAG_SHORT, PUSH_THE_TAG, ARROW, in_queue, _gate_is_too_low, signing_help, opening_line (it was the queue line), the `--batch` option, the `signed/unversioned` name, the settings-file version fallback, `commit.gpgsign true` from SIGNING_SETUP, and the platform, evidence, board and states imports.
- From signatures.py: _project_gate (the gate dependence of counts) and BOUND_FIELDS.
- From the signature format: the triple, level, machine and os fields.

### Looked at

Nothing visual was changed by this lane.

## L6 package

Acceptance passed in the lane: True. Commits: 56ebc9105 feat(package): package format 3, finished or not finished, with the steps and what is left; 8b5fe3c53 feat(skill_export): the states finished and not finished, and a next step for each

### Waits on other lanes

- dev/test_export.py::TestTheFile::test_with_no_version_it_writes_nothing_and_says_how_to_name_one (package PROOF-21) | lane: L5 signing | needs: sign.tag_name to return None when the project states no version (contract 2.7). Today it returns 'signed/unversioned', so the export writes unversioned.json and exits 0. package.version_name treats a None from tag_name as no version, and the command then prints the No version line and exits 1.
- dev/test_export.py::TestTheContent::test_one_rule_carries_who_signed_it_and_with_which_key (package PROOF-27) | lane: L5 signing | needs: Signature format 11 files that carry signer_name (git user.name), key_fingerprint (SHA256:<unpadded base64>) and applies_to. Today's signature files have none of these, so the package reads null.
- dev/test_export.py::TestTheContent::test_one_rule_carries_what_its_signature_locked (package PROOF-28) | lane: L5 signing | needs: Signature format 11 files that carry machines, code_hash and signed_hash (signatures.signed_hash of the rule entry at signing). Today they are absent, so machines reads {} and signed_hash and code_hash read null.
- dev/test_signatures.py::TestTheTag::test_sign_commits_the_package_and_tags_that_commit and ::test_the_same_project_at_signed_gets_the_tag_and_the_package (L5's own tests, and signatures PROOF-78) | lane: L5 signing | needs: L5 rewrites these two tests to contract 2.5. The package the tag carries reads state 'finished' and has no not_for_approval key. Today they assert ('signed', False) and state == 'signed'.

### Contradictions and calls the lane did not make

- WHAT: The refusal reason `write_for_tag` returns when the committed evidence is not finished. sign.py prints it as `No tag: the evidence package was not committed: <why>.`, and neither the plan nor the interfaces file gives new words for it.
  DECISIONS: Options: (a) keep it; (b) the lines of the committed package's `left`, joined; (c) `the committed evidence leaves work to do: run purlin:status`. Note that `short of the gate` is retired wording. The integration sweep does not catch it, because it greps only `meet(s) the gate`.
  LEFT AS: Kept as today: `the committed evidence reads %d of %d rules short of the gate`. The count is the rules with a non-null `left`, out of every rule the package lists. It only shows when the committed evidence is behind the working tree, which L5's `No tag: <feature> has results that are not committed` refusal should catch first.
- WHAT: The type of `signed_commit` in a signature entry. Contract 2.5 names the field but gives no type.
  DECISIONS: The alternative is the sha of the commit that carries the signature. The bool follows decision 67 ('checks that a signature is present and looks no further') and takes the place of `commit_verifies`.
  LEFT AS: A bool: whether the commit carrying the signature file is signed, taken from `signatures.counts(...)[0]`. package_format.md states it that way.
- WHAT: What `left` says in a package that is not finished depends on the machine that exports it. The payload decides between `to_test` and `to_test_remote` by `here_os`, so the same unfinished commit exported on macOS and on Windows can give different bytes. A finished package, which is every package a tag carries, is unaffected.
  DECISIONS: (a) Accept it: RULE-8's same-bytes promise is proven for the tag, where `left` is empty. (b) Have the package recompute `left` with a fixed system. That is a contract change, owned by L1/summary.
  LEFT AS: The payload's `left` is copied as the contract says.
- WHAT: Plan item 'the tag and level lines go' for the export skill is ambiguous: it could mean the spec's lines or the skill's lines.
  DECISIONS: If the owner wants the skill to say that the package the tag carries reads `finished`, one sentence and one RULE-4 clause would add it.
  LEFT AS: Both are applied. The skill's paragraph about `purlin:sign` writing a `signed` package is removed. The skill_export spec loses its RULE-4 tag clause and its `[level: passed]`. Neither the skill nor its spec now says that `purlin:sign` writes the package the tag carries. The `left` line `the version to tag: purlin:sign` points the reader there.

### Departures

1. The `to_tag` line is left out of the package in two cases, not one. The contract says "leaving out to_tag when writing for the tag". The package also leaves it out when it is read at the commit the tag `signed/<version>` names: the same `_tag_names_commit` test the old `signed` state used. Without this, a second clone at the tag would read `not finished` and give bytes different from the tagged package, which breaks package RULE-8 (PROOF-14). The reason is how the payload finds the tag: it reads the checkout at the evidence commit, which is the parent of the tagged commit, so it sees no tag on HEAD.

2. Each signature is compared with the payload entry of the feature it applies to. The lookup is keyed on owner, rule id and `applies_to`, falling back to the owner when the signature names none. This lists an anchor rule's signature for each consumer (decision 76). Today every signature falls back to the owner.

3. `signed_commit` is the first value of `signatures.counts(tree, signature)`. Today that is the %G? check at the gate `signed`, and after L5 it is the gpgsig check. `commit_is_signed` is no longer called from package.py.

4. `rules` is copied from the payload's `summary.rules`, `steps` from `summary.steps` and `left` from `payload.left`, all as P0b built them.

5. The tests no longer use the frozen `signed` and `tagged` fixtures of dev/sign_project.py, because their spec marks RULE-1 `[level: passed]` and so behaves differently before and after L1. dev/test_export.py builds its own projects instead:
   - the spec is `EVERY_RULE_SIGNED`, both rules are audited, and a VERSION file is written;
   - after writing, every evidence file is stamped with the reader's own `evidence.SCHEMA` and each section with `machine` and `hostname`, so the files hold after L2's schema bump;
   - both rules are signed with `sign.sign_and_commit`, not `sign_the_queue`, which reads the payload's `queue`;
   - the tag is made by `package.write_for_tag` then `git tag -s`, not by `sign.tag_if_met`.
   The package's behaviour is tested apart from L5's tag logic.

6. The export skill's closing table gains a `No version` row (`→ Run: purlin:export --release <version>`). Its `not finished` row reads `→ Run: <the command of the first line of left>`, following decision 79: "the first line of Left to do is the next step".

7. The skill grows from 81 to 83 lines; its ceiling is 90.

### For integration

1. After L5 merges, rerun `dev/test_export.py` whole. PROOF-21, PROOF-27 and PROOF-28 should pass with nothing else changed. L5 must also rewrite its two `dev/test_signatures.py` TestTheTag tests and signatures PROOF-78 to read state `finished` with no `not_for_approval`.

2. sign.py keeps calling `package.write_for_tag(project_root, release)`, which still returns `(rel, None)` or `(None, why)`. It refuses when the committed package is `not finished`. `build()` now raises `package.NoVersion` (a PackageError) when `sign.tag_name` returns None.

3. The frozen `dev/sign_project.py` writes evidence with schema `purlin-evidence/1` and no `machine`. After L2 the reader ignores those files, which breaks every lane's tests that use `Project.evidence` unchanged. dev/test_export.py is protected: it stamps each evidence file with `evidence.SCHEMA` and adds `machine` and `hostname` to each section. The shared helper needs fixing at integration.

4. Stale package words in files other lanes own, for L12 or the docs phase:
   - docs/regulated-workflow.md lines 50 and 76 (a state other than `signed`, not for approval);
   - references/glossary.md lines 75 to 82;
   - references/purlin_commands.md line 112 and agents/purlin.md line 56 ("every rule meeting the gate");
   - references/hard_gates.md around line 202;
   - specs/review/signatures.md PROOF-78 (L5).

5. Nothing generated was staged. `.purlin/evidence/local/package.json` and `skill_export.json` need the integration rerun.

6. The package no longer reads `gate.trust`, `level`, `level_marked`, `meets_gate` or `signatures.commit_is_signed`, so step R can delete them without touching package.py.

### Deleted

- From scripts/export/package.py:
  - the states `signed`, `gate <gate> met` and `work in progress` (`SIGNED`, `IN_PROGRESS`);
  - `NOT_FOR_APPROVAL` and the `Not for approval.` suffix;
  - the top-level keys `not_for_approval`, `rules_meeting_gate`, `rules_short_of_gate` and `trust`;
  - each rule's `level`, `level_marked` and `meets_gate`;
  - from each signature entry `machine`, `os`, `level` and `commit_verifies`, and `triple` from `locked`.
- The version fallback to `unversioned`: the package now takes whatever `sign.tag_name` gives.
- The matching fields and state tables in package_format.md.
- In the export skill and its spec: the three-state table, the "Only `purlin:sign` writes a package whose state is `signed`" paragraph, and the `[level: passed]` tag of skill_export RULE-6.

### Looked at

Nothing visual in this lane: no page, dashboard or screenshot was changed.

## L7 runner

Acceptance passed in the lane: False. Commits: 87ee1002c feat(host): the runner runs only the systems the rules name, and its job ends on the test step; ec4ac61de fix(host): the Azure DevOps run reads its whole branch, and a project with ci: none pushes nothing

### Waits on other lanes

- dev/test_consumer_ci.py::test_the_config_is_the_shape_this_release_reads (host PROOF-20, RULE-20) | lane: L8 init | needs: templates/config.json to drop trust (contract 2.7 keys: version, gate, mutation_engine, min_strength, audit_parallel, tests, ci). The fixture already has exactly those keys in that order.
- dev/test_init_scaffold.py: the 22 tests named in acceptance_output | lane: L8 init | needs: The workflow tests rewritten to the contract. A workflow now comes only from an @env tag for another system, never from trust remote. The matrix holds only the named systems, so no tag means no job and a windows tag alone means windows-latest alone. The last step is Run the tests, not Check the gate. The unknown-host line is section 2.6's. The spec rewrites follow: scaffold RULE-42/PROOF-42 (gate check step), PROOF-13 (trust reason), PROOF-44 (host line).
- dev/test_init_update.py::test_purlin_yml_carries_this_releases_triggers_and_gate_check | lane: L9 upgrade | needs: The assertion on scripts/ci/gate_check.py" --check --verify dropped, and update PROOF-15's 'a step named Check the gate' rewritten; the workflow now ends on Run the tests.
- dev/init_e2e_walk.sh (shell suite, proven at integration) | lane: L8 init | needs: Its gate_check.py steps (lines 18-51) and its provenance.committed_by call (lines 226-227) removed; both modules are deleted.

### Contradictions and calls the lane did not make

- WHAT: Decision 77 and the L7 entry say 'ci.py and host.py give purlin_run the runner's kind for the machine field'. Neither section 2 nor phase1-interfaces.md names the function or its shape, and L3's write_sections is the caller.
  DECISIONS: 77; plan L7 and L3 entries; section 2.5 (machine = 'remote runner, <Windows|macOS|Linux/Unix>' for ci)
  LEFT AS: Not built. ci.py and host.py are unchanged here. Options: (a) host.runner_machine() returning 'remote runner, ' + evidence.os_word(evidence.host_os()), which L3 calls for source ci; (b) L3 composes it inside purlin_run from evidence.os_word, and ci.py/host.py give nothing. Integration must check that L3 did not call a name that does not exist.
- WHAT: host.no_commit_line still prints 'Tag run: nothing is written. This run reruns the tests and checks the evidence already committed to <ref>.' Since decision 75 ('On a pushed signed tag the runner runs the tests and nothing else') and the removal of the check step, the tag run checks nothing, so the second sentence is untrue. run_script RULE-47/PROOF-68 and dev/test_run_script.py (L3) quote the whole line, and no contract gives new wording.
  DECISIONS: 75, 83.1; section 2.6 does not list this line
  LEFT AS: The text is as it was today. An option is 'Tag run: nothing is written. This run reruns the tests on <ref>.', with L3's RULE-47, PROOF-68 and test changed to the same words.
- WHAT: workflow.NO_REASON and NO_REASON_AT_PASSED still read 'every proof (test) runs on this operating system and you trust this machine, so nothing has to run remotely'. Trust is gone (decision 75), so 'you trust this machine' is untrue. L8's dev/test_init_scaffold.py line 780, scaffold PROOF-13 and PROOF-49, skills/init/SKILL.md line 161 and docs/running-and-evidence.md line 310 quote it, and no contract gives new wording.
  DECISIONS: 75; section 2.6 gives no no-runner line
  LEFT AS: The text is as it was today. An option is 'every proof runs on this operating system, so nothing has to run remotely' ('every test' at passed), with L8's quotes changed to match.
- WHAT: The runner reason names the system with the stored spec word ('tagged @env for windows'). Section 2.8 says a person reads Windows, macOS or Linux/Unix. The sentence names the @env tag as typed, and L8's scaffold proofs quote <os>.
  DECISIONS: 65, 79; section 2.8
  LEFT AS: The stored word is kept, since it is the tag as typed in the spec. Integration or the owner may want the display word.

### Departures

- Plan: "host PROOF-8 gets the run-branch case". PROOF-8 is not extended. The case is the new PROOF-52 (RULE-8), because a proof this lane writes holds one case. Its wording is the one dev/plans/proofs-rewritten.md line 140 gives. The test of about 15 lines was written new in dev/test_host.py (test_the_azure_push_names_the_whole_run_branch), not taken from history.
- Plan: "host RULE-31 and RULE-28 are reworded". RULE-28 is reworded. RULE-31 is unchanged: none of this lane's changes made anything in it untrue, and the plan does not say what the new wording should be.
- The unknown-host line (workflow.UNKNOWN_HOST) is now section 2.6's text. No host rule proves it: init prints it, and L8's scaffold RULE-44 is the rule that entry names for 'the host line'.
- remote.run_remote reads ci from .purlin/config.json itself, through config_engine.resolve_config. It does not read the cfg purlin_run passes, which it never used. The refusal comes first, before any git process.
- The workflow.wanted signature keeps its trust parameter, unread, because scaffold.py and update.py still pass it. Step R deletes it.
- Added PROOF-47 so the Azure DevOps pipeline template has a proof in host. Its only other coverage was gate_check's scope and L8's tests.
- dev/manual/check_azure_remote.py gains one check, run once the pipeline completes: the runner's commit is on run/<...> and no branch named after the ref's last part was created. Decision 65 says the run-branch fix is 'confirmed on the work machine', and this check is how.
- The commits were split by building the first commit's versions of host.md, test_host.py, workflow.py, host.py and README.md in the index (git hash-object and update-index). Each commit was checked in an exported tree: the four owned test files pass at the first commit except the L8-waiting config test.

### For integration

- Rebuild and commit the evidence once. The run removes .purlin/evidence/local/gate_check.json (no spec defines gate_check any more).
- These now-stale lines are in files this lane does not own:
  - CLAUDE.md lines 49 and 51 name scripts/ci/gate_check.py in the format table. That file is the owner's.
  - references/glossary.md line 93 ('gate check') and references/hard_gates.md lines 127 and 141 (gate_check --check --verify, ci/ provenance) belong to L12.
  - references/drift_criteria.md lines 106, 108 and 112 (gate_check.py as a reader; trust read by workflow.py) belong to L11.
  - skills/init/SKILL.md line 101 (the gate check step) and line 161 (NO_REASON) belong to L8.
  - docs/running-and-evidence.md lines 310, 348 and 371 belong to the docs phase.
  - specs/init/scaffold.md RULE-42, PROOF-42 and PROOF-44 and specs/init/update.md PROOF-15 quote the Check the gate step and the old host line. They belong to L8 and L9.
- dev/mcp_project.py line 45 (frozen) still names dev/test_provenance.py in a comment. Step R or integration removes it.
- dev/sign_project.py (frozen) keeps CI_COMMITTER, CI_EMAIL, ci_signing_key and commit_as_ci. After this lane, their only readers are test_signatures, test_tag and dev/init_e2e_walk.sh. Step R checks whether they are still read.
- Step R deletes the trust parameter of workflow.wanted with its callers in scaffold.py and update.py; wanted already ignores it.
- Shell suite: dev/init_e2e_walk.sh calls scripts/ci/gate_check.py and scripts/mcp/purlin/provenance.py, both deleted. It stays red until L8 rewrites it.
- The integration sweep for 'trust' will find workflow.NO_REASON, NO_REASON_AT_PASSED and wanted's parameter. The first two are in contradictions.
- The live Azure check waits for the work machine: python3 dev/manual/check_azure_remote.py from a clean Azure DevOps clone. It now also confirms that the runner's commit lands on run/<branch>-<sha7> and that no branch named after the ref's last part is created.

### Deleted

- Files: scripts/ci/gate_check.py (with PASS., FAIL., the result key, _ENFORCEMENT_NOTE, _provenance and verify, and so the --verify step), specs/ci/gate_check.md, dev/test_gate_check.py (with the 8 tests P0a moved in), scripts/mcp/purlin/provenance.py (with the SYSTEM_ACCESSTOKEN name it stored), dev/test_provenance.py, dev/manual/check_azure_provenance.py, and this repository's .github/workflows/purlin.yml (decision 83.7).
- In workflow.py: TRUST_REASON, TRUST_REASON_AT_PASSED, trust_reason() and DEFAULT_RUNNER (the ubuntu-latest default job).
- In host.py: ref_branch(), the second branch reader, folded into current_branch().
- The 'Check the gate' step and its comments in both workflow templates.
- trust in the consumer fixture's settings.
- The PROOF-9 tests and their helpers (ACTIONS_BOT, WEB_FLOW_EMAIL, AZURE_BUILD, _commit_by_hand) in dev/test_host.py.

### Looked at

Nothing visual was changed.

## L8 init

Acceptance passed in the lane: True. Commits: 8c2c784e0 feat(scaffold): setup asks the gate, and mutation only at strong and signed; abd42ffc8 feat(skill_init): the init skill names two questions and seven keys

### Waits on other lanes

- dev/test_init_scaffold.py::TestTheWorkflow::test_windows_and_macos_tags_are_the_matrix (scaffold PROOF-15) and test_one_foreign_system_is_the_whole_matrix (PROOF-72) | lane: L7 runner | needs: workflow.runners_for gives one job per system the @env tags name and no ubuntu-latest of its own (decision 83 item 2). Today the matrix is `ubuntu-latest, ...`
- dev/test_init_scaffold.py::TestTheWorkflow::test_the_last_step_is_the_test_run (PROOF-74) and test_the_azure_pipeline_ends_on_the_test_run (PROOF-76) | lane: L7 runner | needs: templates/purlin.yml and templates/purlin.azure-pipelines.yml lose the `Check the gate` step and gate_check.py, so each file ends on `scripts/run/purlin_run.py" --all --ci`
- dev/test_init_scaffold.py::TestTheWorkflow::test_a_missing_prerequisite_is_named_and_nothing_is_written (PROOF-44) and TestTheHost::test_a_host_that_is_neither_says_what_still_works (PROOF-69) | lane: L7 runner | needs: workflow.UNKNOWN_HOST becomes the section 2.6 line `The origin remote is neither GitHub nor Azure DevOps. Everything on this machine works with any host; only purlin:test --remote needs one of those two.` scaffold.py prints workflow_module.UNKNOWN_HOST and does not copy the string.
- dev/test_consumer_ci.py::test_the_config_is_the_shape_this_release_reads (host PROOF-20, an L7 file) | lane: L7 runner | needs: dev/fixtures/consumer-ci/.purlin/config.json drops `trust`, so its keys match templates/config.json, which now has seven keys
- dev/test_init_scaffold.py::TestTheFlags::test_update_hands_the_project_to_the_upgrade (PROOF-33) | lane: L9 upgrade | needs: update._detect_config drops the clause `config.get('trust') not in gate.TRUST_VALUES` and accepts `ci: none`. Until then a project init just set up reads as pending, and this repository's own status shows `→ Run: purlin:init --update`, because its .purlin/config.json no longer has `trust`.
- dev/test_init_scaffold.py::test_a_go_module_runs_through_the_command_its_first_run_suggests (PROOF-52) | lane: L3 run | needs: a run with an empty `tests` setting prints `Suggested entry: <one-line JSON>` (section 2.6). Today it prints `No test suite: ...` and no suggestion.
- dev/test_init_e2e_gates.sh (scaffold PROOF-36, 90, 91, 92, 93) through dev/init_e2e_walk.sh gates | lane: L3 run, L2 evidence, L5 signing, L9 upgrade | needs: L3: the `Suggested entry:` line, and `--commit` making `purlin: specs, tests and settings for greeting` and then `purlin: evidence at <sha7 of the first>`. L2: commit_work/commit_local. L5: `sign.py --all`, `Signed 1 rule as jane@acme.com with the key ending ...<last 4>.`, a tag written with no commit.gpgsign set, and `Nothing left to do. Push the tag to release it: git push origin signed/0.1.0`. L9: no pending update on a freshly set-up project.
- dev/test_init_e2e_wiring.sh (scaffold PROOF-37, 94, 95, 96, 97) through dev/init_e2e_walk.sh wiring | lane: L3 run | needs: the first test run's `Suggested entry:` line naming pytest, vitest or dotnet. The C# nothing-added check (PROOF-96) and the marketplace check (PROOF-97) already pass.

### Contradictions and calls the lane did not make

- WHAT: The plan says scaffold RULE-32 (`--add <framework>`) moves to run_script, with L3 adding it there and this lane deleting it. But `--add` is a flag of scaffold.py, the L3 entry says nothing about it, and section 2.6 lists only `--dry-run` as gone from scaffold.py.
  DECISIONS: Decision 70 (how the tests run is settled at the first test run) against the plan's L8 entry (RULE-32 moves to run_script) and section 2.6 (scaffold.py: as today, --dry-run gone).
  LEFT AS: `--add` kept in scaffold.py, the SKILL.md flag table and skill_init RULE-2. RULE-32 rewritten because a new project's `tests` is empty: appends after the entries already there, once. Options: (a) keep `--add` in init as now; (b) delete `--add`, RULE-32, PROOF-32/98 and the flag row, and let the first test run's suggestion be the only way to set `tests` besides the purlin_config tool.
- WHAT: Two summary notes scaffold prints when it writes a workflow become false once L7 applies decision 83: `  the matrix is %s: ubuntu-latest always, then the @env tags in specs/.` and `  it runs on a push to a run/* branch and on a push of a signed/* tag, and ends with the gate check.` No replacement wording is given in section 2 or the interfaces file.
  DECISIONS: Decision 83 items 1 and 2 (no gate-check step; only the named systems) against the rule to write only contract strings.
  LEFT AS: Both strings left as they were in scaffold.py's write_workflow, and no test asserts them. Options: (a) `  the matrix is %s, the systems the @env tags in specs/ name.` and `  it runs on a push to a run/* branch and on a push of a signed/* tag.`; (b) delete both notes.
- WHAT: When the origin remote names neither GitHub nor Azure, the summary line still reads `Git host not read from a remote.` There is a remote; its host is simply unknown. The contract line follows it on the next line.
  DECISIONS: Decision 65 (setup's line says what still works) and section 2.6 give only the second line.
  LEFT AS: Kept `Git host not read from a remote.` for both no remote and an unknown host (PROOF-69/70 quote it). Options: (a) keep it; (b) `Git host none.` for both; (c) a separate word for an unknown host.

### Departures

1. Section 7 (decision 83) required rewriting scaffold RULE-15 and RULE-42 and their proofs, which the L8 entry did not list: only the named systems in the matrix, and no gate-check step. The tests are written to that contract and wait on L7.
2. The run's ending (RULE-34). Since P0b, status prints no `→ Next:` line, so init's next_step fell back to `→ Next: run purlin:spec to write the first spec.` even when specs existed. next_step now returns the block `purlin:status` ends on: the update line if any, the summary sentence and `Left to do`. With no spec it still prints the `→ Next: run purlin:spec ...` line. This applies decision 79 ("the first line of Left to do is the next step") to init.
3. write_config writes only the template's keys. Values come from the project's file where it has them, so a leftover `trust`, or any unknown key, is not written back. This makes "exactly seven keys" hold without naming `trust` in code. gate.RETIRED_KEYS is no longer read by scaffold.py; the name is not deleted.
4. With no framework detected at strong/signed, NO_ENGINE is filled with "this project's", the same fallback update.py already uses, in place of an empty string that printed "no engine breaks  code".
5. RULE-9 was not deleted outright. Its framework-needs half (jest-junit, sqlite3) moves to run_script per the plan: print_needs is deleted here. Its Stryker half is printed by scaffold's write_engine, so it stays as scaffold RULE-9.
6. RULE-32 and `--add` stay in init; see contradictions. The rule was rewritten because `tests` is now empty after setup.
7. Detection is still used, for the mutation engine only: frameworks_carried() = detect_frameworks(root) plus the names of existing suites. frameworks.entries_for is no longer called by scaffold. entry_for and ENTRIES are still called, by --add.
8. PROOF-62, 63 and 22 name `.purlin/report-data.js` as a changed or ignored file. When a spec exists, the status call at the end of init refreshes the dashboard data, and those three proofs now need a spec, because a workflow now needs an @env-tagged proof.
9. The `Gate %s. Suites %s. Git host %s.` line is kept as it was. It now reads `Suites none` on a new project.
10. `trust_question(gate)` stays for R, since update.py calls it. The TRUST_* constants are deleted, so it holds the two strings inline.
11. The workflow.wanted call passes None for the `trust` parameter by position, so it works both before and after L7; R removes the argument.

### For integration

- Prove the shell suites dev/test_init_e2e_gates.sh and dev/test_init_e2e_wiring.sh after L2, L3, L5 and L9 merge; the walk in dev/init_e2e_walk.sh is written to their contract strings. The walk expects:
  - the first `purlin_run.py --test` to print `Suggested entry: {...}`
  - `--test --commit` to leave HEAD~1 `purlin: specs, tests and settings for greeting` and HEAD `purlin: evidence at <sha7 of HEAD~1>`
  - the ending lines `Nothing left to do.`, `  1 rule to audit: purlin:audit` and `  1 rule to sign: purlin:sign`
  - `Tag run: nothing is written.`
  - `sign.py greeting RULE-1` printing `Signed 1 rule as jane@acme.com with the key ending ...<last 4 of ssh-keygen -l fingerprint>.` and a commit with a gpgsig header, with no commit.gpgsign and no allowed-signers configured
  - `sign.py --all` writing `signed/0.1.0` from a VERSION file and printing `Nothing left to do. Push the tag to release it: git push origin signed/0.1.0`
  If L5's `--all` does not tag when nothing is left to sign, the walk's last step has to change to what does.
- Rerun dev/test_init_scaffold.py after L7 (PROOF-15, 72, 74, 76, 44, 69), L9 (PROOF-33) and L3 (PROOF-52).
- Names left for step R: `scaffold.trust_question` (still called by update.py); the None passed as `trust` to `workflow.wanted` in scaffold.py; `gate.RETIRED_KEYS`, `gate.TRUST_VALUES`/`DEFAULT_TRUST` and `frameworks.entries_for`, which scaffold no longer reads; `frameworks.NEEDS`, which scaffold no longer reads (print_needs deleted).
- Stale text in files other lanes own:
  - references/purlin_commands.md (L12): the init row "Four questions at most"; "The gate, the test command, mutation testing and trust"; `purlin:init --update --dry-run`; "`specs/_anchors/`" and "the trust answer was no" in the what-it-writes row; lines 146-152 on `--update --dry-run`.
  - templates/purlin.yml and templates/purlin.azure-pipelines.yml (L7): comments still name the trust question, `trust: remote` and "does not meet the gate".
- This repository's .purlin/config.json lost `trust`. Until L9 merges, update.pending(.) is true here and status prints `→ Run: purlin:init --update`.
- No generated file was staged, and no format file changed.

### Deleted

- scaffold.py:
  - constants and names: COMMAND_QUESTION, REPORT_QUESTION, NO_COMMAND, ASKED_FILES, TRUST_QUESTION, TRUST_LOCAL, TRUST_QUESTION_AT_PASSED, TRUST_LOCAL_AT_PASSED, TRUST_REMOTE, TRUST_REMOTE_AT_PASSED, _TRUST_WORDS
  - functions: trust_words, ask_trust, format_for, asked_suite, print_needs, signing_setup, print_signed
  - Plan.dry_run and the `--dry-run` flag, including its hand-off as `--check` to update.py
  - the creation of specs/_anchors/
  - the not-a-repository note that only a dry run could reach
- templates/config.json and this repository's .purlin/config.json: the `trust` key. The template's `ci` is now `none`.
- dev/test_init_scaffold.py: the tests of RULE-6, 7, 30 and 49, and the --update --dry-run cases.
- dev/init_e2e_walk.sh: commit_as_ci, committed_by (provenance), the allowed-signers setup, commit.gpgsign true, the gate_check.py steps, the Queue checks and expect_exit.
- skills/init/SKILL.md: the trust section, the commit-signing section and every `--dry-run` mention. The skill is now 195 lines against a ceiling of 250.

### Looked at

Nothing visual in this lane.

## L9 upgrade

Acceptance passed in the lane: True. Commits: 46329a17d feat(update): the upgrade deletes the old cache, has no rehearsal, and asks what setup asks; 52686b39b spec(update): a rule for telling a project 0.9.5 set up and nobody upgraded

### Waits on other lanes

- dev/test_init_scaffold.py::TestTheFlags::test_update_with_dry_run_asks_the_upgrade_what_is_pending and ::test_update_with_dry_run_lists_what_an_older_project_needs (scaffold PROOF-33) | lane: L8 init | needs: delete --dry-run and delegate_update's '--check' argument from scripts/init/scaffold.py, and those two tests with scaffold RULE-30 and RULE-33's second half; update.py no longer accepts --check
- dev/test_init_update.py PROOF-46 (test_the_gate_question_takes_the_answer_you_type) and every update run that asks the gate | lane: L8 init | needs: scaffold.GATE_QUESTION and scaffold.GATE_CHOICES to stay (update prints both), plus scaffold.git_host (returning github, azure or None/none), MUTATION_QUESTION, NO_ENGINE, ENGINE_NAMES, engine_for, min_strength_for, audit_parallel and EVIDENCE_README
- dev/test_init_update.py PROOF-50 (test_a_project_with_no_remote_gets_no_workflow) and PROOF-51 | lane: L7 runner | needs: workflow.NO_REMOTE to keep the words 'No git remote, so there is no runner to read this workflow', and UNKNOWN_HOST to contain 'remote is neither GitHub nor Azure DevOps' (the contract 2.6 line does); workflow.wanted to keep its positional trust parameter until R (update passes None)

### Contradictions and calls the lane did not make

- WHAT: When nothing is pending, update.py ends on 'Nothing is pending: this project is at <version>.' (or the scope advice) and names no next command. Decision 65 says every ending of a command names a command to run next. Old RULE-20 said the last line always names the next step, but only the apply path did it.
  DECISIONS: 65 (every ending names a command) against 76 (a finished state may say Nothing left to do and name no command; that decision is written for the summary, not the upgrade)
  LEFT AS: Behaviour unchanged. RULE-20 is reworded to say what the code does: a run that had migrations to ask about ends on '→ Next: run purlin:status to see where every rule stands.' or '→ Next: run purlin:init --update again for <ids>.' Options: (a) add the existing '→ Next: run purlin:status to see where every rule stands.' line after 'Nothing is pending'; (b) keep it as is, since nothing is left to do for the upgrade.
- WHAT: Neither the plan nor the interfaces file gives the reworded text of RULE-11. The only candidate change was 'trust', which 0.9.5 never wrote, and a test that it is not written back would be a test that a removed thing is absent.
  DECISIONS: 44 (clean release) and plan L9 'RULE-10 and RULE-11 are rewritten'
  LEFT AS: RULE-11 reworded to 'The rewritten config carries no key this release does not read: the dashboard switch 0.9.5 wrote is not written back, whether it was on or off'. Its proof is split into PROOF-11 and PROOF-44. Nothing about trust was added.

### Departures

1. RULE-15, PROOF-15 and update's printed line 'it runs on a push to a run/* branch and on a push of a signed/* tag, and ends with the gate check' no longer mention the gate check. The test no longer asserts the 'Check the gate' step or 'gate_check.py --check --verify'. The plan does not list this for L9, but section 7 item 1 deletes the step from the workflow templates (L7), and the old test would fail once L7 merges. Because PROOF-15 was rewritten, it was split into PROOF-15, 49, 50 and 51.
2. update's line 'wrote <file> for <host>, covering <systems>' now uses evidence.os_word (Windows, macOS, Linux/Unix), per contract 2.8. Before, it printed the raw tags.
3. ci keeps a valid value the project already named (github, azure or none). Otherwise it is scaffold.git_host(root) or 'none'. main kept any old ci value, and otherwise defaulted to github.
4. The pending list printed before the questions no longer ends with '→ Run: purlin:init --update'. That line belonged to --check (deleted RULE-3), and it made no sense inside the run it names.
5. _ask_gate prints scaffold.GATE_QUESTION and scaffold.GATE_CHOICES. The plan names only GATE_QUESTION, but update's deleted copy also carried the choices.
6. The old cache is detected when the folder exists on disk, not only when it is tracked. The fixture's cache is ignored, and 'deletes it outright' covers both cases. It is one pending entry, '.purlin/cache/', and the untrack uses 'git rm -r'.
7. The committed-cache test was not missing. It asserted the folder stayed on disk; it now asserts the folder is gone (PROOF-36), and a new test covers the ignored cache (PROOF-35).
8. PROOF-39 (keys this release stopped reading) now names spec_dir and pre_push explicitly instead of reading gate.RETIRED_KEYS, so it does not depend on L1's gate.py.
9. The source check in the PROOF-11 test ("'report'" appears once in update.py, inside SET_UP_BY_095_KEYS) is kept. The rewritten proof no longer claims it.

### For integration

- L8 must drop scaffold's '--dry-run' and the '--check' it passes to update.main. Until then scaffold PROOF-33's two dry-run tests fail with 'update.py: error: unrecognized arguments: --check'.
- Step R: update.py calls flow.wanted(tags, None, evidence_module.host_os(), gate). R removes the None argument when it removes the trust parameter. update.py no longer reads gate.TRUST_VALUES, gate.DEFAULT_TRUST, scaffold.trust_question or gate.resolve_gate. It still reads gate.GATES, gate.RETIRED_KEYS and frameworks.entries_for / detect_frameworks / entry_for, so R must keep entries_for.
- L3 calls update.set_up_by_095 (unchanged here, now under RULE-32).
- Owner-lane text now stale about update's --check / --dry-run, which I did not touch:
  - references/purlin_commands.md lines 96 and 150 to 153 ('purlin:init --update --dry-run ... exits 1', 'ends with → Run: purlin:init --update') (L12).
  - skills/init/SKILL.md line 239 (L8).
  - scripts/init/scaffold.py lines 5, 554 and 560 to 568 (L8).
- Shell suites: none owned.
- Generated files: none staged. Integration's rerun will refresh .purlin/evidence/local/update.json.
- At integration, check that update.pending('.') is empty for this repository once L8 removes 'trust' from .purlin/config.json. The config detector no longer reads trust, and this repository has no .purlin/cache/.

### Deleted

- From scripts/init/update.py: the --check flag and EXIT_PENDING (exit 1); _ask_trust; update's own GATE_QUESTION copy; _host (replaced by _ci over scaffold.git_host); the trust clause of _detect_config; the trust key written by _apply_config; the gate.resolve_gate call; the '→ Run: purlin:init --update' line in _print_pending; the '..., and ends with the gate check' wording.
- From specs/init/update.md: RULE-3 and PROOF-3.
- From dev/test_init_update.py: the three --check tests of PROOF-3.

### Looked at

Nothing visual changed in this lane.

## L10 dashboard

Acceptance passed in the lane: True. Commits: fd4598529 test(purlin_report): the sample payloads ask every rule what the gate asks; 461c4ebd5 feat(purlin_report): step boxes, Left to do and No proof replace the queue

### Waits on other lanes

- dev/test_report_refresh.py::test_a_signature_writes_the_data_file (purlin_report PROOF-59) | lane: L5 signing | needs: sign.py to take `--all` in place of `--batch` (decision 78). Today it exits 2.
- dev/test_states.py::TestTheFixturesAreTheContract::test_the_fixtures_carry_exactly_the_keys_the_builder_writes (states PROOF-82) | lane: L1 core | needs: the signed cell to drop `machine` and `os` and gain `signer_name` and `key_fingerprint` (RULE-47), and the payload's `gate` to lose `trust`. The fixtures already carry this final shape.
- dev/test_states.py::TestTheFixturesAreTheContract::test_the_fixtures_carry_exactly_the_keys_the_builder_writes (states PROOF-82) | lane: L2 evidence | needs: evidence sections to carry `machine`, so the builder writes a non-empty `rules[].machines`. The fixtures now carry machines per system, for example `remote runner, Windows`.
- dev/test_states.py::TestTheFixturesAreTheContract::test_every_fixture_has_the_key_set_the_builder_writes (states PROOF-96, PROOF-29) | lane: L1 core | needs: `gate.resolve_gate` to stop returning `trust` (decision 75), and the signed cell's final keys.
- dev/test_states.py::TestStatusTable::test_the_board_cells_read_the_way_the_fixtures_say (states PROOF-58) | lane: L1 core | needs: the test's expectations rewritten for decision 73. board.py's cells read `<n> of <rules>`, which gives login `2 of 4 · 86%` and `1 of 4` and invoice `0 of 3 · 64%` and `0 of 3` on the rewritten fixtures. The test's current expectations (`2 of 3`) assume `[level: passed]`.

### Contradictions and calls the lane did not make

- WHAT: RULE-23 now names two screenshots, and its proof checks docs/images holds no other image. docs/images/dashboard-queue.png, and the line in docs/dashboard.md that embeds it (line 182), belong to no lane in this phase, so PROOF-23 fails until someone deletes the image and that line. The other two images also still show the old board.
  DECISIONS: Decision 74 (the queue goes) and the plan's L10 entry (RULE-23 goes to two screenshots). Section 1 gives docs/ to no lane.
  LEFT AS: The capture table and the test are written to two images, and the test fails. docs/ is untouched. Options: (a) integration deletes docs/images/dashboard-queue.png and the docs/dashboard.md line, then runs dev/capture_doc_screenshots.py once the page is rebuilt; (b) the docs phase does it.
- WHAT: The contract does not give the tone of the `No proof` box, the wording of the signed panel, the hand-check explanation, or the words saying Left to do commands are typed in Claude Code.
  DECISIONS: Decisions 68, 77, 78 and 84 give the content but not the exact strings.
  LEFT AS: I chose these, and the owner may want to reword them:
- The No proof box is in the warn tone above zero and the pass tone at zero.
- The signed panel reads `Signed by <name>, <email>, on <date> <time> UTC with the key ending ...<last 4>.`, then one line per system, `On <System> the tests ran on <machine>.`
- The hand-check line reads `A hand check is you checking the rule and signing it in one act; purlin:sign asks what you saw and records it.`
- The list ends with `Type each command in Claude Code.`
- Filter order: No proof, Weak, Not audited.

### Departures

- Fixtures: "with no removed key" is read as keeping every key section 0 says step R deletes (queue, met, meets_gate, level, level_marked, stale, hand_checks, asks_*, flags.stale). Their values were recomputed: every rule's `level` is the gate, `level_marked` is null, stale is 0 or false, and the stale queue row reads `unsigned`. `gate.trust` was removed because L1 removes it, not R. The signed cell has the L1 final shape (`signer_name`, `key_fingerprint`; no `machine` or `os`). `rules[].machines` are filled in. Descriptions were added to login and invoice so RULE-52 can be shown. Fixture data I chose under decision 73:
  - regulated login RULE-3 reads `weak` (its audit found a gap);
  - regulated invoice RULE-1 reads `weak` (strength 64% under 80%);
  - team login RULE-3 reads `strong`.
- Proof splitting: sweeps across the five widths, across the three fixtures in one theme (contrast), and across each filter in turn (PROOF-46) are each written as one proof, treating the sweep as the action. The PROOF-63 family (a `passed` project shows no higher word) was 10 parametrized cases: 5 cell words × with or without proof lines. It is now 6 proofs: 5 cell words with proof lines, plus the no-proof-lines project as the fixture stands. The four other cell words without proof lines are no longer run. PROOF-66 no longer measures the queue screen, which is gone.
- Hand check command: the panel names `purlin:sign <feature> <RULE-N>` without `--note "<what you saw>"`, because decision 84 has purlin:sign ask for the note. The command is composed on the page because the queue row that carried it is gone.
- Renamed so the integration sweep does not flag them: `ageText`'s `stale` flag is now `old`, `refreshIfStale` is now `refreshIfOld`, and the filters' `level:` property is now `step:`.
- The page does not show `summary.sentence`, because decision 57 removed the headline lines above the tiles. The step boxes carry its numbers.

### For integration

- Rebuild the page with python3 dev/build_report.py and commit scripts/report/purlin-report.html. The built page is now 1055 lines and loads the schema 10 fixtures with no console error.
- Delete docs/images/dashboard-queue.png and its embed at docs/dashboard.md:182, then run python3 dev/capture_doc_screenshots.py to retake the two screenshots. Until then PROOF-23 fails.
- After L1, L2 and L5 merge, rerun dev/test_states.py (PROOF-82, PROOF-96/29, PROOF-58) and dev/test_report_refresh.py (PROOF-59):
  - PROOF-82 and PROOF-96/29 pass once the builder writes signer_name/key_fingerprint, drops machine/os and gate.trust, and fills machines from sections.
  - L1 must rewrite its PROOF-58 expectations to `2 of 4 · 86%`, `1 of 4`, `0 of 3 · 64%`, `0 of 3`.
- Step R removes the payload keys the fixtures still carry: queue, met, meets_gate, level, level_marked, stale, hand_checks, asks_*, flags.stale. When it does, it must remove them from dev/fixtures/report/*.json too (L10's files), or PROOF-82 fails.
- The dashboard no longer reads any of those keys, nor `bucket` or `flags`.
- The page reads these payload keys: summary.steps, summary.rules, left, last_line, os_words, rules[].left, rules[].machines, cells.signed.signer_name, cells.signed.key_fingerprint, features[].description.

### Deleted

- scripts/report/src/queue.js: the Queue tab, `queueRow`, `renderQueue` and the ARRIVES empty-state sentences.
- From app.js: `reached`, `bucketTone`, `levelTag`, `levelSource`, `listedRule`, `queueRowFor`, `gateChips` (the count chip and its hover), BUCKETS/BUCKET_LABELS/TILE_HOVER, `VIEW.from`, the queue screen route, the `stale` word and tone, and the stale line of the signer hover.
- From board.js: `flagCard`, `queueLines`, `staleLines`, `untestedLines`, `tileHover`.
- From filters.js: the Untested, Failing, Partial, Queue and Stale filters and `inQueue`.
- From rule.js: the Level row and the queue-driven panel logic.
- From styles.css: the flag card and queue-row (.rev) styles.
- queue.js removed from build_report.py's SCRIPT_FILES, and the queue screenshot removed from capture_doc_screenshots.py.
- Tests: the queue, stale-card, level and count-chip tests (PROOF-18, 19, 31, 34, 36, 37, 49, 52, 67, 73, 74, 78) and the `_levels_payload`, ROW_PILLS, CHIPS, list_cells and flag_cards helpers.

### Looked at

Playwright, headless, dark theme, at 1500, 1280, 1024, 768 and 390 pixels. Screens: the regulated board with login and RULE-4's proofs open, the regulated rule screen for login RULE-1, and the team board with login open.
- 1500: four boxes in one row: Passing 7 and Strong 2 in amber, Signed 1 in amber, No proof 0 in green. The Left to do panel lists six lines, each command in Courier, and ends "Type each command in Claude Code." Filters read No proof 0, Weak 4, Not audited 1. Login's description sits beneath its row and above RULE-1. The table has six columns with no sideways scroll.
- 1024 (team): three boxes, the Left to do list, and five columns that fit.
- 768: the rule screen shows labels above values, Lin and Win boxes, and the Signed panel with the name, email, key ending ...Xy4Q and one line per system.
- 390: boxes two to a row, specs as labelled-pair blocks, the description and proofs wrapping at full width, no sideways scroll.
- No value broke inside itself on any screen. The layout tests confirmed this, PROOF-75, 112 and 113 across both themes.
- Neutral text measured at least 7 to 1 in both themes on every fixture's board and rule screen, PROOF-66 and PROOF-104.

## L11 authoring

Acceptance passed in the lane: True. Commits: 3f23fad96 feat(drift): the QA view prints the lines of Left to do that wait for a person; d5455551f feat(skill_build): repair nearly right markers, leave the test command to purlin:test; d3fc63770 feat(skill_anchor): every ending names a command, and the first anchor makes the folder

### Waits on other lanes


### Contradictions and calls the lane did not make

- WHAT: Drift RULE-18 says each view carries the facts its lines were built from under fixed keys. Neither section 2 nor the interfaces file names a key for the QA view's new Left-to-do lines.
  DECISIONS: Plan L11 entry (drift for QA prints through summary.left_lines); section 2.1 (drift's QA view prints only the two lines, in the same words).
  LEFT AS: No key added. RULE-18 now says those lines are the status's own. The alternative is a `left` key holding the payload's `left` items of kinds to_test_by_hand and to_sign (the contract's own name and shape). If the owner wants it, it is a two-line change in _qa_view plus PROOF-27.

### Departures

1. The drift QA view gets no new fact key for its Left-to-do lines. It drops `queue` and `signatures_stale` and adds nothing. RULE-18 says those lines are the status's own. No contract names a key for them, so I added none (see contradictions).
2. The tests for drift PROOF-32 and PROOF-33 hand compute_drift a real build_payload result whose `left` is replaced by items shaped as contract 2.2 (kind, count, text, command). Making a real `to_sign` rule would need evidence and audit files whose formats L2 and L1 are changing. PROOF-31 is fully end to end: a real @manual rule under gate passed.
3. The skill_anchor PROOF-3 text used to claim two refusal cases that no test ran: a deleted closing section, and a section with one outcome. The rewrite to one case drops them. The new PROOF-6 is the refusal its test shows.
4. The plan scoped the drift_criteria.md update to the drift QA view. I also brought its config-field table in line with section 2.7 and decisions 70, 75, 80 and 83, because this file is L11's and would otherwise say things that are no longer true:
   - the trust row is deleted
   - the gate_check.py readers are removed from `gate` and `min_strength`
   - `tests` is written by purlin:test at the first run
   - `ci` can be `none`
   - `version` is read by purlin:init --update, no longer by sign or export
   - the mutation question is asked at strong and signed only; I kept init's exact question text out, because L8 owns it
   Criteria-Version goes from 8 to 9.
5. To keep the build skill at its 130-line ceiling I cut the TypeScript marker example and the sentence about `.purlin/runtime/`. The anchor skill grew from 96 to 98 lines, under its 160 ceiling.
6. I removed the word stale everywhere in L11's files: "stales its signature" and "staled" became "a signature ... ends" or "back to `to sign`", and "a stale pin" became "a pin that is behind". The build and drift skills no longer say a code change leaves signatures standing.
7. The "rules changed" outcome in the anchor skill and the audit outcome in the build skill keep their existing `→ Next:` prefix. I changed only the endings the plan names, which use `→ Run:`.

### For integration

- Prove the three shell suites L11 owns. I already ran them locally, all green:
  - dev/test_e2e_anchor_authority.sh: 6 passed
  - dev/test_e2e_build_changeset.sh: 15 checks
  - dev/test_e2e_external_refs.sh: 10 passed, check 11 skipped
- `skills/build` matches a .gitignore pattern, so staging skills/build/SKILL.md needs `git add -u` or `-f`. The file is tracked.
- The build skill names `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin/markers.py" --near-misses --project-root .`, the command-line arm L3 adds (contract 2.6). No L11 test runs it; it works once L3 merges. L12's purlin_commands.md row for `--near-misses` should match.
- The build skill says purlin:test suggests and writes the test command at the first run (L3's skill_test and run changes).
- drift_criteria.md's config table no longer lists `trust`. It says the table names every field templates/config.json carries, so it agrees once L8 removes trust from the template. No test reads that table except purlin_version PROOF-8, which still passes.
- Nothing in L11's files now reads payload `queue`, `flags.stale` or `signatures.load_signatures`. drift.py no longer imports signatures, so step R's deletions do not touch drift.
- Rebuild and commit the generated evidence and pages at integration as planned. None of them are staged here.

### Deleted

- From drift.py: the stale-signature list and line, the Queue line and its counts, `_BOUND`, `_stale_reason`, the drift-side read of `payload['queue']` and `flags.stale`, the `signatures` import, and the unused `project_root`/`rng`/`raw_features` parameters of `_qa_view`.
- From the QA view: the keys `signatures_stale` and `queue`.
- From the specs: drift RULE-16 and PROOF-25, and the drift_criteria `trust` row.
- The 9 `[level: passed]` tags in L11's specs (upstream 5, skill_build 1, skill_anchor 1, skill_drift 1) and the 3 in dev/test_e2e_anchor_authority.sh.
- The TypeScript marker example and the `.purlin/runtime/` sentence in the build skill.

### Looked at

Nothing visual in this lane.

## L12 words

Acceptance passed in the lane: True. Commits: bceb5f4af spec(purlin_agent): steps, the summary and Left to do in place of levels and the queue; 2f78bd318 docs(references): the gate, the words and the commands for decisions 60 to 84

### Waits on other lanes


### Contradictions and calls the lane did not make

- WHAT: The purpose sentence of purlin:sign in references/purlin_commands.md reads "Walk the queue, or sign a rule, a feature or a batch as a signed commit". Decision 74 removes the queue as a separate idea, and decision 78 says purlin:sign takes one rule, a feature or all. But this sentence is the one home that the frontmatter `description` of skills/sign/SKILL.md (owned by L5) copies word for word. Neither section 2 nor the interfaces file gives the new sentence, and changing it here alone would split the two.
  DECISIONS: 74, 78
  LEFT AS: Purpose cell left as today: "Walk the queue, or sign a rule, a feature or a batch as a signed commit". Only the command cell changed, to `purlin:sign [feature] [RULE-N ...] [--all]`, and the "Who runs it" cell, which now says it walks the rules waiting for someone to test by hand or to sign. Options: (a) the owner picks one sentence, for example "Walk the rules that wait for a person, or sign one rule, a feature or all, as a signed commit", and integration sets it in both purlin_commands.md and skills/sign/SKILL.md; (b) L5's new frontmatter description is copied into purlin_commands.md at integration.

### Departures

Changes beyond the literal list in the lane entry, all written from the decisions:

- **Glossary: word removed.** "evidence level" was the agent's and the glossary's word for the per-rule dimension. I replaced it with "step" (decisions 68 and 79: "steps reached", "the count at each step", and the payload key `summary.steps`).
- **Glossary: entries removed.** bucket, rollup, trust, queue, gate check and stale are gone.
- **Glossary: entries added.** system (its display words), version, summary, Left to do (with its kinds) and machine.
- **hard_gates.md: section changes.**
  - "The three levels" became "The three steps".
  - "The level" section was deleted.
  - A new section, "When a version is finished", carries the sentence, the table of kinds with each kind's command, and the nothing-left lines. All of this is copied from contract 2.1.
  - The ci/ provenance paragraphs, the Azure identity table and trust were deleted.
- **writing_style.md: paragraph added beyond the system words.** It states the test of any output from decision 69, and says that `Nothing left to do.` at `passed` and `strong` is the one ending that names no command (decision 76).
- **purlin_commands.md: sections added.**
  - An "Exit codes" section with the table from 2.6, the run's stop lines and problem lines, and the markers `--near-misses` output.
  - The init row reads "Two questions at most".
- **Placeholder renamed.** `purlin:init --gate <level>` became `--gate <gate>` in purlin_commands.md and in the agent's routing table.
- **Agent routing row.** The QA row "what went stale?" now reads "what changed that I need to check?", still routed to `purlin:drift qa`.
- **rule_examples.md: unchanged.** It holds no Purlin trust or level text: "TrustEngine" is a product name, "warn level" is a log level and "stale data" is ordinary English. There was nothing to drop.

### For integration

- **Sign purpose sentence.** Settle it in both references/purlin_commands.md and skills/sign/SKILL.md (see contradictions). Until then purlin_commands.md still carries the word "queue" in that one cell, and the sweep will find it.
- **Checks that read my files.** These were kept green, and a later lane edit must not break them:
  - test_skill_status reads `purlin:status [name]` from purlin_commands.md.
  - test_skill_drift needs a row starting `| \`purlin:drift [role]\` |`.
  - frontmatter_problems needs a `purlin:<name>` row with a Purpose cell for every skill.
  - test_skill_build reads the commit_conventions Section table (Changeset = Never).
  - dev/test_e2e_build_changeset.sh greps Changeset, Decisions and Review in commit_conventions.md.
- **Links in docs/ that now point at nothing** (the docs phase's to fix):
  - docs/review-and-signing.md:17 links hard_gates.md#the-level; that section is deleted.
  - docs/ in general still describes levels, the queue, trust and the gate check against references that no longer do.
- **CLAUDE.md** (the owner's) still describes hard_gates.md as "the three levels"; the section is now "The three steps". Report this with the gate_check row.
- **Docstrings in other lanes' files** still say "evidence level":
  - scripts/mcp/purlin/gate.py:4
  - scripts/mcp/purlin/states.py:1
  - scripts/mcp/purlin/status.py:1
  - scripts/report/src/app.js:20
  - the specs/mcp/states.md Description
  
  The glossary word is now "step". Nothing tests this.
- **Behaviour the prose states that other lanes must build** (written from the contract, not checked here):
  - purlin:sign --all, and signing at every gate (L5).
  - Two commits for both `purlin:test --commit` and `purlin:audit --commit` (L3/L2).
  - `purlin:init` asking at most two questions, with an empty `tests` setting and `specs/_anchors/` not created at setup (L8).
  - drift qa printing the to_test_by_hand and to_sign lines (L11).
  - The tag run running the tests and nothing else (L7).
  - The sign/package version lookup (L5/L6).
- **Rebuilt locally, not staged.** No generated files are committed; integration rebuilds them.

### Deleted

- **From the glossary:** the entries for level, queue, trust, gate check, bucket and rollup; "meets the gate"; the `stale` cell word; the signed cell's `stale`.
- **From hard_gates.md:**
  - "The level" section and the level row of the derived-defaults table.
  - The trust paragraphs.
  - The paragraphs on the tag run checking who committed each ci/ file, the provenance table for GitHub and Azure, and the "no token" line.
  - `gate_check.py --check --verify`.
  - Every "meets the gate".
- **From purlin_commands.md:**
  - `purlin:init --update --dry-run` and its CI-preflight sentence.
  - `purlin:sign --batch`.
  - The `gate passed met` and `Nothing blocks at the gate passed.` lines.
  - The `sign: the gate is passed...` stop line.
  - Trust.
  - `specs/_anchors/` from what init writes.
- **From commit_conventions.md:** the "Every rule meets the gate signed." tag message, and the `version` fallback to the config.
- **From agents/purlin.md:**
  - The level paragraph.
  - The `gate passed met` and `Tests: <n> of <rules>` lines.
  - "walks the queue".
  - "When a signature went stale".
  - The words level and queue from NEVER 4's list.

### Looked at

Nothing visual changed. The lane owns only Markdown prose and one text test, so nothing was checked with playwright.

## L13 schema

Acceptance passed in the lane: False. Commits: 7be0089c4 feat(specs): a rule line carries no tag, and its text is the whole line; 046a7008c spec(security_no_dangerous_patterns): a credential name containing the word, and the revision guard narrowed; 565d0683c test(config_engine): the write example uses a key the settings still carry

### Waits on other lanes

- dev/test_security.py::TestSecurityPatterns::test_no_hardcoded_credentials (security_no_dangerous_patterns PROOF-4) | lane: L7 runner | needs: scripts/mcp/purlin/provenance.py deleted. Its line TOKEN_VARIABLE = 'SYSTEM_ACCESSTOKEN' is the only name in scripts/ containing a credential word that is given a quoted value.
- dev/test_specs_reader.py::TestGate::test_the_settings_written_out_are_the_ones_a_project_can_name | lane: L1 core | needs: gate.resolve_gate stops returning trust, so GateConfig.as_dict() holds exactly audit_parallel, ci, gate, min_strength, mutation_engine. The test is written to that contract.
- dev/test_states.py (10 tests: TestARuleWithNoProof::test_above_passed_a_rule_with_a_test_and_no_proof_reads_no_proof, TestHoldsAndSignatures::test_a_signature_is_needed_where_the_level_is_signed, TestThePlatformsInThePassedCell::test_a_passed_level_has_no_strong_cell_whatever_the_audit_found, TestLevels x2, TestALevelAsksItsOwnQuestions x4, TestPayload::test_a_feature_carries_its_rules_with_their_tags_and_proofs) and dev/test_queue.py (3) | lane: L1 core | needs: The level rules and their tests deleted or rewritten (decision 73). These tests use [level: ...] in LEVELS_SPEC/ONE_PASSED_SPEC, which the parser no longer reads.
- dev/test_run_script.py::TestWhichRulesTheAuditReads::test_a_passed_level_is_read_only_at_the_gate_passed and TestTheAuditExitCode::test_a_passed_level_meets_the_strong_line_on_its_tests | lane: L3 run | needs: The level clause of _audit and RULE-49's level half deleted, with these tests.
- dev/test_signatures.py (9 failed + 1 error) and dev/test_tag.py (7) | lane: L5 signing | needs: Tests rewritten without levels. The frozen dev/sign_project.py SPEC marks RULE-1 [level: passed], and signing_project/sign_the_queue rely on it asking for no audit and no signature. With the tag unread, RULE-1 needs both, so the walk writes no tag.
- dev/test_export.py (5 failed + 5 errors) | lane: L6 package | needs: The same dependence on dev/sign_project.py's [level: passed] RULE-1 through signed_project, plus test_a_rule_carries_only_the_statuses_its_level_asks_for. The tests need rewriting without levels.
- dev/test_gate_check.py (16) | lane: L7 runner | needs: The file deleted with scripts/ci/gate_check.py (section 7 item 1).

### Contradictions and calls the lane did not make

- WHAT: The narrowed RULE-6 still leaves one gap in product code: drift's date path hands git `rev-parse --verify -q <sha>^` with no `--end-of-options` (scripts/mcp/purlin/drift.py, about line 318). That sha comes from git's output, not from Purlin, and it is not one of the five places that hand git the fixed word `HEAD` (payload `rev-parse HEAD`; drift `reflog ... HEAD --`, `rev-list --max-count=N HEAD --`, `rev-parse --verify -q HEAD`, `log --since ... HEAD --`).
  DECISIONS: Decision 65: the guard is required where the revision comes from outside Purlin; the five HEAD places stay as they are.
  LEFT AS: drift.py is L11's, so I did not touch it. The PROOF-10 test runs drift with no date, as before, so it does not reach this call. Options: (a) L11 or a later step adds `--end-of-options` before `<sha>^`, and PROOF-10's test also runs drift with a date and a count; (b) the owner counts a sha that git printed as coming from Purlin and widens the rule's exception to say so.

### Departures

1. specs: the plan deletes RULE-1, whose second half ("any other bracketed text at the end is not a tag and stays in the claim") was the one home of the behaviour contract 2.8 keeps (the bracket stays in the rule text and enters the hash). I folded it into RULE-3 instead of adding a rule. The rewritten PROOF-1..4 and PROOF-17 all prove RULE-3, and the proof-text changed-word case became the new PROOF-18. Proofs and tests use `[owner: qa]`, never `[level: ...]`, so the integration sweep for `level:` finds nothing in my files.
2. spec_format.md, beyond removing the tag: "does not meet the gate" became "counts under `Left to do` as a rule to write a proof for" (the phrase "meets the gate" is to be used nowhere). The `@manual` row now says the signature carries a note "when one is given" instead of "always", following decision 84.
3. security PROOF-4 and PROOF-6 each held several cases. Rewriting them to decision 71 split them into PROOF-4, 7, 8 and PROOF-6, 9, 10, 11, and the one test into one test per proof. The PROOF-10 test now treats any argument carrying a sha or `HEAD` as a revision (a range `<sha>..HEAD` included) and leaves out only the literal `HEAD`. This is how I read "PROOF-6's test leaves out the literal HEAD".
4. The credential regex captures the whole name, so a finding names it (for example ['TOKEN_VARIABLE']).
5. dev/test_specs_reader.py holds unmarked gate tests. I deleted test_trust_is_local_or_remote_and_defaults_to_local (decision 75) and test_a_level_is_the_lower_of_its_tag_and_the_gate (decision 73; section 0 has a lane stop using `level_of` in its own files). The settings-key test now expects no `trust`.
6. config_engine PROOF-12 used the retired `trust` key as its example, and the integration sweep greps for it. It now uses `gate`. The plan does not list this.
7. Docstrings in specs.py no longer speak of "the triple" (gone in signature format 11); they say "the rule hash" / "the proof hash" a signature binds.

### For integration

- After this lane merges, `[level: ...]` is plain rule text everywhere. Until L1, L3, L5, L6 and L7 merge, the 57 tests listed under waits_on_other_lanes fail. Those lanes run their own tests against main's parser, which still reads the tag, so a test of theirs that relies on it can pass in their lane and still fail once merged with this one.
- The riskiest dependence is in the frozen helpers: dev/sign_project.py `SPEC` marks RULE-1 `[level: passed]`, and `signing_project`, `sign_the_queue`, `signed_project` and `EVERY_RULE_SIGNED` depend on it. dev/mcp_project.py `SPEC` carries `[level: signed]` on RULE-1, and `LEVELS_SPEC`/`ONE_PASSED_SPEC` exist only for levels. Step R or integration has to strip these brackets and helpers and check that dev/test_signatures.py, dev/test_tag.py and dev/test_export.py pass without them.
- scripts/mcp/purlin/fingerprint.py `rule_line(spec_path, rule_id, text, meta)` still appends ` [level: X]` from `meta`. fingerprint.py reads `info.get('rule_meta', {})`, so it now always passes None. The fingerprint's spec lines come out the same as before, because the bracket is now in the text. The `meta` parameter and the level branch are dead code for L2 or R to delete. payload.py line 517 also reads `rule_meta` through `.get`, which is harmless until L1 removes it.
- Stale `[level: ...]` prose outside my files, for the owning lanes or the docs phase: references/spec_quality_guide.md, review_criteria.md (L4); hard_gates.md, glossary.md, agents/purlin.md (L12); package_format.md (L6); marker_format.md (L3); skills/spec, spec-from-code (L4); skills/sign (L5); docs/specs-and-anchors.md line 78 `- RULE-N: <claim> [level: <level>]` and docs/review-and-signing.md, getting-started.md, raising-the-gate-and-upgrading.md, team-workflow.md, how-purlin-works.md, spec-from-code.md; code comments in gate.py, states.py, summary.py, sign.py, gate_check.py.
- Shell suites: none owned.
- Nothing visual changed.

### Deleted

From scripts/mcp/purlin/specs.py: `_RULE_TAG_RE`, `split_rule_tags`, the `rule_meta` key of each scanned spec, and the tag example in the module docstring. From references/formats/spec_format.md: the section "The rule tag" and its table. From the specs: specs RULE-1, RULE-2, RULE-15 and the `[level: passed]` tags (schema_spec_format 3, specs 2, purlin_version 2). From dev/test_specs_reader.py: the tests of split_rule_tags and rule_meta, test_trust_is_local_or_remote_and_defaults_to_local, test_a_level_is_the_lower_of_its_tag_and_the_gate.

### Looked at

Nothing visual in this lane; no page was looked at.

