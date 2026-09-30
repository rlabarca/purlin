# Feature: summary

> Description: The one sentence and the one list every command ends on in the
>   terminal. The sentence counts the rules and how many pass their tests, and
>   says what the audit found where it read any. `Left to do` names each kind
>   of work left, with its count and the command that clears it, in the order
>   the work is done, or names the release step when nothing is left. The
>   status table, a test run, an audit, drift's view for QA and the evidence
>   package read these words from the payload and write none of their own; the
>   dashboard names its filter buttons by the lines of `Left to do` and shows
>   no sentence.
> Scope: scripts/mcp/purlin/summary.py
> Stack: python/stdlib
> Highest-Rule: 19
> Highest-Proof: 47

## Rules

- RULE-1: The sentence opens `<N> rules. <p> pass their tests.` at both gates, and names no count of signed rules
- RULE-12: Each rule is counted once in the sentence, under the spec that owns it, anchors' included
- RULE-2: A count of one reads singular in the sentence: `1 rule.` and `1 passes its tests.`
- RULE-13: A line of `Left to do` counting one rule reads `1 rule <words>: <command>`
- RULE-3: A count of zero reads plural: `0 pass their tests.`
- RULE-4: While work is left, the sentence is followed by `Left to do:` and one line per kind of work, indented two spaces, reading `<count> <words>: <command>`; the kinds, their words for any count but one, and their commands are `specs to repair`, `purlin:spec`; `rules to write a proof for`, `purlin:spec`; `test comments to correct`, `1 test comment to correct` for one, `purlin:build`; `rules to fix`, `purlin:build`; `rules to write a test for`, `purlin:build`; `rules to test`, `purlin:test`; `rules to test on <systems>`, `purlin:test --remote`; and `rules to strengthen`, `purlin:build`. `test comments to correct` counts, at every gate, the comments above tests that name something no spec has or a rule that has proofs
- RULE-5: The lines of `Left to do` follow the order of the kinds in RULE-4, whatever order the rules come in
- RULE-6: A kind no rule is counted under has no line
- RULE-7: Where nothing is left the ending is the sentence and one line, the last line RULE-18 names; while work is left there is no such line
- RULE-8: Each rule is counted under at most one kind, the first that applies in this order: at `signed`, no proof line (`to write a proof for`); a passed cell reading `failed` or `partial` (`to fix`); `no test` (`to write a test for`); `out of date`, or `not run` where this machine's system is among those it waits for or it names none (`to test`); `not run` for other systems only (`to test on`); a strong cell reading `weak` (`to strengthen`); a `@manual` proof and a rule no audit has read add no kind
- RULE-9: `pass their tests` counts the rules whose passed cell reads `passed`, a rule whose every proof is `@manual` included
- RULE-10: The `to test on` line names the systems its rules wait for in the words `Linux/Unix`, `macOS` and `Windows`, in that order, joined by ` and `
- RULE-14: This machine's own system is never among those the `to test on` line names, since a rule that waits for it is counted `to test`, so the line names one system or two
- RULE-16: The kind `to_repair` is the first line of `Left to do` and counts specs, not rules: those that write a rule or proof number twice or hold a line left from a merge conflict, reading `1 spec to repair: purlin:spec` for one and `<n> specs to repair: purlin:spec` for any other count
- RULE-17: The sentence adds ` The audit found <s> strong and <w> weak.` only where the audit found at least one rule that passes its tests strong or weak
- RULE-18: When nothing is left the last line names the release step: `Nothing left to do. To release a version: purlin:test --release` at the gate `passed`, the same with `, then purlin:sign` at `signed`, and `Nothing left to do. Push the tag to release it: git push origin <tag>` where a `passed/*` or `signed/*` tag points at HEAD
- RULE-19: A rule the audit found weak is left to do as `to_strengthen`, and that kind does not stop a release: it is not among the kinds that block one

## Proof

