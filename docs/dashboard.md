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
  It is green at the signed commit and amber once commits have followed it. `not signed` is
  plain, in no state colour.

Where the two boxes do not fit beside the header line, both move to the line below the logo.

**The theme button** is always at the top right. It shows the glyph of the theme it turns to:
`◐` in the dark theme, `◑` in the light. Its hover names that theme, `Light theme` or
`Dark theme`.

## Board

![The board: the header line naming the branch and commit, the Tests and Sign-off boxes, the count boxes, the Anchors section, and the specs under their categories](images/dashboard-board.png)

**Notices.** Notices sit above the count boxes, one per line. There is one when the working tree
has uncommitted changes:

```
The working tree has uncommitted changes, so what is on this board is not what a commit would carry.
```

The notices then hold every line the status prints between its table and its summary sentence,
but `→ Run: purlin:init --update`.
The warnings come first, such as a spec mistake or an anchor whose pin is behind its source.
Below them come the lines of information, such as a spec ahead of its code:

```
states: 3 files its scope names are not written yet: facts.py, project.py, wording.py. Run purlin:build states, or correct the path with purlin:spec states.
```

Each line reads as the terminal prints it. Two are set on one line here: an anchor's pin line
stands without the `Anchors:` heading, and the uncommitted spec files follow their heading, as
`Uncommitted spec changes: M specs/auth/login.md, ?? specs/auth/logout.md`.

Three or more warnings of one kind about a spec are one notice. It counts the specs and names the
first two, and its hover names every one:

```
33 specs hold a proof line Purlin cannot read: piano_roll, sample_voice, and 31 more. Run purlin:status for each.
```

One or two of a kind keep a notice each, and so does a warning that is about no one spec. The
lines of information group the same way.

**Count boxes.** Up to four boxes count the project's rules:

- `No proof` counts the rules no proof line names. It comes first, and it is there wherever the
  project writes at least one proof line.
- `Passing` counts the rules that pass their tests. The project's total is beneath it, as
  `11 RULES TOTAL`. A rule checked at sign-off is not counted.
- `Failing` counts the rules whose tests failed, in red. It is there only while a rule's status
  is `failed`. Hover over it for each spec that holds one, as `invoice · 1`. A rule that failed
  on one operating system and passed on another reads `partial` and is not counted here.
- `Strong` counts the rules the audit found strong, of the rules that pass their tests and have
  a tested proof. It is there once any rule has an audit entry and at least one rule that is not
  an anchor's passes its tests with a tested proof. Hover over it for the audit's counts, one to
  a line, as `34 strong`, `4 weak`, `2 spot-checked`, then `Last audit: 2026-09-13`.

A box is green once its count is complete, and amber until then. `No proof` is complete at zero.
`Passing` is complete once every rule passes or is checked at sign-off. `Strong` is complete once
every rule the audit could read that is not an anchor's is strong.

**Columns.** `Spec`, `Rules` and `Tests` are always there. `Proofs` sits between `Rules` and
`Tests` wherever the project writes at least one proof line. `Strong` comes last once any rule has
an audit entry. A column the project does not reach is absent, not empty.

