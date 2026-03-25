# Implementation Notes: Purlin Scan Engine

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (silent on per-feature timestamp filtering) | Exemption index stores (timestamp, message) tuples and filters per-feature by status_ts | DISCOVERY | PENDING |

## [DISCOVERY] Per-feature exemption timestamp filtering (2026-03-25)

The exemption index (`_build_exemption_index`) originally stored only commit
messages and used `--since={min_ts}` where `min_ts` was the **global** earliest
status commit across all features. This meant the exemption check in
`_check_spec_modified_after_completion` saw commits that predated a specific
feature's completion — e.g., the original `arch: author feature specs` commit
appeared alongside the `[Spec-FMT]`-tagged recategorize commit, causing false
positives on 30 features.

**Fix:** The index now stores `(timestamp, message)` tuples. The check filters
entries to only those with `ts > status_ts` for the specific feature, so commits
before completion are correctly ignored.
