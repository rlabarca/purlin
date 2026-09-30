# Feature: evidence

> Description: The fingerprint says what a feature's evidence was taken over:
>   its own rule and proof lines, the files its `> Scope:` names, or for an
>   anchor every tracked file but Purlin's records, and the files that carry
>   its proof markers, each read from the working tree. The reader
>   loads a feature's two evidence files, one per source, and says which
>   sections are current against a fingerprint taken now, which parts are out
>   of date, which audit entry answers a rule, which section is the newest,
>   and what a section's result is for each proof. It names the operating
>   system it runs on, and the words a person reads for each one.
>   The reader never writes.
> Scope: scripts/mcp/purlin/fingerprint.py, scripts/mcp/purlin/evidence.py
> Stack: python/stdlib, hashlib, json, subprocess (list-only)
> Highest-Rule: 33
> Highest-Proof: 85

## Rules

- RULE-1: A fingerprint is three 64-character sha256 hex strings named `spec`, `code` and `tests`
- RULE-2: The `spec` part covers the spec's own rule and proof lines; editing a rule's text changes `spec` and no other part
- RULE-4: The `code` part covers the tracked files the `> Scope:` entries reach, and an entry naming a file reaches that file; editing a file it reaches changes `code` and no other part
- RULE-5: A scope entry that reaches no tracked file, because the path does not exist or the glob matches nothing, is listed as unmatched, and the fingerprint is still taken
- RULE-6: A spec with no `> Scope:` line is reported incomplete with the reason `no > Scope: line`, and its fingerprint is still taken, with a `code` part that is the sha256 of the empty string
- RULE-7: The `tests` part covers every tracked test file, one a suite of the `tests` setting names, carrying a marker for the feature; editing such a file changes `tests` and no other part; a marker for another feature is not counted
- RULE-8: An untracked file changes no part of the fingerprint; an untracked file under the feature's scope or in the directory of one of its marker files is listed as untracked, and a file git ignores is not listed
- RULE-9: Asking for the fingerprint of a name no spec defines raises `KeyError` naming that name
- RULE-10: Comparing a stored fingerprint with one taken now names the parts that differ in the order `spec`, `code`, `tests`; a stored fingerprint that is missing or is not an object differs on all three
- RULE-11: The reader loads `.purlin/evidence/local/<feature>.json` and `.purlin/evidence/ci/<feature>.json`; a source with no file reads as no evidence and adds no warning
- RULE-12: A file that is not valid JSON, is not a JSON object, or whose `schema` is not `purlin-evidence/2` is ignored with one warning naming its path
- RULE-13: A file whose `source` field disagrees with the folder it sits in is ignored with exactly one warning naming its path, the source it names and the folder
- RULE-14: Each of the keys `windows`, `macos` and `linux` under `platforms` is one section, so a file holding two operating systems gives two sections; sections are listed `local` first, then in that operating system order, and any other key is skipped
- RULE-15: A section is current when its stored `spec`, `code` and `tests` hashes all equal a fingerprint taken now; otherwise it is out of date and the reader names each part that differs
- RULE-16: The audit entry for a rule is returned only while its `rule_hash`, `proof_hash` and `test_hash` all equal the ones asked for, whatever its `commit`
- RULE-17: The newest section is the one with the latest `at` across both sources, `local` winning a tie, and there is none when neither file holds a section
- RULE-18: Reading evidence writes nothing: the evidence folder holds the same files with the same bytes after a load as before it
- RULE-19: A person reads each operating system as `Windows`, `macOS` or `Linux/Unix`, and in a small box as `Win`, `Mac` or `Lin`; a stored word other than `windows`, `macos` and `linux` reads as `Linux/Unix` and `Lin`
- RULE-20: A section's result for a proof is the worst of the entries it lists against that proof: `fail` where one failed, else `not run` where one reads `missing` or `not run`, else `pass`, so a proof has passed only when every test tied to it ran and passed
- RULE-21: A fingerprint is taken from the working tree, so an edit that is not committed changes it
- RULE-22: Editing `> Description:` changes no part of the fingerprint
- RULE-24: A `> Scope:` entry naming a directory reaches every tracked file under it
- RULE-25: A `> Scope:` entry holding `*`, `?` or `[` is a glob
- RULE-26: A test file under a folder whose name begins with `.` or is `node_modules`, `bin`, `obj` or `mutants` is not counted in the `tests` part
- RULE-27: The machine the reader runs on is `windows` on Windows, `macos` on macOS, and `linux` on any other system
- RULE-28: Where both sources hold a matching audit entry, the later `at` wins, and the entry names its source
- RULE-29: A run with no feature named selects a feature that has no section for this machine's operating system in either source, with the reason `no run on <System> yet`, the system written as a person reads it
- RULE-30: An anchor's `code` part covers every file git tracks but the records Purlin writes, so an edit to any other tracked file changes it and an untracked file does not
- RULE-31: Writing Purlin's records, the evidence under `.purlin/evidence/`, the evidence package, `.purlin/tests.md` and a signature under a `*.signatures/` folder, leaves an anchor's `code` part as it was
- RULE-32: An anchor's `code` part is taken the same on Windows, where git writes each text file out with CRLF, as the blob ids the commit holds
- RULE-33: A run with no feature named selects an anchor after an edit to any tracked file outside Purlin's records, with the reason `code changed since <sha7>`

