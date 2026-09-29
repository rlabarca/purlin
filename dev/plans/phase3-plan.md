# Phase 3: decisions 94, 95 and 96, cut by ownership of files

Written by the planning agent on 2026-09-29. Two steps run alone first (P1, then P2), then 20
lanes run together, then one integration agent alone, then the owner reads the Windows list,
then one marking wave. `phase3-contracts.md` is the contract between lanes: every agent builds
to it and none chooses. One brief per lane is under `phase3-lanes/`.

A workflow runs about ten agents at a time and queues the rest, so the 20 lanes run as two
overlapping waves of about ten. All 20 can run at once as far as ownership goes: no file has
two owners.

Briefs: `phase3-lanes/p1-interfaces.md`, `phase3-lanes/p2-warnings.md`, and one per lane named
in section 4.

## 1. Rules for every lane

- **Worktree, branch, scratch.** Lane `<lane>` works in `/Users/richlabarca/LocalCode/purlin-wt/<lane>`
  on branch `lane/<lane>`, created from `main` after P2 merged, with its own scratch folder
  `<session scratchpad>/lane-<lane>`. It writes only the files its brief lists as owned.
- **Frozen during the fan-out:** `dev/skill_checks.py`, `dev/mcp_project.py`,
  `dev/sign_project.py`, `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`,
  `dev/fake_claude.py`. A lane that needs a helper writes it in its own test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`, screenshots. A lane may
  build them locally to run its tests. Integration rebuilds and commits them once.
- **Tests.** `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH` first. Run the lane's own test
  files whole with `.venv/bin/python -m pytest <files> -q`, then `bash dev/run_tests.sh --fast`
  in the worktree. The full sweep runs once, at integration.
- **Deliberate breaks.** Before breaking code on purpose to check that an assertion fails, the
  agent confirms the break runs only under a test that uses `dev/fake_claude.py` or no model at
  all, with `PATH` holding no real `claude`, and that no real git host, `gh`, `az` or network
  service is reachable from it. It restores the code with `git checkout -- <that file>`, never
  `git checkout -- specs/`.
- **Proofs.** Every proof written or rewritten holds one case in at most 60 words and has a
  marked test of its own (`phase3-contracts.md` C11). A change to parsing or emission of a format
  updates its file under `references/formats/` in the same commit, with the bump C4 or C5 names.
- **Instruction lengths** (decision 80): a change to a skill or to `agents/purlin.md` cuts as many
  lines as it adds. Ceilings: status 100, test 120, build 130, init 250, audit 105, sign 185,
  export 90, spec 210, spec-from-code 130, drift 150, anchor 160, agent 135.
- **Clean release** (decision 44): delete outright what is retired; no test that a removed thing is
  absent; nothing added to `dev/test_vocabulary.py`.
- **A call no decision makes:** build the rest, leave that thing as it is, report it.
- **Commits** on the lane branch, with the prefixes of `references/commit_conventions.md`
  (`feat(<feature>)`, `fix(<feature>)`, `test(<feature>)`, `spec(<feature>)`, `docs(...)`,
  `chore(...)`), ending with the attribution lines the session gives. No push, no tag, no pull
  request, no `purlin:audit`, no `purlin:sign`, no real `claude` program.
- **Before merging:** rebase on `main`, rerun the lane's files and `--fast`, fix the lane's own
  files where an earlier merge changed a result that contracts C7 predicts, report the rest.
- **Report:** each spec's highest RULE and PROOF id after the work; tests before and after;
  every split (C11); every call left; every word the lane chose; every failure in a file it does
  not own.

## 2. The order

1. **Owner questions** (section 8, questions 1 to 23) are asked with the question UI, in their
   order. P1 does not depend on them and may run while they are open. Question 24 is asked with
   the Windows list (step 6).
2. **P1 `interfaces`**, alone: shared interfaces with no owner words.
3. The orchestrator writes the owner's answers into `phase3-contracts.md` and the briefs,
   replacing each `PENDING OQ<n>`.
4. **P2 `warnings`**, alone: the lines several surfaces print or assert, with the owner's words.
5. **The fan-out**: 20 lanes at once, each on disjoint files. Merge order in section 10.
6. **Integration**, alone (section 9). It ends by remapping `phase3-windows-list.md` to the rule
   ids the splits left and showing the list to the owner with question 24 (decision 82).
7. **Marking wave W**, after the owner's answer: each lane that owns a spec on the list adds the
   `@env(windows)` proofs and second markers (section 6).
8. Then the prompt's later steps: the remote run on Windows, sanity check 3, the pages, handoff.

## 3. The steps before the fan-out

### P1 `interfaces` (alone, no owner words)

Worktree `purlin-wt/p1-interfaces`, branch `lane/p1-interfaces`. Each item behaviour-neutral
unless named; each commit keeps `--fast` green.

1. **The breaks, called with the scope alone** (decision 94, C1.1): `tests_by_rule=None` in
   `scripts/run/mutation/__init__.py` `run_breaks`; `scripts/run/purlin_run.py` stops passing it
   and deletes `tests_by_rule()`; `specs/run/run_script.md` RULE-16 becomes `The breaks are asked
   for each feature's scope files`, PROOF-16 is reworded to that one case, PROOF-160 and its test
   are deleted; the stub near `dev/test_run_script.py:615` takes three arguments, and its answer
   drops its `rules` entry and with it `'attribution': 'per_scope'` (line 623), so it holds what
   C1.2 says the engine's answer holds.
2. **`mutation.runs_here`** (C1.3) and **`Popen([*command], ...)`** in `execute` (C1.4, Q50).
3. **`marker_problems` moves** to `scripts/mcp/purlin/markers.py` with `NAMES_NOTHING` and
   `RULE_HAS_PROOFS` (C1.5); `scripts/run/reports.py` imports them.
4. **`specs.spec_mistakes` stub** returning `[]` and its call in `payload.build_payload` (C1.6).
5. **Decision 96's second line:** `workflow.UNKNOWN_HOST` (C1.7, L1), and every test and proof
   that quotes the old words: `dev/test_init_scaffold.py` (around lines 809, 976–978, 1011–1031),
   `dev/test_init_update.py` (around line 1411), `specs/init/scaffold.md` RULE-14, PROOF-44, 69,
   70, `specs/init/update.md` PROOF-51, and any line of `dev/test_host.py` that quotes it.
6. **`scaffold.NOT_A_GATE`** lifted (C1.7).
7. **Q75, the template's version goes** (C1.8): `templates/config.json`; `scaffold.write_config`
   writes the seven keys in C1.8's order; `dev/bump_version.sh` (the `DERIVED` array, header
   comment, usage); `.github/workflows/version-check.yml` (both `paths` lists);
   `specs/instructions/purlin_version.md` (Scope drops the template; RULE-3 keeps "a project
   `purlin:init` sets up is stamped with `VERSION`"; PROOF-3, 19 and 20 and their tests go;
   PROOF-7 and 28 to 33 say two JSON files); `dev/test_purlin_version.py` (`CONFIG_TEMPLATE`,
   the paths near line 335, `TEMPLATE_REL`); `specs/init/scaffold.md` RULE-5 and PROOF-54
   ("the template carries exactly six keys, in this order: `gate`, `mutation_engine`,
   `min_strength`, `audit_parallel`, `tests`, `ci`", stated as what it holds, with no clause on
   what it lacks; its test compares the template's key list with that list); `dev/test_init_scaffold.py` near line 392;
   `dev/test_consumer_ci.py` PROOF-84's test (compare with `['version'] + list(template)`);
   `CLAUDE.md` "Releasing a new version" (two derived locations, "covers all three locations").

Acceptance: the named test files, then `--fast`. Report ids and test counts.

### P2 `warnings` (alone, after the owner's answers; it uses OQ1, OQ2, OQ12 and OQ15)

Worktree `purlin-wt/p2-warnings`, branch `lane/p2-warnings`. An item whose question was answered
with its removal option is skipped.

1. **The five spec mistakes** (decision 94; Q33, Q43, Q53, Q54, Q55; the reused-number fault;
   the evidence RULE-5 gap): `specs.spec_mistakes` returns C3.3's lines. Their rules live in the
   spec-format anchor, the one home of what a spec may hold (as Q44 put the tag rules there):
   `specs/_anchors/schema_spec_format.md` RULE-2 (gains: a rule number written twice is warned
   of; its clause "the author assigns them in increasing order and never reuses one" stays, as
   `references/formats/spec_format.md` line 80 says), RULE-3 (a proof line that cannot be read is warned of), RULE-7 (reworded to
   what Purlin reads: the file name is the spec's name, `# Anchor:` makes a spec an anchor, a
   first line naming another feature is warned of), and two new rules, one for two specs with
   one name and one for a `> Scope:` entry that finds no file. One proof per mistake, each read
   from what the status prints, in `dev/test_schema_spec_format.py`. PROOF-3's and PROOF-7's
   checks of this repository's own files go (Q54's third option, which the warning makes
   redundant). `references/formats/spec_format.md` says which mistakes are warned of, in
   "Location", the `> Scope:` row, "Rules format", "Proof format" and the heading line; no
   bump (no field or structure changes), plus in "Rules format" the sentence of section 12,
   item 5 (Q46, Q48, C11).
2. **The two plurals** L8 and L9 (`payload.py`, `specs.py`), and L8's closing
   ` Run purlin:spec <feature>.` (**PENDING OQ2**: options 1 and 2 add it, 3 and 4 do not).
3. **`config_engine.config_problem`** and its constant (C1.9, C3.4). Its rule and proofs are
   lane `settings`'s.
4. **`sign.NOT_A_RULE`** takes C3.6's first line, and `sign.not_a_rule(feature, rule)` returns
   it filled in (C1.10), so no caller counts the values the owner's words take; every existing
   print of the line calls it; the tests in `dev/test_signatures.py` that quote it (around lines
   872–895) follow.
