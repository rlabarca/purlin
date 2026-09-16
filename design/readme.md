# Purlin Design System

Purlin is a spec-driven development toolkit for teams building software with AI agents. It turns a feature description into a list of rules, a proof for each rule, a test for each proof, and a signed record of what was checked and when. Its pitch: *specs people agree on, tests that prove them, evidence you can hand over.* The repository is `https://github.com/rlabarca/purlin`.

The product has two surfaces, and they look different on purpose:

1. **The deck** — a 50-slide explainer of the method, set on deep navy in Arial and Courier New, with a warm cream/blush/copper palette. This is the brand's outward voice.
2. **The dashboard** — the local board `purlin:status` generates and CI attaches to every PR. Cool Tailwind-slate ground, the same information architecture, plus a semantic state palette (green / amber / red / teal) that the deck never needed.

This system keeps both. The warm half is the default; `data-surface="product"` switches a subtree to the cool half. State hues are shared.

## Sources used

| Source | What was taken from it |
| --- | --- |
| `uploads/Purlin_Presentation_Design.pptx` | Full palette (six colours, exact hex), type stacks and sizes, slide geometry, all deck copy, both logo files (extracted to `assets/`) |
| `uploads/Screenshot 2026-09-13 at 12.04.35 PM.png` | Dashboard layout, product slate ramp, state hues, component inventory for the product surface |

No codebase or Figma file was provided. Everything in `components/` and `ui_kits/` was derived from those two files; nothing was invented from a similar product.

`scraps/deck-text.md` holds the extracted copy of all 50 slides, verbatim.

---

## Content fundamentals

**Voice.** Plain, declarative, unhurried. Purlin explains a process, so every sentence does one job. The deck's own example is the model: "One line saying what the software has to do." Not "Define your requirements at the atomic level."

**Person.** Second person for the reader's actions ("you commit it yourself", "before you push"), third person for the system's ("Purlin breaks your code on purpose", "CI writes the notes during verify"). First person never appears. The product does not say "we".

**Casing.** Sentence case for titles, buttons and body. Uppercase is reserved for two things: tracked eyebrow labels above a section ("WAYS OF WORKING — 01", "A COVERAGE BOARD") and state badges ("PASSED", "STRONG", "SIGNED"). Command names are always lowercase with a colon: `purlin:audit`, never `Purlin Audit`.

**Honesty as a tone.** The deck labels its own limits out loud — a slide is literally headed "THE HONEST NOTE", and another says "Purlin can't prove code is right. It gives you a paper trail." Copy for this brand should keep that: state the gap rather than skip it.

**Numbers carry the argument.** "42 specs", "71% test strength", "884 of 1195 measured", "Twelve rules changed. Two sign-offs went stale. QA reviews two." Figures are exact and unrounded, and they usually close a section rather than open it.

**Machine vs human text.** Anything the machine produced — commands, rule ids, file paths, shas, gates, transcripts — is set in Courier New. Anything a person wrote is Arial. This is the single most consistent rule in the whole deck and it is load-bearing: readers use the typeface to tell whose claim they are reading.

**No emoji, anywhere.** Not in the deck, not in the dashboard, not in the CLI output. Do not add them.

**Sentence shapes to copy.**
- Definitions: "*Record* — The file Purlin writes when you verify: what ran, on which commit, what passed, and the test strength."
- Consequences: "If any of the three change, it no longer counts."
- Instructions: "Run it at the start of a session, after a design export moved, and before a release."
- Reassurance: "Same commands, same output." / "Nothing removed."

**Avoid:** marketing superlatives, "seamless", "powerful", "revolutionise", exclamation marks, rhetorical questions outside the one on slide 2, and any sentence that describes a benefit without naming the mechanism.

---

## Visual foundations

