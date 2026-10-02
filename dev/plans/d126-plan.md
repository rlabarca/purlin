# Decision 126: the upgrade from 0.9.5 survives a real project; the build plan

Written by the coordinator on 2026-10-02 against local `main` after decisions 124 and 125
(`dev/plans/handoff.md`). Decision 126 is in `dev/plans/three-levels.md`. Three lanes, all
local, each in its own worktree. Nothing is pushed, tagged or signed.

## 0. The test this answers

A fresh agent upgraded a copy of a real 0.9.5 project (54 specs, 476 rules, 523 proof lines,
542 test markers; pytest run through `uv` from a subfolder `pipeline/`, vitest, no shell
suite), following `README.md` and `docs/upgrading.md` alone. The upgrade ran in 15 seconds and
made one commit. The first `purlin:test --all --commit` then ended at 57 of 476 rules passing.
Reaching 474 took hand repairs no page describes. The upgraded copy, with those repairs, is at
`/Users/richlabarca/LocalCode/purlin-wt/RLabGenMusic-upgrade` (read it, never change it); the
original is `/Users/richlabarca/LocalCode/RLabGenMusic` (never touch it; copy it with
`cp -Rc` to try a change). Logs of every step are in
`/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/81d9ae94-d490-4bd9-b502-b2caa661d1a4/scratchpad/upgrade-test/`
(`logs/`, `before/`).

The owner: "we need to fix up to 20". The twenty findings, each with what happened and what is
built, follow. The owner answered four questions; their answers are marked **Decided**.

## 1. The findings and what is built

### Lane `update`

1. **The marker rewrite leaves test titles the test run cannot match.**
   `'every route ... forwarded to it ' + '[proof:dev_proxy:PROOF-1:RULE-1:unit]'` became
   `'... forwarded to it ' + ''`. Variants seen: `+ ''` on its own line (150), `' +` then `''`
   on the next line (144), a tag at the start of a title leaving a leading space, the same in
   double quotes. 434 passing tests got no result.
   Built: where the tag is a whole string piece, the piece and its `+` go and the space beside
   it is trimmed, leaving one plain string. After rewriting a file the upgrade reads it back
   with the reader a test run uses and prints one line for each marker whose test title that
   reader cannot read, naming the file and line.
3. **The pytest plugin is deleted and the files that load it are left.** The upgrade printed
   `removed the plugin's wiring from conftest.py` after editing a sentence inside that file's
   docstring; the real lines, `sys.path.insert(...)` to `.purlin/plugins` and
   `pytest_plugins = ["pytest_purlin"]`, stayed, and `pipeline/conftest.py`, the one pytest
   loads, was neither touched nor listed. `npm run test:python` then failed with
   `ImportError: Error importing plugin "pytest_purlin"`.
   Built: every `conftest.py` in the project that names `pytest_purlin` loses that entry and
   the `sys.path` line pointing at `.purlin/plugins`; a file left with nothing but comments,
   a docstring and unused imports is deleted; each file is listed. Text inside a comment or a
   docstring is never edited.
