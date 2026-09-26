# The dashboard

For anyone who wants to see where every rule stands without reading a spec file.

The dashboard is one HTML file with no server, no build step and no dependencies. It opens from
disk beside your editor, and CI publishes the same page as a build artifact so a PM, a designer
or a QA reviewer can open it from a pull request with no checkout at all.

## The two ways to open it

**Locally.** `purlin:init` copies the page to `purlin-report.html` at the project root. It is a
copy rather than a link, because the only path a plugin install can be linked at is
version-pinned and the link would break on the first plugin update. The copy does not refresh
itself; run `purlin:init --update` after a plugin update. The page is gitignored, so each
person gets their own.

Open it in any browser. It reads `.purlin/report-data.js`, which the plugin rewrites in the
background after a tool call or a turn changed a spec, a proof file, a record or the config.
That file is generated and never committed. The page reloads itself when you come back to the
tab and what it is showing is more than 60 seconds old, keeping the screen and the open rule,
so a signature you have just written appears without you reloading anything. A commit you make
by hand outside Claude Code shows up after the next `purlin:status`.

**From CI.** A CI run copies the page and its data into a build artifact named
`purlin-dashboard-<runner>`, one per job in the matrix, so a run on two operating systems
leaves two pages rather than one. Anyone with repository access downloads one from the run and
opens the page. Nothing is provisioned, nothing is hosted, and no site has to be published.

## The chrome

Every screen carries the same top bar: the logo, how old the data is, the gate in force, the
commit the data was built from, and the theme toggle. How old the data is is a button: press it
to reload the page. The age recomputes itself every 60 seconds from the stamp the data already
carries, so a tab left open does not read `less than a minute old` an hour later. Below it are
the tabs: Board, Review list with its count where the gate has one, and the open rule last when
there is one.

## Board

The Board is where every rule stands. Its headline is two lines:

```
3 of 5 rules pass their tests · 0 failing · 0 partial · 2 untested
3 of 5 meet the gate passed
```

The first line is what the board is mainly about: whether the rules pass their tests. The
second names the gate. A rule meets the gate when every cell up to the gate's level is met. The
gate decides how many cells a rule has, so it also decides how much of this page exists.

![The Board at the passed gate: the Untested, Failing, Partial and Passing tiles, and two specs with their rules, proofs and tests](images/dashboard-solo.png)

At the `passed` gate a rule has two cells, its spec status and its passed cell, so the board
carries four tiles and four columns. The tiles are `Untested`, `Failing`, `Partial` and
`Passing`. The last of them counts levels rather than buckets: a rule that is signed is still
passing, so it is counted in `Passing`, in `Strong` and in `Signed` alike. The three below it
count their own bucket alone. The columns are `Spec`, `Rules`, `Proofs` and `Tests`.

| Column | What it reads | What its hover says |
|---|---|---|
| `Spec` | the feature name, under the band that names its category | the spec's path |
| `Rules` | how many rules the spec holds | — |
| `Proofs` | `24 · 3 without a test`, how many proof lines the spec holds and how many of them no tagged test runs, the second count in the warn tone | which proofs those are |
| `Tests` | `21 of 24 · 1 partial · 2 failing`, how many rules passed everywhere they ran, then the two words that say they did not | one line per operating system a counting run covered, newest first: `linux · ci · 9 days old · 22 passed · 1 failed · 1 not run` |

Every count names the word it counts beside the number. The first part is always drawn, so a
spec with nothing passing reads `0 of 24`; a later part is drawn only where it is above zero,
so a spec with nothing partial and nothing failing reads `24 of 24` and stops there.

A rule reads `partial` when its tests passed on one operating system and failed or did not run
on another. It is not passing and it is not failing, so it has a tile, a filter and a word of
its own rather than hiding inside either.

![The Board at the strong gate: a Strong tile beside the first four, and the Strong column](images/dashboard-team.png)

