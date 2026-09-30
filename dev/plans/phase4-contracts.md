# Phase 4 contracts: what lanes produce and consume, word for word

Written by the planning agent on 2026-09-30 for sanity check 3 (`sanity-3.md`) and the owner's
answers of decision 98. Every agent builds to this file and none chooses. `phase4-plan.md` says
who owns what; each brief under `phase4-lanes/` repeats the parts its lane needs.

In the strings below, `<feature>`, `<name>`, `<RULE-N>`, `<PROOF-N>`, `<n>`, `<sha7>`, `<path>`,
`<gate>`, `<suite>`, `<System>` (`Windows`, `macOS` or `Linux/Unix`, from
`evidence.os_word(<stored word>)`) and `<Systems>` (two or more `<System>` in the order
`Linux/Unix`, `macOS`, `Windows`, joined by `, ` and a last ` and `) are filled in; everything
else is literal. A line shown in a fenced block is one printed line unless the block says
otherwise. `<value>` is the value as JSON writes it (`"gold"`, `3.5`, `["x"]`).

Words a person reads that no decision gives were chosen by the planning agent; each is listed
for the owner in `phase4-plan.md` section 12 and is built as written here.

## K1. The step alone before fan-out 1: P1 `shared`

P1 lands these before any lane starts. No lane changes their names, shapes or words.

### K1.1 One ending for a project with no spec (faults 2 and 3; section 6 item 13)

`scripts/mcp/purlin/status.py` gains `no_spec_lines(project_root) -> list[str]`, two lines, the
first always `No specs found under specs/.`, the second by the state of the project:

| State | Second line |
|---|---|
| no `.purlin/config.json` | `→ Run: purlin:init to set this project up.` |
| set up, and the tree holds code | `→ Run: purlin:spec-from-code to write the specs this code already implies.` |
| set up, and the tree holds no code | `→ Run: purlin:spec <name> to write the first spec.` |

`<name>` is written literally. "The tree holds code" (technical call): `git ls-files --cached
--others --exclude-standard` lists a file outside `specs/`, `.purlin/`, `.github/` and `docs/`
whose extension is one of `.py .pyi .js .jsx .mjs .cjs .ts .tsx .cs .fs .vb .go .java .kt .rb
.php .rs .swift .c .h .cc .cpp .hpp .m .scala .sql .sh .ps1`. `NO_SPECS` goes. Every surface
that meets a project with no spec prints the two lines and nothing else there:
`status.sync_status` (returns them joined by a newline), `scaffold.next_step` (its last lines),
`update._print_ending` (after the blank line it prints today) and `purlin_run.main` (then exit
1, as today).

### K1.2 The warning for rule lines with no number (answer 14)

`scripts/mcp/purlin/payload.py` builds the line in the shape of the spec mistakes, with no path
and no prefix:

```
<feature>: 1 line under ## Rules is not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>.
```

```
<feature>: <n> lines under ## Rules are not numbered; a rule is `- RULE-N: <text>`. Run purlin:spec <feature>.
```

It stays where it is in `warnings`: after the unread-tags line and before `spec_mistakes`.

## K2. Printed lines, by lane

Each row replaces the old line with the new one, character for character; a line with no old
form is new. The source is the section and item of `sanity-3.md`, or the answer of decision 98
(`A<n>`). Every spec proof and every test that quotes an old line changes with it, in the lane
that owns them; a quote in a file the lane does not own is K6's.

### K2.1 `core`

| Id | Old | New | Source |
|---|---|---|---|
| core-1 | `windows: no run yet` (a cell reason) | `<System>: no run yet`, e.g. `Windows: no run yet` | §7 fault 7, §6 item 5 |
| core-2 | `passed on linux, macos` | `passed on <Systems>` or `passed on <System>`, e.g. `passed on Linux/Unix and macOS` | §6 item 5 |
| core-3 | `windows: failed` | `<System>: <word>`, e.g. `Windows: failed` | §6 item 5 |
| core-4 | `failing: macos, local` | `failing: <System>, <source>`, e.g. `failing: macOS, local` | §6 item 5 |
| core-5 | `"gate" is 'gold', which is not one of passed, strong, signed; reading it as 'passed'` | `<value> is not accepted for gate in .purlin/config.json; it takes passed, strong or signed. Reading it as passed; set it with purlin:init --gate <gate>.` | §6 items 11, 39 |
| core-6 | `"audit_parallel" is 'four', which is not a whole number from 1 to 16; reading it as 4` | `<value> is not accepted for audit_parallel in .purlin/config.json; it takes a whole number from 1 to 16. Reading it as 4; fix the file by hand.` | §6 item 39 |
| core-7 | `1 spec names no files, so its tests run every time: export.` | `1 spec names no files, so its tests run every time: <name>. Run purlin:spec <name> to add its > Scope: line.` | §6 item 21 |
| core-8 | `<n> specs name no files, so their tests run every time: <names>.` | `<n> specs name no files, so their tests run every time: <names>. Run purlin:spec with each name to add its > Scope: line.` | §6 item 21 |
| core-9 | `<name>: the source could not be read (<error>).` | `<name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` | §6 item 12 |

In core-5 `<gate>` is written literally, and core-6 keeps `4`, the value it reads the setting
as. The status's lines for a pin behind its source and for a source with no pin do not change
(K3.5).

### K2.2 `anchors`

| Id | Old | New | Source |
|---|---|---|---|
| anchors-1 | (new) | `<feature>: > Requires: names <other>, which is not an anchor, so its rules do not apply. Run purlin:spec <feature>.` | A8 |
| anchors-2 | `<count> tags this release does not read (<tags>); they are ignored: <files><more>` | the same, then `. Run purlin:init --update to remove them.` | §6 item 20 |
| anchors-3 | `no run on macos yet` | `no run on <System> yet`, e.g. `no run on macOS yet` | §6 item 4, fault 7 |
| anchors-4 | `<path> is not valid JSON; it is ignored.` | `<path> is not valid JSON; it is ignored. <fix>` | §6 item 34 |
| anchors-5 | `<path> is not a JSON object; it is ignored.` | `<path> is not a JSON object; it is ignored. <fix>` | §6 item 34 |
| anchors-6 | `<path> carries the schema <x>, not <y>; it is ignored.` | `<path> carries the schema <x>, not <y>; it is ignored. <fix>` | §6 item 34 |
| anchors-7 | `<path> names the source <x> but sits in <folder>/; it is ignored.` | `<path> names the source <x> but sits in <folder>/; it is ignored. <fix>` | §6 item 34 |

