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
> Highest-Rule: 42
> Highest-Proof: 107

## Rules

- RULE-1: The audit reads a rule that is its feature's own, has at least one proof with a test, whose passed cell reads `passed` and that has no audit entry for its current rule, proof and test, or whose feature's code changed since that entry, and reading again ignores an existing entry
- RULE-2: The prompt is `references/review_criteria.md` verbatim, then the rule's text, its proofs, the source of each test and each finding of the spot tests and the planted bugs
- RULE-3: The call is `claude -p --output-format json` with the prompt written to its standard input, which is closed after the prompt, and never on the command line, and it is given 300 seconds
- RULE-4: One call is made per rule, each rule is asked about exactly once, and the answers come back in the rules' order
- RULE-6: Each answer names the model the command's JSON reports, the one that wrote the most where several are named, or `unknown` where none is, and carries the sha256 of the criteria as they were sent
- RULE-11: The test source is read out of JavaScript and TypeScript by balancing the brackets of the test's call, with strings, comments and regex literals stepped over, so a nested options object, an apostrophe in a title, a regex literal, a comment or a division never cuts a body short or drops a test
- RULE-12: Reading a rule, asking the model and printing the result write no file anywhere under `.purlin/`
- RULE-33: A rule's verdict comes from the spot tests and the planted bugs alone: `weak` when a spot test fires on one of its tests or a planted bug survives, else `strong` when every planted bug was caught or not made
- RULE-35: The audit's last line is `The audit found <s> of <n> rules strong (<p>%).`, counted over the rules that pass their tests, a rule with a hand check counted where it also has a tested proof
- RULE-36: A proof whose test and whose feature's code are unchanged since its last planted bug keeps that bug's result, and no bug is planted for it again
- RULE-37: No bug is planted for a proof of an anchor's rule; the rule's verdict comes from the spot tests alone
- RULE-38: The model's answer is written into the rule's audit entry as `explanation`, one sentence per line starting `- `, beside the `findings` it explains, and the lines under `notes:` are its notes; the answer sets no verdict
- RULE-39: When the model cannot be reached, because `claude` is not on the path, exits with an error or runs past its 300 seconds, no explanation is recorded and the answer is only the reason: `claude is not on PATH`, `claude exited with an error` or `claude timed out after <n> s`
- RULE-40: What the audit reads for a rule names each marked test's file, its name and its own source, matched by the name the runner records; a test whose source cannot be found shows none rather than another test's
- RULE-41: Each refusal of `ai_audit.py` names what is wrong, and the command or file that fixes it where there is one, and writes nothing: an unknown option, a missing `--feature` or a `--project-root` that is not a folder exits 2; an unknown feature or rule, or an unreadable `.purlin/config.json`, exits 1
- RULE-42: `ai_audit.py --feature <name>` prints, for the rule named with `--rule` or for every rule of the feature, its proofs, each test or `No test yet. Run purlin:build <feature>.`, and what the last audit found with the model and the time that read it, and starts no `claude`

## Proof

