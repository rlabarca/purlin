# Lane 12B: Review and Sign tabs, the Signable column, the bar on the page; docs and slides

Plan: `dev/plans/three-levels.md` (Part A, decisions 23 to 30; 30 is the one you render).
Rules: `dev/plans/lanes/tl-_rules.md` (in full). Read all of `design/readme.md` and
`docs/_mermaid.md`. Worktree `/Users/richlabarca/LocalCode/purlin-wt/12B`, branch `lane/12B`
off the stack tip. **Do not push. Do not open a pull request.** You run in parallel with lane
12A (the code and the schema 7 fixtures); write the fixture changes yourself exactly as
`tl-12A.md` spells them (`rules[].bar`, `bar_from`, `cleared`, `signable`; strong words
`not audited` and `unsettled`; `flags.unsettled`; summary and rollup `unsettled`,
`not_audited`, `signable`; `sign_list`; `schema_version` 7; no `risk`, no `not required`),
read only those keys in the JS, and the orchestrator rebases you onto 12A afterwards with
12A's fixtures winning.

## The board (`scripts/report/src/`)

- `app.js`: `SCHEMA = 7`; `CELL_TONES`: `not audited` idle, `unsettled` warn; `manual audit`
  and `not required` gone; the strings mirror `scripts/mcp/purlin/board.py` (12A adds
  `Signable`; mirror the shape `<n> of <rules>`).
- `board.js`: the `Signable` column between `Strong` and `Signed` at `signed`, hover listing
  the signable rule ids; a `To sign` flag card beside `Stale` at `signed`, fed by
  `summary.signable`, hover with the count by feature. Filters: `Untested`, `Failing`,
  `Partial`, then `Weak` and `To review` at `strong` and above (`To review` = the strong cell
  reads `manual test`, `unsettled` or `held`), then `To sign` and `Stale` at `signed`;
  `Unsigned` and `Stale or held` are gone; each pill shows its count and the spec states each
  pill's rule.
- Two tabs replace the review list: `Review (<n>)` at `strong` and above, rows grouped by
  kind (`manual test`, `unsettled`, `held`), bar `strong` first, columns feature, rule, text,
  bar, kind, reasons; `Sign (<n>)` at `signed`, rows from `sign_list`, columns feature, rule,
  text, bar, the signed cell's word (`unsigned` or `stale`), the command `purlin:sign
  <feature> <RULE-N>`. `review.js` becomes two body functions; the risk summary block is
  gone; the rule screen's risk row becomes `Bar: strong (from the tag)` or `(from the gate)`.
- Layout assessment as lane 11B did: four payloads, 1024 / 1280 / 1440 / 1920, both themes,
  every PNG looked at, a table per width in the report; no sideways scroll at 1024; the
  seven columns at `signed` fit.

## Tests and spec

`dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`: the two tabs, the
column, the flag card, the pills and their counts, the bar row. `specs/dashboard/purlin_report.md`
follows. Rebuild (1200-line limit), recapture the five screenshots (`dashboard-review-list.png`
becomes the Review tab; add `dashboard-sign.png` for the Sign tab and reference it from
`docs/dashboard.md`), look at each.

## Pages and slides

Every page: risk is gone; a rule has a bar; what `not audited`, `unsettled`, `signable` mean;
`sign_at` is `strong` or `all`; the two tabs. `docs/dashboard.md`, `docs/how-purlin-works.md`
(the chain table's strong and signed rows, the questions section), `docs/review-and-signing.md`
(Review then Sign; the walk), `docs/regulated-workflow.md`, `docs/team-workflow.md`,
`docs/solo-workflow.md` (one sentence: the bar defaults to `passed` here), `docs/specs-and-anchors.md`
(the tag), `docs/getting-started.md`, `docs/raising-the-gate-and-upgrading.md` (init's
`sign_at` question; the risk-to-bar migration), `README.md`, `docs/index.md`. Diagrams only
where a step changed; render and look. `dev/plans/lanes/tl-12B-slides.md`: the `signed` slide's
steps say Review then Sign; the `strong` slide's step 6 names `not audited` as what an audit
clears.

## Acceptance

```
python3 dev/build_report.py
pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_vocabulary.py
grep -rn "risk\b\|manual audit\|not required" docs/ README.md | grep -v "glossary\|retired"   (nothing; "risk" survives only where it describes the world, not a tag)
```

Report in the DONE shape of `tl-_rules.md`, with the spec maxima, the test delta, the floor
sum, the layout tables, the code lines each page was checked against once rebased, the full
contents of `tl-12B-slides.md`, and decisions.
