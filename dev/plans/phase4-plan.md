# Phase 4: sanity check 3 applied, cut by ownership of files

Written by the planning agent on 2026-09-30, from `sanity-3.md` and the owner's answers of
decision 98. One step runs alone first (P1 `shared`), then 20 lanes run together (fan-out 1,
the product), then one integration agent alone; after fan-out 1 is merged, 4 lanes run together
(fan-out 2, the pages), then one integration agent alone, which retakes the screenshots last.
`phase4-contracts.md` is the contract between lanes: every agent builds to it and none chooses.
One brief per lane is under `phase4-lanes/`.

The worktree `/Users/richlabarca/LocalCode/purlin-wt/winfix-1` holds two Windows fixes of its
own (the runner templates install `sqlite3` on Windows; the upgrade on Windows commits the
runner file it wrote). Nothing here repeats them, and P1 starts only once that branch is merged
into `main`, since lanes `host` and `update` own the files it changes.

## 1. Rules for every lane

- **Worktree, branch, scratch.** Lane `<lane>` works in `/Users/richlabarca/LocalCode/purlin-wt/p4-<lane>`
  on branch `p4/<lane>`, created from `main` after P1 merged (fan-out 1) or after fan-out 1's
  integration (fan-out 2), with its own scratch folder `<session scratchpad>/p4-<lane>`. It
  writes only the files its brief lists as owned.
- **Frozen:** `dev/skill_checks.py`, `dev/mcp_project.py`, `dev/sign_project.py`,
  `dev/run_project.py`, `dev/reports_project.py`, `dev/conftest.py`, `dev/fake_claude.py`. No
  item of this phase needs one of them changed. A lane that needs a helper writes it in its own
  test file.
- **No generated file is staged:** `scripts/report/purlin-report.html`, `purlin-report.html`,
  `.purlin/evidence/**`, `.purlin/tests.md`, `.purlin/report-data.js`,
  `.github/workflows/purlin.yml`, `docs/images/**`. Integration rebuilds them once.
- **Tests.** `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH` first. Run the lane's own test
  files whole with `.venv/bin/python -m pytest <files> -q`, then `bash dev/run_tests.sh --fast`
  in the worktree. The full sweep runs once per fan-out, at integration.
- **Deliberate breaks.** Before breaking code on purpose to see an assertion fail, the agent
  confirms the break runs only under a test that uses `dev/fake_claude.py` or no model, with no
  real `claude` on `PATH`, and reaching no real git host, `gh`, `az` or network service. It
  restores the file with `git checkout -- <that file>`, never `git checkout -- specs/`.
- **Proofs** (contracts K7): one case, at most 60 words, a marked test of its own. A change to a
  format's parsing or emission updates its file under `references/formats/` in the same commit
  (CLAUDE.md "Format reference versioning"; K4).
- **Instruction lengths** (decision 80): a change to a skill or to `agents/purlin.md` cuts as
  many lines as it adds. Ceilings: status 100, test 120, build 130, init 250, audit 105, sign
  185, export 90, spec 210, spec-from-code 130, drift 150, anchor 160, agent 135.
- **Clean release** (decision 44): what is retired is deleted outright; no test that a removed
  thing is absent; nothing added to `dev/test_vocabulary.py`.
- **A call no decision or contract makes:** build the rest, leave that thing as it is, report it.
- **Commits** on the lane branch, with the prefixes of `references/commit_conventions.md`, each
  ending with the attribution lines the session gives. No push, no tag, no pull request, no
  `purlin:audit`, no `purlin:sign`, no real `claude` program.
- **Before merging:** rebase on `main`, rerun the lane's files and `--fast`, fix the lane's own
  files where an earlier merge changed a result that K6 predicts, report the rest.
- **No reviewer follows a lane.** Each brief ends on a self-check (K7) the lane runs and
  reports.
- **Report:** each spec's highest RULE and PROOF id and its `> Highest-Rule:`; tests before and
  after; every split; every word the lane chose; every call left; every failure in a file it
  does not own; the self-check's results.

## 2. The order

1. The `winfix-1` branch is merged into `main` (not part of this plan).
2. **P1 `shared`**, alone (section 3).
3. **Fan-out 1**: 20 lanes at once on disjoint files (section 4). Merge order in section 8.
4. **Integration 1**, alone (section 7).
5. **Fan-out 2**: 4 lanes at once on the pages (section 9).
6. **Integration 2**, alone (section 10), the screenshots last.

## 3. The step alone before fan-out 1: P1 `shared`

Two items cross the files of several lanes and change a line other lanes' tests read, so they
land alone. Nothing else does: no frozen helper changes, and every other shared line has one
owner and is consumed through K6.

1. **One ending for a project with no spec** (faults 2 and 3, §6 item 13; K1.1):
   `status.no_spec_lines(project_root)`, and its four callers, `status.sync_status`,
   `scaffold.next_step`, `update._print_ending` and `purlin_run.main`; `NO_SPECS` goes. Rules:
   states RULE-39 says the two lines by state, PROOF-46 becomes the set-up-with-code case, and
   two new proofs take the other states; scaffold RULE-34 and PROOF-34 say setup ends on the
   same two lines, with one proof per state that setup can meet (code, no code); update gains
   one proof that an upgrade of a project with no spec ends on the two lines; run_script PROOF-104
   stays. `skills/init/SKILL.md` line 185, which quotes setup's old ending, quotes the new one.
   Every test in the tree that quotes the old lines follows.
