# Feature: purlin_report

> Requires: dashboard_visual
> Scope: scripts/report/purlin-report.html
> Stack: html/css/javascript

## What it does

Static HTML dashboard that renders Purlin coverage data from `.purlin/report-data.js`. Opens via `file://` in any browser with no server or build step.

## Rules

- RULE-1: HTML loads .purlin/report-data.js via a script tag before rendering
- RULE-2: When PURLIN_DATA is undefined, dashboard shows a no-data message with instructions
- RULE-3: Summary strip shows total features, verified, passing, incomplete (partial + untested combined), failing counts from PURLIN_DATA.summary; the incomplete card shows a subtitle breakdown when both partial and untested are nonzero
- RULE-4: Feature table renders one row per feature with name, coverage fraction, status badge, integrity, and verified columns
- RULE-5: Clicking a feature row expands it to show per-rule detail
- RULE-6: Expanded detail shows each rule with id, description, source (blank for own rules, "required" or "global" for others), status, and proof column; when a rule has multiple proofs, all proofs are stacked vertically in a single cell separated by a thin divider, not split across rowspan rows
- RULE-7: Toggling dark/light mode persists the preference to localStorage
- RULE-8: Staleness indicator shows amber warning when data is older than 1 hour
- RULE-9: Staleness indicator shows red warning when data is older than 24 hours
- RULE-10: Anchor features display a type pill (anchor or global) next to their name
- RULE-11: Anchors with source_url display an external link icon with the URL as tooltip
- RULE-12: Feature table columns are sortable by clicking column headers
- RULE-13: Footer docs link uses docs_url from PURLIN_DATA, not a hardcoded URL
- RULE-14: Summary strip shows integrity percentage from audit_summary with color coding, or dash with "run purlin:audit" when null
- RULE-15: Header shows last audit time from audit_summary, with amber warning when stale
- RULE-16: Status column is centered in both the feature table and the expanded rules sub-table at all viewport widths
- RULE-17: Dashboard uses full available width up to 2400px and is responsive down to 1100px
- RULE-18: Coverage bar fill width matches the proved/total fraction — a feature with 2/6 coverage has a bar fill at ~33%, not 100%
- RULE-19: Features are grouped by category with collapsible section headers showing rolled-up summaries (total count, coverage fraction, and status breakdown); category coverage bar is amber when any feature is untested or coverage is incomplete, red when any feature is failing, green only when all features are passing or verified
- RULE-20: Category sections are collapsed by default
- RULE-21: Category and feature open/closed state is persisted to localStorage and restored on reload
- RULE-22: Proof audit tags (STRONG/WEAK/HOLLOW) only appear when audit_summary has data; when audit_summary is null (integrity card shows dash), no audit tags render on any proof
- RULE-23: Expanded detail view shows a status-colored action banner above the rules table: PARTIAL shows how many rules need proofs, FAILING shows how many tests are failing, PASSING shows "run purlin:verify", UNTESTED shows "write tests to begin coverage", VERIFIED shows no banner
- RULE-24: Rules with NO_PROOF status display with an amber left border, visually distinguishing uncovered rules from proved ones
- RULE-25: Rules with FAIL status display with a red left border, visually distinguishing failing rules from passing ones
- RULE-26: Expanded detail view for anchors with source_url shows an "External Reference" info block above the rules table, displaying Source URL (as clickable link), Path (if present, in code font), and Pinned version (SHA truncated to 7 chars for git, full timestamp for Figma); unpinned anchors show amber "Unpinned" text
- RULE-27: External link icon tooltip includes Source URL, Path (if present), and Pinned value (truncated)
- RULE-28: Anchors with `ext_status` of "stale" or "unpinned" display an amber outline "STALE" badge next to the external link icon, with tooltip "Run purlin:anchor sync to update"; anchors with "current" or null ext_status show no badge
- RULE-29: When `uncommitted` array in PURLIN_DATA is non-empty, an expandable "uncommitted work" section appears between the summary strip and the feature table, showing the file count when collapsed and the file list when expanded; when the array is empty or absent, no section appears
- RULE-30: Expanded detail view shows the spec's `## What it does` content as a description block (`.desc-block`) using the full width of the detail container, positioned between the external reference block (or action banner if no external reference) and the "Rules & Proofs" header; the block is only rendered when the feature has a non-null, non-empty description

## Proof

All visual proofs use Playwright to load the dashboard HTML with synthetic data, interact with UI elements, take screenshots, and verify DOM state.