At `strong` each rule gains a strong cell, so a `Strong` tile joins the four and one column
joins the four: `Strong`, reading `18 of 24 · 71%`, how many rules the audit proved strong and
the test strength of the newest record. Its hover names where that record came from, how old it
is, and the minimum strength this gate asks for. Your own `purlin:audit` counts at this gate;
only at `signed` is CI's the one that counts.

![The Board at the signed gate: a Signed tile and a Stale flag card, and the Signed column](images/dashboard-regulated.png)

At `signed` each rule gains a signed cell. A `Signed` tile joins the five, a `Stale` flag card
sits beside the tiles, and a `Signed` column joins the five, reading `1 of 4`. Its hover names
each signer with the date of their newest signature and then how many signatures stopped
matching. The flag card is counted beside the tiles and never instead of them: a stale rule is
still in whichever tile its cells put it. Warnings sit above the headline, one per line: an
uncommitted working tree, or a spec line the parser could not read as a rule.

**Every when, who and platform detail is in a hover.** A hover is a `title` attribute, one item
to a line, so it works on a page opened from disk with no script behind it. That is what let the
board drop from eight columns to six and fit a 1024-wide window where it used to need 1100.

Specs are grouped by category. The band above each group carries the category, how many specs
are in it, and how many of their rules pass their tests, as `mcp · 6 specs · 108 of 113 pass`
with a bar after it. The gate is not repeated there: the `Signed` column carries it for each
spec and the headline's second line carries it for the project.

Every column holds a minimum width, and those minima sum to less than a 1024-wide window gives
the table, so a laptop shows every column the gate reaches with no sideways scroll. At 1280 and
above every count cell holds its parts on one line. In a window narrower than the sum of the
minima the table scrolls sideways rather than squeezing a heading into its neighbour, and no
text on the board is set smaller than 13 pixels in either theme. Nothing on the table is aligned
right: two bare number columns twelve pixels apart read as one number.

**A column exists only where its cell does.** A project at `passed` is not shown two empty
evidence columns, and nothing has to be configured to get the rest: `purlin:init --gate strong`
is the whole of it.

Pressing a spec expands its rules. Each row carries the rule id, the rule text, and one pill per
cell that exists, so a rule at `signed` shows three pills and the same rule at `passed` shows
one. A pill reads the cell's word: `passed`, `partial`, `failed`, `no test`, `not run` or
`code changed` at level 1; `strong`, `weak`, `manual test`, `manual audit` or `held` at level 2;
`signed`, `unsigned`, `stale`, `held` or `not required` at level 3.

## Filters

Filter pills sit above the spec table. Each answers a question someone arrives with, and they
compose: a rule shows when every active filter accepts it, and a spec shows when one of its
rules does. The gate decides which exist, because a filter with no cell behind it selects
nothing.

There is one pill per bucket the board shows and one per evidence column beyond the tests, in
the order the tiles and the columns read. Each pill carries the number of rules it accepts, so
it and the tile or the cell it mirrors state the same number before anything is pressed.

| Filter | What it selects | Exists at |
|---|---|---|
| `Untested` | rules in the untested tile: drafted, or ready with no test or no current counting run | every gate |
| `Failing` | rules in the failing tile: every platform that ran the tests found a failure | every gate |
| `Partial` | rules in the partial tile: passed on one platform, failed or did not run on another | every gate |
| `Weak` | rules whose strong cell reads anything but `strong`: `weak`, `manual test`, `manual audit` or `held` | `strong` and above |
| `Unsigned` | rules whose signed cell reads `unsigned` | `signed` |
| `Stale or held` | rules flagged stale, held, or both | `signed` |

## Rule

Pressing a rule opens it.

![The rule screen for login RULE-1: the spec status and the three cell rows with the risk, origin, spec, last run and signature file, then the brief panel, the sign panel and the proofs](images/dashboard-rule.png)

