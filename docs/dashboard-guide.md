# Dashboard Guide

## What You Need to Know

Open `purlin-report.html` in a browser to see live coverage across your project. It's a static HTML file — no server needed.

```
purlin:init --report    — toggle the dashboard on/off
purlin:status           — updates the dashboard data (prints a clickable link)
```

The dashboard shows: summary strip, anchors section, feature table with coverage bars, and per-rule detail on click. Refresh the browser after running any Purlin command.

---

Purlin includes a static HTML dashboard that visualizes rule-proof coverage across your project. It runs entirely in the browser with no server, no build step, and no dependencies.

![Dashboard summary strip, anchors section, and feature categories](images/dashboard-summary.png)

## Setup

The dashboard is enabled by default. When you run `purlin:init`, it creates a **symlink** at the project root:

```
purlin-report.html -> <purlin-plugin>/scripts/report/purlin-report.html
```

The symlink ensures the dashboard always reflects the latest Purlin version. When the plugin updates, the dashboard updates automatically.

To toggle the dashboard on or off:

```
purlin:init --report
```

Turning **on** creates the symlink and enables data file generation. Turning **off** disables data file generation but does not remove an existing symlink.

### Open in a browser

Open `purlin-report.html` in any browser. `purlin:status` prints a clickable link at the end of its output:

```
Dashboard: file:///path/to/your-project/purlin-report.html
```

## Status Progression

Every feature moves through a fixed progression. The dashboard shows the current status for each feature and anchor.

```
UNTESTED  →  PARTIAL  →  PASSING  →  VERIFIED
```

| Status | What it means | What to do |
|--------|--------------|------------|
| **UNTESTED** | No proofs exist for this feature. Zero tests reference its rules. | Write tests with proof markers: `test <feature>` |
| **PARTIAL** | Some rules have passing proofs, but not all. No proofs are failing. | Write tests for the remaining rules. Coverage shows `proved/total` (e.g., 3/5). |
| **PASSING** | **All** rules have passing proofs. Ready for verification. | Run `purlin:verify` to issue a receipt and move to VERIFIED. |
| **VERIFIED** | All rules proved + a verification receipt has been issued. The receipt contains a tamper-evident `vhash`. | No action needed. If code changes, the receipt becomes stale and status drops back. |
| **FAILING** | At least one proof exists but its test is failing. | Fix the failing test or the code it tests. This blocks progress. |

### How anchors affect status

A feature's "total rules" count includes rules from **all** sources:

- **Own rules** — defined in the feature's `## Rules` section
- **Required anchor rules** — from anchors listed in the feature's `> Requires:` field
- **Global anchor rules** — from anchors with `> Global: true` (auto-applied to all features)

A feature with 3 own rules and 2 global anchor rules has 5 total rules. It reaches PASSING only when all 5 are proved — including the anchor rules. This is why you may see a feature stuck at PARTIAL even after writing tests for all its own rules: the anchor rules need proofs too.

### Example

A feature `login` requires anchor `rest_conventions` (2 rules) and has a global anchor `no_eval` (1 rule). The feature itself has 3 rules.

```
login: 4/6 rules proved         → PARTIAL
  RULE-1: PASS (own)
  RULE-2: PASS (own)
  RULE-3: PASS (own)
  rest_conventions/RULE-1: PASS (required)
  rest_conventions/RULE-2: NO PROOF (required)
  no_eval/RULE-1: NO PROOF (global)
```

Even though all 3 of login's own rules pass, it's PARTIAL because 2 anchor rules are unproved. Once those are covered, it moves to PASSING.

## What the Dashboard Shows

![Feature categories with coverage bars and status badges](images/dashboard-categories.png)

- **Summary strip** — total features, verified count, passing count, incomplete count, failing count, and both quality gauges: Proof Design and Proof Integrity. Each gauge card headlines the figure weighted by measurement coverage, not the assessed score, so a score over a thin slice cannot read as a project-wide result: 100% Integrity from 11 graded proofs out of 643 reads `2%`. Beneath the headline the card states what it measured over (`566 of 586 measured`), coloured by that fraction, and its tooltip carries the per-level counts plus the unweighted assessed score, because a low headline caused by thin coverage needs a wider audit while one caused by bad proofs needs better tests
- **Platform cards** — when some proof declares `@on(<platform>)`, the Verified, Passing and Proof Integrity cards become clickable and open a per-platform table; Failing joins them when a platform has a failing feature. The headline numbers stay the all-platform figures. Verified counts a feature only when every platform it declares is proved and receipted, so its sub-label names what is holding the count back: `34 on host, 30 on windows-2022` when a platform binds it, `every declared platform` when none does. Passing reads `4 awaiting a platform`. A Verified count that fell because a runner has not run yet is not a regression, and the sub-label is what says so

