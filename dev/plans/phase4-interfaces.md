# Phase 4 interfaces: what was built

Written by the first integration agent on 2026-09-29, after P1 `shared` and the 20 lanes of
fan-out 1 (`phase4-plan.md` section 4) merged. This file says what the tree holds. Where it
differs from `phase4-contracts.md`, this file says so, and the code is what it does. Nothing was
pushed or tagged, and no audit or signing was run. Each lane's own report is in the session
scratchpad, `reports-4/<lane>.md`; this file carries what later work needs from them.

## Where `main` stands

- `main` is local. P1 (`0c9a1e42d`, `1d87f5ede`), then the 20 lanes by fast-forward in the order
  of plan section 8, then integration's commits below.
- The full sweep, `bash dev/run_tests.sh`, at `0574fbe8b` (every lane merged and the fixes
  below in): `2241 passed, 3 skipped in 708.03s (0:11:48)`, `>>> All Pytest Tests: PASSED`,
  `Suites: 5 passed, 0 failed`; the four shell suites (`E2E Init (wiring)`, `E2E External Refs`,
  `E2E Required Rules`, `E2E Anchor Authority`) passed.
  Before the lanes: P1's `--fast` read `1830 passed, 3 skipped`. With every lane merged and no
  fix in, `--fast` read `8 failed, 2058 passed, 3 skipped`, each failure one a lane reported.
- This repository through its own tool, `python3 scripts/run/purlin_run.py --test --all` at
  `7a3ef0698`, exit 0: `Markers: 2289 tied to a test, 0 not tied.`, `Ran pytest, shell on 35
  features.`, `86 proofs need Windows; this machine is macOS. Run purlin:test --remote.`,
  `Evidence written to .purlin/evidence/local/ for 35 features.`, then
  `866 rules. 785 pass their tests. 0 are strong. 0 are signed.` and `Left to do:` /
  `  81 rules to test on Windows: purlin:test --remote` / `  785 rules to audit: purlin:audit`.
  No warning prints beside the table: the security anchor's three `finds no file in git` lines
  are gone. No rule reads `partial`, `failed` or `no test`. With `--commit` the same lines,
  with `Evidence committed.` after the evidence line, and one commit,
  `e802f8d02 purlin: evidence at 7a3ef06`.
- The dashboard, `scripts/report/purlin-report.html`, rebuilt and committed once: `7a3ef0698`.
  Looked at with playwright from the `.venv`, headless, on the fixture `regulated`, at 1500,
  1280, 1024, 768 and 390 pixels in both themes: the board with `login` open and `RULE-4`
  unfolded, `login RULE-1`'s page and `login RULE-2`'s page. No screen scrolls sideways at any
  width; the theme button reads `Light theme` in dark and `Dark theme` in light; the back button
  reads `Back to the board`; the unsigned rule reads `Type purlin:sign login RULE-2 in Claude Code.`
  and `Test strength 86%, against a minimum of 80%.`
- The runner file, `.github/workflows/purlin.yml`, written again by setup with `--yes` from the
  templates of phase 4 (the three sentences of K2.6), committed by setup itself:
  `8008d9de6 chore(init): set up Purlin at the gate signed`, holding that file alone. Setup
  printed `it runs on windows-latest, the systems a proof in specs/ is tagged @env for that this
  machine is not.` It also printed `dotnet: dotnet stryker is not installed: run "dotnet tool
  install -g dotnet-stryker"` for this repository, whose suites are pytest and shell.

## The merges

Each lane was rebased on `main` in its worktree, its own test files were named to pytest and run
whole, and `main` was fast-forwarded to it. No rebase met a conflict. Every lane merged; none was
held back.

