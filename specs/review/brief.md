# Feature: brief

> Description: The machine's report on one rule. It sets the rule, its
>   proofs and the source of each test that backs them beside the evidence,
>   in two layers, and stops when it has enough for the rule's level: the test
>   strength the evidence holds, then the AI audit, which reads the rule,
>   the proofs and the test source. The criteria are
>   `references/review_criteria.md` and nothing else. It ends with three
>   things and no judgment: the strength beside the minimum, the audit's
>   observations one sentence at a time, and whether the audit settled. It
>   recommends nothing, and it writes no file: `purlin:audit` reads each
>   brief into the feature's evidence as that rule's audit entry.
> Scope: scripts/review/brief.py, scripts/review/marked_tests.py
> Stack: python/stdlib (json, glob, subprocess, shutil)

## Rules

- RULE-1: A brief for a rule whose level is `passed` runs the test-strength layer and no other, so no AI audit is asked for [bar: strong]
- RULE-2: A brief for a rule whose level is `strong` or `signed` runs both layers, the test strength first and the AI audit last [bar: strong]
- RULE-3: The layers a brief ran are named in its `layers` field, so a reader can tell what was and was not looked at [bar: strong]
- RULE-4: Building a brief for a rule the project does not hold returns nothing rather than an empty brief [bar: passed]
- RULE-7: The brief shows the marked test's file, its name and its source beside the rule [bar: strong]
- RULE-8: A `@manual` proof's test entry reads `manual` true and names no test file and no source, because its evidence is the signer's note [bar: strong]
- RULE-9: The test strength comes off the feature's evidence and is shown against the configured minimum, reading `n/a` when no engine measured one [bar: strong]
- RULE-10: The brief carries no recommendation, no grade, no state and no schema: its fields are the evidence, the observations and the numbers, and nothing else [bar: strong]
- RULE-12: A model answer becomes one observation per sentence, each naming the proof it concerns [bar: strong]
- RULE-13: The brief records whether the review settled the question, as yes, no, or not answered at all [bar: strong]
- RULE-15: The model prompt is `references/review_criteria.md` verbatim, then this rule's rule text, proof text, test bodies and test strength, and it asks for observations rather than a recommendation or a score [bar: strong]
- RULE-16: The AI audit runs only when the caller passes `--ai` and the rule's level is `strong` or `signed`; without it, and with no model on the path, the brief records `not available` [bar: strong]
- RULE-17: An answer in no shape the brief can read observes nothing and leaves the question not answered [bar: strong]
- RULE-19: Building a brief, rendering it and running the command write no file anywhere under `.purlin/`, and the triple a brief names moves whenever the rule, the proof or the test moves [bar: strong]
- RULE-22: The text rendering names the rule, its proofs, the test strength beside the minimum, the observations and whether the review settled, and carries no emoji [bar: passed]
- RULE-23: `brief.py --help` exits 0, an unknown option or a missing `--feature` exits 2, and a feature with no rule in the project exits 1 [bar: passed]
- RULE-24: `brief.py --feature <name>` with no `--rule` builds and prints a brief for every rule of that feature [bar: passed]
- RULE-26: When several tests back one proof, each test in the brief shows its own source; a test whose source cannot be found shows none rather than another test's [bar: strong]
- RULE-28: The test source is read out of JavaScript and TypeScript by balancing braces, so a nested options object, an apostrophe in a title, a regex literal, a comment or a division never cuts a body short or drops a test [bar: strong]

## Proof