- PROOF-1 (RULE-1): Use Playwright to read page source; verify script tag with src=".purlin/report-data.js" is present @e2e
- PROOF-2 (RULE-2): Use Playwright to load purlin-report.html without report-data.js; take screenshot; verify page contains text "No dashboard data" and "purlin:status" @e2e
- PROOF-3 (RULE-3): Write report-data.js with summary {total_features:10, verified:4, passing:2, partial:2, failing:1, untested:1}; load page in Playwright; verify summary cards show: Features=10, Verified=4, Passing=2, Incomplete=3 (with subtitle "2 partial, 1 untested"), Failing=1; take screenshot @e2e
- PROOF-4 (RULE-4): Write report-data.js with 8 features in mixed states; load in Playwright; count table rows with class "fr"; verify count is 8; take screenshot @e2e
- PROOF-5 (RULE-5): Load page with features; click first feature row; verify a detail row with class "dr" becomes visible; verify it contains a rules table; take screenshot of expanded state @e2e
- PROOF-6 (RULE-6): Expand a feature with own + global rules, one rule having 2 proofs; verify own rules have empty Source column; verify global rules show "global" in Source column; verify the multi-proof rule has both proofs stacked in a single td with a .rprf-sep divider between them; take screenshot @e2e
- PROOF-7 (RULE-7): Load page; click theme toggle; verify data-theme attribute changes; reload page; verify theme persisted from localStorage @e2e
- PROOF-8 (RULE-8): Write report-data.js with timestamp set to 2 hours ago; load in Playwright; verify staleness text contains "ago" and has CSS class "warning"; take screenshot @e2e
- PROOF-9 (RULE-9): Write report-data.js with timestamp set to 2 days ago; load in Playwright; verify staleness text has CSS class "stale"; take screenshot @e2e
- PROOF-10 (RULE-10): Write report-data.js with anchor features (one global, one local); load in Playwright; verify elements with class "tp-global" and "tp-anchor" exist; take screenshot @e2e
- PROOF-11 (RULE-11): Write report-data.js with anchor having source_url; load in Playwright; verify element with class "ext-icon" exists and has title attribute containing the URL @e2e
- PROOF-12 (RULE-12): Load page; click "Coverage" column header; verify table row order changes (first row name differs from default sort); take screenshot @e2e
- PROOF-13 (RULE-13): Write report-data.js with docs_url set to "https://example.com/docs"; load in Playwright; verify footer link href equals "https://example.com/docs" @e2e
- PROOF-14 (RULE-14): Write report-data.js with audit_summary.integrity=85; load in Playwright; verify a summary card contains "85%"; write another with audit_summary=null; reload; verify dash shown instead; take screenshots of both @e2e
- PROOF-15 (RULE-15): Write report-data.js with audit_summary.stale=true; load in Playwright; verify element with class "audit-time stale" exists; take screenshot @e2e
- PROOF-16 (RULE-16): Load page in Playwright at 1920px and 1280px widths; expand a feature; verify the status badge td in the feature table has text-align:center; verify the status td in the rules sub-table has text-align:center; take screenshots at both widths @e2e
- PROOF-17 (RULE-17): Load page in Playwright at viewport width 2400px; verify dashboard container max-width is 2400px; resize to 1100px; verify summary strip reflows to 3 columns; take screenshots at both widths @e2e
- PROOF-18 (RULE-18): Create features with known coverage fractions (2/6 and 5/5); load in Playwright; measure the cov-fill element width as a percentage of the cov-bar; verify 2/6 bar is ~33% and 5/5 bar is 100% @e2e
- PROOF-19 (RULE-19): Write report-data.js with features in 3 categories: "skills" (2 PASSING), "mcp" (1 PASSING + 1 UNTESTED), "_anchors" (1 VERIFIED); load in Playwright; verify "mcp" category has amber coverage bar (cov-partial class); verify "skills" has green bar; verify category status summary for "mcp" includes "1 untested"; take screenshot @e2e
- PROOF-20 (RULE-20): Load page with categorized features; verify no feature rows (.fr) are visible before any interaction; click a category header; verify its features become visible; take screenshot @e2e
- PROOF-21 (RULE-21): Load page; expand a category; reload page; verify the same category is still expanded; collapse it; reload; verify it is collapsed @e2e
- PROOF-22 (RULE-22): Load page with audit_summary having integrity=85 and features with proof-level audit tags; expand a feature; verify .atag elements appear on proofs; take screenshot. Then load with audit_summary=null but same per-feature audit data; expand the same feature; verify zero .atag elements render; take screenshot @e2e
- PROOF-23 (RULE-23): Write report-data.js with features in each status (PARTIAL with 2 NO_PROOF rules, FAILING with 1 FAIL rule, PASSING, UNTESTED, VERIFIED); expand each; verify PARTIAL has .ab-partial banner containing "2 rules need proofs"; FAILING has .ab-failing banner containing "1 test failing"; PASSING has .ab-passing banner containing "purlin:verify"; UNTESTED has .ab-untested banner containing "write tests"; VERIFIED has no .ab element; take screenshots @e2e
- PROOF-24 (RULE-24): Expand a PARTIAL feature with NO_PROOF rules; verify rule rows with NO_PROOF status have class "rule-np"; verify the first td of those rows has a computed border-left-color matching amber; take screenshot @e2e
- PROOF-25 (RULE-25): Expand a FAILING feature with FAIL rules; verify rule rows with FAIL status have class "rule-fail"; verify the first td of those rows has a computed border-left-color matching red; take screenshot @e2e
- PROOF-26 (RULE-26): Write report-data.js with an anchor feature having source_url, pinned (40-char SHA), and source_path; expand the anchor; verify .ext-ref-block exists containing a Source link, Path in code element, and Pinned truncated to 7 chars; write another anchor with no pinned; expand it; verify amber "Unpinned" text; take screenshots @e2e
- PROOF-27 (RULE-27): Write report-data.js with anchor having source_url, pinned, and source_path; verify .ext-icon title attribute contains all three values @e2e
- PROOF-28 (RULE-28): Write report-data.js with one anchor having ext_status="stale" and another with ext_status=null; load dashboard; verify stale anchor has .ext-stale badge with text "STALE" and tooltip containing "sync"; verify non-stale anchor has no .ext-stale badge @e2e
- PROOF-29 (RULE-29): Write report-data.js with uncommitted=["M file1.py","?? file2.js"]; load dashboard; verify .uw-section exists with count "2"; click the header; verify .uw-files becomes visible with file list; reload with uncommitted=[]; verify no .uw-section exists @e2e
- PROOF-30 (RULE-30): Write report-data.js with one feature having description "Handles user login" and another with description null; expand each; verify the first shows a .desc-block containing "Handles user login" positioned before the rules table; verify the second has no .desc-block element @e2e
