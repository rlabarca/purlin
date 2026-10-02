# Decision 122, lane `collision`: the report

Branch `lane/d122-collision`, cut from `main` at `e02c9b4f5`. Nothing was pushed, tagged or
signed, no model was reached and no audit was run against this repository.

## What was built

- `scripts/spec/renumber.py` resolves the conflict git left in a spec, then renumbers, in one
  plan and one run. `conflicts(lines, base)` reads each conflict as `both`, `highest` or `left`;
  `resolve(lines, found)` answers the spec's lines with the first two kinds resolved, each kept
  line with its number on disk; `plan` parses that text with `specs._parse_spec` and plans the
  renumbering over it, printing disk line numbers; `apply` writes the resolved lines, then the
  edits. The run stages nothing.
- `renumber.py` takes `--yes`. Without it and without `--dry-run` it prints the plan, asks
  `Do it? [y/N] ` on its input and changes nothing on any answer but `y` or `yes`.
- `scripts/mcp/purlin/drift.py`: `merge_in_progress(project_root)`; the view's key
  `merge_in_progress` and its second line while a merge is not committed; `numbers_twice` gives
  each rule's entry `follows`, and the view prints one line for each proof that follows.
  `renumber._moves` reads `follows` in place of finding the proofs itself.
- `dev/test_collaboration.py`: the first collision is left as git stopped it. Dana edits no
  conflict line; the status and drift send her to the renumbering, run with `--yes`, and her
  commit finishes the merge. The second collision is still resolved by hand, so both paths run.

## Test numbers

| File | Before, on `main` | After |
|---|---|---|
| `dev/test_renumber.py` | 12 passed | 19 passed |
| `dev/test_drift.py` | 35 passed | 37 passed |
| `dev/test_collaboration.py` | 1 passed | 1 passed |

9 tests added, none deleted. 2 tests changed for a reworded proof: `renumber` PROOF-12 and
`drift` PROOF-49.

| Spec | `Highest-Rule` before, after | `Highest-Proof` before, after | Rules added | Rules reworded | Proofs added | Proofs reworded |
|---|---|---|---|---|---|---|
| `renumber` | 10, 13 | 14, 21 | 11, 12, 13 | 9 | 15 to 21 | 12 |
| `drift` | 43, 45 | 88, 90 | 44, 45 | | 89, 90 | 49 |
| `collaboration` | 1, 1 | 1, 1 | | | | |

The numbers the plan assumed were the tree's. Nothing was deleted.

## Rules and proofs, word for word

Every line is the plan's (section 3). None is this lane's own.

### `renumber`

The Description's second sentence: `It first resolves a conflict git left in the spec where both
sides only added lines, then plans the edits to the spec and to the test comments of this
checkout, the line not already on the default branch moving, prints the plan, asks, and makes it
only on a yes.`

Reworded:

- RULE-9: A rule that moves takes with it each proof line naming it that is not on the default branch's copy, and a run answered yes makes the edits in the working tree and commits nothing
- PROOF-12 (RULE-9): After the merge of PROOF-2, a run with `--yes` ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`; HEAD names the commit it named before, and git lists the spec and `tests/test_b.py` as changed and not committed

Added:

- RULE-11: A run without `--dry-run` prints the plan, then asks `Do it? [y/N] `: `y`, `yes` or `--yes` makes the edits, and any other answer, an empty one or the end of input changes no file and ends on `Nothing is changed.`
- RULE-12: A conflict git left in the spec, whose two sides only add rule lines, proof lines or `> Highest-` lines, is resolved in the same plan and the same run, before the renumbering: both sides' lines are kept, a line both sides hold once, and of two `> Highest-` lines of one kind the higher stays
- RULE-13: A conflict in which a side changes or removes a line of the version both sides started from, or holds any other kind of line, or for which git holds no such version, is left as it is and named with its line and why
- PROOF-15 (RULE-11): After the merge of PROOF-2, a run with neither `--dry-run` nor `--yes` and nothing to answer from prints the plan, then `Do it? [y/N] `, ends `Nothing is changed.`, exits 0, and the spec and every test file read byte for byte as before
- PROOF-16 (RULE-11): After the merge of PROOF-2, a run answered `y` on its input ends `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.`
- PROOF-17 (RULE-12): `main` and the branch `qa/login` each add a `RULE-9` line to `login`, `A` and `B`, and the merge stops on them at line 20; the dry run prints `login: the conflict at line 20 keeps both sides: 1 line from HEAD and 1 from qa/login.`, and after a run with `--yes` the spec holds no conflict line, `RULE-9: A` and `RULE-10: B`
- PROOF-18 (RULE-12): The same merge leaves `> Highest-Proof: 9` on `HEAD`'s side of a conflict at line 6 and `> Highest-Proof: 10` on the branch's; the dry run prints `login: the conflict at line 6 takes > Highest-Proof: 10, the higher of 9 and 10.`, and after a run with `--yes` the spec holds one `> Highest-Proof:` line
- PROOF-19 (RULE-12): A merge leaves one conflict in `login`, each side adding a proof under a number of its own; a run with `--yes` ends `Resolved 1 conflict in login. Nothing is committed.`, the spec holds both proofs and no conflict line, and git still lists the spec as not merged
- PROOF-20 (RULE-13): `main` rewords `RULE-2` to `A2` and the branch to `B2`, and the merge stops on that line at line 18; the plan prints `login: the conflict at line 18 is left: both sides changed RULE-2. Resolve it by hand, then run purlin:spec login again.`, and after a run with `--yes` those lines read as before
- PROOF-21 (RULE-13): A conflict at line 3 of `login` holds a `> Description:` line on each side; the plan prints `login: the conflict at line 3 is left: it holds a line that is not a rule, a proof or a > Highest- line. Resolve it by hand, then run purlin:spec login again.`

