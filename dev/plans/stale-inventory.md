# Stale inventory for the 0.10.0 clean release (decision 44)

Read-only survey of `/Users/richlabarca/LocalCode/purlin` at `main` `a73086aa3`, 2026-09-27. No tracked file was changed, no git command that writes was run, no test was run.

## Summary

- The tree has 1350 tracked files. Stale items that no decision names, by area: `.purlin/` 8, `.github/workflows/` 1, root and config files 12, `dev/` 24, `specs/` 18, `scripts/` 17, docs, references and design 16. There are also 13 git ref rows and 9 untracked leftover rows. Items decisions 35 to 43 already name are listed in one closing section.
- The five largest stale items are:
  1. `.purlin/records/`: 262 tracked files, 4.8 MB.
  2. `.purlin/briefs/`: 609 tracked files, 2.0 MB.
  3. `docs/images/`: 6 tracked screenshots, 1.1 MB. Their content is stale under decisions 36 to 38.
  4. `dev/plans/`: 92 tracked files, 761 KB. It is history and gets deleted last.
  5. `design/components/` and `design/guidelines/`: 81 tracked files, roughly 330 KB on disk.

  Untracked and outside the release, but large: `.claude/worktrees/` (199 MB), `mutants/` (104 MB) and `dev/screenshots/` (5.1 MB).
- These would reach a user if 0.10.0 shipped today:
  - **Dead evidence in every install.** The marketplace source is `./`, so every install carries the 871 committed evidence files. They sit in a layout the current readers skip, so they are dead weight.
  - **A file nothing reads.** `purlin:init` writes `.purlin/plugin-root` into every project, and nothing reads it.
  - **Stale ignore entries.** `templates/gitignore.purlin` adds entries for `.purlin/cache/` and `.purlin/report-stamp.js`, and nothing writes either file.
  - **A duplicate-id warning that never comes.** `skills/spec/SKILL.md:169` tells the agent to act when a duplicate rule id warning appears, and no code emits that warning.
- **Before the owner pushes `main`** (826 commits ahead of `origin/main`): this repository's own `.github/workflows/purlin.yml` is from before decision 31. It triggers on every push to `main` and on pull requests, commits records through the API, and still carries the fork step.

## 1. `.purlin/` (committed evidence and local state)

The current readers read `.purlin/records/<source>/<feature>/` and `.purlin/briefs/<source>/<feature>/`, where `<source>` is `ci` or `local`. `source_of_path()` in `scripts/mcp/purlin/records.py:144-155` returns None for any path without a source folder, and says such a record "is not read". Every tracked record and brief below sits directly under `<feature>/`.

| path | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `.purlin/records/` (tracked, 262 files, 4.8 MB, 39 feature folders) | Committed records from 2026-09-16 and 09-17, last commit `2f621694d` | The layout has no source folder, so the reader skips every file (`records.py:147-155`). The file names carry the retired developer runner (`...-rich-labarca-macos.json`). Some folders are for specs that no longer exist: `static_checks`, `greeting` (a fixture feature, leaked by `771258f2c`), `skill_find`, `skill_rename`, `qa_report`, `pm_anchor_userstories`, `upstream`. Decision 10 already said to delete this checkout's records. | `git rm -r .purlin/records` | certain |
| `.purlin/records/README.md` (tracked) | Records README | It says "One file per verify run" and "unless a `validated/<name>` tag names them", which are both retired, and it describes the layout without source folders. `scripts/init/update.py:103` now writes a different text. | Goes with the folder | certain |
| `.purlin/briefs/` (tracked, 609 files, 2.0 MB, 38 feature folders) | Committed briefs, last commit `dd2101961` on 2026-09-16 | Same missing source folder, so `find_brief` (`records.py:127-141`) looks only under `ci/` and `local/`. The folder includes `static_checks/` (35 files), whose spec decision 33 deleted. | `git rm -r .purlin/briefs` | certain |
| `.purlin/tests/states.json`, `.purlin/tests.md` (tracked) | Test results from `6af5ba99d`, one feature, at commit `5b4d0ba` | This is the current decision 28 layout, which decision 40 retires. The table covers 1 feature of 37. | See the section for decisions 35 to 43 | certain |
| `.purlin/plugins/purlin-proof.sh` (tracked) | Shell plugin copy under its 0.9.5 name | Scaffold installs the shell plugin as `purlin-proof.sh` (`dev/test_init_scaffold.py:55`), but this copy differs from `scripts/proof/shell_purlin.sh` at line 56. Nothing in this repository sources it: this repository's suites use `scripts/proof/shell_purlin.sh`. | Refresh or `git rm` | likely |
| `.purlin/plugins/jest_purlin.js`, `vitest_purlin.ts` (tracked) | Plugin copies | They are byte-identical to `scripts/proof/`, but this repository's config says `test_framework: pytest,shell`, so neither is used here. Only the pytest copy matches a framework this repository uses. | `git rm` the two | likely |
| `.purlin/report-stamp.js` (ignored, untracked, 2026-09-13) | Dashboard focus stamp, schema 3 | No writer: `grep report-stamp` under `scripts/` finds only `update.py:75` `IGNORE_LINES`. | `rm`. Also drop it from `.gitignore:21`, `templates/gitignore.purlin` and `update.py:75`. | certain |
| `.purlin/plugin-root` (ignored, untracked) | The plugin path | Written by `scaffold.py:720` and read by nothing. See the `scripts/` table. | `rm` | likely |
| `.purlin/runtime/` (ignored, 552 KB, 2026-09-17) | Runtime proofs and markers | It holds `test_run.json` and `last_sweep.json`, which no script reads. It also holds proof files from deleted specs and tests (`proof_plugins_sql.unit.json`, `purlin_references.unit.json`) and tier-named files (`*.integration.json`, `*.e2e.json`). | `rm -rf`; the next run regenerates it | certain |