2. **The warning for rule lines with no number** (A14, §6 item 44; K1.2): `payload.py`'s line;
   schema_spec_format PROOF-2 and PROOF-45 quote the new lines, PROOF-13 and PROOF-14 say the
   status prints no line containing `is not numbered`, and their tests follow.

Acceptance: `dev/test_states.py`, `dev/test_init_scaffold.py`, `dev/test_init_update.py`,
`dev/test_run_script.py`, `dev/test_schema_spec_format.py`, `dev/test_skill_init.py`, then
`--fast`. Brief: `phase4-lanes/p1-shared.md`. Worktree `purlin-wt/p4-p1-shared`, branch
`p4/p1-shared`.

## 4. Fan-out 1: the lanes

Each file that changes has one owner. "Owns" lists every file the lane may write. Section 5
says where each item came from; the count is the number of items in the lane's brief.

| Lane | Owns | Items |
|---|---|---|
| `anchors` | `scripts/mcp/purlin/{specs,fingerprint,evidence}.py`; `specs/mcp/{specs,evidence}.md`; `specs/_anchors/*.md`; `dev/test_{specs_reader,schema_spec_format,security,fingerprint,evidence_reader}.py`; `references/formats/spec_format.md`; `dev/test_e2e_required_rules.sh` | 10 |
| `core` | `scripts/mcp/purlin/{states,payload,status,summary,board,gate,console}.py`; `specs/mcp/{states,summary}.md`; `dev/test_{states,summary,backing_tests,failing}.py`; `skills/status/SKILL.md`; `specs/skills/skill_status.md`; `dev/test_skill_status.py` | 13 |
| `host` | `scripts/run/{host,ci,remote,workflow}.py`; `templates/purlin.yml`; `templates/purlin.azure-pipelines.yml`; `dev/fixtures/consumer-ci/**`; `specs/run/host.md`; `dev/test_{host,remote,host_pathspec,consumer_ci}.py` | 11 |
| `scaffold` | `scripts/init/scaffold.py`; `templates/{config.json,gitignore.purlin,evidence-readme.md}`; `specs/init/scaffold.md`; `dev/test_init_scaffold.py`; `dev/test_init_e2e_wiring.sh`; `dev/run_tests.sh`; `dev/windows_skip.sh`; `skills/init/SKILL.md`; `specs/skills/skill_init.md`; `dev/test_skill_init.py` | 20 |
| `reports` | `scripts/run/reports.py`; `scripts/mcp/purlin/markers.py`; `specs/run/reports.md`; `dev/test_reports.py`; `references/formats/marker_format.md` | 7 |
| `run` | `scripts/run/{purlin_run,evidence}.py`; `scripts/mcp/purlin/frameworks.py`; `specs/run/{run_script,evidence_writer}.md`; `dev/test_{run_script,evidence_writer}.py`; `references/formats/evidence_format.md`; `references/supported_frameworks.md` | 19 |
| `mutation` | `scripts/run/mutation/*.py`; `specs/run/mutation.md`; `dev/test_mutation_adapters.py` | 3 |
| `settings` | `scripts/mcp/config_engine.py`; `scripts/mcp/purlin/server.py`; `scripts/purlin_python.sh`; `.claude-plugin/plugin.json`; `specs/mcp/{config_engine,server}.md`; `dev/test_{config_engine,mcp_server}.py` | 5 |
| `drift` | `scripts/mcp/purlin/drift.py`; `specs/mcp/drift.md`; `dev/test_drift.py`; `references/drift_criteria.md`; `skills/drift/SKILL.md`; `specs/skills/skill_drift.md`; `dev/test_skill_drift.py` | 8 |
| `update` | `scripts/init/update.py`; `specs/init/update.md`; `dev/test_init_update.py`; `dev/fixtures/upgrade-0.9.5/**` | 6 |
| `signing` | `scripts/review/sign.py`; `scripts/mcp/purlin/signatures.py`; `specs/review/signatures.md`; `dev/test_{signatures,tag}.py`; `references/formats/signature_format.md` | 10 |
| `review` | `scripts/review/{ai_audit,marked_tests}.py`; `specs/review/ai_audit.md`; `dev/test_ai_audit.py`; `dev/test_ai_audit_tests_named.py`; `references/review_criteria.md` | 8 |
| `package` | `scripts/export/package.py`; `specs/export/package.md`; `dev/test_export.py`; `references/formats/package_format.md` | 5 |
| `upstream` | `scripts/anchor/upstream.py`; `specs/anchor/upstream.md`; `dev/test_upstream.py`; `dev/test_upstream_notes.py`; `references/formats/anchor_format.md`; `dev/test_e2e_external_refs.sh`; `dev/test_e2e_anchor_authority.sh`; `dev/setup-external-refs.sh` | 9 |
| `dashboard` | `scripts/report/src/**`; `scripts/mcp/purlin/report_data.py`; `dev/build_report.py`; `dev/capture_doc_screenshots.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report.py`; `dev/test_purlin_report_board_layout.py`; `dev/test_report_refresh.py`; `dev/fixtures/report/*.json` | 10 |
| `instructions` | `agents/purlin.md`; `specs/instructions/{purlin_agent,purlin_version,purlin_output}.md`; `dev/test_{purlin_agent,purlin_version,purlin_output}.py`; `dev/bump_version.sh`; `.github/workflows/version-check.yml` | 5 |
| `skills-run` | `skills/{test,audit}/SKILL.md`; `specs/skills/{skill_test,skill_audit}.md`; `dev/test_skill_{test,audit}.py` | 7 |
| `skills-author` | `skills/{spec,spec-from-code,build,anchor}/SKILL.md`; `specs/skills/{skill_spec,skill_spec_from_code,skill_build,skill_anchor}.md`; `dev/test_skill_{spec,spec_from_code,build,anchor}.py`; `references/commit_conventions.md`; `references/spec_quality_guide.md`; `references/rule_examples.md` | 12 |
| `skills-sign` | `skills/{sign,export}/SKILL.md`; `specs/skills/{skill_sign,skill_export}.md`; `dev/test_skill_{sign,export}.py` | 4 |
| `words` | `references/{glossary,purlin_commands,hard_gates,writing_style}.md`; `CLAUDE.md`; `RELEASE_NOTES.md` | 6 |

