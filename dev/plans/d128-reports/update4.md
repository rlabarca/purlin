# Decision 128, lane `update4`: the report

Branch `lane/d128-update4`, from `main` at `ff3a7be98`. Nothing pushed, tagged or signed.

## What was built

| Item | Built |
|---|---|
| 3 | Inside `markers`, with no question of its own, each line naming `[proof:`, `pytest.mark.proof`, `.purlin/plugins`, `purlin:verify` or `proofs-` goes from each tracked `CLAUDE.md` and `AGENTS.md` (any folder) and each Markdown or JSON file under `.claude/`, the files the leftover list finds. A list item goes whole (its continuation lines and the items under it); a table row alone, the table where no row is left (or where its header names it); a fenced-code line alone, the block with its fences where nothing is left; a settings line between the `---` lines at the top of a file alone, the `---` lines staying; in a paragraph, the sentence holding it; a heading left with nothing under it goes. The blank lines a removal leaves side by side become one, and two breaks (`---`) left side by side become one. Each file is backed up first; each removed line goes to `update.log` as `removed <file>:<n>: <line>`, each shortened one as `<file>:<n> now reads: <text>`; under the `markers` totals: `    removed <n> lines that named 0.9.5 from <file>`. The markers migration's description and its pending list name the agent files too. |
| 7 | `docs/upgrading.md`, beside the existing sentence: `Such a test may need more than one run alone to pass, and making it pass every time is the project's work.` |

`pending(project_root)`, `rewrite_markers` and the left-marker line are unchanged. No migration and no question added; `markers` keeps its id.

## Rules and proofs

`specs/init/update.md`: `> Highest-Rule:` 71 to 73, `> Highest-Proof:` 216 to 220. No file under `references/formats/` changed.

- RULE-72: Where the `markers` migration is applied, each line naming `[proof:`, `pytest.mark.proof`, `.purlin/plugins`, `purlin:verify` or `proofs-` goes from each tracked `CLAUDE.md` and `AGENTS.md`, in any folder, and each Markdown or JSON file under `.claude/`: a list item goes whole, with the lines that continue it and the items under it; a table row goes alone, and the table where no row is left; a line of a fenced code block goes alone, and the block where nothing is left in it; a line of the settings between `---` lines at the top of a file goes alone, and the two `---` lines stay; in a paragraph the sentence holding it goes; a heading left with nothing under it goes; every other line is as it was
- RULE-73: Each file whose lines naming what 0.9.5 used the `markers` migration removes is first copied to the backup folder, each line removed or shortened is written to `update.log`, and under the line of totals of `markers` one line reads `removed <n> lines that named 0.9.5 from <file>`, `<n>` counting the lines that named it; `Purlin left these for you:` then no longer names the file; where `markers` is declined, the file is as it was, and a JSON file that would no longer read as JSON, or a file of another kind under `.claude/`, is left as it was and listed
- PROOF-217 (RULE-72): A `CLAUDE.md` holding a list item whose second line holds `[proof:`, with an item under it, a table row naming `purlin:verify`, a heading whose one paragraph names `.purlin/plugins/`, a line naming `purlin:verify` in a fenced code block under `npm test`, a paragraph whose first sentence names `proofs-` and one whose last sentence names `.purlin/plugins/`, and a sentence above them naming nothing, in a project with a test 0.9.5 marked, is after the update with `--yes` exactly that file with the item and the item under it, the row, the heading with its paragraph, the code line and the two sentences gone, one blank line between what is left, and `markers` is no longer pending
- PROOF-218 (RULE-72): In the same project, `pipeline/AGENTS.md` with a list item naming `purlin:verify`, `.claude/commands/ship.md` ending with such an item, `.claude/commands/check.md` whose settings at the top hold `description: Run purlin:verify.`, and `.claude/settings.json` whose list `allow` ends with `"Skill(purlin:verify)"` lose those lines after the update with `--yes`, `ship.md` reading `Ship it.` alone, `check.md` keeping its two `---` lines and `Check the build.`, and the settings reading as JSON with `allow` holding `Bash(npm test)` alone; `.claude/hooks/check.sh`, naming `purlin:verify`, is byte for byte as it was and listed under `Purlin left these for you:` with `1 line`
- PROOF-219 (RULE-73): After that `CLAUDE.md` is updated with `--yes`, the line after `  markers: rewrote 2 markers in 1 file` reads `    removed 6 lines that named 0.9.5 from CLAUDE.md`; `update.log` holds `removed CLAUDE.md:<n>: <line>` for the item's second line, the row, the heading and the code line, and `CLAUDE.md:30 now reads: Mixed features keep their`; the backup holds the file's bytes from before; no line under `Purlin left these for you:` names `CLAUDE.md`, and `git status` lists nothing
- PROOF-220 (RULE-73): With the question for `markers` answered `n` and every other `y`, that `CLAUDE.md` is as it was, no line of the output holds `that named 0.9.5`, and the output holds `  CLAUDE.md: 6 lines. Change it first: it tells the agent to write what this release does not read.`

