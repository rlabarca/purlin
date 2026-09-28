# The product changes of decisions 60 to 82, cut by ownership of files

Written by a planning agent on 2026-09-28. Two steps run alone first, 13 lanes run together,
one cleanup step runs alone, then integration. Section 2 is the contract between the lanes:
every agent writes to it and none chooses. The answers to section 5 are decision 83 in
`three-levels.md`.

## 0. Rules for every lane

- **Worktree and branch.** Each lane runs in `/Users/richlabarca/LocalCode/purlin-wt/<name>` on branch `<name>`. Before merging it rebases on `main`, reruns its acceptance, and merges by fast-forward.
- **Files are single-owner.** A lane writes only the files it owns (section 1).
  - The shared test helpers created in P0a, `dev/skill_checks.py` and `dev/mcp_project.py`, are frozen after P0. A lane that needs a new helper puts it in its own test file.
- **No lane deletes a name another lane's file still uses.** It stops using the name in its own files. Step R (section 3) deletes every such name once the fan-out has merged. This applies to:
  - payload keys: `queue`, `met`, `meets_gate`, `need`, `level`, `level_marked`, `stale`, `hand_checks`, `asks_*`
  - `gate.TRUST_VALUES` and `gate.level_of`
  - the `trust` parameter of `workflow.wanted`
  - `scaffold.trust_question`
  - `board.queue_line`, `board.headline` and `board.needs_a_person`
  - `signatures.commit_is_signed`
  - the `frameworks` functions that only setup used
- **No lane stages generated files.** That means `scripts/report/purlin-report.html`, the root `purlin-report.html`, `.purlin/evidence/**`, `.purlin/tests.md` and `.purlin/report-data.js`. A lane may rebuild them locally to run its tests. Integration rebuilds and commits them once.
- **Proofs.** Every proof a lane writes or rewrites already meets decision 71: one starting situation, one action, at most 60 words, and a refusal or boundary as its own case. The other proofs are split in the next phase.
- **Instruction length.** Decision 80: "Each command's instructions keep their maximum length: a change cuts as many lines as it adds." The ceilings do not move:

  | File | Lines now / ceiling |
  |---|---|
  | status | 100/100 |
  | test | 120/120 |
  | build | 130/130 |
  | init | 250/250 |
  | audit | 105/105 |
  | sign | 184/185 |
  | export | 81/90 |
  | spec | 177/210 |
  | spec-from-code | 106/130 |
  | drift | 112/150 |
  | anchor | 96/160 |
  | `agents/purlin.md` | 135/135 |

- **Clean release (decision 44).** Each lane deletes outright what it retires. Nobody adds to `dev/test_vocabulary.py`. No test checks that a removed thing is absent. No reader accepts an old spelling.
- **Acceptance per lane:**
  - the lane's named test files, run whole with `.venv/bin/python -m pytest <files>`
  - `bash dev/run_tests.sh --fast`
  - `python3 scripts/run/purlin_run.py --test --all`, where every marker is tied and every rule the lane touched passes, with nothing committed
- **Shell suites.** The shell suites (`dev/test_init_e2e_*.sh`, `dev/test_e2e_*.sh`) exercise several lanes at once. Their owning lane rewrites them to the contract strings, and they are proven green at integration, not in the lane.

## 1. The lanes, by ownership

### P0a `split-tests` (alone, first, mechanical, no behaviour change)

**Splits `dev/test_skills.py`** into:
- `dev/skill_checks.py`: lines 1–325, the readers, checks and broken-copy helpers. It carries no marker and is not collected by pytest.
- One test file per spec:
  - `dev/test_skill_init.py`: from line 326, including `INIT_QUESTIONS`, `INIT_KEYS` and their helpers
  - `dev/test_skill_spec.py`
  - `dev/test_skill_spec_from_code.py`
  - `dev/test_skill_anchor.py`
  - `dev/test_skill_build.py`
  - `dev/test_skill_test.py`
  - `dev/test_skill_audit.py`
  - `dev/test_skill_sign.py`
  - `dev/test_skill_status.py` and `dev/test_skill_drift.py`, splitting the shared section at line 1712
  - `dev/test_skill_export.py`
  - `dev/test_purlin_agent.py`
- `dev/test_skills.py` is deleted.

**Splits `dev/test_mcp_server.py`** into:
- `dev/mcp_project.py`: lines 1–328, the `project` fixture and `_git`, `_write`, `_marked_tests`, `_commit_tests`, `_entry`
- `dev/test_specs_reader.py`: the specs markers, lines 329–728
- `dev/test_states.py`: the states markers, lines 729–2842 and 3119 to the end, with `_section`, `_audit`, `_strong`, `_five_bucket_project`, `_levels_project`, `_feature`
- `dev/test_mcp_server.py` keeps the server markers, lines 2843–3118, with `_rpc`.

**Moves the tests that sit in another spec's file:**
- The one `scaffold`-marked test in `dev/test_reports.py` goes into `dev/test_init_scaffold.py`.
- The 8 `gate_check`-marked tests in `dev/test_tag.py` go into `dev/test_gate_check.py`.
- The 4 `signatures`-marked tests in `dev/test_export.py` go into `dev/test_signatures.py`.

**Acceptance:** the full sweep has the same number of tests passing as before. `purlin_run.py --test --all` shows 1131 markers tied and 566 of 566 rules passing.

### P0b `summary` (alone, after P0a): the one summary and `Left to do`, plus the shared interfaces

It carries decisions 60, 68, 74 and 79 wherever Python prints the summary, and fixes every cross-lane interface of section 2.

**New files:**
- `scripts/mcp/purlin/summary.py`: the one implementation (section 2.3).
- `specs/mcp/summary.md`: new spec, `> Scope: scripts/mcp/purlin/summary.py`. It holds one rule each for:
  - the sentence
  - each wording rule
  - the order of kinds
  - leaving out kinds at zero
  - the line when nothing is left at each gate
  - one kind per rule
  - the step counts
  - `to test on <systems>`
  - `the version to tag`
- `dev/test_summary.py`.

**`scripts/mcp/purlin/payload.py`:**
- `SCHEMA_VERSION` goes to 10.
- New keys (section 2.2): `left`, `finished`, `last_line`, `summary.steps`, `summary.sentence`, `os_words`.
- New per-rule keys: `left`, `hand_checked`, `applies_to`, `code_hash`, `machines`, `audit.notes`.
- The docstring changes to match.
- Nothing is removed yet.

**`scripts/mcp/purlin/status.py`:** `sync_status` ends on `summary.ending(payload)`. The headline, `bucket_line`, the features/proof-lines line, the queue line, `marked_above_the_gate`, `next_step`, `_said` and the `→ Next:` and `→ Queue:` lines are deleted from status. The `→ Run: purlin:init --update` line stays, above the summary.

**`scripts/run/purlin_run.py`:**
- `tests_line`, `gate_line`, `last_lines`, `AUDIT_LINE`, `NOTHING_BLOCKS` and the test-strength line at the end of `_audit` are deleted. `project_counts` keeps only what the exit code reads.
- The run ends on `sync_status`.
- The audit prints its `AI audit: …` line and its could-not-audit lines, then `sync_status`.

**Interfaces:**
- `scripts/mcp/purlin/signatures.py`:
  - `is_current(signature, entry)` and `counts(project_root, signature)` take their final shapes. They keep today's behaviour. Every caller is updated: `states._binds`, `states._what_moved`, `payload._counted`, `gate_check.verify`, `purlin_run._audit`, `package._signatures`.
  - A new `signed_hash(entry)`.
- `scripts/mcp/purlin/evidence.py`: new `os_word(key)` and `os_short(key)`.
- `scripts/init/update.py`: new `set_up_by_095(project_root)` (section 2.7).
- `scripts/report/src/app.js`: `SCHEMA` becomes 10. The `schema_version` in `dev/fixtures/report/solo.json`, `team.json` and `regulated.json` becomes 10.
- `dev/skill_checks.py`: `undirected_outcome_problems` accepts exactly one outcome with no `→`, the one reading `Nothing left to do.` (decision 76).

**Specs:**
- `specs/mcp/states.md`:
  - RULE-37, RULE-38, RULE-55, RULE-58, RULE-60, RULE-67, RULE-68 and RULE-69 are deleted. What they covered is now the summary spec's.
  - RULE-27 (schema 10 and the new keys) is rewritten.
- `specs/run/run_script.md`:
  - RULE-11 becomes "every run ends on the status table, the summary and `Left to do`".
  - RULE-48 and RULE-54 become "the audit keeps one earlier line, `AI audit: <n> rules read, <s> strong, <w> weak.`, then the could-not-audit lines, then the status".
  - RULE-57's ending is reworded.

