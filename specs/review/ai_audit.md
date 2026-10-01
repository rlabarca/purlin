# Feature: ai_audit

> Description: The audit `purlin:audit` runs on each rule it reads, when a person asks, and
>   nothing waits on it. For each rule it runs the heuristic spot tests, then one planted bug
>   per proof, then the model's reading: a rule is `weak` when a spot test fires on one of its
>   tests or a planted bug survives, and `strong` when none fires and every planted bug was
>   caught or not made. The model's reading, one call per rule and four at once, sets the rule,
>   its proofs, the source of each test and the findings beside `references/review_criteria.md`
>   and becomes the explanation under the findings; it decides nothing. Each answer names the
>   model that gave it and a fingerprint of the criteria it was sent. The audit's last line is
>   the share of rules it found strong.
> Scope: scripts/review/audit_run.py, scripts/review/ai_audit.py, scripts/review/marked_tests.py
> Stack: python/stdlib (json, hashlib, subprocess, shutil, concurrent.futures)
> Highest-Rule: 37
> Highest-Proof: 107

## Rules

- RULE-1: The audit reads a rule that is its feature's own, has at least one proof with a test, whose passed cell reads `passed` and that has no audit entry for its current rule, proof and test, or whose feature's code changed since that entry, and reading again ignores an existing entry
- RULE-2: The prompt is `references/review_criteria.md` verbatim, then the rule's text, its proofs, the source of each test and each finding of the spot tests and the planted bugs, and it asks for what was observed rather than a recommendation, a grade or a score
- RULE-3: The call is `claude -p --output-format json` with the prompt written to its standard input, which is closed after the prompt, and never on the command line, and it is given 300 seconds
- RULE-4: One call is made per rule, each rule is asked about exactly once, and the answers come back in the rules' order
- RULE-5: The model's answer is read line by line: each line starting `- ` before any `notes:` line is one sentence of the explanation, in the order written, and the answer sets no verdict
- RULE-6: Each answer names the model the command's JSON reports, the one that wrote the most where several are named, or `unknown` where none is, and carries the sha256 of the criteria as they were sent
- RULE-7: With no `claude` on the path the model cannot be reached: no call is made and the answer is only the reason `claude is not on PATH`
- RULE-8: What the audit reads for a rule names each marked test's file, its name and its source
- RULE-9: A `@manual` proof's test entry reads `manual` true and names no test file and no source
- RULE-10: When several tests back one proof, each test shows its own source; a test whose source cannot be found shows none rather than another test's
- RULE-11: The test source is read out of JavaScript and TypeScript by balancing the brackets of the test's call, with strings, comments and regex literals stepped over, so a nested options object, an apostrophe in a title, a regex literal, a comment or a division never cuts a body short or drops a test
- RULE-12: Reading a rule, asking the model and printing the result write no file anywhere under `.purlin/`
- RULE-13: `ai_audit.py --help` exits 0, an unknown option or a missing `--feature` exits 2, a feature with no rule in the project exits 1, a rule the project does not hold prints only `<feature> <RULE-N> is not a rule any spec has. Run purlin:status <feature> to see its rules.` and exits 1, and the command calls no model
- RULE-14: `ai_audit.py --feature <name>` prints what the audit reads for one rule named with `--rule`, or for every rule of the feature without it
- RULE-16: The lines an answer holds under `notes:` are its notes, where the prompt asks for a proof longer than 60 words or holding more than one case
- RULE-17: For each rule `ai_audit.py` prints, it shows the rule, its proofs, each test or `No test yet. Run purlin:build <feature>.` where it has none, and what the last audit found, in the words every surface uses, then the model and the time that read it, then each note, starting `Note:`
- RULE-18: When `claude` exits with an error the model cannot be reached, and the answer is only the reason `claude exited with an error`
- RULE-19: When `claude` runs past its limit the model cannot be reached, and the answer is only the reason `claude timed out after <n> s`
- RULE-21: When `.purlin/config.json` cannot be read, `ai_audit.py` prints the sentence saying why, prints no rule, writes nothing and exits 1
- RULE-29: `ai_audit.py` run with a `--project-root` that is not a directory prints `ai_audit.py: <path> is not a directory.` and exits 2
- RULE-30: The prompt of an anchor's rule ends on `Anchor: its rules cover the whole project, so its tests must check the whole project.`
- RULE-32: Four calls run at once, or as many as there are rules when there are fewer, and no setting changes the number
- RULE-33: A rule's verdict comes from the spot tests and the planted bugs alone: `weak` when a spot test fires on one of its tests or a planted bug survives, else `strong` when every planted bug was caught or not made
- RULE-34: The model's reading of a rule is written into its audit entry as `explanation`, beside the `findings` it explains
- RULE-35: The audit's last line is `The audit found <s> of <n> rules strong (<p>%).`, counted over the rules that pass their tests, a rule with a hand check counted where it also has a tested proof
- RULE-36: A proof whose test and whose feature's code are unchanged since its last planted bug keeps that bug's result, and no bug is planted for it again
- RULE-37: No bug is planted for a proof of an anchor's rule; the rule's verdict comes from the spot tests alone

