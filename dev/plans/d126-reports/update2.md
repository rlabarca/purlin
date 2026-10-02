# Decision 126, second round, lane `update2`: the report

Branch `lane/d126-update2`, from `main` at `0c5f99486`. Nothing pushed, tagged or signed.
Acceptance: `dev/test_init_update.py`, `dev/test_init_scaffold.py`, `dev/test_skill_init.py`,
`dev/test_skill_spec.py`, `dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`:
`132 passed, 6 skipped`. `bash dev/run_tests.sh --fast`: `1040 passed, 9 skipped`, `Suites: 1 passed, 0 failed`.

## What was built, per finding

| Item | Built |
|---|---|
| 1 | `kind-tags` and `os-tags` read a proof with the lines that continue it, up to the next `- PROOF-`, `- RULE-`, heading or blank line, and act on the tags that end it, on whichever line they are. The kinds dropped are `unit`, `integration`, `e2e` and every kind the project's own 0.9.5 markers name in their last field: `[proof:<feature>:<id>:<rule>:<kind>]`, a fourth string of `pytest.mark.proof(...)`, the xUnit trait and the SQL comment. `@manual`, `@slow` and `@env(...)` are never dropped. A tag alone on its line takes the line with it. The totals line counts tags and specs. |
| 2 | A run that applied nothing prints the pending list with the proposed test commands, the questions and `skipped <id>` where it asked, then `→ Run: purlin:init --update` and one line naming `--yes` and `--apply`. No status, no `These need you:`. |
| 3 | A run that applied a migration and left none pending ends, after its other parts, on `→ Run: purlin:test --all --commit` and `Run it before anything else: every rule reads not run until it has.` The status's count of rules and `Left to do` are not printed. `docs/upgrading.md`, `What you will see`, lists a test comment to correct among the lines about the project and says a test that passes when its feature is run alone is the project's own. |
| 5 | The line for a marker naming a proof no spec holds is the plan's, word for word, the comment in the file's own comment style. `skills/spec/SKILL.md`, `docs/specs-and-anchors.md` and `references/formats/spec_format.md` say where the two `> Highest-` lines go in a spec that has neither. |

`pending(project_root)`, `rewrite_markers`, `_marked_old` and every pattern that finds a 0.9.5
marker in a test file are as they are on `main`. `LEFT_NO_SPEC` takes one more value, the
comment.

## Rules and proofs

`> Highest-*` before and after: `update` Rule 64 to 67, Proof 195 to 205; `skill_spec` Rule 32
to 33, Proof 62 to 63. No number is reused. `references/formats/spec_format.md`: wording only,
`> Format-Version:` not bumped.

Added to `specs/init/update.md`, word for word:

- RULE-65: The tags that end a proof are read with the lines that continue it, up to the next proof, rule, heading or blank line: the Windows tag there becomes `@env(windows)` and each kind-of-test tag goes, the kinds being `unit`, `integration`, `e2e` and every kind the project's own 0.9.5 markers name in their last field; a tag followed only by a note in brackets is read too and the note stays; `@manual`, `@slow` and `@env(...)` are never dropped, and the line of totals says how many tags went from how many specs
- RULE-66: A run that applied nothing ends, after the pending list with each proposed test command, on `→ Run: purlin:init --update` and one line saying how to apply, which names `--yes` and `--apply`; it prints no count of rules and no `Left to do`
- RULE-67: A run that applied a migration and left none pending ends on `→ Run: purlin:test --all --commit` and `Run it before anything else: every rule reads not run until it has.`, and prints no `Left to do`; a run that left a migration pending ends on `→ Run: purlin:init --update` and a line naming each migration still pending
- PROOF-196 to PROOF-200 and PROOF-205 under RULE-65, PROOF-201 under RULE-66, PROOF-202 and PROOF-203 under RULE-67, PROOF-204 under RULE-57: as written in the spec.

Reworded, each test changed under its kept marker line in the same commit:

- PROOF-172 (RULE-57): its expected line is now the plan's: `... Write the proof with purlin:spec piano, put # purlin: piano PROOF-<n> above the test, and take the old tag out of the test's title or decorator.`
- PROOF-173 (RULE-57): "the spec and the test ... are as they were" became "the spec's proofs still read `PROOF-1`, `PROOF-2`, `PROOF-2b` and `PROOF-7b` under `> Highest-Proof: 9`, the test marked for `PROOF-2b` is as it was". Its sample spec holds a proof ending `@integration` on a second line, which `kind-tags` now drops in that run.

Added to `specs/skills/skill_spec.md`:

- RULE-33: The spec skill says where `> Highest-Rule:` and `> Highest-Proof:` go in a spec that has neither: after the last `>` line of the header, `> Highest-Rule:` first
- PROOF-63 (RULE-33): A reader of the spec skill's part headed `Ids` finds the sentence ``In a spec that has neither line, both go after the last `>` line of the header: `> Highest-Rule:` first, then `> Highest-Proof:`.``

## Seen failing first

The code for items 1, 2, 3 and 5 was written before its tests; the tests were then run on
`main`'s `scripts/init/update.py`, where 8 of the 9 new ones and the reworded PROOF-172 failed.
PROOF-198 is a negative and passes on both. PROOF-205 and PROOF-63 were written first and seen
failing.

## On a copy of the real project

A fresh `cp -Rc` of `RLabGenMusic`, from this worktree. Logs: `01-list.txt`, `02-apply.txt`,
`03-full-run.txt`, `04-rerun-project_history.txt` in the scratch folder.

- **The listing run** (`scaffold.py --update < /dev/null`) exits 0, changes nothing, and ends:
  `→ Run: purlin:init --update` then `Nothing was applied. Add --yes to apply every migration and use each proposed test command, or --apply <id>[,<id>...] to apply the migrations named.`
  It lists `kind-tags` with 49 specs, and under `config` the two proposed commands.
- **Applied with `--yes`**, every migration and both proposed commands: `kind-tags: dropped 438 kind-of-test tags from 49 specs: purlin:test runs every marked test`. `@unit`, `@integration`, `@e2e` and `@browser` left in the copy's specs: 0, 0, 0, 0 (before: 114, 160, 4, 160). `@manual`, `@slow`, `@env(`: 0, 0, 0 before and after; the project has none. 34 proofs renumbered, 533 markers rewritten in 95 files, 9 markers left and named with the new line. 159 lines of output, ending `→ Run: purlin:test --all --commit` then `Run it before anything else: every rule reads not run until it has.` A second run prints `Nothing is pending: this project is at 0.10.0.`
- **The full run** (`purlin_run.py --test --all`): `Markers: 533 tied to a test, 0 not tied.`, `476 rules. 474 pass their tests.` The two are `project_history` RULE-10 and RULE-11, one test file. `--test --feature project_history` alone, once: `476 rules. 476 pass their tests.` `Left to do` then holds `1 test comment to correct: purlin:build` alone, the project's own.
- Five of the 438 tags were followed by a note in brackets, as `@unit (python)`; the first trial left those five, and the note shape was then built (PROOF-205).

## Lines chosen

- `kind-tags: dropped <n> kind-of-test tags from <m> specs: purlin:test runs every marked test`; in the log, `dropped <n> tags from <spec>`.
- `Nothing was applied. Add --yes to apply every migration and use each proposed test command, or --apply <id>[,<id>...] to apply the migrations named.`
- `<n> migrations are still pending: <ids>. A test run stops until nothing is pending.` (`1 migration is still pending: ...`)
- Skill and docs: ``In a spec that has neither line, both go after the last `>` line of the header: `> Highest-Rule:` first, then `> Highest-Proof:`. Where one is there, the other goes beside it.``
- `docs/upgrading.md`: the parts `The tags`, `The test run comes next`, and under the lines about the project the test comment and the test that passes alone.

## Calls the plan did not make

1. The listing run prints `→ Run: purlin:init --update` first and the line on how to say yes last, as the applied run prints its arrow and then its sentence.
2. A run that applied nothing prints no `These need you:`: the one line it held there, a spec naming no files, is about the project and is printed by the applied run and the status.
3. A run that applied some migrations and left others pending ends on `→ Run: purlin:init --update` and names them, not on the test run: a test run stops while a migration is pending.
4. The applied run prints neither the status's count line nor its `Left to do`; `Every rule reads `not run` until the tests run again.` from round one stays above.
5. A tag is one that ends the proof. A kind word in the middle of a proof's prose is left, and an `@word` after `and`, `or` or a comma is prose, as the spec reader takes it. A tag followed only by a note in brackets is dropped and the note kept.
6. The kinds are also read from the copies of test files under `.purlin/runtime/update-backup/`, so a project that applied `markers` before `kind-tags` still loses `@browser` (PROOF-200).
7. The test files are read for kinds only where a proof ends with a tag that is none of the three kinds and none of the kept tags, so `pending` costs a current project nothing more.
8. `os-tags` now rewrites `@windows` only where it ends a proof, with or without other tags; on `main` it rewrote one ending any line of a spec.
9. A tag no marker names, such as `@browser` in a project whose markers name no `browser`, is left (PROOF-198).
10. `RELEASE_NOTES.md` and `skills/init/SKILL.md` say the same three things: the kinds dropped, the listing run's ending, the applied run's ending.

## Left, or waiting on another lane

- Nothing waits on lane `run2`. Its warning for the nine markers left is its own.
- `references/purlin_commands.md` lines 255 to 256 are still true; no lane owns the file.
