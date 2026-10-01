# Decision 121, lane `audit`: the report

Branch `lane/d121-audit`, cut from `main` at `fe512e267`. Nothing was pushed, no real `claude`
was started, no audit was run against this repository.

## Test numbers

`python3 -m pytest dev/test_ai_audit.py dev/test_ai_audit_tests_named.py dev/test_planted_bug.py dev/test_plain_checks.py -q`

| | Passed | Failed |
|---|---|---|
| Before, on `main` | 73 | 1, `ai_audit` PROOF-103, the red test the brief names |
| After | 91 | 0 |

17 tests added: 11 for `ai_audit` (PROOF-112 to 122), 4 for `planted_bug` (PROOF-16 to 19), 2 for
`plain_checks` (PROOF-31, 32). None deleted.

| Spec | Rules before, after | Proofs before, after | `Highest-Rule` | `Highest-Proof` |
|---|---|---|---|---|
| `ai_audit` | 17, 19 | 41, 52 | 45 | 122 |
| `planted_bug` | 9, 10 | 13, 17 | 13 | 19 |
| `plain_checks` | 8, 9 | 20, 22 | 10 | 32 |

The numbers the plan assumed were the tree's. No difference to report.

## Seen failing first

- `ai_audit` PROOF-103, on `main`'s code: `assert rule['audit']` failed with `assert None`, since
  the base commit hides an entry out of date. The test now reads the entry through
  `audit_run.audit_entry` and holds `out_of_date == ['code']`.
- `plain_checks` PROOF-32, on `main`'s code: the finding was
  `tests/test_intake.py::test_x: the proof expects is handed in; it is refused with and the test never checks it.`
- `planted_bug` PROOF-16, 17 and 18 and `ai_audit` PROOF-117 could not run on `main`'s code as
  written, because `break_proof` and the call changed shape. Each was seen to fail with its own
  fix alone taken out of the new code: the run before the bug, `not run`, the test-file refusal,
  and `claude gave no answer`.
- Every other new or reworded proof: the code was broken once on purpose and its test failed, in 31
  of 32 breaks. One did not fail: letting the not-found line repeat. The test of `plain_checks`
  PROOF-31 has one test whose source is missing, so it cannot print twice.

## What changed, by item

**The verdict (`ai_audit` RULE-33, 37, 43; plan 2.2).** `audit_run.verdict_of`: `weak` when a spot
test fired or a bug survived, else `strong` when one planted bug was caught, else
`spot-checked`. `audit_run.planted_bugs` builds one `no_bug` sentence for each proof no bug was
caught for, whatever the verdict. An anchor's rule and a proof tagged for another system get no
bug and are asked for none. A rule the model was not reached for is written with what the spot
tests and the kept bugs give, and is read again. Every rule read gets an entry.

**Which rules are read (`ai_audit` RULE-1).** `ai_audit.is_read` reads a rule with no entry, an
entry out of date, or a proof to plant for with no result under `breaks`. `rules_to_read` takes
the entry from `evidence.audit_entry` with the feature's `code` part, so it does not depend on
the one line of `payload._rule_entry` lane `surfaces` takes out. `code_changed` and its
`git diff` are deleted.

**One call per rule (`ai_audit` RULE-2, 3, 4, 44, 45; plan 2.4, K3, K7).** `COMMAND` and
`SYSTEM_PROMPT` are section 2.4's, flag for flag. `claude` is started in a new empty folder
`purlin-audit-*` under the system's temporary folder, with `DISABLE_PROMPT_CACHING=1`, and the
folder is removed when the audit ends. `model_prompt` builds K3's request; `read_reply` cuts the
reply. `bug_prompt`, `BUG_INSTRUCTION`, `ask_for_bug` and `ModelUnreachable` are deleted. The
order is the spot tests for every rule, the calls four at once, then each rule's bugs one at a
time.

