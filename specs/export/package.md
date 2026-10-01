# Feature: package

> Description: The evidence package `purlin:sign` builds: one data file for one version,
>   holding every rule's words, proofs, tests, results, audit and statuses, for a reviewer who
>   cannot open the repository. It is built from the evidence committed at the commit being
>   signed, says first whether every rule's tests pass, carries the total, the count that pass,
>   who ran the tests, where and when, what the audit found, what is left to do, every hand
>   check and who wrote and last changed each rule, proof and test, gives the same bytes for the
>   same commit, and carries a fingerprint of itself. It is evidence handed to a regulated
>   system of record; Purlin makes no claim of compliance.
> Scope: scripts/export/package.py
> Stack: python/stdlib (json, hashlib, subprocess), git worktree
> Highest-Rule: 37
> Highest-Proof: 76

## Rules

- RULE-1: The package for a version is written to `.purlin/evidence/package/<version>.json`, and building it leaves no second checkout behind
- RULE-2: `purlin:sign --version <name>` names the version, the file and the tag the package names, in place of the version the project states or where it states none
- RULE-3: The package's top-level keys are, in this order, `schema` (`purlin-package/4`), `met`, `rules`, `steps`, `audit`, `left`, `purlin_version`, `project`, `version`, `tag`, `commit`, `runs`, `features`, `hand_checks`, `warnings` and `fingerprint`, and `commit` is the commit the evidence was taken at: `HEAD`, stepping back over any commit that changed nothing but files under `.purlin/evidence/package/`
- RULE-4: `rules`, `steps` and `left` say what `purlin:status` says of that commit: the total of rules, the count whose tests pass, and each line of `Left to do` with its kind, count, words and command
- RULE-5: `met` is true when no line of `left` is of a kind that stops the tests being met, so a rule left only to strengthen, because the audit found it weak, leaves it true; `left` is empty when nothing is left to do
- RULE-6: Each rule carries its words exactly as the spec has them, the one kind of work it waits for or null, its proofs and its tests
- RULE-8: The same commit gives the same bytes: the package built twice over one commit, in two clones, is identical, with `\n` line ends and a trailing newline
- RULE-9: `fingerprint` is the sha256 of the package's canonical bytes with that field empty, and a package changed after it was written does not match it
- RULE-11: Each rule carries each result with its operating system, source, time, commit, runner and machine
- RULE-12: Each rule carries what the audit found with the model and the fingerprint of its instructions
- RULE-14: Each rule carries two statuses, `passed` and `strong`
- RULE-17: Every time in the package is in UTC, ending in `Z`
- RULE-22: `purlin:sign --check` on a file that is not a package in the format exits 1 and prints one line, `The package does not match its fingerprint: <reason>.`, the reason naming what is wrong with the file
- RULE-23: Where the package cannot be written, `purlin:sign` prints one line naming why, makes no commit and no tag, and exits 1
- RULE-25: The evidence package states whether every rule's tests pass, as `met`, and no field of it says that the software complies with a regulation
- RULE-26: Each feature entry holds exactly `name`, `spec`, `scope`, `anchor` and `rules`, and an anchor's `scope` is `[]`
- RULE-29: The package carries `audit`, the count of rules the audit found strong, weak and not audited, and `hand_checks`, one entry per rule with a `@manual` proof naming its feature, rule and proofs
- RULE-32: The package carries `runs`, one entry per group of counted results sharing a source, a system, who ran them and a machine, local first and then by system, each naming `by`, the email its sections record, `machine`, `os`, `source`, `at`, `commit` and the count of `rules`
- RULE-33: Each result carries `same_code`, true when every commit from the one its tests ran at to the package's `commit` changes only files under `.purlin/`
- RULE-34: `project` is the name the project's own files give it, read when the package is built
- RULE-35: The version is read from the `VERSION` file, `package.json`, `pyproject.toml` or the first `*.csproj` at the project's root, in that order
- RULE-36: Each result carries `nothing_to_check`, one entry per proof whose every tied test skipped with a reason beginning `nothing to check:`, naming the proof and the reason
- RULE-37: Each rule carries `authors`, read from git: who first wrote the rule's wording and in which commit, followed through a renumber; for each proof who first wrote it and who last changed it, with commits; and for each tied test who last changed it, with the commit

## Proof

