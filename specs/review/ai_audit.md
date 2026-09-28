# Feature: ai_audit

> Description: The AI audit `purlin:audit` runs on each rule it reads. It sets the rule, its
>   proofs and the source of each test that backs them beside `references/review_criteria.md`,
>   sends that prompt to the model through the `claude` command, one call per rule and a set
>   number at once, and reads the answer back into a `verdict` and findings: settled with nothing
>   found is `strong`, settled with findings is `weak`, and not settled is `undecided`. Each
>   answer names the model that gave it and a fingerprint of the criteria it was sent. When the
>   model cannot be reached the answer is only the reason, so nothing is written and the next
>   audit tries again. It writes no file; the run writes what it found into the evidence.
> Scope: scripts/review/ai_audit.py, scripts/review/marked_tests.py
> Stack: python/stdlib (json, hashlib, subprocess, shutil, concurrent.futures)

## Rules

- RULE-1: The audit reads a rule that is its feature's own, has at least one proof with a test, whose passed cell reads `passed` and that has no audit entry for its current rule, proof and test; under a gate above `passed` it never reads a rule whose level is `passed`, and reading again ignores an existing entry
- RULE-2: The prompt is `references/review_criteria.md` verbatim, then the rule's text, its proofs, the source of each test and the test strength, and it asks for what was observed rather than a recommendation, a grade or a score
- RULE-3: The call is `claude -p --output-format json` with the prompt written to its standard input, which is closed after the prompt, and never on the command line, and it is given 300 seconds
- RULE-4: One call is made per rule, and as many calls run at once as the number the caller names
- RULE-5: An answer that settled with no finding is `strong`, one that settled with findings is `weak` with each line a finding, and one that did not settle is `undecided` with its lines as the reason; an answer that says neither is no answer
- RULE-6: Each answer names the model the command's JSON reports, the one that wrote the most where several are named, or `unknown` where none is, and carries the sha256 of the criteria as they were sent
- RULE-7: The model cannot be reached when `claude` is not on the path, when it exits with an error, when it runs past its limit, or when its answer has no settled line after one retry; the answer is then only the reason, `claude is not on PATH`, `claude exited with an error`, `claude timed out after <n> s` or `claude answered without a settled line`, and with no `claude` on the path no call is made
- RULE-8: What the audit reads for a rule names each marked test's file, its name and its source, and the feature's test strength beside the project minimum
- RULE-9: A `@manual` proof's test entry reads `manual` true and names no test file and no source
- RULE-10: When several tests back one proof, each test shows its own source; a test whose source cannot be found shows none rather than another test's
- RULE-11: The test source is read out of JavaScript and TypeScript by balancing braces, so a nested options object, an apostrophe in a title, a regex literal, a comment or a division never cuts a body short or drops a test
- RULE-12: Reading a rule, asking the model and printing the result write no file anywhere under `.purlin/`, and the triple a reading names moves whenever the rule, the proof or the test moves
- RULE-13: `ai_audit.py --help` exits 0, an unknown option or a missing `--feature` exits 2, a feature with no rule in the project exits 1, and the command calls no model [level: passed]
- RULE-14: `ai_audit.py --feature <name>` prints what the audit reads for one rule named with `--rule`, or for every rule of the feature without it: the rule, its proofs, each test, the test strength beside the minimum and what the last audit found, with its `verdict`, model and time, and no emoji [level: passed]
- RULE-15: Reading a rule the project does not hold returns nothing rather than an empty reading [level: passed]

## Proof