**A `claude` that answers nothing (`ai_audit` RULE-39).** Empty output, output that is not JSON,
`is_error` true, or an empty `result` reads `claude gave no answer`.

**The planted bug (`planted_bug` RULE-3, 6, 12, 13).** `break_proof` takes the proof's part of the
reply and returns `cause`. `_run_tests` answers `pass`, `fail` or `not run`; only `fail` is
`caught`. The proof's tests run in the copy before the change, and unless they pass the result
is `not made`. A change to a file holding one of the proof's tests is refused. `break_proof` no
longer takes a snapshot: `audit_run.run` takes one before the first call and compares it after
each rule's bugs (`targeted_break.check_unchanged`). `break_proofs` is deleted.

**The entry (`K2`).** `code_hash` and `no_bug` are handed to `evidence_writer.audit_entry`.

**The lines printed (`ai_audit` RULE-35, 45).** The calls line first, the cost line, and the last
line from `summary.audit_line`. `EXPERIMENTAL = ''` in `audit_run.py` is printed first where the
coordinator fills it (plan 6.9).

**Spot test 6 (`plain_checks` RULE-6, 10).** `_BACKTICK_RE` pairs backticks left to right and an
empty pair names no value. A marked test whose source is not found is named once.

**`dev/fake_claude.py`.** Each call's line gains `cwd`, `listing` (what the folder held) and `env`.
`answers` takes `null` (a `no break` part for each proof asked for, and an empty reading, the
default), an object `{"PROOF-2": <part>, "reading": <lines>}`, or a string given as it is. New
settings `cost` and `writes`, and a helper `fake_claude.reply(parts, reading)`.

## One thing found on the way

The proof's tests now run twice in one copy. Python serves a cached `.pyc` when a source file
keeps its size and its modification time to the second, so a planted `return 401` to `return 200`
read `survived` where it was caught. `targeted_break._plant` now sets the changed file's time 2
seconds later than it was. No rule holds this; `ai_audit` PROOF-97 fails without it.

## Rules, word for word

`ai_audit`, reworded 1, 2, 3, 4, 33, 35, 37, 39, 43; new 44, 45:

- RULE-1: The audit reads a rule that is its feature's own, has at least one proof with a test, whose passed cell reads `passed`, and that has no audit entry, an entry out of date, or a proof it plants a bug for with no result recorded; reading again ignores an existing entry
- RULE-2: The request opens with `references/review_criteria.md` verbatim, then the rule's text, its proofs, the source of each test and each finding of the spot tests; where a bug is to be planted it names each such proof and holds the text of every file the feature's scope reaches, and of no other file
- RULE-3: The call is `claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt <the audit's own>`, started in an empty folder outside the project with `DISABLE_PROMPT_CACHING=1`, the request written to its standard input, which is then closed, and given 300 seconds
- RULE-4: One call is made per rule, holding its planted bugs and its reading together; each rule is asked about exactly once, four at once, and the answers come back in the rules' order
- RULE-33: A rule's verdict comes from the spot tests and the planted bugs alone: `weak` when a spot test fires on one of its tests or a planted bug survives; else `strong` when a planted bug was caught; else `spot-checked`; and the entry records under `no_bug` one sentence for each proof no bug was caught for
- RULE-35: The audit's last line is `The audit found <s> of <n> rules strong (<p>%): ` and the counts as the status words them, counted over the rules that pass their tests, a rule with a hand check counted where it also has a tested proof
- RULE-37: No bug is planted, and the model is asked for none, for a proof of an anchor's rule or a proof tagged `@env` for a system this machine is not, and the entry's `no_bug` says which
- RULE-39: When the model cannot be reached, because `claude` is not on the path, exits with an error, runs past its 300 seconds, or answers nothing or a JSON that reports an error, no explanation is recorded and the answer is only the reason: `claude is not on PATH`, `claude exited with an error`, `claude timed out after <n> s` or `claude gave no answer`
- RULE-43: When the model cannot be reached for a rule, the spot tests and the bugs kept from earlier audits set its verdict; a rule left `spot-checked` records `No bug was planted: the model could not be reached: <why>.`, and the audit prints `The model could not be reached: <why>. <n> rules are spot-checked alone. Run purlin:audit again.`, the middle sentence left out for none
- RULE-44: The reply holds one part per proof asked for, under `=== PROOF-N ===`, and the reading under `=== reading ===`; a proof whose part is missing or names no usable change has no bug planted, with the reason recorded, and the other proofs' bugs are planted
- RULE-45: Before its first call the audit prints `The audit reads <n> rules: <n> model calls.`, and after its last, where `claude` reported a cost, `The model was asked <n> times for <n> rules: $<total> in all, $<per rule> a rule.`, the sum of what each call reported

