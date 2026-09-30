# Feature: package

> Description: The evidence package `purlin:export` writes: one data file for one version,
>   holding every rule's words, proofs, tests, results, audit and statuses, for a reviewer who
>   cannot open the repository. It is built from what git holds, says first whether the version
>   is finished, carries the total, the count that pass, what the audit found, what is left to
>   do and every hand check, gives the same bytes for the same tag, and carries a fingerprint of
>   itself. It is evidence handed to a regulated system of record; Purlin makes no claim of
>   compliance.
> Scope: scripts/export/package.py
> Stack: python/stdlib (json, hashlib, subprocess), git worktree
> Highest-Rule: 31
> Highest-Proof: 64

## Rules

- RULE-1: Run with no argument, the command writes `.purlin/evidence/package/<version>.json`, taking the version the project states as `purlin:test --release` reads it for its tag, prints `Evidence package written to <path>. State: <finished|not finished>.`, commits nothing and leaves no checkout behind
- RULE-2: `--release <name>` names the version, the file and the tag the package names, in place of the version the project states or where it states none
- RULE-3: The package's top-level keys are, in this order, `schema` (`purlin-package/3`), `state`, `rules`, `steps`, `audit`, `left`, `purlin_version`, `project`, `version`, `tag`, `commit`, `gate`, `mutation_engine`, `features`, `hand_checks`, `warnings` and `fingerprint`, and `commit` is the commit the evidence was taken at: `HEAD`, stepping back over any commit that changed nothing but files under `.purlin/evidence/package/`
- RULE-4: `rules`, `steps` and `left` say what `purlin:status` says of that commit: the total of rules, the count whose tests pass, and each line of `Left to do` with its kind, count, words and command; while a line that stops a release is left the state is `not finished`
- RULE-5: When nothing is left to do the state is `finished` and `left` is empty
- RULE-6: Each rule carries its words exactly as the spec has them, the one kind of work it waits for or null, its proofs and its tests
- RULE-7: Evidence written and not committed is left out of the package and named, one line per file, in its `warnings` and on the terminal as `<path> is written and not committed; the package leaves it out.`
- RULE-8: The same commit gives the same bytes: exporting twice, or from a second clone at the tag, writes identical files, with `\n` line ends and a trailing newline
- RULE-9: `fingerprint` is the sha256 of the package's canonical bytes with that field empty; `--check <file>` prints `The package matches its fingerprint.` and exits 0 for a package as written, and for one edited afterwards names the mismatch and exits 1
- RULE-10: `--commit` commits the package alone with the subject `purlin: evidence at <sha7>`, naming the commit the evidence was taken at
- RULE-11: Each rule carries each result with its operating system, source, time, commit, runner and machine
- RULE-12: Each rule carries what the audit found with the model and the fingerprint of its instructions
- RULE-14: Each rule carries two statuses, `passed` and `strong`, at both gates
- RULE-15: Nothing in the package names who last changed a test
- RULE-16: Run with no argument in a project that states no version, the command prints `No version: nothing in this project states one. Run purlin:export --release <version>, or write it to a VERSION file.`, writes nothing and exits 1
- RULE-17: Every time in the package is in UTC, ending in `Z`
- RULE-18: A second `--commit` over the same evidence prints `Package unchanged.` and leaves the commit the evidence was taken at named
- RULE-19: Where `.purlin/config.json` cannot be read, the command, `--check` included, prints `.purlin/config.json cannot be read: <cause>. Fix the file by hand; nothing ran and nothing was saved.`, writes nothing and exits 1
- RULE-20: Run with a `--project-root` that is not a folder, the command prints `package.py: <path> is not a directory.`, writes nothing and exits 2
- RULE-21: A command line the export does not take prints the two usage lines, then `package.py: <what is wrong>`, and the command writes nothing and exits 2
- RULE-22: `--check` on a file that is not a package in the format prints `The package does not match its fingerprint: <reason>.` and exits 1, the reason naming what is wrong with the file
- RULE-23: Where the package cannot be built or written, the command prints `export: the package was not written: <why>.` and exits 1
- RULE-24: Where `--commit` cannot commit the package, the command prints `export: the package was not committed: <why>.` after the line naming the file it wrote, and exits 1
- RULE-25: The evidence package states the gate and whether the version is finished, and no field of it says that the software complies with a regulation
- RULE-26: Each feature entry holds exactly `name`, `spec`, `scope`, `anchor` and `rules`, and an anchor's `scope` is `[]`
- RULE-28: A spec that writes a number twice or holds a line left from a merge conflict is named in `left` as the kind `to_repair`, counting specs, with the command `purlin:spec`
- RULE-29: The package carries `audit`, the count of rules the audit found strong, weak and not audited, and `hand_checks`, one entry per rule with a `@manual` proof naming its feature, rule and proofs
- RULE-30: A rule left only to strengthen, because the audit found it weak, leaves the state `finished`
- RULE-31: `tag` names the tag the release writes: `passed/<version>` at the gate `passed`, `signed/<version>` at `signed`

