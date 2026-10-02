# Decision 127, lane `sign3`: the report

Branch `lane/d127-sign3`, one commit of work on `main` at `c4c548587`, then this report.
Acceptance: `dev/test_signatures.py`, `dev/test_skill_sign.py` and `dev/test_purlin_docs.py`
ended `89 passed`; `bash dev/run_tests.sh --fast` ended `1054 passed, 9 skipped`,
`Suites: 1 passed, 0 failed`. `main` had not moved at the rebase, so the acceptance was run
once, on the commit of work. Nothing is pushed, tagged or signed.

## What was built

**15. No sign-off while a test still carries a 0.9.5 marker.** `scripts/review/sign.py`'s
`refusal()` calls `status.old_markers(project_root)` and uses only the length of the list. At
one or more it returns the plan's line, with `1 test still carries` for one, nothing written
and exit 1. `old_markers` is not changed.

- **Where it stands.** Third: after `files are changed and not committed` and `the evidence
  is written and not committed`, before `No version`. After the first two because
  `old_markers` reads the files on disk, and once nothing tracked is changed those are the
  files of the commit being signed. Before every other refusal because the fix changes test
  files: a person told first to take the results again, or to name a version, would do it
  twice. It reads no version, no tag, no package and no key, and asks nothing.
- **`--show`** prints the same one line and exits 1, as it does for every refusal: the
  refusal is in `refusal()`, which `--show`, the walk and `--answers` all read first.
- **`--check <file>`** is not refused: it returns before `refusal()` is read, as before.
- **Exit code** 1, as every other refusal.

## Rules and proofs, word for word

`specs/review/signatures.md`: `Highest-Rule` 136 to 138, `Highest-Proof` 275 to 280.

- RULE-137: The command refuses while a tracked test still carries a marker from Purlin 0.9.5, as the status counts them: it prints the one line `No sign-off: <n> tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.`, opening `No sign-off: 1 test still carries` for one, writes nothing and exits 1
- RULE-138: That refusal comes before a version is read and before a key is looked for, and asks nothing; `--show` prints the same line and exits 1; `--check <file>` is not refused by it
- PROOF-276 (RULE-137): With committed evidence that passes, `tests/login.test.ts`, a tracked file, holds one test whose title carries `[proof:login:PROOF-1b:RULE-1:unit]`; the walk prints only `No sign-off: 1 test still carries a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.`, writes nothing and exits 1
- PROOF-277 (RULE-137): The same project, with that tag taken out of the test's title; `--show` exits 0, prints no line beginning `No sign-off` and ends `Answer each stop, then run purlin:sign --answers <file>.`
- PROOF-278 (RULE-138): In a project that states no version, in a home and a checkout with no signing key, `tests/login.test.ts` holds three tests whose titles each carry a 0.9.5 tag; the walk prints only `No sign-off: 3 tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.`, asks no question, adds no commit and exits 1
- PROOF-279 (RULE-138): With committed evidence that passes and two tests whose titles each carry a 0.9.5 tag, `--show` prints only `No sign-off: 2 tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.`, writes nothing and exits 1
- PROOF-280 (RULE-138): After the first sign-off of `2.1.0`, a commit adds `tests/login.test.ts` with one test whose title carries a 0.9.5 tag, so `--show` prints that refusal; `--check .purlin/evidence/package/2.1.0.json` exits 0 and prints exactly `The package matches its fingerprint.`

No rule or proof was reworded. `specs/skills/skill_sign.md` and `dev/test_skill_sign.py` are
unchanged: its one rule lists the commands and paths the skill names, and none was added.
`dev/sign_project.py` is unchanged.

## Seen failing first

The five tests, class `TestMarkersFrom095` in `dev/test_signatures.py`, were written and run
before the code: `4 failed, 1 passed`. PROOF-276 and PROOF-279 got the walk's overview and
exit 0; PROOF-278 got `No version`; PROOF-280 got the `the code has changed since` line.
PROOF-277 is the control, the same project with the tag out, and passes before and after.
After the code: `81 passed` in the file.

## On a copy of the real project

`RLabGenMusic-upgrade-3`, copied with `cp -Rc` into the scratch folder; the original was
only read and its `HEAD` and status are as they were.

- At its head, `cf23472`, where the tests were rewritten: `old_markers` gives 0, and `--show`
  prints the `these results were not taken on this version of the code` refusal, as before.
- At `4366261`, the commit just after the upgrade: `--show` and the walk with no input each
  print `No sign-off: 9 tests still carry a marker from Purlin 0.9.5, which is not read. Run
  purlin:status to see each, rewrite them, then purlin:sign.` and exit 1. Nothing was
  written, no tag, `git status` clean. 9 is the count the plan gives for that project.

## Lines chosen

The refusal is the plan's, word for word. Chosen here:

- `docs/sign-off.md`, the "Why" cell of the new row of "What it refuses", third: `a test
  still carries a marker from Purlin 0.9.5, so its result counts for no rule; for one it
  reads `1 test still carries`. `purlin:status` names each`
- `skills/sign/SKILL.md`, step 2: the line in the list of refusals, third, and the bullet
  `The 0.9.5 line reads `1 test still carries` for one. `purlin:status` names each test and
  its rule.` Step 7's row for a `No sign-off:` naming `purlin:status` already gives the next
  step.
- `sign.py`'s own help: `a test still carries a marker from Purlin 0.9.5`, third in its list.

## Calls the plan did not make

- The place, third, and its reasons, above.
- For one test the line still ends `rewrite them`: the plan gives `1 test still carries` as
  the only change.
- `old_markers` is called with no guard. The status guards it so that the status is always
  printed; a sign-off that could not count them should not go on as if there were none, and
  there is no line of the plan's for that case. An error there ends the command with
  Python's own message.
- Two rules: the refusal and its line, then its place, `--show` and `--check`.

## Left, or waiting on another lane

- `references/evidence_and_signoff.md` is lane `run3`'s. Its list under "**The sign-off
  walk.** `purlin:sign` refuses, and writes nothing, in each of these cases:" does not hold
  this refusal. The exact change: after the bullet `- the evidence is written and not
  committed;` add `- a test still carries a marker from Purlin 0.9.5;`.
- Lane `run3` may add members to the items `old_markers` returns; this lane reads the length
  alone, so nothing here changes with that.
