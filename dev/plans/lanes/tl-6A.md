# Lane 6A: docs rewrites

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Read all of `design/readme.md` and `docs/_mermaid.md` before you write. Worktree
`/Users/richlabarca/LocalCode/purlin-wt/6A`, branch `lane/6A` off `three-levels`.

You start from the phase 0 commit and write from Part A. Phases 1 to 4 land on `three-levels`
while you work; when the orchestrator tells you phase 4 is merged, `git rebase three-levels`,
open the five regenerated `docs/images/dashboard-*.png` and check `docs/dashboard.md` against
what they show, check every command, path, message and table you cite against the code as it
then is, run the acceptance again, then report. Until then, write the dashboard page from
Part A6 and the three fixtures in `dev/fixtures/report/`.

## What you own (Part C2, phase 6A)

Full rewrites:

- `docs/dashboard.md`: the board (headline, tiles per gate, columns per gate, expanded rows,
  filters), the rule screen (spec status, cell rows, Proofs, the Brief panel at `strong` and
  above, the Sign panel at `signed`), the review list tab (header, risk summary, rows). Each
  screenshot is referenced where the text describes it.
- `docs/regulated-workflow.md`: the `signed` gate end to end; the mermaid `stateDiagram-v2`
  redrawn as spec status → passed → strong → signed with the `stale` and `code changed`
  edges, using the init block from `docs/_mermaid.md`; the walk; holds; notes; the branch
  rulesets; what CI writes (records and briefs, never a signature).
- `git mv docs/review-and-approval.md docs/review-and-signing.md` and rewrite: the brief
  (what it reports, that it recommends nothing), the review list, the walk's four answers,
  `--note`, `--hold`, `--batch`, when a signature counts, `signature stale`.

Section rewrites (line numbers are from the phase 0 tree):

- `docs/running-and-records.md` L15, L103, L117, L180, L192, L246–264: `purlin:audit`, the
  record at format version 2, `source`, `code changed`, no breaks under `passed`, the local
  preview under `strong`, `record/<name>` tags, the record commit with briefs.
- `docs/team-workflow.md` L1–8, L21–24, L62, L64, L99, L115: the `strong` gate; only a CI
  record counts; the review list at `strong`; `purlin:sign --note` and `--hold` without
  signatures being required.
- `docs/getting-started.md` L50–65, L161–175: the three gate answers, `purlin:test`,
  `purlin:audit`, `purlin:sign`.
- `docs/raising-the-gate-and-upgrading.md` L12–16, L32–50, L73, L111–124, L129–134: the
  three values and what each raise adds (breaks on at `strong`; signer list, `sign_at`, risk
  and origin required at `signed`); `purlin:init --update` from 0.9.5 lands on the new layout
  and drops the old approvals; the user re-signs.
- `docs/working-together.md` L68–72, L136–137, the drift samples: the drift rows
  `qa.signatures_stale`, `qa.review_list_size`, `qa.needs_person`, `eng.code_changed`.
- `RELEASE_NOTES.md`: overwrite the 0.10.0 entry to describe this model: the spec status,
  the three levels and their three commands, the gate values, what CI writes, the brief,
  signatures and holds, the migration, every retired word and its replacement, the format
  versions (record 2, signature 3, payload schema 5, drift criteria 4). Keep the counts line
  that `dev/test_purlin_version.py` reads in the shape it expects; the orchestrator fills the
  numbers after phase 7.

Every doc link to `review-and-approval.md` or `approval_format.md` in the files you own
points at the new names; lane 6B fixes `docs/index.md` and its own pages.

## Words

Part A1 in full; the sentence shapes of `design/readme.md` "Content fundamentals". Never a
retired word.

## Expected red

Anything outside `dev/test_vocabulary.py` and `dev/test_docs*.py` (if present) may be red
while phases 1 to 4 land; name each red file in your report.

## Acceptance

```
pytest dev/test_vocabulary.py $(ls dev/test_docs*.py 2>/dev/null)
grep -rn "review-and-approval\|approval_format" docs/ README.md   (nothing outside lane 6B's files)
```
