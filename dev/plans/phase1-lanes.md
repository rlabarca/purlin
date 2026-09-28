# Phase 1 plan: the product changes for decisions 60 to 72

> Written by a planning agent on 2026-09-28 from decisions 60 to 72. Decisions 73 and later
> were made after it and change it: marking a rule lower goes, the queue goes, trust goes, the
> tag run's two extra checks go. Read `three-levels.md` from decision 73 on before any lane starts.

I changed nothing in the tree. The plan has 21 lanes run in 13 waves, and 38 questions for the owner. Four things need an answer before any agent starts:

- **The contradiction in the remote check (Q5).** Decision 60 says the CI check "still says pass or fail". Decision 68 says no `PASS` or `FAIL` word is printed and the job fails only on tests.
- **The skill length limits (Q10).** Build, init, status, test and audit, plus `agents/purlin.md`, are at their written maximum length today. Sign is 1 line short. Most lanes add lines to them.
- **The trust question (Q11)** decides how big the `init-one-question` lane is.
- **What "committed work" means (Q22).** As written, decision 70's "commit in the same step" and "tag only from committed work" block each other.

## Rules for every lane

- Each lane runs in `/Users/richlabarca/LocalCode/purlin-wt/<name>`, on branch `<name>`, and merges by fast-forward. Before merging, rebase on `main` and rerun the lane's acceptance.
- Every lane that touches `scripts/report/src/` runs `python3 dev/build_report.py`. That writes `scripts/report/purlin-report.html` and the root `purlin-report.html`. These two built files are in every dashboard lane. After a rebase, rebuild them rather than merging them by hand.
- No lane commits evidence. Each lane checks this repository with `python3 scripts/run/purlin_run.py --test --all`: every marker must be tied, and every rule the lane touched must pass. The files `.purlin/evidence/local/*.json` and `.purlin/tests.md` are written again and committed once, at the end of the phase. If lanes committed them, they would conflict with each other.
- No lane adds to `dev/test_vocabulary.py`, the table of removed spellings. No lane writes a test that checks a removed thing is gone. Both are forbidden by decision 44.
- A format version under `references/formats/` goes up by 1 in the lane that changes that format structurally, as `CLAUDE.md` says. The payload's `schema_version` (states RULE-27, `SCHEMA` in `app.js`, now 9) also goes up by 1 in each lane that changes the payload's keys.
- Each lane applies its change to this repository's own files as well (decision 49). That covers `.purlin/config.json`, `.github/workflows/purlin.yml` and `dev/fixtures/consumer-ci/`. After merging, `purlin:init --update` must report nothing pending here.
- A proof a lane writes or rewrites already follows decision 71: one starting situation, one action, at most 60 words. Splitting every other proof waits for phase 2.
- Acceptance for every lane is its named test files run whole (`.venv/bin/python -m pytest <files>`) plus `bash dev/run_tests.sh --fast`.
  - Dashboard lanes also run `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py` and `dev/test_report_refresh.py`. They also check the page with playwright at 1500, 1280, 1024, 768 and 390 pixels in the dark theme.
  - Lanes that touch setup, signing or the run also run the shell suites named in the lane.

## 1. The lanes

### L1 `queue-words` (decision 61)

- **Decision:** "The queue holds hand checks and signatures and nothing else ... `waiting for a person` and `need a person` go. The full sentences are `waiting for someone to test by hand` and `waiting for someone to sign`, used in hovers and empty states; the card stays `Queue`, and beneath it and in the queue tab the short labels are `To test by hand <h> · To sign <s>`. The terminal and the docs use the same words."
- **Code:**
  - `scripts/mcp/purlin/board.py`: `queue_line` and `needs_a_person`.
  - `scripts/mcp/purlin/status.py`: `next_step`'s `person` reason and the `→ Queue:` line in `_directives`.
  - `scripts/mcp/purlin/drift.py`: lines 565-596 build their own queue line. That line becomes `board.queue_line`, so the wording lives in one place.
  - `scripts/review/sign.py`: `opening_line`, and `'Nothing is waiting for a person.'` in `walk`.
  - `scripts/report/src/board.js`: `queueLines`, and the `flagCard` for Queue gets the label line beneath it.
  - `scripts/report/src/queue.js`: `renderQueue`'s heading, its label line and its empty state.
  - `styles.css` if needed, then rebuild the page.
- **Skills and references:**
  - `skills/status/SKILL.md` line 100, `skills/sign/SKILL.md` line 59, `skills/drift/SKILL.md` line 83.
  - `references/drift_criteria.md` line 77, the definition of the queue in `references/glossary.md`, and `references/purlin_commands.md` line 124.
- **Specs:**
  - `specs/mcp/states.md` RULE-55, RULE-58 (the "a person" reason), and PROOF-64.
  - `specs/dashboard/purlin_report.md` RULE-18, RULE-19 and RULE-32, with their proofs 18, 19, 25 and 49.
  - `specs/review/signatures.md` RULE-11, with PROOF-67 and PROOF-80.
  - `specs/mcp/drift.md` for the queue view.
- **Formats:** none.
- **Acceptance:** `dev/test_mcp_server.py`, `dev/test_queue.py`, `dev/test_drift.py`, `dev/test_export.py` (line 691), `dev/test_tag.py` (line 123), `dev/test_signatures.py` and `dev/test_skills.py`, plus the browser suites and `bash dev/test_init_e2e_gates.sh` (`init_e2e_walk.sh` line 381).
- **Questions:** Q9, Q10.

### L2 `azure-branch` (65, the run branch on Azure DevOps)

- **Decision:** "The remote run reads the full branch name first. Fixed on this machine against a stand-in, confirmed on the work machine."
- **Code:** `scripts/run/host.py`. `current_branch` reads `GITHUB_REF_NAME` and then `BUILD_SOURCEBRANCHNAME`. It becomes one reader with `ref_branch`, which reads `BUILD_SOURCEBRANCH` first and strips `refs/heads/`. If `dev/manual/check_azure_remote.py` names the variable order, it changes too.
- **Specs:** `specs/run/host.md`. RULE-8 keeps its text. PROOF-8 gets the run-branch case from the gap text (`refs/heads/run/main-4f1c2ab` is pushed as that ref).
- **Tests:** in `dev/test_host.py`, put back the test of about 15 lines that the rewrite took out.
- **Acceptance:** `dev/test_host.py`, `dev/test_remote.py`, `dev/test_consumer_ci.py`. It is confirmed on the work machine later.
- **Questions:** none.

### L3 `summary` (decisions 60 and 68: the one summary, `Left to do`, the removed count)

- **Decision 60:** "The dashboard's box `<n> of <m> rules meet the gate` and its hover go, and the sentence goes from the terminal ... The tiles carry the number for each level."
- **Decision 68:** "The terminal, the dashboard and the check on a remote runner show the same thing. Each step contains the next: `35 pass their tests. 30 are strong. 20 are signed.` ... `Left to do: 5 rules to audit, 10 to sign.`, and `Nothing left to do` when nothing is."
- **Design to hand the agent, so it does not choose.** The step counts and the left-to-do items are computed once in Python and carried in the payload's `summary`. The terminal and the dashboard both read them. Skill_status RULE-2 already says the skill never recounts, and purlin_report RULE-8 changes from "added up in the page" to "read from the payload".
- **Code:**
  - `scripts/mcp/purlin/states.py`: `feature_rollup` and `project_rollup` get the step counts and the left-to-do counts. `met` is removed if nothing reads it any more.
  - `scripts/mcp/purlin/payload.py`: the summary keys, and schema 9 becomes 10.
  - `scripts/mcp/purlin/board.py`: `headline` is deleted. `bucket_line` becomes the step sentence and a new `left_line` is added.
  - `scripts/mcp/purlin/status.py`: `_summary`, and the last branch of `next_step` (`nothing is outstanding at gate`).
  - `scripts/run/purlin_run.py`: `tests_line`, `gate_line`, `last_lines`, `project_counts`, `_nothing_to_run`, the end of `_audit` (`AUDIT_LINE`, `NOTHING_BLOCKS` plus the gate line), and the module docstring.
  - `scripts/report/src/app.js`: in `gateChips`, the count chip and its hover go and the `gate: <gate>` chip stays. Also `SCHEMA`, `bucketTone` (Q6) and `reached`.
  - `scripts/report/src/board.js`: `statStrip`, and where `Left to do` sits (Q6).
  - `styles.css`, then rebuild the page.
  - `dev/fixtures/report/solo.json`, `team.json`, `regulated.json`, and `dev/build_report.py` if it lists the sample keys.