- PROOF-1 (RULE-1): A rule of the feature's own with a passing test and no audit entry, at the gate `strong`, is read
- PROOF-2 (RULE-1): A rule whose passed cell reads `failed` is not read, a rule whose one proof is `@manual` is not read, and a rule another feature requires is not read where it is required
- PROOF-3 (RULE-1): A rule whose level is `passed` is not read at the gate `strong` nor at `signed`, and is read at the gate `passed`
- PROOF-4 (RULE-1): A rule with an audit entry for its current hashes is not read, and is read when the caller asks to read again
- PROOF-5 (RULE-8): In a project whose evidence names the test `test_valid_credentials_return_200` for `RULE-1`, what the audit reads for `RULE-1` names the file `tests/test_login.py`, that test, and carries the line `assert login("ada", "secret") == 200`
- PROOF-6 (RULE-9): With the proof of `RULE-1` tagged `@manual`, what the audit reads for it has a test entry reading `manual` true, with no file and no source
- PROOF-7 (RULE-15): Asking for `RULE-99`, which the spec does not declare, returns nothing
- PROOF-8 (RULE-8): With evidence whose test strength is 90 at the gate `strong`, what the audit reads for `RULE-2` carries 90 against a minimum of 70; with no strength measured the printed rule reads `Test strength: n/a`
- PROOF-9 (RULE-11): A TypeScript file whose first test passes an options object to a call and whose second title carries an apostrophe yields both proofs, and the first body holds the `expect(` after the options object
- PROOF-10 (RULE-11): One file whose tests divide across a line break after `"a" +`, build `/[}/"']+/g`, build `/\/}/`, hold a `}` in a `//` comment and in a `/* */` comment, and divide `4 / 2` and `8 / 4` on one line yields exactly 6 proofs, each body holding its `expect(`
- PROOF-11 (RULE-2): The prompt for `RULE-2` at the gate `strong` opens with `references/review_criteria.md` byte for byte and then names `RULE-2`, `Invalid credentials return 401`, the test `test_a_bad_password_is_denied` and `Test strength: 90 percent (minimum 70)`
- PROOF-12 (RULE-2): The prompt holds `settled: yes`, `one line per observation`, `Do not recommend a change` and `do not grade the rule`
- PROOF-13 (RULE-3): Asking the fake `claude` about `RULE-2` makes exactly one call whose arguments are exactly `-p`, `--output-format` and `json`, whose standard input is the whole prompt, and none of whose arguments carries the rule text `Invalid credentials`
- PROOF-14 (RULE-3): The call is made with the prompt as its input and a limit of 300 seconds, and is not handed a standard input of its own to leave open
- PROOF-15 (RULE-4): Asking about six rules at four at a time, with each call taking 0.4 seconds, makes 6 calls, reads 6 `strong` answers back in order, and never has more than 4 calls running at the same moment, and at one moment has 4
- PROOF-16 (RULE-4): Asking about four rules at two at a time makes 4 calls and never more than 2 at the same moment
- PROOF-17 (RULE-5): The answer `settled: yes` with no line reads `strong` with no finding
- PROOF-18 (RULE-5): The answer `settled: yes` then `- PROOF-2 asserts the status but never the body the rule names.` reads `weak` with that sentence as its one finding
- PROOF-19 (RULE-5): The answer `settled: no` then `- The body of PROOF-2 is not shown.` reads `undecided` with that sentence
- PROOF-20 (RULE-6): An answer whose JSON names the model `claude-opus-4-1-20250805` records that model and the sha256 of `references/review_criteria.md`; one whose JSON names no model records `unknown`
- PROOF-21 (RULE-6): JSON naming `claude-haiku-3-5` with 12 output tokens and `claude-opus-4-1` with 900 names `claude-opus-4-1`; a top-level model `claude-x-1` names `claude-x-1`; JSON naming none names `unknown`
- PROOF-22 (RULE-5): The answers `It looks fine to me.` and an empty answer find nothing and say nothing about settling, and such an answer carries no `verdict` at all
- PROOF-23 (RULE-7): With no `claude` on the path, asking about two rules answers `claude is not on PATH` for each and the fake records no call
- PROOF-24 (RULE-7): A `claude` that exits 1 answers `claude exited with an error`
- PROOF-25 (RULE-7): With the limit set to 1 second and a `claude` that takes 3, the answer is `claude timed out after 1 s`
- PROOF-26 (RULE-7): A `claude` whose answer is `It looks fine to me.` is asked twice and the answer is `claude answered without a settled line`; one that answers `It looks fine to me.` and then `settled: yes` is asked twice and reads `strong`
- PROOF-27 (RULE-12): List every file under `.purlin/` outside `runtime/`, then read `RULE-2`, ask the fake `claude` about it, print it and run the command for `login`; the list is unchanged
- PROOF-28 (RULE-12): Read `RULE-1`, then change `return 200 with a session token` to `return 200 with a short session token` in the rule and read it again; the two triples differ
- PROOF-29 (RULE-14): With an audit entry finding `PROOF-2 asserts the status but never the body the rule names.`, the printed `RULE-2` names `login RULE-2`, the rule text, `PROOF-2`, `Test strength: 90 percent   minimum 70`, `What the audit found`, `Weak, by unknown at 2026-09-13T12:05:00Z.` and the finding, with no emoji; a rule no audit has read prints `Nothing yet: no audit has read this rule's text`
- PROOF-30 (RULE-13): The command run with `--help`, with `--nope` and with no argument exits 0, 2 and 2
- PROOF-31 (RULE-13): The command run for the feature `nothing`, which no spec declares, exits 1
- PROOF-32 (RULE-14): The command run for `--feature login --rule RULE-1` exits 0 and prints `login RULE-1` and not `login RULE-2`; run for `--feature login` alone it prints both
- PROOF-33 (RULE-13): The command run as its own process for `login RULE-1` exits 0, prints `login RULE-1`, and the fake `claude` records no call
- PROOF-34 (RULE-10): With `test_valid_credentials_return_200` and `test_a_token_comes_back` both marked for `PROOF-1`, the first test's source holds `def test_valid_credentials_return_200` and `== 200` and not `def test_a_token_comes_back`, and the second's holds `def test_a_token_comes_back` and `token` and not `def test_valid_credentials_return_200`
- PROOF-35 (RULE-10): With a third name `test_renamed_away` for `PROOF-1` that the file no longer holds, that test shows no source while the other two still show their own
- PROOF-36 (RULE-10): The names `Acme.LoginTests.Denied(user: "x")`, `test_found[jest-[proof:f:PROOF-1:RULE-1]]`, `TestLogin::test_found` and `works [proof:login:PROOF-1:RULE-1]` each find their own source name among `Allowed`, `Denied`, `test_found` and `works [proof:login:PROOF-1:RULE-1]`, and `test_gone` finds none