## 2. `.github/workflows/` (this repository)

| path | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `.github/workflows/purlin.yml` | This repository's own Purlin workflow, last changed by `e4133969f` | It triggers on `pull_request` and on pushes to `main` and `run/**`, which decision 31 withdrew; `templates/purlin.yml` triggers on `run/**` and `signed/**` only. The header comment describes protected-branch commits and pull request comments. It still has the step "Say that a forked pull request writes no commit", which decision 34 removed. It hard-codes `[ubuntu-latest, windows-latest]`, but this repository's specs name only `@env(linux)` (`specs/init/scaffold.md` PROOF-36), so the template rule (`scaffold` RULE-15) would give `ubuntu-latest` alone. The job is named `audit`, where decision 31 says `purlin`. The gate check lacks `--verify`. It uploads a dashboard artifact the template no longer uploads. Under decision 31's amendment this repository still needs a runner, because `@env(linux)` names an operating system this macOS machine is not. | Regenerate from `templates/purlin.yml` through `purlin:init --update`, or delete it if the owner drops the `@env(linux)` proof | certain |
| `.github/workflows/version-check.yml` | Version drift check, runs `dev/bump_version.sh --check` and `dev/test_purlin_version.py` | Current. It triggers on push or pull request that touches version files, which is a development check for this repository and not the Purlin workflow. It cites `specs/instructions/purlin_version.md` RULE-6/7/8, which exist. The test file it runs contains `TestTheSweepRecordsItself` (see `dev/`), and that job would go if the class goes. | Nothing | certain (current) |

## 3. Root and config files

| path | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `.gitignore:43-44` `*.mmd`, `!assets/src/*.mmd` | Mermaid exception | `assets/src/` was deleted (`git log --diff-filter=D` shows three `.mmd` files). `assets/` holds only `.DS_Store`. | Delete 2 lines | certain |
| `.gitignore:50-53, 62, 31` `.purlin/worktrees/`, `.purlin_worktree_label`, `.purlin_session.lock`, `PURLIN_AGENT_PLAN.md`, `.claude-plugin-data/` | Ignores for earlier runtime files | `git grep` finds no writer or reader in 0.10 or in `v0.9.5`. | Delete 5 lines | likely |
| `.gitignore:19`, `:21` `.purlin/cache/`, `.purlin/report-stamp.js` | Ignores | Nothing writes either file. | Delete 2 lines | certain |
| `.gitignore` comment "(read by .purlin/hooks/)" on `.purlin/plugin-root` | Comment | `.purlin/hooks/` was retired (`update.py:67`). | Goes with the plugin-root item | certain |
| `.gitignore:34-35` `.mcp.json` | Ignore | No `.mcp.json` exists; the server is declared in `.claude-plugin/plugin.json`. | Delete 2 lines, or keep | unsure |
| `.gitignore` comment `/purlin-report.html` "symlinked from framework" | Comment | `scaffold.py:728` copies the page; it does not link it. | Reword | certain |
| `.gitattributes:5-6` "and the git hooks are run by bash" | Rationale | No git hooks ship (decision 31). The `tools/` clause on line 4 is covered by decision 41. | Edit 1 line | certain |
| `requirements.txt:1-3` "before it runs verify" | Comment | Retired command name; the step is `purlin_run.py --all --ci`. | Reword | certain |
| `settings.json` (root, tracked) | `{"agent":{"purlin":{"model":"claude-sonnet-4-6"}}}` | Unchanged since `e0226b080` (2026-03-31). Nothing in the tree reads it except `setup.cfg` also_copy. `agents/purlin.md` names no model. Whether the plugin loader reads it was not confirmed from the tree. | Delete, or confirm (unsure 13) | unsure |
| `.claude-plugin/plugin.json:24` keyword `"verification"` | Marketplace keyword | Names the retired verify step. | Replace | unsure |
| `setup.cfg` `--deselect` for `test_the_dropped_languages_have_no_plugin` | mutmut settings | That test is an absence check marked stale in `dev/`. The `tools` and `designs` entries in also_copy are covered by decisions 38 and 41. | Delete 1 line | likely |
| `init_e2e.test.sh`, `proof_plugins.test.sh`, header comments | Root entry points | They say the shell arm runs `*.test.sh` "at the project root", but `shell_tests()` in `scripts/run/purlin_run.py:274-278` walks the whole project. `@e2e` and "e2e tier" are covered by decision 38. | Reword the comments | certain |

## 4. `dev/` (excluding `dev/plans/`)