- PROOF-1 (RULE-1): In a project whose `VERSION` file reads `2.1.0` and whose two rules pass, the first sign-off of `2.1.0` is answered yes; its signed commit carries `.purlin/evidence/package/2.1.0.json`, and `git worktree list` shows one worktree
- PROOF-2 (RULE-2): In a project whose `VERSION` file reads `2.1.0`, `purlin:sign --version beta` is answered yes; the signed commit carries `.purlin/evidence/package/beta.json`, which reads `version` `beta` and `tag` `signed/beta`, and no `.purlin/evidence/package/2.1.0.json` is written
- PROOF-22 (RULE-2): In a project with no `VERSION` file and nothing else stating a version, `purlin:sign --version beta` is answered yes; the signed commit carries `.purlin/evidence/package/beta.json`, which reads `version` `beta` and `tag` `signed/beta`
- PROOF-3 (RULE-3): A project whose two rules pass is signed for `2.1.0`; its package's top-level keys are exactly the sixteen the rule names, in order, `schema` reads `purlin-package/4`, `purlin_version` the installed Purlin's version, and `commit` the full sha of `HEAD` as it stood before the sign-off's own commit, the commit that holds the evidence
- PROOF-30 (RULE-3): With `2.1.0` signed in a commit `<s>` over the code at `<c>`, `2.2.0` is signed with nothing else changed; the `2.2.0` package's `commit` reads the full sha of `<c>`, not of `<s>`
- PROOF-5 (RULE-4): A project has a third rule, `A locked account returns 423 (URS-042)`, with no proof and one passing test marked with the rule's own id, and is signed; that rule carries those words exactly, no proofs, one result reading `passed` and `left` `no_proof`, and the package's first line left reads `1 rule to write a proof for` with `purlin:spec`
- PROOF-8 (RULE-5): A project whose two rules pass is signed; its package reads `met` `true`, `rules` 2, `steps` `{"passed": 2}` and `left` empty
- PROOF-63 (RULE-5): Both rules pass and `RULE-2` is audited `weak` with one finding; the package the sign-off commits reads `met` `true` and `left` exactly `1 rule to strengthen` with `purlin:build`
- PROOF-9 (RULE-6): In a signed project's package, `RULE-2` reads the words `Invalid credentials return 401 and the body "denied"`, `left` null, one proof, `PROOF-2`, with its words as the spec has them, not manual and with no operating system, and one test under `PROOF-2`, `test_a_bad_password_is_denied` in `tests/test_login.py`
- PROOF-18 (RULE-6): A rule with no proof, `RULE-3`, has one passing test marked with its own id, and the project is signed; `RULE-3` carries no proofs, one test under `RULE-3`, `test_a_locked_account_returns_423` in `tests/test_login.py`, and one result `passed`, while `RULE-2` lists its test under `PROOF-2`
- PROOF-13 (RULE-8): Two clones of one repository at the same commit each sign `2.1.0`, each by its own signer; the two committed packages are the same byte for byte, each ends in `}` and a newline, and neither holds a carriage return
- PROOF-39 (RULE-8): On Windows, with `core.autocrlf` set to `true`, two clones of one repository at the same commit each sign `2.1.0`; the two committed packages are the same byte for byte and hold no carriage return @env(windows)
- PROOF-32 (RULE-9): In a signed package, `fingerprint` reads 64 lowercase hexadecimal characters, equal to the sha256 taken separately over the file's bytes with that field's value emptied to `""`
- PROOF-17 (RULE-9): In a signed package the first `"passed"` is changed to `"failed"` and the file checked with `purlin:sign --check`; it exits 1 and its first line reads `The package does not match its fingerprint: the package records the fingerprint <as written> and its content gives <the sha256 of the edited bytes with that field emptied>.`, the two values differing
- PROOF-25 (RULE-11): In a signed project one of whose results sits under the source `ci`, written on the machine `build-7` by `runner@example.com`, `RULE-2`'s one result reads source `ci`, `passed`, runner `runner`, the time `2026-09-13T12:00:00Z`, current, this machine's operating system, the machine `build-7` and the full sha of the commit the tests ran at
- PROOF-26 (RULE-12): In a signed project's package, `RULE-2`'s audit reads `strong`, no findings, the model `claude-opus-5-20260901`, the fingerprint of the audit's instructions as the evidence records it, and the time `2026-09-13T12:05:00Z`
- PROOF-20 (RULE-14): With both rules passing and audited `strong`, the project is signed; `RULE-1`'s `statuses` holds exactly `passed` and `strong`, reading `passed` and `strong`
- PROOF-29 (RULE-14): A project whose two rules pass and which no audit has read is signed; `RULE-2`'s `statuses` holds exactly `passed` and `strong`, reading `passed` and `not audited`
- PROOF-15 (RULE-17): In a signed project's package, the times stored under `at` that are not null number at least four, and each reads as a date, `T`, a time to the second and `Z`, as `2026-09-13T12:00:00Z` does, with no offset and no fraction of a second
- PROOF-45 (RULE-22): Each of a file whose bytes are not UTF-8 and a file of UTF-8 text that is not JSON is checked with `purlin:sign --check`; each run exits 1 and prints only `The package does not match its fingerprint: the file is not UTF-8 JSON.`
- PROOF-46 (RULE-22): A signed package has its `schema` changed to `purlin-package/3` and is checked with `purlin:sign --check`; it exits 1 and prints only `The package does not match its fingerprint: the file does not carry the schema purlin-package/4.`
- PROOF-52 (RULE-23): In a project where `.purlin/evidence/package` is a file and not a folder, the walk is answered yes; it exits 1, prints one line carrying the operating system's own message, and adds no commit and no tag
- PROOF-55 (RULE-25): With both rules passing, the package the first sign-off commits holds exactly the top-level keys the format lists, its `met` reads `true`, and no key or value in it holds the word `compliant` or `compliance`
- PROOF-56 (RULE-26): In a signed project's package, the `login` entry holds exactly the five fields `name`, `spec`, `scope`, `anchor` and `rules`, reading `login`, `specs/auth/login.md`, `["src/login.py"]` and `false`
- PROOF-57 (RULE-26): Beside `login`, an anchor `secure` whose file carries `> Scope: src/login.py` is signed with it; its entry reads `anchor` `true` and `scope` `[]`
- PROOF-61 (RULE-29): Both rules pass, `RULE-1` is audited `strong` and `RULE-2` `weak`, and the project is signed; the package's `audit` reads `{"strong": 1, "weak": 1, "not_audited": 0}`
- PROOF-62 (RULE-29): `PROOF-2` is marked `@manual` and the project signed; `hand_checks` holds exactly `{"feature": "login", "rule": "RULE-2", "proofs": ["PROOF-2"], "checked": "in the sign-offs"}`
- PROOF-65 (RULE-32): `dana.dev@labconnect.example` runs every test on `dana-laptop`, a Linux machine, and commits them; the package's `runs` holds one entry reading `by` `dana.dev@labconnect.example`, `machine` `dana-laptop`, `os` `linux`, `source` `local`, the run's time and commit, and `rules` `2`
- PROOF-66 (RULE-32): Beside Dana's local run, `PROOF-3` tagged `@env(windows)` ran under the source `ci` on the machine `build-7` as `runner@example.com`; `runs` holds two entries, the local one first, then one reading `by` `runner@example.com`, `machine` `build-7`, `source` `ci`, `os` `windows` and `rules` `1`
- PROOF-67 (RULE-33): The tests run and are committed at `<c>`, then a commit changes only `.purlin/evidence/ci/login.json`, the results a run on another system committed; the project is signed and every result in its package reads `same_code` `true`
- PROOF-68 (RULE-33): The tests run and are committed at `<c>`, then a commit changes `README.md`, which no spec covers; `purlin:sign` prints only `No sign-off: these results were not taken on this version of the code, <sha7>: login on Linux/Unix. Run purlin:test --all --commit, then purlin:sign.`
- PROOF-69 (RULE-34): A project kept in a folder named `work`, whose `pyproject.toml` reads `name = "labconnect"` under `[project]`, is signed; its package reads `project` `labconnect`
- PROOF-70 (RULE-35): The `VERSION` file reads `2.1.0` and `package.json` reads `9.9.9`; the sign-off writes `.purlin/evidence/package/2.1.0.json`, reading `version` `2.1.0`
- PROOF-71 (RULE-35): With no `VERSION` file and no `package.json`, `pyproject.toml` reads `version = "3.0.0"` under `[project]`; the sign-off writes `.purlin/evidence/package/3.0.0.json`, reading `version` `3.0.0`
- PROOF-72 (RULE-36): Anchor `screens` has `PROOF-3`, whose one test skips with `nothing to check: this project has no screens`; in the signed package its Linux/Unix result reads `passed` and `nothing_to_check` `[{"proof": "PROOF-3", "reason": "this project has no screens"}]`
- PROOF-74 (RULE-37): `quinn.qa@labconnect.example` commits `PROOF-1` of `login`, then `pat.product@labconnect.example` rewords it; in the signed package that proof reads `written_by` Quinn's address with Quinn's commit and `changed_by` Pat's address with Pat's commit
- PROOF-75 (RULE-37): `dana.dev@labconnect.example` last changed `test_valid_credentials_return_200` in `tests/test_login.py`; in the signed package that test's entry reads `changed_by` `dana.dev@labconnect.example` and the full sha of Dana's commit
- PROOF-76 (RULE-37): `pat.product@labconnect.example` commits `RULE-4` of `login`, then a renumbering commit by `dana.dev@labconnect.example` moves it to `RULE-6`; in the signed package `RULE-6`'s `authors.rule` reads `written_by` `pat.product@labconnect.example` and the full sha of Pat's commit
