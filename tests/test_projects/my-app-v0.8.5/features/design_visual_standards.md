# Policy: Visual Design Standards

> Label: "Design: Visual Design Standards"
> Category: "Design"

## Purpose

Defines the visual language for all features: design tokens (color, typography, spacing, border radius) implemented as CSS custom properties. All UI features must reference these tokens to ensure visual consistency across the application.

## Design Invariants

### Color Tokens

- `--color-neutral-800`: `#1e1e1e`
- `--color-neutral-100`: `#eeeeee`
- `--color-neutral-300`: `#a3a3a3`
- `--color-white`: `#ffffff`
- `--color-bg-elevated`: `#ffffff`
- `--border-primary`: `#dadada`
- `--text-primary`: `#121212`
- `--text-secondary`: `#3b3b3b`
- `--text-white`: `#f9f9f9`
- `--color-danger`: `#c0392b`

### Typography

- Font family: Inter (loaded from Google Fonts)
- Scale:
  - 12px Regular — captions, helper text
  - 14px Medium — labels, body text
  - 16px Semi Bold — headings

### Spacing

- Base unit: 4px
- Common values: 4, 8, 12, 16, 24px

### Border Radius

- Small: 8px (inputs, buttons)
- Medium: 12px (attachment zones)
- Large: 16px (modal card, footer corners)

## Scenarios

No automated or manual scenarios. This is a policy anchor node — its "scenarios" are
process invariants enforced by instruction files and tooling.
