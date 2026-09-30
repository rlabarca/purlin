# The dashboard

For anyone who wants to see where every rule stands without reading a spec file.

The dashboard is one HTML file with no server, no build step and no dependencies. It opens from
disk beside your editor. Anyone without a checkout reads `.purlin/tests.md` on the git host,
the table `purlin:test --commit` commits.

## Opening it

`purlin:init` copies the page to `purlin-report.html` at the project root. The page is
gitignored, so each person has their own copy. Running `purlin:init` again keeps it and prints
`kept purlin-report.html`. After a plugin update, `purlin:init --update` offers to replace a copy
that is not the page the plugin ships.

Open it in any browser. It reads `.purlin/report-data.js`, which `purlin:status`,
`purlin:test`, `purlin:audit` and `purlin:sign` each write as they finish. Nothing writes it in
the background, so an edit you make with no Purlin command shows up after the next of those
four. With no data file the page says `No board data yet. Run purlin:status to write
.purlin/report-data.js, then reload this page.`

When you come back to the tab and the data is more than 60 seconds old, the page reloads itself
and keeps the screen and the open rule, so a sign-off you have just written appears without
you reloading anything.

The page has two screens: the board, and one rule.

## The top bar

Every screen carries the same top bar:

- the logo;
- how old the data is, as `Data: 12 minutes old`, a button that reloads the page. Its hover
  reads `To refresh it, type purlin:status in Claude Code. Press here to reload the page.`,
  after `This data is old. ` once the data is 90 minutes old. The age recomputes every 60
  seconds;
- the gate, `gate: signed`;
- at the gate `signed` only, the signed tag this commit carries, as `signed/1.4.0`, with the
  commit in its hover, or `no signed tag`, whose hover reads `This commit carries no signed tag.
  The first purlin:sign after purlin:test --release writes signed/<version>, and a person pushes
  it.`;
- the theme button, which shows the glyph of the theme it turns to, `◐` in the dark theme and
  `◑` in the light, its hover naming that theme, `Light theme` or `Dark theme`.

Below it are the tabs: `Board`, then the open rule, such as `login RULE-1`, when there is one.

## Board

![The board at the gate signed: the notice that the working tree has uncommitted changes and one spec warning, the No proof, Passing and Strong boxes, the four buttons To fix, To write a test for, To test and To strengthen, the anchors checkout_design and security_baseline in the Anchors section, and the specs under their categories, both tables with all five columns; login is open under its description, and RULE-4 is unfolded beneath its row, PROOF-4 failed on Windows and PROOF-5 passed](images/dashboard-board.png)

A notice sits above the boxes, one per line, when the working tree has uncommitted changes, `The
working tree has uncommitted changes, so what is on this board is not what a commit would
carry.`, and for each warning the status prints, such as a spec mistake. The board then opens
on the boxes.

**Boxes.** `Passing`, at every gate, counts the rules whose tests pass, a hand check included.
`Strong` counts the rules the AI audit found strong; it is there at either gate once the audit
has found any rule strong or weak, and absent before. At the gate `signed` a `No proof` box
comes first, counting the rules no proof line names. A box is green once it counts every rule
and amber until then. Under `Passing` a second line gives the project's total,
`11 RULES TOTAL`. The boxes carry their column's hover, read over every spec; the `No proof` box
names each spec with how many of its rules have no proof. Nothing on the board is signed rule by
rule: a sign-off covers a release's evidence package, and the top bar names the tag it writes.

**Filter buttons.** One button per line of `Left to do`, in the same order, named as the line
without its count and noun and carrying the count: `3 rules to strengthen` is `To strengthen 3`,
`1 test comment to correct` is `To correct`, and `1 spec to repair` is `To repair`, which shows
the rules of each spec that writes a number twice or holds a line left from a merge conflict.
One button is chosen at a time. Choosing one shows only the rules left to do of that kind, and
the line under the buttons names the command that clears them, such as `Type purlin:test in
Claude Code.`; choosing it again shows every rule. `To correct` counts no rule, so choosing it
leaves every rule showing. With nothing left to do, the buttons give way to the summary's last
line, such as `Nothing left to do. To release a version: purlin:test --release`. A board with
no rule to show reads `No rule is left of this kind.`

**Columns.** `Spec`, `Rules` and `Tests` are there at every gate. `Proofs` sits between `Rules`
and `Tests` at `signed`, and at `passed` only where the project writes at least one proof line,
since proofs are optional there. `Strong` comes last, at either gate, once the audit has found
any rule strong or weak. A column the project does not reach is absent, not empty.

| Column | What it reads | What its hover says |
|---|---|---|
| `Spec` | the feature name, under the band that names its category; an anchor's name, in the `Anchors` section | the spec's path |
| `Rules` | how many rules the spec has, as `16` | — |
| `Proofs` | `5 · 1 no test`: how many proof lines the spec holds and how many no test runs. A `@manual` proof counts as no gap | which proofs have no test |
| `Tests` | `3 of 4 · 1 partial`: how many rules passed everywhere they ran, then `partial` and `failing` | one line per operating system a current run covered, newest first, as `Windows · ci · 18 days old · 3 passed · 1 failed` |
| `Strong` | `2 of 4 · 86%`: how many rules the audit found strong, then the test strength where one was measured; `0 of 26` alone where none was, and always for an anchor | where the newest audit came from and how old it is; the percentage's own hover reads `Test strength: the tests caught 86 of every 100 deliberate breaks of the code.` |

