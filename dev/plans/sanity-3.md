# Sanity check 3: the docs against the rules, and starting from existing code

Run on 2026-09-29 against `main` at `f17c92d39` (decision 64). This repository was not
changed: `git status` was clean before and after, and this file is the one file written in it.
Nothing was committed, pushed, tagged, audited or signed.

Fourteen fresh agents, each in its own scratch folder under the session scratchpad,
`sanity3/<lane>/`:

- Four read the docs page by page against the code and the rules: the start pages (`README.md`,
  `docs/index.md`, `docs/getting-started.md`, `docs/how-purlin-works.md`), running
  (`docs/running-and-evidence.md`, `docs/dashboard.md`), signing
  (`docs/review-and-signing.md`, `docs/regulated-workflow.md`,
  `docs/raising-the-gate-and-upgrading.md`) and specs (`docs/specs-and-anchors.md`,
  `docs/spec-from-code.md`, `docs/working-together.md`, `docs/team-workflow.md`). Each ran what
  it doubted in a scratch project.
- One read every message the product prints, in `scripts/` and `templates/`, against the
  writing style, the decisions and the rules.
- Nine ran `purlin:spec-from-code` for real: three projects, each at the gates `passed`,
  `strong` and `signed`, from setup through the first test run. The agents followed the skills
  by hand and ran the scripts; the real `claude` program was not started, and no model call was
  made.

Every finding below that a lane reported was checked against the repository where it was in
doubt. What this report leaves out is listed, with the reason, in section 10.

## 1. The summary

The docs do not describe the product as it is now. Of 660 statements read on 13 pages, 184 are
false, and nearly all of them describe the product before decisions 60 to 97: a level marked on
each rule, a queue of work for a person, a signature that goes `stale`, a sentence counting the
rules that `meet the gate`, a question about trusting your machine, and a `--dry-run`. Every
sample of printed output on the start pages is wrong. A reader who follows the ten-minute path
exactly reaches step 4 and gets `nothing ran` and exit 1, because the page skips the step where
the first test run suggests a test command and you confirm it. Decision 63 already schedules
the read of every page; this check is the list that read works from.

Starting from existing code works. On all 9 runs at least 7 in 10 rules passed on the first
run: between 88.7% and 97.2%. Every source file got a rule or was listed. What it gets wrong:

- On all 9 runs, before the first test run, `purlin:status` told the agent to write a test for
  every rule, when the tests were already there and marked. An agent that follows it, as the
  agent definition says to, writes the project's tests a second time.
- On all 9 runs, setup and the status sent a project with code to `purlin:spec` or back to
  `purlin:init`, never to `purlin:spec-from-code`.
- The test command suggested for jest fails on every run that names its files, so after the
  first run a JavaScript project cannot run one feature.
- No run met the quality guide in full. Most misses come from the guide itself: it has no
  answer for a library, whose function names and error types are what a caller sees, or for a
  test that checks several inputs in one table.
- The three Python runs left tests untied with no reason the skill allows: 77 docstring
  examples cannot carry a comment at all.
- None of the three projects had a failing test, so the rule that a failing test stays failing
  was not tried.

Counts: 1303 statements and messages checked; 184 false statements in the docs; 4 more that
break a decision; 67 true statements no rule covers; 45 messages that break the style or a
decision; 21 product faults; 19 places the instructions failed the agent; 15 questions.

## 2. The three projects, and the measures of decisions 66 and 81

The projects, copied into each scratch folder at a release tag:

- **Python**: `toolz`, 16 source files, 263 test items (186 test functions and parametrised
  cases, plus 77 docstring examples).
- **JavaScript**: `deep-object-diff`, 9 source files, 120 test declarations that run as 238
  jest cases.
- **C#**: `GuardClauses`, 15 source files, 400 test methods that run as 957 cases.

The three measures: most rules already pass (at least 7 in 10 on the first run); the rules and
proofs meet the quality guide; every source file belongs to a feature, and every existing test
is tied or listed with one of the three reasons of decision 81.

| Project | Gate | Specs | Rules | Pass on the first run | 7 in 10 | Rules / proofs against the guide | Source files | Existing tests tied |
|---|---|---|---|---|---|---|---|---|
| Python | `passed` | 14 | 186 | 179 (96.2%) | met | 22 of 186 rules; 34 of 266 proofs | 15 of 16, 1 listed | 133 of 156 functions; 19 with a reason, 4 and the 77 examples without |
| Python | `strong` | 11 | 183 | 177 (96.7%) | met | 7 of 183 rules; 21 of 204 proofs | 16 of 16 | 162 of 263; 22 with a reason, 2 and the 77 examples without |
| Python | `signed` | 13 | 176 | 171 (97.2%) | met | 23 of 176 rules; 12 of 299 proofs | 16 of 16 | 180 of 263; 2 with a reason, 4 and the 77 examples without; 13 benchmark files not counted |
| JavaScript | `passed` | 8 | 68 | 64 (94.1%) | met | 6 join two claims, 15 describe unexported modules; 5 of 123 proofs | 9 of 9 | 211 of 238 cases; 27 with a reason |
| JavaScript | `strong` | 8 | 64 | 62 (96.9%) | met | 15 describe unexported modules; 12 of 117 proofs | 9 of 9 | 110 of 120 declarations; 10 with a reason |
| JavaScript | `signed` | 8 | 53 | 50 (94.3%) | met | 1 fails, 7 borderline, 12 describe unexported modules; 8 of 116 proofs | 9 of 9 | 110 of 120 declarations; 10 with a reason |
| C# | `passed` | 19 | 97 | 86 (88.7%) | met | 0 fail, 5 borderline; 81 of 223 proofs (69 hold several cases) | 14 of 15, 1 listed | 400 of 400 |
| C# | `strong` | 18 | 129 | 115 (89.1%) | met | 12 join two claims, 1 borderline; 65 of 184 proofs (8 hold two cases, 48 one action over a list of inputs) | 13 of 15, 2 listed | 400 of 400 |
| C# | `signed` | 18 | 125 | 119 (95.2%) | met | 11 join two claims; 107 of 224 proofs (75 hold several cases, 32 end on "passes with no error") | 13 of 15, 2 listed | 400 of 400 |

What the table says:

- **Most rules pass: 9 of 9 runs.** Every rule that did not pass read `no test` because no test
  in the project shows it, with two exceptions. Python `signed`: `package RULE-1` failed because
  the suggested command runs the `python3` first on the path, which lacks the installed package
  (fault 8). C# `passed` and `strong`: one rule each read `not run` where it should read
  `no test` (fault 5).
- **The quality guide: 0 of 9 runs meet it in full.** The misses the guide cannot settle are
  the same on every run: a library's function and exception names in a proof (question 5), a
  test that checks a table of inputs or one input per number type against "one proof, one
  case" (question 6), and rules for modules the package does not export (question 4). Misses
  that are the writer's own: rules joining two claims (about 70 across the runs), a few proofs
  with no exact value, a few that describe how the test works. No rule carries `[level: ...]`
  on any run, and no proof is over 60 words (the longest is 54).
- **Every file: 9 of 9 runs.** No source file was left out without being listed. The files
  listed were vendored code (`JetBrains.Annotations.cs`), an attribute with no behaviour at run
  time, a build script, benchmarks, docs configuration and `toolz/utils.py`.
- **Every test: 6 of 9 runs.** The JavaScript and C# runs tie or explain every test. The three
  Python runs leave 2 to 4 tests of test helpers and all 77 docstring examples with no reason
  the skill allows (question 3).
- **A failing test stays failing: not tried.** None of the three projects had a failing test
  before the run, and no agent ran a test before the specs were committed.
- **The counts are not comparable across the Python runs.** One agent counted test functions
  (156), the other two counted collected items (263); the JavaScript runs counted cases (238)
  on one run and declarations (120) on two.

## 3. Every false statement in the docs

Line numbers are those of `main` at `f17c92d39`. "Levels", "the queue", `stale`, "meets the
gate", the trust setting and `--dry-run` recur on almost every page; each place is listed.

### `README.md`

| Line | Says | What is true |
|---|---|---|
| 23-24 | No CI workflow unless a rule needs another operating system or you do not trust this machine | A runner file is written for one reason: a proof tagged `@env` for a system this machine is not. The trust setting does not exist (decision 75, scaffold RULE-13). |
| 63 | Run one command, `purlin:test`, and it gives the output shown | In a new project the first run runs nothing: `No test command is set in .purlin/config.json, so nothing ran.`, a suggested command, exit 1. Tests run after you confirm the suggestion (run_script RULE-61). |
| 65-73 | The run ends `3 of 3 rules meet the gate passed.`, `Untested 0 · Failing 0 · Partial 0 · Passing 3.`, `1 feature.`, `→ Next: nothing is outstanding at gate passed.`, `Tests: 3 of 3 rules pass.`, `gate passed met: 3 of 3 rules` | It ends `3 rules. 3 pass their tests.` then `Nothing left to do.` None of the six lines is printed by the product. |
| 76-77 | A failing rule is counted under `Failing`; the run ends `Tests: 2 of 3 rules pass.` and `gate passed not met: 2 of 3 rules meet it` | It prints `cart RULE-2 fails: tests/test_cart.py::test_sum. Run purlin:build cart.` and ends `3 rules. 2 pass their tests.`, `Left to do:`, `  1 rule to fix: purlin:build`. Exit 1 is right. |
| 95-97 | `purlin:sign` writes the package and the tag once every rule meets the gate | When nothing is left to do and every result came from committed work (decisions 68, 75). |
| 97-98 | A single rule can ask for less with `[level: passed]` | Marking a rule lower is gone; the tag is read as part of the rule text (decision 73). |
| 111 | `purlin:sign [feature] [RULE-N]`: "Walk the queue, or sign a rule, a feature or a batch as a signed commit" | Syntax `purlin:sign [feature] [RULE-N ...] [--all]`; purpose "Sign a rule, a feature or every rule that waits for a person, as a signed commit". The README is to carry it word for word (`references/purlin_commands.md`). |