**Tests:** the proofs of those rules in `dev/test_states.py`, `dev/test_run_script.py` and `dev/test_queue.py` are rewritten.

**Acceptance:** `dev/test_summary.py`, `dev/test_states.py`, `dev/test_queue.py`, `dev/test_run_script.py`, `dev/test_signatures.py`, `dev/test_export.py`, `dev/test_gate_check.py`, then `bash dev/run_tests.sh --fast`.

### The fan-out: 13 lanes, all at once

#### L1 `core`: rule states and the status skill

**Owns:**
- `scripts/mcp/purlin/states.py`, `payload.py`, `status.py`, `board.py`, `summary.py`, `gate.py`
- `specs/mcp/states.md`, `specs/mcp/summary.md`, `specs/skills/skill_status.md`
- `skills/status/SKILL.md`
- `dev/test_states.py`, `dev/test_summary.py`, `dev/test_queue.py`, `dev/test_backing_tests.py`, `dev/test_failing.py`, `dev/test_skill_status.py`

**Changes:**
- **Decision 73, "Marking a rule lower, `[level: ...]`, goes":**
  - `rule_cells` gives every rule every cell up to the gate. `level_marked` is no longer read, and `_need` is deleted.
  - Rules deleted: RULE-10, RULE-46, RULE-50, RULE-52 and RULE-21's second half. RULE-11 and RULE-15 lose "where its level asks".
  - The board cells `strong_cell` and `signed_cell` read `<n> of <rules>`, and `asks_*` stops being read.
- **Decision 78:**
  - Quoted: "A proof marked `@manual` is checked by a person, who writes what they saw and signs, in one act, at any gate. That act stands for the test, the audit and the signature of the rule."
  - `hand_checked` is true when a counting current signature carries a note.
  - The strong cell's `manual test` is met by it, as today. At the gate `passed` the rule's kind is `to_test_by_hand` until it is checked.
  - RULE-16 and RULE-18 are rewritten. A new rule covers the check at the gate `passed`.
- **Decision 74, "The queue goes as a separate idea":** RULE-29, RULE-30, RULE-31, RULE-53 and RULE-54 are deleted. The queue list is still built until R.
- **Decision 76, "An anchor's rule is signed once in each feature it applies to … counts as signed when it is signed in every one of them":**
  - The signed cell of an anchor's own rule is met only when every consumer, meaning every feature for a global anchor, has a counting signature with that `applies_to`.
  - The signed cell of a rule listed under a consumer is met by that consumer's signature.
  - New rule. RULE-63 is rewritten.
- **Decision 77, "No message is printed when a change ends signatures; the rules return to `to sign`":** the signed cell of a signature that no longer matches reads `unsigned` with no reason, and `AUDIT_MOVED`, `HASHES_MOVED` and `_what_moved` are deleted. This is subject to open question 4. If the owner keeps the stale count, this item reverses.
  - RULE-20, RULE-22 and RULE-73 are rewritten.
  - RULE-47 loses `machine` and `os` and gains `signer_name` and `key_fingerprint`.
- **Decision 75, "The choice not to trust a developer's machine goes, with the setting":** `gate.resolve_gate` stops reading and returning `trust`, and the payload's `gate` loses it. `TRUST_VALUES` and `DEFAULT_TRUST` stay until R.
- **Decision 60:** `board.headline` is no longer called.
- **Status skill (decisions 68, 79, 74, 73):** `skills/status/SKILL.md` prints the summary and `Left to do`. Queue, level and "meets the gate" are gone. It stays within 100 lines.
  - skill_status RULE-2 changes to "prints the sentence and the `Left to do` lines `sync_status` returned".
  - RULE-3's next step is the first line of `Left to do`, or `Nothing left to do`.

**This repository's specs:** remove the 4 `[level: passed]` tags in `specs/mcp/states.md`, and the 1 in `specs/skills/skill_status.md`. The proofs that mention levels are rewritten in the text: states PROOF-12, 18, 25, 32, 59, 61, 69, 89, 90 and 92.

**Formats:** none.

**Deletes:** `_need`, `marked_above_the_gate` and `above_the_gate_line` (if P0b left them), `HAND_CHECK_WORDS` routing into the queue, and the level branches of `_bucket` and `_cell_blocks`.

**Acceptance:** the 6 owned test files, then `--fast`.

#### L2 `evidence`: writing and reading the evidence file

**Owns:**
- `scripts/run/evidence.py`, `scripts/mcp/purlin/evidence.py`, `scripts/mcp/purlin/fingerprint.py`
- `references/formats/evidence_format.md`
- `specs/run/evidence_writer.md`, `specs/mcp/evidence.md`
- `dev/test_evidence_writer.py`, `dev/test_evidence_reader.py`, `dev/test_fingerprint.py`

**Changes:**
- **Decision 65, a foreign proof "whose test is skipped here, is recorded in the evidence as `not run`, never `missing`":** in `build_section`, a proof whose `env` names another system and whose tied test did not pass or fail is written `not run`. evidence_writer RULE-3 is rewritten.
- **Decision 65, "A system that is not Windows or macOS is treated as `linux`":** `host_os()` returns `linux` instead of `sys.platform`, and `os_word` and `os_short` get their final words. mcp/evidence RULE-14 is extended, and a new rule covers the display words.
- **Decision 69, "A rule has passed only when every test tied to it ran and passed":**
  - `proof_results` keeps each proof's worst result, in the order `fail`, then `not run` (from `missing` or `not run`), then `pass`.
  - `rule_word` and `render_table` agree: `.purlin/tests.md` counts a rule as `Passed` only when every tied test passed.
  - A new rule goes in mcp/evidence. evidence_writer RULE-2 and RULE-8 are rewritten.
- **Decision 77:** each section gains `machine` and `hostname` (section 2.5).
- **Decision 80, "A run that commits makes two commits in one step: the rules, the marked tests and the settings, then the results, which name the first":** new `commit_work(project_root, paths)` and `commit_local(project_root, work_sha, removed)`, printing the lines in section 2.6. evidence_writer RULE-10 is rewritten and a new rule added.
- **Decision 75:** the audit entry gains optional `notes`, which is not hashed (section 2.5).
- `evidence_format.md` goes from Format-Version 3 to 4 and the schema string from `purlin-evidence/1` to `purlin-evidence/2`. The "tag run checks who committed each `ci/` file" paragraph is deleted.

**Deletes:** the `sys.platform` fallback; `missing` for a skipped foreign proof; the evidence-only `--commit` path.

**Acceptance:** the 3 owned test files, then `--fast`.

#### L3 `run`: the test run and the test skill

**Owns:**
- `scripts/run/purlin_run.py`, `scripts/run/reports.py`
- `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/frameworks.py`
- `references/formats/marker_format.md`, `references/supported_frameworks.md`
- `specs/run/run_script.md`, `specs/run/reports.md`, `specs/skills/skill_test.md`
- `skills/test/SKILL.md`
- `dev/test_run_script.py`, `dev/test_reports.py`, `dev/test_skill_test.py`, `dev/test_e2e_required_rules.sh`

**Changes:**
- **Decision 69, "A run names each rule that fails or has no test, and its advice fits the cause":** the run prints the problem lines of section 2.6 before the status, and `FIX_ONE`/`FIX_MANY` become the comment-advice line. New rule in run_script. reports RULE-19 is rewritten.
- **Decisions 69 and 80, missing settings:** "With the settings file missing, a run stops, says so, names the command that restores it, and writes nothing" and "A missing settings file ends a run with exit 1". New rule.
- **Decision 80, "In a project set up by 0.9.5 and not upgraded, a run stops and names the upgrade":** the run calls `update.set_up_by_095` before anything else. New rule.
- **Decisions 70 and 80, the first test run:**
  - Quoted: "The first test run in a project with tests and no command suggests one from a fixed list of test tools, and where it recognises none the AI reads the project and proposes one; the user confirms and it runs".
  - `frameworks.suggest(project_root)` returns the entry, and the run prints section 2.6's lines, writes nothing and exits 1.
  - `NO_SUITES` is deleted.
  - `skills/test/SKILL.md` asks the person, writes the entry with the `purlin_config` tool (key `tests`), and reruns. Where nothing was recognised, it reads the project and proposes an entry.
  - run_script RULE-3 is rewritten and 2 rules added. skill_test gets a new rule, and RULE-2 and RULE-5 are rewritten.
  - `frameworks.py` and `supported_frameworks.md` join run_script's `> Scope:`.
- **Decision 69, "a test run does not look for [nearly right comments]":**
  - `malformed_lines` and `NOT_A_MARKER` leave the run.
  - `markers.py` gains `near_misses(project_root, features)` and the command-line arm `--near-misses` (section 2.6), which `purlin:build` uses.
  - reports RULE-1 is rewritten. `marker_format.md` goes from 1 to 2: the "not a marker" report goes, and a skipped foreign test reads `not run`.