- PROOF-1 (RULE-1): Build the brief for a `[level: passed]` rule in a project holding evidence; verify its layers are exactly `test strength`
- PROOF-2 (RULE-1): Build the brief for that same `[level: passed]` rule; verify its layers do not name the AI audit and that its AI audit field is `none`
- PROOF-3 (RULE-2): At the gate `strong`, build the brief for the unmarked rule, whose level is the gate's; verify its layers add `AI audit` after `test strength`
- PROOF-4 (RULE-3): Build the brief for a rule whose level is `strong`; verify its layers are `test strength`, `AI audit` in that order
- PROOF-5 (RULE-4): Build a brief for `RULE-99`, which the spec does not declare; verify nothing comes back
- PROOF-8 (RULE-7): Build the brief for a rule the evidence covers; verify it names the file `tests/test_login.py`, the test `test_valid_credentials_return_200`, and shows the asserting line of that test's source
- PROOF-9 (RULE-8): Retag the proof `@manual` and build the brief; verify the test entry names no file and no source and reads `manual` true
- PROOF-10 (RULE-9): Write evidence whose test strength is 90 and build the brief for a rule whose level is `strong`; verify the brief reads 90 against a minimum of 50
- PROOF-11 (RULE-9): Write evidence with no test strength and render the brief; verify the rendering reads `Test strength: n/a`
- PROOF-12 (RULE-10): Build the brief for a `[level: passed]` rule the evidence covers; verify its field names are exactly the 18 the module builds, none of them `schema`, and its observations list is empty
- PROOF-17 (RULE-13): Read the observations out of `settled: yes` and out of `settled: no` followed by `- PROOF-1 never runs the code.`; verify the first settles with nothing observed and the second does not settle and carries that one sentence
- PROOF-19 (RULE-15): Build the model prompt for a rule whose level is `strong` at gate `strong`; verify it opens with `references/review_criteria.md` byte for byte and then names `RULE-2`, the rule text, the test `test_a_bad_password_is_denied` and `Test strength: 90 percent (minimum 70)`
- PROOF-20 (RULE-16): Build the brief for a rule that asks for an AI audit without passing `--ai`; verify the review it carries reads `not available`, no observation comes back and the rendering reads `Settled: not answered`
- PROOF-21 (RULE-16): With no `claude` on the path, build the brief with `--ai`; verify the review it carries reads `not available`
- PROOF-22 (RULE-16): Build the brief for a `[level: passed]` rule with `--ai` and a probe that raises if the path is searched; verify no model is reached, the review it carries is `none` and the rendering holds no `Observations` heading
- PROOF-23 (RULE-12): Replace the model launch with the answer `settled: no` followed by `- PROOF-2 asserts the status but never the body the rule names.`; verify one `claude -p` call is made, the brief carries that one observation and it did not settle
- PROOF-24 (RULE-17): Read the observations out of `It looks fine to me.`, `not available` and an empty answer; verify each observes nothing and leaves the question not answered
- PROOF-27 (RULE-19): List every file under `.purlin/` outside `runtime/`, then build and render the brief for `RULE-1` and run the command for `login`; verify the list is unchanged
- PROOF-28 (RULE-19): Build the brief for `RULE-1`, then edit the rule text and build it again; verify the two triples differ
- PROOF-31 (RULE-22): Render the brief for a rule whose level is `strong` at gate `strong`; verify the text names `login RULE-2`, the rule text, `PROOF-2`, `Test strength: 90 percent   minimum 70`, an `Observations` heading and a `Settled:` line, and carries no emoji or emoticon
- PROOF-32 (RULE-23): Run the command with `--help`, with `--nope` and with no argument; verify the exit codes are 0, 2 and 2
- PROOF-33 (RULE-23): Run the command for the feature `nothing`, which no spec declares; verify it exits 1
- PROOF-34 (RULE-24): Run the command for `--feature login --rule RULE-1`; verify it exits 0, prints `login RULE-1` and writes no file under `.purlin/` outside `runtime/`
- PROOF-35 (RULE-24): Run the command for `--feature login` with no rule named; verify it exits 0 and prints both `login RULE-1` and `login RULE-2`
- PROOF-36 (RULE-23): Run `brief.py` as a command in a separate process against a project holding evidence; verify it exits 0 and its output names `login RULE-1`
- PROOF-38 (RULE-26): Mark `test_valid_credentials_return_200` and a second test `test_a_token_comes_back` with `PROOF-1`, write both into the evidence, and build the brief; verify the first entry's body holds `def test_valid_credentials_return_200` and `== 200` and not `def test_a_token_comes_back`, and the second entry's body holds `def test_a_token_comes_back` and `token` and not `def test_valid_credentials_return_200`
- PROOF-40 (RULE-26): Write a third name `test_renamed_away` into the evidence for `PROOF-1` that the file no longer holds; verify its body is empty while the other two still show their own source
- PROOF-41 (RULE-26): Read the names a section carries, `Acme.LoginTests.Denied(user: "x")`, `test_found[jest-[proof:f:PROOF-1:RULE-1]]`, `TestLogin::test_found` and `works [proof:login:PROOF-1:RULE-1]` against the source names `Allowed`, `Denied`, `test_found` and `works [proof:login:PROOF-1:RULE-1]`; verify each finds its own source name and nothing else, and `test_gone` finds none
- PROOF-44 (RULE-15): Build the model prompt for a rule whose level is `strong`; verify it holds `settled: yes`, `one line per observation`, `Do not recommend a change` and `do not grade the rule`
- PROOF-46 (RULE-28): Read the source out of a TypeScript file whose first test passes an options object to a call and whose second title carries an apostrophe; verify both proofs come back and the first body holds the `expect(` after the options object
- PROOF-47 (RULE-28): Read the source out of one file whose first test divides across a line break after `"a" +`, whose second builds `/[}/"']+/g`, whose third builds `/\/}/`, whose fourth holds a `}` in a `//` comment and in a `/* */` comment, and whose fifth and sixth sit on one line dividing `4 / 2` and `8 / 4`; verify exactly the 6 proofs come back and each body holds its `expect(`
