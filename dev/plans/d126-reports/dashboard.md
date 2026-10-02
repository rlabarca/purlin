# Decision 126, lane `dashboard`: the report

Branch `lane/d126-dashboard`, one finding: item 9, the dashboard opens on a wall of warnings.

## What was built

Three or more warnings of one kind, each about one spec, are drawn as one notice where the first
of them stood. The page tells a kind from the warning's own sentence: `NOTICE_KINDS` in
`scripts/report/src/app.js` holds one pattern per sentence the status writes about one spec, and
the spec's name is the pattern's one group. The data keeps its shape: no new key, schema 16
stands, and `scripts/mcp/purlin/payload.py` and `report_data.py` are unchanged. The terminal
status is unchanged.

Files changed: `scripts/report/src/app.js`, the rebuilt `scripts/report/purlin-report.html`,
`specs/dashboard/purlin_report.md`, `dev/test_purlin_report.py`, `docs/dashboard.md`.

## Rules and proofs, word for word

`> Highest-Rule:` 80 before, 82 after. `> Highest-Proof:` 256 before, 262 after.

Reworded, RULE-22 (its three proofs and their tests hold as written):

- RULE-22: The board draws the notice that the working tree has uncommitted changes, `The working tree has uncommitted changes, so what is on this board is not what a commit would carry.`, then the warnings the data carries, each a notice of its own, whole, but those RULE-81 draws as one, above the boxes; a rule's screen draws neither

Added:

- RULE-81: Three or more warnings of one kind, each about one spec, are drawn as one notice where the first of them stood, reading `<n> specs <what>: <first two names>, and <n-2> more. Run purlin:status for each.`, `<n>` the specs they name, and its hover names every one of those specs, one to a line. Where they name two specs it reads `2 specs <what>: <a> and <b>. Run purlin:status for each.`, and where one, `<name> <what>, in <k> places. Run purlin:status <name>.`, `<k>` the warnings. The lines of information group the same way, in the neutral tone. One or two of a kind, and a warning that is about no one spec, keep a notice each
- RULE-82: A grouped notice says of its specs what their warnings are about: `hold a line under ## Rules with no number`, `write a rule's number twice`, `write a proof's number twice`, `hold a line left from a merge conflict`, `have a name no test comment can name`, `hold a proof line Purlin cannot read`, `name another spec on the first line`, `tag a proof @slow and @manual`, `carry > Requires:, which Purlin does not read`, `carry > Global:, which Purlin does not read`, `carry > Scope:, which Purlin does not read on an anchor`, `come from a source with a line Purlin does not read`, `have a proof reworded after its test was last changed`, `have an evidence file Purlin ignores`, and, for the lines of information, `name a file in the scope that is not written yet`
- PROOF-257 (RULE-81): Open the board at 1500 by 900 pixels with the regulated sample given 34 warnings, one unreadable proof line in each of 33 specs, the first two piano_roll and sample_voice, then one test whose proof was reworded; exactly 2 notices are on screen, `33 specs hold a proof line Purlin cannot read: piano_roll, sample_voice, and 31 more. Run purlin:status for each.` and the reworded proof's warning whole, the first one's hover lists the 33 names one to a line, and the first row of the `Anchors` table and the first row of the spec table both end above the bottom of the screen
- PROOF-258 (RULE-81): Open the board with the regulated sample given 5 warnings, an unreadable proof line in login and one in invoice, then three `signed/<version> is not in this checkout` lines, which are about no one spec; 5 notices are on screen, each warning whole, and none has a hover
- PROOF-259 (RULE-81): Open the board with the regulated sample given 6 warnings, an unreadable proof line of export, one test whose proof was reworded, then unreadable proof lines of export, invoice, login and login; the notices read, in order, `3 specs hold a proof line Purlin cannot read: export, invoice, and 1 more. Run purlin:status for each.` and the reworded proof's warning
- PROOF-260 (RULE-81): Open the board with the regulated sample given 3 unreadable proof lines, all of login; the one notice reads `login holds a proof line Purlin cannot read, in 3 places. Run purlin:status login.`; with the third line invoice's instead it reads `2 specs hold a proof line Purlin cannot read: login and invoice. Run purlin:status for each.`
- PROOF-261 (RULE-81): Open the board with the regulated sample given no warning and 4 lines of information, a file not written yet in the scope of each of export, invoice, login and refund; the one notice reads `4 specs name a file in the scope that is not written yet: export, invoice, and 2 more. Run purlin:status for each.`, its dot is in the neutral tone, and its hover lists the 4 names
- PROOF-262 (RULE-82): Open the board with the regulated sample given, for each of the 14 kinds of warning the status writes about one spec, that warning for export, invoice and login, 42 warnings; 14 notices are on screen, each reading `3 specs <what>: export, invoice, and 1 more. Run purlin:status for each.` with the `<what>` RULE-82 gives its kind, in the rule's order