- **Skills and references:**
  - `skills/status/SKILL.md` lines 6, 58, 75 and 99, `skills/test/SKILL.md` Step 6, and `skills/audit/SKILL.md` lines 47-48.
  - The rollup definition in `references/glossary.md` and the status row in `references/purlin_commands.md`.
- **Specs:**
  - `specs/mcp/states.md` RULE-25, RULE-26, RULE-27, RULE-37 (rewritten), RULE-58 (its last clause) and RULE-70, plus a new rule for `Left to do`.
  - `specs/dashboard/purlin_report.md` RULE-7 (the count chip goes), RULE-8 and RULE-44, plus a new rule for where `Left to do` is shown.
  - `specs/run/run_script.md` RULE-11, RULE-48, RULE-54 and RULE-57.
  - `specs/skills/skill_test.md` RULE-2 and `skill_audit.md` RULE-6.
- **Formats:** none.
- **Acceptance:**
  - `dev/test_mcp_server.py`, `dev/test_queue.py`, `dev/test_run_script.py`, `dev/test_skills.py`, `dev/test_failing.py`, `dev/test_backing_tests.py`.
  - The browser suites.
  - `bash dev/test_e2e_required_rules.sh` (lines 197 and 212) and `bash dev/test_init_e2e_gates.sh` (`init_e2e_walk.sh` lines 263 and 308).
- **Questions:** Q1 to Q4, Q6, Q10.

### L4 `no-proof-box` (68: the no-proof box and filter, and the description)

- **Decision:** "A rule with no proof, at the gates that ask for one, has its own box and filter on the dashboard. A spec's `> Description:` is shown under the feature's name on the dashboard."
- **Code:**
  - `scripts/mcp/purlin/states.py`: `COUNTED_FLAGS` gets the no-proof count, counting only rules whose level asks for a proof.
  - `scripts/mcp/purlin/payload.py`: the summary and rollup key, and schema 10 becomes 11.
  - `scripts/report/src/board.js`: `statStrip`, and `featureRow` for the description.
  - `scripts/report/src/filters.js`: a new filter.
  - `styles.css`, then rebuild the page and the fixtures.
- **Specs:**
  - `specs/mcp/states.md` RULE-25, RULE-26 and RULE-27.
  - `specs/dashboard/purlin_report.md` RULE-8, RULE-13, RULE-35 and RULE-49, plus two new rules: the box and filter, and the description.
  - `references/formats/spec_format.md` lines 45 and 51 already say the dashboard shows the description. This lane makes that true, so no version change.
- **Acceptance:** `dev/test_mcp_server.py`, the browser suites, the visual check.
- **Questions:** Q7, Q8.

### L5 `remote-check` (68 on the runner, 60 on the CI check)

- **Decision:** "On a remote runner the job fails only when a test fails or could not run; rules not yet audited or signed never fail it, and no `PASS` or `FAIL` word is printed."
- **Code:**
  - `scripts/ci/gate_check.py`: the `PASS.` and `FAIL.` lines go, the `result` key in `--json` goes, the exit codes change per Q5, `_ENFORCEMENT_NOTE` is reworded, and it prints the summary and `Left to do` from L3.
  - `templates/purlin.yml` and `templates/purlin.azure-pipelines.yml`: the comments and the step name "Check the gate".
  - The rendered copies: `.github/workflows/purlin.yml` and the workflow under `dev/fixtures/consumer-ci/`.
  - `scripts/init/scaffold.py`: the note in `write_workflow`, "and ends with the gate check".
  - `skills/init/SKILL.md` line 101, `references/hard_gates.md` (line 127 and the paragraph on what enforces the gate), and the gate check entry in `references/glossary.md`.
- **Specs:**
  - `specs/ci/gate_check.md` RULE-2, RULE-9, RULE-11, RULE-13, RULE-14 and RULE-23, and RULE-15 and RULE-16 depending on Q5 and Q32.
  - `specs/init/scaffold.md` RULE-42, which says the job fails when the gate is not met.
- **Acceptance:** `dev/test_gate_check.py`, `dev/test_provenance.py`, `dev/test_tag.py`, `dev/test_consumer_ci.py`, `dev/test_init_scaffold.py`.
- **Questions:** Q5, Q32.

### L6 `gate-phrase` (60 and 68: "meets the gate" used nowhere; the `No tag` line)

- **Decision 68:** "The phrase `meets the gate` is used nowhere."
- **Decision 60:** "What the last line of a run, the `No tag` line and the CI check's failure say in its place is still to be asked."
- **Why it runs last:** it is a sweep, so it also catches every such sentence the earlier lanes wrote.
- **Code:**
  - `scripts/review/sign.py`: `NO_TAG_SHORT`, `TAGGED`, `tag_message`, and the docstring.
  - `scripts/export/package.py`: `WRITTEN`, the state `gate <gate> met`, and `rules_meeting_gate` and `rules_short_of_gate`, per Q31.
- **Formats:** `references/formats/package_format.md` goes up by 1 if Q31 renames a key or a state.
- **References and skills:**
  - `references/commit_conventions.md` line 86 (the tag message), `references/hard_gates.md`, `references/glossary.md`, `references/purlin_commands.md` line 126, `references/review_criteria.md` line 79, and `references/spec_quality_guide.md` lines 84 and 110.
  - `agents/purlin.md` line 56. That file is at its 135-line limit.
  - `skills/sign`, `skills/export` (lines 8, 38 and 49-51), `skills/spec` (lines 99-101), `skills/audit`, `skills/status`.
- **Specs:** `specs/review/signatures.md` RULE-45, RULE-46, RULE-52 and RULE-54; `specs/export/package.md` RULE-1, RULE-3, RULE-4 and RULE-5; `specs/skills/skill_export.md` RULE-4; `skill_sign.md` RULE-8.
- **Acceptance:** `dev/test_tag.py`, `dev/test_export.py`, `dev/test_signatures.py`, `dev/test_skills.py`, `bash dev/test_e2e_required_rules.sh`, `bash dev/test_init_e2e_gates.sh`.
- **Questions:** Q4, Q10, Q31.

### L7 `one-answer` (69, part 1)

- **Decision:** "A rule has passed only when every test tied to it ran and passed, and the terminal, the dashboard, the evidence and the exit code all say the same."
- **Code:**
  - `scripts/mcp/purlin/evidence.py`: `proof_results` stops dropping `missing` and `not run`.
  - `scripts/mcp/purlin/states.py`: `_passed_cell`. A proof with any tied test that did not run reads `not run`.
  - `scripts/run/evidence.py`: `render_table` and `rule_word`, so that `.purlin/tests.md` agrees with the rest.
- **Specs:** `specs/mcp/states.md` RULE-3, RULE-65 and RULE-71; `specs/run/evidence_writer.md` RULE-2, RULE-8 and RULE-15.
- **Formats:** none. Check the wording of `evidence_format.md`.
- **Acceptance:** `dev/test_mcp_server.py`, `dev/test_evidence_writer.py`, `dev/test_evidence_reader.py`, `dev/test_run_script.py`, `dev/test_backing_tests.py`, `dev/test_failing.py`.
- **Questions:** none. There is one consequence to note, under Risks.

### L8 `next-by-cause` (69, part 2)

- **Decision:** "A run names each rule that fails or has no test, and its advice fits the cause: a comment to correct, settings to restore, or `purlin:build`. With the settings file missing, a run stops, says so, names the command that restores it, and writes nothing."
- **Code:**
  - `scripts/mcp/purlin/status.py`: `next_step` and `_said` name the rules and give advice by cause.
  - `scripts/mcp/purlin/payload.py`: carries each feature's marker problems, so status can see the cause.
  - `scripts/run/purlin_run.py`:
    - `main` stops before anything runs when `.purlin/config.json` is missing, and `--audit` stops the same way.
    - `NO_SUITES` changes.
    - The rules are named after the table.
  - `scripts/run/reports.py`: `FIX_ONE` and `FIX_MANY`.
  - `scripts/mcp/config_engine.py`, if it has to report "no file" apart from "no key".
  - `skills/test/SKILL.md` Step 7 and the next-step table in `skills/status/SKILL.md`. Both skills are at their length limit.
