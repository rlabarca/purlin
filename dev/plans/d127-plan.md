# Decision 127: the open items after the third upgrade test; the build plan

Written by the coordinator on 2026-10-02 against local `main` after decision 126
(`dev/plans/handoff.md`, `dev/plans/d126-reports/upgrade-tests.md`). Decision 127 is in
`dev/plans/three-levels.md`. Five lanes, all local, each in its own worktree. Nothing is
pushed, tagged or signed.

The real 0.9.5 project is `/Users/richlabarca/LocalCode/RLabGenMusic`: never touch it; copy it
with `cp -Rc` to try a change. Three upgraded copies are under
`/Users/richlabarca/LocalCode/purlin-wt/` (`RLabGenMusic-upgrade`, `-upgrade-2`, `-upgrade-3`):
read them, never write in them. The third test's logs are in
`/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin/81d9ae94-d490-4bd9-b502-b2caa661d1a4/scratchpad/upgrade-test-3/`.

## 1. What is built, by lane

### Lane `run3`

A. **A full run says which test files it left out.** `purlin:test --all` hands each tool the
   files that carry a marker (decision 126). **Decided: marked files only, and say so.** Where
   the `files` patterns of a suite match test files that carry no marker, a run with `--all`
   prints, after the `Markers:` line,
   `12 test files carry no marker and were not run.` (`1 test file carries no marker and was not run.`)
   Nothing is printed at zero or on a run without `--all`.
C. **The warning for tests that still carry a 0.9.5 marker names every one, with its rule.**
   **Decided.** In the terminal (the status, every run, the status tool):
   ```
   9 tests still carry a marker from Purlin 0.9.5, which is not read:
     packages/web/test/parameter_lfo.test.ts:153  parameter_lfo RULE-4
     ...
   For each, write the proof with purlin:spec, put the comment above the test, and take the old tag out.
   ```
   One line per test, the feature and the rule read from the old marker itself (a marker that
   names no rule shows the feature alone), sorted by file then line; over 20, the first 20 and
   then `  and <n> more`. In the dashboard's data it is one line:
   `9 tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each.`
   **The line number is the one the upgrade prints** for the same marker (`left <file>:<line>`):
   the status and the upgrade name one line, the old tag's own.
6. **The closing line does not promise a sign-off the sign-off would refuse.** Find what
   `purlin:sign` refuses on results taken on an earlier version of the code, and make the
   status's closing line agree with it: where every rule passes on the committed evidence and
   the sign-off would still refuse for that reason, the line reads
   `Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results taken on this commit.`
   and where it would not refuse, the line it has today. Correct the words to what the code
   does and report them.
7. **The test skill says how `--commit` is passed.** `skills/test/SKILL.md`, step 1.
11. **The status skill says when the uncommitted-results line shows**: only once nothing else
    stops the tests being met (decision 116). The behaviour stays.
14. **The status of a 0.9.5 project whose upgrade is pending writes no dashboard page and no
    data file.** It prints its three lines and writes nothing.

### Lane `update3`

5. **The applied run's ending says what to do with a test that fails in the full run.** After
   `Run it before anything else: every rule reads not run until it has.` it prints
   `A test that fails in that run and passes when its feature is run alone is the project's own: purlin:test <feature>.`
8. **`CLAUDE.md` comes first under `Purlin left these for you:`**, as its own line:
   `  CLAUDE.md: <n> lines. Change it first: it tells the agent to write what this release does not read.`
   The same for `AGENTS.md` and any file under `.claude/` that holds such lines.
9. **A docstring line that is only a 0.9.5 tag goes.** The `markers` migration removes a line
   of a Python docstring that holds nothing but a `[proof:...]` tag (and the docstring where
   that leaves it empty), for a test whose marker it rewrote. A tag inside a sentence stays and
   is counted under `Purlin left these for you:`.
10. **The proposed command cites the script it matches.** For vitest the proposal cited
    `"test"` (`vitest run --project unit`) beside a command with no `--project`. Built: cite
    the script whose command the proposal is closest to (here `test:all`, `vitest run`), and
    where the cited script narrows the run with an option the proposal leaves out, say so:
    `  The proposal leaves out --project unit, so every vitest test runs.`
