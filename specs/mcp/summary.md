# Feature: summary

> Description: The one sentence and the one list every command ends on in the
>   terminal. The sentence counts the rules and the steps they reached, up to
>   the gate, each step containing the next. `Left to do` names each kind of
>   work left, with its count and the command that clears it, in the order the
>   work is done, or says that nothing is left. The status table, a test run,
>   an audit, the sign walk, drift's view for QA and the evidence package read
>   these words from the payload and write none of their own; the dashboard
>   names its filter buttons by the lines of `Left to do` and shows no sentence.
> Scope: scripts/mcp/purlin/summary.py
> Stack: python/stdlib
> Highest-Rule: 14
> Highest-Proof: 37

## Rules

- RULE-1: The sentence reads `<N> rules. <p> pass their tests.` at the gate `passed`, adds ` <s> are strong.` at `strong`, and adds ` <s> are strong. <g> are signed.` at `signed`, naming no step above the gate
- RULE-12: Each rule is counted once in the sentence, under the feature that owns it
- RULE-2: A count of one reads singular in the sentence: `1 rule.`, `1 passes its tests.`, `1 is strong.`, `1 is signed.`
- RULE-13: A line of `Left to do` counting one rule reads `1 rule <words>: <command>`
- RULE-3: A count of zero reads plural: `0 pass their tests.`, `0 are strong.` and `0 are signed.`
- RULE-4: While work is left, the sentence is followed by `Left to do:` and one line per kind of work, indented two spaces, reading `<count> <words>: <command>`; the kinds, their words for any count but one, and their commands are `rules to write a proof for`, `purlin:spec`; `test comments to correct`, `1 test comment to correct` for one, `purlin:build`; `rules to fix`, `purlin:build`; `rules to write a test for`, `purlin:build`; `rules to test`, `purlin:test`; `rules to test on <systems>`, `purlin:test --remote`; `rules to test by hand`, `purlin:sign`; `rules to audit`, `purlin:audit`; `rules to measure`, `purlin:audit`; `rules to strengthen`, `purlin:build`; `rules to tie to their files`, `1 rule to tie to its files` for one, `purlin:spec`; `rules to sign`, `purlin:sign`; and `the version to tag`, with no count, `purlin:sign`. `test comments to correct` counts, at every gate, the comments above tests that name something no spec has or a rule that has proofs
- RULE-5: The lines of `Left to do` follow the order of the kinds in RULE-4, `test comments to correct` second, whatever order the rules come in
- RULE-6: A kind no rule is counted under has no line
- RULE-7: Where nothing is left the ending is the sentence and one line: `Nothing left to do.` at the gates `passed` and `strong`, and `Nothing left to do. Push the tag to release it: git push origin <tag>` at `signed`, naming the `signed/*` tag on HEAD
- RULE-8: Each rule is counted under at most one kind, the first that applies in this order: at `strong` or `signed`, no proof line (`to write a proof for`); a passed cell reading `failed` or `partial` (`to fix`); `no test` (`to write a test for`); `out of date`, or `not run` where this machine's system is among those it waits for or it names none (`to test`); `not run` for other systems only (`to test on`); a `@manual` proof no person has checked by hand (`to test by hand`); at `strong` or `signed`, a strong cell reading neither `strong` nor `weak` (`to audit`); `weak` only because its feature's strength was not measured (`to measure`), `weak` only because its spec names no code files (`to tie to its files`), and any other `weak` (`to strengthen`); at `signed`, a signed cell not reading `signed`, where the owning spec names no files (`to tie to its files`) and otherwise (`to sign`); a rule that reached every step up to the gate is counted under none
- RULE-9: The step counts contain one another: `pass their tests` counts the rules whose passed cell reads `passed` and, where a proof is `@manual`, that a person checked by hand; `are strong` counts those of them whose strong cell reads `strong`; `are signed` counts those of them whose signed cell reads `signed`
- RULE-10: The `to test on` line names the systems its rules wait for in the words `Linux/Unix`, `macOS` and `Windows`, in that order, joined by ` and `
- RULE-14: This machine's own system is never among those the `to test on` line names, since a rule that waits for it is counted `to test`, so the line names one system or two
- RULE-11: At the gate `signed`, where no rule is counted under any kind, no test comment is left to correct and no `signed/*` tag points at HEAD, `Left to do` holds one line, `the version to tag: purlin:sign`; at `passed` and `strong` it never does