**Grounds.** Two navies: `#0C3444` for content, `#092936` one step deeper for section breaks and the product's top bar. The deck's PPTX carries a full-bleed 30%-cream veil over the navy on every slide; it is kept here as `--surface-veil` and used for panels, not for the page, because at page scale it lifts cream body text below a comfortable contrast ratio. The product surface replaces both navies with the slate ramp `#0F172A → #1E293C`.

**Palette.** Cream `#E4DDD4` is the ink. Blush `#E6BEB0` labels. Slate-blue `#93AEB8` annotates — list numerals, secondary mono. Copper `#C0793F` is the only accent, used for eyebrows, gate names, measure lines and the one emphasis per slide. There is no second accent, no gradient ramp, and no purple anywhere.

**Type.** Arial and Courier New, one weight each in the deck (regular), with bold reserved for dashboard metrics and group titles. No display face, no serif. Hierarchy comes from size and letter-spacing, not weight: the cover wordmark tracks −0.006em at 180px, the kicker tracks +0.055em at 33px, eyebrows track +0.12em uppercase.

**Backgrounds.** Flat colour. No photography, no illustration, no texture, no pattern, no gradient — the only gradient in the source file is a flat two-stop of the same colour, which is a flat fill. The logo is the only artwork in the entire deck.

**Layout.** 1920×1080. 200px left and right margins on every slide, no exceptions. Slide titles sit at y=230 with a 1px rule 100px beneath. Numbered lists use a fixed 146 / 336 / rest column grid. Content is left-aligned and top-anchored; the only centred things are dashboard stat tiles.

**Corners.** Every shape in the deck is a true rectangle — `prstGeom prst="rect"`, zero rounding. The product softens to 4px on panels and 6px on stat tiles, and fully rounds pills and the 5px coverage bar. Nothing else is rounded.

**Borders.** 1.5px is the deck's stroke weight (13229 EMU). Three cream weights — 18%, 30%, 45% — plus a solid copper rule for call-outs. Horizontal only; there are no vertical rules in either surface.

**Shadows.** None. Zero drop shadows in the source. Depth is built by stacking tint steps (`canvas-deep → canvas → surface-1 → surface-2`) with a hairline between them. If a card looks flat, add a tint step or a rule — never a shadow.

**Cards.** A card is a rectangle with a 1px or 1.5px hairline, a 4px radius at most, a tint one step above its ground, and 24–32px of padding. No header bar, no accent left-border, no elevation on hover.

**Transparency and blur.** Transparency is used only as a tint against a known ground (6% / 10% / 18% / 30% cream). Blur is used nowhere in the source; `--backdrop-blur` exists for modal scrims only.

**Animation.** The deck is static. The dashboard animates state changes only: 140ms hover tints, a 420ms coverage-bar fill on `cubic-bezier(0,0,0,1)`, nothing else. No entrance animations, no parallax, no bounce, no spring. Reduced-motion zeroes every duration.

**Hover and press.** Hover raises a 6% tint of the element's own hue and brightens the border; it never changes size or adds shadow. Press darkens with a navy overlay and applies a 0.985 scale — barely perceptible, intentionally.

**Imagery.** There is none. If a future design needs a photograph, it should be cool-toned and desaturated to sit beside the navy, but the honest answer is that this brand has no photographic language yet.

**Protection gradients vs capsules.** No protection gradients — nothing ever sits over an image. Capsules (pills) are the only enclosing shape besides the rectangle, used for status and buttons.

---

## Iconography

**Purlin ships no icon set.** Neither source contains an icon font, an SVG sprite, or a single icon file. What the interface uses instead:

- **Unicode geometric glyphs** for disclosure and sort affordances: `▶` `▼` `▲` `▾`. These are typographic, inherit `currentColor`, and are the reason the product needs no icon library.
- **Filled circles** as status dots — 7px in group summaries, 9px in the top bar. Drawn as CSS, not as icons.
- **Arrows in prose** — `→` and `↺` appear in the deck as flow connectors between process steps, set in the running typeface.
- **No emoji.**