| path (or symbol, file:line) | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `dev/consumer_ci_dryrun.sh` | Hand-run walk of the consumer-ci workflow | It calls `purlin_run.py --all --record`, and `parse_args` (`purlin_run.py:146-190`) refuses `--record`. It reads `.purlin/records/greeting/*.json`, which is the layout without a source folder. It calls `ci.publish_dashboard`, but `scripts/run/ci.py` defines only `is_the_workspace`. Its only reference is `test_consumer_ci.py:359-363`, which checks the text and does not run it. | Delete the script. Also delete that test, the docstring at `test_consumer_ci.py:15-16`, and the dry-run clause of `records` PROOF-20. | certain (broken), likely (remove) |
| `dev/run_tests.sh`, `write_marker` trap (roughly lines 40-45, 85-163) | Writes `.purlin/runtime/test_run.json` and `last_sweep.json` | No reader under `scripts/`. `proofs_format.md:79` lists `test_run.json` as retired. The reader was `purlin_version` RULE-9, dropped by decision 31. | Cut the trap and its counters, and rewrite the header | likely |
| `dev/test_purlin_version.py:361-462` `TestTheSweepRecordsItself` | Proof of `purlin_version` RULE-10 | It proves that a file nothing reads gets written. | Delete the class, RULE-10 and PROOF-10, and the RULE-9 and RULE-10 briefs | likely |
| `dev/test_vocabulary.py:78` `PENDING_REWRITE = ()` | Staging list | Empty | Delete the constant and its use | certain |
| `dev/test_vocabulary.py:82` `PENDING_DELETE = (".approvals/",)` | Skip for old signature directories | `git ls-files` finds 0 `.approvals` paths | Delete the constant and the filter at :109 | certain |
| `dev/test_mcp_server.py:2087` `test_the_old_server_module_is_gone` | Asserts `purlin_srv.py` is absent | v0.9.5 shipped `purlin_server.py`; `purlin_srv.py` never shipped. | Delete the test | certain |
| `dev/test_mcp_server.py:637` `test_c_and_php_are_gone` | Absence check | It guards a removal; the history belongs in the release notes. | Delete the test; move the `detect_frameworks == ['shell']` assert elsewhere | likely |
| `dev/test_multilang_proof_plugins.py:934-957` `TestTheRetiredFieldsAreGone` | Absence checks for `test_run.json`, `PURLIN_PLATFORM`, `proofs-`, and the C and PHP plugin files | Same kind of guard | Delete the class, keep the `names == set(PLUGINS.values())` assert, drop the `setup.cfg` deselect, adjust `run_script` PROOF-46 | likely |
| `dev/test_plugin_contract.py:259-270` | Requires the "Retired field" table in `proofs_format.md` | It forces a history table to exist | Delete with the table; adjust `run_script` PROOF-45 | likely |
| `dev/test_plugin_contract.py:195, 232, 316` | Markers for `purlin_references` PROOF-30, 32, 33 | `specs/instructions/purlin_references.md` was deleted in `7bd823815` | Retag or drop | certain |
| `dev/test_records.py:1009` | Marker for `records` PROOF-30 | That proof was removed in `fa4819520` | Retag or drop | certain |
| `dev/test_purlin_report.py:1136-1163` `FREE_CHECK_NAMES`, and the asserts at :734 and :1160 | List of retired scan names | A retired-word list (decisions 31 and 33) | Delete the tuple and loop | likely |
| `dev/test_run_script.py:1161-1177` `TestTheRunScriptCarriesNoRetiredVocabulary` | Private retired-word list | Duplicates `test_vocabulary.py` | Delete; move the emoji assert; adjust `run_script` PROOF-22 | likely |
| `dev/test_init_scaffold.py:833-842`, `:251-252`, `:273`, `:862-865` | Retired-word, `RETIRED_KEYS` and "no hook script" absence checks | Guards for removed things | Delete; keep the exact-key assert at :276 | likely |
| `dev/test_consumer_ci.py:289-298`, `:316-327` `RETIRED_TAG`, `RETIRED_KEYWORD` | Absence checks | Covered by the exact-shape asserts next to them | Delete | likely |
| `dev/test_skills.py:522-540` `SCAFFOLD_RETIRED`, `:839` `'retired term'` | Absence checks | Same kind of guard | Delete | likely |
| `dev/test_schema_proof_format.py:171`, `dev/test_schema_spec_format.py:43-50` | Require the "Retired tags" section in the format files | They depend on history sections | Delete with those sections | likely |
| `dev/test_init_e2e.sh:373-374` | `expect_absent` for the pre-push shim and hook | The hook was removed by decision 31 | Delete 2 lines | likely |
| `dev/test_init_e2e.sh:499` | xunit gate walk that only prints a note | Never runs its case on any host | Finish or remove (unsure 5) | unsure |
| `dev/test_refresh_digest_hook.py:230` | Writes `.purlin/runtime/test_run.json` as a sample | Uses the retired marker's name | Rename the sample file | likely |
| `dev/manual/check_spec.py:30-33` `TMP_BASE` | Default work directory | Points at an earlier session's scratchpad (`.../bdea5a4d-.../scratchpad/lane-9H`) | Default to `tempfile.mkdtemp()` | certain |
| `dev/fixtures/consumer-ci/.purlin/records/README.md` | Fixture README | It says `ci/` is restricted to the build identity and that "only ci/ [counts] at signed", both withdrawn by decisions 31 and 32. It differs from `update.py:103-113`. | Replace, or drop under decision 40 | certain |
| `dev/fixtures/consumer-ci/.purlin/config.json` | Fixture config | It lacks `min_strength`, `sql_engine` and `trust`, which scaffold writes (`test_init_scaffold.py:276`) | Regenerate | likely |
| `dev/screenshots/` (untracked, 62 PNG, 5.1 MB) | Old captures | Decision 18 said delete it. It is ignored by `*.png`, so `git rm` in `lanes/tl-6B.md:31` cannot work on it. | `rm -rf dev/screenshots` | certain |

About `dev/test_vocabulary.py`:
- `PENDING_REWRITE` has 0 entries, and `PENDING_DELETE` has 1 entry that matches 0 paths.
- `MARKED` permits 56 `# retired` lines in 10 files: `update.py` 24, `references/formats/spec_format.md` 7, `dev/test_mcp_server.py` 6, `gate.py` 5, `specs.py` 5, `dev/test_init_update.py` 4, `dev/test_schema_spec_format.py` 2, and 1 each in `test_signatures.py`, `test_schema_proof_format.py` and `test_run_script.py`.
- The file itself is a table of retired words (see unsure 1).

Every other skip in `dev/` depends on the host: node, sqlite3, dotnet, playwright, ssh-keygen, Darwin, and external refs. The `@pytest.mark.skip` strings in the fixtures are text written into temporary projects, not real skips.

