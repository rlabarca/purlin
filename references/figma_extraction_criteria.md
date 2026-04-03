> Criteria-Version: 2

# Figma Extraction Criteria

This document defines how `purlin:invariant sync figma` extracts rules from Figma designs. The invariant skill reads this file at runtime. All extracted rules go into the invariant file — both visual and behavioral.

## Extraction Sources

Figma designs contain two types of information. Both MUST be extracted:

| Source | What it contains | Rule type |
|--------|-----------------|-----------|
| **Design tree** (frames, components, styles) | Visual properties — dimensions, colors, typography, spacing, borders | Visual rules |
| **Annotations** (comments, notes, spec frames) | Behavioral requirements — interactions, validation, accepted inputs, error states | Behavioral rules |

## Visual Extraction (from design tree)

### Required extractions

For each component in the design, extract these when present:

| Property | Example rule |
|----------|-------------|
| **Dimensions** | `RULE-N: Modal width is 428px, height is 541px` |
| **Border radius** | `RULE-N: Modal has 16px border-radius` |
| **Padding** | `RULE-N: Header has 16px 24px padding` |
| **Spacing** | `RULE-N: Sections are spaced 16px apart` |
| **Colors** | `RULE-N: Submit button background is #f59e0b` |
| **Typography** | `RULE-N: Title is Inter Semi Bold 16px, color #121212` |
| **Borders** | `RULE-N: Input has 1px solid #dadada border` |
| **Shadows** | `RULE-N: Dropdown shadow is 0 4px 8px rgba(0,0,0,0.1)` |
| **Component dimensions** | `RULE-N: Upload button is 140px wide, 32px tall` |

### Completeness check

After extraction, verify:
- Every frame with explicit dimensions has a width/height rule
- Every text node has a typography rule (font, size, weight, color)
- Every component with borders has a border rule
- Every component with shadows has a shadow rule
- Interactive elements (buttons, inputs, dropdowns) have dimension rules

If a property is present in the design tree but missing from the extracted rules, add it.

## Behavioral Extraction (from annotations)

### Where to find annotations

1. **Text nodes named "Specs" or similar** — frames containing spec text (like the "Specs" frame in the design tree)
2. **Figma comments** — attached to specific nodes
3. **Component descriptions** — in the component's description field
4. **Annotation frames** — dedicated frames with behavioral descriptions

### Required extractions

Every annotation that describes behavior MUST become at least one rule:

| Annotation type | Example rule |
|----------------|-------------|
| **Interactions** | `RULE-N: Clicking upload button triggers native file picker` |
| **Validation** | `RULE-N: Accepted file types are .jpg, .png, .pdf` |
| **Constraints** | `RULE-N: Max file size is 5MB` |
| **State changes** | `RULE-N: After file selection, filename appears in attachment area` |
| **Error states** | `RULE-N: If file exceeds 5MB, show error message` |
| **Default values** | `RULE-N: Textarea placeholder is "Add any details here ..."` |
| **Options/content** | `RULE-N: Dropdown options are: "Something isn't working", ...` |
| **Conditional behavior** | `RULE-N: If user cancels file picker, no change occurs` |

### Annotation completeness check

After extraction, verify:
- Every annotation text block has produced at least one rule
- Interactive components (buttons, dropdowns, file inputs) have behavioral rules, not just visual ones
- If an annotation mentions an error state, there's a rule for it
- If an annotation mentions a default/placeholder, there's a rule for it

If an annotation exists but has no corresponding rule, add one.

## Proof Descriptions

### Tier tags

All proofs from Figma invariants require rendering the component — they are `@e2e` by definition:

```
- PROOF-1 (RULE-1): Render modal; verify width is 428px and height is 541px @e2e
- PROOF-8 (RULE-15, RULE-16): Click upload; select a 3MB .jpg; verify filename appears @e2e
```

Do NOT leave Figma proofs untagged. Every proof from a design invariant gets `@e2e`.

### Behavioral proofs

Behavioral rules from annotations require interaction tests, not just style checks:

```
# Visual-only (checking CSS)
- PROOF-1 (RULE-1): Render modal; verify width is 428px @e2e

# Behavioral (checking interaction)
- PROOF-8 (RULE-15): Click upload button; select a 6MB .pdf; verify error message shown @e2e
- PROOF-9 (RULE-16): Click upload button; select valid .jpg; verify filename appears in attachment area @e2e
```

### Multi-rule proofs

Group related visual properties into multi-rule proofs when they're verified in the same render:

```
- PROOF-4 (RULE-5, RULE-6, RULE-7, RULE-8): Render modal; verify all typography matches design tokens @e2e
```

Don't group visual and behavioral proofs — they test different things (CSS vs interaction).

## `> Stack:` for Invariants

Design invariants should include `> Stack:` with the rendering technology so the agent knows how to write proofs:

```
> Stack: react/tailwind (or vue/css, svelte, html/css)
```

If the stack is unknown at invariant creation time, omit it — the feature spec that requires the invariant will have its own `> Stack:`.

## Screenshot Comparison Proof

Every design invariant SHOULD include a screenshot comparison proof as the final catch-all:

```
- PROOF-N (RULE-1, RULE-2, ...): Render component, capture screenshot, compare against visual reference; verify <5% pixel difference @e2e
```

This proof catches everything individual rules miss — spatial relationships, alignment, visual weight. Individual rules check measurable properties. The screenshot catches the gestalt.

The screenshot comparison:
1. Renders the built component in a real browser (Playwright)
2. Captures a screenshot
3. Compares pixel-by-pixel against the visual reference (Figma screenshot or reference image)
4. Fails if pixel difference exceeds threshold (default 5%)

This proof is OPTIONAL but RECOMMENDED. Without it, a component can satisfy every individual rule while looking wrong overall.

## Responsive Designs

When a Figma file contains multiple viewport variants (desktop, tablet, mobile):

1. Extract rules for EACH variant. Prefix variant-specific rules:
   ```
   - RULE-1: Modal width is 428px (desktop)
   - RULE-2: Modal width is 100% (mobile)
   - RULE-3: Sidebar collapses to hamburger menu below 768px
   ```

2. Capture a reference screenshot for EACH variant:
   ```
   specs/_invariants/screenshots/i_design_modal_desktop.png
   specs/_invariants/screenshots/i_design_modal_tablet.png
   specs/_invariants/screenshots/i_design_modal_mobile.png
   ```

3. Write separate screenshot comparison proofs per viewport:
   ```
   - PROOF-N (RULE-1, RULE-4, RULE-7): Render at 1440px width; compare against desktop reference @e2e
   - PROOF-M (RULE-2, RULE-5, RULE-8): Render at 375px width; compare against mobile reference @e2e
   ```

4. The `> Visual-Reference:` can point to the primary variant. Additional variants are referenced in the proofs directly.

## Quality Gate

Before writing the invariant file, verify:

1. **Every design tree component** with explicit properties has at least one visual rule
2. **Every annotation** has at least one behavioral rule
3. **Every proof** is tagged `@e2e`
4. **No orphan annotations** — behavioral specs without rules
5. **Dimensions are complete** — width AND height for major components, not just width
6. **Interactive elements have behavioral rules** — buttons do things, inputs validate things, dropdowns have options

If any check fails, add the missing rules before writing the file.