### `docs/index.md`

| Line | Says | What is true |
|---|---|---|
| 26 | Running and evidence covers "the two reasons" a project has a remote runner | There is one reason (decision 75). |
| 39 | Review and signing covers "the level, the queue, ... what stales a signature" | None of the three exists (decisions 73, 74, 83). |
| 61 | The quality guide covers choosing a level | The guide has no such section. |
| 62 | Supported frameworks gives the test command init writes | Setup writes an empty `tests` setting; the first test run suggests the command (scaffold RULE-50). |

### `docs/getting-started.md`

| Line | Says | What is true |
|---|---|---|
| 14-15 | Init writes your test command into the `tests` setting | Setup writes `tests: []` and prints `Suites none.`; the first `purlin:test` suggests the entry and writes it once you confirm (scaffold RULE-50, RULE-37). |
| 19-20 | No CI workflow unless a rule needs another system or you say you do not trust this machine | One reason only (decision 75). |
| 42-44 | Answer `y` to `Do you trust your own machine for the tests?` | Setup asks one question at `passed`, the gate (scaffold RULE-1). |
| 44 | Init reads your test framework from the tree | Setup reads nothing about tests; the first test run does. |
| 45 | Init ends `→ Next: run purlin:spec to write the first spec.` | It ends `→ Run: purlin:spec to write the first spec.` (scaffold RULE-34). |
| 88 | It runs your test command and prints the sample | The first run runs nothing and suggests a command; no step on the page confirms it. With no `conftest.py`, `pytest.ini` or `[tool.pytest`, it prints that no test tool Purlin knows was found. |
| 92-94 | `Running the pytest suite.` followed directly by `Markers: ...` | A blank line stands between them. |
| 106-113 | The sample ends `3 of 3 rules meet the gate passed.` ... `→ Next:` ... `gate passed met: 3 of 3 rules` | `3 rules. 3 pass their tests.` then `Nothing left to do.` (summary RULE-7). |
| 116-117 | A failing rule is counted under `Failing`, ending `Tests: 2 of 3 rules pass.` and `gate passed not met ...` | As for `README.md` 76-77. |
| 149-151 | `purlin:test --commit` commits both files as `purlin: evidence at <sha7>` | It first commits changed specs, marked tests and settings as `purlin: specs, tests and settings for <feature>`, then the evidence, which names that commit (decision 80, evidence_writer RULE-19). |
| 154-155 | Every command ends with one `→ Next:` line | The line is `→ Run:`; a finished project at `passed` or `strong` ends on `Nothing left to do.` and names no command (decision 76). |
| 175 | `purlin:sign` writes the tag once every rule meets the gate `signed` | When nothing is left to do and every result came from committed work. |
| 178 | A single rule can stay lower with `[level: passed]` | Gone (decision 73). |

### `docs/how-purlin-works.md`

| Line | Says | What is true |
|---|---|---|
| 8-9 | A rule's level says how far down it must go | Every rule is asked what the gate asks (decision 73). |
| 11-26 | The diagram branches each rule by level to "meets the gate" or "short of the gate" | No per-rule levels; the phrase is used nowhere. The order test, audit, sign is right; the run ends on the summary and `Left to do`. |
| 30 | A project at `passed` never sees a strength, a queue or a signature | There is no queue; a hand check is signed at any gate, so a project at `passed` can carry a signature (signatures RULE-12). |
| 32-39 | The paragraph on `[level: ...]`, a tag above the gate read as the gate, no cell above its level | Removed (decision 73). |
| 50-52 | At `strong` and `signed`, `purlin:sign` walks the queue; at `signed` it tags when every rule meets the gate | It walks the rules waiting to be tested by hand or signed, at every gate; it tags when nothing is left and every result is committed. |
| 60 | The tag marks a version that is proven | It marks a finished version: nothing left to do, every result from committed work. |
| 62-63 | It prints `Tagged signed/<version> at <sha7>: every rule meets the gate signed.` | `Tagged signed/<version> at <sha7>.` then `Nothing left to do. Push the tag to release it: git push origin signed/<version>` (signatures RULE-70). |
| 63-64 | No tag is written while any rule falls short | Also none while the tree or any feature's results are uncommitted, and none over a tag that exists. |
| 80-81 | A signature is bound to the hashes of the rule, proof, test and audit | Also to the code the feature lists and to the machine the tests ran on for each system (decisions 62, 77). |
| 81-82 | It logs who signed, when, and on which machine | Name and email as git holds them, the time and the key's fingerprint; not the machine it was signed on. |
| 82-84 | Change any of those four and the signature reads `stale` | Six things bind it; a change ends it with no message and the signed cell reads `unsigned`; the rule is `to sign` (decision 83). |
| 94-96 | Init writes a CI workflow for two reasons, one being `trust: remote` | One reason; the settings file has seven keys and no trust key (scaffold RULE-5, RULE-13). |
| 96-97 | The matrix is one Linux job plus one per system the tags name | One job per tagged system this machine is not, and no Linux job of its own (scaffold RULE-15). |
| 104-106 | The tag run checks every signature, checks who committed `ci/`, and ends with the gate check | It runs the tests tied to proofs tagged for its system and writes nothing (run_script RULE-47). |
| 112-114 | `purlin:test` ends `Tests: <n> of <rules> rules pass.` and `gate passed met: ...` | It ends on the summary and `Left to do` or `Nothing left to do.` |
| 123-125 | The last line is `gate <gate> not met: ...`, with a `→ Next:` line above it | Neither exists; the first line of `Left to do` is the next step. |
| 125 | `purlin:test` exits 1 only when a test failed or a marker is wrong | Also when a tied test did not run, evidence is missing, the settings file is missing or unreadable, the project was set up by 0.9.5 and not upgraded, or no test command is set (`references/purlin_commands.md`, "Exit codes"). |
| 131 | At `signed` a signature fails when the rule, proof, test or audit changed | Also when the feature's code or the machine its tests ran on changes. |
| 132-133 | No tag while any rule falls short, so a version not proven has no marker | The conditions are nothing left to do and every result committed; the word is `finished`. |
| 135-140 | "What does a level do?": the audit reads rules whose level is strong or signed; a signature row sits in the queue | From `strong` up every rule is audited; at `signed` every rule needs a signature. |
| 148-149 | `not audited` means the rule's level is strong or signed and no audit has run | The gate is `strong` or above and the evidence has no audit entry for the current hashes (states RULE-15). |
| 151-152 | Both are build work, and neither is in the queue | `not audited` is `to audit`; `weak` is `to strengthen` or `to measure` (decision 97). |

### `docs/running-and-evidence.md`

| Line | Says | What is true |
|---|---|---|
| 9 | Both run on your machine, and neither pushes | `purlin:test --remote` pushes a run branch; line 297 of the same page says so. |
| 51-76 | The sample ends `3 of 3 rules meet the gate passed.` ... `gate passed met: 3 of 3 rules`, with a table without `Proofs` | The table carries `Proofs` where the spec has proofs, then `3 rules. 3 pass their tests.` and `Nothing left to do.` |
| 89-91 | `--commit` commits both files as `purlin: evidence at <sha7>` | Two commits, the work then the results (decision 80). |
| 94-98 | The run ends on `Tests: ...` and `gate <gate>: <n> of <rules>` | It ends on the summary and `Left to do`. |
| 130 | Above `passed`, a rule whose level is `passed` is not read | Levels are gone; the audit reads the same rules at every gate (ai_audit RULE-1). |
| 143-145 | `purlin:audit --commit` commits as `purlin: evidence at <sha7>`; the audit prints a strength line | The same two commits as a test run; no strength line is printed where nothing was measured (decision 93). |
| 146-147 | Prints `<n> signatures went stale: their audit findings changed.` | No such line; the rule returns to `to sign` with no message (decision 77). |
| 149-150 | The audit ends `Audit: <n> strong, <n> weak.` then the gate line; at `passed` `Nothing blocks at the gate passed.` | One earlier line `AI audit: <n> rules read, <s> strong, <w> weak.`, then the table, the summary and `Left to do` (run_script RULE-54). |
| 151-152 | Exits 1 when a rule is short where its level asks | Above `passed`, when a rule it read is weak or could not be audited (run_script RULE-48). |
| 159-168 | The diagram: select, run, tie, write evidence, audit, then print and commit | With `--commit` the work is committed first, before the evidence is written. |
| 191-196 | One line per marker, then `Remove the comment, or write the proof it names.` | One line: `tests/test_login.py:12 names login PROOF-9, which no spec has. Correct the comment, or run purlin:build to repair it.` (reports RULE-19). |
| 203 | Exit 1: a test failed, evidence is missing, a marker names nothing, or the gate is not met | A test run exits on the tests alone, whatever the gate; the row leaves out five causes (run_script RULE-11, 61, 62, 65, 66, 70). |
| 270-272 | When only the code changed, a signature stands | A change to the feature's listed code ends every signature in that feature (decisions 62, 72). |
| 273 | The signed cell reads `stale` | It reads `unsigned`; its words are `signed`, `unsigned`, `waiting`. |
| 288 | `purlin:sign` writes the package when every rule meets it | When nothing is left to do and every result is committed. |
| 380-381 | If the run branch is still on the git host at the end, the command gives the delete command | Without `gh` or `az` the branch is left and only the pull command is printed; a delete command is printed only after the Azure 90-minute wait or a failed delete (question 12). |

