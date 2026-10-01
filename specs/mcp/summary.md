# Feature: summary

> Description: The lines the status opens and ends on in the terminal. It opens on the project,
>   then the two facts: whether every rule passes its tests on the committed evidence, and
>   whether this code is signed. It ends on one sentence and one list. The sentence counts the
>   rules and how many pass their tests, and gives the share of rules the audit found strong
>   where it read any. `Left to do` names each kind of work left, with its count and the command
>   that clears it, in the order the work is done. A last line names `purlin:sign` when the tests
>   are met and this code is not signed. The status table, a test run, an audit and the evidence
>   package read these words from the payload and write none of their own.
> Scope: scripts/mcp/purlin/summary.py, scripts/mcp/purlin/facts.py, scripts/mcp/purlin/status.py
> Stack: python/stdlib
> Highest-Rule: 21
> Highest-Proof: 54

## Rules

- RULE-1: The sentence opens `<N> rules. <p> pass their tests.`
- RULE-12: Each rule is counted once in the sentence, under the spec that owns it, anchors' included
- RULE-2: A count of one reads singular in the sentence: `1 rule.` and `1 passes its tests.`
- RULE-13: A line of `Left to do` counting one rule reads `1 rule <words>: <command>`
- RULE-3: A count of zero reads plural: `0 pass their tests.`
- RULE-4: While work is left, the sentence is followed by `Left to do:` and one line per kind of work, indented two spaces, reading `<count> <words>: <command>`; the kinds, their words for any count but one, and their commands are `specs to repair`, `purlin:spec`; `rules to write a proof for`, `purlin:spec`; `test comments to correct`, `1 test comment to correct` for one, `purlin:build`; `rules to fix`, `purlin:build`; `rules to write a test for`, `purlin:build`; `rules to test`, `purlin:test`; `rules to test on <systems>`, `purlin:test --remote`; `features whose results are not committed`, `1 feature whose results are not committed` for one, `purlin:test --commit`; and `rules to strengthen`, `purlin:build`. `test comments to correct` counts the comments above tests that name something no spec has, a rule that has proofs, or a proof whose wording changed after the test was last changed
- RULE-5: The lines of `Left to do` follow the order of the kinds in RULE-4, whatever order the rules come in
- RULE-6: A kind no rule is counted under has no line
- RULE-7: Where nothing is left there is no `Left to do:` line, and the sentence is followed only by the last line RULE-18 names, where it applies
- RULE-8: Each rule is counted under at most one kind, the first that applies in this order: a passed cell reading `failed` or `partial` (`to fix`); `no test` (`to write a test for`); `out of date`, or `not run` where this machine's system is among those it waits for or it names none (`to test`); `not run` for other systems only (`to test on`); no proof line, its tests passing (`to write a proof for`); a strong cell reading `weak` (`to strengthen`); a hand check and a rule no audit has read add no kind
- RULE-9: `pass their tests` counts the rules whose passed cell reads `passed`, a rule whose every proof is `@manual` included
- RULE-10: The `to test on` line names the systems its rules wait for in the words `Linux/Unix`, `macOS` and `Windows`, in that order, joined by ` and `
- RULE-14: This machine's own system is never among those the `to test on` line names, since a rule that waits for it is counted `to test`, so the line names one system or two
- RULE-16: The kind `to_repair` is the first line of `Left to do` and counts specs, not rules: those that write a rule or proof number twice or hold a line left from a merge conflict, reading `1 spec to repair: purlin:spec` for one and `<n> specs to repair: purlin:spec` for any other count
- RULE-17: The sentence adds ` The audit found <s> of <n> rules strong (<p>%).` where the audit found at least one rule that passes its tests strong or weak; `<n>` counts the rules that pass their tests, a rule with a hand check among them only where it also has a tested proof
- RULE-18: Where the tests are `met` and the sign-off does not read `signed <version> at <sha7>`, the last line, after the table and `Left to do`, reads `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`; otherwise there is no last line
- RULE-19: The kinds `no_proof` and `to_strengthen` are not blocking and every other kind is, so a rule with no proof line, or one the audit found weak, still lets the tests read `met`
- RULE-20: The status opens on three lines: `Purlin status: <project>, plugin <version>`; `Tests: met` where no line of `Left to do` is of a blocking kind, else `Tests: not met`; and `Sign-off: ` followed by, for the newest `signed/*` tag on HEAD or an ancestor of it, `signed <version> at <sha7>` where every commit since changes only `.purlin/`, else `signed <version>, <n> commits since` (`1 commit since` for one), or `not signed` where there is none
- RULE-21: A feature whose results are written and not committed is counted once under `to_commit`, a blocking kind, reading `1 feature whose results are not committed: purlin:test --commit` for one and `<n> features whose results are not committed: purlin:test --commit` for any other count

## Proof