Every count names the word it counts. The first part is always drawn; a later part is drawn
only above zero, so a spec with nothing partial and nothing failing reads `3 of 3`. Every
when, who and platform detail is in a hover, a plain `title` attribute, so it works on a page
opened from disk. A value never breaks inside itself: `2 of 4 · 1 partial · 1 failing` and
`5 · 1 no test` stay on one line. Every column fits a 1024-pixel window. Under 1024 pixels neither table has
a heading row: each spec is a block, its name first and its values beneath as labelled pairs
that wrap whole, `Rules 16`, `Tests 3 of 4`, and a rule in an open spec reads its id and
badges, then its words, then its proofs control. The boxes wrap three to a row, and two to a row
under 600 pixels; the filter buttons and the top bar's chips wrap whole. The page never scrolls
sideways and its text keeps its size, on the board and on a rule's screen.

A spec with no `> Scope:` line names no files, so Purlin cannot tell which code it covers. Its
row reads `<name> · no scope`, and the hover gives the reason. A `purlin:test` with no feature
named always runs such a spec.

**Anchors.** The anchors stand in a section of their own, headed `ANCHORS`, between the filter
buttons and the spec table, in the same columns and rows, with no band. A chosen filter applies
to both tables. A project with no anchor, or a filter that leaves no anchor's rule, shows no
such section. An anchor's rules cover the whole project, and no code is broken on purpose for an
anchor, so its `Strong` cell shows no test strength.

**Bands and rows.** The other specs are grouped by category. The band above each group has two ends: the
category's name and `2 specs` at the left, `4 of 5 rules pass` and a bar at the right, every bar
one width so they line up down the page. A band counts the rules of the specs it holds; under
1024 pixels its count sits beneath its name. Pressing a band, or Enter or Space on it, folds it.
Pressing a spec opens it: its `> Description:` first, then its rules.

Each rule row carries the rule id, the rule text, a badge for each box that counts it, `PASSED`
and `STRONG`, and `FAILED` where a test of the rule failed on any operating system. A box that
does not count the rule draws nothing: why is on the rule's screen.

**Proofs under a rule.** The last control on a rule's row reads `▶ 2 proofs` while closed, in
the warn tone when one of the proofs reads `failed` or `no test`, and `no proof` where the rule
has none. Pressing it opens the rule's proofs beneath the row and turns the glyph to `▼`; a
screen reader hears whether it is open. Each proof reads its id, its words in full, its own
result (`passed`, `failed`, `no test`, `not run` or `hand check`), its `@manual` and `@env`
tags, and each of its tests as `tests/test_login.py :: test_no_cookie` behind a dot in the
colour of that test's result, with the result's word in the dot's hover. A rule with no proof
shows the tests marked with its own id the same way. Every rule's proofs are closed when the
page loads and when you open a spec, and opening one rule's leaves the others as they were. A
filter that hides a rule hides its proofs with it. A project at `passed` that writes no proof
line is told nothing about proofs: the control reads `1 test` and opens the rule's tests, and is
absent where the rule has none.

## Rule

Pressing a rule opens it. A rule is named by the spec that owns it and its id together, so
`ai_audit RULE-1` and `security_no_dangerous_patterns RULE-1` open two different screens, and
the tab names the owner.

![The screen for login RULE-1 at the gate signed: the Passed and Strong rows, the passed row with its Lin and Win boxes, the Spec and Last run rows, then the Audit panel, and PROOF-1 with its test](images/dashboard-rule.png)

`Back to the board` at the top closes the rule. The screen opens with the feature, the rule id
and the rule's text, then one panel of facts: the `Passed` row, the `Strong` row once the audit
has found any rule of the project strong or weak, then `Spec` and `Last run`.

Each cell row carries the cell's word as a badge and its reasons, such as `failing: Linux/Unix,
local`, `Windows: no run yet`, `code changed since 9f8e7d6`, `strength 64%` or `manual proof`.
The passed row adds one box per operating system a current run covered, `Lin`, `Mac` or `Win`,
green where the rule passed and red where it failed, with the system, the word, the source and
the age in its hover. The strong row reads `waiting`, in the neutral colour, with the reason
`waiting for its tests to pass`, while the rule's tests do not pass. Every rule of a spec to
repair reads `failed` in its passed row with the reason, such as `PROOF-2 is written twice in
the spec`, whatever its tests found.

Once the audit has found any rule strong or weak, at either gate, the **Audit** panel follows,
one line each: `Strong. It found nothing.`; or `Strong.`, `Weak.` or `Undecided. The AI audit
could not decide, so the rule reads weak until its proof or test changes.`, followed by each
finding; then, only where one was measured, `Test strength 86%.`; then `Read by <model> on
<date> <time> UTC` and the path of the evidence file. A rule no audit has read says `No audit has
read this rule's text, proof and test yet.` The panel reports and recommends nothing, and
nothing waits on it.

The **Proofs** are last, each drawn exactly as the board draws it under the rule: its words, its
result, its `@manual` and `@env` tags, and its tests with their results. A proof with no test
reads `No test yet. Type purlin:build login in Claude Code.` A `@manual` proof reads, at the
gate `signed`, `Checked by hand when a release is signed, in the walk of purlin:sign.`, and at
`passed`, `Checked by hand. A release at the gate passed lists it as not checked.` A project at
`passed` that writes no proof line has no proofs here, and the screen lists the tests marked with
the rule's own id.

Where the project's remote is on GitHub, the spec and the evidence file are links to that file
on the git host, at the commit the data was built from.

## Both themes

The page opens dark until you choose. The theme button, `◐` or `◑`, switches between dark and
light, and the page opens in the theme you chose the next time it loads. Every colour on the page
is a token the theme redefines, and the logo swaps to the colourway that reads on the new ground.

## Next

- [running-and-evidence.md](running-and-evidence.md): what writes the data this page shows.
- [review-and-signing.md](review-and-signing.md): releasing a version and signing it off.
