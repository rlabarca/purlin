# Policy: Spec-Code Synchronization

> Label: "Policy: Spec-Code Synchronization"
> Category: "Framework Core"
> Prerequisite: purlin_sync_system.md
> Prerequisite: active_deviations.md
> Prerequisite: impl_notes_companion.md

[TODO]

## 1. Overview

Specs and code drift apart. This is inevitable — Engineer discovers constraints during implementation that PM couldn't anticipate, and PM refines intent after seeing what got built. The question is not whether drift happens, but whether it's **visible**.

This policy defines the **Spec-Code Synchronization Model**: a protocol that guarantees every code change is documented in the companion file (`features/<name>.impl.md`), creating a continuous audit trail that bridges the gap between what the spec says and what the code does. The companion file is the ground truth of implementation reality — always current, even when the spec lags behind.

### The Synchronization Diagram

```
                    ┌─────────────────────────────────────────────┐
                    │           SPEC-CODE SYNC MODEL              │
                    └─────────────────────────────────────────────┘

     PM writes spec                                     PM updates spec
    ┌────────────┐                                    ┌────────────┐
    │  Feature    │──── Engineer reads spec ──────────▶│  Feature   │
    │  Spec v1    │                                    │  Spec v2   │
    └────────────┘                                    └─────▲──────┘
                                                            │
                                                     PM acknowledges
                                                     deviations or
                                                     absorbs [IMPL]
                                                     notes into spec
                                                            │
    ┌───────────────────────────────────────────────────────┘
    │
    │  ┌──────────────────────────────────────────────────────────┐
    │  │              COMPANION FILE (impl.md)                    │
    │  │         ═══ GROUND TRUTH OF WHAT WAS BUILT ═══          │
    │  │                                                          │
    │  │  [IMPL] Implemented webhook retry per spec §3.2          │
    │  │  [IMPL] Added rate limiting to batch endpoint            │
    │  │  [DEVIATION] Used exponential backoff, spec said linear  │
    │  │  [DISCOVERY] Need circuit breaker for downstream timeout │
    │  │  [AUTONOMOUS] Added request ID header (spec silent)      │
    │  │                                                          │
    │  │  Every code commit ──▶ at least one entry here           │
    │  └──────────────────────────▲───────────────────────────────┘
    │                             │
    │                      Engineer writes
    │                      impl notes with
    │                      EVERY code commit
    │                             │
    │                    ┌────────┴────────┐
    │                    │   Code Change   │
    │                    │   (commit)      │
    │                    └─────────────────┘
    │
    │
    │  ┌──────────────────────────────────────────────────────────┐
    │  │              THE SYNC GUARANTEE                          │
    │  │                                                          │
    │  │  At any point in time:                                   │
    │  │                                                          │
    │  │    Spec + Companion = Complete picture of the feature    │
    │  │                                                          │
    │  │  The spec may lag behind the code, but the companion     │
    │  │  file NEVER lags behind. If you read the spec AND the    │
    │  │  companion, you know exactly what was built and why.     │
    │  │                                                          │
    │  │  ┌─────────┐   ┌────────────┐   ┌──────────────────┐   │
    │  │  │  Spec   │ + │ Companion  │ = │ Complete Truth    │   │
    │  │  │ (intent)│   │ (reality)  │   │ (intent+reality) │   │
    │  │  └─────────┘   └────────────┘   └──────────────────┘   │
    │  └──────────────────────────────────────────────────────────┘
    │
    │
    │  ┌──────────────────────────────────────────────────────────┐
    │  │              ENFORCEMENT & DETECTION                     │
    │  │                                                          │
    │  │  Sync Detection: sync_ledger + sync_state overlay        │
    │  │  ─── Session-level: code files written without ────     │
    │  │  ─── companion files? Surface as code_ahead. ────────   │
    │  │  Write companion entries or run purlin:spec-code-audit.  │
    │  │                                                          │
    │  │  Advisory: purlin:build Step 4 (Status Tag Commit)       │
    │  │  ─── Did companion file get new entries? ───            │
    │  │  WARN if not. Advisory, not blocking.                    │
    │  │                                                          │
    │  │  Detection: scan_sync_ledger()                           │
    │  │  ─── Reads sync_ledger.json + sync_state.json ───      │
    │  │  Per-feature sync status: synced, code_ahead,           │
    │  │  spec_ahead. Surfaced in purlin:status.                 │
    │  │                                                          │
    │  │  Reconciliation: purlin:spec-code-audit                  │
    │  │  ─── Bulk companion writing for code_ahead features ── │
    │  └──────────────────────────────────────────────────────────┘


              ┌──────────────────────────────────────────┐
              │         AUDIT READS IMPL NOTES           │
              │                                          │
              │  purlin:spec-code-audit uses [IMPL] entries │
              │  as a code map — traces what was built    │
              │  back to spec requirements. Detects:     │
              │                                          │
              │  • Code-ahead status (code without notes)│
              │  • Impl coverage (notes without spec)    │
              │  • Stale notes (code changed, note old)  │
              └──────────────────────────────────────────┘
```