![The Verified card's per-platform table](images/dashboard-platforms.png)

- **Platform chips** — a feature declaring a platform carries a chip per platform under its status badge: `win`, `mac` or `linux` with a mark, green when proved there, amber when awaiting a runner, red when failing. The badge itself never changes colour because of a platform; a PASSING badge held by an awaiting platform only gains a tooltip naming it. Hover a chip for the full record. The expanded detail carries the same information as a Platforms block, one line per platform with the host first and the runner and time that proved it
- **Anchors section** — all anchors from `specs/_anchors/` with coverage bars, status badges, and both quality gauges. Anchors are labeled with `ANCHOR` or `GLOBAL` pills.
- **Features section** — features grouped by category (matching `specs/` subdirectories). Categories are expanded by default; click a category header to collapse one (the choice is remembered per browser).
- **Expanded detail** — click any feature row to see per-rule proof status and audit findings (STRONG/WEAK/HOLLOW for tests, PROVABLE/LOOSE/UNPROVABLE for proof descriptions). Proofs declared in the spec's `## Proof` section that haven't been executed yet appear greyed with a "not run" tag — so the full coverage plan is visible even before any tests exist.
- **Uncommitted files** — when `purlin:status` detects uncommitted spec or proof files, a collapsible section shows which files need committing
- **Staleness indicator** — top-right corner shows time since last `purlin:status` run (amber after 1 hour, red after 24 hours)

## Usage

- **Refresh** the browser to pick up new data after running `purlin:status`, `purlin:verify`, or any skill that checks coverage.
- **Dark/light mode** — toggle via the moon/sun icon in the top right.
- **Sort** — click any column header to sort by that column.
- **Expand** — click a feature row to see per-rule detail and audit findings.

## How Data Flows

### Coverage data

```
purlin:status (or any skill that checks coverage,
or the pre-commit digest hook on every commit)
    |
    v
writes .purlin/report-data.js
    |
    v
purlin-report.html loads it (via <script> tag)
    |
    v
browser renders the dashboard
```

### Audit and quality-gauge data

```
purlin:audit
    |
    v
writes .purlin/cache/audit_cache.json    (STRONG/WEAK/HOLLOW per proof)
    plus .purlin/cache/design_cache.json   (PROVABLE/LOOSE/UNPROVABLE per description)
    |
    v
purlin:status reads the cache on next run
    |
    v
includes audit findings + both gauge scores in .purlin/report-data.js
    |
    v
dashboard shows both gauges in summary strip
    + per-proof STRONG/WEAK/HOLLOW in expanded detail
```

`purlin:audit` populates both caches. `purlin:status` reads them and includes the findings in the data file. A gauge with no data shows "--".

The **Design** and **Integrity** columns are separate because they are separate measurements: one grades the proof *description*, the other the *test* behind it. Neither cell is ever blank. A cell reads:

| Cell | Meaning |
|------|---------|
| `94%` | Measured. Coloured green at 80%+, amber at 50-79%, red below 50%. |
| `not audited` | Nothing has assessed this feature, or only part of it. Amber, because it is actionable. |
| `structural` | Design only. Every description is a structural presence check, which is the correct proof for a structural rule. Teal, because there is nothing to fix. |
| `excluded` | Integrity only. Every proof is excluded from scoring, so nothing is gradeable. Teal. |
| `win ✓` `mac ⏳` `linux ✗` | Status column, under the badge. One chip per platform the feature's proofs declare: green proved there, amber awaiting a runner, red failing there. |

`structural` and `excluded` are the same state in each gauge's own vocabulary: STRUCTURAL
describes a description, EXCLUDED describes a test, and the two never mix. Hover any cell for
the reason and the feature's assessment coverage.

A gauge is never reported as `excluded` or `structural` from a subset. If a feature has twenty
proofs and two were assessed, the cell reads `not audited` however those two graded, because the
answer is not known yet.

The header carries one freshness label per gauge — `/design 3h ago`, `/integrity 78d ago` — each
from its own cache, since the two age independently. A stale gauge names the narrowest command
that refreshes it: `purlin:audit --design`, `purlin:audit --integrity`, or bare `purlin:audit`
when both are stale. Design grading is deterministic and needs no tests; Integrity grading needs
test code and costs LLM calls, so refreshing Design alone should not trigger a full audit.

The Proof Integrity card reads `no tests yet` rather than `run purlin:audit` when every feature
is UNTESTED, because a project being authored spec-first is not a neglected one.

The HTML file loads `.purlin/report-data.js` through a script tag. No fetch calls, no CORS, no server. Just a static file loading another static file.

## Uncommitted Files

When `purlin:status` detects uncommitted changes to spec or proof files, the dashboard shows a collapsible **uncommitted files section** between the summary strip and the anchors table. This helps you remember to commit proof files after test runs or spec edits.

## What's Committed, What's Not

- **`purlin-report.html` is gitignored.** It's a symlink to the installed framework — each developer runs `purlin:init` to get their own.
- **`.purlin/report-data.js` is committed.** It's the project digest — coverage and drift data that travels with the repo so stakeholders (QA, PM, compliance) can open the dashboard without running Purlin tools. A pre-commit hook installed by `purlin:init` regenerates it on every commit (configurable via `purlin:init --digest`: `auto`, `warn`, or `off`).