- **Decision 80, two commits:** `--commit` collects each spec of the features run, the test files carrying their markers, and `.purlin/config.json`, then calls `commit_work` and `commit_local`. skill_test RULE-5 is rewritten. In `skills/test/SKILL.md`, Step 2 and the ending follow decision 79.
- **Decision 65, words for the system:** `FOREIGN_PROOF` becomes `<feature> <PROOF-N> needs <Windows>; this machine is <macOS>. Run purlin:test --remote.` run_script RULE-10 and RULE-21 are rewritten.
- **Decision 77, "A remote runner is named by its kind, `remote runner, Windows`":** `write_sections` passes `machine` and `hostname` (section 2.5).
- **Decision 68, "On a remote runner the job fails only when a test fails or could not run":** the `--ci` exit code is the test exit code alone. RULE-12 and RULE-47 are rewritten.
- **Decision 77, "No message is printed when a change ends signatures":** `WENT_STALE` is deleted and RULE-53 with it.

**This repository's specs:** remove the 2 `[level: passed]` tags in run_script and the 1 in skill_test. RULE-49's "a rule whose level is `passed` is not read" is deleted.

**Deletes:** `NO_SUITES`, `malformed_lines`, `NOT_A_MARKER`, `WENT_STALE`, and the level clause of `_audit`.

**Acceptance:** `dev/test_run_script.py`, `dev/test_reports.py`, `dev/test_skill_test.py`, then `--fast`.

#### L4 `audit`: the audit, the writing guide, the spec skills

**Owns:**
- `scripts/review/ai_audit.py`, `scripts/review/marked_tests.py`
- `references/review_criteria.md`, `references/spec_quality_guide.md`
- `specs/review/ai_audit.md`, `specs/run/mutation.md`, `specs/skills/skill_audit.md`, `skill_spec.md`, `skill_spec_from_code.md`
- `skills/audit/SKILL.md`, `skills/spec/SKILL.md`, `skills/spec-from-code/SKILL.md`
- `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_mutation_adapters.py` (no change expected), `dev/test_skill_audit.py`, `dev/test_skill_spec.py`, `dev/test_skill_spec_from_code.py`

**Changes:**
- **Decision 73:** `is_read` drops `entry.get('level') == 'passed'`, and the reading and prompt stop printing `level`. ai_audit RULE-1 is rewritten.
- **Decision 71, "This is written into `references/spec_quality_guide.md`, `purlin:spec` writes to it and the audit checks it":** the guide gains "One proof, one case": one starting situation, one action, at most 60 words, and a refusal or boundary as its own case. The spec skill cites it. skill_spec gets a new rule.
- **Decision 75, "An audit that finds a proof longer than the standard, or holding two cases, notes it and does not find the rule weak for it":** `review_criteria.md` asks for such observations under `notes`, and `ai_audit.py` parses `notes` into the result. New ai_audit rule.
- **Decision 79, "Every run and every audit ends on the summary and `Left to do`; the audit keeps one earlier line saying what it read and found":** `skills/audit/SKILL.md` says so. skill_audit RULE-6 and RULE-3 are rewritten, and the skill stays within 105 lines.
- **Decisions 81 and 66, starting from existing code:**
  - Quoted: "Every rule is written from what its test expects, passing or not, and no test is run first … ends by listing the files that got none … A test may be left untied for three reasons … it shows only part of what a rule needs, it repeats a test already tied, or it tests code the project does not own".
  - Also 73: "`purlin:spec-from-code` marks no level".
  - skill_spec_from_code RULE-5 is deleted. New rules: RULE-7 (files without a rule listed at the end), RULE-8 (the three reasons to leave a test untied), RULE-9 (every rule written from what its test expects, no test run first). RULE-6 is reconciled with RULE-8.

**This repository's specs:** remove the level tags in ai_audit (3), mutation (1), skill_audit (1), skill_spec (1) and skill_spec_from_code (1).

**Deletes:** the level condition in `is_read`, and spec-from-code's `[level: passed]` instruction.

**Acceptance:** the 6 owned test files, then `--fast`.

#### L5 `signing`: signatures and the sign skill

**Owns:**
- `scripts/review/sign.py`, `scripts/mcp/purlin/signatures.py`
- `references/formats/signature_format.md`
- `specs/review/signatures.md`, `specs/skills/skill_sign.md`
- `skills/sign/SKILL.md`
- `dev/test_signatures.py`, `dev/test_tag.py`, `dev/test_skill_sign.py`

**Changes:**
- **Decisions 62, 72 and 77, what a signature is made over:** "The rule, its proof, its test, the code its feature lists, what the audit found, and the machine the tests ran on. The machine it was signed on is not recorded" (section 2.4).
  - Implemented in `signed_hash`, `is_current`, `write_signature` and `signature_path`. `machine_name` is deleted.
  - signature_format goes from 10 to 11. Its paragraphs "Changing the code alone stales nothing", the `%G?` row and the trust paragraph are deleted.
- **Decisions 67 and 77, "Purlin checks that a signature is present and looks no further":** `counts` reads a `gpgsig` header on the commit. signatures RULE-20 and RULE-23 are rewritten, and RULE-22 is deleted.
- **Decision 77, key setup and the closing line:**
  - Quoted: "With no key set up, `purlin:sign` shows the commands, offers to run them, and carries on. When it finishes it prints `Signed 3 rules as jane@acme.com with the key ending ...Xy4Q.`"
  - `signing_configured` checks for a key, `SIGNING_SETUP` changes (section 2.6), and there is a new `key_fingerprint`. RULE-17 is rewritten, and a rule is added for the line.
- **Decision 75, "Purlin refuses nothing a person does":**
  - `untrusted`, `has_a_ci_run`, `NO_CI_RUN`, `_allowed`, `marked_below`, `MARKED_BELOW`, the `_committed_only` and `_tied_only` filters on signing, and `_gate_is_too_low` are all deleted.
  - Deleted rules: RULE-14, RULE-15, RULE-47, RULE-48, and RULE-49's and RULE-51's signing halves.
- **Decisions 75 and 76, the tag:**
  - Quoted: "the signed tag is written only when nothing is left to do and every result came from committed work", and "A finished project's last line names the release step at the gate `signed`".
  - `tag_if_met` reads `payload['left']` and the tag refusals of section 2.6.
  - `NO_TAG_SHORT` is deleted. `TAGGED` and `tag_message` change.
  - RULE-45 and RULE-53 are rewritten, and a rule is added for the committed-work refusal.
- **Decision 74, "`purlin:sign` still walks the rules that wait for a person":** the walk reads rules whose `left` is `to_test_by_hand` or `to_sign`. `opening_line` and the empty-walk line follow section 2.6. RULE-11, RULE-12 and RULE-16 are rewritten.
- **Decision 78, "Only `purlin:sign` records it … `purlin:sign` takes one rule, a feature or all":** it works at every gate; `--batch` becomes `--all`. RULE-12 and RULE-54 are rewritten.
- **Decision 76, anchors:** an anchor rule is signed once per consumer. `sign_and_commit` writes one file per consumer. New rule.
- **Decisions 70 and 80, "The version is read from a version file, then from what the project already states in its package description, and asked for only when neither gives one":** `project_version` changes per section 2.7, and `tag_name` returns None when there is none. RULE-45 is rewritten and a rule added.
- The walk ends on `summary.ending(payload)`.

**Sign skill (`skills/sign/SKILL.md`):**
- asks for the version and offers to write `VERSION`
- offers to run the key commands
- drops trust, the list of who may sign, and levels
- stays within 185 lines

skill_sign RULE-2, RULE-5, RULE-7 and RULE-8 are rewritten, and a new rule covers the version question.

**This repository's specs:** remove the 3 tags in signatures and the 1 in skill_sign. PROOF-3, PROOF-10 and PROOF-62 lose their level cases.

**Deletes:** `commit.gpgsign true` in the setup; `signed/unversioned`; the version fallback to the settings file; the triple and `level` fields; the allowed-signers setup in `dev/test_signatures.py` 283–329 and `dev/test_tag.py` line 68.

**Acceptance:** the 3 owned test files, then `--fast`.

#### L6 `package`: the evidence package and the export skill

**Owns:**
- `scripts/export/package.py`
- `references/formats/package_format.md`
- `specs/export/package.md`, `specs/skills/skill_export.md`
- `skills/export/SKILL.md`
- `dev/test_export.py`, `dev/test_skill_export.py`

**Changes:**
- **Decision 79, "The evidence package carries the same: the total, the count at each step, what is left, and the state `finished` or `not finished`; its format version is raised":** section 2.5.
  - package_format goes from 2 to 3 and the schema string from `purlin-package/1` to `purlin-package/2`.
  - package RULE-3, RULE-4 and RULE-5 are rewritten, and RULE-6 loses level and `meets_gate`.
