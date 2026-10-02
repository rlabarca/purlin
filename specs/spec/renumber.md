# Feature: renumber

> Description: The renumbering helper `purlin:spec` runs when a spec writes a number twice or a
>   test comment names a proof whose wording, since its test was last changed, moved to another
>   id. It first resolves a conflict git left in the spec where both sides only added lines, then
>   plans the edits to the spec and to the test comments of this checkout, the line not already
>   on the default branch moving, prints the plan, asks, and makes it only on a yes. It reads
>   this checkout alone, names comments on other branches without touching them, and commits
>   nothing.
> Scope: scripts/spec/renumber.py
> Stack: python/stdlib (argparse, re, subprocess), git
> Highest-Rule: 13
> Highest-Proof: 21

## Rules

- RULE-1: A dry run prints the plan and changes no file, ending on `Nothing is changed: this is a dry run.`
- RULE-2: Of a number written twice, the line not on the default branch's copy moves to the next free number of its kind
- RULE-3: Where neither line is on the default branch's copy, or this checkout has no default branch, the later line in the file moves
- RULE-4: A committed test comment naming the moved id moves with it when it was written while the id read the moving line's text, and stays when it was written for the other line's text
- RULE-5: A test comment naming the moved id that is not committed is named in the plan and left as written
- RULE-6: A test comment whose proof's wording changed after its test was last changed moves to the id of the same spec that now holds the wording the proof had at that change
- RULE-7: The spec's `> Highest-Rule:` or `> Highest-Proof:` line is raised to the new number
- RULE-8: A comment on another branch that names the moved id is named with that branch, the file and the line, and that branch is not changed
- RULE-9: A rule that moves takes with it each proof line naming it that is not on the default branch's copy, and a run answered yes makes the edits in the working tree and commits nothing
- RULE-11: A run without `--dry-run` prints the plan, then asks `Do it? [y/N] `: `y`, `yes` or `--yes` makes the edits, and any other answer, an empty one or the end of input changes no file and ends on `Nothing is changed.`
- RULE-12: A conflict git left in the spec, whose two sides only add rule lines, proof lines or `> Highest-` lines, is resolved in the same plan and the same run, before the renumbering: both sides' lines are kept, a line both sides hold once, and of two `> Highest-` lines of one kind the higher stays
- RULE-13: A conflict in which a side changes or removes a line of the version both sides started from, or holds any other kind of line, or for which git holds no such version, is left as it is and named with its line and why

## Proof