The phase-3 table is kept, with three changes: `dev/test_e2e_required_rules.sh` joins
`anchors`, the two other anchor shell suites and `dev/setup-external-refs.sh` join `upstream`,
and `references/formats/signature_format.md` joins `signing` (no lane owned them; nothing in
the last is planned to change); the scaffold row names only the files that still exist; and
`words` no longer owns `README.md` or any page under `docs/`, which are fan-out 2's. P1 writes
in the files of `core`, `scaffold`, `update`, `run` and `anchors` before any lane starts.

No lane owns: `README.md` and `docs/**` (fan-out 2), `dev/plans/**`, `.github/workflows/purlin.yml`,
`design/**`, the frozen helpers, `dev/suites.py`, `dev/browser_launch.py`, `dev/manual/**`,
`dev/test_vocabulary.py`, `conftest.py`, `.purlin/**`, `VERSION`, `scripts/mcp/__init__.py`,
`scripts/mcp/purlin/__init__.py` and `scripts/report/purlin-report.html`. Integration alone
writes in them.

## 5. Where every item went

### The owner's answers (decision 98)

| Answer | Where |
|---|---|
| A1 the README's leaving line | fan-out 2, `pages-start` |
| A2 the ten-minute path | fan-out 2, `pages-start` (K8) |
| A3 examples in documentation | `run` (the pytest entry, K2.5), `skills-author` (the fourth reason, K5.4) |
| A4 code no caller can reach | `skills-author` (K5.4) |
| A5 a library's public names | `skills-author` (the guide, K5.3), `review` (the criteria point at the guide) |
| A6 a list of like inputs | `skills-author` (K5.3), `review` |
| A7 a rule number never reused | `anchors` (format 19, the schema rule), `skills-author` (K5.5), every spec-owning lane (K4.2) |
| A8 `> Requires:` names anchors only | `anchors` (code, format, rules), `run` (evidence format wording), `package` (package format wording), `skills-author` (K5.4 step 4), `dashboard` (comments), `words` (glossary), `review` (K6), fan-out 2 |
| A9 signing a rule whose spec names no files | `signing` (signing-6), `skills-sign` |
| A10 setup asks whether it may commit | `scaffold` (K3.9, K5.6), `skills-author` (K5.8), `words` (K5.9) |
| A11 no key-upload or protection advice | fan-out 2, `pages-signing` |
| A12 no program to wait with | `host` (host-1, host-2), `skills-run` (K3.11), `words` |
| A13 capitals on the dashboard | `words` (K5.2); the page does not change |
| A14 the warning's prefix | P1 (K1.2) |
| A15 no test tool found | `run` (run-5), `skills-run`, `words` |

### Product faults (section 7)

| Fault | Where |
|---|---|
| 1 status before the first run | `reports` (markers read with no suite; reports RULE-3; `marker_format.md`) |
| 2, 3 the no-spec ending | P1 |
| 4 jest and `{files}` | `run` |
| 5 one untested proof among tested ones | `core` |
| 6 the breaking tool's folders | `scaffold` |
| 7 stored system words | `core` (reasons), `anchors` (selection reason), `host` (runner reasons) |
| 8 the Python command | `run` (the doctest option, A3), `skills-run` (the comparison, K5.7); the interpreter stays as decision 97 gives it (section 11) |
| 9 npm assumed | `run` (run-14) |
| 10 the Stryker line | `scaffold` (scaffold-5) |
| 11 the default shown twice | `scaffold` (scaffold-6) |
| 12 `.gitignore` named twice | `scaffold` (scaffold-13) |
| 13, 14 the runner lines | `scaffold` (scaffold-9, scaffold-10) |
| 15 pull a deleted branch | `host` (host-3, host-4) |
| 16 the upgrade's second run | `update` |
| 17 a proof not named | `run` (run-12) |
| 18 no-scope and `waiting` | `core` |
| 19 `--help` | `run` (run-1) |
| 20 the evidence README at `passed` | `scaffold` |
| 21 the dirty heading | `run` (run-13) |

### Messages (section 6)