### `drift`

Reworded:

- PROOF-49 (RULE-42): After a pull, the view carries exactly `anchors_behind`, `comments_changed`, `default_branch`, `lines`, `merge_in_progress`, `numbers_twice`, `proofs_added`, `proofs_changed`, `proofs_moved`, `rules_added`, `rules_changed` and `rules_removed`

Added:

- RULE-44: While a merge is in progress and not committed, the view's second line says so and what to do, and `merge_in_progress` is true
- RULE-45: Where a rule written twice moves, the view names each proof that follows it to the new number
- PROOF-89 (RULE-44): A merge of a branch stops on a conflict in `specs/auth/login.md` and is not committed; the view's second line reads `A merge is in progress and is not committed, so the range above stops before it. Resolve it and commit, then run purlin:drift again.`, and `merge_in_progress` is true
- PROOF-90 (RULE-45): After a merge, `login` writes `RULE-2` twice, the branch's with its proof `PROOF-3`; the view holds, directly after the line naming `RULE-2`, `login: PROOF-3 will name RULE-3.`

### `collaboration`

Not changed. RULE-1 and PROOF-1 still say what the test does.

## Seen failing first

Each test was written and run on `main`'s `renumber.py` and `drift.py` before the code changed.

- The fault itself, by hand, in the merge of the QA check (`main` adds `RULE-9` and `PROOF-9`;
  `qa/login` adds `RULE-9`, `PROOF-9` and `PROOF-10`): `main`'s script printed
  `Renumbered in login: 3 spec lines and 0 test comments. Nothing is committed.` and left all
  nine conflict lines, with `> Highest-Proof: 11` on `HEAD`'s side and a stale
  `> Highest-Proof: 10` on the branch's. This is finding 4.
- `renumber` PROOF-17: the dry run held no `keeps both sides` line; its lines were
  `login: RULE-9 at line 23 becomes RULE-10: "B".` and the rest of the old plan.
- `renumber` PROOF-18: the dry run held no `takes > Highest-Proof: 10` line, and read
  `login: > Highest-Proof: 9 becomes 11.`, the first side's stale number.
- `renumber` PROOF-15: the run renumbered unasked. Its last line was
  `Renumbered in login: 1 spec line and 1 test comment. Nothing is committed.` where the test
  expects `Do it? [y/N] ` and `Nothing is changed.`
- `renumber` PROOF-19: exit 2, `--yes` is no flag of `main`'s script.
- `renumber` PROOF-20: the plan read `login: RULE-2 at line 21 becomes RULE-3: "B2".`, moving a
  line inside the conflict, and held no `is left` line.
- `renumber` PROOF-21: the plan was `login: nothing to renumber.`
- `renumber` PROOF-16 passed on `main`'s code: that script renumbers whatever is on its input.
  It is the one new test not seen failing.
- `drift` PROOF-89: the second line was `1 rule changed: login RULE-1.`
- `drift` PROOF-90: the line after the one naming `RULE-2` was the `origin/main was last
  fetched` line.
- `drift` PROOF-49 as reworded: the view held 11 keys.
- The collaboration test, with the first collision left as git's conflict, failed on `main`'s
  code at `drift.MERGE_LINE`, which that code does not have. The hand run above is what shows
  the fault it guards.

## Lines a person reads that this lane chose

Every other line is K6's or K7's, word for word.

1. `a side changed RULE-2`, as in `login: the conflict at line 18 is left: a side changed
   RULE-2. Resolve it by hand, then run purlin:spec login again.` (`renumber.LEFT_CHANGED`).
   K6 gives `both sides changed` and `a side removes`. It gives no words for a conflict in which
   one side reworded a line of the starting version and the other kept it, which RULE-13 leaves.
2. `a side removes the > Highest-Proof: line`, K6's `a side removes %s` filled with a
   `> Highest-` line in place of an id, for a conflict of `> Highest-` lines in which one side
   drops a line the starting version holds.
3. The second count of `keeps both sides`. K6's comment fills it `'2 lines'`, and section 6.4
   and PROOF-17 print `1 line from HEAD and 1 from qa/login`. The second count carries its noun
   only where the noun differs from the first's: `1 line from HEAD and 1 from qa/login`,
   `1 line from HEAD and 2 lines from qa/login`, `2 lines from HEAD and 3 from qa/login`.