- PROOF-1 (RULE-1): In a checkout whose `login` writes `PROOF-4` twice, `renumber.py login --dry-run` prints its plan and ends `Nothing is changed: this is a dry run.`; the spec and every test file read byte for byte as before
- PROOF-2 (RULE-2): After a merge, `login` writes `PROOF-4` twice, the branch's `B` on line 13 above `origin/main`'s `A` on line 14, with `> Highest-Proof: 4`; the plan reads `login: PROOF-4 at line 13 becomes PROOF-5: "B".`
- PROOF-3 (RULE-3): `login` writes `PROOF-7` twice, `X` on line 13 then `Y` on line 14, and `origin/main` holds neither; the plan reads `login: PROOF-7 at line 14 becomes PROOF-8: "Y". Neither line is on origin/main, so the later one moves.`
- PROOF-4 (RULE-3): In a checkout with no remote, `login` writes `PROOF-4` twice, `A` on line 13 then `B` on line 14; the plan reads `login: PROOF-4 at line 14 becomes PROOF-5: "B". This checkout has no copy of a default branch, so the later one moves.`
- PROOF-5 (RULE-4): After the merge of PROOF-2, a comment naming `login PROOF-4` committed on the branch while `PROOF-4` read `B` is planned as `tests/test_b.py:1 names login PROOF-4 and moves to PROOF-5.`, and after the run names `PROOF-5`
- PROOF-6 (RULE-4): After the merge of PROOF-2, a comment naming `login PROOF-4` committed on `origin/main` while `PROOF-4` read `A` is named in no line of the plan, and after the run still names `PROOF-4`
- PROOF-7 (RULE-5): After the merge of PROOF-2, a test file not yet committed names `login PROOF-4`; the plan reads `tests/test_new.py:1 names login PROOF-4 and is not committed, so it is not changed: check which proof it means.`, and after the run the file still names `PROOF-4`
- PROOF-8 (RULE-6): A test marked `login PROOF-4` is committed while it reads `A`; a later commit rewords `PROOF-4` to `B` and writes `A` under `PROOF-6`; the plan reads `tests/test_login.py:1 names login PROOF-4 and moves to PROOF-6, where its old wording is now.`, and after the run the comment names `PROOF-6`
- PROOF-9 (RULE-7): After the merge of PROOF-2, the plan reads `login: > Highest-Proof: 4 becomes 5.`, and after the run the spec carries `> Highest-Proof: 5`
- PROOF-10 (RULE-8): After the merge of PROOF-2, `origin/qa/age-proofs` holds a comment naming `login PROOF-4`, not merged here; the plan reads `origin/qa/age-proofs names login PROOF-4 at tests/test_qa.py:1, which this checkout does not change. If it means the line that moves, move it to PROOF-5 on that branch.`, and after the run that branch names the same commit
- PROOF-11 (RULE-9): After a merge, `login` writes `RULE-2` twice, the branch's with its proof `PROOF-3` and `origin/main`'s with `PROOF-2`; the plan reads `login: PROOF-3 at line 16 now names RULE-3.` and names no line for `PROOF-2`, which after the run still names `RULE-2`
- PROOF-12 (RULE-9): After the merge of PROOF-2, a run with `--yes` ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`; HEAD names the commit it named before, and git lists the spec and `tests/test_b.py` as changed and not committed
- PROOF-15 (RULE-11): After the merge of PROOF-2, a run with neither `--dry-run` nor `--yes` and nothing to answer from prints the plan, then `Do it? [y/N] `, ends `Nothing is changed.`, exits 0, and the spec and every test file read byte for byte as before
- PROOF-16 (RULE-11): After the merge of PROOF-2, a run answered `y` on its input ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`
- PROOF-17 (RULE-12): `main` and the branch `qa/login` each add a `RULE-9` line to `login`, `A` and `B`, and the merge stops on them at line 20; the dry run prints `login: the conflict at line 20 keeps both sides: 1 line from HEAD and 1 from qa/login.`, and after a run with `--yes` the spec holds no conflict line, `RULE-9: A` and `RULE-10: B`
- PROOF-18 (RULE-12): The same merge leaves `> Highest-Proof: 9` on `HEAD`'s side of a conflict at line 6 and `> Highest-Proof: 10` on the branch's; the dry run prints `login: the conflict at line 6 takes > Highest-Proof: 10, the higher of 9 and 10.`, and after a run with `--yes` the spec holds one `> Highest-Proof:` line
- PROOF-19 (RULE-12): A merge leaves one conflict in `login`, each side adding a proof under a number of its own; a run with `--yes` ends `Resolved 1 conflict in login. Nothing is committed.`, the spec holds both proofs and no conflict line, and git still lists the spec as not merged
- PROOF-20 (RULE-13): `main` rewords `RULE-2` to `A2` and the branch to `B2`, and the merge stops on that line at line 18; the plan prints `login: the conflict at line 18 is left: both sides changed RULE-2. Resolve it by hand, then run purlin:spec login again.`, and after a run with `--yes` those lines read as before
- PROOF-21 (RULE-13): A conflict at line 3 of `login` holds a `> Description:` line on each side; the plan prints `login: the conflict at line 3 is left: it holds a line that is not a rule, a proof or a > Highest- line. Resolve it by hand, then run purlin:spec login again.`