The helpers checked as current:
- `dev/conftest.py`, `browser_launch.py`, `build_report.py`, `bump_version.sh`, `capture_doc_screenshots.py`, `setup-external-refs.sh`, `windows_skip.sh`.
- `dev/fixtures/upgrade-0.9.5/`, `dev/fixtures/mutation/` and `dev/fixtures/report/`.

`dev/plans/` holds 92 tracked files: 761 KB and 11,457 lines. It is planning history: `three-levels.md`, `evidence-workflow*.md`, `handoff.md`, `TODO-0.10.0.md`, `held-rules-0.10.0.md` and 85 lane briefs. Decision 44 covers it, and it is deleted last because the agents still read it.

## 5. `specs/`

The tree has 37 specs, 549 rules and 639 proof lines. No proof JSON is tracked under `specs/`. Every `> Scope:` path exists except the glob `scripts/**/*.php`. The one `> Requires:` line (`run_script` requires `proof_common`) resolves.

| path (or rule, file:line) | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `specs/_anchors/proof_common.md:6-8` | Description | It says each per-framework spec requires this anchor, "copied six times". Those specs were deleted in `7bd823815`; only `run_script` requires it. | Rewrite | certain |
| `specs/_anchors/schema_proof_format.md:3`, `schema_spec_format.md:3` | Descriptions | They name Format-Version 8 and 11; the files are at 9 and 12. | Fix or drop the numbers | certain |
| `specs/init/scaffold.md:19` RULE-1 | "at `passed` with a remote one more: whether to run the tests on a remote runner" | Decision 31 withdrew that question; the script asks the trust question at every gate (`scaffold.py:89,704`). | Reword | certain |
| `specs/skills/skill_init.md:15` RULE-5 | The same retired question | `skills/init/SKILL.md:129-137` asks the trust question | Reword | certain |
| `specs/init/scaffold.md:44` RULE-25, PROOF-25 (:87) | "The shim names no machine" | The hook shim is removed (glossary:206). PROOF-25 has no test. | Delete the rule and proof; fix `scaffold.py:215` | certain |
| `specs/mcp/server.md:31` RULE-18 | Refresh skips on the index lock "because the pre-commit hook owns that regeneration" | `scripts/hooks/pre-commit.sh` was deleted in `7bd823815` | Reword, or drop the condition (unsure 11) | certain |
| `specs/run/run_script.md:45` RULE-40 (second half), PROOF-59 (:84) | "under `--ci` every arm's output is published as `logs/<arm>.log`" | `purlin_run.py` publishes no logs (lines 805-828), and its test at `dev/test_run_script.py:1238` checks `run.log` and "uploads nothing". The comment at `purlin_run.py:877-878` is stale too. | Rewrite the rule half, the proof and the comment | certain |
| `specs/instructions/purlin_version.md:24` RULE-10 | "beside the shared `test_run.json` each proof plugin rewrites" | No plugin writes it (`test_multilang_proof_plugins.py:942`) | Reword, or delete with the sweep marker | certain |
| `specs/run/records.md:40` RULE-26 | "A run whose project root is not the job's checkout speaks for nothing" | It is the one rule with no proof line: PROOF-30 was removed in `fa4819520`, and a test still tags it. | Write a proof or fold into RULE-27 (unsure 9) | likely |
| `specs/run/records.md:35` RULE-21 | Reason "never told its signature is not on the branch" | That is the protected-branch check decision 32 removed | Reword | likely |
| `specs/run/run_script.md:18` RULE-1, last clause | "`--audit --remote` exits 2" | It refuses a flag that never shipped (v0.9.5 has no `--remote` on audit) | Drop the clause, its proof leg and the code branch | likely |
| `specs/_anchors/proof_common.md:25` RULE-11 | Refuses "the retired operating-system keyword" | v0.9.5's pytest plugin has no such keyword, so this is an unshipped spelling. The `proofs_format.md:196-241` section exists only for it. | Delete the rule, proof, tests, six plugin branches and the format section | likely |
| `specs/_anchors/schema_proof_format.md:20` RULE-8 | "names the retired scope tag only under its retired heading" | `@on(` is not in v0.9.5 | Delete with `spec_format.md:185-188` | likely |
| `specs/ci/gate_check.md:51` PROOF-15 | "and never reads `last touched`" | Asserts the absence of the self-signing check decision 32 removed | Drop the clause | likely |
| `specs/_anchors/security_no_dangerous_patterns.md` (Scope, Description, RULE-1) | PHP guard | `scripts/**/*.php` matches nothing; the PHP plugin was deleted | Drop PHP there and in `dev/test_security.py` | likely |
| `specs/mcp/states.md:134-139` PROOF-59, 60, 61, 62, 64; `specs/mcp/specs.md:48-49` PROOF-17, 18; `specs/ci/gate_check.md:72` PROOF-37 | 8 proofs no test is tagged with | The proofs in `states` and `specs` are bar and signable proofs, which go under decisions 36 and 37. `gate_check` PROOF-37 (a re-audit stales a signature under `--verify`) is current and untested. | Write the gate_check test; the rest go with decisions 36 and 37 | certain |
| `specs/_anchors/schema_proof_format.md`, `schema_spec_format.md`, `security_no_dangerous_patterns.md` | Anchors that no spec requires and that are not global | Each proves only its own rules | Move to feature specs, or require them (unsure 8) | unsure |
| `CLAUDE.md:110` | "`purlin_skills` and `purlin_references` hold that scope" | Both specs were deleted in `7bd823815` | Edit 1 line | certain |

