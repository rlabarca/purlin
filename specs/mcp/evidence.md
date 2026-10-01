# Feature: evidence

> Description: The fingerprint says what a feature's evidence was taken over:
>   its own rule and proof lines, the files its `> Scope:` names, or for an
>   anchor every tracked file but Purlin's records, and the files that carry
>   its proof markers, each read from the working tree. The reader
>   loads a feature's two evidence files, one per source, and says which
>   sections are current against a fingerprint taken now, which parts are out
>   of date, which audit entry answers a rule, which section is the newest,
>   and what a section's result is for each proof. It names the operating
>   system it runs on. The reader never writes.
> Scope: scripts/mcp/purlin/fingerprint.py, scripts/mcp/purlin/evidence.py
> Stack: python/stdlib, hashlib, json, subprocess (list-only)
> Highest-Rule: 35
> Highest-Proof: 85

## Rules

- RULE-1: A fingerprint is three 64-character sha256 hex strings named `spec`, `code` and `tests`
- RULE-2: The `spec` part covers the spec's own rule and proof lines alone: editing a rule's text changes `spec` and no other part, and editing `> Description:` changes no part
- RULE-34: The `code` part covers the tracked files the `> Scope:` entries reach, read from the working tree: an entry naming a file reaches that file, one naming a directory every tracked file under it, and one holding `*`, `?` or `[` is a glob; editing a file reached, committed or not, changes `code` and no other part
- RULE-5: A scope entry that reaches no tracked file, because the path does not exist or the glob matches nothing, is listed as unmatched, and the fingerprint is still taken
- RULE-6: A spec with no `> Scope:` line is reported incomplete with the reason `no > Scope: line`, and its fingerprint is still taken, with a `code` part that is the sha256 of the empty string
- RULE-7: The `tests` part covers every tracked test file, one a suite of the `tests` setting names, carrying a marker for the feature; editing such a file changes `tests` and no other part; a marker for another feature is not counted
- RULE-8: An untracked file changes no part of the fingerprint; an untracked file under the feature's scope or in the directory of one of its marker files is listed as untracked, and a file git ignores is not listed
- RULE-30: An anchor's `code` part covers every file git tracks but the records Purlin writes, so an edit to any other tracked file changes it and an untracked file does not
- RULE-31: Writing Purlin's records, the evidence under `.purlin/evidence/`, the evidence package and its sign-offs, leaves an anchor's `code` part as it was
- RULE-32: An anchor's `code` part is taken the same on Windows, where git writes each text file out with CRLF, as the blob ids the commit holds
- RULE-11: The reader loads `.purlin/evidence/local/<feature>.json` and `.purlin/evidence/ci/<feature>.json`; a source with no file reads as no evidence and adds no warning
- RULE-35: An evidence file that is not valid JSON, is not a JSON object, carries a `schema` other than `purlin-evidence/2`, or whose `source` disagrees with the folder it sits in is ignored with exactly one warning naming its path, what is wrong and the command that writes it again
- RULE-14: Each of the keys `windows`, `macos` and `linux` under `platforms` is one section, so a file holding two operating systems gives two sections; sections are listed `local` first, then in that operating system order, and any other key is skipped
- RULE-15: A section is current when its stored `spec`, `code` and `tests` hashes all equal a fingerprint taken now; otherwise it is out of date and the reader names each part that differs, all three where the section stores no fingerprint
- RULE-16: The audit entry for a rule is returned only while its `rule_hash`, `proof_hash` and `test_hash` all equal the ones asked for, whatever its `commit`
- RULE-17: The newest section is the one with the latest `at` across both sources, and there is none when neither file holds a section
- RULE-18: Reading evidence writes nothing: the evidence folder holds the same files with the same bytes after a load as before it
- RULE-20: A section's result for a proof is the worst of the entries it lists against that proof: `fail` where one failed, else `not run` where one reads `missing` or `not run`, else `pass`, so a proof has passed only when every test tied to it ran and passed
- RULE-27: The machine the reader runs on is `windows` on Windows, `macos` on macOS, and `linux` on any other system

## Proof