- **Decision 75:** the `trust` key goes.
- **Decision 77:** the signature entry follows section 2.5, and `commit_verifies` is deleted.
- **Version:** `version_name` uses `sign.tag_name`. With no version, the command prints `No version: nothing in this project states one. Name it with --release <version>.` and exits 1. RULE-1 and RULE-2 are rewritten.
- `WRITTEN` becomes `Evidence package written to <path>. State: <finished|not finished>.`
- **Export skill:** the states `finished` and `not finished`. skill_export RULE-4 is rewritten, and the tag and level lines go.
- The tests write a `VERSION` file into every fixture project; none relies on the settings file's `version`.

**This repository's specs:** remove the 1 tag in skill_export. The prose mention of a level in package.md goes.

**Deletes:** `rules_meeting_gate`, `rules_short_of_gate`, the states `gate <gate> met` and `work in progress`, `trust`, `level`, `level_marked`, `meets_gate`.

**Acceptance:** `dev/test_export.py`, `dev/test_skill_export.py`, then `--fast`.

#### L7 `runner`: the remote runner and the CI files

**Owns:**
- `scripts/ci/gate_check.py`, `scripts/mcp/purlin/provenance.py`
- `scripts/run/host.py`, `remote.py`, `workflow.py`, `ci.py`
- `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml`
- `.github/workflows/purlin.yml`, `dev/fixtures/consumer-ci/**`
- `specs/ci/gate_check.md`, `specs/run/host.md`
- `dev/test_gate_check.py`, `dev/test_provenance.py`, `dev/test_host.py`, `dev/test_host_pathspec.py`, `dev/test_remote.py`, `dev/test_consumer_ci.py`
- `dev/manual/check_azure_provenance.py`, `dev/manual/check_azure_remote.py`, `dev/manual/README.md`

**Changes:**
- **Decision 75, the check of a runner's results:**
  - Quoted: "the check of who committed a runner's results" goes.
  - Delete `scripts/mcp/purlin/provenance.py`, `dev/test_provenance.py` and `dev/manual/check_azure_provenance.py`. host RULE-9 is deleted, and `host.py`'s docstring references go.
  - The `SYSTEM_ACCESSTOKEN` name that decision 65 wanted renamed lived only in `provenance.py`, so it goes with it.
- **Decision 75, "On a pushed signed tag the runner runs the tests and nothing else":** the `--verify` step goes.
- **Decisions 68 and 75, open question 1:**
  - Default: delete `scripts/ci/gate_check.py`, `specs/ci/gate_check.md` and `dev/test_gate_check.py`. The workflow loses its "Check the gate" step. The `--ci` step's own ending, the status with its summary and `Left to do`, is "the check on a remote runner", and its exit code is the job's.
  - Otherwise: keep a print-only `gate_check.py` that prints `summary.ending` and exits 0, or 2 when it cannot read.
- **Decision 75, "A remote runner has one reason, a rule that must hold on another operating system":**
  - `wanted` ignores `trust`, and `TRUST_REASON*` is deleted.
  - Matrix per open question 2. Default: one job per system the `@env` tags name, with no always-Linux job.
  - host RULE-19 and RULE-17 are rewritten, and the template comments are rewritten.
- **Decision 65, Azure DevOps:** "The remote run reads the full branch name first." `current_branch` reads `BUILD_SOURCEBRANCH` (stripping `refs/heads/`) before `BUILD_SOURCEBRANCHNAME`, folded into one reader with `ref_branch`. The test of about 15 lines goes back into `dev/test_host.py`. host PROOF-8 gets the run-branch case.
- **Decisions 65 and 80, other hosts:** `UNKNOWN_HOST` becomes section 2.6's line. `remote.py` refuses under `ci: none` with section 2.6's line. host RULE-31 and RULE-28 are reworded, and a rule is added.
- **Decision 77:** `ci.py` and `host.py` give `purlin_run` the runner's kind for the `machine` field.
- **This repository and the consumer fixture:** `.github/workflows/purlin.yml` follows open question 7. Default: delete it (no `@env` tag exists in this repository). `dev/fixtures/consumer-ci/.purlin/config.json` loses `trust`, and its workflow is re-rendered.
- The 8 tests P0a moved into `dev/test_gate_check.py` are deleted with it, or rewritten if the step stays.

**This repository's specs:** remove the 3 tags in gate_check if it is kept.

**Deletes:** the files above; `PASS.`, `FAIL.`, the `result` key, `_ENFORCEMENT_NOTE`, `_provenance` and `verify`; `TRUST_REASON*`; the second branch reader; the `ubuntu-latest` default job (under the default answer).

**Acceptance:** `dev/test_host.py`, `dev/test_host_pathspec.py`, `dev/test_remote.py`, `dev/test_consumer_ci.py`, then `--fast`. The live Azure check waits for the work machine.

#### L8 `init`: setup and the init skill

**Owns:**
- `scripts/init/scaffold.py`
- `templates/config.json`, `templates/gitignore.purlin`, `templates/evidence-readme.md`
- this repository's `.purlin/config.json`
- `specs/init/scaffold.md`, `specs/skills/skill_init.md`
- `skills/init/SKILL.md`
- `dev/test_init_scaffold.py`, `dev/test_skill_init.py`, `dev/init_e2e_walk.sh`, `dev/test_init_e2e_gates.sh`, `dev/test_init_e2e_wiring.sh`, `dev/windows_skip.sh`

**Changes:**
- **Decision 80, "`purlin:init` asks the gate, and at `strong` and `signed` also whether to break the code on purpose":**
  - Delete `TRUST_*`, `trust_words` and `ask_trust`. `trust_question` stays until R.
  - Delete `COMMAND_QUESTION`, `REPORT_QUESTION`, `NO_COMMAND` and `ASKED_FILES`. Setup writes `"tests": []` and asks nothing about tests (decision 70: "How the tests are run is settled at the first test run").
  - `NO_ENGINE` is not printed at `passed`.
  - scaffold RULE-1, RULE-5, RULE-45 and RULE-46 are rewritten. RULE-6, RULE-7, RULE-9 and RULE-32 move to run_script (L3 adds them there, and this lane deletes them). RULE-49 is deleted.
  - `frameworks.py` and `supported_frameworks.md` leave scaffold's `> Scope:`.
- **Decision 70, "The rehearsal, `--dry-run`, goes":** delete `--dry-run`, `Plan.dry_run` and RULE-30. RULE-33 loses its second half.
- **Decision 70, "The folder for anchors is created when the first anchor is written":** stop creating `specs/_anchors` at scaffold.py line 708. New rule.
- **Decisions 65 and 80, other hosts:** the host line and `ci: none` follow section 2.6 and section 2.7. RULE-14 and RULE-44 are rewritten.
- **Decision 77:** `print_signed`, the signing setup, is deleted, because `purlin:sign` shows it when needed. RULE-10 is rewritten.
- **Settings files:** `templates/config.json` follows section 2.7. This repository's `.purlin/config.json` loses `trust`.
- **Init skill:** `skills/init/SKILL.md` stays within 250 lines. skill_init RULE-2, RULE-5, RULE-6 and RULE-7 are rewritten.
- `dev/init_e2e_walk.sh` is rewritten to the contract strings: no trust, no allowed signers (197–216), no gate check, no queue, Left to do, `--all`.

**This repository's specs:** remove the 4 tags in scaffold and the 1 in skill_init.

**Acceptance:** `dev/test_init_scaffold.py`, `dev/test_skill_init.py`, then `--fast`. The two init shell suites are proven at integration.

#### L9 `upgrade`: the move from 0.9.5

**Owns:** `scripts/init/update.py`, `specs/init/update.md`, `dev/test_init_update.py`, `dev/fixtures/upgrade-0.9.5/**` (an input fixture, kept as it is).

**Changes:**
- **Decision 65, "`purlin:init --update` deletes [the old cache folder] outright":** `_apply_untracked` removes `.purlin/cache/` from git and from disk. RULE-8 and PROOF-8 are rewritten, and the committed-cache test goes back in.
- **Decision 80, "The upgrade has no rehearsal":** delete `--check` and the `--dry-run` hand-off. RULE-3 is deleted and RULE-20 reworded. `pending()` stays, because status reads it.
- **Decisions 80 and 75, the questions:** the gate question, then the mutation question at `strong`/`signed` only. `_ask_trust` is deleted. RULE-12 and RULE-26 are rewritten.
- **The settings the upgrade writes:**
  - `_detect_config` drops the `trust` clause and accepts `ci: none`.
  - `_apply_config` writes the keys of section 2.7 with `ci` from the host, or `none`.
  - update's copy of `GATE_QUESTION` is deleted; it uses `scaffold.GATE_QUESTION`.
  - RULE-10 and RULE-11 are rewritten.
