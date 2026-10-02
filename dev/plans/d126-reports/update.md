# Decision 126, lane `update`: the report

Branch `lane/d126-update`, from `main` at `a84988cdd`. Nothing pushed, tagged or signed.
Acceptance: `dev/test_init_update.py`, `dev/test_init_scaffold.py`, `dev/test_skill_init.py`,
`dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`: `120 passed, 6 skipped`.
`bash dev/run_tests.sh --fast`: `1010 passed, 9 skipped`, `Suites: 1 passed, 0 failed`.

## What was built, per finding

| Item | Built | Commit |
|---|---|---|
| 5 | A migration `lettered-proofs`, before `markers`: each lettered proof takes the next free number in its spec, `> Highest-Proof:` moves with it, the marker of each test that named it is rewritten, each change printed. A marker naming a lettered proof no spec holds is left and named. | `fix(update): a proof 0.9.5 numbered with a letter...` |
| 1, 8 | The JavaScript and TypeScript rewrite reads the file as the test run's reader does. A tag that was a string piece of its own goes with its `+` and the space beside it; a tag opening a title leaves no leading space; the comment goes above the line that opens the test, however many lines the title runs over. Each rewritten file is read back with `markers.read_text` and a marker tied to no test, or to another test than the one under it, is named. | `fix(update): a rewritten marker leaves a title...` |
| 3 | Every `conftest.py` that names `pytest_purlin` is parsed as Python: the entry goes from `pytest_plugins`, the `sys.path` line pointing at `.purlin/plugins` goes, comments and docstrings are never edited, a file left with only comments, a docstring and imports is deleted, each file is listed. A `conftest.py` Python cannot parse is left and named. | `fix(update): every conftest.py...` |
| 4 | The update reads the project's `package.json` scripts, `Makefile` and workflow `run:` lines for how each tool is started, proposes the command setup suggests (`frameworks.entries_for`) started that way, shows it with the project's own command, and asks. `--yes` accepts. A tool the old settings named that a command of the project's runs is kept, where detection at the root alone dropped it. | `fix(update): the test command proposed...` |
| 10 | Backups under `.purlin/runtime/update-backup/<the file's path>`, the bytes from before the run; `.purlin/runtime/` is added to `.gitignore` where missing; the ending says where they are. | `fix(update): the backups go under one folder...` |
| 17 | One line of totals per migration, `<id>: <what it did>`, details under it; each file's line goes to `.purlin/runtime/update-backup/update.log`; the owner's lines last under `These need you:`. | `fix(update): totals first...` |
| 16 | Each question on its own line, the answer taken printed where input is not a terminal. Two flags, `--apply <id>[,<id>...]` and `--test-command <tool>=<command>`, handed over by `scaffold.py --update`. The pending list shows the proposed commands. The skill: list with `< /dev/null`, stop and ask, apply with the flags. | same, and `fix(skill_init): ...` |
| 12 | `Purlin left these for you:` from `git grep` over tracked files for the five needles, a count of lines per file, most first, 20 files then `and <n> more files`. The `.gitignore` lines 0.9.5 wrote for its cache and plugin folder are removed. | `fix(update): totals first...` |
| 11 | After an applied run: every rule reads `not run`; the `verify:` commits stay; the receipts are readable from the commit before the upgrade, named by sha. Also in `docs/upgrading.md`. | same, and `docs: ...` |
| 20 | `docs/upgrading.md`, `What you will see`. | `docs: ...` |
| 15 | `README.md`, under Install: `Coming from 0.9.5? See [docs/upgrading.md](docs/upgrading.md).` | `docs: ...` |

## Rules and proofs

`> Highest-*` before and after: `update` Rule 56 to 64, Proof 168 to 195; `scaffold` Rule 83
unchanged, Proof 176 to 177; `skill_init` Rule 87 to 88, Proof 98 to 100. No number is reused.

