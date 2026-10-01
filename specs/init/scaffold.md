# Feature: scaffold

> Description: `purlin:init`, which sets a project up. It asks one
>   question, whether it may commit the files it wrote, and commits only
>   those. It writes the settings file with `version` and an empty `tests`,
>   `specs/`, the evidence folder and its README, the `.gitignore` block and
>   the dashboard copy, names every file in the summary, writes nothing into
>   the project's test suite and installs no git hook. A project it sets up
>   runs its tests, commits the evidence and signs it off.
> Scope: scripts/init/scaffold.py, templates/config.json, templates/gitignore.purlin, templates/evidence-readme.md
> Stack: python3 (stdlib only, 3.9 floor)
> Highest-Rule: 83
> Highest-Proof: 173

## Rules

- RULE-8: init writes nothing into a project's test suite: no `conftest.py`, no Jest or Vitest configuration and no logger, and a runner configuration the project wrote is left as it was
- RULE-18: The summary names every path init wrote, kept or copied, and each path it says it wrote is on disk afterwards
- RULE-20: A second run writes no file: every file outside `.git/` reads the same, a block init appended to a file the project also owns is there once, and a `tests` setting the project already carries is kept as it is
- RULE-21: A project set up from a marketplace install of the plugin ends the same as one set up from this checkout, and no file init writes names the folder the plugin ran from or this repository's development folder
- RULE-24: init installs no git hook at all and leaves a hook someone else wrote untouched: nothing runs at commit time and nothing runs at push time
- RULE-33: `--update` hands the project to `scripts/init/update.py`
- RULE-36: A project init set up walks run, commit and sign-off: `purlin:test --all --commit` commits the work and then its evidence, and the first `purlin:sign` signs the evidence package in a signed commit and writes `signed/<version>`
- RULE-37: Each language is set up the same way: init writes an empty `tests` setting and adds nothing to its tests, and with the entry its first test run suggests written, its one marked test runs through `purlin:test` and is tied to its marker
- RULE-47: Init creates `.purlin/evidence/` holding one `README.md`, the same bytes as `templates/evidence-readme.md`
- RULE-67: A new project's `.gitignore` keeps out what a run writes locally: `/purlin-report.html` and `.purlin/runtime/`
- RULE-68: Setup commits only on `y`, `yes` or `--yes`, in one commit `chore(init): set up Purlin`, the project's first where it has none; any other answer, an empty one or the end of input commits nothing
- RULE-70: The commit carries only the files setup wrote or changed that git does not ignore: a file the project had already staged stays staged and out of it
- RULE-82: Each refusal of setup names what is wrong and what fixes it, and writes nothing more: a folder that is not a git repository exits 2, a `.purlin/config.json` that cannot be read exits 1, and a commit git refuses leaves the files staged with git's own message
- RULE-83: Setup asks one question, `Commit the files setup wrote? [y/N] `, and nothing about how the tests run, and writes a settings file holding exactly `version`, the plugin's `VERSION` file, and `tests`, an empty list where the project carried none

## Proof