- `set_up_by_095`, which P0b added, becomes this lane's. A rule is added for it.

**This repository's specs:** remove the 2 tags in update.

**Acceptance:** `dev/test_init_update.py`, then `--fast`.

#### L10 `dashboard`: the page

**Owns:**
- `scripts/report/src/*.js`, `styles.css`, `page.html`, `theme.js`
- `scripts/mcp/purlin/report_data.py`
- `dev/build_report.py`, `dev/capture_doc_screenshots.py`, `dev/browser_launch.py`, `dev/fixtures/report/*.json`
- `specs/dashboard/purlin_report.md`
- `dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`, `dev/test_report_refresh.py`

**Changes:**
- **Decision 60, "The dashboard's box `<n> of <m> rules meet the gate` and its hover go":** the count chip goes from `gateChips`. RULE-7 is rewritten.
- **Decision 79, "a step's box is green when every rule has reached it and amber until then, and `Left to do` is a list under the boxes":** boxes are read from `summary.steps`, and the list from `left` with each command shown. RULE-8 is rewritten. `reached()` and `bucketTone` are deleted. The Untested, Failing and Partial tiles follow open question 5.
- **Decision 68, "A rule with no proof … has its own box and filter":** a `No proof` box and filter at `strong`/`signed`, from `rule.left == 'no_proof'`. New rule. RULE-13 is rewritten.
- **Decision 79, "A feature's description shows when its row is opened":** new rule.
- **Decision 74:**
  - Delete `queue.js`, the Queue tab, the Queue card, the Queue filter, `queueLines`, `inQueue` and `queueRowFor`.
  - Delete RULE-18, RULE-19, RULE-24's queue part, RULE-26's queue heading, RULE-30 and RULE-32.
  - RULE-23 changes to two screenshots, the board and one rule.
- **Decision 77:**
  - The Stale card and `staleLines` follow open question 4.
  - `signPanel` shows the signer's name and email, "key ending …Xy4Q", and the machine per system.
  - RULE-15 and RULE-26 are rewritten.
- **Decision 78, "each line of `Left to do` shows what to type in Claude Code to clear it, and nothing is ticked on the page":** new rule.
- **Decision 73:** delete `levelTag`, `levelSource` and RULE-48. RULE-15 is rewritten.
- **Decision 79, system words:** "The systems are shown as `Windows`, `macOS` and `Linux/Unix`, and in the dashboard's small boxes as `Win`, `Mac`, `Lin`". Read from `os_words`. RULE-31 and RULE-37 are rewritten.
- Rewrite the three fixture payloads to schema 10 with no removed key. states RULE-70's fixture list is L1's; this lane edits the fixtures only.
- Check the page with playwright at 1500, 1280, 1024, 768 and 390 pixels, dark theme.

**This repository's specs:** remove the 48 tags. Seven more rules and proofs describe levels in their text: RULE-48 (deleted), PROOF-73 and PROOF-74.

**Acceptance:** the 3 owned suites, then `--fast`. The lane rebuilds the page locally and does not stage it.

#### L11 `authoring`: build, anchor and drift

**Owns:**
- `scripts/mcp/purlin/drift.py`, `scripts/anchor/upstream.py`
- `references/drift_criteria.md`
- `specs/mcp/drift.md`, `specs/anchor/upstream.md`, `specs/skills/skill_build.md`, `skill_anchor.md`, `skill_drift.md`
- `skills/build/SKILL.md`, `skills/anchor/SKILL.md`, `skills/drift/SKILL.md`
- `dev/test_drift.py`, `dev/test_upstream.py`, `dev/test_upstream_notes.py`, `dev/test_skill_build.py`, `dev/test_skill_anchor.py`, `dev/test_skill_drift.py`
- `dev/test_e2e_build_changeset.sh`, `dev/test_e2e_anchor_authority.sh`, `dev/test_e2e_external_refs.sh`

**Changes:**
- **Decision 65, "The build skill's 3 endings and the anchor skill's 2 endings that name none get one, and the test checks every ending":**
  - build: "rules still have no test" → `→ Run: purlin:build <feature>`; hand check → `→ Run: purlin:sign <feature> RULE-<n>`; other system → `→ Run: purlin:test --remote`.
  - anchor: "no feature requires it yet" → `→ Run: purlin:spec <feature>`; "pin current, nothing moved" → `→ Run: purlin:status`.
  - skill_build PROOF-3 and skill_anchor PROOF-3 call `undirected_outcome_problems`.
- **Decisions 69 and 80, "`purlin:build` repairs a comment whose form is wrong or whose feature or rule name is one letter from a real one":** the build skill runs `markers.py --near-misses`, shows each fix, asks, and edits. New skill_build rule.
- **Decision 70, "`purlin:build` sets [the test command] when it writes the tests":** the build skill ends by running `purlin:test`, which suggests and writes the command. It delegates and repeats nothing. New rule. The skill stays within 130 lines.
- **Decision 70, the anchors folder:** the anchor skill states that `specs/_anchors/` is created with the first anchor. New skill_anchor rule.
- **Decisions 74, 77 and 78, drift for QA:**
  - Quoted: "shows under `Left to do` as `to test by hand`, and in drift for QA", and "No message is printed when a change ends signatures".
  - The QA view prints the `to_test_by_hand` and `to_sign` lines of `Left to do` through `summary.left_lines`.
  - The drift-side queue line (drift.py 564–597), `_stale_reason` and `_BOUND` are deleted.
  - drift RULE-16 is deleted, and RULE-15 and RULE-18 are rewritten. `drift_criteria.md` is updated.

**This repository's specs:** remove the tags in upstream (5), skill_build (1), skill_anchor (1) and skill_drift (1). The `[level: passed]` lines in `dev/test_e2e_anchor_authority.sh` (222, 260, 291) go.

**Acceptance:** the 6 owned pytest files, then `--fast`. The shell suites are proven at integration.

#### L12 `words`: the agent and the shared references

**Owns:**
- `agents/purlin.md`, `specs/instructions/purlin_agent.md`, `dev/test_purlin_agent.py`
- `references/glossary.md`, `hard_gates.md`, `purlin_commands.md`, `commit_conventions.md`, `writing_style.md`, `rule_examples.md`

**Changes, all prose, written from section 2:**
- **Decision 68:** "The phrase `meets the gate` is used nowhere."
- The glossary loses queue, rollup-met, level, trust and signer list. It gains the summary, `Left to do` and its kinds, signature (decision 77), and hand check (decision 78).
- `hard_gates.md` gets "what a version is finished means" (decisions 75 and 76), "when a signature counts" (decisions 67 and 77), and the tag.
- `purlin_commands.md`: no `--dry-run`, sign's `--all`, markers `--near-misses`, the run's exit codes.
- `commit_conventions.md`: the two commit subjects (decision 80) and the tag message (section 2.6).
- `writing_style.md`: the three system words (decision 79).
- `rule_examples.md`: drops trust and level.
- `agents/purlin.md` (lines 56 and others) stays within 135 lines. purlin_agent RULE-* is rewritten wherever it quotes those words.

**This repository's specs:** remove the 1 tag in purlin_agent.

**Acceptance:** `dev/test_purlin_agent.py`, then `--fast`. The command-row check lives in each skill's test file and reads `purlin_commands.md` only for a row per command.

#### L13 `schema`: the spec format and the security anchor

**Owns:**
- `scripts/mcp/purlin/specs.py`
- `references/formats/spec_format.md`, `references/formats/anchor_format.md`
- `specs/mcp/specs.md`, `specs/_anchors/schema_spec_format.md`, `specs/_anchors/security_no_dangerous_patterns.md`, `specs/instructions/purlin_version.md`, `specs/mcp/server.md`, `specs/mcp/config_engine.md`
- `dev/test_specs_reader.py`, `dev/test_schema_spec_format.py`, `dev/test_security.py`, `dev/test_purlin_version.py`, `dev/test_mcp_server.py`, `dev/test_config_engine.py`

**Changes:**
- **Decision 73:** delete `_RULE_TAG_RE`, `split_rule_tags` and `rule_meta` (section 2.8). specs RULE-1, RULE-2 and RULE-15 are deleted, and PROOF-1 through PROOF-4 and PROOF-17 are rewritten. spec_format goes from 17 to 18. The schema_spec_format rules that name the tag are rewritten.
- **Decision 65, "No name containing `token` … The rule stays as written and the test checks it in full":** `dev/test_security.py` PROOF-4 matches a name that contains the word, not only one ending in it.
- **Decision 65, "The guard before a revision handed to git is required where the revision comes from outside Purlin … the five places that hand git the fixed word `HEAD` stay as they are":** security RULE-6 is narrowed, and PROOF-6's test leaves out the literal `HEAD`.

