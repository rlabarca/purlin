# Handoff, 2026-10-01: decisions 100 to 117 are built

This section is the newest; everything under "Handoff, 2026-09-30" below describes the tree before the build and is kept until the owner has read this. The same text is `dev/plans/d115-reports/round2.md`; round 1 is `round1.md` beside it, and each lane's report is there too.

`main` is local only. The code, the tests, the skills, the docs and the dashboard meet the specs: 39 specs, 417 rules, 845 proofs.

### The numbers

`bash dev/run_tests.sh` on the Mac, with `dotnet`, `go`, `npm`, `sqlite3`, `ssh-keygen`, Python
3.9 and playwright present, run twice, the second time after the last code fix:

| | Passed | Failed | Skipped |
|---|---|---|---|
| Pytest, every `dev/test_*.py` but `dev/test_install.py` | 838 | 0 | 10 |
| Shell suites | 3 | 0 | 0 |

The 10 skipped are tests that only a Windows machine can show: `config_engine PROOF-39`,
`evidence PROOF-75`, `package PROOF-39`, `host PROOF-117`, `scaffold PROOF-130`, `132`, `136`,
`update PROOF-117`, `118`, `120`. Nothing skipped for a missing tool. Read in the sweep's output
as run and passed: the walks from setup to the signed tag for Python, TypeScript and C#
(`scaffold PROOF-36`, `37`, `93`, `94`, `95`, `119`), `update PROOF-31`, the `dotnet`, `go`,
Jest and Vitest report captures, `run_script`'s `sqlite3` case, `purlin_output PROOF-4` and
`PROOF-5` on Python 3.9, and every playwright test. After the sweep one proof was added
(`purlin_report PROOF-237`); the dashboard's three test files then read 71 passed.

`bash dev/run_tests.sh --install`, once: 5 passed, 0 failed, 0 skipped, in 8.5 seconds, with one
prompt to the smallest model.

`python3 scripts/run/purlin_run.py --test --all --commit`, then `--test --commit` after the
header line changed. The last run ends:

```
Markers: 845 tied to a test, 0 not tied.
...
Purlin status: purlin, plugin 0.10.0
Tests: not met
Sign-off: not signed
...
417 rules. 395 pass their tests.
Left to do:
  22 rules to test on Windows: purlin:test --remote
```

39 specs, 417 rules, 845 proofs, 845 test comments. No rule reads `failed`, `partial` or
`no test`; no spec to repair; no test comment to correct; no warning. The evidence is
committed. Appendix A's script over every `dev/test_*`: `0 gone, 0 reworded, 845 right as they
stand.`

**The real `claude` ran twice, not once.** `--test --all` runs `dev/test_install.py` (plan
section 10), and step 10's state cannot be reached with `install` not run. The run without
`--commit` was made with the real `claude` taken off the path, so its four install proofs
skipped there and it read `4 rules to test`; the run with `--commit` made the one extra prompt.
The later `--test --commit` did not select `install`.

Cloud spend: $79 of the $80 decision 116 allowed ($48 in round 1 for six lanes, $31 in round 2 for four); $42 of $250 is left, expiring 2026-11-05. The final sweep on the last commit: 839 passed, 0 failed, 10 skipped (Windows only), 4 suites passed.

### The spot tests over this repository's own tests

No model. 20 findings at the start, all from check 6, `The test never checks the result the
proof expects`; 0 at the end. Every finding was read.

- **16 cleared by narrowing the check** (`scripts/review/plain_checks.py`, three narrowings):
  a value a Python test writes across adjacent string literals is read as Python joins them
  (11 findings); a value written `NAME=value` or `Name: value` is held where the file holds
  both sides as two strings (3: `host PROOF-91`, `101`, `105`); a value holding a
  `<placeholder>` is held where the file holds each of its other parts (1: `update PROOF-4`);
  and `summary PROOF-44` cleared with the first. `drift PROOF-58` is counted under the tests.
- **4 cleared by fixing the test**: `drift PROOF-58` builds its pattern from the literal line;
  `package PROOF-45` writes the whole printed line; `purlin_report PROOF-122` reads the page
  under `scripts/report/` itself; `run_script PROOF-117` asserts the path
  `.purlin/evidence/ci/feat.json`.

`references/review_criteria.md`, "Heuristic spot tests", is not changed. The three narrowings
are for the owner to accept or take out.

### The review of the fixed tests

Three reviewers that fixed none of them read 136 tests against their proofs: every `fixed`
one, the `stated` ones sampled, the proofs added, decision 117's and `collaboration PROOF-1`.
They agreed with 131. Fixed: `purlin_report PROOF-3` (asserts `--canvas:` is declared),
`PROOF-15` (asserts the passed row's own word), `PROOF-235` (asserts `Before` and `After` as
written), `drift PROOF-40` (the reason names the path, not the file name alone). Left for the
owner: `host PROOF-53`.

### What integration changed

| Commit subject | What |
|---|---|
| `fix(states): the payload's warnings open on the settings warning ...` | the one line in `payload.build_payload`: `warnings = list(settings_warnings(config))` |
| `fix(states): wording.py hands git its commits after --end-of-options ...` | the two fallback reads `anchors` named |
| `docs(run_script): the --ci arm's docstring ...` | no tag run, no breaks |
| `docs: the sign-off's and the audit's lines as decision 117 words them, and the dashboard page as built` | `skills/sign`, `skills/audit`, `docs/sign-off.md`, `docs/running-and-evidence.md`, `references/evidence_and_signoff.md`, `references/purlin_commands.md`, `docs/dashboard.md` |
| `chore: the sweep holds dev/test_install.py out ...` | `dev/run_tests.sh` gains `--install`; `dev/windows_skip.sh` deleted with the suite that sourced it |
| `chore: setup is called with no gate ...` | `dev/manual/check_spec.py`, `.gitignore` (no `mutants/`), `dev/conftest.py`'s note, `--ignore=mutants` out of this repository's own settings |
| `test(collaboration): PROOF-1 ...` | `dev/test_collaboration.py`, 13 seconds, no model |
| `docs(deck): ...` | `dev/plans/deck/build_deck.py`; not published |
| `fix(plain_checks): ...`, three `test(...)` commits | the spot tests and the review, above |
| `fix(purlin_report): a long path in a panel wraps at 390 pixels ...` | the look, below |
| `feat(purlin_report): the header line shows the time in the viewer's own timezone and names it` | the owner's instruction of 2026-10-01, below |
| `chore(purlin_report): the page built from its sources`, `docs: the two dashboard screenshots ...` | generated files |

