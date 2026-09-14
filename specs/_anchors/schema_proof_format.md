# Anchor: schema_proof_format

> Description: The proof file at Format-Version 8: where a proof plugin writes what it
>   observed, the seven fields an entry carries, the two statuses, how a rule reads
>   Tested from it, and why nothing a plugin writes is ever committed. A proof file is
>   runtime; the record is the evidence.
> Type: schema
> Scope: scripts/mcp/purlin/proofs.py, references/formats/proofs_format.md, .gitignore
> Stack: python/stdlib, JSON files under .purlin/runtime/proofs/

## Rules

- RULE-1: A proof file lives at `.purlin/runtime/proofs/<feature>.<tier>.json`, and a passing entry there is what takes a rule from Proof ready to Tested; a rule whose proof has no entry stays at Proof ready [risk: high] [origin: eng]
- RULE-2: An entry carries the seven fields `feature`, `id`, `rule`, `test_file`, `test_name`, `status` and `tier`, and the file carries a top-level `tier` and a `proofs` array; no entry names the runner or the operating system, because a record says where a run happened once per run [risk: medium] [origin: eng]
- RULE-3: `status` is `pass` or `fail` and nothing else counts as proved: an entry carrying any other value, or none at all, leaves its rule short of Tested while a passing entry beside it still counts for its own rule [risk: high] [origin: eng]
- RULE-4: A proof claimed by two entries is proved only when both passed, so one failing test naming a proof id holds that rule back even though another test naming the same id passed [risk: high] [origin: eng]
- RULE-5: A proof directory that does not exist, and one that exists and is empty, both read as no proofs rather than as an error, so a project that has never run its tests still reports [risk: low] [origin: eng]
- RULE-6: A proof file name names the feature and the tier, the tier being the last dotted segment before `.json`, so a feature name carrying dots still parses; a name with no tier segment, and a name that is not a proof file at all, name nothing readable [risk: medium] [origin: eng]
- RULE-7: `.purlin/runtime/` is gitignored and the proof directory sits under it, so a proof file never reaches a commit, two runs on two branches never conflict, and a test run can never produce a merge conflict [risk: high] [origin: eng]
- RULE-8: The spec format documents the tier tags and the environment tag a proof line may carry, and names the retired scope tag only under its retired heading, so a reader of the format cannot pick up a tag this release refuses [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Write a spec holding `RULE-1` and `PROOF-1`, build the payload with an empty proof directory and verify the rule reads `Proof ready`; write `.purlin/runtime/proofs/foo.unit.json` holding one passing entry for `PROOF-1`, build the payload again and verify the rule reads `Tested`
- PROOF-2 (RULE-2): Write a proof file holding one entry, read it back as JSON, and verify the document carries `tier` and `proofs`, that the entry is missing none of the seven required fields, and that it carries neither a `runner` key nor an `os` key
- PROOF-3 (RULE-3): Write a spec holding `RULE-1` and `RULE-2`; for each of the statuses `error`, `fail`, `skipped` and a null status, write a file whose `PROOF-1` entry carries it beside a passing `PROOF-2` entry, and verify `RULE-1` never reads `Tested` while `RULE-2` reads `Tested` every time
- PROOF-4 (RULE-4): Write a spec holding `RULE-1` and `PROOF-1`, then a proof file holding two entries for `PROOF-1` from two different test files, one `pass` and one `fail`; build the payload and verify `RULE-1` does not read `Tested`
- PROOF-5 (RULE-5): Call the proof loader on a project with no proof directory and verify it returns an empty result; create the directory empty, call it again and verify the result is still empty
- PROOF-6 (RULE-6): Call the file-name parser with `login.unit.json` and `login.integration.json` and verify each returns the feature `login` with that tier; call it with `login.md` and with `login.json` and verify each returns none
- PROOF-7 (RULE-7): Read `.gitignore` and verify it carries the line `.purlin/runtime/`; verify the proof directory constant the loader uses begins with `.purlin/runtime/`; a gitignore that has stopped carrying the line fails, because a committed proof file is evidence nothing regenerates
- PROOF-8 (RULE-8): Read `references/formats/spec_format.md` and verify it documents each of the four tags a proof line may carry; split the text at its retired-tags heading and verify the retired scope tag has zero matches before it