Proof and test cross-check:
- The tests carry 1007 tag sites (963 pytest, 44 shell) covering 647 feature and proof pairs, with 0 rule mismatches.
- 630 of 639 proofs have a test. The 9 without are `scaffold` PROOF-25 plus the 8 in the table.
- 4 tag sites point at a proof that does not exist: `records` PROOF-30, and `purlin_references` PROOF-30, 32 and 33.
- 4 shell suites carry no proof tag and run only from `dev/run_tests.sh`: `test_e2e_anchor_authority.sh`, `test_e2e_external_refs.sh`, `test_e2e_required_rules.sh` and `test_e2e_feature_scoped_overwrite.sh`. The same is true of `dev/test_vocabulary.py`.

## 6. `scripts/`, `hooks/`, `templates/`

No `__pycache__` is tracked. Every unused function, class and constant still has a test in `dev/` that calls it. None is called by nothing at all.

| path or symbol (file:line) | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `scripts/init/scaffold.py:215, 720` writes `.purlin/plugin-root` | Plugin path file "which the shim reads" | The shim was the git hook wrapper, removed by decision 31. `grep plugin-root` under `scripts`, `skills`, `agents`, `references` and `templates` finds the writer and two ignore lines, with no reader. The only other hits are tests (`test_init_scaffold.py:748,772,869,1051,1074`, `test_init_e2e.sh:523-528`). | Stop writing it; drop the ignore entries; edit 4 test sites and the scaffold spec | likely |
| `templates/gitignore.purlin` `.purlin/cache/`, `.purlin/report-stamp.js`, "(read by .purlin/hooks/)" | Lines added to every consumer's `.gitignore` | No writer for either file; the hooks are gone | Delete 5 lines; drop `report-stamp.js` from `update.py:75` `IGNORE_LINES` | certain |
| `scripts/mcp/purlin/ids.py:103` `duplicate_ids`, `:138` `renumber`, and their helpers | Duplicate-id check and renumbering | Only `dev/test_mcp_server.py:564,573,594` call them. `skills/spec/SKILL.md:169` says to act "when `sync_status` warns that a spec carries a duplicate rule or proof id"; `grep -i duplicate scripts` finds no such warning. | Wire the warning, or delete roughly 110 lines, the tests and the skill paragraph (unsure 10) | likely |
| `scripts/review/sign.py:318` `_rule_number` | Private helper | No caller; separate copies exist at `payload.py:227` and `purlin_run.py:1098` | Delete 4 lines | certain |
| `scripts/mcp/purlin/results.py:68` `WORDS` | Tuple | No Python reader | Delete 2 lines | certain |
| `scripts/run/records.py:109` `load_records`, `:114` `record_label` | Wrappers | Only `dev/test_records.py` and the unshipped `record-folders` migration call them | Delete; repoint the tests | certain |
| `scripts/mcp/purlin/records.py:294` `counts_under(gate, source)` | Source filter | Ignores `gate` and always returns true for a loaded record. It was left from decision 29's "only ci at signed", which decision 31 withdrew. One caller, `payload.py:470`. | Inline; update 5 tests | certain |
| `scripts/mcp/purlin/records.py:352` `data['label']`, and its readers in `payload.py`, `states.py`, `results.py:162`, `app.js:308,338` | Alias of `source` | The docstring at `:317` calls it the name schema 5 gave the same word | Read `source` everywhere | likely |
| `scripts/mcp/purlin/records.py:451-460` `default_branch` docstring | Rationale | It describes the branch check decision 32 deleted | Rewrite | certain |
| `scripts/review/sign.py:143` `rule_proof_test_hashes` | Hash helper | Only tests call it (`test_signatures.py:344,354,395`), and it returns `design_hash` | Delete; move the tests to `rule_entry` | certain |
| `scripts/mcp/purlin/states.py:71` `BUCKETS`, `:76` `FLAGS` | Tile and flag names | Only tests read them; `app.js:33` has its own copy | Delete or keep (unsure 12) | likely |
| `scripts/run/mutation/__init__.py:51` `ATTRIBUTIONS` | Enum | Only `dev/test_mutation_adapters.py:724` reads it | Delete or keep | unsure |
| `scripts/hooks/refresh_digest.py:54` `lock_exclusive` | Blocking lock | The script uses only `try_lock_exclusive`; the tests use this one | Move into the test | likely |
| `scripts/hooks/refresh_digest.py:12-13, 35` | "the pre-commit hook owns that regeneration" | No pre-commit hook in 0.10; `update.py:250` removes 0.9.5's | Reword; decide on the index-lock skip and `PURLIN_SKIP_DIGEST` (unsure 11) | certain (wording) |
| `scripts/purlin_python.sh:6-9, 26-28, 75-81` | Sourced mode; "the git hooks each have a never-block contract" | Every caller runs it with `sh` and nothing sources it; the git hooks are gone | Drop the sourced branch and the sentence | likely |
| `scripts/init/update.py:13-15` docstring, `:558` `_apply_workflows` docstring | "The detectors read the layout v0.9.5 left"; "runs the same audit a developer runs" | The first is false while the unshipped migrations remain. The second is wrong because CI runs no audit (`templates/purlin.yml:23`). | Rewrite | certain |
| `scripts/mcp/purlin/gate.py:75` `RETIRED_KEYS` | Keys warned about | It lists 9 keys that never shipped, and it misses two real 0.9.5 keys: `audit_criteria_pinned` and `report` | Trim to the 0.9.5 keys: `spec_dir`, `pre_push`, `audit_criteria`, plus the two (unsure 14) | likely |

`scripts/init/update.py`, `# retired` lines checked against `git grep v0.9.5` and `dev/fixtures/upgrade-0.9.5/`:
- **Real 0.9.5, kept as the upgrade exception:** lines 47-51, 54, 55-56, 59 (`.proofs-` marker), 68, 69 and 250.
- **Intermediate, never shipped:** lines 52, 53, 57-58, 60, 61-62, 63-66, 67, 70-72, 247, 85-87, 551-554, 628-713 (`record-folders`) and 300-301 with 348-365 (`sign_at`). Decision 41 names these.

