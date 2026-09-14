# Feature: purlin_report

> Description: The board: one HTML file that shows where every rule stands.
>   It opens from disk and as a build artifact, reads `.purlin/report-data.js`
>   beside it, and carries three screens: the board, one rule, and the review
>   list CI prepared. It is assembled from the parts under `scripts/report/src/`
>   by `dev/build_report.py`, which inlines the design tokens so every colour on
>   the page resolves to one block and both themes ship in the same file. The
>   screenshots the docs embed are captured from the same fixture payloads the
>   tests render.
> Scope: scripts/report/src/page.html, scripts/report/src/styles.css, scripts/report/src/theme.js, scripts/report/src/filters.js, scripts/report/src/board.js, scripts/report/src/rule.js, scripts/report/src/review.js, scripts/report/src/app.js, scripts/report/purlin-report.html, dev/build_report.py, dev/capture_doc_screenshots.py
> Stack: html/css/javascript, no framework and no build-time dependency, design tokens inlined by a python assembler

## Rules

- RULE-1: The build is a pure function of its parts: two runs over unchanged sources write the same bytes [risk: low] [origin: eng]
- RULE-2: The build writes one file of at most 1000 lines and copies it to the project root, where the data file and the design files a spec names resolve beside it [risk: low] [origin: eng]
- RULE-3: Every colour the page uses is written inside the one inlined token block, and no colour literal appears anywhere else in the file [risk: medium] [origin: eng]
- RULE-4: The page carries no shadow, no gradient and no emoji [risk: medium] [origin: eng]
- RULE-5: The page asks nothing of anything outside itself: no stylesheet link, no style import, no fetch, and no source or link address on another host [risk: high] [origin: eng]
- RULE-6: Affordances are unicode glyphs and the page draws no icon set [risk: low] [origin: eng]
- RULE-7: The board heading states the rule count and the spec count the payload rolled up, the top bar states the gate and how old the data is, and every spec in the payload has a row [risk: medium] [origin: eng]
- RULE-8: The strip above the table carries one tile per state in the order Drafted, Proof ready, Tested, Recorded, Reviewed, Approved, Stale, each showing that state's count from the payload, each label set in capitals [risk: medium] [origin: eng]
- RULE-9: A column appears only where the artifact it reports exists: risk and the risk-by-state grid where a rule is tagged above low, test strength, latest record and re-verify where a record exists, approvals where an approval exists. A project that has never recorded shows none of them [risk: medium] [origin: eng]
- RULE-10: A spec row opens to the rules it owns and closes again on the next click [risk: low] [origin: eng]
- RULE-11: A row whose spec pins a single image file shows that image as a thumbnail beside the name [risk: low] [origin: eng]
- RULE-12: Both themes ship in the page. It opens dark on the product surface, the toggle swaps the ground, the ink and the mark to the other theme, and swaps back [risk: medium] [origin: eng]
- RULE-13: The board offers five filters, and each narrows the table to the rules it accepts: high risk not approved, stale, no negative case, low test strength, open items [risk: medium] [origin: eng]
- RULE-14: Filters compose: a rule shows only where every set filter accepts it, a combination nothing matches says so in place of the table, and unsetting them restores every row [risk: medium] [origin: eng]
- RULE-15: The rule screen states the rule text, each proof with its tier, the test file and test name that carry the proof marker, the state, the test strength and why the rule is or is not on the review list [risk: high] [origin: eng]
- RULE-16: Where the payload names a git host the page can address, the spec file, the record and each approval file are links to that host at the payload's commit; where it names no remote the same paths stay plain text and nothing on the screen is a link [risk: medium] [origin: eng]
- RULE-17: A rule whose proof names an operating system that no counting record came from says so on its screen, naming that system, rather than reading as proved [risk: high] [origin: eng]
- RULE-18: The review list names how many rules need a look, groups them high risk first, states the reason beside each, and opens the rule screen from any of them [risk: high] [origin: eng]
- RULE-19: An empty review list says what puts a rule on it instead of showing nothing [risk: low] [origin: eng]
- RULE-20: A payload written for another schema version shows one notice naming the command that rewrites it, and no tiles, no table and no tabs, rather than rendering fields it cannot read [risk: high] [origin: eng]
- RULE-21: With no data file at all the page names the command that writes one [risk: low] [origin: eng]
- RULE-22: The notice that the working tree has uncommitted changes belongs to the board and appears on no other screen [risk: medium] [origin: eng]
- RULE-23: The screenshots the docs embed are captured from the fixture payloads the tests render, not from whatever the checkout holds, and land in `docs/images/` [risk: low] [origin: eng]

## Proof

