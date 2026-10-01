# Decision 120, lane `dark`: what was built (2026-10-01)

One item: every text in the dashboard's dark theme, in any colour, measures at least 7 to 1
against the ground under it, as the light theme does.

## What changed

- `design/tokens/palette.css`: five new tones, `--green-200:#6EF5A0`, `--amber-200:#FFD861`,
  `--red-200:#FFD0D4`, `--teal-200:#62F5E0`, `--purlin-copper-200:#FFD3AE`.
- `design/tokens/theme-dark.css`: `--state-pass`, `--state-warn`, `--state-fail`,
  `--state-neutral`, `--text-accent` and `--link-hover` point at them. `--accent`,
  `--border-accent` and the `-soft` fills keep their tones. The grounds are unchanged.
- `scripts/report/src/styles.css`: `.btn` takes its text colour from `--text-accent`, not
  `--accent`, so the button's text lightens and its outline keeps the brand copper.
- A dot and a pill's outline take their element's text colour, so they lighten with the text.
- `dev/test_purlin_report.py`: one helper measures every text for both themes. The helper that
  left coloured text out is deleted with its option in the page script.

## Rule and proof, reworded, same numbers

- `purlin_report RULE-75`: The page reads on every screen from 390 to 1500 pixels wide, in both
  themes, on the board and a rule's screen: the page never scrolls sideways, no count, label, box
  or rule id breaks onto two lines, and every text drawn, in any colour, the four state colours
  and the accent included, measures at least 7:1 by the WCAG contrast formula against the ground
  beneath it, read through every translucent layer
- `purlin_report PROOF-66 (RULE-75)`: In the dark theme, open the solo, team and regulated
  samples in turn, each on the board with its first spec open and then on the screen of each of
  that spec's rules; every text drawn, in any colour, measures at least 7:1 against the ground
  under it

`PROOF-104` (light) is unchanged and passes. No number was added, so `> Highest-*` is unchanged.

## Lines a person reads

- `design/readme.md`: "In both themes every text, the state hues and the copper included,
  measures at least 7:1 by the WCAG contrast formula against every ground it is drawn on. In the
  dark theme the state hues are lightened for it to `#6EF5A0`, `#FFD861`, `#FFD0D4` and `#62F5E0`
  and the copper text to `#FFD3AE`; outlines and the logo keep the copper `#C0793F`."
- `docs/dashboard.md`: "The dark theme meets the same 7 to 1: its green, amber, red, teal and
  copper text are lightened to reach it."

## Measured

Dark theme, the three samples, board with the first spec open and each of its rules' screens,
then again with rows and buttons hovered: 2,682 measurements. Lowest ratio per tone:

| Tone | Before | After | Before, hovered | After, hovered |
|---|---|---|---|---|
| fail | 3.03 | 8.28 | 2.62 | 7.15 |
| copper | 3.80 | 9.55 | 3.29 | 8.25 |
| pass | 5.01 | 8.28 | 4.33 | 7.16 |
| warn | 5.32 | 8.29 | 4.59 | 7.16 |
| neutral | 8.16 | 11.33 | 8.16 | 11.33 |
| muted | 7.27 | 7.27 | 7.27 | 7.27 |
| secondary | 7.47 | 7.47 | 7.47 | 7.47 |
| primary | 7.60 | 7.60 | 7.60 | 7.60 |
| idle | 9.03 | 9.03 | 7.80 | 7.80 |

This repository's own data (`.purlin/report-data.js` of the main checkout, read only), board with
the first spec open and its first rule's screen, at 1500, 1024 and 390 pixels: 0 texts under 7.

## Tests

`dev/test_purlin_report.py`, `dev/test_purlin_report_board_layout.py`,
`dev/test_report_refresh.py`: 72 passed before, 72 passed after. With `theme-dark.css` put back
to `main` and the page rebuilt, `PROOF-66`'s test fails and `PROOF-104`'s passes.

## Left open

- The new tones reach 7 to 1 on the lightest ground coloured text is drawn on, a hovered card,
  `rgb(37, 72, 85)`. On a group band, `rgb(45, 78, 90)`, where no coloured text is drawn today,
  pass, warn, fail and copper would measure 6.46 to 6.49; teal 6.97. `PROOF-66` catches a coloured
  text put on a band. Reaching 7 there too costs saturation: red would be `#FFDDDD`, copper
  `#FFDFC4`.
- Fail reads as a pale pink, `#FFD0D4`, and copper as a peach, `#FFD3AE`. No red or copper
  nearer its old tone reaches 7 to 1 on these navy grounds; the ground was not to change. They
  are told apart, and from the blush secondary text `#F6E8E2`, but less sharply than green, amber
  and teal are. The owner should look at `after-solo-board-1024.png`.
- `PROOF-66` does not hover; the hovered figures above come from the scratch script.
- Integration rebuilds `scripts/report/purlin-report.html`; it is not committed here.
- No edit is needed in a file this lane does not own.
