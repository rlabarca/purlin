# Feature: states

> Description: The seven states of a rule, the flags beside them, the rollups
>   over them, the structured payload every surface reads, and the status
>   table a person reads. One reader assembles specs, runtime proofs, records
>   and approvals into the state of every rule; the table, the dashboard, the
>   gate and the drift report all render that one payload rather than parsing
>   each other's output.
> Scope: scripts/mcp/purlin/states.py, scripts/mcp/purlin/payload.py, scripts/mcp/purlin/status.py
> Stack: python/stdlib, json, hashlib, subprocess (list-only)

## Rules

- RULE-1: A rule with no proof at all is Drafted [risk: high] [origin: eng]
- RULE-2: A rule whose proof text raises a blocking free check is Drafted; a rule whose proofs raise none is Proof ready [risk: high] [origin: eng]
- RULE-3: A rule is Tested when every one of its proofs passed in the last local test run; one failing entry holds it back [risk: high] [origin: eng]
- RULE-4: A rule is Recorded when a record that counts under the gate passes every one of its proofs and describes the current commit, either by naming it or by carrying the scope tree the working tree still hashes to [risk: high] [origin: eng]
- RULE-5: Under the gates `recorded` and `approved` only a record labelled `ci` counts; a record a developer committed does not [risk: high] [origin: eng]
- RULE-6: A proof carrying `@env` is proved only by a record from that operating system: the rule stays out of Recorded, names the operating system under `missing_env`, and gives the reason `<os>: no record yet` rather than taking an eighth state [risk: high] [origin: eng]
- RULE-7: A rule is Reviewed when a brief exists for its current rule, proof and test hashes together; a brief written for other text is no brief at all [risk: medium] [origin: eng]
- RULE-8: A rule is Approved when a current approval meets a record that passes [risk: high] [origin: eng]
- RULE-9: A rule that carries approvals none of which is current is Stale, whatever else its evidence shows [risk: high] [origin: eng]
- RULE-10: When a passing record and a current approval exist and the record describes neither the head commit nor the current scope tree, the rule stays Approved and raises `re_verify_pending`: only the code moved, so the approval stands until CI runs again [risk: high] [origin: eng]
- RULE-11: A rule is auto-approvable only at risk `low` with a passing record whose test strength is at or above the project minimum; where no break engine measured a strength the free checks stand in for it, and `high` and `medium` are never auto-approvable [risk: high] [origin: eng]
- RULE-12: A rule needs a model to read it first when its risk is at or above the project's review threshold, when an approval has gone stale, or when the test strength is under the minimum; with no break engine available the threshold drops one level, so more rules get a look rather than fewer [risk: medium] [origin: eng]
- RULE-13: The state order is the seven states with Stale first and Approved last, so the feature holding a stale approval sorts to the top of the table [risk: medium] [origin: eng]
- RULE-14: A feature's rollup carries how many rules it has, the count in each state that is not zero, the lowest state any rule reached, and the stale, re-verify and review counts [risk: medium] [origin: eng]
- RULE-15: The project rollup counts each rule once, under the feature that owns it, so a global anchor's rule is counted once however many features have to prove it [risk: high] [origin: eng]
- RULE-16: The payload carries schema version 4 and the top-level keys `generated_at`, `generated_by`, `project`, `version`, `commit`, `dirty`, `gate`, `states`, `features`, `review_list`, `records` and `warnings` [risk: high] [origin: eng]
- RULE-17: A feature entry carries its spec path and category, and each of its rules with the risk, the origin and the criterion the spec tagged, and each proof with its tier and its operating system [risk: medium] [origin: eng]
- RULE-18: The review list names the feature, the rule, the rule's risk and why it is on the list [risk: medium] [origin: eng]
- RULE-19: The dashboard's data file is written as `const PURLIN_DATA = ` followed by the payload and a trailing semicolon, and reads back as the payload that was written [risk: medium] [origin: eng]
- RULE-20: A rebuild whose payload differs from the file on disk only by the stamp on it touches that file instead of rewriting it, so a background refresh never churns the bytes [risk: medium] [origin: eng]
- RULE-21: The status table is one row per feature under the columns Feature, Rules, Lowest state, States, Strength, Record, Approvals and Re-verify, and a feature with no record shows its strength as `n/a` [risk: medium] [origin: eng]
- RULE-22: The report ends with exactly one `Next:` line, computed from the state rather than from what the caller asked for [risk: medium] [origin: eng]
- RULE-23: A project with no specs under `specs/` says what to run instead of printing an empty table [risk: low] [origin: eng]
- RULE-24: The report carries no emoji: the only characters above U+2000 it prints are the arrow, the two triangles and the horizontal rule the design system allows [risk: medium] [origin: eng]
- RULE-25: A config carrying a key this release no longer reads prints the line `Run: purlin:init --update` above the next step [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Write a spec whose `## Proof` section is empty and call the payload builder; verify RULE-1 comes back in state `Drafted` @integration
- PROOF-2 (RULE-2): Write the proof text `Call login and verify it works correctly` and verify the rule is `Drafted` with the finding `vague_verb` on its proof; then write a proof naming a trigger and the value `401` and verify the rule is `Proof ready` @integration
- PROOF-3 (RULE-3): Write one passing runtime proof entry for `PROOF-2` and verify RULE-2 is `Tested`; rewrite the same entry with status `fail` and verify the rule falls back to `Proof ready` @integration
- PROOF-4 (RULE-4): Write and commit a record whose runner is `ci` in which `PROOF-2` passes at the head commit; verify RULE-2 is `Recorded` @integration
- PROOF-5 (RULE-5): Set the gate to `recorded`, commit a record whose runner is a developer in which `PROOF-2` passes, and verify RULE-2 is not `Recorded` @integration
- PROOF-6 (RULE-6): Write a proof carrying `@env(windows)` and commit a passing record from `linux`; verify the rule is not `Recorded`, that `missing_env` is exactly `["windows"]` and that the reasons carry `windows: no record yet`; then commit a passing record from `windows` and verify the rule is `Recorded` @integration
- PROOF-7 (RULE-7): Build the rule state with a brief whose triple hash equals the rule's own; verify the state is `Reviewed`. Repeat with a brief whose triple hash is 64 `f` characters and verify the state falls back to `Proof ready` @integration
- PROOF-8 (RULE-8): Commit a passing record and write an approval binding the rule's current hashes; verify the rule is `Approved` @integration
- PROOF-9 (RULE-9): With that approval in place, write the rule text afresh, changing it from `return 200 with a session token` to `return 201 with a session token`; verify the rule is `Stale` @integration
- PROOF-10 (RULE-10): Write and commit a record carrying the current scope tree and an approval, and verify `re_verify_pending` is false; rewrite the scoped source file, commit it, and verify the rule is still `Approved` with `re_verify_pending` true @integration
- PROOF-11 (RULE-11): Write and commit a record whose test strength is 90 and verify the low-risk RULE-2 is auto-approvable; verify the high-risk RULE-1 of the same feature is not @integration
- PROOF-12 (RULE-12): At gate `recorded`, build the rule state for a high-risk rule and verify it needs a review, and for a low-risk rule and verify it does not; set a medium-risk rule with no break engine available and verify it needs one; set a low-risk rule whose test strength is 10 and verify it needs one; and build one carrying an approval that no longer binds the current text and verify it needs one
- PROOF-13 (RULE-13): Read the state order and verify its first entry is `Stale`, its last is `Approved` and its length is exactly 7; ask for the lowest of `Approved` and `Tested` and verify the answer is `Tested`
- PROOF-14 (RULE-14): Write one passing entry for `PROOF-2` of a two-rule feature and build the payload; verify the feature's rollup reads 2 rules, counts `{"Proof ready": 1, "Tested": 1}` and names `Proof ready` as the lowest state @integration
- PROOF-15 (RULE-15): Add a global anchor with one rule to a project whose one feature has two own rules; build the payload and verify the project rollup counts exactly 3 rules while the feature's own rollup counts 3, so the anchor's rule is counted once and proved by the feature @integration
- PROOF-16 (RULE-16): Build the payload and verify `schema_version` is exactly 4, that all twelve named top-level keys are present, that `gate.gate` reads `tested` and that `generated_at` ends in `Z` @integration
- PROOF-17 (RULE-17): Build the payload for a feature whose RULE-1 is tagged high risk, origin pm and criterion US-12; verify the feature entry names the spec path `specs/auth/login.md` and the category `auth`, that the rule carries those three tag values, and that its proof reads tier `integration` with no operating system @integration
- PROOF-18 (RULE-18): Build the payload at gate `recorded` for a feature holding one high-risk rule; verify the review list is exactly one entry naming that rule with risk `high` and a reason carrying `risk high` @integration
- PROOF-19 (RULE-19): Write the data file and read the bytes back; verify the text starts `const PURLIN_DATA = ` and ends `;` followed by a newline, and that reading the payload back returns the same commit sha the payload was built with @integration
- PROOF-20 (RULE-20): Write the data file, set its modification time to zero, then write the same payload again asking for a write only if it changed; verify the bytes on disk are unchanged and the modification time is no longer zero @integration
- PROOF-21 (RULE-21): Run the status report over a project with one feature and read the header line; verify it names Rules, Lowest state, States, Strength, Record, Approvals and Re-verify, that the feature's row carries `Proof ready` and `Tested 1`, and that its strength reads `n/a` because no record exists @integration
- PROOF-22 (RULE-21): Run the status report over this repository's own specs; verify the output carries the `Lowest state` column, names at least one of the seven states, and that its last line opens with the arrow @integration
- PROOF-23 (RULE-22): Run the status report and count the lines opening with the arrow and `Next:`; verify there is exactly 1, and that on a project whose rules are all Proof ready it names `purlin:build` @integration
- PROOF-24 (RULE-23): Run the status report on a project with no spec files; verify the text carries `No specs found` and names `purlin:init` @integration
- PROOF-25 (RULE-24): Run the status report and read every character of it; verify each one is below U+2000 or is one of the four glyphs the design system allows, so no emoji reaches a terminal @integration
- PROOF-26 (RULE-25): Set a config key this release no longer reads and run the status report; verify the output carries the line `Run: purlin:init --update` @integration
- PROOF-27 (RULE-11): Write and commit a record whose test strength was never measured and verify the low-risk RULE-2 is auto-approvable; then write the proof text `Check that the login handles it properly` and verify the finding `vague_verb` fires and the rule is no longer auto-approvable @integration
