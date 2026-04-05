---
name: status
description: Show rule coverage dashboard with feature table
---

Show rule coverage across all features. Always outputs a consistent table followed by a summary line and dashboard link.

## Usage

```
purlin:status                   Show all features
purlin:status --role <role>     Filter by role (pm, dev, qa)
```

## Step 1 — Call sync_status

```
sync_status(role: <from argument, optional>)
```

## Step 2 — Feature Table (mandatory)

**Always** display a table with three columns: Feature, Coverage, and Status. Every feature and anchor must appear in this table, sorted by status (PARTIAL first, then PASSING, then VERIFIED). Anchors are labeled with `(anchor)` after the name.

```
  Feature                              Coverage   Status
  ─────────────────────────────────────────────────────────
  purlin_report                           12/41   PARTIAL
  schema_spec_format (anchor)              7/8    PARTIAL
  sync_status                             38/41   PARTIAL
  config_engine                           15/15   PASSING
  dashboard_visual (anchor)               11/11   PASSING
  e2e_audit_cache_pipeline                15/15   PASSING
  skill_find                               4/4    VERIFIED
  skill_build                              7/7    VERIFIED
  security_no_dangerous_patterns (anchor)  5/5    VERIFIED
```

Coverage format is `proved/total` rules. The table must include **every** feature and anchor — never omit rows or collapse them into a summary.

Do NOT print the per-feature detail breakdown (individual RULE/PROOF lines and `→` directives) in the table output. The table is a dashboard overview. If the user wants detail on a specific feature, they can use `purlin:find <name>`.

## Step 3 — Summary Line

After the table, print a one-line summary:

```
Summary: 42 features | 10 VERIFIED | 20 PASSING | 6 PARTIAL | 3 FAILING | 3 UNTESTED
```

## Step 4 — Dashboard Link

If `purlin-report.html` exists at the project root, print the clickable link:

```
Dashboard: file://<absolute-path-to-project>/purlin-report.html
```

Check for the file with a glob or ls before printing. If the file does not exist, skip this line.

## Status Definitions

| Status | Meaning |
|--------|---------|
| VERIFIED | All rules proved + verification receipt matches |
| PASSING | All rules proved, no receipt yet |
| PARTIAL | Some rules proved, none failing — more tests needed |
| FAILING | Any proof has status FAIL |
| UNTESTED | No proofs at all |

The progression is: UNTESTED → PARTIAL → PASSING → VERIFIED.
