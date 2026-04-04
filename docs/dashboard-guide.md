# Dashboard Guide

Purlin includes a static HTML dashboard that visualizes rule-proof coverage across your project. It runs entirely in the browser with no server, no build step, and no dependencies.

## Overview

The dashboard shows:

- **Summary strip** — total features, rules proved, overall coverage percentage, and verification status at a glance
- **Feature table** — every feature with coverage bars, status badges, integrity percentages, and verification timestamps. Sortable by any column.
- **Expanded detail** — click any row to see per-rule proof status and audit findings (STRONG/WEAK/HOLLOW)
- **Staleness indicator** — warns when the data is old (amber after 1 hour, red after 24 hours)

Anchors are visually distinguishable with type pills (anchor/global) and external reference icons.

## Setup

The dashboard is enabled by default. When you run `purlin:init`, it copies `purlin-report.html` to the project root and sets `"report": true` in config.

To toggle the dashboard on or off after init:

```
purlin:init --report
```

Or edit `.purlin/config.json` directly: set `"report": false` to disable.

### 3. Open in a browser

Open `purlin-report.html` in any browser. The `sync_status` output includes a clickable link when the HTML file exists:

```
→ Dashboard: file:///path/to/your-project/purlin-report.html
```

## Usage

- **Refresh** the browser to pick up new data. Every time `sync_status` runs (via `/purlin:status`, `/purlin:verify`, or any skill that calls it), the data file is updated.
- **Dark/light mode** — toggle via the sun/moon icon. The default is dark mode. Your preference persists to localStorage.
- **Sort** — click any column header in the feature table to sort.
- **Expand** — click a feature row to see per-rule detail and audit findings.

## How Data Flows

```
sync_status runs
    ↓
writes .purlin/report-data.js    (JS data file with current coverage)
    ↓
purlin-report.html loads it      (via <script> tag)
    ↓
browser renders the dashboard
```

The HTML file loads `.purlin/report-data.js` through a script tag. No fetch calls, no CORS, no server. Just a static file loading another static file.

## Audit Data

Audit findings (STRONG/WEAK/HOLLOW assessments) appear in the expanded detail view after running `purlin:audit`. Until an audit has run, the dashboard shows coverage data without quality assessments.

## Gitignored by Design

Both `purlin-report.html` and `.purlin/report-data.js` are gitignored. The HTML is a local tool, not a shared artifact. Each developer runs `purlin:init` (with `"report": true` in config) to get their own copy.

The footer docs link in the dashboard is dynamically derived from the Purlin plugin's git remote, so it points to the correct documentation regardless of where the plugin is hosted.

### Integrity in the Dashboard

The summary strip shows the project-wide integrity score alongside coverage. This comes from the same audit cache that `purlin:status` reads. If the integrity score shows "—", run `purlin:audit` to populate it.