| # | Lane | Head after rebase | Its own files at merge |
|---|---|---|---|
| 1 | `core` | `2503aec74` | 250 passed |
| 2 | `anchors` | `d3c9df2bc` | 269 passed, 1 skipped, 1 failed (schema_spec_format PROOF-55, K6, fixed below) |
| 3 | `host` | `c176e4667` | 112 passed |
| 4 | `scaffold` | `b5cfffe44` | 155 passed; `dev/test_init_e2e_wiring.sh` ok |
| 5 | `reports` | `556d5bd3a` | 112 passed |
| 6 | `run` | `090a6af94` | 274 passed, 1 skipped, 6 failed (run_script PROOF-91, 177, 179 to 182, K6, fixed below) |
| 7 | `mutation` | `f340ff097` | 91 passed |
| 8 | `settings` | `8719670ae` | 75 passed, 1 skipped |
| 9 | `drift` | `dde6ac11a` | 76 passed |
| 10 | `update` | `74b985985` | 129 passed |
| 11 | `signing` | `211a2bc18` | 131 passed |
| 12 | `review` | `d1e21a446` | 79 passed |
| 13 | `package` | `e17df015c` | 50 passed, 1 failed (package PROOF-4, reported by `reports`, fixed below) |
| 14 | `upstream` | `236667398` | 41 passed |
| 15 | `dashboard` | `200b92e19` | 182 passed (the worktree's modified built page, a generated file, was restored before the rebase) |
| 16 | `instructions` | `edf68ec63` | 41 passed |
| 17 | `skills-run` | `a200ff490` | 47 passed |
| 18 | `skills-author` | `b7b61a683` | 78 passed |
| 19 | `skills-sign` | `8c52049c0` | 38 passed |
| 20 | `words` | `fb0a8ac2b` | owns no test file; every `dev/test_skill_*.py`, `test_purlin_agent.py` and `test_vocabulary.py`: 226 passed |

## Integration's commits

| Commit | What |
|---|---|
| `72b7510c5` | schema_spec_format PROOF-55 and its test quote core-7 whole (K6, lane `anchors` could not before `core` merged) |
| `4d524aa6d` | run_script RULE-76, PROOF-177, 179 to 182 quote core-6 (`<value>` as JSON writes it, so the word reads `"four"`); RULE-56 and PROOF-91 say `no run on <System> yet`, and PROOF-91's test reads `os_word` (K6, handed over by lane `run`). PROOF-177 lost the clause `after the `Purlin status:` line` and now says `at most 4 at once` to stay at 58 words; its test still checks both, and PROOF-179 to 182 state the order |
| `8e0d2bd7f` | reports PROOF-20, 88, 89 quote the suite problems with run-11's step, and their tests compare the whole line |
| `2f9a8db3f` | package PROOF-4: with no suite set the markers are read (ruling 12), so a project with no evidence has its 2 rules left `to test`, `purlin:test`, not `to write a test for` |
| `751d45f6c` | update: the gate refusal takes `scaffold.as_json`, the breaking prompt adds ` [y/N] ` itself, and PROOF-27, 46, 47, 132's tests compare the whole lines, since the shims for before `core` and `scaffold` merged are no longer needed |
| `0574fbe8b` | K9's paragraph in `dev/plans/handoff.md` |
| `7a3ef0698` | the built dashboard page |
| `e802f8d02` | the evidence of the own-tool run, by `--commit` |
| `8008d9de6` | the runner file, by setup with `--yes` (setup's own message, with no attribution lines) |
| this file | `dev/plans/phase4-interfaces.md` |

## The greps of plan section 7 item 8

Outside `dev/plans/`, `RELEASE_NOTES.md`, `docs/`, `README.md` and `dev/fixtures/upgrade-0.9.5/`,
each of these finds nothing: `NO_SPECS`, `WARNING:`, `the CI workflow`, `finished red`,
`no run on macos`, `no run on windows`, `Nothing backs this rule`, `proven?`, `1 rules`,
`The last 1 commits`, `to have one proposed`; `◐` and `←` in `scripts/report/src/`; `-> ` in
`scripts/init/scaffold.py`. `from Claude Code` is gone from the rebuilt page. What is left, and
left as it is:

- `workspace` in `scripts/` and `references/`: only `GITHUB_WORKSPACE`, the name of GitHub's own
  variable, in `scripts/run/ci.py`.
- `Run: purlin:anchor`: `skills/drift/SKILL.md:70` (`→ Run: purlin:anchor sync <name>`) and
  `skills/anchor/SKILL.md:98` (`→ Run: purlin:anchor create <name>`), each a skill's closing
  `→ Run:` directive, not a line the product prints. No contract changes the directive form.
- `is not a gate`: the heading `## What is not a gate` in `references/hard_gates.md`, not the
  retired refusal.

## Ids per spec

Read from the tree after integration. Every spec carries `> Highest-Rule:`, and each equals
its highest rule number now; no lane reused an id (each lane checked its specs against
`git log -p --follow`).

| Spec | Rules | Highest RULE | Proofs | Highest PROOF | `> Highest-Rule:` |
|---|---|---|---|---|---|
| `specs/_anchors/schema_spec_format.md` | 28 | RULE-28 | 64 | PROOF-66 | 28 |
| `specs/_anchors/security_no_dangerous_patterns.md` | 8 | RULE-8 | 89 | PROOF-91 | 8 |
| `specs/anchor/upstream.md` | 26 | RULE-34 | 47 | PROOF-58 | 34 |
| `specs/dashboard/purlin_report.md` | 51 | RULE-59 | 176 | PROOF-197 | 59 |
| `specs/export/package.md` | 24 | RULE-24 | 54 | PROOF-54 | 24 |
| `specs/init/scaffold.md` | 55 | RULE-73 | 140 | PROOF-161 | 73 |
| `specs/init/update.md` | 39 | RULE-45 | 139 | PROOF-152 | 45 |
| `specs/instructions/purlin_agent.md` | 9 | RULE-16 | 10 | PROOF-47 | 16 |
| `specs/instructions/purlin_output.md` | 3 | RULE-3 | 6 | PROOF-6 | 3 |
| `specs/instructions/purlin_version.md` | 13 | RULE-15 | 25 | PROOF-37 | 15 |
| `specs/mcp/config_engine.md` | 11 | RULE-15 | 30 | PROOF-40 | 15 |
| `specs/mcp/drift.md` | 25 | RULE-26 | 64 | PROOF-65 | 26 |
| `specs/mcp/evidence.md` | 29 | RULE-29 | 77 | PROOF-77 | 29 |
| `specs/mcp/server.md` | 20 | RULE-31 | 49 | PROOF-162 | 31 |
| `specs/mcp/specs.md` | 13 | RULE-21 | 34 | PROOF-43 | 21 |
| `specs/mcp/states.md` | 70 | RULE-95 | 203 | PROOF-235 | 95 |
| `specs/mcp/summary.md` | 14 | RULE-14 | 36 | PROOF-37 | 14 |
| `specs/review/ai_audit.md` | 21 | RULE-29 | 81 | PROOF-90 | 29 |
| `specs/review/signatures.md` | 63 | RULE-89 | 137 | PROOF-178 | 89 |
| `specs/run/evidence_writer.md` | 25 | RULE-25 | 87 | PROOF-87 | 25 |
| `specs/run/host.md` | 28 | RULE-44 | 117 | PROOF-138 | 44 |
| `specs/run/mutation.md` | 32 | RULE-37 | 90 | PROOF-100 | 37 |
| `specs/run/reports.md` | 31 | RULE-31 | 114 | PROOF-114 | 31 |
| `specs/run/run_script.md` | 58 | RULE-84 | 207 | PROOF-255 | 84 |
| `specs/skills/skill_anchor.md` | 13 | RULE-13 | 14 | PROOF-34 | 13 |
| `specs/skills/skill_audit.md` | 16 | RULE-24 | 21 | PROOF-51 | 24 |
| `specs/skills/skill_build.md` | 14 | RULE-17 | 15 | PROOF-46 | 17 |
| `specs/skills/skill_drift.md` | 6 | RULE-10 | 13 | PROOF-36 | 10 |
| `specs/skills/skill_export.md` | 12 | RULE-12 | 14 | PROOF-34 | 12 |
| `specs/skills/skill_init.md` | 12 | RULE-85 | 23 | PROOF-96 | 85 |
| `specs/skills/skill_sign.md` | 21 | RULE-21 | 24 | PROOF-49 | 21 |
| `specs/skills/skill_spec.md` | 20 | RULE-21 | 21 | PROOF-50 | 21 |
| `specs/skills/skill_spec_from_code.md` | 26 | RULE-48 | 28 | PROOF-162 | 48 |
| `specs/skills/skill_status.md` | 10 | RULE-11 | 14 | PROOF-35 | 11 |
| `specs/skills/skill_test.md` | 20 | RULE-20 | 26 | PROOF-49 | 20 |
| all 35 | 866 | | 2289 | | |

## Splits, moves and re-pointed proofs

- `host` RULE-31 -> RULE-31 (the Azure lookup, poll, results, no run registered and the
  90-minute limit), RULE-42 (the program to wait with is looked up before the push). PROOF-71
  moved from RULE-12 to RULE-42, PROOF-82 from RULE-31 to RULE-42; both reworded to host-1 and
  host-2.
- `skills-author` skill_spec_from_code RULE-10 -> RULE-10 (code no caller outside the project can
  reach gets no rule, and its files are listed), RULE-48 (what a caller reaches in Python,
  JavaScript and C#). PROOF-145 stays on RULE-10; new PROOF-146 is on RULE-48. RULE-7 lost
  "Give every source file a rule where you can" (K5.4 step 6 replaces it).
- `mutation` PROOF-52 re-pointed from RULE-12 to RULE-37, its text unchanged.
- `settings` PROOF-7's first-line quote moved to the new PROOF-162 (RULE-7), to keep PROOF-7
  under 60 words.
- No other lane split a rule or moved, re-pointed or deleted a proof. No Windows proof moved.

## What was built where it differs from the contracts

1. **Fault 18, technical call 11** (lane `core`). The call says the no-files override of the
   signed cell applies "only once the strong cell is met". The code applies it wherever the
   signed cell does not read `waiting`, which is states RULE-73's condition. The two agree in
   every case a proof covers and differ in two: a rule whose proof is `@manual` and not checked
   by hand keeps the `NAMES_NO_FILES` reason, where the literal reading leaves `unsigned` with no
   reason; a signature binding a rule whose strong cell reads `weak` leaves the rule `unsigned`,
   where the literal reading lets it read `signed`.
2. **K5.1's runner-file sentence** (lane `words`) names `azure-pipelines.yml`; setup writes
   `purlin.azure-pipelines.yml` (`scripts/run/workflow.py`). The glossary carries the contract's
   words, so it names a path the code does not write.
3. **Technical call 20** (integration). The call says setup runs with empty input and the runner
   file is committed as `chore: the runner file, with the templates of phase 4`. The task for
   this integration said `--yes`, so setup made the commit itself:
   `chore(init): set up Purlin at the gate signed`, holding the runner file alone.
4. **K3.12 in the test and audit skills** (lane `skills-run`): neither skill tells the agent to
   call `sync_status` outright; the clause went after the first mention, the pending-migrations
   line. The anchor skill has no `sync_status` call and gained none (lane `skills-author`).
5. **K5.7** (lane `skills-run`): the text ends on a full stop, so "and ask once" became
   "Ask once.".
6. **update's shims** (lane `update`) for the time before `core` and `scaffold` merged are
   removed by integration (`751d45f6c`): the upgrade's gate refusal passes `scaffold.as_json`
   and its breaking prompt appends ` [y/N] `.

## Words chosen by a lane, word for word

No lane chose a printed line: each says every line the product prints is K1, K2 or K3's. The
words below are the ones the lanes wrote that a person reads and no contract gave.

**`core`**: the status skill's Step 1 is K3.12's clause after ``Call `sync_status` ``, which
replaced ``Call `sync_status()`.``. Rule text: RULE-92 `After a test run, the data file the
dashboard reads, `.purlin/report-data.js`, holds that run's results, with no other command run`;
RULE-93 `Each problem found resolving `.purlin/config.json` prints one line beside the status
table: a `gate` or `audit_parallel` value this release does not accept, written as JSON writes
it, with the value read instead and the fix; a `min_strength` that is not a number; and the keys
0.9.5 wrote that this release does not read`; RULE-94 `Where a spec file under `specs/` is
changed and not committed, the status report carries the line `Uncommitted spec changes:` and
under it that file's `git status --porcelain` line, indented two spaces`; skill_status RULE-11
`The skill tells the agent to call `sync_status` with the project root, the top folder of the git
checkout, as `project_root``. Reworded: states RULE-6, 8, 9, 44, 63, 64.

**`anchors`**: evidence RULE-29 `A run with no feature named selects a feature that has no section
for this machine's operating system in either source, with the reason `no run on <System> yet`,
the system written as a person reads it`; schema_spec_format RULE-25 `A name in `> Requires:`
that is a feature's spec and not an anchor is warned of, and its rules do not apply`. The example
proofs of `references/formats/spec_format.md`: `Started with no settings file, the app reports a
request timeout of `30` seconds`; `A sign-up with an email no account uses is answered with the
status `201`, and the email then appears in the list of users`; `With a report open in one
program, deleting it from another is refused with `The report is open in another program`, and
the report is still there @env(windows)`; `A file named `café.txt`, listed in a console with no
encoding set, is shown as `café.txt` @env(macos)`; `Every source file of the app is searched for
the call `eval(`, and 0 are found`; `Every source file of the app is searched for an SQL statement
joined to other text with `+` or `%`, and 0 are found`. A code comment in
`dev/test_security.py`: `Every executable language the anchor's rules name. Its > Scope: names
the three that scripts/ holds; the other three are read wherever they appear.`

**`host`**: RULE-42 `` `purlin:test --remote` looks for the program it waits on the run with,
`gh` for a GitHub remote and `az` for an Azure DevOps one, after the checks of the settings,
`ci: none`, the branch, the uncommitted tree and the Azure DevOps remote and before the push;
where the program is not on the search path it names the program to install, pushes nothing and
exits 1 ``; RULE-43 `` `purlin:test --remote` says on a line of its own that it waits for the
Azure DevOps pipeline on the run branch, that a run branch it could not delete is still on
`origin`, with the command that deletes it, and that a command it could not start failed, with
the operating system's error ``; RULE-31's closing clause `with no run registered and at the
90-minute limit it says so ...`; the spec Description's `project root check`; `workflow.py`'s
docstring first line `Render the runner file`; `ci.is_the_workspace` renamed `is_the_checkout`.

**`scaffold`**: in `skills/init/SKILL.md`: `a jest, vitest or .NET project whose Stryker is not
installed gets a line naming the command that installs it.`; `It prints every file it wrote,
kept or skipped, one per line, then asks the third question.`; ``With no such proof, init writes
no runner file and prints one line, `skipped the runner file (<reason>)`.``; ``Where a runner file
is called for, it gets one job per operating system a proof is tagged `@env` for that this
machine is not,``; `workflow` became `runner file` in 7 places; the two host-10 and host-11
examples read `Windows`. Spec text: new scaffold RULE-64 to 73, skill_init RULE-85; the
Description's `three questions`, `whether it may commit the files it wrote`, `writes the runner
file`.

**`reports`**: no report file was written; the lane's result lists no chosen words beyond its
spec text.

**`run`**: in `references/supported_frameworks.md`: `Where the run detects none, it prints:`
then run-5, then ``and `purlin:test` reads the project and proposes an entry instead.``; ``Where a
file git lists, outside `specs/` and `.purlin/`, holds the text `--doctest-modules`, the
project's own test command runs the examples inside its functions' documentation, and the
suggested command keeps running them: `python3 -m pytest --doctest-modules --ignore=mutants
{files} --junitxml={report}`.``; ``In the jest entry `{files}` comes before `--reporters`, because
jest reads every word after that option as another reporter.``; the jest row ``the package
`jest-junit`: `yarn add --dev jest-junit` where the root holds `yarn.lock`, `pnpm add --save-dev
jest-junit` where it holds `pnpm-lock.yaml`, and `npm install --save-dev jest-junit`
otherwise``; the mutmut paragraph from `docs/running-and-evidence.md` with `Linux/Unix and
macOS`. In `references/formats/evidence_format.md`: ``It opens `# Tests at <sha7>`, the commit of
the newest section across every feature, or `# Tests at <sha7>, with changes that are not
committed` where that section's `dirty` is true, and its columns are:``. Spec text: run_script
RULE-1, 2, 8, 62, 64, 67, 79 to 84; evidence_writer RULE-20, 23 to 25.

**`mutation`**: RULE-34 ``A mutmut run logs, a line each, `engine mutmut, config <section> in
<path>`, `mutmut run exited <code>` and `<n> breaks read`, then `<feature>: <n> breaks, <p>%
caught` for each feature``; RULE-35 ``A Stryker run logs `engine stryker, test runner <runner>`,
then `<feature>: <n> files broken, <p>% caught` for each feature whose report it read``; RULE-36
``A Stryker.NET run logs `engine stryker_net`, then `<feature>: <n> files broken, <p>% caught`
for each feature whose report it read``; RULE-37 ``Stryker and Stryker.NET break nothing for a
feature with no scope files, and the log reads `<feature>: no scope files, nothing to break` ``;
PROOF-92 to 100.

**`settings`**: none printed. Proof rewordings `In a project whose ...` (PROOF-134, 145),
`started in a project root` (PROOF-130), `naming a project root with `project_root`` (PROOF-128),
`the second line of the answer reads` (PROOF-7); RULE-6 `A call may name its own project root
with `project_root`...`.

**`drift`**: the example sha `1a2b3c4` in `references/drift_criteria.md`'s `anchors_behind`
line; skill_drift RULE-10 in the brief's words.

**`update`**: RULE-41 ``Before it asks anything, the update prints the pending list: `<n>
migrations pending in <root>:`, `1 migration` for one, then for each migration `  <id>: <what it
does>` and under it each file it touches, indented six spaces, the first six and then `and <k>
more` ``; RULE-42 `Each migration applied prints, once the last question is answered, the lines
saying what it did, each indented two spaces`; RULE-43 ``A run that commits names the commit on
one line, `  committed <sha> as chore(update): migrate to <VERSION> (<ids>)` ``; RULE-44 ``A
commit git refuses leaves the changes staged and prints `The changes are staged and not
committed: <git's own message>` ``; RULE-45 ``Each backup copy a migration writes is named on a
line of its own, `kept the previous bytes at <path>` ``; RULE-6 gains ``with a question ending
`[y/N]` that any answer but `y` or `yes` declines, an empty one included``; RULE-12 gains `with
its three choices` and K3.4's line.

**`signing`**: RULE-73's clause `, for any reason but work left in the committed evidence,`;
RULE-68's clause ``, reading `1 rule` and `1 case added` for one``; RULE-78 to 89 and PROOF-159
to 178.

**`review`**: in `references/review_criteria.md`: ``, as `references/spec_quality_guide.md`,
"Written for a person who cannot read code", says.``; RULE-29 ``ai_audit.py run with a
`--project-root` that is not a directory prints `ai_audit.py: <path> is not a directory.` and
exits 2``; PROOF-84 to 90.

**`package`**: none printed; RULE-20 to 24 and PROOF-41 to 54; the test file's group note
`the refusals`.

**`upstream`**: RULE-30 ``` `add` from the command line follows its first line with the count of
the anchor's rules, `  <n> rules. Run purlin:status to see them.`, or `  1 rule. Run
purlin:status to see it.` for an anchor of one rule ```; RULE-31 ``` `add` with no `--path`
writes no anchor copy, exits 2 and prints `<name>: no path into the source; pass --path` ```;
RULE-32 ``Without `--json`, `sync --check` gives an anchor that names a source and no pin the
line `<name>: names a source and no pin. Run purlin:anchor sync <name>.` ``; RULE-33 ``` `sync` in
a project where no anchor names a git source exits 0 and prints `No anchors name a git source.`
```; RULE-34 ``A `--project-root` that names no folder exits 2 and prints `No Purlin project root
found. Pass --project-root <dir>.` ``; the anchor format's example proofs ``The project's source
files are searched for a call to `eval`; the search finds 0 calls`` and the same with `exec`.

**`dashboard`**: none on the page. RULE-6 ``Affordances are the unicode glyphs `▶`, `▼`, `▲` and
`→` and no other, and the page draws no icon set``; RULE-12 adds ``the toggle, a button reading
the theme it turns to, `Light theme` or `Dark theme`, swaps ...``; RULE-26 ``naming the command
that answers it, `Type purlin:sign <feature> <RULE-N> in Claude Code.`, the command set in the
monospace face, ...`` and ``..., for each operating system the machine the tests ran on, and then
what the signature covers.``; RULE-39 whole as the lane report gives it; RULE-40 adds `with no
commit in its text and the commit in its hover`; RULE-57 ``With an uncommitted working tree the
board reads `The working tree has uncommitted changes, so what is on this board is not what a
commit would carry.` ``; RULE-58 `A theme chosen with the toggle is the theme the page opens in
after a reload`; RULE-59 `Where a hover or a screen has nothing to show, it says so in one
sentence: a spec no counting run has covered, a spec no audit has read, a spec nobody has
signed, a commit with no signed tag, a filter no rule is left under, a rule with no test, a
proof no run has listed tests for, and an open rule the data no longer holds`. The theme
button's `title` and `aria-label` were removed.

**`instructions`**: purlin_agent RULE-16 ``Where the agent definition first says to call
`sync_status`, it says to set `project_root` to the project root, the top folder of the git
checkout``; PROOF-5 and PROOF-47; purlin_output PROOF-2 `Every Python file under `scripts/` is
read with the grammar of Python 3.9; each is accepted`, PROOF-3 to 6 as in the spec.

**`skills-run`**: the usage line `purlin:test --arm-timeout <seconds>  Give each suite longer than
an hour`; `Ask once.`; skill_test RULE-18 ``The skill tells the agent that `purlin:test --remote`
with no `gh` on GitHub or no `az` on Azure DevOps pushes nothing and names the program to
install``; RULE-19 ``The skill tells the agent to pass `--arm-timeout <seconds>` on to the run
when the person gives it``; skill_test RULE-20 and skill_audit RULE-24 ``The skill tells the
agent to call `sync_status` with `project_root` set to the project root, the top folder of the
git checkout``. Cut to hold the test skill at 118 lines: ``` `purlin:build` and `purlin:audit`
call this script too. ```, ``Use it when a proof is tagged `@env` for another operating
system.`` and ``` `--remote` pulls the runner's results home at every gate. ```.

**`skills-author`**: none in the skills or references beyond the contracts; the example spec in
the spec-from-code skill gains the line `> Highest-Rule: 2`.

**`skills-sign`**: sign skill Step 5 ``and a line for each rule it signed. At the gate `signed` a
rule of a spec that names no files is signed all the same, and its line names the command that
adds them:``; Step 6 `and none over a tag that exists, where it prints`; Step 2 `Call` before
K3.12's words; RULE-18 to 21 and export RULE-12.

**`words`**: none; every sentence added is a contract's.

**P1 `shared`**: the init skill's sentence ``or, with no spec yet, on `No specs found under
specs/.` and `→ Run: purlin:spec-from-code to write the specs this code already implies.` or `→
Run: purlin:spec <name> to write the first spec.` ``.

## Calls left

Each was built as described and left for the owner or a later phase.

- `core`: fault 18's condition (above); summary RULE-10 still says "joined by ` and `", true for
  the two systems RULE-14 allows.
- `anchors`: evidence RULE-12 and RULE-13 say "one warning naming its path" and not the added
  step (their proofs quote it); an anchor's own fingerprint does not cover the anchors it
  requires, and evidence PROOF-4 no longer claims `orders` changes.
- `host`: the no-run line (host-3, host-4) says the branch was deleted and prints before the
  delete; a failed delete prints a second line. A tag naming none of the three systems is kept as
  written. RULE-12 and RULE-31 still state several claims each.
- `scaffold`: the not-committed line's `<git's own message>` is read as signing-1 reads it (copied
  into `scaffold.git_message`); setup exits 0 when git refuses the commit; the heading `A remote
  runner is written because:` prints only over a runner file written in this run; the commit takes
  only files written or copied in this run; the commit answer is lower-cased; `mutmut_paths` reads
  `git ls-files --cached --others --exclude-standard`. The lane returned `done: false` while its
  report lists nothing unbuilt; its 3 tests that waited on `host` pass on `main`.
- `reports`: `markers.py --near-misses` lists nothing with no suite set (a guard keeps that);
  reports RULE-21 still says "in a file one suite's globs match". PROOF-18, 52, 93, 113, 114 check
  their line as a substring ending at its full stop.
- `run`: `--ci` names `purlin:test` in a timeout line; a root with both `yarn.lock` and
  `pnpm-lock.yaml` keeps the npm line; a failing suite's tail no longer carries the log's
  `$ <command>` lines; run-3's step is printed for `--ci --commit` too; `--help` wins only before
  any refused token.
- `mutation`: `1 files broken`, `1 breaks read`, `<feature>: 1 breaks` keep their plural; a
  feature with no score prints `0% caught`.
- `settings`: server RULE-27 and PROOF-5, 6, 8, 9, 129, 133, 138 to 144, 159, 160, 161 still say
  `workspace` in spec text; no proof quotes settings-5; `→ Fix:` stays (plan section 11).
- `drift`: the skill directive `→ Run: purlin:anchor sync <name>`; the criteria's example `5 rules
  have no test: login RULE-1, RULE-2.` gives a count its list does not match.
- `update`: `The changes are staged and not committed: <git's own message>` has no full stop and
  no step; `  it runs on a push to a run/* branch and on a push of a signed/* tag` has no full
  stop where setup's has one; scope-advice names are sorted by name.
- `signing`: a refused signature commit leaves the signature files written and staged; a call that
  writes no signature file prints no line and exits 1; an anchor's rule never gets the no-files
  line; `--help` does not mention the no-files line.
- `review`: no `Read by` line where no audit read the rule; with `min_strength` null the terminal
  keeps `Test strength: <n> percent`; a verdict outside the three prints `<Verdict>.`.
- `package`: `export: the package was not written/committed: <why>.` keep the prefix `export:`;
  `package.py: unexpected argument <x>` is lower case with no full stop; two lines pass Python's
  error text through; a failed `git add` prints git's message over several lines.
- `upstream`: PROOF-31 holds the text and `--json` answers of one command as one case;
  `anchor_format.md`'s sentence that sync advances the pin "all in one commit" is unchanged
  though sync commits nothing; `skills/anchor/SKILL.md` now quotes upstream-4 whole, and
  `docs/specs-and-anchors.md:197` quotes its prefix (fan-out 2).
- `dashboard`: the theme button's `title` and `aria-label` were removed.
- `instructions`: purlin_output's `> Description:` still describes only the no-emoji check; the
  Python 3.9 proofs skip where no 3.9 is found, as call 18 rules.
- `skills-author`: K5.5's "first two paragraphs" read as the prose paragraph and the `git show`
  block; the spec skill's "After a merge conflict" still says "the next free number"; the
  `chore(init):` row of `commit_conventions.md` has no proof.
- `skills-sign`: the sign skill's closing table has no row for `No tag: <tag> is already
  written.`; its `No version:` row keeps `→ Write the version the person gives to VERSION, then
  run: purlin:sign`.
- `words`: the glossary's `azure-pipelines.yml` (above); `references/hard_gates.md` still says a
  rule whose spec names no files `cannot be signed`, and `RELEASE_NOTES.md` says the same, both
  false after A9; `RELEASE_NOTES.md` says init asks two things; the command reference's Syntax
  block has no `--arm-timeout` line; host-1 and host-2 sit as bullets in "A run that stops before
  running anything".
- P1: update RULE-20 still says the run ends on the summary and `Left to do`;
  `docs/getting-started.md:45` quotes the old next step (fan-out 2).
- Windows: no lane changed a test tied to a Windows proof in a way that needs a Unix call, and no
  rule carrying a Windows proof was split or renumbered.

## The lanes' self-checks

Every lane reported its five checks passed: each proof it wrote or reworded holds one case in at
most 60 words with its own marked test; each printed line is character for character K2 and K3;
no generated file staged; no id reused; three breaks each seen to fail its test and restored.
Longest proofs reported: core PROOF-53 60, anchors evidence PROOF-4 55, host PROOF-80 59,
scaffold PROOF-144 and 22 60, run PROOF-127 56, mutation 45, settings PROOF-7 52, drift PROOF-15
56, update PROOF-27 55, signing PROOF-163 58, review PROOF-29 58, package PROOF-21 49, upstream
PROOF-31 50, dashboard PROOF-54 56, instructions PROOF-5 49, skills-run PROOF-44 58,
skills-author skill_spec_from_code PROOF-8 59, skills-sign PROOF-47 48. Integration's own
rewordings: run_script PROOF-177 58, 179 to 181 55, 182 57, 91 59; reports PROOF-20 49, 88 53,
89 42; schema_spec_format PROOF-55 48; package PROOF-4 50.

The section below is `phase4-plan.md` section 12, copied whole.

## Words chosen for the owner to read

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

## The pages

Written by the second integration agent on 2026-09-30, after the four lanes of fan-out 2
(`phase4-plan.md` section 9) merged. Nothing was pushed or tagged, and no audit or signing was
run. The lanes' scratch folders, which the samples came from, are in the session scratchpad and
do not outlive it; what later work needs from them is below.

### The merges

Each lane was rebased on `main` in its worktree, `dev/test_vocabulary.py` and
`dev/test_purlin_docs.py` were run (12 passed each time), and `main` was fast-forwarded to it,
in the order `pages-start`, `pages-running`, `pages-signing`, `pages-specs`. No rebase met a
conflict.

| Lane | Commits on `main` | Files |
|---|---|---|
| `pages-start` | `51fef156f`, `2a748168b`, `eb2a49998` | `README.md`, `docs/index.md`, `docs/getting-started.md`, `docs/how-purlin-works.md`, `specs/instructions/purlin_docs.md` (new), `dev/test_purlin_docs.py` (new) |
| `pages-running` | `125c0403d` | `docs/running-and-evidence.md`, `docs/dashboard.md` |
| `pages-signing` | `128b517da` | `docs/review-and-signing.md`, `docs/regulated-workflow.md`, `docs/raising-the-gate-and-upgrading.md` |
| `pages-specs` | `cb1c3070d` | `docs/specs-and-anchors.md`, `docs/spec-from-code.md`, `docs/working-together.md`, `docs/team-workflow.md` |

### The rules the lanes handed over, as written

Each is one rule, one proof of one case in at most 60 words and a marked test of its own, in
the spec the lane named. Ids are one past the highest the spec has held (`git log -p --follow`).

| Page statement | Spec, rule, proof | Commit |
|---|---|---|
| `README.md`: Purlin makes no claim of compliance | `package` RULE-25, PROOF-55 (43 words) | `7213660d1` |
| `README.md`, `docs/getting-started.md`: the install commands | `purlin_version` RULE-16, PROOF-38 (22); `.claude-plugin/marketplace.json` joins the scope | `b651734e3` |
| `docs/index.md` and every link on the four start pages | `purlin_docs` RULE-12, PROOF-17 (38) | `0e8e970aa` |
| `docs/dashboard.md`: a notice for each warning | `purlin_report` RULE-60, PROOF-198 (38) | `d0ae8d720` |
| `docs/dashboard.md`: a second setup keeps the page | `scaffold` RULE-74, PROOF-162 (33) | `d5bd0bc2e` |
| `docs/running-and-evidence.md`: no process prompts | `host` RULE-45, PROOF-139 (36), GitHub; host RULE-38 holds Azure DevOps | `bfe6d64ca` |
| `docs/review-and-signing.md`, `docs/working-together.md`: a case is a new proof line | `skill_sign` RULE-22, PROOF-50 (49) | `fc4696b34` |
| `docs/review-and-signing.md`: never narrow a rule | `skill_sign` RULE-23, PROOF-51 (23) | `fc4696b34` |
| `docs/regulated-workflow.md`: the regulated system holds the authority to sign off | `skill_export` RULE-13, PROOF-35 (29); the rest of the sentence is a question for the owner | `a8f8e90b2` |
| `docs/specs-and-anchors.md`: `purlin:spec` commits the spec | `skill_spec` RULE-22, PROOF-51 (36) | `cdd1e01ba` |
| `docs/specs-and-anchors.md`: `create` commits as `anchor(<name>): create` | `skill_anchor` RULE-14, PROOF-35 (22) | `ea50a2a15` |
| `docs/specs-and-anchors.md`: `sync` commits nothing | `upstream` RULE-35, PROOF-59 (34) | `91adcd858` |
| `docs/spec-from-code.md`: the status reads specs before setup | `states` RULE-96, PROOF-236 (32) | `41cad3c10` |
| `docs/spec-from-code.md`: twenty to forty features | `skill_spec_from_code` RULE-49, PROOF-163 (30) | `ffbc157ba` |
| `docs/spec-from-code.md`: a proof never names the test | `skill_spec_from_code` RULE-50, PROOF-164 (36) | `ffbc157ba` |
| `docs/spec-from-code.md`: the suite's own helpers | `skill_spec_from_code` RULE-51, PROOF-165 (30) | `ffbc157ba` |
| `docs/working-together.md`: drift writes nothing | `drift` RULE-27, PROOF-66 (42) | `1361395a9` |

`purlin_docs` holds RULE-1, RULE-2 and PROOF-1 to PROOF-9, numbers an earlier spec of the same
name held before it was deleted in `f7bbdbe36` (its highest were RULE-11 and PROOF-16). The lane
left them as they are and set `> Highest-Rule: 2`; integration took RULE-12 and PROOF-17 for the
new rule and raised `> Highest-Rule:` to 12, as K4.2 reads the history.

### What integration also changed

- `c0f3a5d66`, `e8f9602a5`: at the gate `signed` a rule of a spec that names no files is signed
  and its signature does not count (A9), in `skills/spec/SKILL.md` (skill_spec RULE-9, PROOF-30
  and its test), `references/hard_gates.md`, `references/formats/spec_format.md` (the `> Scope:`
  row, wording only, no bump) and `RELEASE_NOTES.md`; the glossary's runner file on Azure DevOps
  reads `purlin.azure-pipelines.yml`, the file setup writes.
- `6634878fd`: the strength reason `strength <n>% under <m>%` shows the whole-number part
  (technical call 14), where it rounded; states PROOF-237 is the boundary, 69.6 under 70.
- `b54a9def4`: the two screenshots retaken from the rebuilt page (unchanged by the build) and
  the fixture `regulated`.

### The links and the diagrams

Every relative link on `README.md` and the 12 pages under `docs/` was followed, 113 in all:
none is broken, each `#` part matching a heading as the git host spells its anchor. The 5
mermaid blocks (`how-purlin-works.md` 11, `regulated-workflow.md` 158,
`running-and-evidence.md` 278 and 427, `team-workflow.md` 38) each parse with mermaid in
headless Chromium from the `.venv`; a broken block is refused.

### Lane `pages-start`, as it reported

#### Per page

##### `README.md`

False statements of `sanity-3.md` section 3 corrected (7 of 7): 23-24 the trust reason (one
reason now); 63 the first run (the suggestion and your confirmation are steps 4); 65-73 the
sample ending (now `3 rules. 3 pass their tests.` / `Nothing left to do.` from a run); 76-77 the
failing run (the `fails` line and `Left to do` from a run); 95-97 the tag (when nothing is left
to do and every result came from committed work); 97-98 `[level: passed]` (cut); 111
`purlin:sign` row (syntax and purpose from `references/purlin_commands.md`, and every other row
the same). Section 4 items 1 and 3: the path uses `purlin:spec` and `purlin:build`; `If you
leave, the markers are comments.` is gone.

Cut: the six sample lines; `A single rule can ask for less with [level: passed]`; `Plain
language reaches every one of them ... The syntax above is canonical, never required.` (no rule;
the command reference says it); `--scope project records the marketplace in the project's
.claude/settings.json, so a teammate ... runs the install and the reload once.` (Claude Code's
behaviour; no rule).

Statements: 31. Covered by a named rule: 26 (scaffold RULE-1, 8, 13, 18, 21, 22, 24, 34, 36, 47,
51, 67, 68, 69; purlin_output RULE-2, 3; run_script RULE-3, 5, 11, 20, 55, 61, 63, 67, 68;
skill_spec RULE-3, 6; skill_build RULE-2, 5, 12; skill_test RULE-7; states RULE-39; signatures
tag rules; purlin_docs RULE-1, 2). Framing or navigation with no behaviour: 3 (the first
sentence, the package as an input to a regulated system, the Documentation links). Handed to
integration: 2 (below).

##### `docs/index.md`

Corrected (4 of 4): 26 `the two reasons` to `the one reason`; 39 `The level, the queue, ... what
stales a signature` to `What the audit found, purlin:sign and the rules it walks, a check by
hand, the tag, and when a signature counts`; 61 `choosing a level` to `reading the cell that
blocks a rule`; 62 `the test command init writes for it` to `the tests entry it suggests for
each`. Also: how-purlin-works' cell `The chain in one diagram ... what red means` reads `The three
steps in one diagram ... when a run exits 1`; `The gate decides how far every rule must go.`
reads `The gate is the last step every rule must reach before a version is finished.`

Cut: `Every entry is one sitting's read.`

Statements: 27 (the intro, the gate paragraph, the gate table, 24 table rows). Covered: the gate
paragraph and table (hard_gates, scaffold RULE-1, 36). The table rows describe other pages; they
are navigation, held true by reading those pages, and every link resolves. Handed: 1 (links).

##### `docs/getting-started.md`

Corrected (13 of 13): 14-15 the `tests` setting (setup leaves it empty; the first run suggests);
19-20 the trust reason; 42-44 the trust question (the three questions, from K3.9 and scaffold
RULE-1); 44 setup reads the framework (cut; the first run does); 45 the old next step (now the
run's two lines, quoted); 88 the first run (quoted with its suggestion, and the confirmation as a
step); 92-94 the blank line (quoted from the run); 106-113 the sample ending; 116-117 the
failing run; 149-151 `--commit` (two commits, the work then the evidence); 154-155 `→ Next:` (the
first line of `Left to do`, or `Nothing left to do.`); 175 the tag condition; 178
`[level: passed]` (cut). Section 4 items 1 and 2: the path uses `purlin:spec` and
`purlin:build`; the steps to remove Purlin are gone.

Cut: `If you leave, the markers are comments. Delete .purlin/, specs/, ... exactly as they
did.`; `Init reads your test framework from the tree`; the typed spec and the typed tests;
`purlin:audit calls a model on each rule and a finding blocks.` (reworded to the glossary);
`purlin:init --gate strong raises the gate and writes what the new gate needs; it changes no
rule.` (reworded to scaffold RULE-12).

Statements: 52. Covered by a named rule: 50 (as for the README, plus run_script RULE-62, 64;
skill_test RULE-15, 17; skill_build RULE-7; skill_spec RULE-5, 15; states RULE-92; drift rules
for `purlin:drift eng`; evidence RULE-29 and run_script RULE-55 for the selection;
evidence_writer RULE-19 for the two commits; summary rules for the summary; reports rules for the
comment syntax per language). Handed: 1 (the install commands, shared with the README).
Navigation: the "Where to go next" links.

##### `docs/how-purlin-works.md`

Corrected (22 of 22): 8-9 and 32-39 levels (cut; every rule is asked what the gate asks); 11-26
the diagram (redrawn: no levels, no `meets the gate`; a rule ends on nothing left, or on left to
do with its command); 30 queue and signature at `passed` (a hand check is signed at any gate);
50-52 the walk (at every gate) and the tag condition; 60 `proven` (`finished`); 62-63 the tag
line (`Tagged signed/<version> at <sha7>.` then the push line); 63-64 the conditions for no tag;
80-81 what a signature binds (six things); 81-82 what it records (name, email, time, key
fingerprint, not the machine); 82-84 `stale` (ends with no message, `unsigned`, `to sign`);
94-96 two reasons and `trust: remote` (one reason); 96-97 the Linux job (one job per tagged
system this machine is not, and no other); 104-106 the tag run (runs the tests, writes nothing);
112-114 and 123-125 the endings (summary and `Left to do`); 125 exit 1 (the full list); 131 and
132-133 the signature and the tag conditions; 135-140 "What does a level do?" (replaced by "What
keeps a rule from the gate?"); 148-149 `not audited` (gate `strong` and up, no audit entry for the
current hashes); 151-152 build work and the queue (`to audit`; `to strengthen` or `to measure`).
Also `<os>: no run yet` reads `Windows: no run yet`, with `to test on Windows`.

Statements: 58. Covered by a named rule: 56 (states RULE-15, 36, 39 and the cell rules;
signatures rules on what a signature binds and records, the walk, RULE-70 and the tag
conditions; scaffold RULE-13, 15, 42, 57; run_script RULE-11, 12, 47, 61, 62, 65, 66; host rules
for `--remote`; evidence_writer RULE-19; states RULE-92; hard_gates' `Left to do` kinds through
the summary rules). Framing: 2 (the page's opening sentence; `A tag holds the whole tree at that
commit`, which is git's own).

#### The scratch runs the samples came from

Scratch folder `<scratchpad>/p4-pages-start`:

- `sample1/`: `python3 dev/test_purlin_docs.py <scratch>/sample1`, which builds the sample the
  test builds and prints each run (`sample1.out`). Every `text` block on the pages is taken from
  it: `setup` (setup at `--gate passed --yes`), `first-run`, `confirmed-run`, `commit-run`,
  `failing-run`, `no-tool`.
- `run2/`: setup with no `--gate`, answering `passed` then `y`: the gate question
  `What must be true of every rule before a version is finished?` and its three choices.
- `walk2/`: the path followed again from the page in a fresh project with the plugin's own
  launcher, `scripts/purlin_python.sh`: setup's last lines and the first run's two lines match.
- `wtcopy/`: a copy of the tree with the new spec, run with `--feature purlin_docs` for the
  marker count.

Lines in prose that are forms, not quotes of one run: `Selected 1 of 1 feature: cart (code
changed since <sha7>).` (sample1 printed `0632354`); `Suggested tests setting: [...]` (abridged);
`chore(init): set up Purlin at the gate <gate>`, `purlin: specs, tests and settings for
<feature>`, `purlin: evidence at <sha7>`, `Tagged signed/<version> at <sha7>.`, `Nothing left to
do. Push the tag to release it: git push origin signed/<version>` (the contracts and
`references/hard_gates.md`; the signed flow needs an audit, which needs a model, so it was not
run); `Spec saved: cart. Next: purlin:build cart` (the spec skill's closing line).

#### Failures and differences in files I do not own

- `purlin_run.py --test --commit` with nothing selected and only `.purlin/config.json` changed
  commits the work as `purlin: specs, tests and settings for`, with no feature after `for`
  (sample1 `commit-run`, commit `04c74dd`; also `run2`). The pages give the subject as
  `purlin: specs, tests and settings for <feature>`.
- `skills/spec/SKILL.md` and skill_spec RULE-9 still say that at the gate `signed` the rules of a
  spec naming no files "cannot be signed" (false after A9), beside `references/hard_gates.md`
  and `RELEASE_NOTES.md`, which the interfaces already list.
- `references/glossary.md` names `azure-pipelines.yml`; my page names
  `purlin.azure-pipelines.yml`, the file setup writes (scaffold RULE-57).
- None failed in the fast sweep.

#### Words I chose

Every sentence below is mine; no code, glossary entry or decision gives it word for word.

README.md:
- `Purlin is a Claude Code plugin for spec-driven development. You write the rules your software must follow, one comment above a test ties it to a rule, and Purlin runs your own test command and tells you which rules pass over the code as it is now.`
- `A team can ask for more: an AI audit of whether the tests are sound, and a person's signature on each rule, with a signed git tag on a finished version.`
- `Purlin keeps that evidence in the repository, for the people who build the software and for whoever signs it off; where sign-off happens in a regulated system, Purlin's evidence package is an input to it.`
- `A settings file, the specs and the evidence: ..., and a copy of the dashboard page, purlin-report.html, which that block keeps out of git.`
- `Your own test command, in your own framework, with the flag that makes it write a report. The first test run suggests it, and you confirm it.`
- `A commit when you agree to one: setup asks before it commits the files it wrote, and a test run commits its results only with --commit.`
- `Nothing running unless you ran it: no git hook, and no Purlin process left running after a command ends. A runner file for the git host is written only where a proof is tagged for an operating system this machine is not.`
- `Nothing added to your test suite.`
- `Set up. Type purlin:init. Answer passed to the gate question and yes to committing the files it wrote. In a project with no code yet it ends:`
- `Write the rules. Type purlin:spec cart and say what the feature does. It shows you the rules and the proofs it drafted, commits the spec once you agree, and ends on ...`
- `Build. Type purlin:build cart. It writes the code and a test for each proof, with one comment above each test naming the proof, commits them, and runs purlin:test cart. The first test run in a project has no test command to run, so it suggests one:`
- `Say yes. The command is written into .purlin/config.json, the tests run, and the run ends:`
- `Read it. Where a test fails, here the test of RULE-2, the run names the rule and the test, ends on what is left to do, and exits 1:`
- `Change the code the spec covers and its rules are out of date; the next purlin:test runs them again and names what changed.`
- `The gate is the last step every rule must reach before a version is finished, and each step has one command:`
- `From strong up, every rule needs a proof, a plain sentence saying how the rule is shown, and the comment above its test names the proof. purlin:sign walks the rules waiting for a person and, at the gate signed, once nothing is left to do and every result came from committed work, writes the evidence package and the signed tag signed/<version>.`
- `No file setup writes into a project names the folder Purlin ran from, so a project is the same on every machine.`

docs/getting-started.md (beyond the README's):
- `A settings file, the specs and the evidence. ... It prints every file it wrote, then asks whether it may commit them. On a yes it commits them in one commit, chore(init): set up Purlin at the gate <gate>.`
- `The comment ties the test to a proof, and the proof names its rule. Where a rule has no proof, the comment names the rule: # purlin: cart RULE-1.`
- `Your own test command, in your own framework. Setup leaves the tests setting empty. The first purlin:test suggests an entry for each test tool it recognises, with the flag that makes the tool write a report Purlin reads, and the entries are written once you confirm them. For pytest the command is ..., starting py -3 on Windows.`
- `A commit when you ask for one. A test run writes its results and commits them only with --commit.`
- `Nothing running unless you ran it. No git hook, and no Purlin process left running after a command ends. A runner file for the git host is written for one reason: a proof tagged @env for an operating system this machine is not.`
- `Nothing added to your test suite. No plugin, no import, no fixture. The one exception is the test tool's own: jest needs jest-junit to write its report, and the first test run prints the command that installs it.`
- `The path below starts in a Python project whose pyproject.toml configures pytest and that holds no code yet. Each step shows what you type and the lines the step ends on. The rules and tests the model writes are your own and differ from run to run, so this page shows none of them.`
- `Set up. Type purlin:init. It asks up to three things:` / `the gate, ..., with the choices passed, strong and signed. Answer passed.` / `at strong and signed only, and only where a tool that can do it exists for your test framework, whether to break the code on purpose to measure test strength.` / `whether it may commit the files it wrote. Answer yes.`
- `It names each file it wrote, copied or skipped:` / `Then it commits them, names the commit and each file in it, and ends on the next step:`
- `In a project that already holds code, the last line names purlin:spec-from-code, which writes the specs that code already implies:`
- `Write the rules. Type purlin:spec cart and say what the cart must do: a sentence, a ticket or a list of criteria. A rule is one line saying what the software must do, and a proof says how that is shown, in words a person who cannot read code can judge. It prints the rules and proofs it drafted for you to read, writes them to specs/<category>/cart.md with a > Scope: line naming the files the code lives in, commits the spec once you agree, and ends on:`
- `Build. Type purlin:build cart. It writes the code into the files > Scope: names and a test for each proof, with one comment above each test naming the proof, where no existing test already shows it. It commits them, with a body saying which rule each change serves, and runs purlin:test cart.`
- `The first test run in a project has no test command to run. It runs nothing, suggests an entry for each test tool it recognises, then prints the whole setting on one line, Suggested tests setting: [...]:`
- `Where your project runs its tests in another way, with another interpreter or other options, the agent shows you the difference. Say yes to the entry you want: the agent writes it into .purlin/config.json and runs the tests again. The run prints:` / `and then the status of every rule, which is what it ends on:`
- `Where the first run recognises no test tool, which for pytest means no conftest.py, no pytest.ini and no [tool.pytest section in pyproject.toml, it prints:`
- `supported_frameworks.md lists the test tools it recognises and the entry it suggests for each.`
- `Read it. 3 rules. 3 pass their tests. is the summary: how many rules there are and how many passed their tests. Nothing left to do. means no rule has anything left at the gate passed. Open purlin-report.html in a browser to see each rule on its own line; it reads the results of the last run.`
- `Where a test fails, here the test of RULE-2, the run names the rule and the test:` / `It ends on what is left to do, and exits 1:`
- `... and the run's first line says why it picked the feature, Selected 1 of 1 feature: cart (code changed since <sha7>)., naming the commit the last run saw. Run it once more with nothing changed and it runs nothing:`
- `purlin:spec <name> turns a requirement into rules and proofs.` / `purlin:test runs the features the change touched: those whose spec, code or tests changed since their last run, and those with no run on this operating system.`
- `purlin:test --commit makes two commits under your own git identity: first the specs, the marked tests and the settings the results describe, as purlin: specs, tests and settings for <feature>, then the evidence, as purlin: evidence at <sha7>, naming the first.`
- `Every run ends on the summary and Left to do. The first line of Left to do is the next step and names its command; a project with nothing left at the gate passed or strong ends on Nothing left to do.`
- `running-and-evidence.md covers a run in full, including the one reason a project has a remote runner: a proof tagged for an operating system this machine is not.`
- `The gate is the last step every rule must reach before a version is finished. There are three:`
- `From strong up every rule needs a proof, which QA writes or reads and the audit checks the test against. purlin:audit has a model read each rule, its proofs and its tests; a finding makes the rule weak, and it is left to do as to strengthen. At signed a person signs each rule, and purlin:sign writes the signed tag signed/<version> once nothing is left to do and every result came from committed work.`
- `purlin:init --gate strong raises the gate. The specs, the tests and the evidence stay as they are, and the summary gains a step.`

docs/how-purlin-works.md:
- `It is the shortest description of the whole thing: one rule, three steps, and who takes each one.`
- `A rule goes through up to three steps, in this order, each containing the one before: passed, strong and signed.`
- the diagram's labels `nothing left to do for this rule`, `left to do,<br>with the command that does it`, `yes, gate passed`, `yes, gate strong or signed`, `yes, gate strong`, `yes, gate signed`
- `The answer to each step is a cell, and a cell exists only at or below the gate, so a project at passed shows no test strength and no Strong or Signed column. A proof marked @manual is checked by a person, who signs the rule with purlin:sign, at any gate.`
- `purlin:sign with no argument walks the rules waiting for someone to test by hand or to sign, at every gate; at signed, once nothing is left to do and every result came from committed work, it writes the evidence package and the tag.`
- `purlin:test --remote is the one command that pushes, and it pushes a run branch of its own, never the branch you are on.`
- `The tag marks a finished version.` and `It writes no tag while anything is left to do, while the working tree or a feature's results are not committed, or over a tag that already exists, and none below the gate signed.`
- `purlin:test --commit commits the specs, the marked tests and the settings the results describe, then the evidence as purlin: evidence at <sha7>, ...`
- `A signature is a person's attestation that a rule, its proof, its test, the code its feature lists, what the audit found and the machine the tests ran on for each operating system belong together. ... A change to any of the six ends it, with no message: its cell reads unsigned and the rule is left to do as to sign.`
- `purlin:init writes a runner file, .github/workflows/purlin.yml on GitHub or purlin.azure-pipelines.yml on Azure DevOps, for one reason: a proof in specs/ is tagged @env for an operating system the machine running setup is not. It holds one job for each such system, and no other.`
- `The runner file runs on a push to a run/* branch and on a push of a signed/* tag. purlin:test --remote creates the run branch, waits for the run through gh on GitHub or az on Azure DevOps, ... A runner runs only the tests tied to proofs tagged @env for its own system, and no audit. A pushed tag starts a run that runs those tests on a clean machine and writes nothing.`
- `What does a run end on? The summary, one count per step up to the gate, such as 3 rules. 2 pass their tests., then Left to do, one line per kind of work left with its count and its command. The first line of Left to do is the next step. A project with nothing left ends on Nothing left to do. at passed and strong, and at signed on the line naming the push of the tag. getting-started.md shows both endings from a real run.`
- `purlin:test runs the marked tests the change touched and writes what they saw, and the dashboard shows that run's results the next time you open it;`
- `When does purlin:test exit 1? When a tied test failed or did not run, evidence is missing, a comment above a test names nothing a spec has, the settings file is missing or cannot be read, the project was set up by Purlin 0.9.5 and not upgraded, or no test command is set. A test run cannot make an audit or a signature appear, so a rule waiting for one never makes it exit 1. purlin_commands.md lists every command's exit codes.`
- `What keeps a rule from the gate? At passed: a failed test, a rule with no test, a result that is out of date, a rule whose tests passed on one operating system and failed on another, or a system that has not run its tests. At strong: a rule with no proof, no audit of the current rule, proof and test, a finding or a test strength under the minimum, or a @manual proof no person has checked. At signed: no signature that still counts. Each is a line of Left to do, with the command that clears it.`
- `... and is left to do as to write a proof for, with purlin:spec.`
- the rewritten `not audited` / `weak` paragraph, and `..., until that system runs it, and the rule is left to do as to test on Windows, with purlin:test --remote.`

docs/index.md: the five cells and the sentence quoted under "Per page" above.

### Lane `pages-running`, as it reported

#### docs/running-and-evidence.md

Corrected, every row of sanity-3 section 3 for this page: 9 (the remote push named), 51-76 (sample taken from a
run: Proofs column, `3 rules. 3 pass their tests.`, `Nothing left to do.`), 89-91 (two commits), 94-98 (ends on
the summary and `Left to do`), 130 (the same rules at every gate), 143-145 (two commits; no strength line), 146-147
(stale line gone), 149-150 (the one `AI audit: ... read` line, then the table, summary, `Left to do`), 151-152
(exit 1 above `passed` when a rule read is weak or not audited), 159-168 (diagram: work committed before the
evidence is written), 191-196 (the one-line marker message, from a run), 203 (exit codes: the test run exits on
the tests alone, plus the four stop causes, link to purlin_commands), 270-273 (a code change ends a signature;
`unsigned`, `to sign`), 288 (package and tag when nothing but the tag is left and results are committed), 380-381
(delete command only where the delete fails, and after the Azure 90 minutes), 241-244 (mutmut advice replaced by
a link to supported_frameworks.md#pytest), 308-310 (setup's `skipped the runner file (...)` line, from a run).
Also found and corrected: the first-run step (empty `tests`, suggestion, confirmation), the Selected/Skipped
lines, the Stryker.NET row (`dotnet test`, not xUnit only), `min_strength` null while off, the no-engine reason,
`strength not measured` and `to measure`, the gh/az check before the push, the runner-file lines setup prints.

Cut: "Takes: seconds / one model call per rule, plus the breaks" row; "Most have none. At every gate a rule
reaches passed, strong and signed on your machine."; the exit-code table; "the matrix" wording.

Rules named, by section: intro and table: run_script RULE-3, 45, 49, 51, 73, 75, host RULE-12. First run:
run_script RULE-61, 62, 63; skill_test RULE-7, 17; scaffold RULE-52. Which features run: run_script RULE-55, 56,
78, 57, 58; evidence RULE-29. What a run prints: run_script RULE-82, 68; reports RULE-1, 16; evidence_writer
RULE-1, 8, 9, 10, 19, 21, 4; scaffold RULE-67 (runtime ignored). How a run ends: run_script RULE-11, 65, 66, 70,
61, 62, RULE-1; hard_gates (summary, Left to do). A failing test: run_script RULE-5, 40, 67. Other OS: run_script
RULE-10; states RULE-6, 43, 44, 57; evidence_writer RULE-3. Loud failures: reports RULE-17, 18, 31; run_script
RULE-8, 79, 80. A comment that names nothing: reports RULE-19; run_script RULE-11; hard_gates `to_correct`.
purlin:audit: ai_audit RULE-1, 2, 3, 4, 5, 6, 16; run_script RULE-48, 49, 50, 51, 52, 54, 76; states RULE-89;
evidence_writer RULE-12, 18. Flow: run_script RULE-68; evidence_writer RULE-19, 10. Test strength: mutation
RULE-1, 3, 8, 18, 19, 23, 27, 29, 14, 32, 22; scaffold RULE-2, 45, 46 (PROOF-45, 86 read `auto`); run_script
RULE-45, 72, 73, 74, 75; states RULE-12, 13, 77. Evidence: evidence RULE-11, 13, 14, 15; evidence_writer RULE-1,
4, 6, 8, 12, 20, 24; states RULE-7; hard_gates "When a signature counts". Runner: scaffold RULE-13, 53, 57, 65,
15; host RULE-18, 19, 28, 32, 39, 12, 36, 33, 42, 43, 31; run_script RULE-12, 47, 75; evidence_writer RULE-16.
About 180 sentences and 16 table rows; each is under one of the rules above, cut, or handed over below.

#### docs/dashboard.md

Corrected, every row of section 3 for this page: 12-13 (re-run keeps the page; `--update` replaces it), 28-30
(count gone), 30-31 (`signed/1.4.0`, commit in the hover), 31-32 (no commit box), 32-33 (`Data: <age>`, hover
text quoted), 35-36 (tabs), 44-46 (no levels), 40 and 147 (the two captions describe the retaken images: the board
with login open and RULE-4 unfolded, and login RULE-1's page), 49-55 (boxes `No proof`, `Passing` with
`<n> RULES TOTAL`, `Strong`, `Signed`), 64/71/77/80 (`16 (+6)` and decision 90's hover), 66 (`Windows`/`Linux/Unix`),
68 (signed over every rule, no stale), 72 (top bar counts nothing), 83 (no Queue tab), 95-96 (badges per step
reached and `FAILED`), 102, 104-106, 108 (waiting on the rule screen), 125-126 (one button at a time), 128-138 (the
filter buttons are the `Left to do` lines, with the `Type <command> in Claude Code.` line), 138-139 (`No rule is
left of this kind.`), 150-153 (no Level row), 157-158 (`Lin`, `Mac`, `Win`), 161 (Audit panel at the gate
`strong` and above), 163-164 (nothing of strength where none was measured), 170-172 (hand check panel names
`Type purlin:sign <feature> <RULE-N> in Claude Code.`, at `signed` only), 177 (`Back to the board`), 179-198 (the
Queue section gone). Also: `last_line` in place of the buttons when nothing is left; links only to a GitHub remote.

Cut: "the tiles, the filters and the top bar count each rule once" (top bar counts none); "at signed none of its
rules can be signed" (A9); "The data file is generated and never committed" (no rule names report-data.js in
`.gitignore`).

Rules named: purlin_report RULE-2, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 21, 22, 24, 25, 26, 27, 28, 29, 31, 35, 36,
37, 39, 40, 41, 42, 43, 44, 46, 47, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59; scaffold RULE-67, 18; update RULE-31, 6.
About 120 sentences and 7 table rows; each under one of these, cut, or handed over.

#### Scratch runs the samples came from

Scratch folder `/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/faec174d-b9c7-49bb-b61f-60ffdfcb84eb/scratchpad/p4-pages-running`.
`samples.sh` builds three projects with `make_demo.sh` (setup through `scripts/init/scaffold.py --yes`, the spec
and the marked tests written by hand as `purlin:spec`/`purlin:build` would) and writes each output to
`samples/<name>.txt`; `samples.final/` is the run the page copies. Git dates are pinned, so shas repeat.

- `demo` (gate `passed`): `first-run` (the suggestion block), `commit-run` (the full sample and `Committed
  373225b`), `tests-md` (the table), `nothing-to-run`, `failing` (the fails line and the ending), `wrong-marker`
  (the comment line and `Left to do`), `windows-proof` (`1 proof needs Windows ...`), `proof-no-test` (`cart
  RULE-2 has no test for PROOF-5 ...`).
- `team` (gate `strong`): `audit`, with `dev/fake_claude.py` installed first on the search path (checked before
  the run); the real `claude` program was never started.
- `remote` (gate `strong`, `@env(windows)` proof, origin `/nonexistent/github.com/example/demo.git`, which no
  network reaches): `setup-runner` (the runner-file lines), `remote-no-gh` (PATH without `gh`: the refusal line).
  A second run with `gh` present failed its push against the local path and printed `Pushing main as
  run/main-274713c.`; nothing reached a git host.
- `g1` (gate `signed`, key made with `ssh-keygen` in the scratch folder, `gpg.format ssh`): audit with the stand-in,
  `sign.py cart RULE-1`, then the page looked at headless with playwright (`look.py`). `fin`: a finished project's
  board (`Nothing left to do.` in place of the buttons).
- The two screenshots staged in scratch from `dev/capture_doc_screenshots.py`'s own `SHOTS` and fixture
  (`shots.py`, `dashboard-board.png`, `dashboard-rule.png` in the scratch folder); captions written from them.
  The built page (`dev/build_report.py`'s `build()` into scratch) is byte-identical to the committed
  `scripts/report/purlin-report.html`.

#### Sentences I wrote that no code, glossary entry or decision gives

- "For the developer who runs Purlin, and for anyone who reads the evidence afterwards." (kept from the page)
- "Both call one run script, `scripts/run/purlin_run.py`, so there is one answer to how a test is run." (kept)
- Table header "The step it answers" and row "Reads each rule with a model | no | yes, one call per rule".
- "Setup leaves the `tests` setting in `.purlin/config.json` empty. The first run finds the test tools the project
  uses, runs nothing, and suggests an entry for each:"
- "A run of a project with one feature and three marked tests, with `--commit`, reads:"
- "A failing test is a result: the evidence records it as `fail`." / "The run ends on the table and:" / "A rule some
  of whose proofs have no test is named the same way:"
- "A test framework that runs nothing says nothing about it, so the run script checks two things the frameworks
  cannot check themselves." (kept) and "Each prints a line starting `Evidence is missing:` and makes the run exit 1."
- "An audit of a project at the gate `strong` in which the model found one gap reads, after the tests:"
- "Both commands take the same steps on your machine, and the audit adds one:" and the diagram node "with
  --commit, commit the specs,<br>the marked tests and the settings".
- "It is what a teammate reads on the git host without running anything:"
- "Use it for the reason above. It pushes a branch of its own, never the branch you are on:" (kept)
- Dashboard: "The page has two screens: the board, and one rule."; "Every screen carries the same top bar:";
  "The board then opens on the boxes."; "A column above the gate is absent, not empty."; "A step not reached draws
  nothing: why it was not reached is on the rule's screen."; "The page opens dark until you choose."; "The panel
  reports and recommends nothing." (kept); the two image descriptions, whole; the Next line "signing the rules
  the page names".

#### Faults found in files this lane does not own (left as they are)

1. `scripts/run/purlin_run.py` `_nothing_to_run`: `--test --commit` with nothing selected makes a first commit with
   the subject `purlin: specs, tests and settings for ` (no feature named) holding `.purlin/config.json` alone,
   and leaves the changed spec and marked tests uncommitted (`work_paths({}, features, [])`). Seen in a scratch
   run: `e57dbd2 purlin: specs, tests and settings for`.
2. `scripts/report/src/app.js` `auditLines`: with mutation testing off (`min_strength` null) the `Strong` box and
   column hover read `minimum strength 0%`.
3. `scripts/report/src/rule.js` `proofDetail`: a `@manual` proof reads `No test yet. Type purlin:build <feature> in
   Claude Code.` although a hand check needs no test.
4. `scripts/mcp/purlin/states.py` line 668: `strength %d%% under %d%%` rounds the strength; technical call 14 says
   the whole-number part (floor) on every surface.
5. `purlin_run.py --audit --commit` prints two blank lines between the committed paths and
   `AI audit: <n> rules to read, <k> at a time.`

### Lane `pages-signing`, as it reported

#### Per page

##### docs/review-and-signing.md (about 90 statements: 76 sentences, 16 table rows)
Section 3 corrected: the queue became the two `Left to do` lines the walk reads (signatures RULE-11); the tag condition is "nothing but the tag left and every result committed" (RULE-45, 46, 49, 55); hand checks at every gate (RULE-12, PROOF-92); levels gone; broken `hard_gates.md#the-level` link gone; opening line and stop heading from a real run (RULE-11, 82, 83, 84); signed-cell words `signed`/`unsigned`/`waiting`; ended signature reads `unsigned` with no message (RULE-6, 7); other work named by its own command; the `passed` refusal lines removed; the close from a real run (RULE-58, 68, 87); version order (RULE-56); tag lines (RULE-70); refusal table (RULE-46, 49, 55, 57, 66, 73, 74, 80, 65); tag run writes nothing (run_script RULE-47, host RULE-28); `--all` not `--batch` (RULE-12); by-name output (RULE-58, 62, 64); no `strong` warning line; no-scope rule signed with the A9 line (RULE-78); no trust setting; no-key lines (RULE-17), no `commit.gpgsign`, no key upload; six things bound, fields (RULE-9, 42, 50); counting (RULE-20, 21, 23), every gate; a code change ends it (RULE-6, PROOF-84), sample from a real run.
Cut: the level section, the queue header, `stale` rows, "Changing the code alone stales nothing", the upload sentence, the `${CLAUDE_PLUGIN_ROOT}` ai_audit command line (replaced by what the skill does, skill_sign RULE-12, ai_audit RULE-17), "a rule from an anchor is changed in the anchor's own repository".

##### docs/regulated-workflow.md (about 61 statements)
Corrected: signature records no signing machine and no level, six things, a change ends it (signatures RULE-6, 9, 50, 61); tag when nothing but the tag is left (RULE-45, 46); version order (RULE-56); tag lines from a real run (RULE-70); package state `finished`/`not finished`, no `not_for_approval` (package RULE-3, 4, 5); settings `gate`, `mutation_engine`, `min_strength` (RULE-3); no level field; signature fields per package RULE-13; nothing verified, any key (RULE-20); loop on one machine unless an `@env` proof for another system; diagram now asks "anything but the tag left?" then work not committed, results not committed, a version stated; setup prints no signing setup, `purlin:sign` prints it (RULE-17); signing is not refused over uncommitted evidence, only the tag (RULE-49); no-scope rule signed with its line (RULE-78); `@manual` waits as `to test by hand`, note optional (RULE-68).
Cut: "What your git host must protect" (A11), the `commit.gpgsign` block, "Three things Purlin does not do" list (kept as one sentence), "`purlin:sign` refuses to sign over evidence".
Package statements: package RULE-1, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 15, 17.

##### docs/raising-the-gate-and-upgrading.md (about 80 statements: 65 sentences, 15 table rows)
Corrected: one reason for a runner (scaffold RULE-13); no `--dry-run` anywhere; settings have seven keys, `tests` empty, no `specs/_anchors/` (RULE-5, 50, 51); no levels, no queue, hand checks at every gate; setup prints no signing setup; runner jobs one per tagged system this machine is not (RULE-15); an unaudited rule is `to audit`; tag needs nothing but the tag left; upgrade asks gate then mutation only at strong/signed, no trust question (update RULE-12, 26, 37, 38); last step is the test run (scaffold RULE-58); pending list printed first (update RULE-41); ending as status (RULE-20); exit codes (RULE-4, 40). Gate question now reads `finished` (scaffold-2), from a real run. The commit question (A10, scaffold RULE-68, 69) shown from a real run.
Cut: the plugin cache path and `--plugin-dir`, "The proof files ... deleted without a copy", "Nothing under specs/ loses a rule or a proof".

#### Scratch runs (under p4-pages-signing/)

Key `keys/jane` made with ssh-keygen; HOME `home/`; PATH with the fake `claude` first and no real one; `mkproj.sh` builds a login project (pytest, 3 rules, one `@manual`), `mkold.sh` the 0.9.5 fixture with a local bare remote.
- `shop` (signed, set up with `--yes`, tests setting written, test --commit, audit --commit with the fake model): `walk1.txt` (walk), `tag.txt` (tag), `refuse-work.txt`, `tag-exists.txt`, `check.txt`.
- `shop-a`: `note.txt`, `norule.txt`, `all.txt`. `shop-k` (no key): `nokey.txt`. `shop-noscope`: `nofiles.txt`. `shop-c` (code change): `codechange.txt`. `shop-v`: `refuse-version.txt`. `shop-x`: `export.txt`, `package-notfinished.json`.
- `shop-gate`: `gate-passed.txt`, `raise-strong.txt`, `raise-signed.txt`, `lower-passed.txt`; `shop-gate-m`: `mutation-on.txt`; `shop-runner` (Windows proof, remote `remotes/github-shop.git`): `runner.txt`.
- `old` (0.9.5 fixture): `upgrade.txt`, `old-run.txt`.
`check_samples.py` checks every output block on the pages against these; `check_links.py` checks every link.
Lines quoted from the code or a rule rather than a run: `No tag: <feature> has results that are not committed. Run purlin:test --commit.` (RULE-49; no real flow left results uncommitted while signatures still counted), the package and git refusals (RULE-73, 80, 66), `skipped the runner file (there is no git remote, ...)` (scaffold RULE-54), the update commit and "Nothing is pending" lines with `<VERSION>` (update RULE-43, PROOF-33), kept as placeholders so no release number sits on the page.

#### Sentences I wrote that no code, glossary entry or decision gives

- "`purlin:sign` is how a person signs."
- "A rule is on one line of `Left to do` at a time, the first that applies, and every other line names another command"
- "at the gate `signed`, every other kind of work on the rule is done and no signature counts for it as it stands"
- signed-cell table: "a signature that counts matches the rule as it stands"; "none does: none was made, or what one was made over changed"
- "A walk at the gate `signed` over three rules, answered `sign`, `case` and `sign`:"
- "The walk is what writes the tag."
- "A signature that ends says nothing"
- "the package, read from the committed evidence, finds work left"
- "An export while two kinds of work are left:" / "and the file it wrote begins:"
- "Its `state` comes second, after the schema, so an export of work in progress reads `not finished` before anything else."
- "which signers were entitled is the regulated system's to decide"
- "It runs on one machine unless a proof is tagged `@env` for a system that machine is not; then `purlin:test --remote` has a remote runner prove it."
- Diagram node words: "anything but the tag left?", "work not committed?", "results not committed?", "a version stated?", "No tag: the summary and Left to do".
- "Raised from `strong` to `signed`, with the commit question answered `y`:"
- "A project on GitHub with one proof tagged `@env(windows)`, set up on a Mac:"

#### Calls left, and failures in files I do not own

- `references/hard_gates.md` lines 200-202 still say a rule whose spec names no files "cannot be signed"; after A9 it is signed and does not count (noted by integration 1 too).
- Running the status (`status.sync_status`) on the 0.9.5 fixture reached the network: its Figma-sourced anchor made git ask `https://www.figma.com/...` and print `remote: Not Found`. I ran it once, by mistake, to read the pending advisory; nothing else in this lane reached a network service. A status on a project with an https `> Source:` makes a network call; the fixture carries such a source.
- `purlin:sign --all` that signs the last rule leaves `the version to tag`; only a second `purlin:sign` writes the tag. The page says so as it is.
- A result that is uncommitted while every signature still counts proved hard to reach in a real flow (a rerun with no change writes identical evidence), so the RULE-49 line is quoted from the rule.
- No test failed in a file I do not own.

### Lane `pages-specs`, as it reported

#### Per page

##### docs/specs-and-anchors.md (86 sentences, 5 table rows)

False statements of sanity-3 section 3 corrected: 47 (headings matched without regard to case,
schema_spec_format RULE-12); 53 (`> Scope:` required at `signed`); 63-65 (code change: the
signature ends, the cell reads `out of date`); 65 (rule text change ends the signature, `to sign`);
78-89 (no tag on a rule line; bracketed text is rule text, specs RULE-3); 91 (`> Highest-Rule:`,
never reused, schema RULE-26, skill_spec RULE-2, 13); 118 (proof optional only at `passed`);
129-130 (note optional, `--note` when given); 196 (`sync` commits nothing; the line quoted whole
with its commit step); 197-198 (the signature ends). Also: example proofs 38-40 and 102 rewritten
to the quality guide (PROOF-1..3 from the spec skill's shape, a new PROOF-4 for the 15-minute
boundary, PROOF-3 absence proof from `spec_format.md`); the `@env` example from `spec_format.md`;
the reason `Windows: no run yet`; `> Requires:` names anchors only with the anchors-1 warning;
the no-files case at `signed` said as the code does it (signed, does not count, `to tie to its
files`); the `(+2 shared)` count.
Cut: "There is no separate syntax for it" (description by denial); "A signature logs the level";
the level table; "a spec with no scope ... its rules cannot be signed".
Rules named for the rest: schema_spec_format RULE-1, 12, 14, 15, 17, 19, 25, 26, 27, 28, 9, 10;
specs RULE-3, 11, 13, 14; evidence RULE-25; states RULE-6, 16, 26, 62, 63, 64, 72, 75, 1;
signatures RULE-6, 7, 13, 78; run_script RULE-20, 55; purlin_report RULE-52; skill_spec RULE-2,
3, 6, 13, 15, 16, 17, 18; skill_anchor RULE-5, 6, 7, 9, 10, 11, 12, 13; upstream RULE-1, 2, 8,
11, 24, 26, 28, 30 (PROOF-25, PROOF-36 quote the add and sync lines); drift RULE-10, 12.

##### docs/spec-from-code.md (42 sentences, 3 table rows)

Corrected: 13-14 (status reads specs before setup; a test run stops, line quoted); 18-19 (rules
from what the test expects, passing or not; skill_spec_from_code RULE-9); 36-37 (the report's
contents, RULE-36, 8, 7); 41, 51-52 (no level in the example; `> Highest-Rule: 2`, RULE-39);
60-61, 81 (level paragraphs cut); 96-97 (a failing rule stays failing until the code is fixed).
Added from the skill: the branch check (RULE-35), shared rules in an anchor first (RULE-37), the
commit with the comments (RULE-34), the position file's shape (RULE-33), the five reasons
(RULE-8), commented-out tests and benchmarks (RULE-38), what a caller reaches (RULE-10, 48), the
ending in order (RULE-3). Cut: "No rule for a private helper", "No level above passed", the
re-mark paragraph. Other rules named: RULE-2, 6, 40, 41, 42, 43, 44, 45, 46, 47; run_script
RULE-65, 61; scaffold RULE-34; reports RULE-3 (markers read with no suite).

##### docs/working-together.md (34 sentences, 3 table rows)

Corrected: 17-18 (the boxes `No proof`, `Passing`, `Strong`, `Signed`, purlin_report RULE-8);
18-19 (`.purlin/tests.md` from every evidence file on disk, evidence_writer RULE-8); 32, 36
(no queue; the walk reads `to test by hand` and `to sign`, signatures RULE-11, 16); 36 (hand
checks at every gate, states RULE-75); 37-39 (the two kinds); 69 (eng sample from a real run,
every rule the feature owns, drift RULE-7); 87-88 (after a clone the last 20 commits, drift
RULE-3); 95 (qa view: changed test files, then the two lines, at every gate, drift RULE-15, 22).
Cut: "loaded from the marketplace or with `claude --plugin-dir <checkout>`" (no rule; setup
names no plugin folder, scaffold RULE-21, but where Claude Code loads a plugin from is not
Purlin's). Other rules named: skill_spec RULE-3, 6; signatures RULE-21, 50, 68, 72; skill_anchor
RULE-11; drift RULE-2, 4, 5, 6, 8, 9, 10, 14, 17; skill_drift RULE-10.

##### docs/team-workflow.md (59 sentences, 8 table rows)

Corrected: 6-8 (with mutation on and nothing measured the cell is `weak` with
`strength not measured: <reason>`, states RULE-77, 78); 22, 27-28 (no levels; the audit reads
each rule with a proof, a passing test and no audit for its current hashes, run_script RULE-49);
29 (`purlin:sign <feature>` signs its rules waiting for a person, signatures RULE-12); 30
(`--all`); 36-47 (diagram: a case goes to `purlin:build`; paths for `no proof`, strength not
measured and no code files); 57-58 (order: `AI audit: <n> rules to read`, evidence lines, then
`AI audit: <n> rules read ...`, run_script RULE-50, 54, quoted from a run); 58-59 (no
test-strength line); 60-61 (ends on the summary and `Left to do`, RULE-11); 61 (exit 1 when a
test failed or did not run, or a rule read is weak or could not be audited, RULE-48); 65-67
(one reason for a runner file); 80 (`weak` also `to measure` and `to tie to its files`); 86-87
(`no mutation score measured` only with mutation off or an engine that cannot run here, states
RULE-13); 89-90 (`to test by hand`; the walk opens on the `Left to do` line or `Nothing is
waiting ...`, signatures RULE-11); 113 (the walk closes with `Walked ...` however much is left,
RULE-68, quoted from a run); 123-125 (signature over rule, proof, test, code, audit, machines,
signatures RULE-6, 61); 125-126 (`unsigned`, states RULE-20). Cut: "Level 1 ... level 2" wording;
"trust this machine"; the queue header. Other rules named: scaffold RULE-2 (70), RULE-67
(`.purlin/runtime/` ignored); states RULE-4, 11, 12, 14, 16, 18, 89; run_script RULE-51, 57, 60;
evidence_writer RULE-10, 23; signatures RULE-8, 58, 87; skill_spec RULE-17.

#### Scratch runs (under `<scratchpad>/p4-pages-specs/`)

- `run1/shop` (gate `strong`, pytest): setup, the first run's suggestion, `--test --commit`,
  `--audit` against the stand-in model (`fakebin/claude`, `dev/fake_claude.py install`, never the
  real program): the audit block and ending on team-workflow. `run1/policies(.git)` the anchor
  repository; `add` from it: the add lines. `run1/dev` a teammate clone of `run1/origin.git`
  reset to `b9f91d5` and pulled: drift `pm`, `eng`, then `--test` and `qa`; `sync --check`
  and `sync security_baseline`: the pin lines.
- `run2/shop`: a doubled `RULE-2` and `> Requires: security_baseline, export`: the two warnings.
- `run3/shop` (gate `signed`, SSH key `key/id` made with `ssh-keygen`): `export` with no
  `> Scope:`: the no-files line; `sign.py export RULE-1` printed
  `  export RULE-1   does not count until the spec names its files: purlin:spec export` and the
  rule stayed `to tie to its files`.
- `run4/shop` (gate `strong`): the walk over one hand check: the closing three lines.
- `run5/api` (gate `passed`): status and run before setup, setup's ending, the status once the
  spec and marker are written; `run5/nosetup/api` the status with specs and no setup.
- `samples.sh` rebuilds every state above under `check/` and writes `check/out/*.txt`;
  `compare.py` checks each quoted block line for line (relative times and the `Commits:` sha
  normalised): `15 samples, 0 lines differ`. `links.py` checks every link and anchor.
  `mparse.py` parses the mermaid block with mermaid in headless Chromium from the `.venv`.

#### Sentences written that no code, glossary entry or decision gives

specs-and-anchors: "A spec with no `> Scope:`, or one whose entries reach no file git tracks, names no files."; "At the gate `signed` a rule of such a spec can be signed, but the signature does not count: the rule is left to do as `to tie to its files`, and no tag is written until the spec names them."; "`purlin:spec` takes the next rule and proof ids against both the working copy and `origin/main`'s copy, so a number already on `origin/main` is not taken again on a branch."; "In the status table a feature's `Rules` cell counts the rules it owns and then the anchor rules it proves, as `4 (+2 shared)`; the summary counts each rule once, under the spec that owns it."; "It commits nothing: you commit the copy in one commit with that subject, so the diff shows which rules moved."; the example proof "PROOF-4 (RULE-3): 15 minutes after the fifth wrong password, the right password is answered with `200`".
spec-from-code: "Set the project up first."; "`purlin:status` reads the specs either way."; "The skill commits as it goes, so it checks that the checkout is on a branch first."; "Before the first test run the status already counts the marked tests as work to run:"; "A rule that reads `failed` stays: it says what its test expects, and it reads `failed` until the code is fixed."; the headings "A proposed list of features", "Shared rules first", "The tests it leaves untied"; the example `{"features": ["rate_limit", "export"], "written": ["rate_limit"]}`.
working-together: "The dashboard's boxes count the rules that reached each step the gate asks for, `Passing`, then `Strong` from the gate `strong` up and `Signed` at `signed`, with a `No proof` box first from `strong` up."; "`.purlin/tests.md` is the table of the newest run of each feature, written from every evidence file on disk, committed or not."; "A rule is `to test by hand` at every gate while a `@manual` proof of it is not checked, and `to sign` at the gate `signed` once its tests pass and its audit is strong."; "After a pull, `purlin:drift eng` names what moved and the command for each:"; "the signature records your name and email as git holds them and the fingerprint of your key, and Purlin does not decide who may sign."; "The `qa` view prints those lines at every gate; at `passed` only a rule to test by hand waits for a person:".
team-workflow: "The passed cell asks whether the marked tests passed; the strong cell asks whether the AI audit found those tests sound."; "A run over tests that already match their evidence runs none of them and still reads every rule the audit has not read:"; "The strong cell reads one of six words, and each names who moves it next. `weak` has three causes, each with its own fix."; "The walk closes on what it did, however much is left:"; the diagram labels "the strong cell", "weak: a finding, or strength under the minimum", "no proof, or no code files in the spec", "weak: strength not measured", "the command the reason names", "a case: a new proof line".

#### Calls left, and failures in files not owned

- The page's `> Source:` example names `https://github.com/acme/policies.git` beside the real
  pin of the run (`71abd36...`), whose source was a local bare repository: it is file content in
  the anchor format's own example form, not a printed line.
- `upstream.py add <local path without .git>` writes a `> Source:` line that `sync --check` and
  drift then read as "not a spec in Purlin's format kept in a git repository" (exit 2):
  `specs.parse_source` splits the path off only after a value ending `.git` or a URL scheme.
  The runs used `policies.git`.
- `skills/spec/SKILL.md` ("its rules cannot be signed and no tag is written"),
  skill_spec RULE-9, and `references/formats/spec_format.md`'s `> Scope:` row say a no-files
  rule cannot be signed at `signed`; the code signs it and the signature does not count
  (signatures RULE-78). The page follows the code.
- Relative times (`0 seconds ago`) and `Commits: bc0f607` are quoted as printed; the comparison
  normalises them.


## Decision 99

Built on 2026-09-30 by five lanes and one integration agent, after the owner's answers to the
five open questions of the handoff (`three-levels.md` decision 99). Each lane's report is in the
session scratchpad, `reports-99/<lane>.md`. Nothing was pushed or tagged, and no audit or signing
was run.

### The merges

Each lane was rebased on `main` in its worktree, its own test files were run, and `main` took it
by fast-forward, in this order:

| Lane | Commit on `main` | Own tests after the rebase |
|---|---|---|
| `d99-proofs` | `c8e0c2ebe`, `39363505e` | 152 passed |
| `d99-run` | `7ce1aacae` | 268 passed, 1 skipped (with `test_schema_spec_format.py`) |
| `d99-scaffold` | `4fea0d670` | 143 passed |
| `d99-dashboard` | `73fa739e0` | 180 passed |
| `d99-export` | `e834c1e39` | 15 passed |

`d99-run`, `d99-scaffold` and `d99-dashboard` each conflicted on one place: the spec's header,
where `d99-proofs` had added `> Highest-Proof:` beside the old `> Highest-Rule:`. Each was
resolved in the lane's worktree during the rebase to the lane's `> Highest-Rule:` and the highest
proof the lane took, the values the lanes reported: `run_script` 85 and 258, `scaffold` 75 and
166, `purlin_report` 62 and 202. `skill_export` took `d99-proofs`' 13 and 35 with no conflict.
Every one of the 36 specs was then checked by script: each carries both lines, and neither is
below the highest id the spec holds.

### What was built, and the ids

- **A proof number is never reused.** The spec format is at version 20: the template and the
  metadata table gain `> Highest-Proof:`, and "Proof format" says how a proof number is taken.
  Every spec under `specs/` carries `> Highest-Proof: <n>` after `> Highest-Rule:`, `<n>` the
  highest `- PROOF-<n>` line in the spec's `git log -p --follow` history; in every spec that
  equals the highest proof it holds today. `schema_spec_format` RULE-29, PROOF-67 to PROOF-70;
  `skill_spec` RULE-23, PROOF-52 and PROOF-53, with PROOF-2 losing its proof-id clause. The
  spec skill's "Ids" and `docs/specs-and-anchors.md` say it. No code allocates ids: the agent
  does, through the spec skill, so PROOF-69 and PROOF-70 check the worked examples on the format
  page.
- **The 78 tests that fail on Windows and that no rule is tagged for** are left as they are.
  Nothing was built.
- **The export instructions say what the system of record holds.** The export skill's sentence
  gains the controlled document and the signature that counts under the regulation.
  `skill_export` RULE-13 and PROOF-35 were rewritten in place under their own ids; the docs page
  already carried the three things and is unchanged.
- **A committing run that selected nothing** commits every changed spec, marked test and
  `.purlin/config.json` in one commit. `run_script` RULE-85, PROOF-256 to PROOF-258. The subject
  names each feature whose spec or marked tests it holds, and reads
  `purlin: specs, tests and settings` where it holds only the settings.
- **Two lines on the dashboard.** `purlin_report` RULE-61 with PROOF-199 (mutation testing off),
  RULE-62 with PROOF-200 to PROOF-202 (a proof checked by hand).
- **Setup leaves test fixtures out.** The one test-tool detection, used by setup, the upgrade
  and the first test run, skips every folder named `fixtures`, `fixture`, `samples`, `sample`,
  `testdata`, `test_data` or `test-data`, at any depth. `scaffold` RULE-75, PROOF-163 to
  PROOF-166. On this repository the detection now reads `pytest` alone where it read `pytest`
  and `dotnet`.

### Integration's commits

- `96d2e42dd docs: the evidence format names the subject of a run that selected nothing;
  evidence format 6`. The run lane changed what a run emits and left
  `references/formats/evidence_format.md` naming only the subject with features. Format-Version
  5 to 6, since a reader of the history now meets a second subject.
- `094f811d5 docs: the release notes name > Highest-Proof: and spec format 20`. The release
  notes said the spec format was at version 19.
- The dashboard page rebuilt and committed once. The two screenshots were not retaken: the
  fixture they are taken from has mutation testing on and no `@manual` proof on either screen, so
  neither changed line shows in them.

### The sweep and the run

- Full sweep, `bash dev/run_tests.sh`, at `094f811d5` (every lane merged and integration's two
  docs commits in; `f0130e44b`, a slide builder change another session committed during the
  sweep, touches no test): `2291 passed, 3 skipped in 729.29s (0:12:09)`,
  `>>> All Pytest Tests: PASSED`, `Suites: 5 passed, 0 failed`; the four shell suites passed.
- This repository through its own tool, `python3 scripts/run/purlin_run.py --test --all` at
  `5f002e00e`, exit 0: `Markers: 2333 tied to a test, 0 not tied.`, `Ran pytest, shell on 36
  features.`, `86 proofs need Windows; this machine is macOS. Run purlin:test --remote.`,
  `Evidence written to .purlin/evidence/local/ for 36 features.`, then
  `891 rules. 867 pass their tests. 0 are strong. 0 are signed.` and `Left to do:` /
  `  24 rules to test on Windows: purlin:test --remote` / `  867 rules to audit: purlin:audit`.
  No rule reads `partial`, `failed` or `no test`, and no warning prints. The 24 are the rules
  with a Windows proof in the features decision 99 changed, whose remote evidence from
  `665f4dbb8` is now out of date. With `--commit` the same lines, `Evidence committed.` after
  the evidence line, and one commit, `b46c93f01 purlin: evidence at 5f002e0`. With `--commit`
  two blank lines stand between the Windows line and the evidence line, where the run without
  it prints one.

### Words chosen, word for word

Integration:

- `references/formats/evidence_format.md`: "A run that selected nothing to run still makes the
  first commit, of every spec, every test file carrying a marker and `.purlin/config.json` that
  changed. Its subject names each feature whose spec or marked tests it holds; where it holds
  only the settings, the subject is:" followed by `purlin: specs, tests and settings`.
- `RELEASE_NOTES.md`: "A spec records the highest rule number it has held in `> Highest-Rule:`
  and the highest proof number in `> Highest-Proof:`, so a deleted number is never used again.
  The spec format is at version 20."
- Commit subjects: `docs: the evidence format names the subject of a run that selected nothing;
  evidence format 6`, `docs: the release notes name > Highest-Proof: and spec format 20`,
  `chore(purlin_report): the dashboard page, built from the sources of decision 99`,
  `chore(three-levels): decision 99 built`.

`d99-proofs`:

- Format template: `> Highest-Proof: <the highest proof number the spec has held>`
- Format table: "The highest proof number the spec has ever held, as a whole number. A new proof
  takes the next number above it, so a deleted number is never used again. It changes no
  fingerprint and no count"
- Format prose: "Proof ids are never reused either. A new proof takes one more than the highest
  of `> Highest-Proof:` and every proof number the spec holds, and `> Highest-Proof:` is raised
  to it, so a number is never used again." "A spec whose `> Highest-Proof:` reads `12` and whose
  `PROOF-10` to `PROOF-12` were deleted, leaving `PROOF-9` its highest, gives its next proof
  `PROOF-13`." "A spec with no `> Highest-Proof:` line whose proofs run to `PROOF-9` gives its
  next proof `PROOF-10`."
- Spec skill: "A new proof takes one more than the highest of `> Highest-Proof:` and every proof
  number in either copy; write that number into `> Highest-Proof:`, adding the line after
  `> Highest-Rule:` where it is missing."
- Docs table: "The highest proof number the spec has ever held". Docs paragraph: "Proof numbers
  are never reused either: a new proof takes one more than the highest of `> Highest-Proof:` and
  every proof number in the spec, and `> Highest-Proof:` is raised to it. `purlin:spec` reads
  both copies of the spec, the working copy and `origin/main`'s, for both numbers."
- `schema_spec_format` RULE-29: "`> Highest-Proof: <n>` records the highest proof number the spec
  has ever held; a new proof takes one more than the highest of it and every proof number the
  spec holds, so a deleted proof's number is never used again; it changes no fingerprint and no
  proof count"
- `skill_spec` RULE-23: "The skill tells the agent that a new proof takes one more than the
  highest of `> Highest-Proof:` and every proof number in either copy of the spec, and to write
  that number into `> Highest-Proof:`, adding the line after `> Highest-Rule:` where it is
  missing"
- Proof texts: `schema_spec_format` PROOF-67 to PROOF-70 and `skill_spec` PROOF-52, PROOF-53, as
  the specs hold them.

`d99-run`:

- Commit subject with no feature: `purlin: specs, tests and settings`
- `run_script` RULE-85: "When such a run selects nothing, `--commit` first commits every spec,
  every test file carrying a marker and `.purlin/config.json` that changed, in one commit whose
  subject is `purlin: specs, tests and settings for <feature>[, <feature>…]`, naming each
  feature whose spec or marked tests it holds, or `purlin: specs, tests and settings` where it
  holds only the settings; where none changed it makes no such commit"
- PROOF-256 to PROOF-258, as `specs/run/run_script.md` holds them.
- `references/commit_conventions.md`: "A run that selected nothing to run still commits, in the
  first commit, every spec, every test file carrying a marker and `.purlin/config.json` that
  changed. Its subject names each feature whose spec or marked tests it holds, and reads
  `purlin: specs, tests and settings` where it holds only the settings."
- Docstring of `_nothing_to_run`: "No test runs. `--commit` still commits every changed spec,
  marked test and the settings in one commit, then the evidence an earlier run wrote, because
  that is the command a refused tag names."

`d99-scaffold`:

- `scaffold` RULE-75: "Deciding which test tools a project uses, setup leaves out every file
  under a folder named `fixtures`, `fixture`, `samples`, `sample`, `testdata`, `test_data` or
  `test-data`, at any depth, so it names only the tools the project itself uses"
- PROOF-163 to PROOF-166, as `specs/init/scaffold.md` holds them.
- `references/supported_frameworks.md`: "It also skips every folder named `fixtures`, `fixture`,
  `samples`, `sample`, `testdata`, `test_data` or `test-data`, at any depth: a project kept there
  to test against is not a tool this project uses, so setup and the first test run name only the
  project's own."
- Comment in `frameworks.py`: "Folders of test fixtures, samples and test data, at any depth: a
  project kept there to test against is not a tool this project uses."

`d99-dashboard`:

- `purlin_report` RULE-61: "With mutation testing off, the `Strong` cell's hover and the
  `Strong` box's hover read `no minimum strength applies: mutation testing is off` in place of
  the minimum strength"
- `purlin_report` RULE-62: "A `@manual` proof no test carries reads under its tests, on the
  board's unfolded row and on the rule's screen alike, `Checked by hand. Type purlin:sign
  <feature> <RULE-N> in Claude Code.`, the command in the monospace face, and `Checked by hand.`
  alone once a signature records the rule's hand check"
- The page line `Checked by hand.` alone, once the rule's hand check is signed. The other page
  lines are decision 99's.
- PROOF-199 to PROOF-202, as `specs/dashboard/purlin_report.md` holds them.

`d99-export`:

- Export skill: "A reviewer who cannot open the repository reads it in the system of record,
  which holds the controlled document, the authority to sign it off and the signature that counts
  under the regulation."
- `skill_export` RULE-13: "The skill tells the agent that the package is read in the system of
  record, and that the system of record holds the controlled document, the authority to sign it
  off and the signature that counts under the regulation"
- PROOF-35: "The export skill, its line breaks read as spaces, carries the words `reads it in the
  system of record, which holds the controlled document, the authority to sign it off and the
  signature that counts under the regulation` word for word"

### Calls left

- **No allocator and no proof of a doubled proof id.** No code allocates ids, so no function was
  built; decision 97 warns of doubled rule ids only, so a proof number written twice is not
  warned of.
- **The spec-from-code skill's example spec and `docs/spec-from-code.md`** carry no
  `> Highest-Proof:` line. They are still valid, since a spec with no line counts from its
  highest proof. `docs/team-workflow.md` says two branches may take the same `RULE-N`, and does
  not say the same of `PROOF-N`.
- **The build skill** never says how an id is chosen and stands at its 130-line ceiling; it is
  unchanged.
- **The docs page on the regulated workflow** says "the regulated system" where the export skill
  says "the system of record", and no proof holds the page to the three things. The row
  `docs/regulated-workflow.md` in "The pages" above still calls the rest of the sentence a
  question; decision 99 answered it. `references/purlin_commands.md`'s `purlin:export` row does
  not say what the system of record holds.
- **The subject with no feature** is a constant in `scripts/run/purlin_run.py`, not beside the
  other subject in `scripts/run/evidence.py`, whose `commit_work` would still write
  `purlin: specs, tests and settings for ` if it were handed no spec; nothing calls it that way.
  `references/purlin_commands.md`'s `purlin:test` row and `evidence_writer` RULE-19 name only
  the shape with features.
- **A committing run that did select features** still commits only their specs and tests; a
  changed spec or test of a feature it did not select stays uncommitted. Decision 99 names only
  the run that selected nothing.
- **Folder names match exactly, in lower case**: `Fixtures`, `Samples` and `TestData` still
  count. PROOF-165, a JavaScript sample, passes with or without the change, since Jest and
  Vitest are found at the root only; it stands as a guard. The upgrade's own walk for v0.9.5
  xUnit logger lines and setup's walk that chooses mutmut's folders do not skip fixture folders;
  neither chooses a test tool.
- **The dashboard.** RULE-37 still says the `Strong` hover names the minimum strength; RULE-61
  states its exception. With mutation testing on and no `min_strength`, the hover reads
  `minimum strength 0%`, which only the gate `passed` could show, where no `Strong` column is
  drawn. A `@manual` proof that lists tests shows its tests. "Already signed" is read from the
  payload's `hand_checked`.