**This repository's specs:** remove the tags in schema_spec_format (3), specs (2) and purlin_version (2).

**Acceptance:** the 6 owned files, then `--fast`.

### R `cleanup` (alone, after every fan-out lane has merged)

R deletes the names and keys section 0 lists:
- `payload['queue']` and `_sorted_queue` / `queue_row`
- `summary`/`rollup` `met`, `queue`, `hand_checks`, `asks_*`, `stale` (under the default of open question 4)
- rule `meets_gate`, `need`, `level`, `level_marked`
- `blocked_by`, where no reader is left
- `gate.TRUST_VALUES`, `DEFAULT_TRUST`, `level_of`, `RETIRED_KEYS` if unread
- `states.HAND_CHECK` and `SIGNATURE`
- `board.headline`, `queue_line`, `needs_a_person`, `bucket_line`
- `scaffold.trust_question`
- the `trust` parameter of `workflow.wanted`, with its callers in `scaffold.py` and `update.py`
- `signatures.commit_is_signed`
- `frameworks.entries_for`, if unread

Before it starts, a grep over `scripts/` confirms each name has no reader. It changes no spec text. **Acceptance:** `bash dev/run_tests.sh --fast`.

## 2. The contracts between lanes

### 2.1 The summary sentence and `Left to do`

**The sentence**, one line, with steps up to the gate only:

| Gate | Sentence |
|---|---|
| `passed` | `<N> rules. <p> pass their tests.` |
| `strong` | adds ` <s> are strong.` |
| `signed` | adds ` <g> are signed.` |

- Singular forms: `1 rule.`, `1 passes its tests.`, `1 is strong.`, `1 is signed.`
- Zero reads `0 pass their tests.`, `0 are strong.`, `0 are signed.`
- A rule is counted once, under the feature that owns it.

**The step counts** (decision 68, "Each step contains the next"):
- `p` counts rules whose passed cell reads `passed` and, where a proof is `@manual`, whose `hand_checked` is true.
- `s` counts the rules in `p` whose strong cell reads `strong`.
- `g` counts the rules in `s` whose signed cell reads `signed`.

**The kinds.** Each rule gets at most one kind: the first that applies, in this order. Lines appear in the same order. A kind at zero is left out.

| # | Kind | When it applies | Singular / plural text | Command |
|---|---|---|---|---|
| 1 | `no_proof` | gate `strong`/`signed`, the rule has no proof line (decision 79: "A rule with neither proof nor test is counted under `No proof` alone") | `1 rule to write a proof for` / `<n> rules to write a proof for` | `purlin:spec` |
| 2 | `to_fix` | passed cell `failed` or `partial` | `1 rule to fix` / `<n> rules to fix` | `purlin:build` |
| 3 | `no_test` | passed cell `no test` (at `passed` this includes a rule with neither proof nor test) | `1 rule to write a test for` / `<n> rules to write a test for` | `purlin:build` |
| 4 | `to_test` | passed cell `not run` or `out of date`, and this machine can run it | `1 rule to test` / `<n> rules to test` | `purlin:test` |
| 5 | `to_test_remote` | passed cell `not run` whose `missing_env` excludes this machine's system | `1 rule to test on <systems>` / `<n> rules to test on <systems>`; systems in display words, ordered Linux/Unix, macOS, Windows, joined `, ` and ` and ` | `purlin:test --remote` |
| 6 | `to_test_by_hand` | a proof is `@manual` and `hand_checked` is false (any gate) | `1 rule to test by hand` / `<n> rules to test by hand` | `purlin:sign` |
| 7 | `to_audit` | gate `strong`/`signed`, strong cell `not audited` | `1 rule to audit` / `<n> rules to audit` | `purlin:audit` |
| 8 | `to_strengthen` | strong cell `weak` | `1 rule to strengthen` / `<n> rules to strengthen` | `purlin:build` |
| 9 | `no_scope` | gate `signed`, signed cell not `signed`, the owning feature spec names no files | `1 rule to tie to its files` / `<n> rules to tie to their files` | `purlin:spec` |
| 10 | `to_sign` | gate `signed`, signed cell not `signed` | `1 rule to sign` / `<n> rules to sign` | `purlin:sign` |
| 11 | `to_tag` | project-level: gate `signed`, kinds 1–10 all zero, and no `signed/*` tag points at HEAD | `the version to tag` | `purlin:sign` |

**Terminal rendering** (decision 79, "the first line of `Left to do` is the next step"):

```
40 rules. 35 pass their tests. 30 are strong. 20 are signed.
Left to do:
  5 rules to audit: purlin:audit
  10 rules to sign: purlin:sign
```

**When nothing is left**, the whole ending is the sentence followed by one line:

| Gate | Line |
|---|---|
| `passed` | `Nothing left to do.` |
| `strong` | `Nothing left to do.` |
| `signed` | `Nothing left to do. Push the tag to release it: git push origin signed/<version>` |

These carry out decision 76.

- Drift's QA view prints only the `to_test_by_hand` and `to_sign` lines, in the same words.
- The sign walk opens on those two lines. When both are zero it prints `Nothing is waiting for someone to test by hand or to sign.`, from the sentences of decision 61.

### 2.2 Payload schema 10

**Added top-level keys:**
- `left`: `[{"kind", "count", "text", "command"}]` in order. `text` excludes the command.
- `finished`: true when `left` is empty.
- `last_line`: the nothing-left line, or null.
- `os_words`: `{"windows": {"word": "Windows", "short": "Win"}, "macos": {"word": "macOS", "short": "Mac"}, "linux": {"word": "Linux/Unix", "short": "Lin"}}`.

**Added `summary` keys:**
- `steps`: `{"passed": p[, "strong": s[, "signed": g]]}`
- `sentence`: the string

**Added per-rule keys:**
- `left`: a kind or null
- `hand_checked`
- `applies_to`: the feature the entry is listed under
- `code_hash`: `fingerprint.code_hash` over the `> Scope:` of `applies_to`
- `machines`: `{os: machine}` over the current sections the passed cell read, from each section's `machine`; `{}` where none
- `audit.notes`

**Removed in R:**
- top-level `queue`
- `summary`/`rollup` `met`, `queue`, `hand_checks`, `asks_strong`, `asks_signed`, and `stale` (default)
- rule `meets_gate`, `need`, `level`, `level_marked`
- `flags.stale` (default)
- `gate.trust`

### 2.3 The one implementation: `scripts/mcp/purlin/summary.py`

P0b writes it; L1 owns it afterwards. The functions:
- `KINDS`: the table in 2.1
- `rule_kind(rule, gate, here_os, incomplete)`
- `steps(own_rules, gate)`
- `sentence(summary, gate)`
- `left(features, gate, here_os, tag)`
- `left_lines(payload, kinds=None)`
- `ending(payload)`, which returns the sentence plus the `Left to do` block or the nothing-left line