- **Specs:** `specs/mcp/states.md` RULE-58, RULE-68 and RULE-69, plus a new rule for naming the rules; `specs/run/run_script.md` RULE-11, plus a new rule for the missing settings file; `specs/run/reports.md` RULE-19.
- **Acceptance:** `dev/test_mcp_server.py`, `dev/test_queue.py`, `dev/test_run_script.py`, `dev/test_reports.py`, `dev/test_skills.py`.
- **Questions:** Q17, Q18, Q19, Q10.

### L9 `near-miss` (69, part 3)

- **Decision:** "A comment above a test that is nearly right is found and repaired by `purlin:build`; a test run does not look for them."
- **Code:**
  - `scripts/mcp/purlin/markers.py`: the malformed-comment detection becomes a near-miss finder, with a command-line arm the build skill runs under `${CLAUDE_PLUGIN_ROOT}/scripts/`.
  - `scripts/run/reports.py`: `malformed_lines` and `NOT_A_MARKER` leave the run.
  - `scripts/run/purlin_run.py`: stops printing them.
  - `skills/build/SKILL.md`: find the near misses, propose the fix, then edit. The skill is at its 130-line limit.
- **Formats:** `references/formats/marker_format.md` line 36, "reported as not a marker", changes. The version goes up by 1.
- **Specs:** `specs/run/reports.md` RULE-1; `specs/skills/skill_build.md` gets a new rule.
- **Acceptance:** `dev/test_reports.py`, `dev/test_run_script.py`, `dev/test_skills.py`.
- **Questions:** Q20, Q10.

### L10 `update-cache` (65, the old cache folder)

- **Decision:** "`purlin:init --update` deletes it outright. The rule changes: it no longer says the folder is left on disk and named in `.gitignore`."
- **Code:** `scripts/init/update.py`, `_detect_untracked` and `_apply_untracked`. `.purlin/cache/` is removed from git and deleted from disk, and the migration's description changes.
- **Specs:** `specs/init/update.md` RULE-8 and PROOF-8.
- **Tests:** in `dev/test_init_update.py`, put back the committed-cache case, now asserting that the folder is gone. The input fixture `dev/fixtures/upgrade-0.9.5/.purlin/cache` stays.
- **Acceptance:** `dev/test_init_update.py`.
- **Questions:** none.

### L11 `foreign-not-run` (65, a proof another operating system owns)

- **Decision:** "whose test is skipped here, is recorded in the evidence as `not run`, never `missing`."
- **Code:** `scripts/run/evidence.py`, `build_section` (lines 157-172). An entry for a foreign proof whose test was skipped here gets the result `not run`.
- **Formats:** `references/formats/marker_format.md` line 178 ("`not run` is written as `missing`") gets the exception, and the version goes up by 1.
- **Specs:** `specs/run/run_script.md` RULE-10 (PROOF-10 gets the skipped case) and `specs/run/evidence_writer.md` RULE-3.
- **Acceptance:** `dev/test_run_script.py` (put back the assertion that PROOF-2 reads `not run`) and `dev/test_evidence_writer.py`.
- **Questions:** none.

### L12 `linux-unix` (65, a system that is not Windows or macOS)

- **Decision:** "is treated as `linux`. The word typed in a spec and the name results are filed under stay `linux`; screens, the dashboard and the docs show it as `Linux/Unix`."
- **Code:**
  - `scripts/mcp/purlin/evidence.py`: `host_os` stops returning `sys.platform` when nothing matches, and one function gives the name a person reads.
  - `scripts/run/purlin_run.py`: the `FOREIGN_PROOF` line.
  - `scripts/mcp/purlin/status.py`: the reason `need <os>, which this machine is not`.
  - `scripts/report/src/app.js` (`platformLines`) and `rule.js` (`platformBoxes`), then rebuild the page.
- **Specs:** `specs/run/run_script.md` RULE-21 and RULE-10; `specs/dashboard/purlin_report.md` RULE-31 and RULE-37; `specs/mcp/states.md` RULE-58.
- **Acceptance:** `dev/test_run_script.py` (add a row: `freebsd13` reads as linux), `dev/test_mcp_server.py`, the browser suites.
- **Questions:** Q33.

### L13 `host-line` (65, a git host that is neither GitHub nor Azure DevOps)

- **Decision:** "Setup's line says what still works: everything on the user's own machine works on any host, and only a remote run needs one of the two."
- **Code:**
  - `scripts/run/workflow.py`: `UNKNOWN_HOST`.
  - `scripts/init/scaffold.py`: the summary line `Git host not read from a remote`.
  - `scripts/run/remote.py`: its refusal for an unknown host.
  - `templates/config.json`: the `ci` default, per Q34.
- **Specs:** `specs/init/scaffold.md` RULE-44 (with PROOF-44) and RULE-14.
- **Acceptance:** `dev/test_init_scaffold.py`, `dev/test_remote.py`, `dev/test_consumer_ci.py`.
- **Questions:** Q34.

### L14 `skill-endings` (65, every ending names a command)

- **Decision:** "The build skill's 3 endings and the anchor skill's 2 endings that name none get one, and the test checks every ending."
- **Skills:** `skills/build/SKILL.md` (at its 130-line limit) and `skills/anchor/SKILL.md`.
- **Specs:** `specs/skills/skill_build.md` PROOF-3 and `specs/skills/skill_anchor.md` PROOF-3.
- **Tests:** in `dev/test_skills.py`, the build and anchor checks call `undirected_outcome_problems`, and one check runs over every skill.
- **Acceptance:** `dev/test_skills.py`.
- **Questions:** Q35, Q10.

### L15 `security-names` (65: the name containing `token`, and the guard before a revision; merged)

- **Decisions:** "No name containing `token` ... The rule stays as written and the test checks it in full." "The guard before a revision handed to git is required where the revision comes from outside Purlin. The rule is narrowed to say so; the five places that hand git the fixed word `HEAD` stay as they are."
- **Why merged:** both parts rewrite the same spec file and the same test file.
- **Code:** `scripts/mcp/purlin/provenance.py` line 57 renames `TOKEN_VARIABLE`, together with its uses at lines 204 and 210 and in `dev/manual/check_azure_provenance.py` lines 157-159.
- **Specs:** `specs/_anchors/security_no_dangerous_patterns.md` RULE-6 (narrowed), PROOF-4 and PROOF-6.
- **Tests:** `dev/test_security.py`. The credential check matches a name that contains the word, and the revision check leaves out the fixed `HEAD`.
- **Acceptance:** `dev/test_security.py`, `dev/test_provenance.py`, `dev/test_gate_check.py`.
- **Questions:** none.

### L16 `signatures` (62, 67 and the signature half of 72; merged)

- **Decision 62:** "A signature says a person signed one exact set: the rule, its proof, its test, what the audit found, the code the rule covers, and the operating systems its test results came from ... The signature format changes, so its `Format-Version` is raised."
- **Decision 67:** "A signature counts when its commit was signed with an SSH key, any key. Purlin records the signer's name, the time and the key's fingerprint, and does not check whose key it is. The list of who may sign goes, with the setting and the code behind it ... Before signing starts Purlin confirms only that there is a key to sign with."
- **Decision 72:** "A signature's code is the files its feature lists: a change to any of them ends the signature of every rule in that feature."
- **Why merged:** both decisions rewrite the same signature fields, the same "counts" function and the same signed-cell reasons, and both raise the same format version.
- **Code:**
  - `scripts/mcp/purlin/signatures.py`: `is_current` binds the code hash and the systems. `commit_is_signed` (which reads `%G?`) is replaced by a check that the commit carries an SSH signature, and that check reads its fingerprint (Q24). `counts` changes to match.
  - `scripts/mcp/purlin/states.py`: `_signed_cell`, `_binds`, `_what_moved` (a new reason for a code change) and `AUDIT_MOVED` / `HASHES_MOVED`. The `machine` and `os` fields change per Q25.
  - `scripts/mcp/purlin/payload.py`: each rule's code hash (from `fingerprint.code_hash` over the owning feature's `> Scope:`, per Q30 for anchors) and its systems.
  - `scripts/review/sign.py`:
    - `write_signature` and `machine_name`.
    - `signing_configured` checks for a key.
    - `SIGNING_SETUP` and `signing_help`.
    - The walk's closing lines (Q27).
  - `scripts/init/scaffold.py`: `print_signed`.
  - `scripts/export/package.py`: the signature entries (`machine`, `os`, `commit_verifies`, `locked`).
  - `scripts/ci/gate_check.py`: `verify` calls `is_current` with the new arguments.
  - `scripts/run/purlin_run.py`: `_audit`'s stale-signature count calls `is_current` with the new arguments.
  - `scripts/report/src/rule.js`: `signPanel`'s "on <machine> (<os>)", then rebuild the page and the fixtures.
