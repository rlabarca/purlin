# Feature: scaffold

> Description: `purlin:init`, which sets a project up. It asks at most two
>   questions, in this order: the gate, "what must be true of every rule
>   before a version is proven?"; and, at `strong` and `signed` only,
>   whether to measure test strength by breaking the code on purpose, where
>   an engine that runs on this operating system exists for a framework the
>   tree carries. Everything else is
>   derived from those answers or read from the tree. It asks nothing about
>   how the tests run and writes an empty `tests` setting, writes nothing
>   into the project's test suite, writes each file in turn and names every
>   one of them in the summary, installs no git hook of any kind, writes the
>   remote runner's workflow for one reason and no other, and ends on the
>   summary and `Left to do` of the project it set up.
> Scope: scripts/init/scaffold.py, templates/config.json, templates/gitignore.purlin, templates/evidence-readme.md
> Stack: python3 (stdlib only, 3.9 floor)

## Rules

- RULE-1: A project is asked the gate question and, at `strong` or `signed` where an engine that runs on this operating system exists for a framework the tree carries, the mutation question, in that order, and nothing else
- RULE-2: With mutation testing on, each gate derives its own minimum test strength: none at `passed`, 70 at `strong` and 80 at `signed`; with it off the minimum is null at every gate
- RULE-3: `--gate` answers the question without asking it, and a later run with no flag keeps the gate the config already names
- RULE-4: An answer that is not one of the three gates is read as `passed` and the fallback is printed, so a typo lowers what CI enforces loudly rather than raising it silently
- RULE-5: The config init writes carries exactly `version`, `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests` and `ci` at every gate, and no other key, whatever the project's own file held; `audit_parallel` is 4 and is never asked
- RULE-52: `templates/config.json` carries exactly six keys, in this order: `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci`, with `tests` empty and `ci` `none`
- RULE-8: init writes nothing into a project's test suite: no `conftest.py`, no Jest or Vitest configuration and no logger, and a runner configuration the project wrote is left as it was and not named in the summary
- RULE-9: With mutation testing on, a Vitest, Jest or .NET project is told in one line that Stryker measures the breaks and that without it test strength is not measured
- RULE-12: Raising the gate writes the setting and keeps every file an earlier run wrote; lowering it writes the setting and deletes nothing
- RULE-13: A workflow is written for one reason and no other, whatever the gate: a proof in `specs/` is tagged `@env` for an operating system this machine is not; the reason is printed as one sentence under the heading `A remote runner is written because:`
- RULE-53: A project with no proof tagged `@env` for an operating system this machine is not is told it needs no remote runner and gets no workflow
- RULE-54: A project with a proof tagged `@env` for an operating system this machine is not and no git remote is told there is no remote and gets no workflow
- RULE-14: The git host is read from the remote URL as `github` or `azure`, written as `ci`, and named on the summary line `Gate <gate>. Suites <names>. Git host <host>.`
- RULE-55: A project whose remote names a git host Purlin cannot use, one other than GitHub and Azure DevOps, has `ci` written `none`, and the line after `Gate <gate>. Suites <names>.` reads `This git host cannot run tests remotely. Everything on this machine works.`
- RULE-56: A project with no remote has `ci` written `none`, and the line after `Gate <gate>. Suites <names>.` reads `No git host found.`
- RULE-57: A project on Azure DevOps gets `purlin.azure-pipelines.yml` in place of `.github/workflows/purlin.yml`
- RULE-15: The workflow carries one job per operating system the `@env` tags in `specs/` name that the machine running setup is not, and no other, and the Purlin release pinned as `v<version>`
- RULE-42: The workflow triggers on a push to a `run/*` branch and on a push of a `signed/*` tag, and on nothing else
- RULE-58: The workflow's last step is the test run, `scripts/run/purlin_run.py --all --ci`
- RULE-18: The summary names every path init wrote, kept, copied or skipped, and each path it says it wrote is on disk afterwards
- RULE-19: A block init appends to a file the project also owns is appended once and never twice, whatever else that file already held
- RULE-20: A second run at the same gate writes no file
- RULE-21: No file init writes into a project names the directory the plugin ran from, so the project is the same on every machine
- RULE-22: A copy of the plugin installed from the marketplace sets a project up the same way this checkout does
- RULE-23: No file init writes into a project points at this repository's own development folder, which a consumer's checkout does not carry
- RULE-24: init installs no git hook at all and leaves a hook someone else wrote untouched: nothing runs at commit time and nothing runs at push time
- RULE-44: Before any workflow is written the prerequisites are checked, and there are two: a remote exists, and its URL names GitHub or Azure DevOps; the first that fails is printed in one line and no workflow is written
- RULE-59: No branch is checked, because a signature counts on whatever commit carries it, so a remote that holds no branch yet still gets the workflow
- RULE-60: Where both prerequisites hold, the host's command-line tool, `gh` on GitHub or `az` on Azure DevOps, is reported as installed or not installed, and the workflow is written in both cases
- RULE-31: A run outside a git repository exits 2 saying to run git init and leaves the directory empty, and a project root that does not exist exits 2
- RULE-33: `--update` hands the project to `scripts/init/update.py`
- RULE-34: A run ends on the lines `purlin:status` ends on for the project as it now is, the summary and `Left to do`, or, with no spec yet, on `→ Run: purlin:spec to write the first spec.`
- RULE-36: A project init set up walks the three gates: at `passed` `purlin:test --all --commit` exits 0 and commits the work, then its evidence; raised to `strong`, `1 rule to audit` is left until `purlin:audit --all --commit` writes an audit into that evidence; a runner's test run on a `signed/*` tag writes nothing and one on a `run/*` branch writes; raised to `signed`, `1 rule to sign` is left until `purlin:sign` signs it in a signed commit, after which `purlin:sign --all` writes the signed tag
- RULE-37: Each language is set up the same way in a real project: init writes an empty `tests` setting and adds nothing to its tests, and with the entry its first test run suggests written, its one marked test runs through `purlin:test` and is tied to its marker
- RULE-39: With mutation testing on, the mutmut block names as source every top-level directory holding a `.py` file at any depth and no test file at its top level, and names as the test selection the directories that do hold one, with `src`, `lib` and `app` preferred as source and `tests` and `test` as the selection; a project with no such directory names each non-test `.py` module at its root, and names `.` only when there is none
- RULE-40: Writing the mutmut block also appends `mutants/` to the project's `.gitignore`, once and never twice, so the copy mutmut breaks is never committed
- RULE-45: The mutation question, `Measure test strength by breaking the code on purpose? It needs <engine> and takes minutes to hours per run. [y/N]`, is asked only at `strong` and `signed`, only where an engine that runs on this operating system exists for a framework the tree carries, and defaults to no; yes writes `mutation_engine` `auto` and wires the engine, no writes `none` and wires nothing
- RULE-61: A project whose frameworks have no engine that runs on this operating system is asked nothing and gets `none`; at `strong` and `signed` it is told why in one line, and at `passed` it is told nothing
- RULE-62: A `mutation_engine` value the config already carries is kept without asking
- RULE-46: `--yes` takes every default, so it leaves mutation testing off, and `--mutation` turns it on without asking
- RULE-47: Init creates `.purlin/evidence/` holding one `README.md` that says what the folder holds, the same bytes as `templates/evidence-readme.md`, and a second run keeps it
- RULE-48: A `tests` setting the project already carries is kept as it is on every later run, whatever the tree holds
- RULE-50: Init asks nothing about how the tests run: a project whose settings carry no `tests` gets an empty one, whatever frameworks the tree holds
- RULE-51: Init creates `specs/` and no folder for anchors: no `specs/_anchors/`
- RULE-63: A project whose `.purlin/config.json` cannot be read is told so in one line naming the cause, and init asks nothing, writes nothing and exits 1