## 7. `references/`, `skills/`, `agents/`, `docs/`, `design/`, `README.md`, `CLAUDE.md`, `RELEASE_NOTES.md`

Checked and found current:
- Every `docs/*.md` and `references/**/*.md` has an inbound link.
- All 10 references and 6 format files in `CLAUDE.md` exist, and none is missing from its tables.
- No `dev/` path appears in shipped prose.
- Decisions 32 to 34 left no hit for `is_fork`, "A run from a fork", `happy_path_only`, `rules_without_a_negative_case`, `static_checks`, "no merge while red" or `PURLIN_REMOTE_RUN`.

| path (or section, file:line) | what it is | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| `references/glossary.md:168-252` "Retired terms" | 68 rows: 37 "Retired by the three-level model" and 31 "Retired earlier" | Decision 44 names a "table of retired words". No code reads it: `dev/test_vocabulary.py` keeps its own `WORDS`/`LITERALS` and lists the glossary only as an exclusion (line 64). Line 171's claim that the check reads the table is false. At least 13 rows name spellings no `v*` tag carries. | Delete the section. Fix the pointers at `glossary.md:4-5`, `agents/purlin.md:32-33, 79-81`, `docs/index.md:62` and `CLAUDE.md:66`. | certain |
| `RELEASE_NOTES.md:184-222` "The words that were retired" | Roughly 29-row table | It repeats the glossary. Many rows (signers, protected branch, self-signing, `--quick`, risk, `record/` tags) are absent from `v0.9.5`, so no user ever saw them. | Trim to what 0.9.5 shipped (unsure 2) | likely |
| `RELEASE_NOTES.md:243-249` "The 0.10.0 line that never shipped" | History of unreleased work | No user had it | Delete or keep (unsure 3) | unsure |
| `CLAUDE.md:10, 15` | "the pull request comment", "pull request comments included" | CI writes no comment (glossary) | Edit 2 lines | certain |
| `references/hard_gates.md:140-145` "Branch rules" | "None. An earlier release printed three rulesets" | `ruleset` is in no `v*` tag | Delete, or cut to one sentence | likely |
| `references/hard_gates.md:118,138,143`, `references/purlin_commands.md:15`, `docs/how-purlin-works.md:125`, `docs/running-and-records.md:328,404` | "a pull request starts nothing", "No skill opens a pull request" | They describe removed behaviour by denying it | Delete the clauses (unsure 4) | unsure |
| `references/hard_gates.md:253-255` | "`--update` removes the pre-push hook an earlier release installed" | v0.9.5 did ship `pre_push`, so this may be the upgrade exception | Move to the upgrade page | unsure |
| `docs/dashboard.md:106` | "where it used to need 1100" | History clause | Cut the clause | certain |
| `references/commit_conventions.md:37` | Example `chore(update): migrate to 0.10.0 (legacy-proof-file, legacy-marker)` | Neither id exists; the real ids are at `update.py:718-740` | Replace | certain |
| `references/supported_frameworks.md:31-33` | "Two languages were dropped in 0.10.0: C and PHP" | Release history in a reference; already said at `RELEASE_NOTES.md:236` | Delete here | likely |
| `docs/raising-the-gate-and-upgrading.md:215-233` "Coming from v0.9.5" | Migration notes | Repeats `RELEASE_NOTES.md:14-34`, and describes the separate files of decision 40 | Link to the notes, or keep (unsure 2) | unsure |
| `design/readme.md:14-20, 126, 128-134, 150-160` | Sources, UI kit, Slides, Files sections | They name paths that do not exist: `uploads/*.pptx`, `uploads/Screenshot*.png`, `scraps/deck-text.md`, `ui_kits/dashboard/`, `slides/`, `assets/logo.png`. Line 132 calls the UI kit "a recreation of the v0.9.5 dashboard"; a "Design System tab" exists nowhere. `CLAUDE.md:9` names this file the authority. | Delete those sections | certain |
| `design/components/` (62 files) | 19 React primitives and 5 preview cards | Nothing outside `design/` references them. `dev/build_report.py` reads only `design/tokens/`, `design/styles.css` and `design/assets/logo-datauri.js`. The cards load `../../_ds_bundle.js`, which does not exist. The content teaches retired things: grading columns (`MetricValue.prompt.md:1`), a remote-queue button, runner-registry tags, a "Coverage" column. | Delete the folder and `design/readme.md:118-126` (unsure 6) | likely |
| `design/guidelines/` (19 cards, 80 KB) | Token specimen pages | Unreferenced; "rendered in the Design System tab", which does not exist | Delete or keep (unsure 7) | unsure |
| `design/SKILL.md` | "purlin-design" skill | It sits outside `skills/`, so it never loads, and it points at `README.md` where the file is `readme.md` | Delete | likely |
| `design/assets/logo-closing.svg` (12 KB) | Logo for "the final slide" | No deck exists; the only reference is `design/readme.md` | Delete | likely |

## 8. Git refs and worktrees (for the owner; no agent deletes refs)

