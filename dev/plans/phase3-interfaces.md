# Phase 3 interfaces: what was built

Written by the integration agent on 2026-09-29, after the 20 lanes of `phase3-plan.md` merged
(plan section 9, step 7). This file says what the tree holds. Where it differs from
`phase3-contracts.md`, this file says so, and the code is what it does. Nothing was pushed or
tagged, and no audit or signing was run.

## Where `main` stands

- `main` is local, at `the commit of this file, after `caf34a00f``: P1 and P2, then the 20 lanes by fast-forward in the order of
  plan section 10, then integration's commits below.
- The full sweep, `bash dev/run_tests.sh`: at `0197b217f`, every lane merged and the first four fixes in: `1977 passed in 561.81s (0:09:21)`, `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`. A second full sweep on the final tree: at `caf34a00f`, `1977 passed in 584.66s (0:09:44)`, `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`; the four shell suites (`E2E Init (wiring)`, `E2E External Refs`, `E2E Required Rules`, `E2E Anchor Authority`) passed in both.
- This repository through its own tool, `purlin_run.py --test --all`: `Markers: 1940 tied to a test, 0 not tied.`, `Ran pytest, shell on 35 features.`, `Evidence written to .purlin/evidence/local/ for 35 features.`, then `752 rules. 752 pass their tests. 0 are strong. 0 are signed.` and `Left to do:` / `  752 rules to audit: purlin:audit`; exit 0. With `--commit` the same lines, with `Evidence committed.` after the evidence line, and one commit, `caf34a00f purlin: evidence at 1e54cba`: nothing but the evidence and the table was left to commit.
- The dashboard, `scripts/report/purlin-report.html`, rebuilt and committed once: `c2e65d01f`

## The merges

Each lane was rebased on `main` in its worktree, its own test files were run whole, and `main`
was fast-forwarded to it. No rebase met a conflict: no file was changed by two lanes.

| # | Lane | Head after rebase | Its own files at merge |
|---|---|---|---|
| 1 | `core` | `f583e7557` | 229 passed |
| 2 | `anchors` | `59c58363f` | 259 passed |
| 3 | `scaffold` | `61e3173e0` | 127 passed |
| 4 | `run` | `de40a8ce8` | 255 passed |
| 5 | `mutation` | `52dd5cf47` | 82 passed |
| 6 | `reports` | `950401b74` | 102 passed |
| 7 | `host` | `d3963524e` | 94 passed |
| 8 | `settings` | `5bb2daeae` | 74 passed |
| 9 | `drift` | `bb45a8304` | not run before the merge (a shell loop passed no file); 70 passed on `main` straight after |
| 10 | `update` | `2e9da7894` | 102 passed, 1 failed, merged by the same loop; the failure is fixed in `bc1fab586` below, then 103 passed |
| 11 | `signing` | `709d306da` | 111 passed |
| 12 | `review` | `079300f79` | 72 passed |
| 13 | `package` | `9987a8cd9` | 37 passed |
| 14 | `upstream` | `7f1754312` | 34 passed |
| 15 | `dashboard` | `aa8371d4a` | 166 passed |
| 16 | `instructions` | `340801f4c` | 35 passed |
| 17 | `skills-run` | `87d8aefe1` | 41 passed |
| 18 | `skills-author` | `b0e5f1cbc` | 50 passed |
| 19 | `skills-sign` | `485a241cf` | 33 passed |
| 20 | `words` | `48bde7d27` | 21 passed (`dev/test_skill_spec.py` and `dev/test_purlin_agent.py`, both shorter once `skills-author` and `instructions` merged) |

Tests of each lane's own files, before the lane and after it, as each lane reported: P2 365 to
374; `core` 211 to 229; `anchors` 217 to 259; `scaffold` 150 to 127; `run` 233 to 255;
`mutation` 81 to 82; `reports` 102 after (the lane's before count is not in its report); `host`
94 to 94; `settings` 57 to 74; `drift` 80 to 70; `update` 113 to 103; `signing` 105 to 111;
`review` 70 to 72; `package` 35 to 37; `upstream` 31 to 34; `dashboard` 165 to 166;
`instructions` 74 to 35; `skills-run` 92 to 41; `skills-author` 135 to 50; `skills-sign` 75 to
33; `words` 80 to 80, no test file of its own. The instruction specs fell most: their damaged
copies left the specs and live on as second assertions inside the tests they guard (C11).

## What integration changed

- `bc1fab586` fix(update): a pytest project on Windows is told mutmut does not run there (made
  after lane `update` merged and before lane `signing` rebased, so the later lanes carry it)
- `5103bcd10` test(scaffold): the walks take the suggested tests setting the first run prints
- `18fad2cc3` docs: marker format says a foreign proof is written not run whatever its test did
- `0197b217f` fix(states): the status prints no line for an anchor whose source names no repository
- `b9e75c0c3` docs: review criteria say what the model is shown of strength and point home for what it is
- `8b4d05e50` spec(scaffold): RULE-55 names a git host Purlin cannot use, in decision 96's words
- `c2e65d01f` chore(purlin_report): the dashboard page rebuilt from the merged sources of phase 3
- `1e54cbafb` docs: the Windows list names the rules and tests the lanes of phase 3 left
- `caf34a00f` purlin: evidence at 1e54cba

## Where the build differs from the contracts, or goes past them

1. **C4.1's order** (lane `core`). A `partial` that holds a failure reads `partial` ahead of
   `failed` and `no test`, since states PROOF-53 and PROOF-66 need a pass beside a failure to
   read `partial`. A `partial` with no failure comes after the failure and no-test checks, as
   C4.1 orders it (states PROOF-214).
2. **C4.2** (lane `core`). The no-code-files reason applies only where no strength was measured
   (states RULE-78), and both not-measured reasons apply only once an audit entry exists: an
   unaudited rule still reads `not audited` and counts `to_audit`.
3. **C1.9, the stream** (lanes `scaffold`, `update`). Setup and the upgrade print the settings
   sentence to stderr, as their other stops do; the run, signing, the package, the audit
   reader and the remote run print it to stdout. The contract says only "prints it".
4. **C1.9, the order in the run** (lane `run`). `settings_stop` asks `config_problem` before the
   0.9.5 check, not third as the brief said, since that check reads the same file.
5. **C1.9, the reader** (lane `settings`). `resolve_config` raises `ConfigUnreadable`, a
   `ValueError`, for a file that cannot be read, where it answered `{}`; every caller asks
   `config_problem` first.
6. **C3.4's causes** (P2). JSON `true` or `false` reads `it holds a boolean where an object
   belongs`, and `null` reads `it holds null where an object belongs`.
7. **C3.6, git's own message** (lane `signing`). git prints `The tag message has been left in
   .git/TAG_EDITMSG` first, so the line takes git's first line starting `fatal: ` or `error: `,
   with that word cut, else its first line, and cuts a closing full stop. Where git prints
   nothing, the line ends `git exited with <n>`. No test pins the cut.
8. **C3.2, the timeout** (lane `mutation`). The timed-out answer's `reason` keeps the timeout
   sentence as well as `missing`, so the run prints it once. mutmut's "wrote no report" is a
   `mutmut results --all true` that lists no break at all.
9. **C3.9** (lane `reports`). The format's sentence "A suggestion names only an id a comment
   may name" does not hold for a comment with a second mistake that names, exactly, a rule
   with proofs (`# purlim: login RULE-3` is given the fix `# purlin: login RULE-3`).
10. **C13, the status** (integration, `0197b217f`). Once drift's `pin_report` answered `error`
    with `not_a_spec`, the status printed `<name>: the source could not be read (...)` for such
    an anchor. C13 says nothing but drift and the anchor check warns of it, so the status now
    skips that row.
11. **C1.11 in the upgrade** (integration, `bc1fab586`). Setup's `engine_for` counts an engine
    that cannot run here as none, so the upgrade's own `runs_here` check was never reached and
    it printed `NO_ENGINE`. It now prints setup's `_no_engine_line`, which gives
    `NO_ENGINE_HERE` for mutmut on Windows.
12. **C12** (integration, `b9e75c0c3`). `references/review_criteria.md` opened its strength
    paragraph with S2's sentence `Test strength is one share per feature, in every language`.
    It now says only what the model is shown and points at `references/hard_gates.md`.
13. **C14 in the templates** (lane `host`, left). Both runner templates and the fixture copy
    still say `The matrix holds one job for each operating system the @env tags in specs/ name,
    and no other`, untrue once only foreign tags are handed in. No contract gives the words.
14. **The merge on a runner** (lane `run`). `merge_for_host` is handed each covered feature's
    whole rule list, not only the tagged rules, since the tagged rules alone would strip
    another system's section (evidence_writer RULE-4).
15. **The `gh` and `az` lookup** (lanes `host`, `scaffold`). Both go through `shutil.which`, as
    C8 says; the scaffold test asserts git's own folder holds no `gh`, which fails where git and
    `gh` share a folder (Homebrew). This Mac's git is `/usr/bin/git`.

## Calls left for the owner

Each lane's own list is under "The lanes" below. These cross lanes or were met at integration:

1. **Instruction rules that describe a file.** Frontmatter, line-ceiling and command-reference
   rules keep a structural form ("`skills/x/SKILL.md` opens with ...") in lanes `core`,
   `drift`, `scaffold`, `skills-run` and `skills-author`; lane `skills-sign` wrote them as
   "... tells the agent ...". C11 does not settle which; they are left as each lane wrote them.
2. **Copies one line over a ceiling.** Lanes `skills-author` and `skills-sign` treated them as
   damaged copies and folded them into the ceiling proof's test; lanes `core`, `drift`,
   `skills-run` and `instructions` kept such a proof where it is the boundary. Left as built.
3. **A written `mutation_engine` reset on Windows** (lane `scaffold`). Setup decides "no engine
   that runs here" before it reads the written value, so a Windows teammate rerunning
   `purlin:init` on a pytest project writes `none` over `auto`, against scaffold RULE-62.
4. **`Evidence committed.`** (lanes `host`, `run`). `_ci` prints it even when the host's commit
   returned nothing: no token, not the workspace, or no branch.
5. **A `--ci` run with no tagged proof** (lane `run`) runs nothing, prints
   `Evidence written to .purlin/evidence/ci/ for 0 features.` and calls the host's commit with
   no path.
6. **The local exit code for a foreign proof's failing test** (lane `run`) stays the suite's
   own, 1, though the section reads that proof `not run`.
7. **reports RULE-16** still says `{files}` is "nothing on a run over every feature"; a `--ci`
   run over every feature hands it the tagged proofs' files. No brief rewords it.
8. **security_no_dangerous_patterns RULE-5** still reads "a list in Python" while the check
   refuses `subprocess.Popen(*argv)` and accepts `subprocess.run(*argv)`.
9. **server RULE-22** holds two claims since PROOF-158 joined it; the brief placed it.
10. **The skills' remaining gaps**: the sign skill's closing table has no row for C3.6's
    git-failure line or for a package not committed, and no proof reads that the sign skill
    starts its scripts through `scripts/purlin_python.sh`; `skills/spec/SKILL.md` lines 117 to
    120 still say an untagged proof is satisfied by a run on any system.
11. **Decision 63's reading.** The stale `docs/` and `README.md` lines lane `words` found outside
    its list (under "The lanes", lane `words`) wait for the reading of every page.

## Words integration chose

Every sentence a person reads that integration wrote, word for word:

- `scripts/init/update.py`, the comment in `_ask_mutation`: "No engine, or only one that cannot
  run on this operating system: setup's own line names which." Its docstring now reads "only
  where an engine that runs on this operating system exists for a framework the project
  carries".
- `scripts/mcp/purlin/status.py`, the comment in `_pin_lines`: "An anchor whose source names no
  repository is read as any spec; purlin:drift and the anchor check name it, and the status
  does not."
- `references/formats/marker_format.md`, "A marker's result": "A proof tagged `@env` for another
  operating system is written as `not run` whatever its test did." (no Format-Version bump:
  clarified wording; the evidence format carries the change, 5).
- `references/review_criteria.md`, "What test strength says", first paragraph: "The model is
  shown the test strength of the feature the rule belongs to: of the deliberate breaks made to
  that feature's code, the share its tests caught, as an integer percent beside `min_strength`
  from `.purlin/config.json`, as `Test strength: 71 percent (minimum 80)`. Where nothing was
  measured, or the engine cannot run on this system, the model is shown `Test strength: not
  measured`. `references/hard_gates.md`, "The three steps", says what test strength is and when
  it leaves a rule `weak`."
- `specs/init/scaffold.md` RULE-55, its opening: "A project whose remote names a git host Purlin
  cannot use, one other than GitHub and Azure DevOps, has `ci` written `none`, ..." (the rest
  unchanged).
- `dev/plans/phase3-windows-list.md`: the new section "Brought up to date", the plain words of
  the twelve moved rows and of reports RULE-16 and signatures RULE-45, and the "Needs" cells of
  upstream RULE-1 and RULE-3, specs RULE-20, scaffold RULE-60, signatures RULE-17, host RULE-12,
  mutation RULE-7 and RULE-32 and run_script RULE-63, as committed in `1e54cbafb`.
- The commit messages of integration's commits, and this file.

## The greps of plan section 9, step 6

Each run with `git grep -F` over the tree, outside `dev/plans/`, `RELEASE_NOTES.md` and
`dev/fixtures/upgrade-0.9.5/`, after the `--commit` run of step 5:

- `--add` in `scripts/init`, `skills/init`, `references`: empty.
- `tests_by_rule`, `attribution`, `per_test`, `rules_by_feature`: empty. (Before the `--commit` run, the committed evidence of `mutation` still named a deleted test ending `read_per_test`; the run rewrote it.)
- `default_branch`: only the test name `test_it_allocates_ids_against_the_default_branch` in `dev/test_skill_spec.py` and the evidence file `.purlin/evidence/local/skill_spec.json` that lists it. (Before the run, `.purlin/evidence/local/host.json` named two deleted tests of `default_branch`.)
- `not_audited` in `scripts/mcp/purlin/drift.py`; `set_up_by_095` in `scripts/init`; `def main` in `scripts/mcp/config_engine.py`; `python3 "${CLAUDE_PLUGIN_ROOT}` in `skills/`; `Git host not read`: empty.
- `FREE_TEXT`, `no_rules`, `free-text` in `scripts/anchor/`, `skills/anchor/`, `specs/anchor/`: empty. `free text`: only `upstream.py` line 194, the `> Note:` field's own words in the `local_notes` docstring, which may stay.
- `neither GitHub nor Azure DevOps`: empty after `8b4d05e50`; scaffold RULE-55, split from RULE-14 by lane `scaffold`, had carried the phrase.
- `init_e2e_walk`, `test_e2e_build_changeset`, `test_init_e2e_gates`, `Process.Start` in `dev/test_security.py`, `"version"` in `templates/config.json`: empty.