12. **The backups sentence says what is kept.**
    `Every file the update rewrote is kept as it was under .purlin/runtime/update-backup/, with each change listed in update.log there. A file it deleted is in git, at <sha7>. Delete the folder once the tests pass.`
13. **The apply run does not print the pending list again.** It prints one line,
    `Applying <n> migrations: <ids>.`, then the totals.

### Lane `dashboard3`

B. **A failing rule is on the first screen.** **Decided: a failing box, and failing specs
   first.** A `Failing` count box, in the fail tone, stands after `Passing` only where at
   least one rule's passed cell reads `failed`; it counts those rules, and its hover names
   each spec with its count. Within the anchors and within each category, a spec with a
   failing rule comes before one with none, the rest of the order as today; a category holding
   a failing rule comes before one holding none. Nothing changes on a page with no failure.
1. **The page shows every line the terminal prints between the table and the sentence.** The
   terminal printed `1 spec names no files, so its tests run every time: patch_graph. Run
   purlin:spec patch_graph to add its > Scope: line.` and the page did not. Find every such
   line the status prints that the page's data does not carry, and carry it.

### Lane `sign3`

15. **No sign-off while a test still carries a 0.9.5 marker.** **Decided: refuse.**
    `purlin:sign` refuses, before the walk, with
    `No sign-off: 9 tests still carry a marker from Purlin 0.9.5, which is not read. Run purlin:status to see each, rewrite them, then purlin:sign.`
    (`1 test still carries`). `--show` prints the same line and exits as it does for any
    refusal it shows. `scripts/mcp/purlin/status.py`'s `old_markers(project_root)` is the one
    home of which tests those are: call it, change none of it.

### Lane `settle`

E. **A settle is refused where the test has not changed since the finding.** **Decided.**
   For a proof whose kept bug reads `survived`, where that proof's tests are the same as when
   the bug got past them, `--settle` plants nothing and prints, under the rule,
   `  PROOF-2: its test is as it was when the bug got past it. Strengthen it with purlin:build, then settle.`
   and the rule stays `weak`. Where the build read the test and judged it already asserts
   what the proof names, it passes an explicit option naming the proof, and the settle then
   goes on as today; the evidence records, on that proof's entry, that the test was not
   changed. Choose the option's name and the field by `references/writing_style.md` and the
   format's own style; a new field is a format change: bump `> Format-Version:` of
   `evidence_format.md` and, where the package carries the entry, `package_format.md`, in the
   same commit as the code, and report it. "The same test" means the proof's own marked tests
   read as the audit reads them, not the whole file; if the evidence does not yet hold what
   is needed to tell, say what you stored and why. `skills/build/SKILL.md` step 2's "Never
   change a test that already asserts what its proof names" gains how to settle such a proof;
   `skills/audit/SKILL.md`, `references/review_criteria.md` ("Settling a finding", the one
   home), `references/purlin_commands.md` and the reasoning part of `docs/audit.md` follow.
   The six bullets under "What to do with a finding" in `docs/audit.md` are the owner's and
   are not changed.

## 2. The lanes