| ref or path | state | why it is stale (evidence) | what removing it would take | confidence |
|---|---|---|---|---|
| Local branches `decision/32`, `decision/33`, `decision/34` and their worktrees `purlin-wt/d32`, `d33`, `d34` | Merged into `main` | Decisions 32 to 34 are applied | `git worktree remove`, then `git branch -d` | certain |
| Local branches `decision/38`, `decision/41` and worktrees `purlin-wt/d38`, `d41` | At `a73086aa3`, which is `main` | Probably in use by the agents applying decisions 38 and 41 | Leave until those land | certain (in use) |
| Local branches `lane/7A` to `lane/12B`, `lane/10A`, `10B`, `11A`, `11B`, `11D`, `14A`, `14B`, `15` (18 branches) and their worktrees under `/Users/richlabarca/LocalCode/purlin-wt/` | Merged into `main` | Lanes closed | `git worktree remove` each, then `git branch -d` | certain |
| `lane/13` (`4b257ba6c` "purlin: tests at 1f72a09"), `lane/14` (`5c6366890` "decision 31, three points settled") and worktrees `purlin-wt/13`, `purlin-wt/14` | 1 commit each not on `main`, no patch equivalent | A test-results commit, and a plan edit decision 31 on `main` already states | Confirm, then `git branch -D` | likely |
| Local branches `lane/1A` to `lane/6B` (11, no worktrees) | Merged into `main` | Closed lanes | `git branch -d` | certain |
| `evidence-workflow`, `two-gauges-remote-verification` (local and `origin/`) | Merged into `main` | Earlier plans | `git branch -d`; `git push origin --delete` | certain |
| `three-levels` (local `51c2afa07`) | Merged into `main` | The handoff branch | `git branch -d` | certain |
| `origin/three-levels` | 3 commits not on `main`, all "purlin: record for ..." | CI record commits in the old layout | `git push origin --delete three-levels` | likely |
| `origin/lane/1A` to `origin/lane/7B` (13 remote branches) | Each has 2 to 9 commits not in `main`'s history. The unique ones are mostly "purlin: record for ..." CI commits; `origin/lane/3` also carries 3 early scaffold and update commits (signer question) that decision 32 superseded. | Closed lanes | `git push origin --delete` each | likely |
| 5 `worktree-agent-*` branches and worktrees under `.claude/worktrees/` (199 MB, 2026-09-15) | Not ancestors of `main`, but `git cherry` finds 0 unique patches for each | Their work is on `main` | `git worktree remove`, `git branch -D`; also `git push origin --delete` for the two on `origin` (`a07ee71e...`, `ac25bbf7...`) | certain |
| Prunable worktree `/private/tmp/claude-501/.../a5e745a8-.../scratchpad/mutation-e78d1868` (detached) | Prunable | Its directory is gone | `git worktree prune` | certain |
| Local tag `validated/1.0` (`0ec919eab`, 2026-09-15, annotated) | Not on `main`'s history, not on `origin` | `validated/` is a retired tag name; the tag marker is now `signed/<version>` | `git tag -d validated/1.0` | certain |
| Tags `v0.5.0` to `v0.9.5`, `pre-instruction-optimization` (local and `origin`) | Released history | Release tags are history the owner may keep; `pre-instruction-optimization` is not a release | Owner's call (unsure 15) | unsure |

## 9. Untracked and ignored leftovers in the working tree

| path | size | why it is a leftover | action | confidence |
|---|---|---|---|---|
| `mutants/` | 104 MB, 2026-09-17 | mutmut's copy, rebuilt per run; ignored | `rm -rf` | certain |
| `dev/screenshots/` | 5.1 MB | See `dev/` | `rm -rf` | certain |
| `purlin-report.html` (root) | 52 KB, 2026-09-17 | Differs from `scripts/report/purlin-report.html`, so opening it shows the old board | `rm`, or rerun `purlin:init --update` | certain |
| `.purlin/runtime/`, `.purlin/report-stamp.js`, `.purlin/plugin-root` | 552 KB | See `.purlin/` | `rm` | certain |
| `scripts/update/` | 1 `__pycache__` only | The package was deleted; only bytecode remains | `rm -rf` | certain |
| `assets/` (root) | `.DS_Store` only | Its `src/` was deleted | `rm -rf` | certain |
| `__pycache__/` (root, 2026-09-15), `dev/__pycache__/`, `dev/fixtures/consumer-ci/__pycache__/`, `scripts/**/__pycache__/` | small | Bytecode | Optional | certain |
| `.claude/worktrees/` | 199 MB | See section 8 | `git worktree remove` | certain |
| `dev/external-refs/` | 84 KB | Created by `dev/setup-external-refs.sh` and read by `test_e2e_external_refs.sh` | Keep | certain (current) |

## 10. Covered by decisions 35 to 43 (one line each, for the final sweep)

