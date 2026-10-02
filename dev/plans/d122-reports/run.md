# Lane `run`: report

Branch `lane/d122-run`, worktree `/Users/richlabarca/LocalCode/purlin-wt/d122-run`, rebased onto
`main` at `e02c9b4f5`. Built to `dev/plans/d122-plan.md` sections 2.7, 2.8, 3, 4.6, 5.3 (K3, K5,
K8), 6 and 7, as `dev/plans/d123-plan.md` section 1 changes the lane.

## What was built

1. **The tools refuse Purlin's own folder, and one refusal serves three callers** (findings 5
   and 6). `scripts/mcp/purlin/project.py` gains `NO_PROJECT_HERE`, `PLUGIN_FOLDER`,
   `plugin_root()`, `same_repository(a, b)` and `refusal(project_root, started_in)`, as K5 writes
   them. `scripts/mcp/purlin/server.py` makes one call to `project.refusal(call_root,
   STARTED_IN)`; `STARTED_IN` is `resolve_project_root()`'s answer, set in `main`. Its own
   `NO_PROJECT_HERE` and its use of `config_problem` are deleted.
2. **Two scripts.** `scripts/run/purlin_status.py [--project-root DIR] [--spec NAME]` and
   `scripts/run/purlin_drift.py [--project-root DIR] [--since N-or-date] [--json]`, each with
   `--help`. Exit codes as K5: the status 0, a refusal 1, a wrong command line 2; `--spec` 1 with
   warnings, 0 with `SPEC_CLEAN`, 1 with `NOT_A_SPEC`; a `since` drift refuses exits 2.
3. **The `tests` setting is asked for** (finding 10). `scripts/run/purlin_run.py` gains
   `--write-tests`, `WRITE_QUESTION`, `WROTE_TESTS` and `asked_yes`. After a suggestion the run
   asks on its input; `y`, `yes` or the flag writes the entries with
   `config_engine.update_config`, prints `WROTE_TESTS`, reads the suites again and goes on. Any
   other answer, an empty one or the end of input writes nothing and exits 1.
4. **The run's own word for a hand check** (findings 9 and 16). `scripts/run/evidence.py`,
   `rule_word`, answers `states.CHECKED_AT_SIGNOFF` where no proof of the rule can run.
   `references/formats/evidence_format.md` is at version 12, in the same commit.

## Rules and proofs, word for word

### `server`

`> Scope:` gains `scripts/mcp/purlin/project.py`, `scripts/run/purlin_status.py` and
`scripts/run/purlin_drift.py`. The Description gains `A script prints the status and another the
drift report, for a session that does not have the tools.`

Reworded:

- RULE-7: A tool called on a root holding no `.purlin/config.json` answers only `No Purlin project root at <root>: .purlin/config.json is not there. Run purlin:init.`, one whose settings file cannot be read answers only what is wrong and what to do, and neither reports or writes anything there
- PROOF-168 (RULE-7): A client calls `sync_status` with `project_root` naming an empty folder; the answer is exactly `No Purlin project root at <that folder>: .purlin/config.json is not there. Run purlin:init.`

Added:

- RULE-38: A tool called on the plugin's own folder, or a folder under it, is refused with one line and reports nothing, unless the server was started in that folder, under it, or in another checkout of the same repository
- RULE-39: `scripts/run/purlin_status.py --project-root <dir>` prints the status the `sync_status` tool answers for that folder and exits 0, and where the tool would refuse it prints only that refusal and exits 1
- RULE-40: `scripts/run/purlin_drift.py --project-root <dir>` prints the lines of the view the `drift` tool answers, one per line, takes `--since` as the tool does, and refuses as the tool refuses
- RULE-41: `purlin_status.py --spec <name>` prints only the warnings that name that spec and exits 1, or one line counting its rules and proofs and saying no mistake was found, and exits 0
- PROOF-170 (RULE-38): A copy of the plugin holds `.purlin/config.json` and the spec `login`; its server is started in another workspace, and a client calls `sync_status` naming the copy; the answer is exactly `<the copy> is Purlin's own folder, not your project. Pass the top folder of the git checkout you are working in.`
- PROOF-171 (RULE-38): That copy's server is started in the copy, and a client calls `sync_status` naming the copy; the answer opens `Purlin status:` and names `login`
- PROOF-172 (RULE-38): That copy is a git repository with a second checkout made by `git worktree add`; its server is started in the second checkout, and a client calls `sync_status` naming the copy; the answer opens `Purlin status:` and names `login`
- PROOF-173 (RULE-39): In a project with the spec `login`, `purlin_status.py --project-root <dir>` prints exactly the text `sync_status` answers for that folder, and exits 0
- PROOF-174 (RULE-39): In an empty folder, `purlin_status.py --project-root <dir>` prints only `No Purlin project root at <dir>: .purlin/config.json is not there. Run purlin:init.` and exits 1
- PROOF-175 (RULE-41): `login` carries `> Requires: api`; `purlin_status.py --project-root <dir> --spec login` prints only `login: > Requires: is not read, because every anchor covers the whole project. Run purlin:spec login.` and exits 1
- PROOF-176 (RULE-41): `login` holds 2 rules and 3 proofs and no mistake; `purlin_status.py --project-root <dir> --spec login` prints only `login: 2 rules and 3 proofs read. No mistake found.` and exits 0
- PROOF-177 (RULE-40): After a pull that adds `RULE-3` to `login`, `purlin_drift.py --project-root <dir>` prints the line naming the range, then `1 rule added: login RULE-3.`, and exits 0