| Lane | Owns, and writes nothing else |
|---|---|
| `run3` | `scripts/run/*.py` (but the handling of lane `settle`'s new option in `purlin_run.py`), `scripts/mcp/purlin/*.py` but `payload.py`, `report_data.py`, `frameworks.py`; `specs/run/*.md`, `specs/mcp/*.md`; their tests under `dev/`; `docs/running-and-evidence.md`, `skills/test/SKILL.md`, `skills/status/SKILL.md`, `specs/skills/skill_test.md`, `specs/skills/skill_status.md`, `dev/test_skill_test.py`, `dev/test_skill_status.py`, `references/supported_frameworks.md`, `references/evidence_and_signoff.md` |
| `update3` | `scripts/init/*.py`, `scripts/mcp/purlin/frameworks.py`, `templates/`; `specs/init/*.md`; `dev/test_init_update.py`, `dev/test_init_scaffold.py`, `dev/fixtures/upgrade-0.9.5`; `docs/upgrading.md`, `skills/init/SKILL.md`, `specs/skills/skill_init.md`, `dev/test_skill_init.py`; `RELEASE_NOTES.md` |
| `dashboard3` | `scripts/report/src/*`, the rebuilt `scripts/report/purlin-report.html`, `scripts/mcp/purlin/payload.py`, `scripts/mcp/purlin/report_data.py`; `specs/dashboard/purlin_report.md`; `dev/test_purlin_report*.py`, `dev/test_report_refresh.py`, `dev/fixtures/report/`; `docs/dashboard.md`; `docs/images/*.png` are retaken by the coordinator |
| `sign3` | `scripts/review/sign.py`; `specs/review/signatures.md`; `dev/test_signatures.py`, `dev/sign_project.py`; `docs/sign-off.md`, `skills/sign/SKILL.md`, `specs/skills/skill_sign.md`, `dev/test_skill_sign.py` |
| `settle` | `scripts/review/audit_run.py`, `ai_audit.py`, `targeted_break.py`, `marked_tests.py`; the parsing and refusal of its one new option in `scripts/run/purlin_run.py` and nothing else there; `specs/review/ai_audit.md`, `specs/review/planted_bug.md`; `dev/test_ai_audit.py`, `dev/test_ai_audit_tests_named.py`, `dev/test_planted_bug.py`, `dev/sample_lab.py`, `dev/fake_claude.py`; `references/review_criteria.md`, `references/purlin_commands.md`, `references/glossary.md`, `references/formats/evidence_format.md`, `references/formats/package_format.md`; `skills/build/SKILL.md`, `skills/audit/SKILL.md`, `specs/skills/skill_build.md`, `specs/skills/skill_audit.md`, `dev/test_skill_build.py`, `dev/test_skill_audit.py`; `docs/audit.md` |

What one lane makes and another uses, fixed here:

- `status.old_markers(project_root)` keeps its name, its argument and its `(file, line)`
  pairs as the first two members of each item it returns; lane `run3` may add members after
  them. Lane `sign3` calls it.
- Lane `run3` changes the line `old_markers` gives to the one the upgrade prints. Lane
  `update3` does not change which line the upgrade prints for a marker it leaves.
- The dashboard's data carries the old-marker warning as the one line item C gives; lane
  `run3` writes it (the status adds it today); lane `dashboard3` needs no change for it.
- Lanes `run3` and `settle` both edit `scripts/run/purlin_run.py`: `settle` only where
  `--settle` is parsed, refused and handed to the audit; `run3` everywhere else.
- If the package's format version moves (lane `settle`), `dev/test_export.py` and
  `scripts/export/package.py` may need the number: lane `settle` may make that one change
  there and reports it.

Merge order: `run3`, `update3`, `dashboard3`, `sign3`, `settle`, each `--no-ff`.

## 3. The lane brief

Section 3 of `dev/plans/d126-plan.md`, with `d127` in every path and branch, this plan in
place of that one, decisions 119 to 127, and the report at
`dev/plans/d127-reports/<lane>.md`. Its traps hold. Each fix starts from a test that fails for
the fault, seen failing first: write the test before the code.

## 4. Integration, by the coordinator, on `main`

1. The five merges. `bash dev/run_tests.sh` to 0 failed.
2. `purlin_run.py --test --all --commit` to the clean state; `python3 dev/windows_run.py`.
3. The run of the already-upgraded real project before and after: the same markers tied to
   the same tests and the same rules passing, the project's unstable tests aside.
4. The upgrade test again, by a fresh agent, on a fresh copy.
5. The dashboard looked at, both themes, 1500 and 390: a page with a failing rule, and the
   docs' screenshots retaken where they changed.
6. `dev/plans/handoff.md` rewritten for where it stands.

Not in this round, by the owner's answers: the audit of Purlin's out-of-date specs and a real
AI session given a goal on a sample project both wait for the last step before signing.
