# Feature: scaffold

> Description: `purlin:init`, which sets a project up. It asks one
>   question, once it wrote a file git does not ignore: whether it may
>   commit the files it wrote. It writes the settings file with `version`
>   and `tests` alone, `specs/`, the evidence folder, the `.gitignore`
>   block and the dashboard copy. It asks nothing about how the tests run
>   and writes an empty `tests` setting, writes nothing into the project's
>   test suite, writes each file in turn and names every one of them in the
>   summary, installs no git hook of any kind, leaves the runner file to the
>   first `purlin:test --remote`, and ends on the summary and `Left to do`
>   of the project it set up.
> Scope: scripts/init/scaffold.py, templates/config.json, templates/gitignore.purlin, templates/evidence-readme.md
> Stack: python3 (stdlib only, 3.9 floor)
> Highest-Rule: 81
> Highest-Proof: 173

## Rules

- RULE-8: init writes nothing into a project's test suite: no `conftest.py`, no Jest or Vitest configuration and no logger, and a runner configuration the project wrote is left as it was and not named in the summary
- RULE-18: The summary names every path init wrote, kept, copied or skipped, each on one line, and each path it says it wrote is on disk afterwards
- RULE-19: A block init appends to a file the project also owns is appended once and never twice, whatever else that file already held
- RULE-20: A second run writes no file
- RULE-21: No file init writes into a project names the directory the plugin ran from, so the project is the same on every machine
- RULE-22: A copy of the plugin installed from the marketplace sets a project up the same way this checkout does
- RULE-23: No file init writes into a project points at this repository's own development folder, which a consumer's checkout does not carry
- RULE-24: init installs no git hook at all and leaves a hook someone else wrote untouched: nothing runs at commit time and nothing runs at push time
- RULE-31: A run outside a git repository exits 2 with `This is not a git repository. Run git init, then purlin:init.` and leaves the directory empty, and a project root that does not exist exits 2
- RULE-33: `--update` hands the project to `scripts/init/update.py`
- RULE-34: A run ends on the lines `purlin:status` ends on for the project as it now is: the summary and `Left to do`, or, with no spec yet, the same two lines the status prints for a project with no spec
- RULE-36: A project init set up walks run, commit and sign-off: `purlin:test --all --commit` exits 0 and commits the work, then its evidence; `purlin:audit --all --commit` writes an audit into that evidence; a runner's test run on a `run/*` branch writes evidence; and the first `purlin:sign` builds the evidence package, signs it in a signed commit and writes `signed/<version>`
- RULE-37: Each language is set up the same way in a real project: init writes an empty `tests` setting and adds nothing to its tests, and with the entry its first test run suggests written, its one marked test runs through `purlin:test` and is tied to its marker
- RULE-47: Init creates `.purlin/evidence/` holding one `README.md` that says what the folder holds, the same bytes as `templates/evidence-readme.md`, and a second run keeps it
- RULE-48: A `tests` setting the project already carries is kept as it is on every later run, whatever the tree holds
- RULE-50: Init asks nothing about how the tests run: a project whose settings carry no `tests` gets an empty one, whatever frameworks the tree holds
- RULE-51: Init creates `specs/` and no folder for anchors: no `specs/_anchors/`
- RULE-63: A project whose `.purlin/config.json` cannot be read is told so in one line naming the cause, and init asks nothing, writes nothing and exits 1
- RULE-67: A new project's `.gitignore` names `/purlin-report.html` and `.purlin/runtime/`
- RULE-68: Once setup wrote or changed a file git does not ignore, it asks `Commit the files setup wrote? [y/N] ` on one line after the lines naming each file; an empty answer, the end of input or any answer but `y` or `yes` commits nothing and prints nothing more
- RULE-69: `--yes` commits the files setup wrote without asking, in one commit whose subject is `chore(init): set up Purlin`, and prints `Committed <sha7>, the files setup wrote:`, then each path, indented two spaces, in the order setup named them
- RULE-70: The commit carries only the files setup wrote or changed that git does not ignore: a file the project had already staged stays staged and out of it
- RULE-71: A project with no commit yet gets setup's commit as its first
- RULE-72: Where git refuses the commit, setup prints `The files setup wrote are staged and not committed: <git's own message>.`
- RULE-73: The block setup adds to `.gitignore` carries a comment above each entry saying what it holds, and a comment saying that `.purlin/evidence/` is tracked on purpose
- RULE-74: Setting up a project that already holds `purlin-report.html` at its root leaves that file as it is, and the summary names it `kept purlin-report.html`
- RULE-79: Setup asks one question, `Commit the files setup wrote? [y/N] `, and no other
- RULE-80: The settings file setup writes holds exactly `version` and `tests`, `version` being the plugin's `VERSION` file
- RULE-81: Setup leaves the runner file to the first `purlin:test --remote`: a project on a GitHub remote with a proof tagged `@env` for a system this machine is not is set up with no `.github/workflows/purlin.yml`

