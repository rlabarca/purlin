# Decision 127, lane `dashboard3`: the report

Branch `lane/d127-dashboard3`, items B and 1 of `dev/plans/d127-plan.md`.

## What was built

**B. A failing rule is on the first screen.** A `Failing` box stands after `Passing` wherever a
rule's passed cell reads `failed`. It counts those rules in the fail tone (`--state-fail`, the
token `FAILED` already uses), and its hover names each spec with its count, `invoice · 1`, one to
a line. The page reads what the data already carries, each rule's passed cell: no new key, schema
16 stands. Among the anchors and within each category a spec with a failing rule comes first, and
a category holding one comes before one holding none; the rest keeps the data's order. Where a
spec fails and no anchor does, the spec table stands above the anchors (a call of mine, below).
Under 1024 pixels four boxes stand four to a line, and two to a line under 768.

**1. The page shows the lines the terminal prints between the table and the sentence.** The
status printed five kinds of line its data did not carry: each anchor rule that passes with
nothing to check, the line naming the specs with no `> Scope:` line, the tests setting changed,
each anchor whose pin is not current, and the uncommitted spec files.
`report_data.with_status_lines` adds them to a copy of the payload as the data file is written:
the first two open `information`, the other three open `warnings`. Each line comes from
`status.py`'s own functions and constants, so the words have one home. `data` itself is left
alone, so the terminal prints exactly what it printed before. Three or more anchor rules with
nothing to check group as one neutral notice (RULE-82 gains that kind).

Files: `scripts/report/src/app.js`, `board.js`, `styles.css`, the rebuilt
`scripts/report/purlin-report.html`, `scripts/mcp/purlin/report_data.py`, the docstring of
`scripts/mcp/purlin/payload.py`, `specs/dashboard/purlin_report.md`, `dev/test_purlin_report.py`,
`dev/test_report_refresh.py`, `docs/dashboard.md`.

## Rules and proofs, word for word

`> Highest-Rule:` 82 before, 85 after. `> Highest-Proof:` 262 before, 279 after. PROOF-276 was
written and taken out in this lane (the update line, below), so 276 is spent and unused.

Reworded: RULE-63 and RULE-82 (no proof of either reworded). Added: RULE-83, RULE-84, RULE-85.

- RULE-63: The anchors stand in a section of their own between the boxes and the spec table, but where RULE-84 stands the spec table first, headed `Anchors` in the small capitals of the section labels, one row per anchor in the spec table's columns, row format, hovers and opening, with no band; the spec table holds no anchor. Where the project has no anchor the section is absent
- RULE-82: A grouped notice says of its specs what their warnings are about: `hold a line under ## Rules with no number`, `write a rule's number twice`, `write a proof's number twice`, `hold a line left from a merge conflict`, `have a name no test comment can name`, `hold a proof line Purlin cannot read`, `name another spec on the first line`, `tag a proof @slow and @manual`, `carry > Requires:, which Purlin does not read`, `carry > Global:, which Purlin does not read`, `carry > Scope:, which Purlin does not read on an anchor`, `come from a source with a line Purlin does not read`, `have a proof reworded after its test was last changed`, `have an evidence file Purlin ignores`, and, for the lines of information, `name a file in the scope that is not written yet` and `have a rule that passes with nothing to check here`
- RULE-83: Wherever a rule's passed cell reads `failed`, a `Failing` box stands after `Passing`, counting those rules in the fail tone, its hover naming each spec that holds one with its count, as `<spec> · <n>`, one to a line; where no rule's passed cell reads `failed` the board draws no such box
- RULE-84: A spec with a rule whose passed cell reads `failed` is listed before a spec with none, among the anchors and within each category; a category holding such a spec stands before one holding none; and where a spec that is no anchor holds such a rule and no anchor does, the spec table stands above the anchors' section. Otherwise the specs, the categories and the two tables keep the order they have with no such rule
- RULE-85: The data file's `information` and `warnings` together hold every line the status prints between its table and its summary sentence but `→ Run: purlin:init --update`, in the status's words: `information` opens with each anchor rule that passes with nothing to check and then the line naming the specs with no `> Scope:` line; `warnings` opens with the line that the tests setting changed, then each anchor whose pin is not current, with no `Anchors:` heading, then the uncommitted spec files on one line, as `Uncommitted spec changes: <status> <file>, <status> <file>`

