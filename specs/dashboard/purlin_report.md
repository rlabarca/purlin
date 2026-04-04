# Feature: purlin_report

> Scope: scripts/report/purlin-report.html
> Stack: html/css/javascript

## What it does

Static HTML dashboard that renders Purlin coverage data from `.purlin/report-data.js`. Opens via `file://` in any browser with no server or build step.

## Rules

- RULE-1: HTML loads .purlin/report-data.js via a script tag before rendering
- RULE-2: When PURLIN_DATA is undefined, dashboard shows a no-data message with instructions
- RULE-3: Summary strip shows total features, ready, partial, and failing counts from PURLIN_DATA.summary
- RULE-4: Feature table renders one row per feature with name, coverage fraction, status badge, integrity, and verified columns
- RULE-5: Clicking a feature row expands it to show per-rule detail
- RULE-6: Expanded detail shows each rule with id, description, label, status, and proof location
- RULE-7: Toggling dark/light mode persists the preference to localStorage
- RULE-8: Staleness indicator shows amber warning when data is older than 1 hour
- RULE-9: Staleness indicator shows red warning when data is older than 24 hours
- RULE-10: Anchor features display a type pill (anchor or global) next to their name
- RULE-11: Anchors with source_url display an external link icon with the URL as tooltip
- RULE-12: Feature table columns are sortable by clicking column headers
- RULE-13: Footer docs link uses docs_url from PURLIN_DATA, not a hardcoded URL
- RULE-14: Summary strip shows integrity percentage from audit_summary with color coding, or dash with "run purlin:audit" when null
- RULE-15: Header shows last audit time from audit_summary, with amber warning when stale

## Proof

- PROOF-1 (RULE-1): Inspect HTML source, verify script tag with src=".purlin/report-data.js" @e2e
- PROOF-2 (RULE-2): Load page without report-data.js, verify no-data message renders @e2e
- PROOF-3 (RULE-3): Load page with sample data, verify summary card numbers match data @e2e
- PROOF-4 (RULE-4): Load page with sample data, verify feature table row count matches features array length @e2e
- PROOF-5 (RULE-5): Click a feature row, verify detail section appears with rule table @e2e
- PROOF-6 (RULE-6): Expand a feature, verify rule rows show id, description, label, status, and proof @e2e
- PROOF-7 (RULE-7): Toggle theme, reload page, verify theme persisted from localStorage @e2e
- PROOF-8 (RULE-8): Set timestamp to 2 hours ago in data, verify amber staleness warning @e2e
- PROOF-9 (RULE-9): Set timestamp to 2 days ago in data, verify red staleness warning @e2e
- PROOF-10 (RULE-10): Load page with anchor features, verify anchor/global pills visible @e2e
- PROOF-11 (RULE-11): Load page with anchor having source_url, verify external link icon with tooltip @e2e
- PROOF-12 (RULE-12): Click a column header, verify table re-sorts by that column @e2e
- PROOF-13 (RULE-13): Load page with docs_url in data, verify footer link href matches @e2e
- PROOF-14 (RULE-14): Load page with audit_summary having integrity=85, verify "85%" card with green color; load with null audit_summary, verify dash with prompt @e2e
- PROOF-15 (RULE-15): Load page with audit_summary having stale=true, verify amber "consider re-auditing" text in header @e2e
