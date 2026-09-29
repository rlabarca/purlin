# Feature: mutation

> Description: Test strength is the share of the deliberate breaks made to the code that the
>   tests caught, as an integer percent. Four engines make those breaks, one per language
>   family: Stryker for jest and vitest, Stryker.NET for dotnet, mutmut for pytest, and the
>   empty engine for everything else. Selection reads the config and the detected frameworks
>   alone, so a caller can print the plan before anything runs; the install check happens
>   when the engine runs, and an engine that is not installed answers with the reason in
>   words rather than raising. Every engine answers in one shape, so the evidence carries the
>   same fields whichever one measured it.
> Scope: scripts/run/mutation/__init__.py, scripts/run/mutation/stryker.py, scripts/run/mutation/stryker_net.py, scripts/run/mutation/mutmut.py, scripts/run/mutation/none.py
> Stack: python/stdlib (importlib, subprocess, json, tempfile), Stryker, Stryker.NET, mutmut

## Rules

- RULE-1: With `mutation_engine` set to `auto`, jest and vitest select `stryker`, dotnet selects `stryker_net`, pytest selects `mutmut`, and go, shell and sql select `none`; the first detected framework that has an engine decides, and a project with no framework selects `none`
- RULE-2: A `mutation_engine` naming an engine wins over the detected frameworks, a name outside the four shipped engines reads as `none` rather than being guessed at, and a missing key reads as `none`, so mutation testing is off until a project turns it on
- RULE-3: Test strength is `killed / (killed + survived)` as an integer percent rounded half up, and is None when no break ran at all
- RULE-4: The rules of a feature are reported in rule-number order, so `RULE-2` comes before `RULE-10`
- RULE-5: Stryker runs once per feature against that feature's scope files alone, under a generated config naming `coverageAnalysis: "perTest"`, `disableBail: true`, the `json` reporter and the report path
- RULE-6: The Stryker test runner is `vitest` when the project's `package.json` declares vitest as a dependency, and `jest` otherwise
- RULE-7: The project's own `node_modules/.bin/stryker` is preferred over one on the PATH, and neither present leaves no engine with a line naming the package to install
- RULE-8: A break whose status is `killed`, `timeout` or, from mutmut, `caught by type check` counts caught; one whose status is `survived`, `nocoverage` or, from mutmut, `no tests` counts missed; and a break with any other status, such as Stryker's `CompileError` or mutmut's `skipped`, counts for neither
- RULE-9: A rule's number is what its own tests caught: a break its tests reached and did not catch counts missed for it, even when another rule's test caught it; a break that timed out counts caught for every rule whose test reached it; a break its tests never reached counts for neither; and a rule whose tests the report never lists measures nothing
- RULE-10: A test in the report is matched to a rule's test by its whole name, its titles joined by single spaces whether the name wrote them with ` > ` or not, so a name that begins another is not that test; and by its file, so a test of the same name in a different test file is not that test
- RULE-11: Attribution is `per_test` when any break names the test that caught it and `per_scope` when none does, and every rule then carries the feature's scope number
- RULE-12: A run that wrote no report, or whose report cannot be read, measures nothing for that feature and says so in the log rather than raising
- RULE-13: Stryker.NET is run as `dotnet stryker` with one `--mutate` per scope file, `--coverage-analysis perTest`, `--disable-bail`, `--reporter json` and `--output`, and its report is found by walking that output directory for `mutation-report.json`
- RULE-14: Without `dotnet` on the PATH there is no engine for C#, and with `dotnet` but no Stryker.NET installed the reason names the `dotnet tool install` command; the install check is `dotnet stryker --version` answering 0
- RULE-15: mutmut needs a config block naming the source paths and the test selection, written to `pyproject.toml` as `[tool.mutmut]` when that file exists and to `setup.cfg` as `[mutmut]` with one value a line otherwise; without the block no breaks are made and the reason names the block and the file
- RULE-16: The output of `mutmut results --all true` is read one line per break, and a line whose status is not one mutmut writes is not counted as a break
- RULE-17: A mutmut break counts for a feature when one of the feature's scope entries covers it, the entry's last path segments matching the first segments of the break's module name, so `src/login/session.py` covers `login.session`; a break no scope entry covers counts for no feature; and every rule of a feature carries that feature's scope number with `attribution: "per_scope"`
- RULE-18: Without mutmut installed there is no engine and the reason names `pip install mutmut`
- RULE-19: The empty engine measures nothing: every rule carries a score of None and `attribution: "unavailable"`, and, when no other reason is given, the reason reads `no engine breaks go, shell or sql code, so test strength is not measured for these rules`
- RULE-20: Every engine answers the same shape, so a caller reads one: an engine name outside the four is not run, a rule the engine never reported is filled in with `attribution: "unavailable"`, and a feature the engine never reached is still listed
- RULE-21: A scope entry naming a package's `__init__.py` covers a mutmut break in that file, which mutmut names after the package, and a scope entry holding `*` covers, as a glob, a break in any file it matches
- RULE-22: An engine invocation that runs past `--arm-timeout` measures nothing: every rule it was breaking and that feature's scope score carry a score of None with `attribution: "unavailable"` whatever report it left, mutmut's one run leaving every feature unmeasured and a Stryker or Stryker.NET run leaving only the feature it was breaking, and the answer's reason and log name the seconds and `--arm-timeout`