Who uses what:
- `payload.build_payload` is the only caller of `rule_kind`, `steps` and `left`.
- `status.sync_status` ends on `ending`. That ending is what the terminal, `purlin_run` (including `--ci`, which is the runner's check), and the audit show.
- `sign.py` uses `ending` and `left_lines(payload, ('to_test_by_hand', 'to_sign'))`.
- `drift.py` uses the same `left_lines` call.
- `package.py` copies `summary.steps` and `left`, leaving out `to_tag` when writing for the tag.
- The dashboard reads the payload keys and composes no text of its own.

### 2.4 Signature format 11 (decisions 62, 72, 76, 77)

**Schema string** `purlin-signature/2`. **File name** `<RULE-N>.<hash8>.<signer-slug>.json`, where `hash8` is `signed_hash[:8]`. The file sits beside the owning spec.

**Required fields:**
- `schema`
- `feature`: the owner
- `rule`
- `applies_to`
- `signed_hash`
- `rule_hash`, `proof_hash`, `test_hash`, `code_hash`, `audit_hash`
- `machines`
- `signer`: the email as git holds it
- `key_fingerprint`: `SHA256:…`
- `timestamp`

**Optional fields:** `signer_name` (git's `user.name`), `test_hash_kind`, `note`, `gate`, `evidence`.

**Gone:** `triple`, `level`, `machine`, `os`.

**The hash.** `signed_hash` is sha256 over seven lines:
1. `applies_to`
2. `rule_hash`
3. `proof_hash`
4. `test_hash`
5. `code_hash`
6. `audit_hash`
7. `machines` written as `os=machine` pairs, sorted, joined with `,`

**Whether a signature counts:**
- `signatures.is_current(signature, entry)` is true when the stored `signed_hash` equals `signed_hash(entry)`. A new system follows open question 3; the default is that any change ends the signature.
- `signatures.counts(project_root, signature)` returns `(True, '')` when the file is tracked and the last commit touching it has a `gpgsig` or `gpgsig-sha256` header. Otherwise it returns `(False, 'the commit that added it is not signed')`.
- A signature counts when both hold, at every gate.
- `key_fingerprint(project_root)` reads `user.signingkey` (a `key::` literal, a `.pub` path, or a private key path plus `.pub`) and returns `SHA256:` plus the unpadded base64 of the sha256 of the key blob. It returns None when there is no SSH key.

### 2.5 The evidence file, v4, and the package, v3

**Evidence, `purlin-evidence/2`:**
- Each section adds two required fields:
  - `machine`: the host's name (`platform.node()`, or `unknown`) for `local`, and `remote runner, <Windows|macOS|Linux/Unix>` for `ci`
  - `hostname`: `platform.node()` always, logged and never compared; this is "the lent name is kept beside it"
- `proofs[].result` is `pass`, `fail`, `missing` or `not run`. A proof tagged for another system whose test did not pass or fail is `not run` (decision 65).
- `audit.rules[].notes` is an optional array of sentences, not hashed.

**Package, `purlin-package/2`.** Top-level keys in this order:

`schema`, `state` (`finished` | `not finished`), `not_for_approval`, `rules`, `steps`, `left`, `purlin_version`, `project`, `version`, `tag`, `commit`, `gate`, `mutation_engine`, `min_strength`, `features`, `warnings`, `fingerprint`

- `not_for_approval` is false only when the state is `finished` at the gate `signed`. Open question 6 decides whether the key stays.
- Rules add `left`, and drop `level`, `level_marked` and `meets_gate`.
- Results add `machine`.
- Signature entries carry: `signer`, `signer_name`, `key_fingerprint`, `applies_to`, `machines`, `at`, `committed_at`, `note`, `gate`, `path`, `signed_commit`, and `locked` (`signed_hash`, `rule_hash`, `proof_hash`, `test_hash`, `test_hash_kind`, `code_hash`, `audit_hash`).
- `trust`, `rules_meeting_gate`, `rules_short_of_gate` and `commit_verifies` are gone.

### 2.6 Exit codes and the exact lines

**Exit codes:**

| Command | 0 | 1 | 2 |
|---|---|---|---|
| `purlin_run.py --test` / `--audit` | everything asked happened | a tied test failed or did not run; evidence is missing; a marker names nothing a spec has; no settings file; set up by 0.9.5 and not upgraded; no test command; for `--audit` at `strong`/`signed`, a rule read is weak or could not be audited | bad command line |
| `purlin_run.py --ci` | tests passed | a test failed or could not run, and nothing else | bad command line |
| `sign.py` | written and committed, or the walk closed | no key, or the commit was not made | bad command line |
| `package.py` | as today | as today | as today |
| `scaffold.py` | as today, `--dry-run` gone | as today | as today |
| `update.py` | nothing pending, or applied | — | no project |
| `markers.py --near-misses` | always | — | bad command line |

`update.py` loses `--check` and its exit 1.

**Run lines:**

| When | Line |
|---|---|
| No settings file | `No .purlin/config.json here, so nothing ran. Run purlin:init to write it.` |
| Set up by 0.9.5, not upgraded | `This project was set up by an older Purlin and not upgraded, so nothing ran. Run purlin:init --update.` |
| No test command, tool recognised | `No test command is set in .purlin/config.json, so nothing ran.`, then `Suggested for <name>: <run>`, then `Suggested entry: <one-line JSON>` |
| No test command, nothing recognised | `No test command is set in .purlin/config.json, and no test tool Purlin knows was found, so nothing ran. Run purlin:test to have one proposed.` |
| A rule fails | `<feature> <RULE-N> fails: <file>::<test>. Run purlin:build <feature>.` |
| A rule has no test | `<feature> <RULE-N> has no test. Run purlin:build <feature>.` |
| A marker names nothing | `<file>:<line> names <feature> <ID>, which no spec has. Correct the comment, or run purlin:build to repair it.` |

**The two commits (decision 80):**
- First commit subject: `purlin: specs, tests and settings for <feature>[, <feature>…]`. It prints `Committed <sha7>, the work these results describe:` and then one path per line, indented two spaces.
- Second commit subject: `purlin: evidence at <sha7 of the first>`, or of HEAD when there was nothing to commit. It prints `Evidence committed.` or `Evidence unchanged.`

**Near misses:** `markers.py --near-misses --project-root DIR` prints one JSON array of `{"file", "line", "text", "fix", "why"}`. It covers:
- `purlin` misspelled by one letter, or in capitals
- no space after the colon
- a `purlin:` comment that cannot be read
- a feature name, or a PROOF/RULE id, one edit from one that exists

**Sign lines:**

| When | Line |
|---|---|
| No key | `No key to sign with. These commands set one up:`, then `  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""` (only when that file does not exist), `  git config gpg.format ssh`, `  git config user.signingkey ~/.ssh/id_ed25519.pub` |
| Signed | `Signed 1 rule as <email> with the key ending ...<last 4>.` / `Signed <n> rules as …` |
| Tag written | `Tagged signed/<version> at <sha7>.` then `Nothing left to do. Push the tag to release it: git push origin signed/<version>` |
| No tag, work left | the summary ending |
| No tag, uncommitted work | `No tag: the working tree holds changes that are not committed, so the results do not describe a commit. Commit them, then run purlin:sign.` |
| No tag, uncommitted evidence | `No tag: <feature> has results that are not committed. Run purlin:test --commit.` |
| No version | `No version: nothing in this project states one. Name it with --release <version>, or write it to a VERSION file.` |

- The tag message: `Nothing left to do at the gate signed.\n\nCommit: <sha>\nGate: signed\n`
- "Every result came from committed work" means that at tag time `git status --porcelain` lists no path outside `.purlin/`, and no evidence file is uncommitted.

**Host lines:**

| When | Line |
|---|---|
| Unknown host | `The origin remote is neither GitHub nor Azure DevOps. Everything on this machine works with any host; only purlin:test --remote needs one of those two.` |
| `--remote` under `ci: none` | `purlin:test --remote needs a GitHub or Azure DevOps remote, and .purlin/config.json says ci: none.` |

### 2.7 The settings file and the version

**Keys:** `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci`.
- `ci` is `github`, `azure` or `none`. It is `none` with no remote or an unknown host (decision 80).
- `trust` is removed. No `signers` or `allowed_signers` key exists in the code today (`git show v0.9.5:templates/config.json` has none), so there is nothing else to remove.
- `templates/config.json` ships `"tests": []` and `"ci": "none"`. Setup writes the host it detects.

**`update.set_up_by_095(root)`** is true when any of these holds:
- `.purlin/config.json` lacks `tests`
- it carries `test_framework`, `spec_dir`, `pre_push`, `report` or `digest`
- a `*.proofs-*.json` or `*.receipt.json` file exists under `specs/`

It never looks at the page or the version stamp.

**`sign.project_version(root)`** reads, first match wins:
1. `VERSION` at the root
2. `package.json` `version`
3. `pyproject.toml` `[project] version`, then `[tool.poetry] version`
4. the first root `*.csproj` `<Version>`
5. otherwise `''`

`tag_name` returns None for `''`.

### 2.8 What the spec format loses, and the system words

- `[level: ...]` is no longer read. A spec that still carries it keeps the bracket as part of the rule text, which enters the rule hash, and no warning is printed. `[level: ...]` never shipped: 0.9.5 has no such tag, as `dev/fixtures/upgrade-0.9.5` shows.
- Wherever a person reads a system: `Windows`, `macOS`, `Linux/Unix`. In the dashboard's small boxes: `Win`, `Mac`, `Lin`. The stored words stay `windows`, `macos`, `linux`, and an unknown platform is `linux`.

## 3. The order

1. **P0a `split-tests`**, alone.
2. **P0b `summary`**, alone. It lands the new module, the payload keys, the status and run endings, and the interface shapes.
3. **Fan-out**, all 13 lanes at once. Each owns disjoint files. Each writes its tests against section 2's strings. None deletes a name another lane reads.
   - Blocked until the owner answers: L7 on questions 1, 2 and 7; L5 on question 3; L1, L3, L10 and L11 on question 4; L10 on question 5; L6 on question 6.
   - The Windows sort of decision 82 ("An agent sorts the rules and shows the owner the list before any is marked") is a read-only task and can run at any time. Nothing is marked until the owner approves.
4. **R `cleanup`**, alone.
5. **Integration**, alone:
   - `python3 dev/build_report.py`, and commit both built pages once. Look at the page with playwright at the five widths.
   - `bash dev/run_tests.sh`, the full sweep with the shell suites.
   - Check that `update.pending(.)` returns nothing and status prints no `→ Run: purlin:init --update`.
   - `python3 scripts/run/purlin_run.py --test --all --commit`. This writes and commits `.purlin/evidence/local/*.json` and `.purlin/tests.md` once, and prunes `gate_check.json`.
   - Sweep `scripts skills agents templates references specs dev .github` for `meets the gate`, `meet the gate`, `level:`, `trust`, `queue`, `Queue`, `stale`, `PASS.` and `FAIL.`. Leave out `dev/plans/`, `dev/fixtures/upgrade-0.9.5/` and `dev/test_vocabulary.py`.
   - Report to the owner the lines of `CLAUDE.md` that are now wrong (the format table's `gate_check` row). That file is the owner's to change.

Because no lane stages a generated file and each source file has one owner, fast-forward merges cannot conflict. A lane that must rebase only rebuilds locally.

## 4. This repository's specs under decision 73

94 rules carry `[level: passed]` today:

| Spec | Rules marked | Lane |
|---|---|---|
| `specs/dashboard/purlin_report.md` | 48 | L10 |
| `specs/anchor/upstream.md` | 5 | L11 |
| `specs/init/scaffold.md` | 4 | L8 |
| `specs/mcp/states.md` | 4 | L1 |
| `specs/_anchors/schema_spec_format.md` | 3 | L13 |
| `specs/ci/gate_check.md` | 3 | L7 (goes with the spec under the default) |
| `specs/review/ai_audit.md` | 3 | L4 |
| `specs/review/signatures.md` | 3 | L5 |
| `specs/init/update.md` | 2 | L9 |
| `specs/instructions/purlin_version.md` | 2 | L13 |
| `specs/mcp/specs.md` | 2 | L13 |
| `specs/run/run_script.md` | 2 | L3 |
| `specs/instructions/purlin_agent.md` | 1 | L12 |
| `specs/run/mutation.md` | 1 | L4 |
| skill_anchor, skill_build, skill_drift | 1 each | L11 |
| skill_audit, skill_spec, skill_spec_from_code | 1 each | L4 |
| skill_export | 1 | L6 |
| skill_init | 1 | L8 |
| skill_sign | 1 | L5 |
| skill_status | 1 | L1 |
| skill_test | 1 | L3 |

Those 94 rules then need an audit and, at the gate `signed`, a signature. They still pass their tests.

The proofs of these rules, which are the 124 proofs decision 73 names, are rewritten to the guide in the next phase, not here. This phase only removes the tag and rewrites rule or proof text that describes marking a level.

## 5. Open questions for the owner

**1. The last step on the remote runner.**
The remote runner reruns your tests on a clean machine. Its last step used to be a separate check that could fail the job; now nothing but a failing test fails it, and the test step already ends by printing the summary and `Left to do`.
Does the separate step stay?
- (a) Remove it. The test step's own ending is what you read, and the job fails only when a test fails or cannot run. (Recommended.)
- (b) Keep a separate step that prints the summary and `Left to do` again and never fails the job.

**2. Which systems the remote runner runs on.**
A remote runner exists for rules that must hold on a system your machine is not. Today it also always runs a Linux job, to run the rules that name no system.
- (a) Only the systems your rules name. A project that names only Windows gets one Windows job. (Recommended; it fits "one reason".)
- (b) Linux first, always, then the named systems. Every remote run then adds Linux results to every rule. Under question 3 (a), that ends every signature made on a Mac.
- (c) Remove the list. The runner runs Windows only.

**3. A remote run that adds a system.**
A signature is locked to the machine each result came from. If you sign on your Mac and later run the remote runner for the first time, some rules gain results from a second system.
- (a) The signature ends, and those rules are back to `to sign`.
- (b) The signature stands while the machines it was made with are unchanged. A new system is added without ending it.
- (c) Remove the machine from what a signature is locked to. It is only recorded.

**4. The count of signatures that ended.**
When code, a test or a result changes after signing, the signature no longer matches. You decided no message is printed and the rules return to `to sign`. The page still has a `Stale` card, and drift lists them for QA.
- (a) Remove the card, the word `stale` and drift's list. The rules simply count under `to sign`. (Recommended.)
- (b) Keep a small count on the page only, with no message anywhere else.

**5. The other boxes on the page.**
The steps' boxes turn green or amber. Beside them are boxes for rules that have no test, fail everywhere, or fail on one system.
- (a) Keep them, since they point at build work.
- (b) Remove them. The step boxes, the `No proof` box and `Left to do` say the same thing.

**6. The package's "not for approval" flag.**
The package tells the regulated system whether a version is finished. It also carries a yes/no saying "not for approval".
- (a) Keep it, false only when the version is finished at the gate `signed`.
- (b) Remove it. The state `finished` or `not finished`, with the gate beside it, says the same.

**7. This repository's own remote runner file, before the Windows list.**
Under "one reason", a project whose rules name no other system gets no runner. None of this repository's rules names Windows yet; decision 82 has that list come to you first.
- (a) Delete the runner file now. Setup writes it again once rules name Windows.
- (b) Keep a Windows-only runner file now, ahead of the list.

## 6. Risks

**Contradictions between decisions, resolved in favour of the later one:**
- 60, "The CI check still says pass or fail", against 68, "no `PASS` or `FAIL` word is printed". 68 holds, and 75's "runs the tests and nothing else" removes the check step's reason to exist (question 1).
- 60, "a rule marked lower meets it at its own level", and 36 and 58, against 73. 73 holds.
- 61, "the card stays `Queue`", against 74, "The queue goes … with its tab, its box and its line". 74 holds. Only 61's two sentences survive, in the sign walk's empty line.
- 62, "the operating systems its test results came from", against 77, "the machine the tests ran on". 77 holds, recorded per system.
- 65, "Every ending of a command names a command … also where the work is complete", against 76, "at the other two gates says `Nothing left to do.` and names no command". 76 holds, and the shared skill check gets the one exception.
- 67, "records the signer's name, the time and the key's fingerprint", against 77, which adds the email. 77 holds.
- 70, "Setup asks one thing", against 80, which adds the mutation question at `strong`/`signed`. 80 holds.
- 70, "commits … in the same step", against 80, "two commits in one step". 80 holds.
- 50, "`purlin:sign` refuses to sign … over evidence that is not committed", against 75, "Purlin refuses nothing a person does". 75 holds. The refusal survives only for the tag.
- 42, "tests changed, signatures stale" in QA's view, and run_script RULE-53, against 77, "No message is printed when a change ends signatures". 77 holds.
- 69, "a test run does not look for [nearly right comments]", beside 56, "A marker that names a feature … no spec has fails the run". Both hold. A well-formed wrong name still fails the run with advice; only build repairs.
- 80's length rule against the additions to status, test, build, init, audit and `agents/purlin.md`, which are all at their ceiling. Each lane must cut what it adds.

**Upgrade from 0.9.5:**
- `update._detect_config` today flags any config whose `trust` is not valid. After 75, every 0.10.0 project would then read as needing an upgrade, and the new "stop and name the upgrade" rule would stop every run. L9 must drop that clause and accept `ci: none`.
- The run must use `set_up_by_095`, not `pending()`. `pending()` also fires on a dashboard page that differs from the shipped one and on the `version` stamp, so after any plugin bump every run would stop.
- R must not remove `gate.TRUST_VALUES` before L9's merge. The order guarantees it.
- Removing `--check`/`--dry-run` leaves no preview of an upgrade. Each migration still asks first and backs up the files it rewrites.
- A 0.9.5 project on a Mac with `@windows` tags gets a Windows-only runner under question 2 (a). Its old workflow is removed as today.
- 0.9.5 configs carry `"version": "0.9.2"`. With the settings-file fallback gone, such a project is asked for a version at its first tag instead of being tagged `signed/0.9.2`.
- Deleting `.purlin/cache/` is irreversible. It holds only 0.9.5 runtime data, and the fixture covers it.

**Consequences for this repository's own state:**
- After P0a and until integration, every feature's evidence is out of date, because the test files were renamed and so their fingerprints changed.
- After decision 73, the count at `strong` and `signed` drops by 94 until they are audited and signed. The owner has said not to audit or sign yet.
- Evidence files at schema `purlin-evidence/1` are ignored after L2, so integration's rerun is required, not optional.
- A test that is tied to a rule and skipped on purpose, without `@env`, now keeps that rule from passing (decision 69). The docs phase must say so.

### Critical Files for Implementation
- /Users/richlabarca/LocalCode/purlin/scripts/mcp/purlin/payload.py
- /Users/richlabarca/LocalCode/purlin/scripts/mcp/purlin/states.py
- /Users/richlabarca/LocalCode/purlin/scripts/run/purlin_run.py
- /Users/richlabarca/LocalCode/purlin/scripts/review/sign.py
- /Users/richlabarca/LocalCode/purlin/scripts/mcp/purlin/signatures.py