### `docs/dashboard.md`

| Line | Says | What is true |
|---|---|---|
| 12-13 | After a plugin update, `purlin:init` again replaces the page | It keeps it and prints `kept purlin-report.html`; `purlin:init --update` replaces it (update RULE-31). |
| 28-30 | The top bar shows `4 of 10 rules meet the gate` | Gone (decision 60). The top bar carries the age, `gate: <gate>`, the tag at `signed`, and the theme control. |
| 30-31 | The tag shows as `signed/1.4.0 · a1b2c3d` | `signed/1.4.0` alone, the commit only in its hover (decision 88). |
| 31-32 | The commit shows as `at a1b2c3d` | No such box (decision 88). |
| 32-33 | From 90 minutes on it adds `— run purlin:status to refresh` | The box reads `Data: <age>` alone; the hover says how to refresh (decision 91). |
| 35-36 | Tabs: Board, `Queue (n)`, the open rule | Board and the open rule. |
| 44-46 | A rule meets the gate when its cells meet its level | No levels; the phrase is used nowhere. |
| 40, 147 | Image descriptions: six tiles with Queue and Stale cards; Level, Spec, Last run, Signatures rows | The images show four boxes, six `To ...` buttons and no Level row. |
| 49-55 | Tiles `Untested`, `Failing`, `Partial`, `Passing`, `Strong`, `Signed`; Queue and Stale cards | Boxes `No proof` (from `strong` up), `Passing` with `<n> RULES TOTAL`, `Strong`, `Signed` (decisions 83, 87, 92). |
| 64, 71, 77, 80 | The Rules cell reads `15 (+6 shared)` | `15 (+6)`, with the hover `15 rules of its own, and 6 more it must also meet, from shared rules:` (decision 90). |
| 66 | Tests hover sample `linux · ci · ...` | The hover reads `Linux/Unix`. |
| 68 | Signed reads `1 of 4` of those whose level is signed; the hover counts `stale` | `<n> of <rules>` over every rule; no stale count. |
| 72 | The tiles, the filters and the top bar count each rule once | The top bar counts no rules. |
| 83 | The page never scrolls sideways on the board, a rule's screen and the Queue tab | There is no Queue tab. |
| 95-96 | Each rule row carries one pill per cell, reading the cell's word | One badge per step reached, `PASSED`, `STRONG`, `SIGNED`, and `FAILED` where a test fails (decision 85). |
| 102 | The signed cell's words include `stale` | They do not. |
| 104-106 | A rule has the cells its level asks for; Weak and Not audited filters | No levels, no such filters. |
| 108 | No filter counts `waiting` | A rule whose strong cell waits on a failing test is under `To fix`. |
| 125-126 | The filters compose | One button is chosen at a time; choosing it again shows every rule (purlin_report RULE-14). |
| 128-138 | The filter table: Untested, Failing, Partial, Weak, Not audited, Queue, Stale | One button per line of `Left to do`, named as the line, with its count; the chosen one reads `Type <command> in Claude Code.` |
| 138-139 | Nothing left reads `No rule matches every filter you set.` | `No rule is left of this kind.` |
| 150-153 | The rule screen has a `Level` row | No such row. |
| 157-158 | Platform boxes read `lin`, `mac`, `win` | `Lin`, `Mac`, `Win`. |
| 161 | The Audit panel shows where the rule's level is strong or signed | Wherever the gate is `strong` or `signed`. |
| 163-164 | The panel reads `no mutation score measured` where none was | It says nothing of strength (decision 93). |
| 170-172 | The hand check panel names `--note "<what you saw>"`; below `signed` a waiting rule has a panel | It names `purlin:sign <feature> <RULE-N>` and says the command asks what you saw; it shows at `signed` only. |
| 177 | The back link reads `← Queue` from the queue | It always reads `← Board`. |
| 179-198 | The whole Queue section | There is no Queue; that work is under `To test by hand` and `To sign` (decision 74). |

### `docs/review-and-signing.md`

| Line | Says | What is true |
|---|---|---|
| 6, 9, 19-51, 216 | `purlin:sign` computes one list, the queue, and walks it | The walk reads the rules left to do as `to test by hand` or `to sign` (decision 74). |
| 7-8, 118 | It writes the package and tag when every rule meets the gate | When nothing but the tag is left and every result is committed. |
| 9, 39-40 | Hand checks are cleared at `strong`; the queue exists from `strong` up | Hand checks are walked at every gate, `passed` included (checked in a scratch project). |
| 12-17, 35-36, 172-173, 193, 211 | Every rule has a level; a signature logs the level | No level tag; at `signed` every rule needs a signature; the signature has no level field. |
| 17 | Link to `../references/hard_gates.md#the-level` | No such heading: a broken link. |
| 27-29 | The walk opens on `Queue: 5 rules. 2 hand checks, 3 signatures.` | It opens on the `Left to do` lines it walks, or on `Nothing is waiting for someone to test by hand or to sign.` |
| 33-36 | Rows `hand check` / `signature`; the signed cell reads `unsigned` or `stale` | Kinds `to test by hand`, `to sign`; cell words `signed`, `unsigned`, `waiting`. |
| 42-46, 73, 200, 205-211 | A stale signature, its heading and its reasons | An ended signature reads `unsigned` with no message (decisions 77, 83). |
| 49-50 | A weak rule is build work for `purlin:build` | `to strengthen` (`purlin:build`), `to measure` (`purlin:audit`) or `to tie to its files` (`purlin:spec`). |
| 53-55 | Under `passed` it prints `sign: the gate is passed, which asks for no signature.` and writes nothing | Neither line exists; at `passed` it walks and signs hand checks. |
| 59, 63 | Stop heading `login RULE-3   level signed   signature` | `<feature> <RULE-N>   <left>`, such as `login RULE-2   to test by hand`. |
| 104-112 | Closing sample `Commits: 4f1a9c2`, `→ Run: purlin:build`, `→ Run: purlin:sign` | `Signed <n> rules as <email> with the key ending ...<4>.` before `Commits:`, then the summary ending or the tag lines; no arrow for a skip. |
| 121-123 | The version comes from `VERSION` or the config's `version` | `VERSION`, then `package.json`, then `pyproject.toml`, then the first root `*.csproj`; the config's version is Purlin's own (signatures RULE-56). |
| 128-130 | `Tagged signed/1.4.0 at a1b2c3d: every rule meets the gate signed.` then `→ Run: git push ...` | `Tagged signed/1.4.0 at a1b2c3d.` then `Nothing left to do. Push the tag to release it: git push origin signed/1.4.0` |
| 137 | `No tag: 3 of 42 rules do not meet the gate signed.` | The summary and `Left to do` (signatures RULE-46). |
| 138 | `No tag: login is out of date (code changed since a1b2c3d).` | No such line; such rules count as `to test`. |
| 139 | `sign: login has evidence that is not committed. Run: purlin:test --commit` | `No tag: login has results that are not committed. Run purlin:test --commit.` |
| 148-149 | Pushing the tag reruns the tests and checks every signature | A tag run exists only with an `@env` proof for another system; it runs those tests, writes nothing and checks no signature. |
| 155-156 | `purlin:sign --batch` | The flag is `--all`; `--batch` exits 2. |
| 163-165 | Prints `Signed <n> rules in <sha7>.`, then `→ Run: purlin:sign` | `Signed <n> rules as <email> with the key ending ...<4>.`, each rule, then the summary ending. |
| 170-171 | At `strong`, `sign: a signature is required only under the gate signed. Writing it anyway.` | No such line; a named rule is signed at every gate without comment. |
| 173-174 | At `signed`, a rule of a spec with no `> Scope:` is refused | It is signed, and the signature never counts; the status gives the reason (decision 75; question 9). |
| 174-176 | Under `trust: remote` a rule is refused | There is no trust setting. |
| 178-185 | No key: `Commit signing is not configured ...` with three commands including `commit.gpgsign true` | `No key to sign with. These commands set one up:`, then `ssh-keygen ...` (only when the file is missing), `git config gpg.format ssh`, `git config user.signingkey ~/.ssh/id_ed25519.pub`; exit 1 (signatures RULE-17). |
| 191-193 | Binds four hashes; logs the level, the machine and its system | Rule, proof, test, code, audit, and the machines the tests ran on; records email, name, key fingerprint, gate, evidence, note, time. |
| 195-199 | The commit is signed and the signature verifies, else `the signing commit is not signed` | The commit only has to carry a signature, any key; nothing is verified. The reason is `the commit that added it is not signed` (decision 77). |
| 203 | Below `signed` a committed signature counts | The same check at every gate. |
| 213-214 | Changing the code alone ends nothing | A change to the feature's listed code ends the signature (decision 62). |