## Proof

- PROOF-1 (RULE-1): With `mutation_engine` set to `auto` and one framework detected, jest and vitest each give the engine `stryker`, dotnet gives `stryker_net` and pytest gives `mutmut`
- PROOF-23 (RULE-1): With `mutation_engine` set to `auto` and go, shell or sql the one framework detected, the engine is `none`
- PROOF-24 (RULE-1): With `mutation_engine` set to `auto`, pytest detected first and jest second, the engine is `mutmut`
- PROOF-25 (RULE-1): With `mutation_engine` set to `auto`, jest detected first and pytest second, the engine is `stryker`
- PROOF-26 (RULE-1): With `mutation_engine` set to `auto`, shell detected first and dotnet second, the engine is `stryker_net`: a framework with no engine does not decide
- PROOF-27 (RULE-1): With `mutation_engine` set to `auto` and no framework detected, the engine is `none`
- PROOF-2 (RULE-2): With `mutation_engine` set to `mutmut` in a project that detects jest, the engine is `mutmut`
- PROOF-28 (RULE-2): With `mutation_engine` set to `none` in a project that detects pytest, the engine is `none`
- PROOF-29 (RULE-2): With `mutation_engine` set to `cosmic-ray`, a name no shipped engine has, in a project that detects pytest, the engine is `none`, not `mutmut`
- PROOF-30 (RULE-2): With settings that name no `mutation_engine`, whether they hold other keys or none at all, a project that detects pytest gets the engine `none`, and so does one that detects jest
- PROOF-3 (RULE-3): Test strength reads 50 for 1 break caught and 1 missed, 67 for 2 caught and 1 missed, 33 for 1 and 2, 71 for 5 and 2, 64 for 7 and 4, 100 for 1 caught and none missed, and 0 for none caught and 1 missed
- PROOF-31 (RULE-3): A split that lands exactly on a half rounds up: 1 caught and 7 missed, 12.5, reads 13, not 12, and 3 caught and 5 missed, 37.5, reads 38
- PROOF-32 (RULE-3): With no break caught and none missed, test strength reads None, not 0
- PROOF-4 (RULE-4): Asked about one feature whose rules arrive in the order RULE-10, RULE-2, RULE-1, the empty engine answers that feature's rules in the order RULE-1, RULE-2, RULE-10
- PROOF-5 (RULE-5): A Stryker run of `calc`, scoped to `src/calc.js` and `src/util.js` in a project that does not declare vitest, gives Stryker a config holding exactly those two files to break, `coverageAnalysis` `perTest`, `disableBail` true, the `json` reporter, the runner `jest` and the path of a report, and nothing more
- PROOF-33 (RULE-5): A Stryker run of `calc`, scoped to `src/calc.js`, whose Stryker writes the captured report to the path its config names, starts `stryker run` once, with a config that breaks `src/calc.js` alone, and answers engine `stryker`, available, with the feature at 64, its RULE-2 at 71, and a log naming `calc`
- PROOF-34 (RULE-5): A Stryker run over `calc`, scoped to `src/calc.js`, and `util`, scoped to `src/util.js` and `src/fmt.js`, starts Stryker exactly twice: the first config breaks `src/calc.js` alone and the second breaks `src/util.js` and `src/fmt.js` alone
- PROOF-6 (RULE-6): A project whose `package.json` lists vitest under `devDependencies` gives Stryker the runner `vitest`
- PROOF-35 (RULE-6): A project whose `package.json` lists vitest under `dependencies` gives Stryker the runner `vitest`
- PROOF-36 (RULE-6): A project whose `package.json` lists only jest gives Stryker the runner `jest`
- PROOF-37 (RULE-6): A project with no `package.json` gives Stryker the runner `jest`
- PROOF-7 (RULE-7): With a Stryker in the project's `node_modules/.bin/` and another on the PATH, a run starts the project's own once and never starts the one on the PATH
- PROOF-38 (RULE-7): With no Stryker in the project and none on the PATH, a run answers engine `none`, not available, with the reason `stryker is not installed: run "npm install --save-dev @stryker-mutator/core"`, and the feature's rule at score None with `attribution: "unavailable"`
- PROOF-8 (RULE-8): A Stryker report of 12 breaks to one file, 6 `Killed`, 1 `Timeout`, 2 `Survived`, 2 `NoCoverage` and 1 `CompileError`, gives the feature 7 caught and 4 missed, 64: the `CompileError` break counts for neither
- PROOF-39 (RULE-8): A mutmut listing of nine breaks to one file, one each `killed`, `timeout`, `caught by type check`, `survived`, `no tests`, `skipped`, `suspicious`, `not checked` and `check was interrupted by user`, gives the feature scoped to that file 3 caught and 2 missed, 60
- PROOF-9 (RULE-9): In the captured Stryker report the rule whose test is `adds two numbers` reads 3 caught, none missed and 100, and the rule whose test is `leaves small values alone` reads 5 caught and 2 missed, the 2 its test reached that nothing caught, so 71. Both carry `attribution: "per_test"`
- PROOF-40 (RULE-9): In a report where one break was reached by the tests `locks` and `unlocks` and caught by `locks` alone, the rule whose test is `unlocks` reads 0 caught, 1 missed and score 0, and the rule whose test is `locks` reads 1 caught and 0 missed
- PROOF-41 (RULE-9): In a report where one break timed out after the tests `locks` and `unlocks` reached it, naming neither as its catcher, the rule whose test is `locks` and the rule whose test is `unlocks` each read 1 caught and 0 missed
- PROOF-42 (RULE-9): In the captured Stryker report, a rule whose one test, `unrelated`, the report never lists reads score None with 0 caught and 0 missed
- PROOF-10 (RULE-10): A report lists the tests `locks` and `locks after five` in one file; `locks` caught one break and `locks after five` reached another that nothing caught. The rule whose test is `locks` reads 1 caught and 0 missed, and the rule whose test is `locks after five` reads 0 caught and 1 missed
- PROOF-43 (RULE-10): A rule whose test is written `login > locks` is credited the break the report's test `login locks` caught, and reads 1 caught and 100
- PROOF-44 (RULE-10): A report whose test `locks the account` in `test/other.test.js` caught a break credits nothing to a rule whose test of that name is in `test/login.test.js`: the rule reads 0 caught
- PROOF-11 (RULE-11): A Stryker.NET run over `src/Login/Session.cs` whose report names no test as a catcher, 3 caught and 2 missed, gives the feature 60 and both its rules 60, 3 caught and 2 missed, with `attribution: "per_scope"`, and its log names `attribution per_scope`
- PROOF-45 (RULE-11): A Stryker.NET run whose report names the test that caught each break gives the rule whose test is `adds two numbers` 100 with `attribution: "per_test"`
- PROOF-12 (RULE-12): A Stryker run of `calc` that exits 0 and leaves its report holding `not json` gives the feature and its rule a score of None, and its log reads `calc: stryker exited 0 and wrote no report`
- PROOF-51 (RULE-12): A Stryker run of `calc` that exits 1, prints `boom` and writes no report gives the feature and its rule a score of None, and its log reads `calc: stryker exited 1 and wrote no report` and carries `boom`
- PROOF-52 (RULE-12): A run of `calc`, a feature with no scope files, never starts Stryker; the feature and its rule read score None, and the log reads `calc: no scope files, nothing to break`
- PROOF-13 (RULE-13): A Stryker.NET run of `login`, scoped to `src/Login/Session.cs` and `src/Api.cs`, starts `dotnet` with exactly `stryker --mutate src/Login/Session.cs --mutate src/Api.cs --coverage-analysis perTest --disable-bail --reporter json --output` and a folder named `login`, once, after the install check
- PROOF-46 (RULE-13): A Stryker.NET run that writes `mutation-report.json` into a `reports` folder under its output folder is measured from that report: the feature reads 60
- PROOF-47 (RULE-13): A Stryker.NET run that writes `mutation-report.json` three folders down, in `StrykerOutput/2026-09-28/reports`, is measured from that report: the feature reads 60
- PROOF-48 (RULE-13): A Stryker.NET run of `login` that leaves its output folder empty measures nothing: the feature and its rule read score None, and the log reads `login: dotnet stryker exited 0 and wrote no report`
- PROOF-14 (RULE-14): With no `dotnet` on the PATH, a Stryker.NET run answers engine `none`, not available, with the reason `dotnet is not installed, so no engine breaks C# code`
- PROOF-49 (RULE-14): With a `dotnet` whose `dotnet stryker --version` exits 1, a Stryker.NET run asks only that, breaks nothing, and answers engine `none`, not available, with the reason `dotnet stryker is not installed: run "dotnet tool install -g dotnet-stryker"`
- PROOF-50 (RULE-14): With a `dotnet` whose `dotnet stryker --version` exits 0, a Stryker.NET run asks that first, then breaks the code, and answers engine `stryker_net`, available, with an empty reason
- PROOF-15 (RULE-15): For a project with a `pyproject.toml`, the block is written to `pyproject.toml` and, for the source path `src` and the tests `tests`, is exactly the three lines `[tool.mutmut]`, `source_paths = ["src"]` and `pytest_add_cli_args_test_selection = ["tests"]`
- PROOF-53 (RULE-15): For a project with no `pyproject.toml`, the block is written to `setup.cfg` and, for `src`, `lib`, `tests` and `-q`, reads `[mutmut]`, `source_paths =`, `src` and `lib` each on its own indented line, `pytest_add_cli_args_test_selection =`, then `tests` and `-q` the same way
- PROOF-54 (RULE-15): With mutmut installed and a `pyproject.toml` without the block, a run never starts mutmut and answers engine `none` with the reason `pyproject.toml carries no [tool.mutmut] block, so mutmut would break files no spec scopes: run "purlin:init" to write it`
- PROOF-55 (RULE-15): With mutmut installed, no `pyproject.toml` and a `setup.cfg` without the block, a run never starts mutmut and answers engine `none` with the reason `setup.cfg carries no [mutmut] block, so mutmut would break files no spec scopes: run "purlin:init" to write it`
- PROOF-16 (RULE-16): A mutmut run, answered with the five-line listing a real mutmut 3.8 run printed when asked `mutmut results --all true` and with nothing otherwise, asks `mutmut run` then that, logs `5 breaks read`, and gives the feature scoped to `calc/ops.py` 1 caught, 4 missed and 20
- PROOF-56 (RULE-16): A mutmut listing holding `2 files mutated, 0 ignored, 0 unmodified`, `244.79 mutations/second` and `Error: something else entirely` beside two breaks to `login.session`, one `killed` and one `survived`, logs `2 breaks read` and gives the feature scoped to `src/login/session.py` 1 caught and 1 missed
- PROOF-17 (RULE-17): A mutmut run over `login`, scoped to `src/login/session.py`, and `reports`, scoped to `src/reports/render.py`, with a listing of nine breaks, gives both rules of `login` 67, 4 caught and 2 missed, and the rule of `reports` 0, 0 caught and 1 missed, each with `attribution: "per_scope"`
- PROOF-57 (RULE-17): A mutmut listing whose one break is `unrelated.tool.x_main__mutmut_1: survived` gives the feature scoped to `src/login/session.py` no break: score None, 0 caught and 0 missed
- PROOF-58 (RULE-17): A mutmut run of the five-break listing a real mutmut 3.8 run printed, all in `calc.ops`, gives the feature scoped to the folder `calc` 1 caught, 4 missed and 20
- PROOF-18 (RULE-18): With no mutmut on the PATH, a run over `login` answers engine `none`, not available, with the reason `mutmut is not installed: run "pip install mutmut"`, and the feature's rule reads `attribution: "unavailable"`
- PROOF-19 (RULE-19): The empty engine, asked about `deploy`, scoped to `deploy.sh`, with two rules, answers engine `none`, not available, with the reason `no engine breaks go, shell or sql code, so test strength is not measured for these rules`; the scope score and both rules read None, 0 caught and 0 missed, the rules with `attribution: "unavailable"`
- PROOF-20 (RULE-20): The empty engine, asked about `deploy` and `infra`, answers exactly `engine`, `available`, `reason`, `features` and `log`, lists both features, each with a scope score of exactly `score`, `killed` and `survived`, and each rule exactly `engine`, `score`, `killed`, `survived` and `attribution`, the last one of `per_test`, `per_scope` and `unavailable`
- PROOF-60 (RULE-20): A mutmut run over a project with its block answers exactly `engine`, `available`, `reason`, `features` and `log`, each feature a scope score of exactly `score`, `killed` and `survived`, and each rule exactly `engine`, `score`, `killed`, `survived` and `attribution`; RULE-1 of `login` reads 67
- PROOF-61 (RULE-20): Asked to run `cosmic-ray` in a project where mutmut, Stryker and Stryker.NET are all installed, the run starts none of them and answers engine `none` with the reason `unknown engine "cosmic-ray": no breaks were made`
- PROOF-62 (RULE-20): An engine's answer that gives `calc` 3 caught and 1 missed and names neither of its two rules is completed: `calc` keeps 75, and each rule reads score None with `attribution: "unavailable"`
- PROOF-63 (RULE-20): A mutmut run asked about `login`, scoped to `src/login/session.py`, and about RULE-1 of `audit`, a feature with no scope entry, still lists `audit`, with a scope score of None and its RULE-1 at score None, 0 caught and 0 missed, with `attribution: "unavailable"`
- PROOF-21 (RULE-21): A mutmut break named `scripts.run.mutation.x_score_percent__mutmut_1`, a break in that package's `__init__.py`, counts for the feature scoped to `scripts/run/mutation/__init__.py`: it reads 1 caught
- PROOF-59 (RULE-21): With the one scope entry `scripts/**/*.py`, a listing of the caught breaks `scripts.run.host.x_commit__mutmut_1` and `scripts.mcp.purlin.x_read__mutmut_1` and the missed break `dev.build_report.x_build__mutmut_1` gives the feature 2 caught and 0 missed
- PROOF-22 (RULE-22): With the limit at 1 second, a mutmut run over `login` and `reports` still going at the limit never asks mutmut for its results, and answers engine `mutmut`, available, with both features' scope scores and all three rules at score None, 0 caught and 0 missed, with `attribution: "unavailable"`
- PROOF-64 (RULE-22): With the limit at 1 second, a mutmut run still going at the limit answers with the reason `the engine timed out after 1 s, so the breaks it made are partial and measure nothing: raise --arm-timeout to give it longer`, and its log carries the same line
- PROOF-65 (RULE-22): With the limit at 3 seconds, a Stryker run of `calc` and `slow`, both leaving a report and only `slow` still going at the limit, gives `calc` 64 and `slow` a scope score of None with its rule at None and `attribution: "unavailable"`; its reason and its log carry `timed out after 3 s` and `--arm-timeout`
- PROOF-66 (RULE-22): With the limit at 3 seconds, a Stryker.NET run of `login` and `slow`, both leaving a report and only `slow` still going at the limit, gives `login` 60 and `slow` a scope score of None with its rule at None and `attribution: "unavailable"`; its reason and its log carry `timed out after 3 s` and `--arm-timeout`
- PROOF-67 (RULE-22): At the gate `strong` with `mutation_engine` set to `mutmut`, a run of `--all --audit --arm-timeout 1` over `login`, whose test passes and whose mutmut would keep breaking for 60 seconds, ends within 30 seconds, prints the line `purlin: the engine timed out after 1 s, ...`, and writes `login`'s evidence with `audit.mutation` at engine `mutmut`, score null
