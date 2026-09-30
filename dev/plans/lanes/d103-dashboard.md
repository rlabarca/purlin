# Lane `dashboard` of decision 103: report

Branch `lane/d103-dashboard`, made from `origin/d103/base` at `e5f82d0`. Built to
`dev/plans/d103-plan.md` section 4, L7, and contracts C4 and C13.

## What was built

- The page reads payload schema 13. `GATE_LEVELS` is `passed`, `signed`.
- Gone from the page: the `Signed` column, box, badge, cell row and panel, the `Signatures` row
  and signature links, `DOES NOT APPLY` and the ` · <k> does not apply` count, the ended reason,
  `waiting for the audit`, the minimum strength in every hover and in the Audit panel,
  `no minimum strength applies: mutation testing is off`, and the buttons `To test by hand`,
  `To confirm`, `To audit`, `To measure`, `To sign` and `To tag`.
- The `Strong` box, column, `STRONG` badge, strong cell row and Audit panel show at either gate
  wherever `summary.audit` has a strong or weak rule, and nowhere else. The test strength in the
  `Strong` cell carries no tone. The Audit panel's strength line reads `Test strength <p>%.`
- The `No proof` box and the always-on `Proofs` column follow the gate `signed`.
- A `@manual` proof reads C13's line at `signed`.
- The boxes wrap three to a row under 1024 pixels (there are at most three), two under 600.
- Fixtures at schema 13: solo at `passed`, no audit; team at `passed` with an audit (a weak rule
  under `To strengthen`, one spec to repair); regulated at `signed` with a hand check
  (invoice `RULE-3`) and `signed/1.4.0` on HEAD. security_baseline `RULE-1` is now `no test`.
- `docs/dashboard.md`, `dev/capture_doc_screenshots.py`'s docstring and
  `scripts/mcp/purlin/report_data.py`'s docstring say the same.

## Highest lines

| Spec | Highest-Rule | Highest-Proof |
|---|---|---|
| `specs/dashboard/purlin_report.md` | 71 (was 68) | 222 (was 217) |

## Rules and proofs

- **Deleted rules:** RULE-26 (signature panel), RULE-61 (no minimum with mutation off), RULE-62
  (hand check names `purlin:sign <feature> RULE-N`), RULE-65 (does not apply), RULE-67 (ended
  signature).
- **Deleted proofs:** PROOF-26, 39, 89, 90, 186 (RULE-26); 199 (RULE-61); 200, 201, 202
  (RULE-62); 210, 211, 212, 213, 214 (RULE-65); 216 (RULE-67); 131, 133 (`To tag`); 149 (the gate
  `strong`); 191 (nobody signed), with their tests.
- **Reworded rules:** RULE-8, 9, 13, 14, 15, 16, 37, 39, 44, 49, 50, 51, 55, 59.
- **Reworded proofs:** PROOF-8, 10, 14, 15, 16, 20, 35, 40, 42, 44, 45, 53, 59, 76, 79, 81, 85, 98,
  113, 114, 115, 116, 119, 124, 125, 126, 130, 142, 144, 161, 162, 164, 165, 166, 167, 169, 174,
  188, 190, 192, 193, 203, 206.
- **New:** RULE-69, no `Signed` column at either gate (PROOF-218). RULE-70, the `Strong` column
  only where a rule was audited (PROOF-219 team, PROOF-220 solo). RULE-71, a `@manual` proof's
  line (PROOF-221 at `signed`, C13's words; PROOF-222 at `passed`, one more than the plan named,
  because the rule states the line at both gates).
- Every proof written or rewritten is one case in at most 60 words with a marked test.

## Tests

- Before, my three files (`dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`,
  `dev/test_report_refresh.py`): 201 passed.
- After: 187 collected, 182 passed, 5 failed, each waiting for another lane (below).
- Deliberate break: `boardColumns` drew `Strong` with nothing audited; PROOF-220's test failed
  (`assert 'Strong' not in ['Spec', 'Rules', 'Proofs', 'Tests', 'Strong']`), then
  `git checkout -- scripts/report/src/board.js` restored it and the test passed.