| Item | Where | Item | Where |
|---|---|---|---|
| 1 | `scaffold` | 24 | `review`, `signing`, `dashboard` (K3.1) |
| 2 | `scaffold` | 25 | `review`, `dashboard` (K3.3) |
| 3 | `host` | 26 | `dashboard` |
| 4 | `anchors` | 27 | `review`, `dashboard` (K3.2) |
| 5 | `core` | 28 | `scaffold`; `words` quotes it |
| 6 | `upstream` | 29 | `scaffold` |
| 7 | `upstream`, `drift` | 30 | `upstream` |
| 8 | `host` | 31 | `signing` |
| 9 | `dashboard` | 32 | `mutation` |
| 10 | `dashboard` | 33 | `settings` |
| 11 | `scaffold`, `core`, `settings` (K3.4) | 34 | `anchors` |
| 12 | `core`, `drift`, `upstream` (K3.5) | 35 | `host` |
| 13 | P1 | 36 | `scaffold` |
| 14 | `run` | 37 | `settings`, `upstream`, `host`, `drift` |
| 15 | `reports` | 38 | `host`; `words` for the prose word `arm` |
| 16 | `reports` | 39 | `core`, `drift`, `package`, `signing`, `review`, `scaffold` |
| 17 | `run` | 40 | `run`, `reports` |
| 18 | `host` | 41 | `drift`, `run` |
| 19 | `drift` | 42 | `settings` |
| 20 | `anchors` | 43 | `words` (A13) |
| 21 | `core`, `update` (K3.6) | 44 | P1 (A14) |
| 22 | `package`, `signing`, `skills-sign` (K3.7) | 45 | `scaffold`, `words`, `skills-author` (K3.13) |
| 23 | `signing` | | |

### Where the instructions failed the agent (section 8)

| Item | Where |
|---|---|
| 1 the position file | `skills-author` (K5.4 step 5) |
| 2 when the comments are committed | `skills-author` (K5.4 step 5, K5.8); what setup writes: A10 |
| 3 the reasons for an untied test | `skills-author` (K5.4) |
| 4 tie every test against no private rule | `skills-author` (A4, K5.4) |
| 5 a library's names | `skills-author` (A5, K5.3) |
| 6 tables of inputs | `skills-author` (A6, K5.3) |
| 7 `> Requires:` | `anchors`, `skills-author` (A8) |
| 8 the ending's order | `skills-author` (K5.4) |
| 9 ask the breaking question and pass it | `scaffold` (K5.6) |
| 10 `sync_status` without the root | `core`, `skills-author`, `skills-sign`, `skills-run`, `instructions` (K3.12) |
| 11 nothing reads specs before setup | `skills-author` (K5.4); the page, fan-out 2 |
| 12 the install line | `run` (run-14), `skills-run` (K5.7) |
| 13 the comparison with the project's own command | `skills-run` (K5.7) |
| 14 a detached head | `skills-author` (K5.4) |
| 15 example proofs that break the guide | `anchors` (`spec_format.md`), `upstream` (`anchor_format.md`); the pages, fan-out 2 |
| 16 the report's length | `skills-author` (K5.4 step 6) |
| 17 what is public | `skills-author` (K5.4) |
| 18 commented-out tests | `skills-author` (K5.4) |
| 19 the handoff paragraph | integration 1 (K9) |

### Statements that break a decision (section 4)

Items 1, 2 and 3: fan-out 2, `pages-start`. Item 4: integration 1 (K9).

### True statements no rule covers (section 5)

37 rows from the docs and 29 groups of messages, counted as the research for this plan split
them (`sanity-3.md` gives 67 in all; the difference is how the groups are split).

| Row | Where | Row | Where |
|---|---|---|---|
| 1 Python 3.9 | `instructions` (purlin_output) | 20 the tag's SSH signature | `signing` |
| 2 setup commits none | `scaffold`, as A10's rules | 21 the columns by gate | covered: states RULE-36 |
| 3 no background job | `instructions` (purlin_output) | 22 the upgrade's gate question | `update` |
| 4 the three run lines | `run` | 23 the `tests` setting line | `update` |
| 5 the page reads a run at once | `core` | 24 the workflow line | `update` |
| 6 the README's command table | fan-out 2, `pages-start` | 25 `[y/N]`, empty declines | `update` |
| 7 printed lines on the start pages | fan-out 2, `pages-start` | 26 `kept the previous bytes at` | `update` |
| 8 `.gitignore` names both | `scaffold` | 27 `> Format-Version: N` | `anchors` |
| 9 `No board data yet...` | `dashboard` | 28 what `purlin:spec` takes | `skills-author` |
| 10 the uncommitted notice | `dashboard` | 29 `> Stack:` | `anchors` |
| 11 the theme remembered | `dashboard` | 30 merges and two pins | `skills-author` (skill_spec) |
| 12 `every test` at `passed` | `scaffold` | 31 an anchor repository | `skills-author` (skill_anchor) |
| 13 the 60-second search | covered: host PROOF-70, 80 | 32 survey to position file | `skills-author` |
| 14 mutmut advice | `run` moves it to `supported_frameworks.md`; the page drops it | 33 every rule a draft | `skills-author` |
| 15 the walk's order | `signing` | 34 no implementation in a rule | `skills-author` |
| 16 a proof shows its tag | `signing` | 35 `--plugin-dir` | `scaffold` |
| 17 the walk's audit lines | `signing` (after K3.1) | 36 drift infers the role | `drift` |
| 18 `What did you see, in one line:` | `signing` | 37 an evidence conflict | `run` |
| 19 a skipped rule waits | `signing` | | |