`planted_bug`, reworded 3, 6, 12; new 13:

- RULE-3: A test that runs and fails with the bug in place reads `caught`; a test that is skipped, is not collected or runs past its limit there reads `not run`, which is neither caught nor survived
- RULE-6: When a file of the project changes while the audit asks the model or plants a bug, the audit stops, prints `The audit stopped: <path> changed while the audit ran. Nothing in the project was written by the audit.`, writes no audit entry and exits 1
- RULE-12: A change that cannot be applied exactly once to a file the feature covers, a change to a file that holds one of the proof's tests, or an answer that names no change, is not applied and reads `not made` with its reason, and the proof's test is not run
- RULE-13: The proof's test is run in the copy before the bug is planted; where it does not pass there, no bug is planted and the result reads `not made` with the reason `the test does not pass in a copy of the project`

`plain_checks`, reworded 6; new 10:

- RULE-6: A test whose file holds none of the values its proof marks in backticks reads `<file>::<test>: the proof expects <value> and the test never checks it.`; a proof with no value in backticks, an empty pair of backticks, the same number written another way, or a value held in a data file the test's file names, is not flagged
- RULE-10: A marked test whose source cannot be found is named once, as `<file>::<test>: its source was not found, so the spot tests did not read it.`

## Proofs, word for word

`ai_audit`, reworded 14, 82, 99, 100, 102, 104, 108, 110; new 112 to 122. PROOF-109 stands as it
was. PROOF-104 is the one the plan left to the lane: the fourth rule reads `weak`.