The only real asset is the logo: `assets/logo.svg` (cream webs, copper measure lines — for navy grounds), `assets/logo-light.svg` (navy webs, darkened copper — for paper and white), plus `assets/logo.png` and the tighter `logo-closing` crop used on the final slide. It is a roof truss with a dashed centre line — a purlin is the horizontal beam a roof's rafters rest on, which is the whole metaphor. `assets/logo-closing.svg` is the same mark, cropped tighter, as used on the final slide.

If a future screen genuinely needs icons, substitute **Lucide** at 1.5px stroke from CDN — closest match to the hairline weight used everywhere else — and record the substitution here. Do not hand-draw SVGs in the brand's name.

---

## Files

```
styles.css            the single entry point consumers link
tokens/               palette, both themes, type, spacing, radii, elevation, motion, base
guidelines/           19 specimen cards rendered in the Design System tab
components/           19 React primitives, grouped by concern
ui_kits/dashboard/    click-through recreation of the product board
slides/               six deck templates at 1920×1080, framed to 1280×720
assets/               logo.svg, logo-light.svg, logo.png, logo-closing.*, logo-datauri.js
scraps/deck-text.md   verbatim copy of all 50 slides
SKILL.md              Agent Skills entry point
```

### Tokens

`tokens/palette.css` holds raw values; never reference those in a component. `tokens/theme-dark.css` defines the semantic aliases and is the default. `tokens/theme-light.css` defines the same aliases under `[data-theme="light"]`. `[data-surface="product"]` overrides grounds and text for the slate surface and composes with either theme.

**The light theme is extrapolated, not sourced.** Neither the deck nor the dashboard has a light variant. The light theme reads the warm half forward: paper grounds `#F7F4EF → #D3C9BC` from the cream, navy ink, copper darkened to `#8F5626` for contrast, and the four state hues dropped to their 700 steps so they clear 4.5:1 on paper. Treat it as a proposal to review, not a recreation.

### Components

**Brand** — `Logo`, `SectionLabel`
**Core** — `Button`, `StatusPill`, `Tag`, `Panel`, `Divider`
**Data** — `StatTile`, `ScorePanel`, `CoverageBar`, `MetricValue`, `DataTable`, `TableHead`, `TableRow`, `GroupHeader`, `DisclosureRow`
**Product** — `TopBar`, `NoticeBar`
**Editorial** — `CodeBlock`, `CommandChip`, `NumberedItem`

Every component has a sibling `.d.ts` (props contract) and `.prompt.md` (what & when, with an example). Each directory has one `@dsCard` HTML showing its states.

**Intentional additions.** `Divider` and `SectionLabel` are not distinct objects in the sources — they are a 1px rule and a tracked caps run that recur on nearly every slide. They are factored out because consumers will otherwise re-derive them inconsistently. Everything else maps one-to-one onto something visible in the deck or the dashboard.

### UI kit

`ui_kits/dashboard/` — board, rule detail and QA review list, click-through. **Marked as a reference recreation of the v0.9.5 dashboard**, recoloured onto the current system rather than the borrowed slate ramp the screenshot used. See its README for what is inert and why.

### Slides

`slides/` — cover, section break, numbered list, split prose + terminal, comparison table, closing statement. Authored at 1920×1080 and scaled into a 1280×720 frame. Plain HTML so they render without the bundle.

---

## Open questions

- **Fonts.** The PPTX names only Arial and Courier New. Exported decks often flatten a licensed face to Arial, so the real brand font may be something else. If Purlin has one, drop the files in and point `--font-sans` at it.
- **The cream veil.** The deck applies a 30% cream overlay across every slide, which would render the ground as `#4D676F` rather than `#0C3444`. This system treats it as a panel tint instead. If the slides really are meant to read slate, say so and the grounds move.
- **The light theme** is an extrapolation, as noted above.