## Proof

- PROOF-1 (RULE-1): `RULE-2` has one proof, its test passed, so its passed cell reads `passed`, and it has no audit entry; the audit reads it
- PROOF-2 (RULE-1): The test of `RULE-2` failed, so its passed cell reads `failed`; the audit does not read it
- PROOF-48 (RULE-1): The one proof of `RULE-2` is tagged `@manual`, its passed cell reads `passed` and it has no audit entry; the audit does not read it
- PROOF-49 (RULE-1): `login` is an anchor under `specs/_anchors/` whose two rules pass with no audit entry, beside the feature `portal`; the audit reads each of the two once, as a rule of `login`
- PROOF-4 (RULE-1): `RULE-2` passes and carries an audit entry reading `strong`, recorded for its current text, proof, test and code; the audit does not read it
- PROOF-51 (RULE-1): `RULE-2` passes and carries an audit entry for its current text, proof and test; asked to read again, the audit reads it
- PROOF-52 (RULE-1): `RULE-2` carries an audit entry; its text is changed from `return 401 and the body` to `return 401 with the body` and its test passes again; it now carries no audit entry and the audit reads it
- PROOF-53 (RULE-1): `RULE-2` carries an audit entry; its proof is changed from `verify 401 and the body "denied"` to `verify 401 and the body reads "denied"` and its test passes again; it now carries no audit entry and the audit reads it
- PROOF-54 (RULE-1): `RULE-2` carries an audit entry; its test's line is changed from `login("ada", "wrong")` to `login("ada", "bad")` and passes again; the rule now carries no audit entry and the audit reads it
- PROOF-103 (RULE-1): `RULE-2` carries an audit entry; a line of `src/login.py`, a file its feature covers, is changed from `return 401` to `return 403 if locked else 401` and its test passes again; the audit reads it
- PROOF-11 (RULE-2): The prompt for `RULE-2` begins with the text of `references/review_criteria.md`, byte for byte; after it come `login RULE-2`, the rule's text, its proof `POST /login with a bad password; verify 401 and the body "denied"`, the test `test_a_bad_password_is_denied` and its line `assert login("ada", "wrong") == 401`
- PROOF-106 (RULE-2): The spot tests found `tests/test_login.py::test_a_bad_password_is_denied: the test checks nothing.` for `RULE-2`; the prompt for `RULE-2` holds that line after the test's source
- PROOF-12 (RULE-2): The prompt for `RULE-2` asks for what was observed and bars a recommendation, a grade and a score: it holds `one line per observation`, `Do not recommend a change`, `do not grade the rule` and `do not score it`
- PROOF-13 (RULE-3): The audit asks `claude` about `RULE-2`; `claude` is started exactly once, with exactly the arguments `-p`, `--output-format` and `json`, none of which holds the rule's text; it reads the whole prompt from its standard input, to the end, and the explanation reads `read to the end`
- PROOF-14 (RULE-3): The audit asks about `RULE-2` with `claude` found at `/bin/claude`; the program started is exactly `/bin/claude -p --output-format json`, it is given 300 seconds, the prompt is handed over as the whole of its standard input, and no other standard input is left open to it
- PROOF-82 (RULE-3): On Windows, with `claude.cmd` on the search path, the audit asks `claude` about `RULE-2`; it is started exactly once, with the arguments `-p`, `--output-format` and `json`, reads the whole question from its input, and the explanation reads `read to the end` @env(windows)
- PROOF-55 (RULE-4): The audit is handed `RULE-1` to `RULE-6`, and the later the rule, the sooner its answer comes back; each rule is asked about exactly once, and the answers come back in the rules' order, `saw RULE-1` first and `saw RULE-6` last
- PROOF-17 (RULE-5): `claude` answers the question about `RULE-2` with the one line `- The test reads the status and never the body.`; the answer's explanation is exactly `The test reads the status and never the body.`, and it carries no verdict
- PROOF-18 (RULE-5): `claude` answers the question about `RULE-2` with `- The test reads the status.` and then `- The body is never read.`; the explanation holds exactly those two sentences, `The test reads the status.` first
- PROOF-20 (RULE-6): `claude` answers the question about `RULE-2` with JSON naming the model `claude-opus-4-1-20250805`; the audit's answer names that model and carries the sha256 of the text of `references/review_criteria.md` it was sent
- PROOF-58 (RULE-6): `claude` answers the question about `RULE-2` with JSON that names no model; the audit's answer names the model `unknown`
- PROOF-21 (RULE-6): `claude` answers with JSON naming `claude-haiku-3-5` with 12 output tokens and then `claude-opus-4-1` with 900; the audit's answer names `claude-opus-4-1`
- PROOF-59 (RULE-6): `claude` answers with JSON naming `claude-opus-4-1` with 900 output tokens and then `claude-haiku-3-5` with 12; the audit's answer names `claude-opus-4-1`
- PROOF-60 (RULE-6): `claude` answers with JSON naming `claude-opus-4-1` with 12 output tokens and then `claude-haiku-3-5` with 900; the audit's answer names `claude-haiku-3-5`
- PROOF-61 (RULE-6): `claude` answers with JSON whose top-level `model` is `claude-x-1`; the audit's answer names `claude-x-1`
- PROOF-23 (RULE-7): With the path set to an empty folder, so that no `claude` can be found, the audit is handed two rules; each answer is only the reason `claude is not on PATH`, and no `claude` is started
- PROOF-24 (RULE-18): `claude` exits with the code 1 when asked about `RULE-2`; the audit's answer is only the reason `claude exited with an error`, with no explanation
- PROOF-25 (RULE-19): With the limit lowered to 1 second and a `claude` that takes 3 seconds to answer, the audit's answer about `RULE-2` is only the reason `claude timed out after 1 s`
- PROOF-83 (RULE-19): On Windows, with the limit lowered to 1 second and a `claude` that takes 3 seconds to answer, the audit's answer about `RULE-2` is only the reason `claude timed out after 1 s` @env(windows)
- PROOF-5 (RULE-8): In a project whose evidence names the test `test_valid_credentials_return_200` for `RULE-1`, what the audit reads for `RULE-1` names the file `tests/test_login.py`, that test, and carries its line `assert login("ada", "secret") == 200`
- PROOF-6 (RULE-9): The proof of `RULE-1` is tagged `@manual` while the project's test file still holds a test marked for that proof; what the audit reads for `RULE-1` has a test entry reading `manual` true, with no test file and no source
- PROOF-34 (RULE-10): The tests `test_valid_credentials_return_200` and `test_a_token_comes_back` in one file are both marked for `PROOF-1` and both passed; what the audit reads for `RULE-1` lists exactly those two, the first shown with its own source, `== 200`, and the second with its own, `token`, neither holding the other's
- PROOF-35 (RULE-10): The evidence names a third test for `PROOF-1`, `test_renamed_away`, which the test file no longer holds; what the audit reads for `RULE-1` shows no source under `test_renamed_away`, and still shows `def test_valid_credentials_return_200` under that test and `def test_a_token_comes_back` under that one
- PROOF-36 (RULE-10): A Python test file holds two tests marked for one proof, `test_found` and `test_other`; the source read for the name a runner records as `test_found[case-1]` is `test_found`'s own, not `test_other`'s
- PROOF-64 (RULE-10): A Python test file holds two tests marked for one proof, `test_found` and `test_other`; the source read for the name a runner records as `TestLogin::test_found` is `test_found`'s own, not `test_other`'s
- PROOF-65 (RULE-10): A C# test file holds two tests marked for one proof, `Allowed` and `Denied`; the source read for the name a runner records as `Acme.LoginTests.Denied(user: "x")` is `Denied`'s own, not `Allowed`'s
- PROOF-66 (RULE-10): A TypeScript test file holds two tests marked for one proof, `works` and `refuses`; the source read for the name a runner records as `login > works` is `works`'s own, not `refuses`'s
- PROOF-9 (RULE-11): A TypeScript test file holds a test that passes the options object `{ cwd: ".", encoding: "utf8" }` to a call and then checks `expect(out).toMatch(/./)`, then a second test; both are found, and the first's source holds `expect(out).toMatch` and stops before the second
- PROOF-67 (RULE-11): A TypeScript test file holds a test titled `cd's into a sibling`, then a second test; both are found, and the first's source holds `expect(1).toBe(1)` and stops before the second
- PROOF-10 (RULE-11): A TypeScript test file holds a test that divides by 2 on the line after `"a" +`, then a second test; both are found, and the first's source holds its `expect(` and stops before the second
- PROOF-68 (RULE-11): A TypeScript test file holds a test that builds the pattern `/[/)}"']+/g`, then a second test; both are found, and the first's source holds its `expect(` and stops before the second
- PROOF-69 (RULE-11): A TypeScript test file holds a test that builds the pattern `/\/)}/`, then a second test; both are found, and the first's source holds its `expect(` and stops before the second
- PROOF-70 (RULE-11): A TypeScript test file holds a test with a `}` and a `)` in a `//` comment and again in a `/* */` comment, then a second test; both are found, and the first's source holds its `expect(` and stops before the second
- PROOF-71 (RULE-11): A TypeScript test file holds two one-line tests, the first dividing `4 / 2` and the second `8 / 4`; both are found, and each one's source holds its own `expect(` and not the other's
- PROOF-27 (RULE-12): What the audit reads for `RULE-2` is taken; afterwards every file under `.purlin/`, `.purlin/runtime/` included, holds the same bytes as before, and no file is added
- PROOF-72 (RULE-12): `claude` is asked about `RULE-2` and answers `- The test reads the status.`; afterwards every file under `.purlin/`, `.purlin/runtime/` included, holds the same bytes as before, and no file is added
- PROOF-73 (RULE-12): The command run for the feature `login` exits 0 and prints both rules; afterwards every file under `.purlin/`, `.purlin/runtime/` included, holds the same bytes as before, and no file is added
- PROOF-30 (RULE-13): The command run with `--help` exits 0 and prints its usage, `ai_audit.py --feature <f> [--rule RULE-N] [--project-root DIR]`
- PROOF-74 (RULE-13): The command run with `--nope` exits 2 and prints `ai_audit.py: unexpected argument --nope`
- PROOF-75 (RULE-13): The command run with no argument exits 2 and prints `ai_audit.py: --feature is required.`
- PROOF-31 (RULE-13): The command run for the feature `nothing`, which no spec declares, exits 1 and prints `audit: no rule of nothing is in this project.`
- PROOF-76 (RULE-13): The command run for `--feature login --rule RULE-99`, a rule the spec of `login` does not declare, exits 1 and prints only `login RULE-99 is not a rule any spec has. Run purlin:status login to see its rules.`
- PROOF-33 (RULE-13): The command run as its own process for `--feature login --rule RULE-1` exits 0 and prints `login RULE-1`, and no `claude` is started
- PROOF-7 (RULE-13): What the audit reads for `RULE-99`, which the spec of `login` does not declare, is nothing at all, not a reading with an empty rule
- PROOF-32 (RULE-14): The command run for `--feature login --rule RULE-1` exits 0 and prints `login RULE-1` and not `login RULE-2`
- PROOF-78 (RULE-14): The command run for `--feature login` alone exits 0 and prints both `login RULE-1` and `login RULE-2`
- PROOF-29 (RULE-17): The audit entry of `RULE-2` finds `PROOF-2 asserts the status but never the body the rule names.`; the command for that rule prints `login RULE-2`, its rule, proof and test line, `  Weak.`, the finding and `  Read by unknown at 2026-09-13T12:05:00Z.`, and no `Note:` line
- PROOF-77 (RULE-17): With no audit entry for `RULE-2`, the command run for that rule prints, under `What the audit found`, `  No audit has read this rule's text, proof and test yet.` and no line naming who read it
- PROOF-80 (RULE-17): With an audit entry for `RULE-2` holding the finding `PROOF-2 asserts the status but never the body the rule names.` and the note `PROOF-2 holds two cases.`, the command run for that rule prints the finding's line, then `  Read by unknown at 2026-09-13T12:05:00Z.`, then `  Note: PROOF-2 holds two cases.`
- PROOF-84 (RULE-17): With an audit entry for `RULE-2` reading `strong` with no finding, the command run for that rule prints, under `What the audit found`, `  Strong. It found nothing.` and then `  Read by unknown at 2026-09-13T12:05:00Z.`
- PROOF-87 (RULE-17): The one proof of `RULE-3` has no test marked for it; the command run for that rule prints, under `Test`, `  No test yet. Run purlin:build login.`
- PROOF-88 (RULE-17): The one proof of `RULE-2` is tagged `@manual`; the command run for that rule prints, under `Test`, `  PROOF-2  manual`
- PROOF-37 (RULE-16): `claude` answers the question about `RULE-2` with `notes:` and the line `- PROOF-2 holds two cases.`; the audit's answer holds no explanation and the one note `PROOF-2 holds two cases.`
- PROOF-38 (RULE-16): `claude` answers the question about `RULE-2` with `- The test reads the status.`, then `notes:` and `- PROOF-2 holds two cases.`; the explanation is `The test reads the status.` and the one note is `PROOF-2 holds two cases.`
- PROOF-39 (RULE-16): The prompt for `RULE-2` shows a `notes:` line in the shape of the answer, and holds the words `a note, under notes:, for a proof longer than 60 words or one holding more than one case`
- PROOF-81 (RULE-21): In a project whose `.purlin/config.json` holds a comma after its last setting, the command run for `--feature login` exits 1, prints only `.purlin/config.json cannot be read: <the JSON reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and every file under `.purlin/` keeps its bytes
- PROOF-90 (RULE-29): The command run with a `--project-root` that names no folder on disk exits 2 and prints `ai_audit.py: <that path> is not a directory.`, with the path as it was given
- PROOF-91 (RULE-30): `login` is an anchor under `specs/_anchors/`; the last line of the prompt for `RULE-2` reads `Anchor: its rules cover the whole project, so its tests must check the whole project.`
- PROOF-94 (RULE-32): The audit is handed six rules, and each `claude` call takes 0.4 seconds to answer; `claude` is started 6 times, at most 4 calls run at the same moment, and 4 run together at one moment
- PROOF-101 (RULE-32): The audit is handed two rules, and each `claude` call takes 0.4 seconds to answer; `claude` is started 2 times, and the 2 calls run together at one moment
- PROOF-95 (RULE-33): The spot tests find `tests/test_login.py::test_a_bad_password_is_denied: the test checks nothing.` and the bug planted for `PROOF-2` is caught; the audit entry of `RULE-2` reads `weak`, with that sentence among its `findings`
- PROOF-96 (RULE-33): No spot test fires on the test of `RULE-2`, and the bug planted for `PROOF-2` survives; the audit entry reads `weak` with the finding `PROOF-2: the test still passes when src/login.py:12 reads "return 200"`
- PROOF-97 (RULE-33): No spot test fires on the tests of `RULE-2`, the bug planted for each proof is caught, and `claude` answers `- This rule is weak.`; the audit entry of `RULE-2` reads `strong`
- PROOF-107 (RULE-33): No spot test fires on the tests of `RULE-2`, the bug planted for `PROOF-2` is caught and the model makes no bug for `PROOF-3`; the audit entry of `RULE-2` reads `strong`
- PROOF-98 (RULE-34): The spot tests find `tests/test_login.py::test_a_bad_password_is_denied: the test checks nothing.` and `claude` answers `- The test calls login and reads no status.`; the entry's `findings` hold only the first sentence and its `explanation` only the second
- PROOF-99 (RULE-35): Five rules pass their tests; the audit finds four `strong` and one `weak`; its last line reads `The audit found 4 of 5 rules strong (80%).`
- PROOF-104 (RULE-35): Four rules pass their tests, three of them found `strong`, and a fifth rule's test fails; the audit's last line reads `The audit found 3 of 4 rules strong (75%).`
- PROOF-105 (RULE-35): Two rules pass their tests and are found `strong`, one of them holding a `@manual` proof beside a tested one; the audit's last line reads `The audit found 2 of 2 rules strong (100%).`
- PROOF-100 (RULE-36): A bug planted for `PROOF-2` was caught; only `RULE-2`'s text changes, so the audit reads the rule again; no bug is planted for `PROOF-2`, the model is asked for none, and its result still reads `caught`
- PROOF-102 (RULE-37): `login` is an anchor under `specs/_anchors/` whose `RULE-2` passes; the audit reads it, the model is asked for no planted bug, and the audit entry of `RULE-2` reads `strong` with no planted bug recorded
