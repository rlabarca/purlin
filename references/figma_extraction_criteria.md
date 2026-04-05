> Criteria-Version: 5

# Figma Extraction Criteria

This document defines how `purlin:anchor add-figma` creates design anchors from Figma files. The anchor skill reads this file at runtime.

## Core Principle

A design anchor has ONE job: point to the visual reference and say "match this." The LLM reads the full Figma design during build for implementation fidelity. The anchor doesn't capture individual CSS values — the visual comparison proof catches drift.

## What Goes Where

| Information | Where it goes | Why |
|------------|--------------|-----|
| Visual design (layout, colors, typography, spacing) | Anchor: ONE visual match rule + screenshot comparison proof | LLM reads Figma directly during build — higher fidelity than extracted rules |
| Behavioral annotations (interactions, validation, state changes) | Feature spec that `> Requires:` the anchor | Behavior is owned by the feature, not the design source |

## Anchor Structure

A Figma design anchor is thin — one rule per viewport, one screenshot comparison proof per rule:

```markdown
# Anchor: design_feedback_modal

> Description: Visual design constraints for the feedback modal, sourced from Figma.
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

When the Figma file contains annotations (spec frames, text nodes with behavioral descriptions, component descriptions, Figma comments), document them in the anchor's "What it does" section as context:

```markdown
## What it does
Visual design constraints for the feedback modal, sourced from Figma.

Behavioral annotations from design:
- Clicking upload button triggers native file picker
- Accepted file types: .jpg, .png, .pdf
- Max file size: 5MB
- After file selection, filename appears in attachment area

These behavioral requirements should be added to feature specs that require this anchor.
```

The annotations are listed for reference but do NOT become rules in the anchor. They become rules in the feature spec:

```markdown
# Feature: feedback_modal

> Description: Feedback modal with file upload and form submission.
> Requires: design_feedback_modal
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

The feature spec has `> Requires: design_feedback_modal` — so `purlin:status` includes the visual match rule in coverage. The feature must pass both its behavioral tests AND the visual comparison.

## Responsive Designs

When a Figma file contains multiple viewport variants (desktop, tablet, mobile), create one rule per viewport in the anchor:

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
specs/_anchors/screenshots/design_modal_desktop.png
specs/_anchors/screenshots/design_modal_tablet.png
specs/_anchors/screenshots/design_modal_mobile.png
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
specs/_anchors/screenshots/design_modal_light.png
specs/_anchors/screenshots/design_modal_dark.png
```

## Visual Fidelity Conventions

When writing screenshot comparison proofs, use a named fidelity tier in the proof description to communicate the expected strictness:

| Convention | Intent | Suggested threshold | Use when |
|------------|--------|-------------------|----------|
| **structure** | Layout and arrangement only | ~15% pixel diff | Early development, wireframe matching |
| **design** | Colors, borders, spacing | ~5% pixel diff | Production components, design handoff |
| **pixel-perfect** | Everything including font rendering | ~2% pixel diff | Same-OS CI, strict brand requirements |

Default is **design** when no tier is specified.

These are **naming conventions**, not built-in enforcement. Purlin does not ship a visual comparison tool. The actual comparison happens in your test framework — for example:

- **Playwright + Jest:** `expect(screenshot).toMatchSnapshot("ref.png", { threshold: 0.05 })`
- **Playwright + pixelmatch:** Custom comparison with configurable tolerance
- **Cypress:** `cy.compareSnapshot("ref", 0.05)`

The convention tells the agent (and human readers) what level of strictness the proof expects, and guides `purlin:build` to write the test with an appropriate threshold.

## Tier Tags

All proofs from Figma anchors require rendering — they are `@e2e` by definition. Do NOT leave Figma proofs untagged.

## `> Stack:` for Anchors

Design anchors should include `> Stack:` with the rendering technology so the agent knows how to write proofs:

```
> Stack: react/tailwind (or vue/css, svelte, html/css)
```

If the stack is unknown at anchor creation time, omit it — the feature spec that requires the anchor will have its own `> Stack:`.
