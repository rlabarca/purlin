# Feature: evidence

> Description: The fingerprint says what a feature's evidence was taken over:
>   its rule and proof lines, the files its `> Scope:` names, and the files
>   that carry its proof markers, each read from the working tree. The reader
>   loads a feature's two evidence files, one per source, and says which
>   sections are current against a fingerprint taken now, which parts are out
>   of date, which audit entry answers a rule, and which section is the newest.
>   The reader never writes.
> Scope: scripts/mcp/purlin/fingerprint.py, scripts/mcp/purlin/evidence.py
> Stack: python/stdlib, hashlib, json, subprocess (list-only)

## Rules

- RULE-1: A fingerprint is three 64-character sha256 hex strings named `spec`, `code` and `tests`, taken from the working tree, so an edit that is not committed changes it
- RULE-2: The `spec` part covers the rule and proof lines of the feature, of every spec it requires transitively and of every global anchor; editing a rule's text changes `spec` and no other part, and editing `> Description:` changes no part
- RULE-3: Editing a rule of an anchor changes the `spec` part of every feature that requires the anchor, directly or through another spec, and leaves a feature that does not require it unchanged
- RULE-4: The `code` part covers the tracked files the `> Scope:` entries reach: a file names itself, a directory names every tracked file under it, and an entry holding `*`, `?` or `[` is a glob; editing a file it reaches changes `code` and no other part
- RULE-5: A scope entry that reaches no tracked file, because the path does not exist or the glob matches nothing, is listed as unmatched, and the fingerprint is still taken
- RULE-6: A spec with no `> Scope:` line is reported as naming no files, and its `code` part is the sha256 of the empty string rather than an error
- RULE-7: The `tests` part covers every tracked file carrying a proof marker for the feature; editing such a file changes `tests` and no other part, and a marker for another feature is not counted
- RULE-8: An untracked file changes no part of the fingerprint; an untracked file under the feature's scope or in the directory of one of its marker files is listed as untracked, and a file git ignores is not listed
- RULE-9: Asking for the fingerprint of a name no spec defines raises `KeyError` naming that name
- RULE-10: Comparing a stored fingerprint with one taken now names the parts that differ in the order `spec`, `code`, `tests`; a stored fingerprint that is missing or is not an object differs on all three
- RULE-11: The reader loads `.purlin/evidence/local/<feature>.json` and `.purlin/evidence/ci/<feature>.json`; a source with no file reads as no evidence and adds no warning
- RULE-12: A file that is not valid JSON, is not a JSON object, or whose `schema` is not `purlin-evidence/1` is ignored with one warning naming its path
- RULE-13: A file whose `source` field disagrees with the folder it sits in is ignored with exactly one warning naming its path, the source it names and the folder
- RULE-14: Each of the keys `windows`, `macos` and `linux` under `platforms` is one section, so a file holding two operating systems gives two sections; sections are listed `local` first, then in that operating system order, and any other key is skipped
- RULE-15: A section is current when its stored `spec`, `code` and `tests` hashes all equal a fingerprint taken now; otherwise it is out of date and the reader names each part that differs
- RULE-16: The audit entry for a rule is returned only while its `rule_hash`, `proof_hash` and `test_hash` all equal the ones asked for, whatever its `commit`; where both sources hold a matching entry the later `at` wins, and the entry names its source
- RULE-17: The newest section is the one with the latest `at` across both sources, `local` winning a tie, and there is none when neither file holds a section
- RULE-18: Reading evidence writes nothing: the evidence folder holds the same files with the same bytes after a load as before it

## Proof