| Group | Where | Group | Where |
|---|---|---|---|
| 1 the gate question and choices | `scaffold` | 16 the audit printout | `review` |
| 2 the skip line with no remote | `scaffold` | 17 the walk | `signing` |
| 3 the lines under a runner file | `scaffold` | 18 `.purlin/tests.md` | `run` |
| 4 `purlin:anchor add` and `sync` | `upstream` | 19 no credentials | `host` |
| 5 the package's refusals | `package` | 20 the engine logs | `mutation` |
| 6 the upgrade's lines | `update` | 21 the run's argument refusals | `run` |
| 7 drift's refusals and eng view | `drift` | 22 the suite-tail block | `run` |
| 8 the settings warnings | `core` (`gate.py` joins states' scope) | 23 the timeout reasons | `run` |
| 9 the suite problems | `reports` | 24 the unknown feature | `run` |
| 10 the near-miss reasons | `reports` | 25 the remote run's lines | `host` |
| 11 the settings tool | covered: server proofs | 26 the report reasons | `reports` |
| 12 the no-project-root answer | `settings` | 27 the dashboard's hovers and empty states | `dashboard` |
| 13 the uncommitted-specs block | `core` | 28 the theme control's label | `dashboard` |
| 14 the anchor lines of the status | `core` | 29 the templates' words | `scaffold`, `host` |
| 15 the plural test-comments line | `core` | | |

### The orchestrator's rulings

| Ruling | Where |
|---|---|
| every product fault fixed unless it needs words or behaviour no decision gives | the faults above; what is left is in section 11 |
| the security anchor's covered files narrowed to what exists | `anchors` |
| the runner templates' matrix sentence says what decision 97 says | `host` (K2.6) |
| every stored system word a person reads becomes `Windows`, `macOS`, `Linux/Unix` | `core`, `anchors`, `host`, and the references that quote reasons (K3.8) |
| `purlin_run.py --help` prints the usage and exits 0 | `run` (run-1) |

Section 9 of `sanity-3.md` also names signatures RULE-68, `<c> case(s) added` as the code prints
it: `signing`. Section 3's 184 false statements are fan-out 2's, by page.

## 6. Technical calls, ruled

1. P1 carries the no-spec ending and the warning's shape alone, because each changes a line
   read by tests in four lanes' files and one lane's. Everything else shared has one owner and
   reaches the others through K6.
2. "The tree holds code" is K1.1's list of extensions over `git ls-files --cached --others
   --exclude-standard`, outside `specs/`, `.purlin/`, `.github/` and `docs/`, so an untracked
   project counts.
3. `> Requires:` narrows in lane `anchors` (`specs.rule_refs`, `fingerprint`,
   `specs.spec_mistakes`), which merges second, after `core`; the only test outside its files that relies on a
   feature requiring a feature is ai_audit PROOF-49's (lane `review`, K6).
4. `> Highest-Rule: <n>` is a metadata line: it changes no fingerprint (metadata is not hashed)
   and no count, and the parser reads nothing new from it. Proof ids keep "one past the highest
   in either copy" (K5.5).
5. Setup commits with `git add -- <paths>` then `git commit -m <subject> -- <paths>`, which
   commits only those files and works on a branch with no commit yet (checked in a scratch
   repository). `--yes` answers yes; the init skill passes `--yes` on the person's yes and runs
   the script with empty input otherwise (K5.6).
6. The Stryker line prints only where the engine is not installed, using the engine modules'
   own constants (scaffold-5).
7. `mutmut_paths` finds a `tests` or `test` folder, or a folder of `test_*.py` files, at any
   depth, never takes a folder named `bench`, `benchmark` or `benchmarks` as the tests, and
   never takes `doc`, `docs`, `examples` or those three as source.
8. The jest entry puts `{files}` before `--reporters`, since jest's own parser reads every
   word after an array option as another reporter (checked against jest 30's yargs).
9. The pytest entry carries `--doctest-modules` where a listed file of the project names it
   (K2.5); the interpreter stays `python3`/`py -3` as decision 97 gives it, and the test skill
   compares the suggestion with the project's own command before asking (K5.7).
10. Fault 17: decision 97 names the proof, so `has no test.` stays only for a rule with no proof.
11. Fault 18: the no-files override of the signed cell applies only once the strong cell is met;
    before that the signed cell reads `waiting`, as the glossary says.
12. Fault 1: with no suite set, markers are read from every tracked file whose extension has a
    test reader in `markers.py`, so a marked proof reads `not run` and counts `to test`.
13. Fault 5: a proof counts as listed in a section only where the section names a test for it.
14. Test strength shows the whole-number part (floor) on every surface.
15. `scripts/mcp/purlin/gate.py` joins `specs/mcp/states.md`'s scope, so its warnings have a
    spec (section 5, group 8).
16. One evidence README for every gate, worded with no step's name (fault 20, decision 50).
17. `workspace` becomes `project root` wherever a person reads it (§6 item 37).
18. The Python 3.9 and no-background-process rules live in `specs/instructions/purlin_output.md`,
    whose scope is every file Purlin prints from; the 3.9 run proofs skip where no Python 3.9
    is on the machine, and one proof parses every file under `scripts/` as Python 3.9.
19. The docs' two rules live in a new spec, `specs/instructions/purlin_docs.md`, written by
    fan-out 2's `pages-start`, which owns the pages it reads.
20. Integration 1 regenerates this repository's runner file by running setup with empty input
    (it commits nothing then) and commits it as `chore: the runner file, with the templates of phase 4`.

## 7. Integration 1 (alone, after every lane of fan-out 1 merged)

1. Merge the lanes by fast-forward in section 8's order; each lane rebased and reran first.
2. Resolve the failures lanes reported in files they do not own, to the contracts; any file.
3. `export PATH=/opt/homebrew/opt/dotnet@8/bin:$PATH`; `bash dev/run_tests.sh`: 0 failed.
4. `python3 dev/build_report.py`; look at the page with playwright from the `.venv`, headless,
   at 1500, 1280, 1024, 768 and 390 pixels in both themes; commit
   `scripts/report/purlin-report.html` once.
5. Run setup on this repository with empty input (call 20) and commit the runner file.
6. Write K9's paragraph into `dev/plans/handoff.md`.
7. `python3 scripts/run/purlin_run.py --test --all`, then with `--commit`: every marker tied;
   the status prints no warning for this repository (the security anchor's three lines are gone).
8. Greps, each empty outside `dev/plans/`, `RELEASE_NOTES.md`, `docs/`, `README.md` and
   `dev/fixtures/upgrade-0.9.5/`: `NO_SPECS`; `WARNING:`; `workspace` in `scripts/` and
   `references/`; `the CI workflow`; `finished red`; `no run on macos`; `no run on windows`;
   `Run: purlin:anchor`; `is not a gate`; `Nothing backs this rule`; `from Claude Code`; `◐`
   and `←` in `scripts/report/src/`; `proven?`; `-> ` in `scripts/init/scaffold.py`; `1 rules`;
   `The last 1 commits`; `to have one proposed`.
9. Write `dev/plans/phase4-interfaces.md`: what was built where it differs from the contracts,
   every word a lane chose, every split, the ids and `> Highest-Rule:` per spec, the test counts,
   section 12 of this plan copied under "Words chosen for the owner to read", and the lanes'
   self-check results.

## 8. Fan-out 1 merge order

P1, then: `core`, `anchors`, `host`, `scaffold`, `reports`, `run`, `mutation`, `settings`,
`drift`, `update`, `signing`, `review`, `package`, `upstream`, `dashboard`, `instructions`,
`skills-run`, `skills-author`, `skills-sign`, `words`.

The files are disjoint, so no merge conflicts in any order. The order keeps `main` green between
merges, following K6: `core` before `anchors`, `run`, `update` and `dashboard` (the reasons,
the settings lines, the no-files line, which schema_spec_format PROOF-55's test quotes);
`anchors` before `review` and `run` (the requires change, the selection reason); `host` before `scaffold` and `update` (the runner reasons); `scaffold` before
`run`, `update` and `instructions` (the gate lines, the commit on `--yes`); `reports` before
`run`; `words` last, since it describes what the others built.

## 9. Fan-out 2: the pages

After integration 1. Four lanes, each owning the pages `sanity-3.md` groups together:

| Lane | Owns | Items |
|---|---|---|
| `pages-start` | `README.md`; `docs/index.md`; `docs/getting-started.md`; `docs/how-purlin-works.md`; `specs/instructions/purlin_docs.md`; `dev/test_purlin_docs.py` | 8 |
| `pages-running` | `docs/running-and-evidence.md`; `docs/dashboard.md` | 5 |
| `pages-signing` | `docs/review-and-signing.md`; `docs/regulated-workflow.md`; `docs/raising-the-gate-and-upgrading.md` | 6 |
| `pages-specs` | `docs/specs-and-anchors.md`; `docs/spec-from-code.md`; `docs/working-together.md`; `docs/team-workflow.md` | 6 |

Each page is read again against the code as merged and rewritten to say what is (decision 63,
K8): every false statement of `sanity-3.md` section 3 for that page corrected, every sample of
printed output taken from a real run in a scratch project, the writing style held, diagrams
plain mermaid, every statement covered by a rule, a statement no rule covers cut or handed to
integration 2 as a rule to add. No lane touches `docs/images/`.

## 10. Integration 2, and the merge order of fan-out 2

Merge order: `pages-start`, `pages-running`, `pages-signing`, `pages-specs` (the files are
disjoint; `pages-start` first, since its test reads the start pages).

1. Merge by fast-forward, each lane rebased and reran first.
2. Write the rules the lanes handed over, each with its proof and test, in the spec the lane
   named; or cut the statement where no rule can hold it, and report which.
3. `bash dev/run_tests.sh`: 0 failed.
4. Retake the two screenshots with `dev/capture_doc_screenshots.py` from the rebuilt dashboard
   and the fixtures, look at them, and commit them.
5. Check every link between pages and into `references/` resolves, and every mermaid block
   parses.
6. `python3 scripts/run/purlin_run.py --test --all --commit`.
7. Append to `dev/plans/phase4-interfaces.md` a section "The pages": each page, the statements
   cut, the rules added, and the samples' scratch runs.

## 11. Left out, and why

- **The interpreter of the suggested Python command** (fault 8): decision 97 gives
  `python3 -m pytest` and `py -3 -m pytest` word for word. The product keeps them; the test
  skill tells the agent to compare with the project's own command (K5.7). Changing the
  command's interpreter is the owner's to decide.
- **Stryker's install command in a yarn or pnpm project** still names npm: C3.2 keeps it word
  for word and no decision changes it (fault 9 names jest-junit's line only).
- **Proof numbers have no recorded highest**: A7 names rule numbers. A deleted top proof on
  `origin/main` can still be handed out again. A question for the owner.
- **`→ Fix:`** in the settings tool's no-project-root answer is not `→ Run:`; §6 item 37 asks
  only for the word `workspace`, and no decision settles the arrow line's word there.
- **The settings warnings for `min_strength`** (`"min_strength" is not a number; ...`) name no
  command: they are not in section 6, so they get their proofs (group 8) and keep their words.
- **The status line `<name>: (source rejected: <reason>)`**: not in section 6; its proof is
  added and its words kept.
- **The next sanity check's project with a failing test** (`sanity-3.md` section 9, last
  line): for the next check, not this phase.
- **Section 10 of `sanity-3.md`** stays dropped, for the reasons it gives.
- **The phase-3 calls left for the owner** (`phase3-interfaces.md`, "Calls left") that no item
  of sanity check 3 reaches, and the Windows calls left after wave W: not in this phase.
- **Nothing else**: every answer, fault, message, instruction fault and uncovered statement has
  a lane in section 5.

## 12. Words chosen for the owner to read

Every sentence a person reads that no decision or answer gives, chosen by the planning agent.
Each lane writes it exactly as here; integration 1 copies this section into
`phase4-interfaces.md`. Placeholders are as in the contracts' opening.

**Setup and the upgrade** (`scripts/init/scaffold.py`, `skills/init/SKILL.md`,
`templates/evidence-readme.md`, `references/commit_conventions.md`):

- `Commit the files setup wrote? [y/N] `
- `Committed <sha7>, the files setup wrote:`
- `The files setup wrote are staged and not committed: <git's own message>.`
- the commit subject `chore(init): set up Purlin at the gate <gate>`, and its row in
  `references/commit_conventions.md`: `` The files setup wrote, once a person agrees or `--yes` is passed ``
- `→ Run: purlin:init to set this project up.`
- `→ Run: purlin:spec-from-code to write the specs this code already implies.`
- `→ Run: purlin:spec <name> to write the first spec.`
- `This is not a git repository. Run git init, then purlin:init.`
- `<value> is not accepted for gate; it takes passed, strong or signed. Reading it as <gate>.`
- `<value> is not accepted for gate; it takes passed, strong or signed. Nothing was written.`
- `<framework>: <the engine's not-installed reason>`
- `skipped the runner file (<reason>)`
- `  it runs on <images>, the systems a proof in specs/ is tagged @env for that this machine is not.`
- `copied <source> to <rel>`
- the evidence README's first sentence `What a run leaves behind for each feature: each proof's result on each operating system, the commit and the time.` and `` A run on your own machine writes `local/`, and `--commit` commits it under your own git identity. ``
- the init skill's third question and its "Run it" sentence (K5.6)

**The status and the settings** (`scripts/mcp/purlin/status.py`, `gate.py`, `states.py`,
`scripts/mcp/purlin/server.py`):

- `<value> is not accepted for gate in .purlin/config.json; it takes passed, strong or signed. Reading it as passed; set it with purlin:init --gate <gate>.`
- `<value> is not accepted for audit_parallel in .purlin/config.json; it takes a whole number from 1 to 16. Reading it as 4; fix the file by hand.`
- `1 spec names no files, so its tests run every time: <name>. Run purlin:spec <name> to add its > Scope: line.`
- `<n> specs name no files, so their tests run every time: <names>. Run purlin:spec with each name to add its > Scope: line.`
- `<name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.`
- `passed on <Systems>` joined with ` and ` (the reason's other words are the stored forms made readable)
- `A change needs a key; nothing was saved.`
- `<key> is now <value>; saved to .purlin/config.json.`
- `No Purlin project root at <root>: .purlin/config.json is not there. That root came from <source>.`
- `→ Fix: pass project_root to this tool, or set PURLIN_PROJECT_ROOT to the project root (in .claude/settings.json "env" for the project), or run purlin:init there.`
- `The project root, the folder holding .purlin/. Defaults to the root the server resolved at startup.`

**Specs** (`scripts/mcp/purlin/specs.py`, `evidence.py`, `references/formats/spec_format.md`,
`specs/_anchors/security_no_dangerous_patterns.md`):

- ` Run purlin:init --update to remove them.` after the unread-tags line
- ` Run purlin:test <feature> to write it again.` and ` Run purlin:test --remote to write it again.` after each ignored evidence file
- the field `> Highest-Rule: <n>` and its sentences in K4.1
- the `> Requires:` row and "Requires behaviour" in K4.1
- the security anchor's Description: the sentence `` The scope names file types `scripts/` does not hold today, so a file in one of them is watched from the day it arrives. `` goes, and `in the form each of the six file types the scope names spells them` reads `in the form each file type the scope names spells them`

**The run** (`scripts/run/purlin_run.py`, `scripts/run/evidence.py`, `scripts/mcp/purlin/frameworks.py`):

- ` Run purlin:test --remote without --commit.`
- ` Run purlin:status to see the specs this project has.`
- ` Run purlin:<action> --arm-timeout <seconds> to give it longer.`
- ` Check its command and report in the tests setting of .purlin/config.json, then run purlin:test.`
- ` Check that its test ran and was not skipped, then run purlin:test.` and ` Check that their tests ran and were not skipped, then run purlin:test.`
- ` Fix the tests setting in .purlin/config.json, then run purlin:test.`
- `# Tests at <sha7>, with changes that are not committed`
- `yarn add --dev jest-junit` and `pnpm add --save-dev jest-junit` in the jest-junit line

**Test comments** (`scripts/run/reports.py`, `scripts/mcp/purlin/markers.py`):

- `<file>:<line> names <feature> <ID> and no test follows it. Put the comment directly above a test, or run purlin:build to repair it.`
- `The report's <case> matches <n> tests in <files>, so its result is not counted. Give the tests different names, then run purlin:test.`
- `<file>:<line> names <feature> <RULE-N>, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.`

**A remote run and the runner file** (`scripts/run/remote.py`, `host.py`, `workflow.py`, the templates):

- `purlin:test --remote waits for the run with the GitHub CLI, gh, which is not installed, so nothing was pushed. Install gh, then run purlin:test --remote again.`
- `purlin:test --remote waits for the run with the Azure CLI, az, which is not installed, so nothing was pushed. Install az with its azure-devops extension, then run purlin:test --remote again.`
- `No run registered for <branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that the git host runs <workflow path> on a push to run/*, then run purlin:test --remote again.`
- `No run registered for <branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that az has the azure-devops extension and is signed in, then run purlin:test --remote again.`
- `The run failed on the git host. The table below is what came back.`
- ` Add one with git remote add origin <url>, then run purlin:init.`
- ` Make one with git switch -c <name>, then run purlin:test --remote again.`
- ` Check that git push origin works from this checkout, then run purlin:test --remote again.`
- `<path> is not the project root this job checked out, so no evidence was committed.`
- `Proofs in specs/ are tagged @env for <Systems>, which this machine is not, so only a runner can prove them.` and `Tests are tagged @env for <Systems>, which this machine is not, so only a runner can run them.`
- the templates' `The matrix holds one job for each operating system a proof in specs/ is tagged @env for that the machine running setup is not, and no other.`, `The run caps each test command at an hour of its own.` and `installs the libraries a Linux/Unix runner lacks`

**The breaking tool** (`scripts/run/mutation/`): `mutation_engine names "<x>", which is not an engine: set it to none, auto, mutmut, stryker or stryker_net`.

**Drift** (`scripts/mcp/purlin/drift.py`): ` Run purlin:test <feature>.`, ` Add each to a spec's > Scope: line with purlin:spec.`, ` Run purlin:build.`, ` Run purlin:test.`, and the anchor lines of K3.5 with `anchor ` before them.

**Signing, the audit and the package** (`scripts/review/sign.py`, `ai_audit.py`, `scripts/export/package.py`):

- `The signature commit was not made: <git's own message>. Nothing was signed; run purlin:sign again once git can make a signed commit.`
- `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` and its export form with `purlin:export`
- `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.`
- `No tag: the committed evidence still has work left to do, so no evidence package was committed. Run purlin:test --commit, then purlin:sign.`
- `  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>`
- `<script>.py: <path> is not a directory.`
- K3.1's lines as one wording on three surfaces (the words exist; `Strong.` for a strong answer with findings and `  Read by <model> at <at>.` are new)
- `  No test yet. Run purlin:build <feature>.`
- `Test strength <p>%, against a minimum of <m>%.` in the terminal

**Anchors** (`scripts/anchor/upstream.py`):

- `<name>: no anchor named <name> carries a git source. Run purlin:status to see the anchors this project has.`
- `  1 rule. Run purlin:status to see it.`
- ` Run purlin:status <name> to see its rules.` after `the pin is current.`
- ` Commit it as anchor(<name>): sync (<new7>), then run purlin:test.` after `Pin advanced ...`
- `No Purlin project root found. Pass --project-root <dir>.` and the help `the project root holding .purlin/ and specs/`

**The dashboard** (`scripts/report/src/`): `Type purlin:sign <feature> <RULE-N> in Claude Code.`,
`No test yet. Type purlin:build <feature> in Claude Code.`, `Back to the board`, and the theme
button's text `Dark theme` or `Light theme`.

**References and instructions**: K3.11's sentence in the test skill; K3.12's clause; K5.1 (the
glossary's `runner file`, `scope` and `anchor` sentences); K5.2 (the writing style's sentence
on capitals); K5.3 (the guide's two paragraphs, its examples and its row); K5.4 (every sentence
of the spec-from-code skill given there, the five reasons, what a caller reaches, commented-out
tests and benchmarks, the position file's fields, the ending); K5.5 (the spec skill's "Ids");
K5.7 (the test skill's comparison); K5.8; K5.9 (the command reference's sentences); K5.10 (the
release notes); K9 (the handoff paragraph).

## 13. The ownership check

`<session scratchpad>/plan4/check_ownership.py` reads the tables of sections 4 and 9, expands
each backticked path (braces, `*` and `**`) against `git ls-files` plus the files a lane
creates, and checks that no file has two owners in the same fan-out. Its output on this plan,
run on 2026-09-30 at `main` `fde87c658`, exit 0:

```
fan-out 1: 20 lanes, 216 files owned, 0 owned twice
  tracked files under the watched folders with no fan-out 1 owner: 4
    dev/test_vocabulary.py
    scripts/mcp/__init__.py
    scripts/mcp/purlin/__init__.py
    scripts/report/purlin-report.html
fan-out 2: 4 lanes, 15 files owned, 0 owned twice
  new files named: dev/test_purlin_docs.py, specs/instructions/purlin_docs.md
```

No file has two owners in either fan-out. The four files the check lists with no fan-out 1
owner change in no item: `dev/test_vocabulary.py` gains nothing (decision 44), the two
`__init__.py` files and the built page are integration's.
