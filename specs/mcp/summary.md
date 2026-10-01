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
> Highest-Rule: 23
> Highest-Proof: 54

## Rules

- RULE-20: The status opens on three lines: `Purlin status: <project>, plugin <version>`; `Tests: met` where no line of `Left to do` is of a blocking kind, else `Tests: not met`; and `Sign-off: ` followed by, for the newest `signed/*` tag on HEAD or an ancestor of it, `signed <version> at <sha7>` where every commit since changes only `.purlin/`, else `signed <version>, <n> commits since` (`1 commit since` for one), or `not signed` where there is none
- RULE-22: The sentence reads `<N> rules. <p> pass their tests.`, `1 rule.` and `1 passes its tests.` for a count of one, counting each rule once under the spec that owns it and, under `pass their tests`, each rule whose passed cell reads `passed`; it adds ` The audit found <s> of <n> rules strong (<p>%).` where the audit found at least one rule that passes its tests strong or weak
- RULE-23: While work is left, the sentence is followed by `Left to do:` and one line per kind of work any rule is counted under, indented two spaces, reading `<count> <words>: <command>`, singular for a count of one, in this order whatever order the rules come in: `specs to repair`, `purlin:spec`, counting specs that write a number twice or hold a line left from a merge conflict; `rules to write a proof for`, `purlin:spec`; `test comments to correct`, `purlin:build`, counting comments that name something no spec has, a rule that has proofs, or a proof whose wording changed after the test was last changed; `rules to fix`, `purlin:build`; `rules to write a test for`, `purlin:build`; `rules to test`, `purlin:test`; `rules to test on <systems>`, `purlin:test --remote`; `features whose results are not committed`, `purlin:test --commit`; and `rules to strengthen`, `purlin:build`. Where nothing is left there is no `Left to do:` line
- RULE-8: Each rule is counted under at most one kind, the first that applies in this order: a passed cell reading `failed` or `partial` (`to fix`); `no test` (`to write a test for`); `out of date`, or `not run` where this machine's system is among those it waits for or it names none (`to test`); `not run` for other systems only (`to test on`); no proof line, its tests passing (`to write a proof for`); a strong cell reading `weak` (`to strengthen`); a hand check and a rule no audit has read add no kind
- RULE-19: The kinds `no_proof` and `to_strengthen` are not blocking and every other kind is, so a rule with no proof line, or one the audit found weak, still lets the tests read `met`
- RULE-21: A feature whose results are written and not committed is counted once under `to_commit`, a blocking kind, reading `1 feature whose results are not committed: purlin:test --commit` for one and `<n> features whose results are not committed: purlin:test --commit` for any other count
- RULE-18: Where the tests are `met` and the sign-off does not read `signed <version> at <sha7>`, the last line, after the table and `Left to do`, reads `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`; otherwise there is no last line

## Proof

- PROOF-48 (RULE-20): In a project whose `pyproject.toml` names `labconnect`, two rules that pass their tests on committed evidence open the status on `Purlin status: labconnect, plugin <version>`, then `Tests: met`
- PROOF-53 (RULE-20): One rule whose test fails makes the status's second line read `Tests: not met`
- PROOF-50 (RULE-20): With `signed/0.1.0` written and then one commit changing `src/age.py` made after it, the status's third line reads `Sign-off: signed 0.1.0, 1 commit since`
- PROOF-5 (RULE-22): A project of one rule that passes its tests reads `1 rule. 1 passes its tests.`
- PROOF-4 (RULE-22): An anchor's one passing rule beside two features of one passing rule each reads `3 rules. 3 pass their tests.`
- PROOF-43 (RULE-22): 50 rules that all pass their tests, 42 found strong and 8 found weak by the audit, read `50 rules. 50 pass their tests. The audit found 42 of 50 rules strong (84%).`
- PROOF-8 (RULE-23): On macOS, over committed evidence, two rules of each of the six kinds of rule work end on `Left to do:` and six lines in RULE-23's order, each reading `  2 rules <words>: <command>`, the fifth `  2 rules to test on Windows: purlin:test --remote`
- PROOF-40 (RULE-23): A broken spec of three failing rules beside another spec of one failing rule ends on `Left to do:`, `  1 spec to repair: purlin:spec` and `  1 rule to fix: purlin:build`, in that order
- PROOF-29 (RULE-23): A test comment naming `login PROOF-9`, which no spec has, beside two rules that pass their tests on committed evidence, ends on `Left to do:` and the one line `  1 test comment to correct: purlin:build`
- PROOF-15 (RULE-8): A rule with no proof line whose own marked test fails is counted as `1 rule to fix` and under no other kind
- PROOF-23 (RULE-8): On macOS, a rule waiting on `macos` and `windows` is counted as `1 rule to test: purlin:test`, since this machine can run part of it
- PROOF-33 (RULE-8): On macOS, a rule whose `PROOF-1` passes here and whose `PROOF-2`, tagged `@env(windows)`, had its test skipped here ends the status on `  1 rule to test on Windows: purlin:test --remote`
- PROOF-47 (RULE-19): A rule that passes its tests on committed evidence and that the audit found weak has the `left` `to_strengthen`, and the status opens `Tests: met`
- PROOF-54 (RULE-19): A rule with no proof line whose own marked test passes on committed evidence is counted as `1 rule to write a proof for: purlin:spec`, and the status opens `Tests: met`
- PROOF-52 (RULE-21): Two features whose rules pass their tests in local results written and not committed end on `  2 features whose results are not committed: purlin:test --commit`, and the status opens `Tests: not met`
- PROOF-44 (RULE-18): Two rules that pass their tests on committed evidence, with no `signed/*` tag, end on `Every rule passes its tests on the committed evidence. To sign it: purlin:sign`
