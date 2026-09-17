# Feature: proofs

> Description: What a test run leaves behind, read back. The proof plugins
>   write one file per feature per tier under `.purlin/runtime/proofs/`, which
>   is gitignored, so two runs on two branches never conflict and nothing a
>   plugin writes reaches a commit. This module is the only reader of those
>   files; the record is what says a run happened.
> Scope: scripts/mcp/purlin/proofs.py
> Stack: python/stdlib, json, re

## Rules

- RULE-1: The proof files a test run writes live under `.purlin/runtime/proofs/`, one per feature per tier, named `<feature>.<tier>.json` [risk: high] [origin: eng]
- RULE-2: The tier is the last dotted segment of the file name before `.json`, so a feature stem carrying dots still resolves to one tier [risk: medium] [origin: eng]
- RULE-3: Entries come back grouped by the `feature` field each one carries, and a project whose proof directory does not exist reads as an empty result rather than an error [risk: high] [origin: eng]
- RULE-4: An entry that names no tier of its own takes the tier the file name carries [risk: medium] [origin: eng]
- RULE-5: A file that is not JSON, whose top level is not an object, or whose name does not end `.<tier>.json` is skipped, and every other file in the directory still loads [risk: medium] [origin: eng]
- RULE-6: A proof has one status per run and `fail` wins: a proof some test claiming it failed on is not proved, whatever another test reported [risk: high] [origin: eng]
- RULE-7: The tests backing a proof are named once each, so a file run twice does not report the same test twice [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Read the module's proof directory constant with the separators normalised to `/`; verify it is exactly `.purlin/runtime/proofs`, then write `login.unit.json` there and verify the load returns the entry it holds @integration
- PROOF-2 (RULE-2): Call the file name splitter on `login.unit.json` and verify it returns the stem `login` with the tier `unit`; call it on `purlin.report.data.integration.json` and verify the stem is `purlin.report.data` with the tier `integration`; call it on `notes.txt` and verify it returns none @integration
- PROOF-3 (RULE-3): Call the loader on a project that has never run a test and verify it returns an empty result with no error raised; write one file holding entries for the features `login` and `signup` and verify the result holds both keys with each feature's own entries under it @integration
- PROOF-4 (RULE-4): Write `login.integration.json` holding one entry with no `tier` key of its own; load it and verify the entry comes back with tier `integration`, taken from the file name @integration
- PROOF-5 (RULE-5): Write four files into the proof directory: one holding invalid JSON, one whose top level is the list `[]`, one named `stray.json` with no tier segment, and one valid `login.integration.json`; load them and verify the result holds the `login` key alone with exactly 1 entry under it and that no error was raised @integration
- PROOF-6 (RULE-6): Write two entries for `PROOF-1`, the first `pass` from one test file and the second `fail` from another; read the statuses and verify `PROOF-1` is `fail`, so the failing test decides @integration
- PROOF-7 (RULE-7): Write the same test file and test name twice for `PROOF-1`; ask for the tests backing it and verify the answer is exactly one pair, `tests/test_login.py` with `test_proof_1` @integration