No rule or proof was reworded; RULE-63 ("it changes none of them") still holds, since a file cleaned is no longer listed.

## Seen failing first

The four tests were written first and run on the unchanged `update.py`: PROOF-217, 218 and 219 failed; PROOF-220 is a negative and passed before and after. The front-matter case was added to PROOF-218 after the first code and seen failing (`'---\n\nCheck the build.\n'`) before its fix.

## On a copy of the real project

A fresh `cp -Rc` of `RLabGenMusic` in the scratch folder, `scaffold.py --update --yes` from this worktree, exit 0, 88 lines. The listing run (input empty, on a second fresh copy) lists `CLAUDE.md` first under `markers`.

Totals:

```
  markers: rewrote 533 markers in 95 files
    removed 85 docstring lines that held only a 0.9.5 tag
    removed 4 lines that named 0.9.5 from CLAUDE.md
```

`Purlin left these for you:` now lists first `  packages/web/test/parameter_lfo.test.ts: 2 lines`, then `stem_order.browser.test.tsx: 2 lines`; 7 files, no agent file. `git grep` of the five words in `CLAUDE.md`: none. `git status` clean; a second `--yes`: `Nothing is pending: this project is at 0.10.0.`

The diff of `CLAUDE.md` (`git show HEAD~1:CLAUDE.md` against the upgraded file), 816 lines to 803:

```diff
@@ -314,16 +314,6 @@ proxy target.
 
 ## Working agreements
 
-- **Purlin, spec-driven.** Write the spec in `specs/<group>/<feature>.md` (3 sections:
-  What it does / Rules / Proof), then tests whose *names* carry the marker
-  `[proof:<feature>:PROOF-n:RULE-n:<tier>]`. Three TS tiers — `unit`, `integration`,
-  `browser` (Playwright + Chromium, for anything needing real Web Audio). `npm run verify`
-  runs all of them plus the Python proofs.
-- **Python proofs only record when pytest runs from the repo root.** `pipeline/pyproject.toml`
-  makes `pipeline/` the rootdir, so the root `conftest.py` is above the cut-off and never
-  loads; `pipeline/conftest.py` is the copy that registers the collector, and the collector
-  writes `specs/<group>/*.proofs-*.json` relative to the *working directory*. Use
-  `npm run test:python`. A green `cd pipeline && uv run pytest` records nothing at all.
 - **The design system is an anchor.** `specs/_anchors/rlab_design_system.md`. Its rules are
   the kind that erode one component at a time, so half are greps over the source (no colour
   literal, no emoji, no second easing, no inset shadow) and half are `getComputedStyle`
@@ -603,9 +593,6 @@ margin over random is the small one, so the initialiser and the objective remain
 leverage is. `--from match` starts from the last accepted patch; `--from params` is the
 comparable baseline.
 
-The TS proof collector (`.purlin/plugins/vitest_purlin.ts`) accepts sub-lettered ids
-(`PROOF-4b`); Purlin's own static checks do not, so new proofs of one rule are numbered.
-
 The agent pane is live: it reads the folder, edits `config.json`, and works every control in
 the registry -- transport, audition, mix, master, solo, key, meter, loop, variation, effects
 on any chain, LFOs, stem order, tracks, parameters by name, saved settings. Re-running the
@@ -709,8 +696,7 @@ button on the imported view, `POST /convert`, and the ask-gated `convert_to_trac
 (`asks: true` on the declaration; the pre-approved fold excludes asking declarations —
 pre-approval would be silence). `projects/groovevox/` is the pack converted: seven tracks,
 kick/toms/snare/snare_2/cymbals/cymbals_2/bass, matched to Kicker, DrumSynth and the
-Analog generator. A python + TS feature keeps python proofs in the unit tier and TS proofs
-in integration: the python collector owns a feature's `proofs-unit.json` wholesale.
+Analog generator.
 
 **Converting arrives on its own, and one voice can join another project.** The
 imported-to-official flip no longer rides on a single SSE event (`sunvox_tracks`
```

It reads sensibly: `## Working agreements` now opens on the design-system bullet; the paragraph on the search numbers is followed directly by the one on the agent pane, one blank line between; the GrooveVox paragraph ends `... DrumSynth and the Analog generator.` Line 368, ``Forty-eight features. `npm run verify` runs typecheck, three TypeScript tiers and the Python proofs``, names none of the five words and stays.

## Lines chosen

- `    removed <n> line<s> that named 0.9.5 from <file>` is the plan's; `<n>` counts the lines that held one of the five words (4 in the real file, the number the leftover list showed before), not every line removed (14 there, the bullets' other lines included).
- In the log: `removed <file>:<n>: <line>` and `<file>:<n> now reads: <text>`.
- The `markers` description: `rewrite each 0.9.5 marker as a comment above its test, and remove each line naming what 0.9.5 used from CLAUDE.md, AGENTS.md and the files under .claude/`.
- Item 7's sentence above; the upgrade page's paragraph `The agent's instructions.`, its example, and `A CLAUDE.md is listed only where markers did not run.`

## Calls the plan did not make

1. **A matching line inside a fenced code block goes alone**, and the block goes with its fences where nothing is left in it. Code lines stand alone like table rows; a list of commands keeps its others. A code sample can be left broken where the line was a test's opening line; the alternative, removing any block that names 0.9.5 whole, loses unrelated commands.
2. **In a paragraph the sentence goes, not the line.** Removing the line alone left half-sentences on the real file (`(PROOF-4b); Purlin's own static checks do not, ...` and `... and TS proofs`). A sentence ends at `.`, `!` or `?` with white space and then anything but a lowercase letter after it. Where a sentence fills the paragraph, the paragraph goes.
3. A list item goes with the items under it; a nested item that names 0.9.5 under one that does not goes alone.
4. A table whose header names 0.9.5 goes whole, and so does one left with no row.
5. A heading goes only where it had something under it before and nothing after.
6. Files: `.md`, `.markdown`, `.mdc`, `.txt` are read as Markdown; `.json` loses its lines, a comma left before `]` or `}` is dropped, and the file is left as it was where the result does not read as JSON. Any other file under `.claude/` (a hook script) is left and stays listed.
7. The settings at the top of a file (between `---` lines) lose a matching line alone and keep both `---` lines.
8. **The agent files do not make `markers` pending on their own.** They are cleaned only where `markers` has a test marker to rewrite; a project with none keeps its `CLAUDE.md`, listed first under `Purlin left these for you:`. Otherwise a project at this version whose `CLAUDE.md` names `purlin:verify` would read as set up by 0.9.5. Where `markers` is pending, the agent files are listed first among its files.
9. The docs' example under `Purlin left these for you:` now shows `.claude/hooks/check.sh` in place of `CLAUDE.md`.

## Acceptance

`dev/test_init_update.py`, `dev/test_init_scaffold.py`, `dev/test_skill_init.py`,
`dev/test_purlin_docs.py`: `137 passed, 6 skipped`. `bash dev/run_tests.sh --fast` on the final
code: `1113 passed, 9 skipped`, `Suites: 1 passed, 0 failed`. An earlier full run, before the
front-matter fix, had one failure, `dev/test_collaboration.py::test_three_people_reach_a_signed_version`
(a `git clone` of its own temporary repository exited 128); it passed alone and in the final run.

## Left, or waiting on another lane

- None waits on another lane.