- PROOF-14 (RULE-3): The audit asks about `RULE-2` with `claude` found at `/bin/claude`; the program started is exactly `/bin/claude -p --output-format json --max-turns 1 --tools "" --strict-mcp-config --safe-mode --setting-sources "" --disable-slash-commands --no-session-persistence --system-prompt` and the audit's system prompt, it is given 300 seconds, and the request is the whole of its standard input
- PROOF-82 (RULE-3): On Windows, with `claude.cmd` on the search path, the audit asks `claude` about `RULE-2`; it is started exactly once, its arguments beginning `-p`, `--output-format`, `json`, `--max-turns`, `1`, `--tools` and an empty argument, reads the whole question from its input, and the explanation reads `read to the end` @env(windows)
- PROOF-99 (RULE-35): Five rules pass their tests; the audit finds four `strong` and one `weak`; its last line reads `The audit found 4 of 5 rules strong (80%): 4 strong, 1 weak.`
- PROOF-100 (RULE-36): A bug planted for `PROOF-2` was caught; only `RULE-2`'s text changes, so the audit reads the rule again; the request asks for no bug, none is planted for `PROOF-2`, and its result still reads `caught`
- PROOF-102 (RULE-37): `login` is an anchor under `specs/_anchors/` whose `RULE-2` passes; the audit reads it, the request asks for no bug, and the entry of `RULE-2` reads `spot-checked` with the one `no_bug` sentence `No bug was planted: no bug is planted for an anchor's rule.`
- PROOF-104 (RULE-35): Four rules pass their tests, three of them found `strong` and one `weak`, and a fifth rule's test fails; the audit's last line reads `The audit found 3 of 4 rules strong (75%): 3 strong, 1 weak.`
- PROOF-108 (RULE-43): `claude` exits with the code 1 at every call and no spot test fires on the test of `RULE-2`, the one rule read; its entry reads `spot-checked`, and the audit prints `login RULE-2   spot-checked` and, once, `The model could not be reached: claude exited with an error. 1 rule is spot-checked alone. Run purlin:audit again.`
- PROOF-110 (RULE-43): `claude` exits with the code 1 at every call and the audit reads two rules that pass, with no spot test firing on either; both entries read `spot-checked`, the audit prints `The model could not be reached: claude exited with an error. 2 rules are spot-checked alone. Run purlin:audit again.` once, and its last line reads `The audit found 0 of 2 rules strong (0%): 0 strong, 2 spot-checked.`
- PROOF-112 (RULE-3): The audit asks about `RULE-2` of the project at `<root>`; `claude` is started in a folder that is neither `<root>` nor under it and holds no file, with `DISABLE_PROMPT_CACHING` reading `1`, and that folder is gone when the audit ends
- PROOF-113 (RULE-4): `RULE-1` has three proofs, each with a test and none with a planted bug on record; the audit reads `RULE-1`, and `claude` is started exactly `1` time, its request naming `PROOF-1`, `PROOF-2` and `PROOF-3`
- PROOF-114 (RULE-2): The project holds `.env` with `KEY=s3cret` and the scope of `login` names `src/login.py` alone; the request for `RULE-2` holds the text of `src/login.py` and does not hold `s3cret`
- PROOF-115 (RULE-36): A bug planted for `PROOF-2` was caught; the body of its test changes from `== 401` to `== 403`; the next request asks for a bug for `PROOF-2`, and the entry's `break_key` differs from the one before
- PROOF-116 (RULE-37): On a machine that is not Windows, `RULE-8` passes on a Windows result and its one proof, `PROOF-38`, is tagged `@env(windows)`; the audit reads it, the request asks for no bug, and the entry reads `spot-checked` with `No bug was planted: PROOF-38 needs Windows, and this machine is <its system>.`
- PROOF-117 (RULE-39): `claude` exits `0` and prints nothing at every call, and no spot test fires on the test of `RULE-2`; its entry reads `spot-checked`, and the audit prints `The model could not be reached: claude gave no answer. 1 rule is spot-checked alone. Run purlin:audit again.`
- PROOF-118 (RULE-33): No spot test fires on the test of `RULE-2`, and the model answers `no break: the proof names no value the code computes` for `PROOF-2`; the entry reads `spot-checked`, its `no_bug` exactly `No bug was planted: the model found no change that would break PROOF-2: the proof names no value the code computes.`
- PROOF-119 (RULE-43): A bug kept for `PROOF-2` reads `survived`, and `claude` exits `1` at every call; the audit entry of `RULE-2` reads `weak` with the finding `PROOF-2: the test still passes when src/login.py:12 reads "return 200"`
- PROOF-120 (RULE-44): `RULE-1` has `PROOF-1` and `PROOF-2`; the reply holds a part for `PROOF-1`, whose bug is caught, and none for `PROOF-2`; the entry reads `strong`, `PROOF-1` reads `caught`, and `no_bug` is exactly `No bug was planted: the model's answer for PROOF-2 could not be used: it holds none.`
- PROOF-121 (RULE-45): The audit reads 2 rules and each call reports `total_cost_usd` `0.05`; it prints `The audit reads 2 rules: 2 model calls.` before the first call and, after the last, `The model was asked 2 times for 2 rules: $0.10 in all, $0.05 a rule.`
- PROOF-122 (RULE-1): `RULE-2`'s entry reads `spot-checked` because the model could not be reached, and nothing has changed since; the audit run again, with a `claude` that answers, reads `RULE-2` and starts `claude` exactly `1` time

`planted_bug`, reworded 7; new 16 to 19:

