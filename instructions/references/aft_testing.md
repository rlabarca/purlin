# AFT Testing Protocol

> **Reference file.** Loaded on demand when a feature has AFT metadata.
> Stub location: BUILDER_BASE Section 3.

## What AFT Tests

AFT verifies what the user actually sees -- the rendered UI, the API response, the CLI output -- not the internal code that produces it. This is the strongest expression of the Behavior Over Artifacts mandate.

| Layer | What it tests | Example |
|-------|--------------|---------|
| Unit/Integration | Code paths and logic | Function returns correct value |
| AFT | User-visible outcome | Browser renders the correct layout |

## Verdict Handling

| Verdict | Owner | Builder Action |
|---------|-------|---------------|
| BUG | Builder | Fix before status tag commit. Code doesn't match spec/Figma. |
| STALE | PM | Log as `[DISCOVERY]` in companion file and continue. Not a Builder blocker. |
| SPEC_DRIFT | PM | Log as `[DISCOVERY]` in companion file and continue. Not a Builder blocker. |

## Iteration Protocol

The Builder MUST iterate the AFT tool until all visual spec items and manual scenarios produce zero BUG verdicts. Each iteration:

1. Run the AFT tool (e.g., `/pl-aft-web` for `> AFT Web:` features).
2. Review BUG verdicts -- fix the implementation.
3. Re-run until zero BUGs remain.

Features without any AFT metadata (`> AFT Web:`, `> AFT API:`, etc.) skip AFT entirely.

## Figma Triangulation

When Figma MCP is available, AFT performs a three-source triangulated comparison:

- **Source 1:** Figma design (via MCP, read-only)
- **Source 2:** Feature spec (Visual Specification checklists, Token Map)
- **Source 3:** Live application (observed via Playwright, HTTP client, etc.)

This three-source comparison is the acceptance bar. It runs regardless of the implementation phase (B1 or B2) and regardless of Token Map/brief.json availability.

## B1/B2 Phase Integration

During phased delivery, AFT behavior differs by sub-phase:

- **B1 (Build):** AFT runs per-feature after local tests pass. Visual design read priority during implementation: Token Map -> brief.json -> Figma (last resort). AFT itself still reads Figma directly when available.
- **B2 (Test):** AFT re-runs for ALL features in the current phase. Visual design priority inverts: reference images + Figma MCP + Playwright = full three-source verification. This catches cross-feature regressions and visual drift.
- **B3 (Fix):** Re-run AFT after each fix to confirm resolution.

Status tags are committed only after B2 passes or B3 escalations are recorded.

## Status Tag Integration

- AFT must pass (zero BUG verdicts) before the status tag commit (Step 4).
- Features with `[Complete]` scope must have zero AFT failures.
- Features with `[Ready for Verification]` must have zero BUG verdicts; STALE/SPEC_DRIFT verdicts are acceptable.

## Implementation Family

See `features/arch_automated_feedback_tests.md` for the full AFT type taxonomy, metadata tags, and naming conventions.

## Cross-References

- **Behavior Over Artifacts:** BUILDER_BASE Section 3, Step 3 (Verify Locally)
- **Builder Decision Protocol:** `instructions/references/builder_decision_protocol.md`
- **Phased Delivery B1/B2/B3:** `instructions/references/phased_delivery.md` Section 10.10
- **AFT Architecture:** `features/arch_automated_feedback_tests.md`