- The browser ran: `pip install playwright==1.56.0` in the lane's own `.venv` matches
  `/opt/pw-browsers/chromium-1194`; no committed helper changed.
- `bash dev/run_tests.sh --fast`: 7 failures, none in a file this lane owns but PROOF-59 (below).

## Tests that fail only because another lane has not merged

- PROOF-65, PROOF-152, PROOF-110, PROOF-111 (`dev/test_purlin_report.py`): each builds a real
  project, and today's `payload.py` writes schema 12. With `SCHEMA_VERSION = 13` set by hand (not
  committed) all four pass. Waits on lane `counting`.
- PROOF-59 (`dev/test_report_refresh.py`): `release.run_release(root, '1.0.0')`, then
  `sign.py --answers` with `{"strong": "go on", "stops": {}, "sign": true}`; the data file is
  written again and its `tag.name` reads `signed/1.0.0`. Waits on lanes `release`, `signoff` and
  `counting`.

## Failures in files this lane does not own

- `dev/test_states.py` PROOF-82 and PROOF-96 (`TestTheFixturesAreTheContract`) and
  `TestStatusTable::test_the_table_and_the_dashboard_show_the_same_cells`: they compare the
  fixtures and the page with today's builder and `board.py`. The key difference is exactly C4's:
  the fixtures carry `summary.audit.*`, `summary.weak`, `rollup.weak`, `flags.strong`,
  `flags.weak`, and lack `rollup.signed`, the signed cell's keys, `does_not_apply`, `ended`,
  `hand_checked`, `features[].signatures`, `gate.min_strength`, `summary.signed` and
  `summary.steps.{strong,signed}`. PROOF-96 also still expects team at `strong`. Lane `counting`
  owns the file.
- `dev/test_signatures.py` `TestTheMachines` (2 tests) and `dev/test_tag.py`
  `test_the_tag_is_signed_with_the_key_the_settings_name`: fail the same way on `d103/base`
  in this Linux container; not caused by this lane.

## Calls left, reported

- **The tag chip at `passed`.** C4's `tag` may name a `passed/*` tag; the page still shows the tag
  chip at `signed` alone, as before.
- **`purlin:sign` refreshing the data file.** C8 does not say. RULE-41 keeps naming
  `purlin:sign`, and PROOF-59 needs lane `signoff`'s `sign.py` to call `report_data.refresh` after
  the sign-off commit.
- **`summary.proofs` and `rollup.proofs*`.** C4 does not list them; the page reads them (the
  `Proofs` column and whether the page names proofs), so the fixtures keep them.
- **A verdict `undecided`** reads `weak` in the fixtures' strong cells, as before.
- **RULE-62 deleted and RULE-71 added**, as section 4 numbers them, rather than RULE-62 reworded.
- **One predicate for the audit**, `summary.audit.strong + weak > 0`, decides the box, the column,
  the badge, the strong cell row and the Audit panel.
- **RULE-45** still says text on a solid badge is not held to 7:1; no solid badge remains. Left.
- **`feature.incomplete`** still draws `<name> · no scope` (RULE-43); C4 does not say whether the
  payload keeps it.

## Words chosen that section 7 does not give

- A `@manual` proof at `passed`: `Checked by hand. A release at the gate passed lists it as not checked.`
- The `no signed tag` hover: `This commit carries no signed tag. The first purlin:sign after purlin:test --release writes signed/<version>, and a person pushes it.`
- The Audit panel's strength: `Test strength 86%.` (the audit's own `STRENGTH_LINE`, C2).
- RULE-69: `The board carries no Signed column at either gate: a sign-off covers a release's evidence package, not a rule`.

## Not done here

- `dev/capture_doc_screenshots.py` was not run; the two docs images need retaking at integration.
- `scripts/report/purlin-report.html` is rebuilt locally and not staged.