Lanes: each wrote only what it owns. `d117` wrote round 1 files and four specs; `dashboard`
added `purlin_report RULE-78` and `PROOF-234` to `236`. No rebase conflicted. The stale
mentions of `references/hard_gates.md` and `dev/test_vocabulary.py` were already gone once
`remote` and `setup` were rebased onto the merged line. K13 is kept as the dashboard lane built
it: a missing page is written only where git ignores it or the root is no git checkout.

### The header line's timezone (the owner, 2026-10-01)

The data keeps `generated_at` in UTC. The page converts it in the browser: the header reads
`<branch> at <commit>, written <hh:mm> <zone>`, 24-hour, the zone the browser's short name or
its offset. Changed: the header line and its hover; the Audit panel's `Read by <model> on
<date> <hh:mm> <zone>`, which was the one other clock time the page shows. Left: every age
(`19 days old`), which is no clock time; a hand check's note, which shows a version, a signer
and a count of commits. Under 600 pixels the line may break between the checkout state and the
time, never inside either; at 390 pixels it stays on one line for `EDT` and `UTC` and takes
two for `GMT+5:30`. The tests set the browser's timezone, `UTC` unless a proof names another,
and `dev/capture_doc_screenshots.py` takes its pictures in `UTC`.

### Spec edits integration made, word for word

`specs/dashboard/purlin_report.md`, on the owner's instruction:

- `RULE-77`, reworded: The top bar names the checkout state its data describes and when it was written, as `<branch> at <commit>, written <hh:mm> <zone>`, as in `main at a1b2c3d, written 06:42 EDT`: the branch and the first 7 characters of the commit the writing command ran on, and the time, 24-hour, in the timezone of the person looking at the page, named by the browser's short name for it or, where it has none, by its offset, as in `GMT+5:30`. Its hover gives the date and time in full in that zone, then the UTC time, as in `2026-10-01 06:42 EDT (10:42 UTC)`. The data keeps its stamp in UTC, and the line is unchanged while the page is open
- `PROOF-232`, reworded: Open the board with the regulated sample, its data written on the branch `main` at the commit `a1b2c3d` and stamped `2026-10-01T10:42:13Z`, in a browser set to `America/New_York`; the top bar reads `main at a1b2c3d, written 06:42 EDT`, its hover reads `2026-10-01 06:42 EDT (10:42 UTC)`, and after the page's clock runs on 2 hours the line reads the same
- `PROOF-237 (RULE-77)`, new: Open the board with the regulated sample, its data stamped `2026-10-01T10:42:13Z`, in a browser set to `UTC`; the top bar reads `main at a1b2c3d, written 10:42 UTC`
- `> Highest-Proof:` 236 to 237.

No other spec was edited by integration. The lanes' own spec edits are in `d117.md` and
`dashboard.md`.

### The dashboard, looked at

Playwright, headless, dark and light, at 1500, 1024 and 390 pixels, this repository's own data
after the `--commit` run and the three fixtures, the board, the board with a spec open and a
rule's page: 72 screenshots, each measured for sideways scroll, a value on two lines and
neutral text under 7 to 1.

- Found: at 390 pixels the Audit panel's evidence path, `.purlin/evidence/local/checkout_design.json`,
  ran out of its panel and the page scrolled sideways by 38 pixels (team) and 11 (regulated).
  Fixed: a paragraph in a panel wraps a long path.
- Found: with the zone `GMT+5:30` the header line was cut at 390 pixels. Fixed as above.
- Left: at 1024 pixels the anchor's name reads `security_no_dangerous...`, cut with an ellipsis;
  its row's hover gives the path. At 1024 the two boxes share the top bar's one row on this
  repository's data.

### Lines a person reads that integration chose

| Line | Where |
|---|---|
| `Two lines in a terminal, from the README: add the marketplace, then claude plugin install.` | the deck, `Start in under ten minutes`, row 1 |
| `Runs your tests and prints 3 rules. 3 pass their tests.` | the deck, the same slide, row 5 |
| `Purlin workflows` | the deck's title, which read `Purlin gate workflows` |
| the deck's notes: the install as the two shell lines; `The first test run suggests the test command for the framework it finds, and you confirm it once.`; `... while files are changed and not committed, or while a rule has no test, and names what to run.`; `which model was asked`; `... and each command that writes its data keeps it current.` | speaker notes of `start`, `signoff`, `regulated`, `touches` |
| `The first line counts tracked files alone, 1 file is for one; a file git does not track stops nothing.` and `purlin:build <feature> for a rule with no test` | `skills/sign/SKILL.md`, step 2 |
| `... means claude could not be reached. A rule a spot test fired on is still written weak; any other rule prints <feature> RULE-N   not audited and gets no audit entry, since strong means the model's part of the audit ran.` | `skills/audit/SKILL.md`, step 2 |
| the reasons beside the three new refusals: `tracked files are changed and not committed; for one it reads 1 file is. A file git does not track stops nothing`; `a committed result was taken over files that were changed and not committed`; `a rule has no test, with or without a proof line`; `a rule fails or has not run` | `docs/sign-off.md`, "What it refuses" |
| `A checkout with no page yet, a fresh clone for one, gets it the same way, as long as git ignores the page, which purlin:init sets up.` | `docs/dashboard.md`, "Opening it" |
| the header line's paragraph, ending `The Audit panel's Read by line shows its time the same way.`, and the Audit panel's sentences on the explanation, `Before` and `After` | `docs/dashboard.md` |
| `usage: dev/run_tests.sh [--fast \| --install]` and the suite name `The install the docs give` | `bash dev/run_tests.sh` |
| the two test labels of `dev/test_collaboration.py`'s output, `--- <person>: <command> (exit <n>)` and `--- <person>: the tool <name>` | shown by pytest when that test fails |

### Left unbuilt

Nothing a spec names is left unbuilt. The deck's pictures are rendered under
`dev/plans/deck/` and not committed: `.gitignore` ignores `*.png` outside `docs/images/`, and
the three older pictures there (`slide-passed.png`, `slide-signed.png`, `slide-strong.png`) are
left on disk. The deck is not published; the live slides equalled the builder's output before
the corrections.

### For the owner

1. **The real `claude` ran twice.** `--test --all` runs the install test; say whether that is
   wanted, or whether the install test should run only under `--install`.
2. **The three narrowings of spot test 6** (adjacent strings, a name and its value, a
   placeholder): accept them or take them out.
3. **`host PROOF-53` says "starts no process"**, and the run starts one, `git remote get-url
   origin`, since the git host is read from the remote each time; the test asserts that one
   process and no push.
4. **The key commands fail in a home with no `~/.ssh` folder**: `ssh-keygen -f
   ~/.ssh/id_ed25519` does not make the folder, and `signatures RULE-17` fixes the three
   commands; the three-person test gives each person the folder.
5. **`--ignore=mutants`** stays in the suggested pytest command, held by `run_script
   PROOF-126`, `221` and `262`, and so in the README, two docs pages,
   `references/supported_frameworks.md` and `dev/run_project.py`.
6. **`config_engine.UPGRADE_KEYS`** names the keys the warning sends to `purlin:init --update`;
   no spec lists them (`mcp`).
7. **A first `purlin:test --remote` with no `@env` tag** writes nothing and exits 1 with a line
   `remote` chose.
8. **A `--remote` run prints no test comment to correct** (`remote`, 4).
9. **`server PROOF-9` says "exactly `{"tests": []}`"** and `PROOF-142` "indented over three
   lines"; the test reads the first as the JSON value.
10. **The upgrade still prints the no-scope advice** and names `test_framework` among the keys
    removed (`setup`, 4 and 5).
11. **The dashboard**: no list of what is left to do; a weak hand check shows no note; the
    strong row repeats the Audit panel's findings; `PROOF-198`'s "above the first box"; no
    proof holds the information notices or the detached line (`dashboard`, 1 to 7); the cut
    anchor name at 1024 pixels; the header line on two lines at 390 pixels for a long zone.
12. **Decision 117's open points** (`d117`, 2 to 10): a file git does not track stops no
    sign-off; the changed files are counted, not named; a rule with no test is named before a
    failing one; nothing records why a rule stayed not audited; `ai_audit RULE-33` still ends
    "caught or not made".
13. **The install test under a person's login** runs its prompt with `--plugin-dir` (`docs`, 1).
14. **`skills/spec-from-code` stays a row of the command reference**, marked optional (`words`, 9).
15. **The deck's pictures are not in git**, and the corrected deck waits for the owner to
    publish.
16. **Round 1's calls still open**: 5 to 17 of `round1.md`, "For the owner", but 5 and 6, which
    decision 117 answered.

### What is left

1. The real-skills QA check on a fresh LabConnect-style project, set up with Purlin from
   nothing (decision 116).
2. Measuring the planted-bug audit against $0.10 a rule and 1 in 5 irrelevant, on Purlin's own
   tests and one sample project (decision 116); `.purlin/runtime/audit_run.json` holds the cost.
3. The remote run on Windows: `purlin:test --remote`, for the 22 rules left.
4. The owner's review: the docs pages, the deck, the differences from 0.9.5, the calls above.

### Lines a person reads that a lane chose, both rounds

Word for word from the reports.

#### Round 1

Word for word from the six reports.

**`evidence`.** None printed.

**`states`.**

| Line | Where it prints |
|---|---|
| `no screens here` (the reason alone, as the run gave it) | the passed cell's reason on a feature's proof that found nothing to check; carried in the payload among the cell's reasons, which the dashboard's rule page shows |

**`signoff`.**

| Line | Where it prints |
|---|---|
| `The evidence package was not written: <why>. Nothing was signed; run purlin:sign again.` | `purlin:sign`, where the package cannot be built or written; `<why>` is the operating system's or git's own message |
| `The audit's findings: <n> weak.` | `purlin:sign --show`, in place of the walk's question, before the list |
| `Rule`, `Proof`, `Results` and `What the audit found` as headings, with the rule's words, each proof and finding indented two spaces | a hand check's stop, in the walk and `--show` |
| `    tied to no test` | under a proof that is not `@manual` and has no test tied, in a stop |
| `  <System>: <word> on <machine>` | a stop's result line |
| `Usage: sign.py [--version <version>] [--show \| --answers FILE \| --check FILE] [--project-root DIR]` | standard error, exit 2 |
| `sign.py: --check needs the package file to check.` | standard error, exit 2, after the usage line |
| `sign.py: --version needs the version to sign.` | the same |
| `sign.py: --show, --answers and --check are three steps; name one.` | the same |
| `sign.py: --check reads a file and takes no version.` | the same |