- PROOF-1 (RULE-1): Run the build twice over unchanged sources and verify the two pages are the same string, byte for byte, so 0 bytes differ between the two runs @unit
- PROOF-2 (RULE-2): Run the build; verify the written page has at most 1000 lines and that the copy at the project root is the same text as the one under `scripts/report/` @unit
- PROOF-3 (RULE-3): Run the build, cut the page at the inlined token block, and verify the block declares `--canvas` and that the text outside it contains zero hex colour literals @unit
- PROOF-4 (RULE-4): Run the build and verify the page outside the token block contains no `box-shadow`, that the whole page contains no `gradient`, and that no character of it falls in the emoji ranges @unit
- PROOF-5 (RULE-5): Run the build and verify the page contains no `<link` element, no `@import`, no `fetch(`, and no `src` or `href` beginning `https:` or `http:` @unit
- PROOF-6 (RULE-6): Run the build and verify the page contains the glyphs `▶`, `▼` and `←`, that it holds zero `<svg` elements, and that the word `icon` appears nowhere in it at any casing @unit
- PROOF-7 (RULE-7): Open the board over `file://` with the solo, team and regulated fixture beside it in turn; verify the heading states that payload's rule count and spec count, that the top bar reads `gate: ` with that payload's gate and a `Data:` age, that 7 state tiles are on screen, and that the spec names listed are exactly the payload's @e2e
- PROOF-8 (RULE-8): Open the board with the regulated fixture; verify the tile labels read `Drafted`, `Proof ready`, `Tested`, `Recorded`, `Reviewed`, `Approved`, `Stale` in that order, that the labels are set in capitals, and that the Approved and Stale tiles show the counts the payload's state totals hold @e2e
- PROOF-9 (RULE-9): Open the board with the solo fixture, which has never recorded, and verify the heading row offers no latest record, no approvals and no risk, and that no risk-by-state grid is on screen; open it with the team fixture and verify latest record, strength, re-verify and risk are offered, approvals are not, and exactly 1 grid is on screen; open it with the regulated fixture and verify approvals are offered @e2e
- PROOF-10 (RULE-10): Open the board with the regulated fixture; verify no rule id is on screen, click the login row and verify the ids read `RULE-1`, `RULE-2`, `RULE-3`, `RULE-4` and that one of them reads `APPROVED`, then click it again and verify no rule id remains @e2e
- PROOF-11 (RULE-11): Open the board with the regulated fixture, whose checkout spec pins one image; verify exactly 1 thumbnail is on screen, that it points at `designs/checkout/cart.png`, and that the image loaded, its natural width being 1 pixel @e2e
- PROOF-12 (RULE-12): Open the board and verify it starts on the dark theme and the product surface; read the ground and the ink, click the theme button, and verify the theme reads light, that both the ground and the ink differ from the dark ones, that the mark address changed, and that 7 tiles are still on screen; click it again and verify the theme reads dark @e2e
- PROOF-13 (RULE-13): Open the board with the regulated fixture and set each filter in turn; verify `high-open` leaves login alone showing `RULE-4`, `stale` leaves login showing `RULE-2`, `no-negative` leaves login and invoice with login showing `RULE-3`, `low-strength` leaves invoice alone, `open` leaves login and invoice with login showing all 4 rules, and that the filter set reads as pressed each time @e2e
- PROOF-14 (RULE-14): Open the board with the regulated fixture, set `stale` and `low-strength` together, and verify no spec row remains and the page reads `No rule matches every filter you set.`; unset both and verify 3 spec rows come back @e2e
- PROOF-15 (RULE-15): Open the board with the regulated fixture, open the login row and then `RULE-1`; verify the heading names `RULE-1`, that the screen carries the rule text `A person signs in with an email address and a password.`, the proof id `PROOF-1`, the test `tests/test_login.py :: test_sign_in`, the state `APPROVED`, the test strength `86%`, and that it does not read `Not on the review list.` @e2e
- PROOF-16 (RULE-16): Open the regulated fixture, whose payload names a git host, and open `RULE-1`; verify the spec path is a link whose address begins `https://github.com/acme/ledger/blob/` and that the approval file `RULE-1.1a2b3c4d.jane-doe.json` is a link too. Open the solo fixture, which names no remote, and open `RULE-1`; verify the screen holds zero links and still shows the text `specs/auth/login.md` @e2e
- PROOF-17 (RULE-17): Open the regulated fixture and open `RULE-4`, whose proof is scoped to one operating system with no record from it; verify the screen reads `windows: no record yet` and does not read `no negative case` @e2e
- PROOF-18 (RULE-18): Open the regulated fixture; verify the tab reads `Review list (4)`, open it and verify the heading reads `4 rules need a look`, that the groups read `high risk`, `medium risk`, `low risk` in that order, that 4 rows are listed, that the third states `the approval is stale`, and that clicking the first opens a screen whose heading names `RULE-1` @e2e
- PROOF-19 (RULE-19): Open the solo fixture, which has nothing to review, open the review list, and verify it reads `Nothing needs a look` @e2e
- PROOF-20 (RULE-20): Open the board with the team fixture rewritten to schema 3; verify exactly 1 notice is on screen, that it names `purlin:status`, and that no tile and no table are rendered @e2e
- PROOF-21 (RULE-21): Open the page with no data file beside it at all; verify the empty state names `purlin:status` @e2e
- PROOF-22 (RULE-22): Open the regulated fixture, whose payload reports an uncommitted working tree; verify 2 notices are on the board, then open the review list and verify zero notices are on screen @e2e
- PROOF-23 (RULE-23): Read the capture table; verify it lists 5 images, that each names a payload that exists under `dev/fixtures/report/` rather than the checkout's own data file, that the images are written to `docs/images/`, and that each of the 5 files exists there and is not empty @unit