## Seen failing first

The six tests were run against the page as `main` built it, before the rebuild. Five failed,
each on the page drawing every warning as its own notice (33 notices where 1 is expected).
PROOF-258's test passed, as it should: it holds what stays as it was.

## On the real project's data

The page was opened over a copy of
`/Users/richlabarca/LocalCode/purlin-wt/RLabGenMusic-upgrade/.purlin/report-data.js` in the
scratch folder. That file holds 34 warnings: 33 unreadable proof lines across 12 specs and one
reworded proof. The page draws 4 notices: the uncommitted tree, `12 specs hold a proof line
Purlin cannot read: control_language, effect_calibration, and 10 more. Run purlin:status for
each.`, the reworded proof's warning whole, and the one line of information. The plan's `33
specs` counted warnings; the notice counts specs, as its words say.

## Lines chosen

The `<what>` of each kind, as RULE-82 lists them, and two shapes the plan does not give:

- Two specs: `2 specs <what>: <a> and <b>. Run purlin:status for each.`
- One spec with three or more warnings of a kind: `<name> <what>, in <k> places. Run purlin:status <name>.`, with the verb in the singular, as in `login holds a proof line Purlin cannot read, in 3 places. Run purlin:status login.`

## Calls made that the plan did not

1. A kind is told from the warning's sentence, in the page. No schema change.
2. The count is of specs, not of warnings. Three or more warnings of a kind group, however many
   specs they name.
3. The lines of information, a spec whose scope names a file not written yet, group the same
   way, in the neutral tone.
4. A grouped notice's hover names every spec it counts, one to a line, as a `title`. It is no
   new control.
5. Not grouped, since each is about no one spec: two spec files with one name, the line naming
   the spec files that carry a tag this release ignores, a settings warning, and a `signed/*`
   tag passed over or not in the checkout.
6. The four sentences for an evidence file Purlin ignores are one kind.
7. The docs' two screenshots do not change: no sample holds three warnings of a kind.
   `dev/capture_doc_screenshots.py` was not run.

## What is left

A pattern in the page follows a sentence in `scripts/mcp/purlin/specs.py`, `wording.py`,
`evidence.py`, `status.py` and `payload.py`. PROOF-262's test builds its warnings from those
modules' own sentences, so a reworded sentence fails that test. The one sentence the test
writes out itself is the unnumbered-rule line, which `payload.py` holds inline.

## What the page looked like

Looked at with playwright, 900 pixels high, both themes, over the test's sample (the regulated
sample with 34 warnings, 2 notices) and over the copy of the real data (4 notices). The two
themes measure the same. At every width in both themes the page scrolls sideways 0 pixels.
Pixels from the top of the page:

| Width | Sample: boxes start | Sample: first spec row | Real data: boxes start | Real data: first spec row |
|---|---|---|---|---|
| 1500 | 258 | 807 to 862 | 447 | 996 to 1051 |
| 1280 | 258 | 807 to 862 | 447 | 996 to 1051 |
| 1024 | 322 | 871 to 927 | 511 | 1060 to 1116 |
| 768 | 375 | 911 to 995 | 604 | 1141 to 1224 |
| 390 | 612 | 1337 to 1481 | 917 | 1484 to 1568 |

With the 34 warnings of the sample the first row of the `Anchors` table (516 to 571) and the
first spec row are both within the first screen at 1500 by 900. At 390 the boxes start 612
pixels down and the first anchor row 947. On the real data at 1500 by 900 the first anchor row
(705 to 760) is on the first screen and the first spec row is not: its four notices, two count
boxes and the `Anchors` table stand above it.

## Acceptance

`python3 -m pytest dev/test_purlin_report.py dev/test_purlin_report_board_layout.py dev/test_report_refresh.py dev/test_purlin_docs.py`: 102 passed.
`bash dev/run_tests.sh`: 1071 passed, 9 skipped; `Suites: 4 passed, 0 failed`.
