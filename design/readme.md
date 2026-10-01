# Purlin Design System

This page is how Purlin looks: the two surfaces, the colours and what they mean, the type, the
tokens, the two themes and the logo. How Purlin writes is in `references/writing_style.md`.

## Two surfaces

Purlin has two surfaces, and they look different on purpose:

1. **The brand and the docs.** Deep navy grounds, cream ink, blush labels and one copper accent.
   This is the default.
2. **The product.** A cool slate ground under `[data-surface="product"]`, with the same type and
   the same state colours.

The state colours are shared by both surfaces.

## Colour

**Grounds.** Two navies: `#0C3444` for content, `#092936` one step deeper for section breaks and
the top bar. The product surface replaces both with the slate ramp `#0F172A` to `#1E293C`.

**Ink and accent.** Cream `#E4DDD4` is the ink. Blush `#E6BEB0` labels. Slate-blue `#93AEB8`
annotates: list numerals and secondary machine text. Copper `#C0793F` is the only accent, used
for eyebrows and one emphasis per view. There is no second accent, no gradient and
no purple.

**State.** Four hues, one meaning each, on every surface:

| Hue | Means |
| --- | --- |
| green | pass |
| amber | warn |
| red | fail |
| teal | neutral |

**Depth.** No shadows. Depth is built by stacking tint steps (`canvas-deep`, `canvas`,
`surface-1`, `surface-2`) with a hairline between them. If a panel looks flat, add a tint step
or a rule, never a shadow. No backgrounds other than flat colour: no photography, no
illustration, no texture, no gradient.

**Shapes.** Panels round to 4px at most, stat tiles to 6px, and pills round fully. Borders are
horizontal hairlines in three cream weights, 18%, 30% and 45%, plus a solid copper rule for a
call-out.

## Type

Two faces, Arial and Courier New, and no display face or serif. Anything the machine produced,
commands, rule ids, file paths, shas, cell words and transcripts, is set in Courier New. Anything a
person wrote is set in Arial. Readers use the typeface to tell whose claim they are reading.
Bold is reserved for dashboard metrics and group titles; hierarchy otherwise comes from size and
letter-spacing.

## Tokens

`styles.css` is the one entry point, and imports every file under `tokens/`.
`tokens/palette.css` holds the raw values, and only the two theme files reference them.
`tokens/theme-dark.css` defines the semantic aliases and is the default.
`tokens/theme-light.css` defines the same aliases under `[data-theme="light"]`.
`[data-surface="product"]` overrides the grounds and the text for the slate surface and composes
with either theme. Reference the semantic aliases only, never a raw palette value.

Both themes ship. The light theme is ink on paper, extrapolated from the warm half. Its page
ground is a paper tan, `#E8DDC6`; cards and tables sit on it one step lighter, `#F5EFE1`, bands
at `#EDE4D1`, sunken rows at `#E6DBC4`, and the top bar one step darker, `#E3D7BE`, each told
from the next by its tone and a hairline, never a shadow. The ink is navy, the copper is
darkened to `#5E3513`, and the four state hues are darkened to `#0A4A20`, `#653200`, `#7C1313`
and `#00464B`, so green, amber, red and teal still read as pass, warn, fail and neutral. The
logo's light colourway keeps its own copper, `#8F5626`: it is a mark, not text.

In both themes every text, the state hues and the copper included, measures at least 7:1 by the
WCAG contrast formula against every ground it is drawn on. In the dark theme the state hues are
lightened for it to `#6EF5A0`, `#FFD861`, `#FFD0D4` and `#62F5E0` and the copper text to
`#FFD3AE`; outlines and the logo keep the copper `#C0793F`.

## Icons

Purlin ships no icon set. The interface uses the unicode glyphs `▶ ▼ ▲ → ◐ ◑`, which inherit
`currentColor`, and status dots drawn in CSS. No emoji.

## The logo

A roof truss with a dashed centre line: a purlin is the horizontal beam a roof's rafters rest
on. `assets/logo.svg` has cream webs and copper measure lines, for navy grounds.
`assets/logo-light.svg` has navy webs and a darkened copper, for paper and white.
`assets/logo-datauri.js` is the dark mark as a data URI, which the dashboard build reads and
recolours for the light theme.