4. **The pytest command it writes cannot work here.** It wrote
   `python3 -m pytest {files} --junitxml={report}`; the project runs `uv run --project pipeline
   pytest pipeline/tests`. **Decided: look and ask.** The upgrade looks at how the project
   already runs its tests, as first setup does (`scripts/init/scaffold.py` and
   `scripts/mcp/purlin/frameworks.py` hold what setup uses; reuse it, one home), shows the
   command it proposes for each test tool, and asks the owner to accept or correct it. `--yes`
   accepts the proposal. (The other half of this finding, `--all` and the file list, is lane
   `run`'s item 4b.)
5. **Lettered proofs are dropped without a word.** 34 proof lines in 17 specs read
   `- PROOF-7b (RULE-6): ...`. The upgrade neither lists nor rewrites them; 29 TypeScript tests
   keep their old tag with no message; 15 Python tests are reported with the message for a
   whole-module marker. **Decided: renumber.** A new migration gives each lettered proof the
   next free number in its spec, moves `> Highest-Proof:` where the spec has one, rewrites the
   marker of each test that named it, and prints each change as
   `piano_roll PROOF-7b is now PROOF-23`. It runs before the marker rewrite, so the markers are
   rewritten once with their final numbers. Like every migration it asks first.
   `scripts/spec/renumber.py` exists; reuse what fits.
8. **A marker was written into the middle of a title.** In
   `packages/web/test/track_import.integration.test.ts` the comment landed between two halves
   of a joined title. Built: the comment always goes above the line holding `it(` or `test(`
   (or the language's own test opener).
10. **The backups.** 151 untracked `.bak` files beside specs and tests; every plain
    `purlin:test` then selects all 54 features with the reason `a file is not tracked`.
    Built: backups go under `.purlin/runtime/update-backup/`, keeping each file's path, which
    git ignores. The update ends with one line saying where they are and that the folder can
    be deleted once the tests pass.
11. **What happens to the old record is not said.** Built: the update's ending and
    `docs/upgrading.md` say that every rule reads `not run` until the tests run again, that
    0.9.5's `verify:` commits stay in git as the earlier record, and that the receipts can be
    read from the commit before the upgrade.
12. **What the upgrade does not touch is not listed.** The project's `CLAUDE.md` still tells
    the agent to write `[proof:...]` markers and names the deleted plugin; 85 Python docstrings
    keep `[proof:...]` tags; `.gitignore` keeps three lines for files 0.9.5 wrote;
    a comment in `vitest.config.ts` still describes the Purlin reporter.
    Built: the update ends with a short part headed `Purlin left these for you:` from a search
    of tracked files for `[proof:`, `pytest.mark.proof`, `.purlin/plugins`, `purlin:verify` and
    `proofs-`, one line per file with a count, most first, at most 20 lines then
    `and <n> more files`. The stale `.gitignore` lines 0.9.5 wrote are removed by the upgrade.
15. **The README does not point at the upgrade page.** Built: one line under its install part:
    `Coming from 0.9.5? See [docs/upgrading.md](docs/upgrading.md).`
16. **Eight questions on one line.** With piped answers all eight questions print on one line
    with no answer shown. Built: each question on its own line, followed by the answer taken
    when input is not a terminal. `skills/init/SKILL.md` tells the agent to ask the person
    about each migration and how to pass each answer.
17. **The update's output is 377 lines, 302 of them per-file.** Built: per migration one line
    of totals (`markers: rewrote 498 markers in 94 files`); then the lines that need the owner,
    last, under their own heading. The per-file lines go to
    `.purlin/runtime/update-backup/update.log`, named in the ending.
20. **Standing notices look like upgrade problems.** `docs/upgrading.md` gains a short part,
    `What you will see`, with real shapes: every rule reads `not run`; the first full run takes
    as long as the suites; lines such as `<spec>: 1 file its scope names is not written yet`
    are about the project, not the upgrade; what done looks like for an upgrade.

### Lane `run`

2. **A title with an escaped apostrophe, or joined from several strings, never gets a result.**
   39 markers above titles like `it('a send is a tap after the node\'s own Amplifier ...')` and
   26 above `'first half ' + 'second half'` had no result while the run said
   `Markers: 497 tied to a test`. Built: the reader takes `\'` and `\"` as the character and
   joins string pieces joined with `+` (JavaScript and TypeScript; check the other languages
   the reader knows for the same). Where a title still is not one readable string (a template
   with `${}`; a variable), the run prints
   `<file>:<line>: the test's title is not one plain string, so its result cannot be matched. Write it as one string.`
   and the marker is not counted as tied.
4b. **`--all` runs the command with no file list from the top folder.** With
   `{files}` empty pytest missed `pipeline/pyproject.toml` and every file failed with
   `No module named 'rgm'`, while one or two features on their own worked. Built: find why
   `--all` drops the list and make a run with `--all` hand the tool the same files a run of
   every feature by name would, unless that breaks a limit you can show (then say which, keep
   it, and document it in `references/supported_frameworks.md` with what a project with its
   test settings in a subfolder must add). Report the call.
6. **Before the upgrade the status buries the one line that matters.** 162 lines, 85 of them
   `Run purlin:spec <name>`, ending `476 rules to write a test for: purlin:build`.
   **Decided: only the upgrade line.** While a migration is pending the status prints its
   first line, as today, and then only:
   `This project was set up by Purlin 0.9.5. Nothing here counts until it is brought to <version>.`
   `→ Run: purlin:init --update`
   No table, no warning, no `Left to do`. (`scripts/init/update.py`'s `pending` says whether
   one is; read it, do not change that file.) The MCP status tool answers the same.
7. **`Check that their tests ran and were not skipped`, when they ran and passed.** Built:
   where the report holds a passing or failing test in the marker's own file whose name
   differs from the source title only by white space, quotes or joined pieces, the run says so
   and shows both names, in place of the skipped-tests sentence for those markers.
13. **A settings change sets every result back, silently.** Built: a run or a status that
    finds the `tests` setting changed since the evidence was taken prints once
    `The tests setting changed, so every result is out of date.`
14. **`--commit` leaves work uncommitted without saying so.** Two deleted files and a test
    file with no marker stayed out of the commit, and the evidence is recorded as taken with
    uncommitted changes. Built: after `--commit`, where tracked files are still changed, the
    run names them (at most 10, then `and <n> more`) and says
    `Commit them, then run purlin:test --all --commit again: a sign-off needs results taken with nothing uncommitted.`
    Check that sentence against what `purlin:sign` really refuses and correct it to the truth.
18. **The commit subject names all 54 features** (about 900 characters). Built: over 5
    features the subject reads `purlin: specs, tests and settings for 54 features` and the
    body lists them; `references/commit_conventions.md` says so.
19. **A full run prints nothing for two minutes.** Built: one line as each suite starts,
    `Running pytest: <the command as run>`, flushed before the tool starts.

### Lane `dashboard`

9. **The dashboard opens on a wall of warnings.** 34 cards above the board. **Decided: one
   card per kind, with a count.** Warnings of the same kind become one card:
   `33 specs hold a proof line Purlin cannot read: piano_roll, sample_voice, and 31 more. Run purlin:status for each.`
   The general shape: `<n> specs <what>: <first two names>, and <n-2> more. Run purlin:status for each.`
   Two or fewer of a kind keep their own cards, as today. Different kinds keep their own
   cards. The board is within the first screen at 1500 by 900 with 34 such warnings in the
   data. The terminal status is unchanged.

## 2. The lanes

| Lane | Owns, and writes nothing else | Acceptance |
|---|---|---|
| `update` | `scripts/init/update.py`, `scripts/init/scaffold.py`, `scripts/spec/renumber.py`, `templates/`; `specs/init/update.md`, `specs/init/scaffold.md`; `dev/test_init_update.py`, `dev/test_init_scaffold.py`, the 0.9.5 sample under `dev/fixtures/upgrade-0.9.5` and its helpers; `docs/upgrading.md`, `README.md`, `skills/init/SKILL.md`, `specs/skills/skill_init.md`, `dev/test_skill_init.py`; `RELEASE_NOTES.md` | its test files, `dev/test_purlin_docs.py` and `dev/test_purlin_agent.py` pass |
| `run` | `scripts/run/*.py`, `scripts/mcp/purlin/*.py` but `payload.py`, `report_data.py`; `specs/run/*.md`, `specs/mcp/*.md`; their tests under `dev/` (`dev/test_run_script.py`, `dev/test_markers*.py`, `dev/test_reports.py`, `dev/test_states.py`, `dev/test_mcp_server.py`, `dev/test_evidence_*.py`, `dev/test_summary.py` and the like); `docs/running-and-evidence.md`, `skills/test/SKILL.md`, `skills/status/SKILL.md`, `references/supported_frameworks.md`, `references/commit_conventions.md`, `references/formats/marker_format.md` | its test files, `dev/test_purlin_docs.py`, `dev/test_skill_test.py`, `dev/test_skill_status.py` pass |
| `dashboard` | `scripts/report/src/*`, the rebuilt `scripts/report/purlin-report.html`, `scripts/mcp/purlin/payload.py`, `scripts/mcp/purlin/report_data.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report*.py`, `dev/test_report_refresh.py`, `dev/fixtures/report/`; `docs/dashboard.md` | its test files pass; looked at with playwright, both themes, 1500 and 390 |

What one lane makes and another uses, fixed here:

- Lane `update` calls the test run's reader of test titles to check its rewrite (item 1). It
  calls what exists on `main` today in `scripts/mcp/purlin/markers.py` and changes none of it.
  Lane `run` makes that reader read more (item 2) and keeps its present functions and their
  arguments as they are, so the call still works after the merges.
- Lane `run` reads `scripts/init/update.py`'s `pending(project_root)` for item 6 and changes
  none of it. Lane `update` keeps `pending` and what it returns as they are.
- The warning lettered proofs raise today disappears from an upgraded project once item 5 is
  built; lane `dashboard` builds its test from sample data it writes, not from that project.

Merge order: `run`, `update`, `dashboard`, each `--no-ff`.

## 3. The lane brief

Every lane reads, in order: `CLAUDE.md`; `references/writing_style.md`;
`dev/plans/three-levels.md`, decisions 119 to 126 (search `119. **`), and decision 44, the
clean release; this file in full; `references/spec_quality_guide.md` before writing a rule or
a proof; `docs/upgrading.md`.

- **Where.** `git worktree add /Users/richlabarca/LocalCode/purlin-wt/d126-<lane> -b
  lane/d126-<lane> main`, run from `/Users/richlabarca/LocalCode/purlin`. Every edit, run and
  commit happens in the worktree. Never edit the main tree. A scratch folder of your own:
  `/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/81d9ae94-d490-4bd9-b502-b2caa661d1a4/scratchpad/d126-<lane>/`.
- **What.** Only the files your lane owns. A change you need in another lane's file is not
  made: build the rest and report it with the exact change.
- **How.** Each fix starts from a test that fails for the fault, seen failing first, built on
  a sample project the test makes (extend the 0.9.5 sample with the real shapes above: the
  joined and escaped titles, the two `conftest.py` files, a lettered proof, a subfolder pytest
  project). Then try your change on a fresh `cp -Rc` copy of the real project in your scratch
  folder and say what happened there. Every rule and proof is written to
  `references/spec_quality_guide.md`; read each `> Highest-*` line before taking a number; a
  number is never used again; a reworded proof's test changes on a kept line in the same
  commit. Every line a person reads that this plan gives is used word for word; where it
  gives none, choose one by `references/writing_style.md` and report it. On a line a person
  reads, name a thing by what the person sees, not by the code's word for it.
- **Formats.** A change to a file under `references/formats/` goes in the same commit as its
  code; bump `> Format-Version:` only for a change of structure, and report it.
- **Tests.** `export PATH=/Users/richlabarca/LocalCode/purlin/.venv/bin:/opt/homebrew/opt/dotnet@8/bin:$PATH`
  first, in every shell: the system `python3` has no pytest. Acceptance is your lane's in
  section 2, then `bash dev/run_tests.sh --fast` (lane `dashboard`: the full
  `bash dev/run_tests.sh`), every failure yours to fix or named in your report as waiting on
  another lane. Run long commands in the foreground with a long timeout. No test reaches a
  real model.
- **Traps.** Never `git checkout -- specs/`. Stage nothing under `.purlin/`, no
  `docs/images/*.png`, no `purlin-report.html` at the repository root. No dollar figure, no
  count of model calls, no emoji. No push, no tag, no `purlin:sign`, no `purlin:audit`, no
  cloud session, no subagent. Never use `pkill` on anything but your own process ids. Never
  write in `/Users/richlabarca/LocalCode/RLabGenMusic` or in
  `/Users/richlabarca/LocalCode/purlin-wt/RLabGenMusic-upgrade`.
- **Commits.** Prefixes from `references/commit_conventions.md`, one logical change each,
  ending:

  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_019ZnevFpAcRMGNmDja38LB4
  ```

- **Finishing.** `git rebase main` in the worktree, the acceptance again, `git status` clean.
  Then write `dev/plans/d126-reports/<lane>.md` in the worktree and commit it: per finding,
  what was built; each rule and proof added or reworded, word for word; each `> Highest-*`
  before and after; what was seen failing first; what happened on the copy of the real
  project; every line a person reads that you chose; every call you made that the plan did
  not; what is left or waits on another lane. End your final message with the branch, its
  head, the acceptance's last line, the lines you chose and the calls you made.

## 4. Integration, by the coordinator, on `main`

1. The three merges. `bash dev/run_tests.sh` to 0 failed.
2. `purlin_run.py --test --all --commit` to the clean state; `python3 dev/windows_run.py`.
3. **The upgrade test again**, by a fresh agent that built none of it, on a fresh copy of the
   real project, with the same brief as the first test. Expect: the first
   `purlin:test --all --commit` after the upgrade ends with every test that passed under 0.9.5
   counted, with no hand repair; name each rule that is not, and why.
4. Fix what that run shows that is certain; list the rest for the owner.
5. The dashboard looked at on the upgraded copy's data, both themes, 1500 and 390.
6. `dev/plans/handoff.md` rewritten for where it stands.

## 5. The second round: five findings of the repeat test

The repeat test (a fresh agent, a fresh copy, at `main` after section 4's merges) reached
`Tests: met` with no hand repair: the first full run counted 474 of 476, the two misses being
the project's own unstable tests. Its copy is at
`/Users/richlabarca/LocalCode/purlin-wt/RLabGenMusic-upgrade-2` and its logs in
`.../scratchpad/upgrade-test-2/` (read both, change neither). It found these, and the owner
said: "Fix 1-5". Two lanes, `update2` and `run2`, with section 3's brief (worktrees
`d126-update2`, `d126-run2`; reports `dev/plans/d126-reports/update2.md`, `run2.md`).

### Lane `update2` (owns what lane `update` owned, plus `docs/specs-and-anchors.md`, `skills/spec/SKILL.md`, `specs/skills/skill_spec.md`, `dev/test_skill_spec.py`)

1. **438 kind-of-test tags are still in the specs and nothing says so.** `@browser` 160,
   `@integration` 160, `@unit` 114, `@e2e` 4, each on the last line of a proof that runs over
   several lines; `kind-tags` reads a proof's first line only and names `unit`, `integration`
   and `e2e` alone. Built: `kind-tags` and `os-tags` read a proof line with its continuation
   lines (the lines after it up to the next `- PROOF-`, `- RULE-`, heading or blank line). The
   kinds dropped are `unit`, `integration`, `e2e`, and every kind the project's own 0.9.5
   markers name in their last field (`[proof:<feature>:<id>:<rule>:<kind>]`,
   `pytest.mark.proof(..., kind)` where it has one), read before the markers are rewritten, so
   `@browser` goes here. `@manual`, `@slow` and `@env(...)` are never dropped. The totals line
   says how many tags went from how many specs.
2. **The listing run ends on a wrong instruction.** A run that applied nothing ended on the
   status, whose last line read `476 rules to write a test for: purlin:build`. Built: a run
   that applied nothing prints the pending list, the proposed test commands, and ends on
   `→ Run: purlin:init --update` with how to say yes (`--yes`, or `--apply`), and no status.
3. **The first `Left to do` after the upgrade does not open on the test run.** It read
   `1 test comment to correct: purlin:build` first, a state the project had before the
   upgrade, where the page shows only `476 rules to test: purlin:test`. Built: a run that
   applied a migration ends, after its other parts and in place of the status's `Left to do`,
   on `→ Run: purlin:test --all --commit` and the sentence
   `Run it before anything else: every rule reads not run until it has.` The upgrade page's
   `What you will see` lists a test comment to correct among the lines about the project, and
   says a test that passes when its feature is run alone is the project's own, not the
   upgrade's.
5. **The instruction for a marker the upgrade leaves is incomplete.** Built, word for word:
   `left <file>:<line> as it was: it names <feature> <id>, which no spec has. Write the proof with purlin:spec <feature>, put # purlin: <feature> PROOF-<n> above the test, and take the old tag out of the test's title or decorator.`
   (the comment in the file's own comment style). The spec page, the spec skill and
   `references/formats/spec_format.md` (wording only, no version) say where `> Highest-Rule:`
   and `> Highest-Proof:` go in a spec that has neither: after the last `>` line of the
   header.

### Lane `run2` (owns what lane `run` owned)

4. **A marker 0.9.5 wrote that is still in a test stops counting, and is named once.** The
   upgrade leaves nine (each names a lettered proof no spec holds). The first full run then
   says `533 tied, 0 not tied`, and no status or run mentions them again. Built: the status and
   every run print one warning while a tracked test file holds a 0.9.5 marker where 0.9.5 read
   it, a test's title or a `pytest.mark.proof` decorator (not a docstring, not a comment):
   `<n> tests still carry a marker from Purlin 0.9.5, which is not read: <file>:<line>, <file>:<line>, and <n-2> more. For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.`
   One or two are named with no `and <n> more`; one reads `1 test still carries`. It shows
   only in a project already brought to this version (a pending 0.9.5 project prints its three
   lines alone). Lane `update2` keeps `scripts/init/update.py`'s way of finding an old marker
   callable as it is today; read it or call it, and change none of that file. The dashboard
   shows the line as a notice, which needs no change to the page: check that it does.

Merge order: `run2`, `update2`. Then section 4's steps 1 to 6 again, the upgrade test by a
fresh agent on a fresh copy (`RLabGenMusic-upgrade-3`) included.
