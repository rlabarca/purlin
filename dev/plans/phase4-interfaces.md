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