5. **`scaffold.NO_ENGINE_HERE`** (C1.11, OQ12): setup's line for a pytest project on Windows,
   added beside `NO_ENGINE` and used by lanes `scaffold` and `update`; nothing else in
   `scripts/init/scaffold.py` changes. Skipped with OQ12's removal option.
6. Run `--fast` and fix every test in the tree the new warning lines disturb (a fixture whose
   scope names a file it never creates now prints a line). List each file touched.

Acceptance: `dev/test_schema_spec_format.py`, `dev/test_specs_reader.py`, `dev/test_states.py`,
`dev/test_signatures.py`, `dev/test_config_engine.py`, then `--fast`.

## 4. The lanes

Each file that changes has one owner. "Owns" lists every file the lane may write.

| Lane | Owns | Items |
|---|---|---|
| `core` | `scripts/mcp/purlin/{states,payload,status,summary,board,gate,console}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing}.py`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` | Q1, Q2, Q7 (cell), Q20 (cell), Q22 (kind, count, status row), Q37 (strong cell, `to_measure`), d94 nothing measured when the spec names no code files (OQ10), Q65 (status), Q72 (both ends), Q9 (states RULE-40), three-name join, d95 (a section answers for the proofs it lists), d94 bullets 1 and 4 for its specs, Q40 for skill_status |
| `anchors` | `scripts/mcp/purlin/{specs,fingerprint,evidence}.py`; `specs/mcp/{specs,evidence}.md`; `specs/_anchors/*.md`; `dev/test_{specs_reader,schema_spec_format,security,fingerprint,evidence_reader}.py`; `references/formats/{spec_format,anchor_format}.md` | Q44, Q49, Q50 (check), Q51, d95 six tests (the unreadable file, a Windows lock), d94 bullet 4 and Q8 for its specs |
| `settings` | `scripts/mcp/config_engine.py`; `scripts/mcp/purlin/server.py`; `scripts/purlin_python.sh`; `.claude-plugin/plugin.json`; `specs/mcp/{config_engine,server}.md`; `dev/test_{config_engine,mcp_server}.py` | Q65 (reader, tools, refusal to save), Q66, Q67, Q68, Q69, Q70, version write (OQ8), the lookup exits 1 and the server start asks for the soft exit (C9, decision 69), d94 bullet 4 |
| `drift` | `scripts/mcp/purlin/drift.py`; `specs/mcp/drift.md`; `dev/test_drift.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py` | Q30, Q31, Q32 (+ OQ19), Q78, Q65 (the drift tool), d94 bullets 1 and 4, Q40 for skill_drift |
| `run` | `scripts/run/{purlin_run,evidence}.py`; `scripts/mcp/purlin/frameworks.py`; `specs/run/{run_script,evidence_writer}.md`; `dev/test_{run_script,evidence_writer}.py`; `references/formats/evidence_format.md`; `references/supported_frameworks.md` | Q7 (run), Q20 (run), Q21, Q37 (write and print), Q10, Q19, Q9 (RULE-22 goes), d94 suggest every tool, d94 warning seen in a run, d95 remote run of tagged tests, d95 foreign result, run_script RULE-12 at `signed`, Q65 (run), OQ20, OQ6, evidence format 5, d94 bullet 4 |
| `host` | `scripts/run/{host,ci,remote,workflow}.py`; `templates/purlin.yml`; `templates/purlin.azure-pipelines.yml`; `dev/fixtures/consumer-ci/**`; `specs/run/host.md`; `dev/test_{host,remote,host_pathspec,consumer_ci}.py` | Q27, Q28, Q29, d95 fault 1 (`gh`/`az` lookup) and stand-ins, d95 descriptions, d95 S1 pointer in both templates' header comments, Q65 (remote), Q8, d94 bullet 4 |
| `mutation` | `scripts/run/mutation/*.py`; `specs/run/mutation.md`; `dev/test_mutation_adapters.py` | d94 one share per feature (per-rule working goes), Q37 (engine answer), d94/Windows Q4 (mutmut on Windows is no engine), Q38, Q39, d95 fault 2 (`stryker.cmd`) and `.cmd` stand-ins, Q8, d94 bullet 4; clears the mutation file-matching fault |
| `reports` | `scripts/run/reports.py`; `scripts/mcp/purlin/markers.py`; `specs/run/reports.md`; `dev/test_reports.py`; `references/formats/marker_format.md` | Q22 (PROOF-19), Q23, Q24 (the near-miss section of `marker_format.md`, OQ18), `marker_format.md` line 106 (OQ5), d95 `{files}` wording, C9 example, Q8, d94 bullet 4 |
| `scaffold` | `scripts/init/scaffold.py`; `templates/{config.json,gitignore.purlin,evidence-readme.md}`; `specs/init/scaffold.md`; `dev/test_init_scaffold.py`; `dev/test_init_e2e_wiring.sh`; `dev/test_init_e2e_gates.sh`; `dev/init_e2e_walk.sh`; `dev/test_e2e_build_changeset.sh`; `dev/run_tests.sh`; `dev/windows_skip.sh`; `skills/init/SKILL.md`; `specs/skills/skill_init.md`; `dev/test_skill_init.py` | Q14, Q15, Q16, Q60, d94 setup's flag goes, d94/Q37 no tool here, Q9 (RULE-35), d96 both host lines in one place (OQ7), Q65 (setup), d95 six tests (the `gh` test, the walks), C8 walk fixture, init skill: C9, Q14, d96 (both lines, OQ7), d95 S1 pointer in "What the runner runs", d94 bullet 1, Q40, d94 bullet 4 |
| `update` | `scripts/init/update.py`; `specs/init/update.md`; `dev/test_init_update.py`; `dev/fixtures/upgrade-0.9.5/**` | Q17, Q18, Q19 (its side), d94/Q37 no tool here, Q9 (RULE-20), Q65 (upgrade), line endings kept, d94 bullet 4 |
| `signing` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_{signatures,tag}.py` | Q11, Q12 (order, tag line), Q13, d95 fault 4 (the home folder), Q65 (signing), d94 bullet 4 |
| `review` | `scripts/review/{ai_audit,marked_tests}.py`; `specs/review/ai_audit.md`; `dev/test_ai_audit.py`; `dev/test_ai_audit_tests_named.py`; `references/review_criteria.md` | Q12/Q26 (audit reader), Q25, Q9 (RULE-14), ai_audit RULE-15 folded (Q13's reason, OQ14), d94 what the model is shown of strength (C12), Q65 (audit reader), d94 bullet 4 |
| `package` | `scripts/export/package.py`; `specs/export/package.md`; `dev/test_export.py`; `references/formats/package_format.md` | d94 bullet 4 (package RULE-6, Q35), Q22 and Q37 kinds (format 4; OQ3, OQ9), Q34 kept, Q65 (export) |
| `upstream` | `scripts/anchor/upstream.py`; `specs/anchor/upstream.md`; `dev/test_upstream.py`; `dev/test_upstream_notes.py` | Q41, d95 fault 3 (backslash `--path`), line endings kept, d94 bullet 4 |
| `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `dev/capture_doc_screenshots.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json` | Q22 (`To correct` button), Q9 (RULE-4), d94 PROOF-146, Q3–Q6 as built |
| `instructions` | `agents/purlin.md`; `specs/instructions/{purlin_agent,purlin_version,purlin_output}.md`; `dev/test_{purlin_agent,purlin_version,purlin_output}.py`; `dev/bump_version.sh`; `.github/workflows/version-check.yml` | Q9 (the one rule), Q57, Q58 (none), Q74, d94 agent wording, d94 bullets 1 and 4, Q40 for both specs |
| `skills-run` | `skills/{test,audit}/SKILL.md`; `specs/skills/{skill_test,skill_audit}.md`; `dev/test_skill_{test,audit}.py` | Q42, Q45, d94 suggest every tool (row), Q37/d94 strength lines, Q25 (audit skill), Q65 (stop rows), d95 remote run of tagged tests, the test skill's Step 5 (OQ20, S1 pointer), C9, d94 bullet 1, Q40 |
| `skills-author` | `skills/{spec,spec-from-code,build,anchor}/SKILL.md`; `specs/skills/{skill_spec,skill_spec_from_code,skill_build,skill_anchor}.md`; `dev/test_skill_{spec,spec_from_code,build,anchor}.py`; `references/commit_conventions.md`; `references/spec_quality_guide.md`; `references/rule_examples.md` | Q61, Q62, Q64, Q7/Q20/Q37 guide rows, d95 the guide's "The operating system" (CLAUDE.md format step 3), the build skill's "Running them" (OQ5, OQ20), C9, d94 bullets 1 and 4, Q40 (OQ13) |
| `skills-sign` | `skills/{sign,export}/SKILL.md`; `specs/skills/{skill_sign,skill_export}.md`; `dev/test_skill_{sign,export}.py` | Q40, Q52, Q12 row, Q11 clause, C9, d94 bullets 1 and 4 |
| `words` | `references/{glossary,purlin_commands,hard_gates,writing_style}.md`; `CLAUDE.md`; `RELEASE_NOTES.md`; `README.md`; `docs/{running-and-evidence,dashboard,how-purlin-works,getting-started,raising-the-gate-and-upgrading,review-and-signing,specs-and-anchors}.md` | the lines the other lanes hand over (brief), the two one-home paragraphs of C12 in `hard_gates.md`, the unknown-host sentence of `hard_gates.md` (d96), the exit table (C6), `purlin:test`'s row (d94), `--arm-timeout` syntax (OQ11), Q79, C9's one home, `RELEASE_NOTES.md` for 94–96, the `docs/` lines of section 11 that the format changes and this phase make false (CLAUDE.md format step 4) |

`docs/`: lane `words` owns the seven pages above and changes in them exactly the lines of
section 11's list that evidence format 5, package format 4 and the other changes of this phase
make false (CLAUDE.md "Format reference versioning" step 4), `docs/dashboard.md`'s stale lines
among them. No other lane owns a file under `docs/`, and no other page under `docs/` changes in
this phase. The reading of every page against the code (decision 63) still comes last, after
sanity check 3.

## 5. Where every item went

### The 55 readings

| Reading | Lane or step |
|---|---|
| Q2 | `core` |
| Q4 | none: as built |
| Q7 and fault `run_script` | `core` (cell, summary proof), `run` (run lines, evidence word, OQ20), `skills-run` (the test skill's Step 5 quotes the line, OQ20), `skills-author` (guide row; the build skill's `needs <os>`, OQ20), `words` (glossary, hard_gates) |
| Q9 | `instructions` (the one rule, replacing run_script RULE-22, which `run` deletes); the five other specs' clauses: `core`, `dashboard`, `scaffold`, `update`, `review`. `CLAUDE.md`, `design/readme.md` and the writing style keep their lines (C10) |
| Q10 | `run` |
| Q11 | `signing` (and OQ16 for git failing); `skills-sign` (clause); `words` (exit table) |
| Q12 and Q26 | P2 (the words, OQ15), `signing` (order), `review` (audit reader), `skills-sign` (row), `words` |
| Q13 | `signing`; its reason applied to ai_audit RULE-15 by `review` only if the owner says so (OQ14); the guide already says it (call 55) |
| Q15 | `scaffold` |
| Q16 | `scaffold` |
| Q17 | `update` |
| Q18 | P1 (constant), `update` |
| Q19 | `run` (rule, eight proofs, detection moved into the run), `update` (rule and tests go) |
| Q20 and fault `evidence_writer` | `core` (cell), `run` (line, evidence word), `skills-run` (row), `skills-author` (guide), `words` |
| Q21 | `run` |
| Q22 | P1 (move), `core` (kind, count, status row; OQ3), `reports` (PROOF-19), `dashboard` (button), `package` (format), `words` |
| Q23 and fault `reports` RULE-8 | `reports` |
| Q24 | `reports` (`markers.near_miss`, and in `marker_format.md` the section "Comments that are nearly a marker", OQ18); `words` |
| Q25 | `review`; `skills-run` |
| Q27 | `host` |
| Q28 | `host` |
| Q29 | `host`; `words` |
| Q30 | `drift` |
| Q32 and fault `drift` RULE-10 | `drift` |
| Q37 and Windows Q4 | P1 (`runs_here`), P2 (setup's Windows line, OQ12), `mutation` (OQ10, OQ11, OQ12), `run`, `core` (OQ9, OQ10's empty spec), `scaffold`, `update`, `review` (criteria), `skills-run`, `skills-author` (guide), `words` (the one home, C12) |
| Q38 | `mutation` |
| Q39 | `mutation` |
| Q40 | `skills-sign` (the reading, skill_sign); the same reason for the 12 other instruction specs in `core`, `drift`, `scaffold`, `skills-run`, `skills-author`, `skills-sign` (skill_export), `instructions` only if the owner says so (OQ13); the guide already says it (call 55) |
| Q41 and fault `upstream` RULE-15 | `upstream` |
| Q44 | `anchors` |
| Q46 and Q48 | every lane (C11); P2 (one sentence in the spec format) |
| Q49 | `anchors` |
| Q50 | P1 (the start), `anchors` (the check) |
| Q51 | `anchors` |
| Q52 | `skills-sign` |
| Q57 | `instructions` |
| Q58 | none: the ban stays in the agent's fourth never |
| Q60 | `scaffold` (owns `dev/run_tests.sh`) |
| Q61 | `skills-author` |
| Q64 | `skills-author` |
| Q65 | P2 (reader, OQ1), `settings`, `core`, `run`, `host`, `scaffold`, `update`, `signing` (`purlin:sign`), `package` (`purlin:export`), `drift` (the drift tool), `review` (the audit reader), `skills-run`, `words` (exit table, C6) |
| Q66 | `settings` |
| Q67 | `settings`; `words` (release notes) |
| Q68 and Q69 | `settings` (OQ8) |
| Q70 | `settings` |
| Q72 | `core` (both ends) |
| Q74 | `instructions` |
| Q75 | P1 |
| Q76 | none: already reads 0.0.0 |
| Q77 | none: the checks stand |
| Q78 and fault `skill_drift` | `drift` |
| Q79 | `words` |

The "already answered" questions: Q1 `core` (and C11 in every lane); Q3, Q5, Q6 none (as built);
Q8 every lane (C11); Q14 `scaffold`; Q31 `drift`; Q34 `package` (the clause stays, its own rule
after the split); Q56 none (135 stays); Q62 `skills-author`.

### The product faults of phase 2

| Fault | Where |
|---|---|
| `run_script`: a rule waiting on another system told `to fix` | Q7 above |
| `evidence_writer`: some proofs untested reads `not run` | Q20 above |
| `reports` RULE-8: three .NET outcomes | Q23, `reports` |
| `ai_audit` RULE-8 and RULE-14 against decision 93 | fixed on `main` in `6f8a54cc2`; `review` confirms nothing prints `n/a` |
| `drift` RULE-10: Azure DevOps anchors never checked | Q32, `drift` |
| `mutation` RULE-10: tests matched by the end of the path | goes with the per-rule working, `mutation` |
| `upstream` RULE-15: a sync downloads once per anchor | Q41, `upstream` |
| `schema_spec_format`: a reused rule number unreported | P2 |
| `skill_build` RULE-5: the example leaves RULE-3 unmapped | fixed on `main` in `00a9cbfff`; Q61 remains, `skills-author` |
| `skill_status`: line 51 | fixed on `main` in `9d5ed6c2b` |
| `skill_drift`: the ending with no command | fixed on `main` in `b512c73b4` |
| `skill_drift`: the 40-character sha | Q78, `drift` |
| gaps left: run_script RULE-12 at `signed` | `run` |
| gaps left: summary RULE-10's three-name join | `core` |
| gaps left: evidence RULE-5 PROOF-9, PROOF-42 | closed by P2's scope-entry warning; `anchors` keeps RULE-5 as worded |
| gaps left: mutation (1) the timed-out rule's strong cell, (2) `src/` and the other JSON file, (3) matching | `core` (C4.2), `mutation` (Q38, Q39, per-rule goes) |
| gaps left: signatures, the tag's exit code | Q11, `signing` |
| gaps left: schema_spec_format PROOF-2, a number written twice; PROOF-3, RULE-7 | P2 (the other half of PROOF-2, ids written out of order, stays open: section 11) |
| gaps left: purlin_version PROOF-7 | Q74, `instructions` |
| gaps left: update PROOF-61's five keys | Q19 moves it: `run` writes one proof per key |

### Decision 94

| Bullet | Where |
|---|---|
| A rule about a command's instructions says what they tell the agent | `core` (skill_status), `drift` (skill_drift), `scaffold` (skill_init), `skills-run`, `skills-author`, `skills-sign`, `instructions` (purlin_agent) |
| A mistake Purlin can see in a spec is warned of, with its fix | P1 (stub), P2 (lines, rules), `run` (one proof that a run prints one and carries on) |
| Test strength is one share per feature | P1 (call), `mutation`, `dashboard` (PROOF-146), `review` (criteria), `skills-run` (audit skill), `words` |
| A rule that lists several separate things is split by claim | every lane, by C11; the three named by the questions: package RULE-6 (`package`), skill_audit RULE-6 (`skills-run`), skill_test RULE-2, 5, 6 (`skills-run`) |
| The first test run suggests a command for every test tool it recognises | `run` (frameworks, lines), `skills-run` (test skill row), `scaffold` (init skill), `skills-author` (the build skill's "Running them"), `reports` (`marker_format.md` line 106), `instructions` (agent line), `words` |
| Setup's flag for adding a tool goes | `scaffold` (script, spec, tests, init skill), `words` |
| With breaking on, nothing measured means not strong | P1, `mutation`, `run`, `core`, `scaffold`, `update`, `review`, `skills-run`, `skills-author`, `words` |
| The 55 readings | the table above |

### Decision 95

| Bullet | Where |
|---|---|
| A remote run on a system runs only the tests tied to proofs tagged for it | `run` (selection, sections, exit; OQ21), `core` (a section answers for what it lists), `host` (descriptions), `words` (the one home in `hard_gates.md`, C12, and the exit table), and pointers to it from `reports` (`{files}`), `skills-run` (the test skill's Step 5, the audit skill), `skills-author` (the guide's "The operating system"), `scaffold` (the init skill's "What the runner runs"), `host` (both templates' header comments), `words` (`hard_gates.md` lines 116, 140 and 207) |
| The list: 90, trimmed and extended | integration remaps `phase3-windows-list.md`; the owner reads it with OQ24 |
| One more proof per rule, tagged `@env(windows)`, tied by a second comment | wave W (section 6) |
| The six tests: walks and file link Mac only; `gh`, SQLite and the unreadable file run on Windows | `scaffold` (the wiring check stops reporting success; the `gh` test runs on Windows), `anchors` (a Windows lock), wave W (the 13 proofs tagged `@env(macos)`, as W3's first option decided; OQ24 asks only whether the Mac machine it brings is wanted), integration step 8 (SQLite on the runner) |
| The four probable faults fixed first, stand-ins with Windows endings | `host` (`gh`, `az`), `mutation` (`stryker.cmd`), `upstream` (backslash), `signing` (home folder); stand-ins in `host`, `mutation`, `scaffold` |
| The skills start scripts through the interpreter lookup | `scaffold` (init), `skills-run`, `skills-author`, `skills-sign`, `words` (one home), `reports` (example), `settings` (the lookup exits 1; the server start asks for exit 0, C9) |
| The whole path on Windows is not walked; the release notes say so | `words` |

### Decision 96

| Item | Where |
|---|---|
| `No git host found.` | `scaffold` (OQ7); init skill's quoted line, `scaffold` |
| `This git host cannot run tests remotely. Everything on this machine works.` | P1 (the words); `scaffold` (its place in setup, the same as `No git host found.`, OQ7); `words` (`hard_gates.md` lines 128 to 129) |
| The signed panel and `Nothing is waiting for someone to test by hand or to sign.` stay | none |
| The other wordings stand; sanity check 3 reads them | none now |

## 6. Windows

### In this fan-out, with no marking

- **The remote run that runs only tagged tests** (`run`): `--ci`, with or without `--all`,
  selects the proofs whose `@env` names this runner's system; `{files}` holds the test files
  carrying their markers; only their markers count for missing evidence and the exit code; the
  `ci` section holds only those proofs and their rules (C4.3); a feature with none is not run;
  no `needs <System>` line is printed on a runner. With OQ21's recommended answer a test file
  holding tagged and untagged tests is started whole and only the tagged tests' results are
  recorded or counted; a suite whose command takes no `{files}` runs whole under the same rule.
  A tag run (`signed/*`) selects the same way.
- **The four faults** and the **stand-ins** (section 5, decision 95).
- **The six tests**: `scaffold` makes `dev/windows_skip.sh` exit 1 on Windows ("stop reporting
  success where they did not walk"; after Q16 deletes the TypeScript and C# walk, the one file
  that sources it is `dev/test_init_e2e_wiring.sh`, and a suite judged by its ending records it
  as failed there, since it has no "not run"), removes the Windows skip of the `gh` test and
  builds its search path without a link; `anchors` locks the unreadable spec the Windows way
  (`msvcrt` or `CreateFileW` with share mode 0) where `os.name == 'nt'`, keeping `chmod`
  elsewhere; the link test and the walk are left as they are until wave W; SQLite is checked at
  the first real Windows run (integration step 8).
- **The interpreter lookup** (C9).

### Wave W, after the owner reads the list and answers OQ24

Integration first remaps each row of `phase3-windows-list.md` to the rule and proof ids the
splits left, updates each row's test name, and shows the owner the final list. Nothing is marked
before the answer. Then each lane below adds, for each of its rules on the list, one proof
ending `@env(windows)`, worded as the list's draft (at most 60 words), and a second
`purlin: <feature> PROOF-<n>` comment above the named test, plus the "Needs" work of each row.
`scaffold` and `update` also tag the 13 Mac-only proofs `@env(macos)` (decision 95, W3's first
option): scaffold PROOF-36, 90 to 93, 117 to 119, 37, 94, 95 and 96 in `specs/init/scaffold.md`,
update PROOF-31 in `specs/init/update.md` (ids as remapped); their tests and markers do not
change. With OQ24's second option they are left untagged.

| Lane | Specs | Test files |
|---|---|---|
| `settings` | `specs/mcp/config_engine.md`, `specs/mcp/server.md` | `dev/test_config_engine.py`, `dev/test_mcp_server.py` |
| `anchors` | `specs/mcp/evidence.md`, `specs/mcp/specs.md` | `dev/test_fingerprint.py`, `dev/test_evidence_reader.py`, `dev/test_specs_reader.py` |
| `core` | `specs/mcp/states.md` | `dev/test_states.py`, `dev/test_backing_tests.py` |
| `drift` | `specs/mcp/drift.md` | `dev/test_drift.py` |
| `run` | `specs/run/run_script.md`, `specs/run/evidence_writer.md` | `dev/test_run_script.py`, `dev/test_evidence_writer.py` |
| `host` | `specs/run/host.md` | `dev/test_host.py`, `dev/test_host_pathspec.py`, `dev/test_remote.py` |
| `mutation` | `specs/run/mutation.md` | `dev/test_mutation_adapters.py` |
| `reports` | `specs/run/reports.md` | `dev/test_reports.py` |
| `scaffold` | `specs/init/scaffold.md` | `dev/test_init_scaffold.py` |
| `update` | `specs/init/update.md` | `dev/test_init_update.py` |
| `signing` | `specs/review/signatures.md` | `dev/test_signatures.py`, `dev/test_tag.py` |
| `review` | `specs/review/ai_audit.md` | `dev/test_ai_audit.py` |
| `package` | `specs/export/package.md` | `dev/test_export.py` |
| `upstream` | `specs/anchor/upstream.md` | `dev/test_upstream.py` |

Acceptance of wave W: on the Mac, `purlin_run.py --test --all` ties every marker, and every rule
on the list reads `not run` with `windows: no run yet`, counted
`<n> rules to test on Windows: purlin:test --remote`; none reads `partial` or `to fix`; the 13
Mac-only proofs (if tagged) pass on the Mac. Then
`purlin:init` writes this repository's runner file (decision 83) and the owner is asked before
the first remote run.

## 7. Technical calls, ruled

1. `marker_problems` moves into `markers.py` in P1 so the payload can count Q22's comments.
2. `to_correct` is the kind's name in the payload (no person reads it). Its place in the list,
   and whether a comment naming a rule that has proofs counts, are OQ3's. Its payload `text` and
   its line take the singular for one (`1 test comment to correct`) through `summary._words`,
   as every kind does. It holds back `to_tag` as any line does (decision 75).
3. (Moved into OQ3.)
4. `to_measure`'s existence and place are OQ9's.
5. The engine's answer keeps `scope_score` and gains `missing` per feature (C1.2); the evidence
   gains optional `audit.mutation.missing` (C4.2); evidence Format-Version 4 to 5, one bump for
   Q21, Q37, decision 95 and the `no test` meaning.
6. `hostname` already on disk in a local section is dropped on the next write that changes the
   section; nothing rewrites a file for it alone.
7. The local section's `rules` word for "all that could run here passed, a foreign proof waits"
   stays `not run`, as evidence_writer RULE-2 already says; only the cell and the kind change.
8. `FOREIGN_PROOF` (or OQ20's count line) leaves out a foreign proof with no test tied to it: it
   has the no-test line instead.
9. A foreign proof's result in a section is `not run` whatever its tied test did there (C4.4).
10. The eight 0.9.5 signs become run_script proofs with tests in `dev/test_run_script.py`, built
    with `dev/run_project.py`'s `_project` and `_spec`; the detection moves from
    `scripts/init/update.py` into `scripts/run/purlin_run.py`, inside run_script's scope, which is
    its one caller. PROOF-61's five keys become five proofs.
11. The Q19 detection is the one piece of 0.9.5 kept in code (decision 44's exception).
12. Q9's one rule lives in a new feature spec, `specs/instructions/purlin_output.md`, scoped
    `scripts/**` and `templates/**` (C10), and replaces run_script RULE-22: not a global anchor
    (one signature, not one per feature) and not run_script (whose scope is one script). The
    reading removes the clauses of the five other specs only; `CLAUDE.md`, `design/readme.md`
    and the writing style keep their lines.
13. The five spec-mistake rules live in the spec-format anchor, beside the tag rules Q44 put
    there. The anchor carries no `> Global: true` and only `specs/mcp/specs.md` requires it, so
    each new rule is audited and signed once, in `specs`, not once per feature.
14. A doubled proof id and a first line of neither form are not warned of: decision 94 names
    five mistakes.
15. The existing unnumbered-rule warning is a mistake Purlin sees in a spec, so decision 94's
    headline ("warned of, with its fix") reaches it: whether it gains ` Run purlin:spec <feature>.`
    is asked inside OQ2 with the five new lines (L8). The unread-tags warning (L9) is left
    without a command: the tags are an older release's, not a mistake in writing the spec, and
    the upgrade already removes them.
16. Q44: specs RULE-4, 5 and 6 and their proofs go; a case the anchor's proofs do not already
    show (specs PROOF-5 and PROOF-21, the unknown tag read through a full scan) moves into the
    anchor as a proof of its own.
17. Q40's reason beyond skill_sign is the owner's (OQ13): about 280 proofs in 12 specs.
18. Q13's reason applied to ai_audit RULE-15 is the owner's (OQ14).
19. Split by claim applies to every rule that meets C11's test; each lane lists its splits for
    the owner's reading of the readings.
20. Decision 94's "a tool that cannot run on this system counts as no tool" reaches setup and
    the upgrade: on Windows a pytest project is not asked the breaking question. What they
    print then is OQ12's (the existing line would say no engine breaks pytest code, untrue
    there); the constant lands in P2 (C1.11) because both lanes print it.
21. Setup's `Without it test strength is not measured.` stays (decision 96); sanity check 3 reads it.
22. Q65 covers setup and the upgrade: each is a command that saves, so each stops (C1.9).
23. Q68's accepted values are the code's own (C3.5); `auto` is an accepted `mutation_engine`;
    `min_strength` takes 0 to 100 or null; `tests` must be a list and its entries are not read.
24. Q70 answers `{"<key>": null}`.
25. Q28: a detached head with no host variable is "nothing names the branch"; the job's exit
    code stays the tests' (decision 68).
26. Q27: RULE-27 is kept and RULE-26 is retired, its number never reused.
27. Q31: `not_audited` goes from drift's QA view; drift's criteria go from Criteria-Version 9 to 10.
28. Q30: a deleted path counts under every spec whose scope entry covers it (file equal, folder
    prefix, glob match); an uncovered deletion joins the uncovered line.
29. Q32: drift keeps `_looks_like_git` for `upstream.py`'s use and stops using it as a filter.
30. Q38: `x.py` at the root wins over `src/x.py` when both exist; a module that maps to no
    tracked file counts for no feature.
31. Q41: the pin written is the `ls-remote` head, as today; the one fetch is of that head.
32. d95 fault 3: `--path` is turned to `/` before use, so the `> Source:` line and git read it the
    same on every system.
33. d95 fault 4: one helper finds the home folder as git does, `HOME` then `USERPROFILE`, in
    `scripts/mcp/purlin/signatures.py`; `sign.py` uses it.
34. Line endings, two cases. `update.py` edits files the project owns, so `_read` and `_write`
    open with `newline=''` and a rewrite keeps each line's ending as it was (the upgrade rules on
    the Windows list). `upstream.py` writes a copy Purlin composes, so `_write` opens with
    `newline=''`, turns every `\r\n` of the text into `\n`, and the copy holds no carriage
    return on any system, whatever the source held (upstream RULE-11 on the Windows list).
35. `dev/windows_skip.sh` exits 1 on Windows: a suite judged by its ending has only pass and
    fail, so "stop reporting success" is a failure there; after Q16 only
    `dev/test_init_e2e_wiring.sh` sources it, and once its proof is tagged `@env(macos)` a
    Windows runner never starts it.
36. The interpreter lookup, `scripts/purlin_python.sh`, exits 1 with its stderr line when it
    finds no Python 3, so a skill that starts a script through it fails loudly (decision 69).
    The plugin's server start keeps today's exit 0 by the means the manifest already allows:
    `.claude-plugin/plugin.json` starts the server with `"command": "sh"` and `"args"` naming
    the lookup and `server.py`, and its `mcpServers.purlin` entry gains
    `"env": {"PURLIN_PYTHON_SOFT": "1"}`; with that variable at `1` the lookup exits 0 after the
    same line (C9). `command` and `args` do not change, so server PROOF-22 and PROOF-137 hold.
    Lane `settings` owns the lookup, the manifest and `specs/mcp/server.md`, whose scope covers
    the manifest; the lookup joins that scope.
37. Q11: git failing to write the tag exits 1 (the reading's "the ending and the exit code
    agree"); its words are OQ16's.
38. Q12: when every named rule is unknown, signing prints the line(s) and the summary ending.
39. Q25: notes show in the audit reader only; the sign walk's audit block is unchanged.
40. Q52: the frame is `→ Run:`, the one every closing row uses.
41. Q61: the `RULE-N →` lines under `Changeset:` are not indented, as today's example is.
42. Q64: new RULE-10 of skill_spec_from_code (RULE-5 is vacant and not reused).
43. Q72: skill_status PROOF-21 moves to `specs/mcp/states.md` as a proof of RULE-27.
44. Q74: a new proof under purlin_version RULE-7, and a scan of `scripts/` for a written
    `version` field whose value is not read from `VERSION`.
45. Q2: RULE-5 folds into RULE-4 though the result names two claims; the reading chose it.
46. Package format 3 to 4 for the new kinds of `left`: a consumer may need to handle them.
47. `board.py`, `gate.py` and `console.py` join no scope in this phase.
48. The skill specs' proofs that run the product (skill_init PROOF-24, 32–35, 38; skill_status
    PROOF-24) stay as checks that the skill quotes the product.
49. `update._version()` keeps its fallback `'0'`: no reading covers it.
50. The first real Windows run (prompt step 3) shows whether the Windows runner image has
    `sqlite3`; the template is changed then only if it does not.
51. `docs/`: lane `words` fixes the lines of section 11 this phase makes false (call 65); every
    other line waits for the reading of every page (decision 63).
52. A rule listed under another feature (an anchor's rule) shows the strength share of the
    feature that owns it, where it is counted; the dashboard's rule page follows.
53. The engine answer's `missing` is per feature, since Stryker runs once per feature and one
    feature can time out alone.
54. P1 and P2 each have a brief of their own under `phase3-lanes/` (`p1-interfaces.md`,
    `p2-warnings.md`); integration and wave W follow sections 9 and 6 of this plan.
55. The guide already says what Q13's and Q40's readings cite: "One claim, observable" (a rule
    names what a caller sees) and "Written before the test, and not about the test". Nothing is
    added to it for them.
56. One home per new fact (C12): decision 95's runner selection (S1) and decision 94's strength
    (S2) are stated once, in `references/hard_gates.md`, which is the one home of which evidence
    counts; the glossary, `purlin_commands.md`, `marker_format.md`, `review_criteria.md`, the
    spec quality guide and the test and audit skills point at it. A spec's rule about its own
    product is not a copy.
57. The spec-format anchor's RULE-2 keeps "the author assigns them in increasing order and never
    reuses one", which `spec_format.md` line 80 also says; it gains only the warning for a number
    written twice.
58. The two-specs-one-name line ends on `git mv`, the command that renames a file, since
    decision 94 wants each warning to name the command that fixes it (OQ2 shows it).
59. `purlin:audit --arm-timeout` exists only with OQ11's first option; the run script already
    reads the flag, so the skill passes it on, and `purlin_commands.md` gains its syntax.
60. `design/readme.md` has no owner in this phase: nothing in it changes.
61. `.claude-plugin/plugin.json` is lane `settings`'s (call 36): it gains the `env` entry and
    nothing else. P1's Q75 work leaves it as a derived location, and its `version` changes only
    through the bump script.
62. The unknown-rule line is printed only through `sign.not_a_rule(feature, rule)` (C1.10), so
    the number of values the owner's chosen words take never reaches a caller.
63. The exit-code table's cells (C6) are reference prose describing behaviour a decision or
    reading already settles, not a printed line: they reuse the table's own words (`a bad command
    line`, `, and nothing else`, `written and committed`, `no key`), the module docstrings' exit
    paragraphs and scaffold RULE-31's cases, and the one new cell word, `set up`, names what the
    command did. They are not owner questions: the owner reads every page in the docs pass, and
    section 12 lists them, with the other reference sentences of this kind, for that reading.
    Every printed line and every usage line is shown to the owner in a question.
64. `run.md` no longer deletes `local_machine()`'s `or 'unknown'`: evidence_writer RULE-16 promises
    `unknown` where the host reports none, and no decision or reading removes it.
65. CLAUDE.md "Format reference versioning" holds. Steps 1, 2 and 5 are the format owners'
    (`run` for evidence format 5, `package` for package format 4): the format file changes in
    the same commit as the code. Step 4 is lane `words`'s: it owns the `docs/` pages that name
    those formats and the other changes of this phase, and fixes in its own commits exactly the
    lines of section 11's list that they make false, `docs/dashboard.md`'s stale lines
    included. Nothing else in `docs/` changes: decision 63's reading of every page comes last,
    after sanity check 3.
66. The empty-spec case of OQ10's first option is lane `core`'s alone: `core` owns the strong
    cell and the kinds and already reads whether a spec names no files, so the engine and the
    evidence gain nothing for it.

## 8. Owner questions

Most basic first: what a person meets on their own machine every day comes first, then the
breaking tool, then Purlin's own specs, then signing and the audit's printout, then shared
rule sets, and the remote runners last. Each blocks only the items named; every other item of a
blocked lane is built. The recommended option is first, and every question has an option that
removes the thing asked about. Questions 1 to 23 are asked before P2; question 24 with the
Windows list (step 6). In the options, `login` stands for any feature and `3600` for the limit in
use.

**OQ1. A settings file that cannot be read.** Blocks: P2 item 3, and that item in `settings`,
`core`, `run`, `host`, `scaffold`, `update`, `signing`, `package`, `drift`, `review`,
`skills-run`, `words`.
What it is for: every Purlin command reads the project's settings file, where Purlin keeps the
gate, the test command and the other settings; the printed lines below name it by its place in
the project. A slip in a hand edit, such as one comma too many, leaves it unreadable. Today every command then
acts as if there were no settings, and the next save writes over the file. The approved reading:
commands say the file cannot be read and name the line, and saving is refused until it is fixed.
That covers the test run, the status, setup, the upgrade, signing, the evidence package, the
report of what changed, the printout of what the audit found and the tool the agent uses to
change a setting.
Question: what should they print, and what should `purlin:test` then tell you to do?
1. Cause and line: `.purlin/config.json cannot be read: Expecting ',' delimiter at line 4. Fix the file by hand; nothing ran and nothing was saved.`
   The middle is the file reader's own words where the file is not valid settings text. The
   three other causes read, in the same place: `it is not UTF-8 text` (the file was saved in
   another character encoding), `it holds a list where an object belongs` (or `a string`,
   `a number`: the file is valid but is not a set of named settings), and the operating
   system's own message where the file could not be opened at all.
   `purlin:test` then ends on `→ Fix the settings file by hand, then run: purlin:test`.
2. Line only: `.purlin/config.json cannot be read at line 4. Fix it, then run the command again.`
   (with no line named, `.purlin/config.json cannot be read. Fix it, then run the command again.`),
   and `purlin:test` adds no line of its own.
3. No stop: commands carry on as if the file were empty and say nothing; only a save is refused,
   with option 1's line. This reverses most of the reading.

**OQ2. Six mistakes in a spec.** Blocks: P2 items 1 and 2 (L8's ending), and `run` (the proof
that a run prints one).
What it is for: a spec is the file of rules and proofs for one feature. Decision 94 says that
when Purlin can see a mistake in a spec, the status and every test run print one line naming the
spec, the mistake and the command that fixes it, and carry on. The five: a file the spec says it
covers that is not in git, two specs with the same name, a rule number written twice, a proof
line that cannot be read, a first line naming a different feature. A sixth is warned of today
with no command: a line under the rules that has no rule number.
Question: which words should the lines use?
1. Name first, command last:
   `login: > Scope: names src/gone.py, which finds no file in git. Run purlin:spec login.` /
   `specs/auth/login.md and specs/admin/login.md are both named login; only specs/auth/login.md is read. Rename one: git mv specs/admin/login.md specs/admin/<new name>.md` /
   `login: RULE-2 is written twice; the second is read. Run purlin:spec login.` /
   `login: a line under ## Proof cannot be read: - PROOF-7 shows the lockout. Run purlin:spec login.` /
   `login: the first line names checkout, but the file is login.md, so it is read as login. Run purlin:spec login.`
   Today's line for rule lines with no number gains the same ending:
   ``WARNING: 1 line under ## Rules in specs/auth/login.md is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec login.``
2. The same five, each opening with the spec's path, `specs/auth/login.md:`, in place of its
   name; today's line gains the same ending as in 1.
3. The same five with no command at the end; today's line stays as it is.
4. None of them: nothing new is printed and today's line stays as it is. This reverses
   decision 94's warning.

**OQ3. Comments above tests that name nothing.** Blocks: `core` (the line), `dashboard` (its
button), `package` (its row in the evidence package), `words`.
What it is for: a test is tied to a proof by a comment directly above it, such as
`# purlin: login PROOF-3`. A comment that names something no spec has, or names a rule where a
proof is meant, fails the test run, and today the run can still end on `Nothing left to do.` The
approved reading adds a line to the list of work left, `<n> test comments to correct: purlin:build`.
Every line of that list is also a filter button on the dashboard and an entry in the evidence
package (the file Purlin writes for a version, which a system of record reviews), and while any
line stands, signing writes no signed tag (the mark `signed/<version>` on the commit of a
finished version, which you push to release it).
Question: where does the line stand, and what does it count?
1. Second in the list, every comment that fails the run: right after `rules to write a proof for`,
   because a comment is corrected before the test it ties can be fixed. One reads
   `1 test comment to correct: purlin:build`, more `3 test comments to correct: purlin:build`.
   The dashboard gains a `To correct` button.
2. Second in the list, only comments naming something no spec has: a comment naming a rule where
   a proof is meant still fails the run and is not counted, so the list can end on
   `Nothing left to do.` while the run fails.
3. No line: the run fails and names each comment, and the list says nothing. This reverses the
   reading.

**OQ4. A proof with no test, named.** Blocks: `run` (R1), `core` (the reason on the rule's
page), `skills-run`, `skills-author`, `words`.
What it is for: a rule can have several proofs, each shown by a test tied to it by a comment.
When some have a test and one has none, the approved reading makes the rule read `no test`, the
run name that proof, and the list of work left point at `purlin:build`. Today the run prints
`login RULE-3 has no test. Run purlin:build login.` only when no proof of the rule has a test.
Question: how should the run and the rule's page name the proof with no test?
1. In the rule's line: `login RULE-3 has no test for PROOF-7. Run purlin:build login.` (several
   joined `PROOF-7, PROOF-9`); the rule's page gives the reason `no test for PROOF-7`.
2. A second line: today's line, then `login PROOF-7 has no test.`; the page as in 1.
3. Not named: today's line alone and no reason on the page; the proof is found by reading the spec.

**OQ5. Suggesting a command for each test tool.** Blocks: `run` (R4), `skills-run` (the test
command's row), `scaffold` (the setup instructions' line), `skills-author` (the build command's
line), `reports` (the marker format's line), `instructions`, `words`.
What it is for: Purlin runs your tests with the test command kept in the settings. When a project
has tests but no command set, the first test run looks at the project, suggests a command for
each test tool it recognises, and you confirm them together (decision 94); the agent then writes
them into the settings. Today it suggests one tool: `Suggested for pytest: python3 -m pytest ...`
then `Suggested entry: {...}`.
Question: with two tools, say pytest and vitest, what should the run print?
1. A line per tool, one list: `Suggested for pytest: <command>` and `Suggested for vitest: <command>`,
   each followed by what that tool needs added, then one line
   `Suggested tests setting: [<pytest entry>, <vitest entry>]` that the agent writes as it stands.
2. A pair per tool: for each tool `Suggested for <tool>: <command>` then `Suggested entry: <entry>`;
   the agent collects the entries.
3. First tool only, as today; a second is added by editing the settings. This reverses that part
   of decision 94.

**OQ6. The Python command suggested on Windows.** Blocks: `run` (the Windows entry).
What it is for: the command suggested for a Python project starts `python3 -m pytest`. Python
installed on Windows from python.org has no `python3` command; it always has the launcher `py`,
and has `python` only when that box was ticked at install.
Question: what should the suggestion say on Windows?
1. `py -3` on Windows: `py -3 -m pytest ...` on Windows, `python3 -m pytest ...` elsewhere.
2. `python` on Windows: `python -m pytest ...`; fails where `python` was not added at install.
3. `python3` everywhere, as today; a Windows user edits the command before confirming.
4. No Python suggestion on Windows: the run says it found pytest and asks you to set the
   command yourself.

**OQ7. Where setup says there is no git host.** Blocks: `scaffold` (the places of L1 and L2,
and the setup instructions' lines).
What it is for: the git host is where your code is pushed; Purlin can run tests remotely only
on GitHub and Azure DevOps. Setup ends with a line such as `Gate strong. Suites pytest. Git host github.`
Decision 96 gives `No git host found.` for a project with no remote (a remote is the address
your code is pushed to); today that case reads `Git host not read from a remote` inside the
line. The upgrade names the missing remote its own way, with the command that adds one.
Decision 96 also gives a line for a remote on a git host Purlin cannot use (one that is neither
GitHub nor Azure DevOps): `This git host cannot run tests remotely. Everything on this machine works.`
Whatever you answer here, that line stands in the same place as `No git host found.`, and the
line before it then names no git host either; with option 4 it stays a line of its own after
`Gate strong. Suites pytest.`
Question: where does `No git host found.` stand?
1. Its own line, setup only: `Gate strong. Suites pytest.` then `No git host found.`; the upgrade
   keeps `No git remote, so there is no runner to read this workflow. Add one with: git remote add origin <url>`.
2. Inside the line: `Gate strong. Suites pytest. No git host found.`; the upgrade as in 1.
3. Its own line in setup and in the upgrade, whose line then no longer names `git remote add`.
4. No line: setup says nothing when there is no remote. This reverses decision 96's first line.

**OQ8. The answers of the tool that changes one setting.** Blocks: `settings` (Q66, Q68, Q69, the
version write).
What it is for: Purlin gives the agent a tool to read or change one setting. The approved
readings: a save that fails says the setting was not saved and why; a change with no value, or
with a value Purlin does not take for a setting it knows (a gate of `gold`), is refused naming
what it takes, and the file is left as it was. The `version` setting is written by setup from
Purlin's own version.
Question: what should the tool answer, and may it change `version`?
1. These answers, `version` refused: `The setting was not saved: <cause>.` /
   `A change needs a value; nothing was saved.` /
   `"gold" is not accepted for gate; it takes passed, strong or signed. Nothing was saved.` /
   `version is written by purlin:init from Purlin's own version; nothing was saved.`
   What each setting takes, in the same place. The agent names each setting by the word in
   the settings file, so the answer uses that word: `gate` (how far every rule must get) takes
   `passed, strong or signed`; `mutation_engine` (which tool breaks the code on purpose; `auto`
   lets Purlin pick from the language, `stryker_net` is the one for C#) takes
   `none, auto, mutmut, stryker or stryker_net`; `min_strength` (the share of breaks the tests
   must catch; `null` means no minimum) takes `a whole number from 0 to 100, or null`;
   `audit_parallel` (how many rules the AI audit reads at once) takes
   `a whole number from 1 to 16`; `tests` (the test commands) takes `a list`; `ci` (the git host
   that runs tests remotely; `azure` is Azure DevOps) takes `github, azure or none`.
2. These answers, `version` allowed: the same, and `version` may be changed like any setting.
3. Only the failed save: only a save that fails is answered; any value is taken, as today. This
   reverses readings Q68 and Q69.

**OQ9. Strength not measured, in the list of work left.** Blocks: `core` (`to_measure`, the weak
cell), `dashboard` (its button), `words`, `skills-run`, `skills-author`, `package` (its row in the
evidence package).
What it is for: at the gates `strong` and `signed`, Purlin can break your code on purpose and
count how many breaks your tests catch (test strength). When that is on and nothing could be
measured, because the breaking tool is not installed or ran past its time limit, decision 94
makes the rule weak with a reason naming the fix, such as `pip install mutmut`. A weak rule is
counted today as `rules to strengthen: purlin:build`, which sends you to write better tests when
the fix is installing a tool.
Question: how should the list of work left count a rule that is weak only because nothing was
measured?
1. A line of its own, just before `rules to strengthen`: `3 rules to measure: purlin:audit`. The
   rule reads `weak`, and its reason names what to install or which limit to raise, after the
   words `strength not measured: `, for example
   `strength not measured: mutmut is not installed: run "pip install mutmut"`;
   `purlin:audit` measures again once that is done.
2. Under strengthen: `3 rules to strengthen: purlin:build`, like any weak rule, with the same
   reason as in 1. No new line; the command does not fit the cause.
3. Not weak: the AI audit alone judges such a rule, as today, and only the run's printed line
   says strength was not measured. This reverses that part of decision 94.

**OQ10. Two more ways to measure nothing.** Blocks: `mutation` (the no-report case), `core`
(the empty-spec case and where it is counted), `words` (the table of work left).
What it is for: decision 94 says that with the code broken on purpose, nothing measured means the
rule is not strong. Besides a breaking tool that is not installed or ran out of time, two more
cases measure nothing: the tool ran and wrote no report, or the spec names no code files, so
there was nothing to break. Today both leave the rule strong on the AI audit alone. A spec that
names no code files is already listed as `rules to tie to their files: purlin:spec`, but only at
the gate `signed`.
Question: how should these two cases read, and where are they counted?
1. Both weak, each counted where its fix is (follows decision 94): the missing report reads
   `strength not measured: mutmut ran and wrote no report: run purlin:audit again` and is
   counted with the other rules to measure (OQ9); the empty spec reads
   `strength not measured: the spec names no code files: run purlin:spec login` and is counted
   as `rules to tie to their files: purlin:spec`, which then also stands at the gate `strong`
   when the code is broken on purpose.
2. Both weak, both counted with the rules to measure, `purlin:audit`, with the same reasons as
   in 1; for the empty spec that command does not fix it, and its reason names the one that does.
3. Only the missing report is weak; a spec naming no code files stays strong on the AI audit
   alone, as today. This departs from decision 94 for that case.
4. Neither: only a tool not installed or out of time makes the rule weak, the letter of reading
   Q37. This departs from decision 94 for both cases.

**OQ11. When the breaking tool finds no .NET, or runs out of time.** Blocks: `mutation` (the two
sentences), `skills-run` (the audit command's new option), `words` (its syntax).
What it is for: when the breaking tool cannot measure, the run prints why and the rule's reason
repeats it, and decision 94 wants that reason to name the command that fixes it. Three reasons
already do, for example `mutmut is not installed: run "pip install mutmut"`. Two do not. For C#
projects, when .NET itself is missing the reason reads `dotnet is not installed, so no engine
breaks C# code`. When the tool runs past its time limit, 3600 seconds per feature unless set
otherwise, the reason ends `raise --arm-timeout to give it longer`, naming an option you cannot
give `purlin:audit` today.
Question: which words, and should `purlin:audit` take a time limit?
1. Name the fix, with a new option: `dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`;
   `the engine timed out after 3600 s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`.
   `purlin:audit` gains `--arm-timeout <seconds>`: how many seconds the breaking tool may run
   for one feature. Its usage line, in the audit command's instructions and in the command
   list, reads `purlin:audit --arm-timeout <seconds>  Give the breaking tool longer per feature`.
2. Name the fix, no new option: the .NET line as in 1; the time line ends
   `measure nothing: run purlin:audit again`. Nothing new to learn; a feature that ran out of time
   once may run out again.
3. Today's words for both, and no new option. This keeps a reason that names no fix.

**OQ12. Python's breaking tool on Windows.** Blocks: P2 item 5, `mutation` (the reason),
`scaffold` and `update` (their line).
What it is for: the breaking tool for Python, mutmut, installs on Windows but does not run there.
Decision 94 says such a tool counts as no tool, and the AI audit alone judges test strength.
Setup and the upgrade would then print today's line for a project no tool can break,
`Mutation testing is off: no engine breaks pytest code, so the AI audit alone judges test strength.`,
which is untrue on Windows, and the test run prints a reason of its own.
Question: what should setup, the upgrade and the test run say on Windows?
1. Say why: setup and the upgrade print
   `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.`;
   the run prints `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`.
2. Short: `Mutation testing is off: mutmut does not run on Windows.` and `mutmut does not run on Windows`.
3. Nothing: on Windows setup, the upgrade and the run print no line about it.

**OQ13. Proofs that describe a broken copy of the instructions.** Blocks: that item in `core`,
`drift`, `scaffold`, `skills-run`, `skills-author`, `skills-sign` (the export command's spec),
`instructions`.
What it is for: each Purlin command is a file of instructions the agent follows, and a spec of
Purlin's own holds the rules about what those instructions say. Many of their proofs describe a
check rather than a fact: "a copy of the instructions with this sentence removed is reported".
The approved reading took such proofs out of the sign command's spec and kept each broken copy
as a second check inside the test of the proof it guards, because a proof says what is true, not
how the test checks it. The same reason fits the other command specs, the spec of the agent's
own instructions and the spec of how Purlin's version is set. Each proof taken out is one fewer
to audit and sign; every check still runs.
Question: should the reading apply to those specs too?
1. Every spec of this kind: about 280 proofs leave 12 specs, and each broken-copy check stays
   inside a test.
2. The sign command's spec only, as the reading says: the 12 others keep their proofs as they are.
3. None: the sign command's spec keeps them too. This reverses the reading.

**OQ14. A rule of the audit printout that only a program sees.** Blocks: `review` (that one rule).
What it is for: the command that prints what the AI audit found for one rule has a rule of
Purlin's own about what happens inside the program when you ask about a rule the project does
not have: one step hands the next a blank where it could have handed an empty record. No person
sees that difference; what a person sees is the command's printout and whether it reports
failure, which reading Q26 extends with a line naming the missing rule. Reading Q13 removed a rule of the
same kind from signing, because a rule says what a caller sees.
Question: should this rule fold into the rule about what the command prints?
1. Fold it: one rule fewer to sign; its one proof moves under the rule about the printout.
2. Keep it as a rule of its own.

**OQ15. Naming a rule that does not exist.** Blocks: P2 item 4, `signing`, `review`,
`skills-sign`, `words`.
What it is for: when you name a rule no spec has, signing prints
`login RULE-9 is not a rule any spec has.`, signs the others and reports failure, and printing
what the audit found for that rule prints nothing. The approved reading adds the next step,
printed last above the summary, and has the audit printout print the same line.
Question: which words?
1. Next step as a sentence: `login RULE-9 is not a rule any spec has. Run purlin:status login to see its rules.`
2. Next step as a pointer: `login RULE-9 is not a rule any spec has. Its rules: purlin:status login`
3. No next step: today's line, printed last and by the audit printout. This drops that part of
   the reading.

**OQ16. A signed tag git could not write.** Blocks: `signing` (that line), `words`.
What it is for: at the gate `signed`, once nothing is left to do, signing writes the signed tag,
`signed/<version>`, the mark on the commit of a finished version that you push to release it.
When git itself fails to write it, for example because the signing key cannot be read, signing
today prints the line for a tag that already exists and reports success, which is wrong. The
change to report failure follows reading Q11; the words are yours.
Question: what should signing print?
1. One line: `No tag: git could not write signed/1.2.0: <git's own message>.`, and it reports failure.
2. Two lines: `git could not write the tag signed/1.2.0.`, then git's own message as git gave it,
   and it reports failure.
3. No line of Purlin's: git's own message alone, and it reports failure.

**OQ17. The heading above the audit's notes.** Blocks: `review` (Q25), `skills-run`.
What it is for: when the AI audit reads a rule it may leave a note, for example that a proof is
longer than 60 words; a note never makes a rule weak. The approved reading prints the notes when
you print what the audit found for one rule, after the part headed `What the audit found`.
Question: what heading goes above the notes?
1. `What the audit noted`, which reads like the heading above it.
2. `Notes`.
3. No heading: each note follows the findings, starting `Note:`.
4. Not printed: the notes stay in the evidence alone, as today. This reverses the reading.

**OQ18. The reason given for a nearly right comment.** Blocks: `reports` (Q24's why), `words`.
What it is for: `purlin:build` finds comments above tests that are nearly right, suggests the
fix and says why. The approved reading: a comment naming `RULE-30`, one character from `RULE-3`,
is offered `PROOF-3` when RULE-3 has exactly one proof, and nothing when it has several. Today
the why reads `` `RULE-30` is one character from `RULE-3`, which login has ``.
Question: what should the why say when the fix is the rule's one proof?
1. `` `RULE-30` is one character from `RULE-3`, which login has; a comment names its one proof, `PROOF-3` ``
2. `` `RULE-30` is one character from `RULE-3`, whose one proof is `PROOF-3` ``
3. No suggestion for a comment one character from a rule id.

**OQ19. Drift and a shared rule set kept in a text file.** Blocks: `drift` (the text-file part
of Q32).
What it is for: an anchor is a set of shared rules copied into your project from a source and
pinned to one version; drift tells you when a source has moved on. The approved reading makes
drift try every source and say `error` when one cannot be read, so an Azure DevOps source is no
longer skipped. A source can also be a plain text file, whose version is a fingerprint of its
text: a short code worked out from every character of the file, which changes whenever any
character does, so two copies with the same code hold the same words. Drift skips those today.
Question: what should drift do with an anchor whose source is a text file?
1. Compare the text: drift reads the file and reports `behind` when its fingerprint no longer
   matches the pin, as `purlin:anchor sync --check` does. A source that is only words, with no
   file, has nothing to compare and is left out.
2. Skip it, as today, and the rule says drift checks repositories only.
3. Report `error`, since it is not a repository.

**OQ20. Proofs waiting for Windows, on the Mac.** Blocks: `run` (R3), `skills-run` (the test
command's instructions quote the line), `skills-author` (the build command's instructions name
it).
What it is for: a proof can be tagged for one system, `@env(windows)`, when what it checks
could differ there. On your Mac such a proof cannot be proven, so every test run prints a line
for it today: `login PROOF-4 needs Windows; this machine is macOS. Run purlin:test --remote.`
Decision 95 adds a Windows proof to about 87 rules, so a full run would print about 87 such
lines, while the list of work left already says `87 rules to test on Windows: purlin:test --remote`.
Question: what should a run on the Mac print about proofs waiting for Windows?
1. One line per system: `87 proofs need Windows; this machine is macOS. Run purlin:test --remote.`
2. One line per proof, as today: about 87 lines on every full run.
3. No line: the list of work left alone says it.

**OQ21. What a Windows runner does with a file of mixed tests.** Blocks: `run` (decision 95's
selection only).
What it is for: a remote run sends your tests to a machine the git host lends, such as a Windows
one (a runner), and brings the results home. Decision 95 says a runner runs only the tests tied
to proofs tagged for its system. Test tools are started with a list of test files, not of single
tests, so a file holding one Windows test and twenty others is started whole.
Question: when a file holds tests tagged for Windows and tests that are not, what does the
Windows runner do with the others?
1. Run the file, count only the tagged: the whole file runs; only the tests of Windows-tagged
   proofs are recorded and can fail the run. The same for every test tool; a run may take
   longer than its tagged tests alone.
2. Pick single tests: Purlin names each tagged test to the test tool, so only those run. The
   shortest run; it needs a way to name one test for each of the seven tools, and some have none.
3. Count everything: every result the file gives is recorded and can fail the run, so a Windows
   failure in a test nobody tagged for Windows blocks its rule. This drops the sorting of results.

**OQ22. A remote run that cannot name its branch.** Blocks: `host` (Q28's refusal).
What it is for: a remote run commits its results to the branch it ran on, reading the branch's
name from the git host. The approved reading removes the guess used when nothing names the
branch: the commit goes on the branch the checkout is on, or is refused with a line saying no
branch could be read. It happens only when a run is started by hand on a bare commit: a
checkout of one commit by its code, with no branch name attached, so git itself cannot say which
branch it is on.
Question: what should the refusal say?
1. `No branch could be read from the git host or from git, so the results were not committed.`
2. `No branch: nothing was committed.`
3. No line: the results are not committed and nothing is printed.

**OQ23. A remote run on another branch.** Blocks: `host` (Q29), `words`.
What it is for: the runner file Purlin writes, which tells the git host when to run the tests
remotely, starts only on a run branch (the branch Purlin pushes for each remote run, named
`run/<your branch>-<commit>`) or on a signed tag. Someone can change that file or start it by hand
on another branch; the run then tests and writes nothing. Today it prints
`Tag run: nothing is written. This run reruns the tests on <branch>.`, calling it a tag run.
Question: what should such a run print?
1. `This run is on feature/x, which is neither a run branch nor a signed tag: the tests ran and nothing is written.`
2. `This branch is not a run branch: nothing is written.`
3. The tag run's line, as today.
4. No line about it.

**OQ24. A Mac machine in this repository's runner file** (asked with the Windows list). Blocks:
the `@env(macos)` marking in wave W (`scaffold`, `update`).
What it is for: decision 95 made three checks Mac only: the walk that takes a new project from
setup to the signed tag, the check that setup adds nothing to a C# project's tests, and the check
that an old dashboard page linked into an install is replaced by a copy. It chose to tag their
13 proofs for macOS, `@env(macos)`, as W3's first option said. The runner file is the file
Purlin writes into a project to tell the git host when to run its tests remotely and on which
machines; it gets one machine for each system any proof is tagged for, so this repository's runner file would run a Mac
machine beside the Windows one, running these 13 on every remote run; your own Mac proves them
too. A Windows runner never starts them either way, since it runs only tests tagged for Windows.
Question: tag the 13 for macOS?
1. Tag them, as decided: every remote run also runs the 13 on a Mac machine the host lends,
   which adds time and uses the host's Mac minutes.
2. Leave them untagged: no Mac machine; only your Mac proves them. This reverses that part of
   decision 95.

## 9. Integration (alone, after every lane merged)

1. Merge the lanes by fast-forward in section 10's order; each lane rebased and reran first.
2. Resolve the failures lanes reported in files they do not own, to the contracts; any file.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH`; `bash dev/run_tests.sh`: 0 failed.
4. `python3 dev/build_report.py`; look at the page with playwright from the `.venv`, headless,
   at 1500, 1280, 1024, 768 and 390 pixels in both themes; commit the built page,
   `scripts/report/purlin-report.html`, once (the copy at the root is ignored by git).
5. `python3 scripts/run/purlin_run.py --test --all`: every marker tied, every rule passing;
   then the same with `--commit`.
6. Greps, each empty outside `dev/plans/`, `RELEASE_NOTES.md` and `dev/fixtures/upgrade-0.9.5/`:
   `--add` in `scripts/init`, `skills/init`, `references`; `tests_by_rule`; `attribution`;
   `per_test`; `rules_by_feature`; `default_branch` (except the test name
   `test_it_allocates_ids_against_the_default_branch` in `dev/test_skill_spec.py`, and where
   `.purlin/evidence/**` and `.purlin/tests.md` list that test); `not_audited` in `scripts/mcp/purlin/drift.py`;
   `set_up_by_095` in `scripts/init`; `def main` in `scripts/mcp/config_engine.py`;
   `python3 "${CLAUDE_PLUGIN_ROOT}` in `skills/`; `Git host not read` (under every option of
   OQ7 the summary line names no git host where none is read, for no remote and for a host
   Purlin cannot use alike, C3.1);
   `neither GitHub nor Azure DevOps`; `init_e2e_walk`; `test_e2e_build_changeset`;
   `test_init_e2e_gates`; `Process.Start` in `dev/test_security.py`; `"version"` in
   `templates/config.json`. And C12: under `references/` and `skills/`, the S1 and S2 sentences
   stand only in `references/hard_gates.md`; every other file names that file instead.
7. Write `dev/plans/phase3-interfaces.md`: what was built where it differs from the contracts,
   every word a lane chose, every split, the ids, the test counts, section 12 of this plan
   copied as it stands under the heading "Words chosen for the owner to read", and a section
   "Docs and the formats" naming evidence format 5 and package format 4, the `docs/` lines lane
   `words` changed for them (call 65), and any line of section 11's list it left, with why.
8. Remap `phase3-windows-list.md` to the new ids and test names; its drafts already say
   `gh.cmd` for scaffold RULE-44 and host RULE-12 (C8), and upstream RULE-11's "no carriage
   return" stands (call 34). Show it to the owner with OQ24; after the answer, run wave W
   (section 6), then the prompt's step 3.

## 10. Merge order

P1, P2, then: `core`, `anchors`, `scaffold`, `run`, `mutation`, `reports`, `host`, `settings`,
`drift`, `update`, `signing`, `review`, `package`, `upstream`, `dashboard`, `instructions`,
`skills-run`, `skills-author`, `skills-sign`, `words`.

The files are disjoint, so no merge conflicts in any order. The order keeps `main` green between
merges: `core` first, so later lanes adjust their own tests to its cells (C7); `scaffold` before
`run`, because C8's walk fixture tags the greeting proof `@env(<this machine's system>)`, which
holds before and after decision 95, and must be on `main` before `run`'s `--ci` selects only
tagged proofs (C7); `run` before `update`, because `update` deletes the 0.9.5 detection `run`
stops calling; `mutation` after `run`; `words` last, since it describes what the others built.

## 11. Not placed in this phase

- `docs/` lines found stale. Lane `words` owns these pages and fixes exactly these lines, with
  what evidence format 5 and package format 4 make false in the same pages (call 65); every
  other line waits for the reading of every page (decision 63), which comes last:
  `docs/running-and-evidence.md` 102–113, 228–235, 296–395 and 348; `docs/dashboard.md` 13 and
  67; `docs/how-purlin-works.md` 102 and 160–162; `docs/getting-started.md` 177;
  `docs/raising-the-gate-and-upgrading.md` 24 and 63; `docs/review-and-signing.md` 80;
  `docs/specs-and-anchors.md` 91–94 (a number written twice is now warned of; a new id) and
  140–144 (which run proves a proof with no `@env`). Line numbers are those of `main` at
  `b172b3c1c`.
- schema_spec_format PROOF-2's other half: rule ids written out of order are not warned of and
  are not tested. Decision 94 names five mistakes and this is not one of them; no decision
  settles what, if anything, is said. Left as it stands.
- `dev/sign_project.py` `Project.proofs()` writes a retired runtime file, and
  `dev/test_vocabulary.py` is a table of retired words: both for decision 44's sweep; the first
  is a frozen helper.
- `upstream.is_repository` reads an Azure DevOps address as free text, so an anchor cannot be
  added from one: no reading covers `add`; seen, not changed.
- A package checked out with CRLF fails `--check` on Windows: no decision; seen.
- `scripts/report/src/rule.js` draws `←`, outside CLAUDE.md's glyph list: no reading.
- scaffold's gap (a), the runner job's result as a scaffold promise; host RULE-17 and RULE-30
  notes; server's four unmarked tests: none is in decisions 94–96 or the readings.
- `purlin:init` without `--yes` hanging once with its output piped: not looked into.

## 12. Words chosen for the owner to read

Reference prose that describes behaviour a decision or reading settles is not an owner question:
the owner reads every page in the docs pass (decision 63). These sentences were chosen by the
planning agent; each lane writes its sentence exactly as below, and integration copies this
section into `phase3-interfaces.md` (section 9, step 7) so the owner reads them there. A mark
**PENDING OQ<n>** means the sentence is written only as that question's answer leaves it.

1. `references/purlin_commands.md`, "Exit codes", the whole table (lane `words`; contracts C6,
   whose notes give each cell's source and its marks, **PENDING OQ1** and **PENDING OQ16**):

   | Command | 0 | 1 | 2 |
   |---------|---|---|---|
   | `scripts/run/purlin_run.py --test`, `--audit` | everything asked happened | a tied test failed or did not run; evidence is missing; a marker names nothing a spec has; no settings file; the settings file cannot be read; a project set up by 0.9.5 and not upgraded; no test command; for `--audit` at `strong` and `signed`, a rule read is weak or could not be audited | a bad command line |
   | `scripts/run/purlin_run.py --ci` | the tests tied to the proofs tagged for this runner's system passed | one of those failed or could not run, and nothing else | a bad command line |
   | `scripts/review/sign.py` | written and committed, the walk closed, nothing to tag, or the tag already exists | no key; the commit was not made; a named rule no spec has; the tag refused for work or results not committed, no version, or a package not committed; git could not write the tag; the settings file cannot be read | a bad command line |
   | `scripts/export/package.py` | written, or the check matched | the check did not match; the project states no version; the package could not be written; the settings file cannot be read | a bad command line |
   | `scripts/review/ai_audit.py` | a rule was printed | the rule is not in the project; the settings file cannot be read | a bad command line |
   | `scripts/init/scaffold.py` | set up | the settings file cannot be read | a bad command line, not a git repository, or no such project root |
   | `scripts/init/update.py` | nothing pending, or applied | the settings file cannot be read | no project |
   | `scripts/mcp/purlin/markers.py --near-misses` | always | never | a bad command line |

2. `references/hard_gates.md`, the `Left to do` table, the `no_scope` row's "When it applies"
   cell (lane `words`; **PENDING OQ10**, option 1; with options 2 to 4 the row stays):

   ```
   at `signed`, the rule is not signed and its spec names no files; at `strong` and `signed` with mutation testing on, its strong cell reads `weak` because its spec names no code files
   ```

3. `references/hard_gates.md`, lines 128 to 129, in place of the sentence that begins "A project
   whose git host is neither GitHub nor Azure DevOps" (lane `words`; decision 96):

   ```
   Purlin runs tests remotely on GitHub and Azure DevOps. On any other git host the settings read `ci: none`, and setup prints `This git host cannot run tests remotely. Everything on this machine works.`
   ```

4. `references/formats/package_format.md`, "What is left", the sentence above the table of
   kinds (lane `package`; **PENDING OQ3**; with OQ3's removal option the sentence stays as it
   is):

   ```
   Each rule is counted under one kind, the first that applies, and a kind at zero has no line. `to_correct` counts test comments, not rules, and is carried by the project:
   ```

5. `references/formats/spec_format.md`, "Rules format", one sentence added (P2; Q46, Q48, C11):

   ```
   A new id is one more than the highest the file has held since it was last written whole; a number deleted since then is never used again.
   ```