- PROOF-2 (RULE-1): A project of 3 rules of which 2 pass their tests and none is audited reads exactly `3 rules. 2 pass their tests.`
- PROOF-4 (RULE-12): An anchor's one passing rule beside two features of one passing rule each reads `3 rules. 3 pass their tests.`
- PROOF-5 (RULE-2): A project of one rule that passes its tests reads `1 rule. 1 passes its tests.`
- PROOF-6 (RULE-13): One rule whose test fails gives the one line `1 rule to fix: purlin:build` under `Left to do:`
- PROOF-7 (RULE-3): A project of two rules whose tests both fail reads `2 rules. 0 pass their tests.`
- PROOF-8 (RULE-4): On macOS, over committed evidence, two rules of each of the six kinds of rule work end on `Left to do:` and six lines in RULE-4's order, each reading `  2 rules <words>: <command>`, the fifth `  2 rules to test on Windows: purlin:test --remote`
- PROOF-10 (RULE-5): A rule the audit found weak listed before a rule whose test fails gives `1 rule to fix: purlin:build` on the line above `1 rule to strengthen: purlin:build`
- PROOF-35 (RULE-5): One test comment to correct beside a rule whose test fails gives `1 test comment to correct: purlin:build` on the line above `1 rule to fix: purlin:build`
- PROOF-11 (RULE-6): Three rules the audit found weak, over committed evidence, give exactly one line under `Left to do:`, `3 rules to strengthen: purlin:build`
- PROOF-12 (RULE-7): Two rules that pass their tests on committed evidence, with `signed/0.1.0` on HEAD, end on the sentence `2 rules. 2 pass their tests.` as the last line, with no `Left to do:` line after it
- PROOF-15 (RULE-8): A rule with no proof line whose own marked test fails is counted as `1 rule to fix` and under no other kind
- PROOF-16 (RULE-8): A rule whose test fails and that no audit has read is counted as `1 rule to fix` and under no other kind
- PROOF-17 (RULE-8): A rule with neither a proof line nor a test is counted as `1 rule to write a test for`, and no line names a proof
- PROOF-18 (RULE-8): A rule whose passed cell reads `out of date` is counted as `1 rule to test: purlin:test`
- PROOF-23 (RULE-8): On macOS, a rule waiting on `macos` and `windows` is counted as `1 rule to test: purlin:test`, since this machine can run part of it
- PROOF-33 (RULE-8): On macOS, a rule whose `PROOF-1` passes here and whose `PROOF-2`, tagged `@env(windows)`, had its test skipped here ends the status on `  1 rule to test on Windows: purlin:test --remote`
- PROOF-34 (RULE-8): A rule whose `PROOF-1` passes in a current section and whose `PROOF-2` no test backs ends the status on `  1 rule to write a test for: purlin:build`
- PROOF-37 (RULE-8): A current section passes `PROOF-1`'s test and lists `PROOF-2`, of the same rule, as `missing` with no test named, and no marker names `PROOF-2`; the status ends on `  1 rule to write a test for: purlin:build`
- PROOF-20 (RULE-9): A rule whose one proof is `@manual`, over committed evidence, reads `1 rule. 1 passes its tests.` and has no line under `Left to do`
- PROOF-22 (RULE-10): On macOS, one rule waiting only on `windows` and one waiting only on `linux` give the one line `2 rules to test on Linux/Unix and Windows: purlin:test --remote`
- PROOF-28 (RULE-14): On macOS, one rule waiting only on `macos` and one waiting only on `windows` give `1 rule to test: purlin:test` and `1 rule to test on Windows: purlin:test --remote`, and no line names macOS
- PROOF-29 (RULE-4): A test comment naming `login PROOF-9`, which no spec has, beside two rules that pass their tests on committed evidence, ends on `Left to do:` and the one line `  1 test comment to correct: purlin:build`
- PROOF-36 (RULE-4): Three test comments naming `login PROOF-7`, `login PROOF-8` and `login PROOF-9`, which no spec has, beside two rules that pass their tests on committed evidence, end the status on `Left to do:` and the one line `  3 test comments to correct: purlin:build`
- PROOF-40 (RULE-16): A broken spec of three failing rules beside another spec of one failing rule ends on `Left to do:`, `  1 spec to repair: purlin:spec` and `  1 rule to fix: purlin:build`, in that order
- PROOF-41 (RULE-16): Two broken specs end on `Left to do:` and the one line `  2 specs to repair: purlin:spec`
- PROOF-42 (RULE-17): 40 rules of which 35 pass their tests and no audit has read any read exactly `40 rules. 35 pass their tests.`
- PROOF-43 (RULE-17): 50 rules that all pass their tests, 42 found strong and 8 found weak by the audit, read `50 rules. 50 pass their tests. The audit found 42 of 50 rules strong (84%).`
- PROOF-44 (RULE-18): Two rules that pass their tests on committed evidence, with no `signed/*` tag, end on `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`
- PROOF-47 (RULE-19): A rule that passes its tests on committed evidence and that the audit found weak has the `left` `to_strengthen`, and the status opens `Tests: met`
- PROOF-54 (RULE-19): A rule with no proof line whose own marked test passes on committed evidence is counted as `1 rule to write a proof for: purlin:spec`, and the status opens `Tests: met`
- PROOF-48 (RULE-20): In a project whose `pyproject.toml` names `labconnect`, two rules that pass their tests on committed evidence open the status on `Purlin status: labconnect, plugin <version>`, then `Tests: met`
- PROOF-53 (RULE-20): One rule whose test fails makes the status's second line read `Tests: not met`
- PROOF-49 (RULE-20): With `signed/0.1.0` written on HEAD, the status's third line reads `Sign-off: signed 0.1.0 at <sha7>`, the tagged commit
- PROOF-50 (RULE-20): With `signed/0.1.0` written and then one commit changing `src/age.py` made after it, the status's third line reads `Sign-off: signed 0.1.0, 1 commit since`
- PROOF-51 (RULE-20): A project with no `signed/*` tag opens with the third line `Sign-off: not signed`
- PROOF-52 (RULE-21): Two features whose rules pass their tests in local results written and not committed end on `  2 features whose results are not committed: purlin:test --commit`, and the status opens `Tests: not met`