## Proof

- PROOF-1 (RULE-1): In a project at the gate `signed` whose `VERSION` file reads `2.1.0` and whose two rules pass, the command is run with no argument; it exits 0 and prints only `Evidence package written to .purlin/evidence/package/2.1.0.json. State: finished.`; `HEAD` has not moved, `git status` lists only that file, untracked, and `git worktree list` shows one worktree
- PROOF-38 (RULE-1): On Windows, in a project at the gate `signed` whose `VERSION` reads `2.1.0` and whose two rules pass, the command is run with no argument; it exits 0, prints `Evidence package written to .purlin/evidence/package/2.1.0.json. State: finished.`, and `git worktree list` shows one worktree @env(windows)
- PROOF-2 (RULE-2): In a project whose `VERSION` file reads `2.1.0`, the command is run with `--release beta`; it exits 0, its first line begins `Evidence package written to .purlin/evidence/package/beta.json.`, that package reads `version` `beta` and `tag` `signed/beta`, and no `.purlin/evidence/package/2.1.0.json` is written
- PROOF-22 (RULE-2): In a project with no `VERSION` file and nothing else stating a version, the command is run with `--release beta`; it exits 0 and writes `.purlin/evidence/package/beta.json`, which reads `version` `beta` and `tag` `signed/beta`
- PROOF-3 (RULE-3): A project named `proj` at the gate `signed`, with no mutation engine set, is exported; the top-level keys are exactly the seventeen the rule names, in order, `schema` reads `purlin-package/3`, `purlin_version` the installed Purlin's version, `project` `proj`, `gate` `signed`, `mutation_engine` `none`, and `commit` the full sha of `HEAD`
- PROOF-30 (RULE-3): After the evidence is committed, a change to the code is committed on top of it, and the project is exported; the package's `commit` reads the full sha of that code change, the new `HEAD`, and not the commit that holds the evidence
- PROOF-4 (RULE-4): A project at the gate `passed` whose `VERSION` file reads `1.0.0` and which has no evidence is exported; its first line ends `State: not finished.`, and the package reads `rules` 2, `steps` `{"passed": 0}` and `left` exactly one line: kind `to_test`, count 2, words `2 rules to test`, command `purlin:test`
- PROOF-5 (RULE-4): A project at the gate `signed` has a third rule, `A locked account returns 423 (URS-042)`, with no proof and no test, and is exported; that rule carries those words exactly, no proofs, no tests, one result reading `no test` and `left` `no_proof`, and the package's first line left reads `1 rule to write a proof for` with `purlin:spec`
- PROOF-8 (RULE-5): A project at the gate `passed` whose two rules pass is exported; its first line ends `State: finished.`, and the package reads `state` `finished`, `rules` 2, `steps` `{"passed": 2}` and `left` empty
- PROOF-9 (RULE-6): In a released project's package, `RULE-2` reads the words `Invalid credentials return 401 and the body "denied"`, `left` null, one proof, `PROOF-2`, with its words as the spec has them, not manual and with no operating system, and one test under `PROOF-2`, `test_a_bad_password_is_denied` in `tests/test_login.py`
- PROOF-18 (RULE-6): At the gate `passed`, a rule with no proof, `RULE-3`, has one passing test marked with its own id, and is exported; `RULE-3` carries no proofs, one test under `RULE-3`, `test_a_locked_account_returns_423` in `tests/test_login.py`, and one result `passed`, while `RULE-2` lists its test under `PROOF-2`
- PROOF-12 (RULE-7): With both rules passing, the `ci` evidence is written again with the later time `2026-09-14T12:00:00Z` and not committed, and the project is exported; it prints `.purlin/evidence/ci/login.json is written and not committed; the package leaves it out.`, `warnings` holds only that line, and `RULE-2`'s one result carries the committed time `2026-09-13T12:00:00Z`
- PROOF-13 (RULE-8): A project is exported twice with nothing changed between; the two files are the same byte for byte, the file ends in `}` and a newline, and it holds no carriage return
- PROOF-14 (RULE-8): A released project is cloned into a second folder, `passed/2.1.0` is checked out there, and the project is exported there; it exits 0, prints only `Evidence package written to .purlin/evidence/package/2.1.0.json. State: finished.`, and the file it writes holds exactly the bytes of `.purlin/evidence/package/2.1.0.json` as the tag holds it
- PROOF-39 (RULE-8): On Windows, with `core.autocrlf` set to `true`, a released project is cloned into a second folder and exported at `passed/2.1.0`; the file it writes holds exactly the bytes the tag holds, with no carriage return @env(windows)
- PROOF-16 (RULE-9): A package is exported and its file checked with `--check`; it exits 0 and prints exactly the one line `The package matches its fingerprint.`
- PROOF-32 (RULE-9): In an exported package, `fingerprint` reads 64 lowercase hexadecimal characters, equal to the sha256 taken separately over the file's bytes with that field's value emptied to `""`
- PROOF-17 (RULE-9): In an exported package the first `"passed"` is changed to `"failed"` and the file checked with `--check`; it exits 1 and its first line reads `The package does not match its fingerprint: the package records the fingerprint <as written> and its content gives <the sha256 of the edited bytes with that field emptied>.`, the two values differing
- PROOF-33 (RULE-9): An exported package has a carriage return put before each newline, nothing else changed, and is checked with `--check`; it exits 1 and prints only `The package does not match its fingerprint: the fingerprint matches the content, but the bytes are not in the canonical form.`
- PROOF-40 (RULE-9): On Windows, a package is exported and its file checked with `--check`; it exits 0 and prints exactly the one line `The package matches its fingerprint.` @env(windows)
- PROOF-10 (RULE-10): In a project whose `HEAD` is `<sha>`, the command is run with `--commit`; it exits 0, its last line reads `Package committed.`, the newest commit's subject reads `purlin: evidence at <the first 7 characters of sha>`, and `git status` is clean
- PROOF-35 (RULE-10): With a change to `src/login.py` staged and not committed, the command is run with `--commit`; the commit it makes changes `.purlin/evidence/package/2.1.0.json` and nothing else, and the change to `src/login.py` is still staged after it
- PROOF-25 (RULE-11): In a released project whose tests ran on a remote runner, `RULE-2`'s one result reads source `ci`, `passed`, runner `ci`, the time `2026-09-13T12:00:00Z`, current, this machine's operating system, the machine `remote runner, ` followed by that system's name, such as `remote runner, macOS`, and the full sha of the commit the tests ran at
- PROOF-26 (RULE-12): In a released project's package, `RULE-2`'s audit reads `strong`, no findings, strength 90, the model `claude-opus-5-20260901`, the fingerprint of the audit's instructions as the evidence records it, and the time `2026-09-13T12:05:00Z`
- PROOF-20 (RULE-14): At the gate `signed`, with both rules passing and audited `strong`, `RULE-1`'s `statuses` holds exactly `passed` and `strong`, reading `passed` and `strong`
- PROOF-29 (RULE-14): A project at the gate `passed` whose two rules pass and which no audit has read is exported; `RULE-2`'s `statuses` holds exactly `passed` and `strong`, reading `passed` and `not audited`
- PROOF-11 (RULE-15): In a released project whose test file was committed by `dev@example.com`, the package's text carries neither that address nor the word `author` anywhere
- PROOF-21 (RULE-16): In a project with no `VERSION` file and nothing else stating a version, the command is run with no argument; it exits 1, prints only `No version: nothing in this project states one. Run purlin:export --release <version>, or write it to a VERSION file.`, and no `.purlin/evidence/package` folder exists
- PROOF-15 (RULE-17): In a released project's package, the times stored under `at` that are not null number at least four, and each reads as a date, `T`, a time to the second and `Z`, as `2026-09-13T12:00:00Z` does, with no offset and no fraction of a second
- PROOF-34 (RULE-18): After the package was committed with `--commit` over the evidence at `<sha>`, `--commit` is run again with nothing changed; it exits 0, its last line reads `Package unchanged.`, `HEAD` has not moved, and the package's `commit` still reads the full `<sha>`
- PROOF-36 (RULE-19): In a project whose `VERSION` file reads `2.1.0`, `.purlin/config.json` reads `{"gate": "signed",}`, with a trailing comma, and the command is run with no argument; it exits 1, prints only `.purlin/config.json cannot be read: <the JSON reader's own message> at line 1. Fix the file by hand; nothing ran and nothing was saved.`, and no `.purlin/evidence/package` folder exists
- PROOF-37 (RULE-19): A package is exported, then `.purlin/config.json` is made to read `{"gate": "signed",}`, with a trailing comma, and the package is checked with `--check`; it exits 1 and prints only `.purlin/config.json cannot be read: <the JSON reader's own message> at line 1. Fix the file by hand; nothing ran and nothing was saved.`
- PROOF-41 (RULE-20): The command is run with `--project-root` naming a path where no folder is; it exits 2 and prints only `package.py: <that path> is not a directory.`
- PROOF-42 (RULE-21): Each of `--release`, `--project-root` and `--check` is given as the last word, with no value after it; each run exits 2 and prints only the two usage lines, the first `Usage: package.py [--release NAME] [--commit] [--project-root DIR]`, then `package.py: <that option> needs a value.`
- PROOF-43 (RULE-21): In a project whose `VERSION` file reads `2.1.0`, the command is run with `--verbose`; it exits 2, prints only the two usage lines, then `package.py: unexpected argument --verbose`, and no `.purlin/evidence/package` folder exists
- PROOF-44 (RULE-21): Each of `--commit` and `--release beta` is given beside `--check <file>`; each run exits 2 and prints only the two usage lines, then `package.py: --check reads a file and takes nothing else.`
- PROOF-45 (RULE-22): Each of a file whose bytes are not UTF-8 and a file of UTF-8 text that is not JSON is checked with `--check`; each run exits 1 and prints only `The package does not match its fingerprint: the file is not UTF-8 JSON.`
- PROOF-46 (RULE-22): An exported package has its `schema` changed to `purlin-package/2` and is checked with `--check`; it exits 1 and prints only `The package does not match its fingerprint: the file does not carry the schema purlin-package/3.`
- PROOF-47 (RULE-22): An exported package gains a top-level key `extra` and is checked with `--check`; it exits 1 and prints only `The package does not match its fingerprint: the package carries keys the format does not name: extra.`
- PROOF-48 (RULE-22): An exported package has its top-level `warnings` key taken out and is checked with `--check`; it exits 1 and prints only `The package does not match its fingerprint: the top-level keys are not the ones the format names, in its order.`
- PROOF-49 (RULE-22): `--check` is given a path where no file is; it exits 1 and prints only `The package does not match its fingerprint: the file could not be read: <the operating system's own message>.`
- PROOF-50 (RULE-23): In a project whose `VERSION` file reads `2.1.0` and which has no commit yet, the command is run with no argument; it exits 1, prints only `export: the package was not written: the project has no commit yet.`, and no `.purlin/evidence/package` folder exists
- PROOF-51 (RULE-23): In a project where git cannot add a second checkout, because `.git/worktrees` is a file, the command is run with no argument; it exits 1 and prints only `export: the package was not written: the commit <the first 7 characters of HEAD> could not be checked out: <git's own message>.`
- PROOF-52 (RULE-23): In a project where `.purlin/evidence/package` is a file and not a folder, the command is run with no argument; it exits 1 and prints only `export: the package was not written: <the operating system's own message>.`
- PROOF-53 (RULE-24): In a project whose commit hook refuses every commit, printing `no commits today`, the command is run with `--commit`; it exits 1, its last line reads `export: the package was not committed: git commit failed: no commits today.`, and `HEAD` has not moved
- PROOF-54 (RULE-24): In a project whose index another git process holds locked, the command is run with `--commit`; it exits 1, and the line after the one naming the file it wrote begins `export: the package was not committed: git add failed: `, followed by git's own message
- PROOF-55 (RULE-25): At the gate `signed`, with both rules passing, the package the release run commits holds exactly the top-level keys the format lists, its `gate` reads `signed` and its `state` `finished`, and no key or value in it holds the word `compliant` or `compliance`
- PROOF-56 (RULE-26): In a released project's package, the `login` entry holds exactly the five fields `name`, `spec`, `scope`, `anchor` and `rules`, reading `login`, `specs/auth/login.md`, `["src/login.py"]` and `false`
- PROOF-57 (RULE-26): Beside `login`, an anchor `secure` whose file carries `> Scope: src/login.py` is exported; its entry reads `anchor` `true` and `scope` `[]`
- PROOF-60 (RULE-28): At the gate `signed`, `login` writes `PROOF-2` twice and the project is exported; the package's `left` holds `{"kind": "to_repair", "count": 1, "text": "1 spec to repair", "command": "purlin:spec"}`
- PROOF-61 (RULE-29): At the gate `signed`, both rules pass, `RULE-1` is audited `strong` and `RULE-2` `weak`, and the project is exported; the package's `audit` reads `{"strong": 1, "weak": 1, "not_audited": 0}`
- PROOF-62 (RULE-29): At the gate `signed`, `PROOF-2` is marked `@manual` and the project exported; `hand_checks` holds exactly `{"feature": "login", "rule": "RULE-2", "proofs": ["PROOF-2"], "checked": "in the sign-offs"}`
- PROOF-63 (RULE-30): At the gate `signed`, both rules pass and `RULE-2` is audited `weak` with one finding; the package reads `state` `finished` and `left` exactly `1 rule to strengthen` with `purlin:build`
- PROOF-64 (RULE-31): A project at the gate `passed` whose `VERSION` file reads `2.1.0` is exported; the package reads `tag` `passed/2.1.0`
