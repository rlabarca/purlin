# The dashboard

The dashboard shows where every rule stands, so you do not have to read a spec file.

It is one HTML file. It needs no server, no build step and no network. Open it from disk beside
your editor.

## Opening it

Open `purlin-report.html` at the project root in any browser. The page is kept out of git, so
each checkout has its own copy.

The page reads `.purlin/report-data.js`. Four commands write that file as they finish:
`purlin:status`, `purlin:test`, `purlin:audit` and `purlin:sign`. Each also writes the page
itself where the project's copy differs from the plugin's, so the page and its data always come
from the same version of Purlin. A fresh clone gets its page the same way, as long as git ignores
the page. `purlin:init` sets that up.

The data is a snapshot from the last of those four commands. Nothing writes it in the
background. An edit you make with no Purlin command shows up after the next one.

With no data file, or one written for another version of the page, the page shows one notice
naming the command that writes it.

The page has two screens: the board, and one rule.

## The top bar

The top bar holds the logo, the header line, two boxes and the theme button.

**The header line** says which checkout you are reading and when its data was written:

```
main at a1b2c3d, written 06:42 EDT
```

That is the branch, the first 7 characters of the commit the command ran on, and the time. The
time is 24-hour and in your own timezone. The line names the zone by your browser's short name
for it, or by its offset, as `GMT+5:30`, where the browser has none. Hover over the line for the
full date and the UTC time: `2026-10-01 06:42 EDT (10:42 UTC)`. The data keeps the time in UTC
and the page converts it. On a detached `HEAD` the line reads
`detached at a1b2c3d, written 06:42 EDT`.

**The two boxes** state the two facts:

- `Tests` reads `met` where every rule's tests pass on the committed evidence, and `not met`
  otherwise.
- `Sign-off` reads `signed 0.1.0 at a1b2c3d`, `signed 0.1.0, 4 commits since` or `not signed`.

**The theme button** shows the glyph of the theme it turns to: `◐` in the dark theme, `◑` in the
light. Its hover names that theme, `Light theme` or `Dark theme`.

## Board

![The board: the header line naming the branch and commit, the Tests and Sign-off boxes, the count boxes, the Anchors section, and the specs under their categories](images/dashboard-board.png)

**Notices.** Notices sit above the count boxes, one per line. There is one when the working tree
has uncommitted changes:

```
The working tree has uncommitted changes, so what is on this board is not what a commit would carry.
```

There is one for each warning the status prints, such as a spec mistake. Below the warnings, a
spec ahead of its code gets one line of information:

```
states: 3 files its scope names are not written yet: facts.py, project.py, wording.py. Run purlin:build states, or correct the path with purlin:spec states.
```

**Count boxes.** Up to three boxes count the project's rules:

- `No proof` counts the rules no proof line names. It comes first, and it is there wherever the
  project writes at least one proof line.
- `Passing` counts the rules whose tests pass, a hand check included. The project's total is
  beneath it, as `11 RULES TOTAL`.
- `Strong` counts the rules the audit found strong. It is there once the audit has found any
  rule strong or weak.

A box is green once its count is complete, and amber until then. `No proof` is complete at zero.

**Columns.** `Spec`, `Rules` and `Tests` are always there. `Proofs` sits between `Rules` and
`Tests` wherever the project writes at least one proof line. `Strong` comes last once the audit
has found any rule strong or weak. A column the project does not reach is absent, not empty.

| Column | What it reads | What its hover says |
|---|---|---|
| `Spec` | the feature's name, or an anchor's | the spec's path |
| `Rules` | how many rules the spec has, as `16` | |
| `Proofs` | `5 · 1 no test`: how many proof lines the spec holds, then how many no test runs. A `@manual` proof is not counted as one | which proofs have no test |
| `Tests` | `3 of 4 · 1 partial`: how many rules passed everywhere they ran, then `partial` and `failing` | one line per operating system a current run covered, with its newest run's source, age and results |
| `Strong` | `2 of 4`: how many rules the audit found strong | where the newest audit came from and how old it is |

Every count names what it counts. The first part is always drawn. A later part is drawn only
above zero, so a spec with nothing partial and nothing failing reads `3 of 3`. Each cell reads
the same characters as the status table in the terminal.

Every hover is a plain `title` attribute, so it works on a page opened from disk. When, who and
which platform are all in hovers.

