# Round 2, integrated

Written by the integration agent on 2026-10-01. Decisions 100 to 117 are built. The eight round 2 lanes are merged in the order `d117`, `remote`, `anchors`, `setup`, `mcp`, `words`, `dashboard`, `docs`, each rebased onto the merged line and merged fast-forward; `team` and `deck` were done on the merged line. Nothing was pushed, tagged, audited or signed.

## The numbers

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

cloud spend: see the coordinator's report

## The spot tests over this repository's own tests

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

## The review of the fixed tests

Three reviewers that fixed none of them read 136 tests against their proofs: every `fixed`
one, the `stated` ones sampled, the proofs added, decision 117's and `collaboration PROOF-1`.
They agreed with 131. Fixed: `purlin_report PROOF-3` (asserts `--canvas:` is declared),
`PROOF-15` (asserts the passed row's own word), `PROOF-235` (asserts `Before` and `After` as
written), `drift PROOF-40` (the reason names the path, not the file name alone). Left for the
owner: `host PROOF-53`.

## What integration changed

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

## The header line's timezone (the owner, 2026-10-01)

The data keeps `generated_at` in UTC. The page converts it in the browser: the header reads
`<branch> at <commit>, written <hh:mm> <zone>`, 24-hour, the zone the browser's short name or
its offset. Changed: the header line and its hover; the Audit panel's `Read by <model> on
<date> <hh:mm> <zone>`, which was the one other clock time the page shows. Left: every age
(`19 days old`), which is no clock time; a hand check's note, which shows a version, a signer
and a count of commits. Under 600 pixels the line may break between the checkout state and the
time, never inside either; at 390 pixels it stays on one line for `EDT` and `UTC` and takes
two for `GMT+5:30`. The tests set the browser's timezone, `UTC` unless a proof names another,
and `dev/capture_doc_screenshots.py` takes its pictures in `UTC`.

## Spec edits integration made, word for word

`specs/dashboard/purlin_report.md`, on the owner's instruction:

- `RULE-77`, reworded: The top bar names the checkout state its data describes and when it was written, as `<branch> at <commit>, written <hh:mm> <zone>`, as in `main at a1b2c3d, written 06:42 EDT`: the branch and the first 7 characters of the commit the writing command ran on, and the time, 24-hour, in the timezone of the person looking at the page, named by the browser's short name for it or, where it has none, by its offset, as in `GMT+5:30`. Its hover gives the date and time in full in that zone, then the UTC time, as in `2026-10-01 06:42 EDT (10:42 UTC)`. The data keeps its stamp in UTC, and the line is unchanged while the page is open
- `PROOF-232`, reworded: Open the board with the regulated sample, its data written on the branch `main` at the commit `a1b2c3d` and stamped `2026-10-01T10:42:13Z`, in a browser set to `America/New_York`; the top bar reads `main at a1b2c3d, written 06:42 EDT`, its hover reads `2026-10-01 06:42 EDT (10:42 UTC)`, and after the page's clock runs on 2 hours the line reads the same
- `PROOF-237 (RULE-77)`, new: Open the board with the regulated sample, its data stamped `2026-10-01T10:42:13Z`, in a browser set to `UTC`; the top bar reads `main at a1b2c3d, written 10:42 UTC`
- `> Highest-Proof:` 236 to 237.

No other spec was edited by integration. The lanes' own spec edits are in `d117.md` and
`dashboard.md`.

## The dashboard, looked at

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

## Lines a person reads that integration chose

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

## Left unbuilt

Nothing a spec names is left unbuilt. The deck's pictures are rendered under
`dev/plans/deck/` and not committed: `.gitignore` ignores `*.png` outside `docs/images/`, and
the three older pictures there (`slide-passed.png`, `slide-signed.png`, `slide-strong.png`) are
left on disk. The deck is not published; the live slides equalled the builder's output before
the corrections.

## For the owner

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

## What is left

1. The real-skills QA check on a fresh LabConnect-style project, set up with Purlin from
   nothing (decision 116).
2. Measuring the planted-bug audit against $0.10 a rule and 1 in 5 irrelevant, on Purlin's own
   tests and one sample project (decision 116); `.purlin/runtime/audit_run.json` holds the cost.
3. The remote run on Windows: `purlin:test --remote`, for the 22 rules left.
4. The owner's review: the docs pages, the deck, the differences from 0.9.5, the calls above.

## Lines a person reads that a lane chose, both rounds

Word for word from the reports.

### Round 1

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

### Round 2

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