### `run_script`

Reworded:

- RULE-102: With the `tests` setting empty the run prints `No test command is set`; for each test tool Purlin knows that it finds in the project it prints `Suggested for <name>: <run>`, then what that tool needs added where it needs something, then `Suggested tests setting: ` and the entries as one JSON array; where it finds none it says so and that the agent proposes a command for the person to confirm; and unless the question of RULE-107 is answered yes it writes nothing and exits 1

Added:

- RULE-107: After a suggested `tests` setting the run asks `Write this tests setting to .purlin/config.json? [y/N] `: `y`, `yes` or `--write-tests` writes the suggested entries as the `tests` setting, prints `Wrote the tests setting to .purlin/config.json.` and runs the tests; any other answer, an empty one or the end of input writes nothing
- PROOF-287 (RULE-107): In a project whose `tests` setting is empty and that holds a `conftest.py` and one marked passing test, `--all --test` with nothing to answer from prints `Write this tests setting to .purlin/config.json? [y/N] ` last, leaves `.purlin/config.json` byte for byte as it was, and exits 1
- PROOF-288 (RULE-107): That project run as `--all --test --write-tests` prints no question, prints `Wrote the tests setting to .purlin/config.json.` and then `Markers: 1 tied to a test, 0 not tied.`; `tests` holds pytest's entry alone, and it exits 0
- PROOF-289 (RULE-107): That project run as `--all --test` and answered `y` on its input writes pytest's entry as the `tests` setting, runs the test and exits 0

### `evidence_writer`

Reworded:

- RULE-30: A rule whose proofs are all `@manual` reads `checked at sign-off` in a run's section, because no run was ever going to observe one, and a `@manual` proof beside a proof whose test failed leaves the rule `failed`
- PROOF-21 (RULE-30): A run in which a rule's one proof is `@manual` and tied to no test writes a section reading the rule `checked at sign-off`

Deleted: none.

## `> Highest-*`, before and after

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `server` | 37, 41 | 169, 177 |
| `run_script` | 106, 107 | 286, 289 |
| `evidence_writer` | 33, 33 | 98, 98 |

`references/formats/evidence_format.md`: `> Format-Version:` 11, 12.

## What was seen failing first

Each test was written, then run against `main`'s code, before the code was kept.

- `dev/test_mcp_server.py` with the new tests and `main`'s `server.py` and `project.py`, and no
  scripts: `7 failed, 28 passed`. `server` PROOF-170 failed because the answer was the copy's
  status table. PROOF-168 failed on the old ending of the line. PROOF-173 to 177 failed because
  there was no such script: nothing was printed. PROOF-171 and PROOF-172 passed, since `main`
  answers for any folder.
- `dev/test_run_script.py -k NoTestCommand` on `main`'s `purlin_run.py`: `4 failed, 7 passed`.
  PROOF-287: no question is printed, the output ends on the `Suggested tests setting:` line.
  PROOF-288: no `Wrote the tests setting` line. PROOF-289: `tests` is still `[]`. PROOF-126's
  test failed too, by design: it now reads the three lines above the question.
- `dev/test_evidence_writer.py` on `main`'s `evidence.py`: `1 failed, 43 passed`, PROOF-21,
  `assert 'passed' == 'checked at sign-off'`.

## Lines a person reads that this lane chose

The plan gives every line the rules name. These it does not give:

