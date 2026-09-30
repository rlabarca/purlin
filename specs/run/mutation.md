# Feature: mutation

> Description: Test strength is the share of the deliberate breaks made to a feature's code
>   that the tests caught, as an integer percent, one share per feature. Four engines make
>   those breaks, one per language family: Stryker for jest and vitest, Stryker.NET for
>   dotnet, mutmut for pytest, and the empty engine for everything else. Selection reads the
>   config and the detected frameworks alone, so a caller can print the plan before anything
>   runs; the install check happens when the engine runs, and an engine that is not
>   installed answers with the reason in words rather than raising. Every engine answers in
>   one shape, each feature with its share and a sentence saying why nothing was measured
>   where nothing was, so the evidence carries the same fields whichever one measured it.
> Scope: scripts/run/mutation/__init__.py, scripts/run/mutation/stryker.py, scripts/run/mutation/stryker_net.py, scripts/run/mutation/mutmut.py, scripts/run/mutation/none.py
> Stack: python/stdlib (importlib, subprocess, json, tempfile), Stryker, Stryker.NET, mutmut
> Highest-Rule: 37

## Rules

- RULE-1: With `mutation_engine` set to `auto`, jest and vitest select `stryker`, dotnet selects `stryker_net`, pytest selects `mutmut`, and go, shell and sql select `none`
- RULE-2: A `mutation_engine` naming an engine wins over the detected frameworks
- RULE-3: Test strength is `killed / (killed + survived)` as an integer percent rounded half up
- RULE-5: Stryker runs once per feature against that feature's scope files alone, under a generated config naming `coverageAnalysis: "perTest"`, `disableBail: true`, the `json` reporter and the report path
- RULE-6: The Stryker test runner is `vitest` when the project's `package.json` declares vitest as a dependency, and `jest` otherwise
- RULE-7: The project's own `node_modules/.bin/stryker` is preferred over one on the PATH
- RULE-8: A break whose status is `killed`, `timeout` or, from mutmut, `caught by type check` counts caught; one whose status is `survived`, `nocoverage` or, from mutmut, `no tests` counts missed; and a break with any other status, such as Stryker's `CompileError` or mutmut's `skipped`, counts for neither
- RULE-12: A run that wrote no report, or whose report cannot be read, measures nothing for that feature, says so in the log rather than raising, and gives the feature the `missing` `<engine> ran and wrote no report: run purlin:audit again`, where `<engine>` is `stryker`, `dotnet stryker`, or `mutmut` for a mutmut run whose results list no break
- RULE-13: Stryker.NET is run as `dotnet stryker` with one `--mutate` per scope file, `--coverage-analysis perTest`, `--disable-bail`, `--reporter json` and `--output`
- RULE-14: Without `dotnet` on the PATH the reason names the .NET SDK and the `dotnet tool install` command, and with `dotnet` but no Stryker.NET installed the reason names the `dotnet tool install` command; the install check is `dotnet stryker --version` answering 0
- RULE-15: mutmut needs a config block naming the source paths and the test selection, written to `pyproject.toml` as `[tool.mutmut]` when that file exists and to `setup.cfg` as `[mutmut]` with one value a line otherwise
- RULE-16: The output of `mutmut results --all true` is read one line per break, and a line whose status is not one mutmut writes is not counted as a break
- RULE-17: A mutmut break counts for every feature whose scope reaches the file it is in: the module `a.b` the break names is the file git tracks at `a/b.py` or `a/b/__init__.py`, looked for at the project root and then under `src/`, the root winning where both exist; a break whose module is no tracked file counts for no feature
- RULE-18: Without mutmut installed the reason names `pip install mutmut`
- RULE-19: The empty engine measures nothing: every feature carries a scope score of None and an empty `missing`, and, when no other reason is given, the reason reads `no engine breaks go, shell or sql code, so test strength is not measured for these rules`
- RULE-20: Every engine answers the same shape, so a caller reads one: every feature the caller named is listed with its scope score and its `missing`, whether or not the engine reached it
- RULE-22: An engine invocation that runs past `--arm-timeout` measures nothing: the feature it was breaking reads a scope score of None whatever report it left, mutmut's one run leaving every feature unmeasured and a Stryker or Stryker.NET run leaving only the feature it was breaking; that feature's `missing`, the answer's reason and its log read `the engine timed out after <seconds> s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`, the first `<seconds>` the limit
- RULE-23: With the selected engine not installed, the answer names that engine and is not available, and its reason and every feature's `missing` are the engine's not-installed sentence
- RULE-24: With `mutation_engine` set to `auto`, the first detected framework that has an engine decides
- RULE-25: With `mutation_engine` set to `auto`, a project with no framework detected selects `none`
- RULE-26: A `mutation_engine` naming anything outside the four shipped engines reads as `none` rather than being guessed at
- RULE-27: Settings with no `mutation_engine` read as `none`, so mutation testing is off until a project turns it on
- RULE-28: Test strength is None when no break ran at all
- RULE-29: With no Stryker in the project and none on the PATH, Stryker is not installed, and the reason names the package to install
- RULE-30: Stryker.NET's report is the file `mutation-report.json` found by walking its `--output` directory; no other file there is read as the report
- RULE-31: Without mutmut's config block no breaks are made, and the reason names the block and the file
- RULE-32: On Windows mutmut is not started, and the answer is engine `none`, not available, with the reason `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides` and every feature's `missing` empty
- RULE-33: An engine name outside the four shipped engines is not run
- RULE-34: A mutmut run logs, a line each, `engine mutmut, config <section> in <path>`, `mutmut run exited <code>` and `<n> breaks read`, then `<feature>: <n> breaks, <p>% caught` for each feature
- RULE-35: A Stryker run logs `engine stryker, test runner <runner>`, then `<feature>: <n> files broken, <p>% caught` for each feature whose report it read
- RULE-36: A Stryker.NET run logs `engine stryker_net`, then `<feature>: <n> files broken, <p>% caught` for each feature whose report it read
- RULE-37: Stryker and Stryker.NET break nothing for a feature with no scope files, and the log reads `<feature>: no scope files, nothing to break`