- PROOF-1 (RULE-1): In a git repository where `login` covers the committed file `src/login.py`, the fingerprint of `login` carries exactly the three parts `code`, `spec` and `tests`, each 64 lowercase hex characters
- PROOF-71 (RULE-1): On Windows, with `core.autocrlf` set to `true`, `login` covers the committed file `src/login.py`; its fingerprint carries the three parts `code`, `spec` and `tests`, and `code` equals the one taken of the same commit with `core.autocrlf` set to `false` @env(windows)
- PROOF-2 (RULE-2): The rule `Valid credentials return 200` of `login` is reworded to `Valid credentials return 201`; the fingerprint of `login` differs from the one taken before in `spec` alone
- PROOF-33 (RULE-2): The `> Description:` of `login` is rewritten from `What it does.` to `Something else entirely.`; all three parts of the fingerprint of `login` equal the ones taken before
- PROOF-32 (RULE-34): `login` covers the committed file `src/login.py`, which is then edited and not committed; the fingerprint of `login` taken after the edit differs from the one taken before in `code` and in no other part
- PROOF-7 (RULE-34): `login` covers the folder `src`, which holds the tracked file `src/deep/token.py` one folder down; editing `src/deep/token.py` changes the fingerprint in `code` alone
- PROOF-8 (RULE-34): `login` covers the glob `src/**/*.py`, and the tracked file `src/deep/token.py`, one folder down, is edited; the fingerprint of `login` differs from the one taken before in `code` alone
- PROOF-9 (RULE-5): In a project where `src/gone.py` does not exist and no `.rs` file is tracked, the scope entries `src/login.py`, `src/gone.py` and `lib/*.rs` reach exactly `src/login.py`, and the entries listed as unmatched are exactly `src/gone.py` then `lib/*.rs`
- PROOF-41 (RULE-5): The `> Scope:` of `login` names `src/login.py`, `src/gone.py`, which does not exist, and `lib/*.rs`, which matches no tracked file; its fingerprint is taken with no error, its `code` part equals that of a `login` whose scope names `src/login.py` alone, and `login` is not reported incomplete
- PROOF-10 (RULE-6): `login` has no `> Scope:` line; it is reported incomplete with the reason `no > Scope: line`, and its fingerprint is taken with no error: `code` is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`, the sha256 of the empty string, and `spec` and `tests` are 64 characters each
- PROOF-11 (RULE-7): The committed file `tests/test_login.py`, named by a suite of the `tests` setting, carries `# purlin: login PROOF-1` above its test; editing it changes the fingerprint of `login` in `tests` alone
- PROOF-43 (RULE-7): The committed file `tests/test_other.py`, named by a suite of the `tests` setting, carries a marker for `billing` and none for `login`; rewriting it leaves the fingerprint of `login` as it was
- PROOF-13 (RULE-8): `login` covers `src` and its marker file is `tests/test_login.py`; `src/new_token.py` and `tests/helper.py` are written and not added to git, and the fingerprint of `login` equals the one taken before
- PROOF-46 (RULE-8): `login` covers `src` and its marker file is `tests/test_login.py`; `src/new_token.py`, `tests/helper.py` and `docs/notes.md` are written and not added to git; the files listed as untracked are exactly `src/new_token.py` and `tests/helper.py`
- PROOF-47 (RULE-8): `login` covers `src`, `.gitignore` lists `src/*.log`, and `src/debug.log` and `src/new_token.py` are written and not added to git; the one file listed as untracked is `src/new_token.py`
- PROOF-78 (RULE-30): The anchor `security` stands beside `login`, which covers `src/login.py`; `docs/guide.md`, a tracked file no `> Scope:` names, is edited and not committed; the fingerprint of `security` differs from the one taken before in `code` alone
- PROOF-79 (RULE-30): Beside the anchor `security`, `docs/draft.md` is written and not added to git; all three parts of the fingerprint of `security` are as they were
- PROOF-80 (RULE-31): A new evidence file `.purlin/evidence/local/login.json` is written and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-82 (RULE-31): A sign-off file `.purlin/evidence/package/1.0.0.signoffs/jane.json` is written and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-83 (RULE-31): An evidence package `.purlin/evidence/package/1.0.0.json` is written and committed; the fingerprint of the anchor `security` is the same as before
- PROOF-84 (RULE-32): In a checkout with `core.autocrlf` set to `true`, whose text files git writes out with CRLF, the anchor `security`'s `code` part equals the sha256 over each tracked file's path and the blob id the commit holds for it, the records aside @env(windows)
- PROOF-17 (RULE-11): Only `.purlin/evidence/ci/login.json` is written; loading the evidence of `login` reads the `ci` file, reads no `local` file, gives the paths `.purlin/evidence/local/login.json` and `.purlin/evidence/ci/login.json`, and gives no warning
- PROOF-18 (RULE-35): `.purlin/evidence/local/login.json` holds `{not json`; loading the evidence of `login` reads no `local` file and gives exactly one warning, `.purlin/evidence/local/login.json is not valid JSON; it is ignored. Run purlin:test login to write it again.`
- PROOF-52 (RULE-35): `.purlin/evidence/local/login.json` is well formed and its `schema` reads `purlin-evidence/1`; loading the evidence of `login` reads no `local` file and gives exactly one warning, `.purlin/evidence/local/login.json carries the schema "purlin-evidence/1", not purlin-evidence/2; it is ignored. Run purlin:test login to write it again.`
- PROOF-19 (RULE-35): `.purlin/evidence/ci/login.json` is written with its `source` reading `local`; loading the evidence of `login` reads no `ci` file and gives exactly one warning, `.purlin/evidence/ci/login.json names the source "local" but sits in ci/; it is ignored. Run purlin:test --remote to write it again.`
- PROOF-20 (RULE-14): The `local` file of `login` holds sections under `linux`, `macos` and `solaris`, and the `ci` file one under `windows`; the sections listed are exactly `local` `macos`, `local` `linux` and `ci` `windows`, in that order, and none is listed for `solaris`
- PROOF-21 (RULE-15): A `local` `macos` section of `login` stores the fingerprint of `login` taken now; checked against a fingerprint taken again, it reads current, with no part out of date
- PROOF-55 (RULE-15): A `local` `macos` section of `login` stores the fingerprint taken now, and `src/login.py` is then edited; checked against a fingerprint taken again, it reads out of date on exactly `code`
- PROOF-57 (RULE-15): A `local` `macos` section of `login` stores no fingerprint; checked against a fingerprint taken now, it reads out of date on `spec`, `code` and `tests`
- PROOF-22 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p` and `t`, whose commit is not the repository's HEAD; asked for RULE-1 with `r`, `p` and `t`, the reader returns it, naming the source `local` and carrying that commit
- PROOF-58 (RULE-16): The `local` file holds an audit entry for RULE-1 with the hashes `r`, `p` and `t`; asked for RULE-1 with `r`, `p` and `t2`, the reader returns no entry
- PROOF-63 (RULE-17): The `local` file of `login` holds a `macos` section dated `2026-09-01T00:00:00Z`, and the `ci` file a `linux` section dated `2026-09-03T00:00:00Z`; the newest section is `ci` `linux`
- PROOF-23 (RULE-17): Neither evidence file of `login` exists; the reader gives no newest section
- PROOF-24 (RULE-18): The `local` file of `login` holds a section and an audit entry, and the `ci` file holds `{not json`; the evidence is loaded, its sections are checked against a fingerprint taken now, and an audit entry and the newest section are asked for; afterwards `.purlin/evidence/` holds the same files with the same bytes, none added and none removed
- PROOF-28 (RULE-20): A section lists `PROOF-1` twice, `pass` with one test and `missing` with another; the reader gives `PROOF-1` the result `not run`
- PROOF-29 (RULE-20): A section lists `PROOF-1` twice, `missing` with one test and `fail` with another; the reader gives `PROOF-1` the result `fail`
- PROOF-25 (RULE-27): On a system that names itself `freebsd14`, the reader gives the machine it runs on as `linux`
- PROOF-75 (RULE-27): On Windows, with nothing simulated, the reader gives the machine it runs on as `windows` @env(windows)