**`spot`.**

| Line | Where it prints |
|---|---|
| `Python`, `JavaScript`, `TypeScript`, `C#`, `Go`, `shell`; any other language by its extension without the dot, as `The test checks nothing is not read in rb tests.` | the language in `NOT_READ`, once per check and language |
| `the answer named no change` (K9's) | the `why` of a planted bug `not made`, printed by the audit in `PROOF-1: no bug was planted: <why>.` |
| `../outside.py is outside the copy of the project` | the same |
| `README.md is not a file the feature's scope names` | the same |
| `src/gone.py is not in the project` | the same |
| `the lines before the change are not in src/age.py` | the same |
| `the lines before the change are in src/age.py 2 times, not once` | the same |
| `the change leaves src/age.py as it was` | the same |

**`audit`.**

| Line | Where it prints |
|---|---|
| `login RULE-2   weak`, then each finding indented two spaces, then each `  PROOF-N: no bug was planted: <why>.` | `audit_run.run`, one block per rule read |
| `2 rules were read without the model's explanation: claude is not on PATH. Run purlin:audit --all once it can be reached.`; for one, `1 rule was read ...` | `audit_run.run`, where the model's reading could not be reached |
| `The audit found no rule that passes its tests.` | `audit_run.run`, in place of the share |
| each sentence of the entry's `explanation`, indented four spaces | `ai_audit.py --feature`, under `What the audit found`, after the findings |

Section 6's two lines are used as written: `The model was asked 31 times for 12 rules: $1.87
in all, $0.16 a rule.` and `PROOF-1: no bug was planted: <why>.`

**`run`.** None. Section 6's `purlin: --commit-runner belongs to --test --remote. Run
purlin:test --remote --commit-runner` prints to standard error with the usage line, with no
full stop after the command.

#### Round 2

**`d117`.**

| Line | Where it prints |
|---|---|
| `No sign-off: 1 file is changed and not committed. Commit it or set it aside, then run purlin:sign again.` | `purlin:sign`, the first refusal |
| `No sign-off: 2 files are changed and not committed. Commit them or set them aside, then run purlin:sign again.` | the same, for any count but 1 |
| `No sign-off: these results were taken while files were changed and not committed: login on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.` | `purlin:sign`, over a committed section reading `dirty`; features and systems as the not-this-code refusal lists them; `purlin:test --remote` for a remote runner's section, both joined by ` and ` |
| `No sign-off: 1 rule has no test at 1cf829e: login RULE-3. Run purlin:build login, then purlin:sign.` | `purlin:sign`, where a rule has no test |
| `No sign-off: 3 rules have no test at 1cf829e: login RULE-3, RULE-4; visit_window RULE-1. Run purlin:build login, then purlin:sign.` | the same, for several; the command names the first feature by name |
| `The model could not be reached: claude is not on PATH. 2 rules stay not audited. Run purlin:audit again.` | `purlin:audit`, once, after the rules and before the cost line and the share |
| `The model could not be reached: claude exited with an error. 1 rule stays not audited. Run purlin:audit again.` | the same, for one |
| `The model could not be reached: claude timed out after 300 s. Run purlin:audit again.` | the same, where every rule the model was not reached for was written `weak` |
| `login RULE-2   not audited` | `purlin:audit`, the line of a rule read and written no entry |

Two reasons in one run are joined by `; ` in that one line.

**`remote`.**

| Line | Where it prints |
|---|---|
| `No proof in specs/ is tagged @env for a system, so there is no runner to write and nothing was pushed. Tag a proof @env(<system>) with purlin:spec, then run purlin:test --remote again.` | `purlin:test --remote` where there is no runner file and no proof in `specs/` carries an `@env` tag; exit 1 |
| `The runner file <path> was not committed: git <add\|commit> failed. Nothing was pushed; run purlin:test --remote --commit-runner again.` | `--commit-runner` where git refuses the add or the commit; exit 1 |
| the runner file's text, whole, between `RUNNER_WRITTEN` and `RUNNER_NEXT` | `purlin:test --remote` on first need; `host RULE-54` and K11 say "the file" |
| the comment lines of both templates, rewritten as above | the runner file |

The lines `host` and section 6 fix are used as written.

**`anchors`.**

No line the code prints is new. Two check labels in `dev/test_e2e_anchor_rules.sh`, printed as
`    ok: <label>` or `    FAIL: <label>` when the suite runs:

- `the status says the tests are met`
- `the table ends on the line that names the sign-off`

The prose of the two format files is mine; the lines it quotes are the specs' and section 6's.

**`setup`.**

| Line | Where it prints |
|---|---|
| `# Dashboard page, rewritten with its data, never committed` | the comment above `/purlin-report.html` in the `.gitignore` block setup writes (`templates/gitignore.purlin`) |
| `# .purlin/evidence/ is tracked on purpose: it is the evidence of each run,` / `# for somebody who did not make it to read.` | the last two lines of that block |
| `config: write .purlin/config.json with version and tests alone` | the upgrade's pending list, the `config` migration |
| `workflows: remove the workflows that committed proof files` | the upgrade's pending list, the `workflows` migration |
| `  removed from .purlin/config.json: <keys>`, the keys in the file's order, `test_framework` among them | the upgrade's `config` migration, for every key but `version` and `tests` |
| `  removed <n> workflow(s) that committed proof files; the first purlin:test --remote writes the runner file` | the upgrade's `workflows` migration |

Setup's summary no longer opens on `Gate <gate>. Suites <names>.` or a git host line; it opens
on the first `wrote` or `kept` line. Nothing replaced those lines.

**`mcp`.**

| Line | Where it prints |
|---|---|
| `No Purlin project root at <folder>: .purlin/config.json is not there. Run purlin:init there, or pass the top folder of a Purlin project as project_root.` | Any tool call whose `project_root` names a folder with no settings file. `server PROOF-168` fixes its first sentence; the second is chosen. It replaces two lines that named how the root was found and `PURLIN_PROJECT_ROOT`, which no call reads now. |
| `.purlin/config.json carries <keys>, which this version does not read. Remove them from .purlin/config.json.` | `config_engine.settings_warnings`, where two or more keys are named and one has no upgrade step. K1 gives `Remove it` for one key; `them` is chosen for more. |
| `Next: commit VERSION and every file above in one commit.` | `bash dev/bump_version.sh <semver>`, last line. It ended `then tag v<semver>.`; the release tag is gone and `signed/<version>` is written by `purlin:sign`. |
| `The top folder of the git checkout you are working in, the one holding .purlin/. Every call names it.` | `tools/list`, the description of `project_root` on all three tools, read by the model. |
| `Read .purlin/config.json, or write its tests setting. The file holds version and tests.` | `tools/list`, the description of `purlin_config`. |
| `... Returns JSON with the range and one view of it, for the purlin:drift skill to print.` | `tools/list`, the end of `drift`'s description, which named three role views. |
| `Show one row per spec and the cells of every rule per feature. Reads specs/ and .purlin/evidence/, and returns the table with the next step.` | `tools/list`, `sync_status`'s description, which also named the signatures. |
| The section `A scope naming a file not yet written`, and the new wording of the `> Scope:` row, the proof paragraph and the `@manual` row | `references/formats/spec_format.md`. The two example lines are `states PROOF-279` and `PROOF-280`'s. |

`<tool> needs project_root: pass the top folder of the git checkout you are working in.`,
`gate is not a setting; .purlin/config.json holds version and tests. Nothing was saved.` and
the settings warning ending `Run purlin:init --update.` or `Remove it from .purlin/config.json.`
are section 6's, as written.

**`words`.**

Section 6's lines for this lane are used as written: the agent's worktree sentence, the
`project_root` sentence in the agent and in every skill but drift's, where it stands under the
tool call, the three lines of `references/writing_style.md`, `CLAUDE.md`'s step 3, and the ten
`RELEASE_NOTES.md` lines, followed by the format numbers.

Chosen here:

| Line | Where it shows |
|---|---|
| `Show the two facts, every rule's cells and what is left to do` | the status skill's description, and its Purpose in `references/purlin_commands.md` |
| `Run the tests, the heuristic spot tests, one planted bug per proof and the model's reading, then write what it found into the evidence` | the audit skill's, the same two places |
| `Build the evidence package from the committed evidence, walk its hand checks with a person, then sign it in a signed commit` | the sign skill's, the same |
| `Report what changed since your last pull` | the drift skill's, the same |
| `Set a project up for Purlin` | the init skill's, the same |
| `→ Run: purlin:sign`, when a person chooses to sign | the status and test skills, the next step after `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` |
| `→ Run: purlin:test --commit` | the status and test skills, after `<n> features whose results are not committed` |
| `→ Ask the person, then run: purlin:test --remote --commit-runner` | the test skill, after the runner file is written |
| `→ Ask the person for the new version, then run: purlin:sign --version <version>` | the sign skill, after the refusal that names a new version |
| `→ Run:` the command it names | the sign skill, after a refusal naming a test run |
| `→ Run: purlin:build <feature>, then purlin:test --all --commit` | the sign skill, after `Stopped at` |
| `→ Fix what it named, then run: purlin:sign` | the sign skill, after the commit or the package could not be written |
| `Specs and marked tests: → Run: purlin:test, which suggests the test commands on its first run.` | the init skill's closing list |
| `A rule reads weak: → Run: purlin:build <feature>, then purlin:audit again.` | the audit skill's closing list |
| `The hand-off is run and commit: purlin:test --all --commit runs every test and commits the specs, tests and settings, then the evidence that names them, and purlin:test --remote does the same for the proofs tagged for a system this machine is not.` | `agents/purlin.md`, "The core loop" |
| `purlin:drift → purlin:spec → purlin:build → purlin:test → purlin:test --all --commit → purlin:sign` | `agents/purlin.md`, the loop |
| `"it is ready for sign-off", "hand it to QA"` routed to `purlin:test --all --commit`; `"what do we hand to the system of record?"` routed to the evidence package `purlin:sign` committed | `agents/purlin.md`, "Routing" |
| The headings `The two facts`, `What is left to do`, `Which evidence counts`, `Where a runner runs`, `When a sign-off counts`, `What signed/<version> means`, `What stops nothing`, `Platforms`, `What stands behind an instruction` | `references/evidence_and_signoff.md` |
| `The tag binds the signing alone: it says what was signed and by whom, and makes no claim about who was entitled to sign.` | `references/evidence_and_signoff.md`, the tag's definition |
| New glossary words: `settings`, `the two facts`, `test comment to correct`, `information`, `hand-off`, `this version of the code`, `nothing to check`, `heuristic spot test`, `planted bug`, `explanation`, `checkout` | `references/glossary.md` |
| `"Purlin plants one bug per proof"` and `"4 of 5 rules strong (80%)"` | `references/writing_style.md`, two examples that named breaking the code and test strength |
| `- Poor: "The settings screen meets the contrast standard."` `- Good: "Every screen in the project meets the contrast standard."` | `references/spec_quality_guide.md`, "A rule for the whole project", the pair that teaches decision 107 |
| `In more words:` | `RELEASE_NOTES.md`, between section 6's lines and the longer entries under them |

**`docs`.**

| Line | Where |
|---|---|
| `claude plugin install purlin@purlin --scope project`, as the third install line, after `cd my-project` and `claude plugin marketplace add https://github.com/rlabarca/purlin.git --scope project` | `README.md` under `Install`, `docs/getting-started.md` step 1. The pages gave the install as `/plugin install purlin@purlin` typed inside Claude Code, which no test can run; `install PROOF-2` runs "the pages' commands" |
| `Start Claude Code in the project, or run /reload-plugins in a session that is already open, and the purlin: commands are there.` | the same two places |
| `claude is not installed here` | the skip reason of `dev/test_install.py`, as section 6 gives it |
| `Nine guides, and the references behind them.` | `docs/index.md`, first line |
| The headings `Four words`, `The two facts`, `Run from a checkout`, `When the tests are met`, `The hand-off`, `What it refuses`, `A key to sign with`, `What is recorded`, `Beside a regulated system`, `Which results count for a sign-off`, `A comment to correct`, `A rule with nothing to check`, `More than one checkout`, `Any screen, both themes`, `When it refuses`, `After the upgrade` | the pages |
| The table of `Left to do` lines with a column `Blocks Tests: met` | `docs/running-and-evidence.md` |
| The sample hand check, `The error messages follow the brand voice guide`, and the sample audit output `login RULE-2   weak` with `PROOF-2: the test still passes when src/auth.py:31 reads "return True"` | `docs/sign-off.md`, `docs/running-and-evidence.md`: examples in the shapes K8 and K9 fix |
| `PROOF-1: the test still passes when src/age.py:12 reads "return minutes + 60"` | `docs/audit.md`, in place of `sample_age PROOF-1: the test still passes when src/age.py:12 adds an hour.`, which is not the shape K9 prints |
| The prompt `List every slash command or skill available to you whose name starts with purlin: and nothing else. Answer with the names only, one per line. Use no tool.` | sent to the model by `install PROOF-4`'s test; no person reads it |

The paragraph of `purlin_docs RULE-16` is section 6's, word for word, with `purlin:status` in
backticks.

**`dashboard`.**

| Line | Where it prints |
|---|---|
| `PROOF-3: its tests missed a bug planted at src/auth/lockout.py:27.` | the `Audit` panel on a rule's page, once per planted bug whose result is `survived` |
| `Before` and `After` | the two labels under that line, each beside the lines the audit recorded, set in the monospace face |
| `Tests` and `Sign-off` | the labels of the top bar's two boxes (`purlin_report RULE-7` names them) |
| each sentence of the audit's `explanation`, as the audit wrote it | the `Audit` panel, after the findings, for a strong and a weak rule alike |

Section 6's `detached at a1b2c3d, written 10:42` and the information line as a notice in the
neutral tone, below the warnings and above the boxes, with no heading, are used as written.

Tones chosen, no words: `Tests` reads in the pass tone when `met` and the warn tone when
`not met`; `Sign-off` in the pass tone for `signed <version> at <commit>`, the warn tone for
`signed <version>, <n> commits since` and the neutral tone for `not signed`.


---

# Handoff, 2026-09-30

For the session that continues Purlin 0.10.0. Read this, then `dev/plans/three-levels.md`
decisions 60 to 100 (together with this file they are the product as the owner settled it), then
`dev/plans/next-agent-prompt.md`, the prompt that session is given.

## Where the tree is (2026-10-01, end of the long session)

- `main` is local only. Decisions 100 to 103 are built in code and tests. Decisions 104 to 115 are
  decided and their SPECS are on `main` (408 rules, 823 proofs, after a weight pass from about
  700), but the code and tests are not built: `main`'s specs run ahead of its code, its sweep may
  fail in places, and the dashboard shows many rules with no test and about 1,600 test comments
  to correct. That is expected until the build.
- Decision 115's text is in `three-levels.md`; its four spec rules are Step 1 of
  `next-agent-prompt.md`.
- The audit's heuristic spot tests are official in `references/review_criteria.md`, with their
  research; `docs/audit.md` explains the audit and cites every paper by link.
- The deck (https://claude.ai/artifact/Rifxf2KXfH4CTzfQ9pZ9is, version 86) has 11 slides for
  decisions 100 to 115, including the comparison with Spec Kit, Kiro, Ketryx and Cucumber and the
  audit slide; built by `dev/plans/deck/build_deck.py`.
- Two QA and product checks ran in the cloud: `sanity-qa-product.md` and `-2.md`. The second
  reached a signed release; decisions 105 to 107 answer it.
- Cloud credits: $127 of $250 were left before the second QA check; they expire 2026-11-05.
- About 50 worktrees under `/Users/richlabarca/LocalCode/purlin-wt/` and many `lane/*` and
  `specs/d110`, `d102/*`, `d103/*`, `sanity/*` branches (some pushed) can be deleted once the owner
  says so.

## What is left, in order

1. `next-agent-prompt.md`: decision 115's specs, the build plan, the build (lanes in the cloud,
   integration local), the cloud sessions archived.
2. The real-skills QA check: three real Claude sessions with the plugin, one feature, one
   collision, run on demand.
3. The remote run on Windows (not run since decision 100), a full reading of the docs pages,
   the owner's review, and the handover to the work machine.

## The model in one paragraph

A rule says what must be true. A proof says in plain language how that is shown: one case, in at
most 60 words. A test is any test in the project's own suite with one comment above it,
`purlin: <feature> PROOF-<n>`. Three steps: `passed` (`purlin:test`), `strong` (`purlin:audit`,
a model reading each test against its proof, with optional mutation testing), `signed`
(`purlin:sign`). The gate is the last step every rule must reach, and every rule is asked what
the gate asks: no rule carries a level of its own. Evidence is one file per feature per source,
written by a run and committed with `--commit`; it goes out of date when the spec, the covered
code or the tests change, and a run with no feature named runs only what changed. Each proof is
proven where its tag says: this machine proves every untagged proof and every proof tagged for
its own system, and a remote runner proves only the proofs tagged `@env` for its system, which
this machine is not. Every run ends on the summary and `Left to do`, one line per kind of work
with its command; there is no queue, and `to test by hand` and `to sign` are two of its lines.
An anchor is a set of rules for the whole project, counted, audited and signed once; no spec
names one. `purlin:sign` walks the rules left `to test by hand` or `to sign` and, at the gate
`signed`, when nothing else is left and every result came from committed work, writes the
evidence package and the signed tag. Purlin makes no claim of compliance: it hands evidence to
a system of record, which decides who was entitled to sign.

## What is left, in order

The prompt for the next session is `dev/plans/next-agent-prompt.md`.

0. **After decisions 102 and 103**: the remote run on Windows (`purlin:test --remote`) for the
   84 rules that wait for it; the anchors slide below; a full reading of the docs pages against
   the code, `docs/review-and-signing.md` and `docs/qa-guide.md` among them; a rerun of the QA
   and product check, with separate agents, against the new workflow (the release run and the
   sign-off walk); then the owner's first `purlin:test --release` and `purlin:sign` on a release
   branch for 0.10.0. Left by the lanes for the owner, in `d103-interfaces.md`: the spec
   format's `> Scope:` still required at `signed`, `CLAUDE.md`'s `package_format.md` row, and
   the release run printing the status before its own lines.
1. **After decisions 100 and 101**, in this order: the remote run on Windows
   (`purlin:test --remote`, pushing only its run branch); the slide on anchors, taken into
   `dev/plans/deck/build_deck.py` with these words and published: title `Anchors: rules the
   whole project must follow`; subtitle `An anchor is a set of rules for the whole project,
   proven by tests that run across all of it.`; card 1 `Written in this project`: `Write a rule
   once, such as no secret in the code. Tests across the whole project prove it, and no feature
   names it. A rule only some features need goes in each of those features' own specs.`; cards
   2 and 3 unchanged; card 4 `Design standards too`: `Design publishes its standards as an
   anchor. Tests across every screen prove them; a standard no test here can show is signed as
   not applying, or checked by the team that owns it.`; footer `Each anchor rule is counted,
   audited and signed once. Any change to the project ends its results and signatures, so
   anchors are signed last.`; a full reading of the docs pages against the code; then the QA
   sanity check, which the owner runs in a cloud session. The two docs screenshots were
   retaken at `30c97d29b`.
2. **The further sanity checks**, each its own fresh agent, in the order the owner picks. The
   next one runs `purlin:spec-from-code` on project copies of which one carries a test that
   fails before the run, so decision 66's clause about failing tests is tried, and the agents
   count existing tests one way (`sanity-3.md` section 9). Then: a QA person writes proofs; an
   upgrade from a real 0.9.5 project; a hostile reviewer who tries to make an unproven rule
   read as proven. Decision 64 repeats the docs-against-rules reading by a fresh agent before
   every release.
3. **The owner's review**: `RELEASE_NOTES.md` 0.10.0, `README.md`, `docs/`, the slides, the
   words below and the 55 readings of `phase2-questions.md`.
4. **The handover to the work machine**: delete `dev/plans/` (it is history, and it ships);
   push the work as a branch; on the work machine run `dev/manual/check_azure_remote.py`
   against a real Azure DevOps project, then `purlin:audit`, `purlin:sign`, the push of the
   tag, the release.

## Words for the owner to read

Decision 103's words are in `d103-interfaces.md`: section 7 of `d103-plan.md` under "Words
chosen for the owner to read", and each lane's own under "Words chosen by a lane, word for word".

Decision 102's words are in `d102-interfaces.md`: section 7 of `d102-plan.md` under "Words
chosen for the owner to read", and each lane's own under "Words chosen by a lane, word for word".

Chosen by an agent where no decision gave them, gathered from `phase3-interfaces.md` ("Words
chosen for the owner to read") and `phase4-interfaces.md` ("Words chosen for the owner to read",
"Words chosen by a lane, word for word", and "The pages"). `<...>` is filled in. Words the
owner already accepted in decision 96 are not repeated.

| Where | What it says |
|---|---|
| Setup, the commit question | `Commit the files setup wrote? [y/N] ` |
| Setup, after the commit | `Committed <sha7>, the files setup wrote:` then each path, indented two spaces |
| Setup, when git refuses the commit | `The files setup wrote are staged and not committed: <git's own message>.` |
| Setup's commit | `chore(init): set up Purlin at the gate <gate>` |
| A project with no spec, not set up | `No specs found under specs/.` then `→ Run: purlin:init to set this project up.` |
| A project with no spec, set up over code | `→ Run: purlin:spec-from-code to write the specs this code already implies.` |
| A project with no spec, set up over no code | `→ Run: purlin:spec <name> to write the first spec.` |
| Setup outside git | `This is not a git repository. Run git init, then purlin:init.` |
| Setup, a typed gate it does not take | `<value> is not accepted for gate; it takes passed, strong or signed. Reading it as <gate>.` |
| Setup, `--gate` it does not take | `<value> is not accepted for gate; it takes passed, strong or signed. Nothing was written.` |
| Setup, the gate question | `What must be true of every rule before a version is finished?` |
| Setup, the breaking question | `Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N] ` |
| Setup, no runner file | `skipped the runner file (<reason>)` |
| Setup, a runner file written | `  it runs on <images>, the systems a proof in specs/ is tagged @env for that this machine is not.` |
| Setup, a file copied | `copied <source> to <rel>` |
| The evidence README | `What a run leaves behind for each feature: each proof's result on each operating system, the commit and the time.` and `` A run on your own machine writes `local/`, and `--commit` commits it under your own git identity. `` |
| The status, a gate it does not take | `<value> is not accepted for gate in .purlin/config.json; it takes passed, strong or signed. Reading it as passed; set it with purlin:init --gate <gate>.` |
| The status, `audit_parallel` it does not take | `<value> is not accepted for audit_parallel in .purlin/config.json; it takes a whole number from 1 to 16. Reading it as 4; fix the file by hand.` |
| The status, a spec naming no files | `1 spec names no files, so its tests run every time: <name>. Run purlin:spec <name> to add its > Scope: line.` and `<n> specs name no files, so their tests run every time: <names>. Run purlin:spec with each name to add its > Scope: line.` |
| The status, a source it cannot read | `<name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` |
| A cell's reasons | `<System>: no run yet`, `passed on <Systems>`, `failing: <System>, <source>` |
| The settings tool | `A change needs a key; nothing was saved.`, `<key> is now <value>; saved to .purlin/config.json.`, `No Purlin project root at <root>: .purlin/config.json is not there. That root came from <source>.` |
| A spec's warnings | `` <feature>: 1 line under ## Rules is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>. `` and `<feature>: > Requires: names <other>, which is not an anchor, so its rules do not apply. Run purlin:spec <feature>.` |
| Evidence ignored | ` Run purlin:test <feature> to write it again.` and ` Run purlin:test --remote to write it again.` after the reason |
| A run's refusals | `purlin: --commit belongs to --test and --audit; a remote run commits on the runner. Run purlin:test --remote without --commit.` and `purlin: no spec named <name> under specs/. Run purlin:status to see the specs this project has.` |
| A run, evidence missing | ` Run purlin:<action> --arm-timeout <seconds> to give it longer.`, ` Check its command and report in the tests setting of .purlin/config.json, then run purlin:test.`, ` Check that its test ran and was not skipped, then run purlin:test.` |
| A run, a suite problem | ` Fix the tests setting in .purlin/config.json, then run purlin:test.` |
| The tests table | `# Tests at <sha7>, with changes that are not committed` |
| Test comments | `<file>:<line> names <feature> <ID> and no test follows it. Put the comment directly above a test, or run purlin:build to repair it.`; `The report's <case> matches <n> tests in <files>, so its result is not counted. Give the tests different names, then run purlin:test.`; `<file>:<line> names <feature> <RULE-N>, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.` |
| A remote run with no program to wait with | `purlin:test --remote waits for the run with the GitHub CLI, gh, which is not installed, so nothing was pushed. Install gh, then run purlin:test --remote again.` (and the Azure CLI form) |
| A remote run no runner picked up | `No run registered for <branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that the git host runs <workflow path> on a push to run/*, then run purlin:test --remote again.` (and the Azure form) |
| A remote run that failed | `The run failed on the git host. The table below is what came back.` |
| A remote run's refusals | ` Add one with git remote add origin <url>, then run purlin:init.`, ` Make one with git switch -c <name>, then run purlin:test --remote again.`, ` Check that git push origin works from this checkout, then run purlin:test --remote again.` |
| A runner outside its checkout | `<path> is not the project root this job checked out, so no evidence was committed.` |
| Proofs for another system | `Proofs in specs/ are tagged @env for <Systems>, which this machine is not, so only a runner can prove them.` |
| The runner templates | `The matrix holds one job for each operating system a proof in specs/ is tagged @env for that the machine running setup is not, and no other.` and `The run caps each test command at an hour of its own.` |
| The breaking tool | `mutation_engine names "<x>", which is not an engine: set it to none, auto, mutmut, stryker or stryker_net` |
| Drift | ` Run purlin:test <feature>.`, ` Add each to a spec's > Scope: line with purlin:spec.`, ` Run purlin:build.`, ` Run purlin:test.` after its lines |
| Signing | `The signature commit was not made: <git's own message>. Nothing was signed; run purlin:sign again once git can make a signed commit.`; `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.`; `No tag: the committed evidence still has work left to do, so no evidence package was committed. Run purlin:test --commit, then purlin:sign.`; `  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>` |
| No version | `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` (and the `purlin:export` form) |
| What the audit found | `No audit has read this rule's text, proof and test yet.`, `Strong. It found nothing.`, `Strong.`, `Weak.`, `Undecided. The AI audit could not decide, so the rule reads weak until its proof or test changes.`, `  Read by <model> at <at>.` |
| Test strength | `Test strength <p>%, against a minimum of <m>%.` |
| No test, terminal and page | `  No test yet. Run purlin:build <feature>.` and `No test yet. Type purlin:build <feature> in Claude Code.` |
| Anchors | `<name>: no anchor named <name> carries a git source. Run purlin:status to see the anchors this project has.`; `  1 rule. Run purlin:status to see it.`; ` Run purlin:status <name> to see its rules.`; ` Commit it as anchor(<name>): sync (<new7>), then run purlin:test.`; `No Purlin project root found. Pass --project-root <dir>.` |
| The dashboard | `Type purlin:sign <feature> <RULE-N> in Claude Code.`, `Back to the board`, the theme button `Dark theme` or `Light theme`, `The working tree has uncommitted changes, so what is on this board is not what a commit would carry.` |
| The references | the glossary's `runner file`, `scope` and `anchor` sentences; the writing style's sentence on capitals; the quality guide's paragraphs on a library's public names and a list of like inputs; the spec-from-code skill's five reasons and what a caller reaches; the spec skill's "Ids"; the test skill's comparison; the command reference's `purlin:init` sentences; the release notes of K5.10 (`phase4-contracts.md` K5) |
| Phase 3's reference prose | the exit-code table of `references/purlin_commands.md`, the `no_scope` row of `hard_gates.md`, the git-host sentence, the package's kinds sentence, the anchor source paragraphs (`phase3-interfaces.md`, "Words chosen for the owner to read", items 1 to 11) |
| The upgrade | `Write <path>, one job per operating system your specs name that this machine is not?` |
| The pages | every sentence the four page lanes wrote, listed per lane in `phase4-interfaces.md`, "The pages" |
| Decision 99 | every sentence, rule and proof listed in `phase4-interfaces.md`, "Decision 99", "Words chosen, word for word": `> Highest-Proof:` in the spec format, the spec skill and the docs; the subject `purlin: specs, tests and settings`; the fixture folders setup leaves out; `Checked by hand.` alone once signed; the export skill's sentence; the evidence format and release-notes sentences integration wrote |
| Integration 2 | the rule and proof texts of "The pages", the table of rules handed over; `is signed and its signature does not count` in `hard_gates.md`, `spec_format.md`, the spec skill and the release notes; the comment `The whole-number part, as every surface shows a share: 69.6 under 70 reads 69%, never the minimum itself.` in `states.py` |

## Small things known and not fixed

- `purlin:test --all --commit` prints two blank lines between `86 proofs need Windows; ...`
  and `Evidence written to ...`, where the same run without `--commit` prints one.
- `purlin:audit --commit` prints two blank lines between the committed paths and
  `AI audit: <n> rules to read, <k> at a time.`
- `purlin:anchor add` given a local path that does not end in `.git` writes a `> Source:` line
  that `sync --check` and drift then read as not a spec kept in a git repository.
- A status of a project whose anchor names an `https` source reaches the network; the 0.9.5
  fixture's Figma anchor does, and printed `remote: Not Found` once in phase 4.
- `purlin:sign --all` that signs the last rule leaves `the version to tag`; a second bare
  `purlin:sign` writes the tag.
- The sign skill says `observation` where the audit's lines and the docs say `finding`.
- `specs/instructions/purlin_docs.md` uses RULE-1, RULE-2 and PROOF-1 to PROOF-9, numbers an
  earlier spec of that name held before it was deleted; the new rule took RULE-12.
- The calls each lane of phase 4 and of decision 99 left: `phase4-interfaces.md`, "Calls
  left", "The pages" and "Decision 99".
- Carried from the earlier handoff, not checked again: `purlin:init` without `--yes`, with its
  output piped, hung once in a scratch Go project; Vitest 4 would not install on this machine,
  version 3 is proven; text on a solid coloured badge measures under 7 to 1 (the owner chose to
  leave it); a hand check may be signed without a note (the owner chose to leave it).

## Open questions for the owner

None. Decision 99 answered the five this section held; the calls its lanes left are in
`phase4-interfaces.md`, "Decision 99", "Calls left".

## How to work, as the owner settled it

- **Decisions close before anything launches.** Ask with the question UI, with options and
  consequences, and wait.
- **Ask from the root.** Say what a thing is for in plain words before asking about it. No
  function names, no file names, no term that has not been explained. Offer the option that
  removes the mechanism. The owner is simplifying Purlin with every answer.
- **Maximum parallelization, cut by ownership of files.** Each agent is Opus, has its own
  worktree and its own scratch folder, and owns files no other agent writes. What one produces
  and another consumes is fixed word for word before they start. Merges are fast-forward.
- **No push, no pull request, no tag, no audit and no signing by any agent**, but the one
  temporary run branch a remote run pushes.
- **Acceptance is the full sweep**, `bash dev/run_tests.sh`, plus this repository run through
  its own tool with every marker tied. Never edit a number to make a sweep green.
- **Look at anything visual** with playwright from the `.venv`, at 1500, 1280, 1024, 768 and
  390 pixels, both themes, before telling the owner it is done. A value never breaks inside
  itself; neutral text measures at least 7 to 1.
- **A clean release.** Nothing that represents earlier functionality stays: no compatibility
  reader, no test that a removed thing is absent, no table of removed words.
  `RELEASE_NOTES.md` is the one place history is kept, and what an upgrade from 0.9.5 needs is
  the one exception in code.
- **A page says what is**, checked against the code, in the words of
  `references/writing_style.md`, and every statement on it is held by a rule, a proof and a
  test (decision 64).