C12: under `references/` and `skills/`, S1 ("A remote runner runs only the tests tied to proofs
tagged `@env` for its own system ...") stands only in `references/hard_gates.md`. S2 ("Test
strength is one share per feature ...") stood also in `references/review_criteria.md`, fixed in
`b9e75c0c3`. `skills/test/SKILL.md` keeps `An untagged proof runs anywhere.`, as C14 asks, followed
by the pointer; `skills/audit/SKILL.md` line 65 says `the AI audit alone decides the strong cell`
of mutation testing turned off, not of an engine that cannot run here.

## Docs and the formats

- **Evidence format 5** (lane `run`, `references/formats/evidence_format.md`): a local section
  carries no `hostname`; a `ci` section carries it and lists only the proofs tagged for its
  runner's system and the rules they prove; a proof tagged for another system reads `not run`
  whatever its test did; `audit.mutation` gains optional `missing`; the rule's word follows C4.5.
  The bump landed in `bfddbb44e`, the first commit that changed emission. One word change,
  `89789024f`, reached the format file one commit later, in `babb23a0f` (lane `run`, left).
- **Package format 4** (lane `package`, `references/formats/package_format.md`): `to_correct` and
  `to_measure` in the table of `left` kinds and the sentence of section 12, item 4. No code
  change: the package copies the payload's `left`.
- **Anchor format 10** (lane `upstream`): section 12, item 8, in the code's commit `3c537b422`.
- **Drift criteria 10** (lane `drift`): `not_audited` out of the QA view, deleted files counted,
  and the row for a source that names no repository.
- **Marker format** stays 3: its `{files}` row points at "Where a runner runs", its near-miss
  section follows C3.9 (lane `reports`), and integration's one sentence above. **Spec format**
  stays 18: P2 added prose and section 12, item 5.
- **The `docs/` lines lane `words` changed for them** (call 65), in `8ff0554a9` and the review's
  `b5dbe150b`: `docs/running-and-evidence.md` 102-113, 228-235 and the whole section 296-395,
  348 inside it (the section "Who committed a ci/ file" went with it, since decision 75 removed
  that check); `docs/dashboard.md` 13 and 67; `docs/how-purlin-works.md` 102 and 160-162;
  `docs/getting-started.md` 177; `docs/raising-the-gate-and-upgrading.md` 24 and 63;
  `docs/review-and-signing.md` 80; `docs/specs-and-anchors.md` 91-94, 140-144, and section 12
  item 10's sentence after the `add` code block.
- **Left from section 11's list, and why**: `docs/how-purlin-works.md` 103-105, the rest of the
  sentence that starts on line 102 (the tag run "checks that every signature still binds ...
  and ends with the gate check"), untrue since decisions 75 and 83. Lane `words` fixed only the
  runner clause on line 102, the line the list names. Every other stale line it found is listed
  under lane `words` below, for decision 63's reading.

## Seen at integration, not changed

- The status prints three warnings for this repository's own anchor
  `security_no_dangerous_patterns`: `> Scope:` names `scripts/**/*.ts`, `scripts/**/*.php` and
  `scripts/**/*.cs`, which find no file. The anchor's Description says it names those file types
  so a file of one is watched from the day it arrives; P2's warning names each entry that finds
  no file. No contract settles which gives way. The dashboard shows the three as notices.
- At 390 pixels, on a proof's test line, a test name longer than the box (about 40 characters of
  monospace) breaks inside itself, for example `test_a_rule_no_test_backs_reads_` /
  `no_test`. `.kv dd` carries `overflow-wrap:anywhere`, unchanged in this phase, and RULE-49 asks
  that text keep its size; keeping the name whole means a box that scrolls sideways or a
  shorter name, a design call. From 768 pixels up the line breaks only after `::`, as
  `testLines` allows. Every other check held at 1500, 1280, 1024, 768 and 390 pixels in both
  themes, on the board with `states` open and `RULE-8` unfolded and on `RULE-8`'s page: the page
  scrolls sideways 0 pixels.
- `dev/manual/check_build.py` lines 36 to 38 still say "Changeset carries no heading of its own",
  stale after Q61; its check still works (lane `skills-author`).
- `scripts/run/ci.py`'s module docstring says what the run does not do (lane `host`, left).
- The drift skill's closing table has no row for an anchor line reading `error` (lane `drift`).

## Specs: ids and counts on `main`

Every spec this phase changed, counted from the files at `f25f62007` (after P2) and on `main`.
"Highest" is the highest id in the file now; a file may have held a higher one, never reused
(C11).

| Spec | Rules before | Rules after | Proofs before | Proofs after | Highest RULE | Highest PROOF |
|---|---|---|---|---|---|---|
| `specs/_anchors/schema_spec_format.md` | 14 | 24 | 53 | 55 | RULE-24 | PROOF-57 |
| `specs/_anchors/security_no_dangerous_patterns.md` | 6 | 8 | 48 | 89 | RULE-8 | PROOF-91 |
| `specs/anchor/upstream.md` | 17 | 21 | 31 | 34 | RULE-29 | PROOF-45 |
| `specs/dashboard/purlin_report.md` | 48 | 48 | 159 | 160 | RULE-56 | PROOF-181 |
| `specs/export/package.md` | 10 | 19 | 35 | 37 | RULE-19 | PROOF-37 |
| `specs/init/scaffold.md` | 35 | 45 | 107 | 107 | RULE-63 | PROOF-128 |
| `specs/init/update.md` | 28 | 34 | 109 | 103 | RULE-40 | PROOF-116 |
| `specs/instructions/purlin_agent.md` | 8 | 8 | 43 | 9 | RULE-8 | PROOF-38 |
| `specs/instructions/purlin_output.md` | 0 | 1 | 0 | 1 | RULE-1 | PROOF-1 |
| `specs/instructions/purlin_version.md` | 8 | 13 | 31 | 25 | RULE-15 | PROOF-37 |
| `specs/mcp/config_engine.md` | 10 | 11 | 27 | 25 | RULE-15 | PROOF-35 |
| `specs/mcp/drift.md` | 18 | 24 | 49 | 58 | RULE-25 | PROOF-59 |
| `specs/mcp/evidence.md` | 20 | 28 | 64 | 70 | RULE-28 | PROOF-70 |
| `specs/mcp/server.md` | 11 | 20 | 25 | 45 | RULE-31 | PROOF-158 |
| `specs/mcp/specs.md` | 11 | 13 | 39 | 32 | RULE-21 | PROOF-41 |
| `specs/mcp/states.md` | 53 | 66 | 150 | 182 | RULE-91 | PROOF-214 |
| `specs/mcp/summary.md` | 11 | 14 | 27 | 34 | RULE-14 | PROOF-35 |
| `specs/review/ai_audit.md` | 16 | 20 | 70 | 72 | RULE-21 | PROOF-81 |
| `specs/review/signatures.md` | 39 | 51 | 105 | 111 | RULE-77 | PROOF-152 |
| `specs/run/evidence_writer.md` | 19 | 22 | 74 | 79 | RULE-22 | PROOF-79 |
| `specs/run/host.md` | 19 | 24 | 87 | 94 | RULE-40 | PROOF-115 |
| `specs/run/mutation.md` | 22 | 28 | 67 | 75 | RULE-33 | PROOF-85 |
| `specs/run/reports.md` | 24 | 28 | 93 | 98 | RULE-28 | PROOF-98 |
| `specs/run/run_script.md` | 43 | 52 | 159 | 176 | RULE-78 | PROOF-224 |
| `specs/skills/skill_anchor.md` | 6 | 12 | 32 | 13 | RULE-12 | PROOF-33 |
| `specs/skills/skill_audit.md` | 7 | 15 | 49 | 20 | RULE-15 | PROOF-50 |
| `specs/skills/skill_build.md` | 9 | 13 | 34 | 14 | RULE-13 | PROOF-41 |
| `specs/skills/skill_drift.md` | 4 | 5 | 31 | 12 | RULE-5 | PROOF-35 |
| `specs/skills/skill_export.md` | 6 | 11 | 33 | 13 | RULE-11 | PROOF-30 |
| `specs/skills/skill_init.md` | 7 | 11 | 43 | 20 | RULE-11 | PROOF-42 |
| `specs/skills/skill_sign.md` | 10 | 17 | 42 | 20 | RULE-17 | PROOF-45 |
| `specs/skills/skill_spec_from_code.md` | 8 | 10 | 32 | 11 | RULE-11 | PROOF-145 |
| `specs/skills/skill_spec.md` | 7 | 11 | 37 | 12 | RULE-11 | PROOF-40 |
| `specs/skills/skill_status.md` | 5 | 9 | 34 | 13 | RULE-9 | PROOF-31 |
| `specs/skills/skill_test.md` | 7 | 16 | 43 | 21 | RULE-16 | PROOF-44 |

## The lanes: ids, splits, words and calls, as each lane and its review reported them

Copied from each lane's report, its sections on ids, splits, the words it chose and the calls it
left, then the review's fixes and what it left. Ids a later review changed are in the review's
part (for example `drift`'s command-reference rule, RULE-9 in the lane's part, is RULE-5). The
report of lane `reports` holds its review alone; its lane's calls are the ones it returned:

- Which ids count as "nearest" for a near miss: every proof and rule the spec has, as before. So
  `RULE-30` beside `RULE-3` (two proofs) and `RULE-20` (no proof) is one character from two ids
  and gets nothing. Considering only the ids a comment may name would offer `RULE-20` instead.
- A comment with a second mistake whose id is one character from a rule with two or more proofs
  (`# purlim: login RULE-30`) is still listed for the misspelled `purlim`, its id left as written.
- reports RULE-16 still says `{files}` is "nothing on a run over every feature" (see "Calls left
  for the owner", 7).
- `references/purlin_commands.md` and `skills/build/SKILL.md` were stale on the near miss and the
  interpreter lookup; lanes `words` and `skills-author` brought both up to date.

### Lane `p2-warnings`

#### Spec maxima
- `specs/_anchors/schema_spec_format.md`: highest RULE-14, highest PROOF-55. Rules 12 -> 14. Proofs 44 -> 53. The highest ids the file ever held (git log -p --follow) were RULE-12 and PROOF-44.
  - Deleted: PROOF-3 and PROOF-7 and their tests. Both checked this repository's own files (Q54, third option).
  - Reworded: RULE-2 (adds the doubled number), RULE-3 (adds the unreadable proof line), RULE-7 (now says what Purlin reads) and PROOF-2 (the singular and the closing `Run purlin:spec test_feat.`).
  - New: RULE-13 (two specs with one name) and RULE-14 (a scope entry that finds no file). New proofs: PROOF-45 (the plural of the unnumbered warning), 46 (a number written twice), 47 and 48 (a proof line that cannot be read, and the 60-character cut), 49, 50 and 51 (RULE-7), 52 (RULE-13), 53, 54 and 55 (RULE-14).
  - No split. Splitting the anchor's specs by claim (decision 94, fourth bullet) belongs to lane `anchors` in the fan-out. RULE-2, RULE-6 and RULE-7 now meet C11's split test.

#### Words chosen (no decision or contract gave them)
- config_problem's cause for JSON `true`/`false`: `it holds a boolean where an object belongs`. For JSON `null`: `it holds null where an object belongs`. C3.4 names only list, string and number.
- The constant name `config_engine.CONFIG_CANNOT_BE_READ`.
- The constant names in specs.py: `SCOPE_FINDS_NOTHING`, `SAME_NAME`, `RULE_WRITTEN_TWICE`, `PROOF_LINE_UNREAD`, `HEADING_NAMES_OTHER`, `PROOF_LINE_SHOWN`.
- `references/formats/spec_format.md` has new prose. The heading line: "where `<name>` is the file name without `.md`. The file name is the spec's name, whatever the first line says; `# Anchor:` makes a spec an anchor wherever it is kept. A first line of either form naming another feature is warned of." Location: "A spec is known by `<name>` alone. Two specs with one name in different folders are warned of: only one is read, and the warning names both files and the `git mv` that renames the other." The Scope row: "An entry that finds no file git tracks, where the others reach files, is warned of." Rules format: "A rule id written twice is warned of; the rule is read once, with the text of its second line." Proof format: "A list item under `## Proof` of any other form is not read as a proof and is warned of." The section 12 item 5 sentence is written word for word.
- The rule texts of schema_spec_format RULE-2, 3, 7, 13 and 14, and PROOF-2 and PROOF-45 to 55, as committed.

#### Calls made where none was given
- The order of the lines spec_mistakes returns: by mistake, in C3.3's table order, and within each mistake by feature name.
- A name held by three or more specs gives one line for each file that is not read.
- A doubled rule id keeps the position where it was first written. It has one line however many times it is written.
- A proof line counts as "cannot be read" when it is a list item (`- `) under `## Proof` that does not parse. Continuation lines and prose do not count.
- A first line `# Feature:` with an empty name is not warned of.
- The scope warning applies to anchors too. An anchor none of whose entries finds a file gets no line, because anchors have no "names no files" line.

#### Items left, and failures in files I do not own
- This repository's own anchor `security_no_dangerous_patterns` now prints three scope lines: `scripts/**/*.ts`, `scripts/**/*.php` and `scripts/**/*.cs` find no file in git. The spec belongs to lane `anchors` and was left as it is.
- `specs/review/signatures.md` RULE-64, PROOF-125 and PROOF-144 still quote the old line `login RULE-9 is not a rule any spec has.`. That spec belongs to lane `signing`. The tests follow the new line.
- `dev/fixtures/report/regulated.json` holds an unnumbered-rule warning without the closing ` Run purlin:spec <feature>.`. That fixture belongs to lane `dashboard`.
- The singular of the unread-tags warning (L9) has no proof. specs RULE-8 belongs to lane `anchors`, which moves the tag rules into the anchor (Q44).
- spec_mistakes adds about 0.9 s to one payload build on this repository: one `git ls-files` per scope entry, through `fingerprint.expand_scope`, as the brief says.
- mutation.run_breaks' fourth argument was left as it is, as instructed.
- No failures in files I do not own.

### Lane `core`

#### Highest ids and counts

| Spec | Rules before, after | Proofs before, after | Highest RULE now | Highest PROOF now |
|---|---|---|---|---|
| `specs/mcp/states.md` | 53, 66 | 150, 181 | RULE-91 | PROOF-213 |
| `specs/mcp/summary.md` | 11, 14 | 27, 34 | RULE-14 | PROOF-35 |
| `specs/skills/skill_status.md` | 5, 9 | 34, 13 | RULE-9 | PROOF-31 (the file has held up to PROOF-34 since it was last written whole, at `7b81a9b88`) |

New ids were counted from the highest each file has held: states R76/P181, summary R11/P28, and skill_status R5/P34 since `7b81a9b88`.

#### Splits

- states RULE-27 -> RULE-27 (schema version and top-level keys: PROOF-31, 96), RULE-80 (`remote_url`: 95, 162), RULE-81 (`summary`, `left` with `to_correct`, `finished`, `last_line`, and the status report ends on the same lines: 97, 98, 207, 213), RULE-82 (`os_words`: 99)
- states RULE-28 -> RULE-28 (spec path, category, signature files, `current`, `evidence`: 32, 128, 129, 130), RULE-83 (the rule's audit hash: 127), RULE-84 (each proof's `@manual`, operating system and no findings key: 126)
- states RULE-74 -> RULE-74 (`applies_to` and `code_hash`: 111), RULE-85 (`machines`: 112, 113), RULE-86 (`hand_checked`: 114, 115, 145), RULE-87 (`left`: 116)
- states RULE-47 -> RULE-47 (`at`: 56, 133), RULE-88 (`signer_name`, `key_fingerprint`: 131, 132)
- states RULE-15 -> RULE-15 (not audited, could not run: 17, 18, 71, 172), RULE-89 (`undecided` reads weak and is to strengthen: 120, 121, 122)
- states RULE-35 -> RULE-35 (the current sections' tests, every system and both sources: 42, 163, 164), RULE-90 (where none is current every section answers: 41)
- states RULE-59 -> RULE-59 (the tag on HEAD at signed, and null below it: 68, 168, 169, 171, 83, 196, 174, 197), RULE-91 (the newest version wins: 170)
- summary RULE-1 -> RULE-1 (the sentence per gate: 1, 2, 3), RULE-12 (each rule counted once under its owner: 4)
- summary RULE-2 -> RULE-2 (singular in the sentence: 5), RULE-13 (a `Left to do` line for one rule: 6)
- summary RULE-10 -> RULE-10 (the words and order joined by ` and `: 22), RULE-14 (this machine's own system is never named: 28)
- skill_status RULE-1 -> RULE-1 (frontmatter: PROOF-1), RULE-6 (the command reference's row: 12)
- skill_status RULE-3 -> RULE-3 (the last section names the next step, the first line of `Left to do`: 3, 22), RULE-7 (the table names every kind with its command: 24), RULE-8 (every row gives a directive but `Nothing left to do.`: 23)
- skill_status RULE-5 -> RULE-5 (what to print for `purlin:status <name>`: 5, 31), RULE-9 (the reference names `purlin:status [name]`: 29)

Not split, and why:
- states RULE-25: PROOF-29 shows both the keys and the bucket counts.
- states RULE-36: PROOF-43 and 165 each show the columns together with the cells.
- summary RULE-4: PROOF-8 shows both the heading and line form and the kinds.
- summary RULE-8: its kinds are one precedence order. Each proof is one case of it.
- states RULE-4: the reading (Q2, call 45) chose one rule.
- A clause that is the other side of the same condition, such as "below `signed`" in RULE-59, RULE-63 and RULE-66, or "otherwise" in RULE-20, stays with its rule. The guide proves a rule in both directions.

#### Calls left, and calls taken where the contracts were silent

1. **Where `partial` stands in the order.** C4.1 gives `failed` > `no test` > `not run`/`partial` > `passed`. As built, and as PROOF-53 and PROOF-66 require, two systems with sections where one passes and one fails read `partial` before the failure check. I kept `partial` first, as built. The `no test` check sits after `partial` and `failed`, and before `not run` and `passed`.
2. **The no-code-files reason applies only where no strength was measured** (`f0995c5ce`). The reason says "strength not measured". In `dev/test_run_script.py` fixtures, an engine records 80% for a spec that names no files; there the reason would be false, and three run_script tests failed. RULE-78 gains "and for which no strength was measured".
3. **The not-measured reasons apply only once an audit entry exists.** A rule not yet audited still reads `not audited` and is counted `to_audit`. C4.2 says "after any findings", which I read as meaning the audit has run.
4. **Where the new proofs sit.** The brief did not name a rule for these:
   - PROOF-204 (Q7): under RULE-6, the rule that states `not run` with `<os>: no run yet`.
   - PROOF-206 (d95): under RULE-3, since every proof passes in some current section.
   - The moved PROOF-213: under RULE-81, the part of RULE-27 that holds `left`. Call 43 said "RULE-27", and the split moved that claim to a new id.
5. **A `no test` cell** keeps RULE-8's "no source, not current, not counting", and its `platforms` lists what the current sections covered. This holds in the mixed case too.
6. **How the status skill stayed at 100 lines.** Adding two rows needed two lines cut. I joined two paragraphs in Step 2 and two in Step 3 by removing the blank line between each pair. No words were removed.

#### Words chosen (every word a person reads that no decision or contract gave)

Spec rules (states):
- RULE-4: "An evidence file's source is the folder it sits in, `ci` or `local`, and a current section under either source, committed or not, leaves the passed cell reading `passed` with that source named, `counts` true and no reason at all, at every gate, `signed` included: a result counts wherever it ran, and its section records where; the test reports a run leaves under `.purlin/runtime/reports/` are not read"
- RULE-8: "A rule some of whose proofs no test backs reads `no test`, with no source, not current and not counting, and the reason `no test for <PROOF-N>`, naming every such proof joined by `, `; a proof that no marker ties to a test and no current section lists has no test, and a `@manual` proof needs none"
- RULE-13: "Where the audit found nothing and no strength was measured, because `mutation_engine` is `none` or the engine cannot run on this system, the strong cell reads `strong` with the reason `no mutation score measured`, and a strength left in the evidence is not compared while mutation testing is off"
- RULE-44: "Where two systems that each have a current section disagree the passed cell reads `partial`, naming the platforms that passed and the word of each that did not; `partial` is not met, its bucket is `partial` and its flag is `partial`"
- RULE-62, tail: "its rules' passed cells read as any other spec's"
- RULE-63, tail: "below `signed`, with mutation testing off, its cells read as they would with its files named"
- RULE-77: "Where mutation testing is on and the feature's evidence records no strength and says why, the engine not installed, out of time or writing no report, the strong cell reads `weak` with the reason `strength not measured: <why>`, after any findings"
- RULE-78: "Where mutation testing is on, at the gates `strong` and `signed`, a rule of a feature spec that names no code files, and for which no strength was measured, reads `weak` in its strong cell with the reason `strength not measured: the spec names no code files: run purlin:spec <feature>`; an anchor is never such a spec"
- RULE-79: "A settings file that cannot be read makes the status report exactly the one sentence `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, with no table and no summary"
- RULE-81: "`summary` carries `steps` and `sentence`; `left` lists the work left, each entry with `kind`, `count`, `text` and `command`, the kind `to_correct` counting the comments above tests that name nothing a spec has rather than rules; `finished` is true when `left` is empty, and `last_line` is then the line said in its place, null otherwise; the status report ends on the same sentence and lines"
- RULE-83: "Each rule in a feature entry carries the audit hash a signature binds"
- RULE-84: "Each proof in a rule's entry carries whether it is `@manual` and its operating system, and no findings key"
- RULE-89: "An audit entry reading `undecided` for a rule's current hashes makes the strong cell read `weak` with the reason `the AI audit could not decide: <its sentence>`, and the rule's `left` reads `to_strengthen`"
- RULE-90: "Where no section is current, every section's list answers for the tests a rule's test hash binds, so a code change alone does not move the hash"
- The other split rules (27, 28, 35, 47, 59, 74, 80, 82, 85-88, 91) reuse the words of the rule they came from, cut at the claim.

Spec rules (summary):
- RULE-4: adds "`test comments to correct`, `1 test comment to correct` for one, `purlin:build`;", "`rules to measure`, `purlin:audit`;" and "`test comments to correct` counts, at every gate, the comments above tests that name something no spec has or a rule that has proofs".
- RULE-5: adds "`test comments to correct` second".
- RULE-8: adds "`weak` only because its feature's strength was not measured (`to measure`), `weak` only because its spec names no code files (`to tie to its files`), and any other `weak` (`to strengthen`)".
- RULE-11: adds "no test comment is left to correct".
- RULE-12: "Each rule is counted once in the sentence, under the feature that owns it".
- RULE-13: "A line of `Left to do` counting one rule reads `1 rule <words>: <command>`".
- RULE-14: "This machine's own system is never among those the `to test on` line names, since a rule that waits for it is counted `to test`, so the line names one system or two".

Spec rules and Description (skill_status):
- Description: "The instructions in `skills/status/SKILL.md`: what they tell the agent to print for `purlin:status` and `purlin:status <name>`, ending on the summary and `Left to do` the tool returned, and how they name the next step."
- RULE-2: "The skill tells the agent to print the sentence and the `Left to do` lines `sync_status` returned and never to recount them"
- RULE-3: "The skill tells the agent, in its last section, to name the next step, the first line of `Left to do`"
- RULE-6: "The table of commands in `references/purlin_commands.md` carries a row for `purlin:status` whose purpose cell is not empty"
- RULE-7: "The skill's closing table names every kind of `Left to do` line with a `→` directive to the command that line names"
- RULE-8: "Every row of the skill's closing table gives a `→` directive but `Nothing left to do.`, which names none"
- RULE-9: "`references/purlin_commands.md` names the form `purlin:status [name]`"

The status skill:
- The row `` | `<n> test comments to correct` | `→ Run: purlin:build` | ``
- The row `` | `<n> rules to measure` | `→ Run: purlin:audit` | ``

Proofs (new, written by me):
- The texts of states PROOF-182-213 and summary PROOF-29-35, as they stand in the two specs.
- The texts of the per-gate proofs, the gate or folder named in each.

Code and docstrings: comments and docstrings in `states.py`, `payload.py`, `summary.py` and `status.py`, including the line "`test comments to correct` counts comments above tests, not rules:" in `summary.py`'s module docstring. Nothing printed at run time is new beyond the contracts' strings.

#### Review: Found and fixed, in `f583e7557` fix(states): a proof with no test comes before a partial run with no failure

1. **C4.1's order, `no test` before `partial`.** As built, `partial` came before `failed` and
   `no test` in every case. C4.1 gives `failed` > `no test` > `not run` / `partial` > `passed`,
   and PROOF-53 and PROOF-66 need a pass beside a failure to read `partial`. The passed cell now
   reads `partial` first only where a system failed. Where the systems disagree with no failure
   (one passed, another ran and did not pass), it reads `no test` first when a proof has no test,
   then `partial`. New PROOF-214 (RULE-8) with its test.
2. **States RULE-81** said `to_correct` counts comments "that name nothing a spec has". C2 counts
   every comment that fails the run. It now reads "that name something no spec has or a rule that
   has proofs". The same fix is in the docstrings of `payload.py` and `summary.py` (`KINDS`,
   `left`).
3. **PROOF-207** said `left` holds "the one item" `to_correct`. Its test asserts two items. It now
   reads "puts first in `left` the item `to_correct`".
4. **PROOF-138** (RULE-63, at `strong`, both rules `strong`) did not say mutation testing was
   off, and RULE-63 is now limited to that case. The proof names `mutation_engine` set to `none`,
   and its test sets it.
5. **Stale docstrings**: the `states.py` module docstring said `weak` means only a finding or a
   strength under the minimum. The `payload.py` module docstring and the comment at `incomplete`
   said only the signed cell reads a spec with no files. Both now name the strength not measured
   with mutation testing on.
6. **Section comments in `dev/test_skill_status.py`** named only the first rule of each split.
   They now name RULE-1 and RULE-6, RULE-3, 7 and 8, and RULE-5 and 9.

#### Review: Left, and why

- A pass beside a failure still reads `partial` ahead of `failed` and `no test`. PROOF-53 and
  PROOF-66 fix it, and C4.1's order cannot hold for that case with them. I rank such a `partial`
  with the failures.
- skill_status RULE-1 (frontmatter), RULE-4 (the line ceiling), RULE-6 and RULE-9 (the command
  reference) are not worded "the skill tells the agent". They state facts about files, not
  instructions. The brief's own split of RULE-1 produces RULE-6. Left as the lane wrote them.
- The lane's calls 2 to 6 stand; I found nothing in the contracts that decides them otherwise.

#### Review: Words I chose

- states PROOF-214: "A `macos` section passes `PROOF-1`'s test and a `linux` section lists it as not run; `PROOF-2`, of the same rule, has no marked test and is listed in no section; the passed cell reads `no test` with the one reason `no test for PROOF-2`, not `partial`"
- states RULE-81, the clause: "the kind `to_correct` counting the comments above tests that name something no spec has or a rule that has proofs, rather than rules"
- states PROOF-207, the opening: "A test comment naming `login PROOF-9`, which no spec has, puts first in `left` the item `to_correct` with the count 1, ..."
- states PROOF-138, the added clause: "with `mutation_engine` set to `none`"
- Docstrings and comments in `states.py`, `payload.py` and `summary.py` as committed in `f583e7557`

### Lane `anchors`

#### Highest ids, and counts

| Spec | Highest RULE | Highest PROOF | Rules before and after | Proofs before and after |
|---|---|---|---|---|
| `specs/mcp/specs.md` | RULE-21 | PROOF-41 | 11 to 13 | 39 to 32 |
| `specs/mcp/evidence.md` | RULE-28 | PROOF-70 | 20 to 28 | 64 to 70 |
| `specs/_anchors/schema_spec_format.md` | RULE-24 | PROOF-57 | 14 to 24 | 53 to 55 |
| `specs/_anchors/security_no_dangerous_patterns.md` | RULE-8 | PROOF-91 | 6 to 8 | 48 to 89 |

New ids start one past the highest ever held in each file's history: specs RULE-16 and PROOF-41; evidence RULE-20 and PROOF-64; schema_spec_format RULE-14 and PROOF-55; security RULE-6 and PROOF-48.

#### Splits

- specs RULE-3 -> RULE-3 (a rule's text is everything after its id, bracket included: PROOF-1, 2), RULE-17 (the text hashes normalise whitespace: PROOF-3, 4, 17, 18, 19)
- specs RULE-7 -> RULE-7 (0.9.5 tags ignored and listed: PROOF-8, 24), RULE-18 (0.9.5 fields ignored and listed: PROOF-25, 26)
- specs RULE-13 -> RULE-13 (a feature proves own, required and global rules: PROOF-14, 37), RULE-19 (an anchor proves its own rules and nothing else: PROOF-36, 38)
- specs RULE-14 -> RULE-14 (keyed by filename stem: PROOF-15), RULE-20 (a file that cannot be read or decoded is skipped: PROOF-39, 41), RULE-21 (no `specs/` folder, no specs: PROOF-40)
- schema_spec_format RULE-1 -> RULE-1 (two sections, no third: PROOF-1), RULE-15 (an unnamed heading still parses, nothing reported: PROOF-13)
- schema_spec_format RULE-2 -> RULE-2 (ids, increasing, gaps reported as nothing: PROOF-14), RULE-16 (an unnumbered line is warned of: PROOF-2, 45), RULE-17 (a number written twice is warned of, read once: PROOF-46)
- schema_spec_format RULE-3 -> RULE-3 (proof line forms; another form is not a proof: PROOF-15, 16, 17), RULE-18 (such a line is warned of: PROOF-47, 48)
- schema_spec_format RULE-6 -> RULE-6 (Scope is a list in the order written: PROOF-6, 22), RULE-19 (the code part hashes exactly those files: PROOF-23, 24)
- schema_spec_format RULE-9 -> RULE-9 (the two tags, either order, read off the end: PROOF-9, 25, 26, 35, 56), RULE-20 (a second `@manual` reads as one: PROOF-33), RULE-21 (of two `@env`, the last is read and the earlier is unknown: PROOF-32), RULE-22 (another trailing at-word stops the reading: PROOF-27, 28, 57), RULE-23 (a tag after a list connector is no tag: PROOF-29, 30, 31, 34)
- schema_spec_format RULE-10 -> RULE-10 (`@env` takes three values, any other is unknown: PROOF-10, 36 to 40), RULE-24 (a bare `@windows` and bracketed at-words are unknown, and `@manual(...)` still reads as manual: PROOF-41, 42, 43)
- security_no_dangerous_patterns RULE-6 -> RULE-6 (`--end-of-options`: PROOF-9, 10, 12, 13), RULE-7 (`--` before paths: PROOF-11), RULE-8 (the refusal of `-`, `ext::` and `fd::` sources: PROOF-6, 47, 48)
- evidence RULE-1 -> RULE-1 (three 64-hex parts: PROOF-1), RULE-21 (taken from the working tree: PROOF-32)
- evidence RULE-2 -> RULE-2 (the spec part covers rule and proof lines: PROOF-2, 3, 34), RULE-22 (Description changes no part: PROOF-33)
- evidence RULE-3 -> RULE-3 (a required anchor's edit reaches the feature: PROOF-4), RULE-23 (a global anchor reaches every feature; one not required and not global does not: PROOF-5, 35)
- evidence RULE-4 -> RULE-4 (the code part; a file entry: PROOF-6, 36), RULE-24 (a directory entry: PROOF-7), RULE-25 (a glob entry: PROOF-8, 37 to 40)
- evidence RULE-7 -> RULE-7 (the tests part; another feature's marker is not counted: PROOF-11, 12, 43, 44), RULE-26 (the skipped folders: PROOF-45, 65 to 68)
- evidence RULE-14 -> RULE-14 (sections and their order: PROOF-20), RULE-27 (the machine the reader runs on: PROOF-25, 53, 54)
- evidence RULE-16 -> RULE-16 (an entry answers while its three hashes match: PROOF-22, 58, 59, 60), RULE-28 (the later `at` wins across sources: PROOF-61, 62)

Rules not split because one proof shows two of their claims: specs RULE-11 (PROOF-12), schema_spec_format RULE-4 (PROOF-4) and RULE-7 (PROOF-49), evidence RULE-8 (PROOF-14). Security RULE-1 to 5 are not split because the whole-tree scan proof shows every claim.

#### Words I chose

Spec text:
- security RULE-7: `` `--` precedes every path argument handed to git ``
- specs PROOF-41: ``A project holds `specs/auth/login.md` and `specs/auth/locked.md`, which the operating system refuses to read; it reads as the one spec `login` ``
- security PROOF-38: ``A planted `.py` file holding `subprocess.Popen(command, cwd=root)` on its third line, handed a name and not a list written in place, is found, and the finding names its file and line 3``
- security PROOF-86: ``A planted `.py` file holding `subprocess.Popen(*argv)` on its third line, handed no list written in place, is found, and the finding names its file and line 3``
- security PROOF-87: ``A planted `.py` file holding `subprocess.Popen([*command], cwd=root)`, a list written in place, is not counted``
- The new rule texts of every split, as they stand in the spec files. Each is a clause of the old rule, lightly rejoined; these differ most from the old wording:
  - evidence RULE-4: ``..., and an entry naming a file reaches that file; ...``
  - evidence RULE-22: ``Editing `> Description:` changes no part of the fingerprint``
  - evidence RULE-26: ``A test file under a folder whose name begins with `.` or is `node_modules`, `bin`, `obj` or `mutants` is not counted in the `tests` part``
  - schema_spec_format RULE-18: ``A list item under `## Proof` that is not a proof line is warned of``
  - schema_spec_format RULE-20: ``A second `@manual` on a proof line reads as one``
  - specs RULE-18: ``The fields 0.9.5 wrote that the format does not carry, `> Visual-Reference:` and `> Visual-Hash:`, are ignored rather than refused, and every spec carrying one lists it under `unknown_tags` ``
- The split one-case proof texts. They reuse the old sentence per input, for example ``A planted `.py` file holding `exec (src)` is found, and the finding names its file and the form `exec(` ``, ``The stored word `macos` reads `macOS` in full and `Mac` in a small box`` and ``A copy of a JavaScript test carrying `// purlin: login PROOF-2` is committed under `bin/`, named by the suite's glob `**/*.test.js`; editing it leaves the fingerprint of `login` as it was``

Test text:
- The skip reason: `file modes do not refuse a read to this user`
- The check's finding line: `Popen at <path>:<line> first arg is not a list written in place: ...`

#### Calls I made or left

- **Evidence RULE-5 is not split.** Its proofs fall into two groups: listed (PROOF-9, 42) and still taken (PROOF-41). The plan and brief keep it "as worded".
- **Where the anchor's split rules sit.** Plan call 57 had P2 put the doubled-number warning into anchor RULE-2. The split (brief item 6 names RULE-2) moved that warning to RULE-17. RULE-2 keeps "the author assigns them in increasing order and never reuses one".
- **Other anchor rules split beyond the brief's candidates.** The brief named RULE-2, 9 and 10. I also split RULE-1, 3 and 6 by the same test.
- **"The other direction" counted as part of one claim.** For example, specs RULE-8 "absent when no spec carries", evidence RULE-17's tie and schema RULE-14's all-entries case were not split out.
- **A `Popen` imported by name** is held to a list written in place, as `subprocess.Popen(` is. The brief names only `subprocess.Popen(`.
- **Evidence PROOF-26** was split one per stored word, though each word has a different result. C11 names only same-result loops; the guide's "one case" covers it.
- **Not updated, not mine:** `dev/plans/phase3-windows-list.md` still names specs RULE-14 and PROOF-41 for the unreadable file. It is now RULE-20; integration brings the list up to date.

#### Review: Found and fixed

- **1904391a6** `spec(schema_spec_format): RULE-22 names the at-words it covers`. After the split, RULE-22 read "Any other trailing at-word is not a tag and stops the reading", and nothing was left for "other" to point at. Read alone, it was also false for a bare `@windows` and for an at-word carrying a value in brackets: RULE-24 reads both as unknown tags, and reading does not stop at them. It now reads: `A trailing at-word that is not `@manual`, `@env` or a bare `@windows`, and carries no value in brackets, is not a tag and stops the reading`. This matches `split_proof_tags`, and PROOF-27, 28 and 57 are unchanged.
- **9e288d5f3** `spec(security_no_dangerous_patterns): PROOF-51 reads as one sentence`. The missing comma after "indented" is in.

#### Review: Left, and why

- **Security RULE-5** still says "a list in Python". The check now refuses `subprocess.Popen(*argv)` and accepts `subprocess.run(*argv)`, and the rule's words do not say that the two differ. The brief holds the check and names no change to the rule text, so it stands.
- **The Windows list names rules the splits moved.** `dev/plans/phase3-windows-list.md` is not this lane's file, and integration brings it up to date. Three rows are affected, and the tests they cite all still exist:
  - evidence RULE-4, whose test (PROOF-7, a folder entry) is now under RULE-24;
  - evidence RULE-14, whose test (PROOF-53, `win32`) is now under RULE-27;
  - specs RULE-14, whose test (PROOF-41) is now under RULE-20. The lane had listed this one.
- **evidence RULE-19** was not split. Its fallback clause, "a stored word other than ... reads as `Linux/Unix` and `Lin`", has a proof of its own (PROOF-27). It is read as a case of the one mapping claim, the same way the lane read RULE-27's "and `linux` on any other system".
- **evidence RULE-10** was not split. PROOF-48 shows both the order and the "all three" clause.
- **The unused `import pytest`** in `dev/test_security.py` was already unused on `main`, so it is untouched.
- **The Windows `msvcrt` branch** of the unreadable-spec test is written and has not run; this machine is a Mac.

### Lane `scaffold`

#### Specs

- `specs/init/scaffold.md`: highest RULE-63, highest PROOF-128. Rules go from 35 to 45; proofs stay at 107 (3 deleted, 3 added). New ids start from the historical maxima RULE-51 and PROOF-125.
- `specs/skills/skill_init.md`: highest RULE-11, highest PROOF-42 (PROOF-43 was held and deleted, so the next free id is PROOF-44). Rules go from 7 to 11; proofs go from 43 to 20. The historical maxima since the whole rewrite at 7b81a9b88 are RULE-7 and PROOF-43.

#### Splits

- scaffold RULE-5 -> RULE-5 (the config init writes: seven keys, `audit_parallel` 4 and not asked; PROOF-5, 55, 56, 58), RULE-52 (the template's six keys in order; PROOF-54)
- scaffold RULE-13 -> RULE-13 (written for one reason, printed under the heading; PROOF-64, 65, 51), RULE-53 (no foreign proof: told, no workflow; PROOF-13), RULE-54 (a foreign proof and no remote: told, no workflow; PROOF-66)
- scaffold RULE-14 -> RULE-14 (host read, written as `ci`, named on the summary line; PROOF-14, 67, 68, 107), RULE-55 (neither host: `ci` none, UNKNOWN_HOST on the next line; PROOF-69), RULE-56 (no remote: `ci` none, `No git host found.`; PROOF-70), RULE-57 (Azure DevOps gets the pipeline file; PROOF-71)
- scaffold RULE-42 -> RULE-42 (the triggers; PROOF-42, 75), RULE-58 (the last step is the test run; PROOF-74, 76). This one was not a named candidate but meets C11.
- scaffold RULE-44 -> RULE-44 (the two prerequisites; PROOF-44), RULE-59 (no branch is checked; PROOF-77), RULE-60 (`gh` or `az` reported, workflow written either way; PROOF-78, 79, 113, 114)
- scaffold RULE-45 -> RULE-45 (the question, yes and no; PROOF-45, 81), RULE-61 (no engine that runs here: nothing asked, `none`, one line at strong and signed, nothing at passed; PROOF-82, 83, new 127), RULE-62 (a value already written is kept; PROOF-84)
- skill_init RULE-1 -> RULE-1 (frontmatter; PROOF-1), RULE-8 (command reference row; PROOF-16)
- skill_init RULE-6 -> RULE-6 (seven keys; PROOF-6, 38), RULE-9 (`audit_parallel` not asked; PROOF-39), RULE-10 (evidence folder with README; PROOF-40)
- skill_init RULE-7 -> RULE-7 (installs nothing, empty `tests`, first test run suggests a command per tool; PROOF-7), RULE-11 (points at the two references; PROOF-42)

#### Words chosen (no decision or contract gave them)

- `skills/init/SKILL.md`:
  - "Where no engine exists, or it cannot run on this operating system (mutmut on Windows), init asks nothing, writes `none` and, at `strong` and `signed`, prints one line saying so."
  - Flag table `--yes`: "Takes the default answer to every question"
  - "A later run asks nothing before it writes. Raising the gate writes the setting, and the gate's `min_strength` where mutation testing is on. Lowering the gate rewrites the setting and deletes nothing: the workflow, the evidence and the signatures stay where they are."
  - "and the first `purlin:test` suggests a command for each test tool it recognises, each with the flag that writes the report Purlin reads, and writes them together once the person agrees."
  - "Under its first summary line init prints `No git host found.` where there is no remote, and `This git host cannot run tests remotely. Everything on this machine works.` where the remote names neither."
  - "it gets a matrix of one job per operating system the `@env` tags name that this machine is not, each writing its own section (`references/hard_gates.md`, "Where a runner runs")."
  - Table cells: "Reruns the tests `references/hard_gates.md`, "Where a runner runs", names, on a clean machine, and commits nothing" and "Runs the tests `references/hard_gates.md`, "Where a runner runs", names, then commits ..."
- `specs/init/scaffold.md`: the rule texts of RULE-13, 14, 42, 44, 45 as split and RULE-52 to 63, and PROOF-15, 69, 70, 126, 127, 128. All are in the file.
- `specs/skills/skill_init.md`: every rule's rewording into "The skill tells / gives / shows / points the agent", and PROOF-2, 7 and 23.
- `scripts/init/scaffold.py`:
  - docstring "Exit codes: 0 the project is set up, 1 the settings file cannot be read, 2 the invocation was wrong, the directory is not a git repository, or the project root does not exist."
  - the docstrings of `engine_for`, `_no_engine_line`, `resolve_mutation`, `write_workflow` and `_existing_config`.
- `dev/windows_skip.sh` header: "Sourced by one test, dev/test_init_e2e_wiring.sh, ... On Windows the suite says it did not run and exits 1: a suite judged by how it ends has only passed and failed, so a run that did not happen reads failed rather than passed."
- `dev/test_init_e2e_wiring.sh` comments. The two printed lines of `purlin_skip_on_windows` are unchanged.

#### Calls left or made where nothing decided

- The `config_problem` sentence goes to stderr, as setup's other stops do. Nothing says stdout or stderr. The check stands after the repository check; `--update` still delegates before it, since lane `update` owns the upgrade's check.
- Which of the two host lines setup prints is decided by `git remote` (any remote), as `prerequisites()` decides. The host is read from `origin`.
- The mutmut block is not written where mutmut cannot run here (a pytest and JavaScript project on Windows with mutation on), since such an engine counts as none.
- scaffold RULE-15 states two claims (the matrix: PROOF-15 and 72; the pinned release: PROOF-73) but was not split, because C14 fixes its words.
- Left whole though each has separate proof groups (not named candidates): scaffold RULE-8 (8, 59, 60 and 61), RULE-31 (31 and 115, 116), RULE-47 (47 and 124, 125), and skill_init RULE-2 (the run line and the flags).
- skill_init RULE-1, 4 and 8 describe files (frontmatter, length, the command reference) and are not phrased as "tells the agent".
- No proof quotes setup's new matrix note.

#### Review: Fixed, in `5906a1f85` fix(scaffold)

- scaffold RULE-1 and the spec's Description still said the mutation question is asked
  "where an engine exists for a framework the tree carries". On Windows a pytest project has
  such an engine and is not asked (RULE-61), so both now say "an engine that runs on this
  operating system".
- In `skills/init/SKILL.md`, the "What the runner runs" cells read "Reruns the tests
  `references/hard_gates.md`, "Where a runner runs", names, ...", which is hard to parse. They
  now read (words chosen):
  - `Reruns the tests it selects (`references/hard_gates.md`, "Where a runner runs") on a clean machine, and commits nothing`
  - `Runs the tests it selects (`references/hard_gates.md`, "Where a runner runs"), then commits ...`
- Two prose lines of the skill ran past the file's wrap, at 156 and 102 characters, and are
  wrapped. The `resolve_mutation` docstring is wrapped too.
- The header of `dev/test_init_scaffold.py` said the typescript and C# projects walk to the
  signed tag. Only the python project does, so the header now says so.

#### Review: Left, and why

- **A written `mutation_engine` can be reset to `none` on Windows** (a call no contract makes).
  Setup decides "no engine that runs here" before it reads the written value. A pytest project
  whose committed settings read `auto` or `mutmut`, set up again on Windows, is rewritten to
  `none` and prints the Windows line. RULE-62 says a written value is kept without asking. The
  same order already rewrote a shell-only project, but there the tree decided it. Now the
  machine decides, so a Windows teammate who reruns `purlin:init` turns mutation testing off
  for the whole team. Left as built; the owner decides which rule wins.
- skill_init RULE-5 and the skill's second question still read "only where an engine exists".
  PROOF-30 reads those words, and the skill's next paragraph names the Windows case.
- The `gh` and `az` test asserts that git's own folder holds no `gh` or `az`. Where git and
  `gh` share a folder, as with Homebrew's `/opt/homebrew/bin`, the test fails on that
  assertion and not on the product. This Mac's git is `/usr/bin/git`.
- On Windows the `gh` test's `gh.cmd` stand-in is found only after lane `host` changes
  `workflow._which` to `shutil.which` (C8). Until then it fails there.
- Everything in the lane's own "Calls left" list stands.

### Lane `run`

#### Highest ids, counts

- `specs/run/run_script.md`: highest RULE-78, highest PROOF-224. Rules 43 -> 52, proofs 159 -> 176.
- `specs/run/evidence_writer.md`: highest RULE-22, highest PROOF-79. Rules 19 -> 22, proofs 74 -> 79.

Every proof has a marker in its test file and every rule has a proof; no proof is over 60 words.

#### Splits

- run_script RULE-11 -> RULE-11 (the run ends on the status table, summary and `Left to do`; `--test`'s exit code), RULE-71 (a project with no specs says so and exits 1)
- run_script RULE-45 -> RULE-45 (under `passed` no breaks, `audit.mutation` null), RULE-72 (`mutation_engine` `none`: no breaks, `strong` with `no mutation score measured`), RULE-73 (above `passed` with an engine: breaks for each feature with a rule read, score written, under `min_strength` weak), RULE-74 (`missing` written and printed), RULE-75 (only `--audit` runs the breaks; `--ci` makes none, calls no model, writes no `audit`)
- run_script RULE-51 -> RULE-51 (one call per rule, `audit_parallel` at once, 4 when absent, each answer written), RULE-76 (an out-of-range value reads as 4 with the warning once beside the table)
- run_script RULE-52 -> RULE-52 (nothing written, `not audited`, one line per cause, exit 1 above `passed`), RULE-77 (the next audit reads the rule again)
- run_script RULE-56 -> RULE-56 (the `Selected` line and the untracked-file lines), RULE-78 (the `Skipped` line)
- evidence_writer RULE-8 -> RULE-8 (rendered from every file, newest section, counts, `Last run`), RULE-20 (the heading and the columns)
- evidence_writer RULE-10 -> RULE-10 (the second commit, its subject, `Evidence committed.`, never pushes), RULE-21 (nothing new: `Evidence unchanged.`, no commit)
- evidence_writer RULE-12 -> RULE-12 (audit.rules entries and audit.mutation written), RULE-22 (`missing`, and an entry differing in it alone replaces the one on disk)
- Not split: run_script RULE-12 (PROOF-12 shows the section, the commit line and the exit code together).

Proofs re-pointed by the splits: PROOF-104 -> RULE-71; PROOF-79 -> RULE-72; PROOF-66, 80, 81, 173 -> RULE-73; PROOF-213 -> RULE-74; PROOF-102, 174, 175 -> RULE-75; PROOF-177 to 182 -> RULE-76; PROOF-83 -> RULE-77; PROOF-205 -> RULE-78; evidence_writer PROOF-32 -> RULE-20, PROOF-38 -> RULE-21, PROOF-79 -> RULE-22.

Deleted: run_script RULE-22 and PROOF-22 with their test. No other proof deleted or moved.

#### Calls left or made

1. `merge_for_host` is handed the whole rule list of each feature the runner covered, not "only those rules" as the brief says. The merge drops, in every section of the file, rules not in the list; handing it only the tagged rules would strip another system's section of its rules, against evidence_writer RULE-4. Reported for the owner or integration to decide.
2. `settings_stop` asks `config_problem` before the 0.9.5 check, not third: the 0.9.5 check reads the same file, and an unreadable file would otherwise read as one with no `tests` and print the upgrade line.
3. A `--ci` run in which no feature has a proof tagged for the runner's system: nothing runs, and `_ci` goes on as before with no sections (it still calls the host's commit with no evidence paths). Not changed.
4. The R3 lines come in the reader's `PLATFORMS` order: Windows, macOS, Linux/Unix.
5. The Windows pytest command is chosen by `frameworks.suggest(root, os_name=None)`: with no `os_name` it reads `os.name == 'nt'`, as `mutation.runs_here` does.
6. PROOF-224 does not quote the JSON reader's message: it differs between Python versions (3.13 says `Illegal trailing comma before end of object at line 3`, older ones `Expecting property name enclosed in double quotes at line 4`); the test derives it from the reader.
7. A test that fails locally for a proof tagged for another system still sets `--test`'s exit code to 1 (the suite's own exit code), though the section reads that proof `not run`. No decision covers the local exit code for this; left as it was.

#### Words chosen

Spec and reference prose the contracts did not fix (printed lines all come from the contracts):

- run_script RULE-69: `A mistake Purlin sees in a spec is printed as one line naming the spec, the mistake and the command that fixes it, and the run carries on: it runs that spec's tests, writes their evidence and exits on them`
- run_script RULE-70: `With a .purlin/config.json that cannot be read, the run prints ..., writes nothing and exits 1`
- run_script RULE-12, 8, 10, 47, 61, 63, 64, 67, 51, 66 rewordings and the split rules RULE-71 to 78 (text in the spec)
- evidence_writer RULE-2, 3, 12, 16, 17 rewordings and RULE-20, 21, 22
- `references/formats/evidence_format.md`: "A `ci` section answers only for the proofs tagged `@env` for the runner's own system: its `proofs` list those proofs alone, and its `rules` the rules they prove. A feature with no such proof gets no `ci` file from that runner."; the rules-word table in C4.5 order and "The words are read in that order. A rule whose proofs are all `@manual` reads `passed`, since no run was ever going to observe one."; the foreign-proof paragraph; the `hostname` and `audit.mutation` rows; the merge sentence "and keeps the one there when `engine`, `score` and `missing` are all the same: two entries that differ in `missing` alone are different."
- `references/supported_frameworks.md`: "suggests an entry for every one it finds, in the order they are listed, with the flag that writes the report already in each command"; the example with pytest and vitest; "right after its own"; "`purlin:test` shows you each command, asks once, writes the suggested setting under `tests` and runs again."; "On Windows the pytest entry's command starts `py -3 -m pytest` in place of `python3 -m pytest`, and the rest of it is the same."; "A project that carries several frameworks is suggested an entry for each, one suite per entry under `tests`."
- New proof texts PROOF-207 to 224 (run_script) and PROOF-75 to 79 (evidence_writer), as in the specs.

#### Review: Found and fixed, commit `6333c4070` (`fix(run_script): the words about a remote run and a foreign proof say what the run does`)

- The `_remote` docstring said "The runner runs the same tests this machine would", which decision 95 made false. It now says the runner runs the tests tied to the proofs tagged for its own operating system.
- The module docstring said a foreign proof "is not run on a person's machine", but its test may run there. It now says the proof reads `not run` whatever its test did there, and that the run counts those proofs in one line per system. Two docstring lines left broken or 97 characters long are rewrapped.
- run_script PROOF-213 described the stand-in engine's answer ("an engine that answers ... as its reason and as the feature's `missing`"). That is the test's mechanics. It now reads: `At the gate `strong`, with `mutation_engine` set to `auto` and `mutmut` chosen and not installed, `--all --audit` writes `mutmut is not installed: run "pip install mutmut"` as `audit.mutation`'s `missing` and prints `purlin: mutmut is not installed: run "pip install mutmut"` once`. The test is unchanged.
- The run_script Description now names what `--ci` runs, that the settings file must be readable, and that a command is suggested for every test tool found. The words are "`--ci`, which runs only the tests of the proofs tagged for the runner's own system", "the settings file is there and can be read" and "suggesting one for every test tool it knows".

#### Review: Left, and why

- Commit `89789024f` changed the rule word (a foreign proof with no test reads `no test`) without touching `references/formats/evidence_format.md`. The next commit, `babb23a0f`, brought the format file up to date. CLAUDE.md step 5 wants both in one commit. Fixing it means rewriting the lane's history, and the two commits merge together, so it is reported rather than rewritten.
- Brief item 1 says `_ci`'s `merge_for_host` gets "only those rules". The lane hands it each covered feature's whole rule list, since only the tagged rules would strip another system's section (evidence_writer RULE-4). I agree with the lane's reading. It stays for the owner or integration to decide.
- Brief item 12 says `config_problem` is `settings_stop`'s third case. The lane asks it second, because the 0.9.5 check reads the same file and would otherwise send an unreadable file to `purlin:init --update`, which itself stops on that file. Left for the owner.
- In a `--ci` run where no feature has a tagged proof, nothing runs, `Evidence written to .purlin/evidence/ci/ for 0 features.` is printed, and the host's commit is called with no evidence path. No contract covers this case, so it is left as it was.
- The lane's other calls_left stand as the lane wrote them.

### Lane `mutation`

#### specs/run/mutation.md

- Highest ids now: RULE-23, PROOF-82 (the highest ever held before was RULE-22, PROOF-67).
- Rules: 22 before, 18 after. Proofs: 67 before, 72 after.
- New rule: RULE-23 (the not-installed answer names the engine; reason and every `missing` are
  its sentence).
- Deleted rules: RULE-4, 9, 10, 11, 21 (21 folded into 17).
- Deleted proofs: PROOF-4, 9, 10, 11, 40, 41, 42, 43, 44, 45.
- Re-pointed: PROOF-21 and PROOF-59, RULE-21 to RULE-17.
- Reworded: PROOF-1, 12, 14, 17, 18, 19, 20, 21, 22, 23, 30, 33, 38, 48, 49, 51, 52, 57, 58, 59,
  60, 62, 63, 64, 65, 66; rules RULE-7, 12, 13, 14, 17, 18, 19, 20, 22 and the Description.
- New proofs: 68 to 82.

#### Splits

None. RULE-22 considered and not split (PROOF-67 shows both claims).

#### Calls left, and calls made where nothing else decided

- mutmut's "wrote no report": the contracts name `mutmut` as an `<engine>` of the no-report
  sentence without saying when mutmut writes none. Built as: `mutmut results --all true` lists
  no break at all; then every feature's `missing` is the sentence. A project whose scope files
  give mutmut nothing to break would also read it. RULE-12 says "`mutmut` for a mutmut run whose
  results list no break".
- The module a break names: taken as the dotted segments before the one starting `x_` (or
  `xǁ`, mutmut 3's class method form), as before. The captured-grammar fixture line
  `login.session.Session.x_reset__mutmut_1` so names the module `login.session.Session`, no
  file, and counts for no feature: PROOF-17 and PROOF-60 now read `login` 60 (3 caught, 2
  missed), not 67. The fixture `dev/fixtures/mutation/mutmut_results.txt` is not mine and was
  not changed.
- mutmut with no config block (`pyproject.toml carries no [tool.mutmut] block ...`) and an
  unknown engine still answer `engine: none` with every `missing` `''`; no contract names them,
  left as they were.
- RULE-18 gains the Windows clause as the brief says. It then states two claims with separate
  proofs (PROOF-18, PROOF-79), which C11 would split; RULE-7 (PROOF-7, PROOF-38) and RULE-14
  were already so. Left unsplit; the brief names RULE-22 alone as the candidate.
- PROOF-3 (seven arithmetic inputs) and PROOF-31 (two), and PROOF-30/73 (three settings shapes
  each), still loop over inputs with one expected result kind; the brief names only PROOF-1, 23
  and 30's tools, so they stand.
- The timed-out answer's `reason` keeps the timeout sentence (the contracts fix `missing` only).

#### Words chosen

Printed or stored words, other than the contracts' sentences:
- Spec rule and proof texts listed above (RULE-7, 12, 13, 14, 17, 18, 19, 20, 22, 23; the
  Description; PROOF-68 to 82 and every reworded proof).
- Log lines unchanged in form; the Stryker.NET success log line lost its
  `, attribution <per_test|per_scope>` ending: `<feature>: <n> files broken, <n>% caught`.
- Module and code docstrings.

#### Review: Found and fixed, commit `14723b805` spec(mutation): split eight rules by claim, and one case per proof

1. **Split by claim was applied to RULE-22 alone.** The brief's "How to number, split" section,
   plan call 19 and plan section 5 ("every lane, by C11") apply C11 to every rule of the spec.
   Eight rules meet its test (two or more claims, proofs in clean groups, no proof showing two):
   - `specs/run/mutation.md RULE-1 -> RULE-1 (the engine each framework selects), RULE-24 (the first detected framework with an engine decides), RULE-25 (no framework selects none)`
   - `specs/run/mutation.md RULE-2 -> RULE-2 (a named engine wins), RULE-26 (a name outside the four reads as none), RULE-27 (no mutation_engine reads as none)`
   - `specs/run/mutation.md RULE-3 -> RULE-3 (the formula, rounded half up), RULE-28 (None when no break ran)`
   - `specs/run/mutation.md RULE-7 -> RULE-7 (the project's own Stryker first), RULE-29 (no Stryker anywhere is not installed, with the package named)`
   - `specs/run/mutation.md RULE-13 -> RULE-13 (the command line), RULE-30 (the report is mutation-report.json and no other file)`
   - `specs/run/mutation.md RULE-15 -> RULE-15 (where and how the block is written), RULE-31 (without the block no breaks, and the reason names it)`
   - `specs/run/mutation.md RULE-18 -> RULE-18 (not installed names pip install mutmut), RULE-32 (on Windows mutmut is no engine)`
   - `specs/run/mutation.md RULE-20 -> RULE-20 (every feature listed with its share and missing), RULE-33 (an engine name outside the four is not run)`

   Proofs re-pointed, ids, text and markers unchanged: PROOF-24, 25, 26 to RULE-24; PROOF-27 to
   RULE-25; PROOF-29 to RULE-26; PROOF-30, 73 to RULE-27; PROOF-32 to RULE-28; PROOF-38 to
   RULE-29; PROOF-46, 47, 48, 74 to RULE-30; PROOF-54, 55 to RULE-31; PROOF-79 to RULE-32;
   PROOF-61 to RULE-33. Not split, because one proof shows two of their claims: RULE-5
   (PROOF-5), RULE-8, RULE-12, RULE-14 (PROOF-49 shows the reason and the install check),
   RULE-16, RULE-19, RULE-22 (PROOF-65, 66, 67). The Windows list (integration) names
   RULE-7, 13 and 18, whose Windows cases now sit under RULE-7, RULE-30 and RULE-32.
2. **PROOF-30 and PROOF-73 each held two cases** ("whether they hold other keys or none at
   all") and their tests looped over three settings with one expected result (C11). Now
   PROOF-30 and PROOF-73 are settings holding `gate`, and new PROOF-83 (pytest) and PROOF-84
   (jest) are settings holding no key at all, each with a test of its own. The `None` input
   is dropped: the run reads absent settings as `{}`, so no caller hands the engine `None`.
3. **A break in a class method was untested.** mutmut names it `<module>.xǁ<Class>ǁ<method>__mutmut_<n>`;
   removing the lane's `xǁ` handling left every test passing. New PROOF-85 (RULE-17) shows such
   a break counted for its file.
4. **Three test names named the old answer**: PROOF-38's
   `test_no_stryker_anywhere_leaves_stryker_not_installed`, PROOF-14's
   `test_no_dotnet_on_the_path_names_the_sdk_to_install`, PROOF-62's
   `test_a_missing_the_engine_left_out_is_filled_in_empty`.

#### Review: Left, and why

- PROOF-3 and PROOF-31 loop over inputs whose expected values differ; C11's trigger is one
  expected result, and the lane did not reword them.
- PROOF-52 (a feature with no scope files never starts Stryker) sits under RULE-12, whose text
  does not state that case. Moving it needs a rule no decision gives.
- `mutmut._module` reads the name before the `x_` or `xǁ` segment, and falls back to dropping
  the last segment; for every name mutmut 3 writes the two agree, so the loop never changes a
  result. Left as the lane wrote it.
- The lane's calls stand as it listed them (no report as an empty listing, the fixture line
  `login.session.Session.x_reset__mutmut_1` counting for no file, the no-block and unknown
  engine answers, the timeout reason kept in `reason`).

### Lane `reports`

#### Review: Found

1. Brief items 1 to 7: all built. PROOF-19 reads the brief's words exactly; RULE-8, PROOF-94 to 96
   and the trx row match Q23; near_miss gives C3.9's fix and why word for word (with the stop
   every why ends on); a rule with no proof keeps today's fix; two or more proofs give none; an
   exact comment naming a rule with one proof is not a near miss; `{files}` points at
   hard_gates.md "Where a runner runs" in one clause; line 106 suggests one for each tool; the C9
   example is in the lookup form. Format-Version stays 3, as the brief says.
2. Files: all five changed files are owned; no generated file committed; no @env added.
3. Proofs: 28 rules, 98 proofs, none over 60 words, no id reused (highest ever held on main was
   RULE-24 and PROOF-93; RULE-30 and RULE-74 in history are only inside proof text), every proof
   has exactly one marker directly above a test of its own, every marker names a proof the spec
   has.
4. Breaks (PATH without the real claude; the tests use no model): offering a rule with two proofs
   fails PROOF-97's test; never swapping to the one proof fails PROOF-91's; a rule with no proof
   offering nothing fails PROOF-98's; dropping `completed` from the TRX pass outcomes fails
   PROOF-95's. Each file restored with git checkout -- <file>.
5. Clean release: the dropped `Nothing left to do.` assertion is removed, not inverted; no history
   in any changed line.
6. Style: RULE-24 called a feature "an id a comment may name". Fixed.
7. No format bump needed.

#### Review: Fixed

- b2131c588 spec(reports): RULE-24 names the fix without calling a feature an id. RULE-24 now
  reads: "A marker whose feature, or whose PROOF or RULE id, is one character from exactly one
  that exists is a near miss whose fix names that feature, that proof, that rule where it has no
  proof, or the rule's one proof where it has exactly one; one character from a rule with two or
  more proofs, or from two or more that exist, is none".

#### Review: Left, and why

- A comment with another mistake and an exact rule id that has proofs, `# purlim: login RULE-3`
  where RULE-3 has one proof, gets the fix `# purlin: login RULE-3`: a rule a comment may not
  name, which then fails the run. marker_format.md's brief-given sentence "A suggestion names
  only an id a comment may name" does not hold for it. C3.9 covers only the nearest-id case and
  gives no why for this one, so the code and the sentence are left as they stand.
- phase3-windows-list.md row reports RULE-16 still says "runs through bash from the project's
  folder", which after the split is RULE-25 and RULE-26; integration brings the list's names up
  to date (plan section 2, step 6).
- The lane's own calls_left stand as it wrote them.

#### Review: After the fix

dev/test_reports.py: 102 passed. bash dev/run_tests.sh --fast: 1965 passed, 0 failed; suites 1
passed, 0 failed; exit 0. Branch head b2131c588; main has not moved from f25f62007.

### Lane `host`

#### specs/run/host.md

- **Before:** 19 rules and 87 proofs. Highest ids: RULE-33, PROOF-105.
- **After:** 22 rules and 94 proofs. Highest ids: RULE-38, PROOF-115.
- **Ids:** no id was reused. The highest ids the file's history ever held were RULE-33 and PROOF-105.

#### Splits

- `host RULE-12 -> RULE-12` (the `--remote` round trip, on both git hosts), `RULE-36` (a detached head and a tree with uncommitted changes are refused before anything is pushed). PROOF-12 and PROOF-63 moved to RULE-36.
- `host RULE-28 -> RULE-28` (where a CI run commits, and what a run that commits nothing says), `RULE-37` (on Azure DevOps the branch is read from `BUILD_SOURCEBRANCH` before `BUILD_SOURCEBRANCHNAME`). PROOF-104 and PROOF-105 moved to RULE-37.
- `host RULE-31 -> RULE-31` (Azure DevOps find, wait, results, limits), `RULE-38` (every `git` and `az` process has a time limit and none can prompt). PROOF-83 moved to RULE-38.

RULE-12 and RULE-31 are split at the one claim whose proofs show nothing else. Their other proofs, such as PROOF-24 and PROOF-78, each show several parts of the round trip, so the rest could not be split further.

#### Words I chose

Rule and proof text:
- RULE-27: "A CI commit through the git host's API from a project root that is not the directory the job checked out, named by `GITHUB_WORKSPACE` or `BUILD_SOURCESDIRECTORY`, is refused, so a fixture project a test suite drives cannot land its evidence on the branch under review; with neither variable set every project commits"
- RULE-28: "A CI run commits where its evidence is kept and nowhere else: it commits on a branch under `run/` and off a runner altogether, where no rule is being spoken for; a tag run writes nothing and says `Tag run: nothing is written.`, and a run on any other ref writes nothing and says that ref is neither a run branch nor a signed tag"
- RULE-34: "A CI commit through the git host's API when neither the git host's variables nor git name a branch, as on a detached head, sends nothing and prints `No branch could be read from the git host or from git, so the results were not committed.`"
- RULE-35: "`purlin:test --remote` in a project whose `.purlin/config.json` cannot be read prints the sentence saying why, starts no process, so nothing is pushed, and exits 1"
- RULE-36: "`purlin:test --remote` refuses a detached head and a tree with uncommitted changes before anything is pushed"
- RULE-37: the old RULE-28 clause, word for word, starting "On Azure DevOps the run's branch is read from ...".
- RULE-38: "On Azure DevOps every `git` and `az` process `purlin:test --remote` starts has a time limit, and none can prompt for a credential"
- PROOF-106: "With the GitHub variables set and no git host variable naming a branch, in a repository on a detached HEAD, a CI commit of one evidence file sends no request, returns no commit sha, and prints exactly `No branch could be read from the git host or from git, so the results were not committed.`"
- PROOF-107: "On GitHub with `GITHUB_REF_NAME=topic`, the line saying why the run commits nothing reads exactly `This run is on topic, which is neither a run branch nor a signed tag: the tests ran and nothing is written.`"
- PROOF-108: "In a project whose `.purlin/config.json` holds a comma after its last entry, with a GitHub `origin`, `purlin:test --remote` exits 1, prints exactly `.purlin/config.json cannot be read: <the JSON reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and starts no process"
- PROOF-109 to 115 repeat the text of the proof they were split from, with one gate, URL or result each.

Descriptions:
- `specs/run/host.md` Description, added sentence: "A runner runs the tests of the proofs tagged `@env` for its own operating system; a proof with no tag is proven on a person's own machine."
- Fixture `greeting.md` Description: "A runner runs the tests of the proofs tagged `@env` for its own operating system. RULE-1 is a claim any host can prove, so its proof carries no `@env` tag and is proven on the person's own machine. RULE-2 is a claim only a Linux host can prove, so its proof carries `@env(linux)` and is proven on a Linux runner."

Template header comments:
- Both templates: "A run branch run runs the marked tests a runner runs (references/hard_gates.md in the Purlin plugin, "Where a runner runs"), writes ..."
- Both templates: "A tag run runs the same tests and writes nothing."

`workflow.py` module docstring: "The matrix names the systems some proof in `specs/` is tagged `@env` for that the machine writing the file is not, one job each and no other: setup and the upgrade hand `render_workflow` those tags through `foreign_tags`. A proof tagged `@env(windows)`, written from a Mac, adds a Windows job to prove it. Nothing else about the workflow varies, so two projects with the same tags, written from the same system, get the same file."

Code comments and docstrings in `host.py` and `remote.py`: `current_branch`, `no_commit_line`, `_have`, `_which`, `run_remote`.

#### Calls left

1. **No branch on a runner.**
   - When a runner can name no branch, `commits_here` answers no and `no_commit_line` prints the C3.8 no-branch line, which is decision 97's words for "a remote run that cannot name its branch".
   - That path has no proof of its own. The brief gives RULE-34 one proof, and it is the API commit.
   - A tag run whose ref is empty keeps the old fallback `this ref`.
2. **`purlin_run.py _ci`, lane run's file.** It prints `Evidence committed.` after `commit_files` even when the commit returned `''`: no token, not the workspace, or now no branch. That line contradicts "the results were not committed". I left it.
3. **The templates' matrix sentence.** Both templates still say "The matrix holds one job for each operating system the @env tags in specs/ name, and no other". That no longer holds once scaffold and update hand only foreign tags (C14). The brief's item 10 names only the "runs the marked tests" sentences, so I left it.
4. **More rules that meet C11's split test.** RULE-6 (moved branch retried / other refusal raised at once), RULE-17 (rendered from the template / one reason for a workflow) and RULE-20 (the fixture's five claims) have proofs that fall into clean groups. The brief names only RULE-12, 28 and 31 as candidates, so these are not split.

#### Review: Fixed

- **8404f01fb `spec(host): RULE-17 and RULE-32 split by claim`.** The brief's split instruction and plan call 19 cover every rule that meets C11's test, not only the three candidates named.
  - RULE-17 keeps the template and its two placeholders (PROOF-17, 40).
  - New RULE-39: `A project has a workflow for one reason, a proof tagged `@env` for an operating system this machine is not, and a project with no such proof gets none`. It takes PROOF-41, 42 and 43.
  - RULE-32 keeps the re-read and merge at the head (PROOF-38, 99, 39) and now ends at "is kept".
  - New RULE-40: `The merge of a CI commit drops the rules the spec no longer carries from every section`. It takes PROOF-100.
  - Proof texts and markers are unchanged. Neither rule is on the Windows list.

#### Review: Left, and why

- **RULE-6 and RULE-22 are not split.** The second clause of each, a refusal that is not retried, is the other direction of the same retry claim. The spec quality guide proves a limit in both directions under one rule, and brief item 1 treats RULE-27's two directions the same way.
- **RULE-20 is not split.** PROOF-87 shows the gate `strong` as well as the one feature, so it covers two of the rule's claims.
- **RULE-5, 8, 12, 18, 28 and 31 are not split.** In each, at least one proof shows two claims.
- **The lane's calls left 1 to 3 stand** (the no-branch path of `no_commit_line`, `Evidence committed.` in `purlin_run.py`, the templates' matrix sentence). Fixing the matrix sentence means choosing words that no contract gives.
- **Not owned:** the `purlin_run.py` `_remote` docstring (lane run) still says "The runner runs the same tests this machine would". Decision 95 makes that false.
- **Found in the review, not in the lane's diff:** the `scripts/run/ci.py` module docstring says what the run does not do ("posts no comment and uploads no artifact ... There is no pull request run"). Rewording it means choosing words, so it is left.

### Lane `settings`

#### Spec maxima and counts

- `specs/mcp/config_engine.md`: highest RULE-15 and PROOF-35. It had 10 rules and 27 proofs before and has 11 rules and 25 proofs now. New ids start after the highest ever held since 5941569a0: RULE-13 and PROOF-31.
- `specs/mcp/server.md`: highest RULE-31 and PROOF-158. It had 11 rules and 25 proofs before and has 20 rules and 45 proofs now. New ids start after the highest ever held: RULE-22 and PROOF-138.

#### Splits

- server RULE-3 -> RULE-3 (a notification produces no response; PROOF-3, 126), RULE-23 (input that is not JSON answers -32700; PROOF-125)
- server RULE-4 -> RULE-4 (an unknown tool answers -32601; PROOF-4), RULE-24 (an unknown method answers -32601; PROOF-127)
- server RULE-6 -> RULE-6 (a call may name its workspace, `~` expanded; PROOF-6, 129), RULE-25 (a call naming none uses the startup root, whatever an earlier call named; PROOF-128)
- server RULE-10 -> RULE-10 (a write naming no key is refused; PROOF-10), RULE-26 (an unknown action is refused; PROOF-136)

These rules were not split, because at least one proof shows two of the rule's claims:

- config_engine RULE-8 (PROOF-24 shows both creating the file and setting the key).
- config_engine RULE-13 (PROOF-15 and 28 to 30 each show the name and the root asked for alone).
- server RULE-5 (PROOF-5), RULE-7 (PROOF-131), RULE-8 (PROOF-133) and RULE-9 (PROOF-134 shows both a write and a read).

config_engine RULE-10 is read as one claim, atomicity, together with its consequence. The brief keeps PROOF-26 and PROOF-27 under it.

#### Calls left or made where nothing decided

- **The trailing-comma proof uses line 2, not line 3.** The file is `{` on one line and `  "gate": "passed",}` on the next. On a three-line file, Python 3.14 names the line of the comma (2) and Python 3.9 names the line of the `}` (3). On this two-line file both name line 2. The reader's message also differs by version (3.14 prints `Illegal trailing comma before end of object`, 3.9 prints `Expecting property name enclosed in double quotes`), so the tests take the message from the JSON reader itself and fix only the line.
- **The exception type.** `ConfigUnreadable(ValueError)` in `config_engine.py` is the exception `update_config` and `resolve_config` raise. Its name is internal.
- **`resolve_config` also raises on an unreadable file.** It no longer answers `{}`, because `_read_json` no longer folds the failure. No proof of config_engine shows the raise from a read; the brief named only the save. Its callers `payload.py`, `purlin_run.py` and `remote.py` check `config_problem` first under C1.9, in lanes `core`, `run` and `host`. Until those lanes merge, one of those callers given an unreadable file raises `ConfigUnreadable` instead of reading `{}`.
- **`<cause>` in `The setting was not saved: <cause>.`** It is the system's own message (`strerror`, for example `No space left on device`), or the error's text when it has no `strerror`, as C3.4 does for a failed open.
- **`<value>` in the refusal.** A string goes in as written; any other value goes in as its JSON (`101`, `null`, `true`, `[...]`). So null reads `"null" is not accepted for gate; ...`.
- **"A whole number".** Only a JSON integer counts: `true`, `false`, `50.0` and `"50"` are refused for `min_strength` and `audit_parallel`.
- **The order of the refusals.** `version` is refused first, whatever else the call holds. Next comes the missing value, for known keys only, as the brief says; an unknown key with no value is written as null, as it was before. Last comes the accepted-value check.
- **`version` asked with no key.** A write naming no key keeps its `Error: 'key' is required for write action.` answer, which comes before any of these checks.
- **Where the server's unreadable-file rule goes.** It is a new rule, RULE-27, and not a proof under RULE-7. RULE-7's text covers only a root with no settings file.
- **PROOF-158 under RULE-22.** The brief places it there. That gives RULE-22 a claim only PROOF-158 shows, which C11 would otherwise split into a rule of its own. I followed the brief and did not split it.

#### Words chosen

These are words a person reads that no decision or contract gave:

- Spec rule texts: config_engine RULE-14 and RULE-15, the new wording of RULE-10 ("and says so"), and server RULE-3, 4, 6, 9, 10 and 22 to 31 as they read in the specs. The sentences inside them are quoted from C3.4 and C3.5.
- Proof texts: config_engine PROOF-26, 27 and 32 to 35; server PROOF-139 to 158.
- The header comment of `scripts/purlin_python.sh`:

  ```
  exits 1, so a skill that starts a script through it fails loudly. With
  PURLIN_PYTHON_SOFT set to 1 it exits 0 after the same line: the plugin
  manifest sets it for the MCP server, whose stderr the client shows, so the
  client decides what a missing interpreter means there. The usage line, for
  a call that names no script, exits 0 either way.
  ```

- The module docstring of `config_engine.py`: "A file that exists and cannot be read is never read as empty: both raise ConfigUnreadable with the sentence config_problem gives, so a save never overwrites a file a person can still fix."
- Code comments in `server.py`: the one above `KNOWN_SETTINGS` and the one above the `config_problem` check.

No printed line was chosen: every answer the tool prints is C3.4's or C3.5's, word for word.

#### Review: What was fixed

- 17905a65e spec(server): PROOF-141 quotes the sentence and holds 59 words. It now reads
  `...; the answer is exactly `.purlin/config.json cannot be read: <the JSON reader's message> at line 2. Fix the file by hand; nothing ran and nothing was saved.`, and the file is unchanged`,
  the sentence quoted as PROOF-139 and PROOF-140 quote it. Case, marker and test unchanged.

#### Review: What was left, and why

- server RULE-22 holds two claims after PROOF-158 joined it (the start through `sh` and the
  resolver, shown by PROOF-22 and 137; the soft variable, shown by PROOF-158 alone), which C11
  would split. The brief places PROOF-158 under RULE-22 by name, so it stays; listed for the
  owner.
- config_engine RULE-14 (one proof per cause) and server RULE-29 (one proof per setting) each
  list cases, not claims: the brief defines each as one rule with one proof per cause or
  refusal, so neither is split.
- `resolve_config`, and through it `payload.build_payload`, now raise `ConfigUnreadable` on an
  unreadable file. Its callers in `scripts/` (`payload.py`, `remote.py`, and every caller of
  `build_payload`: status, drift, the dashboard data, package, update, the audit reader, sign
  and the run) are guarded by the C1.9 checks of lanes `core`, `run`, `host`, `drift`,
  `package`, `update`, `review` and `signing`. Until those merge, such a caller given an
  unreadable file raises instead of reading `{}`; integration sees the joined result.

#### Review: Words chosen by the review

- PROOF-141's text, as quoted above, the closing clause `and the file is unchanged` being the
  review's.

### Lane `drift`

#### Highest ids

- `specs/mcp/drift.md`: RULE-25, PROOF-58.
  - Before: 18 rules and 50 proofs; the highest held since the whole rewrite 0585c2f89 was RULE-19 and PROOF-50.
  - After: 24 rules and 58 proofs.
- `specs/skills/skill_drift.md`: RULE-9, PROOF-35.
  - Before: 4 rules and 31 proofs; the highest held since the rewrite 7b81a9b88 was RULE-8 and PROOF-35.
  - After: 5 rules and 12 proofs.

#### Splits

- drift RULE-15 -> RULE-15 (the test-files-changed line), RULE-22 (the to-test-by-hand and to-sign lines of Left to do). PROOF-31, 32 and 33 now point at RULE-22.
- drift RULE-18 -> RULE-18 (the report carries exactly since and roles; the roles are pm, eng, qa), RULE-23 (each view's fixed keys, PROOF-49), RULE-24 (the QA view's `left`, PROOF-34), RULE-25 (a role argument narrows the answer, PROOF-50).
- skill_drift RULE-1 -> RULE-1 (the frontmatter), RULE-9 (the command reference row, PROOF-9).

#### Calls left

- skill_drift RULE-2 is not split. Its criteria clause is kept after the brief's words because PROOF-20 ("do not restate them here and do not invent a line the tool does not return") shows both claims, and C11 forbids a split then.
- These rules are not split because their proofs are cases of one claim, or a proof shows two claims:
  - drift RULE-2: PROOF-5 shows both the rebase and the first step.
  - drift RULE-3 and RULE-4: count, date and fewer commits are cases or boundaries.
  - drift RULE-6: PROOF-38 shows the name match and the no-change line.
  - drift RULE-7: the folder qualifier and PROOF-14.
- skill_drift RULE-3 keeps its wording. The brief names only RULE-2 for the "tells the agent" form.
- `scripts/mcp/purlin/status.py` (lane `core`) calls `drift.pin_report`, so the status now:
  - prints `<name>: the source could not be read (<the not-a-spec reason>).` for an anchor whose source names no repository. C13 says "nothing else warns of it".
  - runs `git ls-remote` for Azure DevOps anchors.

  I did not change `status.py`.
- The drift skill's closing table has no row for an anchor line reading `error`, for a source that cannot be read or one that names no repository. This was already missing before this work. The not-a-spec line carries its own `Run purlin:spec <name>`.
- `references/drift_criteria.md` "Config field ownership" still says the table must name every field `templates/config.json` carries, and it keeps the `version` row, which P1 took out of the template. No item covers this.

#### Words I chose

- Criteria line 69 (in place of "A file deleted in the range is not on disk and is in neither list."): "A file deleted in the range counts as changed. It joins `code_changed` under every spec whose `> Scope:` entry covers it: a file entry equal to its path, a folder entry it lies under, or a glob that matches it. A deleted file no entry covers joins `unscoped`, with that list's exclusions."
- Criteria "Anchors behind", added to the paragraph: "A source that names no repository, a description in words or a file on disk, is reported without one: no process is handed it. An anchor with no `> Source:` is a local anchor and is not checked."
- drift RULE-7, added: ", and a file deleted in the range counts under every spec whose scope entry names it, holds it in its folder or matches it as a glob"
- drift RULE-8, added: ", a file deleted in the range included,"
- drift RULE-21: "When `.purlin/config.json` exists and cannot be read, drift's answer is the sentence `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.` alone, in place of the report, and it reads nothing else"
- drift RULE-18: "The report carries exactly `since` and `roles`, and the roles are exactly `pm`, `eng` and `qa`"
- drift RULE-22: "The QA view prints the `to test by hand` and `to sign` lines of `Left to do` in the words the status prints them, as `1 rule to test by hand: purlin:sign`, and no other line of `Left to do`"
- drift RULE-23: "Each view carries its lines and the facts they were built from under fixed keys"
- drift RULE-24: "The QA view's `left` holds the status's own items of `Left to do` of the kinds `to_test_by_hand` and `to_sign`, the items its lines of `Left to do` are built from"
- drift RULE-25: "A role argument narrows the answer to exactly `since`, `role` and `view`"
- drift PROOF-51 to 58, as written in `specs/mcp/drift.md`.
- skill_drift RULE-1: "`skills/drift/SKILL.md` opens with a frontmatter block whose `name` is `drift` and whose `description` is one non-empty line"
- skill_drift RULE-2: "The skill tells the agent to take its data from the `drift` tool and to show the lines it returns, and points at `references/drift_criteria.md` for what each line means and where it comes from rather than restating it"
- skill_drift RULE-9: "`references/purlin_commands.md` carries a row for `purlin:drift` in its command table, with its purpose"
- Code comment above `_ABSOLUTE_WINDOWS_PATH`: "An absolute path on Windows: a drive letter, or a UNC share. Neither begins with a slash, so the test below names both, to read a local clone on that operating system as a git repository."

#### Review: Found and fixed

1. **A covered file was called uncovered** (`drift` RULE-8). The lane's code took every changed
   path missing from the index as deleted in the range. A file that the range changed and that
   was then removed with `git rm`, not committed, was not among any scope's deletions. The
   engineer view therefore named it under no spec's scope, though `login` covers it; this was
   reproduced. The deleted set is now the range's own deletions that are not in the index, and
   such a file is left out, as before the lane. Fixed in b6b6c71ae
   `fix(drift): only a file the range deleted joins the deleted, so a covered file removed after the pull is not called uncovered`,
   with the new proof PROOF-59 (RULE-8) and its test.
2. **skill_drift's new rule took RULE-9, not the next free id.** 7b81a9b88 wrote
   `specs/skills/skill_drift.md` whole: RULE-4 to 8 were replaced by RULE-1 to 4, and RULE-4
   took a new meaning. Its highest rule since then is RULE-4, so C11 gives RULE-5. Fixed in
   3bd4878a1
   `spec(skill_drift): the command reference's rule takes RULE-5, the next free id`.
   The split now reads `skill_drift RULE-1 -> RULE-1 (frontmatter, PROOF-1), RULE-5 (command reference row, PROOF-9)`.
   The lane's commit message 3032c6348 still says RULE-9, and it is left as history.

#### Review: Left, and why

- Every call the lane listed stands.
- The `status.py` line for a `not_a_spec` row belongs to lane `core`'s file.
- The closing table of the drift skill has no row for an anchor error line. For a not-a-spec
  anchor, the line printed now names `purlin:spec` itself. Adding a row means choosing words
  that no contract gives.
- The lane called the criteria's "Config field ownership" stale. On review it is not false:
  it asks that the table name every field the template carries, and the table does. Its
  `version` row describes the project's settings file, which still carries `version`. It is
  left unchanged.

#### Review: Words chosen in review

- PROOF-59 (RULE-8): "A pull changes `src/auth/login.py`, which the spec `login` covers, and the file is then removed with `git rm` and not committed; the engineer view prints no line of changed files under no spec's scope"
- `_deleted` docstring: "The paths the range deleted, limited to `pathspecs` when given. A range that reaches the first commit starts from nothing, so it deletes nothing."

### Lane `update`

#### Ids and counts

- `specs/init/update.md`: the highest RULE is RULE-40 and the highest PROOF is PROOF-116. The highest ids ever used were RULE-32 and PROOF-113; the file has never been written whole since 530acf9c8.
- Rules went from 28 to 34 (RULE-11 and RULE-32 deleted; RULE-33 to RULE-40 added).
- Proofs went from 109 to 103 (PROOF-20 and PROOF-59 to PROOF-66 deleted; PROOF-114, 115 and 116 added).

#### Splits

- update RULE-8 -> RULE-8 (no proof or run file beside a spec), RULE-33 (dashboard data untracked, on disk, in .gitignore), RULE-34 (the .purlin/cache/ folder deleted)
- update RULE-16 -> RULE-16 (plugin copies removed, other files left), RULE-35 (the wiring removed, backed up, named), RULE-36 (a .csproj compiling the logger named and left)
- update RULE-26 -> RULE-26 (the question at strong/signed where an engine runs here), RULE-37 (no engine, or one that cannot run here: asked nothing, none, one line), RULE-38 (at passed nothing asked or said, none), RULE-39 (a config carrying mutation_engine keeps it)

#### Words chosen (no decision or contract gave them)

- RULE-12: `; an empty answer takes the default and prints nothing, an answer that is one of the three gates is taken, and any other answer takes the default and prints `purlin: "<answer>" is not a gate; reading it as <gate>.`, naming the default`
- PROOF-47: `Run without `--yes` on the sample v0.9.5 project, the answer `whenever` to the gate question prints `purlin: "whenever" is not a gate; reading it as passed.` and writes the gate `passed``
- PROOF-48: `A sample v0.9.5 config that names the gate `signed`, with `pre_push` `off`, is asked `Gate [signed]: `; an empty answer writes `signed`, and no line saying `is not a gate` is printed`
- RULE-26: adds `that runs on this operating system` after "where an engine".
- RULE-33: `The dashboard data is untracked, left on disk, and named in `.gitignore``
- RULE-34: `The `.purlin/cache/` folder 0.9.5 kept is deleted, from git and from disk`
- RULE-35: `The wiring v0.9.5's init wrote is removed from each file that carries it, each backed up first and named in one line: ...` (the rest is RULE-16's old text)
- RULE-36: `A `.csproj` that compiles the xUnit logger v0.9.5 shipped is named with what to remove by hand and left as it was`
- RULE-37: `At the gate `strong` or `signed`, an update of a config with no `mutation_engine` whose project has no engine, or only one that cannot run on this operating system, asks nothing about mutation, writes `none` and says why in one line`
- RULE-38: `At the gate `passed`, an update of a config with no `mutation_engine` asks and says nothing about mutation and writes `none``
- RULE-39: `A config that already carries `mutation_engine` keeps it`
- RULE-40: `A `.purlin/config.json` that cannot be read stops the update before it writes anything: it prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.` and exits 1`
- PROOF-114: `On a machine given as Windows, at the gate `strong`, the sample v0.9.5 project given a `conftest.py` is asked no mutation question, gets `mutation_engine` `none`, and the output says `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.``
- PROOF-115: `The sample v0.9.5 project with a GitHub remote, given one proof tagged for the operating system the update runs on and one for another, is updated with `--yes`; the runner file written names the runner image of that other system and no other image`
- PROOF-116: `The sample v0.9.5 project whose `.purlin/config.json` has a comma after its last value is updated with `--yes`; it exits 1, prints `.purlin/config.json cannot be read:`, the reader's message with its line, and `Fix the file by hand; nothing ran and nothing was saved.`, and `git status` and the latest commit are unchanged`
- Code comments only: "An engine that cannot run on this operating system counts as none." and "One job per system some proof is tagged for that this machine is not."

#### Calls left

- The unreadable-settings line goes to stderr, as the upgrade's no-project line does. The contract says only "prints it". The test reads stdout and stderr together.
- PROOF-116's test checks ` at line <n>.` and not the JSON reader's exact message, because Python 3.13 words a trailing comma differently from earlier versions.

#### Review: Found and fixed (d9b620def, `test(update): the runner question and the unreadable-settings line are checked word for word`)

- No test checked the question C14 fixes word for word. With the old question back in the code, every test still passed. PROOF-49 now quotes the question, and its test asserts the whole prompt: `Write .github/workflows/purlin.yml, one job per operating system your specs name that this machine is not? [y/N] `.
- The PROOF-116 test checked only ` at line <n>.`, so a wrong JSON message would still have passed. It now compares the whole line with `.purlin/config.json cannot be read: <msg> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`. It takes `<msg>` and `<n>` from the JSON reader's own error on the same text, so the check holds on every Python version. This closes the lane's second call.

Words I chose for a person to read, the reworded PROOF-49: `The sample v0.9.5 project asked `Write .github/workflows/purlin.yml, one job per operating system your specs name that this machine is not?` and answering `n` has no workflow file under `.github/`, its output says `run purlin:init again to add it later`, and `workflows` is no longer pending`

#### Review: Left, and why

- The unreadable-settings sentence goes to stderr. C1.9 says only "prints it". Lane `scaffold` also prints to stderr, while lanes `signing`, `package`, `review` and `host` print to stdout. Choosing one stream for every command is a call no contract makes.
- `rewrite_markers` keeps `\r\n` on the comments it writes only where every line of the file ends with `\r\n`. In a file with mixed endings, each existing line keeps its own ending, and a new comment ends with `\n`. Brief item 7 covers the lines that already exist, not the lines the upgrade adds. No test runs a file with `\r\n` endings; wave W adds the Windows proofs for RULE-13, 23 and 24.
- The `--fast` sweep gives the same result as the lane's: 185 failed, 1741 passed and 24 errors, all 209 in files this lane does not own. The first error in each is `AttributeError: module 'update' has no attribute 'set_up_by_095'`, and the other errors (no evidence file, unpack errors) come after the run stops. Lane `run` has its own `set_up_by_095` in `purlin_run.py` and merges first.

### Lane `signing`

#### Spec `specs/review/signatures.md`

- Highest RULE: RULE-73. Highest PROOF: PROOF-152.
- Rules 39 before, 47 after. Proofs 105 before, 111 after.
- Next free ids at the start were RULE-65 and PROOF-146 (history read with
  `git log -p --follow`; highest ever held RULE-64, PROOF-145).

#### Splits

- signatures RULE-11 -> RULE-11 (the walk opens on what waits and shows each rule; PROOF-31, 89), RULE-68 (the three answers, the note, the closing `Walked` line; PROOF-86, 88, 32, 33), RULE-69 (the walk writes nothing until it closes; PROOF-87)
- signatures RULE-45 -> RULE-45 (the signed tag and its message; PROOF-67), RULE-70 (the `Tagged` and push lines; PROOF-100), RULE-71 (writing the tag pushes nothing; PROOF-101), RULE-72 (the walk that signs the last rules writes the tag; PROOF-81)
- signatures RULE-53 -> RULE-53 (the package committed signed below the tag; PROOF-78), RULE-73 (a package not written or committed: no tag and its line; PROOF-79)

#### Words chosen (no decision, contract or brief gave them)

- Rule texts: RULE-66 `When git cannot write `signed/<version>`, the command prints `No tag: git could not write signed/<version>: <git's own message, first line>.` and exits 1`; RULE-67 `A `.purlin/config.json` that cannot be read stops the command before it reads or writes anything else: it prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, writes nothing and exits 1`; RULE-64 gains `, printed last, just above the summary ending,`.
- Split rule texts: RULE-68 `At each stop of the walk the command takes one of the three answers sign, case or skip, carries the line a person writes when signing a hand check as that signature's note and signs with no note when the line is empty, and closes with `Walked <n> rules: <s> signed, <c> cases added, <k> skipped.``; RULE-69 `The walk writes nothing until it closes`; RULE-70 `Having written `signed/<version>`, the command prints `Tagged signed/<version> at <sha7>.` then `Nothing left to do. Push the tag to release it: git push origin signed/<version>``; RULE-71 `Writing the tag pushes nothing`; RULE-72 `The walk that signs the last rules writes the tag`; RULE-73 `When the evidence package cannot be written or committed the command writes no tag and prints `No tag: the evidence package was not committed: <why>.``.
- Proof texts PROOF-125, 144, 146 to 152 as in the spec.
- Printed fallback where git fails and prints nothing at all: `git exited with <n>` in place of git's message.
- The module docstring's exit paragraph and settings sentence.

#### Calls left or made

- Git's own message, first line (C3.6): git prints `The tag message has been left in .git/TAG_EDITMSG` before its error, so the literal first line names no cause. Built: the first line starting `fatal: ` or `error: ` answers, with that word cut, else the first line; a closing full stop is cut so the line does not end `..`. Example: `No tag: git could not write signed/2.1.0: cannot lock ref 'refs/tags/signed/2.1.0': 'refs/tags/signed' exists; cannot create 'refs/tags/signed/2.1.0'.` The owner may want the prefix kept or the literal first line.
- The brief gave item 2 "one proof" and no rule; it went under a new RULE-66, since RULE-65's given words speak of a refused tag.
- RULE-65 as the brief words it states two claims (exit 1 for a must-fix reason, exit 0 for a tag already written) whose proofs fall into two groups; it is left whole because its text was given.
- Where both a named rule is unknown and the signature commit is not made, the unknown line prints just above `NOT_MADE` (no summary is printed in that path).
- The settings stop comes after the check that `--project-root` is a directory (a bad command line, exit 2); `config_problem` answers None for a missing folder, so the order changes nothing seen.

#### Review: Found and fixed (d22e5fd42, `spec(signatures): RULE-13, 22 and 46 split by claim; PROOF-151 names what git gives`)

- PROOF-151 said the line "goes on with the first line git printed". git first prints
  `The tag message has been left in .git/TAG_EDITMSG`, and the code and the test both use git's
  reason instead. The proof now reads "goes on with git's own reason, which names
  `refs/tags/signed`, and ends with one full stop", which is what the test asserts.
- Three more rules meet C11's split test (plan call 19), and the lane had not split them:
  - signatures RULE-46 -> RULE-46 (work left: no tag, and the summary ending; PROOF-68),
    RULE-74 (no tag over one already written, and its line; PROOF-103), RULE-75 (`--release`
    names another tag; PROOF-102)
  - signatures RULE-13 -> RULE-13 (the note on each rule named; PROOF-16, 145), RULE-76 (`--note`
    misused exits 2; PROOF-17, 93, 94)
  - signatures RULE-22 -> RULE-22 (`--help` exits 0; PROOF-28), RULE-77 (an unknown option exits
    2; PROOF-132, 133)
  - Proof texts and markers are unchanged; only the `(RULE-N)` changes.
- Words chosen in this review:
  - RULE-46 `While any work but the tag is left the command writes no tag and prints the summary ending`
  - RULE-74 ``No tag is written over one that already exists, which prints `No tag: <tag> is already written. Name another with --release <name>.` ``
  - RULE-75 `` `--release <name>` names another tag, `signed/<name>` ``
  - RULE-13 ``--note` puts one line on the signature of each rule named, the line a person writes after checking a `@manual` proof by hand`
  - RULE-76 `` `--note` with no rule named, with `--all`, or with no line, exits 2 ``
  - RULE-22 `` The command exits 0 for `--help` ``
  - RULE-77 `An unknown option exits 2 whether or not a feature is named`
  - PROOF-151 as above.

#### Review: Left, and why

- Whether git's `fatal: `/`error: ` word is cut, and whether the first error line is used
  rather than the literal first line, is the lane's call on C3.6's `<git's own message, first line>`.
  No test pins it; left for the owner.
- The home-folder helper's order (`HOME`, then `USERPROFILE`) is not shown by any test on this
  Mac, because Python reads `HOME` here too. The brief asks only that PROOF-21, 95 and 22 hold.
  Wave W's Windows proof for RULE-17 shows it.
- RULE-65 holds two claims but is left whole, since the brief gave its text. RULE-12, 17, 20,
  54, 59, 60, 64 and 68 were not split: in each, a proof shows two of its claims, or the claims
  are one rule proved in both directions.
- The docstring's `nothing was left to tag` (C6 says `nothing to tag`) is lane wording, left
  as it is.
- `phase3-windows-list.md` names signatures RULE-17, 18, 20, 45, 50 and 60. RULE-45 was split;
  integration brings the names up to date.

### Lane `review`

#### Spec numbers

`specs/review/ai_audit.md`:

| | Before | After |
|---|---|---|
| Rules | 16 | 20 |
| Proofs | 70 | 72 |
| Highest rule | RULE-16 | RULE-21 |
| Highest proof | PROOF-79 | PROOF-81 |

The ids were checked against history from the last whole rewrite, 7c9dc9144: before this work the highest ids were RULE-16 and PROOF-79.

Proofs deleted: none. Proofs re-pointed:
- PROOF-7: RULE-15 -> RULE-13
- PROOF-24: RULE-7 -> RULE-18
- PROOF-25: RULE-7 -> RULE-19
- PROOF-26 and PROOF-62: RULE-7 -> RULE-20
- PROOF-29, PROOF-77 and PROOF-63: RULE-14 -> RULE-17

Proofs reworded: PROOF-76 and PROOF-29.

#### Words I chose

Rule texts:
- RULE-7: `With no `claude` on the path the model cannot be reached: no call is made and the answer is only the reason `claude is not on PATH``
- RULE-13: `` `ai_audit.py --help` exits 0, an unknown option or a missing `--feature` exits 2, a feature with no rule in the project exits 1, a rule the project does not hold prints only `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.` and exits 1, and the command calls no model ``
- RULE-14: `` `ai_audit.py --feature <name>` prints what the audit reads for one rule named with `--rule`, or for every rule of the feature without it ``
- RULE-17: `` For each rule `ai_audit.py` prints, it shows the rule, its proofs, each test, the test strength beside the minimum where one was measured and nothing of strength where none was, and what the last audit found, its verdict, model, time and each finding, and after the findings each note, starting `Note:` ``
- RULE-18: `` When `claude` exits with an error the model cannot be reached, and the answer is only the reason `claude exited with an error` ``
- RULE-19: `` When `claude` runs past its limit the model cannot be reached, and the answer is only the reason `claude timed out after <n> s` ``
- RULE-20: `` An answer with no settled line is asked for once more, and when the second has none either the model cannot be reached and the answer is only the reason `claude answered without a settled line` ``
- RULE-21: `` When `.purlin/config.json` cannot be read, `ai_audit.py` prints the sentence saying why, prints no rule, writes nothing and exits 1 ``

Proof texts:
- PROOF-29 (ends): `` ... the command for that rule prints `login RULE-2`, its text, its proof, its test's line, `Test strength: 90 percent   minimum 70`, `What the audit found`, `Weak, by unknown at 2026-09-13T12:05:00Z.` and the finding, and no `Note:` line ``
- PROOF-76: `` The command run for `--feature login --rule RULE-99`, a rule the spec of `login` does not declare, exits 1 and prints only `login RULE-99 is not a rule any spec has. Run purlin:status login to see its rules.` ``
- PROOF-80: `` Under the gate `strong`, with an audit entry for `RULE-2` holding the finding `PROOF-2 asserts the status but never the body the rule names.` and the note `PROOF-2 holds two cases.`, the command run for that rule prints the finding's line and, on the line straight after it, `  Note: PROOF-2 holds two cases.` ``
- PROOF-81: `` In a project whose `.purlin/config.json` holds a comma after its last setting, the command run for `--feature login` exits 1, prints only `.purlin/config.json cannot be read: <the JSON reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and every file under `.purlin/` keeps its bytes ``

Module docstring:
- "with each note after the findings."
- "A rule no spec has is named on one line, and a settings file that cannot be read stops it before the payload is built."
- "Exit codes: 0 a rule was printed, 1 the rule is not in the project or the settings file cannot be read, 2 the command line was wrong."

`references/review_criteria.md`, "What test strength says", whole:
> Test strength is one share per feature, in every language: of the deliberate breaks made to the feature's code, the share its tests caught, as an integer percent. The model is shown that one share for the feature the rule belongs to, beside `min_strength` from `.purlin/config.json`, as `Test strength: 71 percent (minimum 80)`; a rule has no number of its own. Where nothing was measured, or the engine cannot run on this system, the model is shown `Test strength: not measured`; `references/hard_gates.md`, "The three steps", says when that leaves a rule `weak`.
>
> It says one thing: the feature's tests noticed when its behaviour changed. It does not say the tests prove the right rule, that the proof text matches the test, or that the rule is worth having. A feature can reach 90 percent while one of its proofs observes the wrong thing, and a rule proved correctly can belong to a feature at 0 percent because nothing broke. Read it beside what the audit observed, never instead of it.

Other criteria phrases:
- The gate paragraph: "where mutation testing is on its feature's test strength must reach `min_strength`".
- The report bullet's heading: "**The feature's test strength, beside the minimum, where it was measured.**"
- The report bullet's wording: "Where nothing was measured the report says nothing of strength, and the model reading the rule is shown `Test strength: not measured`."
- The notes bullet: "They are written beside what the audit found, printed after the findings, each on a line of its own starting `Note:`, and change no cell."

#### Calls left as they are

- The brief writes the model's line as `test strength: not measured`, in lower case. The product sends `Test strength: not measured` (RULE-2, PROOF-79, fixed in 6f8a54cc2). I kept the product's line and quoted it as it is in the criteria.
- The pointer names `references/hard_gates.md`, "The three steps", the section that holds the gate table under which lane `words` writes the paragraph.
- Q65: I made a new rule (RULE-21) rather than a proof under RULE-13, because RULE-13 did not say what happens when the settings file cannot be read.
- The notes line: where an entry has no findings, the notes follow `  It found nothing.`
- The unknown-rule and settings lines print to standard output, as the existing `audit: no rule of ...` line and `sign.py` do.
- The `--feature nothing --rule RULE-1` case prints `nothing RULE-1 is not a rule any spec has. ...`. No proof covers it.
- PROOF-7's text, which describes the internal empty result, is kept as it stands under RULE-13, as the brief says ("re-pointed").
- RULE-5 (the four verdicts), RULE-13 (the exits) and RULE-1 arguably meet C11's split test. The brief names only RULE-7 and RULE-14, so I left the others unsplit.
- In PROOF-81, the JSON reader's message and line are written as placeholders. They differ by Python version (3.13 reads `Illegal trailing comma before end of object at line 2`), so the test builds the expected line from the reader's own error.
- `dev/plans/phase3-windows-list.md` lists ai_audit RULE-7 with the timeout test; that is now RULE-19. Integration brings the list up to date.

#### Review: Fixed

- 2f8fbbbac `docs: review criteria say what the model is shown of strength, and set off the gate's condition`
  - I removed the clause `; a rule has no number of its own`. The writing style says "What is, not what was" and does not describe a missing thing by denying it. The sentence before it already says what the model is shown.
  - The gate paragraph read "where mutation testing is on its feature's test strength must reach `min_strength`", which parses as "on its feature's test strength". It now reads "and, where mutation testing is on, its feature's test strength must reach `min_strength`".

#### Review: Left, and why

- By C11's test alone, RULE-2 (proof groups {11}, {12}, {79}), RULE-5 ({17}, {18}, {19}, {22, 57}), RULE-8 ({5}, {8}) and RULE-13 ({30}, {74, 75}, {31}, {76, 7}, {33}) could each be split. The brief names RULE-7 and RULE-14 as the candidates, and whether each clause is a separate claim is a call the brief does not make. I left them unsplit. The lane reported RULE-1, RULE-5 and RULE-13; RULE-1 does not meet the test, because PROOF-1 shows every condition at once.
- PROOF-7 still describes the empty internal result. OQ14 option 1 moves "its one proof" under the printout rule, and the brief says to re-point it only.
- All other calls the lane listed stand as it reported them.

### Lane `package`

#### specs/export/package.md

- Highest RULE-19, highest PROOF-37 (next free before: RULE-11, PROOF-36).
- Rules 10 -> 19; proofs 35 -> 37.

#### Splits

- package RULE-6 -> RULE-6 (words, kind of work, proofs, tests: PROOF-9, 18), RULE-11 (each result with its operating system, source, time, commit, runner and machine: PROOF-25), RULE-12 (what the audit found, with the model and the fingerprint of its instructions: PROOF-26), RULE-13 (each current signature with its fields and locked hashes: PROOF-27, 28), RULE-14 (one status per step up to the gate: PROOF-20, 29), RULE-15 (nothing names who last changed a test: PROOF-11)
- package RULE-1 -> RULE-1 (run with no argument, it writes the file, prints the line, commits nothing, leaves no checkout: PROOF-1), RULE-16 (no version stated: PROOF-21)
- package RULE-8 -> RULE-8 (same bytes, `\n` line ends, trailing newline: PROOF-13, 14), RULE-17 (every time in UTC ending in `Z`: PROOF-15)
- package RULE-10 -> RULE-10 (`--commit` commits the package alone with its subject: PROOF-10, 35), RULE-18 (a second `--commit` prints `Package unchanged.`: PROOF-34)

Proofs re-pointed (text unchanged, markers unchanged): PROOF-25 -> RULE-11, PROOF-26 -> RULE-12,
PROOF-27 and 28 -> RULE-13, PROOF-20 and 29 -> RULE-14, PROOF-11 -> RULE-15, PROOF-21 -> RULE-16,
PROOF-15 -> RULE-17, PROOF-34 -> RULE-18. The moved lines now sit at the end of `## Proof`, in
rule order. No proof deleted.

#### Words chosen (a person reads them)

Rule texts:
- RULE-6: `Each rule carries its words exactly as the spec has them, the one kind of work it waits for or null, its proofs and its tests`
- RULE-11: `Each rule carries each result with its operating system, source, time, commit, runner and machine`
- RULE-12: `Each rule carries what the audit found with the model and the fingerprint of its instructions`
- RULE-13: `Each rule carries each current signature with the signer's email and name, the key's fingerprint, the feature it applies to, the machines, the time, the note, whether its commit is signed and the hashes it locked`
- RULE-14: `Each rule carries one status for each step up to the gate`
- RULE-15: `Nothing in the package names who last changed a test`
- RULE-1 (cut): `Run with no argument, the command writes `.purlin/evidence/package/<version>.json`, taking the version the project states as `purlin:sign` reads it for its tag, prints `Evidence package written to <path>. State: <finished|not finished>.`, commits nothing and leaves no checkout behind`
- RULE-16: ``Run with no argument in a project that states no version, the command prints `No version: nothing in this project states one. Name it with --release <version>.`, writes nothing and exits 1``
- RULE-8 (cut): ``The same commit gives the same bytes: exporting twice, or from a second clone at the tag, writes identical files, with `\n` line ends and a trailing newline``
- RULE-17: ``Every time in the package is in UTC, ending in `Z` ``
- RULE-10 (cut): ``--commit` commits the package alone with the subject `purlin: evidence at <sha7>`, naming the commit the evidence was taken at``
- RULE-18: ``A second `--commit` over the same evidence prints `Package unchanged.` and leaves the commit the evidence was taken at named``
- RULE-19: ``Where `.purlin/config.json` cannot be read, the command, `--check` included, prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, writes nothing and exits 1``

Proofs:
- PROOF-36 (RULE-19): ``In a project whose `VERSION` file reads `2.1.0`, `.purlin/config.json` reads `{"gate": "signed",}`, with a trailing comma, and the command is run with no argument; it exits 1, prints only `.purlin/config.json cannot be read: <the JSON reader's own message> at line 1. Fix the file by hand; nothing ran and nothing was saved.`, and no `.purlin/evidence/package` folder exists`` (57 words)
- PROOF-37 (RULE-19): ``A package is exported, then `.purlin/config.json` is made to read `{"gate": "signed",}`, with a trailing comma, and the package is checked with `--check`; it exits 1 and prints only `.purlin/config.json cannot be read: <the JSON reader's own message> at line 1. Fix the file by hand; nothing ran and nothing was saved.` `` (52 words)

Docstring exit paragraph of `scripts/export/package.py` (printed by `--help`):
`Exit codes: 0 written, or the check matched; 1 the check did not match, the project states no version, the package could not be written, or the settings file cannot be read; 2 the command line was wrong.`

The test's JSON message is taken from the running Python's own reader, since its words differ
between Python versions ("Illegal trailing comma before end of object" on 3.14).

#### Left as it stands, and why

- RULE-3 not split: PROOF-3 shows both the key order and `commit` reading the sha of `HEAD`, so
  one proof shows two claims (C11).
- RULE-5 not split: PROOF-24, a tag case, also shows `state` `finished` with `left` empty, the
  first claim.
- RULE-9 not split: PROOF-17's expected line includes the sha256 worked out as the fingerprint's
  definition, so it shows the definition and the check together.
- RULE-2, RULE-4, RULE-7: each rule's proofs are cases of one claim.
- PROOF-18 stays under RULE-6 though it also reads the rule's one result (the RULE-11 claim), as
  the brief says.
- Proofs moved without a change in words were not measured against the 60-word limit, since
  they were not rewritten.
- `references/formats/package_format.md` says nothing about the unreadable settings file: the
  file format is unchanged and no contract gives words for it.

#### Calls left

None beyond the items above.

#### Review: What was checked, and what was found

1. **Items of the brief, against the contracts.** All five items are built.
   - Item 1: RULE-6 is split into RULE-6, 11, 12, 13, 14 and 15, with the proofs the brief names.
   - Item 2: `> Format-Version: 4`. The `to_correct` and `to_measure` rows match C5 character
     for character and sit where C2 puts them. The sentence above the table is plan section 12
     item 4, word for word (wrapped).
   - Item 3: RULE-1, 8 and 10 are split by C11's test.
   - Item 4: nothing to build. `build()` copies every payload warning into `warnings`, and
     `summary_lines` prints them.
   - Item 5: `main` calls `config_engine.config_problem(root)` after `--help` and the
     bad-command-line exit, and before `--check` or any other read or write. It prints the C3.4
     sentence on stdout, writes nothing and exits 1. The docstring's exit paragraph carries C6's
     `package.py` row, all four clauses.
2. **Ownership.** Four files changed: `scripts/export/package.py`, `specs/export/package.md`,
   `dev/test_export.py` and `references/formats/package_format.md`. The brief owns all four. No
   generated file is committed, and the diff adds no `@env`.
3. **Proofs, by script.**
   - The spec has 19 rules and 37 proofs; on `main` it had 10 and 35.
   - No proof is over 60 words. The longest are PROOF-5 at 59, then PROOF-36 and PROOF-17 at 57.
     This covers the moved proofs, which the lane had not measured.
   - Each proof has exactly one `purlin: package PROOF-<n>` marker, directly above a test of its
     own, all in `dev/test_export.py`. Every marker names a proof the spec has.
   - No id is reused. The history (`git log -p --follow`) peaks at RULE-10 and PROOF-35, so the
     new ids RULE-11 to 19 and PROOF-36 and 37 are the next free.
   - No proof describes the test's mechanics.
4. **Deliberate breaks.** Each ran with a PATH that holds no `claude`. `dev/test_export.py`
   reaches no model and no git host. Each break was restored with
   `git checkout -- scripts/export/package.py`.
   - The stop disabled (`problem = None`): PROOF-36 and PROOF-37 fail.
   - The `--check` branch moved above the stop: PROOF-37 fails.
   - The stop moved to after the package is written: PROOF-36 fails (the package folder exists)
     and PROOF-37 fails.
5. **Clean release.** Nothing is retired in this lane. No test checks that a removed thing is
   absent, no reader handles an old spelling, and nothing was added to `dev/test_vocabulary.py`.
6. **Writing style.** The new rules, proofs, docstring, test comments and commit bodies are plain
   and declarative, with no emoji. The lane changed no skill, reference prose or agent file, so
   no `dev/` path or line ceiling is involved.
7. **Format reference.** Package format 3 to 4 is in a29672b4c. C5 needs no code change for the
   new kinds, so the commit holds the format file alone.

#### Review: Observations left as they stand (no contract makes the call)

- PROOF-27 (RULE-13) also reads a signature time in UTC ending in `Z`, which is RULE-17's claim.
  It moved under RULE-13 as the brief places it, like PROOF-18 under RULE-6.
- RULE-4 is not split: PROOF-4 and PROOF-6 each show both of its claims, the lines of `Left to
  do` and `state` `not finished`.
- The body of a29672b4c says the rows follow "the order summary.KINDS gives them". On this
  branch `summary.KINDS` does not have the two kinds yet (lane `core` adds them), and C2 gives
  the order. The commit message is left as written: rewriting history would change a sha that
  has already been reported.
- The test helper `export()` joins stdout and stderr, so no test pins the sentence to stdout.
  The contracts say only "prints it", so the helper is left as is.

### Lane `upstream`

#### Spec: specs/anchor/upstream.md

- Highest RULE-28, highest PROOF-45. The highest ids ever before were RULE-23 and PROOF-37; the file
  was never rewritten whole.
- Rules: 17 before, 20 after. Proofs: 31 before, 34 after.
- New rules: RULE-24 (`add` refuses a non-spec source, three proofs: PROOF-40 a text file, PROOF-41
  words, PROOF-42 a repository file with no rule). RULE-25 (sync reports an anchor from plain text
  as `error`, three proofs: PROOF-43 `sync --check`, PROOF-44 `sync refunds`, PROOF-45 `sync` with
  no name, with two repository anchors and one from a text file).
- New proofs under existing rules: PROOF-38 (RULE-15), PROOF-39 (RULE-11).

##### Splits

- `upstream RULE-9 -> RULE-9 (sync --check exits 0 when every pin is current), RULE-26 (exits 1 when a pin is behind), RULE-27 (exits 2 when a named anchor does not exist or a source cannot be read)`
- `upstream RULE-10 -> RULE-10 (--json prints one object carrying checked, behind and anchors), RULE-28 (without --json, each anchor behind gets a line naming it and the sync that fixes it)`

##### Proofs re-pointed (text and markers unchanged)

- PROOF-30: RULE-9 -> RULE-26
- PROOF-31: RULE-9 -> RULE-27
- PROOF-32: RULE-9 -> RULE-27
- PROOF-34: RULE-10 -> RULE-28

##### Proofs deleted

- PROOF-7, PROOF-24, PROOF-28, PROOF-29 (with RULE-7)
- PROOF-14 (with RULE-14)

No proof moved to another spec.

#### Calls left

- RULE-11's text does not state the no-carriage-return claim that PROOF-39 shows. The brief says
  only "one new proof under RULE-11", so the rule text is unchanged.
- The `path` in `add`'s result is the `--path` after `\` is turned to `/`. The contract says only
  `<path or null>`. The "what" in the refusal is the `--path` as given, per C13.
- A checkout left by a successful `add`, or by a RULE-5 refusal (path not in the source), stays under
  `.purlin/runtime/anchors/` as before. C13 asks for removal only in the no-rule case. The Windows
  list's RULE-1 draft for wave W ("no downloaded folder is left") needs more work.
- The contracts' C13 cites "upstream RULE-9" for exit 2. After the split, that claim is RULE-27.
- `phase3-windows-list.md` row RULE-9 (test `test_check_exits_2_when_the_source_is_gone`) is now
  RULE-27. Integration updates it.
- `.purlin/evidence/local/upstream.json` names deleted tests. It is a generated file, not staged;
  integration rebuilds it.

#### Words I chose

In the spec, which QA reads:

- The Description clause: `and an anchor's source is a spec in Purlin's format kept in a git repository.`
- RULE-9: `` `sync --check` exits 0 when every pin is current ``
- RULE-10: `` `--json` prints the whole answer as one JSON object carrying `checked`, `behind` and `anchors`, one row per anchor ``
- RULE-24: `` `add` refuses a source that is not a spec in Purlin's format kept in a git repository, whether a file on disk, a description in words or a file in a repository holding no rule: it prints `<name>: not added. <what> is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create <name> to write its rules in this project.`, writes nothing and exits 2 ``
- RULE-25: `` `sync --check`, `sync <name>` and `sync` with no name report an anchor whose `> Source:` names no repository as `error` with the line `<name>: its source, <source>, is not a spec in Purlin's format kept in a git repository, so it cannot be checked. Run purlin:spec <name> to take out its > Source: and > Pinned: lines and keep it as this project's own anchor.`, start no process for it, write nothing and exit 2 ``
- RULE-26: `` `sync --check` exits 1 when a pin is behind ``
- RULE-27: `` `sync --check` exits 2 when a named anchor does not exist or a source cannot be read ``
- RULE-28: `` Without `--json`, each anchor behind gets a line naming it and the `purlin:anchor sync <name>` that fixes it ``
- PROOF-38: `` Two anchors are pinned from the same repository and a new version is published, so both are behind; `sync` with no name returns two rows reading `synced`, and exactly one `git clone` it starts names that repository ``
- PROOF-39: `` A new version of `no_eval` is published with every line ending in a carriage return and a line feed, and `sync no_eval` runs; the copy carries the new pin, and its bytes hold no carriage return ``
- PROOF-40: `` `policy.txt`, a text file in the project, is added as the anchor `refunds`; it exits 2 and prints `refunds: not added. policy.txt is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`, starts no process, and creates no `specs/_anchors/` ``
- PROOF-41: `` The words `Every refund is countersigned` are given as the source of the anchor `refunds`; it exits 2 and prints `refunds: not added. The description given is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`, starts no process, and creates no `specs/_anchors/` ``
- PROOF-42: `` The anchor `refunds` is added from `docs/refunds.md` in another repository, a file holding prose and no rule; it exits 2 and prints `refunds: not added. docs/refunds.md is not a spec in Purlin's format kept in a git repository. Run purlin:anchor create refunds to write its rules in this project.`, `specs/_anchors/` is not created, and `.purlin/runtime/anchors/` holds no file ``
- PROOF-43: `` The anchor `refunds` carries `> Source: policy.txt`, a file in the project; `sync --check` exits 2 and prints the one line the rule names, with `refunds` as the name and `policy.txt` as the source, starts no process, and changes no file ``
- PROOF-44: `` The anchor `refunds` carries `> Source: Every refund is countersigned`, a description in words; `sync refunds` exits 2, its row reads `error` with `not_a_spec` true and the reason naming `Every refund is countersigned` and `purlin:spec refunds`, no process is started, and the copy is unchanged byte for byte ``
- PROOF-45: `` Two anchors are pinned from one repository, a third, `refunds`, carries `> Source: policy.txt`, a file in the project, and a new version is published; `sync` with no name exits 2, the two pinned anchors read `synced`, `refunds` reads `error`, no process it starts names `policy.txt`, and the copy of `refunds` is unchanged ``

In `upstream.py`, which developers read:

- The module docstring: `The file is a spec in Purlin's format kept in a git repository: `add` refuses a file on disk, a description in words or a file that holds no rule, and writes nothing.`
- The module docstring: `sync names the rules that changed and advances the pin, fetching each distinct source once per run. --check changes nothing and exits 1 when a pin is behind, 2 when a source could not be read or names no repository.`
- The docstrings of `fetch_source`, `_is_file` and `_write`.

No printed line was chosen by me: every printed line is the contract's, or unchanged.

#### Review: Found and fixed (commit 9fb1da98a)

- upstream RULE-21 held two claims, each shown by one proof, and was not split (C11):
  `--help names add and sync` (PROOF-21) and `a call with no arguments exits 2 naming
  --project-root` (PROOF-37). Split: RULE-21 keeps the first; the second takes RULE-29;
  PROOF-37 is re-pointed to RULE-29, its text and marker unchanged.
- `compose_copy` kept a branch taking a single note string, used only by the retired free-text
  note; it now takes the list of notes alone.

#### Review: Left, and why

- RULE-6 (a source beginning with `-`, or naming `ext::`, is refused) lists two refused inputs
  of one claim, and PROOF-27 shows the allowed direction, so the proofs do not fall into groups
  each showing exactly one claim; not split.
- PROOF-43 names its expected line as "the one line the rule names" rather than spelling it out:
  the line alone is about 45 words and the proof would pass 60; the test compares the whole line.
- `references/formats/anchor_format.md` "Fields 0.9.5 wrote" describes an older release's
  fields; it predates this lane, is the upgrade's exception, and no brief item names it.
- `scripts/mcp/purlin/drift.py` line 138's comment calling a Windows path free text is lane
  drift's (C13 names it there).
- The Windows list's RULE-1 draft asks that no downloaded folder be left; a successful add
  still leaves its checkout under `.purlin/runtime/anchors/` (wave W).

### Lane `dashboard`

#### Spec maxima and counts

`specs/dashboard/purlin_report.md`: highest RULE-56 and PROOF-181. Rules 48 before and 48 after; proofs 159 before and 160 after.

#### Words chosen

- RULE-4: `The page carries no shadow and no gradient`
- RULE-13, added: ``, `the version to tag` is `To tag` and `1 test comment to correct` is `To correct`, and each`` (in place of `` and `the version to tag` is `To tag`, and each``)
- RULE-14, last sentence: ``` `To tag` counts the version and `To correct` the test comments, neither counts a rule, and so choosing either leaves every rule showing ```
- PROOF-4: ``After a build, the page outside its token block holds no `box-shadow`, and the whole page holds no `gradient` ``
- PROOF-146: ``Open the team sample with login's test strength removed, and its login `RULE-2`; its `Audit` panel's first two lines read `Strong. It found nothing.` and `Read by example-model-1 on 2026-09-12 09:14 UTC` ``
- PROOF-181 (RULE-14): ``Open the board with the regulated sample after its lines of what is left are replaced by `1 test comment to correct`, and choose `To correct`, carrying 1; all 4 spec rows still show, and the line under the buttons reads `Type purlin:build in Claude Code.` ``
- Code comment in `filters.js`: "The kinds of work that count no rule, the version to tag and the test comments to correct: choosing one names the command and leaves every rule showing, because no rule carries it."
- The variable keeps its name `VERSION_KINDS`, although it now also holds `to_correct`.

#### Calls left

- PROOF-181 sits under RULE-14, but it also reads the command line that RULE-53 governs and the button name that RULE-13 governs. The brief asks for one proof, so I added no second proof under RULE-13.
- At 390 px a proof's test line wraps at the space around ` :: `. This was already the case, is not covered by a rule's proof, and I left it as it is.

#### Review: Fixed
- 7469d3030 `spec(purlin_report): RULE-14's last sentence, two clauses joined by a semicolon`. RULE-14 now ends: ``` `To tag` counts the version and `To correct` the test comments; neither counts a rule, so choosing either leaves every rule showing ```

#### Review: Left, and why
- The variable is still named `VERSION_KINDS`, though it now also holds `to_correct`, which is not the version. The brief names the variable ("`to_correct` joins `VERSION_KINDS`"), so I did not rename it. The comment above it names both kinds.
- The 390 px wrap at ` :: ` in a test line is the break `testLines` in `rule.js` is written to allow: its comment says a narrow line may break after a `::` "rather than inside either". The file and the test name each stay whole, so no value breaks inside itself.

### Lane `instructions`

#### Splits

- purlin_version RULE-2 -> RULE-2 (the package reads `VERSION` and the server reports that value: PROOF-2, 16, 18), RULE-11 (with no `VERSION` file both read `0.0.0`: PROOF-17)
- purlin_version RULE-7 -> RULE-7 (the bump script is the one command that sets a new number: PROOF-37), RULE-12 (`<semver>` writes `VERSION` and every derived location: PROOF-7, 32), RULE-13 (refuses a non-semver argument before writing: PROOF-31), RULE-14 (`--check` exits non-zero naming each disagreeing location while reporting the matching ones: PROOF-28, 29, 30, 33)
- purlin_version RULE-8 -> RULE-8 (the drift criteria row names `VERSION` and restates no number: PROOF-8), RULE-15 (no second copy of the row under `skills/` or `references/`: PROOF-34)

New ids follow C11. purlin_version was last written whole at `6e6c4227d`, and its highest ids
since then were RULE-10 and PROOF-36, so new rules start at RULE-11 and the new proof is PROOF-37.
purlin_agent needed no new id; its highest ever is RULE-8 and PROOF-46.

#### Spec maxima and counts

| Spec | Highest RULE | Highest PROOF | Rules before -> after | Proofs before -> after |
|---|---|---|---|---|
| purlin_agent | RULE-8 | PROOF-46 (the highest left in the file is PROOF-38) | 8 -> 8 | 43 -> 9 |
| purlin_version | RULE-15 | PROOF-37 | 8 -> 13 | 31 -> 25 |
| purlin_output | RULE-1 | PROOF-1 | 0 -> 1 | 0 -> 1 |

#### Words chosen (no decision or contract gave them)

- `agents/purlin.md`: "runs once the person confirms them". Only "confirms it" became "confirms
  them", because the sentence now suggests several commands.
- `specs/instructions/purlin_output.md` Description: "The one check of what Purlin prints. Every
  line a person reads from Purlin, in the terminal, the dashboard or a file setup writes, comes
  from a file under `scripts/` or `templates/`, so no emoji and no pictograph in those files means
  none in what Purlin prints."
- purlin_version rule texts for the split claims, taken from the old rule and each given its own
  subject:
  - RULE-11: "With no `VERSION` file, the `purlin` package and its server both read `0.0.0`"
  - RULE-12: "`dev/bump_version.sh <semver>` writes the `VERSION` file and sets the version field in every derived location"
  - RULE-13: "`dev/bump_version.sh` refuses an argument that is not semver before writing anything"
  - RULE-14: "`dev/bump_version.sh --check` exits non-zero naming each location that disagrees while still reporting the ones that match"
  - RULE-15: "No second copy of the config `version` row lives anywhere under `skills/` or `references/`"
- purlin_version PROOF-37: "Every value Purlin's shipped scripts give a `version` field, in a script
  that writes the settings file or the plugin manifest, is read; each is read from the `VERSION`
  file or holds no value, and none is a number written into the script"
- purlin_agent PROOF-5, reworded: "The agent definition carries the sentence "Call `sync_status`
  before you answer any question about state.", and the paragraph holding it names ``` `passed`,
  `strong` and `signed` ``` and says ``` `out of date` means the spec, the code or the tests moved
  since the run ```"
- purlin_agent RULE-4 opens "The agent definition's routing table gives ...". The other seven
  rules open "The agent definition ...".
- `dev/bump_version.sh` header: "this script is the only thing that sets a new number: setup and the
  upgrade copy it from VERSION into a project's settings."

#### Calls left

- Adding `scripts/init/update.py` to purlin_version's `> Scope:` is my call. PROOF-37 reads update.py,
  and the rule names it as a writer. No wider `scripts/**` entry was added.
- PROOF-37's scan finds a version writer only in a module that names `config.json` or
  `plugin.json`. That keeps the evidence package's `version`, the project's own release name in
  `scripts/export/package.py`, out of the check. A writer that builds the file name without either
  literal would not be seen.
- purlin_agent PROOF-38 stays as a boundary under C11's "a boundary holds" clause. PROOF-39, the
  136-line copy, is treated as a broken copy and moved into PROOF-6's test.

#### Review: What was fixed, commit `d53638cd2`

- `dev/test_purlin_output.py` contained a check mark (U+2705), a warning sign (U+26A0) and a heart
  with U+FE0F as literal characters. The writing style allows no emoji in a test, so they are now
  written as `\u` escapes. The comment above them said "a bare variation selector" although the
  case is a heart followed by one, and it now says so.
- The purlin_output Description said every line a person reads from Purlin in the terminal comes
  from `scripts/` or `templates/`. That is not true: the skills and the agent definition also give
  the agent lines to print. It now reads: "The one check of what Purlin prints. The files under
  `scripts/` print Purlin's terminal lines and build its dashboard, and setup writes a project's
  files from `templates/`, so no emoji and no pictograph in those two folders means none in what
  they print or write."

#### Review: What was left, and why

- purlin_agent PROOF-39, the 136-line copy, stays out of the spec, inside PROOF-6's test. The
  reviewer reads C11 as the lane does: a copy the check reports is a broken copy, while PROOF-38
  (135 lines, not reported) is the boundary that holds.
- PROOF-6's test asserts its broken copy through `on_copy` with an exact match rather than through
  `refusals()`. It is stricter than `refusals()` and shows the same thing, so it was not changed.
- PROOF-37 finds a writer through two text heuristics. A module counts as a writer only when it
  names `config.json` or `plugin.json`. A value counts as read from the file when its text names
  `VERSION` or it calls a function of the same module that names `'VERSION'`. This is left as the
  lane reported it.
- The purlin_version Description still says the other locations are "written from it by
  `dev/bump_version.sh`". Setup and the upgrade also copy `VERSION` into a project's settings, but
  the Description's "reads it at run time" covers that, and no decision asks for a change.

### Lane `skills-run`

#### Specs

| Spec | Highest RULE | Highest PROOF | Rules before -> after | Proofs before -> after |
|---|---|---|---|---|
| skill_test | RULE-16 | PROOF-44 | 7 -> 16 | 43 -> 21 |
| skill_audit | RULE-15 | PROOF-50 | 7 -> 15 | 49 -> 20 |

New ids start past the highest each file held since it was last written whole (skill_test 7b81a9b88: RULE-7, PROOF-44; skill_audit a18768ceb: RULE-7, PROOF-49).

#### Splits

- skill_test RULE-1 -> RULE-1 (frontmatter), RULE-16 (command reference row)
- skill_test RULE-2 -> RULE-2 (runs the script with `--test`), RULE-8 (the exit-code line), RULE-9 (a test run cannot make an audit or a signature appear)
- skill_test RULE-5 -> RULE-5 (the two files), RULE-10 (`--commit`, its two commits in order, `Evidence committed.` / `Evidence unchanged.`), RULE-11 (never pushes), RULE-12 (ends on the summary and `Left to do`, whose first line is the next step)
- skill_test RULE-6 -> RULE-6 (the four reasons and the marked test files), RULE-13 (`purlin:test --all`), RULE-14 (the line when nothing is selected)
- skill_test RULE-7 -> RULE-7 (the suggested setting), RULE-15 (no test tool found)
- skill_audit RULE-1 -> RULE-1 (frontmatter), RULE-11 (command reference row)
- skill_audit RULE-2 -> RULE-2 (runs the script with `--audit`), RULE-12 (the remote runner's arm nobody runs by hand)
- skill_audit RULE-5 -> RULE-5 (both sources count at every gate), RULE-13 (both folders named)
- skill_audit RULE-6 -> RULE-6 (what each gate runs, evidence at `signed`), RULE-8 (the audit's line, the ending, the `--commit` subject), RULE-9 (an audit cannot make a signature appear)
- skill_audit RULE-7 -> RULE-7 (the local file), RULE-14 (what a file keeps), RULE-15 (`--remote` belongs to `purlin:test`)

Proofs re-pointed (text unchanged): skill_test PROOF-19 -> RULE-16, 27 -> 8, 28 -> 9, 32 and 33 -> 10, 34 -> 11, 35 and 36 -> 12, 6 -> 13, 40 -> 14, 44 -> 15. skill_audit PROOF-17 -> 11, 26 -> 12, 33 -> 13, 11 and 12 -> 8, 39 -> 9, 44 -> 14, 45 -> 15. Reworded: skill_test PROOF-12 (the new row). Added: skill_audit PROOF-50. Markers unchanged.

#### Words chosen

- Test skill Step 2 row, second cell: "Show the person each suggested command, with the line after it that says what the tool needs added first, such as jest's `jest-junit`, and ask once. On yes, write that array as the `tests` setting with the `purlin_config` tool, then run Step 1 again"
- Test skill Step 5: "the run prints one line per system," and "a rule reads `partial` where two systems that each ran disagree."
- Audit skill Step 1: "`--arm-timeout <seconds>` when the person gave it."
- Audit skill Step 2: "what the strong cell reads when nothing was measured is in `references/hard_gates.md`, under the gate table, and `rules to measure: purlin:audit` is a line an audit clears."
- Audit skill Step 2: "is noted: the audit reader prints each note after the findings, starting `Note:`, with no heading, and a note does not make the rule weak."
- Audit skill gate table `strong` row: "a rule whose feature's strength is under the minimum reads `weak`".
- Rule texts of both specs (each "The skill tells the agent ..."), and skill_test PROOF-12 and skill_audit PROOF-50 as written in the specs.
- Sentences cut to hold the ceilings: test skill "The folder is the source: yours are `local`, and a remote run's, under `.purlin/evidence/ci/`, are `ci`." (the audit skill's Step 4 says it) and "`references/hard_gates.md` defines the gates." (Step 5 now points there); audit skill "The answer names the model that gave it.", and "A remote runner runs the tests, so" before `` `--remote` belongs to `purlin:test --remote` ``.

#### Calls left

- The new test skill Step 2 row for `.purlin/config.json cannot be read:` has no rule or proof of its own: item 5 names only the exit-code rule and its proof as following. Left unproven.
- Item 4's R1 form in Step 4 has no rule or proof: no skill_test rule covers Step 4's printed lines.

#### Review: Faults found and fixed (adb28c521, `fix(skill_audit): ...`)

- Audit skill Step 1 read "Add `--all` ..., `--feature <name>` ..., and `--arm-timeout <seconds>` when the person gave it. With neither, `--audit` runs the tests `purlin:test` would select". "Neither" stood over three flags. Adding `--arm-timeout` alone does not change what is selected, so the sentence said something false. The timeout now has its own sentence first, and "with neither" follows the two flags that select. The paragraph was rewrapped and the skill stays at 105 lines. The broken copy in PROOF-50's test now takes out the new sentence.
- skill_audit RULE-13 read "The skill names both evidence folders". Decision 94 and C11 ask every instruction rule to say what the skill tells the agent. It now reads "The skill tells the agent the two evidence folders, `.purlin/evidence/ci/` and `.purlin/evidence/local/`". PROOF-33 is unchanged.

Words I chose:
- "Add `--arm-timeout <seconds>` when the person gave it. Add `--all` for `purlin:audit --all` and `--feature <name>` for each feature named; with neither, `--audit` runs ..."
- "RULE-13: The skill tells the agent the two evidence folders, `.purlin/evidence/ci/` and `.purlin/evidence/local/`"

#### Review: Left, and why

- Several new sentences in the skills have no proof: Step 5's per-system line (item 6b), the two `references/hard_gates.md` pointers (item 6), the audit skill's `Note:` sentence (item 8), the strength pointer and the naming of `rules to measure: purlin:audit` (item 7), and the `sh ... scripts/purlin_python.sh` start (item 9; PROOF-2 reads only the script path and the flag). The brief asks no proof for any of these, so adding one would mean choosing a new proof.
- The test skill's `no test` word row (old line 88, which item 4 cites) is unchanged. The lane read it as already true. Giving it the C4.1 reason `no test for <PROOF-N>` would be a word the brief does not give.
- RULE-1, RULE-4 and the command-row rules (skill_test RULE-16, skill_audit RULE-11) keep describing the file, not an instruction. The lane's reading is that a frontmatter, a line count and another file's row are not something the skill tells the agent. Item 10 names "every other rule", so this is a call for the owner.

### Lane `skills-author`

#### Spec maxima (highest RULE / PROOF now)

| Spec | RULE max | PROOF max | Rules before → after | Proofs before → after |
|---|---|---|---|---|
| skill_spec | RULE-11 | PROOF-41 | 7 → 11 | 37 → 12 |
| skill_spec_from_code | RULE-11 | PROOF-145 | 8 → 10 | 32 → 11 |
| skill_build | RULE-13 | PROOF-41 | 9 → 13 | 34 → 14 |
| skill_anchor | RULE-12 | PROOF-33 | 6 → 12 | 32 → 13 |

A deleted number is never reused, so new rules and proofs number from the highest each file has ever used since it was last rewritten whole (7b81a9b88): skill_build takes new rules from RULE-10 (no new proof), skill_anchor from RULE-7 and PROOF-33, skill_spec_from_code from RULE-10 and PROOF-145, and skill_spec from RULE-8 (no new proof).

#### Splits

- skill_build RULE-5 -> RULE-5 (one commit, `feat(<name>):`, sections open with `Changeset:`, `Decisions:`, `Review:`, changeset maps every rule, as the conventions render it; PROOF-5, 37), RULE-10 (Changeset never left out; PROOF-35), RULE-11 (Decisions and Review left out when empty; PROOF-36)
- skill_build RULE-7 -> RULE-7 (look first for an existing test, else write an ordinary one; PROOF-7), RULE-12 (the marker is one comment directly above the test; PROOF-40), RULE-13 (a rule with no proof is marked with its own id; PROOF-41)
- skill_anchor RULE-1 -> RULE-1 (frontmatter; PROOF-1), RULE-8 (command reference row; PROOF-9)
- skill_anchor RULE-2 -> RULE-2 (the script started for add and sync; PROOF-2), RULE-9 (`--check` writes nothing, drift runs the same check; PROOF-16)
- skill_anchor RULE-5 -> RULE-5 (a pin is a commit; PROOF-5), RULE-10 (never edit a pinned rule in place; PROOF-27), RULE-11 (a change is a pull request against the source; PROOF-29), RULE-12 (a project-only rule goes in a separate local anchor; PROOF-31)
- skill_spec RULE-1 -> RULE-1 (frontmatter; PROOF-1), RULE-8 (command reference row; PROOF-14)
- skill_spec RULE-5 -> RULE-5 (write `> Scope:`; PROOF-5), RULE-9 (what a spec naming no files costs; PROOF-30)
- skill_spec RULE-6 -> RULE-6 (print and ask before saving; PROOF-6), RULE-10 (draft every proof against the guideline; PROOF-36)
- skill_spec RULE-7 -> RULE-7 (the skill says write each proof as one case; PROOF-7), RULE-11 (the guide's section says the same; PROOF-40)
- skill_spec_from_code RULE-1 -> RULE-1 (frontmatter; PROOF-1), RULE-11 (command reference row; PROOF-125)
- Not split, because the claims share every proof: skill_build RULE-1 (PROOF-1 shows both claims), RULE-2, RULE-6, RULE-8 and RULE-9; skill_spec RULE-2 and RULE-3; skill_spec_from_code RULE-2, 6, 7, 8 and 9.

Proofs re-pointed by the splits, with their text unchanged unless noted: build PROOF-35 and 36 (and PROOF-37, reworded); build PROOF-40 and 41; anchor PROOF-9, 16, 27, 29 and 31; spec PROOF-14, 30, 36 and 40; spec_from_code PROOF-125. PROOF-3, 5, 9, 11 and 37 of skill_build and PROOF-2 of skill_anchor are reworded.

#### Words chosen (no decision or contract gave them)

- Build skill closing outcome: `` - `Left to do` is empty, at the gate `passed` or `strong`: `Nothing left to do.` ``
- Build skill Committing: "The body has three sections, which open with `Changeset:`, `Decisions:` and `Review:`: a `RULE-N → file:line` line for every rule the build addressed; the judgment calls you made between real alternatives; and the places a developer should look hardest."
- Build skill Running them: "where no test command is set it suggests one for each test tool it recognises and writes them once the person confirms, so write no entry yourself." and "A proof tagged `@env` for another operating system is not run here: the run counts such proofs in one line per system that names `purlin:test --remote`."
- Anchor skill closing outcome label: "Anchor refused, its source not a spec:" (the brief gave the whole line; quoted here for the record).
- Guide `no test` row: "One of the rule's proofs has no test carrying its marker comment; the reason names each such proof."
- Guide `not run`, `<os>: no run yet` row: "A proof carries `@env` for an operating system that has not run the rule's tests: no current section comes from it."
- Guide `partial` row: "The rule's tests passed on one operating system and failed on another. `partial` is not met." / "Fix the code or the test for the system that failed, then run the tests there again."
- Guide new strong row: "The feature's test strength was not measured; the reason says why and names the command that fixes it. When the cell reads so is in [references/hard_gates.md](hard_gates.md), "The three steps"." / "Do what the reason names, then `purlin:audit`."
- Guide "The operating system": "Add `@env(windows)`, `@env(macos)` or `@env(linux)`, at most one per proof, where what the proof checks could differ on that operating system because of files or the operating system: a file lock the system holds, a console's default encoding, a filesystem that ignores case. Those three are the whole vocabulary. A rule that holds everywhere but could differ on Windows keeps its untagged proof and gains a second proof tagged `@env(windows)`, tied to the same test by a second marker comment; which run proves each is in [references/hard_gates.md](hard_gates.md), "Where a runner runs"."
- The text of each rule made by a split, and of each reworded rule and proof, is in the four spec files. They follow the old rule's words with "The skill tells the agent" in front.
- Refusal messages in the tests (only a developer reads these): "closing section does not end a finished project at passed and strong on Nothing left to do.", "example has no 'Changeset:' line before its mapped lines", and "add section does not carry ...".

#### Calls left

- RULE-1 (frontmatter) and RULE-4 (line ceiling) of each spec, and the rules split off for the command reference row (build RULE-1's second half, anchor RULE-8, spec RULE-8, spec_from_code RULE-11) and the guide (spec RULE-11): these say what a file holds, not what the skill tells the agent. No contract says how to phrase them, so they keep their structural wording.
- `skills/spec/SKILL.md` lines 117 to 120 still say to add `@env` "when the claim can only be proved on one operating system" and that "A proof with no `@env` is satisfied by a run on any operating system". This is the wording decision 95 and C12 replace in the guide, but C12 does not list the spec skill as a file that should point at S1, and the brief does not name it. It is left as it stands.
- The guide's `not run`, `<os>: no run yet` row keeps its "What moves it" cell ("Run `purlin:test --remote`, whose matrix covers it, or drop the `@env` tag if any operating system could show it."). Under decision 97 the runner file has no job for the system of the machine that ran setup. This cell is left as it stands.
- The one-line-over-ceiling copies (build PROOF-34, anchor PROOF-25, spec PROOF-29, spec_from_code PROOF-142) are treated as damaged copies, following the brief's counts, and kept as second assertions in PROOF-4. The exactly-at-ceiling copies are kept as boundaries.

#### Review: What was found and fixed (commit bd6036f7e)

- skill_build RULE-12 said the marker is one comment "on the line directly above" the test, but the skill says decorators may sit between marker and test. It now reads "on the line above it", as the skill does.
- The PROOF-3 check of the build skill failed when `git push` appeared anywhere in the closing section: a test that a removed thing is absent. It now asks only for the `Nothing left to do.` outcome; the broken copy that puts `→ Run: git push` back still fails it.
- PROOF-2's broken copy of the anchor skill wrote the retired `python3 ...` spelling. It now drops the interpreter lookup from the `add` line, which the check still refuses.
- The guide's not-measured row read "When the cell reads so is in [references/hard_gates.md](hard_gates.md), "The three steps"." It now reads "[references/hard_gates.md](hard_gates.md), "The three steps", says when the cell reads so."

#### Review: What was left, and why

- RULE-1 and RULE-4 of each spec and the command-reference and guide rules keep their structural wording. The brief says "every other rule" should say what the skill tells the agent, but lanes `core`, `drift`, `scaffold` and `skills-run` kept the same structural wording for these rules and `skills-sign` did not. Integration should settle one form.
- The one-line-over-ceiling copies stay folded into PROOF-4. C11 keeps "a boundary holds" proofs, and `skills-run` kept its 121-line proof. But the brief's counts ("about 20", "about 23", "about 26") only add up with these copies included, so the lane's reading stands. Integration should settle one form.
- `skills/spec/SKILL.md` lines 117 to 120 (`@env` "when the claim can only be proved on one operating system") are left as the lane reported. The same sentence stands in `docs/specs-and-anchors.md` and `docs/running-and-evidence.md`, which wait for the docs pass.
- The docstrings of `dev/test_skill_build.py` and `dev/test_skill_anchor.py` say each test also checks broken copies, but the tests of build PROOF-36 and PROOF-40 and of anchor PROOF-24 check none. Only a developer reads this, and the claim is left as it stands.
- The anchor skill keeps two blank lines before "When you are done", as on `main`.

### Lane `skills-sign`

#### Highest ids

- skill_sign: RULE-17, PROOF-45. Rules went from 10 to 17 and proofs from 43 to 20. Before this lane the highest ids ever held were RULE-10 and PROOF-43.
- skill_export: RULE-11, PROOF-33 (no new proof id was needed). Rules went from 6 to 11 and proofs from 33 to 13. Before this lane the highest ids ever held were RULE-6 and PROOF-33.

#### Splits

- skill_sign RULE-1 -> RULE-1 (the frontmatter carries the name and a one-line description; PROOF-1), RULE-11 (the command reference has a row for `purlin:sign`; PROOF-23)
- skill_sign RULE-2 -> RULE-2 (read what waits from `sync_status`; PROOF-2), RULE-12 (read what the audit found before anything is written, with `ai_audit.py` named ahead of `sign.py`; PROOF-30, PROOF-31)
- skill_sign RULE-5 -> RULE-5 (the two things that make a signature count; PROOF-5), RULE-13 (a signature counts whoever wrote it, whoever last committed, on any branch; PROOF-38)
- skill_sign RULE-8 -> RULE-8 (at `signed` the script writes the package, commits it signed and tags that commit; PROOF-8, PROOF-40), RULE-14 (below `signed` it writes no tag and no package; PROOF-41), RULE-15 (it never pushes; PROOF-42)
- skill_sign RULE-9 -> RULE-9 (the order the version is read in; PROOF-19), RULE-16 (with no version, ask and offer to write `VERSION`; PROOF-43)
- skill_export RULE-1 -> RULE-1 (the frontmatter; PROOF-1), RULE-7 (the command reference row; PROOF-14)
- skill_export RULE-2 -> RULE-2 (the command line that runs the script; PROOF-21), RULE-8 (each form of the command on a line; PROOF-2)
- skill_export RULE-3 -> RULE-3 (no claim of compliance; PROOF-3), RULE-9 (the package is evidence for review; PROOF-25)
- skill_export RULE-4 -> RULE-4 (the two states; PROOF-4), RULE-10 (a package that is not finished lists `Left to do` in `left`; PROOF-27)
- skill_export RULE-5 -> RULE-5 (the last heading names the next step; PROOF-5), RULE-11 (a `→` directive for each outcome; PROOF-29, PROOF-13, PROOF-30)

The brief named skill_sign RULE-5 and RULE-8 and each RULE-1 as candidates. The others (sign RULE-2 and RULE-9, and export RULE-2 to RULE-5) meet the test in C11, and plan section 7 item 19 applies that test to every rule. RULE-6, RULE-7 and RULE-10 of skill_sign have one proof each, so none was split.

#### Words chosen

The sign skill's Step 6 clause, which the agent reads:

```
It exits 1 when the tag was refused for a reason to fix, uncommitted work or results, no version,
a package not committed or git failing to write the tag, and 0 when the tag already exists.
```

The --note line of the sign skill's Step 4. The sentence `Add `--note "<text>"` for a hand check, so the note says what was seen.` went, and the command line now ends with `[--note "<text>"]`. This keeps the line count; the usage block still says what `--note` is for.

The wording of every rule, which follows decision 94. The rules are in `specs/skills/skill_sign.md` and `specs/skills/skill_export.md`, and these are the new ones word for word:

- skill_sign RULE-1: `skills/sign/SKILL.md` tells the agent the skill's name, `sign`, and its purpose in one non-empty line, in a frontmatter block at its top
- skill_sign RULE-2: The skill tells the agent to read what waits for a person from `sync_status`, as each rule's `left`, `to_test_by_hand` or `to_sign`
- skill_sign RULE-4: The skill gives the agent its instructions in at most 185 lines, the whole of `skills/sign/SKILL.md`
- skill_sign RULE-11: The table of commands in `references/purlin_commands.md` tells the agent that `purlin:sign` exists, in a row carrying its purpose
- skill_sign RULE-14: The skill tells the agent that below the gate `signed` the script writes no tag and no evidence package
- skill_sign RULE-15: The skill tells the agent that it never pushes
- skill_sign RULE-17: The skill tells the agent that the script exits 1 when the tag was refused for a reason to fix, uncommitted work or results, no version, a package not committed or git failing to write the tag, and 0 when the tag already exists
- skill_sign PROOF-44: The sign skill's closing table gives the outcome `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.` the line `→ Run: purlin:status <feature>`
- skill_sign PROOF-45: The sign skill's section on the tag says the script exits 1 when the tag was refused for a reason to fix, naming uncommitted work or results, no version, a package not committed and git failing to write the tag, and 0 when the tag already exists
- skill_export RULE-2: The skill tells the agent the command line that runs `scripts/export/package.py` through `scripts/purlin_python.sh`
- skill_export RULE-5: The last section of the skill tells the agent the next step, under a heading with the words `next step`
- skill_export RULE-11: The last section of the skill tells the agent a `→` directive for each outcome of an export: evidence not committed, no version, `not finished`, `finished` and a `--check` mismatch
- skill_export PROOF-21: A line of the export skill begins with `sh "${CLAUDE_PLUGIN_ROOT}/scripts/purlin_python.sh"` followed by `"${CLAUDE_PLUGIN_ROOT}/scripts/export/package.py"`

#### Calls left

- The sign skill's closing table has no row for `No tag: git could not write signed/<version>: ...` (C3.6, OQ16), nor for `No tag: the evidence package was not committed: ...`. The brief asks only for the Q11 clause and the unknown-rule row, so I left both as they are.
- skill_sign has no proof that its script lines start through `scripts/purlin_python.sh`, because the brief names such a proof only for skill_export (PROOF-21). The lines are changed. PROOF-31 still reads the two plugin paths.
- The line-ceiling copies (skill_sign PROOF-36 and PROOF-37, skill_export PROOF-32 and PROOF-33) left the spec, as the brief's table does for skill_sign. C11 says a proof that a boundary holds is not a damaged copy and stays. I read that exemption as covering the bump script's inputs. A padded copy of the skill is a damaged copy of the file the spec covers, so I folded the export ones too, for the same reason as the sign ones.
- skill_export PROOF-11 (the finished row loses its `→`) removes words from both PROOF-13's sentence and PROOF-30's. Its check is the directive check, so I folded it into PROOF-30. PROOF-9 (every `→` taken out) is reported through the shared closing check, which contains PROOF-30's check, so it went to PROOF-30 as well.

#### Review: What was found

1. Brief items 1 to 8 are all built. Each damaged copy named in the brief's table is inside the test of the proof it guards, and the same holds for all 20 of skill_export's copies. L6 is word for word. The C3.6 row is word for word with `→ Run: purlin:status <feature>`. The Q11 clause matches the brief. The five script lines match C9. PROOF-21 matches the brief.
2. The branch changes six files, all owned by the brief. It commits no generated file and adds no `@env` or `@manual` tag.
3. A script counted every proof: all are at or under 60 words, the longest being skill_sign PROOF-5 at 54. Each proof has exactly one marker, directly above its own `def test_`, and every marker names a proof its spec has. No id is duplicated. The new ids (skill_sign RULE-11 to 17 and PROOF-44 and 45, skill_export RULE-7 to 11) sit above every id the specs have held in `git log -p --follow`; RULE-11 appears in that history only inside a commit message. No proof describes a test's mechanics.
4. I broke four things on purpose. The tests read text only, start no program, and ran with a PATH holding no `claude`. Each test failed, and each file was restored with `git checkout -- <file>`:
   - the unknown-rule row removed from the sign skill: `test_an_unknown_rule_is_sent_to_the_status` failed;
   - the export mismatch row put back to `→ Export the package again at its tag: purlin:export`: `test_each_stop_short_names_the_next_step` failed;
   - the export script lines put back to `python3 ...`: `test_a_line_runs_the_export_script` failed;
   - the exit clause changed to `and 1 when the tag already exists`: `test_it_says_what_a_refused_tag_exits_with` failed.
5. Clean release holds. No test checks that a removed thing is absent, and nothing describes an earlier state. The old mismatch line appears only in `dev/plans/phase2-report.md`, which is history.
6. Writing style holds. No prose names a path into `dev/` or `specs/`. The sign skill is 174 of 185 lines and the export skill 83 of 90.
7. No format reference is concerned.
8. One fault: after the splits, the helper section headings in both test files still named only the old rules (for example `# RULE-8 and RULE-9: the section on the tag` sat over checks now proving RULE-14 to RULE-17).

#### Review: What was fixed

- 594f32dde `test(skill_sign): the helper headings name the rules the splits made`. The headings now read, for example, `# RULE-8, RULE-9 and RULE-14 to RULE-17: the section on the tag` and `# RULE-5 and RULE-11: the closing section`. No check changes.

#### Review: What was left, and why

- PROOF-44 reads "gives the outcome `...` the line `→ Run: purlin:status <feature>`". I kept it: the same "gives X the line Y" form is used by skill_export PROOF-29 and PROOF-13.
- skill_sign RULE-12 still holds "read what the audit found before writing" (PROOF-30) and "ai_audit.py named ahead of sign.py" (PROOF-31). I read these as one claim, reading before writing, so C11 does not require a split.
- The lane's calls left stand as it wrote them. The two missing closing rows in the sign skill (C3.6's git-failure line, and the package not committed) are not asked for by the brief. There is no proof that the sign skill's script lines start through `scripts/purlin_python.sh`: I checked that reverting them to `python3` passes every test, so the gap is real. The line-ceiling copies were folded into PROOF-4 and PROOF-6.

### Lane `words`

#### Specs

I own no spec. There are no RULE or PROOF maxima, no splits, and no proofs deleted, moved or re-pointed.

#### Calls left

- `docs/how-purlin-works.md` 102: the sentence that starts on line 102 and runs to 105 ("The tag run reruns the tests on a clean machine, checks that every signature still binds ... and ends with the gate check") is still untrue after decisions 75 and 83. I fixed only the runner clause on line 102, because lines 103-105 are not in my list.
- Other `docs/` lines that are stale but not in my list, left for decision 63's reading:
  - `running-and-evidence.md`: 55-76 and 94-100 (the old run ending and gate line); 127 (level); 143-150 (stale signatures, level); 197-201 (the exit table's "or the gate is not met"); 266-269 ("stale"); 284 ("when every rule meets it").
  - `dashboard.md`: 68 (the `Signed` cell's level and `stale`).
  - `how-purlin-works.md`: 95-97 (trust, "one Linux job").
  - `getting-started.md`: 178 (`[level: passed]`) and 181.
  - `raising-the-gate-and-upgrading.md`: 29-33 ("two reasons", `--dry-run`), 40-49 (trust, level, queue), 61-62 (the `--dry-run` row), 67-69 (trust, `ubuntu-latest`).
  - `specs-and-anchors.md`: 85-89 (the `[level: ...]` tag table) and "stales its signature" in the sync paragraph.
- The contract gives the S1 wording "A person's own machine, Mac or Windows". I kept it as written, although a Linux machine behaves the same way.

#### Found, not changed (item 6)

- `README.md`: nothing that decisions 94-97 made untrue. It does carry lines that earlier decisions made untrue:
  - 23-24 "or you do not trust this machine" (decision 75)
  - 65-77, the old run ending and `meet the gate` lines (decisions 60, 68 and 79)
  - 95-96 "once every rule meets it" (decision 75)
  - 97-98 `[level: passed]` (decision 73)
  - 111 "Walk the queue" (decision 74). This cell also differs from the purpose sentence in `purlin_commands.md`.
- `references/writing_style.md`: nothing untrue. Its "No emoji." line stays (C10).

#### Words I chose (every sentence a person reads that no contract fixed)

hard_gates.md:
- "**Test strength is one share per feature**, in every language: the share of the feature's breaks its tests caught, and every rule of the feature is judged on it. With mutation testing on, a feature whose share could not be measured leaves its rules `weak` with the reason `strength not measured: <reason>`, and the reason names the command that fixes it. An engine that cannot run on this system counts as none, and the AI audit alone decides."
- "**Which machine proves which proof.** A remote runner runs only the tests tied to proofs tagged `@env` for its own system. A person's own machine, Mac or Windows, proves every proof with no `@env` and every proof tagged for its own system, and never one tagged for another. A runner file names a remote machine only for a system some proof is tagged for that the machine running setup is not."
- Gate table, passed row: "Every test tied to the rule ran and passed, each current section answering for the proofs it lists."
- "`to_correct` counts test comments, not rules, and is carried by the project."
- `to_correct` row cell: "at every gate, a comment above a test names nothing a spec has, or names a rule that has proofs; each such comment counts once"
- `to_measure` row cell: "with mutation testing on, the strong cell reads `weak` only because its feature's strength could not be measured"
- "A count of 1 reads `1 rule to fix`, `1 rule to tie to its files`, `1 test comment to correct`, and so on."
- "The breaks a person measured are the breaks a runner would measure."
- Tag run cell: "Nothing. On a clean machine it runs the tests a remote runner runs, as the paragraph above says, and nothing else"
- "A run on a ref that is neither a `run/*` branch nor a `signed/*` tag prints `...`" (the line itself is C3.8's)
- "A runner runs the tests "Where a runner runs, and when a project has one" names and, on a run branch, writes its section of the evidence."
- Platforms: "Each section of the evidence names the system it ran on, and answers only for the proofs it lists: a proof a section does not list is neither passed, failed nor `not run` there." / "Where two systems that each have a current section disagree the cell reads `partial`" / "A system a proof is tagged `@env` for with no current section makes the cell read `not run`, with the reason `<os>: no run yet`. Test strength does not depend on the system: the paragraph under the gate table says how it is measured."
- "`purlin:init --gate <gate>` changes the gate later. Raising it adds what is missing."

glossary.md:
- "the first test run suggests an entry for each test tool it recognises, and they are written together once a person confirms them."
- "a rule's tests passed on one system and failed on another. It is not met. A system that has not run reads `not run`."
- "**test strength**: the share of one feature's breaks the tests caught, as a percentage, compared with `min_strength`. `references/hard_gates.md`, under the gate table, says how it reaches a rule."
- "What it runs is in `references/hard_gates.md`, "Where a runner runs"."
- Chain passed row: "..., and every test tied to it ran and passed, each current section answering for the proofs it lists"

purlin_commands.md:
- `purlin:test` row: "...suggests one for each test tool it recognises and runs once you confirm it."
- End of the `purlin:test` Writes row: "; what the runner runs is in `references/hard_gates.md`, "Where a runner runs""
- "`No test command is set in .purlin/config.json, so nothing ran.`, when it recognises a test tool, then for each tool it recognises `Suggested for <name>: <run>` followed by what that tool needs added where it needs something, then `Suggested tests setting: <the entries as one JSON array on one line>`."
- "..., where some of the rule's proofs have no test." / "..., where none of them has one."
- "`purlin:sign` and `scripts/review/ai_audit.py --rule` name a rule no spec has, last, above the summary: `...`"
- "Where the nearest id is a rule with exactly one proof, the fix names that proof; a rule with two or more proofs gives no near miss."
- "Every Purlin script a skill runs is started as `sh ...`, which finds Python 3 the way the plugin's server does, `py -3` on Windows included."

CLAUDE.md:
- "3. Run `purlin:sign` at the gate `signed`. It writes the signed tag `signed/<version>` once nothing is left to do." / "4. The owner pushes the tag: `git push origin signed/<version>`."

docs:
- running-and-evidence, 102-113:
  - "A proof tagged `@env(windows)`, `@env(macos)` or `@env(linux)` is proven only by a run on that operating system; hard_gates.md says which machine proves which proof, the untagged ones included. On your machine the run counts the proofs tagged for another system in one line per system, rather than a pass or a failure, and their rules' passed cells read `not run`, with the reason `<os>: no run yet`:"
  - The example line: `3 proofs need Windows; this machine is macOS. Run purlin:test --remote.`
  - "A proof tagged for another system with no test tied to it is not counted in that line: its rule's line names it as a proof with no test. ... Each section answers only for the proofs it lists. The cell reads `partial` when two systems that each have a current section disagree, and `partial` is not met."
- running-and-evidence, 228-235:
  - "Such a rule shows no strength, and it meets the strong cell when the audit found nothing: the cell's reason reads `no mutation score measured`."
  - "Test strength is one share per feature, whatever the engine, so every rule of a feature carries the same number. hard_gates.md says what a rule reads when its feature's share could not be measured. An engine that runs past `--arm-timeout`, 3600 seconds by default, for one feature measures nothing for it, and the run prints `purlin: the engine timed out after 3600 s, ...`."
- running-and-evidence, "When a project has a runner": the whole section, rewritten. It is in commit 8ff0554a9. Sentences I wrote:
  - "`purlin:init` writes a CI workflow for one reason: ..."
  - "Which machine proves which proof, and which systems the runner file names, is in hard_gates.md."
  - "With no such proof, init prints `...`, and at the gate `passed` the same line with `every test` in place of `every proof`."
  - The mermaid node "each job of the git host's runner runs the tests of the proofs tagged for its system".
  - Table cells: "Runs the tests tied to the proofs tagged for the job's system" / "its own section of each such feature's ..." / "Reruns the same tests on a clean machine".
  - "A `ci` section lists only the proofs tagged for the runner's system and the rules they prove, and names its machine `remote runner, <system>`, with the name the host lent the runner kept beside it as `hostname`."
  - "The test step is the last step: it ends on the summary and `Left to do`, and its exit code is the job's. The job fails only when one of the tests it runs fails or could not run; a rule not yet audited or signed never fails it."
  - "The matrix carries one job per operating system the `@env` tags in `specs/` name that the machine running setup is not."
  - "Use it for the reason above."
- dashboard 13: "run `purlin:init` again and it replaces the copy."
- dashboard 67: "`2 of 4 · 86%`: how many of the spec's rules reached `strong`, then the test strength where one was measured; `0 of 26` alone where none was" | "...; the percentage's own hover reads `Test strength: ...`"
- how-purlin-works 102: "The runner runs the tests hard_gates.md names, and no audit."
- how-purlin-works 160-162: "..., each section answering for the proofs it lists, and it reads `partial` when two systems that each have a current section disagree. A system a proof is tagged for with no current section makes it read `not run`. `partial` is not met, and the rule is left to do as `to fix`. Test strength does not depend on the system: hard_gates.md says how it is measured."
- getting-started 177: "`purlin:init --gate strong` raises the gate and writes what the new gate needs; it changes no rule."
- raising-the-gate 24: "init writes what is missing and touches nothing else."
- specs-and-anchors 91-94: "A rule number written twice is warned of, as `login: RULE-2 is written twice; the second is read. Run purlin:spec login.`" (the new-id sentence is section 12 item 5's)
- specs-and-anchors 140-144: "Which run proves a proof with no `@env`, and which systems a remote runner's matrix names, is in hard_gates.md."

RELEASE_NOTES.md: every sentence of the rewritten section is mine except section 12 item 11 and the lines quoted from the contracts. It is in commit 27fc64578, in full. New sentences:
- The steps: "each rule goes through up to three steps", "Every rule is asked what the gate asks."
- The summary and `Left to do` bullet.
- Two commits on `--commit`.
- "A result counts wherever it ran and records the machine it ran on."
- The notes bullet under the audit.
- The "Test strength, one share per feature." bullet.
- The "Signatures." bullet.
- "`purlin:sign` exits 1 when it refused the tag for a reason to fix: work or results not committed, no version, a package not committed, or git could not write the tag."
- The package's counts and state.
- The "A remote runner for one reason" bullet.
- "A mistake in a spec is warned of, with its fix." bullet.
- Suggestions for every test tool, and `py -3`.
- `@manual` at any gate.
- Setup's two questions and the unreadable-settings line.
- The interpreter-lookup bullet.
- "### Windows: The parts are proven on Windows and the whole path on the Mac. The whole path on Windows, from setup to a signed tag, is not walked for 0.10.0."
- "The shell command line that printed the settings, `python3 scripts/mcp/config_engine.py`."
- The upgrade's intro, config, workflows and ending steps, and the paragraph after them.
- The words table's summary cell.

#### Review: Found and fixed (commit b5dbe150b)

1. hard_gates.md, `Left to do`: rules take "the first that applies, in this order", and
   `to_strengthen` (row 10) read only "the strong cell reads `weak`", so a rule weak because its
   spec names no code files fell under `to_strengthen`, where C2 counts it under `no_scope`.
   The cell now reads: "the strong cell reads `weak`, and not because its spec names no code files".
2. hard_gates.md, the tag run's cell pointed at "the paragraph above", which is the trigger
   paragraph, not S1. Now: "Nothing. On a clean machine it runs the tests a remote runner runs
   (\"Which machine proves which proof\", above), and nothing else".
3. hard_gates.md, "CI writes no signature file": "A runner runs the tests \"Where a runner runs,
   and when a project has one\" names and, ..." read as a garbled sentence. Now: "A runner runs
   the tests named under \"Which machine proves which proof\", above, and, on a run branch,
   writes its section of the evidence."
4. hard_gates.md and docs/running-and-evidence.md: "The job fails only when a test fails or
   could not run" / "one of the tests it runs" is untrue under OQ21 (a mixed file runs whole and
   only the tagged tests count). Both now: "The job fails only when a test whose result it
   records fails or could not run".
5. docs/running-and-evidence.md restated S1's third clause ("one job per operating system the
   `@env` tags in `specs/` name that the machine running setup is not"), against C12. Now: "The
   matrix carries one job per operating system that [hard_gates.md](...#where-a-runner-runs-and-when-a-project-has-one) names."
6. purlin_commands.md put "last, above the summary" on `ai_audit.py --rule` too, which prints
   no summary (C3.6 says it of signing). Now: "`purlin:sign`, last and above the summary, and
   `scripts/review/ai_audit.py --rule` name a rule no spec has: `...`".
7. RELEASE_NOTES.md: "A proof longer than the standard" is not an exact number. Now "A proof
   longer than 60 words".
8. docs/how-purlin-works.md: the lane's reflow left one 111-character line; reflowed, no word
   changed.

#### Review: Left, and why

- The glossary lists `to correct` as a printed kind although the line reads `test comments to
  correct`; the brief gives `to correct` word for word, so it stands.
- hard_gates.md keeps "The breaks a person measured are the breaks a runner would measure."
  (main's second clause; a runner measures no breaks). No decision or brief item names it.
- More stale docs lines outside the brief's list, from earlier decisions, beyond those the lane
  named, for decision 63's reading: review-and-signing 6-55 (the queue, `[level: ...]`),
  how-purlin-works 30, 33, 51, 129, 140, 152 (queue, level), getting-started 20 and 43 (trust),
  dashboard 198 and 210 (queue), raising-the-gate-and-upgrading 64 (`--dry-run`, which no
  script reads), 134, 158-167 (trust), docs/index.md 39 and docs/regulated-workflow.md 56 and
  163 (not owned by any lane in this phase).
- The one-line (unwrapped) sentences of section 12 items 3, 10 and 11 stay on one line each,
  so a grep for the whole sentence finds them.

## Words chosen for the owner to read

Plan section 12, copied as it stands:

Reference prose that describes behaviour a decision or reading settles is not an owner question:
the owner reads every page in the docs pass (decision 63). These sentences were chosen by the
planning agent; each lane writes its sentence exactly as below, and integration copies this
section into `phase3-interfaces.md` (section 9, step 7) so the owner reads them there. A mark
`(OQ<n>)` names the answer a sentence carries. Items 6 and 7 are printed lines that follow from
decision 97 (call 75); sanity check 3 reads them with every other message.

1. `references/purlin_commands.md`, "Exit codes", the whole table (lane `words`; contracts C6,
   whose notes give each cell's source; OQ1 and OQ16):

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
   cell (lane `words`; OQ10):

   ```
   at `signed`, the rule is not signed and its spec names no files; at `strong` and `signed` with mutation testing on, its strong cell reads `weak` because its spec names no code files
   ```

3. `references/hard_gates.md`, lines 128 to 129, in place of the sentence that begins "A project
   whose git host is neither GitHub nor Azure DevOps" (lane `words`; decision 96):

   ```
   Purlin runs tests remotely on GitHub and Azure DevOps. On any other git host the settings read `ci: none`, and setup prints `This git host cannot run tests remotely. Everything on this machine works.`
   ```

4. `references/formats/package_format.md`, "What is left", the sentence above the table of
   kinds (lane `package`; OQ3):

   ```
   Each rule is counted under one kind, the first that applies, and a kind at zero has no line. `to_correct` counts test comments, not rules, and is carried by the project:
   ```

5. `references/formats/spec_format.md`, "Rules format", one sentence added (P2; Q46, Q48, C11):

   ```
   A new id is one more than the highest the file has held since it was last written whole; a number deleted since then is never used again.
   ```

6. Setup's note under a written runner file (lane `scaffold`; C14), in place of
   `  the matrix is <images>, the systems the @env tags in specs/ name.`:

   ```
     the matrix is <images>, the systems the @env tags in specs/ name that this machine is not.
   ```

7. The upgrade's question before it writes a runner file (lane `update`; C14), in place of
   `Write <path>, one job per operating system your specs name?`:

   ```
   Write <path>, one job per operating system your specs name that this machine is not?
   ```

8. `references/formats/anchor_format.md`, "The source: a git URL plus a path", after its first
   paragraph (lane `upstream`; C13):

   ```
   The file at the path is a spec in this format that holds at least one rule. `purlin:anchor add` refuses any other source, a file on disk, a description in words or a file with no rule, and writes nothing. A copy whose `> Source:` names no repository reads `error` in `purlin:drift` and in `purlin:anchor sync --check`. A local anchor carries no `> Source:` and is never checked.
   ```

9. `skills/anchor/SKILL.md`, the `add` section, in place of the paragraph that begins "When the
   source file is free text" (lane `skills-author`; C13):

   ```
   The file is a spec in Purlin's format that holds at least one rule, kept in a git repository. Any other source, a text file, a description in words or a file with no rule, is refused and nothing is written; the refusal names `purlin:anchor create <name>`, which writes the rules in this project instead.
   ```

10. `docs/specs-and-anchors.md`, "An anchor repo", after the `add` paragraph's code block (lane
    `words`; C13):

    ```
    The file is a spec in Purlin's format that holds at least one rule. `add` refuses any other source, a text file, a description in words or a file with no rule, and writes nothing.
    ```

11. `RELEASE_NOTES.md`, "Unreleased — 0.10.0", one line under what changed (lane `words`; C13):

    ```
    - An anchor is copied only from a spec in Purlin's format kept in a git repository. `purlin:anchor add` refuses a text file, a description in words or a file with no rule, and `purlin:drift` and `purlin:anchor sync --check` report an anchor made from plain text as `error`.
    ```

## Wave W

Integration of wave W, 2026-09-29. The 14 marking lanes were each rebased onto `main`, their own
test files rerun and merged by fast-forward in the order settings, anchors, core, drift, run,
host, mutation, reports, scaffold, update, signing, review, package, upstream. None conflicted,
none failed its tests and none was left out. `main` went from `070c8a942` to `9c9cf4e30` with 18
lane commits, then `267d42f5f` (the evidence) and `d8fa97dcf` (the runner file).

No row was left for integration: the one row a lane could not mark in a file it did not own,
update PROOF-31 `@env(macos)`, which lane scaffold named, was marked by lane update.

### Proofs marked, by spec: 86 tagged `@env(windows)`

Each is one past the highest id its spec has held (`git log -p --follow`), worded as the list's
draft unless named under "Wording that differs from the list", and tied by a second
`purlin: <feature> PROOF-<n>` comment to the test the list's row names.

| Lane | Spec | Rule: new proof |
|---|---|---|
| `settings` | `config_engine` | RULE-1: PROOF-36, RULE-2: PROOF-37, RULE-8: PROOF-38, RULE-10: PROOF-39, RULE-13: PROOF-40 |
| `settings` | `server` | RULE-5: PROOF-159, RULE-6: PROOF-160, RULE-22: PROOF-161 |
| `anchors` | `evidence` | RULE-1: PROOF-71, RULE-24: PROOF-72, RULE-7: PROOF-73, RULE-8: PROOF-74, RULE-27: PROOF-75 |
| `anchors` | `specs` | RULE-11: PROOF-42, RULE-20: PROOF-43 |
| `core` | `states` | RULE-28: PROOF-215, RULE-32: PROOF-216, RULE-47: PROOF-217, RULE-90: PROOF-218 |
| `drift` | `drift` | RULE-17: PROOF-60 |
| `run` | `evidence_writer` | RULE-1: PROOF-80, RULE-4: PROOF-81, RULE-7: PROOF-82, RULE-16: PROOF-83 |
| `run` | `run_script` | RULE-4: PROOF-225, RULE-10: PROOF-226, RULE-12: PROOF-227, RULE-21: PROOF-228, RULE-39: PROOF-229, RULE-40: PROOF-230, RULE-43: PROOF-231, RULE-55: PROOF-232, RULE-58: PROOF-233, RULE-63: PROOF-234 |
| `host` | `host` | RULE-5: PROOF-116, RULE-12: PROOF-117, RULE-24: PROOF-118, RULE-27: PROOF-119, RULE-31: PROOF-120 |
| `mutation` | `mutation` | RULE-5: PROOF-86, RULE-7: PROOF-87, RULE-30: PROOF-88, RULE-14: PROOF-89, RULE-32: PROOF-90, RULE-22: PROOF-91 |
| `reports` | `reports` | RULE-3: PROOF-99, RULE-10: PROOF-100, RULE-15: PROOF-101, RULE-16: PROOF-102, RULE-17: PROOF-103, RULE-21: PROOF-104 |
| `scaffold` | `scaffold` | RULE-13: PROOF-129, RULE-19: PROOF-130, RULE-20: PROOF-131, RULE-21: PROOF-132, RULE-22: PROOF-133, RULE-23: PROOF-134, RULE-60: PROOF-135, RULE-47: PROOF-136 |
| `update` | `update` | RULE-5: PROOF-117, RULE-7: PROOF-118, RULE-34: PROOF-119, RULE-35: PROOF-120, RULE-18: PROOF-121, RULE-28: PROOF-122, RULE-29: PROOF-123, RULE-13: PROOF-124, RULE-23: PROOF-125, RULE-24: PROOF-126 |
| `signing` | `signatures` | RULE-17: PROOF-153, RULE-18: PROOF-154, RULE-20: PROOF-155, RULE-45: PROOF-156, RULE-50: PROOF-157, RULE-60: PROOF-158 |
| `review` | `ai_audit` | RULE-3: PROOF-82, RULE-19: PROOF-83 |
| `package` | `package` | RULE-1: PROOF-38, RULE-8: PROOF-39, RULE-9: PROOF-40 |
| `upstream` | `upstream` | RULE-1: PROOF-46, RULE-3: PROOF-47, RULE-8: PROOF-48, RULE-27: PROOF-49, RULE-11: PROOF-50, RULE-22: PROOF-51 |

### The 13 proofs tagged `@env(macos)`

Their tests and comments did not change. All 13 pass on this Mac.

- `scaffold` RULE-36: PROOF-36, 90, 91, 92, 93, 117, 118, 119 (lane `scaffold`).
- `scaffold` RULE-37: PROOF-37, 94, 95, 96 (lane `scaffold`).
- `update` RULE-31: PROOF-31 (lane `update`).

### Wording that differs from the list

- `config_engine` PROOF-38: `its lines ending with no carriage return` in place of the draft's
  `with no carriage return`.
- `config_engine` PROOF-39: `stops with the system's error and leaves the file reading exactly`
  in place of the draft's `leaves it reading exactly`.
- `update` PROOF-124: the draft's `every other line of that spec is byte for byte as it was`
  became `every line of that spec that does not end with an `@` tag is byte for byte as it was,
  line endings included`, since the same run also rewrites lines ending `@e2e`, `@integration`
  and `PROOF-54`'s `@windows`.
- `upstream` PROOF-46: the draft's `no downloaded folder is left in the temporary folder` became
  `no downloaded file is left under `.purlin/runtime/anchors/``, where `add` downloads.
- `scaffold` PROOF-129 quotes the printed line as the code prints it, `A test is tagged @env for
  macos, ...`, where the draft said `macOS`.
- `scaffold` PROOF-133 also sets `.purlin/report-data.js` aside, as its test does.

### Tests changed or added for Windows

New tests, each skipped off Windows except the last:

- `dev/test_config_engine.py::TestAtomicWrite::test_on_windows_a_move_onto_a_file_held_open_leaves_it_whole`
  (PROOF-39): a second Python process holds the settings file open during the write.
- `dev/test_evidence_reader.py::test_on_windows_the_reader_names_its_own_machine_windows`
  (PROOF-75), skip reason `only a Windows machine can show its own name`.
- `dev/test_run_script.py::test_this_windows_machine_reads_windows` (PROOF-228).
- `dev/test_backing_tests.py::TestTheEvidenceNamesTheTests::test_a_checkout_with_windows_line_endings_keeps_the_hash`
  (PROOF-218), not skipped: `core.autocrlf true` writes `\r\n` on a Mac too, so it runs here.

Changed:

- `settings`: the settings file and the server's output are compared as bytes; `_child` reads
  the server's output as UTF-8; the manifest test says `sh is not on the search path` when no
  `sh` is found.
- `anchors`: the fingerprint is taken under `core.autocrlf false` and `true` and `code` compared;
  the fixture's `write` writes line feeds alone; on Windows the unreadable spec is locked by a
  child process through `msvcrt.locking`, `chmod` elsewhere.
- `core`: the data file's ending is read as bytes; the signature commit is dated
  `2026-09-20T17:30:00+05:00` and the cell must read `2026-09-20T12:30:00Z`.
- `drift`: the repository is made with `core.autocrlf true`, the specs written with CRLF, and
  their mtime moved 5 s forward.
- `run`: fixture files and shell scripts are written as bytes; the RULE-4 test swaps `windows`
  and `linux` by system; `_other_os` gives `macos` on Windows; the cp1252 test uses the real
  default character set on Windows.
- `host`: paths are joined by the system's separator; `gh.cmd` and `az.cmd` are asserted to be
  what was found on Windows; `GITHUB_WORKSPACE` is written with `os.path.normpath`.
- `mutation`: PROOF-90's test asks the real system on Windows; PROOF-87's checks the project's
  own `stryker.cmd` is chosen; PROOF-91's checks the run ends within 30 s.
- `reports`: the Jest report is given the system's separator; the exit suite's scripts are
  written with bare line feeds.
- `scaffold`: the starting `.gitignore` carries `\r\n` on Windows and is compared as bytes; the
  plugin's path is looked for spelled with `\`, `/` and JSON-doubled `\\`; `\dev\` and a
  relative `dev\` are looked for; the `gh.cmd` stand-in is written as bytes.
- `update`: `_read_bytes` and `_write_bytes`; the conftest is written with `os.linesep`; the old
  test files are written as bytes; the rewritten shell script is run with
  `purlin_run.bash_command()`; spec lines are compared as bytes, each with its own ending.
- `signing`: `owner_only(private_key)` runs `icacls <key> /inheritance:r /grant:r <USERNAME>:F`
  on Windows; PROOF-158's key path is written with `\`.
- `review`: the call test sets `PYTHONUTF8=1`, and on Windows asserts the stand-in found is
  `claude.cmd`.
- `package`: the clone is made with `-c core.autocrlf=true` and the file compared to the tag's
  blob as bytes; the command's output is read as UTF-8.
- `upstream`: `.purlin/runtime/anchors/` is asserted empty after `add`; the synced copy is read
  as bytes.

### Product changes

- `scripts/mcp/config_engine.py`: `update_config` writes with `newline='\n'`.
- `scripts/mcp/purlin/server.py`: `main()` sets `sys.stdout.reconfigure(newline='\n')`.
- `scripts/mcp/purlin/payload.py`: `write_report_data` writes with `newline='\n'`.
- `scripts/run/evidence.py`: the evidence file, `.purlin/tests.md` and the could-not-run file are
  written with `newline='\n'`.
- `scripts/run/mutation/__init__.py`: at the time limit on Windows, `taskkill /F /T /PID` stops
  the engine and what it started before `process.kill()`. No row's Needs named it.
- `scripts/init/scaffold.py`: `write_evidence` writes the evidence README from the shipped bytes.
- `scripts/anchor/upstream.py`: `add` removes its download under `.purlin/runtime/anchors/` on
  every way out.

### Acceptance on this Mac

`bash dev/run_tests.sh`: `1978 passed, 3 skipped in 571.60s`, `Suites: 5 passed, 0 failed`. The
three skips are the three Windows-only tests.

`python3 scripts/run/purlin_run.py --test --all --commit` exited 0 and printed:

```
Markers: 2026 tied to a test, 0 not tied.
Ran pytest, shell on 35 features.

86 proofs need Windows; this machine is macOS. Run purlin:test --remote.

752 rules. 666 pass their tests. 0 are strong. 0 are signed.
Left to do:
  86 rules to test on Windows: purlin:test --remote
  666 rules to audit: purlin:audit
```

Every rule's passed cell reads `passed` but 86, which read `not run` with the one reason
`windows: no run yet`; none reads `partial`, `failed` or `no test`.

### The runner file

`sh scripts/purlin_python.sh scripts/init/scaffold.py --project-root . --yes` wrote
`.github/workflows/purlin.yml`, the template with `os: [windows-latest]` and the ref `v0.10.0`,
and printed `  the matrix is windows-latest, the systems the @env tags in specs/ name that this
machine is not.` Checked against a GitHub `windows-latest` runner: each step names
`shell: bash`, which GitHub starts as Git's bash there; `python3` comes from
`actions/setup-python`; `requirements.txt` installs pytest and playwright; the test step runs
`purlin_run.py --all --ci`, which runs only the tests tied to proofs tagged for the runner's
system; `.gitattributes` keeps every checkout at LF. No step fails for a reason seen by reading,
so the template and the code that renders it did not change. `sqlite3` is not known to be on
the image; call 50 leaves the template as it is until the first run shows it.

### Likely to fail on Windows

- `server` PROOF-161: Git's `sh` running `"$PURLIN_PYTHON"` given a `C:\...\python.exe` path, on
  a script path mixing `\` and `/`.
- `config_engine` PROOF-39: the test asserts only that an `OSError` is raised by the move.
- `specs` PROOF-43: that an `msvcrt.locking` lock held by another process makes the scanner's
  read raise `OSError`.
- `evidence` PROOF-71, `states` PROOF-218, `update` PROOF-117 and 121, `drift` PROOF-60,
  `run_script` PROOF-232, `package` PROOF-39: how git treats line endings under the runner's
  `core.autocrlf`.
- `states` PROOF-217: whether Git for Windows honours `TZ=UTC` for `format-local` dates (a UTC
  runner cannot show it).
- `signatures` PROOF-154 to 157, `states` PROOF-217, `package` PROOF-39: which `ssh-keygen` makes
  the key and which signs, and whether the key's permissions are accepted.
- `run_script` PROOF-225: skips, and so reads not run, if `sqlite3` is not on the image.
- `run_script` PROOF-229: a runner in UTF-8 mode would pass without showing the cp1252 case.
- `run_script` PROOF-230, `ai_audit` PROOF-83, `mutation` PROOF-91: stopping a program at its
  limit stops `bash` or `cmd.exe` and may wait for what it started.
- `reports` PROOF-100 to 103: the Jest spelling is built, not captured; quoting through
  `list2cmdline` to Git's `bash.exe`; `usr/bin` on the search path of a non-login bash.
- `scaffold` PROOF-133, 135 and the GitHub remote read from a temp path holding `github`.
- `host` PROOF-119: `os.path.realpath` turning `RUNNER~1` into the long form on both sides.
- `package` PROOF-38: a temporary worktree left behind if Windows holds a file open.
- `upstream` PROOF-46: download paths near 260 characters; `shutil.rmtree(onerror=)`.
- `ai_audit`: on Python 3.12.0 alone, `shutil.which('claude')` may find the stand-in with no
  ending.
- The run's length: the files tied to Windows proofs take about 12 minutes on this Mac, and the
  job is capped at 90.

### Calls left

- `scripts/run/workflow.py` `FOREIGN_OS_REASON` and `FOREIGN_OS_REASON_AT_PASSED` print the
  stored word, `macos` or `windows`, where `references/writing_style.md` asks for `macOS` and
  `Windows`.
- `templates/purlin.yml` and `templates/purlin.azure-pipelines.yml` still say `The matrix holds
  one job for each operating system the @env tags in specs/ name, and no other.`, which C14 made
  false (the machine running setup is left out). The runner file committed here carries it.
- Stopping a whole process tree at a time limit on Windows (`run_script` RULE-40, `ai_audit`
  RULE-19, `host` RULE-38); mutation alone does it.
- `signatures.commit_date` reads `--date=format-local` under `TZ=UTC`; `--format=%at` formatted
  in Python would not depend on Git for Windows.
- `states` PROOF-218 sits under RULE-90, whose words begin `Where no section is current`; its
  claim is RULE-35's.
- The server reads its input in the console's code page on Windows.
- `upstream` `sync` still leaves its downloads under `.purlin/runtime/anchors/`.
- `package`: clearing the read-only bit and retrying the temporary worktree's removal.
- `dev/fake_claude.py` counts calls with `fcntl`, which Windows lacks (PROOF-62's test).
- `drift._specs_uncommitted` strips the first path's leading character.
- `run_script` PROOF-126's test expects `python3 -m pytest` and fails on Windows, where it is
  not counted.
- The nine other `update` Windows proofs say `sample 0.9.5 project` where the older ones say
  `sample v0.9.5 project`.
- With `--commit` the run prints two blank lines between the `need Windows` line and `Evidence
  written`; without it, one.
- Setup on this repository prints `kept .gitignore` twice and the line `dotnet: Stryker
  measures the breaks. Without it test strength is not measured.`
