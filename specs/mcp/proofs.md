# Feature: proofs

> Description: What a test run leaves behind, read back. The proof plugins
>   write one file per feature under `.purlin/runtime/proofs/`, which
>   is gitignored, so two runs on two branches never conflict and nothing a
>   plugin writes reaches a commit. This module is the only reader of those
>   files; the record is what says a run happened.
> Scope: scripts/mcp/purlin/proofs.py
> Stack: python/stdlib, json, re

## Rules

- RULE-1: The proof files a test run writes live under `.purlin/runtime/proofs/`, one per feature, named `<feature>.json` [bar: strong]
- RULE-3: Entries come back grouped by the `feature` field each one carries, and a project whose proof directory does not exist reads as an empty result rather than an error [bar: strong]
- RULE-5: A file that is not JSON, whose top level is not an object, or whose name does not end `.json` is skipped, and every other file in the directory still loads [bar: strong]
- RULE-6: A proof has one status per run and `fail` wins: a proof some test claiming it failed on is not proved, whatever another test reported [bar: strong]
- RULE-7: The tests backing a proof are named once each, so a file run twice does not report the same test twice [bar: passed]

## Proof

- PROOF-1 (RULE-1): Read the module's proof directory constant with the separators normalised to `/`; verify it is exactly `.purlin/runtime/proofs`, then write `login.json` there and verify the load returns the entry it holds
- PROOF-3 (RULE-3): Call the loader on a project that has never run a test and verify it returns an empty result with no error raised; write one file holding entries for the features `login` and `signup` and verify the result holds both keys with each feature's own entries under it
- PROOF-5 (RULE-5): Write four files into the proof directory: one holding invalid JSON, one whose top level is the list `[]`, one named `notes.txt` holding a valid proof document, and one valid `login.json`; load them and verify the result holds the `login` key alone with exactly 1 entry under it and that no error was raised
- PROOF-6 (RULE-6): Write two entries for `PROOF-1`, the first `pass` from one test file and the second `fail` from another; read the statuses and verify `PROOF-1` is `fail`, so the failing test decides
- PROOF-7 (RULE-7): Write the same test file and test name twice for `PROOF-1`; ask for the tests backing it and verify the answer is exactly one pair, `tests/test_login.py` with `test_proof_1`