- **Formats:** `references/formats/signature_format.md` goes from 10 to 11. The paragraph "Changing the code alone stales nothing" goes, and so do the `%G?` row and the machine and os rows. `references/formats/package_format.md` goes from 2 to 3 (the signature entry).
- **References and skills:** `references/hard_gates.md` and `references/glossary.md`; the "two things that count" in `skills/sign/SKILL.md`; the signing setup in `skills/init/SKILL.md` (lines 189-193).
- **Specs:**
  - `specs/review/signatures.md` RULE-6, RULE-9, RULE-17, RULE-20, RULE-21, RULE-23 and RULE-50, plus new rules for binding the code and the systems.
  - `specs/mcp/states.md` RULE-18, RULE-20, RULE-22, RULE-35 and RULE-47, and RULE-4's clause "what a signature locks is the evidence rather than the machine".
  - `specs/export/package.md` RULE-6; `specs/ci/gate_check.md` RULE-15; `specs/init/scaffold.md` RULE-10; `specs/skills/skill_sign.md` RULE-5; `specs/dashboard/purlin_report.md` RULE-15 and RULE-26.
- **Acceptance:**
  - `dev/test_signatures.py`, `dev/test_tag.py`, `dev/test_export.py`, `dev/test_mcp_server.py`, `dev/test_gate_check.py`, `dev/test_init_scaffold.py`, `dev/test_skills.py`.
  - The browser suites and `bash dev/test_init_e2e_gates.sh`.
  - The allowed-signers setup in the test helpers is deleted wherever it only served signatures: `dev/test_signatures.py` 283-329, `dev/test_export.py` 536-538, `dev/test_mcp_server.py` 258-264, `dev/test_tag.py` 68 and `dev/init_e2e_walk.sh` 197-216. It stays in `dev/test_host.py` and `dev/test_provenance.py`, which check the runner's files and not signatures.
- **Questions:** Q24 to Q30, Q10.

### L17 `sign-version` (70: the version, and the tag only from committed work)

- **Decision:** "With no version stated by the project, `purlin:sign` asks for one and offers to write it to a version file. A signed tag is written only when every result came from committed work."
- **Code:**
  - `scripts/review/sign.py`: `project_version` drops the fallback to the version in the config; `tag_name` drops `unversioned`; `tag_if_met` gets two new refusals.
  - `scripts/export/package.py`: the same source for the version (line 14 and the reader).
- **Skills:** `skills/sign/SKILL.md` asks and offers to write the file. It is 1 line under its 185-line limit. Also `skills/export/SKILL.md`.
- **Specs:** `specs/review/signatures.md` RULE-45, plus new rules; `specs/export/package.md` RULE-1 and RULE-2; `specs/skills/skill_sign.md` gets a new rule.
- **Acceptance:** `dev/test_tag.py`, `dev/test_export.py`, `dev/test_signatures.py`, `dev/test_skills.py`, `bash dev/test_init_e2e_gates.sh`.
- **Questions:** Q22, Q23, Q10.

### L18 `init-one-question` (70: setup)

- **Decision:** "`purlin:init` asks how far every rule must go ... The question about breaking the code on purpose is asked only at the gates where it runs. The rehearsal, `--dry-run`, goes. The folder for anchors is created when the first anchor is written or brought in."
- **Code:**
  - `scripts/init/scaffold.py`:
    - The questions change.
    - `--dry-run` and `Plan.dry_run` go.
    - `specs/_anchors` is no longer created (line 708).
    - `NO_ENGINE` is not printed at `passed`.
    - The trust handling (`TRUST_QUESTION*`, `trust_words`, `ask_trust`) follows Q11.
  - `scripts/init/update.py`: its questions follow Q11 and Q12, its `--check` follows Q15, and the copy of the gate question in `GATE_QUESTION` is removed.
  - Only if Q11 removes the setting: `scripts/mcp/purlin/gate.py`, `scripts/run/workflow.py` (`TRUST_REASON*`, `wanted`), `sign.py` (`untrusted`, `has_a_ci_run`, `NO_CI_RUN`), `status.py` (the trust branch) and `package.py` (the `trust` key; `package_format.md` goes up by 1).
  - `templates/config.json` and this repository's `.purlin/config.json`.
- **Skills and references:**
  - `skills/init/SKILL.md` (at its 250-line limit), and the trust text in `skills/test`, `skills/sign` and `skills/audit`.
  - `references/purlin_commands.md` (lines 91, 96 and 152), `hard_gates.md`, `glossary.md`, `drift_criteria.md` line 112, and `supported_frameworks.md`.
- **Specs:**
  - `specs/init/scaffold.md` RULE-1, RULE-5, RULE-6, RULE-13, RULE-18, RULE-30, RULE-33, RULE-45, RULE-46 and RULE-49, plus a new rule that no anchors folder is created.
  - `specs/init/update.md` RULE-3, RULE-10, RULE-12 and RULE-26.
  - `specs/skills/skill_init.md` RULE-2, RULE-5 and RULE-6.
  - `specs/review/signatures.md` RULE-47, `specs/mcp/states.md` RULE-58, and `specs/export/package.md` RULE-3, each if Q11 removes trust.
- **Acceptance:** `dev/test_init_scaffold.py`, `dev/test_init_update.py`, `dev/test_config_engine.py`, `dev/test_skills.py`, `dev/test_consumer_ci.py`, `dev/test_signatures.py`, `dev/test_export.py`, `dev/test_mcp_server.py`, `bash dev/test_init_e2e_gates.sh` and `bash dev/test_init_e2e_wiring.sh`.
- **Questions:** Q11, Q12, Q13, Q15, Q10.

### L19 `first-test-run` (70: the test command)

- **Decision:** "How the tests are run is settled at the first test run: `purlin:build` sets it when it writes the tests, and where tests already exist Purlin suggests a command, the user confirms, and it runs at once."
- **Design to hand the agent:** the run script never reads stdin (its own docstring says so). With no `tests` setting it prints what it found and a suggested command in a fixed form, writes nothing, and exits. The test and build skills ask the person, write the setting through a non-interactive form of `scaffold.py` (`--add <framework>`, and a new `--command <cmd> --report <path>`), and run again.
- **Code:**
  - `scripts/run/purlin_run.py`: the no-suite path, and a check for pending upgrade migrations before any suggestion.
  - `scripts/mcp/purlin/frameworks.py`: the suggestion.
  - `scripts/init/scaffold.py`: `COMMAND_QUESTION`, `REPORT_QUESTION`, `asked_suite` and `format_for` move to the non-interactive form. They are moved, not copied.
- **Skills:** `skills/test/SKILL.md` (at its 120-line limit) and `skills/build/SKILL.md` (at its 130-line limit).
- **References:** `references/supported_frameworks.md`, `references/purlin_commands.md`, and the "The `tests` setting" section of `references/formats/marker_format.md`. That last change is wording about who writes the setting, so no version change.
- **Specs:** `specs/run/run_script.md` RULE-3, plus new rules; `specs/init/scaffold.md` RULE-6 and RULE-32; new rules in `specs/skills/skill_test.md` and `skill_build.md`.
- **Acceptance:** `dev/test_run_script.py`, `dev/test_init_scaffold.py`, `dev/test_skills.py`, `bash dev/test_init_e2e_gates.sh` and `bash dev/test_init_e2e_wiring.sh`.
- **Questions:** Q13, Q14, Q10.

### L20 `commit-together` (70: committing with the results)

- **Decision:** "A test run that commits its results commits the rules, the marked tests and the settings they describe in the same step, and lists each file."
- **Code:**
  - `scripts/run/evidence.py`: `commit_local` and `commit_paths` stage the specs, the marked test files and `.purlin/config.json` of the features run, and print each file.
  - `scripts/run/purlin_run.py`: the call, and the `_nothing_to_run` path.