### `docs/regulated-workflow.md`

| Line | Says | What is true |
|---|---|---|
| 29-31, 94-95, 102-105 | The signature records the signing machine and the level; it locks four things; a change stales it | Neither is recorded; six things; a change ends it with no message. |
| 34, 95 | The tag is written when every rule meets it; "every rule that needs one" | When nothing but the tag is left; at `signed` every rule needs a signature. |
| 36-37 | The version comes from `VERSION` or the config | As `review-and-signing.md` 121-123. |
| 39-42 | `Tagged ... : every rule meets the gate signed.` then `→ Run: git push ...` | As `review-and-signing.md` 128-130. |
| 44-45 | `No tag: 3 of 42 rules do not meet the gate signed.` | The summary and `Left to do`. |
| 50-51, 54-55, 76-78 | Below `signed` the package reads `work in progress` or `gate <gate> met`; `not_for_approval` | The state is `finished` or `not finished` at every gate; no `not_for_approval` (decision 83; package RULE-3, RULE-4). |
| 56 | The package holds the trust setting | Its settings are `gate`, `mutation_engine`, `min_strength`. |
| 57 | Each rule carries its level | No level field. |
| 60-61 | Each signature carries the signing machine and system | No signing machine; see package RULE-13 for the fields. |
| 99-101 | The commit is cryptographically signed and the signature verifies | Nothing is verified (decision 77). |
| 106-107 | A code change leaves the signature standing | It ends it. |
| 138 | The loop runs all on one machine | Not with a proof tagged `@env` for another system. |
| 144 | Diagram node "every rule meets the gate signed?" | The check is whether anything but the tag is left; the diagram leaves out uncommitted work, uncommitted results and no version. |
| 151-158 | `purlin:init --gate signed` prints the signing setup, with `commit.gpgsign true` | Setup prints no signing setup; `purlin:sign` prints it when there is no key; `commit.gpgsign` is not needed. |
| 160-161 | `purlin:sign` refuses to sign over uncommitted evidence | Signing goes ahead; only the tag is refused. |
| 161-163 | A rule of a spec with no `> Scope:` is refused at `signed` | As `review-and-signing.md` 173-174. |
| 163-164 | A `@manual` rule waits in the queue and the signer writes one line | It waits as `to test by hand`; the note is optional (decision 84). |

### `docs/raising-the-gate-and-upgrading.md`

| Line | Says | What is true |
|---|---|---|
| 30-31, 67-69 | A runner is written for two reasons, one a no to the trust question | One reason (decision 75). |
| 33-34, 64 | `--dry-run` prints every file and writes none | No such flag; exit 2 (decision 70). |
| 40-41 | The settings hold the trust answer and a detected `tests` setting; setup writes `specs/_anchors/` | No trust key; `tests: []`; the anchor folder comes with the first anchor (scaffold RULE-50, RULE-51). |
| 47-49 | At `strong` a rule whose level is strong or signed meets the gate when ...; a hand check joins the queue | No levels, no queue; hand checks wait at every gate. |
| 51-53 | At `signed`, setup prints the signing setup | It prints none. |
| 53-57 | A rule marked lower meets the gate on its lower cells | No level tags. |
| 69-70 | The matrix is `ubuntu-latest` plus one job per tagged system | One job per tagged system this machine is not; no Linux job of its own. |
| 88, 92-93 | A rule no audit has read does not meet the gate; the tag needs every rule to meet it | Such a rule is `to audit`; the tag needs nothing but the tag left. |
| 115-120 | `purlin:init --update --dry-run` as a CI preflight, exit 1 while pending | No such flag: exit 2. |
| 134, 158-168 | The migration asks the gate, mutation and trust questions | The gate, then the mutation question at `strong` or `signed` only; no trust question. |
| 151-153 | The mutation question follows where an engine exists | Also only at `strong` or `signed` (update RULE-26, RULE-38). |
| 176 | The migrated workflow ends with the gate check | The separate check is gone; the last step is the test run (decision 83). |
| 185-186 | Pass `--yes` once you have read the `--dry-run` output | The pending list prints at the start of every run. |
| 195-196 | It ends on `→ Next: run purlin:status ...` or names skipped migrations | It ends as `purlin:status` ends; a skip prints `skipped <id>`. |
| 198-199 | Exit 1 for `--dry-run` with something pending | Exit 1 means the settings file cannot be read (update RULE-40). |

### `docs/specs-and-anchors.md`

| Line | Says | What is true |
|---|---|---|
| 47 | `## Rules` and `## Proof` are read spelled exactly so | Matched without regard to case (spec_format RULE-12). |
| 53 | Every metadata line is optional | At `signed`, `> Scope:` is required. |
| 63-65 | When only the code changed, the signature stands | It ends. |
| 65 | When the text changes the signature goes stale | It ends; the rule is `to sign`. |
| 78-89 | Rule grammar with `[level: <level>]` and its table | A rule line carries no tag; bracketed text is rule text (specs RULE-3). |
| 91 | A deleted number is never used again | `purlin:spec` takes one past the highest id in the main-branch copy or the working copy, so a top number deleted from both is handed out again (question 7). |
| 118 | A proof is optional for a rule marked `[level: passed]` | Optional only at the gate `passed`. |
| 129-130 | A `@manual` proof's evidence is a signature with a one-line note | The note is optional (decision 84). |
| 196 | `sync` updates the copy and advances the pin in one commit | `sync` commits nothing; you commit it with `anchor(<name>):`. |
| 197-198 | A rule whose text moved stales its signature | The signature ends. |

### `docs/spec-from-code.md`

| Line | Says | What is true |
|---|---|---|
| 13-14 | Nothing can read the specs until the project has a settings file | `purlin:status` reads them; only a run stops. The skill says the same false thing. |
| 18-19 | A rule read off code says what the code does; a bug becomes a rule | Where a test exists the rule is written from what the test expects, passing or not (decision 81). |
| 36-37 | The report says how many rules already have a passing test | No test is run first; the report gives the counts, each proof beside its test, each untied test with its reason, and the files with no rule. |
| 41, 51-52 | Every rule carries `[level: passed]` | No level is marked (decision 73). |
| 60-61, 81 | The level is re-marked later; no level above `passed` | No levels. |
| 96-97 | Re-mark levels, and delete rules that describe a bug | Levels are gone; a rule its failing test shows to be a bug stays, and the test stays failing (decisions 66, 72). |

### `docs/working-together.md`

| Line | Says | What is true |
|---|---|---|
| 17-18 | The dashboard's rollup says how many rules meet the gate, one count per bucket | Boxes `No proof`, `Passing`, `Strong`, `Signed` (decisions 60, 87, 92). |
| 18-19 | `.purlin/tests.md` is the table of the latest committed evidence | It is written from every evidence file on disk, committed or not. |
| 32, 36 | `purlin:sign` walks the queue, never the whole list | No queue; the walk reads rules `to test by hand` or `to sign`. |
| 36 | The queue exists at `strong` and above | Hand checks wait at every gate (decision 78). |
| 37-39 | A rule reaches it through `manual test` or `unsigned`/`stale`, as a row | The kinds are `to test by hand` and `to sign`. |
| 69 | Sample `... RULE-2, RULE-5 are behind them.` beside a `RULE-7` of the same feature | The line names every rule the feature owns (drift RULE-7). |
| 87-88 | The range starts at the newest pull, merge, rebase, checkout, clone or reset | After a clone with nothing later, it is the last 20 commits (drift RULE-3). |
| 95 | The qa view shows stale signatures and the queue size, at `strong` up | Changed test files and their features, then the `to test by hand` and `to sign` lines, at every gate. |

### `docs/team-workflow.md`

| Line | Says | What is true |
|---|---|---|
| 6-8 | `strong` is met when the audit found nothing and, with mutation testing on, strength is at the minimum | With it on and nothing measured, the cell is `weak` with `strength not measured: <why>` (decisions 94, 97). |
| 22, 27-28 | Every unmarked rule's level is strong | No levels; the audit reads each rule with a proof, a passing test and no audit for its current hashes (run_script RULE-49). |
| 29 | `purlin:sign <feature>` signs the feature's rows in the queue | Its rules `to test by hand` or `to sign`. |
| 30 | `purlin:sign --batch` | `--all`; `--batch` exits 2. |
| 36-47 | The diagram: "the rule meets the gate strong"; a case goes back to `purlin:spec` | `purlin:sign` writes the case itself and the next step is `purlin:build`; the diagram has no path for `no proof`, `strength not measured` or a spec with no code files. |
| 57-58 | The audit prints the table, then `AI audit: ...` | The `AI audit` line comes first. |
| 58-59 | It prints `Test strength: ...` or `not measured; mutation testing is off.` | Neither is printed (decision 93). |
| 60-61 | It ends `Audit: <n> strong, <n> weak.` and `gate strong met: ...` | The summary and `Left to do`. |
| 61 | It exits 1 when a rule is short of its tests or its audit | When a tied test failed or did not run, or above `passed` when a rule it read is weak or could not be audited. |
| 65-67 | A workflow is written for two reasons | One. |
| 80 | `weak` is build work for `purlin:build` | Also `to measure` and `to tie to its files`. |
| 86-87 | With nothing measured, the reason is `no mutation score measured` | Only with it off or an engine that cannot run here; otherwise `weak`. |
| 89-90 | The queue holds the rules whose level is strong and that read `manual test`; header `<n> rules need a person` | These are `to test by hand`; the walk opens on the `Left to do` lines or on `Nothing is waiting ...`. |
| 113 | When the queue is empty and every rule meets the gate, the walk closes `Walked <n> rules: ...` | The walk closes with that line however much is left. |
| 123-125 | A signature binds rule, proof and test | Also code, audit, machines. |
| 125-126 | The branch that changed the text reads `stale` | `unsigned`, and nothing says why. |

