# Feature: planted_bug

> Description: One planted bug per proof, the audit's second step. For a proof whose test or
>   covered code changed since the audit last read it, the model is asked for the smallest change
>   to one file the feature covers that would break what the proof says. The change is made in a
>   copy of the project, never in the project itself, and only the proof's own test runs against
>   it there; the copy is then deleted. A test that still passes reads `survived`, with the change
>   as the finding; a test that fails reads `caught`; a change that cannot be made reads
>   `not made`. A check before and after each planted bug stops the audit if the project changed.
> Scope: scripts/review/targeted_break.py
> Stack: python/stdlib (subprocess, tempfile, hashlib, shutil)
> Highest-Rule: 12
> Highest-Proof: 15

## Rules

- RULE-1: The bug is planted in a copy of the project made from the files git lists as tracked or untracked and not ignored, and nothing in the project itself is written
- RULE-2: A test that still passes with the bug in place reads `survived`, with the finding `<PROOF-N>: the test still passes when <file>:<line> reads "<the changed line>"`
- RULE-3: A test that fails with the bug in place reads `caught`
- RULE-5: A write to a path outside the copy is refused, and the result reads `not made`
- RULE-6: When a file of the project changes while a bug is planted, the audit stops, prints `The audit stopped: <path> changed while a bug was planted. Nothing in the project was written by the audit.` and exits 1
- RULE-7: The copy is removed when the test passes, fails or runs past its limit
- RULE-8: No test of this feature reaches a real model: each runs with a `claude` that resolves under its own temporary folder
- RULE-10: Only the proof's own test runs against its planted bug, so a bug only another proof's test catches reads `survived`
- RULE-12: A change that cannot be applied exactly once to a file the feature covers, or an answer that names no change, is not applied and reads `not made` with its reason, and the proof's test is not run

## Proof

- PROOF-1 (RULE-1): A bug is planted for `PROOF-1` in `src/age.py`; afterwards every file of the project holds the same bytes as before, and `git status --porcelain` prints what it printed before
- PROOF-2 (RULE-2): The model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`, line 12, and the test of `PROOF-1` still passes; the result reads `survived` and the finding `PROOF-1: the test still passes when src/age.py:12 reads "return 0"`
- PROOF-3 (RULE-3): The model answers `file: src/age.py`, `before:` `return days`, `after:` `return 0`, and the test of `PROOF-1` fails; the result reads `caught`
- PROOF-6 (RULE-5): The model answers `file: ../outside.py`; the result reads `not made`, and no file outside the copy is written
- PROOF-7 (RULE-6): The model's answer, as it is given, writes a line to `src/age.py` in the project; the audit prints `The audit stopped: src/age.py changed while a bug was planted. Nothing in the project was written by the audit.` and exits `1`
- PROOF-13 (RULE-6): Bugs are planted for three proofs while nothing else touches the project; no line starting `The audit stopped:` is printed, and the audit exits `0`
- PROOF-8 (RULE-7): The test of `PROOF-1` fails with the bug in place; afterwards the temporary folder holds no folder whose name starts `purlin-break-`
- PROOF-14 (RULE-7): The test of `PROOF-1` runs past its limit with the bug in place; afterwards the temporary folder holds no folder whose name starts `purlin-break-`
- PROOF-9 (RULE-8): In every test of this feature, `claude` on the path resolves to a file under that test's own temporary folder before the first call
- PROOF-12 (RULE-10): The bug planted for `PROOF-1` makes the test of `PROOF-2` fail and leaves the test of `PROOF-1` passing; the result for `PROOF-1` reads `survived`
- PROOF-5 (RULE-12): The model answers `before:` `return days`, which `src/age.py` holds twice; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-15 (RULE-12): The model answers `file: README.md`, which the feature's `> Scope:` does not name; the result reads `not made` and the test of `PROOF-1` is not run
- PROOF-10 (RULE-12): The model answers `no break: the proof names no value the code computes`; the result reads `not made` with the reason `the proof names no value the code computes`