- PROOF-263 (RULE-83): Open the board with the solo sample, where invoice `RULE-2` is the one rule whose passed cell reads `failed`; the boxes read, left to right, `No proof`, `Passing` and `Failing`, `Failing` reads `1` in the fail tone, and its hover reads `invoice · 1`
- PROOF-264 (RULE-83): Open the board with the team sample, where refund's 2 rules read `failed`, after security_baseline `RULE-1` is given `failed` too; after `No proof` the boxes read `Passing`, `Failing` 3 and `Strong`, and the hover of `Failing` reads the two lines `refund · 2` and `security_baseline · 1`
- PROOF-265 (RULE-83): Open the board with the regulated sample, where no rule's passed cell reads `failed` and login `RULE-4` reads `partial`; the boxes read `No proof`, `Passing` and `Strong`, the anchors read checkout_design then security_baseline, the bands `auth` then `billing`, and the specs login, invoice, export
- PROOF-266 (RULE-84): Open the board with the team sample, whose data lists login of `auth`, then invoice, receipt and refund of `billing`, refund alone holding a rule that reads `failed`; the bands read `billing` then `auth`, and the specs refund, invoice, receipt, login
- PROOF-267 (RULE-84): Open the board with the team sample after security_baseline `RULE-1` is given `failed`; the anchors read security_baseline then checkout_design
- PROOF-268 (RULE-84): Open the board with the team sample after invoice `RULE-2` is given `failed` beside refund's; the specs read invoice, refund, receipt, login
- PROOF-269 (RULE-84): Open the board at 1500 by 900 pixels with the regulated sample given the 4 notices a real project showed, two warnings and two lines of information, and 41 more specs, the last of them, `zz_last` of the last category `zeta`, the only one with a rule that reads `failed`; the section labels read `SPECS` then `ANCHORS`, the first band is `zeta` and its first row `zz_last`, and that row and the `Failing` box both end above the bottom of the screen
- PROOF-278 (RULE-84): Open the board with the team sample, where refund holds a rule that reads `failed` and no anchor does; the section labels read `SPECS` then `ANCHORS`, the boxes above both
- PROOF-279 (RULE-84): Open the board with the team sample after security_baseline `RULE-1` is given `failed`; the section labels read `ANCHORS` then `SPECS`
- PROOF-270 (RULE-85): In a project whose one spec, login, has no `> Scope:` line, run `purlin:status`; the first line it prints below its table is `1 spec names no files, so its tests run every time: login. Run purlin:spec login to add its > Scope: line.`, it prints that line once, and the data file's `information` holds exactly that line
- PROOF-271 (RULE-85): In a project whose anchor screens passes `RULE-1` on a test that skipped with `nothing to check: this project has no screens`, run `purlin:status`; the first line below its table and the one line of the data file's `information` both read `screens RULE-1 passes with nothing to check here: this project has no screens.`
- PROOF-272 (RULE-85): In a project whose `tests` setting gained `-v` after its evidence was committed, run `purlin:status`; it prints `The tests setting changed, so every result is out of date.` below its table, and that line is the first of the data file's `warnings`
- PROOF-273 (RULE-85): In a project whose anchor policy is pinned to the first of its source's two commits, run `purlin:status`; the line `policy: the pin <old> is behind its source, now <new>. Run purlin:anchor sync policy.` is printed below the table and is in the data file's `warnings`, which holds no line reading `Anchors:`
- PROOF-274 (RULE-85): In a project with `specs/auth/login.md` edited and `specs/auth/logout.md` new, neither committed, run `purlin:status`; it prints `Uncommitted spec changes:` and under it ` M specs/auth/login.md` and `?? specs/auth/logout.md`, and the data file's `warnings` holds `Uncommitted spec changes: M specs/auth/login.md, ?? specs/auth/logout.md`
- PROOF-277 (RULE-85): In a project the update has nothing for but an older `purlin-report.html`, run `purlin:status`; it prints no line between its table and its sentence, and the data file's `warnings` and `information` are both empty
- PROOF-275 (RULE-82): Open the board with the regulated sample given no warning and 4 lines of information, checkout_design's `RULE-1`, `RULE-2` and `RULE-3` each passing with nothing to check, then the line naming export as a spec with no `> Scope:` line; the 2 notices read `checkout_design has a rule that passes with nothing to check here, in 3 places. Run purlin:status checkout_design.` and that line whole, each with a dot in the neutral tone

## Seen failing first

The 13 new tests then on hand were run against `main`'s page and code before any change: 12
failed (no `Failing` box; the data file held none of the status's extra lines; the nothing-to-check
lines drawn one notice each). PROOF-265's test passed, as it should: it holds what stays. PROOF-278 and PROOF-269's real-notices version failed against the
first build, which had the order without the section swap: the failing row ended at 1071 pixels.
PROOF-277 failed against an interim build that carried the update line, then passed.

## What the terminal order is, and where the page differs

`status._table` sorts by the count of rules left to do of any kind (`-_left_count`, then name),
anchors first, with no categories. The page keeps categories and moves only specs with a rule
whose passed cell reads `failed`. So a spec with many `no test` rules leads the terminal and does
not move on the page. The page's notices also keep their order, warnings before information,
where the terminal prints the information first and the warnings last.

## On the copy of the real project