- PROOF-8 (RULE-8): A pytest project with no `conftest.py` is set up; afterwards it holds no `conftest.py`, the summary names none, every file it held reads byte for byte the same, and the only paths added are `.gitignore`, `.purlin/`, `.purlin/config.json`, `.purlin/evidence/`, `.purlin/evidence/README.md`, `purlin-report.html` and `specs/`
- PROOF-61 (RULE-8): A Jest project whose own `jest.config.js` reads `// ours` is set up; the file still reads `// ours` and the summary does not name it
- PROOF-108 (RULE-18): A pytest project is set up; the files and folders that appear in the project are exactly the paths its summary reports as `wrote` or `copied`, and each of them is on disk
- PROOF-20 (RULE-20): Init is run twice on the same project; no line of the second run's summary begins `wrote`, and every file and folder in the project outside `.git/` reads byte for byte the same after the second run as before it
- PROOF-48 (RULE-20): A pytest project's settings are given one suite of their own, `unit`, running `make test REPORT={report}`; after init runs again, the `tests` setting is exactly that one suite, with no `pytest` suite added
- PROOF-130 (RULE-20): On Windows, a project whose `.gitignore` reads `node_modules/` followed by a carriage return and a line feed is set up twice; the file is the same after the second run as after the first, and holds `.purlin/report-data.js` exactly once @env(windows)
- PROOF-22 (RULE-21): A marketplace-style copy of the plugin, run with `CLAUDE_PLUGIN_ROOT` naming it, sets up a pytest project; the same project set up from this checkout ends with the same files, `.purlin/report-data.js` aside, and the same output, paths and commits aside
- PROOF-23 (RULE-21): Init sets up a project; no readable file in the project outside `.git/` holds `/dev/`, once every `/dev/null` is set aside, and none holds a relative path starting `dev/`, such as `dev/test_x.py`
- PROOF-132 (RULE-21): On Windows, a marketplace copy of the plugin, named by `CLAUDE_PLUGIN_ROOT`, sets up a project; no readable file outside `.git/` holds the copy's path, spelled with `\` or with `/` @env(windows)
- PROOF-24 (RULE-24): Init is run; the files under `.git/hooks/` are exactly those that were there before it ran, and neither `pre-push` nor `pre-commit` is among them
- PROOF-112 (RULE-24): A project whose `.git/hooks/pre-push` reads `echo mine` is set up; the hook reads the same afterwards
- PROOF-33 (RULE-33): On a project init has just set up, `--update --yes` exits 0 and prints `Nothing is pending: this project is at <version>.`, the version being the plugin's `VERSION` file
- PROOF-36 (RULE-36): A python project, with one committed spec, its marked test and its suggested test entry, runs `purlin:test --all --commit`; it exits 0, commits `purlin: specs, tests and settings for greeting`, then `purlin: evidence at <that commit's sha7>` holding `.purlin/evidence/local/greeting.json`, and ends `Every rule passes its tests on the committed evidence. To sign it: purlin:sign` @env(macos)
- PROOF-119 (RULE-36): That audited python project, with a `VERSION` file reading `0.1.0` and an SSH signing key set up for `jane@acme.com`, runs `purlin:sign --answers` with the signature answered yes; it exits 0, its commit carries a signature, and it prints `Signed 0.1.0 as jane@acme.com with the key ending ...<the key fingerprint's last 4 characters>.` @env(macos)
- PROOF-93 (RULE-36): That first sign-off writes the tag `signed/0.1.0` on its commit, and prints `Push the branch and the tag: git push origin <branch> signed/0.1.0`, `<branch>` being the branch it signed on @env(macos)
- PROOF-37 (RULE-37): A python project set up with nothing to answer from has `tests` empty and no `conftest.py`; its first `purlin:test` suggests an entry named `pytest`, and with it written the one marked test's run prints `Markers: 1 tied to a test, 0 not tied.` and `1 rule. 1 passes its tests.` @env(macos)
- PROOF-94 (RULE-37): A typescript project set up with nothing to answer from has `tests` empty and no `vitest.config.ts`; its first `purlin:test` suggests an entry named `vitest`, and with it written the one marked test's run prints `1 rule. 1 passes its tests.`; it is skipped where npm cannot install Vitest @env(macos)
- PROOF-95 (RULE-37): A C# project set up with nothing to answer from has `tests` empty; its first `purlin:test` suggests an entry named `dotnet`, and with it written the one marked test's run prints `1 rule. 1 passes its tests.`. It is skipped with a note where `dotnet` is not installed @env(macos)
- PROOF-47 (RULE-47): Init writes `.purlin/evidence/README.md`, byte for byte the same as `templates/evidence-readme.md` and naming `local/` and `ci/`, and the summary reports it as `wrote`
- PROOF-136 (RULE-47): On Windows, init writes `.purlin/evidence/README.md`, byte for byte the same as the README Purlin ships and naming `local/` and `ci/`, and the summary reports it as `wrote` @env(windows)
- PROOF-153 (RULE-67): A new project set up has a `.gitignore` holding the line `/purlin-report.html`
- PROOF-154 (RULE-67): A new project set up has a `.gitignore` holding the line `.purlin/runtime/`
- PROOF-157 (RULE-68): A pytest project is set up with nothing to answer from; the line after the last file it names reads `Commit the files setup wrote? [y/N] `, no line starts `Committed`, and the project's last commit is the one it had before
- PROOF-158 (RULE-68): A pytest project is set up with `--yes`; no commit question is shown, its last commit's subject is `chore(init): set up Purlin`, and the output has `Committed <sha7>, the files setup wrote:`, then `  .purlin/config.json`, `  .gitignore` and `  .purlin/evidence/README.md`
- PROOF-160 (RULE-68): A git project with no commit yet is set up with `--yes`; afterwards it has one commit, `chore(init): set up Purlin`
- PROOF-159 (RULE-70): A project with `notes.txt` staged is set up with `--yes`; the commit setup makes holds exactly `.gitignore`, `.purlin/config.json` and `.purlin/evidence/README.md`, and `notes.txt` is still staged
- PROOF-31 (RULE-82): Init with `--yes` in an empty folder that is not a git repository exits 2, its error output is the one line `This is not a git repository. Run git init, then purlin:init.`, and the folder is still empty
- PROOF-128 (RULE-82): A project whose `.purlin/config.json` holds a comma after its last value is set up; it exits 1, prints `.purlin/config.json cannot be read: <the JSON reader's own message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and every file reads as before
- PROOF-161 (RULE-82): A project whose git has no author email, with guessing it turned off, is set up with `--yes`; it prints `The files setup wrote are staged and not committed: no email was given and auto-detection is disabled.`, and `.purlin/config.json` is staged
- PROOF-171 (RULE-83): A new pytest project, one of whose proofs is tagged `@env` for a system this machine is not, is set up with no flag and nothing to answer from; its output holds `[y/N]` exactly once, on the line `Commit the files setup wrote? [y/N] `
- PROOF-172 (RULE-83): A new pytest project is set up with nothing to answer from; its `.purlin/config.json` holds exactly the keys `tests` and `version`, `tests` an empty list and `version` the text of the plugin's `VERSION` file
- PROOF-88 (RULE-83): An empty git project is set up with nothing to answer from; it exits 0, the one question it asks is `Commit the files setup wrote?`, and its settings read `tests` as an empty list