**Anchors.** The anchors have a section of their own, headed `ANCHORS`, between the count boxes
and the spec table. It has the same columns and rows, and no band. A project with no anchor shows
no such section.

**Bands and rows.** The other specs are grouped by category. A band heads each group:

```
▼ BILLING 2 specs 4 of 5 rules pass
```

A band counts the rules of the specs it holds. Press a band, or press Enter or Space on it, to
fold it. Press a spec to open it: you see its `> Description:`, then its rules. Press it again
to close it.

Each rule row carries the rule id, the rule text and its badges. `PASSED` and `STRONG` each mark
a rule its box counts. `FAILED` marks a rule with a test that failed on any operating system. A
rule a box does not count gets no badge for it. The rule's screen says why.

## Rule

Press a rule to open its screen. A rule is named by its spec and its id together, so
`ai_audit RULE-1` and `security_no_dangerous_patterns RULE-1` open two different screens.

![The screen for one rule: Back to the board, the rule's text, the Passed and Strong rows with the boxes for each operating system, the Audit panel, and each proof with its tests](images/dashboard-rule.png)

`Back to the board` at the top returns to the board. Below it are the feature, the rule id and
the rule's text. Then come four rows: `Passed`, `Strong`, `Spec` and `Last run`. The `Strong` row
is there once the audit has found any rule of the project strong or weak. `Spec` is the spec's
path. `Last run` is the newest run's source and age.

**The `Passed` and `Strong` rows.** Each carries the cell's word as a badge, then its reasons:
`failing: Linux/Unix, local`, `Windows: no run yet` or `code changed since 9f8e7d6`.

The `Passed` row adds one box per operating system a counting run covered: `Lin`, `Mac` or
`Win`. A box is green where the rule passed and red where it failed. Its hover gives the system,
the result, the source and the age.

Three cases to know:

- **A slow proof not yet run.** The row reads `not run` with `slow: runs with purlin:test --all`,
  and the proof carries the tag `@slow`.
- **An anchor's rule with nothing to check.** The row reads `passed` with the reason the test
  gave, as `PROOF-3: this project has no screens`. You see the rule was not exercised.
- **A spec to repair.** Every rule of it reads `failed` with the reason, such as
  `PROOF-2 is written twice in the spec`, whatever its tests found.

**The Audit panel.** It is there once the audit has found any rule strong or weak. It reads, in
this order:

1. `Strong. It found nothing.`, or `Weak.` and each finding in the sentence the audit wrote.
2. The model's explanation, each sentence on its own line. A strong rule has one too.
3. Each planted bug the rule's tests missed, as
   `PROOF-2: its tests missed a bug planted at src/billing/invoice.py:12.` The lines before the
   bug are under `Before`, and the lines after it under `After`. A bug the tests caught is not
   shown.
4. `Read by`, the model and the time, in your timezone like the header line.

A rule no audit has read says `No audit has read this rule's text, proof and test yet.` In a
project no audit has read, the page says nothing of the audit at all.

**The proofs.** They come last. Each shows:

- its id and its words in full;
- its own result: `passed`, `failed`, `no test`, `not run` or `checked at sign-off`;
- its tags, `@manual`, `@slow` and `@env(windows)`, where it carries them;
- each of its tests, as `tests/test_login.py :: test_no_cookie`, behind a dot in the colour of
  that test's result. The dot's hover gives the result's word.

A rule with no proof shows the tests marked with its own id the same way.

A hand check, a `@manual` proof, reads `checked at sign-off`. Beneath it is the note of the
newest sign-off that holds one:

```
noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, 4 commits since: the tube is red
```

## Any screen, both themes

The page reads on every screen from 390 to 1500 pixels wide. It never scrolls sideways. No
count, label, box or rule id breaks onto two lines.

The page opens dark until you choose. The theme button switches between dark and light, and the
page opens in the theme you chose the next time it loads. The logo changes with the theme.

The light theme is ink on paper: a paper tan ground, cards one step lighter, and navy text.
Every text on it, in any colour, measures at least 7 to 1 against the ground under it. Green,
amber, red and teal are darkened to reach that. In the dark theme every neutral text measures at
least 7 to 1.

## Next

- [running-and-evidence.md](running-and-evidence.md): what writes the data this page shows.
- [sign-off.md](sign-off.md): the sign-off the `Sign-off` box names.
- [working-together.md](working-together.md#more-than-one-checkout): one page per checkout.