`<fix>` is `Run purlin:test <feature> to write it again.` for a file under `local/` and
`Run purlin:test --remote to write it again.` for a file under `ci/`, where `<feature>` is the
file name without `.json`. anchors-1 is one line per spec and name, in `specs.spec_mistakes`,
after the five lines of decision 97, sorted by feature then by name; `<other>` is a name the
spec's `> Requires:` holds that is a spec in the project and not an anchor. A name no spec
carries is not warned of.

### K2.3 `settings`

| Id | Old | New | Source |
|---|---|---|---|
| settings-1 | `Error: 'key' is required for write action.` | `A change needs a key; nothing was saved.` | §6 item 33 |
| settings-2 | `Set 'gate' = "strong"` | `<key> is now <value>; saved to .purlin/config.json.`, e.g. `gate is now "strong"; saved to .purlin/config.json.` | §6 item 42 |
| settings-3 | `No Purlin workspace at <root>: .purlin/config.json is not there. That root came from <source>.` | `No Purlin project root at <root>: .purlin/config.json is not there. That root came from <source>.` | §6 item 37 |
| settings-4 | `→ Fix: pass project_root to this tool, or set PURLIN_PROJECT_ROOT to the workspace directory (in .claude/settings.json "env" for the project), or run purlin:init there.` | `→ Fix: pass project_root to this tool, or set PURLIN_PROJECT_ROOT to the project root (in .claude/settings.json "env" for the project), or run purlin:init there.` | §6 item 37 |
| settings-5 | tool schema: `Directory of the Purlin workspace (the one holding .purlin/). Defaults to the root the server resolved at startup.` | `The project root, the folder holding .purlin/. Defaults to the root the server resolved at startup.` | §6 item 37 |

### K2.4 `drift`

| Id | Old | New | Source |
|---|---|---|---|
| drift-1 | `anchor <name> is behind its source (now <sha>). Run: purlin:anchor sync <name>.` | `anchor <name>: the pin <old7> is behind its source, now <new7>. Run purlin:anchor sync <name>.` | §6 items 12, 41 |
| drift-2 | `anchor <name> names a source and no pin. Run: purlin:anchor sync <name>.` | `anchor <name>: names a source and no pin. Run purlin:anchor sync <name>.` | §6 items 12, 41 |
| drift-3 | `anchor <name>: its source could not be read (<error>).` | `anchor <name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` | §6 item 12 |
| drift-4 | `<files> changed under <feature>'s scope: <behind>.` | the same, then ` Run purlin:test <feature>.` | §6 item 19 |
| drift-5 | `<k> changed file(s) is/are under no spec's scope: <files>.` | the same, then ` Add each to a spec's > Scope: line with purlin:spec.` | §6 item 19 |
| drift-6 | `<n> rule(s) has/have no test: <rules>.` | the same, then ` Run purlin:build.` | §6 item 19 |
| drift-7 | `<n> feature(s) is/are out of date: <features>.` | the same, then ` Run purlin:test.` | §6 item 19 |
| drift-8 | `The last 1 commits`, `in the last 1 commits`, `Since the clone, <when>, the last 1 commits` | `The last commit`, `in the last commit`, `Since the clone, <when>, the last commit`; two or more stay as they are | §6 item 7 |
| drift-9 | `...; refusing to pass '<x>' to git` | `...; refusing to pass <value> to git` | §6 item 39 |

drift-4 to drift-7 keep their own words, and the added sentence follows the full stop. In
drift-1 `<old7>` and `<new7>` are the pinned and the source's shas cut to 7 characters.

### K2.5 `run`

