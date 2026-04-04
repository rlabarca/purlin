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
- RULE-6: Expanded detail shows each rule with id, description, source (blank for own rules, "required" or "global" for others), status, and proof location
- RULE-7: Toggling dark/light mode persists the preference to localStorage
- RULE-8: Staleness indicator shows amber warning when data is older than 1 hour
- RULE-9: Staleness indicator shows red warning when data is older than 24 hours
- RULE-10: Anchor features display a type pill (anchor or global) next to their name
- RULE-11: Anchors with source_url display an external link icon with the URL as tooltip
- RULE-12: Feature table columns are sortable by clicking column headers
- RULE-13: Footer docs link uses docs_url from PURLIN_DATA, not a hardcoded URL
- RULE-14: Summary strip shows integrity percentage from audit_summary with color coding, or dash with "run purlin:audit" when null
- RULE-15: Header shows last audit time from audit_summary, with amber warning when stale
- RULE-16: Clicking the staleness indicator refreshes the page to load new data
- RULE-17: Dashboard uses full available width up to 2400px and is responsive down to 1100px

## Proof

All visual proofs use Playwright to load the dashboard HTML with synthetic data, interact with UI elements, take screenshots, and verify DOM state.

- PROOF-1 (RULE-1): Use Playwright to read page source; verify script tag with src=".purlin/report-data.js" is present @e2e
- PROOF-2 (RULE-2): Use Playwright to load purlin-report.html without report-data.js; take screenshot; verify page contains text "No dashboard data" and "purlin:status" @e2e
- PROOF-3 (RULE-3): Write report-data.js with summary {total_features:10, ready:5, partial:3, failing:1, no_proofs:1}; load page in Playwright; verify 5 summary cards exist; verify card text matches "10", "5", "3", "1"; take screenshot @e2e
- PROOF-4 (RULE-4): Write report-data.js with 8 features in mixed states; load in Playwright; count table rows with class "fr"; verify count is 8; take screenshot @e2e
- PROOF-5 (RULE-5): Load page with features; click first feature row; verify a detail row with class "dr" becomes visible; verify it contains a rules table; take screenshot of expanded state @e2e
- PROOF-6 (RULE-6): Expand a feature with own + global rules; verify own rules have empty Source column; verify global rules show "global" in Source column; take screenshot @e2e
- PROOF-7 (RULE-7): Load page; click theme toggle; verify data-theme attribute changes; reload page; verify theme persisted from localStorage @e2e
- PROOF-8 (RULE-8): Write report-data.js with timestamp set to 2 hours ago; load in Playwright; verify staleness text contains "ago" and has CSS class "warning"; take screenshot @e2e
- PROOF-9 (RULE-9): Write report-data.js with timestamp set to 2 days ago; load in Playwright; verify staleness text has CSS class "stale"; take screenshot @e2e
- PROOF-10 (RULE-10): Write report-data.js with anchor features (one global, one local); load in Playwright; verify elements with class "tp-global" and "tp-anchor" exist; take screenshot @e2e
- PROOF-11 (RULE-11): Write report-data.js with anchor having source_url; load in Playwright; verify element with class "ext-icon" exists and has title attribute containing the URL @e2e
- PROOF-12 (RULE-12): Load page; click "Coverage" column header; verify table row order changes (first row name differs from default sort); take screenshot @e2e
- PROOF-13 (RULE-13): Write report-data.js with docs_url set to "https://example.com/docs"; load in Playwright; verify footer link href equals "https://example.com/docs" @e2e
- PROOF-14 (RULE-14): Write report-data.js with audit_summary.integrity=85; load in Playwright; verify a summary card contains "85%"; write another with audit_summary=null; reload; verify dash shown instead; take screenshots of both @e2e
- PROOF-15 (RULE-15): Write report-data.js with audit_summary.stale=true; load in Playwright; verify element with class "audit-time stale" exists; take screenshot @e2e
- PROOF-16 (RULE-16): Load page in Playwright; click element with id "refresh-btn"; verify page navigation occurred (URL reloaded) @e2e
- PROOF-17 (RULE-17): Load page in Playwright at viewport width 2400px; verify dashboard container max-width is 2400px; resize to 1100px; verify summary strip reflows to 3 columns; take screenshots at both widths @e2e
