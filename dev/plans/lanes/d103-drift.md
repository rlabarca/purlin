# Lane `drift`, decision 103

Built the lane `drift` part of the plan (C10, C11's drift lines, C12's drift parts, C14's Criteria-Version) on
`lane/d103-drift`, from `d103/base` at `e5f82d0`. It ran on Linux in a cloud session, with no
real `claude` and no network service. Every repository a test makes is local.

## Highest lines after the work

| Spec | `> Highest-Rule:` | `> Highest-Proof:` |
|---|---|---|
| `specs/mcp/drift.md` | 34 (unchanged; RULE-34 deleted, not reused) | 80 (unchanged; PROOF-78 deleted, not reused) |
| `specs/skills/skill_drift.md` | 13 (was 12) | 39 (was 38) |
| `specs/spec/renumber.md` (new) | 9 | 12 |

Each proof written or reworded holds one case in at most 55 words and has a marked test of its
own.

## Rules and proofs deleted or reworded

- `drift`: RULE-34 and PROOF-78 (the ended-signature line) deleted, with their test.
- `drift`: RULE-22 reworded: the QA view prints the lines of `Left to do` whose kinds stop a
  release. RULE-24 reworded: `left` holds those items. PROOF-31 to PROOF-34 rewritten to that
  contract (`1 rule to write a test for: purlin:build`; `2 rules to fix: purlin:build` beside
  `3 rules to strengthen`; `to_strengthen` alone prints nothing; `left` holds the `to_fix` item).
- `drift`: PROOF-80 loses `signatures_ended`.
- `drift`: PROOF-24 reworded, which the plan does not list. The QA view now also prints the
  blocking lines of `Left to do`, so "after its first line the QA view reads exactly `2 test files
  changed, ...`" no longer held. It now reads: the line after the first is that line, and no
  other line names a test file changed.
- `drift`: the Description drops "the rules waiting for someone to test by hand or to sign".
- `skill_drift`: new RULE-13 and PROOF-39. The skill sends a number written twice, and a test
  comment whose proof's wording changed, to `Renumbering` in `purlin:spec`. RULE-12 and PROOF-38
  stand as written.
- `renumber`: RULE-1 to RULE-9 and PROOF-1 to PROOF-12, as section 4 gives them.

## Tests

- Before, on `d103/base`: `dev/test_drift.py` 78 tests, `dev/test_skill_drift.py` 15, no
  `dev/test_renumber.py`.
- After, run whole: 105 tests (77 + 16 + 12). 32 passed and 73 failed. Every failure is in
  `dev/test_drift.py` and is the same `AttributeError: module 'purlin.summary' has no attribute
  'BLOCKING'`, which waits for lane `counting` (below).
- With a stand-in `BLOCKING` (C3's tuple) added to `summary.py`, all 105 passed. The stand-in was
  never committed and was removed with `git checkout -- scripts/mcp/purlin/summary.py`.
- `bash dev/run_tests.sh --fast`: 2140 passed, 82 failed, 9 skipped, 1 error. After it ran, one
  failure in `dev/test_vocabulary.py` was fixed (`is_ancestor` is a retired spelling; the helper
  is now `_in_history`). Of the rest:
  - 73 in `dev/test_drift.py`, 1 in `dev/test_mcp_server.py` (`test_drift_answers_json`) and 4 in
    `dev/test_security.py` (`TestGitArgvHardening`, which calls drift) wait for `BLOCKING`. With
    the stand-in, those three files passed whole: 216 passed.
  - 3 failures and 1 error also fail on `d103/base` in this container:
    - `dev/test_signatures.py`: "a new system ends nothing" and "a system it names that is gone
      ends it".
    - `dev/test_tag.py`: "the tag is signed with the key the settings name". The container's
      `code-sign` signing program stops it.
    - `dev/test_states.py`: "the table and the dashboard show the same cells". The pip
      Playwright has no matching browser at `/opt/pw-browsers`.

## Deliberate break

In `scripts/mcp/purlin/drift.py`, for a number written twice where one line is on the default
branch, the break set the moving line to the default branch's line (`written[keeper]`).
The PROOF-2 test failed: `login: PROOF-4 at line 14 becomes PROOF-5: "A".` in place of line 13 and
`"B"`. The file was restored with `git checkout -- scripts/mcp/purlin/drift.py`, and all 12
renumber tests passed again.

## What was built

- `drift.py`: the QA view's lines of `Left to do` and its `left` read `summary.BLOCKING`. The
  ended lines, `_ended_lines` and `signatures_ended` are deleted. The module docstring names the
  new `qa` view. The drift lines C11 keeps are unchanged in words.
- `drift.py`, for the helper to call rather than restate:
  - `numbers_twice` entries gain `case` (`kept`, `neither`, `on_default`, `no_default`) and
    `moves`, the line that moves as `{'line', 'text'}`.
  - New `default_spec` and `spec_at` helpers.
  - `comment_reworded` is the one reading of a comment's wording at its blamed commit.
    `comments_changed` calls it.
  - `_blamed_commit` takes an optional revision.
  - `_text_of` is now `text_of`.
- `scripts/spec/renumber.py`: C10 in full, with every plan line in C10's words.
- `references/drift_criteria.md` is at Criteria-Version 12:
  - The `qa` table loses `signatures_ended`.
  - `left` and the paragraph under it name the lines that stop a release.
  - One sentence says `purlin:spec` makes the renumbering on a yes.
  - The config table loses `min_strength`. `mutation_engine` is asked at `signed` and set by
    `--mutation` at either gate.
- `skills/drift/SKILL.md` is 91 lines, ceiling 150:
  - The usage line for `qa` changes.
  - The "A number written twice" section points at `Renumbering` in one line for a number and one
    for a comment.
  - The closing table loses the two signing rows and gains `A line of Left to do`.
  - The changed-comment row names `purlin:spec` where its old wording is now another id.

## Calls left, each reported

- **Proof lines of a moved rule with no default branch.** Where the checkout has no default
  branch, no proof line follows a moved rule: nothing says which of the two rules a proof means.
  Where the default branch has no copy of the spec, every proof line naming the rule follows,
  as C10 reads.
- **Comments on other branches.** A comment whose line was written in a commit already in HEAD's
  history is not named: step 2 handles it here. This keeps an old local branch from naming every
  merged comment.
- **Highest lines.** A Highest line is raised only where the spec carries one. None is added.
- **When `NOTHING` prints.** It prints when the plan changes no spec line and no test comment.
- **Order of the plan lines.** They print in C10's constant order: moves, proofs that follow,
  comments that move, comments that follow, comments not committed, Highest lines, other
  branches. Then `DRY_RUN` or `DONE`.
- **Which comments step 2 reads.** Step 2 reads every test file a suite names, from disk, so a
  file not yet added is named as not committed.
- **Settings file.** The helper does not check the settings file. C10 gives it no refusal but
  "the feature is no spec".

## Words chosen that section 7 does not give

- The helper, exit 1: `<feature>: no spec of this checkout has that name. Run purlin:status to see its specs.`
- Drift criteria, `qa`: `After those lines the view prints the lines of Left to do that stop a
  release, in the words the status prints them, such as 2 rules to fix: purlin:build and 1 spec
  to repair: purlin:spec. Each is left out at zero, and no other line of Left to do is printed: a
  rule to strengthen or to write a proof for stops no release.`
- Drift criteria, a number written twice: `purlin:spec makes the edit, and moves the test comments, when you say yes to its plan.`
- Drift criteria, `mutation_engine`: `purlin:init, which asks at the gate signed whether to break
  the code on purpose, and purlin:init --mutation at either gate`; `none turns mutation testing
  off, so no breaks run; any other value runs them when purlin:audit runs, and nothing waits on
  them`.
- Drift skill: `purlin:drift qa   Proofs and tests changed, and what stops a release`; `To
  renumber it and move the test comments that name it, follow Renumbering in purlin:spec: it
  shows the plan and asks before anything changes.`; `A test comment whose proof's wording
  changed moves the same way: follow Renumbering in purlin:spec.`; the rows `A line of Left to
  do | → Run: the command that line names` and `→ Run: purlin:spec <feature> where its old
  wording is now another id, else → Run: purlin:build <feature>`; `→ Nothing changed that the
  specs or the tests need. Run: purlin:status`.

## Failures in files this lane does not own

- `dev/test_mcp_server.py` `test_drift_answers_json` and `dev/test_security.py`
  `TestGitArgvHardening` (4 tests) call drift. They fail only until `summary.BLOCKING` exists,
  and need no change.

## Tests that fail only because another lane has not merged

- Lane `counting` (`summary.BLOCKING`, C3): 73 tests of `dev/test_drift.py`, because every drift
  report builds the QA view. They include the `qa` view tests that read `Left to do` (PROOF-31 to
  PROOF-34). Also `dev/test_mcp_server.py` `test_drift_answers_json` and the 4 tests of
  `dev/test_security.py` `TestGitArgvHardening`. All pass with C3's `BLOCKING` in place.
- The renumber tests and the skill tests wait on no lane.

`skills/spec/SKILL.md`'s `Renumbering` section, which the drift skill points at, is lane
`skills`'s.