## Proof

- PROOF-1 (RULE-1): In a git repository where `login` covers the committed file `src/login.py`, the fingerprint of `login` carries exactly the three parts `code`, `spec` and `tests`, each 64 lowercase hex characters
- PROOF-71 (RULE-1): On Windows, with `core.autocrlf` set to `true`, `login` covers the committed file `src/login.py`; its fingerprint carries the three parts `code`, `spec` and `tests`, and `code` equals the one taken of the same commit with `core.autocrlf` set to `false` @env(windows)
- PROOF-32 (RULE-21): `login` covers the committed file `src/login.py`, which is then edited and not committed; the fingerprint of `login` taken after the edit differs from the one taken before in `code` and in no other part
- PROOF-2 (RULE-2): The rule `Valid credentials return 200` of `login` is reworded to `Valid credentials return 201`; the fingerprint of `login` differs from the one taken before in `spec` alone
- PROOF-33 (RULE-22): The `> Description:` of `login` is rewritten from `What it does.` to `Something else entirely.`; all three parts of the fingerprint of `login` equal the ones taken before
- PROOF-3 (RULE-2): The anchor `api` stands beside the feature `login`, and `api` RULE-1 is reworded from `Carry a request id` to `Carry a trace id`; all three parts of the fingerprint of `login` are as they were
- PROOF-34 (RULE-2): `@manual` is added to the end of the one proof line of `login`; the fingerprint of `login` differs from the one taken before in `spec` alone
- PROOF-6 (RULE-4): `login` covers `src/login.py`, and that file is edited; the fingerprint of `login` differs from the one taken before in `code` alone
- PROOF-36 (RULE-4): `login` covers `src/login.py`, and `src/other.py`, a tracked file outside the scope, is edited; all three parts of the fingerprint of `login` are as they were
- PROOF-7 (RULE-24): `login` covers the folder `src`, which holds the tracked file `src/deep/token.py` one folder down; editing `src/deep/token.py` changes the fingerprint in `code` alone
- PROOF-72 (RULE-24): On Windows, `login` covers the folder `src`, which holds the tracked file `src/deep/token.py` one folder down; editing that file changes the fingerprint in `code` alone @env(windows)
- PROOF-8 (RULE-25): `login` covers the glob `src/**/*.py`, and the tracked file `src/deep/token.py`, one folder down, is edited; the fingerprint of `login` differs from the one taken before in `code` alone
- PROOF-37 (RULE-25): `login` covers the glob `src/**/*.py`, and the tracked file `src/login.py`, directly in `src`, is edited; the fingerprint of `login` differs from the one taken before in `code` alone
- PROOF-38 (RULE-25): `login` covers the glob `src/**/*.py`, and the tracked file `src/notes.txt` is edited; the fingerprint of `login` is the same as before
- PROOF-39 (RULE-25): `login` covers `src/logi?.py`, and the tracked file `src/login.py` is edited; the fingerprint of `login` differs from the one taken before in `code` alone, so the entry was read as a glob
- PROOF-40 (RULE-25): `login` covers `src/[l]ogin.py`, and the tracked file `src/login.py` is edited; the fingerprint of `login` differs from the one taken before in `code` alone, so the entry was read as a glob
- PROOF-9 (RULE-5): In a project where `src/gone.py` does not exist and no `.rs` file is tracked, the scope entries `src/login.py`, `src/gone.py` and `lib/*.rs` reach exactly `src/login.py`, and the entries listed as unmatched are exactly `src/gone.py` then `lib/*.rs`
- PROOF-41 (RULE-5): The `> Scope:` of `login` names `src/login.py`, `src/gone.py`, which does not exist, and `lib/*.rs`, which matches no tracked file; its fingerprint is taken with no error, its `code` part equals that of a `login` whose scope names `src/login.py` alone, and `login` is not reported incomplete
- PROOF-42 (RULE-5): `src/draft.py` is written and not added to git, and the `> Scope:` line of `login` names `src/login.py` and `src/draft.py`; the entries read from that line reach exactly `src/login.py`, and the one listed as unmatched is `src/draft.py`
- PROOF-10 (RULE-6): `login` has no `> Scope:` line; it is reported incomplete with the reason `no > Scope: line`, and its fingerprint is taken with no error: `code` is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, the sha256 of the empty string, and `spec` and `tests` are 64 characters each
- PROOF-11 (RULE-7): The committed file `tests/test_login.py`, named by a suite of the `tests` setting, carries `# purlin: login PROOF-1` above its test; editing it changes the fingerprint of `login` in `tests` alone
- PROOF-43 (RULE-7): The committed file `tests/test_other.py`, named by a suite of the `tests` setting, carries a marker for `billing` and none for `login`; rewriting it leaves the fingerprint of `login` as it was
- PROOF-44 (RULE-7): The committed file `scripts/check_login.py` carries `# purlin: login PROOF-1` above a test, and no suite of the `tests` setting names it; editing it leaves the fingerprint of `login` as it was
- PROOF-12 (RULE-7): The committed JavaScript file `web/login.test.js`, named by a suite's glob `**/*.test.js`, carries `// purlin: login PROOF-2` above its test; editing it changes the fingerprint of `login` in `tests` alone
- PROOF-73 (RULE-7): On Windows, the committed file `web/login.test.js`, named by a suite's pattern `**/*.test.js`, carries `// purlin: login PROOF-2` above its test; editing it changes the fingerprint of `login` in `tests` alone @env(windows)
- PROOF-45 (RULE-26): A copy of a JavaScript test carrying `// purlin: login PROOF-2` is committed under `node_modules/pkg/`, named by the suite's glob `**/*.test.js`; editing it leaves the fingerprint of `login` as it was
- PROOF-65 (RULE-26): A copy of a JavaScript test carrying `// purlin: login PROOF-2` is committed under `bin/`, named by the suite's glob `**/*.test.js`; editing it leaves the fingerprint of `login` as it was
- PROOF-66 (RULE-26): A copy of a JavaScript test carrying `// purlin: login PROOF-2` is committed under `obj/`, named by the suite's glob `**/*.test.js`; editing it leaves the fingerprint of `login` as it was
- PROOF-67 (RULE-26): A copy of a JavaScript test carrying `// purlin: login PROOF-2` is committed under `mutants/`, named by the suite's glob `**/*.test.js`; editing it leaves the fingerprint of `login` as it was
- PROOF-68 (RULE-26): A copy of a JavaScript test carrying `// purlin: login PROOF-2` is committed under `.cache/`, named by the suite's glob `**/*.test.js`; editing it leaves the fingerprint of `login` as it was
- PROOF-13 (RULE-8): `login` covers `src` and its marker file is `tests/test_login.py`; `src/new_token.py` and `tests/helper.py` are written and not added to git, and the fingerprint of `login` equals the one taken before
- PROOF-46 (RULE-8): `login` covers `src` and its marker file is `tests/test_login.py`; `src/new_token.py`, `tests/helper.py` and `docs/notes.md` are written and not added to git; the files listed as untracked are exactly `src/new_token.py` and `tests/helper.py`
- PROOF-74 (RULE-8): On Windows, `login` covers `src` and its marker file is `tests/test_login.py`; `src/new_token.py`, `tests/helper.py` and `docs/notes.md` are written and not added to git; the files listed as untracked are exactly `src/new_token.py` and `tests/helper.py` @env(windows)
- PROOF-47 (RULE-8): `login` covers `src`, `.gitignore` lists `src/*.log`, and `src/debug.log` and `src/new_token.py` are written and not added to git; the one file listed as untracked is `src/new_token.py`
- PROOF-14 (RULE-8): `login` covers `src`, and `src/new_token.py` is written and not added to git; once it is added, and not committed, the fingerprint differs from the one taken before it was written in `code` alone, and no file is listed as untracked
- PROOF-15 (RULE-9): In a project whose one spec is `login`, asking for the fingerprint of `nosuch` fails with `KeyError`, and its message names `nosuch`
- PROOF-16 (RULE-10): A stored fingerprint of `spec` `a`, `code` `b` and `tests` `c` is compared with one taken now of `a`, `x` and `y`; the parts named are exactly `code` then `tests`
- PROOF-48 (RULE-10): A stored fingerprint that is missing is compared with one taken now of `a`, `x` and `y`; the parts named are exactly `spec`, `code` and `tests`, in that order
- PROOF-49 (RULE-10): A stored fingerprint that is the text `abc` is compared with one taken now of `a`, `x` and `y`; the parts named are exactly `spec`, `code` and `tests`, in that order
- PROOF-50 (RULE-10): A stored fingerprint of `a`, `x` and `y` is compared with one taken now of `a`, `x` and `y`; no part is named
- PROOF-17 (RULE-11): Only `.purlin/evidence/ci/login.json` is written; loading the evidence of `login` reads the `ci` file, reads no `local` file, gives the paths `.purlin/evidence/local/login.json` and `.purlin/evidence/ci/login.json`, and gives no warning
- PROOF-18 (RULE-12): `.purlin/evidence/local/login.json` holds `{not json`; loading the evidence of `login` reads no `local` file and gives exactly one warning, `.purlin/evidence/local/login.json is not valid JSON; it is ignored. Run purlin:test login to write it again.`
- PROOF-51 (RULE-12): `.purlin/evidence/local/login.json` holds `[1, 2]`; loading the evidence of `login` reads no `local` file and gives exactly one warning, `.purlin/evidence/local/login.json is not a JSON object; it is ignored. Run purlin:test login to write it again.`
- PROOF-52 (RULE-12): `.purlin/evidence/local/login.json` is well formed and its `schema` reads `purlin-evidence/1`; loading the evidence of `login` reads no `local` file and gives exactly one warning, `.purlin/evidence/local/login.json carries the schema "purlin-evidence/1", not purlin-evidence/2; it is ignored. Run purlin:test login to write it again.`
- PROOF-19 (RULE-13): `.purlin/evidence/ci/login.json` is written with its `source` reading `local`; loading the evidence of `login` reads no `ci` file and gives exactly one warning, `.purlin/evidence/ci/login.json names the source "local" but sits in ci/; it is ignored. Run purlin:test --remote to write it again.`
- PROOF-77 (RULE-12): `.purlin/evidence/ci/login.json` holds `{not json`; loading the evidence of `login` reads no `ci` file and gives exactly one warning, `.purlin/evidence/ci/login.json is not valid JSON; it is ignored. Run purlin:test --remote to write it again.`
- PROOF-20 (RULE-14): The `local` file of `login` holds sections under `linux`, `macos` and `solaris`, and the `ci` file one under `windows`; the sections listed are exactly `local` `macos`, `local` `linux` and `ci` `windows`, in that order, and none is listed for `solaris`
- PROOF-25 (RULE-27): On a system that names itself `freebsd14`, the reader gives the machine it runs on as `linux`
- PROOF-53 (RULE-27): On a system that names itself `win32`, the reader gives the machine it runs on as `windows`
- PROOF-54 (RULE-27): On a system that names itself `darwin`, the reader gives the machine it runs on as `macos`
- PROOF-75 (RULE-27): On Windows, with nothing simulated, the reader gives the machine it runs on as `windows` @env(windows)
- PROOF-21 (RULE-15): A `local` `macos` section of `login` stores the fingerprint of `login` taken now; checked against a fingerprint taken again, it reads current, with no part out of date
- PROOF-55 (RULE-15): A `local` `macos` section of `login` stores the fingerprint taken now, and `src/login.py` is then edited; checked against a fingerprint taken again, it reads out of date on exactly `code`
- PROOF-56 (RULE-15): A `local` `macos` section of `login` stores the fingerprint taken now, and then `src/login.py` and the text of RULE-1 are both edited; the section reads out of date on exactly `spec` and `code`
- PROOF-57 (RULE-15): A `local` `macos` section of `login` stores no fingerprint; checked against a fingerprint taken now, it reads out of date on `spec`, `code` and `tests`
- PROOF-22 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p` and `t`, whose commit is not the repository's HEAD; asked for RULE-1 with `r`, `p` and `t`, the reader returns it, naming the source `local` and carrying that commit
- PROOF-58 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p` and `t`; asked for RULE-1 with `r`, `p` and `t2`, the reader returns no entry
- PROOF-59 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p` and `t`; asked for RULE-1 with `r2`, `p` and `t`, the reader returns no entry
- PROOF-60 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p` and `t`; asked for RULE-1 with `r`, `p2` and `t`, the reader returns no entry
- PROOF-61 (RULE-28): The `local` file holds an audit entry for RULE-1 dated `2026-09-01T00:00:00Z`, and the `ci` file one with the same hashes dated `2026-09-02T00:00:00Z` and another commit; the reader returns the `ci` entry, carrying its commit and the path `.purlin/evidence/ci/login.json`
- PROOF-62 (RULE-28): The `local` file holds an audit entry for RULE-1 dated `2026-09-03T00:00:00Z`, and the `ci` file one with the same hashes dated `2026-09-02T00:00:00Z` and another commit; the reader returns the `local` entry, carrying its own commit and the path `.purlin/evidence/local/login.json`
- PROOF-23 (RULE-17): Neither evidence file of `login` exists; the reader gives no newest section
- PROOF-63 (RULE-17): The `local` file of `login` holds a `macos` section dated `2026-09-01T00:00:00Z`, and the `ci` file a `linux` section dated `2026-09-03T00:00:00Z`; the newest section is `ci` `linux`
- PROOF-64 (RULE-17): The `local` file of `login` holds a `macos` section and the `ci` file a `linux` section, both dated `2026-09-01T00:00:00Z`; the newest section is `local` `macos`
- PROOF-24 (RULE-18): The `local` file of `login` holds a section and an audit entry, and the `ci` file holds `{not json`; the evidence is loaded, its sections are checked against a fingerprint taken now, and an audit entry and the newest section are asked for; afterwards `.purlin/evidence/` holds the same files with the same bytes, none added and none removed
- PROOF-26 (RULE-19): The stored word `windows` reads `Windows` in full and `Win` in a small box
- PROOF-69 (RULE-19): The stored word `macos` reads `macOS` in full and `Mac` in a small box
- PROOF-70 (RULE-19): The stored word `linux` reads `Linux/Unix` in full and `Lin` in a small box
- PROOF-27 (RULE-19): The stored word `solaris` reads `Linux/Unix` in full and `Lin` in a small box
- PROOF-28 (RULE-20): A section lists `PROOF-1` twice, `pass` with one test and `missing` with another; the reader gives `PROOF-1` the result `not run`
- PROOF-29 (RULE-20): A section lists `PROOF-1` twice, `missing` with one test and `fail` with another; the reader gives `PROOF-1` the result `fail`
- PROOF-30 (RULE-20): A section lists `PROOF-1` twice, `pass` with each of two tests; the reader gives `PROOF-1` the result `pass`
- PROOF-31 (RULE-20): A section lists `PROOF-1` once, `not run` with no test named; the reader gives `PROOF-1` the result `not run`
- PROOF-76 (RULE-29): In a project whose one feature `login` has no evidence file in either source, a run with no feature named selects `login` with the one reason `no run on <System> yet`, `<System>` the running machine's word: `macOS` on a Mac, `Windows` on Windows, `Linux/Unix` elsewhere
- PROOF-78 (RULE-30): The anchor `security` stands beside `login`, which covers `src/login.py`; `docs/guide.md`, a tracked file no `> Scope:` names, is edited and not committed; the fingerprint of `security` differs from the one taken before in `code` alone
- PROOF-79 (RULE-30): Beside the anchor `security`, `docs/draft.md` is written and not added to git; all three parts of the fingerprint of `security` are as they were
- PROOF-80 (RULE-31): A new evidence file `.purlin/evidence/local/login.json` is written and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-81 (RULE-31): The tracked table `.purlin/tests.md` is rewritten and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-82 (RULE-31): A signature file `specs/_anchors/security.signatures/RULE-1.json` is written and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-83 (RULE-31): An evidence package `.purlin/evidence/package/1.0.0.json` is written and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-84 (RULE-32): In a checkout with `core.autocrlf` set to `true`, whose text files git writes out with CRLF, the anchor `security`'s `code` part equals the sha256 over each tracked file's path and the blob id the commit holds for it, the records aside @env(windows)
- PROOF-85 (RULE-33): The anchor `security` has a section for this machine holding its fingerprint taken at the last commit; `docs/guide.md` is edited; a run with no feature named selects `security` with the one reason `code changed since <sha7>`, `<sha7>` that commit's first 7 characters
