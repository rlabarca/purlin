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
so an approval you have just made appears without you reloading anything. A commit you make by
hand outside Claude Code shows up after the next `purlin:status`.

**From CI.** A CI verify copies the page and its data into the `purlin-dashboard` build
artifact. Anyone with repository access downloads it from the run and opens the page. Nothing
is provisioned, nothing is hosted, and no site has to be published.

## The chrome

Every screen carries the same top bar: the logo, how old the data is, the gate in force, the
commit the data was built from, and the theme toggle. How old the data is is a button: press it
to reload the page. The age recomputes itself every 60 seconds from the stamp the data already
carries, so a tab left open does not read `less than a minute old` an hour later. Below it are
the tabs: Board, Review list with its count, and the open rule last when there is one.

## Board

The Board is where every rule stands.

![The Board at the tested gate: seven state tiles, and two specs with coverage bars and state badges](images/dashboard-solo.png)

At the `tested` gate the board carries a headline count, one tile per state, and a table of
specs grouped by category with coverage and state. Three columns, because three artifacts
exist.

![The Board at the recorded gate, with the risk grid and the strength, latest record and re-verify columns](images/dashboard-team.png)

At `recorded` the same board has more in it, because more exists to show: a risk-by-state grid,
and the strength, latest record and re-verify columns. The latest record column prints the
record's label, `ci` or `developer`, which is the thing that decides whether it counts.

![The Board at the approved gate, with the approvals column, a stale rule, and two warnings above the ledger](images/dashboard-regulated.png)

At `approved` an approvals column joins them. Warnings sit above the ledger: an uncommitted
working tree, or a spec line the parser could not read as a rule. A Stale badge and a pending
re-verify are both visible in one row here, and they mean different things: Stale is text that
changed and needs a human, `1 pending` is code that changed and clears on the next CI run.

**Columns exist only where their artifact does.** Risk appears when rules carry risk tags.
Strength, latest record and re-verify appear when records exist. Approvals appears when approval
files exist. A project at `tested` is not shown seven empty columns, and nothing has to be
configured to get the rest.

## Filters

Five filter pills sit above the spec table. Each answers a question someone arrives with, and
they compose: a rule shows when every active filter accepts it, and a spec shows when one of its
rules does.

| Filter | What it selects |
|---|---|
| High risk not approved | Rules tagged `high` that are not in the Approved state |
| Stale | Rules whose text changed after their approval |
| No negative case | Rules whose proofs only cover the happy path |
| Low test strength | Specs whose test strength is below `min_strength` |
| Open items | Drafted, Stale, awaiting an AI review, or re-verify pending |

## Rule

Clicking a rule opens it.

![The rule screen for login RULE-1: state, risk, origin, spec path, test strength, latest record, approvals, the review reason, and the proof with its test](images/dashboard-rule.png)

One rule, its state and tags, the spec that holds it, its test strength, the latest record, the
approval files that bind it, and each proof with its tier and the tests that ran it. This is the
screen to open when a status line says a rule needs a look and you want to know what it claims
before you decide.

The Review panel says why the rule is on the review list and what the free checks found, each
finding in one sentence naming the proofs that carry it. Under it, a rule that is not approved
names the command that approves it, `purlin:approve <feature> <RULE-N>`, to run in Claude Code:
an approval is a signed commit by someone on the approver list, so this page can only read one
back once it is on the branch. A rule that is approved names who approved it instead.

`← Review list` at the top closes the rule and returns to the list it was opened from; from the
board the same link reads `← Board`.

## Review list

The review list is what CI put in front of a person.

![The review list: four rules grouped high, medium and low, each with its spec, rule id, rule text, state and the reason it is listed](images/dashboard-review-list.png)

Rules are grouped by risk, highest first. A row carries the spec, the rule id, the rule's
text cut to one line and its state, so you read what you are about to open before you open
it. A reason sits beside that only where it says more than the group already does: `stale`,
`strength 64% under 80%`, `windows: no record yet`, `re-verify pending`, or the sentence a
free check writes. A rule whose only reason is its risk carries none, because the group
header said it. QA works this list, never the whole rule table. When nothing is waiting the
tab reads `Review list (0)` and the screen says so.

`purlin:review` walks the same list one brief at a time in a checkout. The page is the read-only
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

It reads `specs/` and `.purlin/records/` by sparse fetch and prints the seven-state rollup,
noting how many commits behind the latest record the ref is. `--repo` also takes a local path.
CI posts the same rollup as a pull request comment, so a reviewer reads one answer whether they
are on the pull request, in a checkout, or looking at the page.

## Next

- [running-and-records.md](running-and-records.md): what writes the data this page shows.
- [review-and-approval.md](review-and-approval.md): working the review list.