### Why Impl Files, Not Just the Spec?

The spec is PM-owned. PM may not be available to update it immediately. The spec may need discussion, design review, or Figma iteration before it can be updated. Meanwhile, the code is already built and deployed.

The companion file is Engineer-owned. It can be updated in the same commit as the code. It captures reality **now**, not after PM catches up. This means:

1. **No information loss during the PM lag.** The companion file records exactly what was built, when, and why — even if the spec won't be updated for days.
2. **PM has a complete delta when they return.** Instead of reverse-engineering code changes from git diffs, PM reads structured `[IMPL]`, `[DEVIATION]`, and `[DISCOVERY]` entries that explain intent.
3. **The audit has a code map.** `purlin:spec-code-audit` uses impl entries as an index of what the engineer intended, making spec-code comparison faster and more accurate.

---

## 2. Requirements

### 2.1 The Companion File Commit Covenant

Every engineer code commit for a feature MUST include a companion file update. No exceptions. No judgment call about whether the change "matches the spec exactly."

- The minimum entry is a single `[IMPL]` line: `**[IMPL]** <what was implemented and which spec requirement it addresses>`
- If the change deviates from spec, the entry MUST use the appropriate deviation tag (`[DEVIATION]`, `[DISCOVERY]`, `[AUTONOMOUS]`, `[CLARIFICATION]`, `[INFEASIBLE]`) instead of or in addition to `[IMPL]`.
- Multiple commits for the same feature in rapid succession (implement + test + fix) MAY batch their entries into a single companion update committed with the last commit in the batch. The gate fires at `purlin:build` Step 4, not per-commit.

### 2.2 The [IMPL] Tag

The `[IMPL]` tag is a new Engineer Decision Tag with severity NONE. It records work that matches the spec — the "happy path" of implementation.

- `[IMPL]` entries do NOT require PM acknowledgment. They are informational.
- `[IMPL]` entries do NOT appear in the Active Deviations table. They are prose entries in the companion file body.
- `[IMPL]` entries MUST still be meaningful — not boilerplate. They describe WHAT was implemented and WHERE in the spec it was required.
- The scan does NOT surface `[IMPL]` entries as PM action items. Only deviation-level tags (`[AUTONOMOUS]`, `[DEVIATION]`, `[DISCOVERY]`, `[INFEASIBLE]`) are surfaced.

### 2.3 Mechanical Enforcement Gates

All enforcement gates MUST be **mechanical** (did the file change?) not **judgmental** (did the engineer deviate?). This removes the failure mode where the engineer decides "this matches the spec" and skips documentation.

#### Advisory: `purlin:build` Step 4 — Companion File Warning

- The build checks the sync ledger for the target feature's `sync_status`.
- If `code_ahead`: **WARN** and recommend writing `[IMPL]` entries. Allow the status tag commit to proceed.
- Advisory only — sync tracking surfaces drift, it does not block writes.

#### Detection: Sync Ledger — `scan_sync_ledger()`

- Reads `.purlin/sync_ledger.json` (persistent, committed) and `.purlin/runtime/sync_state.json` (session-scoped, gitignored).
- Per-feature sync status: `synced`, `code_ahead`, `spec_ahead`, `unknown`.
- `purlin:status` routes `code_ahead` features to Engineer advisory items with a hint to run `purlin:spec-code-audit` for bulk reconciliation.
- Updated on every commit by `sync-ledger-update.sh`.

### 2.4 The Sync Guarantee

At any point in time, reading a feature's spec AND its companion file MUST provide a complete picture of the feature's intended and actual behavior.

- The spec defines intent (what PM wants).
- The companion file defines reality (what Engineer built, and where it differs from intent).
- The union of spec + companion = the complete truth about the feature.
- When the spec is updated to absorb companion entries, PM marks those entries as `[ACKNOWLEDGED]`. The companion file is pruned of acknowledged entries over time, keeping it focused on the current delta.

### 2.5 Audit Integration

`purlin:spec-code-audit` MUST leverage companion file `[IMPL]` entries as a structured index of implementation work:

- **Code-ahead detection**: Features with `code_ahead` sync status (code commits without corresponding companion entries) are a HIGH-severity gap (dimension: "Companion coverage").
- **Impl-to-spec tracing**: `[IMPL]` entries that reference spec sections provide a mapping from code to requirements, making scenario-by-scenario comparison faster.
- **Stale note detection**: If code has been modified since the last companion entry was written (git log comparison), flag as MEDIUM-severity "Stale companion notes."
- **Coverage completeness**: A feature with code changes and only `[IMPL]` entries (no deviations) is a signal that implementation matched spec — the audit can deprioritize deep code comparison for these features (triage optimization).

### 2.6 Performance Constraints

The companion file commit covenant MUST NOT significantly impact engineer velocity:

- Writing a single `[IMPL]` line takes ~5 seconds. This is the minimum overhead per commit batch.
- Batching is allowed within a single `purlin:build` session — multiple commits can share one companion update.
- The removal of the "did I deviate?" judgment call is a net performance gain — no more deliberation overhead.
- The mechanical gate check (did the file change?) is faster than the old judgmental check (review all diffs for deviation).

---

## 3. Scenarios

### Unit Tests

#### Scenario: Companion file commit covenant blocks status tag without impl entry

    Given Engineer has committed code changes for feature "webhook_delivery"
    And features/webhook_delivery.impl.md has no new entries from this session
    When purlin:build Step 4 runs the Companion File Gate
    Then the status tag commit is BLOCKED
    And the message indicates companion file entries are required

#### Scenario: [IMPL] entry satisfies the companion file gate

    Given Engineer has committed code changes for feature "webhook_delivery"
    And features/webhook_delivery.impl.md contains a new [IMPL] entry from this session
    When purlin:build Step 4 runs the Companion File Gate
    Then the status tag commit proceeds

#### Scenario: Sync ledger detects code-ahead from companion debt

    Given Engineer has committed code for features "webhook_delivery" and "rate_limiting"
    And features/webhook_delivery.impl.md has been updated
    And features/rate_limiting.impl.md has NOT been updated
    When scan_sync_ledger() runs
    Then "rate_limiting" has sync_status "code_ahead"
    And purlin:status surfaces it as an Engineer advisory item with companion debt

#### Scenario: Sync ledger detects code-ahead from commit timestamps

    Given feature "webhook_delivery" has code commits at 2026-03-26T10:00:00
    And no spec or impl update since
    When scan_sync_ledger() runs
    Then "webhook_delivery" has sync_status "code_ahead"
    And purlin:status routes it to Engineer advisory items

#### Scenario: [IMPL] entries not surfaced to PM

    Given features/webhook_delivery.impl.md contains only [IMPL] entries (no deviations)
    When purlin:status generates PM action items
    Then no items appear for "webhook_delivery"
    And the [IMPL] entries are not listed as unacknowledged deviations

#### Scenario: Batch companion update across rapid commits

    Given Engineer makes 3 commits for feature "webhook_delivery" in quick succession
    And writes all companion entries in the third commit
    When purlin:build Step 4 runs
    Then the gate passes (companion file was updated during the session)

#### Scenario: Status surfaces code-ahead features

    Given feature "rate_limiting" has sync_status "code_ahead" in sync_ledger.json
    When purlin:status is invoked
    Then "rate_limiting" appears as an Engineer advisory item
    And the hint says "Run purlin:spec-code-audit to reconcile"

#### Scenario: Spec plus companion equals complete picture

    Given feature "webhook_delivery" spec defines retry behavior as "linear backoff"
    And features/webhook_delivery.impl.md contains [DEVIATION] "Used exponential backoff"
    When an agent reads both files
    Then the spec says "linear backoff" (PM intent)
    And the companion says "exponential backoff" (implementation reality)
    And together they provide the complete truth

#### Scenario: Audit uses [IMPL] entries as code map

    Given features/webhook_delivery.impl.md contains [IMPL] entries referencing spec §3.2 and §3.4
    When purlin:spec-code-audit processes "webhook_delivery"
    Then the audit uses [IMPL] references to map code to spec sections
    And scenario-by-scenario comparison is informed by the impl-to-spec mapping

#### Scenario: Audit flags companion debt as HIGH severity

    Given feature "rate_limiting" has code commits but no companion file entries
    When purlin:spec-code-audit evaluates gap dimensions
    Then a gap is recorded with dimension "Companion coverage"
    And the gap severity is HIGH

#### Scenario: Audit flags stale companion notes as MEDIUM severity

    Given feature "webhook_delivery" has code modified after the last companion entry
    When purlin:spec-code-audit evaluates gap dimensions
    Then a gap is recorded with dimension "Companion coverage"
    And the gap description indicates stale companion notes
    And the gap severity is MEDIUM

### QA Scenarios

None.

## Implementation Notes

- This is a new feature. Implementation notes will be populated during development.