## Proof

- PROOF-8 (RULE-8): A pytest project with no `conftest.py` is set up; afterwards it holds no `conftest.py`, the summary names none, every file it held reads byte for byte the same, and the only paths added are `.gitignore`, `.purlin/`, `.purlin/config.json`, `.purlin/evidence/`, `.purlin/evidence/README.md`, `purlin-report.html` and `specs/`
- PROOF-59 (RULE-8): A Vitest project is set up; afterwards it holds no `vitest.config.ts` and the summary names none
- PROOF-60 (RULE-8): A Jest project is set up; afterwards it holds no `jest.config.js` and the summary names none
- PROOF-61 (RULE-8): A Jest project whose own `jest.config.js` reads `// ours` is set up; the file still reads `// ours` and the summary does not name it
- PROOF-18 (RULE-18): A pytest project is set up; its summary names `.purlin/config.json`, `.gitignore`, `.purlin/evidence/README.md` and `purlin-report.html`, each as `wrote` or `copied`, and each of the four is on disk afterwards
- PROOF-108 (RULE-18): A pytest project is set up; the files and folders that appear in the project are exactly the paths its summary reports as `wrote` or `copied`, and each of them is on disk
- PROOF-109 (RULE-18): A project set up has a `purlin-report.html` that reads the same as the dashboard the plugin ships, and the summary reports it as `copied`
- PROOF-19 (RULE-19): A project whose `.gitignore` reads `node_modules/` is set up twice; the file is the same after the second run as after the first, still begins `node_modules/`, holds `.purlin/runtime/`, and holds `.purlin/report-data.js` exactly once
- PROOF-130 (RULE-19): On Windows, a project whose `.gitignore` reads `node_modules/` followed by a carriage return and a line feed is set up twice; the file is the same after the second run as after the first, and holds `.purlin/report-data.js` exactly once @env(windows)
- PROOF-20 (RULE-20): Init is run twice on the same project; no line of the second run's summary begins `wrote`, and every file and folder in the project outside `.git/` reads byte for byte the same after the second run as before it
- PROOF-131 (RULE-20): On Windows, init is run twice on the same project; no line of the second run's summary begins `wrote`, and every file outside `.git/` reads byte for byte the same after the second run as before it @env(windows)
- PROOF-21 (RULE-21): A copy of the plugin laid out as a marketplace install sets up a project, run from that copy with `CLAUDE_PLUGIN_ROOT` naming it; no readable file in the project outside `.git/` holds the copy's path
- PROOF-132 (RULE-21): On Windows, a marketplace copy of the plugin, named by `CLAUDE_PLUGIN_ROOT`, sets up a project; no readable file outside `.git/` holds the copy's path, spelled with `\` or with `/` @env(windows)
- PROOF-97 (RULE-21): A copy of the plugin laid out as a marketplace install sets up a fresh project; `.purlin/config.json` is written, and no file in the project outside `.git/` names the install's path
- PROOF-147 (RULE-21): Setup is run from this checkout of the plugin, the folder `--plugin-dir` loads; no file in the project outside `.git/` names that folder's path
- PROOF-22 (RULE-22): A marketplace-style copy of the plugin, run with `CLAUDE_PLUGIN_ROOT` naming it, sets up a pytest project; the same project set up from this checkout ends with the same files, `.purlin/report-data.js` aside, and the same output, paths and commits aside
- PROOF-133 (RULE-22): On Windows, a marketplace copy of the plugin, named by `CLAUDE_PLUGIN_ROOT`, sets up a pytest project; the same project set up from this checkout ends with the same files, `.purlin/report-data.js` aside, and the same output, paths and commits aside @env(windows)
- PROOF-23 (RULE-23): Init sets up a project; no readable file in the project outside `.git/` holds `/dev/`, once every `/dev/null` is set aside, and none holds a relative path starting `dev/`, such as `dev/test_x.py`
- PROOF-134 (RULE-23): On Windows, init sets up a project; no readable file outside `.git/` holds `/dev/` or `\dev\`, once every `/dev/null` is set aside, and none holds a relative path starting `dev/` or `dev\` @env(windows)
- PROOF-24 (RULE-24): Init is run; the files under `.git/hooks/` are exactly those that were there before it ran, and neither `pre-push` nor `pre-commit` is among them
- PROOF-112 (RULE-24): A project whose `.git/hooks/pre-push` reads `echo mine` is set up; the hook reads the same afterwards
- PROOF-31 (RULE-31): Init with `--yes` in an empty folder that is not a git repository exits 2, its error output is the one line `This is not a git repository. Run git init, then purlin:init.`, and the folder is still empty
- PROOF-115 (RULE-31): Init with `--project-root /no/such/dir` exits 2
- PROOF-116 (RULE-31): Init given the root `no/such/dir` inside an empty folder exits 2, prints nothing on its standard output, its error output is the one line `no such project root: <that path>`, and the empty folder is still empty afterwards
- PROOF-33 (RULE-33): On a project init has just set up, `--update --yes` exits 0 and prints `Nothing is pending: this project is at <version>.`, the version being the plugin's `VERSION` file
- PROOF-34 (RULE-34): A project with no spec whose tree holds `conftest.py` and `tests/test_x.py` is set up; the last two lines it prints are `No specs found under specs/.` and `→ Run: purlin:spec-from-code to write the specs this code already implies.`
- PROOF-137 (RULE-34): A project with no spec and no file of code is set up; the last two lines it prints are `No specs found under specs/.` and `→ Run: purlin:spec <name> to write the first spec.`
- PROOF-80 (RULE-34): A project holding one spec, whose one rule has a proof and no test, is set up; the last three lines it prints are `1 rule. 0 pass their tests.`, `Left to do:` and `  1 rule to write a test for: purlin:build`
- PROOF-36 (RULE-36): A python project, with one committed spec, its marked test and its suggested test entry, runs `purlin:test --all --commit`; it exits 0, commits `purlin: specs, tests and settings for greeting`, then `purlin: evidence at <that commit's sha7>` holding `.purlin/evidence/local/greeting.json`, and ends `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` @env(macos)
- PROOF-117 (RULE-36): That python project runs `purlin:audit --all --commit`; the evidence file it commits holds an audit of `RULE-1`, and the output says `Evidence committed.` and `The audit found 1 of 1 rules strong (100%).` @env(macos)
- PROOF-118 (RULE-36): On that audited python project, a runner's test run whose git host variables name the branch `run/main-0000000` prints `Evidence written to .purlin/evidence/ci/greeting.json.` and writes that file @env(macos)
- PROOF-119 (RULE-36): That audited python project, with a `VERSION` file reading `0.1.0` and an SSH signing key set up for `jane@acme.com`, runs `purlin:sign --answers` with the signature answered yes; it exits 0, its commit carries a signature, and it prints `Signed 0.1.0 as jane@acme.com with the key ending ...<the key fingerprint's last 4 characters>.` @env(macos)
- PROOF-93 (RULE-36): That first sign-off writes the tag `signed/0.1.0` on its commit, and prints `Push the branch and the tag: git push origin <branch> signed/0.1.0`, `<branch>` being the branch it signed on @env(macos)
- PROOF-37 (RULE-37): A python project set up with nothing to answer from has `tests` empty and no `conftest.py`; its first `purlin:test` suggests an entry named `pytest`, and with it written the one marked test's run prints `Markers: 1 tied to a test, 0 not tied.` and `1 rule. 1 passes its tests.` @env(macos)
- PROOF-94 (RULE-37): A typescript project set up with nothing to answer from has `tests` empty and no `vitest.config.ts`; its first `purlin:test` suggests an entry named `vitest`, and with it written the one marked test's run prints `1 rule. 1 passes its tests.`; it is skipped where npm cannot install Vitest @env(macos)
- PROOF-95 (RULE-37): A C# project set up with nothing to answer from has `tests` empty; its first `purlin:test` suggests an entry named `dotnet`, and with it written the one marked test's run prints `1 rule. 1 passes its tests.`. It is skipped with a note where `dotnet` is not installed @env(macos)
- PROOF-96 (RULE-37): A C# project whose project file and marked test were committed before init is set up; its settings read `tests` empty, nothing under `App/` or `App.Tests/` is changed or added, and no `.cs`, `.csproj`, `.props`, `.targets`, `.sln` or `.runsettings` file is written @env(macos)
- PROOF-52 (RULE-37): A Go module of two packages, set up and given the entry its first test run suggests, runs `purlin:test --all`; it prints `Markers: 7 tied to a test, 0 not tied.`, exits 1, and records `pass`, `fail` or `missing` for each test as Go reported it; no Go file and no `go.sum` is added
- PROOF-47 (RULE-47): Init writes `.purlin/evidence/README.md`, byte for byte the same as `templates/evidence-readme.md` and naming `local/` and `ci/`, and the summary reports it as `wrote`
- PROOF-136 (RULE-47): On Windows, init writes `.purlin/evidence/README.md`, byte for byte the same as the README Purlin ships and naming `local/` and `ci/`, and the summary reports it as `wrote` @env(windows)
- PROOF-124 (RULE-47): A project set up once is set up again; the summary reports `.purlin/evidence/README.md` as `kept`
- PROOF-125 (RULE-47): A project set up once adds the line `Our own note.` to `.purlin/evidence/README.md` and is set up again; the summary reports the README as `kept`, and it reads byte for byte as the project left it
- PROOF-150 (RULE-47): A project set up has a `.purlin/evidence/README.md` in which no word starts `audit`, in any case
- PROOF-151 (RULE-47): A new project's `.purlin/evidence/README.md` opens, under `# Evidence`, with the sentence `What a run leaves behind for each feature: each proof's result on each operating system, the commit and the time.`
- PROOF-48 (RULE-48): A pytest project's settings are given one suite of their own, `unit`, running `make test REPORT={report}`; after init runs again, the `tests` setting is exactly that one suite, with no `pytest` suite added
- PROOF-87 (RULE-50): A pytest project holding a test file is set up with nothing to answer from; its settings read `tests` as an empty list
- PROOF-88 (RULE-50): An empty git project is set up with nothing to answer from; it exits 0, the one question it asks is `Commit the files setup wrote?`, and its settings read `tests` as an empty list
- PROOF-89 (RULE-51): A pytest project is set up; afterwards `specs/` is there, there is no `specs/_anchors/`, and the summary names no `specs/_anchors`
- PROOF-128 (RULE-63): A project whose `.purlin/config.json` holds a comma after its last value is set up; it exits 1, prints `.purlin/config.json cannot be read: <the JSON reader's own message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and every file reads as before
- PROOF-153 (RULE-67): A new project set up has a `.gitignore` holding the line `/purlin-report.html`
- PROOF-154 (RULE-67): A new project set up has a `.gitignore` holding the line `.purlin/runtime/`
- PROOF-155 (RULE-73): A new project's `.gitignore` holds `# Purlin runtime: the test reports and the run log, never committed`, `# Dashboard HTML (copied by purlin:init and refreshed by purlin:init --update)` and `# Dashboard data, regenerated locally, never committed`, each on the line above its entry
- PROOF-156 (RULE-73): A new project's `.gitignore` holds the two comment lines `# .purlin/evidence/ is tracked on purpose: it is` and `# the evidence of each run, for somebody who did not make it to read.`
- PROOF-157 (RULE-68): A pytest project is set up with nothing to answer from; the line after the last file it names reads `Commit the files setup wrote? [y/N] `, no line starts `Committed`, and the project's last commit is the one it had before
- PROOF-158 (RULE-69): A pytest project is set up with `--yes`; no commit question is shown, its last commit's subject is `chore(init): set up Purlin`, and the output has `Committed <sha7>, the files setup wrote:`, then `  .purlin/config.json`, `  .gitignore` and `  .purlin/evidence/README.md`
- PROOF-159 (RULE-70): A project with `notes.txt` staged is set up with `--yes`; the commit setup makes holds exactly `.gitignore`, `.purlin/config.json` and `.purlin/evidence/README.md`, and `notes.txt` is still staged
- PROOF-160 (RULE-71): A git project with no commit yet is set up with `--yes`; afterwards it has one commit, `chore(init): set up Purlin`
- PROOF-161 (RULE-72): A project whose git has no author email, with guessing it turned off, is set up with `--yes`; it prints `The files setup wrote are staged and not committed: no email was given and auto-detection is disabled.`, and `.purlin/config.json` is staged
- PROOF-162 (RULE-74): A project set up has its `purlin-report.html` changed by hand, then is set up again; the page holds the changed bytes, and the summary reads `kept purlin-report.html`
- PROOF-171 (RULE-79): A new pytest project, one of whose proofs is tagged `@env` for a system this machine is not, is set up with no flag and nothing to answer from; its output holds `[y/N]` exactly once, on the line `Commit the files setup wrote? [y/N] `
- PROOF-172 (RULE-80): A new pytest project is set up with nothing to answer from; its `.purlin/config.json` holds exactly the keys `tests` and `version`, `tests` an empty list and `version` the text of the plugin's `VERSION` file
- PROOF-173 (RULE-81): A pytest project whose remote is `git@github.com:acme/demo.git`, one of whose proofs is tagged `@env` for a system this machine is not, is set up with `--yes`; afterwards there is no `.github/workflows/purlin.yml`, and no summary line names it
