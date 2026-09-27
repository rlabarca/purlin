# Purlin Design System

This page is how Purlin looks: the two surfaces, the colours and what they mean, the type, the
tokens, the two themes and the logo.

## Content fundamentals

**Voice.** Plain, declarative, unhurried. Purlin explains a process, so every sentence does one job. The deck's own example is the model: "One line saying what the software has to do." Not "Define your requirements at the atomic level."

**Person.** Second person for the reader's actions ("you commit it yourself", "before you push"), third person for the system's ("Purlin breaks your code on purpose", "the audit writes a brief for each rule it reached"). First person never appears. The product does not say "we".

**Casing.** Sentence case for titles, buttons and body. Uppercase is reserved for two things: tracked eyebrow labels above a section ("WAYS OF WORKING — 01", "A COVERAGE BOARD") and state badges ("PASSED", "STRONG", "SIGNED"). Command names are always lowercase with a colon: `purlin:audit`, never `Purlin Audit`.

**Honesty as a tone.** The deck labels its own limits out loud — a slide is literally headed "THE HONEST NOTE", and another says "Purlin can't prove code is right. It gives you a paper trail." Copy for this brand should keep that: state the gap rather than skip it.

**Numbers carry the argument.** "42 specs", "71% test strength", "884 of 1195 measured", "Twelve rules changed. Two signatures went stale. Two rules need a person." Figures are exact and unrounded, and they usually close a section rather than open it.

**Machine vs human text.** Anything the machine produced — commands, rule ids, file paths, shas, gates, transcripts — is set in Courier New. Anything a person wrote is Arial. This is the single most consistent rule in the whole deck and it is load-bearing: readers use the typeface to tell whose claim they are reading.

**No emoji, anywhere.** Not in the deck, not in the dashboard, not in the CLI output. Do not add them.

**Sentence shapes to copy.**
- Definitions: "*Record* — The file `purlin:audit` writes: what ran, on which commit, what passed, and the test strength."
- Consequences: "If any of the three change, it no longer counts."
- Instructions: "Run it at the start of a session, after a design export moved, and before a release."
- Reassurance: "Same commands, same output." / "Nothing removed."

**Avoid:** marketing superlatives, "seamless", "powerful", "revolutionise", exclamation marks, rhetorical questions outside the one on slide 2, and any sentence that describes a benefit without naming the mechanism.

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
for eyebrows, gate names and one emphasis per view. There is no second accent, no gradient and
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
commands, rule ids, file paths, shas, gates and transcripts, is set in Courier New. Anything a
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

Both themes ship. The light theme is extrapolated from the warm half: paper grounds `#FBF8EC` to
`#D3C9BC` from the cream, navy ink, copper darkened to `#8F5626` for contrast, and the four state
hues dropped to their 700 steps so they clear 4.5:1 on paper.

## Icons

Purlin ships no icon set. The interface uses the unicode glyphs `▶ ▼ ▲ →`, which inherit
`currentColor`, and status dots drawn in CSS. No emoji.

## The logo

A roof truss with a dashed centre line: a purlin is the horizontal beam a roof's rafters rest
on. `assets/logo.svg` has cream webs and copper measure lines, for navy grounds.
`assets/logo-light.svg` has navy webs and a darkened copper, for paper and white.
`assets/logo-datauri.js` is the dark mark as a data URI, which the dashboard build reads and
recolours for the light theme.