| Column | What it reads | What its hover says |
|---|---|---|
| `Spec` | the feature's name, or an anchor's | the spec's path |
| `Rules` | how many rules the spec has, as `16` | |
| `Proofs` | `5 · 1 no test`: how many proof lines the spec holds, then how many no test runs. A `@manual` proof is not counted as one | which proofs have no test |
| `Tests` | `3 of 4 · 1 partial`: how many rules passed everywhere they ran, then `by hand`, `partial` and `failing`. `2 of 3 · 1 by hand` holds one rule checked at sign-off | one line per operating system a current run covered, with its newest run's source, age and results |
| `Strong` | `2 of 4`, as `<strong> of <n>`: how many rules the audit found strong, of the rules that pass their tests and have a tested proof. An anchor reads one word, `weak`, `out of date` or `spot-checked`, or nothing | where the newest audit came from and how old it is; an anchor's opens on `No bug is planted for an anchor's rule.` |

Every count names what it counts. The first part is always drawn. A later part is drawn only
above zero, so a spec with nothing partial and nothing failing reads `3 of 3`. Each cell reads
the same characters as the status table in the terminal.

Every hover is a plain `title` attribute, so it works on a page opened from disk. When, who and
which platform are all in hovers.

**Anchors.** The anchors have a section of their own, headed `ANCHORS`, between the count boxes
and the spec table. It has the same columns and rows, and no band. A project with no anchor shows
no such section.

**Failing specs first.** A spec with a failing rule is listed before a spec with none, among the
anchors and within each category, and a category that holds one comes before a category that
holds none. Where a spec fails and no anchor does, the spec table stands above the anchors. So the
`Failing` box and the first failing spec are on the first screen. Nothing else moves: specs are
listed by name. The status table in the terminal has its own order, the spec with the most rules
left to do first.

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
is there once any rule of the project has an audit entry. `Spec` is the spec's
path. `Last run` is the newest run's source and age.

**The `Passed` and `Strong` rows.** Each carries the cell's word as a badge, then its reasons:
`failing: Linux/Unix, local`, `Windows: no run yet` or `code changed since 9f8e7d6`.

The `Strong` row reads `STRONG`, `WEAK`, `SPOT-CHECKED`, `OUT OF DATE` or `CHECKED AT SIGN-OFF`:

- `SPOT-CHECKED`: the spot tests found nothing and no bug was planted and caught. The reason
  says why, as `The spot tests found nothing. No bug was planted: no bug is planted for an anchor's rule.`
- `OUT OF DATE`: the rule, its proof, its test or its code changed since the audit read it. The
  reasons name what changed and the last result: `code changed since a1b2c3d`, then
  `the last audit found it strong on 2026-09-13`.

The `Passed` row adds one box per operating system a counting run covered: `Lin`, `Mac` or
`Win`. A box is green where the rule passed and red where it failed. Its hover gives the system,
the result, the source and the age.

Four cases to know:

- **A rule checked by hand alone.** The row reads `CHECKED AT SIGN-OFF` with
  `no sign-off has checked it yet`. Once a sign-off notes it, it reads `PASSED` with the note.
  After a rewording it reads `CHECKED AT SIGN-OFF` again, with
  `the rule's wording changed since its last note` or
  `the proof's wording changed since its last note`.
- **A slow proof not yet run.** The row reads `not run` with `slow: runs with purlin:test --all`,
  and the proof carries the tag `@slow`.
- **An anchor's rule with nothing to check.** The row reads `passed` with the reason the test
  gave, as `PROOF-3: this project has no screens`. You see the rule was not exercised.
- **A spec to repair.** Every rule of it reads `failed` with the reason, such as
  `PROOF-2 is written twice in the spec`, whatever its tests found.

**The Audit panel.** It is there once any rule has an audit entry. It reads, in this order:

1. `Strong. It found nothing.`, or `Weak.` and each finding in the sentence the audit wrote, or
   `Spot-checked.`, then `The spot tests found nothing.` and why no bug was caught. An entry out
   of date opens the panel with `Out of date:` and the row's reasons. A bug that survived is
   followed by the case the AI says it breaks, as `PROOF-2: the AI says this breaks: <case>`.
2. The model's explanation, each sentence on its own line. A strong rule has one too.
3. Each planted bug the rule's tests missed, as
   `PROOF-2: its tests missed a bug planted at src/billing/invoice.py:12.` The lines before the
   bug are under `Before`, and the lines after it under `After`. A bug the tests caught is not
   shown.
4. `Read by`, the model and the time, in your timezone like the header line.

A rule no audit has read says `No audit has read this rule yet.` In a
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
amber, red and teal are darkened to reach that. The dark theme meets the same 7 to 1,
but its red and copper text, which measure at least 4.5 to 1: a red that reaches 7 to 1 on the
dark ground no longer reads as red.

## Next

- [running-and-evidence.md](running-and-evidence.md): what writes the data this page shows.
- [sign-off.md](sign-off.md): the sign-off the `Sign-off` box names.
- [working-together.md](working-together.md#more-than-one-checkout): one page per checkout.