## 4. Statements that break a decision

True of the page, and against a decision:

1. `README.md` 41-61 and `docs/getting-started.md` 47-80: the ten-minute path types the rules
   and the comments by hand; `purlin:build` does not appear. Decision 63 asks for `purlin:spec`
   and `purlin:build` (question 2).
2. `docs/getting-started.md` 23-24: the steps to remove Purlin. Decision 70: the docs carry no
   section on removing it.
3. `README.md` 26: "If you leave, the markers are comments." One line, not a section (question
   1).
4. `dev/plans/handoff.md`, "The model in one paragraph", which this check was told to read,
   still describes `[level: ...]`, "a column a rule is not asked shows nothing" and "one
   queue". Decisions 73 and 74 removed all three.

## 5. True statements no rule covers

Each gets a rule, a proof and a test by default (decision 64). The rule is given in the words it
would need. Two of the docs rows are rules that would have caught false statements.

### From the docs

| Where | Statement | The rule it gets |
|---|---|---|
| `README.md` 30, `getting-started.md` 28 | Purlin needs Python 3.9 or later | Setup, a test run and the status each exit 0 when the only Python on the path is 3.9. |
| `getting-started.md` 9-10 | Setup commits none of the files it writes | Setting a project up adds no commit. |
| `README.md` 23, `getting-started.md` 19 | No background job | No Purlin command leaves a process of its own running after it exits. |
| `getting-started.md` 93-95 | `Running the <suite> suite.`, `Markers: <t> tied to a test, <u> not tied.`, `Ran <suite> on <n> feature(s).` | A test run prints those three lines before the table. |
| `how-purlin-works.md` 118 | The dashboard reads a run's results at once | After a test run the reopened page shows that run's results with no other command. |
| `README.md` 103-115 (false today) | The command table gives each command's purpose sentence | The README's command table gives every command the purpose sentence `references/purlin_commands.md` gives it, word for word. |
| The start pages (false today) | Every quoted printed line | Every printed line quoted on a start page is printed, word for word, by a run of the sample project the page describes. |
| `dashboard.md` 11-12, `running-and-evidence.md` 49, `team-workflow.md` 127-128 | The page and `.purlin/runtime/` are kept out of git | A new project's `.gitignore` names `/purlin-report.html` and `.purlin/runtime/`. |
| `dashboard.md` 18-19 | `No board data yet. Run purlin:status to write .purlin/report-data.js, then reload this page.` | purlin_report RULE-21 gets a proof that quotes the whole sentence. |
| `dashboard.md` 42-43 | The uncommitted-tree notice | With an uncommitted tree the board reads `The working tree has uncommitted changes, so what is on this board is not what a commit would carry.` |
| `dashboard.md` 203-205 | The theme choice is remembered | A theme chosen with the toggle is the theme the page opens in after a reload. |
| `running-and-evidence.md` 308-310 | At `passed` the no-runner line reads `every test` | scaffold RULE-53 gets a proof at `--gate passed`. |
| `running-and-evidence.md` 369-370 | On GitHub the run is looked for for up to 60 seconds | A run branch whose run never registers is given up after 60 seconds, with its line. |
| `running-and-evidence.md` 241-244 | mutmut advice: dotted imports, `mutants/`, `--deselect` | Advice about another tool: it moves to `references/supported_frameworks.md` or leaves the page; no rule. |
| `review-and-signing.md` 40 | Rules come by feature, then by rule number | The walk stops in order of feature name, then rule number, so `RULE-2` comes before `RULE-10`. |
| `review-and-signing.md` 60 | Each proof at a stop shows its tag | A `@manual` or `@env(<system>)` proof shows that tag after its id. |
| `review-and-signing.md` 74-75 | The walk's audit lines | The line under `What the audit found` reads `Strong. It found nothing.`, `Weak. <finding>`, `Undecided. <finding>` or `Nothing yet: ...`. |
| `review-and-signing.md` 86-87 | Signing a hand check asks `What did you see, in one line:` | That prompt, before the next stop. |
| `review-and-signing.md` 94-95 | A skipped rule waits again next time | A skipped rule is still `to sign` or `to test by hand` after the walk, and no file records it. |
| `review-and-signing.md` 124, `regulated-workflow.md` 35 | The tag is signed with the commit key | `signed/<version>` carries an SSH signature made with the key `user.signingkey` names. |
| `raising-the-gate-and-upgrading.md` 89-90 | The table grows `Strong` at `strong`, `Signed` at `signed` | The status table's columns by gate. |
| `raising-the-gate-and-upgrading.md` 141-149 | The upgrade's gate question and its three answers | Quoted. |
| `raising-the-gate-and-upgrading.md` 170-172 | It names the `tests` setting it wrote | `wrote the tests setting: <names>`, or its no-suite form. |
| `raising-the-gate-and-upgrading.md` 174-176 | The workflow line | `it runs on a push to a run/* branch and on a push of a signed/* tag` |
| `raising-the-gate-and-upgrading.md` 184 | Each migration's question ends `[y/N]` | And an empty answer declines it. |
| `raising-the-gate-and-upgrading.md` 188-189 | `kept the previous bytes at <path>` | Each backup is named on that line. |
| `specs-and-anchors.md` 12-14 | The format page opens with `> Format-Version: N` | That line, N a whole number. |
| `specs-and-anchors.md` 43-45 | `purlin:spec` takes a sentence, a ticket, a document or criteria, and edits in place | The skill says so, and says not to renumber. |
| `specs-and-anchors.md` 60 | `> Stack:` holds the language and libraries | It is read as one line and changes no fingerprint. |
| `specs-and-anchors.md` 153-156 | After a merge the incoming duplicate id takes the next number; two pins resolve to the newer | The skill says so. |
| `specs-and-anchors.md` 169-176 | An anchor repository is for two or more projects | The skill says so. |
| `spec-from-code.md` 9-11, 24-35 | Survey, taxonomy, stop, order, one commit per spec, the position file | The skill says so. |
| `spec-from-code.md` 19-20 | Every rule is a draft until a person reads it, and the skill says so | The skill tells the agent to say so when it hands over. |
| `spec-from-code.md` 79-84 | No implementation in a rule; no evidence or signatures; an unobservable behaviour goes to `> Description:` | The skill says so. |
| `working-together.md` 49-50 | Loaded from the marketplace or with `--plugin-dir` | No file setup writes names the plugin's folder (scaffold RULE-21 comes close). |
| `working-together.md` 97-98 | Drift infers the role and says which | The skill infers it from the files the session touched and says which it chose. |
| `team-workflow.md` 130-132 | An evidence conflict is fixed by keeping either side and running again | A test run over either side rewrites that feature's section and commits it with `--commit`. |

### From the messages

No proof quotes these lines. Each gets a proof that quotes it, or one rule on the form of a
family of lines: the gate question and its three choices (`scaffold.py:75-79`); setup's skip
line with no remote (85); the lines under a written runner file (474, 477); the text
`purlin:anchor add` and `sync` print (`upstream.py` 148, 419, 433, 442, 445, 493); each refusal
and each `--check` reason of the evidence package (`package.py`); what `--update` prints for
each migration and for a failed commit, and each applied line (`update.py`); drift's two
refusals and the eng view's lines (`drift.py`); each settings warning (`gate.py` 125, 127, 135,
160); the suite problems a run prints (`markers.py` 218-242); the near-miss reasons
(`markers.py` 974, 1016-1038); the config tool's other answers and the no-workspace answer
(`server.py`); the uncommitted-specs block and the anchor error line (`status.py` 84, 222); the
plural `3 test comments to correct: purlin:build` (decision 97; proofs quote only the
singular); the audit printout's lines (`ai_audit.py` 456, 472-482); the walk's prompts and
closing lines (`sign.py`); the `.purlin/tests.md` text (`evidence.py` 64-69); the two
no-credentials lines of a remote runner (`host.py` 300, 386); the engine log lines
(`scripts/run/mutation/`); the run's argument refusals, the suite-tail block, the timeout
reasons and the unknown-feature line (`purlin_run.py`); every line a remote run prints
(`remote.py`); the report-reading reasons (`reports.py` 208, 212); the dashboard's hovers and
empty states (`app.js`, `board.js`, `rule.js`); the theme control's label (`theme.js` 29); the
words the templates write into a project (`templates/`). That is 29 groups.

## 6. Messages that break the style or a decision

Each is a line a person reads. Where the line is also false, it says so.

1. `scaffold.py:73` `Run git init, then init.`: no command is named `init`; it is
   `purlin:init` (decision 69).
2. `scaffold.py:83` with `446-453`: `A remote runner is written because:` is printed before the
   prerequisites are checked, and the same output then says `skipped the CI workflow`. False.