4. After `Do it? [y/N] ` the script ends the line itself where its input is no terminal, so
   `Nothing is changed.` stands on a line of its own in a transcript.
5. `renumber.py --help`: `Resolve the conflict a merge left in a spec, renumber a number it
   writes twice, and move the test comments that name it. It asks before it changes a file.`;
   `--dry-run`: `print the plan and change nothing`; `--yes`: `make the edits without asking`.

## Calls this lane made that the plan did not

1. **A side that removes a line is left, though K6's sentence reads it as `both`.** K6 calls a
   conflict `both` where every line of each side is new or reads as the starting version does.
   A conflict where one side holds an unchanged line of the starting version and the other
   side does not hold that id passes that sentence, and resolving it would bring back a line a
   person deleted. RULE-13 says such a conflict is left, and K6 has the words `a side removes
   RULE-2` for it. The rule was followed.
2. **`highest` covers both kinds in one conflict.** K6: `highest` where each side is one
   `> Highest-` line of one kind. With git's `diff3` conflict style, or where both
   `> Highest-` lines differ, git puts `> Highest-Rule:` and `> Highest-Proof:` in one
   conflict. RULE-12 resolves a conflict whose sides only add `> Highest-` lines, the higher of
   each kind staying, so such a conflict is `highest`, with one `takes` line per kind the two
   sides wrote differently. K6 would have left it with no reason it has words for.
3. **A number written twice inside a conflict that is left is not renumbered in that run.**
   PROOF-20 requires the left conflict's lines to read as before. The old code renumbered one
   side of it. The `is left` line already says to run `purlin:spec` again.
4. **A proof that follows a moved rule is repointed even inside a conflict that is left.** The
   rule moves in this run; a proof left naming the old number would name the other rule.
5. **`resolve(lines, found)`** takes the conflicts `conflicts(lines, base)` answered, where
   section 4.3 writes `resolve(lines)`. It needs the kinds, and the kinds need `base`. Each
   conflict also carries `end`, beside K6's six keys.
6. **`numbers_twice(project_root, features, ref, spec_lines=None)`.** `follows` needs the spec's
   lines. Drift reads them from the file; `renumber` hands over the resolved lines it parsed, so
   the line numbers agree.
7. **No `takes` line for a kind both sides wrote alike**, unless no kind differs.
8. **PROOF-19's spec carries no `> Highest-` lines.** With them, two sides that each add a proof
   under its own number also conflict on `> Highest-Proof:`, and the run would end
   `Resolved 2 conflicts`. The format allows a spec without the lines.
9. **`renumber` RULE-10 does not exist** on `main`: `> Highest-Rule:` read 10 over rules 1 to 9.
   The new rules are 11 to 13, as the plan numbers them.
10. **The collaboration test's needles for the skills.** The test checks that a skill gives
    each command before it runs it, and the skills are lane `words`'. Three needles were
    changed to words that the skills hold now and will hold after section 6.8:
    `sync_status` followed by a backtick in the status skill; `purlin:drift` and
    `` `project_root` `` in the drift skill; and, for the renumbering, the dry run's command and
    `Do it? [y/N]` in the spec skill, in place of `run the same command without --dry-run`,
    which 6.8 removes. So the test passes on this branch and should pass after `words` merges.
11. **Stability's lines in the collaboration test end in the order `RULE-4`, `RULE-3`** and
    `PROOF-5`, `PROOF-4`: K6 keeps the first side's lines first, Dana's, and hers are the ones
    that move. The test's last check reads that order.

## Left, or waiting on another lane

- **`words`**: `skills/spec/SKILL.md` still says `run the same command without --dry-run`. Until
  6.8's text lands, an agent following the skill runs the script with no flag and nothing on its
  input, and it ends `Nothing is changed.` Once `words` merges, the needle in
  `dev/test_collaboration.py`, `Person.renumber`, can be tightened to
  `scripts/spec/renumber.py" <name> --yes`. `purlin_agent` PROOF-51 and PROOF-52 wait on the
  `--yes` flag this lane adds.
- **`words`**: `references/drift_criteria.md` takes K7's two lines and the view's new key
  `merge_in_progress`. `numbers_twice` entries for a rule now carry `follows`.
- **`words`**, one line beyond 6.4 to quote if it lists the reasons a conflict is left:
  `a side changed RULE-2`.
- **`run`**: `scripts/run/purlin_drift.py` prints `view.lines`, so it prints both new lines
  with no change.
- **The coordinator**: the collaboration test takes its `tests` setting with the
  `purlin_config` tool, as it did. Section 6.8 moves the suggested entry to `--write-tests`,
  lane `run`'s flag, which this branch does not have. The test's needle there,
  `` write that array as the `tests` setting with the `purlin_config` tool, then run Step 1
  again ``, stays true only if `words` keeps those words with their backticks.
- No format under `references/formats/` is this lane's, and none changed.