Added, word for word in `specs/init/update.md`: RULE-57 (PROOF-169 to 173), RULE-58 (PROOF-174
to 178), RULE-59 (PROOF-179), RULE-60 (PROOF-182, 183), RULE-61 (PROOF-184, 185), RULE-62
(PROOF-186 to 189), RULE-63 (PROOF-190 to 192), RULE-64 (PROOF-193, 194); PROOF-180, 181 under
RULE-35; PROOF-195 under RULE-7. In `specs/init/scaffold.md`: PROOF-177 under RULE-33. In
`specs/skills/skill_init.md`: RULE-88 (PROOF-99, 100).

Reworded, each test changed under its kept marker line in the same commit: `update` RULE-7,
RULE-18, RULE-35; PROOF-7, 71, 118, 89, 164 (backups); PROOF-83, 120 (a `conftest.py` of
`import os` alone is now deleted, so the kept file holds `ROOT = os.getcwd()` too); PROOF-29,
168, 109, 24, 163 (per-file lines moved to the log); `scaffold` RULE-33.

No file under `references/formats/` changed.

## Seen failing first

Items 5, 1, 8, 3, 10: the tests were written first and failed on the code before the fix (5 of
5, 6 of 6, 2 of 2, 3 of 4). Item 4: the two tests were run on the code before the fix after it
was written, and failed there. Items 17, 16, 12, 11: 10 of the 12 new tests failed on the
commit before; `PROOF-194` is a negative and passed on both.

## On a copy of the real project

Each trial is a fresh `cp -Rc` of `RLabGenMusic`, updated, then
`purlin_run.py --test --all --project-root <copy>` from this worktree.

| Trial | Markers tied | Rules passing of 476 | Untracked after the update |
|---|---|---|---|
| `main` | 497, 1 not tied | 57 | 151 |
| item 5 | 532, 1 not tied | 58 | 151 |
| items 1 and 8 | 533, 0 not tied | 304 | 151 |
| item 3 | 533, 0 | 302 | 151 |
| item 4, answers typed | 533, 0 | 307 | 151 |
| item 10 | 533, 0 | 305 | 0 |
| final, by the skill's three steps | 533, 0 | 305 | 0 |

The count moves between 302 and 307 from one run to the next: 2 or 3 vitest tests
(`project_workspace` rename, `project_history` restore, `stem_workbench`) fail in some runs of
the copy and pass in others.

- 34 proofs renumbered in 13 specs and 35 markers in 17 files. The plan says 17 specs; the
  project holds lettered proof lines in 13. Nine markers name a lettered proof no spec holds
  (`generated_track PROOF-1b`, `parameter_lfo PROOF-1b` and `PROOF-3b`, `sample_controls
  PROOF-8b`, `stem_order PROOF-1b`, `master_solo PROOF-1b`, `layered_voice PROOF-10b`,
  `percussive_match PROOF-7b` and `PROOF-7c`); each is left and named under `These need you:`.
- 533 markers rewritten in 95 files; no title is left with `+ ''`; the read-back named none.
- Both `conftest.py` files deleted and listed; `npm run test:python` then ran `117 passed`.
- The pytest command proposed is `uv run --project pipeline pytest {files}
  --junitxml={report}`, read from `package.json`'s `test:python`; the vitest proposal is the one
  setup suggests. Both accepted as the owner would.
- The update's output is 153 lines, 56 of them the pending list and 34 the renumbered proofs;
  `update.log` holds 368.

**What is still short, and whose it is.** 169 rules read `not run` after `--all`:

- Lane `run` 4b: with every feature selected the run hands pytest no file list, and every
  Python file fails with `No module named 'rgm'`. A run of the 10 `pipeline` features by name,
  on the item 4 copy, counted 400 of 476: the proposed command works when it is given files. A
  run naming all 54 features drops the list the same way as `--all`.
- Lane `run` item 2: titles with an escaped apostrophe or joined from pieces get no result.
  The rewrite leaves a title of three or more pieces joined, with only its tag gone.
- This lane's nine left markers above.

## Lines chosen

