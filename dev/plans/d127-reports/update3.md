# Decision 127, lane `update3`: the report

Branch `lane/d127-update3`, from `main` at `c4c548587`. Nothing pushed, tagged or signed.
Acceptance: `dev/test_init_update.py`, `dev/test_init_scaffold.py`, `dev/test_skill_init.py`,
`dev/test_purlin_docs.py`, `dev/test_purlin_agent.py`: `140 passed, 6 skipped`.
`bash dev/run_tests.sh --fast`: `1059 passed, 9 skipped`, `Suites: 1 passed, 0 failed`.

## What was built, per item

| Item | Built |
|---|---|
| 5 | After `Run it before anything else: ...` the applied run prints `A test that fails in that run and passes when its feature is run alone is the project's own: purlin:test <feature>.` |
| 8 | Under `Purlin left these for you:` a `CLAUDE.md` stands first, then `AGENTS.md`, then each file under `.claude/` (a root file before one in a folder), whatever the counts; each of their lines ends `. Change it first: it tells the agent to write what this release does not read.` The rest follow, most first. |
| 9 | In a Python test whose 0.9.5 mark the run rewrote, a docstring line holding nothing but `[proof:...]` tags goes: a docstring that was the tag alone goes whole; a tag opening a docstring goes with the blank lines under it, the opening quotes moving to the first line of text; a tag ending one goes with the blank lines above it. A tag in a sentence, a docstring that is all its test holds, and the docstring of a test whose marker was left or never existed stay. The file is checked to read as the same code (docstrings aside) afterwards, or kept as it was. A detail line under the `markers` totals counts the lines. |
| 10 | Of the project's commands that run a tool, the proposal cites the one with the fewest options that run only some of the tool's tests (the first of those); the launcher comes from it. Where it still carries such an option: `  The proposal leaves out --project unit, so every vitest test runs.` |
| 12 | `Every file the update rewrote is kept as it was under .purlin/runtime/update-backup/, with each change listed in update.log there. A file it deleted is in git, at <sha7>. Delete the folder once the tests pass.`, `<sha7>` being HEAD before the run; with no earlier commit the middle sentence is left out. |
| 13 | A run with `--yes`, or with `--apply` naming at least one pending migration, prints `Applying <n> migrations: <ids>.` (`1 migration`) as its first line in place of the pending list. A run that asks, or an `--apply` naming nothing pending, prints the list as before. |

`pending(project_root)`, `rewrite_markers(text, ext)` and its return are unchanged; the line
the upgrade prints for a marker it leaves is unchanged. `scripts/mcp/purlin/frameworks.py`,
`templates/`, `scripts/init/scaffold.py` and the 0.9.5 fixture are not changed.

## Rules and proofs

`specs/init/update.md`: `> Highest-Rule:` 67 to 71, `> Highest-Proof:` 205 to 215. No number is
reused. No file under `references/formats/` changed.

Added, word for word:

- RULE-68: Under `Purlin left these for you:` a `CLAUDE.md` stands first, then an `AGENTS.md`, then each file under `.claude/`, whatever its count, and each of their lines ends `. Change it first: it tells the agent to write what this release does not read.`
- RULE-69: In a Python test whose marker the update rewrote, a docstring line that holds nothing but a 0.9.5 tag is removed: a docstring that was the tag alone goes whole, a tag that opened a docstring goes with the blank lines under it, and a tag that ended one goes with the blank lines above it; the line of totals says how many lines went; a tag inside a sentence, a docstring that is all its test holds, and the docstring of a test whose marker was not rewritten stay as they were
- RULE-70: Where several commands of the project's own run a test tool, the proposal cites the one closest to the command proposed, the one with the fewest options that run only some of the tool's tests; where the command cited carries such an option, the line under it reads `The proposal leaves out <option>, so every <tool> test runs.`
- RULE-71: A run told what to apply, with `--yes` or `--apply`, prints `Applying <n> migrations: <ids>.` as its first line in place of the pending list, naming the migrations it applies in the order they are applied
- PROOF-206, 207 (RULE-68), PROOF-208, 209, 215 (RULE-69), PROOF-210, 211, 212 (RULE-70), PROOF-213, 214 (RULE-71): as written in the spec.

Reworded, each test changed under its kept marker line in the same commit:

- RULE-7: "... the update ends by saying where the copies are, that a file it deleted is in git at the commit before the update, which it names, and that the folder can be deleted once the tests pass". PROOF-195: the new sentence with `<sha7>` the commit before the update; a run file the update deleted has no copy under the folder, and `git show <sha7>:<path>` shows it.
- RULE-63: "most first" became "the files that instruct an agent first and the others most first". PROOF-190: `  CLAUDE.md: 4 lines. Change it first: ...`.
- RULE-67 and PROOF-202: the applied run ends on three lines, the third item 5's.

## Seen failing first

The tests were written first and run on the unchanged `update.py`: 10 failed (PROOF-195, 190,
202, 206, 207, 208, 210, 211, 213, 214). PROOF-209 and PROOF-212 are negatives and passed
before and after. PROOF-215 was split from PROOF-209 after the code was written; it is a
negative too.

## On a copy of the real project

A fresh `cp -Rc` of `RLabGenMusic` in the scratch folder, from this worktree. Logs
`01-list.txt`, `02-apply.txt`, `03-full-run.txt`, `04-rerun-project_history.txt`.

The listing run (`scaffold.py --update < /dev/null`), exit 0, its proposal whole:

```
  config: write .purlin/config.json with version and tests alone
      .purlin/config.json
      pytest: uv run --project pipeline pytest {files} --junitxml={report}
        package.json, "test:python", runs it as: uv run --project pipeline pytest pipeline/tests
      vitest: npx vitest run --reporter=default --reporter=junit --outputFile.junit={report} {files}
        package.json, "test:all", runs it as: vitest run
```