- **Skills and references:** `skills/test/SKILL.md` Step 2 and `references/commit_conventions.md`.
- **Specs:** `specs/run/evidence_writer.md` RULE-9 and RULE-10, and `specs/skills/skill_test.md` RULE-5.
- **Acceptance:** `dev/test_evidence_writer.py`, `dev/test_run_script.py`, `dev/test_skills.py`, `bash dev/test_init_e2e_gates.sh`.
- **Questions:** Q21, Q22.

### L21 `spec-from-code` (the product parts of 66 and 72)

- **Decision 66:** "Every source file belongs to some feature's rules. Rules say what a user or a caller can see; an internal helper is covered by the rule of the behaviour it serves and gets no rule of its own. Every test the project already had is tied to a rule, unless the report says why not ... A test that was failing before is never made to pass by writing the rule to fit it."
- **Decision 72:** "Where existing code has a test that was already failing, `purlin:spec-from-code` writes the rule from what the test expects and leaves it failing."
- **Skill:** `skills/spec-from-code/SKILL.md`, now 106 lines against a limit of 130. "The honest limit" is rewritten, the Procedure's step 6 "Report" changes, and "What not to do" changes.
- **Specs:** `specs/skills/skill_spec_from_code.md` gets RULE-7 (every source file is in some `> Scope:`), RULE-8 (every existing test is tied or reported with a reason) and RULE-9 (a failing test: the rule is written from what the test expects, the test is left failing, and no test or code is edited). RULE-6 is squared with RULE-8: a partly matching test is reported with its reason.
- **Code:** only if Q36 chooses a tool, a lister under `scripts/`.
- **Acceptance:** `dev/test_skills.py`.
- **Questions:** Q36, Q37, Q38.

## 2. The overlaps, and the order

The shared files. A lane is listed where it writes the file.

| File | Lanes |
|---|---|
| `scripts/mcp/purlin/status.py` | L1, L3, L8, L12, L18 |
| `scripts/mcp/purlin/board.py` | L1, L3 |
| `scripts/mcp/purlin/states.py` | L3, L4, L7, L16 |
| `scripts/mcp/purlin/payload.py` | L3, L4, L8, L16 |
| `scripts/mcp/purlin/evidence.py` | L7, L12 |
| `scripts/run/purlin_run.py` | L3, L8, L9, L12, L16, L19, L20 |
| `scripts/run/evidence.py` | L7, L11, L20 |
| `scripts/run/reports.py` | L8, L9 |
| `scripts/run/workflow.py` | L13, L18 |
| `scripts/ci/gate_check.py` | L5, L16 |
| `scripts/review/sign.py` | L1, L6, L16, L17, L18 |
| `scripts/export/package.py` | L6, L16, L17, L18 |
| `scripts/init/scaffold.py` | L5, L13, L16, L18, L19 |
| `scripts/init/update.py` | L10, L18 |
| `scripts/report/src/*.js` and both built pages | L1, L3, L4, L12, L16 |
| `dev/fixtures/report/*.json` | L3, L4, L16 |
| `templates/config.json` | L13, L18 |
| `references/formats/package_format.md` | L6, L16, L18 |
| `references/formats/marker_format.md` | L9, L11 |
| `references/hard_gates.md`, `glossary.md` | L1, L3, L5, L6, L16, L18 |
| `skills/test`, `skills/status`, `skills/sign`, `skills/build`, `skills/init` | L3, L6, L8, L18, L19, L20; L1, L3, L6, L8; L1, L6, L16, L17, L18; L9, L14, L19; L5, L16, L18 |
| `specs/mcp/states.md` | L1, L3, L4, L7, L8, L12, L16, L18 |
| `specs/dashboard/purlin_report.md` | L1, L3, L4, L12, L16 |
| `specs/run/run_script.md` | L3, L8, L11, L12, L19 |
| `specs/review/signatures.md` | L1, L6, L16, L17, L18 |
| `specs/init/scaffold.md` | L5, L13, L16, L18, L19 |
| `dev/test_skills.py` | L3, L6, L8, L9, L14, L16, L17, L18, L19, L20, L21 |
| `dev/test_mcp_server.py` | L1, L3, L4, L7, L8, L12, L16, L18 |
| `dev/test_run_script.py` | L3, L7, L8, L9, L11, L12, L19, L20 |
| `dev/init_e2e_walk.sh` | L1, L3, L16, L17, L18, L20 |

**Merged lanes.** 62 and 67 are one lane (L16). The two security parts of 65 are one lane (L15). Decisions 60 and 68 rewrite the same lines, so they are carried together in four lanes that run one after another: L3 (the summary), L4 (the new box and the description), L5 (the runner) and L6 (the phrase sweep).

**The order.** Lanes on the same line run together; a line waits for the one above it.

| Wave | Lanes |
|---|---|
| 1 | L1 `queue-words` and L2 `azure-branch` |
| 2 | L3 `summary` and L15 `security-names` |
| 3 | L4 `no-proof-box` and L10 `update-cache` |
| 4 | L11 `foreign-not-run` and L21 `spec-from-code` |
| 5 | L7 `one-answer` and L14 `skill-endings` |
| 6 | L8 `next-by-cause` and L13 `host-line` |
| 7 | L9 `near-miss` and L5 `remote-check` |
| 8 | L12 `linux-unix` and L17 `sign-version` |
| 9 | L16 `signatures` alone |
| 10 | L18 `init-one-question` alone |
| 11 | L19 `first-test-run` alone |
| 12 | L20 `commit-together` alone |
| 13 | L6 `gate-phrase` alone |

Why this order:
- L1 comes before L3, because `Left to do` uses the queue's words.
- L3 comes before L4, L5, L6 and L8, which render its summary.
- L11 comes before L7, which reads the corrected word.
- L14 comes before L9 and L19, which also edit the build skill.
- L8 comes before L19, which relies on the stop when the settings file is missing.
- L18 comes before L19 and L20.
- L6 is last because it is a sweep.
- If Q37 answers "run the tests first", L21 moves to after L19. L14 then pairs with L11 in wave 4, and L7 runs alone in wave 5.

## 3. Questions for the owner

Most basic first. Each one says what the thing is for, asks the question, and gives the options.

**Q1. The summary line.** After a run, in the status and on the dashboard, one line says how far the rules have got. Decision 68's example is `35 pass their tests. 30 are strong. 20 are signed.` Does it also say how many rules there are?
- (a) No totals, as in your example. At `passed` only the first sentence shows, at `strong` two, at `signed` three. A reader who wants the total reads the table.
- (b) The total first: `40 rules. 35 pass their tests. 30 are strong. 20 are signed.`
- (c) Each step out of the rules asked for it: `35 of 40 pass their tests. 30 of 33 are strong. 20 of 25 are signed.`
- (d) Remove the line. The table and `Left to do` carry it.

**Q2. `Left to do`.** It says whether a version is finished, by naming the work left. Which kinds does it name, in what words?
- (a) One item per kind of work, in the order the work runs, leaving out any at zero: `Left to do: 2 rules to write a test for, 1 failing test to fix, 3 rules to run again, 1 rule to write a proof for, 5 rules to audit, 1 weak rule to strengthen, 1 rule to test by hand, 10 rules to sign.` At `passed` only the test items can appear.
- (b) One item per step: `Left to do: 4 rules to pass their tests, 5 to audit, 10 to sign.`
- (c) (a) in the terminal and (b) on the dashboard.
- (d) Remove it. The `Next:` line says the first thing to do.

**Q3. What a test run and an audit end on.** Today a test run ends on `Tests: 35 of 40 rules pass.` and a gate line, and an audit ends on `Audit: 3 strong, 1 weak.` and the gate line.
- (a) Both end on the summary and `Left to do`. The audit keeps its earlier line `AI audit: 4 rules read, 3 strong, 1 weak.` above them.
- (b) As (a), and the audit also keeps `Audit: 3 strong, 1 weak.`
- (c) Both end on the `Next:` line alone.

