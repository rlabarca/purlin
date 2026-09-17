# Feature: brief

> Description: The machine's report on one rule. It gathers evidence in layers,
>   cheapest first, and stops when it has enough for the rule's risk: the free
>   checks on the proof text, the free checks on the test body, the test
>   strength from the latest record, then a model review. The criteria are
>   `references/review_criteria.md` and nothing else, so the brief reports
>   findings under the names that file gives. It ends with four things and no
>   judgment: the strength beside the minimum, the findings, the model's
>   observations one sentence at a time, and whether the review settled. It
>   recommends nothing. The brief lands beside the records, named for the
>   triple it was built from.
> Scope: scripts/review/brief.py
> Stack: python/stdlib (json, glob, subprocess, shutil)

## Rules

- RULE-1: A low-risk rule's brief runs the proof-text and test-body layers and no others, so its test strength is never read [risk: medium] [origin: eng]
- RULE-2: A medium-risk rule's brief adds the test strength layer and stops there [risk: medium] [origin: eng]
- RULE-3: A high-risk rule's brief runs all four layers, the model review last [risk: high] [origin: eng]
- RULE-4: Building a brief for a rule the project does not hold returns nothing rather than an empty brief [risk: low] [origin: eng]
- RULE-5: Every free check on the proof text reaches the brief under the name `references/review_criteria.md` gives it [risk: high] [origin: eng]
- RULE-6: Every free check on the marked test body reaches the brief under its own name, each with the reason a reader acts on [risk: high] [origin: eng]
- RULE-7: The brief shows the marked test's file, its name and its source beside the rule [risk: medium] [origin: eng]
- RULE-8: A `@manual` proof carries a note where a test would be and no test file, because its evidence is the signer's note [risk: high] [origin: eng]
- RULE-9: The test strength comes off the feature's latest record and is shown against the configured minimum, reading `n/a` when no engine measured one [risk: medium] [origin: eng]
- RULE-10: The brief carries no recommendation, no grade and no state: its fields are the evidence, the observations and the numbers, and nothing else [risk: high] [origin: eng]
- RULE-12: A model answer becomes one observation per sentence, each naming the proof it concerns [risk: high] [origin: eng]
- RULE-13: The brief records whether the review settled the question, as yes, no, or not answered at all [risk: high] [origin: eng]
- RULE-15: The model prompt is `references/review_criteria.md` verbatim, then this rule's rule text, proof text, test bodies and test strength, and it asks for observations rather than a recommendation or a score [risk: medium] [origin: eng]
- RULE-16: The model review runs only when the caller passes `--ai` and the rule's risk is at or above `ai_review_at`; without it, and with no model on the path, the brief records `not available` [risk: medium] [origin: eng]
- RULE-17: An answer in no shape the brief can read observes nothing and leaves the question not answered [risk: high] [origin: eng]
- RULE-18: A rule a designer owns shows the pinned mock beside the screenshot the test captured, and a glob that matches nothing is shown as the glob [risk: medium] [origin: eng]
- RULE-19: The brief is written as `.purlin/briefs/<feature>/<RULE-N>.<hash8>.brief.json` carrying schema `purlin-brief/2`, with a text rendering of the same name beside it, and is found again only while the triple stands [risk: medium] [origin: eng]
- RULE-21: Writing briefs with no list named covers every rule whose risk is at or above `ai_review_at` and whose passed cell counts, and a narrower list covers only what it names [risk: low] [origin: eng]
- RULE-22: The text rendering names the rule, its proofs, the test strength beside the minimum, the observations and whether the review settled, and carries no emoji [risk: low] [origin: eng]
- RULE-23: `brief.py --help` exits 0, an unknown option or a missing `--feature` exits 2, and a feature with no rule in the project exits 1 [risk: low] [origin: eng]
- RULE-24: `brief.py --feature <name>` with no `--rule` builds, prints and writes a brief for every rule of that feature [risk: low] [origin: eng]
- RULE-25: A name that opens with an underscore reaches the brief as `implementation_coupling` unless it follows a `/`, so a path or URL segment such as `specs/_anchors/` or `/_git/` is not read as a private symbol [risk: medium] [origin: eng]
- RULE-26: When several tests back one proof, each test in the brief shows its own source and its own findings; a test whose source cannot be found shows none rather than another test's [risk: high] [origin: eng]
- RULE-27: Writing a brief again for a triple that already has one leaves the JSON byte for byte as it was unless the evidence in it changed; a difference only in when it was built or the record it was built from is not a change, so reading a brief dirties no tracked file [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Build the brief for a `[risk: low]` rule in a project holding a record; verify its layers are exactly `proof text` and `test body` @integration
- PROOF-2 (RULE-1): Build the brief for that same low-risk rule; verify its test strength is `none` because the strength layer did not run @integration
- PROOF-3 (RULE-2): Retag the rule `[risk: medium]`, run the tests and write a record, then build the brief; verify its layers are `proof text`, `test body`, `test strength` and nothing after @integration
- PROOF-4 (RULE-3): Build the brief for a `[risk: high]` rule; verify its layers are `proof text`, `test body`, `test strength`, `model review` in that order @integration
- PROOF-5 (RULE-4): Build a brief for `RULE-99`, which the spec does not declare; verify nothing comes back @integration
- PROOF-6 (RULE-5): Write a proof reading `The login works correctly`, then build the brief; verify its findings carry both `no_expected_value` and `vague_verb` @integration
- PROOF-7 (RULE-6): Edit the marked test so it calls the code and asserts nothing, then build the brief; verify the test's findings are exactly `no_assertion` and that a reason is printed with it @integration
- PROOF-8 (RULE-7): Build the brief for a rule a record covers; verify it names the file `tests/test_login.py`, the test `test_valid_credentials_return_200`, and shows the asserting line of that test's source @integration
- PROOF-9 (RULE-8): Retag the proof `@manual` and build the brief; verify the test entry names no file and its findings are exactly `manual` @integration
- PROOF-10 (RULE-9): Write a record whose test strength is 90 and build the brief for a high-risk rule; verify the brief reads 90 against a minimum of 50 @integration
- PROOF-11 (RULE-9): Write a record with no test strength and render the brief; verify the rendering reads `Test strength: n/a` @integration
- PROOF-12 (RULE-10): Build the brief for a low-risk rule a record covers; verify its field names are exactly the 23 the module writes, its schema is `purlin-brief/2` and its observations list is empty @integration
- PROOF-17 (RULE-13): Read the observations out of `settled: yes` and out of `settled: no` followed by `- PROOF-1 never runs the code.`; verify the first settles with nothing observed and the second does not settle and carries that one sentence
- PROOF-19 (RULE-15): Build the model prompt for a high-risk rule at gate `strong`; verify it opens with `references/review_criteria.md` byte for byte and then names `RULE-2`, the rule text, the test `test_a_bad_password_is_denied` and `Test strength: 90 percent (minimum 70)` @integration
- PROOF-20 (RULE-16): Build the brief for a rule that asks for a model review without passing `--ai`; verify the review it carries reads `not available`, no observation comes back and the rendering reads `Settled: not answered` @integration
- PROOF-21 (RULE-16): With no `claude` on the path, build the brief with `--ai`; verify the review it carries reads `not available` @integration
- PROOF-22 (RULE-16): Build the brief for a rule whose risk is below `ai_review_at` with `--ai` and a probe that raises if the path is searched; verify no model is reached, the review it carries is `none` and the rendering holds no `Observations` heading @integration
- PROOF-23 (RULE-12): Replace the model launch with the answer `settled: no` followed by `- PROOF-2 asserts the status but never the body the rule names.`; verify one `claude -p` call is made, the brief carries that one observation and it did not settle @integration
- PROOF-24 (RULE-17): Read the observations out of `It looks fine to me.`, `not available` and an empty answer; verify each observes nothing and leaves the question not answered
- PROOF-25 (RULE-18): Write a mock at `designs/login/sign-in.png` and a screenshot for `PROOF-1`, then build the brief for an `[origin: design]` rule; verify both paths are shown and the pinned hash reads `3f2a1b0c9d8e7f6a` @integration
- PROOF-26 (RULE-18): Build the same design rule's brief with no screenshot on disk; verify the mock is shown as the glob `designs/login/*.png` and the screenshot list is empty @integration
- PROOF-27 (RULE-19): Write the brief for a rule; verify the path is `.purlin/briefs/login/RULE-1.<hash8>.brief.json` for the rule's own triple, that a `.txt` rendering sits beside it, and that the JSON carries schema `purlin-brief/2` @integration
- PROOF-28 (RULE-19): Write the brief for `RULE-1`, then edit the rule text and build it again; verify the file written first is still on disk and the new triple differs from it @integration
- PROOF-29 (RULE-21): Write a CI record in a project at gate `strong`, then write briefs with no list named; verify exactly 1 path comes back, it names `RULE-2` and it opens `.purlin/briefs/login/` @integration
- PROOF-30 (RULE-21): Write briefs for the single pair `login RULE-1`; verify exactly 1 path comes back and it names `RULE-1` @integration
- PROOF-31 (RULE-22): Render the brief for a high-risk rule at gate `strong`; verify the text names `login RULE-2`, the rule text, `PROOF-2`, `Test strength: 90 percent   minimum 70`, an `Observations` heading and a `Settled:` line, and carries no emoji or emoticon @integration
- PROOF-32 (RULE-23): Run the command with `--help`, with `--nope` and with no argument; verify the exit codes are 0, 2 and 2 @integration
- PROOF-33 (RULE-23): Run the command for the feature `nothing`, which no spec declares; verify it exits 1 @integration
- PROOF-34 (RULE-24): Run the command for `--feature login --rule RULE-1`; verify it exits 0, prints `login RULE-1` and creates the `.purlin/briefs/login` directory @integration
- PROOF-35 (RULE-24): Run the command for `--feature login` with no rule named; verify it exits 0 and prints both `login RULE-1` and `login RULE-2` @integration
- PROOF-36 (RULE-23): Run `brief.py` as a command in a separate process against a project holding a record; verify it exits 0 and its output names `login RULE-1` @integration
- PROOF-37 (RULE-25): Write a proof reading `POST /login, then read specs/_anchors/policy.md and https://dev.azure.com/acme/_git/policies; verify 200`, build the brief and verify its findings carry no `implementation_coupling`; rewrite it to call a function whose name opens with an underscore and verify 200, and verify `implementation_coupling` is present @integration
- PROOF-38 (RULE-26): Mark `test_valid_credentials_return_200` and a second test `test_a_token_comes_back` with `PROOF-1`, write both into the record, and build the brief; verify the first entry's body holds `def test_valid_credentials_return_200` and `== 200` and not `def test_a_token_comes_back`, and the second entry's body holds `def test_a_token_comes_back` and `token` and not `def test_valid_credentials_return_200` @integration
- PROOF-39 (RULE-26): Write the second test so that it asserts nothing; verify `no_assertion` is among the second entry's findings and not among the first's @integration
- PROOF-40 (RULE-26): Write a third name `test_renamed_away` into the record for `PROOF-1` that the file no longer holds; verify its body is empty while the other two still show their own source @integration
- PROOF-41 (RULE-26): Read the names a record carries, `Acme.LoginTests.Denied(user: "x")`, `test_found[jest-[proof:f:PROOF-1:RULE-1]]`, `TestLogin::test_found` and `works [proof:login:PROOF-1:RULE-1]` against the source names `Allowed`, `Denied`, `test_found` and `works [proof:login:PROOF-1:RULE-1]`; verify each finds its own source name and nothing else, and `test_gone` finds none
- PROOF-42 (RULE-27): Write the brief for `RULE-1`, then write a copy whose `generated_at` and `record` differ; verify the JSON on disk is byte for byte the first write @integration
- PROOF-43 (RULE-27): Write the brief for `RULE-1`, then write a copy carrying the observation `PROOF-1 never names the token.`; verify the JSON on disk now carries that sentence and reads settled @integration
- PROOF-44 (RULE-15): Build the model prompt for a high-risk rule; verify it holds `settled: yes`, `one line per observation`, `Do not recommend a change` and `do not grade the rule` @integration
- PROOF-45 (RULE-21): Write briefs with no list named in a project at gate `strong` whose only record a person committed; verify nothing is written, because a developer record does not count there @integration