3. `workflow.py:114-118, 154`: `tagged @env for windows`: a person reads `Windows`; and
   `A proof` stays singular for several.
4. `fingerprint.py:420` `no run on macos yet`, shown on every first run: `macOS`.
5. `states.py:346, 487, 493-495, 513`: `windows: no run yet`, `passed on linux, macos`,
   `failing: macos, local`, shown on the rule's page and in the terminal: the names a person
   reads.
6. `upstream.py:355` with `441-443`: `nosuch: the source could not be read (no anchor named
   nosuch carries a git source).` No source was read; the anchor does not exist. No next step.
7. `upstream.py:419` `1 rules.`; `drift.py:348-349, 377, 384` `The last 1 commits`: singulars.
8. `remote.py:68, 90`: `No run registered ... then run: git pull --ff-only ...`, and the branch
   is deleted on the next line, so the step it names cannot work. False (host RULE-31 says the
   branch is deleted, so the line changes).
9. `rule.js:80` rounds test strength, `board.js:169` floors it: 85.7 reads 86 on one surface
   and 85 on the other.
10. `rule.js:214` `←` and `theme.js:31` `◐`: glyphs outside the four `CLAUDE.md` allows.
11. The gate refusal in three wordings: `scaffold.py:81`, `gate.py:111` (with Python quotes),
    `server.py:112`. The first two name no fix. Decision 97 gives the wording.
12. An anchor behind its source in three shapes (`status.py:214, 219`, `drift.py:612, 615`,
    `upstream.py:428, 433`): `Run` and `Run:`, a 40-character sha and a 7-character one.
13. `status.py:40`, printed also by `purlin_run.py:821` and `update.py:1107`: sends a set-up
    project to setup, and names `purlin:spec` without its `<name>`. False after setup (fault
    2).
14. `purlin_run.py:931-966, 493, 511, 520`, `reports.py:200-212`: `Evidence is missing: ...`
    lines that name no fix (no `--arm-timeout`, no check of the report path).
15. `reports.py:55, 56`: `is tied to no test`, `matches 2 tests ... not counted`: no step, no
    full stop, though the comment above them says the line says what to do.
16. `markers.py:930`: `names a rule that has proofs; name one of them`: another shape than its
    sibling, no command, no full stop.
17. `purlin_run.py:841`: `purlin: no spec named nosuch under specs/.`: exit 2 and no step.
18. `remote.py:58-59, 127, 147`: `ci: none`, not on a branch, the push failed: no step.
19. `drift.py:550, 553, 559, 566-567`: rules with no test, features out of date, files behind:
    no command (decision 69).
20. `specs.py:373`: the unknown-tags warning names no command (decision 94).
21. `status.py:177-180` and `update.py:104`: one fact in two wordings; the upgrade prints the
    placeholder `<name>` where the name is known.
22. `package.py:97` and `sign.py:97, 90`: the missing version in two wordings; `--release`
    without its command.
23. `sign.py:99` with `package.py:99, 579`: `the evidence package was not committed: the
    committed evidence still has work left to do.` The cause and effect read backwards; no
    step.
24. `ai_audit.py:472-482`, `sign.py:668-676`, `rule.js:68-76`: the audit's answer and the
    no-audit state in different words on three surfaces.
25. `ai_audit.py:279, 467` `Test strength: 86 percent  minimum 80` against `rule.js:80`
    `Test strength 86%, against a minimum of 80%.`: two wordings; the style's form is `86%`.
26. `rule.js:141-142` "from Claude Code" against `Type <command> in Claude Code.` (decision 96).
27. `ai_audit.py:456` `Nothing backs this rule yet.` and `rule.js:187, 206` `No test yet.`:
    two wordings, neither names `purlin:build <feature>`.
28. `scaffold.py:75` the gate question: `before a version is proven?`: the glossary word is
    `finished`.
29. `scaffold.py:95-97`: the same file is `the runner file` at `passed` and `the CI workflow`
    above it (decisions 83, 97).
30. `upstream.py:426, 436`: `the pin is current`, `Pin advanced`: no next step (decision 76).
31. `sign.py:133-134`: `sign: the signature commit was not made. Check that signing works ...`:
    no command to run, and a `sign:` prefix no sibling carries.
32. `mutation/__init__.py:237` `unknown engine "x"` names no allowed value;
    `mutmut.py:208` quotes a command that every other line writes bare.
33. `server.py:179` `Error: 'key' is required for write action.`: not decision 97's voice; does
    not say nothing was saved.
34. `evidence.py:127-137`: an evidence file ignored, with no fix named.
35. `remote.py:180` `The run finished red.`: colour jargon.
36. `scaffold.py:294` `copied ... -> purlin-report.html`: an ASCII arrow.
37. `workspace` in `upstream.py:463, 493`, `server.py:42, 199`, `host.py:121`: not a glossary
    word; the reference says project root.
38. `templates/purlin.yml`, `purlin.azure-pipelines.yml`: `arm` is not a glossary word, and
    `a Linux runner` reads `Linux/Unix`.
39. Python quotes reach a person: `gate.py:111, 160`, `drift.py:334`, `package.py:649`,
    `sign.py:894`, `ai_audit.py:539`.
40. Lines that start lower case with no full stop beside full sentences: `purlin_run.py:153,
    165`, `reports.py:55, 56`, `markers.py:930`, the suite problems.
41. `Run:` and `Run` side by side (`drift.py:612, 615`, `purlin_run.py:153` against the rest).
42. `server.py:187` `Set 'gate' = "strong"`: an assignment, not a sentence.
43. The dashboard sets labels and headings in capitals through its stylesheet; the style keeps
    capitals for badges (question 13).
44. `payload.py:181` `WARNING:`: decision 97's own wording, against the casing rule (question
    14).
45. `scripts/init/scaffold.py` and every page: `CI workflow`, `matrix`: the glossary word is
    remote runner and the runner file.

## 7. Product faults

Each was reproduced by a lane, in a scratch project, and the cause checked in the code where
named. Most severe first.

1. **Before the first test run, the status sends every rule to be written again.** With the
   specs and the comments above the tests written and `tests: []`, as setup leaves it, every
   proof reads `no test` and `Left to do` reads `125 rules to write a test for:
   purlin:build`. Comments are read only from files a suite's globs match
   (`markers.py:850-870`), and there is no suite yet. The glossary gives `not run` for a proof
   whose marker ties it to a test, and the step is `purlin:test`, which suggests the command.
   9 of 9 runs.
2. **The status after setup sends the project back to setup.** `No specs found under specs/.`
   then `→ Run: purlin:init to set this project up, or purlin:spec to write the first one.`,
   with the settings file present (`status.py:40`). The test run and the upgrade print the same
   line. It never names `purlin:spec-from-code` for a tree with code. 9 of 9 runs, and the
   upgrade in a scratch project.
