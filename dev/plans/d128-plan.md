# Decision 128: the owner's answers after the fourth upgrade test; the build plan

Written by the coordinator on 2026-10-02 against local `main` after decision 127
(`dev/plans/handoff.md`). Four lanes, local, each in its own worktree. Nothing is pushed,
tagged or signed. The brief is section 3 of `dev/plans/d126-plan.md`, with `d128` in every
path and branch, this plan in place of that one, decisions 119 to 128, and the report at
`dev/plans/d128-reports/<lane>.md`. Each fix starts from a test written first and seen
failing. The real 0.9.5 project is `/Users/richlabarca/LocalCode/RLabGenMusic` (never touch
it; `cp -Rc` it); the fourth test's copy is `/Users/richlabarca/LocalCode/purlin-wt/RLabGenMusic-upgrade-4`
(read it, never write in it), its logs in `.../scratchpad/upgrade-test-4/`.

## 1. What is built

### Lane `sign4`
1. **The signer sees a finding cleared by judgment.** The sign-off's list of audit findings
   (`audit_list_lines` in `scripts/review/sign.py`) also names each rule, of any verdict, with
   a proof settled with its test unchanged: one line,
   `<feature> <RULE-N>: PROOF-6 was settled with its test unchanged: it was judged to assert what the proof names.`
   (the sentence `no_bug` holds). It does not stop the sign-off. Owns `scripts/review/sign.py`,
   `specs/review/signatures.md`, `dev/test_signatures.py`, `dev/sign_project.py`,
   `docs/sign-off.md`, `skills/sign/SKILL.md`.

### Lane `update4`
3. **The upgrade removes the 0.9.5 instructions from the project's agent files itself**, with
   no question of its own: inside the `markers` migration (the one that already asks), every
   line of `CLAUDE.md`, `AGENTS.md` and the files under `.claude/` (any folder, as the leftover
   list finds them) that names `[proof:`, `pytest.mark.proof`, `.purlin/plugins`,
   `purlin:verify` or `proofs-` is removed; a bullet or table row is removed whole; a heading
   left with nothing under it is removed; each file is backed up first as every rewritten file
   is. The totals line: `removed <n> lines that named 0.9.5 from CLAUDE.md` (one per file);
   each removed line goes to `update.log`. `Purlin left these for you:` then no longer lists
   those files for those lines. `docs/upgrading.md` says so.
7. **The upgrade page says an unstable test may need more than one run alone**, and that
   making it stable is the project's work. One sentence, beside the existing one.
   Owns what lane `update3` owned in `d127-plan.md`.

### Lane `run4`
4. **`purlin:status <name>` shows one spec's rules.** As `skills/status/SKILL.md` already
   describes: the spec's path and rule count, then one line per rule with its two cells and,
   where a cell is not `passed` or `strong`, its reasons, then the proof lines behind it. The
   mistake check stays, printed first where the spec has a mistake. The script is
   `scripts/run/purlin_status.py` (its `--spec <name>`), and the status tool gains the same
   view where it is given a spec's name, if it takes one. Match the skill's example; where the
   skill's example is not what the code can print, correct the skill and report it.
6. **An anchor whose results are out of date says so in its Tests cell** in the terminal:
   `0 of 11 · 11 out of date`, the count of its rules whose passed cell reads `out of date`,
   after the other parts the cell already has. A feature's row is unchanged.
   Owns what lane `run3` owned in `d127-plan.md`, but `scripts/mcp/purlin/payload.py` and
   `report_data.py`.

### Lane `dashboard4`
6. **The same on the dashboard**: an anchor's Tests cell reads `0 of 11 · 11 out of date`,
   from the rules' passed cells, worded as the terminal words it.
8. **The count boxes stand above the warnings at every width.** Order: the top bar, the count
   boxes, the notices, the anchors, the specs. Owns what lane `dashboard3` owned in
   `d127-plan.md`; the docs' two screenshots are retaken by the coordinator if they change.

Not built, by the owner's answers: a `Left to do` line for tests with a 0.9.5 marker, a
`Left to do` listing every kind at once, a retry of unstable tests.

## 2. Contracts

- The out-of-date part of an anchor's cell is `· <n> out of date`, terminal and page alike,
  after `by hand`, `partial` and `failing` where those show.
- `markers` stays the migration's id; lane `update4` adds no migration and no question.

Merge order: `run4`, `update4`, `dashboard4`, `sign4`. Then the sweep, `--test --all --commit`,
the Windows run, the dashboard looked at, and the upgrade tried on a fresh copy by the
coordinator: the project's `CLAUDE.md` after the upgrade holds no line naming 0.9.5.