- PROOF-2 (RULE-1): At the gate `passed`, a project of 3 rules of which 2 pass their tests and none is audited reads exactly `3 rules. 2 pass their tests.`
- PROOF-4 (RULE-12): At the gate `passed`, an anchor's one passing rule beside two features of one passing rule each reads `3 rules. 3 pass their tests.`
- PROOF-5 (RULE-2): At the gate `signed`, a project of one rule that passes its tests reads `1 rule. 1 passes its tests.`
- PROOF-6 (RULE-13): At the gate `passed`, one rule whose test fails gives the one line `1 rule to fix: purlin:build` under `Left to do:`
- PROOF-7 (RULE-3): At the gate `signed`, a project of two rules whose tests both fail reads `2 rules. 0 pass their tests.`
- PROOF-8 (RULE-4): At the gate `signed`, on macOS, two rules of each of the six kinds of rule work end on `Left to do:` and six lines in RULE-4's order, each reading `  2 rules <words>: <command>`, the fifth `  2 rules to test on Windows: purlin:test --remote`
- PROOF-10 (RULE-5): At the gate `signed`, a rule the audit found weak listed before a rule whose test fails gives `1 rule to fix: purlin:build` on the line above `1 rule to strengthen: purlin:build`
- PROOF-35 (RULE-5): At the gate `passed`, one test comment to correct beside a rule whose test fails gives `1 test comment to correct: purlin:build` on the line above `1 rule to fix: purlin:build`
- PROOF-11 (RULE-6): At the gate `passed`, three rules the audit found weak give exactly one line under `Left to do:`, `3 rules to strengthen: purlin:build`
- PROOF-12 (RULE-7): At the gate `passed`, two rules that pass their tests end on exactly two lines, the sentence and a line opening `Nothing left to do.`, and `finished` is true
- PROOF-15 (RULE-8): At the gate `signed`, a rule with no proof line whose own marked test fails is counted as `1 rule to write a proof for` and under no other kind
- PROOF-16 (RULE-8): At the gate `signed`, a rule whose test fails and that no audit has read is counted as `1 rule to fix` and under no other kind
- PROOF-17 (RULE-8): At the gate `passed`, a rule with neither a proof line nor a test is counted as `1 rule to write a test for`, and no line names a proof
- PROOF-18 (RULE-8): At the gate `passed`, a rule whose passed cell reads `out of date` is counted as `1 rule to test: purlin:test`
- PROOF-23 (RULE-8): On macOS, a rule waiting on `macos` and `windows` is counted as `1 rule to test: purlin:test`, since this machine can run part of it
- PROOF-33 (RULE-8): On macOS, a rule whose `PROOF-1` passes here and whose `PROOF-2`, tagged `@env(windows)`, had its test skipped here ends the status on `  1 rule to test on Windows: purlin:test --remote`
- PROOF-34 (RULE-8): A rule whose `PROOF-1` passes in a current section and whose `PROOF-2` no test backs ends the status on `  1 rule to write a test for: purlin:build`
- PROOF-37 (RULE-8): A current section passes `PROOF-1`'s test and lists `PROOF-2`, of the same rule, as `missing` with no test named, and no marker names `PROOF-2`; the status ends on `  1 rule to write a test for: purlin:build`
- PROOF-20 (RULE-9): At the gate `passed`, a rule whose one proof is `@manual` reads `1 rule. 1 passes its tests.` and has no line under `Left to do`
- PROOF-22 (RULE-10): At the gate `passed`, on macOS, one rule waiting only on `windows` and one waiting only on `linux` give the one line `2 rules to test on Linux/Unix and Windows: purlin:test --remote`
- PROOF-28 (RULE-14): At the gate `passed`, on macOS, one rule waiting only on `macos` and one waiting only on `windows` give `1 rule to test: purlin:test` and `1 rule to test on Windows: purlin:test --remote`, and no line names macOS
- PROOF-29 (RULE-4): At the gate `passed`, a test comment naming `login PROOF-9`, which no spec has, beside two rules that pass their tests, ends on `Left to do:` and the one line `  1 test comment to correct: purlin:build`
- PROOF-36 (RULE-4): At the gate `passed`, three test comments naming `login PROOF-7`, `login PROOF-8` and `login PROOF-9`, which no spec has, beside two rules that pass their tests, end the status on `Left to do:` and the one line `  3 test comments to correct: purlin:build`
- PROOF-40 (RULE-16): At the gate `passed`, a broken spec of three failing rules beside another spec of one failing rule ends on `Left to do:`, `  1 spec to repair: purlin:spec` and `  1 rule to fix: purlin:build`, in that order
- PROOF-41 (RULE-16): At the gate `passed`, two broken specs end on `Left to do:` and the one line `  2 specs to repair: purlin:spec`
- PROOF-42 (RULE-17): At the gate `signed`, 40 rules of which 35 pass their tests and no audit has read any read exactly `40 rules. 35 pass their tests.`
- PROOF-43 (RULE-17): At the gate `passed`, 40 rules of which 35 pass their tests, 30 found strong and 2 found weak by the audit, read `40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.`
- PROOF-44 (RULE-18): At the gate `passed`, two rules that pass their tests, with no tag on HEAD, end on `Nothing left to do. To release a version: purlin:test --release`
- PROOF-45 (RULE-18): At the gate `signed`, two rules that pass their tests, with no tag on HEAD, end on `Nothing left to do. To release a version: purlin:test --release, then purlin:sign`
- PROOF-46 (RULE-18): At the gate `passed`, two rules that pass their tests, with `passed/1.2.0` on HEAD, end on `Nothing left to do. Push the tag to release it: git push origin passed/1.2.0`
- PROOF-47 (RULE-19): At the gate `signed`, a rule that passes its tests and that the audit found weak has the `left` `to_strengthen`, and that kind is not among the blocking kinds