| Line | Where |
|---|---|
| `Usage: purlin_status.py [--project-root DIR] [--spec NAME]` | `purlin_status.py --help`, and under a wrong command line |
| `Usage: purlin_drift.py [--project-root DIR] [--since N-or-date] [--json]` | `purlin_drift.py --help`, and under a wrong command line |
| `purlin: unknown argument <token>.` | either script, to stderr, exit 2 |
| `purlin: <flag> needs a value.` | either script, to stderr, exit 2 |
| `[--write-tests]` in both lines of `purlin_run.py`'s usage | `purlin_run.py --help` |

`evidence_format.md`, the table of a section's `rules` words, gains a first row:
`` `checked at sign-off` `` with `` every proof of the rule is `@manual`: no test is written for
it, so no run observes it and a person checks it in the sign-off walk ``. The sentence under the
table reads `` Where a `@manual` proof stands beside a proof that is not `@manual`, the rule
reads from the rows below the first. ``

## Calls this lane made that the plan did not

- **The path a refusal prints** is the folder as the call named it, made absolute, not its real
  path. `NO_PROJECT_HERE` printed it that way before.
- **`STARTED_IN` before `main` runs** is `None`, and `handle_request` then reads the working
  directory. Only a test that calls `handle_request` without `main` meets it.
- **`--write-tests` still prints the suggestion**, `No test command is set in
  .purlin/config.json, so nothing ran.` included, then `Wrote the tests setting to
  .purlin/config.json.`. RULE-102 as the plan words it prints that line whatever the answer.
  The line says `so nothing ran` above a run that then goes on; rewording it is a question for
  the owner, since four proofs and several pages quote it.
- **Where no tool is detected, no question is asked** and `--write-tests` writes nothing: there
  is no suggested setting to write. The run exits 1 as before.
- **The question is asked under `--test`, `--audit` and `--ci` alike.** A `--ci` run on another
  system has no input, so it writes nothing, as before.
- **The answer is read with its case and outer spaces set aside**: `Y` and ` yes ` are yes.
- **After a no, the question is the last thing printed, with no line end**, as PROOF-287 says.
- **`dev/run_project.py`, `_run`** now gives the run an input at its end, and takes `answer=`.
  Before, the run inherited pytest's own input, which at a terminal would wait for a person.
- **Two existing tests were changed, their proofs not**: `run_script` PROOF-126's test reads the
  three lines above the question, and PROOF-134's finds the `Suggested for jest:` line by its
  text. Both proofs hold as written.
- **`purlin_status.py --spec` counts rules and proofs from the spec reader** and takes the
  warnings from the payload, so it writes nothing: it does not refresh `.purlin/report-data.js`.
  The plain status does, as the tool does.
- **`purlin_drift.py` shares `purlin_status.py`'s command-line reader** rather than a third
  file.
- **Both scripts are mode 644**, as `purlin_run.py` is; a skill starts them through the
  interpreter.
- **Paths are compared with `os.path.normcase` too**, so a Windows path that differs in case
  alone is the same folder.
- **A checkout with no commit** makes `purlin_drift.py` print `no commits: <reason>` and exit 2,
  the same way as a `since` it refuses.

## Left, or waiting on another lane

- **`words`**: the skills, `docs/` and `references/purlin_commands.md` name
  `scripts/run/purlin_status.py`, `scripts/run/purlin_drift.py`, `--spec`, `--since`, `--json`
  and `--write-tests`. All exist as K5 and K8 write them, so `purlin_agent` PROOF-51 and
  PROOF-52 can clear at integration.
- **`surfaces`**: `scripts/mcp/purlin/states.py`'s opening comment still says a rule whose every
  proof is `@manual` reads `passed` with no test. Its lane changes that.
- **`signoff`**: `package.py` reads a section's `rules` word. This lane now writes
  `checked at sign-off` there; `package_format.md` version 12 is that lane's.
- **CLAUDE.md's step 4** for a format change, the grep of `docs/`, `skills/`, `references/` and
  `agents/purlin.md`: run, and nothing there restates the old word for a section. Nothing to
  hand on.
- **Not done here, by the plan**: the Windows run. `project._within` and `same_repository` have
  no test on Windows; the coordinator's Windows run is the first.
- No file of another lane was changed.

## Acceptance

`server` PROOF-170 failed first. The three test files:

```
152 passed in 85.15s (0:01:25)
```

`bash dev/run_tests.sh --fast`:

```
================== 846 passed, 9 skipped in 947.56s (0:15:47) ==================
Suites: 1 passed, 0 failed
```
