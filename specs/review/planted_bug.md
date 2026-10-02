# Feature: planted_bug

> Description: One planted bug per proof, aimed past that proof's test, the audit's third step.
>   For a proof whose test or covered code changed since the audit last read it, the model is
>   shown the proof, its test and the code, and asked for the smallest change to one file the
>   feature covers after which the case the proof names gives a different result, choosing the
>   change that test is most likely to miss, and for the case the change breaks. The change is
>   made in a copy of the project, never in the project itself, and only the proof's own test
>   runs against it there; the copy is then deleted. A test that still passes reads `survived`,
>   with the change as the finding and the case the model named under it; a test that ran and
>   failed reads `caught`; a test that did not run reads `not run`; a change that cannot be made,
>   names no case or touches only a comment reads `not made`. A check before the model is asked
>   and after the last bug stops the audit if the project changed.
> Scope: scripts/review/targeted_break.py
> Stack: python/stdlib (subprocess, tempfile, hashlib, shutil)
> Highest-Rule: 20
> Highest-Proof: 40

## Rules

- RULE-1: The bug is planted in a copy of the project made from the files git lists as tracked or untracked and not ignored, and nothing in the project itself is written
- RULE-2: A test that still passes with the bug in place reads `survived`, with the finding `<PROOF-N>: the test still passes when <file>:<line> reads "<the changed line>"`
- RULE-3: A test that runs and fails with the bug in place reads `caught`; a test that is skipped, is not collected, runs past its limit or ends in an error its tool does not report as a failure there reads `not run`, which is neither caught nor survived, an error with the reason `the test ended in an error, not a failure`
- RULE-5: A write to a path outside the copy is refused, and the result reads `not made`
- RULE-6: When a file of the project changes while the audit asks the model or plants a bug, the audit stops, prints `The audit stopped: <path> changed while the audit ran. Nothing in the project was written by the audit.`, writes no audit entry and exits 1
- RULE-7: The copy is removed when the test passes, fails or runs past its limit
- RULE-8: No test of this feature reaches a real model: each runs with a `claude` that resolves under its own temporary folder
- RULE-10: Only the proof's own test runs against its planted bug, so a bug only another proof's test catches reads `survived`
- RULE-12: A change that cannot be applied exactly once to a file the feature covers, a change to a file that holds one of the proof's tests, or an answer that names no change, is not applied and reads `not made` with its reason, and the proof's test is not run
- RULE-13: The proof's test is run in the copy before the bug is planted; where it does not pass there, no bug is planted and the result reads `not made` with the reason `the test does not pass in a copy of the project`
- RULE-14: The file the bug changes is given a later time than it had, so the test, which already ran once in the copy, runs the changed code and not a compiled copy kept from that first run
- RULE-15: A part's `aim:` line is recorded as `past the test` or `plain`, and any other word, or a part with no `aim:` line, is recorded `plain`
- RULE-16: A part's `case:` line is kept as the model wrote it, with outer spaces cut and at most its first 300 characters
- RULE-17: A part that names a change and holds no `case:` line, or an empty one, is not planted: the result reads `not made` with the reason `the answer named no case of the proof`, the audit prints `No bug was planted: the model's answer for <PROOF-N> could not be used: the answer named no case of the proof.`, and the proof's test is not run
- RULE-18: A change that differs from the lines it replaces only in blank lines and comment lines is not planted: the result reads `not made` with the reason `the change touches only a comment`, the audit prints `No bug was planted: the model's answer for <PROOF-N> could not be used: the change touches only a comment.`, and the proof's test is not run; a comment line starts, after its indent, with `//` in any file or with `#` in a file ending `.py`, `.sh`, `.bash`, `.rb`, `.yml`, `.yaml` or `.toml`
- RULE-19: A change whose code lines differ from the lines they replace only in a comment at the line's end is not planted either, with the same reason, `the change touches only a comment`: that comment starts, after a space, at `#` in a file ending `.py`, `.sh`, `.bash`, `.rb`, `.yml`, `.yaml` or `.toml` and at `//` in any other file, and a line that holds a quotation mark before it is read as code throughout. The check is narrow on purpose: a `/* */` comment, a docstring, a `--` comment and a comment in any other kind of file are read as code, so a change to one is planted
- RULE-20: A part reads as naming no bug where its first line, or the first line after its `aim:` and `case:` lines, reads `no break: <why>`: the result reads `not made`, and its reason is the rest of that one line, whatever lines follow it