The screen opens with the feature, the rule id and the rule's text, then one panel of facts:
the spec status, `ready` or `drafted`, then one row per cell that exists, then the risk at
`strong` and above, the origin, the spec's path, the last run and the signature files that bind
the rule. Each cell row carries the cell's word as a pill and the reasons it carries:
`failing: tests/test_login.py`, `windows: no record yet`, `code changed since 9f8e7d6`,
`strength 64% under 80%`, `manual proof`, `held by sam@acme.com: the lock expiry is never
read`, `by jane@acme.com`. A cell with nothing to add carries no reason.

The passed cell's row also carries one small box per operating system a counting run covered,
labelled `lin`, `mac` or `win`, green where the rule passed there and red where it failed, each
naming that system's word, the source of its newest run and how old that run is in its hover.
The board draws no such box: which platform found what is the rule's business, and the `Tests`
cell's hover sums it for the spec. The signed cell's row names the signer and the date beside
the word.

At `strong` and above the **Brief panel** follows: the test strength beside `min_strength`, the
free-check findings on the proof text and the test body, what the model review observed, each
in one sentence naming the proofs it concerns, whether the review settled the question, and a
link to the brief file. The brief reports and recommends nothing, so what you read here is what
was seen, not what to do about it.

At `signed` the **Sign panel** comes next. A rule that is not signed is headed `To sign` and
names the command, `purlin:sign <feature> <RULE-N>`, to run in Claude Code: a signature is a
signed commit by someone on the signer list, so this page can only read one back once it is on
the branch. A rule that is signed is headed `Signed` and names who signed it.

The **Proofs** are last, each with its tier, its findings and the tests that ran it.

`← Review list` at the top closes the rule and returns to the list it was opened from; from the
board the same link reads `← Board`.

## Review list

The review list is the rules whose next step is a person. The tab exists at `strong` and above,
because below that there is no cell a person answers.

![The review list: the header, the risk summary, and three rows grouped by risk, each with its feature, rule id, text, risk tag, cell word and reasons](images/dashboard-review-list.png)

The header says `<n> rules need a person`. Under it the risk summary prints one line per risk
that has rows, with the counts of unsigned, stale, held, manual test and manual audit rules in
that risk; a risk with nothing on the list gets no line. Then the rows, grouped by risk with
high first, and within a group the stale and held rules before the rest. A row carries the
feature, the rule id, the rule's text cut to one line, its risk tag, the word of the cell that
blocks it, and that cell's reasons.

A rule is on the list when its blocking cell is the strong cell reading `manual test`,
`manual audit` or `held`, or the signed cell reading `unsigned`, `stale` or `held`. Nothing else is: a rule with no test, a
failing rule and a weak rule are all build work, and they stay on the board. When nothing is
waiting the tab reads `Review list (0)` and the screen says so.

`purlin:sign` walks the same list one brief at a time in a checkout. The page is the read-only
view of it, for someone who has no checkout.

## Both themes

The toggle in the top bar switches between dark and light. Every colour on the page is a token
the theme redefines, so nothing else changes and the logo swaps to the colourway that reads on
the new ground. The choice is remembered in the browser.

## Without a checkout: scan.py

Anyone with a repository URL can print the same rollup without cloning the repository whole:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/report/scan.py" --repo <url> [--ref <branch-or-tag>]
```

It reads `specs/`, `.purlin/tests/` and `.purlin/records/` by sparse fetch and prints the headline, one line per
bucket, and the flags beside them, then how far the ref has moved past the newest record, then
the review list, one line per rule with its risk, the rule, the cell that blocks it and why a
person is needed. `--repo` also takes a local path. CI posts the same rollup as a pull request
comment, so a reviewer reads one answer whether they are on the pull request, in a checkout, or
looking at the page.

## Next

- [running-and-records.md](running-and-records.md): what writes the data this page shows.
- [review-and-signing.md](review-and-signing.md): working the review list.