## Proof

- PROOF-1 (RULE-1): A pytest project is set up with `strong` typed at the first question and nothing typed after it; it is asked exactly two questions, `What must be true of every rule before a version is proven?`, then `Measure test strength by breaking the code on purpose? It needs mutmut and takes minutes to hours per run. [y/N]`
- PROOF-53 (RULE-1): A pytest project is set up with `passed` typed at the first question; it is asked exactly one question, `What must be true of every rule before a version is proven?`, and its settings read `gate` `passed` and `mutation_engine` `none`
- PROOF-126 (RULE-1): A pytest project set up at `--gate passed` is set up again at `--gate signed`, with answers ready to be typed; it asks no question, and its settings read `gate` `signed`
- PROOF-2 (RULE-2): A pytest project is set up with `--gate passed --mutation`; its settings read `min_strength` null
- PROOF-99 (RULE-2): A pytest project is set up with `--gate strong --mutation`; its settings read `min_strength` 70
- PROOF-100 (RULE-2): A pytest project is set up with `--gate signed --mutation`; its settings read `min_strength` 80
- PROOF-103 (RULE-2): A pytest project is set up with `--gate passed` and mutation testing left off; its settings read `min_strength` null
- PROOF-101 (RULE-2): A pytest project is set up with `--gate strong` and mutation testing left off; its settings read `min_strength` null
- PROOF-102 (RULE-2): A pytest project is set up with `--gate signed` and mutation testing left off; its settings read `min_strength` null
- PROOF-3 (RULE-3): A pytest project is set up with `--gate passed`; the output never shows `What must be true of every rule before a version is proven?`, and its settings read `gate` `passed`
- PROOF-104 (RULE-3): A project set up once with `--gate strong` is set up again with no `--gate` and every question at its default; the gate question is not asked, and its settings still read `gate` `strong`, not the default `passed`
- PROOF-4 (RULE-4): Init is run and `whenever` is typed at the gate question; it exits 0, prints the line `purlin: "whenever" is not a gate; reading it as passed.`, and the settings file reads `gate` `passed`
- PROOF-5 (RULE-5): Init at `--gate strong` writes a settings file whose keys are exactly `audit_parallel`, `ci`, `gate`, `min_strength`, `mutation_engine`, `tests` and `version`, with `version` equal to the plugin's `VERSION` file and `audit_parallel` 4; the only question shown is the mutation question, and no line names `audit_parallel`
- PROOF-54 (RULE-52): The settings template, `templates/config.json`, carries exactly six keys, in this order: `gate`, `mutation_engine`, `min_strength`, `audit_parallel`, `tests`, `ci`; `tests` is an empty list and `ci` reads `none`
- PROOF-55 (RULE-5): A project whose settings carry `audit_parallel` 9 is set up again with no flag but `--yes`; its settings still read `audit_parallel` 9
- PROOF-56 (RULE-5): A project whose settings carry `audit_parallel` 40, outside the range 1 to 16, is set up again with no flag but `--yes`; its settings read `audit_parallel` 4
- PROOF-58 (RULE-5): A project whose settings carry a key `colour` beside the seven is set up again at `--gate passed`; the settings it writes hold exactly the seven keys and no `colour`
- PROOF-8 (RULE-8): A pytest project with no `conftest.py` is set up at `--gate passed`; afterwards it holds no `conftest.py`, the summary names none, every file it held reads byte for byte the same, and the only paths added are `.gitignore`, `.purlin/`, `.purlin/config.json`, `.purlin/evidence/`, `.purlin/evidence/README.md`, `purlin-report.html` and `specs/`
- PROOF-59 (RULE-8): A Vitest project is set up at `--gate passed`; afterwards it holds no `vitest.config.ts` and the summary names none
- PROOF-60 (RULE-8): A Jest project is set up at `--gate passed`; afterwards it holds no `jest.config.js` and the summary names none
- PROOF-61 (RULE-8): A Jest project whose own `jest.config.js` reads `// ours` is set up at `--gate passed`; the file still reads `// ours` and the summary does not name it
- PROOF-9 (RULE-9): A Vitest project set up at `--gate passed` with `--mutation` prints the line `vitest: Stryker measures the breaks. Without it test strength is not measured.`
- PROOF-105 (RULE-9): A Jest project set up at `--gate strong` with `--mutation` prints the line `jest: Stryker measures the breaks. Without it test strength is not measured.`
- PROOF-106 (RULE-9): A C# project whose test project references xunit, set up at `--gate strong` with `--mutation`, prints the line `dotnet: Stryker measures the breaks. Without it test strength is not measured.`
- PROOF-12 (RULE-12): A project whose specs tag no proof for another operating system is set up at `--gate passed`, then at `--gate strong`; its settings read `gate` `strong`, and neither run writes a workflow
- PROOF-62 (RULE-12): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong`, then at `--gate signed`; its settings read `gate` `signed`, the summary reports the workflow as `kept`, and every file the first run wrote reads byte for byte the same except the settings file and `.purlin/report-data.js`
- PROOF-63 (RULE-12): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate signed`, then at `--gate passed`; its settings read `gate` `passed` with `min_strength` null, and every file the first run wrote, the workflow included, reads byte for byte the same except the settings file and `.purlin/report-data.js`
- PROOF-13 (RULE-53): A project whose specs tag no proof for another operating system is set up at `--gate strong`; no workflow is written, and the output has the line `No remote runner: every proof runs on this operating system, so nothing has to run remotely.`
- PROOF-64 (RULE-13): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate passed`; the workflow is written, and under `A remote runner is written because:` stands the one indented reason `A test is tagged @env for <os>, which this machine is not, so only a runner can run it.`, naming that system
- PROOF-65 (RULE-13): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong`; the workflow is written, and under the same heading stands the one reason `A proof in specs/ is tagged @env for <os>, which this machine is not, so only a runner can prove it.`, naming that system
- PROOF-51 (RULE-13): A project with proofs tagged `@env` for both operating systems this machine is not is set up at `--gate strong`; under `A remote runner is written because:` stands exactly one indented reason, and it names both systems
- PROOF-66 (RULE-54): A project with a proof tagged `@env` for an operating system this machine is not, and no git remote, is set up at `--gate strong`; no workflow is written and the output says `there is no git remote`
- PROOF-14 (RULE-14): A pytest project whose remote is `git@github.com:acme/demo.git` is set up at `--gate strong`; it prints `Gate strong. Suites none. Git host github.` and its settings read `ci` `github`
- PROOF-67 (RULE-14): A pytest project whose remote is `https://github.com/acme/demo.git` is set up at `--gate strong`; it prints `Gate strong. Suites none. Git host github.` and its settings read `ci` `github`
- PROOF-68 (RULE-14): A pytest project whose remote is `https://dev.azure.com/acme/demo/_git/demo` is set up at `--gate strong`; it prints `Gate strong. Suites none. Git host azure.` and its settings read `ci` `azure`
- PROOF-107 (RULE-14): A pytest project whose remote is `https://acme.visualstudio.com/demo/_git/demo` is set up at `--gate strong`; it prints `Gate strong. Suites none. Git host azure.` and its settings read `ci` `azure`
- PROOF-69 (RULE-55): A pytest project whose remote is `https://git.example.com/acme/demo.git` is set up at `--gate strong`; it prints the line `Gate strong. Suites none.`, then the line `This git host cannot run tests remotely. Everything on this machine works.`, and its settings read `ci` `none`
- PROOF-70 (RULE-56): A pytest project with no remote is set up at `--gate strong`; it prints the line `Gate strong. Suites none.`, then the line `No git host found.`, and its settings read `ci` `none`
- PROOF-71 (RULE-57): A project on an Azure DevOps remote with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong`; it prints `wrote purlin.azure-pipelines.yml`, the file is there, and there is no `.github/workflows/purlin.yml`
- PROOF-15 (RULE-15): A project with one proof tagged `@env(windows)` and another tagged `@env(macos)` is set up on a Mac at `--gate strong`; its workflow's matrix reads exactly `os: [windows-latest]`
- PROOF-72 (RULE-15): A project whose one tagged proof names an operating system this machine is not, Windows or macOS, is set up at `--gate strong`; its workflow's matrix names that system's runner alone, and the workflow holds no `ubuntu-latest`
- PROOF-73 (RULE-15): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong`; its workflow names the Purlin release as `v` followed by the plugin's `VERSION` file
- PROOF-42 (RULE-42): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong` on a GitHub remote; the workflow's `on:` block is exactly a `push:` with `branches: ['run/**']` and `tags: ['signed/**']`
- PROOF-74 (RULE-58): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong` on a GitHub remote; its workflow ends on the command `scripts/run/purlin_run.py" --all --ci`
- PROOF-75 (RULE-42): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong` on an Azure DevOps remote; the pipeline triggers on `run/*` and `signed/*` and reads `pr: none`
- PROOF-76 (RULE-58): A project with a proof tagged `@env` for an operating system this machine is not is set up at `--gate strong` on an Azure DevOps remote; the pipeline's last step runs `scripts/run/purlin_run.py" --all --ci`, and no step follows it
- PROOF-18 (RULE-18): A pytest project is set up at `--gate strong`; its summary names `.purlin/config.json`, `.gitignore`, `.purlin/evidence/README.md` and `purlin-report.html`, each as `wrote` or `copied`, and each of the four is on disk afterwards
- PROOF-108 (RULE-18): A pytest project is set up at `--gate strong`; the files and folders that appear in the project are exactly the paths its summary reports as `wrote` or `copied`, and each of them is on disk
- PROOF-109 (RULE-18): A project set up at `--gate passed` has a `purlin-report.html` that reads the same as the dashboard the plugin ships, and the summary reports it as `copied`
- PROOF-19 (RULE-19): A project whose `.gitignore` reads `node_modules/` is set up twice; the file is the same after the second run as after the first, still begins `node_modules/`, holds `.purlin/runtime/`, and holds `.purlin/report-data.js` exactly once
- PROOF-110 (RULE-19): A project whose `pyproject.toml` reads `[project]` and `name = "demo"`, with a `src/app.py`, is set up with `--mutation`, then again; the file still begins with those two lines and holds `[tool.mutmut]` exactly once, with `source_paths = ["src"]` and `pytest_add_cli_args_test_selection = ["tests"]`
- PROOF-111 (RULE-19): A pytest project with no `pyproject.toml` is set up with `--mutation`, then again; `setup.cfg` holds `[mutmut]` exactly once
- PROOF-20 (RULE-20): Init is run twice at `--gate strong` on the same project; no line of the second run's summary begins `wrote`, and every file and folder in the project outside `.git/` reads byte for byte the same after the second run as before it
- PROOF-21 (RULE-21): A copy of the plugin laid out as a marketplace install sets up a project at `--gate strong`, run from that copy with `CLAUDE_PLUGIN_ROOT` naming it; no readable file in the project outside `.git/` holds the copy's path
- PROOF-22 (RULE-22): A marketplace-style copy of the plugin, run with `CLAUDE_PLUGIN_ROOT` naming it, sets up a pytest project with a proof tagged `@env` for an operating system this machine is not at `--gate strong`; it writes the workflow, and the same project set up from this checkout ends with the same files, `.purlin/report-data.js` aside, and the same output, each project's path aside
- PROOF-23 (RULE-23): Init sets up a project at `--gate strong`; no readable file in the project outside `.git/` holds `/dev/`, once every `/dev/null` is set aside, and none holds a relative path starting `dev/`, such as `dev/test_x.py`
- PROOF-24 (RULE-24): Init is run at `--gate passed`; the files under `.git/hooks/` are exactly those that were there before it ran, and neither `pre-push` nor `pre-commit` is among them
- PROOF-112 (RULE-24): A project whose `.git/hooks/pre-push` reads `echo mine` is set up at `--gate passed`; the hook reads the same afterwards
- PROOF-44 (RULE-44): A project with a proof tagged `@env` for an operating system this machine is not, whose remote is `https://example.invalid/x.git`, is set up at `--gate strong`; the line `This git host cannot run tests remotely. Everything on this machine works.` is printed once, `skipped the CI workflow (a prerequisite is missing)` is printed, and no workflow is written
- PROOF-77 (RULE-59): A project with a proof tagged `@env` for an operating system this machine is not, whose GitHub remote holds no branch yet, is set up at `--gate strong`; the workflow is written and the summary reports it as `wrote`
- PROOF-78 (RULE-60): A project with a proof tagged `@env` for an operating system this machine is not on a GitHub remote, set up at `--gate strong` with a `gh` on the search path, prints `gh is installed, so a remote run can be watched from here.` and writes the workflow
- PROOF-79 (RULE-60): A project with a proof tagged `@env` for an operating system this machine is not on a GitHub remote, set up at `--gate strong` with no `gh` on the search path, prints `gh is not installed, so purlin:test --remote cannot watch a run. Install it, or open the run on the git host instead.` and writes the workflow
- PROOF-113 (RULE-60): A project with a proof tagged `@env` for an operating system this machine is not on an Azure DevOps remote, set up at `--gate strong` with an `az` on the search path, prints `az is installed, so a remote run can be watched from here.` and writes the pipeline
- PROOF-114 (RULE-60): A project with a proof tagged `@env` for an operating system this machine is not on an Azure DevOps remote, set up at `--gate strong` with no `az` on the search path, prints `az is not installed, so purlin:test --remote cannot watch a run. Install it, or open the run on the git host instead.` and writes the pipeline
- PROOF-31 (RULE-31): Init with `--gate passed --yes` in an empty folder that is not a git repository exits 2, its error output names `git init`, and the folder is still empty
- PROOF-115 (RULE-31): Init with `--project-root /no/such/dir` exits 2
- PROOF-116 (RULE-31): Init given the root `no/such/dir` inside an empty folder exits 2, prints nothing on its standard output, its error output is the one line `no such project root: <that path>`, and the empty folder is still empty afterwards
- PROOF-33 (RULE-33): On a project init has just set up at `--gate passed`, `--update --yes` exits 0 and prints `Nothing is pending: this project is at <version>.`, the version being the plugin's `VERSION` file
- PROOF-34 (RULE-34): A project with no spec is set up at `--gate passed`; the last line it prints is `→ Run: purlin:spec to write the first spec.`
- PROOF-80 (RULE-34): A project holding one spec, whose one rule has a proof and no test, is set up at `--gate passed`; the last three lines it prints are `1 rule. 0 pass their tests.`, `Left to do:` and `  1 rule to write a test for: purlin:build`
- PROOF-36 (RULE-36): A python project set up at `passed`, with one committed spec, its marked test and the test entry its first run suggested, runs `purlin:test --all --commit`; it exits 0, commits `purlin: specs, tests and settings for greeting`, then `purlin: evidence at <that commit's sha7>` holding `.purlin/evidence/local/greeting.json` and `.purlin/tests.md`, and ends `Nothing left to do.`
- PROOF-90 (RULE-36): That python project, its tests passed and committed, is set up again at `strong`; the last line it prints is `  1 rule to audit: purlin:audit`
- PROOF-117 (RULE-36): That python project at `strong` runs `purlin:audit --all --commit`; the evidence file it commits holds an audit of `RULE-1`, the output says `Evidence committed.`, then ends on `1 rule. 1 passes its tests. 1 is strong.` and `Nothing left to do.`
- PROOF-91 (RULE-36): On that audited python project, a runner's test run whose git host variables name the tag `signed/0.1.0` prints `Tag run: nothing is written. This run reruns the tests on signed/0.1.0.` and writes no `.purlin/evidence/ci/greeting.json`
- PROOF-118 (RULE-36): On that audited python project, a runner's test run whose git host variables name the branch `run/main-0000000` prints `Evidence written to .purlin/evidence/ci/greeting.json.`, writes that file, and prints no `Tag run:`
- PROOF-92 (RULE-36): That audited python project, set up again at `signed`, ends on the line `  1 rule to sign: purlin:sign`
- PROOF-119 (RULE-36): That python project at `signed`, with an SSH signing key set up for `jane@acme.com`, runs `purlin:sign greeting RULE-1`; it exits 0, its commit carries a signature, and it prints `Signed 1 rule as jane@acme.com with the key ending ...<the key fingerprint's last 4 characters>.`
- PROOF-93 (RULE-36): With that rule signed and the tree committed, `purlin:sign --all` writes the tag `signed/0.1.0` and prints `Nothing left to do. Push the tag to release it: git push origin signed/0.1.0`
- PROOF-37 (RULE-37): A python project set up at `passed` has `tests` empty and no `conftest.py`; its first `purlin:test` suggests an entry named `pytest`, and with it written the one marked test's run ends on `1 rule. 1 passes its tests.` and `Nothing left to do.`, after `Markers: 1 tied to a test, 0 not tied.`
- PROOF-94 (RULE-37): A typescript project set up at `passed` has `tests` empty and no `vitest.config.ts`; its first `purlin:test` suggests an entry named `vitest`, and with it written the one marked test's run ends on `1 rule. 1 passes its tests.` and `Nothing left to do.`. It is skipped with a note where npm cannot install Vitest
- PROOF-95 (RULE-37): A C# project set up at `passed` has `tests` empty; its first `purlin:test` suggests an entry named `dotnet`, and with it written the one marked test's run ends on `1 rule. 1 passes its tests.` and `Nothing left to do.`. It is skipped with a note where `dotnet` is not installed
- PROOF-96 (RULE-37): A C# project whose project file and marked test were committed before init is set up at `passed`; its settings read `tests` empty, nothing under `App/` or `App.Tests/` is changed or added, and no `.cs`, `.csproj`, `.props`, `.targets`, `.sln` or `.runsettings` file is written
- PROOF-97 (RULE-21): A copy of the plugin laid out as a marketplace install sets up a fresh project at `passed`; `.purlin/config.json` is written, and no file in the project outside `.git/` names the install's path
- PROOF-52 (RULE-37): A Go module of two packages, set up at `--gate passed` and given the entry its first test run suggests, runs `purlin:test --all`; it prints `Markers: 7 tied to a test, 0 not tied.`, exits 1, and records `pass`, `fail` or `missing` for each test as Go reported it; no Go file and no `go.sum` is added
- PROOF-39 (RULE-39): A project holding `scripts/run/job.py`, `dev/test_job.py`, `dev/build.py` and `docs/guide.md` is set up with `--mutation`; its `setup.cfg` reads `[mutmut]`, then `source_paths =` with `scripts` on an indented line, then `pytest_add_cli_args_test_selection =` with `dev` on an indented line
- PROOF-120 (RULE-39): A project holding `src/app.py`, `tools/helper.py`, `tests/test_app.py` and `dev/test_extra.py` is set up with `--mutation`; its `setup.cfg` names exactly the source `src` and the test selection `tests`, each on its own indented line
- PROOF-121 (RULE-39): A project holding `greeting.py`, `conftest.py` and `test_greeting.py` at its root beside a `tests/` folder is set up with `--mutation`; its `setup.cfg` names exactly the source `greeting.py` and the test selection `tests`
- PROOF-122 (RULE-39): A project whose only `.py` files are a `conftest.py` and the tests under `tests/` is set up with `--mutation`; its `setup.cfg` names exactly the source `.` and the test selection `tests`
- PROOF-123 (RULE-39): A project holding `demo/__init__.py`, a `tests/` folder and no `src/` is set up with `--mutation`; its `setup.cfg` names exactly the source `demo` and the test selection `tests`
- PROOF-40 (RULE-40): A project holding `greeting.py` and `tests/test_greeting.py` is set up with `--mutation` and then set up again; its `.gitignore` holds the line `mutants/` exactly once
- PROOF-45 (RULE-45): A pytest project is set up at `--gate strong` and `y` is typed at `Measure test strength by breaking the code on purpose? It needs mutmut and takes minutes to hours per run. [y/N]`; its settings read `mutation_engine` `auto` and `min_strength` 70, and `setup.cfg` holds `[mutmut]`
- PROOF-81 (RULE-45): A pytest project is set up at `--gate strong` and `n` is typed at the mutation question; its settings read `mutation_engine` `none` and `min_strength` null, no `setup.cfg` is written and `.gitignore` holds no `mutants/`
- PROOF-82 (RULE-61): A project whose only framework is shell is set up at `--gate strong`; it is not asked the mutation question, its settings read `mutation_engine` `none`, and the output has the line `Mutation testing is off: no engine breaks shell code, so the AI audit alone judges test strength.`
- PROOF-83 (RULE-61): A project whose only framework is shell is set up at `--gate passed`; it is not asked the mutation question, its settings read `mutation_engine` `none`, and no line of the output holds `no engine breaks`
- PROOF-127 (RULE-61): A pytest project is set up at `--gate strong` on a machine whose system is Windows; it is not asked the mutation question, its settings read `mutation_engine` `none`, and the output has the line `Mutation testing is off: mutmut does not run on Windows, so the AI audit alone judges test strength.`
- PROOF-84 (RULE-62): A pytest project whose settings already read `mutation_engine` `auto` is set up at `--gate strong` with nothing to answer from; it is not asked the mutation question, and its settings still read `auto`
- PROOF-46 (RULE-46): A pytest project set up with `--gate strong --yes` prints the mutation question followed by `[n]: n`, and its settings read `mutation_engine` `none` and `min_strength` null, with no `setup.cfg` written
- PROOF-85 (RULE-46): A new pytest project set up with `--yes` and no gate prints `[passed]: passed` under the gate question, and its settings read `gate` `passed`
- PROOF-86 (RULE-46): A pytest project set up with `--gate strong --yes --mutation` is not asked the mutation question; its settings read `mutation_engine` `auto` and `min_strength` 70, and its `setup.cfg` holds `[mutmut]`
- PROOF-47 (RULE-47): Init at `--gate passed` writes `.purlin/evidence/README.md`, byte for byte the same as `templates/evidence-readme.md` and naming `local/` and `ci/`, and the summary reports it as `wrote`
- PROOF-124 (RULE-47): A project set up once at `--gate passed` is set up again; the summary reports `.purlin/evidence/README.md` as `kept`
- PROOF-125 (RULE-47): A project set up at `--gate passed` adds the line `Our own note.` to `.purlin/evidence/README.md` and is set up again; the summary reports the README as `kept`, and it reads byte for byte as the project left it
- PROOF-48 (RULE-48): A pytest project's settings are given one suite of their own, `unit`, running `make test REPORT={report}`; after init runs again at `--gate strong`, the `tests` setting is exactly that one suite, with no `pytest` suite added
- PROOF-87 (RULE-50): A pytest project holding a test file is set up at `--gate strong`; its settings read `tests` as an empty list, and the only question shown is the mutation question
- PROOF-88 (RULE-50): An empty git project is set up at `--gate passed`; it exits 0, asks no question, and its settings read `tests` as an empty list
- PROOF-89 (RULE-51): A pytest project is set up at `--gate strong`; afterwards `specs/` is there, there is no `specs/_anchors/`, and the summary names no `specs/_anchors`
- PROOF-128 (RULE-63): A project whose `.purlin/config.json` holds a comma after its last value is set up at `--gate strong`; it exits 1, prints `.purlin/config.json cannot be read: <the JSON reader's own message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and every file reads as before