- Migration: `lettered-proofs`, `give each proof numbered with a letter, such as PROOF-3b, the next free number in its spec`.
- `renumbered <n> proofs in <n> specs and <n> markers in <n> files`
- `left <file>:<line> as it was: it names <feature> <id>, which no spec has. Write the proof with purlin:spec <feature>, then write the marker as a comment above the test by hand`
- `left <file>:<line> as it was: it names <feature> <id>, which is numbered with a letter. Run purlin:init --update again and apply lettered-proofs`
- `<file>:<line>: the title of the test under this marker cannot be read, so its result cannot be matched. Write it as one plain string.`
- `left <file> as it was: it cannot be read as Python. Remove the lines that load pytest_purlin by hand`
- `<tool>: <command>`, `  <where> runs it as: <command>`, `Use this command for <tool>? Press Enter to use it, or type the command to use instead: `
- `Every file the update changed is kept as it was under .purlin/runtime/update-backup/, with each change listed in update.log there. Delete the folder once the tests pass.`
- Totals: `removed the design reference from <n> specs`, `removed the lines naming anchors from <n> specs`, `rewrote <n> markers in <n> files`, with `; a shell or SQL file is one test now, and passes when it exits 0`.
- `These need you:`
- Under `Purlin left these for you:`: `  <file>: <n> lines`, `  and <n> more files`, and `  Each line counted names something 0.9.5 used: [proof:, pytest.mark.proof, .purlin/plugins, purlin:verify, proofs-. This release reads none of them.`
- ``Every rule reads `not run` until the tests run again.`` and ``The `verify:` commits 0.9.5 made stay in git as the earlier record, and its receipts can be read from the commit before the upgrade, <sha7>.``
- `<id> is not a migration. The migrations are: <ids>.` and `--test-command takes <tool>=<command>, ...; it was given <value>.`

## Calls the plan did not make

1. Two new flags, `--apply` and `--test-command`, as how an agent passes each answer. Answers
   on the input still work.
2. The pending list shows the proposed test commands, so the person can be asked before
   anything is applied.
3. A marker naming a lettered proof no spec holds is left and named, not given a number.
4. A `[proof:...]` tag in a Python docstring is not renumbered: it is no marker, and it is
   counted under `Purlin left these for you:`.
5. A tag in a string that is no test's title is left and named with the existing `left` line.
   A title joined to a name, `it(NAME + ' [tag]')`, is rewritten and then named by the read-back.
6. The read-back relies on the reader alone, so once lane `run` makes it refuse a title that is
   not one plain string, the update names those too with no change here.
7. The renumbered proofs are printed, one line each, under the totals line: the plan says
   both "prints each change" and "one line of totals".
8. `config` prints its commands, dropped tools and removed keys under its totals line.
9. The order of the ending: the old record and the backups line, then `Purlin left these for
   you:`, then `These need you:`, then the status's own ending.
10. The `.gitignore` lines removed are `.purlin/cache/`, `.purlin/plugins/__pycache__/` and
    the two comments 0.9.5's template wrote above them; `# Dashboard HTML (symlinked from
    framework)` is reworded to this release's comment. `.purlin/runtime/` is added where missing.
11. A backup is written once per file per folder: a second migration, or a second run,
    keeps the first copy.
12. A command that installs a tool (`pip install pytest`) is not read as running it. A
    launcher that is the suggested one in another spelling (`pytest`, `vitest`) keeps the
    suggestion.
13. `scripts/spec/renumber.py` is not changed or called: it renumbers a number written twice
    from git history, and nothing in it fits a lettered id.
14. The sample under `dev/fixtures/upgrade-0.9.5` is unchanged; each test writes the real
    shapes onto its copy, so PROOF-2 and PROOF-68 keep their nine migrations.
15. Items 17, 16, 12 and 11 share one code commit: they change the same functions.

## Left, or waiting on another lane

- Lane `run`, items 2 and 4b, for the counts above.
- `kind-tags` and `os-tags` find nothing in the real project: its proof lines run over several
  lines and the tag ends the last one. Not among the twenty; the tag is read as text.
- `references/purlin_commands.md` lines 255 to 256 describe the update's list and are still
  true; no lane owns the file and it is not changed.
