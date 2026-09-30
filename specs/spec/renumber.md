# Feature: renumber

> Description: The renumbering helper `purlin:spec` runs when a spec writes a number twice or a
>   test comment names a proof whose wording moved to another id. It plans the edits to the spec
>   and to the test comments of this checkout, the line not already on the default branch moving,
>   prints the plan, and makes it only when run without `--dry-run`. It reads this checkout
>   alone, names comments on other branches without touching them, and commits nothing.
> Scope: scripts/spec/renumber.py
> Stack: python/stdlib (argparse, re, subprocess), git
> Highest-Rule: 9
> Highest-Proof: 12

## Rules

- RULE-1: A dry run prints the plan and changes no file, ending on `Nothing is changed: this is a dry run.`
- RULE-2: Of a number written twice, the line not on the default branch's copy moves to the next free number of its kind
- RULE-3: Where neither line is on the default branch's copy, or this checkout has no default branch, the later line in the file moves
- RULE-4: A committed test comment naming the moved id moves with it when it was written while the id read the moving line's text, and stays when it was written for the other line's text
- RULE-5: A test comment naming the moved id that is not committed is named in the plan and left as written
- RULE-6: A committed test comment whose proof's wording changed moves to the id of the same spec that now holds its old wording
- RULE-7: The spec's `> Highest-Rule:` or `> Highest-Proof:` line is raised to the new number
- RULE-8: A comment on another branch that names the moved id is named with that branch, the file and the line, and that branch is not changed
- RULE-9: A rule that moves takes with it each proof line naming it that is not on the default branch's copy, and a run without `--dry-run` makes the edits in the working tree and commits nothing

## Proof

- PROOF-1 (RULE-1): In a checkout whose `login` writes `PROOF-4` twice, `renumber.py login --dry-run` prints its plan and ends `Nothing is changed: this is a dry run.`; the spec and every test file read byte for byte as before
- PROOF-2 (RULE-2): After a merge, `login` writes `PROOF-4` twice, the branch's `B` on line 13 above `origin/main`'s `A` on line 14, with `> Highest-Proof: 4`; the plan reads `login: PROOF-4 at line 13 becomes PROOF-5: "B".`
- PROOF-3 (RULE-3): `login` writes `PROOF-7` twice, `X` on line 13 then `Y` on line 14, and `origin/main` holds neither; the plan reads `login: PROOF-7 at line 14 becomes PROOF-8: "Y". Neither line is on origin/main, so the later one moves.`
- PROOF-4 (RULE-3): In a checkout with no remote, `login` writes `PROOF-4` twice, `A` on line 13 then `B` on line 14; the plan reads `login: PROOF-4 at line 14 becomes PROOF-5: "B". This checkout has no copy of a default branch, so the later one moves.`
- PROOF-5 (RULE-4): After the merge of PROOF-2, a comment naming `login PROOF-4` committed on the branch while `PROOF-4` read `B` is planned as `tests/test_b.py:1 names login PROOF-4 and moves to PROOF-5.`, and after the run names `PROOF-5`
- PROOF-6 (RULE-4): After the merge of PROOF-2, a comment naming `login PROOF-4` committed on `origin/main` while `PROOF-4` read `A` is named in no line of the plan, and after the run still names `PROOF-4`
- PROOF-7 (RULE-5): After the merge of PROOF-2, a test file not yet committed names `login PROOF-4`; the plan reads `tests/test_new.py:1 names login PROOF-4 and is not committed, so it is not changed: check which proof it means.`, and after the run the file still names `PROOF-4`
- PROOF-8 (RULE-6): A comment naming `login PROOF-4` is committed while it reads `A`; the spec then rewords `PROOF-4` to `B` and writes `A` under `PROOF-6`; the plan reads `tests/test_login.py:1 names login PROOF-4 and moves to PROOF-6, where its old wording is now.`, and after the run the comment names `PROOF-6`
- PROOF-9 (RULE-7): After the merge of PROOF-2, the plan reads `login: > Highest-Proof: 4 becomes 5.`, and after the run the spec carries `> Highest-Proof: 5`
- PROOF-10 (RULE-8): After the merge of PROOF-2, `origin/qa/age-proofs` holds a comment naming `login PROOF-4`, not merged here; the plan reads `origin/qa/age-proofs names login PROOF-4 at tests/test_qa.py:1, which this checkout does not change. If it means the line that moves, move it to PROOF-5 on that branch.`, and after the run that branch names the same commit
- PROOF-11 (RULE-9): After a merge, `login` writes `RULE-2` twice, the branch's with its proof `PROOF-3` and `origin/main`'s with `PROOF-2`; the plan reads `login: PROOF-3 at line 16 now names RULE-3.` and names no line for `PROOF-2`, which after the run still names `RULE-2`
- PROOF-12 (RULE-9): After the merge of PROOF-2, a run without `--dry-run` ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`; HEAD names the commit it named before, and git lists the spec and `tests/test_b.py` as changed and not committed