## Proof

- PROOF-1 (RULE-1): At the gate `signed`, a project of 40 rules, where 35 pass their tests, 30 of those are strong and 20 of those are signed, reads `40 rules. 35 pass their tests. 30 are strong. 20 are signed.`
- PROOF-2 (RULE-1): At the gate `passed`, a project of 3 rules of which 2 pass their tests reads exactly `3 rules. 2 pass their tests.`, with no strong or signed count
- PROOF-3 (RULE-1): At the gate `strong`, a project of 3 rules, 2 passing their tests and both strong, reads exactly `3 rules. 2 pass their tests. 2 are strong.`, with no signed count
- PROOF-4 (RULE-12): At the gate `passed`, a global anchor's one passing rule, listed under two features of one passing rule each, reads `3 rules. 3 pass their tests.`: the anchor's rule is counted once
- PROOF-5 (RULE-2): At the gate `signed`, a project of one rule that passes its tests, is strong and is signed reads `1 rule. 1 passes its tests. 1 is strong. 1 is signed.`
- PROOF-6 (RULE-13): At the gate `strong`, one rule that passes its tests and has not been audited gives the one line `1 rule to audit: purlin:audit` under `Left to do:`
- PROOF-7 (RULE-3): At the gate `signed`, a project of two rules whose tests both fail reads `2 rules. 0 pass their tests. 0 are strong. 0 are signed.`
- PROOF-8 (RULE-4): At the gate `signed`, on macOS, a project holding two rules of each of the eleven kinds of rule work ends on `Left to do:` and eleven lines in the order RULE-4 lists the kinds, each reading `  2 rules <words>: <command>` with that kind's words and command, the fifth `  2 rules to test on Windows: purlin:test --remote`
- PROOF-9 (RULE-4): At the gate `signed`, one strong, unsigned rule whose spec names no files gives the line `1 rule to tie to its files: purlin:spec`
- PROOF-10 (RULE-5): At the gate `signed`, a rule waiting to be signed listed before a rule whose test fails gives `1 rule to fix: purlin:build` on the line above `1 rule to sign: purlin:sign`
- PROOF-35 (RULE-5): At the gate `passed`, one test comment to correct beside a rule whose test fails gives `1 test comment to correct: purlin:build` on the line above `1 rule to fix: purlin:build`
- PROOF-11 (RULE-6): At the gate `strong`, three rules that pass their tests and have not been audited give exactly one line under `Left to do:`, `3 rules to audit: purlin:audit`
- PROOF-12 (RULE-7): At the gate `passed`, two rules that pass their tests end on exactly two lines, `2 rules. 2 pass their tests.` and `Nothing left to do.`
- PROOF-13 (RULE-7): At the gate `strong`, two rules that pass their tests and are strong end on exactly two lines, `2 rules. 2 pass their tests. 2 are strong.` and `Nothing left to do.`
- PROOF-14 (RULE-7): At the gate `signed`, every rule signed with the tag `signed/1.4.0` on HEAD, the last line reads `Nothing left to do. Push the tag to release it: git push origin signed/1.4.0`
- PROOF-15 (RULE-8): At the gate `strong`, a rule with no proof line whose own marked test fails is counted as `1 rule to write a proof for` and under no other kind
- PROOF-16 (RULE-8): At the gate `signed`, a rule whose test fails, that no audit has read and that nobody signed, is counted as `1 rule to fix` and under no other kind
- PROOF-17 (RULE-8): At the gate `passed`, a rule with neither a proof line nor a test is counted as `1 rule to write a test for`, and no line names a proof
- PROOF-18 (RULE-8): At the gate `strong`, a rule whose passed cell reads `out of date` is counted as `1 rule to test: purlin:test`
- PROOF-19 (RULE-9): At the gate `signed`, a rule that passes its tests, that the audit found weak and that carries a counting signature, reads `1 rule. 1 passes its tests. 0 are strong. 0 are signed.`
- PROOF-20 (RULE-9): At the gate `passed`, a rule whose one proof is `@manual` and that nobody has checked by hand reads `1 rule. 0 pass their tests.` and gives `1 rule to test by hand: purlin:sign`
- PROOF-21 (RULE-9): At the gate `passed`, a rule whose one proof is `@manual` and that a person has checked by hand reads `1 rule. 1 passes its tests.` and `Nothing left to do.`
- PROOF-22 (RULE-10): At the gate `passed`, on macOS, one rule waiting only on `windows` and one waiting only on `linux` give the one line `2 rules to test on Linux/Unix and Windows: purlin:test --remote`
- PROOF-28 (RULE-14): At the gate `passed`, on macOS, one rule waiting only on `macos` and one waiting only on `windows` give `1 rule to test: purlin:test` and `1 rule to test on Windows: purlin:test --remote`, and no line names macOS
- PROOF-23 (RULE-8): On macOS, a rule waiting on `macos` and `windows` is counted as `1 rule to test: purlin:test`, since this machine can run part of it
- PROOF-31 (RULE-8): At the gate `strong`, a rule whose strong cell reads `weak` with the one reason `strength not measured: mutmut is not installed: run "pip install mutmut"` gives the line `  1 rule to measure: purlin:audit`
- PROOF-32 (RULE-8): At the gate `strong`, with `mutation_engine` set to `auto`, a spec with no `> Scope:` line whose one rule passes its test and is audited with nothing found ends the status on `  1 rule to tie to its files: purlin:spec`
- PROOF-33 (RULE-8): On macOS, a rule whose `PROOF-1` passes here and whose `PROOF-2`, tagged `@env(windows)`, had its test skipped here ends the status on `  1 rule to test on Windows: purlin:test --remote`
- PROOF-34 (RULE-8): A rule whose `PROOF-1` passes in a current section and whose `PROOF-2` no test backs ends the status on `  1 rule to write a test for: purlin:build`
- PROOF-24 (RULE-11): At the gate `signed`, every rule signed and no `signed/*` tag on HEAD, `Left to do:` holds the one line `the version to tag: purlin:sign`
- PROOF-25 (RULE-11): At the gate `strong`, every rule strong and no tag anywhere, the ending's last line is `Nothing left to do.` and no line names a tag
- PROOF-30 (RULE-11): At the gate `signed`, every rule signed, no `signed/*` tag on HEAD and one test comment naming nothing, `Left to do:` holds the one line `  1 test comment to correct: purlin:build`, and no line names the version to tag
- PROOF-26 (RULE-4): At the gate `signed`, the status report of a project whose one spec has no `> Scope:` line, and whose two rules pass their tests and are audited with nothing found, ends on `Left to do:` and `  2 rules to tie to their files: purlin:spec`
- PROOF-29 (RULE-4): At the gate `passed`, a test comment naming `login PROOF-9`, which no spec has, beside two rules that pass their tests, ends on `Left to do:` and the one line `  1 test comment to correct: purlin:build`
- PROOF-36 (RULE-4): At the gate `passed`, three test comments naming `login PROOF-7`, `login PROOF-8` and `login PROOF-9`, which no spec has, beside two rules that pass their tests, end the status on `Left to do:` and the one line `  3 test comments to correct: purlin:build`
- PROOF-37 (RULE-8): A current section passes `PROOF-1`'s test and lists `PROOF-2`, of the same rule, as `missing` with no test named, and no marker names `PROOF-2`; the status ends on `  1 rule to write a test for: purlin:build`