- PROOF-4 (RULE-1): `RULE-2` passes and carries an audit entry reading `strong`, recorded for its current text, proof, test and code; the audit does not read it
- PROOF-103 (RULE-1): `RULE-2` carries an audit entry; a line of `src/login.py`, a file its feature covers, is changed from `return 401` to `return 403 if locked else 401` and its test passes again; the audit reads it
- PROOF-51 (RULE-1): `RULE-2` passes and carries an audit entry for its current text, proof and test; asked to read again, the audit reads it
- PROOF-11 (RULE-2): The prompt for `RULE-2` begins with the text of `references/review_criteria.md`, byte for byte; after it come `login RULE-2`, the rule's text, its proof `POST /login with a bad password; verify 401 and the body "denied"`, the test `test_a_bad_password_is_denied` and its line `assert login("ada", "wrong") == 401`
- PROOF-106 (RULE-2): The spot tests found `tests/test_login.py::test_a_bad_password_is_denied: the test checks nothing.` for `RULE-2`; the prompt for `RULE-2` holds that line after the test's source
- PROOF-14 (RULE-3): The audit asks about `RULE-2` with `claude` found at `/bin/claude`; the program started is exactly `/bin/claude -p --output-format json`, it is given 300 seconds, the prompt is handed over as the whole of its standard input, and no other standard input is left open to it
- PROOF-82 (RULE-3): On Windows, with `claude.cmd` on the search path, the audit asks `claude` about `RULE-2`; it is started exactly once, with the arguments `-p`, `--output-format` and `json`, reads the whole question from its input, and the explanation reads `read to the end` @env(windows)
- PROOF-55 (RULE-4): The audit is handed `RULE-1` to `RULE-6`, and the later the rule, the sooner its answer comes back; each rule is asked about exactly once, and the answers come back in the rules' order, `saw RULE-1` first and `saw RULE-6` last
- PROOF-20 (RULE-6): `claude` answers the question about `RULE-2` with JSON naming the model `claude-opus-4-1-20250805`; the audit's answer names that model and carries the sha256 of the text of `references/review_criteria.md` it was sent
- PROOF-58 (RULE-6): `claude` answers the question about `RULE-2` with JSON that names no model; the audit's answer names the model `unknown`
- PROOF-21 (RULE-6): `claude` answers with JSON naming `claude-haiku-3-5` with 12 output tokens and then `claude-opus-4-1` with 900; the audit's answer names `claude-opus-4-1`
- PROOF-9 (RULE-11): A TypeScript test file holds a test that passes the options object `{ cwd: ".", encoding: "utf8" }` to a call and then checks `expect(out).toMatch(/./)`, then a second test; both are found, and the first's source holds `expect(out).toMatch` and stops before the second
- PROOF-67 (RULE-11): A TypeScript test file holds a test titled `cd's into a sibling`, then a second test; both are found, and the first's source holds `expect(1).toBe(1)` and stops before the second
- PROOF-10 (RULE-11): A TypeScript test file holds a test that divides by 2 on the line after `"a" +`, then a second test; both are found, and the first's source holds its `expect(` and stops before the second
- PROOF-72 (RULE-12): `claude` is asked about `RULE-2` and answers `- The test reads the status.`; afterwards every file under `.purlin/`, `.purlin/runtime/` included, holds the same bytes as before, and no file is added
- PROOF-73 (RULE-12): The command run for the feature `login` exits 0 and prints both rules; afterwards every file under `.purlin/`, `.purlin/runtime/` included, holds the same bytes as before, and no file is added
- PROOF-95 (RULE-33): The spot tests find `tests/test_login.py::test_a_bad_password_is_denied: the test checks nothing.` and the bug planted for `PROOF-2` is caught; the audit entry of `RULE-2` reads `weak`, with that sentence among its `findings`
- PROOF-96 (RULE-33): No spot test fires on the test of `RULE-2`, and the bug planted for `PROOF-2` survives; the audit entry reads `weak` with the finding `PROOF-2: the test still passes when src/login.py:12 reads "return 200"`
- PROOF-97 (RULE-33): No spot test fires on the tests of `RULE-2`, the bug planted for each proof is caught, and `claude` answers `- This rule is weak.`; the audit entry of `RULE-2` reads `strong`
- PROOF-99 (RULE-35): Five rules pass their tests; the audit finds four `strong` and one `weak`; its last line reads `The audit found 4 of 5 rules strong (80%).`
- PROOF-104 (RULE-35): Four rules pass their tests, three of them found `strong`, and a fifth rule's test fails; the audit's last line reads `The audit found 3 of 4 rules strong (75%).`
- PROOF-100 (RULE-36): A bug planted for `PROOF-2` was caught; only `RULE-2`'s text changes, so the audit reads the rule again; no bug is planted for `PROOF-2`, the model is asked for none, and its result still reads `caught`
- PROOF-102 (RULE-37): `login` is an anchor under `specs/_anchors/` whose `RULE-2` passes; the audit reads it, the model is asked for no planted bug, and the audit entry of `RULE-2` reads `strong` with no planted bug recorded
- PROOF-98 (RULE-38): The spot tests find `tests/test_login.py::test_a_bad_password_is_denied: the test checks nothing.` and `claude` answers `- The test calls login and reads no status.`; the entry's `findings` hold only the first sentence and its `explanation` only the second
- PROOF-38 (RULE-38): `claude` answers the question about `RULE-2` with `- The test reads the status.`, then `notes:` and `- PROOF-2 holds two cases.`; the explanation is `The test reads the status.` and the one note is `PROOF-2 holds two cases.`
- PROOF-23 (RULE-39): With the path set to an empty folder, so that no `claude` can be found, the audit is handed two rules; each answer is only the reason `claude is not on PATH`, and no `claude` is started
- PROOF-24 (RULE-39): `claude` exits with the code 1 when asked about `RULE-2`; the audit's answer is only the reason `claude exited with an error`, with no explanation
- PROOF-25 (RULE-39): With the limit lowered to 1 second and a `claude` that takes 3 seconds to answer, the audit's answer about `RULE-2` is only the reason `claude timed out after 1 s`
- PROOF-34 (RULE-40): The tests `test_valid_credentials_return_200` and `test_a_token_comes_back` in one file are both marked for `PROOF-1` and both passed; what the audit reads for `RULE-1` lists exactly those two, the first shown with its own source, `== 200`, and the second with its own, `token`, neither holding the other's
- PROOF-35 (RULE-40): The evidence names a third test for `PROOF-1`, `test_renamed_away`, which the test file no longer holds; what the audit reads for `RULE-1` shows no source under `test_renamed_away`, and still shows `def test_valid_credentials_return_200` under that test and `def test_a_token_comes_back` under that one
- PROOF-65 (RULE-40): A C# test file holds two tests marked for one proof, `Allowed` and `Denied`; the source read for the name a runner records as `Acme.LoginTests.Denied(user: "x")` is `Denied`'s own, not `Allowed`'s
- PROOF-74 (RULE-41): The command run with `--nope` exits 2 and prints `ai_audit.py: unexpected argument --nope`
- PROOF-76 (RULE-41): The command run for `--feature login --rule RULE-99`, a rule the spec of `login` does not declare, exits 1 and prints only `login RULE-99 is not a rule any spec has. Run purlin:status login to see its rules.`
- PROOF-81 (RULE-41): In a project whose `.purlin/config.json` holds a comma after its last setting, the command run for `--feature login` exits 1, prints only `.purlin/config.json cannot be read: <the JSON reader's message> at line <n>. Fix the file by hand; nothing ran and nothing was saved.`, and every file under `.purlin/` keeps its bytes
- PROOF-29 (RULE-42): The audit entry of `RULE-2` finds `PROOF-2 asserts the status but never the body the rule names.`; the command for that rule prints `login RULE-2`, its rule, proof and test line, `  Weak.`, the finding and `  Read by unknown at 2026-09-13T12:05:00Z.`, and no `Note:` line
- PROOF-87 (RULE-42): The one proof of `RULE-3` has no test marked for it; the command run for that rule prints, under `Test`, `  No test yet. Run purlin:build login.`
- PROOF-33 (RULE-42): The command run as its own process for `--feature login --rule RULE-1` exits 0 and prints `login RULE-1`, and no `claude` is started
