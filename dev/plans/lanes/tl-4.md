# Lane 4: dashboard

Plan: `dev/plans/three-levels.md` (in full). Rules: `dev/plans/lanes/tl-_rules.md` (in full).
Read all of `design/readme.md` before you write a line. Worktree
`/Users/richlabarca/LocalCode/purlin-wt/4`, branch `lane/4` off `three-levels`.

Your contract is the three fixtures `dev/fixtures/report/solo.json` (gate `passed`),
`team.json` (`strong`) and `regulated.json` (`signed`), schema 5, written by hand from Part
B1. The payload builder (lane 1A) lands the same shape in parallel; you build against the
fixtures and need nothing from the Python side. `regulated` carries one stale rule (login
RULE-2), one held rule (login RULE-3), one `needs a person` rule (checkout_design RULE-1),
one `code changed` rule (export RULE-1), two `weak` rules (invoice RULE-1 and RULE-2) and one
`windows: no record yet` rule (login RULE-4). `team` carries an unsettled review (login
RULE-1), a weak rule and a developer record that does not count.

## What you own (Part B5)

- `scripts/report/src/app.js`: `SCHEMA = 5`; `STATES` and `TONES` replaced by `BUCKETS`
  (`untested`, `failing`, `passed`, `strong`, `signed`) and `CELL_TONES` (`passed`, `strong`,
  `signed` pass; `failed`, `stale` fail; `no test`, `not run`, `code changed`, `unsigned`,
  `weak`, `needs a person`, `held` warn; `drafted`, `not required` idle; `ready` pass);
  `pill(word)` solid only for `signed`; `hasRisks`, `hasRecords`, `hasApprovals` replaced by
  `level(name)` reading `DATA.gate.gate` (`level('strong')` is true at `strong` and `signed`).
- `board.js`: headline `<met> of <rules> rules meet the gate <gate> · <failing> failing`;
  `statStrip` from `DATA.summary` and `level()`: tiles `Untested`, `Failing`, `Passed`, then
  `Strong` at `strong`, then `Signed` and a `Stale` flag card at `signed`; `riskGrid` deleted;
  `boardColumns` per Part A6: `Spec`, `Rules`, `Spec status` (`ready · drafted`), `Tests`
  (`passed · failing · no test`, each count in its tone), `Last run` (source, os, age), then
  `Strength` and `Strong` (`n of m` with a bar) at `strong`, then `Signed` (`n of m`, stale
  count in the fail tone) at `signed`. No risk column, no coverage column, no state column, no
  risk-by-state grid. Expanded rule rows: id, text, one pill per existing cell.
- `filters.js`: `Untested`, `Failing`; `Weak` at `strong`; `Unsigned`, `Stale or held` at
  `signed`; each gated by `level()`.
- `rule.js`: spec status, then one row per existing cell with its word and reasons, then
  Proofs; `briefPanel` at `strong` and above (strength beside the minimum, the findings, the
  observations, each in one sentence naming the proofs it concerns, and whether it settled);
  `signPanel` at `signed` (`purlin:sign <feature> <RULE-N>` or `Signed by <email>`);
  `signerOf` reads the signature file's third dot part.
- `review.js`: tab exists at `strong` and above; header `<n> rules need a person`; the risk
  summary block, one line per risk with counts of unsigned, stale, held and needs-a-person;
  rows grouped by risk high first, stale and held first within a group; six columns: feature,
  rule id, text, risk tag, the blocking cell's word, its reasons; `why` tokens rendered as
  sentences.
- `styles.css`: `.tiles` uses `repeat(auto-fit, minmax(0,1fr))`; `.strip` two columns only
  when the flag card exists; `.grid` rules deleted; `.rev` six columns. Tokens only from
  `design/tokens/theme-dark.css` and `theme-light.css`, both themes ship, no colour literal,
  no gradient, no shadow, no icon beyond `▶ ▼ ▲ →`, no emoji.
- `dev/capture_doc_screenshots.py`: descriptions in the new words; the five shots keep their
  names; regenerate the five `docs/images/dashboard-*.png` after `python3 dev/build_report.py`.
- `scripts/report/purlin-report.html`: rebuilt by `dev/build_report.py` and committed with the
  source in the same commit. The 1200-line limit (`purlin_report` RULE-2) holds.

## Tests

`dev/test_purlin_report.py` (L227, L242, L360, L375, L387, L423, L436, L493, L524, L614, L689
and `FILTER_CASES`; its docstring describes the fixtures at schema 5),
`dev/test_purlin_report_board_layout.py` (L41, L56). Every assertion reads a word from Part
A2 or A6. Every marker names the spec's feature and RULE id after your renumbering.

## Spec

`specs/dashboard/purlin_report.md`: rewrite RULE-7, RULE-8, RULE-9, RULE-13, RULE-15, RULE-16,
RULE-18, RULE-26, RULE-30, RULE-32 and their proofs; keep RULE-2's limit; read every other
rule and fix any that names an old state, tile, column or filter.

## Words

Tiles `Untested Failing Passed Strong Signed Stale`; columns per Part A6; cell words per
Part A2; `meets the gate`; `needs a person`. Never a state name from the old ladder, never
`approve`, `approval`, `re-verify`, `Proof ready`.

## Expected red

Everything outside `dev/test_purlin_report*.py` and `dev/test_vocabulary.py` may be red in
your worktree while phases 1 to 3 land; you own none of it. Name every red file in your
report.

## Acceptance

```
python3 dev/build_report.py
pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_vocabulary.py
python3 dev/capture_doc_screenshots.py   (then look at each of the five PNGs and describe what it shows in your report)
wc -l scripts/report/purlin-report.html   (1200 or under)
```
