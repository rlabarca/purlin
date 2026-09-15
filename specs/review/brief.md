# Feature: brief

> Description: The review brief a person reads before approving one rule. It
>   gathers evidence in layers, cheapest first, and stops when it has enough for
>   the rule's risk: the free checks on the proof text, the free checks on the
>   test body, the test strength from the latest record, then a model review.
>   The criteria are `references/review_criteria.md` and nothing else, so the
>   brief reports findings under the names that file gives and writes one of the
>   four verdicts it names. The brief lands beside the approval it informs,
>   named for the triple it was built from.
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
- RULE-8: A `@manual` proof carries a note where a test would be and no test file, because its evidence is the approver's own [risk: high] [origin: eng]
- RULE-9: The test strength comes off the feature's latest record and is shown against the configured minimum, reading `n/a` when no engine measured one [risk: medium] [origin: eng]
- RULE-10: A blocking finding on the proof text makes the verdict `rewrite the proof` and names the finding among the reasons [risk: high] [origin: eng]
- RULE-11: A finding on the test body, or a `@manual` proof, makes the verdict `needs a human` [risk: high] [origin: eng]
- RULE-12: An advisory `happy_path_only`, or a test strength below the minimum, makes the verdict `add a case` [risk: medium] [origin: eng]
- RULE-13: A rule with no finding anywhere and enough test strength gets the verdict `ready` [risk: medium] [origin: eng]
- RULE-14: The brief writes one of exactly four verdicts and no fifth word [risk: low] [origin: eng]
- RULE-15: The model prompt is `references/review_criteria.md` verbatim, followed by this rule's rule text, proof text, test bodies and test strength [risk: medium] [origin: eng]
- RULE-16: The model review runs only when the caller passes `--ai` and the rule needs one; without it, and with no model on the path, the brief records `not available` [risk: medium] [origin: eng]
- RULE-17: A model answer opening with one of the four verdicts decides the brief's verdict; an answer naming none decides nothing [risk: high] [origin: eng]
- RULE-18: A rule a designer owns shows the pinned mock beside the screenshot the test captured, and a missing screenshot makes the verdict `needs a human` [risk: medium] [origin: eng]
- RULE-19: The brief is written beside the approval it informs as `<RULE-N>.<hash8>.brief.json` carrying schema `purlin-brief/1`, with a text rendering of the same name beside it [risk: medium] [origin: eng]
- RULE-20: A brief written for the current triple puts its rule in Reviewed, and editing the rule, the proof or the test takes it back out [risk: high] [origin: eng]
- RULE-21: Writing briefs with no list named covers the review list the payload computed, and a narrower list covers only what it names [risk: low] [origin: eng]
- RULE-22: The text rendering names the rule, its proofs and its verdict, and carries no emoji [risk: low] [origin: eng]
- RULE-23: `brief.py --help` exits 0, an unknown option or a missing `--feature` exits 2, and a feature with no rule in the project exits 1 [risk: low] [origin: eng]
- RULE-24: `brief.py --feature <name>` with no `--rule` builds, prints and writes a brief for every rule of that feature [risk: low] [origin: eng]
- RULE-25: A name that opens with an underscore reaches the brief as `implementation_coupling` unless it follows a `/`, so a path or URL segment such as `specs/_anchors/` or `/_git/` is not read as a private symbol [risk: medium] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Build the brief for a `[risk: low]` rule in a recorded project; verify its layers are exactly `proof text` and `test body` @integration
- PROOF-2 (RULE-1): Build the brief for that same low-risk rule; verify its test strength is `none` because the strength layer did not run @integration
- PROOF-3 (RULE-2): Retag the rule `[risk: medium]`, run the tests and write a record, then build the brief; verify its layers are `proof text`, `test body`, `test strength` and nothing after @integration
- PROOF-4 (RULE-3): Build the brief for a `[risk: high]` rule; verify its layers are `proof text`, `test body`, `test strength`, `model review` in that order @integration
- PROOF-5 (RULE-4): Build a brief for `RULE-99`, which the spec does not declare; verify nothing comes back @integration
- PROOF-6 (RULE-5): Write a proof reading `The login works correctly`, then build the brief; verify its findings carry both `no_expected_value` and `vague_verb` @integration
- PROOF-7 (RULE-6): Edit the marked test so it calls the code and asserts nothing, then build the brief; verify the test's findings are exactly `no_assertion` and that a reason is printed with it @integration
- PROOF-8 (RULE-7): Build the brief for a recorded rule; verify it names the file `tests/test_login.py`, the test `test_valid_credentials_return_200`, and shows the asserting line of that test's source @integration
- PROOF-9 (RULE-8): Retag the proof `@manual` and build the brief; verify the test entry names no file and its findings are exactly `manual` @integration
- PROOF-10 (RULE-9): Write a record whose test strength is 90 and build the brief for a high-risk rule; verify the brief reads 90 against a minimum of 50 @integration
- PROOF-11 (RULE-9): Write a record with no test strength and render the brief; verify the rendering reads `Test strength: n/a` @integration
- PROOF-12 (RULE-10): Build the brief for a rule whose proof text names no value; verify the verdict is `rewrite the proof` and a reason names `no_expected_value` @integration
- PROOF-13 (RULE-11): Edit the marked test to `assert True` and build the brief; verify the verdict is `needs a human` and a reason names the tautological assertion @integration
- PROOF-14 (RULE-11): Retag the proof `@manual` and build the brief; verify the verdict is `needs a human` @integration
- PROOF-15 (RULE-12): Build the brief for a rule proved only in the accepting direction; verify `happy_path_only` is among its findings and the verdict is `add a case` @integration
- PROOF-16 (RULE-12): Set the minimum test strength to 70, record 40, and build the brief; verify the verdict is `add a case` and a reason reads `40 percent` @integration
- PROOF-17 (RULE-13): Build the brief for a recorded high-risk rule with no finding; verify the verdict is `ready` @integration
- PROOF-18 (RULE-14): Read the four verdicts the module declares; verify they are `ready`, `add a case`, `rewrite the proof`, `needs a human` and that a built brief's verdict is one of them @integration
- PROOF-19 (RULE-15): Build the model prompt for a high-risk rule; verify it opens with `references/review_criteria.md` byte for byte and then names `RULE-2`, the rule text, the test `test_a_bad_password_is_denied` and `Test strength: 90 percent (minimum 70)` @integration
- PROOF-20 (RULE-16): Build the brief for a rule that needs a model review without passing `--ai`; verify the recorded review reads `not available` and the rendering still carries a `Model review` heading @integration
- PROOF-21 (RULE-16): With no `claude` on the path, build the brief with `--ai`; verify the recorded review reads `not available` @integration
- PROOF-22 (RULE-16): Build the brief for a low-risk rule with `--ai` and a probe that raises if the path is searched; verify no model is reached and the recorded review is `none` @integration
- PROOF-23 (RULE-17): Replace the model launch with an answer opening `add a case`; verify one `claude -p` call is made and the brief's verdict is `add a case` @integration
- PROOF-24 (RULE-17): Read the verdict out of the answers `It looks fine to me.`, `not available` and `Ready.`; verify the first two name nothing and the third names `ready`
- PROOF-25 (RULE-18): Write a mock at `designs/login/sign-in.png` and a screenshot for `PROOF-1`, then build the brief for an `[origin: design]` rule; verify both paths are shown and the pinned hash reads `3f2a1b0c9d8e7f6a` @integration
- PROOF-26 (RULE-18): Build the same design rule's brief with no screenshot on disk; verify the mock is shown as the glob `designs/login/*.png`, the screenshot list is empty and the verdict is `needs a human` @integration
- PROOF-27 (RULE-19): Write the brief for a rule; verify the path is `specs/auth/login.approvals/RULE-1.<hash8>.brief.json` for the rule's own triple, that a `.txt` rendering sits beside it, and that the JSON carries schema `purlin-brief/1` @integration
- PROOF-28 (RULE-20): Write the brief, read the rule's state and verify it is `Reviewed`; then edit the rule text and verify the state is no longer `Reviewed` @integration
- PROOF-29 (RULE-21): Write briefs with no list named in a project whose high-risk rule is on the review list; verify every path written ends `.brief.json` and one names `RULE-2` @integration
- PROOF-30 (RULE-21): Write briefs for the single pair `login RULE-1`; verify exactly 1 path comes back and it names `RULE-1` @integration
- PROOF-31 (RULE-22): Render the brief for a recorded rule; verify the text names `login RULE-2`, the rule text, `PROOF-2` and `Verdict: ready`, and carries no emoji or emoticon @integration
- PROOF-32 (RULE-23): Run the command with `--help`, with `--nope` and with no argument; verify the exit codes are 0, 2 and 2 @integration
- PROOF-33 (RULE-23): Run the command for the feature `nothing`, which no spec declares; verify it exits 1 @integration
- PROOF-34 (RULE-24): Run the command for `--feature login --rule RULE-1`; verify it exits 0, prints `login RULE-1` and a `Verdict:` line, and creates the `login.approvals` directory @integration
- PROOF-35 (RULE-24): Run the command for `--feature login` with no rule named; verify it exits 0 and prints both `login RULE-1` and `login RULE-2` @integration
- PROOF-36 (RULE-23): Run `brief.py` as a command in a separate process against a recorded project; verify it exits 0 and its output carries a `Verdict:` line @integration
- PROOF-37 (RULE-25): Write a proof reading `POST /login, then read specs/_anchors/policy.md and https://dev.azure.com/acme/_git/policies; verify 200`, build the brief and verify its findings carry no `implementation_coupling`; rewrite it to call a function whose name opens with an underscore and verify 200, and verify `implementation_coupling` is present @integration