**Q4. Rules marked to need less than the gate.** A rule can be marked to need only its tests at the gate `signed`. It is finished once its tests pass. Where does it count in the summary, in `Left to do` and in the `No tag` line?
- (a) It counts in the steps it is asked for and is left out of the steps above its level ("30 are strong" counts only rules asked to be strong). It never appears in `Left to do` once its own level is reached.
- (b) Once it reaches its own level, it counts as having reached every step.
- (c) It has its own line: `5 rules need their tests only, and pass them.`
- (d) Remove it from the summary. Only the table shows it.

**Q5. What fails the remote runner's job.** A runner reruns the tests on a clean machine, for a run branch or for a pushed signed tag. Decision 68 says the job fails only when a test fails or could not run, and prints no `PASS` or `FAIL`. Decision 60 said the CI check "still says pass or fail". Today a tag run also fails when a signature no longer matches the tagged code, or when a result file in the runner's folder was written by a person.
- (a) Only a test failing or not running fails either kind of run. On a tag run the other two problems are printed and do not fail.
- (b) A run branch fails only on tests. A tag run also fails on a signature that no longer matches, or a result file a person wrote there, because the tag claims the version is proven.
- (c) Remove the tag run's extra checks. A tag run only reruns the tests.

**Q6. The dashboard's existing boxes, and where `Left to do` goes.** The boxes count rules at each step (Untested, Failing, Partial, Passing, Strong, Signed), with the Queue and Stale cards beside them. Today a step box below the project's gate reads amber even when every rule is fine. The `N of M rules meet the gate` chip goes (decision 60). Putting `Left to do` above the boxes would bring back a line decision 57 removed.
- (a) The boxes stay. A step box is green when every rule asked for that step has reached it, amber otherwise. `Left to do` is one line under the boxes.
- (b) The boxes and their colours stay as today. `Left to do` sits in the top bar where the count chip was.
- (c) The boxes stay. Only Failing (red) and Partial (amber) are coloured. `Left to do` is not on the dashboard.
- (d) Remove the step boxes. The board shows `Left to do` and the table.

**Q7. The no-proof box.** From `strong` up, a rule asked for the audit needs a proof. A rule with none blocks the version, and nothing on the board counts it today.
- (a) A `No proof` box among the step boxes, with a filter of the same name. It counts only rules whose level asks for a proof. A rule with neither proof nor test counts here and not in Untested.
- (b) A card beside Queue and Stale, with the same filter. The rule also stays in its step box as today.
- (c) Remove the box and keep the filter only.

**Q8. The description under a feature's name.** A spec may carry a `> Description:`. Some in this repository run to 10 lines.
- (a) The full text, muted, under the name. The row grows.
- (b) The first sentence under the name, the full text on hover.
- (c) Shown only when the row is opened, above its rules.
- (d) Remove it. It is not shown, and the spec format stops saying the dashboard shows it.

**Q9. The queue's remaining words.** Decision 61 fixed `To test by hand <h> · To sign <s>` and the two full sentences. Still open are the terminal line, the `Next:` reason, the queue tab's heading, the word in each row's "Needs" column, and the card at `strong`. The proposal:
- Terminal: `Queue: To test by hand 1 · To sign 2.`
- `Next:` line: `→ Next: run purlin:sign. 3 rules are waiting for someone to test by hand or to sign.`
- Tab heading: `Queue`, with the two labels beneath.
- Row words: `test by hand` and `sign`.
- Empty queue: `Nothing is waiting for someone to test by hand or to sign.`

The options:
- (a) As proposed, and the Queue card also shows at `strong`, where hand checks exist.
- (b) As proposed, with the card at `signed` only, as today.
- (c) As proposed, but the row words stay `hand check` and `signature`.
- (d) Remove the counting line from the terminal. The `Next:` line alone names the queue.

**Q10. The length limits on each command's instructions.** Each command's written instructions have a maximum length so they stay quick to follow. Build, init, status, test and audit are at their maximum, and so is the agent file; sign is 1 line short. Several decisions add instructions to them.
- (a) Raise each limit by what its change needs, up to 20 lines.
- (b) Keep the limits. Each change cuts as many lines as it adds.
- (c) Remove the length rules.

**Q11. Trust.** Setup asks "Do you trust your own machine for the tests and the signing?" A no makes signing refuse any rule whose tests have not run on the remote runner, and writes a runner. Decision 70 says setup asks one thing. The upgrade from 0.9.5 asks the same question.
- (a) The question goes from setup and from the upgrade. The setting stays, `local` unless you edit the settings file.
- (b) The question, the setting and the refusal all go. Your own runs always count, and a runner is written only for a proof that needs another operating system.
- (c) The question moves to the first time the gate is raised to `signed`.

**Q12. Breaking the code on purpose.** At `strong` and `signed`, Purlin can change the code on purpose to see whether the tests notice. It is slow and needs a tool installed.
- (a) Setup asks only when the chosen gate is `strong` or `signed`, and again when the gate is raised to one of them. The upgrade asks the same way. At `strong`, setup therefore asks two things.
- (b) Setup never asks. The first audit asks.
- (c) Remove the question. It stays off unless turned on by a flag or the settings file.

**Q13. The test command at setup.** The settings file holds the command that runs the project's tests. Today setup writes it for a framework it recognises, and asks when it recognises none.
- (a) Setup never touches it. The first test run settles it, even for a recognised framework, with one confirmation.
- (b) Setup still writes it silently for a recognised framework. Only the unrecognised case moves to the first test run.
- (c) Nothing is asked when a framework is recognised: the first run uses its command at once. It asks only when nothing is recognised.

**Q14. The first test run when tests exist and no command is set.** Decision 70 says Purlin suggests a command, you confirm, and it runs at once. What does it ask?
- (a) "Your tests look like pytest. Run them with `python3 -m pytest ...`? [Y/n]". The suggestion comes from a fixed list per framework, and test files are also recognised by their usual names. When nothing is recognised, it asks for the command in plain words, with examples.
- (b) Claude reads the project and proposes a command, for example from a Makefile. You confirm.
- (c) It always asks, and lists the usual commands to pick from.
- (d) No suggestion. The run stops, says no command is set, and names `purlin:init`.

**Q15. The upgrade's rehearsal.** `purlin:init --update --dry-run` lists what an upgrade from 0.9.5 would change and changes nothing. Decision 70 removes `--dry-run` from setup.
- (a) Keep it for the upgrade only.
- (b) Remove it too. The upgrade already asks before each change.
- (c) Remove the flag, and have `purlin:status` list each pending change of the upgrade.

**Q16. The missing test command in a 0.9.5 project.** A 0.9.5 project that has not been upgraded has no test command set. The first test run could suggest one, or send you to the upgrade.
- (a) It sends you to `purlin:init --update` first and suggests nothing.
- (b) It suggests a command anyway.

**Q17. Naming the rules.** When rules fail or have no test, the run names each one.
- (a) After the table, one line per kind: `Failing: login RULE-3, cart RULE-1.` At most 10 names per line, then "and N more".
- (b) In the `Next:` line, naming the first 3.
- (c) Both.
- (d) Remove the names. They show only in `purlin:status <feature>`.

**Q18. When a comment names nothing.** A comment above a test ties it to a rule. A typo leaves the rule with no test.
- (a) `→ Next: run purlin:build cart. The comment at tests/test_cart.py:12 names carts, which no spec has.` Build repairs comments.
- (b) `→ Next: correct the comment at tests/test_cart.py:12, then run purlin:test.`
- (c) Remove the special advice. The run's file-and-line error is enough, and the `Next:` line stays general.

**Q19. The settings file missing.** Decision 69 says the run stops, says so, names the command that restores it, and writes nothing. What exit code?
- (a) Exit 1, with `No .purlin/config.json here, so nothing ran. Run purlin:init to write it again.`
- (b) Exit 2, as for a wrong command line.
- (c) Remove the check and run as if the file were empty. This is today's behaviour, which overwrote good results with "no test".

**Q20. Nearly right comments.** For example `# purln: cart PROOF-1`, `# Purlin: ...`, or `# purlin:cart PROOF-1` with no space. Today the run prints some of these and ignores others.
- (a) "Nearly right" means: the word misspelled by one letter or in capitals, no space after the colon, or a `purlin:` comment whose rest cannot be read. Build lists each one, proposes the fix, asks, and then edits. The run prints none of them.
- (b) As (a), but the run keeps printing the `purlin:` comments it cannot read.
- (c) As (a), and build also fixes a well-formed comment whose feature or proof is one letter off a real one. The run still fails on those (decision 56).
- (d) Remove the search. The docs show the exact form.