3. **Setup's last line names the wrong command for a project with code.** `→ Run: purlin:spec
   to write the first spec.` (`scaffold.py:488`); the init skill says code with no specs goes
   to `purlin:spec-from-code`. 9 of 9 runs.
4. **The jest command breaks every run that names files.** The suggested entry ends
   `--reporters=default --reporters=jest-junit {files}`, and jest reads the files after it as
   more reporters: `Error: Could not resolve a module for a custom reporter.` /
   `Module name: test/preserveArray.test.js`. The run then writes `Evidence is missing` and
   sends you to `purlin:test`, which fails the same way. `{files}` is filled by `purlin:test
   <feature>`, by a run after a change, and by `purlin:build`. The entry is in
   `scripts/mcp/purlin/frameworks.py:52` and `references/supported_frameworks.md:93`. 3 of 3
   JavaScript runs are exposed; one probe reproduced it.
5. **A rule with one untested proof among tested ones is sent to `purlin:test`.** The evidence
   lists the untested proof with `"result": "missing"`; the passed cell counts a listed proof
   as tested (`states.py`, `_untested`) and reads `not run`, so `Left to do` says `1 rule to
   test: purlin:test`, which cannot clear it. The run itself says `has no test for PROOF-6.
   Run purlin:build`. The glossary gives `no test` with `no test for PROOF-6` (decision 69: the
   terminal and the evidence say the same). 2 of 3 C# runs.
6. **Setup wires the breaking tool to the wrong folders.** On `toolz`, `[tool.mutmut]` got
   `source_paths = ["doc", "examples", "tlz", "toolz"]` and
   `pytest_add_cli_args_test_selection = ["bench"]`: the benchmarks as the tests, the docs as
   source. `mutmut_paths` (`scaffold.py:196`) looks only at top-level folders, and the tests
   live in `toolz/tests/`. 2 of 2 Python runs with the breaks on.
7. **Systems are shown by their stored words.** Every first run printed `(no run on macos
   yet)`; the cell reasons and setup's runner reason do the same (section 6, items 3 to 5). 9
   of 9 runs.
8. **The suggested Python command runs the wrong interpreter and drops the project's own
   options, silently.** `python3 -m pytest ...` runs the first `python3` on the path, which in
   these runs was Purlin's own environment; `test_has_version` failed there for want of the
   installed package, and passed under the project's own. The 77 docstring examples the
   project's own CI runs (`--doctest-modules`) are not run, and nothing says so. 3 of 3 Python
   runs (question 3).
9. **The install line assumes npm.** `run npm install --save-dev jest-junit` in a yarn
   project: run as printed, it wrote `package-lock.json` beside `yarn.lock` and rewrote
   `yarn.lock`. 3 of 3 JavaScript runs.
10. **Setup's line about Stryker says nothing of its absence.** `jest: Stryker measures the
    breaks. Without it test strength is not measured.`, with Stryker not installed and no
    install command; decision 97 gives the command for .NET. 4 runs.
11. **The breaking question shows its default twice**, `[y/N]` then `[n]: `
    (`scaffold.py:242-245`). With no input the script takes `n` silently. 6 runs.
12. **`wrote .gitignore` is printed twice** when the breaks are on. 2 runs; seen in sanity
    check 2 as well.
13. **Setup says the runner is written, then skips it**, where there is no remote or a
    prerequisite is missing (section 6, item 2). Reproduced twice in scratch projects.
14. **Setup says one thing twice**: `No remote runner: every proof runs on this operating
    system, ...` then `skipped the CI workflow (every proof runs on this operating system,
    ...)`.
15. **A remote run tells you to pull a branch it has just deleted** (section 6, item 8).
16. **The upgrade needs two runs for one 0.9.5 line.** A proof line ending `@unit @windows`:
    the pending list is read once, before the `os-tags` migration rewrites the tag, so
    `kind-tags` is found only on a second run. Update RULE-5 says a second run finds nothing
    left (`update.py:1068`).
17. **A rule whose only proof has no test is named without the proof.** `dicts RULE-2 has no
    test. Run purlin:build dicts.`; decision 97 gives `has no test for PROOF-2`. The test skill
    documents both forms, so this may be meant. 2 runs.
18. **The glossary and states RULE-63 disagree** on a rule of a spec with no `> Scope:` at
    `signed`: its strong cell reads `waiting` and its signed cell `unsigned`, where the
    glossary gives `waiting` while the cell below is not met.
19. **`purlin_run.py --help` is refused** as an unknown argument, then the usage prints. Seen in
    sanity check 2.
20. **At `passed`, `.purlin/evidence/README.md` names the audit and what it found.** Decision 50
    keeps words of a higher step out of `passed`. Not checked further.
21. **`.purlin/tests.md` heads a dirty run `Tests at 89cdda7`** with no mark, where the evidence
    records `"dirty": true`.

## 8. Where the instructions failed the agent

1. **The position file of `purlin:spec-from-code` has no shape.** Nine agents wrote nine
   shapes. No reference names a reader.
2. **When the comments above tests are committed is not said.** Agents put them in each
   `spec(<name>):` commit, left them for `purlin:test --commit`, or left 39 test files dirty
   so the evidence records `dirty: true`. The files setup writes (`.gitignore`,
   `pyproject.toml`) are committed by no step (question 10).
3. **The three reasons for leaving a test untied cover too little.** Docstring examples cannot
   carry a comment at all; tests of the test suite's own helpers, of internal helpers, and
   benchmarks fit none of the three. Agents stretched "shows only part of what a rule needs"
   over 20 tests (question 3).
4. **"Tie every test" and "no rule for a private helper" pull opposite ways** for modules the
   package does not export but tests (both JavaScript modules, 26 tests). The guide also names
   "rules for behaviour that exists only in tests" as too many rules (question 4).
5. **The quality guide has no case for a library.** It bars function and class names in a
   proof; for a library those, and the error types, are what a caller sees. 8 of 9 runs
   (question 5).
6. **"One proof, one case" is silent on tables of inputs** and on one test per number type.
   The C# runs tied such tests to proofs holding several cases, 69 to 75 times each
   (question 6).
7. **`> Requires:` is recommended without its effect.** The required spec's rules are counted
   again in the requiring spec (`2 (+39 shared)`, `38 of 41`), under the word `shared` that
   decision 90 gives to anchors. 5 runs (question 8).
8. **The skill's ending lists three next steps and no order,** and the third,
   `→ Run: purlin:init --gate strong`, names the gate the project may already be at. The
   status at that moment names a fourth (fault 1).
9. **The init skill does not say to ask the breaking question and pass the answer.** The
   script asks on its own input; the flag `--mutation` exists but the skill does not tell the
   agent to ask the person first and pass it. 6 runs piped `y`.
10. **"Before you start: call `sync_status`"** does not say to pass the project's root; without
    it the tool read the folder its server started in. Its answer then contradicts the skill
    (fault 2).
11. **The skill and its page say nothing can read specs before setup.** The status reads them.
12. **The install line the test run prints is passed on verbatim.** The test skill does not say
    whether the agent runs it, or to use the project's package manager.
13. **Nothing prompts a comparison of the suggested command with the project's own**: its
    interpreter, `--doctest-modules`, `--no-restore`.
14. **A detached head is not mentioned.** Two C# runs and one JavaScript run started on a tag;
    commits went onto the detached head until the agent made a branch.
15. **`references/formats/spec_format.md`'s own example proofs break the quality guide**:
    "Parse the config and verify the default values", "POST /api/users against the database;
    verify 201", "Grep src/ for eval(); verify zero matches". So do `docs/specs-and-anchors.md`
    38-40 and 102.
16. **The report step asks for every proof beside its test**, 447 lines on one run, with no
    shorter form.
17. **What counts as public in Python is not said** (`__all__`, a leading underscore, the
    project's API page).
18. **Commented-out tests** (8 in the C# project) are not mentioned.
19. **The check's own brief was out of date**: `handoff.md`'s paragraph (section 4, item 4).

## 9. The work that follows by default

By file, so a planner can cut lanes. Each item names the decision or rule that settles it.

**Docs (decision 63; each page rewritten from the tables in section 3, samples taken from a
real run, words from the glossary):**

- `README.md`, `docs/index.md`, `docs/getting-started.md`, `docs/how-purlin-works.md`: the
  ten-minute path through `purlin:spec`, the first test run's suggestion and your confirmation,
  and `purlin:build` (decision 63); the removal steps go (decision 70); the command table
  carries the purpose sentences word for word.
- `docs/running-and-evidence.md`, `docs/dashboard.md`; both screenshots retaken last.
- `docs/review-and-signing.md`, `docs/regulated-workflow.md`,
  `docs/raising-the-gate-and-upgrading.md`; the broken link to `#the-level` goes.
- `docs/specs-and-anchors.md`, `docs/spec-from-code.md`, `docs/working-together.md`,
  `docs/team-workflow.md`; the example proofs on these pages meet the guide.
- `references/formats/spec_format.md`: its example proofs meet the guide (no bump: an example).
- `dev/plans/handoff.md`: the paragraph "The model in one paragraph" says what is now.

**Product:**

- `scripts/mcp/purlin/status.py`, `scripts/init/scaffold.py` (`next_step`),
  `scripts/init/update.py` (`_print_ending`), `scripts/run/purlin_run.py:821`: one ending for
  a project with no spec, by state: set up with code, `→ Run: purlin:spec-from-code`; set up
  with no code, `→ Run: purlin:spec <name>`; not set up, `→ Run: purlin:init` (faults 2, 3;
  decision 69). Specs: `mcp/status`, `init/scaffold`.
- `scripts/mcp/purlin/markers.py`, `scripts/mcp/purlin/summary.py`: with an empty `tests`
  setting, comments in tracked files are read, a marked proof reads `not run`, and `Left to do`
  reads `to test: purlin:test` (fault 1; glossary chain).
- `scripts/mcp/purlin/states.py`: a proof listed as `missing` counts as untested, so the rule
  reads `no test` with `no test for PROOF-<n>` (fault 5); the no-scope case follows the
  glossary (fault 18). Spec: `mcp/states`.
- `scripts/mcp/purlin/frameworks.py`, `references/supported_frameworks.md`: the jest entry
  puts `{files}` where jest reads it as files (fault 4); the install line uses the lock file's
  package manager (fault 9). Spec: the frameworks spec; `Format-Version` of none changes.
- `scripts/init/scaffold.py`: `mutmut_paths` finds a test folder below the top level and never
  takes a benchmark folder as the tests (fault 6); `wrote .gitignore` once (12); the default
  shown once (11); the runner reasons printed only when the file is written (13) and said once
  (14); one name, the runner file, at every gate (section 6, 29); the Stryker line names the
  install command (10); `Run git init, then purlin:init.`; the gate question says `finished`;
  the gate refusal in decision 97's wording; the ASCII arrow goes.
- `scripts/mcp/purlin/fingerprint.py`, `scripts/mcp/purlin/states.py`,
  `scripts/run/workflow.py`: every system a person reads is `Windows`, `macOS` or `Linux/Unix`
  (fault 7; writing style).
- `scripts/run/remote.py`: the no-run-registered lines say the branch was deleted and name the
  next step (host RULE-31); `The run finished red.` reworded; each problem line names a step.
- `scripts/init/update.py`: the pending list is read again after each migration (fault 16;
  update RULE-5); the scope line prints the feature's name.
- `scripts/report/src/rule.js`, `board.js`, `theme.js`: one rounding for test strength; the
  audit and no-test wordings match the terminal; `Type <command> in Claude Code.`; the glyphs
  `←` and `◐` go (`CLAUDE.md`).
- `scripts/review/ai_audit.py`, `scripts/review/sign.py`: the audit's answer in one wording;
  `NOT_MADE` names a check; the tag-refusal line reads the right way round.