- PROOF-7 (RULE-6): `claude`, as it answers, writes a line to `src/age.py` in the project; the audit prints `The audit stopped: src/age.py changed while the audit ran. Nothing in the project was written by the audit.`, exits `1`, and `.purlin/evidence/local/age.json` holds the bytes it held before
- PROOF-16 (RULE-13): The test of `PROOF-1` reads `data/built.json`, a file git ignores; the model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`; the result reads `not made` with the reason `the test does not pass in a copy of the project`, not `caught`
- PROOF-17 (RULE-3): The model answers `file: src/age.py`, `before:` `def age(`, `after:` `def age_(`, so `tests/test_age.py` can no longer be collected; the result reads `not run`, not `caught`
- PROOF-18 (RULE-12): The feature's `> Scope:` names `tests/test_age.py` and the model answers `file: tests/test_age.py`, `before:` `assert age(s) == 90`, `after:` `assert age(s) == 0`; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-19 (RULE-1): The test of `PROOF-1` runs past its limit with the bug in place; afterwards every file of the project holds the same bytes as before

`plain_checks`, new 31, 32:

- PROOF-31 (RULE-10): The evidence names `test_renamed_away` for `PROOF-1`, which `tests/test_login.py` no longer holds; the audit prints `tests/test_login.py::test_renamed_away: its source was not found, so the spot tests did not read it.` exactly once
- PROOF-32 (RULE-6): `PROOF-1` reads "an empty barcode `` is handed in; it is refused with `barcode is required`", and `tests/test_intake.py` holds `barcode is required`; nothing is found

Each is the plan's text. `ai_audit` PROOF-110 is 69 words as the plan words it, over the 60 the
brief sets; it was left as given.

The two Descriptions take the plan's sentences.

## Lines a person reads

From the plan, unchanged: every line of section 6.3, the `no_bug` sentences of K2, `claude gave
no answer`, `Spot-checked.`, `No audit has read this rule yet.`,
`<file>::<test>: its source was not found, so the spot tests did not read it.`, and
`<path> holds one of the proof's tests`.

Chosen by this lane:

- `Answer in this shape and with nothing else:` the request's last part where no bug is asked
  for. K3 says the shape is then the reading alone and gives no opening line.
- `the test does not pass in a copy of the project`: `planted_bug` RULE-13's reason, held in
  `targeted_break.BASELINE`; the `no_bug` sentence is K2's, naming the proof.
- Under a `spot-checked` rule with no `no_bug` sentence the line reads `The spot tests found
  nothing.`, with no space after it.
- The two notices of the spot tests, `... is not read in <language> tests.` and `... its source
  was not found ...`, are printed together, before the first rule's line. Section 6.3 lists the
  second after the rules.

## `references/review_criteria.md`, before and after

"Heuristic spot tests", the one sentence of check 6:

- Before: ``**Does not flag** a proof that names no value in backticks; the same number written another way (`90` and `90.0`); a value the test reads from a data file its own file names.``
- After: ``**Does not flag** a proof that names no value in backticks; an empty pair of backticks, which marks an empty value and names nothing to look for; the same number written another way (`90` and `90.0`); a value the test reads from a data file its own file names.``

No other sentence of that section changed. One of them is now out of step and was left, since the
section is the owner's: "A missed case is left to the planted bug, the audit's second step". The
planted bug is now the third step.

Outside that section:

| Where | Before | After |
|---|---|---|
| The opening | three steps: the spot tests, one planted bug per proof, the model's reading; "The model's prompt opens with this file" | the spot tests, one model call for the rule's bugs and its reading, each bug planted; "The model's request opens with this file" |
| "Which rules the audit reads", last bullet | no entry for its current rule, proofs and tests, or its code changed | no entry, an entry out of date, or a proof it plants a bug for with no result recorded |
| "The verdict" | `strong` when every planted bug was caught or not made; a rule the model was not reached for stays not audited | section 6.8's two paragraphs, word for word |
| "The planted bug" | one answer per proof; `Caught` on a failure, an error, a test not collected or a timeout; `PROOF-1: no bug was planted: <why>.` | K3's part under `=== PROOF-1 ===`; the tests run once before the change; `Caught`, `Not run` and `Not made` as 6.8 words them; `No bug was planted: <why>.`; no bug for a proof tagged for another system; "changes while the audit runs" |
| "What the model is sent" | the model reads each rule after the bugs, the verdict already set | 6.8's paragraph; `**The answer.**` is `**The reading.**`, under `=== reading ===` |
| "The call" | `claude -p --output-format json` | the command of 2.4, "The model is given no tools and is started in an empty folder, so it can read and change nothing.", the fourth reason `claude gave no answer`, and `2 rules are spot-checked alone` |
| "Anchors" | its verdict comes from the spot tests alone | its rule reads `spot-checked` where the spot tests find nothing |
| "What the audit reports" | `$1.87 in all, $0.16 a rule`; `The audit found 4 of 5 rules strong (80%).`; an entry for each rule read with the model reached | the calls line; the `no_bug` sentences; the cost line with no figure; `The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.`; an entry for each rule read, with `code` among its hashes and `no_bug` |

## Edits needed in files this lane does not own

1. `dev/test_evidence_writer.py`, `evidence_writer` PROOF-54 (lane `evidence`). It fails here on
   `assert entry['verdict'] == 'strong'`; the entry now reads `spot-checked`. For the model to
   answer `no break` for `PROOF-1`, install the fake with
   `answers=({'PROOF-1': NOTHING_TO_CHANGE},)`. The bare string is a reply with no part, which
   also gives `not made` and one `no_bug` sentence, but the sentence then reads
   `... the model's answer for PROOF-1 could not be used: it holds none.`
2. `dev/sign_project.py` and `dev/mcp_project.py`, `audit(...)` (base commit). They write an entry
   with no `breaks`. The audit now reads such a rule again, since a proof it plants a bug for has
   no result. A test of another lane that writes an entry this way and then runs the real audit
   will see the rule read. This lane's tests add the `breaks` themselves (`settle`, in
   `dev/test_ai_audit.py`). No edit is needed unless such a test exists.
3. `scripts/run/purlin_run.py`, the docstring of `_audit` (lane `evidence`): "or 1 where the audit
   stopped because the project changed while a planted bug ran" should read "while the audit
   ran".
4. Lane `words`: `skills/audit/SKILL.md` lines 57, 79 and 83 and `docs/running-and-evidence.md`
   lines 323 and 360 still quote `stay not audited` and `while a bug was planted`. Section 6 of
   the plan already gives their new words.
5. Lane `surfaces`: `ai_audit.verdict_lines` and `SPOT_CHECKED` word a `spot-checked` entry as
   `Spot-checked.` then `The spot tests found nothing. <sentences>`. `ai_audit.py --feature`
   shows it only once `payload.audit_summary` passes `spot-checked` and `no_bug` through.

## Left open

- **A junit `error` on the proof's own test reads `caught`.** The run reads a test case's
  `<error>` as `fail`, as it does everywhere, and `_run_tests` follows the plan: `caught` needs
  `fail`. A test that is skipped, is not collected or runs past its limit reads `not run`. If a
  setup error on a test that was collected should also read `not run`, that is one condition in
  `targeted_break._run_tests` and a change to how `reports.py` tells the two apart, which lane
  `evidence` owns.
- **`planted_bug`'s Description still opens "the audit's second step".** The plan rewords only its
  result sentence.
- **The cost of a call that reached nothing.** A call that exits with an error or gives no answer
  is counted in `The model was asked <n> times`, and its cost is added where the JSON reported
  one.
- **Windows.** `ai_audit` PROOF-82 passes here against the fake. Its `claude.cmd` path, with the
  empty arguments, runs only on the real Windows run of integration.
- No real audit was run and no cost was measured, as the brief says.