## Proof

- PROOF-1 (RULE-1): With `mutation_engine` set to `auto` and jest the one framework detected, the engine is `stryker`
- PROOF-23 (RULE-1): With `mutation_engine` set to `auto` and go the one framework detected, the engine is `none`
- PROOF-24 (RULE-24): With `mutation_engine` set to `auto`, pytest detected first and jest second, the engine is `mutmut`
- PROOF-25 (RULE-24): With `mutation_engine` set to `auto`, jest detected first and pytest second, the engine is `stryker`
- PROOF-26 (RULE-24): With `mutation_engine` set to `auto`, shell detected first and dotnet second, the engine is `stryker_net`: a framework with no engine does not decide
- PROOF-27 (RULE-25): With `mutation_engine` set to `auto` and no framework detected, the engine is `none`
- PROOF-68 (RULE-1): With `mutation_engine` set to `auto` and vitest the one framework detected, the engine is `stryker`
- PROOF-69 (RULE-1): With `mutation_engine` set to `auto` and dotnet the one framework detected, the engine is `stryker_net`
- PROOF-70 (RULE-1): With `mutation_engine` set to `auto` and pytest the one framework detected, the engine is `mutmut`
- PROOF-71 (RULE-1): With `mutation_engine` set to `auto` and shell the one framework detected, the engine is `none`
- PROOF-72 (RULE-1): With `mutation_engine` set to `auto` and sql the one framework detected, the engine is `none`
- PROOF-2 (RULE-2): With `mutation_engine` set to `mutmut` in a project that detects jest, the engine is `mutmut`
- PROOF-28 (RULE-2): With `mutation_engine` set to `none` in a project that detects pytest, the engine is `none`
- PROOF-29 (RULE-26): With `mutation_engine` set to `cosmic-ray`, a name no shipped engine has, in a project that detects pytest, the engine is `none`, not `mutmut`
- PROOF-30 (RULE-27): With settings holding `gate` and no `mutation_engine`, a project that detects pytest gets the engine `none`
- PROOF-73 (RULE-27): With settings holding `gate` and no `mutation_engine`, a project that detects jest gets the engine `none`
- PROOF-83 (RULE-27): With settings holding no key at all, a project that detects pytest gets the engine `none`
- PROOF-84 (RULE-27): With settings holding no key at all, a project that detects jest gets the engine `none`
- PROOF-3 (RULE-3): Test strength reads 50 for 1 break caught and 1 missed, 67 for 2 caught and 1 missed, 33 for 1 and 2, 71 for 5 and 2, 64 for 7 and 4, 100 for 1 caught and none missed, and 0 for none caught and 1 missed
- PROOF-31 (RULE-3): A split that lands exactly on a half rounds up: 1 caught and 7 missed, 12.5, reads 13, not 12, and 3 caught and 5 missed, 37.5, reads 38
- PROOF-32 (RULE-28): With no break caught and none missed, test strength reads None, not 0
- PROOF-5 (RULE-5): A Stryker run of `calc`, scoped to `src/calc.js` and `src/util.js` in a project that does not declare vitest, gives Stryker a config holding exactly those two files to break, `coverageAnalysis` `perTest`, `disableBail` true, the `json` reporter, the runner `jest` and the path of a report, and nothing more
- PROOF-33 (RULE-5): A Stryker run of `calc`, scoped to `src/calc.js`, whose Stryker writes the captured report to the path its config names, starts `stryker run` once, with a config that breaks `src/calc.js` alone, and answers engine `stryker`, available, with the feature at 64 and a log naming `calc`
- PROOF-34 (RULE-5): A Stryker run over `calc`, scoped to `src/calc.js`, and `util`, scoped to `src/util.js` and `src/fmt.js`, starts Stryker exactly twice: the first config breaks `src/calc.js` alone and the second breaks `src/util.js` and `src/fmt.js` alone
- PROOF-86 (RULE-5): On Windows, a Stryker run of `calc`, scoped to `src/calc.js` and `src/util.js`, gives Stryker a config naming exactly those two files to break, spelled with `/`, `coverageAnalysis` `perTest`, `disableBail` true, the `json` reporter and a report path @env(windows)
- PROOF-6 (RULE-6): A project whose `package.json` lists vitest under `devDependencies` gives Stryker the runner `vitest`
- PROOF-35 (RULE-6): A project whose `package.json` lists vitest under `dependencies` gives Stryker the runner `vitest`
- PROOF-36 (RULE-6): A project whose `package.json` lists only jest gives Stryker the runner `jest`
- PROOF-37 (RULE-6): A project with no `package.json` gives Stryker the runner `jest`
- PROOF-7 (RULE-7): With a Stryker in the project's `node_modules/.bin/` and another on the PATH, a run starts the project's own once and never starts the one on the PATH
- PROOF-87 (RULE-7): On Windows, with `stryker.cmd` in the project's `node_modules/.bin/` and another Stryker on the search path, a run starts the project's own once and never starts the one on the search path @env(windows)
- PROOF-38 (RULE-29): With no Stryker in the project and none on the PATH, a run answers engine `stryker`, not available, with the reason `stryker is not installed: run "npm install --save-dev @stryker-mutator/core"`
- PROOF-8 (RULE-8): A Stryker report of 12 breaks to one file, 6 `Killed`, 1 `Timeout`, 2 `Survived`, 2 `NoCoverage` and 1 `CompileError`, gives the feature 7 caught and 4 missed, 64: the `CompileError` break counts for neither
- PROOF-39 (RULE-8): A mutmut listing of nine breaks to one file, one each `killed`, `timeout`, `caught by type check`, `survived`, `no tests`, `skipped`, `suspicious`, `not checked` and `check was interrupted by user`, gives the feature scoped to that file 3 caught and 2 missed, 60
- PROOF-12 (RULE-12): A Stryker run of `calc` that exits 0 and leaves its report holding `not json` gives the feature a score of None, and its log reads `calc: stryker exited 0 and wrote no report`
- PROOF-51 (RULE-12): A Stryker run of `calc` that exits 1, prints `boom` and writes no report gives the feature a score of None, and its log reads `calc: stryker exited 1 and wrote no report` and carries `boom`
- PROOF-52 (RULE-37): A run of `calc`, a feature with no scope files, never starts Stryker; the feature reads score None with an empty `missing`, and the log reads `calc: no scope files, nothing to break`
- PROOF-75 (RULE-12): A Stryker run of `calc` that exits 0 and writes no report gives the feature a score of None and the `missing` `stryker ran and wrote no report: run purlin:audit again`
- PROOF-82 (RULE-12): A mutmut run whose results list no break gives the feature scoped to `src/login/session.py` a score of None and the `missing` `mutmut ran and wrote no report: run purlin:audit again`
- PROOF-13 (RULE-13): A Stryker.NET run of `login`, scoped to `src/Login/Session.cs` and `src/Api.cs`, starts `dotnet` with exactly `stryker --mutate src/Login/Session.cs --mutate src/Api.cs --coverage-analysis perTest --disable-bail --reporter json --output` and a folder named `login`, once, after the install check
- PROOF-46 (RULE-30): A Stryker.NET run that writes `mutation-report.json` into a `reports` folder under its output folder is measured from that report: the feature reads 60
- PROOF-47 (RULE-30): A Stryker.NET run that writes `mutation-report.json` three folders down, in `StrykerOutput/2026-09-28/reports`, is measured from that report: the feature reads 60
- PROOF-88 (RULE-30): On Windows, a Stryker.NET run that writes `mutation-report.json` three folders down, in `StrykerOutput\2026-09-28\reports`, is measured from that report: the feature reads 60 @env(windows)
- PROOF-48 (RULE-30): A Stryker.NET run of `login` that leaves its output folder empty measures nothing: the feature reads score None, and the log reads `login: dotnet stryker exited 0 and wrote no report`
- PROOF-74 (RULE-30): A Stryker.NET run of `login` that writes a report named `other.json`, and no `mutation-report.json`, into its output folder measures nothing: the feature reads score None, and the log reads `login: dotnet stryker exited 0 and wrote no report`
- PROOF-14 (RULE-14): With no `dotnet` on the PATH, a Stryker.NET run answers engine `stryker_net`, not available, with the reason `dotnet is not installed: install the .NET SDK, then run "dotnet tool install -g dotnet-stryker"`
- PROOF-49 (RULE-14): With a `dotnet` whose `dotnet stryker --version` exits 1, a Stryker.NET run asks only that, breaks nothing, and answers engine `stryker_net`, not available, with the reason `dotnet stryker is not installed: run "dotnet tool install -g dotnet-stryker"`
- PROOF-50 (RULE-14): With a `dotnet` whose `dotnet stryker --version` exits 0, a Stryker.NET run asks that first, then breaks the code, and answers engine `stryker_net`, available, with an empty reason
- PROOF-89 (RULE-14): On Windows, with a `dotnet` whose `dotnet stryker --version` exits 0, a Stryker.NET run asks that first, then breaks the code, and answers engine `stryker_net`, available, with an empty reason @env(windows)
- PROOF-15 (RULE-15): For a project with a `pyproject.toml`, the block is written to `pyproject.toml` and, for the source path `src` and the tests `tests`, is exactly the three lines `[tool.mutmut]`, `source_paths = ["src"]` and `pytest_add_cli_args_test_selection = ["tests"]`
- PROOF-53 (RULE-15): For a project with no `pyproject.toml`, the block is written to `setup.cfg` and, for `src`, `lib`, `tests` and `-q`, reads `[mutmut]`, `source_paths =`, `src` and `lib` each on its own indented line, `pytest_add_cli_args_test_selection =`, then `tests` and `-q` the same way
- PROOF-54 (RULE-31): With mutmut installed and a `pyproject.toml` without the block, a run never starts mutmut and answers engine `none` with the reason `pyproject.toml carries no [tool.mutmut] block, so mutmut would break files no spec scopes: run purlin:init to write it`
- PROOF-55 (RULE-31): With mutmut installed, no `pyproject.toml` and a `setup.cfg` without the block, a run never starts mutmut and answers engine `none` with the reason `setup.cfg carries no [mutmut] block, so mutmut would break files no spec scopes: run purlin:init to write it`
- PROOF-16 (RULE-16): A mutmut run, answered with the five-line listing a real mutmut 3.8 run printed when asked `mutmut results --all true` and with nothing otherwise, asks `mutmut run` then that, logs `5 breaks read`, and gives the feature scoped to `calc/ops.py` 1 caught, 4 missed and 20
- PROOF-56 (RULE-16): A mutmut listing holding `2 files mutated, 0 ignored, 0 unmodified`, `244.79 mutations/second` and `Error: something else entirely` beside two breaks to `login.session`, one `killed` and one `survived`, logs `2 breaks read` and gives the feature scoped to `src/login/session.py` 1 caught and 1 missed
- PROOF-17 (RULE-17): In a project whose git holds `src/login/session.py` and `src/reports/render.py`, a mutmut run over `login`, scoped to the first, and `reports`, scoped to the second, with a listing of nine breaks, gives `login` 60, 3 caught and 2 missed, and `reports` 0, 0 caught and 1 missed
- PROOF-57 (RULE-17): A mutmut listing whose one break is `unrelated.tool.x_main__mutmut_1: survived`, a module no file in git is, gives the feature scoped to `src/login/session.py` no break: score None, 0 caught and 0 missed
- PROOF-58 (RULE-17): In a project whose git holds `calc/ops.py`, a mutmut run of the five-break listing a real mutmut 3.8 run printed, all in `calc.ops`, gives the feature scoped to the folder `calc` 1 caught, 4 missed and 20
- PROOF-21 (RULE-17): In a project whose git holds `scripts/run/mutation/__init__.py`, a killed mutmut break named `scripts.run.mutation.x_score_percent__mutmut_1` counts for the feature scoped to that file: it reads 1 caught
- PROOF-59 (RULE-17): With the one scope entry `scripts/**/*.py`, a listing of the caught breaks `scripts.run.host.x_commit__mutmut_1` and `scripts.mcp.purlin.x_read__mutmut_1` and the missed break `dev.build_report.x_build__mutmut_1`, each in a file git holds, gives the feature 2 caught and 0 missed
- PROOF-76 (RULE-17): In a project whose git holds `src/login/session.py`, a killed mutmut break named `login.session.x_lock__mutmut_1` counts for the feature whose one scope entry is the folder `src/`: it reads 1 caught
- PROOF-77 (RULE-17): In a project whose git holds `pkg/__init__.py` and `pkg/other.py`, a killed mutmut break named `pkg.other.x_run__mutmut_1` counts for no feature scoped to `pkg/__init__.py`: it reads 0 caught and 0 missed
- PROOF-78 (RULE-17): In a project whose git holds both `login/session.py` and `src/login/session.py`, a killed mutmut break named `login.session.x_lock__mutmut_1` counts 1 caught for the feature scoped to `login/session.py` and none for the feature scoped to `src/login/session.py`
- PROOF-85 (RULE-17): In a project whose git holds `src/login/session.py`, a killed mutmut break named `login.session.xǁSessionǁreset__mutmut_1`, in a method of the class `Session`, counts for the feature scoped to that file: it reads 1 caught
- PROOF-18 (RULE-18): With no mutmut on the PATH, a run over `login` answers engine `mutmut`, not available, with the reason `mutmut is not installed: run "pip install mutmut"`
- PROOF-79 (RULE-32): On Windows, with mutmut installed and its block written, a run over `login` never starts mutmut and answers engine `none`, not available, with the reason `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`, and `login`'s `missing` empty
- PROOF-90 (RULE-32): On Windows, with mutmut installed and on the search path, a run over `login` answers engine `none`, not available, with the reason `mutmut does not run on Windows, so test strength is not measured here and the AI audit alone decides`, and the feature's `missing` empty @env(windows)
- PROOF-19 (RULE-19): The empty engine, asked about `deploy`, scoped to `deploy.sh`, answers engine `none`, not available, with the reason `no engine breaks go, shell or sql code, so test strength is not measured for these rules`; the scope score reads None, 0 caught and 0 missed, and `missing` is empty
- PROOF-20 (RULE-20): The empty engine, asked about `deploy` and `infra`, answers exactly `engine`, `available`, `reason`, `features` and `log`, and lists both features, each exactly a `scope_score` of exactly `score`, `killed` and `survived`, and a `missing`
- PROOF-60 (RULE-20): A mutmut run over a project with its block answers exactly `engine`, `available`, `reason`, `features` and `log`, each feature exactly a `scope_score` of exactly `score`, `killed` and `survived`, and a `missing`; `login` reads 60
- PROOF-61 (RULE-33): Asked to run `cosmic-ray` in a project where mutmut, Stryker and Stryker.NET are all installed, the run starts none of them and answers engine `none` with the reason `mutation_engine names "cosmic-ray", which is not an engine: set it to none, auto, mutmut, stryker or stryker_net`
- PROOF-62 (RULE-20): An engine's answer that gives `calc` 3 caught and 1 missed and carries no `missing` for it is completed: `calc` keeps 75 and its `missing` reads empty
- PROOF-63 (RULE-20): A mutmut run asked about `login`, scoped to `src/login/session.py`, and `audit`, a feature with no scope entry, still lists `audit`, with a scope score of None, 0 caught and 0 missed, and an empty `missing`
- PROOF-22 (RULE-22): With the limit at 1 second, a mutmut run over `login` and `reports` still going at the limit never asks mutmut for its results, and answers engine `mutmut`, available, with both features' scope scores at None, 0 caught and 0 missed
- PROOF-64 (RULE-22): With the limit at 1 second, a mutmut run still going at the limit answers with the reason `the engine timed out after 1 s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer`, and its log carries the same line
- PROOF-65 (RULE-22): With the limit at 3 seconds, a Stryker run of `calc` and `slow`, both leaving a report and only `slow` still going at the limit, gives `calc` 64 and `slow` a scope score of None; its reason and its log carry `timed out after 3 s` and `--arm-timeout`
- PROOF-91 (RULE-22): On Windows, with the limit at 3 seconds, a Stryker run of `calc` and `slow`, only `slow` still going at the limit, gives `calc` 64 and `slow` a score of None, and `slow`'s `missing` carries `timed out after 3 s` @env(windows)
- PROOF-66 (RULE-22): With the limit at 3 seconds, a Stryker.NET run of `login` and `slow`, both leaving a report and only `slow` still going at the limit, gives `login` 60 and `slow` a scope score of None; its reason and its log carry `timed out after 3 s` and `--arm-timeout`
- PROOF-67 (RULE-22): At the gate `strong` with `mutation_engine` set to `mutmut`, a run of `--all --audit --arm-timeout 1` over `login`, whose test passes and whose mutmut would keep breaking for 60 seconds, ends within 30 seconds, prints the line `purlin: the engine timed out after 1 s, ...`, and writes `login`'s evidence with `audit.mutation` at engine `mutmut`, score null
- PROOF-80 (RULE-22): With the limit at 3 seconds, a Stryker run of `calc` and `slow`, only `slow` still going at the limit, gives `slow` the `missing` `the engine timed out after 3 s, so the breaks it made measure nothing: run purlin:audit --arm-timeout <seconds> to give it longer` and `calc` an empty `missing`
- PROOF-81 (RULE-23): With no Stryker in the project and none on the PATH, a run of `calc` and `util` gives each feature the `missing` `stryker is not installed: run "npm install --save-dev @stryker-mutator/core"`
- PROOF-92 (RULE-34): A mutmut run in a project whose `pyproject.toml` carries the `[tool.mutmut]` block logs the line `engine mutmut, config [tool.mutmut] in pyproject.toml`
- PROOF-93 (RULE-34): A mutmut run whose `mutmut run` exits 2 logs the line `mutmut run exited 2`, then still reads the breaks mutmut lists
- PROOF-94 (RULE-34): A mutmut run whose listing holds nine breaks logs the line `9 breaks read`
- PROOF-95 (RULE-34): A mutmut run over `login`, scoped to `src/login/session.py`, whose listing gives that file 3 caught and 2 missed breaks, logs the line `login: 5 breaks, 60% caught`
- PROOF-96 (RULE-35): A Stryker run in a project whose `package.json` lists vitest logs the line `engine stryker, test runner vitest` first
- PROOF-97 (RULE-35): A Stryker run of `calc`, scoped to `src/calc.js` and `src/util.js`, whose report holds 7 caught and 4 missed breaks, logs the line `calc: 2 files broken, 64% caught`
- PROOF-98 (RULE-36): A Stryker.NET run with `dotnet stryker` installed logs the line `engine stryker_net` first
- PROOF-99 (RULE-36): A Stryker.NET run of `login`, scoped to `src/Login/Session.cs` and `src/Api.cs`, whose report holds 3 caught and 2 missed breaks, logs the line `login: 2 files broken, 60% caught`
- PROOF-100 (RULE-37): A Stryker.NET run of `login`, a feature with no scope files, starts `dotnet` only to ask its version; `login` reads score None with an empty `missing`, and the log reads `login: no scope files, nothing to break`