`cp -Rc` of `RLabGenMusic-upgrade-3` at `4366261`, data written with the worktree's
`scripts/run/purlin_status.py`. The terminal output is byte for byte what it was before the change.
The data file's lines equal the four lines the terminal prints between table and sentence, and
the page draws those 4 notices: the reworded proof and the 0.9.5 markers (warn tone), the specs
with no files and the spec ahead of its code (neutral). The board: `No proof 0`,
`Passing 475 / 476 RULES TOTAL`, `Failing 1` (hover `project_workspace · 1`); `SPECS` above
`ANCHORS`; band `SERVER` first, row `project_workspace` `10 of 11 · 1 failing` first. The status
took 11.4 s with the change and 11.3 s on `main`.

## What the page looked like

Playwright from the `.venv`, 900 high, both themes (the two measure the same). Sideways scroll 0
and no value on two lines at every width, on every page. Pixels from the top:

| Width | Real: boxes | Real: `Failing` box | Real: failing row | Team: `Failing` box | Team: failing row |
|---|---|---|---|---|---|
| 1500 | 467 | 467 to 600 | 780 to 836 | 238 to 371 | 551 to 606 |
| 1280 | 467 | 467 to 600 | 780 to 836 | 238 to 371 | 551 to 606 |
| 1024 | 508 | 508 to 641 | 821 to 876 | 258 to 391 | 571 to 626 |
| 768 | 625 | 625 to 758 | 920 to 1003 | 314 to 447 | 609 to 693 |
| 390 | 1019 | 1168 to 1279 | 1441 to 1555 | 574 to 685 | 847 to 961 |

At 1500 by 900 on the real copy the `Failing` box and the failing row are both on the first
screen. At 390 the four notices take the first screen. The regulated sample, which has no failing
rule: full-page screenshots of this page and `main`'s page are byte for byte the same at all five
widths in both themes.

## The docs' screenshots

They do not change. `dev/capture_doc_screenshots.py` uses the regulated sample, in which no rule's
passed cell reads `failed` (login `RULE-4` failed on Windows and passed on Linux, so it reads
`partial`; its row keeps its `FAILED` badge). The board is unchanged there, as above.

## Lines chosen

- The box's label `Failing`, its hover `<spec> · <n>`, one to a line.
- `Uncommitted spec changes: M specs/auth/login.md, ?? specs/auth/logout.md`: the status's heading
  and its lines joined on one line, each as git names it.
- An anchor's pin line stands as the status words it, without the `Anchors:` heading.
- The grouped notice for anchor rules with nothing to check: `<name> has a rule that passes with
  nothing to check here, in <k> places. Run purlin:status <name>.`, and
  `<n> specs have a rule that passes with nothing to check here: ...`.
- `docs/dashboard.md`: the `Failing` bullet and a paragraph "Failing specs first".

## Calls made that the plan did not

1. **The spec table stands above the anchors where a spec fails and no anchor does.** Without
   it the failing row on the real copy ends at 1071 at 1500 by 900: four notices, the boxes and
   the two-row anchors table stand above it. RULE-63 is reworded to allow it. Undo it in
   `renderBoard` (`specsFirst`) if the owner wants the anchors always above.
2. **`Failing` counts the passed cell's `failed` only**, as the plan says. A rule that failed on
   one system and passed on another reads `partial`, carries `FAILED` on its row, and is not
   counted.
3. **No new key, no schema change.** The lines go in the data file's own two lists, added when the
   file is written, not in the payload `build_payload` returns. The payload, the evidence package
   and `states` RULE-27's seventeen keys are unchanged.
4. **`→ Run: purlin:init --update` is not carried.** Lane `run3`'s tests in
   `dev/test_mcp_server.py` (the 0.9.5-marker line is the data's last warning) and
   `dev/test_states.py` (`information == [line]`) leave it no place in either list. To carry it,
   lane `run3` would change those two assertions and `with_status_lines` would add
   `status_module.ending_lines(data, project_root)[:-1]` at the end of `information`, the last
   notice drawn, as it is the last line the status prints above its sentence.
5. Five of the lines are worked out twice per status, once for the terminal and once for the
   data file; the pin check reads each remote anchor's source twice. The exact change that ends
   it, lane `run3`'s: `status.sync_status` builds these lines once (`with_status_lines`) and hands
   them to `report_data.refresh`, which would take them as an argument.
6. `with_status_lines` calls `status._pin_lines` and `status._uncommitted_specs`, which are private
   to lane `run3`'s module. Making them public is lane `run3`'s change.
7. The fixtures are not regenerated: team's invoice has no `> Scope:` line and its fixture's
   `information` does not hold that line, as a fixture is a payload, not a data file.

## What is left

Items 4, 5 and 6 above wait on lane `run3`. The old-marker line reaches the data file as lane
`run3` writes it; nothing here changes for item C.

## Acceptance

`python3 -m pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_report_refresh.py dev/test_purlin_docs.py`: 118 passed.
`bash dev/run_tests.sh`: 1155 passed, 9 skipped; `Suites: 4 passed, 0 failed`.
