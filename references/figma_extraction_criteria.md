> Criteria-Version: 5

# Figma Extraction Criteria

This document defines how `purlin:invariant add-figma` creates design invariants from Figma files. The invariant skill reads this file at runtime.

## Core Principle

A design invariant has ONE job: point to the visual reference and say "match this." The LLM reads the full Figma design during build for implementation fidelity. The invariant doesn't capture individual CSS values — the visual comparison proof catches drift.

## What Goes Where

| Information | Where it goes | Why |
|------------|--------------|-----|
| Visual design (layout, colors, typography, spacing) | Invariant: ONE visual match rule + screenshot comparison proof | LLM reads Figma directly during build — higher fidelity than extracted rules |
| Behavioral annotations (interactions, validation, state changes) | Feature spec that `> Requires:` the invariant | Behavior is owned by the feature, not the design source |

## Invariant Structure

A Figma design invariant is thin — one rule per viewport, one screenshot comparison proof per rule:

```markdown
# Invariant: i_design_feedback_modal

> Type: design
> Source: figma.com/design/TEZI0T6lObCJrC9mkmZT8v/modal-test
> Visual-Reference: figma://TEZI0T6lObCJrC9mkmZT8v/0-1
> Pinned: 2026-04-03T00:00:00Z

## What it does
Visual design constraints for the feedback modal, sourced from Figma.

## Rules
- RULE-1: Implementation must visually match the Figma design at the referenced node

## Proof
- PROOF-1 (RULE-1): Render component at same viewport size as Figma frame, capture screenshot, compare against Figma screenshot; verify visual match at design fidelity @e2e
```

One rule. One proof. The LLM reads Figma directly during build for full fidelity. The test does a visual comparison to catch drift.

## Behavioral Annotations

When the Figma file contains annotations (spec frames, text nodes with behavioral descriptions, component descriptions, Figma comments), document them in the invariant's "What it does" section as context:

```markdown
## What it does
Visual design constraints for the feedback modal, sourced from Figma.

Behavioral annotations from design:
- Clicking upload button triggers native file picker
- Accepted file types: .jpg, .png, .pdf
- Max file size: 5MB
- After file selection, filename appears in attachment area

These behavioral requirements should be added to feature specs that require this invariant.
```

The annotations are listed for reference but do NOT become rules in the invariant. They become rules in the feature spec:

```markdown
# Feature: feedback_modal

> Requires: i_design_feedback_modal
> Scope: src/components/FeedbackModal.jsx
> Stack: react/tailwind

## Rules
- RULE-1: Clicking upload button triggers native file picker
- RULE-2: Accepted file types are .jpg, .png, .pdf
- RULE-3: Max file size is 5MB
- RULE-4: After file selection, filename appears in attachment area

## Proof
- PROOF-1 (RULE-1): Click upload button; verify file picker dialog opens @e2e
- PROOF-2 (RULE-2): Attempt to upload a .exe file; verify it's rejected @e2e
- PROOF-3 (RULE-3): Upload a 6MB file; verify error message @e2e
- PROOF-4 (RULE-4): Upload valid file; verify filename displayed @e2e
```

The feature spec has `> Requires: i_design_feedback_modal` — so `sync_status` includes the visual match rule in coverage. The feature must pass both its behavioral tests AND the visual comparison.

## Responsive Designs

When a Figma file contains multiple viewport variants (desktop, tablet, mobile), create one rule per viewport:

```markdown
## Rules
- RULE-1: Implementation must visually match the Figma design at desktop viewport (1440px)
- RULE-2: Implementation must visually match the Figma design at tablet viewport (768px)
- RULE-3: Implementation must visually match the Figma design at mobile viewport (375px)

## Proof
- PROOF-1 (RULE-1): Render at 1440px width, capture screenshot, compare against desktop Figma screenshot; verify visual match at design fidelity @e2e
- PROOF-2 (RULE-2): Render at 768px width, capture screenshot, compare against tablet Figma screenshot; verify visual match at design fidelity @e2e
- PROOF-3 (RULE-3): Render at 375px width, capture screenshot, compare against mobile Figma screenshot; verify visual match at design fidelity @e2e
```

Capture a reference screenshot for EACH variant:

```
specs/_invariants/screenshots/i_design_modal_desktop.png
specs/_invariants/screenshots/i_design_modal_tablet.png
specs/_invariants/screenshots/i_design_modal_mobile.png
```

The `> Visual-Reference:` points to the primary variant. Additional variants are referenced in the proofs directly.

## Theme Variants

When a design has theme variants (light/dark, high contrast), create one rule per theme:

```markdown
## Rules
- RULE-1: Implementation must visually match the Figma design in light theme
- RULE-2: Implementation must visually match the Figma design in dark theme

## Proof
- PROOF-1 (RULE-1): Render with light theme, capture screenshot, compare against light theme Figma screenshot; verify visual match at design fidelity @e2e
- PROOF-2 (RULE-2): Render with dark theme, capture screenshot, compare against dark theme Figma screenshot; verify visual match at design fidelity @e2e
```

Capture one screenshot per theme:

```
specs/_invariants/screenshots/i_design_modal_light.png
specs/_invariants/screenshots/i_design_modal_dark.png
```

## Visual Fidelity Tiers

Instead of raw pixel percentages, Purlin uses named fidelity tiers that describe what you want to catch:

| Tier | What it catches | What it allows | Use when |
|------|----------------|----------------|----------|
| **structure** | Missing sections, wrong arrangement, major spacing breaks | Color differences, font rendering, minor spacing | Early development, wireframe-level matching |
| **design** | Wrong colors, missing borders, icon changes, spacing shifts | Font rendering differences across OS, subpixel antialiasing | Production components, design handoff |
| **pixel-perfect** | Everything — font weight, subpixel spacing, antialiasing | Almost nothing | Same-OS CI, strict brand requirements |

If no fidelity tier is specified in a proof, the default is **design**.

The fidelity tier is written by whoever creates the invariant or anchor — in the proof description:

```
- PROOF-1 (RULE-1): Screenshot comparison at design fidelity @e2e
```

For a wireframe-stage mockup:

```
- PROOF-1 (RULE-1): Screenshot comparison at structure fidelity @e2e
```

For strict brand requirements:

```
- PROOF-1 (RULE-1): Screenshot comparison at pixel-perfect fidelity @e2e
```

### Internal mapping (reference only)

The tiers map to pixel diff thresholds internally. Users don't need to set these — they're documentation for how the comparison works:

| Tier | Pixel diff threshold |
|------|---------------------|
| structure | 15% |
| design | 5% |
| pixel-perfect | 2% |

The screenshot comparison:
1. Renders the built component in a real browser (Playwright)
2. Captures a screenshot
3. Compares pixel-by-pixel against the visual reference (Figma screenshot)
4. Fails if pixel difference exceeds the tier's threshold

## Tier Tags

All proofs from Figma invariants require rendering — they are `@e2e` by definition. Do NOT leave Figma proofs untagged.

## `> Stack:` for Invariants

Design invariants should include `> Stack:` with the rendering technology so the agent knows how to write proofs:

```
> Stack: react/tailwind (or vue/css, svelte, html/css)
```

If the stack is unknown at invariant creation time, omit it — the feature spec that requires the invariant will have its own `> Stack:`.
