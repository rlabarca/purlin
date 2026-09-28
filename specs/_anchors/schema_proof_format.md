# Anchor: schema_proof_format

> Description: The proof file at Format-Version 10: where a proof plugin writes what it
>   observed, the six fields an entry carries, the two statuses, how a rule's passed
>   cell reads it, and why nothing a plugin writes is ever committed. A proof file is
>   runtime; the record is the evidence.
> Type: schema
> Scope: scripts/mcp/purlin/proofs.py, references/formats/proofs_format.md, .gitignore
> Stack: python/stdlib, JSON files under .purlin/runtime/proofs/

## Rules

- RULE-1: A proof file lives at `.purlin/runtime/proofs/<feature>.json`, and a passing entry there is what makes a rule's passed cell read `passed` under the gate `passed`; a rule whose proof has no entry reads `no test` [bar: strong]
- RULE-2: An entry carries the six fields `feature`, `id`, `rule`, `test_file`, `test_name` and `status`, and the file carries a `proofs` array and nothing else; no entry names the runner or the operating system, because a record says where a run happened once per run [bar: strong]
- RULE-3: `status` is `pass` or `fail` and nothing else counts as proved: an entry carrying any other value, or none at all, holds its rule's passed cell short of `passed` while a passing entry beside it still counts for its own rule [bar: strong]
- RULE-4: A proof claimed by two entries is proved only when both passed, so one failing test naming a proof id holds that rule's passed cell back even though another test naming the same id passed [bar: strong]
- RULE-5: A proof directory that does not exist, and one that exists and is empty, both read as no proofs rather than as an error, so a project that has never run its tests still reports [bar: passed]
- RULE-7: `.purlin/runtime/` is gitignored and the proof directory sits under it, so a proof file never reaches a commit, two runs on two branches never conflict, and a test run can never produce a merge conflict [bar: strong]
- RULE-8: The spec format documents the `@manual` tag and the environment tag a proof line may carry, and names the retired scope tag only under its retired heading, so a reader of the format cannot pick up a tag this release refuses [bar: passed]

## Proof

- PROOF-1 (RULE-1): Write a spec holding `RULE-1` and `PROOF-1`, build the payload with an empty proof directory and verify the rule's passed cell reads `no test`; write `.purlin/runtime/proofs/foo.json` holding one passing entry for `PROOF-1`, build the payload again and verify the cell reads `passed`
- PROOF-2 (RULE-2): Write a proof file holding one entry, read it back as JSON, and verify the document's only key is `proofs`, that the entry is missing none of the six required fields, and that it carries neither a `runner` key nor an `os` key
- PROOF-3 (RULE-3): Write a spec holding `RULE-1` and `RULE-2`; for each of the statuses `error`, `fail`, `skipped` and a null status, write a file whose `PROOF-1` entry carries it beside a passing `PROOF-2` entry, and verify `RULE-1`'s passed cell never reads `passed` while `RULE-2`'s reads `passed` every time
- PROOF-4 (RULE-4): Write a spec holding `RULE-1` and `PROOF-1`, then a proof file holding two entries for `PROOF-1` from two different test files, one `pass` and one `fail`; build the payload and verify `RULE-1`'s passed cell does not read `passed`
- PROOF-5 (RULE-5): Call the proof loader on a project with no proof directory and verify it returns an empty result; create the directory empty, call it again and verify the result is still empty
- PROOF-7 (RULE-7): Read `.gitignore` and verify it carries the line `.purlin/runtime/`; verify the proof directory constant the loader uses begins with `.purlin/runtime/`; a gitignore that has stopped carrying the line fails, because a committed proof file is evidence nothing regenerates
- PROOF-8 (RULE-8): Read `references/formats/spec_format.md` and verify it documents each of the two tags a proof line may carry; split the text at its retired-tags heading and verify the retired scope tag has zero matches before it
