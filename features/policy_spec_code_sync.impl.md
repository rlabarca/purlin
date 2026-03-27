# Implementation Notes: Spec-Code Synchronization

## Active Deviations

| Spec says | Implementation does | Tag | PM status |
|-----------|-------------------|-----|-----------|
| (none) | (none) | — | — |

## Notes

**[IMPL]** Added `[IMPL]` tag to `instructions/references/active_deviations.md` Engineer Decision Tags table with NONE severity, no PM review, and format note (severity line omitted).

**[IMPL]** Updated `instructions/PURLIN_BASE.md` §3.1 — replaced "companion file mandate" with "companion file commit covenant" language requiring [IMPL] entries on every code commit.

**[IMPL]** Updated `instructions/PURLIN_BASE.md` §4.2 — rewrote pre-switch check to be mechanical (did companion file get new entries?) with no skip escape.

**[IMPL]** Updated `.claude/commands/pl-build.md` Step 4 — replaced conditional companion file gate with mechanical check. Removed "if all changes match the spec exactly: no companion entry required" exemption.

**[IMPL]** Updated `.claude/commands/pl-mode.md` — added companion file gate as step 2 in mode switch protocol (Engineer exit only). No skip option. Hard block until entries written.

**[IMPL]** Updated `.claude/commands/pl-spec-code-audit.md` — added dimension 13 (Companion coverage) to Gap Dimensions Table, updated triage and deep mode protocols to extract `[IMPL]` entries as code map and check companion debt/stale notes. Updated all "12 dimensions" references to "13".

**[IMPL]** Added `scan_companion_debt()` to `tools/cdd/scan.py` — compares git log timestamps for feature test directories against companion file mtimes. Detects "missing" (no companion file) and "stale" (companion older than code) debt. Wired into `run_scan()` with new `companion_debt` section and `--only companion_debt` support.
