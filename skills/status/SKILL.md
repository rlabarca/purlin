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

**Always** display a table with five columns: Feature, Coverage, Status, Design and Integrity.
Every feature and anchor must appear in it, sorted by status: FAILING first, then PARTIAL,
PASSING, VERIFIED, and UNTESTED last — attention-first, so what needs work is at the top.
Anchors are labeled with `(anchor)` after the name.

```
  Feature                              Coverage   Status       Design    Integrity
  ──────────────────────────────────────────────────────────────────────────────────
  purlin_report                           12/41   PARTIAL         94%  not audited
  schema_spec_format (anchor)              7/8    PARTIAL         67%          50%
  sync_status                             38/41   PARTIAL         88%  not audited
  config_engine                           15/15   PASSING        100%         100%
  dashboard_visual (anchor)               11/11   PASSING         57%  not audited
  skill_find                               4/4    VERIFIED  structural  not audited
  skill_build                              7/7    VERIFIED         56%          83%
  security_no_dangerous_patterns (anchor)  5/5    VERIFIED  structural   excluded
```

Coverage format is `proved/total` rules. The table must include **every** feature and anchor —
never omit rows or collapse them into a summary.

The two gauge columns come straight from `sync_status`; do not recompute them. Each cell is a
percentage, or one of:

| Token | Meaning |
|-------|---------|
| `not audited` | No assessment for this feature, or only part of it. The answer is not known yet. |
| `structural` | Design only. Every description is a structural presence check, which is the correct proof for a structural rule. Nothing to score, nothing to fix. |
| `excluded` | Integrity only. Every proof is excluded from scoring, so nothing is gradeable. |

`structural` and `excluded` are the same state in each gauge's own vocabulary: STRUCTURAL
describes a *description*, EXCLUDED describes a *test*, and the two never mix
(`references/audit_criteria.md`).

Do NOT print the per-feature rule-by-rule breakdown in the table output. The table is an
overview; `purlin:find <name>` gives detail on one feature. Do surface the `→` directives that
`sync_status` emits for features needing attention, including the gauge-driven ones in Step 3b.

## Step 3 — Summary Line

Print the summary line **exactly as `sync_status` returned it**. Do not compose a replacement:
a reconstructed status-count line cannot carry either gauge, which is why `purlin:status` showed
neither while the server was already computing both.

It looks like this, and each gauge carries its own measurement coverage and its own age, because
the two caches are independent:

```
37/40 features VERIFIED | Proof Design: 86% (566 of 586 measured, 91% of those assessed, 3 hours ago) | Proof Integrity: 2% (15 of 592 measured, 100% of those assessed, 78 days ago, run purlin:audit --integrity)
```

A percentage without its denominator is the thing to avoid: 100% over 15 of 592 assessments is
not a project-wide 100%.

## Step 3b — Gauge Recommendations

After the summary line, surface what the gauges say to do next. **Design before Integrity**:
most Integrity criteria compare a test against its proof description, so a LOOSE description
leaves them nothing to catch, and a high Integrity score over vague descriptions means the spec
is unfalsifiable rather than that the tests are good.

| What you see | What it means | Directive |
|--------------|---------------|-----------|
| Design finding (LOOSE / UNPROVABLE) | The proof description is the artifact at fault | `→ Run: purlin:spec <feature>` |
| Integrity finding (WEAK / HOLLOW) | Only test code moves Integrity; no rewording will | `→ Run: purlin:build <feature>` |
| A gauge reads `not audited` | Nothing measured it yet | `→ Run: purlin:audit --design <feature>` for Design alone, `purlin:audit <feature>` for both |
| A gauge is marked stale | Its cache is over 24h old | Run the command the summary line names |

Never narrow a proof description to make a WEAK finding disappear — that lowers the claim
instead of strengthening the evidence, and on an anchor rule it is forbidden outright.

Report the gauge scores `sync_status` returned. Do not compute either percentage yourself: the
CLI and the dashboard must show the same number from the same computation.

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