No leave-out line: `test:all` narrows nothing. The apply run (`--yes`), exit 0, 88 lines
(test 3: 159 with the second pending list), first lines:

```
Applying 11 migrations: design-refs, anchor-lines, kind-tags, untracked-files, hooks, config, evidence, dashboard, lettered-proofs, markers, plugins.
  design-refs: removed the design reference from 1 spec
  anchor-lines: removed the lines naming anchors from 53 specs
```

(11, where test 3 had 10: the original's `purlin-report.html` is the 0.9.5 link, so `dashboard`
is pending.) Under `markers: rewrote 533 markers in 95 files` it printed
`    removed 85 docstring lines that held only a 0.9.5 tag`. Its ending:

```
Every rule reads `not run` until the tests run again.
The `verify:` commits 0.9.5 made stay in git as the earlier record, and its receipts can be read from the commit before the upgrade, e257e2c.
Every file the update rewrote is kept as it was under .purlin/runtime/update-backup/, with each change listed in update.log there. A file it deleted is in git, at e257e2c. Delete the folder once the tests pass.
...
→ Run: purlin:test --all --commit
Run it before anything else: every rule reads not run until it has.
A test that fails in that run and passes when its feature is run alone is the project's own: purlin:test <feature>.
```

First under `Purlin left these for you:`:
`  CLAUDE.md: 4 lines. Change it first: it tells the agent to write what this release does not read.`
The list fell from 17 files to 8; the 7 test files of the `pipeline` package are gone from it.

- `[proof:` lines in the copy's Python files: 0 after (85 by `grep -rn` before; the plan says
  86). The two Python files still listed hold the three marks the upgrade left (no spec has
  their lettered proof); their tests had no tag docstring.
- All 29 tracked Python files parse; `uv run --project pipeline pytest --collect-only -q -c
  pipeline/pyproject.toml pipeline/tests`: `117 tests collected`, as before the upgrade.
- A second `--yes` run: `Nothing is pending: this project is at 0.10.0.`; `git status` clean.
- `purlin_run.py --test --all` without `--commit`: `Markers: 533 tied to a test, 0 not tied.`,
  `476 rules. 475 pass their tests.` The one is `project_history` RULE-11 (a browser test, a
  restore). `--test --feature project_history` alone, once: `476 rules. 476 pass their tests.`

## Lines chosen

- `    removed <n> docstring line<s> that held only a 0.9.5 tag` under the `markers` totals; in
  the log, the same with ` in <file>`.
- The docs: the paragraphs on the cited script, the docstring lines, the deleted file in git,
  and `Applying 3 migrations: anchor-lines, config, markers.` as the example.

Every other line is the plan's, word for word.

## Calls the plan did not make

1. Which options "narrow the run": a fixed list per tool. pytest `-k`, `-m`, `--deselect`,
   `--ignore`, `--ignore-glob`, `--lf`, `--last-failed`; vitest `--project`, `-t`,
   `--testNamePattern`, `--dir`, `--exclude`, `--shard`, `--changed`; jest `-t`,
   `--testNamePattern`, `--testPathPattern(s)`, `--testPathIgnorePatterns`,
   `--selectProjects`, `--shard`, `-o`, `--onlyChanged`, `--changedSince`. Any other option
   (`--coverage`, `--reporter`) is not named. "Closest" is the fewest of those, the first on a
   tie. It lives in `update.py`; `frameworks.py` is not changed.
2. The cited script also gives the launcher (before, the first script did).
3. The leave-out line shows in the listing and before each question, not in the applied run's
   totals.
4. A docstring that is the tag alone goes whole only where another statement follows it in the
   test; a tag that opened a multi-line docstring takes the blank lines under it and the
   quotes move down; the file is kept as it was where the result does not read as the same
   code. Lettered tags (`PROOF-1b`) in docstrings count as tags.
5. Agent files: `CLAUDE.md` and `AGENTS.md` by name in any folder (the root first), and any
   file under `.claude/`. They stay within the 20 shown.
6. `Applying ...` names the migrations pending at the start; one a later migration leaves
   pending is applied and has its totals line but is not named there. A `--apply` that names
   nothing pending prints the pending list as before.
7. With no commit before the run, the backups sentence leaves out `A file it deleted is in
   git, at <sha7>.`
8. `docs/upgrading.md` shows the old-marker warning in item C's new shape (lane `run3`'s line),
   so the page agrees after the merge.
9. The init skill gains item 5's sentence, the docstring line, the deleted-file sentence, the
   `Applying` line and the agent files first; `specs/skills/skill_init.md` gains no rule for
   them.
10. One code commit carries the six items: they change the same functions and test file.

## Left, or waiting on another lane

- **The line the upgrade prints for a marker it leaves is the line in the file before the
  rewrite.** In the copy, `parameter_lfo.test.ts`'s left tag is at 154 after the upgrade (one
  comment was written above it) and the upgrade prints 153; the full run's warning names 154.
  The contract keeps this lane from changing it. The change that would make the two agree:
  in `_apply_markers`, map each left line through the rewrite (count the lines added and
  removed above it in `new`) before printing `LEFT_NO_SPEC`. Item 9 can shift Python lines the
  same way where a removed docstring stands above a left mark; in the copy it moved none of the
  three.
- The full run's old-marker warning is still the one-line form; lane `run3` owns it.
- On the copy I ran the collect-only once in the original `RLabGenMusic` folder by mistake, for
  the before count (`117 tests collected`). It wrote no tracked file: `git status` there reads
  ` M .purlin/report-data.js`, as it did when this lane started.