**Q21. Committing with the results.** Today `purlin:test --commit` commits only the result files.
- (a) One commit with the rules, the marked tests, the settings and the results. The results then describe work that was not committed when the tests ran (see Q22).
- (b) Two commits in one step: first the rules, the tests, the settings and the code those specs name, then the results, which name the first commit. No rerun.
- (c) Two commits and a rerun: commit the work, run the tests again on the clean tree, commit the results.
- (d) Remove committing from the run. You commit by hand.

**Q22. "Every result came from committed work."** The signed tag says a version is proven. Results from edits that were never committed prove nothing about any commit.
- (a) Results count toward the tag only if the run was on a tree with no uncommitted change outside Purlin's own folder. The refusal reads: `No tag: login's results came from work that was not committed. Commit it, then run purlin:test login.`
- (b) Results count when the spec, code and tests they were taken over are identical to what the tagged commit holds. Today's rule already checks this, so nothing new is added.
- (c) As (a), but only that feature's own files must have been committed.
- (d) Remove the check. The package notes that a run was on uncommitted work.

**Q23. The version.** The tag is `signed/<version>`. With no version file today, a new project's first tag takes Purlin's own version.
- (a) Only a `VERSION` file at the root counts. Signing asks, offers to write the file, and commits it with the package.
- (b) Also read the version the project already states in `package.json`, `pyproject.toml` or a `.csproj`. Ask only when none does.
- (c) Ask each time, and never write a file.
- (d) Remove the version from the tag: name it by date and commit.

**Q24. What makes a signature count.** Decision 67: any SSH key counts, and Purlin records the key and does not ask whose it is.
- (a) Purlin checks that the signature really belongs to that commit and was not copied or altered. It never asks whose key it is. This needs `ssh-keygen`, which ships with Git. If `ssh-keygen` is missing, the signature does not count and the line says why.
- (b) Purlin checks only that a signature is present.
- (c) As (a), and GPG keys count too.
- (d) Remove the check. A committed signature file counts, and the commit's key is recorded when there is one.

**Q25. What a signature records.** Today it records the email, the time, the signing machine's name and its operating system.
- (a) The email, the name git holds, the time and the key's fingerprint. The machine and its system go.
- (b) As (a), and keep the machine and system as logged extras.
- (c) The email, the time and the fingerprint only.

**Q26. The check before signing.** Decision 67 says Purlin confirms only that there is a key to sign with.
- (a) Check that git names a signing key and that the key file exists. When it does not, print the one-time setup: `ssh-keygen -t ed25519` (only when there is no key file), `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub`.
- (b) As (a), and setup at `signed` prints the same lines, as today.
- (c) Check only that a key is named, and print the two git commands.
- (d) Remove the check. A signing that fails shows git's own error.

**Q27. What the walk prints after signing.**
- (a) `Signed 3 rules in a1b2c3d with the key SHA256:Xy…. Purlin records the key and does not check whose it is.`, then the tag, or `No tag` with `Left to do`.
- (b) As (a) without the second sentence.
- (c) Show the key only on the dashboard and in the package.
- (d) Only `Signed 3 rules in a1b2c3d.`

**Q28. How you are told that a code change ended signatures.** A change to any file a feature lists now ends every signature in that feature.
- (a) The test run that finds them prints `This change ends 4 signatures in login: RULE-1, RULE-2, RULE-3, RULE-5. Run purlin:sign once the tests pass.` Status and the dashboard show them stale, with the reason `code changed after the signature`.
- (b) Status and the dashboard only.
- (c) As (a), and `purlin:build` warns before it edits a file under a signed feature.
- (d) No line. They show up in the queue again.

**Q29. Which change to where the tests ran ends a signature.** A signature now binds the operating systems its results came from. A remote runner always adds a Linux run.
- (a) Any change ends it, including a new system. A first `purlin:test --remote` after signing on a Mac ends every signature.
- (b) Only losing a system, or a system's result changing, ends it. A new passing system does not.
- (c) The signature binds the systems that had run when it was signed, and later runs elsewhere are not read for it.
- (d) Remove the binding. The systems are recorded only.

**Q30. The code a shared rule binds.** A shared (anchor) rule lists no files. Its code lives in the features that use it.
- (a) It binds no code, so a code change never ends its signature.
- (b) It binds the files of every feature that requires it. For a global anchor, that is every feature's files.
- (c) Remove signing for shared rules: they can be marked to need at most the audit.

**Q31. The package's counts and states.** The data file handed to the regulated system carries "rules meeting the gate" counts and the state `gate <gate> met`.
- (a) Keep them. A machine reads them, and no person sees them.
- (b) Rename them to the steps and a `Left to do` list, with the state `finished` in place of `gate <gate> met`.
- (c) Remove the two counts and keep the state.

**Q32. The check on the runner's own result files.** At a tag run, Purlin checks that each result file in the runner's folder was committed by the runner, so nobody can pass off their own results as the runner's. Decision 67 says Purlin polices nothing about signing.
- (a) Keep it. It checks results, not people.
- (b) Remove it.
- (c) Keep it, print only, and never fail the job (goes with Q5 (a)).

**Q33. How the operating systems are shown.** Results are filed under windows, macos and linux. Decision 65 shows linux as `Linux/Unix`.
- (a) `Windows`, `macOS` and `Linux/Unix` wherever a person reads them. The small boxes read `Win`, `Mac`, `Lin`.
- (b) Only linux changes.
- (c) The full names in the boxes as well.

**Q34. A git host that is neither GitHub nor Azure DevOps.** The proposed line: `The origin remote is neither GitHub nor Azure DevOps. Everything on this machine works with any host; only purlin:test --remote needs one of those two.` The settings today default to `ci: github` even then.
- (a) That line, and no `ci` setting when no host is read.
- (b) That line, and `ci: none`.
- (c) That line, and keep `github` as today.
- (d) Remove the line. It is printed only when a runner is wanted.

**Q35. The next command at the missing endings.**
- (a) Build:
  - "rules still have no test": `→ Run: purlin:build <feature>`
  - a hand-checked proof: `→ Run: purlin:sign <feature> RULE-<n> --note "<what you saw>"`
  - another operating system: `→ Run: purlin:test --remote`

  Anchor:
  - "no feature requires it yet": `→ Run: purlin:spec <feature>`
  - "pin current, nothing moved": `→ Run: purlin:status`
- (b) As (a), but "nothing moved" gives `→ Run: purlin:drift`.
- (c) Remove the two anchor endings.

**Q36. Every source file covered.** After `purlin:spec-from-code`, every source file should belong to some feature.
- (a) A tool lists every tracked file that no feature lists, skipping tests, specs, docs and generated files. The report names each one with a reason.
- (b) Claude checks by reading, and the report says it did.
- (c) Remove the check from the skill. Status and drift show unlisted files later.

**Q37. Knowing which tests were failing before.**
- (a) The skill runs the project's tests once before writing anything. That needs the first-test-run mechanism, so the lane moves to after it. Rules for failing tests are written from what the test expects and listed as "left failing".
- (b) Every rule is written from what its test expects, and no test or code is ever edited. The first `purlin:test` shows which fail, and the report says so.
- (c) Remove this: existing tests are not read for rules.

**Q38. Tests left untied.**
- (a) Allowed reasons: the test shows only part of a proof, it duplicates a tied test, or it tests code the project does not own. The report lists each test with its reason.
- (b) No reasons are allowed. Every test gets a rule.
- (c) The report gives only the count of untied tests.

## 4. What the clean-release rule (decision 44) deletes, lane by lane

- **L1:**
  - `needs_a_person` and every "need a person" and "waiting for a person" string.
  - The `Hand checks <h> · Signatures <s>` label line.
  - The old `Queue: <n> rules. <h> hand checks, <s> signatures.` format.
  - drift.py's second copy of the queue line.
- **L2:** the second branch reader (`current_branch` goes into `ref_branch`), and the order that read `BUILD_SOURCEBRANCHNAME` first.
- **L3:**
  - `board.headline`, `gate_line`, and the `gate <gate> met` / `not met` lines.
  - `tests_line` if Q3 (a) or (c).
  - The count chip and its per-level hover in `gateChips`.
  - `reached()` (the page stops adding up counts itself).
  - `summary.met` and `rollup.met` if nothing reads them.
  - `NOTHING_BLOCKS`'s suffix.
  - The terminal's one-count-per-rule bucket line.
- **L4:** the Untested hover text that folded in "no proof written", under Q7 (a).
- **L5:**
  - `PASS.` and `FAIL.`, `result` in `--json`, and the exit rule "1 the gate is not met".
  - The "fails when the gate is not met" comments in both templates and in this repository's own workflow.
  - scaffold RULE-42's clause.
  - `_ENFORCEMENT_NOTE`'s "meets it".
- **L6:**
  - Every "meets the gate" and "meet the gate" in code, skills, references and the agent file.
  - `NO_TAG_SHORT` as written, and `TAGGED`'s wording.
  - The tag message `Every rule meets the gate`.
  - The package's `gate <gate> met` and its counts, if Q31 (b) or (c).
- **L7:** `proof_results` dropping skipped tests, and `.purlin/tests.md` counting a skipped test under "No test".
- **L8:** `_said`'s count-only reasons, and `NO_SUITES` saying the file "names no tests" when it is missing.
- **L9:** `malformed_lines` and `NOT_A_MARKER` in the run, and marker_format's "reported as not a marker".
- **L10:** the code that untracked the cache and kept it on disk.
- **L11:** `missing` for a foreign proof whose test was skipped.
- **L12:** `host_os`'s `return sys.platform` fallback.
- **L13:** `UNKNOWN_HOST` as written, and the `ci: github` default if Q34 (a) or (b).
- **L14:** nothing.
- **L15:** the name `TOKEN_VARIABLE`, and the test pattern that matched only names ending in the word.
- **L16:**
  - `commit_is_signed` and the `%G?` read for signatures, and the reason `the signing commit is not signed`.
  - `commit.gpgsign true` in the setup lines.
  - `machine_name()`, and the signature's `machine` and `os` fields, if Q25 (a) or (c).
  - The package's `commit_verifies`.
  - signature_format's "Changing the code alone stales nothing".
  - states RULE-47's machine and os, and signatures RULE-50.
  - The allowed-signers setup in the signature tests.
- **L17:** the fallback to the version in the config (`project_version`, `package.py` line 14), and the tag name `signed/unversioned`.
- **L18:**
  - `--dry-run`, `Plan.dry_run`, scaffold RULE-30, and RULE-33's `--dry-run` half.
  - The `specs/_anchors` creation.
  - The trust question and its texts: `TRUST_QUESTION*`, `TRUST_LOCAL*`, `TRUST_REMOTE*`, `trust_words`, `ask_trust`, update's `_ask_trust`. If Q11 (b), also the `trust` setting, `untrusted`, `has_a_ci_run`, `NO_CI_RUN`, `TRUST_REASON*`, the trust branch in status, and the package's `trust`.
  - update's copy of `GATE_QUESTION`, and `--check` if Q15 (b) or (c).
  - `NO_ENGINE` at `passed`.
- **L19:** the interactive `COMMAND_QUESTION`, `REPORT_QUESTION` and `NO_COMMAND` in setup (moved, not copied), and `NO_SUITES`.
- **L20:** the evidence-only commit path.
- **L21:** the "A bug becomes a rule if you are not careful" framing.

## 5. Risks

### Decisions that contradict each other

- **60 against 68.** 60: "The CI check still says pass or fail." 68: "no `PASS` or `FAIL` word is printed" and "the job fails only when a test fails or could not run". 68 also weakens decision 31's "the tag run ... ends with the gate check" and scaffold RULE-42. A hand-made `signed/*` tag would then pass its tag run (Q5).
- **70 against itself.** "A test run that commits its results commits the rules, the marked tests and the settings ... in the same step" against "A signed tag is written only when every result came from committed work". Results committed in the same commit as the work were taken over uncommitted files, so the tag would refuse until a rerun (Q21, Q22).
- **70 against itself, and against 48.** "Setup asks one thing" against "The question about breaking the code on purpose is asked only at the gates where it runs", which makes two questions at `strong`. And 48 says "`trust: remote` stays as a project's own setting", while nothing would ask for it any more (Q11, Q12).
- **62 against 48.** 62: "the machine and operating system were recorded and bound nothing. A signature still belongs to no machine." 48: "every signature records the machine's name and its operating system". 67 lists only name, time and fingerprint (Q25).
- **62 against 31, and against states RULE-4.** Binding "the operating systems its test results came from" meets decision 31's "local counts everywhere" and states RULE-4's "what a signature locks is the evidence rather than the machine that produced it". Every runner job starts with a Linux job, so a first remote run after signing on a Mac ends every signature under Q29 (a).
- **72 against the anchor exemption.** "A signature's code is the files its feature lists": an anchor lists none, and states RULE-63 and sign.py exempt anchors from naming files (Q30).
- **67 against 31.** 67, "Purlin ... polices none", against decision 31's tag run, which checks that the runner's own identity committed each `ci/` file (Q32).
- **69 against 56.** 69, "a test run does not look for them" (nearly right comments), against 56, "A marker that names a feature, a proof or a rule no spec has fails the run". A well-formed comment with a misspelled feature is both. 56 should hold and 69 cover only shapes the run cannot read (Q20).
- **68 against 57.** A `Left to do` line on the dashboard brings back a line above the tiles that 57 removed ("The two headline lines above the tiles go") (Q6).
- **65 against the anchor skill's own ending.** 65's "every ending names a command" against the anchor skill's "say so in one line and stop" (Q35).
- **66 against spec_from_code RULE-6.** 66's "every test ... tied to a rule, unless the report says why not" against RULE-6's "leave it unmarked". L21 resolves this with a reported reason.
- **The length limits against every lane that adds instructions** (Q10).
- **Decision 44 against the existing table.** `dev/test_vocabulary.py` is a table of removed words, which 44 forbids. It stays until the final sweep, and no lane adds to it.

### A consequence to tell the owner

After L7, a test tied to a rule that is skipped on purpose, without an `@env` tag, keeps that rule from passing forever. The only ways out are to remove the comment, tag the proof `@env`, or run the test. This is what decision 69 asks for, but the docs phase must say it.

### The upgrade from 0.9.5

- **The list of who may sign.** 0.9.5 had no signatures and no such list. `git show v0.9.5:templates/config.json` carries no signer key, and nothing under `v0.9.5:scripts` signs. So there is nothing to move and nothing to drop, and Q11 needs no migration either, because 0.9.5 had no `trust` key.
- **The cache (L10).** Deleting `.purlin/cache/` is safe: 0.9.5 wrote it and nothing reads it now. The upgrade fixture carries it, so the test covers the case.
- **The rehearsal (L18).** Removing `--dry-run` from the upgrade removes the only way to preview an upgrade of a real 0.9.5 project (Q15).
- **The first test run (L19).** A 0.9.5 project that has not been upgraded has no `tests` setting. The first-test-run path would suggest a command instead of sending the user to `purlin:init --update`. L19 must check for pending upgrade changes first (Q16).
- **The upgrade's questions (L18).** `update.py` asks the gate, the mutation question and trust (update RULE-12 and RULE-26). Decision 70 changes all three, and update RULE-10's list of eight keys changes if Q11 (b).
- **The workflow (L5).** The upgrade replaces the 0.9.5 workflow with the new template. A runner job that used to go red when the gate was short will now go green, which a 0.9.5 user may rely on (Q5).
- **The version (L17).** 0.9.5 configs carry `"version": "0.9.2"` or `"0.9.5"`. Dropping the config fallback stops a tag named for an old Purlin version, and such projects will be asked for a version at their first signing.
- **The dashboard (L3, L4, L16).** Each of these lanes raises the payload schema. An old data file shows the "run purlin:status" notice until it is written again, which is harmless.

### Critical files for implementation
- /Users/richlabarca/LocalCode/purlin/scripts/mcp/purlin/status.py
- /Users/richlabarca/LocalCode/purlin/scripts/run/purlin_run.py
- /Users/richlabarca/LocalCode/purlin/scripts/review/sign.py
- /Users/richlabarca/LocalCode/purlin/scripts/mcp/purlin/signatures.py
- /Users/richlabarca/LocalCode/purlin/scripts/init/scaffold.py