- PROOF-1 (RULE-1): Take the fingerprint of `login` in a git repository; verify it has exactly the keys `code`, `spec` and `tests`, each 64 lowercase hex characters; edit `src/login.py` without committing and verify the `code` part changes
- PROOF-2 (RULE-2): Take the fingerprint of `login`; change the text of its RULE-1 and verify only `spec` changes; restore it, rewrite `> Description:` to `Something else entirely.` and verify all three parts equal the first fingerprint
- PROOF-3 (RULE-2): Give `login` `> Requires: api` and take its fingerprint; change the text of the proof line of `api`, and separately add `@manual` to a proof of `login`; verify `spec` changes each time
- PROOF-4 (RULE-3): Write anchor `api`, feature `orders` requiring `api`, feature `login` requiring `orders`, and feature `billing` requiring nothing; edit the text of `api` RULE-1; verify `spec` changes for `api`, `orders` and `login` and stays the same for `billing`
- PROOF-5 (RULE-3): Write a global anchor `security`; edit its RULE-1 text; verify `spec` changes for `login`, which does not name it in `> Requires:`
- PROOF-6 (RULE-4): Scope `login` to `src/login.py`; edit that file and verify only `code` changes; edit `src/other.py`, outside the scope, and verify nothing changes
- PROOF-7 (RULE-4): Scope `login` to the directory `src`, holding the tracked files `src/login.py` and `src/deep/token.py`; edit `src/deep/token.py` and verify `code` changes
- PROOF-8 (RULE-4): Scope `login` to the glob `src/**/*.py` over tracked `src/login.py` and `src/deep/token.py`; verify the glob reaches exactly those two files; edit `src/deep/token.py` and verify `code` changes; edit the tracked `src/notes.txt` and verify it does not
- PROOF-9 (RULE-5): Scope `login` to `src/login.py, src/gone.py, lib/*.rs`, where `src/gone.py` does not exist and no `.rs` file exists; verify the scope report lists exactly `src/gone.py` and `lib/*.rs` as unmatched, that the feature still names `src/login.py`, and that the fingerprint is taken without raising
- PROOF-10 (RULE-6): Write `login` with no `> Scope:` line; verify the scope report says it names no files, its `code` part equals the sha256 of the empty string, and its `spec` and `tests` parts are still 64 characters
- PROOF-11 (RULE-7): Commit `tests/test_login.py` carrying `@pytest.mark.proof("login", "PROOF-1", "RULE-1")` and `tests/test_other.py` carrying a marker for `billing`; verify the marker files of `login` are exactly `tests/test_login.py`; edit it and verify only `tests` changes; edit `tests/test_other.py` and verify the fingerprint of `login` does not change
- PROOF-12 (RULE-7): Commit a jest file `web/login.test.js` carrying `[proof:login:PROOF-2:RULE-2:default]` and a copy of a marked test under `node_modules/`; verify the marker files of `login` include `web/login.test.js` and nothing under `node_modules/`
- PROOF-13 (RULE-8): Scope `login` to `src`; write `src/new_token.py` and `tests/helper.py` without adding them to git; verify the fingerprint equals the one taken before, and that the untracked report lists exactly `src/new_token.py` and `tests/helper.py`; list `src/*.log` in `.gitignore`, write `src/debug.log` and verify it is not listed
- PROOF-14 (RULE-8): Add `src/new_token.py` to git and verify the `code` part changes and the file leaves the untracked report
- PROOF-15 (RULE-9): Take the fingerprint of `nosuch`; verify `KeyError` is raised and its message names `nosuch`
- PROOF-16 (RULE-10): Compare `{spec: a, code: b, tests: c}` with `{spec: a, code: x, tests: y}` and verify the answer is exactly `["code", "tests"]`; compare `None` and the string `abc` with any fingerprint and verify each answer is `["spec", "code", "tests"]`; compare two equal fingerprints and verify the answer is empty
- PROOF-17 (RULE-11): Write only `.purlin/evidence/ci/login.json`; load `login` and verify the `ci` file is read, the `local` file is none, the paths are `.purlin/evidence/local/login.json` and `.purlin/evidence/ci/login.json`, and there are no warnings
- PROOF-18 (RULE-12): Write `local/login.json` holding `{not json`, then holding `[1, 2]`, then holding a valid file whose `schema` is `purlin-evidence/2`; verify each load reads no `local` file and gives exactly one warning naming `.purlin/evidence/local/login.json`
- PROOF-19 (RULE-13): Write `ci/login.json` whose `source` reads `local`; verify the load reads no `ci` file and gives exactly one warning that names `.purlin/evidence/ci/login.json`, `"local"` and `ci/`
- PROOF-20 (RULE-14): Write `local/login.json` with sections for `linux` and `macos` and a key `solaris`, and `ci/login.json` with a `windows` section; verify the sections are exactly `local macos`, `local linux`, `ci windows` in that order
- PROOF-21 (RULE-15): Store the fingerprint taken now in a `macos` section and verify it is current with nothing out of date; edit a scoped file and verify it is out of date on exactly `code`; edit the rule text as well and verify `spec` and `code`; remove the section's fingerprint and verify all three
- PROOF-22 (RULE-16): Store an audit entry for RULE-1 with hashes `r`, `p`, `t` in `local`, at `2026-09-01T00:00:00Z`; ask with `r`, `p`, `t` and verify it comes back naming `local`; ask with `r`, `p`, `t2` and verify none; add a matching entry in `ci` at `2026-09-02T00:00:00Z` with another `commit` and verify the `ci` entry wins
- PROOF-23 (RULE-17): Write a `local` `macos` section at `2026-09-01T00:00:00Z` and a `ci` `linux` section at `2026-09-03T00:00:00Z`; verify the newest is `ci` `linux`; set both to the same time and verify the newest is `local` `macos`; with no files verify the newest is none
- PROOF-24 (RULE-18): Write evidence files for `login` in both folders, one of them malformed; record every path and its bytes under `.purlin/evidence/`; load, list sections, check them, ask for an audit entry and the newest section; verify the paths and bytes are unchanged and no file was added