| Id | Old | New | Source |
|---|---|---|---|
| run-1 | `purlin_run.py --help` refused, exit 2 | `--help` and `-h` print the usage to stdout and exit 0 | fault 19 |
| run-2 | `purlin: a remote runner runs the tests, so --remote belongs to --test. Run: purlin:test --remote.` | `purlin: a remote runner runs the tests, so --remote belongs to --test. Run purlin:test --remote.` | §6 items 40, 41 |
| run-3 | `purlin: --commit belongs to --test and --audit; a remote run commits on the runner.` | `purlin: --commit belongs to --test and --audit; a remote run commits on the runner. Run purlin:test --remote without --commit.` | §6 item 40 |
| run-4 | `purlin: no spec named <name> under specs/.` | `purlin: no spec named <name> under specs/. Run purlin:status to see the specs this project has.` | §6 item 17 |
| run-5 | `No test command is set in .purlin/config.json, and no test tool Purlin knows was found, so nothing ran. Run purlin:test to have one proposed.` | `No test command is set and no test tool Purlin knows was found, so nothing ran. The agent reads the project and proposes a command for you to confirm.` | A15 |
| run-6 | `Evidence is missing: the <suite> suite timed out after <n> s on <path>.` | `Evidence is missing: the <suite> suite timed out after <n> s on <path>. Run purlin:<action> --arm-timeout <seconds> to give it longer.` | §6 item 14 |
| run-7 | `Evidence is missing: the <suite> suite timed out after <n> s.` | `Evidence is missing: the <suite> suite timed out after <n> s. Run purlin:<action> --arm-timeout <seconds> to give it longer.` | §6 item 14 |
| run-8 | `Evidence is missing: the <suite> suite <problem>.` (a report problem) | `Evidence is missing: the <suite> suite <problem>. Check its command and report in the tests setting of .purlin/config.json, then run purlin:test.` | §6 item 14 |
| run-9 | `Evidence is missing: 1 marker has no passing or failing result: <list>.` | `Evidence is missing: 1 marker has no passing or failing result: <list>. Check that its test ran and was not skipped, then run purlin:test.` | §6 item 14 |
| run-10 | `Evidence is missing: <n> markers have no passing or failing result: <list>.` | `Evidence is missing: <n> markers have no passing or failing result: <list>. Check that their tests ran and were not skipped, then run purlin:test.` | §6 item 14 |
| run-11 | `purlin: <suite problem>.` | `purlin: <suite problem>. Fix the tests setting in .purlin/config.json, then run purlin:test.` | §6 item 40 |
| run-12 | `<feature> <RULE-N> has no test. Run purlin:build <feature>.` for a rule none of whose proofs has a test | `<feature> <RULE-N> has no test for <PROOF-N>[, <PROOF-M>...]. Run purlin:build <feature>.`; `has no test.` stays only for a rule with no proof | fault 17, decision 97 |
| run-13 | `# Tests at <sha7>` (the table's heading, the newest section dirty) | `# Tests at <sha7>, with changes that are not committed` | fault 21 |
| run-14 | `jest needs the package jest-junit to write its report: run npm install --save-dev jest-junit` | the same, with `yarn add --dev jest-junit` where the project root holds `yarn.lock` and `pnpm add --save-dev jest-junit` where it holds `pnpm-lock.yaml` | fault 9 |

`<action>` is `test` or `audit`, the run's own; `<seconds>` is written literally. The suggested
entries (technical, no person's words): the jest `run` becomes
`JEST_JUNIT_OUTPUT_FILE={report} JEST_JUNIT_ADD_FILE_ATTRIBUTE=true JEST_JUNIT_CLASSNAME='{classname}' JEST_JUNIT_TITLE='{title}' JEST_JUNIT_ANCESTOR_SEPARATOR=' > ' npx jest --ci {files} --reporters=default --reporters=jest-junit`
(fault 4); the pytest `run` gains `--doctest-modules` after `-m pytest` where any file
`git ls-files` lists, other than under `specs/` and `.purlin/`, holds the text
`--doctest-modules` (A3). `references/supported_frameworks.md` shows both as the code builds
them.

### K2.6 `host`

| Id | Old | New | Source |
|---|---|---|---|
| host-1 | the line saying the GitHub CLI is not installed, printed after the push (`remote.py` 157-159) | before any push: `purlin:test --remote waits for the run with the GitHub CLI, gh, which is not installed, so nothing was pushed. Install gh, then run purlin:test --remote again.` | A12 |
| host-2 | `NO_AZ`, after the push | before any push: `purlin:test --remote waits for the run with the Azure CLI, az, which is not installed, so nothing was pushed. Install az with its azure-devops extension, then run purlin:test --remote again.` | A12 |
| host-3 | `No run registered for <branch> within 60 seconds. Open it on the git host, then run: git pull --ff-only origin <branch>` | `No run registered for <branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that the git host runs <workflow path> on a push to run/*, then run purlin:test --remote again.` | fault 15, §6 item 8 |
| host-4 | `NO_AZURE_RUN` (`remote.py` 90-93), which names `git pull --ff-only origin <branch>` for a branch it then deletes | `No run registered for <branch> within 60 seconds, so the run branch was deleted and nothing came back. Check that az has the azure-devops extension and is signed in, then run purlin:test --remote again.` | fault 15, §6 item 8 |
| host-5 | `The run finished red. The table below is what came back.` | `The run failed on the git host. The table below is what came back.` | §6 item 35 |
| host-6 | `purlin:test --remote needs a GitHub or Azure DevOps remote, and .purlin/config.json says ci: none.` | the same, then ` Add one with git remote add origin <url>, then run purlin:init.` | §6 item 18 |
| host-7 | `This checkout is not on a branch, so there is nothing to push.` | `This checkout is not on a branch, so there is nothing to push. Make one with git switch -c <name>, then run purlin:test --remote again.` | §6 item 18 |
| host-8 | `The push failed, so no run was started.` | `The push failed, so no run was started. Check that git push origin works from this checkout, then run purlin:test --remote again.` | §6 item 18 |
| host-9 | `<path> is not the workspace this job checked out, so no evidence was committed.` | `<path> is not the project root this job checked out, so no evidence was committed.` | §6 item 37 |
| host-10 | `A proof in specs/ is tagged @env for windows, which this machine is not, so only a runner can prove it.` | one system: `A proof in specs/ is tagged @env for <System>, which this machine is not, so only a runner can prove it.`; two: `Proofs in specs/ are tagged @env for <Systems>, which this machine is not, so only a runner can prove them.` | §6 item 3 |
| host-11 | `A test is tagged @env for windows, which this machine is not, so only a runner can run it.` | one system: `A test is tagged @env for <System>, which this machine is not, so only a runner can run it.`; two: `Tests are tagged @env for <Systems>, which this machine is not, so only a runner can run them.` | §6 item 3 |

`<workflow path>` is `.github/workflows/purlin.yml`, the path `workflow.workflow_path('github')`
answers. host-1 and host-2 are checked after the checks of settings, `ci: none`, the branch,
the uncommitted tree and the Azure remote, and before `Pushing <branch> as <run branch>.`: the
push starts no process when the program is missing. The template comments, in
`templates/purlin.yml`, `templates/purlin.azure-pipelines.yml` and the fixture copy
`dev/fixtures/consumer-ci/.github/workflows/purlin.yml`:

| Old | New |
|---|---|
| `The matrix holds one job for each operating system the @env tags in specs/ name, and no other.` | `The matrix holds one job for each operating system a proof in specs/ is tagged @env for that the machine running setup is not, and no other.` |
| `The run caps each arm at an hour of its own.` | `The run caps each test command at an hour of its own.` |
| `installs the libraries a Linux runner lacks` | `installs the libraries a Linux/Unix runner lacks` |

Each keeps its line wrapping at the comment's width; nothing else in the templates changes, and
the step the `winfix-1` branch adds is left as that branch wrote it.

### K2.7 `mutation`

| Id | Old | New | Source |
|---|---|---|---|
| mutation-1 | `unknown engine "<x>": no breaks were made` | `mutation_engine names "<x>", which is not an engine: set it to none, auto, mutmut, stryker or stryker_net` | §6 item 32 |
| mutation-2 | `<file> carries no <section> block, so mutmut would break files no spec scopes: run "purlin:init" to write it` | `<file> carries no <section> block, so mutmut would break files no spec scopes: run purlin:init to write it` | §6 item 32 |

Both stay reasons in C3.2's form (lower case, no full stop), since the run prints
`purlin: <reason>` and the cell reads `strength not measured: <reason>`.

### K2.8 `reports`

| Id | Old | New | Source |
|---|---|---|---|
| reports-1 | `purlin: <feature> <ID> at <file>:<line> is tied to no test` | `<file>:<line> names <feature> <ID> and no test follows it. Put the comment directly above a test, or run purlin:build to repair it.` | §6 items 15, 40 |
| reports-2 | `purlin: the report's <case> matches <n> tests in <files>, so its result is not counted` | `The report's <case> matches <n> tests in <files>, so its result is not counted. Give the tests different names, then run purlin:test.` | §6 items 15, 40 |
| reports-3 | `purlin: <feature> <RULE-N> at <file>:<line> names a rule that has proofs; name one of them` | `<file>:<line> names <feature> <RULE-N>, which has proofs; a comment names one of its proofs. Correct the comment, or run purlin:build to repair it.` | §6 items 16, 40 |

The suite problems of `markers.py` keep their words; the run adds the step (run-11).

### K2.9 `scaffold`

| Id | Old | New | Source |
|---|---|---|---|
| scaffold-1 | `This is not a git repository. Run git init, then init.` | `This is not a git repository. Run git init, then purlin:init.` | §6 item 1 |
| scaffold-2 | `What must be true of every rule before a version is proven?` | `What must be true of every rule before a version is finished?` | §6 item 28 |
| scaffold-3 | `purlin: "<answer>" is not a gate; reading it as <gate>.` | `<value> is not accepted for gate; it takes passed, strong or signed. Reading it as <gate>.` | §6 item 11 |
| scaffold-4 | `--gate gold`: argparse's `invalid choice: 'gold' (choose from ...)` | `<value> is not accepted for gate; it takes passed, strong or signed. Nothing was written.`, to stderr, exit 2 | §6 item 39 |
| scaffold-5 | `<framework>: Stryker measures the breaks. Without it test strength is not measured.` | only where the engine is not installed: `<framework>: <the engine's own not-installed reason>`, e.g. `jest: stryker is not installed: run "npm install --save-dev @stryker-mutator/core"`, `dotnet: dotnet stryker is not installed: run "dotnet tool install -g dotnet-stryker"`, `dotnet: dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`; nothing where it is installed | fault 10 |
| scaffold-6 | the breaking question, then `[n]: ` on a line of its own | one line, `Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N] `, the answer read on that line; with `--yes` the line ends `[y/N] n` | fault 11 |
| scaffold-7 | (new) | the commit question, K3.9 | A10 |
| scaffold-8 | `skipped the CI workflow (...)` | `skipped the runner file (...)` at every gate | §6 item 29 |
| scaffold-9 | `No remote runner: <reason>.` then `skipped ... (<reason>)` | the one line `skipped the runner file (<reason>)`, where `<reason>` is `workflow.no_reason(gate)` | fault 14 |
| scaffold-10 | `A remote runner is written because:` and its reasons, printed before the file is known to be written | printed only when the runner file is written, after the prerequisites are checked | fault 13, §6 item 2 |
| scaffold-11 | `  the matrix is <images>, the systems the @env tags in specs/ name that this machine is not.` | `  it runs on <images>, the systems a proof in specs/ is tagged @env for that this machine is not.` | §6 item 45 |
| scaffold-12 | `copied <source> -> <rel>` | `copied <source> to <rel>` | §6 item 36 |
| scaffold-13 | `wrote .gitignore` twice | each path is named once | fault 12 |

scaffold-5's reasons are the engine modules' own constants (`stryker.NOT_INSTALLED`,
`stryker_net.NO_STRYKER`, `stryker_net.NO_DOTNET`), imported, never retyped. The file
`templates/evidence-readme.md` (fault 20; decision 50) reads, whole:

```
# Evidence

What a run leaves behind for each feature: each proof's result on each operating system, the
commit and the time. There is one JSON file per feature per source:

<the template's fenced block of the two paths, unchanged>

The folder is the source. A run on your own machine writes `local/`, and `--commit` commits it
under your own git identity. A remote runner writes `ci/` and commits it through the git host.
Every file here is tracked, because the point of the files is that somebody who did not make
the run can read them. You do not edit anything here by hand.

The format is `references/formats/evidence_format.md` in the Purlin plugin.
```

The block above is the file's text, with the template's own fenced block of the two paths,
`.purlin/evidence/local/<feature>.json   a person's own run` and
`.purlin/evidence/ci/<feature>.json      a remote runner's run`, where the placeholder line
stands. The first sentence and the sentence after `The folder is the source.` change; nothing
else does.

### K2.10 `update`

| Id | Old | New | Source |
|---|---|---|---|
| update-1 | `<n> spec(s) has/have no > Scope: line: <names>. Run purlin:spec <name> to add one. The line is optional below the gate signed and required at signed.` | `status.incomplete_line(names)`: core-7 or core-8 | §6 item 21 |

The pending list is read again after each migration it applies (fault 16), so one run applies
`kind-tags` to a line `os-tags` has just rewritten.

### K2.11 `signing`

| Id | Old | New | Source |
|---|---|---|---|
| signing-1 | `sign: the signature commit was not made. Check that signing works and that the files are not already committed.` | `The signature commit was not made: <git's own message>. Nothing was signed; run purlin:sign again once git can make a signed commit.` | §6 item 31 |
| signing-2 | `No version: nothing in this project states one. Name it with --release <version>, or write it to a VERSION file.` | `No version: nothing in this project states one. Run purlin:sign --release <version>, or write it to a VERSION file.` | §6 item 22 |
| signing-3 | `No tag: <tag> is already written. Name another with --release <name>.` | `No tag: <tag> is already written. Run purlin:sign --release <name> to name another.` | §6 item 22 |
| signing-4 | `No tag: the evidence package was not committed: the committed evidence still has work left to do.` | `No tag: the committed evidence still has work left to do, so no evidence package was committed. Run purlin:test --commit, then purlin:sign.` | §6 item 23 |
| signing-5 | `sign.py: not a directory: '<path>'` | `sign.py: <path> is not a directory.` | §6 item 39 |
| signing-6 | (new) at `signed`, on the line of a signed rule whose feature's spec names no files | `  <feature> <RULE-N>   does not count until the spec names its files: purlin:spec <feature>` | A9 |

signing-1's `<git's own message>` is taken as `NO_TAG_GIT`'s is (the first line starting
`fatal: ` or `error: `, that word cut, a closing full stop cut; `git exited with <n>` where git
printed nothing). signing-4 replaces the line only for `package.WORK_LEFT`; any other reason
keeps `No tag: the evidence package was not committed: <why>.` signing-6 replaces the plain
`  <feature> <RULE-N>` line under `Signed <n> rules as ...`; the walk prints the same line for
each such rule it signed, after its case lines and before `Signed <n> rules as ...`. The walk's
audit lines are K3.1.

### K2.12 `review`

| Id | Old | New | Source |
|---|---|---|---|
| review-1 | `  Nothing backs this rule yet.` | `  No test yet. Run purlin:build <feature>.` | §6 item 27 |
| review-2 | `Test strength: 90 percent   minimum 70` (the printout) | `Test strength 90%, against a minimum of 70%.` | §6 item 25 |
| review-3 | `  Strong, by <model> at <at>.` and the other verdicts | the verdict lines of K3.1, then `  Read by <model> at <at>.` | §6 item 24 |
| review-4 | `ai_audit.py: not a directory: '<path>'` | `ai_audit.py: <path> is not a directory.` | §6 item 39 |

The model's prompt keeps `Test strength: 71 percent (minimum 80)` and
`Test strength: not measured`: no person reads it (`references/review_criteria.md` is its home).

### K2.13 `package`

| Id | Old | New | Source |
|---|---|---|---|
| package-1 | `No version: nothing in this project states one. Name it with --release <version>.` | `No version: nothing in this project states one. Run purlin:export --release <version>, or write it to a VERSION file.` | §6 item 22 |
| package-2 | `package.py: not a directory: '<path>'` | `package.py: <path> is not a directory.` | §6 item 39 |

### K2.14 `upstream`

| Id | Old | New | Source |
|---|---|---|---|
| upstream-1 | `<name>: the source could not be read (no anchor named <name> carries a git source).` | `<name>: no anchor named <name> carries a git source. Run purlin:status to see the anchors this project has.` | §6 item 6 |
| upstream-2 | `  1 rules. Run purlin:status to see them.` | `  1 rule. Run purlin:status to see it.`; two or more stay | §6 item 7 |
| upstream-3 | `<name>: the pin is current.` | `<name>: the pin is current. Run purlin:status <name> to see its rules.` | §6 item 30 |
| upstream-4 | `<name>: <summary>. Pin advanced from <old7> to <new7>.` | `<name>: <summary>. Pin advanced from <old7> to <new7>. Commit it as anchor(<name>): sync (<new7>), then run purlin:test.` | §6 item 30 |
| upstream-5 | `<name>: the source could not be read (<error>).` | `<name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.` | §6 item 12 |
| upstream-6 | `No Purlin workspace found. Pass --project-root DIR.` | `No Purlin project root found. Pass --project-root <dir>.` | §6 item 37 |
| upstream-7 | help: `the workspace holding .purlin/ and specs/` | `the project root holding .purlin/ and specs/` | §6 item 37 |

upstream-1 is the line for a name no anchor carries; the row's `error` field reads
`no anchor named <name> carries a git source`, as upstream PROOF-31 has it.

### K2.15 `dashboard`

| Id | Old | New | Source |
|---|---|---|---|
| dashboard-1 | the Audit panel's lines | K3.1 | §6 item 24 |
| dashboard-2 | `Test strength <Math.round>%, against a minimum of <m>%.` | `Test strength <Math.floor>%, against a minimum of <m>%.`; the board keeps its floor | §6 items 9, 25 |
| dashboard-3 | `purlin:sign <feature> <RULE-N>` then `from Claude Code` | `Type purlin:sign <feature> <RULE-N> in Claude Code.` | §6 item 26 |
| dashboard-4 | `No test yet.` (a proof's test, the rule page) | `No test yet. Type purlin:build <feature> in Claude Code.` | §6 item 27 |
| dashboard-5 | `← Board` | `Back to the board` | §6 item 10 |
| dashboard-6 | the theme button's `◐` | the button's text is its label, `Dark theme` or `Light theme`, as its `title` already reads | §6 item 10 |

Small labels stay in capitals (A13): nothing in the stylesheet changes for them.

## K3. Lines two or more lanes share

Each is built once by its owner; the others consume it and quote it character for character.

### K3.1 What the audit found (lanes `review`, `signing`, `dashboard`; §6 item 24)

On all three surfaces, one line each, in this order (the terminal indents each two spaces, as
today; the page sets each as a line of its own):

| The audit | Lines |
|---|---|
| none for the current hashes | `No audit has read this rule's text, proof and test yet.` |
| strong, no finding | `Strong. It found nothing.` |
| strong, with findings | `Strong.`, then each finding |
| weak | `Weak.`, then each finding |
| undecided | `Undecided. The AI audit could not decide, so the rule reads weak until its proof or test changes.`, then each finding |

The apostrophe is `'` (U+0027) on every surface. `ai_audit.py --rule` then prints
`  Read by <model> at <at>.` (`<model>` or `unknown`, `<at>` or `an unknown time`) and each
note, `  Note: <note>`; the walk prints no read-by line; the page keeps its own read-by line.

### K3.2 No test yet (lanes `review`, `dashboard`; §6 item 27)

Terminal (`ai_audit.py --rule`, under `Test`): `  No test yet. Run purlin:build <feature>.`
Page: `No test yet. Type purlin:build <feature> in Claude Code.`

### K3.3 Test strength (lanes `review`, `dashboard`; §6 items 9, 25)

`Test strength <p>%, against a minimum of <m>%.` where `<p>` is the whole-number part of the
share (floor) on every surface, and `<m>` is `min_strength`.

### K3.4 A value not accepted for gate (lanes `scaffold`, `update`, `core`, `settings`; §6 item 11)

| Where | Line |
|---|---|
| setup's and the upgrade's typed answer (`scaffold.NOT_A_GATE`, printed by both) | `<value> is not accepted for gate; it takes passed, strong or signed. Reading it as <gate>.` |
| setup's `--gate` flag | `<value> is not accepted for gate; it takes passed, strong or signed. Nothing was written.` |
| the settings file (core-5) | `<value> is not accepted for gate in .purlin/config.json; it takes passed, strong or signed. Reading it as passed; set it with purlin:init --gate <gate>.` |
| the settings tool (unchanged, decision 97) | `<value> is not accepted for gate; it takes passed, strong or signed. Nothing was saved.` |

### K3.5 An anchor's pin (lanes `core`, `drift`, `upstream`; §6 item 12)

The status and `purlin:anchor sync --check` print these; drift prints them after `anchor `:

```
<name>: the pin <old7> is behind its source, now <new7>. Run purlin:anchor sync <name>.
<name>: names a source and no pin. Run purlin:anchor sync <name>.
<name>: the source could not be read (<error>). Check its > Source: line, then run purlin:anchor sync <name>.
```

### K3.6 A spec that names no files (lanes `core`, `update`; §6 item 21)

core-7 and core-8, built by `status.incomplete_line(names)`; the upgrade calls it.

### K3.7 No version (lanes `package`, `signing`, `skills-sign`; §6 item 22)

package-1 and signing-2. The export and sign skills quote them where they quote the old lines.

### K3.8 System words in cell reasons (lanes `core`, `anchors`, `host`, `words`, `skills-author`; fault 7)

`<System>: no run yet`, `no run on <System> yet`, `passed on <Systems>`. `references/hard_gates.md`,
`references/glossary.md` (lane `words`), `references/spec_quality_guide.md` (lane
`skills-author`) and `references/formats/spec_format.md` (lane `anchors`) write the reason as
`<System>: no run yet`, for example `Windows: no run yet`. The payload's `missing_env`, the
evidence and every `@env(...)` keep the stored words.

### K3.9 Setup asks whether it may commit (lanes `scaffold`, `skills-author`, `words`; A10)

After the lines naming each file, and only when setup wrote or changed a file git does not
ignore, setup asks on one line and reads the answer on it:

```
Commit the files setup wrote? [y/N] 
```

An empty answer, the end of input, or anything but `y` or `yes` is no; on no nothing more is
printed. With `--yes` the question is not printed and the answer is yes. On yes setup runs
`git add -- <paths>` and `git commit -m "chore(init): set up Purlin at the gate <gate>" -- <paths>`
over exactly those files, so nothing else staged goes in, and prints:

```
Committed <sha7>, the files setup wrote:
```

then each path, indented two spaces, in the order setup named them. Where git refuses:

```
The files setup wrote are staged and not committed: <git's own message>.
```

`<paths>` are the files setup wrote or changed, the settings, `.gitignore`, the breaking tool's
configuration, `.purlin/evidence/README.md` and the runner file among them; never the ignored
`purlin-report.html`. The subject `chore(init): set up Purlin at the gate <gate>` is one row of
`references/commit_conventions.md` (lane `skills-author`), whose `Who commits it` cell reads
`purlin:init`.

### K3.10 No test tool (lanes `run`, `skills-run`, `words`; A15)

run-5. The test skill's row that matches `no test tool Purlin knows was found` stays, since the
new line holds that phrase. `references/purlin_commands.md` quotes run-5 in place of its old
line (lane `words`).

### K3.11 A remote run with no program to wait with (lanes `host`, `skills-run`, `words`; A12)

host-1 and host-2. The test skill says, in place of "a red run, no CLI, no run found or the wait
over exits 1": `With no gh on GitHub or no az on Azure DevOps it pushes nothing and names the program to install; a failed run, no run found or the wait over exits 1.`

### K3.12 `sync_status` and the project root (lanes `core`, `skills-author`, `skills-sign`, `skills-run`, `instructions`; §8 item 10)

Every first call of `sync_status` in a skill or the agent definition gains, right after
`` `sync_status` ``, the words:

```
with `project_root` set to the project root, the top folder of the git checkout
```

### K3.13 The runner file's name (lanes `scaffold`, `words`, `skills-author`; §6 items 29, 45)

A person reads `the runner file`, never `the CI workflow` or `the matrix`. The glossary's entry
(lane `words`) is K5.1.

## K4. Formats

### K4.1 Spec format 19 (lane `anchors`, in the commit that changes `specs.py`)

`references/formats/spec_format.md` goes from `> Format-Version: 18` to `19`: `> Requires:`
narrows to anchors and a new optional field, `> Highest-Rule:`, is added.

- The template line reads `> Requires: <comma-separated anchor names>` and the template gains,
  after `> Stack:`, the line `> Highest-Rule: <the highest rule number the spec has held>`.
- The metadata table's `> Requires:` row reads:
  `` | `> Requires:` | No | Comma-separated list of anchor names, the project's own or pinned, whose rules also apply. A name that is a feature's spec and not an anchor is warned of, and its rules do not apply | ``
- A new row after `> Stack:`:
  `` | `> Highest-Rule:` | No | The highest rule number the spec has ever held, as a whole number. A new rule takes the next number above it, so a deleted number is never used again. It changes no fingerprint and no count | ``
- In "Rules format", the sentence `A new id is one more than the highest the file has held since it was last written whole; a number deleted since then is never used again.` is replaced by:
  `` A new rule takes one more than the highest of `> Highest-Rule:` and every rule number the spec holds, and `> Highest-Rule:` is raised to it, so a number is never used again. ``
- "Requires behaviour" reads:
  `` When a spec declares `> Requires: design_tokens, api_contracts`, the rules of those anchors are counted with its own, labelled `required`, and its tests must prove them. An anchor's own `> Requires:` brings in the anchors it names in turn. A name in `> Requires:` that is a feature's spec and not an anchor is warned of, and its rules do not apply. An anchor with `> Global: true` applies to every feature spec without being named. ``
- The example proofs of "The manual tag", "Operating system tags" and "Rules that forbid
  something" are rewritten to `references/spec_quality_guide.md`: one case, what is done, what
  is observed, the value, no function or file names (§8 item 15). Their rule lines and tags
  stay.
- The reason `windows: no run yet` reads `Windows: no run yet` (K3.8).

No other format changes number. `references/formats/evidence_format.md` line 189 reads "of every
anchor it requires, transitively" (lane `run`, wording); `references/formats/package_format.md`'s
`requires` row reads "the names its `> Requires:` line holds" (lane `package`, wording);
`references/formats/marker_format.md` quotes reports-1 to reports-3 and says, where it says
which files are read for markers, that with no suite set the comments in every tracked file of
a language Purlin reads tests in are read (lane `reports`, wording);
`references/formats/anchor_format.md`'s example proof is rewritten to the guide (lane
`upstream`, wording). `references/drift_criteria.md` keeps `Criteria-Version: 10`: its quoted
lines follow drift-1 to drift-8 and `workspace` reads `project root` (wording).

### K4.2 `> Highest-Rule:` in this repository's specs

Every lane that owns a spec under `specs/` adds, to each spec it owns, after its last other
`>` line, `> Highest-Rule: <n>`, where `<n>` is the highest `RULE-<n>` of that spec's own
`- RULE-<n>:` lines in `git log -p --follow -- <spec>` (its own lines only, not ids a proof or
another spec names), and raises it with every rule it adds. A spec written for the first time
in this phase carries it from its first commit.

## K5. Reference and instruction sentences

### K5.1 `references/glossary.md` (lane `words`)

- New, after **remote run**: `` **runner file**: the file setup writes for the git host, `.github/workflows/purlin.yml` or `azure-pipelines.yml`, with one job for each system a proof is tagged `@env` for that the machine running setup is not. ``
- **scope**: `` It is optional below the gate `signed` and required at `signed`, where a rule of a spec that names no files is signed and its signature does not count. ``
- **anchor**, one sentence added: `` A feature spec names the anchors whose rules apply to it with `> Requires:`; `> Requires:` names anchors only. ``

### K5.2 `references/writing_style.md` (lane `words`; A13)

In **Casing.**, after `Uppercase is reserved for state badges ("PASSED", "STRONG", "SIGNED").`:

```
On the dashboard the design also sets small labels in capitals, such as `563 RULES TOTAL`.
```

### K5.3 `references/spec_quality_guide.md` (lane `skills-author`; A5, A6)

At the end of "Written for a person who cannot read code":

```
Where the product is a library, its public names are what a caller sees: a proof may name a function or class the library exports and an error type a caller gets back. A name from inside the code, a private helper or a module the package does not export, stays out.

- Poor: "`_split_fields` returns three parts for a line with two commas."
- Good: "`parse_line` given `a,b` raises `LineTooShort`, and its message names the line."
```

At the end of "One proof, one case":

```
One proof may name a list of like inputs that share one action and one kind of result: "Each of `0`, `-1` and `-0.5` is refused with `Amount must be positive`." Inputs that differ in what is done, or in the kind of result seen, are cases of their own.
```

"When a rule is stuck", the `<os>: no run yet` row: the word column reads
`` `not run`, with `<System>: no run yet` `` and its fix
`` Run `purlin:test --remote`, whose runner file names that system, or drop the `@env` tag if any operating system could show it. ``

### K5.4 `skills/spec-from-code/SKILL.md` (lane `skills-author`)

Within 130 lines. Each item names its source.

- **Before you start** (§8 items 10, 11, 14), in place of its paragraph:
  `` Call `sync_status` with `project_root` set to the project root, the top folder of the git checkout. When the project has no `.purlin/config.json`, run `purlin:init` first. Run `git branch --show-current`; when it prints nothing the checkout is on no branch, so make one with `git switch -c <name>` before the first commit. ``
- **Step 4** (A8, §8 item 7): `` 4. **Order by dependency.** Where features share rules, write those rules once in an anchor with `purlin:anchor create <name>`, first, and have each feature name it with `> Requires: <name>`. `> Requires:` names anchors only. ``
- **Step 5** (§8 items 1, 2): `` 5. **Write one spec at a time**, in that order, committing each spec with the comments it adds above existing tests, on its own, with the `spec(<name>):` prefix from `references/commit_conventions.md`. After each commit write `.purlin/runtime/spec-from-code.json`, `{"features": [<the agreed list, in order>], "written": [<each feature committed so far>]}`; a session that finds it goes on with the first feature not in `written`. ``
- **Step 6** (§8 item 16): `6. **Report.** Print one line per feature: its rules, its proofs, how many proofs an existing test already shows, and how many have no test. Then each test left untied, with its reason, and last the source files that got no rule, for a person or an agent to decide.`
- **Where the proofs come from**, the reasons (A3, A4, §8 items 3, 4, 17, 18): `Tie every test the project already has. A test is left untied for one of five reasons, and the report lists each such test with its reason: it shows only part of what a rule needs, it repeats a test already tied, it tests code the project does not own, it cannot carry a comment (an example inside a function's documentation), or it tests code no caller can reach. A test of the test suite's own helpers tests code no caller can reach. A test that is commented out, or a benchmark the project's test command does not run, is not a test: leave it and count it nowhere.`
- **What not to do**, in place of the private-helper bullet (A4, §8 items 4, 17): `` - Do not write a rule for code no caller outside the project can reach: list its files among the files with no rule. A caller reaches what the package exports: in Python, the names a module's `__all__` lists, or with no `__all__` the names with no leading underscore in a module whose own name has none; in JavaScript, what `package.json`'s `main` or `exports` reaches; in C#, the `public` types of a project that is not a test project. ``
- **When you are done** (§8 item 8): `Report the counts, then name the first of these that applies:` then the numbered list
  `` 1. Rules whose existing tests now carry their comments: `→ Run: purlin:test`, which suggests the test command and runs them. ``,
  `` 2. Rules with no test at all: `→ Run: purlin:build <name>` on the feature with the most of them. ``,
  `` 3. At the gate `passed`, with every rule passing and the team wanting the paper trail: `→ Run: purlin:init --gate strong`. ``
- Each spec it writes carries `> Highest-Rule: <n>` (A7).

### K5.5 `skills/spec/SKILL.md` "Ids" (lane `skills-author`; A7)

In place of the section's first two paragraphs and the procedure's step 5:

```
A new rule takes one more than the highest of `> Highest-Rule:` and every rule number in either copy of the spec, the working copy and `origin/main`'s, read with `git show origin/main:<spec>`. Write that number into `> Highest-Rule:`, adding the line after the spec's other `>` lines where it is missing, so a deleted number is never used again. Proof ids are allocated the same way against the proof numbers of both copies.
```

Procedure step 5 reads `5. Allocate ids as "Ids" below says, never against the working tree alone.`

### K5.6 `skills/init/SKILL.md` (lane `scaffold`; A10, §8 item 9)

"The questions" lists three: the gate (its words scaffold-2), the breaking question at
`strong` and `signed`, and

```
3. **Committing**, whenever setup writes a file: `Commit the files setup wrote? [y/N]`. The default is no; a yes commits them in one commit, `chore(init): set up Purlin at the gate <gate>`.
```

and "Run it" says: `` Ask the person each question yourself. Pass `--mutation` when they say yes to breaking the code on purpose. Pass `--yes` when they say yes to the commit; otherwise run the script with its input empty, `< /dev/null`, so every question it would ask takes its default. `` The flag table's `--yes` row reads `Takes the default answer to every question and commits the files setup wrote`.

### K5.7 `skills/test/SKILL.md` (lane `skills-run`; §8 items 12, 13)

In the row for `Suggested tests setting: ...`, before "and ask once":

```
Compare each suggested command with how the project runs its tests itself, in its CI files, its manifest's scripts, `tox.ini` or `Makefile`: the interpreter, and options such as `--doctest-modules` or `--no-restore`; show the person each difference and offer the entry with the project's own. Run the line that says what a tool needs, as printed, once the person agrees.
```

The line count stays at or under 120: the lane cuts as many lines as it adds.

### K5.8 `references/commit_conventions.md` (lane `skills-author`)

- New row, before `chore:`: `` | `chore(init): set up Purlin at the gate <gate>` | The files setup wrote, once a person agrees or `--yes` is passed | `purlin:init` | ``
- The `spec(<name>):` row's "When" cell reads `` Creating or editing a spec or an anchor's local rules; from `purlin:spec-from-code`, with the comments it adds above the project's existing tests ``.

### K5.9 `references/purlin_commands.md` (lane `words`)

- `purlin:init`'s row, last column: `` A developer, once. Three questions at most: the gate, at `strong` and `signed` whether to break the code on purpose, and whether to commit what it wrote ``.
- The `purlin:init` prose `It commits nothing.` reads `` It commits the files it wrote in one commit, `chore(init): set up Purlin at the gate <gate>`, once you agree or with `--yes`. ``
- `purlin:test`'s syntax: `purlin:test [feature ...] [--all] [--arm-timeout <seconds>]`.
- The sentence on the CI job reads `` the CI job runs the same run script and writes its section under `.purlin/evidence/ci/`, which it always commits. That job is the workflow's to run and nobody types it. ``
- The quoted no-test-tool line is run-5; the remote-run lines quote host-1 and host-2 where the
  page names a missing program.
- The gate question (`hard_gates.md` line 22, lane `words`) is scaffold-2.

### K5.10 `RELEASE_NOTES.md` (lane `words`), under "Unreleased — 0.10.0"

```
- `> Requires:` names anchors only. A name that is a feature's spec is warned of, and its rules do not apply.
- A spec records the highest rule number it has held in `> Highest-Rule:`, so a deleted number is never used again. The spec format is at version 19.
- `purlin:init` asks whether it may commit the files it wrote, and with `--yes` commits them as `chore(init): set up Purlin at the gate <gate>`.
- `purlin:test --remote` with no `gh` on GitHub or no `az` on Azure DevOps pushes nothing and names the program to install.
- The first test run keeps running examples inside a function's documentation where the project's own test command ran them.
- At the gate `signed`, signing a rule whose spec names no files says, on that rule's line, that the signature does not count until the spec names them.
- Every system a person reads is written `Windows`, `macOS` or `Linux/Unix`.
```

## K6. Cross-lane expectations

A lane never edits a file it does not own. Before merging, each lane rebases on `main`, reruns
its own files and `--fast`, fixes its own files where a lane merged earlier changed a result
this table predicts, and reports every other failure with the test, the assertion and the value
seen.

| When this lane merges | What changes for other lanes' tests | Who adjusts |
|---|---|---|
| `core` | cell reasons read `<System>`; core-5, core-6, core-7, core-8, core-9 | `anchors`: schema_spec_format PROOF-55 and its test quote core-7; `run`: run_script PROOF-177 to 182 quote core-6; `update`: update PROOF-27 and PROOF-104 quote core-7 or core-8; `dashboard`: purlin_report PROOF-17, 100, 101 and the fixtures under `dev/fixtures/report/` read `<System>` where the tests build a live payload |
| `anchors` | a feature whose `> Requires:` names a feature spec no longer proves that spec's rules, and the status warns (anchors-1); `no run on <System> yet` (anchors-3) | `review`: ai_audit PROOF-49's fixture makes `login` an anchor under `specs/_anchors/`, and the proof's words follow; `run`: run_script PROOF-91 and its test read `no run on <System> yet` |
| `host` | host-10, host-11 | `scaffold`: scaffold PROOF-64, 129, 65, 51 and their tests; `update`: any proof quoting the reasons the upgrade prints |
| `scaffold` | scaffold-2, scaffold-3, scaffold-6; `--yes` commits the files setup wrote | `update`: update PROOF-46 to 48 and their tests; `run`: `dev/test_evidence_writer.py` near line 1361, where setup runs with `--yes`; `instructions`: `dev/test_purlin_version.py` near line 224 |
| `reports` | reports-1 to reports-3 | `run`: any test of `dev/test_run_script.py` quoting them |
| `run` | run-12 | `skills-run`: the test skill's Step 4 quotes both forms and keeps them |

No lane merged before one of these is affected by it (section 8 of the plan orders them).

## K7. Numbering, proofs, and the self-check

- **A new id** is one more than the highest the spec has ever held: the larger of its
  `> Highest-Rule:` (rules) and the highest of its own ids in `git log -p --follow -- <spec>`
  (rules, and proofs likewise). A deleted number is never reused. After this phase every spec
  carries `> Highest-Rule:` (K4.2).
- **One proof, one case** (decision 71, as A6 amends it): one starting situation, one action,
  what is seen, at most 60 words; a list of like inputs sharing one action and one kind of
  result is one case. Every proof written or reworded has a test of its own with the marker
  directly above it. A proof names no source file, no test, no test framework and no function
  inside the code; a library's public names and error types may appear (A5).
- **The statements with no rule** (`sanity-3.md` section 5): each gets, in the spec its row
  names in the plan's section 5, a rule and one proof per line or case it covers, each quoting
  the printed line character for character as the code prints it after this phase.
- **The self-check every brief ends on:** every proof one case in at most 60 words with a marked
  test of its own; every printed line character for character as K2 and K3 give it; no generated
  file staged (`scripts/report/purlin-report.html`, `purlin-report.html`, `.purlin/evidence/**`,
  `.purlin/tests.md`, `.purlin/report-data.js`, `.github/workflows/purlin.yml`, screenshots);
  no id reused; the lane's three most important changes broken on purpose, one at a time, and
  each seen to fail its test, then restored with `git checkout -- <file>`.

## K8. Fan-out 2: the pages

- Each page says what is (decision 63; writing style "What is, not what was"): every false
  statement of `sanity-3.md` section 3 for that page is corrected to its "What is true" cell,
  read again against the code as merged after fan-out 1, which wins where the two differ.
- Every sample of printed output is taken from a real run of the scripts in a scratch project
  under the lane's scratch folder: `scripts/init/scaffold.py`, `scripts/run/purlin_run.py`,
  `scripts/review/sign.py` with a signing key made in the scratch folder, `scripts/export/package.py`,
  `scripts/anchor/upstream.py`, and the `sync_status` text through `status.sync_status`. A
  command a model carries out (`purlin:spec`, `purlin:build`, `purlin:spec-from-code`, the AI
  audit's reading) is shown as what you type and the summary it ends on (A2), with the
  skill's own closing line where it has one (`Spec saved: <name>. Next: purlin:build <name>`).
- Diagrams are plain mermaid. Words follow `references/glossary.md` and
  `references/writing_style.md`. No page carries the line `If you leave, the markers are
  comments.` (A1), a section on removing Purlin (decision 70), advice to upload keys to the git
  host or to protect branches and tags (A11), or a statement about `[level: ...]`, a queue,
  `stale`, `meets the gate`, a trust setting or `--dry-run`.
- Every statement is covered by a rule: the lane names the spec and rule for each. A statement
  no rule covers is cut, or listed in the lane's report as a rule to add, in the words it would
  need, for integration to write with its proof and test.
- Lane `pages-start` writes `specs/instructions/purlin_docs.md`, scope `README.md,
  docs/index.md, docs/getting-started.md, docs/how-purlin-works.md`, with two rules and their
  proofs and tests in `dev/test_purlin_docs.py` (section 5, rows 6 and 7): the README's command
  table gives every command the purpose sentence `references/purlin_commands.md` gives it, word
  for word; every printed line quoted on those four pages is printed, word for word, by a run
  of the sample project the page describes, built by the test in a temporary folder.

## K9. The paragraph integration writes into `dev/plans/handoff.md` (§4 item 4, §8 item 19)

In place of the paragraph under "The model in one paragraph", whole:

```
A rule says what must be true. A proof says in plain language how that is shown. A test is
any test in the project's own suite with one comment above it, `purlin: <feature> PROOF-<n>`.
Three steps: `passed` (`purlin:test`), `strong` (`purlin:audit`, a model reading each test
against its proof, with optional mutation testing), `signed` (`purlin:sign`). The gate is the
last step every rule must reach, and every rule is asked what the gate asks. Evidence is one
file per feature, written by a run and committed with `--commit`; it goes out of date when the
spec, the covered code or the tests change, and a run with no feature named runs only what
changed. Every run ends on the summary and `Left to do`, one line per kind of work with its
command. `purlin:sign` walks the rules left `to test by hand` or `to sign` and, at the gate
`signed`, when nothing else is left and every result came from committed work, writes the
evidence package and the signed tag. Purlin makes no claim of compliance: it hands evidence to
a system of record.
```