- `scripts/anchor/upstream.py`: `1 rule`; a missing anchor named as missing, with a step; the
  pin lines name the next step; the behind-its-source line in one shape with `status.py` and
  `drift.py`.
- `scripts/mcp/purlin/drift.py`: `The last commit`; each problem names its command (decision
  69).
- `scripts/mcp/purlin/gate.py`, `server.py`, `specs.py`, `evidence.py`,
  `scripts/run/reports.py`, `scripts/mcp/purlin/markers.py`,
  `scripts/run/mutation/`, `scripts/export/package.py`: the lines of section 6 that name no
  step or break a shape.
- `scripts/run/purlin_run.py`: `--help` prints the usage and exits 0; the unknown-feature line
  names a step.
- `templates/evidence-readme.md`, `templates/purlin.yml`, `templates/purlin.azure-pipelines.yml`:
  no word of a higher step at `passed`; `Linux/Unix`; no `arm`.
- Rules and proofs for every row of section 5, in the spec each belongs to, and one test that
  runs the sample project of the start pages and compares every quoted line (decision 64).

**Skills and references:**

- `skills/spec-from-code/SKILL.md`: the position file's fields; pass the project root to
  `sync_status`; the claim that nothing reads specs before setup goes; the endings in order,
  with `purlin:init --gate strong` only below `strong`; a detached head is named before the
  first commit. Its length stays within its maximum (decision 80).
- `skills/init/SKILL.md`: ask the breaking question, then pass `--mutation` or not.
- `skills/test/SKILL.md`: run the install line the suggestion prints, with the project's
  package manager.
- `specs/review/signatures.md` RULE-68: `<c> case(s) added` as the code prints it.

**For the next sanity check:** one project copy carries a test that fails before the run, so
decision 66's clause about failing tests is tried; the agents count existing tests one way.

## 10. What was dropped, and why

- **Every lane's note that the harness refused `report.md`.** The check's own doing; the
  findings came back in each lane's output.
- **"Show the list and stop" with no person there.** The check's own doing: the agents
  answered as the person.
- **`--project-root` added to the scripts.** The check's own doing; inside Claude Code the
  project root is the working folder.
- **The dotnet entry's glob `**/*.cs` taking in `src/`.** It did no harm; only tests carry
  comments.
- **The upgrade's applied lines that name what 0.9.5 did.** Covered by the one exception for
  the upgrade from 0.9.5.
- **The model prompt in the audit as a message a proof must quote.** No person reads it;
  `references/review_criteria.md` is its home.
- **Questions a decision already settles**, moved to section 9: whether the style allows a
  stored system word in a reason (the writing style, "Systems by their names"); `proven` or
  `finished` in the gate question (the glossary); whether drift names commands and whether the
  status of an unset project names setup (decision 69); whether the dashboard page is fixed now
  or last (decision 63); whether the remote branch is kept or the line changes (host RULE-31);
  whether printed samples are checked by a test (decision 64).
- **Duplicates merged:** the ten-minute path (two lanes); the `.gitignore` lines (two lanes);
  the status after setup, setup's last line, `macos` and the empty-suite status (nine runs
  each); the breaking question's two defaults (six runs); the Stryker line (four runs).

## 11. Questions for the owner

Most basic first. Each: what the thing is for, the question, the options, the recommended
first.

**1. What the docs say about leaving.** Purlin's promise is that it stays out of your way: your
tests are your own and keep running without it. The docs carry no section on removing Purlin,
but the README keeps one line, "If you leave, the markers are comments." Does that line stay?
- Keep the one line. It states the promise in six words and is not a section.
- Remove it. The README says only what Purlin does while you use it.

**2. What the ten-minute path shows.** The first page walks a new reader from nothing to one
passing rule. It will now use the commands that write rules and tests with a model, which
produce different words each time. What does the page show?
- What you type, and the summary each step ends on, which is the same on every run. The reader
  sees their own rules on their own screen.
- The exact rules and tests from one real run, labelled as an example. The page is longer and
  drifts from what a reader gets.
- Keep the path typed by hand and name the two commands after it. This goes against decision
  63.

**3. Tests that cannot carry a comment.** Purlin ties a rule to a test through a comment above
the test. Python projects often keep examples inside the documentation of each function, and
their own test command runs them; they cannot carry a comment, and the suggested command today
stops running them without saying so. What happens to them?
- The suggested command keeps running them, and the report lists them under a fourth reason, "a
  test that cannot carry a comment". Nothing the project ran before stops running.
- They are left untied under the reason "shows only part of what a rule needs", and the
  suggested command stays as it is. Fewer words; the project runs less than before.
- The starting-from-code step turns each example into a test that can carry a comment. More
  work for the agent; the project gains tests.

**4. Code no caller can reach.** Starting from code writes rules for what a user or a caller
can see. Some projects keep modules that nothing outside the package can call, yet test them.
Does such a module get rules?
- No. It is listed among the files with no rule, and its tests are left untied under a fourth
  reason, "tests code no caller can reach". The rules stay about what callers see.
- Yes, as if it were public, so its tests are tied. More rules, and the audit may call them too
  many.
- Ask the person each time, in the step where they edit the list of features.

**5. Proofs for a library.** A proof is written so a person who cannot read code can judge it,
and so it names no function and no class. For a library, the function a caller calls and the
error type it gets back are the only things the caller sees. May a proof name them?
- Yes, when the name is part of what a caller sees: the library's public names and its error
  types. The guide gains that case.
- No. The proof describes the call in words, as the runs did; the rule carries the name.
- Remove the bar on names in proofs altogether.

**6. One test that checks many inputs.** A proof holds one case. Many projects write one test
that runs a table of inputs, or the same test once per number type. How is such a test tied?
- One proof per case the table holds, all tied to the same test. The proof count grows with
  the table.
- One proof may name a list of like inputs with one action and one kind of result, and counts
  as one case. The guide says so.
- Leave the test untied as showing only part of a rule.

**7. Reusing a rule number.** Each rule has a number that signatures, comments and evidence
refer to. The format promises a deleted number is never used again, but the command that adds
rules picks one past the highest number it sees, so deleting the highest rule on the main
branch frees its number. Which holds?
- Never reused: the spec keeps a record of the highest number it has held.
- Reused only when the number was never signed, tested or committed; the format says so.
- Reused whenever it is free; the format stops promising otherwise.

**8. Rules a spec takes from another spec.** A spec may say it requires another, so it does not
repeat that spec's rules. Today the required rules are counted again in the requiring spec's
row, as `2 (+39 shared)`, with the word the dashboard keeps for rules from shared anchors. What
does the row count?
- Its own rules only. The required spec is counted once, in its own row.
- Its own and the required rules, with a word of its own, such as `(+39 required)`.
- Remove the requirement line; a spec that depends on another says so in its description.

**9. Signing a rule whose feature names no code.** At the gate `signed`, a signature covers
the code of the feature, which a spec names in its list of covered files. A rule in a spec
with no such list can be signed, but the signature never counts. Should the signer be told?
- Yes: signing says, on the line for that rule, that it will not count and names the command
  that adds the files. Nothing is refused.
- No: the status already gives the reason, and signing stays silent.

**10. Who commits what setup writes.** Setup writes the settings file, the ignore list and,
with the breaks on, a tool's configuration, and commits nothing. A test run with `--commit`
commits the settings file and the specs, not the other files. Who commits them?
- The first test run with `--commit`, which commits them with the specs, tests and settings
  it already commits. One step, and nothing is left dirty.
- Setup commits its own files in one commit. Setup then commits, which it does not today.
- The person, told so in setup's last lines.

**11. The key upload and the branch protection the signing pages advise.** Purlin records who
signed and does not check whose key it was, and it neither sets nor reads a git host's
protections. The signing pages tell each signer to upload their key to the git host, and
teams to protect the main branch and the signed tags. Does that advice stay?
- It stays, marked as the git host's own feature that Purlin does not rely on.
- It goes. The pages say what Purlin records, and the system of record decides the rest.

**12. A remote run with no way to watch it.** A remote run pushes a temporary branch, waits for
the git host to run the tests there, and brings the results back. Without the GitHub or Azure
command-line program, it cannot wait, and the branch stays on the git host. What does it do?
- It prints the pull command and, after it, the command that deletes the branch.
- It refuses before pushing and names the program to install. Nothing is left on the host.
- It leaves the branch and prints the pull command, as today.

**13. Capitals on the dashboard.** The writing style keeps capitals for the state badges. The
dashboard's design sets every label and heading in capitals, and a decision asks for `563
RULES TOTAL`. Which rules?
- The design: the style page says labels are set in capitals by the design. Nothing on the page
  changes.
- The style: labels and headings in sentence case, badges alone in capitals.

**14. The `WARNING:` prefix.** When a line under a spec's rules has no number, the status prints
one warning that starts `WARNING:`, as decision 97 wrote it. No other message has a prefix.
- Drop the prefix, so the line reads like the other four spec warnings.
- Keep it as decision 97 wrote it.

**15. What the first test run says when it finds no test tool.** `purlin:test` prints `... so
nothing ran. Run purlin:test to have one proposed.` The command names itself.
- It says that the agent now reads the project and proposes a command, and names nothing to
  type.
- It keeps naming `purlin:test`, since a person typing it again inside Claude Code gets the
  proposal.