- Signer list (32, 41): `update.py:63-66, 276-290, 729`; `gate.py:30-31`; `gate_check` RULE-8 and PROOF-11; `update` RULE-25; `signatures` RULE-21; `scaffold` RULE-10; the `signer-key` row in `docs/raising-the-gate-and-upgrading.md:151,191`.
- Free scans and hints (33, 35): only glossary rows 204-205 and `RELEASE_NOTES.md:212-213, 237` remain.
- `--quick` (34): only glossary:213, `RELEASE_NOTES.md:218` and the `MARKED` line in `dev/test_run_script.py`.
- `@integration`, `@e2e`, tiers: `pytest_purlin.py:40-65`, `specs.py:18, 61-65`, 319 proof lines, 349 `tier=` uses in 28 test files, `proofs_format.md` `proofs[].tier`, `spec_quality_guide.md`, `CLAUDE.md:70`, `.purlin/runtime/*.integration.json`.
- `--tier`: `purlin_run.py:5, 94, 164`; `run_script` RULE-1, 3, 16.
- Owner and criterion tags: `[origin: ...]` on all 549 rules; `specs.py:11, 48-52, 93-113`; `scaffold.py:239`; `spec_format.md:78`; `docs/team-workflow.md:146-152`; `skills/spec/SKILL.md:149`; `dev/manual/check_spec.py:42`.
- Design tie: `designs/README.md` (tracked); `docs/design-in-specs.md`; `sign.py:143-156`; `update.py:55-56, 499-528`; `drift.py` `CHANGED_DESIGNS`; `setup.cfg` also_copy `designs`; `test_init_update.py:638-660`.
- Holds: `dev/test_holds.py`; `sign.py` (7 sites); `states.py`; `hard_gates.md:216`; `commit_conventions.md:17`; `signature_format.md:14`; 174 "hold" hits in docs.
- Review and Sign lists, signable: `states.py:199, 813-831`; `board.py:85, 127`; `review.js`; `agents/purlin.md:50`; `CLAUDE.md:69`; `docs/images/dashboard-sign.png`, `dashboard-review-list.png`.
- Bar: `[bar: ...]` on all 549 rules; `gate.py:45-58, 186-205`; `hard_gates.md:54`; 7 untested proofs in `states` and `specs`.
- `sign_at`: `gate.py:50-58, 162-205`; `update.py:300-301, 348-365`; `.purlin/config.json`; `dev/fixtures/report/*.json`.
- `unsettled`: `states.py`, `brief.py:21`, `gate_check.py:14`, `design/components/core/StatusPill.jsx:10`, 46 doc hits.
- Spec status, `drafted`, `ready`: `states.py:1-8, 99-128, 748-787`; `StatusPill.d.ts:4`; `dashboard-rule.png`.
- Test results, records and briefs as separate files (40): `scripts/run/results.py`, `scripts/mcp/purlin/results.py`, `scripts/run/records.py`, `scripts/review/brief.py`; `specs/run/test_results.md`; `references/formats/tests_format.md`, `record_format.md`; `docs/running-and-records.md`; `.purlin/tests/`, `.purlin/tests.md`; the `CLAUDE.md` format table.
- Per-person settings file: `scripts/mcp/config_engine.py:1-20`; `server.py:133-152`; `config_engine` RULE-4 to 11; `.gitignore:17`; `templates/gitignore.purlin:10-11`; `dev/test_config_engine.py`.
- `purlin:anchor propose`: `upstream.py`; `upstream` RULE-16 to 21; `skills/anchor/SKILL.md:81,124`; `dev/test_e2e_anchor_authority.sh:319-345`.
- Upstream check: `templates/purlin.yml:45-48, 125-179` and `issues: write`; `scaffold.py:4`; `workflow.py:60-61, 106, 163`; `scaffold` RULE-16.
- `tools/`: 4 tracked files; `specs/tools/*.md`; `dev/pack_tools.sh`; `dev/manual/check_qa_tool.py`; `.gitattributes:4`; `setup.cfg` also_copy `tools`.
- Repository reader script: `scripts/report/scan.py`; `dev/test_scan.py`, `test_scan_review_list.py`; `records` RULE-13 to 16, 23, 25.
- `purlin:find`: `skills/find/SKILL.md`, `specs/skills/skill_find.md`, `.purlin/*/skill_find`.
- `purlin:rename`: `skills/rename/SKILL.md`, `specs/skills/skill_rename.md`, `.purlin/*/skill_rename`.
- Unshipped migrations: the intermediate `update.py` lines in section 6; `gate.py:58` `_SIGN_AT_WAS`; `update` RULE-17, 22 to 25; `test_init_update.py` unshipped-layout cases.
- Old-spelling readers: `specs.py:23, 49, 59, 81-83, 109, 142-146`; `pytest_purlin.py:49-52, 190-192`; the `platforms=`, `:on(` and `PURLIN_PROOF_PLATFORMS` plugin branches and their tests; `spec_format.md:69-75, 112-116, 183-188`; `proofs_format.md:75-81, 196-241`.
- Drift's design view: `drift.py:34, 473, 509`; `server.py:83`; `purlin_commands.md:81`; `drift` RULE-3; `test_drift.py:772-802`.
- Azure DevOps fix (43): `records` RULE-8, 9; `gate_check` RULE-16; the Azure paths in `test_records.py`.
- Audit calls the model (35): `brief.py:4, 63, 124` `--ai`; `states.py:85-89` `NO_MODEL`; `brief` RULE-16.

## Unsure: questions that would settle each

1. Once no list of retired words may ship, should an automatic check still stop an old word from coming back into the docs and code, or is a reviewer's reading enough?
2. Should the release notes list only words a released version used, and should the upgrade page keep its own "coming from the last release" section or just link to the notes?
3. Should the release notes keep a paragraph about development work that was never released?
4. Should the reference pages still say that a pull request starts nothing and that no command opens one, or say nothing about pull requests?
5. The end-to-end setup walk for a C# project stops before it tests anything, on every machine. Finish it or remove it?
6. Does anyone open the design system's gallery of example components when working on the dashboard or the docs, or can it go, keeping only the colours, type and logo?
7. Should the specimen pages for colours, type and spacing ship as a contributor reference, though nothing links to them?
8. Three shared rule sets (the spec format, the proof format, the dangerous-pattern check) are required by no spec. Should they become ordinary specs, or should the specs they govern require them?
9. A rule says a run from a folder that is not the job's own checkout speaks for nothing, and it has no proof now. Keep it with a new proof, or fold it into the neighbouring rule?
10. After a merge where two branches both added the same rule number to a spec, should Purlin warn and offer to renumber, or does a person fix it by hand?
11. While a person is mid-commit, should the dashboard refresh wait? Does anyone need a switch beyond the dashboard-refresh setting to turn it off?
12. Should the gate and the dashboard share one list of tile names that tests pin, or is the dashboard's own list enough?
13. Is the file at the plugin root meant to make the Purlin agent the default and pin it to one model?
14. Should an upgrade from the last release warn about the two old settings it drops silently (the report setting and the pinned audit criteria)?
15. Should the old release tags and the pre-release experiment tag stay on the remote, as history beside the release notes?
16. Should a test that only proves a removed feature is still absent be kept as a guard, or deleted because it names earlier functionality?
17. The full local test sweep writes a summary of what ran, and nothing reads it. Should it keep writing one?