## Proof

- PROOF-1 (RULE-1): A bug is planted for `PROOF-1` in `src/age.py`; afterwards every file of the project holds the same bytes as before, and `git status --porcelain` prints what it printed before
- PROOF-19 (RULE-1): The test of `PROOF-1` runs past its limit with the bug in place; afterwards every file of the project holds the same bytes as before
- PROOF-2 (RULE-2): The model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`, line 12, and the test of `PROOF-1` still passes; the result reads `survived` and the finding `PROOF-1: the test still passes when src/age.py:12 reads "return 0"`
- PROOF-3 (RULE-3): The model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`, and the test of `PROOF-1` fails; the result reads `caught`
- PROOF-17 (RULE-3): The model answers `file: src/age.py`, `before:` `def age(`, `after:` `def age_(`, so `tests/test_age.py` can no longer be collected; the result reads `not run`, not `caught`
- PROOF-20 (RULE-3): A fixture every test of `tests/test_age.py` takes calls `minutes`, and the model answers `file: src/age.py`, `before:` `return 90`, `after:` `raise ValueError(stamp)`, so pytest reports the test of `PROOF-1` under `<error>`; the result reads `not run` with the reason `the test ended in an error, not a failure`, not `caught`
- PROOF-6 (RULE-5): The model answers `file: ../outside.py`; the result reads `not made`, and no file outside the copy is written
- PROOF-7 (RULE-6): `claude`, as it answers, writes a line to `src/age.py` in the project; the audit prints `The audit stopped: src/age.py changed while the audit ran. Nothing in the project was written by the audit.`, exits `1`, and `.purlin/evidence/local/age.json` holds the bytes it held before
- PROOF-13 (RULE-6): Bugs are planted for three proofs while nothing else touches the project; no line starting `The audit stopped:` is printed, and the audit exits `0`
- PROOF-8 (RULE-7): The test of `PROOF-1` fails with the bug in place; afterwards the temporary folder holds no folder whose name starts `purlin-break-`
- PROOF-14 (RULE-7): The test of `PROOF-1` runs past its limit with the bug in place; afterwards the temporary folder holds no folder whose name starts `purlin-break-`
- PROOF-9 (RULE-8): In every test of this feature, `claude` on the path resolves to a file under that test's own temporary folder before the first call
- PROOF-12 (RULE-10): The bug planted for `PROOF-1` makes the test of `PROOF-2` fail and leaves the test of `PROOF-1` passing; the result for `PROOF-1` reads `survived`
- PROOF-5 (RULE-12): The model answers `before:` `return days`, which `src/age.py` holds twice; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-15 (RULE-12): The model answers `file: README.md`, which the feature's `> Scope:` does not name; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-10 (RULE-12): The model answers `no break: the proof names no value the code computes`; the result reads `not made` with the reason `the proof names no value the code computes`
- PROOF-18 (RULE-12): The feature's `> Scope:` names `tests/test_age.py` and the model answers `file: tests/test_age.py`, `before:` `assert age(s) == 90`, `after:` `assert age(s) == 0`; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-16 (RULE-13): The test of `PROOF-1` reads `data/built.json`, a file git ignores; the model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`; the result reads `not made` with the reason `the test does not pass in a copy of the project`, not `caught`
- PROOF-21 (RULE-14): The model answers `file: src/age.py`, `before:` `return 90`, `after:` `return 91`, a change that keeps the file's size, and the test of `PROOF-1` expects `90`; the result reads `caught`, not `survived`
- PROOF-22 (RULE-15): The model's part for `PROOF-1` opens `aim: past the test`; after the audit, the bug's entry reads `aim` `past the test`
- PROOF-23 (RULE-15): The part for `PROOF-1` opens `aim: around the test` and the part for `PROOF-2` holds no `aim:` line; after the audit, each bug's entry reads `aim` `plain`
- PROOF-24 (RULE-16): The part for `PROOF-1` holds the line `case:   a stamp of 2026-01-01; the proof says 90; the changed code gives 0  `; after the audit, the bug's entry reads `case` `a stamp of 2026-01-01; the proof says 90; the changed code gives 0`
- PROOF-25 (RULE-16): The part's `case:` line holds 320 characters; after the audit, the bug's entry holds a `case` of its first 300
- PROOF-26 (RULE-17): The part for `PROOF-1` names `file: src/age.py`, `before:` `return days` and `after:` `return 0` and holds no `case:` line; the audit prints `age RULE-1   spot-checked` and under it `  The spot tests found nothing. No bug was planted: the model's answer for PROOF-1 could not be used: the answer named no case of the proof.`, and the test of `PROOF-1` runs in no copy of the project
- PROOF-27 (RULE-17): The part for `PROOF-1` holds the line `case:` with nothing after it; the bug's entry reads `not made` with the reason `the answer named no case of the proof`
- PROOF-28 (RULE-18): The model's change adds the one line `# off by one` above `return days` in `src/age.py`; the audit prints `  The spot tests found nothing. No bug was planted: the model's answer for PROOF-1 could not be used: the change touches only a comment.`, and the test of `PROOF-1` runs in no copy of the project
- PROOF-29 (RULE-18): The feature covers `src/age.js`, and the model's change adds the one line `// planted` to it; the bug's entry reads `not made` with the reason `the change touches only a comment`
- PROOF-30 (RULE-18): The feature covers `src/notes.txt`, and the model's change adds the one line `# 90` to it; the bug is planted, and its entry reads `survived`
- PROOF-31 (RULE-18): The model's change turns `return days` into the two lines `# planted` and `return 0`; the bug is planted, and its entry reads `caught`
- PROOF-32 (RULE-19): The model's change turns `return days` in `src/age.py` into `return days  # planted bug`; the audit prints `age RULE-1   spot-checked` and under it `  The spot tests found nothing. No bug was planted: the model's answer for PROOF-1 could not be used: the change touches only a comment.`, and the test of `PROOF-1` runs in no copy of the project
- PROOF-33 (RULE-19): The feature covers `src/age.js`, and the model's change turns `return 90;` in it into `return 90; // planted`; the bug's entry reads `not made` with the reason `the change touches only a comment`
- PROOF-34 (RULE-19): The model's change turns `if stamp == "":` into `if stamp == " #":`, and the test of `PROOF-1` expects an age of `0` for an empty stamp; the bug is planted, and its entry reads `caught`
- PROOF-35 (RULE-19): `src/age.py` ends `return days // 1`, and the model's change turns it into `return days // 2`; the bug is planted, and its entry reads `caught`
- PROOF-36 (RULE-19): The feature covers `src/age.js`, and the model's change turns `return 90;` in it into `return 90; /* planted */`; the bug is planted, and its entry reads `survived`
- PROOF-37 (RULE-18): The feature covers `src/limits.yml`, and the model's change adds the one line `# planted` above `oldest: 90` in it; the bug's entry reads `not made` with the reason `the change touches only a comment`
- PROOF-38 (RULE-18): The model's change adds one empty line above `return days` in `src/age.py` and nothing else; the bug's entry reads `not made` with the reason `the change touches only a comment`
- PROOF-39 (RULE-20): The part for `PROOF-1` reads `aim: plain` and under it `no break: the test checks the case and its result`; the audit prints `age RULE-1   spot-checked` and under it `  The spot tests found nothing. No bug was planted: the model found no change that would break PROOF-1: the test checks the case and its result.`
- PROOF-40 (RULE-20): The part for `PROOF-1` reads `no break: nothing here.` and under it a second line, `The code is a constant.`; the bug's entry reads `not made` with the reason `nothing here.`, and no line the audit prints holds `The code is a constant`
